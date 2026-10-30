"""
naukariPro Learning Subsystem: Contextual Bandit Selection Policy (Milestone 4 / R4)
Implements:
1. LinUCB (Linear Upper Confidence Bound) Contextual Bandit with exploration factor alpha = 0.2
2. 7-Dimensional Context Feature Vector:
   - x[0]: match_score (normalized: score / 100.0)
   - x[1]: required_yoe (normalized: min(yoe, 10.0) / 10.0)
   - x[2]: posting_age_hours (normalized: min(age, 168.0) / 168.0)
   - x[3]: company_tier (Tier 1 GCC = 1.0, Mid = 0.5, Other = 0.2)
   - x[4]: ats_platform (1-Click / Easy Apply = 1.0, Greenhouse/Lever = 0.6, Workday = 0.3)
   - x[5]: skill_overlap (fraction 0.0 to 1.0 of core skills matched)
   - x[6]: salary_lpa (normalized: min(salary, 40.0) / 40.0)
3. Action Space:
   - APPLY (0)
   - SKIP (1)
   - DEFER_TO_REVIEW (2)
4. Reward Structure:
   - callback: +1.0
   - view: +0.3
   - rejection: -1.0
   - silence: -0.2
   - duplicate: -2.0
5. Cold-Start Inverse-Propensity Bootstrap from historical SQLite rows
"""

import os
import json
import math
import logging
from enum import IntEnum
from typing import Optional, Dict, Any, List, Tuple, Union

from naukari_pro.config import DB_PATH, WORKSPACE_DIR
from naukari_pro.modules.db import get_db_connection, init_db

logger = logging.getLogger("naukariPro.BanditPolicy")

CONTEXT_DIMENSION = 7
DEFAULT_ALPHA = 0.2

# Target Tier 1 GCCs & Tech Hubs
TIER_1_COMPANIES = {
    "microsoft", "walmart", "amazon", "google", "uber", "atlassian",
    "flipkart", "razorpay", "salesforce", "adobe", "linkedin",
    "databricks", "nvidia", "jpmorgan", "goldman sachs", "morgan stanley"
}

# Standardized Reward Schedule
REWARD_SCHEDULE: Dict[str, float] = {
    "callback": 1.0,
    "interview": 1.0,
    "view": 0.3,
    "contacted": 0.3,
    "confirmation": 0.1,
    "silence": -0.2,
    "rejection": -1.0,
    "rejected": -1.0,
    "duplicate": -2.0,
}


class PolicyAction(IntEnum):
    APPLY = 0
    SKIP = 1
    DEFER_TO_REVIEW = 2


def extract_context_vector(job: Dict[str, Any]) -> List[float]:
    """
    Extracts and normalizes the 7-dimensional context vector x in R^7.
    All dimensions bounded in [0.0, 1.0].
    """
    # 1. Match score (0 to 100 -> 0.0 to 1.0)
    score_raw = job.get("match_score", 70.0)
    try:
        score = float(score_raw)
    except (ValueError, TypeError):
        score = 70.0
    x0 = max(0.0, min(1.0, score / 100.0))

    # 2. Required YOE (0 to 10 Yrs -> 0.0 to 1.0)
    yoe_raw = job.get("required_yoe") or job.get("yoe") or job.get("experience", 2.5)
    try:
        yoe = float(yoe_raw)
    except (ValueError, TypeError):
        yoe = 2.5
    x1 = max(0.0, min(1.0, yoe / 10.0))

    # 3. Posting age in hours (0 to 168 hours / 1 week -> 0.0 to 1.0)
    age_raw = job.get("posting_age_hours") or job.get("age_hours", 24.0)
    try:
        age = float(age_raw)
    except (ValueError, TypeError):
        age = 24.0
    x2 = max(0.0, min(1.0, age / 168.0))

    # 4. Company tier
    company = str(job.get("company", "")).lower()
    if any(t in company for t in TIER_1_COMPANIES):
        x3 = 1.0
    elif any(t in company for t in ("tech", "systems", "global", "solutions", "corp", "analytics")):
        x3 = 0.5
    else:
        x3 = 0.2

    # 5. ATS Platform
    portal = str(job.get("platform") or job.get("portal") or job.get("application_type", "")).lower()
    if "1-click" in portal or "easy apply" in portal or "naukri" in portal or "linkedin" in portal:
        x4 = 1.0
    elif any(ats in portal for ats in ("greenhouse", "lever", "ashby", "rippling")):
        x4 = 0.6
    else:
        x4 = 0.3

    # 6. Skill overlap
    jd = str(job.get("jd") or job.get("raw_jd") or job.get("description", "")).lower()
    core_skills = ["pyspark", "databricks", "delta lake", "kafka", "adf", "sql", "terraform"]
    matches = sum(1 for s in core_skills if s in jd)
    x5 = max(0.1, min(1.0, matches / float(len(core_skills))))

    # 7. Salary LPA (0 to 40 LPA -> 0.0 to 1.0)
    sal_raw = job.get("salary_lpa") or job.get("salary", 20.0)
    try:
        sal = float(sal_raw)
    except (ValueError, TypeError):
        sal = 20.0
    x6 = max(0.0, min(1.0, sal / 40.0))

    return [x0, x1, x2, x3, x4, x5, x6]


