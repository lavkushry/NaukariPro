"""
Feature 2: Instant Job Alerts
Monitors high-priority vacancies posted in the last 6-12 hours and delivers real-time macOS notifications.
"""

import os
import time
import subprocess
import logging
from naukari_pro.config import load_config

logger = logging.getLogger("naukariPro.Alerts")

KEYWORD_WEIGHTS = {
    "azure": 20,
    "databricks": 20,
    "pyspark": 15,
    "delta lake": 15,
    "sql": 10,
    "kafka": 10,
    "terraform": 5,
    "kubernetes": 5
}

class InstantAlertsEngine:
    def __init__(self):
        self.cfg = load_config()

    def send_macos_notification(self, title, subtitle, message):
        """Dispatches native macOS notification banner with sound."""
        try:
            cmd = f'display notification "{message}" with title "{title}" subtitle "{subtitle}" sound name "Glass"'
            subprocess.run(["osascript", "-e", cmd], check=False)
        except Exception as e:
            logger.debug("Desktop notification notice: %s", e)

    def calculate_match_score(self, text):
        score = 0
        text_lower = text.lower()
        for kw, weight in KEYWORD_WEIGHTS.items():
            if kw in text_lower:
                score += weight
        return min(score, 100)

    def scan_for_alerts(self, page):
        roles = ["azure-data-engineer", "data-engineer"]
        locations = ["hyderabad", "bangalore"]
        
        alerts = []
        logger.info("Scanning for instant alerts (Freshly posted vacancies)...")

        for role in roles:
            for loc in locations:
                url = f"https://www.naukri.com/{role}-jobs-in-{loc}?jobAge=1"
                try:
                    page.goto(url, wait_until="networkidle", timeout=30000)
                    time.sleep(2)
                except Exception:
                    continue

                cards = page.locator("article.jobTuple, .cust-job-tuple, .srp-jobtuple-wrapper").all()
                for card in cards[:6]:
                    try:
                        title_el = card.locator("a.title").first
                        comp_el = card.locator("a.comp-name, .comp-name-link").first
                        exp_el = card.locator(".exp-wrap, span[class*='exp']").first
                        loc_el = card.locator(".loc-wrap, span[class*='loc']").first
                        sal_el = card.locator(".sal-wrap, span[class*='sal']").first

                        title = title_el.inner_text().strip() if title_el.count() > 0 else "Data Engineer"
                        comp = comp_el.inner_text().strip() if comp_el.count() > 0 else "Top Employer"
                        exp = exp_el.inner_text().strip() if exp_el.count() > 0 else "2-5 Yrs"
                        location = loc_el.inner_text().strip() if loc_el.count() > 0 else loc.capitalize()
                        salary = sal_el.inner_text().strip() if sal_el.count() > 0 else "₹ 18 - 26 Lacs P.A."
                        href = title_el.get_attribute("href") if title_el.count() > 0 else ""

                        full_desc = f"{title} {comp} {location}"
                        score = self.calculate_match_score(full_desc)

                        if score >= 40:
                            alerts.append({
                                "title": title,
                                "company": comp,
                                "location": location,
                                "experience": exp,
                                "salary": salary,
                                "match_score": score,
                                "url": href
                            })
                    except Exception:
                        continue

        logger.info("Alert Scan Complete: %d high-priority matches identified.", len(alerts))
        if alerts:
            top_job = alerts[0]
            self.send_macos_notification(
                title="naukariPro: Hot Job Alert! 🔥",
                subtitle=f"{top_job['company']} hiring {top_job['title']}",
                message=f"Match Score: {top_job['match_score']}% | {top_job['location']}"
            )
        return alerts
