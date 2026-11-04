"""
Hybrid candidate profile for ONE BEAST SYSTEM.

Market surface: Azure Data Engineer (headline, search, outreach opener).
Official employment titles/dates: 01_FACT_MATRIX.md only.
Lakehouse / Delta / ETL metrics: project proof only — never CGI employment.
"""

from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional

from naukari_pro.config import RESUME_PDF_PATH, WORKSPACE_DIR

PROFILE_PATH = Path.home() / ".job-apply" / "profile.json"
FACT_MATRIX_PATH = Path(WORKSPACE_DIR) / "01_FACT_MATRIX.md"

TARGET_TITLE = "Azure Data Engineer"

PROJECT_PROOF_POINTS = {
    "project": "Azure-Data-Engineering-Medallion-Lakehouse-Project",
    "stack": "Azure Databricks, PySpark, Delta Lake, ADF, Kafka, SQL, ADLS Gen2, Terraform",
    "metrics": [
        "Medallion Lakehouse processing 2M+ events/day into Bronze/Silver/Gold Delta tables",
        "35% ETL runtime reduction via Spark SQL optimizations",
        "99.95% platform availability on lakehouse pipelines (project benchmark)",
    ],
    "one_liner": (
        "Project: Medallion Lakehouse on Azure Databricks/PySpark/Delta — "
        "2M+ events/day, 35% ETL runtime cut"
    ),
}

OFFICIAL_WORK_HISTORY = [
    {
        "company": "CGI India (PNC Bank GCC)",
        "title": "DevOps Engineer",
        "startDate": "2026-06",
        "endDate": None,
        "current": True,
        "duration": "Jun 2026 – Present",
        "location": "Bangalore, India",
        "description": (
            "Standardized AWS EKS container platform deployments using Terraform and Ansible, "
            "established multi-tenant cluster baselines, and hardened ingress/API gateway policies "
            "with Nginx Ingress and Kong. Automated GitOps sync with ArgoCD and Helm."
        ),
    },
    {
        "company": "HFCL Limited",
        "title": "Engineer 1 — DevOps / Platform Engineering",
        "startDate": "2025-08",
        "endDate": "2026-06",
        "current": False,
        "duration": "Aug 2025 – Jun 2026",
        "location": "Gurugram / Bangalore",
        "description": (
            "Orchestrated stateful distributed data backbones (Apache Kafka, Redis, PostgreSQL/"
            "TimescaleDB, MongoDB) on a 50-node Kubernetes platform via StatefulSets, cutting RTO "
            "from 8h to 30min and MTTR by 45%. Authored 40+ Ansible roles; Jenkins CI/CD with "
            "Docker, Helm, SonarQube, Trivy."
        ),
    },
    {
        "company": "CGI India",
        "title": "Security Analyst Apprentice",
        "startDate": "2024-09",
        "endDate": "2025-08",
        "current": False,
        "duration": "Sep 2024 – Aug 2025",
        "location": "Bangalore",
        "description": (
            "Centralized multi-source log ingestion using ELK Stack; authored Grok patterns for "
            "firewall/IDS/endpoint syslog, cutting root-cause investigation time by 35%."
        ),
    },
    {
        "company": "Stipe Solutions",
        "title": "Full Stack Developer Intern",
        "startDate": "2024-03",
        "endDate": "2024-09",
        "current": False,
        "duration": "Mar 2024 – Sep 2024",
        "location": "Bengaluru",
        "description": (
            "Developed cross-platform mobile modules (React Native, Flutter) and REST API "
            "integrations for 1,000+ daily active users."
        ),
    },
]

