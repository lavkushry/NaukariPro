"""Optional Common Crawl CDX discovery with live API verification before auto-add."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

from naukari_pro.aggregation.adapters._http import http_json, http_text
from naukari_pro.aggregation.base import AdapterRegistry, SourceRecord
from naukari_pro.aggregation.storage import AggregationStore

log = logging.getLogger(__name__)

CDX_API = "https://web.archive.org/cdx/search/cdx"

# Host patterns that imply ATS type + board id extraction
ATS_HOST_PATTERNS = [
    (r"boards(?:-api)?\.greenhouse\.io/([^/?#]+)", "greenhouse", 1),
    (r"job-boards\.greenhouse\.io/([^/?#]+)", "greenhouse", 1),
    (r"jobs\.ashbyhq\.com/([^/?#]+)", "ashby", 1),
    (r"api\.ashbyhq\.com/posting-api/job-board/([^/?#]+)", "ashby", 1),
    (r"jobs\.lever\.co/([^/?#]+)", "lever", 1),
    (r"api\.lever\.co/v0/postings/([^/?#]+)", "lever", 1),
    (r"([^.]+)\.bamboohr\.com", "bamboohr", 1),
    (r"([^.]+)\.pinpointhq\.com", "pinpoint", 1),
    (r"([^.]+)\.recruitee\.com", "recruitee", 1),
    (r"apply\.workable\.com/([^/?#]+)", "workable", 1),
]


@dataclass
class DiscoveredBoard:
    company: str
    ats_type: str
    board_identifier: str
    domain: Optional[str]
    verified: bool
    source_url: str


def parse_ats_from_url(url: str) -> Optional[Tuple[str, str]]:
    for pattern, ats, group in ATS_HOST_PATTERNS:
        m = re.search(pattern, url, re.I)
        if m:
            return ats, m.group(group)
    return None


async def verify_board_live(ats_type: str, board_identifier: str, company: str = "Unknown") -> bool:
    """Hit the live adapter; accept only HTTP 200 with parseable payload (may be empty jobs)."""
    adapter_cls = AdapterRegistry.get(ats_type)
    if not adapter_cls:
        return False
    # Import side-effect registration
    import naukari_pro.aggregation.adapters  # noqa: F401

    source = SourceRecord(
        company=company,
        ats_type=ats_type,
        board_identifier=board_identifier,
        active=True,
    )
    result = await adapter_cls().fetch_jobs(source)
    if result.board_missing:
        return False
    if result.status_code == 200 and result.error is None:
        return True
    return False


async def discover_from_cdx(
    query: str = "*.greenhouse.io",
    *,
    limit: int = 50,
    verify: bool = True,
) -> List[DiscoveredBoard]:
    """
    Query Common Crawl / Wayback CDX for ATS host URLs, then optionally verify live.
    Auto-add only after verification succeeds.
    """
    params = (
        f"?url={quote(query)}&output=json&fl=original&filter=statuscode:200"
        f"&collapse=urlkey&limit={limit}"
    )
    url = CDX_API + params
    code, data = await http_json(url, timeout=60.0)
    rows: List[Any] = []
    if code == 200 and isinstance(data, list):
        rows = data[1:] if data and data[0] == ["original"] else data
    elif code == 200 and isinstance(data, str):
        # newline JSON fallback
        for line in data.splitlines():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                if line.strip().startswith("http"):
                    rows.append([line.strip()])

    found: Dict[str, DiscoveredBoard] = {}
    for row in rows:
        original = row[0] if isinstance(row, list) and row else (row if isinstance(row, str) else None)
        if not original:
            continue
        parsed = parse_ats_from_url(str(original))
        if not parsed:
            continue
        ats, board_id = parsed
        key = f"{ats}:{board_id}".lower()
        if key in found:
            continue
        company = board_id.replace("-", " ").replace("_", " ").title()
        verified = False
        if verify:
            try:
                verified = await verify_board_live(ats, board_id, company)
            except Exception as exc:  # noqa: BLE001
                log.debug("verify failed %s: %s", key, exc)
                verified = False
        found[key] = DiscoveredBoard(
            company=company,
            ats_type=ats,
            board_identifier=board_id,
            domain=None,
            verified=verified,
            source_url=str(original),
        )
    return list(found.values())


def auto_add_verified(
    boards: List[DiscoveredBoard],
    store: Optional[AggregationStore] = None,
) -> int:
    store = store or AggregationStore()
    added = 0
    for b in boards:
        if not b.verified:
            continue
        sid = f"{b.ats_type}:{b.board_identifier}".lower()
        store.upsert_source(
            {
                "source_id": sid,
                "company": b.company,
                "ats_type": b.ats_type,
                "board_identifier": b.board_identifier,
                "domain": b.domain,
                "active": True,
            }
        )
        added += 1
    return added
