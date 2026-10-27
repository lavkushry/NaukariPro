"""
naukariPro Autonomous LinkedIn Recruiter Outreach & Connection Bot
Target: 5 Recruiter Calls Per Day for ₹25 LPA Azure Data Engineer Opportunities.

Provides:
- LinkedInOutreachSender: High-converting, anti-detect LinkedIn connection request engine.
- Direct & Overflow ("More") Connect Button detection & handling.
- Anti-detection typing with humanized keystroke delay.
- <= 300 character strict limit compliance for Connection Notes.
- Automatic duplicate & pending invitation detection (ALREADY_CONNECTED, PENDING).
- Simulation & Dry-run verification mode (dismisses modal safely without sending).
- Strict daily safety throttling (5-8 connections/day) & 8-15s inter-profile jitter.
- Graceful handling of HTTP 429, checkpoints, and authwalls.
- Synchronous and asynchronous execution interfaces.
- Automatic CRM synchronization (outreach_tracker.json & Excel Recruiter_Outreach_Log).
"""

import os
import sys
import re
import json
import time
import random
import inspect
import logging
import asyncio
import urllib.parse
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Tuple

try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None

from naukari_pro.modules.linkedin_session import (
    LinkedInSessionManager,
    LinkedInError,
    LinkedInSessionError,
    LinkedInCookieMissingError,
    LinkedInCookieExpiredError,
    LinkedInCheckpointError,
    LinkedInRateLimitError,
)
from naukari_pro.modules.recruiter_outreach import (
    RecruiterOutreachCRM,
    RecruiterTemplateGenerator,
    TOP_GCC_TARGETS,
    DEFAULT_OUTREACH_JSON,
)

logger = logging.getLogger("naukariPro.LinkedInOutreach")

# ==============================================================================
# SELECTORS CATALOG FOR LINKEDIN PEOPLE & PROFILE ACTIONS
# ==============================================================================

SEARCH_PROFILE_SELECTORS = [
    "div.entity-result__item a.app-aware-link[href*='/in/']",
    "li.reusable-search__result-container a[href*='/in/']",
    "div.search-results-container a[href*='/in/']",
    "div.artdeco-entity-lockup__title a[href*='/in/']",
    "a.app-aware-link[href*='/in/']",
    "a[href*='linkedin.com/in/']",
]

PENDING_SELECTORS = [
    "button:has-text('Pending')",
    "button[aria-label*='Pending']",
    "button[aria-label*='Invitation sent']",
    "button:has-text('Withdraw')",
    "span:has-text('Pending')",
    "button[disabled]:has-text('Pending')",
]

CONNECTED_SELECTORS = [
    "span.dist-value:has-text('1st')",
    "span:has-text('1st degree connection')",
    "span:has-text('• 1st')",
    "button:has-text('Remove Connection')",
    "div.artdeco-dropdown__item:has-text('Remove Connection')",
    "div[role='button']:has-text('Remove Connection')",
]

DIRECT_CONNECT_SELECTORS = [
    "button:has-text('Connect')",
    "button[aria-label*='Invite'][aria-label*='to connect']",
    "button[aria-label^='Connect with']",
    "div.pvs-profile-actions button:has-text('Connect')",
    "div.ph5 button:has-text('Connect')",
    "button[aria-label*='Connect']",
]

MORE_SELECTORS = [
    "button[aria-label='More actions']",
    "div.pvs-profile-actions button:has-text('More')",
    "button:has-text('More')",
    "button.artdeco-dropdown__trigger:has-text('More')",
]

OVERFLOW_CONNECT_SELECTORS = [
    "div[role='button']:has-text('Connect')",
    "div.artdeco-dropdown__item:has-text('Connect')",
    "span:has-text('Connect')",
    "button:has-text('Connect')",
    "div[aria-label*='Invite'][aria-label*='to connect']",
    "div[aria-label*='Connect']",
]

