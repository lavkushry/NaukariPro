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

DEFAULT_TOP_25_KEY_SKILLS = [
    "Azure Databricks",
    "PySpark",
    "Delta Lake",
    "Azure Data Factory (ADF)",
    "SQL",
    "Apache Kafka",
    "Python",
    "ETL Pipelines",
    "Medallion Architecture",
    "ADLS Gen2",
    "Azure Synapse Analytics",
    "Microsoft Fabric",
    "Unity Catalog",
    "dbt",
    "Change Data Capture (CDC)",
    "Terraform",
    "Kubernetes (EKS)",
    "Docker",
    "CI/CD",
    "Azure DevOps",
    "PostgreSQL",
    "Data Modeling",
    "Star Schema Data Modeling",
    "DataOps",
    "Great Expectations"
]

DEFAULT_PREFERRED_LOCATIONS = [
    "Bengaluru",
    "Hyderabad",
    "Pune",
    "Gurugram",
    "Noida",
    "Mumbai",
    "Chennai"
]

DEFAULT_IT_SKILLS = [
    {"skill": "Azure Databricks", "version": "-", "last_used": "2026", "exp_years": 2, "exp_months": 0},
    {"skill": "PySpark", "version": "3.5", "last_used": "2026", "exp_years": 2, "exp_months": 0},
    {"skill": "Delta Lake", "version": "-", "last_used": "2026", "exp_years": 2, "exp_months": 0},
    {"skill": "Azure Data Factory (ADF)", "version": "-", "last_used": "2026", "exp_years": 2, "exp_months": 0},
    {"skill": "SQL", "version": "-", "last_used": "2026", "exp_years": 2, "exp_months": 6},
    {"skill": "Apache Kafka", "version": "-", "last_used": "2026", "exp_years": 2, "exp_months": 0},
    {"skill": "Python", "version": "3.x", "last_used": "2026", "exp_years": 2, "exp_months": 6},
    {"skill": "Terraform", "version": "1.x", "last_used": "2026", "exp_years": 2, "exp_months": 0},
    {"skill": "Kubernetes (EKS / kubeadm)", "version": "1.28", "last_used": "2026", "exp_years": 2, "exp_months": 6},
    {"skill": "Docker", "version": "-", "last_used": "2026", "exp_years": 2, "exp_months": 6},
    {"skill": "Microsoft Fabric", "version": "-", "last_used": "2026", "exp_years": 1, "exp_months": 0},
    {"skill": "Azure Synapse Analytics", "version": "-", "last_used": "2026", "exp_years": 1, "exp_months": 0},
    {"skill": "PostgreSQL", "version": "15", "last_used": "2026", "exp_years": 2, "exp_months": 0},
]

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

def sync_resume_headline(page, target_headline=None):
    """
    Ensures the complete 247-char Azure Data Engineer headline is persisted on live profile.
    """
    cfg = load_config()
    default_hl = (
        "Azure Data Engineer | Azure Databricks · PySpark · Delta Lake · "
        "Azure Data Factory (ADF) · SQL · Apache Kafka · Terraform · Medallion Architecture | "
        "Certified AZ-900 · Databricks Associate (Pursuing) | 2.5 YOE Cloud Data Platforms & CI/CD"
    )
    hl = (target_headline or cfg.get("headline_template", default_hl)).strip()
    if not hl:
        hl = default_hl

    logger.info("Synchronizing Resume Headline (%d chars)...", len(hl))
    if "profile" not in page.url:
        page.goto('https://www.naukri.com/mnjuser/profile', wait_until='domcontentloaded', timeout=45000)
        time.sleep(3)

    try:
        headline_edit = page.locator(
            'span[aria-label*="Edit resume headline"], span[aria-label*="resume headline" i], .resumeHeadline .edit'
        ).first

        if headline_edit.count() > 0 and headline_edit.is_visible():
            headline_edit.scroll_into_view_if_needed()
            headline_edit.click()
            time.sleep(2)

            textarea = page.locator(
                "textarea#resumeHeadlineTxt, form[name='resumeHeadline'] textarea, .resumeHeadline textarea, textarea"
            ).first

            if textarea.is_visible():
                curr_val = textarea.input_value().strip()
                if curr_val.rstrip(".") != hl.rstrip("."):
                    textarea.click()
                    textarea.fill("")
                    time.sleep(0.2)
                    textarea.fill(hl)
                    time.sleep(0.5)

                    save_btn = page.locator(
                        '.resumeHeadline button:has-text("Save"), button.btn-dark-ot:has-text("Save"), button:has-text("Save")'
                    ).first
                    if save_btn.count() == 0 or not save_btn.is_visible():
                        save_btn = page.get_by_role("button", name="Save", exact=True)

                    if save_btn.count() > 0 and save_btn.is_visible():
                        save_btn.click()
                        time.sleep(3)
                        logger.info("Successfully updated Resume Headline on live profile.")
                        return True
                else:
                    logger.info("Resume Headline already matches target headline on live profile.")
                    return True
            else:
                logger.warning("Headline textarea not visible.")
    except Exception as e:
        logger.warning("Notice updating Resume Headline: %s", e)
    return False

