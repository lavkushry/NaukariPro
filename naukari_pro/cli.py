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
from naukari_pro.modules.linkedin_optimizer import (
    LINKEDIN_100K_BLUEPRINT,
    LinkedInProfileAuditor,
    export_100k_blueprint_markdown,
)
from naukari_pro.modules.recruiter_outreach import (
    RecruiterOutreachCRM,
    RecruiterTemplateGenerator,
    TOP_GCC_TARGETS,
)
from naukari_pro.modules.goal_5calls import Goal5CallsEngine


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
    print("  [D] Run Complete Daily Autonomous Cycle (Unified Naukri + LinkedIn 8-Stage Cycle)")
    print("  [G] AGY Autonomous Scheduler (Linux systemd & agy CLI schedule)")
    print("  [A] Authenticate Session (One-time Login & Cookie Persistence)")
    print("  [V] LinkedIn Session Diagnostic (Verify li_at cookie & Identity)")
    print("  [L] LinkedIn Easy Apply (Autonomous Multi-Step Bot & Screening Solver)")
    print("  [K] LinkedIn 100k+ Search SEO & Recruiter Optimizer (Blueprint & Audit)")
    print("  [O] 5-Calls/Day Recruiter Outreach & Goal Achievement Engine")
    print("  [0] Exit")
    print("========================================================================")

def handle_pro(limit=20, headless=False, dry_run=False, force=False):
    engine = ProAutoPilotEngine(limit=limit, headless=headless, dry_run=dry_run, force=force)
    return engine.run_full_pipeline()

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

def handle_daily_cycle(headless=False, dry_run=False, force=False, limit=20):
    print("\n[*] Launching Complete Autonomous Daily Cycle (Unified Naukri + LinkedIn 8-Stage Pipeline)...")
    engine = ProAutoPilotEngine(limit=limit, headless=headless, dry_run=dry_run, force=force)
    return engine.run_full_pipeline()

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
    When dry_run=True, executes 100% offline without launching browser or opening network sockets.
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

    # Parse comma-delimited keywords and locations into clean lists
    keywords_list = None
    if keyword:
        keywords_list = [k.strip() for k in str(keyword).split(",") if k.strip()]

    locations_list = None
    if location:
        locations_list = [l.strip() for l in str(location).split(",") if l.strip()]

    print("\n" + "=" * 76)
    print("   LINKEDIN AUTONOMOUS EASY APPLY ENGINE")
    print("=" * 76)
    mode_str = "DRY-RUN OFFLINE SIMULATION (NO SUBMISSIONS)" if dry_run else "LIVE AUTONOMOUS SUBMISSIONS"
    print(f"  • Execution Mode:        {mode_str}")
    print(f"  • Daily Cycle Limit:     {limit} applications")
    print(f"  • Minimum Match Gate:    {min_score}%")
    print(f"  • Browser Mode:          {'Offline (No Browser)' if dry_run else ('Headless' if headless else 'Visible GUI')}")
    if keywords_list:
        print(f"  • Keyword Filter:        {', '.join(keywords_list)}")
    if locations_list:
        print(f"  • Location Filter:       {', '.join(locations_list)}")
    print("=" * 76)

    from naukari_pro.modules.linkedin_apply import LinkedInApplyEngine
    apply_engine = LinkedInApplyEngine(min_score=min_score)

    try:
        if dry_run:
            # 100% Offline execution path
            stats = apply_engine.run_offline_dry_run(
                keywords=keywords_list,
                locations=locations_list,
                limit=limit,
                min_score=min_score
            )
        else:
            # Live execution path
            stats = asyncio.run(apply_engine.run_apply_cycle(
                keywords=keywords_list,
                locations=locations_list,
                limit=limit,
                dry_run=False,
                headless=headless
            ))
    except Exception as e:
        print(f"\n[!] Execution error during LinkedIn apply cycle: {e}")
        return 1

    # Formatted Vacancy Results Table
    jobs = stats.get("jobs", [])
    if jobs:
        print("\n" + "-" * 76)
        print(f"  {'#':<3} {'Job ID':<12} {'Company':<20} {'Match':<8} {'Status':<18} {'Steps'}")
        print("-" * 76)
        for idx, j in enumerate(jobs, 1):
            score_val = j.get('score', 0)
            score_str = f"{score_val:.1f}%" if isinstance(score_val, (int, float)) else str(score_val)
            print(f"  {idx:<3} {j.get('job_id', 'N/A'):<12} {j.get('company', 'Unknown')[:18]:<20} {score_str:<8} {j.get('status', 'N/A'):<18} {j.get('steps', 0)}")
        print("-" * 76)

    print("\n" + "=" * 76)
    print("   LINKEDIN APPLY CYCLE RESULTS SUMMARY")
    print("=" * 76)
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
    print("=" * 76 + "\n")
    return 0

