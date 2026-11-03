"""
tests/test_autonomous_agent.py
Offline Test Suite for Milestone 1: Autonomous Intent-Based Application Engine
Covers:
1. CandidateIntent data model & IntentParser validation rules
2. PlatformDispatcher protocol, timeout guards, exception shielding, and async bridging
3. Multi-platform dispatch coordination across Naukri, LinkedIn, Workday, Greenhouse, Lever
4. Deduplication gating via applied_jobs.db
5. Quota management and execution capping
6. MockMultiPortalHarness 5-platform form field mapping and zero unresolved mandatory fields
7. CLI subcommand apply-intent integration
"""

import os
import time
import json
import sqlite3
import argparse
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from naukari_pro.agent.intent import (
    CandidateIntent,
    DEFAULT_TARGET_ROLES,
    DEFAULT_TARGET_LOCATIONS,
    SUPPORTED_PLATFORMS
)
from naukari_pro.agent.parser import IntentParser
from naukari_pro.agent.dispatchers.base import (
    PlatformDispatcher,
    PlatformExecutionReport,
    BasePlatformDispatcher
)
from naukari_pro.agent.dispatchers.naukri_dispatcher import NaukriDispatcher
from naukari_pro.agent.dispatchers.linkedin_dispatcher import LinkedInDispatcher
from naukari_pro.agent.dispatchers.ats_dispatcher import ATSDispatcher, ExternalATSDispatcher
from naukari_pro.agent.orchestrator import AutonomousJobApplyAgent, AgentExecutionSummary
from naukari_pro.agent.mock_engine import (
    MockMultiPortalHarness,
    MockPlatformDispatcher,
    CANONICAL_CANDIDATE_PROFILE
)
from naukari_pro.modules.db import init_db, get_db_connection, record_applied_job, is_job_already_applied
from naukari_pro.cli import handle_apply_intent


@pytest.fixture
def temp_db(tmp_path):
    """Provides an isolated SQLite database for deduplication and logging tests."""
    db_file = str(tmp_path / "test_applied_jobs.db")
    init_db(db_file)
    return db_file


@pytest.fixture
def sample_intent():
    """Provides a canonical MLOps CandidateIntent for testing."""
    return CandidateIntent(
        target_roles=["MLOps Engineer", "ML Platform Engineer", "DevOps for AI"],
        target_locations=["Bengaluru", "Hyderabad", "Pune", "Remote"],
        min_salary_lpa=20.0,
        min_experience_years=2.0,
        max_experience_years=3.0,
        work_authorization="India",
        requires_sponsorship=False,
        platforms=["naukri", "linkedin", "workday", "greenhouse", "lever"],
        max_applications=10,
        dry_run=True,
        strict_match_threshold=70.0
    )


# ==============================================================================
# 1. CANDIDATE INTENT MODEL TESTS
# ==============================================================================

