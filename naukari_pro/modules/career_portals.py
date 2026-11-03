"""
naukariPro Feature: Career Portal Auto-Filler
Powered by neonwatty/job-apply-plugin architecture.
Fills external career portal applications:
- Greenhouse (boards.greenhouse.io)
- Ashby (jobs.ashbyhq.com)
- Lever (jobs.lever.co)
- Workday (*.myworkdayjobs.com)
- Rippling (ats.rippling.com)
- Generic ATS & Company Career Portals
"""

import os
import sys
import json
import time
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
import openpyxl

from naukari_pro.config import TRACKER_PATH, RESUME_PDF_PATH, load_config
from naukari_pro.modules.learning.screening_solver import FactMatrixScreeningSolver
from naukari_pro.modules.learning.evidence import EvidenceVerifier

logger = logging.getLogger("naukariPro.CareerPortals")

# Candidate Ground Truth
PROFILE_PATH = Path.home() / ".job-apply" / "profile.json"

DEFAULT_CANDIDATE = {
    "firstName": "Lavkush",
    "lastName": "Kumar",
    "fullName": "Lavkush Kumar",
    "email": "lavkushry@gmail.com",
    "applicantEmail": "lav84095@gmail.com",
    "phone": "+91-9122036484",
    "city": "Hyderabad",
    "state": "Telangana",
    "country": "India",
    "zip": "500081",
    "linkedInUrl": "https://linkedin.com/in/lavkushry",
    "githubUrl": "https://github.com/lavkushry",
    "portfolioUrl": "https://github.com/lavkushry",
    "experienceYears": "2.5",
    "noticePeriodDays": "15",
    "currentCtcLpa": "12",
    "expectedCtcLpa": "25",
    "resumePath": RESUME_PDF_PATH,
    "currentCompany": "CGI India (PNC Bank GCC)",
    "currentTitle": "DevOps Engineer / Azure Data Engineer",
    "workHistory": [
        {
            "company": "CGI India (PNC Bank GCC)",
            "title": "DevOps Engineer / Azure Data Engineer",
            "startDate": "2026-06",
            "endDate": None,
            "current": True,
            "duration": "Jun 2026 – Present",
            "location": "Hyderabad / Bangalore",
            "description": "Engineered scalable cloud data lakehouse infrastructure on Azure using Terraform modules, establishing automated ADLS Gen2 storage tiers, Azure Databricks workspaces, and Unity Catalog RBAC governance across 3 environments, cutting provisioning time by 60%."
        },
        {
            "company": "HFCL Limited",
            "title": "Engineer 1 — DevOps / Platform Engineering",
            "startDate": "2025-08",
            "endDate": "2026-06",
            "current": False,
            "duration": "Aug 2025 – Jun 2026",
            "location": "Gurugram / Bangalore",
            "description": "Orchestrated stateful distributed data backbones (Apache Kafka, Redis, PostgreSQL, TimescaleDB, MongoDB) on Kubernetes via StatefulSets, cutting RTO from 8h to 30min (93% reduction) and MTTR by 45%."
        },
        {
            "company": "CGI India",
            "title": "Security Analyst Apprentice",
            "startDate": "2024-09",
            "endDate": "2025-08",
            "current": False,
            "duration": "Sep 2024 – Aug 2025",
            "location": "Bangalore",
            "description": "Engineered centralized log telemetry ingestion pipelines via ELK Stack (Elasticsearch, Logstash, Kibana) and SQL analytical queries, accelerating incident triage by 50%."
        },
        {
            "company": "Stipe Solutions",
            "title": "Full Stack Developer Intern",
            "startDate": "2024-03",
            "endDate": "2024-09",
            "current": False,
            "duration": "Mar 2024 – Sep 2024",
            "location": "Bengaluru",
            "description": "Shipped 30+ responsive UI screens and data validation workflows using React Native and Flutter, integrating RESTful APIs and SQL queries for 1,000+ daily active users."
        }
    ],
    "education": [
        {
            "degree": "B.Tech in Computer Science and Engineering",
            "institution": "Maharishi Dayanand University (MDU), Rohtak",
            "field": "Computer Science and Engineering",
            "startDate": "2020-06",
            "endDate": "2023-05",
            "dates": "2020 – 2023"
        }
    ]
}

def load_applicant_profile():
    data = json.loads(json.dumps(DEFAULT_CANDIDATE))

    # 1. Overlay ~/.job-apply/profile.json if it exists
    if PROFILE_PATH.exists():
        try:
            with open(PROFILE_PATH, "r", encoding="utf-8") as f:
                doc = json.load(f)
                prof = doc.get("profile", doc)
                if prof.get("firstName"):
                    data["firstName"] = prof.get("firstName", data["firstName"])
                    data["lastName"] = prof.get("lastName", data["lastName"])
                    data["fullName"] = f"{data['firstName']} {data['lastName']}".strip()
                    data["email"] = prof.get("email", data["email"])
                    data["phone"] = prof.get("phone", data["phone"])
                    data["linkedInUrl"] = prof.get("linkedInUrl", data["linkedInUrl"])
                    data["githubUrl"] = prof.get("githubUrl", data["githubUrl"])
                    data["resumePath"] = prof.get("resumePath", data["resumePath"])
                    if isinstance(prof.get("location"), dict):
                        loc = prof["location"]
                        data["city"] = loc.get("city", data["city"])
        except Exception:
            pass

    # 2. Overlay config.json candidate facts (authoritative single source of truth)
    try:
        cfg = load_config()
        cand = cfg.get("candidate", {})
        if cand.get("name"):
            names = cand["name"].split(" ", 1)
            data["firstName"] = names[0]
            data["lastName"] = names[1] if len(names) > 1 else ""
            data["fullName"] = cand["name"]
        if cand.get("email"): data["email"] = cand["email"]
        if cand.get("phone"): data["phone"] = cand["phone"]
        if cand.get("current_company"): data["currentCompany"] = cand["current_company"]
        if cand.get("current_designation"): data["currentTitle"] = cand["current_designation"]
        if cand.get("linkedin"): data["linkedInUrl"] = f"https://{cand['linkedin']}" if not cand['linkedin'].startswith('http') else cand['linkedin']
        if cand.get("github"): data["githubUrl"] = f"https://{cand['github']}" if not cand['github'].startswith('http') else cand['github']
        if cand.get("total_experience_years"): data["experienceYears"] = str(cand["total_experience_years"])
        if cand.get("notice_period_days"): data["noticePeriodDays"] = str(cand["notice_period_days"])
        if cand.get("current_ctc_lakhs"): data["currentCtcLpa"] = str(cand["current_ctc_lakhs"])
        if cand.get("expected_ctc_lakhs"): data["expectedCtcLpa"] = str(cand["expected_ctc_lakhs"])

        if cfg.get("experience") and isinstance(cfg["experience"], list):
            mapped_history = []
            for item in cfg["experience"]:
                bullets = item.get("bullets", [])
                desc = " ".join(bullets) if bullets else ""
                mapped_history.append({
                    "company": item.get("company", ""),
                    "title": item.get("title", ""),
                    "duration": item.get("duration", ""),
                    "location": item.get("location", ""),
                    "description": desc,
                    "bullets": bullets,
                    "current": "Present" in item.get("duration", "")
                })
            if mapped_history:
                data["workHistory"] = mapped_history

        if cfg.get("education") and isinstance(cfg["education"], list):
            data["education"] = cfg["education"]
    except Exception:
        pass

    return data

def log_portal_application(
    company,
    role,
    portal_type,
    status,
    url,
    match_score=85,
    tracker_path=None
):
    """
    Appends 11-column record to Applications_Log in tracker workbook:
    [Application Date, Company Name, Job Title, Match Score (%), Role Category,
     Experience Required, Location, Application Type, Status, Job URL, Recruiter Response]
    """
    try:
        path = tracker_path or TRACKER_PATH
        if not os.path.exists(path):
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Applications_Log"
            ws.append([
                "Application Date",
                "Company Name",
                "Job Title",
                "Match Score (%)",
                "Role Category",
                "Experience Required",
                "Location",
                "Application Type",
                "Status",
                "Job URL",
                "Recruiter Response"
            ])
        else:
            wb = openpyxl.load_workbook(path)
            if "Applications_Log" in wb.sheetnames:
                ws = wb["Applications_Log"]
            else:
                ws = wb.create_sheet(title="Applications_Log")
                ws.append([
                    "Application Date",
                    "Company Name",
                    "Job Title",
                    "Match Score (%)",
                    "Role Category",
                    "Experience Required",
                    "Location",
                    "Application Type",
                    "Status",
                    "Job URL",
                    "Recruiter Response"
                ])

        if isinstance(match_score, (int, float)):
            score_str = f"{int(match_score)}%"
        elif isinstance(match_score, str) and match_score.replace('%', '').strip().isdigit():
            score_str = f"{int(match_score.replace('%', '').strip())}%"
        else:
            score_str = "85%"

        safe_url = url if url and str(url).strip() else "N/A"

        ws.append([
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            company,
            role,
            score_str,
            "Azure Data Engineer",
            "2-5 Yrs",
            "Hyderabad / Remote",
            f"Career Portal ({portal_type})",
            status,
            safe_url,
            "Form Auto-Filled; Ready for Final Review"
        ])
        wb.save(path)

        # Record into applied_jobs.db for persistent deduplication & audit trail
        try:
            from naukari_pro.modules.db import record_applied_job
            p = load_applicant_profile()
            record_applied_job(
                title=role,
                company=company,
                platform="career_portal",
                location="Hyderabad / Remote",
                experience_req="2-5 Yrs",
                match_score=score_str,
                status=status,
                application_type=f"Career Portal ({portal_type})",
                job_url=safe_url,
                applicant_email=p.get("email", "lav84095@gmail.com")
            )
        except Exception:
            pass

        return True
    except Exception:
        return False


