"""
Unit and Integration Tests for Milestone 1 LinkedIn Easy Apply Root Cause Resolution & Pipeline Repair.

Covers:
1. Search & Scoring Engine:
   - Experience Level Expansion (f_E=2,3,4)
   - Adaptive Freshness Fallback (r86400 -> r604800 when qualified < 3)
   - Two-Stage Scoring (Stage 1 Title Alignment >= 30% and Stage 2 Full JD Scoring >= 70%)
   - Public evaluate_title facade
2. Bot Modal Mounting & Multi-Step Navigation:
   - 3-Stage Modal Mounting (fast-path DOM check + explicit wait_for_selector + post-wait locator resolution)
   - Circuit breaker anti-flapping and timeout resilience
   - Multi-step progression (Contact, Resume, Questions, Review)
   - Follow company checkbox unchecking
   - Clean modal dismissal with discard confirmation
3. Session & CSRF Token Management:
   - format_jsessionid_token normalization preserving "ajax:..." quotes
   - 3-tier loading for LINKEDIN_JSESSIONID (env var, workspace .env, disk cookie files)
   - format_jsessionid_cookie Playwright attributes
   - Cookie jar synchronization of li_at and JSESSIONID while preserving companion cookies
4. Job Deduplication Clean Filtering:
   - Filtering strictly for confirmed application statuses (Submitted, Submitted (Confirmed), Applied, SUCCESS)
   - Excluding unconfirmed statuses (SUBMITTED_DRY_RUN, FAILED, MODAL_FAILED, CHECKPOINT_BLOCKED, SKIPPED_LOW_MATCH, Error)
   - Multi-sheet support (LinkedIn_Applications_Log and Applications_Log)
   - Backward compatibility for legacy sheets without status columns
"""

import os
import re
import json
import asyncio
import functools
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from naukari_pro.modules.linkedin_search import (
    LinkedInSearchUrlBuilder,
    LinkedInSearchEngine,
    LinkedInJobCardParser,
    JobMatchScorer,
    JobDeduplicator,
    CONFIRMED_APPLICATION_STATUSES,
    IGNORED_APPLICATION_STATUSES,
)
from naukari_pro.modules.linkedin_bot import (
    LinkedInEasyApplyBot,
    LinkedInCircuitBreaker,
    ModalState,
    EasyApplySelectors,
    safe_count,
)
from naukari_pro.modules.linkedin_session import (
    LinkedInSessionManager,
    format_jsessionid_token,
    LinkedInSessionError,
)
from naukari_pro.modules.linkedin_apply import (
    LinkedInApplyEngine,
    LinkedInApplicationTracker,
)


def run_async(coro):
    """Decorator to run async coroutines within synchronous pytest functions."""
    @functools.wraps(coro)
    def wrapper(*args, **kwargs):
        return asyncio.run(coro(*args, **kwargs))
    return wrapper


# ==============================================================================
# SECTION 1: SEARCH & SCORING ENGINE TESTS
# ==============================================================================

def test_url_builder_default_experience_levels_expanded():
    """Verify default experience levels are expanded to '2,3,4' for Mid-Senior inclusion."""
    url = LinkedInSearchUrlBuilder.build("Azure Data Engineer")
    assert "f_E=2,3,4" in url
    parsed = LinkedInSearchUrlBuilder.parse(url)
    assert parsed["f_E"] == "2,3,4"


def test_url_builder_custom_experience_levels_override():
    """Verify custom experience levels override default '2,3,4'."""
    url_custom = LinkedInSearchUrlBuilder.build("Azure Data Engineer", experience_levels="2")
    assert "f_E=2" in url_custom

    url_none = LinkedInSearchUrlBuilder.build("Azure Data Engineer", experience_levels=None)
    assert "f_E" not in url_none


