#!/usr/bin/env python3
"""
Naukri Autonomous Job Application & Profile Management System (Legacy Wrapper)
Consolidated into the unified naukari_pro package to ensure a single source of truth
for browser sessions, stealth scripts, cookie profiles, and Excel trackers.
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import logging
from naukari_pro.config import load_config, TRACKER_PATH, SESSION_DIR
from naukari_pro.session import get_stealth_context, ensure_authenticated
from naukari_pro.modules.profile_enhancer import ProfileEnhancerEngine
from naukari_pro.modules.auto_apply import AutoApplyEngine
from naukari_pro.modules.job_alerts import InstantAlertsEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("NaukriSystem.LegacyWrapper")

class NaukriAutomationSystem:
    def __init__(self, config_path=None):
        logger.info("[CONSOLIDATED] NaukriAutomationSystem is delegating to unified naukari_pro architecture.")
        self.cfg = load_config()
        self.profile_engine = ProfileEnhancerEngine()
        self.apply_engine = AutoApplyEngine()
        self.alerts_engine = InstantAlertsEngine()

    def get_browser_context(self, playwright, headless=False):
        return get_stealth_context(playwright, headless=headless)

    def bump_profile(self, page):
        return self.profile_engine.bump_profile(page)

    def scan_and_export_jobs(self, page, keywords=None, limit=50):
        return self.alerts_engine.scan_for_alerts(page)

    def auto_apply(self, page, limit=20, dry_run=False):
        return self.apply_engine.run(page=page, limit=limit, dry_run=dry_run)

    def run_daily_cycle(self, headless=False, dry_run=False):
        from naukari_pro.cli import handle_daily_cycle
        return handle_daily_cycle(headless=headless, dry_run=dry_run)

def main():
    logger.info("[CONSOLIDATED] naukri_system/engine.py is delegating to naukari_pro.cli.main()...")
    from naukari_pro.cli import main as cli_main
    cli_main()

if __name__ == "__main__":
    main()
