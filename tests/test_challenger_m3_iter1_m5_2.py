"""
Empirical Adversarial Challenge Suite: Milestone 3 Iteration 1
Autonomous LinkedIn Engine (Features 9-15)
Authored by Challenger 2 (teamwork_preview_challenger_m3_iter1_m5_2)
Governed by: PROJECT.md, TEST_INFRA.md, ORIGINAL_REQUEST.md, AGENTS.md

Adversarial Challenge Dimensions:
1. 2-Tier Resume Attachment Architecture (Card selection vs file upload, fallback to MLOps, missing file handling, corrupted paths)
2. Circuit Breaker Triggers & Error Accounting (3 consecutive errors, security checkpoint URLs & DOM, daily rate-limit banners, jitter delays, and Navigator-Engine double-counting empirical proof)
3. Dry-Run Mode Submission Immunity (Hostile DOM conditions, Submit button NEVER clicked, follow-company uncheck, clean discard, error resilience)
"""

import os
import sys
import json
import socket
import inspect
import asyncio
import functools
import random
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

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
    safe_is_checked,
    safe_count,
    safe_is_visible,
    safe_inner_text,
    humanized_delay
)
from naukari_pro.modules.linkedin_apply import (
    LinkedInApplyEngine,
    LinkedInApplicationTracker,
    LinkedInSessionManager
)
from tests.test_linkedin_suite import make_playwright_cm_mock


def run_async(coro):
    @functools.wraps(coro)
    def wrapper(*args, **kwargs):
        return asyncio.run(coro(*args, **kwargs))
    return wrapper


# ==============================================================================
# SECTION 0: OFFLINE ISOLATION & MOCK FACTORIES
# ==============================================================================

class BlockedNetworkError(RuntimeError):
    pass


def guard_socket_connect(*args, **kwargs):
    raise BlockedNetworkError("Offline Test Violation: Unauthorized network connection attempt!")


@pytest.fixture(autouse=True)
def enforce_offline_isolation(monkeypatch):
    """Intercept socket primitives to guarantee tests execute strictly offline."""
    monkeypatch.setattr(socket.socket, "connect", guard_socket_connect)
    monkeypatch.setattr(socket, "create_connection", guard_socket_connect)
    monkeypatch.setattr(socket, "getaddrinfo", guard_socket_connect)


def make_mock_locator(count: int = 1, visible: bool = True, text: str = "", is_checked: bool = False, attr_map: Optional[dict] = None):
    """Creates a comprehensive Playwright locator mock supporting async operations."""
    loc = MagicMock()
    loc.count = AsyncMock(return_value=count)
    loc.is_visible = AsyncMock(return_value=visible)
    loc.inner_text = AsyncMock(return_value=text)
    loc.is_checked = AsyncMock(return_value=is_checked)
    loc.click = AsyncMock(return_value=None)
    loc.check = AsyncMock(return_value=None)
    loc.uncheck = AsyncMock(return_value=None)
    loc.fill = AsyncMock(return_value=None)
    loc.select_option = AsyncMock(return_value=None)
    loc.set_input_files = AsyncMock(return_value=None)
    
    attr_map = attr_map or {}
    loc.get_attribute = AsyncMock(side_effect=lambda a: attr_map.get(a, None))
    
    loc.first = loc
    loc.last = loc
    loc.nth = MagicMock(return_value=loc)
    return loc


def make_mock_page(current_url: str = "https://www.linkedin.com/jobs/view/410001", locators: Optional[dict] = None):
    """Creates an async MockPage with selectable locators."""
    page = MagicMock()
    page.url = current_url
    page.goto = AsyncMock(return_value=None)
    page.wait_for_selector = AsyncMock(return_value=None)
    page.wait_for_load_state = AsyncMock(return_value=None)
    page.close = AsyncMock(return_value=None)
    page.evaluate = AsyncMock(return_value=None)
    
    locs = locators or {}
    def page_locator(selector):
        for pat, loc in locs.items():
            if pat in selector:
                return loc
        return make_mock_locator(count=0, visible=False)
        
    page.locator = MagicMock(side_effect=page_locator)
    return page


# ==============================================================================
# SECTION 1: 2-TIER RESUME ATTACHMENT ADVERSARIAL CHALLENGES
# ==============================================================================

