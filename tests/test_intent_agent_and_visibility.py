"""
tests/test_intent_agent_and_visibility.py
Comprehensive verification test suite for Intent-Based Job Apply Agent & 30-Day Visibility Growth Engine:
1. Intent parsing (natural language NLP extraction, score gating, location/role normalization, ATS detection)
2. Multi-channel execution planning and task decomposition
3. Autonomous dispatching across Naukri, LinkedIn, and External Portals (Greenhouse, Lever, Ashby, Workday)
4. Cross-platform deduplication and state tracking in SQLite applied_jobs.db and Excel
5. External ATS Portal Manager & Batch Runner
6. Multi-tier recruiter search keyword optimizer and diluting term guards
7. 30-day algorithmic visibility growth engine, roadmap phases, and 100K impression pacing
8. Candidate ground truth fidelity (2.5 YOE, 15 days notice, ₹20-25 LPA, no forbidden claims)
9. CLI subcommands (intent-apply & boost-visibility) flag parsing and execution
"""

import os
import re
import json
import sqlite3
import tempfile
import pytest
from unittest.mock import patch, MagicMock

from naukari_pro.modules.intent_agent import (
    ApplicationIntent,
    ApplicationExecutionPlan,
    IntentApplyResult,
    IntentParser,
    IntentJobApplyAgent,
    DEFAULT_ROLES,
    DEFAULT_LOCATIONS
)
from naukari_pro.modules.visibility_growth import (
    RecruiterKeywordOptimizer,
    VisibilityGrowthEngine,
    GrowthDaySchedule,
    get_schedule_for_day,
    PROFILE_VARIATIONS,
    TIER_1_MUST_HAVE,
    TIER_2_STRONG_SIGNAL,
    TIER_3_DIFFERENTIATORS,
    DILUTING_TERMS
)
from naukari_pro.modules.career_portals import (
    CareerPortalManager,
    ExternalPortalBatchRunner,
    CURATED_ATS_VACANCIES
)
from naukari_pro.modules.db import (
    init_db,
    get_db_connection,
    record_applied_job,
    is_job_already_applied
)
from naukari_pro.cli import handle_intent_apply, handle_boost_visibility


@pytest.fixture
def temp_db(tmp_path):
    """Provides an isolated SQLite database for deduplication and logging tests."""
    db_file = str(tmp_path / "test_applied_jobs.db")
    init_db(db_file)
    return db_file


@pytest.fixture
def temp_excel(tmp_path):
    """Provides an isolated Excel path for tracker tests."""
    return str(tmp_path / "Test_Application_Tracker.xlsx")


# ==============================================================================
# 1. INTENT PARSING TESTS
# ==============================================================================

class TestIntentParsing:
    def test_parse_natural_language_full_prompt(self):
        query = (
            "Apply to Azure Data Engineer and Databricks roles in Bengaluru/Hyderabad "
            "with match >= 75% on LinkedIn, Naukri, and Greenhouse limit 10"
        )
        intent = IntentParser.parse(query)
        assert isinstance(intent, ApplicationIntent)
        assert "Azure Data Engineer" in intent.roles
        assert "Bengaluru" in intent.locations
        assert "Hyderabad" in intent.locations
        assert "linkedin" in intent.platforms
        assert "naukri" in intent.platforms
        assert "career_portals" in intent.platforms
        assert "greenhouse" in intent.ats_filters
        assert intent.min_match_score == 75.0
        assert intent.limit == 10

    def test_parse_specific_ats_portals(self):
        query = "Apply on Lever, Ashby, and Workday for PySpark Developer in Pune"
        intent = IntentParser.parse(query)
        assert "PySpark Developer" in intent.roles
        assert "Pune" in intent.locations
        assert "career_portals" in intent.platforms
        assert "lever" in intent.ats_filters
        assert "ashby" in intent.ats_filters
        assert "workday" in intent.ats_filters

    def test_parse_dry_run_and_limit_flags(self):
        query = "Simulate 5 Azure Databricks vacancies in Remote with score >= 80% dry-run"
        intent = IntentParser.parse(query)
        assert intent.dry_run is True
        assert intent.limit == 5
        assert intent.min_match_score == 80.0
        assert "Remote" in intent.locations

    def test_parse_empty_string_defaults_to_candidate_ground_truth(self):
        intent = IntentParser.parse("")
        assert len(intent.roles) > 0
        assert "Azure Data Engineer" in intent.roles
        assert "Bengaluru" in intent.locations
        assert intent.min_match_score == 70.0
        assert intent.limit == 15
        assert intent.dry_run is False

    def test_parse_none_defaults_to_canonical(self):
        intent = IntentParser.parse(None)
        assert isinstance(intent, ApplicationIntent)
        assert "naukri" in intent.platforms
        assert "linkedin" in intent.platforms
        assert "career_portals" in intent.platforms

    def test_parse_with_overrides(self):
        query = "Apply on LinkedIn"
        intent = IntentParser.parse(
            query,
            min_match_score=85.0,
            limit=20,
            dry_run=True,
            roles=["Medallion Lakehouse Engineer"]
        )
        assert intent.min_match_score == 85.0
        assert intent.limit == 20
        assert intent.dry_run is True
        assert intent.roles == ["Medallion Lakehouse Engineer"]

    def test_parse_structured_dataclass_input(self):
        original = ApplicationIntent(
            raw_intent="Pre-formed",
            roles=["Azure Data Engineer"],
            limit=7,
            min_match_score=72.0
        )
        parsed = IntentParser.parse(original)
        assert parsed.limit == 7
        assert parsed.min_match_score == 72.0
        assert parsed.roles == ["Azure Data Engineer"]