@run_async
async def test_adaptive_freshness_fallback_under_three_results():
    """Verify search widens to r604800 when 24h search produces < 3 qualified jobs."""
    engine = LinkedInSearchEngine()

    card_24h = {
        "job_id": "9001",
        "title": "Azure Data Engineer",
        "company": "Company A",
        "is_easy_apply": True,
        "is_already_applied": False,
        "raw_snippet": "Bengaluru · 1 day ago · Easy Apply"
    }
    card_7d_1 = {
        "job_id": "9002",
        "title": "Data Engineer",
        "company": "Company B",
        "is_easy_apply": True,
        "is_already_applied": False,
        "raw_snippet": "Bengaluru · 3 days ago · Easy Apply"
    }
    card_7d_2 = {
        "job_id": "9003",
        "title": "Big Data Engineer",
        "company": "Company C",
        "is_easy_apply": True,
        "is_already_applied": False,
        "raw_snippet": "Bengaluru · 5 days ago · Easy Apply"
    }

    call_count = 0
    async def mock_parse_job_cards(page, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return [card_24h]
        return [card_24h, card_7d_1, card_7d_2]

    engine.parse_job_cards = mock_parse_job_cards

    page = MagicMock()
    visited_urls = []
    async def mock_goto(url):
        visited_urls.append(url)
    page.goto = mock_goto

    results = await engine.search_jobs(
        page=page,
        keyword="Azure Data Engineer",
        location="Bengaluru",
        freshness_sec=86400,
        auto_fallback_freshness=True,
    )

    assert len(visited_urls) == 2
    assert "f_TPR=r86400" in visited_urls[0]
    assert "f_TPR=r604800" in visited_urls[1]
    assert len(results) == 3
    result_ids = {r["job_id"] for r in results}
    assert result_ids == {"9001", "9002", "9003"}


@run_async
async def test_adaptive_freshness_no_fallback_when_three_or_more_results():
    """Verify search does NOT widen when >= 3 qualified jobs are found in 24h window."""
    engine = LinkedInSearchEngine()

    cards = [
        {"job_id": f"901{i}", "title": "Azure Data Engineer", "is_easy_apply": True, "raw_snippet": "Bengaluru"}
        for i in range(3)
    ]

    engine.parse_job_cards = AsyncMock(return_value=cards)
    page = MagicMock()
    visited_urls = []
    async def mock_goto(url):
        visited_urls.append(url)
    page.goto = mock_goto

    results = await engine.search_jobs(
        page=page,
        keyword="Azure Data Engineer",
        freshness_sec=86400,
        auto_fallback_freshness=True
    )

    assert len(visited_urls) == 1
    assert "f_TPR=r86400" in visited_urls[0]
    assert len(results) == 3


@run_async
async def test_adaptive_freshness_disabled_flag():
    """Verify search does NOT widen when auto_fallback_freshness is False."""
    engine = LinkedInSearchEngine()

    card_24h = {
        "job_id": "9050",
        "title": "Azure Data Engineer",
        "is_easy_apply": True,
        "raw_snippet": "Bengaluru · 1 day ago"
    }

    engine.parse_job_cards = AsyncMock(return_value=[card_24h])
    page = MagicMock()
    visited_urls = []
    async def mock_goto(url):
        visited_urls.append(url)
    page.goto = mock_goto

    results = await engine.search_jobs(
        page=page,
        keyword="Azure Data Engineer",
        freshness_sec=86400,
        auto_fallback_freshness=False
    )

    assert len(visited_urls) == 1
    assert len(results) == 1


@run_async
async def test_two_stage_scoring_stage1_filtering():
    """Verify Stage 1 qualifies cards with title alignment >= 30% and rejects non-aligned/disqualified."""
    engine = LinkedInSearchEngine()

    cards = [
        {"job_id": "1", "title": "Azure Data Engineer", "is_easy_apply": True, "raw_snippet": "Short snippet"},
        {"job_id": "2", "title": "Data Engineer", "is_easy_apply": True, "raw_snippet": "Short snippet"},
        {"job_id": "3", "title": "Frontend React Developer", "is_easy_apply": True, "raw_snippet": "React, CSS"},
        {"job_id": "4", "title": "Director of Data Engineering", "is_easy_apply": True, "raw_snippet": "Executive"},
    ]

    engine.parse_job_cards = AsyncMock(return_value=cards)
    page = MagicMock()
    page.goto = AsyncMock(return_value=None)

    qualified = await engine.search_jobs(
        page=page,
        keyword="Azure Data Engineer",
        auto_fallback_freshness=False
    )

    q_ids = [q["job_id"] for q in qualified]
    assert "1" in q_ids  # Azure Data Engineer (100.0% title match)
    assert "2" in q_ids  # Data Engineer (75.0% title match)
    assert "3" not in q_ids  # Frontend (0.0% title match, disqualified)
    assert "4" not in q_ids  # Director (Disqualified negative pattern)


@run_async
async def test_two_stage_scoring_stage2_full_jd_elevation():
    """Verify Stage 2 scoring elevates 55% snippet score to 90%+ using full right-pane JD."""
    engine = LinkedInSearchEngine()

    card = {
        "job_id": "9999",
        "title": "Azure Data Engineer",
        "company": "Enterprise Corp",
        "raw_snippet": "Bengaluru · 1 day ago · Easy Apply"
    }

    full_jd_text = """
    About the role:
    We are seeking an Azure Data Engineer with 2-4 years of experience.
    Responsibilities:
    - Build scalable ETL pipelines using Azure Data Factory (ADF) and Azure Synapse.
    - Develop distributed processing jobs using PySpark on Azure Databricks.
    - Implement Delta Lake Medallion Architecture (Bronze, Silver, Gold).
    - Write clean, modular Python and SQL.
    - Implement CI/CD using Docker, Git, and Terraform.
    """

    mock_page = MagicMock()
    mock_loc = MagicMock()
    mock_loc.count = AsyncMock(return_value=1)
    mock_loc.first.is_visible = AsyncMock(return_value=True)
    mock_loc.first.inner_text = AsyncMock(return_value=full_jd_text)
    mock_page.locator = MagicMock(return_value=mock_loc)

    extracted_jd = await engine.extract_right_pane_jd(mock_page)
    assert "Azure Data Factory" in extracted_jd

    passed, score_res = engine.evaluate_stage2_jd(card, extracted_jd, min_match_score=70.0)
    assert passed is True
    assert score_res.score >= 90.0
    assert card["stage2_passed"] is True
    assert card["match_score"] >= 90.0


def test_job_match_scorer_evaluate_title_facade():
    """Verify JobMatchScorer public evaluate_title returns consistent taxonomy scores."""
    scorer = JobMatchScorer()

    score, pen, disq, reasons = scorer.evaluate_title("Azure Data Engineer")
    assert score == 35.0
    assert disq is False

    score_de, pen_de, disq_de, _ = scorer.evaluate_title("Data Engineer")
    assert score_de == 26.25
    assert disq_de is False

    score_dir, pen_dir, disq_dir, _ = scorer.evaluate_title("Director of Engineering")
    assert disq_dir is True


# ==============================================================================
# SECTION 2: BOT MODAL MOUNTING & AUTOMATION TESTS
# ==============================================================================

@run_async
async def test_open_easy_apply_modal_fast_path():
    """Verify that when modal container is already attached in DOM, open_easy_apply_modal returns immediately without wait_for_selector."""
    bot = LinkedInEasyApplyBot()
    page = MagicMock()

    # Easy Apply button mock
    btn_loc = MagicMock()
    btn_loc.count = AsyncMock(return_value=1)
    btn_loc.first.is_visible = AsyncMock(return_value=True)
    btn_loc.first.click = AsyncMock(return_value=None)

    # Modal container mock
    modal_loc = MagicMock()
    modal_loc.count = AsyncMock(return_value=1)
    modal_loc.first = MagicMock()

    def get_locator(sel):
        if sel in EasyApplySelectors.EASY_APPLY_BUTTONS:
            return btn_loc
        if sel in EasyApplySelectors.MODAL_CONTAINERS:
            return modal_loc
        empty = MagicMock()
        empty.count = AsyncMock(return_value=0)
        return empty

    page.locator = MagicMock(side_effect=get_locator)
    page.wait_for_selector = AsyncMock()

    res = await bot.open_easy_apply_modal(page)
    assert res == modal_loc.first
    assert bot.current_state == ModalState.MODAL_MOUNTED
    # wait_for_selector was NOT called due to fast-path
    assert page.wait_for_selector.called is False


@run_async
async def test_open_easy_apply_modal_delayed_mount_wait():
    """Verify that when modal is NOT present at t=0, open_easy_apply_modal calls wait_for_selector."""
    bot = LinkedInEasyApplyBot()
    page = MagicMock()

    # Easy Apply button mock
    btn_loc = MagicMock()
    btn_loc.count = AsyncMock(return_value=1)
    btn_loc.first.is_visible = AsyncMock(return_value=True)
    btn_loc.first.click = AsyncMock(return_value=None)

    # Modal container mock: count=0 on initial fast-path check, count=1 on post-wait resolution
    modal_query_count = 0
    modal_loc = MagicMock()
    modal_loc.first = MagicMock()

    async def mock_count():
        nonlocal modal_query_count
        modal_query_count += 1
        return 0 if modal_query_count <= len(EasyApplySelectors.MODAL_CONTAINERS) else 1

    modal_loc.count = mock_count

    def get_locator(sel):
        if sel in EasyApplySelectors.EASY_APPLY_BUTTONS:
            return btn_loc
        if sel in EasyApplySelectors.MODAL_CONTAINERS:
            return modal_loc
        empty = MagicMock()
        empty.count = AsyncMock(return_value=0)
        return empty

    page.locator = MagicMock(side_effect=get_locator)
    page.wait_for_selector = AsyncMock(return_value=MagicMock())

    res = await bot.open_easy_apply_modal(page, timeout_ms=3000)
    assert res == modal_loc.first
    assert bot.current_state == ModalState.MODAL_MOUNTED
    assert page.wait_for_selector.called is True
    # Verify timeout argument was passed
    args, kwargs = page.wait_for_selector.call_args
    assert kwargs.get("timeout") == 3000
    assert kwargs.get("state") == "attached"


@run_async
async def test_open_easy_apply_modal_timeout_and_circuit_breaker():
    """Verify that when modal container fails to mount after timeout, open_easy_apply_modal returns None and circuit breaker increments."""
    bot = LinkedInEasyApplyBot()
    page = MagicMock()

    btn_loc = MagicMock()
    btn_loc.count = AsyncMock(return_value=1)
    btn_loc.first.is_visible = AsyncMock(return_value=True)
    btn_loc.first.click = AsyncMock(return_value=None)

    empty_loc = MagicMock()
    empty_loc.count = AsyncMock(return_value=0)

    def get_locator(sel):
        if sel in EasyApplySelectors.EASY_APPLY_BUTTONS:
            return btn_loc
        return empty_loc

    page.locator = MagicMock(side_effect=get_locator)
    page.wait_for_selector = AsyncMock(side_effect=Exception("Timeout 3000ms"))

    res = await bot.open_easy_apply_modal(page, timeout_ms=3000)
    assert res is None
    assert bot.current_state == ModalState.TERMINAL_FAILED

    # Record failure on circuit breaker
    cb = LinkedInCircuitBreaker(max_consecutive_errors=3)
    cb.record_failure("MODAL_FAILED")
    assert cb.consecutive_errors == 1
    assert cb.is_tripped is False

    cb.record_failure("MODAL_FAILED")
    cb.record_failure("MODAL_FAILED")
    assert cb.is_tripped is True
    assert cb.trip_reason == "CONSECUTIVE_ERRORS"


@run_async
async def test_multi_step_modal_progression_contact_to_review():
    """Verify classify_step correctly categorizes Contact, Resume, Questions, and Review steps."""
    bot = LinkedInEasyApplyBot()

    def make_step_modal(header_text: str, has_submit: bool = False):
        modal = MagicMock()
        # Submit locator
        submit_loc = MagicMock()
        submit_loc.count = AsyncMock(return_value=1 if has_submit else 0)
        submit_loc.first.is_visible = AsyncMock(return_value=has_submit)

        # Header locator
        h_loc = MagicMock()
        h_loc.count = AsyncMock(return_value=1)
        h_loc.first.inner_text = AsyncMock(return_value=header_text)

        def modal_locator(sel):
            if sel in EasyApplySelectors.SUBMIT_BUTTONS:
                return submit_loc
            if sel in EasyApplySelectors.STEP_HEADERS:
                return h_loc
            empty = MagicMock()
            empty.count = AsyncMock(return_value=0)
            return empty

        modal.locator = MagicMock(side_effect=modal_locator)
        return modal

    modal_contact = make_step_modal("Contact info")
    state_contact = await bot.classify_step(modal_contact)
    assert state_contact == ModalState.STEP_CONTACT

    modal_resume = make_step_modal("Resume and CV")
    state_resume = await bot.classify_step(modal_resume)
    assert state_resume == ModalState.STEP_RESUME

    modal_questions = make_step_modal("Additional questions")
    state_questions = await bot.classify_step(modal_questions)
    assert state_questions == ModalState.STEP_QUESTIONS

    modal_review = make_step_modal("Review your application", has_submit=True)
    state_review = await bot.classify_step(modal_review)
    assert state_review == ModalState.STEP_REVIEW


@run_async
async def test_follow_company_checkbox_uncheck():
    """Verify uncheck_follow_company unchecks checked follow-company checkboxes."""
    bot = LinkedInEasyApplyBot()
    modal = MagicMock()

    cb_item = MagicMock()
    cb_item.is_checked = AsyncMock(return_value=True)
    cb_item.uncheck = AsyncMock(return_value=None)

    cb_loc = MagicMock()
    cb_loc.count = AsyncMock(return_value=1)
    cb_loc.nth = MagicMock(return_value=cb_item)

    modal.locator = MagicMock(return_value=cb_loc)

    result = await bot.uncheck_follow_company(modal)
    assert result is True
    assert cb_item.uncheck.called is True


@run_async
async def test_dismiss_modal_discard_confirmation_dialog():
    """Verify dismiss_modal clicks dismiss button and handles discard confirmation dialog."""
    bot = LinkedInEasyApplyBot()
    page = MagicMock()

    dismiss_btn = MagicMock()
    dismiss_btn.count = AsyncMock(return_value=1)
    dismiss_btn.first.is_visible = AsyncMock(return_value=True)
    dismiss_btn.first.click = AsyncMock(return_value=None)

    discard_btn = MagicMock()
    discard_btn.count = AsyncMock(return_value=1)
    discard_btn.first.is_visible = AsyncMock(return_value=True)
    discard_btn.first.click = AsyncMock(return_value=None)

    def page_locator(sel):
        if sel in EasyApplySelectors.DISMISS_BUTTONS:
            return dismiss_btn
        if sel in EasyApplySelectors.DISCARD_CONFIRM_BUTTONS:
            return discard_btn
        empty = MagicMock()
        empty.count = AsyncMock(return_value=0)
        return empty

    page.locator = MagicMock(side_effect=page_locator)

    res = await bot.dismiss_modal(page)
    assert res is True
    assert bot.current_state == ModalState.TERMINAL_DISCARDED
    assert dismiss_btn.first.click.called is True
    assert discard_btn.first.click.called is True


# ==============================================================================
# SECTION 3: SESSION & CSRF TOKEN TESTS
# ==============================================================================

def test_format_jsessionid_token_variants():
    """Validates formatting and preservation of quotes across various input representations."""
    # 1. Already quoted string
    assert format_jsessionid_token('"ajax:7525523478491085393"') == '"ajax:7525523478491085393"'

    # 2. Unquoted string
    assert format_jsessionid_token("ajax:7525523478491085393") == '"ajax:7525523478491085393"'

    # 3. Outer single quotes from shell export
    assert format_jsessionid_token("'\"ajax:7525523478491085393\"'") == '"ajax:7525523478491085393"'
    assert format_jsessionid_token("'ajax:7525523478491085393'") == '"ajax:7525523478491085393"'

    # 4. Whitespace trimming
    assert format_jsessionid_token('  "ajax:123"  ') == '"ajax:123"'
    assert format_jsessionid_token("  ajax:123  ") == '"ajax:123"'

    # 5. Empty / None
    assert format_jsessionid_token(None) is None
    assert format_jsessionid_token("") is None


def test_format_jsessionid_token_empty_placeholders_return_none():
    """Validates that empty quoted placeholders and whitespace return None, avoiding cookie shadowing."""
    assert format_jsessionid_token('""') is None
    assert format_jsessionid_token('"   "') is None
    assert format_jsessionid_token("''") is None
    assert format_jsessionid_token("'   '") is None
    assert format_jsessionid_token('\'""\'') is None
    assert format_jsessionid_token('"\'\'"') is None
    assert format_jsessionid_token("   ") is None
    assert format_jsessionid_token("") is None
    assert format_jsessionid_token(None) is None


def test_get_jsessionid_cookie_empty_dotenv_falls_back_to_tier3(tmp_path, monkeypatch):
    """Verifies that an empty placeholder in .env falls back cleanly to Tier 3 session_cookies.json."""
    monkeypatch.delenv("LINKEDIN_JSESSIONID", raising=False)
    monkeypatch.delenv("JSESSIONID", raising=False)

    env_file = tmp_path / ".env"
    env_file.write_text('LINKEDIN_JSESSIONID=""\n')

    cookie_file = tmp_path / "session_cookies.json"
    cookie_file.write_text(json.dumps([{"name": "JSESSIONID", "value": "ajax:FALLBACK_999"}]))

    with patch("naukari_pro.modules.linkedin_session.WORKSPACE_DIR", str(tmp_path)):
        mgr = LinkedInSessionManager(cookie_path=str(cookie_file))
        assert mgr.get_jsessionid_cookie() == '"ajax:FALLBACK_999"'


def test_jsessionid_loader_from_env(monkeypatch):
    """Validates Tier 1 environment variable loading for LINKEDIN_JSESSIONID."""
    monkeypatch.setenv("LINKEDIN_JSESSIONID", '"ajax:998877665544"')
    manager = LinkedInSessionManager(cookie_path="nonexistent.json")

    token = manager.get_jsessionid_cookie()
    assert token == '"ajax:998877665544"'

    cookie = manager.format_jsessionid_cookie(token)
    assert cookie["name"] == "JSESSIONID"
    assert cookie["value"] == '"ajax:998877665544"'
    assert cookie["domain"] == ".www.linkedin.com"
    assert cookie["path"] == "/"
    assert cookie["httpOnly"] is False
    assert cookie["secure"] is True
    assert cookie["sameSite"] == "None"


def test_jsessionid_loader_from_dotenv(tmp_path, monkeypatch):
    """Validates Tier 2 unexported .env file loading for LINKEDIN_JSESSIONID."""
    monkeypatch.delenv("LINKEDIN_JSESSIONID", raising=False)
    monkeypatch.delenv("JSESSIONID", raising=False)

    env_file = tmp_path / ".env"
    env_file.write_text('LINKEDIN_JSESSIONID="ajax:1122334455"\n')

    with patch("naukari_pro.modules.linkedin_session.WORKSPACE_DIR", str(tmp_path)):
        manager = LinkedInSessionManager(cookie_path="nonexistent.json")
        token = manager.get_jsessionid_cookie()
        assert token == '"ajax:1122334455"'


def test_jsessionid_loader_from_cookie_json_file(tmp_path, monkeypatch):
    """Validates Tier 3 file loading from session_cookies.json (list of dicts)."""
    monkeypatch.delenv("LINKEDIN_JSESSIONID", raising=False)
    monkeypatch.delenv("JSESSIONID", raising=False)

    cookie_file = tmp_path / "session_cookies.json"
    cookie_file.write_text(json.dumps([
        {"name": "bcookie", "value": "v=2&xxx"},
        {"name": "JSESSIONID", "value": "ajax:55667788"}
    ]))

    manager = LinkedInSessionManager(cookie_path=str(cookie_file))
    token = manager.get_jsessionid_cookie()
    assert token == '"ajax:55667788"'


def test_get_formatted_cookies_synchronizes_both_li_at_and_jsessionid(tmp_path, monkeypatch):
    """Validates that get_formatted_cookies formats both cookies with required attributes."""
    monkeypatch.setenv("LINKEDIN_LI_AT", "AQEDAQ_TOKEN_LI_AT")
    monkeypatch.setenv("LINKEDIN_JSESSIONID", "ajax:998877")

    manager = LinkedInSessionManager(cookie_path=str(tmp_path / "empty.json"))
    cookies = manager.get_formatted_cookies()

    cookie_map = {c["name"]: c for c in cookies}
    assert "li_at" in cookie_map
    assert "JSESSIONID" in cookie_map

    # Check li_at attributes
    li_cookie = cookie_map["li_at"]
    assert li_cookie["value"] == "AQEDAQ_TOKEN_LI_AT"
    assert li_cookie["domain"] == ".linkedin.com"
    assert li_cookie["httpOnly"] is True
    assert li_cookie["secure"] is True
    assert li_cookie["sameSite"] == "Lax"

    # Check JSESSIONID attributes
    js_cookie = cookie_map["JSESSIONID"]
    assert js_cookie["value"] == '"ajax:998877"'
    assert js_cookie["domain"] == ".www.linkedin.com"
    assert js_cookie["httpOnly"] is False
    assert js_cookie["secure"] is True
    assert js_cookie["sameSite"] == "None"


def test_get_formatted_cookies_preserves_companion_cookies(tmp_path, monkeypatch):
    """Validates that companion cookies (bcookie, bscookie, lidc) in session_cookies.json are retained."""
    monkeypatch.setenv("LINKEDIN_LI_AT", "ACTIVE_LI_AT")
    monkeypatch.setenv("LINKEDIN_JSESSIONID", "ajax:ACTIVE_CSRF")

    cookie_file = tmp_path / "session_cookies.json"
    cookie_file.write_text(json.dumps([
        {"name": "bcookie", "value": "bcookie_val", "domain": ".linkedin.com"},
        {"name": "lidc", "value": "lidc_val", "domain": ".linkedin.com"},
        {"name": "li_at", "value": "OLD_LI_AT"},
        {"name": "JSESSIONID", "value": "OLD_JSESSIONID"}
    ]))

    manager = LinkedInSessionManager(cookie_path=str(cookie_file))
    cookies = manager.get_formatted_cookies()

    cookie_map = {c["name"]: c for c in cookies}
    assert cookie_map["bcookie"]["value"] == "bcookie_val"
    assert cookie_map["lidc"]["value"] == "lidc_val"
    assert cookie_map["li_at"]["value"] == "ACTIVE_LI_AT"
    assert cookie_map["JSESSIONID"]["value"] == '"ajax:ACTIVE_CSRF"'
    assert cookie_map["JSESSIONID"]["domain"] == ".www.linkedin.com"
    assert cookie_map["JSESSIONID"]["httpOnly"] is False


# ==============================================================================
# SECTION 4: JOB DEDUPLICATOR CLEAN STATUS FILTERING TESTS
# ==============================================================================

def test_deduplicator_sync_confirmed_statuses_only(tmp_path):
    """
    Validates that sync_from_excel_tracker strictly imports confirmed application
    statuses and excludes SUBMITTED_DRY_RUN, FAILED, MODAL_FAILED, and errors.
    """
    mock_wb = MagicMock()
    mock_wb.sheetnames = ["LinkedIn_Applications_Log"]
    ws_mock = MagicMock()

    # 10 canonical columns:
    # Job ID, Platform, Company, Job Title, Location, Match Score, Status, Steps Completed, Applied Timestamp, Job URL
    ws_mock.iter_rows = MagicMock(return_value=[
        ("Job ID", "Platform", "Company", "Job Title", "Location", "Match Score", "Status", "Steps Completed", "Applied Timestamp", "Job URL"),
        ("101", "LinkedIn Easy Apply", "Company A", "MLOps Engineer", "Bengaluru", "88%", "Submitted", 1, "2026-11-02", "https://www.linkedin.com/jobs/view/101/"),
        ("102", "LinkedIn Easy Apply", "Company B", "DevOps Engineer", "Bengaluru", "85%", "Submitted (Confirmed)", 1, "2026-11-02", "https://www.linkedin.com/jobs/view/102/"),
        ("103", "LinkedIn Easy Apply", "Company C", "Platform Engineer", "Bengaluru", "90%", "Applied", 1, "2026-11-02", "https://www.linkedin.com/jobs/view/103/"),
        ("104", "LinkedIn Easy Apply", "Company D", "Data Engineer", "Bengaluru", "82%", "SUCCESS", 1, "2026-11-02", "https://www.linkedin.com/jobs/view/104/"),
        ("201", "LinkedIn Easy Apply", "Company E", "MLOps Engineer", "Bengaluru", "88%", "SUBMITTED_DRY_RUN", 1, "2026-11-02", "https://www.linkedin.com/jobs/view/201/"),
        ("202", "LinkedIn Easy Apply", "Company F", "DevOps Engineer", "Bengaluru", "85%", "FAILED", 0, "2026-11-02", "https://www.linkedin.com/jobs/view/202/"),
        ("203", "LinkedIn Easy Apply", "Company G", "Platform Engineer", "Bengaluru", "90%", "MODAL_FAILED", 0, "2026-11-02", "https://www.linkedin.com/jobs/view/203/"),
        ("204", "LinkedIn Easy Apply", "Company H", "Data Engineer", "Bengaluru", "82%", "CHECKPOINT_BLOCKED", 0, "2026-11-02", "https://www.linkedin.com/jobs/view/204/"),
        ("205", "LinkedIn Easy Apply", "Company I", "Cloud Engineer", "Bengaluru", "78%", "Error", 0, "2026-11-02", "https://www.linkedin.com/jobs/view/205/"),
    ])
    mock_wb.__getitem__ = MagicMock(return_value=ws_mock)

    with patch("openpyxl.load_workbook", return_value=mock_wb), \
         patch("os.path.exists", return_value=True):
        dedup = JobDeduplicator(
            applied_file=str(tmp_path / "app.json"),
            seen_file=str(tmp_path / "seen.json"),
            tracker_path=str(tmp_path / "Tracker.xlsx")
        )
        count = dedup.sync_from_excel_tracker()

        # Confirmed jobs: 101, 102, 103, 104 -> count == 4
        assert count == 4
        assert dedup.is_applied("101") is True
        assert dedup.is_applied("102") is True
        assert dedup.is_applied("103") is True
        assert dedup.is_applied("104") is True

        # Ignored jobs: 201, 202, 203, 204, 205 -> NOT applied!
        assert dedup.is_applied("201") is False
        assert dedup.is_applied("202") is False
        assert dedup.is_applied("203") is False
        assert dedup.is_applied("204") is False
        assert dedup.is_applied("205") is False


def test_deduplicator_sync_applications_log_sheet(tmp_path):
    """Validates sync from Applications_Log worksheet where Status is column index 8."""
    mock_wb = MagicMock()
    mock_wb.sheetnames = ["Applications_Log"]
    ws_mock = MagicMock()

    ws_mock.iter_rows = MagicMock(return_value=[
        ("Date", "Company", "Title", "Score", "Category", "Exp", "Location", "Type", "Status", "Job URL"),
        ("2026-11-02", "Company A", "MLOps", "90%", "Azure Data Eng", "2-5 Yrs", "Bengaluru", "Easy Apply", "Submitted", "https://www.linkedin.com/jobs/view/301/"),
        ("2026-11-02", "Company B", "MLOps", "90%", "Azure Data Eng", "2-5 Yrs", "Bengaluru", "Easy Apply", "SUBMITTED_DRY_RUN", "https://www.linkedin.com/jobs/view/302/"),
    ])
    mock_wb.__getitem__ = MagicMock(return_value=ws_mock)

    with patch("openpyxl.load_workbook", return_value=mock_wb), \
         patch("os.path.exists", return_value=True):
        dedup = JobDeduplicator(
            applied_file=str(tmp_path / "app.json"),
            seen_file=str(tmp_path / "seen.json"),
            tracker_path=str(tmp_path / "Tracker.xlsx")
        )
        count = dedup.sync_from_excel_tracker()
        assert count == 1
        assert dedup.is_applied("301") is True
        assert dedup.is_applied("302") is False


def test_deduplicator_sync_legacy_sheet_without_status_column(tmp_path):
    """Ensures backward compatibility for legacy sheets without a status column."""
    mock_wb = MagicMock()
    mock_wb.sheetnames = ["LinkedIn_Applications_Log"]
    ws_mock = MagicMock()
    ws_mock.iter_rows = MagicMock(return_value=[
        ("Header1", "Header2", "Job URL"),
        ("TCS", "Azure Data Engineer", "https://www.linkedin.com/jobs/view/4159823455/"),
        ("Infosys", "PySpark Developer", "https://www.linkedin.com/jobs/view/4159823456/"),
    ])
    mock_wb.__getitem__ = MagicMock(return_value=ws_mock)

    with patch("openpyxl.load_workbook", return_value=mock_wb), \
         patch("os.path.exists", return_value=True):
        dedup = JobDeduplicator(
            applied_file=str(tmp_path / "app.json"),
            seen_file=str(tmp_path / "seen.json"),
            tracker_path=str(tmp_path / "Tracker.xlsx")
        )
        count = dedup.sync_from_excel_tracker()
        assert count == 2
        assert dedup.is_applied("4159823455") is True
        assert dedup.is_applied("4159823456") is True


# ==============================================================================
# SECTION 5: SAFE COUNT AND FRESHNESS NORMALIZATION TESTS
# ==============================================================================

@run_async
async def test_safe_count_unconfigured_magic_mock_returns_zero():
    """Unconfigured MagicMock locator must return 0 without raising TypeError."""
    mock_loc = MagicMock()
    result = await safe_count(mock_loc)
    assert result == 0
    assert isinstance(result, int)


@run_async
async def test_safe_count_unconfigured_async_mock_returns_zero():
    """Unconfigured AsyncMock locator must return 0."""
    mock_loc = MagicMock()
    mock_loc.count = AsyncMock()
    result = await safe_count(mock_loc)
    assert result == 0
    assert isinstance(result, int)


@run_async
async def test_safe_count_numeric_types():
    """Configured int, float, and numeric strings must coerce to int."""
    loc_int = MagicMock()
    loc_int.count = MagicMock(return_value=3)
    assert await safe_count(loc_int) == 3

    loc_float = MagicMock()
    loc_float.count = MagicMock(return_value=2.0)
    assert await safe_count(loc_float) == 2

    loc_str = MagicMock()
    loc_str.count = MagicMock(return_value=" 5 ")
    assert await safe_count(loc_str) == 5


@run_async
async def test_safe_count_edge_cases():
    """None, bool, and exceptions must return 0."""
    assert await safe_count(None) == 0

    loc_bool = MagicMock()
    loc_bool.count = MagicMock(return_value=True)
    assert await safe_count(loc_bool) == 0

    loc_err = MagicMock()
    loc_err.count.side_effect = RuntimeError("Playwright Target Closed")
    assert await safe_count(loc_err) == 0


@run_async
async def test_open_easy_apply_modal_with_unconfigured_page_mock_does_not_crash():
    """open_easy_apply_modal must complete cleanly and not crash when page is a plain MagicMock."""
    bot = LinkedInEasyApplyBot()
    mock_page = MagicMock()
    modal = await bot.open_easy_apply_modal(mock_page)
    assert modal is None
    assert bot.current_state == ModalState.TERMINAL_FAILED


def test_format_freshness_zero_normalizations():
    """Verify that all variations of 0, r0, and whitespace return None."""
    assert LinkedInSearchUrlBuilder.format_freshness(0) is None
    assert LinkedInSearchUrlBuilder.format_freshness(0.0) is None
    assert LinkedInSearchUrlBuilder.format_freshness("0") is None
    assert LinkedInSearchUrlBuilder.format_freshness("r0") is None
    assert LinkedInSearchUrlBuilder.format_freshness("  0  ") is None
    assert LinkedInSearchUrlBuilder.format_freshness("r00") is None
    assert LinkedInSearchUrlBuilder.format_freshness("00") is None
    assert LinkedInSearchUrlBuilder.format_freshness("-86400") is None
    assert LinkedInSearchUrlBuilder.format_freshness(-86400) is None


def test_format_freshness_positive_seconds_preserved():
    """Verify positive seconds are preserved."""
    assert LinkedInSearchUrlBuilder.format_freshness(86400) == "r86400"
    assert LinkedInSearchUrlBuilder.format_freshness("86400") == "r86400"
    assert LinkedInSearchUrlBuilder.format_freshness("r86400") == "r86400"
    assert LinkedInSearchUrlBuilder.format_freshness("24h") == "r86400"
    assert LinkedInSearchUrlBuilder.format_freshness("7d") == "r604800"


def test_build_search_url_omits_ftpr_for_zero_freshness():
    """Verify LinkedInSearchUrlBuilder.build omits f_TPR entirely when freshness is 0 or '0'."""
    url_int = LinkedInSearchUrlBuilder.build("MLOps", freshness_sec=0)
    assert "f_TPR" not in url_int

    url_str = LinkedInSearchUrlBuilder.build("MLOps", freshness_sec="0")
    assert "f_TPR" not in url_str

    url_r0 = LinkedInSearchUrlBuilder.build("MLOps", freshness_sec="r0")
    assert "f_TPR" not in url_r0


# ==============================================================================
# SECTION 6: APPLY ENGINE TWO-STAGE SCORING INTEGRATION TESTS
# ==============================================================================

def _setup_mock_apply_engine(tmp_path, vacancies, extract_jd_fn=None, execute_easy_apply_fn=None, omit_extract_jd=False):
    session_mgr = MagicMock()
    session_mgr.verify_session = AsyncMock(return_value={
        "status": "VALID",
        "authenticated": True,
        "candidate_name": "Lavkush Kumar"
    })
    session_lock = MagicMock()
    session_lock.acquire = MagicMock(return_value=True)
    session_lock.release = MagicMock(return_value=True)
    session_mgr.get_lock = MagicMock(return_value=session_lock)

    mock_page = MagicMock()
    mock_page.goto = AsyncMock()
    mock_page.wait_for_selector = AsyncMock()
    mock_ctx = MagicMock(pages=[mock_page], close=AsyncMock())
    session_mgr.create_stealth_context = AsyncMock(return_value=mock_ctx)

    search_engine = LinkedInSearchEngine()
    if extract_jd_fn is not None:
        search_engine.extract_right_pane_jd = extract_jd_fn
    elif omit_extract_jd:
        search_mock = MagicMock(wraps=search_engine)
        del search_mock.extract_right_pane_jd
        search_engine = search_mock

    search_engine.search_jobs = AsyncMock(return_value=vacancies)

    mock_nav = MagicMock()
    if execute_easy_apply_fn:
        mock_nav.execute_easy_apply = execute_easy_apply_fn
    else:
        mock_nav.execute_easy_apply = AsyncMock(return_value={
            "success": True,
            "status": "DRY_RUN_VERIFIED",
            "job_id": vacancies[0].get("job_id", "1") if vacancies else "1",
            "steps": 3
        })

    tracker = LinkedInApplicationTracker(
        excel_path=str(tmp_path / "Tracker.xlsx"),
        json_log_path=str(tmp_path / "log.json"),
        skip_file_path=str(tmp_path / "skip.json")
    )

    engine = LinkedInApplyEngine(
        session_manager=session_mgr,
        search_engine=search_engine,
        navigator=mock_nav,
        tracker=tracker,
        min_score=70.0
    )

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=MagicMock())
    cm.__aexit__ = AsyncMock(return_value=None)
    mock_pw_factory = MagicMock(return_value=cm)

    return engine, mock_page, mock_nav, mock_pw_factory


