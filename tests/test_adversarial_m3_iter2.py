"""
Milestone 3 Iteration 2 Adversarial Stress Test Suite
Authored by Challenger 1 (teamwork_preview_challenger_m3_iter2_1)

Empirically and adversarially verifies:
1. Non-matching roles ("Cashier", "Bartender", "Dental Hygienist", "PHP 5.4 Webmaster")
   with and without JDs through NativeChromeRunner, PlaywrightRunner, CareerPortalFiller,
   and UniversalJobSearchEngine:
   - Must NEVER be approved.
   - Must NEVER receive artificial score 85 or any score >= 70.
   - Must have status "REJECTED_BELOW_THRESHOLD" (CareerPortalFiller) or False with threshold message (Runners).
2. Genuine matching roles ("Azure Data Engineer with Databricks, PySpark, Delta Lake"):
   - Must receive authentic >= 70 score.
   - Must generate VALIDATED_PAYLOAD.
   - Must be approved in dry-run mode.
3. Edge case score boundaries:
   - Score at 65 (rejected below threshold).
   - Score at 70 (exact threshold accepted).
   - Score at 75 (above threshold accepted).
4. Candidate ground truth fidelity (AGENTS.md §9):
   - CGI India, HFCL Limited, CGI India Apprenticeship, Stipe Solutions.
   - B.Tech from MDU Rohtak.
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

from naukari_pro.modules.job_alerts import (
    calculate_match_score,
    MATCH_SCORE_THRESHOLD,
    KEYWORD_WEIGHTS
)
from naukari_pro.modules.auto_apply import (
    NativeChromeRunner,
    PlaywrightRunner,
    AutoApplyEngine,
    ApplicationPayload,
    evaluate_job_match,
    build_dry_run_payload
)
from naukari_pro.modules.career_portals import (
    CareerPortalFiller,
    load_applicant_profile,
    DEFAULT_CANDIDATE
)
from naukari_pro.modules.multi_search import (
    UniversalJobSearchEngine
)


# ==============================================================================
# SECTION 1: NON-MATCHING ROLES EMPIRICAL STRESS TESTS
# ==============================================================================

NON_MATCHING_ROLES = [
    ("Cashier", "Walmart Supercenter", "Operate cash register, scan items, bag groceries, handle cash and credit card transactions."),
    ("Bartender", "The Rusty Anchor Bar", "Mix cocktails, pour beers, serve patrons, maintain clean bar station and inventory."),
    ("Dental Hygienist", "Apex Smile Clinic", "Clean teeth, examine gums, take dental X-rays, educate patients on oral hygiene."),
    ("PHP 5.4 Webmaster", "Legacy Hosting LLC", "Maintain ancient LAMP stack, edit PHP 5.4 scripts, manage cPanel and MySQL 5.1 databases.")
]


class TestNonMatchingRolesAdversarial:
    """Stress tests completely non-matching roles with and without JDs."""

    @pytest.mark.parametrize("role, company, jd", NON_MATCHING_ROLES)
    def test_non_matching_roles_calculate_match_score(self, role, company, jd):
        """Verify natural match score is strictly 0 and never artificially inflated."""
        assert calculate_match_score(role) == 0
        assert calculate_match_score(f"{role} {company}") == 0
        # JD contains zero Azure Data Engineering keywords (Note: MySQL contains sql which is 10, still << 70)
        score_with_jd = calculate_match_score(f"{role} {company} {jd}")
        assert score_with_jd < MATCH_SCORE_THRESHOLD
        assert score_with_jd != 85

    @pytest.mark.parametrize("role, company, jd", NON_MATCHING_ROLES)
    def test_career_portal_filler_with_and_without_jd(self, role, company, jd):
        """
        Verify CareerPortalFiller.fill_dry_run strictly rejects non-matching roles
        both with empty JD, None JD, and non-matching JD.
        Must NEVER receive 85 or VALIDATED_PAYLOAD.
        """
        filler = CareerPortalFiller()

        # 1. Without JD (empty string)
        p1 = filler.fill_dry_run(
            portal_url="https://boards.greenhouse.io/corp/jobs/101",
            company=company,
            role=role,
            raw_jd="",
            calculate_score=True,
            match_score=None
        )
        assert p1.match_score == 0
        assert p1.match_score != 85
        assert p1.status == "REJECTED_BELOW_THRESHOLD"
        assert p1.status != "VALIDATED_PAYLOAD"

        # 2. With non-matching JD
        p2 = filler.fill_dry_run(
            portal_url="https://jobs.ashbyhq.com/corp/202",
            company=company,
            role=role,
            raw_jd=jd,
            calculate_score=True,
            match_score=None
        )
        assert p2.match_score < 70
        assert p2.match_score != 85
        assert p2.status == "REJECTED_BELOW_THRESHOLD"
        assert p2.status != "VALIDATED_PAYLOAD"

        # 3. With calculate_score=False and match_score=None
        p3 = filler.fill_dry_run(
            portal_url="https://jobs.lever.co/corp/303",
            company=company,
            role=role,
            raw_jd="",
            calculate_score=False,
            match_score=None
        )
        assert p3.match_score == 0
        assert p3.match_score != 85
        assert p3.status == "REJECTED_BELOW_THRESHOLD"

    @pytest.mark.parametrize("role, company, jd", NON_MATCHING_ROLES)
    def test_native_chrome_runner_with_and_without_jd(self, role, company, jd):
        """
        Verify NativeChromeRunner.apply_to_job strictly rejects non-matching roles
        in dry-run mode and live mode.
        Must NEVER return True / approved.
        """
        runner = NativeChromeRunner(skip_list=set(), dry_run=True)

        # Without JD
        ok1, msg1 = runner.apply_to_job(
            job_url="https://www.naukri.com/job-1",
            title=role,
            company=company,
            salary="5-8 LPA",
            raw_jd="",
            match_score=None
        )
        assert ok1 is False
        assert "below required 70% threshold" in msg1
        assert "85%" not in msg1

        # With non-matching JD
        ok2, msg2 = runner.apply_to_job(
            job_url="https://www.naukri.com/job-2",
            title=role,
            company=company,
            salary="5-8 LPA",
            raw_jd=jd,
            match_score=None
        )
        assert ok2 is False
        assert "below required 70% threshold" in msg2
        assert "85%" not in msg2

    @pytest.mark.parametrize("role, company, jd", NON_MATCHING_ROLES)
    def test_playwright_runner_with_and_without_jd(self, role, company, jd):
        """Verify PlaywrightRunner.apply_to_job_async defense-in-depth gate."""
        import asyncio
        runner = PlaywrightRunner(skip_list=set(), dry_run=True)

        # Without JD
        ok1, msg1 = asyncio.run(runner.apply_to_job_async(
            context=None,
            job_url="https://www.naukri.com/job-pw1",
            title=role,
            company=company,
            salary="6 LPA",
            raw_jd="",
            match_score=None
        ))
        assert ok1 is False
        assert "below required 70% threshold" in msg1

        # With non-matching JD
        ok2, msg2 = asyncio.run(runner.apply_to_job_async(
            context=None,
            job_url="https://www.naukri.com/job-pw2",
            title=role,
            company=company,
            salary="6 LPA",
            raw_jd=jd,
            match_score=None
        ))
        assert ok2 is False
        assert "below required 70% threshold" in msg2

    @pytest.mark.parametrize("role, company, jd", NON_MATCHING_ROLES)
    def test_universal_job_search_engine_non_matching(self, role, company, jd):
        """Verify multi-search transformation gates non-matching discovered vacancies."""
        engine = UniversalJobSearchEngine()

        job_dict = {
            "title": role,
            "company": company,
            "url": "https://jobs.lever.co/company/job-99",
            "snippet": jd
        }
        payload = engine.generate_application_payload(job_dict, salary="10 LPA")
        assert payload.match_score < 70
        assert payload.match_score != 85
        assert payload.status == "REJECTED_BELOW_THRESHOLD"


# ==============================================================================
# SECTION 2: GENUINE MATCHING ROLES VERIFICATION
# ==============================================================================

class TestGenuineMatchingRoles:
    """Tests genuine matching roles that must authenticly pass >= 70%."""

    GENUINE_JOB = {
        "title": "Azure Data Engineer",
        "company": "PNC Financial Services Partner",
        "jd": "Seeking Azure Data Engineer with Databricks, PySpark, Delta Lake, SQL, and Kafka experience for Lakehouse architecture.",
        "url": "https://boards.greenhouse.io/pnc/jobs/45678"
    }

    def test_genuine_role_scores_authentic_gte_70(self):
        """Verify genuine matching role achieves authentic >= 70 score."""
        combined_text = f"{self.GENUINE_JOB['title']} {self.GENUINE_JOB['company']} {self.GENUINE_JOB['jd']}"
        score = calculate_match_score(combined_text)
        # azure(20) + databricks(20) + pyspark(15) + delta lake(15) + sql(10) + kafka(10) = 90
        assert score == 90
        assert score >= MATCH_SCORE_THRESHOLD

    def test_genuine_role_career_portal_filler(self):
        """Verify CareerPortalFiller generates VALIDATED_PAYLOAD for genuine role."""
        filler = CareerPortalFiller()
        payload = filler.fill_dry_run(
            portal_url=self.GENUINE_JOB["url"],
            company=self.GENUINE_JOB["company"],
            role=self.GENUINE_JOB["title"],
            raw_jd=self.GENUINE_JOB["jd"],
            salary="25 LPA"
        )
        assert payload.match_score == 90
        assert payload.status == "VALIDATED_PAYLOAD"
        assert payload.dry_run is True
        assert "CGI India" in payload.answers["current_company"]
        assert payload.answers["current_title"] in ["Azure Data Engineer", "DevOps Engineer / Azure Data Engineer"]

    def test_genuine_role_native_chrome_runner(self):
        """Verify NativeChromeRunner approves genuine matching role in dry-run mode."""
        runner = NativeChromeRunner(skip_list=set(), dry_run=True)
        ok, msg = runner.apply_to_job(
            job_url=self.GENUINE_JOB["url"],
            title=self.GENUINE_JOB["title"],
            company=self.GENUINE_JOB["company"],
            salary="25 LPA",
            raw_jd=self.GENUINE_JOB["jd"],
            match_score=None
        )
        assert ok is True
        assert "Dry Run Simulation" in msg

    def test_genuine_role_playwright_runner(self):
        """Verify PlaywrightRunner approves genuine matching role in dry-run mode."""
        import asyncio
        runner = PlaywrightRunner(skip_list=set(), dry_run=True)
        ok, msg = asyncio.run(runner.apply_to_job_async(
            context=None,
            job_url=self.GENUINE_JOB["url"],
            title=self.GENUINE_JOB["title"],
            company=self.GENUINE_JOB["company"],
            salary="25 LPA",
            raw_jd=self.GENUINE_JOB["jd"],
            match_score=None
        ))
        assert ok is True
        assert "Dry Run Simulation" in msg


# ==============================================================================
# SECTION 3: EXACT SCORE BOUNDARIES (65, 70, 75)
# ==============================================================================

class TestExactScoreBoundaries:
    """
    Stress-tests the boundary conditions around 70%:
    - Score 65: azure (20) + databricks (20) + pyspark (15) + sql (10) = 65.
    - Score 70: azure (20) + databricks (20) + pyspark (15) + delta lake (15) = 70.
    - Score 75: azure (20) + databricks (20) + pyspark (15) + delta lake (15) + terraform (5) = 75.
    """

    JD_65 = "Azure Databricks PySpark SQL developer"
    JD_70 = "Azure Databricks PySpark Delta Lake engineer"
    JD_75 = "Azure Databricks PySpark Delta Lake Terraform specialist"

    def test_score_calculation_exact_values(self):
        assert calculate_match_score(self.JD_65) == 65
        assert calculate_match_score(self.JD_70) == 70
        assert calculate_match_score(self.JD_75) == 75

    def test_boundary_65_rejection(self):
        """Score 65 is below 70 threshold: must be rejected across all modules."""
        # 1. CareerPortalFiller
        filler = CareerPortalFiller()
        p = filler.fill_dry_run(
            portal_url="https://boards.greenhouse.io/test/65",
            company="TestCo",
            role="Data Specialist",
            raw_jd=self.JD_65
        )
        assert p.match_score == 65
        assert p.status == "REJECTED_BELOW_THRESHOLD"

        # 2. NativeChromeRunner
        runner = NativeChromeRunner(skip_list=set(), dry_run=True)
        ok, msg = runner.apply_to_job(
            job_url="https://www.naukri.com/65",
            title="Data Specialist",
            company="TestCo",
            salary="20 LPA",
            raw_jd=self.JD_65
        )
        assert ok is False
        assert "Match score 65% is below required 70% threshold" in msg

        # 3. Explicit match_score=65 passed
        p_explicit = filler.fill_dry_run(
            portal_url="https://boards.greenhouse.io/test/65-exp",
            company="TestCo",
            role="Data Specialist",
            match_score=65
        )
        assert p_explicit.match_score == 65
        assert p_explicit.status == "REJECTED_BELOW_THRESHOLD"

    def test_boundary_70_acceptance(self):
        """Score 70 is exact threshold: must be accepted across all modules."""
        # 1. CareerPortalFiller
        filler = CareerPortalFiller()
        p = filler.fill_dry_run(
            portal_url="https://boards.greenhouse.io/test/70",
            company="TestCo",
            role="Data Specialist",
            raw_jd=self.JD_70
        )
        assert p.match_score == 70
        assert p.status == "VALIDATED_PAYLOAD"

        # 2. NativeChromeRunner
        runner = NativeChromeRunner(skip_list=set(), dry_run=True)
        ok, msg = runner.apply_to_job(
            job_url="https://www.naukri.com/70",
            title="Data Specialist",
            company="TestCo",
            salary="20 LPA",
            raw_jd=self.JD_70
        )
        assert ok is True
        assert "Dry Run Simulation" in msg

        # 3. Explicit match_score=70 passed
        p_explicit = filler.fill_dry_run(
            portal_url="https://boards.greenhouse.io/test/70-exp",
            company="TestCo",
            role="Data Specialist",
            match_score=70
        )
        assert p_explicit.match_score == 70
        assert p_explicit.status == "VALIDATED_PAYLOAD"

    def test_boundary_75_acceptance(self):
        """Score 75 is above threshold: must be accepted across all modules."""
        # 1. CareerPortalFiller
        filler = CareerPortalFiller()
        p = filler.fill_dry_run(
            portal_url="https://boards.greenhouse.io/test/75",
            company="TestCo",
            role="Data Specialist",
            raw_jd=self.JD_75
        )
        assert p.match_score == 75
        assert p.status == "VALIDATED_PAYLOAD"

        # 2. NativeChromeRunner
        runner = NativeChromeRunner(skip_list=set(), dry_run=True)
        ok, msg = runner.apply_to_job(
            job_url="https://www.naukri.com/75",
            title="Data Specialist",
            company="TestCo",
            salary="20 LPA",
            raw_jd=self.JD_75
        )
        assert ok is True
        assert "Dry Run Simulation" in msg

        # 3. Explicit match_score=75 passed
        p_explicit = filler.fill_dry_run(
            portal_url="https://boards.greenhouse.io/test/75-exp",
            company="TestCo",
            role="Data Specialist",
            match_score=75
        )
        assert p_explicit.match_score == 75
        assert p_explicit.status == "VALIDATED_PAYLOAD"


# ==============================================================================
# SECTION 4: CANDIDATE GROUND TRUTH FIDELITY (AGENTS.md §9)
# ==============================================================================

class TestCandidateGroundTruthFidelity:
    """Verifies AGENTS.md §9 ground truth candidate facts in profile and payloads."""

    def test_default_candidate_constants(self):
        assert DEFAULT_CANDIDATE["currentCompany"] == "CGI India (PNC Bank GCC)"
        assert DEFAULT_CANDIDATE["currentTitle"] == "DevOps Engineer / Azure Data Engineer"
        assert len(DEFAULT_CANDIDATE["workHistory"]) == 4

        roles = [r["company"] for r in DEFAULT_CANDIDATE["workHistory"]]
        assert "CGI India (PNC Bank GCC)" in roles[0]
        assert "HFCL Limited" in roles[1]
        assert "CGI India" in roles[2]
        assert "Stipe Solutions" in roles[3]

        assert len(DEFAULT_CANDIDATE["education"]) >= 1
        assert "Maharishi Dayanand University" in DEFAULT_CANDIDATE["education"][0]["institution"]

    def test_load_applicant_profile_contains_ground_truth(self):
        prof = load_applicant_profile()
        assert "CGI India" in prof["currentCompany"]
        assert len(prof["workHistory"]) == 4
        assert len(prof["education"]) >= 1

    def test_dry_run_payload_preserves_ground_truth(self):
        filler = CareerPortalFiller()
        p = filler.fill_dry_run(
            portal_url="https://jobs.lever.co/company/job-1",
            company="Target Corp",
            role="Azure Data Engineer",
            raw_jd="Azure Databricks PySpark Delta Lake"
        )
        assert "CGI India" in p.answers["current_company"]
        assert p.answers["current_title"] in ["Azure Data Engineer", "DevOps Engineer / Azure Data Engineer"]
        assert len(p.answers["work_history"]) == 4
        assert len(p.answers["education"]) >= 1
        assert p.payload_data["work_history_count"] == 4
        assert p.payload_data["current_company"] == "CGI India (PNC Bank GCC)"


# ==============================================================================
# SECTION 5: MALFORMED / NULL SAFETY & DEFENSIVE RESILIENCE
# ==============================================================================

class TestMalformedAndNullSafetyAdversarial:
    """Stress tests null inputs, empty dictionaries, and unexpected types."""

    def test_calculate_match_score_malformed_inputs(self):
        assert calculate_match_score(None) == 0
        assert calculate_match_score("") == 0
        assert calculate_match_score("   ") == 0
        assert calculate_match_score(123456) == 0
        assert calculate_match_score(["azure", "databricks"]) == 40  # str(["azure", ...]) contains azure and databricks

    def test_career_portal_filler_null_safety(self):
        filler = CareerPortalFiller()
        p = filler.fill_dry_run(
            portal_url=None,
            company=None,
            role=None,
            raw_jd=None
        )
        assert p.match_score == 0
        assert p.status == "REJECTED_BELOW_THRESHOLD"
        assert p.url == "N/A"

    def test_native_chrome_runner_null_safety(self):
        runner = NativeChromeRunner(skip_list=set(), dry_run=True)
        ok, msg = runner.apply_to_job(
            job_url=None,
            title=None,
            company=None,
            salary=None,
            raw_jd=None
        )
        assert ok is False
        assert "below required 70% threshold" in msg

    def test_universal_job_search_engine_empty_dict(self):
        engine = UniversalJobSearchEngine()
        # Empty dict defaults title to "Azure Data Engineer", containing "azure" (20 pts), still << 70
        payload = engine.generate_application_payload({})
        assert payload.match_score == 20
        assert payload.status == "REJECTED_BELOW_THRESHOLD"
        assert payload.url == "N/A"

        # Explicit non-matching role
        payload_cashier = engine.generate_application_payload({"title": "Cashier", "company": "Store"})
        assert payload_cashier.match_score == 0
        assert payload_cashier.status == "REJECTED_BELOW_THRESHOLD"

    def test_detect_ats_null_and_malformed(self):
        filler = CareerPortalFiller()
        assert filler.detect_ats(None) == "Generic Portal"
        assert filler.detect_ats("") == "Generic Portal"
        assert filler.detect_ats("   ") == "Generic Portal"
        assert filler.detect_ats(12345) == "Generic Portal"
        assert filler.detect_ats("https://invalid-url-with-no-ats.org") == "Generic Portal"


# ==============================================================================
# SECTION 6: SHARP STEP FUNCTION AT THRESHOLD (69 vs 70 vs 71)
# ==============================================================================

class TestSharpThresholdStepFunction:
    """Proves the gate behaves as a sharp mathematical step function with no leakages."""

    def test_explicit_score_step_function(self):
        filler = CareerPortalFiller()
        runner = NativeChromeRunner(skip_list=set(), dry_run=True)

        # 69: Rejected
        p69 = filler.fill_dry_run("https://example.com/69", match_score=69)
        ok69, msg69 = runner.apply_to_job("https://example.com/69", "Role", "Co", "20 LPA", match_score=69)
        assert p69.status == "REJECTED_BELOW_THRESHOLD"
        assert p69.match_score == 69
        assert ok69 is False

        # 70: Accepted
        p70 = filler.fill_dry_run("https://example.com/70", match_score=70)
        ok70, msg70 = runner.apply_to_job("https://example.com/70", "Role", "Co", "20 LPA", match_score=70)
        assert p70.status == "VALIDATED_PAYLOAD"
        assert p70.match_score == 70
        assert ok70 is True

        # 71: Accepted
        p71 = filler.fill_dry_run("https://example.com/71", match_score=71)
        ok71, msg71 = runner.apply_to_job("https://example.com/71", "Role", "Co", "20 LPA", match_score=71)
        assert p71.status == "VALIDATED_PAYLOAD"
        assert p71.match_score == 71
        assert ok71 is True

