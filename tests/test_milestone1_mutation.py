"""
Comprehensive Offline Test Suite for Milestone 1 (R1: Resdex SEO Saturation and Controlled Profile Mutation Engine)
Target Subsystems:
- naukari_pro/modules/learning/mutator.py (BlacklistValidator, NaukriWhitelist, LinkedInTokenRotator, HashEngine, CadenceScheduler, ProfileMutator)
- naukari_pro/modules/db.py (profile_mutations table, indexes, ledger methods)
- naukari_pro/modules/profile_enhancer.py (Two-tier bump and mutator integration)
- naukari_pro/modules/linkedin_optimizer.py (Token rotation and About injection integration)
- scripts/sync_naukri_live_profile.py (execute_controlled_sync_field and wrapped sync methods)

100% Offline Socket Compliance: Uses in-memory or temporary SQLite databases and mock fixtures.
"""

import os
import json
import sqlite3
import pytest
from datetime import datetime, date, time, timezone, timedelta
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

from naukari_pro.modules.learning.mutator import (
    BlacklistValidator,
    BlacklistViolationError,
    NaukriWhitelist,
    LinkedInWhitelist,
    LinkedInTokenRotator,
    HashEngine,
    CadenceScheduler,
    ProfileMutator,
    MutationProposal,
    MutationResult,
    MutationStatus,
    Platform,
    MutationField,
)
from naukari_pro.modules.db import (
    init_db,
    init_mutations_db,
    record_profile_mutation,
    get_weekly_mutation_count,
    can_apply_keyword_mutation,
    get_latest_mutation,
    revert_profile_mutation,
    compute_field_hash,
    get_db_connection,
)
from scripts.sync_naukri_live_profile import execute_controlled_sync_field
from naukari_pro.modules.profile_enhancer import ProfileEnhancerEngine
from naukari_pro.modules.linkedin_optimizer import (
    get_rotated_headline,
    get_injected_about,
    rotate_and_record_headline,
)

IST_TZ = ZoneInfo("Asia/Kolkata")


@pytest.fixture
def test_db(tmp_path):
    """Provides an isolated SQLite database file with all schemas initialized."""
    db_file = str(tmp_path / "test_applied_jobs.db")
    init_db(db_file)
    return db_file


# ==============================================================================
# SECTION 1: BLACKLIST VALIDATOR ADVERSARIAL REJECTION TESTS
# ==============================================================================

