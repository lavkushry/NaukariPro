"""
Adversarial Stress Test Suite for Milestone 1 Iteration 2 (R1: Live Profile DOM Persistence & 3x/Day Boost)
Authored by Challenger 2 (teamwork_preview_challenger_m1_iter2_2)

Validates:
1. Master config exactness: 15-day notice period and all 7 Tier-1 tech hubs without deviations.
2. Runtime config overlay (.env vs config.json notice period consistency).
3. scripts/sync_naukri_live_profile.py selector construction, fallbacks, and graceful degradation on missing DOM elements.
4. scripts/verify_naukri_live_profile_dom.py inspection accuracy across authentic, degraded, and unauthenticated states.
5. ProfileEnhancerEngine cooldown throttle (7200s) and full 247-char headline overwrite recovery.
6. Autonomous runner wiring (agy_schedule_runner.sh and pro_autopilot.py).
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, call
import pytest

from naukari_pro.config import load_config
from naukari_pro.modules.profile_enhancer import ProfileEnhancerEngine
from scripts.sync_naukri_live_profile import (
    DEFAULT_TOP_25_KEY_SKILLS,
    DEFAULT_PREFERRED_LOCATIONS,
    DEFAULT_IT_SKILLS,
    sync_resume_headline,
    sync_notice_period,
    sync_preferred_locations,
    sync_key_skills,
    sync_it_skills,
    sync_full_naukri_profile
)
from scripts.verify_naukri_live_profile_dom import (
    TARGET_HUBS,
    TOP_25_KEYWORDS,
    verify_live_profile_dom,
    format_terminal_report
)


@pytest.fixture(autouse=True)
def fast_sleep():
    """Mock time.sleep across all tests for near-instant execution."""
    with patch("time.sleep", return_value=None):
        yield


def _make_mock_locator(count=0, visible=False, text="", value=""):
    """Creates a deterministic Playwright locator mock."""
    loc = MagicMock()
    loc.count.return_value = count
    loc.is_visible.return_value = visible
    loc.inner_text.return_value = text
    loc.input_value.return_value = value
    loc.first = loc
    loc.last = loc
    loc.nth.return_value = loc
    return loc


# ==============================================================================
# SECTION 1: MASTER CONFIG INTEGRITY & EXACT CALIBRATION (R1)
# ==============================================================================

def test_raw_config_json_notice_period_and_seven_hubs():
    """Verify raw naukri_system/config.json contains 15 days notice and all 7 tech hubs."""
    config_path = "naukri_system/config.json"
    assert os.path.exists(config_path)
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    cand = cfg.get("candidate", {})
    assert cand.get("notice_period_days") == 15, "Raw config.json notice_period_days must be 15"
    assert cand.get("notice_period") == "15 Days or less"

    expected_7_hubs = ["Bengaluru", "Hyderabad", "Pune", "Gurugram", "Noida", "Mumbai", "Chennai"]
    actual_hubs = cand.get("preferred_locations", [])

    assert len(actual_hubs) == 7, f"Expected exactly 7 preferred hubs, found {len(actual_hubs)}: {actual_hubs}"
    assert set(actual_hubs) == set(expected_7_hubs), f"Mismatch in preferred hubs: {set(actual_hubs) ^ set(expected_7_hubs)}"
    assert len(actual_hubs) == len(set(actual_hubs)), "Duplicate entries in preferred_locations"

    # Search settings locations
    search_locs = [s.lower() for s in cfg.get("search_settings", {}).get("locations", [])]
    for hub in expected_7_hubs:
        assert hub.lower() in search_locs, f"Search location list missing hub '{hub}'"

    # Common answers
    answers = cfg.get("answers_to_common_questions", {})
    assert "15" in answers.get("notice_period", "")
    assert answers.get("notice_period_detail") == "15 Days or less"
    for hub in expected_7_hubs:
        assert hub in answers.get("preferred_locations", "")


def test_env_notice_period_drift():
    """
    CRITICAL CHALLENGE: Check if .env NOTICE_PERIOD environment variable
    conflicts with or overrides config.json 15-day notice period in load_config().
    """
    env_path = ".env"
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            env_content = f.read()
        for line in env_content.splitlines():
            line = line.strip()
            if line.startswith("NOTICE_PERIOD="):
                val = line.split("=", 1)[1].strip()
                assert val == "15", (
                    f"CRITICAL DISCREPANCY: .env defines NOTICE_PERIOD={val} instead of 15! "
                    "When load_config() executes, it reads .env and overwrites candidate['notice_period_days'] "
                    "and answers_to_common_questions['notice_period'] back to 30 days!"
                )


def test_metadata_constants_exact_counts_and_attributes():
    """Verify script default constants match exact specification constraints."""
    # 1. Top 25 Key Skills
    assert len(DEFAULT_TOP_25_KEY_SKILLS) == 25
    assert len(set(DEFAULT_TOP_25_KEY_SKILLS)) == 25, "Duplicate skills in DEFAULT_TOP_25_KEY_SKILLS"
    for core in ["Azure Databricks", "PySpark", "Delta Lake", "Azure Data Factory (ADF)", "Apache Kafka"]:
        assert core in DEFAULT_TOP_25_KEY_SKILLS, f"Core skill '{core}' missing from top 25"

    # 2. 7 Preferred Locations
    assert len(DEFAULT_PREFERRED_LOCATIONS) == 7
    assert set(DEFAULT_PREFERRED_LOCATIONS) == set(["Bengaluru", "Hyderabad", "Pune", "Gurugram", "Noida", "Mumbai", "Chennai"])

    # 3. 13 Detailed IT Skills
    assert len(DEFAULT_IT_SKILLS) == 13
    assert len(set(item["skill"] for item in DEFAULT_IT_SKILLS)) == 13, "Duplicate IT skills"
    for item in DEFAULT_IT_SKILLS:
        assert all(k in item for k in ["skill", "version", "last_used", "exp_years", "exp_months"])
        assert item["last_used"] == "2026"
        assert item["exp_years"] >= 1


# ==============================================================================
# SECTION 2: SELECTOR TARGET CONSTRUCTION & GRACEFUL DEGRADATION
# ==============================================================================

def test_sync_resume_headline_missing_elements_graceful():
    """Verify sync_resume_headline handles missing elements and exceptions gracefully."""
    mock_page = MagicMock()
    mock_page.url = "https://www.naukri.com/mnjuser/profile"

    # Scenario A: Edit button count is 0
    empty_loc = _make_mock_locator(count=0, visible=False)
    mock_page.locator.return_value = empty_loc

    result = sync_resume_headline(mock_page, target_headline="Test Headline")
    assert result is False, "Must return False when edit button is not found"

    # Scenario B: Exception during locator interaction
    mock_page.locator.side_effect = Exception("DOM connection reset")
    result = sync_resume_headline(mock_page, target_headline="Test Headline")
    assert result is False, "Must catch exception and return False without crashing"


def test_sync_resume_headline_success_path():
    """Verify sync_resume_headline correctly executes textarea fill and save."""
    mock_page = MagicMock()
    mock_page.url = "https://www.naukri.com/mnjuser/profile"

    mock_edit_btn = _make_mock_locator(count=1, visible=True)
    mock_textarea = _make_mock_locator(count=1, visible=True, value="Old short headline")
    mock_save_btn = _make_mock_locator(count=1, visible=True)

    def locator_side_effect(selector):
        if "headline" in selector.lower() and ("span" in selector or ".edit" in selector):
            return mock_edit_btn
        elif "textarea" in selector:
            return mock_textarea
        elif "save" in selector.lower():
            return mock_save_btn
        return _make_mock_locator(count=0, visible=False)

    mock_page.locator.side_effect = locator_side_effect

    target_hl = "Azure Data Engineer | Azure Databricks · PySpark · Delta Lake · ADF"
    result = sync_resume_headline(mock_page, target_headline=target_hl)

    assert result is True
    mock_edit_btn.click.assert_called()
    mock_textarea.fill.assert_called_with(target_hl)
    mock_save_btn.click.assert_called()


def test_sync_notice_period_missing_elements_graceful():
    """Verify sync_notice_period falls through strategies without throwing exceptions."""
    mock_page = MagicMock()
    mock_page.url = "https://www.naukri.com/mnjuser/profile"

    empty_loc = _make_mock_locator(count=0, visible=False)
    mock_page.locator.return_value = empty_loc

    res = sync_notice_period(mock_page, target_notice="15 Days or less")
    assert res is True, "sync_notice_period must exit cleanly without unhandled errors"


def test_sync_notice_period_strategy_a_and_b_selectors():
    """Verify sync_notice_period checks employment dropdown and career profile availability chips."""
    mock_page = MagicMock()
    mock_page.url = "https://www.naukri.com/mnjuser/profile"

    mock_emp_sec = _make_mock_locator(count=1, visible=True)
    mock_edit_btn = _make_mock_locator(count=1, visible=True)
    mock_select = _make_mock_locator(count=1, visible=True)
    mock_select.locator.return_value.all_inner_texts.return_value = ["30 Days", "15 Days or less", "Immediate"]
    mock_save_btn = _make_mock_locator(count=1, visible=True)

    def emp_locator_side_effect(selector):
        if "edit" in selector:
            return mock_edit_btn
        elif "noticeperiod" in selector.lower() and "select" in selector.lower():
            return mock_select
        elif "#submitemployment" in selector.lower():
            return mock_save_btn
        return _make_mock_locator(count=0, visible=False)

    mock_emp_sec.locator.side_effect = emp_locator_side_effect

    def page_locator_side_effect(selector):
        if "#lazyEmployment" in selector:
            return mock_emp_sec
        elif "#noticePeriod" in selector and "select" in selector:
            return mock_select
        elif "#submitEmployment" in selector:
            return mock_save_btn
        return _make_mock_locator(count=0, visible=False)

    mock_page.locator.side_effect = page_locator_side_effect

    res = sync_notice_period(mock_page, target_notice="15 Days or less")
    assert res is True
    mock_select.select_option.assert_called_with(label="15 Days or less")
    mock_save_btn.click.assert_called()


def test_sync_preferred_locations_missing_section_graceful():
    """Verify sync_preferred_locations returns False cleanly if #lazyCareerProfile is missing."""
    mock_page = MagicMock()
    mock_page.url = "https://www.naukri.com/mnjuser/profile"

    empty_loc = _make_mock_locator(count=0, visible=False)
    mock_page.locator.return_value = empty_loc

    res = sync_preferred_locations(mock_page)
    assert res is False, "Must return False when Career Profile section is missing"


