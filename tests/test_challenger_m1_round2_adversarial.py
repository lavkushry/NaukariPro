"""
Adversarial Stress Test Suite for Milestone 1 Round 2 (Empirical Challenge)
Authored by Challenger 1 (teamwork_preview_challenger_m1_round2_1)

Empirical Challenge Objectives:
1. scripts/verify_naukri_live_profile_dom.py mock DOM evaluation:
   - When notice period fails -> overall status MUST evaluate to FAIL and overall_pass MUST be False.
   - When preferred locations fail -> overall status MUST evaluate to FAIL and overall_pass MUST be False.
   - When all fields pass -> overall status MUST evaluate to PASS and overall_pass MUST be True.
   - Boundary tests (< 4 vs >= 4 hubs, alias handling, missing sections, locator exceptions).
   - Combinatorial failure isolation across all 7 critical checks.
2. scripts/sync_naukri_live_profile.py:sync_resume_headline:
   - When headline matches target -> returns True without unnecessary DOM write/save.
   - When headline matches target with trailing dot differences -> returns True without write/save.
   - When headline does not match -> edits, fills target, saves, and returns True.
   - Fallback button selector verification (by-role Save button).
   - Graceful handling of missing edit button, hidden textarea, missing save button, and DOM exceptions.
"""

import sys
import os
from unittest.mock import MagicMock, patch, call
import pytest

from scripts.verify_naukri_live_profile_dom import (
    verify_live_profile_dom,
    format_terminal_report,
    TARGET_HUBS,
    TOP_25_KEYWORDS
)
from scripts.sync_naukri_live_profile import sync_resume_headline


@pytest.fixture(autouse=True)
def fast_sleep(monkeypatch):
    """Bypass all time.sleep calls for instant test execution."""
    monkeypatch.setattr("time.sleep", lambda *args: None)
    monkeypatch.setattr("scripts.verify_naukri_live_profile_dom.time.sleep", lambda *args: None)
    monkeypatch.setattr("scripts.sync_naukri_live_profile.time.sleep", lambda *args: None)


def _make_mock_locator(count=1, visible=True, text="", value=""):
    """Helper creating a standard mock Playwright Locator."""
    loc = MagicMock()
    loc.count.return_value = count
    loc.is_visible.return_value = visible
    loc.inner_text.return_value = text
    loc.input_value.return_value = value
    loc.first = loc
    loc.last = loc
    loc.nth.return_value = loc
    return loc


def _build_compliant_dom_locators(
    headline_text=None,
    summary_text=None,
    key_skills_list=None,
    notice_period_text=None,
    preferred_locations_text=None,
    cv_text=None,
    employment_text=None,
):
    """
    Constructs a baseline set of compliant DOM element mocks.
    Any field can be selectively overridden to test failure isolation.
    """
    valid_headline = (
        "Azure Data Engineer | Azure Databricks · PySpark · Delta Lake · "
        "Azure Data Factory (ADF) · SQL · Apache Kafka · Terraform · Medallion Architecture | "
        "Certified AZ-900 · Databricks Associate | 2.5 YOE Cloud Data Platforms & CI/CD"
    )
    valid_summary = (
        "Azure Data Engineer with 2.5 YOE specializing in Azure Databricks, Delta Lake, and ADF "
        "within enterprise Medallion Lakehouses. Automated CI/CD release cycles and Terraform provisioning."
    )
    valid_skills = TOP_25_KEYWORDS
    valid_notice = "Current: Azure Data Engineer at CGI India\nNotice Period: 15 Days or less"
    valid_locations = "Preferred Locations: Bengaluru, Hyderabad, Pune, Gurugram, Noida, Mumbai, Chennai\nAvailability to Join: 15 Days or less"
    valid_cv = "Lavkush_Kumar_Azure_Data_Engineer_Resume.pdf\nUploaded today"
    valid_employment = "Current: Azure Data Engineer at CGI India\nNotice Period: 15 Days or less"

    hl_mock = _make_mock_locator(text=headline_text if headline_text is not None else valid_headline)
    sum_mock = _make_mock_locator(text=summary_text if summary_text is not None else valid_summary)

    # Key skills mock
    skills = key_skills_list if key_skills_list is not None else valid_skills
    ks_mock = _make_mock_locator(text=" ".join(skills))
    chips_mock = _make_mock_locator(count=len(skills))
    chips_mock.nth.side_effect = lambda i: _make_mock_locator(text=skills[i])
    ks_mock.locator.return_value = chips_mock

    emp_mock = _make_mock_locator(text=employment_text if employment_text is not None else valid_employment)
    cp_mock = _make_mock_locator(text=preferred_locations_text if preferred_locations_text is not None else valid_locations)
    cv_mock = _make_mock_locator(text=cv_text if cv_text is not None else valid_cv)

    return {
        "headline": hl_mock,
        "summary": sum_mock,
        "key_skills": ks_mock,
        "employment": emp_mock,
        "career_profile": cp_mock,
        "cv": cv_mock,
    }