class TestBlacklistValidatorAdversarial:
    """Tests strict rejection of any attempt to mutate protected facts defined in 01_FACT_MATRIX.md."""

    @pytest.mark.parametrize("failing_text, expected_category", [
        ("Azure Data Engineer with 5+ years of experience in distributed systems", "YOE Inflation"),
        ("Senior Data Engineer with 4 YOE", "YOE Inflation"),
        ("Lead MLOps Engineer scaling platforms", "YOE Inflation"),
        ("Principal Platform Engineer with 8 YOE", "YOE Inflation"),
        ("Over a decade of experience across cloud architectures", "YOE Inflation"),
        ("Current CTC: 35 LPA | Fixed component: 30 LPA", "CTC Fabrication"),
        ("Expected CTC: 50 LPA for GCC roles", "CTC Fabrication"),
        ("Serving 60 days notice period", "Notice Period Distortion"),
        ("Notice Period: 90 Days", "Notice Period Distortion"),
        ("Immediate to 30 Days Notice", "Notice Period Distortion"),
        ("Available in 3 months notice", "Notice Period Distortion"),
        ("Ex-Google | Ex-Amazon | Cloud Data Architect", "Employer Fabrication"),
        ("Previously worked at Microsoft as Lead Engineer", "Employer Fabrication"),
        ("M.Tech in Artificial Intelligence from IIT Bombay", "Education Inflation"),
        ("MS in Computer Science from Stanford University", "Education Inflation"),
        ("Ph.D. in Computer Engineering from MIT", "Education Inflation"),
        ("AWS Certified Solutions Architect Professional (SAP-C02)", "Unverified Certification"),
        ("Certified Kubernetes Administrator (CKA)", "Unverified Certification"),
        ("GCP Professional Cloud Architect", "Unverified Certification"),
        ("Engineered 12+ production ML models at HFCL Limited", "Synthetic Workload Conversion"),
        ("Deployed 15+ production ML microservices at HFCL", "Synthetic Workload Conversion"),
        ("Instrumented Triton inference server at HFCL", "Synthetic Workload Conversion"),
        ("Implemented NVIDIA MPS dynamic batching at HFCL", "Synthetic Workload Conversion"),
        ("Engineered model inference logging at CGI India", "Synthetic Workload Conversion"),
        ("Automated model validation gates at HFCL", "Synthetic Workload Conversion"),
        ("Repo link: github.com/lavkushry/mlops-platform-automation", "Ghost Repository Reference"),
        ("Refer to repo github.com/lavkushry/genai-observability-platform", "Ghost Repository Reference"),
    ])
    def test_adversarial_rejections(self, failing_text, expected_category):
        with pytest.raises(BlacklistViolationError) as exc_info:
            BlacklistValidator.enforce(failing_text, field_name="test_field")
        assert expected_category in str(exc_info.value)

    @pytest.mark.parametrize("forbidden_field", [
        "yoe", "experience", "total_experience", "ctc", "salary",
        "notice_period", "employment_dates", "company", "employer",
        "education", "certifications"
    ])
    def test_forbidden_field_targeting_rejected(self, forbidden_field):
        with pytest.raises(BlacklistViolationError) as exc_info:
            BlacklistValidator.enforce("Some text", field_name=forbidden_field, check_field_immutability=True)
        assert "immutable" in str(exc_info.value).lower()

    def test_canonical_candidate_facts_accepted(self):
        """Verifies that truthful facts from 01_FACT_MATRIX.md pass blacklist verification cleanly."""
        valid_headline = (
            "Azure Data Engineer | Azure Databricks · PySpark · Delta Lake · "
            "Azure Data Factory (ADF) · SQL · Apache Kafka · Terraform · Medallion Architecture | "
            "Certified AZ-900 · Databricks Associate (Pursuing) | 2.5 YOE Cloud Data Platforms & CI/CD"
        )
        BlacklistValidator.enforce(valid_headline, field_name="headline")

        valid_summary = (
            "Azure Data Engineer with 2.5 YOE designing, deploying, and maintaining production data platforms "
            "and streaming pipelines. Experienced with CGI India and HFCL Limited."
        )
        BlacklistValidator.enforce(valid_summary, field_name="summary")

        valid_notice = "15 Days or less"
        BlacklistValidator.enforce(valid_notice, field_name="notice_period_status")


# ==============================================================================
# SECTION 2: NAUKRI WHITELIST INVARIANTS TESTS
# ==============================================================================

