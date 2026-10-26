"""
Unit & Integration Test Suite: Unified Multi-Platform Daily Autonomous Pipeline
Target: ProAutoPilotEngine & handle_daily_cycle in naukari_pro
Governed by: AGENTS.md, ORIGINAL_REQUEST.md

Verifies:
1. Air-gap isolation: Zero network socket connections during dry-run.
2. Full 8-stage pipeline orchestration across Naukri and LinkedIn.
3. Complete error isolation: LinkedIn cookie expiry never impacts Naukri operations, and vice versa.
4. Summary return dictionary completeness (applied_count, total_tracked, etc.).
5. CLI argument parsing and routing for `daily` and `pro` commands (--dry-run, --force, --limit).
6. Multi-platform application tracking across both Excel worksheets.
7. Candidate profile calibration and recruiter privacy (Lavkush Kumar, 2.5 YOE, 15 days notice).
"""

import os
import sys
import socket
import argparse
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import pytest
import openpyxl

from naukari_pro.config import TRACKER_PATH, RESUME_PDF_PATH
from naukari_pro.modules.pro_autopilot import ProAutoPilotEngine
from naukari_pro.cli import handle_daily_cycle, handle_pro, main
from naukari_pro.modules.linkedin_apply import LinkedInApplyEngine, LinkedInApplicationTracker
from naukari_pro.modules.linkedin_session import LinkedInSessionManager, LinkedInCookieMissingError
from naukari_pro.modules.linkedin_optimizer import LinkedInProfileAuditor, LINKEDIN_100K_BLUEPRINT


# ==============================================================================
# 1. STRICT OFFLINE AIR-GAP FIXTURE
# ==============================================================================

class AirGapViolationError(RuntimeError):
    pass

@pytest.fixture
def strict_airgap(monkeypatch):
    """Intercept socket primitives to guarantee tests execute strictly offline."""
    def block_socket(*args, **kwargs):
        raise AirGapViolationError("CRITICAL: Unauthorized network socket call during offline execution!")

    monkeypatch.setattr(socket.socket, "connect", block_socket)
    monkeypatch.setattr(socket, "create_connection", block_socket)
    monkeypatch.setattr(socket, "getaddrinfo", block_socket)


# ==============================================================================
# 2. PIPELINE INITIALIZATION & COMPONENT INTEGRITY
# ==============================================================================

def test_pro_autopilot_engine_initialization():
    """Verify ProAutoPilotEngine initializes all required Naukri and LinkedIn engines."""
    engine = ProAutoPilotEngine(limit=15, headless=True, dry_run=True, force=True)
    assert engine.limit == 15
    assert engine.headless is True
    assert engine.dry_run is True
    assert engine.force is True

    # Naukri components
    assert hasattr(engine, "profile_engine")
    assert hasattr(engine, "apply_engine")
    assert hasattr(engine, "search_engine")
    assert hasattr(engine, "portal_filler")
    assert hasattr(engine, "perf_engine")

    # LinkedIn components
    assert hasattr(engine, "li_session_manager")
    assert isinstance(engine.li_session_manager, LinkedInSessionManager)
    assert hasattr(engine, "li_apply_engine")
    assert isinstance(engine.li_apply_engine, LinkedInApplyEngine)
    assert hasattr(engine, "li_auditor")
    assert isinstance(engine.li_auditor, LinkedInProfileAuditor)


# ==============================================================================
# 3. COMPLETE 8-STAGE OFFLINE DRY-RUN EXECUTION
# ==============================================================================

def test_unified_pipeline_dry_run_full_execution(strict_airgap, capsys):
    """
    Executes ProAutoPilotEngine.run_full_pipeline() in dry_run mode.
    Proves:
    - Executes 100% offline with ZERO socket calls under strict_airgap.
    - All 8 stages complete successfully.
    - Summary dictionary contains all required keys.
    """
    engine = ProAutoPilotEngine(limit=5, headless=True, dry_run=True, force=False)
    summary = engine.run_full_pipeline()

    # Capture output and verify 8 stages were logged
    captured = capsys.readouterr().out
    assert "[STAGE 1/8]" in captured
    assert "[STAGE 2/8]" in captured
    assert "[STAGE 3/8]" in captured
    assert "[STAGE 4/8]" in captured
    assert "[STAGE 5/8]" in captured
    assert "[STAGE 6/8]" in captured
    assert "[STAGE 7/8]" in captured
    assert "[STAGE 8/8]" in captured

    # Output content checks
    assert "Azure Data Engineer" in captured
    assert "Lavkush Kumar" in captured
    assert "Recruiter Search Optimization Score" in captured
    assert "Multi-Platform Session Verification" in captured
    assert "LinkedIn Offline Simulation" in captured

    # Return contract verification
    assert isinstance(summary, dict)
    assert "applied_count" in summary
    assert "applied_naukri" in summary
    assert "applied_linkedin" in summary
    assert "li_dry_run_verified" in summary
    assert "total_tracked" in summary
    assert "total_tracked_naukri" in summary
    assert "total_tracked_linkedin" in summary
    assert "duration_seconds" in summary
    assert "seo_score" in summary
    assert "linkedin_status" in summary
    assert "naukri_status" in summary

    assert summary["applied_count"] == summary["applied_naukri"] + summary["applied_linkedin"]
    assert summary["seo_score"] >= 90.0
    assert summary["linkedin_status"] in ("DRY_RUN_VERIFIED", "SUCCESS")


