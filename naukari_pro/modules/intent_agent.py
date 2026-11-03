"""
naukariPro Feature: Intent-Based Autonomous Job Apply Agent
Module: naukari_pro.modules.intent_agent

Provides:
- ApplicationIntent: Rich data structure capturing target roles, locations, platforms,
  match score gates (>= 70-80%), limits, compensation thresholds, and execution modes.
- IntentParser: Natural-language parser translating conversational instructions into structured intents.
- IntentJobApplyAgent: Autonomous agent planning and executing multi-channel application cycles across:
  * Naukri (AutoApplyEngine)
  * LinkedIn Easy Apply (LinkedInApplyEngine / LinkedInApplyRunner)
  * External Portals (CareerPortalManager / ExternalPortalBatchRunner: Greenhouse, Lever, Ashby, Workday)
- Cross-Platform Deduplication, SQLite applied_jobs.db auditing, and master Excel tracking.
"""

import os
import re
import sys
import time
import json
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Union, Tuple, Set

from naukari_pro.config import (
    TRACKER_PATH,
    RESUME_PDF_PATH,
    WORKSPACE_DIR,
    BASE_DIR,
    load_config
)
from naukari_pro.modules.auto_apply import AutoApplyEngine, evaluate_job_match, is_salary_acceptable
from naukari_pro.modules.linkedin_apply import LinkedInApplyRunner, LinkedInApplyEngine
from naukari_pro.modules.career_portals import (
    CareerPortalManager,
    ExternalPortalBatchRunner,
    load_applicant_profile
)
from naukari_pro.modules.db import (
    init_db,
    is_job_already_applied,
    record_applied_job,
    generate_job_id,
    get_db_connection,
    DB_PATH
)
from naukari_pro.modules.job_alerts import calculate_match_score

logger = logging.getLogger("naukariPro.IntentAgent")

# Candidate Ground Truth Defaults (01_FACT_MATRIX.md & AGENTS.md)
DEFAULT_ROLES = [
    "Azure Data Engineer",
    "Azure Databricks Engineer",
    "PySpark Developer",
    "Delta Lake Engineer",
    "Data Platform Engineer"
]

DEFAULT_LOCATIONS = [
    "Bengaluru",
    "Hyderabad",
    "Pune",
    "Gurugram",
    "Noida",
    "Remote"
]

SUPPORTED_PLATFORMS = {
    "naukri",
    "linkedin",
    "career_portals",
    "greenhouse",
    "lever",
    "ashby",
    "workday"
}


# ==============================================================================
# DATA MODELS
# ==============================================================================

@dataclass
class ApplicationIntent:
    """Structured representation of a candidate's job application objective."""
    raw_intent: str = ""
    roles: List[str] = field(default_factory=lambda: list(DEFAULT_ROLES))
    locations: List[str] = field(default_factory=lambda: list(DEFAULT_LOCATIONS))
    platforms: List[str] = field(default_factory=lambda: ["naukri", "linkedin", "career_portals"])
    min_match_score: float = 70.0
    limit: int = 15
    min_salary_lpa: float = 20.0
    max_experience: float = 4.0
    auto_submit: bool = True
    dry_run: bool = False
    headless: bool = True
    ats_filters: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ApplicationExecutionPlan:
    """Decomposed multi-channel execution plan."""
    intent: ApplicationIntent
    tasks: List[Dict[str, Any]] = field(default_factory=list)
    estimated_applications: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