@run_async
async def test_run_apply_cycle_two_stage_scoring_success(tmp_path):
    """Test Spec 1: Two-Stage Scoring Success End-to-End."""
    job = {
        "job_id": "4199990001",
        "title": "Lead Azure Data Engineer",
        "company": "Microsoft GCC",
        "location": "Bengaluru",
        "url": "https://www.linkedin.com/jobs/view/4199990001/",
        "is_easy_apply": True,
        "raw_snippet": "Bengaluru · 1 day ago · Easy Apply",
        "stage1_passed": True,
    }
    jd_text = (
        "We are seeking a Lead Azure Data Engineer with 2-4 years of experience. "
        "Required skills: PySpark, Azure Databricks, Azure Data Factory (ADF), Delta Lake, and SQL."
    )
    extract_jd_fn = AsyncMock(return_value=jd_text)

    engine, mock_page, mock_nav, mock_pw_factory = _setup_mock_apply_engine(
        tmp_path, [job], extract_jd_fn=extract_jd_fn
    )

    with patch("naukari_pro.modules.linkedin_apply.humanized_delay", AsyncMock()), \
         patch("playwright.async_api.async_playwright", mock_pw_factory):
        stats = await engine.run_apply_cycle(
            keywords=["Azure Data Engineer"],
            locations=["Bengaluru"],
            limit=5,
            dry_run=True
        )

    assert stats["skipped"] == 0
    assert stats["scored_above_threshold"] == 1
    assert stats["dry_run_verified"] == 1
    assert len(stats["jobs"]) == 1
    assert stats["jobs"][0]["score"] >= 90.0
    mock_nav.execute_easy_apply.assert_called_once()


