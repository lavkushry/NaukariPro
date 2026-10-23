"""
Empirical Repeat-Write and Adversarial Stress Harness for Milestone 2
Authored by Challenger 2 (Iter 2) - teamwork_preview_challenger_m2_iter2_2

Performs deep stress-testing on an isolated copy of Naukri_Live_Application_Tracker.xlsx:
1. 100 sequential log_to_excel appends with adversarial/edge-case payloads
2. 50 sequential log_portal_application appends across 5 ATS portals
3. 30 sequential log_performance_snapshot appends across 30 simulated days
4. Comprehensive cell-by-cell regression verification of all historical records
5. Schema compliance audit of all 180 newly created records
6. Openpyxl and zipfile integrity verification
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import shutil
import tempfile
import zipfile
import openpyxl
from datetime import datetime

from naukari_pro.config import TRACKER_PATH
from naukari_pro.modules.auto_apply import log_to_excel
from naukari_pro.modules.career_portals import log_portal_application
from naukari_pro.modules.profile_performance import ProfilePerformanceEngine, compute_benchmark_pacing

CANONICAL_11_APP_HEADERS = [
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

def run_stress_test():
    print("=" * 80)
    print("CHALLENGER 2: STARTING EMPIRICAL REPEAT-WRITE STRESS TEST ON REAL TRACKER")
    print("=" * 80)

    assert os.path.exists(TRACKER_PATH), f"Real tracker not found at {TRACKER_PATH}"

    with tempfile.TemporaryDirectory() as tmpdir:
        isolated_tracker = os.path.join(tmpdir, "Isolated_Naukri_Tracker.xlsx")
        shutil.copy2(TRACKER_PATH, isolated_tracker)
        print(f"[OK] Isolated copy created: {isolated_tracker}")

        # Baseline snapshot
        wb_base = openpyxl.load_workbook(isolated_tracker, data_only=True)
        sheets = wb_base.sheetnames
        print(f"[OK] Baseline sheets: {sheets}")
        assert set(sheets) == {"Applications_Log", "Daily_Performance_Metrics", "Recruiter_Performance_Log"}

        ws_app_base = wb_base["Applications_Log"]
        ws_perf_base = wb_base["Recruiter_Performance_Log"]
        ws_daily_base = wb_base["Daily_Performance_Metrics"]

        base_app_rows = ws_app_base.max_row
        base_perf_rows = ws_perf_base.max_row
        base_daily_rows = ws_daily_base.max_row

        print(f"[OK] Baseline counts: Applications_Log={base_app_rows}, Recruiter_Performance_Log={base_perf_rows}, Daily_Performance_Metrics={base_daily_rows}")
        assert base_app_rows == 115, f"Expected 115 rows in Applications_Log, found {base_app_rows}"
        assert base_perf_rows == 3, f"Expected 3 rows in Recruiter_Performance_Log, found {base_perf_rows}"
        assert base_daily_rows == 2, f"Expected 2 rows in Daily_Performance_Metrics, found {base_daily_rows}"

        # Capture complete data snapshots of all baseline cells
        snapshot_app = [[ws_app_base.cell(r, c).value for c in range(1, 12)] for r in range(1, base_app_rows + 1)]
        snapshot_perf = [[ws_perf_base.cell(r, c).value for c in range(1, 11)] for r in range(1, base_perf_rows + 1)]
        snapshot_daily = [[ws_daily_base.cell(r, c).value for c in range(1, 7)] for r in range(1, base_daily_rows + 1)]
        wb_base.close()

        # ----------------------------------------------------------------------
        # STRESS PHASE 1: 100 Sequential log_to_excel appends
        # ----------------------------------------------------------------------
        print("\n--- PHASE 1: 100 Sequential log_to_excel Writes ---")
        adversarial_titles = [
            "Data Engineer, Azure & PySpark (L3)",
            "Senior Azure Data Platform Engineer - Databricks/Delta",
            "Azure Cloud Data Architect & ADF / Synapse Lead",
            "Data Engineer | Real-Time Kafka & PySpark | Lakehouse",
            "Specialist: Big Data & Azure Analytics (CI/CD, Terraform)"
        ]
        adversarial_companies = [
            "Tech Mahindra Ltd.",
            "LTIMindtree, Global Systems",
            "Accenture Solutions Pvt Ltd",
            "Deloitte Consulting India",
            "Cognizant Technology Solutions"
        ]
        
        for i in range(100):
            title = adversarial_titles[i % len(adversarial_titles)] + f" [Batch-{i}]"
            comp = adversarial_companies[i % len(adversarial_companies)]
            
            # Mix match_score formats: int, float, string with %, string without %, legacy format
            if i % 5 == 0:
                score = 70 + (i % 31)  # int e.g. 70, 75
            elif i % 5 == 1:
                score = float(70 + (i % 30))  # float e.g. 75.0
            elif i % 5 == 2:
                score = f"{70 + (i % 31)}%"  # string with % e.g. "85%"
            elif i % 5 == 3:
                score = f" {70 + (i % 31)} "  # string without % e.g. " 82 "
            else:
                score = 85  # default int

            res = log_to_excel(
                title=title,
                company=comp,
                status="Applied Successfully (1-Click)",
                match_score=score,
                app_type="1-Click Apply",
                salary=f"{15 + (i % 8)}-{22 + (i % 8)} LPA",
                url=f"https://www.naukri.com/job-listings-data-engineer-azure-{i}-221026000000",
                tracker_path=isolated_tracker
            )
            assert res is True, f"log_to_excel failed at write {i}"
        print("[PASS] 100 sequential log_to_excel writes completed successfully.")

        # ----------------------------------------------------------------------
        # STRESS PHASE 2: 50 Sequential log_portal_application appends
        # ----------------------------------------------------------------------
        print("\n--- PHASE 2: 50 Sequential log_portal_application Writes ---")
        portals = ["Workday", "Greenhouse", "Lever", "Ashby", "Rippling"]
        for i in range(50):
            portal = portals[i % len(portals)]
            comp = f"Global Tech Partner {i}"
            role = f"Azure Data Engineer - {portal} External {i}"
            res = log_portal_application(
                company=comp,
                role=role,
                portal_type=portal,
                status="Form Auto-Filled",
                url=f"https://boards.{portal.lower()}.io/job/{i}000{i}",
                match_score=78 + (i % 22),
                tracker_path=isolated_tracker
            )
            assert res is True, f"log_portal_application failed at write {i}"
        print("[PASS] 50 sequential log_portal_application writes completed successfully.")

        # ----------------------------------------------------------------------
        # STRESS PHASE 3: 30 Sequential log_performance_snapshot appends
        # ----------------------------------------------------------------------
        print("\n--- PHASE 3: 30 Sequential log_performance_snapshot Writes ---")
        perf_engine = ProfilePerformanceEngine()
        hist_path = os.path.join(tmpdir, "perf_history.json")
        for day in range(1, 31):
            snap = {
                "timestamp": f"2026-11-{day:02d} 09:30",
                "search_appearances": 3333 * day,
                "profile_views": 150 * day,
                "resume_downloads": 20 * day,
                "contact_views": 10 * day,
                "search_terms": ["Azure Data Engineer", "Databricks", "PySpark"]
            }
            perf_engine.log_performance_snapshot(snap, tracker_path=isolated_tracker, history_file=hist_path)
        print("[PASS] 30 sequential log_performance_snapshot writes completed successfully.")

        # ----------------------------------------------------------------------
        # STRESS PHASE 4: File and Zip Integrity Checks
        # ----------------------------------------------------------------------
        print("\n--- PHASE 4: Openpyxl & Zipfile Integrity Audit ---")
        zip_err = zipfile.ZipFile(isolated_tracker).testzip()
        assert zip_err is None, f"Zipfile corruption detected: {zip_err}"
        print("[PASS] Zipfile internal CRC test passed (testzip() is None).")

        # ----------------------------------------------------------------------
        # STRESS PHASE 5: Schema and Regression Forensic Verification
        # ----------------------------------------------------------------------
        print("\n--- PHASE 5: Cell-by-Cell Forensic Regression Verification ---")
        wb_aud = openpyxl.load_workbook(isolated_tracker, data_only=True)
        assert set(wb_aud.sheetnames) == {"Applications_Log", "Daily_Performance_Metrics", "Recruiter_Performance_Log"}

        ws_app = wb_aud["Applications_Log"]
        ws_perf = wb_aud["Recruiter_Performance_Log"]
        ws_daily = wb_aud["Daily_Performance_Metrics"]

        expected_app_rows = 115 + 100 + 50  # 265
        expected_perf_rows = 3 + 30          # 33
        expected_daily_rows = 2              # 2

        print(f"Post-stress counts: Applications_Log={ws_app.max_row}, Recruiter_Performance_Log={ws_perf.max_row}, Daily_Performance_Metrics={ws_daily.max_row}")
        assert ws_app.max_row == expected_app_rows, f"Applications_Log has {ws_app.max_row} rows (expected {expected_app_rows})"
        assert ws_perf.max_row == expected_perf_rows, f"Recruiter_Performance_Log has {ws_perf.max_row} rows (expected {expected_perf_rows})"
        assert ws_daily.max_row == expected_daily_rows, f"Daily_Performance_Metrics has {ws_daily.max_row} rows (expected {expected_daily_rows})"

        # Check 5.1: Exact preservation of all 114 historical application records (rows 1-115)
        print("Checking historical Applications_Log preservation (rows 1 to 115)...")
        for r in range(1, 116):
            for c in range(1, 12):
                orig_v = snapshot_app[r - 1][c - 1]
                curr_v = ws_app.cell(r, c).value
                assert orig_v == curr_v, f"Corrupted historical Applications_Log at row {r}, col {c}: expected '{orig_v}', got '{curr_v}'"
        print("[PASS] All 115 historical application rows (including 108-111) are 100% byte-for-byte identical.")

        # Check 5.2: Exact preservation of Recruiter_Performance_Log baseline (rows 1-3)
        print("Checking historical Recruiter_Performance_Log preservation (rows 1 to 3)...")
        for r in range(1, 4):
            for c in range(1, 11):
                orig_v = snapshot_perf[r - 1][c - 1]
                curr_v = ws_perf.cell(r, c).value
                assert orig_v == curr_v, f"Corrupted historical Recruiter_Performance_Log at row {r}, col {c}: expected '{orig_v}', got '{curr_v}'"
        print("[PASS] All 3 historical performance log rows are 100% identical.")

        # Check 5.3: Exact preservation of Daily_Performance_Metrics (rows 1-2)
        print("Checking Daily_Performance_Metrics preservation (rows 1 to 2)...")
        for r in range(1, 3):
            for c in range(1, 7):
                orig_v = snapshot_daily[r - 1][c - 1]
                curr_v = ws_daily.cell(r, c).value
                assert orig_v == curr_v, f"Corrupted Daily_Performance_Metrics at row {r}, col {c}: expected '{orig_v}', got '{curr_v}'"
        print("[PASS] Daily_Performance_Metrics is 100% untouched.")

        # Check 5.4: Compliance of all 150 new application rows (rows 116 to 265)
        print("Auditing 150 new application rows for canonical 11-column schema adherence...")
        for r in range(116, ws_app.max_row + 1):
            row = [ws_app.cell(r, c).value for c in range(1, 12)]
            assert len(row) == 11
            # Col 1: Date
            assert any(sep in str(row[0]) for sep in ["-", "/"]), f"Row {r} col 1 date invalid: {row[0]}"
            # Col 2: Company
            assert row[1] and "|" not in str(row[1]), f"Row {r} col 2 company invalid: {row[1]}"
            # Col 3: Title
            assert row[2], f"Row {r} col 3 title invalid: {row[2]}"
            # Col 4: Match score
            assert str(row[3]).endswith("%"), f"Row {r} col 4 score missing %: {row[3]}"
            score_num = int(str(row[3]).replace("%", "").strip())
            assert 70 <= score_num <= 100, f"Row {r} col 4 score out of range: {score_num}"
            # Col 5: Role Category
            assert row[4] == "Azure Data Engineer", f"Row {r} col 5 role category: {row[4]}"
            # Col 6: Experience
            assert row[5] == "2-5 Yrs", f"Row {r} col 6 exp: {row[5]}"
            # Col 7: Location
            assert row[6], f"Row {r} col 7 location: {row[6]}"
            # Col 8: App Type
            assert "Apply" in str(row[7]) or "Career Portal" in str(row[7]), f"Row {r} col 8 app type: {row[7]}"
            # Col 9: Status
            assert row[8], f"Row {r} col 9 status: {row[8]}"
            # Col 10: URL
            assert str(row[9]).startswith("http"), f"Row {r} col 10 URL: {row[9]}"
            # Col 11: Response
            assert row[10], f"Row {r} col 11 response: {row[10]}"
        print("[PASS] All 150 newly appended application records conform strictly to 11-column schema.")

        # Check 5.5: Compliance of all 30 new performance snapshot rows (rows 4 to 33)
        print("Auditing 30 new performance snapshot rows for canonical 10-column schema adherence...")
        for r in range(4, ws_perf.max_row + 1):
            row = [ws_perf.cell(r, c).value for c in range(1, 11)]
            assert len(row) == 10
            # Col 1: Timestamp
            assert "-" in str(row[0])
            # Col 2-5: Metric integers
            assert isinstance(row[1], int) and row[1] > 0
            assert isinstance(row[2], int) and row[2] > 0
            assert isinstance(row[3], int) and row[3] > 0
            assert isinstance(row[4], int) and row[4] > 0
            # Col 6-7: CTR, Conv %
            assert str(row[5]).endswith("%")
            assert str(row[6]).endswith("%")
            # Col 8: Daily Pace
            assert isinstance(row[7], (int, float))
            # Col 9: Projected 30d Volume
            assert isinstance(row[8], int)
            # Col 10: Pacing Status
            assert row[9] in ("ON_TRACK", "AHEAD", "DEFICIT")
        print("[PASS] All 30 newly appended performance records conform strictly to 10-column schema.")

        wb_aud.close()

    print("\n" + "=" * 80)
    print("ALL REPEAT-WRITE STRESS TESTS PASSED WITH 100% DATA AND SCHEMA INTEGRITY!")
    print("=" * 80)

if __name__ == "__main__":
    run_stress_test()
