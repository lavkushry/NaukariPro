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
        needle="if _is_blocked_ssrf_host(host):",
        replacement="if False and _is_blocked_ssrf_host(host):  # MUTANT",
        name="ssrf_denylist_gutted",
    ),
    Mutant(
        path=ROOT / "naukari_pro" / "governed_apply" / "fill_verify.py",
        needle="layer1 = _norm(dom_value) == exp",
        replacement="layer1 = True  # MUTANT: always pass DOM layer",
        name="fill_layer1_always_true",
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
    Mutant(
        path=ROOT / "naukari_pro" / "hammer_safe.py",
        needle='raise ValidationError("path traversal refused", context={"path": raw[:200]})',
        replacement='return base / "mutant_allowed"  # MUTANT',
        name="path_traversal_gutted",
    ),
    Mutant(
        path=ROOT / "naukari_pro" / "governed_apply" / "approval.py",
        needle="WHERE token=? AND status='pending'",
        replacement="WHERE token=? ",
        name="approval_pending_guard_dropped",
    ),
    Mutant(
        path=ROOT / "naukari_pro" / "security" / "canary.py",
        needle="blocked = bool(canaries or no_ai or takehome or injection)",
        replacement="blocked = bool(canaries or no_ai or takehome)  # MUTANT: ignore injection",
        name="injection_gate_disabled",
    ),
    Mutant(
        path=ROOT / "naukari_pro" / "hammer_safe.py",
        needle="if redirects > MAX_REDIRECTS:",
        replacement="if False and redirects > MAX_REDIRECTS:  # MUTANT",
        name="redirect_cap_disabled",
    ),
]


FOCUS = [
    "tests/hammer/test_all_blows.py::test_hammer_blow[H1-08]",  # ssrf metadata
    "tests/hammer/test_all_blows.py::test_hammer_blow[H1-09]",  # ssrf localhost
    "tests/hammer/test_all_blows.py::test_hammer_blow[H1-03]",  # oversized
    "tests/hammer/test_all_blows.py::test_hammer_blow[H1-06]",  # yaml bomb
    "tests/hammer/test_all_blows.py::test_hammer_blow[H8-01]",  # react remount
    "tests/hammer/test_all_blows.py::test_hammer_blow[H4-03]",  # token race
    "tests/hammer/test_all_blows.py::test_hammer_blow[H10-01]",  # path traversal
    "tests/hammer/test_all_blows.py::test_hammer_blow[H2-18]",  # prompt inject
    "tests/hammer/test_all_blows.py::test_hammer_blow[H7-15]",  # redirect loop
    "tests/hammer/test_phase5_regressions.py::test_p5_f1_empty_expected_rejects_fabricated_dom",
    "tests/hammer/test_phase5_regressions.py::test_p5_f3_loopback_variants_blocked",
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
    skipped = [n for n, s in results if s == "SKIP_NEEDLE_MISSING"]
    print("MUTATION_HAMMER_RESULTS")
    for n, s in results:
        print(f"  {n}: {s}")
    print(f"surviving_safety_mutants={len(survived)}")
    print(f"skipped_needles={len(skipped)}")
    kill_rate = 0.0
    attempted = [s for _, s in results if s in ("KILLED", "SURVIVED")]
    if attempted:
        kill_rate = sum(1 for s in attempted if s == "KILLED") / len(attempted)
    print(f"kill_rate={kill_rate:.2%}")
    if survived:
        return 1
    if skipped:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
