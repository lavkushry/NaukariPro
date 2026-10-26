"""
naukariPro: High-Performance Autonomous CLI Interface
Targeting ₹25 LPA Azure Data Engineer Opportunities
Ground-truth metrics, real server entitlement inspection, and robust error handling.
"""

import os
import sys
import argparse

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright

from naukari_pro.session import get_stealth_context, ensure_authenticated, save_session_cookies, detect_challenge
from naukari_pro.config import load_config
from naukari_pro.modules.auto_apply import AutoApplyEngine
from naukari_pro.modules.job_alerts import InstantAlertsEngine
from naukari_pro.modules.profile_enhancer import ProfileEnhancerEngine
from naukari_pro.modules.hidden_jobs import HiddenJobsEngine
from naukari_pro.modules.resume_maker import AIResumeMaker
from naukari_pro.modules.interview_prep import InterviewPrepEngine
from naukari_pro.modules.skill_insights import SkillInsightsEngine
from naukari_pro.modules.hiring_trends import HiringTrendsEngine
from naukari_pro.modules.early_access import EarlyAccessEngine
from naukari_pro.modules.career_portals import CareerPortalFiller
from naukari_pro.modules.multi_search import UniversalJobSearchEngine
from naukari_pro.modules.pro_autopilot import ProAutoPilotEngine
from naukari_pro.modules.profile_performance import ProfilePerformanceEngine, ProfilePerformanceTracker
import asyncio
import inspect
from naukari_pro.modules.linkedin_session import (
    LinkedInSessionManager,
    LinkedInCookieMissingError,
    LinkedInCookieExpiredError,
    LinkedInCheckpointError,
    mask_cookie_token,
)

BANNER = r"""
========================================================================
   __  _ ___  __  __ __ ___  _  ___  ____  ___ 
  / / / // _ \/ / / // // _ \/ |/ _ \/ __ \/ _ \
 / /_/ // // / /_/ // // // /    / // /_/ // ___/
 \___\_/\___/\___\_/_/ \___/_/|_/_/ \____/_/    
========================================================================
   Autonomous AI Career Suite | Target: ₹25 LPA Azure Data Engineer
   Candidate: Lavkush Kumar (2.5 YOE | CGI / PNC Bank GCC | HFCL)
========================================================================
"""

def print_menu():
    print(BANNER)
    print("  [P] PRO AUTONOMOUS AUTO-PILOT (Complete All-in-One AI Career Engine)")
    print("  [W] Weekly Recruiter Performance & Keyword Diff Report (The 5 Live Numbers)")
    print("  [E] Server Entitlements & Profile Performance (JWT & Search Stats)")
    print("  [1] Auto-Apply on Naukri (1-Click & Verified Questionnaire Solver)")
    print("  [2] Instant Job Alerts (Cross-platform Desktop & In-App Alerts)")
    print("  [3] AI-Enhanced Profile (Once-a-Day Timestamp Touch & Audit)")
    print("  [4] Hidden Job Opportunities (Inquiries, Recommended Feed & GCCs)")
    print("  [5] AI Resume Maker (1-Page ATS PDF & Quality Scorecard)")
    print("  [6] AI Interview Prep Tools (Master Q&A Bank for ₹25 LPA)")
    print("  [M] Interactive AI Mock Interview Evaluator (Answer Scoring & Coaching)")
    print("  [7] In-Demand Skill Insights (Skill Matrix & Live Market Sampling)")
    print("  [8] Industry Hiring Trends (Salary Benchmarks & GCC Packages)")
    print("  [9] Early Access & NVites (Scrape Homepage & Inbox NVites)")
    print("  [S] Multi-Source Job Hunter (Search Naukri + LinkedIn + Hacker News)")
    print("  [C] Career Portal Auto-Filler (Greenhouse / Ashby / Lever / Workday)")
    print("  [D] Run Complete Daily Autonomous Cycle (Bump + Scan + Apply + Log)")
    print("  [G] AGY Autonomous Scheduler (Linux systemd & agy CLI schedule)")
    print("  [A] Authenticate Session (One-time Login & Cookie Persistence)")
    print("  [V] LinkedIn Session Diagnostic (Verify li_at cookie & Identity)")
    print("  [L] LinkedIn Easy Apply (Autonomous Multi-Step Bot & Screening Solver)")
    print("  [0] Exit")
    print("========================================================================")

