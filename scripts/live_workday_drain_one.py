#!/usr/bin/env python3
"""Live single Workday/external apply for autonomy proof."""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")
os.environ.setdefault("CAPTCHA_HUMAN_WAIT_SEC", "90")


def main() -> int:
    from naukari_pro.modules.autonomous_loop import list_incomplete_portal_jobs
    from naukari_pro.modules.career_portals import CareerPortalFiller, FillResult

    rows = list_incomplete_portal_jobs(limit=30)
    # Prefer Workday Ready-for-Review / SUBMIT_NOT_FOUND (skip CAPTCHA first)
    pick = None
    for r in rows:
        url = (r.get("job_url") or "").lower()
        st = r.get("status") or ""
        if "captcha" in st.lower():
            continue
        if "workday" in url or "myworkday" in url:
            pick = r
            break
    if not pick:
        for r in rows:
            if "CAPTCHA" not in (r.get("status") or ""):
                pick = r
                break
    if not pick:
        print("No incomplete non-CAPTCHA portal rows to drain.")
        return 2

    url = pick["job_url"]
    company = pick.get("company") or "Company"
    role = pick.get("title") or "Role"
    print(f"[LIVE DRAIN] {role} @ {company}")
    print(f"  url={url}")
    print(f"  prior_status={pick.get('status')}")

    filler = CareerPortalFiller()
    try:
        res = filler.fill(
            portal_url=url,
            company=company,
            role=role,
            headless=True,
            dry_run=False,
            match_score=int(float(pick.get("match_score") or 75)),
            auto_submit=True,
        )
    except Exception:
        traceback.print_exc()
        return 1

    if isinstance(res, FillResult):
        print(f"RESULT success={res.success} status={res.status} evidence={res.evidence_path}")
        return 0 if res.success or (res.status and "Submitted" in res.status) else 3
    print("RESULT", res)
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
