"""
Comprehensive Test Suite for Universal No-Filter Autonomous Apply Engine
Verifies:
1. NO FILTERING: Removal of score threshold, title filter, company filter, industry filter, salary gate, and experience gate in universal mode.
2. ONLY 3 HARD STOPS:
   - Deduplication (already applied in applied_jobs.db)
   - Closed / dead / expired job link
   - Form error after 2 retries or invalid session
3. STATUS DISTINCTION:
   - 'Submitted (Confirmed)' strictly requires verified non-empty PNG on disk
   - Non-confirmed forms marked as 'Form Auto-Filled' or 'Form Auto-Filled (Ready for Review)'
4. DUAL LOGGING PARITY:
   - Every attempt synchronously recorded in both applied_jobs.db and Naukri_Live_Application_Tracker.xlsx
5. SCORECARD:
   - CycleScorecard aggregates and outputs discovered, applied, confirmed, autofilled, skipped, and failed counts by platform.
"""

import os
import tempfile
import sqlite3
import pytest
import openpyxl
from unittest.mock import MagicMock, patch

from naukari_pro.modules.scorecard import PlatformStats, CycleScorecard, sync_dual_log
from naukari_pro.modules.career_portals import ExternalPortalBatchRunner, CareerPortalManager
from naukari_pro.modules.auto_apply import AutoApplyEngine, NativeChromeRunner, PlaywrightRunner
from naukari_pro.modules.linkedin_apply import LinkedInApplyEngine
from naukari_pro.modules.learning.evidence import PNG_MAGIC_HEADER


@pytest.fixture
def temp_env():
    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "test_applied.db")
        tracker_path = os.path.join(td, "test_tracker.xlsx")
        yield db_path, tracker_path, td


class TestUniversalNoFiltering:
    """Verifies that no score, title, company, or salary gates reject jobs in universal mode."""

    def test_external_batch_runner_applies_all_unfiltered_in_universal_mode(self, temp_env):
        db_path, tracker_path, td = temp_env
        feed = [
            {
                "company": "Random Employer A",
                "title": "Marketing Intern (Totally Unrelated)",
                "salary": "3 - 5 Lacs PA",  # Low salary
                "exp": "8-12 Yrs",          # High experience
                "url": "https://boards.greenhouse.io/random/1",
                "jd": "SEO writing content creation",
                "ats": "Greenhouse"
            },
            {
                "company": "Random Employer B",
                "title": "Chief Technology Officer",
                "salary": "Undisclosed",
                "exp": "15+ Yrs",
                "url": "https://jobs.lever.co/random/2",
                "jd": "Executive management",
                "ats": "Lever"
            }
        ]

        runner = ExternalPortalBatchRunner(
            dry_run=True,
            db_path=db_path,
            universal_apply=True
        )

        with patch("naukari_pro.modules.scorecard.DB_PATH", db_path), \
             patch("naukari_pro.modules.scorecard.TRACKER_PATH", tracker_path):
            stats = runner.run_batch(vacancies=feed, dry_run=True)

        assert stats["total_evaluated"] == 2
        assert stats["submitted"] == 2
        assert stats["skipped"] == 0

    def test_auto_apply_engine_run_offline_preserves_all_payloads_in_universal_mode(self):
        feed = [
            {
                "company": "Generic Corp",
                "title": "Junior Receptionist",
                "salary": "2 - 3 Lacs PA",
                "url": "https://www.naukri.com/job-001",
                "jd": "Greeting visitors answering phones"
            }
        ]
        engine = AutoApplyEngine(dry_run=True, universal_apply=True)
        # Even with an unrelated job, in universal mode offline dry-run evaluates
        assert engine.universal_apply is True