# Pure Python Linear Algebra Helpers for 7x7 Matrices (zero numpy dependency requirement)
def matrix_zeros(rows: int, cols: int) -> List[List[float]]:
    return [[0.0 for _ in range(cols)] for _ in range(rows)]


def matrix_eye(dim: int) -> List[List[float]]:
    m = matrix_zeros(dim, dim)
    for i in range(dim):
        m[i][i] = 1.0
    return m


def mat_vec_mul(m: List[List[float]], v: List[float]) -> List[float]:
    return [sum(m[r][c] * v[c] for c in range(len(v))) for r in range(len(m))]


def vec_dot(u: List[float], v: List[float]) -> float:
    return sum(a * b for a, b in zip(u, v))


def invert_symmetric_7x7(a: List[List[float]]) -> List[List[float]]:
    """
    Gaussian elimination with partial pivoting for small 7x7 positive definite matrices.
    """
    n = len(a)
    # Augment matrix with identity
    aug = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(a)]
    for i in range(n):
        # Pivot search
        max_row = i
        max_val = abs(aug[i][i])
        for k in range(i + 1, n):
            if abs(aug[k][i]) > max_val:
                max_val = abs(aug[k][i])
                max_row = k
        if max_val < 1e-12:
            # Regularize near singular matrix
            aug[i][i] += 1e-4
        if max_row != i:
            aug[i], aug[max_row] = aug[max_row], aug[i]

        pivot = aug[i][i]
        for j in range(2 * n):
            aug[i][j] /= pivot
        for r in range(n):
            if r != i:
                factor = aug[r][i]
                for c in range(2 * n):
                    aug[r][c] -= factor * aug[i][c]

    return [row[n:] for row in aug]


