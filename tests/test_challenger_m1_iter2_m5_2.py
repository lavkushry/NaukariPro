"""
Comprehensive Empirical Adversarial Challenge Suite: Milestone 1 Iteration 2 (m5_2)
Authored by Challenger 2 (teamwork_preview_challenger_m1_iter2_m5_2)

Mission Objectives:
1. Lock safety on missing cookie:
   - Simulate LinkedInCookieMissingError during create_stealth_context.
   - Assert lock._acquired is False and the lock file is released/unheld.
   - Assert pre-existing lock file on disk remains unheld and immediately acquirable.
   - Assert launch failure, init_script failure, and add_cookies failure release lock.
   - Assert normal context.close() releases lock via callback.
2. CLI async handler:
   - Test ./naukariPro linkedin-verify real subprocess execution with simulated:
     * VALID session -> exact exit code 0
     * CHECKPOINT session -> exact exit code 2
     * EXPIRED session -> exact exit code 1
     * COOKIE_MISSING session -> exact exit code 1
     * UNREACHABLE session -> exact exit code 1
   - Assert zero event loop collisions across repeated invocations.
   - Verify argument parsing (--headed vs headless).
3. Token sanitization fuzzing:
   - Nested and mixed quotes convergence stripping.
   - Whitespace stripping (tabs, newlines, unicode non-breaking space).
   - Inline comment stripping in .env (single #, multiple #, export prefix).
   - Non-ASCII, Unicode, emoji, and extreme boundary strings.
   - Masking length thresholds and formatting.
"""

import os
import sys
import tempfile
import subprocess
import asyncio
import functools
from unittest.mock import MagicMock, AsyncMock, patch
import pytest

from naukari_pro.modules.linkedin_session import (
    LinkedInSessionManager,
    LinkedInError,
    LinkedInSessionError,
    LinkedInCookieMissingError,
    LinkedInCookieExpiredError,
    LinkedInCheckpointError,
    sanitize_cookie_token,
    mask_cookie_token
)
from naukari_pro.session import SessionLock
from naukari_pro.cli import handle_linkedin_verify
from tests.test_linkedin_suite import (
    make_mock_page,
    make_mock_locator,
    make_playwright_cm_mock
)


def run_async(coro):
    @functools.wraps(coro)
    def wrapper(*args, **kwargs):
        return asyncio.run(coro(*args, **kwargs))
    return wrapper


# ==============================================================================
# SECTION 1: EMPIRICAL ADVERSARIAL CHALLENGES — LOCK SAFETY & LIFECYCLE
# ==============================================================================

@run_async
async def test_adversarial_lock_safety_missing_cookie_raises_and_lock_unacquired(tmp_path, monkeypatch):
    """
    Challenge 1.1: Missing cookie during create_stealth_context must raise
    LinkedInCookieMissingError and strictly ensure lock._acquired is False.
    """
    monkeypatch.delenv("LINKEDIN_LI_AT", raising=False)
    monkeypatch.delenv("LI_AT", raising=False)
    monkeypatch.setenv("WORKSPACE_DIR", str(tmp_path))

    session_dir = str(tmp_path / "browser_session")
    lock_path = str(tmp_path / ".linkedin_session.lock")
    cookie_path = str(tmp_path / "nonexistent_cookies.json")

    manager = LinkedInSessionManager(
        session_dir=session_dir,
        cookie_path=cookie_path,
        lock_path=lock_path
    )
    lock = manager.get_lock()
    assert lock._acquired is False

    with pytest.raises(LinkedInCookieMissingError):
        await manager.create_stealth_context(p=None)

    # Lock must remain completely unacquired
    assert lock._acquired is False
    assert lock._file_obj is None

    # Verify that another process can acquire the lock without blocking
    independent_lock = SessionLock(session_dir=str(tmp_path), lock_filename=".linkedin_session.lock", timeout_sec=0.5)
    assert independent_lock.acquire(blocking=False) is True
    assert independent_lock._acquired is True
    independent_lock.release()