# ==============================================================================
# 2. EXECUTION PLANNING TESTS
# ==============================================================================

class TestExecutionPlanning:
    def test_plan_execution_decomposes_tasks_across_platforms(self, temp_db, temp_excel):
        agent = IntentJobApplyAgent(dry_run=True, db_path=temp_db, tracker_path=temp_excel)
        intent = ApplicationIntent(
            roles=["Azure Data Engineer", "Databricks Engineer"],
            locations=["Bengaluru", "Hyderabad"],
            platforms=["naukri", "linkedin", "career_portals"],
            ats_filters=["greenhouse"],
            limit=12,
            min_match_score=75.0,
            dry_run=True
        )
        plan = agent.plan_execution(intent)
        assert isinstance(plan, ApplicationExecutionPlan)
        assert len(plan.tasks) == 3
        platforms = [t["platform"] for t in plan.tasks]
        assert "naukri" in platforms
        assert "linkedin" in platforms
        assert "career_portals" in platforms
        # 12 limit / 3 platforms = 4 per task
        assert plan.tasks[0]["limit"] == 4
        assert plan.tasks[0]["min_score"] == 75.0

    def test_plan_execution_single_platform(self, temp_db, temp_excel):
        agent = IntentJobApplyAgent(dry_run=True, db_path=temp_db, tracker_path=temp_excel)
        intent = ApplicationIntent(
            platforms=["linkedin"],
            limit=10,
            min_match_score=80.0
        )
        plan = agent.plan_execution(intent)
        assert len(plan.tasks) == 1
        assert plan.tasks[0]["platform"] == "linkedin"
        assert plan.tasks[0]["limit"] == 10


# ==============================================================================
# 3. INTENT JOB APPLY AGENT DISPATCHING & DEDUPLICATION
# ==============================================================================

class TestIntentJobApplyAgentExecution:
    def test_execute_intent_dry_run_multi_platform(self, temp_db, temp_excel):
        agent = IntentJobApplyAgent(dry_run=True, db_path=temp_db, tracker_path=temp_excel)
        intent = ApplicationIntent(
            raw_intent="Test execution multi platform",
            roles=["Azure Data Engineer", "Databricks Engineer"],
            locations=["Bengaluru", "Hyderabad"],
            platforms=["naukri", "linkedin", "career_portals"],
            limit=6,
            min_match_score=70.0,
            dry_run=True
        )
        result = agent.execute_intent(intent)
        assert isinstance(result, IntentApplyResult)
        assert result.summary["total_evaluated"] > 0
        assert result.summary["total_submitted"] > 0
        assert result.summary["mode"] == "DRY-RUN"
        assert result.duration_seconds >= 0.0

        # Check breakdown contains all 3 platforms
        breakdown = result.summary["breakdown"]
        assert "naukri" in breakdown
        assert "linkedin" in breakdown
        assert "career_portals" in breakdown

    def test_cross_platform_deduplication(self, temp_db, temp_excel):
        """Pre-seeds SQLite DB with a job and verifies IntentJobApplyAgent skips it."""
        agent = IntentJobApplyAgent(dry_run=True, db_path=temp_db, tracker_path=temp_excel)

        # Pre-seed one Microsoft vacancy as already applied
        record_applied_job(
            title="Lead Azure Data Engineer",
            company="Microsoft GCC",
            platform="naukri",
            status="Submitted (Confirmed)",
            db_path=temp_db
        )

        assert is_job_already_applied(title="Lead Azure Data Engineer", company="Microsoft GCC", db_path=temp_db)

        # Execute intent cycle covering Microsoft GCC
        intent = ApplicationIntent(
            roles=["Azure Data Engineer"],
            locations=["Bengaluru"],
            platforms=["naukri", "career_portals"],
            limit=4,
            min_match_score=70.0,
            dry_run=True
        )
        result = agent.execute_intent(intent)

        # Confirm deduplication detected and reported
        assert result.summary["total_dedup_skipped"] >= 1
        skipped_titles = [s["title"] for s in result.skipped_records if s["status"] == "SKIPPED_DUPLICATE"]
        assert any("Azure Data Engineer" in t for t in skipped_titles)

    def test_summary_report_formatting(self, temp_db, temp_excel):
        agent = IntentJobApplyAgent(dry_run=True, db_path=temp_db, tracker_path=temp_excel)
        intent = ApplicationIntent(raw_intent="Formatted summary check", dry_run=True, limit=3)
        result = agent.execute_intent(intent)
        report = result.format_summary_report()
        assert "INTENT-BASED JOB APPLY AGENT EXECUTION SUMMARY" in report
        assert "Channel Breakdown:" in report
        assert "Total Evaluated:" in report


