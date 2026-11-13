#!/usr/bin/env python3
"""Capture Workday page state for submit debugging."""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

URL = (
    "https://fractal.wd1.myworkdayjobs.com/en-US/Careers/job/Bengaluru/"
    "Senior-AWS-DevOps---Platform-Engineer--6-9-Years-_SR-47601"
)


def main() -> int:
    from playwright.sync_api import sync_playwright
    from naukari_pro.session import get_stealth_context
    from naukari_pro.modules.career_portals import WorkdayHandler, PORTALS_SESSION_DIR
    from naukari_pro.modules.candidate_profile import load_hybrid_profile

    out = ROOT / "logs" / "workday_fractal_diagnose.png"
    with sync_playwright() as p:
        ctx = get_stealth_context(p, headless=True, session_dir=PORTALS_SESSION_DIR, lock_timeout=60)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=45000)
        time.sleep(3)
        handler = WorkdayHandler(load_hybrid_profile())
        print("overlay_before", handler._workday_overlay_present(page))
        print("signin_ready_before", handler._workday_sign_in_ready(page))
        dismissed = handler.dismiss_workday_overlays(page, max_rounds=4)
        print("overlay_dismissed", dismissed)
        print("overlay_after", handler._workday_overlay_present(page))
        print("signin_ready_after_cookie", handler._workday_sign_in_ready(page))
        handler.open_apply_modal_if_needed(page)
        time.sleep(2)
        # Re-hit apply URL after cookies (Workday sometimes drops to homepage)
        if "/login" not in (page.url or "") and "/apply" not in (page.url or ""):
            page.goto(URL + "/apply/applyManually", wait_until="domcontentloaded", timeout=45000)
            time.sleep(2)
            handler.dismiss_workday_overlays(page, max_rounds=4)
        print("signin_ready_pre_vault", handler.wait_for_workday_sign_in_fields(page, timeout_sec=8))
        signed = handler.attempt_vault_sign_in(page, job_url=URL)
        print("vault_signed", signed)
        print("signin_ready_post_vault", handler._workday_sign_in_ready(page))
        print("overlay_post_vault", handler._workday_overlay_present(page))
        time.sleep(2)
        handler.fill_form(page)
        time.sleep(2)
        # Dump automation ids / buttons
        info = page.evaluate(
            """() => {
              const buttons = [...document.querySelectorAll('button, a, div[data-automation-id]')].slice(0, 80)
                .map(el => ({
                  tag: el.tagName,
                  text: (el.innerText||'').trim().slice(0,60),
                  auto: el.getAttribute('data-automation-id'),
                  aria: el.getAttribute('aria-label'),
                  visible: !!(el.offsetWidth || el.offsetHeight)
                }))
                .filter(x => x.visible && (x.text || x.auto));
              return {url: location.href, title: document.title, buttons};
            }"""
        )
        page.screenshot(path=str(out), full_page=True)
        print("url", info.get("url"))
        print("title", info.get("title"))
        for b in info.get("buttons") or []:
            print(f"  [{b.get('tag')}] auto={b.get('auto')} aria={b.get('aria')} text={b.get('text')!r}")
        print("screenshot", out)
        try:
            ctx.close()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