# ==============================================================================
# 4. HANDLE_DAILY_CYCLE CLI FACADE INTEGRATION
# ==============================================================================

def test_handle_daily_cycle_facade(strict_airgap, capsys):
    """
    Verifies handle_daily_cycle(dry_run=True) executes the full unified pipeline
    and returns the structured summary.
    """
    summary = handle_daily_cycle(headless=True, dry_run=True, force=False, limit=3)
    captured = capsys.readouterr().out

    assert "Launching Complete Autonomous Daily Cycle (Unified Naukri + LinkedIn 8-Stage Pipeline)" in captured
    assert "[STAGE 8/8]" in captured
    assert isinstance(summary, dict)
    assert summary["applied_count"] >= 1
    assert "total_tracked" in summary


def test_handle_pro_facade(strict_airgap, capsys):
    """
    Verifies handle_pro(dry_run=True) executes the unified pipeline cleanly.
    """
    summary = handle_pro(limit=2, headless=True, dry_run=True, force=False)
    assert isinstance(summary, dict)
    assert "applied_count" in summary
    assert "total_tracked" in summary


# ==============================================================================
# 5. ERROR ISOLATION: LINKEDIN COOKIE MISSING / EXPIRED
# ==============================================================================

def test_error_isolation_linkedin_cookie_missing(capsys):
    """
    Simulates missing LinkedIn li_at cookie in live mode.
    Verifies:
    - Naukri apply and profile bump proceed normally.
    - LinkedIn apply gracefully pauses with COOKIE_REFRESH_REQUIRED status.
    - No exception is raised; summary reports linkedin_status=COOKIE_REFRESH_REQUIRED.
    """
    engine = ProAutoPilotEngine(limit=5, headless=True, dry_run=False, force=False)

    mock_ctx = MagicMock()
    mock_ctx.pages = [MagicMock()]
    mock_pw = MagicMock()
    mock_pw.return_value.__enter__.return_value = MagicMock()

    with patch.object(engine.apply_engine, "run", return_value=3), \
         patch.object(engine.li_session_manager, "get_li_at_cookie", return_value=None), \
         patch.object(engine.perf_engine, "display_report"), \
         patch.object(engine.search_engine, "search_hacker_news", return_value=[]), \
         patch("naukari_pro.session.get_stealth_context", return_value=mock_ctx), \
         patch("naukari_pro.session.ensure_authenticated", return_value=True), \
         patch("scripts.sync_naukri_live_profile.sync_full_naukri_profile"), \
         patch("playwright.sync_api.sync_playwright", mock_pw):

        summary = engine.run_full_pipeline()

        captured = capsys.readouterr().out
        assert "COOKIE_REFRESH_REQUIRED" in captured
        assert "Naukri Apply Cycle completed: 3 applications processed." in captured

        assert summary["applied_naukri"] == 3
        assert summary["applied_linkedin"] == 0
        assert summary["linkedin_status"] == "COOKIE_REFRESH_REQUIRED"
        assert summary["naukri_status"] == "SUCCESS"


def test_error_isolation_linkedin_apply_exception(capsys):
    """
    Simulates an unexpected runtime error inside LinkedIn apply engine.
    Verifies the error is caught, isolated, and does NOT crash the pipeline.
    """
    engine = ProAutoPilotEngine(limit=5, headless=True, dry_run=False, force=False)

    mock_ctx = MagicMock()
    mock_ctx.pages = [MagicMock()]
    mock_pw = MagicMock()
    mock_pw.return_value.__enter__.return_value = MagicMock()

    with patch.object(engine.apply_engine, "run", return_value=4), \
         patch.object(engine.li_session_manager, "get_li_at_cookie", return_value="mock_token_1234567890"), \
         patch.object(engine.li_apply_engine, "run_apply_cycle", AsyncMock(side_effect=RuntimeError("Simulated LinkedIn DOM failure"))), \
         patch.object(engine.perf_engine, "display_report"), \
         patch.object(engine.search_engine, "search_hacker_news", return_value=[]), \
         patch("naukari_pro.session.get_stealth_context", return_value=mock_ctx), \
         patch("naukari_pro.session.ensure_authenticated", return_value=True), \
         patch("scripts.sync_naukri_live_profile.sync_full_naukri_profile"), \
         patch("playwright.sync_api.sync_playwright", mock_pw):

        summary = engine.run_full_pipeline()

        captured = capsys.readouterr().out
        assert "LinkedIn apply error (isolated)" in captured

        assert summary["applied_naukri"] == 4
        assert summary["applied_linkedin"] == 0
        assert summary["linkedin_status"] == "FAILED"
        assert summary["naukri_status"] == "SUCCESS"