class TestNaukriWhitelistInvariants:
    """Tests Naukri Resdex whitelist rules: headline limits, skill swap, summary rephrase."""

    def test_headline_length_boundary_and_saturation(self):
        for cycle in range(5):
            hl = NaukriWhitelist.rephrase_headline(cycle=cycle)
            assert len(hl) <= 250, f"Cycle {cycle} headline exceeds 250 chars ({len(hl)})"
            assert len(hl) >= 200, f"Cycle {cycle} headline lacks saturation ({len(hl)})"
            assert "Azure Data Engineer" in hl
            assert "2.5 YOE" in hl

    def test_key_skills_reorder_preserves_exact_set(self):
        skills = [
            "Azure Databricks", "PySpark", "Delta Lake", "SQL",
            "Azure Data Factory (ADF)", "Apache Kafka", "Terraform", "PostgreSQL"
        ]
        scores = {"Terraform": 0.95, "Delta Lake": 0.88, "SQL": 0.70}
        reordered = NaukriWhitelist.reorder_key_skills(skills, utility_scores=scores)
        assert len(reordered) == len(skills)
        assert set(reordered) == set(skills)
        assert reordered[0] == "Terraform"
        assert reordered[1] == "Delta Lake"

    def test_single_skill_swap_protects_anchors_and_maintains_count(self):
        initial_skills = [
            "Azure Databricks", "PySpark", "Delta Lake", "SQL", "Azure Data Factory (ADF)",
            "Apache Kafka", "Terraform", "Python", "ETL Pipelines", "Medallion Architecture",
            "ADLS Gen2", "Azure Synapse Analytics", "Microsoft Fabric", "dbt",
            "Change Data Capture (CDC)", "Docker", "CI/CD", "Azure DevOps", "PostgreSQL",
            "Data Modeling", "Star Schema Data Modeling", "DataOps", "Great Expectations",
            "Bash", "Linux"
        ]
        assert len(initial_skills) == 25

        new_skills, dropped, added = NaukriWhitelist.swap_single_skill(
            current_skills=initial_skills,
            drop_skill="Bash",
            add_skill="Unity Catalog"
        )
        assert len(new_skills) == 25
        assert dropped == "Bash"
        assert added == "Unity Catalog"
        assert "Unity Catalog" in new_skills
        assert "Bash" not in new_skills

        # Protected anchors must NEVER be dropped
        for anchor in NaukriWhitelist.PROTECTED_ANCHORS:
            assert anchor in new_skills

    def test_single_skill_swap_refuses_to_drop_protected_anchor(self):
        initial_skills = [
            "Azure Databricks", "PySpark", "Delta Lake", "SQL", "Azure Data Factory (ADF)",
            "Apache Kafka", "Terraform", "Linux"
        ]
        # Attempt to drop "Azure Databricks" (protected anchor)
        new_skills, dropped, added = NaukriWhitelist.swap_single_skill(
            current_skills=initial_skills,
            drop_skill="Azure Databricks",
            add_skill="Unity Catalog"
        )
        assert "Azure Databricks" in new_skills, "Protected anchor was erroneously dropped!"
        assert dropped != "Azure Databricks", "Drop target must fallback to non-protected skill"

    def test_summary_sentence_rephrase_preserves_remaining_sentences(self):
        base_summary = (
            "Azure Data Engineer with 2.5 YOE designing scalable cloud platforms. "
            "Built legacy pipelines with standard processing tools. "
            "Certified in Azure Fundamentals with strong CI/CD knowledge."
        )
        new_summary = NaukriWhitelist.rephrase_summary_sentence(
            current_summary=base_summary,
            target_sentence_index=1,
            cycle=0
        )
        assert "Azure Data Engineer with 2.5 YOE" in new_summary
        assert "Certified in Azure Fundamentals" in new_summary
        assert "Built legacy pipelines" not in new_summary
        assert len(new_summary) > 100


# ==============================================================================
# SECTION 3: LINKEDIN WHITELIST & TOKEN ROTATOR TESTS
# ==============================================================================