# ==============================================================================
# 4. EXTERNAL ATS PORTAL MANAGER & BATCH RUNNER
# ==============================================================================

class TestExternalPortalBatchRunner:
    def test_detect_ats_various_domains(self):
        manager = CareerPortalManager()
        assert manager.detect_ats("https://boards.greenhouse.io/company/jobs/123") == "Greenhouse"
        assert manager.detect_ats("https://jobs.lever.co/company/456") == "Lever"
        assert manager.detect_ats("https://jobs.ashbyhq.com/company/789") == "Ashby"
        assert manager.detect_ats("https://company.wd5.myworkdayjobs.com/en-US/jobs/101") == "Workday"
        assert manager.detect_ats("https://unknowncompany.com/apply") == "Generic Portal"

    def test_batch_runner_dry_run_filtering(self):
        runner = ExternalPortalBatchRunner(dry_run=True, min_score=70.0, limit=5)
        res = runner.run_batch()
        assert res["dry_run"] is True
        assert res["total_evaluated"] > 0
        assert res["submitted"] > 0
        # Frontend React engineer in curated list should be rejected below threshold
        skipped_statuses = [j["status"] for j in res["jobs"]]
        assert "REJECTED_BELOW_THRESHOLD" in skipped_statuses

    def test_batch_runner_ats_filter(self):
        runner = ExternalPortalBatchRunner(dry_run=True, min_score=70.0, limit=5)
        res = runner.run_batch(ats_types=["Greenhouse"])
        # Only Greenhouse vacancies should be evaluated
        for job in res["jobs"]:
            if job["status"] == "SUBMITTED_DRY_RUN":
                assert job["ats"] == "Greenhouse"


# ==============================================================================
# 5. RECRUITER KEYWORD OPTIMIZER
# ==============================================================================

class TestRecruiterKeywordOptimizer:
    def test_keyword_optimizer_high_score(self):
        opt = RecruiterKeywordOptimizer()
        sample = (
            "Azure Data Engineer | Azure Databricks · PySpark · Delta Lake · Azure Data Factory (ADF) · "
            "SQL · Apache Kafka · ADLS Gen2 · Medallion Architecture · Lakehouse · Terraform · CI/CD | 2.5 YOE"
        )
        audit = opt.audit_text(sample)
        assert audit["tier1_coverage_pct"] >= 70.0
        assert audit["tier2_coverage_pct"] >= 50.0
        assert audit["saturation_score"] >= 60.0
        assert len(audit["diluting_terms_found"]) == 0

    def test_diluting_terms_penalty(self):
        opt = RecruiterKeywordOptimizer()
        sample = "Azure Data Engineer sysadmin junior web developer html css"
        audit = opt.audit_text(sample)
        assert len(audit["diluting_terms_found"]) > 0
        assert audit["is_optimal"] is False

    def test_empty_text_handled_safely(self):
        opt = RecruiterKeywordOptimizer()
        audit = opt.audit_text("")
        assert audit["saturation_score"] == 0.0
        assert audit["tier1_coverage_pct"] == 0.0


# ==============================================================================
# 6. 30-DAY VISIBILITY GROWTH ENGINE
# ==============================================================================

