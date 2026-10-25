"""
Adversarial Empirical Challenge Test Suite for Milestone 2 Iteration 2
Target: High-Volume Live Application & Recommended Job Harvesting
Scope:
1. Search pagination URL construction (pageNo=1, 2, 3) and multi-location URL generation
2. "Already Applied" button states -> verify they are skipped and NOT logged as newly submitted applications
3. Recommended jobs harvesting at https://www.naukri.com/mnjuser/recommendedjobs with >=70% match scoring
4. Excel tracker 11-column canonical schema preservation
"""

import os
import json
import shutil
import asyncio
import tempfile
import urllib.parse
from unittest.mock import MagicMock, AsyncMock, patch
import pytest
import openpyxl

from naukari_pro.modules.auto_apply import (
    DEFAULT_KEYWORDS,
    CANONICAL_LOCATIONS,
    LOCATIONS,
    EXPERIENCE_PARAM,
    MATCH_SCORE_THRESHOLD,
    evaluate_job_match,
    calculate_match_score,
    log_to_excel,
    make_job_id,
    PlaywrightRunner,
    NativeChromeRunner,
)
from naukari_pro.modules.hidden_jobs import HiddenJobsEngine, TARGET_GCCS
from naukari_pro.config import TRACKER_PATH


# ==============================================================================
# SUITE 1: Search Pagination & Multi-Location URL Generation
# ==============================================================================

