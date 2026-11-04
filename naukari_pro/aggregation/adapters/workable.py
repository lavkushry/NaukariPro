"""Workable widget API adapter."""

from __future__ import annotations

from typing import Any, Dict, List

from naukari_pro.aggregation.adapters._http import http_json
from naukari_pro.aggregation.base import AdapterRegistry, BaseATSAdapter, FetchResult, SourceRecord


@AdapterRegistry.register("workable")
class WorkableAdapter(BaseATSAdapter):
    ats_type = "workable"

    async def fetch_jobs(self, source: SourceRecord) -> FetchResult:
        account = source.board_identifier.strip()
        if not account:
            return FetchResult(error="missing board_identifier")
        url = f"https://apply.workable.com/api/v1/widget/accounts/{account}"
        code, data = await http_json(url, timeout=self.timeout)
        if code == 404:
            return FetchResult(status_code=404, board_missing=True, error="board not found")
        if code != 200 or not isinstance(data, dict):
            return FetchResult(status_code=code, error=f"workable http {code}")
        jobs_raw: List[Dict[str, Any]] = data.get("jobs") or []
        out = []
        for j in jobs_raw:
            jid = str(j.get("shortcode") or j.get("id") or "")
            if not jid:
                continue
            abs_url = j.get("url") or f"https://apply.workable.com/{account}/j/{jid}/"
            loc = j.get("location") or j.get("city")
            if isinstance(loc, dict):
                loc = loc.get("city") or loc.get("location_str")
            out.append(
                self.normalize_common(
                    external_job_id=jid,
                    source=source,
                    company=source.company,
                    title=j.get("title") or "",
                    url=abs_url,
                    location=loc if isinstance(loc, str) else None,
                    description_full=None,
                    published_at=j.get("published_on") or j.get("created_at"),
                    employment_type=j.get("employment_type"),
                    salary=None,
                    experience_required=None,
                    raw={"workable": jid},
                )
            )
        return FetchResult(jobs=out, status_code=200)
