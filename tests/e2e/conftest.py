"""conftest.py for NaukariPro 4-Pillar Autonomous Platform E2E Test Suite.

Provides mock fixtures, isolated test SQLite databases, candidate fact matrix
ground truth fixtures, and helper utilities.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List
import pytest

from naukari_pro.aggregation.models import NormalizedJob
from naukari_pro.aggregation.storage import AggregationStore
from naukari_pro.governed_apply.approval import ApprovalQueue
from naukari_pro.llm.gateway import LLMGateway
from naukari_pro.llm.ledger import SpendLedger
from naukari_pro.tracking.store import TrackingStore


# Ground truth candidate facts strictly derived from AGENTS.md & 01_FACT_MATRIX.md
CANDIDATE_FACTS: Dict[str, Any] = {
    "name": "Lavkush Kumar",
    "target_role": "Azure Data Engineer / MLOps Platform Engineer",
    "summary": "DevOps Engineer at CGI India with 2.5 YOE specializing in Azure data platforms, Databricks, PySpark, Terraform, and Kubernetes infrastructure.",
    "skills": [
        "Python", "SQL", "Azure", "Databricks", "PySpark", "Delta Lake",
        "Terraform", "Docker", "Kubernetes", "CI/CD", "ADF", "Airflow",
        "MLflow", "Prometheus", "Grafana", "Git", "Bash", "Linux",
    ],
    "titles": [
        "DevOps Engineer",
        "Engineer 1 — DevOps / Platform Engineering",
        "Security Analyst Apprentice",
        "Full Stack Developer Intern",
        "Azure Data Engineer",
    ],
    "yoe": 2.5,
    "seniority": "mid",
    "location": "Bengaluru, Karnataka, India",
    "work_authorization": "India",
    "experience": [
        {
            "title": "DevOps Engineer",
            "company": "CGI India",
            "dates": "Jun 2026 – Present",
            "bullets": [
                "Automated CI/CD for 5 Azure services cutting deployment cycle time from 45m to 12m.",
                "Instrumented Databricks lakehouse pipelines with Prometheus & Grafana alerting, sustaining 99.5% uptime.",
                "Provisioned multi-environment Terraform modules across dev, stage, and prod with zero drift.",
            ],
        },
        {
            "title": "Engineer 1 — DevOps / Platform Engineering",
            "company": "HFCL Limited",
            "dates": "Aug 2025 – Jun 2026",
            "bullets": [
                "Containerized internal microservices with Docker, accelerating dev onboarding and build speeds 2x.",
                "Managed cloud networking and security posture across private cloud deployments.",
            ],
        },
        {
            "title": "Security Analyst Apprentice",
            "company": "CGI India",
            "dates": "Sep 2024 – Aug 2025",
            "bullets": [
                "Audited IAM roles, secrets rotation, and vulnerability remediation across platform services.",
            ],
        },
        {
            "title": "Full Stack Developer Intern",
            "company": "Stipe Solutions",
            "dates": "Mar 2024 – Sep 2024",
            "bullets": [
                "Engineered responsive web interfaces and REST APIs using Python and modern frontend frameworks.",
            ],
        },
    ],
    "projects": [
        {
            "name": "AegisAgent",
            "description": "Autonomous governance engine for AI agent workflows with policy enforcement and token spend controls.",
            "technologies": ["Python", "FastAPI", "SQLite", "Docker"],
            "url": "https://github.com/lavkushkumar/AegisAgent",
        },
        {
            "name": "Vulcan",
            "description": "High-throughput data streaming and ETL pipeline benchmarked on Azure Databricks and Delta Lake.",
            "technologies": ["PySpark", "Delta Lake", "Azure Databricks", "Terraform"],
            "url": "https://github.com/lavkushkumar/Vulcan",
        },
    ],
    "education": [
        {
            "degree": "B.Tech in Computer Science and Engineering",
            "school": "APJ Abdul Kalam Technical University",
            "year": "2024",
        }
    ],
    "certifications": [
        {"name": "Microsoft Certified: Azure Data Fundamentals (DP-900)"},
        {"name": "HashiCorp Certified: Terraform Associate"},
    ],
}

CANDIDATE_CONTACT: Dict[str, Any] = {
    "name": "Lavkush Kumar",
    "email": "lavkush.career@example.com",
    "phone": "+91-9876543210",
    "location": "Bengaluru, Karnataka, India",
    "linkedin": "https://linkedin.com/in/lavkush-kumar",
    "github": "https://github.com/lavkushkumar",
    "work_authorization": "India",
    "notice_period_days": 30,
    "current_ctc_lpa": 12.0,
    "expected_ctc_lpa": 25.0,
}


@pytest.fixture
def candidate_facts() -> Dict[str, Any]:
    return dict(CANDIDATE_FACTS)


@pytest.fixture
def candidate_contact() -> Dict[str, Any]:
    return dict(CANDIDATE_CONTACT)


@pytest.fixture
def temp_agg_store(tmp_path: Path) -> AggregationStore:
    db_file = tmp_path / "test_agg.db"
    return AggregationStore(db_path=db_file)


@pytest.fixture
def temp_tracking_store(tmp_path: Path) -> TrackingStore:
    db_file = tmp_path / "test_tracking.db"
    return TrackingStore(db_path=db_file)


@pytest.fixture
def temp_approval_queue(tmp_path: Path) -> ApprovalQueue:
    db_file = tmp_path / "test_governed.db"
    return ApprovalQueue(db_path=db_file)


@pytest.fixture
def temp_spend_ledger(tmp_path: Path) -> SpendLedger:
    ledger_file = tmp_path / "test_spend.jsonl"
    return SpendLedger(
        path=ledger_file,
        monthly_cap_usd=25.0,
        alert_at_usd=20.0,
        enable_sqlite=False,
    )


@pytest.fixture
def sample_jobs_across_ats() -> List[NormalizedJob]:
    """Sample jobs covering all 12 ATS platforms with honest metadata."""
    ats_list = [
        ("greenhouse", "https://boards.greenhouse.io/gitlab/jobs/101", "GitLab"),
        ("ashby", "https://jobs.ashbyhq.com/reddit/jobs/102", "Reddit"),
        ("lever", "https://jobs.lever.co/netflix/103", "Netflix"),
        ("workday", "https://myworkdayjobs.com/adobe/jobs/104", "Adobe"),
        ("smartrecruiters", "https://jobs.smartrecruiters.com/visa/105", "Visa"),
        ("workable", "https://apply.workable.com/spotify/j/106", "Spotify"),
        ("recruitee", "https://careers.recruitee.com/stripe/107", "Stripe"),
        ("teamtailor", "https://career.teamtailor.com/uber/108", "Uber"),
        ("pinpoint", "https://pinpointhq.com/atlassian/109", "Atlassian"),
        ("bamboohr", "https://bamboohr.com/databricks/110", "Databricks"),
        ("icims", "https://careers-icims.com/salesforce/111", "Salesforce"),
        ("keka", "https://keka.com/razorpay/112", "Razorpay"),
    ]
    jobs: List[NormalizedJob] = []
    for i, (ats, url, co) in enumerate(ats_list, start=1):
        jobs.append(
            NormalizedJob(
                external_job_id=str(100 + i),
                source_id=f"{ats}:{co.lower()}",
                company=co,
                title=f"Azure Data Engineer ({co})",
                url=url,
                location="Bengaluru / Remote",
                remote=True,
                description_full=f"We are hiring an Azure Data Engineer at {co}. Required skills: Python, Databricks, PySpark, SQL, Azure, and Terraform. 2+ years of experience required.",
                departments=["Data Platform", "Engineering"],
                employment_type="Full-time",
                ats_type=ats,
                salary=None,  # Honest metadata: null unless fetched
                experience_required=None,
            )
        )
    return jobs
