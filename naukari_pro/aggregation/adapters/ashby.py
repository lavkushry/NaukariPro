"""Ashby non-user GraphQL / public posting API adapter."""

from __future__ import annotations

from typing import Any, Dict, List

from naukari_pro.aggregation.adapters._http import http_json
from naukari_pro.aggregation.base import AdapterRegistry, BaseATSAdapter, FetchResult, SourceRecord

# Public job board API used by many Ashby hosts
ASHBY_JOB_BOARD = "https://api.ashbyhq.com/posting-api/job-board/{board}"


@AdapterRegistry.register("ashby")
class AshbyAdapter(BaseATSAdapter):
    ats_type = "ashby"

    async def fetch_jobs(self, source: SourceRecord) -> FetchResult:
        board = source.board_identifier.strip()
        if not board:
            return FetchResult(error="missing board_identifier")
        url = ASHBY_JOB_BOARD.format(board=board)
        code, data = await http_json(url, timeout=self.timeout)
        if code == 404:
            return FetchResult(status_code=404, board_missing=True, error="board not found")
        if code != 200:
            return FetchResult(status_code=code, error=f"ashby http {code}")

        jobs_raw: List[Dict[str, Any]] = []
        if isinstance(data, dict):
            jobs_raw = data.get("jobs") or data.get("jobPostings") or []
        elif isinstance(data, list):
            jobs_raw = data

        out = []
        for j in jobs_raw:
            jid = str(j.get("id") or j.get("jobId") or j.get("jobPostingId") or "")
            if not jid:
                continue
            title = j.get("title") or j.get("jobTitle") or ""
            abs_url = j.get("jobUrl") or j.get("applyUrl") or j.get("url") or ""
            if not abs_url and source.domain:
                abs_url = f"https://jobs.ashbyhq.com/{board}/{jid}"
            loc = j.get("location")
            if isinstance(loc, dict):
                loc = loc.get("name") or loc.get("locationName")
            desc = j.get("descriptionHtml") or j.get("descriptionPlain") or j.get("description")
            departments = []
            dept = j.get("department") or j.get("team")
            if isinstance(dept, str):
                departments = [dept]
            elif isinstance(dept, dict) and dept.get("name"):
                departments = [dept["name"]]
            remote = j.get("isRemote") if "isRemote" in j else None
            # Compensation only if Ashby returns it — never invent
            salary = None
            comp = j.get("compensation") or j.get("compensationTierSummary")
            if isinstance(comp, str) and comp.strip():
                salary = comp.strip()
            out.append(
                self.normalize_common(
                    external_job_id=jid,
                    source=source,
                    company=source.company,
                    title=title,
                    url=abs_url,
                    location=loc if isinstance(loc, str) else None,
                    remote=remote if isinstance(remote, bool) else None,
                    description_full=desc if desc else None,
                    departments=departments,
                    published_at=j.get("publishedAt") or j.get("updatedAt"),
                    employment_type=j.get("employmentType"),
                    salary=salary,
                    experience_required=None,
                    raw={"ashby_id": jid},
                )
            )
        return FetchResult(jobs=out, status_code=200)

    async def probe_closed(self, board: str, job_id: str) -> bool:
        """Ashby GraphQL-style probe: missing posting => closed."""
        url = ASHBY_JOB_BOARD.format(board=board)
        code, data = await http_json(url, timeout=self.timeout)
        if code != 200 or not isinstance(data, dict):
            return False
        jobs = data.get("jobs") or data.get("jobPostings") or []
        ids = {str(j.get("id") or j.get("jobId") or "") for j in jobs}
        return job_id not in ids
