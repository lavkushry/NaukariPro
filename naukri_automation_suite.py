#!/usr/bin/env python3
"""
Naukri Automation Suite (Legacy Entrypoint)
Consolidated into the unified naukari_pro package.
Delegates all CLI invocations directly to naukari_pro.cli.main() so bug fixes land in one place.
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import logging
from naukari_pro.cli import main

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logging.info("[CONSOLIDATED] naukri_automation_suite.py is delegating to naukari_pro...")
    main()
