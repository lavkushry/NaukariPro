"""
Profile Performance, Entitlement Verification & Keyword Diff Engine
Tracks the 5 live numbers that dictate recruiter outreach:
1. Search Appearances (recruiter database searches returning candidate)
2. Profile Views (recruiters opening full profile)
3. Resume Downloads (recruiters downloading PDF)
4. Contact Views (recruiters unlocking phone/email — THE NORTH STAR)
5. Recruiter Search Terms (exact keywords recruiters typed in Resdex)

Provides:
- Conversion Funnel Analysis (CTR, Contact Conversion Rate, Bottleneck Detection)
- Keyword Diff against Headline and Key Skills (Matching, Missing High-Intent, Diluting)
- Weekly Performance Logging to JSON and Excel Tracker
"""

import os
import json
import base64
import time
import re
from datetime import datetime
import logging
import openpyxl
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

from naukari_pro.config import COOKIES_SEED_PATH, TRACKER_PATH, load_config, WORKSPACE_DIR

logger = logging.getLogger("naukariPro.Performance")

HISTORY_FILE = os.path.join(WORKSPACE_DIR, "naukri_system", "profile_performance_history.json")

MONTHLY_SEARCH_BENCHMARK = 100_000
DAILY_SEARCH_BENCHMARK = 3333.33

@dataclass
class BenchmarkPacing:
    total_searches_30d: int
    target_monthly: int = 100000
    daily_target: float = 3333.33
    current_daily_pace: float = 0.0
    projected_monthly: int = 0
    percent_attainment: float = 0.0
    status: str = "DEFICIT"  # "ON_TRACK", "AHEAD", "DEFICIT"
    deficit: int = 0
    daily_shortfall: float = 0.0
    naukri_searches: int = 0
    linkedin_searches: int = 0
    linkedin_impressions: int = 0
    total_impressions: int = 0
    platform_breakdown: Dict[str, int] = field(default_factory=dict)

    @property
    def target_total(self) -> int:
        return self.target_monthly

    @property
    def actual_daily_pace(self) -> float:
        return self.current_daily_pace

    @property
    def projected_30d_volume(self) -> int:
        return self.projected_monthly

    @property
    def attainment_pct(self) -> float:
        return round((self.total_impressions or self.total_searches_30d) / self.target_monthly * 100, 2) if self.target_monthly > 0 else 0.0


def compute_benchmark_pacing(
    appearances: int = 0,
    days: int = 7,
    target_monthly: int = 100000,
    *,
    current_appearances: Optional[int] = None,
    elapsed_days: Optional[int] = None,
    target_appearances: Optional[int] = None,
    target_days: int = 30,
    naukri_searches: Optional[int] = None,
    linkedin_searches: Optional[int] = None,
    linkedin_impressions: Optional[int] = None,
    total_impressions: Optional[int] = None
) -> BenchmarkPacing:
    """Computes daily pace, 30-day projected velocity, and target attainment against 100k monthly benchmark.
    Supports unified cross-platform aggregation (Naukri searches + LinkedIn searches + LinkedIn impressions).
    """
    if current_appearances is not None:
        appearances = current_appearances
    if elapsed_days is not None:
        days = elapsed_days
    if target_appearances is not None:
        target_monthly = target_appearances

    safe_days = max(days, 1)
    safe_target_days = max(target_days, 1)

    n_search = max(naukri_searches, 0) if naukri_searches is not None else None
    l_search = max(linkedin_searches, 0) if linkedin_searches is not None else None
    l_impr = max(linkedin_impressions, 0) if linkedin_impressions is not None else None

    if total_impressions is not None:
        total_val = max(total_impressions, 0)
    elif n_search is not None or l_search is not None or l_impr is not None:
        total_val = (n_search or 0) + (l_search or 0) + (l_impr or 0)
    else:
        total_val = max(appearances, 0)

    daily_pace = round(total_val / safe_days, 2)
    daily_target = round(target_monthly / float(safe_target_days), 2)
    projected_monthly = int(round(daily_pace * safe_target_days))
    percent_attainment = round((projected_monthly / target_monthly) * 100, 2) if target_monthly > 0 else 0.0

    ratio = daily_pace / daily_target if daily_target > 0 else 1.0
    if ratio > 1.05:
        status = "AHEAD"
    elif ratio < 0.95:
        status = "DEFICIT"
    else:
        status = "ON_TRACK"

    deficit = max(0, target_monthly - projected_monthly)
    daily_shortfall = max(0.0, round(daily_target - daily_pace, 2))

    breakdown = {
        "naukri_searches": n_search if n_search is not None else total_val,
        "linkedin_searches": l_search if l_search is not None else 0,
        "linkedin_impressions": l_impr if l_impr is not None else 0,
        "total_unified_impressions": total_val
    }

    return BenchmarkPacing(
        total_searches_30d=total_val,
        target_monthly=target_monthly,
        daily_target=daily_target,
        current_daily_pace=daily_pace,
        projected_monthly=projected_monthly,
        percent_attainment=percent_attainment,
        status=status,
        deficit=deficit,
        daily_shortfall=daily_shortfall,
        naukri_searches=n_search if n_search is not None else total_val,
        linkedin_searches=l_search or 0,
        linkedin_impressions=l_impr or 0,
        total_impressions=total_val,
        platform_breakdown=breakdown
    )


def compute_unified_pacing(
    naukri_appearances: int = 0,
    linkedin_appearances: int = 0,
    linkedin_impressions: int = 0,
    days: int = 7,
    target_monthly: int = 100000
) -> BenchmarkPacing:
    """Convenience helper computing unified 100K pacing across Naukri and LinkedIn."""
    return compute_benchmark_pacing(
        days=days,
        target_monthly=target_monthly,
        naukri_searches=naukri_appearances,
        linkedin_searches=linkedin_appearances,
        linkedin_impressions=linkedin_impressions
    )