class TestVisibilityGrowthEngine:
    def test_roadmap_phase_and_schedule_coverage(self):
        for day in [1, 7, 8, 14, 15, 21, 22, 30]:
            sched = get_schedule_for_day(day)
            assert isinstance(sched, GrowthDaySchedule)
            assert 1 <= sched.phase_number <= 4
            assert sched.target_daily_impressions >= 2000
            assert sched.cumulative_target > 0
            assert len(sched.actions) >= 3

    def test_profile_variations_character_constraints(self):
        engine = VisibilityGrowthEngine(dry_run=True)
        audits = engine.audit_profile_variations()
        assert len(audits) >= 3
        for vkey, vres in audits.items():
            # Naukri character limit <= 250
            assert vres["naukri_headline_len"] <= 250, f"{vkey} Naukri headline exceeded 250 chars"
            assert vres["naukri_headline_len_ok"] is True
            # LinkedIn character limit <= 220
            assert vres["linkedin_headline_len"] <= 220, f"{vkey} LinkedIn headline exceeded 220 chars"
            assert vres["linkedin_headline_len_ok"] is True
            # Zero blacklist violations
            assert vres["blacklist_passed"] is True, f"{vkey} failed blacklist validation: {vres['blacklist_violations']}"
            assert vres["tier1_coverage_pct"] == 100.0

    def test_execute_daily_visibility_boost_dry_run(self, temp_db):
        engine = VisibilityGrowthEngine(db_path=temp_db, dry_run=True)
        res = engine.execute_daily_visibility_boost(day=12, platform="all", dry_run=True)
        assert res["day"] == 12
        assert res["phase"] == 2
        assert res["dry_run"] is True
        assert len(res["mutations"]) == 2  # Naukri and LinkedIn


# ==============================================================================
# 7. CANDIDATE GROUND TRUTH FIDELITY
# ==============================================================================

class TestCandidateGroundTruthFidelity:
    def test_no_forbidden_verbs_in_profile_variations(self):
        """Verifies that no forbidden passive verbs appear in profile variations."""
        forbidden = ["helped", "assisted", "responsible for"]
        for vname, var in PROFILE_VARIATIONS.items():
            summary_low = var["summary"].lower()
            for verb in forbidden:
                assert f" {verb} " not in f" {summary_low} ", f"Forbidden verb '{verb}' found in {vname} summary"

    def test_candidate_canonical_attributes(self):
        for vname, var in PROFILE_VARIATIONS.items():
            combined = f"{var['naukri_headline']} {var['linkedin_headline']} {var['summary']}"
            # Must state 2.5 YOE or 2.5 years
            assert "2.5" in combined
            # Must state 15 days notice
            assert "15" in combined
            # Must not claim 5+ or 10+ YOE
            assert "5+" not in combined
            assert "10+" not in combined


# ==============================================================================
# 8. CLI INTEGRATION TESTS
# ==============================================================================

class TestCLIIntegration:
    def test_handle_intent_apply_dry_run(self, temp_db, temp_excel):
        with patch("naukari_pro.modules.intent_agent.DB_PATH", temp_db):
            with patch("naukari_pro.modules.intent_agent.TRACKER_PATH", temp_excel):
                res = handle_intent_apply(
                    intent="Apply to Azure Data Engineer roles in Bengaluru with match >= 75%",
                    limit=4,
                    dry_run=True,
                    headless=True
                )
                assert isinstance(res, IntentApplyResult)
                assert res.intent.min_match_score == 75.0
                assert res.summary["mode"] == "DRY-RUN"

    def test_handle_boost_visibility_audit(self, temp_db):
        with patch("naukari_pro.modules.visibility_growth.DB_PATH", temp_db):
            audit = handle_boost_visibility(audit=True, dry_run=True)
            assert isinstance(audit, dict)
            assert "Variation_A_Lakehouse_Scale" in audit

    def test_handle_boost_visibility_execution(self, temp_db):
        with patch("naukari_pro.modules.visibility_growth.DB_PATH", temp_db):
            res = handle_boost_visibility(day=5, platform="naukri", dry_run=True)
            assert res["day"] == 5
            assert res["phase"] == 1
            assert len(res["mutations"]) == 1


# ==============================================================================
# 9. EDGE CASES & BOUNDARY VALUES
# ==============================================================================

