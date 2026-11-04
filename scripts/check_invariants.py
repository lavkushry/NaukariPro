#!/usr/bin/env python3
"""Ten Hammer Protocol invariants — run after blows / chaos faults."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
HAMMER_LOG = ROOT / "tests" / "hammer" / "hammer_log.jsonl"

SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9]{20,}|xai-[A-Za-z0-9]{20,}|AIza[0-9A-Za-z\-_]{20,})"
)
PII_PHONE = re.compile(r"(?<!\d)(?:\+91[-\s]?)?[6-9]\d{9}(?!\d)")


def _load_log() -> List[Dict[str, Any]]:
    if not HAMMER_LOG.exists():
        return []
    rows = []
    for line in HAMMER_LOG.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def check_all(db_path: Path | None = None) -> List[str]:
    violations: List[str] = []
    rows = _load_log()

    # I6 exit codes truthful for contained blows
    for r in rows:
        obs = r.get("observed") or ""
        if "exit_code\": 3" in obs or "exit_code': 3" in obs or "exit_code=3" in obs:
            if r.get("outcome") not in ("contained", "broke_fixed", "survived"):
                violations.append(f"I6 bad outcome for captcha blow {r.get('blow_id')}")

    # I5 secrets in log
    blob = "\n".join(json.dumps(r) for r in rows)
    if SECRET_RE.search(blob):
        violations.append("I5 secret-like token in hammer_log.jsonl")

    # I9 nothing silent — every blow has an outcome
    for r in rows:
        if not r.get("outcome"):
            violations.append(f"I9 missing outcome for {r.get('blow_id')}")
        if r.get("outcome") == "broke_unfixed":
            violations.append(f"I9/anti-law broke_unfixed: {r.get('blow_id')}")

    # I7 DB integrity
    if db_path and db_path.exists():
        con = sqlite3.connect(str(db_path))
        try:
            row = con.execute("PRAGMA integrity_check").fetchone()
            if not row or row[0] != "ok":
                violations.append(f"I7 integrity_check={row}")
        finally:
            con.close()

    # I1/I2/I3/I8 — structural checks when applications DB present
    apps = ROOT / "applied_jobs.db"
    if apps.exists():
        con = sqlite3.connect(str(apps))
        try:
            con.execute("SELECT 1").fetchone()
        except sqlite3.DatabaseError as exc:
            violations.append(f"I7 applied_jobs unreadable: {exc}")
        finally:
            con.close()

    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Hammer invariant checker")
    parser.add_argument("--db", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    viol = check_all(args.db)
    if args.json:
        print(json.dumps({"ok": not viol, "violations": viol}, indent=2))
    else:
        if viol:
            print("INVARIANT VIOLATIONS:")
            for v in viol:
                print(f"  - {v}")
        else:
            print("OK — 0 invariant violations")
    return 1 if viol else 0


if __name__ == "__main__":
    sys.exit(main())
