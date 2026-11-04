"""Stage B — LLM JD structuring via Runtime Prompt P1 (schema-validated)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from naukari_pro.llm.gateway import LLMGateway, LLMResponse
from naukari_pro.matching.extract_p1 import extract_p1


def _normalize_p1(structured: Dict[str, Any], job: Dict[str, Any]) -> Dict[str, Any]:
    """Enforce truth-only post-conditions after LLM or heuristic extract."""
    out = dict(structured)

    # salary_signals must be a list of verbatim strings (never invent)
    sal = out.get("salary_signals")
    if sal is None or sal == "" or sal == "null":
        out["salary_signals"] = []
    elif isinstance(sal, str):
        out["salary_signals"] = [sal] if sal.strip() else []
    elif isinstance(sal, list):
        out["salary_signals"] = [str(x) for x in sal if x is not None and str(x).strip()]
    else:
        out["salary_signals"] = []

    # If job row has no salary and JD extract also empty — stay []
    if job.get("salary") is None and not out["salary_signals"]:
        out["salary_signals"] = []

    # ats_keywords: lowercase, dedupe, max 25
    kws: List[str] = []
    seen = set()
    for k in out.get("ats_keywords") or []:
        tok = str(k).strip().lower()
        if tok and tok not in seen:
            seen.add(tok)
            kws.append(tok)
        if len(kws) >= 25:
            break
    out["ats_keywords"] = kws

    # lists
    for key in ("responsibilities", "must_haves", "nice_to_haves"):
        val = out.get(key)
        out[key] = [str(x) for x in val] if isinstance(val, list) else []

    # min_years_experience
    mye = out.get("min_years_experience")
    if mye in ("", "null", "None"):
        out["min_years_experience"] = None
    elif mye is not None:
        try:
            out["min_years_experience"] = float(mye)
        except (TypeError, ValueError):
            out["min_years_experience"] = None

    # seniority / work_mode — allow null seniority when unstated
    if out.get("seniority") in ("", "unknown", "null", "None"):
        out["seniority"] = None
    if out.get("work_mode") in ("", "null", "None", None):
        out["work_mode"] = "unknown"

    # role_summary word cap ~60
    summary = str(out.get("role_summary") or "").strip()
    words = summary.split()
    if len(words) > 60:
        out["role_summary"] = " ".join(words[:60])
    else:
        out["role_summary"] = summary

    return out


def structure_jd(
    job: Dict[str, Any],
    *,
    gateway: Optional[LLMGateway] = None,
    stage_a_hints: Optional[Dict[str, Any]] = None,
    use_llm: bool = True,
) -> Dict[str, Any]:
    """
    Structure a JD with P1. When use_llm=False (or LLM unavailable), use
    deterministic truth-only extract_p1 — never invent fields.
    """
    if not use_llm:
        structured = extract_p1(
            description=str(job.get("jd") or job.get("description_full") or ""),
            title=str(job.get("title") or ""),
            company=str(job.get("company") or ""),
            location=str(job.get("location") or ""),
        )
        structured = _normalize_p1(structured, job)
        structured["_meta"] = {"scorer": "extract_p1", "cached": False, "cost_usd": 0.0}
        return structured

    gw = gateway or LLMGateway()
    variables = {
        "title": job.get("title") or "",
        "company": job.get("company") or "",
        "location": job.get("location") or "",
        "description": job.get("jd") or job.get("description_full") or "",
    }
    resp: LLMResponse = gw.call("P1_jd_structure", variables)
    structured = _normalize_p1(dict(resp.data), job)

    # Prefer Stage A work_mode only when LLM/extract says unknown
    if stage_a_hints:
        if structured.get("work_mode") == "unknown" and stage_a_hints.get("work_mode"):
            wm = stage_a_hints["work_mode"]
            if wm in ("remote", "hybrid", "onsite", "unknown"):
                structured["work_mode"] = wm
        # seniority: only fill from Stage A if extract left null AND Stage A had an explicit hit
        if structured.get("seniority") is None and stage_a_hints.get("seniority") not in (None, "unknown"):
            # map legacy Stage A labels
            legacy = {
                "junior": "entry",
                "mid": "mid",
                "senior": "senior",
                "staff": "staff",
            }
            mapped = legacy.get(stage_a_hints["seniority"])
            if mapped:
                structured["seniority"] = mapped

    structured["_meta"] = {
        "prompt_version": resp.prompt_version,
        "input_hash": resp.input_hash,
        "cached": resp.cached,
        "cost_usd": resp.cost_usd,
    }
    return structured
