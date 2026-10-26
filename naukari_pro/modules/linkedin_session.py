"""
naukariPro LinkedIn Stealth Session & Cookie Architecture Module
Milestone 1: Anti-detection Playwright session manager for LinkedIn.
Provides persistent Chromium context, OS-level flock mutual exclusion,
priority cookie injection (li_at), checkpoint/expiry detection, and diagnostic verification.
"""

import os
import sys
import re
import json
import time
import shutil
import logging
import inspect
from datetime import datetime, timezone
from urllib.parse import urlparse
from typing import Optional, Dict, Any, List, Union, Tuple

try:
    import fcntl
except ImportError:
    fcntl = None

from playwright.async_api import Playwright as AsyncPlaywright, BrowserContext as AsyncBrowserContext, Page as AsyncPage

from naukari_pro.config import WORKSPACE_DIR, load_config
from naukari_pro.session import SessionLock, cleanup_stale_chromium_locks, parse_proxy_settings

logger = logging.getLogger("naukariPro.LinkedInSession")

# Default Workspace Paths
DEFAULT_LINKEDIN_SESSION_DIR = os.path.join(WORKSPACE_DIR, "linkedin_system", "browser_session")
DEFAULT_LINKEDIN_LOCK_FILE = os.path.join(WORKSPACE_DIR, "linkedin_system", ".linkedin_session.lock")
DEFAULT_LINKEDIN_COOKIE_FILE = os.path.join(WORKSPACE_DIR, "linkedin_system", "session_cookies.json")
FEED_URL = "https://www.linkedin.com/feed/"

# Platform consistency
DEFAULT_PLATFORM = "MacIntel" if sys.platform == "darwin" else ("Win32" if sys.platform == "win32" else "Linux x86_64")
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    if sys.platform == "darwin"
    else "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

# Stealth JS Anti-Detection Injection template
STEALTH_JS_TEMPLATE = """
// 1. Evade navigator.webdriver detection
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// 2. Mock window.chrome runtime
window.chrome = {
    runtime: {},
    loadTimes: function() {},
    csi: function() {},
    app: {}
};
window.navigator.chrome = window.chrome;

// 3. Platform & Vendor Consistency
Object.defineProperty(navigator, 'platform', { get: () => '__PLATFORM__' });
Object.defineProperty(navigator, 'vendor', { get: () => 'Google Inc.' });

// 4. Emulate realistic browser hardware and language properties
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });

// 5. Spoof WebGL vendor and renderer (Intel Iris OpenGL Engine)
const getParameterOrig = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) return 'Intel Inc.'; // UNMASKED_VENDOR_WEBGL
    if (parameter === 37446) return 'Intel Iris OpenGL Engine'; // UNMASKED_RENDERER_WEBGL
    return getParameterOrig.call(this, parameter);
};
if (typeof WebGL2RenderingContext !== 'undefined') {
    const getParameter2Orig = WebGL2RenderingContext.prototype.getParameter;
    WebGL2RenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) return 'Intel Inc.';
        if (parameter === 37446) return 'Intel Iris OpenGL Engine';
        return getParameter2Orig.call(this, parameter);
    };
}
"""
STEALTH_JS = STEALTH_JS_TEMPLATE.replace("__PLATFORM__", DEFAULT_PLATFORM)

# Note: context.on("close", lambda *args, **kwargs: lock.release()) is used locally
# in create_stealth_context to avoid global monkeypatching of SessionLock.


# ==============================================================================
# Error Hierarchy
# ==============================================================================

class LinkedInError(Exception):
    """Root exception for all LinkedIn automation operations."""
    pass


class LinkedInSessionError(LinkedInError):
    """Base exception for LinkedIn session, cookie, and browser initialization failures."""
    pass