def sync_notice_period(page, target_notice="15 Days or less"):
    """
    Automates Notice Period selection (15 Days or less / 15 days) on live Naukri profile.
    Checks and updates via Current Employment (#lazyEmployment) or Career Profile (#lazyCareerProfile).
    """
    logger.info("Synchronizing Notice Period to '%s'...", target_notice)
    if "profile" not in page.url:
        page.goto('https://www.naukri.com/mnjuser/profile', wait_until='domcontentloaded', timeout=45000)
        time.sleep(3)

    for i in range(1, 6):
        page.evaluate(f'window.scrollTo(0, {i * 500})')
        time.sleep(0.2)
    time.sleep(1)

    # Strategy A: Check Current Employment (#lazyEmployment)
    try:
        emp_section = page.locator('#lazyEmployment')
        if emp_section.count() > 0:
            edit_btn = emp_section.locator('.editOneTheme, span.edit').first
            if edit_btn.count() > 0 and edit_btn.is_visible():
                edit_btn.scroll_into_view_if_needed()
                edit_btn.click()
                time.sleep(2)

                np_loc = page.locator('#noticePeriod, select[name="noticePeriod"], [name="noticePeriod"], .noticePeriod select').first
                if np_loc.count() > 0 and np_loc.is_visible():
                    try:
                        options = np_loc.locator('option').all_inner_texts()
                        match_opt = next((o for o in options if "15" in o), None)
                        if match_opt:
                            np_loc.select_option(label=match_opt)
                            logger.info("Selected notice period option: %s", match_opt)
                    except Exception:
                        pass
                else:
                    np_dropdown = page.locator('.noticePeriod .dropdown, div[name="noticePeriod"], #noticePeriodDiv').first
                    if np_dropdown.count() > 0 and np_dropdown.is_visible():
                        np_dropdown.click()
                        time.sleep(1)
                        target_opt = page.locator(f'li:has-text("{target_notice}"), span:has-text("15 Days"), li:has-text("15 days")').first
                        if target_opt.count() > 0 and target_opt.is_visible():
                            target_opt.click()
                            time.sleep(0.5)

                save_btn = page.locator('#submitEmployment')
                if save_btn.count() > 0 and save_btn.is_visible():
                    save_btn.click()
                    time.sleep(3)
                    logger.info("Submitted Employment modal for Notice Period.")
    except Exception as e:
        logger.warning("Notice period update in #lazyEmployment notice: %s", e)

    # Strategy B: Check Career Profile (#lazyCareerProfile)
    try:
        cp_section = page.locator('#lazyCareerProfile, .desiredProfile')
        if cp_section.count() > 0:
            cp_section.scroll_into_view_if_needed()
            edit_btn = cp_section.locator('.editOneTheme, span.edit, .desiredProfile .edit').first
            if edit_btn.count() > 0 and edit_btn.is_visible():
                edit_btn.click()
                time.sleep(2)

                avail_loc = page.locator('#availabilityToJoin, select[name="availabilityToJoin"], #noticePeriod').first
                if avail_loc.count() > 0 and avail_loc.is_visible():
                    try:
                        avail_loc.select_option(label="15 Days or less")
                    except Exception:
                        pass
                else:
                    avail_chip = page.locator('span:has-text("15 Days or less"), label:has-text("15 Days or less"), div:has-text("15 Days or less")').first
                    if avail_chip.count() > 0 and avail_chip.is_visible():
                        avail_chip.click()

                save_btn = page.locator('#submitDesiredProfile, #submitCareerProfile, button:has-text("Save")').first
                if save_btn.count() > 0 and save_btn.is_visible():
                    save_btn.click()
                    time.sleep(3)
                    logger.info("Submitted Career Profile modal for Notice Period.")
    except Exception as e:
        logger.warning("Notice period update in #lazyCareerProfile notice: %s", e)

    return True

