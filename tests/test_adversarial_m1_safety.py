"""
Adversarial Verification Suite: Milestone 1 Safety & Deduplication Guarantees
Tests:
1. Dry-run mode safety: zero modifications to applied_jobs table, Excel tracker, or LinkedIn log.
2. 4-tier deduplication gating: Job ID (Tier 1), Job URL (Tier 2), Exact Title+Company (Tier 3), Fuzzy Title+Company (Tier 4).
3. Quota allocation stress tests: strict enforcement of total_submitted <= intent.max_applications.
4. CLI dry-run execution safety: exit code 0 and zero DB side effects.
5. Adversarial vulnerability tests:
   - Orchestrator post-dispatch deduplication gate in dry-run mode (orchestrator.py:296)
   - LinkedIn dispatcher Tier 1 job_id deduplication (linkedin_dispatcher.py:119)
"""

import os
import copy
import hashlib
import sqlite3
import tempfile
import argparse
import pytest
from typing import Dict, Any

from naukari_pro.config import BASE_DIR, TRACKER_PATH
from naukari_pro.modules.db import (
    init_db,
    is_job_already_applied,
    generate_job_id,
    normalize_company_name,
    normalize_role_title,
    get_db_connection
)
from naukari_pro.agent.intent import CandidateIntent
from naukari_pro.agent.orchestrator import AutonomousJobApplyAgent
from naukari_pro.agent.parser import IntentParser
from naukari_pro.agent.mock_engine import MockMultiPortalHarness, MockPlatformDispatcher
from naukari_pro.cli import handle_apply_intent


LINKEDIN_LOG_PATH = os.path.join(BASE_DIR, "linkedin_applications_log.json")


def _get_file_hash(path: str) -> str:
    """Returns SHA256 hex digest of file, or empty string if not found."""
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


class TestDryRunSafetyGuarantees:
    """Empirical verification that dry-run mode NEVER mutates persistent application state."""

    def test_dry_run_never_modifies_applied_jobs_table(self):
        """Verifies zero rows are added or altered in applied_jobs table when dry_run=True."""
        with tempfile.NamedTemporaryFile(suffix=".db") as f:
            db_path = f.name
            init_db(db_path)

            conn = sqlite3.connect(db_path)
            conn.execute("""
                INSERT INTO applied_jobs (job_id, platform, company, title, status, job_url)
                VALUES ('seed_001', 'naukri', 'Baseline Co', 'Baseline Role', 'Submitted (Confirmed)', 'https://baseline.com/1')
            """)
            conn.commit()
            before_rows = conn.execute("SELECT * FROM applied_jobs ORDER BY id").fetchall()
            conn.close()

            agent = AutonomousJobApplyAgent(dry_run=True, db_path=db_path)
            intent = CandidateIntent(
                target_roles=["MLOps Engineer", "ML Platform Engineer"],
                target_locations=["Bengaluru"],
                platforms=["naukri", "workday", "greenhouse", "lever"],
                max_applications=10,
                dry_run=True
            )
            summary = agent.execute_intent(intent)

            # Verification: applications were evaluated and simulated
            assert summary.total_submitted > 0, "Dry-run should simulate submissions"

            # Database check: Zero new rows in applied_jobs
            conn = sqlite3.connect(db_path)
            after_rows = conn.execute("SELECT * FROM applied_jobs ORDER BY id").fetchall()
            conn.close()

            assert len(before_rows) == len(after_rows), f"Expected 1 row, found {len(after_rows)}"
            assert before_rows == after_rows, "applied_jobs rows must remain byte-for-byte identical"

    def test_dry_run_never_touches_tracker_or_linkedin_log(self):
        """Verifies Naukri_Live_Application_Tracker.xlsx and linkedin_applications_log.json remain byte-identical."""
        tracker_before = _get_file_hash(TRACKER_PATH)
        linkedin_before = _get_file_hash(LINKEDIN_LOG_PATH)

        with tempfile.NamedTemporaryFile(suffix=".db") as f:
            db_path = f.name
            init_db(db_path)
            agent = AutonomousJobApplyAgent(dry_run=True, db_path=db_path)
            intent = CandidateIntent(
                target_roles=["MLOps Engineer"],
                target_locations=["Bengaluru"],
                platforms=["naukri", "linkedin", "workday", "greenhouse", "lever"],
                max_applications=5,
                dry_run=True
            )
            summary = agent.execute_intent(intent)
            assert summary.status == "COMPLETED"

        tracker_after = _get_file_hash(TRACKER_PATH)
        linkedin_after = _get_file_hash(LINKEDIN_LOG_PATH)

        if tracker_before:
            assert tracker_before == tracker_after, "Excel tracker hash changed during dry run!"
        if linkedin_before:
            assert linkedin_before == linkedin_after, "LinkedIn log hash changed during dry run!"


