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
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
import openpyxl

from naukari_pro.config import TRACKER_PATH, RESUME_PDF_PATH, load_config

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


class CareerPortalFiller:
    def __init__(self):
        self.profile = load_applicant_profile()

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
        Leaves the application on the review page for human verification.
        """
        if not portal_url or not isinstance(portal_url, str):
            print("    [!] Error: Invalid or empty portal URL.")
            return False, []

        ats_type = self.detect_ats(portal_url)
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
                    print(f"    ATS Platform Detected: {ats_type} ({target_portal_url[:80]}...)")

                    # Run auto-filler script
                    js_code = self.generate_fill_script(ats_type)
                    res_str = active_page.evaluate(js_code)
                    res_data = json.loads(res_str) if isinstance(res_str, str) else res_str
                    filled_fields = res_data.get("filled", [])
                    print(f"    [✓] Auto-Filled Fields: {', '.join(filled_fields) if filled_fields else 'Basic Fields'}")

                    # Attach resume PDF if file input exists
                    file_input = active_page.locator("input[type='file']").first
                    resume_path = self.profile.get("resumePath")
                    if file_input.count() > 0 and resume_path and os.path.exists(resume_path):
                        try:
                            file_input.set_input_files(resume_path)
                            print(f"    📎 Resume Uploaded: {os.path.basename(resume_path)}")
                        except Exception as e_file:
                            print(f"    Notice on resume attachment: {e_file}")

                    time.sleep(2)

                    # Submit application if requested with 3-point evidence state machine
                    from naukari_pro.modules.learning.evidence import EvidenceVerifier
                    ev = EvidenceVerifier()
                    evidence_file = None
                    sub_status = "Form Auto-Filled (Ready for Review)"

                    if auto_submit:
                        submit_btn = active_page.locator("button[type='submit'], input[type='submit'], button:has-text('Submit Application'), button:has-text('Submit'), button:has-text('Apply')").first
                        if submit_btn.count() > 0 and submit_btn.is_visible():
                            try:
                                submit_btn.click(timeout=5000)
                                time.sleep(3)
                                sc_path = ev.capture_screenshot_sync(active_page, company, title)
                                if sc_path and ev.verify_screenshot_file(sc_path):
                                    sub_status = "Submitted (Confirmed)"
                                    evidence_file = sc_path
                                    print(f"    🚀 Form Submitted on {ats_type} Portal with verified evidence: {sc_path}")
                                else:
                                    sub_status = "Form Auto-Filled (Ready for Review)"
                                    print(f"    ⚠️ Submitted but unconfirmed; status strictly maintained as Ready for Review.")
                            except Exception as e_sub:
                                print(f"    Submit click notice: {e_sub}")
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