def handle_pro(limit=10, headless=False, dry_run=False, force=False):
    engine = ProAutoPilotEngine(limit=limit, headless=headless, dry_run=dry_run, force=force)
    engine.run_full_pipeline()

def handle_performance(headless=False):
    engine = ProfilePerformanceEngine()
    try:
        with sync_playwright() as p:
            context = get_stealth_context(p, headless=headless)
            page = context.pages[0] if context.pages else context.new_page()
            if ensure_authenticated(page, headless=headless):
                engine.display_report(page=page)
            else:
                engine.display_report()
            context.close()
    except Exception as e:
        print(f"  [!] Notice launching browser for performance report: {e}")
        engine.display_report()

def handle_weekly_report(headless=False):
    engine = ProfilePerformanceEngine()
    try:
        with sync_playwright() as p:
            context = get_stealth_context(p, headless=headless)
            page = context.pages[0] if context.pages else context.new_page()
            if ensure_authenticated(page, headless=headless):
                engine.display_weekly_report(page=page)
            else:
                engine.display_weekly_report()
            context.close()
    except Exception as e:
        print(f"  [!] Notice launching browser for weekly report: {e}")
        engine.display_weekly_report()

def handle_auto_apply(headless=False, limit=20, dry_run=False):
    print("\n[*] Starting Auto-Apply on Naukri...")
    engine = AutoApplyEngine(dry_run=dry_run)
    engine.run(headless=headless, limit=limit, dry_run=dry_run)

def handle_alerts(headless=False):
    print("\n[*] Scanning for Instant Job Alerts...")
    engine = InstantAlertsEngine()
    with sync_playwright() as p:
        context = get_stealth_context(p, headless=headless)
        page = context.pages[0] if context.pages else context.new_page()
        if ensure_authenticated(page, headless=headless):
            alerts = engine.scan_for_alerts(page)
            print(f"\n[+] Identified {len(alerts)} High-Priority Vacancies:")
            for a in alerts:
                print(f" -> [{a['match_score']}% Match] {a['title']} | {a['company']} | {a['location']} | {a['salary']}")
                print(f"    URL: {a['url']}")
        context.close()

def handle_profile(headless=False, force=False):
    print("\n[*] Running AI-Enhanced Profile Module (Once-a-Day Recency Throttle)...")
    engine = ProfileEnhancerEngine()
    
    with sync_playwright() as p:
        context = get_stealth_context(p, headless=headless)
        page = context.pages[0] if context.pages else context.new_page()
        
        audit = engine.audit_profile_strength(page=page if not headless else None)
        print(f"\n[+] Profile Resdex Strength Score: {audit['score']}/100 ({audit['tier']})")
        print(f"    Source: {audit.get('source', 'Config Facts')}")
        for name, desc, pts in audit['checklist']:
            print(f"  [✓] {name:<26} (+{pts} pts) : {desc}")

        if ensure_authenticated(page, headless=headless):
            engine.bump_profile(page, force=force)
        context.close()

def handle_hidden_jobs(headless=False):
    print("\n[*] Discovering Hidden & Off-Market Opportunities...")
    engine = HiddenJobsEngine()
    with sync_playwright() as p:
        context = get_stealth_context(p, headless=headless)
        page = context.pages[0] if context.pages else context.new_page()
        if ensure_authenticated(page, headless=headless):
            jobs = engine.discover_hidden_opportunities(page)
            print(f"\n[+] Discovered {len(jobs)} Off-Market Openings:")
            for j in jobs:
                gcc_tag = " [TOP GCC]" if j.get("is_gcc") else ""
                print(f" -> {j['title']} | {j['company']}{gcc_tag} | {j['location']} ({j['source']})")
                print(f"    URL: {j['url']}")
        context.close()