class TestLinkedInWhitelistAndTokenRotator:
    """Tests LinkedIn token rotation, character limits, and About sentence injection."""

    def test_rotated_headline_preserves_all_8_primary_tokens(self):
        rotator = LinkedInTokenRotator()
        for cycle in range(10):
            hl = rotator.generate_rotated_headline(rotation_cycle=cycle)
            assert len(hl) <= 220, f"Cycle {cycle} headline exceeds 220 chars ({len(hl)})"
            for prim in rotator.PRIMARY_TOKENS:
                assert prim in hl, f"Cycle {cycle} missing primary recruiter token '{prim}'"

    def test_about_sentence_injection_strictly_under_2600_chars(self):
        rotator = LinkedInTokenRotator()
        base_about = (
            "Results-driven Azure Data Engineer with 2.5 YOE building enterprise Lakehouse platforms.\n\n"
            "⚡ CORE TECHNICAL EXPERTISE:\n"
            "• Azure Databricks, PySpark, Delta Lake, Azure Data Factory (ADF)\n"
            "• SQL, Apache Kafka, Terraform, CI/CD\n\n"
            "Key Focus: High-throughput data streaming."
        )
        injected = rotator.inject_about_sentence(base_about, claimable_token="Unity Catalog")
        assert len(injected) <= 2600
        assert "Unity Catalog" in injected
        assert "table lineage tracking" in injected

    def test_open_to_work_guard_enforces_recruiters_only(self):
        valid_payload = json.dumps({"visibility": "Recruiters only", "job_titles": ["Azure Data Engineer"]})
        assert LinkedInWhitelist.validate_open_to_work(valid_payload) is True

        invalid_payload = json.dumps({"visibility": "all_linkedin_members", "job_titles": ["Azure Data Engineer"]})
        with pytest.raises(BlacklistViolationError):
            LinkedInWhitelist.validate_open_to_work(invalid_payload)

    def test_weekly_activity_signal_structure(self):
        sig = LinkedInWhitelist.generate_weekly_activity_signal()
        assert sig["day"] == "Wednesday"
        assert sig["action"] == "like_technical_post"
        assert "Databricks" in sig["target_publisher"]


# ==============================================================================
# SECTION 4: HASH ENGINE DETERMINISM TESTS
# ==============================================================================

class TestHashEngineDeterminism:
    """Tests cryptographic SHA-256 calculation and canonical normalization."""

    def test_crlf_vs_lf_produces_identical_hash(self):
        t1 = "Line 1\r\nLine 2\r\n"
        t2 = "Line 1\nLine 2\n"
        assert HashEngine.compute_text_hash(t1) == HashEngine.compute_text_hash(t2)

    def test_outer_whitespace_produces_identical_hash(self):
        t1 = "  Azure Data Engineer  "
        t2 = "Azure Data Engineer"
        assert HashEngine.compute_text_hash(t1) == HashEngine.compute_text_hash(t2)

    def test_empty_or_none_string_produces_empty_hash(self):
        expected_empty = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert HashEngine.compute_text_hash("") == expected_empty
        assert HashEngine.compute_text_hash(None) == expected_empty

    def test_unordered_list_hash_invariance(self):
        l1 = ["SQL", "PySpark", "Kafka"]
        l2 = ["Kafka", "SQL", "PySpark"]
        assert HashEngine.compute_list_hash(l1, ordered=False) == HashEngine.compute_list_hash(l2, ordered=False)

    def test_canonical_dict_hash_key_order_invariance(self):
        d1 = {"b": 2, "a": 1}
        d2 = {"a": 1, "b": 2}
        assert HashEngine.compute_dict_hash(d1) == HashEngine.compute_dict_hash(d2)


# ==============================================================================
# SECTION 5: CADENCE SCHEDULER & JITTER TESTS
# ==============================================================================

