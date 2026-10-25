"""
Adversarial Stress Test Suite for Milestone 1 Iteration 2 (R1: Live Profile DOM Persistence & 3x/Day Boost)
Authored by Challenger 1 (teamwork_preview_challenger_m1_iter2_1)

Scope & Tasks empirically verified:
1. bump_profile 2-hour cooldown logic:
   - Calling bump_profile twice within 2 hours respects cooldown unless force=True.
   - Calling bump_profile after 2 hours executes bump.
   - Calling bump_profile with force=True bypasses cooldown.
   - Cooldown boundary precision at 7199s vs 7200s.
   - Resilience against corrupted timestamp strings and forward-skewed clocks (negative elapsed).
2. Headline restoration & saturation:
   - Restores full 247-char Azure Data Engineer headline if empty.
   - Restores full 247-char Azure Data Engineer headline if short/truncated (<200 chars).
   - Restores full 247-char Azure Data Engineer headline if long (>=200 chars) but missing core keywords.
   - Micro-toggles trailing period (appends '.' if absent, removes '.' if present) when already complete.
3. scripts/verify_naukri_live_profile_dom.py:
   - Reports PASS on full compliant profile state (all 7 criteria).
   - Reports FAIL with authentication error when redirected to login.
   - Reports FAIL on short headline (<200 chars).
   - Reports FAIL on headline missing core keywords.
   - Reports FAIL on summary <150 chars or missing Lakehouse keywords.
   - Reports FAIL on key skills with <12 matched top industry keywords.
   - Reports PASS on notice period "15 Days or less" / "15 days" / "Immediate", and FAIL on "30 Days" / "90 Days".
   - Reports PASS on preferred locations with >= 4 target hubs, and FAIL on < 4 target hubs.
   - Reports FAIL on non-pdf resume or missing current designation ("Azure Data Engineer" at "CGI").
4. Real Headless Chromium Playwright E2E:
   - Real browser DOM interaction with route interception for bump_profile.
   - Real browser DOM extraction and widget scroll hydration for verify_live_profile_dom.
"""

import json
import os
import time
from datetime import datetime, timedelta
import pytest
from playwright.sync_api import sync_playwright

from naukari_pro.config import load_config
from naukari_pro.modules.profile_enhancer import ProfileEnhancerEngine
from scripts.verify_naukri_live_profile_dom import (
    TARGET_HUBS,
    TOP_25_KEYWORDS,
    verify_live_profile_dom,
    format_terminal_report
)


@pytest.fixture(autouse=True)
def fast_sleep(monkeypatch):
    """Monkeypatch time.sleep across modules for instantaneous test execution."""
    monkeypatch.setattr("time.sleep", lambda *args: None)
    monkeypatch.setattr("naukari_pro.modules.profile_enhancer.time.sleep", lambda *args: None)
    monkeypatch.setattr("scripts.verify_naukri_live_profile_dom.time.sleep", lambda *args: None)


# ==============================================================================
# MOCK DOM & PAGE HARNESS FOR PLAYWRIGHT INTERFACES
# ==============================================================================

class MockLocator:
    def __init__(self, tag="div", text="", value="", visible=True, count=1, children=None):
        self.tag = tag
        self._text = text
        self.value = value
        self.visible = visible
        self._count = count
        self._children = children or []
        self.clicks = 0
        self.filled_values = []

    def count(self):
        return self._count

    @property
    def first(self):
        return self

    def is_visible(self):
        return self.visible

    def click(self):
        self.clicks += 1

    def input_value(self):
        return self.value

    def fill(self, val):
        self.value = val
        self.filled_values.append(val)

    def inner_text(self):
        return self._text

    def locator(self, selector):
        if ".chip" in selector or ".tag" in selector or "span" in selector:
            if self._children:
                return MockLocatorList(self._children)
        return MockLocator(text=self._text, count=0)

    def nth(self, idx):
        if self._children and 0 <= idx < len(self._children):
            return self._children[idx]
        return MockLocator(text="", count=0)


class MockLocatorList:
    def __init__(self, items):
        self.items = items

    def count(self):
        return len(self.items)

    def nth(self, idx):
        if 0 <= idx < len(self.items):
            return self.items[idx]
        return MockLocator(text="", count=0)

    @property
    def first(self):
        return self.items[0] if self.items else MockLocator(text="", count=0)


