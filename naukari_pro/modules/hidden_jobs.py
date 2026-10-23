"""
Feature 4: Hidden Job Opportunities
Discovers off-market vacancies, personalized recommended jobs, and high-paying GCC direct openings.
Accurately categorizes sources and reports real counts.
"""

import time
import logging
from naukari_pro.config import load_config

logger = logging.getLogger("naukariPro.HiddenJobs")

TARGET_GCCS = [
    "Lloyds Technology Centre",
    "PNC Bank",
    "JPMorgan Chase",
    "Barclays",
    "HSBC",
    "Standard Chartered",
    "Wells Fargo",
    "Morgan Stanley",
    "BNY Mellon",
    "Goldman Sachs",
    "Mastercard",
    "Optum",
    "Target Enterprise",
    "Walmart Global Tech"
]

class HiddenJobsEngine:
    def __init__(self):
        self.cfg = load_config()

    def discover_hidden_opportunities(self, page):
        """
        Scrapes personalized recommended jobs and GCC direct engineering listings.
        Differentiates between recruiter direct inquiries and algorithmic feed matches.
        """
        logger.info("Scanning for off-market and curated job opportunities...")
        hidden_jobs = []

        # 1. Scrape Direct Recruiter Inquiries / Inbox
        try:
            page.goto("https://www.naukri.com/mnjuser/inbox", wait_until="domcontentloaded", timeout=25000)
            time.sleep(2)
            if "login" not in page.url:
                inbox_cards = page.locator(".msg-card, .inbox-tuple, div[class*='messageTuple']").all()
                for ic in inbox_cards[:5]:
                    txt = ic.inner_text().strip().replace("\n", " | ")
                    if txt:
                        hidden_jobs.append({
                            "title": txt[:60] + "...",
                            "company": "Direct Recruiter Inquiry",
                            "location": "Inbox",
                            "source": "Private Recruiter NVite / Message",
                            "is_gcc": False,
                            "url": "https://www.naukri.com/mnjuser/inbox"
                        })
        except Exception as e:
            logger.debug("Inbox check notice: %s", e)

        # 2. Scrape Personalized Recommended Jobs Feed
        try:
            page.goto("https://www.naukri.com/mnjuser/recommendedjobs", wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)
            # Modern and fallback selectors
            cards = page.locator(".srp-jobtuple-wrapper, .cust-job-tuple, .job-tuple, article.jobTuple").all()
            for c in cards[:10]:
                try:
                    title_el = c.locator("a.title, a[class*='title']").first
                    comp_el = c.locator("a.comp-name, span.comp-nameText, a.subTitle").first
                    loc_el = c.locator("span.locWdth, .loc-wrap, span[class*='loc']").first

                    title = title_el.inner_text().strip() if title_el.count() > 0 else ""
                    comp = comp_el.inner_text().strip() if comp_el.count() > 0 else "Confidential Employer"
                    loc = loc_el.inner_text().strip() if loc_el.count() > 0 else "Hyderabad / Bengaluru"
                    href = title_el.get_attribute("href") if title_el.count() > 0 else ""

                    if title and href:
                        hidden_jobs.append({
                            "title": title,
                            "company": comp,
                            "location": loc,
                            "source": "Naukri Curated AI Match Feed",
                            "is_gcc": any(gcc.lower() in comp.lower() for gcc in TARGET_GCCS),
                            "url": href
                        })
                except Exception:
                    continue
        except Exception as e:
            logger.warning("Recommended feed notice: %s", e)

        # 3. Scrape Targeted GCC Direct Openings in Hyderabad & Bangalore
        for gcc in TARGET_GCCS[:3]:
            slug = gcc.lower().replace(" ", "-")
            url = f"https://www.naukri.com/{slug}-jobs-in-hyderabad"
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=20000)
                time.sleep(2)
                cards = page.locator(".srp-jobtuple-wrapper, .cust-job-tuple, .job-tuple").all()
                for c in cards[:2]:
                    title_el = c.locator("a.title, a[class*='title']").first
                    title = title_el.inner_text().strip() if title_el.count() > 0 else ""
                    href = title_el.get_attribute("href") if title_el.count() > 0 else ""

                    if title and href and any(k in title.lower() for k in ["data", "cloud", "platform", "azure", "engineer"]):
                        hidden_jobs.append({
                            "title": title,
                            "company": gcc,
                            "location": "Hyderabad",
                            "source": "GCC Direct Engineering Portal",
                            "is_gcc": True,
                            "url": href
                        })
            except Exception:
                continue

        logger.info("Identified %d off-market/recommended opportunities.", len(hidden_jobs))
        return hidden_jobs