def sync_preferred_locations(page, locations=None):
    """
    Automates Preferred Locations selection for all 7 tech hubs in #lazyCareerProfile:
    ("Bengaluru", "Hyderabad", "Pune", "Gurugram", "Noida", "Mumbai", "Chennai").
    """
    target_locations = locations or DEFAULT_PREFERRED_LOCATIONS
    logger.info("Synchronizing 7 Tier-1 Preferred Locations: %s...", ", ".join(target_locations))

    if "profile" not in page.url:
        page.goto('https://www.naukri.com/mnjuser/profile', wait_until='domcontentloaded', timeout=45000)
        time.sleep(3)

    for i in range(1, 8):
        page.evaluate(f'window.scrollTo(0, {i * 600})')
        time.sleep(0.2)
    time.sleep(1)

    cp_section = page.locator('#lazyCareerProfile, .desiredProfile')
    if cp_section.count() == 0:
        logger.warning("#lazyCareerProfile section not found.")
        return False

    cp_section.scroll_into_view_if_needed()
    time.sleep(1)

    edit_btn = cp_section.locator('.editOneTheme, span.edit, .desiredProfile .edit').first
    if edit_btn.count() == 0 or not edit_btn.is_visible():
        logger.warning("Career Profile edit button not found.")
        return False

    edit_btn.click()
    time.sleep(2.5)

    loc_input = page.locator('#locationSugg, #preferredLocation, input[placeholder*="location" i]').first
    if loc_input.count() == 0 or not loc_input.is_visible():
        logger.warning("Location input in Career Profile not visible.")
        return False

    for loc in target_locations:
        try:
            chip = page.locator(f'.desiredProfileForm span.chip:has-text("{loc}"), .sugChips span:has-text("{loc}"), .chip:has-text("{loc}")').first
            if chip.count() > 0 and chip.is_visible():
                continue

            loc_input.click()
            loc_input.fill("")
            time.sleep(0.2)
            loc_input.type(loc, delay=60)
            time.sleep(1.2)

            suggestion = page.locator(f'li:has-text("{loc}"), .sWrap li:has-text("{loc}"), div.layer li:has-text("{loc}")').first
            if suggestion.count() > 0 and suggestion.is_visible():
                suggestion.click()
                time.sleep(0.4)
            else:
                loc_input.press("Enter")
                time.sleep(0.4)
        except Exception as e:
            logger.warning("Could not add location %s: %s", loc, e)

    save_btn = page.locator('#submitDesiredProfile, #submitCareerProfile, button:has-text("Save")').first
    if save_btn.count() > 0 and save_btn.is_visible():
        save_btn.click()
        time.sleep(4)
        logger.info("Successfully updated Preferred Locations in Career Profile.")
        return True
    return False