def test_sync_preferred_locations_iteration_and_submission():
    """Verify sync_preferred_locations enters all 7 target hubs and saves."""
    mock_page = MagicMock()
    mock_page.url = "https://www.naukri.com/mnjuser/profile"

    mock_cp_sec = _make_mock_locator(count=1, visible=True)
    mock_edit_btn = _make_mock_locator(count=1, visible=True)
    mock_loc_input = _make_mock_locator(count=1, visible=True)
    mock_save_btn = _make_mock_locator(count=1, visible=True)

    typed_hubs = []
    def loc_input_type(text, **kwargs):
        typed_hubs.append(text)
    mock_loc_input.type.side_effect = loc_input_type

    def page_locator_side_effect(selector):
        if "#lazyCareerProfile" in selector:
            return mock_cp_sec
        elif "locationsugg" in selector.lower() or "preferredlocation" in selector.lower():
            return mock_loc_input
        elif "submitdesiredprofile" in selector.lower() or "submitcareerprofile" in selector.lower():
            return mock_save_btn
        elif "chip" in selector.lower():
            return _make_mock_locator(count=0, visible=False)
        elif "li:has-text" in selector.lower():
            return _make_mock_locator(count=1, visible=True)
        return _make_mock_locator(count=0, visible=False)

    mock_cp_sec.locator.side_effect = lambda sel: mock_edit_btn if "edit" in sel else _make_mock_locator(count=0)
    mock_page.locator.side_effect = page_locator_side_effect

    res = sync_preferred_locations(mock_page, locations=DEFAULT_PREFERRED_LOCATIONS)
    assert res is True
    assert set(typed_hubs) == set(DEFAULT_PREFERRED_LOCATIONS)
    assert len(typed_hubs) == 7
    mock_save_btn.click.assert_called()