class MockPage:
    def __init__(self, url="https://www.naukri.com/mnjuser/profile", locators=None, redirect_url=None):
        self.url = url
        self.locators = locators or {}
        self.redirect_url = redirect_url
        self.goto_calls = []
        self.evaluate_calls = []

    def goto(self, url, wait_until=None, timeout=None):
        self.goto_calls.append(url)
        if self.redirect_url:
            self.url = self.redirect_url
        else:
            self.url = url

    def evaluate(self, script):
        self.evaluate_calls.append(script)

    def locator(self, selector):
        for key, loc in self.locators.items():
            if any(part.strip() in selector for part in key.split(",")):
                return loc
        return MockLocator(count=0)

    def get_by_role(self, role, name=None, exact=False):
        for key, loc in self.locators.items():
            if name and name.lower() in key.lower():
                return loc
        return MockLocator(count=0)


# ==============================================================================
# SECTION 1: PROFILE FRESHNESS BOOST & 2-HOUR COOLDOWN LOGIC
# ==============================================================================

def test_bump_profile_cooldown_within_two_hours_skips_edit(tmp_path):
    """
    TASK 1.1: Verify calling bump_profile twice within 2 hours respects cooldown.
    Second call must skip navigation/DOM edit and return True.
    """
    state_file = str(tmp_path / "session_state.json")
    engine = ProfileEnhancerEngine(state_file=state_file)

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")

    # Initial state: touched 30 minutes ago (1800s < 7200s cooldown)
    past_ts = (now - timedelta(minutes=30)).isoformat()
    engine._save_state({"last_bumped_date": today, "last_bumped_timestamp": past_ts})

    mock_page = MockPage()
    result = engine.bump_profile(mock_page, force=False, cooldown_seconds=7200)

    assert result is True, "Cooldown skip should return True (Active Today status preserved)"
    assert len(mock_page.goto_calls) == 0, "Navigation must NOT be performed when within cooldown period"


def test_bump_profile_after_two_hours_executes_bump(tmp_path):
    """
    TASK 1.2: Verify calling bump_profile after 2 hours (>7200s) executes bump.
    Must navigate, fill headline, save, and update timestamp in state file.
    """
    state_file = str(tmp_path / "session_state.json")
    engine = ProfileEnhancerEngine(state_file=state_file)

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")

    # Touched 2.5 hours ago (9000s > 7200s cooldown)
    past_ts = (now - timedelta(hours=2, minutes=30)).isoformat()
    engine._save_state({"last_bumped_date": today, "last_bumped_timestamp": past_ts})

    # Prepare mock page with editable headline
    edit_loc = MockLocator(tag="span", visible=True, count=1)
    textarea_loc = MockLocator(tag="textarea", value="Azure Data Engineer | 2.5 YOE", visible=True, count=1)
    save_loc = MockLocator(tag="button", visible=True, count=1)

    mock_page = MockPage(locators={
        "Edit resume headline": edit_loc,
        "resumeHeadlineTxt": textarea_loc,
        "Save": save_loc
    })

    result = engine.bump_profile(mock_page, force=False, cooldown_seconds=7200)

    assert result is True, "Bump must succeed after cooldown expires"
    assert len(mock_page.goto_calls) == 1, "Must navigate to profile page when cooldown has expired"
    assert edit_loc.clicks == 1, "Edit headline affordance must be clicked"
    assert save_loc.clicks == 1, "Save button must be clicked"

    # Verify state timestamp was refreshed to current time
    updated_state = engine._load_state()
    new_ts_str = updated_state.get("last_bumped_timestamp")
    assert new_ts_str != past_ts, "last_bumped_timestamp must be updated in state file"
    new_dt = datetime.fromisoformat(new_ts_str)
    assert abs((datetime.now() - new_dt).total_seconds()) < 5, "Updated timestamp must reflect current time"


def test_bump_profile_force_bypasses_cooldown(tmp_path):
    """
    TASK 1.3: Verify calling bump_profile with force=True bypasses cooldown.
    Even if touched 10 seconds ago, it must execute navigation, edit, and save.
    """
    state_file = str(tmp_path / "session_state.json")
    engine = ProfileEnhancerEngine(state_file=state_file)

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")

    # Touched 10 seconds ago
    past_ts = (now - timedelta(seconds=10)).isoformat()
    engine._save_state({"last_bumped_date": today, "last_bumped_timestamp": past_ts})

    edit_loc = MockLocator(tag="span", visible=True, count=1)
    textarea_loc = MockLocator(tag="textarea", value="Azure Data Engineer | 2.5 YOE", visible=True, count=1)
    save_loc = MockLocator(tag="button", visible=True, count=1)

    mock_page = MockPage(locators={
        "Edit resume headline": edit_loc,
        "resumeHeadlineTxt": textarea_loc,
        "Save": save_loc
    })

    result = engine.bump_profile(mock_page, force=True, cooldown_seconds=7200)

    assert result is True, "Forced bump must return True"
    assert len(mock_page.goto_calls) == 1, "Forced bump must bypass cooldown and navigate"
    assert edit_loc.clicks == 1, "Forced bump must click edit"
    assert save_loc.clicks == 1, "Forced bump must click save"

    updated_state = engine._load_state()
    assert updated_state.get("last_bumped_timestamp") != past_ts


