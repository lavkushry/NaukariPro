"""
Shared fixtures for the NP scenario suite.

- Session socket-block: any accidental network fails loudly with the test ID.
- frozen_clock / seeded_rng / tmp_sqlite_wal for determinism.
"""

from __future__ import annotations

import os
import random
import socket
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from unittest.mock import patch

import pytest

FROZEN_TS = datetime(2026, 6, 15, 9, 30, 0, tzinfo=timezone.utc)
SEED = 42


class NetworkBlockedError(RuntimeError):
    """Raised when a scenario attempts a real network socket."""


@pytest.fixture(scope="session", autouse=True)
def socket_block():
    """Block all outbound/inbound sockets for the scenario session."""
    real_socket = socket.socket

    def blocked_socket(*args, **kwargs):
        node = os.environ.get("PYTEST_CURRENT_TEST", "<unknown>")
        raise NetworkBlockedError(
            f"Network socket blocked in offline scenario suite (test={node})"
        )

    with patch("socket.socket", side_effect=blocked_socket):
        # Keep AF_UNIX allowed for local multiprocessing if needed — still blocked here
        # to force 100% fixture/mocks. Tests that need localhost sockets must use mocks.
        yield
    # restore is automatic via patch context
    _ = real_socket


@pytest.fixture
def frozen_clock(monkeypatch):
    """Freeze wall-clock time to FROZEN_TS (UTC)."""

    class _FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return FROZEN_TS.replace(tzinfo=None)
            return FROZEN_TS.astimezone(tz)

        @classmethod
        def utcnow(cls):
            return FROZEN_TS.replace(tzinfo=None)

    monkeypatch.setattr("datetime.datetime", _FrozenDateTime)
    return FROZEN_TS


@pytest.fixture
def seeded_rng():
    rng = random.Random(SEED)
    return rng


@pytest.fixture
def tmp_sqlite_wal(tmp_path) -> Path:
    """Fresh WAL-mode SQLite with approval/dedupe/tracking bootstrap tables."""
    db = tmp_path / "scenario.db"
    conn = sqlite3.connect(str(db))
    conn.execute("PRAGMA journal_mode=WAL;")
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
        CREATE TABLE IF NOT EXISTS company_apply_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_key TEXT NOT NULL,
            employer_job_id TEXT,
            applied_at TEXT NOT NULL,
            job_url TEXT
        );
        CREATE TABLE IF NOT EXISTS tracker_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_key TEXT NOT NULL,
            status TEXT NOT NULL,
            board TEXT,
            resume_version TEXT,
            created_at TEXT NOT NULL,
            approval_event_id TEXT
        );
        CREATE TABLE IF NOT EXISTS captcha_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            board TEXT NOT NULL,
            resolved_by TEXT,
            spend_usd REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            unresolved INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS ai_spend (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT,
            task TEXT,
            cost_usd REAL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS jobs (
            job_key TEXT PRIMARY KEY,
            url TEXT,
            title TEXT,
            company TEXT,
            location TEXT,
            status TEXT,
            payload_json TEXT
        );
        CREATE TABLE IF NOT EXISTS webhook_deliveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payload TEXT,
            signature TEXT,
            status TEXT,
            created_at TEXT NOT NULL
        );
        """
    )
    conn.commit()
    conn.close()
    return db


@pytest.fixture
def fixtures_root() -> Path:
    return Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def profile_evidence(fixtures_root) -> dict:
    path = fixtures_root / "profile" / "golden_candidate.json"
    if path.exists():
        import json

        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "name": "Lavkush Kumar",
        "email": "candidate@example.com",
        "phone": "+91-9876543210",
        "resume_text": (
            "DevOps Engineer with Kubernetes, Docker, Terraform, AWS. "
            "Reduced deployment time from 45 minutes to 12 minutes. "
            "Certified in nothing fabricated. Notice period 30 days. "
            "Current CTC 18 LPA. Expected CTC 28 LPA."
        ),
        "certificates": ["AWS Cloud Practitioner"],
        "numbers": ["45", "12", "30", "18", "28"],
        "project_bullets": [
            "Containerized 8 microservices on EKS with Helm.",
            "Instrumented Prometheus/Grafana SLOs at 99.5% uptime.",
        ],
    }