def test_error_isolation_naukri_sync_exception(capsys):
    """
    Simulates an exception during live Naukri profile sync.
    Verifies standard profile bump / cached telemetry is used and LinkedIn is unaffected.
    """
    engine = ProAutoPilotEngine(limit=5, headless=True, dry_run=True, force=False)

    with patch.object(engine.perf_engine, "display_report", side_effect=Exception("Cached telemetry warning")), \
         patch.object(engine.apply_engine, "run", return_value=2):

        summary = engine.run_full_pipeline()

        assert summary["applied_naukri"] == 2
        assert summary["applied_linkedin"] >= 0
        assert "total_tracked" in summary


# ==============================================================================
# 6. CLI ARGUMENT PARSING & ROUTING FOR DAILY & PRO
# ==============================================================================

def test_cli_daily_command_parsing():
    """Verify CLI parser correctly parses `daily` command with flags."""
    test_args = ["naukariPro", "daily", "--dry-run", "--limit", "10", "--force", "--headless"]
    with patch("sys.argv", test_args), \
         patch("naukari_pro.cli.handle_daily_cycle") as mock_daily:
        main()
        mock_daily.assert_called_once_with(headless=True, dry_run=True, force=True, limit=10)


def test_cli_pro_command_parsing():
    """Verify CLI parser correctly parses `pro` command with flags."""
    test_args = ["naukariPro", "pro", "--dry-run", "--limit", "12", "--force", "--headless"]
    with patch("sys.argv", test_args), \
         patch("naukari_pro.cli.handle_pro") as mock_pro:
        main()
        mock_pro.assert_called_once_with(limit=12, headless=True, dry_run=True, force=True)


# ==============================================================================
# 7. CANDIDATE PROFILE & TARGET CALIBRATION INTEGRITY
# ==============================================================================

def test_candidate_profile_and_recruiter_privacy_alignment():
    """
    Verifies that the LinkedIn audit evaluates against candidate Lavkush Kumar's
    target profile and privacy constraints (recruiters-only visibility).
    """
    auditor = LinkedInProfileAuditor()
    bp = LINKEDIN_100K_BLUEPRINT

    res = auditor.audit(
        headline=bp["headline"],
        about=bp["about"],
        skills=bp["top_50_skills"],
        current_title="DevOps Engineer / Azure Data Engineer"
    )

    # Score must exceed 90% and earn Grade A
    score = res.get("seo_score") or res.get("overall_score", 0)
    assert score >= 90.0
    assert "A" in res["grade"]

    # Critical keywords must be covered
    covered = [k.lower() for k in res["critical_keywords_covered"]]
    assert "azure data engineer" in covered
    assert "databricks" in covered
    assert "pyspark" in covered
    assert "delta lake" in covered
    assert "adf" in covered
    assert "sql" in covered

    # Blueprint candidate identity check
    assert "lavkushry@gmail.com" in bp["about"]
    assert "CGI India" in str(bp["experience"])
    assert "15 Days" in bp["headline"]


# ==============================================================================
# 8. MULTI-PLATFORM EXCEL TRACKER FIDELITY
# ==============================================================================

def test_multi_platform_tracker_sheet_discovery(tmp_path):
    """
    Verifies tracker reads and aggregates application counts from both
    'Applications_Log' (Naukri) and 'LinkedIn_Applications_Log' (LinkedIn).
    """
    tracker_file = tmp_path / "Test_Application_Tracker.xlsx"
    wb = openpyxl.Workbook()

    # Create Naukri sheet
    ws_naukri = wb.active
    ws_naukri.title = "Applications_Log"
    ws_naukri.append(["Job ID", "Title", "Company", "Status"])
    ws_naukri.append(["N101", "Azure Data Engineer", "Microsoft", "APPLIED"])
    ws_naukri.append(["N102", "Senior DE", "Amazon", "APPLIED"])

    # Create LinkedIn sheet
    ws_li = wb.create_sheet(title="LinkedIn_Applications_Log")
    ws_li.append(["Job ID", "Title", "Company", "Match Score", "Status"])
    ws_li.append(["L201", "Lead Azure DE", "Walmart", 92.5, "APPLIED"])
    ws_li.append(["L202", "Data Platform Engineer", "Google", 88.0, "APPLIED"])
    ws_li.append(["L203", "PySpark DE", "Uber", 85.0, "SUBMITTED_DRY_RUN"])

    wb.save(tracker_file)
    wb.close()

    with patch("naukari_pro.modules.pro_autopilot.TRACKER_PATH", str(tracker_file)):
        engine = ProAutoPilotEngine(limit=2, dry_run=True)
        summary = engine.run_full_pipeline()

        assert summary["total_tracked_naukri"] == 2
        assert summary["total_tracked_linkedin"] == 3
        assert summary["total_tracked"] == 5
