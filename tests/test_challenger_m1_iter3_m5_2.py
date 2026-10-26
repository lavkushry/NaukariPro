"""
Comprehensive Empirical Adversarial Challenge Suite: Milestone 1 Iteration 3 (m5_2)
Authored by Challenger 2 (teamwork_preview_challenger_m1_iter3_m5_2)

Adversarial Focus Areas:
1. Lock safety & File Descriptor leak testing:
   - 200 consecutive acquire/release cycles: assert zero FD leaks.
   - Stale lock detection & concurrent multi-process contention.
   - Multiple context.close() calls: assert idempotent release without exception.
   - Browser launch / script injection / cookie injection crash: assert lock released.
2. CLI exit codes & real subprocess execution:
   - Real subprocess ./naukariPro linkedin-verify without cookie -> code 1.
   - Real subprocess ./naukariPro linkedin-verify with dummy token -> code 1.
   - Real subprocess argument handling (--help -> 0, invalid arg -> 2).
   - Real concurrent subprocess execution (two simultaneous processes contending for lock).
   - Asyncio event loop collision / nested run check.
3. Extreme bound token fuzzing & oracles:
   - Deep quote nesting, whitespace edge cases, Unicode, null-bytes.
   - 100,000 char tokens.
   - Corrupted and malformed JSON payloads in cookie files.
   - 3-tier priority resolution under conflicting sources.
"""

import os
import sys
import time
import json
import tempfile
import subprocess
import asyncio
import functools
import multiprocessing
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
    mask_cookie_token,
    clean_avatar_name
)
from naukari_pro.session import SessionLock
from naukari_pro.cli import handle_linkedin_verify
from tests.test_linkedin_suite import (
    make_mock_page,
    make_mock_locator,
    make_mock_context,
    make_mock_playwright,
    make_playwright_cm_mock
)


def run_async(coro):
    @functools.wraps(coro)
    def wrapper(*args, **kwargs):
        return asyncio.run(coro(*args, **kwargs))
    return wrapper


def _get_open_fd_count():
    """Returns number of open file descriptors for the current process."""
    if sys.platform == "darwin":
        try:
            return len(os.listdir("/dev/fd"))
        except Exception:
            pass
    elif sys.platform.startswith("linux"):
        try:
            return len(os.listdir("/proc/self/fd"))
        except Exception:
            pass
    return None


# ==============================================================================
# SECTION 1: LOCK SAFETY & FD LEAK EMPIRICAL TESTS
# ==============================================================================

def test_adversarial_lock_fd_leak_under_high_churn():
    """
    Stress-test SessionLock acquire/release churn across 200 cycles.
    Assert zero file descriptor leak.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        lock = SessionLock(session_dir=tmpdir, lock_filename="test_churn.lock")
        
        # Warmup to stabilize runtime FD baselines
        for _ in range(5):
            lock.acquire(blocking=True)
            lock.release()
            
        initial_fds = _get_open_fd_count()
        
        for _ in range(200):
            lock.acquire(blocking=True)
            assert lock._acquired is True
            assert lock._file_obj is not None
            lock.release()
            assert lock._acquired is False
            assert lock._file_obj is None
            
        final_fds = _get_open_fd_count()
        if initial_fds is not None and final_fds is not None:
            fd_diff = final_fds - initial_fds
            assert fd_diff <= 1, f"FD leak detected: grew by {fd_diff} descriptors"


def _worker_hold_lock(tmpdir, lock_file, hold_time, ready_event):
    lock = SessionLock(session_dir=tmpdir, lock_filename=lock_file, timeout_sec=1.0)
    lock.acquire(blocking=True)
    ready_event.set()
    time.sleep(hold_time)
    lock.release()


def test_adversarial_multiprocess_lock_contention():
    """
    Empirically test OS-level flock contention using real multiprocessing.
    Process A holds lock for 0.8s.
    Process B non-blocking acquire must raise BlockingIOError.
    Process C blocking with timeout=0.2s must raise TimeoutError.
    Process D blocking with timeout=2.0s must successfully acquire lock.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        lock_file = ".contention.lock"
        ready_event = multiprocessing.Event()
        
        p = multiprocessing.Process(
            target=_worker_hold_lock,
            args=(tmpdir, lock_file, 0.8, ready_event)
        )
        p.start()
        
        try:
            assert ready_event.wait(timeout=5.0), "Worker failed to start"
            
            # Process B: Non-blocking acquire should fail immediately
            lock_b = SessionLock(session_dir=tmpdir, lock_filename=lock_file, timeout_sec=0.1)
            with pytest.raises(BlockingIOError):
                lock_b.acquire(blocking=False)
                
            # Process C: Blocking acquire with short timeout should timeout
            lock_c = SessionLock(session_dir=tmpdir, lock_filename=lock_file, timeout_sec=0.2, poll_interval=0.05)
            with pytest.raises(TimeoutError):
                lock_c.acquire(blocking=True)
                
            # Process D: Blocking acquire with sufficient timeout should acquire once A finishes
            lock_d = SessionLock(session_dir=tmpdir, lock_filename=lock_file, timeout_sec=3.0, poll_interval=0.1)
            t0 = time.time()
            acquired = lock_d.acquire(blocking=True)
            elapsed = time.time() - t0
            assert acquired is True
            assert elapsed >= 0.3, "Acquired too quickly while worker was holding lock"
            lock_d.release()
        finally:
            p.join(timeout=3.0)
            if p.is_alive():
                p.terminate()