def _wire_mock_page(dom_map, url="https://www.naukri.com/mnjuser/profile"):
    """Creates a mock Playwright Page dispatching selectors to dom_map elements."""
    page = MagicMock()
    page.url = url

    def locator_router(selector):
        sel_lower = selector.lower()
        if "headline" in sel_lower:
            return dom_map["headline"]
        elif "profilesummary" in sel_lower:
            return dom_map["summary"]
        elif "keyskills" in sel_lower:
            return dom_map["key_skills"]
        elif "#lazyemployment" in sel_lower:
            return dom_map["employment"]
        elif "#lazycareerprofile" in sel_lower or "desiredprofile" in sel_lower:
            return dom_map["career_profile"]
        elif "cv" in sel_lower or "resume" in sel_lower:
            return dom_map["cv"]
        return _make_mock_locator(count=0, visible=False)

    page.locator.side_effect = locator_router
    return page


# ==============================================================================
# SECTION 1: VERIFY_NAUKRI_LIVE_PROFILE_DOM — NOTICE PERIOD FAILURE ISOLATION
# ==============================================================================

@pytest.mark.parametrize("failing_notice_text,scenario_name", [
    ("Current: Azure Data Engineer at CGI India\nNotice Period: 30 Days", "30_days_notice"),
    ("Current: Azure Data Engineer at CGI India\nNotice Period: 60 Days", "60_days_notice"),
    ("Current: Azure Data Engineer at CGI India\nNotice Period: 90 Days", "90_days_notice"),
    ("Current: Azure Data Engineer at CGI India\nNotice Period: 1 Month", "1_month_notice"),
    ("Current: Azure Data Engineer at CGI India\nNotice Period: 2 Months", "2_months_notice"),
    ("Current: Azure Data Engineer at CGI India\nNotice Period: 3 Months", "3_months_notice"),
    ("Current: Azure Data Engineer at CGI India\nNotice Period: Not Serving", "not_serving"),
    ("Current: Azure Data Engineer at CGI India", "missing_notice_period_text"),
    ("Current: Azure Data Engineer at CGI India\nNotice Period: Unknown", "unknown_notice_period"),
])
def test_verify_dom_notice_period_failure_produces_overall_fail(failing_notice_text, scenario_name):
    """
    CRITICAL EMPIRICAL CHALLENGE 1.1:
    When notice period fails while ALL other fields pass:
    - notice_period check MUST be FAIL.
    - overall_status MUST be FAIL.
    - overall_pass MUST be False.
    """
    # Career profile also set without 15 days
    cp_text = "Preferred Locations: Bengaluru, Hyderabad, Pune, Gurugram, Noida, Mumbai, Chennai\nAvailability: 30 Days"
    dom = _build_compliant_dom_locators(
        employment_text=failing_notice_text,
        preferred_locations_text=cp_text
    )
    page = _wire_mock_page(dom)

    overall_pass, report = verify_live_profile_dom(page)

    # Assertions
    assert overall_pass is False, f"Failed for scenario: {scenario_name}. overall_pass must be False!"
    assert report["overall_status"] == "FAIL", f"Failed for scenario: {scenario_name}. overall_status must be FAIL!"
    assert report["checks"]["notice_period"]["status"] == "FAIL"

    # Verify that the OTHER fields indeed passed (isolating notice period as the sole failure cause)
    assert report["checks"]["headline"]["status"] == "PASS"
    assert report["checks"]["profile_summary"]["status"] == "PASS"
    assert report["checks"]["key_skills"]["status"] == "PASS"
    assert report["checks"]["preferred_locations"]["status"] == "PASS"
    assert report["checks"]["attached_resume_pdf"]["status"] == "PASS"
    assert report["checks"]["current_designation"]["status"] == "PASS"


