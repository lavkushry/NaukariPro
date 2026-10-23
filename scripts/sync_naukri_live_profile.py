#!/usr/bin/env python3
"""
Naukri Live Profile Synchronization Script
Automates:
1. Updating CGI Current Designation to "Azure Data Engineer" for 100% recruiter search match.
2. Synchronizing boosted Profile Summary with top recruiter keywords.
3. Synchronizing all 4 Employment Role Descriptions (CGI, HFCL, CGI Apprentice, Stipe Solutions).
4. Synchronizing the flagship Azure Lakehouse and DataOps projects to the live profile.
5. Uploading the latest 1-page ATS-optimized Azure Data Engineer Resume PDF.
6. Bumping profile timestamp for fresh "Active Today" Resdex status.
"""

import os
import sys
import time
import json
import logging
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from playwright.sync_api import sync_playwright
from naukari_pro.config import load_config, RESUME_PDF_PATH, WORKSPACE_DIR
from naukari_pro.session import get_stealth_context, ensure_authenticated
from naukari_pro.modules.profile_enhancer import ProfileEnhancerEngine
from naukari_pro.modules.resume_maker import AIResumeMaker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("NaukriLiveSync")

STATE_FILE = os.path.join(WORKSPACE_DIR, "naukri_system", "session_state.json")

def _load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_state(state):
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.warning("Could not save session state: %s", e)

def sync_employment_designation(page, target_title="Azure Data Engineer"):
    if "profile" not in page.url:
        page.goto('https://www.naukri.com/mnjuser/profile', wait_until='domcontentloaded', timeout=45000)
        time.sleep(3)

    for i in range(1, 8):
        page.evaluate(f'window.scrollTo(0, {i * 600})')
        time.sleep(0.3)
    time.sleep(1)

    emp_section = page.locator('#lazyEmployment')
    emp_head = emp_section.locator('.widgetHead, span.edit, .editOneTheme').first
    try:
        emp_head.wait_for(state='visible', timeout=15000)
    except Exception:
        pass

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

def sync_profile_summary(page, summary_text):
    if not summary_text:
        return False
    logger.info("Synchronizing boosted Profile Summary...")
    if "profile" not in page.url:
        page.goto('https://www.naukri.com/mnjuser/profile', wait_until='domcontentloaded', timeout=45000)
        time.sleep(3)

    for i in range(1, 8):
        page.evaluate(f'window.scrollTo(0, {i * 600})')
        time.sleep(0.2)
    time.sleep(1)

    sum_section = page.locator('#lazyProfileSummary')
    edit_btn = sum_section.locator('.editOneTheme, span.edit').first
    if edit_btn.count() == 0 or not edit_btn.is_visible():
        logger.warning("Profile Summary edit button not found.")
        return False

    edit_btn.scroll_into_view_if_needed()
    edit_btn.click()
    time.sleep(2)

    ta = page.locator('#profileSummaryTxt, textarea[name="profileSummary"]').first
    if ta.count() == 0 or not ta.is_visible():
        logger.warning("Profile Summary textarea did not open.")
        return False

    ta.click()
    ta.fill("")
    time.sleep(0.3)
    ta.fill(summary_text)
    time.sleep(0.5)

    save_btn = page.locator('.profileSummaryEdit button:has-text("Save"), button.btn-dark-ot:has-text("Save")').last
    if save_btn.count() > 0 and save_btn.is_visible():
        save_btn.click()
        time.sleep(4)
        logger.info("Successfully updated Profile Summary on live Naukri profile.")
        return True
    return False

