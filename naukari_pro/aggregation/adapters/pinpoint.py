"""Pinpoint jobs JSON: https://{org}.pinpointhq.com/postings.json"""

from __future__ import annotations

from typing import Any, Dict, List

from naukari_pro.aggregation.adapters._http import http_json
from naukari_pro.aggregation.base import AdapterRegistry, BaseATSAdapter, FetchResult, SourceRecord


@AdapterRegistry.register("pinpoint")
class PinpointAdapter(BaseATSAdapter):
    ats_type = "pinpoint"

    async def fetch_jobs(self, source: SourceRecord) -> FetchResult:
        org = source.board_identifier.strip()
        if not org:
            return FetchResult(error="missing board_identifier")
        url = f"https://{org}.pinpointhq.com/postings.json"
        code, data = await http_json(url, timeout=self.timeout)
        if code == 404:
            return FetchResult(status_code=404, board_missing=True, error="board not found")
        if code != 200:
            return FetchResult(status_code=code, error=f"pinpoint http {code}")
        jobs_raw: List[Dict[str, Any]] = data if isinstance(data, list) else (data.get("data") if isinstance(data, dict) else [])
        out = []
        for j in jobs_raw or []:
            if not isinstance(j, dict):
                continue
            jid = str(j.get("id") or j.get("key") or "")
            if not jid:
                continue
            title = j.get("title") or ""
            abs_url = j.get("url") or j.get("careers_url") or ""
            loc = j.get("location") or j.get("workplace_type")
            if isinstance(loc, dict):
                loc = loc.get("name")
            desc = j.get("description") or j.get("key_responsibilities")
            out.append(
                self.normalize_common(
                    external_job_id=jid,
                    source=source,
                    company=source.company,
                    title=title,
                    url=abs_url,
                    location=loc if isinstance(loc, str) else None,
                    description_full=desc if desc else None,
                    published_at=j.get("created_at") or j.get("published_at"),
                    salary=None,
                    experience_required=None,
                    raw={"pinpoint": jid},
                )
            )
        return FetchResult(jobs=out, status_code=200)
