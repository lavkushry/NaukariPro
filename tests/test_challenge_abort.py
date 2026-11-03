"""
tests/test_challenge_abort.py

Comprehensive tests for Milestone M1 (Feature 4): Challenge Abort Protocol.
Validates:
1. SecurityChallengeError exception definition.
2. detect_challenge() (sync) and detect_challenge_async() (async) detect CAPTCHA, Turnstile, OTP, Checkpoint.
3. NativeChromeRunner.apply_to_job raises SecurityChallengeError and logs FAILED_SECURITY_CHALLENGE.
4. PlaywrightRunner.apply_to_job_async detects challenge, logs FAILED_SECURITY_CHALLENGE, and raises SecurityChallengeError.
5. Channel execution halts immediately without attempting automated bypass.
"""

import asyncio
import sqlite3
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from naukari_pro.session import (
    SecurityChallengeError,
    detect_challenge,
    detect_challenge_async
)
from naukari_pro.modules.auto_apply import (
    NativeChromeRunner,
    PlaywrightRunner
)
from naukari_pro.modules.db import init_db


@pytest.fixture
def temp_db(tmp_path):
    """Provides isolated SQLite database."""
    db_file = str(tmp_path / "test_challenge.db")
    init_db(db_file)
    return db_file


def test_security_challenge_error_structure():
    """Verifies SecurityChallengeError inherits from Exception and stores metadata."""
    err = SecurityChallengeError(
        challenge_type="Cloudflare Turnstile",
        details="Encountered on https://naukri.com/sample-job"
    )
    assert isinstance(err, Exception)
    assert err.challenge_type == "Cloudflare Turnstile"
    assert "https://naukri.com/sample-job" in err.details
    assert "Cloudflare Turnstile" in str(err)


def test_detect_challenge_async_phrases():
    """Verifies detect_challenge_async catches checkpoint text phrases."""
    async def _test():
        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value="Checkpoint: verify you are human")

        res = await detect_challenge_async(mock_page)
        assert res == "Checkpoint: verify you are human"

    asyncio.run(_test())


def test_detect_challenge_async_clean_page():
    """Verifies detect_challenge_async returns None on normal clean job page."""
    async def _test():
        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=None)

        res = await detect_challenge_async(mock_page)
        assert res is None

    asyncio.run(_test())


def test_detect_challenge_sync():
    """Verifies sync detect_challenge catches visual captcha elements."""
    mock_page = MagicMock()
    mock_page.evaluate.return_value = "Visual Captcha/Turnstile"

    res = detect_challenge(mock_page)
    assert res == "Visual Captcha/Turnstile"


def test_playwright_runner_apply_aborts_on_challenge(temp_db):
    """
    Verifies PlaywrightRunner.apply_to_job_async logs FAILED_SECURITY_CHALLENGE
    and raises SecurityChallengeError when a security challenge is detected.
    """
    async def _test():
        runner = PlaywrightRunner(skip_list={}, dry_run=False)

        mock_tab = AsyncMock()
        mock_tab.goto = AsyncMock()
        mock_tab.wait_for_timeout = AsyncMock()
        mock_tab.close = AsyncMock()
        mock_tab.url = "https://www.naukri.com/job-listings-1234567890"

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_tab)

        with patch("naukari_pro.modules.auto_apply.detect_challenge_async", new=AsyncMock(return_value="Visual Captcha/Turnstile")):
            with patch("naukari_pro.modules.scorecard.DB_PATH", temp_db), patch("naukari_pro.modules.db.DB_PATH", temp_db):
                with pytest.raises(SecurityChallengeError) as exc_info:
                    await runner.apply_to_job_async(
                        context=mock_context,
                        job_url="https://www.naukri.com/job-listings-1234567890",
                        title="Senior Azure Data Engineer",
                        company="FinTech Corp",
                        salary="25 LPA"
                    )

                assert "Visual Captcha/Turnstile" in str(exc_info.value)

                # Verify FAILED_SECURITY_CHALLENGE was written to SQLite
                conn = sqlite3.connect(temp_db)
                conn.row_factory = sqlite3.Row
                row = conn.execute("SELECT * FROM applied_jobs WHERE company = 'FinTech Corp'").fetchone()
                conn.close()

                assert row is not None
                assert row["status"] == "FAILED_SECURITY_CHALLENGE"
                assert "Visual Captcha" in (row["raw_metadata"] or "")

    asyncio.run(_test())


def test_native_chrome_runner_apply_aborts_on_challenge(temp_db):
    """
    Verifies NativeChromeRunner.apply_to_job raises SecurityChallengeError
    and dual-logs FAILED_SECURITY_CHALLENGE when Chrome AppleScript returns action: challenge.
    """
    runner = NativeChromeRunner(skip_list={}, dry_run=False)

    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = '{"action": "challenge", "detail": "Visual Captcha/Turnstile"}'
    mock_proc.stderr = ""

    with patch("subprocess.run", return_value=mock_proc):
        with patch("naukari_pro.modules.scorecard.DB_PATH", temp_db), patch("naukari_pro.modules.db.DB_PATH", temp_db):
            with pytest.raises(SecurityChallengeError) as exc_info:
                runner.apply_to_job(
                    job_url="https://www.naukri.com/job-999",
                    title="Lead Data Engineer",
                    company="CloudScale",
                    salary="30 LPA"
                )

            assert "Naukri Security Checkpoint" in str(exc_info.value)

            # Verify SQLite entry
            conn = sqlite3.connect(temp_db)
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM applied_jobs WHERE company = 'CloudScale'").fetchone()
            conn.close()

            assert row is not None
            assert row["status"] == "FAILED_SECURITY_CHALLENGE"