def handle_resume_maker(jd=None):
    print("\n[*] Compiling AI ATS Resume strictly from config facts...")
    jd_content = None
    if jd:
        if os.path.exists(jd):
            try:
                with open(jd, "r", encoding="utf-8") as f:
                    jd_content = f.read()
                print(f"  [✓] Loaded target JD from file: {jd}")
            except Exception as e:
                print(f"  [!] Could not read JD file ({e}), treating as raw text.")
                jd_content = jd
        else:
            jd_content = jd
        print("  [✓] Tailoring skills and bullets against target Job Description keywords.")

    maker = AIResumeMaker()
    out = maker.build_ats_resume_pdf(jd_text=jd_content)
    print(f"\n[✓] ATS Resume generated successfully: {out}")

    # Generate objective Quality Scorecard
    score = maker.calculate_resume_quality_score(jd_text=jd_content)
    print("\n" + "=" * 65)
    print(f"  📋 ATS RESUME QUALITY SCORECARD — {score['overall_score']}/100")
    print("=" * 65)
    print(f"  • ATS Layout Compliance:    {score.get('ats_compliance_display', score['ats_compliance_score'])}")
    print(f"  • Quantified Metrics Ratio: {score.get('quantified_metrics_display', score['quantified_metrics_score'])}")
    print(f"  • Target Keyword Coverage:  {score.get('keyword_alignment_display', score['keyword_alignment_score'])}")
    print(f"  • Key Matched Keywords:     {', '.join(score['matched_keywords'])}")
    print("  • Evaluator Recommendations:")
    for rec in score['recommendations']:
        print(f"    👉 {rec}")
    print("=" * 65 + "\n")

def handle_interview_prep(mock=False):
    engine = InterviewPrepEngine()
    if mock:
        engine.run_interactive_mock_interview()
    else:
        engine.display_full_prep_guide()

def handle_skill_insights(headless=False):
    engine = SkillInsightsEngine()
    live_samples = None
    if not headless:
        try:
            with sync_playwright() as p:
                context = get_stealth_context(p, headless=True)
                page = context.pages[0] if context.pages else context.new_page()
                live_samples = engine.sample_live_skill_demand(page)
                context.close()
        except Exception:
            pass
    engine.display_insights(live_data=live_samples)

def handle_hiring_trends(headless=False):
    engine = HiringTrendsEngine()
    live_samples = None
    if not headless:
        try:
            with sync_playwright() as p:
                context = get_stealth_context(p, headless=True)
                page = context.pages[0] if context.pages else context.new_page()
                live_samples = engine.sample_live_salary_disclosure(page)
                context.close()
        except Exception:
            pass
    engine.display_market_report(live_data=live_samples)

def handle_portal_apply(url=None, company="Company", role="Azure Data Engineer", jd="", headless=False, dry_run=False):
    filler = CareerPortalFiller()
    if not url:
        if dry_run:
            url = "https://boards.greenhouse.io/microsoft/jobs/123"
        else:
            print("\n" + "=" * 65)
            print("  🌐 CAREER PORTAL AUTO-FILLER (Job-Apply Engine)")
            print("  Supported: Greenhouse, Ashby, Lever, Workday, Rippling, Portals")
            print("=" * 65)
            url = input("Enter job application URL: ").strip()
            if not url:
                print("URL cannot be empty.")
                return
            c_in = input("Company name (optional, press Enter for auto): ").strip()
            if c_in: company = c_in
            r_in = input("Role title (optional, press Enter for 'Azure Data Engineer'): ").strip()
            if r_in: role = r_in

    return filler.fill(url, company=company, role=role, headless=headless, dry_run=dry_run, raw_jd=jd)

def handle_multi_search(dry_run=False):
    engine = UniversalJobSearchEngine()
    return engine.run_multi_search(dry_run=dry_run)

def handle_daily_cycle(headless=False, dry_run=False, force=False):
    print("\n[*] Launching Complete Autonomous Daily Cycle...")
    # 1. Profile Synchronization & Active Today Bump
    print("\n[Step 1/3] Full Profile Synchronization & Resdex Recency Touch...")
    if not dry_run:
        try:
            from scripts.sync_naukri_live_profile import sync_full_naukri_profile
            with sync_playwright() as p:
                context = get_stealth_context(p, headless=headless)
                page = context.pages[0] if context.pages else context.new_page()
                if ensure_authenticated(page, headless=headless):
                    sync_full_naukri_profile(page, force=force)
                context.close()
        except Exception as e:
            print(f"[!] Profile sync notice: {e}. Executing standard recency bump...")
            handle_profile(headless=headless, force=force)
    else:
        print("  [DRY-RUN] Simulated profile headline & skills refresh (No browser opened).")

    # 2. Auto-apply
    print("\n[Step 2/3] Autonomous Auto-Apply on Naukri...")
    handle_auto_apply(headless=headless, limit=20, dry_run=dry_run)

    # 3. Alerts
    print("\n[Step 3/3] Scanning Instant High-Priority Alerts...")
    if not dry_run:
        handle_alerts(headless=headless)
    else:
        print("  [DRY-RUN] Simulated instant alerts scan: Found top vacancy 'Microsoft GCC hiring Lead Azure Data Engineer' (No browser opened).")