@run_async
async def test_resume_attachment_card_text_permutations():
    """
    Challenge 1.1: Pre-existing card text matching across uppercase, lowercase,
    whitespace, and already-checked radio button states.
    """
    mgr = LinkedInResumeManager()
    
    test_cases = [
        ("Lavkush_Kumar_Azure_Data_Engineer_Resume.pdf", True),
        ("lavkush kumar - azure data engineer (2026)", True),
        ("AZURE DATA ENGINEER - LAVKUSH KUMAR", True),
        ("Frontend React Developer Resume.pdf", False),
        ("Generic Unrelated Resume Document.pdf", False)
    ]
    
    for card_text, should_match in test_cases:
        mock_radio = make_mock_locator(count=1, visible=True, is_checked=False)
        mock_card = make_mock_locator(count=1, visible=True, text=card_text)
        mock_card.locator = MagicMock(return_value=mock_radio)
        
        card_loc = MagicMock()
        card_loc.count = AsyncMock(return_value=1)
        card_loc.nth = MagicMock(return_value=mock_card)
        card_loc.first = mock_card
        
        modal = MagicMock()
        modal.locator = MagicMock(side_effect=lambda s: card_loc if "jobs-document-upload" in s else make_mock_locator(count=0, visible=False))
        
        res = await mgr.attach_or_select_resume(modal, resume_path="Lavkush_Kumar_Azure_Data_Engineer_Resume.pdf")
        if should_match:
            assert res.success is True, f"Failed on matching card text: {card_text}"
            assert res.method == "CARD_SELECTED"
            mock_radio.check.assert_called_once()
        else:
            # If not matching primary, fallback will select first available card
            assert res.success is True
            assert res.method == "CARD_SELECTED"
            assert res.filename == "existing_default_card"


@run_async
async def test_resume_attachment_already_checked_card_no_redundant_check():
    """
    Challenge 1.2: If pre-existing matching card is ALREADY checked,
    it should NOT call .check() or .click() again, but still report success.
    """
    mgr = LinkedInResumeManager()
    
    mock_radio = make_mock_locator(count=1, visible=True, is_checked=True)  # Already checked
    mock_card = make_mock_locator(count=1, visible=True, text="Lavkush Kumar Azure Data Engineer Resume")
    mock_card.locator = MagicMock(return_value=mock_radio)
    
    card_loc = MagicMock()
    card_loc.count = AsyncMock(return_value=1)
    card_loc.nth = MagicMock(return_value=mock_card)
    card_loc.first = mock_card
    
    modal = MagicMock()
    modal.locator = MagicMock(side_effect=lambda s: card_loc if "jobs-document-upload" in s else make_mock_locator(count=0, visible=False))
    
    res = await mgr.attach_or_select_resume(modal, resume_path="Lavkush_Kumar_Azure_Data_Engineer_Resume.pdf")
    assert res.success is True
    assert res.method == "CARD_SELECTED"
    mock_radio.check.assert_not_called()
    mock_radio.click.assert_not_called()


@run_async
async def test_resume_attachment_card_radio_click_fallback_when_no_check_method():
    """
    Challenge 1.3: If radio element lacks .check() method, it must fall back to .click().
    """
    mgr = LinkedInResumeManager()
    
    mock_radio = MagicMock()
    mock_radio.is_checked = AsyncMock(return_value=False)
    # Delete 'check' attribute so hasattr(mock_radio, 'check') is False
    del mock_radio.check
    mock_radio.click = AsyncMock(return_value=None)
    
    mock_card = make_mock_locator(count=1, visible=True, text="Lavkush Kumar Azure Data Engineer")
    mock_card.locator = MagicMock(return_value=mock_radio)
    
    card_loc = MagicMock()
    card_loc.count = AsyncMock(return_value=1)
    card_loc.nth = MagicMock(return_value=mock_card)
    card_loc.first = mock_card
    
    modal = MagicMock()
    modal.locator = MagicMock(side_effect=lambda s: card_loc if "jobs-document-upload" in s else make_mock_locator(count=0, visible=False))
    
    res = await mgr.attach_or_select_resume(modal, resume_path="Lavkush_Kumar_Azure_Data_Engineer_Resume.pdf")
    assert res.success is True
    assert res.method == "CARD_SELECTED"
    mock_radio.click.assert_called_once()


@run_async
async def test_resume_attachment_tier1_precedence_over_tier2(tmp_path):
    """
    Challenge 1.4: Precedence proof: when BOTH pre-existing matching card AND
    file input element exist, Tier 1 (card selection) MUST win, and set_input_files
    MUST NEVER be invoked.
    """
    pdf_file = tmp_path / "Lavkush_Kumar_Azure_Data_Engineer_Resume.pdf"
    pdf_file.write_text("Dummy Content", encoding="utf-8")
    
    mgr = LinkedInResumeManager(primary_resume_path=str(pdf_file))
    
    # Matching card
    mock_radio = make_mock_locator(count=1, visible=True, is_checked=False)
    mock_card = make_mock_locator(count=1, visible=True, text="Lavkush Kumar Azure Data Engineer")
    mock_card.locator = MagicMock(return_value=mock_radio)
    
    card_loc = MagicMock()
    card_loc.count = AsyncMock(return_value=1)
    card_loc.nth = MagicMock(return_value=mock_card)
    card_loc.first = mock_card
    
    # File input
    mock_file_input = make_mock_locator(count=1, visible=True)
    file_loc = make_mock_locator(count=1, visible=True)
    file_loc.first = mock_file_input
    
    modal = MagicMock()
    def modal_locator(sel):
        if "jobs-document-upload" in sel:
            return card_loc
        if "input[type='file']" in sel:
            return file_loc
        return make_mock_locator(count=0, visible=False)
    modal.locator = MagicMock(side_effect=modal_locator)
    
    res = await mgr.attach_or_select_resume(modal, resume_path=str(pdf_file))
    assert res.success is True
    assert res.method == "CARD_SELECTED"
    mock_radio.check.assert_called_once()
    mock_file_input.set_input_files.assert_not_called()