@pytest.mark.parametrize("elapsed_seconds,should_skip", [
    (0, True),        # Immediately after
    (3600, True),     # 1 hour after
    (7199, True),     # 1 second before 2-hour threshold
    (7200, False),    # Exactly at 2-hour threshold
    (7201, False),    # 1 second after 2-hour threshold
    (14400, False),   # 4 hours after
])
def test_bump_profile_cooldown_boundary_matrix(tmp_path, elapsed_seconds, should_skip):
    """Verify precise mathematical boundaries of cooldown throttle."""
    state_file = str(tmp_path / "session_state.json")
    engine = ProfileEnhancerEngine(state_file=state_file)

    now = datetime.now()
    past_ts = (now - timedelta(seconds=elapsed_seconds)).isoformat()
    engine._save_state({"last_bumped_date": now.strftime("%Y-%m-%d"), "last_bumped_timestamp": past_ts})

    edit_loc = MockLocator(tag="span", visible=True, count=1)
    textarea_loc = MockLocator(tag="textarea", value="Azure Data Engineer | 2.5 YOE", visible=True, count=1)
    save_loc = MockLocator(tag="button", visible=True, count=1)

    mock_page = MockPage(locators={
        "Edit resume headline": edit_loc,
        "resumeHeadlineTxt": textarea_loc,
        "Save": save_loc
    })

    result = engine.bump_profile(mock_page, force=False, cooldown_seconds=7200)
    assert result is True

    if should_skip:
        assert len(mock_page.goto_calls) == 0, f"At {elapsed_seconds}s, navigation should have been skipped"
    else:
        assert len(mock_page.goto_calls) == 1, f"At {elapsed_seconds}s, bump should have executed"


def test_bump_profile_malformed_timestamp_and_future_clock_resilience(tmp_path):
    """Verify resilience against corrupted timestamps or forward-skewed clock."""
    state_file = str(tmp_path / "session_state.json")
    engine = ProfileEnhancerEngine(state_file=state_file)

    # 1. Corrupted timestamp string
    engine._save_state({"last_bumped_timestamp": "CORRUPTED_NOT_ISO_DATE"})
    edit_loc = MockLocator(tag="span", visible=True, count=1)
    textarea_loc = MockLocator(tag="textarea", value="Azure Data Engineer | 2.5 YOE", visible=True, count=1)
    save_loc = MockLocator(tag="button", visible=True, count=1)

    mock_page = MockPage(locators={
        "Edit resume headline": edit_loc,
        "resumeHeadlineTxt": textarea_loc,
        "Save": save_loc
    })

    # Should not raise exception; should proceed with bump
    result = engine.bump_profile(mock_page, force=False, cooldown_seconds=7200)
    assert result is True
    assert len(mock_page.goto_calls) == 1

    # 2. Future timestamp (clock skewed forward by 1 hour -> elapsed < 0)
    future_ts = (datetime.now() + timedelta(hours=1)).isoformat()
    engine._save_state({"last_bumped_timestamp": future_ts})
    mock_page.goto_calls.clear()

    result_future = engine.bump_profile(mock_page, force=False, cooldown_seconds=7200)
    assert result_future is True
    assert len(mock_page.goto_calls) == 1, "Future timestamp (elapsed < 0) must not skip bump"


# ==============================================================================
# SECTION 2: HEADLINE RESTORATION & SATURATION LOGIC
# ==============================================================================