def sync_key_skills(page, keywords=None):
    """
    Automates Key Skills tag cloud in #lazyKeySkills with top 25 Azure Data Engineering keywords.
    """
    target_skills = keywords or DEFAULT_TOP_25_KEY_SKILLS
    logger.info("Synchronizing top %d Key Skills to live profile...", len(target_skills))

    if "profile" not in page.url:
        page.goto('https://www.naukri.com/mnjuser/profile', wait_until='domcontentloaded', timeout=45000)
        time.sleep(3)

    for i in range(1, 5):
        page.evaluate(f'window.scrollTo(0, {i * 500})')
        time.sleep(0.2)
    time.sleep(1)

    ks_section = page.locator('#lazyKeySkills, .keySkills')
    if ks_section.count() == 0:
        logger.warning("#lazyKeySkills section not found.")
        return False

    ks_section.scroll_into_view_if_needed()
    time.sleep(0.5)

    edit_btn = ks_section.locator('.editOneTheme, span.edit, .keySkills .edit').first
    if edit_btn.count() == 0 or not edit_btn.is_visible():
        logger.warning("Key Skills edit button not found.")
        return False

    edit_btn.click()
    time.sleep(2.5)

    skill_input = page.locator('#keySkillSugg, input[placeholder*="skill" i], #keySkillsTxt').first
    if skill_input.count() == 0 or not skill_input.is_visible():
        logger.warning("Key skill input field not visible.")
        return False

    for skill in target_skills:
        try:
            chip = page.locator(f'.chip:has-text("{skill}"), .tag:has-text("{skill}"), .sugChips span:has-text("{skill}")').first
            if chip.count() > 0 and chip.is_visible():
                continue

            skill_input.click()
            skill_input.fill("")
            time.sleep(0.15)
            skill_input.type(skill, delay=50)
            time.sleep(1.0)

            suggestion = page.locator(f'li:has-text("{skill}"), .sWrap li:has-text("{skill}")').first
            if suggestion.count() > 0 and suggestion.is_visible():
                suggestion.click()
                time.sleep(0.3)
            else:
                skill_input.press("Enter")
                time.sleep(0.3)
        except Exception as e:
            logger.warning("Could not add skill %s: %s", skill, e)

    save_btn = page.locator('#submitKeySkills, button:has-text("Save"), .saveKeySkills').first
    if save_btn.count() > 0 and save_btn.is_visible():
        save_btn.click()
        time.sleep(4)
        logger.info("Successfully updated Key Skills.")
        return True
    return False

def sync_it_skills(page, it_skills=None):
    """
    Automates Detailed IT Skills table in #lazyItSkills for 13 skills from
    NAUKRI_PROFILE_COMPLETE_UPDATE_DATA_ENGINEER.md with versions, experience, and last used.
    """
    target_skills = it_skills or DEFAULT_IT_SKILLS
    logger.info("Synchronizing %d IT Skills in #lazyItSkills...", len(target_skills))

    if "profile" not in page.url:
        page.goto('https://www.naukri.com/mnjuser/profile', wait_until='domcontentloaded', timeout=45000)
        time.sleep(3)

    for i in range(1, 8):
        page.evaluate(f'window.scrollTo(0, {i * 600})')
        time.sleep(0.2)
    time.sleep(1)

    it_section = page.locator('#lazyItSkills, .itSkills')
    if it_section.count() == 0:
        logger.warning("#lazyItSkills section not found.")
        return False

    it_section.scroll_into_view_if_needed()
    time.sleep(1)

    table_text = it_section.inner_text() if it_section.count() > 0 else ""

    for item in target_skills:
        s_name = item["skill"]
        ver = item.get("version", "-")
        last_u = item.get("last_used", "2026")
        exp_y = str(item.get("exp_years", 2))

        if s_name in table_text:
            continue

        try:
            add_btn = it_section.locator('span.add, .add-btn, a:has-text("Add another"), span:has-text("Add")').first
            if add_btn.count() == 0 or not add_btn.is_visible():
                add_btn = page.locator('#lazyItSkills .editOneTheme, #lazyItSkills span.edit').first

            if add_btn.count() > 0 and add_btn.is_visible():
                add_btn.scroll_into_view_if_needed()
                add_btn.click()
                time.sleep(2)

                s_input = page.locator('#itSkillSugg, #skillName, input[placeholder*="skill" i]').first
                if s_input.count() > 0 and s_input.is_visible():
                    s_input.click()
                    s_input.fill("")
                    s_input.type(s_name, delay=50)
                    time.sleep(1)

                    match = page.locator(f'li:has-text("{s_name}"), .sWrap li:has-text("{s_name}")').first
                    if match.count() > 0 and match.is_visible():
                        match.click()
                    else:
                        s_input.press("Enter")

                if ver and ver != "-":
                    v_input = page.locator('#version, input[name="version"]').first
                    if v_input.count() > 0 and v_input.is_visible():
                        v_input.fill(ver)

                ly_select = page.locator('#lastUsedYear, select[name="lastUsedYear"]').first
                if ly_select.count() > 0 and ly_select.is_visible():
                    try:
                        ly_select.select_option(label=last_u)
                    except Exception:
                        pass

                ey_select = page.locator('#expYears, select[name="expYears"]').first
                if ey_select.count() > 0 and ey_select.is_visible():
                    try:
                        ey_select.select_option(value=exp_y)
                    except Exception:
                        pass

                save_btn = page.locator('#submitItSkills, button:has-text("Save")').first
                if save_btn.count() > 0 and save_btn.is_visible():
                    save_btn.click()
                    time.sleep(3)
                    logger.info("Saved IT skill: %s", s_name)
        except Exception as e:
            logger.warning("Notice updating IT skill %s: %s", s_name, e)

    return True

