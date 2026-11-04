"""Question sensitivity classes — LEGAL/SENSITIVE stay browser-only and masked in logs."""

from __future__ import annotations

import re
from enum import Enum
from typing import Optional


class Sensitivity(str, Enum):
    NEVER = "NEVER"
    LEGAL = "LEGAL"
    SENSITIVE = "SENSITIVE"
    CONTACT = "CONTACT"
    JOB_SPECIFIC = "JOB_SPECIFIC"


_NEVER = re.compile(
    r"\b(password|otp|one[-\s]?time|2fa|mfa|verification code|ssn|social security|"
    r"credit\s*card|cvv|card\s*number)\b",
    re.I,
)
_LEGAL = re.compile(
    r"\b(authorized to work|right to work|visa|citizenship|gender|race|ethnicity|"
    r"disability|veteran|lgbt|sexual orientation|religion|hispanic|demographic|"
    r"eeo|equal opportunity|sponsorship|require sponsorship)\b",
    re.I,
)
_SENSITIVE = re.compile(
    r"\b(salary|ctc|compensation|current pay|expected pay|date of birth|dob|"
    r"government\s*id|passport|aadhaar|pan\b|national id|background check)\b",
    re.I,
)
_CONTACT = re.compile(
    r"\b(email|phone|mobile|linkedin|github|address|city|state|zip|postal)\b",
    re.I,
)


def classify_question(label: str) -> Sensitivity:
    text = label or ""
    if _NEVER.search(text):
        return Sensitivity.NEVER
    if _LEGAL.search(text):
        return Sensitivity.LEGAL
    if _SENSITIVE.search(text):
        return Sensitivity.SENSITIVE
    if _CONTACT.search(text):
        return Sensitivity.CONTACT
    return Sensitivity.JOB_SPECIFIC


def mask_for_log(value: Optional[str], sensitivity: Sensitivity) -> str:
    if value is None:
        return ""
    if sensitivity in (Sensitivity.NEVER, Sensitivity.LEGAL, Sensitivity.SENSITIVE):
        if len(value) <= 2:
            return "***"
        return value[0] + "***" + value[-1]
    return value