def test_verify_dom_notice_period_exception_produces_overall_fail():
    """Verify that an exception when reading notice period elements results in FAIL."""
    dom = _build_compliant_dom_locators()
    # Mock employment locator raising an exception on inner_text
    dom["employment"].inner_text.side_effect = Exception("Stale DOM element reference")
    dom["career_profile"].inner_text.side_effect = Exception("Stale DOM element reference")
    page = _wire_mock_page(dom)

    overall_pass, report = verify_live_profile_dom(page)

    assert overall_pass is False
    assert report["overall_status"] == "FAIL"
    assert report["checks"]["notice_period"]["status"] == "FAIL"


# ==============================================================================
# SECTION 2: VERIFY_NAUKRI_LIVE_PROFILE_DOM — PREFERRED LOCATIONS FAILURE ISOLATION
# ==============================================================================

@pytest.mark.parametrize("hubs_text,expected_found_count,scenario_name", [
    ("Preferred Locations: None", 0, "zero_hubs"),
    ("Preferred Locations: Kolkata, Ahmedabad, Jaipur", 0, "non_target_hubs_only"),
    ("Preferred Locations: Bengaluru", 1, "one_hub_bengaluru"),
    ("Preferred Locations: Bengaluru, Hyderabad", 2, "two_hubs_blr_hyd"),
    ("Preferred Locations: Bengaluru, Hyderabad, Pune", 3, "three_hubs_boundary_fail"),
    ("Preferred Locations: Gurgaon, Noida, Mumbai", 3, "three_hubs_with_alias_boundary_fail"),
    ("", 0, "empty_career_profile"),
])
def test_verify_dom_preferred_locations_failure_produces_overall_fail(hubs_text, expected_found_count, scenario_name):
    """
    CRITICAL EMPIRICAL CHALLENGE 1.2:
    When preferred locations fails (< 4 target hubs) while ALL other fields pass:
    - preferred_locations check MUST be FAIL.
    - overall_status MUST be FAIL.
    - overall_pass MUST be False.
    """
    dom = _build_compliant_dom_locators(preferred_locations_text=hubs_text)
    page = _wire_mock_page(dom)

    overall_pass, report = verify_live_profile_dom(page)

    assert overall_pass is False, f"Failed for scenario: {scenario_name}. overall_pass must be False!"
    assert report["overall_status"] == "FAIL", f"Failed for scenario: {scenario_name}. overall_status must be FAIL!"
    assert report["checks"]["preferred_locations"]["status"] == "FAIL"
    assert report["checks"]["preferred_locations"]["matched_hubs_count"] == expected_found_count

    # Verify that the OTHER fields indeed passed (isolating preferred locations as the sole failure cause)
    assert report["checks"]["headline"]["status"] == "PASS"
    assert report["checks"]["profile_summary"]["status"] == "PASS"
    assert report["checks"]["key_skills"]["status"] == "PASS"
    assert report["checks"]["notice_period"]["status"] == "PASS"
    assert report["checks"]["attached_resume_pdf"]["status"] == "PASS"
    assert report["checks"]["current_designation"]["status"] == "PASS"


def test_verify_dom_preferred_locations_missing_section_produces_overall_fail():
    """Verify that a missing career profile section (count=0) produces FAIL."""
    dom = _build_compliant_dom_locators()
    dom["career_profile"] = _make_mock_locator(count=0, visible=False)
    page = _wire_mock_page(dom)

    overall_pass, report = verify_live_profile_dom(page)

    assert overall_pass is False
    assert report["overall_status"] == "FAIL"
    assert report["checks"]["preferred_locations"]["status"] == "FAIL"
    assert report["checks"]["preferred_locations"]["matched_hubs_count"] == 0


# ==============================================================================
# SECTION 3: VERIFY_NAUKRI_LIVE_PROFILE_DOM — ALL FIELDS PASS & BOUNDARY MATRICES
# ==============================================================================

