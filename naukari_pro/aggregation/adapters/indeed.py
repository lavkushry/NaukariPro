"""Indeed India RSS aggregator adapter (honest fields only; no invented salary/YOE)."""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from typing import List, Optional
from urllib.parse import quote_plus, urlparse, parse_qs

from naukari_pro.aggregation.adapters._http import sync_request
from naukari_pro.aggregation.base import AdapterRegistry, BaseATSAdapter, FetchResult, SourceRecord

DEFAULT_QUERIES = (
    'devops OR mlops OR "data engineer" OR "platform engineer" OR "azure data"',
)

# Strip HTML tags from RSS description
_TAG_RE = re.compile(r"<[^>]+>")


def _text(el: Optional[ET.Element]) -> str:
    if el is None or el.text is None:
        return ""
    return el.text.strip()


def _rss_url_from_source(source: SourceRecord) -> str:
    ident = (source.board_identifier or "").strip()
    if ident.startswith("http"):
        return ident
    # board_identifier = query|location  OR bare query
    q = DEFAULT_QUERIES[0]
    loc = "Hyderabad"
    if "|" in ident:
        parts = [p.strip() for p in ident.split("|", 1)]
        if parts[0]:
            q = parts[0]
        if len(parts) > 1 and parts[1]:
            loc = parts[1]
    elif ident:
        q = ident
    return (
        "https://www.indeed.co.in/rss?"
        f"q={quote_plus(q)}&l={quote_plus(loc)}"
    )


@AdapterRegistry.register("indeed")
class IndeedAdapter(BaseATSAdapter):
    """Fetch Indeed.co.in RSS for India DE/DevOps/MLOps queries."""

    ats_type = "indeed"
    semaphore_limit = 2

    async def fetch_jobs(self, source: SourceRecord) -> FetchResult:
        url = _rss_url_from_source(source)
        if not url:
            return FetchResult(error="missing board_identifier")

        import asyncio

        def _fetch() -> FetchResult:
            code, _hdrs, raw = sync_request(
                url,
                headers={
                    "Accept": "application/rss+xml, application/xml, text/xml;q=0.9,*/*;q=0.8",
                    "User-Agent": "NaukariProAggregator/1.0 (job-seeker RSS)",
                },
                timeout=self.timeout,
            )
            if code == 404:
                return FetchResult(error="rss_not_found", status_code=404, board_missing=True)
            if code != 200 or not raw:
                return FetchResult(error=f"http_{code}", status_code=code)
            try:
                root = ET.fromstring(raw)
            except ET.ParseError as exc:
                return FetchResult(error=f"xml_parse:{exc}", status_code=code)

            channel = root.find("channel")
            items = channel.findall("item") if channel is not None else root.findall(".//item")
            jobs: List = []
            for item in items:
                title = _text(item.find("title"))
                link = _text(item.find("link"))
                if not title or not link:
                    continue
                # Indeed RSS often encodes company in title: "Role - Company"
                company = source.company or "Indeed"
                role = title
                if " - " in title:
                    role, _, co = title.rpartition(" - ")
                    if co.strip():
                        company = co.strip()
                        role = role.strip() or title
                desc_html = _text(item.find("description"))
                desc = _TAG_RE.sub(" ", desc_html)
                desc = re.sub(r"\s+", " ", desc).strip() or None
                loc_el = item.find("{http://base.google.com/ns/1.0}location")
                location = _text(loc_el) if loc_el is not None else None
                if not location:
                    # fallback: parse from description snippet
                    m = re.search(r"([A-Za-z ]+,\s*(?:IN|India|Telangana|Karnataka))", desc or "")
                    location = m.group(1) if m else None
                pub = _text(item.find("pubDate")) or None
                # Stable id from link path or hash
                path = urlparse(link).path or link
                jk = parse_qs(urlparse(link).query).get("jk", [None])[0]
                ext_id = jk or hashlib.sha1(path.encode("utf-8")).hexdigest()[:16]
                jobs.append(
                    self.normalize_common(
                        external_job_id=f"indeed_{ext_id}",
                        source=source,
                        company=company,
                        title=role,
                        url=link,
                        location=location,
                        description_full=desc,
                        published_at=pub,
                        raw={"rss_link": link, "source": "indeed_rss"},
                    )
                )
            return FetchResult(jobs=jobs, status_code=200)

        return await asyncio.to_thread(_fetch)
