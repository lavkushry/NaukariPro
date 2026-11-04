"""SQLite storage for sources, normalized jobs, snapshots, and diff events."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from naukari_pro.aggregation.models import NormalizedJob, content_hash_text, utc_now_iso

DEFAULT_DB = Path(__file__).resolve().parents[1] / "aggregation.db"


SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    company TEXT NOT NULL,
    ats_type TEXT NOT NULL,
    board_identifier TEXT NOT NULL,
    domain TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    last_checked_at TEXT,
    consecutive_empty INTEGER NOT NULL DEFAULT 0,
    backoff_until TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    ats_job_key TEXT PRIMARY KEY,
    external_job_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    company TEXT NOT NULL,
    title TEXT NOT NULL,
    location TEXT,
    remote INTEGER,
    url TEXT NOT NULL,
    description_full TEXT,
    departments_json TEXT,
    employment_type TEXT,
    published_at TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    ats_type TEXT,
    salary TEXT,
    experience_required TEXT,
    raw_metadata_json TEXT,
    UNIQUE(url)
);

CREATE TABLE IF NOT EXISTS job_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ats_job_key TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    description_full TEXT,
    captured_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS job_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ats_job_key TEXT NOT NULL,
    event_type TEXT NOT NULL,
    detail TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source_id);
CREATE INDEX IF NOT EXISTS idx_jobs_active ON jobs(is_active);
CREATE INDEX IF NOT EXISTS idx_jobs_hash ON jobs(content_hash);
CREATE INDEX IF NOT EXISTS idx_snapshots_key ON job_snapshots(ats_job_key);
"""


@dataclass
class UpsertResult:
    status: str  # inserted | updated | unchanged
    job_key: str