def handle_auth():
    print("\n[*] Launching browser window for authentic Naukri login...")
    with sync_playwright() as p:
        context = get_stealth_context(p, headless=False)
        page = context.pages[0] if context.pages else context.new_page()

        try:
            page.goto("https://www.naukri.com/nlogin/login", wait_until="domcontentloaded", timeout=30000)
            import time
            time.sleep(2)

            # Auto-fill credentials from config/.env if login form is displayed
            if "nlogin" in page.url or page.locator("#usernameField").count() > 0:
                cfg = load_config()
                cand = cfg.get("candidate", {})
                email = os.getenv("NAUKRI_EMAIL") or cand.get("email", "")
                password = os.getenv("NAUKRI_PASSWORD", "")

                user_field = page.locator("#usernameField").first
                if user_field.is_visible() and email:
                    user_field.fill(email)
                    time.sleep(0.3)
                pass_field = page.locator("#passwordField").first
                if pass_field.is_visible() and password:
                    pass_field.fill(password)
                    time.sleep(0.3)
                login_btn = page.locator("button[type='submit']").first
                if login_btn.is_visible() and password:
                    login_btn.click()
                    time.sleep(2)
                elif not password:
                    print("[!] Notice: NAUKRI_PASSWORD not found in .env. Please type your password in the browser window.")

            challenge = detect_challenge(page)
            if challenge:
                print(f"\n⚠️ {challenge} detected on login page!")

            print("\n" + "=" * 65)
            print("  🔑 CREDENTIALS SUBMITTED!")
            print("  If a visual challenge (Captcha/OTP) appears in the browser window,")
            print("  please complete it manually. Waiting up to 3 minutes for confirmation...")
            print("=" * 65 + "\n")

            page.wait_for_url("**/mnjuser/**", timeout=180000)
            save_session_cookies(context)
            print("\n[✓] SUCCESS: Authenticated session confirmed and cookies synchronized to disk!")
        except Exception as e:
            print(f"\n[!] Notice during login: {e}")

        context.close()

def handle_early_access(headless=False):
    print("\n[*] Scanning Early Access Roles and Recruiter NVites...")
    engine = EarlyAccessEngine()
    with sync_playwright() as p:
        context = get_stealth_context(p, headless=headless)
        page = context.pages[0] if context.pages else context.new_page()
        if ensure_authenticated(page, headless=headless):
            res = engine.scan_early_access(page)
            print(f"\n[+] Profile Status: {res['profile_status']}")
            print(f"[+] Early Access Roles Detected: {res['early_roles_detected']}")
            if res['nvites']:
                print(f"[+] Direct Recruiter Shortlists / NVites:")
                for n in res['nvites']:
                    print(f"  • {n}")
        context.close()

def handle_agy_schedule(action="status"):
    import subprocess
    import os
    workspace = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    runner = os.path.join(workspace, "agy_schedule_runner.sh")
    installer = os.path.join(workspace, "install_linux_schedule.sh")

    if action == "install":
        print("\n[*] Installing NaukariPro AGY Autonomous Linux Scheduler...")
        subprocess.run(["bash", installer], check=False)
    elif action == "run":
        print("\n[*] Triggering immediate AGY Autonomous Cycle...")
        subprocess.run(["bash", runner], check=False)
    elif action == "logs":
        history = os.path.join(workspace, "logs", "agy_schedule_history.log")
        if os.path.exists(history):
            print(f"\n[*] Recent logs from {history}:")
            subprocess.run(["tail", "-n", "50", history])
        else:
            print(f"\n[*] No schedule logs found yet in {history}")
    else:  # status
        print("\n[*] Checking Linux systemd user timers (naukaripro-agy):")
        subprocess.run(["systemctl", "--user", "list-timers", "--no-pager"], check=False)
        print("\n[*] Checking Crontab Fallback:")
        subprocess.run(["crontab", "-l"], check=False)

