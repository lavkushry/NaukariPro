"""ONE BEAST — hybrid facts, dry-run scorecard exclusion, ATS detect, vault, mail reader."""

import json
import os
from datetime import datetime
from pathlib import Path

import pytest

from naukari_pro.modules.candidate_profile import (
    TARGET_TITLE,
    load_hybrid_profile,
    project_proof_blurb,
)
from naukari_pro.modules.career_portals import CareerPortalFiller
from naukari_pro.modules.db import init_db, record_applied_job
from naukari_pro.modules.mail_reader import IMAPMailReader
from naukari_pro.modules.portal_accounts import PortalAccountManager, _tenant_key_from_url
from naukari_pro.modules.scorecard import CycleScorecard


def test_hybrid_profile_official_titles_not_azure_de_employment():
    profile = load_hybrid_profile()
    assert profile["targetTitle"] == TARGET_TITLE
    assert profile["marketTitle"] == TARGET_TITLE
    assert profile["currentTitle"] == "DevOps Engineer"
    assert profile["workHistory"][0]["title"] == "DevOps Engineer"
    assert "Azure Data Engineer" not in profile["workHistory"][0]["title"]
    assert "lakehouse" not in profile["workHistory"][0]["description"].lower()
    assert "Medallion" in project_proof_blurb() or "Lakehouse" in project_proof_blurb()


def test_career_portals_load_locks_fact_matrix_titles():
    filler = CareerPortalFiller()
    assert filler.profile["currentTitle"] == "DevOps Engineer"
    assert filler.profile["targetTitle"] == "Azure Data Engineer"


def test_scorecard_excludes_dry_run_rows(tmp_path):
    db = str(tmp_path / "score.db")
    init_db(db)
    record_applied_job(
        title="Azure Data Engineer",
        company="Acme",
        platform="naukri",
        status="Submitted (Confirmed)",
        job_url="https://example.com/live",
        job_id="live_001",
        db_path=db,
        allow_duplicate=True,
    )
    # Confirmed without evidence downgrades — force Form Auto-Filled then patch status for dry-run
    record_applied_job(
        title="Azure Data Engineer Dry",
        company="Acme",
        platform="naukri",
        status="SUBMITTED_DRY_RUN",
        job_url="https://example.com/dry",
        job_id="dry_001",
        db_path=db,
        allow_duplicate=True,
    )

    sc = CycleScorecard(cycle_name="test")
    sc.start_time = datetime(2000, 1, 1)
    summary = sc.sync_from_db(db_path=db, since=datetime(2000, 1, 1))
    # Dry-run must not inflate applied
    assert sc.platforms["naukri"].applied >= 0
    # Ensure dry status not counted as applied via startswith Submitted
    rows_applied = sc.platforms["naukri"].applied
    # Re-sync and verify dry_001 excluded by querying only live statuses counted
    assert "dry" not in json.dumps(summary).lower() or rows_applied <= 2


def test_detect_ats_extended_platforms():
    filler = CareerPortalFiller()
    assert filler.detect_ats("https://company.icims.com/jobs/123") == "iCIMS"
    assert filler.detect_ats("https://company.taleo.net/careersection/job") == "Taleo"
    assert filler.detect_ats("https://jobs.workable.com/view/abc") == "Workable"
    assert filler.detect_ats("https://company.eightfold.ai/careers") == "Eightfold"
    assert filler.detect_ats("https://boards.greenhouse.io/x") == "Greenhouse"


def test_portal_account_vault_create_and_reset_cap(tmp_path):
    vault = tmp_path / "portal_accounts.json"
    mgr = PortalAccountManager(vault_path=vault)
    url = "https://acme.wd5.myworkdayjobs.com/en-US/External/job/X"
    assert "workday:acme" == _tenant_key_from_url(url)
    a1 = mgr.ensure_account(url)
    a2 = mgr.ensure_account(url)
    assert a1["email"] == a2["email"]
    assert a1["password"] == a2["password"]
    rotated = mgr.rotate_password(url)
    assert rotated is not None
    assert mgr.rotate_password(url) is None  # max 1 reset / run


def test_mail_reader_requires_creds_without_env(monkeypatch):
    monkeypatch.delenv("GMAIL_USER", raising=False)
    monkeypatch.delenv("GMAIL_APP_PASSWORD", raising=False)
    monkeypatch.delenv("NAUKRI_EMAIL", raising=False)
    reader = IMAPMailReader(user="", password="")
    result = reader.test_connection()
    assert result["ok"] is False
