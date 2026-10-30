"""
naukariPro Learning Subsystem: Safety Rails & Execution Controls (M2 / R2)
Re-exports core safety mechanisms for learning modules.
"""

from naukari_pro.modules.safety import (
    CHECKPOINT_SELECTORS,
    CHECKPOINT_URL_PATTERNS,
    ApplicationLock,
    SingletonLock,
    SafetyViolationError,
    CheckpointDetectedException,
    get_human_typing_delay,
    human_type_async,
    human_type_sync,
    detect_security_checkpoint_async,
    detect_security_checkpoint_sync,
    safe_click_async,
    safe_click_sync,
)

__all__ = [
    "CHECKPOINT_SELECTORS",
    "CHECKPOINT_URL_PATTERNS",
    "ApplicationLock",
    "SingletonLock",
    "SafetyViolationError",
    "CheckpointDetectedException",
    "get_human_typing_delay",
    "human_type_async",
    "human_type_sync",
    "detect_security_checkpoint_async",
    "detect_security_checkpoint_sync",
    "safe_click_async",
    "safe_click_sync",
]
