"""
naukariPro Agent Platform Dispatchers: Naukri Adapter
Module: naukari_pro.agent.dispatchers.naukri_dispatcher

Adapts AutoApplyEngine for unified intent-based dispatch on Naukri.com.
Supports offline dry-run evaluation and live 1-click/questionnaire application cycles.
"""

from __future__ import annotations

import time
import logging
from typing import Dict, List, Optional, Any

from naukari_pro.agent.dispatchers.base import BasePlatformDispatcher, PlatformExecutionReport
from naukari_pro.modules.auto_apply import AutoApplyEngine, ApplicationPayload
from naukari_pro.modules.db import is_job_already_applied, generate_job_id, DB_PATH

logger = logging.getLogger("naukariPro.Agent.Dispatchers.Naukri")


class NaukriDispatcher(BasePlatformDispatcher):
    """
    Adapter for Naukri.com application automation.
    Wraps AutoApplyEngine with CandidateIntent parameter mapping, deduplication gating,
    and standardized PlatformExecutionReport generation.
    """
    platform_name: str = "naukri"

    def __init__(
        self,
        engine: Optional[AutoApplyEngine] = None,
        timeout_seconds: Optional[float] = None,
        headless: bool = True,
        db_path: Optional[str] = None,
        config_path: Optional[str] = None
    ):
        super().__init__(timeout_seconds=timeout_seconds)
        self.engine = engine or AutoApplyEngine(dry_run=False)
        self.headless = headless
        self.db_path = db_path or DB_PATH
        self.config_path = config_path

    def _generate_synthetic_feed(self, roles: List[str], locations: List[str]) -> List[Dict[str, Any]]:
        """Generates realistic test vacancies for offline evaluation aligned with intent."""
        primary_role = roles[0] if roles else "MLOps Engineer"
        sec_role = roles[1] if len(roles) > 1 else "ML Platform Engineer"
        loc = locations[0] if locations else "Bengaluru"

        return [
            {
                "title": f"Lead {primary_role}",
                "company": "Microsoft GCC",
                "salary": "24 - 32 Lacs PA",
                "url": "https://www.naukri.com/job-msft-mlops-001",
                "location": loc,
                "jd": "Azure Databricks PySpark Delta Lake Kubernetes Docker Terraform PyTorch MLflow CI/CD vLLM Triton AWS Python"
            },
            {
                "title": f"{sec_role}",
                "company": "Walmart Global Tech",
                "salary": "22 - 28 Lacs PA",
                "url": "https://www.naukri.com/job-walmart-platform-002",
                "location": loc,
                "jd": "Azure Databricks PySpark Delta Lake Kubernetes Docker Helm ArgoCD Prometheus Grafana FastAPI Python"
            },
            {
                "title": f"Senior {primary_role}",
                "company": "Amazon AWS",
                "salary": "26 - 35 Lacs PA",
                "url": "https://www.naukri.com/job-amzn-infra-003",
                "location": loc,
                "jd": "Azure Databricks PySpark Delta Lake Docker Kubernetes Terraform MLflow Ray Triton Python Linux"
            },
            {
                "title": "Junior PHP Web Developer",
                "company": "Agency",
                "salary": "6 - 8 Lacs PA",
                "url": "https://www.naukri.com/job-agency-004",
                "location": loc,
                "jd": "HTML CSS PHP WordPress MySQL"
            },
            {
                "title": "Frontend React Engineer",
                "company": "Fintech Startup",
                "salary": "18 - 24 Lacs PA",
                "url": "https://www.naukri.com/job-startup-005",
                "location": loc,
                "jd": "React Redux TypeScript Tailwind CSS"
            }
        ]

    def dispatch_dry_run(self, intent: Any) -> PlatformExecutionReport:
        """
        Executes 100% offline dry-run evaluation for Naukri.
        Evaluates salary acceptable gate, match score gate (>= threshold), and dedup.
        """
        start_time = time.time()
        report = PlatformExecutionReport(platform_name=self.platform_name, dry_run=True)

        limit = getattr(intent, "max_applications", 15)
        min_score = getattr(intent, "strict_match_threshold", 70.0)
        target_roles = getattr(intent, "target_roles", ["MLOps Engineer"])
        target_locations = getattr(intent, "target_locations", ["Bengaluru"])

        feed = self._generate_synthetic_feed(target_roles, target_locations)
        report.total_evaluated = len(feed)

        # Configure engine for dry-run
        self.engine.dry_run = True
        payloads: List[ApplicationPayload] = self.engine.run_offline_dry_run(job_feed=feed, limit=limit)

        for p in payloads:
            title = p.job_title or p.title or "Role"
            company = p.company or "Company"
            url = p.url or "N/A"
            score = float(p.match_score or 0.0)
            job_id = getattr(p, "job_id", None) or getattr(p, "id", None) or generate_job_id(title, company, url)

            # Deduplication gate check
            if is_job_already_applied(title=title, company=company, job_url=url, job_id=job_id, db_path=self.db_path):
                report.add_record({
                    "job_id": job_id,
                    "platform": self.platform_name,
                    "title": title,
                    "company": company,
                    "url": url,
                    "status": "SKIPPED_DUPLICATE",
                    "match_score": score,
                    "salary": p.salary
                })
                continue

            if p.status == "VALIDATED_PAYLOAD" and score >= min_score:
                report.add_record({
                    "job_id": job_id,
                    "platform": self.platform_name,
                    "title": title,
                    "company": company,
                    "url": url,
                    "status": "SUBMITTED_DRY_RUN",
                    "match_score": score,
                    "salary": p.salary,
                    "portal_type": p.portal_type,
                    "answers": p.answers
                })
            else:
                report.add_record({
                    "job_id": job_id,
                    "platform": self.platform_name,
                    "title": title,
                    "company": company,
                    "url": url,
                    "status": p.status,
                    "match_score": score,
                    "salary": p.salary
                })

        report.duration_seconds = time.time() - start_time
        return report

    def _execute_live(self, intent: Any) -> PlatformExecutionReport:
        """Executes live application automation on Naukri."""
        start_time = time.time()
        report = PlatformExecutionReport(platform_name=self.platform_name, dry_run=False)

        limit = getattr(intent, "max_applications", 15)
        applied_count = self.engine.run(
            headless=self.headless,
            limit=limit,
            dry_run=False
        )

        report.total_evaluated = applied_count
        report.submitted_count = applied_count
        report.duration_seconds = time.time() - start_time
        report.success = True
        return report
