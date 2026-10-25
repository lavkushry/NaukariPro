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

def compute_benchmark_pacing(appearances: int, days: int = 7, target_monthly: int = 100000) -> BenchmarkPacing:
    """Computes daily pace, 30-day projected velocity, and target attainment against 100k monthly benchmark."""
    safe_days = max(days, 1)
    safe_apps = max(appearances, 0)
    daily_pace = round(safe_apps / safe_days, 2)
    daily_target = round(target_monthly / 30.0, 2)
    projected_monthly = int(round(daily_pace * 30))
    percent_attainment = round((projected_monthly / target_monthly) * 100, 2) if target_monthly > 0 else 0.0

    if projected_monthly > target_monthly:
        status = "AHEAD"
    elif projected_monthly == target_monthly:
        status = "ON_TRACK"
    else:
        status = "DEFICIT"

    return BenchmarkPacing(
        total_searches_30d=safe_apps,
        target_monthly=target_monthly,
        daily_target=daily_target,
        current_daily_pace=daily_pace,
        projected_monthly=projected_monthly,
        percent_attainment=percent_attainment,
        status=status
    )

# Verified Azure Data Engineer target keywords and spelling standards
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
    "Data Lakehouse"
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
    def __init__(self):
        self.cfg = load_config()

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

    def log_performance_snapshot(self, metrics, tracker_path=None, history_file=None):
        """Persists the 5 live numbers and benchmark pacing to historical JSON ledger and Excel tracker."""
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

        apps = max(metrics.get("search_appearances", 0), 0)
        views = max(metrics.get("profile_views", 0), 0)
        downloads = max(metrics.get("resume_downloads", 0), 0)
        contacts = max(metrics.get("contact_views", 0), 0)

        pacing = compute_benchmark_pacing(appearances=apps, days=7, target_monthly=100000)
        ctr = round((views / apps) * 100, 2) if apps > 0 else 0.0
        contact_conv = round((contacts / views) * 100, 2) if views > 0 else 0.0

        metrics["daily_pace"] = pacing.current_daily_pace
        metrics["projected_monthly"] = pacing.projected_monthly
        metrics["percent_attainment"] = pacing.percent_attainment
        metrics["pacing_status"] = pacing.status
        metrics["ctr_pct"] = ctr
        metrics["contact_conv_pct"] = contact_conv

        history.append(metrics)
        try:
            with open(h_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            logger.warning("Could not save performance history JSON: %s", e)

        # Log to Excel Tracker under Recruiter_Performance_Log
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
            return True
        except Exception as e:
            logger.warning("Could not append to Excel tracker: %s", e)
            return False

    def generate_keyword_diff_report(self, live_search_terms=None):
        """
        Calculates exact diff between:
        1. Recruiter search terms that found candidate (from Profile Performance)
        2. Verified target Azure Data Engineer keywords
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

        headline_lower = headline.lower()
        skills_lower = [s.lower() for s in current_skills]

        # Use live search terms if available, otherwise target DE keywords
        benchmark_terms = live_search_terms if (live_search_terms and len(live_search_terms) > 0) else TARGET_DE_KEYWORDS

        matched_terms = []
        missing_high_intent = []
        for term in benchmark_terms:
            t_clean = term.strip()
            if t_clean.lower() in headline_lower or any(t_clean.lower() in s for s in skills_lower):
                matched_terms.append(t_clean)
            else:
                missing_high_intent.append(t_clean)

        # Detect diluting terms (generic non-DE terms that dilute data platform ranking)
        diluting_terms = []
        diluting_candidates = ["devops", "security analyst", "trivy", "jenkins only", "sysadmin"]
        for dt in diluting_candidates:
            if dt in headline_lower:
                diluting_terms.append(dt.capitalize())

        # Build recommended aligned headline
        recommended_headline = (
            "Azure Data Engineer | Azure Databricks · PySpark · Delta Lake · "
            "Azure Data Factory (ADF) · SQL · Apache Kafka · ADLS Gen2 · Terraform | "
            "2.5 YOE Cloud Data Platforms & Medallion Lakehouse"
        )

        return {
            "current_headline": headline,
            "matched_terms": matched_terms,
            "missing_high_intent": missing_high_intent,
            "diluting_terms": diluting_terms,
            "recommended_headline": recommended_headline,
            "recommended_key_skills": (
                "PySpark, Azure Databricks, Delta Lake, Azure Data Factory (ADF), "
                "SQL, Apache Kafka, ADLS Gen2, Medallion Architecture, Terraform, "
                "Python, Spark SQL, Data Pipelines, ETL, Unity Catalog, Docker, Linux"
            )
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


# Canonical alias for CLI and module compatibility
ProfilePerformanceTracker = ProfilePerformanceEngine

__all__ = [
    "ProfilePerformanceEngine",
    "ProfilePerformanceTracker",
    "compute_benchmark_pacing",
    "BenchmarkPacing",
    "MONTHLY_SEARCH_BENCHMARK",
    "DAILY_SEARCH_BENCHMARK",
    "TARGET_DE_KEYWORDS"
]

