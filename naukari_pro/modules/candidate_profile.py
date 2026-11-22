"""
Hybrid candidate profile for ONE BEAST SYSTEM.

Market surface: Platform, DevOps & MLOps Infrastructure Engineer (~2.5 YOE).
Official employment titles/dates: 01_FACT_MATRIX.md & AGENTS.md §9 only.
AI/ML/Data project metrics: verified public GitHub repositories only — never CGI employment.
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

TARGET_TITLE = "Platform & MLOps Engineer"

PROJECT_PROOF_POINTS = {
    "project": "AegisAgent | Vulcan | Azure-Data-Engineering-Medallion-Lakehouse-Project",
    "projects": [
        {
            "name": "AegisAgent",
            "url": "https://github.com/lavkushry/AegisAgent",
            "stack": "Rust, Cedar Policy Engine, Kubernetes, Helm, Docker, GitHub Actions",
            "summary": "Zero-trust AI agent security gateway with sub-75ms Cedar ABAC evaluation and Helm charts.",
        },
        {
            "name": "vulcan",
            "url": "https://github.com/lavkushry/vulcan",
            "stack": "Python, FastAPI, pgvector, Redis Redlock, MinIO S3, WebSockets, Ansible",
            "summary": "Enterprise automation control plane with pgvector HNSW retrieval (<2 min diagnostics).",
        },
        {
            "name": "Azure-Data-Engineering-Medallion-Lakehouse-Project",
            "url": "https://github.com/lavkushry/Azure-Data-Engineering-Medallion-Lakehouse-Project",
            "stack": "PySpark, Azure Databricks, Delta Lake, Azure Data Factory, ADLS Gen2, SQL",
            "summary": "Medallion Lakehouse (Bronze/Silver/Gold) cutting batch ETL runtime by 35%.",
        },
    ],
    "stack": "Kubernetes, Terraform, Ansible, Python, Rust, FastAPI, pgvector, PySpark, Databricks, Delta Lake",
    "metrics": [
        "AegisAgent (github.com/lavkushry/AegisAgent): Rust/Cedar zero-trust AI agent gateway with <75ms ABAC policy evaluation",
        "Project Vulcan (github.com/lavkushry/vulcan): FastAPI + Redis Redlock + pgvector HNSW control plane (<2 min SRE diagnostics)",
        "Azure-Data-Engineering-Medallion-Lakehouse-Project (github.com/lavkushry/Azure-Data-Engineering-Medallion-Lakehouse-Project): PySpark/Databricks/Delta Lakehouse cutting batch ETL runtime by 35%",
    ],
    "one_liner": (
        "Projects: AegisAgent (github.com/lavkushry/AegisAgent, Rust/Cedar/K8s <75ms), "
        "Vulcan (github.com/lavkushry/vulcan, FastAPI/pgvector/Redis), "
        "Medallion Lakehouse (github.com/lavkushry/Azure-Data-Engineering-Medallion-Lakehouse-Project, PySpark/Databricks/Delta, 35% ETL cut)"
    ),
}

OFFICIAL_WORK_HISTORY = [
    {
        "company": "CGI India",
        "title": "DevOps Engineer",
        "startDate": "2026-06",
        "endDate": None,
        "current": True,
        "duration": "Jun 2026 – Present",
        "location": "Bangalore, India",
        "description": (
            "Standardized multi-tenant AWS EKS container platform deployments using modular Terraform and Ansible, "
            "engineered Jenkins/GitLab CI pipelines with Trivy security scanning, hardened Nginx/Kong ingress "
            "policies, and automated GitOps rollouts with ArgoCD and Helm charts."
        ),
    },
    {
        "company": "HFCL Limited",
        "title": "Engineer 1 — DevOps / Platform Engineering",
        "startDate": "2025-08",
        "endDate": "2026-06",
        "current": False,
        "duration": "Aug 2025 – Jun 2026",
        "location": "Bangalore, India",
        "description": (
            "Automated 50-node bare-metal kubeadm Kubernetes lifecycle via 40+ Ansible roles (2 days -> 4 hours "
            "bootstrap, 83%), sustained 99.95% availability across 15+ microservices, orchestrated Kafka/Redis/"
            "PostgreSQL/TimescaleDB/MongoDB StatefulSets with Velero DR (RTO 8h -> 30min, MTTR -45%), and "
            "doubled Jenkins/Helm/Trivy release frequency (2x)."
        ),
    },
    {
        "company": "CGI India",
        "title": "Security Analyst Apprentice",
        "startDate": "2024-09",
        "endDate": "2025-08",
        "current": False,
        "duration": "Sep 2024 – Aug 2025",
        "location": "Bangalore, India",
        "description": (
            "Centralized multi-source log ingestion using ELK Stack (Elasticsearch, Logstash, Kibana) and authored "
            "custom Grok patterns for firewall/IDS/endpoint syslog, cutting root-cause investigation time by 35% "
            "and log triage time by 45%."
        ),
    },
    {
        "company": "Stipe Solutions",
        "title": "Full Stack Developer Intern",
        "startDate": "2024-03",
        "endDate": "2024-09",
        "current": False,
        "duration": "Mar 2024 – Sep 2024",
        "location": "Bangalore, India",
        "description": (
            "Developed 30+ cross-platform mobile screens (React Native, Flutter) and REST API integrations with "
            "PostgreSQL optimization for 1,000+ daily active users."
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
    "linkedInUrl": "https://www.linkedin.com/in/lavkushry/",
    "githubUrl": "https://github.com/lavkushry",
    "portfolioUrl": "https://github.com/lavkushry",
    "experienceYears": "2.5",
    "noticePeriodDays": "15",
    "currentCtcLpa": "12",
    "expectedCtcLpa": "25",
    "expectedCtcBand": "20-25",
    "resumePath": RESUME_PDF_PATH,
    "targetTitle": TARGET_TITLE,
    "skills": [
        "Kubernetes",
        "Docker",
        "Terraform",
        "Ansible",
        "Helm",
        "ArgoCD",
        "AWS EKS",
        "CI/CD",
        "Jenkins",
        "GitLab CI",
        "GitHub Actions",
        "Trivy",
        "SonarQube",
        "Prometheus",
        "Grafana",
        "Alertmanager",
        "ELK Stack",
        "Elasticsearch",
        "Logstash",
        "Kibana",
        "Velero",
        "Harbor Registry",
        "Nginx Ingress",
        "Kong Gateway",
        "containerd",
        "Apache Kafka",
        "Redis",
        "PostgreSQL",
        "TimescaleDB",
        "MongoDB",
        "pgvector",
        "MinIO",
        "Python",
        "Rust",
        "FastAPI",
        "SQL",
        "Bash",
        "Linux",
        "YAML",
        "Jinja2",
        "PySpark",
        "Azure Databricks",
        "Delta Lake",
        "Azure Data Factory",
        "ADLS Gen2",
        "MLflow",
        "MLOps",
        "GitOps",
        "Site Reliability Engineering",
        "Infrastructure as Code (IaC)",
    ],
    "currentCompany": "CGI India",
    "currentTitle": "DevOps Engineer",
    "marketTitle": TARGET_TITLE,
    "workHistory": OFFICIAL_WORK_HISTORY,
    "projectProofPoints": PROJECT_PROOF_POINTS,
    "education": [
        {
            "degree": "B.Tech in Computer Science and Engineering",
            "institution": "World College of Technology and Management (MDU, Rohtak)",
            "field": "Computer Science and Engineering",
            "startDate": "2020-06",
            "endDate": "2023-05",
            "dates": "2020 – 2023",
        },
        {
            "degree": "Diploma in Computer Science Engineering",
            "institution": "Government Polytechnic, Patna-7",
            "field": "Computer Science Engineering",
            "startDate": "2016-07",
            "endDate": "2019-06",
            "dates": "2016 – 2019",
        },
    ],
    "outreachOpener": (
        f"Platform & MLOps Engineer | 2.5 YOE | 15-day notice | ₹20–25 LPA | "
        f"{PROJECT_PROOF_POINTS['one_liner']}"
    ),
    "factMatrixPath": str(FACT_MATRIX_PATH),
}


def _normalize_url(val: str) -> str:
    s = (val or "").strip()
    if not s:
        return ""
    if not s.startswith(("http://", "https://")):
        return f"https://{s.lstrip('/')}"
    return s


def _env_override(data: Dict[str, Any]) -> Dict[str, Any]:
    """Apply explicit .env overrides without inventing employment claims."""
    mapping = {
        "CANDIDATE_CITY": "city",
        "CANDIDATE_LOCATION": "city",
        "CANDIDATE_STATE": "state",
        "CANDIDATE_PHONE": "phone",
        "CANDIDATE_EMAIL": "email",
        "CANDIDATE_LINKEDIN": "linkedInUrl",
        "CANDIDATE_GITHUB": "githubUrl",
        "CANDIDATE_PORTFOLIO": "portfolioUrl",
        "NOTICE_PERIOD": "noticePeriodDays",
        "CURRENT_CTC": "currentCtcLpa",
        "EXPECTED_CTC": "expectedCtcLpa",
        "TOTAL_EXPERIENCE": "experienceYears",
    }
    for env_key, field in mapping.items():
        val = os.environ.get(env_key)
        if val:
            cleaned = val.strip()
            if field in ("linkedInUrl", "githubUrl", "portfolioUrl"):
                cleaned = _normalize_url(cleaned)
            elif field == "city" and "," in cleaned:
                cleaned = cleaned.split(",")[0].strip()
            data[field] = cleaned
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
                "githubUrl", "portfolioUrl", "resumePath", "applicantEmail", "zip",
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