@pytest.mark.parametrize("hubs_text,expected_count,scenario_name", [
    ("Preferred Locations: Bengaluru, Hyderabad, Pune, Gurugram", 4, "boundary_pass_4_hubs"),
    ("Preferred Locations: Bangalore, Gurgaon, Hyderabad, Pune", 4, "boundary_pass_4_hubs_with_aliases"),
    ("Preferred Locations: Bengaluru, Hyderabad, Pune, Gurugram, Noida", 5, "pass_5_hubs"),
    ("Preferred Locations: Bengaluru, Hyderabad, Pune, Gurugram, Noida, Mumbai", 6, "pass_6_hubs"),
    ("Preferred Locations: Bengaluru, Hyderabad, Pune, Gurugram, Noida, Mumbai, Chennai", 7, "pass_all_7_hubs"),
    ("Preferred Locations: Bangalore, Hyderabad, Pune, Gurgaon, Noida, Mumbai, Chennai", 7, "pass_all_7_hubs_with_aliases"),
])
def test_verify_dom_all_fields_pass_evaluates_to_overall_pass(hubs_text, expected_count, scenario_name):
    """
    CRITICAL EMPIRICAL CHALLENGE 1.3:
    When all fields pass (including notice period 15 days and >= 4 target hubs):
    - overall_status MUST evaluate to PASS.
    - overall_pass MUST be True.
    """
    dom = _build_compliant_dom_locators(preferred_locations_text=hubs_text)
    page = _wire_mock_page(dom)

    overall_pass, report = verify_live_profile_dom(page)

    assert overall_pass is True, f"Failed for scenario: {scenario_name}. overall_pass must be True!"
    assert report["overall_status"] == "PASS", f"Failed for scenario: {scenario_name}. overall_status must be PASS!"
    assert report["checks"]["preferred_locations"]["status"] == "PASS"
    assert report["checks"]["preferred_locations"]["matched_hubs_count"] == expected_count
    assert report["checks"]["notice_period"]["status"] == "PASS"
    assert report["checks"]["headline"]["status"] == "PASS"
    assert report["checks"]["profile_summary"]["status"] == "PASS"
    assert report["checks"]["key_skills"]["status"] == "PASS"
    assert report["checks"]["attached_resume_pdf"]["status"] == "PASS"
    assert report["checks"]["current_designation"]["status"] == "PASS"


@pytest.mark.parametrize("notice_string", [
    "Notice Period: 15 Days or less",
    "Notice Period: 15 days",
    "Notice Period: 15 day",
    "Notice Period: Immediate Joining",
    "Notice Period: Immediate",
])
def test_verify_dom_notice_period_acceptable_variations_pass(notice_string):
    """Verify all valid 15-day / immediate phrasing variants evaluate to PASS."""
    dom = _build_compliant_dom_locators(employment_text=f"Current: Azure Data Engineer at CGI India\n{notice_string}")
    page = _wire_mock_page(dom)

    overall_pass, report = verify_live_profile_dom(page)

    assert overall_pass is True
    assert report["overall_status"] == "PASS"
    assert report["checks"]["notice_period"]["status"] == "PASS"


def test_verify_dom_combined_failures_evaluated_accurately():
    """Verify that both notice period AND preferred locations failing registers both in checks and overall FAIL."""
    dom = _build_compliant_dom_locators(
        employment_text="Current: Azure Data Engineer at CGI India\nNotice Period: 90 Days",
        preferred_locations_text="Preferred Locations: None"
    )
    page = _wire_mock_page(dom)

    overall_pass, report = verify_live_profile_dom(page)

    assert overall_pass is False
    assert report["overall_status"] == "FAIL"
    assert report["checks"]["notice_period"]["status"] == "FAIL"
    assert report["checks"]["preferred_locations"]["status"] == "FAIL"


# ==============================================================================
# SECTION 4: SYNC_RESUME_HEADLINE — MATCHED VS UNMATCHED EMPIRICAL TESTS
# ==============================================================================

def test_sync_resume_headline_when_headline_already_matches_returns_true():
    """
    CRITICAL EMPIRICAL CHALLENGE 2.1:
    When live headline already matches target headline:
    - Function MUST return True.
    - Function MUST NOT call textarea.fill() or save_btn.click() (idempotency, no wasted writes).
    """
    target_hl = (
        "Azure Data Engineer | Azure Databricks · PySpark · Delta Lake · "
        "Azure Data Factory (ADF) · SQL · Apache Kafka · Terraform · Medallion Architecture | "
        "Certified AZ-900 · Databricks Associate | 2.5 YOE Cloud Data Platforms & CI/CD"
    )

    mock_page = MagicMock()
    mock_page.url = "https://www.naukri.com/mnjuser/profile"

    mock_edit_btn = _make_mock_locator(count=1, visible=True)
    mock_textarea = _make_mock_locator(count=1, visible=True, value=target_hl)
    mock_save_btn = _make_mock_locator(count=1, visible=True)

    def locator_side_effect(selector):
        sel_lower = selector.lower()
        if "headline" in sel_lower and ("span" in sel_lower or ".edit" in sel_lower):
            return mock_edit_btn
        elif "textarea" in sel_lower:
            return mock_textarea
        elif "save" in sel_lower:
            return mock_save_btn
        return _make_mock_locator(count=0, visible=False)

    mock_page.locator.side_effect = locator_side_effect

    result = sync_resume_headline(mock_page, target_headline=target_hl)

    # Verification: must return True
    assert result is True, "sync_resume_headline MUST return True when headline already matches!"

    # Verification: edit was opened to inspect, but NO overwrite or save occurred
    mock_edit_btn.click.assert_called_once()
    mock_textarea.fill.assert_not_called()
    mock_save_btn.click.assert_not_called()