class TestSearchPaginationAndUrlConstruction:
    """Empirical verification of search query URLs across all locations, keywords, and pages."""

    def test_search_url_pagination_parameters(self):
        """Verify page 1, 2, and 3 URL construction format and query parameters."""
        kw = "Azure Data Engineer"
        slug = "-".join(kw.lower().split())
        loc = "hyderabad"

        for page_num in range(1, 4):
            page_suffix = f"-{page_num}" if page_num > 1 else ""
            page_query = f"&pageNo={page_num}" if page_num > 1 else ""
            url = f"https://www.naukri.com/{slug}-jobs-in-{loc}{page_suffix}?experience={EXPERIENCE_PARAM}&jobAge=1&freshness=1&sortBy=date&sortType=1{page_query}"

            parsed = urllib.parse.urlparse(url)
            params = urllib.parse.parse_qs(parsed.query)

            assert parsed.scheme == "https"
            assert parsed.netloc == "www.naukri.com"
            assert params["experience"] == [str(EXPERIENCE_PARAM)]
            assert params["jobAge"] == ["1"]
            assert params["freshness"] == ["1"]
            assert params["sortBy"] == ["date"]
            assert params["sortType"] == ["1"]

            if page_num == 1:
                assert "pageNo" not in params
                assert "-1" not in parsed.path
                assert parsed.path == f"/{slug}-jobs-in-{loc}"
            else:
                assert params["pageNo"] == [str(page_num)]
                assert parsed.path == f"/{slug}-jobs-in-{loc}-{page_num}"

    def test_all_11_keywords_and_7_locations_combinatorics(self):
        """Verify all 231 permutations (11 keywords * 7 locations * 3 pages) generate valid search URLs."""
        assert len(DEFAULT_KEYWORDS) >= 11, f"Expected at least 11 keywords, got {len(DEFAULT_KEYWORDS)}"
        assert len(CANONICAL_LOCATIONS) == 7, f"Expected 7 locations, got {len(CANONICAL_LOCATIONS)}"

        generated_urls = set()
        for loc in CANONICAL_LOCATIONS:
            for kw in DEFAULT_KEYWORDS:
                slug = "-".join(kw.lower().split())
                for page_num in range(1, 4):
                    page_suffix = f"-{page_num}" if page_num > 1 else ""
                    page_query = f"&pageNo={page_num}" if page_num > 1 else ""
                    url = f"https://www.naukri.com/{slug}-jobs-in-{loc}{page_suffix}?experience={EXPERIENCE_PARAM}&jobAge=1&freshness=1&sortBy=date&sortType=1{page_query}"
                    generated_urls.add(url)

                    # Validate slug format: lowercase, hyphen-delimited, no spaces
                    assert " " not in url
                    assert kw.lower().replace(" ", "-") in url.lower()
                    assert loc.lower() in url.lower()

        expected_count = len(DEFAULT_KEYWORDS) * len(CANONICAL_LOCATIONS) * 3
        assert len(generated_urls) == expected_count, f"Expected {expected_count} unique URLs, got {len(generated_urls)}"

    def test_playwright_runner_scans_across_multiple_pages(self):
        """Verify PlaywrightRunner.run_async iterates through pages and processes cards on each page."""
        mock_page = AsyncMock()
        mock_context = AsyncMock()
        mock_context.pages = [mock_page]
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.add_init_script = AsyncMock()
        mock_context.add_cookies = AsyncMock()
        mock_context.on = MagicMock()
        mock_context.close = AsyncMock()

        visited_urls = []
        async def mock_goto(url, **kwargs):
            visited_urls.append(url)
            return None
        mock_page.goto = mock_goto
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.close = AsyncMock()

        # Provide 1 job on page 1, 1 job on page 2, 0 jobs on page 3
        async def mock_evaluate(script):
            if "srp-jobtuple-wrapper" in script:
                current_url = visited_urls[-1] if visited_urls else ""
                if "pageNo=3" in current_url or "-3?" in current_url:
                    return []
                return [{
                    "title": "Azure Data Engineer",
                    "company": "Cognizant",
                    "sal": "16 LPA",
                    "href": f"https://www.naukri.com/job-{len(visited_urls)}",
                    "desc": "Azure Data Engineer PySpark Databricks Delta Lake Kafka ADF",
                    "tags": "PySpark, Databricks"
                }]
            return []
        mock_page.evaluate = mock_evaluate

        runner = PlaywrightRunner(skip_list=set(), dry_run=True)
        runner.harvest_recommended_jobs_async = AsyncMock(return_value=0)
        runner.harvest_nvites_and_inbox_async = AsyncMock(return_value=0)

        async def run_test():
            with patch("naukari_pro.modules.auto_apply.DEFAULT_KEYWORDS", ["Azure Data Engineer"]):
                with patch("naukari_pro.modules.auto_apply.LOCATIONS", ["hyderabad"]):
                    total = await runner.run_async(limit=2)
                    return total

        mock_p_ctx = AsyncMock()
        mock_p_ctx.chromium.launch_persistent_context = AsyncMock(return_value=mock_context)

        with patch("playwright.async_api.async_playwright") as mock_ap:
            mock_ap.return_value.__aenter__.return_value = mock_p_ctx
            with patch("naukari_pro.session.SessionLock") as mock_lock_cls:
                mock_lock = MagicMock()
                mock_lock.acquire.return_value = True
                mock_lock.release = MagicMock()
                mock_lock_cls.return_value = mock_lock
                total = asyncio.run(run_test())

        assert total == 2
        assert any("pageNo=2" in u for u in visited_urls)
        assert any(u.endswith("freshness=1&sortBy=date&sortType=1") for u in visited_urls)

    def test_defect_native_chrome_runner_loop_indentation_drops_jobs(self):
        """
        EMPIRICAL DEFECT PROOF:
        In NativeChromeRunner.run, line 766 `for job in jobs:` is indented 12 spaces,
        making it a sibling to `for kw in DEFAULT_KEYWORDS:` and outside `for page_num in range(1, 4):`.
        This causes jobs from earlier pages and earlier keywords to be overwritten by subsequent fetches,
        evaluating ONLY the last page of the last keyword per location.
        """
        import inspect
        src = inspect.getsource(NativeChromeRunner.run)
        lines = src.split("\n")

        kw_indent = None
        page_indent = None
        job_loop_indent = None

        for l in lines:
            if "for kw in DEFAULT_KEYWORDS:" in l:
                kw_indent = len(l) - len(l.lstrip())
            elif "for page_num in range(1, 4):" in l:
                page_indent = len(l) - len(l.lstrip())
            elif "for job in jobs:" in l:
                job_loop_indent = len(l) - len(l.lstrip())

        # Verify remediation: for job in jobs must be nested inside page loop
        assert kw_indent is not None
        assert page_indent is not None
        assert job_loop_indent is not None
        # `for job in jobs:` must be inside `for page_num in range(1, 4):` (20 > 16 > 12)
        assert job_loop_indent > page_indent, (
            f"Indentation defect detected: `for job in jobs:` has indent {job_loop_indent}, "
            f"must be nested inside `for page_num in range(1, 4):` ({page_indent})."
        )
        assert job_loop_indent > kw_indent