class TestCandidateIntentModel:
    def test_default_candidate_intent_values(self):
        intent = CandidateIntent()
        assert "MLOps Engineer" in intent.target_roles
        assert "Bengaluru" in intent.target_locations
        assert intent.min_salary_lpa == 20.0
        assert intent.min_experience_years == 2.0
        assert intent.max_experience_years == 3.0
        assert intent.work_authorization == "India"
        assert intent.requires_sponsorship is False
        assert intent.max_applications == 15
        assert intent.dry_run is False
        assert intent.strict_match_threshold == 70.0
        assert set(intent.platforms) == {"naukri", "linkedin", "workday", "greenhouse", "lever"}

    def test_custom_candidate_intent_normalization(self):
        intent = CandidateIntent(
            target_roles="MLOps Engineer, AI Infrastructure Engineer",
            target_locations="bangalore, wfh, gurgaon",
            platforms="naukri, linkedin, workday"
        )
        assert intent.target_roles == ["MLOps Engineer", "AI Infrastructure Engineer"]
        assert intent.target_locations == ["Bengaluru", "Remote", "Gurugram"]
        assert intent.platforms == ["naukri", "linkedin", "workday"]

    def test_salary_validation(self):
        with pytest.raises(ValueError, match="min_salary_lpa cannot be negative"):
            CandidateIntent(min_salary_lpa=-5.0)

        with pytest.raises(ValueError, match="cannot be less than min_salary_lpa"):
            CandidateIntent(min_salary_lpa=25.0, max_salary_lpa=20.0)

    def test_experience_bounds_validation(self):
        with pytest.raises(ValueError, match="cannot be less than min_experience_years"):
            CandidateIntent(min_experience_years=5.0, max_experience_years=2.0)

        with pytest.raises(ValueError, match="cannot be negative"):
            CandidateIntent(min_experience_years=-1.0, max_experience_years=3.0)

    def test_platform_validation(self):
        with pytest.raises(ValueError, match="Unsupported platform 'unsupported_portal'"):
            CandidateIntent(platforms=["naukri", "unsupported_portal"])

    def test_application_limits_validation(self):
        with pytest.raises(ValueError, match="max_applications must be at least 1"):
            CandidateIntent(max_applications=0)

        with pytest.raises(ValueError, match="exceeds safety limit"):
            CandidateIntent(max_applications=150)

    def test_strict_match_threshold_validation(self):
        with pytest.raises(ValueError, match="strict_match_threshold must be between 0.0 and 100.0"):
            CandidateIntent(strict_match_threshold=105.0)

    def test_serialization_roundtrip(self, sample_intent):
        d = sample_intent.to_dict()
        assert isinstance(d, dict)
        assert d["min_salary_lpa"] == 20.0

        recreated = CandidateIntent.from_dict(d)
        assert recreated.target_roles == sample_intent.target_roles
        assert recreated.max_applications == sample_intent.max_applications

        json_str = sample_intent.to_json()
        from_json = CandidateIntent.from_json(json_str)
        assert from_json.min_salary_lpa == sample_intent.min_salary_lpa

    def test_compatibility_aliases(self, sample_intent):
        assert sample_intent.roles == sample_intent.target_roles
        assert sample_intent.locations == sample_intent.target_locations
        assert sample_intent.limit == sample_intent.max_applications
        assert sample_intent.min_match_score == sample_intent.strict_match_threshold


# ==============================================================================
# 2. DYNAMIC INTENT PARSER TESTS
# ==============================================================================

class TestIntentParser:
    def test_parse_cli_namespace(self):
        args = argparse.Namespace(
            roles=["MLOps Engineer", "DevOps for AI"],
            locations=["Bengaluru", "Pune"],
            platforms=["naukri", "linkedin"],
            min_salary_lpa=22.0,
            max_salary_lpa=30.0,
            strict_match_threshold=75.0,
            limit=8,
            dry_run=True,
            headed=False,
            work_authorization="India",
            requires_sponsorship=False
        )
        intent = IntentParser.from_args(args)
        assert intent.target_roles == ["MLOps Engineer", "DevOps for AI"]
        assert intent.target_locations == ["Bengaluru", "Pune"]
        assert intent.platforms == ["naukri", "linkedin"]
        assert intent.min_salary_lpa == 22.0
        assert intent.max_salary_lpa == 30.0
        assert intent.strict_match_threshold == 75.0
        assert intent.max_applications == 8
        assert intent.dry_run is True
        assert intent.headless is True

    def test_parse_json_file(self, tmp_path):
        json_file = tmp_path / "intent_config.json"
        data = {
            "target_roles": ["AI Infrastructure Engineer"],
            "target_locations": ["Hyderabad"],
            "min_salary_lpa": 24.0,
            "platforms": ["workday", "greenhouse"],
            "max_applications": 5,
            "dry_run": True
        }
        json_file.write_text(json.dumps(data), encoding="utf-8")

        intent = IntentParser.from_json_file(json_file)
        assert intent.target_roles == ["AI Infrastructure Engineer"]
        assert intent.target_locations == ["Hyderabad"]
        assert intent.min_salary_lpa == 24.0
        assert intent.platforms == ["workday", "greenhouse"]

    def test_parse_dict_with_legacy_aliases(self):
        raw_dict = {
            "roles": ["ML Platform Engineer"],
            "locations": ["Bangalore"],
            "limit": 12,
            "min_score": 80.0,
            "min_salary": 22.0,
            "dry_run": True
        }
        intent = IntentParser.from_dict(raw_dict)
        assert intent.target_roles == ["ML Platform Engineer"]
        assert intent.target_locations == ["Bengaluru"]
        assert intent.max_applications == 12
        assert intent.strict_match_threshold == 80.0
        assert intent.min_salary_lpa == 22.0

    def test_parse_natural_language_full_query(self):
        prompt = (
            "Apply to MLOps Engineer and AI Infrastructure Engineer roles in Bengaluru and Remote "
            "with score >= 75% on LinkedIn, Naukri, and Workday limit 10 dry-run"
        )
        intent = IntentParser.from_text(prompt)
        assert "MLOps Engineer" in intent.target_roles
        assert "AI Infrastructure Engineer" in intent.target_roles
        assert "Bengaluru" in intent.target_locations
        assert "Remote" in intent.target_locations
        assert set(intent.platforms) == {"naukri", "linkedin", "workday"}
        assert intent.strict_match_threshold == 75.0
        assert intent.max_applications == 10
        assert intent.dry_run is True

    def test_parse_natural_language_salary_range(self):
        prompt = "Apply to ML Platform Engineer vacancies with 22-28 LPA in Pune"
        intent = IntentParser.from_text(prompt)
        assert "ML Platform Engineer" in intent.target_roles
        assert "Pune" in intent.target_locations
        assert intent.min_salary_lpa == 22.0
        assert intent.max_salary_lpa == 28.0

    def test_parse_empty_defaults_to_ground_truth(self):
        intent_none = IntentParser.parse(None)
        assert "MLOps Engineer" in intent_none.target_roles
        assert intent_none.min_salary_lpa == 20.0

        intent_empty = IntentParser.parse("")
        assert "Bengaluru" in intent_empty.target_locations

    def test_parse_with_explicit_overrides(self):
        prompt = "Apply to DevOps Engineer in Pune limit 5"
        intent = IntentParser.parse(prompt, min_salary_lpa=25.0, max_applications=3)
        assert intent.min_salary_lpa == 25.0
        assert intent.max_applications == 3