class LinkedInCookieMissingError(LinkedInSessionError):
    """Raised when no li_at cookie can be discovered in .env or session files."""
    def __init__(self, message: Optional[str] = None):
        msg = message or (
            "LinkedIn authentication cookie (li_at) missing.\n"
            "Action Required: Set LINKEDIN_LI_AT in .env or provide linkedin_system/session_cookies.json."
        )
        super().__init__(msg)


class LinkedInCookieExpiredError(LinkedInSessionError):
    """Raised when session cookie is invalid, expired, or rejected by LinkedIn authwall."""
    def __init__(self, message: Optional[str] = None, redirect_url: Optional[str] = None):
        msg = message or f"LinkedIn session expired or redirected to authwall (URL: {redirect_url})."
        super().__init__(msg)
        self.redirect_url = redirect_url


# Backward-compatibility alias
LinkedInSessionExpiredError = LinkedInCookieExpiredError


class LinkedInRateLimitError(LinkedInSessionError):
    """Raised when LinkedIn responds with HTTP 429 Too Many Requests."""
    def __init__(self, message: Optional[str] = None):
        super().__init__(message or "LinkedIn returned HTTP 429 (Too Many Requests / IP rate limit).")


class LinkedInCheckpointError(LinkedInSessionError):
    """Raised when LinkedIn presents a security checkpoint, CAPTCHA, or verification pin."""
    def __init__(self, message: str, checkpoint_url: Optional[str] = None, challenge_type: Optional[str] = None):
        super().__init__(message)
        self.checkpoint_url = checkpoint_url
        self.challenge_type = challenge_type


# ==============================================================================
# Helper Functions
# ==============================================================================

def sanitize_cookie_token(token: Optional[str]) -> Optional[str]:
    """Recursively strips quotes and whitespace from cookie token."""
    if not token:
        return None
    prev = None
    curr = str(token).strip()
    while curr != prev:
        prev = curr
        curr = curr.strip().strip('"\'').strip()
    return curr if curr else None


def mask_cookie_token(token: Optional[str]) -> str:
    """Masks a cookie token for safe logging/display without revealing credentials."""
    t = sanitize_cookie_token(token)
    if not t:
        return "None"
    if len(t) <= 8:
        return "****"
    return f"{t[:4]}...{t[-4:]} ({len(t)} chars, masked)"


def clean_avatar_name(alt_text: Optional[str]) -> Optional[str]:
    """Cleans nav avatar alt text to extract candidate name."""
    if not alt_text or not alt_text.strip():
        return None
    cleaned = re.sub(
        r"^(?:Photo\s+of|Profile\s+photo\s+of)(?:\s+|$)",
        "",
        alt_text.strip(),
        flags=re.IGNORECASE
    ).strip()
    return cleaned if cleaned else None


# ==============================================================================
# Session Manager Class
# ==============================================================================