class LinUCBBanditPolicy:
    """
    Contextual Bandit Selection Policy using LinUCB algorithm.
    Decides whether to APPLY, SKIP, or DEFER_TO_REVIEW based on upper confidence bound.
    """

    def __init__(
        self,
        alpha: float = DEFAULT_ALPHA,
        d: int = CONTEXT_DIMENSION,
        policy_version: str = "v2.0-linucb"
    ):
        self.alpha = float(alpha)
        self.d = d
        self.policy_version = policy_version
        self.actions = [PolicyAction.APPLY, PolicyAction.SKIP, PolicyAction.DEFER_TO_REVIEW]

        # Initialize per-action design matrices A_a = I_d and response vectors b_a = 0
        self.A: Dict[int, List[List[float]]] = {
            int(a): matrix_eye(self.d) for a in self.actions
        }
        self.b: Dict[int, List[float]] = {
            int(a): [0.0] * self.d for a in self.actions
        }

    def predict_ucb(self, x: List[float], action: PolicyAction) -> Tuple[float, float, float]:
        """
        Calculates UCB score for a given action and context vector x:
        theta_a = A_a^(-1) * b_a
        score = theta_a^T * x + alpha * sqrt(x^T * A_a^(-1) * x)
        Returns: (ucb_score, expected_payoff, confidence_width)
        """
        a_idx = int(action)
        A_inv = invert_symmetric_7x7(self.A[a_idx])
        theta = mat_vec_mul(A_inv, self.b[a_idx])

        expected_payoff = vec_dot(theta, x)
        inv_x = mat_vec_mul(A_inv, x)
        variance = vec_dot(x, inv_x)
        confidence_width = self.alpha * math.sqrt(max(0.0, variance))

        ucb_score = expected_payoff + confidence_width
        return round(ucb_score, 4), round(expected_payoff, 4), round(confidence_width, 4)

    def select_action(self, job: Dict[str, Any]) -> Tuple[PolicyAction, float, Dict[str, Any]]:
        """
        Extracts context x, computes UCB for all actions, and selects argmax UCB.
        Returns: (best_action, best_ucb, diagnostics_dict)
        """
        x = extract_context_vector(job)
        diagnostics = {}
        best_action = PolicyAction.APPLY
        best_ucb = -float("inf")

        for action in self.actions:
            ucb, payoff, width = self.predict_ucb(x, action)
            diagnostics[action.name] = {
                "ucb": ucb,
                "payoff": payoff,
                "width": width
            }
            if ucb > best_ucb:
                best_ucb = ucb
                best_action = action

        # Compute softmax propensity per decision
        tau = 0.5
        max_u = max(d["ucb"] for d in diagnostics.values())
        exp_terms = {a.name: math.exp(max(-20.0, min(20.0, (diagnostics[a.name]["ucb"] - max_u) / tau))) for a in self.actions}
        sum_exp = sum(exp_terms.values())
        propensities = {k: round(v / sum_exp, 4) for k, v in exp_terms.items()}

        diagnostics["selected_action"] = best_action.name
        diagnostics["context_vector"] = x
        diagnostics["policy_version"] = self.policy_version
        diagnostics["propensity"] = propensities.get(best_action.name, 1.0)
        diagnostics["propensities"] = propensities
        return best_action, best_ucb, diagnostics

    def update(self, x: List[float], action: PolicyAction, reward: float) -> None:
        """
        Updates LinUCB parameters given observed reward r for chosen action:
        A_a = A_a + x * x^T
        b_a = b_a + r * x
        """
        a_idx = int(action)
        r = float(reward)

        # Update A_a += x * x^T
        for i in range(self.d):
            for j in range(self.d):
                self.A[a_idx][i][j] += x[i] * x[j]

        # Update b_a += r * x
        for i in range(self.d):
            self.b[a_idx][i] += r * x[i]

    def update_from_outcome(self, x: List[float], action: PolicyAction, outcome_label: str) -> float:
        """Looks up reward schedule and updates policy."""
        label = outcome_label.lower().strip()
        reward = REWARD_SCHEDULE.get(label, 0.0)
        self.update(x, action, reward)
        return reward

    def bootstrap_from_history(self, db_path: Optional[str] = None) -> int:
        """
        Cold-start inverse-propensity bootstrap:
        Reads historical rows with observed outcome_labels from applied_jobs.db
        and updates policy parameters A and b.
        """
        target_db = db_path or DB_PATH
        init_db(target_db)
        conn = get_db_connection(target_db)
        updated_rows = 0
        try:
            query = """
                SELECT match_score, experience_req, status, application_type, job_url,
                       outcome_label, company, title
                FROM applied_jobs
                WHERE outcome_label IS NOT NULL
            """
            rows = conn.execute(query).fetchall()
            for r in rows:
                label = (r["outcome_label"] or "").lower().strip()
                if label not in REWARD_SCHEDULE:
                    continue
                # Synthesize job dict for context extraction
                job_dict = {
                    "match_score": r["match_score"] or 70.0,
                    "experience": 2.5,
                    "company": r["company"] or "",
                    "platform": r["application_type"] or "1-Click Direct",
                    "salary": 20.0,
                    "jd": f"{r['title']} {r['company']}"
                }
                x = extract_context_vector(job_dict)
                reward = REWARD_SCHEDULE[label]
                # In historical data, recorded jobs were applied
                self.update(x, PolicyAction.APPLY, reward)
                updated_rows += 1
            return updated_rows
        finally:
            conn.close()

    def refit_if_due(self, db_path: Optional[str] = None, min_new_outcomes: int = 50) -> bool:
        """
        Refits policy parameters when historical labeled records are available.
        Refits every 50 labeled outcomes or on-demand.
        """
        updated = self.bootstrap_from_history(db_path=db_path)
        logger.info("LinUCB Policy refitted with %d historical labeled rows", updated)
        return updated >= min_new_outcomes

    def to_dict(self) -> Dict[str, Any]:
        """Serializes policy parameters to JSON-compatible dictionary."""
        return {
            "policy_version": self.policy_version,
            "alpha": self.alpha,
            "d": self.d,
            "A": {str(k): v for k, v in self.A.items()},
            "b": {str(k): v for k, v in self.b.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LinUCBBanditPolicy":
        """Deserializes policy parameters from dictionary."""
        policy = cls(
            alpha=data.get("alpha", DEFAULT_ALPHA),
            d=data.get("d", CONTEXT_DIMENSION),
            policy_version=data.get("policy_version", "v2.0-linucb")
        )
        if "A" in data:
            policy.A = {int(k): v for k, v in data["A"].items()}
        if "b" in data:
            policy.b = {int(k): v for k, v in data["b"].items()}
        return policy

    def save_weights(self, filepath: str) -> None:
        """Saves weights to JSON file."""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_weights(cls, filepath: str) -> "LinUCBBanditPolicy":
        """Loads weights from JSON file."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)
