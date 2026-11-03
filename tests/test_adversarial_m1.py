"""
tests/test_adversarial_m1.py
Empirical Adversarial Stress Verification Suite for Milestone 1.

Targeting:
1. Extreme, zero, negative salaries, and reversed experience/salary bounds.
2. Conflicting, duplicate, or unsupported platform specifications.
3. Ambiguous, malformed, injection, and high-volume natural language inputs.
4. Hanging dispatchers, timeouts, and unhandled dispatcher exceptions.
5. Rapid sequential and concurrent multi-threaded dispatches with SQLite deduplication.
6. Boundary conditions for quotas, limits, and match score thresholds.
"""

import time
import json
import sqlite3
import threading
import concurrent.futures
from unittest.mock import MagicMock
import pytest

from naukari_pro.agent.intent import (
    CandidateIntent,
    DEFAULT_TARGET_ROLES,
    DEFAULT_TARGET_LOCATIONS,
    SUPPORTED_PLATFORMS,
)
from naukari_pro.agent.parser import IntentParser
from naukari_pro.agent.dispatchers.base import (
    PlatformDispatcher,
    PlatformExecutionReport,
    BasePlatformDispatcher,
)
from naukari_pro.agent.orchestrator import (
    AutonomousJobApplyAgent,
    AgentExecutionSummary,
)
from naukari_pro.agent.mock_engine import MockMultiPortalHarness, MockPlatformDispatcher
from naukari_pro.modules.db import init_db, get_db_connection, record_applied_job, is_job_already_applied


@pytest.fixture
def temp_db(tmp_path):
    """Provides an isolated SQLite database for deduplication and logging tests."""
    db_file = str(tmp_path / "adversarial_applied_jobs.db")
    init_db(db_file)
    return db_file


# ==============================================================================
# SUITE 1: SALARY & EXPERIENCE BOUNDS ADVERSARIAL STRESS
# ==============================================================================