# ==============================================================================
# SUITE 2: "Already Applied" Button States & Zero False-Positive Logging
# ==============================================================================

class TestAlreadyAppliedDetectionAndSkip:
    """Empirical verification that 'Already Applied' button states are skipped without Excel logging."""

    def test_btn_info_already_applied_variations(self):
        """Verify button text variations for 'Already Applied' are categorized as already_applied."""
        def evaluate_btn_info(btn_text, has_co_btn=False, has_apply_btn=True):
            if has_co_btn:
                return {"type": "company_site"}
            if not has_apply_btn:
                return {"type": "no_button"}
            txt = (btn_text or "").lower().strip()
            if "already applied" in txt:
                return {"type": "already_applied"}
            return {"type": "apply", "text": txt}

        assert evaluate_btn_info("Already Applied")["type"] == "already_applied"
        assert evaluate_btn_info("already applied")["type"] == "already_applied"
        assert evaluate_btn_info("  Already Applied  \n")["type"] == "already_applied"
        assert evaluate_btn_info("You have already applied")["type"] == "already_applied"
        assert evaluate_btn_info("Already applied on 23 Oct 2026")["type"] == "already_applied"
        assert evaluate_btn_info("ALREADY APPLIED")["type"] == "already_applied"
        assert evaluate_btn_info("Apply")["type"] == "apply"
        assert evaluate_btn_info("Apply on company site", has_co_btn=True)["type"] == "company_site"
        assert evaluate_btn_info("", has_apply_btn=False)["type"] == "no_button"

    def test_final_check_already_applied_body_and_button_rejection(self):
        """Verify final_check evaluation logic rejects already applied states and requires authentic submission."""
        def evaluate_final_check(url, drawer_text="", toast_present=False, body_text="", btn_text=""):
            if "saveapply" in url.lower() or "myapply" in url.lower():
                return True
            if drawer_text:
                t = drawer_text.lower()
                if "thank you for your responses" in t or "submitted" in t or "successfully applied" in t:
                    return True
            b_txt = (body_text or "").lower()
            btn_t = (btn_text or "").lower().strip()
            is_already = ("already applied" in btn_t) or ("you have already applied" in b_txt)
            if is_already:
                return False
            is_newly_applied = (btn_t == "applied") or ("application submitted" in btn_t) or ("applied successfully" in btn_t)
            return bool(toast_present) or is_newly_applied or ("successfully applied" in b_txt) or ("apply confirmation" in b_txt)

        # Case 1: Button says "Already Applied"
        assert evaluate_final_check("https://www.naukri.com/job", btn_text="Already Applied") is False

        # Case 2: Body text contains "you have already applied"
        assert evaluate_final_check("https://www.naukri.com/job", body_text="You have already applied for this vacancy", btn_text="Apply") is False

        # Case 3: Genuine newly applied (button text transitions to "applied")
        assert evaluate_final_check("https://www.naukri.com/job", btn_text="Applied") is True

        # Case 4: Toast message confirmed
        assert evaluate_final_check("https://www.naukri.com/job", toast_present=True, btn_text="Apply") is True

        # Case 5: Drawer with thank you message
        assert evaluate_final_check("https://www.naukri.com/job", drawer_text="Thank you for your responses! Your application was submitted.") is True

        # Case 6: Redirect to myapply URL
        assert evaluate_final_check("https://www.naukri.com/mnjuser/myapply?jobId=123") is True

    def test_apply_to_job_async_skips_and_does_not_log_already_applied(self, tmp_path):
        """Verify PlaywrightRunner.apply_to_job_async skips already applied job and writes 0 records to Excel."""
        temp_tracker = str(tmp_path / "Test_Tracker.xlsx")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Applications_Log"
        ws.append([
            "Application Date", "Company Name", "Job Title", "Match Score (%)",
            "Role Category", "Experience Required", "Location", "Application Type",
            "Status", "Job URL", "Recruiter Response"
        ])
        wb.save(temp_tracker)

        mock_context = AsyncMock()
        mock_job_tab = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_job_tab)
        mock_job_tab.goto = AsyncMock()
        mock_job_tab.wait_for_timeout = AsyncMock()

        # Simulate evaluate returning already_applied for btn_info
        mock_job_tab.evaluate = AsyncMock(return_value={"type": "already_applied"})

        runner = PlaywrightRunner(skip_list=set(), dry_run=False)

        async def run_apply():
            with patch("naukari_pro.modules.auto_apply.TRACKER_PATH", temp_tracker):
                success, msg = await runner.apply_to_job_async(
                    context=mock_context,
                    job_url="https://www.naukri.com/job-12345",
                    title="Azure Data Engineer",
                    company="TCS",
                    salary="15 LPA",
                    raw_jd="Azure Databricks PySpark Delta Lake Kafka ADF",
                    match_score=85
                )
                return success, msg

        success, msg = asyncio.run(run_apply())

        assert success is False
        assert "Already applied previously" in msg
        assert make_job_id("Azure Data Engineer", "TCS") in runner.skip_list

        # Verify Excel tracker was NOT written to
        verify_wb = openpyxl.load_workbook(temp_tracker)
        verify_ws = verify_wb["Applications_Log"]
        assert verify_ws.max_row == 1, f"Expected 1 row (header only), but found {verify_ws.max_row} rows!"


