"""
Captcha safety chain (MP §4.9) — human-default, fail-closed.

Back-compat surface used by Family F scenarios and governed_apply.
"""

from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import List, Optional, Sequence
from urllib.parse import urlparse

from naukari_pro.captcha.circuit import CIRCUIT_UNRESOLVED_THRESHOLD, circuit_open
from naukari_pro.captcha.detector import detect_captcha
from naukari_pro.captcha.events import CaptchaEventsStore
from naukari_pro.captcha.vendor import build_vendor_client

EXIT_CAPTCHA_BLOCKED = 3


class Resolution(str, Enum):
    NEEDS_HUMAN = "needs_human"
    VENDOR_OK = "vendor_ok"
    VENDOR_DENIED = "vendor_denied"
    CIRCUIT_OPEN = "circuit_open"
    APPLIED_INVALID = "applied_invalid"


@dataclass
class CaptchaResult:
    resolution: Resolution
    resolved_by: str
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
        # Domain is already lstrip(".")'d; match against pattern with optional
        # leading-dot stripped so "*.ashbyhq.com" / ".ashbyhq.com" both work.
        if fnmatch.fnmatch(d, p.lstrip(".")):
            return True
    return False


def extract_domain(page_url: str) -> str:
    try:
        return (urlparse(page_url).netloc or "").lower()
    except Exception:
        return ""


def detect_captcha_type(page_html: str) -> Optional[str]:
    det = detect_captcha(page_html)
    return det.type if det else None


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
        # Empty allowlist = deny everywhere for vendor; tests often pass ["*"]
        self.domains: List[str] = list(domains) if domains is not None else []
        self.spend_24h = float(spend_24h)
        self.cap = float(cap)
        self.board = board
        self.db_path = Path(db_path) if db_path else None
        self._store = CaptchaEventsStore(self.db_path) if self.db_path else None
        # Physically omit vendor in human mode — never construct/store a callable
        if self.mode == "human" or "vendor" not in {m.strip() for m in self.mode.split(",")}:
            self._vendor = None
            self._vendor_client = None
        else:
            self._vendor = vendor_callable
            self._vendor_client = build_vendor_client(mode=self.mode, api_key=self.api_key)

    def handle(self, *, captcha_type: str, page_url: str) -> CaptchaResult:
        domain = extract_domain(page_url)

        if circuit_open(self.db_path, self.board):
            self._ledger(resolved_by="none", spend=0.0, unresolved=1, captcha_type=captcha_type, page_url=page_url, resolution="circuit_open")
            return CaptchaResult(
                resolution=Resolution.CIRCUIT_OPEN,
                resolved_by="none",
                exit_code=EXIT_CAPTCHA_BLOCKED,
                detail=f"circuit_open board={self.board}",
                vendor_attempted=False,
            )

        if self.mode == "human" or self._vendor is None:
            self._ledger(resolved_by="human", spend=0.0, unresolved=1, captcha_type=captcha_type, page_url=page_url, resolution="needs_human")
            return CaptchaResult(
                resolution=Resolution.NEEDS_HUMAN,
                resolved_by="human",
                exit_code=EXIT_CAPTCHA_BLOCKED,
                detail="human_mode_or_no_vendor",
                vendor_attempted=False,
            )

        if not self.api_key:
            self._ledger(resolved_by="human", spend=0.0, unresolved=1, captcha_type=captcha_type, page_url=page_url, resolution="vendor_denied")
            return CaptchaResult(
                resolution=Resolution.VENDOR_DENIED,
                resolved_by="human",
                exit_code=EXIT_CAPTCHA_BLOCKED,
                detail="missing_api_key",
                vendor_attempted=False,
            )

        if not domain_allowed(domain, self.domains):
            self._ledger(resolved_by="human", spend=0.0, unresolved=1, captcha_type=captcha_type, page_url=page_url, resolution="vendor_denied")
            return CaptchaResult(
                resolution=Resolution.VENDOR_DENIED,
                resolved_by="human",
                exit_code=EXIT_CAPTCHA_BLOCKED,
                detail=f"domain_denied:{domain}",
                vendor_attempted=False,
            )

        if self.spend_24h >= self.cap:
            self._ledger(resolved_by="human", spend=0.0, unresolved=1, captcha_type=captcha_type, page_url=page_url, resolution="vendor_denied")
            return CaptchaResult(
                resolution=Resolution.VENDOR_DENIED,
                resolved_by="human",
                exit_code=EXIT_CAPTCHA_BLOCKED,
                detail="spend_cap",
                vendor_attempted=False,
            )

        try:
            ok = bool(self._vendor(captcha_type=captcha_type, page_url=page_url))
        except Exception as exc:  # noqa: BLE001
            self._ledger(resolved_by="human", spend=0.0, unresolved=1, captcha_type=captcha_type, page_url=page_url, resolution="needs_human")
            return CaptchaResult(
                resolution=Resolution.NEEDS_HUMAN,
                resolved_by="human",
                exit_code=EXIT_CAPTCHA_BLOCKED,
                detail=f"vendor_error:{type(exc).__name__}",
                vendor_attempted=True,
            )

        if ok:
            self._ledger(resolved_by="vendor", spend=0.1, unresolved=0, captcha_type=captcha_type, page_url=page_url, resolution="vendor_ok")
            return CaptchaResult(
                resolution=Resolution.VENDOR_OK,
                resolved_by="vendor",
                exit_code=0,
                detail="vendor_ok",
                vendor_attempted=True,
            )

        self._ledger(resolved_by="human", spend=0.0, unresolved=1, captcha_type=captcha_type, page_url=page_url, resolution="needs_human")
        return CaptchaResult(
            resolution=Resolution.NEEDS_HUMAN,
            resolved_by="human",
            exit_code=EXIT_CAPTCHA_BLOCKED,
            detail="vendor_failed",
            vendor_attempted=True,
        )

    def _ledger(
        self,
        *,
        resolved_by: str,
        spend: float,
        unresolved: int,
        captcha_type: str,
        page_url: str,
        resolution: str,
    ) -> None:
        if not self._store:
            return
        self._store.record(
            board=self.board,
            captcha_type=captcha_type,
            resolved_by=resolved_by,
            resolution=resolution,
            page_url=page_url,
            cost_usd=spend,
            detail=resolution,
            unresolved=bool(unresolved),
        )
