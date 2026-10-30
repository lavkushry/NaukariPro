"""
Adversarial Stress Harness & Generator Test Suite for Milestone 1 (R1)
Empirical verification of:
1. LinkedInTokenRotator across 50 cycles (headline <= 220 chars, all 8 primary tokens preserved).
2. NaukriWhitelist skill swap across 50 cycles (exact 25 count, 7 anchors protected, exactly 1 swap/cycle, pool edge cases).
3. CadenceScheduler jitter distribution (1000 simulated slots strictly within 08:00-13:00 IST envelope).
4. BlacklistValidator baseline defenses (verifying what currently holds).
5. BlacklistValidator adversarial attacks (YOE words, notice period formats, CTC variants, employer variants, workload variations, unicode/zwsp evasions).

Author: Challenger M1_1
Date: 2026-10-30
"""

import json
import random
import unicodedata
import pytest
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo
from typing import List, Generator, Tuple

from naukari_pro.modules.learning.mutator import (
    BlacklistValidator,
    BlacklistViolationError,
    NaukriWhitelist,
    LinkedInWhitelist,
    LinkedInTokenRotator,
    CadenceScheduler,
    HashEngine,
    Platform,
    MutationField,
)

IST_TZ = ZoneInfo("Asia/Kolkata")


# ==============================================================================
# 1. LINKEDIN TOKEN ROTATOR STRESS HARNESS (50 CYCLES)
# ==============================================================================

class TestLinkedInTokenRotatorStress50Cycles:
    """Stress tests LinkedInTokenRotator across 50 full rotation cycles."""

    def test_50_cycles_headline_length_and_all_8_tokens_preserved(self):
        rotator = LinkedInTokenRotator()
        assert len(rotator.PRIMARY_TOKENS) == 8, f"Expected 8 primary tokens, found {len(rotator.PRIMARY_TOKENS)}"

        for cycle in range(50):
            headline = rotator.generate_rotated_headline(rotation_cycle=cycle)
            # 1. Headline length <= 220 chars
            assert len(headline) <= 220, (
                f"Cycle {cycle}: headline length {len(headline)} exceeds 220 characters! "
                f"Content: '{headline}'"
            )
            # 2. Saturated length >= 140 chars
            assert len(headline) >= 140, (
                f"Cycle {cycle}: headline length {len(headline)} is suspiciously short! "
                f"Content: '{headline}'"
            )
            # 3. All 8 primary recruiter tokens preserved verbatim
            for token in rotator.PRIMARY_TOKENS:
                assert token in headline, (
                    f"Cycle {cycle}: Primary token '{token}' missing from headline! "
                    f"Headline: '{headline}'"
                )

    def test_inject_about_sentence_boundary_conditions(self):
        rotator = LinkedInTokenRotator()
        marker = "⚡ CORE TECHNICAL EXPERTISE:\n"
        base_short = f"Azure Data Engineer.\n\n{marker}• PySpark\n• Delta Lake"
        injected = rotator.inject_about_sentence(base_short, "Unity Catalog")
        assert len(injected) <= 2600
        assert "Unity Catalog" in injected

        # Boundary test: base text under 2600 chars, but injection would overflow
        filler = "A" * 2500
        base_long = f"{filler}\n\n{marker}• PySpark"
        assert len(base_long) <= 2600
        # Should gracefully return original base text (length <= 2600) without applying overflowing injection
        result = rotator.inject_about_sentence(base_long, "Unity Catalog")
        assert len(result) <= 2600
        assert result == base_long

    def test_open_to_work_guard_rejects_adversarial_payloads(self):
        # Valid
        assert LinkedInWhitelist.validate_open_to_work({"visibility": "Recruiters only"}) is True
        assert LinkedInWhitelist.validate_open_to_work('{"visibility": "Recruiters only"}') is True

        # Adversarial non-private visibility
        with pytest.raises(BlacklistViolationError):
            LinkedInWhitelist.validate_open_to_work({"visibility": "all_linkedin_members"})

        with pytest.raises(BlacklistViolationError):
            LinkedInWhitelist.validate_open_to_work('{"visibility": "public"}')

        # Corrupted / missing key
        with pytest.raises(BlacklistViolationError):
            LinkedInWhitelist.validate_open_to_work('{"other_key": "value"}')

        with pytest.raises(BlacklistViolationError):
            LinkedInWhitelist.validate_open_to_work('NOT_JSON')


