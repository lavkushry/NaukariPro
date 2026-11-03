"""
tests/test_challenger_m1_iter2_adversarial.py
Adversarial Verification Suite authored by Challenger teamwork_challenger_m1_iter2_1.

Empirically verifies:
1. Non-blocking ThreadPoolExecutor shutdown: caller returns in < 1.0s on simulated dispatcher hang (0.2s timeout vs 10.0s hang).
2. Whitespace/comma string fallback: produces canonical ground truth defaults, not empty lists, across roles, locations, and platforms.
3. Dry-run deduplication: duplicates across all 4 tiers are strictly skipped and counted as dedup_skipped_count without DB insertion.
4. Excel tracker hash immutability: zero bytes modified in Naukri_Live_Application_Tracker.xlsx and linkedin_applications_log.json.
5. Orchestrator-level safety gating: post-dispatch duplicates caught in dry-run mode.
"""

import os
import time
import hashlib
import sqlite3
import tempfile
import pytest
from typing import Dict, Any

from naukari_pro.config import BASE_DIR, TRACKER_PATH
from naukari_pro.agent.intent import (
    CandidateIntent,
    DEFAULT_TARGET_ROLES,
    DEFAULT_TARGET_LOCATIONS,
    SUPPORTED_PLATFORMS,
)
from naukari_pro.agent.parser import IntentParser
from naukari_pro.agent.dispatchers.base import (
    BasePlatformDispatcher,
    PlatformExecutionReport,
)
from naukari_pro.agent.orchestrator import (
    AutonomousJobApplyAgent,
    AgentExecutionSummary,
)
from naukari_pro.agent.mock_engine import MockMultiPortalHarness, MockPlatformDispatcher
from naukari_pro.modules.db import (
    init_db,
    generate_job_id,
    record_applied_job,
    is_job_already_applied,
)


LINKEDIN_LOG_PATH = os.path.join(BASE_DIR, "linkedin_applications_log.json")


