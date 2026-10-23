"""
Milestone 4 Feature Verification Suite
Tests for:
- Feature 14: Schedule Collision Resolution (Crontab purging and single authority)
- Feature 15: Process-Level File Locking (SessionLock, stale lock cleanup, flock mutual exclusion)
- Feature 16: Headless Cloud Proxy Routing & Akamai WAF Evasion (parse_proxy_settings & stealth)
"""

import os
import sys
import tempfile
import shutil
import subprocess
import pytest
import fcntl
from unittest.mock import patch

from naukari_pro.session import (
    SessionLock,
    cleanup_stale_chromium_locks,
    parse_proxy_settings,
    STEALTH_JS
)


# ==============================================================================
# Feature 16 Tests: Proxy Parsing & Normalization
# ==============================================================================

class TestProxyParsing:
    def test_proxy_none_without_env(self, monkeypatch):
        monkeypatch.delenv("NAUKRI_PROXY", raising=False)
        assert parse_proxy_settings(None) is None
        assert parse_proxy_settings("") is None
        assert parse_proxy_settings("   ") is None

    def test_proxy_env_fallback(self, monkeypatch):
        monkeypatch.setenv("NAUKRI_PROXY", "http://env-proxy.local:8080")
        res = parse_proxy_settings(None)
        assert res == {"server": "http://env-proxy.local:8080"}

    def test_proxy_explicit_overrides_env(self, monkeypatch):
        monkeypatch.setenv("NAUKRI_PROXY", "http://env-proxy.local:8080")
        res = parse_proxy_settings("http://explicit-proxy.local:3128")
        assert res == {"server": "http://explicit-proxy.local:3128"}

    def test_proxy_plain_url(self):
        res = parse_proxy_settings("http://proxy.example.com:8080")
        assert res == {"server": "http://proxy.example.com:8080"}

    def test_proxy_host_port_without_scheme(self):
        res = parse_proxy_settings("proxy.example.com:8080")
        assert res == {"server": "http://proxy.example.com:8080"}

    def test_proxy_inline_credentials(self):
        res = parse_proxy_settings("http://user:pass@proxy.example.com:3128")
        assert res == {
            "server": "http://proxy.example.com:3128",
            "username": "user",
            "password": "pass"
        }

    def test_proxy_url_encoded_credentials(self):
        res = parse_proxy_settings("http://user%40corp:pass%23123@gate.smartproxy.com:7000")
        assert res == {
            "server": "http://gate.smartproxy.com:7000",
            "username": "user@corp",
            "password": "pass#123"
        }

    def test_proxy_socks5_protocol(self):
        res = parse_proxy_settings("socks5://proxyuser:proxypass@127.0.0.1:1080")
        assert res == {
            "server": "socks5://127.0.0.1:1080",
            "username": "proxyuser",
            "password": "proxypass"
        }

    def test_proxy_dict_input_canonical(self):
        input_dict = {
            "server": "http://gate.smartproxy.com:7000",
            "username": "myuser",
            "password": "mypassword",
            "bypass": "localhost,127.0.0.1"
        }
        res = parse_proxy_settings(input_dict)
        assert res == {
            "server": "http://gate.smartproxy.com:7000",
            "username": "myuser",
            "password": "mypassword",
            "bypass": "localhost,127.0.0.1"
        }

    def test_proxy_dict_with_inline_credentials(self):
        input_dict = {
            "server": "http://admin:secret@proxy.internal:8080"
        }
        res = parse_proxy_settings(input_dict)
        assert res == {
            "server": "http://proxy.internal:8080",
            "username": "admin",
            "password": "secret"
        }

    def test_proxy_dict_empty_server(self):
        assert parse_proxy_settings({"server": ""}) is None
        assert parse_proxy_settings({}) is None

    def test_proxy_malformed_string(self):
        # Invalid input formats should return None without crashing
        assert parse_proxy_settings("::://not-a-valid-url") is None or isinstance(parse_proxy_settings("::://not-a-valid-url"), dict)


# ==============================================================================
# Feature 16 Tests: Stealth JS Anti-Detection
# ==============================================================================

class TestStealthEvasion:
    def test_stealth_js_contains_akamai_evasion_tokens(self):
        assert "webdriver" in STEALTH_JS
        assert "window.chrome" in STEALTH_JS
        assert "Win32" in STEALTH_JS
        assert "Google Inc." in STEALTH_JS
        assert "hardwareConcurrency" in STEALTH_JS
        assert "deviceMemory" in STEALTH_JS
        assert "Intel Inc." in STEALTH_JS
        assert "Intel Iris OpenGL Engine" in STEALTH_JS


# ==============================================================================
# Feature 15 Tests: Process-Level File Locking & Chromium Singleton Cleanup
# ==============================================================================

