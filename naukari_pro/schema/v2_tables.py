"""Postgres-ready SQLite schemas for profile, match_decisions, resumes (§5)."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

DEFAULT_DB = Path(__file__).resolve().parents[1] / "applied_jobs.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    facts_json TEXT NOT NULL,
    evidence_json TEXT NOT NULL DEFAULT '[]',
    compensation_floor_amount REAL,
    compensation_floor_currency TEXT DEFAULT 'INR',
    compensation_floor_period TEXT,
    notice_period TEXT,
    phone TEXT,
    role_families_json TEXT DEFAULT '[]',
    location_preferences_json TEXT DEFAULT '[]',
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS match_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    req_id TEXT NOT NULL,
    ats_job_key TEXT,
    deterministic_score REAL,
    llm_score REAL,
    rationale TEXT,
    flags_json TEXT DEFAULT '[]',
    decision TEXT NOT NULL,
    seen_set_pointer TEXT,
    decision_history_json TEXT DEFAULT '[]',
    created_at TEXT NOT NULL,
    UNIQUE(req_id)
);

CREATE TABLE IF NOT EXISTS resumes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resume_key TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL,
    job_key TEXT,
    content_json TEXT NOT NULL,
    grounding_json TEXT,
    ats_score_json TEXT,
    render_check_json TEXT,
    diff_json TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_match_decisions_decision ON match_decisions(decision);
CREATE INDEX IF NOT EXISTS idx_resumes_job ON resumes(job_key);
"""


def ensure_v2_tables(db_path: Optional[Path] = None) -> Path:
    path = Path(db_path) if db_path else DEFAULT_DB
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(path)) as conn:
        conn.executescript(SCHEMA)
        # Jobs constraint-level dedupe if jobs table exists without it
        try:
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_source_external
                ON jobs(source_id, external_job_id)
                """
            )
        except sqlite3.OperationalError:
            pass
        conn.commit()
    return path
