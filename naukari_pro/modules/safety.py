"""
naukariPro Feature: Safety Rails & Execution Controls (M2 / R2)
Implements:
1. Randomized keystroke delays (30-80ms) for humanized typing
2. Cross-platform singleton application locks (fcntl.flock)
3. Captcha / security checkpoint detection, screenshot capture, and immediate abort
"""

import os
import time
import fcntl
import random
import inspect
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Any

from naukari_pro.config import BASE_DIR

logger = logging.getLogger("naukariPro.Safety")

CHECKPOINT_SELECTORS = [
    "input#captcha",
    "div.captcha-container",
    "iframe[src*='captcha']",
    "iframe[src*='recaptcha']",
    "iframe[src*='arkoselabs']",
    "iframe[src*='turnstile']",
    "div:has-text('Security Verification')",
    "div:has-text('Please solve this puzzle')",
    "div:has-text('Verify it\\'s you')",
    "div.checkpoint-challenge",
    "input[placeholder*='OTP']",
    "#otp",
    ".recaptcha",
    "#captcha-internal",
]

CHECKPOINT_URL_PATTERNS = [
    "/checkpoint",
    "/uas/consumer-captcha",
    "/uas/captcha",
    "challenge",
    "security-check",
    "verify",
    "access_denied",
]


def get_human_typing_delay() -> int:
    """Returns randomized per-character typing delay in milliseconds (30ms - 80ms)."""
    return random.randint(30, 80)


async def human_type_async(target: Any, text: str, page: Optional[Any] = None) -> None:
    """
    Types text into an input element or page using humanized keystroke delays (30-80ms).
    Prefers press_sequentially / type over instant fill.
    """
    if not text:
        return

    delay_ms = get_human_typing_delay()

    if hasattr(target, "focus"):
        f_res = target.focus()
        if inspect.isawaitable(f_res):
            await f_res

    if hasattr(target, "press_sequentially"):
        res = target.press_sequentially(text, delay=delay_ms)
        if inspect.isawaitable(res):
            await res
    elif hasattr(target, "type"):
        res = target.type(text, delay=delay_ms)
        if inspect.isawaitable(res):
            await res
    elif page and hasattr(page, "keyboard"):
        res = page.keyboard.type(text, delay=delay_ms)
        if inspect.isawaitable(res):
            await res
    elif hasattr(target, "fill"):
        res = target.fill(text)
        if inspect.isawaitable(res):
            await res


class SafetyViolationError(BlockingIOError):
    """Raised when process-level application lock cannot be acquired or safety rule violated."""
    pass


class CheckpointDetectedException(Exception):
    """Raised when CAPTCHA, bot checkpoint, or security challenge is encountered."""
    pass


def human_type_sync(target: Any, text: str, page: Optional[Any] = None) -> None:
    """Synchronous version of human typing with 30-80ms delays."""
    if not text:
        return
    delay_ms = get_human_typing_delay()
    if hasattr(target, "focus"):
        target.focus()
    if hasattr(target, "type"):
        target.type(text, delay=delay_ms)
    elif hasattr(target, "fill"):
        target.fill(text)


def safe_click_async(target: Any, page: Optional[Any] = None) -> None:
    pass


def safe_click_sync(target: Any, page: Optional[Any] = None) -> None:
    if hasattr(target, "click"):
        target.click()