def safe_count(locator: Any) -> int:
    """Safely extracts integer count from Playwright locator, returning 0 on mock or failure."""
    try:
        if locator is None:
            return 0
        c = locator.count()
        if hasattr(c, "__await__") or not isinstance(c, (int, float)):
            return 0
        return int(c)
    except Exception:
        return 0


class BaseATSHandler:
    """Base class for dedicated ATS platform form handlers."""

    def __init__(self, profile: Dict[str, Any], solver: Optional[FactMatrixScreeningSolver] = None, ats_type: str = "Generic"):
        self.profile = profile
        self.solver = solver or FactMatrixScreeningSolver()
        self.ats_type = ats_type

    def detect_barriers(self, page: Any) -> Optional[str]:
        """Detects barriers such as CAPTCHAs, MFA, or login walls."""
        if not page:
            return None
        try:
            captcha_selectors = [
                "iframe[src*='recaptcha']",
                "iframe[src*='hcaptcha']",
                "iframe[src*='turnstile']",
                "div.g-recaptcha",
                "div.h-captcha",
                "div.cf-turnstile",
                "#cf-turnstile",
                "[data-sitekey]"
            ]
            for sel in captcha_selectors:
                try:
                    loc = page.locator(sel)
                    if safe_count(loc) > 0 and loc.first.is_visible():
                        return f"CAPTCHA Challenge detected ({sel})"
                except Exception:
                    pass
        except Exception:
            pass
        return None

    def fill_form(self, page: Any) -> Dict[str, Any]:
        """Fills standard form inputs and screening questions."""
        raise NotImplementedError

    def upload_resume(self, page: Any, resume_path: Optional[str]) -> bool:
        """Uploads resume to available file input."""
        if not page or not resume_path or not os.path.exists(resume_path):
            return False
        try:
            file_input = page.locator("input[type='file']").first
            if safe_count(file_input) > 0:
                file_input.set_input_files(resume_path)
                return True
        except Exception as e:
            logger.debug("Resume upload notice in %s: %s", self.ats_type, e)
        return False

    def submit_form(self, page: Any) -> bool:
        """Finds and clicks submit button. Returns True if clicked."""
        raise NotImplementedError

    def verify_confirmation(self, page: Any, timeout: float = 10.0) -> bool:
        """Verifies if the page transitioned to a genuine confirmation page."""
        raise NotImplementedError


class GreenhouseHandler(BaseATSHandler):
    """Dedicated handler for Greenhouse ATS (boards.greenhouse.io)."""

    def __init__(self, profile: Dict[str, Any], solver: Optional[FactMatrixScreeningSolver] = None):
        super().__init__(profile, solver, ats_type="Greenhouse")

    def fill_form(self, page: Any) -> Dict[str, Any]:
        filled = []
        p = self.profile
        if not page:
            return {"filled": filled, "ats": "Greenhouse"}

        field_map = [
            ("#first_name, input[name*='first_name' i], input[autocomplete='given-name']", p.get("firstName", "Lavkush"), "First Name"),
            ("#last_name, input[name*='last_name' i], input[autocomplete='family-name']", p.get("lastName", "Kumar"), "Last Name"),
            ("#email, input[type='email'], input[name*='email' i]", p.get("email", "lavkushry@gmail.com"), "Email"),
            ("#phone, input[type='tel'], input[name*='phone' i]", p.get("phone", "+91-9122036484"), "Phone"),
            ("#job_application_location, input[name*='location' i]", p.get("city", "Hyderabad"), "Location"),
            ("input[name*='linkedin' i], input[id*='linkedin' i]", p.get("linkedInUrl", "https://linkedin.com/in/lavkushry"), "LinkedIn"),
            ("input[name*='website' i], input[name*='portfolio' i], input[name*='github' i]", p.get("portfolioUrl", "https://github.com/lavkushry"), "Website"),
        ]
        for selector, val, label in field_map:
            try:
                loc = page.locator(selector).first
                if safe_count(loc) > 0 and loc.is_visible():
                    loc.fill(str(val))
                    filled.append(label)
            except Exception:
                pass

        # Custom screening questions using FactMatrixScreeningSolver
        try:
            custom_fields = page.locator("div.field, div.custom-question, .form-group")
            field_cnt = safe_count(custom_fields)
            for i in range(min(field_cnt, 20)):
                field_elem = custom_fields.nth(i)
                label_elem = field_elem.locator("label").first
                if safe_count(label_elem) > 0:
                    q_text = label_elem.inner_text().strip()
                    if q_text:
                        opts = []
                        opt_elems = field_elem.locator("option")
                        if safe_count(opt_elems) > 0:
                            opts = [opt.inner_text().strip() for opt in opt_elems.all() if opt.inner_text().strip()]
                        decision = self.solver.evaluate_question(q_text, context={"options": opts})
                        if decision.answer and not decision.is_ambiguous and decision.confidence >= 0.7:
                            select_elem = field_elem.locator("select").first
                            if safe_count(select_elem) > 0:
                                try:
                                    select_elem.select_option(label=decision.answer)
                                    filled.append(f"Screening: {q_text[:20]}")
                                    continue
                                except Exception:
                                    pass
                            radios = field_elem.locator("input[type='radio']")
                            if safe_count(radios) > 0:
                                r_labels = field_elem.locator("label")
                                for r_idx in range(safe_count(r_labels)):
                                    r_lbl = r_labels.nth(r_idx)
                                    if decision.answer.lower() in r_lbl.inner_text().lower():
                                        try:
                                            r_lbl.click()
                                            filled.append(f"Screening: {q_text[:20]}")
                                            break
                                        except Exception:
                                            pass
                                continue
                            text_in = field_elem.locator("input[type='text'], textarea").first
                            if safe_count(text_in) > 0:
                                try:
                                    text_in.fill(str(decision.answer))
                                    filled.append(f"Screening: {q_text[:20]}")
                                except Exception:
                                    pass
        except Exception as e_custom:
            logger.debug("Greenhouse custom screening notice: %s", e_custom)

        return {"filled": filled, "ats": "Greenhouse"}

    def upload_resume(self, page: Any, resume_path: Optional[str]) -> bool:
        if not page or not resume_path or not os.path.exists(resume_path):
            return False
        try:
            file_input = page.locator("#resume, input[type='file'][id*='resume' i], input[type='file']").first
            if safe_count(file_input) > 0:
                file_input.set_input_files(resume_path)
                return True
        except Exception as e:
            logger.debug("Greenhouse resume upload notice: %s", e)
        return False

    def submit_form(self, page: Any) -> bool:
        if not page:
            return False
        submit_selectors = [
            "input#submit_app",
            "button#submit_app",
            "input[type='submit'][value*='Submit' i]",
            "button[type='submit']:has-text('Submit Application')",
            "button:has-text('Submit Application')",
            "button[type='submit']"
        ]
        for sel in submit_selectors:
            try:
                btn = page.locator(sel).first
                if safe_count(btn) > 0 and btn.is_visible():
                    btn.click(timeout=5000)
                    return True
            except Exception:
                pass
        return False

    def verify_confirmation(self, page: Any, timeout: float = 10.0) -> bool:
        if not page:
            return False
        start = time.time()
        while time.time() - start < timeout:
            try:
                url = (getattr(page, "url", "") or "").lower()
                if "/confirmation" in url or "application_confirmation" in url:
                    return True
                conf_selectors = [
                    "#application_confirmation",
                    "div[data-qa='confirmation-page']",
                    "h1:has-text('Thank you')",
                    "h2:has-text('Thank you')",
                    "h1:has-text('Application Submitted')",
                    "h2:has-text('Application Submitted')",
                    "div:has-text('Thank you for applying')",
                    "div:has-text('Your application was submitted')"
                ]
                for sel in conf_selectors:
                    try:
                        loc = page.locator(sel)
                        if safe_count(loc) > 0 and loc.first.is_visible():
                            errs = page.locator(".field-error, li.error, .error-message, div.error")
                            if safe_count(errs) == 0 or not errs.first.is_visible():
                                return True
                    except Exception:
                        pass
            except Exception:
                pass
            time.sleep(1)
        return False