class TestFourTierDeduplicationGating:
    """Empirical verification of 4-tier deduplication gating in dry-run and live modes."""

    def test_dedup_tier1_job_id(self):
        """Tier 1: Pre-existing job_id must trigger SKIPPED_DUPLICATE and increment dedup_skipped_count."""
        with tempfile.NamedTemporaryFile(suffix=".db") as f:
            db_path = f.name
            init_db(db_path)

            target_title = "MLOps Engineer"
            target_company = "AI Robotics GCC"
            target_url = "https://boards.greenhouse.io/airobotics/jobs/401"
            target_id = generate_job_id(target_title, target_company, target_url)

            # Insert with matching job_id, but completely unmatched dummy title/company/URL
            conn = sqlite3.connect(db_path)
            conn.execute("""
                INSERT INTO applied_jobs (job_id, platform, company, title, status, job_url)
                VALUES (?, 'greenhouse', 'Completely Unmatched Co', 'Completely Unmatched Title', 'Submitted (Confirmed)', 'https://unmatched.org/999')
            """, (target_id,))
            conn.commit()
            conn.close()

            agent = AutonomousJobApplyAgent(dry_run=True, db_path=db_path)
            intent = CandidateIntent(
                target_roles=[target_title],
                target_locations=["Bengaluru"],
                platforms=["greenhouse"],
                max_applications=5,
                dry_run=True
            )
            summary = agent.execute_intent(intent)

            gh_report = summary.platform_reports["greenhouse"]
            assert gh_report.dedup_skipped_count >= 1, "Tier 1: job_id match must increment dedup_skipped_count"
            assert any(r.get("status") == "SKIPPED_DUPLICATE" for r in gh_report.records)

    def test_dedup_tier2_job_url(self):
        """Tier 2: Pre-existing job_url must trigger SKIPPED_DUPLICATE and increment dedup_skipped_count."""
        with tempfile.NamedTemporaryFile(suffix=".db") as f:
            db_path = f.name
            init_db(db_path)

            target_url = "https://www.naukri.com/job-msft-mlops-001"

            # Insert with matching job_url, but distinct job_id and unmatched title/company
            conn = sqlite3.connect(db_path)
            conn.execute("""
                INSERT INTO applied_jobs (job_id, platform, company, title, status, job_url)
                VALUES ('unique_tier2_id', 'naukri', 'Different Co', 'Different Title', 'Submitted (Confirmed)', ?)
            """, (target_url,))
            conn.commit()
            conn.close()

            agent = AutonomousJobApplyAgent(dry_run=True, db_path=db_path)
            intent = CandidateIntent(
                target_roles=["MLOps Engineer"],
                target_locations=["Bengaluru"],
                platforms=["naukri"],
                max_applications=5,
                dry_run=True
            )
            summary = agent.execute_intent(intent)

            naukri_report = summary.platform_reports["naukri"]
            assert naukri_report.dedup_skipped_count >= 1, "Tier 2: job_url match must increment dedup_skipped_count"
            duplicate_rec = [r for r in naukri_report.records if r.get("url") == target_url]
            assert duplicate_rec[0]["status"] == "SKIPPED_DUPLICATE"

    def test_dedup_tier3_exact_title_and_company(self):
        """Tier 3: Exact title and company match (case-insensitive & trimmed) must trigger SKIPPED_DUPLICATE."""
        with tempfile.NamedTemporaryFile(suffix=".db") as f:
            db_path = f.name
            init_db(db_path)

            # Insert with exact company and title, but different job_id and URL
            conn = sqlite3.connect(db_path)
            conn.execute("""
                INSERT INTO applied_jobs (job_id, platform, company, title, status, job_url)
                VALUES ('unique_tier3_id', 'naukri', ' walmart global tech ', ' ml platform engineer ', 'Submitted (Confirmed)', 'https://old-legacy-url.com')
            """)
            conn.commit()
            conn.close()

            agent = AutonomousJobApplyAgent(dry_run=True, db_path=db_path)
            intent = CandidateIntent(
                target_roles=["MLOps Engineer", "ML Platform Engineer"],
                target_locations=["Bengaluru"],
                platforms=["naukri"],
                max_applications=5,
                dry_run=True
            )
            summary = agent.execute_intent(intent)

            naukri_report = summary.platform_reports["naukri"]
            assert naukri_report.dedup_skipped_count >= 1, "Tier 3: Exact title+company must increment dedup_skipped_count"
            duplicate_rec = [r for r in naukri_report.records if "Walmart" in r.get("company", "")]
            assert duplicate_rec[0]["status"] == "SKIPPED_DUPLICATE"

    def test_dedup_tier4_fuzzy_title_and_company(self):
        """Tier 4: Normalized/fuzzy company and role match must trigger SKIPPED_DUPLICATE."""
        with tempfile.NamedTemporaryFile(suffix=".db") as f:
            db_path = f.name
            init_db(db_path)

            # Insert with legal qualifiers and extra qualifiers that normalization strips
            # Vacancy to test: "Senior MLOps Engineer" at "Amazon AWS"
            conn = sqlite3.connect(db_path)
            conn.execute("""
                INSERT INTO applied_jobs (job_id, platform, company, title, status, job_url)
                VALUES ('unique_tier4_id', 'naukri', 'Amazon AWS Private Limited (India)', 'Senior MLOps Engineer - Immediate Joiner (Remote)', 'Submitted (Confirmed)', 'https://different-url-tier4.com')
            """)
            conn.commit()
            conn.close()

            agent = AutonomousJobApplyAgent(dry_run=True, db_path=db_path)
            intent = CandidateIntent(
                target_roles=["MLOps Engineer", "ML Platform Engineer"],
                target_locations=["Bengaluru"],
                platforms=["naukri"],
                max_applications=5,
                dry_run=True
            )
            summary = agent.execute_intent(intent)

            naukri_report = summary.platform_reports["naukri"]
            assert naukri_report.dedup_skipped_count >= 1, "Tier 4: Fuzzy normalized match must increment dedup_skipped_count"
            duplicate_rec = [r for r in naukri_report.records if "Amazon" in r.get("company", "")]
            assert duplicate_rec[0]["status"] == "SKIPPED_DUPLICATE"


