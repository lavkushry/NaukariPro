"""Aggregation pipeline: seed sources → fetch with locks → upsert → dedup → age filter."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from naukari_pro.aggregation.base import AdapterRegistry, SourceRecord
from naukari_pro.aggregation.dedup import DedupEngine
from naukari_pro.aggregation.models import NormalizedJob, utc_now_iso
from naukari_pro.aggregation.storage import AggregationStore

# Ensure adapters register
import naukari_pro.aggregation.adapters  # noqa: F401

log = logging.getLogger(__name__)

SOURCES_PATH = Path(__file__).with_name("sources.json")
AGE_FILTER_DAYS = 90
BOARD_404_BACKOFF_HOURS = 12
GLOBAL_CONCURRENCY = 8


@dataclass
class IngestStats:
    sources_attempted: int = 0
    sources_ok: int = 0
    sources_failed: int = 0
    sources_missing: int = 0
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    removed: int = 0
    dedup_skipped: int = 0
    age_filtered: int = 0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sources_attempted": self.sources_attempted,
            "sources_ok": self.sources_ok,
            "sources_failed": self.sources_failed,
            "sources_missing": self.sources_missing,
            "inserted": self.inserted,
            "updated": self.updated,
            "unchanged": self.unchanged,
            "removed": self.removed,
            "dedup_skipped": self.dedup_skipped,
            "age_filtered": self.age_filtered,
            "errors": self.errors[:20],
        }


class AggregationPipeline:
    def __init__(
        self,
        store: Optional[AggregationStore] = None,
        *,
        sources_path: Optional[Path] = None,
        max_concurrency: int = GLOBAL_CONCURRENCY,
    ) -> None:
        self.store = store or AggregationStore()
        self.sources_path = Path(sources_path) if sources_path else SOURCES_PATH
        self.max_concurrency = max_concurrency
        self._locks: Dict[str, asyncio.Lock] = {}
        self.dedup = DedupEngine()
        self.cycle = 0

    def seed_sources(self, path: Optional[Path] = None) -> int:
        p = Path(path) if path else self.sources_path
        raw = json.loads(p.read_text(encoding="utf-8"))
        count = 0
        for row in raw:
            rec = SourceRecord(
                company=row["company"],
                ats_type=row["ats_type"],
                board_identifier=row["board_identifier"],
                domain=row.get("domain"),
                active=bool(row.get("active", True)),
            )
            self.store.upsert_source(
                {
                    "source_id": rec.source_id,
                    "company": rec.company,
                    "ats_type": rec.ats_type,
                    "board_identifier": rec.board_identifier,
                    "domain": rec.domain,
                    "active": rec.active,
                }
            )
            count += 1
        return count

    def _lock_for(self, source_id: str) -> asyncio.Lock:
        if source_id not in self._locks:
            self._locks[source_id] = asyncio.Lock()
        return self._locks[source_id]

    @staticmethod
    def _too_old(job: NormalizedJob) -> bool:
        if not job.published_at:
            return False  # unknown age — keep; do not invent dates
        try:
            published = datetime.fromisoformat(str(job.published_at).replace("Z", "+00:00"))
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) - published > timedelta(days=AGE_FILTER_DAYS)
        except ValueError:
            # epoch millis?
            try:
                ms = int(float(str(job.published_at)))
                if ms > 10_000_000_000:
                    ms = ms // 1000
                published = datetime.fromtimestamp(ms, tz=timezone.utc)
                return datetime.now(timezone.utc) - published > timedelta(days=AGE_FILTER_DAYS)
            except (TypeError, ValueError, OSError):
                return False

    async def _fetch_one(self, row: Dict[str, Any], stats: IngestStats, sem: asyncio.Semaphore) -> None:
        source = SourceRecord(
            company=row["company"],
            ats_type=row["ats_type"],
            board_identifier=row["board_identifier"],
            domain=row.get("domain"),
            active=bool(row.get("active", True)),
            source_id=row["source_id"],
            consecutive_empty=int(row.get("consecutive_empty") or 0),
            backoff_until=row.get("backoff_until"),
        )
        adapter_cls = AdapterRegistry.get(source.ats_type)
        if not adapter_cls:
            stats.sources_failed += 1
            stats.errors.append(f"no adapter for {source.ats_type}")
            return

        async with sem:
            async with self._lock_for(source.source_id or ""):
                stats.sources_attempted += 1
                adapter = adapter_cls()
                result = await adapter.fetch_with_retry(source)

                if result.board_missing:
                    stats.sources_missing += 1
                    backoff = (
                        datetime.now(timezone.utc) + timedelta(hours=BOARD_404_BACKOFF_HOURS)
                    ).isoformat()
                    self.store.mark_source_checked(
                        source.source_id or "",
                        board_missing=True,
                        backoff_until=backoff,
                    )
                    return

                if result.error and not result.jobs:
                    stats.sources_failed += 1
                    stats.errors.append(f"{source.source_id}: {result.error}")
                    self.store.mark_source_checked(source.source_id or "", empty=True)
                    return

                stats.sources_ok += 1
                seen_keys: Set[str] = set()
                empty = True
                for job in result.jobs:
                    if self._too_old(job):
                        stats.age_filtered += 1
                        continue
                    empty = False
                    decision = self.dedup.check(job)
                    if decision.is_duplicate and decision.reason == "simhash":
                        # Same content different key — skip insert but track
                        stats.dedup_skipped += 1
                        seen_keys.add(decision.matched_key or job.ats_job_key)
                        continue
                    upsert = self.store.upsert_job(job)
                    self.dedup.remember(job)
                    seen_keys.add(upsert.job_key)
                    if upsert.status == "inserted":
                        stats.inserted += 1
                    elif upsert.status == "updated":
                        stats.updated += 1
                    else:
                        stats.unchanged += 1

                removed = self.store.deactivate_missing(source.source_id or "", seen_keys)
                stats.removed += removed
                self.store.mark_source_checked(source.source_id or "", empty=empty)

    async def run(self, *, limit_sources: Optional[int] = None) -> IngestStats:
        self.cycle += 1
        # Seed dedup from existing active jobs
        existing = self.store.list_active_jobs(limit=20000)
        self.dedup.seed_from_jobs(existing)

        sources = self.store.list_active_sources(cycle=self.cycle)
        if limit_sources is not None:
            sources = sources[:limit_sources]

        stats = IngestStats()
        sem = asyncio.Semaphore(self.max_concurrency)
        await asyncio.gather(*(self._fetch_one(s, stats, sem) for s in sources))
        return stats


def run_ingest_cycle(
    *,
    seed: bool = True,
    limit_sources: Optional[int] = None,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    store = AggregationStore(db_path=db_path) if db_path else AggregationStore()
    pipe = AggregationPipeline(store=store)
    seeded = pipe.seed_sources() if seed else 0
    stats = asyncio.run(pipe.run(limit_sources=limit_sources))
    return {
        "seeded_sources": seeded,
        "store_stats": store.stats(),
        "ingest": stats.to_dict(),
        "adapters": AdapterRegistry.known(),
        "finished_at": utc_now_iso(),
    }


def fetch_live_normalized(
    *,
    limit_sources: int = 30,
    db_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """
    Run a bounded ingest and return legacy vacancy dicts with honest NULLs.
    Replaces fabricated exp/salary/jd stamping in career_portals.
    """
    result = run_ingest_cycle(seed=True, limit_sources=limit_sources, db_path=db_path)
    store = AggregationStore(db_path=db_path) if db_path else AggregationStore()
    jobs = store.list_active_jobs(limit=2000)
    vacancies = [j.to_legacy_vacancy() for j in jobs]
    log.info("fetch_live_normalized: %s jobs (ingest=%s)", len(vacancies), result.get("ingest"))
    return vacancies