def test_sync_key_skills_missing_section_graceful():
    """Verify sync_key_skills returns False if #lazyKeySkills is missing."""
    mock_page = MagicMock()
    mock_page.url = "https://www.naukri.com/mnjuser/profile"

    empty_loc = _make_mock_locator(count=0, visible=False)
    mock_page.locator.return_value = empty_loc

    res = sync_key_skills(mock_page)
    assert res is False, "Must return False when Key Skills section is missing"


def test_sync_it_skills_missing_section_graceful():
    """Verify sync_it_skills returns False cleanly if #lazyItSkills is missing."""
    mock_page = MagicMock()
    mock_page.url = "https://www.naukri.com/mnjuser/profile"

    empty_loc = _make_mock_locator(count=0, visible=False)
    mock_page.locator.return_value = empty_loc

    res = sync_it_skills(mock_page)
    assert res is False, "Must return False when IT Skills section is missing"


# ==============================================================================
# SECTION 3: LIVE PROFILE DOM VERIFICATION LOGIC STRESS-TESTS
# ==============================================================================

def test_verify_naukri_live_profile_dom_redirect_to_login():
    """Verify verify_live_profile_dom detects session expiry / redirect to login."""
    mock_page = MagicMock()
    mock_page.url = "https://www.naukri.com/nlogin/login"

    passed, report = verify_live_profile_dom(mock_page)
    assert passed is False
    assert report["overall_status"] == "FAIL"
    assert "authentication" in report["checks"]
    assert report["checks"]["authentication"]["status"] == "FAIL"


