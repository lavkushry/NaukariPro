"""CaptchaResolver chain: passthrough → vendor → vlm → human (always last)."""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Protocol, Sequence

from naukari_pro.captcha.circuit import circuit_open
from naukari_pro.captcha.detector import CaptchaDetection, detect_captcha
from naukari_pro.captcha.events import CaptchaEventsStore
from naukari_pro.captcha.vendor import VendorClient, build_vendor_client
from naukari_pro.captcha.vlm import try_solve_text_math

EXIT_CAPTCHA_BLOCKED = 3


@dataclass
class CaptchaResolveResult:
    resolved: bool
    resolved_by: str  # passthrough | vendor | vlm | human | none
    exit_code: int
    detail: str
    detection: Optional[CaptchaDetection] = None
    token: Optional[str] = None


class CaptchaResolver(Protocol):
    name: str

    def can_handle(self, detection: CaptchaDetection, *, mode: str) -> bool: ...

    def resolve(self, detection: CaptchaDetection) -> Optional[str]:
        """Return token/answer or None to fall through."""
        ...


_EXISTING_TOKEN_RE = re.compile(
    r'name=["\'](?:g-recaptcha-response|h-captcha-response|cf-turnstile-response)["\']'
    r'[^>]*value=["\']([^"\']+)["\']|'
    r'value=["\']([^"\']+)["\'][^>]*'
    r'name=["\'](?:g-recaptcha-response|h-captcha-response|cf-turnstile-response)["\']',
    re.I,
)


def _extract_existing_token(html: str) -> Optional[str]:
    m = _EXISTING_TOKEN_RE.search(html or "")
    if not m:
        return None
    tok = m.group(1) or m.group(2) or ""
    tok = tok.strip()
    return tok or None


class PassthroughResolver:
    name = "passthrough"

    def can_handle(self, detection: CaptchaDetection, *, mode: str) -> bool:
        return detection.type.endswith("_invisible") or (
            not detection.interactive and detection.type in ("turnstile", "recaptcha_v2_invisible")
        )

    def resolve(self, detection: CaptchaDetection) -> Optional[str]:
        # Only pass through when a non-empty token is already present on the page.
        # Empty marker HTML must fall through to human (Phase-5 F4).
        detail = getattr(detection, "raw_html", None) or ""
        token = _extract_existing_token(detail)
        return token


class VendorResolver:
    name = "vendor"

    def __init__(self, client: Optional[VendorClient] = None) -> None:
        self.client = client

    def can_handle(self, detection: CaptchaDetection, *, mode: str) -> bool:
        modes = {m.strip() for m in mode.split(",") if m.strip()}
        return "vendor" in modes and detection.vendor_mappable and self.client is not None

    def resolve(self, detection: CaptchaDetection) -> Optional[str]:
        if self.client is None:
            return None
        try:
            tid = self.client.create_task(
                captcha_type=detection.type,
                page_url=detection.page_url,
                sitekey=detection.sitekey or "",
            )
            return self.client.get_result(tid)
        except Exception:  # noqa: BLE001
            return None


class VlmResolver:
    name = "vlm"

    def can_handle(self, detection: CaptchaDetection, *, mode: str) -> bool:
        modes = {m.strip() for m in mode.split(",") if m.strip()}
        return "vlm" in modes and detection.type in ("text_math", "text_captcha", "image_captcha")

    def resolve(self, detection: CaptchaDetection) -> Optional[str]:
        # Only deterministic math in offline path
        return try_solve_text_math(detection.page_url or detection.type)


class HumanResolver:
    name = "human"

    def can_handle(self, detection: CaptchaDetection, *, mode: str) -> bool:
        return True  # always last, always can handle

    def resolve(self, detection: CaptchaDetection) -> Optional[str]:
        return None  # signals NEEDS HUMAN


