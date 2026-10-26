"""
naukariPro Feature: LinkedIn Autonomous Easy Apply Engine
Milestone 3: End-to-End Multi-Step Easy Apply Bot with Precision Screening Solver

Provides:
- Intelligent Screening Questionnaire Solver (regex fuzzy matching for tech stack, notice period, CTC, visa, relocation)
- Multi-Step Modal Form Navigator (auto-fill contact, attach ATS resume, answer questions, uncheck 'Follow company')
- Precision Submission Verifier & Error Recovery (DOM verification of successful application dispatch)
- Unified LinkedIn Application Tracker (Excel 'LinkedIn_Applications_Log' worksheet + JSON audit log)
- Complete Apply Engine coordinating discovery, scoring gate (>= 70.0%), deduplication, and execution throttling (25-30 apps/cycle)
"""

import os
import sys
import re
import time
import json
import random
import inspect
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union, Tuple

import openpyxl

from naukari_pro.config import WORKSPACE_DIR, TRACKER_PATH, RESUME_PDF_PATH, load_config
from naukari_pro.modules.linkedin_session import (
    LinkedInSessionManager,
    LinkedInError,
    LinkedInSessionError
)
from naukari_pro.modules.linkedin_search import (
    LinkedInSearchEngine,
    JobMatchScorer,
    JobDeduplicator,
    TECH_HUBS,
    DEFAULT_KEYWORDS
)

logger = logging.getLogger("naukariPro.LinkedInApply")

# ==============================================================================
# EXCEPTIONS HIERARCHY
# ==============================================================================

class LinkedInApplyError(LinkedInError):
    """Base exception for Easy Apply execution errors."""
    pass


class LinkedInModalNotFoundError(LinkedInApplyError):
    """Raised when Easy Apply modal fails to open after clicking button."""
    pass


class LinkedInSubmissionFailedError(LinkedInApplyError):
    """Raised when application submission verification fails on DOM."""
    pass


# ==============================================================================
# CANONICAL CANDIDATE PROFILE & SCREENING ANSWERS
# ==============================================================================

def get_candidate_profile() -> Dict[str, Any]:
    """Dynamically loads candidate facts from config.json with robust fallbacks."""
    cfg = load_config()
    cand = cfg.get("candidate", {})
    common = cfg.get("answers_to_common_questions", {})

    return {
        "name": cand.get("name", "Lavkush Kumar"),
        "email": cand.get("email", "lavkushry@gmail.com"),
        "phone": cand.get("phone", "+91 9122036484"),
        "phone_national": "9122036484",
        "phone_country_code": "+91",
        "total_experience_years": float(cand.get("total_experience_years", 2.5)),
        "current_company": cand.get("current_company", "CGI India (PNC Bank GCC)"),
        "current_designation": cand.get("current_designation", "Azure Data Engineer"),
        "current_ctc_lakhs": float(cand.get("current_ctc_lakhs", 12.0)),
        "expected_ctc_lakhs": float(cand.get("expected_ctc_lakhs", 20.0)),
        "notice_period_days": int(cand.get("notice_period_days", 15)),
        "notice_period_text": cand.get("notice_period", "15 Days or less"),
        "primary_location": cand.get("primary_location", "Hyderabad, India"),
        "preferred_locations": cand.get("preferred_locations", [
            "Bengaluru", "Hyderabad", "Pune", "Gurugram", "Noida", "Mumbai", "Chennai"
        ]),
        "linkedin": cand.get("linkedin", "linkedin.com/in/lavkushry"),
        "github": cand.get("github", "github.com/lavkushry"),
        "resume_path": cand.get("resume_path", RESUME_PDF_PATH),
        "education_degree": "Bachelor's Degree",
        "education_field": "Computer Science and Engineering",
        "education_school": "Maharishi Dayanand University (MDU)",
        # Skill-specific experience calibration for 2.5 YOE profile
        "skills_experience": {
            "pyspark": 2.0,
            "databricks": 2.0,
            "azure": 2.5,
            "azure data factory": 2.0,
            "adf": 2.0,
            "sql": 2.5,
            "spark": 2.0,
            "delta lake": 2.0,
            "kafka": 1.5,
            "python": 2.5,
            "etl": 2.5,
            "data lakehouse": 2.0,
            "medallion": 2.0,
            "terraform": 1.5,
            "docker": 2.0,
            "kubernetes": 2.0,
            "ci/cd": 2.0,
            "git": 2.5,
        }
    }


# ==============================================================================
# UTILITY HELPER FUNCTIONS (PLAYWRIGHT SAFE ASYNC)
# ==============================================================================

async def safe_count(loc: Any) -> int:
    """Safely retrieves locator count or 0."""
    if loc is None:
        return 0
    try:
        res = loc.count()
        return await res if inspect.isawaitable(res) else res
    except Exception:
        return 0


async def safe_inner_text(loc: Any) -> str:
    """Safely extracts inner text or empty string."""
    if loc is None:
        return ""
    try:
        res = loc.inner_text()
        text = await res if inspect.isawaitable(res) else res
        return (text or "").strip()
    except Exception:
        return ""


async def safe_is_visible(loc: Any) -> bool:
    """Safely checks if locator is visible."""
    if loc is None:
        return False
    try:
        res = loc.is_visible()
        return await res if inspect.isawaitable(res) else res
    except Exception:
        return False


