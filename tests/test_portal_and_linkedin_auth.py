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


def test_interactive_login_async_autofill_and_persist():
    import asyncio
    async def _test():
        with tempfile.TemporaryDirectory() as td:
            cookie_file = os.path.join(td, "session_cookies.json")
            env_file = os.path.join(td, ".env")
            with open(env_file, "w") as f:
                f.write('EXISTING="yes"\n')

            with patch("naukari_pro.modules.linkedin_session.WORKSPACE_DIR", td), \
                 patch.dict(os.environ, {"LINKEDIN_EMAIL": "test@example.com", "LINKEDIN_PASSWORD": "SecretPassword123"}):

                mgr = LinkedInSessionManager(cookie_path=cookie_file)

                # Mock Async Playwright components
                mock_user_input = MagicMock()
                mock_user_input.is_visible = MagicMock(return_value=True)
                mock_user_input.input_value = MagicMock(return_value="")
                mock_user_input.fill = MagicMock()

                async def async_ret(val):
                    return val

                mock_user_input.is_visible = lambda timeout=None: async_ret(True)
                mock_user_input.input_value = lambda: async_ret("")
                mock_user_input.fill = lambda val: async_ret(None)

                mock_pass_input = MagicMock()
                mock_pass_input.is_visible = lambda timeout=None: async_ret(True)
                mock_pass_input.input_value = lambda: async_ret("")
                mock_pass_input.fill = lambda val: async_ret(None)

                mock_submit_btn = MagicMock()
                mock_submit_btn.is_visible = lambda timeout=None: async_ret(True)
                mock_submit_btn.click = lambda: async_ret(None)

                mock_nav = MagicMock()
                mock_nav.count = lambda: async_ret(1)

                def mock_locator(selector):
                    if "#username" in selector or "session_key" in selector:
                        return MagicMock(first=mock_user_input)
                    elif "#password" in selector or "session_password" in selector:
                        return MagicMock(first=mock_pass_input)
                    elif "button[type='submit']" in selector or "sign-in-form__submit-btn" in selector:
                        return MagicMock(first=mock_submit_btn)
                    elif ".global-nav" in selector:
                        return MagicMock(first=mock_nav)
                    return MagicMock(first=MagicMock(count=lambda: async_ret(0), is_visible=lambda: async_ret(False)))

                mock_page = MagicMock()
                mock_page.goto = lambda url, **kwargs: async_ret(None)
                mock_page.locator = mock_locator
                mock_page.url = "https://www.linkedin.com/feed/"

                mock_context = MagicMock()
                mock_context.new_page = lambda: async_ret(mock_page)
                mock_context.cookies = lambda urls: async_ret([
                    {"name": "li_at", "value": "AQED_NEW_FRESH_TOKEN_999"},
                    {"name": "JSESSIONID", "value": "ajax:99999"}
                ])

                mock_browser = MagicMock()
                mock_browser.new_context = lambda **kwargs: async_ret(mock_context)
                mock_browser.close = lambda: async_ret(None)

                mock_playwright = MagicMock()
                mock_playwright.chromium.launch = lambda **kwargs: async_ret(mock_browser)

                class MockAsyncPWContext:
                    async def __aenter__(self):
                        return mock_playwright
                    async def __aexit__(self, exc_type, exc_val, exc_tb):
                        pass

                with patch("playwright.async_api.async_playwright", return_value=MockAsyncPWContext()):
                    res = await mgr.interactive_login_async(timeout_seconds=5, headless=True)

                assert res["status"] == "VALID"
                assert res["authenticated"] is True
                assert res["li_at"] == "AQED_NEW_FRESH_TOKEN_999"

                # Verify saved cookies
                assert os.path.exists(cookie_file)
                # Verify .env updated
                with open(env_file) as f:
                    env_text = f.read()
                assert "AQED_NEW_FRESH_TOKEN_999" in env_text

    asyncio.run(_test())


def test_run_apply_cycle_auto_login_on_expired_token():
    import asyncio
    async def _test():
        from naukari_pro.modules.linkedin_apply import LinkedInApplyEngine

        mock_session_mgr = MagicMock()
        # 1st verify -> EXPIRED, 2nd verify (after login) -> VALID
        verify_results = [
            {"status": "EXPIRED", "authenticated": False, "detail": "Session cookie rejected"},
            {"status": "VALID", "authenticated": True, "candidate_name": "Lavkush Kumar"}
        ]
        async def mock_verify(page, raise_for_status=False):
            return verify_results.pop(0) if verify_results else {"status": "VALID", "authenticated": True}

        mock_session_mgr.verify_session = mock_verify

        async def mock_interactive_login(timeout_seconds=180, headless=False):
            return {"status": "VALID", "authenticated": True, "li_at": "AQED_FRESH_123"}

        mock_session_mgr.interactive_login_async = mock_interactive_login

        mock_lock = MagicMock()
        mock_lock.acquire.return_value = True
        mock_lock.release.return_value = None
        mock_session_mgr.get_lock.return_value = mock_lock

        mock_page = MagicMock()
        mock_context = MagicMock()
        mock_context.pages = [mock_page]

        async def async_ret(val=None):
            return val

        mock_context.close = lambda: async_ret(None)
        mock_session_mgr.create_stealth_context = lambda p, headless=True: async_ret(mock_context)

        mock_search = MagicMock()
        mock_search.search_jobs = lambda **kwargs: async_ret([])

        engine = LinkedInApplyEngine(session_manager=mock_session_mgr, search_engine=mock_search)

        class MockAsyncPW:
            async def __aenter__(self):
                return MagicMock()
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        with patch("playwright.async_api.async_playwright", return_value=MockAsyncPW()), \
             patch("sys.platform", "darwin"):
            stats = await engine.run_apply_cycle(limit=5, dry_run=False, headless=True)

        # Successfully renewed and ran discovery without halting on EXPIRED
        assert stats["status"] != "FAILED"
        assert stats["discovered"] == 0

    asyncio.run(_test())
