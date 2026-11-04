"""Hammer suite fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.hammer.harness import FIXTURES, LOG_PATH


@pytest.fixture(scope="session", autouse=True)
def _hammer_dirs():
    import os

    FIXTURES.mkdir(parents=True, exist_ok=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Full Phase-1 suites truncate; mutation/chaos focus runs must append
    # so they do not erase the 420-blow ledger (set HAMMER_TRUNCATE=1 to reset).
    if os.environ.get("HAMMER_TRUNCATE", "0") == "1" or not LOG_PATH.exists():
        LOG_PATH.write_text("", encoding="utf-8")
    yield


@pytest.fixture
def exploit_dir() -> Path:
    return FIXTURES