class CaptchaResolverChain:
    def __init__(
        self,
        *,
        mode: Optional[str] = None,
        store: Optional[CaptchaEventsStore] = None,
        board: str = "unknown",
        company: str = "",
        domain_allowlist: Optional[Sequence[str]] = None,
        spend_24h: float = 0.0,
        spend_cap: float = 5.0,
        vendor_client: Optional[VendorClient] = None,
        resolvers: Optional[List[CaptchaResolver]] = None,
    ) -> None:
        self.mode = (mode or os.environ.get("CAPTCHA_MODE") or "human").lower()
        self.store = store
        self.board = board
        self.company = company
        self.domain_allowlist = list(domain_allowlist) if domain_allowlist is not None else []
        self.spend_24h = spend_24h
        self.spend_cap = spend_cap
        # Human mode: never construct vendor client
        if vendor_client is not None and "vendor" in {m.strip() for m in self.mode.split(",")}:
            client = vendor_client
        else:
            client = build_vendor_client(mode=self.mode)
        self._vendor_client = client
        self.resolvers: List[CaptchaResolver] = resolvers or [
            PassthroughResolver(),
            VendorResolver(client),
            VlmResolver(),
            HumanResolver(),
        ]

    def resolve_html(self, page_html: str, *, page_url: str = "") -> CaptchaResolveResult:
        t0 = time.time()
        detection = detect_captcha(page_html, page_url=page_url)
        if detection is None:
            return CaptchaResolveResult(
                resolved=True,
                resolved_by="none",
                exit_code=0,
                detail="no_captcha",
            )

        db = self.store.db_path if self.store else None
        if circuit_open(db, self.board):
            self._log(detection, "none", "circuit_open", time.time() - t0, unresolved=True)
            return CaptchaResolveResult(
                resolved=False,
                resolved_by="none",
                exit_code=EXIT_CAPTCHA_BLOCKED,
                detail="circuit_open",
                detection=detection,
            )

        for resolver in self.resolvers:
            try:
                if not resolver.can_handle(detection, mode=self.mode):
                    continue
                if resolver.name == "vendor":
                    if not self._vendor_allowed(page_url):
                        continue
                token = resolver.resolve(detection)
            except Exception as exc:  # noqa: BLE001 — broken resolver must not kill filler
                self._log(
                    detection,
                    "none",
                    f"resolver_error:{resolver.name}:{type(exc).__name__}",
                    time.time() - t0,
                    unresolved=True,
                )
                continue
            if token:
                by = resolver.name
                unresolved = by == "human"
                self._log(detection, by, "ok", time.time() - t0, unresolved=unresolved, cost=0.1 if by == "vendor" else 0.0)
                return CaptchaResolveResult(
                    resolved=by != "human",
                    resolved_by=by,
                    exit_code=0 if by != "human" else EXIT_CAPTCHA_BLOCKED,
                    detail=f"{by}_ok" if by != "human" else "needs_human",
                    detection=detection,
                    token=token if by != "human" else None,
                )
            if resolver.name == "human":
                self._log(detection, "human", "needs_human", time.time() - t0, unresolved=True)
                return CaptchaResolveResult(
                    resolved=False,
                    resolved_by="human",
                    exit_code=EXIT_CAPTCHA_BLOCKED,
                    detail="needs_human",
                    detection=detection,
                )

        self._log(detection, "human", "needs_human", time.time() - t0, unresolved=True)
        return CaptchaResolveResult(
            resolved=False,
            resolved_by="human",
            exit_code=EXIT_CAPTCHA_BLOCKED,
            detail="needs_human",
            detection=detection,
        )

    def _vendor_allowed(self, page_url: str) -> bool:
        from naukari_pro.captcha.safety import domain_allowed, extract_domain

        if self._vendor_client is None:
            return False
        if not self.domain_allowlist:
            return False  # empty allowlist = deny everywhere
        if self.spend_24h >= self.spend_cap:
            return False
        return domain_allowed(extract_domain(page_url), self.domain_allowlist)

    def _log(
        self,
        detection: CaptchaDetection,
        resolved_by: str,
        resolution: str,
        duration_s: float,
        *,
        unresolved: bool,
        cost: float = 0.0,
    ) -> None:
        if not self.store:
            return
        try:
            self.store.record(
                board=self.board,
                company=self.company,
                page_url=detection.page_url,
                captcha_type=detection.type,
                resolved_by=resolved_by,
                resolution=resolution if resolution != "ok" else (
                    "vendor_ok" if resolved_by == "vendor" else "passthrough"
                ),
                duration_s=duration_s,
                cost_usd=cost,
                detail=resolution,
                unresolved=unresolved,
            )
        except Exception:  # noqa: BLE001
            pass