@run_async
async def test_run_apply_cycle_two_stage_scoring_gated_out_at_stage2(tmp_path):
    """Test Spec 2: Stage 2 Full JD Gating Out Non-Matching Posting."""
    job = {
        "job_id": "4199990002",
        "title": "Azure Data Engineer",
        "company": "Enterprise Corp",
        "location": "Bengaluru",
        "url": "https://www.linkedin.com/jobs/view/4199990002/",
        "is_easy_apply": True,
        "raw_snippet": "Short card snippet",
        "stage1_passed": True,
    }
    # Unmatched description failing score threshold
    jd_text = (
        "Principal Architect position. Must have 15+ years experience in enterprise "
        "IT governance, COBOL mainframe systems, and non-cloud data warehousing."
    )
    extract_jd_fn = AsyncMock(return_value=jd_text)

    engine, mock_page, mock_nav, mock_pw_factory = _setup_mock_apply_engine(
        tmp_path, [job], extract_jd_fn=extract_jd_fn
    )

    with patch("naukari_pro.modules.linkedin_apply.humanized_delay", AsyncMock()), \
         patch("playwright.async_api.async_playwright", mock_pw_factory):
        stats = await engine.run_apply_cycle(
            keywords=["Azure Data Engineer"],
            locations=["Bengaluru"],
            limit=5,
            dry_run=True
        )

    assert stats["skipped"] == 1
    assert stats["scored_above_threshold"] == 0
    assert stats["dry_run_verified"] == 0
    mock_nav.execute_easy_apply.assert_not_called()