class AggregationStore:
    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            with conn:
                yield conn
        finally:
            conn.close()

    def _init(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    def upsert_source(self, source: Any) -> None:
        now = utc_now_iso()
        if hasattr(source, "__dataclass_fields__") or not isinstance(source, dict):
            src_dict = {
                "source_id": getattr(source, "source_id", f"{getattr(source, 'ats_type')}:{getattr(source, 'board_identifier')}"),
                "company": getattr(source, "company", "Unknown"),
                "ats_type": getattr(source, "ats_type", "unknown"),
                "board_identifier": getattr(source, "board_identifier", ""),
                "domain": getattr(source, "domain", None),
                "active": getattr(source, "active", True),
                "last_checked_at": getattr(source, "last_checked_at", None),
                "consecutive_empty": getattr(source, "consecutive_empty", 0),
                "backoff_until": getattr(source, "backoff_until", None),
            }
        else:
            src_dict = source

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sources (
                    source_id, company, ats_type, board_identifier, domain,
                    active, last_checked_at, consecutive_empty, backoff_until, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id) DO UPDATE SET
                    company=excluded.company,
                    ats_type=excluded.ats_type,
                    board_identifier=excluded.board_identifier,
                    domain=excluded.domain,
                    active=excluded.active
                """,
                (
                    src_dict["source_id"],
                    src_dict["company"],
                    src_dict["ats_type"],
                    src_dict["board_identifier"],
                    src_dict.get("domain"),
                    1 if src_dict.get("active", True) else 0,
                    src_dict.get("last_checked_at"),
                    int(src_dict.get("consecutive_empty") or 0),
                    src_dict.get("backoff_until"),
                    now,
                ),
            )

    def list_sources(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM sources ORDER BY company").fetchall()
        return [dict(r) for r in rows]

    def list_active_sources(self, *, include_quiet_every_n: int = 3, cycle: int = 0) -> List[Dict[str, Any]]:
        now = utc_now_iso()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM sources
                WHERE active=1
                  AND (backoff_until IS NULL OR backoff_until <= ?)
                ORDER BY company
                """,
                (now,),
            ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            # Quiet boards (3+ empty cycles) polled every Nth cycle
            if int(d.get("consecutive_empty") or 0) >= 3 and (cycle % include_quiet_every_n) != 0:
                continue
            out.append(d)
        return out

    def mark_source_checked(
        self,
        source_id: str,
        *,
        empty: bool = False,
        board_missing: bool = False,
        backoff_until: Optional[str] = None,
    ) -> None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT consecutive_empty FROM sources WHERE source_id=?",
                (source_id,),
            ).fetchone()
            empty_n = int(row["consecutive_empty"] if row else 0)
            empty_n = empty_n + 1 if empty else 0
            active = 0 if board_missing else 1
            conn.execute(
                """
                UPDATE sources SET last_checked_at=?, consecutive_empty=?,
                    backoff_until=?, active=CASE WHEN ?=1 THEN 0 ELSE active END
                WHERE source_id=?
                """,
                (utc_now_iso(), empty_n, backoff_until, 1 if board_missing else 0, source_id),
            )
            if board_missing:
                conn.execute(
                    "UPDATE sources SET active=0 WHERE source_id=?",
                    (source_id,),
                )

    def upsert_job(self, job: NormalizedJob) -> UpsertResult:
        key = job.ats_job_key
        now = utc_now_iso()
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT * FROM jobs WHERE ats_job_key=?", (key,)
            ).fetchone()
            if existing is None:
                # Also check URL collision
                by_url = conn.execute(
                    "SELECT * FROM jobs WHERE url=?", (job.url,)
                ).fetchone()
                if by_url is not None:
                    existing = by_url
                    key = by_url["ats_job_key"]

            if existing is None:
                conn.execute(
                    """
                    INSERT INTO jobs (
                        ats_job_key, external_job_id, source_id, company, title,
                        location, remote, url, description_full, departments_json,
                        employment_type, published_at, first_seen_at, last_seen_at,
                        content_hash, is_active, ats_type, salary, experience_required,
                        raw_metadata_json
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        key, job.external_job_id, job.source_id, job.company, job.title,
                        job.location,
                        None if job.remote is None else (1 if job.remote else 0),
                        job.url, job.description_full,
                        json.dumps(job.departments or []),
                        job.employment_type, job.published_at,
                        job.first_seen_at or now, now,
                        job.content_hash or content_hash_text(job.title, job.description_full),
                        1 if job.is_active else 0,
                        job.ats_type, job.salary, job.experience_required,
                        json.dumps(job.raw_metadata or {}),
                    ),
                )
                self._snapshot(conn, key, job)
                self._event(conn, key, "NEW", None)
                return UpsertResult("inserted", key)

            old_hash = existing["content_hash"]
            first_seen = existing["first_seen_at"]  # immutable
            new_hash = job.content_hash or content_hash_text(job.title, job.description_full)
            if old_hash == new_hash and existing["is_active"]:
                conn.execute(
                    "UPDATE jobs SET last_seen_at=?, is_active=1 WHERE ats_job_key=?",
                    (now, existing["ats_job_key"]),
                )
                return UpsertResult("unchanged", existing["ats_job_key"])

            conn.execute(
                """
                UPDATE jobs SET
                    title=?, location=?, remote=?, url=?, description_full=?,
                    departments_json=?, employment_type=?, published_at=?,
                    last_seen_at=?, content_hash=?, is_active=1,
                    salary=?, experience_required=?, raw_metadata_json=?,
                    first_seen_at=?
                WHERE ats_job_key=?
                """,
                (
                    job.title, job.location,
                    None if job.remote is None else (1 if job.remote else 0),
                    job.url, job.description_full,
                    json.dumps(job.departments or []),
                    job.employment_type, job.published_at,
                    now, new_hash,
                    job.salary, job.experience_required,
                    json.dumps(job.raw_metadata or {}),
                    first_seen,  # keep immutable
                    existing["ats_job_key"],
                ),
            )
            self._snapshot(conn, existing["ats_job_key"], job)
            self._trim_snapshots(conn, existing["ats_job_key"], keep=2)
            self._event(conn, existing["ats_job_key"], "UPDATED", f"{old_hash}->{new_hash}")
            return UpsertResult("updated", existing["ats_job_key"])

    def deactivate_missing(self, source_id: str, seen_keys: Iterable[str]) -> int:
        seen = set(seen_keys)
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT ats_job_key FROM jobs WHERE source_id=? AND is_active=1",
                (source_id,),
            ).fetchall()
            removed = 0
            now = utc_now_iso()
            for r in rows:
                if r["ats_job_key"] not in seen:
                    conn.execute(
                        "UPDATE jobs SET is_active=0, last_seen_at=? WHERE ats_job_key=?",
                        (now, r["ats_job_key"]),
                    )
                    self._event(conn, r["ats_job_key"], "REMOVED", "not in latest fetch")
                    removed += 1
            return removed

    def deactivate_job(self, ats_job_key: str, reason: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE jobs SET is_active=0, last_seen_at=? WHERE ats_job_key=?",
                (utc_now_iso(), ats_job_key),
            )
            self._event(conn, ats_job_key, "REMOVED", reason)

    def list_active_jobs(self, limit: int = 5000) -> List[NormalizedJob]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE is_active=1 ORDER BY last_seen_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_job(r) for r in rows]

    def get_job(self, ats_job_key: str) -> Optional[NormalizedJob]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM jobs WHERE ats_job_key=?",
                (ats_job_key,),
            ).fetchone()
            if row is None:
                row = conn.execute(
                    "SELECT * FROM jobs WHERE external_job_id=?",
                    (ats_job_key,),
                ).fetchone()
        return self._row_to_job(row) if row else None

    def stats(self) -> Dict[str, int]:
        with self._connect() as conn:
            active = conn.execute("SELECT COUNT(*) c FROM jobs WHERE is_active=1").fetchone()["c"]
            sources = conn.execute("SELECT COUNT(*) c FROM sources WHERE active=1").fetchone()["c"]
            events = conn.execute("SELECT COUNT(*) c FROM job_events").fetchone()["c"]
        return {"active_jobs": active, "active_sources": sources, "events": events}

    def _snapshot(self, conn: sqlite3.Connection, key: str, job: NormalizedJob) -> None:
        conn.execute(
            """
            INSERT INTO job_snapshots (ats_job_key, content_hash, description_full, captured_at)
            VALUES (?, ?, ?, ?)
            """,
            (key, job.content_hash, job.description_full, utc_now_iso()),
        )

    def _trim_snapshots(self, conn: sqlite3.Connection, key: str, keep: int = 2) -> None:
        rows = conn.execute(
            """
            SELECT id FROM job_snapshots WHERE ats_job_key=?
            ORDER BY captured_at DESC
            """,
            (key,),
        ).fetchall()
        for r in rows[keep:]:
            conn.execute("DELETE FROM job_snapshots WHERE id=?", (r["id"],))

    def _event(self, conn: sqlite3.Connection, key: str, event_type: str, detail: Optional[str]) -> None:
        conn.execute(
            "INSERT INTO job_events (ats_job_key, event_type, detail, created_at) VALUES (?,?,?,?)",
            (key, event_type, detail, utc_now_iso()),
        )

    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> NormalizedJob:
        deps = json.loads(row["departments_json"] or "[]")
        remote = row["remote"]
        return NormalizedJob(
            external_job_id=row["external_job_id"],
            source_id=row["source_id"],
            company=row["company"],
            title=row["title"],
            url=row["url"],
            location=row["location"],
            remote=None if remote is None else bool(remote),
            description_full=row["description_full"],
            departments=deps,
            employment_type=row["employment_type"],
            published_at=row["published_at"],
            first_seen_at=row["first_seen_at"],
            last_seen_at=row["last_seen_at"],
            content_hash=row["content_hash"],
            is_active=bool(row["is_active"]),
            ats_type=row["ats_type"],
            salary=row["salary"],
            experience_required=row["experience_required"],
            raw_metadata=json.loads(row["raw_metadata_json"] or "{}"),
        )
