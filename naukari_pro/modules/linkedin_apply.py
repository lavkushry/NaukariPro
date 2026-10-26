"""
naukariPro Feature: LinkedIn Autonomous Easy Apply Engine
Milestone 3: End-to-End Multi-Step Easy Apply Bot with Precision Screening Solver

Provides:
- Intelligent Screening Questionnaire Solver (regex fuzzy matching for tech stack, notice period, CTC, visa, relocation)
- Multi-Step Modal Form Navigator (auto-fill contact, attach ATS resume, answer questions, uncheck 'Follow company')
- Precision Submission Verifier & Error Recovery (DOM verification of successful application dispatch)
- Unified LinkedIn Application Tracker (Excel 'LinkedIn_Applications_Log' worksheet + JSON audit log)
- Complete Apply Engine coordinating discovery, scoring gate (>= 70.0%), deduplication, and execution throttling (25-30 apps/cycle)
"""

import os
import sys
import re
import csv
import time
import json
import random
import inspect
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union, Tuple, Set

import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.utils import get_column_letter

from naukari_pro.config import WORKSPACE_DIR, TRACKER_PATH, RESUME_PDF_PATH, load_config
from naukari_pro.modules.linkedin_session import (
    LinkedInSessionManager,
    LinkedInError,
    LinkedInSessionError
)
from naukari_pro.modules.linkedin_search import (
    LinkedInSearchEngine,
    JobMatchScorer,
    JobDeduplicator,
    TECH_HUBS,
    DEFAULT_KEYWORDS
)

logger = logging.getLogger("naukariPro.LinkedInApply")

# Styling constants for LinkedIn branding
LINKEDIN_BLUE_FILL = PatternFill(start_color="0A66C2", end_color="0A66C2", fill_type="solid")
WHITE_BOLD_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
HEADER_ALIGNMENT = Alignment(horizontal="center", vertical="center", wrap_text=True)

# ==============================================================================
# EXCEPTIONS HIERARCHY
# ==============================================================================

class LinkedInApplyError(LinkedInError):
    """Base exception for Easy Apply execution errors."""
    pass


class LinkedInModalNotFoundError(LinkedInApplyError):
    """Raised when Easy Apply modal fails to open after clicking button."""
    pass


class LinkedInSubmissionFailedError(LinkedInApplyError):
    """Raised when application submission verification fails on DOM."""
    pass


# ==============================================================================
# RE-EXPORTS FROM LINKEDIN_BOT (FEATURES 9-15)
# ==============================================================================

from naukari_pro.modules.linkedin_bot import (
    ModalState,
    EasyApplySelectors,
    ResumeSelectionResult,
    LinkedInResumeManager,
    LinkedInCircuitBreaker,
    LinkedInCircuitBreakerError,
    LinkedInScreeningSolver,
    LinkedInEasyApplyBot,
    LinkedInEasyApplyNavigator,
    get_candidate_profile,
    safe_count,
    safe_inner_text,
    safe_is_visible,
    safe_is_checked,
    humanized_delay,
)


# ==============================================================================
# 3. UNIFIED APPLICATION TRACKER (EXCEL & JSON)
# ==============================================================================

