"""
Hard duplicate / cooldown rules (please-hire-me + job-application-agent).

Exit code 2 = blocked / hard skip (unknown-required or policy block).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

DEFAULT_COOLDOWN_DAYS = 15
DEFAULT_MAX_PER_COMPANY_LIFETIME = 2
EXIT_HARD_SKIP = 2


@dataclass
class DedupeDecision:
    allow: bool
    reason: str
    exit_code: int = 0

    def to_dict(self):
        return {"allow": self.allow, "reason": self.reason, "exit_code": self.exit_code}


class CompanyDedupeLedger:
    def __init__(
        self,
        db_path: Optional[Path] = None,
        *,
        cooldown_days: int = DEFAULT_COOLDOWN_DAYS,
        max_lifetime: int = DEFAULT_MAX_PER_COMPANY_LIFETIME,
    ) -> None:
        root = Path(__file__).resolve().parents[1]
        self.db_path = Path(db_path) if db_path else root / "applied_jobs.db"
        self.cooldown_days = cooldown_days
        self.max_lifetime = max_lifetime
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS company_apply_ledger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_key TEXT NOT NULL,
                    employer_job_id TEXT,
                    applied_at TEXT NOT NULL,
                    job_url TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_company_ledger_key
                    ON company_apply_ledger(company_key);
                """
            )

    @staticmethod
    def company_key(company: str) -> str:
        return "".join(c for c in (company or "").lower() if c.isalnum())

    def record(self, company: str, *, employer_job_id: str = "", job_url: str = "") -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO company_apply_ledger (company_key, employer_job_id, applied_at, job_url)
                VALUES (?, ?, ?, ?)
                """,
                (self.company_key(company), employer_job_id or None, now, job_url or None),
            )
            conn.commit()

    def check(
        self,
        company: str,
        *,
        employer_job_id: str = "",
        interview_tracker_companies: Optional[set] = None,
    ) -> DedupeDecision:
        key = self.company_key(company)
        if not key:
            return DedupeDecision(False, "missing_company", EXIT_HARD_SKIP)
        track = {self.company_key(c) for c in (interview_tracker_companies or set())}
        if key in track:
            return DedupeDecision(False, "interview_tracker_hard_skip", EXIT_HARD_SKIP)

        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM company_apply_ledger WHERE company_key=? ORDER BY applied_at DESC",
                (key,),
            ).fetchall()

        if employer_job_id:
            for r in rows:
                if (r["employer_job_id"] or "") == employer_job_id:
                    return DedupeDecision(False, "employer_job_id_duplicate", EXIT_HARD_SKIP)

        if len(rows) >= self.max_lifetime:
            return DedupeDecision(
                False,
                f"max_applications_per_company_lifetime:{self.max_lifetime}",
                EXIT_HARD_SKIP,
            )

        now = datetime.now(timezone.utc)
        if rows:
            try:
                last = datetime.fromisoformat(str(rows[0]["applied_at"]).replace("Z", "+00:00"))
            except ValueError:
                last = now
            # same-day freeze
            if last.date() == now.date():
                return DedupeDecision(False, "same_day_company_freeze", EXIT_HARD_SKIP)
            if now - last < timedelta(days=self.cooldown_days):
                return DedupeDecision(
                    False,
                    f"company_cooldown_{self.cooldown_days}d",
                    EXIT_HARD_SKIP,
                )

        return DedupeDecision(True, "ok", 0)