ADD_NOTE_SELECTORS = [
    "button[aria-label='Add a note']",
    "button:has-text('Add a note')",
    "button.artdeco-button--secondary:has-text('Add a note')",
]

TEXTAREA_SELECTORS = [
    "textarea[name='message']",
    "textarea#custom-message",
    "textarea[id*='custom-message']",
    "div[role='dialog'] textarea",
    "textarea",
]

DISMISS_SELECTORS = [
    "button[aria-label='Dismiss']",
    "button[aria-label='Cancel']",
    "button:has-text('Cancel')",
    "button.artdeco-modal__dismiss",
]

SEND_SELECTORS = [
    "button[aria-label='Send invitation']",
    "button[aria-label='Send now']",
    "button.artdeco-button--primary:has-text('Send')",
    "button:has-text('Send')",
]


# ==============================================================================
# SAFE ASYNC DOM HELPERS
# ==============================================================================

async def safe_count(loc: Any) -> int:
    """Safely retrieves locator count or 0."""
    if loc is None:
        return 0
    try:
        res = loc.count()
        return await res if inspect.isawaitable(res) else res
    except Exception:
        return 0


async def safe_inner_text(loc: Any) -> str:
    """Safely extracts inner text or empty string."""
    if loc is None:
        return ""
    try:
        res = loc.inner_text()
        text = await res if inspect.isawaitable(res) else res
        return (text or "").strip()
    except Exception:
        return ""


async def safe_is_visible(loc: Any) -> bool:
    """Safely checks if locator is visible."""
    if loc is None:
        return False
    try:
        res = loc.is_visible()
        return await res if inspect.isawaitable(res) else res
    except Exception:
        return False


async def humanized_delay(min_ms: int = 500, max_ms: int = 1200, page: Optional[Any] = None):
    """Introduces human-like delay with optional page wait."""
    delay = random.uniform(min_ms / 1000.0, max_ms / 1000.0)
    if page and hasattr(page, "wait_for_timeout"):
        try:
            res = page.wait_for_timeout(int(delay * 1000))
            if inspect.isawaitable(res):
                await res
                return
        except Exception:
            pass
    await asyncio.sleep(delay)


# ==============================================================================
# MAIN OUTREACH SENDER CLASS
# ==============================================================================

