"""
naukariPro Feature: LinkedIn Autonomous Easy Apply Bot
Milestone 3: SOTA Multi-Step "Easy Apply" Bot (Features 9-15)

Provides:
- ModalState: 18-state enum tracking finite state machine lifecycle
- EasyApplySelectors: Unified ArtDeco DOM selectors catalog with cascading fallbacks
- ResumeSelectionResult & LinkedInResumeManager: 2-tier resume attachment (card selection vs file upload with fallback)
- LinkedInCircuitBreaker & LinkedInCircuitBreakerError: Rate-limiting safety circuit breaker (3 consecutive errors, CAPTCHA, daily limit banner, jitter throttles)
- LinkedInScreeningSolver: Calibrated questionnaire regex engine for Lavkush Kumar (Azure Data Engineer, 2.5 YOE)
- LinkedInEasyApplyBot: Finite state machine multi-step navigator (Contact -> Resume -> Screening -> Review -> Submit/Discard)
- LinkedInEasyApplyNavigator: Backwards-compatible coordinator facade
"""

import os
import sys
import re
import time
import random
import inspect
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Union, Tuple

from naukari_pro.config import WORKSPACE_DIR, RESUME_PDF_PATH, load_config
from naukari_pro.modules.linkedin_session import LinkedInError

logger = logging.getLogger("naukariPro.LinkedInBot")

# ==============================================================================
# 1. STATE MACHINE ENUM & SELECTOR CATALOG
# ==============================================================================

class ModalState(str, Enum):
    """Finite State Machine states for LinkedIn Easy Apply modal progression."""
    IDLE = "IDLE"
    EVALUATING = "EVALUATING"
    TRIGGERING = "TRIGGERING"
    MODAL_MOUNTED = "MODAL_MOUNTED"
    STEP_DETECT = "STEP_DETECT"
    STEP_CONTACT = "STEP_CONTACT"
    STEP_RESUME = "STEP_RESUME"
    STEP_QUESTIONS = "STEP_QUESTIONS"
    STEP_REVIEW = "STEP_REVIEW"
    ADVANCING = "ADVANCING"
    ERROR_DETECTED = "ERROR_DETECTED"
    RESOLVING_ERROR = "RESOLVING_ERROR"
    SUBMITTING = "SUBMITTING"
    VERIFYING_SUBMISSION = "VERIFYING_SUBMISSION"
    DISCARDING = "DISCARDING"
    TERMINAL_SUCCESS = "TERMINAL_SUCCESS"
    TERMINAL_DRY_RUN = "TERMINAL_DRY_RUN"
    TERMINAL_DISCARDED = "TERMINAL_DISCARDED"
    TERMINAL_FAILED = "TERMINAL_FAILED"


class EasyApplySelectors:
    """Consolidated ArtDeco DOM Selectors for LinkedIn Easy Apply."""

    # 1. Trigger Buttons
    EASY_APPLY_BUTTONS = [
        "button.jobs-apply-button[aria-label*='Easy Apply']",
        "button.jobs-apply-button:has-text('Easy Apply')",
        "div.jobs-apply-button--top-card button[aria-label*='Easy Apply']",
        "div.jobs-apply-button--top-card button:has-text('Easy Apply')",
        "button[data-control-name='jobdetails_topcard_inapply']",
        "button[data-job-id][class*='jobs-apply-button']",
        "button:has-text('Easy Apply')",
        "button[aria-label*='Easy Apply']",
        "button.jobs-apply-button",
    ]

    EXTERNAL_APPLY_INDICATORS = [
        "apply on company website",
        "apply externally",
        "company website",
        "redirects to"
    ]

    ALREADY_APPLIED_INDICATORS = [
        "span.artdeco-inline-feedback--success:has-text('Applied')",
        "div.jobs-details-top-card__actions-container:has-text('Applied')",
        "button[disabled]:has-text('Applied')",
        "span:has-text('Applied')",
    ]

    # 2. Modal Containers
    MODAL_CONTAINERS = [
        "div.jobs-easy-apply-modal",
        "div[data-test-modal-id='easy-apply-modal']",
        "div[data-view-name='job-details-easy-apply-modal']",
        "div[data-test-modal]",
        "div.jobs-easy-apply-content",
        "div[role='dialog'][aria-labelledby*='easy-apply']",
        "div[role='dialog'][aria-labelledby*='jobs-apply']",
        "div[role='dialog']",
    ]
    MODAL_CONTENT = "div.jobs-easy-apply-modal__content, div.jobs-easy-apply-content"

    # 3. Progression & Headings
    PROGRESS_BAR = [
        "progress.artdeco-completeness-meter-bar",
        "progress",
        "div[role='progressbar'].artdeco-completeness-meter-linear__progress-container",
    ]
    STEP_HEADERS = [
        "div.jobs-easy-apply-modal__content h3",
        "div.jobs-easy-apply-modal__content h4",
        "div.jobs-easy-apply-modal h3",
        "h3.t-16",
        "h3",
        "h4",
    ]

    # 4. Action Buttons (Footer)
    NEXT_BUTTONS = [
        "button[data-easy-apply-next-button]",
        "button[aria-label='Continue to next step']",
        "button:has-text('Next')",
        "footer button.artdeco-button--primary:has-text('Next')",
    ]
    REVIEW_BUTTONS = [
        "button[aria-label='Review your application']",
        "button:has-text('Review')",
        "footer button.artdeco-button--primary:has-text('Review')",
    ]
    SUBMIT_BUTTONS = [
        "button[data-live-test-easy-apply-submit-button]",
        "button[aria-label='Submit application']",
        "button:has-text('Submit application')",
        "button:has-text('Submit')",
        "footer button.artdeco-button--primary:has-text('Submit')",
    ]

    # 5. Follow Company Checkbox
    FOLLOW_COMPANY_CHECKBOXES = [
        "input#follow-company-checkbox",
        "input[type='checkbox'][id*='follow-company']",
        "input[type='checkbox'][id*='follow']",
        "input[type='checkbox'][name*='follow']",
        "div.jobs-easy-apply-footer__consent input[type='checkbox']",
        "label[for*='follow']",
        "label:has-text('Follow')",
    ]

    # 6. Validation Errors
    INLINE_ERRORS = [
        "div.artdeco-inline-feedback--error",
        "div.fb-form-element--error",
        "span.artdeco-inline-feedback__message",
        "p.artdeco-inline-feedback__message",
        "div[data-test-form-element-error-messages]",
    ]

    # 7. Dismiss & Discard Modal
    DISMISS_BUTTONS = [
        "button[aria-label='Dismiss']",
        "button[data-test-modal-close-btn]",
        "button.artdeco-modal__dismiss",
    ]
    DISCARD_CONFIRM_DIALOG = [
        "div.artdeco-modal--layer-confirmation",
        "div[role='alertdialog']",
        "div[data-test-modal-id='discard-confirmation-modal']",
    ]
    DISCARD_CONFIRM_BUTTONS = [
        "button[data-control-name='discard_application_confirm_btn']",
        "button[data-test-dialog-secondary-action]",
        "button[data-test-dialog-primary-btn]:has-text('Discard')",
        "button:has-text('Discard')",
        "button[data-test-dialog-primary-btn]",
        "div.artdeco-modal button:has-text('Discard')",
    ]

    # 8. Post-Submission Confirmation
    CONFIRMATION_BANNERS = [
        "h3:has-text('Application submitted')",
        "div:has-text('Your application was sent to')",
        "div.artdeco-modal:has-text('Application submitted')",
        "div.artdeco-modal:has-text('submitted')",
        "span:has-text('Application submitted')",
        "span:has-text('Application sent')",
    ]
    CONFIRMATION_DONE_BUTTONS = [
        "button:has-text('Done')",
        "button[aria-label='Done']",
        "button[data-control-name='submit_application_dismiss']",
        "button.artdeco-button--primary:has-text('Done')",
        "button[aria-label='Dismiss']",
    ]


