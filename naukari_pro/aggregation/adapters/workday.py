"""
Workday careers site adapter — paginated POST to /wday/cxs/{tenant}/{site}/jobs.
Uses sessionless-total workaround: request body with appliedFacets + limit/offset;
total from response when available, else stop when page shorter than limit.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from naukari_pro.aggregation.adapters._http import http_json
from naukari_pro.aggregation.base import AdapterRegistry, BaseATSAdapter, FetchResult, SourceRecord

PAGE_SIZE = 20


@AdapterRegistry.register("workday")
class WorkdayAdapter(BaseATSAdapter):
    ats_type = "workday"
    semaphore_limit = 2  # Workday is sensitive

    def _jobs_endpoint(self, source: SourceRecord) -> Optional[str]:
        """
        board_identifier formats:
          - host|tenant|site  e.g. microsoft.wd1.myworkdayjobs.com|microsoft|External
          - or full base https://host/wday/cxs/tenant/site
        """
        ident = source.board_identifier.strip()
        if ident.startswith("http"):
            return ident.rstrip("/") + "/jobs"
        parts = [p.strip() for p in ident.split("|")]
        if len(parts) == 3:
            host, tenant, site = parts
            return f"https://{host}/wday/cxs/{tenant}/{site}/jobs"
        if source.domain and len(parts) == 2:
            tenant, site = parts
            return f"https://{source.domain}/wday/cxs/{tenant}/{site}/jobs"
        return None

    async def fetch_jobs(self, source: SourceRecord) -> FetchResult:
        endpoint = self._jobs_endpoint(source)
        if not endpoint:
            return FetchResult(error="invalid workday board_identifier (host|tenant|site)")

        all_jobs: List[Any] = []
        offset = 0
        total: Optional[int] = None
        last_code = 200

        while True:
            body = {
                "appliedFacets": {},
                "limit": PAGE_SIZE,
                "offset": offset,
                "searchText": "",
            }
            code, data = await http_json(
                endpoint, method="POST", json_body=body, timeout=self.timeout
            )
            last_code = code
            if code == 404:
                return FetchResult(status_code=404, board_missing=True, error="board not found")
            if code != 200 or not isinstance(data, dict):
                return FetchResult(status_code=code, error=f"workday http {code}")

            batch = data.get("jobPostings") or data.get("jobs") or []
            if total is None:
                # sessionless-total: prefer total if present; else None
                total = data.get("total") or data.get("totalJobs")
                try:
                    total = int(total) if total is not None else None
                except (TypeError, ValueError):
                    total = None

            if not batch:
                break
            all_jobs.extend(batch)
            offset += len(batch)
            if len(batch) < PAGE_SIZE:
                break
            if total is not None and offset >= total:
                break
            if offset > 5000:  # safety
                break

        out = []
        for j in all_jobs:
            if not isinstance(j, dict):
                continue
            jid = str(
                j.get("bulletFields", [None])[0]
                if isinstance(j.get("bulletFields"), list) and j.get("bulletFields")
                else j.get("id") or j.get("jobId") or j.get("externalPath") or ""
            )
            title = j.get("title") or j.get("jobTitle") or ""
            path = j.get("externalPath") or j.get("jobPostingUrl") or ""
            abs_url = path if str(path).startswith("http") else ""
            if not abs_url and source.domain and path:
                abs_url = f"https://{source.domain}{path}"
            loc = j.get("locationsText") or j.get("location")
            # Workday list endpoint often omits full JD — store NULL, never invent
            desc = j.get("jobDescription") or j.get("description") or None
            out.append(
                self.normalize_common(
                    external_job_id=jid or abs_url,
                    source=source,
                    company=source.company,
                    title=title,
                    url=abs_url or f"workday://{source.board_identifier}/{jid}",
                    location=loc if isinstance(loc, str) else None,
                    description_full=desc,
                    published_at=j.get("postedOn") or j.get("startDate"),
                    salary=None,
                    experience_required=None,
                    raw={"workday": True},
                )
            )
        return FetchResult(jobs=out, status_code=last_code)
