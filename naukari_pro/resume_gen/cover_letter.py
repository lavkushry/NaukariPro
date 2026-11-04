"""P5 v1.1.0 — grounded cover letter from facts only."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def draft_cover_letter(
    master_facts: Dict[str, Any],
    *,
    company: str,
    title: str,
    must_haves: Optional[List[str]] = None,
    use_llm: bool = False,
    gateway: Optional[Any] = None,
) -> Dict[str, Any]:
    if use_llm and gateway is not None:
        resp = gateway.call(
            "P5_cover_letter",
            {
                "candidate_facts": master_facts,
                "company": company,
                "title": title,
                "must_haves": must_haves or [],
            },
        )
        data = dict(resp.data)
        data.setdefault("unsupported_claims", [])
        data.setdefault("provider", resp.provider)
        text = str(data.get("cover_letter") or "")
        data["word_count"] = len(text.split())
        return data

    summary = str(master_facts.get("summary") or master_facts.get("headline") or "").strip()
    skills = master_facts.get("skills") or master_facts.get("key_skills") or []
    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(",") if s.strip()]
    skill_bits = ", ".join(str(s) for s in list(skills)[:6])
    claims: List[str] = []
    unsupported: List[str] = []
    parts: List[str] = []
    if summary:
        parts.append(summary)
        claims.append("summary")
    if skill_bits:
        parts.append(f"Relevant strengths include {skill_bits}.")
        claims.append("skills")
    if title or company:
        parts.append(
            f"I am applying for the {title or 'role'} position at {company or 'your company'}."
        )
    # Never invent must-have claims
    for m in must_haves or []:
        blob = " ".join(parts).lower() + " " + str(master_facts).lower()
        if str(m).lower() not in blob:
            unsupported.append(str(m))
    letter = " ".join(parts).strip()
    words = letter.split()
    if len(words) > 180:
        letter = " ".join(words[:180])
    return {
        "cover_letter": letter,
        "claims_used": claims,
        "unsupported_claims": unsupported,
        "word_count": len(letter.split()),
        "provider": "deterministic",
    }
