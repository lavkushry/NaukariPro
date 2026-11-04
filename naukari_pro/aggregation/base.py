"""Adapter interface for ATS job boards."""

from __future__ import annotations

import asyncio
import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type

from naukari_pro.aggregation.models import NormalizedJob

log = logging.getLogger(__name__)

# Quiet boards (few changes) polled every 3rd cycle; 404 boards backoff 12h.
DEFAULT_SEM_LIMIT = 5
MAX_RETRIES = 4
BASE_BACKOFF_S = 1.5
BOARD_404_BACKOFF_S = 12 * 3600


@dataclass
class SourceRecord:
    company: str
    ats_type: str
    board_identifier: str
    domain: Optional[str] = None
    active: bool = True
    last_checked_at: Optional[str] = None
    consecutive_empty: int = 0
    backoff_until: Optional[str] = None
    source_id: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.source_id:
            self.source_id = f"{self.ats_type}:{self.board_identifier}".lower()


@dataclass
class FetchResult:
    jobs: List[NormalizedJob] = field(default_factory=list)
    error: Optional[str] = None
    status_code: Optional[int] = None
    board_missing: bool = False


class AdapterRegistry:
    _adapters: Dict[str, Type["BaseATSAdapter"]] = {}

    @classmethod
    def register(cls, ats_type: str):
        def deco(adapter_cls: Type["BaseATSAdapter"]):
            cls._adapters[ats_type.lower()] = adapter_cls
            return adapter_cls
        return deco

    @classmethod
    def get(cls, ats_type: str) -> Optional[Type["BaseATSAdapter"]]:
        return cls._adapters.get((ats_type or "").lower())

    @classmethod
    def known(cls) -> List[str]:
        return sorted(cls._adapters.keys())


class BaseATSAdapter(ABC):
    """fetch_jobs(source) -> list[NormalizedJob]. Honest fields only."""

    ats_type: str = "generic"
    semaphore_limit: int = DEFAULT_SEM_LIMIT

    def __init__(self, session: Any = None, timeout: float = 30.0) -> None:
        self.session = session
        self.timeout = timeout
        self._sem = asyncio.Semaphore(self.semaphore_limit)

    @abstractmethod
    async def fetch_jobs(self, source: SourceRecord) -> FetchResult:
        ...

    async def fetch_with_retry(self, source: SourceRecord) -> FetchResult:
        last: FetchResult = FetchResult(error="not attempted")
        for attempt in range(MAX_RETRIES):
            async with self._sem:
                try:
                    last = await self.fetch_jobs(source)
                except Exception as exc:  # noqa: BLE001
                    last = FetchResult(error=str(exc))
                    log.warning("%s fetch error %s: %s", self.ats_type, source.source_id, exc)

            if last.board_missing or (last.status_code == 404):
                last.board_missing = True
                return last
            if last.error is None and last.status_code not in (429, 500, 502, 503, 504):
                return last
            if last.status_code not in (429, 500, 502, 503, 504) and last.error is None:
                return last

            sleep_s = BASE_BACKOFF_S * (2 ** attempt) + random.uniform(0, 0.75)
            log.info(
                "%s backoff %.1fs attempt=%s source=%s code=%s",
                self.ats_type, sleep_s, attempt + 1, source.source_id, last.status_code,
            )
            await asyncio.sleep(sleep_s)
        return last

    def normalize_common(
        self,
        *,
        external_job_id: str,
        source: SourceRecord,
        company: str,
        title: str,
        url: str,
        location: Optional[str] = None,
        remote: Optional[bool] = None,
        description_full: Optional[str] = None,
        departments: Optional[List[str]] = None,
        employment_type: Optional[str] = None,
        published_at: Optional[str] = None,
        salary: Optional[str] = None,
        experience_required: Optional[str] = None,
        raw: Optional[Dict[str, Any]] = None,
    ) -> NormalizedJob:
        return NormalizedJob(
            external_job_id=str(external_job_id),
            source_id=source.source_id or f"{source.ats_type}:{source.board_identifier}",
            company=company or source.company,
            title=(title or "").strip(),
            url=url,
            location=location,
            remote=remote,
            description_full=description_full,  # None if not fetched — never invent
            departments=departments or [],
            employment_type=employment_type,
            published_at=published_at,
            ats_type=self.ats_type,
            salary=salary,  # None unless source provided
            experience_required=experience_required,
            raw_metadata=raw or {},
        )