class Unified100KSpeedometer:
    """
    Unified 100K Monthly Impression Pacing Speedometer.
    Aggregates recruiter search appearances and profile impressions across
    Naukri and LinkedIn into a single velocity benchmark ($3,333.33/day).
    """

    def __init__(
        self,
        target_monthly: int = MONTHLY_SEARCH_BENCHMARK,
        target_total: Optional[int] = None,
        target_days: int = 30
    ):
        self.target_total = target_total or target_monthly
        self.target_monthly = self.target_total
        self.target_days = target_days
        self.daily_target = self.target_total / float(self.target_days) if self.target_days > 0 else DAILY_SEARCH_BENCHMARK

        self.naukri_searches = 0
        self.naukri_views = 0
        self.linkedin_searches = 0
        self.linkedin_impressions = 0

    def add_naukri_metrics(self, search_appearances: int = 0, profile_views: int = 0) -> None:
        """Adds or updates Naukri search appearances and profile views."""
        self.naukri_searches += search_appearances
        self.naukri_views += profile_views

    def add_linkedin_metrics(self, search_appearances: int = 0, impressions: int = 0) -> None:
        """Adds or updates LinkedIn search appearances and impressions."""
        self.linkedin_searches += search_appearances
        self.linkedin_impressions += impressions

    def compute_current_pacing(self, elapsed_days: int = 7) -> BenchmarkPacing:
        """Computes current pacing using accumulated platform metrics."""
        return compute_benchmark_pacing(
            current_appearances=self.naukri_searches + self.linkedin_searches + self.linkedin_impressions,
            naukri_searches=self.naukri_searches,
            linkedin_searches=self.linkedin_searches,
            linkedin_impressions=self.linkedin_impressions,
            elapsed_days=elapsed_days,
            target_appearances=self.target_total,
            target_days=self.target_days
        )

    def generate_speedometer_report(self, elapsed_days: int = 7) -> str:
        """Generates a detailed ASCII dashboard report of the unified speedometer."""
        pacing = self.compute_current_pacing(elapsed_days=elapsed_days)
        lines = [
            "================================================================================",
            "   🚀 UNIFIED 100K IMPRESSION PACING SPEEDOMETER",
            f"   Status: {pacing.status} | Attainment: {pacing.attainment_pct:.1f}% ({pacing.total_impressions:,} / {pacing.target_total:,})",
            "================================================================================",
            f"  Elapsed Days:       {elapsed_days} / {self.target_days}",
            f"  Daily Target Pace:  {pacing.daily_target:,.2f} impressions/day",
            f"  Actual Daily Pace:  {pacing.actual_daily_pace:,.2f} impressions/day",
            f"  30-Day Projection:  {pacing.projected_30d_volume:,} impressions",
            f"  Deficit / Buffer:   {pacing.deficit:,.2f} impressions",
            "--------------------------------------------------------------------------------",
            "  PLATFORM BREAKDOWN:",
            f"  • Naukri Searches:      {self.naukri_searches:,}",
            f"  • LinkedIn Searches:    {self.linkedin_searches:,}",
            f"  • LinkedIn Impressions: {self.linkedin_impressions:,}",
            "================================================================================"
        ]
        return "\n".join(lines)

    def calculate_pace(
        self,
        naukri_searches: int = 0,
        linkedin_searches: int = 0,
        linkedin_impressions: int = 0,
        days: int = 7
    ) -> BenchmarkPacing:
        """Calculates unified pacing across all channels."""
        return compute_unified_pacing(
            naukri_appearances=naukri_searches,
            linkedin_appearances=linkedin_searches,
            linkedin_impressions=linkedin_impressions,
            days=days,
            target_monthly=self.target_monthly
        )

    def aggregate_telemetry(
        self,
        naukri_telemetry: Optional[Dict[str, Any]] = None,
        linkedin_telemetry: Optional[Dict[str, Any]] = None,
        days: int = 7
    ) -> Dict[str, Any]:
        """Combines platform telemetry dictionaries into unified speedometer report."""
        n_tel = naukri_telemetry or {}
        l_tel = linkedin_telemetry or {}

        n_search = n_tel.get("search_appearances", n_tel.get("search_appearances_7d", 0))
        l_search = l_tel.get("search_appearances", 0)
        l_impr = l_tel.get("impressions", l_tel.get("profile_views", 0))

        pacing = self.calculate_pace(
            naukri_searches=n_search,
            linkedin_searches=l_search,
            linkedin_impressions=l_impr,
            days=days
        )

        return {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "target_monthly": self.target_monthly,
            "daily_target": self.daily_target,
            "naukri_searches": n_search,
            "linkedin_searches": l_search,
            "linkedin_impressions": l_impr,
            "total_unified_impressions": pacing.total_impressions,
            "daily_pace": pacing.current_daily_pace,
            "projected_monthly": pacing.projected_monthly,
            "percent_attainment": pacing.percent_attainment,
            "pacing_status": pacing.status,
            "deficit": pacing.deficit,
            "daily_shortfall": pacing.daily_shortfall,
            "platform_breakdown": pacing.platform_breakdown,
            "naukri_telemetry": n_tel,
            "linkedin_telemetry": l_tel
        }

