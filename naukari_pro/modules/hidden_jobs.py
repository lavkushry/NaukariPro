"""
Feature 4: Hidden Job Opportunities
Discovers off-market vacancies, personalized recommended jobs, and high-paying GCC direct openings.
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
        """Scrapes personalized recommended jobs and GCC direct listings."""
        logger.info("Scanning for stealth & off-market job opportunities...")
        hidden_jobs = []

        # 1. Scrape Personalized Recommended Jobs Feed
        try:
            page.goto("https://www.naukri.com/mnjuser/recommendedjobs", wait_until="networkidle", timeout=30000)
            time.sleep(3)
            cards = page.locator("article.jobTuple, .cust-job-tuple, .srp-jobtuple-wrapper, .job-tuple").all()
            for c in cards[:10]:
                try:
                    title = c.locator("a.title").first.inner_text().strip() if c.locator("a.title").count() > 0 else ""
                    comp = c.locator("a.comp-name, .comp-name-link").first.inner_text().strip() if c.locator("a.comp-name, .comp-name-link").count() > 0 else ""
                    loc = c.locator(".loc-wrap, span[class*='loc']").first.inner_text().strip() if c.locator(".loc-wrap, span[class*='loc']").count() > 0 else ""
                    href = c.locator("a.title").first.get_attribute("href") if c.locator("a.title").count() > 0 else ""
                    if title and href:
                        hidden_jobs.append({
                            "title": title,
                            "company": comp,
                            "location": loc,
                            "source": "Naukri AI Match Feed",
                            "is_gcc": any(gcc.lower() in comp.lower() for gcc in TARGET_GCCS),
                            "url": href
                        })
                except Exception:
                    continue
        except Exception as e:
            logger.warning("Recommended feed notice: %s", e)

        # 2. Scrape GCC Dedicated Direct Openings in Hyderabad & Bangalore
        for gcc in TARGET_GCCS[:3]:
            url = f"https://www.naukri.com/{gcc.lower().replace(' ', '-')}-jobs-in-hyderabad"
            try:
                page.goto(url, wait_until="networkidle", timeout=25000)
                time.sleep(2)
                cards = page.locator("article.jobTuple, .cust-job-tuple, .srp-jobtuple-wrapper").all()
                for c in cards[:2]:
                    title = c.locator("a.title").first.inner_text().strip() if c.locator("a.title").count() > 0 else ""
                    href = c.locator("a.title").first.get_attribute("href") if c.locator("a.title").count() > 0 else ""
                    if title and href and any(k in title.lower() for k in ["data", "cloud", "platform", "devops", "engineer"]):
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

        logger.info("Discovered %d hidden/stealth opportunities.", len(hidden_jobs))
        return hidden_jobs
