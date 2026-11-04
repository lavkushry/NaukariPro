"""
Back-compat shim — implementation lives in naukari_pro.captcha (§4.9).
"""

from naukari_pro.captcha.circuit import CIRCUIT_UNRESOLVED_THRESHOLD
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
    "EXIT_CAPTCHA_BLOCKED",
    "CIRCUIT_UNRESOLVED_THRESHOLD",
    "CaptchaResult",
    "CaptchaSafetyManager",
    "Resolution",
    "detect_captcha_type",
    "domain_allowed",
    "extract_domain",
]
