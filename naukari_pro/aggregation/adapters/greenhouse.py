"""Greenhouse boards-api adapter: https://boards-api.greenhouse.io/v1/boards/{token}/jobs"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from naukari_pro.aggregation.adapters._http import http_json
from naukari_pro.aggregation.base import AdapterRegistry, BaseATSAdapter, FetchResult, SourceRecord


@AdapterRegistry.register("greenhouse")
class GreenhouseAdapter(BaseATSAdapter):
    ats_type = "greenhouse"

    async def fetch_jobs(self, source: SourceRecord) -> FetchResult:
        token = source.board_identifier.strip()
        if not token:
            return FetchResult(error="missing board_identifier")
        url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
        code, data = await http_json(url, timeout=self.timeout)
        if code == 404:
            return FetchResult(status_code=404, board_missing=True, error="board not found")
        if code != 200 or not isinstance(data, dict):
            return FetchResult(status_code=code, error=f"greenhouse http {code}")

        jobs_raw: List[Dict[str, Any]] = data.get("jobs") or []
        out = []
        for j in jobs_raw:
            jid = str(j.get("id") or "")
            if not jid:
                continue
            loc = None
            if isinstance(j.get("location"), dict):
                loc = j["location"].get("name")
            elif isinstance(j.get("location"), str):
                loc = j["location"]
            abs_url = j.get("absolute_url") or ""
            content = j.get("content")  # HTML description — real when content=true
            departments = []
            for d in j.get("departments") or []:
                if isinstance(d, dict) and d.get("name"):
                    departments.append(d["name"])
            remote = None
            if loc and "remote" in loc.lower():
                remote = True
            out.append(
                self.normalize_common(
                    external_job_id=jid,
                    source=source,
                    company=source.company,
                    title=j.get("title") or "",
                    url=abs_url,
                    location=loc,
                    remote=remote,
                    description_full=content if content else None,
                    departments=departments,
                    published_at=j.get("updated_at") or j.get("created_at"),
                    salary=None,  # Greenhouse list API does not reliably expose salary
                    experience_required=None,
                    raw={"greenhouse_id": jid},
                )
            )
        return FetchResult(jobs=out, status_code=200)