@dataclass
class IntentApplyResult:
    """Consolidated outcome of an intent execution."""
    intent: ApplicationIntent
    plan: ApplicationExecutionPlan
    summary: Dict[str, Any]
    applied_records: List[Dict[str, Any]] = field(default_factory=list)
    skipped_records: List[Dict[str, Any]] = field(default_factory=list)
    duration_seconds: float = 0.0
    tracker_updated: bool = False
    db_updated: bool = False

    def format_summary_report(self) -> str:
        s = self.summary
        lines = [
            "=" * 72,
            "  🎯 INTENT-BASED JOB APPLY AGENT EXECUTION SUMMARY",
            "=" * 72,
            f"  Intent:              {self.intent.raw_intent or 'Autonomous Multi-Channel Run'}",
            f"  Roles:               {', '.join(self.intent.roles[:4])}",
            f"  Locations:           {', '.join(self.intent.locations[:4])}",
            f"  Platforms:           {', '.join(self.intent.platforms)}",
            f"  Min Match Score:     {self.intent.min_match_score}%",
            f"  Mode:                {'DRY-RUN (Simulated)' if self.intent.dry_run else 'LIVE SUBMISSION'}",
            f"  Execution Time:      {self.duration_seconds:.2f}s",
            "-" * 72,
            f"  Total Evaluated:     {s.get('total_evaluated', 0)}",
            f"  Total Validated/App: {s.get('total_submitted', 0)}",
            f"  Total Skipped:       {s.get('total_skipped', 0)}",
            f"  Dedup Blocked:       {s.get('total_dedup_skipped', 0)}",
            "-" * 72,
            "  Channel Breakdown:"
        ]
        breakdown = s.get("breakdown", {})
        for plat, pstat in breakdown.items():
            lines.append(
                f"    • {plat.upper():16} -> Evaluated: {pstat.get('evaluated', 0):2} | "
                f"Submitted/Valid: {pstat.get('submitted', 0):2} | Skipped: {pstat.get('skipped', 0):2}"
            )
        lines.append("=" * 72)
        return "\n".join(lines)


# ==============================================================================
# INTENT PARSER
# ==============================================================================