DEFAULT_HYBRID_PROFILE: Dict[str, Any] = {
    "firstName": "Lavkush",
    "lastName": "Kumar",
    "fullName": "Lavkush Kumar",
    "email": "lav84095@gmail.com",
    "applicantEmail": "lav84095@gmail.com",
    "phone": "+91-9122036484",
    "city": "Bangalore",
    "state": "Karnataka",
    "country": "India",
    "zip": "560001",
    "linkedInUrl": "https://linkedin.com/in/lavkush-kumar",
    "githubUrl": "https://github.com/lavkush-kumar",
    "portfolioUrl": "https://github.com/lavkush-kumar",
    "experienceYears": "2.5",
    "noticePeriodDays": "15",
    "currentCtcLpa": "12",
    "expectedCtcLpa": "25",
    "expectedCtcBand": "20-25",
    "resumePath": RESUME_PDF_PATH,
    "targetTitle": TARGET_TITLE,
    "skills": [
        "Azure Databricks",
        "PySpark",
        "Azure Data Factory (ADF)",
        "Delta Lake",
        "Apache Spark",
        "Spark SQL",
        "Data Engineering",
        "ETL Pipelines",
        "ELT Pipelines",
        "Data Lakehouse",
        "Medallion Architecture",
        "ADLS Gen2",
        "Azure Synapse Analytics",
        "Microsoft Fabric",
        "Change Data Capture (CDC)",
        "SQL",
        "PostgreSQL",
        "Data Modeling",
        "Star Schema",
        "Snowflake",
        "Redis",
        "MongoDB",
        "Query Optimization",
        "Apache Kafka",
        "Spark Structured Streaming",
        "Event Streaming",
        "Kafka Connect",
        "Azure Event Hubs",
        "Terraform",
        "Infrastructure as Code (IaC)",
        "Azure DevOps",
        "CI/CD",
        "Docker",
        "Kubernetes",
        "Helm",
        "Git",
        "GitHub Actions",
        "GitLab CI",
        "Linux",
        "Bash",
        "Unity Catalog",
        "Great Expectations",
        "Data Quality Gates",
        "Prometheus",
        "Grafana",
        "OpenTelemetry",
        "Data Pipelines Observability",
        "dbt",
        "Cloud Data Management",
        "Python (Programming Language)",
    ],
    "currentCompany": "CGI India (PNC Bank GCC)",
    "currentTitle": "DevOps Engineer",
    "marketTitle": TARGET_TITLE,
    "workHistory": OFFICIAL_WORK_HISTORY,
    "projectProofPoints": PROJECT_PROOF_POINTS,
    "education": [
        {
            "degree": "B.Tech in Computer Science and Engineering",
            "institution": "Maharishi Dayanand University (MDU), Rohtak",
            "field": "Computer Science and Engineering",
            "startDate": "2020-06",
            "endDate": "2023-05",
            "dates": "2020 – 2023",
        }
    ],
    "outreachOpener": (
        f"Azure Data Engineer | 2.5 YOE | 15-day notice | ₹20–25 LPA | "
        f"{PROJECT_PROOF_POINTS['one_liner']}"
    ),
    "factMatrixPath": str(FACT_MATRIX_PATH),
}


def _env_override(data: Dict[str, Any]) -> Dict[str, Any]:
    """Apply explicit .env overrides without inventing employment claims."""
    mapping = {
        "CANDIDATE_CITY": "city",
        "CANDIDATE_STATE": "state",
        "CANDIDATE_PHONE": "phone",
        "CANDIDATE_EMAIL": "email",
        "NOTICE_PERIOD": "noticePeriodDays",
        "CURRENT_CTC": "currentCtcLpa",
        "EXPECTED_CTC": "expectedCtcLpa",
        "TOTAL_EXPERIENCE": "experienceYears",
    }
    for env_key, field in mapping.items():
        val = os.environ.get(env_key)
        if val:
            data[field] = val.strip()
    return data


def load_hybrid_profile(profile_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load hybrid candidate profile.
    Official titles always come from FACT_MATRIX constants; overlays may change
    contact/location/CTC only.
    """
    data = deepcopy(DEFAULT_HYBRID_PROFILE)
    path = profile_path or PROFILE_PATH

    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                doc = json.load(f)
            prof = doc.get("profile", doc)
            for key in (
                "firstName", "lastName", "email", "phone", "linkedInUrl",
                "githubUrl", "resumePath", "applicantEmail", "zip",
            ):
                if prof.get(key):
                    data[key] = prof[key]
            if prof.get("firstName") or prof.get("lastName"):
                data["fullName"] = f"{data['firstName']} {data['lastName']}".strip()
            loc = prof.get("location")
            if isinstance(loc, dict):
                data["city"] = loc.get("city", data["city"])
                data["state"] = loc.get("state", data["state"])
                data["country"] = loc.get("country", data["country"])
            elif isinstance(loc, str) and loc.strip():
                data["city"] = loc.strip()
        except Exception:
            pass

    data = _env_override(data)
    # Never allow overlays to rewrite official employment titles
    data["currentTitle"] = "DevOps Engineer"
    data["workHistory"] = deepcopy(OFFICIAL_WORK_HISTORY)
    data["targetTitle"] = TARGET_TITLE
    data["marketTitle"] = TARGET_TITLE
    data["projectProofPoints"] = deepcopy(PROJECT_PROOF_POINTS)
    return data


def official_title_for_company(company: str) -> Optional[str]:
    c = (company or "").lower()
    for row in OFFICIAL_WORK_HISTORY:
        if row["company"].split("(")[0].strip().lower() in c or c in row["company"].lower():
            return row["title"]
    return None


def project_proof_blurb() -> str:
    return PROJECT_PROOF_POINTS["one_liner"]
