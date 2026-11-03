"""
naukariPro Agent Subsystem: Unified Autonomous Job Apply Orchestrator
Module: naukari_pro.agent.orchestrator

Coordinates multi-platform application execution across Naukri, LinkedIn,
Workday, Greenhouse, and Lever based on CandidateIntent.
Enforces deduplication via applied_jobs.db, handles per-platform timeouts,
and aggregates consolidated execution telemetry.
"""

from __future__ import annotations

import os
import copy
import time
import logging
import concurrent.futures
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Union

from naukari_pro.config import DB_PATH, load_config
from naukari_pro.agent.intent import CandidateIntent
from naukari_pro.agent.parser import IntentParser
from naukari_pro.agent.dispatchers.base import PlatformDispatcher, PlatformExecutionReport
from naukari_pro.modules.db import is_job_already_applied, record_applied_job, init_db

logger = logging.getLogger("naukariPro.AutonomousAgent")


@dataclass
class AgentExecutionSummary:
    """
    Consolidated execution summary detailing outcomes across all targeted platforms.
    Provides structured metrics, granular job records, and formatted terminal reports.
    """
    intent: CandidateIntent
    total_evaluated: int = 0
    total_submitted: int = 0
    total_skipped: int = 0
    total_dedup_skipped: int = 0
    total_errors: int = 0
    platform_reports: Dict[str, Any] = field(default_factory=dict)
    applied_jobs: List[Dict[str, Any]] = field(default_factory=list)
    skipped_jobs: List[Dict[str, Any]] = field(default_factory=list)
    duration_seconds: float = 0.0
    db_updated: bool = False
    status: str = "COMPLETED"  # "COMPLETED", "PARTIAL", "FAILED"
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Converts summary to dictionary."""
        intent_dict = (
            self.intent.to_dict()
            if hasattr(self.intent, "to_dict")
            else asdict(self.intent)
            if hasattr(self.intent, "__dataclass_fields__")
            else self.intent
        )
        return {
            "intent": intent_dict,
            "total_evaluated": self.total_evaluated,
            "total_submitted": self.total_submitted,
            "total_skipped": self.total_skipped,
            "total_dedup_skipped": self.total_dedup_skipped,
            "total_errors": self.total_errors,
            "duration_seconds": round(self.duration_seconds, 2),
            "db_updated": self.db_updated,
            "status": self.status,
            "error_message": self.error_message,
            "applied_jobs": self.applied_jobs,
            "skipped_jobs": self.skipped_jobs,
            "platform_breakdown": {
                k: (v.to_dict() if hasattr(v, "to_dict") else asdict(v) if hasattr(v, "__dataclass_fields__") else v)
                for k, v in self.platform_reports.items()
            }
        }

    def format_summary_report(self) -> str:
        """Formats a human-readable execution summary for CLI display."""
        lines = [
            "=" * 74,
            "  🎯 AUTONOMOUS JOB APPLY AGENT: MULTI-PLATFORM EXECUTION SUMMARY",
            "=" * 74,
            f"  Status:              {self.status}",
            f"  Execution Time:      {self.duration_seconds:.2f}s",
            f"  Target Roles:        {', '.join(self.intent.target_roles[:3])}",
            f"  Target Locations:    {', '.join(self.intent.target_locations[:4])}",
            f"  Target Platforms:    {', '.join(self.intent.platforms)}",
            f"  Mode:                {'DRY-RUN (Simulated)' if self.intent.dry_run else 'LIVE SUBMISSION'}",
            "-" * 74,
            f"  Total Evaluated:     {self.total_evaluated}",
            f"  Total Submitted:     {self.total_submitted} / {self.intent.max_applications}",
            f"  Total Skipped:       {self.total_skipped}",
            f"  Deduplication Gate:  {self.total_dedup_skipped} skipped (already applied)",
            f"  Total Errors:        {self.total_errors}",
            "-" * 74,
            "  Platform Breakdown:"
        ]
        for plat, rep in self.platform_reports.items():
            sub = getattr(rep, "submitted_count", getattr(rep, "total_applied", 0))
            eva = getattr(rep, "total_evaluated", 0)
            skp = getattr(rep, "skipped_count", getattr(rep, "total_skipped", 0))
            errs = len(getattr(rep, "errors", []))
            err_flag = f" [ERRORS: {errs}]" if errs > 0 else ""
            lines.append(f"    • {plat.upper():14} -> Evaluated: {eva:2} | Applied: {sub:2} | Skipped: {skp:2}{err_flag}")
        lines.append("=" * 74)
        return "\n".join(lines)


class AutonomousJobApplyAgent:
    """
    High-level orchestrator executing multi-platform candidate job applications.
    Coordinates platform dispatchers, enforces deduplication via applied_jobs.db,
    allocates application quotas, and isolates timeouts and errors.
    """

    SUPPORTED_PLATFORMS = ("naukri", "linkedin", "workday", "greenhouse", "lever", "ashby", "career_portals")

    def __init__(
        self,
        config_path: Optional[str] = None,
        dry_run: bool = False,
        db_path: Optional[str] = None,
        per_platform_timeout_seconds: float = 120.0,
        headless: bool = True
    ):
        self.config_path = config_path
        self.dry_run = dry_run
        self.db_path = db_path or DB_PATH
        self.per_platform_timeout_seconds = per_platform_timeout_seconds
        self.headless = headless
        self.dispatchers: Dict[str, PlatformDispatcher] = {}

        # Ensure DB is initialized
        try:
            init_db(self.db_path)
        except Exception as e:
            logger.warning(f"Could not auto-initialize DB at {self.db_path}: {e}")

    def register_dispatcher(self, platform_name: str, dispatcher: PlatformDispatcher) -> None:
        """Explicitly registers a platform dispatcher adapter."""
        key = platform_name.lower().strip()
        if hasattr(dispatcher, "db_path") and getattr(dispatcher, "db_path", None) is None:
            try:
                dispatcher.db_path = self.db_path
            except Exception:
                pass
        self.dispatchers[key] = dispatcher
        logger.debug(f"Registered dispatcher for platform '{key}': {dispatcher.__class__.__name__}")

    def get_dispatcher(self, platform_name: str) -> Optional[PlatformDispatcher]:
        """Resolves dispatcher from registry or lazily instantiates default adapter."""
        key = platform_name.lower().strip()
        if key in self.dispatchers:
            return self.dispatchers[key]

        # Lazy loading of default dispatchers
        try:
            if key == "naukri":
                from naukari_pro.agent.dispatchers.naukri_dispatcher import NaukriDispatcher
                self.dispatchers[key] = NaukriDispatcher(
                    config_path=self.config_path,
                    db_path=self.db_path,
                    headless=self.headless,
                    timeout_seconds=self.per_platform_timeout_seconds
                )
                return self.dispatchers[key]
            elif key == "linkedin":
                from naukari_pro.agent.dispatchers.linkedin_dispatcher import LinkedInDispatcher
                self.dispatchers[key] = LinkedInDispatcher(
                    config_path=self.config_path,
                    db_path=self.db_path,
                    headless=self.headless,
                    timeout_seconds=self.per_platform_timeout_seconds
                )
                return self.dispatchers[key]
            elif key in ("workday", "greenhouse", "lever", "ashby", "career_portals"):
                from naukari_pro.agent.dispatchers.ats_dispatcher import ExternalATSDispatcher
                ats_type = key if key != "career_portals" else None
                dispatcher = ExternalATSDispatcher(
                    platform_name=key,
                    ats_type=ats_type,
                    config_path=self.config_path,
                    db_path=self.db_path,
                    headless=self.headless,
                    timeout_seconds=self.per_platform_timeout_seconds
                )
                self.dispatchers[key] = dispatcher
                return dispatcher
        except ImportError as exc:
            logger.warning(f"Could not auto-import dispatcher for '{key}': {exc}")

        return None

    def execute_intent(
        self,
        intent_or_input: Union[CandidateIntent, Dict[str, Any], str, None] = None,
        **overrides
    ) -> AgentExecutionSummary:
        """
        Main execution entry point: translates intent into multi-platform applications.
        """
        start_time = time.time()

        # 1. Parse / resolve CandidateIntent
        if isinstance(intent_or_input, CandidateIntent):
            intent = intent_or_input
        else:
            intent = IntentParser.parse(intent_or_input, **overrides)

        # Agent-level dry_run override
        if self.dry_run:
            intent.dry_run = True

        # Validation guard
        if not intent.target_roles or not intent.target_locations or not intent.platforms:
            return AgentExecutionSummary(
                intent=intent,
                status="FAILED",
                error_message="Invalid intent: target_roles, target_locations, and platforms must be non-empty."
            )

        requested_platforms = [
            p.lower().strip() for p in intent.platforms
            if p.lower().strip() in self.SUPPORTED_PLATFORMS
        ]
        if not requested_platforms:
            return AgentExecutionSummary(
                intent=intent,
                status="FAILED",
                error_message=f"No supported platforms requested in intent: {intent.platforms}"
            )

        # 2. Partition Quota across platforms
        total_limit = max(1, intent.max_applications)
        num_platforms = len(requested_platforms)
        base_quota = max(1, total_limit // num_platforms)

        summary = AgentExecutionSummary(intent=intent)
        total_applied_so_far = 0

        # 3. Iterate over platforms sequentially
        for idx, platform_name in enumerate(requested_platforms):
            if total_applied_so_far >= total_limit:
                logger.info(f"Application limit ({total_limit}) reached. Skipping remaining platforms.")
                break

            remaining_quota = total_limit - total_applied_so_far
            # Last platform gets whatever quota remains, otherwise min(base_quota, remaining_quota)
            platform_limit = remaining_quota if idx == num_platforms - 1 else min(base_quota, remaining_quota)

            dispatcher = self.get_dispatcher(platform_name)
            if not dispatcher:
                logger.error(f"No dispatcher available for platform '{platform_name}'. Skipping.")
                summary.total_errors += 1
                summary.platform_reports[platform_name] = PlatformExecutionReport(
                    platform_name=platform_name,
                    success=False,
                    errors=[f"No dispatcher registered or found for '{platform_name}'"]
                )
                continue

            # Clone intent with platform-specific limit
            platform_intent = copy.deepcopy(intent)
            platform_intent.max_applications = platform_limit

            logger.info(f"Dispatching to platform '{platform_name}' (target quota: {platform_limit})...")

            # 4. Execute dispatch with per-platform timeout protection
            report = self._dispatch_with_timeout(dispatcher, platform_intent, is_dry_run=intent.dry_run)

            # 5. Process platform report & deduplication gating
            summary.platform_reports[platform_name] = report
            summary.total_evaluated += report.total_evaluated
            summary.total_skipped += getattr(report, "skipped_count", getattr(report, "total_skipped", 0))
            summary.total_dedup_skipped += getattr(report, "dedup_skipped_count", getattr(report, "dedup_skipped", 0))

            if not report.success or report.errors:
                summary.total_errors += len(report.errors) if report.errors else 1

            # Tally and persist applied jobs
            applied_jobs_source = getattr(report, "applied_jobs", report.records)
            for job in applied_jobs_source:
                status = str(job.get("status", "")).upper()
                # Skip jobs that were not applied or validated
                if "SUBMITTED" not in status and "APPLIED" not in status and "VALIDATED" not in status:
                    continue

                if total_applied_so_far >= total_limit:
                    break

                # Post-dispatch safety deduplication check
                is_dup = is_job_already_applied(
                    title=job.get("title"),
                    company=job.get("company"),
                    job_url=job.get("job_url") or job.get("url"),
                    job_id=job.get("job_id"),
                    db_path=self.db_path
                )

                if is_dup:
                    summary.total_dedup_skipped += 1
                    summary.skipped_jobs.append({
                        "job_id": job.get("job_id"),
                        "company": job.get("company"),
                        "title": job.get("title"),
                        "platform": platform_name,
                        "reason": "Duplicate detected at orchestrator gate"
                    })
                    continue

                total_applied_so_far += 1
                summary.total_submitted += 1
                summary.applied_jobs.append(job)

                # Persist to SQLite DB if in live mode
                if not intent.dry_run:
                    try:
                        record_applied_job(
                            title=job.get("title", "Unknown Role"),
                            company=job.get("company", "Unknown Company"),
                            platform=platform_name,
                            location=job.get("location", "Bangalore"),
                            match_score=float(job.get("match_score", 70.0)),
                            status="Submitted (Pending)",
                            job_url=job.get("job_url") or job.get("url", "N/A"),
                            job_id=job.get("job_id"),
                            db_path=self.db_path
                        )
                        summary.db_updated = True
                    except Exception as e:
                        logger.error(f"Failed to record applied job to DB: {e}")

            summary.skipped_jobs.extend(getattr(report, "skipped_jobs", []))

        # 6. Finalize Summary Status
        summary.duration_seconds = time.time() - start_time
        if summary.total_errors == 0:
            summary.status = "COMPLETED"
        elif summary.total_submitted > 0:
            summary.status = "PARTIAL"
        else:
            summary.status = "FAILED"
            summary.error_message = f"Execution failed across all {len(requested_platforms)} platforms."

        return summary

    def _dispatch_with_timeout(
        self,
        dispatcher: PlatformDispatcher,
        intent: CandidateIntent,
        is_dry_run: bool
    ) -> PlatformExecutionReport:
        """Executes a dispatcher call wrapped in a ThreadPoolExecutor with timeout."""
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        target_fn = dispatcher.dispatch_dry_run if is_dry_run else dispatcher.dispatch
        future = executor.submit(target_fn, intent)
        try:
            report = future.result(timeout=self.per_platform_timeout_seconds)
            executor.shutdown(wait=False, cancel_futures=True)
            return report
        except concurrent.futures.TimeoutError:
            logger.error(f"Platform {dispatcher.platform_name} timed out after {self.per_platform_timeout_seconds}s")
            executor.shutdown(wait=False, cancel_futures=True)
            return PlatformExecutionReport(
                platform_name=dispatcher.platform_name,
                success=False,
                errors=[f"Execution timed out after {self.per_platform_timeout_seconds} seconds"]
            )
        except Exception as exc:
            logger.exception(f"Platform {dispatcher.platform_name} error: {exc}")
            executor.shutdown(wait=False, cancel_futures=True)
            return PlatformExecutionReport(
                platform_name=dispatcher.platform_name,
                success=False,
                errors=[f"Exception during dispatch: {str(exc)}"]
            )
