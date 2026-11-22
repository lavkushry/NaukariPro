"""
naukariPro Feature: LinkedIn 100k+ Search Appearance Optimizer & Profile SEO Engine
Target: 100,000+ Monthly LinkedIn Recruiter Search Appearances for Platform, DevOps & MLOps Engineering
Candidate: Lavkush Kumar (Platform / DevOps / MLOps & AI Infrastructure, ~2.5 YOE | ₹20-25 LPA Target | 15-day notice)

Provides:
- Exact <=220-character Recruiter-Optimized Headline
- Full <=2,600-character Algorithmic "About" Section with Keyword Indexation Clusters
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
        "Platform & MLOps Engineer | Kubernetes (EKS, kubeadm) · Docker · Helm · "
        "Terraform · Ansible · ArgoCD · CI/CD · Prometheus · Kafka · Python · Rust | 2.5 YOE | 15 Days Notice"
    ),
    "headline_length": 173,  # Under 220-character limit
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
        "Platform, DevOps & MLOps Infrastructure Engineer with ~2.5 years of experience operating high-availability "
        "Kubernetes platforms (50-node kubeadm, AWS EKS), CI/CD automation pipelines, and stateful data backbones.\n\n"
        "At CGI India, standardized multi-tenant AWS EKS deployments via modular Terraform and Ansible, hardened "
        "Nginx/Kong ingress gateways, and automated Jenkins/GitLab CI + Trivy pipelines and ArgoCD/Helm GitOps. "
        "At HFCL Limited, automated 50-node bare-metal kubeadm clusters with 40+ Ansible roles (2 days -> 4 hours, "
        "83% faster bootstrap), sustained 99.95% availability across 15+ microservices, and managed Kafka, Redis, "
        "PostgreSQL, TimescaleDB, and MongoDB StatefulSets with Velero DR (RTO 8h -> 30min, 93%; MTTR -45%).\n\n"
        "⚡ CORE TECHNICAL EXPERTISE:\n"
        "• Platform & Orchestration: Kubernetes (kubeadm, AWS EKS), Docker, containerd, Helm, ArgoCD, Harbor, RBAC, HPA.\n"
        "• IaC, CI/CD & Security: Terraform (modular IaC), Ansible (40+ roles, Jinja2), Jenkins, GitLab CI, GitHub Actions, Trivy, SonarQube, Nginx/Kong.\n"
        "• Observability & SRE: Prometheus, Grafana, Alertmanager, ELK Stack (Elasticsearch, Logstash Grok, Kibana), Velero DR.\n"
        "• Data & Streaming Backbones: Apache Kafka, Redis, PostgreSQL, TimescaleDB, MongoDB, pgvector (HNSW), MinIO S3.\n"
        "• Open-Source AI & Data Projects: AegisAgent (github.com/lavkushry/AegisAgent, Rust/Cedar/K8s <75ms policy eval), "
        "Project Vulcan (github.com/lavkushry/vulcan, FastAPI/pgvector/Redis Redlock), and Azure Medallion Lakehouse "
        "(github.com/lavkushry/Azure-Data-Engineering-Medallion-Lakehouse-Project, PySpark/Databricks/Delta Lake/ADF).\n\n"
        "📍 Current Location: Bangalore, India\n"
        "🎯 Preferred Hubs: Bengaluru, Hyderabad, Pune, Gurugram, Noida, Mumbai, Chennai, Remote\n"
        "⏱ Notice Period: 15 Days or less (Immediate Joiner)\n"
        "📫 Contact: lav84095@gmail.com | +91-9122036484 | https://www.linkedin.com/in/lavkushry/ | https://github.com/lavkushry"
    ),
    "experience": [
        {
            "company": "CGI India",
            "title": "DevOps Engineer",
            "dates": "June 2026 – Present",
            "location": "Bangalore, India",
            "bullets": [
                "Standardized multi-tenant AWS EKS container platform deployments using modular Terraform and Ansible, establishing reproducible cluster baselines, auto-scaling node groups, and IAM roles across 3 environments.",
                "Engineered automated CI/CD pipelines in Jenkins and GitLab CI with Trivy vulnerability scanning, container linting, and staging smoke tests.",
                "Hardened cluster ingress and API gateway policies using Nginx Ingress and Kong Gateway (rate-limiting, TLS termination), and automated GitOps rollouts with ArgoCD and Helm charts."
            ],
            "skills": [
                "Kubernetes", "AWS EKS", "Terraform", "Ansible", "Docker", "Helm", "ArgoCD", "Jenkins", "GitLab CI", "Linux"
            ]
        },
        {
            "company": "HFCL Limited",
            "title": "Engineer 1 — DevOps / Platform Engineering",
            "dates": "August 2025 – June 2026",
            "location": "Bangalore, India",
            "bullets": [
                "Automated bare-metal Kubernetes (kubeadm) cluster lifecycle via 40+ Ansible roles and Jinja2 templates (OS hardening, CNI, Harbor, Helm), reducing bootstrap time from 2 days to 4 hours (83% reduction).",
                "Operated a 50-node on-premise Kubernetes platform for 15+ distributed microservices with namespace isolation, RBAC, and HPA, sustaining 99.95% platform availability.",
                "Orchestrated stateful cluster workloads (Apache Kafka, Redis, PostgreSQL, TimescaleDB, MongoDB) via StatefulSets; configured Velero DR and Prometheus/Grafana alerts, cutting RTO from 8h to 30min (93%) and MTTR by 45%.",
                "Standardized declarative Jenkins pipelines with Docker, Helm, SonarQube, and Trivy security gates, doubling release frequency (2x) with zero-downtime rolling updates."
            ],
            "skills": [
                "Kubernetes", "Ansible", "Docker", "Helm", "Apache Kafka", "Redis", "Prometheus", "Grafana", "Linux", "Terraform"
            ]
        },
        {
            "company": "CGI India",
            "title": "Security Analyst Apprentice",
            "dates": "September 2024 – August 2025",
            "location": "Bangalore, India",
            "bullets": [
                "Centralized multi-source log ingestion using the ELK Stack (Elasticsearch, Logstash, Kibana), designing operational dashboards that reduced root-cause investigation time by 35%.",
                "Authored custom Grok parsing patterns in Logstash to parse high-volume syslog and firewall/IDS telemetry streams into structured fields, cutting log triage time by 45%."
            ],
            "skills": [
                "ELK Stack", "Logstash", "Elasticsearch", "Kibana", "Python", "SQL", "Linux"
            ]
        },
        {
            "company": "Stipe Solutions",
            "title": "Full Stack Developer Intern",
            "dates": "March 2024 – September 2024",
            "location": "Bangalore, India",
            "bullets": [
                "Developed 30+ cross-platform mobile application screens (React Native, Flutter) and RESTful API integrations with PostgreSQL optimization for 1,000+ daily active users."
            ],
            "skills": [
                "Python", "Docker", "REST APIs", "SQL", "PostgreSQL", "GitHub Actions", "Git"
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
        "Ansible",
        "ArgoCD",
        "AWS EKS",
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
        "GitOps",
        "Site Reliability Engineering",
        "Infrastructure as Code (IaC)"
    ]
}
LINKEDIN_100K_MLOPS_BLUEPRINT["employment_history"] = LINKEDIN_100K_MLOPS_BLUEPRINT["experience"]


def get_100k_blueprint(persona: str = "mlops") -> Dict[str, Any]:
    """Returns canonical 100K blueprint grounded in 01_FACT_MATRIX.md."""
    if str(persona).lower() in ("mlops", "ai", "platform"):
        return LINKEDIN_100K_MLOPS_BLUEPRINT
    return LINKEDIN_100K_BLUEPRINT

# ==============================================================================
# CANONICAL 100K+ LINKEDIN RECRUITER BLUEPRINT (UNIFIED PLATFORM & DATA INFRA)
# ==============================================================================

LINKEDIN_100K_BLUEPRINT: Dict[str, Any] = {
    "headline": (
        "Platform & MLOps Engineer | Kubernetes (EKS, kubeadm) · Terraform · Ansible · "
        "Docker · Helm · ArgoCD · CI/CD · Kafka · Prometheus · Python · Rust | 2.5 YOE | 15 Days Notice"
    ),
    "headline_length": 173,  # Under 220-character limit
    "target_titles": [
        "Platform Engineer",
        "MLOps Engineer",
        "DevOps Engineer",
        "AI Infrastructure Engineer",
        "Cloud Infrastructure Engineer"
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
            "Platform Engineer",
            "MLOps Engineer",
            "DevOps Engineer",
            "AI Infrastructure Engineer",
            "Cloud Infrastructure Engineer"
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
    "about": LINKEDIN_100K_MLOPS_BLUEPRINT["about"],
    "experience": LINKEDIN_100K_MLOPS_BLUEPRINT["experience"],
    "top_50_skills": LINKEDIN_100K_MLOPS_BLUEPRINT["top_50_skills"],
}
LINKEDIN_100K_BLUEPRINT["employment_history"] = LINKEDIN_100K_BLUEPRINT["experience"]


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
        "aws"
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
        "ansible",
        "velero",
        "argocd",
        "kafka",
        "elk stack",
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
        has_mlops_signal = (
            "mlops" in hl_lower
            or "mlops" in ab_lower
            or "mlops" in cur_t_lower
            or any("kubernetes" in s or "mlops" in s for s in sk_lower[:5])
        )
        is_mlops = (
            persona.lower() in ("mlops", "ai", "platform")
            or (persona.lower() == "auto" and has_mlops_signal)
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
        ab_matches = sum(
            1 for kw in crit_keywords
            if kw in ab_lower or kw in hl_lower or any(kw in s for s in sk_lower)
        )
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
            top3_target = ["kubernetes", "docker", "terraform"]
            top3_labels = ["Kubernetes", "Docker", "Terraform"]
        else:
            top3_target = ["azure databricks", "pyspark", "azure data factory"]
            top3_labels = ["Azure Databricks", "PySpark", "Azure Data Factory (ADF)"]

        top3_present = sum(1 for t in top3_target if any(t in s for s in sk_lower[:6]))
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
                score += 12.0
                findings.append(f"✓ Current designation '{cur_t}' reflects verified production DevOps/Platform tenure.")
                recommendations.append("Keep current designation truthful ('DevOps Engineer') and highlight project-only data stack under Projects.")
            else:
                score += 5.0
                recommendations.append("Align current job title to 'DevOps Engineer' or 'Platform Engineer' per 01_FACT_MATRIX.md.")

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

    bp = LINKEDIN_100K_MLOPS_BLUEPRINT
    exp0 = bp["experience"][0]
    exp1 = bp["experience"][1]
    md_content = f"""# 🚀 LinkedIn 100k+ Search Appearances Blueprint: Platform, DevOps & MLOps Engineer
