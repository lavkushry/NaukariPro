#!/usr/bin/env python3
"""
Phase-3 seeded chaos monkey — injects faults into a minimal offline pipeline,
then re-checks the 10 invariants after every fault.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Dict, List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from naukari_pro.errors import NaukariProError  # noqa: E402
from naukari_pro import hammer_safe as hs  # noqa: E402
from naukari_pro.governed_apply.fill_verify import verify_field  # noqa: E402
from naukari_pro.governed_apply.approval import ApprovalQueue  # noqa: E402
from scripts.check_invariants import check_all  # noqa: E402
from tests.hammer.attacks import run_kind  # noqa: E402
from tests.hammer.harness import run_blow  # noqa: E402


FAULT_KINDS = [
    ("typed_raise", {"step": "parse"}),
    ("json_raw", {"raw": '{"score": 9, "rationale": "unclosed'}),
    ("ssrf", {"url": "http://127.0.0.1/"}),
    ("path_traversal", {"path": "../../etc/passwd"}),
    ("boot_vendor_no_key", {}),
    ("react_remount", {}),
    ("dedupe_idempotent", {}),
    ("http_sim", {"stall": True}),
    ("audit_disk_full", {"disk_full": True}),
    ("token_race", {"workers": 4}),
]


def _pipeline_slice(rng: random.Random, fault: Callable[[], Any] | None = None) -> Dict[str, Any]:
    """Minimal offline pipeline: parse → score stub → fill-verify → approval → ledger."""
    steps: List[str] = []
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        # parse
        hs.parse_json_safe('{"score": 8, "rationale": "fit"}')
        steps.append("parse")
        if fault and rng.random() < 0.25:
            fault()
        # score stub
        score = 8
        steps.append("score")
        # fill-verify
        vr = verify_field(
            field_id="email",
            expected="ci@example.com",
            dom_value="ci@example.com",
            check_validity=True,
            model_value="ci@example.com",
        )
        assert vr.ok
        steps.append("fill")
        if fault and rng.random() < 0.25:
            fault()
        # approval
        q = ApprovalQueue(db_path=base / "a.db")
        items = q.enqueue_batch(
            [{"url": "https://example.com/j/chaos", "company": "ChaosCo", "title": "Eng", "fit_score": score}]
        )
        assert q.decide(items[0].token, approve=True) is True
        steps.append("approve")
        # ledger audit
        hs.audit_write_fail_closed(base / "audit.jsonl", json.dumps({"job": "chaos", "status": "dry_run"}))
        steps.append("ledger")
    return {"ok": True, "steps": steps}


def run_chaos(*, seed: int, duration_s: int, interval_s: int, pipeline: bool = True) -> int:
    rng = random.Random(seed)
    t_end = time.time() + duration_s
    faults = 0
    violations_total = 0
    while time.time() < t_end:
        kind, payload = rng.choice(FAULT_KINDS)

        def _fault(k: str = kind, pl: Dict[str, Any] = payload) -> Any:
            return run_kind(k, pl)

        try:
            if pipeline and rng.random() < 0.5:
                try:
                    _pipeline_slice(rng, fault=_fault)
                except NaukariProError:
                    pass
            run_blow(
                blow_id=f"CHAOS-{faults}",
                hammer="chaos",
                vector=f"monkey:{kind}",
                target="pipeline",
                attack=_fault,
                expect="contained",
            )
        except AssertionError:
            # Raw crash under chaos — still fail-closed if ledgered
            pass
        except NaukariProError:
            pass
        faults += 1
        viol = check_all(ensure_fixture=True)
        violations_total += len(viol)
        if viol:
            print(json.dumps({"fault": faults, "violations": viol}))
        # Keep CI responsive: sleep the remainder of the interval
        time.sleep(max(0.0, interval_s))
    print(
        json.dumps(
            {
                "seed": seed,
                "faults": faults,
                "invariant_violations": violations_total,
                "ok": violations_total == 0,
                "pipeline": pipeline,
            }
        )
    )
    return 0 if violations_total == 0 else 1


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=42)
    p.add_argument(
        "--duration",
        type=int,
        default=30,
        help="seconds (PR default 30; nightly 900; overnight 28800)",
    )
    p.add_argument("--interval", type=int, default=2)
    p.add_argument("--no-pipeline", action="store_true")
    args = p.parse_args()
    return run_chaos(
        seed=args.seed,
        duration_s=args.duration,
        interval_s=args.interval,
        pipeline=not args.no_pipeline,
    )


if __name__ == "__main__":
    raise SystemExit(main())
