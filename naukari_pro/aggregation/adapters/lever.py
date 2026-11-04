"""Lever postings API: https://api.lever.co/v0/postings/{site}?mode=json"""

from __future__ import annotations

from typing import Any, Dict, List

from naukari_pro.aggregation.adapters._http import http_json
from naukari_pro.aggregation.base import AdapterRegistry, BaseATSAdapter, FetchResult, SourceRecord


@AdapterRegistry.register("lever")
class LeverAdapter(BaseATSAdapter):
    ats_type = "lever"

    async def fetch_jobs(self, source: SourceRecord) -> FetchResult:
        site = source.board_identifier.strip()
        if not site:
            return FetchResult(error="missing board_identifier")
        url = f"https://api.lever.co/v0/postings/{site}?mode=json"
        code, data = await http_json(url, timeout=self.timeout)
        if code == 404:
            return FetchResult(status_code=404, board_missing=True, error="board not found")
        if code != 200:
            return FetchResult(status_code=code, error=f"lever http {code}")
        jobs_raw: List[Dict[str, Any]] = data if isinstance(data, list) else []
        out = []
        for j in jobs_raw:
            jid = str(j.get("id") or "")
            if not jid:
                continue
            cats = j.get("categories") or {}
            loc = cats.get("location") if isinstance(cats, dict) else None
            team = cats.get("team") if isinstance(cats, dict) else None
            commitment = cats.get("commitment") if isinstance(cats, dict) else None
            desc_parts = []
            for key in ("descriptionPlain", "description", "lists"):
                val = j.get(key)
                if isinstance(val, str) and val.strip():
                    desc_parts.append(val)
                elif key == "lists" and isinstance(val, list):
                    for item in val:
                        if isinstance(item, dict):
                            desc_parts.append(item.get("text") or item.get("content") or "")
            desc = "\n\n".join(p for p in desc_parts if p).strip() or None
            abs_url = j.get("hostedUrl") or j.get("applyUrl") or ""
            workplace = (j.get("workplaceType") or "").lower()
            remote = True if workplace == "remote" else (False if workplace else None)
            out.append(
                self.normalize_common(
                    external_job_id=jid,
                    source=source,
                    company=source.company,
                    title=j.get("text") or "",
                    url=abs_url,
                    location=loc,
                    remote=remote,
                    description_full=desc,
                    departments=[team] if team else [],
                    employment_type=commitment,
                    published_at=str(j.get("createdAt")) if j.get("createdAt") else None,
                    salary=None,
                    experience_required=None,
                    raw={"lever_id": jid},
                )
            )
        return FetchResult(jobs=out, status_code=200)
