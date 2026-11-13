"""Offline proofs for Always-on Beast autonomy helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from naukari_pro.modules.autonomous_loop import DRAIN_STATUSES, list_incomplete_portal_jobs
from naukari_pro.modules.db import is_job_already_applied
from naukari_pro.modules.role_guard import is_strictly_data_or_cloud_role


def test_platform_engineer_not_rejected_at_zero_score():
    ok, reason = is_strictly_data_or_cloud_role("Platform Engineer, Python", score=0.0)
    assert ok is True
    assert "matches target" in reason.lower() or "domain" in reason.lower()


def test_devops_title_still_allowed():
    ok, _ = is_strictly_data_or_cloud_role("DevOps Engineer", score=0.0)
    assert ok is True


def test_incomplete_statuses_are_retryable(tmp_path: Path):
    db = tmp_path / "applied_jobs.db"
    conn = sqlite3.connect(str(db))
    conn.execute(
        """
        CREATE TABLE applied_jobs (
            id INTEGER PRIMARY KEY,
            job_id TEXT,
            platform TEXT,
            company TEXT,
            title TEXT,
            location TEXT,
            experience_req TEXT,
            match_score REAL,
            status TEXT,
            application_type TEXT,
            job_url TEXT,
            applied_at TEXT,
            applicant_email TEXT,
            raw_metadata TEXT,
            evidence_path TEXT,
            outcome_label TEXT,
            outcome_observed_at TEXT,
            policy_version TEXT,
            is_backfill INTEGER
        )
        """
    )
    conn.execute(
        """
        INSERT INTO applied_jobs (job_id, platform, company, title, status, job_url, applied_at)
        VALUES ('wd1', 'career_portal', 'Salesforce', 'DevOps Engineer',
                'FALLBACK (SUBMIT_NOT_FOUND)',
                'https://salesforce.wd12.myworkdayjobs.com/job/JR1',
                '2026-11-13 10:00')
        """
    )
    conn.commit()
    conn.close()

    # Incomplete status must NOT block retry
    assert is_job_already_applied(
        title="DevOps Engineer",
        company="Salesforce",
        job_url="https://salesforce.wd12.myworkdayjobs.com/job/JR1",
        db_path=str(db),
    ) is False

    rows = list_incomplete_portal_jobs(limit=10, db_path=db)
    assert len(rows) == 1
    assert rows[0]["status"] in DRAIN_STATUSES


def test_workday_submit_form_has_wizard_advance():
    """Workday submit path includes multi-step Next advance before Submit."""
    import inspect

    from naukari_pro.modules.career_portals import WorkdayHandler

    src = inspect.getsource(WorkdayHandler.submit_form)
    assert "SUBMIT_WIZARD_ADVANCE" in src or "next_selectors" in src
    assert "_click_workday_submit_if_visible" in src
    assert "Next" in src