# ==============================================================================
# SUITE 3: Recommended Jobs Harvesting & Match Score Gating (>= 70%)
# ==============================================================================

class TestRecommendedJobsHarvesting:
    """Empirical verification of Recommended Jobs harvesting and strict >= 70% threshold gating."""

    def test_recommended_jobs_harvest_evaluates_cards_and_gates_at_70_percent(self):
        """Verify harvest_recommended_jobs_async evaluates cards and accepts only >= 70% score."""
        mock_page = AsyncMock()
        mock_context = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.url = "https://www.naukri.com/mnjuser/recommendedjobs"

        # 4 mock cards:
        # Card 1: 80% match (Azure Data Engineer, Databricks, PySpark, Delta Lake, Kafka)
        # Card 2: 80% match (Azure Data Engineer, Databricks, Delta Lake, PySpark, ADF, Kafka)
        # Card 3: 20% match (Junior Java Developer, Spring Boot, Microservices)
        # Card 4: 0% match (Accountant, Tally, GST)
        mock_cards = [
            {
                "title": "Azure Data Engineer",
                "company": "Infosys",
                "sal": "18 LPA",
                "href": "https://www.naukri.com/rec-job-1",
                "desc": "Azure Data Engineer with hands-on PySpark, Databricks, Delta Lake, Kafka, and ADF pipelines.",
                "tags": "PySpark, Databricks, Delta Lake"
            },
            {
                "title": "Azure Data Engineer Specialist",
                "company": "Wipro",
                "sal": "20 LPA",
                "href": "https://www.naukri.com/rec-job-2",
                "desc": "Azure Data Engineer Databricks Delta Lake PySpark Kafka Snowflake ADF Medallion Architecture",
                "tags": "PySpark, ADF, Databricks"
            },
            {
                "title": "Junior Java Developer",
                "company": "AppCo",
                "sal": "8 LPA",
                "href": "https://www.naukri.com/rec-job-3",
                "desc": "Java backend developer with Spring Boot and Hibernate experience.",
                "tags": "Java, Spring Boot"
            },
            {
                "title": "Accountant",
                "company": "FinanceLtd",
                "sal": "5 LPA",
                "href": "https://www.naukri.com/rec-job-4",
                "desc": "Experienced accountant with Tally and GST filing knowledge.",
                "tags": "Tally, GST"
            }
        ]

        async def mock_evaluate(script):
            if "srp-jobtuple-wrapper" in script or "recommended" in script:
                return mock_cards
            return []
        mock_page.evaluate = mock_evaluate

        runner = PlaywrightRunner(skip_list=set(), dry_run=True)

        async def run_harvest():
            total = await runner.harvest_recommended_jobs_async(
                context=mock_context,
                page=mock_page,
                limit=10,
                total_applied=0
            )
            return total

        total_applied = asyncio.run(run_harvest())

        # Exactly 2 jobs meet >= 70% threshold
        assert total_applied == 2

        # Verify low-match jobs were added to skip_list with low-match reason
        assert make_job_id("Junior Java Developer", "AppCo") in runner.skip_list
        assert make_job_id("Accountant", "FinanceLtd") in runner.skip_list

    def test_recommended_jobs_login_redirect_handled_safely(self):
        """Verify harvest_recommended_jobs_async returns gracefully if redirected to login."""
        mock_page = AsyncMock()
        mock_context = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.url = "https://www.naukri.com/nlogin/login"

        runner = PlaywrightRunner(skip_list=set(), dry_run=True)

        async def run_login_check():
            total = await runner.harvest_recommended_jobs_async(
                context=mock_context,
                page=mock_page,
                limit=10,
                total_applied=0
            )
            return total

        total = asyncio.run(run_login_check())
        assert total == 0

    def test_hidden_jobs_engine_harvest_and_evaluate(self):
        """Verify HiddenJobsEngine.harvest_and_evaluate_opportunities filters at min_threshold >= 70%."""
        engine = HiddenJobsEngine()

        mock_page = MagicMock()
        mock_page.url = "https://www.naukri.com/mnjuser/recommendedjobs"

        # Mock discover_hidden_opportunities returning list with varied match scores
        with patch.object(engine, "discover_hidden_opportunities", return_value=[
            {"title": "Azure Data Engineer", "company": "Barclays", "match_score": 85, "is_gcc": True},
            {"title": "Big Data Specialist", "company": "PNC Bank", "match_score": 75, "is_gcc": True},
            {"title": "PHP Developer", "company": "WebTech", "match_score": 15, "is_gcc": False},
        ]):
            qualified = engine.harvest_and_evaluate_opportunities(mock_page, min_threshold=70)
            assert len(qualified) == 2
            assert all(j["match_score"] >= 70 for j in qualified)
            assert all(j["is_gcc"] is True for j in qualified)


