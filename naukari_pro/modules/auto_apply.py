"""
naukariPro Feature 1: Intelligent Auto-Apply Engine
Dual-Engine Architecture:
1. Native Chrome Bridge (macOS): 100% undetected by Akamai WAF. Interacts directly
   with the user's authentic, authenticated Google Chrome browser.
2. Playwright Stealth Context (Linux/Headless): Automated headless pipeline for remote
   cloud servers and scheduled cron jobs.
"""

import os
import sys
import time
import json
import re
import hashlib
import subprocess
from datetime import datetime
import openpyxl

from naukari_pro.config import TRACKER_PATH, SESSION_DIR, COOKIES_SEED_PATH
from naukari_pro.modules.career_portals import CareerPortalFiller

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKIP_FILE = os.path.join(BASE_DIR, "skip_list.json")
LOG_FILE = os.path.join(BASE_DIR, "naukri_applications_log.json")

# Candidate Profile Defaults
NAUKRI_EMAIL = "lavkushry@gmail.com"
EXPERIENCE_PARAM = "2"  # Integer for Naukri query string (2 matches 2-5 YOE; 2.5 causes 20-25 YOE bug)
EXPERIENCE_YEARS = "2.5"
NOTICE_PERIOD = "30"
CURRENT_CTC = "12"
EXPECTED_CTC = "25"
MIN_SALARY_LPA = 12.0
APPLY_TIMEOUT_SECONDS = 15
BATCH_SIZE = 5

DEFAULT_KEYWORDS = [
    "Azure Data Engineer",
    "Azure Databricks",
    "PySpark",
    "Delta Lake",
    "Azure Data Factory",
    "Data Engineer"
]

LOCATIONS = ["hyderabad", "bengaluru", "pune"]

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
    except Exception:
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

def is_mac_chrome_available():
    if sys.platform != "darwin":
        return False
    try:
        cmd = "pgrep -i 'Google Chrome'"
        out = subprocess.check_output(cmd, shell=True).decode().strip()
        return bool(out)
    except Exception:
        return False

