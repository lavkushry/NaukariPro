"""
Deterministic pre-score (ashby-job-scraper rules engine, India-tuned).

Stores score *excluding* freshness; recompute freshness at query time.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from naukari_pro.aggregation.india_geo import is_recruiter_consultancy, location_allows_india, normalize_location


# Weighted keywords (positive + negative). India tier terms included.
KEYWORD_WEIGHTS = [
    (re.compile(r"\bfresher\b", re.I), 15),
    (re.compile(r"\b0\s*[-–to]+\s*1\s+years?\b", re.I), 12),
    (re.compile(r"\bentry[-\s]?level\b", re.I), 10),
    (re.compile(r"\bjunior\b", re.I), 8),
    (re.compile(r"\bwalk[-\s]?in\b", re.I), 5),
    (re.compile(r"\bimmediate\s+joiner\b", re.I), 8),
    (re.compile(r"\bnotice\s+period\b", re.I), 3),
    (re.compile(r"\bmlops\b", re.I), 18),
    (re.compile(r"\bdevops\b", re.I), 14),
    (re.compile(r"\bkubernetes|k8s\b", re.I), 12),
    (re.compile(r"\bplatform\s+engineer\b", re.I), 14),
    (re.compile(r"\bdata\s+engineer\b", re.I), 12),
    (re.compile(r"\bazure\b", re.I), 8),
    (re.compile(r"\bpython\b", re.I), 6),
    (re.compile(r"\bsenior\b", re.I), -5),
    (re.compile(r"\bstaff\b", re.I), -8),
    (re.compile(r"\bprincipal\b", re.I), -10),
    (re.compile(r"\bintern\b", re.I), -100),  # unless targeted — caller can override
]

NICHE_CLASSIFIERS = {
    "ai": re.compile(r"\b(mlops|machine\s+learning|llm|genai|ai\s+engineer)\b", re.I),
    "backend": re.compile(r"\b(backend|api|microservices|golang|java|node)\b", re.I),
    "data": re.compile(r"\b(data\s+engineer|spark|databricks|etl|lakehouse)\b", re.I),
    "devops": re.compile(r"\b(devops|sre|platform|kubernetes|terraform|ci/?cd)\b", re.I),
}


@dataclass
class DeterministicScore:
    score: float  # excluding freshness
    freshness_boost: float
    niches: List[str] = field(default_factory=list)
    flags: List[str] = field(default_factory=list)
    location_canon: Optional[str] = None

    @property
    def total(self) -> float:
        return self.score + self.freshness_boost


def _parse_posted_at(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def freshness_boost(posted_at: Optional[str], *, now: Optional[datetime] = None) -> float:
    """Boost ≤48h; recompute at query time (not stored)."""
    dt = _parse_posted_at(posted_at)
    if not dt:
        return 0.0
    now = now or datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    age_h = (now - dt).total_seconds() / 3600.0
    if age_h <= 48:
        return max(0.0, 10.0 * (1.0 - age_h / 48.0))
    return 0.0


def score_job(
    job: Dict[str, Any],
    *,
    allow_intern: bool = False,
    now: Optional[datetime] = None,
) -> DeterministicScore:
    title = str(job.get("title") or "")
    loc = str(job.get("location") or "")
    desc = str(job.get("description_full") or job.get("jd") or job.get("description") or "")
    company = str(job.get("company") or "")
    blob = f"{title}\n{loc}\n{desc}\n{company}"

    score = 0.0
    flags: List[str] = []
    for cre, weight in KEYWORD_WEIGHTS:
        if cre.search(blob):
            if weight == -100 and allow_intern:
                continue
            score += weight
            flags.append(f"kw:{cre.pattern}:{weight:+d}")

    niches = [name for name, cre in NICHE_CLASSIFIERS.items() if cre.search(blob)]
    if niches:
        score += 5.0

    canon = normalize_location(loc) if loc else None
    if location_allows_india(loc) or location_allows_india(blob):
        score += 8.0
        flags.append("location_india_or_remote")
    elif loc:
        score -= 15.0
        flags.append("location_non_india")

    remote = job.get("remote")
    if remote is True or re.search(r"\bremote\b", blob, re.I):
        score += 5.0
        flags.append("remote_boost")

    if is_recruiter_consultancy(f"{company} {title} {desc}"):
        score -= 20.0
        flags.append("consultancy")

    fresh = freshness_boost(job.get("published_at") or job.get("posted_at"), now=now)
    return DeterministicScore(
        score=score,
        freshness_boost=fresh,
        niches=niches,
        flags=flags,
        location_canon=canon,
    )
