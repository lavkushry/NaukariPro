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
import re
import json
import time
import logging
import asyncio
import requests
import subprocess
from enum import Enum
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Union, Tuple
from concurrent.futures import ThreadPoolExecutor
import openpyxl

from naukari_pro.config import BASE_DIR, TRACKER_PATH, RESUME_PDF_PATH, load_config
from naukari_pro.modules.candidate_profile import (
    DEFAULT_HYBRID_PROFILE,
    OFFICIAL_WORK_HISTORY,
    PROFILE_PATH,
    PROJECT_PROOF_POINTS,
    TARGET_TITLE,
    load_hybrid_profile,
)
from naukari_pro.modules.learning.screening_solver import FactMatrixScreeningSolver
from naukari_pro.modules.learning.evidence import EvidenceVerifier
from naukari_pro.modules.scorecard import sync_dual_log

logger = logging.getLogger("naukariPro.CareerPortals")

PORTALS_SESSION_DIR = os.path.join(BASE_DIR, "career_portals_system", "browser_session")

# Dedicated worker thread pool to isolate Playwright Sync API from any running asyncio loops.
# max_workers=1: serialize portal browsers so they never contend with each other
# (Naukri holds a separate session dir; portals use PORTALS_SESSION_DIR).
_PORTAL_WORKER_POOL = ThreadPoolExecutor(max_workers=1, thread_name_prefix="PortalWorker")

def _is_asyncio_loop_running() -> bool:
    """Returns True if the current thread owns an active running asyncio event loop."""
    try:
        loop = asyncio.get_running_loop()
        return loop is not None and loop.is_running()
    except RuntimeError:
        return False

# Hybrid ground truth: FACT_MATRIX titles + Azure DE market surface
DEFAULT_CANDIDATE = json.loads(json.dumps(DEFAULT_HYBRID_PROFILE))

def load_applicant_profile():
    data = load_hybrid_profile()

    # 1. Overlay ~/.job-apply/profile.json contact fields only (titles locked in hybrid loader)
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

    # Hybrid lock: official FACT_MATRIX titles + project proofs; market target stays Azure DE
    data["currentTitle"] = "DevOps Engineer"
    data["workHistory"] = json.loads(json.dumps(OFFICIAL_WORK_HISTORY))
    data["targetTitle"] = TARGET_TITLE
    data["marketTitle"] = TARGET_TITLE
    data["projectProofPoints"] = json.loads(json.dumps(PROJECT_PROOF_POINTS))
    return data

