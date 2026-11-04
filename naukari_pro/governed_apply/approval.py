"""Approval batches: max 25 items, 24h expiry, per-item token. HITL by default."""

from __future__ import annotations

import secrets
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_DB = Path(__file__).resolve().parents[1] / "governed_apply.db"
BATCH_MAX = 25
BATCH_TTL_HOURS = 24


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ApprovalItem:
    item_id: str
    token: str
    job_url: str
    company: str
    title: str
    fit_score: float
    coverage_pct: float
    status: str  # pending | approved | rejected | expired
    expires_at: str


class ApprovalQueue:
    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS approval_items (
                    item_id TEXT PRIMARY KEY,
                    token TEXT NOT NULL UNIQUE,
                    job_url TEXT NOT NULL,
                    company TEXT,
                    title TEXT,
                    fit_score REAL,
                    coverage_pct REAL,
                    status TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    decided_at TEXT
                );
                CREATE TABLE IF NOT EXISTS quarantine (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL,
                    sensitivity TEXT NOT NULL,
                    job_url TEXT,
                    created_at TEXT NOT NULL,
                    resolved_value TEXT,
                    resolved_at TEXT
                );
                CREATE TABLE IF NOT EXISTS field_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_url TEXT NOT NULL,
                    field_id TEXT NOT NULL,
                    label TEXT,
                    sensitivity TEXT,
                    action TEXT,
                    value_masked TEXT,
                    dry_run INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_url TEXT NOT NULL,
                    company TEXT,
                    title TEXT,
                    confirmation_text TEXT,
                    confirmation_url TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    def enqueue_batch(self, jobs: List[Dict[str, Any]]) -> List[ApprovalItem]:
        jobs = jobs[:BATCH_MAX]
        expires = (_utc_now() + timedelta(hours=BATCH_TTL_HOURS)).isoformat()
        now = _utc_now().isoformat()
        items: List[ApprovalItem] = []
        with self._connect() as conn:
            for j in jobs:
                item_id = secrets.token_hex(8)
                token = secrets.token_urlsafe(16)
                conn.execute(
                    """
                    INSERT INTO approval_items (
                        item_id, token, job_url, company, title, fit_score,
                        coverage_pct, status, expires_at, created_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        item_id, token, j.get("url") or "",
                        j.get("company"), j.get("title"),
                        float(j.get("fit_score") or 0),
                        float(j.get("coverage_pct") or 0),
                        "pending", expires, now,
                    ),
                )
                items.append(
                    ApprovalItem(
                        item_id=item_id,
                        token=token,
                        job_url=j.get("url") or "",
                        company=j.get("company") or "",
                        title=j.get("title") or "",
                        fit_score=float(j.get("fit_score") or 0),
                        coverage_pct=float(j.get("coverage_pct") or 0),
                        status="pending",
                        expires_at=expires,
                    )
                )
        return items

    def decide(self, token: str, *, approve: bool) -> bool:
        self.expire_stale()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM approval_items WHERE token=?", (token,)
            ).fetchone()
            if not row or row["status"] != "pending":
                return False
            conn.execute(
                "UPDATE approval_items SET status=?, decided_at=? WHERE token=?",
                ("approved" if approve else "rejected", _utc_now().isoformat(), token),
            )
            return True

    def expire_stale(self) -> int:
        now = _utc_now().isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                """
                UPDATE approval_items SET status='expired'
                WHERE status='pending' AND expires_at < ?
                """,
                (now,),
            )
            return cur.rowcount

    def pending(self) -> List[Dict[str, Any]]:
        self.expire_stale()
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM approval_items WHERE status='pending' ORDER BY created_at"
            ).fetchall()
        return [dict(r) for r in rows]

    def quarantine_ask(self, question: str, sensitivity: str, job_url: str = "") -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO quarantine (question, sensitivity, job_url, created_at)
                VALUES (?,?,?,?)
                """,
                (question, sensitivity, job_url, _utc_now().isoformat()),
            )
            return int(cur.lastrowid)

    def audit_field(
        self,
        *,
        job_url: str,
        field_id: str,
        label: str,
        sensitivity: str,
        action: str,
        value_masked: str,
        dry_run: bool,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO field_audit (
                    job_url, field_id, label, sensitivity, action,
                    value_masked, dry_run, created_at
                ) VALUES (?,?,?,?,?,?,?,?)
                """,
                (
                    job_url, field_id, label, sensitivity, action,
                    value_masked, 1 if dry_run else 0, _utc_now().isoformat(),
                ),
            )

    def record_confirmed_submit(
        self,
        *,
        job_url: str,
        company: str,
        title: str,
        confirmation_text: Optional[str],
        confirmation_url: Optional[str],
    ) -> int:
        """filled != applied: only call after visible ATS confirmation."""
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO submissions (
                    job_url, company, title, confirmation_text,
                    confirmation_url, status, created_at
                ) VALUES (?,?,?,?,?,?,?)
                """,
                (
                    job_url, company, title, confirmation_text,
                    confirmation_url, "applied", _utc_now().isoformat(),
                ),
            )
            return int(cur.lastrowid)

    def field_audit_rows(self, job_url: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            if job_url:
                rows = conn.execute(
                    "SELECT * FROM field_audit WHERE job_url=? ORDER BY id", (job_url,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM field_audit ORDER BY id").fetchall()
        return [dict(r) for r in rows]

    def submission_count(self) -> int:
        with self._connect() as conn:
            return int(conn.execute("SELECT COUNT(*) c FROM submissions").fetchone()["c"])
