"""
naukariPro Learning Subsystem: Telemetry & Outcome Labeling (Milestone 3 / R3)
Implements:
1. Daily job to scan applied_jobs where outcome_label IS NULL and applied_at < datetime('now', '-24 hours')
2. Multi-channel label signals:
   - 'callback': Recruiter contacted candidate / scheduled interview / outreach response
   - 'view': Recruiter viewed application / profile
   - 'rejection': Explicit rejection email or portal update
   - 'silence': >30 days without response (or >72h unresolved fallback)
3. Enforces SLA: 0 rows >72h with NULL outcome
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple

from naukari_pro.config import DB_PATH, WORKSPACE_DIR
from naukari_pro.modules.db import get_db_connection, init_db

logger = logging.getLogger("naukariPro.OutcomeLabeler")

VALID_OUTCOMES = {"callback", "view", "rejection", "silence", "confirmation"}


class OutcomeLabeler:
    """
    Scans historical application records in SQLite and labels recruitment outcomes
    based on recruiter views, confirmations, outreach callbacks, and age.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DB_PATH
        init_db(self.db_path)

    def get_unlabeled_jobs(self, min_age_hours: float = 24.0) -> List[Dict[str, Any]]:
        """
        Retrieves applications where outcome_label IS NULL and applied_at < now - min_age_hours.
        """
        conn = get_db_connection(self.db_path)
        try:
            cutoff_dt = datetime.now() - timedelta(hours=min_age_hours)
            cutoff_str = cutoff_dt.strftime("%Y-%m-%d %H:%M:%S")

            query = """
                SELECT id, job_id, platform, company, title, applied_at, status
                FROM applied_jobs
                WHERE outcome_label IS NULL
                  AND (applied_at IS NULL OR applied_at <= ?)
                ORDER BY applied_at ASC
            """
            rows = conn.execute(query, (cutoff_str,)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_unlabeled_count(self, hours: float = 72.0) -> int:
        """Returns count of applications older than `hours` still lacking an outcome label."""
        return len(self.get_unlabeled_jobs(min_age_hours=hours))

    def record_outcome(
        self,
        job_id: str,
        outcome_label: str,
        observed_at: Optional[str] = None
    ) -> bool:
        """
        Sets outcome_label and outcome_observed_at on a specific application.
        """
        label = outcome_label.lower().strip()
        if label not in VALID_OUTCOMES:
            raise ValueError(f"Invalid outcome label '{label}'. Must be one of: {sorted(VALID_OUTCOMES)}")

        obs_time = observed_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = get_db_connection(self.db_path)
        try:
            with conn:
                res = conn.execute("""
                    UPDATE applied_jobs
                    SET outcome_label = ?, outcome_observed_at = ?
                    WHERE job_id = ? OR id = ?
                """, (label, obs_time, job_id, job_id))
                return res.rowcount > 0
        finally:
            conn.close()

    def label_all_unlabeled(
        self,
        min_age_hours: float = 24.0,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Runs the daily outcome labeling job.
        Rules:
        - Checks for callback signals in outreach tracker or recruitment logs.
        - Checks for status signals: 'Rejected' -> 'rejection', 'Viewed' -> 'view'.
        - If applied > 30 days ago without signal -> 'silence'.
        - If applied > 72 hours ago without signal -> defaults to 'silence' (or 'view' if status indicated review).
        """
        unlabeled = self.get_unlabeled_jobs(min_age_hours=min_age_hours)
        labeled_count = 0
        results_breakdown: Dict[str, int] = {k: 0 for k in VALID_OUTCOMES}

        # Load outreach signals if available
        outreach_callbacks = set()
        outreach_file = os.path.join(WORKSPACE_DIR, "outreach_tracker.json")
        if os.path.exists(outreach_file):
            try:
                with open(outreach_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data.get("outreach_history", []):
                        if item.get("status") in ("ACCEPTED", "INTERVIEW", "CALLBACK", "RESPONSE"):
                            comp = (item.get("target_company") or "").lower().strip()
                            if comp:
                                outreach_callbacks.add(comp)
            except Exception as e:
                logger.debug("Could not read outreach tracker: %s", e)

        now = datetime.now()
        for job in unlabeled:
            jid = job["job_id"]
            company_lower = (job.get("company") or "").lower().strip()
            status_lower = (job.get("status") or "").lower().strip()
            applied_at_str = job.get("applied_at")

            if applied_at_str:
                try:
                    clean_str = applied_at_str.strip()[:19]
                    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                        try:
                            applied_dt = datetime.strptime(clean_str, fmt)
                            age_days = (now - applied_dt).total_seconds() / 86400.0
                            break
                        except ValueError:
                            continue
                except Exception:
                    age_days = 2.0  # Fallback age

            # Signal 1: Callback / Outreach response
            if company_lower in outreach_callbacks:
                chosen_label = "callback"
            # Signal 2: Status explicitly says Rejected
            elif "reject" in status_lower:
                chosen_label = "rejection"
            # Signal 3: Status explicitly says Viewed / Contacted
            elif "view" in status_lower or "contact" in status_lower:
                chosen_label = "view"
            # Signal 4: > 30 days or > 72h default to silence
            elif age_days >= 3.0:
                chosen_label = "silence"
            else:
                chosen_label = "confirmation"

            if not dry_run:
                self.record_outcome(jid, chosen_label)

            results_breakdown[chosen_label] += 1
            labeled_count += 1

        return {
            "scanned": len(unlabeled),
            "labeled": labeled_count,
            "breakdown": results_breakdown,
            "dry_run": dry_run,
        }


def label_unlabeled_outcomes(min_age_hours: float = 24.0, db_path: Optional[str] = None, dry_run: bool = False) -> Dict[str, Any]:
    """Convenience functional facade for OutcomeLabeler."""
    labeler = OutcomeLabeler(db_path=db_path)
    return labeler.label_all_unlabeled(min_age_hours=min_age_hours, dry_run=dry_run)


def get_unlabeled_count(hours: float = 72.0, db_path: Optional[str] = None) -> int:
    """Convenience function returning count of >72h unlabeled jobs."""
    labeler = OutcomeLabeler(db_path=db_path)
    return labeler.get_unlabeled_count(hours=hours)
