#!/usr/bin/env python3
"""Apply ≥10 live career-portal jobs one-by-one; record steps to JSONL + screenshots.

Uses the same CareerPortalFiller.fill path for Workday / Greenhouse / Lever / Ashby.
Does not invent candidate facts. Persists outcomes via filler dual-log into applied_jobs.db.
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")
os.environ.setdefault("CAPTCHA_HUMAN_WAIT_SEC", "120")

EVIDENCE_DIR = ROOT / "evidence"
LOG_PATH = EVIDENCE_DIR / "portal_batch_10.jsonl"
SUMMARY_PATH = EVIDENCE_DIR / "portal_batch_10_summary.json"

# Live HTTP-200 URLs verified 2026-11-14. Mix of Workday / Greenhouse / Lever / Ashby.
JOBS: List[Dict[str, Any]] = [
    {
        "company": "ResMed",
        "title": "Machine Learning Ops Engineer",
        "ats": "Workday",
        "url": "https://resmed.wd3.myworkdayjobs.com/en-US/ResMed_External_Careers/job/Bangalore-India/Machine-Learning-Ops-Engineer_JR_053664",
        "allow_retry": False,
    },
    {
        "company": "Ecolab",
        "title": "AI engineer Databricks Data Platform",
        "ats": "Workday",
        "url": "https://ecolab.wd1.myworkdayjobs.com/en-US/Ecolab_External/job/AI-engineer-Databricks-Data-Platform_R00305094",
        "allow_retry": False,
    },
    {
        "company": "Illumina",
        "title": "Senior Data Engineer",
        "ats": "Workday",
        "url": "https://illumina.wd1.myworkdayjobs.com/en-US/illumina-careers/job/Senior-Data-Engineer_43471-JOB",
        "allow_retry": False,
    },
    {
        "company": "Fractal Analytics",
        "title": "Senior AWS DevOps Platform Engineer",
        "ats": "Workday",
        "url": "https://fractal.wd1.myworkdayjobs.com/en-US/Careers/job/Bengaluru/Senior-AWS-DevOps---Platform-Engineer_R25053",
        "allow_retry": True,
    },
    {
        "company": "Dyson",
        "title": "Lead MLOps Engineer",
        "ats": "Workday",
        "url": "https://dyson.wd3.myworkdayjobs.com/en-US/dyson_careers/job/Lead-Mlops-Engineer_JR38502",
        "allow_retry": False,
    },
    {
        "company": "Cloudflare",
        "title": "Data Engineer",
        "ats": "Greenhouse",
        "url": "https://boards.greenhouse.io/cloudflare/jobs/8055118",
        "allow_retry": False,
    },
    {
        "company": "Databricks",
        "title": "Staff Software Engineer - Data Platform",
        "ats": "Greenhouse",
        "url": "https://job-boards.greenhouse.io/databricks/jobs/7601572002",
        "allow_retry": False,
    },
    {
        "company": "Nift",
        "title": "ML Ops Engineer",
        "ats": "Greenhouse",
        "url": "https://job-boards.greenhouse.io/nift/jobs/5234369007",
        "allow_retry": False,
    },
    {
        "company": "Acceldata",
        "title": "Staff Platform Engineer",
        "ats": "Lever",
        "url": "https://jobs.lever.co/acceldata/63634645-c457-4c73-a1bd-7bc8e1dc18c8",
        "allow_retry": False,
    },
    {
        "company": "ValGenesis",
        "title": "Senior Software Engineer, Data Engineering",
        "ats": "Lever",
        "url": "https://jobs.lever.co/valgenesis/3bab8728-3f05-4db5-8b51-4a3d77187313",
        "allow_retry": False,
    },
    {
        "company": "Triomics",
        "title": "MLOps & Data Engineer",
        "ats": "Ashby",
        "url": "https://jobs.ashbyhq.com/triomics/1f3e01da-3f06-44db-b736-df3ce40aec86",
        "allow_retry": False,
    },
    {
        "company": "Browserbase",
        "title": "Software Engineer (Agent Platform)",
        "ats": "Ashby",
        "url": "https://jobs.ashbyhq.com/browserbase/7724fbe3-6a27-4418-9705-2dcc40751a16",
        "allow_retry": False,
    },
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_step(record: Dict[str, Any]) -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        fh.flush()


def _serialize_result(res: Any) -> Dict[str, Any]:
    if res is None:
        return {"success": False, "status": "NONE", "fields": [], "evidence_path": None}
    success = getattr(res, "success", None)
    if success is None and isinstance(res, (tuple, list)) and res:
        success = bool(res[0])
    fields = getattr(res, "fields", None)
    if fields is None and isinstance(res, (tuple, list)) and len(res) > 1:
        fields = res[1]
    return {
        "success": bool(success),
        "status": getattr(res, "status", None),
        "fields": list(fields or [])[:80],
        "evidence_path": getattr(res, "evidence_path", None),
        "field_record_count": len(getattr(res, "field_records", None) or []),
    }


def apply_one(job: Dict[str, Any], index: int, total: int) -> Dict[str, Any]:
    from naukari_pro.modules.career_portals import CareerPortalFiller, FillResult

    company = job["company"]
    title = job["title"]
    url = job["url"]
    ats = job["ats"]
    allow_retry = bool(job.get("allow_retry"))

    started = _now()
    t0 = time.time()
    step_start = {
        "event": "job_start",
        "index": index,
        "total": total,
        "company": company,
        "title": title,
        "ats": ats,
        "url": url,
        "allow_retry": allow_retry,
        "ts": started,
    }
    _append_step(step_start)
    print(f"\n===== [{index}/{total}] {ats} | {title} @ {company} =====", flush=True)
    print(f"  url={url}", flush=True)

    filler = CareerPortalFiller()
    error: Optional[str] = None
    res: Any = None
    try:
        res = filler.fill(
            portal_url=url,
            company=company,
            role=title,
            headless=True,
            dry_run=False,
            match_score=78,
            auto_submit=True,
            allow_retry=allow_retry,
        )
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"
        traceback.print_exc()

    elapsed = round(time.time() - t0, 1)
    payload = _serialize_result(res)
    record = {
        "event": "job_end",
        "index": index,
        "total": total,
        "company": company,
        "title": title,
        "ats": ats,
        "url": url,
        "started_at": started,
        "ended_at": _now(),
        "elapsed_sec": elapsed,
        "error": error,
        **payload,
        "result_type": type(res).__name__ if res is not None else None,
        "is_fill_result": isinstance(res, FillResult) if res is not None else False,
    }
    _append_step(record)
    print(
        f"  DONE success={record.get('success')} status={record.get('status')} "
        f"elapsed={elapsed}s evidence={record.get('evidence_path')}",
        flush=True,
    )
    return record


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Sequential career-portal apply batch")
    parser.add_argument("--start-at", type=int, default=1, help="1-based job index to start from")
    parser.add_argument("--only", type=int, nargs="*", help="Optional 1-based indices to run exclusively")
    args = parser.parse_args()

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    start_at = max(1, int(args.start_at or 1))
    only = set(int(x) for x in (args.only or []))

    # Seed run marker
    _append_step(
        {
            "event": "batch_start",
            "ts": _now(),
            "job_count": len(JOBS),
            "start_at": start_at,
            "only": sorted(only) if only else None,
            "budget_note": "PER_JOB_TIME_BUDGET_SEC raised to 900 in career_portals.py",
            "prior_confirmed": [
                {
                    "company": "Embitel Technologies",
                    "title": "MLOps Engineer",
                    "ats": "Workday",
                    "status": "Submitted (Confirmed)",
                    "note": "Prior live confirm Job_Application_ID present in applied_jobs.db",
                },
                {
                    "company": "Databricks",
                    "title": "Evergreen - AI Engineer, AI FDE",
                    "ats": "Greenhouse",
                    "status": "Submitted (Confirmed)",
                    "note": "Prior live Greenhouse confirm in applied_jobs.db",
                },
            ],
        }
    )

    results: List[Dict[str, Any]] = []
    total = len(JOBS)
    for i, job in enumerate(JOBS, start=1):
        if only and i not in only:
            continue
        if not only and i < start_at:
            continue
        results.append(apply_one(job, i, total))

    confirmed = [r for r in results if r.get("status") and "Submitted" in str(r.get("status"))]
    summary = {
        "event": "batch_complete",
        "ts": _now(),
        "attempted": len(results),
        "confirmed_or_submitted": len(confirmed),
        "by_status": {},
        "results": results,
        "log_path": str(LOG_PATH),
    }
    for r in results:
        st = str(r.get("status") or r.get("error") or "UNKNOWN")
        summary["by_status"][st] = summary["by_status"].get(st, 0) + 1

    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    _append_step({"event": "batch_complete", "ts": _now(), "summary_path": str(SUMMARY_PATH), "by_status": summary["by_status"]})
    print("\n===== BATCH COMPLETE =====", flush=True)
    print(json.dumps(summary["by_status"], indent=2), flush=True)
    print(f"summary → {SUMMARY_PATH}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
