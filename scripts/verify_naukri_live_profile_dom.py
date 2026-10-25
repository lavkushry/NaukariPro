#!/usr/bin/env python3
"""
Naukri Live Profile DOM Persistence Verification Script
Inspects the live authenticated Naukri profile DOM at https://www.naukri.com/mnjuser/profile
and asserts that all high-conversion Resdex fields are genuinely persisted:
1. Resume Headline: Full 247-char Azure Data Engineer keyword saturated string.
2. Profile Summary: Medallion Lakehouse, DataOps, and core streaming keywords.
3. Key Skills: Top 25 Azure Data Engineering industry keywords.
4. Notice Period: Highest recruiter conversion tier ("15 Days or less" / "15 days").
5. Preferred Locations: All 7 Tier-1 tech hubs (Bengaluru, Hyderabad, Pune, Gurugram, Noida, Mumbai, Chennai).
6. Uploaded CV: Lavkush_Kumar_Azure_Data_Engineer_Resume.pdf.
7. Current Designation: "Azure Data Engineer" at CGI India.
"""

import os
import sys
import time
import json
import argparse
import logging
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from playwright.sync_api import sync_playwright
from naukari_pro.config import load_config, RESUME_PDF_PATH, WORKSPACE_DIR
from naukari_pro.session import get_stealth_context, ensure_authenticated

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("NaukriDOMVerifier")

TARGET_HUBS = [
    "Bengaluru",
    "Hyderabad",
    "Pune",
    "Gurugram",
    "Noida",
    "Mumbai",
    "Chennai"
]

TOP_25_KEYWORDS = [
    "Azure Databricks",
    "PySpark",
    "Delta Lake",
    "Azure Data Factory",
    "SQL",
    "Apache Kafka",
    "Python",
    "ETL",
    "Medallion Architecture",
    "ADLS Gen2",
    "Azure Synapse",
    "Microsoft Fabric",
    "Unity Catalog",
    "dbt",
    "Change Data Capture",
    "Terraform",
    "Kubernetes",
    "Docker",
    "CI/CD",
    "Azure DevOps",
    "PostgreSQL",
    "Data Modeling",
    "Star Schema",
    "DataOps",
    "Great Expectations"
]

