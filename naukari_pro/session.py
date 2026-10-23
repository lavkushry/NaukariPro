"""
naukariPro Browser Session & Anti-Bot Evasion Module
Provides persistent Chrome/Chromium context, stealth JS injection, and cookie synchronization.
Supports macOS, Linux (ARM64/x86_64), and Headless Cloud Execution.
Handles OTP and Captcha challenge detection gracefully.
"""

import os
import sys
import time
import json
import logging
import platform
import shutil
from naukari_pro.config import SESSION_DIR, COOKIES_SEED_PATH, WORKSPACE_DIR, load_config

logger = logging.getLogger("naukariPro.Session")

STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
window.navigator.chrome = { runtime: {} };
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en', 'hi'] });
"""

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

def get_stealth_context(playwright, headless=False):
    """
    Launches an anti-detect persistent Google Chrome/Chromium context.
    Works natively across macOS and Linux with zero configuration.
    Bypasses Akamai Bot Protection and maintains long-lived authenticated state.
    Seamlessly falls back to bundled Chromium if Google Chrome is not installed.
    """
    os.makedirs(SESSION_DIR, exist_ok=True)

    # Clean up stale lock files
    for lock_file in ["SingletonLock", "SingletonSocket", "SingletonCookie"]:
        lock_path = os.path.join(SESSION_DIR, lock_file)
        if os.path.exists(lock_path) or os.path.islink(lock_path):
            try:
                os.unlink(lock_path)
            except Exception:
                pass

    launch_args = [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
    ]
    if not headless:
        launch_args.append("--start-maximized")

    # On macOS or Linux, determine if Google Chrome or system Chromium binary is present
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

    try:
        context = playwright.chromium.launch_persistent_context(**kwargs)
    except Exception as e:
        logger.warning("Primary browser launch fallback (%s). Retrying with default bundled Chromium...", e)
        kwargs.pop("channel", None)
        kwargs.pop("executable_path", None)
        context = playwright.chromium.launch_persistent_context(**kwargs)

    context.add_init_script(STEALTH_JS)

    # Inject latest session cookies if available
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
