"""India-first location alias normalization (master prompt §4.8)."""

from __future__ import annotations

import re
from typing import Optional, Set

# Canonical hub → aliases
GEO_ALIASES = {
    "bengaluru": {"bengaluru", "bangalore", "blr", "bengalooru"},
    "ncr": {
        "ncr",
        "delhi",
        "new delhi",
        "gurgaon",
        "gurugram",
        "noida",
        "greater noida",
        "faridabad",
        "ghaziabad",
        "delhi-ncr",
        "delhi ncr",
    },
    "hyderabad": {"hyderabad", "hyd", "secunderabad"},
    "pune": {"pune", "pmc", "pcmc"},
    "mumbai": {"mumbai", "bombay", "navi mumbai", "thane"},
    "chennai": {"chennai", "madras"},
    "remote_india": {
        "remote (india)",
        "remote - india",
        "remote india",
        "work from india",
        "wfh india",
        "india remote",
    },
}

# Flatten alias → canonical
_ALIAS_TO_CANON = {}
for canon, aliases in GEO_ALIASES.items():
    for a in aliases:
        _ALIAS_TO_CANON[a.lower()] = canon
    _ALIAS_TO_CANON[canon] = canon

INDIA_HUBS = set(GEO_ALIASES.keys()) | {"india", "remote"}

# Indian consultancy / recruiter agency keywords (extend job-board-aggregator RECRUITER_TERMS)
RECRUITER_TERMS = re.compile(
    r"\b("
    r"consultancy|consulting\s+firm|staffing|recruitment\s+agency|"
    r"manpower|body\s*shop|contract\s+staffing|third\s*party\s+payroll|"
    r"teamlease|quess|randstad|adecco|michael\s+page|naukri\s+recruiter"
    r")\b",
    re.I,
)


def normalize_location(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    low = text.strip().lower()
    # Direct alias hit
    if low in _ALIAS_TO_CANON:
        return _ALIAS_TO_CANON[low]
    # Substring match for longer strings like "Bengaluru, Karnataka, India"
    for alias, canon in sorted(_ALIAS_TO_CANON.items(), key=lambda x: -len(x[0])):
        if alias in low:
            return canon
    return text.strip()


def location_allows_india(text: Optional[str], *, allow_unspecified: bool = False) -> bool:
    """Fail-closed for India targeting: True if India hub / remote-India / India mentioned."""
    if not text or not str(text).strip():
        return bool(allow_unspecified)
    low = str(text).lower()
    if "india" in low:
        return True
    canon = normalize_location(low)
    if canon in INDIA_HUBS:
        return True
    if "remote" in low and ("india" in low or "anywhere" in low or "worldwide" in low):
        return True
    # Pure global remote without India — treat as allow for remote-open roles
    if low.strip() in ("remote", "work from home", "wfh"):
        return True
    return False


def is_recruiter_consultancy(text: Optional[str]) -> bool:
    if not text:
        return False
    return bool(RECRUITER_TERMS.search(text))