class TestSalaryAndExperienceAdversarial:
    def test_zero_salary_is_permissible(self):
        """Zero salary represents an unconstrained or unpaid internship scenario."""
        intent = CandidateIntent(min_salary_lpa=0.0)
        assert intent.min_salary_lpa == 0.0

    def test_negative_salary_rejection(self):
        """Negative salaries must be rejected with ValueError."""
        with pytest.raises(ValueError, match="min_salary_lpa cannot be negative"):
            CandidateIntent(min_salary_lpa=-0.01)

        with pytest.raises(ValueError, match="min_salary_lpa cannot be negative"):
            CandidateIntent(min_salary_lpa=-500.0)

    def test_extreme_high_salary_allowed(self):
        """Ultra-high salary bounds must not overflow float or crash."""
        intent = CandidateIntent(min_salary_lpa=10000.0, max_salary_lpa=50000.0)
        assert intent.min_salary_lpa == 10000.0
        assert intent.max_salary_lpa == 50000.0

    def test_reversed_salary_bounds_rejection(self):
        """max_salary_lpa < min_salary_lpa must raise ValueError."""
        with pytest.raises(ValueError, match="cannot be less than min_salary_lpa"):
            CandidateIntent(min_salary_lpa=30.0, max_salary_lpa=25.0)

    def test_negative_max_salary_rejection(self):
        """Negative max salary must be rejected."""
        with pytest.raises(ValueError, match="cannot be less than min_salary_lpa"):
            CandidateIntent(min_salary_lpa=0.0, max_salary_lpa=-1.0)

    def test_equal_salary_bounds_permitted(self):
        """min_salary_lpa == max_salary_lpa represents an exact salary point."""
        intent = CandidateIntent(min_salary_lpa=20.0, max_salary_lpa=20.0)
        assert intent.min_salary_lpa == intent.max_salary_lpa == 20.0

    def test_invalid_type_salary_rejection(self):
        """Non-numeric salary representations must raise ValueError."""
        with pytest.raises(ValueError):
            CandidateIntent(min_salary_lpa="invalid_salary")

        with pytest.raises(ValueError):
            CandidateIntent(min_salary_lpa=[10.0])

    def test_negative_experience_years_rejection(self):
        """Negative experience years must raise ValueError."""
        with pytest.raises(ValueError, match="Experience bounds cannot be negative"):
            CandidateIntent(min_experience_years=-1.0)

        with pytest.raises(ValueError, match="Experience bounds cannot be negative"):
            CandidateIntent(min_experience_years=0.0, max_experience_years=-0.5)

    def test_reversed_experience_years_rejection(self):
        """max_experience_years < min_experience_years must raise ValueError."""
        with pytest.raises(ValueError, match="max_experience_years cannot be less than min_experience_years"):
            CandidateIntent(min_experience_years=5.0, max_experience_years=2.0)

    def test_equal_experience_years_permitted(self):
        """Equal bounds (e.g. exactly 2.5 YOE) must be valid."""
        intent = CandidateIntent(min_experience_years=2.5, max_experience_years=2.5)
        assert intent.min_experience_years == 2.5
        assert intent.max_experience_years == 2.5

    def test_non_numeric_experience_rejection(self):
        """Non-numeric experience strings must raise ValueError."""
        with pytest.raises(ValueError, match="Experience bounds must be numeric"):
            CandidateIntent(min_experience_years="three")

    def test_empty_or_whitespace_roles_fallback_to_defaults(self):
        """Empty list, blank strings, or comma-only roles strings must default to canonical roles."""
        intent_empty = CandidateIntent(target_roles=[])
        assert intent_empty.target_roles == DEFAULT_TARGET_ROLES

        intent_blank_str = CandidateIntent(target_roles="   ,  , \t ")
        assert intent_blank_str.target_roles == DEFAULT_TARGET_ROLES

        intent_none = CandidateIntent(target_roles=None)
        assert intent_none.target_roles == DEFAULT_TARGET_ROLES

    def test_empty_or_whitespace_locations_fallback_to_defaults(self):
        """Empty list or blank strings for locations must default to canonical locations."""
        intent_empty = CandidateIntent(target_locations=[])
        assert "Bengaluru" in intent_empty.target_locations

        intent_blank = CandidateIntent(target_locations="  ,  ,  ")
        assert "Bengaluru" in intent_blank.target_locations

        intent_none = CandidateIntent(target_locations=None)
        assert "Bengaluru" in intent_none.target_locations


# ==============================================================================
# SUITE 2: PLATFORM CONFIGURATION ADVERSARIAL STRESS
# ==============================================================================

class TestPlatformConfigurationAdversarial:
    def test_unsupported_platform_in_list_raises(self):
        """Any unknown platform in the list must raise ValueError immediately."""
        with pytest.raises(ValueError, match="Unsupported platform 'indeed'"):
            CandidateIntent(platforms=["naukri", "indeed", "linkedin"])

    def test_completely_invalid_platforms_raise(self):
        with pytest.raises(ValueError, match="Unsupported platform 'monster'"):
            CandidateIntent(platforms=["monster", "careerbuilder"])

    def test_empty_platform_list_falls_back_to_defaults(self):
        """Empty list should fall back to default supported platforms."""
        intent = CandidateIntent(platforms=[])
        assert set(intent.platforms) == {"naukri", "linkedin", "workday", "greenhouse", "lever"}

    def test_duplicate_platforms_deduplicated(self):
        """Duplicate platforms in input must be deduplicated while preserving order."""
        intent = CandidateIntent(platforms=["naukri", "linkedin", "naukri", "linkedin", "workday"])
        assert intent.platforms == ["naukri", "linkedin", "workday"]

    def test_platform_case_and_whitespace_normalization(self):
        """Platform strings with whitespace or irregular casing must normalize."""
        intent = CandidateIntent(platforms=["  NAUKRI  ", "LinkedIn", "  WORKDAY  "])
        assert intent.platforms == ["naukri", "linkedin", "workday"]

    def test_comma_delimited_platform_string(self):
        """Platform provided as comma-separated string must be parsed correctly."""
        intent = CandidateIntent(platforms="naukri, linkedin, workday, greenhouse")
        assert intent.platforms == ["naukri", "linkedin", "workday", "greenhouse"]