@run_async
async def test_resume_attachment_tier2_upload_exception_falls_back_to_tier3():
    """
    Challenge 1.5: If set_input_files throws an exception during file upload,
    it must catch the error gracefully and fall back to selecting an existing card.
    """
    mgr = LinkedInResumeManager()
    
    # Mock file input that throws on set_input_files
    mock_file_input = MagicMock()
    mock_file_input.set_input_files = AsyncMock(side_effect=RuntimeError("Playwright File Upload I/O Failure"))
    file_loc = make_mock_locator(count=1, visible=True)
    file_loc.first = mock_file_input
    
    # Existing default card radio
    mock_default_radio = make_mock_locator(count=1, visible=True, is_checked=False)
    
    modal = MagicMock()
    def modal_locator(sel):
        if "div.jobs-document-upload input[type='radio']" in sel:
            loc = make_mock_locator(count=1, visible=True)
            loc.first = mock_default_radio
            return loc
        if "jobs-document-upload" in sel:
            # No matching name card on step 1
            return make_mock_locator(count=0, visible=False)
        if "input[type='file']" in sel:
            return file_loc
        return make_mock_locator(count=0, visible=False)
    modal.locator = MagicMock(side_effect=modal_locator)
    
    # Mock resolve_resume_path to return a valid dummy path
    with patch.object(mgr, "resolve_resume_path", return_value="/tmp/dummy.pdf"):
        res = await mgr.attach_or_select_resume(modal, resume_path="/tmp/dummy.pdf")
        
    assert res.success is True
    assert res.method == "CARD_SELECTED"
    assert res.filename == "existing_default_card"
    mock_default_radio.check.assert_called_once()


@run_async
async def test_resume_attachment_missing_all_files_and_cards_graceful(tmp_path):
    """
    Challenge 1.6: When primary PDF, fallback PDF, all disk candidates,
    and all DOM cards are missing, returns SKIPPED_NOT_FOUND cleanly
    without throwing any unhandled exceptions.
    """
    mgr = LinkedInResumeManager(
        primary_resume_path=str(tmp_path / "nonexistent_primary.pdf"),
        fallback_resume_path=str(tmp_path / "nonexistent_fallback.pdf")
    )
    
    modal = MagicMock()
    modal.locator = MagicMock(return_value=make_mock_locator(count=0, visible=False))
    
    res = await mgr.attach_or_select_resume(modal, resume_path=str(tmp_path / "missing_target.pdf"))
    assert res.success is False
    assert res.method == "SKIPPED_NOT_FOUND"
    assert res.filename == ""
    assert "No resume upload input or cards available" in res.detail


@run_async
async def test_resume_attachment_hostile_corrupt_paths(tmp_path):
    """
    Challenge 1.7: Hostile input types: non-existent files, directories, empty strings.
    """
    dir_path = tmp_path / "a_directory_not_a_file"
    dir_path.mkdir()
    non_existent1 = str(tmp_path / "non_existent_primary.pdf")
    non_existent2 = str(tmp_path / "non_existent_fallback.pdf")
    
    mgr = LinkedInResumeManager(
        primary_resume_path=non_existent1,
        fallback_resume_path=non_existent2
    )
    
    # Non-existent file as requested path
    assert mgr.resolve_resume_path(str(tmp_path / "ghost.pdf")) is None
    # Directory as requested path (isfile is False)
    assert mgr.resolve_resume_path(str(dir_path)) is None
    # None as requested path
    assert mgr.resolve_resume_path(None) is None


# ==============================================================================
# SECTION 2: CIRCUIT BREAKER TRIGGERS & ERROR ACCOUNTING ADVERSARIAL CHALLENGES
# ==============================================================================

def test_circuit_breaker_exact_consecutive_errors_threshold():
    """
    Challenge 2.1: Verify circuit breaker trips precisely at max_consecutive_errors.
    """
    cb = LinkedInCircuitBreaker(max_consecutive_errors=3)
    
    # Error 1
    assert cb.record_failure("Error 1") is False
    assert cb.is_tripped is False
    assert cb.consecutive_errors == 1
    
    # Error 2
    assert cb.record_failure("Error 2") is False
    assert cb.is_tripped is False
    assert cb.consecutive_errors == 2
    
    # Error 3: Trips!
    assert cb.record_failure("Error 3") is True
    assert cb.is_tripped is True
    assert cb.trip_reason == "CONSECUTIVE_ERRORS"
    assert cb.consecutive_errors == 3
    
    # Error 4: Stays tripped
    assert cb.record_failure("Error 4") is True
    assert cb.is_tripped is True
    assert cb.consecutive_errors == 4