def sync_employment_descriptions(page, experience_data):
    logger.info("Synchronizing boosted Employment Role Descriptions...")
    if not experience_data:
        return False

    # Structure descriptions directly from unified configuration facts
    roles_payload = []
    for exp in experience_data:
        rname = exp.get("company", "Role")
        bullets = exp.get("bullets", [])
        desc = "\n".join(f"• {b}" for b in bullets)
        roles_payload.append((rname, desc))

    for idx, (rname, desc) in enumerate(roles_payload):
        logger.info("Updating Employment Role %d: %s...", idx + 1, rname)
        page.goto('https://www.naukri.com/mnjuser/profile', wait_until='domcontentloaded', timeout=45000)
        time.sleep(3)

        for i in range(1, 8):
            page.evaluate(f'window.scrollTo(0, {i * 600})')
            time.sleep(0.2)
        time.sleep(1)

        emp_sec = page.locator('#lazyEmployment')
        edit_btns = emp_sec.locator('.editOneTheme, span.edit')
        if idx >= edit_btns.count():
            logger.info("Employment slot %d not found (total %d); skipping.", idx, edit_btns.count())
            continue

        btn = edit_btns.nth(idx)
        btn.scroll_into_view_if_needed()
        time.sleep(0.5)
        btn.click()
        time.sleep(2.5)

        # For CGI current role, ensure designation is set to Azure Data Engineer
        if idx == 0:
            desig_input = page.locator('#designationSugg')
            if desig_input.count() > 0 and desig_input.is_visible():
                curr = desig_input.input_value().strip()
                if "Azure Data Engineer" not in curr:
                    desig_input.click()
                    desig_input.fill("")
                    time.sleep(0.2)
                    desig_input.type("Azure Data Engineer", delay=80)
                    time.sleep(1.5)
                    first_match = page.locator('li:has-text("Azure Data Engineer"), .sWrap li:has-text("Azure Data Engineer")').last
                    if first_match.count() > 0 and first_match.is_visible():
                        first_match.click()
                        time.sleep(0.5)
                    else:
                        desig_input.press("Tab")

        ta = page.locator('textarea#jobDescription, textarea[name="jobDescription"]').first
        if ta.count() > 0 and ta.is_visible():
            ta.click()
            ta.fill("")
            time.sleep(0.2)
            ta.fill(desc)
            time.sleep(0.3)
        else:
            logger.info("Notice: No jobDescription textarea in form for Role %d (%s) (internship/pre-configured card).", idx + 1, rname)

        save_btn = page.locator('#submitEmployment')
        if save_btn.count() > 0 and save_btn.is_visible():
            save_btn.click()
            time.sleep(4)
            logger.info("Successfully saved Employment Role %d: %s.", idx + 1, rname)
        else:
            logger.warning("Save button not found for Role %d.", idx + 1)
    return True

PROJECT_METADATA = [
    {
        "name": "Enterprise Medallion Lakehouse Platform on Azure",
        "client": "Enterprise Cloud Data Platform",
        "role": "Architected Medallion Lakehouse pipelines and distributed PySpark batch transformations on Azure Databricks with Delta Lake."
    },
    {
        "name": "Real-Time Streaming Ingestion & CDC Lakehouse",
        "client": "Streaming Lakehouse Platform",
        "role": "Engineered real-time streaming ingestion and CDC pipelines using Apache Kafka, Spark Structured Streaming, and Delta Lake."
    },
    {
        "name": "Cloud Data Platform CI/CD & Governance",
        "client": "DataOps & Cloud Infrastructure",
        "role": "Automated end-to-end DataOps release cycles, Terraform IaC provisioning, and Great Expectations quality validation gates."
    },
    {
        "name": "Cloud AI Infrastructure & Observability Platform",
        "client": "Cloud AI & Platform Engineering",
        "tech_stack": "Kubernetes, Docker, Prometheus, Grafana, OpenTelemetry, Python, CI/CD",
        "role": "Engineered real-time platform observability, telemetry dashboards, and automated CI/CD release pipelines across 15+ microservices.",
        "bullets": [
            "Built an end-to-end telemetry and observability backbone using Prometheus, Grafana, and OpenTelemetry, monitoring 15+ distributed microservices with under 100ms scraping latency, slashing incident MTTR by 40%.",
            "Automated deployment and scaling of data serving microservices using Docker, Kubernetes, and GitHub Actions with automated canary rollback safeguards, sustaining 99.9% platform availability."
        ]
    }
]

