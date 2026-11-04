"""Recruitee offers API: https://{company}.recruitee.com/api/offers"""

from __future__ import annotations

from typing import Any, Dict, List

from naukari_pro.aggregation.adapters._http import http_json
from naukari_pro.aggregation.base import AdapterRegistry, BaseATSAdapter, FetchResult, SourceRecord


@AdapterRegistry.register("recruitee")
class RecruiteeAdapter(BaseATSAdapter):
    ats_type = "recruitee"

    async def fetch_jobs(self, source: SourceRecord) -> FetchResult:
        company = source.board_identifier.strip()
        if not company:
            return FetchResult(error="missing board_identifier")
        url = f"https://{company}.recruitee.com/api/offers"
        code, data = await http_json(url, timeout=self.timeout)
        if code == 404:
            return FetchResult(status_code=404, board_missing=True, error="board not found")
        if code != 200 or not isinstance(data, dict):
            return FetchResult(status_code=code, error=f"recruitee http {code}")
        jobs_raw: List[Dict[str, Any]] = data.get("offers") or []
        out = []
        for j in jobs_raw:
            jid = str(j.get("id") or "")
            if not jid:
                continue
            abs_url = j.get("careers_url") or j.get("url") or ""
            loc = j.get("location")
            desc = j.get("description") or j.get("requirements")
            out.append(
                self.normalize_common(
                    external_job_id=jid,
                    source=source,
                    company=source.company,
                    title=j.get("title") or "",
                    url=abs_url,
                    location=loc if isinstance(loc, str) else None,
                    remote=j.get("remote"),
                    description_full=desc if desc else None,
                    departments=[j.get("department")] if j.get("department") else [],
                    published_at=j.get("published_at") or j.get("created_at"),
                    employment_type=j.get("employment_type_code"),
                    salary=None,
                    experience_required=None,
                    raw={"recruitee_id": jid},
                )
            )
        return FetchResult(jobs=out, status_code=200)
