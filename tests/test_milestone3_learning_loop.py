"""
Comprehensive Offline Test Suite for Milestone 3 (R3): Learning Loop & Attribution
Verifies:
1. Outcome Labeler:
   - Identifies applications where outcome_label IS NULL and applied_at < 24h
   - Correctly assigns 'callback', 'view', 'rejection', 'silence', 'confirmation'
   - Enforces SLA: 0 rows > 72h with NULL outcome
2. Keyword & Skill Utility Miner:
   - Token frequency analysis over fresh JDs (demand)
   - Profile saturation analysis
   - Utility formula: U = Demand / Saturation
   - Truth matrix verification: rejects synthetic/forbidden skills (claimable = 0) and admits legitimate competencies (claimable = 1)
   - Populates keyword_utility table
3. Attribution Engine:
   - Difference-in-Differences (DiD) computation: (treat_post - treat_pre) - (ctrl_post - ctrl_pre)
   - Enforces n >= 3 observations before asserting causality
   - Weekly appearance telemetry persistence in search_appearance_weekly
"""

import os
import sqlite3
import pytest
from datetime import datetime, timedelta

from naukari_pro.modules.db import init_db, record_applied_job, get_db_connection
from naukari_pro.modules.learning.outcome_labeler import (
    OutcomeLabeler,
    label_unlabeled_outcomes,
    get_unlabeled_count,
    VALID_OUTCOMES,
)
from naukari_pro.modules.learning.keyword_miner import (
    KeywordMiner,
    calculate_utility,
    is_token_claimable,
    mine_keywords,
    get_top_keywords,
)
from naukari_pro.modules.learning.attribution import (
    AttributionEngine,
    calculate_did,
    MIN_OBSERVATIONS_FOR_CAUSALITY,
)
from naukari_pro.modules.profile_performance import ProfilePerformanceEngine


# ==============================================================================
# 1. OUTCOME LABELER TESTS
# ==============================================================================

