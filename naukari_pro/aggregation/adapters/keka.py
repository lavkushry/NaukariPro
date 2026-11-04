"""
Keka careers adapter — 2-step: resolve org-id, then fetch openings.
board_identifier = careers subdomain/slug (e.g. company.keka.com path slug).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from naukari_pro.aggregation.adapters._http import http_json, http_text
from naukari_pro.aggregation.base import AdapterRegistry, BaseATSAdapter, FetchResult, SourceRecord


@AdapterRegistry.register("keka")
class KekaAdapter(BaseATSAdapter):
    ats_type = "keka"

    async def _resolve_org_id(self, slug: str) -> Optional[str]:
        # Step 1: load careers page / config endpoint for org id
        careers_url = f"https://{slug}.keka.com/careers/"
        code, text = await http_text(careers_url, timeout=self.timeout)
        if code == 404:
            return None
        if code != 200:
            # try alternate host pattern
            alt = f"https://careers.keka.com/{slug}"
            code2, text2 = await http_text(alt, timeout=self.timeout)
            if code2 != 200:
                return None
            text = text2
        m = re.search(r'"orgId"\s*:\s*"?([0-9a-fA-F-]{8,})"?', text)
        if m:
            return m.group(1)
        m2 = re.search(r"orgId[=:](\d+)", text)
        return m2.group(1) if m2 else None

    async def fetch_jobs(self, source: SourceRecord) -> FetchResult:
        slug = source.board_identifier.strip().removesuffix(".keka.com")
        if not slug:
            return FetchResult(error="missing board_identifier")

        org_id = await self._resolve_org_id(slug)
        if not org_id:
            return FetchResult(status_code=404, board_missing=True, error="keka org-id not resolved")

        # Step 2: openings API (best-effort public pattern)
        api = f"https://{slug}.keka.com/careers/api/openings"
        code, data = await http_json(
            api,
            headers={"X-Org-Id": str(org_id)},
            timeout=self.timeout,
        )
        if code == 404:
            # alternate
            api2 = f"https://{slug}.keka.com/api/careers/openings?orgId={org_id}"
            code, data = await http_json(api2, timeout=self.timeout)
        if code == 404:
            return FetchResult(status_code=404, board_missing=True, error="openings not found")
        if code != 200:
            return FetchResult(status_code=code, error=f"keka http {code}")

        jobs_raw: List[Dict[str, Any]] = []
        if isinstance(data, dict):
            jobs_raw = data.get("data") or data.get("openings") or data.get("jobs") or []
        elif isinstance(data, list):
            jobs_raw = data

        out = []
        for j in jobs_raw or []:
            if not isinstance(j, dict):
                continue
            jid = str(j.get("id") or j.get("jobId") or j.get("openingId") or "")
            if not jid:
                continue
            title = j.get("title") or j.get("jobTitle") or ""
            abs_url = j.get("url") or f"https://{slug}.keka.com/careers/jobdetails/{jid}"
            loc = j.get("location") or j.get("jobLocation")
            if isinstance(loc, dict):
                loc = loc.get("name") or loc.get("city")
            desc = j.get("description") or j.get("jobDescription")
            out.append(
                self.normalize_common(
                    external_job_id=jid,
                    source=source,
                    company=source.company,
                    title=title,
                    url=abs_url,
                    location=loc if isinstance(loc, str) else None,
                    description_full=desc if desc else None,
                    published_at=j.get("postedOn") or j.get("createdOn"),
                    salary=None,
                    experience_required=None,
                    raw={"keka_org": org_id, "keka_id": jid},
                )
            )
        return FetchResult(jobs=out, status_code=200)