def test_verify_naukri_live_profile_dom_full_pass():
    """Verify verify_live_profile_dom produces PASS report when all DOM fields match."""
    mock_page = MagicMock()
    mock_page.url = "https://www.naukri.com/mnjuser/profile"

    mock_hl = _make_mock_locator(
        count=1,
        visible=True,
        text="Azure Data Engineer | Azure Databricks · PySpark · Delta Lake · Azure Data Factory (ADF) · SQL · Apache Kafka · Terraform · Medallion Architecture | Certified AZ-900 · Databricks Associate | 2.5 YOE Cloud Data Platforms & CI/CD"
    )
    mock_sum = _make_mock_locator(
        count=1,
        visible=True,
        text="Azure Data Engineer with 2.5 YOE specializing in Azure Databricks, Delta Lake, and ADF within enterprise Medallion Lakehouses. Automated CI/CD release cycles and Terraform provisioning."
    )
    mock_ks = _make_mock_locator(count=1, visible=True)
    mock_chips = _make_mock_locator(count=25, visible=True)
    mock_chips.nth.side_effect = lambda i: _make_mock_locator(count=1, visible=True, text=TOP_25_KEYWORDS[i])
    mock_ks.locator.return_value = mock_chips

    mock_emp = _make_mock_locator(count=1, visible=True, text="Current: Azure Data Engineer at CGI India\nNotice Period: 15 Days or less")
    mock_cp = _make_mock_locator(count=1, visible=True, text="Preferred Locations: Bengaluru, Hyderabad, Pune, Gurugram, Noida, Mumbai, Chennai\nAvailability to Join: 15 Days or less")
    mock_cv = _make_mock_locator(count=1, visible=True, text="Lavkush_Kumar_Azure_Data_Engineer_Resume.pdf\nUploaded today")

    def page_locator_side_effect(selector):
        if "headline" in selector.lower():
            return mock_hl
        elif "profilesummary" in selector.lower():
            return mock_sum
        elif "keyskills" in selector.lower():
            return mock_ks
        elif "#lazyemployment" in selector.lower():
            return mock_emp
        elif "#lazycareerprofile" in selector.lower() or "desiredprofile" in selector.lower():
            return mock_cp
        elif "cv" in selector.lower() or "resume" in selector.lower():
            return mock_cv
        return _make_mock_locator(count=0, visible=False)

    mock_page.locator.side_effect = page_locator_side_effect

    passed, report = verify_live_profile_dom(mock_page)
    assert passed is True
    assert report["overall_status"] == "PASS"
    assert report["checks"]["headline"]["status"] == "PASS"
    assert report["checks"]["profile_summary"]["status"] == "PASS"
    assert report["checks"]["key_skills"]["status"] == "PASS"
    assert report["checks"]["notice_period"]["status"] == "PASS"
    assert report["checks"]["preferred_locations"]["status"] == "PASS"
    assert report["checks"]["attached_resume_pdf"]["status"] == "PASS"
    assert report["checks"]["current_designation"]["status"] == "PASS"

    terminal_output = format_terminal_report(report)
    assert "NAUKRI LIVE PROFILE DOM VERIFICATION REPORT" in terminal_output
    assert "Overall Status: PASS" in terminal_output


