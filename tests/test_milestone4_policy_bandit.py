"""
Comprehensive Offline Test Suite for Milestone 4 (R4): LinUCB Contextual Bandit Selection Policy
Verifies:
1. 7-Dimensional Context Vector:
   - Validates dimension (len == 7) and normalization bounds [0.0, 1.0]
   - Correctly processes match score, YOE, age, tier, ATS platform, skill overlap, and salary
2. LinUCB Policy Execution:
   - Exploration factor alpha = 0.2
   - Inverse matrix calculation and Upper Confidence Bound evaluation
   - Action selection among APPLY (0), SKIP (1), and DEFER_TO_REVIEW (2)
3. Reward Updating & Closed-Loop Learning:
   - Applies exact reward schedule (+1.0 callback, +0.3 view, -1.0 rejection, -0.2 silence, -2.0 duplicate)
   - Online updates to covariance matrix A_a and reward vector b_a
   - Positive feedback reinforces high-converting vacancy contexts
4. Cold-Start Bootstrap & Serialization:
   - Bootstraps parameters from historical SQLite applied_jobs
   - Full round-trip weights persistence to JSON
"""

import os
import json
import tempfile
import pytest

from naukari_pro.modules.db import init_db, record_applied_job
from naukari_pro.modules.learning.policy import (
    LinUCBBanditPolicy,
    PolicyAction,
    extract_context_vector,
    REWARD_SCHEDULE,
    DEFAULT_ALPHA,
    CONTEXT_DIMENSION,
)


class TestContextVectorExtraction:
    """Verifies feature engineering and normalization of 7-dimensional context vector."""

    def test_context_vector_dimension_and_bounds(self):
        """Context vector must have exactly 7 dimensions, all bounded in [0.0, 1.0]."""
        job = {
            "match_score": 85.0,
            "required_yoe": 3.0,
            "posting_age_hours": 12.0,
            "company": "Microsoft GCC",
            "platform": "Naukri 1-Click",
            "jd": "Azure Databricks PySpark Delta Lake Kafka ADF SQL Terraform",
            "salary_lpa": 28.0,
        }
        x = extract_context_vector(job)
        assert len(x) == CONTEXT_DIMENSION
        for i, val in enumerate(x):
            assert 0.0 <= val <= 1.0, f"Feature index {i} out of bounds: {val}"

        # Match score 85 -> 0.85
        assert x[0] == 0.85
        # YOE 3.0 -> 0.3
        assert x[1] == 0.3
        # Age 12h -> 12 / 168 = 0.0714
        assert abs(x[2] - 12.0 / 168.0) < 1e-4
        # Company Microsoft -> Tier 1 GCC = 1.0
        assert x[3] == 1.0
        # Platform 1-Click -> 1.0
        assert x[4] == 1.0
        # Skill overlap: all 7 present -> 1.0
        assert x[5] == 1.0
        # Salary 28 -> 28 / 40 = 0.7
        assert x[6] == 0.7

    def test_context_vector_extreme_and_missing_values(self):
        """Verifies graceful handling and capping of missing or out-of-range inputs."""
        empty_job = {}
        x_empty = extract_context_vector(empty_job)
        assert len(x_empty) == CONTEXT_DIMENSION
        for val in x_empty:
            assert 0.0 <= val <= 1.0

        # Capped high values
        extreme_job = {
            "match_score": 150.0,
            "required_yoe": 25.0,
            "posting_age_hours": 500.0,
            "salary_lpa": 100.0,
        }
        x_extreme = extract_context_vector(extreme_job)
        assert x_extreme[0] == 1.0  # Capped at 1.0
        assert x_extreme[1] == 1.0  # Capped at 1.0
        assert x_extreme[2] == 1.0  # Capped at 1.0
        assert x_extreme[6] == 1.0  # Capped at 1.0


