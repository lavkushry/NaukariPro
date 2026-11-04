#!/usr/bin/env python3
"""Gate 2: every SUT module ≥90% lines; critical modules 100% branch."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# coverage JSON from `coverage json -o coverage.json`
ROOT = Path(__file__).resolve().parents[1]
COVERAGE_JSON = ROOT / "coverage.json"

SUT = [
    "naukari_pro/resume_gen/claim_validator.py",
    "naukari_pro/resume_gen/writing_lint.py",
    "naukari_pro/governed_apply/fill_verify.py",
    "naukari_pro/governed_apply/approval.py",
    "naukari_pro/governed_apply/dedupe_rules.py",
    "naukari_pro/governed_apply/exit_codes.py",
    "naukari_pro/governed_apply/attention.py",
    "naukari_pro/captcha/safety.py",
    "naukari_pro/captcha/detector.py",
    "naukari_pro/captcha/circuit.py",
    "naukari_pro/captcha/events.py",
    "naukari_pro/security/pii.py",
    "naukari_pro/security/paths.py",
    "naukari_pro/security/canary.py",
    "naukari_pro/aggregation/models.py",
    "naukari_pro/aggregation/dedup.py",
    "naukari_pro/aggregation/india_geo.py",
    "naukari_pro/matching/deterministic_score.py",
    "naukari_pro/llm/routing.py",
    "naukari_pro/llm/ledger.py",
]

# 100% branch required
BRANCH_CRITICAL = [
    "naukari_pro/resume_gen/claim_validator.py",
    "naukari_pro/governed_apply/approval.py",
    "naukari_pro/captcha/safety.py",
    "naukari_pro/governed_apply/exit_codes.py",
]


def main() -> int:
    if not COVERAGE_JSON.exists():
        print("missing coverage.json — run coverage json first")
        return 1
    data = json.loads(COVERAGE_JSON.read_text())
    files = data.get("files") or {}
    # normalize keys
    by_suffix = {k.replace("\\", "/"): v for k, v in files.items()}

    def find(path: str):
        for k, v in by_suffix.items():
            if k.endswith(path) or path in k:
                return k, v
        return None, None

    failed = []
    rows = []
    for path in SUT:
        key, meta = find(path)
        if not meta:
            failed.append((path, "missing", None))
            continue
        summary = meta["summary"]
        covered = summary.get("covered_lines", 0)
        nlines = summary.get("num_statements", 0)
        pct = (100.0 * covered / nlines) if nlines else 100.0
        b_pct = None
        if summary.get("num_branches"):
            b_cov = summary.get("covered_branches", 0)
            b_tot = summary.get("num_branches", 0)
            b_pct = (100.0 * b_cov / b_tot) if b_tot else 100.0
        rows.append((path, pct, b_pct))
        if pct < 90.0 - 1e-9:
            failed.append((path, f"line={pct:.1f}%", b_pct))
        if path in BRANCH_CRITICAL and b_pct is not None and b_pct < 100.0 - 1e-9:
            failed.append((path, f"branch={b_pct:.1f}%", b_pct))

    for path, pct, b_pct in rows:
        print(f"{path}: lines={pct:.1f}% branch={b_pct}")
    if failed:
        print("GATE2_FAIL", failed)
        return 1
    print("GATE2_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
