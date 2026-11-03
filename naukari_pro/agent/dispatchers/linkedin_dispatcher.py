"""
naukariPro Agent Platform Dispatchers: LinkedIn Adapter
Module: naukari_pro.agent.dispatchers.linkedin_dispatcher

Adapts LinkedInApplyEngine for unified intent-based dispatch on LinkedIn.
Bridges async Playwright execution safely to synchronous dispatcher protocol.
"""

from __future__ import annotations

import time
import asyncio
import logging
import concurrent.futures
from typing import Dict, List, Optional, Any, Callable

from naukari_pro.agent.dispatchers.base import BasePlatformDispatcher, PlatformExecutionReport
from naukari_pro.modules.linkedin_apply import LinkedInApplyEngine
from naukari_pro.modules.db import is_job_already_applied, generate_job_id, DB_PATH

logger = logging.getLogger("naukariPro.Agent.Dispatchers.LinkedIn")


class LinkedInDispatcher(BasePlatformDispatcher):
    """
    Adapter for LinkedIn Easy Apply automation.
    Wraps LinkedInApplyEngine with async-to-sync event loop isolation,
    circuit breaker shielding, and deduplication gating.
    """
    platform_name: str = "linkedin"

    def __init__(
        self,
        engine: Optional[LinkedInApplyEngine] = None,
        timeout_seconds: Optional[float] = None,
        headless: bool = True,
        db_path: Optional[str] = None,
        config_path: Optional[str] = None
    ):
        super().__init__(timeout_seconds=timeout_seconds)
        self.engine = engine or LinkedInApplyEngine()
        self.headless = headless
        self.db_path = db_path or DB_PATH
        self.config_path = config_path

    def _generate_synthetic_vacancies(self, roles: List[str], locations: List[str]) -> List[Dict[str, Any]]:
        """Generates realistic synthetic LinkedIn Easy Apply vacancies."""
        primary_role = roles[0] if roles else "MLOps Engineer"
        sec_role = roles[1] if len(roles) > 1 else "ML Platform Engineer"
        loc = locations[0] if locations else "Bengaluru"

        return [
            {
                "job_id": "4188001001",
                "title": f"Lead {primary_role}",
                "company": "Microsoft GCC",
                "location": loc,
                "url": "https://www.linkedin.com/jobs/view/4188001001/",
                "raw_snippet": "Required 2-4 years experience in Kubernetes, Docker, Terraform, MLflow, PyTorch, vLLM, and AWS. Notice period 15-30 days."
            },
            {
                "job_id": "4188001002",
                "title": f"{sec_role}",
                "company": "Walmart Global Tech",
                "location": loc,
                "url": "https://www.linkedin.com/jobs/view/4188001002/",
                "raw_snippet": "Looking for Engineer with 2-3 years hands-on experience in Kubernetes, Docker, Helm, ArgoCD, Prometheus, Grafana, and CI/CD."
            },
            {
                "job_id": "4188001003",
                "title": f"Senior {primary_role}",
                "company": "Amazon AWS",
                "location": loc,
                "url": "https://www.linkedin.com/jobs/view/4188001003/",
                "raw_snippet": "Seeking 2-5 years experience with Docker, Kubernetes, Terraform, MLflow, Ray, Triton Inference Server, and Python."
            },
            {
                "job_id": "4188001004",
                "title": "Principal Enterprise Architect",
                "company": "Legacy Corp",
                "location": loc,
                "url": "https://www.linkedin.com/jobs/view/4188001004/",
                "raw_snippet": "Requires 15+ years experience directing enterprise strategy, SAP ERP migration, and multimillion IT governance."
            }
        ]

    def dispatch_dry_run(self, intent: Any) -> PlatformExecutionReport:
        """
        Executes 100% offline dry-run evaluation for LinkedIn.
        Evaluates synthetic vacancies through JobMatchScorer and LinkedInScreeningSolver.
        """
        start_time = time.time()
        report = PlatformExecutionReport(platform_name=self.platform_name, dry_run=True)

        limit = getattr(intent, "max_applications", 15)
        min_score = getattr(intent, "strict_match_threshold", 70.0)
        roles = getattr(intent, "target_roles", ["MLOps Engineer"])
        locations = getattr(intent, "target_locations", ["Bengaluru"])

        synthetic_feed = self._generate_synthetic_vacancies(roles, locations)

        stats = self.engine.run_offline_dry_run(
            keywords=roles,
            locations=locations,
            limit=limit,
            min_score=min_score,
            synthetic_vacancies=synthetic_feed
        )

        report.total_evaluated = stats.get("discovered", len(synthetic_feed))

        for job in stats.get("jobs", []):
            title = job.get("title", "Role")
            company = job.get("company", "Company")
            job_id = str(job.get("job_id") or job.get("id") or "")
            url = job.get("url") or (f"https://www.linkedin.com/jobs/view/{job_id}" if job_id else "N/A")
            score = float(job.get("score", 0.0))
            if not job_id:
                job_id = generate_job_id(title, company, url)

            # Deduplication check
            if is_job_already_applied(title=title, company=company, job_url=url, job_id=job_id, db_path=self.db_path):
                report.add_record({
                    "job_id": job_id,
                    "platform": self.platform_name,
                    "title": title,
                    "company": company,
                    "url": url,
                    "status": "SKIPPED_DUPLICATE",
                    "match_score": score
                })
                continue

            if job.get("success") or job.get("status") in ("SUBMITTED_DRY_RUN", "APPLIED", "VALIDATED"):
                report.add_record({
                    "job_id": job_id,
                    "platform": self.platform_name,
                    "title": title,
                    "company": company,
                    "url": url,
                    "status": "SUBMITTED_DRY_RUN",
                    "match_score": score,
                    "salary": job.get("salary", "20 - 28 Lacs PA")
                })
            else:
                report.add_record({
                    "job_id": job_id,
                    "platform": self.platform_name,
                    "title": title,
                    "company": company,
                    "url": url,
                    "status": job.get("status", "GATED_OUT"),
                    "match_score": score
                })

        report.duration_seconds = time.time() - start_time
        return report

    def _execute_live(self, intent: Any) -> PlatformExecutionReport:
        """
        Executes live LinkedIn Easy Apply cycle.
        Bridges async run_apply_cycle into isolated worker thread event loop.
        """
        start_time = time.time()
        report = PlatformExecutionReport(platform_name=self.platform_name, dry_run=False)

        roles = getattr(intent, "target_roles", ["MLOps Engineer"])
        locations = getattr(intent, "target_locations", ["Bengaluru"])
        limit = getattr(intent, "max_applications", 15)

        def _run_coroutine_in_new_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    self.engine.run_apply_cycle(
                        keywords=roles,
                        locations=locations,
                        limit=limit,
                        dry_run=False,
                        headless=self.headless
                    )
                )
            finally:
                loop.close()

        # Execute inside dedicated worker thread to prevent event loop collision
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_run_coroutine_in_new_loop)
            stats = future.result(timeout=self.timeout_seconds)

        report.total_evaluated = stats.get("discovered", 0)

        for job in stats.get("jobs", []):
            report.add_record(job)

        if report.submitted_count == 0 and stats.get("applied", 0) > 0:
            report.submitted_count = stats.get("applied", 0)
        if report.skipped_count == 0 and stats.get("skipped", 0) > 0:
            report.skipped_count = stats.get("skipped", 0)
        if report.failed_count == 0 and stats.get("failed", 0) > 0:
            report.failed_count = stats.get("failed", 0)

        report.duration_seconds = time.time() - start_time
        report.success = report.failed_count == 0 or report.submitted_count > 0
        return report