def test_circuit_breaker_counter_reset_on_success():
    """
    Challenge 2.2: Intermittent failures must be completely reset by a single success.
    """
    cb = LinkedInCircuitBreaker(max_consecutive_errors=3)
    
    cb.record_failure("Error 1")
    cb.record_failure("Error 2")
    assert cb.consecutive_errors == 2
    
    # Success resets consecutive_errors to 0
    cb.record_success()
    assert cb.consecutive_errors == 0
    assert cb.total_applied == 1
    assert cb.is_tripped is False
    
    # Two more failures do NOT trip because counter started at 0
    cb.record_failure("Error A")
    cb.record_failure("Error B")
    assert cb.consecutive_errors == 2
    assert cb.is_tripped is False
    
    # Another success resets again
    cb.record_success()
    assert cb.consecutive_errors == 0
    assert cb.total_applied == 2


@run_async
async def test_circuit_breaker_security_checkpoint_urls_exhaustive():
    """
    Challenge 2.3: Exhaustive security checkpoint URL pattern detection.
    Every URL in CHECKPOINT_URL_PATTERNS plus query string permutations must trip immediately.
    """
    cb = LinkedInCircuitBreaker()
    
    test_urls = [
        "https://www.linkedin.com/checkpoint/challenge",
        "https://www.linkedin.com/checkpoint/challenge/AQEv1234?redirect=feed",
        "https://www.linkedin.com/checkpoint/security-check",
        "https://www.linkedin.com/checkpoint/rp/verify-identity",
        "https://www.linkedin.com/uas/consumer-captcha",
        "https://www.linkedin.com/uas/captcha?v=2",
        "https://www.linkedin.com/uas/consumer-captcha?session_redirect=https%3A%2F%2Fwww.linkedin.com%2Fjobs",
    ]
    
    for u in test_urls:
        cb.reset()
        mock_page = MagicMock()
        mock_page.url = u
        tripped = await cb.check_security_checkpoint(mock_page)
        assert tripped is True, f"Failed to trip on checkpoint URL: {u}"
        assert cb.is_tripped is True
        assert cb.trip_reason == "SECURITY_CHECKPOINT"
        assert u in cb.trip_detail


@run_async
async def test_circuit_breaker_security_checkpoint_dom_selectors_exhaustive():
    """
    Challenge 2.4: Exhaustive security checkpoint DOM element detection.
    All 6 selectors in CHECKPOINT_SELECTORS must trip when visible.
    """
    cb = LinkedInCircuitBreaker()
    
    for sel in LinkedInCircuitBreaker.CHECKPOINT_SELECTORS:
        cb.reset()
        mock_loc = make_mock_locator(count=1, visible=True)
        page = MagicMock()
        page.url = "https://www.linkedin.com/jobs/view/410001"
        page.locator = MagicMock(side_effect=lambda s, target_sel=sel: mock_loc if s == target_sel else make_mock_locator(count=0, visible=False))
        
        tripped = await cb.check_security_checkpoint(page)
        assert tripped is True, f"Failed to trip on checkpoint DOM selector: {sel}"
        assert cb.is_tripped is True
        assert cb.trip_reason == "SECURITY_CHECKPOINT"


@run_async
async def test_circuit_breaker_hidden_checkpoint_does_not_trip():
    """
    Challenge 2.5: If a captcha selector exists on DOM but is HIDDEN (visible=False),
    it must NOT trip the circuit breaker.
    """
    cb = LinkedInCircuitBreaker()
    hidden_captcha = make_mock_locator(count=1, visible=False)  # Hidden element
    page = MagicMock()
    page.url = "https://www.linkedin.com/jobs/view/410001"
    page.locator = MagicMock(return_value=hidden_captcha)
    
    tripped = await cb.check_security_checkpoint(page)
    assert tripped is False
    assert cb.is_tripped is False


@run_async
async def test_circuit_breaker_daily_rate_limit_banners_exhaustive():
    """
    Challenge 2.6: Exhaustive daily rate limit banner DOM selector detection.
    All 5 selectors in DAILY_LIMIT_SELECTORS must trip immediately.
    """
    cb = LinkedInCircuitBreaker()
    
    for sel in LinkedInCircuitBreaker.DAILY_LIMIT_SELECTORS:
        cb.reset()
        mock_loc = make_mock_locator(count=1, visible=True)
        modal = MagicMock()
        modal.locator = MagicMock(side_effect=lambda s, target_sel=sel: mock_loc if s == target_sel else make_mock_locator(count=0, visible=False))
        
        tripped = await cb.check_daily_rate_limit(modal)
        assert tripped is True, f"Failed to trip on daily limit banner: {sel}"
        assert cb.is_tripped is True
        assert cb.trip_reason == "DAILY_LIMIT_REACHED"