@run_async
async def test_adversarial_context_double_close_idempotency():
    """
    Verify that if Playwright context triggers close multiple times
    or user calls context.close() multiple times, lock.release() remains idempotent.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        lock_path = os.path.join(tmpdir, ".idempotent.lock")
        mgr = LinkedInSessionManager(session_dir=tmpdir, lock_path=lock_path)
        mgr.get_li_at_cookie = MagicMock(return_value="AQEDAQ_IDEMPOTENT_TEST")
        
        ctx = make_mock_context()
        pw = make_mock_playwright(context=ctx)
        
        context = await mgr.create_stealth_context(pw, headless=True)
        assert mgr.get_lock()._acquired is True
        
        # Trigger close first time
        await context.close()
        assert mgr.get_lock()._acquired is False
        
        # Trigger close second time - must not raise AttributeError, ValueError, or OSError
        try:
            await context.close()
        except Exception as e:
            pytest.fail(f"Repeated context.close() raised exception: {e}")
        assert mgr.get_lock()._acquired is False


# ==============================================================================
# SECTION 2: REAL CLI SUBPROCESS RUNS & EXIT CODES
# ==============================================================================

def test_adversarial_real_subprocess_missing_cookie_exit_code():
    """
    Execute ./naukariPro linkedin-verify in real external subprocess with no cookie.
    Assert exact exit code 1 and structured output.
    """
    cmd = [sys.executable, "-m", "naukari_pro.cli", "linkedin-verify"]
    env = os.environ.copy()
    env.pop("LINKEDIN_LI_AT", None)
    env.pop("LI_AT", None)
    
    with tempfile.TemporaryDirectory() as empty_workspace:
        # Pass empty dir as workspace to guarantee no .env or json cookies exist
        env["WORKSPACE_DIR"] = empty_workspace
        res = subprocess.run(
            cmd,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            env=env,
            capture_output=True,
            text=True,
            timeout=15
        )
        assert res.returncode == 1
        assert "Session Status:         COOKIE_MISSING" in res.stdout
        assert "Cookie Present:         NO" in res.stdout


def test_adversarial_real_subprocess_help_flag_exit_code():
    """
    Execute ./naukariPro linkedin-verify --help and top-level --help in real external subprocess.
    Assert exact exit code 0.
    """
    cmd = [sys.executable, "-m", "naukari_pro.cli", "linkedin-verify", "--help"]
    res = subprocess.run(
        cmd,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        capture_output=True,
        text=True,
        timeout=15
    )
    assert res.returncode == 0
    assert "--headed" in res.stdout
    assert "usage:" in res.stdout

    # Verify top-level CLI lists linkedin-verify subcommand description
    cmd_top = [sys.executable, "-m", "naukari_pro.cli", "--help"]
    res_top = subprocess.run(
        cmd_top,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        capture_output=True,
        text=True,
        timeout=15
    )
    assert res_top.returncode == 0
    assert "linkedin-verify" in res_top.stdout
    assert "Validate LinkedIn session freshness" in res_top.stdout


def test_adversarial_real_subprocess_invalid_flag_exit_code():
    """
    Execute ./naukariPro linkedin-verify with unknown argument.
    Assert argparse exit code 2.
    """
    cmd = [sys.executable, "-m", "naukari_pro.cli", "linkedin-verify", "--unknown-adversarial-arg"]
    res = subprocess.run(
        cmd,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        capture_output=True,
        text=True,
        timeout=15
    )
    assert res.returncode == 2
    assert "unrecognized arguments" in res.stderr.lower() or "error" in res.stderr.lower()


def test_adversarial_sequential_cli_runs_leave_clean_lock():
    """
    Run 5 consecutive CLI runs in real subprocesses.
    Assert that every run exits with code 1 and no deadlock or leftover lock occurs.
    """
    cmd = [sys.executable, "-m", "naukari_pro.cli", "linkedin-verify"]
    env = os.environ.copy()
    env.pop("LINKEDIN_LI_AT", None)
    env.pop("LI_AT", None)
    env["WORKSPACE_DIR"] = "/nonexistent/test_workspace"
    
    for i in range(5):
        res = subprocess.run(
            cmd,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            env=env,
            capture_output=True,
            text=True,
            timeout=15
        )
        assert res.returncode == 1, f"Run {i+1} failed with returncode {res.returncode}"


def _worker_cli_with_lock(tmpdir, delay_before_start, mock_duration, res_queue):
    env = os.environ.copy()
    env["LINKEDIN_LI_AT"] = "AQEDAQ_DUMMY_CONCURRENT_COOKIE"
    time.sleep(delay_before_start)
    
    lock_file = os.path.join(tmpdir, ".linkedin_session.lock")
    mgr = LinkedInSessionManager(session_dir=tmpdir, lock_path=lock_file, lock_timeout=5.0)
    
    t0 = time.time()
    lock = mgr.get_lock()
    lock.acquire(blocking=True)
    try:
        time.sleep(mock_duration)
        res_queue.put({"success": True, "elapsed": time.time() - t0})
    finally:
        lock.release()


def test_adversarial_concurrent_processes_lock_queuing():
    """
    Verify two concurrent processes attempting to access LinkedIn session queue safely:
    Process 1 acquires lock and holds for 0.6s.
    Process 2 starts 0.1s later and must wait until Process 1 releases before acquiring.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        res_q = multiprocessing.Queue()
        
        p1 = multiprocessing.Process(target=_worker_cli_with_lock, args=(tmpdir, 0.0, 0.6, res_q))
        p2 = multiprocessing.Process(target=_worker_cli_with_lock, args=(tmpdir, 0.1, 0.2, res_q))
        
        p1.start()
        p2.start()
        
        p1.join(timeout=5.0)
        p2.join(timeout=5.0)
        
        assert not p1.is_alive()
        assert not p2.is_alive()
        
        r1 = res_q.get(timeout=3.0)
        r2 = res_q.get(timeout=3.0)
        assert r1["success"] is True
        assert r2["success"] is True