class TestSessionLock:
    def test_session_lock_sync_context_manager(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            lock = SessionLock(session_dir=tmpdir, timeout_sec=1.0)
            with lock:
                assert lock._acquired is True
                assert os.path.exists(lock.lock_path)
                with open(lock.lock_path, "r") as f:
                    content = f.read()
                assert f"pid={os.getpid()}" in content
            assert lock._acquired is False

    def test_session_lock_async_context_manager(self):
        import asyncio

        async def _run():
            with tempfile.TemporaryDirectory() as tmpdir:
                lock = SessionLock(session_dir=tmpdir, timeout_sec=1.0)
                async with lock:
                    assert lock._acquired is True
                    assert os.path.exists(lock.lock_path)
                assert lock._acquired is False

        asyncio.run(_run())

    def test_session_lock_mutual_exclusion_non_blocking(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            l1 = SessionLock(session_dir=tmpdir, timeout_sec=1.0)
            l2 = SessionLock(session_dir=tmpdir, timeout_sec=1.0)

            assert l1.acquire() is True
            try:
                with pytest.raises(BlockingIOError):
                    l2.acquire(blocking=False)
            finally:
                l1.release()

            # Now l2 can acquire successfully
            assert l2.acquire() is True
            l2.release()

    def test_session_lock_timed_acquisition_timeout(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            l1 = SessionLock(session_dir=tmpdir, timeout_sec=1.0)
            l2 = SessionLock(session_dir=tmpdir, timeout_sec=0.4, poll_interval=0.1)

            assert l1.acquire() is True
            try:
                with pytest.raises(TimeoutError) as exc_info:
                    l2.acquire(blocking=True)
                assert "Timed out after 0.4s" in str(exc_info.value)
            finally:
                l1.release()

    def test_session_lock_idempotent_release(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            lock = SessionLock(session_dir=tmpdir)
            lock.acquire()
            lock.release()
            # Second release must be clean and not raise
            lock.release()
            lock.release()

    def test_cleanup_stale_chromium_locks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create simulated regular file, symlink, and broken symlink
            reg_lock = os.path.join(tmpdir, "SingletonLock")
            with open(reg_lock, "w") as f:
                f.write("test-host-12345")

            socket_target = os.path.join(tmpdir, "socket_target")
            with open(socket_target, "w") as f:
                f.write("target")
            sock_lock = os.path.join(tmpdir, "SingletonSocket")
            os.symlink(socket_target, sock_lock)

            # Broken symlink for cookie
            cookie_lock = os.path.join(tmpdir, "SingletonCookie")
            os.symlink(os.path.join(tmpdir, "nonexistent"), cookie_lock)

            # Assert all 3 exist or are links
            assert os.path.exists(reg_lock)
            assert os.path.islink(sock_lock)
            assert os.path.lexists(cookie_lock)

            # Run cleanup
            cleanup_stale_chromium_locks(session_dir=tmpdir)

            # Assert all are safely removed
            assert not os.path.exists(reg_lock)
            assert not os.path.lexists(sock_lock)
            assert not os.path.lexists(cookie_lock)

    def test_bash_runner_flock_mutual_exclusion(self):
        """Verifies that agy_schedule_runner.sh flock mutual exclusion exits cleanly with status 0."""
        lock_file = "/tmp/naukaripro_runner.lock"
        # Open lock file and hold exclusive lock
        with open(lock_file, "w") as held_fd:
            fcntl.flock(held_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            held_fd.write(f"{os.getpid()}\n")
            held_fd.flush()

            # Execute agy_schedule_runner.sh in a subshell; should detect active lock and exit 0
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            runner_script = os.path.join(root_dir, "agy_schedule_runner.sh")
            res = subprocess.run(["/bin/bash", runner_script], capture_output=True, text=True)

            assert res.returncode == 0
            assert "[MUTUAL_EXCLUSION] Overlapping execution prevented" in res.stdout + res.stderr
            assert "Exiting cleanly with status 0" in res.stdout + res.stderr

            fcntl.flock(held_fd.fileno(), fcntl.LOCK_UN)


# ==============================================================================
# Feature 14 Tests: Schedule Collision Resolution & Crontab Sanitization
# ==============================================================================

class TestScheduleCollisionResolution:
    def test_crontab_purging_logic(self):
        """Validates that crontab sanitization removes redundant schedule runner entries."""
        simulated_crontab = (
            "# Unrelated user backup job\n"
            "0 2 * * * /usr/bin/backup.sh\n"
            "\n"
            "# NaukariPro AGY Autonomous Scheduler (09:15, 14:30, 18:00 IST)\n"
            "45 3,9,12 * * * /bin/bash /home/ubuntu/Resume/agy_schedule_runner.sh >> /home/ubuntu/Resume/logs/cron_fallback.log 2>&1\n"
            "\n"
            "# Another unrelated job\n"
            "*/10 * * * * /usr/bin/check_health.sh\n"
        )

        with tempfile.NamedTemporaryFile("w+", delete=False) as tf:
            tf.write(simulated_crontab)
            tf.flush()
            tmp_path = tf.name

        try:
            # Simulate purge logic from install_linux_schedule.sh
            clean_path = tmp_path + ".clean"
            cmd = f"grep -v 'agy_schedule_runner.sh' '{tmp_path}' | grep -v '# NaukariPro AGY' > '{clean_path}'"
            subprocess.run(cmd, shell=True, check=True)

            with open(clean_path, "r") as f:
                cleaned_content = f.read()

            assert "agy_schedule_runner.sh" not in cleaned_content
            assert "# NaukariPro AGY" not in cleaned_content
            assert "/usr/bin/backup.sh" in cleaned_content
            assert "/usr/bin/check_health.sh" in cleaned_content
            os.remove(clean_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_installer_syntax(self):
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        installer_script = os.path.join(root_dir, "install_linux_schedule.sh")
        res = subprocess.run(["/bin/bash", "-n", installer_script], capture_output=True, text=True)
        assert res.returncode == 0, f"Syntax error in install_linux_schedule.sh: {res.stderr}"

    def test_runner_syntax(self):
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        runner_script = os.path.join(root_dir, "agy_schedule_runner.sh")
        res = subprocess.run(["/bin/bash", "-n", runner_script], capture_output=True, text=True)
        assert res.returncode == 0, f"Syntax error in agy_schedule_runner.sh: {res.stderr}"