@run_async
async def test_adversarial_lock_safety_existing_file_unheld_on_missing_cookie(tmp_path, monkeypatch):
    """
    Challenge 1.2: When lock file already exists on disk, missing cookie error
    must NOT leave an open flock handle or block other processes.
    """
    monkeypatch.delenv("LINKEDIN_LI_AT", raising=False)
    monkeypatch.delenv("LI_AT", raising=False)
    monkeypatch.setenv("WORKSPACE_DIR", str(tmp_path))

    lock_path = str(tmp_path / ".linkedin_session.lock")
    with open(lock_path, "w", encoding="utf-8") as f:
        f.write("pid=88888\ntime=2026-10-26 00:00:00\n")

    manager = LinkedInSessionManager(
        session_dir=str(tmp_path / "session"),
        cookie_path=str(tmp_path / "nonexistent.json"),
        lock_path=lock_path
    )
    lock = manager.get_lock()

    with pytest.raises(LinkedInCookieMissingError):
        await manager.create_stealth_context(p=None)

    assert lock._acquired is False
    assert lock._file_obj is None

    # Assert another lock can acquire the pre-existing file without blocking
    other_lock = SessionLock(session_dir=str(tmp_path), lock_filename=".linkedin_session.lock", timeout_sec=0.5)
    assert other_lock.acquire(blocking=False) is True
    other_lock.release()


@pytest.mark.parametrize("failure_stage", ["launch", "init_script", "add_cookies"])
@run_async
async def test_adversarial_lock_released_on_any_creation_failure(failure_stage, tmp_path, monkeypatch):
    """
    Challenge 1.3: If browser launch, script injection, or cookie addition fails
    after lock acquisition, lock MUST be released and _acquired set to False.
    """
    monkeypatch.setenv("LINKEDIN_LI_AT", "AQEDAQ_VALID_FOR_LOCK_TEST")

    session_dir = str(tmp_path / f"session_{failure_stage}")
    lock_path = str(tmp_path / f".lock_{failure_stage}")

    manager = LinkedInSessionManager(
        session_dir=session_dir,
        lock_path=lock_path
    )
    lock = manager.get_lock()

    mock_pw = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.on = MagicMock()
    mock_ctx.close = AsyncMock()

    if failure_stage == "launch":
        mock_pw.chromium.launch_persistent_context = MagicMock(side_effect=RuntimeError("Chromium binary missing"))
    elif failure_stage == "init_script":
        mock_ctx.add_init_script = AsyncMock(side_effect=RuntimeError("Script injection aborted"))
        mock_pw.chromium.launch_persistent_context = MagicMock(return_value=mock_ctx)
    elif failure_stage == "add_cookies":
        mock_ctx.add_init_script = AsyncMock()
        mock_ctx.add_cookies = AsyncMock(side_effect=RuntimeError("Cookie rejected by domain"))
        mock_pw.chromium.launch_persistent_context = MagicMock(return_value=mock_ctx)

    with pytest.raises(RuntimeError):
        await manager.create_stealth_context(mock_pw)

    # Lock must be released
    assert lock._acquired is False
    assert lock._file_obj is None

    # Context close must have been attempted if context was created
    if failure_stage in ["init_script", "add_cookies"]:
        assert mock_ctx.close.called

    # Another process can immediately acquire lock
    other_lock = SessionLock(session_dir=str(tmp_path), lock_filename=f".lock_{failure_stage}", timeout_sec=0.5)
    assert other_lock.acquire(blocking=False) is True
    other_lock.release()


@run_async
async def test_adversarial_normal_context_close_releases_lock(tmp_path, monkeypatch):
    """
    Challenge 1.4: Normal context.close() triggers callback and releases session lock.
    """
    monkeypatch.setenv("LINKEDIN_LI_AT", "AQEDAQ_TOKEN")

    manager = LinkedInSessionManager(
        session_dir=str(tmp_path / "session"),
        lock_path=str(tmp_path / ".lock")
    )
    lock = manager.get_lock()

    callbacks = {}
    mock_ctx = MagicMock()
    mock_ctx.on = MagicMock(side_effect=lambda evt, cb: callbacks.update({evt: cb}))
    mock_ctx.add_init_script = AsyncMock()
    mock_ctx.add_cookies = AsyncMock()

    async def mock_close():
        if "close" in callbacks:
            callbacks["close"]()

    mock_ctx.close = AsyncMock(side_effect=mock_close)
    mock_pw = MagicMock()
    mock_pw.chromium.launch_persistent_context = MagicMock(return_value=mock_ctx)

    context = await manager.create_stealth_context(mock_pw)
    assert lock._acquired is True

    await context.close()
    assert lock._acquired is False
    assert lock._file_obj is None

    # Another lock can acquire immediately
    other = SessionLock(session_dir=str(tmp_path), lock_filename=".lock", timeout_sec=0.5)
    assert other.acquire(blocking=False) is True
    other.release()


