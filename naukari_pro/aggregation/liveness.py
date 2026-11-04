"""Detect closed postings via phrasing heuristics + optional Ashby probe."""

from __future__ import annotations

import re
from typing import Optional

CLOSED_PHRASINGS = [
    r"no longer accepting applications",
    r"this (?:job|position|role) is (?:no longer|not) available",
    r"this posting has (?:been )?closed",
    r"position has been filled",
    r"job (?:has been )?filled",
    r"applications? (?:are|have been) closed",
    r"we are no longer hiring for",
    r"this opportunity is closed",
    r"role is no longer open",
    r"vacancy has been closed",
    r"posting expired",
    r"this job has expired",
    r"sorry[,.]? this job is no longer",
    r"page not found",
    r"404\s*[-–]?\s*not found",
    r"the job you(?:'| a)?re looking for",
    r"listing (?:has been )?removed",
    r"requisition (?:has been )?closed",
    r"this requisition is closed",
    r"currently not accepting",
]

_CLOSED_RE = re.compile("|".join(f"(?:{p})" for p in CLOSED_PHRASINGS), re.I)


def looks_closed(page_text: Optional[str]) -> bool:
    if not page_text:
        return False
    sample = page_text[:8000]
    return bool(_CLOSED_RE.search(sample))


def closed_reason(page_text: Optional[str]) -> Optional[str]:
    if not page_text:
        return None
    m = _CLOSED_RE.search(page_text[:8000])
    return m.group(0) if m else None
