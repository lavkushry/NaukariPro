"""
Stage C — hiring-fit judge (P2 v1.1).
When in doubt, downgrade. Evidence only from CANDIDATE_PROFILE.

fit_score = coverage*40 + role_family*25 + location_workmode*15
          + seniority*10 + compensation*10

AUTO_APPLY only if fit>=80 AND coverage>=0.7 AND zero missing must_haves.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from naukari_pro.llm.gateway import LLMGateway

TRANSFER = {
    "k8s": {"kubernetes"},
    "kubernetes": {"k8s"},
    "js": {"javascript"},
    "javascript": {"js"},
    "ts": {"typescript"},
    "typescript": {"ts"},
    "gcp": {"google cloud", "googlecloud"},
    "aws": {"amazon web services"},
    "adf": {"azure data factory", "data factory"},
    "pyspark": {"spark"},
    "spark": {"pyspark"},
    "ci/cd": {"cicd", "github actions", "gitlab ci"},
    "cicd": {"ci/cd"},
}

ROLE_FAMILIES = {
    "data_engineer": {
        "data engineer", "azure data", "data platform", "lakehouse", "etl", "elt",
        "databricks", "spark", "analytics engineer",
    },
    "devops": {
        "devops", "sre", "platform engineer", "infrastructure", "site reliability",
        "mlops", "ci/cd",
    },
    "backend": {"backend", "software engineer", "full stack", "api engineer"},
    "frontend": {"frontend", "react", "ui engineer", "web engineer"},
    "manager": {"manager", "engineering manager", "director", "head of"},
    "research": {"research scientist", "research engineer", "phd", "scientist"},
    "retail": {"retail", "store manager", "merchandising"},
}

SENIORITY_RANK = {
    "intern": 0,
    "entry": 1,
    "junior": 1,
    "mid": 2,
    "senior": 3,
    "lead": 4,
    "staff": 5,
    "manager": 5,
    "director_plus": 6,
}


def _norm_tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9+#\./]+", (text or "").lower()))


def _profile_blob(candidate_facts: Dict[str, Any]) -> str:
    parts: List[str] = []
    for key in ("skills", "tools", "titles", "experience", "projects", "summary", "keywords", "headline"):
        val = candidate_facts.get(key)
        if isinstance(val, list):
            for x in val:
                if isinstance(x, dict):
                    parts.append(str(x.get("title") or ""))
                    parts.append(str(x.get("company") or ""))
                    parts.extend(str(b) for b in (x.get("bullets") or x.get("highlights") or []))
                else:
                    parts.append(str(x))
        elif isinstance(val, dict):
            parts.append(str(val))
        elif val:
            parts.append(str(val))
    for k, v in candidate_facts.items():
        if isinstance(v, str):
            parts.append(v)
    return " ".join(parts)


def _find_profile_fact(req: str, profile: str, facts: Dict[str, Any]) -> Optional[str]:
    """Return a short verbatim-ish fact snippet supporting the requirement, or None."""
    req_l = req.lower().strip()
    # skills list hits
    for s in facts.get("skills") or facts.get("key_skills") or []:
        if str(s).lower() in req_l or req_l in str(s).lower():
            return f"skills:{s}"
    for tok in _norm_tokens(req):
        if len(tok) < 3:
            continue
        if tok in profile.lower():
            # clip surrounding context
            idx = profile.lower().find(tok)
            if idx >= 0:
                start = max(0, idx - 20)
                end = min(len(profile), idx + len(tok) + 20)
                return profile[start:end].strip()
    return None


def _classify_must_have(
    req: str,
    profile: str,
    profile_tokens: set[str],
    facts: Dict[str, Any],
) -> Tuple[str, Optional[str]]:
    req_l = req.lower().strip()
    if not req_l:
        return "missing", None
    fact = _find_profile_fact(req, profile, facts)
    if req_l in profile.lower():
        return "direct", fact or req_l
    req_tokens = _norm_tokens(req_l)
    if req_tokens and req_tokens.issubset(profile_tokens):
        return "direct", fact or " ".join(sorted(req_tokens))
    for tok in req_tokens:
        alts = TRANSFER.get(tok, set())
        if alts & profile_tokens or any(a in profile.lower() for a in alts):
            matched = next(iter(alts & profile_tokens), None) or next(iter(alts), tok)
            return "transferable", fact or f"transfer:{tok}->{matched}"
    return "missing", None


def _role_family(text: str) -> Optional[str]:
    t = (text or "").lower()
    best = None
    best_hits = 0
    for family, kws in ROLE_FAMILIES.items():
        hits = sum(1 for k in kws if k in t)
        if hits > best_hits:
            best_hits = hits
            best = family
    return best if best_hits else None


def _role_family_match(profile: Dict[str, Any], job: Dict[str, Any]) -> float:
    p_blob = _profile_blob(profile)
    j_blob = " ".join(
        str(job.get(k) or "")
        for k in ("role_summary", "title")
    ) + " " + " ".join(str(x) for x in (job.get("must_haves") or [])[:5])
    # also accept title on job via ats path
    pf = _role_family(p_blob + " " + " ".join(str(t) for t in (profile.get("titles") or [])))
    jf = _role_family(j_blob)
    if pf is None or jf is None:
        return 0.25  # doubt → downgrade
    if pf == jf:
        return 1.0
    # adjacent pairs
    adjacent = {
        frozenset({"data_engineer", "devops"}),
        frozenset({"devops", "backend"}),
        frozenset({"data_engineer", "backend"}),
    }
    if frozenset({pf, jf}) in adjacent:
        return 0.55
    return 0.15


def _location_workmode_fit(profile: Dict[str, Any], job: Dict[str, Any]) -> float:
    pref_mode = str(profile.get("work_mode") or profile.get("preferred_work_mode") or "").lower()
    pref_locs = " ".join(
        str(x).lower()
        for x in (
            profile.get("locations")
            or profile.get("preferred_locations")
            or ([profile.get("location")] if profile.get("location") else [])
            or []
        )
    )
    job_mode = str(job.get("work_mode") or "unknown").lower()
    job_loc = str(job.get("location") or "").lower()

    score = 0.0
    # work mode
    if job_mode == "unknown":
        score += 0.35  # doubt → partial credit only
    elif job_mode == "remote":
        score += 1.0 if pref_mode in ("", "remote", "hybrid", "any") else 0.7
    elif job_mode == "hybrid":
        score += 0.85 if pref_mode in ("", "hybrid", "remote", "any") else 0.4
    elif job_mode == "onsite":
        if pref_mode == "remote":
            score += 0.1
        else:
            score += 0.6 if any(x in job_loc for x in ("india", "bengaluru", "bangalore", "hyderabad", "pune", "chennai", "mumbai", "noida", "gurgaon", "gurugram")) or not job_loc else 0.3
    else:
        score += 0.25

    # location soft boost
    if job_mode == "remote" or "remote" in job_loc:
        return min(1.0, score)
    if pref_locs and job_loc and any(p in job_loc for p in pref_locs.split() if len(p) > 2):
        return min(1.0, max(score, 0.85))
    if not job_loc:
        return min(1.0, score * 0.8)  # downgrade unknown location
    return min(1.0, score)


def _seniority_fit(profile: Dict[str, Any], job: Dict[str, Any]) -> float:
    job_sen = job.get("seniority")
    if not job_sen:
        return 0.35  # unstated → downgrade
    cand = str(profile.get("seniority") or profile.get("level") or "").lower()
    # derive from yoe if needed
    yoe = profile.get("yoe") or profile.get("years_of_experience")
    if not cand and yoe is not None:
        try:
            y = float(yoe)
            cand = "entry" if y < 2 else "mid" if y < 5 else "senior" if y < 8 else "staff"
        except (TypeError, ValueError):
            cand = ""
    if not cand:
        return 0.3
    jr = SENIORITY_RANK.get(str(job_sen).lower())
    cr = SENIORITY_RANK.get(cand)
    if jr is None or cr is None:
        return 0.3
    delta = abs(jr - cr)
    if delta == 0:
        return 1.0
    if delta == 1:
        return 0.7
    if delta == 2:
        return 0.35
    return 0.1  # over/under-leveled → strong downgrade


def _compensation_vs_floor(profile: Dict[str, Any], job: Dict[str, Any]) -> float:
    """
    Compare job salary_signals to candidate floor. Unknown → downgrade (not invent).
    """
    floor = profile.get("salary_floor_lpa") or profile.get("expected_ctc_lpa") or profile.get("min_salary_lpa")
    signals = job.get("salary_signals") or []
    if isinstance(signals, str):
        signals = [signals] if signals else []
    if floor is None or not signals:
        return 0.25  # doubt → downgrade
    try:
        floor_f = float(floor)
    except (TypeError, ValueError):
        return 0.25

    nums: List[float] = []
    for s in signals:
        for m in re.finditer(r"(\d+(?:\.\d+)?)", str(s)):
            nums.append(float(m.group(1)))
    if not nums:
        return 0.25
    # use lower bound of stated range
    low = min(nums)
    # Heuristic: values > 100 likely INR absolute not LPA — skip comparison, downgrade
    if low > 100:
        return 0.25
    if low >= floor_f:
        return 1.0
    if low >= floor_f * 0.85:
        return 0.55
    return 0.1


def _truncate_rationale(text: str, max_words: int = 30) -> str:
    words = (text or "").split()
    return " ".join(words[:max_words])


def judge_fit(
    candidate_profile: Dict[str, Any],
    job_requirements: Dict[str, Any],
    *,
    job_title: str = "",
    job_location: str = "",
) -> Dict[str, Any]:
    """
    P2 hiring-fit judge. Returns the exact contract JSON.
    Empty/unknown inputs → downgrade (never invent evidence).
    """
    profile = candidate_profile or {}
    job = dict(job_requirements or {})
    if job_title and not job.get("title"):
        job["title"] = job_title
    if job_location and not job.get("location"):
        job["location"] = job_location

    # Empty profile or empty requirements → protect candidate time
    if not profile and not job:
        return {
            "fit_score": 0,
            "must_have_coverage": 0.0,
            "coverage_detail": [],
            "role_family_match": 0.0,
            "location_workmode_fit": 0.0,
            "seniority_fit": 0.0,
            "compensation_vs_floor": 0.0,
            "recommendation": "SKIP",
            "flags": ["empty_profile", "empty_requirements"],
            "rationale": "No profile or requirements provided; skip to protect candidate time.",
        }

    profile_text = _profile_blob(profile)
    profile_tokens = _norm_tokens(profile_text)
    must = [str(x) for x in (job.get("must_haves") or []) if str(x).strip()]

    coverage_detail: List[Dict[str, Any]] = []
    missing_n = 0
    covered_n = 0
    for req in must:
        evidence, fact = _classify_must_have(req, profile_text, profile_tokens, profile)
        if evidence == "missing":
            missing_n += 1
        else:
            covered_n += 1
        coverage_detail.append(
            {"must_have": req, "evidence": evidence, "profile_fact": fact}
        )

    if must:
        coverage = covered_n / len(must)
    else:
        coverage = 0.0  # no explicit must-haves → cannot claim coverage

    role_m = _role_family_match(profile, job)
    loc_m = _location_workmode_fit(profile, job)
    sen_m = _seniority_fit(profile, job)
    comp_m = _compensation_vs_floor(profile, job)

    fit = int(round(
        coverage * 40
        + role_m * 25
        + loc_m * 15
        + sen_m * 10
        + comp_m * 10
    ))
    fit = max(0, min(100, fit))

    flags: List[str] = []
    if missing_n:
        flags.append(f"missing_must_haves:{missing_n}")
    if not must:
        flags.append("no_explicit_must_haves")
    if not profile_text.strip():
        flags.append("empty_profile_evidence")
    if job.get("work_mode") == "unknown":
        flags.append("work_mode_unknown")
    if not (job.get("salary_signals") or []):
        flags.append("salary_unstated")
    if role_m < 0.4:
        flags.append("role_family_mismatch")
    if sen_m <= 0.15:
        flags.append("seniority_mismatch")

    # Recommendation gates
    if fit < 40:
        recommendation = "SKIP"
    elif (
        fit >= 80
        and coverage >= 0.7
        and missing_n == 0
        and bool(must)  # require explicit must-haves for AUTO_APPLY
    ):
        recommendation = "AUTO_APPLY"
    else:
        recommendation = "REVIEW"

    rationale = _truncate_rationale(
        f"coverage={coverage:.2f} missing={missing_n} role={role_m:.2f} "
        f"loc={loc_m:.2f} sen={sen_m:.2f} comp={comp_m:.2f} → {recommendation}."
    )

    return {
        "fit_score": fit,
        "must_have_coverage": round(coverage, 4),
        "coverage_detail": coverage_detail,
        "role_family_match": round(role_m, 4),
        "location_workmode_fit": round(loc_m, 4),
        "seniority_fit": round(sen_m, 4),
        "compensation_vs_floor": round(comp_m, 4),
        "recommendation": recommendation,
        "flags": flags,
        "rationale": rationale,
    }


def score_fit_deterministic(
    structured_jd: Dict[str, Any],
    candidate_facts: Dict[str, Any],
    *,
    title_weight: float = 0.7,  # retained for call-site compat; unused in P2 v1.1 formula
    job_title: str = "",
    job_location: str = "",
) -> Dict[str, Any]:
    """Deterministic P2 judge + legacy aliases for pipeline/bandit."""
    judged = judge_fit(
        candidate_facts,
        structured_jd,
        job_title=job_title or str(structured_jd.get("title") or ""),
        job_location=job_location or str(structured_jd.get("location") or ""),
    )
    detail = judged["coverage_detail"]
    direct = [d["must_have"] for d in detail if d["evidence"] == "direct"]
    transferable = [d["must_have"] for d in detail if d["evidence"] == "transferable"]
    missing = [d["must_have"] for d in detail if d["evidence"] == "missing"]
    coverage_pct = round(float(judged["must_have_coverage"]) * 100.0, 1)

    return {
        **judged,
        # Legacy aliases used by MatchingPipeline / eval / bandit
        "must_have_coverage_lists": {
            "direct": direct,
            "transferable": transferable,
            "missing": missing,
        },
        "must_have_coverage": judged["must_have_coverage"],  # float 0-1 (contract)
        "coverage_pct": coverage_pct,
        "fit_score": judged["fit_score"],
        "decision": judged["recommendation"],
        "rationale": judged["rationale"],
        "scorer": "p2_judge_v1.1",
    }


def score_fit_llm(
    structured_jd: Dict[str, Any],
    candidate_facts: Dict[str, Any],
    *,
    gateway: Optional[LLMGateway] = None,
) -> Dict[str, Any]:
    gw = gateway or LLMGateway()
    resp = gw.call(
        "P2_fit_score",
        {
            "candidate_facts": candidate_facts,
            "jd_structured": structured_jd,
        },
    )
    data = dict(resp.data)
    # Server-side gate enforcement (never trust model alone for AUTO_APPLY)
    fit = int(data.get("fit_score") or 0)
    cov = float(data.get("must_have_coverage") or 0)
    detail = data.get("coverage_detail") or []
    missing_n = sum(1 for d in detail if (d or {}).get("evidence") == "missing")
    must_n = len(detail)

    if fit < 40:
        data["recommendation"] = "SKIP"
    elif fit >= 80 and cov >= 0.7 and missing_n == 0 and must_n > 0:
        data["recommendation"] = "AUTO_APPLY"
    else:
        data["recommendation"] = "REVIEW"

    data["decision"] = data["recommendation"]
    data["coverage_pct"] = round(cov * 100.0, 1)
    data["rationale"] = _truncate_rationale(str(data.get("rationale") or ""))
    data["scorer"] = "llm"
    data["_meta"] = {
        "prompt_version": resp.prompt_version,
        "cached": resp.cached,
        "cost_usd": resp.cost_usd,
    }
    return data


def to_bandit_context(job: Dict[str, Any], stage_c: Dict[str, Any]) -> Dict[str, Any]:
    """Features for existing LinUCB extract_context_vector."""
    return {
        **job,
        "match_score": stage_c.get("fit_score"),
        "required_yoe": job.get("exp") or job.get("experience_required") or (
            (stage_c.get("coverage_detail") and None)
        ),
        "platform": job.get("ats") or job.get("ats_type") or job.get("platform"),
        "coverage_pct": stage_c.get("coverage_pct"),
        "decision": stage_c.get("decision") or stage_c.get("recommendation"),
    }
