"""
Captcha safety chain (MP §4.9) — human-default, fail-closed.

Minimal surface required by Family F scenarios:
- CAPTCHA_MODE=human never constructs a vendor HTTP caller
- vendor mode requires key + allowlisted domain + under spend cap
- circuit breaker: ≥5 unresolved / 24h per board → back off, exit 3
- never silently marks captcha as solved/applied
"""

from __future__ import annotations

import fnmatch
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import List, Optional, Sequence
from urllib.parse import urlparse


class Resolution(str, Enum):
    NEEDS_HUMAN = "needs_human"
    VENDOR_OK = "vendor_ok"
    VENDOR_DENIED = "vendor_denied"
    CIRCUIT_OPEN = "circuit_open"
    APPLIED_INVALID = "applied_invalid"  # forbidden outcome


EXIT_CAPTCHA_BLOCKED = 3
CIRCUIT_UNRESOLVED_THRESHOLD = 5
CIRCUIT_WINDOW_HOURS = 24


@dataclass
class CaptchaResult:
    resolution: Resolution
    resolved_by: str  # "human" | "vendor" | "none"
    exit_code: int
    detail: str
    vendor_attempted: bool = False


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def domain_allowed(domain: str, allowlist: Sequence[str]) -> bool:
    if not allowlist:
        return False
    d = (domain or "").lower().lstrip(".")
    for pattern in allowlist:
        p = (pattern or "").lower().strip()
        if not p:
            continue
        if p == "*":
            return True
        if fnmatch.fnmatch(d, p.lstrip(".")):
            return True
        if fnmatch.fnmatch(d, p):
            return True
    return False


def extract_domain(page_url: str) -> str:
    try:
        return (urlparse(page_url).netloc or "").lower()
    except Exception:
        return ""


