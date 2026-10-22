"""
naukariPro Browser Session & Anti-Bot Evasion Module
Provides persistent Chrome context, stealth JS injection, and cookie synchronization.
Supports macOS, Linux (ARM64/x86_64), and Headless Cloud Execution.
"""

import os
import sys
import time
import json
import logging
import platform
from naukari_pro.config import SESSION_DIR, COOKIES_SEED_PATH

logger = logging.getLogger("naukariPro.Session")

STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
window.navigator.chrome = { runtime: {} };
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en', 'hi'] });
"""

def get_stealth_context(playwright, headless=False):
    """
    Launches an anti-detect persistent Google Chrome/Chromium context.
    Works natively across macOS and Linux with zero configuration.
    Bypasses Akamai Bot Protection and maintains long-lived authenticated state.
    """
    os.makedirs(SESSION_DIR, exist_ok=True)

    # Clean up any stale Chrome lock files to prevent SingletonLock collisions
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

    is_linux = platform.system().lower() == "linux"
    channel = None if is_linux else "chrome"

    kwargs = {
        "user_data_dir": SESSION_DIR,
        "headless": headless,
        "args": launch_args,
        "viewport": None,
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    }
    if channel:
        kwargs["channel"] = channel

    try:
        context = playwright.chromium.launch_persistent_context(**kwargs)
    except Exception as e:
        logger.warning("Primary browser launch fallback (%s). Retrying with default bundled Chromium...", e)
        kwargs.pop("channel", None)
        context = playwright.chromium.launch_persistent_context(**kwargs)

    context.add_init_script(STEALTH_JS)

    # Inject latest session cookies if available
    if os.path.exists(COOKIES_SEED_PATH):
        try:
            with open(COOKIES_SEED_PATH, "r") as f:
                seed_cookies = json.load(f)
            context.add_cookies(seed_cookies)
            logger.info("Synchronized %d session authentication tokens.", len(seed_cookies))
        except Exception as e:
            logger.warning("Could not load seed cookies: %s", e)

    return context

def ensure_authenticated(page):
    """
    Verifies that the session is logged into Naukri.
    If not logged in, pauses and prompts the user to log in once in the opened window.
    """
    logger.info("Validating Naukri authentication state...")
    try:
        page.goto("https://www.naukri.com/mnjuser/profile", wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)
    except Exception as e:
        logger.warning("Navigation notice: %s", e)

    if "login" in page.url or page.locator("text=Login").first.is_visible() or "Access Denied" in page.title():
        logger.warning("=" * 70)
        logger.warning("ACTION REQUIRED: Complete 1-time login in the opened Chrome browser window.")
        logger.warning("Waiting for successful login (up to 3 minutes)...")
        logger.warning("=" * 70)
        try:
            page.wait_for_url("**/profile**", timeout=180000)
            logger.info("Login confirmed! Session permanently saved at %s", SESSION_DIR)
            return True
        except Exception:
            logger.error("Authentication timeout. Please run 'naukariPro auth' to log in.")
            return False
    else:
        logger.info("Session verified: Logged in and active.")
        return True