# ==============================================================================
# 2. UTILITY SAFE ASYNC HELPERS
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
    apply_mod = sys.modules.get("naukari_pro.modules.linkedin_apply")
    if apply_mod and hasattr(apply_mod, "humanized_delay"):
        curr_fn = getattr(apply_mod, "humanized_delay")
        if curr_fn is not humanized_delay:
            res = curr_fn(min_ms, max_ms, page=page)
            if inspect.isawaitable(res):
                return await res
            return res

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
# 3. CANONICAL CANDIDATE PROFILE
# ==============================================================================

def get_candidate_profile() -> Dict[str, Any]:
    """Dynamically loads candidate facts from config.json with robust calibrated defaults."""
    cfg = load_config()
    cand = cfg.get("candidate", {})

    return {
        "name": cand.get("name", "Lavkush Kumar"),
        "first_name": cand.get("first_name", "Lavkush"),
        "last_name": cand.get("last_name", "Kumar"),
        "email": cand.get("email", "lavkushry@gmail.com"),
        "phone": cand.get("phone", "+91 9122036484"),
        "phone_national": cand.get("phone_national", "9122036484"),
        "phone_country_code": "+91",
        "phone_country_name": "India (+91)",
        "total_experience_years": float(cand.get("total_experience_years", 2.5)),
        "total_experience_int": 2,
        "current_company": cand.get("current_company", "CGI India (PNC Bank GCC)"),
        "current_designation": cand.get("current_designation", "Azure Data Engineer"),
        "current_ctc_lakhs": float(cand.get("current_ctc_lakhs", 12.0)),
        "expected_ctc_lakhs": float(cand.get("expected_ctc_lakhs", 20.0)),
        "notice_period_days": int(cand.get("notice_period_days", 15)),
        "notice_period_text": cand.get("notice_period", "15 Days or less"),
        "primary_location": cand.get("primary_location", "Hyderabad, India"),
        "current_city": cand.get("current_city", "Hyderabad"),
        "current_state": "Telangana",
        "country": "India",
        "postal_code": cand.get("postal_code", "500081"),
        "preferred_locations": cand.get("preferred_locations", [
            "Bengaluru", "Hyderabad", "Pune", "Gurugram", "Noida", "Mumbai", "Chennai"
        ]),
        "linkedin": cand.get("linkedin", "linkedin.com/in/lavkushry"),
        "github": cand.get("github", "github.com/lavkushry"),
        "resume_path": cand.get("resume_path", RESUME_PDF_PATH),
        "education_degree": "Bachelor's Degree",
        "education_field": "Computer Science and Engineering",
        "education_school": "Maharishi Dayanand University (MDU)",
        "graduation_year": "2023",
        "work_authorization_india": True,
        "require_sponsorship": False,
        "willing_to_relocate": True,
        "commute_onsite": True,
        "english_proficiency": "Professional",
        # Skill-specific experience calibration for 2.5 YOE profile
        "skills_experience": {
            "pyspark": 2.0,
            "azure databricks": 2.0,
            "databricks": 2.0,
            "azure data factory": 2.0,
            "adf": 2.0,
            "delta lake": 2.0,
            "medallion": 2.0,
            "lakehouse": 2.0,
            "data lakehouse": 2.0,
            "spark sql": 2.0,
            "apache spark": 2.0,
            "spark": 2.0,
            "azure": 2.5,
            "microsoft azure": 2.5,
            "sql": 2.5,
            "python": 2.5,
            "etl": 2.5,
            "elt": 2.5,
            "git": 2.5,
            "kafka": 1.5,
            "apache kafka": 1.5,
            "terraform": 1.5,
            "docker": 2.0,
            "kubernetes": 2.0,
            "ci/cd": 2.0,
            "devops": 2.0,
            "data modeling": 2.0,
            "azure synapse": 1.5,
            "synapse": 1.5,
            "microsoft fabric": 1.0,
            "fabric": 1.0,
        }
    }


# ==============================================================================
# 4. RESUME MANAGER (2-TIER CARD VS UPLOAD WITH FALLBACK)
# ==============================================================================

@dataclass
class ResumeSelectionResult:
    """Outcome payload of resume attachment operation."""
    success: bool
    method: str  # "CARD_SELECTED", "FILE_UPLOADED", "SKIPPED_NOT_FOUND", "FAILED"
    filename: str
    detail: str = ""


