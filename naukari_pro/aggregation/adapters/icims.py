"""iCIMS public search JSON (best-effort; many boards need portal-specific hosts)."""

from __future__ import annotations

from typing import Any, Dict, List

from naukari_pro.aggregation.adapters._http import http_json
from naukari_pro.aggregation.base import AdapterRegistry, BaseATSAdapter, FetchResult, SourceRecord


@AdapterRegistry.register("icims")
class ICIMSAdapter(BaseATSAdapter):
    ats_type = "icims"

    async def fetch_jobs(self, source: SourceRecord) -> FetchResult:
        # board_identifier = host e.g. careers-company.icims.com
        host = source.board_identifier.strip().removeprefix("https://").removeprefix("http://")
        if not host:
            return FetchResult(error="missing board_identifier")
        # Common iCIMS JSON search endpoint pattern
        url = f"https://{host}/jobs/search?ss=1&in_iframe=1&searchKeyword=&searchLocation=&mobile=false&pageSize=100"
        # Prefer JSON API if available
        api = f"https://{host}/api/jobs?pr=0&schemaId=&fields=id,url,title,location,updatedDate"
        code, data = await http_json(api, timeout=self.timeout)
        if code == 404:
            # fallback — mark missing only if both fail
            code2, _ = await http_json(url, timeout=self.timeout)
            if code2 == 404:
                return FetchResult(status_code=404, board_missing=True, error="board not found")
            return FetchResult(status_code=code2, error="icims json api unavailable", jobs=[])
        if code != 200:
            return FetchResult(status_code=code, error=f"icims http {code}")
        jobs_raw: List[Dict[str, Any]] = []
        if isinstance(data, dict):
            jobs_raw = data.get("jobs") or data.get("searchResults") or data.get("data") or []
        elif isinstance(data, list):
            jobs_raw = data
        out = []
        for j in jobs_raw or []:
            if not isinstance(j, dict):
                continue
            jid = str(j.get("id") or j.get("jobId") or "")
            if not jid:
                continue
            title = j.get("title") or j.get("jobTitle") or ""
            abs_url = j.get("url") or j.get("overviewUrl") or f"https://{host}/jobs/{jid}"
            loc = j.get("location") or j.get("jobLocation")
            if isinstance(loc, dict):
                loc = loc.get("label") or loc.get("name")
            out.append(
                self.normalize_common(
                    external_job_id=jid,
                    source=source,
                    company=source.company,
                    title=title if isinstance(title, str) else str(title),
                    url=abs_url if isinstance(abs_url, str) else str(abs_url),
                    location=loc if isinstance(loc, str) else None,
                    description_full=None,
                    published_at=j.get("updatedDate") or j.get("postedDate"),
                    salary=None,
                    experience_required=None,
                    raw={"icims": jid},
                )
            )
        return FetchResult(jobs=out, status_code=200)