class TestEdgeCasesAndBoundaryValues:
    def test_intent_parser_out_of_bounds_match_score(self):
        query = "Apply with match >= 150% and limit 0"
        intent = IntentParser.parse(query)
        # 150% is out of [50.0, 100.0] range, falls back to default 70.0
        assert intent.min_match_score == 70.0

    def test_intent_parser_unsupported_platforms_fallback(self):
        query = "Apply on Indeed and Dice for Azure Data Engineer"
        intent = IntentParser.parse(query)
        # Neither Indeed nor Dice supported, falls back to canonical multi-channel
        assert "naukri" in intent.platforms
        assert "linkedin" in intent.platforms
        assert "career_portals" in intent.platforms

    def test_intent_parser_special_characters_and_casing(self):
        query = "   !!! APPLY TO AZURE DATA ENGINEER IN BENGALURU WITH MATCH >= 85% !!!   "
        intent = IntentParser.parse(query)
        assert "Azure Data Engineer" in intent.roles
        assert "Bengaluru" in intent.locations
        assert intent.min_match_score == 85.0

    def test_batch_runner_empty_vacancies_list(self):
        runner = ExternalPortalBatchRunner(dry_run=True, limit=5)
        res = runner.run_batch(vacancies=[])
        assert res["total_evaluated"] == 0
        assert res["submitted"] == 0
        assert res["skipped"] == 0
        assert len(res["jobs"]) == 0

    def test_visibility_schedule_clamped_boundaries(self):
        sched_low = get_schedule_for_day(-5)
        assert sched_low.day_number == 1
        assert sched_low.phase_number == 1

        sched_high = get_schedule_for_day(99)
        assert sched_high.day_number == 30
        assert sched_high.phase_number == 4

    def test_blacklist_violation_prevention(self):
        from naukari_pro.modules.learning.mutator import BlacklistValidator, BlacklistViolationError
        # Attempting to inject 5+ YOE or 90 days notice must be caught by BlacklistValidator
        is_val, viols = BlacklistValidator.validate_text("Azure Data Engineer with 5+ YOE", "headline")
        assert is_val is False
        assert len(viols) > 0
        assert "YOE Inflation" in viols[0]

        is_val_np, viols_np = BlacklistValidator.validate_text("Candidate serving 90 days notice", "summary")
        assert is_val_np is False
        assert len(viols_np) > 0

    def test_pro_autopilot_recency_touch_integration(self):
        engine = VisibilityGrowthEngine(dry_run=True)
        touch = engine.execute_recency_touch(day=5, dry_run=True)
        assert touch["day"] == 5
        assert touch["autopilot_integrated"] is True
        assert touch["status"] == "DRY_RUN_TOUCH_VERIFIED"
        assert "09:30" in touch["scheduled_time_ist"]

    def test_batch_runner_salary_gating(self):
        runner = ExternalPortalBatchRunner(dry_run=True, min_salary=20.0, limit=5)
        # Low salary test vacancy
        custom_vacancies = [{
            "company": "Low Pay Inc",
            "title": "Azure Data Engineer",
            "url": "https://boards.greenhouse.io/lowpay/jobs/1",
            "salary": "8 - 10 Lacs PA",
            "jd": "Azure Databricks PySpark Delta Lake Medallion"
        }]
        res = runner.run_batch(vacancies=custom_vacancies, min_salary=20.0)
        assert res["submitted"] == 0
        assert res["skipped"] == 1
        assert res["jobs"][0]["status"] == "REJECTED_LOW_SALARY"

    def test_multi_task_platform_breakdown_aggregation(self, temp_db, temp_excel):
        agent = IntentJobApplyAgent(dry_run=True, db_path=temp_db, tracker_path=temp_excel)
        # Passing multiple external platforms creates multiple tasks for career_portals
        intent = ApplicationIntent(
            platforms=["greenhouse", "lever"],
            limit=4,
            dry_run=True
        )
        result = agent.execute_intent(intent)
        # Breakdown should have career_portals with properly accumulated counts
        assert "career_portals" in result.summary["breakdown"]
        cp_stat = result.summary["breakdown"]["career_portals"]
        assert cp_stat["evaluated"] > 0
        assert result.summary["total_evaluated"] >= cp_stat["evaluated"]

    def test_intent_parser_extended_patterns(self):
        query = "Apply for 8 Cloud Data Engineer roles in Delhi NCR and Kolkata with at least 80% match salary >= 22 LPA"
        intent = IntentParser.parse(query)
        assert "Cloud Data Engineer" in intent.roles
        assert "Delhi / NCR" in intent.locations
        assert "Kolkata" in intent.locations
        assert intent.limit == 8
        assert intent.min_match_score == 80.0
        assert intent.min_salary_lpa == 22.0

    def test_cli_min_salary_override(self, temp_db, temp_excel):
        with patch("naukari_pro.modules.intent_agent.DB_PATH", temp_db):
            with patch("naukari_pro.modules.intent_agent.TRACKER_PATH", temp_excel):
                res = handle_intent_apply(
                    intent="Apply to Azure Data Engineer",
                    min_salary=24.0,
                    limit=2,
                    dry_run=True
                )
                assert res.intent.min_salary_lpa == 24.0