class TestCadenceSchedulerAndJitter:
    """Tests dual-tier rate limiting and jitter calculation envelope."""

    def test_active_cadence_days_classification(self):
        # 2026-10-26 is Monday, 27 is Tue, 28 is Wed, 29 is Thu, 30 is Fri
        mon = datetime(2026, 10, 26, 10, 0, tzinfo=IST_TZ)
        tue = datetime(2026, 10, 27, 10, 0, tzinfo=IST_TZ)
        wed = datetime(2026, 10, 28, 10, 0, tzinfo=IST_TZ)
        thu = datetime(2026, 10, 29, 10, 0, tzinfo=IST_TZ)
        fri = datetime(2026, 10, 30, 10, 0, tzinfo=IST_TZ)

        assert CadenceScheduler.is_active_cadence_day(mon) is False
        assert CadenceScheduler.is_active_cadence_day(tue) is True
        assert CadenceScheduler.is_active_cadence_day(wed) is True
        assert CadenceScheduler.is_active_cadence_day(thu) is True
        assert CadenceScheduler.is_active_cadence_day(fri) is False

    def test_jitter_slot_stays_within_envelope(self):
        test_d = date(2026, 10, 27)  # Tuesday
        for seed in range(50):
            slot = CadenceScheduler.calculate_daily_jittered_slot(target_date=test_d, seed=seed)
            assert slot.date() == test_d
            # Envelope must be strictly within 08:00 to 13:00 IST
            assert time(8, 0) <= slot.time() <= time(13, 0)

    def test_weekly_keyword_mutation_rate_limiting(self, test_db):
        ref_dt = datetime(2026, 10, 28, 10, 0, tzinfo=IST_TZ)  # Wednesday

        # Slot 1: Allowed
        can, count, _ = can_apply_keyword_mutation("naukri", max_weekly=2, reference_date=ref_dt, db_path=test_db)
        assert can is True
        assert count == 0

        record_profile_mutation(
            platform="naukri",
            field="headline",
            new_value="Headline V1",
            old_value="Headline V0",
            is_keyword_mutation=True,
            applied_at="2026-10-27 04:30:00",
            db_path=test_db
        )

        # Slot 2: Allowed
        can, count, _ = can_apply_keyword_mutation("naukri", max_weekly=2, reference_date=ref_dt, db_path=test_db)
        assert can is True
        assert count == 1

        record_profile_mutation(
            platform="naukri",
            field="key_skills",
            new_value="Skill V2",
            old_value="Skill V1",
            is_keyword_mutation=True,
            applied_at="2026-10-28 05:00:00",
            db_path=test_db
        )

        # Slot 3: BLOCKED
        can, count, reason = can_apply_keyword_mutation("naukri", max_weekly=2, reference_date=ref_dt, db_path=test_db)
        assert can is False
        assert count == 2
        assert "limit reached" in reason.lower()


# ==============================================================================
# SECTION 6: DATABASE LEDGER & PERSISTENCE TESTS
# ==============================================================================

