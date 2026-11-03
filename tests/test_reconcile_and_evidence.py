"""
tests/test_reconcile_and_evidence.py

Unit tests for H8: Reconciler and Evidence Auditor.
Tests valid PNG magic bytes, downgrading unverified confirmation rows, and key parity.
"""

import os
import sqlite3
import pytest
from scripts.reconcile_tracker_db import (
    _norm,
    audit_confirmed_evidence,
    load_db_keys,
)


def test_norm_normalization():
    assert _norm("  Google   LLC  ") == "google llc"
    assert _norm("Senior MLOps Engineer") == "senior mlops engineer"
    assert _norm("") == ""
    assert _norm(None) == ""


def test_audit_confirmed_evidence_downgrades_invalid_or_missing_files(tmp_path):
    db_file = str(tmp_path / "test_audit.db")
    conn = sqlite3.connect(db_file)
    conn.execute("""
        CREATE TABLE applied_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT UNIQUE NOT NULL,
            platform TEXT NOT NULL,
            company TEXT NOT NULL,
            title TEXT NOT NULL,
            status TEXT NOT NULL,
            evidence_path TEXT,
            applied_at TEXT
        )
    """)

    # 1. Valid PNG file (>= 1024 bytes with authentic magic header)
    valid_png = str(tmp_path / "valid.png")
    with open(valid_png, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 1024)

    # 2. Corrupt PNG file (invalid magic header)
    fake_png = str(tmp_path / "fake.png")
    with open(fake_png, "wb") as f:
        f.write(b"NOT_A_PNG" + b"\x00" * 1024)

    # 3. Too small PNG file (< 1024 bytes)
    small_png = str(tmp_path / "small.png")
    with open(small_png, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 10)

    # Insert rows
    conn.execute(
        "INSERT INTO applied_jobs (job_id, platform, company, title, status, evidence_path, applied_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("job_valid", "naukri", "Corp A", "MLOps Eng", "Submitted (Confirmed)", valid_png, "2026-11-03 10:00:00")
    )
    conn.execute(
        "INSERT INTO applied_jobs (job_id, platform, company, title, status, evidence_path, applied_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("job_fake", "linkedin", "Corp B", "Data Eng", "Submitted (Confirmed)", fake_png, "2026-11-03 10:01:00")
    )
    conn.execute(
        "INSERT INTO applied_jobs (job_id, platform, company, title, status, evidence_path, applied_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("job_small", "workday", "Corp C", "DevOps Eng", "Submitted (Confirmed)", small_png, "2026-11-03 10:02:00")
    )
    conn.execute(
        "INSERT INTO applied_jobs (job_id, platform, company, title, status, evidence_path, applied_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("job_missing", "greenhouse", "Corp D", "Platform Eng", "Submitted (Confirmed)", str(tmp_path / "missing.png"), "2026-11-03 10:03:00")
    )
    conn.commit()
    conn.close()

    # Run audit
    downgraded = audit_confirmed_evidence(db_file)

    # Expect job_fake, job_small, and job_missing to be downgraded
    down_ids = [d["job_id"] for d in downgraded]
    assert "job_valid" not in down_ids
    assert "job_fake" in down_ids
    assert "job_small" in down_ids
    assert "job_missing" in down_ids

    # Verify status in database
    conn = sqlite3.connect(db_file)
    rows = conn.execute("SELECT job_id, status FROM applied_jobs").fetchall()
    conn.close()

    status_map = dict(rows)
    assert status_map["job_valid"] == "Submitted (Confirmed)"
    assert status_map["job_fake"] == "Form Auto-Filled (Ready for Review)"
    assert status_map["job_small"] == "Form Auto-Filled (Ready for Review)"
    assert status_map["job_missing"] == "Form Auto-Filled (Ready for Review)"