def sync_full_naukri_profile(page, config=None, force=False):
    """
    Executes complete end-to-end live profile synchronization and bumping.
    Allows 3x/day scheduled boosts: if already synchronized today and not force,
    still executes micro-bump with cooldown to refresh Resdex timestamp.
    """
    cfg = config or load_config()
    today = datetime.now().strftime("%Y-%m-%d")
    state = _load_state()

    # If content was already synchronized today and not force, perform scheduled freshness boost (3x/day)
    if not force and state.get("last_sync_date") == today:
        logger.info("Profile content already synchronized today (%s). Performing scheduled freshness boost...", today)
        enhancer = ProfileEnhancerEngine()
        return enhancer.bump_profile(page, force=False)

    target_desig = cfg.get("candidate", {}).get("current_designation", "Azure Data Engineer")
    summary = cfg.get("profile_summary", "")
    experience = cfg.get("experience", [])
    projects = cfg.get("projects", [])
    target_notice = cfg.get("candidate", {}).get("notice_period", "15 Days or less")
    preferred_locs = cfg.get("candidate", {}).get("preferred_locations", DEFAULT_PREFERRED_LOCATIONS)
    key_skills = cfg.get("default_keywords", DEFAULT_TOP_25_KEY_SKILLS)
    headline = cfg.get("headline_template", None)

    # 1. Regenerate 1-page ATS Resume PDF
    logger.info("Compiling canonical 1-page ATS Resume PDF from unified facts...")
    maker = AIResumeMaker()
    pdf_path = maker.build_ats_resume_pdf(config=cfg)

    # 2. Update Resume Headline (247-char saturated)
    sync_resume_headline(page, target_headline=headline)

    # 3. Update Designation
    sync_employment_designation(page, target_title=target_desig)

    # 4. Update Notice Period (15 Days or less)
    sync_notice_period(page, target_notice=target_notice)

    # 5. Update Profile Summary
    sync_profile_summary(page, summary)

    # 6. Update Key Skills Tag Cloud (top 25 keywords)
    sync_key_skills(page, keywords=key_skills)

    # 7. Update Employment Descriptions
    sync_employment_descriptions(page, experience)

    # 8. Update Projects
    sync_projects(page, projects)

    # 9. Update Detailed IT Skills (13 skills)
    sync_it_skills(page, it_skills=DEFAULT_IT_SKILLS)

    # 10. Update Preferred Locations (7 Tier-1 tech hubs)
    sync_preferred_locations(page, locations=preferred_locs)

    # 11. Upload ATS Resume PDF
    enhancer = ProfileEnhancerEngine()
    enhancer.upload_resume_pdf(page, pdf_path=pdf_path)

    # 12. Micro-bump profile timestamp
    enhancer.bump_profile(page, force=True)

    # Record sync state
    now_iso = datetime.now().isoformat()
    state["last_sync_date"] = today
    state["last_sync_timestamp"] = now_iso
    state["last_bumped_date"] = today
    state["last_bumped_timestamp"] = now_iso
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
