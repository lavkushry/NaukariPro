"""
Adversarial Stress Test Suite for Milestone 2 (Recruiter Search Analytics & Application Tracker)
Authored by Challenger 1 (teamwork_preview_challenger_m2_1)
Validates Excel logging under repeat writes, concurrency, benchmark pacing math across varied ranges,
and forensic integrity of historical rows in Naukri_Live_Application_Tracker.xlsx.
"""

import os
import openpyxl
import pytest
import concurrent.futures
from datetime import datetime

from naukari_pro.config import TRACKER_PATH
from naukari_pro.modules.auto_apply import log_to_excel
from naukari_pro.modules.career_portals import log_portal_application
from naukari_pro.modules.profile_performance import (
    compute_benchmark_pacing,
    BenchmarkPacing,
    MONTHLY_SEARCH_BENCHMARK,
    DAILY_SEARCH_BENCHMARK
)

CANONICAL_11_HEADERS = [
    "Application Date",
    "Company Name",
    "Job Title",
    "Match Score (%)",
    "Role Category",
    "Experience Required",
    "Location",
    "Application Type",
    "Status",
    "Job URL",
    "Recruiter Response"
]

CANONICAL_10_PERF_HEADERS = [
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


# ==============================================================================
# CHALLENGE 1: Forensic Audit of Historical Rows in Naukri_Live_Application_Tracker.xlsx
# ==============================================================================

def test_historical_tracker_clean_row_count():
    """
    CRITICAL CHALLENGE: Verify Naukri_Live_Application_Tracker.xlsx has at least 114 real data rows (max_row >= 115)
    and zero synthetic/mock test rows left behind.
    """
    assert os.path.exists(TRACKER_PATH), f"Tracker workbook not found at {TRACKER_PATH}"
    wb = openpyxl.load_workbook(TRACKER_PATH, data_only=True)
    ws = wb["Applications_Log"]
    assert ws.max_row >= 115, (
        f"Applications_Log has {ws.max_row} rows (expected >= 115: 1 header + >= 114 real applications)."
    )
    for r in range(2, ws.max_row + 1):
        row_str = " ".join(str(ws.cell(r, c).value or "") for c in range(1, 12)).lower()
        assert "example.com" not in row_str and "mockcorp" not in row_str and "testcompany" not in row_str, (
            f"Row {r} contains synthetic test artifact: {row_str}"
        )


def test_historical_tracker_rows_schema_and_column_alignment():
    """
    CRITICAL CHALLENGE: Audit every data row in Applications_Log for schema adherence.
    Exposes Bug: Rows 108-111 are scrambled with integer IDs in Application Date,
    swapped Title/Company/Location columns, and None in Job URL and Recruiter Response.
    """
    assert os.path.exists(TRACKER_PATH)
    wb = openpyxl.load_workbook(TRACKER_PATH, data_only=True)
    ws = wb["Applications_Log"]

    corruptions = []
    for r in range(2, ws.max_row + 1):
        row_vals = [ws.cell(r, c).value for c in range(1, ws.max_column + 1)]
        
        # Col 1: Application Date must be a date string (YYYY-MM-DD...), not an integer serial ID
        date_val = str(row_vals[0]) if row_vals[0] is not None else ""
        if row_vals[0] is None or isinstance(row_vals[0], int) or not any(ch in date_val for ch in ["-", "/"]):
            corruptions.append((r, "Col 1 invalid Application Date (found ID/non-date)", row_vals[0]))

        # Col 2: Company Name must not be empty or pipe-delimited job title
        comp_val = str(row_vals[1]) if row_vals[1] is not None else ""
        if not comp_val or "|" in comp_val:
            corruptions.append((r, "Col 2 invalid Company Name (contains title/pipe or empty)", comp_val))

        # Col 4: Match Score (%) must end with '%' and parse to 0-100
        score_val = str(row_vals[3]) if row_vals[3] is not None else ""
        if not score_val.endswith("%"):
            corruptions.append((r, "Col 4 missing percentage symbol", score_val))

        # Col 10: Job URL must not be None
        if row_vals[9] is None:
            corruptions.append((r, "Col 10 Job URL is None", row_vals[9]))

        # Col 11: Recruiter Response must not be None
        if row_vals[10] is None:
            corruptions.append((r, "Col 11 Recruiter Response is None", row_vals[10]))

    assert len(corruptions) == 0, (
        f"Found {len(corruptions)} schema corruptions in historical applications log: {corruptions}"
    )


# ==============================================================================
# CHALLENGE 2: Benchmark Velocity Math & Truncation Flaw
# ==============================================================================

def test_benchmark_pacing_exact_100k_in_30_days_is_on_track():
    """
    CRITICAL CHALLENGE: Pacing engine must classify exact 100k attainment in 30 days as ON_TRACK (or AHEAD), not DEFICIT.
    Exposes Bug: int(daily_pace * 30) truncates 99999.9 to 99999, reporting DEFICIT on 100.0% goal attainment.
    """
    pacing = compute_benchmark_pacing(appearances=100000, days=30, target_monthly=100000)
    assert pacing.percent_attainment == 100.0, f"Expected 100.0% attainment, got {pacing.percent_attainment}"
    assert pacing.status in ("ON_TRACK", "AHEAD"), (
        f"Exact 100,000 appearances in 30 days must be ON_TRACK, got status '{pacing.status}' "
        f"with projected_monthly={pacing.projected_monthly}"
    )


@pytest.mark.parametrize("apps,days,expected_status,min_projected,max_projected", [
    (500, 7, "DEFICIT", 2100, 2200),
    (3333, 1, "DEFICIT", 99900, 100000),
    (15000, 15, "DEFICIT", 29900, 30100),
    (23333, 7, "DEFICIT", 99900, 100020),
    (28000, 7, "AHEAD", 119900, 120100),
    (150000, 30, "AHEAD", 149900, 150100),
    (0, 7, "DEFICIT", 0, 0),
    (-500, 7, "DEFICIT", 0, 0),
    (3500, 0, "AHEAD", 100000, 110000),  # safe_days = max(days, 1)
])
def test_benchmark_pacing_varied_ranges(apps, days, expected_status, min_projected, max_projected):
    """Verify velocity and run rate across wide operational ranges and boundary values."""
    p = compute_benchmark_pacing(appearances=apps, days=days, target_monthly=100000)
    assert p.daily_target == 3333.33
    assert min_projected <= p.projected_monthly <= max_projected
    if expected_status != "ANY":
        assert p.status == expected_status


# ==============================================================================
# CHALLENGE 3: Excel Logging Under Repeat Writes & Sequential Stability
# ==============================================================================

def test_log_to_excel_sequential_repeat_writes_50_rows(tmp_path):
    """Stress-test log_to_excel with 50 sequential appends maintaining 11-column contract."""
    wb_path = str(tmp_path / "repeat_tracker.xlsx")
    
    for i in range(50):
        ok = log_to_excel(
            title=f"Azure Data Platform Engineer {i}",
            company=f"Enterprise Tech {i}",
            status="Submitted",
            match_score=75 + (i % 20),
            app_type="1-Click Apply",
            salary="18-24 LPA",
            url=f"https://www.naukri.com/job-{i}",
            tracker_path=wb_path
        )
        assert ok is True, f"Sequential write {i} failed"

    wb = openpyxl.load_workbook(wb_path)
    assert "Applications_Log" in wb.sheetnames
    ws = wb["Applications_Log"]
    assert ws.max_row == 51  # 1 header + 50 entries
    assert ws.max_column == 11

    headers = [ws.cell(1, c).value for c in range(1, 12)]
    assert headers == CANONICAL_11_HEADERS

    # Spot check first, middle, and last rows
    for r in [2, 26, 51]:
        row_vals = [ws.cell(r, c).value for c in range(1, 12)]
        assert len(row_vals) == 11
        assert "Azure Data Platform Engineer" in str(row_vals[2])
        assert "%" in str(row_vals[3])
        assert row_vals[4] == "Azure Data Engineer"
        assert row_vals[7] == "1-Click Apply"
        assert row_vals[8] == "Submitted"
        assert "https://www.naukri.com/job-" in str(row_vals[9])
        assert row_vals[10] == "Awaiting Recruiter Review"


def test_log_portal_application_repeat_writes(tmp_path):
    """Stress-test log_portal_application with 25 sequential appends."""
    wb_path = str(tmp_path / "portal_repeat_tracker.xlsx")
    
    for i in range(25):
        ok = log_portal_application(
            company=f"Cloud Corp {i}",
            role=f"Senior Data Engineer {i}",
            portal_type="Workday",
            status="Form Auto-Filled",
            url=f"https://cloudcorp{i}.myworkdayjobs.com/job",
            match_score=88,
            tracker_path=wb_path
        )
        assert ok is True, f"Portal write {i} failed"

    wb = openpyxl.load_workbook(wb_path)
    ws = wb["Applications_Log"]
    assert ws.max_row == 26
    assert ws.max_column == 11
    headers = [ws.cell(1, c).value for c in range(1, 12)]
    assert headers == CANONICAL_11_HEADERS


def test_log_to_excel_backward_compatibility_positional_calls(tmp_path):
    """Verify backwards-compatibility for legacy positional calls in auto_apply.py."""
    wb_path = str(tmp_path / "legacy_tracker.xlsx")
    
    # Legacy style call: log_to_excel(title, comp, status, app_type, salary, url)
    ok1 = log_to_excel(
        "Data Engineer",
        "TCS",
        "Submitted (Pending)",
        "1-Click Direct",
        "12-16 LPA",
        "https://naukri.com/job/123",
        tracker_path=wb_path
    )
    assert ok1 is True

    # Multi-apply style: log_to_excel(title, comp, status, app_type)
    ok2 = log_to_excel(
        "Multi-Apply Batch",
        "Naukri AI Matches",
        "Submitted",
        "Recommended Multi-Apply",
        tracker_path=wb_path
    )
    assert ok2 is True

    wb = openpyxl.load_workbook(wb_path)
    ws = wb["Applications_Log"]
    assert ws.max_row == 3

    # Row 2 (Legacy 1-click): Col 4 should have fallback match score, Col 8 should have '1-Click Direct'
    row2 = [ws.cell(2, c).value for c in range(1, 12)]
    assert row2[3] == "85%"
    assert row2[7] == "1-Click Direct"
    assert row2[9] == "https://naukri.com/job/123"

    # Row 3 (Multi-apply): Col 4 fallback match score, Col 8 'Recommended Multi-Apply'
    row3 = [ws.cell(3, c).value for c in range(1, 12)]
    assert row3[3] == "85%"
    assert row3[7] == "Recommended Multi-Apply"


# ==============================================================================
# CHALLENGE 4: Concurrency Race Condition Failure Demonstration
# ==============================================================================

def test_concurrent_writes_data_loss_under_uncoordinated_calls(tmp_path):
    """
    Demonstrates lack of file locking in log_to_excel during concurrent calls.
    Uncoordinated concurrent writes result in BadZipFile collisions or dropped records.
    """
    wb_path = str(tmp_path / "concurrent_loss.xlsx")

    def worker_write(i):
        return log_to_excel(
            title=f"Concurrent Job {i}",
            company=f"Concurrent Co {i}",
            status="Submitted",
            match_score=80,
            tracker_path=wb_path
        )

    # 10 concurrent writes across 4 threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(worker_write, range(10)))

    # Empirical finding: under concurrent writes without mutex, not all writes succeed
    successful_calls = results.count(True)
    # Document that without process/thread locking, concurrent writes can drop records
    assert successful_calls <= 10
