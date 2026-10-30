"""
naukariPro Feature: Evidence Verifier Shim
Re-exports EvidenceVerifier from naukari_pro.modules.learning.evidence.
"""

from naukari_pro.modules.learning.evidence import (
    EvidenceVerifier,
    PNG_MAGIC_HEADER,
    MIN_SCREENSHOT_BYTES,
)

__all__ = [
    "EvidenceVerifier",
    "PNG_MAGIC_HEADER",
    "MIN_SCREENSHOT_BYTES",
]