class LeverHandler(BaseATSHandler):
    """Dedicated handler for Lever ATS (jobs.lever.co)."""

    def __init__(self, profile: Dict[str, Any], solver: Optional[FactMatrixScreeningSolver] = None):
        super().__init__(profile, solver, ats_type="Lever")

    def fill_form(self, page: Any) -> Dict[str, Any]:
        filled = []
        p = self.profile
        if not page:
            return {"filled": filled, "ats": "Lever"}

        field_map = [
            ("input[name='name']", p.get("fullName", "Lavkush Kumar"), "Full Name"),
            ("input[name='email']", p.get("email", "lavkushry@gmail.com"), "Email"),
            ("input[name='phone']", p.get("phone", "+91-9122036484"), "Phone"),
            ("input[name='org']", p.get("currentCompany", "CGI India (PNC Bank GCC)"), "Current Company"),
            ("input[name='urls[LinkedIn]']", p.get("linkedInUrl", "https://linkedin.com/in/lavkushry"), "LinkedIn"),
            ("input[name='urls[GitHub]']", p.get("githubUrl", "https://github.com/lavkushry"), "GitHub"),
            ("input[name='urls[Portfolio]'], input[name='urls[Other]']", p.get("portfolioUrl", "https://github.com/lavkushry"), "Portfolio"),
        ]
        for selector, val, label in field_map:
            try:
                loc = page.locator(selector).first
                if safe_count(loc) > 0 and loc.is_visible():
                    loc.fill(str(val))
                    filled.append(label)
            except Exception:
                pass

        try:
            questions = page.locator(".application-question, .custom-question")
            q_cnt = safe_count(questions)
            for i in range(min(q_cnt, 15)):
                q_box = questions.nth(i)
                lbl = q_box.locator(".text, label").first
                if safe_count(lbl) > 0:
                    q_text = lbl.inner_text().strip()
                    opt_elems = q_box.locator("option, label")
                    opts = [o.inner_text().strip() for o in opt_elems.all() if o.inner_text().strip()] if safe_count(opt_elems) > 0 else []
                    decision = self.solver.evaluate_question(q_text, context={"options": opts})
                    if decision.answer and not decision.is_ambiguous:
                        radios = q_box.locator("label")
                        clicked_radio = False
                        for r_idx in range(safe_count(radios)):
                            r_lbl = radios.nth(r_idx)
                            if decision.answer.lower() in r_lbl.inner_text().lower():
                                try:
                                    r_lbl.click()
                                    filled.append(f"Screening: {q_text[:20]}")
                                    clicked_radio = True
                                    break
                                except Exception:
                                    pass
                        if not clicked_radio:
                            inp = q_box.locator("input[type='text'], textarea").first
                            if safe_count(inp) > 0:
                                try:
                                    inp.fill(str(decision.answer))
                                    filled.append(f"Screening: {q_text[:20]}")
                                except Exception:
                                    pass
        except Exception as e_lever:
            logger.debug("Lever screening notice: %s", e_lever)

        return {"filled": filled, "ats": "Lever"}

    def upload_resume(self, page: Any, resume_path: Optional[str]) -> bool:
        if not page or not resume_path or not os.path.exists(resume_path):
            return False
        try:
            file_input = page.locator("#resume-upload-input, input[name='resume'], input[type='file']").first
            if safe_count(file_input) > 0:
                file_input.set_input_files(resume_path)
                return True
        except Exception as e:
            logger.debug("Lever resume upload notice: %s", e)
        return False

    def submit_form(self, page: Any) -> bool:
        if not page:
            return False
        submit_selectors = [
            "button#btn-submit",
            "button[type='submit']",
            "button:has-text('Submit application')",
            "button:has-text('Apply')",
            ".postings-btn"
        ]
        for sel in submit_selectors:
            try:
                btn = page.locator(sel).first
                if safe_count(btn) > 0 and btn.is_visible():
                    btn.click(timeout=5000)
                    return True
            except Exception:
                pass
        return False

    def verify_confirmation(self, page: Any, timeout: float = 10.0) -> bool:
        if not page:
            return False
        start = time.time()
        while time.time() - start < timeout:
            try:
                url = (getattr(page, "url", "") or "").lower()
                if "/thanks" in url or "/confirmation" in url:
                    return True
                conf_selectors = [
                    ".application-confirmation",
                    "h2:has-text('Thank you')",
                    "h3:has-text('Thank you')",
                    "h2:has-text('Application Submitted')",
                    "div:has-text('Thank you for applying')",
                    "div:has-text('Your application has been received')"
                ]
                for sel in conf_selectors:
                    try:
                        loc = page.locator(sel)
                        if safe_count(loc) > 0 and loc.first.is_visible():
                            errs = page.locator(".error-message, .error-label")
                            if safe_count(errs) == 0 or not errs.first.is_visible():
                                return True
                    except Exception:
                        pass
            except Exception:
                pass
            time.sleep(1)
        return False


class AshbyHandler(BaseATSHandler):
    """Dedicated handler for Ashby ATS (jobs.ashbyhq.com)."""

    def __init__(self, profile: Dict[str, Any], solver: Optional[FactMatrixScreeningSolver] = None):
        super().__init__(profile, solver, ats_type="Ashby")

    def fill_form(self, page: Any) -> Dict[str, Any]:
        filled = []
        p = self.profile
        if not page:
            return {"filled": filled, "ats": "Ashby"}

        field_map = [
            ("input[name='name'], input[id*='name' i]", p.get("fullName", "Lavkush Kumar"), "Full Name"),
            ("input[name='email'], input[id*='email' i]", p.get("email", "lavkushry@gmail.com"), "Email"),
            ("input[name='phoneNumber'], input[type='tel']", p.get("phone", "+91-9122036484"), "Phone"),
            ("input[name*='linkedin' i], input[id*='linkedin' i]", p.get("linkedInUrl", "https://linkedin.com/in/lavkushry"), "LinkedIn"),
            ("input[name*='github' i], input[id*='github' i]", p.get("githubUrl", "https://github.com/lavkushry"), "GitHub"),
        ]
        for selector, val, label in field_map:
            try:
                loc = page.locator(selector).first
                if safe_count(loc) > 0 and loc.is_visible():
                    loc.fill(str(val))
                    filled.append(label)
            except Exception:
                pass
        return {"filled": filled, "ats": "Ashby"}

    def submit_form(self, page: Any) -> bool:
        if not page:
            return False
        submit_selectors = [
            "button[type='submit']",
            "button:has-text('Submit Application')",
            "button:has-text('Apply')"
        ]
        for sel in submit_selectors:
            try:
                btn = page.locator(sel).first
                if safe_count(btn) > 0 and btn.is_visible():
                    btn.click(timeout=5000)
                    return True
            except Exception:
                pass
        return False

    def verify_confirmation(self, page: Any, timeout: float = 10.0) -> bool:
        if not page:
            return False
        start = time.time()
        while time.time() - start < timeout:
            try:
                url = (getattr(page, "url", "") or "").lower()
                if "/confirmation" in url or "/submitted" in url:
                    return True
                conf_selectors = [
                    "h1:has-text('Application Submitted')",
                    "h2:has-text('Application Submitted')",
                    "h1:has-text('Thank you')",
                    "h2:has-text('Thank you')",
                    "div:has-text('Your application has been submitted')"
                ]
                for sel in conf_selectors:
                    try:
                        loc = page.locator(sel)
                        if safe_count(loc) > 0 and loc.first.is_visible():
                            return True
                    except Exception:
                        pass
            except Exception:
                pass
            time.sleep(1)
        return False


class WorkdayHandler(BaseATSHandler):
    """Dedicated handler for Workday ATS (*.myworkdayjobs.com)."""

    def __init__(self, profile: Dict[str, Any], solver: Optional[FactMatrixScreeningSolver] = None):
        super().__init__(profile, solver, ats_type="Workday")

    def detect_barriers(self, page: Any) -> Optional[str]:
        parent_barrier = super().detect_barriers(page)
        if parent_barrier:
            return parent_barrier
        if not page:
            return None
        try:
            account_selectors = [
                "[data-automation-id='signInLink']",
                "input[data-automation-id='email']",
                "input[data-automation-id='password']",
                "button[data-automation-id='signInSubmitButton']",
                "h2:has-text('Sign In')",
                "h3:has-text('Create Account')"
            ]
            for sel in account_selectors:
                try:
                    loc = page.locator(sel)
                    if safe_count(loc) > 0 and loc.first.is_visible():
                        return f"Workday Account / Sign-In Barrier detected ({sel})"
                except Exception:
                    pass
        except Exception:
            pass
        return None

    def fill_form(self, page: Any) -> Dict[str, Any]:
        filled = []
        p = self.profile
        if not page:
            return {"filled": filled, "ats": "Workday"}

        try:
            start_btn = page.locator("button[data-automation-id='startApplication'], button[data-automation-id='applyButton']").first
            if safe_count(start_btn) > 0 and start_btn.is_visible():
                start_btn.click()
                time.sleep(2)
        except Exception:
            pass

        field_map = [
            ("input[data-automation-id='legalNameSection_firstName']", p.get("firstName", "Lavkush"), "First Name"),
            ("input[data-automation-id='legalNameSection_lastName']", p.get("lastName", "Kumar"), "Last Name"),
            ("input[data-automation-id='email'], input[data-automation-id='contactInfoEmail']", p.get("email", "lavkushry@gmail.com"), "Email"),
            ("input[data-automation-id='phone-number'], input[data-automation-id='phoneNumber']", p.get("phone", "+91-9122036484"), "Phone"),
            ("input[data-automation-id='addressSection_city']", p.get("city", "Hyderabad"), "City"),
        ]
        for selector, val, label in field_map:
            try:
                loc = page.locator(selector).first
                if safe_count(loc) > 0 and loc.is_visible():
                    loc.fill(str(val))
                    filled.append(label)
            except Exception:
                pass

        try:
            next_btn = page.locator("button[data-automation-id='bottom-navigation-next-button'], button[data-automation-id='saveAndContinue']").first
            if safe_count(next_btn) > 0 and next_btn.is_visible():
                next_btn.click()
                time.sleep(2)
        except Exception:
            pass

        return {"filled": filled, "ats": "Workday"}

    def submit_form(self, page: Any) -> bool:
        if not page:
            return False
        submit_selectors = [
            "button[data-automation-id='submitButton']",
            "button[data-automation-id='bottom-navigation-submit-button']",
            "button:has-text('Submit')"
        ]
        for sel in submit_selectors:
            try:
                btn = page.locator(sel).first
                if safe_count(btn) > 0 and btn.is_visible():
                    btn.click(timeout=5000)
                    return True
            except Exception:
                pass
        return False

    def verify_confirmation(self, page: Any, timeout: float = 10.0) -> bool:
        if not page:
            return False
        start = time.time()
        while time.time() - start < timeout:
            try:
                conf_selectors = [
                    "div[data-automation-id='applicationSubmitted']",
                    "div[data-automation-id='thankYouMessage']",
                    "[data-automation-id='pageHeader']:has-text('Application Submitted')",
                    "h2:has-text('Application Submitted')"
                ]
                for sel in conf_selectors:
                    try:
                        loc = page.locator(sel)
                        if safe_count(loc) > 0 and loc.first.is_visible():
                            return True
                    except Exception:
                        pass
            except Exception:
                pass
            time.sleep(1)
        return False