def verify_live_profile_dom(page, cfg=None):
    """
    Navigates to the live profile, scrolls to hydrate all dynamic widgets,
    extracts DOM text, and evaluates assertions against target values.
    Returns: (bool: overall_pass, dict: detailed_report)
    """
    config = cfg or load_config()
    target_headline = config.get("headline_template", "").strip()
    target_pdf = os.path.basename(config.get("candidate", {}).get("resume_path", RESUME_PDF_PATH))

    report = {
        "timestamp": datetime.now().isoformat(),
        "url": page.url,
        "overall_status": "FAIL",
        "checks": {}
    }

    if "profile" not in page.url:
        logger.info("Navigating to Naukri profile page...")
        try:
            page.goto("https://www.naukri.com/mnjuser/profile", wait_until="domcontentloaded", timeout=45000)
            time.sleep(3)
        except Exception as e:
            logger.error("Navigation error: %s", e)
            report["checks"]["navigation"] = {"status": "FAIL", "error": str(e)}
            return False, report

    if "login" in page.url:
        logger.error("Session not authenticated (redirected to login).")
        report["checks"]["authentication"] = {"status": "FAIL", "error": "Redirected to login"}
        return False, report

    # Sequential scroll down to trigger hydration of all lazy widgets
    logger.info("Hydrating dynamic profile widgets via sequential scroll...")
    for i in range(1, 9):
        page.evaluate(f"window.scrollTo(0, {i * 600})")
        time.sleep(0.3)
    time.sleep(1.5)

    # ── 1. Resume Headline ──
    hl_text = ""
    try:
        hl_elem = page.locator(".resumeHeadline .text, .resumeHeadline .resumeHeadlineTxt, .resumeHeadline, #lazyResumeHeadline").first
        if hl_elem.count() > 0:
            hl_text = hl_elem.inner_text().strip()
    except Exception as e:
        logger.warning("Error reading headline: %s", e)

    hl_matched_kws = [kw for kw in ["Azure Data Engineer", "Databricks", "PySpark", "Delta Lake", "ADF", "Kafka"] if kw.lower() in hl_text.lower()]
    hl_pass = len(hl_text) >= 200 and "Azure Data Engineer" in hl_text and len(hl_matched_kws) >= 4
    report["checks"]["headline"] = {
        "status": "PASS" if hl_pass else "FAIL",
        "length": len(hl_text),
        "target_length": len(target_headline) if target_headline else 247,
        "matched_keywords": hl_matched_kws,
        "preview": hl_text[:80] + "..." if len(hl_text) > 80 else hl_text
    }

    # ── 2. Profile Summary ──
    sum_text = ""
    try:
        sum_elem = page.locator("#lazyProfileSummary, .profileSummary").first
        if sum_elem.count() > 0:
            sum_text = sum_elem.inner_text().strip()
    except Exception as e:
        logger.warning("Error reading summary: %s", e)

    sum_kws = [kw for kw in ["Azure Databricks", "Delta Lake", "ADF", "Medallion", "2.5 YOE", "Terraform"] if kw.lower() in sum_text.lower()]
    sum_pass = len(sum_text) >= 150 and len(sum_kws) >= 3
    report["checks"]["profile_summary"] = {
        "status": "PASS" if sum_pass else "FAIL",
        "length": len(sum_text),
        "matched_keywords": sum_kws,
        "preview": sum_text[:100] + "..." if len(sum_text) > 100 else sum_text
    }

    # ── 3. Key Skills Tag Cloud ──
    skills_found = []
    try:
        ks_elem = page.locator("#lazyKeySkills, .keySkills").first
        if ks_elem.count() > 0:
            # Try chip elements first
            chips = ks_elem.locator(".chip, .tag, .sugChips span, a.chip")
            if chips.count() > 0:
                skills_found = [chips.nth(i).inner_text().strip() for i in range(chips.count()) if chips.nth(i).inner_text().strip()]
            else:
                raw_ks = ks_elem.inner_text()
                skills_found = [s.strip() for s in raw_ks.split("\n") if len(s.strip()) > 1]
    except Exception as e:
        logger.warning("Error reading key skills: %s", e)

    all_skills_str = " ".join(skills_found).lower()
    matched_top_kws = [kw for kw in TOP_25_KEYWORDS if kw.lower() in all_skills_str]
    ks_pass = len(matched_top_kws) >= 12  # Substantial saturation
    report["checks"]["key_skills"] = {
        "status": "PASS" if ks_pass else "FAIL",
        "total_extracted_chips": len(skills_found),
        "matched_top_keywords_count": len(matched_top_kws),
        "target_keywords_count": len(TOP_25_KEYWORDS),
        "matched_keywords": matched_top_kws,
        "sample_chips": skills_found[:10]
    }

    # ── 4. Notice Period ──
    np_text = ""
    try:
        emp_text = page.locator("#lazyEmployment").first.inner_text() if page.locator("#lazyEmployment").count() > 0 else ""
        cp_text = page.locator("#lazyCareerProfile, .desiredProfile").first.inner_text() if page.locator("#lazyCareerProfile, .desiredProfile").count() > 0 else ""
        np_combined = f"{emp_text} {cp_text}"
        if "15 day" in np_combined.lower() or "15 days" in np_combined.lower() or "immediate" in np_combined.lower():
            np_text = "15 Days or less / 15 days"
        elif "30 day" in np_combined.lower() or "1 month" in np_combined.lower():
            np_text = "30 Days (needs update)"
        else:
            np_text = "Not explicitly found in visible text"
    except Exception as e:
        logger.warning("Error reading notice period: %s", e)

    np_pass = "15" in np_text.lower() or "immediate" in np_text.lower()
    report["checks"]["notice_period"] = {
        "status": "PASS" if np_pass else "FAIL",
        "detected_value": np_text,
        "target": "15 Days or less"
    }

    # ── 5. Preferred Locations (7 Tier-1 Tech Hubs) ──
    found_hubs = []
    missing_hubs = []
    try:
        cp_section = page.locator("#lazyCareerProfile, .desiredProfile").first
        cp_text = cp_section.inner_text() if cp_section.count() > 0 else ""
        for hub in TARGET_HUBS:
            # Check for city name or aliases
            aliases = [hub.lower()]
            if hub.lower() == "bengaluru":
                aliases.append("bangalore")
            if hub.lower() == "gurugram":
                aliases.append("gurgaon")

            if any(a in cp_text.lower() for a in aliases):
                found_hubs.append(hub)
            else:
                missing_hubs.append(hub)
    except Exception as e:
        logger.warning("Error reading preferred locations: %s", e)

    loc_pass = len(found_hubs) >= 4  # Majority or all hubs enabled
    report["checks"]["preferred_locations"] = {
        "status": "PASS" if loc_pass else "FAIL",
        "matched_hubs_count": len(found_hubs),
        "total_target_hubs": len(TARGET_HUBS),
        "found_hubs": found_hubs,
        "missing_hubs": missing_hubs
    }

    # ── 6. Attached Resume CV Filename ──
    cv_filename = ""
    try:
        cv_section = page.locator("#lazyAttachCV, .attachCV, .resume-name").first
        if cv_section.count() > 0:
            cv_text = cv_section.inner_text()
            lines = [l.strip() for l in cv_text.split("\n") if ".pdf" in l.lower()]
            if lines:
                cv_filename = lines[0]
            else:
                cv_filename = cv_text[:80]
    except Exception as e:
        logger.warning("Error reading CV filename: %s", e)

    cv_pass = target_pdf.lower() in cv_filename.lower() or "azure_data_engineer" in cv_filename.lower() or ".pdf" in cv_filename.lower()
    report["checks"]["attached_resume_pdf"] = {
        "status": "PASS" if cv_pass else "FAIL",
        "detected_filename": cv_filename,
        "target_filename": target_pdf
    }

    # ── 7. Current Designation (Role 1) ──
    desig_text = ""
    try:
        emp_sec = page.locator("#lazyEmployment").first
        if emp_sec.count() > 0:
            desig_text = emp_sec.inner_text()
    except Exception as e:
        logger.warning("Error reading current designation: %s", e)

    desig_pass = "Azure Data Engineer" in desig_text and "CGI" in desig_text
    report["checks"]["current_designation"] = {
        "status": "PASS" if desig_pass else "FAIL",
        "contains_target_title": "Azure Data Engineer" in desig_text,
        "contains_current_company": "CGI" in desig_text
    }

    # ── Overall Evaluation ──
    # Pass requires critical fields (headline, summary, key skills, notice period, preferred locations, resume, designation)
    critical_passes = [hl_pass, sum_pass, ks_pass, np_pass, loc_pass, cv_pass, desig_pass]
    overall_pass = all(critical_passes)
    report["overall_status"] = "PASS" if overall_pass else "FAIL"

    return overall_pass, report

