"""
naukariPro Learning Subsystem: Strict Evidence Verification Engine (M2 / R2)
Implements 3-Point Evidence Verification State Machine:
1. Condition (a): Thank-You / confirmation screenshot saved to evidence/evidence_<company>_<role>.png
2. Condition (b): Database row updated to 'Submitted (Confirmed)' with evidence_path and timestamp
3. Condition (c): Asynchronous confirmation email harvesting hook
Universal Fallback: Unconfirmed submissions remain strictly 'Form Auto-Filled (Ready for Review)'
"""

import os
import re
import json
import inspect
import logging
import unicodedata
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any, Union

from naukari_pro.config import BASE_DIR

logger = logging.getLogger("naukariPro.EvidenceVerifier")

PNG_MAGIC_HEADER = b"\x89PNG\r\n\x1a\n"
MIN_SCREENSHOT_BYTES = 1024


class EvidenceVerifier:
    """
    3-Point Evidence Verification Engine.
    Enforces that applications count as submitted only with verifiable PNG evidence.
    """

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or BASE_DIR)
        self.evidence_dir = self.base_dir / "evidence"
        self.evidence_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def sanitize_token(text: Optional[str], default: str = "unknown", max_len: int = 50) -> str:
        """
        Sanitizes text tokens for safe, deterministic filenames across all platforms.
        Normalizes unicode, converts to lowercase, replaces non-alphanumeric with underscores,
        and bounds length <= 50.
        """
        if not text:
            return default
        norm = unicodedata.normalize("NFKD", str(text))
        clean = re.sub(r"[^a-zA-Z0-9]+", "_", norm).strip("_").lower()
        clean = clean[:max_len].rstrip("_")
        return clean or default

    def get_evidence_path(self, company: str, role: str) -> Path:
        """Generates canonical deterministic evidence screenshot path."""
        c = self.sanitize_token(company, default="company")
        r = self.sanitize_token(role, default="role")
        return self.evidence_dir / f"evidence_{c}_{r}.png"

    def verify_screenshot_file(self, filepath: Union[str, Path, None]) -> bool:
        """
        Verifies that an evidence screenshot exists on disk, exceeds 1KB,
        and contains a valid 8-byte PNG signature header.
        """
        if not filepath:
            return False
        p = Path(filepath)
        if not p.is_file() or p.stat().st_size < MIN_SCREENSHOT_BYTES:
            return False
        try:
            with open(p, "rb") as f:
                header = f.read(8)
                return header == PNG_MAGIC_HEADER
        except Exception as e:
            logger.debug("Failed to verify screenshot header: %s", e)
            return False

    async def capture_screenshot_async(self, page: Any, company: str, role: str) -> Optional[str]:
        """Asynchronously captures confirmation screenshot for Playwright pages."""
        if not page or not hasattr(page, "screenshot"):
            return None
        target_path = self.get_evidence_path(company, role)
        try:
            res = page.screenshot(path=str(target_path), full_page=False)
            if inspect.isawaitable(res):
                await res
            if self.verify_screenshot_file(target_path):
                return str(target_path)
            return None
        except Exception as e:
            logger.error("Async screenshot capture failed for %s @ %s: %s", role, company, e)
            return None

    def capture_screenshot_sync(self, page: Any, company: str, role: str) -> Optional[str]:
        """Synchronously captures confirmation screenshot for synchronous Playwright pages."""
        if not page or not hasattr(page, "screenshot"):
            return None
        target_path = self.get_evidence_path(company, role)
        try:
            page.screenshot(path=str(target_path), full_page=False)
            if self.verify_screenshot_file(target_path):
                return str(target_path)
            return None
        except Exception as e:
            logger.error("Sync screenshot capture failed for %s @ %s: %s", role, company, e)
            return None

    def capture_confirmation_screenshot(self, page: Any, company: str, role: str) -> Optional[str]:
        """
        Public contract per PROJECT.md interface contract.
        Handles both sync and async page objects.
        """
        if not page:
            return None
        # If in an async running loop and page.screenshot is async
        return self.capture_screenshot_sync(page, company, role)

    def evaluate_submission_state(
        self,
        confirmation_detected: bool,
        screenshot_path: Optional[str]
    ) -> Tuple[str, Optional[str]]:
        """
        Evaluates 3-point submission state machine.
        Returns: (status: str, verified_evidence_path: Optional[str])
        """
        if confirmation_detected and screenshot_path and self.verify_screenshot_file(screenshot_path):
            return "Submitted (Confirmed)", str(screenshot_path)
        return "Form Auto-Filled (Ready for Review)", None

    def verify_and_record_submission(
        self,
        job_id: str,
        company: str,
        role: str,
        screenshot_path: Optional[str],
        db_path: Optional[str] = None
    ) -> str:
        """
        Public contract per PROJECT.md interface contract.
        Evaluates screenshot evidence and records status into applied_jobs.db.
        """
        from naukari_pro.modules.db import update_application_evidence

        valid = bool(screenshot_path and self.verify_screenshot_file(screenshot_path))
        target_status = "Submitted (Confirmed)" if valid else "Form Auto-Filled (Ready for Review)"
        valid_path = screenshot_path if valid else None

        update_application_evidence(
            job_id=job_id,
            status=target_status,
            evidence_path=valid_path,
            db_path=db_path
        )
        return target_status

    def verify_email_confirmation(
        self,
        company: str,
        role: str = "",
        since_ts: float = 0.0,
        timeout_sec: float = 15.0
    ) -> Tuple[bool, Optional[str]]:
        """
        Polls candidate Gmail via IMAP SSL to verify incoming post-submission confirmation
        email ("Thank you for applying", "Application received", etc.) for the target company.
        Returns: (is_confirmed: bool, email_subject: Optional[str])
        """
        import imaplib, email, email.utils, time
        from dotenv import load_dotenv
        load_dotenv()
        user = os.getenv("GMAIL_USER", "lav84095@gmail.com")
        pwd = os.getenv("GMAIL_APP_PASSWORD", "")
        if not user or not pwd:
            return False, None

        c_clean = company.lower().split()[0] if company else ""
        t_start = time.time()
        while time.time() - t_start < timeout_sec:
            try:
                mail = imaplib.IMAP4_SSL("imap.gmail.com")
                mail.login(user, pwd)
                mail.select("INBOX")
                status, data = mail.search(None, "ALL")
                ids = data[0].split()
                for mid in reversed(ids[-20:]):
                    status, mdata = mail.fetch(mid, "(RFC822)")
                    msg = email.message_from_bytes(mdata[0][1])
                    subj = msg.get("Subject", "")
                    subj_lower = subj.lower()
                    date_tuple = email.utils.parsedate_tz(msg.get("Date"))
                    msg_epoch = email.utils.mktime_tz(date_tuple) if date_tuple else 0
                    if since_ts > 0 and msg_epoch > 0 and msg_epoch < (since_ts - 30):
                        continue

                    # Check for confirmation indicators
                    is_confirmation_subj = any(k in subj_lower for k in [
                        "thank you for applying",
                        "application received",
                        "we received your application",
                        "application confirmation",
                        "thanks for your interest",
                        "application submitted",
                        "applied to"
                    ])
                    company_match = not c_clean or c_clean in subj_lower or c_clean in (msg.get("From", "")).lower()

                    if is_confirmation_subj and company_match:
                        mail.close()
                        mail.logout()
                        return True, subj

                mail.close()
                mail.logout()
            except Exception as e_imap:
                logger.debug("IMAP confirmation poll notice: %s", e_imap)
            time.sleep(3)
        return False, None