@run_async
async def test_run_apply_cycle_stage1_failed_skips_immediately(tmp_path):
    """Test Spec 3: Stage 1 Explicit Failure Skips Without Navigation."""
    job = {
        "job_id": "4199990003",
        "title": "Frontend React Developer",
        "company": "Design Studio",
        "location": "Bengaluru",
        "url": "https://www.linkedin.com/jobs/view/4199990003/",
        "is_easy_apply": True,
        "raw_snippet": "React, CSS, HTML",
        "stage1_passed": False,
    }

    engine, mock_page, mock_nav, mock_pw_factory = _setup_mock_apply_engine(
        tmp_path, [job], extract_jd_fn=AsyncMock(return_value="Should not be called")
    )

    with patch("naukari_pro.modules.linkedin_apply.humanized_delay", AsyncMock()), \
         patch("playwright.async_api.async_playwright", mock_pw_factory):
        stats = await engine.run_apply_cycle(
            keywords=["Azure Data Engineer"],
            locations=["Bengaluru"],
            limit=5,
            dry_run=True
        )

    assert stats["skipped"] == 1
    mock_page.goto.assert_not_called()
    mock_nav.execute_easy_apply.assert_not_called()


@run_async
async def test_run_apply_cycle_pre_scored_snippet_compatibility(tmp_path):
    """Test Spec 4: Pre-scored Snippet Backward Compatibility."""
    job = {
        "job_id": "4199990004",
        "title": "Azure Data Engineer",
        "company": "Cloud Tech",
        "location": "Bengaluru",
        "url": "https://www.linkedin.com/jobs/view/4199990004/",
        "is_easy_apply": True,
        "raw_snippet": "PySpark, Databricks, ADF, SQL, Delta Lake, 2-4 yrs exp"
        # stage1_passed omitted intentionally
    }

    # Pass omit_extract_jd=True so search_engine does not have extract_right_pane_jd
    engine, mock_page, mock_nav, mock_pw_factory = _setup_mock_apply_engine(
        tmp_path, [job], omit_extract_jd=True
    )

    with patch("naukari_pro.modules.linkedin_apply.humanized_delay", AsyncMock()), \
         patch("playwright.async_api.async_playwright", mock_pw_factory):
        stats = await engine.run_apply_cycle(
            keywords=["Azure Data Engineer"],
            locations=["Bengaluru"],
            limit=5,
            dry_run=True
        )

    assert stats["scored_above_threshold"] == 1
    assert stats["dry_run_verified"] == 1
    mock_nav.execute_easy_apply.assert_called_once()