# ==============================================================================
# 3. PLATFORM DISPATCHERS TESTS
# ==============================================================================

class TestPlatformDispatchers:
    def test_platform_dispatcher_protocol_compliance(self, temp_db):
        harness = MockMultiPortalHarness()
        naukri_disp = NaukriDispatcher(db_path=temp_db)
        linkedin_disp = LinkedInDispatcher(db_path=temp_db)
        ats_disp = ATSDispatcher(db_path=temp_db)
        mock_disp = MockPlatformDispatcher("naukri", harness)

        assert isinstance(naukri_disp, PlatformDispatcher)
        assert isinstance(linkedin_disp, PlatformDispatcher)
        assert isinstance(ats_disp, PlatformDispatcher)
        assert isinstance(mock_disp, PlatformDispatcher)

    def test_platform_execution_report_metrics(self):
        report = PlatformExecutionReport(platform_name="test_portal")
        report.add_record({"title": "Job 1", "company": "Comp A", "status": "SUBMITTED"})
        report.add_record({"title": "Job 2", "company": "Comp B", "status": "SKIPPED_DUPLICATE"})
        report.add_record({"title": "Job 3", "company": "Comp C", "status": "REJECTED_BELOW_THRESHOLD"})
        report.add_record({"title": "Job 4", "company": "Comp D", "status": "FAILED_NETWORK"})

        assert report.submitted_count == 1
        assert report.dedup_skipped_count == 1
        assert report.skipped_count == 2  # 1 duplicate + 1 rejected
        assert report.failed_count == 1
        assert len(report.applied_jobs) == 1
        assert len(report.skipped_jobs) == 3

        summary_str = report.summary()
        assert "[TEST_PORTAL]" in summary_str
        assert "Submitted: 1" in summary_str

    def test_naukri_dispatcher_dry_run(self, temp_db, sample_intent):
        dispatcher = NaukriDispatcher(db_path=temp_db)
        report = dispatcher.dispatch_dry_run(sample_intent)

        assert report.platform_name == "naukri"
        assert report.dry_run is True
        assert report.total_evaluated > 0
        assert report.submitted_count > 0
        assert report.success is True

    def test_naukri_dispatcher_dedup_gating(self, temp_db, sample_intent):
        record_applied_job(
            title="Lead MLOps Engineer",
            company="Microsoft GCC",
            platform="naukri",
            job_url="https://www.naukri.com/job-msft-mlops-001",
            status="Submitted (Confirmed)",
            db_path=temp_db
        )

        dispatcher = NaukriDispatcher(db_path=temp_db)
        report = dispatcher.dispatch_dry_run(sample_intent)
        assert report.dedup_skipped_count >= 1

    def test_linkedin_dispatcher_dry_run(self, temp_db, sample_intent):
        dispatcher = LinkedInDispatcher(db_path=temp_db)
        report = dispatcher.dispatch_dry_run(sample_intent)

        assert report.platform_name == "linkedin"
        assert report.dry_run is True
        assert report.total_evaluated > 0
        assert report.success is True

    def test_linkedin_dispatcher_async_bridging(self, temp_db, sample_intent):
        engine_mock = MagicMock()
        # Mock run_apply_cycle coroutine
        async def mock_run_apply_cycle(**kwargs):
            return {
                "discovered": 2,
                "applied": 1,
                "skipped": 1,
                "failed": 0,
                "jobs": [{"title": "MLOps", "company": "GCC", "status": "SUBMITTED"}]
            }
        engine_mock.run_apply_cycle.side_effect = mock_run_apply_cycle

        dispatcher = LinkedInDispatcher(engine=engine_mock, db_path=temp_db)
        report = dispatcher._execute_live(sample_intent)

        assert report.platform_name == "linkedin"
        assert report.submitted_count == 1
        assert report.total_evaluated == 2
        assert report.success is True

    def test_ats_dispatcher_dry_run_multi_portal(self, temp_db, sample_intent):
        ats_disp = ATSDispatcher(db_path=temp_db)
        report = ats_disp.dispatch_dry_run(sample_intent)

        assert report.platform_name == "career_portals"
        assert report.dry_run is True
        assert report.total_evaluated > 0
        assert report.submitted_count > 0

    def test_dispatcher_timeout_guard(self):
        class HangingDispatcher(BasePlatformDispatcher):
            platform_name = "hanging"
            def _execute_live(self, intent):
                time.sleep(1.0)
                return PlatformExecutionReport(platform_name=self.platform_name)
            def dispatch_dry_run(self, intent):
                return self._execute_live(intent)

        disp = HangingDispatcher(timeout_seconds=0.2)
        intent = CandidateIntent(dry_run=False)
        report = disp.dispatch(intent)

        assert report.success is False
        assert "timed out" in report.errors[0].lower()

    def test_dispatcher_exception_shielding(self):
        class CrashingDispatcher(BasePlatformDispatcher):
            platform_name = "crashing"
            def _execute_live(self, intent):
                raise ConnectionResetError("Remote host reset connection")
            def dispatch_dry_run(self, intent):
                return self._execute_live(intent)

        disp = CrashingDispatcher(timeout_seconds=10.0)
        intent = CandidateIntent(dry_run=False)
        report = disp.dispatch(intent)

        assert report.success is False
        assert "unhandled exception" in report.errors[0].lower()