@run_async
async def test_circuit_breaker_throttling_delays_statistical_bounds():
    """
    Challenge 2.7: Statistical verification of jitter delays across 100 trials:
    - Field delay: strictly within [150ms, 400ms]
    - Step delay: strictly within [1200ms, 2800ms]
    - Inter-application delay: strictly within [3000ms, 7000ms]
    - Verify non-deterministic distribution (stdev > 0).
    """
    cb = LinkedInCircuitBreaker()
    
    field_delays = []
    step_delays = []
    job_delays = []
    
    async def capture_delay(min_ms, max_ms, page=None):
        return (min_ms, max_ms)
        
    with patch("naukari_pro.modules.linkedin_apply.humanized_delay", side_effect=capture_delay):
        for _ in range(100):
            # Capture sleep calls directly by wrapping _sleep
            with patch.object(cb, "_sleep", AsyncMock()) as mock_sleep:
                await cb.throttle_field()
                field_delays.append(mock_sleep.call_args[0][0])
                
                await cb.throttle_step()
                step_delays.append(mock_sleep.call_args[0][0])
                
                await cb.throttle_inter_application()
                job_delays.append(mock_sleep.call_args[0][0])
                
    assert len(field_delays) == 100
    assert all(0.15 <= d <= 0.40 for d in field_delays), "Field delay out of [0.15, 0.40]s"
    assert len(set(field_delays)) > 50, "Field delay has insufficient random entropy"
    
    assert len(step_delays) == 100
    assert all(1.2 <= d <= 2.8 for d in step_delays), "Step delay out of [1.2, 2.8]s"
    assert len(set(step_delays)) > 50, "Step delay has insufficient random entropy"
    
    assert len(job_delays) == 100
    assert all(3.0 <= d <= 7.0 for d in job_delays), "Job delay out of [3.0, 7.0]s"
    assert len(set(job_delays)) > 50, "Job delay has insufficient random entropy"


@run_async
async def test_circuit_breaker_double_counting_between_navigator_and_engine(tmp_path):
    """
    Challenge 2.8 (CRITICAL AUDIT / FINDING VERIFICATION):
    Empirical reproduction of circuit breaker double-counting between navigator and engine.
    
    Observation:
    When LinkedInApplyEngine and LinkedInEasyApplyNavigator share the same circuit_breaker:
    1. Inside navigator.execute_easy_apply, unresolvable failures (MODAL_FAILED, STALLED, etc.)
       call self.circuit_breaker.record_failure(...)
    2. Inside LinkedInApplyEngine.run_apply_cycle lines 401-403, it ALSO calls:
       self.circuit_breaker.record_failure(app_res.get("status", "FAILED"))
    
    Empirical Hypothesis:
    A single failed vacancy causes TWO record_failure calls, incrementing consecutive_errors by 2.
    Consequently, TWO failed vacancies cause consecutive_errors to reach 4 (>= 3),
    tripping the circuit breaker on the 2nd vacancy instead of the 3rd!
    """
    shared_cb = LinkedInCircuitBreaker(max_consecutive_errors=3)
    
    # Create engine sharing circuit breaker with real navigator
    session_mgr = MagicMock()
    session_mgr.get_lock = MagicMock(return_value=MagicMock(acquire=MagicMock(return_value=True), release=MagicMock()))
    session_mgr.verify_session = AsyncMock(return_value={"status": "VALID", "authenticated": True, "candidate_name": "Lavkush"})
    
    # Real page mock that implements locator and count properly
    mock_page = make_mock_page()
    mock_ctx = MagicMock(pages=[mock_page], close=AsyncMock())
    session_mgr.create_stealth_context = AsyncMock(return_value=mock_ctx)
    
    # 3 vacancies that will fail to open modal
    vacancies = [
        {"job_id": "41001", "title": "Azure Data Engineer", "company": "Co A", "is_easy_apply": True, "raw_snippet": "PySpark, Databricks, SQL"},
        {"job_id": "41002", "title": "Azure Data Engineer", "company": "Co B", "is_easy_apply": True, "raw_snippet": "PySpark, Databricks, SQL"},
        {"job_id": "41003", "title": "Azure Data Engineer", "company": "Co C", "is_easy_apply": True, "raw_snippet": "PySpark, Databricks, SQL"}
    ]
    
    mock_search = MagicMock()
    mock_search.search_jobs = AsyncMock(return_value=vacancies)
    
    # Real navigator with shared circuit breaker
    real_nav = LinkedInEasyApplyNavigator(circuit_breaker=shared_cb)
    # Mock open_easy_apply_modal to return None (MODAL_FAILED)
    real_nav.open_easy_apply_modal = AsyncMock(return_value=None)
    
    tracker = MagicMock()
    tracker.is_applied = MagicMock(return_value=False)
    
    engine = LinkedInApplyEngine(
        session_manager=session_mgr,
        search_engine=mock_search,
        navigator=real_nav,
        tracker=tracker,
        circuit_breaker=shared_cb,
        min_score=70.0
    )
    score_obj = MagicMock()
    score_obj.passed = True
    score_obj.score = 85.0
    engine.scorer.evaluate = MagicMock(return_value=score_obj)
    
    with patch("naukari_pro.modules.linkedin_apply.humanized_delay", AsyncMock()), \
         patch("playwright.async_api.async_playwright", make_playwright_cm_mock(mock_ctx)):
         
        stats = await engine.run_apply_cycle(
            keywords=["Azure Data Engineer"],
            locations=["Hyderabad"],
            limit=5,
            dry_run=False
        )
        
    # EMPIRICAL MEASUREMENT:
    # Notice: shared_cb was tripped!
    assert shared_cb.is_tripped is True
    assert shared_cb.trip_reason == "CONSECUTIVE_ERRORS"
    # REMEDIATION VERIFICATION:
    # Double counting is eliminated. Navigator records failure once.
    # Exactly 3 failed jobs are attempted before tripping the breaker (max_consecutive_errors=3):
    assert shared_cb.is_tripped is True
    assert shared_cb.trip_reason == "CONSECUTIVE_ERRORS"
    assert len(stats["jobs"]) == 3, f"Expected 3 attempted jobs without double-counting, got {len(stats['jobs'])}"
    assert shared_cb.consecutive_errors >= 3
    print(f"\n[REMEDIATION VERIFIED] Double-counting eliminated: {len(stats['jobs'])} failed jobs caused circuit breaker trip (consecutive_errors={shared_cb.consecutive_errors})")