def handle_linkedin_seo(args=None, output_path: str = None) -> int:
    """
    Audits candidate profile parameters and generates the 100k+ monthly recruiter
    search optimization blueprint (Headline, About, Top 3 Pinned skills, 50-skills taxonomy,
    and hidden Open-to-Work configuration).
    """
    target_out = output_path
    if args and hasattr(args, "output") and args.output:
        target_out = args.output

    auditor = LinkedInProfileAuditor()
    bp = LINKEDIN_100K_BLUEPRINT

    result = auditor.audit(
        headline=bp["headline"],
        about=bp["about"],
        skills=bp["top_50_skills"],
        current_title="DevOps Engineer / Azure Data Engineer"
    )

    md_file = export_100k_blueprint_markdown(target_out)

    print("\n" + "=" * 76)
    print("   LINKEDIN 100K+ RECRUITER SEARCH APPEARANCES & SEO OPTIMIZER")
    print("=" * 76)
    print(f"  • Candidate:             Lavkush Kumar (2.5 YOE | ₹20-25 LPA Target)")
    print(f"  • Target Specialization: Azure Data Engineer / Lakehouse Platform")
    print(f"  • Profile SEO Score:     {result['seo_score']}/100.0 [{result['grade']}]")
    print(f"  • Core Keywords Active:  {len(result['critical_keywords_covered'])}/{len(auditor.CRITICAL_RECRUITER_KEYWORDS)} matched")
    print(f"  • Skills Saturation:     {len(bp['top_50_skills'])}/50 skills defined (100% capacity)")
    print("=" * 76)

    print("\n📌 1. RECRUITER-OPTIMIZED HEADLINE (208 / 220 chars):")
    print("-" * 76)
    print(f"  {bp['headline']}")
    print("-" * 76)

    print("\n📌 2. TOP 3 PINNED SKILLS (Recruiter Boolean Priority 1):")
    print("-" * 76)
    for idx, sk in enumerate(bp['top_50_skills'][:3], 1):
        print(f"  {idx}. {sk}")
    print("-" * 76)

    print("\n📌 3. OPEN TO WORK CONFIGURATION (Recruiters Only):")
    print("-" * 76)
    otw = bp['open_to_work_settings']
    print(f"  • Target Titles:    {', '.join(otw['job_titles'])}")
    print(f"  • Target Hubs:      {', '.join(otw['locations_on_site'])} + Remote")
    print(f"  • Availability:     {otw['start_date']}")
    print(f"  • Visibility:       {otw['visibility']}")
    print("-" * 76)

    print("\n📌 4. STANDALONE BLUEPRINT EXPORT:")
    print("-" * 76)
    print(f"  ✓ Exported to: {md_file}")
    print(f"  ✓ Includes full 2,600-char 'About' section, 50-skills taxonomy, and experience bullets.")
    print("-" * 76 + "\n")
    return 0