# ==============================================================================
# SECTION 2: EMPIRICAL ADVERSARIAL CHALLENGES — CLI ASYNC HANDLER & SUBPROCESS
# ==============================================================================

@pytest.mark.parametrize("sim_mode,expected_exit_code,expected_pattern", [
    ("VALID", 0, "Session Status:         VALID"),
    ("CHECKPOINT", 2, "Session Status:         CHECKPOINT"),
    ("EXPIRED", 1, "Session Status:         EXPIRED"),
    ("UNREACHABLE", 1, "Session Status:         UNREACHABLE"),
])
def test_adversarial_cli_subprocess_execution_exact_exit_codes(sim_mode, expected_exit_code, expected_pattern, tmp_path):
    """
    Challenge 2.1: Real subprocess execution of ./naukariPro linkedin-verify
    must yield exact exit codes (0 for VALID, 2 for CHECKPOINT, 1 for EXPIRED/UNREACHABLE).
    """
    sitecustomize_content = f'''
import os
from unittest.mock import MagicMock, AsyncMock
from naukari_pro.modules.linkedin_session import (
    LinkedInSessionManager,
    LinkedInCheckpointError,
    LinkedInCookieExpiredError
)

mode = os.environ.get("TEST_SIMULATE_MODE", "{sim_mode}")

async def mock_create_stealth_context(self, p, headless=True, proxy=None):
    ctx = MagicMock()
    ctx.pages = [MagicMock()]
    ctx.close = AsyncMock()
    return ctx

async def mock_verify_session(self, page, raise_for_status=False):
    if mode == "VALID":
        return {{
            "status": "VALID",
            "authenticated": True,
            "candidate_name": "Lavkush Kumar",
            "headline": "Azure Data Engineer | 2.5 YOE",
            "dom_verified": True,
            "feed_url": "https://www.linkedin.com/feed/"
        }}
    elif mode == "CHECKPOINT":
        raise LinkedInCheckpointError("Challenge encountered", "https://www.linkedin.com/checkpoint/challenge/999", "captcha")
    elif mode == "EXPIRED":
        raise LinkedInCookieExpiredError("Session expired", "https://www.linkedin.com/authwall")
    elif mode == "UNREACHABLE":
        raise TimeoutError("Navigation timeout of 30000ms exceeded")
    return {{"status": "UNKNOWN", "authenticated": False}}

LinkedInSessionManager.create_stealth_context = mock_create_stealth_context
LinkedInSessionManager.verify_session = mock_verify_session
'''
    sitecustomize_file = tmp_path / "sitecustomize.py"
    sitecustomize_file.write_text(sitecustomize_content, encoding="utf-8")

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{tmp_path}:{env.get('PYTHONPATH', '')}"
    env["TEST_SIMULATE_MODE"] = sim_mode
    env["LINKEDIN_LI_AT"] = "AQEDAQ_REAL_SUBPROCESS_TEST_TOKEN_12345"

    proc = subprocess.run(
        ["./naukariPro", "linkedin-verify"],
        env=env,
        capture_output=True,
        text=True,
        timeout=15
    )

    assert proc.returncode == expected_exit_code, (
        f"Mode {sim_mode} returned code {proc.returncode}, expected {expected_exit_code}.\n"
        f"Stdout:\n{proc.stdout}\nStderr:\n{proc.stderr}"
    )
    assert expected_pattern in proc.stdout


def test_adversarial_cli_subprocess_missing_cookie_exit_code_1():
    """
    Challenge 2.2: Real subprocess execution of ./naukariPro linkedin-verify with
    no cookie in environment or files must exit with code 1.
    """
    env = os.environ.copy()
    env.pop("LINKEDIN_LI_AT", None)
    env.pop("LI_AT", None)
    env["WORKSPACE_DIR"] = "/nonexistent/test_workspace"

    # Patch workspace .env reading by pointing to nonexistent env
    proc = subprocess.run(
        ["./naukariPro", "linkedin-verify"],
        env=env,
        capture_output=True,
        text=True,
        timeout=15
    )

    # Either missing cookie (if .env doesn't have token) or runs verify
    # Since workspace .env has no active LINKEDIN_LI_AT, it returns exit code 1
    assert proc.returncode == 1
    assert "COOKIE_MISSING" in proc.stdout or "Cookie Present:         NO" in proc.stdout