# ==============================================================================
# 4. AUTONOMOUS JOB APPLY AGENT ORCHESTRATION TESTS
# ==============================================================================

class TestAutonomousJobApplyAgent:
    def test_selective_platform_dispatch(self, temp_db):
        agent = AutonomousJobApplyAgent(db_path=temp_db, dry_run=True)
        harness = MockMultiPortalHarness()
        mock_dispatchers = harness.create_mock_dispatchers()

        for name, disp in mock_dispatchers.items():
            agent.register_dispatcher(name, disp)

        intent = CandidateIntent(
            target_roles=["MLOps Engineer"],
            target_locations=["Bengaluru"],
            platforms=["naukri", "greenhouse"],
            max_applications=6,
            dry_run=True
        )

        summary = agent.execute_intent(intent)
        assert summary.status == "COMPLETED"
        assert set(summary.platform_reports.keys()) == {"naukri", "greenhouse"}
        assert "linkedin" not in summary.platform_reports
        assert "workday" not in summary.platform_reports

    def test_quota_partitioning_and_capping(self, temp_db):
        agent = AutonomousJobApplyAgent(db_path=temp_db, dry_run=True)
        harness = MockMultiPortalHarness()
        mock_dispatchers = harness.create_mock_dispatchers()

        for name, disp in mock_dispatchers.items():
            agent.register_dispatcher(name, disp)

        intent = CandidateIntent(
            target_roles=["MLOps Engineer"],
            target_locations=["Bengaluru"],
            platforms=["naukri", "linkedin", "workday", "greenhouse", "lever"],
            max_applications=3,  # Strict cap is 3
            dry_run=True
        )

        summary = agent.execute_intent(intent)
        assert summary.total_submitted <= 3
        assert len(summary.applied_jobs) <= 3

    def test_dedup_blocks_already_applied_job(self, temp_db):
        record_applied_job(
            title="MLOps Engineer (Kubernetes & CI/CD)",
            company="TechCorp India GCC",
            platform="naukri",
            job_id="NAUKRI_MOCK_101",
            status="Submitted (Confirmed)",
            db_path=temp_db
        )

        agent = AutonomousJobApplyAgent(db_path=temp_db, dry_run=False)
        harness = MockMultiPortalHarness()
        mock_dispatchers = harness.create_mock_dispatchers()

        for name, disp in mock_dispatchers.items():
            agent.register_dispatcher(name, disp)

        intent = CandidateIntent(
            target_roles=["MLOps Engineer"],
            target_locations=["Bengaluru"],
            platforms=["naukri"],
            max_applications=5,
            dry_run=False
        )

        summary = agent.execute_intent(intent)
        assert summary.total_dedup_skipped >= 1
        applied_ids = [j.get("job_id") for j in summary.applied_jobs]
        assert "NAUKRI_MOCK_101" not in applied_ids

    def test_dry_run_zero_db_mutation(self, temp_db):
        agent = AutonomousJobApplyAgent(db_path=temp_db, dry_run=True)
        harness = MockMultiPortalHarness()
        mock_dispatchers = harness.create_mock_dispatchers()

        for name, disp in mock_dispatchers.items():
            agent.register_dispatcher(name, disp)

        intent = CandidateIntent(
            target_roles=["MLOps Engineer"],
            target_locations=["Bengaluru"],
            platforms=["greenhouse", "lever"],
            max_applications=5,
            dry_run=True
        )

        summary = agent.execute_intent(intent)
        assert summary.total_submitted > 0

        # Verify applied_jobs table is completely empty
        conn = get_db_connection(temp_db)
        count = conn.execute("SELECT COUNT(*) FROM applied_jobs").fetchone()[0]
        conn.close()
        assert count == 0

    def test_live_submission_records_to_db(self, temp_db):
        agent = AutonomousJobApplyAgent(db_path=temp_db, dry_run=False)
        harness = MockMultiPortalHarness()
        mock_dispatchers = harness.create_mock_dispatchers()

        for name, disp in mock_dispatchers.items():
            agent.register_dispatcher(name, disp)

        intent = CandidateIntent(
            target_roles=["MLOps Engineer"],
            target_locations=["Bengaluru"],
            platforms=["greenhouse"],
            max_applications=2,
            dry_run=False
        )

        summary = agent.execute_intent(intent)
        assert summary.total_submitted > 0
        assert summary.db_updated is True

        # Verify applied_jobs table received the record
        conn = get_db_connection(temp_db)
        count = conn.execute("SELECT COUNT(*) FROM applied_jobs WHERE platform = 'greenhouse'").fetchone()[0]
        conn.close()
        assert count >= 1

    def test_platform_exception_does_not_abort_run(self, temp_db):
        agent = AutonomousJobApplyAgent(db_path=temp_db, dry_run=True)
        harness = MockMultiPortalHarness()

        gh_dispatcher = MockPlatformDispatcher("greenhouse", harness)

        faulty_li = MagicMock()
        faulty_li.platform_name = "linkedin"
        faulty_li.dispatch_dry_run.side_effect = ConnectionResetError("LinkedIn Playwright connection lost")

        agent.register_dispatcher("linkedin", faulty_li)
        agent.register_dispatcher("greenhouse", gh_dispatcher)

        intent = CandidateIntent(
            target_roles=["MLOps Engineer"],
            target_locations=["Bengaluru"],
            platforms=["linkedin", "greenhouse"],
            max_applications=6,
            dry_run=True
        )

        summary = agent.execute_intent(intent)
        assert summary.status == "PARTIAL"
        assert summary.total_errors >= 1
        assert summary.platform_reports["linkedin"].success is False
        assert summary.platform_reports["greenhouse"].success is True
        assert summary.total_submitted > 0

    def test_per_platform_timeout_protection(self, temp_db):
        agent = AutonomousJobApplyAgent(db_path=temp_db, dry_run=True, per_platform_timeout_seconds=0.2)
        harness = MockMultiPortalHarness()

        def hanging_call(*args, **kwargs):
            time.sleep(1.0)
            return PlatformExecutionReport(platform_name="workday", success=True)

        hanging_disp = MagicMock()
        hanging_disp.platform_name = "workday"
        hanging_disp.dispatch_dry_run.side_effect = hanging_call

        agent.register_dispatcher("workday", hanging_disp)
        agent.register_dispatcher("lever", MockPlatformDispatcher("lever", harness))

        intent = CandidateIntent(
            target_roles=["MLOps Engineer"],
            target_locations=["Bengaluru"],
            platforms=["workday", "lever"],
            max_applications=4,
            dry_run=True
        )

        summary = agent.execute_intent(intent)
        assert summary.platform_reports["workday"].success is False
        assert "timed out" in summary.platform_reports["workday"].errors[0].lower()
        assert summary.platform_reports["lever"].success is True

    def test_agent_summary_formatting(self, temp_db):
        agent = AutonomousJobApplyAgent(db_path=temp_db, dry_run=True)
        harness = MockMultiPortalHarness()
        for name, disp in harness.create_mock_dispatchers().items():
            agent.register_dispatcher(name, disp)

        intent = CandidateIntent(
            target_roles=["MLOps Engineer"],
            target_locations=["Bengaluru", "Pune"],
            platforms=["naukri", "linkedin", "workday", "greenhouse", "lever"],
            max_applications=8,
            dry_run=True
        )

        summary = agent.execute_intent(intent)
        report_text = summary.format_summary_report()

        assert "AUTONOMOUS JOB APPLY AGENT" in report_text
        assert "NAUKRI" in report_text
        assert "LINKEDIN" in report_text
        assert "WORKDAY" in report_text
        assert "GREENHOUSE" in report_text
        assert "LEVER" in report_text
        assert summary.status == "COMPLETED"


