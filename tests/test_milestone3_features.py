"""
Milestone 3 Automated Test Suite: Autonomous Multi-Channel Application Engine & Dry-Run
Validates Features 10, 11, 12, 13, CLI dry-run routes, and ApplicationPayload contracts.
"""

import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock

from naukari_pro.modules.job_alerts import (
    calculate_match_score,
    MATCH_SCORE_THRESHOLD,
    KEYWORD_WEIGHTS,
    InstantAlertsEngine
)
from naukari_pro.modules.auto_apply import (
    ApplicationPayload,
    build_dry_run_payload,
    generate_dry_run_payload,
    evaluate_job_match,
    AutoApplyEngine,
    NativeChromeRunner
)
from naukari_pro.modules.career_portals import (
    CareerPortalFiller,
    load_applicant_profile,
    DEFAULT_CANDIDATE
)
from naukari_pro.modules.multi_search import (
    UniversalJobSearchEngine
)
from naukari_pro.modules.profile_performance import (
    ProfilePerformanceEngine,
    ProfilePerformanceTracker,
    compute_benchmark_pacing
)
from naukari_pro.modules.pro_autopilot import ProAutoPilotEngine


# ==============================================================================
# FEATURE 10: MATCH SCORING GATE (>= 70%)
# ==============================================================================

def test_f10_match_score_threshold_constant():
    assert MATCH_SCORE_THRESHOLD == 70


def test_f10_module_level_calculate_match_score():
    assert calculate_match_score("") == 0
    assert calculate_match_score(None) == 0
    # Core technologies
    score = calculate_match_score("Azure Databricks PySpark Delta Lake")
    assert score >= 70
    # Irrelevant
    assert calculate_match_score("Frontend React Native HTML CSS") == 0


def test_f10_instant_alerts_engine_delegates_to_module_function():
    engine = InstantAlertsEngine()
    assert engine.calculate_match_score("Azure Databricks") == 40
    assert engine.calculate_match_score("Non matching role") == 0


def test_f10_evaluate_job_match_gating():
    # Qualified
    qualified, score, reason = evaluate_job_match(
        "Lead Azure Data Engineer",
        "Microsoft GCC",
        "Databricks PySpark Delta Lake Kafka"
    )
    assert qualified is True
    assert score >= 70
    assert "meets" in reason

    # Unqualified
    unqualified, score_low, reason_low = evaluate_job_match(
        "Frontend Engineer",
        "Startup",
        "React Redux JavaScript"
    )
    assert unqualified is False
    assert score_low < 70
    assert "below" in reason_low


def test_f10_apply_to_job_defense_in_depth_rejection():
    runner = NativeChromeRunner(skip_list=set(), dry_run=False)
    success, msg = runner.apply_to_job(
        job_url="https://naukri.com/job-123",
        title="Web Developer",
        company="Agency",
        salary="15 LPA",
        raw_jd="PHP WordPress HTML CSS",
        match_score=0
    )
    assert success is False
    assert "Rejected: Match score" in msg
    assert "below required 70% threshold" in msg


# ==============================================================================
# FEATURE 11: STRUCTURED DRY-RUN ENGINE & APPLICATIONPAYLOAD DATACLASS
# ==============================================================================

def test_f11_application_payload_schema_and_sync():
    payload = ApplicationPayload(
        company="Microsoft",
        title="Azure Data Engineer",
        url="https://naukri.com/msft-1",
        match_score=85,
        salary="25 LPA",
        answers={"exp": "2.5y"}
    )
    assert payload.company == "Microsoft"
    assert payload.title == "Azure Data Engineer"
    assert payload.job_title == "Azure Data Engineer"
    assert payload.role == "Azure Data Engineer"
    assert payload.payload_data == {"exp": "2.5y"}
    assert payload.dry_run is True
    assert payload.status == "VALIDATED_PAYLOAD"

    # Verify to_dict and to_json
    d = payload.to_dict()
    assert isinstance(d, dict)
    assert d["company"] == "Microsoft"
    assert d["role"] == "Azure Data Engineer"

    j = payload.to_json()
    assert isinstance(j, str)
    parsed = json.loads(j)
    assert parsed["company"] == "Microsoft"


def test_f11_build_and_generate_dry_run_payload_helpers():
    p1 = build_dry_run_payload(
        company="Databricks",
        title="Azure Data Platform Engineer",
        url="https://naukri.com/db-1",
        salary="30 LPA",
        raw_jd="Databricks PySpark Delta Lake SQL"
    )
    assert p1.match_score >= 70
    assert p1.status == "VALIDATED_PAYLOAD"

    p2 = generate_dry_run_payload({
        "company": "Agency",
        "title": "PHP Dev",
        "salary": "6 LPA",
        "jd": "WordPress HTML"
    })
    assert p2.match_score < 70
    assert p2.status == "REJECTED_BELOW_THRESHOLD"