async def safe_is_checked(loc: Any) -> bool:
    """Safely checks if checkbox/radio is checked."""
    if loc is None:
        return False
    try:
        if hasattr(loc, "is_checked"):
            res = loc.is_checked()
            return await res if inspect.isawaitable(res) else res
        return False
    except Exception:
        return False


async def humanized_delay(min_ms: int = 1500, max_ms: int = 3000, page: Optional[Any] = None):
    """Introduces human-like jitter between navigation steps."""
    delay = random.uniform(min_ms / 1000.0, max_ms / 1000.0)
    if page and hasattr(page, "wait_for_timeout"):
        try:
            res = page.wait_for_timeout(int(delay * 1000))
            if inspect.isawaitable(res):
                await res
                return
        except Exception:
            pass
    time.sleep(delay)


# ==============================================================================
# 1. SCREENING QUESTIONNAIRE SOLVER
# ==============================================================================

class LinkedInScreeningSolver:
    """
    Solves complex multi-format application questionnaires using fuzzy regex
    and candidate facts from single source of truth.
    Handles text inputs, number inputs, radio buttons, dropdowns, and checkboxes.
    """

    def __init__(self, candidate: Optional[Dict[str, Any]] = None):
        self.candidate = candidate or get_candidate_profile()

    def get_numeric_experience_for_skill(self, text: str) -> str:
        """Determines calibrated years of experience for a queried skill or general YOE."""
        t_low = text.lower()
        skills = self.candidate.get("skills_experience", {})

        # Longest skill match first (e.g. 'azure data factory' before 'azure')
        sorted_skills = sorted(skills.items(), key=lambda x: len(x[0]), reverse=True)

        for skill_name, yoe in sorted_skills:
            pattern = r"\b" + re.escape(skill_name) + r"\b"
            if re.search(pattern, t_low):
                # Return integer string if whole number, else float string
                return str(int(yoe)) if yoe.is_integer() else str(yoe)

        # General total experience fallback
        tot = self.candidate.get("total_experience_years", 2.5)
        return str(int(tot)) if float(tot).is_integer() else str(tot)

    def determine_text_answer(self, label_text: str) -> Optional[str]:
        """Maps freeform or numeric question labels to candidate facts."""
        label_low = label_text.lower().strip()

        # 1. Phone number
        if any(k in label_low for k in ["phone", "mobile", "contact number", "cell"]):
            if "country" in label_low:
                return self.candidate.get("phone_country_code", "+91")
            return self.candidate.get("phone_national", "9122036484")

        # 2. Email
        if "email" in label_low:
            return self.candidate.get("email", "lavkushry@gmail.com")

        # 3. Years of Experience (specific tech or general)
        if any(k in label_low for k in ["how many years", "years of experience", "experience with", "experience do you have", "yoe"]):
            return self.get_numeric_experience_for_skill(label_text)

        # 4. Notice Period
        if any(k in label_low for k in ["notice period", "notice", "how soon can you join", "joining period", "days required"]):
            if "day" in label_low or "numeric" in label_low or "number" in label_low:
                return str(self.candidate.get("notice_period_days", 15))
            return self.candidate.get("notice_period_text", "15 Days or less")

        # 5. Compensation / CTC
        if any(k in label_low for k in ["current ctc", "current compensation", "current salary", "present ctc"]):
            curr = self.candidate.get("current_ctc_lakhs", 12.0)
            if "lakh" in label_low or "lpa" in label_low or "in inr (lpa)" in label_low:
                return str(int(curr))
            return str(int(curr * 100000)) if "inr" in label_low and "lakh" not in label_low else str(int(curr))

        if any(k in label_low for k in ["expected ctc", "expected compensation", "expected salary", "salary expectation"]):
            exp = self.candidate.get("expected_ctc_lakhs", 20.0)
            if "lakh" in label_low or "lpa" in label_low or "in inr (lpa)" in label_low:
                return str(int(exp))
            return str(int(exp * 100000)) if "inr" in label_low and "lakh" not in label_low else str(int(exp))

        # 6. Current City / Location
        if any(k in label_low for k in ["current city", "current location", "where are you located", "address"]):
            return self.candidate.get("primary_location", "Hyderabad, India")

        # 7. LinkedIn / Portfolio URL
        if "linkedin" in label_low:
            return f"https://www.{self.candidate.get('linkedin', 'linkedin.com/in/lavkushry')}"
        if "github" in label_low:
            return f"https://{self.candidate.get('github', 'github.com/lavkushry')}"
        if "website" in label_low or "portfolio" in label_low:
            return f"https://{self.candidate.get('github', 'github.com/lavkushry')}"

        # 8. Highest Degree / College
        if any(k in label_low for k in ["degree", "education", "highest qualification"]):
            return self.candidate.get("education_degree", "Bachelor's Degree")
        if any(k in label_low for k in ["university", "college", "school", "institution"]):
            return self.candidate.get("education_school", "Maharishi Dayanand University (MDU)")

        # 9. Generic numeric questions (default to 2 or 15 depending on context)
        if any(k in label_low for k in ["experience", "years"]):
            return "2"

        return None

    def determine_radio_answer(self, prompt_text: str) -> bool:
        """
        Determines True (Yes) or False (No) for binary screening questions.
        Standard rules:
        - Work authorization in India: True (Yes)
        - Visa sponsorship required: False (No)
        - Relocation / Commute / Hybrid: True (Yes)
        - Background check / Drug test: True (Yes)
        - Degree completed: True (Yes)
        """
        p_low = prompt_text.lower().strip()

        # Visa sponsorship: "Will you now or in the future require sponsorship?" -> NO
        if any(k in p_low for k in ["require sponsorship", "need sponsorship", "require visa", "need visa"]):
            return False

        # Work authorization: "Are you legally authorized to work in India?" -> YES
        if any(k in p_low for k in ["authorized to work", "legally authorized", "right to work", "eligible to work"]):
            return True

        # Relocation / Commuting / In-office
        if any(k in p_low for k in ["relocate", "relocation", "commute", "travel", "hybrid", "on-site", "in-person", "work from office"]):
            return True

        # Background verification / agreement
        if any(k in p_low for k in ["background check", "drug test", "consent", "agree", "certify", "confirm"]):
            return True

        # Education / Degree completed
        if any(k in p_low for k in ["completed", "degree", "bachelor", "graduated"]):
            return True

        # Default affirmative for suitability questions
        return True

    def find_best_dropdown_option(self, options: List[str], prompt_text: str) -> Optional[str]:
        """Finds best matching dropdown option for a given question prompt."""
        p_low = prompt_text.lower().strip()
        opts_low = [o.lower().strip() for o in options]

        # 1. Notice period dropdown
        if any(k in p_low for k in ["notice", "joining", "how soon"]):
            for target in ["15 days", "immediate", "less than 15", "15-30", "1 month", "30 days"]:
                for idx, o in enumerate(opts_low):
                    if target in o:
                        return options[idx]

        # 2. Education dropdown
        if any(k in p_low for k in ["education", "degree", "qualification"]):
            for target in ["bachelor", "b.tech", "graduate", "undergraduate", "engineering"]:
                for idx, o in enumerate(opts_low):
                    if target in o:
                        return options[idx]

        # 3. Work Authorization / Sponsorship
        if any(k in p_low for k in ["sponsorship", "visa"]):
            for idx, o in enumerate(opts_low):
                if any(w in o for w in ["no", "do not", "not require", "false"]):
                    return options[idx]

        if any(k in p_low for k in ["authorized", "right to work"]):
            for idx, o in enumerate(opts_low):
                if any(w in o for w in ["yes", "authorized", "eligible", "true"]):
                    return options[idx]

        # 4. English / Language proficiency
        if any(k in p_low for k in ["english", "language", "proficiency"]):
            for target in ["professional", "fluent", "native", "advanced", "intermediate"]:
                for idx, o in enumerate(opts_low):
                    if target in o:
                        return options[idx]

        # 5. Experience dropdown brackets (e.g. "1-3 years", "2-4 years")
        if any(k in p_low for k in ["experience", "years"]):
            for target in ["2-3", "2 to 3", "2-4", "2+", "2 years", "1-3"]:
                for idx, o in enumerate(opts_low):
                    if target in o:
                        return options[idx]

        # Fallback: Prefer "Yes" or first non-placeholder option
        for idx, o in enumerate(opts_low):
            if o in ["yes", "agree", "comfortable"]:
                return options[idx]

        for idx, o in enumerate(options):
            if not any(ph in opts_low[idx] for ph in ["select", "choose", "none", "--"]):
                return options[idx]

        return options[0] if options else None

    async def solve_all_questions_in_step(self, modal: Any, page: Optional[Any] = None) -> List[Dict[str, Any]]:
        """
        Scans all form elements in current modal step and fills answers.
        Returns list of handled question records for logging.
        """
        handled_records = []
        if not modal:
            return handled_records

        # 1. Handle Text / Number Inputs
        input_selectors = [
            "input[type='text']",
            "input[type='number']",
            "input[type='tel']",
            "textarea"
        ]
        for sel in input_selectors:
            loc = modal.locator(sel) if hasattr(modal, "locator") else None
            cnt = await safe_count(loc)
            for i in range(cnt):
                item = loc.nth(i) if hasattr(loc, "nth") else loc
                if not await safe_is_visible(item):
                    continue

                # Check if already filled
                curr_val = ""
                if hasattr(item, "input_value"):
                    try:
                        res = item.input_value()
                        curr_val = await res if inspect.isawaitable(res) else res
                    except Exception:
                        pass
                if curr_val and curr_val.strip():
                    continue

                # Discover label text
                label_text = await self._find_label_for_element(item, modal)
                ans = self.determine_text_answer(label_text)
                if ans is not None:
                    await self._type_value(item, ans)
                    handled_records.append({"type": "text", "question": label_text, "answer": ans})

        # 2. Handle Radio Groups (Fieldsets)
        fs_loc = modal.locator("fieldset") if hasattr(modal, "locator") else None
        fs_cnt = await safe_count(fs_loc)
        for i in range(fs_cnt):
            fs = fs_loc.nth(i) if hasattr(fs_loc, "nth") else fs_loc
            if not await safe_is_visible(fs):
                continue

            legend_text = await safe_inner_text(fs.locator("legend")) if hasattr(fs, "locator") else ""
            if not legend_text:
                continue

            # Determine Yes vs No preference
            wants_yes = self.determine_radio_answer(legend_text)
            target_str = "yes" if wants_yes else "no"

            radios = fs.locator("input[type='radio']") if hasattr(fs, "locator") else None
            r_cnt = await safe_count(radios)
            clicked = False
            for r_idx in range(r_cnt):
                r = radios.nth(r_idx) if hasattr(radios, "nth") else radios
                label_loc = fs.locator(f"label[for='{r_idx}']") if hasattr(fs, "locator") else None
                r_text = await safe_inner_text(r.locator("xpath=..")) if hasattr(r, "locator") else ""
                val = ""
                if hasattr(r, "get_attribute"):
                    try:
                        res = r.get_attribute("value")
                        val = await res if inspect.isawaitable(res) else res
                    except Exception:
                        pass
                combined = f"{r_text} {val}".lower()

                if target_str in combined:
                    if hasattr(r, "check"):
                        res_c = r.check()
                        if inspect.isawaitable(res_c):
                            await res_c
                    elif hasattr(r, "click"):
                        res_c = r.click()
                        if inspect.isawaitable(res_c):
                            await res_c
                    clicked = True
                    handled_records.append({"type": "radio", "question": legend_text, "answer": target_str.capitalize()})
                    break

            if not clicked and r_cnt > 0:
                # Fallback: check first radio
                first_r = radios.first if hasattr(radios, "first") else radios
                if hasattr(first_r, "check"):
                    res_c = first_r.check()
                    if inspect.isawaitable(res_c):
                        await res_c

        # 3. Handle Native Select Dropdowns
        sel_loc = modal.locator("select") if hasattr(modal, "locator") else None
        sel_cnt = await safe_count(sel_loc)
        for i in range(sel_cnt):
            select_el = sel_loc.nth(i) if hasattr(sel_loc, "nth") else sel_loc
            if not await safe_is_visible(select_el):
                continue

            label_text = await self._find_label_for_element(select_el, modal)
            # Gather options text
            opt_loc = select_el.locator("option") if hasattr(select_el, "locator") else None
            opt_cnt = await safe_count(opt_loc)
            opt_texts = []
            for o_i in range(opt_cnt):
                o = opt_loc.nth(o_i) if hasattr(opt_loc, "nth") else opt_loc
                t = await safe_inner_text(o)
                if t:
                    opt_texts.append(t)

            best_opt = self.find_best_dropdown_option(opt_texts, label_text)
            if best_opt and hasattr(select_el, "select_option"):
                try:
                    res_s = select_el.select_option(label=best_opt)
                    if inspect.isawaitable(res_s):
                        await res_s
                    handled_records.append({"type": "select", "question": label_text, "answer": best_opt})
                except Exception:
                    pass

        return handled_records

    async def _find_label_for_element(self, element: Any, modal: Any) -> str:
        """Finds associated label or description text for a form element."""
        # 1. aria-label attribute
        if hasattr(element, "get_attribute"):
            try:
                res = element.get_attribute("aria-label")
                aria = await res if inspect.isawaitable(res) else res
                if aria and aria.strip():
                    return aria.strip()
            except Exception:
                pass

        # 2. Associated label via for="id"
        elem_id = ""
        if hasattr(element, "get_attribute"):
            try:
                res = element.get_attribute("id")
                elem_id = await res if inspect.isawaitable(res) else res
            except Exception:
                pass

        if elem_id and hasattr(modal, "locator"):
            label_loc = modal.locator(f"label[for='{elem_id}']")
            if await safe_count(label_loc) > 0:
                t = await safe_inner_text(label_loc.first)
                if t:
                    return t

        # 3. Closest parent label or form-element wrapper
        if hasattr(element, "locator"):
            parent_loc = element.locator("xpath=ancestor::div[contains(@class, 'form-element') or contains(@class, 'jobs-easy-apply-form-section')][1]")
            if await safe_count(parent_loc) > 0:
                text = await safe_inner_text(parent_loc.first)
                return " ".join(text.split()[:20])

        return ""

    async def _type_value(self, item: Any, value: str):
        """Types value into input with human-like randomized delays."""
        try:
            if hasattr(item, "fill"):
                res = item.fill(value)
                if inspect.isawaitable(res):
                    await res
            elif hasattr(item, "type"):
                res = item.type(value, delay=random.randint(30, 70))
                if inspect.isawaitable(res):
                    await res
        except Exception as e:
            logger.debug("Notice typing value '%s': %s", value, e)


