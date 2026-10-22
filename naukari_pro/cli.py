"""
naukariPro CLI & Master Orchestrator
Integrates all 8 core modules into a unified terminal tool and automated pipeline.
"""

import sys
import argparse
from playwright.sync_api import sync_playwright

from naukari_pro.session import get_stealth_context, ensure_authenticated
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
    print("  [1] Auto-Apply on Naukri (1-Click & Questionnaire Applications)")
    print("  [2] Instant Job Alerts (Scan Fresh Openings & Send Desktop Alerts)")
    print("  [3] AI-Enhanced Profile (Daily Bumper & Resdex 100% Audit)")
    print("  [4] Hidden Job Opportunities (Recommended Jobs & GCC Openings)")
    print("  [5] AI Resume Maker (Compile 1-Page ATS PDF)")
    print("  [6] AI Interview Prep Tools (Master Q&A Bank for ₹25 LPA)")
    print("  [7] In-Demand Skill Insights (Real-time Skill Demand & Trends)")
    print("  [8] Industry Hiring Trends (Salary Benchmarks & Top GCCs)")
    print("  [9] Early Access & NVites (Pre-Market Roles & Recruiter Shortlists)")
    print("  [C] Career Portal Auto-Filler (Greenhouse / Ashby / Lever / Workday / Portals)")
    print("  [D] Run Complete Daily Autonomous Cycle (Bump + Scan + Apply + Log)")
    print("  [A] Authenticate Session (One-time Chrome Login Setup)")
    print("  [0] Exit")
    print("========================================================================")

def handle_auto_apply(headless=False, limit=20):
    print("\n[*] Starting Auto-Apply on Naukri...")
    engine = AutoApplyEngine()
    engine.run(headless=headless, limit=limit)

def handle_alerts(headless=False):
    print("\n[*] Scanning for Instant Job Alerts...")
    engine = InstantAlertsEngine()
    with sync_playwright() as p:
        context = get_stealth_context(p, headless=headless)
        page = context.pages[0] if context.pages else context.new_page()
        if ensure_authenticated(page):
            alerts = engine.scan_for_alerts(page)
            print(f"\n[+] Identified {len(alerts)} High-Priority Vacancies:")
            for a in alerts:
                print(f" -> [{a['match_score']}% Match] {a['title']} | {a['company']} | {a['location']} | {a['salary']}")
                print(f"    URL: {a['url']}")
        context.close()

def handle_profile(headless=False):
    print("\n[*] Running AI-Enhanced Profile Module...")
    engine = ProfileEnhancerEngine()
    audit = engine.audit_profile_strength()
    print(f"\n[+] Profile Resdex Strength Score: {audit['score']}/100 ({audit['tier']})")
    for name, desc, pts in audit['checklist']:
        print(f"  [✓] {name:<26} (+{pts} pts) : {desc}")

    with sync_playwright() as p:
        context = get_stealth_context(p, headless=headless)
        page = context.pages[0] if context.pages else context.new_page()
        if ensure_authenticated(page):
            engine.bump_profile(page)
        context.close()

def handle_hidden_jobs(headless=False):
    print("\n[*] Discovering Hidden & Stealth Opportunities...")
    engine = HiddenJobsEngine()
    with sync_playwright() as p:
        context = get_stealth_context(p, headless=headless)
        page = context.pages[0] if context.pages else context.new_page()
        if ensure_authenticated(page):
            jobs = engine.discover_hidden_opportunities(page)
            print(f"\n[+] Discovered {len(jobs)} Off-Market Openings:")
            for j in jobs:
                gcc_tag = " [TOP GCC]" if j.get("is_gcc") else ""
                print(f" -> {j['title']} | {j['company']}{gcc_tag} | {j['location']} ({j['source']})")
                print(f"    URL: {j['url']}")
        context.close()

def handle_resume_maker():
    print("\n[*] Compiling AI ATS Resume...")
    maker = AIResumeMaker()
    out = maker.build_ats_resume_pdf()
    print(f"\n[✓] ATS Resume generated successfully: {out}")

def handle_interview_prep():
    engine = InterviewPrepEngine()
    engine.display_full_prep_guide()

def handle_skill_insights():
    engine = SkillInsightsEngine()
    engine.display_insights()

def handle_hiring_trends():
    engine = HiringTrendsEngine()
    engine.display_market_report()

def handle_portal_apply(url=None, company="Company", role="Azure Data Engineer", headless=False):
    filler = CareerPortalFiller()
    if not url:
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

    import sys
    if sys.platform == "darwin":
        filler.fill_in_chrome(url, company=company, role=role)
    else:
        with sync_playwright() as p:
            context = get_stealth_context(p, headless=headless)
            page = context.pages[0] if context.pages else context.new_page()
            filler.fill_in_playwright(page, url, company=company, role=role)
            context.close()

def handle_daily_cycle(headless=False):
    print("\n[*] Launching Complete Autonomous Daily Cycle...")
    # 1. Profile bump
    handle_profile(headless=headless)
    # 2. Auto-apply
    handle_auto_apply(headless=headless, limit=20)
    # 3. Alerts
    handle_alerts(headless=headless)