@run_async
async def test_circuit_breaker_success_double_counting_between_navigator_and_engine():
    """
    Challenge 2.9 (CRITICAL AUDIT / FINDING VERIFICATION):
    Empirical reproduction of total_applied double-increment on successful applications.
    
    When an application succeeds (or completes dry-run):
    1. Inside navigator.execute_easy_apply:
       self.circuit_breaker.record_success() (increments total_applied by 1)
    2. Inside LinkedInApplyEngine.run_apply_cycle lines 395/399:
       self.circuit_breaker.record_success() (increments total_applied by 1 again)
    
    Hypothesis:
    A single successful application increments total_applied to 2 instead of 1.
    """
    shared_cb = LinkedInCircuitBreaker(max_consecutive_errors=3)
    
    session_mgr = MagicMock()
    session_mgr.get_lock = MagicMock(return_value=MagicMock(acquire=MagicMock(return_value=True), release=MagicMock()))
    session_mgr.verify_session = AsyncMock(return_value={"status": "VALID", "authenticated": True, "candidate_name": "Lavkush"})
    
    mock_page = make_mock_page()
    mock_ctx = MagicMock(pages=[mock_page], close=AsyncMock())
    session_mgr.create_stealth_context = AsyncMock(return_value=mock_ctx)
    
    vacancies = [
        {"job_id": "41001", "title": "Azure Data Engineer", "company": "Co A", "is_easy_apply": True, "raw_snippet": "PySpark, Databricks, SQL"}
    ]
    
    mock_search = MagicMock()
    mock_search.search_jobs = AsyncMock(return_value=vacancies)
    
    real_nav = LinkedInEasyApplyNavigator(circuit_breaker=shared_cb)
    async def mock_execute(*args, **kwargs):
        shared_cb.record_success()
        return {"success": True, "status": "DRY_RUN_VERIFIED", "job_id": "41001", "steps": 1}
    real_nav.execute_easy_apply = mock_execute
    
    tracker = MagicMock()
    tracker.is_applied = MagicMock(return_value=False)
    
    engine = LinkedInApplyEngine(
        session_manager=session_mgr,
        search_engine=mock_search,
        navigator=real_nav,
        tracker=tracker,
        circuit_breaker=shared_cb,
        min_score=70.0
    )
    score_obj = MagicMock()
    score_obj.passed = True
    score_obj.score = 85.0
    engine.scorer.evaluate = MagicMock(return_value=score_obj)
    
    with patch("naukari_pro.modules.linkedin_apply.humanized_delay", AsyncMock()), \
         patch("playwright.async_api.async_playwright", make_playwright_cm_mock(mock_ctx)):
        stats = await engine.run_apply_cycle(
            keywords=["Azure Data Engineer"],
            locations=["Hyderabad"],
            limit=5,
            dry_run=True
        )
        
    assert stats["dry_run_verified"] == 1
    assert len(stats["jobs"]) == 1
    # REMEDIATION VERIFICATION: total_applied is exactly 1 (no double increment):
    assert shared_cb.total_applied == 1, f"Expected total_applied=1 without double counting, got {shared_cb.total_applied}"
    print(f"\n[REMEDIATION VERIFIED] Success double-counting eliminated: 1 application resulted in total_applied={shared_cb.total_applied}")


# ==============================================================================
# SECTION 3: DRY-RUN MODE SUBMISSION IMMUNITY ADVERSARIAL CHALLENGES
# ==============================================================================