def test_adversarial_cli_sequential_calls_no_event_loop_collision(capsys, monkeypatch):
    """
    Challenge 2.3: Multiple consecutive calls to handle_linkedin_verify must execute
    cleanly without event loop collisions or state leakage.
    """
    monkeypatch.setenv("LINKEDIN_LI_AT", "AQEDAQ_CONSECUTIVE_TOKEN")

    name_loc = make_mock_locator(count=1, visible=True, text="Lavkush Kumar")
    nav_loc = make_mock_locator(count=1, visible=True, text="")
    mock_page = make_mock_page(
        current_url="https://www.linkedin.com/feed/",
        locators={
            "div.feed-identity-module__actor-meta a span": name_loc,
            "nav.global-nav": nav_loc,
            "div.feed-identity-module": name_loc
        }
    )
    pw_mock = make_playwright_cm_mock(page=mock_page)

    with patch("naukari_pro.cli.async_playwright", pw_mock), \
         patch("naukari_pro.cli.sync_playwright", pw_mock):

        for i in range(5):
            code = handle_linkedin_verify(headless=True)
            assert code == 0, f"Sequential run {i} failed with code {code}"

        out = capsys.readouterr().out
        assert out.count("Session Status:         VALID") == 5


def test_adversarial_cli_headed_flag_propagation(monkeypatch):
    """
    Challenge 2.4: handle_linkedin_verify respects args.headed and toggles headless appropriately.
    """
    monkeypatch.setenv("LINKEDIN_LI_AT", "AQEDAQ_TOKEN")

    mock_page = make_mock_page(current_url="https://www.linkedin.com/feed/")
    pw_mock = make_playwright_cm_mock(page=mock_page)

    class Args:
        headed = True

    with patch("naukari_pro.cli.async_playwright", pw_mock), \
         patch("naukari_pro.modules.linkedin_session.LinkedInSessionManager.create_stealth_context", new_callable=AsyncMock) as mock_create, \
         patch("naukari_pro.modules.linkedin_session.LinkedInSessionManager.verify_session", new_callable=AsyncMock) as mock_verify:

        mock_create.return_value = MagicMock(pages=[mock_page], close=AsyncMock())
        mock_verify.return_value = {"status": "VALID", "authenticated": True, "candidate_name": "Lavkush Kumar"}

        handle_linkedin_verify(Args())
        assert mock_create.call_args[1]["headless"] is False


# ==============================================================================
# SECTION 3: EMPIRICAL ADVERSARIAL CHALLENGES — TOKEN SANITIZATION FUZZING
# ==============================================================================

@pytest.mark.parametrize("fuzz_input,expected_output", [
    # Quotes fuzzing
    ('"token"', "token"),
    ("'token'", "token"),
    ('\'"token"\'', "token"),
    ('"\'token\'"', "token"),
    ('"""token"""', "token"),
    ("'''token'''", "token"),
    ('\'"\'"\'"token"\'"\'"\'', "token"),
    ('"token', "token"),
    ('token"', "token"),
    ("'token", "token"),
    ("token'", "token"),
    ('""', None),
    ("''", None),
    ('"""\'\'\'', None),

    # Whitespace fuzzing
    ("   token   ", "token"),
    ("\t\ttoken\t\t", "token"),
    ("\r\n\t token \t\r\n", "token"),
    ("  '  \"  token  \"  '  ", "token"),
    (" \u00a0 token \u00a0 ", "token"),  # Unicode non-breaking space
    ("   ", None),
    ("\t\r\n", None),
    ("", None),
    (None, None),

    # Raw / Escape combinations: backslashes are not stripped by quote stripper
    ('\\"token\\"', '\\"token\\'),
])
def test_adversarial_fuzz_token_sanitization_core(fuzz_input, expected_output):
    """
    Challenge 3.1: Fuzz test sanitize_cookie_token with permutations of quotes and whitespace.
    """
    result = sanitize_cookie_token(fuzz_input)
    assert result == expected_output, f"Input {repr(fuzz_input)} produced {repr(result)}, expected {repr(expected_output)}"