class LinkedInResumeManager:
    """Handles resume attachment via file upload or selecting pre-existing saved cards."""

    CARD_CONTAINER_SELECTORS = [
        "div.jobs-document-upload",
        "div[data-test-jobs-document-upload]",
        "div.jobs-document-upload__title",
        "label.jobs-document-upload__file-label"
    ]

    FILE_INPUT_SELECTORS = [
        "input[type='file'][id*='resume']",
        "input[type='file'][name*='resume']",
        "input[type='file'][name*='file']",
        "input[type='file']"
    ]

    def __init__(self, primary_resume_path: Optional[str] = None, fallback_resume_path: Optional[str] = None):
        self.primary_resume = primary_resume_path or RESUME_PDF_PATH
        self.fallback_resume = fallback_resume_path or os.path.join(WORKSPACE_DIR, "Lavkush_Kumar_MLOps_Resume.pdf")

    def resolve_resume_path(self, requested_path: Optional[str] = None) -> Optional[str]:
        """Resolves existing resume file on disk with fallback chain."""
        candidates = [requested_path, self.primary_resume, self.fallback_resume]
        for p in candidates:
            if p and os.path.exists(p) and os.path.isfile(p):
                return os.path.abspath(p)
        return None

    async def attach_or_select_resume(self, modal: Any, resume_path: Optional[str] = None) -> ResumeSelectionResult:
        """
        2-Tier resume attachment:
        1. Scan modal for existing uploaded resume cards matching target name.
        2. If none matched, upload local PDF via input[type='file'].
        3. Fallback: select first available pre-existing card if present.
        """
        resolved_file = self.resolve_resume_path(resume_path)
        target_name = os.path.basename(resolved_file) if resolved_file else "Lavkush_Kumar_Azure_Data_Engineer_Resume.pdf"

        # Tier 1: Check for pre-existing resume cards on DOM
        card_selected = await self._select_existing_card(modal, target_name)
        if card_selected:
            return ResumeSelectionResult(
                success=True,
                method="CARD_SELECTED",
                filename=target_name,
                detail="Selected pre-existing resume card"
            )

        # Tier 2: Upload file via input[type='file']
        if resolved_file:
            uploaded = await self._upload_resume_file(modal, resolved_file)
            if uploaded:
                return ResumeSelectionResult(
                    success=True,
                    method="FILE_UPLOADED",
                    filename=target_name,
                    detail="Uploaded file via file input"
                )

        # Fallback: Check if any card exists as fallback (e.g. first available card)
        first_card_selected = await self._select_first_available_card(modal)
        if first_card_selected:
            return ResumeSelectionResult(
                success=True,
                method="CARD_SELECTED",
                filename="existing_default_card",
                detail="Selected first available card as fallback"
            )

        return ResumeSelectionResult(
            success=False,
            method="SKIPPED_NOT_FOUND",
            filename="",
            detail="No resume upload input or cards available on this step"
        )

    async def _select_existing_card(self, modal: Any, target_filename: str) -> bool:
        """Selects existing resume card matching target filename."""
        card_loc = modal.locator("div.jobs-document-upload") if hasattr(modal, "locator") else None
        cnt = await safe_count(card_loc)
        clean_target = target_filename.lower().replace(".pdf", "").replace("_", " ")

        for i in range(cnt):
            card = card_loc.nth(i) if hasattr(card_loc, "nth") else card_loc
            text = (await safe_inner_text(card)).lower().replace("_", " ")
            if any(term in text for term in ["azure data engineer", "lavkush kumar", clean_target]):
                radio = card.locator("input[type='radio']") if hasattr(card, "locator") else card
                if not await safe_is_checked(radio):
                    if hasattr(radio, "check"):
                        res = radio.check()
                        if inspect.isawaitable(res):
                            await res
                    elif hasattr(radio, "click"):
                        res = radio.click()
                        if inspect.isawaitable(res):
                            await res
                return True
        return False

    async def _upload_resume_file(self, modal: Any, file_path: str) -> bool:
        """Uploads file using Playwright set_input_files on hidden or styled file input."""
        for sel in self.FILE_INPUT_SELECTORS:
            file_input = modal.locator(sel) if hasattr(modal, "locator") else None
            if await safe_count(file_input) > 0:
                try:
                    res = file_input.first.set_input_files(file_path)
                    if inspect.isawaitable(res):
                        await res
                    logger.info("Attached resume '%s' via '%s'", os.path.basename(file_path), sel)
                    return True
                except Exception as e:
                    logger.debug("Notice setting input files on '%s': %s", sel, e)
        return False

    async def _select_first_available_card(self, modal: Any) -> bool:
        """Selects the first available resume radio card as a fallback."""
        radio_loc = modal.locator("div.jobs-document-upload input[type='radio']") if hasattr(modal, "locator") else None
        if await safe_count(radio_loc) > 0:
            first_radio = radio_loc.first
            if not await safe_is_checked(first_radio):
                try:
                    if hasattr(first_radio, "check"):
                        res = first_radio.check()
                        if inspect.isawaitable(res):
                            await res
                    elif hasattr(first_radio, "click"):
                        res = first_radio.click()
                        if inspect.isawaitable(res):
                            await res
                    return True
                except Exception:
                    pass
            return True
        return False


# ==============================================================================
# 5. CIRCUIT BREAKER & SAFETY CONTROLS
# ==============================================================================

class LinkedInCircuitBreakerError(LinkedInError):
    """Raised when rate-limit or safety circuit breaker trips."""
    pass


class LinkedInCircuitBreaker:
    """
    Monitors consecutive failures, security checkpoints, and daily rate limits.
    Provides calibrated throttling delays to prevent account restrictions.
    """

    DAILY_LIMIT_SELECTORS = [
        "div:has-text('reached your application limit for today')",
        "div:has-text('daily limit for Easy Apply')",
        "div:has-text('maximum number of applications today')",
        "p:has-text('application limit for today')",
        "div.artdeco-inline-feedback:has-text('limit for today')",
    ]

    CHECKPOINT_SELECTORS = [
        "input#captcha",
        "div.captcha-container",
        "iframe[src*='recaptcha']",
        "iframe[src*='arkoselabs']",
        "div:has-text('Security Verification')",
        "div:has-text('Please solve this puzzle')",
    ]

    CHECKPOINT_URL_PATTERNS = [
        "/checkpoint/challenge",
        "/checkpoint/security-check",
        "/checkpoint/rp/",
        "/uas/consumer-captcha",
        "/uas/captcha"
    ]

    def __init__(self, max_consecutive_errors: int = 3, max_daily_apps: int = 30):
        self.max_consecutive_errors = max_consecutive_errors
        self.max_daily_apps = max_daily_apps
        self.consecutive_errors: int = 0
        self.total_applied: int = 0
        self.is_tripped: bool = False
        self.trip_reason: Optional[str] = None
        self.trip_detail: str = ""

    def record_success(self):
        """Resets consecutive errors on successful application or dry-run verification."""
        self.consecutive_errors = 0
        self.total_applied += 1

    def record_failure(self, reason: str = "UNKNOWN_ERROR") -> bool:
        """Increments consecutive error count and trips if threshold reached."""
        self.consecutive_errors += 1
        logger.warning("Consecutive application error #%d: %s", self.consecutive_errors, reason)
        if self.consecutive_errors >= self.max_consecutive_errors:
            self.trip("CONSECUTIVE_ERRORS", f"{self.consecutive_errors} consecutive unresolvable errors reached.")
            return True
        return False

    def trip(self, reason: str, detail: str):
        """Immediately trips the breaker."""
        self.is_tripped = True
        self.trip_reason = reason
        self.trip_detail = detail
        logger.critical("🚨 CIRCUIT BREAKER TRIPPED [%s]: %s. Halting apply cycle.", reason, detail)

    def reset(self):
        """Resets circuit breaker state."""
        self.consecutive_errors = 0
        self.is_tripped = False
        self.trip_reason = None
        self.trip_detail = ""

    async def check_security_checkpoint(self, page: Any) -> bool:
        """Inspects page URL and DOM for security challenge or CAPTCHA."""
        url = getattr(page, "url", "") or ""
        if any(pat in url for pat in self.CHECKPOINT_URL_PATTERNS):
            self.trip("SECURITY_CHECKPOINT", f"Checkpoint URL detected: {url}")
            return True

        for sel in self.CHECKPOINT_SELECTORS:
            loc = page.locator(sel) if hasattr(page, "locator") else None
            if await safe_count(loc) > 0 and await safe_is_visible(loc.first):
                self.trip("SECURITY_CHECKPOINT", f"CAPTCHA element detected: {sel}")
                return True
        return False

    async def check_daily_rate_limit(self, page_or_modal: Any) -> bool:
        """Inspects DOM for LinkedIn daily rate limit banner."""
        for sel in self.DAILY_LIMIT_SELECTORS:
            loc = page_or_modal.locator(sel) if hasattr(page_or_modal, "locator") else None
            if await safe_count(loc) > 0 and await safe_is_visible(loc.first):
                self.trip("DAILY_LIMIT_REACHED", "LinkedIn daily application limit banner detected.")
                return True
        return False

    async def throttle_field(self, page: Optional[Any] = None):
        """Calibrated delay between field fills (150ms - 400ms)."""
        delay_sec = random.uniform(0.15, 0.40)
        await self._sleep(delay_sec, page)

    async def throttle_step(self, page: Optional[Any] = None):
        """Calibrated delay between modal steps (1.2s - 2.8s)."""
        delay_sec = random.uniform(1.2, 2.8)
        await self._sleep(delay_sec, page)

    async def throttle_inter_application(self, page: Optional[Any] = None):
        """Calibrated delay between job vacancies (3.0s - 7.0s)."""
        delay_sec = random.uniform(3.0, 7.0)
        await self._sleep(delay_sec, page)

    async def _sleep(self, delay: float, page: Optional[Any] = None):
        ms = int(delay * 1000)
        await humanized_delay(ms, ms, page=page)