def test_f11_auto_apply_engine_run_offline_dry_run():
    engine = AutoApplyEngine(dry_run=True)
    count = engine.run(limit=5)
    assert count == 3
    assert len(engine.payloads) == 5
    assert engine.payloads[0].status == "VALIDATED_PAYLOAD"
    assert engine.payloads[1].status == "VALIDATED_PAYLOAD"
    assert engine.payloads[2].status == "VALIDATED_PAYLOAD"
    assert engine.payloads[3].status == "REJECTED_LOW_SALARY"
    assert engine.payloads[4].status == "REJECTED_BELOW_THRESHOLD"
    assert all(p.dry_run is True for p in engine.payloads)


# ==============================================================================
# FEATURE 12: CAREER PORTAL MULTI-ATS FORM AUTOFILL & DRY-RUN
# ==============================================================================

def test_f12_ats_detection_all_platforms():
    filler = CareerPortalFiller()
    assert filler.detect_ats("https://boards.greenhouse.io/acme/jobs/1") == "Greenhouse"
    assert filler.detect_ats("https://jobs.lever.co/stripe/2") == "Lever"
    assert filler.detect_ats("https://jobs.ashbyhq.com/openai/3") == "Ashby"
    assert filler.detect_ats("https://walmart.myworkdayjobs.com/careers/4") == "Workday"
    assert filler.detect_ats("https://ats.rippling.com/startup/5") == "Rippling"
    assert filler.detect_ats("https://www.linkedin.com/jobs/view/6") == "LinkedIn"
    assert filler.detect_ats("https://jobs.smartrecruiters.com/corp/7") == "SmartRecruiters"
    assert filler.detect_ats("https://example.com/careers/generic/8") == "Generic Portal"


def test_f12_career_portal_fill_dry_run():
    filler = CareerPortalFiller()
    payload = filler.fill_dry_run(
        portal_url="https://boards.greenhouse.io/databricks/jobs/123",
        company="Databricks",
        role="Lead Azure Data Engineer",
        raw_jd="Azure Databricks PySpark Delta Lake",
        salary="28 LPA"
    )
    assert payload.company == "Databricks"
    assert payload.match_score >= 70
    assert payload.status == "VALIDATED_PAYLOAD"
    assert payload.portal_type == "Career Portal (Greenhouse)"
    assert payload.dry_run is True
    assert payload.answers["first_name"] == "Lavkush"
    assert payload.answers["experience"] == "2.5"
    assert payload.answers["notice_period"] == "15"


def test_f12_career_portal_unified_fill_dry_run():
    filler = CareerPortalFiller()
    success, payload = filler.fill(
        portal_url="https://jobs.ashbyhq.com/scale/456",
        company="Scale AI",
        role="Azure Data Engineer",
        dry_run=True
    )
    assert success is True
    assert isinstance(payload, ApplicationPayload)
    assert payload.dry_run is True
    assert payload.company == "Scale AI"


# ==============================================================================
# FEATURE 13: HN & LINKEDIN MULTI-CHANNEL SOURCING
# ==============================================================================

def test_f13_hn_payload_generation_gating():
    search_engine = UniversalJobSearchEngine()
    mock_jobs = [
        {
            "source": "Hacker News (Who's Hiring)",
            "title": "Principal Lakehouse Engineer",
            "company": "CloudTech",
            "location": "Remote",
            "url": "https://jobs.ashbyhq.com/cloudtech/1",
            "snippet": "We need Azure Databricks PySpark Delta Lake Kafka specialists."
        },
        {
            "source": "Hacker News (Who's Hiring)",
            "title": "Frontend React Dev",
            "company": "UIWorks",
            "location": "Remote",
            "url": "https://jobs.lever.co/uiworks/2",
            "snippet": "Building React and Tailwind CSS components."
        }
    ]
    payloads = search_engine.generate_application_payloads_from_hn(limit=5, jobs=mock_jobs)
    assert len(payloads) == 1
    assert payloads[0].company == "CloudTech"
    assert payloads[0].match_score >= 70
    assert payloads[0].status == "VALIDATED_PAYLOAD"


def test_f13_linkedin_precision_payloads_generation():
    search_engine = UniversalJobSearchEngine()
    payloads = search_engine.generate_application_payloads_from_linkedin(limit=3)
    assert len(payloads) >= 1
    for p in payloads:
        assert p.match_score >= 70
        assert p.status == "VALIDATED_PAYLOAD"
        assert p.dry_run is True
        assert "LinkedIn" in p.portal_type


