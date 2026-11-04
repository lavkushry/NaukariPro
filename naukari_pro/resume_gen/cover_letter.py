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

    # Construct auditable 3-paragraph structure
    paragraphs: List[Dict[str, Any]] = []

    # Paragraph 1: Specific hook tied to candidate
    p1_sentences: List[Dict[str, Any]] = []
    if title or company:
        p1_sentences.append({
            "text": f"I am applying for the {title or 'role'} position at {company or 'your organization'}.",
            "kind": "job",
            "cv_evidence": [],
        })
    if summary:
        p1_sentences.append({
            "text": summary,
            "kind": "cv",
            "cv_evidence": [0],
        })
        claims.append("summary")
    if p1_sentences:
        paragraphs.append({"sentences": p1_sentences})

    # Paragraph 2: Resume-backed achievements
    p2_sentences: List[Dict[str, Any]] = []
    bullets = master_facts.get("experience_bullets") or []
    if bullets:
        for idx, b in enumerate(bullets[:2]):
            p2_sentences.append({
                "text": str(b),
                "kind": "cv",
                "cv_evidence": [idx + 1],
            })
            claims.append(f"bullet_{idx}")
    elif skill_bits:
        p2_sentences.append({
            "text": f"Relevant production capabilities include {skill_bits}.",
            "kind": "cv",
            "cv_evidence": [1],
        })
        claims.append("skills")
    if p2_sentences:
        paragraphs.append({"sentences": p2_sentences})

    # Paragraph 3: Honest bridge and clear call to action
    p3_sentences: List[Dict[str, Any]] = [{
        "text": f"I would welcome the opportunity to discuss how this background aligns with the engineering needs at {company or 'your team'}.",
        "kind": "courtesy",
        "cv_evidence": [],
    }]
    paragraphs.append({"sentences": p3_sentences})

    # Build flat cover letter text
    para_texts = [" ".join(s["text"] for s in p["sentences"]) for p in paragraphs]
    letter = "\n\n".join(t for t in para_texts if t).strip()

    # Never invent must-have claims
    for m in must_haves or []:
        blob = letter.lower() + " " + str(master_facts).lower()
        if str(m).lower() not in blob:
            unsupported.append(str(m))

    words = letter.split()
    return {
        "cover_letter": letter,
        "paragraphs": paragraphs,
        "claims_used": claims,
        "unsupported_claims": unsupported,
        "word_count": len(words),
        "provider": "deterministic",
    }
