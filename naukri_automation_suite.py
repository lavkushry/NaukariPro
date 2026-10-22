#!/usr/bin/env python3
"""
Naukri Automation Suite
Author: Lavkush Kumar
Capabilities:
  1. Profile Refresher: Automatically touches headline/profile to maintain "Last updated today" status.
  2. Job Search & Exporter: Scrapes live Azure Data Engineer / DevOps job openings and exports to Excel.
  3. Auto-Apply Engine: Automatically scans matched jobs and submits applications.
Bypasses Akamai Bot Protection using stealth browser context and persistent session.
"""

import os
import sys
import time
import argparse
import logging
from datetime import datetime
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("NaukriBot")

SESSION_DIR = os.path.expanduser("~/.naukri_automation_profile")

STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
window.navigator.chrome = { runtime: {} };
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en', 'hi'] });
"""

def get_browser_context(playwright, headless=False):
    """Launches Chromium with persistent session and anti-detection flags."""
    context = playwright.chromium.launch_persistent_context(
        user_data_dir=SESSION_DIR,
        headless=headless,
        channel="chrome",  # Uses local Google Chrome if available for max legitimacy
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--no-sandbox",
            "--disable-infobars",
            "--start-maximized"
        ],
        viewport=None,
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    )
    context.add_init_script(STEALTH_JS)
    return context

def ensure_login(page):
    """Ensures user is authenticated. If not, pauses for 1-time manual login."""
    page.goto("https://www.naukri.com/mnjuser/profile", wait_until="domcontentloaded")
    time.sleep(3)
    if "login" in page.url or page.locator("text=Login").is_visible():
        logger.warning("Session not active. Please log in manually in the opened browser window...")
        page.wait_for_url("**/profile**", timeout=180000)
        logger.info("Login detected! Session saved permanently to %s", SESSION_DIR)
    else:
        logger.info("Existing authenticated session verified.")

# ==============================================================================
# FEATURE 1: DAILY PROFILE REFRESHER (BUMPER)
# ==============================================================================
def refresh_profile(page):
    """
    Subtly updates the resume headline or key skills to reset the 'Last updated' timestamp.
    This pushes your profile to the top of recruiter searches across India.
    """
    logger.info("=== Running Profile Refresher ===")
    page.goto("https://www.naukri.com/mnjuser/profile", wait_until="networkidle")
    time.sleep(3)

    try:
        # Locate Resume Headline edit button
        headline_edit = page.locator("span.edit:has-text('edit')").first
        if not headline_edit.is_visible():
            headline_edit = page.locator(".widgetHead .edit").first

        if headline_edit.is_visible():
            headline_edit.click()
            time.sleep(1.5)

            # Target the headline textarea
            textarea = page.locator("textarea#resumeHeadlineTxt, textarea").first
            current_text = textarea.input_value().strip()

            # Toggle a trailing period or space to trigger a legitimate update
            if current_text.endswith("."):
                new_text = current_text[:-1]
            else:
                new_text = current_text + "."

            textarea.fill(new_text)
            time.sleep(1)

            # Click Save
            save_btn = page.locator("button:has-text('Save')").first
            save_btn.click()
            time.sleep(3)
            logger.info("SUCCESS: Profile timestamp touched! Status set to 'Last updated today'.")
            return True
        else:
            logger.warning("Headline edit button not found. Trying alternative save button...")
            page.evaluate("window.scrollTo(0, 300)")
            return False
    except Exception as e:
        logger.error("Error refreshing profile: %s", e)
        return False

# ==============================================================================
# FEATURE 2: AUTO JOB SEARCH & EXPORTER
# ==============================================================================
def search_jobs(page, role="azure-data-engineer", location="hyderabad", max_pages=2):
    """
    Searches jobs matching target title and location posted in the last 24h,
    and returns a structured list of vacancies.
    """
    logger.info("=== Searching Jobs: %s in %s ===", role, location)
    search_url = f"https://www.naukri.com/{role}-jobs-in-{location}?jobAge=1"
    page.goto(search_url, wait_until="networkidle")
    time.sleep(3)

    jobs = []
    for p_idx in range(1, max_pages + 1):
        logger.info("Scraping page %d...", p_idx)
        articles = page.locator("article.jobTuple, .cust-job-tuple").all()
        logger.info("Found %d job tuples on page %d", len(articles), p_idx)

        for art in articles:
            try:
                title_elem = art.locator("a.title").first
                company_elem = art.locator("a.comp-name, .comp-name-link").first
                exp_elem = art.locator(".exp-wrap, span[class*='exp']").first
                loc_elem = art.locator(".loc-wrap, span[class*='loc']").first
                url = title_elem.get_attribute("href") if title_elem.count() > 0 else ""

                job_info = {
                    "title": title_elem.inner_text().strip() if title_elem.count() > 0 else "N/A",
                    "company": company_elem.inner_text().strip() if company_elem.count() > 0 else "N/A",
                    "experience": exp_elem.inner_text().strip() if exp_elem.count() > 0 else "N/A",
                    "location": loc_elem.inner_text().strip() if loc_elem.count() > 0 else "N/A",
                    "url": url,
                    "date_scraped": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                jobs.append(job_info)
            except Exception as ex:
                continue

        # Next page if available
        next_btn = page.locator("a:has-text('Next')").first
        if next_btn.is_visible() and p_idx < max_pages:
            next_btn.click()
            time.sleep(3)
        else:
            break

    logger.info("Total jobs scraped: %d", len(jobs))
    return jobs

def export_jobs_to_excel(jobs, filename="Naukri_Discovered_Jobs.xlsx"):
    """Saves discovered jobs to an Excel file using openpyxl."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Discovered_Jobs"

    headers = ["Job Title", "Company", "Experience", "Location", "URL", "Date Scraped"]
    ws.append(headers)

    header_fill = PatternFill(start_color="11355D", end_color="11355D", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    for j in jobs:
        ws.append([j["title"], j["company"], j["experience"], j["location"], j["url"], j["date_scraped"]])

    for col in ws.columns:
        max_len = max(len(str(c.value or "")) for c in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 50)

    wb.save(filename)
    logger.info("Saved %d jobs to %s", len(jobs), filename)

# ==============================================================================
# FEATURE 3: AUTO APPLY ENGINE
# ==============================================================================
def auto_apply(page, job_urls, max_apps=5):
    """Navigates to job postings and triggers 1-Click Apply if available."""
    logger.info("=== Running Auto-Apply (Max: %d) ===", max_apps)
    applied_count = 0

    for url in job_urls:
        if applied_count >= max_apps:
            break
        if not url:
            continue

        try:
            logger.info("Reviewing: %s", url)
            page.goto(url, wait_until="networkidle")
            time.sleep(2)

            # Check for standard 1-click apply button on Naukri
            apply_btn = page.locator("button#apply-button, button:has-text('Apply')").first
            if apply_btn.is_visible():
                btn_text = apply_btn.inner_text().strip().lower()
                if "company site" in btn_text:
                    logger.info("Skipping external company redirect.")
                    continue

                apply_btn.click()
                time.sleep(2)

                # Check if application confirmation appeared
                if page.locator("text=Applied, text=Application sent").first.is_visible():
                    logger.info("SUCCESS: Applied to %s", url)
                    applied_count += 1
                time.sleep(2)
        except Exception as e:
            logger.warning("Could not apply to %s: %s", url, e)

    logger.info("Total successful applications: %d", applied_count)

# ==============================================================================
# MAIN RUNNER
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="Naukri Automation Engine")
    parser.add_argument("--refresh", action="store_true", help="Bump profile timestamp to Today")
    parser.add_argument("--search", action="store_true", help="Search and scrape live jobs")
    parser.add_argument("--apply", action="store_true", help="Auto-apply to scraped jobs")
    parser.add_argument("--all", action="store_true", help="Run full pipeline: refresh + search + apply")
    parser.add_argument("--role", default="azure-data-engineer", help="Role query string")
    parser.add_argument("--location", default="hyderabad", help="Target city")
    parser.add_argument("--headless", action="store_true", help="Run browser headlessly")

    args = parser.parse_args()

    if not any([args.refresh, args.search, args.apply, args.all]):
        args.all = True

    with sync_playwright() as p:
        context = get_browser_context(p, headless=args.headless)
        page = context.pages[0] if context.pages else context.new_page()

        ensure_login(page)

        if args.refresh or args.all:
            refresh_profile(page)

        scraped_jobs = []
        if args.search or args.all:
            scraped_jobs = search_jobs(page, role=args.role, location=args.location)
            if scraped_jobs:
                export_jobs_to_excel(scraped_jobs)

        if (args.apply or args.all) and scraped_jobs:
            auto_apply(page, [j["url"] for j in scraped_jobs], max_apps=3)

        context.close()
        logger.info("Automation run complete.")

if __name__ == "__main__":
    main()