**Candidate:** Lavkush Kumar (~2.5 YOE | Target: ₹20–25 LPA | Notice: 15 Days or less)  
**Goal:** 100,000+ Monthly LinkedIn Recruiter Search Appearances in Platform / DevOps / MLOps Engineering  
**Algorithm Target:** LinkedIn Recruiter (RPS) Boolean Search & Recruiter Spotlights  

---

## 1. Profile Headline (Strict 220-Character Recruiter SEO Standard)

> **Headline Text (Copy & Paste to LinkedIn):**
```text
{bp["headline"]}
```
* **Character Count:** {len(bp["headline"])} / 220 chars (Optimized to prevent truncation while packing core Platform/MLOps search tokens).

---

## 2. "Open to Work" Configuration (Private to Recruiters Only)

* **Job Titles (Max 5):** `{', '.join(bp["open_to_work_settings"]["job_titles"])}`
* **Locations:** `{', '.join(bp["open_to_work_settings"]["locations_on_site"])}` + `Remote`
* **Start Date:** `Immediately, I'm actively applying`
* **Employment Types:** `Full-time`, `Contract`
* **Visibility:** **Recruiters only**

---

## 3. "About" Section (2,600-Character Algorithmic Keyword Index)

> **About Text (Copy & Paste to LinkedIn):**
```text
{bp["about"]}
```