@pytest.mark.parametrize("env_line,expected_token", [
    ("LINKEDIN_LI_AT=AQEDAQ_STANDARD_TOKEN", "AQEDAQ_STANDARD_TOKEN"),
    ('export LINKEDIN_LI_AT="AQEDAQ_QUOTED_TOKEN"', "AQEDAQ_QUOTED_TOKEN"),
    ("LI_AT='AQEDAQ_SINGLE_QUOTED'", "AQEDAQ_SINGLE_QUOTED"),
    ("export LI_AT=AQEDAQ_NO_QUOTES # inline comment", "AQEDAQ_NO_QUOTES"),
    ('LINKEDIN_LI_AT="AQEDAQ_COMMENTED" # with comment after quote', "AQEDAQ_COMMENTED"),
    ("LINKEDIN_LI_AT=AQEDAQ_NOSPACE#comment_immediately_adjacent", "AQEDAQ_NOSPACE"),
    ('export LINKEDIN_LI_AT="AQEDAQ_MULTI_HASH" # comment 1 # comment 2', "AQEDAQ_MULTI_HASH"),
    ("LINKEDIN_LI_AT=AQEDAQ_EMPTY_COMMENT #", "AQEDAQ_EMPTY_COMMENT"),
    ('LINKEDIN_LI_AT="   AQEDAQ_SPACED_QUOTED   " # trailing comment', "AQEDAQ_SPACED_QUOTED"),
    ('LINKEDIN_LI_AT="" # empty token comment', None),
    ("LINKEDIN_LI_AT=   # whitespace only", None),
])
def test_adversarial_fuzz_env_inline_comments(env_line, expected_token, tmp_path, monkeypatch):
    """
    Challenge 3.2: Fuzz test .env file reading with various inline comment patterns.
    """
    env_file = tmp_path / ".env"
    env_file.write_text(f"{env_line}\n", encoding="utf-8")

    manager = LinkedInSessionManager(cookie_path=str(tmp_path / "none.json"))

    with patch("naukari_pro.modules.linkedin_session.WORKSPACE_DIR", str(tmp_path)), \
         patch.dict(os.environ, {}, clear=True):

        if expected_token is None:
            with pytest.raises(LinkedInCookieMissingError):
                manager.get_li_at_cookie(raise_if_missing=True)
        else:
            token = manager.get_li_at_cookie(raise_if_missing=True)
            assert token == expected_token, f"Line '{env_line}' yielded token '{token}', expected '{expected_token}'"


@pytest.mark.parametrize("token_input,expected_mask", [
    (None, "None"),
    ("", "None"),
    ("   ", "None"),
    ("1", "****"),
    ("12345678", "****"),
    ("123456789", "1234...6789 (9 chars, masked)"),
    ("AQEDAQ_LONG_SESSION_TOKEN_XYZ", "AQED..._XYZ (29 chars, masked)"),
    ('  "  AQEDAQ_QUOTED_TOKEN  "  ', "AQED...OKEN (19 chars, masked)"),
    ("AQEDAQ_🔥_EMOJI", "AQED...MOJI (14 chars, masked)"),
])
def test_adversarial_fuzz_masking(token_input, expected_mask):
    """
    Challenge 3.3: Fuzz test mask_cookie_token across boundary lengths and formats.
    """
    assert mask_cookie_token(token_input) == expected_mask


def test_adversarial_fuzz_extreme_length_and_types():
    """
    Challenge 3.4: Extreme string length (100k chars) and non-string types.
    """
    huge_token = "A" * 100000
    assert sanitize_cookie_token(f'  "{huge_token}"  ') == huge_token
    assert len(mask_cookie_token(huge_token)) > 10

    # Numeric and boolean inputs
    assert sanitize_cookie_token(123456789) == "123456789"
    assert sanitize_cookie_token(True) == "True"


def test_adversarial_format_cookie_schema(monkeypatch):
    """
    Challenge 3.5: Playwright cookie dictionary schema verification.
    """
    manager = LinkedInSessionManager()
    cookie = manager.format_cookie('  "  AQEDAQ_TOKEN_123  "  ')

    assert cookie["name"] == "li_at"
    assert cookie["value"] == "AQEDAQ_TOKEN_123"
    assert cookie["domain"] == ".linkedin.com"
    assert cookie["path"] == "/"
    assert cookie["httpOnly"] is True
    assert cookie["secure"] is True
    assert cookie["sameSite"] == "Lax"