# ==============================================================================
# 2. MULTI-STEP MODAL NAVIGATOR
# ==============================================================================

class LinkedInEasyApplyNavigator:
    """
    Coordinates end-to-end multi-step Easy Apply dialog navigation.
    Handles resume file attachment, questionnaire answers, 'Follow company' unchecking,
    dry-run simulation, and live submission verification.
    """

    MODAL_SELECTORS = [
        "div.jobs-easy-apply-modal",
        "div[data-test-modal]",
        "div.jobs-easy-apply-content",
        "div[role='dialog'][aria-labelledby*='easy-apply']",
        "div[role='dialog']",
    ]

    EASY_APPLY_BUTTON_SELECTORS = [
        "button.jobs-apply-button",
        "button[data-job-id][class*='jobs-apply-button']",
        "div.jobs-apply-button--top-card button",
        "button:has-text('Easy Apply')",
        "button[aria-label*='Easy Apply']",
    ]

    NEXT_BUTTON_SELECTORS = [
        "button[data-easy-apply-next-button]",
        "button[aria-label='Continue to next step']",
        "button:has-text('Next')",
    ]

    REVIEW_BUTTON_SELECTORS = [
        "button[aria-label='Review your application']",
        "button:has-text('Review')",
    ]

    SUBMIT_BUTTON_SELECTORS = [
        "button[data-live-test-easy-apply-submit-button]",
        "button[aria-label='Submit application']",
        "button:has-text('Submit application')",
        "button:has-text('Submit')",
    ]

    DISMISS_BUTTON_SELECTORS = [
        "button[aria-label='Dismiss']",
        "button[data-test-modal-close-btn]",
        "button.artdeco-modal__dismiss",
    ]

    DISCARD_CONFIRM_SELECTORS = [
        "button[data-control-name='discard_application_confirm_btn']",
        "button:has-text('Discard')",
        "button[data-test-dialog-primary-btn]",
    ]

    def __init__(self, solver: Optional[LinkedInScreeningSolver] = None):
        self.solver = solver or LinkedInScreeningSolver()

    async def is_easy_apply_available(self, page: Any) -> bool:
        """Determines if the active job page features a native Easy Apply button."""
        for sel in self.EASY_APPLY_BUTTON_SELECTORS:
            if hasattr(page, "locator"):
                loc = page.locator(sel)
                if await safe_count(loc) > 0 and await safe_is_visible(loc.first):
                    text = await safe_inner_text(loc.first)
                    if "easy apply" in text.lower():
                        return True
        return False

    async def open_easy_apply_modal(self, page: Any) -> Optional[Any]:
        """Clicks the Easy Apply button and waits for the modal container."""
        for sel in self.EASY_APPLY_BUTTON_SELECTORS:
            loc = page.locator(sel) if hasattr(page, "locator") else None
            if await safe_count(loc) > 0 and await safe_is_visible(loc.first):
                try:
                    res_c = loc.first.click()
                    if inspect.isawaitable(res_c):
                        await res_c
                    break
                except Exception:
                    continue

        # Wait for modal container
        for m_sel in self.MODAL_SELECTORS:
            if hasattr(page, "locator"):
                m_loc = page.locator(m_sel)
                if await safe_count(m_loc) > 0:
                    return m_loc.first

        return None

    async def handle_resume_attachment(self, modal: Any, resume_path: str) -> bool:
        """
        Attaches the candidate resume PDF if a file upload input is present,
        or ensures an existing resume is selected.
        """
        if not os.path.exists(resume_path):
            logger.warning("Resume file does not exist at '%s'. Skipping attachment.", resume_path)
            return False

        file_input = modal.locator("input[type='file']") if hasattr(modal, "locator") else None
        if await safe_count(file_input) > 0:
            try:
                res_u = file_input.first.set_input_files(resume_path)
                if inspect.isawaitable(res_u):
                    await res_u
                logger.info("Successfully attached resume '%s'", os.path.basename(resume_path))
                return True
            except Exception as e:
                logger.debug("Notice during file upload: %s", e)

        return False

    async def uncheck_follow_company(self, modal: Any) -> bool:
        """Locates and unchecks the 'Follow company' checkbox before application submission."""
        follow_selectors = [
            "input#follow-company-checkbox",
            "input[type='checkbox'][id*='follow']",
            "label[for*='follow']",
            "label:has-text('Follow')",
        ]

        for sel in follow_selectors:
            loc = modal.locator(sel) if hasattr(modal, "locator") else None
            cnt = await safe_count(loc)
            for i in range(cnt):
                item = loc.nth(i) if hasattr(loc, "nth") else loc
                if await safe_is_checked(item):
                    try:
                        res_un = item.uncheck()
                        if inspect.isawaitable(res_un):
                            await res_un
                        logger.info("Unchecked 'Follow company' checkbox.")
                        return True
                    except Exception:
                        try:
                            res_c = item.click()
                            if inspect.isawaitable(res_c):
                                await res_c
                            return True
                        except Exception:
                            pass
        return False

    async def dismiss_modal(self, page: Any, modal: Optional[Any] = None) -> bool:
        """Cleanly dismisses the modal and confirms discard if prompted."""
        # Click Dismiss button
        for d_sel in self.DISMISS_BUTTON_SELECTORS:
            loc = page.locator(d_sel) if hasattr(page, "locator") else None
            if await safe_count(loc) > 0 and await safe_is_visible(loc.first):
                try:
                    res_c = loc.first.click()
                    if inspect.isawaitable(res_c):
                        await res_c
                    break
                except Exception:
                    continue

        # Check if "Discard application?" confirmation appears
        for disc_sel in self.DISCARD_CONFIRM_SELECTORS:
            loc = page.locator(disc_sel) if hasattr(page, "locator") else None
            if await safe_count(loc) > 0 and await safe_is_visible(loc.first):
                try:
                    res_c = loc.first.click()
                    if inspect.isawaitable(res_c):
                        await res_c
                    return True
                except Exception:
                    pass

        return True

    async def execute_easy_apply(
        self,
        page: Any,
        job_info: Dict[str, Any],
        resume_path: Optional[str] = None,
        dry_run: bool = False,
        max_steps: int = 12
    ) -> Dict[str, Any]:
        """
        Executes end-to-end multi-step application workflow for a specific vacancy.
        Returns execution result dictionary with audit trail.
        """
        job_id = job_info.get("job_id", "unknown")
        title = job_info.get("title", "Azure Data Engineer")
        company = job_info.get("company", "Company")
        url = job_info.get("url", f"https://www.linkedin.com/jobs/view/{job_id}/")
        r_path = resume_path or RESUME_PDF_PATH

        logger.info("Starting Easy Apply for Job %s: '%s' at '%s' (dry_run=%s)", job_id, title, company, dry_run)

        # 1. Open modal
        modal = await self.open_easy_apply_modal(page)
        if not modal:
            logger.warning("Could not find or open Easy Apply modal for job %s", job_id)
            return {
                "success": False,
                "status": "MODAL_FAILED",
                "job_id": job_id,
                "title": title,
                "company": company,
                "url": url,
                "detail": "Failed to open Easy Apply modal dialog"
            }

        step_count = 0
        all_answers_audit: List[Dict[str, Any]] = []

        # 2. Multi-step progression loop
        while step_count < max_steps:
            step_count += 1
            await humanized_delay(800, 1500, page=page)

            # Solve all questions in current view
            step_answers = await self.solver.solve_all_questions_in_step(modal, page=page)
            if step_answers:
                all_answers_audit.extend(step_answers)

            # Handle resume attachment if on upload step
            await self.handle_resume_attachment(modal, r_path)

            # Check if SUBMIT button is available (Final Step)
            submit_loc = None
            for s_sel in self.SUBMIT_BUTTON_SELECTORS:
                loc = modal.locator(s_sel) if hasattr(modal, "locator") else None
                if await safe_count(loc) > 0 and await safe_is_visible(loc.first):
                    submit_loc = loc.first
                    break

            if submit_loc:
                # We are at the final submit step!
                await self.uncheck_follow_company(modal)

                if dry_run:
                    logger.info("[DRY-RUN] Verified final step for '%s' at '%s'. Dismissing without submit.", title, company)
                    await self.dismiss_modal(page, modal)
                    return {
                        "success": True,
                        "status": "DRY_RUN_VERIFIED",
                        "job_id": job_id,
                        "title": title,
                        "company": company,
                        "url": url,
                        "steps": step_count,
                        "answers_count": len(all_answers_audit),
                        "answers": all_answers_audit
                    }
                else:
                    # LIVE SUBMISSION
                    logger.info("Executing LIVE application submission for '%s' at '%s'", title, company)
                    try:
                        res_sub = submit_loc.click()
                        if inspect.isawaitable(res_sub):
                            await res_sub
                        await humanized_delay(2000, 3500, page=page)

                        # Confirm submission on DOM
                        confirmed = await self._verify_submission_confirmation(page)
                        await self.dismiss_modal(page)

                        return {
                            "success": confirmed,
                            "status": "APPLIED" if confirmed else "SUBMITTED_UNVERIFIED",
                            "job_id": job_id,
                            "title": title,
                            "company": company,
                            "url": url,
                            "steps": step_count,
                            "answers_count": len(all_answers_audit),
                            "answers": all_answers_audit
                        }
                    except Exception as e:
                        logger.error("Error clicking submit button: %s", e)
                        await self.dismiss_modal(page)
                        return {
                            "success": False,
                            "status": "FAILED",
                            "job_id": job_id,
                            "title": title,
                            "company": company,
                            "url": url,
                            "detail": f"Submit click error: {e}"
                        }

            # Check for REVIEW button
            review_loc = None
            for r_sel in self.REVIEW_BUTTON_SELECTORS:
                loc = modal.locator(r_sel) if hasattr(modal, "locator") else None
                if await safe_count(loc) > 0 and await safe_is_visible(loc.first):
                    review_loc = loc.first
                    break

            if review_loc:
                try:
                    res_r = review_loc.click()
                    if inspect.isawaitable(res_r):
                        await res_r
                    continue
                except Exception:
                    pass

            # Check for NEXT button
            next_loc = None
            for n_sel in self.NEXT_BUTTON_SELECTORS:
                loc = modal.locator(n_sel) if hasattr(modal, "locator") else None
                if await safe_count(loc) > 0 and await safe_is_visible(loc.first):
                    next_loc = loc.first
                    break

            if next_loc:
                try:
                    res_n = next_loc.click()
                    if inspect.isawaitable(res_n):
                        await res_n
                    continue
                except Exception:
                    pass

            # Neither Submit, Review, nor Next was clickable or found
            logger.warning("No forward progression button found on step %s. Aborting modal.", step_count)
            break

        # If loop exited without submitting or dry-run return
        await self.dismiss_modal(page, modal)
        return {
            "success": False,
            "status": "STALLED",
            "job_id": job_id,
            "title": title,
            "company": company,
            "url": url,
            "steps": step_count,
            "detail": "Modal workflow did not reach submit button within step limit"
        }

    async def _verify_submission_confirmation(self, page: Any) -> bool:
        """Verifies presence of submission confirmation on the DOM."""
        success_indicators = [
            "h3:has-text('Application submitted')",
            "div:has-text('Your application was sent to')",
            "div.artdeco-modal:has-text('submitted')",
            "span:has-text('Application submitted')",
        ]

        for ind in success_indicators:
            if hasattr(page, "locator"):
                loc = page.locator(ind)
                if await safe_count(loc) > 0:
                    return True

        return False


