#!/usr/bin/env python3
"""
P1-4 Live ATS Verification Suite:
Executes live portal applications across Arting Digital, Microland, Ambee,
and 1 live vacancy per major ATS (Greenhouse, Ashby, Lever, Workday).
Enforces strict evidence verification: Submitted (Confirmed) ONLY with
screenshot + confirmation URL/DOM. Every non-confirmation logs a fallback_reason code.
"""

import os
import sys
import json
import time
import sqlite3
from typing import Dict, Any, List

from naukari_pro.modules.career_portals import (
    CareerPortalFiller,
    FillResult,
    load_applicant_profile
)
from naukari_pro.modules.learning.evidence import EvidenceVerifier
from naukari_pro.modules.db import get_db_connection, init_db, record_applied_job
from naukari_pro.modules.scorecard import sync_dual_log

JOBS_TO_TEST = [
    {
        "company": "Arting Digital",
        "title": "Python Developer+AI/ML",
        "url": "https://artingdigital.zohorecruit.in/jobs/Careers/107457000077981057",
        "ats_expected": "Generic Portal (Zoho Recruit)",
        "notes": "Stuck job 1 from 09:15 run"
    },
    {
        "company": "Microland",
        "title": "Sr Engineer - Cloud and Datacenter",
        "url": "https://careers.microland.com/microland/jobview/senior-engineer-cloud-and-datacenter-ent--ind-ka-bengaluru-btpcitrine-ml-2026110210003759",
        "ats_expected": "Generic Portal (Microland)",
        "notes": "Stuck job 2 from 14:31 run"
    },
    {
        "company": "Ambee",
        "title": "Sr Full Stack Engineer",
        "url": "https://getambee.keka.com/careers/jobdetails/168788",
        "ats_expected": "Generic Portal (Keka)",
        "notes": "Stuck job 3 from 14:31 run"
    },
    {
        "company": "GitLab",
        "title": "AI Transformation Owner, CRO",
        "url": "https://job-boards.greenhouse.io/gitlab/jobs/8638232002",
        "ats_expected": "Greenhouse",
        "notes": "Live Greenhouse vacancy"
    },
    {
        "company": "Supabase",
        "title": "AI Platform Engineer",
        "url": "https://jobs.ashbyhq.com/supabase/3b5d54ca-741b-45ac-bd3f-31605a0d3541",
        "ats_expected": "Ashby",
        "notes": "Live Ashby vacancy"
    },
    {
        "company": "Spotify",
        "title": "Engineering Manager - Data Platform",
        "url": "https://jobs.lever.co/spotify/abcc8b41-7553-4054-b5eb-8d3e49e00e25",
        "ats_expected": "Lever",
        "notes": "Live Lever vacancy"
    },
    {
        "company": "NVIDIA",
        "title": "Test Engineer",
        "url": "https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite/job/Singapore-Remote/Test-Engineer_JR2020205",
        "ats_expected": "Workday",
        "notes": "Live Workday tenant"
    }
]

