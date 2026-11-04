"""Teamtailor careers JSON feed."""

from __future__ import annotations

from typing import Any, Dict, List

from naukari_pro.aggregation.adapters._http import http_json
from naukari_pro.aggregation.base import AdapterRegistry, BaseATSAdapter, FetchResult, SourceRecord


@AdapterRegistry.register("teamtailor")
class TeamtailorAdapter(BaseATSAdapter):
    ats_type = "teamtailor"

    async def fetch_jobs(self, source: SourceRecord) -> FetchResult:
        # board_identifier = careers host e.g. careers.example.com or slug.teamtailor.com
        host = source.board_identifier.strip().removeprefix("https://").removeprefix("http://")
        if not host:
            return FetchResult(error="missing board_identifier")
        url = f"https://{host}/jobs.json"
        code, data = await http_json(url, timeout=self.timeout)
        if code == 404:
            return FetchResult(status_code=404, board_missing=True, error="board not found")
        if code != 200:
            return FetchResult(status_code=code, error=f"teamtailor http {code}")
        jobs_raw: List[Dict[str, Any]] = []
        if isinstance(data, dict):
            jobs_raw = data.get("jobs") or data.get("data") or []
        elif isinstance(data, list):
            jobs_raw = data
        out = []
        for j in jobs_raw:
            if not isinstance(j, dict):
                continue
            attrs = j.get("attributes") if "attributes" in j else j
            jid = str(j.get("id") or attrs.get("id") or attrs.get("slug") or "")
            if not jid:
                continue
            title = attrs.get("title") or attrs.get("name") or ""
            abs_url = attrs.get("url") or attrs.get("careers-url") or f"https://{host}/jobs/{jid}"
            loc = attrs.get("location") or attrs.get("human-status")
            if isinstance(loc, dict):
                loc = loc.get("name")
            desc = attrs.get("body") or attrs.get("description")
            out.append(
                self.normalize_common(
                    external_job_id=jid,
                    source=source,
                    company=source.company,
                    title=title,
                    url=abs_url,
                    location=loc if isinstance(loc, str) else None,
                    remote=attrs.get("remote-status") == "fully" if attrs.get("remote-status") else None,
                    description_full=desc if desc else None,
                    published_at=attrs.get("created-at") or attrs.get("start-date"),
                    salary=None,
                    experience_required=None,
                    raw={"teamtailor": jid},
                )
            )
        return FetchResult(jobs=out, status_code=200)
