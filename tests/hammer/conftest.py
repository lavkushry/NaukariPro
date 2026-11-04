"""Hammer suite fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.hammer.harness import FIXTURES, LOG_PATH


@pytest.fixture(scope="session", autouse=True)
def _hammer_dirs():
    FIXTURES.mkdir(parents=True, exist_ok=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Truncate log at session start for clean Phase-1 ledger
    LOG_PATH.write_text("", encoding="utf-8")
    yield


@pytest.fixture
def exploit_dir() -> Path:
    return FIXTURES