# ==============================================================================
# 6. SCREENING QUESTIONNAIRE SOLVER
# ==============================================================================

class LinkedInScreeningSolver:
    """
    Solves complex multi-format application questionnaires using fuzzy regex
    and candidate facts from single source of truth.
    Handles text inputs, number inputs, radio buttons, dropdowns, and checkboxes.
    """

    def __init__(self, candidate: Optional[Dict[str, Any]] = None):
        self.candidate = candidate or get_candidate_profile()

    def get_numeric_experience_for_skill(self, text: str, integer_only: bool = False) -> str:
        """Determines calibrated years of experience for a queried skill or general YOE."""
        t_low = text.lower()
        skills = self.candidate.get("skills_experience", {})

        # Longest skill match first (e.g. 'azure data factory' before 'azure')
        sorted_skills = sorted(skills.items(), key=lambda x: len(x[0]), reverse=True)

        for skill_name, yoe in sorted_skills:
            pattern = r"\b" + re.escape(skill_name) + r"\b"
            if re.search(pattern, t_low):
                if integer_only:
                    return str(int(round(float(yoe))))
                return str(int(yoe)) if float(yoe).is_integer() else str(yoe)

        # General total experience fallback
        tot = self.candidate.get("total_experience_years", 2.5)
        if integer_only:
            return str(int(round(float(tot))))
        return str(int(tot)) if float(tot).is_integer() else str(tot)

    def determine_text_answer(self, label_text: str, integer_only: bool = False) -> Optional[str]:
        """Maps freeform or numeric question labels to candidate facts."""
        label_low = label_text.lower().strip()

        # 1. Phone number
        if any(k in label_low for k in ["phone", "mobile", "contact number", "cell"]):
            if "country" in label_low or "code" in label_low:
                return self.candidate.get("phone_country_code", "+91")
            return self.candidate.get("phone_national", "9122036484")

        # 2. Email
        if "email" in label_low:
            return self.candidate.get("email", "lavkushry@gmail.com")

        # 3. Name fields
        if any(k in label_low for k in ["first name", "given name"]):
            return self.candidate.get("first_name", "Lavkush")
        if any(k in label_low for k in ["last name", "surname", "family name"]):
            return self.candidate.get("last_name", "Kumar")
        if "full name" in label_low:
            return self.candidate.get("name", "Lavkush Kumar")

        # 4. Years of Experience (specific tech or general)
        if any(k in label_low for k in ["how many years", "years of experience", "experience with", "experience do you have", "yoe"]):
            return self.get_numeric_experience_for_skill(label_text, integer_only=integer_only)

        # 5. Notice Period
        if any(k in label_low for k in ["notice period", "notice", "how soon can you join", "joining period", "days required"]):
            if any(w in label_low for w in ["day", "numeric", "number", "days"]) or integer_only:
                return str(self.candidate.get("notice_period_days", 15))
            return self.candidate.get("notice_period_text", "15 Days or less")

        # 6. Compensation / CTC
        if any(k in label_low for k in ["current ctc", "current compensation", "current salary", "present ctc", "fixed ctc"]) or (
            ("current" in label_low or "present" in label_low) and any(w in label_low for w in ["salary", "ctc", "compensation"])
        ):
            curr = self.candidate.get("current_ctc_lakhs", 12.0)
            if any(w in label_low for w in ["lakh", "lpa", "in inr (lpa)"]):
                return str(int(curr))
            if "annual" in label_low or "inr" in label_low:
                return str(int(curr * 100000))
            return str(int(curr))

        if any(k in label_low for k in ["expected ctc", "expected compensation", "expected salary", "salary expectation", "desired ctc"]) or (
            ("expected" in label_low or "desired" in label_low) and any(w in label_low for w in ["salary", "ctc", "compensation"])
        ):
            exp = self.candidate.get("expected_ctc_lakhs", 20.0)
            if any(w in label_low for w in ["lakh", "lpa", "in inr (lpa)"]):
                return str(int(exp))
            if "annual" in label_low or "inr" in label_low:
                return str(int(exp * 100000))
            return str(int(exp))

        # 7. Current Employer & Designation
        if any(k in label_low for k in ["current company", "current employer", "present company", "organization"]):
            return self.candidate.get("current_company", "CGI India (PNC Bank GCC)")
        if any(k in label_low for k in ["current job title", "current designation", "current role", "present title"]):
            return self.candidate.get("current_designation", "Azure Data Engineer")

        # 8. Postal code & Location
        if any(k in label_low for k in ["postal code", "pin code", "zip code", "pincode"]):
            return self.candidate.get("postal_code", "500081")

        if any(k in label_low for k in ["current city", "current location", "where are you located", "address"]):
            return self.candidate.get("primary_location", "Hyderabad, India")

        if "city" in label_low:
            return self.candidate.get("current_city", "Hyderabad")
        if "state" in label_low or "province" in label_low:
            return self.candidate.get("current_state", "Telangana")
        if "country" in label_low:
            return self.candidate.get("country", "India")

        # 9. LinkedIn / Portfolio URL
        if "linkedin" in label_low:
            return f"https://www.{self.candidate.get('linkedin', 'linkedin.com/in/lavkushry')}"
        if any(k in label_low for k in ["github", "website", "portfolio", "blog"]):
            return f"https://{self.candidate.get('github', 'github.com/lavkushry')}"

        # 10. Education
        if any(k in label_low for k in ["degree", "education", "highest qualification"]):
            return self.candidate.get("education_degree", "Bachelor's Degree")
        if any(k in label_low for k in ["university", "college", "school", "institution"]):
            return self.candidate.get("education_school", "Maharishi Dayanand University (MDU)")
        if any(k in label_low for k in ["graduation year", "year of graduation", "passing year", "year of passing", "year of completion", "graduation"]):
            return self.candidate.get("graduation_year", "2023")

        # 11. Generic numeric questions (default to 2 or 15 depending on context)
        if any(k in label_low for k in ["experience", "years"]):
            return "2"

        return None

    def determine_radio_answer(self, prompt_text: str) -> bool:
        """
        Determines True (Yes) or False (No) for binary screening questions.
        Includes explicit negative guards for disqualifying queries.
        """
        p_low = prompt_text.lower().strip()

        # Handle affirmative "without sponsorship" exception before negative sponsorship check:
        if (
            "without requiring sponsorship" in p_low
            or "without sponsorship" in p_low
            or "without requiring employer sponsorship" in p_low
            or "without requiring visa" in p_low
            or bool(re.search(r"\bwithout\b.*?\b(?:requiring\s+|needing\s+)?(?:employer\s+|visa\s+)?sponsorship\b", p_low))
        ):
            return True

        # Explicit Negative Disqualifiers (Must return False / No)
        # Visa / Sponsorship questions: "require ... sponsorship", "need ... visa", etc.
        if (any(r in p_low for r in ["require", "need", "future", "will you"]) and any(s in p_low for s in ["sponsorship", "visa"])) or any(k in p_low for k in [
            "require sponsorship", "need sponsorship", "require visa", "need visa",
            "require a visa", "require work authorization sponsorship", "employer sponsorship",
            "convicted", "felony", "criminal", "misdemeanor",
            "non-compete", "noncompetition", "non-competition", "restrictive covenant", "terminated for cause",
            "disciplinary action", "disciplinary proceedings", "family member working", "relative working"
        ]):
            return False

        # Explicit Affirmative Qualifiers (Must return True / Yes)
        if any(k in p_low for k in [
            "authorized to work", "legally authorized", "right to work", "eligible to work",
            "citizen", "permanent resident",
            "relocate", "relocation", "commute", "travel", "hybrid", "on-site", "in-person", "work from office",
            "background check", "drug test", "consent", "agree", "certify", "confirm", "acknowledge",
            "completed", "degree", "bachelor", "graduated",
            "18 years", "full-time", "notice period", "immediate"
        ]):
            return True

        # Default affirmative for general suitability questions
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

        # 1. Handle Text / Number / Tel Inputs
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
                if curr_val and str(curr_val).strip():
                    continue

                # Discover label text
                label_text = await self._find_label_for_element(item, modal)
                input_type = (await item.get_attribute("type") if hasattr(item, "get_attribute") else "") or ""
                integer_only = input_type.lower() == "number"
                ans = self.determine_text_answer(label_text, integer_only=integer_only)
                if ans is not None:
                    await self._type_value(item, ans)
                    handled_records.append({"type": "text", "question": label_text, "answer": ans})

        # 2. Handle Radio Groups (Fieldsets & ArtDeco Div Containers)
        radio_containers = [
            "fieldset",
            "div[data-test-form-builder-radio-button-form-component='true']",
            "div.fb-radio-button-group",
        ]
        for fs_sel in radio_containers:
            fs_loc = modal.locator(fs_sel) if hasattr(modal, "locator") else None
            fs_cnt = await safe_count(fs_loc)
            for i in range(fs_cnt):
                fs = fs_loc.nth(i) if hasattr(fs_loc, "nth") else fs_loc
                if not await safe_is_visible(fs):
                    continue

                legend_text = ""
                if hasattr(fs, "locator"):
                    legend_text = await safe_inner_text(fs.locator("legend"))
                    if not legend_text:
                        legend_text = await safe_inner_text(fs.locator("span.fb-form-element-label"))
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
                    r_text = await safe_inner_text(r.locator("xpath=..")) if hasattr(r, "locator") else ""
                    val = ""
                    if hasattr(r, "get_attribute"):
                        try:
                            res = r.get_attribute("value")
                            val = await res if inspect.isawaitable(res) else res
                        except Exception:
                            pass
                    combined = f"{r_text} {val}".lower()

                    if re.search(r"\b" + re.escape(target_str) + r"\b", combined, re.IGNORECASE):
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

        # 4. Handle Standalone Checkboxes (Consent / Certification / Acknowledgement)
        chk_loc = modal.locator("input[type='checkbox']") if hasattr(modal, "locator") else None
        chk_cnt = await safe_count(chk_loc)
        for i in range(chk_cnt):
            chk_el = chk_loc.nth(i) if hasattr(chk_loc, "nth") else chk_loc
            if not await safe_is_visible(chk_el):
                continue

            label_text = await self._find_label_for_element(chk_el, modal)
            if not label_text and hasattr(chk_el, "inner_text"):
                label_text = await safe_inner_text(chk_el)
            if not label_text and hasattr(chk_el, "locator"):
                parent_loc = chk_el.locator("xpath=..")
                label_text = await safe_inner_text(parent_loc)

            label_lower = label_text.lower() if label_text else ""

            # Skip the Follow Company checkbox (handled specifically on the review step)
            chk_id = ""
            if hasattr(chk_el, "get_attribute"):
                try:
                    res_id = chk_el.get_attribute("id")
                    chk_id = (await res_id if inspect.isawaitable(res_id) else res_id) or ""
                except Exception:
                    pass

            if "follow-company" in chk_id.lower() or ("follow" in label_lower and "company" in label_lower):
                continue

            consent_keywords = [
                "agree", "consent", "certify", "acknowledge", "terms", "truthful", "accurate", "confirm", "background check"
            ]
            is_consent = any(kw in label_lower for kw in consent_keywords)

            # If it's a consent checkbox or has no text (standalone required checkbox)
            if is_consent or not label_lower:
                already_checked = await safe_is_checked(chk_el)
                if not already_checked:
                    clicked_chk = False
                    if hasattr(chk_el, "check"):
                        try:
                            res_c = chk_el.check()
                            if inspect.isawaitable(res_c):
                                await res_c
                            clicked_chk = True
                        except Exception:
                            pass
                    if not clicked_chk and hasattr(chk_el, "click"):
                        try:
                            res_clk = chk_el.click()
                            if inspect.isawaitable(res_clk):
                                await res_clk
                            clicked_chk = True
                        except Exception:
                            pass
                    if clicked_chk:
                        handled_records.append({"type": "checkbox", "question": label_text, "answer": True})

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
            parent_loc = element.locator(
                "xpath=ancestor::div[contains(@class, 'form-element') or contains(@class, 'jobs-easy-apply-form-section')][1]"
            )
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
# 7. SOTA MULTI-STEP EASY APPLY BOT (FEATURES 9-15)
# ==============================================================================

