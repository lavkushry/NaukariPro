"""Captcha Resolution Pipeline (§4.9) — human-default, vendor opt-in, fail-closed."""

from naukari_pro.captcha.circuit import CIRCUIT_UNRESOLVED_THRESHOLD, circuit_open
from naukari_pro.captcha.detector import CaptchaDetection, detect_captcha
from naukari_pro.captcha.events import CaptchaEventsStore
from naukari_pro.captcha.resolver import CaptchaResolverChain, CaptchaResolveResult
from naukari_pro.captcha.safety import (
    EXIT_CAPTCHA_BLOCKED,
    CaptchaResult,
    CaptchaSafetyManager,
    Resolution,
    detect_captcha_type,
    domain_allowed,
    extract_domain,
)

__all__ = [
    "CaptchaDetection",
    "CaptchaEventsStore",
    "CaptchaResolverChain",
    "CaptchaResolveResult",
    "CaptchaResult",
    "CaptchaSafetyManager",
    "CIRCUIT_UNRESOLVED_THRESHOLD",
    "EXIT_CAPTCHA_BLOCKED",
    "Resolution",
    "circuit_open",
    "detect_captcha",
    "detect_captcha_type",
    "domain_allowed",
    "extract_domain",
]