# Canonical MLOps / ML Platform / AI Infrastructure Engineer target keywords (2+ YOE) per 01_FACT_MATRIX.md & AGENTS.md
TARGET_MLOPS_KEYWORDS = [
    "MLOps Engineer",
    "ML Platform Engineer",
    "AI Infrastructure Engineer",
    "Kubernetes",
    "Docker",
    "Helm",
    "CI/CD",
    "GitHub Actions",
    "Terraform",
    "Prometheus",
    "Grafana",
    "Triton",
    "Triton Inference Server",
    "vLLM",
    "MLflow",
    "Kafka",
    "Python",
    "Linux",
    "FastAPI",
    "EKS",
    "AWS",
    "Redis",
    "StatefulSets"
]

# Verified Azure Data Engineer target keywords and spelling standards (Retained for backwards compatibility)
TARGET_DE_KEYWORDS = [
    "Azure Data Engineer",
    "PySpark",
    "Azure Databricks",
    "Delta Lake",
    "Azure Data Factory",
    "SQL",
    "Apache Kafka",
    "ADLS Gen2",
    "Medallion Architecture",
    "Terraform",
    "ETL",
    "Data Pipeline",
    "Data Lakehouse",
    "Azure Synapse",
    "Microsoft Fabric"
]

def decode_naukri_jwt(token_str):
    """Decodes JWT payload without external dependencies."""
    try:
        parts = token_str.split(".")
        if len(parts) >= 2:
            payload_b64 = parts[1]
            padding = len(payload_b64) % 4
            if padding:
                payload_b64 += "=" * (4 - padding)
            decoded_bytes = base64.urlsafe_b64decode(payload_b64)
            return json.loads(decoded_bytes.decode("utf-8"))
    except Exception as e:
        logger.debug("JWT decode notice: %s", e)
    return {}