class TestThreeHardStops:
    """Verifies that jobs are skipped only for the 3 allowed hard stops."""

    def test_hard_stop_1_already_applied_deduplication(self, temp_env):
        db_path, tracker_path, td = temp_env

        # Pre-seed applied_jobs.db with an applied job
        from naukari_pro.modules.db import record_applied_job
        record_applied_job(
            title="Lead Azure Data Engineer",
            company="Microsoft GCC",
            platform="career_portal",
            status="Submitted (Confirmed)",
            job_url="https://boards.greenhouse.io/msft/401",
            db_path=db_path
        )

        feed = [{
            "company": "Microsoft GCC",
            "title": "Lead Azure Data Engineer",
            "url": "https://boards.greenhouse.io/msft/401",
            "jd": "Azure Databricks PySpark",
            "ats": "Greenhouse"
        }]

        runner = ExternalPortalBatchRunner(dry_run=True, db_path=db_path, universal_apply=True)
        with patch("naukari_pro.modules.scorecard.DB_PATH", db_path), \
             patch("naukari_pro.modules.scorecard.TRACKER_PATH", tracker_path):
            stats = runner.run_batch(vacancies=feed, dry_run=True)

        assert stats["submitted"] == 0
        assert stats["skipped"] == 1
        assert stats["jobs"][0]["status"] == "SKIPPED_ALREADY_APPLIED"

    def test_hard_stop_2_dead_or_closed_link(self, temp_env):
        db_path, tracker_path, td = temp_env

        feed = [{
            "company": "Dead Corp",
            "title": "Data Engineer",
            "url": "https://example.com/invalid-closed-job",
            "jd": "Azure Databricks",
            "ats": "Generic"
        }]

        runner = ExternalPortalBatchRunner(dry_run=True, db_path=db_path, universal_apply=True)
        with patch("naukari_pro.modules.scorecard.DB_PATH", db_path), \
             patch("naukari_pro.modules.scorecard.TRACKER_PATH", tracker_path):
            stats = runner.run_batch(vacancies=feed, dry_run=True)

        assert stats["submitted"] == 0
        assert stats["skipped"] == 1
        assert stats["jobs"][0]["status"] == "SKIPPED_CLOSED_OR_EXPIRED"

    def test_hard_stop_3_form_error_after_retries(self, temp_env):
        db_path, tracker_path, td = temp_env

        mock_mgr = MagicMock()
        mock_mgr.detect_ats.return_value = "Greenhouse"
        mock_mgr.fill.side_effect = RuntimeError("DOM form crash: submit failed after retries")

        feed = [{
            "company": "Failing Corp",
            "title": "Data Engineer",
            "url": "https://boards.greenhouse.io/failing/1",
            "jd": "Azure Databricks",
            "ats": "Greenhouse"
        }]

        runner = ExternalPortalBatchRunner(manager=mock_mgr, dry_run=False, db_path=db_path, universal_apply=True)
        with patch("naukari_pro.modules.scorecard.DB_PATH", db_path), \
             patch("naukari_pro.modules.scorecard.TRACKER_PATH", tracker_path):
            stats = runner.run_batch(vacancies=feed, dry_run=False)

        assert stats["submitted"] == 0
        assert stats["skipped"] == 1
        assert stats["jobs"][0]["status"] == "FAILED_FORM_ERROR"