# ==============================================================================
# 2. NAUKRI WHITELIST SKILL SWAP STRESS HARNESS (50 CYCLES)
# ==============================================================================

class TestNaukriSkillSwapStress50Cycles:
    """Stress tests Naukri skill swapping across 50 cycles to verify invariants."""

    @pytest.fixture
    def canonical_25_skills(self) -> List[str]:
        return [
            "Azure Databricks", "PySpark", "Delta Lake", "SQL",
            "Azure Data Factory (ADF)", "Apache Kafka", "Terraform",
            "Python", "ETL Pipelines", "Data Modeling",
            "Data Warehousing", "Azure Synapse Analytics", "ADLS Gen2",
            "Git", "CI/CD", "Docker", "Linux",
            "Data Engineering", "Azure DevOps", "Snowflake",
            "REST APIs", "Data Lakehouse", "Power BI", "Bash", "Airflow"
        ]

    def test_50_cycles_skill_swap_invariants(self, canonical_25_skills):
        current_skills = list(canonical_25_skills)
        assert len(current_skills) == 25
        assert NaukriWhitelist.PROTECTED_ANCHORS.issubset(set(current_skills))

        for cycle in range(50):
            new_skills, dropped, added = NaukriWhitelist.swap_single_skill(current_skills)

            # Invariant 1: Total skill count remains exactly 25
            assert len(new_skills) == 25, (
                f"Cycle {cycle}: total skill count changed to {len(new_skills)}"
            )

            # Invariant 2: The 7 core anchor skills are NEVER swapped out
            for anchor in NaukriWhitelist.PROTECTED_ANCHORS:
                assert anchor in new_skills, (
                    f"Cycle {cycle}: protected anchor '{anchor}' was removed!"
                )
            assert dropped not in NaukriWhitelist.PROTECTED_ANCHORS, (
                f"Cycle {cycle}: dropped skill '{dropped}' is a protected anchor!"
            )

            # Invariant 3: Exactly 1 skill swapped per cycle
            if dropped != added:
                diff_dropped = set(current_skills) - set(new_skills)
                diff_added = set(new_skills) - set(current_skills)
                assert len(diff_dropped) == 1, (
                    f"Cycle {cycle}: expected exactly 1 dropped skill, got {diff_dropped}"
                )
                assert len(diff_added) == 1, (
                    f"Cycle {cycle}: expected exactly 1 added skill, got {diff_added}"
                )

            current_skills = new_skills

    def test_skill_swap_pool_exhaustion_duplicate_risk(self):
        """
        Adversarial Edge Case:
        When current_skills already contains all skills in VALIDATED_SKILL_POOL,
        swap_single_skill falls back to 'dbt', introducing a duplicate skill and reducing unique count to 24.
        """
        skills_saturated = (
            list(NaukriWhitelist.PROTECTED_ANCHORS)
            + list(NaukriWhitelist.VALIDATED_SKILL_POOL)
            + [f"FillerSkill_{i}" for i in range(8)]
        )
        assert len(skills_saturated) == 25
        assert len(set(skills_saturated)) == 25

        new_skills, dropped, added = NaukriWhitelist.swap_single_skill(skills_saturated)
        # Verify if unique count is maintained or if duplicates are introduced
        unique_count = len(set(new_skills))
        assert unique_count == 25, (
            f"VULNERABILITY DETECTED: swap_single_skill introduced duplicate '{added}', "
            f"reducing unique skills from 25 to {unique_count}!"
        )


# ==============================================================================
# 3. CADENCE SCHEDULER ENVELOPE STRESS (1000 SAMPLES)
# ==============================================================================

class TestCadenceSchedulerEnvelopeStress:
    """Simulates 1,000 randomized jitter slots to prove boundary safety."""

    def test_1000_daily_jitter_slots_strictly_within_envelope(self):
        envelope_start = time(8, 0)
        envelope_end = time(13, 0)
        base_date = date(2026, 10, 20)  # Tuesday

        for i in range(1000):
            slot = CadenceScheduler.calculate_daily_jittered_slot(target_date=base_date, seed=i)
            t = slot.time()
            assert envelope_start <= t <= envelope_end, (
                f"Sample {i}: scheduled time {t} is outside envelope [08:00, 13:00] IST!"
            )