def handle_goal_5calls(
    args=None,
    outreach=False,
    pacing=False,
    status=False,
    block=None,
    dry_run=False,
    company=None,
    recruiter=None,
    role="Azure Data Engineer",
    msg_type=None,
    update_status=None,
    lead_id=None,
    notes=None,
    send_outreach=False,
    limit=5,
    headed=False,
    profile_url=None,
    note=None
):
    """
    Handles 5-Calls/Day Goal Pacing, Recruiter Outreach Engine, and Daily 3-Block Execution.
    """
    if args and getattr(args, "interactive", False) is True:
        return handle_goal_5calls_interactive()

    if args:
        val_send = getattr(args, "send_outreach", False)
        if val_send is True or (isinstance(val_send, bool) and val_send):
            send_outreach = True
        raw_limit = getattr(args, "limit", None)
        if isinstance(raw_limit, int):
            limit = raw_limit
        elif raw_limit is not None and not isinstance(raw_limit, type(args)):
            try:
                limit = int(raw_limit)
            except (ValueError, TypeError):
                pass
        raw_headed = getattr(args, "headed", False)
        if raw_headed is True or (isinstance(raw_headed, bool) and raw_headed):
            headed = True
        raw_url = getattr(args, "profile_url", None)
        if isinstance(raw_url, str):
            profile_url = raw_url
        raw_note = getattr(args, "note", None)
        if isinstance(raw_note, str):
            note = raw_note

        val_outreach = getattr(args, "outreach", False)
        if val_outreach is True or (isinstance(val_outreach, bool) and val_outreach):
            outreach = True
        val_pacing = getattr(args, "pacing", False)
        if val_pacing is True or (isinstance(val_pacing, bool) and val_pacing):
            pacing = True
        val_status = getattr(args, "status", False)
        if val_status is True or (isinstance(val_status, bool) and val_status):
            status = True
        val_block = getattr(args, "block", None)
        if isinstance(val_block, int):
            block = val_block
        elif val_block is not None and not isinstance(val_block, type(args)):
            try:
                block = int(val_block)
            except (ValueError, TypeError):
                pass
        val_dry = getattr(args, "dry_run", False)
        if val_dry is True or (isinstance(val_dry, bool) and val_dry):
            dry_run = True
        val_comp = getattr(args, "company", None)
        if isinstance(val_comp, str):
            company = val_comp
        val_rec = getattr(args, "recruiter", None)
        if isinstance(val_rec, str):
            recruiter = val_rec
        val_role = getattr(args, "role", None)
        if isinstance(val_role, str):
            role = val_role
        val_type = getattr(args, "msg_type", None)
        if isinstance(val_type, str):
            msg_type = val_type
        val_up = getattr(args, "update_status", None)
        if isinstance(val_up, str):
            update_status = val_up
        val_lid = getattr(args, "lead_id", None)
        if isinstance(val_lid, str):
            lead_id = val_lid
        val_notes = getattr(args, "notes", None)
        if isinstance(val_notes, str):
            notes = val_notes

    # 0. Autonomous Recruiter Connection Bot (Playwright Stealth)
    if send_outreach:
        from naukari_pro.modules.linkedin_outreach import LinkedInOutreachSender
        sender = LinkedInOutreachSender(headless=not headed, max_daily_limit=min(limit, 8))

        print("\n" + "=" * 76)
        print("   🤖 AUTONOMOUS LINKEDIN RECRUITER CONNECTION BOT (PLAYWRIGHT STEALTH)")
        print("   Candidate: Lavkush Kumar (₹20–25 LPA | 15-Day Notice | Azure Data Engineer)")
        print("=" * 76)
        mode_desc = "[DRY-RUN SIMULATION] (Safe: Modal verified, no live invitations sent)" if dry_run else "[LIVE DISPATCH] (Sending live connection requests)"
        print(f"  • Mode:              {mode_desc}")
        print(f"  • Browser:           {'Headed (Visible GUI)' if headed else 'Headless (Stealth)'}")
        print(f"  • Daily Limit:       {min(limit, 8)} profiles max")
        print("-" * 76)

        if company or recruiter or profile_url:
            rec = recruiter or "Hiring Team"
            comp = company or "Target Company"
            print(f"[*] Navigating to {rec} at {comp} (URL: {profile_url or 'LinkedIn Search'})...")
            res = sender.run_outreach(
                recruiter_name=rec,
                company=comp,
                profile_url=profile_url,
                note=note,
                dry_run=dry_run,
                max_daily_limit=min(limit, 8)
            )
            print("-" * 76)
            print(f"  • Recruiter:         {res.get('recruiter_name')}")
            print(f"  • Company:           {res.get('company')}")
            print(f"  • Status:            {res.get('status')}")
            print(f"  • Invitation Sent:   {res.get('sent')}")
            if res.get("note"):
                print(f"  • Note ({res.get('note_length', len(res['note']))}/300 chars):")
                print(f"    \"{res.get('note')}\"")
            print(f"  • Diagnostic Detail: {res.get('detail')}")
            print("=" * 76 + "\n")
            return 0 if res.get("status") in ["SENT", "DRY_RUN_VERIFIED", "ALREADY_CONNECTED", "PENDING"] else 1
        else:
            print(f"[*] Executing Autonomous Outreach Batch (up to {min(limit, 8)} GCC Recruiters)...")
            batch_res = sender.run_batch(
                limit=min(limit, 8),
                dry_run=dry_run,
                headless=not headed,
                custom_note=note
            )
            print("\n" + "=" * 76)
            print("   RECRUITER OUTREACH BATCH EXECUTION RESULTS")
            print("=" * 76)
            print(f"  • Batch Status:      {batch_res.get('status')}")
            print(f"  • Processed:         {batch_res.get('total_processed', 0)}")
            print(f"  • Live Invites Sent: {batch_res.get('sent_count', 0)}")
            print(f"  • Dry-Run Verified:  {batch_res.get('dry_run_count', 0)}")
            print("-" * 76)
            results_list = batch_res.get("results", [])
            if results_list:
                print(f"  {'#':<3} {'Company':<22} {'Recruiter':<22} {'Status':<18} {'Length'}")
                print("-" * 76)
                for i, r in enumerate(results_list, 1):
                    c_name = str(r.get("company", ""))[:20]
                    r_name = str(r.get("recruiter_name", ""))[:20]
                    st = str(r.get("status", ""))[:16]
                    n_len = f"{r.get('note_length', 0)}/300" if r.get("note") else "N/A"
                    print(f"  {i:<3} {c_name:<22} {r_name:<22} {st:<18} {n_len}")
            print("=" * 76 + "\n")
            return 0

    engine = Goal5CallsEngine()

    # 1. Update lead status if requested
    if update_status:
        target_id = lead_id or recruiter or company
        if not target_id:
            print("[!] Error: Must specify --lead-id, --recruiter, or --company with --update-status.")
            return 1
        updated = engine.crm.update_status(target_id, update_status, notes=notes)
        if updated:
            print(f"\n[✓] Successfully updated lead '{updated.get('lead_id')}' ({updated.get('company')}) to {update_status}.")
            print(f"    Notes: {updated.get('notes')}")
        else:
            print(f"\n[!] Lead '{target_id}' not found in outreach CRM.")
            return 1
        return 0

    # 2. Daily Block Execution
    if block is not None:
        print(f"\n[*] Executing Daily Block {block} (Dry-Run: {dry_run})...")
        res = engine.run_block(block_number=int(block), dry_run=dry_run)
        print("\n" + "=" * 76)
        print(f"   5-CALLS/DAY DAILY BLOCK {block} EXECUTION SUMMARY")
        print("=" * 76)
        print(f"  • Timestamp: {res.get('timestamp')}")
        print(f"  • Status:    {res.get('status')}")
        print("  • Actions Executed:")
        for act in res.get("actions_executed", []):
            print(f"    - {act.get('action')}: {act.get('details', '')}")
            if "count" in act:
                print(f"      Count: {act['count']}")
        print("=" * 76 + "\n")
        return 0

    # 3. Outreach Pitch Generation
    if outreach:
        gen = engine.generator
        if company:
            rec = recruiter or "Hiring Team"
            t_type = msg_type or "inmail"
            template_res = gen.generate_template(t_type, rec, company, role=role)
            conn_note = gen.generate_connection_note(rec, company)

            print("\n" + "=" * 76)
            print(f"   RECRUITER OUTREACH TEMPLATES: {company.upper()}")
            print("=" * 76)
            print(f"  • Recruiter / Lead: {rec}")
            print(f"  • Role Target:      {role}")
            print(f"  • Template Type:    {t_type}")
            print("-" * 76)
            print(f"📌 1. LINKEDIN CONNECTION NOTE (Length: {len(conn_note)}/300 chars):")
            print(f"   {conn_note}")
            print("-" * 76)
            print(f"📌 2. {template_res.get('subject', 'MESSAGE')}:")
            print(template_res.get("body", ""))
            print("-" * 76)

            if not dry_run:
                entry = engine.crm.log_outreach(
                    recruiter_name=rec,
                    company=company,
                    target_role=role,
                    platform="LinkedIn",
                    message_type=t_type,
                    status="CONTACTED",
                    notes=notes or "Generated via naukariPro goal-5calls CLI",
                    message_content=template_res.get("body", "")
                )
                print(f"[✓] Logged outreach lead: {entry.get('lead_id')} to outreach_tracker.json & Excel.")
            else:
                print("[*] Dry-run mode: CRM entry not persisted.")
            print("=" * 76 + "\n")
            return 0
        else:
            # Batch generate for top 10 GCCs
            print("\n[*] Batch-generating recruiter pitches across top 10 GCC target companies...")
            pitches = engine.crm.batch_generate_gcc_outreach()
            print("\n" + "=" * 76)
            print(f"   TOP 10 GCC RECRUITER OUTREACH PITCHES GENERATED")
            print("=" * 76)
            for idx, p in enumerate(pitches, 1):
                lead = p["lead"]
                print(f"  {idx:2d}. {lead.get('company'):<22} | {lead.get('recruiter_name'):<32} | {lead.get('message_type')}")
                print(f"      Connection Note ({len(p['connection_note'])} chars): {p['connection_note']}")
            print("-" * 76)
            print(f"[✓] Synchronized {len(pitches)} leads into outreach_tracker.json & Recruiter_Outreach_Log.")
            print("=" * 76 + "\n")
            return 0

    # 4. Status / CRM Summary
    if status:
        leads = engine.crm.list_active_leads()
        summary = engine.crm.get_summary()
        print("\n" + "=" * 76)
        print("   RECRUITER OUTREACH CRM & ACTIVE PIPELINE STATUS")
        print("=" * 76)
        print(f"  • Total Leads Logged:        {summary.get('total_leads', 0)}")
        print(f"  • Outreaches Today:          {summary.get('today_outreaches', 0)}")
        print(f"  • Recruiter Calls Booked:    {summary.get('today_calls_scheduled', 0)}")
        print("  • Leads by Status:")
        for st, count in summary.get("by_status", {}).items():
            print(f"    - {st:<16}: {count}")
        print("-" * 76)
        if leads:
            print(f"  {'Lead ID':<18} {'Date':<17} {'Company':<20} {'Status':<16} {'Recruiter'}")
            print("-" * 76)
            for l in leads[-10:]:
                print(f"  {l.get('lead_id', 'N/A'):<18} {l.get('date', '')[:16]:<17} {l.get('company', '')[:18]:<20} {l.get('status', ''):<16} {l.get('recruiter_name', '')[:20]}")
            print("-" * 76)
        print("=" * 76 + "\n")
        return 0

    # 5. Default / Pacing Dashboard
    dashboard = engine.format_dashboard()
    print("\n" + dashboard + "\n")
    return 0

