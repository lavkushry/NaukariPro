"""SQLite cost ledger table `ai_calls` (Postgres-ready schema)."""

from __future__ import annotations

import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_DB = Path(__file__).resolve().parents[1] / "applied_jobs.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS ai_calls (
    id TEXT PRIMARY KEY,
    ts TEXT NOT NULL,
    task TEXT,
    prompt_id TEXT,
    prompt_version TEXT,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    tokens_in INTEGER NOT NULL DEFAULT 0,
    tokens_out INTEGER NOT NULL DEFAULT 0,
    cost_usd REAL NOT NULL DEFAULT 0,
    latency_ms INTEGER NOT NULL DEFAULT 0,
    request_id TEXT,
    input_hash TEXT,
    status TEXT NOT NULL,
    cached INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_ai_calls_ts ON ai_calls(ts);
CREATE INDEX IF NOT EXISTS idx_ai_calls_task ON ai_calls(task);
"""


class AICallsStore:
    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _init(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)

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

    def record(
        self,
        *,
        ts: str,
        task: Optional[str],
        prompt_id: Optional[str],
        prompt_version: Optional[str],
        provider: str,
        model: str,
        tokens_in: int,
        tokens_out: int,
        cost_usd: float,
        latency_ms: int = 0,
        request_id: Optional[str] = None,
        input_hash: Optional[str] = None,
        status: str = "ok",
        cached: bool = False,
    ) -> str:
        row_id = str(uuid.uuid4())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO ai_calls (
                    id, ts, task, prompt_id, prompt_version, provider, model,
                    tokens_in, tokens_out, cost_usd, latency_ms, request_id,
                    input_hash, status, cached
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row_id,
                    ts,
                    task,
                    prompt_id,
                    prompt_version,
                    provider,
                    model,
                    int(tokens_in),
                    int(tokens_out),
                    float(cost_usd),
                    int(latency_ms),
                    request_id or row_id,
                    input_hash,
                    status,
                    1 if cached else 0,
                ),
            )
        return row_id

    def day_spend(self, day_prefix: str) -> float:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(cost_usd), 0) AS s FROM ai_calls WHERE ts LIKE ?",
                (f"{day_prefix}%",),
            ).fetchone()
        return float(row["s"] if row else 0.0)

    def summary(self) -> Dict[str, Any]:
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) AS c FROM ai_calls").fetchone()["c"]
            spend = conn.execute(
                "SELECT COALESCE(SUM(cost_usd), 0) AS s FROM ai_calls WHERE cached = 0"
            ).fetchone()["s"]
        return {"rows": int(total), "lifetime_spend_usd": float(spend), "db": str(self.db_path)}