def handle_auth():
    print("\n[*] Launching Chrome window with your credentials pre-filled...")
    with sync_playwright() as p:
        context = get_stealth_context(p, headless=False)
        page = context.pages[0] if context.pages else context.new_page()

        try:
            page.goto("https://www.naukri.com/nlogin/login", wait_until="domcontentloaded", timeout=30000)
            import time
            time.sleep(2)

            # Auto-fill credentials if login form is displayed
            if "nlogin" in page.url or page.locator("#usernameField").count() > 0:
                user_field = page.locator("#usernameField").first
                if user_field.is_visible():
                    user_field.fill("lavkushry@gmail.com")
                    time.sleep(0.3)
                pass_field = page.locator("#passwordField").first
                if pass_field.is_visible():
                    pass_field.fill("Lodu@735671")
                    time.sleep(0.3)
                login_btn = page.locator("button[type='submit']").first
                if login_btn.is_visible():
                    login_btn.click()
                    time.sleep(2)

            print("\n" + "=" * 65)
            print("  🔑 CREDENTIALS SUBMITTED!")
            print("  If a quick visual verification (Captcha/OTP) appears in the")
            print("  opened Chrome window on your screen, please complete it.")
            print("  Waiting up to 3 minutes for login confirmation...")
            print("=" * 65 + "\n")

            page.wait_for_url("**/mnjuser/**", timeout=180000)
            print("\n[✓] SUCCESS: Authenticated session verified and permanently saved!")
        except Exception as e:
            print(f"\n[!] Notice during login: {e}")

        context.close()

def handle_early_access(headless=False):
    print("\n[*] Scanning Early Access Roles and Recruiter NVites...")
    engine = EarlyAccessEngine()
    with sync_playwright() as p:
        context = get_stealth_context(p, headless=headless)
        page = context.pages[0] if context.pages else context.new_page()
        if ensure_authenticated(page):
            res = engine.scan_early_access(page)
            print(f"\n[+] Profile Status: {res['profile_status']}")
            print(f"[+] Early Access Roles Detected: {res['early_roles_detected']}")
            if res['nvites']:
                print(f"[+] Direct Recruiter Shortlists / NVites:")
                for n in res['nvites']:
                    print(f"  • {n}")
        context.close()

def interactive_loop():
    while True:
        print_menu()
        choice = input("Select an option [0-9, D, A]: ").strip().upper()
        if choice == "1":
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
        elif choice == "7":
            handle_skill_insights()
        elif choice == "8":
            handle_hiring_trends()
        elif choice == "9":
            handle_early_access()
        elif choice.upper() == "C":
            handle_portal_apply()
        elif choice.upper() == "D":
            handle_daily_cycle()
        elif choice.upper() == "A":
            handle_auth()
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

    parser = argparse.ArgumentParser(description="naukariPro Career Suite", parents=[common_parser])
    subparsers = parser.add_subparsers(dest="command")

    for cmd, hlp in [
        ("auto-apply", "Auto-Apply to target vacancies"),
        ("alerts", "Scan instant hot alerts"),
        ("bump", "Bump profile to Today"),
        ("hidden-jobs", "Discover hidden/stealth jobs"),
        ("early-access", "Scan early access roles and NVites"),
        ("resume-maker", "Generate ATS Resume PDF"),
        ("interview-prep", "Interview prep master bank"),
        ("skill-insights", "In-demand skills intelligence"),
        ("hiring-trends", "Salary & GCC hiring report"),
        ("daily", "Run full daily autonomous cycle"),
        ("auth", "Authenticate session"),
        ("menu", "Launch interactive menu"),
    ]:
        subparsers.add_parser(cmd, help=hlp, parents=[common_parser])

    portal_parser = subparsers.add_parser("portal-apply", help="Auto-fill external career portal application (Greenhouse, Ashby, Lever, Workday)", parents=[common_parser])
    portal_parser.add_argument("--url", required=True, help="Job application URL")
    portal_parser.add_argument("--company", default="Company", help="Company name")
    portal_parser.add_argument("--role", default="Azure Data Engineer", help="Role title")

    args = parser.parse_args()

    if args.command == "auto-apply":
        handle_auto_apply(headless=args.headless, limit=args.limit)
    elif args.command == "alerts":
        handle_alerts(headless=args.headless)
    elif args.command == "bump":
        handle_profile(headless=args.headless)
    elif args.command == "hidden-jobs":
        handle_hidden_jobs(headless=args.headless)
    elif args.command == "early-access":
        handle_early_access(headless=args.headless)
    elif args.command == "resume-maker":
        handle_resume_maker()
    elif args.command == "interview-prep":
        handle_interview_prep()
    elif args.command == "skill-insights":
        handle_skill_insights()
    elif args.command == "hiring-trends":
        handle_hiring_trends()
    elif args.command == "daily":
        handle_daily_cycle(headless=args.headless)
    elif args.command == "portal-apply":
        handle_portal_apply(url=args.url, company=args.company, role=args.role, headless=args.headless)
    elif args.command == "auth":
        handle_auth()
    else:
        interactive_loop()

if __name__ == "__main__":
    main()
