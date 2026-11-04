"""100-point ATS scorecard gate — dispatch blocked unless score >= 85."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional


GATE_THRESHOLD = 85.0


def score_ats_100(
    *,
    pdf_path: Path,
    candidate: Dict[str, Any],
    tailored: Dict[str, Any],
    jd_keywords: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Structure 30 + quantification 35 + keyword alignment 35 = 100.
    """
    struct = 0.0
    pages = 0
    extractable = False
    try:
        import pypdf
        reader = pypdf.PdfReader(str(pdf_path))
        pages = len(reader.pages)
        text = "\n".join((p.extract_text() or "") for p in reader.pages)
        extractable = len(text.strip()) > 40
        if pages == 1:
            struct += 20
        elif pages > 0:
            struct += 5
        if extractable:
            struct += 5
    except Exception:
        struct += 5

    if candidate.get("name") and candidate.get("email") and candidate.get("phone"):
        struct += 5
    struct = min(30.0, struct)

    bullets: List[str] = []
    for sec in tailored.get("tailored_sections") or []:
        if sec.get("name") == "experience_bullets":
            bullets.extend(str(b) for b in (sec.get("content") or []))
        if sec.get("name") == "experience":
            for role in sec.get("content") or []:
                if isinstance(role, dict):
                    bullets.extend(str(b) for b in (role.get("bullets") or []))

    quant_re = re.compile(
        r"\d+(?:\.\d+)?\s*(?:%|[kmgtb]\+?|ms|x|lpa)|\$\d+",
        re.I,
    )
    quantified = sum(1 for b in bullets if quant_re.search(b))
    metric_pts = round((quantified / max(1, len(bullets))) * 35.0, 1) if bullets else 10.0

    kws = [k.lower() for k in (jd_keywords or [])]
    resume_text = " ".join(bullets).lower()
    for sec in tailored.get("tailored_sections") or []:
        resume_text += " " + str(sec.get("content") or "").lower()
    if not kws:
        kws = ["python", "azure", "databricks", "sql", "spark"]
    matched = [k for k in kws if k in resume_text]
    kw_pts = round(min(35.0, (len(matched) / max(1, len(kws))) * 35.0), 1)

    missing = [k for k in kws if k not in matched]
    total = round(struct + metric_pts + kw_pts, 1)
    return {
        "overall_score": total,
        "score": total,
        "structure": struct,
        "quantified_metrics": metric_pts,
        "keyword_alignment": kw_pts,
        "pages": pages,
        "extractable": extractable,
        "gate_threshold": GATE_THRESHOLD,
        "gate_passed": total >= GATE_THRESHOLD,
        "matched_keywords": matched[:20],
        "missing_keywords": missing[:20],
    }


def ats_score_text(resume_text: str, jd_text: str) -> Dict[str, Any]:
    """Lightweight ATS score from plain text (CLI/API free-tier funnel)."""
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9+.#-]{1,}", jd_text or "")
    # Prefer longer distinctive terms
    stop = {
        "and", "the", "for", "with", "you", "our", "will", "are", "this", "that",
        "from", "have", "job", "role", "team", "work", "experience", "years",
    }
    weights: Dict[str, int] = {}
    for t in tokens:
        low = t.lower()
        if low in stop or len(low) < 3:
            continue
        weights[low] = weights.get(low, 0) + 1
    ranked = sorted(weights.keys(), key=lambda k: (-weights[k], -len(k), k))[:40]
    blob = (resume_text or "").lower()
    matched = [k for k in ranked if k in blob]
    missing = [k for k in ranked if k not in blob]
    score = round(100.0 * len(matched) / max(1, len(ranked)), 1) if ranked else 0.0
    return {
        "score": score,
        "matched_keywords": matched,
        "missing_keywords": missing,
    }