def handle_goal_5calls_interactive():
    """
    Interactive terminal controller for 5-Calls/Day Goal Pacing, Outreach Generator & CRM.
    """
    engine = Goal5CallsEngine()
    while True:
        print("\n" + "=" * 76)
        print("   🎯 5-CALLS/DAY RECRUITER OUTREACH & GOAL PACING CONTROL CENTER")
        print("   Candidate: Lavkush Kumar (₹20–25 LPA | 15-Day Notice | Azure Data Engineer)")
        print("=" * 76)
        print("  [1] View 5-Calls/Day Funnel Pacing & Diagnostic Report")
        print("  [2] Generate Recruiter Outreach Pitch (Custom or Top GCCs)")
        print("  [3] Execute Daily High-Impact Block (Block 1: Morning, 2: Afternoon, 3: Evening)")
        print("  [4] Update Recruiter Lead Status (CONTACTED -> CONNECTED -> CALL_SCHEDULED)")
        print("  [5] View Recruiter Outreach CRM Active Pipeline & Summary")
        print("  [B] Execute Autonomous Recruiter Connection Bot (Playwright Stealth)")
        print("  [0] Return to Main Menu")
        print("=" * 76)
        choice = input("Select an option [0-5, B]: ").strip()
        if choice == "1":
            print("\n" + engine.format_dashboard() + "\n")
        elif choice == "2":
            comp = input("\nEnter Company Name (leave blank for Top 10 GCC batch): ").strip()
            if comp:
                rec = input("Enter Recruiter Name (or leave blank for Hiring Team): ").strip() or "Hiring Team"
                role = input("Enter Target Role [default: Azure Data Engineer]: ").strip() or "Azure Data Engineer"
                print("\nMessage Types:")
                print("  [1] LinkedIn Connection Note (<= 300 chars)")
                print("  [2] Direct InMail / First Message")
                print("  [3] Tech Lead / Hiring Manager Pitch")
                print("  [4] 48-Hour Urgent Follow-Up")
                print("  [5] External Application Follow-Up")
                t_choice = input("Select message type [1-5, default 2]: ").strip() or "2"
                t_map = {"1": "note", "2": "inmail", "3": "tech-lead", "4": "followup", "5": "app-followup"}
                t_type = t_map.get(t_choice, "inmail")
                dry_in = input("Dry-run mode (do not log to CRM)? [Y/n]: ").strip().lower()
                is_dry = dry_in != "n"
                handle_goal_5calls(outreach=True, company=comp, recruiter=rec, role=role, msg_type=t_type, dry_run=is_dry)
            else:
                handle_goal_5calls(outreach=True)
        elif choice == "3":
            print("\nExecution Blocks:")
            print("  [1] Block 1 (09:00 - 11:00): Morning Resdex bump + 25 batch applications")
            print("  [2] Block 2 (14:00 - 16:00): 10 Top GCC InMail & Tech Lead pitches")
            print("  [3] Block 3 (18:00 - 20:00): Evening Resdex bump + 5 follow-ups + funnel audit")
            blk_in = input("Select block to execute [1-3]: ").strip()
            if blk_in in ["1", "2", "3"]:
                dry_in = input("Execute in dry-run mode? [Y/n]: ").strip().lower()
                is_dry = dry_in != "n"
                handle_goal_5calls(block=int(blk_in), dry_run=is_dry)
        elif choice == "4":
            ident = input("\nEnter Lead ID, Company, or Recruiter Name: ").strip()
            if ident:
                print("\nAvailable Statuses:")
                print("  [1] CONTACTED")
                print("  [2] CONNECTED")
                print("  [3] PITCH_SENT")
                print("  [4] CALL_SCHEDULED")
                print("  [5] REJECTED")
                st_in = input("Select new status [1-5]: ").strip()
                st_map = {"1": "CONTACTED", "2": "CONNECTED", "3": "PITCH_SENT", "4": "CALL_SCHEDULED", "5": "REJECTED"}
                st = st_map.get(st_in)
                if st:
                    notes = input("Enter notes (optional): ").strip()
                    handle_goal_5calls(update_status=st, lead_id=ident, notes=notes or None)
        elif choice == "5":
            handle_goal_5calls(status=True)
        elif choice.upper() == "B":
            print("\nAutonomous Recruiter Connection Bot Modes:")
            print("  [1] Batch Run: Top GCC Recruiters (Microsoft, Walmart, JPMorgan, etc.)")
            print("  [2] Single Recruiter Target (Custom Company & Recruiter Name / Profile URL)")
            bot_mode = input("Select outreach mode [1-2, default 1]: ").strip() or "1"

            comp = None
            rec = None
            prof_url = None
            if bot_mode == "2":
                comp = input("Enter Company Name: ").strip() or "Target Company"
                rec = input("Enter Recruiter Name: ").strip() or "Hiring Team"
                prof_url = input("Enter Direct Profile URL (optional, leave blank to search): ").strip() or None

            limit_in = input("Enter connection limit [1-8, default 5]: ").strip()
            limit_val = int(limit_in) if limit_in.isdigit() and 1 <= int(limit_in) <= 8 else 5

            dry_in = input("Run in Dry-Run simulation mode? [Y/n]: ").strip().lower()
            is_dry = dry_in != "n"

            headed_in = input("Run with visible browser window (headed)? [y/N]: ").strip().lower()
            is_headed = headed_in == "y"

            handle_goal_5calls(
                send_outreach=True,
                company=comp,
                recruiter=rec,
                profile_url=prof_url,
                limit=limit_val,
                dry_run=is_dry,
                headed=is_headed
            )
        elif choice == "0":
            break
        else:
            print("\n[!] Invalid choice. Please select from [0-5, B].")
        input("\nPress Enter to continue...")
    return 0

