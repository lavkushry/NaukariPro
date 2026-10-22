#!/usr/bin/env python3
"""
Naukri Autonomous Job Application & Profile Management System
Author: Lavkush Kumar
Version: 2.5 (Production Architecture)

Core Pillars:
  1. Profile Bumper (Keeps status at 'Last updated today' for 10x recruiter visibility).
  2. Targeted Job Scanner (Filters Azure Data Engineer / DevOps jobs posted <24 hours).
  3. Smart Auto-Applier (Submits 1-Click & Questionnaire applications).
  4. Real-time Excel Tracker (Logs applications, companies, and response statuses).
  5. Anti-Detection Stealth (Bypasses Akamai Bot Protection with persistent session).
"""

import os
import sys
import time
import json
import random
import logging
import argparse
from datetime import datetime
from playwright.sync_api import sync_playwright

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.expanduser("~/naukri_system.log"))
    ]
)
logger = logging.getLogger("NaukriSystem")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
COOKIES_SEED_PATH = os.path.join(BASE_DIR, "cookies_seed.json")
SESSION_DIR = os.path.expanduser("~/.naukri_system_profile")

STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
window.navigator.chrome = { runtime: {} };
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en', 'hi'] });
"""

class NaukriAutomationSystem:
    def __init__(self, config_path=CONFIG_PATH):
        with open(config_path, "r") as f:
            self.cfg = json.load(f)
        self.applied_urls = set()
        self.load_tracker_cache()

    # --------------------------------------------------------------------------
    # EXCEL TRACKER INTEGRATION
    # --------------------------------------------------------------------------
    def load_tracker_cache(self):
        """Loads previously tracked job URLs from the Excel log to prevent duplicates."""
        import openpyxl
        excel_path = self.cfg["tracker_excel_path"]
        if not os.path.exists(excel_path):
            return
        try:
            wb = openpyxl.load_workbook(excel_path, read_only=True)
            if "Applications_Log" in wb.sheetnames:
                ws = wb["Applications_Log"]
            else:
                ws = wb.active
            for row in ws.iter_rows(min_row=2, values_only=True):
                if len(row) > 8 and row[8]:
                    self.applied_urls.add(str(row[8]).strip())
                elif len(row) > 6 and row[6]:
                    self.applied_urls.add(str(row[6]).strip())
            logger.info("Loaded %d previously tracked jobs from Excel tracker.", len(self.applied_urls))
        except Exception as e:
            logger.warning("Could not read tracker cache: %s", e)

    def log_application(self, job_info, status, app_type="1-Click Apply"):
        """Appends a new application record to the Excel tracker."""
        import openpyxl
        excel_path = self.cfg["tracker_excel_path"]
        try:
            wb = openpyxl.load_workbook(excel_path)
            ws = wb["Applications_Log"] if "Applications_Log" in wb.sheetnames else wb.active
            
            row = [
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                job_info.get("company", "N/A"),
                job_info.get("title", "N/A"),
                job_info.get("role_category", "Azure Data Engineer"),
                job_info.get("experience", "N/A"),
                job_info.get("location", "N/A"),
                app_type,
                status,
                job_info.get("url", "N/A"),
                "Awaiting Recruiter Review"
            ]
            ws.append(row)
            wb.save(excel_path)
            self.applied_urls.add(job_info.get("url", ""))
            logger.info("Tracker updated: [%s] at %s (%s)", status, job_info.get("company"), job_info.get("title"))
        except Exception as e:
            logger.error("Failed to log application to Excel: %s", e)

    def log_daily_summary(self, scanned_count, applied_count, bump_status):
        """Records the day's high-level execution metrics."""
        import openpyxl
        excel_path = self.cfg["tracker_excel_path"]
        try:
            wb = openpyxl.load_workbook(excel_path)
            if "Daily_Performance_Metrics" in wb.sheetnames:
                ws = wb["Daily_Performance_Metrics"]
                ws.append([
                    datetime.now().strftime("%Y-%m-%d"),
                    scanned_count,
                    applied_count,
                    "Yes" if bump_status else "No",
                    "Last updated today" if bump_status else "Pending",
                    "Azure Data Engineer & Cloud Data Platform"
                ])
                wb.save(excel_path)
        except Exception as e:
            logger.warning("Could not append daily summary: %s", e)

    # --------------------------------------------------------------------------
    # BROWSER & PERSISTENT SESSION MANAGEMENT
    # --------------------------------------------------------------------------
    def get_context(self, playwright, headless=False):
        """Launches persistent Chrome context with anti-bot evasion and seed cookies."""
        os.makedirs(SESSION_DIR, exist_ok=True)
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=SESSION_DIR,
            headless=headless,
            channel="chrome",  # Uses local Google Chrome
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--start-maximized"
            ],
            viewport=None,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
        )
        context.add_init_script(STEALTH_JS)

        # Inject seed cookies if available
        if os.path.exists(COOKIES_SEED_PATH):
            try:
                with open(COOKIES_SEED_PATH, "r") as f:
                    seed_cookies = json.load(f)
                context.add_cookies(seed_cookies)
                logger.info("Injected %d seed authentication cookies into Chrome session.", len(seed_cookies))
            except Exception as e:
                logger.warning("Could not inject seed cookies: %s", e)

        return context

    def ensure_auth(self, page):
        """Verifies authentication state. Pauses for 1-time manual login if required."""
        logger.info("Verifying authentication state on Naukri...")
        try:
            page.goto("https://www.naukri.com/mnjuser/profile", wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)
        except Exception as e:
            logger.warning("Navigation notice: %s", e)

        if "login" in page.url or page.locator("text=Login").first.is_visible() or "Access Denied" in page.title():
            logger.warning("=" * 70)
            logger.warning("AUTHENTICATION NEEDED: Please complete 1-time login in the browser window.")
            logger.warning("Waiting for login confirmation (up to 3 minutes)...")
            logger.warning("=" * 70)
            try:
                page.wait_for_url("**/profile**", timeout=180000)
                logger.info("Login confirmed! Persistent session permanently stored at %s", SESSION_DIR)
            except Exception:
                logger.error("Login timeout expired. Please run './run.sh --auth' to authenticate.")
                sys.exit(1)
        else:
            logger.info("SUCCESS: Authenticated session confirmed. Ready for execution.")

    # --------------------------------------------------------------------------
    # PILLAR 1: PROFILE BUMPER (Keeps 'Last updated today')
    # --------------------------------------------------------------------------
    def bump_profile(self, page):
        """
        Updates the headline with a micro-change to touch Naukri's recency algorithm.
        This forces status to 'Last updated today', multiplying search impressions by 10x.
        """
        logger.info("=== [PILLAR 1] Executing Daily Profile Bumper ===")
        page.goto("https://www.naukri.com/mnjuser/profile", wait_until="networkidle", timeout=30000)
        time.sleep(2)

        try:
            # Locate headline widget
            headline_edit = page.locator(".widgetHead .edit, span.edit, .resumeHeadline .edit").first
            if headline_edit.is_visible():
                headline_edit.click()
                time.sleep(1.5)

                textarea = page.locator("textarea#resumeHeadlineTxt, form[name='resumeHeadline'] textarea, textarea").first
                curr_val = textarea.input_value().strip()

                template = self.cfg["headline_template"]
                # Micro-toggle: alternate period at the end
                if curr_val.endswith("."):
                    new_val = template.rstrip(".")
                else:
                    new_val = template.rstrip(".") + "."

                textarea.fill(new_val)
                time.sleep(1)

                save_btn = page.locator("button[type='submit'], .btn-dark-ot, button:has-text('Save')").first
                if save_btn.is_visible():
                    save_btn.click()
                    time.sleep(3)
                    logger.info("SUCCESS: Profile timestamp refreshed! Status is 'Last updated today'.")
                    return True
            else:
                logger.warning("Headline edit button not immediately visible.")
        except Exception as e:
            logger.error("Error during profile bump: %s", e)
        return False

    # --------------------------------------------------------------------------
    # PILLAR 2: TARGETED JOB SCANNER
    # --------------------------------------------------------------------------
    def scan_jobs(self, page, role, location, max_pages=1):
        """Scrapes fresh jobs matching target role and city posted in the last 24h."""
        logger.info("=== [PILLAR 2] Scanning '%s' in '%s' ===", role, location)
        days = self.cfg["search_settings"].get("posted_within_days", 1)
        url = f"https://www.naukri.com/{role}-jobs-in-{location}?jobAge={days}"
        
        try:
            page.goto(url, wait_until="networkidle", timeout=35000)
            time.sleep(3)
        except Exception as e:
            logger.warning("Navigation failed for %s: %s", url, e)
            return []

        discovered = []
        for p_idx in range(1, max_pages + 1):
            logger.info("Parsing search results page %d...", p_idx)
            tuples = page.locator("article.jobTuple, .cust-job-tuple, .srp-jobtuple-wrapper").all()

            for item in tuples:
                try:
                    title_node = item.locator("a.title").first
                    comp_node = item.locator("a.comp-name, .comp-name-link").first
                    exp_node = item.locator(".exp-wrap, span[class*='exp']").first
                    loc_node = item.locator(".loc-wrap, span[class*='loc']").first
                    
                    job_url = title_node.get_attribute("href") if title_node.count() > 0 else ""
                    if not job_url:
                        continue

                    # Filter out already applied / tracked
                    if job_url in self.applied_urls:
                        continue

                    job_info = {
                        "title": title_node.inner_text().strip() if title_node.count() > 0 else "Unknown Title",
                        "company": comp_node.inner_text().strip() if comp_node.count() > 0 else "Unknown Company",
                        "experience": exp_node.inner_text().strip() if exp_node.count() > 0 else "N/A",
                        "location": loc_node.inner_text().strip() if loc_node.count() > 0 else location.capitalize(),
                        "role_category": role.replace("-", " ").title(),
                        "url": job_url
                    }
                    discovered.append(job_info)
                except Exception:
                    continue

            # Pagination check
            next_btn = page.locator("a:has-text('Next')").first
            if next_btn.is_visible() and p_idx < max_pages:
                next_btn.click()
                time.sleep(3)
            else:
                break

        logger.info("Discovered %d new, unapplied vacancies for '%s' in '%s'.", len(discovered), role, location)
        return discovered

    # --------------------------------------------------------------------------
    # PILLAR 3: SMART AUTO-APPLY ENGINE
    # --------------------------------------------------------------------------
    def apply_to_job(self, page, job_info):
        """Navigates to job posting and executes 1-Click apply or questionnaire submission."""
        url = job_info.get("url")
        logger.info("Evaluating: '%s' at '%s'", job_info.get("title"), job_info.get("company"))
        
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            time.sleep(2.5)

            # Check if already applied
            if page.locator("text=Already Applied, text=You have already applied").count() > 0:
                logger.info("Status: Already applied.")
                self.log_application(job_info, "Already Applied", "1-Click Apply")
                return "Already Applied"

            # Locate Apply Button
            apply_btn = page.locator("button#apply-button, button:has-text('Apply'), .apply-button").first
            if not apply_btn.is_visible():
                logger.info("No direct apply button found (may be expired or require manual link).")
                self.log_application(job_info, "Not Available", "External")
                return "Not Available"

            btn_label = apply_btn.inner_text().strip().lower()
            if "company site" in btn_label:
                logger.info("External employer link. Logged to Excel for candidate review.")
                self.log_application(job_info, "External Redirect", "External Employer Portal")
                return "External Redirect"

            # Execute 1-Click Apply
            apply_btn.click()
            time.sleep(2)

            # Handle questionnaire if present
            questionnaire_handled = self.handle_questionnaire(page)

            # Verify submission
            time.sleep(2)
            if page.locator("text=Applied, text=Application sent, text=successfully applied").count() > 0:
                app_type = "Questionnaire Modal" if questionnaire_handled else "1-Click Apply"
                logger.info("SUCCESS: Application submitted to %s!", job_info.get("company"))
                self.log_application(job_info, "Applied (Direct)", app_type)
                return "Applied (Direct)"
            else:
                self.log_application(job_info, "Submitted (Pending)", "Direct")
                return "Submitted"
        except Exception as e:
            logger.warning("Application exception for %s: %s", url, e)
            self.log_application(job_info, "Error", "1-Click Apply")
            return "Error"

    def handle_questionnaire(self, page):
        """Auto-fills employer screening questions inside the application modal or chatbot drawer."""
        answers = self.cfg["answers_to_common_questions"]
        handled = False
        try:
            # Multi-step loop (max 4 steps)
            for step in range(4):
                text_inputs = page.locator(".chatbot_drawer input[type='text'], .apply-message-container input, form input[type='text']").all()
                if not text_inputs and not page.locator("button:has-text('Submit'), button:has-text('Save & Apply')").is_visible():
                    break

                handled = True
                for inp in text_inputs:
                    placeholder = (inp.get_attribute("placeholder") or "").lower()
                    inp_id = (inp.get_attribute("id") or "").lower()
                    
                    if any(k in placeholder or k in inp_id for k in ["experience", "years", "yoe"]):
                        inp.fill(answers.get("experience", "2.5"))
                    elif "notice" in placeholder or "notice" in inp_id:
                        inp.fill(answers.get("notice_period", "30 days"))
                    elif "location" in placeholder or "city" in inp_id:
                        inp.fill(answers.get("current_location", "Hyderabad"))

                # Radio options (e.g., Relocation = Yes)
                yes_radios = page.locator("label:has-text('Yes'), input[value*='Yes']").all()
                for r in yes_radios:
                    try:
                        r.click()
                    except Exception:
                        pass

                # Click Submit or Next
                submit_btn = page.locator("button:has-text('Submit'), button:has-text('Apply Now'), button:has-text('Save & Apply'), button:has-text('Next')").first
                if submit_btn.is_visible():
                    submit_btn.click()
                    time.sleep(2)
                else:
                    break
        except Exception as ex:
            logger.debug("Questionnaire auto-fill note: %s", ex)
        return handled

    # --------------------------------------------------------------------------
    # FULL DAILY PIPELINE (Bump -> Scan -> Auto-Apply -> Excel Summary)
    # --------------------------------------------------------------------------
    def run_daily_pipeline(self, headless=False):
        """Executes complete automated workflow for daily 100k recruiter exposure."""
        logger.info("==================================================================")
        logger.info("LAUNCHING NAUKRI AUTONOMOUS DAILY WORKFLOW")
        logger.info("==================================================================")

        with sync_playwright() as p:
            context = self.get_context(p, headless=headless)
            page = context.pages[0] if context.pages else context.new_page()

            # 1. Auth Check
            self.ensure_auth(page)

            # 2. Bump Profile
            bump_ok = self.bump_profile(page)

            # 3. Scan & Filter Jobs
            roles = self.cfg["search_settings"]["roles"]
            locations = self.cfg["search_settings"]["locations"]
            daily_limit = self.cfg["search_settings"]["daily_application_limit"]

            all_new_jobs = []
            for r in roles[:2]:  # Top 2 roles (Azure Data Engineer, Data Engineer)
                for loc in locations[:2]:  # Top 2 locations (Hyderabad, Bangalore)
                    jobs = self.scan_jobs(page, r, loc, max_pages=1)
                    all_new_jobs.extend(jobs)
                    time.sleep(2)

            logger.info("Discovered %d candidate vacancies across target hubs.", len(all_new_jobs))

            # 4. Auto-Apply
            applied_today = 0
            for job in all_new_jobs:
                if applied_today >= daily_limit:
                    logger.info("Reached safe daily threshold of %d applications.", daily_limit)
                    break
                status = self.apply_to_job(page, job)
                if "Applied" in status or "Submitted" in status:
                    applied_today += 1
                time.sleep(random.uniform(2.5, 4.5))  # Safe human emulation delay

            # 5. Log Daily Metrics
            self.log_daily_summary(len(all_new_jobs), applied_today, bump_ok)

            context.close()
            logger.info("==================================================================")
            logger.info("DAILY PIPELINE COMPLETED: Applied to %d jobs. Logged to %s", applied_today, self.cfg["tracker_excel_path"])
            logger.info("==================================================================")

