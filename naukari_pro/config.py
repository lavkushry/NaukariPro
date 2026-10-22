"""
naukariPro Configuration Module
Handles candidate facts, search preferences, paths, and screening answers.
"""

import os
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACKER_PATH = os.path.join(BASE_DIR, "Naukri_Live_Application_Tracker.xlsx")
RESUME_PDF_PATH = os.path.join(BASE_DIR, "Lavkush_Kumar_Azure_Data_Engineer_Resume.pdf")
COOKIES_SEED_PATH = os.path.join(BASE_DIR, "naukri_system", "cookies_seed.json")
SESSION_DIR = os.path.expanduser("~/.naukri_system_profile")
LOG_PATH = os.path.expanduser("~/naukari_pro.log")

CONFIG_FILE = os.path.join(BASE_DIR, "naukri_system", "config.json")

DEFAULT_CONFIG = {
    "candidate": {
        "name": "Lavkush Kumar",
        "email": "lavkushry@gmail.com",
        "phone": "9122036484",
        "current_company": "CGI",
        "current_designation": "DevOps Engineer",
        "current_ctc_lakhs": 12,
        "expected_ctc_lakhs": 25,
        "total_experience_years": 2.5,
        "notice_period_days": 30,
        "primary_location": "Hyderabad",
        "resume_path": RESUME_PDF_PATH
    },
    "search_settings": {
        "roles": [
            "azure-data-engineer",
            "data-engineer",
            "databricks-engineer",
            "devops-engineer"
        ],
        "locations": [
            "hyderabad",
            "bangalore",
            "pune",
            "remote"
        ],
        "max_experience": 4,
        "posted_within_days": 1,
        "daily_application_limit": 20
    },
    "answers_to_common_questions": {
        "experience": "2.5",
        "pyspark_experience": "2",
        "databricks_experience": "2",
        "azure_experience": "2.5",
        "sql_experience": "2.5",
        "kubernetes_experience": "2.5",
        "terraform_experience": "2",
        "notice_period": "30 days",
        "current_location": "Hyderabad",
        "relocation": "Yes"
    },
    "headline_template": "Azure Data Engineer | Azure Databricks · PySpark · Delta Lake · Azure Data Factory (ADF) · SQL · Apache Kafka · Terraform · Medallion Architecture | Certified AZ-900 · Databricks Associate (Pursuing) | 2.5 YOE Cloud Data Platforms & CI/CD",
    "tracker_excel_path": TRACKER_PATH
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                cfg = json.load(f)
                return cfg
        except Exception:
            pass
    return DEFAULT_CONFIG