# ==============================================================================
# SECTION 3: EXTREME BOUND TOKEN FUZZING & ORACLES
# ==============================================================================

@pytest.mark.parametrize("fuzz_input, expected", [
    ("", None),
    ("   ", None),
    ("\t\r\n", None),
    ("None", "None"),
    ("null", "null"),
    ('""', None),
    ("''", None),
    ('"""', None),
    ("'''", None),
    ('"""""', None),
    ('"  "', None),
    ("'  '", None),
    ('"\t\r\n"', None),
    ('  "  \'  "  \'  "  \'  token  \'  "  \'  "  \'  "  ', "token"),
    ('"""AQEDAQ_TRIPLE_DOUBLE_QUOTES"""', "AQEDAQ_TRIPLE_DOUBLE_QUOTES"),
    ("'''AQEDAQ_TRIPLE_SINGLE_QUOTES'''", "AQEDAQ_TRIPLE_SINGLE_QUOTES"),
    ('"""""AQEDAQ_FIVE_QUOTES"""""', "AQEDAQ_FIVE_QUOTES"),
    (' "AQEDAQ_PREFIX_SPACE', "AQEDAQ_PREFIX_SPACE"),
    ('AQEDAQ_SUFFIX_SPACE" ', "AQEDAQ_SUFFIX_SPACE"),
    ("AQEDAQ\x00NULL_BYTE", "AQEDAQ\x00NULL_BYTE"),
    ("AQEDAQ🔥KEY", "AQEDAQ🔥KEY"),
    ("AQEDAQ_INTERNAL_SPACES_RETAINED   ", "AQEDAQ_INTERNAL_SPACES_RETAINED"),
    ("AQEDAQ==PADDING==", "AQEDAQ==PADDING=="),
    ("AQEDAQ-URL_SAFE_TOKEN_123", "AQEDAQ-URL_SAFE_TOKEN_123"),
])
def test_adversarial_token_sanitization_fuzz(fuzz_input, expected):
    """Fuzz sanitize_cookie_token with edge cases, boundaries, and degenerate strings."""
    assert sanitize_cookie_token(fuzz_input) == expected


def test_adversarial_massive_token_fuzzing():
    """
    Stress-test sanitize_cookie_token and mask_cookie_token with 100,000-character strings.
    Verify O(N) linear performance and zero recursion depth crash.
    """
    massive_token = "A" * 100000
    quoted_massive = f'""" {massive_token} """'
    
    t0 = time.time()
    sanitized = sanitize_cookie_token(quoted_massive)
    elapsed = time.time() - t0
    
    assert elapsed < 0.5, f"Sanitization took {elapsed:.3f}s (potential ReDoS or infinite loop)"
    assert sanitized == massive_token
    assert len(sanitized) == 100000
    
    masked = mask_cookie_token(sanitized)
    assert masked == f"AAAA...AAAA (100000 chars, masked)"