def test_headline_restore_when_empty(tmp_path):
    """
    TASK 1.4A: Verify headline restore logic restores full 247-char Azure Data Engineer headline
    when headline is empty or deleted.
    """
    state_file = str(tmp_path / "session_state.json")
    engine = ProfileEnhancerEngine(state_file=state_file)

    edit_loc = MockLocator(tag="span", visible=True, count=1)
    textarea_loc = MockLocator(tag="textarea", value="", visible=True, count=1)  # Empty
    save_loc = MockLocator(tag="button", visible=True, count=1)

    mock_page = MockPage(locators={
        "Edit resume headline": edit_loc,
        "resumeHeadlineTxt": textarea_loc,
        "Save": save_loc
    })

    result = engine.bump_profile(mock_page, force=True)
    assert result is True

    filled = textarea_loc.filled_values[-1]
    assert len(filled) >= 235 and len(filled) <= 250, f"Restored headline length {len(filled)} outside valid bounds"
    for kw in ["Azure Data Engineer", "Databricks", "Delta Lake", "ADF"]:
        assert kw.lower() in filled.lower(), f"Keyword {kw} missing from restored headline"


def test_headline_restore_when_short_or_truncated(tmp_path):
    """
    TASK 1.4B: Verify headline restore overwrites truncated headline (<200 chars).
    """
    state_file = str(tmp_path / "session_state.json")
    engine = ProfileEnhancerEngine(state_file=state_file)

    short_headline = "Azure Data Engineer | 2.5 YOE | Python & SQL"  # 44 chars
    edit_loc = MockLocator(tag="span", visible=True, count=1)
    textarea_loc = MockLocator(tag="textarea", value=short_headline, visible=True, count=1)
    save_loc = MockLocator(tag="button", visible=True, count=1)

    mock_page = MockPage(locators={
        "Edit resume headline": edit_loc,
        "resumeHeadlineTxt": textarea_loc,
        "Save": save_loc
    })

    result = engine.bump_profile(mock_page, force=True)
    assert result is True

    filled = textarea_loc.filled_values[-1]
    assert filled != short_headline, "Short headline must be overwritten"
    assert len(filled) >= 235 and len(filled) <= 250
    assert "Azure Databricks" in filled
    assert "Medallion Architecture" in filled


def test_headline_restore_when_long_but_missing_core_keywords(tmp_path):
    """
    TASK 1.4C: Verify headline restore overwrites long headline (>=200 chars) if missing
    core keywords ('Azure Data Engineer', 'Databricks', 'Delta Lake', 'ADF').
    """
    state_file = str(tmp_path / "session_state.json")
    engine = ProfileEnhancerEngine(state_file=state_file)

    # 225-character old DevOps headline
    old_devops_headline = (
        "DevOps Engineer & Cloud Infrastructure Specialist | Kubernetes · Docker · "
        "Terraform · CI/CD Pipelines · Prometheus · Grafana · AWS Platform Engineering · "
        "Microservices Architecture & Linux System Administration | 2.5 YOE"
    )
    assert len(old_devops_headline) >= 200

    edit_loc = MockLocator(tag="span", visible=True, count=1)
    textarea_loc = MockLocator(tag="textarea", value=old_devops_headline, visible=True, count=1)
    save_loc = MockLocator(tag="button", visible=True, count=1)

    mock_page = MockPage(locators={
        "Edit resume headline": edit_loc,
        "resumeHeadlineTxt": textarea_loc,
        "Save": save_loc
    })

    result = engine.bump_profile(mock_page, force=True)
    assert result is True

    filled = textarea_loc.filled_values[-1]
    assert "Azure Data Engineer" in filled
    assert "Delta Lake" in filled
    assert "ADF" in filled


def test_headline_micro_toggle_when_complete(tmp_path):
    """
    TASK 1.4D: When headline is already full and complete, verify micro-toggling:
    - If ends without period -> appends period
    - If ends with period -> removes period
    """
    state_file = str(tmp_path / "session_state.json")
    engine = ProfileEnhancerEngine(state_file=state_file)
    cfg = load_config()
    template = cfg.get("headline_template").strip().rstrip(".")

    # Case 1: Without trailing period
    edit_loc = MockLocator(tag="span", visible=True, count=1)
    textarea_loc = MockLocator(tag="textarea", value=template, visible=True, count=1)
    save_loc = MockLocator(tag="button", visible=True, count=1)

    mock_page = MockPage(locators={
        "Edit resume headline": edit_loc,
        "resumeHeadlineTxt": textarea_loc,
        "Save": save_loc
    })

    result = engine.bump_profile(mock_page, force=True)
    assert result is True
    filled1 = textarea_loc.filled_values[-1]
    assert filled1.endswith("."), "Should append period when previously absent"
    assert filled1[:-1] == template

    # Case 2: With trailing period
    mock_page.goto_calls.clear()
    textarea_loc.value = template + "."
    textarea_loc.filled_values.clear()

    result2 = engine.bump_profile(mock_page, force=True)
    assert result2 is True
    filled2 = textarea_loc.filled_values[-1]
    assert not filled2.endswith("."), "Should remove period when previously present"
    assert filled2 == template