@run_async
async def test_dry_run_submit_button_immunity_under_hostile_conditions(tmp_path):
    """
    Challenge 3.1: Under hostile DOM conditions in dry_run=True:
    1. Multiple submit buttons are present and visible.
    2. Review button and next buttons are also present.
    3. Follow company checkbox is present and checked.
    4. Assert Submit button click is NEVER invoked.
    5. Assert Follow company is unchecked.
    6. Assert modal is cleanly dismissed with confirmation.
    7. Assert DRY_RUN_VERIFIED payload returned with dry_run=True.
    8. Assert circuit_breaker.record_success() was called.
    """
    cb = LinkedInCircuitBreaker(max_consecutive_errors=3)
    cb.record_failure("Pre-existing error")
    assert cb.consecutive_errors == 1
    
    resume_file = tmp_path / "Lavkush_Kumar_Azure_Data_Engineer_Resume.pdf"
    resume_file.write_text("Dummy Content", encoding="utf-8")
    
    # 1. Easy Apply button
    apply_btn = make_mock_locator(count=1, visible=True, text="Easy Apply")
    
    # 2. Hostile Submit button: if clicked, will record call
    submit_btn = make_mock_locator(count=1, visible=True, text="Submit application")
    submit_btn.click = AsyncMock(return_value=None)
    
    # 3. Follow company checkbox (initially checked)
    follow_cb = make_mock_locator(count=1, visible=True, is_checked=True)
    follow_cb.uncheck = AsyncMock(return_value=None)
    
    # 4. Dismiss button
    dismiss_btn = make_mock_locator(count=1, visible=True, text="Dismiss")
    dismiss_confirm_btn = make_mock_locator(count=1, visible=True, text="Discard")
    
    # Construct modal element
    modal_elem = MagicMock()
    def modal_locator(sel):
        if "submit" in sel.lower():
            return submit_btn
        if "follow" in sel.lower():
            return follow_cb
        if "jobs-document-upload" in sel:
            return make_mock_locator(count=0, visible=False)
        if "input[type='file']" in sel:
            f_loc = make_mock_locator(count=1, visible=True)
            f_loc.first = make_mock_locator(count=1, visible=True)
            return f_loc
        return make_mock_locator(count=0, visible=False)
    modal_elem.locator = MagicMock(side_effect=modal_locator)
    
    modal_page = make_mock_locator(count=1, visible=True)
    modal_page.first = modal_elem
    
    page = MagicMock()
    page.url = "https://www.linkedin.com/jobs/view/410099"
    def page_locator(sel):
        if "jobs-apply-button" in sel:
            return apply_btn
        if "jobs-easy-apply-modal" in sel or "[data-test-modal]" in sel:
            return modal_page
        if "dismiss" in sel.lower():
            return dismiss_btn
        if "discard" in sel.lower():
            return dismiss_confirm_btn
        return make_mock_locator(count=0, visible=False)
    page.locator = MagicMock(side_effect=page_locator)
    
    bot = LinkedInEasyApplyBot(page=page, resume_path=str(resume_file), circuit_breaker=cb)
    
    with patch("naukari_pro.modules.linkedin_apply.humanized_delay", AsyncMock()):
        res = await bot.execute_easy_apply(
            page=page,
            job_info={"job_id": "410099", "title": "Azure Data Engineer", "company": "Target Tier-1"},
            dry_run=True
        )
        
    # VERIFICATIONS:
    # 1. Submit button was NEVER clicked
    submit_btn.click.assert_not_called()
    assert submit_btn.first.click.call_count == 0
    
    # 2. Follow company was unchecked
    follow_cb.uncheck.assert_called_once()
    
    # 3. Dismiss was clicked
    assert dismiss_btn.first.click.called
    assert dismiss_confirm_btn.first.click.called
    
    # 4. Result payload
    assert res["success"] is True
    assert res["status"] == "DRY_RUN_VERIFIED"
    assert res["dry_run"] is True
    assert res["job_id"] == "410099"
    
    # 5. Circuit breaker success record
    assert cb.consecutive_errors == 0
    assert cb.total_applied == 1
    
    # 6. Final State
    assert bot.current_state == ModalState.TERMINAL_DRY_RUN


@run_async
async def test_dry_run_uncheck_follow_company_when_already_unchecked():
    """
    Challenge 3.2: If follow company is already unchecked (is_checked=False),
    uncheck() or click() must NOT be called.
    """
    bot = LinkedInEasyApplyBot()
    follow_cb = make_mock_locator(count=1, visible=True, is_checked=False)
    
    modal = MagicMock()
    modal.locator = MagicMock(side_effect=lambda s: follow_cb if "follow" in s.lower() else make_mock_locator(count=0, visible=False))
    
    unchecked = await bot.uncheck_follow_company(modal)
    assert unchecked is False
    follow_cb.uncheck.assert_not_called()
    follow_cb.click.assert_not_called()


@run_async
async def test_dry_run_follow_company_click_fallback_when_uncheck_raises():
    """
    Challenge 3.3: If checkbox.uncheck() raises an exception, it must fall back
    to click(force=True).
    """
    bot = LinkedInEasyApplyBot()
    follow_cb = make_mock_locator(count=1, visible=True, is_checked=True)
    follow_cb.uncheck = AsyncMock(side_effect=RuntimeError("Uncheck unsupported"))
    follow_cb.click = AsyncMock(return_value=None)
    
    modal = MagicMock()
    modal.locator = MagicMock(side_effect=lambda s: follow_cb if "follow" in s.lower() else make_mock_locator(count=0, visible=False))
    
    unchecked = await bot.uncheck_follow_company(modal)
    assert unchecked is True
    follow_cb.click.assert_called_once_with(force=True)


