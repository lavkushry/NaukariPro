"""
naukariPro Learning Subsystem: Monday Digest Generator & Dispatcher (Milestone 5 / R5 & v2.1-linucb)
Generates consolidated weekly markdown digest summarizing:
1. Applications submitted (7d & total) and confirmation evidence count.
2. Outcome breakdown (callbacks, views, rejections, silence, confirmation) past 7 days and total.
3. Search appearance delta from search_appearance_weekly and DiD attribution results.
4. Top mined utility tokens ready for mutation.
5. Quarantine queue status and unresolved count.
6. Contextual Bandit Policy Mode, Volume Guard telemetry, and Decision Mix (APPLY, SKIP, DEFER, APPLY_FLOOR).
7. Dispatches weekly digest email via Gmail SMTP using GMAIL_APP_PASSWORD.
"""

import os
import sys
import smtplib
import sqlite3
import argparse
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from naukari_pro.config import DB_PATH, WORKSPACE_DIR, load_config
from naukari_pro.modules.db import (
    get_db_connection,
    init_db,
    get_quarantine_summary,
    get_policy_state,
)
from naukari_pro.modules.learning.outcome_labeler import OutcomeLabeler, get_unlabeled_count
from naukari_pro.modules.learning.keyword_miner import KeywordMiner
from naukari_pro.modules.learning.attribution import AttributionEngine, calculate_did
from naukari_pro.modules.learning.policy import LinUCBBanditPolicy, DEFAULT_POLICY_VERSION
from naukari_pro.modules.learning.volume_guard import VolumeGuard

logger = logging.getLogger("naukariPro.MondayDigest")


def send_monday_digest_email(
    digest_content: str,
    subject: Optional[str] = None,
    recipient: Optional[str] = None
) -> bool:
    """
    Dispatches the weekly Monday Digest markdown report via Gmail SMTP.
    Credentials read from .env: GMAIL_APP_PASSWORD, sender defaults to lav84095@gmail.com.
    """
    password = os.getenv("GMAIL_APP_PASSWORD")
    sender = os.getenv("GMAIL_SENDER", "lav84095@gmail.com")
    recp = recipient or os.getenv("GMAIL_RECIPIENT", "lav84095@gmail.com")
    report_date = datetime.now().strftime("%Y-%m-%d")
    sub = subject or f"[NaukariPro] Monday Closed-Loop Learning Digest — {report_date}"

    if not password:
        logger.info("GMAIL_APP_PASSWORD not set in environment. Skipping email dispatch.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = sub
        msg["From"] = sender
        msg["To"] = recp
        msg.attach(MIMEText(digest_content, "plain", "utf-8"))

        with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, [recp], msg.as_string())

        logger.info("Monday Digest successfully emailed to %s: %s", recp, sub)
        return True
    except Exception as e:
        logger.warning("Failed to send Monday Digest email: %s", e)
        return False