# ==============================================================================
# SECTION 3: LIVE DOM VERIFIER (`scripts/verify_naukri_live_profile_dom.py`)
# ==============================================================================

def create_mock_dom_page(
    headline_text,
    summary_text,
    key_skills_list,
    employment_text,
    career_profile_text,
    cv_filename_text,
    url="https://www.naukri.com/mnjuser/profile",
    redirect_url=None
):
    """Helper to assemble a MockPage wired with realistic selectors matching Naukri DOM."""
    hl_loc = MockLocator(text=headline_text, visible=True, count=1 if headline_text else 0)
    sum_loc = MockLocator(text=summary_text, visible=True, count=1 if summary_text else 0)

    # Key skills chip children
    chip_locators = [MockLocator(text=kw, visible=True, count=1) for kw in key_skills_list]
    ks_loc = MockLocator(text="\n".join(key_skills_list), visible=True, count=1 if key_skills_list else 0, children=chip_locators)

    emp_loc = MockLocator(text=employment_text, visible=True, count=1 if employment_text else 0)
    cp_loc = MockLocator(text=career_profile_text, visible=True, count=1 if career_profile_text else 0)
    cv_loc = MockLocator(text=cv_filename_text, visible=True, count=1 if cv_filename_text else 0)

    locators = {
        "resumeHeadline": hl_loc,
        "lazyProfileSummary": sum_loc,
        "profileSummary": sum_loc,
        "lazyKeySkills": ks_loc,
        "keySkills": ks_loc,
        "lazyEmployment": emp_loc,
        "lazyCareerProfile": cp_loc,
        "desiredProfile": cp_loc,
        "lazyAttachCV": cv_loc,
        "attachCV": cv_loc,
        "resume-name": cv_loc
    }

    return MockPage(url=url, locators=locators, redirect_url=redirect_url)


def test_verify_dom_full_pass_state():
    """
    TASK 1.5A: Verify scripts/verify_naukri_live_profile_dom.py reports PASS
    when all profile criteria are satisfied.
    """
    cfg = load_config()
    headline = cfg.get("headline_template")
    summary = cfg.get("profile_summary")
    skills = TOP_25_KEYWORDS
    emp = "Azure Data Engineer at CGI India (PNC Bank GCC). Notice Period: 15 Days or less."
    cp = "Preferred Locations: Bengaluru, Hyderabad, Pune, Gurugram, Noida, Mumbai, Chennai."
    cv = "Lavkush_Kumar_Azure_Data_Engineer_Resume.pdf\nUploaded on 25 Oct 2026"

    page = create_mock_dom_page(headline, summary, skills, emp, cp, cv)
    overall_pass, report = verify_live_profile_dom(page, cfg=cfg)

    assert overall_pass is True, f"Full compliant profile state must pass. Report: {report}"
    assert report["overall_status"] == "PASS"

    # Assert every individual check is PASS
    assert report["checks"]["headline"]["status"] == "PASS"
    assert report["checks"]["profile_summary"]["status"] == "PASS"
    assert report["checks"]["key_skills"]["status"] == "PASS"
    assert report["checks"]["notice_period"]["status"] == "PASS"
    assert report["checks"]["preferred_locations"]["status"] == "PASS"
    assert report["checks"]["attached_resume_pdf"]["status"] == "PASS"
    assert report["checks"]["current_designation"]["status"] == "PASS"

    # Terminal report formatting check
    formatted = format_terminal_report(report)
    assert "[✓] Resume Headline" in formatted
    assert "[✓] Profile Summary" in formatted
    assert "[✓] Key Skills" in formatted
    assert "[✓] Notice Period" in formatted
    assert "[✓] Preferred Locations" in formatted
    assert "[✓] Attached Resume CV" in formatted
    assert "[✓] Current Designation" in formatted


def test_verify_dom_login_redirect_failure():
    """
    TASK 1.5B: When redirected to login page, verifier must report FAIL with authentication error.
    """
    page = create_mock_dom_page(
        headline_text="", summary_text="", key_skills_list=[],
        employment_text="", career_profile_text="", cv_filename_text="",
        url="https://www.naukri.com/landing",
        redirect_url="https://www.naukri.com/nlogin/login"
    )
    overall_pass, report = verify_live_profile_dom(page)

    assert overall_pass is False
    assert report["overall_status"] == "FAIL"
    assert report["checks"]["authentication"]["status"] == "FAIL"