class LinkedInApplicationTracker:
    """
    Enterprise-grade application tracker for LinkedIn Easy Apply.
    - Primary: 'LinkedIn_Applications_Log' in Naukri_Live_Application_Tracker.xlsx (10 canonical columns, styled #0A66C2)
    - Fallback 1: 'Applications_Log' worksheet in the same workbook
    - Fallback 2: 'linkedin_applications_fallback.csv' emergency file
    - Audit: 'linkedin_applications_log.json' & 'skip_list_linkedin.json'
    """

    CANONICAL_HEADERS = [
        "Job ID",
        "Platform",
        "Company",
        "Job Title",
        "Location",
        "Match Score",
        "Status",
        "Steps Completed",
        "Applied Timestamp",
        "Job URL"
    ]

    # Kept for backward compatibility
    EXCEL_HEADERS = CANONICAL_HEADERS
    LEGACY_HEADERS = [
        "Application Date",
        "Company Name",
        "Job Title",
        "Match Score (%)",
        "Role Category",
        "Location",
        "Application Type",
        "Status",
        "Job URL",
        "Easy Apply Steps",
        "Recruiter Response"
    ]

    # Column widths for canonical 10 columns
    COLUMN_WIDTHS = {
        "A": 16,  # Job ID
        "B": 20,  # Platform
        "C": 25,  # Company
        "D": 28,  # Job Title
        "E": 25,  # Location
        "F": 14,  # Match Score
        "G": 18,  # Status
        "H": 16,  # Steps Completed
        "I": 20,  # Applied Timestamp
        "J": 45   # Job URL
    }

    def __init__(
        self,
        excel_path: Optional[str] = None,
        json_log_path: Optional[str] = None,
        skip_file_path: Optional[str] = None,
        fallback_csv_path: Optional[str] = None
    ):
        target_ws = os.getenv("WORKSPACE_DIR") or WORKSPACE_DIR
        self.excel_path = excel_path or TRACKER_PATH
        self.json_log_path = json_log_path or os.path.join(target_ws, "linkedin_applications_log.json")
        self.skip_file_path = skip_file_path or os.path.join(target_ws, "skip_list_linkedin.json")
        csv_dir = os.path.dirname(self.excel_path) if self.excel_path else target_ws
        self.fallback_csv_path = fallback_csv_path or os.path.join(csv_dir, "linkedin_applications_fallback.csv")
        self._ensure_excel_sheet()

    def _apply_header_styling(self, ws):
        """Applies LinkedIn Blue #0A66C2 styling, bold white font, freeze panes, and column widths."""
        try:
            ws.row_dimensions[1].height = 26
            for col_idx in range(1, len(self.CANONICAL_HEADERS) + 1):
                cell = ws.cell(1, col_idx)
                cell.fill = LINKEDIN_BLUE_FILL
                cell.font = WHITE_BOLD_FONT
                cell.alignment = HEADER_ALIGNMENT
            for col_letter, width in self.COLUMN_WIDTHS.items():
                ws.column_dimensions[col_letter].width = width
            ws.freeze_panes = "A2"
        except Exception as e:
            logger.debug("Notice applying header styling: %s", e)

    def _ensure_excel_sheet(self):
        """Ensures the 'LinkedIn_Applications_Log' worksheet exists with canonical headers & styling."""
        try:
            if not os.path.exists(self.excel_path):
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "LinkedIn_Applications_Log"
                ws.append(self.CANONICAL_HEADERS)
                self._apply_header_styling(ws)
                wb.save(self.excel_path)
            else:
                wb = openpyxl.load_workbook(self.excel_path)
                if "LinkedIn_Applications_Log" not in wb.sheetnames:
                    ws = wb.create_sheet(title="LinkedIn_Applications_Log")
                    ws.append(self.CANONICAL_HEADERS)
                    self._apply_header_styling(ws)
                    wb.save(self.excel_path)
                else:
                    ws = wb["LinkedIn_Applications_Log"]
                    if ws.max_row == 0 or (ws.max_row == 1 and not ws.cell(1, 1).value):
                        ws.append(self.CANONICAL_HEADERS)
                        self._apply_header_styling(ws)
                        wb.save(self.excel_path)
                    elif ws.max_row >= 1 and ws.cell(1, 1).value != "Job ID":
                        # Seamlessly upgrade legacy headers and rows to canonical 10 columns
                        old_rows = list(ws.iter_rows(values_only=True))
                        ws.delete_rows(1, ws.max_row)
                        ws.append(self.CANONICAL_HEADERS)
                        self._apply_header_styling(ws)
                        for r in old_rows[1:]:
                            if not r or not any(r):
                                continue
                            r_ts = r[0] if len(r) > 0 else ""
                            r_comp = r[1] if len(r) > 1 else ""
                            r_title = r[2] if len(r) > 2 else ""
                            r_score = r[3] if len(r) > 3 else "85%"
                            r_loc = r[5] if len(r) > 5 else "India"
                            r_status = r[7] if len(r) > 7 else "APPLIED"
                            r_url = r[8] if len(r) > 8 else "N/A"
                            r_steps = r[9] if len(r) > 9 else 1
                            m = re.search(r"/jobs/view/(\d+)", str(r_url))
                            r_jid = m.group(1) if m else ""
                            ws.append([
                                r_jid,
                                "LinkedIn Easy Apply",
                                r_comp,
                                r_title,
                                r_loc,
                                r_score,
                                r_status,
                                r_steps,
                                r_ts,
                                r_url
                            ])
                        wb.save(self.excel_path)
                    elif ws.max_row >= 1 and ws.cell(1, 1).value == "Job ID":
                        # Ensure styling on existing canonical sheet if unstyled
                        c1 = ws.cell(1, 1)
                        if not c1.fill or not c1.fill.fill_type:
                            self._apply_header_styling(ws)
                            wb.save(self.excel_path)
        except Exception as e:
            logger.warning("Notice ensuring Excel sheet: %s", e)

    def log_application(
        self,
        job_data: Dict[str, Any],
        status: str,
        match_score: Optional[float] = None,
        steps: int = 1,
        dry_run: bool = False
    ) -> bool:
        """
        Logs application event to Excel (with multi-tier fallback to Applications_Log and CSV),
        JSON audit log, and skip list.
        CRITICAL: Never mutates skip_list_linkedin.json during dry_run.
        """
        company = job_data.get("company", "Unknown Employer")
        title = job_data.get("title", "Azure Data Engineer")
        location = job_data.get("location", "India")
        url = job_data.get("url", "N/A")
        job_id = str(job_data.get("job_id", ""))
        score_val = f"{int(match_score)}%" if match_score is not None else "85%"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        excel_logged = False

        # Tier 1: Primary 'LinkedIn_Applications_Log' in Excel
        try:
            if not os.path.exists(self.excel_path):
                self._ensure_excel_sheet()

            wb = openpyxl.load_workbook(self.excel_path)
            if "LinkedIn_Applications_Log" in wb.sheetnames:
                ws = wb["LinkedIn_Applications_Log"]
                first_header = ws.cell(1, 1).value if ws.max_row >= 1 else None
                if first_header == "Job ID" or ws.max_column == 10:
                    ws.append([
                        job_id,
                        "LinkedIn Easy Apply",
                        company,
                        title,
                        location,
                        score_val,
                        status,
                        steps,
                        timestamp,
                        url
                    ])
                else:
                    # Legacy 11-column compatibility
                    ws.append([
                        timestamp,
                        company,
                        title,
                        score_val,
                        "Azure Data Engineer",
                        location,
                        "LinkedIn Easy Apply",
                        status,
                        url,
                        str(steps),
                        "Pending Initial Review"
                    ])
                wb.save(self.excel_path)
                excel_logged = True
            else:
                raise KeyError("LinkedIn_Applications_Log sheet not found in workbook")
        except Exception as e1:
            logger.warning("Failed appending to LinkedIn_Applications_Log: %s. Attempting Tier 2 fallback.", e1)

            # Tier 2: Fallback to 'Applications_Log' in same workbook
            try:
                if os.path.exists(self.excel_path):
                    wb = openpyxl.load_workbook(self.excel_path)
                    ws = wb["Applications_Log"] if "Applications_Log" in wb.sheetnames else wb.active
                    ws.append([
                        timestamp,
                        company,
                        title,
                        score_val,
                        "Azure Data Engineer",
                        "2-5 Yrs",
                        location,
                        "LinkedIn Easy Apply",
                        status,
                        url,
                        "Awaiting Recruiter Review"
                    ])
                    wb.save(self.excel_path)
                    excel_logged = True
                    logger.info("Successfully logged application to fallback sheet '%s'", ws.title)
            except Exception as e2:
                logger.warning("Failed appending to fallback Applications_Log: %s. Attempting Tier 3 CSV fallback.", e2)

        # Tier 3: Emergency CSV Fallback (guarantees zero data loss if Excel fails entirely)
        if not excel_logged:
            try:
                csv_exists = os.path.exists(self.fallback_csv_path)
                with open(self.fallback_csv_path, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    if not csv_exists or os.path.getsize(self.fallback_csv_path) == 0:
                        writer.writerow(self.CANONICAL_HEADERS)
                    writer.writerow([
                        job_id,
                        "LinkedIn Easy Apply",
                        company,
                        title,
                        location,
                        score_val,
                        status,
                        steps,
                        timestamp,
                        url
                    ])
                logger.info("Application emergency logged to fallback CSV: %s", self.fallback_csv_path)
            except Exception as e3:
                logger.error("Failed writing to emergency fallback CSV: %s", e3)

        # Tier 4: JSON Audit Log
        record = {
            "timestamp": timestamp,
            "job_id": job_id,
            "company": company,
            "title": title,
            "location": location,
            "url": url,
            "status": status,
            "match_score": score_val,
            "steps": steps,
            "dry_run": dry_run
        }
        try:
            existing_log = []
            if os.path.exists(self.json_log_path):
                with open(self.json_log_path, "r", encoding="utf-8") as f:
                    existing_log = json.load(f)
            existing_log.append(record)
            with open(self.json_log_path, "w", encoding="utf-8") as f:
                json.dump(existing_log, f, indent=2)
        except Exception as e:
            logger.debug("Notice saving JSON application log: %s", e)

        # Tier 5: Update Skip List (ONLY on authentic live submissions; NEVER on dry-run!)
        if not dry_run and job_id and status in ["APPLIED", "SUBMITTED"]:
            try:
                skip_set = set()
                if os.path.exists(self.skip_file_path):
                    with open(self.skip_file_path, "r", encoding="utf-8") as f:
                        skip_set = set(json.load(f))
                skip_set.add(job_id)
                with open(self.skip_file_path, "w", encoding="utf-8") as f:
                    json.dump(sorted(list(skip_set)), f, indent=2)
            except Exception as e:
                logger.debug("Notice updating skip list: %s", e)

        return True

    def get_applied_job_ids(self) -> Set[str]:
        """
        Extracts all applied Job IDs across all storage layers:
        - Skip List: 'skip_list_linkedin.json'
        - JSON Log: 'linkedin_applications_log.json'
        - Emergency CSV: 'linkedin_applications_fallback.csv'
        - Excel: 'LinkedIn_Applications_Log' & 'Applications_Log'
        """
        applied_ids: Set[str] = set()

        # 1. From Skip List
        if os.path.exists(self.skip_file_path):
            try:
                with open(self.skip_file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        applied_ids.update(str(x).strip() for x in data if str(x).strip())
                    elif isinstance(data, dict):
                        applied_ids.update(str(x).strip() for x in data.get("applied_job_ids", []) if str(x).strip())
            except Exception as e:
                logger.debug("Notice reading skip file: %s", e)

        # 2. From JSON Log
        if os.path.exists(self.json_log_path):
            try:
                with open(self.json_log_path, "r", encoding="utf-8") as f:
                    entries = json.load(f)
                    for item in entries:
                        jid = str(item.get("job_id", "")).strip()
                        if jid and item.get("status") in ["APPLIED", "SUBMITTED"]:
                            applied_ids.add(jid)
            except Exception as e:
                logger.debug("Notice reading JSON log: %s", e)

        # 3. From Emergency CSV Fallback
        if os.path.exists(self.fallback_csv_path):
            try:
                with open(self.fallback_csv_path, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    headers = next(reader, None)
                    job_id_col = 0
                    if headers and "Job ID" in headers:
                        job_id_col = headers.index("Job ID")
                    for row in reader:
                        if len(row) > job_id_col and row[job_id_col].strip():
                            applied_ids.add(row[job_id_col].strip())
            except Exception as e:
                logger.debug("Notice reading CSV fallback: %s", e)

        # 4. From Excel Sheets
        if os.path.exists(self.excel_path):
            try:
                wb = openpyxl.load_workbook(self.excel_path, read_only=True)
                for sheetname in ["LinkedIn_Applications_Log", "Applications_Log"]:
                    if sheetname in wb.sheetnames:
                        ws = wb[sheetname]
                        for row in ws.iter_rows(values_only=True):
                            if not row:
                                continue
                            # Check status if available (avoid adding dry run simulations)
                            status_val = ""
                            if len(row) >= 7 and row[6] is not None:
                                status_val = str(row[6]).upper()
                            if "DRY_RUN" in status_val:
                                continue

                            # Check first cell for direct numeric job id
                            c0 = str(row[0]).strip() if row[0] is not None else ""
                            if c0.isdigit() and len(c0) >= 4:
                                applied_ids.add(c0)
                            # Also scan any cell containing linkedin job URL
                            for cell in row:
                                if cell and isinstance(cell, str) and "linkedin.com/jobs/view/" in cell:
                                    m = re.search(r"/jobs/view/(\d+)", cell)
                                    if m:
                                        applied_ids.add(m.group(1))
            except Exception as e:
                logger.debug("Notice reading Excel for applied IDs: %s", e)

        return applied_ids

    def is_applied(self, job_id: str) -> bool:
        """Checks if a job has already been applied across skip list, JSON log, CSV, or Excel."""
        if not job_id:
            return False
        clean_id = str(job_id).strip()
        # Fast path: check skip list file
        if os.path.exists(self.skip_file_path):
            try:
                with open(self.skip_file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if clean_id in data:
                        return True
            except Exception:
                pass
        return clean_id in self.get_applied_job_ids()


# ==============================================================================
# 4. MASTER LINKEDIN APPLY ENGINE
# ==============================================================================

class LinkedInApplyEngine:
    """
    Master coordinator orchestrating precision job search, match scoring gate (>= 70.0%),
    deduplication, and autonomous Easy Apply execution.
    """

    def __init__(
        self,
        session_manager: Optional[LinkedInSessionManager] = None,
        search_engine: Optional[LinkedInSearchEngine] = None,
        navigator: Optional[LinkedInEasyApplyNavigator] = None,
        tracker: Optional[LinkedInApplicationTracker] = None,
        circuit_breaker: Optional[LinkedInCircuitBreaker] = None,
        min_score: float = 70.0
    ):
        self.session_manager = session_manager or LinkedInSessionManager()
        self.search_engine = search_engine or LinkedInSearchEngine()
        self.circuit_breaker = circuit_breaker or LinkedInCircuitBreaker()
        self.navigator = navigator or LinkedInEasyApplyNavigator(circuit_breaker=self.circuit_breaker)
        self.tracker = tracker or LinkedInApplicationTracker()
        self.min_score = min_score
        self.scorer = JobMatchScorer()

    async def run_apply_cycle(
        self,
        keywords: Optional[List[str]] = None,
        locations: Optional[List[str]] = None,
        limit: int = 25,
        dry_run: bool = False,
        headless: bool = True
    ) -> Dict[str, Any]:
        """
        Executes a single autonomous apply cycle across target locations and keywords.
        Strictly enforces 25-30 applications limit, match score >= 70.0%, and process lock.
        """
        from playwright.async_api import async_playwright

        lock = self.session_manager.get_lock()
        if not lock.acquire(blocking=True):
            raise LinkedInSessionError("Could not acquire exclusive LinkedIn session lock. Another run is active.")

        stats = {
            "discovered": 0,
            "scored_above_threshold": 0,
            "applied": 0,
            "dry_run_verified": 0,
            "skipped": 0,
            "failed": 0,
            "jobs": []
        }

        try:
            target_keywords = keywords or DEFAULT_KEYWORDS[:3]
            target_locations = locations or ["Bengaluru", "Hyderabad", "Pune", "Gurugram", "Noida", "Remote"]

            async with async_playwright() as p:
                context = await self.session_manager.create_stealth_context(p, headless=headless)
                try:
                    page = context.pages[0] if (hasattr(context, "pages") and context.pages) else await context.new_page()

                    # 1. Verify session freshness
                    diag = await self.session_manager.verify_session(page, raise_for_status=False)
                    if diag.get("status") != "VALID":
                        logger.error("Session verification failed: %s", diag.get("status"))
                        stats["status"] = diag.get("status", "FAILED")
                        stats["detail"] = diag.get("detail", "")
                        return stats

                    logger.info("Session verified for '%s'. Beginning precision job discovery...", diag.get("candidate_name"))

                    # 2. Iterate through location & keyword matrix
                    for loc in target_locations:
                        if (stats["applied"] + stats["dry_run_verified"]) >= limit:
                            break
                        if self.circuit_breaker.is_tripped:
                            logger.critical("Circuit breaker tripped: %s. Halting apply cycle.", self.circuit_breaker.trip_reason)
                            break

                        for kw in target_keywords:
                            if (stats["applied"] + stats["dry_run_verified"]) >= limit:
                                break
                            if self.circuit_breaker.is_tripped:
                                logger.critical("Circuit breaker tripped: %s. Halting apply cycle.", self.circuit_breaker.trip_reason)
                                break

                            logger.info("Searching vacancies: keyword='%s', location='%s'", kw, loc)
                            search_res = await self.search_engine.search_jobs(
                                page=page,
                                keyword=kw,
                                location=loc,
                                max_pages=1,
                                easy_apply_only=True,
                                min_match_score=self.min_score
                            )

                            vacancies = search_res if isinstance(search_res, list) else search_res.get("jobs", [])
                            stats["discovered"] += len(vacancies)

                            for job in vacancies:
                                if (stats["applied"] + stats["dry_run_verified"]) >= limit:
                                    break
                                if self.circuit_breaker.is_tripped:
                                    logger.critical("Circuit breaker tripped: %s. Halting apply cycle.", self.circuit_breaker.trip_reason)
                                    break

                                job_id = str(job.get("job_id", ""))
                                if not job_id or self.tracker.is_applied(job_id):
                                    stats["skipped"] += 1
                                    continue

                                # 3. Match Scoring Gate (>= 70.0%)
                                score_res = self.scorer.evaluate(
                                    job_title=job.get("title", ""),
                                    job_description=job.get("raw_snippet", "")
                                )

                                if not score_res.passed or score_res.score < self.min_score:
                                    logger.info(
                                        "Job %s ('%s') gated out: score %.1f%% < %.1f%%",
                                        job_id, job.get("title"), score_res.score, self.min_score
                                    )
                                    stats["skipped"] += 1
                                    continue

                                stats["scored_above_threshold"] += 1
                                logger.info(
                                    "Target Vacancy Qualified: '%s' at '%s' (Score: %.1f%%). Navigating to Easy Apply...",
                                    job.get("title"), job.get("company"), score_res.score
                                )

                                # 4. Navigate directly to job view URL
                                try:
                                    res_g = page.goto(job.get("url", f"https://www.linkedin.com/jobs/view/{job_id}/"), wait_until="domcontentloaded")
                                    if inspect.isawaitable(res_g):
                                        await res_g
                                    await humanized_delay(1500, 2500, page=page)
                                except Exception as e:
                                    logger.warning("Error navigating to job %s: %s", job_id, e)
                                    stats["failed"] += 1
                                    self.circuit_breaker.record_failure(f"NAV_ERROR: {e}")
                                    continue

                                # 5. Execute Easy Apply Workflow
                                app_res = await self.navigator.execute_easy_apply(
                                    page=page,
                                    job_info=job,
                                    resume_path=RESUME_PDF_PATH,
                                    dry_run=dry_run
                                )

                                job_record = {
                                    "job_id": job_id,
                                    "title": job.get("title"),
                                    "company": job.get("company"),
                                    "score": score_res.score,
                                    "status": app_res.get("status"),
                                    "success": app_res.get("success", False)
                                }
                                stats["jobs"].append(job_record)

                                # Check if navigator already handled circuit breaker recording
                                navigator_manages_cb = (
                                    hasattr(self.navigator, "circuit_breaker")
                                    and self.navigator.circuit_breaker is self.circuit_breaker
                                )

                                if app_res.get("status") == "DRY_RUN_VERIFIED":
                                    stats["dry_run_verified"] += 1
                                    if not navigator_manages_cb:
                                        self.circuit_breaker.record_success()
                                    self.tracker.log_application(job, "DRY_RUN_VERIFIED", match_score=score_res.score, steps=app_res.get("steps", 1), dry_run=dry_run)
                                elif app_res.get("status") == "APPLIED":
                                    stats["applied"] += 1
                                    if not navigator_manages_cb:
                                        self.circuit_breaker.record_success()
                                    self.tracker.log_application(job, "APPLIED", match_score=score_res.score, steps=app_res.get("steps", 1), dry_run=dry_run)
                                else:
                                    stats["failed"] += 1
                                    if not navigator_manages_cb:
                                        self.circuit_breaker.record_failure(app_res.get("status", "FAILED"))

                                if self.circuit_breaker.is_tripped:
                                    logger.critical("Circuit breaker tripped: %s. Aborting vacancy processing.", self.circuit_breaker.trip_reason)
                                    stats["status"] = f"CIRCUIT_BREAKER_TRIPPED: {self.circuit_breaker.trip_reason}"
                                    break

                                # Randomized inter-application delay
                                await humanized_delay(2000, 4000, page=page)

                finally:
                    if hasattr(context, "close"):
                        c_res = context.close()
                        if inspect.isawaitable(c_res):
                            await c_res
        finally:
            lock.release()

        if "status" not in stats:
            if stats["applied"] > 0:
                stats["status"] = "SUCCESS"
            elif stats["dry_run_verified"] > 0:
                stats["status"] = "DRY_RUN_VERIFIED"
            elif stats["failed"] > 0:
                stats["status"] = "FAILED"
            elif stats["skipped"] > 0:
                stats["status"] = "SKIPPED_OR_ALREADY_APPLIED"
            else:
                stats["status"] = "IDLE"

        return stats

    def run_offline_dry_run(
        self,
        keywords: Optional[List[str]] = None,
        locations: Optional[List[str]] = None,
        limit: int = 25,
        min_score: float = 70.0,
        synthetic_vacancies: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        100% Offline Dry-Run Engine.
        Executes without Playwright, browser context, or live network calls.
        Evaluates synthetic Azure Data Engineer vacancies through JobMatchScorer (>=70%),
        simulates questionnaire solving via LinkedInScreeningSolver, and logs validated
        records to Excel with status 'SUBMITTED_DRY_RUN' without touching skip list.
        """
        solver = LinkedInScreeningSolver()
        target_keywords = keywords or DEFAULT_KEYWORDS[:3]
        target_locations = locations or ["Bengaluru", "Hyderabad", "Pune", "Gurugram", "Noida", "Remote"]

        if synthetic_vacancies is None:
            synthetic_vacancies = [
                {
                    "job_id": "4188001001",
                    "title": "Lead Azure Data Engineer",
                    "company": "Microsoft GCC",
                    "location": "Bengaluru",
                    "url": "https://www.linkedin.com/jobs/view/4188001001/",
                    "raw_snippet": "Required 2-4 years experience in Azure Databricks, PySpark, Delta Lake, Medallion Architecture, ADF, SQL. Notice period 15-30 days."
                },
                {
                    "job_id": "4188001002",
                    "title": "Azure Data Platform Engineer",
                    "company": "Walmart Global Tech",
                    "location": "Hyderabad",
                    "url": "https://www.linkedin.com/jobs/view/4188001002/",
                    "raw_snippet": "Looking for Data Engineer with 2-3 years hands-on experience in Azure Databricks, PySpark, Delta Lake, CI/CD, Terraform, and SQL."
                },
                {
                    "job_id": "4188001003",
                    "title": "Data Engineer - PySpark & Azure",
                    "company": "Amazon",
                    "location": "Bengaluru",
                    "url": "https://www.linkedin.com/jobs/view/4188001003/",
                    "raw_snippet": "Seeking 2-5 years experience with PySpark, Apache Spark, Delta Lake, Kafka streaming, and Azure infrastructure."
                },
                {
                    "job_id": "4188001004",
                    "title": "Senior Principal Data Architect",
                    "company": "Oracle Cloud",
                    "location": "Bengaluru",
                    "url": "https://www.linkedin.com/jobs/view/4188001004/",
                    "raw_snippet": "Required 12-15 years experience architecting enterprise lakehouses and leading large data engineering organizations."
                },
                {
                    "job_id": "4188001005",
                    "title": "Frontend React / UI Developer",
                    "company": "Swiggy",
                    "location": "Bengaluru",
                    "url": "https://www.linkedin.com/jobs/view/4188001005/",
                    "raw_snippet": "Design and build web user interfaces with React, Next.js, Redux, Tailwind CSS, TypeScript."
                }
            ]

        stats = {
            "discovered": len(synthetic_vacancies),
            "scored_above_threshold": 0,
            "applied": 0,
            "dry_run_verified": 0,
            "skipped": 0,
            "failed": 0,
            "jobs": []
        }

        for job in synthetic_vacancies:
            if stats["dry_run_verified"] >= limit:
                break

            job_id = str(job.get("job_id", ""))
            title = job.get("title", "")
            company = job.get("company", "")
            snippet = job.get("raw_snippet", "")
            location = job.get("location", "India")

            # 1. Match Scoring Gate (>= 70.0%)
            score_res = self.scorer.evaluate(job_title=title, job_description=snippet)

            if not score_res.passed or score_res.score < min_score:
                stats["skipped"] += 1
                job_record = {
                    "job_id": job_id,
                    "title": title,
                    "company": company,
                    "location": location,
                    "score": score_res.score,
                    "status": "GATED_OUT",
                    "success": False,
                    "steps": 0
                }
                stats["jobs"].append(job_record)
                continue

            stats["scored_above_threshold"] += 1

            # 2. Simulate Questionnaire Solving via solver
            simulated_answers = [
                {"question": "How many years of work experience do you have with PySpark?", "answer": solver.get_numeric_experience_for_skill("pyspark", integer_only=True)},
                {"question": "How many years of work experience do you have with Azure Databricks?", "answer": solver.get_numeric_experience_for_skill("azure databricks", integer_only=True)},
                {"question": "Notice period in days", "answer": solver.determine_text_answer("notice period in days", integer_only=True)},
                {"question": "Are you legally authorized to work in India?", "answer": solver.determine_radio_answer("authorized to work")},
                {"question": "Will you require sponsorship?", "answer": solver.determine_radio_answer("require sponsorship")},
                {"question": "Comfortable with hybrid commute / relocation?", "answer": solver.determine_radio_answer("willing to relocate")}
            ]

            simulated_steps = 4  # Contact -> Resume -> Screening -> Review

            # 3. Log to Excel tracker with status 'SUBMITTED_DRY_RUN' (dry_run=True guarantees no skip-list mutation)
            self.tracker.log_application(
                job_data=job,
                status="SUBMITTED_DRY_RUN",
                match_score=score_res.score,
                steps=simulated_steps,
                dry_run=True
            )

            stats["dry_run_verified"] += 1
            job_record = {
                "job_id": job_id,
                "title": title,
                "company": company,
                "location": location,
                "score": score_res.score,
                "status": "SUBMITTED_DRY_RUN",
                "success": True,
                "steps": simulated_steps,
                "answers": simulated_answers
            }
            stats["jobs"].append(job_record)

        return stats


# ==============================================================================
# 5. LINKEDIN APPLY RUNNER FACADE (PROJECT.MD CONTRACT)
# ==============================================================================

class LinkedInApplyRunner:
    """
    Facade implementing PROJECT.md Interface Contract for LinkedInApplyRunner.
    Wraps LinkedInApplyEngine and provides direct logging helper.
    """
    def __init__(self, headless: bool = True, dry_run: bool = False, limit: int = 15, min_score: float = 70.0):
        self.headless = headless
        self.dry_run = dry_run
        self.limit = limit
        self.min_score = min_score
        self.engine = LinkedInApplyEngine(min_score=min_score)

    async def run(self, keywords: Optional[List[str]] = None, locations: Optional[List[str]] = None) -> Dict[str, Any]:
        """Main coordinator: initializes session, searches vacancies, evaluates score >=70%, applies, and logs to Excel tracker."""
        if self.dry_run:
            return self.engine.run_offline_dry_run(
                keywords=keywords,
                locations=locations,
                limit=self.limit,
                min_score=self.min_score
            )
        return await self.engine.run_apply_cycle(
            keywords=keywords,
            locations=locations,
            limit=self.limit,
            dry_run=self.dry_run,
            headless=self.headless
        )

    def log_application_to_excel(self, entry: Dict[str, Any], tracker_path: Optional[str] = None) -> bool:
        """Logs entry to LinkedIn_Applications_Log worksheet (with fallback to Applications_Log)."""
        tracker = LinkedInApplicationTracker(excel_path=tracker_path)
        return tracker.log_application(
            job_data=entry,
            status=entry.get("status", "APPLIED"),
            match_score=entry.get("match_score"),
            steps=entry.get("steps", 1),
            dry_run=self.dry_run
        )