# ==============================================================================
# 4. BLACKLIST VALIDATOR BASELINE DEFENSES (VERIFIED PASSING)
# ==============================================================================

class TestBlacklistValidatorBaselineDefenses:
    """Verifies that baseline known attacks are successfully blocked by existing rules."""

    @pytest.mark.parametrize("blocked_text", [
        "Azure Data Engineer with 4 YOE",
        "Senior Data Engineer with 5+ years of experience",
        "Lead Software Engineer",
        "Principal Data Engineer",
        "Current CTC: 30 LPA",
        "Expected CTC: 45 LPA",
        "Serving 60 days notice period",
        "Notice period: 90 days",
        "Ex-Google cloud architect",
        "Worked at Amazon as engineer",
        "Stanford University graduate",
        "IIT Delhi M.Tech degree",
        "Ph.D. in Computer Science",
        "AWS Certified Solutions Architect Professional",
        "Certified Kubernetes Administrator (CKA)",
        "Engineered 12+ production ML models at HFCL",
        "mlops-platform-automation",
        "genai-observability-platform",
    ])
    def test_known_attacks_properly_blocked(self, blocked_text):
        with pytest.raises(BlacklistViolationError):
            BlacklistValidator.enforce(blocked_text, field_name="headline")

    @pytest.mark.parametrize("canonical_truth", [
        "Azure Data Engineer with 2.5 YOE",
        "Current CTC 12 LPA, Expected CTC 22 LPA",
        "Immediate – 15 Days Notice",
        "B.Tech CSE from MDU Rohtak",
        "AZ-900 Certified",
        "Databricks Certified Associate Data Engineer (Pursuing)",
        "CGI India and HFCL Limited experience",
    ])
    def test_canonical_ground_truth_cleanly_permitted(self, canonical_truth):
        # Must NOT raise
        BlacklistValidator.enforce(canonical_truth, field_name="headline")


# ==============================================================================
# 5. ADVERSARIAL GENERATOR ATTACKS AGAINST BLACKLIST VALIDATOR
# ==============================================================================

def generate_yoe_word_attacks() -> Generator[Tuple[str, str], None, None]:
    """Generates subtle YOE inflations using english words instead of digits."""
    word_map = ["three", "four", "five", "six", "seven", "eight", "nine", "ten"]
    suffixes = [
        "years of experience",
        "years experience",
        "years",
        "YOE",
        "yrs",
    ]
    for w in word_map:
        for s in suffixes:
            payload = f"Azure Data Engineer with {w} {s} in cloud platforms"
            yield payload, f"YOE in words: '{w} {s}'"


def generate_notice_period_evasions() -> Generator[Tuple[str, str], None, None]:
    """Generates notice period variations with hyphenation and word formats."""
    # Hyphenated days
    for days in ["30", "45", "60", "90"]:
        yield f"Available with {days}-day notice", f"Hyphenated {days}-day notice"
        yield f"Serving {days}-day notice period", f"Hyphenated serving {days}-day notice"
    # Word months
    for m in ["one", "two", "three"]:
        yield f"Notice period: {m} month notice", f"Word month '{m} month'"
        yield f"Available in {m} months", f"Word months 'in {m} months'"


def generate_ctc_evasions() -> Generator[Tuple[str, str], None, None]:
    """Generates CTC fabrications with sentence filler words bypassing regex colons."""
    for amount in ["30", "35", "40", "50"]:
        yield f"Current CTC is {amount} LPA", f"Filler 'is': Current CTC is {amount} LPA"
        yield f"Expected CTC is {amount} LPA", f"Filler 'is': Expected CTC is {amount} LPA"
        yield f"CTC: {amount} LPA", f"Missing 'Current': CTC: {amount} LPA"
        yield f"Annual CTC: {amount} LPA", f"Prefix 'Annual': Annual CTC: {amount} LPA"
        yield f"Fixed compensation: {amount} LPA", f"Fixed compensation: {amount} LPA"


