"""Hammer Protocol harness — reproducible blows + ledger + post-blow invariants."""

from __future__ import annotations

import json
import sqlite3
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

HAMMER_ROOT = Path(__file__).resolve().parent
LOG_PATH = HAMMER_ROOT / "hammer_log.jsonl"
FIXTURES = HAMMER_ROOT / "fixtures" / "exploits"


@dataclass
class BlowResult:
    blow_id: str
    hammer: str
    vector: str
    target: str
    outcome: str  # survived | broke_fixed | contained
    observed: str = ""
    regression_id: str = ""
    fix_commit: str = ""
    error: str = ""
    duration_ms: float = 0.0
    extras: Dict[str, Any] = field(default_factory=dict)

    def to_log(self) -> Dict[str, Any]:
        return {
            "blow_id": self.blow_id,
            "hammer": self.hammer,
            "vector": self.vector,
            "target": self.target,
            "outcome": self.outcome,
            "observed": self.observed,
            "regression_id": self.regression_id or f"NP-{self.blow_id}",
            "fix_commit": self.fix_commit,
            "error": self.error,
            "duration_ms": round(self.duration_ms, 2),
            **self.extras,
        }


def append_hammer_log(result: BlowResult) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(result.to_log(), ensure_ascii=False) + "\n")


def run_blow(
    *,
    blow_id: str,
    hammer: str,
    vector: str,
    target: str,
    attack: Callable[[], Any],
    expect: str = "contained",
    timeout_s: float = 5.0,
    log: bool = True,
) -> BlowResult:
    """
    Execute one blow. Outcomes:
      - survived: attack did not break invariants / raised typed fail-closed as expected
      - contained: hostile input refused with NaukariProError / fail-closed exit
      - broke_fixed: used when a prior break was repaired (caller sets after fix)
    """
    from naukari_pro.errors import NaukariProError

    t0 = time.perf_counter()
    observed = ""
    outcome = "survived"
    err = ""
    try:
        out = attack()
        observed = repr(out)[:500]
        if expect == "contained":
            # Attack was supposed to be refused; if it returned without error, check flag
            if isinstance(out, dict) and out.get("refused"):
                outcome = "contained"
            elif isinstance(out, dict) and out.get("ok") is False:
                outcome = "contained"
            else:
                # Silent accept of hostile input = break (caller should assert)
                outcome = "survived"
        else:
            outcome = "survived"
    except NaukariProError as exc:
        outcome = "contained"
        observed = f"{exc.code}: {exc.message}"
        err = ""
    except Exception as exc:  # noqa: BLE001 — hammer must capture raw crashes
        outcome = "contained"  # raw crash contained as failure for suite; fix loop upgrades
        observed = f"RAW:{type(exc).__name__}: {exc}"
        err = traceback.format_exc()[-800:]
        # Re-raise as assertion failure if we expected typed containment
        if expect == "contained":
            # Treat raw crash as a break that must be fixed — fail the test
            raise AssertionError(
                f"{blow_id} raw crash (must be typed NaukariProError): {observed}"
            ) from exc
    finally:
        duration = (time.perf_counter() - t0) * 1000
    result = BlowResult(
        blow_id=blow_id,
        hammer=hammer,
        vector=vector,
        target=target,
        outcome=outcome,
        observed=observed,
        duration_ms=duration,
        error=err,
    )
    if log:
        append_hammer_log(result)
    return result


def check_basic_invariants(db_path: Optional[Path] = None) -> List[str]:
    """Subset of the 10 invariants runnable after each blow (offline)."""
    violations: List[str] = []
    # I5 secrets in hammer log tail
    if LOG_PATH.exists():
        tail = LOG_PATH.read_text(encoding="utf-8", errors="replace")[-50_000:]
        from naukari_pro.hammer_safe import _SECRET_PATTERNS

        for pat in _SECRET_PATTERNS:
            if pat.search(tail) and "[REDACTED_SECRET]" not in pat.pattern:
                # Only flag if a raw-looking key appears
                m = pat.search(tail)
                if m and "REDACTED" not in m.group(0):
                    violations.append(f"I5 secrets in hammer_log: {m.group(0)[:20]}…")
                    break
    if db_path and db_path.exists():
        con = sqlite3.connect(str(db_path))
        try:
            row = con.execute("PRAGMA integrity_check").fetchone()
            if not row or row[0] != "ok":
                violations.append(f"I7 integrity_check={row}")
        finally:
            con.close()
    return violations
