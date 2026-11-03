"""
tests/test_scorecard.py

Comprehensive tests for Milestone M1 (Feature 3): Unified DB Scorecard.
Validates:
1. PlatformStats tracks all 7 core metrics:
   discovered, applied, confirmed, redirects_pending, outreach_sent, followups_sent, calls_booked.
2. CycleScorecard instantiates all 6 channels:
   naukri, linkedin, external_ats, recruiter_outreach, follow_ups, callbacks.
3. CycleScorecard.sync_from_db() reads metrics directly from applied_jobs and recruiter_outreach in applied_jobs.db.
4. Dual-logging to recruiter_outreach table from RecruiterOutreachCRM.
5. print_scorecard() outputs ASCII table with all 6 channels and 7 metrics.
"""

import os
import sqlite3
import pytest
from datetime import datetime, timedelta

from naukari_pro.modules.scorecard import PlatformStats, CycleScorecard
from naukari_pro.modules.db import (
    init_db,
    record_applied_job,
    record_outreach,
    update_outreach_status
)
from naukari_pro.modules.recruiter_outreach import RecruiterOutreachCRM


@pytest.fixture
def temp_db(tmp_path):
    """Isolated SQLite database fixture."""
    db_file = str(tmp_path / "test_scorecard.db")
    init_db(db_file)
    return db_file


def test_platform_stats_fields():
    """Verifies PlatformStats contains all 7 core metrics and backward-compatible fields."""
    stats = PlatformStats()
    # 7 core metrics
    assert hasattr(stats, "discovered")
    assert hasattr(stats, "applied")
    assert hasattr(stats, "confirmed")
    assert hasattr(stats, "redirects_pending")
    assert hasattr(stats, "outreach_sent")
    assert hasattr(stats, "followups_sent")
    assert hasattr(stats, "calls_booked")
    # Diagnostic / legacy fields
    assert hasattr(stats, "form_autofilled")
    assert hasattr(stats, "skipped_duplicate")
    assert hasattr(stats, "skipped_closed")
    assert hasattr(stats, "failed_form")
    assert hasattr(stats, "failed_session")
    assert hasattr(stats, "evidence_paths")


def test_cycle_scorecard_platforms_initialization():
    """Verifies CycleScorecard initializes all 6 platforms."""
    sc = CycleScorecard(cycle_name="Test Cycle")
    expected_channels = {
        "naukri",
        "linkedin",
        "external_ats",
        "recruiter_outreach",
        "follow_ups",
        "callbacks"
    }
    assert set(sc.platforms.keys()) == expected_channels
    for channel in expected_channels:
        assert isinstance(sc.platforms[channel], PlatformStats)


def test_scorecard_record_helpers():
    """Verifies incremental record helpers for outreach, follow-ups, calls, and redirects."""
    sc = CycleScorecard()

    sc.record_redirect_pending("external_ats", count=3)
    assert sc.platforms["external_ats"].redirects_pending == 3

    sc.record_outreach_sent("recruiter_outreach", count=5)
    assert sc.platforms["recruiter_outreach"].outreach_sent == 5
    assert sc.platforms["recruiter_outreach"].discovered == 5

    sc.record_followup_sent("follow_ups", count=4)
    assert sc.platforms["follow_ups"].followups_sent == 4
    assert sc.platforms["follow_ups"].discovered == 4

    sc.record_call_booked("callbacks", count=2)
    assert sc.platforms["callbacks"].calls_booked == 2


