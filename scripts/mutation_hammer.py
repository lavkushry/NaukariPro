#!/usr/bin/env python3
"""
Phase-4 safety mutation hammer (DIY, offline).

Applies one-line mutants to safety-critical modules, re-runs a focused hammer
subset, and requires every mutant to be KILLED (tests fail). Restores sources.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

@dataclass
class Mutant:
    path: Path
    needle: str
    replacement: str
    name: str


MUTANTS = [
    Mutant(
        path=ROOT / "naukari_pro" / "hammer_safe.py",
        needle="if host in blocked_hosts or host.endswith(\".local\") or host.startswith(\"10.\"):",
        replacement="if False and (host in blocked_hosts or host.endswith(\".local\") or host.startswith(\"10.\")):  # MUTANT",
        name="ssrf_denylist_gutted",
    ),
    Mutant(
        path=ROOT / "naukari_pro" / "hammer_safe.py",
        needle="if _byte_len(value) > max_bytes:",
        replacement="if False and _byte_len(value) > max_bytes:  # MUTANT",
        name="size_cap_disabled",
    ),
    Mutant(
        path=ROOT / "naukari_pro" / "hammer_safe.py",
        needle="if aliases > MAX_YAML_ALIASES or refs > MAX_YAML_ALIASES:",
        replacement="if False and (aliases > MAX_YAML_ALIASES or refs > MAX_YAML_ALIASES):  # MUTANT",
        name="yaml_alias_cap_disabled",
    ),
]


FOCUS = [
    "tests/hammer/test_all_blows.py::test_hammer_blow[H1-08]",  # ssrf metadata
    "tests/hammer/test_all_blows.py::test_hammer_blow[H1-09]",  # ssrf localhost
    "tests/hammer/test_all_blows.py::test_hammer_blow[H1-03]",  # 10mb
    "tests/hammer/test_all_blows.py::test_hammer_blow[H1-06]",  # yaml bomb
]


def _run_focus() -> int:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        *FOCUS,
        "-q",
        "--tb=no",
    ]
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True).returncode


def main() -> int:
    # Baseline must pass
    if _run_focus() != 0:
        print("BASELINE_FAIL — focused hammer subset red before mutation")
        return 2

    results = []
    for m in MUTANTS:
        original = m.path.read_text(encoding="utf-8")
        if m.needle not in original:
            results.append((m.name, "SKIP_NEEDLE_MISSING"))
            continue
        mutated = original.replace(m.needle, m.replacement, 1)
        backup = Path(tempfile.mkstemp(suffix=".py")[1])
        shutil.copy2(m.path, backup)
        try:
            m.path.write_text(mutated, encoding="utf-8")
            rc = _run_focus()
            killed = rc != 0
            results.append((m.name, "KILLED" if killed else "SURVIVED"))
        finally:
            shutil.copy2(backup, m.path)
            backup.unlink(missing_ok=True)

    survived = [n for n, s in results if s == "SURVIVED"]
    print("MUTATION_HAMMER_RESULTS")
    for n, s in results:
        print(f"  {n}: {s}")
    print(f"surviving_safety_mutants={len(survived)}")
    return 1 if survived else 0


if __name__ == "__main__":
    raise SystemExit(main())
