"""
Tests for:
1. LinkedIn authentication persistence (set_li_at_token, update_env_variable).
2. CareerPortalFiller Hard Stop 2 (Closed/Expired expJD detection).
3. Dynamic ATS vacancy discovery (fetch_live_ats_vacancies).
"""

import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch

from naukari_pro.modules.linkedin_session import update_env_variable, LinkedInSessionManager
from naukari_pro.modules.career_portals import CareerPortalFiller, fetch_live_ats_vacancies, ExternalPortalBatchRunner


def test_update_env_variable_existing_and_new():
    with tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8") as tf:
        tf.write('EXISTING_VAR="hello"\nLINKEDIN_LI_AT="old_token"\nOTHER="123"\n')
        tf_path = tf.name

    try:
        # Update existing
        ok = update_env_variable("LINKEDIN_LI_AT", "fresh_token_xyz", env_path=tf_path)
        assert ok is True
        with open(tf_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert 'LINKEDIN_LI_AT="fresh_token_xyz"' in content
        assert 'EXISTING_VAR="hello"' in content
        assert 'OTHER="123"' in content

        # Append new
        ok2 = update_env_variable("NEW_SECRET", "super_secret_val", env_path=tf_path)
        assert ok2 is True
        with open(tf_path, "r", encoding="utf-8") as f:
            content2 = f.read()
        assert 'NEW_SECRET="super_secret_val"' in content2
    finally:
        if os.path.exists(tf_path):
            os.remove(tf_path)


def test_set_li_at_token_sync():
    with tempfile.TemporaryDirectory() as td:
        cookie_file = os.path.join(td, "session_cookies.json")
        env_file = os.path.join(td, ".env")
        with open(env_file, "w") as f:
            f.write('FOO="bar"\n')

        with patch("naukari_pro.modules.linkedin_session.WORKSPACE_DIR", td):
            mgr = LinkedInSessionManager(cookie_path=cookie_file)
            test_token = "AQED_TEST_TOKEN_1234567890"
            ok = mgr.set_li_at_token(test_token, jsessionid="ajax:12345")
            assert ok is True

            # Verify in .env
            with open(env_file, "r") as f:
                env_text = f.read()
            assert test_token in env_text

            # Verify in session_cookies.json
            assert os.path.exists(cookie_file)
            with open(cookie_file, "r") as f:
                raw_json = f.read()
            assert test_token in raw_json
            assert "ajax:12345" in raw_json


def test_fetch_live_ats_vacancies_schema():
    mock_gh_response = {
        "jobs": [
            {
                "title": "Lead Cloud Data Engineer",
                "absolute_url": "https://job-boards.greenhouse.io/gitlab/jobs/99901",
                "location": {"name": "Remote"},
                "content": "<p>Real greenhouse JD</p>",
            },
            {
                "title": "Sales Representative", # Should be filtered out by keywords
                "absolute_url": "https://job-boards.greenhouse.io/gitlab/jobs/99902",
                "location": {"name": "Remote"}
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_gh_response

    with patch("requests.get", return_value=mock_resp), patch(
        "requests.post", return_value=mock_resp
    ):
        # POST used for Workday; return empty postings
        mock_resp.json.return_value = mock_gh_response
        vacancies = fetch_live_ats_vacancies(limit=5)
        assert len(vacancies) >= 1
        v = vacancies[0]
        assert "Data Engineer" in v["title"]
        assert v["ats"] == "Greenhouse"
        assert v["url"] == "https://job-boards.greenhouse.io/gitlab/jobs/99901"
        # Keys present but unfetched values must be NULL (honest metadata)
        assert "exp" in v and v["exp"] is None
        assert "salary" in v and v["salary"] is None
        assert v["jd"] == "<p>Real greenhouse JD</p>"


def test_hard_stop_2_expired_job_detection():
    filler = CareerPortalFiller()

    # Create dummy workbook
    import openpyxl
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tf:
        tf_path = tf.name

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Applications_Log"
    ws.append(["Date", "Company", "Title", "Score", "Sal", "Exp", "Loc", "Type", "Status", "URL", "Notes"])
    # Expired row
    ws.append(["2026-10-22", "OldCo", "Old Role", "85%", "25 LPA", "2-5 Yrs", "Remote", "Portal", "External Redirect", "https://www.naukri.com/job-listings-old-1234", "Pending"])
    wb.save(tf_path)

    mock_page = MagicMock()
    # Simulate redirection to expJD=true
    mock_page.url = "https://www.naukri.com/data-engineer-jobs?expJD=true"
    mock_page.content.return_value = "<html><body>The job you are looking for is no longer active</body></html>"

    mock_context = MagicMock()
    mock_context.pages = [mock_page]

    with patch("naukari_pro.modules.career_portals.TRACKER_PATH", tf_path), \
         patch("naukari_pro.modules.career_portals.sync_dual_log") as mock_dual_log, \
         patch("playwright.sync_api.sync_playwright") as mock_pw:

        mock_pw_inst = MagicMock()
        mock_pw.return_value.__enter__.return_value = mock_pw_inst
        mock_pw_inst.chromium.launch.return_value.new_context.return_value = mock_context

        # Patch get_stealth_context
        with patch("naukari_pro.session.get_stealth_context", return_value=mock_context):
            res = filler.process_external_redirects(limit=5, headless=True, dry_run=False)

        assert res["skipped"] == 1
        assert res["submitted"] == 0

        # Verify Excel status was updated to SKIPPED_CLOSED_OR_EXPIRED
        wb_check = openpyxl.load_workbook(tf_path)
        ws_check = wb_check["Applications_Log"]
        assert ws_check.cell(row=2, column=9).value == "SKIPPED_CLOSED_OR_EXPIRED"

        # Verify SQLite dual log was invoked
        mock_dual_log.assert_called_with(
            title="Old Role",
            company="OldCo",
            platform="career_portal",
            status="SKIPPED_CLOSED_OR_EXPIRED",
            job_url="https://www.naukri.com/job-listings-old-1234",
            match_score=85.0,
            experience_req="2-5 Yrs",
            error_reason="Job expired on source platform (expJD=true)"
        )

    if os.path.exists(tf_path):
        os.remove(tf_path)
