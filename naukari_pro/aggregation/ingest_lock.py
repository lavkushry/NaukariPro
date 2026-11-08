"""Ingest cycle lockfile: pid + timestamp; stale after 30 minutes → clear."""

from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

DEFAULT_LOCK = Path(__file__).resolve().parents[1] / "runtime" / "ingest.lock"
STALE_SECONDS = 30 * 60


class IngestLockError(RuntimeError):
    pass


def _read_lock(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def acquire_ingest_lock(path: Optional[Path] = None, *, stale_seconds: int = STALE_SECONDS) -> Path:
    path = Path(path) if path else DEFAULT_LOCK
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = _read_lock(path)
    now = time.time()
    if existing:
        pid = int(existing.get("pid") or 0)
        started = float(existing.get("started_at") or 0)
        age = now - started if started else stale_seconds + 1
        if age > stale_seconds or not _pid_alive(pid):
            path.unlink(missing_ok=True)
        else:
            raise IngestLockError(
                f"ingest already running pid={pid} age_s={int(age)} lock={path}"
            )
    payload = {"pid": os.getpid(), "started_at": now, "host": os.uname().nodename}
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def release_ingest_lock(path: Optional[Path] = None) -> None:
    path = Path(path) if path else DEFAULT_LOCK
    existing = _read_lock(path)
    if existing and int(existing.get("pid") or 0) == os.getpid():
        path.unlink(missing_ok=True)


@contextmanager
def ingest_lock(path: Optional[Path] = None) -> Iterator[Path]:
    lock_path = acquire_ingest_lock(path)
    try:
        yield lock_path
    finally:
        release_ingest_lock(lock_path)