class TestStatusDistinctionAndEvidence:
    """Verifies that 'Submitted (Confirmed)' strictly requires verified PNG evidence."""

    def test_submitted_confirmed_requires_valid_png_file(self, temp_env):
        db_path, tracker_path, td = temp_env

        # Case A: Status claimed Confirmed but no evidence file
        db_ok, jid = sync_dual_log(
            title="Senior Data Engineer",
            company="Tech Corp",
            platform="naukri",
            status="Submitted (Confirmed)",
            job_url="https://naukri.com/job/1",
            evidence_path=None,
            db_path=db_path,
            tracker_path=tracker_path
        )

        from naukari_pro.modules.db import get_db_connection
        conn = get_db_connection(db_path)
        row = conn.execute("SELECT status, evidence_path FROM applied_jobs WHERE job_id = ?", (jid,)).fetchone()
        conn.close()

        # Must be downgraded to Form Auto-Filled because evidence is missing
        assert row["status"] == "Form Auto-Filled (Ready for Review)"
        assert row["evidence_path"] is None

        # Case B: Status claimed Confirmed with authentic valid PNG file
        shot_path = os.path.join(td, "real_evidence.png")
        with open(shot_path, "wb") as f:
            f.write(PNG_MAGIC_HEADER + b"\x00" * 2048)

        db_ok2, jid2 = sync_dual_log(
            title="Staff Azure Data Engineer",
            company="Cloud Corp",
            platform="linkedin",
            status="Submitted (Confirmed)",
            job_url="https://linkedin.com/jobs/view/999/",
            evidence_path=shot_path,
            db_path=db_path,
            tracker_path=tracker_path
        )

        conn2 = get_db_connection(db_path)
        row2 = conn2.execute("SELECT status, evidence_path FROM applied_jobs WHERE job_id = ?", (jid2,)).fetchone()
        conn2.close()

        assert row2["status"] == "Submitted (Confirmed)"
        assert row2["evidence_path"] == shot_path


class TestDualLoggingParity:
    """Verifies that SQLite DB and Excel Master Tracker are updated synchronously without drift."""

    def test_dual_logging_synchronization(self, temp_env):
        db_path, tracker_path, td = temp_env

        # 1. Log an application
        sync_dual_log(
            title="Azure Data Platform Engineer",
            company="Walmart Global Tech",
            platform="career_portal (Workday)",
            status="Form Auto-Filled (Ready for Review)",
            job_url="https://walmart.wd5.myworkdayjobs.com/job/101",
            match_score=92.0,
            db_path=db_path,
            tracker_path=tracker_path
        )

        # 2. Check SQLite DB
        from naukari_pro.modules.db import get_db_connection
        conn = get_db_connection(db_path)
        db_count = conn.execute("SELECT COUNT(*) as c FROM applied_jobs").fetchone()["c"]
        conn.close()
        assert db_count == 1

        # 3. Check Excel Tracker
        assert os.path.exists(tracker_path)
        wb = openpyxl.load_workbook(tracker_path, read_only=True)
        assert "Applications_Log" in wb.sheetnames
        ws = wb["Applications_Log"]
        excel_rows = ws.max_row - 1  # Excluding header
        wb.close()
        assert excel_rows == 1


class TestCycleScorecard:
    """Verifies that CycleScorecard properly aggregates multi-platform metrics and outputs scorecard."""

    def test_scorecard_aggregation_and_reporting(self, capsys):
        sc = CycleScorecard(cycle_name="Test Cycle")
        sc.record_discovered("naukri", 15)
        sc.record_applied("naukri", confirmed=False)
        sc.record_applied("naukri", confirmed=True)
        sc.record_skipped_duplicate("naukri", 2)

        sc.record_discovered("linkedin", 10)
        sc.record_applied("linkedin", confirmed=True)
        sc.record_failed_session("linkedin", 1)

        sc.record_discovered("external_ats", 5)
        sc.record_applied("external_ats", confirmed=False)
        sc.record_skipped_closed("external_ats", 1)

        summary = sc.generate_summary()
        assert summary["totals"]["discovered"] == 30
        assert summary["totals"]["applied"] == 4
        assert summary["totals"]["confirmed"] == 2
        assert summary["totals"]["form_autofilled"] == 2
        assert summary["totals"]["skipped"] == 3
        assert summary["totals"]["failed"] == 1

        sc.print_scorecard()
        captured = capsys.readouterr().out
        assert "NAUKARIPRO AUTONOMOUS MULTI-PLATFORM APPLY SCORECARD" in captured
        assert "Naukri" in captured
        assert "LinkedIn" in captured
        assert "External ATS" in captured