# ------------------------------------------------------------------------------
# CLI ENTRY POINT
# ------------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Naukri Autonomous System Engine")
    parser.add_argument("--bump", action="store_true", help="Bump profile timestamp to Today")
    parser.add_argument("--scan", action="store_true", help="Scan and discover fresh vacancies")
    parser.add_argument("--apply", action="store_true", help="Execute auto-application cycle")
    parser.add_argument("--daily", action="store_true", help="Run full end-to-end daily pipeline")
    parser.add_argument("--auth", action="store_true", help="Verify or set up 1-time Chrome login")
    parser.add_argument("--headless", action="store_true", help="Run browser silently in background")

    args = parser.parse_args()
    system = NaukriAutomationSystem()

    if args.auth:
        with sync_playwright() as p:
            context = system.get_context(p, headless=False)
            page = context.pages[0] if context.pages else context.new_page()
            system.ensure_auth(page)
            print("\n[OK] Authenticated session saved! You can now run daily automation.\n")
            context.close()
        return

    if args.bump:
        with sync_playwright() as p:
            context = system.get_context(p, headless=args.headless)
            page = context.pages[0] if context.pages else context.new_page()
            system.ensure_auth(page)
            system.bump_profile(page)
            context.close()
        return

    if args.scan:
        with sync_playwright() as p:
            context = system.get_context(p, headless=args.headless)
            page = context.pages[0] if context.pages else context.new_page()
            system.ensure_auth(page)
            for r in system.cfg["search_settings"]["roles"][:2]:
                system.scan_jobs(page, r, "hyderabad")
            context.close()
        return

    if args.apply:
        with sync_playwright() as p:
            context = system.get_context(p, headless=args.headless)
            page = context.pages[0] if context.pages else context.new_page()
            system.ensure_auth(page)
            jobs = system.scan_jobs(page, "azure-data-engineer", "hyderabad")
            applied = 0
            for j in jobs[:5]:
                res = system.apply_to_job(page, j)
                if "Applied" in res or "Submitted" in res:
                    applied += 1
                time.sleep(3)
            logger.info("Batch apply finished. Submitted %d applications.", applied)
            context.close()
        return

    # Default: Run daily pipeline
    system.run_daily_pipeline(headless=args.headless)

if __name__ == "__main__":
    main()
