"""Stage D — optional LLM rubric (1-10, <=30-word rationale) for borderline 40-79 jobs."""

from __future__ import annotations

from typing import Any, Dict, Optional


def optional_rubric(
    structured_jd: Dict[str, Any],
    stage_c: Dict[str, Any],
    candidate_facts: Dict[str, Any],
    *,
    gateway: Optional[Any] = None,
) -> Optional[Dict[str, Any]]:
    fit = float(stage_c.get("fit_score") or 0)
    if fit < 40 or fit >= 80:
        return None  # only borderline REVIEW band

    # Cheap deterministic rubric when no LLM / offline
    buckets = stage_c.get("must_have_coverage_lists") or {}
    if not buckets:
        detail = stage_c.get("coverage_detail") or []
        buckets = {
            "direct": [d for d in detail if (d or {}).get("evidence") == "direct"],
            "missing": [d for d in detail if (d or {}).get("evidence") == "missing"],
        }
    missing = len(buckets.get("missing") or [])
    direct = len(buckets.get("direct") or [])
    score_10 = max(1, min(10, round(fit / 10)))
    rationale = (
        f"Borderline fit {fit:.0f}/100; {direct} direct vs {missing} missing must-haves."
    )[:180]
    return {
        "rubric_score": score_10,
        "rationale": rationale,
        "source": "deterministic_borderline",
    }