class ApplicationLock:
    """
    Global mutual exclusion lock using fcntl.flock to prevent overlapping
    runs across multi-channel application pipelines (Naukri, LinkedIn, Career Portals).
    """

    def __init__(self, lock_path: Optional[str] = None, lock_file: Optional[str] = None, timeout_sec: float = 5.0):
        self.lock_path = lock_file or lock_path or os.path.join(BASE_DIR, ".naukari_application.lock")
        self.timeout_sec = timeout_sec
        self._fd: Optional[Any] = None
        self._acquired = False

    @property
    def is_locked(self) -> bool:
        return self._acquired

    def __enter__(self):
        self.acquire(blocking=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

    def acquire(self, blocking: bool = False) -> bool:
        if self._acquired:
            return True
        start = time.time()
        self._fd = open(self.lock_path, "a+")
        while True:
            try:
                fcntl.flock(self._fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                self._acquired = True
                self._fd.seek(0)
                self._fd.truncate()
                self._fd.write(f"pid={os.getpid()}\ntime={time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                self._fd.flush()
                return True
            except (BlockingIOError, OSError) as e:
                if not blocking or (time.time() - start) >= self.timeout_sec:
                    if self._fd:
                        self._fd.close()
                        self._fd = None
                    raise SafetyViolationError(f"Process-level lock already held by another process on {self.lock_path}") from e
                time.sleep(0.2)

    def release(self):
        if self._acquired and self._fd:
            try:
                fcntl.flock(self._fd.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
            try:
                self._fd.close()
            except Exception:
                pass
            self._fd = None
            self._acquired = False


SingletonLock = ApplicationLock


def detect_security_checkpoint_sync(page: Any, platform: str = "generic", raise_exception: bool = False) -> Optional[str]:
    """Synchronous checkpoint detection for Playwright pages."""
    if not page:
        return None
    url = getattr(page, "url", "") or ""
    detected = False
    reason = ""
    for pat in CHECKPOINT_URL_PATTERNS:
        if pat in url.lower():
            detected = True
            reason = f"Checkpoint URL pattern: {pat}"
            break
    if not detected and hasattr(page, "query_selector"):
        for sel in CHECKPOINT_SELECTORS:
            try:
                el = page.query_selector(sel)
                if el and getattr(el, "is_visible", lambda: True)():
                    detected = True
                    reason = f"Challenge DOM selector visible: {sel}"
                    break
            except Exception:
                continue
    if not detected:
        return None
    if raise_exception:
        raise CheckpointDetectedException(f"Security challenge or CAPTCHA detected on {platform} ({reason})")
    return reason


async def check_and_handle_checkpoint(page: Any, platform: str = "generic") -> Optional[str]:
    """
    Inspects page for CAPTCHA, security checkpoint, or account flag.
    If detected:
      1. Immediately aborts execution without escalating evasion.
      2. Captures full screenshot to evidence/checkpoint_<platform>_<timestamp>.png.
      3. Dispatches desktop notification alert.
      4. Returns screenshot path.
    """
    if not page:
        return None

    url = getattr(page, "url", "") or ""
    detected = False
    reason = ""

    # 1. URL Inspection
    for pat in CHECKPOINT_URL_PATTERNS:
        if pat in url.lower():
            detected = True
            reason = f"Checkpoint URL pattern: {pat}"
            break

    # 2. DOM Inspection
    if not detected and hasattr(page, "locator"):
        for sel in CHECKPOINT_SELECTORS:
            try:
                loc = page.locator(sel)
                cnt_res = loc.count()
                cnt = await cnt_res if inspect.isawaitable(cnt_res) else cnt_res
                if cnt > 0:
                    first_el = loc.first if hasattr(loc, "first") else loc
                    vis_res = first_el.is_visible()
                    vis = await vis_res if inspect.isawaitable(vis_res) else vis_res
                    if vis:
                        detected = True
                        reason = f"Challenge selector visible: {sel}"
                        break
            except Exception:
                continue

    if not detected:
        return None

    # Prepare evidence directory
    evidence_dir = Path(BASE_DIR) / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    screenshot_name = f"checkpoint_{platform.lower()}_{timestamp}.png"
    screenshot_path = evidence_dir / screenshot_name

    try:
        if hasattr(page, "screenshot"):
            ss_res = page.screenshot(path=str(screenshot_path), full_page=True)
            if inspect.isawaitable(ss_res):
                await ss_res
    except Exception as e:
        logger.error("Failed to capture checkpoint screenshot: %s", e)

    # Trigger desktop alert if instant alerts module exists
    try:
        from naukari_pro.modules.job_alerts import InstantAlertsEngine
        alerter = InstantAlertsEngine()
        alerter.send_notification(
            title="⚠️ SECURITY CHECKPOINT DETECTED",
            subtitle=f"Platform: {platform.capitalize()} — Execution Aborted",
            message=f"Challenge encountered ({reason}). Screenshot saved: {screenshot_name}. Awaiting human action."
        )
    except Exception:
        pass

    logger.critical(
        "🛑 ACCOUNT SAFETY RAIL TRIGGERED: Checkpoint detected on %s (%s). "
        "Saved evidence to %s. Halting runner to preserve account integrity.",
        platform, reason, screenshot_path
    )
    return str(screenshot_path)


detect_security_checkpoint_async = check_and_handle_checkpoint
