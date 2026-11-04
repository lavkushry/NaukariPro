"""Attention queue for 14 blocker classes — never silent-solve captcha."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class BlockerClass(str, Enum):
    AUTH = "auth"
    MFA = "mfa"
    CAPTCHA = "captcha"
    LEGAL_ATTESTATION = "legal_attestation"
    DEMOGRAPHIC = "demographic"
    GOVERNMENT_ID = "government_id"
    PAYMENT = "payment"
    JUDGMENT = "judgment"
    UPLOAD_MISSING = "upload_missing"
    ACCOUNT_CREATE = "account_create"
    GEO_BLOCK = "geo_block"
    RATE_LIMIT = "rate_limit"
    BROKEN_FORM = "broken_form"
    UNKNOWN = "unknown"


@dataclass
class AttentionItem:
    blocker: BlockerClass
    job_url: str
    detail: str
    status: str = "open"  # open | resolved | blocked


@dataclass
class AttentionQueue:
    items: List[AttentionItem] = field(default_factory=list)

    def push(self, blocker: BlockerClass, job_url: str, detail: str) -> AttentionItem:
        item = AttentionItem(blocker=blocker, job_url=job_url, detail=detail)
        self.items.append(item)
        return item

    def open_items(self) -> List[AttentionItem]:
        return [i for i in self.items if i.status == "open"]


def detect_blocker(page_text: str, *, url: str = "") -> Optional[BlockerClass]:
    t = (page_text or "").lower()
    if any(k in t for k in ("captcha", "recaptcha", "hcaptcha", "cf-challenge")):
        return BlockerClass.CAPTCHA
    if any(k in t for k in ("two-factor", "2fa", "mfa", "authenticator", "verification code")):
        return BlockerClass.MFA
    if any(k in t for k in ("sign in", "log in", "login", "authenticate")):
        return BlockerClass.AUTH
    if any(k in t for k in ("government id", "passport", "driver license", "aadhaar")):
        return BlockerClass.GOVERNMENT_ID
    if any(k in t for k in ("credit card", "payment required", "pay to apply")):
        return BlockerClass.PAYMENT
    if any(k in t for k in ("equal opportunity", "eeo", "race", "gender identity", "disability")):
        return BlockerClass.DEMOGRAPHIC
    if any(k in t for k in ("i attest", "i certify", "under penalty")):
        return BlockerClass.LEGAL_ATTESTATION
    if any(k in t for k in ("create an account", "sign up to apply")):
        return BlockerClass.ACCOUNT_CREATE
    if any(k in t for k in ("too many requests", "rate limit", "try again later")):
        return BlockerClass.RATE_LIMIT
    if any(k in t for k in ("not available in your region", "geo")):
        return BlockerClass.GEO_BLOCK
    return None