def interactive_loop():
    while True:
        print_menu()
        choice = input("Select an option [0-9, P, W, E, M, S, C, D, G, A, V, L, K, O]: ").strip().upper()
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
        elif choice == "K":
            handle_linkedin_seo()
        elif choice == "O":
            handle_goal_5calls_interactive()
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
    apply_parser.add_argument("--keyword", "--keywords", dest="keyword", type=str, default=None, help="Override search keyword(s), comma-separated (e.g. 'Azure Data Engineer,Databricks')")
    apply_parser.add_argument("--location", "--locations", dest="location", type=str, default=None, help="Override search location(s), comma-separated (e.g. 'Bengaluru,Hyderabad')")
    apply_parser.set_defaults(limit=25)

    seo_parser = subparsers.add_parser("linkedin-seo", help="Audit and export LinkedIn 100k+ Recruiter Search SEO blueprint", parents=[common_parser])
    seo_parser.add_argument("--output", type=str, default=None, help="Custom export path for the markdown blueprint")

    optimize_parser = subparsers.add_parser("linkedin-optimize", help="Alias for linkedin-seo", parents=[common_parser])
    optimize_parser.add_argument("--output", type=str, default=None, help="Custom export path for the markdown blueprint")

    goal_parser = subparsers.add_parser("goal-5calls", help="5-Calls/Day Recruiter Outreach & Goal Achievement Engine", parents=[common_parser])
    goal_parser.add_argument("--interactive", action="store_true", help="Launch interactive 5-calls/day console")
    goal_parser.add_argument("--send-outreach", action="store_true", help="Execute Autonomous LinkedIn Recruiter Connection Bot (Playwright Stealth)")
    goal_parser.add_argument("--headed", action="store_true", default=False, help="Run browser in visible GUI mode (default: headless)")
    goal_parser.add_argument("--profile-url", type=str, default=None, help="Direct LinkedIn profile URL to send connection request to")
    goal_parser.add_argument("--note", type=str, default=None, help="Custom connection note (<= 300 characters)")
    goal_parser.add_argument("--outreach", action="store_true", help="Generate and log recruiter outreach pitch(es)")
    goal_parser.add_argument("--pacing", action="store_true", help="Display 5-calls/day funnel pacing & diagnostic report")
    goal_parser.add_argument("--status", action="store_true", help="Show outreach CRM active leads and funnel status")
    goal_parser.add_argument("--block", type=int, choices=[1, 2, 3], help="Execute daily high-impact block: 1 (Morning), 2 (Afternoon), 3 (Evening)")
    goal_parser.add_argument("--company", type=str, default=None, help="Target company name for outreach pitch")
    goal_parser.add_argument("--recruiter", type=str, default=None, help="Recruiter or Engineering Lead name")
    goal_parser.add_argument("--role", type=str, default="Azure Data Engineer", help="Target role title")
    goal_parser.add_argument("--type", type=str, default=None, dest="msg_type", choices=["note", "inmail", "tech-lead", "followup", "app-followup"], help="Message template type to generate")
    goal_parser.add_argument("--update-status", type=str, default=None, choices=["CONTACTED", "CONNECTED", "PITCH_SENT", "CALL_SCHEDULED", "REJECTED"], help="Update lead status in CRM")
    goal_parser.add_argument("--lead-id", type=str, default=None, help="Lead ID or recruiter identifier to update")
    goal_parser.add_argument("--notes", type=str, default=None, help="Optional notes for status update or lead logging")

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
        handle_daily_cycle(headless=args.headless, dry_run=args.dry_run, force=getattr(args, "force", False), limit=getattr(args, "limit", 20))
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
    elif args.command in ("linkedin-seo", "linkedin-optimize"):
        exit_code = handle_linkedin_seo(args)
        sys.exit(exit_code)
    elif args.command in ("goal-5calls", "goal", "outreach"):
        exit_code = handle_goal_5calls(args=args)
        if exit_code:
            sys.exit(exit_code)
    else:
        interactive_loop()

if __name__ == "__main__":
    main()
