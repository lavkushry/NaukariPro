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
import openpyxl

from naukari_pro.config import TRACKER_PATH, RESUME_PDF_PATH

# Candidate Ground Truth
PROFILE_PATH = Path.home() / ".job-apply" / "profile.json"

DEFAULT_CANDIDATE = {
    "firstName": "Lavkush",
    "lastName": "Kumar",
    "fullName": "Lavkush Kumar",
    "email": "lavkushry@gmail.com",
    "phone": "+91-9122036484",
    "city": "Hyderabad",
    "state": "Telangana",
    "country": "India",
    "zip": "500081",
    "linkedInUrl": "https://linkedin.com/in/lavkushry",
    "githubUrl": "https://github.com/lavkushry",
    "portfolioUrl": "https://github.com/lavkushry",
    "experienceYears": "2.5",
    "noticePeriodDays": "30",
    "currentCtcLpa": "12",
    "expectedCtcLpa": "25",
    "resumePath": RESUME_PDF_PATH
}

def load_applicant_profile():
    if PROFILE_PATH.exists():
        try:
            with open(PROFILE_PATH, "r", encoding="utf-8") as f:
                doc = json.load(f)
                prof = doc.get("profile", doc)
                if prof.get("firstName"):
                    data = dict(DEFAULT_CANDIDATE)
                    data.update({
                        "firstName": prof.get("firstName", "Lavkush"),
                        "lastName": prof.get("lastName", "Kumar"),
                        "fullName": f"{prof.get('firstName', 'Lavkush')} {prof.get('lastName', 'Kumar')}",
                        "email": prof.get("email", "lavkushry@gmail.com"),
                        "phone": prof.get("phone", "+91-9122036484"),
                        "linkedInUrl": prof.get("linkedInUrl", "https://linkedin.com/in/lavkushry"),
                        "githubUrl": prof.get("githubUrl", "https://github.com/lavkushry"),
                        "resumePath": prof.get("resumePath", RESUME_PDF_PATH)
                    })
                    if isinstance(prof.get("location"), dict):
                        loc = prof["location"]
                        data["city"] = loc.get("city", "Hyderabad")
                        data["country"] = loc.get("country", "India")
                    return data
        except Exception:
            pass
    return DEFAULT_CANDIDATE

def log_portal_application(company, role, portal_type, status, url):
    try:
        wb = openpyxl.load_workbook(TRACKER_PATH)
        ws = wb["Applications_Log"] if "Applications_Log" in wb.sheetnames else wb.active
        ws.append([
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            company,
            role,
            "Azure Data Engineer",
            "2-5 Yrs",
            "Hyderabad / Remote",
            f"Career Portal ({portal_type})",
            status,
            url,
            "Form Auto-Filled; Ready for Final Review"
        ])
        wb.save(TRACKER_PATH)
    except Exception:
        pass


class CareerPortalFiller:
    def __init__(self):
        self.profile = load_applicant_profile()

    def detect_ats(self, url: str) -> str:
        u = url.lower()
        if "greenhouse.io" in u or "gh_jid" in u:
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

            // 7. Check for resume file input
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