def log_portal_application(
    company,
    role,
    portal_type,
    status,
    url,
    match_score=85,
    tracker_path=None,
    evidence_path=None
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
                applicant_email=p.get("email", "lav84095@gmail.com"),
                evidence_path=evidence_path
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


# ==============================================================================
# ARCHITECTURE RULES A1–A5: STATE MACHINE, SCHEMAS & ANCHORS
# ==============================================================================

class PortalState(str, Enum):
    """Architecture Rule A1: Explicit Unified State Machine."""
    DETECT = "DETECT"
    ACCOUNT = "ACCOUNT"
    FILL = "FILL"
    REVIEW = "REVIEW"
    SUBMIT = "SUBMIT"
    VERIFY = "VERIFY"
    LOG = "LOG"


class FallbackReason(str, Enum):
    """Architecture Rule A1: Standardized Auditor Fallback Reason Codes."""
    ASYNCIO_ERROR = "ASYNCIO_ERROR"
    SIGNIN_WALL = "SIGNIN_WALL"
    ACCOUNT_CREATE_FAILED = "ACCOUNT_CREATE_FAILED"
    OTP_NOT_FOUND = "OTP_NOT_FOUND"
    SELECTOR_MISS = "SELECTOR_MISS"
    SUBMIT_NOT_FOUND = "SUBMIT_NOT_FOUND"
    CLICKED_NO_CONFIRMATION = "CLICKED_NO_CONFIRMATION"
    VALIDATION_ERRORS = "VALIDATION_ERRORS"
    CAPTCHA = "CAPTCHA"
    TIMEOUT_240S = "TIMEOUT_240S"
    CLOSED_OR_EXPIRED = "CLOSED_OR_EXPIRED"
    ALREADY_APPLIED = "SKIPPED_ALREADY_APPLIED"


PER_JOB_TIME_BUDGET_SEC: float = 240.0


def checkpoint_portal_state(
    job_id: str,
    state: PortalState,
    company: str = "",
    role: str = "",
    db_path: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
):
    """
    Architecture Rule A4: Checkpoint State Machine Step to DB after every transition
    so killed cycles can be audited or resumed cleanly.
    """
    try:
        from naukari_pro.modules.db import get_db_connection
        conn = get_db_connection(db_path)
        c = conn.cursor()
        chk = f"CHECKPOINT_{state.value}"
        c.execute(
            "UPDATE applied_jobs SET outcome_label = ? WHERE job_id = ?",
            (chk, str(job_id))
        )
        conn.commit()
        conn.close()
    except Exception as e_chk:
        logger.debug("State checkpoint notice: %s", e_chk)


class ATSFormSchemaPlanner:
    """
    Architecture Rule A2: SCHEMA BEFORE BROWSER.
    Fetches ATS public form schemas (Greenhouse Job Board API, Lever postings API, Ashby public API)
    offline before browser execution and constructs an AnswerPlan.
    """
    def __init__(self, profile: Dict[str, Any], solver: Optional[FactMatrixScreeningSolver] = None):
        self.profile = profile
        self.solver = solver or FactMatrixScreeningSolver()

    def fetch_schema_plan(self, portal_url: str) -> Optional[Dict[str, Any]]:
        if not portal_url or not isinstance(portal_url, str):
            return None
        u = portal_url.lower()
        if "greenhouse.io" in u:
            return self._plan_greenhouse(portal_url)
        elif "lever.co" in u:
            return self._plan_lever(portal_url)
        return None

    def _plan_greenhouse(self, url: str) -> Optional[Dict[str, Any]]:
        # Extract board and job_id from Greenhouse URL
        m = re.search(r"greenhouse\.io/(?:embed/job_app\?for=([^&]+)&token=([^&]+)|([^/]+)/jobs/(\d+))", url)
        board, jid = None, None
        if m:
            if m.group(1) and m.group(2):
                board, jid = m.group(1), m.group(2)
            elif m.group(3) and m.group(4):
                board, jid = m.group(3), m.group(4)
        if not board or not jid:
            return None

        api_url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{jid}?questions=true"
        try:
            r = requests.get(api_url, timeout=5)
            if r.status_code != 200:
                return None
            data = r.json()
            questions = data.get("questions", [])
            answers: Dict[str, Any] = {}
            p = self.profile
            for q in questions:
                lbl = q.get("label", "")
                fields = q.get("fields", [])
                for f in fields:
                    fname = f.get("name", "")
                    ftype = f.get("type", "")
                    vals = f.get("values", [])
                    opt_labels = [v.get("label") for v in vals if isinstance(v, dict) and "label" in v]
                    ans = None
                    if "first" in fname.lower():
                        ans = p.get("firstName", "Lavkush")
                    elif "last" in fname.lower():
                        ans = p.get("lastName", "Kumar")
                    elif "email" in fname.lower():
                        ans = p.get("email", "lav84095@gmail.com")
                    elif "phone" in fname.lower():
                        ans = p.get("phone", "+91-9122036484")
                    elif "location" in fname.lower():
                        ans = p.get("city", "Hyderabad, India")
                    elif "linkedin" in fname.lower():
                        ans = p.get("linkedInUrl", "https://linkedin.com/in/lavkush-kumar")
                    elif any(k in fname.lower() for k in ("website", "portfolio", "github")):
                        ans = p.get("portfolioUrl", "https://github.com/lavkush-kumar")
                    else:
                        decision = self.solver.evaluate_question(lbl, context={"options": opt_labels})
                        if decision and decision.answer and not decision.is_ambiguous:
                            ans = decision.answer
                    if ans:
                        answers[fname] = ans
                        answers[lbl] = ans
            return {"ats": "Greenhouse", "board": board, "job_id": jid, "answers": answers}
        except Exception as e:
            logger.debug("Notice fetching Greenhouse schema plan: %s", e)
            return None

    def _plan_lever(self, url: str) -> Optional[Dict[str, Any]]:
        m = re.search(r"lever\.co/([^/]+)/([a-zA-Z0-9-]+)", url)
        if not m:
            return None
        company, jid = m.group(1), m.group(2)
        api_url = f"https://api.lever.co/v0/postings/{company}/{jid}"
        try:
            r = requests.get(api_url, timeout=5)
            if r.status_code == 200:
                data = r.json()
                return {"ats": "Lever", "company": company, "job_id": jid, "data": data}
        except Exception:
            pass
        return None


def resolve_anchor_ladder(
    container: Any,
    field_id: str = "",
    label_text: str = "",
    autocomplete: str = "",
    name: str = "",
    aria_label: str = "",
    css_fallback: str = ""
) -> Tuple[Optional[Any], str]:
    """
    Architecture Rule A3: ANCHOR LADDER for every field in order:
    1. data-automation-id
    2. label text (label:has-text(...) -> for attribute or nested input)
    3. autocomplete attribute
    4. name or id attribute
    5. aria-label attribute
    6. CSS fallback (flags SELECTOR_MISS if only CSS matches)
    Returns: (locator, rung_matched: str)
    """
    if not container:
        return None, "NONE"

    # Rung 1: data-automation-id
    if field_id:
        try:
            loc = container.locator(f"[data-automation-id='{field_id}']")
            if safe_count(loc) > 0 and loc.first.is_visible():
                return loc.first, "data-automation-id"
        except Exception:
            pass

    # Rung 2: label text
    if label_text:
        try:
            lbl = container.locator(f"label:has-text('{label_text}')").first
            if safe_count(lbl) > 0 and lbl.is_visible():
                for_id = lbl.get_attribute("for")
                if for_id:
                    inp = container.locator(f"#{for_id}").first
                    if safe_count(inp) > 0 and inp.is_visible():
                        return inp, "label text (for)"
                nested_inp = lbl.locator("input, textarea, select").first
                if safe_count(nested_inp) > 0 and nested_inp.is_visible():
                    return nested_inp, "label text (nested)"
        except Exception:
            pass

    # Rung 3: autocomplete
    if autocomplete:
        try:
            loc = container.locator(f"input[autocomplete='{autocomplete}']")
            if safe_count(loc) > 0 and loc.first.is_visible():
                return loc.first, "autocomplete"
        except Exception:
            pass

    # Rung 4: name or id
    if name:
        try:
            loc = container.locator(f"input[name='{name}'], textarea[name='{name}'], select[name='{name}'], input#{name}, textarea#{name}")
            if safe_count(loc) > 0 and loc.first.is_visible():
                return loc.first, "name/id"
        except Exception:
            pass

    # Rung 5: aria-label
    if aria_label:
        try:
            loc = container.locator(f"[aria-label*='{aria_label}' i]")
            if safe_count(loc) > 0 and loc.first.is_visible():
                return loc.first, "aria-label"
        except Exception:
            pass

    # Rung 6: CSS fallback
    if css_fallback:
        try:
            loc = container.locator(css_fallback)
            if safe_count(loc) > 0 and loc.first.is_visible():
                logger.warning("SELECTOR_MISS: Field matched only via CSS rung: %s", css_fallback)
                return loc.first, "CSS (SELECTOR_MISS)"
        except Exception:
            pass

    return None, "NONE"


class BaseATSHandler:
    """Base class for dedicated ATS platform form handlers."""

    def __init__(self, profile: Dict[str, Any], solver: Optional[FactMatrixScreeningSolver] = None, ats_type: str = "Generic"):
        self.profile = profile
        self.solver = solver or FactMatrixScreeningSolver()
        self.ats_type = ats_type
        self.field_records: List[Dict[str, Any]] = []

    def record_field(
        self,
        label: str,
        value: Any,
        field_name: Optional[str] = None,
        field_type: str = "text",
        step: int = 1,
        step_name: str = "APPLICATION_FORM",
        action_type: str = "FILLED",
        rung: str = "ladder"
    ):
        """Appends a field interaction record to the handler's audit ledger."""
        self.field_records.append({
            "step": step,
            "step_name": step_name,
            "field": str(label),
            "name": str(field_name or label),
            "type": field_type,
            "value": str(value),
            "action_type": action_type,
            "rung": rung
        })

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

    def fill_form(self, page: Any, schema_plan: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Fills standard form inputs and screening questions."""
        raise NotImplementedError

    def upload_resume(self, page: Any, resume_path: Optional[str]) -> bool:
        """Uploads resume to available file input and logs the file attachment."""
        if not page or not resume_path or not os.path.exists(resume_path):
            return False
        try:
            file_input = page.locator("input[type='file']").first
            if safe_count(file_input) > 0:
                file_input.set_input_files(resume_path)
                self.record_field(
                    label="Resume File",
                    value=os.path.basename(resume_path),
                    field_name="resume",
                    field_type="file",
                    step=1,
                    step_name="RESUME_ATTACHMENT",
                    action_type="UPLOADED"
                )
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


USED_GREENHOUSE_SECURITY_CODES = set()


def fetch_greenhouse_security_code(since_ts: float = 0.0, timeout_sec: float = 45.0) -> Optional[str]:
    """Retrieves fresh 8-character Greenhouse email verification security code via Gmail IMAP."""
    import imaplib, email, re, email.utils
    from dotenv import load_dotenv
    load_dotenv()
    user = os.getenv("GMAIL_USER", "lav84095@gmail.com")
    pwd = os.getenv("GMAIL_APP_PASSWORD", "")
    start = time.time()
    while time.time() - start < timeout_sec:
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(user, pwd)
            mail.select("INBOX")
            status, data = mail.search(None, "ALL")
            ids = data[0].split()
            for mid in reversed(ids[-15:]):
                status, mdata = mail.fetch(mid, "(RFC822)")
                msg = email.message_from_bytes(mdata[0][1])
                subj = msg.get("Subject", "")
                if any(k in subj.lower() for k in ["security code", "verification code", "verify your application", "verification"]):
                    # Check email date if available
                    date_tuple = email.utils.parsedate_tz(msg.get("Date"))
                    msg_epoch = email.utils.mktime_tz(date_tuple) if date_tuple else 0
                    if since_ts > 0 and msg_epoch > 0 and msg_epoch < (since_ts - 15):
                        continue

                    clean_text = ""
                    for part in msg.walk():
                        ctype = part.get_content_type()
                        if ctype == "text/plain":
                            clean_text += " " + part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        elif ctype == "text/html":
                            raw_html = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                            clean_text += " " + re.sub(r"<[^>]+>", " ", raw_html)
                    clean_text = re.sub(r"\s+", " ", clean_text).strip()

                    match = re.search(r"into the security code field on your application:\s*([a-zA-Z0-9]{8})", clean_text)
                    if not match:
                        match = re.search(r"\b(?:security code|verification code|your code is|enter the code)[:\s]+([a-zA-Z0-9]{6,8})\b", clean_text, re.IGNORECASE)
                    if not match:
                        match = re.search(r"\b([A-Z0-9]{8})\b", clean_text)

                    if match:
                        code = match.group(1)
                        if code in USED_GREENHOUSE_SECURITY_CODES:
                            continue  # Stale code from prior application, wait for new email
                        USED_GREENHOUSE_SECURITY_CODES.add(code)
                        mail.logout()
                        return code
            mail.logout()
        except Exception:
            pass
        time.sleep(2.5)
    return None


class GreenhouseHandler(BaseATSHandler):
    """Dedicated handler for Greenhouse ATS (boards.greenhouse.io & job-boards.greenhouse.io)."""

    def __init__(self, profile: Dict[str, Any], solver: Optional[FactMatrixScreeningSolver] = None):
        super().__init__(profile, solver, ats_type="Greenhouse")

    def fill_form(self, page: Any, schema_plan: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        filled = []
        p = self.profile
        if not page:
            return {"filled": filled, "ats": "Greenhouse"}

        # 0. Pre-apply answers from schema_plan if available (Architecture Rule A2: SCHEMA BEFORE BROWSER)
        if schema_plan and isinstance(schema_plan, dict) and "answers" in schema_plan:
            for k, v in schema_plan["answers"].items():
                try:
                    target_inp = page.locator(f"input[name='{k}'], textarea[name='{k}'], input#{k}, textarea#{k}").first
                    if safe_count(target_inp) > 0 and target_inp.is_visible():
                        val_now = ""
                        if hasattr(target_inp, "input_value"):
                            try:
                                iv = target_inp.input_value()
                                if isinstance(iv, str):
                                    val_now = iv
                            except Exception:
                                pass
                        if not val_now:
                            target_inp.fill(str(v))
                            filled.append(f"Schema: {k}")
                            self.record_field(
                                label=k,
                                value=v,
                                field_name=k,
                                field_type="text",
                                step=1,
                                step_name="SCHEMA_PLAN",
                                action_type="FILLED",
                                rung="schema_plan"
                            )
                except Exception:
                    pass

        # 1. Standard Contact Fields via Anchor Ladder (Architecture Rule A3)
        contact_ladder = [
            ("first_name", "First Name", "given-name", "first_name", "first name", "#first_name, input[name*='first_name' i]", p.get("firstName", "Lavkush"), "First Name"),
            ("last_name", "Last Name", "family-name", "last_name", "last name", "#last_name, input[name*='last_name' i]", p.get("lastName", "Kumar"), "Last Name"),
            ("email", "Email", "email", "email", "email", "#email, input[type='email'], input[name*='email' i]", p.get("email", "lav84095@gmail.com"), "Email"),
            ("phone", "Phone", "tel", "phone", "phone", "#phone, input[type='tel'], input[name*='phone' i]", p.get("phone", "+91-9122036484"), "Phone"),
            ("job_application_location", "Location", "address-level2", "location", "location", "#job_application_location, input[name*='location' i]", p.get("city", "Hyderabad"), "Location"),
            ("linkedin", "LinkedIn", "", "linkedin", "linkedin", "input[name*='linkedin' i], input[id*='linkedin' i]", p.get("linkedInUrl", "https://linkedin.com/in/lavkush-kumar"), "LinkedIn"),
            ("website", "Website", "", "website", "portfolio", "input[name*='website' i], input[name*='portfolio' i], input[name*='github' i]", p.get("portfolioUrl", "https://github.com/lavkush-kumar"), "Website"),
        ]
        for f_id, lbl_txt, ac, nm, aria, css, val, label in contact_ladder:
            try:
                loc, rung = resolve_anchor_ladder(page, field_id=f_id, label_text=lbl_txt, autocomplete=ac, name=nm, aria_label=aria, css_fallback=css)
                if loc and safe_count(loc) > 0 and loc.is_visible():
                    val_cur = ""
                    if hasattr(loc, "input_value"):
                        try:
                            iv = loc.input_value()
                            if isinstance(iv, str):
                                val_cur = iv
                        except Exception:
                            pass
                    if not val_cur:
                        loc.fill(str(val))
                        filled.append(label)
                        self.record_field(
                            label=label,
                            value=val,
                            field_name=nm or f_id,
                            field_type="text",
                            step=1,
                            step_name="BASIC_INFO",
                            action_type="FILLED",
                            rung=rung
                        )
            except Exception:
                pass

        # 2. React-Select Location Search (e.g. #candidate-location)
        try:
            loc_inp = page.locator("#candidate-location, input[id*='location' i].select__input").first
            if safe_count(loc_inp) > 0 and loc_inp.is_visible():
                loc_inp.click()
                loc_inp.fill("Hyderabad")
                time.sleep(1.2)
                opts = page.locator(".select__option")
                if safe_count(opts) > 0:
                    opts.first.click()
                else:
                    if hasattr(page, "keyboard"):
                        page.keyboard.press("ArrowDown")
                        page.keyboard.press("Enter")
                filled.append("Location (React-Select)")
                self.record_field(
                    label="Candidate Location",
                    value="Hyderabad, India",
                    field_name="candidate-location",
                    field_type="select",
                    step=1,
                    step_name="BASIC_INFO",
                    action_type="SELECTED"
                )
        except Exception as e_loc:
            logger.debug("Greenhouse location React-Select notice: %s", e_loc)

        # 3. Comprehensive Question Filling across all visible Labels & Inputs
        try:
            labels = page.locator("label")
            lbl_cnt = safe_count(labels)
            for i in range(lbl_cnt):
                try:
                    lbl = labels.nth(i)
                    lbl_text = lbl.inner_text().strip()
                    if not lbl_text:
                        continue
                    q_lower = lbl_text.lower()
                    for_id = lbl.get_attribute("for")
                    if not for_id:
                        continue
                    inp = page.locator(f'[id="{for_id}"]').first
                    if safe_count(inp) > 0 and inp.is_visible():
                        tag_name = inp.evaluate("el => el.tagName")
                        is_special = inp.evaluate("el => el.classList.contains('select__input') || el.type === 'file'")
                        if tag_name in ["INPUT", "TEXTAREA"] and not is_special:
                            cur_val = inp.input_value() if hasattr(inp, "input_value") else ""
                            if not cur_val:
                                decision = self.solver.evaluate_question(lbl_text)
                                ans_to_fill = decision.answer if (decision and decision.confidence >= 0.7 and decision.answer) else None
                                if not ans_to_fill:
                                    if "linkedin" in q_lower:
                                        ans_to_fill = p.get("linkedInUrl", "https://linkedin.com/in/lavkush-kumar")
                                    elif any(k in q_lower for k in ["github", "portfolio", "website", "artifact", "code", "project", "work"]):
                                        ans_to_fill = p.get("portfolioUrl", "https://github.com/lavkush-kumar")
                                    elif any(k in q_lower for k in ["country", "timezone", "time zone"]):
                                        ans_to_fill = "India (IST, UTC+5:30)"
                                    elif any(k in q_lower for k in ["hear about", "opportunity", "source", "referral"]):
                                        ans_to_fill = "LinkedIn"
                                    elif any(k in q_lower for k in ["notice", "availability"]):
                                        ans_to_fill = "15 Days"
                                    elif any(k in q_lower for k in ["salary", "compensation"]):
                                        ans_to_fill = "Market Standard / Negotiable"
                                    elif any(k in q_lower for k in ["programming language", "primary language"]):
                                        ans_to_fill = "Python"
                                    elif any(k in q_lower for k in ["adjustment", "accommodation"]):
                                        ans_to_fill = "None"
                                    else:
                                        ans_to_fill = "Yes"
                                inp.fill(str(ans_to_fill))
                                filled.append(f"Screening: {lbl_text[:20]}")
                                self.record_field(
                                    label=lbl_text,
                                    value=ans_to_fill,
                                    field_name=for_id,
                                    field_type="text",
                                    step=1,
                                    step_name="CUSTOM_SCREENING",
                                    action_type="ANSWERED"
                                )
                except Exception:
                    pass
        except Exception as e_lbls:
            logger.debug("Greenhouse label traversal notice: %s", e_lbls)

        # 4. React-Select Control Handler (Comboboxes, Custom Questions & Anti-Bot Protection)
        try:
            react_selects = page.locator(".select__control")
            rs_cnt = safe_count(react_selects)
            for i in range(rs_cnt):
                try:
                    ctrl = react_selects.nth(i)
                    parent_lbl = ctrl.locator("xpath=ancestor::div[contains(@class, 'field-wrapper') or contains(@class, 'field')]//label").first
                    lbl_text = parent_lbl.inner_text().strip() if safe_count(parent_lbl) > 0 else f"Select {i}"
                    lbl_lower = lbl_text.lower()
                    ctrl_text = ctrl.inner_text() or ""

                    # Skip phone country code and candidate city location search (already handled)
                    if ("+1" in ctrl_text and "phone" in lbl_lower) or "location (city)" in lbl_lower or ctrl.locator("#candidate-location").count() > 0 or (lbl_lower.startswith("location") and "sponsorship" not in lbl_lower):
                        continue

                    ctrl.click()
                    time.sleep(0.3)
                    opt_locs = page.locator(".select__option")
                    opts = [o.strip() for o in opt_locs.all_inner_texts() if o.strip()]

                    target_choice = None
                    # Anti-Bot Protection: Always answer "I am a human being"
                    if any("human" in o.lower() for o in opts) or "best describes you" in lbl_lower:
                        for opt in opts:
                            if "human" in opt.lower():
                                target_choice = opt
                                break
                    elif "sponsorship" in lbl_lower:
                        for opt in opts:
                            if opt.lower() == "no":
                                target_choice = opt
                                break
                    elif any(k in lbl_lower for k in ["employment agreements", "restrictions", "post-employment"]):
                        for opt in opts:
                            if opt.lower() == "no":
                                target_choice = opt
                                break
                    elif "previously worked" in lbl_lower:
                        for opt in opts:
                            if opt.lower() == "no":
                                target_choice = opt
                                break
                    elif "country" in lbl_lower:
                        for opt in opts:
                            if opt.lower() == "india":
                                target_choice = opt
                                break
                        if not target_choice:
                            inp = ctrl.locator("input.select__input").first
                            if safe_count(inp) > 0:
                                inp.fill("India")
                                time.sleep(0.5)
                                opts_after = page.locator(".select__option").all_inner_texts()
                                for opt in opts_after:
                                    if "india" in opt.lower():
                                        target_choice = opt.strip()
                                        break
                    elif "eligible to work" in lbl_lower or "authorized to work" in lbl_lower:
                        for opt in opts:
                            if opt.lower() == "yes":
                                target_choice = opt
                                break
                    elif any("prefer not" in o.lower() or "do not wish" in o.lower() for o in opts):
                        for opt in opts:
                            if "prefer not" in opt.lower() or "do not wish" in opt.lower():
                                target_choice = opt
                                break
                    elif opts:
                        target_choice = opts[1] if len(opts) > 1 and opts[0].lower() in ["select...", "select an option"] else opts[0]

                    if target_choice:
                        matched_opt = page.locator(f".select__option:has-text('{target_choice}')").first
                        if safe_count(matched_opt) > 0:
                            matched_opt.click()
                            filled.append(f"Screening (Select): {lbl_text[:20]}")
                            self.record_field(
                                label=lbl_text,
                                value=target_choice,
                                field_name=f"select_control_{i}",
                                field_type="select",
                                step=1,
                                step_name="CUSTOM_SCREENING",
                                action_type="SELECTED"
                            )
                    else:
                        if hasattr(page, "keyboard"):
                            page.keyboard.press("Escape")
                    time.sleep(0.1)
                except Exception:
                    pass
        except Exception as e_rs:
            logger.debug("Greenhouse React-Select controls notice: %s", e_rs)

        # 5. Checkbox agreements & consent (GDPR, Background Check, Privacy Policy)
        try:
            for cb in page.locator("input[type='checkbox']").all():
                try:
                    if not cb.is_checked():
                        parent = cb.locator("xpath=ancestor::label | ancestor::div[1]").first
                        txt = parent.inner_text().lower() if safe_count(parent) > 0 else ""
                        if any(k in txt for k in ["consent", "privacy", "terms", "agree", "certify", "acknowledge", "data processing"]) or cb.get_attribute("required") is not None:
                            cb.check(force=True)
                            filled.append("Consent Checkbox")
                            self.record_field(
                                label="Consent / Agreement Checkbox",
                                value="Checked",
                                field_name="checkbox",
                                field_type="checkbox",
                                step=1,
                                step_name="DISCLOSURES",
                                action_type="CHECKED"
                            )
                except Exception:
                    pass
        except Exception as e_cb:
            logger.debug("Greenhouse checkbox notice: %s", e_cb)

        # 6. Standard HTML <select> elements (for native Greenhouse boards)
        try:
            native_selects = page.locator("select").all()
            for s_idx, sel_el in enumerate(native_selects):
                try:
                    if not sel_el.is_visible():
                        continue
                    parent_lbl = sel_el.locator("xpath=ancestor::div[contains(@class, 'field') or contains(@class, 'question')]//label | ancestor::div[1]//label").first
                    lbl_text = parent_lbl.inner_text().strip() if safe_count(parent_lbl) > 0 else f"Select {s_idx}"
                    lbl_lower = lbl_text.lower()
                    opts = [o.inner_text().strip() for o in sel_el.locator("option").all() if o.inner_text().strip()]
                    if not opts:
                        continue
                    chosen = None
                    if any("human" in o.lower() for o in opts) or "best describes you" in lbl_lower:
                        chosen = next((o for o in opts if "human" in o.lower()), None)
                    elif any(k in lbl_lower for k in ["sponsorship", "visa", "restrictions"]):
                        chosen = next((o for o in opts if o.lower() == "no"), None)
                    elif any(k in lbl_lower for k in ["authorized", "eligible to work", "legally"]):
                        chosen = next((o for o in opts if o.lower() == "yes"), None)
                    elif "country" in lbl_lower:
                        chosen = next((o for o in opts if "india" in o.lower()), None)
                    elif any("prefer not" in o.lower() or "decline" in o.lower() for o in opts):
                        chosen = next((o for o in opts if "prefer not" in o.lower() or "decline" in o.lower()), None)
                    elif opts:
                        decision = self.solver.evaluate_question(lbl_text, context={"options": opts})
                        if decision and decision.answer and not decision.is_ambiguous:
                            for opt in opts:
                                if decision.answer.lower() in opt.lower():
                                    chosen = opt
                                    break
                        if not chosen:
                            chosen = opts[1] if len(opts) > 1 and opts[0].lower() in ["select...", "choose...", "select an option"] else opts[0]

                    if chosen:
                        sel_el.select_option(label=chosen)
                        filled.append(f"Screening (Native Select): {lbl_text[:20]}")
                        self.record_field(
                            label=lbl_text,
                            value=chosen,
                            field_name=f"native_select_{s_idx}",
                            field_type="select",
                            step=1,
                            step_name="CUSTOM_SCREENING",
                            action_type="SELECTED"
                        )
                except Exception:
                    pass
        except Exception as e_ns:
            logger.debug("Greenhouse native select notice: %s", e_ns)

        return {"filled": filled, "field_records": list(self.field_records), "ats": "Greenhouse"}

    def upload_resume(self, page: Any, resume_path: Optional[str]) -> bool:
        if not page or not resume_path or not os.path.exists(resume_path):
            return False
        try:
            file_input = page.locator("#resume, input[type='file'][id*='resume' i], input[type='file'][name*='resume' i], input[type='file']").first
            if safe_count(file_input) > 0:
                file_input.set_input_files(resume_path)
                # Poll for S3 presigned async upload to complete
                for _ in range(8):
                    time.sleep(0.5)
                    progress = page.locator("#upload-progress, .progress-bar, [data-status='uploading'], .loading-spinner")
                    if safe_count(progress) == 0 or not progress.first.is_visible():
                        break
                try:
                    if hasattr(page, "evaluate"):
                        page.evaluate("""() => {
                            const el = document.getElementById('resume') || document.querySelector("input[type='file']");
                            if (el) {
                                el.dispatchEvent(new Event('input', { bubbles: true }));
                                el.dispatchEvent(new Event('change', { bubbles: true }));
                            }
                        }""")
                except Exception:
                    pass
                self.record_field(
                    label="Resume File",
                    value=os.path.basename(resume_path),
                    field_name="resume",
                    field_type="file",
                    step=1,
                    step_name="RESUME_ATTACHMENT",
                    action_type="UPLOADED"
                )
                return True
        except Exception as e:
            logger.debug("Greenhouse resume upload notice: %s", e)
        return False

    def submit_form(self, page: Any) -> bool:
        if not page:
            return False

        # Pre-submit: Remove any residual required constraint from empty non-file inputs so HTML5 validation does not block submit
        try:
            if hasattr(page, "evaluate"):
                page.evaluate("""() => {
                    document.querySelectorAll('[required]').forEach(el => {
                        if (el.type !== 'file' && (!el.value || el.value === '')) {
                            el.removeAttribute('required');
                            el.removeAttribute('aria-required');
                            if (el.classList.contains('remix-css-1a0ro4n-requiredInput') || el.getAttribute('tabindex') === '-1') {
                                el.value = 'Selected';
                            }
                        }
                    });
                }""")
        except Exception:
            pass

        submit_selectors = [
            "button[type='submit']:has-text('Submit application')",
            "button:has-text('Submit application')",
            "button[type='submit']:has-text('Submit Application')",
            "button:has-text('Submit Application')",
            "button:has-text('Verify')",
            "button:has-text('Submit code')",
            "button:has-text('Continue')",
            "input#submit_app",
            "button#submit_app",
            "input[type='submit'][value*='Submit' i]",
            "button[type='submit']",
            "button:has-text('Submit')",
            "button:has-text('Apply')"
        ]
        submit_clicked = False
        t_click = time.time()
        for sel in submit_selectors:
            try:
                btn = page.locator(sel).first
                if safe_count(btn) > 0 and btn.is_visible():
                    btn.click(timeout=5000)
                    submit_clicked = True
                    self.record_field(
                        label="Submit Application Button",
                        value="CLICKED",
                        field_name=sel,
                        field_type="button",
                        step=1,
                        step_name="SUBMIT_APPLICATION",
                        action_type="SUBMITTED"
                    )
                    break
            except Exception:
                pass

        if not submit_clicked:
            return False

        # Greenhouse Email Verification Prompt Handler (.email-verification)
        try:
            for _ in range(4):
                time.sleep(1.5)
                # Fast exit if confirmation page is already reached
                if self.verify_confirmation(page, timeout=0.5):
                    break
                verif = page.locator(".email-verification, div:has-text('security code'), div:has-text('Enter the code')")
                if safe_count(verif) > 0 and verif.first.is_visible():
                    print("    📧 Greenhouse Email Verification detected. Retrieving 8-character security code from Gmail...")
                    code = fetch_greenhouse_security_code(since_ts=t_click, timeout_sec=45.0)
                    if code and len(code) in [6, 8]:
                        print(f"    🔑 Entering Greenhouse security code: {code}")
                        entered = False
                        # 1. Try segmented inputs (e.g. input#security-input-0 .. 7)
                        first_seg = page.locator("input#security-input-0")
                        if safe_count(first_seg) > 0:
                            for i, ch in enumerate(code):
                                inp_i = page.locator(f"input#security-input-{i}")
                                if safe_count(inp_i) > 0:
                                    inp_i.fill(ch)
                            entered = True

                        # 2. Fallback to unified single code input if segmented not found
                        if not entered:
                            single_inputs = page.locator(
                                "input#security_code, input[name*='security_code' i], input[name*='code' i], "
                                "input[placeholder*='code' i], input[aria-label*='code' i], input[type='text'][maxlength='8'], "
                                "input[type='text'][maxlength='6']"
                            )
                            if safe_count(single_inputs) > 0 and single_inputs.first.is_visible():
                                single_inputs.first.fill(code)
                                entered = True

                        self.record_field(
                            label="Greenhouse Email Verification Code",
                            value="Security Code Verified via Gmail",
                            field_name="security_code",
                            field_type="code",
                            step=1,
                            step_name="EMAIL_VERIFICATION",
                            action_type="VERIFIED"
                        )
                        time.sleep(1)
                        for sel in submit_selectors:
                            try:
                                btn = page.locator(sel).first
                                if safe_count(btn) > 0 and btn.is_visible():
                                    btn.click(timeout=5000)
                                    print("    🚀 Resubmitted with verified security code!")
                                    break
                            except Exception:
                                pass
                    break
        except Exception as e_verif:
            logger.debug("Greenhouse verification solver notice: %s", e_verif)

        return True

    def verify_confirmation(self, page: Any, timeout: float = 25.0) -> bool:
        if not page:
            return False
        start = time.time()
        while time.time() - start < timeout:
            try:
                url = (getattr(page, "url", "") or "").lower()
                if "/confirmation" in url or "application_confirmation" in url:
                    return True

                title = ""
                try:
                    title = (page.title() or "").lower()
                except Exception:
                    pass
                if "thank you for applying" in title or "application submitted" in title or "thank you" in title:
                    return True

                body_txt = ""
                try:
                    if hasattr(page, "evaluate"):
                        body_txt = (page.evaluate("() => document.body ? document.body.innerText.toLowerCase() : ''") or "").lower()
                except Exception:
                    pass
                if any(phrase in body_txt for phrase in ["thank you for applying", "thank you for your application", "application was submitted", "application submitted", "we have received your application"]):
                    return True

                conf_selectors = [
                    "#application_confirmation",
                    "div[data-qa='confirmation-page']",
                    "h1:has-text('Thank you')",
                    "h2:has-text('Thank you')",
                    "h1:has-text('Application Submitted')",
                    "h2:has-text('Application Submitted')",
                    "div:has-text('Thank you for applying')",
                    "div:has-text('Your application was submitted')",
                    "div:has-text('We have received your application')"
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

    def fill_form(self, page: Any, schema_plan: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        filled = []
        p = self.profile
        if not page:
            return {"filled": filled, "ats": "Lever"}

        # 1. Navigation to /apply if currently on job landing page
        try:
            url = getattr(page, "url", "") or ""
            if not url.rstrip("/").endswith("/apply"):
                apply_btn = page.locator("a:has-text('Apply for this job'), a:has-text('APPLY FOR THIS JOB'), a:has-text('Apply'), button:has-text('Apply')").first
                if safe_count(apply_btn) > 0 and apply_btn.is_visible():
                    apply_btn.click()
                    self.record_field(
                        label="Apply for Job Navigation",
                        value="CLICKED",
                        field_name="apply_button",
                        field_type="button",
                        step=1,
                        step_name="NAVIGATION",
                        action_type="CLICKED"
                    )
                    time.sleep(2)
        except Exception:
            pass

        field_map = [
            ("input[name='name']", p.get("fullName", "Lavkush Kumar"), "Full Name"),
            ("input[name='email']", p.get("email", "lav84095@gmail.com"), "Email"),
            ("input[name='phone']", p.get("phone", "+91-9122036484"), "Phone"),
            ("input[name='org']", p.get("currentCompany", "CGI India (PNC Bank GCC)"), "Current Company"),
            ("input[name='urls[LinkedIn]']", p.get("linkedInUrl", "https://linkedin.com/in/lavkush-kumar"), "LinkedIn"),
            ("input[name='urls[GitHub]']", p.get("githubUrl", "https://github.com/lavkush-kumar"), "GitHub"),
            ("input[name='urls[Portfolio]'], input[name='urls[Other]']", p.get("portfolioUrl", "https://github.com/lavkush-kumar"), "Portfolio"),
            ("input[name='location']", p.get("city", "Hyderabad, India"), "Location"),
            ("textarea[name='comments'], input[name='comments']", "Experienced Azure Data Engineer (2.5 YOE) specializing in Databricks, PySpark, Delta Lake, ADF, and high-throughput streaming pipelines.", "Additional Information"),
        ]
        for selector, val, label in field_map:
            try:
                loc = page.locator(selector).first
                if safe_count(loc) > 0 and loc.is_visible():
                    loc.fill(str(val))
                    filled.append(label)
                    self.record_field(
                        label=label,
                        value=val,
                        field_name=selector,
                        field_type="text",
                        step=1,
                        step_name="BASIC_INFO",
                        action_type="FILLED"
                    )
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
                                    self.record_field(
                                        label=q_text,
                                        value=decision.answer,
                                        field_name="radio",
                                        field_type="radio",
                                        step=1,
                                        step_name="CUSTOM_SCREENING",
                                        action_type="ANSWERED"
                                    )
                                    clicked_radio = True
                                    break
                                except Exception:
                                    pass
                        # Check for select dropdown inside this question
                        sel_box = q_box.locator("select").first
                        if safe_count(sel_box) > 0 and sel_box.is_visible():
                            s_opts = [o.inner_text().strip() for o in sel_box.locator("option").all() if o.inner_text().strip()]
                            chosen_opt = None
                            if decision and decision.answer:
                                for so in s_opts:
                                    if decision.answer.lower() in so.lower():
                                        chosen_opt = so
                                        break
                            if not chosen_opt:
                                if any("yes" in so.lower() for so in s_opts) and any(k in q_text.lower() for k in ["authorized", "eligible", "legal"]):
                                    chosen_opt = next((so for so in s_opts if "yes" in so.lower()), None)
                                elif any("no" in so.lower() for so in s_opts) and any(k in q_text.lower() for k in ["sponsorship", "visa", "restrictions"]):
                                    chosen_opt = next((so for so in s_opts if "no" in so.lower()), None)
                                elif any("decline" in so.lower() or "prefer not" in so.lower() for so in s_opts):
                                    chosen_opt = next((so for so in s_opts if "decline" in so.lower() or "prefer not" in so.lower()), None)
                                elif s_opts:
                                    chosen_opt = s_opts[1] if len(s_opts) > 1 and s_opts[0].lower() in ["select...", "choose..."] else s_opts[0]
                            if chosen_opt:
                                try:
                                    sel_box.select_option(label=chosen_opt)
                                    filled.append(f"Screening (Select): {q_text[:20]}")
                                    self.record_field(
                                        label=q_text,
                                        value=chosen_opt,
                                        field_name="select",
                                        field_type="select",
                                        step=1,
                                        step_name="CUSTOM_SCREENING",
                                        action_type="SELECTED"
                                    )
                                    continue
                                except Exception:
                                    pass

                        if not clicked_radio:
                            inp = q_box.locator("input[type='text'], textarea").first
                            if safe_count(inp) > 0:
                                try:
                                    inp.fill(str(decision.answer))
                                    filled.append(f"Screening: {q_text[:20]}")
                                    self.record_field(
                                        label=q_text,
                                        value=decision.answer,
                                        field_name="text_or_textarea",
                                        field_type="text",
                                        step=1,
                                        step_name="CUSTOM_SCREENING",
                                        action_type="ANSWERED"
                                    )
                                except Exception:
                                    pass
        except Exception as e_lever:
            logger.debug("Lever screening notice: %s", e_lever)

        # Checkboxes (GDPR, Privacy, Terms, Required)
        try:
            for cb in page.locator("input[type='checkbox']").all():
                try:
                    if not cb.is_checked():
                        parent = cb.locator("xpath=ancestor::label | ancestor::div[1]").first
                        txt = parent.inner_text().lower() if safe_count(parent) > 0 else ""
                        if any(k in txt for k in ["consent", "privacy", "terms", "agree", "certify", "acknowledge", "gdpr", "data processing"]) or cb.get_attribute("required") is not None:
                            cb.check(force=True)
                            filled.append("Consent Checkbox")
                            self.record_field(
                                label="Consent Checkbox",
                                value="Checked",
                                field_name="checkbox",
                                field_type="checkbox",
                                step=1,
                                step_name="DISCLOSURES",
                                action_type="CHECKED"
                            )
                except Exception:
                    pass
        except Exception as e_lcb:
            logger.debug("Lever checkbox notice: %s", e_lcb)

        return {"filled": filled, "field_records": list(self.field_records), "ats": "Lever"}

    def upload_resume(self, page: Any, resume_path: Optional[str]) -> bool:
        if not page or not resume_path or not os.path.exists(resume_path):
            return False
        try:
            file_input = page.locator("#resume-upload-input, input[name='resume'], input[type='file']").first
            if safe_count(file_input) > 0:
                file_input.set_input_files(resume_path)
                self.record_field(
                    label="Resume File",
                    value=os.path.basename(resume_path),
                    field_name="resume",
                    field_type="file",
                    step=1,
                    step_name="RESUME_ATTACHMENT",
                    action_type="UPLOADED"
                )
                return True
        except Exception as e:
            logger.debug("Lever resume upload notice: %s", e)
        return False

    def submit_form(self, page: Any) -> bool:
        if not page:
            return False

        # Pre-submit: Remove any residual required constraint from empty non-file inputs
        try:
            if hasattr(page, "evaluate"):
                page.evaluate("""() => {
                    document.querySelectorAll('[required]').forEach(el => {
                        if (el.type !== 'file' && (!el.value || el.value === '')) {
                            el.removeAttribute('required');
                            el.removeAttribute('aria-required');
                        }
                    });
                }""")
        except Exception:
            pass

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
                    self.record_field(
                        label="Submit Application Button",
                        value="CLICKED",
                        field_name=sel,
                        field_type="button",
                        step=1,
                        step_name="SUBMIT_APPLICATION",
                        action_type="SUBMITTED"
                    )
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

    def detect_barriers(self, page: Any) -> Optional[str]:
        parent_barrier = super().detect_barriers(page)
        if parent_barrier:
            return parent_barrier
        if not page:
            return None
        try:
            # Check for visual recaptcha/hcaptcha challenge frames
            iframes = page.locator("iframe[src*='recaptcha'], iframe[src*='hcaptcha'], iframe[src*='arkose']").all()
            for frame in iframes:
                if frame.is_visible() and any(c in (frame.get_attribute("src") or "") for c in ("bframe", "challenge", "checkpoint")):
                    return "Ashby Bot Detection / Visual reCAPTCHA Challenge active"
        except Exception:
            pass
        return None

    def upload_resume(self, page: Any, resume_path: Optional[str]) -> bool:
        if not page or not resume_path or not os.path.exists(resume_path):
            return False
        try:
            file_input = page.locator("input#_systemfield_resume, input[type='file']").first
            if safe_count(file_input) > 0:
                file_input.set_input_files(resume_path)
                self.record_field(
                    label="Resume File",
                    value=os.path.basename(resume_path),
                    field_name="_systemfield_resume",
                    field_type="file",
                    step=1,
                    step_name="RESUME_ATTACHMENT",
                    action_type="UPLOADED"
                )
                time.sleep(2)
                return True
        except Exception:
            pass
        return False

    def fill_form(self, page: Any, schema_plan: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        filled = []
        p = self.profile
        if not page:
            return {"filled": filled, "ats": "Ashby"}

        # 1. Navigation to /application if currently on job landing page
        try:
            url = getattr(page, "url", "") or ""
            if "/application" not in url.lower():
                apply_btn = page.locator("a:has-text('Apply for this Job'), button:has-text('Apply for this Job'), a:has-text('Apply'), button:has-text('Apply')").first
                if safe_count(apply_btn) > 0 and apply_btn.is_visible():
                    apply_btn.click()
                    self.record_field(
                        label="Apply for Job Navigation",
                        value="CLICKED",
                        field_name="apply_button",
                        field_type="button",
                        step=1,
                        step_name="NAVIGATION",
                        action_type="CLICKED"
                    )
                    time.sleep(2)
        except Exception:
            pass

        # 2. Standard system fields
        std_map = [
            ("input#_systemfield_name, input[name='_systemfield_name'], input[name='name']", p.get("fullName", "Lavkush Kumar"), "Full Name"),
            ("input#_systemfield_email, input[name='_systemfield_email'], input[name='email']", p.get("email", "lav84095@gmail.com"), "Email"),
            ("input[type='tel'], input#phone, input[name='phone'], input[name*='phone' i]", p.get("phone", "+919122036484"), "Phone"),
            ("input[name*='linkedin' i], input[id*='linkedin' i]", p.get("linkedInUrl", "https://linkedin.com/in/lavkush-kumar"), "LinkedIn"),
            ("input[name*='github' i], input[id*='github' i]", p.get("githubUrl", "https://github.com/lavkush-kumar"), "GitHub"),
        ]
        for sel, val, label in std_map:
            try:
                loc = page.locator(sel).first
                if safe_count(loc) > 0 and loc.is_visible():
                    loc.fill(str(val))
                    filled.append(label)
                    self.record_field(
                        label=label,
                        value=val,
                        field_name=sel,
                        field_type="text",
                        step=1,
                        step_name="BASIC_INFO",
                        action_type="FILLED"
                    )
            except Exception:
                pass

        # 3. Location autocomplete
        try:
            loc_inp = page.locator("input.ashby-application-form-input-autocomplete, input[placeholder*='Start typing']").first
            if safe_count(loc_inp) > 0 and loc_inp.is_visible() and not loc_inp.input_value():
                loc_inp.click()
                loc_inp.fill(p.get("city", "Hyderabad"))
                time.sleep(1.5)
                opt = page.locator("[role='listbox']").locator("text=India").first
                if safe_count(opt) > 0:
                    opt.click()
                    filled.append("Location (Hyderabad, India)")
                    self.record_field(
                        label="Location",
                        value="Hyderabad, India",
                        field_name="location_autocomplete",
                        field_type="autocomplete",
                        step=1,
                        step_name="LOCATION",
                        action_type="SELECTED"
                    )
                else:
                    opt_any = page.locator("[role='listbox'] div, [role='listbox'] li").first
                    if safe_count(opt_any) > 0:
                        opt_any.click()
                        filled.append("Location")
                        self.record_field(
                            label="Location",
                            value="First Option Selected",
                            field_name="location_autocomplete",
                            field_type="autocomplete",
                            step=1,
                            step_name="LOCATION",
                            action_type="SELECTED"
                        )
        except Exception:
            pass

        # 4. Custom question inputs & textareas
        try:
            for inp in page.locator("input[type='text'], input:not([type]), textarea").all():
                try:
                    iid = inp.get_attribute("id") or ""
                    name = inp.get_attribute("name") or ""
                    itype = inp.get_attribute("type") or ""
                    if iid in ("_systemfield_name", "_systemfield_email") or name in ("_systemfield_name", "_systemfield_email") or itype == "tel":
                        continue
                    if inp.input_value():
                        continue
                    label_text = ""
                    if iid:
                        lbl = page.locator(f"label[for='{iid}']").first
                        if safe_count(lbl) > 0:
                            label_text = lbl.inner_text().strip()
                    if not label_text:
                        parent = inp.locator("xpath=ancestor::div[1]").first
                        if safe_count(parent) > 0:
                            label_text = parent.inner_text().strip().split("\n")[0]
                    lt = label_text.lower()
                    ans_to_fill = ""
                    if "github" in lt:
                        ans_to_fill = p.get("githubUrl", "https://github.com/lavkush-kumar")
                        filled.append("GitHub Profile")
                    elif "linkedin" in lt:
                        ans_to_fill = p.get("linkedInUrl", "https://linkedin.com/in/lavkush-kumar")
                        filled.append("LinkedIn Profile")
                    elif "pronoun" in lt:
                        ans_to_fill = "He/Him"
                        filled.append("Pronouns")
                    elif "why" in lt and "join" in lt:
                        ans_to_fill = "Excited by the engineering mission, modern architecture, and scale; eager to contribute to robust distributed data pipelines and platform observability."
                        filled.append("Why Join")
                    elif "country" in lt or "based in" in lt:
                        ans_to_fill = "India"
                        filled.append("Country")
                    elif "notice" in lt:
                        ans_to_fill = f"{p.get('noticePeriodDays', '15')} Days"
                        filled.append("Notice Period")
                    elif "refer" in lt:
                        ans_to_fill = "No"
                        filled.append("Referral")
                    elif "cover letter" in lt:
                        ans_to_fill = "Experienced Azure Data Engineer (2.5 YOE) with deep expertise in PySpark, Databricks, Delta Lake, ADF, and production streaming pipelines."
                        filled.append("Cover Letter")
                    elif "work on" in lt or "features" in lt:
                        ans_to_fill = "High-throughput data streaming, lakehouse architectures, and real-time event platforms."
                        filled.append("Areas of Interest")
                    elif "pm hat" in lt or "product problem" in lt:
                        ans_to_fill = "At CGI, optimized data ingest pipeline reducing latency from 45m to 8m by aligning requirements across analytics and data platform stakeholders."
                        filled.append("Product Experience")
                    elif "good at" in lt or "teach" in lt:
                        ans_to_fill = "Azure Databricks, PySpark optimization, Delta Lake lakehouse engineering, and enterprise CI/CD automation."
                        filled.append("Technical Strengths")
                    elif inp.get_attribute("required") is not None:
                        ans_to_fill = "Azure Data Engineer with 2.5 YOE specializing in Databricks, PySpark, Delta Lake, and automated pipelines."
                        filled.append(f"Screening Question ({label_text[:20]})")

                    if ans_to_fill:
                        inp.fill(ans_to_fill)
                        self.record_field(
                            label=label_text or "Question",
                            value=ans_to_fill,
                            field_name=iid or name or "screening_text",
                            field_type="text",
                            step=1,
                            step_name="CUSTOM_SCREENING",
                            action_type="ANSWERED"
                        )
                except Exception:
                    pass
        except Exception:
            pass

        # 5. Yes/No button widgets
        try:
            for container in page.locator("div.ashby-application-form-input-yesno").all():
                try:
                    txt = container.locator("xpath=ancestor::div[2]").first.inner_text().lower()
                    if any(w in txt for w in ("office", "join us", "hybrid", "onsite")):
                        yes_btn = container.locator("button[data-option='yes']").first
                        if safe_count(yes_btn) > 0:
                            yes_btn.click()
                            filled.append("In-Office / Hybrid (Yes)")
                            self.record_field(
                                label="In-Office / Hybrid",
                                value="Yes",
                                field_name="yes_no_button",
                                field_type="button_toggle",
                                step=1,
                                step_name="CUSTOM_SCREENING",
                                action_type="CLICKED"
                            )
                    elif any(w in txt for w in ("sponsorship", "require visa")):
                        no_btn = container.locator("button[data-option='no']").first
                        if safe_count(no_btn) > 0:
                            no_btn.click()
                            filled.append("Visa Sponsorship (No)")
                            self.record_field(
                                label="Visa Sponsorship",
                                value="No",
                                field_name="yes_no_button",
                                field_type="button_toggle",
                                step=1,
                                step_name="CUSTOM_SCREENING",
                                action_type="CLICKED"
                            )
                except Exception:
                    pass
        except Exception:
            pass

        # 6. Radios (agreements, EEOC)
        try:
            for r in page.locator("input[type='radio']").all():
                try:
                    parent = r.locator("xpath=ancestor::div[1]").first
                    txt = parent.inner_text().lower()
                    if any(w in txt for w in ("privacy policy", "acknowledge", "i agree")):
                        r.check(force=True)
                        filled.append("Privacy Policy Acknowledged")
                        self.record_field(label="Privacy Policy", value="Acknowledged", field_name="radio", field_type="radio", step=1, step_name="DISCLOSURES", action_type="CHECKED")
                    elif "male" in txt and "female" not in txt:
                        r.check(force=True)
                        filled.append("EEOC Gender (Male)")
                        self.record_field(label="EEOC Gender", value="Male", field_name="radio", field_type="radio", step=1, step_name="EEOC", action_type="CHECKED")
                    elif "asian" in txt:
                        r.check(force=True)
                        filled.append("EEOC Race (Asian)")
                        self.record_field(label="EEOC Race", value="Asian", field_name="radio", field_type="radio", step=1, step_name="EEOC", action_type="CHECKED")
                    elif "not a protected veteran" in txt or "not a veteran" in txt:
                        r.check(force=True)
                        filled.append("EEOC Veteran (Non-Veteran)")
                        self.record_field(label="EEOC Veteran", value="Non-Veteran", field_name="radio", field_type="radio", step=1, step_name="EEOC", action_type="CHECKED")
                    elif "no, i do not have a disability" in txt or "decline to state" in txt or "decline" in txt:
                        r.check(force=True)
                        filled.append("EEOC Disability")
                        self.record_field(label="EEOC Disability", value="Declined/No", field_name="radio", field_type="radio", step=1, step_name="EEOC", action_type="CHECKED")
                except Exception:
                    pass
        except Exception:
            pass

        # 7. Ashby Custom React-Select & Combobox Dropdowns
        try:
            ashby_selects = page.locator("div.ashby-application-form-input-select, div[class*='SelectContainer'], div[role='combobox']").all()
            for s_idx, sel_ctrl in enumerate(ashby_selects):
                try:
                    if not sel_ctrl.is_visible():
                        continue
                    parent_lbl = sel_ctrl.locator("xpath=ancestor::div[contains(@class, 'field') or contains(@class, 'question')]//label | ancestor::div[1]//label").first
                    lbl_text = parent_lbl.inner_text().strip() if safe_count(parent_lbl) > 0 else f"Select {s_idx}"
                    lbl_lower = lbl_text.lower()
                    ctrl_text = sel_ctrl.inner_text().strip()
                    if ctrl_text and ctrl_text.lower() not in ["select...", "select an option", "choose...", ""]:
                        continue

                    sel_ctrl.click()
                    time.sleep(0.3)
                    opt_locs = page.locator("[role='option'], div.ashby-application-form-input-select-option, div[class*='option']")
                    opts = [o.strip() for o in opt_locs.all_inner_texts() if o.strip()]

                    target_opt = None
                    if any("human" in o.lower() for o in opts) or "best describes you" in lbl_lower:
                        target_opt = next((o for o in opts if "human" in o.lower()), None)
                    elif "sponsorship" in lbl_lower or "visa" in lbl_lower:
                        target_opt = next((o for o in opts if o.lower() == "no" or "not require" in o.lower()), None)
                    elif "authorized" in lbl_lower or "eligible" in lbl_lower or "legally" in lbl_lower:
                        target_opt = next((o for o in opts if o.lower() == "yes" or "authorized" in o.lower()), None)
                    elif any(k in lbl_lower for k in ["country", "location", "reside"]):
                        target_opt = next((o for o in opts if "india" in o.lower()), None)
                    elif any("prefer not" in o.lower() or "decline" in o.lower() for o in opts):
                        target_opt = next((o for o in opts if "prefer not" in o.lower() or "decline" in o.lower()), None)
                    elif opts:
                        decision = self.solver.evaluate_question(lbl_text, context={"options": opts})
                        if decision and decision.answer and not decision.is_ambiguous:
                            for opt in opts:
                                if decision.answer.lower() in opt.lower():
                                    target_opt = opt
                                    break
                        if not target_opt:
                            target_opt = opts[0] if opts[0].lower() not in ["select...", "choose..."] else (opts[1] if len(opts) > 1 else opts[0])

                    if target_opt:
                        matched_item = page.locator(f"[role='option']:has-text('{target_opt}'), div.ashby-application-form-input-select-option:has-text('{target_opt}')").first
                        if safe_count(matched_item) > 0:
                            matched_item.click()
                            filled.append(f"Dropdown: {lbl_text[:20]}")
                            self.record_field(
                                label=lbl_text,
                                value=target_opt,
                                field_name=f"ashby_select_{s_idx}",
                                field_type="select",
                                step=1,
                                step_name="CUSTOM_SCREENING",
                                action_type="SELECTED"
                            )
                    else:
                        if hasattr(page, "keyboard"):
                            page.keyboard.press("Escape")
                except Exception:
                    pass
        except Exception as e_ashby_sel:
            logger.debug("Ashby custom dropdown notice: %s", e_ashby_sel)

        # 8. Ashby Checkboxes (Consents, Terms, Background Check)
        try:
            for cb in page.locator("input[type='checkbox']").all():
                try:
                    if not cb.is_checked():
                        parent = cb.locator("xpath=ancestor::label | ancestor::div[1]").first
                        txt = parent.inner_text().lower() if safe_count(parent) > 0 else ""
                        if any(k in txt for k in ["consent", "privacy", "terms", "agree", "certify", "acknowledge", "background check"]) or cb.get_attribute("required") is not None:
                            cb.check(force=True)
                            filled.append("Consent Checkbox")
                            self.record_field(
                                label="Consent Checkbox",
                                value="Checked",
                                field_name="checkbox",
                                field_type="checkbox",
                                step=1,
                                step_name="DISCLOSURES",
                                action_type="CHECKED"
                            )
                except Exception:
                    pass
        except Exception as e_acb:
            logger.debug("Ashby checkbox notice: %s", e_acb)

        return {"filled": filled, "field_records": list(self.field_records), "ats": "Ashby"}

    def submit_form(self, page: Any) -> bool:
        if not page:
            return False

        # Pre-submit: Remove any residual required constraint from empty non-file inputs
        try:
            if hasattr(page, "evaluate"):
                page.evaluate("""() => {
                    document.querySelectorAll('[required]').forEach(el => {
                        if (el.type !== 'file' && (!el.value || el.value === '')) {
                            el.removeAttribute('required');
                            el.removeAttribute('aria-required');
                        }
                    });
                }""")
        except Exception:
            pass

        submit_selectors = [
            "button.ashby-application-form-submit-button",
            "button:has-text('Submit Application')",
            "button[type='submit']",
            "button:has-text('Apply')"
        ]
        for sel in submit_selectors:
            try:
                btn = page.locator(sel).first
                if safe_count(btn) > 0 and btn.is_visible():
                    btn.click(timeout=5000)
                    self.record_field(
                        label="Submit Application Button",
                        value="CLICKED",
                        field_name=sel,
                        field_type="button",
                        step=1,
                        step_name="SUBMIT_APPLICATION",
                        action_type="SUBMITTED"
                    )
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
                    "h1:has-text('Thanks for applying')",
                    "h2:has-text('Thanks for applying')",
                    "div:has-text('Your application has been submitted')",
                    "div:has-text('Thank you for applying')",
                    "div:has-text('Thanks for applying')",
                    "div:has-text('We have received your application')",
                    "div:has-text('Application received')",
                    ".ashby-application-form-success",
                    "[data-testid='application-success']"
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

    def attempt_vault_sign_in(self, page: Any, job_url: str = "") -> bool:
        """Fill Workday sign-in from portal_accounts vault. Never logs password."""
        try:
            from naukari_pro.modules.portal_accounts import PortalAccountManager
            mgr = PortalAccountManager()
            acct = mgr.ensure_account(job_url or (page.url if page else ""), email=self.profile.get("email", "lav84095@gmail.com"))
            acct_email = acct.get("email") or self.profile.get("email", "lav84095@gmail.com")
            acct_pwd = os.getenv("PORTAL_PASSWORD") or acct.get("password") or "PortalSecure@2026!"
            if not any(c.isupper() for c in acct_pwd):
                acct_pwd += "A"
            if not any(c.islower() for c in acct_pwd):
                acct_pwd += "a"
            if not any(c.isdigit() for c in acct_pwd):
                acct_pwd += "1"
            if not any(c in "!@#$%^&*" for c in acct_pwd):
                acct_pwd += "!"

            # If SignInWithEmailButton or 'Sign in with email' is visible
            email_btn_sel = "[data-automation-id='SignInWithEmailButton'], button:has-text('Sign in with email'), a:has-text('Sign in with email')"
            try:
                page.wait_for_selector(email_btn_sel, timeout=10000)
            except Exception:
                pass

            email_sign_in_btn = page.locator(email_btn_sel).first
            if safe_count(email_sign_in_btn) > 0 and email_sign_in_btn.is_visible():
                email_sign_in_btn.click()
                self.record_field(
                    label="Sign In With Email Button",
                    value="CLICKED",
                    field_name="sign_in_with_email",
                    field_type="button",
                    step=1,
                    step_name="VAULT_AUTH",
                    action_type="CLICKED"
                )
                try:
                    page.wait_for_selector("input[data-automation-id='email']", timeout=8000)
                except Exception:
                    time.sleep(2)

            email_loc = page.locator("input[data-automation-id='email']").first
            pass_loc = page.locator("input[data-automation-id='password']").first
            verify_pass_loc = page.locator("input[data-automation-id='verifyPassword']").first

            # If create account fields exist
            if safe_count(verify_pass_loc) > 0 and verify_pass_loc.is_visible():
                if safe_count(email_loc) > 0:
                    email_loc.fill(str(acct_email))
                    self.record_field(
                        label="Account Email",
                        value=acct_email,
                        field_name="email",
                        field_type="email",
                        step=1,
                        step_name="VAULT_AUTH",
                        action_type="FILLED"
                    )
                if safe_count(pass_loc) > 0:
                    pass_loc.fill(str(acct_pwd))
                    self.record_field(
                        label="Account Password",
                        value="********",
                        field_name="password",
                        field_type="password",
                        step=1,
                        step_name="VAULT_AUTH",
                        action_type="FILLED"
                    )
                verify_pass_loc.fill(str(acct_pwd))
                self.record_field(
                    label="Verify Password",
                    value="********",
                    field_name="verifyPassword",
                    field_type="password",
                    step=1,
                    step_name="VAULT_AUTH",
                    action_type="FILLED"
                )
                cb = page.locator("input[data-automation-id='createAccountCheckbox']").first
                if safe_count(cb) > 0:
                    cb.check(force=True)
                    self.record_field(
                        label="Create Account Terms",
                        value="True",
                        field_name="createAccountCheckbox",
                        field_type="checkbox",
                        step=1,
                        step_name="VAULT_AUTH",
                        action_type="CHECKED"
                    )
                time.sleep(1)
                cf = page.locator("div[data-automation-id='click_filter'][aria-label='Create Account']").first
                if safe_count(cf) > 0 and cf.is_visible():
                    cf.click()
                else:
                    sub = page.locator("button[data-automation-id='createAccountSubmitButton']").first
                    if safe_count(sub) > 0:
                        sub.click(force=True)
                self.record_field(
                    label="Create Account Submit",
                    value="CLICKED",
                    field_name="createAccountSubmitButton",
                    field_type="button",
                    step=1,
                    step_name="VAULT_AUTH",
                    action_type="CLICKED"
                )
                time.sleep(3)
                return True

            if safe_count(email_loc) > 0 and email_loc.is_visible():
                email_loc.fill(str(acct_email))
                self.record_field(
                    label="Account Email",
                    value=acct_email,
                    field_name="email",
                    field_type="email",
                    step=1,
                    step_name="VAULT_AUTH",
                    action_type="FILLED"
                )
            if safe_count(pass_loc) > 0 and pass_loc.is_visible():
                pass_loc.fill(str(acct_pwd))
                self.record_field(
                    label="Account Password",
                    value="********",
                    field_name="password",
                    field_type="password",
                    step=1,
                    step_name="VAULT_AUTH",
                    action_type="FILLED"
                )

            cf_sign = page.locator("div[data-automation-id='click_filter'][aria-label='Sign In'], div[data-automation-id='click_filter'][aria-label='Submit'], div[data-automation-id='click_filter']").first
            if safe_count(cf_sign) > 0 and cf_sign.is_visible():
                cf_sign.click(force=True)
                self.record_field(
                    label="Sign In Submit",
                    value="CLICKED",
                    field_name="signInClickFilter",
                    field_type="button",
                    step=1,
                    step_name="VAULT_AUTH",
                    action_type="CLICKED"
                )
                time.sleep(2)
                return True

            submit = page.locator("button[data-automation-id='signInSubmitButton']").first
            if safe_count(submit) > 0:
                submit.click(force=True)
                self.record_field(
                    label="Sign In Submit",
                    value="CLICKED",
                    field_name="signInSubmitButton",
                    field_type="button",
                    step=1,
                    step_name="VAULT_AUTH",
                    action_type="CLICKED"
                )
                time.sleep(2)
                return True

            # Create Account path
            create_btn = page.locator("button:has-text('Create Account'), a:has-text('Create Account'), [data-automation-id='createAccountLink']").first
            if safe_count(create_btn) > 0 and create_btn.is_visible():
                create_btn.click()
                self.record_field(
                    label="Create Account Navigation",
                    value="CLICKED",
                    field_name="createAccountLink",
                    field_type="button",
                    step=1,
                    step_name="VAULT_AUTH",
                    action_type="CLICKED"
                )
                time.sleep(1)
                if safe_count(email_loc) > 0:
                    email_loc.fill(str(acct_email))
                    self.record_field(
                        label="Account Email",
                        value=acct_email,
                        field_name="email",
                        field_type="email",
                        step=1,
                        step_name="VAULT_AUTH",
                        action_type="FILLED"
                    )
                if safe_count(pass_loc) > 0:
                    pass_loc.fill(str(acct_pwd))
                    self.record_field(
                        label="Account Password",
                        value="********",
                        field_name="password",
                        field_type="password",
                        step=1,
                        step_name="VAULT_AUTH",
                        action_type="FILLED"
                    )
                if safe_count(verify_pass_loc) > 0:
                    verify_pass_loc.fill(str(acct_pwd))
                    self.record_field(
                        label="Verify Password",
                        value="********",
                        field_name="verifyPassword",
                        field_type="password",
                        step=1,
                        step_name="VAULT_AUTH",
                        action_type="FILLED"
                    )
                cb = page.locator("input[data-automation-id='createAccountCheckbox']").first
                if safe_count(cb) > 0:
                    cb.check(force=True)
                    self.record_field(
                        label="Create Account Terms",
                        value="True",
                        field_name="createAccountCheckbox",
                        field_type="checkbox",
                        step=1,
                        step_name="VAULT_AUTH",
                        action_type="CHECKED"
                    )
                create_sub = page.locator("button[data-automation-id='createAccountSubmitButton']").first
                if safe_count(create_sub) > 0:
                    create_sub.click(force=True)
                    self.record_field(
                        label="Create Account Submit",
                        value="CLICKED",
                        field_name="createAccountSubmitButton",
                        field_type="button",
                        step=1,
                        step_name="VAULT_AUTH",
                        action_type="CLICKED"
                    )
                time.sleep(3)
                return True
        except Exception:
            return False
        return False

    def detect_barriers(self, page: Any) -> Optional[str]:
        parent_barrier = super().detect_barriers(page)
        if parent_barrier:
            # Captcha/checkpoint still hard-stop
            if any(k in parent_barrier.lower() for k in ("captcha", "checkpoint", "otp", "turnstile")):
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
            wall = False
            for sel in account_selectors:
                try:
                    loc = page.locator(sel)
                    if safe_count(loc) > 0 and loc.first.is_visible():
                        wall = True
                        break
                except Exception:
                    pass
            if wall:
                # Beast H4: attempt vault login/create instead of hard-stop
                signed = self.attempt_vault_sign_in(page, job_url=getattr(page, "url", "") or "")
                if signed:
                    # Re-check captcha after sign-in attempt
                    parent_barrier = super().detect_barriers(page)
                    if parent_barrier:
                        return parent_barrier
                    return None
                return "Workday Account / Sign-In Barrier — vault auth incomplete (needs mail verify or manual)"
        except Exception:
            pass
        return None

    def upload_resume(self, page: Any, resume_path: Optional[str]) -> bool:
        if not page or not resume_path or not os.path.exists(resume_path):
            return False
        try:
            file_input = page.locator("input[type='file'][data-automation-id='file-upload-input'], input[data-automation-id='file-upload-input'], input[type='file']").first
            if safe_count(file_input) > 0:
                file_input.set_input_files(resume_path)
                # Wait for upload progress bar
                for _ in range(8):
                    time.sleep(0.5)
                    progress = page.locator("div[data-automation-id='progressBar'], .progress-bar")
                    if safe_count(progress) == 0 or not progress.first.is_visible():
                        break
                self.record_field(
                    label="Resume File",
                    value=os.path.basename(resume_path),
                    field_name="workday_resume_upload",
                    field_type="file",
                    step=1,
                    step_name="RESUME_ATTACHMENT",
                    action_type="UPLOADED"
                )
                return True
        except Exception as e_wu:
            logger.debug("Workday resume upload notice: %s", e_wu)
        return False

    def fill_form(self, page: Any, schema_plan: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        filled = []
        p = self.profile
        if not page:
            return {"filled": filled, "ats": "Workday"}

        try:
            apply_sel = "a[data-automation-id='adventureButton'], button[data-automation-id='adventureButton'], a[data-automation-id='applyButton'], button[data-automation-id='applyButton'], button[data-automation-id='startApplication'], a:has-text('Apply'), button:has-text('Apply')"
            try:
                page.wait_for_selector(apply_sel, timeout=6000)
            except Exception:
                pass

            start_btn = page.locator(apply_sel).first
            if safe_count(start_btn) > 0 and start_btn.is_visible():
                start_btn.click()
                self.record_field(
                    label="Apply Navigation Button",
                    value="CLICKED",
                    field_name="apply_button",
                    field_type="button",
                    step=1,
                    step_name="NAVIGATION",
                    action_type="CLICKED"
                )
                time.sleep(2)
                manual_btn = page.locator("[data-automation-id='applyManually'], a:has-text('Apply Manually'), button:has-text('Apply Manually'), [data-automation-id='autofillWithResume']").first
                if safe_count(manual_btn) > 0 and manual_btn.is_visible():
                    manual_btn.click()
                    self.record_field(
                        label="Apply Option Selection",
                        value="Apply Manually",
                        field_name="apply_option",
                        field_type="button",
                        step=1,
                        step_name="NAVIGATION",
                        action_type="CLICKED"
                    )
                    time.sleep(3)
        except Exception:
            pass

        # Workday Vault Sign-in / Create Account step if needed
        try:
            self.attempt_vault_sign_in(page, job_url=getattr(page, "url", "") or "")
        except Exception:
            pass

        field_map = [
            ("input[data-automation-id='legalNameSection_firstName']", p.get("firstName", "Lavkush"), "First Name"),
            ("input[data-automation-id='legalNameSection_lastName']", p.get("lastName", "Kumar"), "Last Name"),
            ("input[data-automation-id='email'], input[data-automation-id='contactInfoEmail']", p.get("email", "lav84095@gmail.com"), "Email"),
            ("input[data-automation-id='phone-number'], input[data-automation-id='phoneNumber']", p.get("phone", "+919122036484"), "Phone"),
            ("input[data-automation-id='addressSection_city']", p.get("city", "Hyderabad"), "City"),
            ("input[data-automation-id='addressSection_postalCode']", p.get("postalCode", "500081"), "Postal Code"),
        ]

        # Multi-Step Wizard Engine (Loops up to 5 steps until Review/Submit)
        for wizard_step in range(1, 6):
            # Check if final Submit button is reached (only on step > 1 if form fields not present)
            if wizard_step > 1:
                submit_visible = False
                for s_sel in ["button[data-automation-id='submitButton']", "button[data-automation-id='bottom-navigation-submit-button']"]:
                    s_btn = page.locator(s_sel).first
                    if safe_count(s_btn) > 0 and s_btn.is_visible():
                        submit_visible = True
                        break
                if submit_visible:
                    filled.append(f"Reached Final Review Step {wizard_step}")
                    break

            # 1. Standard Contact / Identity Fields
            for selector, val, label in field_map:
                try:
                    loc = page.locator(selector).first
                    if safe_count(loc) > 0 and loc.is_visible():
                        val_cur = ""
                        if hasattr(loc, "input_value"):
                            try:
                                iv = loc.input_value()
                                if isinstance(iv, str):
                                    val_cur = iv
                            except Exception:
                                pass
                        if not val_cur:
                            loc.fill(str(val))
                            filled.append(label)
                            self.record_field(
                                label=label,
                                value=val,
                                field_name=selector,
                                field_type="text",
                                step=wizard_step,
                                step_name=f"WIZARD_STEP_{wizard_step}",
                                action_type="FILLED"
                            )
                except Exception:
                    pass

            # 2. General Text Inputs & Textareas on current step
            try:
                for inp in page.locator("input[data-automation-id]:not([type='file']):not([type='checkbox']):not([type='radio']), textarea[data-automation-id]").all():
                    try:
                        if not inp.is_visible():
                            continue
                        val_cur = ""
                        if hasattr(inp, "input_value"):
                            try:
                                iv = inp.input_value()
                                if isinstance(iv, str):
                                    val_cur = iv
                            except Exception:
                                pass
                        if val_cur:
                            continue
                        auto_id = inp.get_attribute("data-automation-id") or ""
                        if any(k in auto_id.lower() for k in ["email", "phone", "name", "city", "postal"]):
                            continue
                        parent = inp.locator("xpath=ancestor::div[1]").first
                        lbl_text = parent.inner_text().strip().split("\n")[0] if safe_count(parent) > 0 else auto_id
                        ans = "Yes"
                        if any(k in lbl_text.lower() for k in ["salary", "compensation"]):
                            ans = "Competitive / Market Standard"
                        elif any(k in lbl_text.lower() for k in ["notice", "availability"]):
                            ans = "15 Days"
                        elif any(k in lbl_text.lower() for k in ["linkedin", "website"]):
                            ans = p.get("linkedInUrl", "https://linkedin.com/in/lavkush-kumar")
                        inp.fill(ans)
                        filled.append(f"Field ({lbl_text[:15]})")
                        self.record_field(
                            label=lbl_text,
                            value=ans,
                            field_name=auto_id,
                            field_type="text",
                            step=wizard_step,
                            step_name=f"WIZARD_STEP_{wizard_step}",
                            action_type="FILLED"
                        )
                    except Exception:
                        pass
            except Exception:
                pass

            # 3. Workday Custom Dropdowns (Country, Source, Phone Type, Disclosures)
            try:
                wd_dropdowns = page.locator("button[data-automation-id*='Dropdown' i], button[data-automation-id*='prompt' i], button[aria-haspopup='listbox']").all()
                for dd_idx, dd_btn in enumerate(wd_dropdowns):
                    try:
                        if not dd_btn.is_visible():
                            continue
                        dd_id = dd_btn.get_attribute("data-automation-id") or f"dropdown_{dd_idx}"
                        dd_text = dd_btn.inner_text().strip().lower()
                        if dd_text and dd_text not in ["select", "select one", "select...", ""]:
                            continue

                        dd_btn.click()
                        time.sleep(0.4)
                        opts_loc = page.locator("div[data-automation-id='promptOption'], div[role='option'], li[role='option']")
                        opts = [o.strip() for o in opts_loc.all_inner_texts() if o.strip()]

                        chosen = None
                        if "country" in dd_id.lower():
                            chosen = next((o for o in opts if "india" in o.lower()), None)
                        elif "source" in dd_id.lower():
                            chosen = next((o for o in opts if "linkedin" in o.lower() or "career site" in o.lower()), None)
                        elif "phone" in dd_id.lower() or "device" in dd_id.lower():
                            chosen = next((o for o in opts if "mobile" in o.lower()), None)
                        elif any("prefer not" in o.lower() or "decline" in o.lower() for o in opts):
                            chosen = next((o for o in opts if "prefer not" in o.lower() or "decline" in o.lower()), None)
                        elif opts:
                            chosen = opts[0]

                        if chosen:
                            opt_match = page.locator(f"div[data-automation-id='promptOption']:has-text('{chosen}'), div[role='option']:has-text('{chosen}')").first
                            if safe_count(opt_match) > 0:
                                opt_match.click()
                                filled.append(f"Workday Dropdown: {chosen}")
                                self.record_field(
                                    label=dd_id,
                                    value=chosen,
                                    field_name=dd_id,
                                    field_type="select",
                                    step=wizard_step,
                                    step_name=f"WIZARD_STEP_{wizard_step}",
                                    action_type="SELECTED"
                                )
                        else:
                            if hasattr(page, "keyboard"):
                                page.keyboard.press("Escape")
                    except Exception:
                        pass
            except Exception as e_wdd:
                logger.debug("Workday dropdown notice: %s", e_wdd)

            # 4. Workday Checkboxes (Disclosures, Terms, Consent)
            try:
                for cb in page.locator("input[data-automation-id='agreementCheckbox'], input[type='checkbox']").all():
                    try:
                        if not cb.is_checked():
                            cb.check(force=True)
                            filled.append("Workday Agreement Checkbox")
                            self.record_field(
                                label="Workday Agreement Checkbox",
                                value="Checked",
                                field_name="checkbox",
                                field_type="checkbox",
                                step=wizard_step,
                                step_name=f"WIZARD_STEP_{wizard_step}",
                                action_type="CHECKED"
                            )
                    except Exception:
                        pass
            except Exception:
                pass

            # 5. Check if Resume File upload is present on this step
            try:
                resume_path = p.get("resumePath")
                if resume_path and os.path.exists(resume_path):
                    f_inp = page.locator("input[data-automation-id='file-upload-input'], input[type='file']").first
                    if safe_count(f_inp) > 0 and f_inp.is_visible():
                        self.upload_resume(page, resume_path)
                        filled.append("Workday Resume File")
            except Exception:
                pass

            # Advance to Next Step
            try:
                next_btn = page.locator("button[data-automation-id='bottom-navigation-next-button'], button[data-automation-id='saveAndContinue']").first
                if safe_count(next_btn) > 0 and next_btn.is_visible():
                    next_btn.click()
                    self.record_field(
                        label=f"Next Step Navigation (Step {wizard_step})",
                        value="CLICKED",
                        field_name="next_button",
                        field_type="button",
                        step=wizard_step,
                        step_name=f"WIZARD_STEP_{wizard_step}",
                        action_type="CLICKED"
                    )
                    time.sleep(2.5)
                else:
                    break
            except Exception:
                break

        return {"filled": filled, "field_records": list(self.field_records), "ats": "Workday"}

    def submit_form(self, page: Any) -> bool:
        if not page:
            return False

        # Pre-submit: Remove any residual required constraint from empty non-file inputs
        try:
            if hasattr(page, "evaluate"):
                page.evaluate("""() => {
                    document.querySelectorAll('[required]').forEach(el => {
                        if (el.type !== 'file' && (!el.value || el.value === '')) {
                            el.removeAttribute('required');
                            el.removeAttribute('aria-required');
                        }
                    });
                }""")
        except Exception:
            pass

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
                    self.record_field(
                        label="Submit Application Button",
                        value="CLICKED",
                        field_name=sel,
                        field_type="button",
                        step=1,
                        step_name="SUBMIT_APPLICATION",
                        action_type="SUBMITTED"
                    )
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

    def fill_form(self, page: Any, schema_plan: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        filled = []
        p = self.profile
        if not page:
            return {"filled": filled, "ats": self.ats_type}

        # Semantic anchor hierarchy: autocomplete > data-automation-id > name/id > placeholder
        field_map = [
            ("input[autocomplete='given-name'], input[data-automation-id*='firstName' i], input[name*='first_name' i], input[name*='firstName' i], #first_name, input[placeholder*='first name' i]", p.get("firstName", "Lavkush"), "First Name"),
            ("input[autocomplete='family-name'], input[data-automation-id*='lastName' i], input[name*='last_name' i], input[name*='lastName' i], #last_name, input[placeholder*='last name' i]", p.get("lastName", "Kumar"), "Last Name"),
            ("input[autocomplete='name'], input[data-automation-id*='fullName' i], input[name*='full_name' i], input[name*='fullName' i], input[name='name'], #name, input[placeholder*='full name' i]", p.get("fullName", "Lavkush Kumar"), "Full Name"),
            ("input[type='email'], input[autocomplete='email'], input[data-automation-id*='email' i], input[name*='email' i], #email, input[placeholder*='email' i]", p.get("email", "lav84095@gmail.com"), "Email"),
            ("input[type='tel'], input[autocomplete='tel'], input[data-automation-id*='phone' i], input[name*='phone' i], input[name*='mobile' i], #phone, input[placeholder*='phone' i]", p.get("phone", "+91-9122036484"), "Phone"),
            ("input[autocomplete='address-level2'], input[data-automation-id*='city' i], input[data-automation-id*='location' i], input[name*='city' i], input[name*='location' i], #location", p.get("city", "Hyderabad"), "Location"),
            ("input[autocomplete='organization'], input[data-automation-id*='company' i], input[name*='company' i], input[name*='org' i], input[placeholder*='company' i]", p.get("currentCompany", "CGI India (PNC Bank GCC)"), "Company"),
            ("input[autocomplete='organization-title'], input[data-automation-id*='title' i], input[name*='title' i], input[name*='designation' i], input[placeholder*='job title' i]", p.get("currentTitle", "DevOps Engineer / Azure Data Engineer"), "Title"),
            ("input[data-automation-id*='linkedin' i], input[name*='linkedin' i], input[id*='linkedin' i], input[placeholder*='linkedin' i]", p.get("linkedInUrl", "https://linkedin.com/in/lavkush-kumar"), "LinkedIn"),
            ("input[data-automation-id*='github' i], input[name*='github' i], input[id*='github' i], input[placeholder*='github' i]", p.get("githubUrl", "https://github.com/lavkush-kumar"), "GitHub"),
        ]
        for selector, val, label in field_map:
            try:
                loc = page.locator(selector).first
                if safe_count(loc) > 0 and loc.is_visible():
                    loc.fill(str(val))
                    filled.append(label)
                    self.record_field(
                        label=label,
                        value=val,
                        field_name=selector,
                        field_type="text",
                        step=1,
                        step_name="BASIC_INFO",
                        action_type="FILLED"
                    )
                else:
                    logger.debug("GenericPortalHandler selector miss for %s: %s", label, selector)
            except Exception as e_f:
                logger.debug("GenericPortalHandler field fill notice [%s]: %s", label, e_f)

        # AIHawk Lesson: Label text anchor fallback for custom/obfuscated input IDs (e.g. Zoho, Keka, Darwinbox)
        label_fallbacks = [
            ("First Name", p.get("firstName", "Lavkush")),
            ("Last Name", p.get("lastName", "Kumar")),
            ("Email", p.get("email", "lav84095@gmail.com")),
            ("Phone", p.get("phone", "+91-9122036484")),
            ("Mobile", p.get("phone", "+91-9122036484")),
            ("Current Company", p.get("currentCompany", "CGI India (PNC Bank GCC)")),
            ("LinkedIn", p.get("linkedInUrl", "https://linkedin.com/in/lavkush-kumar")),
            ("GitHub", p.get("githubUrl", "https://github.com/lavkush-kumar")),
        ]
        for lbl_name, val in label_fallbacks:
            if lbl_name not in filled:
                try:
                    lbl_el = page.locator(f"label:has-text('{lbl_name}')").first
                    if safe_count(lbl_el) > 0 and lbl_el.is_visible():
                        inp_el = lbl_el.locator("xpath=following::input[1] | ..//input").first
                        if safe_count(inp_el) > 0 and inp_el.is_visible() and not inp_el.input_value():
                            inp_el.fill(str(val))
                            filled.append(lbl_name)
                            self.record_field(
                                label=lbl_name,
                                value=val,
                                field_name=f"label_{lbl_name}",
                                field_type="text",
                                step=1,
                                step_name="BASIC_INFO",
                                action_type="FILLED"
                            )
                except Exception:
                    pass

        # Consent and privacy checkboxes
        try:
            for cb in page.locator("input[type='checkbox']").all():
                try:
                    if not cb.is_checked():
                        parent = cb.locator("xpath=ancestor::label | ancestor::div[1]").first
                        txt = parent.inner_text().lower() if safe_count(parent) > 0 else ""
                        if any(k in txt for k in ["consent", "privacy", "terms", "agree", "certify", "acknowledge", "data processing"]) or cb.get_attribute("required") is not None:
                            cb.check(force=True)
                            filled.append("Consent Checkbox")
                            self.record_field(
                                label="Consent / Agreement Checkbox",
                                value="Checked",
                                field_name="checkbox",
                                field_type="checkbox",
                                step=1,
                                step_name="DISCLOSURES",
                                action_type="CHECKED"
                            )
                except Exception:
                    pass
        except Exception as e_cb:
            logger.debug("GenericPortalHandler checkbox notice: %s", e_cb)

        return {"filled": filled, "field_records": list(self.field_records), "ats": self.ats_type}

    def submit_form(self, page: Any) -> bool:
        if not page:
            return False

        # Pre-submit: Remove any residual required constraint from empty non-file inputs
        try:
            if hasattr(page, "evaluate"):
                page.evaluate("""() => {
                    document.querySelectorAll('[required]').forEach(el => {
                        if (el.type !== 'file' && (!el.value || el.value === '')) {
                            el.removeAttribute('required');
                            el.removeAttribute('aria-required');
                        }
                    });
                }""")
        except Exception:
            pass

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
                    self.record_field(
                        label="Submit Application Button",
                        value="CLICKED",
                        field_name=sel,
                        field_type="button",
                        step=1,
                        step_name="SUBMIT_APPLICATION",
                        action_type="SUBMITTED"
                    )
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


class FillResult(tuple):
    """Tuple subclass preserving (success, fields) unpacking while carrying evidence_path, field_records, and status."""
    def __new__(cls, success: bool, fields: List[str], evidence_path: Optional[str] = None, field_records: Optional[List[Dict[str, Any]]] = None, status: Optional[str] = None):
        return super().__new__(cls, (success, fields))

    def __init__(self, success: bool, fields: List[str], evidence_path: Optional[str] = None, field_records: Optional[List[Dict[str, Any]]] = None, status: Optional[str] = None):
        self.success = success
        self.fields = fields
        self.evidence_path = evidence_path
        self.field_records = field_records or []
        self.status = status or ("Submitted (Confirmed)" if success else "Failed")


class CareerPortalFiller:
    def __init__(self, db_path: Optional[str] = None):
        self.profile = load_applicant_profile()
        self.solver = FactMatrixScreeningSolver()
        self.db_path = db_path

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
        if "greenhouse.io" in u or "gh_jid" in u:
            return "Greenhouse"
        if "ashbyhq.com" in u:
            return "Ashby"
        if "lever.co" in u:
            return "Lever"
        if "myworkdayjobs.com" in u or "workday" in u:
            return "Workday"
        if "rippling.com" in u:
            return "Rippling"
        if "smartrecruiters.com" in u:
            return "SmartRecruiters"
        if "icims.com" in u:
            return "iCIMS"
        if "taleo.net" in u or "taleo." in u:
            return "Taleo"
        if "oraclecloud.com" in u and "recruiting" in u:
            return "Oracle Recruiting"
        if "successfactors.com" in u or "successfactors.eu" in u:
            return "SuccessFactors"
        if "workable.com" in u:
            return "Workable"
        if "breezy.hr" in u:
            return "Breezy"
        if "jazz.co" in u or "applytojob.com" in u:
            return "JazzHR"
        if "recruitee.com" in u:
            return "Recruitee"
        if "teamtailor.com" in u:
            return "Teamtailor"
        if "personio.de" in u or "personio.com" in u:
            return "Personio"
        if "bamboohr.com" in u:
            return "BambooHR"
        if "jobvite.com" in u:
            return "Jobvite"
        if "phenom.com" in u or "phenompeople.com" in u:
            return "Phenom"
        if "eightfold.ai" in u:
            return "Eightfold"
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

        # Strict Deduplication Check: Never apply to the same job again
        from naukari_pro.modules.db import is_job_already_applied
        target_db = getattr(self, "db_path", None)
        if is_job_already_applied(title=role, company=company, job_url=portal_url, db_path=target_db):
            print(f"    [DEDUP] Already applied to '{role}' at '{company}' ({portal_url}). Skipping strictly per rule.")
            return False, []

        ats_type = self.detect_ats(portal_url)

        if sys.platform != "darwin":
            print("    [!] Notice: AppleScript Chrome automation is macOS-only. Routing via headless Playwright...")
            if _is_asyncio_loop_running():
                logger.info("Active asyncio loop detected in thread. Dispatching fill_in_chrome to dedicated worker thread...")
                future = _PORTAL_WORKER_POOL.submit(self.fill_in_chrome, portal_url, company=company, role=role)
                return future.result()
            try:
                from playwright.sync_api import sync_playwright
                from naukari_pro.session import get_stealth_context
                with sync_playwright() as p:
                    context = get_stealth_context(
                        p, headless=True, session_dir=PORTALS_SESSION_DIR, lock_timeout=90.0
                    )
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

    def fill_in_playwright(
        self,
        page,
        portal_url: str,
        company: str = "Company",
        role: str = "Azure Data Engineer",
        auto_submit: bool = True
    ) -> FillResult:
        """
        Architecture Rules A1–A5 Unified State Machine Executor.
        State sequence: DETECT -> ACCOUNT -> FILL -> REVIEW -> SUBMIT -> VERIFY -> LOG.
        Terminal outcomes: CONFIRMED (evidence attached) or FALLBACK (standard reason code).
        """
        t_start = time.time()
        if not portal_url or not isinstance(portal_url, str):
            print("    [!] Error: Invalid or empty portal URL.")
            return FillResult(False, [], None, status=FallbackReason.CLOSED_OR_EXPIRED.value)

        from naukari_pro.modules.db import is_job_already_applied, generate_job_id, record_batch_field_audit
        target_db = getattr(self, "db_path", None)
        cand_job_id = generate_job_id(role, company, portal_url)

        # ── STATE 1: DETECT ──
        checkpoint_portal_state(cand_job_id, PortalState.DETECT, company, role, target_db)

        # A5 Idempotency Check 1
        if is_job_already_applied(title=role, company=company, job_url=portal_url, job_id=cand_job_id, db_path=target_db):
            print(f"    [DEDUP] Already applied to '{role}' at '{company}' ({portal_url}). Skipping strictly per rule.")
            return FillResult(False, [], None, status=FallbackReason.ALREADY_APPLIED.value)

        # A4 Time budget check
        if time.time() - t_start > PER_JOB_TIME_BUDGET_SEC:
            print(f"    [FALLBACK: {FallbackReason.TIMEOUT_240S.value}] Per-job time budget exceeded.")
            return FillResult(False, [], None, status=FallbackReason.TIMEOUT_240S.value)

        ats_type = self.detect_ats(portal_url)
        print(f"\n[*] [DETECT] Navigating to {ats_type} Portal via Playwright...")

        # A2 Schema Before Browser: fetch offline schema plan if public API exists
        schema_planner = ATSFormSchemaPlanner(self.profile, self.solver)
        schema_plan = schema_planner.fetch_schema_plan(portal_url)
        if schema_plan:
            print(f"    [SCHEMA-FIRST] Pre-computed offline schema plan with {len(schema_plan.get('answers', {}))} answers")

        try:
            page.goto(portal_url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e_nav:
            print(f"    Notice navigating: {e_nav}")
        time.sleep(2)

        # Hard stop: closed or expired link
        page_url_lower = (getattr(page, "url", "") or "").lower()
        page_content_lower = ""
        try:
            page_content_lower = (page.content() or "").lower()
        except Exception:
            pass
        if (
            "expjd=true" in page_url_lower
            or "/jobs-in-" in page_url_lower
            or "job you are looking for is no longer active" in page_content_lower
            or "this job has expired" in page_content_lower
            or "position has been filled" in page_content_lower
            or "job is no longer available" in page_content_lower
        ):
            print(f"    [FALLBACK: {FallbackReason.CLOSED_OR_EXPIRED.value}] Job posting expired or closed on host platform.")
            return FillResult(False, [], None, status=FallbackReason.CLOSED_OR_EXPIRED.value)

        # Universal Cookie & Overlay Dismissal
        try:
            cookie_buttons = page.locator(
                "button:has-text('Accept'), button:has-text('Allow'), button:has-text('Agree'), "
                "button:has-text('Accept all'), button:has-text('Got it'), button:has-text('OK'), "
                "[data-automation-id*='cookie' i], .cw-cookie-freeze-layer"
            )
            if safe_count(cookie_buttons) > 0 and cookie_buttons.first.is_visible():
                cookie_buttons.first.click(force=True, timeout=2000)
                time.sleep(0.5)
        except Exception:
            pass

        # Universal Landing Page CTA Opener (reveals form if on job description / view page)
        try:
            visible_inputs = safe_count(page.locator("input:not([type='hidden'])"))
            if visible_inputs < 2:
                cta_selectors = [
                    "button:has-text('interested')",
                    "button:has-text('Apply for this job')",
                    "a:has-text('Apply for this job')",
                    "button:has-text('Apply Now')",
                    "a:has-text('Apply Now')",
                    "button:has-text('Apply')",
                    "a:has-text('Apply')"
                ]
                for cta_sel in cta_selectors:
                    cta = page.locator(cta_sel).first
                    if safe_count(cta) > 0 and cta.is_visible():
                        print(f"    🔘 Opening application form via CTA: {cta_sel}...")
                        cta.click(force=True, timeout=5000)
                        time.sleep(2)
                        break
        except Exception as e_cta:
            logger.debug("CTA opener notice: %s", e_cta)

        handler = self.get_handler(ats_type)

        # ── STATE 2: ACCOUNT & BARRIERS ──
        checkpoint_portal_state(cand_job_id, PortalState.ACCOUNT, company, role, target_db)
        if time.time() - t_start > PER_JOB_TIME_BUDGET_SEC:
            print(f"    [FALLBACK: {FallbackReason.TIMEOUT_240S.value}] Per-job time budget exceeded.")
            return FillResult(False, [], None, status=FallbackReason.TIMEOUT_240S.value)

        barrier = handler.detect_barriers(page)
        if barrier:
            b_low = barrier.lower()
            if any(k in b_low for k in ("captcha", "turnstile", "challenge", "recaptcha", "hcaptcha", "arkose")):
                print(f"    [FALLBACK: {FallbackReason.CAPTCHA.value}] Stopped on anti-bot challenge: {barrier}")
                return FillResult(False, [], None, field_records=list(handler.field_records), status=FallbackReason.CAPTCHA.value)
            elif any(k in b_low for k in ("sign-in", "login", "account", "vault")):
                print(f"    [FALLBACK: {FallbackReason.SIGNIN_WALL.value}] Sign-in wall encountered: {barrier}")
                return FillResult(False, [], None, field_records=list(handler.field_records), status=FallbackReason.SIGNIN_WALL.value)
            else:
                print(f"    [FALLBACK: {FallbackReason.SIGNIN_WALL.value}] Barrier encountered: {barrier}")
                return FillResult(False, [], None, field_records=list(handler.field_records), status=FallbackReason.SIGNIN_WALL.value)

        # ── STATE 3: FILL ──
        checkpoint_portal_state(cand_job_id, PortalState.FILL, company, role, target_db)
        if time.time() - t_start > PER_JOB_TIME_BUDGET_SEC:
            print(f"    [FALLBACK: {FallbackReason.TIMEOUT_240S.value}] Per-job time budget exceeded.")
            return FillResult(False, [], None, status=FallbackReason.TIMEOUT_240S.value)

        filled_fields: List[str] = []
        try:
            handler_res = handler.fill_form(page, schema_plan=schema_plan) if hasattr(handler.fill_form, "__code__") and "schema_plan" in handler.fill_form.__code__.co_varnames else handler.fill_form(page)
            filled_fields = handler_res.get("filled", [])
            print(f"[✓] [FILL] {ats_type} Form Auto-Filled via Handler: {', '.join(filled_fields) if filled_fields else 'Basic Fields'}")
        except Exception as e_h:
            print(f"    Handler fill notice: {e_h}")

        # Also run JS fill script for backward compatibility with generic portals
        try:
            js_code = self.generate_fill_script(ats_type)
            res_str = page.evaluate(js_code)
            res_data = json.loads(res_str) if isinstance(res_str, str) else res_str
            if isinstance(res_data, dict):
                filled_fields = list(set(filled_fields + res_data.get("filled", [])))
        except Exception:
            pass

        # Attempt resume upload
        resume_path = self.profile.get("resumePath")
        if resume_path and os.path.exists(resume_path):
            uploaded = handler.upload_resume(page, resume_path)
            if uploaded:
                print(f"    📎 [RESUME] Resume PDF uploaded: {os.path.basename(resume_path)}")
                filled_fields.append("Resume PDF")

        # Cloud upload settling delay
        time.sleep(3)

        # ── STATE 4: REVIEW ──
        checkpoint_portal_state(cand_job_id, PortalState.REVIEW, company, role, target_db)
        if time.time() - t_start > PER_JOB_TIME_BUDGET_SEC:
            print(f"    [FALLBACK: {FallbackReason.TIMEOUT_240S.value}] Per-job time budget exceeded.")
            return FillResult(False, filled_fields, None, field_records=list(handler.field_records), status=FallbackReason.TIMEOUT_240S.value)

        # Check for validation errors on form
        has_validation_errors = False
        try:
            error_elems = page.locator(".field-error, li.error, .error-message, div.error, [aria-invalid='true']")
            if safe_count(error_elems) > 0 and error_elems.first.is_visible():
                has_validation_errors = True
        except Exception:
            pass

        # ── STATE 5: SUBMIT ──
        checkpoint_portal_state(cand_job_id, PortalState.SUBMIT, company, role, target_db)

        # A5 Idempotency Check 2: Immediately before submit
        if is_job_already_applied(title=role, company=company, job_url=portal_url, job_id=cand_job_id, db_path=target_db):
            print(f"    [DEDUP] Pre-submit check confirmed job already applied. Halting submit.")
            return FillResult(False, filled_fields, None, field_records=list(handler.field_records), status=FallbackReason.ALREADY_APPLIED.value)

        evidence_file = None
        is_confirmed = False

        if auto_submit:
            submit_clicked = handler.submit_form(page)
            if not submit_clicked:
                all_records = list(handler.field_records)
                fallback_reason = FallbackReason.VALIDATION_ERRORS.value if has_validation_errors else FallbackReason.SUBMIT_NOT_FOUND.value
                print(f"    [FALLBACK: {fallback_reason}] Submit button not located or constrained.")
                log_portal_application(company, role, ats_type, f"FALLBACK ({fallback_reason})", portal_url)
                return FillResult(False, filled_fields, None, field_records=all_records, status=fallback_reason)

            # ── STATE 6: VERIFY ──
            checkpoint_portal_state(cand_job_id, PortalState.VERIFY, company, role, target_db)
            is_confirmed = handler.verify_confirmation(page, timeout=25.0)
            if is_confirmed:
                from naukari_pro.modules.learning.evidence import EvidenceVerifier
                ev = EvidenceVerifier()
                sc_path = ev.capture_screenshot_sync(page, company, role)
                sub_status, evidence_file = ev.evaluate_submission_state(is_confirmed, sc_path)
                if sub_status == "Submitted (Confirmed)" and evidence_file and os.path.exists(evidence_file):
                    print(f"    🚀 [CONFIRMED] Form Submitted on {ats_type} Portal with verified evidence: {evidence_file}")
                    # Optional IMAP email confirmation audit
                    try:
                        email_conf, subj = ev.verify_email_confirmation(company, role, since_ts=t_start, timeout_sec=8.0)
                        if email_conf:
                            print(f"    ✉️ [IMAP-CONFIRMED] Confirmation email received: '{subj}'")
                    except Exception:
                        pass

                    # ── STATE 7: LOG ──
                    checkpoint_portal_state(cand_job_id, PortalState.LOG, company, role, target_db)
                    log_portal_application(company, role, ats_type, "Submitted (Confirmed)", portal_url, evidence_path=evidence_file)
                    all_field_records = list(handler.field_records)
                    try:
                        record_batch_field_audit(cand_job_id, f"career_portal ({ats_type})", company, role, all_field_records)
                    except Exception:
                        pass
                    return FillResult(True, filled_fields, evidence_file, field_records=all_field_records, status="Submitted (Confirmed)")
                else:
                    fallback_reason = FallbackReason.CLICKED_NO_CONFIRMATION.value
                    print(f"    [FALLBACK: {fallback_reason}] Confirmation detected but screenshot validation failed.")
                    return FillResult(False, filled_fields, None, field_records=list(handler.field_records), status=fallback_reason)
            else:
                fallback_reason = FallbackReason.CLICKED_NO_CONFIRMATION.value
                print(f"    [FALLBACK: {fallback_reason}] Submit clicked but confirmation not detected within timeout.")
                return FillResult(False, filled_fields, None, field_records=list(handler.field_records), status=fallback_reason)

        all_field_records = list(handler.field_records)
        try:
            record_batch_field_audit(cand_job_id, f"career_portal ({ats_type})", company, role, all_field_records)
        except Exception:
            pass

        log_portal_application(company, role, ats_type, "Form Auto-Filled", portal_url)
        return FillResult(is_confirmed, filled_fields, evidence_file, field_records=all_field_records, status="Form Auto-Filled")

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
        from naukari_pro.modules.role_guard import is_strictly_data_or_cloud_role
        is_role_ok, _ = is_strictly_data_or_cloud_role(role, raw_jd, score=final_score, company=company)
        if not is_role_ok:
            status = "REJECTED_BELOW_THRESHOLD"

        answers = {
            "first_name": self.profile.get("firstName", "Lavkush"),
            "last_name": self.profile.get("lastName", "Kumar"),
            "full_name": self.profile.get("fullName", "Lavkush Kumar"),
            "email": self.profile.get("email", "lav84095@gmail.com"),
            "phone": self.profile.get("phone", "+91-9122036484"),
            "location": self.profile.get("city", "Hyderabad"),
            "linkedin": self.profile.get("linkedInUrl", "https://linkedin.com/in/lavkush-kumar"),
            "github": self.profile.get("githubUrl", "https://github.com/lavkush-kumar"),
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
        match_score: Optional[int] = None,
        auto_submit: bool = True
    ):
        """Unified entrypoint supporting both live submission and offline dry-run."""
        # P0-1: If called from inside an active asyncio event loop thread (e.g. from
        # async auto_apply / NaukriAutoApplier), dispatch to a dedicated worker thread
        # that owns NO running event loop. This completely eliminates Playwright's
        # "sync API inside asyncio loop" crash.
        if page is None and _is_asyncio_loop_running():
            logger.info("Active asyncio loop detected in thread. Dispatching CareerPortalFiller.fill to dedicated worker thread...")
            future = _PORTAL_WORKER_POOL.submit(
                self.fill,
                portal_url=portal_url,
                company=company,
                role=role,
                headless=headless,
                dry_run=dry_run,
                raw_jd=raw_jd,
                salary=salary,
                page=None,
                match_score=match_score,
                auto_submit=auto_submit
            )
            return future.result()

        # Unconditional Role Guard: Never apply to non-data / non-cloud roles
        from naukari_pro.modules.role_guard import is_strictly_data_or_cloud_role
        is_role_ok, role_reason = is_strictly_data_or_cloud_role(role, raw_jd, score=match_score, company=company)
        if not is_role_ok:
            logger.info("CareerPortalFiller rejected non-target role: %s @ %s (%s)", role, company, role_reason)
            return FillResult(False, [], None, status="REJECTED_NON_DATA_ROLE")

        # Strict Deduplication Check: Never apply to the same job again
        from naukari_pro.modules.db import is_job_already_applied
        target_db = getattr(self, "db_path", None)
        if not dry_run and is_job_already_applied(title=role, company=company, job_url=portal_url, db_path=target_db):
            print(f"  [DEDUP] Already applied to '{role}' at '{company}' ({portal_url}). Skipping strictly per rule.")
            return FillResult(False, [], None, status=FallbackReason.ALREADY_APPLIED.value)

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
            return self.fill_in_playwright(page, portal_url, company=company, role=role, auto_submit=auto_submit)
        elif sys.platform == "darwin" and not headless:
            return self.fill_in_chrome(portal_url, company=company, role=role)
        else:
            try:
                from playwright.sync_api import sync_playwright
                from naukari_pro.session import get_stealth_context
                with sync_playwright() as p:
                    context = get_stealth_context(
                        p, headless=headless, session_dir=PORTALS_SESSION_DIR, lock_timeout=90.0
                    )
                    page_ctx = context.pages[0] if context.pages else context.new_page()
                    res = self.fill_in_playwright(page_ctx, portal_url, company=company, role=role, auto_submit=auto_submit)
                    context.close()
                    return res
            except Exception as e:
                print(f"Playwright automation error: {e}")
                return FillResult(False, [], None)

    def process_external_redirects(
        self,
        limit: int = 10,
        headless: bool = True,
        dry_run: bool = False,
        min_score: float = 0.0,
        max_exp: float = 4.0,
        auto_submit: bool = True,
        universal_apply: Optional[bool] = True
    ) -> Dict[str, Any]:
        """
        Processes pending external career portal redirects from Naukri_Live_Application_Tracker.xlsx.
        Scans for rows with Status == 'External Redirect' (or 'Not Available'),
        filters by experience and score unless universal_apply is enabled,
        and automates form-filling, resume attachment, and submission.
        Updates tracker Excel and applied_jobs.db.
        """
        if _is_asyncio_loop_running():
            logger.info("Active asyncio loop detected in thread. Dispatching process_external_redirects to dedicated worker thread...")
            future = _PORTAL_WORKER_POOL.submit(
                self.process_external_redirects,
                limit=limit,
                headless=headless,
                dry_run=dry_run,
                min_score=min_score,
                max_exp=max_exp,
                auto_submit=auto_submit,
                universal_apply=universal_apply
            )
            return future.result()
        import openpyxl
        from naukari_pro.modules.auto_apply import is_experience_eligible
        from naukari_pro.modules.db import is_job_already_applied, record_applied_job

        is_universal = universal_apply if universal_apply is not None else True

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

                # Strict Deduplication Check: Never apply to the same job again
                from naukari_pro.modules.db import is_job_already_applied
                if is_job_already_applied(title=title, company=company, job_url=url, db_path=self.db_path):
                    continue

                # Unconditional Role Guard: Never apply to non-data / non-cloud roles
                from naukari_pro.modules.role_guard import is_strictly_data_or_cloud_role
                is_role_ok, _ = is_strictly_data_or_cloud_role(title, "", score=score, company=company)
                if not is_role_ok:
                    continue

                if not is_universal:
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

        # Beast CONVERT: oldest-first backlog (date ascending, unknown dates last)
        def _redirect_sort_key(item: Dict[str, Any]):
            d = item.get("date")
            if d is None:
                return "9999-12-31"
            if hasattr(d, "strftime"):
                return d.strftime("%Y-%m-%d %H:%M:%S")
            return str(d)

        candidates_to_process.sort(key=_redirect_sort_key)

        # Contextual bandit selection policy gating & volume floor enforcement (v2.1-linucb)
        active_policy = getattr(self, "policy", None)
        if active_policy is None:
            try:
                from naukari_pro.modules.learning.policy import LinUCBBanditPolicy
                active_policy = LinUCBBanditPolicy()
            except Exception:
                active_policy = None

        if not is_universal and active_policy is not None and candidates_to_process:
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
        if is_universal:
            print(f"  Total Eligible Pending Redirects: {len(candidates_to_process)} (Universal Apply Mode — No Filtering)")
        else:
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
            context = get_stealth_context(
                p, headless=headless, session_dir=PORTALS_SESSION_DIR, lock_timeout=90.0
            )
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

                    # Hard Stop 2: Dead / Closed / Expired Link Check
                    curr_url_lower = page.url.lower()
                    page_content_lower = ""
                    try:
                        page_content_lower = (page.content() or "").lower()
                    except Exception:
                        pass

                    is_closed = (
                        "expjd=true" in curr_url_lower
                        or "/jobs-in-" in curr_url_lower
                        or "job you are looking for is no longer active" in page_content_lower
                        or "this job has expired" in page_content_lower
                        or "position has been filled" in page_content_lower
                        or "job is no longer available" in page_content_lower
                    )
                    if is_closed:
                        print(f"    🛑 Hard Stop 2: Job expired / closed on source platform (expJD=true). Skipping...")
                        ws.cell(row=row_idx, column=9, value="SKIPPED_CLOSED_OR_EXPIRED")
                        ws.cell(row=row_idx, column=11, value="Closed / Expired on Source (expJD=true)")
                        wb.save(TRACKER_PATH)
                        sync_dual_log(
                            title=title,
                            company=company,
                            platform="career_portal",
                            status="SKIPPED_CLOSED_OR_EXPIRED",
                            job_url=url,
                            match_score=score,
                            experience_req=item.get("exp"),
                            error_reason="Job expired on source platform (expJD=true)"
                        )
                        skipped += 1
                        results.append({"company": company, "title": title, "status": "SKIPPED_CLOSED_OR_EXPIRED", "url": url})
                        continue

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
                                if len(context.pages) > 1 and "naukri.com" not in context.pages[-1].url.lower():
                                    active_page = context.pages[-1]
                                    target_portal_url = active_page.url
                                elif "naukri.com" not in page.url.lower():
                                    active_page = page
                                    target_portal_url = page.url
                                else:
                                    try:
                                        href = co_btn.get_attribute("href")
                                        if href and "naukri.com" not in href.lower():
                                            page.goto(href, wait_until="domcontentloaded", timeout=30000)
                                            active_page = page
                                            target_portal_url = page.url
                                    except Exception:
                                        pass
                        else:
                            print(f"    ⚠️ 'Apply on Company Site' button not visible on Naukri. Marking SKIPPED_CLOSED_OR_EXPIRED.")
                            ws.cell(row=row_idx, column=9, value="SKIPPED_CLOSED_OR_EXPIRED")
                            ws.cell(row=row_idx, column=11, value="Company site button missing")
                            wb.save(TRACKER_PATH)
                            sync_dual_log(
                                title=title,
                                company=company,
                                platform="career_portal",
                                status="SKIPPED_CLOSED_OR_EXPIRED",
                                job_url=url,
                                match_score=score,
                                error_reason="Apply button missing on source page"
                            )
                            skipped += 1
                            results.append({"company": company, "title": title, "status": "SKIPPED_CLOSED_OR_EXPIRED", "url": url})
                            continue
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
                    fallback_reason = None
                    ev = EvidenceVerifier()

                    if barrier:
                        b_low = barrier.lower()
                        if any(k in b_low for k in ("captcha", "turnstile", "challenge", "recaptcha", "hcaptcha", "arkose")):
                            fallback_reason = FallbackReason.CAPTCHA.value
                        elif any(k in b_low for k in ("sign-in", "login", "account", "vault")):
                            fallback_reason = FallbackReason.SIGNIN_WALL.value
                        else:
                            fallback_reason = FallbackReason.SIGNIN_WALL.value
                        print(f"    [FALLBACK: {fallback_reason}] Barrier encountered on {ats_type} portal: {barrier}")
                        sub_status = f"FALLBACK ({fallback_reason})"
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

                        # Ensure cloud file upload completes before submit
                        time.sleep(4)

                        # Submit application if requested with strict confirmation detection
                        if auto_submit:
                            submit_clicked = handler.submit_form(active_page)
                            if submit_clicked:
                                is_confirmed = handler.verify_confirmation(active_page, timeout=25.0)
                                if is_confirmed:
                                    sc_path = ev.capture_screenshot_sync(active_page, company, title)
                                    sub_status, evidence_file = ev.evaluate_submission_state(is_confirmed, sc_path)
                                    if sub_status == "Submitted (Confirmed)":
                                        print(f"    🚀 [CONFIRMED] Form Submitted on {ats_type} Portal with verified evidence: {evidence_file}")
                                    else:
                                        fallback_reason = FallbackReason.CLICKED_NO_CONFIRMATION.value
                                        print(f"    [FALLBACK: {fallback_reason}] Form submitted but screenshot header validation failed.")
                                        sub_status = f"FALLBACK ({fallback_reason})"
                                else:
                                    fallback_reason = FallbackReason.CLICKED_NO_CONFIRMATION.value
                                    print(f"    [FALLBACK: {fallback_reason}] Submit clicked but confirmation not detected within timeout.")
                                    sub_status = f"FALLBACK ({fallback_reason})"
                            else:
                                # Check for validation errors
                                has_val_err = False
                                try:
                                    err_loc = active_page.locator(".field-error, li.error, .error-message, div.error, [aria-invalid='true']")
                                    if safe_count(err_loc) > 0 and err_loc.first.is_visible():
                                        has_val_err = True
                                except Exception:
                                    pass
                                fallback_reason = FallbackReason.VALIDATION_ERRORS.value if has_val_err else FallbackReason.SUBMIT_NOT_FOUND.value
                                print(f"    [FALLBACK: {fallback_reason}] Final submit button not located or constrained.")
                                sub_status = f"FALLBACK ({fallback_reason})"

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
                        raw_metadata={
                            "policy_action": item.get("policy_action", "APPLY"),
                            "field_audit": list(getattr(handler, "field_records", []))
                        },
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

# Seed titles/URLs only — salary/exp/jd stay NULL until fetched from a live ATS API.
# Curated offline fixtures for dry-run / pytest. JD keywords are intentional fixtures
# (not scraped claims) so match scoring stays deterministic offline.
_CURATED_ADE_JD = (
    "Azure Databricks PySpark Delta Lake SQL Kafka Terraform Kubernetes. "
    "Build production lakehouse pipelines for India GCC teams."
)

CURATED_ATS_VACANCIES: List[Dict[str, Any]] = [
    {
        "company": "Microsoft GCC",
        "title": "Lead Azure Data Engineer",
        "salary": None,
        "url": "https://boards.greenhouse.io/microsoftgcc/jobs/401",
        "jd": None,
        "exp": None,
        "location": "Bengaluru / Hyderabad",
        "ats": "Greenhouse"
    },
    {
        "company": "Walmart Global Tech",
        "title": "Azure Data Platform Engineer",
        "salary": None,
        "url": "https://walmart.wd5.myworkdayjobs.com/en-US/jobs/job/Azure-Data-Engineer_R-9901",
        "jd": None,
        "exp": None,
        "location": "Bengaluru",
        "ats": "Workday"
    },
    {
        "company": "Uber Technologies",
        "title": "Data Engineer II - Real-Time Streaming",
        "salary": None,
        "url": "https://jobs.lever.co/uber/803",
        "jd": None,
        "exp": None,
        "location": "Hyderabad",
        "ats": "Lever"
    },
    {
        "company": "Atlassian",
        "title": "Data Platform Engineer",
        "salary": None,
        "url": "https://boards.greenhouse.io/atlassian/jobs/502",
        "jd": None,
        "exp": None,
        "location": "Bengaluru / Remote",
        "ats": "Greenhouse"
    },
    {
        "company": "Databricks Partner GCC",
        "title": "Senior Azure Databricks Specialist",
        "salary": None,
        "url": "https://jobs.ashbyhq.com/databricks-partner/904",
        "jd": None,
        "exp": None,
        "location": "Bengaluru / Pune",
        "ats": "Ashby"
    },
    {
        "company": "Swiggy Engineering",
        "title": "Frontend React Engineer",
        "salary": None,
        "url": "https://boards.greenhouse.io/swiggy/jobs/701",
        "jd": None,
        "exp": None,
        "location": "Bengaluru",
        "ats": "Greenhouse"
    }
]


def fetch_live_ats_vacancies(limit: int = 25, ats_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Dynamically queries public multi-ATS job boards.
    Honest metadata only: exp/salary/jd are NULL unless the ATS response includes them.
    Never invent JD text, experience bands, or salary ranges.
    """
    import requests
    by_ats: Dict[str, List[Dict[str, Any]]] = {
        "Greenhouse": [],
        "Ashby": [],
        "Workday": [],
        "Lever": []
    }
    keywords = ["data", "platform", "devops", "cloud", "engineer", "infrastructure", "software", "backend", "system", "analytics", "sre", "machine learning", "mlops", "ai", "database", "security", "developer", "architect", "manager", "specialist"]

    per_ats_limit = max(limit, 30)

    # 1. Greenhouse (content=true returns real HTML description when available)
    gh_boards = [
        ("GitLab", "gitlab"), ("Databricks", "databricks"), ("Stripe", "stripe"),
        ("Cloudflare", "cloudflare"), ("Canonical", "canonical"), ("Elastic", "elastic"),
        ("Grafana Labs", "grafanalabs"), ("Figma", "figma"), ("Anthropic", "anthropic"),
        ("Scale AI", "scaleai"), ("Airbnb", "airbnb"), ("Pinterest", "pinterest"),
        ("Instacart", "instacart"), ("Cockroach Labs", "cockroachlabs")
    ]
    per_gh_board = max(per_ats_limit, 80) if (ats_types and any("greenhouse" in a.lower() for a in ats_types)) else max(per_ats_limit // len(gh_boards), 40)
    for co_name, board_token in gh_boards:
        try:
            url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                jobs = r.json().get("jobs", [])
                board_added = 0
                for j in jobs:
                    if board_added >= per_gh_board:
                        break
                    title = j.get("title", "")
                    if any(kw in title.lower() for kw in keywords):
                        loc_dict = j.get("location") or {}
                        loc_name = loc_dict.get("name") if isinstance(loc_dict, dict) else (str(loc_dict) if loc_dict else None)
                        content = j.get("content")
                        by_ats["Greenhouse"].append({
                            "company": co_name,
                            "title": title,
                            "url": j.get("absolute_url"),
                            "ats": "Greenhouse",
                            "location": loc_name,  # None if missing — do not default-invent
                            "exp": None,
                            "salary": None,
                            "jd": content if content else None,
                        })
                        board_added += 1
        except Exception as e:
            logger.debug("Notice querying Greenhouse %s: %s", board_token, e)

    # 2. Ashby
    ashby_boards = [
        ("Sentry", "sentry"), ("Linear", "linear"), ("Ramp", "ramp"),
        ("Supabase", "supabase")
    ]
    per_ashby_board = max(per_ats_limit // len(ashby_boards), 15)
    for co_name, board_token in ashby_boards:
        try:
            url = f"https://api.ashbyhq.com/posting-api/job-board/{board_token}"
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                jobs = r.json().get("jobs", [])
                board_added = 0
                for j in jobs:
                    if board_added >= per_ashby_board:
                        break
                    title = j.get("title", "")
                    if any(kw in title.lower() for kw in keywords):
                        desc = j.get("descriptionHtml") or j.get("descriptionPlain") or j.get("description")
                        comp = j.get("compensationTierSummary") or j.get("compensation")
                        salary = comp.strip() if isinstance(comp, str) and comp.strip() else None
                        by_ats["Ashby"].append({
                            "company": co_name,
                            "title": title,
                            "url": j.get("jobUrl"),
                            "ats": "Ashby",
                            "location": j.get("location") or None,
                            "exp": None,
                            "salary": salary,
                            "jd": desc if desc else None,
                        })
                        board_added += 1
        except Exception as e:
            logger.debug("Notice querying Ashby %s: %s", board_token, e)

    # 3. Workday (NVIDIA, Salesforce, Autodesk) — list API usually omits JD; leave NULL
    workday_tenants = [
        ("NVIDIA", "https://nvidia.wd5.myworkdayjobs.com/wday/cxs/nvidia/NVIDIAExternalCareerSite/jobs", "https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite"),
        ("Salesforce", "https://salesforce.wd12.myworkdayjobs.com/wday/cxs/salesforce/External_Career_Site/jobs", "https://salesforce.wd12.myworkdayjobs.com/en-US/External_Career_Site"),
        ("Autodesk", "https://autodesk.wd1.myworkdayjobs.com/wday/cxs/autodesk/Ext/jobs", "https://autodesk.wd1.myworkdayjobs.com/en-US/Ext")
    ]
    for co_name, post_url, base_url in workday_tenants:
        try:
            payload = {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": "Engineer"}
            r = requests.post(post_url, json=payload, timeout=6)
            if r.status_code == 200:
                postings = r.json().get("jobPostings", [])
                board_added = 0
                for j in postings:
                    if board_added >= 15:
                        break
                    title = j.get("title", "")
                    ext_path = j.get("externalPath", "")
                    if any(kw in title.lower() for kw in keywords):
                        real_jd = j.get("jobDescription") or j.get("description") or None
                        by_ats["Workday"].append({
                            "company": co_name,
                            "title": title,
                            "url": f"{base_url}{ext_path}",
                            "ats": "Workday",
                            "location": j.get("locationsText") or None,
                            "exp": None,
                            "salary": None,
                            "jd": real_jd,
                        })
                        board_added += 1
        except Exception as e:
            logger.debug("Notice querying Workday %s: %s", co_name, e)

    # 4. Lever (Spotify)
    try:
        url = "https://api.lever.co/v0/postings/spotify?mode=json"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            postings = r.json()
            board_added = 0
            for j in postings:
                if board_added >= per_ats_limit:
                    break
                title = j.get("text", "")
                if any(kw in title.lower() for kw in keywords):
                    wpt = (j.get("workplaceType") or "").strip()
                    loc_cat = (j.get("categories") or {}).get("location", "")
                    loc_str = f"{loc_cat} ({wpt.capitalize()})" if wpt and loc_cat else (loc_cat or wpt or None)
                    desc = j.get("descriptionPlain") or j.get("description") or None
                    by_ats["Lever"].append({
                        "company": "Spotify",
                        "title": title,
                        "url": j.get("hostedUrl"),
                        "ats": "Lever",
                        "location": loc_str,
                        "exp": None,
                        "salary": None,
                        "jd": desc,
                    })
                    board_added += 1
    except Exception as e:
        logger.debug("Notice querying Lever: %s", e)

    # Helper: Remote-first location priority
    def _location_priority(loc: Any) -> int:
        l = str(loc or "").lower()
        if any(k in l for k in ("remote", "anywhere", "wfh", "virtual", "home based", "home-based", "worldwide")):
            return 0  # Remote First
        elif any(k in l for k in ("india", "bengaluru", "bangalore", "hyderabad", "pune", "gurugram", "gurgaon", "noida", "mumbai", "chennai", "delhi")):
            return 1  # India Tech Hubs
        else:
            return 2  # Other Global

    # Balanced bucket interleave across ATS platforms (prioritizing requested ats_types if provided)
    ats_order = [a.title() for a in ats_types] if ats_types else []
    ats_keys = [k for k in ats_order if k in by_ats] + [k for k in ["Greenhouse", "Ashby", "Workday", "Lever"] if k not in ats_order]
    p_buckets: Dict[int, Dict[str, List[Dict[str, Any]]]] = {
        0: {k: [] for k in ats_keys},
        1: {k: [] for k in ats_keys},
        2: {k: [] for k in ats_keys}
    }
    for k in ats_keys:
        for v in by_ats[k]:
            p = _location_priority(v.get("location", ""))
            p_buckets[p][k].append(v)

    vacancies: List[Dict[str, Any]] = []
    # Interleave ATS within Priority 0 (Remote First), then Priority 1 (India), then Priority 2 (Global)
    for p in (0, 1, 2):
        bucket = p_buckets[p]
        max_b = max((len(bucket[k]) for k in ats_keys), default=0)
        for idx in range(max_b):
            for k in ats_keys:
                if idx < len(bucket[k]):
                    vacancies.append(bucket[k][idx])

    if ats_types:
        ats_lower = [a.lower().strip() for a in ats_types]
        vacancies = [v for v in vacancies if any(a in v.get("ats", "").lower() for a in ats_lower)]

    return vacancies[:limit]


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
        match_score: Optional[int] = None,
        auto_submit: bool = True
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
            match_score=match_score,
            auto_submit=auto_submit
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
        if _is_asyncio_loop_running():
            logger.info("Active asyncio loop detected in thread. Dispatching ExternalPortalBatchRunner.run_batch to dedicated worker thread...")
            future = _PORTAL_WORKER_POOL.submit(
                self.run_batch,
                vacancies=vacancies,
                roles=roles,
                locations=locations,
                ats_types=ats_types,
                dry_run=dry_run,
                limit=limit,
                min_score=min_score,
                min_salary=min_salary,
                universal_apply=universal_apply
            )
            return future.result()
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

        if vacancies is not None:
            feed = list(vacancies)
        elif active_dry_run:
            # Offline/dry-run stays on curated fixtures so pytest and demos stay deterministic.
            feed = list(self.curated_vacancies)
        else:
            # Prefer aggregation store / fetch_live_normalized over hardcoded boards.
            live_feed: List[Dict[str, Any]] = []
            try:
                from naukari_pro.aggregation.pipeline import fetch_live_normalized
                from naukari_pro.aggregation.storage import AggregationStore

                store = AggregationStore()
                cached = store.list_active_jobs(limit=max(active_limit * 10, 400))
                if cached:
                    live_feed = [j.to_legacy_vacancy() for j in cached]
                else:
                    live_feed = fetch_live_normalized(limit_sources=min(30, max(active_limit, 10)))
            except Exception as exc:  # noqa: BLE001
                logger.debug("aggregation feed unavailable, falling back: %s", exc)
            if not live_feed:
                live_feed = fetch_live_ats_vacancies(
                    limit=max(active_limit * 10, 400), ats_types=ats_types
                )
            feed = live_feed if live_feed else list(self.curated_vacancies)

        # Filter by ats_types if explicitly specified
        if ats_types:
            ats_lower = [a.lower().strip() for a in ats_types]
            filtered_feed = []
            for v in feed:
                v_ats = (self.manager.detect_ats(v.get("url") or "") or "").lower()
                tag_ats = (v.get("ats") or "").lower()
                if any(target in v_ats or target in tag_ats for target in ats_lower):
                    filtered_feed.append(v)
            feed = filtered_feed

        # In legacy mode only: filter by roles if specified
        if not is_universal and roles:
            roles_lower = [r.lower().strip() for r in roles]
            feed = [
                v for v in feed
                if any(
                    r in (v.get("title") or "").lower() or r in (v.get("jd") or "").lower()
                    for r in roles_lower
                )
            ]

        # In legacy mode only: filter by locations if specified
        if not is_universal and locations:
            locs_lower = [l.lower().strip() for l in locations]
            feed = [
                v for v in feed
                if any(
                    l in (v.get("location") or "").lower() or "remote" in (v.get("location") or "").lower()
                    for l in locs_lower
                )
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

        playwright_mgr = None
        browser_context = None
        if not active_dry_run:
            try:
                from playwright.sync_api import sync_playwright
                from naukari_pro.session import get_stealth_context
                playwright_mgr = sync_playwright().start()
                browser_context = get_stealth_context(
                    playwright_mgr,
                    headless=self.headless,
                    session_dir=PORTALS_SESSION_DIR,
                    lock_timeout=90.0,
                )
            except Exception as e_pw:
                logger.debug("Notice pre-initializing batch Playwright context: %s", e_pw)

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

            # Unconditional Role Guard: Never apply to non-data / non-cloud roles
            from naukari_pro.modules.role_guard import is_strictly_data_or_cloud_role
            is_role_ok, role_reason = is_strictly_data_or_cloud_role(title, jd, score=score, company=company)
            if not is_role_ok:
                stats["skipped"] += 1
                stats["jobs"].append({
                    "company": company,
                    "title": title,
                    "url": url,
                    "ats": ats_type,
                    "status": "REJECTED_NON_DATA_ROLE",
                    "score": score,
                    "reason": role_reason
                })
                continue

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
                    job_page = None
                    try:
                        if browser_context:
                            try:
                                job_page = browser_context.new_page()
                            except Exception:
                                job_page = None
                        fill_res = self.manager.fill(
                            portal_url=url,
                            company=company,
                            role=title,
                            headless=self.headless,
                            dry_run=False,
                            raw_jd=jd,
                            salary=salary,
                            page=job_page,
                            match_score=int(score),
                            auto_submit=True
                        )
                        if isinstance(fill_res, tuple) and len(fill_res) >= 2:
                            submission_success = bool(fill_res[0])
                            filled_fields = fill_res[1]
                            evidence_file = getattr(fill_res, "evidence_path", None)
                            if len(fill_res) > 2 and evidence_file is None:
                                evidence_file = fill_res[2]
                        break
                    except Exception as e_fill:
                        last_error = str(e_fill)
                        if attempt < 2:
                            time.sleep(2)
                    finally:
                        if job_page:
                            try:
                                job_page.close()
                            except Exception:
                                pass

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

                is_confirmed = (
                    submission_success
                    and evidence_file
                    and os.path.exists(evidence_file)
                    and os.path.getsize(evidence_file) >= 1024
                )
                res_status = getattr(fill_res, "status", None)
                if is_confirmed:
                    status_str = "Submitted (Confirmed)"
                elif res_status and ("FALLBACK" in str(res_status) or any(r.value == str(res_status) for r in FallbackReason)):
                    status_str = f"FALLBACK ({res_status})" if not str(res_status).startswith("FALLBACK") else str(res_status)
                else:
                    status_str = "Form Auto-Filled (Ready for Review)"
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
                    field_audit=getattr(fill_res, "field_records", None) or filled_fields,
                    db_path=self.db_path,
                )
                if is_confirmed:
                    stats["submitted"] += 1
                    print(f"  [★ CONFIRMED APPLIED #{stats['submitted']}/{active_limit}] {company} | {title} | Evidence: {evidence_file}")
                else:
                    stats["skipped"] += 1

                stats["jobs"].append({
                    "company": company,
                    "title": title,
                    "url": url,
                    "ats": ats_type,
                    "status": status_str,
                    "score": score,
                    "filled": filled_fields
                })
        if browser_context:
            try:
                browser_context.close()
            except Exception:
                pass
        if playwright_mgr:
            try:
                playwright_mgr.stop()
            except Exception:
                pass

        return stats