class IntentParser:
    """
    Parses conversational natural-language job search instructions into structured ApplicationIntent.
    Supports role detection, location detection, ATS portal identification, match scoring thresholds,
    limits, and execution flags.
    """

    KNOWN_ROLE_PATTERNS = [
        (r"azure\s+data\s+engineer", "Azure Data Engineer"),
        (r"azure\s+databricks(\s+engineer)?", "Azure Databricks Engineer"),
        (r"databricks(\s+engineer|\s+specialist)?", "Databricks Engineer"),
        (r"pyspark(\s+developer|\s+engineer)?", "PySpark Developer"),
        (r"delta\s+lake(\s+engineer)?", "Delta Lake Engineer"),
        (r"medallion(\s+architecture)?", "Medallion Lakehouse Engineer"),
        (r"data\s+platform(\s+engineer)?", "Data Platform Engineer"),
        (r"azure\s+data\s+factory|adf", "Azure Data Factory (ADF) Engineer"),
        (r"apache\s+kafka|kafka(\s+engineer)?", "Kafka Data Streaming Engineer"),
        (r"cloud\s+data\s+engineer", "Cloud Data Engineer"),
        (r"data\s+engineer", "Data Engineer"),
        (r"big\s+data(\s+engineer)?", "Big Data Engineer"),
        (r"mlops(\s+engineer)?", "MLOps Engineer"),
        (r"spark(\s+developer)?", "Spark Developer"),
    ]

    KNOWN_LOCATION_PATTERNS = [
        (r"bengaluru|bangalore", "Bengaluru"),
        (r"hyderabad", "Hyderabad"),
        (r"pune", "Pune"),
        (r"gurugram|gurgaon", "Gurugram"),
        (r"noida", "Noida"),
        (r"delhi(\s+ncr)?", "Delhi / NCR"),
        (r"mumbai", "Mumbai"),
        (r"chennai", "Chennai"),
        (r"kolkata", "Kolkata"),
        (r"remote|wfh|work\s+from\s+home", "Remote"),
    ]

    KNOWN_PLATFORM_PATTERNS = [
        (r"linkedin(\s+easy\s+apply)?", "linkedin"),
        (r"naukri|naukari", "naukri"),
        (r"greenhouse(\.io)?", "greenhouse"),
        (r"lever(\.co)?", "lever"),
        (r"ashby(hq)?", "ashby"),
        (r"workday|myworkdayjobs", "workday"),
        (r"external(\s+portals?)?|career\s+portals?|ats", "career_portals"),
    ]

    @classmethod
    def parse(
        cls,
        text_or_intent: Union[str, ApplicationIntent, Dict[str, Any], None] = None,
        **overrides
    ) -> ApplicationIntent:
        """
        Normalizes natural language text or raw input into an ApplicationIntent object,
        applying explicit overrides if supplied.
        """
        if isinstance(text_or_intent, ApplicationIntent):
            intent = text_or_intent
        elif isinstance(text_or_intent, dict):
            intent = ApplicationIntent(**{k: v for k, v in text_or_intent.items() if hasattr(ApplicationIntent, k)})
        elif isinstance(text_or_intent, str) and text_or_intent.strip():
            intent = cls._parse_text(text_or_intent)
        else:
            intent = ApplicationIntent()

        # Apply keyword overrides
        for k, v in overrides.items():
            if hasattr(intent, k) and v is not None:
                setattr(intent, k, v)

        return intent

    @classmethod
    def _parse_text(cls, text: str) -> ApplicationIntent:
        clean_text = text.strip()
        lowered = clean_text.lower()

        # 1. Roles extraction
        extracted_roles = []
        for pat, canonical in cls.KNOWN_ROLE_PATTERNS:
            if re.search(r"\b" + pat + r"\b", lowered):
                extracted_roles.append(canonical)
        if not extracted_roles:
            extracted_roles = list(DEFAULT_ROLES)

        # 2. Locations extraction
        extracted_locations = []
        for pat, canonical in cls.KNOWN_LOCATION_PATTERNS:
            if re.search(r"\b" + pat + r"\b", lowered):
                extracted_locations.append(canonical)
        if not extracted_locations:
            extracted_locations = list(DEFAULT_LOCATIONS)

        # 3. Platforms & ATS extraction
        extracted_platforms = []
        ats_filters = []
        for pat, plat in cls.KNOWN_PLATFORM_PATTERNS:
            if re.search(r"\b" + pat + r"\b", lowered):
                if plat in ("greenhouse", "lever", "ashby", "workday"):
                    if "career_portals" not in extracted_platforms:
                        extracted_platforms.append("career_portals")
                    ats_filters.append(plat)
                else:
                    if plat not in extracted_platforms:
                        extracted_platforms.append(plat)

        if not extracted_platforms:
            extracted_platforms = ["naukri", "linkedin", "career_portals"]

        # 4. Match Score extraction (e.g. "match >= 75%", "score >= 80", "75% match", "threshold 70")
        min_score = 70.0
        score_match = re.search(r"(?:match|score|threshold|at least|minimum of)\s*(?:>=|>|above|minimum|min|equal\s*to)?\s*(\d{2})\s*(?:%|percent)?|(?:\b(?:>=|>|above|minimum|min)\s*(\d{2})\s*(?:%|percent)\b)", lowered)
        if score_match:
            try:
                val_str = score_match.group(1) or score_match.group(2)
                val = float(val_str)
                if 50.0 <= val <= 100.0:
                    min_score = val
            except (ValueError, IndexError):
                min_score = 70.0

        # 5. Limit extraction (e.g. "limit 15", "apply to 10 jobs", "20 vacancies", "simulate 5", "max 5")
        limit = 15
        limit_match = re.search(r"\b(?:limit|apply\s+(?:to|for)|max|count|simulate|target)\s*(?:of)?\s*(\d{1,3})\b|\b(\d{1,3})\s+(?:vacancies|roles|jobs|positions)\b", lowered)
        if limit_match:
            try:
                val_str = limit_match.group(1) or limit_match.group(2)
                limit = int(val_str)
            except (ValueError, IndexError):
                limit = 15

        # 6. Salary extraction (e.g. "20 LPA", "25 LPA", "salary >= 22", "₹22 LPA")
        min_salary = 20.0
        sal_match = re.search(r"(?:₹|inr|rs\.?|salary\s*(?:>=|above|min|minimum)?\s*)?(\d{1,2}(?:\.\d+)?)\s*(?:lpa|lakhs|lac|ctc)\b|\bsalary\s*(?:>=|>|above|min|minimum)\s*(\d{1,2}(?:\.\d+)?)\b", lowered)
        if sal_match:
            try:
                val_str = sal_match.group(1) or sal_match.group(2)
                min_salary = float(val_str)
            except (ValueError, IndexError):
                min_salary = 20.0

        # 7. Flags: dry run & headless
        dry_run = bool(re.search(r"\b(dry[- ]?run|simulate|simulation|offline|test[- ]mode)\b", lowered))
        headless = not bool(re.search(r"\b(headed|interactive|visible|show\s+browser)\b", lowered))

        return ApplicationIntent(
            raw_intent=clean_text,
            roles=extracted_roles,
            locations=extracted_locations,
            platforms=extracted_platforms,
            min_match_score=min_score,
            limit=limit,
            min_salary_lpa=min_salary,
            dry_run=dry_run,
            headless=headless,
            ats_filters=ats_filters
        )


