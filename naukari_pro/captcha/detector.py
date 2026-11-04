"""Tier 2 — detect & classify captcha widgets (never interacts)."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


@dataclass
class CaptchaDetection:
    type: str
    sitekey: Optional[str]
    page_url: str
    frame: Optional[str]
    interactive: bool
    behavioral: bool
    vendor_mappable: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


_SITEKEY_RE = re.compile(
    r'data-sitekey=["\']([^"\']+)["\']|sitekey["\']?\s*[:=]\s*["\']([^"\']+)["\']',
    re.I,
)


def _sitekey(html: str) -> Optional[str]:
    m = _SITEKEY_RE.search(html or "")
    if not m:
        return None
    return m.group(1) or m.group(2)


def detect_captcha(page_html: str, *, page_url: str = "") -> Optional[CaptchaDetection]:
    """Classify captcha from HTML. Detection only — never solves."""
    t = (page_html or "").lower()
    html = page_html or ""

    # Invisible token already present → Tier 1 passthrough candidate
    if any(
        x in t
        for x in (
            'name="g-recaptcha-response"',
            'name="h-captcha-response"',
            'name="cf-turnstile-response"',
        )
    ) and "data-size=\"invisible\"" in t:
        return CaptchaDetection(
            type="recaptcha_v2_invisible",
            sitekey=_sitekey(html),
            page_url=page_url,
            frame=None,
            interactive=False,
            behavioral=False,
            vendor_mappable=True,
        )

    checks = [
        (
            "recaptcha_v3",
            ("recaptcha/enterprise", "grecaptcha.execute"),
            False,
            True,
            False,  # v3 behavioral — not vendor-solvable honestly
        ),
        (
            "recaptcha_v2",
            ("g-recaptcha", "recaptcha/api.js"),
            True,
            False,
            True,
        ),
        (
            "hcaptcha",
            ("h-captcha", "hcaptcha.com"),
            True,
            False,
            True,
        ),
        (
            "turnstile",
            ("cf-turnstile", "challenges.cloudflare.com"),
            False,
            True,
            True,
        ),
        (
            "funcaptcha",
            ("arkose", "funcaptcha"),
            True,
            False,
            False,
        ),
        (
            "geetest",
            ("geetest", "gt_captcha"),
            True,
            False,
            False,
        ),
        (
            "text_math",
            ("what is", "solve:"),
            True,
            False,
            False,
        ),
        (
            "text_captcha",
            ("type the characters", "enter the code shown"),
            True,
            False,
            False,
        ),
        (
            "image_captcha",
            ("captcha-image", "input#captcha"),
            True,
            False,
            False,
        ),
    ]
    for name, needles, interactive, behavioral, vendor_mappable in checks:
        if any(n in t for n in needles):
            return CaptchaDetection(
                type=name,
                sitekey=_sitekey(html),
                page_url=page_url,
                frame="iframe" if "iframe" in t and name.startswith("recaptcha") else None,
                interactive=interactive,
                behavioral=behavioral,
                vendor_mappable=vendor_mappable,
            )
    if "captcha" in t:
        return CaptchaDetection(
            type="unknown_captcha",
            sitekey=_sitekey(html),
            page_url=page_url,
            frame=None,
            interactive=True,
            behavioral=False,
            vendor_mappable=False,
        )
    return None