def test_f13_search_and_dry_run_multi_channel():
    search_engine = UniversalJobSearchEngine()
    payloads = search_engine.search_and_dry_run(limit=2)
    assert len(payloads) >= 2
    for p in payloads:
        assert p.dry_run is True
        assert p.status == "VALIDATED_PAYLOAD"


def test_f12_candidate_profile_compliance_agents_section_9():
    """Validates AGENTS.md §9 candidate employment history facts in career portal profile."""
    prof = load_applicant_profile()
    assert prof["currentCompany"] is not None
    assert "CGI" in prof["currentCompany"]
    assert prof["currentTitle"] is not None
    assert "workHistory" in prof
    assert len(prof["workHistory"]) >= 4

    companies = [w["company"] for w in prof["workHistory"]]
    assert any("CGI" in c for c in companies)
    assert any("HFCL" in c or "Himachal" in c for c in companies)
    assert any("Stipe" in c for c in companies)

    assert "education" in prof
    assert len(prof["education"]) >= 1

    # Verify fill_dry_run answers include complete history
    filler = CareerPortalFiller()
    payload = filler.fill_dry_run(
        portal_url="https://boards.greenhouse.io/databricks/jobs/123",
        company="Databricks",
        role="Azure Data Engineer",
        raw_jd="Azure Databricks PySpark Delta Lake"
    )
    assert payload.answers["current_company"] == prof["currentCompany"]
    assert payload.answers["current_title"] == prof["currentTitle"]
    assert len(payload.answers["work_history"]) >= 4
    assert len(payload.answers["education"]) >= 1


def test_f12_detect_ats_none_and_malformed_url_safety():
    """Validates defensive safety of detect_ats against None, empty, and non-string inputs."""
    filler = CareerPortalFiller()
    assert filler.detect_ats(None) == "Generic Portal"
    assert filler.detect_ats("") == "Generic Portal"
    assert filler.detect_ats(123) == "Generic Portal"
    assert filler.detect_ats("https://example.com/careers/openings") == "Generic Portal"

    # MultiSearch caller defense test
    search_engine = UniversalJobSearchEngine()
    payload = search_engine.generate_application_payload({"title": "Azure Data Engineer", "url": None})
    assert isinstance(payload, ApplicationPayload)
    assert payload.url == "N/A"
    assert payload.portal_type == "Career Portal (Generic Portal)"


def test_f12_sub_threshold_match_score_gate_without_raw_jd():
    """Validates that sub-threshold roles are rejected and not artificially boosted to 85%."""
    filler = CareerPortalFiller()
    payload = filler.fill_dry_run(
        portal_url="https://boards.greenhouse.io/acme/jobs/123",
        company="Startup",
        role="Frontend React Developer"
    )
    assert payload.match_score == 0
    assert payload.status == "REJECTED_BELOW_THRESHOLD"


# ==============================================================================
# FEATURE 14: LIVE AUTHENTICATED NAUKRI ANALYTICS EXTRACTION
# ==============================================================================

def test_f14_profile_performance_tracker_alias_and_methods():
    """Validates ProfilePerformanceTracker alias and display_report / generate_report methods."""
    assert ProfilePerformanceTracker is ProfilePerformanceEngine
    tracker = ProfilePerformanceTracker()
    assert hasattr(tracker, "display_report")
    assert hasattr(tracker, "generate_report")
    report = tracker.display_report()
    assert isinstance(report, dict)
    assert "search_appearances" in report
    assert "data_source" in report