def generate_employer_evasions() -> Generator[Tuple[str, str], None, None]:
    """Generates unapproved employer claims with title or sentence structures."""
    for comp in ["Google", "Amazon", "Apple", "Uber", "Netflix", "Databricks", "Meta"]:
        yield f"Senior at {comp}", f"Title: Senior at {comp}"
        yield f"Engineer at {comp}", f"Role: Engineer at {comp}"
        yield f"Joined {comp} as Platform Engineer", f"Joined {comp}"
        yield f"Former {comp} Data Engineer", f"Former {comp}"


def generate_workload_evasions() -> Generator[Tuple[str, str], None, None]:
    """Generates workload conversion claims without mandatory 'production' word or '+' symbol."""
    for count in ["12", "15", "16", "20"]:
        yield f"Deployed {count} ML models at HFCL", f"Omitted 'production': {count} ML models at HFCL"
        yield f"Engineered {count} ML microservices at HFCL", f"Omitted '+': {count} ML microservices at HFCL"


def generate_unicode_evasions() -> Generator[Tuple[str, str], None, None]:
    """Generates zero-width space and full-width Unicode characters to bypass regex word boundaries."""
    # Zero-width space (\u200b) injection
    yield "3\u200byears experience", "Zero-width space in '3 years'"
    yield "3\u200b0 days notice", "Zero-width space in '30 days'"
    yield "Ex\u200b-Google engineer", "Zero-width space in 'Ex-Google'"
    yield "Stan\u200bford University", "Zero-width space in 'Stanford'"

    # Full-width Unicode characters (NFKD / NFKC)
    fullwidth_3_years = "\uff13 years experience"  # ３ years experience
    yield fullwidth_3_years, "Full-width digit '３ years'"

    fullwidth_ex_google = "\uff25\uff58\uff0d\uff27\uff4f\uff4f\uff47\uff4c\uff45"  # Ｅｘ－Ｇｏｏｇｌｅ
    yield fullwidth_ex_google, "Full-width letters 'Ｅｘ－Ｇｏｏｇｌｅ'"


class TestBlacklistValidatorAdversarialAttacks:
    """
    Adversarial challenge test battery attacking BlacklistValidator.
    Each test asserts that BlacklistValidator.enforce MUST reject the payload.
    Any failure indicates an empirical vulnerability in fact validation.
    """

    @pytest.mark.parametrize("payload, attack_vector", list(generate_yoe_word_attacks())[:10])
    def test_subtle_yoe_in_words_must_be_blocked(self, payload, attack_vector):
        with pytest.raises(BlacklistViolationError, match=r"YOE|Candidate fact integrity"):
            BlacklistValidator.enforce(payload, field_name="headline")

    @pytest.mark.parametrize("payload, attack_vector", list(generate_notice_period_evasions()))
    def test_notice_period_evasions_must_be_blocked(self, payload, attack_vector):
        with pytest.raises(BlacklistViolationError, match=r"Notice Period|Candidate fact integrity"):
            BlacklistValidator.enforce(payload, field_name="notice_period")

    @pytest.mark.parametrize("payload, attack_vector", list(generate_ctc_evasions()))
    def test_ctc_fabrication_evasions_must_be_blocked(self, payload, attack_vector):
        with pytest.raises(BlacklistViolationError, match=r"CTC|Candidate fact integrity"):
            BlacklistValidator.enforce(payload, field_name="ctc")

    @pytest.mark.parametrize("payload, attack_vector", list(generate_employer_evasions()))
    def test_employer_claims_must_be_blocked(self, payload, attack_vector):
        with pytest.raises(BlacklistViolationError, match=r"Employer|Candidate fact integrity"):
            BlacklistValidator.enforce(payload, field_name="employer")

    @pytest.mark.parametrize("payload, attack_vector", list(generate_workload_evasions()))
    def test_workload_conversions_must_be_blocked(self, payload, attack_vector):
        with pytest.raises(BlacklistViolationError, match=r"Workload|Candidate fact integrity"):
            BlacklistValidator.enforce(payload, field_name="workload")

    @pytest.mark.parametrize("payload, attack_vector", list(generate_unicode_evasions()))
    def test_unicode_evasions_must_be_blocked(self, payload, attack_vector):
        with pytest.raises(BlacklistViolationError, match=r"Candidate fact integrity"):
            BlacklistValidator.enforce(payload, field_name="unicode_attack")
