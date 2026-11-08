"""Normalized job schema — never invent salary/experience/JD."""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_job_url(url: Optional[str]) -> str:
    """Canonical URL: lowercase host, strip tracking params, drop fragments."""
    if not url:
        return ""
    raw = str(url).strip()
    try:
        p = urlparse(raw)
        host = (p.netloc or "").lower().replace("www.", "")
        path = re.sub(r"/+", "/", p.path or "").rstrip("/") or "/"
        q = parse_qs(p.query, keep_blank_values=False)
        drop = {
            "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
            "gh_src", "source", "ref", "fbclid", "gclid",
        }
        kept = {k: v for k, v in q.items() if k.lower() not in drop}
        query = urlencode(kept, doseq=True)
        return urlunparse((p.scheme.lower() or "https", host, path, "", query, ""))
    except Exception:
        return raw.lower()


def content_hash_text(*parts: Optional[str]) -> str:
    blob = "\n".join((p or "").strip() for p in parts)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


@dataclass
class NormalizedJob:
    external_job_id: str
    source_id: str
    company: str
    title: str
    url: str
    location: Optional[str] = None
    remote: Optional[bool] = None
    description_full: Optional[str] = None
    departments: Optional[List[str]] = None
    employment_type: Optional[str] = None
    published_at: Optional[str] = None
    first_seen_at: Optional[str] = None
    last_seen_at: Optional[str] = None
    content_hash: Optional[str] = None
    is_active: bool = True
    ats_type: Optional[str] = None
    # Honest metadata — NULL unless fetched from source
    salary: Optional[str] = None
    experience_required: Optional[str] = None
    raw_metadata: Dict[str, Any] = field(default_factory=dict)
    # v2 NormalizedJob extensions (jobRadar / master prompt §4.3)
    apply_url: Optional[str] = None
    description_hash: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = None
    salary_interval: Optional[str] = None
    status: str = "active"  # active | removed | updated

    def __post_init__(self) -> None:
        self.url = normalize_job_url(self.url)
        if self.apply_url:
            self.apply_url = normalize_job_url(self.apply_url)
        now = utc_now_iso()
        self.first_seen_at = self.first_seen_at or now
        self.last_seen_at = self.last_seen_at or now
        if not self.description_hash and self.description_full:
            self.description_hash = content_hash_text(self.description_full)
        if not self.content_hash:
            self.content_hash = content_hash_text(
                self.title, self.company, self.description_full, self.url
            )
        if self.departments is None:
            self.departments = []
        if not self.is_active and self.status == "active":
            self.status = "removed"

    @property
    def ats_job_key(self) -> str:
        """Canonical identity: greenhouse:{id} / lever:{id} / ashby:{id} / workday:{tenant}:{site}:{reqId}."""
        ats = (self.ats_type or "unknown").lower().strip()
        jid = (self.external_job_id or "").strip() or content_hash_text(self.url)[:16]
        if ats == "workday":
            # external_job_id already tenant:site:reqId when adapter is correct
            if jid.count(":") >= 2:
                return f"workday:{jid}" if not jid.startswith("workday:") else jid
            return f"workday:{jid}"
        return f"{ats}:{jid}"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["ats_job_key"] = self.ats_job_key
        return d

    def to_legacy_vacancy(self) -> Dict[str, Any]:
        """
        Compatibility shape for ExternalPortalBatchRunner.
        Unfetched fields stay None — never fabricate exp/salary/jd.
        """
        return {
            "company": self.company,
            "title": self.title,
            "url": self.url,
            "ats": self.ats_type or "Generic",
            "location": self.location,
            "exp": self.experience_required,  # may be None
            "salary": self.salary,  # may be None
            "jd": self.description_full,  # may be None
            "external_job_id": self.external_job_id,
            "source_id": self.source_id,
            "content_hash": self.content_hash,
            "ats_job_key": self.ats_job_key,
        }
