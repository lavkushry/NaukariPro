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

            # 5. Open to Work — Recruiters Only (/opportunities/job-opportunities/edit/)
            await sync_open_to_work_recruiters_only(page)

            # 6. Clean unverified skills & add core DevOps/Platform/MLOps/Cloud skills
            await sync_linkedin_skills(page)

        finally:
            await ctx.close()


async def sync_open_to_work_recruiters_only(page: Any) -> bool:
    """
    Activates LinkedIn 'Open to work' strictly for RECRUITERS ONLY (hidden from current employer):
    - 5 high-volume titles: DevOps Engineer, Platform Engineer, MLOps Engineer, Cloud Engineer, Site Reliability Engineer
    - 5 India hubs: India, Bengaluru, Hyderabad, Pune, Gurugram (removing Singapore/Dubai wasted slots)
    - Notice period: '15 days or less'
    - Expected annual salary: '₹ 15+ Lakhs'
    - Start date: 'Immediately, I am actively applying'
    - Visibility: 'Recruiters only' (NEVER public #OpenToWork green frame)
    """
    print("\n[*] Synchronizing LinkedIn Open to Work (Recruiters Only)...")
    await page.goto(
        "https://www.linkedin.com/in/lavkushry/opportunities/job-opportunities/edit/",
        wait_until="domcontentloaded",
        timeout=35000,
    )
    await page.wait_for_timeout(4000)

    # 1. Remove low-yield foreign locations (Singapore, Dubai) to free slots for Pune & Gurugram
    for bad_loc in ("Singapore", "Dubai"):
        try:
            rm_btn = page.locator(f"button[aria-label*='Remove {bad_loc}']").first
            if await rm_btn.count() > 0 and await rm_btn.is_visible():
                await rm_btn.click(timeout=2500)
                await page.wait_for_timeout(500)
                print(f"  [✓] Removed foreign location slot: {bad_loc}")
        except Exception:
            pass

    # 2. Add target job titles up to LinkedIn's max (5)
    target_titles = [
        "DevOps Engineer",
        "Platform Engineer",
        "MLOps Engineer",
        "Cloud Engineer",
        "Site Reliability Engineer",
    ]
    for title in target_titles:
        try:
            exists = await page.locator(f"button[aria-label='Remove {title}']").count()
            if exists > 0:
                continue
            add_btn = page.locator("button:has-text('Add title')").first
            if await add_btn.count() == 0 or not await add_btn.is_visible():
                break
            await add_btn.click(timeout=2500)
            await page.wait_for_timeout(600)
            inp = page.locator("input[placeholder*='title' i], input[aria-label*='title' i], input[type='text']").last
            if await inp.count() > 0 and await inp.is_visible():
                await inp.fill(title, timeout=2500)
                await page.wait_for_timeout(1200)
                opt = page.locator("div[role='option'], ul[role='listbox'] li, .basic-typeahead__selectable").first
                if await opt.count() > 0 and await opt.is_visible():
                    await opt.click(timeout=2500)
                else:
                    await inp.press("Enter")
                await page.wait_for_timeout(600)
                print(f"  [+] Added OTW job title: {title}")
        except Exception as e:
            print(f"  [!] OTW title notice ({title}): {e}")

    # 3. Add India Tier-1 hubs (Pune, Gurugram) up to max (5)
    for city in ("Pune, Maharashtra, India", "Gurugram, Haryana, India"):
        try:
            short = city.split(",")[0]
            if await page.locator(f"button[aria-label*='Remove {short}']").count() > 0:
                continue
            add_loc = page.locator("button:has-text('Add location')").first
            if await add_loc.count() == 0 or not await add_loc.is_visible():
                break
            await add_loc.click(timeout=2500)
            await page.wait_for_timeout(600)
            inp = page.locator("input[placeholder*='location' i], input[aria-label*='location' i], input[type='text']").last
            if await inp.count() > 0 and await inp.is_visible():
                await inp.fill(city, timeout=2500)
                await page.wait_for_timeout(1200)
                opt = page.locator("div[role='option'], ul[role='listbox'] li, .basic-typeahead__selectable").first
                if await opt.count() > 0 and await opt.is_visible():
                    await opt.click(timeout=2500)
                else:
                    await inp.press("Enter")
                await page.wait_for_timeout(600)
                print(f"  [+] Added OTW location: {city}")
        except Exception as e:
            print(f"  [!] OTW location notice ({city}): {e}")

    # 4. Select Notice Period = '15 days or less' & Expected Annual Salary = '₹ 15+ Lakhs'
    selects = page.locator("select")
    sel_cnt = await selects.count()
    for idx in range(sel_cnt):
        sel = selects.nth(idx)
        try:
            txt = (await sel.inner_text()).lower()
            if "15 days or less" in txt:
                await sel.select_option(label="15 days or less", timeout=3000)
                print("  [✓] Set OTW Notice period = '15 days or less'")
            elif "15+ lakhs" in txt:
                await sel.select_option(label="₹ 15+ Lakhs", timeout=3000)
                print("  [✓] Set OTW Expected salary = '₹ 15+ Lakhs'")
        except Exception as e:
            print(f"  [!] OTW select notice ({idx}): {e}")

    # 5. Select Start Date = 'Immediately, I am actively applying' AND enforce Visibility = 'Recruiters only'
    otw_radios = await page.evaluate(
        """() => {
            let startSet = false;
            let visSet = false;
            const startRadios = Array.from(document.querySelectorAll("input[type='radio'][name*='START_DATE']"));
            if (startRadios.length > 0) {
                const target = startRadios.find(r => (r.closest('label, div')?.innerText || '').toLowerCase().includes('immediately')) || startRadios[0];
                target.click();
                startSet = true;
            }
            const visRadios = Array.from(document.querySelectorAll("input[type='radio'][name*='VISIBILITY']"));
            if (visRadios.length > 0) {
                const recOnly = visRadios.find(r => (r.closest('label, div')?.innerText || '').toLowerCase().includes('recruiters only')) || visRadios[0];
                if (!recOnly.checked) recOnly.click();
                visSet = !!recOnly.checked;
            }
            return {startSet, visSet};
        }"""
    )
    print("  [✓] OTW Start Date & Recruiters-Only Visibility:", otw_radios)

    await page.wait_for_timeout(1000)
    saved = await click_save(page)
    await page.wait_for_timeout(4500)
    print(f"[✓] Saved LinkedIn Open to Work (Recruiters only): {saved}")
    return saved


