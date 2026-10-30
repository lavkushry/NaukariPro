"""
naukariPro Configuration Module
Single source of truth for candidate facts, credentials (.env), screening answers, and paths.
"""

import os
import json
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKSPACE_DIR = os.getenv("WORKSPACE_DIR") or BASE_DIR

# 1. Load .env once right at import
ENV_PATH = os.getenv("ENV_PATH") or os.path.join(WORKSPACE_DIR, ".env")
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH, override=False)

# 2. Canonical File Paths
TRACKER_PATH = os.path.join(BASE_DIR, "Naukri_Live_Application_Tracker.xlsx")
RESUME_PDF_PATH = os.path.join(BASE_DIR, "Lavkush_Kumar_Azure_Data_Engineer_Resume.pdf")
COOKIES_SEED_PATH = os.path.join(BASE_DIR, "naukri_system", "cookies_seed.json")
SESSION_DIR = os.path.join(BASE_DIR, "naukri_system", "browser_session")
LOG_PATH = os.path.expanduser("~/naukari_pro.log")
CONFIG_FILE = os.path.join(BASE_DIR, "naukri_system", "config.json")
CONFIG_PATH = CONFIG_FILE

def load_config():
    """
    Loads unified configuration from naukri_system/config.json and overlays .env values.
    Ensures candidate facts, screening answers, and search settings stay 100% in sync.
    """
    cfg = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}

    candidate = cfg.setdefault("candidate", {})
    search_settings = cfg.setdefault("search_settings", {})
    common_answers = cfg.setdefault("answers_to_common_questions", {})

    # Overlay environment variables from .env if present
    if os.getenv("NAUKRI_EMAIL"):
        candidate["email"] = os.getenv("NAUKRI_EMAIL")
    if os.getenv("TOTAL_EXPERIENCE"):
        try:
            candidate["total_experience_years"] = float(os.getenv("TOTAL_EXPERIENCE"))
        except ValueError:
            pass
    if os.getenv("CURRENT_CTC"):
        try:
            candidate["current_ctc_lakhs"] = float(os.getenv("CURRENT_CTC"))
        except ValueError:
            pass
    if os.getenv("EXPECTED_CTC"):
        try:
            candidate["expected_ctc_lakhs"] = float(os.getenv("EXPECTED_CTC"))
        except ValueError:
            pass
    if os.getenv("NOTICE_PERIOD"):
        try:
            candidate["notice_period_days"] = int(os.getenv("NOTICE_PERIOD"))
        except ValueError:
            pass
    if os.getenv("MIN_SALARY_LPA"):
        try:
            search_settings["min_salary_lpa"] = float(os.getenv("MIN_SALARY_LPA"))
        except ValueError:
            pass
    if os.getenv("DAILY_APPLICATION_LIMIT"):
        try:
            search_settings["daily_application_limit"] = int(os.getenv("DAILY_APPLICATION_LIMIT"))
        except ValueError:
            pass
    if os.getenv("MIN_MATCH_SCORE"):
        try:
            search_settings["min_match_score"] = float(os.getenv("MIN_MATCH_SCORE"))
        except ValueError:
            pass
    elif "min_match_score" not in search_settings:
        search_settings["min_match_score"] = 80.0

    if os.getenv("LINKEDIN_AUTOMATION_ENABLED") is not None:
        search_settings["linkedin_automation_enabled"] = os.getenv("LINKEDIN_AUTOMATION_ENABLED").lower() in ("true", "1", "yes")
    elif "linkedin_automation_enabled" not in search_settings:
        search_settings["linkedin_automation_enabled"] = False

    # Ensure screening answers are dynamically derived from candidate facts
    tot_exp = str(candidate.get("total_experience_years", "2.5"))
    notice_days = str(candidate.get("notice_period_days", "30"))
    curr_ctc = str(candidate.get("current_ctc_lakhs", "12"))
    exp_ctc = str(candidate.get("expected_ctc_lakhs", "25"))

    common_answers.setdefault("experience", tot_exp)
    common_answers["experience"] = tot_exp
    common_answers.setdefault("notice_period", f"{notice_days} days")
    common_answers["notice_period"] = f"{notice_days} days"
    common_answers.setdefault("current_ctc", curr_ctc)
    common_answers["current_ctc"] = curr_ctc
    common_answers.setdefault("expected_ctc", exp_ctc)
    common_answers["expected_ctc"] = exp_ctc

    # Absolute paths
    if "resume_path" in candidate and not os.path.isabs(candidate["resume_path"]):
        candidate["resume_path"] = os.path.join(BASE_DIR, candidate["resume_path"])
    else:
        candidate["resume_path"] = RESUME_PDF_PATH

    cfg["tracker_excel_path"] = TRACKER_PATH
    return cfg