class LinkedInEasyApplyBot:
    """
    SOTA Multi-Step Easy Apply Bot with Finite State Machine Navigation.
    Implements Features 9-15 of PROJECT.md.
    """

    def __init__(
        self,
        page: Optional[Any] = None,
        candidate_info: Optional[Dict[str, Any]] = None,
        resume_path: Optional[str] = None,
        max_steps: int = 12,
        max_step_retries: int = 2,
        circuit_breaker: Optional[LinkedInCircuitBreaker] = None
    ):
        self.page = page
        self.candidate = candidate_info or get_candidate_profile()
        self.resume_path = resume_path or RESUME_PDF_PATH
        self.max_steps = max_steps
        self.max_step_retries = max_step_retries
        self.solver = LinkedInScreeningSolver(self.candidate)
        self.resume_manager = LinkedInResumeManager(primary_resume_path=self.resume_path)
        self.circuit_breaker = circuit_breaker or LinkedInCircuitBreaker()
        self.selectors = EasyApplySelectors()
        self.current_state = ModalState.IDLE
        self.history: List[Dict[str, Any]] = []

    def solve_question(self, question_text: str, input_type: str, options: Optional[List[str]] = None) -> Any:
        """
        Direct question solver conforming strictly to PROJECT.md interface contract.
        """
        input_type = (input_type or "").lower().strip()
        if input_type in ["text"]:
            return self.solver.determine_text_answer(question_text)
        elif input_type in ["number", "numeric"]:
            ans = self.solver.determine_text_answer(question_text, integer_only=True)
            if ans is not None:
                return ans
            return self.solver.get_numeric_experience_for_skill(question_text, integer_only=True)
        elif input_type in ["radio", "boolean"]:
            return self.solver.determine_radio_answer(question_text)
        elif input_type in ["select", "dropdown"]:
            return self.solver.find_best_dropdown_option(options or [], question_text)
        elif input_type in ["checkbox"]:
            p_low = question_text.lower()
            if any(neg in p_low for neg in ["criminal", "non-compete", "require sponsorship"]):
                return False
            return True
        return self.solver.determine_text_answer(question_text)

    async def is_easy_apply(self) -> bool:
        """Determines if the active job page features a native Easy Apply button."""
        return await self.is_easy_apply_available(self.page)

    async def is_easy_apply_available(self, page: Optional[Any] = None) -> bool:
        """Determines if the active job page features a native Easy Apply button."""
        target_page = page or self.page
        if not target_page:
            return False

        # 1. Check if already applied
        for sel in self.selectors.ALREADY_APPLIED_INDICATORS:
            if hasattr(target_page, "locator"):
                loc = target_page.locator(sel)
                if await safe_count(loc) > 0 and await safe_is_visible(loc.first):
                    return False

        # 2. Check Easy Apply buttons
        for sel in self.selectors.EASY_APPLY_BUTTONS:
            if hasattr(target_page, "locator"):
                loc = target_page.locator(sel)
                cnt = await safe_count(loc)
                if cnt > 0 and await safe_is_visible(loc.first):
                    text = (await safe_inner_text(loc.first)).lower()
                    if any(ext in text for ext in self.selectors.EXTERNAL_APPLY_INDICATORS):
                        continue
                    if "easy apply" in text:
                        return True
        return False

    async def open_modal(self) -> Optional[Any]:
        """Triggers the Easy Apply modal and waits for DOM mount."""
        return await self.open_easy_apply_modal(self.page)

    async def open_easy_apply_modal(self, page: Optional[Any] = None) -> Optional[Any]:
        """Clicks the Easy Apply button and returns the active modal container."""
        target_page = page or self.page
        if not target_page:
            return None

        self.current_state = ModalState.TRIGGERING
        clicked = False
        for sel in self.selectors.EASY_APPLY_BUTTONS:
            if hasattr(target_page, "locator"):
                loc = target_page.locator(sel)
                if await safe_count(loc) > 0 and await safe_is_visible(loc.first):
                    try:
                        res = loc.first.click()
                        if inspect.isawaitable(res):
                            await res
                        clicked = True
                        break
                    except Exception:
                        continue

        if not clicked:
            self.current_state = ModalState.TERMINAL_FAILED
            return None

        # Wait for modal container mount
        for m_sel in self.selectors.MODAL_CONTAINERS:
            if hasattr(target_page, "locator"):
                m_loc = target_page.locator(m_sel)
                if await safe_count(m_loc) > 0:
                    self.current_state = ModalState.MODAL_MOUNTED
                    return m_loc.first

        self.current_state = ModalState.TERMINAL_FAILED
        return None

    async def classify_step(self, modal: Any) -> ModalState:
        """Classifies current modal step based on action buttons, headings, and input elements."""
        if not modal:
            return ModalState.TERMINAL_FAILED

        # 1. If Submit button is visible -> STEP_REVIEW
        for s_sel in self.selectors.SUBMIT_BUTTONS:
            loc = modal.locator(s_sel) if hasattr(modal, "locator") else None
            if await safe_count(loc) > 0 and await safe_is_visible(loc.first):
                return ModalState.STEP_REVIEW

        # 2. Inspect Step Heading
        header_text = ""
        for h_sel in self.selectors.STEP_HEADERS:
            loc = modal.locator(h_sel) if hasattr(modal, "locator") else None
            if await safe_count(loc) > 0 and await safe_is_visible(loc.first):
                header_text = (await safe_inner_text(loc.first)).lower()
                break

        if any(w in header_text for w in ["contact", "phone", "email"]):
            return ModalState.STEP_CONTACT
        if any(w in header_text for w in ["resume", "cv", "document"]):
            return ModalState.STEP_RESUME
        if any(w in header_text for w in ["review", "preview"]):
            return ModalState.STEP_REVIEW

        # 3. Element inspection fallback
        if hasattr(modal, "locator"):
            if await safe_count(modal.locator("input[type='file'], div.jobs-document-upload")) > 0:
                return ModalState.STEP_RESUME
            if await safe_count(modal.locator("input[type='tel'], select[id*='country']")) > 0:
                return ModalState.STEP_CONTACT

        return ModalState.STEP_QUESTIONS

    async def detect_validation_errors(self, modal: Any) -> List[str]:
        """Extracts visible form validation error strings from modal."""
        errors = []
        if not modal or not hasattr(modal, "locator"):
            return errors

        for sel in self.selectors.INLINE_ERRORS:
            loc = modal.locator(sel)
            cnt = await safe_count(loc)
            for i in range(cnt):
                item = loc.nth(i) if hasattr(loc, "nth") else loc
                if await safe_is_visible(item):
                    msg = await safe_inner_text(item)
                    if msg and msg not in errors:
                        errors.append(msg)
        return errors

    async def auto_heal_step(self, modal: Any, attempt: int = 1) -> bool:
        """Applies self-healing fallback inputs for elements with errors."""
        self.current_state = ModalState.RESOLVING_ERROR
        if not modal or not hasattr(modal, "locator"):
            return False

        error_selectors = [
            "input[aria-invalid='true']",
            "select[aria-invalid='true']",
            "div.artdeco-inline-feedback--error input",
            "div.fb-form-element--error input",
            "div.artdeco-inline-feedback--error select",
            "div.fb-form-element--error select"
        ]

        seen_elements = set()
        for sel in error_selectors:
            invalid_inputs = modal.locator(sel)
            cnt = await safe_count(invalid_inputs)
            for i in range(cnt):
                item = invalid_inputs.nth(i) if hasattr(invalid_inputs, "nth") else invalid_inputs
                if item in seen_elements:
                    continue
                seen_elements.add(item)
                input_type = (await item.get_attribute("type") if hasattr(item, "get_attribute") else "") or ""
                input_type = input_type.lower()

                if input_type in ["number", "tel"]:
                    fallback_val = "2" if attempt == 1 else "1"
                    if hasattr(item, "fill"):
                        res = item.fill(fallback_val)
                        if inspect.isawaitable(res):
                            await res
                elif input_type in ["text"]:
                    fallback_val = self.candidate.get("primary_location", "Hyderabad, India")
                    if hasattr(item, "fill"):
                        res = item.fill(fallback_val)
                        if inspect.isawaitable(res):
                            await res
        return True

    async def advance_step(self, modal: Any) -> Tuple[bool, Optional[str]]:
        """Clicks Next or Review button to advance the modal."""
        self.current_state = ModalState.ADVANCING
        if not modal or not hasattr(modal, "locator"):
            return False, None

        # Check Review first
        for r_sel in self.selectors.REVIEW_BUTTONS:
            loc = modal.locator(r_sel)
            if await safe_count(loc) > 0 and await safe_is_visible(loc.first):
                try:
                    res = loc.first.click()
                    if inspect.isawaitable(res):
                        await res
                    return True, "REVIEW"
                except Exception:
                    pass

        # Check Next
        for n_sel in self.selectors.NEXT_BUTTONS:
            loc = modal.locator(n_sel)
            if await safe_count(loc) > 0 and await safe_is_visible(loc.first):
                try:
                    res = loc.first.click()
                    if inspect.isawaitable(res):
                        await res
                    return True, "NEXT"
                except Exception:
                    pass

        return False, None

    async def uncheck_follow_company(self, modal: Any) -> bool:
        """Locates and unchecks the 'Follow company' checkbox before application submission."""
        if not modal or not hasattr(modal, "locator"):
            return False

        for sel in self.selectors.FOLLOW_COMPANY_CHECKBOXES:
            loc = modal.locator(sel)
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
                            res_c = item.click(force=True) if hasattr(item, "click") else None
                            if inspect.isawaitable(res_c):
                                await res_c
                            return True
                        except Exception:
                            pass
        return False

    async def discard_modal(self, modal: Optional[Any] = None) -> bool:
        """Executes full clean auto-discard sequence without saving drafts."""
        return await self.dismiss_modal(self.page, modal)

    async def dismiss_modal(self, page: Optional[Any] = None, modal: Optional[Any] = None) -> bool:
        """Cleanly dismisses the modal and confirms discard if prompted."""
        target_page = page or self.page
        self.current_state = ModalState.DISCARDING

        if not target_page:
            return True

        # 1. Click Dismiss button
        for d_sel in self.selectors.DISMISS_BUTTONS:
            if hasattr(target_page, "locator"):
                loc = target_page.locator(d_sel)
                if await safe_count(loc) > 0 and await safe_is_visible(loc.first):
                    try:
                        res_c = loc.first.click()
                        if inspect.isawaitable(res_c):
                            await res_c
                        break
                    except Exception:
                        continue

        # 2. Handle Discard Confirmation Dialog
        for disc_sel in self.selectors.DISCARD_CONFIRM_BUTTONS:
            if hasattr(target_page, "locator"):
                loc = target_page.locator(disc_sel)
                if await safe_count(loc) > 0 and await safe_is_visible(loc.first):
                    try:
                        res_c = loc.first.click()
                        if inspect.isawaitable(res_c):
                            await res_c
                        self.current_state = ModalState.TERMINAL_DISCARDED
                        return True
                    except Exception:
                        pass

        self.current_state = ModalState.TERMINAL_DISCARDED
        return True

    async def verify_submission(self) -> bool:
        """Verifies presence of submission confirmation on the DOM."""
        return await self.verify_and_dismiss_submission(self.page)

    async def verify_and_dismiss_submission(self, page: Optional[Any] = None, modal: Optional[Any] = None) -> bool:
        """
        Verifies authentic application submission on the DOM and dismisses the
        post-submission 'Done' confirmation modal so subsequent jobs are not blocked.
        """
        target_page = page or self.page
        if not target_page:
            return False

        confirmed = False
        for ind in self.selectors.CONFIRMATION_BANNERS:
            if hasattr(target_page, "locator"):
                loc = target_page.locator(ind)
                if await safe_count(loc) > 0 and await safe_is_visible(loc.first):
                    confirmed = True
                    break

        # Dismiss the confirmation dialog by clicking 'Done'
        for done_sel in self.selectors.CONFIRMATION_DONE_BUTTONS:
            if hasattr(target_page, "locator"):
                loc = target_page.locator(done_sel)
                if await safe_count(loc) > 0 and await safe_is_visible(loc.first):
                    try:
                        res = loc.first.click()
                        if inspect.isawaitable(res):
                            await res
                        logger.info("Clicked 'Done' button on submission confirmation modal.")
                        break
                    except Exception as e:
                        logger.debug("Notice clicking Done button: %s", e)

        # Fallback dismiss if modal is still attached
        await self.dismiss_modal(target_page, modal)
        return confirmed

    async def handle_resume_attachment(self, modal: Any, resume_path: Optional[str] = None) -> bool:
        """Attaches the candidate resume PDF or selects an existing card."""
        res = await self.resume_manager.attach_or_select_resume(modal, resume_path or self.resume_path)
        return res.success

    async def apply_to_job(self, job_url: str, dry_run: bool = False) -> Dict[str, Any]:
        """
        Executes end-to-end multi-step Easy Apply conforming to PROJECT.md interface contract.
        """
        job_id = "job"
        match = re.search(r"/view/(\d+)", job_url or "")
        if match:
            job_id = match.group(1)

        job_info = {
            "job_id": job_id,
            "title": "Azure Data Engineer",
            "company": "Company",
            "url": job_url
        }

        if self.page and job_url:
            try:
                res_g = self.page.goto(job_url, wait_until="domcontentloaded")
                if inspect.isawaitable(res_g):
                    await res_g
                await humanized_delay(1500, 2500, page=self.page)
            except Exception as e:
                logger.warning("Error navigating to '%s': %s", job_url, e)

        return await self.execute_easy_apply(
            page=self.page,
            job_info=job_info,
            resume_path=self.resume_path,
            dry_run=dry_run,
            max_steps=self.max_steps
        )

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
        target_page = page or self.page
        job_id = str(job_info.get("job_id", "unknown"))
        title = job_info.get("title", "Azure Data Engineer")
        company = job_info.get("company", "Company")
        url = job_info.get("url", f"https://www.linkedin.com/jobs/view/{job_id}/")
        r_path = resume_path or self.resume_path

        logger.info("Starting Easy Apply for Job %s: '%s' at '%s' (dry_run=%s)", job_id, title, company, dry_run)

        # 0. Check Security Checkpoint / Daily Rate Limit before opening
        if target_page:
            if await self.circuit_breaker.check_security_checkpoint(target_page):
                return {
                    "success": False,
                    "status": "CHECKPOINT_BLOCKED",
                    "job_id": job_id,
                    "title": title,
                    "company": company,
                    "url": url,
                    "detail": "Security checkpoint detected on page"
                }

        # 1. Open modal
        modal = await self.open_easy_apply_modal(target_page)
        if not modal:
            logger.warning("Could not find or open Easy Apply modal for job %s", job_id)
            self.circuit_breaker.record_failure("MODAL_FAILED")
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
            await humanized_delay(800, 1500, page=target_page)

            # Classify current step and update FSM
            current_step_state = await self.classify_step(modal)
            self.current_state = current_step_state
            self.history.append({
                "step": step_count,
                "state": current_step_state.value if hasattr(current_step_state, "value") else str(current_step_state),
                "timestamp": time.time()
            })

            # Check daily rate limit on modal
            if await self.circuit_breaker.check_daily_rate_limit(modal):
                await self.dismiss_modal(target_page, modal)
                return {
                    "success": False,
                    "status": "RATE_LIMITED",
                    "job_id": job_id,
                    "title": title,
                    "company": company,
                    "url": url,
                    "detail": "LinkedIn daily rate limit banner detected"
                }

            # Solve all questions in current view
            step_answers = await self.solver.solve_all_questions_in_step(modal, page=target_page)
            if step_answers:
                all_answers_audit.extend(step_answers)

            # Handle resume attachment if on upload/resume step
            await self.handle_resume_attachment(modal, r_path)

            # Check if SUBMIT button is available (Final Step)
            submit_loc = None
            for s_sel in self.selectors.SUBMIT_BUTTONS:
                loc = modal.locator(s_sel) if hasattr(modal, "locator") else None
                if await safe_count(loc) > 0 and await safe_is_visible(loc.first):
                    submit_loc = loc.first
                    break

            if submit_loc:
                self.current_state = ModalState.STEP_REVIEW
                # We are at the final submit step!
                await self.uncheck_follow_company(modal)

                if dry_run:
                    logger.info("[DRY-RUN] Verified final step for '%s' at '%s'. Dismissing without submit.", title, company)
                    await self.dismiss_modal(target_page, modal)
                    self.circuit_breaker.record_success()
                    self.current_state = ModalState.TERMINAL_DRY_RUN
                    return {
                        "success": True,
                        "status": "DRY_RUN_VERIFIED",
                        "job_id": job_id,
                        "title": title,
                        "company": company,
                        "url": url,
                        "steps": step_count,
                        "answers_count": len(all_answers_audit),
                        "answers": all_answers_audit,
                        "dry_run": True
                    }
                else:
                    # LIVE SUBMISSION
                    self.current_state = ModalState.SUBMITTING
                    logger.info("Executing LIVE application submission for '%s' at '%s'", title, company)
                    try:
                        res_sub = submit_loc.click()
                        if inspect.isawaitable(res_sub):
                            await res_sub
                        await humanized_delay(2000, 3500, page=target_page)

                        # Confirm submission on DOM and dismiss 'Done' modal
                        self.current_state = ModalState.VERIFYING_SUBMISSION
                        confirmed = await self.verify_and_dismiss_submission(target_page, modal)

                        if confirmed:
                            self.circuit_breaker.record_success()
                            self.current_state = ModalState.TERMINAL_SUCCESS
                        else:
                            self.circuit_breaker.record_failure("SUBMISSION_UNVERIFIED")

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
                        await self.dismiss_modal(target_page, modal)
                        self.circuit_breaker.record_failure(f"SUBMIT_ERROR: {e}")
                        self.current_state = ModalState.TERMINAL_FAILED
                        return {
                            "success": False,
                            "status": "FAILED",
                            "job_id": job_id,
                            "title": title,
                            "company": company,
                            "url": url,
                            "detail": f"Submit click error: {e}"
                        }

            # Check for validation errors on current step
            errors = await self.detect_validation_errors(modal)
            if errors:
                logger.warning("Inline form validation errors detected: %s. Attempting auto-heal.", errors)
                healed = False
                remaining_errors = errors
                for attempt in range(1, self.max_step_retries + 1):
                    await self.auto_heal_step(modal, attempt=attempt)
                    await self.advance_step(modal)
                    # Recheck errors after advance attempt
                    remaining_errors = await self.detect_validation_errors(modal)
                    if not remaining_errors:
                        healed = True
                        break

                if not healed:
                    logger.error("Persistent unresolvable screening errors. Auto-discarding modal.")
                    await self.dismiss_modal(target_page, modal)
                    self.circuit_breaker.record_failure("UNRESOLVABLE_SCREENING_QUESTION")
                    return {
                        "success": False,
                        "status": "DISCARDED_UNRESOLVABLE",
                        "job_id": job_id,
                        "title": title,
                        "company": company,
                        "url": url,
                        "steps": step_count,
                        "detail": f"Unresolvable form validation errors: {remaining_errors}"
                    }
                continue

            # Forward progression via Next or Review button
            advanced, _ = await self.advance_step(modal)
            if advanced:
                continue

            # Neither Submit, Review, nor Next was clickable or found
            logger.warning("No forward progression button found on step %s. Aborting modal.", step_count)
            break

        # If loop exited without submitting or dry-run return
        await self.dismiss_modal(target_page, modal)
        self.circuit_breaker.record_failure("STALLED")
        self.current_state = ModalState.TERMINAL_FAILED
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


