"""BambooHR careers board JSON."""

from __future__ import annotations

from typing import Any, Dict, List

from naukari_pro.aggregation.adapters._http import http_json
from naukari_pro.aggregation.base import AdapterRegistry, BaseATSAdapter, FetchResult, SourceRecord


@AdapterRegistry.register("bamboohr")
class BambooHRAdapter(BaseATSAdapter):
    ats_type = "bamboohr"

    async def fetch_jobs(self, source: SourceRecord) -> FetchResult:
        company = source.board_identifier.strip()
        if not company:
            return FetchResult(error="missing board_identifier")
        url = f"https://{company}.bamboohr.com/careers/list"
        code, data = await http_json(url, timeout=self.timeout)
        if code == 404:
            return FetchResult(status_code=404, board_missing=True, error="board not found")
        if code != 200:
            return FetchResult(status_code=code, error=f"bamboohr http {code}")
        jobs_raw: List[Dict[str, Any]] = []
        if isinstance(data, dict):
            jobs_raw = data.get("result") or data.get("meta") or data.get("jobs") or []
            if isinstance(jobs_raw, dict):
                jobs_raw = list(jobs_raw.values()) if jobs_raw else []
        out = []
        for j in jobs_raw or []:
            if not isinstance(j, dict):
                continue
            jid = str(j.get("id") or j.get("jobOpeningId") or "")
            if not jid:
                continue
            title = j.get("jobOpeningName") or j.get("title") or ""
            abs_url = j.get("jobOpeningShareUrl") or f"https://{company}.bamboohr.com/careers/{jid}"
            loc = j.get("location") or j.get("departmentLabel")
            if isinstance(loc, dict):
                loc = loc.get("city") or loc.get("name")
            out.append(
                self.normalize_common(
                    external_job_id=jid,
                    source=source,
                    company=source.company,
                    title=title,
                    url=abs_url,
                    location=loc if isinstance(loc, str) else None,
                    description_full=None,
                    departments=[j.get("departmentLabel")] if j.get("departmentLabel") else [],
                    employment_type=j.get("employmentStatusLabel"),
                    salary=None,
                    experience_required=None,
                    raw={"bamboohr": jid},
                )
            )
        return FetchResult(jobs=out, status_code=200)