@run_async
async def test_dry_run_unresolvable_validation_error_aborts_without_submit(tmp_path):
    """
    Challenge 3.4: Under dry-run mode with unresolvable inline validation errors,
    the bot must auto-heal, fail, discard the modal cleanly, and NEVER click submit.
    """
    resume_file = tmp_path / "resume.pdf"
    resume_file.write_text("Dummy", encoding="utf-8")
    
    apply_btn = make_mock_locator(count=1, visible=True, text="Easy Apply")
    submit_btn = make_mock_locator(count=0, visible=False, text="Submit application")
    submit_btn.click = AsyncMock(return_value=None)
    # Next button cannot advance due to form validation error
    next_btn = make_mock_locator(count=1, visible=True, text="Next")
    next_btn.click = AsyncMock(side_effect=Exception("Form validation error prevents advancing"))
    
    dismiss_btn = make_mock_locator(count=1, visible=True, text="Dismiss")
    err_loc = make_mock_locator(count=1, visible=True, text="Enter a valid response")
    
    modal_elem = MagicMock()
    def modal_locator(sel):
        if "artdeco-inline-feedback--error" in sel:
            return err_loc
        if "next" in sel.lower():
            return next_btn
        return make_mock_locator(count=0, visible=False)
    modal_elem.locator = MagicMock(side_effect=modal_locator)
    
    modal_page = make_mock_locator(count=1, visible=True)
    modal_page.first = modal_elem
    
    page = MagicMock()
    def page_locator(sel):
        if "jobs-apply-button" in sel:
            return apply_btn
        if "jobs-easy-apply-modal" in sel or "[data-test-modal]" in sel:
            return modal_page
        if "dismiss" in sel.lower():
            return dismiss_btn
        return make_mock_locator(count=0, visible=False)
    page.locator = MagicMock(side_effect=page_locator)
    
    cb = LinkedInCircuitBreaker()
    bot = LinkedInEasyApplyBot(page=page, resume_path=str(resume_file), circuit_breaker=cb)
    
    with patch("naukari_pro.modules.linkedin_apply.humanized_delay", AsyncMock()):
        res = await bot.execute_easy_apply(
            page=page,
            job_info={"job_id": "410055", "title": "Data Engineer", "company": "Corp"},
            dry_run=True
        )
        
    assert res["success"] is False
    assert res["status"] == "DISCARDED_UNRESOLVABLE"
    submit_btn.click.assert_not_called()
    assert dismiss_btn.first.click.called
    assert cb.consecutive_errors == 1


@run_async
async def test_dry_run_security_checkpoint_on_initial_page_halts_immediately():
    """
    Challenge 3.5: If security checkpoint URL is detected before opening modal,
    execution halts immediately with CHECKPOINT_BLOCKED without touching modal.
    """
    cb = LinkedInCircuitBreaker()
    page = MagicMock()
    page.url = "https://www.linkedin.com/checkpoint/challenge/AQE_token"
    page.locator = MagicMock(return_value=make_mock_locator(count=0, visible=False))
    
    bot = LinkedInEasyApplyBot(page=page, circuit_breaker=cb)
    res = await bot.execute_easy_apply(
        page=page,
        job_info={"job_id": "410077", "title": "Data Engineer", "company": "Corp"},
        dry_run=True
    )
    
    assert res["success"] is False
    assert res["status"] == "CHECKPOINT_BLOCKED"
    assert cb.is_tripped is True
    assert cb.trip_reason == "SECURITY_CHECKPOINT"


@run_async
async def test_dry_run_daily_rate_limit_banner_on_modal_aborts_immediately():
    """
    Challenge 3.6: If daily rate limit banner appears on modal during dry-run,
    the bot halts immediately with RATE_LIMITED, trips breaker, and discards modal.
    """
    cb = LinkedInCircuitBreaker()
    apply_btn = make_mock_locator(count=1, visible=True, text="Easy Apply")
    dismiss_btn = make_mock_locator(count=1, visible=True, text="Dismiss")
    limit_banner = make_mock_locator(count=1, visible=True, text="reached your application limit for today")
    
    modal_elem = MagicMock()
    modal_elem.locator = MagicMock(side_effect=lambda s: limit_banner if "reached your application limit for today" in s else make_mock_locator(count=0, visible=False))
    modal_page = make_mock_locator(count=1, visible=True)
    modal_page.first = modal_elem
    
    page = MagicMock()
    page.url = "https://www.linkedin.com/jobs/view/410088"
    def page_locator(sel):
        if "jobs-apply-button" in sel:
            return apply_btn
        if "jobs-easy-apply-modal" in sel or "[data-test-modal]" in sel:
            return modal_page
        if "dismiss" in sel.lower():
            return dismiss_btn
        return make_mock_locator(count=0, visible=False)
    page.locator = MagicMock(side_effect=page_locator)
    
    bot = LinkedInEasyApplyBot(page=page, circuit_breaker=cb)
    
    with patch("naukari_pro.modules.linkedin_apply.humanized_delay", AsyncMock()):
        res = await bot.execute_easy_apply(
            page=page,
            job_info={"job_id": "410088", "title": "Data Engineer", "company": "Corp"},
            dry_run=True
        )
        
    assert res["success"] is False
    assert res["status"] == "RATE_LIMITED"
    assert cb.is_tripped is True
    assert cb.trip_reason == "DAILY_LIMIT_REACHED"
    assert dismiss_btn.first.click.called