def handle_linkedin_verify(args=None, headless: bool = True) -> int:
    """
    Executes LinkedIn session diagnostic verification and prints structured status box.
    Uses pure async Playwright inside asyncio.run() to prevent event loop collisions.
    Returns:
        0 if session is VALID
        1 if session is EXPIRED, COOKIE_MISSING, or UNREACHABLE
        2 if session is CHECKPOINT
    """
    if hasattr(args, "headed"):
        headless = not getattr(args, "headed", False)
    elif hasattr(args, "headless"):
        headless = getattr(args, "headless", True)
    elif isinstance(args, bool):
        headless = args

    manager = LinkedInSessionManager()
    token = None
    try:
        token = manager.get_li_at_cookie(raise_if_missing=True)
    except LinkedInCookieMissingError:
        token = None

    if not token:
        print("\n" + "=" * 72)
        print("   LINKEDIN SESSION DIAGNOSTIC & IDENTITY VERIFICATION")
        print("=" * 72)
        print("  • Cookie Source:          NONE (Checked .env and linkedin_system/)")
        print("  • Cookie Present:         NO")
        print("  • Session Status:         COOKIE_MISSING")
        print("  • Authenticated Identity: UNKNOWN")
        print("=" * 72)
        print("  DIAGNOSTIC DETAILS & REMEDIATION:")
        print("  [!] No LinkedIn authentication cookie found.")
        print("  👉 Remediation Instructions:")
        print("     1. Open Chrome on your desktop and log in to https://www.linkedin.com.")
        print("     2. Open DevTools (F12) -> Application tab -> Cookies -> https://www.linkedin.com.")
        print("     3. Copy the value of cookie named 'li_at'.")
        print("     4. Add to /Users/lavkushkumar/Desktop/Resume/.env:")
        print('        LINKEDIN_LI_AT="your_li_at_cookie_value_here"')
        print("     5. Alternatively, export LINKEDIN_LI_AT=\"your_cookie\" in your environment.")
        print("=" * 72 + "\n")
        return 1

    masked_token = mask_cookie_token(token)
    source_desc = getattr(manager, "last_cookie_source", ".env (LINKEDIN_LI_AT)")

    async def _run_verify_async():
        async with async_playwright() as p:
            context = await manager.create_stealth_context(p, headless=headless)
            try:
                page = context.pages[0] if (hasattr(context, "pages") and context.pages) else await context.new_page()
                res = await manager.verify_session(page, raise_for_status=False)
                return res
            finally:
                if hasattr(context, "close"):
                    c_res = context.close()
                    if inspect.isawaitable(c_res):
                        await c_res

    diag = {}
    try:
        diag = asyncio.run(_run_verify_async())
    except LinkedInCheckpointError as e:
        diag = {
            "status": "CHECKPOINT",
            "authenticated": False,
            "checkpoint_detected": True,
            "candidate_name": None,
            "headline": None,
            "final_url": getattr(e, "checkpoint_url", "https://www.linkedin.com/checkpoint/challenge"),
            "detail": str(e)
        }
    except LinkedInCookieExpiredError as e:
        diag = {
            "status": "EXPIRED",
            "authenticated": False,
            "candidate_name": None,
            "headline": None,
            "final_url": getattr(e, "redirect_url", "https://www.linkedin.com/authwall"),
            "detail": str(e)
        }
    except Exception as e:
        err_msg = str(e)
        if "timeout" in err_msg.lower() or "err_" in err_msg.lower() or "dns" in err_msg.lower():
            status_val = "UNREACHABLE"
        else:
            status_val = "EXPIRED"
        diag = {
            "status": status_val,
            "authenticated": False,
            "candidate_name": None,
            "headline": None,
            "detail": f"Verification error: {e}"
        }

    status = diag.get("status", "UNKNOWN")
    candidate_name = diag.get("candidate_name") or "UNKNOWN"
    headline = diag.get("headline") or diag.get("candidate_headline") or "N/A"
    final_url = diag.get("final_url") or diag.get("feed_url") or "N/A"
    dom_verified = diag.get("dom_verified", False)

    print("\n" + "=" * 72)
    print("   LINKEDIN SESSION DIAGNOSTIC & IDENTITY VERIFICATION")
    print("=" * 72)
    print(f"  • Cookie Source:          {source_desc}")
    print("  • Cookie Present:         YES")
    print(f"  • Cookie Token:           {masked_token}")
    print(f"  • Session Status:         {status}")
    print(f"  • Authenticated Identity: {candidate_name}")
    print(f"  • Professional Headline:  {headline}")
    if final_url != "N/A":
        print(f"  • Verified URL:           {final_url}")
    print("=" * 72)
    print("  DIAGNOSTIC DETAILS & REMEDIATION:")

    if status == "VALID":
        print("  [✓] LinkedIn session is active, valid, and authenticated.")
        if dom_verified:
            print(f"  [✓] Verified candidate identity on live DOM: {candidate_name}.")
        print("  [✓] System is fully ready for autonomous Easy Apply execution.")
        print("=" * 72 + "\n")
        return 0
    elif status == "CHECKPOINT":
        print("  ⚠️ LinkedIn security checkpoint or CAPTCHA challenge encountered!")
        print("  👉 Remediation Instructions:")
        print("     1. Run with visible GUI: './naukariPro linkedin-verify --headed'")
        print("     2. Complete the visual challenge or email/SMS OTP in the browser window.")
        print("     3. Once at https://www.linkedin.com/feed/, copy the refreshed 'li_at' cookie and update .env.")
        print("=" * 72 + "\n")
        return 2
    elif status == "UNREACHABLE":
        print("  [!] LinkedIn is unreachable. Check network connection or DNS resolution.")
        print(f"  👉 Diagnostic Detail: {diag.get('detail', 'Network timeout or unreachable host')}")
        print("=" * 72 + "\n")
        return 1
    elif status == "RATE_LIMITED":
        print("  ⚠️ LinkedIn returned HTTP 429 (Too Many Requests / IP Cooldown).")
        print("  👉 Remediation Instructions:")
        print("     1. LinkedIn has temporarily throttled this IP address from repeated rapid page requests.")
        print("     2. Wait 10-15 minutes for the rate limit cooldown to automatically expire.")
        print("     3. Or run with residential proxy in .env (e.g. LINKEDIN_PROXY=http://user:pass@host:port).")
        print("=" * 72 + "\n")
        return 1
    else:  # EXPIRED, UNKNOWN or other
        print("  [!] The provided li_at cookie has expired or was revoked by LinkedIn.")
        print("  👉 Remediation Instructions:")
        print("     1. Open Chrome on your desktop and log in to https://www.linkedin.com.")
        print("     2. Open DevTools (F12) -> Application -> Cookies -> https://www.linkedin.com.")
        print("     3. Copy the fresh value of cookie named 'li_at'.")
        print("     4. Update LINKEDIN_LI_AT in .env.")
        print("=" * 72 + "\n")
        return 1