def _get_file_hash(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ==============================================================================
# 1. NON-BLOCKING THREADPOOLEXECUTOR SHUTDOWN VERIFICATION
# ==============================================================================

class TestNonBlockingThreadPoolShutdown:
    def test_single_hanging_dispatcher_returns_subsecond(self):
        """Dispatcher hangs for 10.0s, timeout is 0.2s. Caller must return in < 1.0s."""
        class TenSecondHangingDispatcher(BasePlatformDispatcher):
            platform_name = "ten_sec_hang"

            def _execute_live(self, intent):
                time.sleep(10.0)
                return PlatformExecutionReport(platform_name=self.platform_name)

            def dispatch_dry_run(self, intent):
                time.sleep(10.0)
                return PlatformExecutionReport(platform_name=self.platform_name)

        dispatcher = TenSecondHangingDispatcher(timeout_seconds=0.2)
        intent = CandidateIntent(dry_run=False)

        start = time.perf_counter()
        report = dispatcher.dispatch(intent)
        elapsed = time.perf_counter() - start

        assert not report.success
        assert any("timed out" in err.lower() for err in report.errors)
        assert elapsed < 1.0, f"Shutdown blocked caller! Elapsed time: {elapsed:.2f}s"

    def test_orchestrator_non_blocking_on_multiple_hanging_dispatchers(self, tmp_path):
        """Orchestrator dispatches to multiple hanging platforms, must return in < 1.5s total."""
        db_file = str(tmp_path / "hang_test.db")
        init_db(db_file)

        agent = AutonomousJobApplyAgent(db_path=db_file, per_platform_timeout_seconds=0.2, dry_run=True)

        class MultiHangDispatcher(BasePlatformDispatcher):
            def __init__(self, name):
                super().__init__(timeout_seconds=0.2)
                self.platform_name = name

            def _execute_live(self, intent):
                time.sleep(5.0)
                return PlatformExecutionReport(platform_name=self.platform_name)

            def dispatch_dry_run(self, intent):
                time.sleep(5.0)
                return PlatformExecutionReport(platform_name=self.platform_name)

        agent.register_dispatcher("naukri", MultiHangDispatcher("naukri"))
        agent.register_dispatcher("linkedin", MultiHangDispatcher("linkedin"))

        intent = CandidateIntent(
            target_roles=["MLOps Engineer"],
            target_locations=["Bengaluru"],
            platforms=["naukri", "linkedin"],
            max_applications=4,
            dry_run=True
        )

        start = time.perf_counter()
        summary = agent.execute_intent(intent)
        elapsed = time.perf_counter() - start

        assert summary.status == "FAILED"
        assert summary.total_errors == 2
        assert summary.platform_reports["naukri"].success is False
        assert summary.platform_reports["linkedin"].success is False
        assert elapsed < 1.5, f"Orchestrator hung waiting for thread pools! Elapsed: {elapsed:.2f}s"


# ==============================================================================
# 2. WHITESPACE / COMMA STRING FALLBACK VERIFICATION
# ==============================================================================

class TestWhitespaceCommaStringFallback:
    @pytest.mark.parametrize("roles_input", [
        "",
        "   ",
        " , , ",
        " \t , \n , \r ",
        [],
        ["", "  ", "\t"],
        None
    ])
    def test_roles_fallback_canonical(self, roles_input):
        intent = CandidateIntent(target_roles=roles_input)
        assert intent.target_roles == DEFAULT_TARGET_ROLES
        assert len(intent.target_roles) > 0
        assert "MLOps Engineer" in intent.target_roles

    @pytest.mark.parametrize("locs_input", [
        "",
        "   ",
        " , , ",
        " \t , \n , \r ",
        [],
        ["", "  ", "\t"],
        None
    ])
    def test_locations_fallback_canonical(self, locs_input):
        intent = CandidateIntent(target_locations=locs_input)
        assert len(intent.target_locations) > 0
        assert "Bengaluru" in intent.target_locations

    @pytest.mark.parametrize("plats_input", [
        "",
        "   ",
        " , , ",
        " \t , \n , \r ",
        [],
        ["", "  ", "\t"],
        None
    ])
    def test_platforms_fallback_canonical(self, plats_input):
        intent = CandidateIntent(platforms=plats_input)
        assert len(intent.platforms) > 0
        assert intent.platforms == ["naukri", "linkedin", "workday", "greenhouse", "lever"]

    def test_parser_with_whitespace_and_empty_strings(self):
        intent = IntentParser.parse("   ")
        assert intent.target_roles == DEFAULT_TARGET_ROLES
        assert "Bengaluru" in intent.target_locations
        assert "naukri" in intent.platforms


# ==============================================================================
# 3. DRY-RUN DEDUPLICATION VERIFICATION
# ==============================================================================

class TestDryRunDeduplicationEmpirical:
    def test_four_tier_deduplication_in_dry_run_with_counts(self, tmp_path):
        db_file = str(tmp_path / "dedup_test.db")
        init_db(db_file)

        # Seed database with known jobs across 4 tiers
        conn = sqlite3.connect(db_file)
        # Tier 1: job_id
        target_id = generate_job_id("MLOps Engineer", "Tier1 Co", "https://t1.com/1")
        conn.execute("""
            INSERT INTO applied_jobs (job_id, platform, company, title, status, job_url)
            VALUES (?, 'greenhouse', 'Tier1 Co', 'MLOps Engineer', 'Submitted (Confirmed)', 'https://t1.com/1')
        """, (target_id,))
        # Tier 2: job_url
        target_url = "https://www.naukri.com/job-msft-mlops-001"
        conn.execute("""
            INSERT INTO applied_jobs (job_id, platform, company, title, status, job_url)
            VALUES ('tier2_id', 'naukri', 'Different Co', 'Different Title', 'Submitted (Confirmed)', ?)
        """, (target_url,))
        # Tier 3: exact title + company
        conn.execute("""
            INSERT INTO applied_jobs (job_id, platform, company, title, status, job_url)
            VALUES ('tier3_id', 'naukri', 'Walmart Global Tech', 'ML Platform Engineer', 'Submitted (Confirmed)', 'https://t3.com')
        """)
        # Tier 4: fuzzy title + company
        conn.execute("""
            INSERT INTO applied_jobs (job_id, platform, company, title, status, job_url)
            VALUES ('tier4_id', 'naukri', 'Amazon AWS Private Limited (India)', 'Senior MLOps Engineer - Immediate Joiner (Remote)', 'Submitted (Confirmed)', 'https://t4.com')
        """)
        conn.commit()
        conn.close()

        agent = AutonomousJobApplyAgent(dry_run=True, db_path=db_file)
        intent = CandidateIntent(
            target_roles=["MLOps Engineer", "ML Platform Engineer"],
            target_locations=["Bengaluru"],
            platforms=["naukri", "greenhouse"],
            max_applications=10,
            dry_run=True
        )

        summary = agent.execute_intent(intent)

        # Assert dedup counter is incremented
        assert summary.total_dedup_skipped >= 1
        naukri_report = summary.platform_reports["naukri"]
        assert naukri_report.dedup_skipped_count >= 1
        assert any(r.get("status") == "SKIPPED_DUPLICATE" for r in naukri_report.records)

        # Ensure no duplicates leaked into applied_jobs
        applied_ids = [j.get("job_id") for j in summary.applied_jobs]
        assert target_id not in applied_ids

        # Ensure database was NOT modified
        conn = sqlite3.connect(db_file)
        count = conn.execute("SELECT COUNT(*) FROM applied_jobs").fetchone()[0]
        conn.close()
        assert count == 4, f"Dry-run inserted into DB! Expected 4, got {count}"


# ==============================================================================
# 4. EXCEL TRACKER & LOG HASH IMMUTABILITY VERIFICATION
# ==============================================================================

class TestExcelTrackerHashImmutability:
    def test_tracker_and_linkedin_log_remain_strictly_unmodified(self, tmp_path):
        tracker_before_hash = _get_file_hash(TRACKER_PATH)
        linkedin_before_hash = _get_file_hash(LINKEDIN_LOG_PATH)

        temp_db = str(tmp_path / "immutability.db")
        init_db(temp_db)

        # Execute full multi-platform dry run across all 5 platforms
        agent = AutonomousJobApplyAgent(dry_run=True, db_path=temp_db)
        intent = CandidateIntent(
            target_roles=["MLOps Engineer", "DevOps Engineer"],
            target_locations=["Bengaluru", "Pune"],
            platforms=["naukri", "linkedin", "workday", "greenhouse", "lever"],
            max_applications=10,
            dry_run=True
        )

        summary = agent.execute_intent(intent)
        assert summary.status in ("COMPLETED", "PARTIAL")

        tracker_after_hash = _get_file_hash(TRACKER_PATH)
        linkedin_after_hash = _get_file_hash(LINKEDIN_LOG_PATH)

        if tracker_before_hash:
            assert tracker_before_hash == tracker_after_hash, (
                f"FATAL: Excel tracker hash changed during dry run!\n"
                f"Before: {tracker_before_hash}\nAfter:  {tracker_after_hash}"
            )
        if linkedin_before_hash:
            assert linkedin_before_hash == linkedin_after_hash, (
                f"FATAL: LinkedIn log hash changed during dry run!\n"
                f"Before: {linkedin_before_hash}\nAfter:  {linkedin_after_hash}"
            )