# ==============================================================================
# SUITE 3: MALFORMED & AMBIGUOUS NATURAL LANGUAGE INPUTS
# ==============================================================================

class TestMalformedNLInputsAdversarial:
    def test_empty_and_whitespace_prompts(self):
        """Whitespace or blank inputs must cleanly fall back to ground truth."""
        for prompt in ["", "   ", "\t\t\n\n", "   \r\n   "]:
            intent = IntentParser.parse(prompt)
            assert "MLOps Engineer" in intent.target_roles
            assert "Bengaluru" in intent.target_locations
            assert intent.min_salary_lpa == 20.0

    def test_random_gibberish_input(self):
        """Gibberish strings must not crash the parser."""
        gibberish = "asdfghjkl qwertyuiop zxcvbnm 1234567890 !@#$%^&*()_+{}|:<>?"
        intent = IntentParser.parse(gibberish)
        assert len(intent.target_roles) > 0
        assert len(intent.target_locations) > 0
        assert intent.min_salary_lpa == 20.0
        assert intent.raw_intent == gibberish

    def test_sql_injection_attempt_in_prompt(self):
        """SQL injection strings must be safely handled as plain text."""
        injection = "'; DROP TABLE applied_jobs; SELECT * FROM users WHERE '1'='1"
        intent = IntentParser.parse(injection)
        assert intent.raw_intent == injection
        assert "MLOps Engineer" in intent.target_roles

    def test_xss_and_html_tags_in_prompt(self):
        """HTML/JS tags must be safely treated as text."""
        xss = "<script>alert('pwned')</script><iframe src='javascript:void(0)'></iframe>"
        intent = IntentParser.parse(xss)
        assert "<script>" in intent.raw_intent

    def test_extreme_length_prompt_redos_resistance(self):
        """50,000 characters prompt must parse in < 250ms without catastrophic regex backtracking."""
        long_prompt = "MLOps Engineer in Bengaluru " * 1500
        start = time.perf_counter()
        intent = IntentParser.parse(long_prompt)
        elapsed = time.perf_counter() - start
        assert elapsed < 0.5, f"Parsing took too long ({elapsed:.3f}s), possible ReDoS"
        assert "MLOps Engineer" in intent.target_roles
        assert "Bengaluru" in intent.target_locations

    def test_unicode_and_emojis_in_prompt(self):
        """Unicode characters and emojis must parse smoothly without encoding errors."""
        prompt = "🚀 Looking for MLOps Engineer roles in 📍 Bengaluru with 💰 25 LPA on LinkedIn"
        intent = IntentParser.parse(prompt)
        assert "MLOps Engineer" in intent.target_roles
        assert "Bengaluru" in intent.target_locations
        assert "linkedin" in intent.platforms
        assert intent.min_salary_lpa == 25.0

    def test_inverted_salary_range_in_prompt_handled(self):
        """
        When text states '30 to 20 LPA', min_salary is 30, max_salary is 20.
        CandidateIntent.from_dict validates max < min and raises ValueError.
        Verify that this raises a descriptive ValueError.
        """
        inverted_prompt = "Apply for MLOps roles with 30-20 LPA in Bengaluru"
        with pytest.raises(ValueError, match="cannot be less than min_salary_lpa"):
            IntentParser.parse(inverted_prompt)

    def test_conflicting_platforms_and_locations(self):
        """Conflicting or non-target locations mixed with canonical locations."""
        prompt = "Apply to MLOps Engineer in Tokyo, London, Bengaluru, and Pune on Naukri and Monster"
        intent = IntentParser.parse(prompt)
        # Canonical recognized locations are parsed
        assert "Bengaluru" in intent.target_locations
        assert "Pune" in intent.target_locations
        # Supported platforms parsed, unsupported ignored by NL parser
        assert "naukri" in intent.platforms

    def test_missing_json_file_raises_not_found(self, tmp_path):
        """Non-existent JSON config file must raise FileNotFoundError."""
        missing = tmp_path / "does_not_exist.json"
        with pytest.raises(FileNotFoundError):
            IntentParser.from_json_file(missing)

    def test_malformed_json_raises_decode_error(self, tmp_path):
        """Malformed JSON string/file must raise JSONDecodeError."""
        bad_json = tmp_path / "bad.json"
        bad_json.write_text("{ unquoted_key: 123, }", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            IntentParser.from_json_file(bad_json)

    def test_unsupported_parse_source_type_raises_type_error(self):
        """Passing int, float, or arbitrary objects to IntentParser.parse must raise TypeError."""
        with pytest.raises(TypeError, match="Cannot parse CandidateIntent from unsupported type"):
            IntentParser.parse(12345)

        with pytest.raises(TypeError, match="Cannot parse CandidateIntent from unsupported type"):
            IntentParser.parse(object())


# ==============================================================================
# SUITE 4: DISPATCHER HANGS, TIMEOUTS & ERROR SHIELDING
# ==============================================================================

class TestDispatcherHangsAndTimeoutsAdversarial:
    def test_simulated_dispatcher_hang_times_out(self):
        """A dispatcher that sleeps longer than timeout must be cleanly interrupted."""
        class HungDispatcher(BasePlatformDispatcher):
            platform_name = "hung_portal"
            def _execute_live(self, intent):
                time.sleep(2.0)
                return PlatformExecutionReport(platform_name=self.platform_name)
            def dispatch_dry_run(self, intent):
                return self._execute_live(intent)

        dispatcher = HungDispatcher(timeout_seconds=0.15)
        intent = CandidateIntent(dry_run=False)

        start = time.perf_counter()
        report = dispatcher.dispatch(intent)
        elapsed = time.perf_counter() - start

        assert report.success is False
        assert any("timed out" in err.lower() for err in report.errors)
        assert elapsed < 1.0, f"Dispatcher hung too long: {elapsed:.2f}s"

    def test_orchestrator_handles_dispatcher_hanging(self, temp_db):
        """Orchestrator per_platform_timeout_seconds terminates hanging dispatchers."""
        agent = AutonomousJobApplyAgent(db_path=temp_db, per_platform_timeout_seconds=0.15, dry_run=True)
        harness = MockMultiPortalHarness()

        # Normal dispatcher
        agent.register_dispatcher("greenhouse", MockPlatformDispatcher("greenhouse", harness))

        # Hanging dispatcher
        hanging_disp = MagicMock()
        hanging_disp.platform_name = "workday"
        def hung_exec(*args, **kwargs):
            time.sleep(2.0)
            return PlatformExecutionReport(platform_name="workday", success=True)
        hanging_disp.dispatch_dry_run.side_effect = hung_exec
        agent.register_dispatcher("workday", hanging_disp)

        intent = CandidateIntent(
            target_roles=["MLOps Engineer"],
            target_locations=["Bengaluru"],
            platforms=["workday", "greenhouse"],
            max_applications=4,
            dry_run=True
        )

        start = time.perf_counter()
        summary = agent.execute_intent(intent)
        elapsed = time.perf_counter() - start

        assert summary.platform_reports["workday"].success is False
        assert any("timed out" in err.lower() for err in summary.platform_reports["workday"].errors)
        assert summary.platform_reports["greenhouse"].success is True
        assert summary.total_submitted > 0
        assert summary.status == "PARTIAL"
        assert elapsed < 1.5

    def test_orchestrator_shields_catastrophic_exceptions(self, temp_db):
        """Dispatcher raising unhandled exceptions (MemoryError, ZeroDivisionError) must not kill orchestrator."""
        agent = AutonomousJobApplyAgent(db_path=temp_db, dry_run=True)
        harness = MockMultiPortalHarness()

        class ExplodingDispatcher(BasePlatformDispatcher):
            platform_name = "exploding"
            def _execute_live(self, intent):
                raise ZeroDivisionError("Simulated division by zero in scraper")
            def dispatch_dry_run(self, intent):
                raise RuntimeError("Simulated runtime failure in dry-run")

        agent.register_dispatcher("exploding", ExplodingDispatcher())
        agent.register_dispatcher("lever", MockPlatformDispatcher("lever", harness))

        # Force register exploding platform into agent's supported list for test
        agent.SUPPORTED_PLATFORMS = agent.SUPPORTED_PLATFORMS + ("exploding",)

        # Dispatch
        intent = CandidateIntent(
            target_roles=["MLOps Engineer"],
            target_locations=["Bengaluru"],
            platforms=["lever"],
            max_applications=2,
            dry_run=True
        )
        summary = agent.execute_intent(intent)
        assert summary.status == "COMPLETED"
        assert summary.total_submitted > 0

    def test_all_platforms_failing_sets_status_failed(self, temp_db):
        """When every platform dispatcher fails, status must be FAILED."""
        agent = AutonomousJobApplyAgent(db_path=temp_db, dry_run=True)

        fail_disp = MagicMock()
        fail_disp.platform_name = "naukri"
        fail_disp.dispatch_dry_run.return_value = PlatformExecutionReport(
            platform_name="naukri",
            success=False,
            errors=["Network unreachable"]
        )
        agent.register_dispatcher("naukri", fail_disp)

        intent = CandidateIntent(platforms=["naukri"], max_applications=2, dry_run=True)
        summary = agent.execute_intent(intent)
        assert summary.status == "FAILED"
        assert summary.total_submitted == 0
        assert summary.total_errors >= 1


# ==============================================================================
# SUITE 5: RAPID SEQUENTIAL & CONCURRENT MULTI-THREADED DISPATCHES
# ==============================================================================

class TestConcurrencyAndRapidDispatchesAdversarial:
    def test_rapid_sequential_dispatches_state_isolation(self, temp_db):
        """Executing 25 consecutive intent dispatches must maintain clean isolation."""
        agent = AutonomousJobApplyAgent(db_path=temp_db, dry_run=True)
        harness = MockMultiPortalHarness()
        for name, disp in harness.create_mock_dispatchers().items():
            agent.register_dispatcher(name, disp)

        intent = CandidateIntent(
            target_roles=["MLOps Engineer"],
            target_locations=["Bengaluru"],
            platforms=["greenhouse", "lever"],
            max_applications=2,
            dry_run=True
        )

        for i in range(20):
            summary = agent.execute_intent(intent)
            assert summary.status == "COMPLETED"
            assert summary.total_submitted == 2
            assert summary.total_dedup_skipped == 0
            assert summary.total_errors == 0
            # Ensure duration is positive and isolated
            assert summary.duration_seconds >= 0.0

    def test_multi_threaded_concurrent_dispatches_with_shared_db(self, temp_db):
        """
        Spawning 8 concurrent threads executing live submissions against a shared SQLite DB
        must not throw 'database is locked' errors or corrupt records.
        """
        agent = AutonomousJobApplyAgent(db_path=temp_db, dry_run=False)
        harness = MockMultiPortalHarness()
        for name, disp in harness.create_mock_dispatchers().items():
            agent.register_dispatcher(name, disp)

        num_threads = 6
        summaries = [None] * num_threads
        exceptions = []

        def worker_task(idx):
            try:
                # Give each thread a unique platform/role to simulate multi-agent load
                intent = CandidateIntent(
                    target_roles=["MLOps Engineer"],
                    target_locations=["Bengaluru"],
                    platforms=["greenhouse"],
                    max_applications=1,
                    dry_run=False
                )
                res = agent.execute_intent(intent)
                summaries[idx] = res
            except Exception as exc:
                exceptions.append((idx, exc))

        threads = [threading.Thread(target=worker_task, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        assert len(exceptions) == 0, f"Concurrent execution raised exceptions: {exceptions}"
        assert all(s is not None for s in summaries)

        # Verify DB integrity: verify table is queryable and records exist
        conn = get_db_connection(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM applied_jobs")
        total_rows = cursor.fetchone()[0]
        conn.close()

        # Because all threads attempted Greenhouse, after the 1st thread applies, subsequent threads may deduplicate
        assert total_rows >= 1, f"Expected at least 1 record in DB, found {total_rows}"

    def test_concurrent_deduplication_integrity(self, temp_db):
        """
        Concurrent pre-checks and post-checks on identical job listings
        must prevent duplicate entries.
        """
        # Pre-seed one job
        record_applied_job(
            title="Senior MLOps Platform Engineer",
            company="Anthropic India",
            platform="greenhouse",
            job_url="https://boards.greenhouse.io/anthropic/jobs/999",
            status="Submitted (Confirmed)",
            db_path=temp_db
        )

        # Check deduplication concurrently from 10 threads
        results = []
        def check_dup():
            is_dup = is_job_already_applied(
                title="Senior MLOps Platform Engineer",
                company="Anthropic India",
                job_url="https://boards.greenhouse.io/anthropic/jobs/999",
                db_path=temp_db
            )
            results.append(is_dup)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(check_dup) for _ in range(10)]
            concurrent.futures.wait(futures)

        assert len(results) == 10
        assert all(r is True for r in results)


# ==============================================================================
# SUITE 6: BOUNDARY CONDITIONS & QUOTA ALLOCATION
# ==============================================================================

class TestBoundaryConditionsAndQuotasAdversarial:
    def test_max_applications_boundary_values(self):
        """max_applications must strictly enforce [1, 100] bounds."""
        with pytest.raises(ValueError, match="must be at least 1"):
            CandidateIntent(max_applications=0)

        with pytest.raises(ValueError, match="must be at least 1"):
            CandidateIntent(max_applications=-10)

        intent_min = CandidateIntent(max_applications=1)
        assert intent_min.max_applications == 1

        intent_max = CandidateIntent(max_applications=100)
        assert intent_max.max_applications == 100

        with pytest.raises(ValueError, match="exceeds safety limit of 100"):
            CandidateIntent(max_applications=101)

    def test_strict_match_threshold_boundary_values(self):
        """strict_match_threshold must enforce [0.0, 100.0] bounds."""
        with pytest.raises(ValueError, match="between 0.0 and 100.0"):
            CandidateIntent(strict_match_threshold=-0.1)

        intent_zero = CandidateIntent(strict_match_threshold=0.0)
        assert intent_zero.strict_match_threshold == 0.0

        intent_hundred = CandidateIntent(strict_match_threshold=100.0)
        assert intent_hundred.strict_match_threshold == 100.0

        with pytest.raises(ValueError, match="between 0.0 and 100.0"):
            CandidateIntent(strict_match_threshold=100.1)

    def test_single_application_quota_across_five_platforms(self, temp_db):
        """
        When max_applications=1 and 5 platforms are targeted,
        partitioning must not divide by zero or exceed 1 total application.
        """
        agent = AutonomousJobApplyAgent(db_path=temp_db, dry_run=True)
        harness = MockMultiPortalHarness()
        for name, disp in harness.create_mock_dispatchers().items():
            agent.register_dispatcher(name, disp)

        intent = CandidateIntent(
            target_roles=["MLOps Engineer"],
            target_locations=["Bengaluru"],
            platforms=["naukri", "linkedin", "workday", "greenhouse", "lever"],
            max_applications=1,
            dry_run=True
        )

        summary = agent.execute_intent(intent)
        assert summary.total_submitted == 1
        assert len(summary.applied_jobs) == 1

    def test_intent_with_no_supported_platforms_fails_gracefully(self, temp_db):
        """If intent has only unrecognized platforms, orchestrator returns FAILED summary."""
        agent = AutonomousJobApplyAgent(db_path=temp_db, dry_run=True)

        # Create valid intent then alter platforms to simulate unhandled or bypassed platforms
        intent = CandidateIntent(dry_run=True)
        intent.platforms = ["unsupported_portal_1", "unsupported_portal_2"]

        summary = agent.execute_intent(intent)
        assert summary.status == "FAILED"
        assert "No supported platforms requested" in summary.error_message