async def sync_linkedin_skills(page: Any) -> None:
    """
    1. Purges unverified/drifted skills (Evidently AI, Feast, DVC, Airflow) from /details/skills/
    2. Adds verified high-demand DevOps/Platform/Cloud/MLOps skills via /details/skills/add/
    """
    print("\n[*] Synchronizing LinkedIn Skills...")
    bad_skills = {"evidently ai", "feast", "dvc", "airflow"}
    await page.goto(
        "https://www.linkedin.com/in/lavkushry/details/skills/",
        wait_until="domcontentloaded",
        timeout=35000,
    )
    await page.wait_for_timeout(4000)

    # Check which skills are currently present
    existing_text = (await page.evaluate("() => document.body ? document.body.innerText : ''")).lower()

    # Delete unverified skills by locating edit links inside skill list items
    bad_edit_links: List[str] = await page.evaluate(
        """(badList) => {
            const links = [];
            const items = Array.from(document.querySelectorAll("li.pvs-list__paged-list-item, div[data-view-name='profile-component-entity']"));
            for (const it of items) {
                const txt = (it.innerText || "").toLowerCase();
                const firstLine = txt.split("\\n").map(s => s.trim()).filter(Boolean)[0] || "";
                if (badList.includes(firstLine)) {
                    const a = it.querySelector("a[href*='/details/skills/edit/forms/']");
                    if (a && a.href) links.push(a.href);
                }
            }
            return Array.from(new Set(links));
        }""",
        list(bad_skills),
    )
    for edit_url in bad_edit_links:
        try:
            await page.goto(edit_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2500)
            del_btn = page.locator("button:has-text('Delete skill')").first
            if await del_btn.count() > 0 and await del_btn.is_visible():
                await del_btn.click(timeout=2500)
                await page.wait_for_timeout(1200)
                confirm = page.locator("div[role='dialog'] button:has-text('Delete'), button.artdeco-button--primary:has-text('Delete')").last
                if await confirm.count() > 0 and await confirm.is_visible():
                    await confirm.click(timeout=2500)
                    await page.wait_for_timeout(2000)
                print(f"  [✓] Deleted unverified LinkedIn skill via {edit_url}")
        except Exception as e:
            print(f"  [!] Skill delete notice: {e}")

    # Add core verified skills missing from the live profile
    core_skills = [
        "Kubernetes",
        "Amazon Web Services (AWS)",
        "Microsoft Azure",
        "Docker",
        "Terraform",
        "Ansible",
        "DevOps",
        "ArgoCD",
        "Helm",
        "Jenkins",
        "CI/CD",
        "Prometheus",
        "Grafana",
        "Apache Kafka",
        "Linux",
        "SQL",
    ]
    for skill in core_skills:
        short_key = skill.split("(")[0].strip().lower()
        if f"\n{skill.lower()}\n" in existing_text or f"\n{short_key}\n" in existing_text:
            continue
        try:
            await page.goto(
                "https://www.linkedin.com/in/lavkushry/edit/forms/skills/new/?profileFormEntryPoint=PROFILE_SECTION",
                wait_until="domcontentloaded",
                timeout=30000,
            )
            await page.wait_for_timeout(2500)
            inp = page.locator("input[placeholder*='Skill' i], input[aria-label*='Skill' i], input[type='text']").first
            if await inp.count() > 0 and await inp.is_visible():
                await inp.fill(skill, timeout=2500)
                await page.wait_for_timeout(1200)
                opt = page.locator("div[role='option'], ul[role='listbox'] li, .basic-typeahead__selectable").first
                if await opt.count() > 0 and await opt.is_visible():
                    await opt.click(timeout=2500)
                await page.wait_for_timeout(600)
                saved = await click_save(page)
                await page.wait_for_timeout(2500)
                print(f"  [+] Added LinkedIn skill '{skill}': saved={saved}")
        except Exception as e:
            print(f"  [!] Skill add notice ({skill}): {e}")


if __name__ == "__main__":
    asyncio.run(sync_linkedin_live())