def handle_linkedin_apply(args=None, limit=25, dry_run=False, headless=True, min_score=70.0, keyword=None, location=None):
    """
    Executes autonomous LinkedIn Easy Apply workflow across target hubs and keywords.
    Strictly gates jobs by score (>= 70.0%) and handles multi-step screening forms.
    """
    if args:
        if hasattr(args, "limit") and args.limit is not None:
            limit = args.limit
        if hasattr(args, "dry_run"):
            dry_run = getattr(args, "dry_run", dry_run)
        if hasattr(args, "headed"):
            headless = not getattr(args, "headed", False)
        elif hasattr(args, "headless"):
            headless = getattr(args, "headless", headless)
        if hasattr(args, "min_score") and args.min_score is not None:
            min_score = args.min_score
        if hasattr(args, "keyword") and args.keyword:
            keyword = args.keyword
        if hasattr(args, "location") and args.location:
            location = args.location

    print("\n" + "=" * 72)
    print("   LINKEDIN AUTONOMOUS EASY APPLY ENGINE")
    print("=" * 72)
    mode_str = "DRY-RUN SIMULATION (NO SUBMISSIONS)" if dry_run else "LIVE AUTONOMOUS SUBMISSIONS"
    print(f"  • Execution Mode:        {mode_str}")
    print(f"  • Daily Cycle Limit:     {limit} applications")
    print(f"  • Minimum Match Gate:    {min_score}%")
    print(f"  • Browser Mode:          {'Headless' if headless else 'Visible GUI'}")
    if keyword:
        print(f"  • Keyword Filter:        {keyword}")
    if location:
        print(f"  • Location Filter:       {location}")
    print("=" * 72)

    from naukari_pro.modules.linkedin_apply import LinkedInApplyEngine
    apply_engine = LinkedInApplyEngine(min_score=min_score)

    keywords_list = [keyword] if keyword else None
    locations_list = [location] if location else None

    try:
        stats = asyncio.run(apply_engine.run_apply_cycle(
            keywords=keywords_list,
            locations=locations_list,
            limit=limit,
            dry_run=dry_run,
            headless=headless
        ))
    except Exception as e:
        print(f"\n[!] Execution error during LinkedIn apply cycle: {e}")
        return 1

    print("\n" + "=" * 72)
    print("   LINKEDIN APPLY CYCLE RESULTS SUMMARY")
    print("=" * 72)
    print(f"  • Vacancies Discovered:  {stats.get('discovered', 0)}")
    print(f"  • Passed Match Gate:     {stats.get('scored_above_threshold', 0)}")
    if dry_run:
        print(f"  • Dry-Run Verified:      {stats.get('dry_run_verified', 0)}")
    else:
        print(f"  • Applications Sent:     {stats.get('applied', 0)}")
    print(f"  • Skipped / Gated Out:   {stats.get('skipped', 0)}")
    print(f"  • Errors / Stalled:      {stats.get('failed', 0)}")
    print("  • Excel Tracker:         Naukri_Live_Application_Tracker.xlsx")
    print("  • Tracker Worksheet:     LinkedIn_Applications_Log")
    print("=" * 72 + "\n")
    return 0