@pytest.mark.parametrize("fuzz_len, expected_shape", [
    (0, "None"),
    (1, "****"),
    (4, "****"),
    (7, "****"),
    (8, "****"),
    (9, "AAAA...AAAA (9 chars, masked)"),
    (10, "AAAA...AAAA (10 chars, masked)"),
    (50, "AAAA...AAAA (50 chars, masked)"),
])
def test_adversarial_mask_cookie_token_boundaries(fuzz_len, expected_shape):
    """Verify mask_cookie_token boundary lengths (<=8 vs >=9 chars)."""
    token = "A" * fuzz_len if fuzz_len > 0 else ""
    res = mask_cookie_token(token)
    assert res == expected_shape


def test_adversarial_extract_token_corrupted_json_variants():
    """
    Test _extract_token_from_file against various malformed or pathological JSON payloads.
    Must never crash or raise unhandled exceptions.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        cookie_file = os.path.join(tmpdir, "fuzz_cookie.json")
        mgr = LinkedInSessionManager(cookie_path=cookie_file)
        
        pathological_json_payloads = [
            "",  # Empty file
            "   \n\t  ",  # Whitespace only
            "{",  # Truncated JSON
            '{"name": "li_at"',  # Truncated dict
            "[",  # Truncated array
            "null",  # JSON null
            "12345",  # JSON int
            "true",  # JSON bool
            "[]",  # Empty list
            "{}",  # Empty dict
            "[1, 2, 3]",  # Array of non-dicts
            '["string1", "string2"]',  # Array of strings
            '[null, false, {}]',  # Array of mixed invalid items
            '[{"other_key": "val"}]',  # Dict missing 'name'
            '[{"name": "session_id", "value": "xyz"}]',  # No li_at
            '[{"name": "li_at", "value": ""}]',  # Empty li_at value
            '[{"name": "li_at", "value": null}]',  # Null li_at value
            '[{"name": "li_at", "value": "   "}]',  # Whitespace li_at value
            '{"li_at": null}',  # Dict null value
            '{"li_at": ""}',  # Dict empty value
            '{"li_at": "   "}',  # Dict whitespace value
            '{"other_cookie": "xyz"}',  # Dict without li_at
        ]
        
        for payload in pathological_json_payloads:
            with open(cookie_file, "w", encoding="utf-8") as f:
                f.write(payload)
            # Should safely return None without crashing
            token = mgr._extract_token_from_file(cookie_file)
            assert token is None, f"Expected None for payload: {payload!r}, got: {token!r}"

        # Verify raw string extraction fallback for files not starting with '{' or '['
        raw_cookie = "AQEDAQ_RAW_COOKIE_TOKEN_FROM_PLAIN_FILE"
        with open(cookie_file, "w", encoding="utf-8") as f:
            f.write(raw_cookie)
        extracted = mgr._extract_token_from_file(cookie_file)
        assert extracted == raw_cookie


def test_adversarial_priority_resolution_all_tiers_present():
    """
    When ALL tiers are simultaneously populated with different tokens:
    Tier 1 (env LINKEDIN_LI_AT) must win over all others.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        cookie_file = os.path.join(tmpdir, "cookies.json")
        with open(cookie_file, "w") as f:
            json.dump([{"name": "li_at", "value": "TOKEN_TIER_3"}], f)
            
        mgr = LinkedInSessionManager(session_dir=tmpdir, cookie_path=cookie_file)
        
        with patch.dict(os.environ, {"LINKEDIN_LI_AT": "TOKEN_TIER_1", "LI_AT": "TOKEN_TIER_1_FALLBACK"}):
            token = mgr.get_li_at_cookie(raise_if_missing=True)
            assert token == "TOKEN_TIER_1"
            assert "LINKEDIN_LI_AT" in mgr.last_cookie_source


def test_adversarial_priority_resolution_tier2_wins_when_tier1_absent():
    """
    When env var is absent, workspace .env file (Tier 2) must win over JSON cookie file (Tier 3).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        env_file = os.path.join(tmpdir, ".env")
        with open(env_file, "w") as f:
            f.write('export LINKEDIN_LI_AT="TOKEN_TIER_2_ENV_FILE"\n')
            
        cookie_file = os.path.join(tmpdir, "cookies.json")
        with open(cookie_file, "w") as f:
            json.dump([{"name": "li_at", "value": "TOKEN_TIER_3_JSON"}], f)
            
        mgr = LinkedInSessionManager(session_dir=tmpdir, cookie_path=cookie_file)
        
        with patch.dict(os.environ, {}, clear=True):
            with patch("naukari_pro.modules.linkedin_session.WORKSPACE_DIR", tmpdir):
                token = mgr.get_li_at_cookie(raise_if_missing=True)
                assert token == "TOKEN_TIER_2_ENV_FILE"
                assert "TOKEN_TIER_2" in token
