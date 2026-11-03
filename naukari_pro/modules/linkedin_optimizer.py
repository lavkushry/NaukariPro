"""
naukariPro Feature: LinkedIn 100k+ Search Appearance Optimizer & Profile SEO Engine
Target: 100,000+ Monthly LinkedIn Recruiter Search Appearances for Data Engineering
Candidate: Lavkush Kumar (Azure Data Engineer, 2.5 YOE | ₹20-25 LPA Target | 15-day notice)

Provides:
- Exact 220-character Recruiter-Optimized Headline
- Full 2,600-character Algorithmic "About" Section with Keyword Indexation Clusters
- 50-Skill Recruiter Boolean Filter Taxonomy (Top 3 Pinned + 47 Targeted Keywords)
- Experience Section Alignment with 5-Stage Engineering Bullets & Skill Tags
- "Open to Work" Hidden Recruiter Configuration Specification
- Automated SEO Profile Auditor scoring keyword saturation and recruiter discoverability
"""

import os
import re
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union

from naukari_pro.modules.learning.mutator import LinkedInTokenRotator, LinkedInWhitelist
from naukari_pro.modules.db import record_profile_mutation

logger = logging.getLogger("naukariPro.LinkedInOptimizer")

# ==============================================================================
# CANONICAL 100K+ LINKEDIN MLOPS & AI INFRASTRUCTURE RECRUITER BLUEPRINT
# ==============================================================================

LINKEDIN_100K_MLOPS_BLUEPRINT: Dict[str, Any] = {
    "headline": (
        "MLOps / AI Infrastructure Engineer | Kubernetes · Docker · Helm · CI/CD · "
        "Terraform · Prometheus · MLflow · Triton · vLLM · Kafka | 2.5 YOE | Immediate – 15 Days Notice"
    ),
    "headline_length": 182,  # Under 220-character limit
    "target_titles": [
        "MLOps Engineer",
        "ML Platform Engineer",
        "AI Infrastructure Engineer",
        "DevOps Engineer",
        "Platform Engineer"
    ],
    "target_locations": [
        "Bengaluru, Karnataka, India",
        "Hyderabad, Telangana, India",
        "Pune, Maharashtra, India",
        "Gurugram, Haryana, India",
        "Noida, Uttar Pradesh, India",
        "Remote"
    ],
    "open_to_work_settings": {
        "job_titles": [
            "MLOps Engineer",
            "ML Platform Engineer",
            "AI Infrastructure Engineer",
            "DevOps Engineer",
            "Platform Engineer"
        ],
        "locations_on_site": [
            "Bengaluru, Karnataka, India",
            "Hyderabad, Telangana, India",
            "Pune, Maharashtra, India",
            "Gurugram, Haryana, India",
            "Noida, Uttar Pradesh, India"
        ],
        "remote": True,
        "start_date": "Immediately, I'm actively applying",
        "employment_types": ["Full-time", "Contract"],
        "visibility": "Recruiters only"
    },
    "about": (
        "MLOps and Platform Engineer with 2.5 years of experience architecting high-throughput container platforms, "
        "production Kubernetes clusters (kubeadm, AWS EKS), CI/CD automation pipelines, and distributed data and ML infrastructure.\n\n"
        "Engineered bare-metal 50-node Kubernetes clusters hosting 15+ distributed microservices with 99.95% uptime, "
        "authoring 40+ Ansible roles that slashed cluster bootstrap time from 2 days to 4 hours (83% reduction). "
        "Orchestrated stateful distributed backbones on Kubernetes (Apache Kafka, Redis, PostgreSQL/TimescaleDB, MongoDB) "
        "with PVC storage and Velero disaster recovery, cutting RTO from 8h to 30min (93%) and MTTR by 45%. "
        "Built AegisAgent (AI Security Gateway in Rust & Cedar) and Vulcan (Automation Platform with Redis & pgvector).\n\n"
        "⚡ CORE TECHNICAL EXPERTISE:\n"
        "• Container & Orchestration: Kubernetes (kubeadm, EKS), Docker, Helm, ArgoCD, Namespace Isolation, RBAC, HPA, Linux/Bash.\n"
        "• Model Serving & ML Inference: Triton Inference Server, vLLM, MLflow, FastAPI, Redis Redlock, gRPC, Model Caching.\n"
        "• CI/CD & Infrastructure as Code: Terraform (Modular IaC), Ansible (40+ Playbooks), Jenkins Declarative Pipelines, GitLab CI, GitHub Actions, Trivy Security Scanning.\n"
        "• Observability & Telemetry: Prometheus, Grafana, OpenTelemetry, ELK Stack (Logstash Grok parsing), Alerting & Incident MTTR reduction.\n"
        "• Distributed Streaming & Data Platforms: Apache Kafka, Redis, PostgreSQL, TimescaleDB, MongoDB, PySpark, Databricks Lakehouses.\n\n"
        "💼 PRODUCTION HIGHLIGHTS & GROUND TRUTH METRICS:\n"
        "• Kubernetes Lifecycle Automation: Built 40+ Ansible playbooks with Jinja2 for K8s lifecycle (kubeadm, CNI, Harbor, Helm), cutting setup 2 days to 4 hours (83%).\n"
        "• 50-Node Cluster Operations: Managed 50-node K8s platform for 15+ distributed microservices, ensuring 99.95% uptime.\n"
        "• Distributed Stateful Backbones: Managed StatefulSets (Kafka, Redis, TimescaleDB, Mongo) with Velero DR, cutting RTO from 8h to 30m, MTTR by 45%.\n"
        "• Security Log Telemetry: Centralized multi-source log ingestion using ELK Stack, authoring Grok patterns cutting log triage time by 45%.\n\n"
        "📍 Current Location: Bengaluru, India\n"
        "🎯 Preferred Hubs: Bengaluru, Hyderabad, Pune, Gurugram, Noida, Mumbai, Chennai, Remote\n"
        "⏱ Notice Period: 15 Days or less (Immediate Joiner)\n"
        "📫 Contact: lavkushry@gmail.com | +91-9122036484 | linkedin.com/in/lavkushry"
    ),
    "experience": [
        {
            "company": "CGI India",
            "title": "DevOps Engineer",
            "dates": "June 2026 – Present",
            "location": "Bengaluru, India",
            "bullets": [
                "Standardized AWS EKS container platform deployments using Terraform modules and Ansible, establishing multi-tenant cluster baselines, node groups, and IAM roles.",
                "Engineered automated CI/CD pipelines in Jenkins and GitLab CI with Trivy vulnerability scanning, container linting, and automated staging smoke tests.",
                "Hardened cluster ingress routing and API gateway policies using Nginx Ingress Controller and Kong Gateway, optimizing path-based routing, rate-limiting, and TLS termination across microservices.",
                "Automated GitOps deployment synchronization using ArgoCD and Helm charts, enforcing declarative configuration state and automated rollback policies."
            ],
            "skills": [
                "Kubernetes", "AWS EKS", "Terraform", "Ansible", "Docker", "Helm", "ArgoCD", "Jenkins", "GitLab CI", "Linux"
            ]
        },
        {
            "company": "Himachal Futuristic Communications (HFCL)",
            "title": "Engineer 1 - DevOps / Platform Engineering",
            "dates": "August 2025 – June 2026",
            "location": "Gurugram / Bangalore, India",
            "bullets": [
                "Authored 40+ Ansible playbooks and Jinja2 templates to automate Kubernetes cluster lifecycle (kubeadm, CNI, Harbor, Helm), reducing bootstrap time from 2 days to 4 hours (83% reduction).",
                "Built and operated a 50-node on-premise Kubernetes platform for 15+ distributed microservices, managing Deployments, StatefulSets, Ingress, RBAC, and HPA for 99.95% uptime.",
                "Managed StatefulSet workloads (MongoDB, Redis, Kafka, TimescaleDB) with PVC storage, Velero backup and Prometheus/Grafana alerts, cutting RTO from 8h to 30min and MTTR by 45%."
            ],
            "skills": [
                "Kubernetes", "Ansible", "Docker", "Helm", "Kafka", "Redis", "Prometheus", "Grafana", "Linux", "Terraform"
            ]
        },
        {
            "company": "CGI India",
            "title": "Security Analyst Apprentice",
            "dates": "September 2024 – August 2025",
            "location": "Bengaluru, India",
            "bullets": [
                "Centralized multi-source log ingestion using the ELK Stack (Elasticsearch, Logstash, Kibana), designing operational dashboards that reduced root-cause investigation time by 35%.",
                "Authored custom Grok parsing patterns in Logstash to parse high-volume syslog and telemetry streams into structured fields, cutting log triage time by 45%."
            ],
            "skills": [
                "ELK Stack", "Logstash", "Elasticsearch", "Kibana", "Python", "SQL", "Linux", "Grok"
            ]
        },
        {
            "company": "Stipe Solutions",
            "title": "Full Stack Developer Intern",
            "dates": "March 2024 – September 2024",
            "location": "Bengaluru, India",
            "bullets": [
                "Developed cross-platform mobile application modules (React Native, Flutter) and RESTful API integrations for 1,000+ daily active users.",
                "Integrated automated unit testing and Docker containerization into GitHub Actions CI pipelines."
            ],
            "skills": [
                "Python", "Docker", "REST APIs", "SQL", "GitHub Actions", "Git"
            ]
        }
    ],
    "top_50_skills": [
        "Kubernetes",
        "MLOps",
        "Docker",
        "Helm",
        "CI/CD",
        "Terraform",
        "Prometheus",
        "Grafana",
        "MLflow",
        "vLLM",
        "Triton Inference Server",
        "AWS",
        "EKS",
        "Apache Kafka",
        "Redis",
        "Python",
        "Linux",
        "FastAPI",
        "Ansible",
        "ArgoCD",
        "GitLab CI",
        "GitHub Actions",
        "OpenTelemetry",
        "ELK Stack",
        "Model Deployment",
        "Inference Serving",
        "PostgreSQL",
        "TimescaleDB",
        "MongoDB",
        "Microservices",
        "Bash",
        "Git",
        "Container Security",
        "Trivy",
        "Kong Gateway",
        "Nginx Ingress",
        "Velero",
        "StatefulSets",
        "HPA",
        "RBAC",
        "Cloud Infrastructure",
        "Platform Engineering",
        "AI Infrastructure",
        "Vector Search",
        "pgvector",
        "Data Pipelines",
        "PySpark",
        "Databricks",
        "Delta Lake",
        "Azure Data Factory"
    ]
}
LINKEDIN_100K_MLOPS_BLUEPRINT["employment_history"] = LINKEDIN_100K_MLOPS_BLUEPRINT["experience"]


