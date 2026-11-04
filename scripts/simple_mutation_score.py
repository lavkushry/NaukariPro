#!/usr/bin/env python3
"""
Lightweight mutation score for Gate 3 when mutmut is unavailable.

Applies textual mutants to claim_validator + captcha safety, runs focused
tests, and reports kill rate. Also requires 5 red-team mutation proofs.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TARGETS = [
    (
        "naukari_pro/resume_gen/claim_validator.py",
        [
            ("novelty > novelty_cap", "novelty > 1.0"),
            ("support < support_threshold", "support < -1"),
            ("ok = len(unsupported) == 0 and doc_novelty <= novelty_cap", "ok = True"),
            ('reasons.append(f"unsourced_number:{num}")', "pass  # mutated-unsourced"),
        ],
        ["tests/scenarios/verifier/", "tests/gates/test_coverage_helpers.py"],
    ),
    (
        "naukari_pro/captcha/safety.py",
        [
            ("if not self.api_key:", "if False:  # mutated-key"),
            ("if self.spend_24h >= self.cap:", "if False:  # mutated-cap"),
            (
                "exit_code=EXIT_CAPTCHA_BLOCKED,\n                detail=\"human_mode_or_no_vendor\",",
                "exit_code=0,\n                detail=\"human_mode_or_no_vendor\",",
            ),
            ("if not domain_allowed(domain, self.domains):", "if False:  # mutated-allow"),
        ],
        ["tests/scenarios/captcha/", "tests/gates/test_coverage_helpers.py"],
    ),
]


def run_pytest(paths: list[str]) -> bool:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", *paths, "-q", "--tb=no"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


def main() -> int:
    if not run_pytest(["tests/scenarios/verifier/", "tests/scenarios/captcha/"]):
        print("BASELINE_FAIL")
        return 1

    killed = 0
    total = 0
    details = []
    for rel, mutants, tests in TARGETS:
        src = ROOT / rel
        original = src.read_text(encoding="utf-8")
        for old, new in mutants:
            total += 1
            if old not in original:
                details.append({"file": rel, "old": old, "status": "SKIP_no_match"})
                continue
            try:
                src.write_text(original.replace(old, new, 1), encoding="utf-8")
                survived = run_pytest(tests)
                status = "SURVIVED" if survived else "KILLED"
                if not survived:
                    killed += 1
                details.append({"file": rel, "old": old, "status": status})
            finally:
                src.write_text(original, encoding="utf-8")

    rate = (100.0 * killed / total) if total else 0.0
    print(f"MUTANTS total={total} killed={killed} rate={rate:.1f}%")
    for row in details:
        print(" ", row)

    proof = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/gates/test_mutation_proofs.py", "-q", "--tb=no"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    print(proof.stdout.strip())
    proofs_ok = proof.returncode == 0

    # Per-file rates
    by_file: dict[str, list[str]] = {}
    for d in details:
        by_file.setdefault(d["file"], []).append(d["status"])
    file_rates = {
        f: (100.0 * s.count("KILLED") / max(1, len([x for x in s if x != "SKIP_no_match"])))
        for f, s in by_file.items()
    }
    print("FILE_RATES", file_rates)

    hot = all(file_rates.get(f, 0) >= 70 for f in file_rates)  # practical floor
    ok = rate >= 70.0 and proofs_ok
    print("GATE3", "PASS" if ok else "FAIL", f"rate={rate:.1f} proofs={proofs_ok} hot={hot}")
    (ROOT / "tests" / "mutation_last_run.json").write_text(
        json.dumps(
            {
                "total": total,
                "killed": killed,
                "rate": rate,
                "file_rates": file_rates,
                "proofs_ok": proofs_ok,
                "details": details,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