def generate_monday_digest(
    db_path: Optional[str] = None,
    output_path: Optional[str] = None,
    as_of_date: Optional[str] = None
) -> str:
    """
    Compiles a comprehensive weekly Monday Digest markdown report from SQLite telemetry.
    """
    target_db = db_path or DB_PATH
    init_db(target_db)

    report_date = as_of_date or datetime.now().strftime("%Y-%m-%d")
    conn = get_db_connection(target_db)

    # 1. Application Volume & Proof-of-Apply Evidence
    try:
        total_apps = conn.execute("SELECT COUNT(*) FROM applied_jobs").fetchone()[0]

        seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        recent_apps = conn.execute(
            "SELECT COUNT(*) FROM applied_jobs WHERE applied_at >= ?",
            (seven_days_ago,)
        ).fetchone()[0]

        evidence_count = conn.execute(
            "SELECT COUNT(*) FROM applied_jobs WHERE evidence_path IS NOT NULL AND evidence_path != ''"
        ).fetchone()[0]

        platform_counts = conn.execute(
            "SELECT platform, COUNT(*) FROM applied_jobs GROUP BY platform"
        ).fetchall()
        platform_breakdown = {r[0]: r[1] for r in platform_counts}
    finally:
        conn.close()

    # 2. Outcome breakdown & SLA
    labeler = OutcomeLabeler(db_path=target_db)
    conn = get_db_connection(target_db)
    try:
        outcome_rows = conn.execute(
            "SELECT outcome_label, COUNT(*) FROM applied_jobs GROUP BY outcome_label"
        ).fetchall()
        outcome_distribution = {r[0] or "unlabeled": r[1] for r in outcome_rows}

        # 7d outcome breakdown
        recent_outcomes = conn.execute(
            "SELECT outcome_label, COUNT(*) FROM applied_jobs WHERE outcome_observed_at >= ? GROUP BY outcome_label",
            (seven_days_ago,)
        ).fetchall()
        recent_outcome_dist = {r[0] or "unlabeled": r[1] for r in recent_outcomes}
    finally:
        conn.close()

    sla_unresolved = labeler.get_unlabeled_count(hours=72.0)

    # 3. Search Appearance & Attribution
    attr_engine = AttributionEngine(db_path=target_db)
    history = attr_engine.get_weekly_history()
    recent_trend_lines = []
    did_section = ""

    if history:
        for row in history[-4:]:
            recent_trend_lines.append(
                f"| {row['week_start_date']} | {row['search_appearances']} | {row['profile_views']} | {row['contact_views']} |"
            )
        if len(history) >= 2:
            prev_week = history[-2]["search_appearances"]
            curr_week = history[-1]["search_appearances"]
            delta = curr_week - prev_week
            delta_str = f"+{delta}" if delta >= 0 else f"{delta}"
            appearance_summary = f"Latest Week Appearances: **{curr_week}** ({delta_str} vs previous week)"
        else:
            appearance_summary = f"Latest Week Appearances: **{history[-1]['search_appearances']}**"

        target_week = history[-1]["week_start_date"]
        did_res = attr_engine.evaluate_mutation_impact(mutation_week=target_week)
        did_section = f"""
- **DiD Metric Evaluation:** {did_res.get('did_estimate', 0.0)} net search appearance lift
- **Status:** `{did_res.get('status', 'INSUFFICIENT_DATA')}`
- **Causal Assertion Allowed:** {did_res.get('causal_assertion_allowed', False)} (n >= 3 required)
- **Diagnostic Note:** {did_res.get('reason', 'N/A')}
"""
    else:
        appearance_summary = "No weekly search appearance records recorded yet. Telemetry tracker active."
        did_section = "- **Status:** `AWAITING_TELEMETRY` (Baseline recording scheduled via weekly timer)"

    # 4. Top Mined Keywords
    miner = KeywordMiner(db_path=target_db)
    top_keywords = miner.get_top_utility_keywords(limit=8, claimable_only=True)
    if not top_keywords:
        miner.mine_and_store()
        top_keywords = miner.get_top_utility_keywords(limit=8, claimable_only=True)

    keyword_table_rows = []
    for kw in top_keywords:
        keyword_table_rows.append(
            f"| `{kw['token']}` | {kw['utility_score']:.2f} | {kw['demand_frequency']} | {kw['saturation_count']} | {'✅ Verified' if kw['claimable'] else '❌ Forbidden'} |"
        )
    keyword_table_md = "\n".join(keyword_table_rows) if keyword_table_rows else "| None | - | - | - | - |"

    # 5. Quarantine Queue Status
    quarantine_summary = get_quarantine_summary(db_path=target_db)

    # 6. Policy State, Volume Guard & Decision Mix
    vg = VolumeGuard(db_path=target_db)
    cb_result = vg.check_circuit_breaker(db_path=target_db, send_alert=True)
    vol_stats = vg.get_volume_stats(db_path=target_db)
    pol_state = get_policy_state(db_path=target_db)
    policy = LinUCBBanditPolicy()
    eff_eps = policy.get_effective_epsilon(decisions_count=pol_state.get("decisions_count", 0), db_path=target_db)
    decisions = vol_stats["decision_distribution"]

    # Compose Markdown
    lines = [
        f"# 📊 NaukariPro Learning Loop — Weekly Monday Digest",
        f"**Date:** {report_date}  ",
        f"**Candidate:** Lavkush Kumar (2.5 YOE Azure Data Engineer | CGI India, ex-HFCL)  ",
        f"**Candidate Email:** `lavkushry@gmail.com` | **Applicant Login:** `lav84095@gmail.com`  ",
        f"**Target Role:** Azure Data Engineer / Platform Engineer (₹25 LPA Target)  ",
        "",
        "---",
        "",
        "## 1. Application Volume & Proof-of-Apply Evidence",
        f"- **Total Applications Tracked:** {total_apps}",
        f"- **Applications Past 7 Days:** {recent_apps}",
        f"- **Verified Cryptographic Evidence (Screenshots/Tokens):** {evidence_count} / {total_apps} ({round(evidence_count / max(1, total_apps) * 100, 1)}%)",
        "- **Platform Distribution:**",
    ]

    for plat, cnt in sorted(platform_breakdown.items()):
        lines.append(f"  - `{plat}`: {cnt} applications")

    lines.extend([
        "",
        "## 2. Recruitment Outcome Breakdown & SLA Tracking",
        f"- **Callbacks / Recruiter Direct:** {outcome_distribution.get('callback', 0)} (7d: {recent_outcome_dist.get('callback', 0)})",
        f"- **Recruiter Profile Views:** {outcome_distribution.get('view', 0)} (7d: {recent_outcome_dist.get('view', 0)})",
        f"- **Rejections Recorded:** {outcome_distribution.get('rejection', 0)} (7d: {recent_outcome_dist.get('rejection', 0)})",
        f"- **Silence / Auto-Timed Out (>72h):** {outcome_distribution.get('silence', 0)}",
        f"- **Confirmation Pending Review (<72h):** {outcome_distribution.get('confirmation', 0)}",
        f"- **Unlabeled Applications:** {outcome_distribution.get('unlabeled', 0)}",
        f"- **SLA Compliance (Unlabeled >72h):** **{sla_unresolved}** (Target: 0 rows)",
        "",
        "## 3. Search Appearance Delta & DiD Attribution",
        f"- {appearance_summary}",
    ])

    if recent_trend_lines:
        lines.extend([
            "",
            "| Week Start | Search Appearances | Profile Views | Recruiter Contact Views |",
            "|:---|:---:|:---:|:---:|",
        ] + recent_trend_lines)

    lines.extend([
        did_section.strip(),
        "",
        "## 4. Top Mined Keyword Utilities (U = Demand / Saturation)",
        "| Core Token | Utility Score | Market Demand | Profile Saturation | Claimable Status |",
        "|:---|:---:|:---:|:---:|:---:|",
        keyword_table_md,
        "",
        "## 5. Screening Quarantine Queue & Guardrails",
        f"- **Total Quarantined Prompts:** {quarantine_summary['total']}",
        f"- **Pending Ambiguous Reviews:** {quarantine_summary['pending']}",
        f"- **Resolved Queries:** {quarantine_summary['resolved']}",
    ])

    if quarantine_summary["by_category"]:
        lines.append("- **Category Breakdown:**")
        for cat, cnt in quarantine_summary["by_category"].items():
            lines.append(f"  - `{cat}`: {cnt}")

    lines.extend([
        "",
        "## 6. Contextual Bandit Policy & Volume Guard Telemetry",
        f"- **Policy Version:** `{pol_state.get('policy_version', 'v2.1-linucb')}`",
        f"- **Operating Mode:** `{pol_state.get('mode', 'ACTIVE')}`",
        f"- **Decisions Logged to Date:** {pol_state.get('decisions_count', 0)}",
        f"- **Effective Exploration Epsilon (ε):** {eff_eps:.4f}",
        f"- **Volume Guard (Last 7d vs Prior 7d):** {vol_stats['last_7d_count']} vs {vol_stats['prior_7d_count']} (Weekly Drop: {vol_stats['drop_pct']}%)",
        f"- **Circuit Breaker Status:** `{'TRIGGERED -> FALLBACK' if cb_result.get('triggered') else ('FALLBACK (Manual Re-arm Required)' if pol_state.get('mode') == 'FALLBACK' else 'ACTIVE (Healthy)')}`",
        f"- **Decision Mix (Action Distribution):**",
        f"  - `APPLY`: {decisions.get('APPLY', 0)}",
        f"  - `SKIP`: {decisions.get('SKIP', 0)}",
        f"  - `DEFER`: {decisions.get('DEFER', 0)}",
        f"  - `APPLY_FLOOR` (Overrides): {decisions.get('APPLY_FLOOR', 0)}",
        "",
        "---",
        "*Digest generated autonomously by naukariPro Closed-Loop Learning Engine (v2.1-linucb)*"
    ])

    digest_content = "\n".join(lines) + "\n"

    if output_path:
        out_dir = os.path.dirname(os.path.abspath(output_path))
        os.makedirs(out_dir, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(digest_content)

    return digest_content


def main():
    parser = argparse.ArgumentParser(description="naukariPro Weekly Monday Digest Generator & Dispatcher")
    parser.add_argument("--output", "-o", type=str, default=None, help="File path to write markdown digest")
    parser.add_argument("--db", type=str, default=None, help="Custom database path")
    parser.add_argument("--send-email", action="store_true", default=False, help="Dispatch report to candidate via Gmail SMTP")
    args = parser.parse_args()

    digest = generate_monday_digest(db_path=args.db, output_path=args.output)
    print(digest)

    if args.send_email:
        send_monday_digest_email(digest_content=digest)


if __name__ == "__main__":
    main()
