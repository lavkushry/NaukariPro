"""
naukariPro Learning Subsystem: Attribution Engine (Milestone 3 / R3)
Implements:
1. Difference-in-differences (DiD) statistical attribution on weekly search appearances
2. Formula: DiD = (Y_treat_post - Y_treat_pre) - (Y_ctrl_post - Y_ctrl_pre)
3. Rigorous pre-condition: Enforces n >= 3 observations before asserting causality
4. Reads from search_appearance_weekly and profile_mutations SQLite tables
"""

import sqlite3
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

from naukari_pro.config import DB_PATH
from naukari_pro.modules.db import get_db_connection, init_db

logger = logging.getLogger("naukariPro.Attribution")

MIN_OBSERVATIONS_FOR_CAUSALITY = 3


def calculate_did(
    treat_pre: List[float],
    treat_post: List[float],
    ctrl_pre: List[float],
    ctrl_post: List[float]
) -> Dict[str, Any]:
    """
    Computes Difference-in-Differences estimator:
    DiD = (Mean(treat_post) - Mean(treat_pre)) - (Mean(ctrl_post) - Mean(ctrl_pre))
    Enforces n >= 3 per condition for causal assertion.
    """
    n_treat_pre = len(treat_pre)
    n_treat_post = len(treat_post)
    n_ctrl_pre = len(ctrl_pre)
    n_ctrl_post = len(ctrl_post)

    can_assert_causality = (
        n_treat_pre >= MIN_OBSERVATIONS_FOR_CAUSALITY
        and n_treat_post >= MIN_OBSERVATIONS_FOR_CAUSALITY
        and n_ctrl_pre >= MIN_OBSERVATIONS_FOR_CAUSALITY
        and n_ctrl_post >= MIN_OBSERVATIONS_FOR_CAUSALITY
    )

    if not treat_pre or not treat_post or not ctrl_pre or not ctrl_post:
        return {
            "did_estimate": 0.0,
            "causal_assertion_allowed": False,
            "sample_sizes": {
                "treat_pre": n_treat_pre,
                "treat_post": n_treat_post,
                "ctrl_pre": n_ctrl_pre,
                "ctrl_post": n_ctrl_post,
            },
            "treatment_delta": 0.0,
            "control_delta": 0.0,
            "status": "INSUFFICIENT_DATA",
            "reason": f"Need at least 1 observation in all 4 partitions (and n >= {MIN_OBSERVATIONS_FOR_CAUSALITY} for causality)"
        }

    m_treat_pre = sum(treat_pre) / n_treat_pre
    m_treat_post = sum(treat_post) / n_treat_post
    m_ctrl_pre = sum(ctrl_pre) / n_ctrl_pre
    m_ctrl_post = sum(ctrl_post) / n_ctrl_post

    treat_delta = m_treat_post - m_treat_pre
    ctrl_delta = m_ctrl_post - m_ctrl_pre
    did_estimate = round(treat_delta - ctrl_delta, 2)

    status = "CAUSAL_EFFECT_VERIFIED" if can_assert_causality else "CORRELATION_ONLY_UNDERPOWERED"

    return {
        "did_estimate": did_estimate,
        "causal_assertion_allowed": can_assert_causality,
        "treatment_delta": round(treat_delta, 2),
        "control_delta": round(ctrl_delta, 2),
        "means": {
            "treat_pre": round(m_treat_pre, 2),
            "treat_post": round(m_treat_post, 2),
            "ctrl_pre": round(m_ctrl_pre, 2),
            "ctrl_post": round(m_ctrl_post, 2),
        },
        "sample_sizes": {
            "treat_pre": n_treat_pre,
            "treat_post": n_treat_post,
            "ctrl_pre": n_ctrl_pre,
            "ctrl_post": n_ctrl_post,
        },
        "status": status,
        "reason": "Causality supported by DiD" if can_assert_causality else f"Sample size (n < {MIN_OBSERVATIONS_FOR_CAUSALITY}) insufficient to rule out exogenous search algorithm shocks"
    }


class AttributionEngine:
    """
    Evaluates profile mutations against weekly search appearance telemetry.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DB_PATH
        init_db(self.db_path)

    def record_weekly_appearances(
        self,
        week_start_date: Optional[str] = None,
        search_appearances: Optional[int] = None,
        profile_views: int = 0,
        contact_views: int = 0,
        platform: str = "naukri",
        week_start: Optional[str] = None,
        appearances: Optional[int] = None,
        screenshot_path: Optional[str] = None
    ) -> bool:
        """Stores weekly telemetry in search_appearance_weekly conforming to §4.6 and §4.7."""
        w_start = week_start or week_start_date or datetime.now().strftime("%Y-%m-%d")
        w_date = week_start_date or w_start
        app_cnt = appearances if appearances is not None else (search_appearances if search_appearances is not None else 0)
        s_apps = search_appearances if search_appearances is not None else app_cnt
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = get_db_connection(self.db_path)
        try:
            with conn:
                conn.execute("""
                    INSERT INTO search_appearance_weekly (
                        platform, week_start, week_start_date, appearances, search_appearances,
                        profile_views, contact_views, captured_at, recorded_at, screenshot_path
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(week_start_date) DO UPDATE SET
                        platform = excluded.platform,
                        week_start = excluded.week_start,
                        appearances = excluded.appearances,
                        search_appearances = excluded.search_appearances,
                        profile_views = excluded.profile_views,
                        contact_views = excluded.contact_views,
                        captured_at = excluded.captured_at,
                        recorded_at = excluded.recorded_at,
                        screenshot_path = COALESCE(excluded.screenshot_path, search_appearance_weekly.screenshot_path)
                """, (
                    platform, w_start, w_date, app_cnt, s_apps,
                    profile_views, contact_views, now_str, now_str, screenshot_path
                ))
                return True
        finally:
            conn.close()

    def get_weekly_history(self) -> List[Dict[str, Any]]:
        """Retrieves ordered weekly search appearance history."""
        conn = get_db_connection(self.db_path)
        try:
            rows = conn.execute("""
                SELECT week_start_date, search_appearances, profile_views, contact_views, recorded_at
                FROM search_appearance_weekly
                ORDER BY week_start_date ASC
            """).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def evaluate_mutation_impact(
        self,
        mutation_week: str,
        benchmark_control_delta: float = 0.0
    ) -> Dict[str, Any]:
        """
        Calculates impact of mutations around a given mutation week.
        Partitions weekly appearances into pre-mutation and post-mutation periods.
        """
        history = self.get_weekly_history()
        pre_weeks = [float(h["search_appearances"]) for h in history if h["week_start_date"] < mutation_week]
        post_weeks = [float(h["search_appearances"]) for h in history if h["week_start_date"] >= mutation_week]

        # Use benchmark control delta if no separate control series
        ctrl_pre = [0.0] * max(len(pre_weeks), 1)
        ctrl_post = [benchmark_control_delta] * max(len(post_weeks), 1)

        return calculate_did(
            treat_pre=pre_weeks,
            treat_post=post_weeks,
            ctrl_pre=ctrl_pre,
            ctrl_post=ctrl_post
        )


def evaluate_did(treat_pre: List[float], treat_post: List[float], ctrl_pre: List[float], ctrl_post: List[float]) -> Dict[str, Any]:
    """Convenience facade for calculate_did."""
    return calculate_did(treat_pre, treat_post, ctrl_pre, ctrl_post)