def test_f14_fetch_live_performance_targets_correct_url_and_extracts_metrics():
    """Validates fetch_live_performance visits https://www.naukri.com/mnjuser/performance and parses DOM."""
    import re
    engine = ProfilePerformanceEngine()
    mock_page = MagicMock()
    mock_page.url = "https://www.naukri.com/mnjuser/performance"

    class MockElement:
        def __init__(self, text, count=1, visible=True):
            self._text = text
            self._count = count
            self._visible = visible
        def count(self):
            return self._count
        def is_visible(self):
            return self._visible
        def inner_text(self):
            return self._text
        @property
        def first(self):
            return self
        def all(self):
            return [self] if self._count > 0 else []
        def locator(self, sel):
            if "tag-count" in sel or "ja-tag-count" in sel:
                m = re.search(r'\b\d+\b', self._text)
                return MockElement(m.group(0) if m else "0")
            elif "keyword-label" in sel:
                return MockElement(self._text)
            return MockElement("")

    def mock_locator(selector):
        sel_lower = selector.lower()
        if "summary-card__search-appearance--value" in sel_lower:
            return MockElement("621")
        elif "search-appearances-droop" in sel_lower:
            return MockElement("33 Search appearances in last")
        elif "summary-card__recruiter-actions--value" in sel_lower:
            return MockElement("21")
        elif "ja-tag" in sel_lower:
            tags = [
                MockElement("Naukri profile viewed 7"),
                MockElement("Contact viewed 4"),
                MockElement("Resume downloaded 2"),
                MockElement("NVite sent 12"),
                MockElement("Profile bookmarked 1")
            ]
            m_list = MagicMock()
            m_list.all.return_value = tags
            return m_list
        elif "search-keyword-card" in sel_lower:
            keywords = [
                MockElement("Kubernetes"),
                MockElement("Aws Cloud Or Chennai"),
                MockElement("Databricks"),
                MockElement("Pipeline"),
                MockElement("Qa/qc Engineer")
            ]
            m_list = MagicMock()
            m_list.all.return_value = keywords
            return m_list
        elif "body" in sel_lower:
            return MockElement(
                "621 Search appearances 21 Recruiter actions "
                "33 Search appearances in last 7 days "
                "Profile viewed 7 Contact viewed 4 Resume downloaded 2 NVite sent 12 Profile bookmarked 1"
            )
        return MockElement("", count=0, visible=False)

    mock_page.locator.side_effect = mock_locator

    with patch.object(engine, "log_performance_snapshot") as mock_log:
        metrics = engine.fetch_live_performance(mock_page)

    mock_page.goto.assert_called_once()
    target_url = mock_page.goto.call_args[0][0]
    assert target_url == "https://www.naukri.com/mnjuser/performance"
    assert "/profile-performance" not in target_url

    assert metrics["search_appearances_90d"] == 621
    assert metrics["search_appearances_7d"] == 33
    assert metrics["search_appearances"] == 621
    assert metrics["recruiter_actions"] == 21
    assert metrics["profile_views"] == 7
    assert metrics["contact_views"] == 4
    assert metrics["resume_downloads"] == 2
    assert metrics["nvites"] == 12
    assert metrics["recruiter_bookmarks"] == 1
    assert "Kubernetes" in metrics["search_terms"]
    assert "Databricks" in metrics["search_terms"]
    mock_log.assert_called_once_with(metrics)


# ==============================================================================
# FEATURE 15: RECRUITER PERFORMANCE LOG CANONICAL 10-COLUMN SCHEMA
# ==============================================================================

def test_f15_recruiter_performance_log_canonical_10_column_persistence(tmp_path):
    """Validates Recruiter_Performance_Log logs with canonical 10-column schema."""
    import openpyxl
    tracker_file = str(tmp_path / "test_tracker.xlsx")
    json_file = str(tmp_path / "test_history.json")

    engine = ProfilePerformanceEngine()
    sample_metrics = {
        "timestamp": "2026-10-25 18:00",
        "search_appearances": 621,
        "search_appearances_90d": 621,
        "search_appearances_7d": 33,
        "recruiter_actions": 21,
        "profile_views": 7,
        "resume_downloads": 2,
        "contact_views": 4,
        "nvites": 12,
        "recruiter_bookmarks": 1,
        "search_terms": ["Kubernetes", "Databricks"],
        "data_source": "Live Naukri Portal"
    }

    ok = engine.log_performance_snapshot(sample_metrics, tracker_path=tracker_file, history_file=json_file)
    assert ok is True

    wb = openpyxl.load_workbook(tracker_file)
    assert "Recruiter_Performance_Log" in wb.sheetnames
    ws = wb["Recruiter_Performance_Log"]
    headers = [cell.value for cell in ws[1]]
    assert len(headers) == 10
    expected_headers = [
        "Timestamp",
        "Search Appearances",
        "Profile Views",
        "Resume Downloads",
        "Contact Views",
        "CTR (%)",
        "Contact Conv (%)",
        "Daily Pace (req 3333)",
        "Projected 30d Volume",
        "Pacing Status"
    ]
    assert headers == expected_headers

    row2 = [cell.value for cell in ws[2]]
    assert row2[0] == "2026-10-25 18:00"
    assert row2[1] == 621
    assert row2[2] == 7
    assert row2[3] == 2
    assert row2[4] == 4
    assert row2[9] in ["DEFICIT", "ON_TRACK", "AHEAD"]


# ==============================================================================
# FEATURE 16: AUTOPILOT & CLI LIVE TELEMETRY INTEGRATION
# ==============================================================================

def test_f16_pro_autopilot_telemetry_wiring():
    """Validates that ProAutoPilotEngine initializes with perf_engine and runs dry_run cleanly."""
    autopilot = ProAutoPilotEngine(limit=2, dry_run=True)
    assert isinstance(autopilot.perf_engine, ProfilePerformanceEngine)
    assert hasattr(autopilot.perf_engine, "display_report")

    summary = autopilot.run_full_pipeline()
    assert isinstance(summary, dict)
    assert "applied_count" in summary
    assert "total_tracked" in summary