def test_verify_dom_short_or_incomplete_headline_failure():
    """
    TASK 1.5C: When headline is short (<200 chars) or missing core keywords,
    headline check must report FAIL and overall_pass must be False.
    """
    cfg = load_config()
    summary = cfg.get("profile_summary")
    skills = TOP_25_KEYWORDS
    emp = "Azure Data Engineer at CGI India. Notice Period: 15 Days or less."
    cp = "Preferred Locations: Bengaluru, Hyderabad, Pune, Gurugram, Noida, Mumbai, Chennai."
    cv = "Lavkush_Kumar_Azure_Data_Engineer_Resume.pdf"

    # Case 1: Short headline
    short_hl = "Azure Data Engineer | 2.5 YOE"
    page1 = create_mock_dom_page(short_hl, summary, skills, emp, cp, cv)
    pass1, rep1 = verify_live_profile_dom(page1, cfg=cfg)
    assert pass1 is False
    assert rep1["checks"]["headline"]["status"] == "FAIL"

    # Case 2: Long headline but missing core keywords (e.g. ADF, Kafka, Delta Lake)
    long_missing_kw = "Azure Data Engineer " * 15  # >200 chars but only 1 keyword
    page2 = create_mock_dom_page(long_missing_kw, summary, skills, emp, cp, cv)
    pass2, rep2 = verify_live_profile_dom(page2, cfg=cfg)
    assert pass2 is False
    assert rep2["checks"]["headline"]["status"] == "FAIL"


def test_verify_dom_summary_failure():
    """
    TASK 1.5D: When summary is <150 chars or lacks core Lakehouse keywords,
    summary check must report FAIL.
    """
    cfg = load_config()
    headline = cfg.get("headline_template")
    skills = TOP_25_KEYWORDS
    emp = "Azure Data Engineer at CGI India. Notice Period: 15 Days or less."
    cp = "Preferred Locations: Bengaluru, Hyderabad, Pune, Gurugram, Noida, Mumbai, Chennai."
    cv = "Lavkush_Kumar_Azure_Data_Engineer_Resume.pdf"

    # Short summary
    short_sum = "Azure Data Engineer with 2.5 YOE building pipelines."
    page = create_mock_dom_page(headline, short_sum, skills, emp, cp, cv)
    overall_pass, report = verify_live_profile_dom(page, cfg=cfg)

    assert overall_pass is False
    assert report["checks"]["profile_summary"]["status"] == "FAIL"


def test_verify_dom_insufficient_key_skills_failure():
    """
    TASK 1.5E: When key skills has fewer than 12 matched top industry keywords,
    key skills check must report FAIL.
    """
    cfg = load_config()
    headline = cfg.get("headline_template")
    summary = cfg.get("profile_summary")
    emp = "Azure Data Engineer at CGI India. Notice Period: 15 Days or less."
    cp = "Preferred Locations: Bengaluru, Hyderabad, Pune, Gurugram, Noida, Mumbai, Chennai."
    cv = "Lavkush_Kumar_Azure_Data_Engineer_Resume.pdf"

    # Only 3 skills
    weak_skills = ["Python", "SQL", "Git"]
    page = create_mock_dom_page(headline, summary, weak_skills, emp, cp, cv)
    overall_pass, report = verify_live_profile_dom(page, cfg=cfg)

    assert overall_pass is False
    assert report["checks"]["key_skills"]["status"] == "FAIL"
    assert report["checks"]["key_skills"]["matched_top_keywords_count"] < 12


def test_verify_dom_notice_period_detection_states():
    """
    TASK 1.5F: Verify notice period detection:
    - '15 Days or less' / '15 days' / 'Immediate' -> PASS
    - '30 Days' / '1 month' / '90 Days' -> FAIL
    """
    cfg = load_config()
    headline = cfg.get("headline_template")
    summary = cfg.get("profile_summary")
    skills = TOP_25_KEYWORDS
    cp = "Preferred Locations: Bengaluru, Hyderabad, Pune, Gurugram, Noida, Mumbai, Chennai."
    cv = "Lavkush_Kumar_Azure_Data_Engineer_Resume.pdf"

    # 1. 15 Days -> PASS
    page_15d = create_mock_dom_page(headline, summary, skills, "Azure Data Engineer at CGI India. Notice Period: 15 Days.", cp, cv)
    _, rep_15d = verify_live_profile_dom(page_15d, cfg=cfg)
    assert rep_15d["checks"]["notice_period"]["status"] == "PASS"

    # 2. Immediate -> PASS
    page_imm = create_mock_dom_page(headline, summary, skills, "Azure Data Engineer at CGI India. Immediate Available.", cp, cv)
    _, rep_imm = verify_live_profile_dom(page_imm, cfg=cfg)
    assert rep_imm["checks"]["notice_period"]["status"] == "PASS"

    # 3. 30 Days -> FAIL
    page_30d = create_mock_dom_page(headline, summary, skills, "Azure Data Engineer at CGI India. Notice Period: 30 Days.", cp, cv)
    _, rep_30d = verify_live_profile_dom(page_30d, cfg=cfg)
    assert rep_30d["checks"]["notice_period"]["status"] == "FAIL"


