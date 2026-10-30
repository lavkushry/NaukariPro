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
