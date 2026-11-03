#!/usr/bin/env python3
"""H8 — Reconcile applied_jobs.db vs Naukri_Live_Application_Tracker.xlsx."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Set, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from naukari_pro.config import DB_PATH, TRACKER_PATH
from naukari_pro.modules.db import get_db_connection, init_db


def _norm(s: Any) -> str:
    return " ".join(str(s or "").lower().split())


def load_excel_keys(path: str) -> Set[Tuple[str, str, str]]:
    import openpyxl

    keys: Set[Tuple[str, str, str]] = set()
    if not os.path.exists(path):
        return keys
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    for sheet in ("Applications_Log", "LinkedIn_Applications_Log"):
        if sheet not in wb.sheetnames:
            continue
        ws = wb[sheet]
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row:
                continue
            date_s = str(row[0] or "")[:10]
            company = _norm(row[1])
            title = _norm(row[2])
            if company and title:
                keys.add((company, title, date_s))
    wb.close()
    return keys


def load_db_keys(db_path: str) -> Set[Tuple[str, str, str]]:
    init_db(db_path)
    conn = get_db_connection(db_path)
    keys: Set[Tuple[str, str, str]] = set()
    try:
        for row in conn.execute(
            "SELECT company, title, substr(COALESCE(applied_at,''), 1, 10) FROM applied_jobs"
        ):
            company = _norm(row[0])
            title = _norm(row[1])
            date_s = str(row[2] or "")
            if company and title:
                keys.add((company, title, date_s))
    finally:
        conn.close()
    return keys


def audit_confirmed_evidence(db_path: str) -> List[Dict[str, Any]]:
    """Downgrade Submitted (Confirmed) rows lacking valid PNG header."""
    init_db(db_path)
    conn = get_db_connection(db_path)
    downgraded: List[Dict[str, Any]] = []
    try:
        rows = conn.execute(
            "SELECT job_id, evidence_path, status FROM applied_jobs WHERE status = 'Submitted (Confirmed)'"
        ).fetchall()
        for r in rows:
            ep = r["evidence_path"]
            ok = False
            if ep and os.path.isfile(ep) and os.path.getsize(ep) >= 1024:
                with open(ep, "rb") as f:
                    ok = f.read(8) == b"\x89PNG\r\n\x1a\n"
            if not ok:
                conn.execute(
                    "UPDATE applied_jobs SET status = ?, evidence_path = NULL WHERE job_id = ?",
                    ("Form Auto-Filled (Ready for Review)", r["job_id"]),
                )
                downgraded.append({"job_id": r["job_id"], "evidence_path": ep})
        conn.commit()
    finally:
        conn.close()
    return downgraded


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile DB ↔ Excel tracker")
    parser.add_argument("--db", default=DB_PATH)
    parser.add_argument("--excel", default=TRACKER_PATH)
    parser.add_argument("--audit-evidence", action="store_true")
    args = parser.parse_args()

    excel_keys = load_excel_keys(args.excel)
    db_keys = load_db_keys(args.db)
    only_excel = excel_keys - db_keys
    only_db = db_keys - excel_keys

    print("=" * 64)
    print(f"  RECONCILE @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Excel keys: {len(excel_keys)} | DB keys: {len(db_keys)}")
    print(f"  Only in Excel: {len(only_excel)} | Only in DB: {len(only_db)}")
    print("=" * 64)
    for i, k in enumerate(sorted(only_excel)[:15], 1):
        print(f"  EXCEL-ONLY {i}: {k}")
    for i, k in enumerate(sorted(only_db)[:15], 1):
        print(f"  DB-ONLY {i}: {k}")

    if args.audit_evidence:
        down = audit_confirmed_evidence(args.db)
        print(f"  Evidence audit downgraded: {len(down)}")
        for d in down[:10]:
            print(f"    - {d['job_id']}: {d['evidence_path']}")

    return 0 if not only_excel and not only_db else 1


if __name__ == "__main__":
    raise SystemExit(main())
