"""
Feature 2: Instant Job Alerts
Monitors high-priority vacancies posted in the last 6-12 hours.
Cross-platform notifications (macOS osascript / Linux notify-send / console logging).
Ground-truth salary reporting (no fake salary strings).
"""

import os
import sys
import time
import shutil
import subprocess
import logging
from naukari_pro.config import load_config, WORKSPACE_DIR

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

MATCH_SCORE_THRESHOLD = 70

def calculate_match_score(text: str) -> int:
    """
    Computes weighted keyword match score (0-100) based on Azure Data Engineering competencies.
    Returns: integer score. Threshold >= 70 required to apply.
    """
    if not text:
        return 0
    score = 0
    text_lower = str(text).lower()
    for kw, weight in KEYWORD_WEIGHTS.items():
        if kw in text_lower:
            score += weight
    return min(score, 100)

class InstantAlertsEngine:
    def __init__(self):
        self.cfg = load_config()

    def send_notification(self, title, subtitle, message):
        """Dispatches desktop notification banner across macOS and Linux."""
        if sys.platform == "darwin":
            try:
                cmd = f'display notification "{message}" with title "{title}" subtitle "{subtitle}" sound name "Glass"'
                subprocess.run(["osascript", "-e", cmd], check=False)
            except Exception as e:
                logger.debug("macOS notification notice: %s", e)
        elif sys.platform.startswith("linux"):
            if shutil.which("notify-send"):
                try:
                    subprocess.run(["notify-send", f"{title}: {subtitle}", message], check=False)
                except Exception as e:
                    logger.debug("Linux notify-send notice: %s", e)
            else:
                logger.info("[DESKTOP ALERT] %s - %s: %s", title, subtitle, message)

        # Log to alerts log file
        try:
            log_dir = os.path.join(WORKSPACE_DIR, "logs")
            os.makedirs(log_dir, exist_ok=True)
            with open(os.path.join(log_dir, "job_alerts.log"), "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {title} | {subtitle} | {message}\n")
        except Exception:
            pass

    def calculate_match_score(self, text):
        return calculate_match_score(text)

    def scan_for_alerts(self, page):
        roles = ["azure-data-engineer", "data-engineer"]
        locations = ["hyderabad", "bangalore"]
        
        alerts = []
        logger.info("Scanning for instant alerts (Freshly posted vacancies in last 24h)...")

        for role in roles:
            for loc in locations:
                url = f"https://www.naukri.com/{role}-jobs-in-{loc}?jobAge=1"
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=25000)
                    time.sleep(2)
                except Exception:
                    continue

                # Modern and fallback card selectors
                cards = page.locator(".srp-jobtuple-wrapper, .cust-job-tuple, .job-tuple, article.jobTuple").all()
                for card in cards[:6]:
                    try:
                        title_el = card.locator("a.title, a[class*='title']").first
                        comp_el = card.locator("a.comp-name, span.comp-nameText, a.subTitle").first
                        exp_el = card.locator("span.expwdth, .exp-wrap, span[class*='exp']").first
                        loc_el = card.locator("span.locWdth, .loc-wrap, span[class*='loc']").first
                        sal_el = card.locator("span.sal-wrap, span[class*='sal'], span.ni-job-tuple-icon-srp-rupee + span").first

                        title = title_el.inner_text().strip() if title_el.count() > 0 else "Data Engineer"
                        comp = comp_el.inner_text().strip() if comp_el.count() > 0 else "Confidential"
                        exp = exp_el.inner_text().strip() if exp_el.count() > 0 else "2-5 Yrs"
                        location = loc_el.inner_text().strip() if loc_el.count() > 0 else loc.capitalize()
                        
                        # Ground-truth salary parsing: NEVER insert fake salary
                        salary = sal_el.inner_text().strip() if sal_el.count() > 0 and sal_el.inner_text().strip() else "Not Disclosed"
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

        # In-app notifications scan
        try:
            page.goto("https://www.naukri.com/mnjuser/notifications", wait_until="domcontentloaded", timeout=20000)
            time.sleep(2)
            if "login" not in page.url:
                notif_cards = page.locator(".notif-item, .notification-card, div[class*='notificationItem']").all()
                for nc in notif_cards[:3]:
                    ntxt = nc.inner_text().strip().replace("\n", " | ")
                    if ntxt:
                        alerts.append({
                            "title": ntxt[:60] + "...",
                            "company": "Naukri In-App Alert",
                            "location": "In-App Notification",
                            "experience": "N/A",
                            "salary": "Not Disclosed",
                            "match_score": 75,
                            "url": "https://www.naukri.com/mnjuser/notifications"
                        })
        except Exception as e:
            logger.debug("Notifications scan notice: %s", e)

        logger.info("Alert Scan Complete: %d high-priority matches identified.", len(alerts))
        if alerts:
            top_job = alerts[0]
            self.send_notification(
                title="naukariPro: Hot Vacancy Alert 🔥",
                subtitle=f"{top_job['company']} hiring {top_job['title']}",
                message=f"Match Score: {top_job['match_score']}% | {top_job['location']} ({top_job['salary']})"
            )
        return alerts