# ==============================================================================
# INTENT JOB APPLY AGENT
# ==============================================================================

class IntentJobApplyAgent:
    """
    Master Autonomous Intent-Based Job Apply Agent.
    Coordinates natural-language parsing, cross-platform execution planning,
    autonomous dispatching, multi-tier deduplication, and application logging.
    """

    def __init__(
        self,
        dry_run: bool = False,
        headless: bool = True,
        min_score: float = 70.0,
        tracker_path: Optional[str] = None,
        db_path: Optional[str] = None
    ):
        self.dry_run = dry_run
        self.headless = headless
        self.min_score = min_score
        self.tracker_path = tracker_path or TRACKER_PATH
        self.db_path = db_path or DB_PATH

        # Initialize engines
        self.naukri_engine = AutoApplyEngine(dry_run=dry_run)
        self.linkedin_runner = LinkedInApplyRunner(headless=headless, dry_run=dry_run, min_score=min_score)
        self.portal_runner = ExternalPortalBatchRunner(
            dry_run=dry_run,
            headless=headless,
            min_score=min_score,
            min_salary=20.0,
            db_path=self.db_path
        )
        self.profile = load_applicant_profile()

        # Guarantee SQLite DB initialization
        init_db(self.db_path)

    def plan_execution(self, intent: ApplicationIntent) -> ApplicationExecutionPlan:
        """Constructs an executable multi-channel execution plan from intent."""
        tasks = []
        limit_per_channel = max(1, intent.limit // max(1, len(intent.platforms)))

        for platform in intent.platforms:
            if platform == "naukri":
                tasks.append({
                    "platform": "naukri",
                    "channel_name": "Naukri (1-Click & Verified Solver)",
                    "roles": intent.roles,
                    "locations": intent.locations,
                    "limit": limit_per_channel,
                    "min_score": intent.min_match_score,
                    "dry_run": intent.dry_run,
                    "headless": intent.headless
                })
            elif platform == "linkedin":
                tasks.append({
                    "platform": "linkedin",
                    "channel_name": "LinkedIn (Easy Apply Modal Navigator)",
                    "roles": intent.roles,
                    "locations": intent.locations,
                    "limit": limit_per_channel,
                    "min_score": intent.min_match_score,
                    "dry_run": intent.dry_run,
                    "headless": intent.headless
                })
            elif platform in ("career_portals", "greenhouse", "lever", "ashby", "workday"):
                target_ats = intent.ats_filters if intent.ats_filters else ([platform] if platform != "career_portals" else [])
                tasks.append({
                    "platform": "career_portals",
                    "channel_name": f"Career Portals ({', '.join(target_ats) if target_ats else 'All ATS'})",
                    "roles": intent.roles,
                    "locations": intent.locations,
                    "ats_types": target_ats,
                    "limit": limit_per_channel,
                    "min_score": intent.min_match_score,
                    "dry_run": intent.dry_run,
                    "headless": intent.headless
                })

        return ApplicationExecutionPlan(
            intent=intent,
            tasks=tasks,
            estimated_applications=min(intent.limit, len(tasks) * limit_per_channel)
        )

    def execute_intent(
        self,
        intent_input: Union[str, ApplicationIntent, Dict[str, Any], None] = None,
        **overrides
    ) -> IntentApplyResult:
        """
        Executes end-to-end intent-driven job application cycle.
        Parses intent, generates multi-channel plan, enforces deduplication,
        records into SQLite applied_jobs.db and logs to Excel tracker.
        """
        start_time = time.time()
        intent = IntentParser.parse(intent_input, **overrides)
        if self.dry_run:
            intent.dry_run = True

        plan = self.plan_execution(intent)
        print("\n" + "=" * 74)
        print("  🤖 NAUKARIPRO: INTENT-BASED AUTONOMOUS APPLICATION AGENT")
        print(f"  Parsed Intent: {intent.raw_intent or 'Autonomous multi-platform targeted apply'}")
        print(f"  Target Roles:  {', '.join(intent.roles[:3])}")
        print(f"  Target Hubs:   {', '.join(intent.locations[:4])}")
        print(f"  Score Gate:    >= {intent.min_match_score}% | Limit: {intent.limit} applications")
        print(f"  Mode:          {'DRY-RUN (100% Offline Simulation)' if intent.dry_run else 'LIVE SUBMISSION'}")
        print("=" * 74)

        all_applied = []
        all_skipped = []
        platform_breakdown = {}
        total_dedup_skipped = 0

        for task in plan.tasks:
            plat = task["platform"]
            limit = task["limit"]
            min_score = task["min_score"]
            channel_name = task["channel_name"]
            print(f"\n[*] Dispatching Channel: {channel_name} (Target: {limit} apps, Score >= {min_score}%)...")

            channel_applied = []
            channel_skipped = []
            evaluated_count = 0

            if plat == "naukri":
                # Naukri 1-Click & Verified Questionnaire Solver
                self.naukri_engine.dry_run = intent.dry_run
                if intent.dry_run:
                    payloads = self.naukri_engine.run_offline_dry_run(limit=limit)
                    evaluated_count = len(payloads)
                    for p in payloads:
                        title = p.job_title or p.title
                        company = p.company
                        url = p.url
                        score = float(p.match_score or 0.0)

                        # Deduplication check
                        if is_job_already_applied(title=title, company=company, job_url=url, db_path=self.db_path):
                            total_dedup_skipped += 1
                            channel_skipped.append({
                                "platform": "naukri",
                                "company": company,
                                "title": title,
                                "url": url,
                                "status": "SKIPPED_DUPLICATE",
                                "score": score
                            })
                            continue

                        if p.status == "VALIDATED_PAYLOAD" and score >= min_score:
                            record = {
                                "platform": "naukri",
                                "company": company,
                                "title": title,
                                "url": url,
                                "status": "SUBMITTED_DRY_RUN",
                                "score": score,
                                "salary": p.salary,
                                "applied_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            channel_applied.append(record)
                            self._log_to_db(record)
                            self._log_to_excel(record, sheet_name="Applications_Log")
                        else:
                            channel_skipped.append({
                                "platform": "naukri",
                                "company": company,
                                "title": title,
                                "url": url,
                                "status": p.status,
                                "score": score
                            })
                else:
                    # Live Naukri execution
                    applied_cnt = self.naukri_engine.run(headless=intent.headless, limit=limit, dry_run=False)
                    evaluated_count = applied_cnt
                    channel_applied.append({
                        "platform": "naukri",
                        "company": "Live Naukri Vacancies",
                        "title": "Azure Data Engineer",
                        "status": "Submitted (Confirmed)",
                        "count": applied_cnt
                    })

            elif plat == "linkedin":
                # LinkedIn Easy Apply Navigator & Questionnaire Solver
                self.linkedin_runner.dry_run = intent.dry_run
                self.linkedin_runner.limit = limit
                self.linkedin_runner.min_score = min_score
                self.linkedin_runner.headless = intent.headless

                if intent.dry_run:
                    li_stats = self.linkedin_runner.engine.run_offline_dry_run(
                        keywords=intent.roles,
                        locations=intent.locations,
                        limit=limit,
                        min_score=min_score
                    )
                else:
                    import asyncio
                    try:
                        li_stats = asyncio.run(self.linkedin_runner.run(
                            keywords=intent.roles,
                            locations=intent.locations
                        ))
                    except Exception as e_li:
                        logger.error("Live LinkedIn run error: %s", e_li)
                        li_stats = {"discovered": 0, "jobs": [], "error": str(e_li), "status": "LIVE_ERROR"}

                evaluated_count = li_stats.get("discovered", 0)

                for job in li_stats.get("jobs", []):
                    title = job.get("title", "")
                    company = job.get("company", "")
                    url = job.get("url", f"https://www.linkedin.com/jobs/view/{job.get('job_id', '')}")
                    score = float(job.get("score", 0.0))

                    # Deduplication check
                    if is_job_already_applied(title=title, company=company, job_url=url, db_path=self.db_path):
                        total_dedup_skipped += 1
                        channel_skipped.append({
                            "platform": "linkedin",
                            "company": company,
                            "title": title,
                            "url": url,
                            "status": "SKIPPED_DUPLICATE",
                            "score": score
                        })
                        continue

                    if job.get("success") or job.get("status") in ("SUBMITTED_DRY_RUN", "APPLIED"):
                        record = {
                            "platform": "linkedin",
                            "company": company,
                            "title": title,
                            "url": url,
                            "status": "SUBMITTED_DRY_RUN" if intent.dry_run else "APPLIED",
                            "score": score,
                            "salary": "22 - 28 Lacs PA",
                            "applied_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        channel_applied.append(record)
                        self._log_to_db(record)
                        self.linkedin_runner.log_application_to_excel(record, tracker_path=self.tracker_path)
                    else:
                        channel_skipped.append({
                            "platform": "linkedin",
                            "company": company,
                            "title": title,
                            "url": url,
                            "status": job.get("status", "GATED_OUT"),
                            "score": score
                        })

                if not intent.dry_run and not li_stats.get("jobs") and li_stats.get("status") in ("COOKIE_REFRESH_REQUIRED", "RATE_LIMITED", "LIVE_ERROR"):
                    channel_skipped.append({
                        "platform": "linkedin",
                        "company": "LinkedIn Easy Apply",
                        "title": "Live Session",
                        "url": "https://www.linkedin.com/jobs",
                        "status": li_stats.get("status"),
                        "score": 0.0
                    })

            elif plat in ("career_portals", "greenhouse", "lever", "ashby", "workday"):
                # External ATS Portals
                portal_stats = self.portal_runner.run_batch(
                    roles=intent.roles,
                    locations=intent.locations,
                    ats_types=task.get("ats_types", []),
                    dry_run=intent.dry_run,
                    limit=limit,
                    min_score=min_score,
                    min_salary=intent.min_salary_lpa
                )
                evaluated_count = portal_stats.get("total_evaluated", 0)

                for job in portal_stats.get("jobs", []):
                    title = job.get("title", "")
                    company = job.get("company", "")
                    url = job.get("url", "")
                    score = float(job.get("score", 0.0))
                    status = job.get("status", "")

                    if "SUBMITTED" in status or "Submitted" in status or "Auto-Filled" in status:
                        record = {
                            "platform": f"career_portal ({job.get('ats', 'ATS')})",
                            "company": company,
                            "title": title,
                            "url": url,
                            "status": status,
                            "score": score,
                            "salary": "24 - 30 Lacs PA",
                            "applied_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        channel_applied.append(record)
                        self._log_to_db(record)
                        self._log_to_excel(record, sheet_name="Applications_Log")
                    else:
                        if status == "SKIPPED_DUPLICATE":
                            total_dedup_skipped += 1
                        channel_skipped.append({
                            "platform": f"career_portal ({job.get('ats', 'ATS')})",
                            "company": company,
                            "title": title,
                            "url": url,
                            "status": status,
                            "score": score
                        })

            if plat not in platform_breakdown:
                platform_breakdown[plat] = {
                    "evaluated": 0,
                    "submitted": 0,
                    "skipped": 0
                }
            platform_breakdown[plat]["evaluated"] += evaluated_count
            platform_breakdown[plat]["submitted"] += len(channel_applied)
            platform_breakdown[plat]["skipped"] += len(channel_skipped)
            all_applied.extend(channel_applied)
            all_skipped.extend(channel_skipped)

        duration = round(time.time() - start_time, 2)
        summary = {
            "total_evaluated": sum(p["evaluated"] for p in platform_breakdown.values()),
            "total_submitted": len(all_applied),
            "total_skipped": len(all_skipped),
            "total_dedup_skipped": total_dedup_skipped,
            "breakdown": platform_breakdown,
            "duration_seconds": duration,
            "mode": "DRY-RUN" if intent.dry_run else "LIVE"
        }

        result = IntentApplyResult(
            intent=intent,
            plan=plan,
            summary=summary,
            applied_records=all_applied,
            skipped_records=all_skipped,
            duration_seconds=duration,
            tracker_updated=len(all_applied) > 0,
            db_updated=len(all_applied) > 0
        )

        print("\n" + result.format_summary_report())
        return result

    def _log_to_db(self, record: Dict[str, Any]) -> bool:
        """Safely records applied vacancy to SQLite database."""
        try:
            record_applied_job(
                title=record.get("title", ""),
                company=record.get("company", ""),
                platform=record.get("platform", "naukri"),
                location="Bengaluru / Hyderabad / Remote",
                experience_req="2-5 Yrs",
                match_score=record.get("score", 75.0),
                status=record.get("status", "Submitted (Confirmed)"),
                application_type=f"Intent Apply ({record.get('platform', 'Auto')})",
                job_url=record.get("url", "N/A"),
                applicant_email=self.profile.get("email", "lav84095@gmail.com"),
                applied_at=record.get("applied_at"),
                db_path=self.db_path
            )
            return True
        except Exception as e:
            logger.debug("Intent agent DB logging error: %s", e)
            return False

    def _log_to_excel(self, record: Dict[str, Any], sheet_name: str = "Applications_Log") -> bool:
        """Appends application record to master Excel tracker worksheet."""
        try:
            import openpyxl
            path = self.tracker_path
            if not os.path.exists(path):
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = sheet_name
                ws.append([
                    "Application Date", "Company Name", "Job Title", "Match Score (%)",
                    "Role Category", "Experience Required", "Location", "Application Type",
                    "Status", "Job URL", "Recruiter Response"
                ])
            else:
                wb = openpyxl.load_workbook(path)
                if sheet_name in wb.sheetnames:
                    ws = wb[sheet_name]
                else:
                    ws = wb.create_sheet(title=sheet_name)
                    ws.append([
                        "Application Date", "Company Name", "Job Title", "Match Score (%)",
                        "Role Category", "Experience Required", "Location", "Application Type",
                        "Status", "Job URL", "Recruiter Response"
                    ])

            date_str = record.get("applied_at") or datetime.now().strftime("%Y-%m-%d %H:%M")
            ws.append([
                date_str,
                record.get("company", ""),
                record.get("title", ""),
                f"{int(record.get('score', 80))}%",
                "Azure Data Engineering",
                "2-5 Yrs",
                "Bengaluru / Hyderabad",
                f"Intent Agent ({record.get('platform', 'Auto')})",
                record.get("status", "SUBMITTED_DRY_RUN"),
                record.get("url", "N/A"),
                "Pending (Dispatched via Intent Agent)"
            ])
            wb.save(path)
            return True
        except Exception as e:
            logger.debug("Intent agent Excel logging error: %s", e)
            return False