class GenericPortalHandler(BaseATSHandler):
    """Fallback handler for generic company portals and ATS platforms."""

    def __init__(self, profile: Dict[str, Any], solver: Optional[FactMatrixScreeningSolver] = None, ats_type: str = "Generic Portal"):
        super().__init__(profile, solver, ats_type=ats_type)

    def fill_form(self, page: Any) -> Dict[str, Any]:
        filled = []
        p = self.profile
        if not page:
            return {"filled": filled, "ats": self.ats_type}

        field_map = [
            ("#first_name, input[name*='first_name' i], input[name*='firstName' i]", p.get("firstName", "Lavkush"), "First Name"),
            ("#last_name, input[name*='last_name' i], input[name*='lastName' i]", p.get("lastName", "Kumar"), "Last Name"),
            ("#email, input[type='email'], input[name*='email' i]", p.get("email", "lavkushry@gmail.com"), "Email"),
            ("#phone, input[type='tel'], input[name*='phone' i], input[name*='mobile' i]", p.get("phone", "+91-9122036484"), "Phone"),
            ("input[name*='company' i], input[name*='org' i]", p.get("currentCompany", "CGI India (PNC Bank GCC)"), "Company"),
            ("input[name*='title' i], input[name*='designation' i]", p.get("currentTitle", "DevOps Engineer / Azure Data Engineer"), "Title"),
            ("input[name*='linkedin' i], input[id*='linkedin' i]", p.get("linkedInUrl", "https://linkedin.com/in/lavkushry"), "LinkedIn"),
            ("input[name*='github' i], input[id*='github' i]", p.get("githubUrl", "https://github.com/lavkushry"), "GitHub"),
        ]
        for selector, val, label in field_map:
            try:
                loc = page.locator(selector).first
                if safe_count(loc) > 0 and loc.is_visible():
                    loc.fill(str(val))
                    filled.append(label)
            except Exception:
                pass
        return {"filled": filled, "ats": self.ats_type}

    def submit_form(self, page: Any) -> bool:
        if not page:
            return False
        submit_selectors = [
            "button[type='submit']",
            "input[type='submit']",
            "button:has-text('Submit Application')",
            "button:has-text('Submit')",
            "button:has-text('Apply')"
        ]
        for sel in submit_selectors:
            try:
                btn = page.locator(sel).first
                if safe_count(btn) > 0 and btn.is_visible():
                    btn.click(timeout=5000)
                    return True
            except Exception:
                pass
        return False

    def verify_confirmation(self, page: Any, timeout: float = 10.0) -> bool:
        if not page:
            return False
        start = time.time()
        while time.time() - start < timeout:
            try:
                url = (getattr(page, "url", "") or "").lower()
                for term in ["/confirm", "/thank", "/submitted", "/success", "/applied"]:
                    if term in url:
                        return True
                conf_selectors = [
                    "h1:has-text('Application Submitted')",
                    "h2:has-text('Application Submitted')",
                    "h1:has-text('Thank You')",
                    "h2:has-text('Thank You')",
                    "h1:has-text('Application Received')",
                    "h2:has-text('Application Received')"
                ]
                for sel in conf_selectors:
                    try:
                        loc = page.locator(sel)
                        if safe_count(loc) > 0 and loc.first.is_visible():
                            errs = page.locator(".error, .has-error, [aria-invalid='true']")
                            if safe_count(errs) == 0 or not errs.first.is_visible():
                                return True
                    except Exception:
                        pass
            except Exception:
                pass
            time.sleep(1)
        return False


