"""
Truth-preserving tailor: reorder/rewrite ONLY from facts.
Never add tools/metrics/employers. Mirror ATS keywords only when covered.
P3 v1.1.0 contract: keyword_coverage have/support/gap + experience relevance order.
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
                    for nb in item.get("bullets") or []:
                        if isinstance(nb, str) and nb.strip():
                            pool.append(nb.strip())
    for role in facts.get("experience") or []:
        if isinstance(role, dict):
            for nb in role.get("bullets") or role.get("highlights") or []:
                if isinstance(nb, str) and nb.strip():
                    pool.append(nb.strip())
    seen = set()
    out = []
    for b in pool:
        if b not in seen:
            seen.add(b)
            out.append(b)
    return out


def _classify_terms(terms: Sequence[str], blob: str) -> Dict[str, List[str]]:
    have: List[str] = []
    support: List[str] = []
    gap: List[str] = []
    for raw in terms:
        t = str(raw).strip()
        if not t:
            continue
        tl = t.lower()
        if tl in blob:
            have.append(t)
            continue
        # partial / support: any token ≥4 chars appears
        tokens = [w for w in re.findall(r"[a-z0-9]+", tl) if len(w) >= 4]
        if tokens and any(tok in blob for tok in tokens):
            support.append(t)
        else:
            gap.append(t)
    return {"have": have, "support": support, "gap": gap}


def _reorder_experience(
    experience: Any,
    ats_kw: Sequence[str],
    must: Sequence[str],
) -> List[Dict[str, Any]]:
    roles: List[Dict[str, Any]] = []
    if not isinstance(experience, list):
        return roles
    keys = [k.lower() for k in list(ats_kw) + list(must)]
    for role in experience:
        if not isinstance(role, dict):
            continue
        bullets = [
            str(b).strip()
            for b in (role.get("bullets") or role.get("highlights") or [])
            if isinstance(b, str) and b.strip()
        ]
        blob = " ".join(
            [
                str(role.get("title") or ""),
                str(role.get("company") or ""),
                " ".join(bullets),
            ]
        ).lower()
        relevance = float(sum(1 for k in keys if k and k in blob))
        # Rank bullets inside role by keyword hits
        bullets_ranked = sorted(
            bullets,
            key=lambda b: sum(1 for k in keys if k and k in b.lower()),
            reverse=True,
        )
        roles.append(
            {
                "company": str(role.get("company") or ""),
                "title": str(role.get("title") or ""),
                "bullets": bullets_ranked,
                "relevance": relevance,
                "start": role.get("start"),
                "end": role.get("end"),
            }
        )
    roles.sort(key=lambda r: r.get("relevance") or 0.0, reverse=True)
    return roles


def tailor_from_facts(
    master_facts: Dict[str, Any],
    structured_jd: Dict[str, Any],
    *,
    use_llm: bool = False,
    gateway: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Returns P3 v1.1 contract: tailored_sections + keyword_coverage + gaps + mirrored.
    LLM path uses P3; default path is deterministic and offline-safe.
    """
    facts = _flatten_facts(master_facts)
    if use_llm and gateway is not None:
        resp = gateway.call(
            "P3_resume_tailor",
            {"candidate_facts": facts, "jd_structured": structured_jd},
        )
        data = dict(resp.data)
        blob = _fact_blob(facts)
        mirrored = []
        for kw in data.get("keywords_mirrored") or []:
            if str(kw).lower() in blob:
                mirrored.append(kw)
        data["keywords_mirrored"] = mirrored
        # Ensure coverage object exists even if model omitted
        if not isinstance(data.get("keyword_coverage"), dict):
            terms = list(structured_jd.get("must_haves") or []) + list(
                structured_jd.get("ats_keywords") or []
            )
            data["keyword_coverage"] = _classify_terms(terms, blob)
        data.setdefault("scorer", "llm")
        return data

    must = [str(x) for x in (structured_jd.get("must_haves") or [])]
    ats_kw = [str(x) for x in (structured_jd.get("ats_keywords") or [])]
    nice = [str(x) for x in (structured_jd.get("nice_to_haves") or [])]
    blob = _fact_blob(facts)
    bullets = _bullet_pool(facts)

    def score_bullet(b: str) -> int:
        bl = b.lower()
        return sum(1 for k in ats_kw + must if k.lower() in bl)

    ranked = sorted(bullets, key=score_bullet, reverse=True)

    coverage = _classify_terms(list(dict.fromkeys(must + ats_kw + nice)), blob)
    mirrored = list(dict.fromkeys(coverage["have"]))
    gaps = [m for m in must if m.lower() not in blob]

    skills = facts.get("skills") or facts.get("key_skills") or []
    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(",") if s.strip()]
    skills_list = [str(s) for s in skills]
    skills_ranked = sorted(
        skills_list,
        key=lambda s: sum(1 for k in ats_kw if k.lower() in s.lower()),
        reverse=True,
    )

    experience_ordered = _reorder_experience(facts.get("experience") or [], ats_kw, must)
    summary = str(facts.get("summary") or facts.get("headline") or "")

    sections = [
        {"name": "summary", "content": summary},
        {"name": "skills", "content": skills_ranked},
        {"name": "experience_bullets", "content": ranked},
        {"name": "experience", "content": experience_ordered or (facts.get("experience") or [])},
        {"name": "education", "content": facts.get("education") or []},
        {"name": "certifications", "content": facts.get("certifications") or []},
    ]
    return {
        "summary": summary,
        "tailored_sections": sections,
        "experience": experience_ordered,
        "skills_ordered": skills_ranked,
        "gaps_reported": gaps,
        "keywords_mirrored": mirrored,
        "keyword_coverage": coverage,
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
    for kw in tailored.get("keywords_mirrored") or []:
        if str(kw).lower() not in blob:
            violations.append(f"mirrored_keyword_not_in_facts:{kw}")
    allowed = set(_bullet_pool(master_facts))
    for sec in tailored.get("tailored_sections") or []:
        if sec.get("name") == "experience_bullets":
            for b in sec.get("content") or []:
                if b not in allowed:
                    if not any(b in a or a in b for a in allowed):
                        violations.append(f"bullet_not_in_facts:{b[:80]}")
        text = str(sec.get("content") or "")
        for cre in FORBIDDEN_FABRICATION_MARKERS:
            if cre.search(text):
                violations.append(f"forbidden_marker:{cre.pattern}")
    # Coverage gaps must not be silently promoted to "have"
    cov = tailored.get("keyword_coverage") or {}
    for kw in cov.get("have") or []:
        if str(kw).lower() not in blob:
            violations.append(f"coverage_have_ungrounded:{kw}")
    return violations
