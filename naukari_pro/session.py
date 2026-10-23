"""
naukariPro Browser Session & Anti-Bot Evasion Module
Provides persistent Chrome/Chromium context, stealth JS injection, and cookie synchronization.
Supports macOS, Linux (ARM64/x86_64), and Headless Cloud Execution.
Handles OTP and Captcha challenge detection gracefully.
Features 15 & 16: Process-level file locking, SingletonLock protection, NAUKRI_PROXY routing, and Akamai WAF evasion.
"""

import os
import sys
import time
import json
import logging
import platform
import shutil
from urllib.parse import urlparse, unquote
from typing import Optional, Dict, Any, Union

try:
    import fcntl
except ImportError:
    fcntl = None

from naukari_pro.config import SESSION_DIR, COOKIES_SEED_PATH, WORKSPACE_DIR, load_config

logger = logging.getLogger("naukariPro.Session")

# Akamai Bot Protection & WAF Evasion Stealth Injection
STEALTH_JS = """
// 1. Evade navigator.webdriver detection
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// 2. Fix window.chrome (Akamai check: typeof window.chrome !== 'undefined')
window.chrome = {
    runtime: {},
    loadTimes: function() {},
    csi: function() {},
    app: {}
};
window.navigator.chrome = window.chrome;

// 3. Match navigator.platform with Windows User Agent
Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
Object.defineProperty(navigator, 'vendor', { get: () => 'Google Inc.' });

// 4. Emulate realistic browser hardware and language properties
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en', 'hi'] });
Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });

// 5. Spoof WebGL vendor and renderer to evade headless Linux SwiftShader/llvmpipe detection
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


class SessionLock:
    """
    Process-level mutual exclusion file lock for Chromium SESSION_DIR using fcntl.flock.
    Prevents concurrent browser launches against the same user data directory,
    eliminating Chromium SingletonLock collisions, SQLite database locks, and process aborts.
    Supports both synchronous and asynchronous context managers.
    """

    def __init__(self, session_dir=None, lock_filename=".naukari_session.lock", timeout_sec=15.0, poll_interval=0.25):
        self.session_dir = session_dir or SESSION_DIR
        os.makedirs(self.session_dir, exist_ok=True)
        self.lock_path = os.path.join(self.session_dir, lock_filename)
        self.timeout_sec = timeout_sec
        self.poll_interval = poll_interval
        self._file_obj = None
        self._acquired = False

    def acquire(self, blocking=True):
        """Acquires exclusive process lock on SESSION_DIR."""
        if self._acquired and self._file_obj is not None:
            return True

        start_time = time.time()
        self._file_obj = open(self.lock_path, "a+")

        while True:
            try:
                if fcntl:
                    fcntl.flock(self._file_obj.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                self._acquired = True
                try:
                    self._file_obj.seek(0)
                    self._file_obj.truncate()
                    self._file_obj.write(f"pid={os.getpid()}\ntime={time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    self._file_obj.flush()
                except Exception:
                    pass
                logger.debug("Acquired session lock on %s (PID %d)", self.lock_path, os.getpid())
                return True
            except (BlockingIOError, IOError, OSError) as e:
                if not blocking:
                    self._cleanup_fd()
                    raise BlockingIOError(f"Session lock currently held on {self.lock_path} by another process") from e

                elapsed = time.time() - start_time
                if elapsed >= self.timeout_sec:
                    self._cleanup_fd()
                    raise TimeoutError(
                        f"Timed out after {self.timeout_sec}s waiting for session lock on {self.lock_path}. "
                        "Another Chromium browser session is currently active."
                    ) from e

                logger.info("Session directory locked by another process. Waiting (%.1fs elapsed)...", elapsed)
                time.sleep(self.poll_interval)

    def release(self):
        """Releases the session lock. Idempotent across multiple invocations."""
        if not self._acquired or self._file_obj is None:
            return
        try:
            if fcntl:
                fcntl.flock(self._file_obj.fileno(), fcntl.LOCK_UN)
        except Exception as e:
            logger.debug("Notice releasing flock: %s", e)
        finally:
            self._cleanup_fd()
            self._acquired = False
            logger.debug("Released session lock on %s", self.lock_path)

    def _cleanup_fd(self):
        if self._file_obj is not None:
            try:
                self._file_obj.close()
            except Exception:
                pass
            self._file_obj = None

    def __enter__(self):
        self.acquire(blocking=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

    async def __aenter__(self):
        self.acquire(blocking=True)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.release()


def cleanup_stale_chromium_locks(session_dir=SESSION_DIR):
    """
    Cleans up stale Chromium singleton locks (SingletonLock, SingletonSocket, SingletonCookie).
    Safe to execute only while holding SessionLock.
    Handles standard files, symlinks, and broken symlinks safely.
    """
    for lock_file in ["SingletonLock", "SingletonSocket", "SingletonCookie"]:
        lock_path = os.path.join(session_dir, lock_file)
        if os.path.lexists(lock_path) or os.path.islink(lock_path) or os.path.exists(lock_path):
            try:
                os.unlink(lock_path)
                logger.debug("Unlinked stale lock file: %s", lock_path)
            except Exception as e:
                logger.warning("Could not unlink stale lock %s: %s", lock_path, e)


def parse_proxy_settings(proxy_input: Optional[Union[str, Dict[str, Any]]] = None) -> Optional[Dict[str, str]]:
    """
    Parses and normalizes proxy configurations for Playwright launch_persistent_context.

    Accepts:
      - None: falls back to os.environ.get("NAUKRI_PROXY")
      - str: 'http://user:pass@host:port', 'http://host:port', 'host:port', 'socks5://user:pass@host:port'
      - dict: {'server': '...', 'username': '...', 'password': '...', 'bypass': '...'}

    Returns:
      - Playwright-compliant ProxySettings dict:
        {'server': '...', 'username': '...', 'password': '...', Optional['bypass']: '...'}
      - None if proxy is unconfigured or invalid.
    """
    if proxy_input is None:
        proxy_input = os.environ.get("NAUKRI_PROXY")

    if not proxy_input:
        return None

    try:
        # Case 1: Dictionary input
        if isinstance(proxy_input, dict):
            server = proxy_input.get("server", "").strip()
            if not server:
                return None
            if "://" not in server:
                server = "http://" + server
            parsed = urlparse(server)
            username = proxy_input.get("username") or (unquote(parsed.username) if parsed.username else None)
            password = proxy_input.get("password") or (unquote(parsed.password) if parsed.password else None)
            bypass = proxy_input.get("bypass")

            clean_host = parsed.hostname or ""
            if parsed.port:
                clean_host += f":{parsed.port}"
            clean_server = f"{parsed.scheme or 'http'}://{clean_host}"

            res = {"server": clean_server}
            if username:
                res["username"] = username
            if password:
                res["password"] = password
            if bypass:
                res["bypass"] = str(bypass)
            return res

        # Case 2: String input
        if isinstance(proxy_input, str):
            p_str = proxy_input.strip()
            if not p_str:
                return None
            if "://" not in p_str:
                p_str = "http://" + p_str
            parsed = urlparse(p_str)
            scheme = parsed.scheme or "http"
            username = unquote(parsed.username) if parsed.username else None
            password = unquote(parsed.password) if parsed.password else None

            clean_host = parsed.hostname or ""
            if parsed.port:
                clean_host += f":{parsed.port}"
            clean_server = f"{scheme}://{clean_host}"

            res = {"server": clean_server}
            if username:
                res["username"] = username
            if password:
                res["password"] = password
            return res
    except Exception as e:
        logger.warning("Could not parse proxy configuration '%s': %s", proxy_input, e)
        return None

    return None


def save_session_cookies(context):
    """Exports authenticated session cookies to disk for persistent reuse."""
    try:
        cookies = context.cookies()
        if cookies:
            os.makedirs(os.path.dirname(COOKIES_SEED_PATH), exist_ok=True)
            with open(COOKIES_SEED_PATH, "w", encoding="utf-8") as f:
                json.dump(cookies, f, indent=2)
            alt_path = os.path.join(WORKSPACE_DIR, "naukri_system", "session_cookies.json")
            with open(alt_path, "w", encoding="utf-8") as f:
                json.dump(cookies, f, indent=2)
            logger.info("Saved %d authenticated session tokens to disk.", len(cookies))
            return True
    except Exception as e:
        logger.warning("Could not persist session cookies: %s", e)
    return False


def get_stealth_context(playwright, headless=False, proxy=None, lock_timeout=15.0):
    """
    Launches an anti-detect persistent Google Chrome/Chromium context with
    process-level file lock protection on SESSION_DIR, automatic stale lock cleanup,
    and Akamai Bot Protection WAF evasion.
    Works natively across macOS and Linux with zero configuration.
    Routes through NAUKRI_PROXY if specified or present in environment.
    Seamlessly falls back to bundled Chromium if Google Chrome is not installed.
    """
    # 1. On Linux servers without an X11 display, automatically enforce headless mode
    if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
        headless = True

    os.makedirs(SESSION_DIR, exist_ok=True)

    # 2. Acquire exclusive process file lock on SESSION_DIR to prevent concurrent Chromium collisions
    session_lock = SessionLock(session_dir=SESSION_DIR, timeout_sec=lock_timeout)
    session_lock.acquire(blocking=True)

    # 3. Clean up stale lock files ONLY while holding exclusive session lock
    cleanup_stale_chromium_locks(SESSION_DIR)

    launch_args = [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
    ]
    if not headless:
        launch_args.append("--start-maximized")

    # 4. Resolve system Chrome or Chromium binary
    has_system_chrome = False
    system_chromium_path = None
    if sys.platform == "darwin":
        has_system_chrome = os.path.exists("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    elif sys.platform.startswith("linux"):
        has_system_chrome = bool(shutil.which("google-chrome") or shutil.which("google-chrome-stable"))
        if not has_system_chrome:
            for cand in [shutil.which("chromium"), shutil.which("chromium-browser"), "/snap/bin/chromium", "/usr/bin/chromium"]:
                if cand and os.path.exists(cand):
                    system_chromium_path = cand
                    break

    channel = "chrome" if has_system_chrome else None

    kwargs = {
        "user_data_dir": SESSION_DIR,
        "headless": headless,
        "args": launch_args,
        "viewport": None,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    }
    if channel:
        kwargs["channel"] = channel
    elif system_chromium_path:
        kwargs["executable_path"] = system_chromium_path

    # 5. Ingest and configure proxy routing for Akamai WAF evasion
    proxy_settings = parse_proxy_settings(proxy)
    if proxy_settings:
        kwargs["proxy"] = proxy_settings
        logger.info("Configured Playwright upstream proxy: %s", proxy_settings.get("server"))

    # 6. Launch persistent context with fallback
    try:
        context = playwright.chromium.launch_persistent_context(**kwargs)
    except Exception as e:
        logger.warning("Primary browser launch fallback (%s). Retrying with default bundled Chromium...", e)
        kwargs.pop("channel", None)
        kwargs.pop("executable_path", None)
        # Refresh stale locks in case first attempt left broken state
        cleanup_stale_chromium_locks(SESSION_DIR)
        context = playwright.chromium.launch_persistent_context(**kwargs)

    # 7. Bind session lock lifecycle to Playwright context
    context._session_lock = session_lock
    context.on("close", lambda _: session_lock.release())

    context.add_init_script(STEALTH_JS)

    # 8. Inject latest session cookies if available
    if os.path.exists(COOKIES_SEED_PATH):
        try:
            with open(COOKIES_SEED_PATH, "r", encoding="utf-8") as f:
                seed_cookies = json.load(f)
            context.add_cookies(seed_cookies)
            logger.info("Synchronized %d session authentication tokens.", len(seed_cookies))
        except Exception as e:
            logger.warning("Could not load seed cookies: %s", e)

    return context


def detect_challenge(page):
    """Inspects page DOM for OTP or Captcha challenges."""
    challenge_type = None
    try:
        body = page.locator("body").inner_text().lower()
        if "otp" in body or page.locator("input[placeholder*='OTP'], #otp, input[name*='otp']").count() > 0:
            challenge_type = "OTP Verification"
        elif "captcha" in body or page.locator("iframe[src*='captcha'], iframe[src*='recaptcha'], #captcha").count() > 0:
            challenge_type = "Visual Captcha"
    except Exception:
        pass
    return challenge_type


def ensure_authenticated(page, headless=False):
    """
    Verifies that the session is logged into Naukri.
    If not logged in, handles interactive wait in headed mode or provides actionable error in headless mode.
    """
    logger.info("Validating Naukri authentication state...")
    try:
        page.goto("https://www.naukri.com/mnjuser/profile", wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)
    except Exception as e:
        logger.warning("Navigation notice: %s", e)

    is_login_page = "login" in page.url or page.locator("text=Login").first.is_visible() or "Access Denied" in page.title()

    if is_login_page:
        # 1. Attempt automated credential login if configured
        email = os.getenv("NAUKRI_EMAIL") or load_config().get("candidate", {}).get("email")
        password = os.getenv("NAUKRI_PASSWORD")
        if email and password:
            try:
                logger.info("Attempting automated credential login...")
                if "nlogin" not in page.url:
                    page.goto("https://www.naukri.com/nlogin/login", wait_until="domcontentloaded", timeout=30000)
                    time.sleep(2)
                user_field = page.locator("#usernameField").first
                pass_field = page.locator("#passwordField").first
                btn = page.locator("button[type='submit']").first
                if user_field.is_visible() and pass_field.is_visible():
                    user_field.fill(email)
                    time.sleep(0.3)
                    pass_field.fill(password)
                    time.sleep(0.3)
                    btn.click()
                    time.sleep(5)
                    # Check if login succeeded
                    if "nlogin" not in page.url or page.locator("text=View profile").count() > 0 or "Mynaukri" in page.title():
                        logger.info("Automated login succeeded!")
                        save_session_cookies(page.context)
                        return True
            except Exception as e:
                logger.warning("Automated login attempt notice: %s", e)

        challenge = detect_challenge(page)
        challenge_str = f" ({challenge} detected)" if challenge else ""

        if headless:
            logger.error("=" * 70)
            logger.error("HEADLESS AUTHENTICATION REQUIRED%s", challenge_str)
            logger.error("Interactive OTP or Captcha challenge cannot be completed in headless mode.")
            logger.error("Remedy: Run './naukariPro auth' in a desktop environment to log in once,")
            logger.error("which will save authenticated session cookies for headless automation.")
            logger.error("=" * 70)
            return False

        logger.warning("=" * 70)
        logger.warning("ACTION REQUIRED: Complete login in the opened Chrome browser window%s.", challenge_str)
        logger.warning("Waiting for successful login (up to 3 minutes)...")
        logger.warning("=" * 70)
        try:
            page.wait_for_url("**/profile**", timeout=180000)
            logger.info("Login confirmed! Session permanently saved at %s", SESSION_DIR)
            save_session_cookies(page.context)
            return True
        except Exception:
            logger.error("Authentication timeout. Please run './naukariPro auth' to log in.")
            return False
    else:
        logger.info("Session verified: Logged in and active.")
        save_session_cookies(page.context)
        return True
