"""Hirist adapter stub (India tech board)."""

from __future__ import annotations

from naukari_pro.aggregation.base import AdapterRegistry, BaseATSAdapter, FetchResult, SourceRecord


@AdapterRegistry.register("hirist")
class HiristAdapter(BaseATSAdapter):
    ats_type = "hirist"
    semaphore_limit = 3

    async def fetch_jobs(self, source: SourceRecord) -> FetchResult:
        if not source.board_identifier.strip():
            return FetchResult(error="missing board_identifier")
        # Honest empty until official/public JSON endpoint is confirmed
        return FetchResult(jobs=[], status_code=200)