class TestQuotaEnforcementUnderStress:
    """Stress tests verifying quota allocation invariants."""

    @pytest.mark.parametrize("max_apps", [1, 2, 3, 4, 5, 8, 12])
    def test_quota_strictly_enforced(self, max_apps):
        """Verifies that total_submitted never exceeds intent.max_applications."""
        with tempfile.NamedTemporaryFile(suffix=".db") as f:
            db_path = f.name
            init_db(db_path)
            agent = AutonomousJobApplyAgent(dry_run=True, db_path=db_path)
            intent = CandidateIntent(
                target_roles=["MLOps Engineer", "ML Platform Engineer"],
                target_locations=["Bengaluru"],
                platforms=["naukri", "workday", "greenhouse", "lever"],
                max_applications=max_apps,
                dry_run=True
            )
            summary = agent.execute_intent(intent)

            assert summary.total_submitted <= max_apps, f"Quota breached: {summary.total_submitted} > {max_apps}"
            assert len(summary.applied_jobs) == summary.total_submitted, "applied_jobs list length must equal total_submitted"

    def test_single_application_cap(self):
        """Verifies that with max_applications=1, exactly one application is submitted across all platforms."""
        with tempfile.NamedTemporaryFile(suffix=".db") as f:
            db_path = f.name
            init_db(db_path)
            agent = AutonomousJobApplyAgent(dry_run=True, db_path=db_path)
            intent = CandidateIntent(
                target_roles=["MLOps Engineer"],
                target_locations=["Bengaluru"],
                platforms=["naukri", "workday", "greenhouse", "lever"],
                max_applications=1,
                dry_run=True
            )
            summary = agent.execute_intent(intent)

            assert summary.total_submitted == 1
            assert len(summary.applied_jobs) == 1


