"""
Profile Performance & Account Entitlements Engine
Inspects authentic Naukri server-side entitlements and profile analytics:
- JWT Session Entitlement Inspector (ud_isPaidClient, auth state, user ID)
- Profile Performance Analytics (Search Appearances, Recruiter Actions, Downloads, Views)
- Top Recruiter Search Keywords (Real keywords recruiters used in Resdex)
- Paid Services Entitlement Verifier (Featured Profile, Priority Applicant, Pro Status)
"""

import os
import json
import base64
import time
import logging
from naukari_pro.config import COOKIES_SEED_PATH, load_config

logger = logging.getLogger("naukariPro.Performance")

def decode_naukri_jwt(token_str):
    """Decodes JWT payload without external crypto dependencies."""
    try:
        parts = token_str.split(".")
        if len(parts) >= 2:
            payload_b64 = parts[1]
            # Add padding if needed
            padding = len(payload_b64) % 4
            if padding:
                payload_b64 += "=" * (4 - padding)
            decoded_bytes = base64.urlsafe_b64decode(payload_b64)
            return json.loads(decoded_bytes.decode("utf-8"))
    except Exception as e:
        logger.debug("JWT decode notice: %s", e)
    return {}

class ProfilePerformanceEngine:
    def __init__(self):
        self.cfg = load_config()

    def get_session_entitlements(self, cookies=None):
        """
        Inspects session tokens to determine real server-side account entitlements.
        Naukri stores authentic subscription flags on its server and in the signed 'nauk_at' JWT.
        """
        token = None
        if cookies:
            for c in cookies:
                if c.get("name") == "nauk_at":
                    token = c.get("value")
                    break

        if not token and os.path.exists(COOKIES_SEED_PATH):
            try:
                with open(COOKIES_SEED_PATH, "r") as f:
                    seed = json.load(f)
                for c in seed:
                    if c.get("name") == "nauk_at":
                        token = c.get("value")
                        break
            except Exception:
                pass

        if not token:
            return {
                "authenticated": False,
                "is_paid_client": False,
                "user_id": None,
                "tier": "Unknown / Unauthenticated",
                "details": "No 'nauk_at' session token found in cookies."
            }

        payload = decode_naukri_jwt(token)
        is_paid = bool(payload.get("ud_isPaidClient", False))
        user_id = payload.get("userId") or payload.get("sub")
        email = payload.get("ud_username") or payload.get("ud_email")
        state = payload.get("userState", "UNKNOWN")

        return {
            "authenticated": state == "AUTHENTICATED",
            "is_paid_client": is_paid,
            "user_id": user_id,
            "email": email,
            "user_state": state,
            "tier": "Naukri Paid / Pro Account" if is_paid else "Standard Free Account",
            "server_entitlements": {
                "featured_flag_resdex": is_paid,
                "priority_applicant_flag": is_paid,
                "pro_ai_entitlements": is_paid,
            },
            "raw_claims": {
                "deviceType": payload.get("deviceType"),
                "sessionStatTime": payload.get("sessionStatTime"),
                "exp": payload.get("exp")
            }
        }

    def fetch_live_performance(self, page):
        """
        Navigates to Naukri Profile Performance (/mnjuser/profile-performance)
        and extracts real recruiter view, download, search appearance, and keyword metrics.
        """
        logger.info("Accessing live Naukri Profile Performance...")
        metrics = {
            "search_appearances": None,
            "recruiter_actions": None,
            "profile_views": None,
            "resume_downloads": None,
            "top_search_keywords": [],
            "recent_recruiters": [],
            "data_source": "Live Naukri Portal"
        }

        try:
            page.goto("https://www.naukri.com/mnjuser/profile-performance", wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)

            # Check if redirected to login
            if "login" in page.url:
                logger.warning("Session expired; redirected to login page.")
                metrics["data_source"] = "Session Expired (Login Required)"
                return metrics

            # Scrape performance cards
            body_text = page.locator("body").inner_text()

            # Search appearances (e.g., "120 Search appearances in last 90 days")
            app_el = page.locator(".search-appearances, .perf-count, span[class*='searchAppCount'], div[class*='searchApp']").first
            if app_el.count() > 0 and app_el.is_visible():
                metrics["search_appearances"] = app_el.inner_text().strip()

            # Recruiter actions / views
            rec_el = page.locator(".recruiter-actions, span[class*='recruiterAction'], div[class*='recAction']").first
            if rec_el.count() > 0 and rec_el.is_visible():
                metrics["recruiter_actions"] = rec_el.inner_text().strip()

            view_el = page.locator(".profile-views, span[class*='profileViews'], div[class*='profView']").first
            if view_el.count() > 0 and view_el.is_visible():
                metrics["profile_views"] = view_el.inner_text().strip()

            # Top keywords searched by recruiters
            kw_els = page.locator(".keyword-chip, .keyword-pill, div[class*='keywordTag'], span[class*='keyword']").all()
            for kw in kw_els[:10]:
                t = kw.inner_text().strip()
                if t and t not in metrics["top_search_keywords"]:
                    metrics["top_search_keywords"].append(t)

            # Fallback parsing from text blocks if specific classes vary
            lines = [l.strip() for l in body_text.split("\n") if l.strip()]
            for i, line in enumerate(lines):
                l_lower = line.lower()
                if "search appearance" in l_lower and i > 0 and not metrics["search_appearances"]:
                    if lines[i-1].isdigit():
                        metrics["search_appearances"] = lines[i-1]
                if "recruiter action" in l_lower and i > 0 and not metrics["recruiter_actions"]:
                    if lines[i-1].isdigit():
                        metrics["recruiter_actions"] = lines[i-1]

        except Exception as e:
            logger.warning("Profile performance query notice: %s", e)
            metrics["data_source"] = f"Extraction Notice: {str(e)}"

        return metrics

    def display_report(self, page=None):
        """Displays clear, honest breakdown of account status and performance metrics."""
        cookies = page.context.cookies() if page else None
        entitlements = self.get_session_entitlements(cookies=cookies)

        print("\n" + "=" * 70)
        print("  📊 NAUKARIPRO: SERVER-SIDE ENTITLEMENTS & PROFILE PERFORMANCE")
        print("=" * 70)
        print(f"  Candidate: {self.cfg['candidate']['name']} ({self.cfg['candidate']['email']})")
        print(f"  Account State: {entitlements['user_state']}")
        print(f"  User ID: {entitlements['user_id']}")
        print(f"  Server Subscription Tier: {entitlements['tier']}")
        print("-" * 70)
        print("  [SERVER ENTITLEMENT AUDIT]")
        is_paid = entitlements['is_paid_client']
        print(f"  • Featured Profile (Resdex Weekly Refresh): {'ACTIVE (Server-Side)' if is_paid else 'INACTIVE (Requires Paid Subscription)'}")
        print(f"  • Priority Applicant Tag on Applications:   {'ACTIVE (Server-Side)' if is_paid else 'STANDARD (Free Tier Submission)'}")
        print(f"  • Naukri Pro AI Tools Entitlement:         {'ACTIVE (Server-Side)' if is_paid else 'INACTIVE (Off-Market Local Suite Active)'}")
        print("-" * 70)

        if not is_paid:
            print("  ℹ️ NOTICE ON NAUKRI PRO / PAID SERVICES:")
            print("    Naukri's backend strictly enforces 'ud_isPaidClient=false' for this session.")
            print("    Client automation cannot inject server-side paid flags (Featured/Priority).")
            print("    However, NaukariPro maximizes your free account performance through:")
            print("      1. Daily Recency Bumping (maintains 'Last updated today' timestamp)")
            print("      2. Strict 1-Page ATS Resume Generation & Keyword Tailoring")
            print("      3. Sub-6-hour Fast Vacancy Response & Direct 1-Click Apply")
            print("-" * 70)

        if page:
            perf = self.fetch_live_performance(page)
            print("  [LIVE PROFILE PERFORMANCE METRICS]")
            print(f"  • Search Appearances (90 Days): {perf['search_appearances'] or 'Not Disclosed by Portal'}")
            print(f"  • Recruiter Actions / Views:    {perf['recruiter_actions'] or 'Not Disclosed by Portal'}")
            print(f"  • Profile Views:                {perf['profile_views'] or 'Not Disclosed by Portal'}")
            if perf['top_search_keywords']:
                print(f"  • Keywords Found By:            {', '.join(perf['top_search_keywords'])}")
            print(f"  • Data Source:                  {perf['data_source']}")
        else:
            print("  [LIVE PROFILE PERFORMANCE METRICS]")
            print("  • Search Appearances:           Connect live browser session to query")
            print("  • Recruiter Actions:            Connect live browser session to query")
            print("  • Tip: Run './naukariPro performance' with active login to inspect.")
        print("=" * 70 + "\n")
        return entitlements
