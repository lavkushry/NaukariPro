"""SmartRecruiters public postings API."""

from __future__ import annotations

from typing import Any, Dict, List

from naukari_pro.aggregation.adapters._http import http_json
from naukari_pro.aggregation.base import AdapterRegistry, BaseATSAdapter, FetchResult, SourceRecord


@AdapterRegistry.register("smartrecruiters")
class SmartRecruitersAdapter(BaseATSAdapter):
    ats_type = "smartrecruiters"

    async def fetch_jobs(self, source: SourceRecord) -> FetchResult:
        company = source.board_identifier.strip()
        if not company:
            return FetchResult(error="missing board_identifier")
        url = f"https://api.smartrecruiters.com/v1/companies/{company}/postings"
        code, data = await http_json(url, timeout=self.timeout)
        if code == 404:
            return FetchResult(status_code=404, board_missing=True, error="board not found")
        if code != 200 or not isinstance(data, dict):
            return FetchResult(status_code=code, error=f"smartrecruiters http {code}")
        jobs_raw: List[Dict[str, Any]] = data.get("content") or []
        out = []
        for j in jobs_raw:
            jid = str(j.get("id") or j.get("uuid") or "")
            if not jid:
                continue
            loc = None
            loc_obj = j.get("location") or {}
            if isinstance(loc_obj, dict):
                parts = [loc_obj.get("city"), loc_obj.get("region"), loc_obj.get("country")]
                loc = ", ".join(p for p in parts if p) or None
            abs_url = (j.get("ref") or {}).get("jobAd") if isinstance(j.get("ref"), dict) else None
            abs_url = abs_url or j.get("applyUrl") or ""
            out.append(
                self.normalize_common(
                    external_job_id=jid,
                    source=source,
                    company=source.company,
                    title=j.get("name") or "",
                    url=abs_url,
                    location=loc,
                    description_full=None,  # detail endpoint needed — leave NULL
                    published_at=j.get("releasedDate"),
                    employment_type=(j.get("typeOfEmployment") or {}).get("label")
                    if isinstance(j.get("typeOfEmployment"), dict) else None,
                    salary=None,
                    experience_required=None,
                    raw={"sr_id": jid},
                )
            )
        return FetchResult(jobs=out, status_code=200)