---

## 4. Experience Section (Canonical `01_FACT_MATRIX.md` Alignment)

### Role 1: Current Employment
* **Company:** `{exp0["company"]}`
* **Designation:** `{exp0["title"]}`
* **Dates:** `{exp0["dates"]}`
* **Location:** `{exp0["location"]}`
* **Description:**
```text
{chr(10).join("• " + b for b in exp0["bullets"])}

Skills: {' · '.join(exp0["skills"])}
```

### Role 2: Previous Employment
* **Company:** `{exp1["company"]}`
* **Designation:** `{exp1["title"]}`
* **Dates:** `{exp1["dates"]}`
* **Location:** `{exp1["location"]}`
* **Description:**
```text
{chr(10).join("• " + b for b in exp1["bullets"])}

Skills: {' · '.join(exp1["skills"])}
```

---

## 5. Top 50 Skills Taxonomy (Recruiter Filter Saturation)

### 📌 Top 3 Pinned Skills (Priority 1)
1. **`{bp["top_50_skills"][0]}`**
2. **`{bp["top_50_skills"][1]}`**
3. **`{bp["top_50_skills"][2]}`**

### Remaining 47 Skills (Full Category Saturation):
```text
{', '.join(bp["top_50_skills"][3:])}
```

---

## 6. The Math of 100k+ Search Appearances
* **5 Open-to-Work Job Titles x 7 Tier-1 Indian Tech Hubs x 50 Indexed Skills** = Maximum LinkedIn Recruiter (RPS) Boolean query surface across daily DevOps, Platform, and MLOps recruiter searches.
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