class LinkedInEasyApplyNavigator(LinkedInEasyApplyBot):
    """
    Backwards-compatible coordinator facade inheriting from LinkedInEasyApplyBot.
    Maintains exact legacy interface for existing tests and callers.
    """

    MODAL_SELECTORS = EasyApplySelectors.MODAL_CONTAINERS
    EASY_APPLY_BUTTON_SELECTORS = EasyApplySelectors.EASY_APPLY_BUTTONS
    NEXT_BUTTON_SELECTORS = EasyApplySelectors.NEXT_BUTTONS
    REVIEW_BUTTON_SELECTORS = EasyApplySelectors.REVIEW_BUTTONS
    SUBMIT_BUTTON_SELECTORS = EasyApplySelectors.SUBMIT_BUTTONS
    DISMISS_BUTTON_SELECTORS = EasyApplySelectors.DISMISS_BUTTONS
    DISCARD_CONFIRM_SELECTORS = EasyApplySelectors.DISCARD_CONFIRM_BUTTONS

    def __init__(
        self,
        solver: Optional[LinkedInScreeningSolver] = None,
        page: Optional[Any] = None,
        circuit_breaker: Optional[LinkedInCircuitBreaker] = None
    ):
        super().__init__(page=page, circuit_breaker=circuit_breaker)
        if solver:
            self.solver = solver

    async def _verify_submission_confirmation(self, page: Any) -> bool:
        """Internal legacy verification helper."""
        return await self.verify_and_dismiss_submission(page)