def sync_projects(page, projects_data):
    all_projects = list(projects_data)
    if len(all_projects) < 4 and len(PROJECT_METADATA) >= 4:
        all_projects.append(PROJECT_METADATA[3])

    logger.info("Synchronizing %d projects to live profile...", len(all_projects))
    for idx, proj in enumerate(all_projects):
        title = proj.get("name", "")
        tech = proj.get("tech_stack", "")
        bullets = proj.get("bullets", [])
        details = "\n".join(f"• {b}" for b in bullets)
        fallback_meta = PROJECT_METADATA[idx] if idx < len(PROJECT_METADATA) else {}
        client = proj.get("client") or fallback_meta.get("client", "Enterprise Cloud Data Platform")
        role_desc = proj.get("role") or fallback_meta.get("role", "Engineered scalable cloud data infrastructure and automated pipelines.")

        logger.info("Updating Project %d: '%s'...", idx + 1, title)
        page.goto('https://www.naukri.com/mnjuser/profile', wait_until='domcontentloaded', timeout=45000)
        time.sleep(3)

        for i in range(1, 8):
            page.evaluate(f'window.scrollTo(0, {i * 700})')
            time.sleep(0.3)
        time.sleep(2)

        edit_btns = page.locator('#lazyProject span.edit')
        total_btns = edit_btns.count()
        if idx >= total_btns:
            logger.info("Profile has %d project slots; skipping index %d.", total_btns, idx)
            break

        edit_btn = edit_btns.nth(idx)
        edit_btn.scroll_into_view_if_needed()
        time.sleep(0.5)
        edit_btn.click()
        time.sleep(2.5)

        title_input = page.locator('#projectTitle')
        title_input.wait_for(state="visible", timeout=15000)
        title_input.click()
        title_input.fill("")
        time.sleep(0.2)
        title_input.type(title, delay=20)
        time.sleep(0.4)

        client_input = page.locator('#clientName')
        if client_input.count() > 0:
            client_input.click()
            client_input.fill("")
            time.sleep(0.2)
            client_input.type(client, delay=20)
            time.sleep(0.4)
            client_input.press("Tab")

        details_textarea = page.locator('#projectDetails')
        details_textarea.click()
        details_textarea.fill("")
        time.sleep(0.2)
        details_textarea.fill(details)
        time.sleep(0.4)

        skills_in = page.locator('#skillsUsed')
        if skills_in.count() > 0:
            skills_in.click()
            skills_in.fill("")
            time.sleep(0.2)
            skills_in.type(tech, delay=20)
            time.sleep(0.4)

        role_in = page.locator('#roleDesc')
        if role_in.count() > 0:
            role_in.click()
            role_in.fill("")
            time.sleep(0.2)
            role_in.fill(role_desc)
            time.sleep(0.4)

        save_btn = page.locator('#submitProject')
        save_btn.click()
        time.sleep(4)
        logger.info("Project %d saved successfully.", idx + 1)
    return True

def sync_full_naukri_profile(page, config=None, force=False):
    """
    Executes complete end-to-end live profile synchronization and bumping.
    Throttled to once per day unless force=True.
    """
    cfg = config or load_config()
    today = datetime.now().strftime("%Y-%m-%d")
    state = _load_state()

    if not force and state.get("last_sync_date") == today:
        logger.info("Profile content already synchronized today (%s). Checking micro-bump...", today)
        enhancer = ProfileEnhancerEngine()
        return enhancer.bump_profile(page, force=False)

    target_desig = cfg.get("candidate", {}).get("current_designation", "Azure Data Engineer")
    summary = cfg.get("profile_summary", "")
    experience = cfg.get("experience", [])
    projects = cfg.get("projects", [])

    # 1. Regenerate 1-page ATS Resume PDF
    logger.info("Compiling canonical 1-page ATS Resume PDF from unified facts...")
    maker = AIResumeMaker()
    pdf_path = maker.build_ats_resume_pdf(config=cfg)

    # 2. Update Designation
    sync_employment_designation(page, target_title=target_desig)

    # 3. Update Profile Summary
    sync_profile_summary(page, summary)

    # 4. Update Employment Descriptions
    sync_employment_descriptions(page, experience)

    # 5. Update Projects
    sync_projects(page, projects)

    # 6. Upload ATS Resume PDF
    enhancer = ProfileEnhancerEngine()
    enhancer.upload_resume_pdf(page, pdf_path=pdf_path)

    # 7. Micro-bump profile timestamp
    enhancer.bump_profile(page, force=True)

    # Record sync state
    state["last_sync_date"] = today
    state["last_sync_timestamp"] = datetime.now().isoformat()
    state["last_bumped_date"] = today
    state["last_bumped_timestamp"] = datetime.now().isoformat()
    _save_state(state)

    logger.info("✓ Full Naukri profile synchronization and boost completed!")
    return True

def main():
    cfg = load_config()
    with sync_playwright() as p:
        ctx = get_stealth_context(p, headless=True)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        if not ensure_authenticated(page, headless=True):
            logger.error("Authentication check failed. Cannot proceed with live synchronization.")
            return False

        sync_full_naukri_profile(page, config=cfg, force=True)
        ctx.close()
    logger.info("Naukri live profile synchronization completed successfully!")

if __name__ == '__main__':
    main()