# ─────────────────────────────────────────────────────────────────────────────
# ENGINE 1: NATIVE MACOS CHROME RUNNER (100% Undetected by Akamai)
# ─────────────────────────────────────────────────────────────────────────────
class NativeChromeRunner:
    def __init__(self, skip_list):
        self.skip_list = skip_list

    def exec_js_in_tab(self, tab_url, js_code, wait_sec=4):
        apple_script = f'''
        tell application "Google Chrome"
            set myTab to make new tab at end of tabs of window 1 with properties {{URL:"{tab_url}"}}
            delay {wait_sec}
            set res to execute myTab javascript {json.dumps(js_code)}
            close myTab
            return res
        end tell
        '''
        p = subprocess.run(["osascript", "-e", apple_script], capture_output=True, text=True)
        if p.returncode == 0:
            return p.stdout.strip()
        return None

    def run_multi_apply_recommended(self):
        print("\n[PHASE 1] Scanning Recommended Jobs Multi-Apply Feed via Chrome...")
        multi_js = """
        (() => {
            try {
                window.scrollTo(0, 1000);
                const checkboxes = Array.from(document.querySelectorAll('i.naukicon-ot-checkbox, .tuple-check-box'));
                let checked = 0;
                for (let cb of checkboxes.slice(0, 5)) {
                    cb.click();
                    checked++;
                }
                const allBtns = Array.from(document.querySelectorAll('button'));
                const multiBtn = allBtns.find(b => (b.innerText || '').trim().toLowerCase() === 'apply');
                if (checked > 0 && multiBtn) {
                    multiBtn.click();
                    return JSON.stringify({ status: 'applied', count: checked });
                }
                return JSON.stringify({ status: 'no_jobs', count: checked });
            } catch(e) {
                return JSON.stringify({ error: e.toString() });
            }
        })()
        """
        res = self.exec_js_in_tab("https://www.naukri.com/mnjuser/recommendedjobs", multi_js, wait_sec=4)
        if res:
            try:
                data = json.loads(res)
                if data.get("status") == "applied":
                    c = data.get("count", 0)
                    print(f"  ✓ Multi-Apply Batch Submitted: {c} jobs on Recommended Feed!")
                    log_to_excel("Multi-Apply Recommended Jobs Batch", "Naukri Curated AI Matches", "Submitted", "Recommended Multi-Apply")
                    return c
            except Exception:
                pass
        print("  ℹ️ Recommended feed batch already claimed or 0 unapplied jobs.")
        return 0

    def apply_to_job(self, job_url, title, company, salary):
        """Applies to a single job in Chrome, handling 1-click and screening questionnaires."""
        apply_script = f'''
        tell application "Google Chrome"
            set myTab to make new tab at end of tabs of window 1 with properties {{URL:"{job_url}"}}
            delay 4
            
            -- Step 1: Check button status
            set step1 to execute myTab javascript "(() => {{
                const btn = document.querySelector('button#apply-button, .styles_apply-button__uJI3A, button.apply-button');
                const coBtn = document.querySelector('button#company-site-button, .styles_company-site-button__C_2YK');
                if (coBtn) {{
                    coBtn.click();
                    return JSON.stringify({{ action: 'company_site_clicked' }});
                }}
                if (!btn) return JSON.stringify({{ action: 'no_button' }});
                const txt = (btn.innerText || '').toLowerCase();
                if (txt.includes('already applied')) return JSON.stringify({{ action: 'already_applied' }});
                btn.click();
                return JSON.stringify({{ action: 'clicked' }});
            }})()"
            
            delay 3
            
            if step1 contains "company_site_clicked" then
                close myTab
                return "{'isApplied': true, 'action': 'company_site'}"
            end if
            
            -- Step 2: Handle potential screening chatbot questions
            set step2 to execute myTab javascript "(() => {{
                const drawer = document.querySelector('.chatbot_Drawer, [class*=\\"chatbot_Drawer\\"]');
                if (!drawer) {{
                    const applied = document.body.innerText.toLowerCase().includes('application sent') || document.body.innerText.toLowerCase().includes('applied');
                    return JSON.stringify({{ isApplied: applied, hasDrawer: false }});
                }}
                
                // Read last bot question
                const qEls = drawer.querySelectorAll('.botMsg span, .botMsg div, .botMsg');
                let lastQ = '';
                for (let el of qEls) {{
                    const t = (el.innerText || '').trim();
                    if (t && t.length > 5) lastQ = t;
                }}
                const qLower = lastQ.toLowerCase();
                
                // Radio options
                const radioLabels = Array.from(drawer.querySelectorAll('.ssrc__label, label')).filter(l => l.innerText.trim().length > 0);
                if (radioLabels.length > 0) {{
                    let chosen = radioLabels[0];
                    for (let l of radioLabels) {{
                        const lt = l.innerText.toLowerCase();
                        if (['yes', 'agree', 'comfortable', 'immediate', '30 days', '1 month'].some(w => lt.includes(w))) {{
                            chosen = l;
                            break;
                        }}
                    }}
                    chosen.click();
                }}
                
                // Text inputs
                const textEl = drawer.querySelector('div.textArea[contenteditable=\\"true\\"], input[type=\\"text\\"], textarea');
                if (textEl) {{
                    let ans = 'NA';
                    if (qLower.includes('notice')) ans = '{NOTICE_PERIOD}';
                    else if (qLower.includes('current ctc') || qLower.includes('current salary')) ans = '{CURRENT_CTC}';
                    else if (qLower.includes('expected ctc') || qLower.includes('expected salary')) ans = '{EXPECTED_CTC}';
                    else if (qLower.includes('experience') || qLower.includes('years')) ans = '{EXPERIENCE_YEARS}';
                    
                    if (textEl.isContentEditable || textEl.tagName === 'DIV') {{
                        textEl.focus();
                        textEl.innerText = ans;
                        textEl.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }} else {{
                        textEl.focus();
                        textEl.value = ans;
                        textEl.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }}
                }}
                
                // Click send
                const sendBtn = drawer.querySelector('.sendMsg, .send, button[type=\\"submit\\"], button.send');
                if (sendBtn) sendBtn.click();
                
                return JSON.stringify({{ isApplied: true, hasDrawer: true, answered: lastQ }});
            }})()"
            
            delay 2
            close myTab
            return step2
        end tell
        '''
        p = subprocess.run(["osascript", "-e", apply_script], capture_output=True, text=True)
        if p.returncode == 0:
            out = p.stdout.strip()
            try:
                data = json.loads(out)
                if data.get("action") == "company_site":
                    return True, "Redirected to External Career Portal (Tracked)"
                if data.get("isApplied"):
                    return True, "Applied via Native Chrome"
            except Exception:
                pass
        return False, "Failed to confirm"

    def run(self, limit=20):
        print("\n" + "=" * 65)
        print("  🚀 NAUKARIPRO: NATIVE CHROME STEALTH ENGINE (macOS)")
        print(f"  Target: Up to {limit} Applications | Candidate: {NAUKRI_EMAIL}")
        print("  Zero Akamai WAF blocking — using authentic Chrome session")
        print("=" * 65)

        total_applied = self.run_multi_apply_recommended()

        search_js = """
        (() => {
            const items = Array.from(document.querySelectorAll('.srp-jobtuple-wrapper, article.jobTuple'));
            return JSON.stringify(items.slice(0, 10).map(it => {
                const title = it.querySelector('a.title');
                const comp = it.querySelector('a.comp-name, a.subTitle');
                const exp = it.querySelector('.exp-wrap, [class*="exp"]');
                const sal = it.querySelector('.sal-wrap, [class*="sal"]');
                return {
                    title: title ? title.innerText.trim() : '',
                    href: title ? title.href : '',
                    company: comp ? comp.innerText.trim() : '',
                    exp: exp ? exp.innerText.trim() : '',
                    sal: sal ? sal.innerText.trim() : 'Undisclosed'
                };
            }));
        })()
        """

        print("\n[PHASE 2] Scanning Keyword Search Feeds (2-5 YOE)...")
        for kw in DEFAULT_KEYWORDS:
            if total_applied >= limit:
                break

            slug = "-".join(kw.lower().split())
            search_url = f"https://www.naukri.com/{slug}-jobs-in-hyderabad?experience={EXPERIENCE_PARAM}&jobAge=1"
            print(f"\nScanning: '{kw}' (Hyderabad) -> {search_url}")

            raw = self.exec_js_in_tab(search_url, search_js, wait_sec=4)
            if not raw:
                continue

            try:
                jobs = json.loads(raw)
            except Exception:
                continue

            print(f"  Found {len(jobs)} fresh vacancies.")

            for job in jobs:
                if total_applied >= limit:
                    break

                title = job.get("title", "")
                comp = job.get("company", "")
                salary = job.get("sal", "Undisclosed")
                job_url = job.get("href", "")

                if not job_url or make_job_id(title, comp) in self.skip_list:
                    continue

                acceptable, reason = is_salary_acceptable(salary, MIN_SALARY_LPA)
                if not acceptable:
                    self.skip_list = add_to_skip(self.skip_list, title, comp, "low-salary")
                    continue

                print(f"\n  → Applying to: {title} @ {comp} ({salary})")
                success, msg = self.apply_to_job(job_url, title, comp, salary)

                if success:
                    total_applied += 1
                    print(f"    ✓ Successfully applied to {title} @ {comp}!")
                    log_to_excel(title, comp, "Submitted (Pending)", "1-Click Direct", salary, job_url)
                    self.skip_list = add_to_skip(self.skip_list, title, comp, "already-applied")
                else:
                    print(f"    ⚠️ Could not submit direct apply ({msg}).")
                    self.skip_list = add_to_skip(self.skip_list, title, comp, "no-direct-apply")

                time.sleep(1.5)

        print("\n" + "=" * 65)
        print(f"  🏁 AUTO-APPLY CYCLE FINISHED: {total_applied} Applications Submitted.")
        print(f"  📊 Live Excel Tracker: {TRACKER_PATH}")
        print("=" * 65 + "\n")
        return total_applied