def run_live_tests(db_path: str = "/tmp/test_p1_live.db") -> List[Dict[str, Any]]:
    print("=" * 80)
    print("  🚀 NAUKARIPRO: P1-4 PROVE IT LIVE — ATS PORTAL SUBMISSION SUITE")
    print("=" * 80)

    # Use isolated test DB so prior runs don't prematurely dedup-skip the live probe
    filler = CareerPortalFiller(db_path=db_path)
    # Bypass dedup specifically for this verification run by checking custom DB or allowing re-evaluation
    results = []

    for idx, job in enumerate(JOBS_TO_TEST, 1):
        company = job["company"]
        title = job["title"]
        url = job["url"]
        ats_exp = job["ats_expected"]

        print(f"\n[{idx}/{len(JOBS_TO_TEST)}] Testing {company} — {title}")
        print(f"  Target URL: {url}")
        print(f"  Expected ATS: {ats_exp}")

        t0 = time.time()
        fallback_reason = None
        evidence_file = None
        status = "FAILED"
        fields_filled = []

        try:
            # Execute live fill with auto_submit=True, headless=True
            # Use isolated temporary page runner so dedup on production DB doesn't skip our probe
            detected_ats = filler.detect_ats(url)
            from playwright.sync_api import sync_playwright
            from naukari_pro.session import get_stealth_context

            with sync_playwright() as p:
                ctx = get_stealth_context(p, headless=True)
                page = ctx.pages[0] if ctx.pages else ctx.new_page()
                try:
                    # Let fill_in_playwright execute the full lifecycle
                    # Directly call fill_in_playwright without dedup filter
                    fill_res = filler.fill_in_playwright(page, url, company=company, role=title, auto_submit=True)
                    duration = time.time() - t0

                    is_confirmed = fill_res.success
                    fields_filled = fill_res.fields
                    evidence_file = fill_res.evidence_path

                    if is_confirmed and evidence_file and os.path.exists(evidence_file) and os.path.getsize(evidence_file) >= 1024:
                        status = "Submitted (Confirmed)"
                    elif len(fields_filled) > 0:
                        status = "Form Auto-Filled (Ready for Review)"
                        if "captcha" in (page.content() if hasattr(page, "content") else "").lower():
                            fallback_reason = "CAPTCHA_DETECTED_STOPPED"
                        elif "sign in" in (page.content() if hasattr(page, "content") else "").lower() or "login" in page.url.lower():
                            fallback_reason = "SIGN_IN_WALL_OR_AUTH_BARRIER"
                        else:
                            fallback_reason = "FINAL_SUBMIT_REQUIRES_MANUAL_REVIEW_OR_CODE"
                    else:
                        status = "FAILED"
                        fallback_reason = "NO_FIELDS_FILLED_OR_NAVIGATION_BLOCKED"

                    # Capture screenshot evidence if not already captured
                    if not evidence_file or not os.path.exists(evidence_file):
                        try:
                            clean_id = f"{company}_{title}".replace(" ", "_")[:30]
                            sc_path = f"logs/evidence_p1_{clean_id}.png"
                            os.makedirs("logs", exist_ok=True)
                            page.screenshot(path=sc_path)
                            if os.path.exists(sc_path) and os.path.getsize(sc_path) >= 1024:
                                evidence_file = sc_path
                        except Exception:
                            pass

                except Exception as e_page:
                    duration = time.time() - t0
                    status = "FAILED"
                    fallback_reason = f"EXCEPTION: {str(e_page)[:60]}"
                finally:
                    ctx.close()

        except Exception as e_run:
            duration = time.time() - t0
            status = "FAILED"
            fallback_reason = f"PLAYWRIGHT_START_ERROR: {str(e_run)[:60]}"

        print(f"  • Detected ATS:     {detected_ats}")
        print(f"  • Final Status:     {status}")
        print(f"  • Fields Filled:    {len(fields_filled)} fields: {', '.join(fields_filled[:4])}")
        print(f"  • Fallback Reason:  {fallback_reason or 'NONE (CONFIRMED)'}")
        print(f"  • Evidence Image:   {evidence_file or 'NONE'}")
        print(f"  • Duration:         {duration:.2f}s")

        results.append({
            "company": company,
            "title": title,
            "url": url,
            "ats": detected_ats,
            "status": status,
            "fields_count": len(fields_filled),
            "fallback_reason": fallback_reason,
            "evidence": evidence_file,
            "duration": round(duration, 2)
        })

    print("\n" + "=" * 80)
    print("  SUMMARY TABLE (P1-4 PROVE IT LIVE)")
    print("=" * 80)
    print(f"{'Company':<18} | {'ATS':<14} | {'Status':<32} | {'Fallback Reason':<35} | {'Evidence':<25}")
    print("-" * 135)
    for r in results:
        ev_short = os.path.basename(r["evidence"]) if r["evidence"] else "NONE"
        reason = r["fallback_reason"] or "CONFIRMED"
        print(f"{r['company']:<18} | {r['ats']:<14} | {r['status']:<32} | {reason:<35} | {ev_short:<25}")

    return results

if __name__ == "__main__":
    run_live_tests()