def interactive_loop():
    while True:
        print_menu()
        choice = input("Select an option [0-9, P, W, E, M, S, C, D, G, A, V, L]: ").strip().upper()
        if choice == "P":
            handle_pro()
        elif choice == "W":
            handle_weekly_report()
        elif choice == "E":
            handle_performance()
        elif choice == "G":
            handle_agy_schedule("status")
        elif choice == "1":
            handle_auto_apply()
        elif choice == "2":
            handle_alerts()
        elif choice == "3":
            handle_profile()
        elif choice == "4":
            handle_hidden_jobs()
        elif choice == "5":
            handle_resume_maker()
        elif choice == "6":
            handle_interview_prep()
        elif choice == "M":
            handle_interview_prep(mock=True)
        elif choice == "7":
            handle_skill_insights()
        elif choice == "8":
            handle_hiring_trends()
        elif choice == "9":
            handle_early_access()
        elif choice == "S":
            handle_multi_search()
        elif choice == "C":
            handle_portal_apply()
        elif choice == "D":
            handle_daily_cycle()
        elif choice == "A":
            handle_auth()
        elif choice == "V":
            handle_linkedin_verify(headless=True)
        elif choice == "L":
            handle_linkedin_apply(dry_run=True)
        elif choice == "0":
            print("\nExiting naukariPro. Good luck with your ₹25 LPA goal!\n")
            break
        else:
            print("\nInvalid choice. Please select from the menu.")
        input("\nPress Enter to return to main menu...")