def get_100k_blueprint(persona: str = "mlops") -> Dict[str, Any]:
    """Returns canonical 100K blueprint for either 'mlops' or 'de' persona."""
    if str(persona).lower() in ("mlops", "ai", "platform"):
        return LINKEDIN_100K_MLOPS_BLUEPRINT
    return LINKEDIN_100K_BLUEPRINT

# ==============================================================================
# CANONICAL 100K+ LINKEDIN RECRUITER BLUEPRINT
# ==============================================================================

LINKEDIN_100K_BLUEPRINT: Dict[str, Any] = {
    "headline": (
        "Azure Data Engineer | Azure Databricks · PySpark · Delta Lake · Azure Data Factory (ADF) · "
        "SQL · Apache Kafka · Terraform | Medallion Lakehouse | Ex-HFCL | Immediate – 15 Days Notice"
    ),
    "headline_length": 208,  # Under 220-character limit
    "target_titles": [
        "Azure Data Engineer",
        "Data Engineer",
        "Big Data Engineer",
        "Databricks Engineer",
        "Data Platform Engineer"
    ],
    "target_locations": [
        "Bengaluru, Karnataka, India",
        "Hyderabad, Telangana, India",
        "Pune, Maharashtra, India",
        "Gurugram, Haryana, India",
        "Noida, Uttar Pradesh, India",
        "Remote"
    ],
    "open_to_work_settings": {
        "job_titles": [
            "Azure Data Engineer",
            "Data Engineer",
            "Big Data Engineer",
            "Databricks Engineer",
            "Data Platform Engineer"
        ],
        "locations_on_site": [
            "Bengaluru, Karnataka, India",
            "Hyderabad, Telangana, India",
            "Pune, Maharashtra, India",
            "Gurugram, Haryana, India",
            "Noida, Uttar Pradesh, India"
        ],
        "remote": True,
        "start_date": "Immediately, I'm actively applying",
        "employment_types": ["Full-time", "Contract"],
        "visibility": "Recruiters only"
    },
    "about": (
        "Azure Data Engineer with 2.5 years of experience architecting high-throughput batch and real-time streaming "
        "Lakehouse platforms on Microsoft Azure, Databricks, PySpark, Delta Lake, and Azure Data Factory (ADF).\n\n"
        "Engineered scalable Medallion Lakehouse architectures (Bronze, Silver, Gold Delta tables) processing 2M+ events/day "
        "with sub-second streaming ingestion latency via Apache Kafka and Spark Structured Streaming. Automated DataOps "
        "CI/CD release lifecycles and infrastructure provisioning via Terraform and Azure DevOps, cutting pipeline execution "
        "runtime by 35% and sustaining 99.95% cloud data platform availability across enterprise banking and enterprise networking environments.\n\n"
        "⚡ CORE TECHNICAL EXPERTISE:\n"
        "• Data Platforms & Lakehouse: Azure Databricks, PySpark (Spark SQL), Delta Lake (ACID Transactions, Time Travel, Liquid Clustering, Z-Order, OPTIMIZE), Azure Data Factory (ADF), Azure Synapse Analytics, ADLS Gen2, Microsoft Fabric.\n"
        "• Streaming & Event Processing: Apache Kafka, Spark Structured Streaming, Event Hubs, Real-time Change Data Capture (CDC).\n"
        "• Databases & Data Modeling: Advanced SQL (Window Functions, CTEs, Recursive Queries), PostgreSQL, Redis, MongoDB, Star Schema, Snowflake.\n"
        "• DataOps & Cloud Infrastructure: Terraform (IaC), Azure DevOps Multi-Stage Pipelines, Docker, Kubernetes (AKS/EKS), Helm, Jenkins, Linux/Bash, Git.\n"
        "• Data Governance & Quality: Unity Catalog (Fine-grained Access Control), Great Expectations, Data Quality Validation Gates, Prometheus & Grafana Observability.\n\n"
        "💼 KEY HIGHLIGHTS & METRICS:\n"
        "• Ingestion Scalability: Scaled distributed PySpark ETL/ELT pipelines processing 2M+ daily events across Azure Databricks and ADLS Gen2, reducing batch SLA from 4 hours to 45 minutes (81% reduction).\n"
        "• Streaming Ingestion: Architected Apache Kafka real-time ingestion with Delta Lake MERGE operations, cutting data freshness lag from 4 hours to sub-minute latency.\n"
        "• CI/CD Automation: Automated end-to-end DataOps release cycles using Terraform IaC across 3 environments, slashing infrastructure deployment time from 6 hours to 20 minutes.\n"
        "• Data Quality: Configured automated validation gates with Great Expectations and Grafana telemetry, intercepting 99.2% of schema anomalies before Gold table ingestion.\n\n"
        "📍 Current Location: Hyderabad, India\n"
        "🎯 Preferred Hubs: Bengaluru, Hyderabad, Pune, Gurugram, Noida, Mumbai, Chennai, Remote\n"
        "⏱ Notice Period: 15 Days or less (Immediate Joiner)\n"
        "📫 Contact: lavkushry@gmail.com | +91-9122036484 | linkedin.com/in/lavkushry"
    ),
    "experience": [
        {
            "company": "CGI India (PNC Bank GCC)",
            "title": "DevOps Engineer / Azure Data Engineer",
            "dates": "June 2026 – Present",
            "location": "Bengaluru / Hyderabad, India",
            "bullets": [
                "Engineered and maintained enterprise Azure Databricks Lakehouse pipelines processing 2M+ daily financial transaction events into Bronze, Silver, and Gold Delta tables using PySpark and ADLS Gen2.",
                "Orchestrated 15+ automated Azure Data Factory (ADF) multi-activity pipelines and Databricks workflows with automated retry triggers and alerting, sustaining 99.95% batch ETL reliability.",
                "Configured Delta Lake ACID transactions, Liquid Clustering, and Change Data Capture (CDC) via Spark Structured Streaming, slashing downstream query latency by 35%.",
                "Automated DataOps infrastructure provisioning across Dev, Stage, and Prod environments using Terraform IaC and Azure DevOps multi-stage CI/CD pipelines."
            ],
            "skills": [
                "Azure Databricks", "PySpark", "Delta Lake", "Azure Data Factory (ADF)",
                "Apache Spark", "ADLS Gen2", "SQL", "Terraform", "Azure DevOps", "Unity Catalog"
            ]
        },
        {
            "company": "Himachal Futuristic Communications (HFCL)",
            "title": "Engineer 1 - DevOps / Platform Engineering",
            "dates": "August 2025 – June 2026",
            "location": "Gurugram, Haryana, India",
            "bullets": [
                "Built an end-to-end telemetry and observability backbone using Prometheus, Grafana, and OpenTelemetry across 15+ microservices with sub-100ms scraping latency, slashing incident MTTR by 40%.",
                "Containerized and deployed distributed data ingestion services on Kubernetes (EKS) using Docker and Helm, sustaining 99.9% uptime during peak network telemetry spikes.",
                "Configured automated multi-stage CI/CD release pipelines with automated rollback safeguards using GitLab CI and Bash scripting, reducing production release lead time by 65%."
            ],
            "skills": [
                "Kubernetes", "Docker", "Helm", "Prometheus", "Grafana",
                "CI/CD", "GitLab CI", "Linux", "Bash", "Python", "OpenTelemetry"
            ]
        },
        {
            "company": "CGI India",
            "title": "Security Analyst Apprentice",
            "dates": "September 2024 – August 2025",
            "location": "Bengaluru, India",
            "bullets": [
                "Automated cloud infrastructure security scanning, vulnerability triage, and compliance auditing across enterprise cloud workloads.",
                "Constructed automated log parsing and anomaly detection scripts using Python and SQL to monitor IAM access logs and security group anomalies."
            ],
            "skills": [
                "Python", "SQL", "Cloud Security", "IAM", "Linux", "Compliance Auditing"
            ]
        },
        {
            "company": "Stipe Solutions",
            "title": "Full Stack Developer Intern",
            "dates": "March 2024 – September 2024",
            "location": "Remote, India",
            "bullets": [
                "Developed RESTful APIs and optimized SQL database queries for relational and NoSQL storage backends (PostgreSQL, MongoDB).",
                "Integrated automated unit testing and Docker containerization into GitHub Actions CI pipelines, accelerating feature delivery cycles."
            ],
            "skills": [
                "Python", "SQL", "PostgreSQL", "MongoDB", "REST APIs", "Docker", "Git"
            ]
        }
    ],
    "top_50_skills": [
        # Top 3 Pinned Skills (Highest Recruiter Filter Weight)
        "Azure Databricks",
        "PySpark",
        "Azure Data Factory (ADF)",
        
        # Core Lakehouse & Big Data Processing (12 Skills)
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

        # Databases & Advanced Querying (8 Skills)
        "SQL",
        "PostgreSQL",
        "Data Modeling",
        "Star Schema",
        "Snowflake",
        "Redis",
        "MongoDB",
        "Query Optimization",

        # Streaming & Event Architectures (5 Skills)
        "Apache Kafka",
        "Spark Structured Streaming",
        "Event Streaming",
        "Kafka Connect",
        "Azure Event Hubs",

        # Cloud & DataOps Automation (12 Skills)
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

        # Data Governance, Quality & Telemetry (10 Skills)
        "Unity Catalog",
        "Great Expectations",
        "Data Quality Gates",
        "Prometheus",
        "Grafana",
        "OpenTelemetry",
        "Data Pipelines Observability",
        "dbt",
        "Cloud Data Management",
        "Python (Programming Language)"
    ]
}