class ProfilePerformanceEngine:
    def __init__(self, tracker_path: Optional[str] = None, history_file: Optional[str] = None, **kwargs):
        self.cfg = load_config()
        self.tracker_path = tracker_path
        self.history_file = history_file

    def get_session_entitlements(self, cookies=None):
        """
        Inspects session tokens to determine real server-side account entitlements.
        Naukri stores authentic subscription flags on its server and in the signed 'nauk_at' JWT.
        """
        token = None
        if cookies:
            for c in cookies:
                if c.get("name") == "nauk_at":
                    token = c.get("value")
                    break

        if not token and os.path.exists(COOKIES_SEED_PATH):
            try:
                with open(COOKIES_SEED_PATH, "r", encoding="utf-8") as f:
                    seed = json.load(f)
                for c in seed:
                    if c.get("name") == "nauk_at":
                        token = c.get("value")
                        break
            except Exception:
                pass

        if not token:
            return {
                "authenticated": False,
                "is_paid_client": False,
                "user_id": None,
                "user_state": "UNAUTHENTICATED",
                "tier": "Unknown / Unauthenticated",
                "details": "No 'nauk_at' session token found in cookies."
            }

        payload = decode_naukri_jwt(token)
        is_paid = bool(payload.get("ud_isPaidClient", False))
        user_id = payload.get("userId") or payload.get("sub")
        email = payload.get("ud_username") or payload.get("ud_email")
        state = payload.get("userState", "UNKNOWN")

        return {
            "authenticated": state == "AUTHENTICATED",
            "is_paid_client": is_paid,
            "user_id": user_id,
            "email": email,
            "user_state": state,
            "tier": "Naukri Paid / Pro Account" if is_paid else "Standard Free Account",
            "server_entitlements": {
                "featured_flag_resdex": is_paid,
                "priority_applicant_flag": is_paid,
                "pro_ai_entitlements": is_paid,
            },
            "raw_claims": {
                "deviceType": payload.get("deviceType"),
                "sessionStatTime": payload.get("sessionStatTime"),
                "exp": payload.get("exp")
            }
        }

    def fetch_live_performance(self, page):
        """
        Navigates to authentic live Naukri Profile Performance (https://www.naukri.com/mnjuser/performance)
        and extracts 90d/7d search appearances, recruiter actions (profile views,
        contact views, resume downloads, NVites, recruiter bookmarks), and search keywords.
        """
        logger.info("Accessing live Naukri Profile Performance at https://www.naukri.com/mnjuser/performance...")
        metrics = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "search_appearances": 0,
            "search_appearances_90d": 0,
            "search_appearances_7d": 0,
            "recruiter_actions": 0,
            "profile_views": 0,
            "resume_downloads": 0,
            "contact_views": 0,
            "nvites": 0,
            "recruiter_bookmarks": 0,
            "search_terms": [],
            "data_source": "Live Naukri Portal"
        }

        try:
            page.goto("https://www.naukri.com/mnjuser/performance", wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)

            if "login" in page.url.lower():
                logger.warning("Session expired; redirected to login page.")
                metrics["data_source"] = "Session Expired (Login Required)"
                return metrics

            body_text = page.locator("body").inner_text() if page.locator("body").count() > 0 else ""

            # Helper to extract integer from selector or regex
            def extract_stat(selectors, regex_patterns):
                for sel in selectors:
                    try:
                        el = page.locator(sel).first
                        if el.count() > 0 and el.is_visible():
                            txt = el.inner_text().strip()
                            num_match = re.search(r'\b\d+\b', txt)
                            if num_match:
                                return int(num_match.group(0))
                    except Exception:
                        pass
                for pat in regex_patterns:
                    m = re.search(pat, body_text, re.IGNORECASE)
                    if m:
                        for g in m.groups():
                            if g and g.isdigit():
                                return int(g)
                return 0

            # 1. 90-day search appearances
            search_90d = extract_stat(
                [
                    ".summary-card__search-appearance--value.typ-40Medium",
                    ".summary-card__search-appearance--value",
                    "[class*='search-appearance--value']",
                    ".searchAppWrapper .count",
                    ".search-appearances",
                    ".perf-count",
                    "span[class*='searchAppCount']",
                    "div[class*='searchApp']"
                ],
                [
                    r'(\d+)\s*search appearance[s]?\s*(?:in last 90 days)?',
                    r'appeared in\s*(\d+)\s*searches',
                    r'(\d+)\s*search appearances?'
                ]
            )

            # 2. 7-day search appearances
            search_7d = extract_stat(
                [
                    ".search-appearances-droop",
                    "span:has-text('Search appearances in last')",
                    "[class*='recent-search-appearances']"
                ],
                [
                    r'(\d+)\s*search appearance[s]?\s*in last\s*(?:7\s*days)?',
                    r'last\s*7\s*days[:\s]+(\d+)\s*searches'
                ]
            )

            metrics["search_appearances_90d"] = search_90d
            metrics["search_appearances_7d"] = search_7d
            metrics["search_appearances"] = search_90d if search_90d > 0 else search_7d

            # 3. Cumulative Recruiter Actions (90 Days)
            recruiter_actions = extract_stat(
                [
                    ".summary-card__recruiter-actions--value.typ-40Medium",
                    ".summary-card__recruiter-actions--value",
                    "[class*='recruiter-actions--value']",
                    ".recActWrapper .count",
                    ".recruiter-actions"
                ],
                [
                    r'(\d+)\s*recruiter actions?',
                    r'recruiter actions?[:\s]+(\d+)'
                ]
            )
            metrics["recruiter_actions"] = recruiter_actions

            # 4. Recruiter Actions Breakdown (DOM: .ja-tag container and .ja-tag-count badge)
            try:
                tag_elements = page.locator(".ja-tag, [class*='ja-tag'], .action-tag").all()
                for tag in tag_elements:
                    txt = tag.inner_text().strip()
                    txt_lower = txt.lower()
                    count_val = None
                    count_el = tag.locator(".ja-tag-count, [class*='tag-count']").first
                    if count_el.count() > 0:
                        c_text = count_el.inner_text().strip()
                        m = re.search(r'\b\d+\b', c_text)
                        if m:
                            count_val = int(m.group(0))
                    if count_val is None:
                        m = re.search(r'\b\d+\b', txt)
                        if m:
                            count_val = int(m.group(0))

                    if count_val is not None:
                        if "profile viewed" in txt_lower:
                            metrics["profile_views"] = count_val
                        elif "contact viewed" in txt_lower:
                            metrics["contact_views"] = count_val
                        elif "resume downloaded" in txt_lower or "cv downloaded" in txt_lower:
                            metrics["resume_downloads"] = count_val
                        elif "nvite" in txt_lower:
                            metrics["nvites"] = count_val
                        elif "bookmarked" in txt_lower:
                            metrics["recruiter_bookmarks"] = count_val
            except Exception as tag_err:
                logger.debug("Tag extraction notice: %s", tag_err)

            # Fallbacks for specific actions if not caught by .ja-tag
            if metrics["profile_views"] == 0:
                metrics["profile_views"] = extract_stat(
                    [".profile-views", "span[class*='profileViews']", "div[class*='profView']"],
                    [r'(?:naukri\s*)?profile viewed\s*(\d+)', r'(\d+)\s*(?:naukri\s*)?profile views?']
                )

            if metrics["contact_views"] == 0:
                metrics["contact_views"] = extract_stat(
                    ["span[class*='contactView']", "div[class*='contactCount']"],
                    [r'contact viewed\s*(\d+)', r'(\d+)\s*contact views?', r'(\d+)\s*contact details? viewed']
                )

            if metrics["resume_downloads"] == 0:
                metrics["resume_downloads"] = extract_stat(
                    ["span[class*='downloadCount']", "div[class*='downloadCount']", ".resume-download-count"],
                    [r'resume downloaded\s*(\d+)', r'(\d+)\s*resume downloads?', r'(\d+)\s*cv downloads?']
                )

            if metrics["nvites"] == 0:
                metrics["nvites"] = extract_stat(
                    [".nvite-count", "[class*='nvite'] .count"],
                    [r'nvites?\s*sent\s*(\d+)', r'(\d+)\s*nvites?']
                )

            if metrics["recruiter_bookmarks"] == 0:
                metrics["recruiter_bookmarks"] = extract_stat(
                    [".bookmark-count", "[class*='bookmark'] .count"],
                    [r'profile bookmarked\s*(\d+)', r'(\d+)\s*bookmarks?']
                )

            # 5. Search terms typed by recruiters (.search-keyword-card)
            try:
                kw_cards = page.locator(".search-keyword-card, [class*='search-keyword-card'], .keyword-container").all()
                for card in kw_cards[:15]:
                    lbl = card.locator(".keyword-label, [class*='keyword-label']").first
                    if lbl.count() > 0:
                        t = lbl.inner_text().strip()
                    else:
                        raw_t = card.inner_text().strip()
                        t = re.split(r'\d+\s*times?', raw_t, flags=re.IGNORECASE)[0].strip()
                    if t and len(t) < 50 and t not in metrics["search_terms"]:
                        metrics["search_terms"].append(t)
            except Exception as kw_err:
                logger.debug("Keyword card extraction notice: %s", kw_err)

            if not metrics["search_terms"]:
                kw_els = page.locator(".keyword-chip, .keyword-pill, div[class*='keywordTag'], span[class*='keyword'], .chip").all()
                for kw in kw_els[:15]:
                    t = kw.inner_text().strip()
                    if t and len(t) < 40 and t not in metrics["search_terms"]:
                        metrics["search_terms"].append(t)

            # 6. Fallback to /mnjuser/homepage if search appearances is still 0
            if metrics["search_appearances"] == 0 and "login" not in page.url.lower():
                try:
                    logger.info("Attempting homepage telemetry fallback at /mnjuser/homepage...")
                    page.goto("https://www.naukri.com/mnjuser/homepage", wait_until="domcontentloaded", timeout=15000)
                    time.sleep(2)
                    app_el = page.locator(".searchAppWrapper .count").first
                    if app_el.count() > 0 and app_el.is_visible():
                        m = re.search(r'\b\d+\b', app_el.inner_text().strip())
                        if m:
                            metrics["search_appearances"] = int(m.group(0))
                            metrics["search_appearances_90d"] = metrics["search_appearances"]
                    rec_el = page.locator(".recActWrapper .count").first
                    if rec_el.count() > 0 and rec_el.is_visible():
                        m = re.search(r'\b\d+\b', rec_el.inner_text().strip())
                        if m:
                            metrics["recruiter_actions"] = int(m.group(0))
                except Exception as hp_err:
                    logger.debug("Homepage fallback notice: %s", hp_err)

            # Log snapshot to history
            self.log_performance_snapshot(metrics)

        except Exception as e:
            logger.warning("Profile performance query notice: %s", e)
            metrics["data_source"] = f"Extraction Notice: {str(e)}"

        return metrics

    def compute_benchmark_pacing(self, appearances: int, days: int = 7, target_monthly: int = 100000) -> BenchmarkPacing:
        """Calculates benchmark pacing against monthly search target."""
        return compute_benchmark_pacing(appearances, days, target_monthly)

    def compute_unified_pacing(
        self,
        naukri_appearances: int = 0,
        linkedin_appearances: int = 0,
        linkedin_impressions: int = 0,
        days: int = 7,
        target_monthly: int = 100000
    ) -> BenchmarkPacing:
        """Calculates unified pacing across all channels."""
        return compute_unified_pacing(
            naukri_appearances=naukri_appearances,
            linkedin_appearances=linkedin_appearances,
            linkedin_impressions=linkedin_impressions,
            days=days,
            target_monthly=target_monthly
        )

    def get_unified_speedometer(
        self,
        naukri_telemetry: Optional[Dict[str, Any]] = None,
        linkedin_telemetry: Optional[Dict[str, Any]] = None,
        days: int = 7,
        target_monthly: int = 100000
    ) -> Dict[str, Any]:
        """Provides a unified speedometer summary aggregating Naukri and LinkedIn impressions."""
        speedometer = Unified100KSpeedometer(target_monthly=target_monthly)
        return speedometer.aggregate_telemetry(
            naukri_telemetry=naukri_telemetry,
            linkedin_telemetry=linkedin_telemetry,
            days=days
        )

    def log_performance_snapshot(self, metrics, tracker_path=None, history_file=None, db_path=None):
        """Persists the 5 live numbers and benchmark pacing to multi-sink destinations:
        1. Historical JSON ledger (naukri_system/profile_performance_history.json)
        2. Excel tracker (Naukri_Live_Application_Tracker.xlsx § Recruiter_Performance_Log)
        3. SQLite database (search_appearance_weekly & unified_impressions_ledger)
        """
        h_file = history_file or HISTORY_FILE
        t_path = tracker_path or TRACKER_PATH
        os.makedirs(os.path.dirname(h_file), exist_ok=True)
        history = []
        if os.path.exists(h_file):
            try:
                with open(h_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                history = []

        apps = max(metrics.get("search_appearances", metrics.get("searches", metrics.get("searches_7d", 0))), 0)
        views = max(metrics.get("profile_views", metrics.get("views", metrics.get("views_7d", 0))), 0)
        downloads = max(metrics.get("resume_downloads", 0), 0)
        contacts = max(metrics.get("contact_views", 0), 0)
        n_search = metrics.get("naukri_searches", apps)
        l_search = metrics.get("linkedin_searches", 0)
        l_impr = metrics.get("linkedin_impressions", 0)
        elapsed_days = metrics.get("elapsed_days", 7)

        pacing = compute_benchmark_pacing(
            appearances=apps,
            days=elapsed_days,
            target_monthly=100000,
            naukri_searches=n_search,
            linkedin_searches=l_search,
            linkedin_impressions=l_impr
        )
        ctr = round((views / apps) * 100, 2) if apps > 0 else 0.0
        contact_conv = round((contacts / views) * 100, 2) if views > 0 else 0.0

        metrics["searches_7d"] = apps
        metrics["views_7d"] = views
        metrics["daily_pace"] = pacing.current_daily_pace
        metrics["projected_monthly"] = pacing.projected_monthly
        metrics["percent_attainment"] = pacing.percent_attainment
        metrics["pacing_status"] = pacing.status
        metrics["deficit"] = pacing.deficit
        metrics["daily_shortfall"] = pacing.daily_shortfall
        metrics["ctr_pct"] = ctr
        metrics["contact_conv_pct"] = contact_conv
        metrics["total_impressions"] = pacing.total_impressions
        metrics["total_unified_impressions"] = pacing.total_impressions
        metrics["naukri_searches"] = pacing.naukri_searches
        metrics["linkedin_searches"] = pacing.linkedin_searches
        metrics["linkedin_impressions"] = pacing.linkedin_impressions

        history.append(metrics)
        try:
            with open(h_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            logger.warning("Could not save performance history JSON: %s", e)

        # Multi-sink Destination 2: Excel Tracker under Recruiter_Performance_Log
        try:
            perf_headers_10 = [
                "Timestamp",
                "Search Appearances",
                "Profile Views",
                "Resume Downloads",
                "Contact Views",
                "CTR (%)",
                "Contact Conv (%)",
                "Daily Pace (req 3333)",
                "Projected 30d Volume",
                "Pacing Status"
            ]
            if not os.path.exists(t_path):
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "Applications_Log"
                ws.append([
                    "Application Date", "Company Name", "Job Title", "Match Score (%)",
                    "Role Category", "Experience Required", "Location", "Application Type",
                    "Status", "Job URL", "Recruiter Response"
                ])
                ws_perf = wb.create_sheet(title="Recruiter_Performance_Log")
                ws_perf.append(perf_headers_10)
            else:
                wb = openpyxl.load_workbook(t_path)
                sheet_name = "Recruiter_Performance_Log"
                if sheet_name in wb.sheetnames:
                    ws_perf = wb[sheet_name]
                else:
                    ws_perf = wb.create_sheet(title=sheet_name)
                    ws_perf.append(perf_headers_10)

            headers = [cell.value for cell in ws_perf[1]] if ws_perf.max_row >= 1 else []
            ctr_str = f"{ctr}%"
            conv_str = f"{contact_conv}%"

            if len(headers) == 9 and "Recruiter Search Terms" in headers:
                terms_str = ", ".join(metrics.get("search_terms", []))
                ws_perf.append([
                    metrics.get("timestamp", datetime.now().strftime("%Y-%m-%d")),
                    apps,
                    views,
                    downloads,
                    contacts,
                    terms_str,
                    ctr_str,
                    conv_str,
                    f"Benchmark Run Rate: {pacing.projected_monthly} ({pacing.status})"
                ])
            else:
                ws_perf.append([
                    metrics.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M")),
                    apps,
                    views,
                    downloads,
                    contacts,
                    ctr_str,
                    conv_str,
                    pacing.current_daily_pace,
                    pacing.projected_monthly,
                    pacing.status
                ])
            wb.save(t_path)
        except Exception as e:
            logger.warning("Could not append to Excel tracker: %s", e)

        # Multi-sink Destination 3: SQLite Database
        try:
            self.record_weekly_telemetry(
                week_start_date=metrics.get("timestamp", datetime.now().strftime("%Y-%m-%d")),
                search_appearances=apps,
                profile_views=views,
                contact_views=contacts,
                platform=metrics.get("platform", "naukri"),
                db_path=db_path
            )
            # Also record unified telemetry if LinkedIn is present
            if l_search > 0 or l_impr > 0:
                self.record_weekly_telemetry(
                    week_start_date=metrics.get("timestamp", datetime.now().strftime("%Y-%m-%d")),
                    search_appearances=l_search,
                    profile_views=l_impr,
                    contact_views=0,
                    platform="linkedin",
                    db_path=db_path
                )
            # Direct insert into profile_performance table if present in db_path
            if db_path and os.path.exists(db_path):
                import sqlite3
                conn = sqlite3.connect(db_path)
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='profile_performance'")
                if cursor.fetchone():
                    conn.execute("""
                        INSERT INTO profile_performance (
                            timestamp, searches_7d, views_7d, calls_today, total_impressions, daily_pace, pacing_status, notes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        metrics.get("timestamp", datetime.now().isoformat()),
                        apps,
                        views,
                        metrics.get("calls_today", 0),
                        pacing.total_impressions,
                        pacing.current_daily_pace,
                        pacing.status,
                        metrics.get("notes", "")
                    ))
                    conn.commit()
                conn.close()
        except Exception as sqle:
            logger.debug("SQLite telemetry write notice: %s", sqle)

        return True

    def generate_keyword_diff_report(self, live_search_terms=None, persona: str = "de"):
        """
        Calculates exact diff between:
        1. Recruiter search terms that found candidate (from Profile Performance)
        2. Verified target MLOps or Azure Data Engineer keywords
        3. Current headline and technical skills configured
        """
        cfg = load_config()
        headline = cfg.get("headline_template", "")
        competencies = cfg.get("technical_competencies", {})
        
        # Collect candidate's current configured skill strings
        current_skills = []
        for cat, skills in competencies.items():
            if isinstance(skills, list):
                current_skills.extend(skills)
            elif isinstance(skills, str):
                current_skills.extend([s.strip() for s in skills.split(",") if s.strip()])

        # Select benchmark terms based on persona
        is_mlops = persona.lower() in ("mlops", "ai", "platform") and persona.lower() != "de"

        if live_search_terms and isinstance(live_search_terms, list):
            skills_lower = [str(s).lower().strip() for s in live_search_terms]
            headline_lower = ""
        else:
            skills_lower = [s.lower().strip() for s in current_skills]
            headline_lower = headline.lower()

        if is_mlops:
            benchmark_terms = TARGET_MLOPS_KEYWORDS
            diluting_candidates = ["sysadmin", "frontend", "php", "wordpress", "html css", "junior web", "trivy only"]
            recommended_headline = (
                "MLOps Engineer | Kubernetes · Docker · Helm · Terraform · "
                "CI/CD · Prometheus · MLflow · Kafka · FastAPI · AWS EKS | "
                "2.5 YOE Platform Engineering | 15 Days Notice"
            )
            recommended_key_skills = (
                "Kubernetes, Docker, Helm, CI/CD, GitHub Actions, Terraform, "
                "Prometheus, Grafana, Triton, vLLM, MLflow, Kafka, Python, "
                "Linux, FastAPI, EKS, AWS, Redis"
            )
        else:
            benchmark_terms = TARGET_DE_KEYWORDS
            diluting_candidates = ["devops", "security analyst", "trivy", "jenkins only", "sysadmin"]
            recommended_headline = (
                "Azure Data Engineer | Azure Databricks · PySpark · Delta Lake · "
                "Azure Data Factory (ADF) · SQL · Apache Kafka · ADLS Gen2 · Terraform | "
                "2.5 YOE Cloud Data Platforms & Medallion Lakehouse"
            )
            recommended_key_skills = (
                "PySpark, Azure Databricks, Delta Lake, Azure Data Factory (ADF), "
                "SQL, Apache Kafka, ADLS Gen2, Medallion Architecture, Terraform, "
                "Python, Spark SQL, Data Pipelines, ETL, Unity Catalog, Docker, Linux"
            )

        matched_terms = []
        missing_high_intent = []
        for term in benchmark_terms:
            t_clean = term.strip()
            if t_clean.lower() in headline_lower or any(t_clean.lower() in s for s in skills_lower):
                matched_terms.append(t_clean)
            else:
                missing_high_intent.append(t_clean)

        diluting_terms = []
        for dt in diluting_candidates:
            if dt in headline_lower:
                diluting_terms.append(dt.capitalize())

        return {
            "current_headline": headline,
            "matched_terms": matched_terms,
            "matched_keywords": matched_terms,
            "missing_high_intent": missing_high_intent,
            "missing_keywords": missing_high_intent,
            "diluting_terms": diluting_terms,
            "recommended_headline": recommended_headline,
            "recommended_key_skills": recommended_key_skills,
            "persona": "mlops" if is_mlops else "de"
        }

    def display_weekly_report(self, page=None):
        """
        Displays the weekly performance audit:
        The 5 live numbers + conversion funnel analytics + keyword diff.
        """
        cookies = page.context.cookies() if page else None
        entitlements = self.get_session_entitlements(cookies=cookies)
        
        # Query live metrics if page is active, otherwise inspect latest history
        metrics = None
        if page:
            metrics = self.fetch_live_performance(page)
        elif os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    history = json.load(f)
                if history:
                    metrics = history[-1]
            except Exception:
                pass

        if not metrics:
            metrics = {
                "timestamp": datetime.now().strftime("%Y-%m-%d"),
                "search_appearances": 0,
                "profile_views": 0,
                "resume_downloads": 0,
                "contact_views": 0,
                "search_terms": [],
                "data_source": "No prior records (Connect live browser to query)"
            }

        apps = metrics.get("search_appearances", 0)
        views = metrics.get("profile_views", 0)
        downloads = metrics.get("resume_downloads", 0)
        contacts = metrics.get("contact_views", 0)
        terms = metrics.get("search_terms", [])

        # Conversion calculations
        ctr = round((views / apps) * 100, 1) if apps > 0 else 0.0
        contact_rate = round((contacts / views) * 100, 1) if views > 0 else 0.0

        print("\n" + "=" * 75)
        print("  📈 NAUKARIPRO: WEEKLY RECRUITER PERFORMANCE & CONVERSION AUDIT")
        print("  Focus: Azure Data Engineer (Single Unified Title | 2.5 YOE | ₹20 LPA)")
        print("=" * 75)
        print(f"  Candidate: {self.cfg['candidate']['name']} ({self.cfg['candidate']['email']})")
        print(f"  Account State: {entitlements['user_state']} | Server Entitlement: {entitlements['tier']}")
        print(f"  Data As Of: {metrics.get('timestamp', 'N/A')} ({metrics.get('data_source', 'Portal')})")
        print("-" * 75)

        print("  [THE 5 RECRUITER ACTION NUMBERS]")
        print(f"  1. Search Appearances: {apps:>6}  (Recruiters who saw your profile card in Resdex)")
        print(f"  2. Profile Views:      {views:>6}  (Recruiters who clicked and opened full profile)")
        print(f"  3. Resume Downloads:   {downloads:>6}  (Recruiters who saved your ATS resume PDF)")
        print(f"  4. Contact Views:      {contacts:>6}  (Recruiters who viewed phone/email — THE NORTH STAR ⭐)")
        print(f"  5. Recruiter Queries:  {', '.join(terms) if terms else 'Connect browser session to extract'}")
        print("-" * 75)

        print("  [CONVERSION FUNNEL ANALYTICS]")
        print(f"  • Click-Through Rate (Views / Searches):       {ctr}%  (Target: > 8%)")
        print(f"  • Contact Conversion Rate (Contacts / Views):  {contact_rate}%  (Target: > 15%)")
        print("-" * 75)

        # 100k Benchmark Pacing Analytics
        pacing = compute_benchmark_pacing(appearances=apps, days=7, target_monthly=100000)
        print("  [100K MONTHLY SEARCH BENCHMARK PACING (TARGET: 100,000 / MONTH)]")
        print(f"  • Required Daily Target:       {pacing.daily_target:>8.2f} appearances/day")
        print(f"  • Current Daily Pace (7d):     {pacing.current_daily_pace:>8.2f} appearances/day")
        print(f"  • Projected 30-Day Volume:     {pacing.projected_monthly:>8} searches")
        print(f"  • Monthly Attainment:          {pacing.percent_attainment:>7.2f}%")
        print(f"  • Benchmark Pacing Status:     {pacing.status}")
        if pacing.status == "DEFICIT":
            deficit = max(0, 100000 - pacing.projected_monthly)
            daily_shortfall = max(0.0, pacing.daily_target - pacing.current_daily_pace)
            print(f"  ⚠️ VELOCITY DEFICIT: {deficit:,} searches below 100k target ({daily_shortfall:.1f}/day shortfall)")
            print("    Remedy: Trigger daily 09:15 AM active recency bump and verify Top 25 Azure DE keywords.")
        elif pacing.status == "AHEAD":
            surplus = pacing.projected_monthly - 100000
            print(f"  🚀 AHEAD OF TARGET: +{surplus:,} searches above 100k benchmark velocity.")
        else:
            print("  ✓ ON TRACK: Exactly meeting 100k monthly search pace.")
        print("-" * 75)

        print("  [FUNNEL BOTTLENECK DIAGNOSTICS]")
        if apps == 0:
            print("  ⚠️ ZERO SEARCH APPEARANCES DETECTED:")
            print("    1. Recruiter Filters: Ensure Expected CTC is within ₹18-22 LPA band for 2.5 YOE.")
            print("    2. Active Recency: Run daily bump at 09:15 AM to enter 'Active Today' search filter.")
            print("    3. Title Alignment: Primary title must be strictly 'Azure Data Engineer'.")
        elif ctr < 5.0:
            print("  ⚠️ LOW CLICK-THROUGH RATE (< 5%):")
            print("    Recruiters see your profile in searches but aren't clicking.")
            print("    Remedy: Headline must start immediately with 'Azure Data Engineer | Azure Databricks'.")
        elif contact_rate < 10.0 and views > 5:
            print("  ⚠️ LOW CONTACT CONVERSION RATE (< 10%):")
            print("    Recruiters open your profile but don't unlock phone/email.")
            print("    Remedy: Ensure Project bullets and Key Skills emphasize production Lakehouse impact.")
        else:
            print("  ✓ Healthy Funnel Dynamics: Traffic is successfully converting to recruiter engagement.")
        print("-" * 75)

        # Keyword Diff Report
        diff = self.generate_keyword_diff_report(live_search_terms=terms)
        print("  [KEYWORD DIFF: RECRUITER SEARCH TERMS VS HEADLINE & SKILLS]")
        print(f"  • Matched High-Intent Keywords: {', '.join(diff['matched_terms'][:8]) if diff['matched_terms'] else 'None'}")
        if diff['missing_high_intent']:
            print(f"  • Missing High-Value Terms:     {', '.join(diff['missing_high_intent'][:5])}")
        if diff['diluting_terms']:
            print(f"  • Diluting Keywords to Prune:   {', '.join(diff['diluting_terms'])}")
        print("\n  [RECOMMENDED SYNCHRONIZED HEADLINE]")
        print(f"  👉 \"{diff['recommended_headline']}\"")
        print("\n  [RECOMMENDED KEY SKILLS (EXACT SPELLINGS FOR RESDEX)]")
        print(f"  👉 {diff['recommended_key_skills']}")
        print("=" * 75 + "\n")
        return metrics

    def display_report(self, page=None):
        """
        Displays recruiter performance report and keyword diff.
        Aliases to display_weekly_report for CLI and automation compatibility.
        """
        return self.display_weekly_report(page=page)

    def generate_report(self, page=None):
        """Generates performance report."""
        return self.display_weekly_report(page=page)

    def record_weekly_telemetry(
        self,
        week_start_date: Optional[str] = None,
        search_appearances: Optional[int] = None,
        profile_views: int = 0,
        contact_views: int = 0,
        platform: str = "naukri",
        week_start: Optional[str] = None,
        appearances: Optional[int] = None,
        screenshot_path: Optional[str] = None,
        db_path: Optional[str] = None
    ) -> bool:
        """Stores weekly telemetry directly into SQLite search_appearance_weekly table conforming to §4.6 and §4.7."""
        from naukari_pro.modules.learning.attribution import AttributionEngine
        engine = AttributionEngine(db_path=db_path)
        return engine.record_weekly_appearances(
            week_start_date=week_start_date,
            search_appearances=search_appearances,
            profile_views=profile_views,
            contact_views=contact_views,
            platform=platform,
            week_start=week_start,
            appearances=appearances,
            screenshot_path=screenshot_path
        )


# Canonical alias for CLI and module compatibility
ProfilePerformanceTracker = ProfilePerformanceEngine


def get_unified_speedometer(target_total: int = MONTHLY_SEARCH_BENCHMARK, target_days: int = 30) -> Unified100KSpeedometer:
    """Convenience factory returning an initialized Unified100KSpeedometer instance."""
    return Unified100KSpeedometer(target_total=target_total, target_days=target_days)


def generate_keyword_diff_report(live_search_terms=None, persona: str = "de") -> Dict[str, Any]:
    """Module-level helper to generate keyword diff report for specified persona."""
    engine = ProfilePerformanceEngine()
    return engine.generate_keyword_diff_report(live_search_terms=live_search_terms, persona=persona)


def log_performance_snapshot(
    metrics: Optional[Dict[str, Any]] = None,
    tracker_path: Optional[str] = None,
    history_file: Optional[str] = None,
    db_path: Optional[str] = None,
    **kwargs
) -> bool:
    """Module-level helper to log performance snapshot across JSON, Excel, and SQLite sinks."""
    h_file = history_file or kwargs.get("json_path") or HISTORY_FILE
    t_path = tracker_path or kwargs.get("excel_path") or TRACKER_PATH
    d_path = db_path or kwargs.get("db_path")
    engine = ProfilePerformanceEngine(tracker_path=t_path, history_file=h_file)
    data = dict(metrics or {})
    data.update(kwargs)
    return engine.log_performance_snapshot(
        metrics=data,
        tracker_path=t_path,
        history_file=h_file,
        db_path=d_path
    )


__all__ = [
    "ProfilePerformanceEngine",
    "ProfilePerformanceTracker",
    "compute_benchmark_pacing",
    "compute_unified_pacing",
    "Unified100KSpeedometer",
    "get_unified_speedometer",
    "generate_keyword_diff_report",
    "log_performance_snapshot",
    "BenchmarkPacing",
    "MONTHLY_SEARCH_BENCHMARK",
    "DAILY_SEARCH_BENCHMARK",
    "TARGET_DE_KEYWORDS",
    "TARGET_MLOPS_KEYWORDS"
]

