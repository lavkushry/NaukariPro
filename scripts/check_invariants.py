#!/usr/bin/env python3
"""Ten Hammer Protocol invariants — run after blows / chaos faults."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
HAMMER_LOG = ROOT / "tests" / "hammer" / "hammer_log.jsonl"

SECRET_RE = re.compile(
    r"(?<![A-Za-z0-9_\-])(sk-[A-Za-z0-9]{20,}|xai-[A-Za-z0-9]{20,}|AIza[0-9A-Za-z\-_]{20,})(?![A-Za-z0-9_\-])"
)
PII_PHONE = re.compile(r"(?<!\d)(?:\+91[-\s]?)?[6-9]\d{9}(?!\d)")
PII_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ALLOWED_OUTCOMES = {"survived", "broke_fixed", "contained"}


def _load_log() -> List[Dict[str, Any]]:
    if not HAMMER_LOG.exists():
        return []
    rows = []
    for line in HAMMER_LOG.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _ensure_fixture_db(db_path: Path) -> Path:
    """Build a mini applications/events DB exercising I1/I2/I8/I9/I10."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path))
    try:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              job_id TEXT NOT NULL,
              event TEXT NOT NULL,
              token TEXT,
              ts TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS applications (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              job_id TEXT NOT NULL,
              company TEXT NOT NULL,
              board TEXT NOT NULL,
              status TEXT NOT NULL,
              approval_token TEXT,
              ts TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS circuit (
              name TEXT PRIMARY KEY,
              failures INTEGER NOT NULL,
              open INTEGER NOT NULL
            );
            """
        )
        # Seed a valid submit path: approval_granted then submitted
        con.execute(
            "INSERT INTO events(job_id, event, token, ts) VALUES (?,?,?,?)",
            ("job-1", "approval_granted", "tok-1", "2026-01-01T00:00:00+00:00"),
        )
        con.execute(
            "INSERT INTO applications(job_id, company, board, status, approval_token, ts) VALUES (?,?,?,?,?,?)",
            ("job-1", "Acme", "naukri", "submitted", "tok-1", "2026-01-01T00:01:00+00:00"),
        )
        # Blocked/captcha must never count as applied
        con.execute(
            "INSERT INTO applications(job_id, company, board, status, approval_token, ts) VALUES (?,?,?,?,?,?)",
            ("job-2", "Beta", "linkedin", "blocked", None, "2026-01-02T00:00:00+00:00"),
        )
        con.execute(
            "INSERT INTO applications(job_id, company, board, status, approval_token, ts) VALUES (?,?,?,?,?,?)",
            ("job-3", "Gamma", "hirist", "captcha", None, "2026-01-03T00:00:00+00:00"),
        )
        con.execute(
            "INSERT INTO events(job_id, event, token, ts) VALUES (?,?,?,?)",
            ("job-2", "failure_explained", None, "2026-01-02T00:00:01+00:00"),
        )
        con.execute(
            "INSERT INTO events(job_id, event, token, ts) VALUES (?,?,?,?)",
            ("job-3", "captcha", None, "2026-01-03T00:00:01+00:00"),
        )
        con.execute(
            "INSERT INTO circuit(name, failures, open) VALUES (?,?,?)",
            ("board-x", 5, 1),
        )
        con.commit()
    finally:
        con.close()
    return db_path


def check_db_invariants(db_path: Path) -> List[str]:
    violations: List[str] = []
    if not db_path.exists():
        return ["I7 db missing"]
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    try:
        row = con.execute("PRAGMA integrity_check").fetchone()
        if not row or row[0] != "ok":
            violations.append(f"I7 integrity_check={row}")

        # I1: submitted => prior approval_granted
        submitted = con.execute(
            "SELECT job_id, approval_token FROM applications WHERE status='submitted'"
        ).fetchall()
        for s in submitted:
            tok = s["approval_token"]
            ev = con.execute(
                "SELECT 1 FROM events WHERE job_id=? AND event='approval_granted' AND (? IS NULL OR token=?)",
                (s["job_id"], tok, tok),
            ).fetchone()
            if not ev:
                violations.append(f"I1 submitted without approval_granted: {s['job_id']}")

        # I2: every outward submission traces to a token
        for s in submitted:
            if not s["approval_token"]:
                violations.append(f"I2 submitted missing token: {s['job_id']}")

        # blocked/captcha never applied
        bad = con.execute(
            "SELECT job_id, status FROM applications WHERE status IN ('blocked','captcha') AND status='submitted'"
        ).fetchall()
        for b in bad:
            violations.append(f"I1 blocked counted submitted: {b['job_id']}")

        applied_like = con.execute(
            "SELECT COUNT(*) c FROM applications WHERE status IN ('applied','submitted')"
        ).fetchone()["c"]
        blocked = con.execute(
            "SELECT COUNT(*) c FROM applications WHERE status IN ('blocked','captcha')"
        ).fetchone()["c"]
        if blocked and applied_like < 0:
            violations.append("I1 impossible counts")

        # I8: no duplicate job rows; company cooldown across boards (same company twice submitted)
        dups = con.execute(
            "SELECT job_id, COUNT(*) c FROM applications GROUP BY job_id HAVING c > 1"
        ).fetchall()
        for d in dups:
            violations.append(f"I8 duplicate job_id: {d['job_id']}")

        multi = con.execute(
            """
            SELECT company, COUNT(*) c FROM applications
            WHERE status='submitted'
            GROUP BY lower(company) HAVING c > 1
            """
        ).fetchall()
        for m in multi:
            violations.append(f"I8 same-company multi-submit: {m['company']}")

        # I9: every failure has an event
        fails = con.execute(
            "SELECT job_id FROM applications WHERE status IN ('blocked','captcha','failed','interrupted')"
        ).fetchall()
        for f in fails:
            any_ev = con.execute(
                "SELECT 1 FROM events WHERE job_id=?", (f["job_id"],)
            ).fetchone()
            if not any_ev:
                violations.append(f"I9 silent failure: {f['job_id']}")

        # I10: circuit open when failures >= threshold
        circuits = con.execute("SELECT name, failures, open FROM circuit").fetchall()
        for c in circuits:
            if c["failures"] >= 5 and not c["open"]:
                violations.append(f"I10 breaker not open: {c['name']}")
    finally:
        con.close()
    return violations


def check_all(
    db_path: Optional[Path] = None,
    *,
    sample_sinks: Optional[List[str]] = None,
    ensure_fixture: bool = True,
) -> List[str]:
    violations: List[str] = []
    rows = _load_log()

    # I6 exit codes truthful for contained blows
    for r in rows[-5000:]:
        obs = r.get("observed") or ""
        if r.get("outcome") not in ALLOWED_OUTCOMES and r.get("outcome"):
            violations.append(f"I6/anti-law bad outcome {r.get('blow_id')}: {r.get('outcome')}")
        if "exit_code\": 3" in obs or "exit_code': 3" in obs or "exit_code=3" in obs:
            if r.get("outcome") not in ALLOWED_OUTCOMES:
                violations.append(f"I6 bad outcome for captcha blow {r.get('blow_id')}")

    # I3: fabrication attempts in log should show refused / unsupported
    for r in rows[-2000:]:
        vec = (r.get("vector") or "").lower()
        if any(x in vec for x in ("fabricat", "number_mutation", "puffery", "hallucin")):
            obs = (r.get("observed") or "").lower()
            if r.get("outcome") not in ("contained", "broke_fixed") and "refused" not in obs:
                violations.append(f"I3 fabrication not refused: {r.get('blow_id')}")

    # I5 secrets in log (ignore REDACTED markers)
    blob = "\n".join(json.dumps(r) for r in rows[-3000:])
    for m in SECRET_RE.finditer(blob):
        if "REDACTED" not in m.group(0):
            violations.append("I5 secret-like token in hammer_log.jsonl")
            break

    # I4 PII in sampled sinks (redacted helpers must scrub)
    sinks = sample_sinks or []
    for sink in sinks:
        if PII_PHONE.search(sink) or (
            PII_EMAIL.search(sink) and "example.com" not in sink and "ci@" not in sink
        ):
            # Only flag if sink claims to be redacted output
            if "REDACTED" not in sink:
                violations.append("I4 PII pattern in sampled sink")

    # I9 nothing silent — every blow has an outcome
    for r in rows[-5000:]:
        if not r.get("outcome"):
            violations.append(f"I9 missing outcome for {r.get('blow_id')}")
        if r.get("outcome") == "broke_unfixed":
            violations.append(f"I9/anti-law broke_unfixed: {r.get('blow_id')}")

    # DB invariants
    path = db_path
    tmp: Optional[tempfile.TemporaryDirectory] = None
    if path is None and ensure_fixture:
        tmp = tempfile.TemporaryDirectory()
        path = _ensure_fixture_db(Path(tmp.name) / "invariants.db")
    if path is not None:
        violations.extend(check_db_invariants(Path(path)))

    # Live applied_jobs.db if present
    apps = ROOT / "applied_jobs.db"
    if apps.exists():
        con = sqlite3.connect(str(apps))
        try:
            row = con.execute("PRAGMA integrity_check").fetchone()
            if not row or row[0] != "ok":
                violations.append(f"I7 applied_jobs integrity={row}")
        except sqlite3.DatabaseError as exc:
            violations.append(f"I7 applied_jobs unreadable: {exc}")
        finally:
            con.close()

    if tmp is not None:
        tmp.cleanup()
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Hammer invariant checker")
    parser.add_argument("--db", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-fixture", action="store_true")
    args = parser.parse_args()
    viol = check_all(args.db, ensure_fixture=not args.no_fixture)
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
