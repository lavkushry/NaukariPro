"""Tier 4 — vendor solver (opt-in, default OFF). Never constructed in human mode."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, Protocol


class VendorClient(Protocol):
    def create_task(self, *, captcha_type: str, page_url: str, sitekey: str = "") -> str: ...

    def get_result(self, task_id: str) -> Optional[str]: ...


@dataclass
class VendorConfig:
    api_key: str
    provider: str = "2captcha"
    enabled: bool = False


def build_vendor_client(
    *,
    mode: str,
    api_key: Optional[str] = None,
) -> Optional[VendorClient]:
    """
    Human mode must never construct a vendor HTTP client.
    Vendor mode requires an explicit API key.
    """
    modes = {m.strip() for m in (mode or "human").lower().split(",") if m.strip()}
    if "vendor" not in modes:
        return None
    key = api_key if api_key is not None else os.environ.get("CAPTCHA_VENDOR_API_KEY", "")
    if not key:
        return None
    return _StubVendorClient(api_key=key)


class _StubVendorClient:
    """Offline-safe stub — real HTTP is intentionally not implemented in CI."""

    def __init__(self, *, api_key: str) -> None:
        self.api_key = api_key
        self.calls = 0

    def create_task(self, *, captcha_type: str, page_url: str, sitekey: str = "") -> str:
        self.calls += 1
        return f"task-{self.calls}"

    def get_result(self, task_id: str) -> Optional[str]:
        # Stub always returns None so real solves require injecting a callable in tests
        return None