# ==============================================================================
# 5. MOCK MULTI-PORTAL HARNESS (5 PLATFORMS) TESTS
# ==============================================================================

class TestMockMultiPortalHarness:
    def test_harness_feed_contains_all_5_platforms(self):
        harness = MockMultiPortalHarness()
        for plat in ("naukri", "linkedin", "workday", "greenhouse", "lever"):
            feed = harness.get_mock_job_feed(plat)
            assert len(feed) >= 1
            assert feed[0]["title"] is not None

    def test_form_field_and_screening_resolution_across_all_5(self):
        harness = MockMultiPortalHarness()
        all_results = harness.verify_all_platforms()

        assert len(all_results) == 5
        for plat, results in all_results.items():
            for res in results:
                assert res.is_valid is True, f"Failed on {plat} {res.job_id}: {res.unresolved_mandatory_fields}"
                assert len(res.unresolved_mandatory_fields) == 0

    def test_ground_truth_adherence_in_resolved_fields(self):
        harness = MockMultiPortalHarness()
        wd_jobs = harness.get_mock_job_feed("workday")
        res = harness.simulate_form_fill("workday", wd_jobs[0])

        assert res.resolved_fields["legal_name"] == "Lavkush Kumar"
        assert res.resolved_fields["first_name"] == "Lavkush"
        assert res.resolved_fields["last_name"] == "Kumar"
        assert "Bangalore" in res.resolved_fields["address"]

        answers = res.screening_answers
        for q, ans in answers.items():
            if "convicted" in q.lower():
                assert ans in ("No", "False", False)
            elif "background check" in q.lower():
                assert ans in ("Yes", "True", True)
            elif "sponsorship" in q.lower():
                assert ans in ("No", "False", False)
            elif "authorized" in q.lower():
                assert ans in ("Yes", "True", True)

    def test_candidate_profile_ground_truth_constants(self):
        profile = CANONICAL_CANDIDATE_PROFILE
        assert profile["full_name"] == "Lavkush Kumar"
        assert profile["email"] == "lav84095@gmail.com"
        assert profile["experience_years"] == 2.5
        assert profile["notice_period_days"] == 15
        assert profile["current_ctc_lpa"] == 12.0
        assert profile["expected_ctc_lpa"] == 20.0
        assert profile["current_company"] == "CGI India"
        assert profile["current_title"] == "DevOps Engineer"
        assert profile["work_authorization"] == "India"
        assert profile["requires_sponsorship"] is False


# ==============================================================================
# 6. CLI INTEGRATION TESTS
# ==============================================================================

class TestCLIIntegration:
    def test_handle_apply_intent_controller(self):
        args = argparse.Namespace(
            intent="",
            roles=["MLOps Engineer"],
            locations=["Bengaluru"],
            platforms=["naukri"],
            min_salary_lpa=20.0,
            max_salary_lpa=None,
            strict_match_threshold=70.0,
            config_path=None,
            work_authorization="India",
            requires_sponsorship=False,
            headed=False,
            headless=True,
            limit=2,
            dry_run=True
        )
        exit_code = handle_apply_intent(args)
        assert exit_code == 0