class LinkedInSessionManager:
    """
    Manages anti-detect Playwright browser sessions for LinkedIn.
    Handles process locking, 3-tier cookie priority loading, and session verification.
    """

    def __init__(
        self,
        session_dir: str = DEFAULT_LINKEDIN_SESSION_DIR,
        cookie_path: Optional[str] = None,
        lock_path: Optional[str] = None,
        lock_timeout: float = 15.0
    ):
        self.session_dir = session_dir
        self.cookie_path = cookie_path or DEFAULT_LINKEDIN_COOKIE_FILE
        if lock_path:
            self.lock_path = lock_path
        elif session_dir != DEFAULT_LINKEDIN_SESSION_DIR:
            self.lock_path = os.path.join(session_dir, ".linkedin_session.lock")
        else:
            self.lock_path = DEFAULT_LINKEDIN_LOCK_FILE
        self.lock_timeout = lock_timeout
        self._session_lock: Optional[SessionLock] = None
        self.last_cookie_source: str = "NONE"

    def get_lock(self) -> SessionLock:
        """Instantiates or returns dedicated SessionLock for LinkedIn."""
        if self._session_lock is None:
            lock_dir = os.path.dirname(self.lock_path)
            lock_filename = os.path.basename(self.lock_path)
            self._session_lock = SessionLock(
                session_dir=lock_dir,
                lock_filename=lock_filename,
                timeout_sec=self.lock_timeout
            )
        return self._session_lock

    def get_li_at_cookie(self, raise_if_missing: bool = True) -> Optional[str]:
        """
        Retrieves the li_at cookie token following strict 3-tier priority:
        1. Environment variable LINKEDIN_LI_AT or LI_AT
        2. Workspace .env file directly (if unexported)
        3. Primary dedicated cookie file (self.cookie_path)
        4. Fallback files (cookies_seed.json, naukri_system/session_cookies.json)
        """
        # Tier 1: Environment variables
        for env_var in ["LINKEDIN_LI_AT", "LI_AT"]:
            val = os.getenv(env_var)
            if val and val.strip():
                token = sanitize_cookie_token(val)
                if token:
                    self.last_cookie_source = f".env ({env_var})"
                    return token

        # Tier 2: Check .env directly in workspace root
        target_ws = os.getenv("WORKSPACE_DIR") or WORKSPACE_DIR
        env_file = os.path.join(target_ws, ".env")
        if os.path.exists(env_file):
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        for prefix in ["LINKEDIN_LI_AT=", "export LINKEDIN_LI_AT=", "LI_AT=", "export LI_AT="]:
                            if line.startswith(prefix):
                                raw_val = line.split("=", 1)[1].split("#", 1)[0]
                                token = sanitize_cookie_token(raw_val)
                                if token:
                                    self.last_cookie_source = f".env file ({env_file})"
                                    return token
            except Exception as e:
                logger.debug("Notice reading workspace .env: %s", e)

        # Tier 3: Dedicated cookie files and fallbacks
        candidate_files = [
            (self.cookie_path, f"JSON cookies ({self.cookie_path})"),
            (os.path.join(target_ws, "linkedin_system", "cookies_seed.json"), "linkedin_system/cookies_seed.json"),
            (os.path.join(target_ws, "naukri_system", "session_cookies.json"), "naukri_system/session_cookies.json"),
            (os.path.join(target_ws, "naukri_system", "cookies_seed.json"), "naukri_system/cookies_seed.json")
        ]

        for path, desc in candidate_files:
            if not path or not os.path.exists(path):
                continue
            token = self._extract_token_from_file(path)
            if token:
                self.last_cookie_source = desc
                return token

        self.last_cookie_source = "NONE"
        if raise_if_missing:
            raise LinkedInCookieMissingError()
        return None

    def _extract_token_from_file(self, file_path: str) -> Optional[str]:
        """Extracts li_at token from JSON list, JSON dict, or raw text."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return None
                try:
                    data = json.loads(content)
                    if isinstance(data, list):
                        for cookie in data:
                            if isinstance(cookie, dict) and cookie.get("name") == "li_at":
                                val = cookie.get("value")
                                token = sanitize_cookie_token(val)
                                if token:
                                    return token
                    elif isinstance(data, dict):
                        for key in ["li_at", "LINKEDIN_LI_AT", "LI_AT", "token"]:
                            if key in data:
                                token = sanitize_cookie_token(data[key])
                                if token:
                                    return token
                except json.JSONDecodeError:
                    if len(content) > 10 and not content.startswith("{") and not content.startswith("["):
                        return sanitize_cookie_token(content)
        except Exception as e:
            logger.debug("Notice reading cookie candidate %s: %s", file_path, e)
        return None

    def format_cookie(self, token: str) -> Dict[str, Any]:
        """Formats li_at string into a Playwright-compliant cookie dictionary."""
        sanitized_token = sanitize_cookie_token(token) or token
        return {
            "name": "li_at",
            "value": sanitized_token,
            "domain": ".linkedin.com",
            "path": "/",
            "httpOnly": True,
            "secure": True,
            "sameSite": "Lax",
        }

    def get_cookie_dict(self) -> Dict[str, Any]:
        """Returns single Playwright cookie dict or raises LinkedInCookieMissingError."""
        token = self.get_li_at_cookie(raise_if_missing=True)
        return self.format_cookie(token)

    def get_formatted_cookies(self) -> List[Dict[str, Any]]:
        """
        Returns Playwright cookie list or raises LinkedInCookieMissingError.
        If a rich session_cookies.json file is available, loads all companion cookies
        (JSESSIONID, bcookie, bscookie, etc.) while ensuring li_at is updated with the active token.
        """
        token = self.get_li_at_cookie(raise_if_missing=True)
        cookies = []
        if self.cookie_path and os.path.exists(self.cookie_path):
            try:
                with open(self.cookie_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        cookies = [c for c in data if isinstance(c, dict) and "name" in c and "value" in c]
            except Exception as e:
                logger.debug("Notice loading companion cookies from %s: %s", self.cookie_path, e)

        has_li_at = False
        for c in cookies:
            if c.get("name") == "li_at":
                c["value"] = token
                has_li_at = True
                break

        if not has_li_at:
            cookies.append(self.format_cookie(token))

        return cookies

    async def create_stealth_context(
        self,
        p: Any,
        headless: bool = True,
        proxy: Optional[Union[str, Dict[str, Any]]] = None
    ) -> Any:
        """
        Launches an anti-detect persistent Playwright context with process locking,
        stale lock cleanup, STEALTH_JS injection, and li_at cookie synchronization.
        Ensures SessionLock is never leaked if cookie discovery or context launch fails.
        """
        # Force headless on Linux servers without display
        if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
            headless = True

        # 1. Pre-validate cookie presence BEFORE acquiring OS lock or launching browser
        cookies = self.get_formatted_cookies()

        os.makedirs(self.session_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.lock_path), exist_ok=True)

        # 2. Acquire dedicated session lock
        lock = self.get_lock()
        lock.acquire(blocking=True)

        context = None
        try:
            # 3. Cleanup stale Chromium locks inside user_data_dir while holding lock
            cleanup_stale_chromium_locks(self.session_dir)

            # 4. Detect Chrome binary vs Chromium
            channel = None
            system_chromium_path = None
            if sys.platform == "darwin":
                if os.path.exists("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"):
                    channel = "chrome"
            elif sys.platform.startswith("linux"):
                if shutil.which("google-chrome") or shutil.which("google-chrome-stable"):
                    channel = "chrome"
                else:
                    for cand in [shutil.which("chromium"), shutil.which("chromium-browser"), "/usr/bin/chromium"]:
                        if cand and os.path.exists(cand):
                            system_chromium_path = cand
                            break

            launch_args = [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-infobars",
                "--window-size=1920,1080",
            ]
            if not headless:
                launch_args.append("--start-maximized")

            kwargs: Dict[str, Any] = {
                "user_data_dir": self.session_dir,
                "headless": headless,
                "args": launch_args,
                "viewport": {"width": 1920, "height": 1080},
                "screen": {"width": 1920, "height": 1080},
                "user_agent": DEFAULT_USER_AGENT,
                "locale": "en-US",
                "timezone_id": "Asia/Kolkata",
                "geolocation": {"latitude": 12.9716, "longitude": 77.5946},
                "permissions": ["geolocation", "notifications"],
                "bypass_csp": True,
                "ignore_https_errors": True,
            }

            if channel:
                kwargs["channel"] = channel
            elif system_chromium_path:
                kwargs["executable_path"] = system_chromium_path

            # Proxy routing
            proxy_setting = parse_proxy_settings(proxy or os.getenv("LINKEDIN_PROXY") or os.getenv("NAUKRI_PROXY"))
            if proxy_setting:
                kwargs["proxy"] = proxy_setting

            # 5. Launch persistent context (handles both async Playwright and sync Playwright / mocks)
            res = p.chromium.launch_persistent_context(**kwargs)
            if inspect.isawaitable(res):
                context = await res
            else:
                context = res

            # 6. Bind lock lifecycle to context with argument-tolerant closure
            context._session_lock = lock
            if hasattr(context, "on"):
                context.on("close", lambda *args, **kwargs: lock.release())

            # 7. Inject stealth scripts
            if hasattr(context, "add_init_script"):
                res_init = context.add_init_script(STEALTH_JS)
                if inspect.isawaitable(res_init):
                    await res_init

            # 8. Inject li_at authentication cookie
            if hasattr(context, "add_cookies"):
                res_cookies = context.add_cookies(cookies)
                if inspect.isawaitable(res_cookies):
                    await res_cookies
            logger.info("Synchronized LinkedIn authentication cookie (li_at) into context.")

            return context
        except Exception:
            # Emergency cleanup: close context if open and guarantee lock release
            if context is not None and hasattr(context, "close"):
                try:
                    c_res = context.close()
                    if inspect.isawaitable(c_res):
                        await c_res
                except Exception:
                    pass
            lock.release()
            raise

    async def verify_session(self, page: Any, raise_for_status: bool = False) -> Dict[str, Any]:
        """
        Navigates to LinkedIn feed to test authentication freshness.
        Positively verifies LinkedIn domain and presence of authenticated feed elements.
        Detects security checkpoints, expired sessions, and extracts profile identity.
        Guarantees zero fallthrough to VALID on blank, error, or unauthenticated pages.
        """
        logger.info("Verifying LinkedIn session status...")

        # Step 0: Navigation Execution with Exception Trap
        nav_failed = False
        nav_error_msg = ""
        try:
            res_goto = page.goto(FEED_URL, wait_until="domcontentloaded", timeout=30000)
            if inspect.isawaitable(res_goto):
                await res_goto
        except Exception as e:
            nav_failed = True
            nav_error_msg = str(e)
            logger.warning("Navigation notice during session verification: %s", e)

        raw_url = getattr(page, "url", "") or ""
        current_url = raw_url.lower()

        # If navigation completely failed/timed out, distinguish 429 rate limit vs expired/unreachable
        if nav_failed:
            is_429 = "429" in nav_error_msg or "err_http_response_code_failure" in nav_error_msg.lower()
            status_name = "RATE_LIMITED" if is_429 else "EXPIRED"
            if raise_for_status:
                if is_429:
                    raise LinkedInRateLimitError(f"LinkedIn returned rate limit during verification: {nav_error_msg}")
                raise LinkedInCookieExpiredError(
                    f"Navigation failed during session verification: {nav_error_msg}",
                    redirect_url=raw_url
                )
            return {
                "status": status_name,
                "authenticated": False,
                "checkpoint_detected": False,
                "rate_limited": is_429,
                "candidate_name": None,
                "headline": None,
                "candidate_headline": None,
                "final_url": raw_url,
                "feed_url": raw_url,
                "detail": f"Navigation failed during session verification: {nav_error_msg}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        # Step 1: URL & Domain Verification
        parsed = urlparse(raw_url)
        hostname = (parsed.hostname or "").lower()
        is_linkedin_domain = hostname == "linkedin.com" or hostname.endswith(".linkedin.com")

        if not raw_url or raw_url == "about:blank" or not is_linkedin_domain:
            if raise_for_status:
                raise LinkedInCookieExpiredError(
                    f"Page loaded non-LinkedIn or blank URL: {raw_url or 'about:blank'}",
                    redirect_url=raw_url
                )
            return {
                "status": "UNKNOWN",
                "authenticated": False,
                "checkpoint_detected": False,
                "candidate_name": None,
                "headline": None,
                "candidate_headline": None,
                "final_url": raw_url,
                "feed_url": raw_url,
                "detail": f"Unrecognized non-LinkedIn or blank page: {raw_url or 'about:blank'}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        body_text = ""
        try:
            res_content = page.content()
            if inspect.isawaitable(res_content):
                body_text = (await res_content).lower()
            elif isinstance(res_content, str):
                body_text = res_content.lower()
        except Exception:
            pass

        # Helper to safely evaluate locator count across sync and async mocks
        async def _count_matches(selectors: Union[str, List[str]]) -> int:
            if isinstance(selectors, str):
                sel_candidates = [selectors] + [s.strip() for s in selectors.split(",") if s.strip()]
            else:
                sel_candidates = selectors
            for sel in sel_candidates:
                try:
                    loc = page.locator(sel)
                    cnt_res = loc.count()
                    if inspect.isawaitable(cnt_res):
                        cnt = await cnt_res
                    else:
                        cnt = int(cnt_res)
                    if cnt > 0:
                        return cnt
                except Exception:
                    continue
            return 0

        # Step 2: Comprehensive Checkpoint / CAPTCHA Detection
        is_checkpoint_url = (
            "/checkpoint" in current_url
            or "/uas/consumer-captcha" in current_url
            or "/uas/captcha" in current_url
            or "/challenge" in current_url
            or "/security-check" in current_url
        )
        
        captcha_count = await _count_matches([
            "input#captcha",
            "iframe[src*='captcha']",
            "iframe[src*='arkoselabs']",
            "iframe[src*='arkose']",
            "div.checkpoint-challenge",
            "input#input__email_verification_pin",
            "input#input__phone_verification_pin",
            "input[name='pin']",
            "div#checkpoint-challenge",
            "form#checkpoint-challenge-form",
            "div.challenge-dialog"
        ])
        
        has_checkpoint_text = (
            "security check" in body_text
            or "solve this puzzle" in body_text
            or "quick security check" in body_text
            or "verification pin" in body_text
            or "enter the code" in body_text
            or "let's do a quick security check" in body_text
        )

        if is_checkpoint_url or captcha_count > 0 or has_checkpoint_text:
            challenge_type = "Visual CAPTCHA" if ("captcha" in current_url or captcha_count > 0 or "puzzle" in body_text) else "Security Verification"
            if raise_for_status:
                raise LinkedInCheckpointError(
                    f"LinkedIn security challenge encountered ({challenge_type})",
                    checkpoint_url=raw_url,
                    challenge_type=challenge_type
                )
            return {
                "status": "CHECKPOINT",
                "authenticated": False,
                "checkpoint_detected": True,
                "candidate_name": None,
                "headline": None,
                "candidate_headline": None,
                "final_url": raw_url,
                "feed_url": raw_url,
                "detail": f"Security checkpoint or CAPTCHA detected ({challenge_type})",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        # Step 3: Rate-Limit Detection
        if "/uas/request-denied" in current_url or "http 999" in body_text or "request denied" in body_text:
            return {
                "status": "RATE_LIMITED",
                "authenticated": False,
                "checkpoint_detected": False,
                "candidate_name": None,
                "headline": None,
                "candidate_headline": None,
                "final_url": raw_url,
                "feed_url": raw_url,
                "detail": "LinkedIn WAF request denied (HTTP 999 / IP Block)",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        # Step 4: Expired Session / Authwall / Sign-In Detection
        expired_urls = ["/authwall", "/login", "/uas/login", "/home", "/signup", "/start/join"]
        is_expired_url = any(aw in current_url for aw in expired_urls)
        signin_count = await _count_matches([
            "input#session_key",
            "button[data-id='sign-in-form__submit-btn']",
            "form.login__form",
            "div.authwall-join-form",
            "button[data-tracking-control-name='cold_join_sign_in']",
            "input#username",
            "div.sign-in-card"
        ])
        
        has_signin_text = (
            ("sign in" in current_url and "sign in to see more" in body_text)
            or ("join now" in current_url and "agree & join" in body_text)
        )

        if is_expired_url or signin_count > 0 or has_signin_text:
            if raise_for_status:
                raise LinkedInCookieExpiredError(
                    "Session cookie rejected: redirected to login/authwall",
                    redirect_url=raw_url
                )
            return {
                "status": "EXPIRED",
                "authenticated": False,
                "checkpoint_detected": False,
                "candidate_name": None,
                "headline": None,
                "candidate_headline": None,
                "final_url": raw_url,
                "feed_url": raw_url,
                "detail": f"Redirected to authentication page: {raw_url}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        # Step 5: Identity & Authenticated DOM Extraction
        candidate_name = None
        candidate_headline = None
        profile_url = None

        # Tier 1: Left identity module
        tier1_name_selectors = [
            "div.feed-identity-module__actor-meta a span",
            "div.feed-identity-module__actor-meta a",
            "div.profile-rail-card__actor-link",
            "div[class*='feed-identity-module'] [class*='actor-meta'] a",
            "div.feed-identity-module h3 a",
            "div.feed-identity-module div.t-16",
            "a[href*='/in/'] span.feed-identity-module__actor-meta"
        ]
        for sel in tier1_name_selectors:
            try:
                loc = page.locator(sel)
                if hasattr(loc, "first"):
                    loc = loc.first
                cnt = loc.count()
                if inspect.isawaitable(cnt):
                    cnt = await cnt
                if cnt > 0:
                    text_res = loc.inner_text()
                    if inspect.isawaitable(text_res):
                        text = await text_res
                    else:
                        text = str(text_res)
                    text = text.strip()
                    if text and len(text) < 60 and not text.lower().startswith("view") and not text.lower().startswith("photo of"):
                        candidate_name = text
                        if hasattr(loc, "get_attribute"):
                            attr_res = loc.get_attribute("href")
                            if inspect.isawaitable(attr_res):
                                profile_url = await attr_res
                            else:
                                profile_url = attr_res
                        break
            except Exception:
                continue

        # Tier 2: Nav avatar alt text
        if not candidate_name:
            tier2_selectors = [
                "img.global-nav__me-photo",
                "button.global-nav__primary-link-me-menu-trigger img",
                "img[class*='global-nav__me-photo']"
            ]
            for sel in tier2_selectors:
                try:
                    loc = page.locator(sel)
                    if hasattr(loc, "first"):
                        loc = loc.first
                    cnt = loc.count()
                    if inspect.isawaitable(cnt):
                        cnt = await cnt
                    if cnt > 0 and hasattr(loc, "get_attribute"):
                        alt_res = loc.get_attribute("alt")
                        if inspect.isawaitable(alt_res):
                            alt_val = await alt_res
                        else:
                            alt_val = alt_res
                        cleaned = clean_avatar_name(alt_val)
                        if cleaned:
                            candidate_name = cleaned
                            break
                except Exception:
                    continue

        # Tier 3: In-feed profile links
        if not candidate_name:
            try:
                in_links = page.locator("a[href*='/in/']")
                cnt = in_links.count()
                if inspect.isawaitable(cnt):
                    cnt = await cnt
                if cnt > 0:
                    for idx in range(min(cnt, 8)):
                        link_loc = in_links.nth(idx)
                        href_res = link_loc.get_attribute("href")
                        href = (await href_res) if inspect.isawaitable(href_res) else href_res
                        txt_res = link_loc.inner_text()
                        txt = (await txt_res) if inspect.isawaitable(txt_res) else txt_res
                        txt = (txt or "").strip()
                        if txt and "\n" in txt:
                            txt = txt.split("\n")[0].strip()
                        if txt and 2 <= len(txt) <= 40 and not any(w in txt.lower() for w in ["view", "photo", "member", "linkedin", "premium"]):
                            candidate_name = txt
                            profile_url = href
                            break
            except Exception:
                pass

        # Headline extraction
        headline_selectors = [
            "div.feed-identity-module .feed-identity-module__headline",
            "div.feed-identity-module__actor-meta + p",
            "div[class*='feed-identity-module'] p.t-12",
            "div.identity-headline"
        ]
        for sel in headline_selectors:
            try:
                loc = page.locator(sel)
                if hasattr(loc, "first"):
                    loc = loc.first
                cnt = loc.count()
                if inspect.isawaitable(cnt):
                    cnt = await cnt
                if cnt > 0:
                    text_res = loc.inner_text()
                    if inspect.isawaitable(text_res):
                        text = await text_res
                    else:
                        text = str(text_res)
                    text = text.strip()
                    if text:
                        candidate_headline = text
                        break
            except Exception:
                continue

        # Count positive authenticated navigation & feed DOM anchors
        nav_count = await _count_matches([
            "nav.global-nav",
            "div#global-nav",
            "header#global-nav",
            "li.global-nav__me",
            "button.global-nav__primary-link-me-menu-trigger",
            "img.global-nav__me-photo",
            "div.feed-identity-module",
            "a[href*='/in/']"
        ])
        
        feed_content_count = await _count_matches([
            "div.scaffold-layout__main",
            "main.scaffold-layout__main",
            "div.feed-shared-update-v2",
            "div.feed-identity-module",
            "div.core-rail",
            "a[href*='/in/']"
        ])

        # POSITIVE ASSERTION GATE
        # Must have positive evidence of authenticated navigation or identity AND feed path
        dom_verified = (candidate_name is not None) or (nav_count > 0 and feed_content_count > 0)
        is_feed_subpath = (
            "/feed" in current_url
            or "/in/" in current_url
            or "/mynetwork" in current_url
            or "/jobs" in current_url
        )

        if dom_verified and is_feed_subpath:
            # Fallback to configured candidate identity if on authenticated feed
            if not candidate_name:
                cfg = load_config()
                candidate_name = cfg.get("candidate", {}).get("name", "Lavkush Kumar")

            if not candidate_headline and candidate_name:
                cfg = load_config()
                candidate_headline = cfg.get("candidate", {}).get("headline", "Azure Data Engineer | 2.5 YOE")

            return {
                "status": "VALID",
                "authenticated": True,
                "checkpoint_detected": False,
                "candidate_name": candidate_name,
                "headline": candidate_headline or "Azure Data Engineer | 2.5 YOE",
                "candidate_headline": candidate_headline or "Azure Data Engineer | 2.5 YOE",
                "profile_url": profile_url or "https://www.linkedin.com/in/me/",
                "final_url": raw_url,
                "feed_url": raw_url,
                "detail": "Active authenticated feed confirmed",
                "dom_verified": dom_verified,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        # Step 6: Negative Fallthrough — If not positively authenticated, report EXPIRED (or raise)
        if raise_for_status:
            raise LinkedInCookieExpiredError(
                f"Feed verification failed: unauthenticated DOM at {raw_url}",
                redirect_url=raw_url
            )
        return {
            "status": "EXPIRED",
            "authenticated": False,
            "checkpoint_detected": False,
            "candidate_name": None,
            "headline": None,
            "candidate_headline": None,
            "final_url": raw_url,
            "feed_url": raw_url,
            "detail": f"Unauthenticated page or unverified feed state on LinkedIn: {raw_url}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def save_session_cookies(self, cookies: List[Dict[str, Any]]) -> bool:
        """Persists extracted browser cookies to session_cookies.json."""
        try:
            os.makedirs(os.path.dirname(self.cookie_path), exist_ok=True)
            with open(self.cookie_path, "w", encoding="utf-8") as f:
                json.dump(cookies, f, indent=2)
            logger.info("Saved %d LinkedIn cookies to %s", len(cookies), self.cookie_path)
            return True
        except Exception as e:
            logger.warning("Could not persist cookies to %s: %s", self.cookie_path, e)
            return False

    async def __aenter__(self):
        self.get_lock().acquire(blocking=True)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session_lock:
            self._session_lock.release()

    def __enter__(self):
        self.get_lock().acquire(blocking=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._session_lock:
            self._session_lock.release()
