"""captcha_events SQLite ledger + JSONL audit (§4.9 / §5.9)."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_DB = Path(__file__).resolve().parents[1] / "applied_jobs.db"
DEFAULT_JSONL = Path(__file__).resolve().parents[2] / "logs" / "captcha_audit.jsonl"

SCHEMA = """
CREATE TABLE IF NOT EXISTS captcha_events (
    id TEXT PRIMARY KEY,
    ts TEXT NOT NULL,
    board TEXT,
    company TEXT,
    page_url TEXT,
    captcha_type TEXT,
    resolved_by TEXT,
    resolution TEXT,
    duration_s REAL,
    cost_usd REAL NOT NULL DEFAULT 0,
    detail TEXT
);
CREATE INDEX IF NOT EXISTS idx_captcha_events_board_ts ON captcha_events(board, ts);

CREATE TABLE IF NOT EXISTS captcha_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    board TEXT NOT NULL,
    resolved_by TEXT,
    spend_usd REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    unresolved INTEGER NOT NULL DEFAULT 0
);
"""


class CaptchaEventsStore:
    def __init__(
        self,
        db_path: Optional[Path] = None,
        *,
        jsonl_path: Optional[Path] = None,
    ) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB
        self.jsonl_path = Path(jsonl_path) if jsonl_path else DEFAULT_JSONL
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.executescript(SCHEMA)

    def record(
        self,
        *,
        board: str,
        captcha_type: str,
        resolved_by: str,
        resolution: str,
        page_url: str = "",
        company: str = "",
        duration_s: float = 0.0,
        cost_usd: float = 0.0,
        detail: str = "",
        unresolved: bool = True,
    ) -> str:
        row_id = str(uuid.uuid4())
        ts = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                INSERT INTO captcha_events (
                    id, ts, board, company, page_url, captcha_type,
                    resolved_by, resolution, duration_s, cost_usd, detail
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    row_id,
                    ts,
                    board,
                    company,
                    page_url,
                    captcha_type,
                    resolved_by,
                    resolution,
                    duration_s,
                    cost_usd,
                    detail,
                ),
            )
            conn.execute(
                """
                INSERT INTO captcha_ledger (board, resolved_by, spend_usd, created_at, unresolved)
                VALUES (?, ?, ?, ?, ?)
                """,
                (board, resolved_by, cost_usd, ts, 1 if unresolved else 0),
            )
            conn.commit()
        payload: Dict[str, Any] = {
            "id": row_id,
            "ts": ts,
            "board": board,
            "company": company,
            "page_url": page_url,
            "type": captcha_type,
            "resolved_by": resolved_by,
            "resolution": resolution,
            "duration_s": duration_s,
            "cost": cost_usd,
            "detail": detail,
        }
        with self.jsonl_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return row_id

    def rate_by_board(self, *, hours: int = 24) -> Dict[str, Dict[str, float]]:
        from datetime import timedelta

        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        with sqlite3.connect(str(self.db_path)) as conn:
            rows = conn.execute(
                """
                SELECT board,
                       COUNT(*) AS total,
                       SUM(CASE WHEN resolution IN ('needs_human','circuit_open','vendor_denied') THEN 1 ELSE 0 END) AS unresolved
                FROM captcha_events
                WHERE ts >= ?
                GROUP BY board
                """,
                (cutoff,),
            ).fetchall()
        out: Dict[str, Dict[str, float]] = {}
        for board, total, unresolved in rows:
            t = float(total or 0)
            u = float(unresolved or 0)
            out[str(board or "unknown")] = {
                "total": t,
                "unresolved": u,
                "rate": (u / t) if t else 0.0,
            }
        return out