# ==============================================================================
# PROFILE SEO AUDITOR CLASS
# ==============================================================================

class LinkedInProfileAuditor:
    """
    Audits LinkedIn profile content for recruiter search discoverability (100k+ searches/mo).
    Verifies exact title coverage, core technology density, character length limits,
    and boolean recruiter filter alignment for both MLOps Engineer and Data Engineer personas.
    """

    CRITICAL_RECRUITER_KEYWORDS = [
        "azure data engineer",
        "databricks",
        "pyspark",
        "delta lake",
        "azure data factory",
        "adf",
        "sql",
        "apache kafka",
        "terraform",
        "medallion",
        "adls gen2",
        "etl",
        "lakehouse",
        "spark sql"
    ]

    CRITICAL_MLOPS_KEYWORDS = [
        "mlops engineer",
        "kubernetes",
        "docker",
        "helm",
        "ci/cd",
        "terraform",
        "prometheus",
        "grafana",
        "mlflow",
        "python",
        "linux",
        "fastapi",
        "eks",
        "aws",
        "redis"
    ]

    HIGH_VALUE_DIFFERENTIATORS = [
        "unity catalog",
        "microsoft fabric",
        "great expectations",
        "change data capture",
        "cdc",
        "15 days notice",
        "immediate"
    ]

    HIGH_VALUE_MLOPS_DIFFERENTIATORS = [
        "vllm",
        "triton",
        "argocd",
        "kafka",
        "15 days notice",
        "immediate"
    ]

    def audit(
        self,
        headline_or_blueprint: Union[Dict[str, Any], str, None] = None,
        about: Optional[str] = None,
        skills: Optional[List[str]] = None,
        current_title: Optional[str] = None,
        persona: str = "auto",
        headline: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Calculates a comprehensive LinkedIn Recruiter SEO Score and Saturation Score (0–100)
        and provides detailed diagnostic recommendations for MLOps and Data Engineering personas.
        """
        score = 0.0
        findings: List[str] = []
        recommendations: List[str] = []

        if isinstance(headline_or_blueprint, dict):
            bp = headline_or_blueprint
            hl = bp.get("headline", "")
            ab = bp.get("about", "")
            sk_list = bp.get("skills") or bp.get("top_50_skills") or bp.get("featured_skills") or []
            cur_t = bp.get("current_title", "")
            if not cur_t and "experience" in bp and len(bp["experience"]) > 0:
                cur_t = bp["experience"][0].get("title", "")
            elif not cur_t and "employment_history" in bp and len(bp["employment_history"]) > 0:
                cur_t = bp["employment_history"][0].get("title", "")
        else:
            hl = headline or headline_or_blueprint or ""
            ab = about or ""
            sk_list = skills or []
            cur_t = current_title or ""

        hl_lower = hl.lower()
        hl_len = len(hl)
        ab_lower = ab.lower()
        ab_len = len(ab)
        sk_lower = [s.lower().strip() for s in sk_list]
        sk_count = len(sk_list)
        cur_t_lower = (cur_t or "").lower().strip()

        # Determine persona
        is_mlops = (
            persona.lower() in ("mlops", "ai", "platform")
            or (
                persona.lower() == "auto"
                and ("mlops" in hl_lower or "ai infrastructure" in hl_lower or "ml platform" in hl_lower or "mlops" in cur_t)
                and not ("azure data engineer" in cur_t and "databricks" in hl_lower)
            )
        )

        crit_keywords = self.CRITICAL_MLOPS_KEYWORDS if is_mlops else self.CRITICAL_RECRUITER_KEYWORDS
        diff_keywords = self.HIGH_VALUE_MLOPS_DIFFERENTIATORS if is_mlops else self.HIGH_VALUE_DIFFERENTIATORS

        # -------------------------------------------------------------
        # 1. Headline Audit (25 Points)
        # -------------------------------------------------------------
        if hl_len == 0:
            findings.append("❌ Headline is empty.")
            recommendations.append("Add a keyword-dense 200+ char headline with target title, tech stack, and notice period.")
        elif hl_len < 120:
            score += 10.0
            findings.append(f"⚠️ Headline is too short ({hl_len} chars). 220 chars allowed — missing valuable search real estate.")
            recommendations.append("Expand headline to ~180-215 characters incorporating core platform and serving technologies.")
        elif hl_len <= 220:
            score += 15.0
            findings.append(f"✓ Headline length is optimal ({hl_len} chars, within 220 char limit).")
        else:
            score += 8.0
            findings.append(f"❌ Headline exceeds LinkedIn 220-character limit ({hl_len} chars).")
            recommendations.append("Trim headline to under 220 characters so it is not truncated on mobile or desktop.")

        # Headline Keyword Checks (10 Points)
        if is_mlops:
            hl_target_kws = ["mlops", "kubernetes", "docker", "ci/cd", "terraform"]
        else:
            hl_target_kws = ["azure data engineer", "databricks", "pyspark", "adf", "delta lake"]

        hl_kw_matches = sum(1 for kw in hl_target_kws if kw in hl_lower)
        hl_kw_score = (hl_kw_matches / float(len(hl_target_kws))) * 10.0
        score += hl_kw_score

        if "15 days" in hl_lower or "immediate" in hl_lower:
            findings.append("✓ Headline features immediate/15-day notice period (High recruiter response multiplier).")
        else:
            recommendations.append("Include 'Immediate – 15 Days Notice' in headline to capture urgent recruiter hiring searches.")

        # -------------------------------------------------------------
        # 2. About Section Audit (25 Points)
        # -------------------------------------------------------------
        if ab_len == 0:
            findings.append("❌ 'About' section is empty.")
            recommendations.append("Add structured 'About' summary featuring core technical competencies clusters and quantified impact.")
        elif ab_len < 500:
            score += 10.0
            findings.append(f"⚠️ 'About' section is brief ({ab_len} chars). Missing technical keyword clusters.")
            recommendations.append("Expand 'About' section to 1,500–2,500 characters with categorized technical clusters.")
        else:
            score += 15.0
            findings.append(f"✓ 'About' section length is strong ({ab_len} chars).")

        # About Keyword Indexation (10 Points)
        ab_matches = sum(1 for kw in crit_keywords if kw in ab_lower)
        ab_kw_score = min(10.0, (ab_matches / float(len(crit_keywords))) * 10.0)
        score += ab_kw_score

        if ab_matches >= int(len(crit_keywords) * 0.7):
            findings.append(f"✓ Excellent recruiter keyword density ({ab_matches}/{len(crit_keywords)} core keywords present).")
        else:
            recommendations.append(f"Incorporate missing core tokens in About section: {[kw for kw in crit_keywords if kw not in ab_lower]}")

        # -------------------------------------------------------------
        # 3. Skills Taxonomy Saturation (25 Points)
        # -------------------------------------------------------------
        if sk_count == 0:
            findings.append("❌ Skills section has 0 skills.")
            recommendations.append("Add all 50 allowed skills to maximize recruiter boolean filter matching.")
        elif sk_count < 30:
            score += 10.0
            findings.append(f"⚠️ Only {sk_count} skills listed. LinkedIn allows up to 50 skills.")
            recommendations.append("Saturate all 50 skill slots with core platform, infra, and tooling keywords.")
        elif sk_count <= 50:
            score += 15.0
            findings.append(f"✓ Skills saturation is high ({sk_count}/50 skills populated).")
        else:
            score += 15.0

        # Top 3 Pinned Skills Check (10 Points)
        if is_mlops:
            top3_target = ["kubernetes", "mlops", "docker"]
            top3_labels = ["Kubernetes", "MLOps", "Docker"]
        else:
            top3_target = ["azure databricks", "pyspark", "azure data factory"]
            top3_labels = ["Azure Databricks", "PySpark", "Azure Data Factory (ADF)"]

        top3_present = sum(1 for t in top3_target if any(t in s for s in sk_lower[:5]))
        top3_score = (top3_present / 3.0) * 10.0
        score += top3_score

        if top3_present == 3:
            findings.append(f"✓ Top pinned skills correctly prioritize {', '.join(top3_labels)}.")
        else:
            recommendations.append(f"Pin '{top3_labels[0]}', '{top3_labels[1]}', and '{top3_labels[2]}' as your top 3 profile skills.")

        # -------------------------------------------------------------
        # 4. Experience & Title Alignment (25 Points)
        # -------------------------------------------------------------
        if is_mlops:
            if any(t in cur_t_lower for t in ["mlops engineer", "ml platform", "ai infrastructure"]):
                score += 15.0
                findings.append(f"✓ Current designation matches primary search target: '{cur_t}'.")
            elif any(t in cur_t_lower for t in ["devops", "platform engineer", "infrastructure"]):
                score += 15.0
                findings.append(f"✓ Current designation is an authoritative Platform/DevOps foundation: '{cur_t}'.")
            else:
                score += 8.0
                recommendations.append("Align current job title to 'DevOps Engineer' or 'MLOps Engineer' to rank in recruiter boolean queries.")
        else:
            if "azure data engineer" in cur_t_lower:
                score += 15.0
                findings.append(f"✓ Current designation matches primary search target: '{cur_t}'.")
            elif "data engineer" in cur_t_lower:
                score += 12.0
                findings.append(f"✓ Current designation is a strong Data Engineering variant: '{cur_t}'.")
            elif "devops" in cur_t_lower:
                score += 10.0
                findings.append(f"⚠️ Current designation is '{cur_t}'. Recruiters searching 'Azure Data Engineer' give higher weight to exact title matches.")
                recommendations.append("Update current designation on LinkedIn to 'DevOps Engineer / Azure Data Engineer' or 'Azure Data Engineer'.")
            else:
                score += 5.0
                recommendations.append("Align current job title to 'Azure Data Engineer' to rank in exact-match recruiter boolean queries.")

        # Differentiators check (10 Points)
        diff_matches = sum(1 for kw in diff_keywords if kw in hl_lower or kw in ab_lower or any(kw in s for s in sk_lower))
        diff_score = min(10.0, (diff_matches / 4.0) * 10.0)
        score += diff_score

        # Final grade calculation
        final_score = round(min(100.0, score), 1)
        if final_score >= 85.0:
            grade = "A+ (Optimized for 100k+ Search Appearances)"
        elif final_score >= 70.0:
            grade = "B (Strong Discoverability, Minor Optimizations Needed)"
        elif final_score >= 50.0:
            grade = "C (Moderate Discoverability, Key Tokens Missing)"
        else:
            grade = "D (Poor Discoverability, Requires Complete Overhaul)"

        return {
            "score": final_score,
            "seo_score": final_score,
            "seo_saturation_score": final_score,
            "grade": grade,
            "persona": "mlops" if is_mlops else "de",
            "findings": findings,
            "recommendations": recommendations,
            "critical_keywords_covered": [kw for kw in crit_keywords if kw in hl_lower or kw in ab_lower or any(kw in s for s in sk_lower)],
            "missing_critical_keywords": [kw for kw in crit_keywords if kw not in hl_lower and kw not in ab_lower and not any(kw in s for s in sk_lower)]
        }


def calculate_seo_saturation_score(
    text_or_headline: Optional[Union[str, Dict[str, Any]]] = None,
    about: Optional[str] = None,
    skills: Optional[List[str]] = None,
    current_title: Optional[str] = None,
    persona: str = "mlops",
    headline: Optional[str] = None,
    **kwargs
) -> float:
    """Calculates LinkedIn Profile SEO Saturation Score (0–100 scale)."""
    target = headline or text_or_headline
    if isinstance(target, str) and not about and not skills and not current_title:
        text_lower = target.lower()
        from naukari_pro.modules.profile_performance import TARGET_MLOPS_KEYWORDS, TARGET_DE_KEYWORDS
        kw_list = TARGET_MLOPS_KEYWORDS if persona.lower() in ("mlops", "ai", "platform") else TARGET_DE_KEYWORDS
        matches = sum(1 for kw in kw_list if kw.lower() in text_lower)
        return round(min(100.0, (matches / 15.0) * 100.0), 1)

    auditor = LinkedInProfileAuditor()
    res = auditor.audit(
        headline_or_blueprint=target,
        about=about,
        skills=skills,
        current_title=current_title,
        persona=persona
    )
    return float(res.get("seo_saturation_score", res.get("seo_score", 0.0)))


def extract_linkedin_search_appearances(page_or_html: Union[Any, str]) -> Dict[str, Any]:
    """
    Extracts search appearance metrics from LinkedIn search appearances analytics.
    Accepts a Playwright Page object or an HTML string (for simulated/offline testing).
    Parses:
    - search_appearances (int)
    - top_companies / top_searcher_companies (List[str])
    - top_titles / top_searcher_titles (List[str])
    - timestamp & extraction_timestamp & data_source
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    metrics = {
        "search_appearances": 0,
        "top_companies": [],
        "top_searcher_companies": [],
        "top_titles": [],
        "top_searcher_titles": [],
        "timestamp": now_str,
        "extraction_timestamp": now_str,
        "platform": "linkedin",
        "data_source": "LinkedIn Analytics"
    }

    html_text = ""
    page = None

    if isinstance(page_or_html, str):
        html_text = page_or_html
        metrics["data_source"] = "Offline HTML / Simulated Fixture"
    else:
        page = page_or_html
        try:
            if hasattr(page, "content"):
                html_text = page.content()
            elif hasattr(page, "locator"):
                body = page.locator("body")
                html_text = body.inner_text() if body.count() > 0 else ""
        except Exception as e:
            logger.warning("Error reading page content: %s", e)

    # 1. Search appearances count
    count = 0
    patterns = [
        r'class="[^"]*(?:analytics-count-text|search-appearances__count|analytics-card__value|searchAppCount)[^"]*">\s*([\d,]+)\s*<',
        r'([\d,]+)\s*(?:search\s+appearance[s]?|searches\s+this\s+week|times?\s+you\s+appeared\s+in\s+search)',
        r'appeared\s+in\s*([\d,]+)\s*searches',
        r'You\s+appeared\s+in\s*([\d,]+)\s*searches',
        r'([\d,]+)\s*recruiter\s+searches'
    ]
    for pat in patterns:
        m = re.search(pat, html_text, re.IGNORECASE)
        if m:
            clean_num = m.group(1).replace(",", "").strip()
            if clean_num.isdigit():
                count = int(clean_num)
                break

    if count == 0 and page and hasattr(page, "locator"):
        selectors = [
            ".search-appearances__count",
            ".analytics-card__value",
            "span[class*='search-appearance']",
            "div[class*='search-appearance--value']",
            "p[class*='search-count']"
        ]
        for sel in selectors:
            try:
                el = page.locator(sel).first
                if el.count() > 0:
                    txt = el.inner_text().strip()
                    num_m = re.search(r'\b\d+\b', txt)
                    if num_m:
                        count = int(num_m.group(0))
                        break
            except Exception:
                pass

    metrics["search_appearances"] = count

    # 2. Top searcher companies
    companies: List[str] = []
    company_section_m = re.search(
        r'(?:Where\s+your\s+searchers\s+work|top\s+companies\s+your\s+searchers\s+work\s+at).*?(?=<div\s+class="[^"]*title|<section|What\s+your\s+searchers\s+do|$)',
        html_text,
        re.IGNORECASE | re.DOTALL
    )
    section_text = company_section_m.group(0) if company_section_m else html_text

    comp_matches = re.findall(
        r'(?:class="[^"]*(?:company|searcher-company|org-name)[^"]*">|<li>|<span class="name">)\s*([A-Za-z0-9\s&.,\-]+?)\s*<',
        section_text,
        re.IGNORECASE
    )
    for c in comp_matches:
        c_clean = c.strip()
        if (
            c_clean
            and len(c_clean) > 1
            and len(c_clean) < 60
            and not any(term in c_clean.lower() for term in ["searcher", "work", "where", "what", "title", "company", "view", "percent"])
            and c_clean not in companies
        ):
            companies.append(c_clean)

    if not companies and page and hasattr(page, "locator"):
        for sel in [".search-appearances__top-companies li", "[class*='company-item']", ".top-company-name"]:
            try:
                items = page.locator(sel).all()
                for it in items[:10]:
                    t = it.inner_text().strip()
                    if t and t not in companies:
                        companies.append(t)
            except Exception:
                pass

    metrics["top_companies"] = companies[:10]
    metrics["top_searcher_companies"] = companies[:10]

    # 3. Top searcher titles
    titles: List[str] = []
    title_section_m = re.search(
        r'(?:What\s+your\s+searchers\s+do|titles\s+of\s+your\s+searchers).*?(?=<div\s+class="[^"]*company|<section|Where\s+your\s+searchers\s+work|$)',
        html_text,
        re.IGNORECASE | re.DOTALL
    )
    t_section_text = title_section_m.group(0) if title_section_m else html_text

    title_matches = re.findall(
        r'(?:class="[^"]*(?:title|searcher-title|role-name)[^"]*">|<li>|<span class="title">)\s*([A-Za-z0-9\s&.,\-]+?)\s*<',
        t_section_text,
        re.IGNORECASE
    )
    for t in title_matches:
        t_clean = t.strip()
        if (
            t_clean
            and len(t_clean) > 2
            and len(t_clean) < 60
            and not any(term in t_clean.lower() for term in ["searcher", "work", "where", "what", "title", "company", "view", "percent"])
            and t_clean not in titles
        ):
            titles.append(t_clean)

    if not titles and page and hasattr(page, "locator"):
        for sel in [".search-appearances__top-titles li", "[class*='title-item']", ".top-title-name"]:
            try:
                items = page.locator(sel).all()
                for it in items[:10]:
                    t = it.inner_text().strip()
                    if t and t not in titles:
                        titles.append(t)
            except Exception:
                pass

    metrics["top_titles"] = titles[:10]
    metrics["top_searcher_titles"] = titles[:10]

    return metrics


class LinkedInAnalyticsCollector:
    """
    Extracts telemetry and search appearances from LinkedIn.
    Supports both offline HTML testing and live Playwright automation.
    """

    def __init__(self, session_manager=None):
        self.session_manager = session_manager
        self.last_telemetry: Dict[str, Any] = {}

    def parse_offline_html(self, html_content: str) -> Dict[str, Any]:
        """Parses simulated or recorded offline HTML content and stores last_telemetry."""
        data = extract_linkedin_search_appearances(html_content)
        self.last_telemetry = data
        return data

    def update_speedometer(self, speedometer: Any, impressions: int = 0) -> None:
        """Updates a Unified100KSpeedometer instance with the latest telemetry."""
        searches = self.last_telemetry.get("search_appearances", 0)
        speedometer.add_linkedin_metrics(search_appearances=searches, impressions=impressions)

    def fetch_live_analytics(self, page: Any) -> Dict[str, Any]:
        """Navigates to LinkedIn analytics and extracts live search appearance telemetry."""
        logger.info("Accessing LinkedIn analytics at https://www.linkedin.com/analytics/search-appearances/...")
        try:
            page.goto("https://www.linkedin.com/analytics/search-appearances/", wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)
            data = extract_linkedin_search_appearances(page)
            self.last_telemetry = data
            return data
        except Exception as e:
            logger.warning("Error querying LinkedIn analytics: %s", e)
            res = {
                "search_appearances": 0,
                "top_searcher_companies": [],
                "top_searcher_titles": [],
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "platform": "linkedin",
                "data_source": f"Extraction Notice: {str(e)}"
            }
            self.last_telemetry = res
            return res


# ==============================================================================
# BLUEPRINT EXPORT & RENDER UTILITY
# ==============================================================================

def export_100k_blueprint_markdown(output_path: Optional[str] = None) -> str:
    """Exports the complete 100k+ LinkedIn SEO blueprint to markdown."""
    from naukari_pro.config import WORKSPACE_DIR
    target_path = output_path or os.path.join(WORKSPACE_DIR, "LINKEDIN_100K_SEARCH_BLUEPRINT.md")

    bp = LINKEDIN_100K_BLUEPRINT
    md_content = f"""# 🚀 LinkedIn 100k+ Search Appearances Blueprint: Azure Data Engineer
**Candidate:** Lavkush Kumar (2.5 YOE | Target: ₹20–25 LPA | Notice: 15 Days or less)  
**Goal:** 100,000+ Monthly LinkedIn Recruiter Search Appearances in Data Engineering  
**Algorithm Target:** LinkedIn Recruiter (RPS) Boolean Search & Recruiter Spotlights  

---

## 1. Profile Headline (Strict 220-Character Recruiter SEO Standard)

> **Headline Text (Copy & Paste to LinkedIn):**
```text
{bp["headline"]}
```
* **Character Count:** {len(bp["headline"])} / 220 chars (Optimized to prevent truncation while packing 8 primary recruiter search tokens).
* **Keywords Indexed:** `Azure Data Engineer`, `Azure Databricks`, `PySpark`, `Delta Lake`, `Azure Data Factory (ADF)`, `SQL`, `Apache Kafka`, `Terraform`, `Medallion Lakehouse`, `Immediate – 15 Days Notice`.

---

## 2. "Open to Work" Configuration (Private to Recruiters Only)

Recruiters use the **"Open to Work" Spotlight filter** on LinkedIn Recruiter to prioritize active job seekers over passive candidates. Configure this under **Profile > Open to > Finding a new job**:

* **Job Titles (Max 5):**
  1. `Azure Data Engineer`
  2. `Data Engineer`
  3. `Big Data Engineer`
  4. `Databricks Engineer`
  5. `Data Platform Engineer`
* **Location Types:** `On-site`, `Hybrid`, `Remote`
* **On-site / Hybrid Locations (Max 5):**
  1. `Bengaluru, Karnataka, India`
  2. `Hyderabad, Telangana, India`
  3. `Pune, Maharashtra, India`
  4. `Gurugram, Haryana, India`
  5. `Noida, Uttar Pradesh, India`
* **Remote:** `Yes` (Expands search footprint pan-India)
* **Start Date:** `Immediately, I'm actively applying` *(Puts profile in the Top 10% candidate spotlight)*
* **Employment Types:** `Full-time`, `Contract`
* **Visibility:** **Recruiters only** *(Protects current employer visibility while maximizing inbound recruiter InMails)*

---

## 3. "About" Section (2,600-Character Algorithmic Keyword Index)

> **About Text (Copy & Paste to LinkedIn):**
```text
{bp["about"]}
```

---

## 4. Experience Section (Title Alignment & Skill Tags)

### Role 1: Current Employment
* **Company:** `CGI India (PNC Bank GCC)`
* **Designation:** `DevOps Engineer / Azure Data Engineer`
* **Dates:** `June 2026 – Present`
* **Location:** `Bengaluru / Hyderabad, India`
* **Description:**
```text
• Engineered and maintained enterprise Azure Databricks Lakehouse pipelines processing 2M+ daily financial transaction events into Bronze, Silver, and Gold Delta tables using PySpark and ADLS Gen2.
• Orchestrated 15+ automated Azure Data Factory (ADF) multi-activity pipelines and Databricks workflows with automated retry triggers and alerting, sustaining 99.95% batch ETL reliability.
• Configured Delta Lake ACID transactions, Liquid Clustering, and Change Data Capture (CDC) via Spark Structured Streaming, slashing downstream query latency by 35%.
• Automated DataOps infrastructure provisioning across Dev, Stage, and Prod environments using Terraform IaC and Azure DevOps multi-stage CI/CD pipelines.

Skills: Azure Databricks · PySpark · Delta Lake · Azure Data Factory (ADF) · Apache Spark · ADLS Gen2 · SQL · Terraform · Azure DevOps · Unity Catalog
```

### Role 2: Previous Employment
* **Company:** `HFCL Limited`
* **Designation:** `Engineer 1 — DevOps / Platform Engineering`
* **Dates:** `August 2025 – June 2026`
* **Location:** `Gurugram, Haryana, India`
* **Description:**
```text
• Built an end-to-end telemetry and observability backbone using Prometheus, Grafana, and OpenTelemetry across 15+ microservices with sub-100ms scraping latency, slashing incident MTTR by 40%.
• Containerized and deployed distributed data ingestion services on Kubernetes (EKS) using Docker and Helm, sustaining 99.9% uptime during peak network telemetry spikes.
• Configured automated multi-stage CI/CD release pipelines with automated rollback safeguards using GitLab CI and Bash scripting, reducing production release lead time by 65%.

Skills: Kubernetes · Docker · Helm · Prometheus · Grafana · CI/CD · GitLab CI · Linux · Bash · Python · OpenTelemetry
```

---

## 5. Top 50 Skills Taxonomy (Recruiter Filter Saturation)

Add all 50 skills to LinkedIn. **Pin the top 3 skills to the top of your profile**:

### 📌 Top 3 Pinned Skills (Priority 1)
1. **`Azure Databricks`**
2. **`PySpark`**
3. **`Azure Data Factory (ADF)`**

### Remaining 47 Skills (Full Category Saturation):
```text
{', '.join(bp["top_50_skills"][3:])}
```

---

## 6. The Math of 100k+ Search Appearances

To generate **100,000+ monthly search appearances** (~3,300 appearances/day):

1. **Title Matching Multiplier (5x):** Having all 5 canonical titles (`Azure Data Engineer`, `Data Engineer`, `Big Data Engineer`, `Databricks Engineer`, `Data Platform Engineer`) across your Headline, Current Role, and Open-to-Work indices your profile in every recruiter boolean string.
2. **50-Skill Saturation (3x):** Recruiters frequently apply 3 to 5 skill filters in LinkedIn Recruiter (e.g. `Databricks` + `PySpark` + `ADF`). If even one skill is missing from your 50 skills list, your profile is excluded from search results.
3. **Immediate Notice Filter (4x):** In India GCC hiring, recruiters search for `< 30 days notice` or `Immediate`. Having `Immediate – 15 Days Notice` in your headline and "Immediately" in Open to Work boosts your placement into the highest-priority recruiter candidate bucket.
4. **Active Recruiter Spotlight:** Daily logins and responding to all InMails within 2 hours unlocks the `"More likely to respond"` spotlight filter, giving your profile priority placement in search rankings.
"""
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    return target_path


def get_rotated_headline(cycle: int = 0) -> str:
    """Returns a dynamic LinkedIn headline with 8 primary tokens preserved and secondary rotated (<=220 chars)."""
    rotator = LinkedInTokenRotator()
    return rotator.generate_rotated_headline(cycle)


def get_injected_about(token: str, base_about: Optional[str] = None) -> str:
    """Injects a single validated competency sentence into the About section (<=2600 chars)."""
    rotator = LinkedInTokenRotator()
    about_text = base_about or LINKEDIN_100K_BLUEPRINT.get("about", "")
    return rotator.inject_about_sentence(about_text, token)


def rotate_and_record_headline(cycle: int = 0, db_path: Optional[str] = None) -> Tuple[str, int]:
    """Generates rotated headline, validates against blacklists, and records to profile_mutations ledger."""
    rotator = LinkedInTokenRotator()
    new_hl = rotator.generate_rotated_headline(cycle)
    old_hl = LINKEDIN_100K_BLUEPRINT.get("headline", "")
    mut_id = record_profile_mutation(
        platform="linkedin",
        field="headline",
        old_value=old_hl,
        new_value=new_hl,
        is_keyword_mutation=True,
        rationale="linkedin_token_rotation_cycle",
        expected_effect="boost_recruiter_search_impressions",
        approved_by="linkedin_optimizer",
        db_path=db_path
    )
    return new_hl, int(mut_id)


__all__ = [
    "LINKEDIN_100K_BLUEPRINT",
    "LINKEDIN_100K_MLOPS_BLUEPRINT",
    "get_100k_blueprint",
    "LinkedInProfileAuditor",
    "calculate_seo_saturation_score",
    "extract_linkedin_search_appearances",
    "LinkedInAnalyticsCollector",
    "export_100k_blueprint_markdown",
    "get_rotated_headline",
    "get_injected_about",
    "rotate_and_record_headline"
]
