"""Unit sims for SessionLock re-entrancy, stale steal, and foreign timeout → requeue."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from naukari_pro.session import (
    SessionLock,
    SessionLockTimeout,
    cleanup_orphaned_chromium,
    read_lock_owner_pid,
    requeue_after_lock_timeout,
    same_process_tree,
)


def test_same_process_tree_self():
    assert same_process_tree(os.getpid(), os.getpid()) is True


def test_reentrant_acquire_when_owner_is_self(tmp_path):
    lock_path = tmp_path / ".naukari_session.lock"
    lock_path.write_text(f"pid={os.getpid()}\ntime=now\n", encoding="utf-8")
    lock = SessionLock(session_dir=str(tmp_path), timeout_sec=2.0)
    assert lock.acquire(blocking=True) is True
    assert lock._reentrant is True
    lock.release()
    # Re-entrant release must not wipe owner marker for parent holder
    assert lock_path.exists()


def test_stale_lock_stolen_from_dead_pid(tmp_path):
    lock_path = tmp_path / ".naukari_session.lock"
    dead_pid = 99999999
    lock_path.write_text(f"pid={dead_pid}\ntime=now\n", encoding="utf-8")
    lock = SessionLock(session_dir=str(tmp_path), timeout_sec=2.0)
    with patch("naukari_pro.session._pid_alive", side_effect=lambda p: False if p == dead_pid else True):
        assert lock.acquire(blocking=True) is True
    assert lock._reentrant is False
    assert read_lock_owner_pid(str(lock_path)) == os.getpid()
    lock.release()


def test_foreign_lock_times_out_and_requeues(tmp_path):
    lock_path = tmp_path / ".naukari_session.lock"
    # Use a live pid that is NOT us and NOT in our tree: PID 1 is typically init/systemd
    foreign = 1
    lock_path.write_text(f"pid={foreign}\ntime=now\n", encoding="utf-8")

    # Hold flock with a real fd so acquire cannot succeed via flock
    import fcntl

    holder = open(lock_path, "a+")
    fcntl.flock(holder.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    lock = SessionLock(session_dir=str(tmp_path), timeout_sec=0.4, poll_interval=0.05)
    with patch("naukari_pro.session.same_process_tree", return_value=False), patch(
        "naukari_pro.session._pid_alive", return_value=True
    ):
        with pytest.raises(SessionLockTimeout) as ei:
            lock.acquire(blocking=True)
    assert ei.value.lock_path.endswith(".naukari_session.lock")

    with patch("naukari_pro.modules.scorecard.sync_dual_log") as dual:
        requeue_after_lock_timeout(
            portal_url="https://jobs.ashbyhq.com/demo/1",
            company="Demo",
            role="Azure Data Engineer",
        )
        dual.assert_called_once()
        assert dual.call_args.kwargs.get("status") == "External Redirect"

    fcntl.flock(holder.fileno(), fcntl.LOCK_UN)
    holder.close()


def test_cleanup_orphaned_chromium_noop_without_procs(tmp_path):
    assert cleanup_orphaned_chromium(str(tmp_path)) == 0
