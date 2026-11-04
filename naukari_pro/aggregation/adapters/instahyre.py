"""Instahyre adapter stub — public listing fetch when endpoints available."""

from __future__ import annotations

from naukari_pro.aggregation.adapters._http import http_json
from naukari_pro.aggregation.base import AdapterRegistry, BaseATSAdapter, FetchResult, SourceRecord


@AdapterRegistry.register("instahyre")
class InstahyreAdapter(BaseATSAdapter):
    ats_type = "instahyre"
    semaphore_limit = 3

    async def fetch_jobs(self, source: SourceRecord) -> FetchResult:
        # Stub: no unofficial scrape; return empty honest result until official API wired
        board = source.board_identifier.strip()
        if not board:
            return FetchResult(error="missing board_identifier")
        # Probe a placeholder URL — treat non-200 as quiet empty, never invent jobs
        url = f"https://www.instahyre.com/api/v1/job_boards/{board}/"
        try:
            code, _data = await http_json(url, timeout=self.timeout)
        except Exception as exc:  # noqa: BLE001
            return FetchResult(error=f"instahyre_unreachable:{exc}", status_code=0)
        if code == 404:
            return FetchResult(status_code=404, board_missing=True, error="board not found")
        # Without a stable public schema, return empty rather than fabricate
        return FetchResult(jobs=[], status_code=code if code else 200, error=None)