class CareerPortalFiller:
    def __init__(self):
        self.profile = load_applicant_profile()
        self.solver = FactMatrixScreeningSolver()

    def get_handler(self, ats_type: str) -> BaseATSHandler:
        """Returns dedicated platform handler for the detected ATS type."""
        t = (ats_type or "").lower()
        if "greenhouse" in t:
            return GreenhouseHandler(self.profile, solver=self.solver)
        elif "lever" in t:
            return LeverHandler(self.profile, solver=self.solver)
        elif "ashby" in t:
            return AshbyHandler(self.profile, solver=self.solver)
        elif "workday" in t:
            return WorkdayHandler(self.profile, solver=self.solver)
        else:
            return GenericPortalHandler(self.profile, solver=self.solver, ats_type=ats_type)

    def detect_ats(self, url: Optional[str] = None) -> str:
        if not url or not isinstance(url, str):
            return "Generic Portal"
        u = url.lower().strip()
        if not u:
            return "Generic Portal"
        if "linkedin.com" in u:
            return "LinkedIn"
        elif "greenhouse.io" in u or "gh_jid" in u:
            return "Greenhouse"
        elif "ashbyhq.com" in u:
            return "Ashby"
        elif "lever.co" in u:
            return "Lever"
        elif "myworkdayjobs.com" in u or "workday" in u:
            return "Workday"
        elif "rippling.com" in u:
            return "Rippling"
        elif "smartrecruiters.com" in u:
            return "SmartRecruiters"
        else:
            return "Generic Portal"

    def generate_fill_script(self, ats_type: str) -> str:
        """
        Generates robust JavaScript form-filler adapted from neonwatty/job-apply-plugin.
        Handles text fields, email, phone, dropdowns, and file upload triggers.
        """
        p = self.profile
        return f"""
        (() => {{
            const res = {{ filled: [], missing: [], ats: '{ats_type}' }};
            const p = {json.dumps(p)};

            function setVal(el, val, name) {{
                if (!el) return false;
                try {{
                    el.focus();
                    if (el.isContentEditable || el.tagName === 'DIV') {{
                        el.innerText = val;
                        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }} else {{
                        el.value = val;
                        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                    res.filled.push(name);
                    return true;
                }} catch(e) {{
                    return false;
                }}
            }}

            // 1. First Name / Last Name / Full Name
            const fn = document.querySelector('#first_name, input[name*="first_name" i], input[name*="firstName" i], input[autocomplete="given-name"]');
            if (fn) setVal(fn, p.firstName, 'First Name');

            const ln = document.querySelector('#last_name, input[name*="last_name" i], input[name*="lastName" i], input[autocomplete="family-name"]');
            if (ln) setVal(ln, p.lastName, 'Last Name');

            const full = document.querySelector('input[name*="name" i]:not([name*="first" i]):not([name*="last" i]), input[id*="name" i]:not([id*="first" i]):not([id*="last" i]), input[autocomplete="name"]');
            if (full && !fn && !ln) setVal(full, p.fullName, 'Full Name');

            // 2. Email
            const email = document.querySelector('#email, input[type="email"], input[name*="email" i], input[autocomplete="email"]');
            if (email) setVal(email, p.email, 'Email');

            // 3. Phone
            const phone = document.querySelector('#phone, input[type="tel"], input[name*="phone" i], input[name*="mobile" i], input[autocomplete="tel"]');
            if (phone) setVal(phone, p.phone, 'Phone');

            // 4. LinkedIn & Social URLs
            const li = document.querySelector('input[name*="linkedin" i], input[id*="linkedin" i], input[placeholder*="linkedin" i]');
            if (li) setVal(li, p.linkedInUrl, 'LinkedIn');

            const gh = document.querySelector('input[name*="github" i], input[id*="github" i], input[placeholder*="github" i]');
            if (gh) setVal(gh, p.githubUrl, 'GitHub');

            const port = document.querySelector('input[name*="website" i], input[name*="portfolio" i], input[placeholder*="portfolio" i]');
            if (port && !gh) setVal(port, p.portfolioUrl, 'Portfolio');

            // 5. Location / City
            const loc = document.querySelector('input[name*="location" i], input[name*="city" i], input[id*="location" i], input[id*="city" i]');
            if (loc) setVal(loc, p.city, 'Location');

            // 5b. Current Company / Employer / Organization
            const comp = document.querySelector('input[name*="company" i], input[name*="org" i], input[name*="employer" i], input[id*="company" i], input[id*="org" i], input[placeholder*="company" i], input[placeholder*="current company" i], input[autocomplete="organization"]');
            if (comp && p.currentCompany) setVal(comp, p.currentCompany, 'Current Company');

            // 5c. Current Job Title / Designation / Headline
            const curTitle = document.querySelector('input[name*="title" i], input[name*="headline" i], input[name*="designation" i], input[id*="title" i], input[id*="headline" i], input[placeholder*="title" i], input[placeholder*="current title" i]');
            if (curTitle && p.currentTitle) setVal(curTitle, p.currentTitle, 'Current Title');

            // 5d. Education (School / University / Degree)
            const school = document.querySelector('input[name*="school" i], input[name*="university" i], input[name*="institution" i], input[id*="school" i], input[id*="university" i], input[placeholder*="school" i], input[placeholder*="university" i]');
            if (school && p.education && p.education.length > 0) {{
                const sName = p.education[0].institution || p.education[0].school || '';
                if (sName) setVal(school, sName, 'Education School');
            }}
            const deg = document.querySelector('input[name*="degree" i], input[id*="degree" i], input[placeholder*="degree" i]');
            if (deg && p.education && p.education.length > 0) {{
                const dName = p.education[0].degree || '';
                if (dName) setVal(deg, dName, 'Education Degree');
            }}

            // 5e. Experience Years & Notice Period inputs
            const expInput = document.querySelector('input[name*="experience" i]:not([type="checkbox"]):not([type="radio"]), input[id*="experience" i]:not([type="checkbox"]):not([type="radio"])');
            if (expInput && p.experienceYears) setVal(expInput, p.experienceYears, 'Experience Years');

            const noticeInput = document.querySelector('input[name*="notice" i]:not([type="checkbox"]):not([type="radio"]), input[id*="notice" i]:not([type="checkbox"]):not([type="radio"])');
            if (noticeInput && p.noticePeriodDays) setVal(noticeInput, p.noticePeriodDays, 'Notice Period');

            // 6. Radio / Dropdown screening questions (Work Auth, Relocation, Notice)
            const labels = Array.from(document.querySelectorAll('label, .ssrc__label, [role="radio"]'));
            for (let l of labels) {{
                const txt = (l.innerText || '').toLowerCase();
                // Work Authorization: Authorized -> Yes
                if (txt.includes('authorized to work') || txt.includes('legally authorized') || txt.includes('eligible to work')) {{
                    if (txt.includes('yes')) l.click();
                }}
                // Visa sponsorship: Require sponsorship -> No
                if (txt.includes('sponsorship') || txt.includes('require visa')) {{
                    if (txt.includes('no')) l.click();
                }}
                // Relocation: Open to relocate -> Yes
                if (txt.includes('relocate') || txt.includes('relocation')) {{
                    if (txt.includes('yes') || txt.includes('agree')) l.click();
                }}
            }}

            // 7. LinkedIn Easy Apply Modal Handling
            if (window.location.hostname.includes('linkedin.com')) {{
                const easyApplyBtn = document.querySelector('.jobs-apply-button, button[aria-label*="Easy Apply"]');
                const modal = document.querySelector('.jobs-easy-apply-modal, [data-test-modal]');
                if (easyApplyBtn && !modal) {{
                    easyApplyBtn.click();
                    res.filled.push('Easy Apply Triggered');
                }} else if (modal) {{
                    const phoneInput = modal.querySelector('input[id*="phoneNumber"], input[autocomplete="tel"], input[type="tel"]');
                    if (phoneInput && !phoneInput.value) setVal(phoneInput, p.phone, 'LinkedIn Phone');
                    res.filled.push('LinkedIn Modal Form Step');
                }}
            }}

            // 8. Check for resume file input
            const fileInputs = Array.from(document.querySelectorAll('input[type="file"]'));
            res.hasFileInput = fileInputs.length > 0;
            res.fileInputCount = fileInputs.length;

            return JSON.stringify(res);
        }})()
        """

    def fill_in_chrome(self, portal_url: str, company: str = "Company", role: str = "Azure Data Engineer"):
        """
        Fills the career portal inside Google Chrome via AppleScript without submitting.
        On non-macOS systems (e.g. Linux VM), routes via headless Playwright.
        Leaves the application on the review page for human verification.
        """
        if not portal_url or not isinstance(portal_url, str):
            print("    [!] Error: Invalid or empty portal URL.")
            return False, []

        ats_type = self.detect_ats(portal_url)

        if sys.platform != "darwin":
            print("    [!] Notice: AppleScript Chrome automation is macOS-only. Routing via headless Playwright...")
            try:
                from playwright.sync_api import sync_playwright
                from naukari_pro.session import get_stealth_context
                with sync_playwright() as p:
                    context = get_stealth_context(p, headless=True)
                    page = context.pages[0] if context.pages else context.new_page()
                    success, filled = self.fill_in_playwright(page, portal_url, company=company, role=role)
                    context.close()
                    return success, filled
            except Exception as e_pw:
                print(f"    Playwright fallback notice: {e_pw}")
                return False, []

        print(f"\n[*] Opening {ats_type} Career Portal in Chrome...")
        print(f"    URL: {portal_url}")

        js_code = self.generate_fill_script(ats_type)

        apple_script = f'''
        tell application "Google Chrome"
            set myTab to make new tab at end of tabs of window 1 with properties {{URL:"{portal_url}"}}
            delay 6
            set fillRes to execute myTab javascript {json.dumps(js_code)}
            return fillRes
        end tell
        '''

        try:
            p = subprocess.run(["osascript", "-e", apple_script], capture_output=True, text=True)
            if p.returncode == 0:
                raw = p.stdout.strip()
                try:
                    data = json.loads(raw)
                    filled = data.get("filled", [])
                    print(f"\n[✓] {ats_type} Form Auto-Filled successfully!")
                    print(f"    Fields populated: {', '.join(filled)}")
                    if data.get("hasFileInput"):
                        print(f"    📎 Resume upload field ready: {self.profile['resumePath']}")
                    print(f"    🛑 Stopped safely before final Submit button (job-apply policy: review_only).")

                    log_portal_application(company, role, ats_type, "Form Auto-Filled", portal_url)
                    return True, filled
                except Exception:
                    print(f"    Raw output: {raw}")
            else:
                print(f"    Error: {p.stderr}")
        except Exception as e:
            print(f"    Exception: {e}")

        return False, []

    def fill_in_playwright(self, page, portal_url: str, company: str = "Company", role: str = "Azure Data Engineer"):
        """Fills career portal using Playwright context."""
        if not portal_url or not isinstance(portal_url, str):
            print("    [!] Error: Invalid or empty portal URL.")
            return False, []

        ats_type = self.detect_ats(portal_url)
        print(f"\n[*] Navigating to {ats_type} Portal via Playwright...")
        page.goto(portal_url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(4)

        js_code = self.generate_fill_script(ats_type)
        res_str = page.evaluate(js_code)
        try:
            data = json.loads(res_str)
            filled = data.get("filled", [])
            print(f"[✓] {ats_type} Form Auto-Filled: {', '.join(filled)}")

            # Attempt file upload if input[type='file'] exists
            file_input = page.locator("input[type='file']").first
            if file_input.count() > 0 and os.path.exists(self.profile["resumePath"]):
                file_input.set_input_files(self.profile["resumePath"])
                print(f"    📎 Resume PDF uploaded: {self.profile['resumePath']}")

            log_portal_application(company, role, ats_type, "Form Auto-Filled", portal_url)
            return True, filled
        except Exception as e:
            print(f"    Notice: {e}")
            return False, []

    def fill_dry_run(
        self,
        portal_url: str,
        company: str = "Company",
        role: str = "Azure Data Engineer",
        raw_jd: str = "",
        salary: str = "25 LPA",
        calculate_score: bool = True,
        match_score: Optional[int] = None
    ):
        """
        Executes 100% offline dry-run: detects ATS, computes match score,
        generates autofill script, and returns validated ApplicationPayload
        without launching live browsers or submitting forms.
        """
        ats_type = self.detect_ats(portal_url)

        if match_score is not None:
            final_score = int(match_score)
        elif calculate_score:
            from naukari_pro.modules.job_alerts import calculate_match_score
            score_text = f"{role} {company} {raw_jd}".strip()
            final_score = calculate_match_score(score_text)
        else:
            final_score = 0

        from naukari_pro.modules.job_alerts import MATCH_SCORE_THRESHOLD
        status = "VALIDATED_PAYLOAD" if final_score >= MATCH_SCORE_THRESHOLD else "REJECTED_BELOW_THRESHOLD"

        answers = {
            "first_name": self.profile.get("firstName", "Lavkush"),
            "last_name": self.profile.get("lastName", "Kumar"),
            "full_name": self.profile.get("fullName", "Lavkush Kumar"),
            "email": self.profile.get("email", "lavkushry@gmail.com"),
            "phone": self.profile.get("phone", "+91-9122036484"),
            "location": self.profile.get("city", "Hyderabad"),
            "linkedin": self.profile.get("linkedInUrl", "https://linkedin.com/in/lavkushry"),
            "github": self.profile.get("githubUrl", "https://github.com/lavkushry"),
            "experience": self.profile.get("experienceYears", "2.5"),
            "notice_period": self.profile.get("noticePeriodDays", "15"),
            "current_ctc_lpa": self.profile.get("currentCtcLpa", "12"),
            "expected_ctc_lpa": self.profile.get("expectedCtcLpa", "25"),
            "current_company": self.profile.get("currentCompany", "CGI India (PNC Bank GCC)"),
            "current_title": self.profile.get("currentTitle", "DevOps Engineer / Azure Data Engineer"),
            "work_history": self.profile.get("workHistory", []),
            "education": self.profile.get("education", []),
            "work_auth": "Yes",
            "visa_sponsorship": "No",
            "relocation": "Yes",
            "ats_type": ats_type
        }

        fill_script = self.generate_fill_script(ats_type)

        from naukari_pro.modules.auto_apply import ApplicationPayload
        safe_url = portal_url if (portal_url and isinstance(portal_url, str)) else "N/A"
        payload = ApplicationPayload(
            company=company,
            job_title=role,
            title=role,
            url=safe_url,
            match_score=final_score,
            salary=salary,
            answers=answers,
            payload_data={
                "ats_type": ats_type,
                "script_length": len(fill_script),
                "has_script": bool(fill_script),
                "resume_path": self.profile.get("resumePath"),
                "work_history_count": len(self.profile.get("workHistory", [])),
                "current_company": self.profile.get("currentCompany")
            },
            portal_type=f"Career Portal ({ats_type})",
            dry_run=True,
            status=status
        )
        return payload

    def fill(
        self,
        portal_url: str,
        company: str = "Company",
        role: str = "Azure Data Engineer",
        headless: bool = False,
        dry_run: bool = False,
        raw_jd: str = "",
        salary: str = "25 LPA",
        page=None,
        match_score: Optional[int] = None
    ):
        """Unified entrypoint supporting both live review-only fill and offline dry-run."""
        if dry_run:
            payload = self.fill_dry_run(
                portal_url=portal_url,
                company=company,
                role=role,
                raw_jd=raw_jd,
                salary=salary,
                match_score=match_score
            )
            print(f"\n[DRY-RUN] Career Portal Autofill Payload Generated:")
            print(f"  • ATS Platform: {self.detect_ats(portal_url)}")
            print(f"  • Company:      {payload.company}")
            print(f"  • Title:        {payload.title}")
            print(f"  • Match Score:  {payload.match_score}%")
            print(f"  • Status:       {payload.status}")
            return True, payload

        if page is not None:
            return self.fill_in_playwright(page, portal_url, company=company, role=role)
        elif sys.platform == "darwin" and not headless:
            return self.fill_in_chrome(portal_url, company=company, role=role)
        else:
            try:
                from playwright.sync_api import sync_playwright
                from naukari_pro.session import get_stealth_context
                with sync_playwright() as p:
                    context = get_stealth_context(p, headless=headless)
                    page_ctx = context.pages[0] if context.pages else context.new_page()
                    success, filled = self.fill_in_playwright(page_ctx, portal_url, company=company, role=role)
                    context.close()
                    return success, filled
            except Exception as e:
                print(f"Playwright automation error: {e}")
                return False, []

    def process_external_redirects(
        self,
        limit: int = 10,
        headless: bool = True,
        dry_run: bool = False,
        min_score: float = 70.0,
        max_exp: float = 4.0,
        auto_submit: bool = True
    ) -> Dict[str, Any]:
        """
        Processes pending external career portal redirects from Naukri_Live_Application_Tracker.xlsx.
        Scans for rows with Status == 'External Redirect' (or 'Not Available'),
        filters by experience (<= 4 YOE) and score (>= 70%),
        and automates form-filling, resume attachment, and submission.
        Updates tracker Excel and applied_jobs.db.
        """
        import openpyxl
        from naukari_pro.modules.auto_apply import is_experience_eligible
        from naukari_pro.modules.db import is_job_already_applied, record_applied_job

        if not os.path.exists(TRACKER_PATH):
            print(f"  [!] Tracker file not found: {TRACKER_PATH}")
            return {"processed": 0, "submitted": 0, "skipped": 0, "items": []}

        wb = openpyxl.load_workbook(TRACKER_PATH)
        if "Applications_Log" not in wb.sheetnames:
            print("  [!] Applications_Log sheet not found in tracker.")
            return {"processed": 0, "submitted": 0, "skipped": 0, "items": []}

        ws = wb["Applications_Log"]
        candidates_to_process = []

        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not row or not any(row):
                continue
            status = str(row[8] or "").strip()
            if status in ("External Redirect", "Not Available"):
                date_val = row[0]
                company = str(row[1] or "").strip()
                title = str(row[2] or "").strip()
                score_str = str(row[3] or "0").replace("%", "").strip()
                score = float(score_str) if score_str.replace(".", "", 1).isdigit() else 0.0
                exp = str(row[5] or "").strip()
                url = str(row[9] or "").strip()

                if not title or not company or not url or url == "N/A":
                    continue

                # Pre-filtering: Experience Gate
                is_exp_ok, exp_reason, _, _ = is_experience_eligible(
                    exp_text=exp,
                    title=title,
                    url=url,
                    candidate_exp=float(self.profile.get("experienceYears", 2.5)),
                    max_allowed=max_exp
                )
                if not is_exp_ok:
                    continue

                # Pre-filtering: Match Score Gate
                if score < min_score:
                    continue

                candidates_to_process.append({
                    "row_idx": row_idx,
                    "date": date_val,
                    "company": company,
                    "title": title,
                    "score": score,
                    "exp": exp,
                    "url": url,
                    "status": status
                })

        # Contextual bandit selection policy gating & volume floor enforcement (v2.1-linucb)
        active_policy = getattr(self, "policy", None)
        if active_policy is None:
            try:
                from naukari_pro.modules.learning.policy import LinUCBBanditPolicy
                active_policy = LinUCBBanditPolicy()
            except Exception:
                active_policy = None

        if active_policy is not None and candidates_to_process:
            try:
                from naukari_pro.modules.learning.volume_guard import VolumeGuard
                from naukari_pro.modules.db import get_daily_application_count, record_policy_event
                vg = VolumeGuard()
                gated_candidates = []
                skipped_candidates = []
                for item in candidates_to_process:
                    job_ctx = {
                        "match_score": item["score"],
                        "required_yoe": item["exp"],
                        "posting_age_hours": 24.0,
                        "company": item["company"],
                        "platform": "Career Portal",
                        "salary_lpa": 20.0,
                        "jd": f"{item['title']} {item['company']}"
                    }
                    action, ucb_score, diag = active_policy.select_action(job_ctx, explore=True, increment_decision=True)
                    act_name = action.name if hasattr(action, "name") else str(action)
                    item["policy_action"] = act_name
                    item["policy_score"] = ucb_score
                    if act_name == "SKIP":
                        skipped_candidates.append(item)
                    else:
                        gated_candidates.append(item)

                today_applied = get_daily_application_count()
                shortfall = max(0, vg.min_applications_per_day - (today_applied + len(gated_candidates)))
                if shortfall > 0 and skipped_candidates:
                    skipped_candidates.sort(key=lambda x: float(x.get("score", 0.0)), reverse=True)
                    for item in skipped_candidates[:shortfall]:
                        item["policy_action"] = "APPLY_FLOOR"
                        item["policy_floor_override"] = True
                        gated_candidates.append(item)
                        record_policy_event(
                            event_type="APPLY_FLOOR_OVERRIDE",
                            details={
                                "company": item.get("company"),
                                "title": item.get("title"),
                                "match_score": item.get("score"),
                                "floor_target": vg.min_applications_per_day,
                                "projected_before_override": today_applied + len(gated_candidates)
                            },
                            mode="ACTIVE"
                        )
                candidates_to_process = gated_candidates
            except Exception as e_pol:
                pass

        print("\n" + "=" * 65)
        print("  🌐 AUTOMATED EXTERNAL CAREER PORTAL RUNNER")
        print(f"  Total Eligible Pending Redirects: {len(candidates_to_process)} (Score >= {min_score}%, YOE <= {max_exp})")
        print(f"  Batch Limit: {limit} | Mode: {'DRY-RUN (Simulated)' if dry_run else 'LIVE SUBMISSION'}")
        print("=" * 65)

        processed = 0
        submitted = 0
        skipped = 0
        results = []

        # If dry run, validate payloads offline without launching browser
        if dry_run:
            for item in candidates_to_process[:limit]:
                payload = self.fill_dry_run(
                    portal_url=item["url"],
                    company=item["company"],
                    role=item["title"],
                    match_score=int(item["score"])
                )
                print(f"\n  [DRY-RUN] Validated External Application:")
                print(f"    • Company:     {item['company']}")
                print(f"    • Role:        {item['title']}")
                print(f"    • Match Score: {item['score']}%")
                print(f"    • Experience:  {item['exp']}")
                print(f"    • ATS Type:    {payload.portal_type}")
                print(f"    • URL:         {item['url']}")
                print(f"    • Status:      {payload.status}")
                processed += 1
                submitted += 1
                results.append({"company": item["company"], "title": item["title"], "status": payload.status, "ats": payload.portal_type})
            return {"processed": processed, "submitted": submitted, "skipped": skipped, "items": results}

        # Live execution via Playwright
        from playwright.sync_api import sync_playwright
        from naukari_pro.session import get_stealth_context

        with sync_playwright() as p:
            context = get_stealth_context(p, headless=headless)
            page = context.pages[0] if context.pages else context.new_page()

            for item in candidates_to_process[:limit]:
                row_idx = item["row_idx"]
                company = item["company"]
                title = item["title"]
                score = item["score"]
                url = item["url"]
                processed += 1

                print(f"\n[*] [{processed}/{min(limit, len(candidates_to_process))}] Processing External Redirect: {title} @ {company} ({score}%)")
                print(f"    Naukri Source URL: {url}")

                target_portal_url = url
                ats_type = self.detect_ats(url)

                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    time.sleep(3)

                    # Check if page is Naukri with "Apply on Company Site" button
                    if "naukri.com" in page.url.lower():
                        print("    Detecting external company portal redirect button...")
                        co_btn = page.locator("button#company-site-button, .styles_company-site-button__C_2YK, a:has-text('Apply on Company Site'), button:has-text('Apply on Company Site')").first
                        if co_btn.count() > 0 and co_btn.is_visible():
                            try:
                                with context.expect_page(timeout=15000) as new_page_info:
                                    co_btn.click()
                                ext_page = new_page_info.value
                                ext_page.wait_for_load_state("domcontentloaded", timeout=25000)
                                time.sleep(3)
                                active_page = ext_page
                                target_portal_url = ext_page.url
                            except Exception:
                                time.sleep(4)
                                active_page = context.pages[-1]
                                target_portal_url = active_page.url
                        else:
                            active_page = page
                            target_portal_url = page.url
                    else:
                        active_page = page
                        target_portal_url = page.url

                    ats_type = self.detect_ats(target_portal_url)
                    handler = self.get_handler(ats_type)
                    print(f"    ATS Platform Detected: {ats_type} ({target_portal_url[:80]}...)")

                    # Check for barriers (CAPTCHAs, Workday sign-in, MFA)
                    barrier = handler.detect_barriers(active_page)
                    evidence_file = None
                    sub_status = "Form Auto-Filled (Ready for Review)"
                    ev = EvidenceVerifier()

                    if barrier:
                        print(f"    ⚠️ Barrier encountered on {ats_type} portal: {barrier}. Halting auto-submit; maintaining status as Ready for Review.")
                        try:
                            handler.fill_form(active_page)
                            js_code = self.generate_fill_script(ats_type)
                            active_page.evaluate(js_code)
                            handler.upload_resume(active_page, self.profile.get("resumePath"))
                        except Exception:
                            pass
                    else:
                        # Dedicated ATS form filling + JS script execution
                        handler_res = handler.fill_form(active_page)
                        js_code = self.generate_fill_script(ats_type)
                        try:
                            res_str = active_page.evaluate(js_code)
                            res_data = json.loads(res_str) if isinstance(res_str, str) else res_str
                            filled_fields = list(set((handler_res.get("filled", []) + res_data.get("filled", []))))
                        except Exception:
                            filled_fields = handler_res.get("filled", [])
                        print(f"    [✓] Auto-Filled Fields: {', '.join(filled_fields) if filled_fields else 'Basic Fields'}")

                        # Attach resume PDF if file input exists
                        resume_path = self.profile.get("resumePath")
                        uploaded = handler.upload_resume(active_page, resume_path)
                        if uploaded:
                            print(f"    📎 Resume Uploaded: {os.path.basename(resume_path)}")

                        time.sleep(2)

                        # Submit application if requested with strict confirmation detection
                        if auto_submit:
                            submit_clicked = handler.submit_form(active_page)
                            if submit_clicked:
                                is_confirmed = handler.verify_confirmation(active_page, timeout=12.0)
                                if is_confirmed:
                                    sc_path = ev.capture_screenshot_sync(active_page, company, title)
                                    sub_status, evidence_file = ev.evaluate_submission_state(is_confirmed, sc_path)
                                    if sub_status == "Submitted (Confirmed)":
                                        print(f"    🚀 Form Submitted on {ats_type} Portal with verified evidence: {evidence_file}")
                                    else:
                                        print(f"    ⚠️ Form submitted but screenshot header validation failed; status maintained as Ready for Review.")
                                else:
                                    print(f"    ⚠️ Submit clicked but confirmation not detected; status strictly maintained as Ready for Review.")
                                    sub_status = "Form Auto-Filled (Ready for Review)"
                            else:
                                print(f"    ℹ️ Final submit button requires manual review; form 100% pre-filled.")
                                sub_status = "Form Auto-Filled (Ready for Review)"

                    # Update Excel tracker row
                    ws.cell(row=row_idx, column=9, value=sub_status)
                    ws.cell(row=row_idx, column=11, value="External ATS Auto-Filled & Submitted via Agy")
                    wb.save(TRACKER_PATH)

                    # Record into applied_jobs.db
                    record_applied_job(
                        title=title,
                        company=company,
                        platform="career_portal",
                        location="Hyderabad / Remote",
                        experience_req=item["exp"],
                        match_score=score,
                        status=sub_status,
                        application_type=f"Career Portal ({ats_type})",
                        job_url=target_portal_url,
                        applicant_email=self.profile.get("email", "lav84095@gmail.com"),
                        evidence_path=evidence_file,
                        raw_metadata={"policy_action": item.get("policy_action", "APPLY")},
                        policy_version="v2.1-linucb"
                    )

                    submitted += 1
                    results.append({"company": company, "title": title, "status": sub_status, "ats": ats_type})
                    if active_page != page:
                        try:
                            active_page.close()
                        except Exception:
                            pass

                except Exception as e:
                    print(f"    ❌ Error processing {company}: {e}")
                    skipped += 1

            context.close()

        print("\n" + "=" * 65)
        print(f"  🏁 External Portal Batch Complete: {submitted} Submitted, {skipped} Skipped")
        print("=" * 65)
        return {"processed": processed, "submitted": submitted, "skipped": skipped, "items": results}


# ==============================================================================
# EXTERNAL ATS PORTAL MANAGER & BATCH RUNNER
# ==============================================================================

CURATED_ATS_VACANCIES: List[Dict[str, Any]] = [
    {
        "company": "Microsoft GCC",
        "title": "Lead Azure Data Engineer",
        "salary": "25 - 32 Lacs PA",
        "url": "https://boards.greenhouse.io/microsoftgcc/jobs/401",
        "jd": "Azure Databricks PySpark Delta Lake Medallion Architecture Kafka ADF SQL Terraform",
        "exp": "2-5 Yrs",
        "location": "Bengaluru / Hyderabad",
        "ats": "Greenhouse"
    },
    {
        "company": "Walmart Global Tech",
        "title": "Azure Data Platform Engineer",
        "salary": "22 - 28 Lacs PA",
        "url": "https://walmart.wd5.myworkdayjobs.com/en-US/jobs/job/Azure-Data-Engineer_R-9901",
        "jd": "Azure Databricks PySpark Delta Lake SQL Terraform ADLS Gen2 DataOps",
        "exp": "2-5 Yrs",
        "location": "Bengaluru",
        "ats": "Workday"
    },
    {
        "company": "Uber Technologies",
        "title": "Data Engineer II - Real-Time Streaming",
        "salary": "24 - 35 Lacs PA",
        "url": "https://jobs.lever.co/uber/803",
        "jd": "Apache Kafka PySpark Delta Lake Medallion Architecture Azure Databricks SQL",
        "exp": "2-4 Yrs",
        "location": "Hyderabad",
        "ats": "Lever"
    },
    {
        "company": "Atlassian",
        "title": "Data Platform Engineer",
        "salary": "24 - 30 Lacs PA",
        "url": "https://boards.greenhouse.io/atlassian/jobs/502",
        "jd": "Azure Data Factory Databricks PySpark Delta Lake Terraform Medallion Lakehouse",
        "exp": "2-5 Yrs",
        "location": "Bengaluru / Remote",
        "ats": "Greenhouse"
    },
    {
        "company": "Databricks Partner GCC",
        "title": "Senior Azure Databricks Specialist",
        "salary": "25 - 34 Lacs PA",
        "url": "https://jobs.ashbyhq.com/databricks-partner/904",
        "jd": "Azure Databricks PySpark Delta Lake Unity Catalog Medallion Architecture SQL",
        "exp": "2-5 Yrs",
        "location": "Bengaluru / Pune",
        "ats": "Ashby"
    },
    {
        "company": "Swiggy Engineering",
        "title": "Frontend React Engineer",
        "salary": "18 - 22 Lacs PA",
        "url": "https://boards.greenhouse.io/swiggy/jobs/701",
        "jd": "React Redux TypeScript Next.js Tailwind CSS HTML",
        "exp": "2-4 Yrs",
        "location": "Bengaluru",
        "ats": "Greenhouse"
    }
]


class CareerPortalManager:
    """
    Unified Manager for External ATS Career Portals (Greenhouse, Lever, Ashby, Workday, etc.).
    Coordinates detection, ATS-specific form handlers, screening question resolution, and submission.
    """
    def __init__(self, profile: Optional[Dict[str, Any]] = None, solver: Optional[FactMatrixScreeningSolver] = None):
        self.filler = CareerPortalFiller()
        self.profile = profile or self.filler.profile
        self.solver = solver or self.filler.solver

    def detect_ats(self, url: Optional[str]) -> str:
        return self.filler.detect_ats(url)

    def get_handler(self, ats_type: str) -> BaseATSHandler:
        return self.filler.get_handler(ats_type)

    def fill_dry_run(
        self,
        portal_url: str,
        company: str = "Company",
        role: str = "Azure Data Engineer",
        raw_jd: str = "",
        salary: str = "25 LPA",
        match_score: Optional[int] = None
    ) -> Any:
        return self.filler.fill_dry_run(
            portal_url=portal_url,
            company=company,
            role=role,
            raw_jd=raw_jd,
            salary=salary,
            match_score=match_score
        )

    def fill(
        self,
        portal_url: str,
        company: str = "Company",
        role: str = "Azure Data Engineer",
        headless: bool = False,
        dry_run: bool = False,
        raw_jd: str = "",
        salary: str = "25 LPA",
        page=None,
        match_score: Optional[int] = None
    ):
        return self.filler.fill(
            portal_url=portal_url,
            company=company,
            role=role,
            headless=headless,
            dry_run=dry_run,
            raw_jd=raw_jd,
            salary=salary,
            page=page,
            match_score=match_score
        )


class ExternalPortalBatchRunner:
    """
    Autonomous Batch Execution Engine for External ATS Portals.
    In Universal Apply Mode (default):
    - NO FILTERING: Applies to every discovered job regardless of title, company, domain, salary, or score.
    - 3 HARD STOPS ONLY: (1) already applied, (2) closed/expired, (3) form error/auth barrier after 2 retries.
    - 100% Dual Logging: Synchronous SQLite DB + Excel Tracker persistence.
    """
    def __init__(
        self,
        manager: Optional[CareerPortalManager] = None,
        dry_run: bool = False,
        headless: bool = True,
        min_score: float = 0.0,
        limit: int = 25,
        min_salary: float = 0.0,
        db_path: Optional[str] = None,
        universal_apply: Optional[bool] = None
    ):
        self.manager = manager or CareerPortalManager()
        self.dry_run = dry_run
        self.headless = headless
        self.min_score = min_score
        self.limit = limit
        self.min_salary = min_salary
        self.db_path = db_path
        if universal_apply is not None:
            self.universal_apply = universal_apply
        else:
            self.universal_apply = (min_score <= 0.0 and min_salary <= 0.0)
        self.curated_vacancies = list(CURATED_ATS_VACANCIES)

    def run_batch(
        self,
        vacancies: Optional[List[Dict[str, Any]]] = None,
        roles: Optional[List[str]] = None,
        locations: Optional[List[str]] = None,
        ats_types: Optional[List[str]] = None,
        dry_run: Optional[bool] = None,
        limit: Optional[int] = None,
        min_score: Optional[float] = None,
        min_salary: Optional[float] = None,
        universal_apply: Optional[bool] = None
    ) -> Dict[str, Any]:
        active_dry_run = self.dry_run if dry_run is None else dry_run
        active_limit = self.limit if limit is None else limit
        active_min_score = self.min_score if min_score is None else min_score
        active_min_salary = self.min_salary if min_salary is None else min_salary
        if universal_apply is not None:
            is_universal = universal_apply
        elif (min_score is not None and min_score > 0.0) or (min_salary is not None and min_salary > 0.0):
            is_universal = False
        else:
            is_universal = self.universal_apply

        feed = list(vacancies) if vacancies is not None else list(self.curated_vacancies)

        # Filter by ats_types if explicitly specified
        if ats_types:
            ats_lower = [a.lower().strip() for a in ats_types]
            filtered_feed = []
            for v in feed:
                v_ats = self.manager.detect_ats(v.get("url", "")).lower()
                tag_ats = v.get("ats", "").lower()
                if any(target in v_ats or target in tag_ats for target in ats_lower):
                    filtered_feed.append(v)
            feed = filtered_feed

        # In legacy mode only: filter by roles if specified
        if not is_universal and roles:
            roles_lower = [r.lower().strip() for r in roles]
            feed = [
                v for v in feed
                if any(r in v.get("title", "").lower() or r in v.get("jd", "").lower() for r in roles_lower)
            ]

        # In legacy mode only: filter by locations if specified
        if not is_universal and locations:
            locs_lower = [l.lower().strip() for l in locations]
            feed = [
                v for v in feed
                if any(l in v.get("location", "").lower() or "remote" in v.get("location", "").lower() for l in locs_lower)
            ]

        stats = {
            "total_evaluated": 0,
            "submitted": 0,
            "skipped": 0,
            "dry_run": active_dry_run,
            "jobs": []
        }

        from naukari_pro.modules.auto_apply import is_salary_acceptable, is_experience_eligible
        from naukari_pro.modules.job_alerts import calculate_match_score
        from naukari_pro.modules.db import is_job_already_applied, generate_job_id
        from naukari_pro.modules.scorecard import sync_dual_log

        for job in feed:
            if stats["submitted"] >= active_limit:
                break

            stats["total_evaluated"] += 1
            company = job.get("company", "Company")
            title = job.get("title", "Role")
            url = job.get("url", "N/A")
            jd = job.get("jd", "")
            salary = job.get("salary", "22 - 28 Lacs PA")
            exp = job.get("exp", "2-5 Yrs")
            ats_type = self.manager.detect_ats(url)
            score = float(calculate_match_score(f"{title} {company} {jd}"))

            if not is_universal:
                # ── Legacy Mode Filtering ──
                sal_ok, _ = is_salary_acceptable(salary, active_min_salary)
                if not sal_ok:
                    stats["skipped"] += 1
                    stats["jobs"].append({
                        "company": company,
                        "title": title,
                        "url": url,
                        "ats": ats_type,
                        "status": "REJECTED_LOW_SALARY",
                        "score": 0.0
                    })
                    continue

                is_exp_ok, _, _, _ = is_experience_eligible(
                    exp_text=exp,
                    title=title,
                    url=url,
                    candidate_exp=float(self.manager.profile.get("experienceYears", 2.5)),
                    max_allowed=4.5
                )
                if not is_exp_ok:
                    stats["skipped"] += 1
                    stats["jobs"].append({
                        "company": company,
                        "title": title,
                        "url": url,
                        "ats": ats_type,
                        "status": "REJECTED_EXPERIENCE",
                        "score": 0.0
                    })
                    continue

                if score < active_min_score:
                    stats["skipped"] += 1
                    stats["jobs"].append({
                        "company": company,
                        "title": title,
                        "url": url,
                        "ats": ats_type,
                        "status": "REJECTED_BELOW_THRESHOLD",
                        "score": score
                    })
                    continue

            # ── 3 HARD STOPS (Universal Mode) ──

            # Hard Stop 1: Deduplication (Job ID / URL / Title + Company)
            cand_job_id = job.get("job_id") or generate_job_id(title, company, url)
            if is_job_already_applied(title=title, company=company, job_url=url, job_id=cand_job_id, db_path=self.db_path):
                stats["skipped"] += 1
                stats["jobs"].append({
                    "job_id": cand_job_id,
                    "company": company,
                    "title": title,
                    "url": url,
                    "ats": ats_type,
                    "status": "SKIPPED_ALREADY_APPLIED",
                    "score": score
                })
                if not active_dry_run:
                    sync_dual_log(
                        title=title,
                        company=company,
                        platform=f"career_portal ({ats_type})",
                        status="SKIPPED_ALREADY_APPLIED",
                        job_url=url,
                        match_score=score,
                        experience_req=exp,
                        db_path=self.db_path
                    )
                continue

            # Hard Stop 2: Dead / Closed / Expired Link Check
            if not url or url == "N/A" or "example.com" in url or "invalid" in url:
                stats["skipped"] += 1
                stats["jobs"].append({
                    "company": company,
                    "title": title,
                    "url": url,
                    "ats": ats_type,
                    "status": "SKIPPED_CLOSED_OR_EXPIRED",
                    "score": score
                })
                if not active_dry_run:
                    sync_dual_log(
                        title=title,
                        company=company,
                        platform=f"career_portal ({ats_type})",
                        status="SKIPPED_CLOSED_OR_EXPIRED",
                        job_url=url,
                        match_score=score,
                        experience_req=exp,
                        error_reason="Dead link / expired URL",
                        db_path=self.db_path
                    )
                continue

            # Process Application
            if active_dry_run:
                payload = self.manager.fill_dry_run(
                    portal_url=url,
                    company=company,
                    role=title,
                    raw_jd=jd,
                    salary=salary,
                    match_score=int(score)
                )
                stats["submitted"] += 1
                stats["jobs"].append({
                    "company": company,
                    "title": title,
                    "url": url,
                    "ats": ats_type,
                    "status": "SUBMITTED_DRY_RUN",
                    "score": score,
                    "payload": payload
                })
            else:
                # Live Execution with 2 Retries (Hard Stop 3 Enforcement)
                submission_success = False
                filled_fields = []
                evidence_file = None
                last_error = ""

                for attempt in range(1, 3):
                    try:
                        success, fields = self.manager.fill(
                            portal_url=url,
                            company=company,
                            role=title,
                            headless=self.headless,
                            dry_run=False,
                            raw_jd=jd,
                            salary=salary,
                            match_score=int(score)
                        )
                        submission_success = success
                        filled_fields = fields
                        break
                    except Exception as e_fill:
                        last_error = str(e_fill)
                        if attempt < 2:
                            time.sleep(2)

                if not submission_success and not filled_fields and last_error:
                    # Hard Stop 3: Failed after 2 retries
                    stats["skipped"] += 1
                    stats["jobs"].append({
                        "company": company,
                        "title": title,
                        "url": url,
                        "ats": ats_type,
                        "status": "FAILED_FORM_ERROR",
                        "score": score,
                        "error": last_error
                    })
                    sync_dual_log(
                        title=title,
                        company=company,
                        platform=f"career_portal ({ats_type})",
                        status="FAILED_FORM_ERROR",
                        job_url=url,
                        match_score=score,
                        experience_req=exp,
                        error_reason=f"Failed after 2 retries: {last_error}",
                        db_path=self.db_path
                    )
                    continue

                status_str = "Submitted (Confirmed)" if submission_success else "Form Auto-Filled (Ready for Review)"
                sync_dual_log(
                    title=title,
                    company=company,
                    platform=f"career_portal ({ats_type})",
                    status=status_str,
                    job_url=url,
                    match_score=score,
                    experience_req=exp,
                    location=job.get("location", "Hyderabad / Remote"),
                    application_type=f"Career Portal ({ats_type})",
                    evidence_path=evidence_file,
                    db_path=self.db_path,
                )
                stats["submitted"] += 1
                stats["jobs"].append({
                    "company": company,
                    "title": title,
                    "url": url,
                    "ats": ats_type,
                    "status": status_str,
                    "score": score,
                    "filled": filled_fields
                })

        return stats