def main():
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--headless", action="store_true", help="Run browser in background")
    common_parser.add_argument("--limit", type=int, default=20, help="Max daily applications")
    common_parser.add_argument("--dry-run", action="store_true", help="Simulate job matches, answers, and tracker logging without submitting live applications")

    parser = argparse.ArgumentParser(description="naukariPro Career Suite", parents=[common_parser])
    subparsers = parser.add_subparsers(dest="command")
    pro_parser = subparsers.add_parser("pro", help="Run Complete All-in-One Pro Autonomous Pipeline", parents=[common_parser])
    pro_parser.add_argument("--force", action="store_true", help="Force profile sync and bump even if already updated today")

    for cmd, hlp in [
        ("weekly-report", "Run weekly 5-number recruiter performance & keyword diff audit"),
        ("performance", "Inspect Server-Side Entitlements & Profile Analytics"),
        ("auto-apply", "Auto-Apply to target vacancies"),
        ("dry-run", "Execute offline dry-run simulation across multi-channel and 1-click apply"),
        ("alerts", "Scan instant hot alerts"),
        ("hidden-jobs", "Discover hidden/off-market jobs"),
        ("early-access", "Scan early access roles and NVites"),
        ("search-all", "Search across Naukri, LinkedIn, and Hacker News Who's Hiring"),
        ("multi-search", "Search across Naukri, LinkedIn, and Hacker News Who's Hiring"),
        ("skill-insights", "In-demand skills intelligence"),
        ("hiring-trends", "Salary & GCC hiring report"),
        ("auth", "Authenticate session"),
        ("menu", "Launch interactive menu"),
    ]:
        subparsers.add_parser(cmd, help=hlp, parents=[common_parser])

    bump_parser = subparsers.add_parser("bump", help="Bump profile to Today (Once-a-day throttle)", parents=[common_parser])
    bump_parser.add_argument("--force", action="store_true", help="Force profile bump even if already touched today")

    daily_parser = subparsers.add_parser("daily", help="Run full daily autonomous cycle", parents=[common_parser])
    daily_parser.add_argument("--force", action="store_true", help="Force profile bump even if already touched today")

    prep_parser = subparsers.add_parser("interview-prep", help="Interview prep master bank and mock evaluator", parents=[common_parser])
    prep_parser.add_argument("--mock", action="store_true", help="Launch interactive AI mock interview evaluator with scoring")

    resume_parser = subparsers.add_parser("resume-maker", help="Generate ATS Resume PDF & Quality Scorecard (Supports --jd tailoring)", parents=[common_parser])
    resume_parser.add_argument("--jd", type=str, help="Path to target Job Description text file or raw JD string for tailoring")

    portal_parser = subparsers.add_parser("portal-apply", help="Auto-fill external career portal application (Greenhouse, Ashby, Lever, Workday)", parents=[common_parser])
    portal_parser.add_argument("--url", default=None, nargs="?", help="Job application URL")
    portal_parser.add_argument("--company", default="Company", help="Company name")
    portal_parser.add_argument("--role", default="Azure Data Engineer", help="Role title")
    portal_parser.add_argument("--jd", default="", help="Target job description or keywords")

    sched_parser = subparsers.add_parser("agy-schedule", help="Manage Linux AGY Autonomous Scheduler (systemd timer + agy CLI)", parents=[common_parser])
    sched_parser.add_argument("action", nargs="?", default="status", choices=["install", "run", "status", "logs"], help="Action to perform: install | run | status | logs")

    verify_parser = subparsers.add_parser("linkedin-verify", help="Validate LinkedIn session freshness & extract candidate identity", parents=[common_parser])
    verify_parser.add_argument("--headed", action="store_true", default=False, help="Run browser in visible GUI mode (default: headless)")

    apply_parser = subparsers.add_parser("linkedin-apply", help="Run autonomous LinkedIn Easy Apply engine across target vacancies", parents=[common_parser])
    apply_parser.add_argument("--headed", action="store_true", default=False, help="Run browser in visible GUI mode (default: headless)")
    apply_parser.add_argument("--min-score", type=float, default=70.0, help="Minimum job match score cutoff (default: 70.0)")
    apply_parser.add_argument("--keyword", type=str, default=None, help="Override search keyword (e.g. 'Azure Data Engineer')")
    apply_parser.add_argument("--location", type=str, default=None, help="Override search location (e.g. 'Bengaluru' or 'Remote')")

    args = parser.parse_args()

    if args.command == "pro":
        handle_pro(limit=args.limit, headless=args.headless, dry_run=args.dry_run, force=getattr(args, "force", False))
    elif args.command == "weekly-report":
        handle_weekly_report(headless=args.headless)
    elif args.command == "performance":
        handle_performance(headless=args.headless)
    elif args.command == "agy-schedule":
        handle_agy_schedule(action=args.action)
    elif args.command == "auto-apply":
        handle_auto_apply(headless=args.headless, limit=args.limit, dry_run=args.dry_run)
    elif args.command == "dry-run":
        handle_auto_apply(headless=args.headless, limit=args.limit, dry_run=True)
    elif args.command == "alerts":
        handle_alerts(headless=args.headless)
    elif args.command == "bump":
        handle_profile(headless=args.headless, force=getattr(args, "force", False))
    elif args.command == "hidden-jobs":
        handle_hidden_jobs(headless=args.headless)
    elif args.command == "early-access":
        handle_early_access(headless=args.headless)
    elif args.command in ("search-all", "multi-search"):
        handle_multi_search(dry_run=args.dry_run)
    elif args.command == "resume-maker":
        handle_resume_maker(jd=args.jd)
    elif args.command == "interview-prep":
        handle_interview_prep(mock=getattr(args, "mock", False))
    elif args.command == "skill-insights":
        handle_skill_insights(headless=args.headless)
    elif args.command == "hiring-trends":
        handle_hiring_trends(headless=args.headless)
    elif args.command == "daily":
        handle_daily_cycle(headless=args.headless, dry_run=args.dry_run, force=getattr(args, "force", False))
    elif args.command == "portal-apply":
        handle_portal_apply(
            url=args.url,
            company=args.company,
            role=args.role,
            jd=getattr(args, "jd", ""),
            headless=args.headless,
            dry_run=args.dry_run
        )
    elif args.command == "auth":
        handle_auth()
    elif args.command == "linkedin-verify":
        is_headless = not getattr(args, "headed", False)
        exit_code = handle_linkedin_verify(args, headless=is_headless)
        sys.exit(exit_code)
    elif args.command == "linkedin-apply":
        exit_code = handle_linkedin_apply(args)
        sys.exit(exit_code)
    else:
        interactive_loop()

if __name__ == "__main__":
    main()