def test_verify_naukri_live_profile_dom_detects_short_headline():
    """Verify verify_live_profile_dom fails headline check if text is truncated."""
    mock_page = MagicMock()
    mock_page.url = "https://www.naukri.com/mnjuser/profile"

    short_hl = _make_mock_locator(count=1, visible=True, text="Azure Data Engineer")

    def page_locator_side_effect(selector):
        if "headline" in selector.lower():
            return short_hl
        return _make_mock_locator(count=0, visible=False)

    mock_page.locator.side_effect = page_locator_side_effect

    passed, report = verify_live_profile_dom(mock_page)
    assert passed is False
    assert report["checks"]["headline"]["status"] == "FAIL"
    assert report["checks"]["headline"]["length"] == len("Azure Data Engineer")


def test_verify_naukri_live_profile_dom_overall_pass_must_require_notice_period_and_locations():
    """
    CRITICAL CHALLENGE: Verify verify_live_profile_dom includes notice_period and preferred_locations
    in overall_pass evaluation rather than returning PASS when notice period or locations fail.
    """
    mock_page = MagicMock()
    mock_page.url = "https://www.naukri.com/mnjuser/profile"

    # All headline, summary, key skills, cv, designation PASS
    mock_hl = _make_mock_locator(count=1, visible=True, text="Azure Data Engineer | Azure Databricks · PySpark · Delta Lake · Azure Data Factory (ADF) · SQL · Apache Kafka · Terraform · Medallion Architecture | Certified AZ-900 · Databricks Associate | 2.5 YOE Cloud Data Platforms & CI/CD")
    mock_sum = _make_mock_locator(count=1, visible=True, text="Azure Data Engineer with 2.5 YOE specializing in Azure Databricks, Delta Lake, and ADF within enterprise Medallion Lakehouses. Automated CI/CD release cycles and Terraform provisioning.")
    mock_ks = _make_mock_locator(count=1, visible=True)
    mock_chips = _make_mock_locator(count=25, visible=True)
    mock_chips.nth.side_effect = lambda i: _make_mock_locator(count=1, visible=True, text=TOP_25_KEYWORDS[i])
    mock_ks.locator.return_value = mock_chips
    mock_cv = _make_mock_locator(count=1, visible=True, text="Lavkush_Kumar_Azure_Data_Engineer_Resume.pdf")

    # BUT Notice period is 90 Days (FAIL!)
    mock_emp = _make_mock_locator(count=1, visible=True, text="Current: Azure Data Engineer at CGI India\nNotice Period: 90 Days")
    # AND Preferred locations is EMPTY (FAIL!)
    mock_cp = _make_mock_locator(count=1, visible=True, text="Preferred Locations: None\nAvailability to Join: 90 Days")

    def page_locator_side_effect(selector):
        if "headline" in selector.lower():
            return mock_hl
        elif "profilesummary" in selector.lower():
            return mock_sum
        elif "keyskills" in selector.lower():
            return mock_ks
        elif "#lazyemployment" in selector.lower():
            return mock_emp
        elif "#lazycareerprofile" in selector.lower() or "desiredprofile" in selector.lower():
            return mock_cp
        elif "cv" in selector.lower():
            return mock_cv
        return _make_mock_locator(count=0, visible=False)

    mock_page.locator.side_effect = page_locator_side_effect

    passed, report = verify_live_profile_dom(mock_page)

    assert report["checks"]["notice_period"]["status"] == "FAIL"
    assert report["checks"]["preferred_locations"]["status"] == "FAIL"

    # If critical_passes omits np_pass and loc_pass, passed will be True (defect!)
    assert passed is False, (
        "DEFECT DETECTED: verify_live_profile_dom returned passed=True despite Notice Period and "
        "Preferred Locations failing! critical_passes list in scripts/verify_naukri_live_profile_dom.py "
        "must include np_pass and loc_pass."
    )


