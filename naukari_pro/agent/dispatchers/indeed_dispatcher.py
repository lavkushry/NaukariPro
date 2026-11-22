"""
Indeed apply bridge.

Indeed public RSS is deprecated (404) and HTML search is often 403.
When a concrete Indeed job URL is provided, open it and:
1) follow "Apply on company site" / external redirects into CareerPortalFiller, or
2) queue CAPTCHA / auth blockers via M5 AttentionQueue (never silent bypass).
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from naukari_pro.agent.dispatchers.base import BasePlatformDispatcher, PlatformExecutionReport
from naukari_pro.modules.career_portals import CareerPortalFiller, FillResult
from naukari_pro.modules.db import DB_PATH, is_job_already_applied
from naukari_pro.governed_apply.attention import AttentionQueue, BlockerClass, detect_blocker
from naukari_pro.modules.autonomous_loop import ATTENTION_PATH

logger = logging.getLogger("naukariPro.Agent.Dispatchers.Indeed")


class IndeedDispatcher(BasePlatformDispatcher):
    """Bridge Indeed job pages → external ATS apply (or attention queue)."""

    platform_name = "indeed"

    def __init__(
        self,
        filler: Optional[CareerPortalFiller] = None,
        *,
        headless: bool = True,
        db_path: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ):
        super().__init__(timeout_seconds=timeout_seconds)
        self.filler = filler or CareerPortalFiller()
        self.headless = headless
        self.db_path = db_path or DB_PATH
        self.attention = AttentionQueue()

    def _persist_attention(self) -> None:
        import json
        from pathlib import Path

        path = Path(ATTENTION_PATH)
        existing: List[Dict[str, Any]] = []
        if path.exists():
            try:
                existing = json.loads(path.read_text(encoding="utf-8") or "[]")
            except Exception:
                existing = []
        seen = {(e.get("blocker"), e.get("job_url")) for e in existing if isinstance(e, dict)}
        for i in self.attention.items:
            key = (i.blocker.value, i.job_url)
            if key in seen:
                continue
            existing.append(
                {
                    "blocker": i.blocker.value,
                    "job_url": i.job_url,
                    "detail": i.detail,
                    "status": i.status,
                }
            )
            seen.add(key)
        path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")

    def _follow_external_apply(self, page: Any) -> Optional[str]:
        """Click company-site apply and return destination URL if off-Indeed."""
        selectors = (
            "a:has-text('Apply on company site')",
            "a:has-text('Apply on company website')",
            "button:has-text('Apply on company site')",
            "a[href*='indeed.com/rc/clk']",
            "a[data-tn-element='jobHeader-companyName']",
            "a:has-text('Apply now')",
            "button:has-text('Apply now')",
        )
        start = getattr(page, "url", "") or ""
        for sel in selectors:
            try:
                loc = page.locator(sel).first
                if loc.count() == 0 or not loc.is_visible():
                    continue
                with page.expect_navigation(timeout=15000, wait_until="domcontentloaded"):
                    loc.click(timeout=5000)
                time.sleep(1.0)
                dest = getattr(page, "url", "") or ""
                if dest and "indeed." not in urlparse(dest).netloc.lower():
                    return dest
                # Popup / same-tab still on indeed — try href
                href = loc.get_attribute("href") or ""
                if href.startswith("http") and "indeed." not in urlparse(href).netloc.lower():
                    page.goto(href, wait_until="domcontentloaded", timeout=30000)
                    return page.url
            except Exception:
                continue
        # Still on Indeed: capture blocker
        try:
            body = (page.inner_text("body") or "")[:4000]
        except Exception:
            body = ""
        blocker = detect_blocker(body, url=start)
        if blocker:
            self.attention.push(blocker, start, f"Indeed page blocker: {blocker.value}")
            self._persist_attention()
        return None

    def apply_job(
        self,
        *,
        job_url: str,
        company: str = "Indeed",
        title: str = "Role",
        dry_run: bool = False,
        match_score: Optional[int] = None,
    ) -> Dict[str, Any]:
        if not job_url or "indeed." not in job_url.lower():
            return {"success": False, "status": "INVALID_INDEED_URL", "url": job_url}
        if not dry_run and is_job_already_applied(
            title=title, company=company, job_url=job_url, db_path=self.db_path
        ):
            return {"success": False, "status": "SKIPPED_ALREADY_APPLIED", "url": job_url}
        if dry_run:
            return {"success": True, "status": "DRY_RUN", "url": job_url}

        from playwright.sync_api import sync_playwright
        from naukari_pro.session import get_stealth_context
        from naukari_pro.modules.career_portals import PORTALS_SESSION_DIR

        external_url = None
        try:
            with sync_playwright() as p:
                context = get_stealth_context(
                    p, headless=self.headless, session_dir=PORTALS_SESSION_DIR, lock_timeout=120.0
                )
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(job_url, wait_until="domcontentloaded", timeout=45000)
                time.sleep(1.5)
                try:
                    body = (page.inner_text("body") or "")[:4000]
                except Exception:
                    body = ""
                blocker = detect_blocker(body, url=job_url)
                if blocker == BlockerClass.CAPTCHA:
                    self.attention.push(blocker, job_url, "Indeed CAPTCHA / bot wall on landing")
                    self._persist_attention()
                    context.close()
                    return {"success": False, "status": "FALLBACK (CAPTCHA)", "url": job_url}

                external_url = self._follow_external_apply(page)
                context.close()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Indeed bridge navigation failed: %s", exc)
            return {"success": False, "status": f"INDEED_NAV_ERROR: {exc}", "url": job_url}

        if not external_url:
            return {
                "success": False,
                "status": "INDEED_NO_EXTERNAL_APPLY",
                "url": job_url,
                "detail": "No company-site apply redirect; attention may be queued",
            }

        res = self.filler.fill(
            portal_url=external_url,
            company=company,
            role=title,
            headless=self.headless,
            dry_run=False,
            match_score=match_score,
            auto_submit=True,
            allow_retry=True,
        )
        if isinstance(res, FillResult):
            return {
                "success": bool(res.success),
                "status": res.status or ("Submitted (Confirmed)" if res.success else "UNKNOWN"),
                "url": external_url,
                "source_indeed_url": job_url,
                "evidence_path": res.evidence_path,
            }
        return {"success": False, "status": str(res), "url": external_url, "source_indeed_url": job_url}

    def _jobs_from_intent(self, intent: Any) -> List[Dict[str, Any]]:
        jobs = list(getattr(intent, "jobs", None) or [])
        if jobs:
            return jobs
        meta = getattr(intent, "metadata", None) or {}
        if isinstance(meta, dict) and meta.get("jobs"):
            return list(meta["jobs"])
        return []

    def dispatch_dry_run(self, intent: Any) -> PlatformExecutionReport:
        report = PlatformExecutionReport(platform_name=self.platform_name, dry_run=True)
        jobs = self._jobs_from_intent(intent)
        if not jobs:
            report.add_error("No Indeed job URLs provided (RSS deprecated; pass explicit jobs).", fatal=True)
            return report
        for job in jobs:
            report.total_evaluated += 1
            report.add_record(
                {
                    "company": job.get("company") or "Indeed",
                    "title": job.get("title") or job.get("role") or "Role",
                    "job_url": job.get("url") or job.get("job_url") or "",
                    "status": "DRY_RUN",
                }
            )
        report.success = True
        return report

    def _execute_live(self, intent: Any) -> PlatformExecutionReport:
        report = PlatformExecutionReport(platform_name=self.platform_name, dry_run=False)
        jobs = self._jobs_from_intent(intent)
        if not jobs:
            report.add_error("No Indeed job URLs provided (RSS deprecated; pass explicit jobs).", fatal=True)
            return report

        for job in jobs:
            url = job.get("url") or job.get("job_url") or ""
            company = job.get("company") or "Indeed"
            title = job.get("title") or job.get("role") or "Role"
            report.total_evaluated += 1
            out = self.apply_job(
                job_url=url,
                company=company,
                title=title,
                dry_run=False,
                match_score=job.get("match_score"),
            )
            status = str(out.get("status") or "")
            rec = {"company": company, "title": title, "job_url": url, "status": status, **out}
            report.add_record(rec)
            if out.get("success") or "Submitted" in status:
                # add_record already counted SUBMITTED; avoid double-count when status differs
                if "SUBMITTED" not in status.upper() and "APPLIED" not in status.upper():
                    report.submitted_count += 1
                    report.applied_jobs.append(rec)
            elif "SKIPPED" in status.upper() or "DUPLICATE" in status.upper():
                pass  # add_record handled
            elif "FAILED" not in status.upper() and "ERROR" not in status.upper():
                report.failed_count += 1

        report.success = report.failed_count == 0 and not report.errors
        return report

    def search_and_apply(
        self,
        keywords: Optional[List[str]] = None,
        locations: Optional[List[str]] = None,
        limit: int = 10,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Discovers DevOps / MLOps / Platform / Data Engineering roles on Indeed India
        (https://in.indeed.com/jobs) and routes matching 1-4 YOE roles through apply_job().
        If Cloudflare / anti-bot challenge is detected, queues to AttentionQueue and exits cleanly.
        """
        from urllib.parse import quote_plus
        from naukari_pro.modules.role_guard import is_target_role

        target_keywords = keywords or [
            "DevOps Engineer",
            "MLOps Engineer",
            "Platform Engineer",
            "Site Reliability Engineer",
            "Azure Data Engineer",
        ]
        target_locations = locations or ["Bengaluru", "Hyderabad", "Pune"]

        if dry_run:
            return {
                "discovered": len(target_keywords),
                "applied": 0,
                "blocked": 0,
                "status": "DRY_RUN",
            }

        from playwright.sync_api import sync_playwright
        from naukari_pro.session import get_stealth_context
        from naukari_pro.modules.career_portals import PORTALS_SESSION_DIR

        discovered: List[Dict[str, str]] = []
        blocked_count = 0

        try:
            with sync_playwright() as p:
                context = get_stealth_context(
                    p, headless=self.headless, session_dir=PORTALS_SESSION_DIR, lock_timeout=60.0
                )
                try:
                    page = context.pages[0] if context.pages else context.new_page()
                    for kw in target_keywords:
                        if len(discovered) >= limit or blocked_count > 0:
                            break
                        for loc in target_locations:
                            if len(discovered) >= limit or blocked_count > 0:
                                break
                            search_url = (
                                f"https://in.indeed.com/jobs?q={quote_plus(kw)}"
                                f"&l={quote_plus(loc)}&fromage=3"
                            )
                            page.goto(search_url, wait_until="domcontentloaded", timeout=35000)
                            time.sleep(2.5)
                            try:
                                body = (page.inner_text("body") or "")[:4000]
                                title_txt = page.title() or ""
                            except Exception:
                                body = ""
                                title_txt = ""
                            blocker = detect_blocker(body + "\n" + title_txt, url=search_url)
                            if (
                                blocker == BlockerClass.CAPTCHA
                                or "just a moment" in title_txt.lower()
                                or "additional verification required" in body.lower()
                            ):
                                self.attention.push(
                                    BlockerClass.CAPTCHA,
                                    search_url,
                                    "Indeed India Cloudflare verification required on search landing",
                                )
                                self._persist_attention()
                                blocked_count += 1
                                break

                            cards = page.evaluate(
                                r"""() => {
                                    return Array.from(document.querySelectorAll("a[data-jk], a.jcs-JobTitle")).map(a => {
                                        const jk = a.getAttribute("data-jk") || "";
                                        const card = a.closest(".job_seen_beacon, .resultContent, li, td") || a.parentElement;
                                        const compEl = card ? card.querySelector("[data-testid='company-name'], .companyName") : null;
                                        return {
                                            jk,
                                            title: (a.innerText || "").replace(/\s+/g, " ").trim(),
                                            company: compEl ? (compEl.innerText || "").trim() : "Indeed Employer",
                                            href: a.href || (jk ? "https://in.indeed.com/viewjob?jk=" + jk : "")
                                        };
                                    }).filter(c => c.title && c.href);
                                }"""
                            )
                            for c in cards:
                                ok_role, _ = is_target_role(c["title"])
                                if not ok_role:
                                    continue
                                discovered.append(c)
                                if len(discovered) >= limit:
                                    break
                finally:
                    context.close()
        except Exception as exc:
            logger.warning("Indeed discovery notice: %s", exc)

        applied = 0
        for item in discovered[:limit]:
            res = self.apply_job(
                job_url=item["href"],
                company=item["company"],
                title=item["title"],
                dry_run=False,
            )
            if res.get("success"):
                applied += 1

        return {
            "discovered": len(discovered),
            "applied": applied,
            "blocked": blocked_count,
            "status": "BLOCKED_CAPTCHA_QUEUED" if blocked_count > 0 and applied == 0 else ("SUCCESS" if applied > 0 else "IDLE"),
        }