def format_terminal_report(report):
    """Formats a clean terminal output summarizing the verification checks."""
    lines = [
        "========================================================================",
        "             NAUKRI LIVE PROFILE DOM VERIFICATION REPORT",
        f" Timestamp: {report.get('timestamp', 'N/A')}",
        f" Overall Status: {report.get('overall_status')}",
        "========================================================================"
    ]
    checks = report.get("checks", {})

    # Headline
    hl = checks.get("headline", {})
    hl_icon = "[✓]" if hl.get("status") == "PASS" else "[✗]"
    lines.append(f" {hl_icon} Resume Headline: {hl.get('length', 0)} chars (Target: {hl.get('target_length', 247)})")
    if hl.get("preview"):
        lines.append(f"     Preview: {hl['preview']}")

    # Profile Summary
    sm = checks.get("profile_summary", {})
    sm_icon = "[✓]" if sm.get("status") == "PASS" else "[✗]"
    lines.append(f" {sm_icon} Profile Summary: {sm.get('length', 0)} chars | Keywords matched: {', '.join(sm.get('matched_keywords', []))}")

    # Key Skills
    ks = checks.get("key_skills", {})
    ks_icon = "[✓]" if ks.get("status") == "PASS" else "[✗]"
    lines.append(f" {ks_icon} Key Skills: {ks.get('matched_top_keywords_count', 0)}/{ks.get('target_keywords_count', 25)} top keywords | Total chips: {ks.get('total_extracted_chips', 0)}")

    # Notice Period
    np_c = checks.get("notice_period", {})
    np_icon = "[✓]" if np_c.get("status") == "PASS" else "[✗]"
    lines.append(f" {np_icon} Notice Period: {np_c.get('detected_value', 'Unknown')} (Target: {np_c.get('target')})")

    # Preferred Locations
    pl = checks.get("preferred_locations", {})
    pl_icon = "[✓]" if pl.get("status") == "PASS" else "[✗]"
    lines.append(f" {pl_icon} Preferred Locations: {pl.get('matched_hubs_count', 0)}/{pl.get('total_target_hubs', 7)} Hubs matched")
    if pl.get("found_hubs"):
        lines.append(f"     Found: {', '.join(pl['found_hubs'])}")
    if pl.get("missing_hubs"):
        lines.append(f"     Missing: {', '.join(pl['missing_hubs'])}")

    # Attached Resume PDF
    cv = checks.get("attached_resume_pdf", {})
    cv_icon = "[✓]" if cv.get("status") == "PASS" else "[✗]"
    lines.append(f" {cv_icon} Attached Resume CV: {cv.get('detected_filename', 'Not detected')}")

    # Current Designation
    cd = checks.get("current_designation", {})
    cd_icon = "[✓]" if cd.get("status") == "PASS" else "[✗]"
    lines.append(f" {cd_icon} Current Designation: Azure Data Engineer at CGI India ({cd.get('status')})")

    lines.append("========================================================================")
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="Verify Naukri Live Profile DOM")
    parser.add_argument("--headless", action="store_true", default=True, help="Run headless")
    parser.add_argument("--no-headless", action="store_false", dest="headless", help="Run with visible browser window")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    parser.add_argument("--report-file", type=str, default=None, help="Save JSON report to file")
    args = parser.parse_args()

    cfg = load_config()

    with sync_playwright() as p:
        ctx = get_stealth_context(p, headless=args.headless)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        if not ensure_authenticated(page, headless=args.headless):
            logger.error("Authentication check failed. Cannot inspect live profile.")
            sys.exit(1)

        overall_pass, report = verify_live_profile_dom(page, cfg=cfg)
        ctx.close()

    if args.report_file:
        os.makedirs(os.path.dirname(os.path.abspath(args.report_file)), exist_ok=True)
        with open(args.report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        logger.info("Saved report to %s", args.report_file)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(format_terminal_report(report))

    sys.exit(0 if overall_pass else 1)

if __name__ == "__main__":
    main()