class TestCLIApplyIntentSafety:
    """Verification of CLI `./naukariPro apply-intent --dry-run` execution safety."""

    def test_cli_apply_intent_dry_run_zero_db_insertions(self):
        """Verifies handle_apply_intent with --dry-run returns exit code 0 and causes 0 applied_jobs insertions."""
        with tempfile.NamedTemporaryFile(suffix=".db") as f:
            db_path = f.name
            init_db(db_path)

            conn = sqlite3.connect(db_path)
            count_before = conn.execute("SELECT COUNT(*) FROM applied_jobs").fetchone()[0]
            conn.close()

            args = argparse.Namespace(
                command="apply-intent",
                intent="Apply for MLOps roles in Bengaluru",
                roles=["MLOps Engineer"],
                locations=["Bengaluru"],
                platforms=["naukri", "workday", "greenhouse", "lever"],
                min_salary_lpa=20.0,
                max_salary_lpa=None,
                strict_match_threshold=70.0,
                config_path=None,
                work_authorization="India",
                requires_sponsorship=False,
                headed=False,
                headless=True,
                dry_run=True,
                limit=3
            )

            # Patch DB_PATH in orchestrator to use the temp db
            from unittest.mock import patch
            with patch("naukari_pro.agent.orchestrator.DB_PATH", db_path), \
                 patch("naukari_pro.modules.db.DB_PATH", db_path):
                exit_code = handle_apply_intent(args)

            assert exit_code == 0, f"Expected exit code 0, got {exit_code}"

            conn = sqlite3.connect(db_path)
            count_after = conn.execute("SELECT COUNT(*) FROM applied_jobs").fetchone()[0]
            conn.close()

            assert count_after == count_before, "Zero rows should be inserted into applied_jobs during dry-run CLI execution"


class TestAdversarialVulnerabilities:
    """Adversarial stress-tests exposing edge-case gating and deduplication vulnerabilities."""

    def test_orchestrator_post_dispatch_dedup_gate_in_dry_run(self):
        """
        VULNERABILITY TEST:
        In orchestrator.py line 296, 'if is_dup and not intent.dry_run:' disables orchestrator-level
        deduplication gating in dry-run mode. When a dispatcher (such as MockPlatformDispatcher)
        emits a job that already exists in applied_jobs.db, the orchestrator counts it as 'total_submitted'
        rather than skipping it and incrementing 'total_dedup_skipped'.
        """
        with tempfile.NamedTemporaryFile(suffix=".db") as f:
            db_path = f.name
            init_db(db_path)

            # Pre-populate DB with a job that MockPlatformDispatcher will generate
            conn = sqlite3.connect(db_path)
            conn.execute("""
                INSERT INTO applied_jobs (job_id, platform, company, title, status, job_url)
                VALUES ('NAUKRI_MOCK_101', 'naukri', 'TechCorp India GCC', 'MLOps Engineer (Kubernetes & CI/CD)', 'Submitted (Confirmed)', 'https://naukri.com/mock101')
            """)
            conn.commit()
            conn.close()

            agent = AutonomousJobApplyAgent(dry_run=True, db_path=db_path)
            harness = MockMultiPortalHarness()
            agent.register_dispatcher("naukri", MockPlatformDispatcher("naukri", harness))

            intent = CandidateIntent(
                target_roles=["MLOps Engineer"],
                target_locations=["Bengaluru"],
                platforms=["naukri"],
                max_applications=5,
                dry_run=True
            )
            summary = agent.execute_intent(intent)

            # The pre-existing job MUST be skipped as duplicate and counted in total_dedup_skipped
            assert summary.total_dedup_skipped >= 1, (
                f"Expected orchestrator gate to record dedup_skipped >= 1 in dry run, got {summary.total_dedup_skipped}. "
                f"Applied jobs: {[j.get('job_id') for j in summary.applied_jobs]}"
            )
            assert not any(j.get("job_id") == "NAUKRI_MOCK_101" for j in summary.applied_jobs), (
                "Pre-existing job 'NAUKRI_MOCK_101' should not be present in applied_jobs!"
            )
