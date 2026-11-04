"""Internshala adapter stub."""

from __future__ import annotations

from naukari_pro.aggregation.base import AdapterRegistry, BaseATSAdapter, FetchResult, SourceRecord


@AdapterRegistry.register("internshala")
class InternshalaAdapter(BaseATSAdapter):
    ats_type = "internshala"
    semaphore_limit = 3

    async def fetch_jobs(self, source: SourceRecord) -> FetchResult:
        if not source.board_identifier.strip():
            return FetchResult(error="missing board_identifier")
        return FetchResult(jobs=[], status_code=200)