class TestLinUCBBanditPolicy:
    """Verifies LinUCB action selection, reward updates, and bootstrap."""

    def test_policy_initialization_and_action_space(self):
        """Verifies default alpha=0.2, dimension=7, and identity design matrices."""
        policy = LinUCBBanditPolicy(alpha=0.2)
        assert policy.alpha == 0.2
        assert policy.d == 7

        for a in policy.actions:
            a_idx = int(a)
            # A_a is 7x7 identity matrix
            assert len(policy.A[a_idx]) == 7
            assert policy.A[a_idx][0][0] == 1.0
            assert policy.A[a_idx][0][1] == 0.0
            # b_a is 7-dim zero vector
            assert len(policy.b[a_idx]) == 7
            assert all(v == 0.0 for v in policy.b[a_idx])

    def test_predict_ucb_and_action_selection(self):
        """Verifies UCB prediction and action selection on an incoming job posting."""
        policy = LinUCBBanditPolicy(alpha=0.2)
        job = {
            "match_score": 90.0,
            "required_yoe": 2.5,
            "company": "Walmart Global Tech",
            "platform": "1-Click Direct",
            "jd": "Azure Databricks PySpark Delta Lake SQL",
            "salary_lpa": 24.0
        }

        action, ucb_score, diag = policy.select_action(job)
        assert action in (PolicyAction.APPLY, PolicyAction.SKIP, PolicyAction.DEFER_TO_REVIEW)
        assert ucb_score > 0
        assert "context_vector" in diag
        assert diag["policy_version"] == "v2.0-linucb"

    def test_reward_update_adapts_policy_preferences(self):
        """
        Closed-loop verification:
        When APPLY receives positive callback rewards (+1.0),
        its expected payoff and UCB strictly increase relative to unrewarded actions.
        """
        policy = LinUCBBanditPolicy(alpha=0.2)
        x = [0.85, 0.25, 0.1, 1.0, 1.0, 0.8, 0.6]

        # Initial payoff for APPLY is 0.0
        _, payoff_pre, _ = policy.predict_ucb(x, PolicyAction.APPLY)
        assert payoff_pre == 0.0

        # Observe multiple positive callbacks for APPLY
        policy.update_from_outcome(x, PolicyAction.APPLY, "callback")
        policy.update_from_outcome(x, PolicyAction.APPLY, "callback")

        # Payoff after positive callbacks must strictly increase
        _, payoff_post, _ = policy.predict_ucb(x, PolicyAction.APPLY)
        assert payoff_post > payoff_pre, "Payoff failed to increase after callback rewards!"

        # Observe rejection for SKIP on same context -> APPLY should be strongly preferred
        policy.update_from_outcome(x, PolicyAction.SKIP, "rejection")
        best_action, _, _ = policy.select_action({"match_score": 85, "company": "Microsoft"})
        assert best_action == PolicyAction.APPLY

    def test_cold_start_bootstrap_from_sqlite(self, tmp_path):
        """Verifies policy bootstraps historical records from applied_jobs database."""
        db_path = str(tmp_path / "test_bootstrap.db")
        init_db(db_path)

        # Seed 3 historical applications with outcomes
        record_applied_job(title="Azure Data Engineer", company="Walmart", status="Submitted", db_path=db_path)
        record_applied_job(title="Data Platform Engineer", company="Microsoft", status="Submitted", db_path=db_path)

        # Update their outcomes in DB
        from naukari_pro.modules.learning.outcome_labeler import OutcomeLabeler
        labeler = OutcomeLabeler(db_path=db_path)
        jobs = labeler.get_unlabeled_jobs(min_age_hours=0.0)
        assert len(jobs) >= 2
        labeler.record_outcome(jobs[0]["job_id"], "callback")
        labeler.record_outcome(jobs[1]["job_id"], "view")

        # Bootstrap policy
        policy = LinUCBBanditPolicy(alpha=0.2)
        updated = policy.bootstrap_from_history(db_path=db_path)
        assert updated >= 2

        # Verify design matrices are non-identity after bootstrap
        assert policy.A[int(PolicyAction.APPLY)][0][0] > 1.0
        assert sum(abs(v) for v in policy.b[int(PolicyAction.APPLY)]) > 0.0

    def test_policy_weights_round_trip_serialization(self, tmp_path):
        """Verifies saving and reloading policy parameters to/from JSON preserving identical weights."""
        policy = LinUCBBanditPolicy(alpha=0.25, policy_version="v2.1-test")
        x = [0.8, 0.2, 0.1, 1.0, 0.6, 0.7, 0.5]
        policy.update(x, PolicyAction.APPLY, reward=1.0)
        policy.update(x, PolicyAction.SKIP, reward=-1.0)

        weights_file = str(tmp_path / "bandit_weights.json")
        policy.save_weights(weights_file)
        assert os.path.exists(weights_file)

        # Load weights into new instance
        loaded = LinUCBBanditPolicy.load_weights(weights_file)
        assert loaded.alpha == 0.25
        assert loaded.policy_version == "v2.1-test"
        assert loaded.A == policy.A
        assert loaded.b == policy.b

    def test_propensity_logging_and_action_diagnostics(self):
        """Verifies policy emits softmax propensities per decision bounded in [0.0, 1.0]."""
        policy = LinUCBBanditPolicy(alpha=0.2)
        job = {
            "match_score": 88.0,
            "company": "Microsoft GCC",
            "required_yoe": 2.5,
            "platform": "LinkedIn Easy Apply",
            "salary_lpa": 24.0,
            "jd": "Azure Databricks PySpark Delta Lake Kafka",
        }
        action, ucb, diag = policy.select_action(job)
        assert action in (PolicyAction.APPLY, PolicyAction.SKIP, PolicyAction.DEFER_TO_REVIEW)
        assert "propensity" in diag
        assert 0.0 <= diag["propensity"] <= 1.0
        assert "propensities" in diag
        assert len(diag["propensities"]) == 3
        assert abs(sum(diag["propensities"].values()) - 1.0) < 1e-2

    def test_refit_if_due_execution(self, tmp_path):
        """Verifies refit_if_due executes historical bootstrap."""
        db_path = str(tmp_path / "test_refit.db")
        init_db(db_path)
        record_applied_job(title="Data Eng", company="Comp A", status="Submitted", db_path=db_path)
        from naukari_pro.modules.learning.outcome_labeler import OutcomeLabeler
        labeler = OutcomeLabeler(db_path=db_path)
        jobs = labeler.get_unlabeled_jobs(min_age_hours=0.0)
        labeler.record_outcome(jobs[0]["job_id"], "callback")

        policy = LinUCBBanditPolicy(alpha=0.2)
        did_refit = policy.refit_if_due(db_path=db_path, min_new_outcomes=1)
        assert did_refit is True

    def test_auto_apply_prefilter_interception_with_bandit_policy(self):
        """Verifies AutoApplyEngine intercepts match gate and flags REJECTED_POLICY_BANDIT if policy skips."""
        from naukari_pro.modules.auto_apply import AutoApplyEngine
        policy = LinUCBBanditPolicy(alpha=0.0)
        # Train SKIP arm heavily positive and APPLY arm negative
        x_dummy = [0.85, 0.25, 0.1, 1.0, 1.0, 0.8, 0.6]
        policy.update(x_dummy, PolicyAction.SKIP, reward=10.0)
        policy.update(x_dummy, PolicyAction.APPLY, reward=-10.0)

        feed = [{
            "title": "Lead Azure Data Engineer",
            "company": "Microsoft GCC",
            "salary": "25 Lacs PA",
            "url": "https://naukri.com/job-1",
            "jd": "Azure Databricks PySpark Delta Lake Medallion"
        }]

        engine = AutoApplyEngine(dry_run=True, policy=policy)
        payloads = engine.run_offline_dry_run(job_feed=feed, limit=1)
        assert len(payloads) == 1
        assert payloads[0].status == "REJECTED_POLICY_BANDIT"