class CaptchaSafetyManager:
    """Policy gate in front of any captcha vendor resolver."""

    def __init__(
        self,
        *,
        mode: Optional[str] = None,
        api_key: Optional[str] = None,
        domains: Optional[Sequence[str]] = None,
        spend_24h: float = 0.0,
        cap: float = 5.0,
        db_path: Optional[Path] = None,
        board: str = "unknown",
        vendor_callable=None,
    ) -> None:
        self.mode = (mode or os.environ.get("CAPTCHA_MODE") or "human").lower()
        self.api_key = api_key if api_key is not None else os.environ.get("CAPTCHA_VENDOR_API_KEY")
        self.domains: List[str] = list(domains) if domains is not None else ["*"]
        self.spend_24h = float(spend_24h)
        self.cap = float(cap)
        self.board = board
        self.db_path = Path(db_path) if db_path else None
        # Physically omit vendor in human mode — never construct/store a callable
        if self.mode == "human":
            self._vendor = None
        else:
            self._vendor = vendor_callable

    def _unresolved_count_24h(self) -> int:
        if not self.db_path or not self.db_path.exists():
            return 0
        cutoff = (_utc_now() - timedelta(hours=CIRCUIT_WINDOW_HOURS)).isoformat()
        with sqlite3.connect(str(self.db_path)) as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) FROM captcha_ledger
                WHERE board = ? AND unresolved = 1 AND created_at >= ?
                """,
                (self.board, cutoff),
            ).fetchone()
        return int(row[0] if row else 0)

    def _ledger(self, *, resolved_by: str, spend: float, unresolved: int) -> None:
        if not self.db_path:
            return
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS captcha_ledger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    board TEXT NOT NULL,
                    resolved_by TEXT,
                    spend_usd REAL NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    unresolved INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                """
                INSERT INTO captcha_ledger (board, resolved_by, spend_usd, created_at, unresolved)
                VALUES (?, ?, ?, ?, ?)
                """,
                (self.board, resolved_by, spend, _utc_now().isoformat(), unresolved),
            )
            conn.commit()

    def handle(self, *, captcha_type: str, page_url: str) -> CaptchaResult:
        domain = extract_domain(page_url)

        if self._unresolved_count_24h() >= CIRCUIT_UNRESOLVED_THRESHOLD:
            self._ledger(resolved_by="none", spend=0.0, unresolved=1)
            return CaptchaResult(
                resolution=Resolution.CIRCUIT_OPEN,
                resolved_by="none",
                exit_code=EXIT_CAPTCHA_BLOCKED,
                detail=f"circuit_open board={self.board}",
                vendor_attempted=False,
            )

        if self.mode == "human" or self._vendor is None:
            self._ledger(resolved_by="human", spend=0.0, unresolved=1)
            return CaptchaResult(
                resolution=Resolution.NEEDS_HUMAN,
                resolved_by="human",
                exit_code=EXIT_CAPTCHA_BLOCKED,
                detail="human_mode_or_no_vendor",
                vendor_attempted=False,
            )

        if not self.api_key:
            self._ledger(resolved_by="human", spend=0.0, unresolved=1)
            return CaptchaResult(
                resolution=Resolution.VENDOR_DENIED,
                resolved_by="human",
                exit_code=EXIT_CAPTCHA_BLOCKED,
                detail="missing_api_key",
                vendor_attempted=False,
            )

        if not domain_allowed(domain, self.domains):
            self._ledger(resolved_by="human", spend=0.0, unresolved=1)
            return CaptchaResult(
                resolution=Resolution.VENDOR_DENIED,
                resolved_by="human",
                exit_code=EXIT_CAPTCHA_BLOCKED,
                detail=f"domain_denied:{domain}",
                vendor_attempted=False,
            )

        if self.spend_24h >= self.cap:
            self._ledger(resolved_by="human", spend=0.0, unresolved=1)
            return CaptchaResult(
                resolution=Resolution.VENDOR_DENIED,
                resolved_by="human",
                exit_code=EXIT_CAPTCHA_BLOCKED,
                detail="spend_cap",
                vendor_attempted=False,
            )

        # Vendor path — callable may raise; never claim APPLIED_INVALID success
        try:
            ok = bool(self._vendor(captcha_type=captcha_type, page_url=page_url))
        except Exception as exc:  # noqa: BLE001 — fail closed to human
            self._ledger(resolved_by="human", spend=0.0, unresolved=1)
            return CaptchaResult(
                resolution=Resolution.NEEDS_HUMAN,
                resolved_by="human",
                exit_code=EXIT_CAPTCHA_BLOCKED,
                detail=f"vendor_error:{type(exc).__name__}",
                vendor_attempted=True,
            )

        if ok:
            self._ledger(resolved_by="vendor", spend=0.1, unresolved=0)
            return CaptchaResult(
                resolution=Resolution.VENDOR_OK,
                resolved_by="vendor",
                exit_code=0,
                detail="vendor_ok",
                vendor_attempted=True,
            )

        self._ledger(resolved_by="human", spend=0.0, unresolved=1)
        return CaptchaResult(
            resolution=Resolution.NEEDS_HUMAN,
            resolved_by="human",
            exit_code=EXIT_CAPTCHA_BLOCKED,
            detail="vendor_failed",
            vendor_attempted=True,
        )


def detect_captcha_type(page_html: str) -> Optional[str]:
    """Classify captcha widget from captured HTML (offline fixtures)."""
    t = (page_html or "").lower()
    checks = [
        ("recaptcha_v2", ("g-recaptcha", "recaptcha/api.js", "data-sitekey")),
        ("recaptcha_v3", ("recaptcha/enterprise", "grecaptcha.execute")),
        ("hcaptcha", ("h-captcha", "hcaptcha.com")),
        ("turnstile", ("cf-turnstile", "challenges.cloudflare.com")),
        ("funcaptcha", ("arkose", "funcaptcha")),
        ("geetest", ("geetest", "gt_captcha")),
        ("image_captcha", ("captcha-image", "input#captcha")),
        ("text_captcha", ("type the characters", "enter the code shown")),
    ]
    for name, needles in checks:
        if any(n in t for n in needles):
            return name
    if "captcha" in t:
        return "unknown_captcha"
    return None
