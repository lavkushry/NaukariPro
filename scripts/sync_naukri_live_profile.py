#!/usr/bin/env python3
"""
Naukri Live Profile Synchronization Script
Automates:
1. Updating CGI Current Designation to "Azure Data Engineer" for 100% recruiter search match.
2. Synchronizing the 3 flagship Azure Lakehouse projects to the live profile.
3. Uploading the latest 1-page ATS-optimized Azure Data Engineer Resume PDF.
4. Bumping profile timestamp for fresh active status.
"""

import os
import sys
import time
import logging

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from playwright.sync_api import sync_playwright
from naukari_pro.config import load_config, RESUME_PDF_PATH
from naukari_pro.session import get_stealth_context
from naukari_pro.modules.profile_enhancer import ProfileEnhancerEngine
from naukari_pro.modules.resume_maker import AIResumeMaker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("NaukriLiveSync")

def sync_employment_designation(page, target_title="Azure Data Engineer"):
    logger.info("Checking and updating CGI current designation to '%s'...", target_title)
    page.goto('https://www.naukri.com/mnjuser/profile', wait_until='domcontentloaded', timeout=45000)
    time.sleep(4)

    page.evaluate('''() => {
        const el = document.getElementById('lazyEmployment');
        if (el) el.scrollIntoView();
    }''')
    time.sleep(2)

    emp_section = page.locator('#lazyEmployment')
    first_role_text = emp_section.inner_text()
    if target_title in first_role_text and "CGI" in first_role_text:
        logger.info("CGI current designation is already set to '%s'.", target_title)
        return True

    edit_btn = emp_section.locator('.editOneTheme, span.edit').first
    edit_btn.click()
    time.sleep(2)

    desig_input = page.locator('#designationSugg')
    desig_input.click()
    desig_input.fill("")
    time.sleep(0.3)
    page.keyboard.type(target_title, delay=80)
    time.sleep(1.5)

    first_match = page.locator(
        f'li:has-text("{target_title}"), .sWrap li:has-text("{target_title}"), div:has-text("{target_title}")'
    ).last
    if first_match.count() > 0 and first_match.is_visible():
        first_match.click()
        time.sleep(1)
    else:
        desig_input.press("Tab")
        time.sleep(1)

    save_btn = page.locator('#submitEmployment')
    save_btn.click()
    time.sleep(4)
    logger.info("Successfully updated CGI current designation.")
    return True

def sync_projects(page, projects_data):
    logger.info("Synchronizing %d production Azure Lakehouse projects to live profile...", len(projects_data))
    for idx, proj in enumerate(projects_data):
        title = proj.get("name", "")
        tech = proj.get("tech_stack", "")
        bullets = proj.get("bullets", [])
        details = "\n".join(f"• {b}" for b in bullets)

        logger.info("Updating Project %d: '%s'...", idx + 1, title)
        page.goto('https://www.naukri.com/mnjuser/profile', wait_until='domcontentloaded', timeout=45000)
        time.sleep(4)

        for i in range(1, 8):
            page.evaluate(f'window.scrollTo(0, {i * 700})')
            time.sleep(0.3)
        time.sleep(2)

        clicked = page.evaluate(f'''() => {{
            const btns = Array.from(document.querySelectorAll('#lazyProject span[aria-label*="Edit project"]'));
            if (btns.length > {idx}) {{
                btns[{idx}].scrollIntoView();
                btns[{idx}].click();
                return true;
            }}
            return false;
        }}''')

        if not clicked:
            logger.warning("Could not find project edit button at index %d.", idx)
            continue

        time.sleep(2.5)

        title_input = page.locator('#projectTitle')
        title_input.wait_for(state="visible", timeout=15000)
        title_input.click()
        title_input.fill("")
        time.sleep(0.3)
        title_input.type(title, delay=25)
        time.sleep(0.5)

        client_input = page.locator('#clientName')
        if client_input.count() > 0:
            client_input.click()
            client_input.fill("")
            time.sleep(0.3)
            client_input.type("Enterprise Cloud Data Platform", delay=25)
            time.sleep(0.5)
            client_input.press("Tab")

        details_textarea = page.locator('#projectDetails')
        details_textarea.click()
        details_textarea.fill("")
        time.sleep(0.3)
        details_textarea.fill(details)
        time.sleep(0.5)

        save_btn = page.locator('#submitProject')
        save_btn.click()
        time.sleep(4)
        logger.info("Project %d saved successfully.", idx + 1)

def main():
    cfg = load_config()
    target_desig = cfg.get("candidate", {}).get("current_designation", "Azure Data Engineer")
    projects = cfg.get("projects", [])

    # 1. Regenerate 1-page ATS Resume
    logger.info("Generating canonical 1-page ATS Resume PDF...")
    maker = AIResumeMaker()
    pdf_path = maker.build_ats_resume_pdf(config=cfg)
    logger.info("Resume PDF ready at %s", pdf_path)

    # 2. Live Naukri browser updates
    with sync_playwright() as p:
        ctx = get_stealth_context(p, headless=True)
        page = ctx.new_page()

        # Update designation
        sync_employment_designation(page, target_title=target_desig)

        # Update projects
        sync_projects(page, projects)

        # Upload ATS Resume PDF
        enhancer = ProfileEnhancerEngine()
        enhancer.upload_resume_pdf(page, pdf_path=pdf_path)

        # Micro-bump profile timestamp
        enhancer.bump_profile(page, force=True)

        ctx.close()
    logger.info("Naukri live profile synchronization completed successfully!")

if __name__ == '__main__':
    main()
