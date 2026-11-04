"""SQLite tracking store — funnel + interview rounds UNIQUE(application_id, round)."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from naukari_pro.tracking.models import ApplicationStatus

DEFAULT_DB = Path(__file__).resolve().parents[1] / "tracking.db"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class TrackingStore:
    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_url TEXT NOT NULL,
                    company TEXT,
                    title TEXT,
                    ats TEXT,
                    fit_score REAL,
                    status TEXT NOT NULL,
                    first_saved_at TEXT NOT NULL,
                    applied_at TEXT,
                    outcome_at TEXT,
                    rejection_hours REAL,
                    UNIQUE(job_url)
                );
                CREATE TABLE IF NOT EXISTS interview_rounds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    application_id INTEGER NOT NULL,
                    round INTEGER NOT NULL,
                    round_type TEXT NOT NULL,
                    scheduled_at TEXT,
                    notes TEXT,
                    UNIQUE(application_id, round),
                    FOREIGN KEY(application_id) REFERENCES applications(id)
                );
                CREATE INDEX IF NOT EXISTS idx_app_status ON applications(status);
                CREATE INDEX IF NOT EXISTS idx_app_ats ON applications(ats);
                """
            )

    def upsert_application(self, job: Dict[str, Any], *, status: str = ApplicationStatus.SAVED.value) -> int:
        now = _now()
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT id, status FROM applications WHERE job_url=?",
                (job.get("url") or "",),
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE applications SET company=?, title=?, ats=?, fit_score=?,
                        status=CASE WHEN ?='applied' AND status='saved' THEN 'applied' ELSE status END,
                        applied_at=CASE WHEN ?='applied' AND applied_at IS NULL THEN ? ELSE applied_at END
                    WHERE id=?
                    """,
                    (
                        job.get("company"), job.get("title"), job.get("ats"),
                        job.get("fit_score"), status, status, now, existing["id"],
                    ),
                )
                return int(existing["id"])
            cur = conn.execute(
                """
                INSERT INTO applications (
                    job_url, company, title, ats, fit_score, status, first_saved_at, applied_at
                ) VALUES (?,?,?,?,?,?,?,?)
                """,
                (
                    job.get("url") or "", job.get("company"), job.get("title"),
                    job.get("ats"), job.get("fit_score"), status, now,
                    now if status == ApplicationStatus.APPLIED.value else None,
                ),
            )
            return int(cur.lastrowid)

    def set_status(self, application_id: int, status: str, *, rejection_hours: Optional[float] = None) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE applications SET status=?, outcome_at=?, rejection_hours=COALESCE(?, rejection_hours)
                WHERE id=?
                """,
                (status, _now(), rejection_hours, application_id),
            )

    def add_interview_round(
        self,
        application_id: int,
        round_no: int,
        round_type: str,
        *,
        scheduled_at: Optional[str] = None,
        notes: str = "",
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO interview_rounds (application_id, round, round_type, scheduled_at, notes)
                VALUES (?,?,?,?,?)
                ON CONFLICT(application_id, round) DO UPDATE SET
                    round_type=excluded.round_type,
                    scheduled_at=excluded.scheduled_at,
                    notes=excluded.notes
                """,
                (application_id, round_no, round_type, scheduled_at, notes),
            )

    def funnel_counts(self) -> Dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) c FROM applications GROUP BY status"
            ).fetchall()
        out = {s.value: 0 for s in ApplicationStatus}
        for r in rows:
            out[r["status"]] = int(r["c"])
        return out

    def feed(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM applications
                ORDER BY COALESCE(fit_score, 0) DESC, first_saved_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def rejection_histogram(self) -> Dict[str, int]:
        """Buckets: <24h ATS filter, 1-3d recruiter, 4-14d HM, >14d ghosted."""
        buckets = {"lt_24h": 0, "d1_3": 0, "d4_14": 0, "gt_14d": 0}
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT rejection_hours FROM applications
                WHERE status='rejected' AND rejection_hours IS NOT NULL
                """
            ).fetchall()
        for r in rows:
            h = float(r["rejection_hours"])
            if h < 24:
                buckets["lt_24h"] += 1
            elif h < 72:
                buckets["d1_3"] += 1
            elif h < 336:
                buckets["d4_14"] += 1
            else:
                buckets["gt_14d"] += 1
        return buckets

    def rejection_rate_by_ats(self) -> Dict[str, float]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT ats,
                       SUM(CASE WHEN status='rejected' THEN 1 ELSE 0 END) AS rej,
                       COUNT(*) AS total
                FROM applications
                WHERE ats IS NOT NULL AND ats != ''
                GROUP BY ats
                """
            ).fetchall()
        return {
            (r["ats"] or "unknown"): (float(r["rej"]) / float(r["total"]) if r["total"] else 0.0)
            for r in rows
        }
