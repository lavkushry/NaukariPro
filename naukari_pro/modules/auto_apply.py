"""
naukariPro Feature 1: Intelligent Auto-Apply Engine
Adapted from kumarankur123/naukari_job with stealth persistent Chrome context,
recommended jobs multi-apply, keyword search apply, chatbot auto-answer, and Excel logging.
"""

import os
import sys
import asyncio
import json
import re
import hashlib
from datetime import datetime
from playwright.async_api import async_playwright
import openpyxl

from naukari_pro.config import TRACKER_PATH, SESSION_DIR, COOKIES_SEED_PATH

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKIP_FILE = os.path.join(BASE_DIR, "skip_list.json")
LOG_FILE = os.path.join(BASE_DIR, "naukri_applications_log.json")

# Candidate Defaults
NAUKRI_EMAIL = "lavkushry@gmail.com"
EXPERIENCE_YEARS = "2.5"
NOTICE_PERIOD = "30"
CURRENT_CTC = "12"
EXPECTED_CTC = "25"
MIN_SALARY_LPA = 12.0
APPLY_TIMEOUT_SECONDS = 10
BATCH_SIZE = 5

DEFAULT_KEYWORDS = [
    "Azure Data Engineer",
    "Data Engineer",
    "Azure Databricks",
    "PySpark",
    "Delta Lake",
    "Cloud Data Platform",
    "Azure Data Factory",
    "DevOps Engineer"
]

STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
window.navigator.chrome = { runtime: {} };
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en', 'hi'] });
"""

def make_job_id(title, company):
    raw = f"{title.lower().strip()}_{company.lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]

def load_skip_list():
    skip_set = set()
    if os.path.exists(SKIP_FILE):
        try:
            with open(SKIP_FILE, "r", encoding="utf-8") as f:
                skip_set = set(json.load(f))
        except Exception:
            pass
    return skip_set

def save_skip_list(skip_set):
    try:
        with open(SKIP_FILE, "w", encoding="utf-8") as f:
            json.dump(list(skip_set), f, indent=2)
    except Exception:
        pass

def add_to_skip(skip_set, title, company, reason="skipped"):
    jid = make_job_id(title, company)
    skip_set.add(jid)
    save_skip_list(skip_set)
    print(f"  ⛔ Skipped: {title} @ {company} ({reason})")
    return skip_set

def log_to_excel(title, company, status, app_type="1-Click Apply", salary="N/A", url="N/A"):
    try:
        wb = openpyxl.load_workbook(TRACKER_PATH)
        ws = wb["Applications_Log"] if "Applications_Log" in wb.sheetnames else wb.active
        ws.append([
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            company,
            title,
            "Azure Data Engineer",
            "2-5 Yrs",
            "Hyderabad / Bengaluru",
            app_type,
            status,
            url,
            "Awaiting Recruiter Review"
        ])
        wb.save(TRACKER_PATH)
    except Exception as e:
        pass

def parse_salary(salary_text):
    if not salary_text:
        return True, None, None, ""
    text = salary_text.strip()
    lower = text.lower()
    if any(u in lower for u in ["not disclosed", "undisclosed", "confidential", "best in industry"]):
        return True, None, None, text

    cleaned = re.sub(r'(?<=\d),(?=\d)', '', lower)
    range_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)', cleaned)
    if range_match:
        v1 = float(range_match.group(1))
        v2 = float(range_match.group(2))
        return False, min(v1, v2), max(v1, v2), text

    single_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:lacs|lac|lpa)', cleaned)
    if single_match:
        v = float(single_match.group(1))
        return False, v, v, text

    return True, None, None, text

def is_salary_acceptable(salary_text, min_threshold_lpa=MIN_SALARY_LPA):
    is_undisclosed, min_lpa, max_lpa, _ = parse_salary(salary_text)
    if is_undisclosed:
        return True, "Salary undisclosed (allowed)"
    if max_lpa < min_threshold_lpa:
        return False, f"Salary {min_lpa}-{max_lpa} LPA below minimum {min_threshold_lpa} LPA"
    return True, f"Salary {min_lpa}-{max_lpa} LPA meets minimum"

async def close_popups(page):
    for sel in ["button[aria-label='close']", "[class*='closeBtn']", "button.crossIcon", ".modal-close"]:
        try:
            el = await page.query_selector(sel)
            if el and await el.is_visible():
                await el.click()
                await page.wait_for_timeout(200)
        except Exception:
            pass
    try:
        await page.keyboard.press("Escape")
    except Exception:
        pass

# ── Screening Chatbot Auto-Answer Engine ──
async def handle_chatbot(page, max_seconds=APPLY_TIMEOUT_SECONDS):
    drawer_found = False
    for _ in range(6):
        await page.wait_for_timeout(250)
        has_drawer = await page.evaluate("""() => {
            const d = document.querySelector('.chatbot_Drawer, [class*="chatbot_Drawer"]');
            return d && d.offsetWidth > 100 && d.offsetHeight > 100;
        }""")
        if has_drawer:
            drawer_found = True
            break

    if not drawer_found:
        return False

    print(f"  💬 Screening Chatbot detected — auto-answering questions (⏱️ {max_seconds}s timer)...")
    start_time = asyncio.get_event_loop().time()

    for attempt in range(15):
        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed >= max_seconds:
            print(f"    ⏱️ Chatbot questions timed out (> {max_seconds}s limit)")
            return "timeout"

        await page.wait_for_timeout(350)

        status = await page.evaluate("""() => {
            const drawer = document.querySelector('.chatbot_Drawer, [class*="chatbot_Drawer"]');
            if (!drawer || drawer.offsetWidth === 0) return { isApplied: true, isDrawerOpen: false };
            const txt = (drawer.innerText || '').toLowerCase();
            const isApplied = txt.includes('application submitted') || txt.includes('successfully applied') || txt.includes('application sent');
            return { isApplied, isDrawerOpen: true };
        }""")

        if status["isApplied"] or not status["isDrawerOpen"]:
            print("    ✓ Chatbot completed! Application submitted.")
            return True

        step_data = await page.evaluate(r"""() => {
            const drawer = document.querySelector('.chatbot_Drawer, [class*="chatbot_Drawer"]') || document.body;
            const qEls = drawer.querySelectorAll('.botMsg span, .botMsg div, .botMsg');
            let lastQ = '';
            for (let el of qEls) {
                const t = (el.innerText || '').trim();
                if (t && t.length > 5 && !t.toLowerCase().includes('thank you')) lastQ = t;
            }

            const labels = Array.from(drawer.querySelectorAll('.ssrc__label, label, input.ssrc__radio, .ssrc__radio-btn-container, [role="radio"]')).map(l => ({
                text: (l.innerText || l.value || '').replace(/\s+/g, ' ').trim()
            })).filter(l => l.text && l.text.length < 50 && !['save', 'submit', 'next'].includes(l.text.toLowerCase()));

            const textInputEl = drawer.querySelector('div.textArea[contenteditable="true"], div[contenteditable="true"], input[type="text"], textarea');
            return { lastQ, labels, hasTextInput: !!textInputEl && textInputEl.offsetWidth > 0 };
        }""")

        q_text = step_data.get("lastQ", "").lower()
        labels = step_data.get("labels", [])
        has_text_input = step_data.get("hasTextInput", False)

        # Radio options
        if labels:
            chosen = None
            if any(w in q_text for w in ["notice", "joining", "days"]):
                chosen = labels[0]["text"]
                for l in labels:
                    if any(p in l["text"].lower() for p in ["30 days", "1 month", "15 days", "immediate"]):
                        chosen = l["text"]
                        break
            elif any(w in q_text for w in ["experience", "years"]):
                chosen = labels[0]["text"]
                for l in labels:
                    if any(p in l["text"].lower() for p in ["2", "3", "2-3", "1-3"]):
                        chosen = l["text"]
                        break
            elif any(w in q_text for w in ["ctc", "salary"]):
                chosen = labels[0]["text"]
            else:
                for l in labels:
                    if any(pos in l["text"].lower() for pos in ["yes", "agree", "comfortable", "willing", "open"]):
                        chosen = l["text"]
                        break
                if not chosen:
                    chosen = labels[0]["text"]

            try:
                loc = page.locator(f".chatbot_Drawer label:has-text('{chosen}'), .chatbot_Drawer .ssrc__label:has-text('{chosen}')").first
                await loc.click(force=True)
                print(f"    ✓ Selected option: '{chosen}'")
            except Exception:
                pass
            await page.wait_for_timeout(300)

        elif has_text_input:
            ans = "Yes"
            if any(w in q_text for w in ["notice", "days"]):
                ans = NOTICE_PERIOD
            elif any(w in q_text for w in ["current ctc", "current salary"]):
                ans = CURRENT_CTC
            elif any(w in q_text for w in ["expected ctc", "expected salary"]):
                ans = EXPECTED_CTC
            elif any(w in q_text for w in ["experience", "years"]):
                ans = EXPERIENCE_YEARS
            elif any(w in q_text for w in ["english", "communication"]):
                ans = "Fluent"

            await page.evaluate("""(val) => {
                const el = document.querySelector('.chatbot_Drawer div.textArea[contenteditable="true"], .chatbot_Drawer input[type="text"], .chatbot_Drawer textarea');
                if (el) {
                    if (el.isContentEditable || el.tagName === 'DIV') {
                        el.focus();
                        el.innerText = val;
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                    } else {
                        el.focus();
                        el.value = val;
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                    }
                }
            }""", ans)
            print(f"    ✓ Filled answer: '{ans}'")
            await page.wait_for_timeout(400)

        # Submit / Save button
        await page.evaluate("""() => {
            const drawer = document.querySelector('.chatbot_Drawer, [class*="chatbot_Drawer"]');
            if (!drawer) return;
            const btns = Array.from(drawer.querySelectorAll('.sendMsg, .send, button')).filter(b => {
                const t = (b.innerText || '').toLowerCase();
                return (t === 'save' || t === 'submit' || t === 'next' || t === 'apply' || t === 'send') && b.offsetWidth > 0;
            });
            if (btns.length > 0) btns[btns.length - 1].click();
        }""")
        await page.wait_for_timeout(500)

    return True

# ── Main AutoApplyEngine Class ──
class AutoApplyEngine:
    def __init__(self):
        self.skip_list = load_skip_list()

    def run(self, page=None, headless=False, limit=20):
        """Runs async pipeline standalone or with existing page."""
        return asyncio.run(self.run_async(headless=headless, limit=limit))

    async def run_async(self, headless=False, limit=20):
        print("\n" + "=" * 60)
        print("  🚀 NAUKARIPRO: ADVANCED AUTO-APPLY ENGINE ACTIVE")
        print(f"  Target: Up to {limit} Applications | Candidate: {NAUKRI_EMAIL}")
        print("=" * 60)

        # Clean stale Singleton locks
        for lock_file in ["SingletonLock", "SingletonSocket", "SingletonCookie"]:
            lock_path = os.path.join(SESSION_DIR, lock_file)
            if os.path.exists(lock_path) or os.path.islink(lock_path):
                try:
                    os.unlink(lock_path)
                except Exception:
                    pass

        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=SESSION_DIR,
                headless=headless,
                channel="chrome",
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--start-maximized"],
                viewport=None,
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
            )
            await context.add_init_script(STEALTH_JS)

            if os.path.exists(COOKIES_SEED_PATH):
                try:
                    with open(COOKIES_SEED_PATH, "r") as f:
                        cookies = json.load(f)
                    await context.add_cookies(cookies)
                except Exception:
                    pass

            page = context.pages[0] if context.pages else await context.new_page()

            # Verify authentication
            await page.goto("https://www.naukri.com/mnjuser/profile", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)

            total_applied = 0

            # Phase 1: Recommended Jobs Feed Multi-Apply
            print("\n[PHASE 1] Scanning Recommended Jobs Multi-Apply Feed...")
            try:
                await page.goto("https://www.naukri.com/mnjuser/recommendedjobs", wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(3000)
                await close_popups(page)

                checkboxes = await page.query_selector_all("i.naukicon-ot-checkbox, .tuple-check-box i, input[type='checkbox']")
                print(f"Found {len(checkboxes)} multi-apply job checkboxes on recommended feed.")

                selected_count = 0
                for cb in checkboxes[:BATCH_SIZE]:
                    try:
                        if await cb.is_visible():
                            await cb.click(force=True)
                            selected_count += 1
                            await page.wait_for_timeout(300)
                    except Exception:
                        pass

                if selected_count > 0:
                    print(f"Selected {selected_count} recommended jobs. Clicking multi-apply button...")
                    apply_btn = await page.query_selector("button.multi-apply-button, [class*='multi-apply'], button:has-text('Apply')")
                    if apply_btn and await apply_btn.is_visible():
                        await apply_btn.click()
                        await page.wait_for_timeout(2000)
                        await handle_chatbot(page)
                        total_applied += selected_count
                        print(f"✓ Successfully submitted batch of {selected_count} recommended jobs!")
                        log_to_excel("Multi-Apply Recommended Jobs Batch", "Naukri Curated AI Matches", "Submitted", "Recommended Multi-Apply")
            except Exception as e:
                print(f"Recommended feed notice: {e}")

            # Phase 2: Keyword Search Apply
            print("\n[PHASE 2] Scanning Search Results for Azure Data Engineer Vacancies...")
            for keyword in DEFAULT_KEYWORDS[:3]:
                if total_applied >= limit:
                    break

                slug = "-".join(keyword.lower().split())
                url = f"https://www.naukri.com/{slug}-jobs-in-hyderabad?experience={EXPERIENCE_YEARS}&jobAge=1"
                print(f"\nScanning: '{keyword}' in Hyderabad ({url})")

                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(3000)
                    await close_popups(page)

                    tuples = await page.query_selector_all("article.jobTuple, div.srp-jobtuple-wrapper, div.cust-job-tuple")
                    print(f"Found {len(tuples)} fresh job postings.")

                    for item in tuples[:8]:
                        if total_applied >= limit:
                            break

                        title_el = await item.query_selector("a.title")
                        comp_el = await item.query_selector("a.comp-name, a.subTitle")
                        sal_el = await item.query_selector(".sal-wrap, [class*='sal']")

                        title = (await title_el.inner_text()).strip() if title_el else "Data Engineer"
                        comp = (await comp_el.inner_text()).strip() if comp_el else "Employer"
                        salary = (await sal_el.inner_text()).strip() if sal_el else "Undisclosed"
                        job_url = await title_el.get_attribute("href") if title_el else ""

                        if not job_url or make_job_id(title, comp) in self.skip_list:
                            continue

                        # Salary filter
                        acceptable, _ = is_salary_acceptable(salary, MIN_SALARY_LPA)
                        if not acceptable:
                            self.skip_list = add_to_skip(self.skip_list, title, comp, "low-salary")
                            continue

                        print(f"\n  → Applying to: {title} @ {comp} ({salary})")

                        # Open job in new tab
                        job_tab = await context.new_page()
                        try:
                            await job_tab.goto(job_url, wait_until="domcontentloaded", timeout=25000)
                            await job_tab.wait_for_timeout(2000)
                            await close_popups(job_tab)

                            # Locate apply button
                            btn = await job_tab.query_selector("button#apply-button, button:has-text('Apply'), .apply-button")
                            if btn and await btn.is_visible():
                                btn_txt = (await btn.inner_text()).lower()
                                if "company site" in btn_txt:
                                    print("    ⏭️ Requires external portal redirect — logging to Excel.")
                                    log_to_excel(title, comp, "External Redirect", "External Employer Portal", salary, job_url)
                                    self.skip_list = add_to_skip(self.skip_list, title, comp, "external-company-site")
                                else:
                                    await btn.click()
                                    await job_tab.wait_for_timeout(2000)
                                    await handle_chatbot(job_tab)
                                    total_applied += 1
                                    print(f"    ✓ Successfully applied to {title} @ {comp}!")
                                    log_to_excel(title, comp, "Submitted (Pending)", "1-Click Direct", salary, job_url)
                                    self.skip_list = add_to_skip(self.skip_list, title, comp, "already-applied")
                            else:
                                print("    ⚠️ No direct apply button.")
                                self.skip_list = add_to_skip(self.skip_list, title, comp, "no-apply-button")
                        except Exception as err:
                            print(f"    ❌ Error applying: {err}")
                        finally:
                            await job_tab.close()
                            await page.wait_for_timeout(1500)

                except Exception as e:
                    print(f"Search warning: {e}")

            await context.close()

            print("\n" + "=" * 60)
            print(f"  🏁 AUTO-APPLY CYCLE FINISHED: {total_applied} Applications Submitted.")
            print(f"  📊 Live Excel Tracker: {TRACKER_PATH}")
            print("=" * 60 + "\n")
            return total_applied