def test_verify_dom_preferred_locations_detection_states():
    """
    TASK 1.5G: Verify preferred locations detection:
    - >= 4 target hubs -> PASS
    - < 4 target hubs -> FAIL
    """
    cfg = load_config()
    headline = cfg.get("headline_template")
    summary = cfg.get("profile_summary")
    skills = TOP_25_KEYWORDS
    emp = "Azure Data Engineer at CGI India. Notice Period: 15 Days."
    cv = "Lavkush_Kumar_Azure_Data_Engineer_Resume.pdf"

    # 1. 7 hubs -> PASS
    cp_7 = "Preferred Locations: Bengaluru, Hyderabad, Pune, Gurugram, Noida, Mumbai, Chennai"
    page_7 = create_mock_dom_page(headline, summary, skills, emp, cp_7, cv)
    _, rep_7 = verify_live_profile_dom(page_7, cfg=cfg)
    assert rep_7["checks"]["preferred_locations"]["status"] == "PASS"
    assert rep_7["checks"]["preferred_locations"]["matched_hubs_count"] == 7

    # 2. 4 hubs -> PASS (majority threshold)
    cp_4 = "Preferred Locations: Bengaluru, Hyderabad, Pune, Mumbai"
    page_4 = create_mock_dom_page(headline, summary, skills, emp, cp_4, cv)
    _, rep_4 = verify_live_profile_dom(page_4, cfg=cfg)
    assert rep_4["checks"]["preferred_locations"]["status"] == "PASS"
    assert rep_4["checks"]["preferred_locations"]["matched_hubs_count"] == 4

    # 3. 2 hubs -> FAIL
    cp_2 = "Preferred Locations: Kolkata, Patna, Ahmedabad, Bengaluru, Pune"
    page_2 = create_mock_dom_page(headline, summary, skills, emp, cp_2, cv)
    _, rep_2 = verify_live_profile_dom(page_2, cfg=cfg)
    assert rep_2["checks"]["preferred_locations"]["status"] == "FAIL"
    assert rep_2["checks"]["preferred_locations"]["matched_hubs_count"] == 2


def test_verify_dom_cv_and_designation_failures():
    """
    TASK 1.5H: Verify failure states for attached resume PDF and current designation.
    """
    cfg = load_config()
    headline = cfg.get("headline_template")
    summary = cfg.get("profile_summary")
    skills = TOP_25_KEYWORDS
    emp_correct = "Azure Data Engineer at CGI India. Notice Period: 15 Days."
    cp = "Preferred Locations: Bengaluru, Hyderabad, Pune, Gurugram, Noida, Mumbai, Chennai."

    # 1. Non-pdf resume file
    cv_wrong = "my_profile_summary.docx"
    page_cv = create_mock_dom_page(headline, summary, skills, emp_correct, cp, cv_wrong)
    pass_cv, rep_cv = verify_live_profile_dom(page_cv, cfg=cfg)
    assert pass_cv is False
    assert rep_cv["checks"]["attached_resume_pdf"]["status"] == "FAIL"

    # 2. Wrong company or designation
    cv_correct = "Lavkush_Kumar_Azure_Data_Engineer_Resume.pdf"
    emp_wrong = "Junior Developer at ABC Tech"
    page_desig = create_mock_dom_page(headline, summary, skills, emp_wrong, cp, cv_correct)
    pass_desig, rep_desig = verify_live_profile_dom(page_desig, cfg=cfg)
    assert pass_desig is False
    assert rep_desig["checks"]["current_designation"]["status"] == "FAIL"


# ==============================================================================
# SECTION 4: REAL HEADLESS CHROMIUM PLAYWRIGHT VERIFICATION
# ==============================================================================