@pytest.mark.parametrize("current_in_dom,target_requested", [
    (
        "Azure Data Engineer | Azure Databricks · PySpark · Delta Lake · ADF · SQL",
        "Azure Data Engineer | Azure Databricks · PySpark · Delta Lake · ADF · SQL."
    ),
    (
        "Azure Data Engineer | Azure Databricks · PySpark · Delta Lake · ADF · SQL.",
        "Azure Data Engineer | Azure Databricks · PySpark · Delta Lake · ADF · SQL"
    ),
    (
        "Azure Data Engineer | Azure Databricks · PySpark · Delta Lake · ADF · SQL...",
        "Azure Data Engineer | Azure Databricks · PySpark · Delta Lake · ADF · SQL"
    )
])
def test_sync_resume_headline_trailing_period_equivalence_returns_true(current_in_dom, target_requested):
    """
    CRITICAL EMPIRICAL CHALLENGE 2.1b:
    Trailing dot differences (curr_val.rstrip('.') == hl.rstrip('.')) MUST evaluate as matching:
    - Returns True.
    - Does NOT trigger textarea.fill() or save_btn.click().
    """
    mock_page = MagicMock()
    mock_page.url = "https://www.naukri.com/mnjuser/profile"

    mock_edit_btn = _make_mock_locator(count=1, visible=True)
    mock_textarea = _make_mock_locator(count=1, visible=True, value=current_in_dom)
    mock_save_btn = _make_mock_locator(count=1, visible=True)

    def locator_side_effect(selector):
        sel_lower = selector.lower()
        if "headline" in sel_lower and ("span" in sel_lower or ".edit" in sel_lower):
            return mock_edit_btn
        elif "textarea" in sel_lower:
            return mock_textarea
        elif "save" in sel_lower:
            return mock_save_btn
        return _make_mock_locator(count=0, visible=False)

    mock_page.locator.side_effect = locator_side_effect

    result = sync_resume_headline(mock_page, target_headline=target_requested)

    assert result is True
    mock_textarea.fill.assert_not_called()
    mock_save_btn.click.assert_not_called()


def test_sync_resume_headline_when_headline_does_not_match_edits_and_saves():
    """
    CRITICAL EMPIRICAL CHALLENGE 2.2:
    When live headline does NOT match target headline:
    - Textarea MUST be clicked and cleared with fill("").
    - Textarea MUST be filled with target headline.
    - Save button MUST be clicked.
    - Function MUST return True upon save.
    """
    target_hl = (
        "Azure Data Engineer | Azure Databricks · PySpark · Delta Lake · "
        "Azure Data Factory (ADF) · SQL · Apache Kafka · Terraform · Medallion Architecture | "
        "Certified AZ-900 · Databricks Associate | 2.5 YOE Cloud Data Platforms & CI/CD"
    )
    old_hl = "Senior Software Engineer with Java and Spring experience."

    mock_page = MagicMock()
    mock_page.url = "https://www.naukri.com/mnjuser/profile"

    mock_edit_btn = _make_mock_locator(count=1, visible=True)
    mock_textarea = _make_mock_locator(count=1, visible=True, value=old_hl)
    mock_save_btn = _make_mock_locator(count=1, visible=True)

    def locator_side_effect(selector):
        sel_lower = selector.lower()
        if "headline" in sel_lower and ("span" in sel_lower or ".edit" in sel_lower):
            return mock_edit_btn
        elif "textarea" in sel_lower:
            return mock_textarea
        elif "save" in sel_lower:
            return mock_save_btn
        return _make_mock_locator(count=0, visible=False)

    mock_page.locator.side_effect = locator_side_effect

    result = sync_resume_headline(mock_page, target_headline=target_hl)

    # Verification: must return True
    assert result is True, "sync_resume_headline MUST return True upon successful edit and save!"

    # Verification: textarea was filled with empty string then target headline
    mock_textarea.fill.assert_has_calls([call(""), call(target_hl)])

    # Verification: save button was clicked
    mock_save_btn.click.assert_called_once()


