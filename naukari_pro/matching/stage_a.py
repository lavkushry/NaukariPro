"""Stage A — deterministic cheap recall filter (no LLM)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence


SENIORITY_PATTERNS = [
    (re.compile(r"\b(staff|principal|distinguished|fellow)\b", re.I), "staff", 0.2),
    (re.compile(r"\b(senior|sr\.?|lead)\b", re.I), "senior", 0.6),
    (re.compile(r"\b(junior|jr\.?|graduate|intern|entry[-\s]?level)\b", re.I), "junior", 0.3),
    (re.compile(r"\b(mid[-\s]?level|intermediate)\b", re.I), "mid", 0.8),
]

REMOTE_RE = re.compile(r"\b(remote|work\s*from\s*home|wfh|distributed)\b", re.I)
HYBRID_RE = re.compile(r"\bhybrid\b", re.I)
ONSITE_RE = re.compile(r"\b(on[-\s]?site|in[-\s]?office|office[-\s]?based)\b", re.I)

INDIA_LOC_RE = re.compile(
    r"\b(india|bengaluru|bangalore|hyderabad|pune|chennai|mumbai|noida|gurgaon|gurugram|delhi|remote)\b",
    re.I,
)


@dataclass
class StageAResult:
    passed: bool
    reasons: List[str] = field(default_factory=list)
    seniority: str = "unknown"
    work_mode: str = "unknown"
    title_weight: float = 0.5


class StageAFilter:
    """
    Weighted title regex + location + work-mode + comp-floor + excluded-companies.
    Missing salary does NOT invent a floor pass — only fails if salary known and below floor.
    """

    def __init__(
        self,
        *,
        target_titles: Optional[Sequence[str]] = None,
        excluded_companies: Optional[Sequence[str]] = None,
        require_india_or_remote: bool = True,
        min_salary_lpa: Optional[float] = 20.0,
        allowed_seniority: Optional[Sequence[str]] = None,
    ) -> None:
        self.target_titles = [t.lower() for t in (target_titles or [
            "data engineer", "azure data", "platform engineer", "mlops",
            "devops", "data platform", "lakehouse", "spark", "databricks",
        ])]
        self.excluded = {c.lower() for c in (excluded_companies or [])}
        self.require_india_or_remote = require_india_or_remote
        self.min_salary_lpa = min_salary_lpa
        self.allowed_seniority = set(allowed_seniority or ["junior", "mid", "senior", "unknown"])

    def evaluate(self, job: Dict[str, Any]) -> StageAResult:
        reasons: List[str] = []
        title = str(job.get("title") or "")
        company = str(job.get("company") or "")
        location = str(job.get("location") or "")
        description = str(job.get("jd") or job.get("description_full") or "")
        blob = f"{title} {location} {description}"

        if company.lower() in self.excluded:
            return StageAResult(False, ["excluded_company"], title_weight=0.0)

        seniority, title_weight = self._seniority(title)
        if seniority not in self.allowed_seniority and seniority != "unknown":
            reasons.append(f"seniority_blocked:{seniority}")

        # Title relevance
        title_l = title.lower()
        if not any(t in title_l for t in self.target_titles):
            reasons.append("title_mismatch")
            title_weight *= 0.4
        else:
            title_weight = min(1.0, title_weight + 0.2)

        work_mode = self._work_mode(blob)
        if self.require_india_or_remote:
            loc_ok = bool(INDIA_LOC_RE.search(location) or INDIA_LOC_RE.search(blob) or work_mode == "remote")
            if location and not loc_ok:
                reasons.append("location_gate")
            elif not location and work_mode not in ("remote", "unknown"):
                reasons.append("location_unknown_non_remote")

        salary = job.get("salary")
        if salary is not None and self.min_salary_lpa is not None:
            parsed = self._parse_salary_lpa(str(salary))
            if parsed is not None and parsed < self.min_salary_lpa:
                reasons.append(f"comp_floor:{parsed}<{self.min_salary_lpa}")
        # salary is None → do not invent; do not fail

        hard = [r for r in reasons if r.startswith(("excluded", "comp_floor", "seniority_blocked"))]
        soft = [r for r in reasons if r not in hard]
        # Fail only on hard gates; soft gates keep for ranking but allow Stage B
        passed = len(hard) == 0 and "title_mismatch" not in soft
        return StageAResult(
            passed=passed,
            reasons=reasons,
            seniority=seniority,
            work_mode=work_mode,
            title_weight=title_weight,
        )

    @staticmethod
    def _seniority(title: str) -> tuple[str, float]:
        for cre, label, weight in SENIORITY_PATTERNS:
            if cre.search(title):
                return label, weight
        return "unknown", 0.7

    @staticmethod
    def _work_mode(text: str) -> str:
        if REMOTE_RE.search(text):
            return "remote"
        if HYBRID_RE.search(text):
            return "hybrid"
        if ONSITE_RE.search(text):
            return "onsite"
        return "unknown"

    @staticmethod
    def _parse_salary_lpa(text: str) -> Optional[float]:
        m = re.search(r"(\d+(?:\.\d+)?)\s*[-–to]+\s*(\d+(?:\.\d+)?)\s*(?:lpa|lacs?|lac)", text, re.I)
        if m:
            return float(m.group(1))
        m2 = re.search(r"(\d+(?:\.\d+)?)\s*(?:lpa|lacs?|lac)", text, re.I)
        if m2:
            return float(m2.group(1))
        return None