# ==============================================================================
# 3. UNIFIED APPLICATION TRACKER (EXCEL & JSON)
# ==============================================================================

class LinkedInApplicationTracker:
    """
    Maintains persistent audit logs of LinkedIn applications.
    Writes to 'LinkedIn_Applications_Log' in Naukri_Live_Application_Tracker.xlsx,
    updates linkedin_applications_log.json, and syncs skip_list_linkedin.json.
    """

    EXCEL_HEADERS = [
        "Application Date",
        "Company Name",
        "Job Title",
        "Match Score (%)",
        "Role Category",
        "Location",
        "Application Type",
        "Status",
        "Job URL",
        "Easy Apply Steps",
        "Recruiter Response"
    ]

    def __init__(
        self,
        excel_path: Optional[str] = None,
        json_log_path: Optional[str] = None,
        skip_file_path: Optional[str] = None
    ):
        target_ws = os.getenv("WORKSPACE_DIR") or WORKSPACE_DIR
        self.excel_path = excel_path or TRACKER_PATH
        self.json_log_path = json_log_path or os.path.join(target_ws, "linkedin_applications_log.json")
        self.skip_file_path = skip_file_path or os.path.join(target_ws, "skip_list_linkedin.json")
        self._ensure_excel_sheet()

    def _ensure_excel_sheet(self):
        """Ensures the 'LinkedIn_Applications_Log' worksheet exists with proper headers."""
        try:
            if not os.path.exists(self.excel_path):
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "LinkedIn_Applications_Log"
                ws.append(self.EXCEL_HEADERS)
                wb.save(self.excel_path)
            else:
                wb = openpyxl.load_workbook(self.excel_path)
                if "LinkedIn_Applications_Log" not in wb.sheetnames:
                    ws = wb.create_sheet(title="LinkedIn_Applications_Log")
                    ws.append(self.EXCEL_HEADERS)
                    wb.save(self.excel_path)
        except Exception as e:
            logger.debug("Notice ensuring Excel sheet: %s", e)

    def log_application(
        self,
        job_data: Dict[str, Any],
        status: str,
        match_score: Optional[float] = None,
        steps: int = 1
    ) -> bool:
        """Logs an application event to Excel, JSON audit log, and skip list."""
        company = job_data.get("company", "Unknown Employer")
        title = job_data.get("title", "Azure Data Engineer")
        location = job_data.get("location", "India")
        url = job_data.get("url", "N/A")
        job_id = str(job_data.get("job_id", ""))
        score_val = f"{int(match_score)}%" if match_score is not None else "85%"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        # 1. Append to Excel
        try:
            if os.path.exists(self.excel_path):
                wb = openpyxl.load_workbook(self.excel_path)
                ws = wb["LinkedIn_Applications_Log"] if "LinkedIn_Applications_Log" in wb.sheetnames else wb.active
                ws.append([
                    timestamp,
                    company,
                    title,
                    score_val,
                    "Azure Data Engineer",
                    location,
                    "LinkedIn Easy Apply",
                    status,
                    url,
                    str(steps),
                    "Pending Initial Review"
                ])
                wb.save(self.excel_path)
        except Exception as e:
            logger.warning("Failed appending to tracker Excel: %s", e)

        # 2. Append to JSON Audit Log
        record = {
            "timestamp": timestamp,
            "job_id": job_id,
            "company": company,
            "title": title,
            "location": location,
            "url": url,
            "status": status,
            "match_score": score_val,
            "steps": steps
        }
        try:
            existing_log = []
            if os.path.exists(self.json_log_path):
                with open(self.json_log_path, "r", encoding="utf-8") as f:
                    existing_log = json.load(f)
            existing_log.append(record)
            with open(self.json_log_path, "w", encoding="utf-8") as f:
                json.dump(existing_log, f, indent=2)
        except Exception as e:
            logger.debug("Notice saving JSON application log: %s", e)

        # 3. Add to Skip List if successfully applied or dry-run verified
        if job_id and status in ["APPLIED", "DRY_RUN_VERIFIED"]:
            try:
                skip_set = set()
                if os.path.exists(self.skip_file_path):
                    with open(self.skip_file_path, "r", encoding="utf-8") as f:
                        skip_set = set(json.load(f))
                skip_set.add(job_id)
                with open(self.skip_file_path, "w", encoding="utf-8") as f:
                    json.dump(sorted(list(skip_set)), f, indent=2)
            except Exception as e:
                logger.debug("Notice updating skip list: %s", e)

        return True

    def is_applied(self, job_id: str) -> bool:
        """Checks if a job has already been applied or recorded in skip list."""
        if not job_id:
            return False
        j_id = str(job_id)
        if os.path.exists(self.skip_file_path):
            try:
                with open(self.skip_file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if j_id in data:
                        return True
            except Exception:
                pass
        return False


# ==============================================================================
# 4. MASTER LINKEDIN APPLY ENGINE
# ==============================================================================

class LinkedInApplyEngine:
    """
    Master coordinator orchestrating precision job search, match scoring gate (>= 70.0%),
    deduplication, and autonomous Easy Apply execution.
    """

    def __init__(
        self,
        session_manager: Optional[LinkedInSessionManager] = None,
        search_engine: Optional[LinkedInSearchEngine] = None,
        navigator: Optional[LinkedInEasyApplyNavigator] = None,
        tracker: Optional[LinkedInApplicationTracker] = None,
        min_score: float = 70.0
    ):
        self.session_manager = session_manager or LinkedInSessionManager()
        self.search_engine = search_engine or LinkedInSearchEngine()
        self.navigator = navigator or LinkedInEasyApplyNavigator()
        self.tracker = tracker or LinkedInApplicationTracker()
        self.min_score = min_score
        self.scorer = JobMatchScorer()

    async def run_apply_cycle(
        self,
        keywords: Optional[List[str]] = None,
        locations: Optional[List[str]] = None,
        limit: int = 25,
        dry_run: bool = False,
        headless: bool = True
    ) -> Dict[str, Any]:
        """
        Executes a single autonomous apply cycle across target locations and keywords.
        Strictly enforces 25-30 applications limit, match score >= 70.0%, and process lock.
        """
        from playwright.async_api import async_playwright

        lock = self.session_manager.get_lock()
        if not lock.acquire(blocking=True):
            raise LinkedInSessionError("Could not acquire exclusive LinkedIn session lock. Another run is active.")

        stats = {
            "discovered": 0,
            "scored_above_threshold": 0,
            "applied": 0,
            "dry_run_verified": 0,
            "skipped": 0,
            "failed": 0,
            "jobs": []
        }

        try:
            target_keywords = keywords or DEFAULT_KEYWORDS[:3]
            target_locations = locations or ["Bengaluru", "Hyderabad", "Pune", "Gurugram", "Noida", "Remote"]

            async with async_playwright() as p:
                context = await self.session_manager.create_stealth_context(p, headless=headless)
                try:
                    page = context.pages[0] if (hasattr(context, "pages") and context.pages) else await context.new_page()

                    # 1. Verify session freshness
                    diag = await self.session_manager.verify_session(page, raise_for_status=False)
                    if diag.get("status") != "VALID":
                        logger.error("Session verification failed: %s", diag.get("status"))
                        return stats

                    logger.info("Session verified for '%s'. Beginning precision job discovery...", diag.get("candidate_name"))

                    # 2. Iterate through location & keyword matrix
                    for loc in target_locations:
                        if (stats["applied"] + stats["dry_run_verified"]) >= limit:
                            break

                        for kw in target_keywords:
                            if (stats["applied"] + stats["dry_run_verified"]) >= limit:
                                break

                            logger.info("Searching vacancies: keyword='%s', location='%s'", kw, loc)
                            search_res = await self.search_engine.search_jobs(
                                page=page,
                                keyword=kw,
                                location=loc,
                                max_pages=1,
                                easy_apply_only=True,
                                min_match_score=self.min_score
                            )

                            vacancies = search_res if isinstance(search_res, list) else search_res.get("jobs", [])
                            stats["discovered"] += len(vacancies)

                            for job in vacancies:
                                if (stats["applied"] + stats["dry_run_verified"]) >= limit:
                                    break

                                job_id = str(job.get("job_id", ""))
                                if not job_id or self.tracker.is_applied(job_id):
                                    stats["skipped"] += 1
                                    continue

                                # 3. Match Scoring Gate (>= 70.0%)
                                score_res = self.scorer.evaluate(
                                    job_title=job.get("title", ""),
                                    job_description=job.get("raw_snippet", "")
                                )

                                if not score_res.passed or score_res.score < self.min_score:
                                    logger.info(
                                        "Job %s ('%s') gated out: score %.1f%% < %.1f%%",
                                        job_id, job.get("title"), score_res.score, self.min_score
                                    )
                                    stats["skipped"] += 1
                                    continue

                                stats["scored_above_threshold"] += 1
                                logger.info(
                                    "Target Vacancy Qualified: '%s' at '%s' (Score: %.1f%%). Navigating to Easy Apply...",
                                    job.get("title"), job.get("company"), score_res.score
                                )

                                # 4. Navigate directly to job view URL
                                try:
                                    res_g = page.goto(job.get("url", f"https://www.linkedin.com/jobs/view/{job_id}/"), wait_until="domcontentloaded")
                                    if inspect.isawaitable(res_g):
                                        await res_g
                                    await humanized_delay(1500, 2500, page=page)
                                except Exception as e:
                                    logger.warning("Error navigating to job %s: %s", job_id, e)
                                    stats["failed"] += 1
                                    continue

                                # 5. Execute Easy Apply Workflow
                                app_res = await self.navigator.execute_easy_apply(
                                    page=page,
                                    job_info=job,
                                    resume_path=RESUME_PDF_PATH,
                                    dry_run=dry_run
                                )

                                job_record = {
                                    "job_id": job_id,
                                    "title": job.get("title"),
                                    "company": job.get("company"),
                                    "score": score_res.score,
                                    "status": app_res.get("status"),
                                    "success": app_res.get("success", False)
                                }
                                stats["jobs"].append(job_record)

                                if app_res.get("status") == "DRY_RUN_VERIFIED":
                                    stats["dry_run_verified"] += 1
                                    self.tracker.log_application(job, "DRY_RUN_VERIFIED", match_score=score_res.score, steps=app_res.get("steps", 1))
                                elif app_res.get("status") == "APPLIED":
                                    stats["applied"] += 1
                                    self.tracker.log_application(job, "APPLIED", match_score=score_res.score, steps=app_res.get("steps", 1))
                                else:
                                    stats["failed"] += 1

                                # Randomized inter-application delay
                                await humanized_delay(2000, 4000, page=page)

                finally:
                    if hasattr(context, "close"):
                        c_res = context.close()
                        if inspect.isawaitable(c_res):
                            await c_res
        finally:
            lock.release()

        return stats
