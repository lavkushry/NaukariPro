#!/usr/bin/env python3
"""
Synchronize live LinkedIn profile (https://www.linkedin.com/in/lavkushry/)
with the canonical 01_FACT_MATRIX.md & AGENTS.md blueprint:
1. Intro (/edit/intro/): First name="Lavkush", Last name="Kumar", Headline (Tiptap ProseMirror)
2. About section (/edit/forms/summary/new/) (Tiptap ProseMirror)
3. 4 Experience roles (/details/experience/): Title* (aria-labelledby) + Description (Tiptap ProseMirror)
4. Verified public GitHub Projects (/details/projects/)
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from playwright.async_api import async_playwright

from naukari_pro.modules.db import record_profile_mutation
from naukari_pro.modules.linkedin_optimizer import LINKEDIN_100K_MLOPS_BLUEPRINT
from naukari_pro.modules.linkedin_session import LinkedInSessionManager


async def fill_by_exact_label(
    page: Any,
    label_regex: str,
    value: str,
    allow_single_tiptap_fallback: bool = False,
) -> Dict[str, Any]:
    return await page.evaluate(
        r"""({labelRegex, val, allowTiptapFallback}) => {
            const re = new RegExp(labelRegex, "i");
            const setFieldValue = (el, v) => {
                if (el.isContentEditable || el.getAttribute("contenteditable") === "true" || el.getAttribute("role") === "textbox") {
                    el.focus();
                    const sel = window.getSelection();
                    const range = document.createRange();
                    range.selectNodeContents(el);
                    sel.removeAllRanges();
                    sel.addRange(range);
                    const ok = document.execCommand("insertText", false, v);
                    if (!ok || (el.innerText || "").trim().length === 0) {
                        el.innerText = v;
                    }
                    el.dispatchEvent(new InputEvent("input", {bubbles: true, inputType: "insertText", data: v}));
                    el.dispatchEvent(new Event("change", {bubbles: true}));
                    el.dispatchEvent(new Event("blur", {bubbles: true}));
                    return;
                }
                const proto = el.tagName === "TEXTAREA"
                    ? window.HTMLTextAreaElement.prototype
                    : window.HTMLInputElement.prototype;
                const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
                if (setter) setter.call(el, v);
                else el.value = v;
                el.dispatchEvent(new Event("input", {bubbles: true}));
                el.dispatchEvent(new Event("change", {bubbles: true}));
                el.dispatchEvent(new Event("blur", {bubbles: true}));
            };

            const getLabelText = (el) => {
                const id = el.id || "";
                const lblFor = id ? document.querySelector('label[for="' + id + '"]') : el.closest("label");
                const ariaLblBy = el.getAttribute("aria-labelledby");
                const lblByEl = ariaLblBy ? document.getElementById(ariaLblBy) : null;
                const parts = [
                    lblFor ? lblFor.innerText : "",
                    lblByEl ? lblByEl.innerText : "",
                    el.getAttribute("aria-label") || "",
                ];
                return parts.join(" ").replace(/\s+/g, " ").trim();
            };

            const allEls = Array.from(
                document.querySelectorAll("input, textarea, [contenteditable='true'], [role='textbox']")
            ).filter(el => {
                if (el.tagName === "INPUT") {
                    return el.type === "text" || el.type === "url" || el.type === "search" || !el.getAttribute("type");
                }
                return true;
            });

            for (const el of allEls) {
                const lblText = getLabelText(el);
                if (lblText && re.test(lblText)) {
                    const oldVal = (el.value !== undefined ? el.value : el.innerText || "");
                    setFieldValue(el, val);
                    const newVal = (el.value !== undefined ? el.value : el.innerText || "");
                    return {
                        ok: true,
                        matched: lblText,
                        tag: el.tagName,
                        oldVal: oldVal.slice(0, 100),
                        newLen: newVal.length
                    };
                }
            }

            if (allowTiptapFallback) {
                const tiptaps = Array.from(
                    document.querySelectorAll("div[contenteditable='true'][role='textbox'], div.ProseMirror[contenteditable='true'], textarea")
                );
                if (tiptaps.length === 1) {
                    const el = tiptaps[0];
                    const oldVal = (el.value !== undefined ? el.value : el.innerText || "");
                    setFieldValue(el, val);
                    const newVal = (el.value !== undefined ? el.value : el.innerText || "");
                    return {
                        ok: true,
                        matched: "single_tiptap_or_textarea_fallback",
                        tag: el.tagName,
                        oldVal: oldVal.slice(0, 100),
                        newLen: newVal.length
                    };
                }
            }

            return {
                ok: false,
                allFields: allEls.map(e => ({
                    tag: e.tagName,
                    id: e.id || "",
                    ce: e.isContentEditable,
                    label: getLabelText(e),
                    val: (e.value !== undefined ? e.value : e.innerText || "").slice(0, 50)
                }))
            };
        }""",
        {
            "labelRegex": label_regex,
            "val": value,
            "allowTiptapFallback": allow_single_tiptap_fallback,
        },
    )


async def click_save(page: Any) -> bool:
    return bool(
        await page.evaluate(
            """() => {
                const btns = Array.from(document.querySelectorAll("button")).filter(
                    b => /^save$/i.test((b.innerText || "").trim())
                );
                if (btns.length > 0) {
                    btns[btns.length - 1].click();
                    return true;
                }
                return false;
            }"""
        )
    )


async def wait_for_editor_ready(page: Any, timeout_ms: int = 20000) -> None:
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    try:
        await page.locator(
            "div[contenteditable='true'][role='textbox'], div.ProseMirror[contenteditable='true'], textarea"
        ).first.wait_for(state="visible", timeout=timeout_ms)
    except Exception:
        pass
    await page.wait_for_timeout(1500)


async def sync_linkedin_live() -> None:
    load_dotenv(".env", override=True)
    mgr = LinkedInSessionManager()
    bp = LINKEDIN_100K_MLOPS_BLUEPRINT
    headline = bp["headline"]
    about = bp["about"]
    exps: List[Dict[str, Any]] = bp["experience"]

    async with async_playwright() as p:
        ctx = await mgr.create_stealth_context(p, headless=True)
        try:
            page = ctx.pages[0] if ctx.pages else await ctx.new_page()

            # 1. Intro & Headline (/edit/intro/)
            await page.goto(
                "https://www.linkedin.com/in/lavkushry/edit/intro/",
                wait_until="domcontentloaded",
                timeout=35000,
            )
            await wait_for_editor_ready(page)
            r_fn = await fill_by_exact_label(page, r"first\s*name", "Lavkush")
            r_ln = await fill_by_exact_label(page, r"last\s*name", "Kumar")
            r_hl = await fill_by_exact_label(
                page, r"headline", headline, allow_single_tiptap_fallback=True
            )
            print("INTRO FILL:", {"first_name": r_fn, "last_name": r_ln, "headline": r_hl})
            if r_fn.get("ok") or r_hl.get("ok"):
                await page.wait_for_timeout(1000)
                saved = await click_save(page)
                await page.wait_for_timeout(4500)
                record_profile_mutation(
                    platform="linkedin",
                    field="headline",
                    old_value=r_hl.get("oldVal", ""),
                    new_value=headline,
                    is_keyword_mutation=True,
                    rationale="live_linkedin_sync",
                    approved_by="sync_linkedin_live",
                )
                print("[✓] Saved LinkedIn Intro & Headline:", saved)

            # 2. About (/edit/forms/summary/new/)
            await page.goto(
                "https://www.linkedin.com/in/lavkushry/edit/forms/summary/new/",
                wait_until="domcontentloaded",
                timeout=35000,
            )
            await wait_for_editor_ready(page, timeout_ms=15000)
            r_abt = await fill_by_exact_label(
                page, r"^about$|summary", about, allow_single_tiptap_fallback=True
            )
            print("ABOUT FILL:", r_abt)
            if r_abt.get("ok"):
                await page.wait_for_timeout(1000)
                saved = await click_save(page)
                await page.wait_for_timeout(4500)
                record_profile_mutation(
                    platform="linkedin",
                    field="summary",
                    old_value=r_abt.get("oldVal", ""),
                    new_value=about[:120],
                    is_keyword_mutation=True,
                    rationale="live_linkedin_sync",
                    approved_by="sync_linkedin_live",
                )
                print(f"[✓] Saved LinkedIn About ({len(about)} chars):", saved)

            # 3. Experience (/details/experience/)
            await page.goto(
                "https://www.linkedin.com/in/lavkushry/details/experience/",
                wait_until="domcontentloaded",
                timeout=35000,
            )
            await page.wait_for_timeout(4000)
            exp_links: List[str] = await page.evaluate(
                """() => Array.from(new Set(
                    Array.from(document.querySelectorAll('a[href*="/details/experience/edit/forms/"]'))
                        .map(a => a.href)
                ))"""
            )
            print("UNIQUE EXP LINKS:", exp_links)
            for idx, e_url in enumerate(exp_links[: len(exps)]):
                role_data = exps[idx]
                role_desc = "\n".join("• " + b for b in role_data["bullets"])
                await page.goto(e_url, wait_until="domcontentloaded", timeout=35000)
                await wait_for_editor_ready(page)
                r_t = await fill_by_exact_label(page, r"^title\*?$", role_data["title"])
                r_eh = await fill_by_exact_label(page, r"profile\s*headline", headline)
                r_d = await fill_by_exact_label(
                    page, r"description", role_desc, allow_single_tiptap_fallback=True
                )
                co_name = role_data["company"]
                print(f"EXP {idx + 1} ({co_name}): title={r_t} exp_headline={r_eh} desc={r_d}")
                await page.wait_for_timeout(1000)
                saved = await click_save(page)
                await page.wait_for_timeout(4500)
                print(f"[✓] Saved LinkedIn Experience {idx + 1}: {saved}")

            # 4. Projects (/details/projects/)
            await page.goto(
                "https://www.linkedin.com/in/lavkushry/details/projects/",
                wait_until="domcontentloaded",
                timeout=35000,
            )
            await page.wait_for_timeout(4000)
            proj_links: List[str] = await page.evaluate(
                """() => Array.from(new Set(
                    Array.from(document.querySelectorAll('a[href*="/details/projects/edit/forms/"]'))
                        .map(a => a.href)
                ))"""
            )
            print("UNIQUE PROJ LINKS:", proj_links)
            projects_data = [
                (
                    "AegisAgent — Zero-Trust AI Agent Security Gateway (github.com/lavkushry/AegisAgent)",
                    "• Architected an open-source zero-trust security gateway for AI agents in Rust integrating the Cedar Policy Engine to enforce ABAC over MCP tool invocations with sub-75ms policy evaluation latency.\n• Engineered production Kubernetes Helm charts (aegis-gateway), Prometheus ServiceMonitors, and NetworkPolicies with automated GitHub Actions CI/SAST pipelines.\n\nRepository: https://github.com/lavkushry/AegisAgent",
                ),
                (
                    "Project Vulcan — Enterprise Automation Control Plane (github.com/lavkushry/vulcan)",
                    "• Architected an asynchronous infrastructure automation control plane in Python (FastAPI) with Redis Redlock distributed locking, Celery workers, and MinIO S3 artifact storage.\n• Integrated semantic incident retrieval using PostgreSQL with pgvector HNSW indexing and WebSocket live log streaming, cutting SRE diagnostic triage under 2 minutes.\n\nRepository: https://github.com/lavkushry/vulcan",
                ),
                (
                    "Azure Medallion Lakehouse Platform (github.com/lavkushry/Azure-Data-Engineering-Medallion-Lakehouse-Project)",
                    "• Built an end-to-end Medallion Lakehouse (Bronze, Silver, Gold) on Azure Databricks, PySpark, Delta Lake, and Azure Data Factory (ADF) across ADLS Gen2, optimizing Spark SQL partition pruning to cut batch ETL runtime from 4.0h to 2.6h (35% reduction).\n\nRepository: https://github.com/lavkushry/Azure-Data-Engineering-Medallion-Lakehouse-Project",
                ),
            ]
            for idx, p_url in enumerate(proj_links[: len(projects_data)]):
                p_title, p_desc = projects_data[idx]
                await page.goto(p_url, wait_until="domcontentloaded", timeout=35000)
                await wait_for_editor_ready(page)
                r_pt = await fill_by_exact_label(page, r"project\s*name|name|title", p_title)
                r_pd = await fill_by_exact_label(
                    page, r"description", p_desc, allow_single_tiptap_fallback=True
                )
                print(f"PROJ {idx + 1}: title={r_pt} desc={r_pd}")
                await page.wait_for_timeout(1000)
                saved = await click_save(page)
                await page.wait_for_timeout(4500)
                print(f"[✓] Saved LinkedIn Project {idx + 1}: {saved}")

        finally:
            await ctx.close()


if __name__ == "__main__":
    asyncio.run(sync_linkedin_live())