def test_sync_resume_headline_fallback_save_button_resolution():
    """
    Verify fallback locator resolution when class-based Save button is absent:
    Uses page.get_by_role("button", name="Save", exact=True).
    """
    target_hl = "Azure Data Engineer | Azure Databricks · PySpark · Delta Lake"
    old_hl = "Outdated Profile Headline"

    mock_page = MagicMock()
    mock_page.url = "https://www.naukri.com/mnjuser/profile"

    mock_edit_btn = _make_mock_locator(count=1, visible=True)
    mock_textarea = _make_mock_locator(count=1, visible=True, value=old_hl)

    # Class-based save button is missing
    mock_missing_save_btn = _make_mock_locator(count=0, visible=False)
    # Role-based save button exists
    mock_role_save_btn = _make_mock_locator(count=1, visible=True)
    mock_page.get_by_role.return_value = mock_role_save_btn

    def locator_side_effect(selector):
        sel_lower = selector.lower()
        if "headline" in sel_lower and ("span" in sel_lower or ".edit" in sel_lower):
            return mock_edit_btn
        elif "textarea" in sel_lower:
            return mock_textarea
        elif "save" in sel_lower:
            return mock_missing_save_btn
        return _make_mock_locator(count=0, visible=False)

    mock_page.locator.side_effect = locator_side_effect

    result = sync_resume_headline(mock_page, target_headline=target_hl)

    assert result is True
    mock_page.get_by_role.assert_called_with("button", name="Save", exact=True)
    mock_role_save_btn.click.assert_called_once()


# ==============================================================================
# SECTION 5: SYNC_RESUME_HEADLINE — DEGRADED & ERROR CONDITION STRESS TESTS
# ==============================================================================

def test_sync_resume_headline_missing_edit_button():
    """Verify returns False when edit button locator returns count 0."""
    mock_page = MagicMock()
    mock_page.url = "https://www.naukri.com/mnjuser/profile"
    mock_page.locator.return_value = _make_mock_locator(count=0, visible=False)

    result = sync_resume_headline(mock_page, target_headline="New Headline")
    assert result is False


def test_sync_resume_headline_invisible_textarea():
    """Verify returns False when textarea is present in DOM but not visible."""
    mock_page = MagicMock()
    mock_page.url = "https://www.naukri.com/mnjuser/profile"

    mock_edit_btn = _make_mock_locator(count=1, visible=True)
    mock_textarea = _make_mock_locator(count=1, visible=False)

    def locator_side_effect(selector):
        if "headline" in selector.lower() and ("span" in selector.lower() or ".edit" in selector.lower()):
            return mock_edit_btn
        elif "textarea" in selector.lower():
            return mock_textarea
        return _make_mock_locator(count=0, visible=False)

    mock_page.locator.side_effect = locator_side_effect

    result = sync_resume_headline(mock_page, target_headline="New Headline")
    assert result is False


def test_sync_resume_headline_missing_save_buttons():
    """Verify returns False when headline is modified but save button cannot be located."""
    mock_page = MagicMock()
    mock_page.url = "https://www.naukri.com/mnjuser/profile"

    mock_edit_btn = _make_mock_locator(count=1, visible=True)
    mock_textarea = _make_mock_locator(count=1, visible=True, value="Old Headline")
    mock_missing_btn = _make_mock_locator(count=0, visible=False)

    def locator_side_effect(selector):
        if "headline" in selector.lower() and ("span" in selector.lower() or ".edit" in selector.lower()):
            return mock_edit_btn
        elif "textarea" in selector.lower():
            return mock_textarea
        elif "save" in selector.lower():
            return mock_missing_btn
        return _make_mock_locator(count=0, visible=False)

    mock_page.locator.side_effect = locator_side_effect
    mock_page.get_by_role.return_value = mock_missing_btn

    result = sync_resume_headline(mock_page, target_headline="New Headline")
    assert result is False


def test_sync_resume_headline_locator_exception_handled():
    """Verify exceptions during DOM queries are caught and return False cleanly."""
    mock_page = MagicMock()
    mock_page.url = "https://www.naukri.com/mnjuser/profile"
    mock_page.locator.side_effect = RuntimeError("Playwright TargetClosedError")

    result = sync_resume_headline(mock_page, target_headline="New Headline")
    assert result is False
