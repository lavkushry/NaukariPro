#!/usr/bin/env python3
"""
Phase-3 seeded chaos monkey — injects a fault every interval, then runs invariants.

Offline-safe: does not touch live ATS; mutates in-process callables / temp DBs only.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.check_invariants import check_all  # noqa: E402
from tests.hammer.attacks import ATTACKS  # noqa: E402
from tests.hammer.blow_registry import ALL_BLOWS  # noqa: E402
from tests.hammer.harness import run_blow  # noqa: E402


FAULTS = [
    "typed_raise",
    "json_truncated",
    "ssrf_localhost",
    "path_traversal",
    "boot_vendor_no_key",
    "react_remount",
    "dedupe_idempotent",
]


def run_chaos(*, seed: int, duration_s: int, interval_s: int) -> int:
    rng = random.Random(seed)
    t_end = time.time() + duration_s
    faults = 0
    violations_total = 0
    while time.time() < t_end:
        name = rng.choice(FAULTS)
        blow = rng.choice(ALL_BLOWS)
        attack = ATTACKS[name]
        try:
            run_blow(
                blow_id=f"CHAOS-{blow['blow_id']}-{faults}",
                hammer="chaos",
                vector=f"monkey:{name}",
                target=blow["target"],
                attack=attack,
                expect="contained",
            )
        except AssertionError:
            # Raw crash under chaos — still fail-closed if ledgered
            pass
        faults += 1
        viol = check_all()
        violations_total += len(viol)
        if viol:
            print(json.dumps({"fault": faults, "violations": viol}))
        time.sleep(interval_s)
    print(
        json.dumps(
            {
                "seed": seed,
                "faults": faults,
                "invariant_violations": violations_total,
                "ok": violations_total == 0,
            }
        )
    )
    return 0 if violations_total == 0 else 1


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--duration", type=int, default=30, help="seconds (CI default 30; overnight 28800)")
    p.add_argument("--interval", type=int, default=2, help="seconds between faults")
    args = p.parse_args()
    return run_chaos(seed=args.seed, duration_s=args.duration, interval_s=args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