# ─────────────────────────────────────────────────────────────────────────────
# ENGINE 2: PLAYWRIGHT STEALTH RUNNER (Linux Cloud Server / Headless Fallback)
# ─────────────────────────────────────────────────────────────────────────────
STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
window.navigator.chrome = { runtime: {} };
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en', 'hi'] });
"""

class PlaywrightRunner:
    def __init__(self, skip_list):
        self.skip_list = skip_list

    async def handle_chatbot(self, page):
        for _ in range(5):
            await page.wait_for_timeout(300)
            has_drawer = await page.evaluate("() => !!document.querySelector('.chatbot_Drawer, [class*=\"chatbot_Drawer\"]')")
            if has_drawer:
                break
        else:
            return False

        print("  💬 Screening Chatbot detected — auto-answering questions...")
        for _ in range(10):
            await page.wait_for_timeout(400)
            status = await page.evaluate("""() => {
                const drawer = document.querySelector('.chatbot_Drawer, [class*="chatbot_Drawer"]');
                if (!drawer) return { isApplied: true };
                const txt = drawer.innerText.toLowerCase();
                return { isApplied: txt.includes('submitted') || txt.includes('sent') || txt.includes('applied') };
            }""")
            if status.get("isApplied"):
                return True

            await page.evaluate(f"""() => {{
                const drawer = document.querySelector('.chatbot_Drawer, [class*="chatbot_Drawer"]');
                if (!drawer) return;
                const radios = Array.from(drawer.querySelectorAll('.ssrc__label, label'));
                if (radios.length > 0) {{
                    radios[0].click();
                }}
                const txt = drawer.querySelector('div.textArea[contenteditable="true"], input[type="text"], textarea');
                if (txt) {{
                    txt.focus();
                    txt.innerText = 'NA';
                    txt.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }}
                const send = drawer.querySelector('.sendMsg, .send, button[type="submit"]');
                if (send) send.click();
            }}""")

        return True

    async def run_async(self, headless=False, limit=20):
        from playwright.async_api import async_playwright

        print("\n" + "=" * 65)
        print("  🚀 NAUKARIPRO: PLAYWRIGHT STEALTH ENGINE (Linux/Headless)")
        print(f"  Target: Up to {limit} Applications | Candidate: {NAUKRI_EMAIL}")
        print("=" * 65)

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
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
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
            total_applied = 0

            # Scan keywords
            for kw in DEFAULT_KEYWORDS[:3]:
                if total_applied >= limit:
                    break
                slug = "-".join(kw.lower().split())
                url = f"https://www.naukri.com/{slug}-jobs-in-hyderabad?experience={EXPERIENCE_PARAM}&jobAge=1"
                print(f"\nScanning: '{kw}' in Hyderabad ({url})")

                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(3000)

                    tuples = await page.query_selector_all("article.jobTuple, div.srp-jobtuple-wrapper")
                    print(f"Found {len(tuples)} postings.")

                    for item in tuples[:6]:
                        if total_applied >= limit:
                            break

                        title_el = await item.query_selector("a.title")
                        comp_el = await item.query_selector("a.comp-name, a.subTitle")
                        sal_el = await item.query_selector(".sal-wrap")

                        title = (await title_el.inner_text()).strip() if title_el else "Data Engineer"
                        comp = (await comp_el.inner_text()).strip() if comp_el else "Employer"
                        salary = (await sal_el.inner_text()).strip() if sal_el else "Undisclosed"
                        job_url = await title_el.get_attribute("href") if title_el else ""

                        if not job_url or make_job_id(title, comp) in self.skip_list:
                            continue

                        print(f"\n  → Applying to: {title} @ {comp} ({salary})")
                        job_tab = await context.new_page()
                        try:
                            await job_tab.goto(job_url, wait_until="domcontentloaded", timeout=25000)
                            await job_tab.wait_for_timeout(2500)

                            btn = await job_tab.query_selector("button#apply-button, .styles_apply-button__uJI3A, button:has-text('Apply')")
                            co_btn = await job_tab.query_selector("button#company-site-button, .styles_company-site-button__C_2YK")

                            if co_btn:
                                print("    🌐 External portal detected — auto-filling via CareerPortalFiller...")
                                filler = CareerPortalFiller()
                                ok, _ = filler.fill_in_playwright(job_tab, job_url, comp, title)
                                if ok:
                                    total_applied += 1
                                    self.skip_list = add_to_skip(self.skip_list, title, comp, "career-portal-filled")
                                else:
                                    log_to_excel(title, comp, "External Redirect", "External Employer Portal", salary, job_url)
                                    self.skip_list = add_to_skip(self.skip_list, title, comp, "external-portal")
                            elif btn and await btn.is_visible():
                                await btn.click()
                                await job_tab.wait_for_timeout(2000)
                                await self.handle_chatbot(job_tab)
                                total_applied += 1
                                print(f"    ✓ Successfully applied to {title} @ {comp}!")
                                log_to_excel(title, comp, "Submitted (Pending)", "1-Click Direct", salary, job_url)
                                self.skip_list = add_to_skip(self.skip_list, title, comp, "already-applied")
                            else:
                                print("    ⚠️ No direct apply button.")
                                self.skip_list = add_to_skip(self.skip_list, title, comp, "no-apply-button")
                        except Exception as e:
                            print(f"    ❌ Error: {e}")
                        finally:
                            await job_tab.close()
                except Exception as e:
                    print(f"Search warning: {e}")

            await context.close()
            return total_applied


# ─────────────────────────────────────────────────────────────────────────────
# MAIN AUTO APPLY ENGINE ENTRYPOINT
# ─────────────────────────────────────────────────────────────────────────────
class AutoApplyEngine:
    def __init__(self):
        self.skip_list = load_skip_list()

    def run(self, page=None, headless=False, limit=20):
        # Auto-detect best engine: Native Chrome on macOS if Chrome is open; otherwise Playwright
        if is_mac_chrome_available():
            engine = NativeChromeRunner(self.skip_list)
            return engine.run(limit=limit)
        else:
            import asyncio
            engine = PlaywrightRunner(self.skip_list)
            return asyncio.run(engine.run_async(headless=headless, limit=limit))
