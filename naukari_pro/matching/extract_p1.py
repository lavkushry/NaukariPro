"""
Deterministic P1 extractor (offline / no-LLM).
Truth-only: never invent salary, years, or requirements not marked in text.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

SENIORITY_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\b(intern|internship)\b", re.I), "intern"),
    (re.compile(r"\b(director|vp|vice\s*president|head of|chief)\b", re.I), "director_plus"),
    (re.compile(r"\b(manager|management)\b", re.I), "manager"),
    (re.compile(r"\b(staff|principal|distinguished|fellow)\b", re.I), "staff"),
    (re.compile(r"\b(lead|tech\s*lead|team\s*lead)\b", re.I), "lead"),
    (re.compile(r"\b(senior|sr\.?)\b", re.I), "senior"),
    (re.compile(r"\b(junior|jr\.?|entry[-\s]?level|graduate|new\s*grad)\b", re.I), "entry"),
    (re.compile(r"\b(mid[-\s]?level|intermediate)\b", re.I), "mid"),
]

REMOTE_RE = re.compile(r"\b(remote|work\s*from\s*home|wfh|distributed)\b", re.I)
HYBRID_RE = re.compile(r"\bhybrid\b", re.I)
ONSITE_RE = re.compile(r"\b(on[-\s]?site|in[-\s]?office|office[-\s]?based)\b", re.I)

MUST_HDR = re.compile(
    r"(?im)^(?:\s*(?:requirements?|required|qualifications?|what you(?:'ll| will)? need|"
    r"must[-\s]?haves?|must have|essential|essentials?)[:\s]*)\s*$"
)
NICE_HDR = re.compile(
    r"(?im)^(?:\s*(?:nice[-\s]?to[-\s]?haves?|nice-to-have|preferred|bonus|"
    r"good to have|pluses?|desired)[:\s]*)\s*$"
)
RESP_HDR = re.compile(
    r"(?im)^(?:\s*(?:responsibilities|what you(?:'ll| will) do|the role|"
    r"about the (?:role|job)|day to day)[:\s]*)\s*$"
)

SALARY_RE = re.compile(
    r"(?i)(?:₹|rs\.?|inr|usd|\$|€|£)?\s*\d[\d,]*(?:\.\d+)?\s*"
    r"(?:[-–to]+\s*(?:₹|rs\.?|inr|usd|\$|€|£)?\s*\d[\d,]*(?:\.\d+)?)?\s*"
    r"(?:lpa|lacs?|lac|lakhs?|k|per\s*year|/yr|annually|a year)?"
)

YOE_RE = re.compile(
    r"(?i)(?:minimum|min\.?|at least|require[sd]?|must have)?\s*"
    r"(\d+(?:\.\d+)?)\s*[+\-]?\s*(?:\d+(?:\.\d+)?)?\s*"
    r"(?:\+?\s*)?(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp\.?)?"
)

ATS_TOKEN_RE = re.compile(
    r"\b(?:Azure|AWS|GCP|Python|PySpark|Spark|Databricks|Delta(?:\s*Lake)?|"
    r"Kafka|Terraform|Kubernetes|K8s|Docker|SQL|NoSQL|ADF|Airflow|dbt|"
    r"Snowflake|MLflow|CI/?CD|Linux|Java|Scala|Go|React|TypeScript|"
    r"PostgreSQL|MongoDB|Redis|Grafana|Prometheus|Helm|ArgoCD|Git|"
    r"Unity\s*Catalog|Medallion|Lakehouse|ETL|ELT|REST|gRPC|FastAPI|"
    r"Bachelor'?s|Master'?s|PhD|PMP|CKA|AWS\s*Certified)\b",
    re.I,
)

BULLET_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+(.+)$", re.M)
MUST_INLINE = re.compile(r"(?i)\b(?:must|required|essential)\b.{0,80}")
NICE_INLINE = re.compile(r"(?i)\b(?:preferred|nice[-\s]?to[-\s]?have|bonus)\b.{0,80}")


def _section_blocks(text: str) -> Dict[str, List[str]]:
    lines = (text or "").splitlines()
    current = "body"
    buckets: Dict[str, List[str]] = {"body": [], "must": [], "nice": [], "resp": []}
    for line in lines:
        if MUST_HDR.match(line.strip()):
            current = "must"
            continue
        if NICE_HDR.match(line.strip()):
            current = "nice"
            continue
        if RESP_HDR.match(line.strip()):
            current = "resp"
            continue
        buckets[current].append(line)
    return buckets


def _bullets(lines: List[str]) -> List[str]:
    blob = "\n".join(lines)
    items = [m.group(1).strip() for m in BULLET_RE.finditer(blob)]
    return [i for i in items if i]


def _work_mode(text: str) -> str:
    if REMOTE_RE.search(text):
        return "remote"
    if HYBRID_RE.search(text):
        return "hybrid"
    if ONSITE_RE.search(text):
        return "onsite"
    return "unknown"


def _salary_signals(text: str) -> List[str]:
    found = []
    for m in SALARY_RE.finditer(text or ""):
        s = m.group(0).strip()
        # Filter noise like lone small numbers without currency/unit
        if re.search(r"(?i)lpa|lac|lakh|₹|\$|usd|inr|k\b|per\s*year|/yr|annually", s) or "–" in s or "-" in s:
            if s not in found:
                found.append(s)
    return found


def _min_years(text: str) -> Optional[float]:
    # Only when experience language is present
    for m in YOE_RE.finditer(text or ""):
        ctx = text[max(0, m.start() - 40) : m.end() + 40].lower()
        if "year" not in ctx and "yr" not in ctx:
            continue
        if any(k in ctx for k in ("experience", "exp", "minimum", "at least", "require", "must")):
            try:
                return float(m.group(1))
            except ValueError:
                continue
    return None


def _ats_keywords(text: str) -> List[str]:
    seen = set()
    out: List[str] = []
    for m in ATS_TOKEN_RE.finditer(text or ""):
        tok = m.group(0).strip().lower()
        tok = re.sub(r"\s+", " ", tok)
        if tok not in seen:
            seen.add(tok)
            out.append(tok)
        if len(out) >= 25:
            break
    return out


def _role_summary(title: str, company: str, text: str) -> str:
    # First 1-2 non-empty prose sentences from body, capped ~60 words
    prose = re.sub(r"\s+", " ", (text or "").strip())
    if not prose:
        base = " ".join(x for x in [title, f"at {company}" if company else ""] if x).strip()
        return base[:300]
    sentences = re.split(r"(?<=[.!?])\s+", prose)
    words: List[str] = []
    for s in sentences:
        if not s or len(s) < 20:
            continue
        for w in s.split():
            words.append(w)
            if len(words) >= 60:
                return " ".join(words[:60])
        if len(words) >= 25:
            break
    return " ".join(words[:60]) if words else (title or "")[:300]


def extract_p1(
    *,
    description: str,
    title: str = "",
    company: str = "",
    location: str = "",
) -> Dict[str, Any]:
    """
    Truth-only deterministic extraction matching P1 v1.1 schema.
    Unstated fields → null or [].
    """
    text = description or ""
    blob = "\n".join(x for x in [title, company, location, text] if x)
    blocks = _section_blocks(text)

    must = _bullets(blocks["must"])
    nice = _bullets(blocks["nice"])
    resp = _bullets(blocks["resp"])

    # Inline must/nice only when explicit markers appear on the same fragment
    if not must:
        for m in MUST_INLINE.finditer(text):
            frag = m.group(0).strip()
            # Only keep if it looks like a requirement clause, not a random "must"
            if len(frag) > 15:
                must.append(frag)
                if len(must) >= 8:
                    break
    if not nice:
        for m in NICE_INLINE.finditer(text):
            frag = m.group(0).strip()
            if len(frag) > 15:
                nice.append(frag)
                if len(nice) >= 8:
                    break

    seniority = None
    for cre, label in SENIORITY_PATTERNS:
        if cre.search(blob):
            seniority = label
            break

    return {
        "role_summary": _role_summary(title, company, text),
        "responsibilities": resp,
        "must_haves": must,
        "nice_to_haves": nice,
        "ats_keywords": _ats_keywords(blob),
        "seniority": seniority,  # null if unstated
        "work_mode": _work_mode(blob),
        "salary_signals": _salary_signals(text),
        "min_years_experience": _min_years(text),
    }