# ==============================================================================
# SECTION 4: PROFILE ENHANCER COOLDOWN & HEADLINE RESTORATION (3X/DAY BOOST)
# ==============================================================================

def test_profile_enhancer_cooldown_throttle(tmp_path):
    """Verify bump_profile skips redundant edits if touched < 7200s ago unless force=True."""
    engine = ProfileEnhancerEngine()
    session_file = tmp_path / "test_session_state.json"
    engine.session_state_file = str(session_file)

    now = datetime.now()
    recent_ts = (now - timedelta(minutes=30)).isoformat()
    engine._save_state({
        "last_bumped_date": now.strftime("%Y-%m-%d"),
        "last_bumped_timestamp": recent_ts
    })

    mock_page = MagicMock()

    # 1. Without force -> skips edit and returns True
    res = engine.bump_profile(mock_page, force=False, cooldown_seconds=7200)
    assert res is True
    mock_page.goto.assert_not_called(), "Should not navigate when inside cooldown window"

    # 2. With force=True -> ignores cooldown and navigates
    mock_page.url = "https://www.naukri.com/mnjuser/profile"
    mock_edit_btn = _make_mock_locator(count=0, visible=False)
    mock_page.locator.return_value = mock_edit_btn

    res_forced = engine.bump_profile(mock_page, force=True, cooldown_seconds=7200)
    mock_page.goto.assert_called_with("https://www.naukri.com/mnjuser/profile", wait_until="domcontentloaded", timeout=30000)


def test_profile_enhancer_headline_overwrite_on_truncation(tmp_path):
    """Verify bump_profile restores full 247-char headline if current headline is truncated."""
    engine = ProfileEnhancerEngine()
    session_file = tmp_path / "test_state.json"
    engine.session_state_file = str(session_file)
    engine._save_state({})

    mock_page = MagicMock()
    mock_page.url = "https://www.naukri.com/mnjuser/profile"

    mock_edit_btn = _make_mock_locator(count=1, visible=True)
    mock_textarea = _make_mock_locator(count=1, visible=True, value="Short Data Engineer")
    mock_save_btn = _make_mock_locator(count=1, visible=True)

    def loc_side_effect(selector):
        if "headline" in selector.lower() and ("span" in selector or ".edit" in selector):
            return mock_edit_btn
        elif "textarea" in selector:
            return mock_textarea
        elif "save" in selector.lower() or "button" in selector:
            return mock_save_btn
        return _make_mock_locator(count=0, visible=False)

    mock_page.locator.side_effect = loc_side_effect

    res = engine.bump_profile(mock_page, force=True)
    assert res is True

    filled_text = mock_textarea.fill.call_args[0][0]
    assert len(filled_text) >= 200, f"Expected full headline >= 200 chars, got: '{filled_text}'"
    assert "Azure Data Engineer" in filled_text
    assert "Databricks" in filled_text


# ==============================================================================
# SECTION 5: AUTONOMOUS RUNNER & CRON WRAPPER VERIFICATION
# ==============================================================================

def test_agy_schedule_runner_force_flag_present():
    """Verify agy_schedule_runner.sh specifies --force to guarantee 3x/day profile freshness."""
    script_path = "agy_schedule_runner.sh"
    assert os.path.exists(script_path)
    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "--force" in content, "agy_schedule_runner.sh must include --force flag"
    assert "./naukariPro pro --headless --limit 15 --force" in content
    assert "15 days or less notice" in content.lower()
    for hub in ["Bengaluru", "Hyderabad", "Pune", "Gurugram", "Noida", "Mumbai", "Chennai"]:
        assert hub in content, f"Hub '{hub}' missing from agy_schedule_runner prompt"