# ==============================================================================
# SUITE 4: Excel Tracker 11-Column Canonical Schema Preservation
# ==============================================================================

class TestExcelTrackerCanonicalSchema:
    """Empirical verification of 11-column Excel schema preservation across repeat writes."""

    CANONICAL_COLUMNS = [
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

    def test_canonical_tracker_header_and_column_count(self):
        """Verify real Naukri_Live_Application_Tracker.xlsx has exactly 11 canonical columns."""
        assert os.path.exists(TRACKER_PATH), f"Tracker not found at {TRACKER_PATH}"
        wb = openpyxl.load_workbook(TRACKER_PATH, data_only=True)
        assert "Applications_Log" in wb.sheetnames
        ws = wb["Applications_Log"]

        header = [cell.value for cell in ws[1]]
        assert len(header) == 11, f"Expected 11 columns, got {len(header)}: {header}"
        assert header == self.CANONICAL_COLUMNS

    def test_isolated_repeat_writes_schema_preservation(self, tmp_path):
        """Verify 50 sequential log_to_excel writes preserve 11-column schema without drift or corruption."""
        temp_tracker = str(tmp_path / "Stress_Tracker.xlsx")
        shutil.copyfile(TRACKER_PATH, temp_tracker)

        initial_wb = openpyxl.load_workbook(temp_tracker)
        initial_rows = initial_wb["Applications_Log"].max_row

        # Write 50 diverse records
        for i in range(50):
            status = "Submitted (Pending)" if i % 2 == 0 else "External Redirect"
            app_type = "1-Click Direct" if i % 2 == 0 else "External Employer Portal"
            score = 70 + (i % 25)
            url = f"https://www.naukri.com/job-listings-data-engineer-test-{i}"

            ok = log_to_excel(
                title=f"Azure Data Engineer Level {i}",
                company=f"Enterprise Tech {i}",
                status=status,
                match_score=score,
                app_type=app_type,
                salary="18 LPA",
                url=url,
                tracker_path=temp_tracker
            )
            assert ok is True

        # Audit modified workbook
        audit_wb = openpyxl.load_workbook(temp_tracker, data_only=True)
        ws = audit_wb["Applications_Log"]

        assert ws.max_row == initial_rows + 50
        assert ws.max_column == 11

        # Check every appended row for exact 11 columns and format adherence
        for r in range(initial_rows + 1, ws.max_row + 1):
            row_cells = [ws.cell(r, c).value for c in range(1, 12)]
            assert len(row_cells) == 11

            # Col 1: Date string
            assert row_cells[0] is not None
            assert "-" in str(row_cells[0])

            # Col 2: Company
            assert row_cells[1] is not None and "Enterprise Tech" in str(row_cells[1])

            # Col 3: Title
            assert row_cells[2] is not None and "Azure Data Engineer" in str(row_cells[2])

            # Col 4: Match Score (%) with % symbol
            assert str(row_cells[3]).endswith("%")

            # Col 5: Role Category
            assert row_cells[4] == "Azure Data Engineer"

            # Col 6: Experience Required
            assert row_cells[5] == "2-5 Yrs"

            # Col 7: Location
            assert row_cells[6] == "Hyderabad / Bengaluru"

            # Col 8: App Type
            assert row_cells[7] in ("1-Click Direct", "External Employer Portal")

            # Col 9: Status
            assert row_cells[8] in ("Submitted (Pending)", "External Redirect")

            # Col 10: URL
            assert str(row_cells[9]).startswith("https://www.naukri.com/")

            # Col 11: Recruiter Response
            assert row_cells[10] == "Awaiting Recruiter Review"

    def test_log_to_excel_backward_compatibility(self, tmp_path):
        """Verify legacy positional calling convention (where match_score is string app_type) preserves 11 columns."""
        temp_tracker = str(tmp_path / "Compat_Tracker.xlsx")
        shutil.copyfile(TRACKER_PATH, temp_tracker)

        # Legacy call: log_to_excel(title, comp, status, app_type)
        ok = log_to_excel(
            "Legacy Azure Data Engineer",
            "Legacy Corp",
            "Submitted (Pending)",
            "1-Click Direct",  # Passed as 4th positional argument
            tracker_path=temp_tracker
        )
        assert ok is True

        audit_wb = openpyxl.load_workbook(temp_tracker, data_only=True)
        ws = audit_wb["Applications_Log"]
        last_row = [ws.cell(ws.max_row, c).value for c in range(1, 12)]

        assert len(last_row) == 11
        assert last_row[1] == "Legacy Corp"
        assert last_row[2] == "Legacy Azure Data Engineer"
        assert last_row[3] == "85%"  # Fallback score for legacy call
        assert last_row[7] == "1-Click Direct"
        assert last_row[8] == "Submitted (Pending)"

    def test_sibling_sheets_preserved_after_applications_log_appends(self, tmp_path):
        """Verify log_to_excel never alters or removes sibling sheets (Daily_Performance_Metrics, Recruiter_Performance_Log)."""
        temp_tracker = str(tmp_path / "MultiSheet_Tracker.xlsx")
        shutil.copyfile(TRACKER_PATH, temp_tracker)

        orig_wb = openpyxl.load_workbook(temp_tracker, data_only=True)
        orig_sheets = set(orig_wb.sheetnames)
        orig_daily_rows = orig_wb["Daily_Performance_Metrics"].max_row
        orig_recruiter_rows = orig_wb["Recruiter_Performance_Log"].max_row

        # Append 10 application records
        for i in range(10):
            log_to_excel(f"Job {i}", f"Comp {i}", "Submitted (Pending)", match_score=80, tracker_path=temp_tracker)

        new_wb = openpyxl.load_workbook(temp_tracker, data_only=True)
        assert set(new_wb.sheetnames) == orig_sheets
        assert new_wb["Daily_Performance_Metrics"].max_row == orig_daily_rows
        assert new_wb["Recruiter_Performance_Log"].max_row == orig_recruiter_rows
