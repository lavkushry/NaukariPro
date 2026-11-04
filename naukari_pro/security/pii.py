"""PII / secret redaction for log sinks (MP §6)."""

from __future__ import annotations

import re
from typing import List

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(
    r"(?:\+91[\s-]?)?[6-9]\d{9}\b|\+\d{1,3}[\s-]?\d{6,14}\b"
)
# PAN-like: 5 letters + 4 digits + 1 letter
PAN_RE = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b", re.I)
# Aadhaar-like: 12 digits, optionally spaced
AADHAAR_RE = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
API_KEY_RE = re.compile(
    r"\b(sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|xai-[A-Za-z0-9]{16,})\b"
)
BEARER_RE = re.compile(r"(?i)(authorization:\s*bearer\s+)\S+")


def redact_pii(text: str) -> str:
    if not text:
        return text
    out = EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    out = PHONE_RE.sub("[REDACTED_PHONE]", out)
    out = PAN_RE.sub("[REDACTED_PAN]", out)
    out = AADHAAR_RE.sub("[REDACTED_AADHAAR]", out)
    out = API_KEY_RE.sub("[REDACTED_SECRET]", out)
    out = BEARER_RE.sub(r"\1[REDACTED_TOKEN]", out)
    return out


def secrets_in_text(text: str) -> List[str]:
    """Return matched secret-like substrings (for hygiene asserts)."""
    found: List[str] = []
    for cre in (API_KEY_RE, BEARER_RE):
        found.extend(m.group(0) for m in cre.finditer(text or ""))
    return found