class TestDatabaseLedgerPersistence:
    """Tests profile_mutations table creation, indexes, insertions, and rollbacks."""

    def test_schema_and_indexes_exist(self, test_db):
        conn = get_db_connection(test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='profile_mutations'")
        assert cursor.fetchone() is not None

        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_mut_%'")
        indexes = [row[0] for row in cursor.fetchall()]
        assert "idx_mut_platform_time" in indexes
        assert "idx_mut_kw_platform_time" in indexes
        conn.close()

    def test_record_profile_mutation_dual_return_type(self, test_db):
        res = record_profile_mutation(
            platform="naukri",
            field="headline",
            old_value="Old Headline",
            new_value="New Saturated Headline",
            rationale="seo_saturation",
            expected_effect="boost_impressions",
            db_path=test_db
        )
        # 1. Usable as int
        assert res > 0
        assert isinstance(res, int)

        # 2. Unpackable as tuple
        ok, mid, msg = res
        assert ok is True
        assert mid > 0
        assert "successfully" in msg.lower()

    def test_noop_detection_rejects_identical_hash(self, test_db):
        res = record_profile_mutation(
            platform="naukri",
            field="headline",
            old_value="Identical Text",
            new_value="Identical Text",
            is_keyword_mutation=True,
            db_path=test_db
        )
        assert not res
        ok, mid, msg = res
        assert ok is False
        assert mid == -1
        assert "no-op" in msg.lower()

    def test_get_latest_mutation_and_revert(self, test_db):
        res = record_profile_mutation(
            platform="linkedin",
            field="about",
            old_value="Old About",
            new_value="New Injected About",
            rationale="about_injection",
            expected_effect="boost_discoverability",
            db_path=test_db
        )
        mut_id = int(res)

        latest = get_latest_mutation("linkedin", field="about", db_path=test_db)
        assert latest is not None
        assert latest["new_value"] == "New Injected About"
        assert latest["status"] == "APPLIED"

        # Revert mutation
        rev_ok = revert_profile_mutation(mut_id, reason="A/B test rollback", db_path=test_db)
        assert rev_ok is True

        latest_after = get_latest_mutation("linkedin", field="about", db_path=test_db)
        assert latest_after is None, "Reverted mutation must not be returned as APPLIED"


# ==============================================================================
# SECTION 7: INTEGRATION HOOKS TESTS
# ==============================================================================

class TestIntegrationHooks:
    """Tests integration between controlled mutator, sync scripts, and optimizers."""

    def test_execute_controlled_sync_field_wrapper(self, test_db):
        mock_page = MagicMock()
        dom_store = {"headline": "Old Live Headline"}

        def mock_read(p):
            return dom_store["headline"]

        def mock_write(p, val):
            dom_store["headline"] = val
            return True

        mutator = ProfileMutator(db_path=test_db)
        new_headline = (
            "Azure Data Engineer | Azure Databricks · PySpark · Delta Lake · "
            "Azure Data Factory (ADF) · SQL · Apache Kafka · Terraform · Medallion Architecture | "
            "Certified AZ-900 · Databricks Associate (Pursuing) | 2.5 YOE Cloud Data Platforms & CI/CD"
        )

        ok = execute_controlled_sync_field(
            page=mock_page,
            field_name="headline",
            new_value=new_headline,
            dom_read_fn=mock_read,
            dom_write_fn=mock_write,
            rationale="test_sync",
            expected_effect="boost_discoverability",
            mutator=mutator
        )
        assert ok is True
        assert dom_store["headline"] == new_headline

        # Verify entry written to ledger
        latest = get_latest_mutation("naukri", field="headline", db_path=test_db)
        assert latest is not None
        assert latest["new_value"] == new_headline

    def test_execute_controlled_sync_field_rejects_blacklist(self):
        mock_page = MagicMock()
        with pytest.raises(BlacklistViolationError):
            execute_controlled_sync_field(
                page=mock_page,
                field_name="headline",
                new_value="Azure Data Engineer with 10 YOE",
                dom_read_fn=lambda p: "",
                dom_write_fn=lambda p, v: True
            )

    def test_profile_enhancer_two_tier_execution(self, test_db):
        mock_page = MagicMock()
        mutator = ProfileMutator(db_path=test_db)
        enhancer = ProfileEnhancerEngine(mutator=mutator)

        # Mock page DOM elements
        mock_textarea = MagicMock()
        mock_textarea.input_value.return_value = "Short Old Headline"
        mock_textarea.is_visible.return_value = True
        mock_textarea.first = mock_textarea

        mock_save = MagicMock()
        mock_save.count.return_value = 1
        mock_save.is_visible.return_value = True
        mock_save.first = mock_save

        mock_edit = MagicMock()
        mock_edit.count.return_value = 1
        mock_edit.first = mock_edit

        mock_page.locator.side_effect = lambda sel: (
            mock_edit if "edit" in sel.lower()
            else mock_textarea if "textarea" in sel.lower()
            else mock_save
        )
        mock_page.get_by_role.return_value = mock_save
        mock_page.url = "https://www.naukri.com/mnjuser/profile"

        success = enhancer.bump_profile(mock_page, force=True)
        assert success is True

        # Verify mutation was recorded to ledger
        latest = get_latest_mutation("naukri", field="headline", db_path=test_db)
        assert latest is not None
        assert len(latest["new_value"]) >= 200

    def test_linkedin_optimizer_helper_functions(self, test_db):
        # 1. get_rotated_headline
        hl = get_rotated_headline(cycle=0)
        assert len(hl) <= 220
        assert "Azure Data Engineer" in hl

        # 2. get_injected_about
        abt = get_injected_about("Unity Catalog")
        assert len(abt) <= 2600
        assert "Unity Catalog" in abt

        # 3. rotate_and_record_headline
        new_hl, mid = rotate_and_record_headline(cycle=1, db_path=test_db)
        assert mid > 0
        latest = get_latest_mutation("linkedin", field="headline", db_path=test_db)
        assert latest is not None
        assert latest["new_value"] == new_hl
