"""Typed NaukariPro errors — parsers/gates raise these instead of raw crashes."""

from __future__ import annotations

from typing import Any, Dict, Optional


class NaukariProError(Exception):
    """Base typed error with optional context for ledger/trace."""

    code: str = "NP_ERROR"
    exit_code: int = 1

    def __init__(self, message: str, *, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.context = dict(context or {})

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": self.code,
            "message": self.message,
            "exit_code": self.exit_code,
            "context": self.context,
        }


class ParseError(NaukariProError):
    code = "NP_PARSE"
    exit_code = 4


class ValidationError(NaukariProError):
    code = "NP_VALIDATION"
    exit_code = 4


class ApprovalRequiredError(NaukariProError):
    code = "NP_APPROVAL"
    exit_code = 2


class BlockedError(NaukariProError):
    code = "NP_BLOCKED"
    exit_code = 2


class CaptchaBlockedError(NaukariProError):
    code = "NP_CAPTCHA"
    exit_code = 3


class BudgetExhaustedError(NaukariProError):
    code = "NP_BUDGET"
    exit_code = 2


class NetworkHardFailError(NaukariProError):
    code = "NP_NETWORK"
    exit_code = 1


class IntegrityError(NaukariProError):
    code = "NP_INTEGRITY"
    exit_code = 2


class ConfigError(NaukariProError):
    code = "NP_CONFIG"
    exit_code = 4