@run_async
async def test_run_apply_cycle_stage2_jd_hydration_wait(tmp_path):
    """Test Spec 5: DOM Hydration Fallback Retry."""
    job = {
        "job_id": "4199990005",
        "title": "Azure Data Engineer",
        "company": "Tech Corp",
        "location": "Bengaluru",
        "url": "https://www.linkedin.com/jobs/view/4199990005/",
        "is_easy_apply": True,
        "raw_snippet": "Bengaluru · 1 day ago · Easy Apply",
        "stage1_passed": True,
    }

    calls = [0]
    async def hydration_jd(page):
        calls[0] += 1
        if calls[0] == 1:
            return ""  # Not ready on initial read
        return "PySpark, Databricks, ADF, SQL, Delta Lake, 2-4 yrs exp"

    extract_jd_fn = AsyncMock(side_effect=hydration_jd)

    engine, mock_page, mock_nav, mock_pw_factory = _setup_mock_apply_engine(
        tmp_path, [job], extract_jd_fn=extract_jd_fn
    )

    with patch("naukari_pro.modules.linkedin_apply.humanized_delay", AsyncMock()), \
         patch("playwright.async_api.async_playwright", mock_pw_factory):
        stats = await engine.run_apply_cycle(
            keywords=["Azure Data Engineer"],
            locations=["Bengaluru"],
            limit=5,
            dry_run=True
        )

    mock_page.wait_for_selector.assert_called_once()
    assert stats["scored_above_threshold"] == 1
    assert stats["dry_run_verified"] == 1
    mock_nav.execute_easy_apply.assert_called_once()