def test_sync_from_db_all_7_metrics(temp_db, tmp_path):
    """
    Verifies sync_from_db directly queries applied_jobs.db
    and populates all 7 metrics across all 6 channels.
    """
    now = datetime.now()
    cycle_start = now - timedelta(minutes=5)
    time_str = now.strftime("%Y-%m-%d %H:%M:%S")

    # 1. Create a dummy evidence screenshot
    evidence_file = str(tmp_path / "evidence_test.png")
    with open(evidence_file, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + b"X" * 2048)

    # 2. Insert records into applied_jobs
    record_applied_job(
        title="Azure Data Engineer",
        company="Microsoft",
        platform="naukri",
        status="Submitted (Confirmed)",
        evidence_path=evidence_file,
        applied_at=time_str,
        db_path=temp_db
    )
    record_applied_job(
        title="MLOps Engineer",
        company="Amazon",
        platform="linkedin",
        status="Submitted",
        applied_at=time_str,
        db_path=temp_db
    )
    record_applied_job(
        title="Cloud Platform Engineer",
        company="Stripe",
        platform="external_ats",
        status="External Redirect",
        applied_at=time_str,
        db_path=temp_db
    )

    # 3. Insert records into recruiter_outreach
    record_outreach(
        recruiter_name="Ananya Sharma",
        company="Walmart Global Tech",
        platform="LinkedIn",
        message_type="Direct InMail",
        status="CONTACTED",
        created_at=time_str,
        db_path=temp_db
    )
    record_outreach(
        recruiter_name="Rahul Verma",
        company="JPMorgan Chase",
        platform="LinkedIn",
        message_type="48-Hour Follow-Up",
        status="PITCH_SENT",
        created_at=time_str,
        db_path=temp_db
    )
    record_outreach(
        recruiter_name="Sarah Jenkins",
        company="Microsoft",
        platform="LinkedIn",
        message_type="Connection Note",
        status="CALL_SCHEDULED",
        call_scheduled_at=time_str,
        created_at=time_str,
        db_path=temp_db
    )

    # 4. Synchronize scorecard directly from SQLite
    sc = CycleScorecard(cycle_name="DB Sync Verification")
    summary = sc.sync_from_db(db_path=temp_db, since=cycle_start)

    totals = summary["totals"]
    by_plat = summary["by_platform"]

    # Verify Naukri
    assert by_plat["naukri"]["applied"] == 1
    assert by_plat["naukri"]["confirmed"] == 1
    assert by_plat["naukri"]["evidence_count"] == 1

    # Verify LinkedIn
    assert by_plat["linkedin"]["applied"] == 1

    # Verify External ATS
    assert by_plat["external_ats"]["redirects_pending"] == 1

    # Verify Recruiter Outreach
    assert by_plat["recruiter_outreach"]["outreach_sent"] == 2

    # Verify Follow-ups
    assert by_plat["follow_ups"]["followups_sent"] == 1

    # Verify Callbacks
    assert by_plat["callbacks"]["calls_booked"] == 1

    # Verify Totals
    assert totals["applied"] == 2
    assert totals["confirmed"] == 1
    assert totals["redirects_pending"] == 1
    assert totals["outreach_sent"] == 2
    assert totals["followups_sent"] == 1
    assert totals["calls_booked"] == 1


def test_recruiter_crm_dual_logging_to_sqlite(temp_db, tmp_path):
    """Verifies that RecruiterOutreachCRM dual-logs directly into SQLite recruiter_outreach table."""
    json_path = str(tmp_path / "outreach.json")
    crm = RecruiterOutreachCRM(json_path=json_path, db_path=temp_db)

    # Monkeypatch default db_path in record_outreach if needed or verify via CRM
    with pytest.MonkeyPatch.context() as mp:
        import naukari_pro.modules.recruiter_outreach as ro
        import naukari_pro.config as cfg
        mp.setattr(cfg, "DB_PATH", temp_db)

        # Log outreach via CRM
        entry = crm.log_outreach(
            recruiter_name="Priya Patel",
            company="Goldman Sachs",
            target_role="MLOps Engineer",
            platform="LinkedIn",
            message_type="Direct InMail",
            status="CONTACTED",
            notes="Testing SQLite dual-log integration"
        )
        assert entry["recruiter_name"] == "Priya Patel"

        # Verify entry entered SQLite
        conn = sqlite3.connect(temp_db)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM recruiter_outreach WHERE recruiter_name = 'Priya Patel'").fetchone()
        conn.close()

        assert row is not None
        assert row["company"] == "Goldman Sachs"
        assert row["status"] == "CONTACTED"

        # Update status via CRM
        crm.update_status(
            identifier="Priya Patel",
            new_status="CALL_SCHEDULED",
            notes="Interview booked for Friday"
        )

        conn = sqlite3.connect(temp_db)
        conn.row_factory = sqlite3.Row
        row_up = conn.execute("SELECT * FROM recruiter_outreach WHERE recruiter_name = 'Priya Patel'").fetchone()
        conn.close()

        assert row_up is not None
        assert row_up["status"] == "CALL_SCHEDULED"
        assert "Friday" in (row_up["notes"] or "")


def test_print_scorecard_runs_cleanly(capsys):
    """Verifies print_scorecard outputs the formatted ASCII table without raising exceptions."""
    sc = CycleScorecard(cycle_name="ASCII Output Test")
    sc.record_applied("naukri", confirmed=True)
    sc.record_redirect_pending("external_ats", count=2)
    sc.record_outreach_sent("recruiter_outreach", count=3)
    sc.record_followup_sent("follow_ups", count=2)
    sc.record_call_booked("callbacks", count=1)

    sc.print_scorecard()

    out = capsys.readouterr().out
    assert "UNIFIED MULTI-CHANNEL SCORECARD" in out
    assert "Naukri" in out
    assert "LinkedIn" in out
    assert "External Portals" in out
    assert "Recruiter Outreach" in out
    assert "Follow-ups" in out
    assert "Callbacks" in out
    assert "TOTAL" in out
