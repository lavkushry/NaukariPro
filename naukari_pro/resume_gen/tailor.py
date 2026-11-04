"""
Truth-preserving tailor: reorder/rewrite ONLY from facts.
Never add tools/metrics/employers. Mirror ATS keywords only when covered.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence


def _flatten_facts(facts: Dict[str, Any]) -> Dict[str, Any]:
    return dict(facts or {})


def _fact_blob(facts: Dict[str, Any]) -> str:
    parts: List[str] = []
    for v in facts.values():
        if isinstance(v, list):
            parts.extend(str(x) for x in v)
        elif isinstance(v, dict):
            parts.append(str(v))
        elif v:
            parts.append(str(v))
    return " ".join(parts).lower()


def _bullet_pool(facts: Dict[str, Any]) -> List[str]:
    pool: List[str] = []
    for key in ("bullets", "experience_bullets", "achievements", "projects"):
        val = facts.get(key)
        if isinstance(val, list):
            for item in val:
                if isinstance(item, str) and item.strip():
                    pool.append(item.strip())
                elif isinstance(item, dict):
                    b = item.get("bullet") or item.get("text") or item.get("description")
                    if b:
                        pool.append(str(b).strip())
                    # nested bullets
                    for nb in item.get("bullets") or []:
                        if isinstance(nb, str) and nb.strip():
                            pool.append(nb.strip())
    # experience roles
    for role in facts.get("experience") or []:
        if isinstance(role, dict):
            for nb in role.get("bullets") or role.get("highlights") or []:
                if isinstance(nb, str) and nb.strip():
                    pool.append(nb.strip())
    # dedupe preserve order
    seen = set()
    out = []
    for b in pool:
        if b not in seen:
            seen.add(b)
            out.append(b)
    return out


def tailor_from_facts(
    master_facts: Dict[str, Any],
    structured_jd: Dict[str, Any],
    *,
    use_llm: bool = False,
    gateway: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Returns tailored_sections + gaps_reported + keywords_mirrored.
    LLM path uses P3; default path is deterministic and offline-safe.
    """
    facts = _flatten_facts(master_facts)
    if use_llm and gateway is not None:
        resp = gateway.call(
            "P3_resume_tailor",
            {"candidate_facts": facts, "jd_structured": structured_jd},
        )
        data = dict(resp.data)
        # Post-filter: drop any mirrored keyword not in facts
        blob = _fact_blob(facts)
        mirrored = []
        for kw in data.get("keywords_mirrored") or []:
            if str(kw).lower() in blob:
                mirrored.append(kw)
        data["keywords_mirrored"] = mirrored
        return data

    must = [str(x) for x in (structured_jd.get("must_haves") or [])]
    ats_kw = [str(x) for x in (structured_jd.get("ats_keywords") or [])]
    blob = _fact_blob(facts)
    bullets = _bullet_pool(facts)

    def score_bullet(b: str) -> int:
        bl = b.lower()
        return sum(1 for k in ats_kw + must if k.lower() in bl)

    ranked = sorted(bullets, key=score_bullet, reverse=True)

    mirrored = []
    for kw in ats_kw + must:
        if kw.lower() in blob:
            mirrored.append(kw)
    # unique
    mirrored = list(dict.fromkeys(mirrored))

    gaps = [m for m in must if m.lower() not in blob]

    skills = facts.get("skills") or facts.get("key_skills") or []
    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(",") if s.strip()]
    # Reorder skills: JD-overlapping first, but only existing skills
    skills_list = [str(s) for s in skills]
    skills_ranked = sorted(
        skills_list,
        key=lambda s: sum(1 for k in ats_kw if k.lower() in s.lower()),
        reverse=True,
    )

    sections = [
        {"name": "summary", "content": facts.get("summary") or facts.get("headline") or ""},
        {"name": "skills", "content": skills_ranked},
        {"name": "experience_bullets", "content": ranked},
        {
            "name": "experience",
            "content": facts.get("experience") or [],
        },
        {"name": "education", "content": facts.get("education") or []},
        {"name": "certifications", "content": facts.get("certifications") or []},
    ]
    return {
        "tailored_sections": sections,
        "gaps_reported": gaps,
        "keywords_mirrored": mirrored,
        "scorer": "deterministic",
    }


FORBIDDEN_FABRICATION_MARKERS = [
    re.compile(r"\b(?:invented|placeholder|TODO|TBD|lorem ipsum)\b", re.I),
]


def audit_no_fabrication(
    tailored: Dict[str, Any],
    master_facts: Dict[str, Any],
) -> List[str]:
    """Return list of violation messages; empty means clean."""
    violations: List[str] = []
    blob = _fact_blob(master_facts)
    # Every mirrored keyword must appear in facts
    for kw in tailored.get("keywords_mirrored") or []:
        if str(kw).lower() not in blob:
            violations.append(f"mirrored_keyword_not_in_facts:{kw}")
    # Bullets must be subset of fact bullets (exact string match)
    allowed = set(_bullet_pool(master_facts))
    for sec in tailored.get("tailored_sections") or []:
        if sec.get("name") == "experience_bullets":
            for b in sec.get("content") or []:
                if b not in allowed:
                    # allow if bullet is substring of a fact bullet (reorder-only rewrite = exact for deterministic)
                    if not any(b in a or a in b for a in allowed):
                        violations.append(f"bullet_not_in_facts:{b[:80]}")
        text = str(sec.get("content") or "")
        for cre in FORBIDDEN_FABRICATION_MARKERS:
            if cre.search(text):
                violations.append(f"forbidden_marker:{cre.pattern}")
    return violations
