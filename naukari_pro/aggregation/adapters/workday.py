"""
Workday careers site adapter — paginated POST to /wday/cxs/{tenant}/{site}/jobs.
List view has NO description; optional detail GET for jobRequisitionId + JD.
Hard cap: 10 pages × 20 = 200 newest jobs per site per cycle.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from naukari_pro.aggregation.adapters._http import http_json
from naukari_pro.aggregation.base import AdapterRegistry, BaseATSAdapter, FetchResult, SourceRecord

PAGE_SIZE = 20
MAX_PAGES = 10
DETAIL_BUDGET = 60  # max detail GETs per cycle per site

# Role-Scope G1: only these title tokens get expensive detail GETs
ROLE_SCOPE_TOKENS = (
    "engineer", "devops", "sre", "platform", "infra", "mlops", "data",
    "cloud", "backend", "software", "site reliability", "ml ", "ai ",
)


def role_scope_g1_pass(title: str) -> bool:
    t = (title or "").lower()
    return any(tok in t for tok in ROLE_SCOPE_TOKENS)


def parse_workday_posted_on(raw: Any) -> Optional[str]:
    """Parse Workday postedOn (ISO or relative like 'Posted 3 Days Ago') → ISO or None."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except ValueError:
        pass
    m = re.search(r"(\d+)\s+day", text, re.I)
    if m:
        days = int(m.group(1))
        return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    if re.search(r"today|just\s+posted|hours?\s+ago", text, re.I):
        return datetime.now(timezone.utc).isoformat()
    if re.search(r"yesterday", text, re.I):
        return (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    return None  # unparseable → null, never crash


@AdapterRegistry.register("workday")
class WorkdayAdapter(BaseATSAdapter):
    ats_type = "workday"
    semaphore_limit = 2

    def _parse_ident(self, source: SourceRecord) -> Optional[Dict[str, str]]:
        ident = source.board_identifier.strip()
        if ident.startswith("http"):
            # https://host/wday/cxs/tenant/site[/jobs]
            m = re.search(
                r"https?://([^/]+)/wday/cxs/([^/]+)/([^/]+)",
                ident,
                re.I,
            )
            if not m:
                return None
            return {"host": m.group(1), "tenant": m.group(2), "site": m.group(3)}
        parts = [p.strip() for p in ident.split("|")]
        if len(parts) == 3:
            return {"host": parts[0], "tenant": parts[1], "site": parts[2]}
        if source.domain and len(parts) == 2:
            return {"host": source.domain, "tenant": parts[0], "site": parts[1]}
        return None

    def _jobs_endpoint(self, parts: Dict[str, str]) -> str:
        return f"https://{parts['host']}/wday/cxs/{parts['tenant']}/{parts['site']}/jobs"

    async def _fetch_detail(
        self,
        parts: Dict[str, str],
        external_path: str,
    ) -> Dict[str, Any]:
        path = external_path.lstrip("/")
        url = f"https://{parts['host']}/wday/cxs/{parts['tenant']}/{parts['site']}/job/{path}"
        code, data = await http_json(url, timeout=self.timeout)
        if code != 200 or not isinstance(data, dict):
            return {}
        info = data.get("jobPostingInfo") or data
        return info if isinstance(info, dict) else {}

    async def fetch_jobs(self, source: SourceRecord) -> FetchResult:
        parts = self._parse_ident(source)
        if not parts:
            return FetchResult(error="invalid workday board_identifier (host|tenant|site)")

        endpoint = self._jobs_endpoint(parts)
        all_jobs: List[Any] = []
        offset = 0
        last_code = 200
        pages = 0

        while pages < MAX_PAGES:
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
            pages += 1
            if code == 404:
                return FetchResult(status_code=404, board_missing=True, error="board not found")
            if code != 200 or not isinstance(data, dict):
                return FetchResult(status_code=code, error=f"workday http {code}")

            batch = data.get("jobPostings") or data.get("jobs") or []
            if not batch:
                break
            all_jobs.extend(batch)
            offset += len(batch)
            if len(batch) < PAGE_SIZE:
                break

        out = []
        detail_used = 0
        for j in all_jobs:
            if not isinstance(j, dict):
                continue
            path = str(j.get("externalPath") or j.get("jobPostingUrl") or "")
            title = j.get("title") or j.get("jobTitle") or ""
            abs_url = path if str(path).startswith("http") else ""
            if not abs_url and parts["host"] and path:
                abs_url = f"https://{parts['host']}{path if path.startswith('/') else '/' + path}"

            req_id = ""
            desc = None
            # Detail GET only for Role-Scope G1 passers (budgeted)
            if path and detail_used < DETAIL_BUDGET and role_scope_g1_pass(str(title)):
                detail_used += 1
                info = await self._fetch_detail(parts, path)
                req_id = str(
                    info.get("jobRequisitionId")
                    or info.get("id")
                    or ""
                )
                desc = info.get("jobDescription") or info.get("description") or None
                if not abs_url:
                    abs_url = str(info.get("externalUrl") or "") or abs_url

            if not req_id:
                # Fallback — never invent; use path slug as last resort for key stability
                req_id = path.rstrip("/").split("/")[-1] or str(j.get("id") or "")

            external_job_id = f"{parts['tenant']}:{parts['site']}:{req_id}"
            loc = j.get("locationsText") or j.get("location")
            posted = parse_workday_posted_on(j.get("postedOn") or j.get("startDate"))
            out.append(
                self.normalize_common(
                    external_job_id=external_job_id,
                    source=source,
                    company=source.company,
                    title=title,
                    url=abs_url or f"https://{parts['host']}/en-US/{parts['site']}/{req_id}",
                    location=loc if isinstance(loc, str) else None,
                    description_full=desc,
                    published_at=posted,
                    salary=None,
                    experience_required=None,
                    raw={
                        "workday": True,
                        "tenant": parts["tenant"],
                        "site": parts["site"],
                        "externalPath": path,
                        "detail_fetches": detail_used,
                        "pages": pages,
                    },
                )
            )
        return FetchResult(jobs=out, status_code=last_code)
