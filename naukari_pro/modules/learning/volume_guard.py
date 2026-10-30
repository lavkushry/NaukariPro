"""
naukariPro Learning Subsystem: Volume Guard & Circuit Breaker (v2.1-linucb)
Implements:
1. Volume Floor: Guarantees min_applications_per_day (default: 10).
   Tops up pipeline with highest match_score skipped jobs tagged policy_action=APPLY_FLOOR.
2. Circuit Breaker: Compares last-7d vs prior-7d application counts from applied_jobs.
   If drop > 50% while policy is ACTIVE -> triggers FALLBACK mode (score-only ranking),
   sends Gmail alert, records event in policy_events.
3. Manual re-arm mechanism via policy-arm CLI.
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple, Union

from naukari_pro.config import DB_PATH, load_config
from naukari_pro.modules.db import (
    get_db_connection,
    init_db,
    get_policy_state,
    update_policy_mode,
    record_policy_event,
    get_daily_application_count,
)

logger = logging.getLogger("naukariPro.VolumeGuard")

DEFAULT_MIN_APPLICATIONS_PER_DAY = 10
DEFAULT_WINDOW_DAYS = 7
DEFAULT_DROP_THRESHOLD_PCT = 50.0


def send_gmail_notification(subject: str, body_text: str, recipient: Optional[str] = None) -> bool:
    """
    Sends notification email via Gmail SMTP using credentials from .env.
    Gracefully logs and returns False if password not set or offline.
    """
    password = os.getenv("GMAIL_APP_PASSWORD")
    sender = os.getenv("GMAIL_SENDER", "lav84095@gmail.com")
    recp = recipient or os.getenv("GMAIL_RECIPIENT", "lav84095@gmail.com")

    if not password:
        logger.info("GMAIL_APP_PASSWORD not set. Email notification suppressed.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = recp
        msg.attach(MIMEText(body_text, "plain", "utf-8"))

        with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as server:
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, [recp], msg.as_string())
        logger.info("Notification email sent to %s: %s", recp, subject)
        return True
    except Exception as e:
        logger.warning("Could not send email notification: %s", e)
        return False


class VolumeGuard:
    """
    Monitors application output rates and prevents cold-start policy starvation.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DB_PATH
        init_db(self.db_path)
        try:
            cfg = load_config()
            vol_cfg = cfg.get("learning", {}).get("volume", {})
            self.min_applications_per_day = int(vol_cfg.get("min_applications_per_day", DEFAULT_MIN_APPLICATIONS_PER_DAY))
            cb_cfg = vol_cfg.get("circuit_breaker", {})
            self.cb_enabled = bool(cb_cfg.get("enabled", True))
            self.window_days = int(cb_cfg.get("window_days", DEFAULT_WINDOW_DAYS))
            self.drop_threshold_pct = float(cb_cfg.get("drop_threshold_pct", DEFAULT_DROP_THRESHOLD_PCT))
        except Exception as e:
            logger.debug("Failed reading volume guard config, using defaults: %s", e)
            self.min_applications_per_day = DEFAULT_MIN_APPLICATIONS_PER_DAY
            self.cb_enabled = True
            self.window_days = DEFAULT_WINDOW_DAYS
            self.drop_threshold_pct = DEFAULT_DROP_THRESHOLD_PCT

    def get_volume_stats(self, db_path: Optional[str] = None, window_days: Optional[int] = None) -> Dict[str, Any]:
        """
        Calculates last-7d vs prior-7d volume and decision distribution from applied_jobs.
        Enforces real submission tracking (status LIKE 'Submitted%', non-empty evidence_path,
        excluding 'Form Auto-Filled' and synthetic backfill rows).
        Also captures raw counts for telemetry audit.
        """
        target_db = db_path or self.db_path
        days = window_days or self.window_days
        conn = get_db_connection(target_db)
        try:
            now = datetime.now()
            t_now = now.strftime("%Y-%m-%d %H:%M:%S")
            t_mid = (now - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
            t_prior = (now - timedelta(days=2 * days)).strftime("%Y-%m-%d %H:%M:%S")

            # Check if is_backfill column exists in table
            col_names = [col[1] for col in conn.execute("PRAGMA table_info(applied_jobs);").fetchall()]
            has_backfill = "is_backfill" in col_names
            backfill_clause = "AND (is_backfill IS NULL OR is_backfill = 0)" if has_backfill else ""

            # 1. Real submission counts (only real confirmed submissions with non-empty evidence, excluding Form Auto-Filled and backfill rows)
            q_sub_last = f"""
                SELECT COUNT(*) FROM applied_jobs
                WHERE applied_at >= ? AND applied_at <= ?
                  AND status LIKE 'Submitted%'
                  AND status NOT LIKE 'Form Auto-Filled%'
                  AND evidence_path IS NOT NULL AND evidence_path != ''
                  {backfill_clause}
            """
            sub_last_7d_count = conn.execute(q_sub_last, (t_mid, t_now)).fetchone()[0]

            q_sub_prior = f"""
                SELECT COUNT(*) FROM applied_jobs
                WHERE applied_at >= ? AND applied_at < ?
                  AND status LIKE 'Submitted%'
                  AND status NOT LIKE 'Form Auto-Filled%'
                  AND evidence_path IS NOT NULL AND evidence_path != ''
                  {backfill_clause}
            """
            sub_prior_7d_count = conn.execute(q_sub_prior, (t_prior, t_mid)).fetchone()[0]

            # 2. Raw total application counts (unfiltered volume for audit/telemetry)
            q_raw_last = """
                SELECT COUNT(*) FROM applied_jobs
                WHERE applied_at >= ? AND applied_at <= ?
            """
            raw_last_7d_count = conn.execute(q_raw_last, (t_mid, t_now)).fetchone()[0]

            q_raw_prior = """
                SELECT COUNT(*) FROM applied_jobs
                WHERE applied_at >= ? AND applied_at < ?
            """
            raw_prior_7d_count = conn.execute(q_raw_prior, (t_prior, t_mid)).fetchone()[0]

            # Primary 7-day counts strictly track real submissions
            last_7d_count = sub_last_7d_count
            prior_7d_count = sub_prior_7d_count

            if prior_7d_count > 0:
                drop_pct = round(max(0.0, (prior_7d_count - last_7d_count) / float(prior_7d_count) * 100.0), 2)
            else:
                drop_pct = 0.0

            # Today's application count
            today_str = now.strftime("%Y-%m-%d")
            today_count = conn.execute("""
                SELECT COUNT(*) FROM applied_jobs
                WHERE substr(applied_at, 1, 10) = ?
            """, (today_str,)).fetchone()[0]

            # Decision distribution
            rows_meta = conn.execute("""
                SELECT raw_metadata, status FROM applied_jobs
            """).fetchall()

            decisions = {"APPLY": 0, "SKIP": 0, "DEFER": 0, "APPLY_FLOOR": 0}
            for r in rows_meta:
                meta_str = r["raw_metadata"] or ""
                if '"policy_action": "APPLY_FLOOR"' in meta_str or "APPLY_FLOOR" in meta_str:
                    decisions["APPLY_FLOOR"] += 1
                elif '"policy_action": "DEFER"' in meta_str or "DEFER" in meta_str:
                    decisions["DEFER"] += 1
                elif '"policy_action": "SKIP"' in meta_str:
                    decisions["SKIP"] += 1
                elif "Submitted" in (r["status"] or "") or "Applied" in (r["status"] or ""):
                    decisions["APPLY"] += 1

            # Check policy events table for decision mix as well
            ev_rows = conn.execute("""
                SELECT event_type, COUNT(*) FROM policy_events GROUP BY event_type
            """).fetchall()
            for etype, cnt in ev_rows:
                if "APPLY_FLOOR" in etype:
                    decisions["APPLY_FLOOR"] = max(decisions["APPLY_FLOOR"], cnt)

            return {
                "window_days": days,
                "last_7d_count": last_7d_count,
                "prior_7d_count": prior_7d_count,
                "submission_last_7d_count": sub_last_7d_count,
                "submission_prior_7d_count": sub_prior_7d_count,
                "raw_last_7d_count": raw_last_7d_count,
                "raw_prior_7d_count": raw_prior_7d_count,
                "drop_pct": drop_pct,
                "daily_count_today": today_count,
                "decision_distribution": decisions,
            }
        finally:
            conn.close()

    def check_circuit_breaker(self, db_path: Optional[str] = None, send_alert: bool = True) -> Dict[str, Any]:
        """
        Weekly job: compares last-7d vs prior-7d volume.
        If drop > drop_threshold_pct (50%) while policy ACTIVE -> switches mode to FALLBACK,
        writes policy_events row, and sends email alert.
        """
        target_db = db_path or self.db_path
        stats = self.get_volume_stats(db_path=target_db)
        state = get_policy_state(db_path=target_db)
        current_mode = state.get("mode", "ACTIVE")

        drop_pct = stats["drop_pct"]
        prior_7d = stats["prior_7d_count"]
        last_7d = stats["last_7d_count"]

        if self.cb_enabled and prior_7d > 0 and drop_pct > self.drop_threshold_pct:
            if current_mode == "ACTIVE":
                reason = f"Application volume dropped {drop_pct:.1f}% ({prior_7d} -> {last_7d}) exceeding {self.drop_threshold_pct}% threshold."
                update_policy_mode(mode="FALLBACK", reason=reason, db_path=target_db)
                record_policy_event(
                    event_type="CIRCUIT_BREAKER_TRIGGERED",
                    details={
                        "prior_7d": prior_7d,
                        "last_7d": last_7d,
                        "drop_pct": drop_pct,
                        "threshold_pct": self.drop_threshold_pct,
                        "action": "mode_set_to_FALLBACK"
                    },
                    mode="FALLBACK",
                    db_path=target_db
                )
                if send_alert:
                    subject = f"[NaukariPro ALERT] Policy Circuit Breaker Triggered (Volume Drop {drop_pct:.1f}%)"
                    body = (
                        f"ALERT: NaukariPro Policy Circuit Breaker has triggered on host {os.uname().nodename}.\n\n"
                        f"Reason: Application volume dropped by {drop_pct:.1f}% over the past {self.window_days} days.\n"
                        f"Prior {self.window_days}d Applications: {prior_7d}\n"
                        f"Last {self.window_days}d Applications:  {last_7d}\n\n"
                        f"Policy Mode: Automatically set to FALLBACK (score-only ranking gate).\n"
                        f"Action Required: Investigate vacancy funnel and manually re-arm when resolved:\n"
                        f"    ./naukariPro policy-arm\n"
                    )
                    send_gmail_notification(subject=subject, body_text=body)

                return {
                    "triggered": True,
                    "previous_mode": "ACTIVE",
                    "new_mode": "FALLBACK",
                    "drop_pct": drop_pct,
                    "prior_7d": prior_7d,
                    "last_7d": last_7d
                }

        return {
            "triggered": False,
            "mode": current_mode,
            "drop_pct": drop_pct,
            "prior_7d": prior_7d,
            "last_7d": last_7d
        }

    def rearm_policy(self, db_path: Optional[str] = None) -> bool:
        """
        Manually re-arms policy from FALLBACK to ACTIVE mode.
        """
        target_db = db_path or self.db_path
        update_policy_mode(mode="ACTIVE", reason="Manual re-arm via policy-arm CLI", db_path=target_db)
        record_policy_event(
            event_type="POLICY_REARMED",
            details={"mode": "ACTIVE", "rearmed_by": "CLI policy-arm"},
            mode="ACTIVE",
            db_path=target_db
        )
        return True

    def enforce_volume_floor(
        self,
        qualified_jobs: List[Dict[str, Any]],
        skipped_jobs: List[Dict[str, Any]],
        target_daily_volume: Optional[int] = None,
        db_path: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Top up daily volume to floor if projected volume < min_applications_per_day.
        Picks highest match_score jobs from skipped_jobs, tags with policy_action=APPLY_FLOOR.
        """
        target_db = db_path or self.db_path
        floor = target_daily_volume if target_daily_volume is not None else self.min_applications_per_day
        today_applied = get_daily_application_count(db_path=target_db)
        projected = today_applied + len(qualified_jobs)
        shortfall = max(0, floor - projected)

        top_up_jobs: List[Dict[str, Any]] = []
        if shortfall > 0 and skipped_jobs:
            sorted_skipped = sorted(
                skipped_jobs,
                key=lambda j: float(j.get("match_score", 0.0)),
                reverse=True
            )
            to_promote = sorted_skipped[:shortfall]
            for job in to_promote:
                job["policy_action"] = "APPLY_FLOOR"
                job["policy_floor_override"] = True
                qualified_jobs.append(job)
                top_up_jobs.append(job)

                record_policy_event(
                    event_type="APPLY_FLOOR_OVERRIDE",
                    details={
                        "company": job.get("company"),
                        "title": job.get("title"),
                        "match_score": job.get("match_score"),
                        "floor_target": floor,
                        "projected_before_override": projected
                    },
                    mode="ACTIVE",
                    db_path=target_db
                )

            promoted_ids = {id(j) for j in to_promote}
            skipped_jobs[:] = [j for j in skipped_jobs if id(j) not in promoted_ids]

        return qualified_jobs, top_up_jobs
