"""filled != applied — require visible ATS confirmation text or URL pattern."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


CONFIRM_TEXT_PATTERNS = [
    r"application (?:has been )?submitted",
    r"thanks for applying",
    r"thank you for (?:your )?application",
    r"we(?:'| ha)?ve received your application",
    r"application received",
    r"successfully applied",
    r"your application is complete",
]

CONFIRM_URL_PATTERNS = [
    r"/confirmation",
    r"/thanks",
    r"/application[_-]?submitted",
    r"[?&]success=1",
    r"/applied",
]

_TEXT_RE = re.compile("|".join(f"(?:{p})" for p in CONFIRM_TEXT_PATTERNS), re.I)
_URL_RE = re.compile("|".join(f"(?:{p})" for p in CONFIRM_URL_PATTERNS), re.I)
# Negation / error context near a success substring → fail closed (Phase-5 F1).
_NEGATION_RE = re.compile(
    r"\b("
    r"error|failed|failure|unable|unsuccessful|not\s+submitted|could\s+not|"
    r"cannot|can't|denied|rejected|invalid|please\s+fix"
    r")\b",
    re.I,
)


@dataclass
class ConfirmationResult:
    confirmed: bool
    matched_text: Optional[str] = None
    matched_url: Optional[str] = None


def detect_submission_confirmation(
    *,
    page_text: str = "",
    page_url: str = "",
) -> ConfirmationResult:
    text = page_text or ""
    text_m = _TEXT_RE.search(text)
    url_m = _URL_RE.search(page_url or "")
    # Any error/negation on the page voids both text and URL confirmation (Phase-5 F6).
    if _NEGATION_RE.search(text):
        return ConfirmationResult(
            confirmed=False,
            matched_text=text_m.group(0) if text_m else None,
            matched_url=page_url if url_m else None,
        )
    if text_m or url_m:
        return ConfirmationResult(
            confirmed=True,
            matched_text=text_m.group(0) if text_m else None,
            matched_url=page_url if url_m else None,
        )
    return ConfirmationResult(confirmed=False)