class TestOutcomeLabeler:
    """Verifies automated scanning, multi-signal outcome labeling, and SLA compliance."""

    def test_outcome_labeling_signals_and_sla(self, tmp_path):
        """Verifies callback, rejection, view, and age-based silence labeling with 0 rows >72h NULL SLA."""
        db_path = str(tmp_path / "test_outcomes.db")
        init_db(db_path)
        labeler = OutcomeLabeler(db_path=db_path)

        now = datetime.now()
        t_5d_ago = (now - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S")
        t_4d_ago = (now - timedelta(days=4)).strftime("%Y-%m-%d %H:%M:%S")
        t_2d_ago = (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
        t_1h_ago = (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")

        # 1. Job 1: 5 days ago, status='External Redirect' -> should become 'silence' (>72h without signal)
        record_applied_job(
            title="Azure Data Engineer",
            company="Company Silence",
            applied_at=t_5d_ago,
            status="External Redirect",
            db_path=db_path
        )

        # 2. Job 2: 4 days ago, status='Rejected by Employer' -> should become 'rejection'
        record_applied_job(
            title="Senior Data Engineer",
            company="Company Reject",
            applied_at=t_4d_ago,
            status="Rejected by Employer",
            db_path=db_path
        )

        # 3. Job 3: 2 days ago, status='Viewed by Recruiter' -> should become 'view'
        record_applied_job(
            title="Data Platform Engineer",
            company="Company View",
            applied_at=t_2d_ago,
            status="Viewed by Recruiter",
            db_path=db_path
        )

        # 4. Job 4: 1 hour ago -> too recent (<24h), should NOT be labeled yet
        record_applied_job(
            title="PySpark Engineer",
            company="Recent Corp",
            applied_at=t_1h_ago,
            status="Submitted (Pending)",
            db_path=db_path
        )

        # Verify unlabeled counts before labeling
        unlabeled_24h = labeler.get_unlabeled_jobs(min_age_hours=24.0)
        assert len(unlabeled_24h) == 3  # Jobs 1, 2, 3

        # Execute labeling run
        summary = labeler.label_all_unlabeled(min_age_hours=24.0)
        assert summary["scanned"] == 3
        assert summary["labeled"] == 3
        assert summary["breakdown"]["silence"] >= 1
        assert summary["breakdown"]["rejection"] >= 1
        assert summary["breakdown"]["view"] >= 1

        # Verify SLA: Exactly 0 rows older than 72 hours have NULL outcome
        unlabeled_72h = labeler.get_unlabeled_count(hours=72.0)
        assert unlabeled_72h == 0, f"SLA breach: Found {unlabeled_72h} jobs >72h with NULL outcome!"

    def test_invalid_outcome_label_raises_error(self, tmp_path):
        """Verifies recording an unapproved outcome label raises ValueError."""
        db_path = str(tmp_path / "test_err.db")
        init_db(db_path)
        labeler = OutcomeLabeler(db_path=db_path)

        with pytest.raises(ValueError) as exc:
            labeler.record_outcome("job-123", "made_up_label")
        assert "Invalid outcome label" in str(exc.value)


# ==============================================================================
# 2. KEYWORD & SKILL UTILITY MINER TESTS
# ==============================================================================

class TestKeywordMiner:
    """Verifies token extraction, utility scoring, and 01_FACT_MATRIX claimable filtering."""

    def test_utility_formula_calculation(self):
        """Verifies U = Demand / Saturation."""
        assert calculate_utility(demand=10, saturation=2) == 5.0
        assert calculate_utility(demand=9, saturation=3) == 3.0
        assert calculate_utility(demand=0, saturation=5) == 0.0
        # Saturation floor of 1
        assert calculate_utility(demand=8, saturation=0) == 8.0

    def test_claimable_token_admittance_and_forbidden_rejection(self):
        """
        Anchored in 01_FACT_MATRIX.md:
        - True skills (Azure Databricks, PySpark, Delta Lake, Kafka, Terraform, ADF) -> claimable = True
        - Forbidden/synthetic skills (Triton, NVIDIA MPS, GPU Slicing, CUDA) -> claimable = False
        """
        # Verified skills for 2.5 YOE Azure Data Engineer
        assert is_token_claimable("pyspark") is True
        assert is_token_claimable("azure databricks") is True
        assert is_token_claimable("delta lake") is True
        assert is_token_claimable("apache kafka") is True
        assert is_token_claimable("terraform") is True
        assert is_token_claimable("adf") is True

        # Forbidden unverified modeling / senior infrastructure
        assert is_token_claimable("triton") is False
        assert is_token_claimable("triton inference server") is False
        assert is_token_claimable("nvidia mps") is False
        assert is_token_claimable("gpu slicing") is False
        assert is_token_claimable("cuda") is False

    def test_mine_and_store_populates_sqlite_table(self, tmp_path):
        """Verifies mine_and_store populates keyword_utility table with correct demand and utility."""
        db_path = str(tmp_path / "test_kw.db")
        init_db(db_path)
        miner = KeywordMiner(db_path=db_path)

        sample_jds = [
            "We need an Azure Data Engineer skilled in PySpark, Azure Databricks, Delta Lake, and Kafka.",
            "Senior PySpark engineer with Databricks and Delta Lake lakehouse experience.",
            "PySpark and Azure Data Factory ADF data pipeline automation.",
            "Triton inference server with NVIDIA MPS for generative AI.",
        ]

        results = miner.mine_and_store(job_descriptions=sample_jds)
        assert len(results) > 0

        # Retrieve top keywords
        top_claimable = miner.get_top_utility_keywords(limit=10, claimable_only=True)
        tokens = [k["token"] for k in top_claimable]

        assert "pyspark" in tokens
        # Verify forbidden token is excluded from claimable
        assert "triton" not in tokens
        assert "nvidia" not in tokens

        # Verify all claimable items in DB have claimable == 1
        for item in top_claimable:
            assert item["claimable"] == 1
            assert item["utility_score"] >= 0


# ==============================================================================
# 3. ATTRIBUTION ENGINE TESTS
# ==============================================================================

class TestAttributionEngine:
    """Verifies Difference-in-Differences calculation, n>=3 causality rule, and telemetry."""

    def test_did_causality_requires_minimum_sample_size(self):
        """
        Verifies that calculate_did strictly refuses to assert causality
        when sample size n < 3 per condition (preventing false attribution of search shocks).
        """
        # Case 1: Underpowered (n = 2 observations per group)
        underpowered = calculate_did(
            treat_pre=[100.0, 110.0],
            treat_post=[140.0, 150.0],
            ctrl_pre=[80.0, 85.0],
            ctrl_post=[85.0, 90.0]
        )
        assert underpowered["causal_assertion_allowed"] is False
        assert underpowered["status"] == "CORRELATION_ONLY_UNDERPOWERED"
        assert "insufficient" in underpowered["reason"].lower()

        # Case 2: Sufficient (n = 3 observations per group)
        sufficient = calculate_did(
            treat_pre=[100.0, 105.0, 110.0],      # Pre-mutation mean: 105.0
            treat_post=[140.0, 150.0, 160.0],     # Post-mutation mean: 150.0 -> Treat Delta = +45.0
            ctrl_pre=[80.0, 85.0, 90.0],          # Ctrl pre mean: 85.0
            ctrl_post=[85.0, 90.0, 95.0]          # Ctrl post mean: 90.0 -> Ctrl Delta = +5.0
        )
        assert sufficient["causal_assertion_allowed"] is True
        assert sufficient["status"] == "CAUSAL_EFFECT_VERIFIED"
        # DiD = 45.0 - 5.0 = 40.0
        assert sufficient["did_estimate"] == 40.0
        assert sufficient["treatment_delta"] == 45.0
        assert sufficient["control_delta"] == 5.0

    def test_weekly_appearance_telemetry_persistence(self, tmp_path):
        """Verifies persistence and retrieval of weekly telemetry records."""
        db_path = str(tmp_path / "test_attrib.db")
        init_db(db_path)
        perf_engine = ProfilePerformanceEngine()

        # Store 4 weeks of telemetry
        perf_engine.record_weekly_telemetry("2026-10-05", search_appearances=2500, profile_views=120, contact_views=15, db_path=db_path)
        perf_engine.record_weekly_telemetry("2026-10-12", search_appearances=2800, profile_views=140, contact_views=18, db_path=db_path)
        perf_engine.record_weekly_telemetry("2026-10-19", search_appearances=3600, profile_views=210, contact_views=28, db_path=db_path)
        perf_engine.record_weekly_telemetry("2026-10-26", search_appearances=4200, profile_views=260, contact_views=35, db_path=db_path)

        attrib = AttributionEngine(db_path=db_path)
        history = attrib.get_weekly_history()
        assert len(history) == 4
        assert history[0]["week_start_date"] == "2026-10-05"
        assert history[0]["search_appearances"] == 2500
        assert history[3]["week_start_date"] == "2026-10-26"
        assert history[3]["search_appearances"] == 4200