class LinkedInOutreachSender:
    """
    Autonomous LinkedIn Connection Bot using Playwright Stealth.
    Sends high-converting, personalized <= 300 character notes to GCC recruiters
    with rate limiting, human typing, and duplicate connection guards.
    """

    MAX_SAFE_DAILY_LIMIT = 8
    DEFAULT_DAILY_LIMIT = 5

    def __init__(
        self,
        session_manager: Optional[LinkedInSessionManager] = None,
        crm: Optional[RecruiterOutreachCRM] = None,
        generator: Optional[RecruiterTemplateGenerator] = None,
        max_daily_limit: int = MAX_SAFE_DAILY_LIMIT,
        headless: bool = True
    ):
        self.session_manager = session_manager or LinkedInSessionManager()
        self.crm = crm or RecruiterOutreachCRM()
        self.generator = generator or RecruiterTemplateGenerator()
        self.max_daily_limit = min(max_daily_limit, self.MAX_SAFE_DAILY_LIMIT)
        self.headless = headless
        self.sent_today_count = 0

    def _get_today_outreaches_count(self) -> int:
        """Counts real (non-dry-run) LinkedIn connection requests sent today."""
        today_str = datetime.now().strftime("%Y-%m-%d")
        crm_count = sum(
            1 for l in self.crm.leads
            if str(l.get("date", "")).startswith(today_str)
            and l.get("platform") == "LinkedIn"
            and l.get("status") in ["CONTACTED", "CONNECTED", "PITCH_SENT"]
            and "[DRY RUN]" not in str(l.get("notes", ""))
        )
        return crm_count + self.sent_today_count

    async def _check_page_health(self, page: Any, recruiter_name: str, company: str, dry_run: bool) -> Optional[Dict[str, Any]]:
        """
        Inspects page for HTTP 429 rate limits, checkpoints, or authwalls.
        Returns a diagnostic result dict if an issue is detected, else None.
        """
        current_url = getattr(page, "url", "") or ""
        content_str = ""
        try:
            c_res = page.content()
            content_str = await c_res if inspect.isawaitable(c_res) else c_res
        except Exception:
            pass
        content_lower = (content_str or "").lower()

        # 1. HTTP 429 Rate Limit
        if (
            "too many requests" in content_lower
            or "http 429" in content_lower
            or "status 429" in content_lower
            or "429 too many" in content_lower
        ):
            logger.warning("LinkedIn HTTP 429 Rate Limit detected for %s at %s", recruiter_name, company)
            return {
                "status": "RATE_LIMITED",
                "recruiter_name": recruiter_name,
                "company": company,
                "sent": False,
                "dry_run": dry_run,
                "detail": "LinkedIn returned HTTP 429 (Too Many Requests / IP rate limit)."
            }

        # 2. Checkpoint / Verification challenge
        if "/checkpoint" in current_url or "checkpoint-challenge" in content_lower or "security verification" in content_lower:
            logger.warning("LinkedIn security checkpoint detected at %s", current_url)
            return {
                "status": "CHECKPOINT",
                "recruiter_name": recruiter_name,
                "company": company,
                "sent": False,
                "dry_run": dry_run,
                "detail": f"LinkedIn security challenge / CAPTCHA detected (URL: {current_url})."
            }

        # 3. Authwall / Log-in wall
        if "/authwall" in current_url or "/login" in current_url or "join linkedin" in content_lower:
            logger.warning("LinkedIn authwall redirect detected at %s", current_url)
            return {
                "status": "AUTH_WALL",
                "recruiter_name": recruiter_name,
                "company": company,
                "sent": False,
                "dry_run": dry_run,
                "detail": f"LinkedIn authwall redirect detected (URL: {current_url})."
            }

        return None

    async def _send_outreach_on_page(
        self,
        page: Any,
        recruiter_name: str,
        company: str,
        profile_url: Optional[str] = None,
        note: Optional[str] = None,
        dry_run: bool = True,
        max_daily_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Internal executor for outreach actions on an active Playwright page.
        """
        effective_limit = max_daily_limit if max_daily_limit is not None else self.max_daily_limit

        # 1. Check daily safety throttling
        today_total = self._get_today_outreaches_count()
        if (not dry_run and today_total >= effective_limit) or (effective_limit <= 0):
            logger.warning("Daily connection limit (%d) reached for today.", effective_limit)
            return {
                "status": "DAILY_LIMIT_REACHED",
                "recruiter_name": recruiter_name,
                "company": company,
                "sent": False,
                "dry_run": dry_run,
                "detail": f"Safety throttle: Maximum daily limit ({effective_limit}) reached ({today_total} sent today)."
            }

        # 2. Navigate to profile or search
        target_profile_url = profile_url
        if target_profile_url and target_profile_url.strip():
            goto_res = page.goto(target_profile_url, wait_until="domcontentloaded")
            if inspect.isawaitable(goto_res):
                await goto_res
            await humanized_delay(400, 800, page=page)
        else:
            search_kw = f"{recruiter_name} {company}"
            search_url = f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote_plus(search_kw)}"
            goto_res = page.goto(search_url, wait_until="domcontentloaded")
            if inspect.isawaitable(goto_res):
                await goto_res
            await humanized_delay(500, 900, page=page)

            # Health check on search results
            health_err = await self._check_page_health(page, recruiter_name, company, dry_run)
            if health_err:
                return health_err

            # Find profile link in search results
            found_profile = False
            for sel in SEARCH_PROFILE_SELECTORS:
                loc = page.locator(sel)
                cnt = await safe_count(loc)
                if cnt > 0:
                    target = loc.first if hasattr(loc, "first") else loc
                    href_res = target.get_attribute("href")
                    href = await href_res if inspect.isawaitable(href_res) else href_res
                    if href:
                        clean_href = href.split("?")[0]
                        target_profile_url = clean_href
                        p_goto = page.goto(clean_href, wait_until="domcontentloaded")
                        if inspect.isawaitable(p_goto):
                            await p_goto
                        await humanized_delay(400, 800, page=page)
                        found_profile = True
                        break

            if not found_profile:
                curr_url = getattr(page, "url", "") or ""
                if "/in/" not in curr_url:
                    return {
                        "status": "NOT_FOUND",
                        "recruiter_name": recruiter_name,
                        "company": company,
                        "sent": False,
                        "dry_run": dry_run,
                        "detail": f"Could not locate LinkedIn profile for '{recruiter_name}' at '{company}'."
                    }

        # 3. Post-navigation health check
        health_err = await self._check_page_health(page, recruiter_name, company, dry_run)
        if health_err:
            return health_err

        # 4. Check if already Pending
        for p_sel in PENDING_SELECTORS:
            loc = page.locator(p_sel)
            if await safe_is_visible(loc.first if hasattr(loc, "first") else loc):
                entry = self.crm.log_outreach(
                    recruiter_name=recruiter_name,
                    company=company,
                    target_role="Azure Data Engineer",
                    platform="LinkedIn",
                    message_type="Connection Request Note",
                    status="CONTACTED",
                    notes="Invitation already pending on LinkedIn"
                )
                return {
                    "status": "PENDING",
                    "recruiter_name": recruiter_name,
                    "company": company,
                    "profile_url": target_profile_url,
                    "sent": False,
                    "dry_run": dry_run,
                    "lead": entry,
                    "detail": f"Connection invitation to {recruiter_name} ({company}) is already pending."
                }

        # 5. Check if already Connected (1st degree)
        for c_sel in CONNECTED_SELECTORS:
            loc = page.locator(c_sel)
            if await safe_is_visible(loc.first if hasattr(loc, "first") else loc):
                entry = self.crm.log_outreach(
                    recruiter_name=recruiter_name,
                    company=company,
                    target_role="Azure Data Engineer",
                    platform="LinkedIn",
                    message_type="Connection Request Note",
                    status="CONNECTED",
                    notes="Already 1st-degree connection on LinkedIn"
                )
                return {
                    "status": "ALREADY_CONNECTED",
                    "recruiter_name": recruiter_name,
                    "company": company,
                    "profile_url": target_profile_url,
                    "sent": False,
                    "dry_run": dry_run,
                    "lead": entry,
                    "detail": f"Already connected with {recruiter_name} ({company}) as 1st-degree connection."
                }

        # 6. Click Connect button (Direct vs More Dropdown)
        clicked_connect = False
        for d_sel in DIRECT_CONNECT_SELECTORS:
            loc = page.locator(d_sel)
            cnt = await safe_count(loc)
            if cnt > 0:
                for idx in range(cnt):
                    target = loc.nth(idx) if cnt > 1 else loc
                    if await safe_is_visible(target):
                        c_res = target.click()
                        if inspect.isawaitable(c_res):
                            await c_res
                        clicked_connect = True
                        break
                if clicked_connect:
                    break

        if not clicked_connect:
            # Check More overflow menu
            more_btn = None
            for m_sel in MORE_SELECTORS:
                loc = page.locator(m_sel)
                if await safe_is_visible(loc.first if hasattr(loc, "first") else loc):
                    more_btn = loc.first if hasattr(loc, "first") else loc
                    break

            if more_btn:
                m_res = more_btn.click()
                if inspect.isawaitable(m_res):
                    await m_res
                await humanized_delay(200, 400, page=page)

                for o_sel in OVERFLOW_CONNECT_SELECTORS:
                    loc = page.locator(o_sel)
                    if await safe_is_visible(loc.first if hasattr(loc, "first") else loc):
                        btn = loc.first if hasattr(loc, "first") else loc
                        c_res = btn.click()
                        if inspect.isawaitable(c_res):
                            await c_res
                        clicked_connect = True
                        break

        if not clicked_connect:
            return {
                "status": "CONNECT_UNAVAILABLE",
                "recruiter_name": recruiter_name,
                "company": company,
                "profile_url": target_profile_url,
                "sent": False,
                "dry_run": dry_run,
                "detail": "Connect button could not be found in direct profile actions or More dropdown."
            }

        # 7. Add a Note Modal Handling
        await humanized_delay(300, 600, page=page)
        for an_sel in ADD_NOTE_SELECTORS:
            loc = page.locator(an_sel)
            if await safe_is_visible(loc.first if hasattr(loc, "first") else loc):
                btn = loc.first if hasattr(loc, "first") else loc
                an_res = btn.click()
                if inspect.isawaitable(an_res):
                    await an_res
                await humanized_delay(200, 400, page=page)
                break

        # 8. Note Composition & Strict Character Limit (<= 300)
        personalized_note = note or self.generator.generate_connection_note(recruiter_name, company)
        if len(personalized_note) > 300:
            personalized_note = personalized_note[:300]

        # 9. Type Note with Humanized Keystrokes
        typed = False
        for t_sel in TEXTAREA_SELECTORS:
            loc = page.locator(t_sel)
            if await safe_is_visible(loc.first if hasattr(loc, "first") else loc):
                ta = loc.first if hasattr(loc, "first") else loc
                f_res = ta.focus()
                if inspect.isawaitable(f_res):
                    await f_res
                clr_res = ta.fill("")
                if inspect.isawaitable(clr_res):
                    await clr_res
                # Humanized typing delay per character
                if hasattr(ta, "press_sequentially"):
                    typ_res = ta.press_sequentially(personalized_note, delay=random.randint(25, 45))
                elif hasattr(ta, "type"):
                    typ_res = ta.type(personalized_note, delay=random.randint(25, 45))
                else:
                    typ_res = ta.fill(personalized_note)
                if inspect.isawaitable(typ_res):
                    await typ_res
                typed = True
                break

        # 10. Dry-Run Dismiss vs Live Send
        if dry_run:
            # Dismiss modal without sending
            for dis_sel in DISMISS_SELECTORS:
                loc = page.locator(dis_sel)
                if await safe_is_visible(loc.first if hasattr(loc, "first") else loc):
                    btn = loc.first if hasattr(loc, "first") else loc
                    d_res = btn.click()
                    if inspect.isawaitable(d_res):
                        await d_res
                    break

            entry = self.crm.log_outreach(
                recruiter_name=recruiter_name,
                company=company,
                target_role="Azure Data Engineer",
                platform="LinkedIn",
                message_type="Connection Request Note",
                status="CONTACTED",
                notes=f"[DRY RUN] Simulated connection request note ({len(personalized_note)}/300 chars)",
                message_content=personalized_note
            )
            return {
                "status": "DRY_RUN_VERIFIED",
                "recruiter_name": recruiter_name,
                "company": company,
                "profile_url": target_profile_url,
                "note": personalized_note,
                "note_length": len(personalized_note),
                "sent": False,
                "dry_run": True,
                "lead": entry,
                "detail": f"Dry-run verified: Note populated ({len(personalized_note)}/300 chars) and modal dismissed safely."
            }

        # Live Mode: Click Send
        sent_clicked = False
        for s_sel in SEND_SELECTORS:
            loc = page.locator(s_sel)
            if await safe_is_visible(loc.first if hasattr(loc, "first") else loc):
                btn = loc.first if hasattr(loc, "first") else loc
                s_res = btn.click()
                if inspect.isawaitable(s_res):
                    await s_res
                sent_clicked = True
                break

        if not sent_clicked:
            return {
                "status": "ERROR",
                "recruiter_name": recruiter_name,
                "company": company,
                "profile_url": target_profile_url,
                "sent": False,
                "dry_run": False,
                "detail": "Could not locate Send button in invitation modal."
            }

        self.sent_today_count += 1
        entry = self.crm.log_outreach(
            recruiter_name=recruiter_name,
            company=company,
            target_role="Azure Data Engineer",
            platform="LinkedIn",
            message_type="Connection Request Note",
            status="CONTACTED",
            notes="Live connection request invitation sent via Playwright Stealth Bot",
            message_content=personalized_note
        )

        return {
            "status": "SENT",
            "recruiter_name": recruiter_name,
            "company": company,
            "profile_url": target_profile_url,
            "note": personalized_note,
            "note_length": len(personalized_note),
            "sent": True,
            "dry_run": False,
            "lead": entry,
            "detail": "Live connection invitation successfully dispatched with personalized note."
        }

    async def send_outreach(
        self,
        recruiter_name: str,
        company: str,
        profile_url: Optional[str] = None,
        note: Optional[str] = None,
        dry_run: bool = True,
        max_daily_limit: Optional[int] = None,
        page: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Public outreach method. Uses provided page or initializes stealth Playwright context.
        """
        effective_limit = max_daily_limit if max_daily_limit is not None else self.max_daily_limit

        # If page provided (e.g. from batch or mock), execute directly
        if page is not None:
            return await self._send_outreach_on_page(
                page=page,
                recruiter_name=recruiter_name,
                company=company,
                profile_url=profile_url,
                note=note,
                dry_run=dry_run,
                max_daily_limit=effective_limit
            )

        if async_playwright is None:
            raise RuntimeError("Playwright is not installed or available.")

        # Check safety throttle before browser launch
        if not dry_run and self._get_today_outreaches_count() >= effective_limit:
            return {
                "status": "DAILY_LIMIT_REACHED",
                "recruiter_name": recruiter_name,
                "company": company,
                "sent": False,
                "dry_run": dry_run,
                "detail": f"Safety throttle: Daily limit of {effective_limit} connection requests already reached today."
            }

        async with async_playwright() as p:
            context = await self.session_manager.create_stealth_context(p, headless=self.headless)
            try:
                pg = context.pages[0] if (hasattr(context, "pages") and context.pages) else await context.new_page()
                diag = await self.session_manager.verify_session(pg, raise_for_status=False)
                if diag.get("status") != "VALID":
                    return {
                        "status": diag.get("status", "FAILED"),
                        "recruiter_name": recruiter_name,
                        "company": company,
                        "sent": False,
                        "dry_run": dry_run,
                        "detail": diag.get("detail", "LinkedIn session verification failed.")
                    }

                return await self._send_outreach_on_page(
                    page=pg,
                    recruiter_name=recruiter_name,
                    company=company,
                    profile_url=profile_url,
                    note=note,
                    dry_run=dry_run,
                    max_daily_limit=effective_limit
                )
            finally:
                if hasattr(context, "close"):
                    c_res = context.close()
                    if inspect.isawaitable(c_res):
                        await c_res

    async def send_batch_outreach(
        self,
        leads: Optional[List[Dict[str, Any]]] = None,
        limit: int = 5,
        dry_run: bool = True,
        headless: bool = True,
        custom_note: Optional[str] = None,
        throttle_delay_range: Tuple[float, float] = (8.0, 15.0)
    ) -> Dict[str, Any]:
        """
        Executes autonomous batch connection outreach with anti-detection pacing
        (randomized 8-15s delay between profiles) across active leads or Top GCC targets.
        """
        if async_playwright is None:
            raise RuntimeError("Playwright is not installed or available.")

        capped_limit = min(limit, self.max_daily_limit, self.MAX_SAFE_DAILY_LIMIT)

        # Assemble target leads
        target_leads: List[Dict[str, Any]] = []
        if leads:
            target_leads = leads[:capped_limit]
        else:
            # Prefer active uncontacted leads from CRM
            active = [
                l for l in self.crm.leads
                if l.get("platform") == "LinkedIn" and l.get("status") not in ["CONNECTED", "REJECTED"]
            ]
            if not active:
                active = [
                    {"recruiter_name": t["recruiter"], "company": t["company"], "target_role": t["role"]}
                    for t in TOP_GCC_TARGETS
                ]
            target_leads = active[:capped_limit]

        results = []
        async with async_playwright() as p:
            context = await self.session_manager.create_stealth_context(p, headless=headless)
            try:
                page = context.pages[0] if (hasattr(context, "pages") and context.pages) else await context.new_page()
                diag = await self.session_manager.verify_session(page, raise_for_status=False)
                if diag.get("status") != "VALID":
                    return {
                        "status": diag.get("status", "FAILED"),
                        "detail": diag.get("detail", "LinkedIn session verification failed."),
                        "results": []
                    }

                for idx, lead in enumerate(target_leads):
                    rec = lead.get("recruiter_name") or lead.get("recruiter", "Recruiter")
                    comp = lead.get("company", "Company")
                    prof_url = lead.get("profile_url")
                    n_text = custom_note or lead.get("note")

                    res = await self._send_outreach_on_page(
                        page=page,
                        recruiter_name=rec,
                        company=comp,
                        profile_url=prof_url,
                        note=n_text,
                        dry_run=dry_run,
                        max_daily_limit=self.max_daily_limit
                    )
                    results.append(res)

                    # Halt batch on critical stop signals
                    if res.get("status") in ["RATE_LIMITED", "CHECKPOINT", "AUTH_WALL", "DAILY_LIMIT_REACHED"]:
                        logger.warning("Terminating batch outreach early due to stop condition: %s", res.get("status"))
                        break

                    # Anti-detection jitter between profile views
                    if idx < len(target_leads) - 1:
                        if dry_run:
                            jitter = random.uniform(0.1, 0.4)
                        else:
                            jitter = random.uniform(throttle_delay_range[0], throttle_delay_range[1])
                        logger.info("Humanized safety throttle: waiting %.1fs before next recruiter...", jitter)
                        await asyncio.sleep(jitter)

                return {
                    "status": "COMPLETED",
                    "total_processed": len(results),
                    "sent_count": sum(1 for r in results if r.get("sent")),
                    "dry_run_count": sum(1 for r in results if r.get("status") == "DRY_RUN_VERIFIED"),
                    "results": results
                }
            finally:
                if hasattr(context, "close"):
                    c_res = context.close()
                    if inspect.isawaitable(c_res):
                        await c_res

    # Synchronous helper methods for CLI & scripts
    def run_outreach(
        self,
        recruiter_name: str,
        company: str,
        profile_url: Optional[str] = None,
        note: Optional[str] = None,
        dry_run: bool = True,
        max_daily_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Synchronous wrapper for single recruiter outreach."""
        return asyncio.run(
            self.send_outreach(
                recruiter_name=recruiter_name,
                company=company,
                profile_url=profile_url,
                note=note,
                dry_run=dry_run,
                max_daily_limit=max_daily_limit
            )
        )

    def run_batch(
        self,
        leads: Optional[List[Dict[str, Any]]] = None,
        limit: int = 5,
        dry_run: bool = True,
        headless: bool = True,
        custom_note: Optional[str] = None
    ) -> Dict[str, Any]:
        """Synchronous wrapper for batch recruiter outreach."""
        return asyncio.run(
            self.send_batch_outreach(
                leads=leads,
                limit=limit,
                dry_run=dry_run,
                headless=headless,
                custom_note=custom_note
            )
        )
