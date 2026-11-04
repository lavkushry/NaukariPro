"""3-layer dedup: URL normalization → per-ATS key → SimHash JD fingerprint."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional, Set, Tuple

from naukari_pro.aggregation.models import NormalizedJob, normalize_job_url

SIMHASH_THRESHOLD = 0.92
SIMHASH_WINDOW_DAYS = 90
REAPPLY_COOLDOWN_DAYS = 15


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def _shingles(tokens: List[str], n: int = 3) -> List[str]:
    if len(tokens) < n:
        return [" ".join(tokens)] if tokens else []
    return [" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


def simhash64(text: str) -> int:
    """64-bit SimHash over 3-token shingles."""
    tokens = _tokenize(text)
    shingles = _shingles(tokens, 3)
    if not shingles:
        return 0
    v = [0] * 64
    for sh in shingles:
        h = int(hashlib.md5(sh.encode("utf-8")).hexdigest(), 16)
        for i in range(64):
            bit = (h >> i) & 1
            v[i] += 1 if bit else -1
    out = 0
    for i in range(64):
        if v[i] > 0:
            out |= 1 << i
    return out


def hamming_similarity(a: int, b: int) -> float:
    xor = a ^ b
    dist = bin(xor).count("1")
    return 1.0 - (dist / 64.0)


@dataclass
class DedupDecision:
    is_duplicate: bool
    reason: str
    matched_key: Optional[str] = None
    similarity: Optional[float] = None


class DedupEngine:
    def __init__(
        self,
        *,
        simhash_threshold: float = SIMHASH_THRESHOLD,
        window_days: int = SIMHASH_WINDOW_DAYS,
    ) -> None:
        self.simhash_threshold = simhash_threshold
        self.window_days = window_days
        self._urls: Set[str] = set()
        self._ats_keys: Set[str] = set()
        self._simhashes: List[Tuple[int, str, datetime]] = []  # hash, key, seen_at

    def seed_from_jobs(self, jobs: Iterable[NormalizedJob]) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.window_days)
        for job in jobs:
            self._urls.add(normalize_job_url(job.url))
            self._ats_keys.add(job.ats_job_key)
            if job.description_full:
                seen = _parse_iso(job.last_seen_at) or datetime.now(timezone.utc)
                if seen >= cutoff:
                    self._simhashes.append(
                        (simhash64(job.description_full), job.ats_job_key, seen)
                    )

    def check(self, job: NormalizedJob) -> DedupDecision:
        url = normalize_job_url(job.url)
        if url and url in self._urls:
            return DedupDecision(True, "url", matched_key=url)
        if job.ats_job_key in self._ats_keys:
            return DedupDecision(True, "ats_key", matched_key=job.ats_job_key)
        if job.description_full:
            h = simhash64(job.description_full)
            cutoff = datetime.now(timezone.utc) - timedelta(days=self.window_days)
            for prev_h, key, seen in self._simhashes:
                if seen < cutoff:
                    continue
                sim = hamming_similarity(h, prev_h)
                if sim >= self.simhash_threshold:
                    return DedupDecision(True, "simhash", matched_key=key, similarity=sim)
        return DedupDecision(False, "unique")

    def remember(self, job: NormalizedJob) -> None:
        url = normalize_job_url(job.url)
        if url:
            self._urls.add(url)
        self._ats_keys.add(job.ats_job_key)
        if job.description_full:
            self._simhashes.append(
                (simhash64(job.description_full), job.ats_job_key, datetime.now(timezone.utc))
            )


def company_role_key(company: str, title: str) -> str:
    c = re.sub(r"[^a-z0-9]+", "", (company or "").lower())
    t = re.sub(r"[^a-z0-9]+", "", (title or "").lower())
    return f"{c}::{t}"


def within_reapply_cooldown(
    last_applied_iso: Optional[str],
    *,
    days: int = REAPPLY_COOLDOWN_DAYS,
) -> bool:
    if not last_applied_iso:
        return False
    last = _parse_iso(last_applied_iso)
    if not last:
        return False
    return datetime.now(timezone.utc) - last < timedelta(days=days)


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
