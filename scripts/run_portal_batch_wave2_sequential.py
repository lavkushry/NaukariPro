#!/usr/bin/env python3
"""Wave-2: ≥10 live career-portal applies one-by-one with step records.

Workday / Greenhouse / Lever / Ashby via CareerPortalFiller.fill.
Does not invent candidate facts. Dual-logs into applied_jobs.db.
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
LOG_PATH = EVIDENCE_DIR / "portal_batch_wave2.jsonl"
SUMMARY_PATH = EVIDENCE_DIR / "portal_batch_wave2_summary.json"

# Live HTTP-200 URLs verified 2026-11-14. Mix of Workday / Greenhouse / Lever / Ashby.
JOBS: List[Dict[str, Any]] = [
    {
        "company": "Cloudflare",
        "title": "Data Engineer",
        "ats": "Greenhouse",
        "url": "https://boards.greenhouse.io/cloudflare/jobs/8055118",
        "allow_retry": True,
        "note": "Re-drain after GH relocate/sponsorship select label fix",
    },
    {
        "company": "GitLab",
        "title": "Intermediate Data Engineer",
        "ats": "Greenhouse",
        "url": "https://job-boards.greenhouse.io/gitlab/jobs/8924923002",
        "allow_retry": False,
    },
    {
        "company": "Twilio",
        "title": "DevOps Engineer (Observability)",
        "ats": "Greenhouse",
        "url": "https://job-boards.greenhouse.io/twilio/jobs/8108771",
        "allow_retry": False,
    },
    {
        "company": "Figma",
        "title": "Support Engineer, AI Infrastructure & Tooling",
        "ats": "Greenhouse",
        "url": "https://boards.greenhouse.io/figma/jobs/5802956004",
        "allow_retry": False,
    },
    {
        "company": "Asana",
        "title": "Data Engineer",
        "ats": "Greenhouse",
        "url": "https://boards.greenhouse.io/asana/jobs/8131896",
        "allow_retry": False,
    },
    {
        "company": "Databricks",
        "title": "Senior Software Engineer (Data Platform)",
        "ats": "Greenhouse",
        "url": "https://job-boards.greenhouse.io/databricks/jobs/7647369002",
        "allow_retry": False,
    },
    {
        "company": "Databricks",
        "title": "Senior Software Engineer (Infra)",
        "ats": "Greenhouse",
        "url": "https://job-boards.greenhouse.io/databricks/jobs/7619810002",
        "allow_retry": False,
    },
    {
        "company": "Palantir",
        "title": "DevOps Engineer",
        "ats": "Lever",
        "url": "https://jobs.lever.co/palantir/51ea4a3b-7764-4c87-96e4-310e19c856d5",
        "allow_retry": False,
    },
    {
        "company": "Palantir",
        "title": "Edge Infrastructure Engineer",
        "ats": "Lever",
        "url": "https://jobs.lever.co/palantir/3d06b4bc-6a7b-4f73-b5c5-4544354e3d0f",
        "allow_retry": False,
    },
    {
        "company": "Sentry",
        "title": "Senior Software Engineer, AI Platform",
        "ats": "Ashby",
        "url": "https://jobs.ashbyhq.com/sentry/6eb8d5f2-977e-4ff4-bdbe-fccb8747b5d7",
        "allow_retry": False,
    },
    {
        "company": "Browserbase",
        "title": "Software Engineer (Core Infrastructure)",
        "ats": "Ashby",
        "url": "https://jobs.ashbyhq.com/browserbase/bcbf0fb9-2405-497b-bbc9-e09d8f7a4963",
        "allow_retry": True,
    },
    {
        "company": "Fractal Analytics",
        "title": "Senior AWS DevOps Platform Engineer",
        "ats": "Workday",
        "url": "https://fractal.wd1.myworkdayjobs.com/en-US/Careers/job/Bengaluru/Senior-AWS-DevOps---Platform-Engineer_R25053",
        "allow_retry": True,
        "note": "Workday vault / applyManually drain retry",
    },
    {
        "company": "Illumina",
        "title": "Senior Data Engineer",
        "ats": "Workday",
        "url": "https://illumina.wd1.myworkdayjobs.com/en-US/illumina-careers/job/Senior-Data-Engineer_43471-JOB",
        "allow_retry": True,
        "note": "Workday wizard timeout retry with 900s budget",
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
        "note": job.get("note"),
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

    parser = argparse.ArgumentParser(description="Wave-2 sequential career-portal apply batch")
    parser.add_argument("--start-at", type=int, default=1, help="1-based job index to start from")
    parser.add_argument("--only", type=int, nargs="*", help="Optional 1-based indices to run exclusively")
    args = parser.parse_args()

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    start_at = max(1, int(args.start_at or 1))
    only = set(int(x) for x in (args.only or []))

    _append_step(
        {
            "event": "batch_start",
            "wave": 2,
            "ts": _now(),
            "job_count": len(JOBS),
            "start_at": start_at,
            "only": sorted(only) if only else None,
            "budget_note": "PER_JOB_TIME_BUDGET_SEC=900; GH select label fix; Workday vault retry",
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
        "wave": 2,
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
    _append_step(
        {"event": "batch_complete", "wave": 2, "ts": _now(), "summary_path": str(SUMMARY_PATH), "by_status": summary["by_status"]}
    )
    print("\n===== WAVE2 BATCH COMPLETE =====", flush=True)
    print(json.dumps(summary["by_status"], indent=2), flush=True)
    print(f"summary → {SUMMARY_PATH}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