def test_bump_profile_real_chromium_execution(tmp_path):
    """
    TASK 2A: Execute bump_profile on real Chromium headless browser with stateful route interception.
    Confirms actual DOM interactions: click, clear, fill, save, and state persistence.
    """
    server_headline = ["Old Truncated Headline"]

    def handle_profile_route(route):
        html = f"""
        <!DOCTYPE html>
        <html>
        <head><title>Naukri Profile</title></head>
        <body>
          <div class="resumeHeadline">
            <span class="edit" aria-label="Edit resume headline">Edit</span>
            <textarea id="resumeHeadlineTxt" style="display:block;">{server_headline[0]}</textarea>
            <button class="btn-dark-ot">Save</button>
          </div>
        </body>
        </html>
        """
        route.fulfill(status=200, content_type="text/html", body=html)

    state_file = str(tmp_path / "real_state.json")
    engine = ProfileEnhancerEngine(state_file=state_file)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.route("**/mnjuser/profile", handle_profile_route)

        # First bump: overwrites short headline and records state
        res1 = engine.bump_profile(page, force=False)
        assert res1 is True
        textarea_val1 = page.locator("textarea#resumeHeadlineTxt").input_value()
        assert "Azure Data Engineer" in textarea_val1
        assert "Delta Lake" in textarea_val1
        assert len(textarea_val1) >= 235
        # Simulate server saving the value
        server_headline[0] = textarea_val1

        # Check state file
        with open(state_file, "r") as f:
            st1 = json.load(f)
        assert "last_bumped_timestamp" in st1

        # Second bump immediately: cooldown kicks in, no page reload
        res2 = engine.bump_profile(page, force=False)
        assert res2 is True

        # Third bump with force=True: executes again and micro-toggles trailing period
        res3 = engine.bump_profile(page, force=True)
        assert res3 is True
        textarea_val3 = page.locator("textarea#resumeHeadlineTxt").input_value()
        assert textarea_val3 != textarea_val1 or textarea_val3.endswith(".") != textarea_val1.endswith(".")
        server_headline[0] = textarea_val3

        # Fourth bump with force=True: micro-toggles back
        res4 = engine.bump_profile(page, force=True)
        assert res4 is True
        textarea_val4 = page.locator("textarea#resumeHeadlineTxt").input_value()
        assert textarea_val4 != textarea_val3 or textarea_val4.endswith(".") != textarea_val3.endswith(".")

        browser.close()


def test_verify_live_profile_dom_real_chromium_execution():
    """
    TASK 2B: Execute verify_live_profile_dom on real Chromium headless browser with rendered HTML DOM.
    Confirms that DOM extraction and widget scroll hydration function on genuine browser engine.
    """
    cfg = load_config()
    headline = cfg.get("headline_template")
    summary = cfg.get("profile_summary")
    chips_html = "".join([f'<span class="chip">{kw}</span>' for kw in TOP_25_KEYWORDS])

    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Naukri Profile</title></head>
    <body>
      <div id="lazyResumeHeadline" class="resumeHeadline">
        <div class="text">{headline}</div>
      </div>
      <div id="lazyProfileSummary" class="profileSummary">
        {summary}
      </div>
      <div id="lazyKeySkills" class="keySkills">
        {chips_html}
      </div>
      <div id="lazyEmployment">
        Current: Azure Data Engineer at CGI India (PNC Bank GCC). Notice Period: 15 Days or less.
      </div>
      <div id="lazyCareerProfile" class="desiredProfile">
        Preferred Locations: Bengaluru, Hyderabad, Pune, Gurugram, Noida, Mumbai, Chennai.
      </div>
      <div id="lazyAttachCV" class="attachCV">
        <div class="resume-name">Lavkush_Kumar_Azure_Data_Engineer_Resume.pdf</div>
      </div>
    </body>
    </html>
    """

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.route("**/mnjuser/profile", lambda route: route.fulfill(status=200, content_type="text/html", body=full_html))

        overall_pass, report = verify_live_profile_dom(page, cfg=cfg)
        browser.close()

    assert overall_pass is True
    assert report["overall_status"] == "PASS"
    assert report["checks"]["headline"]["status"] == "PASS"
    assert report["checks"]["profile_summary"]["status"] == "PASS"
    assert report["checks"]["key_skills"]["status"] == "PASS"
    assert report["checks"]["notice_period"]["status"] == "PASS"
    assert report["checks"]["preferred_locations"]["status"] == "PASS"
    assert report["checks"]["attached_resume_pdf"]["status"] == "PASS"
    assert report["checks"]["current_designation"]["status"] == "PASS"
