"""Aggregation pipeline: seed sources → fetch with locks → upsert → dedup → age filter."""

from __future__ import annotations

import asyncio
import logging
import secrets
import time
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
BOARD_JITTER_S = (2.0, 5.0)


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
    empty_success_rejected: int = 0
    errors: List[str] = field(default_factory=list)
    cycle_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
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
            "empty_success_rejected": self.empty_success_rejected,
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
        import json

        p = Path(path) if path else self.sources_path
        raw = json.loads(p.read_text(encoding="utf-8"))
        seen_ids = set()
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
            seen_ids.add(rec.source_id)
        return len(seen_ids)

    def _lock_for(self, source_id: str) -> asyncio.Lock:
        if source_id not in self._locks:
            self._locks[source_id] = asyncio.Lock()
        return self._locks[source_id]

    @staticmethod
    def _too_old(job: NormalizedJob) -> bool:
        if not job.published_at:
            return False
        try:
            published = datetime.fromisoformat(str(job.published_at).replace("Z", "+00:00"))
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) - published > timedelta(days=AGE_FILTER_DAYS)
        except ValueError:
            try:
                ms = int(float(str(job.published_at)))
                if ms > 10_000_000_000:
                    ms = ms // 1000
                published = datetime.fromtimestamp(ms, tz=timezone.utc)
                return datetime.now(timezone.utc) - published > timedelta(days=AGE_FILTER_DAYS)
            except (TypeError, ValueError, OSError):
                return False

    async def _fetch_one(self, row: Dict[str, Any], stats: IngestStats, sem: asyncio.Semaphore) -> None:
        import random

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
        sid = source.source_id or ""
        adapter_cls = AdapterRegistry.get(source.ats_type)
        if not adapter_cls:
            stats.sources_failed += 1
            stats.errors.append(f"no adapter for {source.ats_type}")
            self.store.record_drop(reason="no_adapter", source_id=sid, detail=source.ats_type)
            self.store.bump_board_health(sid, ats_type=source.ats_type, fetch_attempts=1, fetch_err=1)
            return

        async with sem:
            async with self._lock_for(sid):
                # Jitter between boards (JSON boards are generous but not unlimited)
                await asyncio.sleep(random.uniform(*BOARD_JITTER_S))
                stats.sources_attempted += 1
                adapter = adapter_cls()
                result = await adapter.fetch_with_retry(source)
                code = result.status_code or 0
                http_4xx = 1 if 400 <= code < 500 else 0
                http_5xx = 1 if code >= 500 else 0
                timeout = 1 if result.error and "timeout" in (result.error or "").lower() else 0

                if result.board_missing:
                    stats.sources_missing += 1
                    backoff = (
                        datetime.now(timezone.utc) + timedelta(hours=BOARD_404_BACKOFF_HOURS)
                    ).isoformat()
                    self.store.mark_source_checked(sid, board_missing=True, backoff_until=backoff)
                    self.store.record_drop(reason="board_missing", source_id=sid, detail=result.error)
                    self.store.bump_board_health(
                        sid, ats_type=source.ats_type, fetch_attempts=1, fetch_err=1, http_4xx=1
                    )
                    return

                if result.error and not result.jobs:
                    stats.sources_failed += 1
                    stats.errors.append(f"{sid}: {result.error}")
                    self.store.mark_source_checked(sid, empty=True)
                    self.store.record_drop(reason="fetch_error", source_id=sid, detail=result.error)
                    self.store.bump_board_health(
                        sid,
                        ats_type=source.ats_type,
                        fetch_attempts=1,
                        fetch_err=1,
                        http_4xx=http_4xx,
                        http_5xx=http_5xx,
                        timeouts=timeout,
                    )
                    return

                # Fail-closed: HTTP 200 with zero jobs is NOT a healthy fetch for JSON boards
                # (wrong slug / jobs:null already mapped to board_missing by adapters).
                if not result.jobs:
                    stats.empty_success_rejected += 1
                    stats.sources_failed += 1
                    stats.errors.append(f"{sid}: empty_board_no_jobs")
                    self.store.mark_source_checked(sid, empty=True)
                    self.store.record_drop(
                        reason="empty_board",
                        source_id=sid,
                        detail="HTTP success but 0 jobs — not counted as fetch_ok",
                    )
                    self.store.bump_board_health(
                        sid, ats_type=source.ats_type, fetch_attempts=1, fetch_err=1, http_4xx=http_4xx
                    )
                    return

                stats.sources_ok += 1
                seen_keys: Set[str] = set()
                jobs_new = 0
                dedupe_hits = 0
                jobs_seen = 0
                for job in result.jobs:
                    jobs_seen += 1
                    if self._too_old(job):
                        stats.age_filtered += 1
                        self.store.record_drop(
                            reason="age_filtered",
                            source_id=sid,
                            ats_job_key=job.ats_job_key,
                            detail=str(job.published_at),
                        )
                        continue
                    decision = self.dedup.check(job)
                    if decision.is_duplicate and decision.reason == "simhash":
                        stats.dedup_skipped += 1
                        dedupe_hits += 1
                        seen_keys.add(decision.matched_key or job.ats_job_key)
                        self.store.record_drop(
                            reason="dedupe_simhash",
                            source_id=sid,
                            ats_job_key=job.ats_job_key,
                            detail=decision.matched_key,
                        )
                        continue
                    upsert = self.store.upsert_job(job)
                    self.dedup.remember(job)
                    seen_keys.add(upsert.job_key)
                    if upsert.status == "inserted":
                        stats.inserted += 1
                        jobs_new += 1
                    elif upsert.status == "updated":
                        stats.updated += 1
                    else:
                        stats.unchanged += 1

                removed = self.store.deactivate_missing(sid, seen_keys)
                stats.removed += removed
                self.store.mark_source_checked(sid, empty=False)
                self.store.bump_board_health(
                    sid,
                    ats_type=source.ats_type,
                    fetch_attempts=1,
                    fetch_ok=1,
                    jobs_seen=jobs_seen,
                    jobs_new=jobs_new,
                    dedupe_hits=dedupe_hits,
                )

    async def run(self, *, limit_sources: Optional[int] = None) -> IngestStats:
        self.cycle += 1
        cycle_id = f"cycle-{utc_now_iso()}-{secrets.token_hex(3)}"
        self.store.record_cycle(cycle_id, "cycle_started", {"cycle": self.cycle})
        existing = self.store.list_active_jobs(limit=20000)
        self.dedup.seed_from_jobs(existing)

        sources = self.store.list_active_sources(cycle=self.cycle)
        if limit_sources is not None:
            sources = sources[:limit_sources]

        stats = IngestStats(cycle_id=cycle_id)
        sem = asyncio.Semaphore(self.max_concurrency)
        await asyncio.gather(*(self._fetch_one(s, stats, sem) for s in sources))
        self.store.record_cycle(
            cycle_id,
            "cycle_done",
            {
                "jobs_seen": stats.inserted + stats.updated + stats.unchanged + stats.dedup_skipped,
                "jobs_new": stats.inserted,
                "dedupe_hits": stats.dedup_skipped,
                **{k: v for k, v in stats.to_dict().items() if k != "errors"},
            },
        )
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
    # Prefer curated verified boards (boards.csv) so limited cycles hit HEALTHY fleets first
    boards_imported = 0
    if seed:
        try:
            from naukari_pro.aggregation.boards_registry import import_boards_csv

            boards_imported = import_boards_csv(store=store)
        except Exception as exc:  # noqa: BLE001
            log.warning("boards.csv import skipped: %s", exc)
    stats = asyncio.run(pipe.run(limit_sources=limit_sources))
    return {
        "seeded_sources": seeded,
        "boards_imported": boards_imported,
        "store_stats": store.stats(),
        "ingest": stats.to_dict(),
        "adapters": AdapterRegistry.known(),
        "healthy_boards": store.healthy_boards(),
        "verified_boards_total": store.verified_boards_total(),
        "finished_at": utc_now_iso(),
    }


def fetch_live_normalized(
    *,
    limit_sources: int = 30,
    db_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """
    Run a bounded ingest and return legacy vacancy dicts with honest NULLs.
    Preferred over career_portals.fetch_live_ats_vacancies for apply feeds.
    """
    result = run_ingest_cycle(seed=True, limit_sources=limit_sources, db_path=db_path)
    store = AggregationStore(db_path=db_path) if db_path else AggregationStore()
    jobs = store.list_active_jobs(limit=2000)
    vacancies = [j.to_legacy_vacancy() for j in jobs]
    log.info("fetch_live_normalized: %s jobs (ingest=%s)", len(vacancies), result.get("ingest"))
    return vacancies
