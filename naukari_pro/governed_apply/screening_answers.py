"""
P4 screening answerer — profile-only, never invent, ASK_USER when unsure.
Plain text; open-ended must cite real employer + title from experience.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

BANNED_PHRASES = [
    "passionate about",
    "excited about",
    "i hope this finds you well",
    "proven track record",
    "results-driven",
    "team player",
]

BANNED_PUFFERY = [
    "effective",
    "crucial",
    "seamless",
    "world-class",
    "extensive",
]

LEGAL_RE = re.compile(
    r"(?i)\b("
    r"authorized to work|right to work|work authorization|visa|sponsorship|"
    r"require sponsorship|citizenship|ethnicity|race|gender|sex|disability|"
    r"veteran|criminal|conviction|demographic|lgbt|sexual orientation|"
    r"religion|hispanic|eeo|equal opportunity"
    r")\b"
)

YES_NO_RE = re.compile(
    r"(?i)^(do you|are you|have you|will you|can you|is there)\b|\b(yes\/no|y\/n)\b"
)


def _ask(reason_note: str = "ASK_USER", grounding: Optional[List[str]] = None) -> Dict[str, Any]:
    # reason_note kept for callers via optional internal use; contract JSON omits it
    return {
        "answer": None,
        "reason": "ASK_USER",
        "grounding": grounding or [],
        "confidence": 0.0,
    }


def _ok(answer: str, grounding: List[str], confidence: float) -> Dict[str, Any]:
    cleaned = _scrub_banned(answer)
    return {
        "answer": cleaned,
        "reason": "ok",
        "grounding": grounding,
        "confidence": round(max(0.0, min(1.0, confidence)), 3),
    }


def _scrub_banned(text: str) -> str:
    out = text or ""
    # strip markdown-ish and em dashes
    out = out.replace("—", "-").replace("–", "-")
    out = re.sub(r"[#*`]", "", out)
    out = re.sub(r"(?m)^\s*[-•]\s+", "", out)
    low = out.lower()
    for phrase in BANNED_PHRASES:
        if phrase in low:
            # remove the phrase occurrence case-insensitively
            out = re.sub(re.escape(phrase), "", out, flags=re.I)
            low = out.lower()
    # puffery words only stripped when present; caller should avoid introducing them
    for w in BANNED_PUFFERY:
        out = re.sub(rf"\b{re.escape(w)}\b", "", out, flags=re.I)
    out = re.sub(r"\s{2,}", " ", out).strip(" ,;")
    return out.strip()


def _experience_roles(profile: Dict[str, Any]) -> List[Dict[str, str]]:
    roles: List[Dict[str, str]] = []
    for item in profile.get("experience") or []:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or item.get("role") or "").strip()
        company = str(item.get("company") or item.get("employer") or "").strip()
        if title and company:
            roles.append({"title": title, "company": company, "raw": item})
    return roles


def _primary_role(profile: Dict[str, Any]) -> Optional[Dict[str, str]]:
    roles = _experience_roles(profile)
    return roles[0] if roles else None


def _apply_limit(text: str, character_limit: Optional[int]) -> str:
    if character_limit is None:
        return text
    try:
        n = int(character_limit)
    except (TypeError, ValueError):
        return text
    if n <= 0:
        return text
    if len(text) <= n:
        return text
    return text[: max(0, n - 1)].rstrip() + "."


def _legal_stored(profile: Dict[str, Any], question: str) -> Optional[Tuple[str, str]]:
    legal = profile.get("legal_answers") or {}
    if not isinstance(legal, dict) or not legal:
        return None
    q = question.lower()
    # map common keys
    key_map = [
        (("authorized to work", "right to work", "work authorization"), "authorized_to_work"),
        (("sponsorship", "visa"), "sponsorship"),
        (("gender",), "gender"),
        (("ethnicity", "race", "hispanic"), "ethnicity"),
        (("disability",), "disability"),
        (("veteran",), "veteran"),
        (("criminal", "conviction"), "criminal_record"),
    ]
    for needles, key in key_map:
        if any(n in q for n in needles) and legal.get(key) is not None and str(legal.get(key)).strip():
            return str(legal[key]), f"legal_answers.{key}"
    # exact question key fallback
    for k, v in legal.items():
        if k.lower() in q and v is not None and str(v).strip():
            return str(v), f"legal_answers.{k}"
    return None


def _contact_answer(profile: Dict[str, Any], question: str) -> Optional[Tuple[str, str]]:
    q = question.lower()
    pairs = [
        (("email",), "email", profile.get("email") or profile.get("contact_email")),
        (("phone", "mobile"), "phone", profile.get("phone") or profile.get("mobile")),
        (("linkedin",), "linkedin", profile.get("linkedin")),
        (("github",), "github", profile.get("github")),
        (("name", "full name"), "name", profile.get("name") or profile.get("full_name")),
        (("city", "location", "current location"), "location", profile.get("city") or profile.get("location")),
        (("notice",), "notice_period", profile.get("notice_period")),
        (("expected ctc", "expected salary", "current ctc", "current salary"), "expected_ctc",
         profile.get("expected_ctc") or profile.get("expected_ctc_lpa") or profile.get("salary_floor_lpa")),
        (("total experience", "years of experience", "how many years"), "yoe", profile.get("yoe") or profile.get("years_of_experience")),
    ]
    for needles, key, val in pairs:
        if any(n in q for n in needles) and val is not None and str(val).strip():
            return str(val), f"profile.{key}"
    return None


def _skill_yes_no(profile: Dict[str, Any], question: str) -> Optional[Tuple[str, List[str], float]]:
    """If question asks about a skill present in profile, answer Yes with grounding."""
    skills = [str(s) for s in (profile.get("skills") or profile.get("key_skills") or [])]
    if not skills:
        return None
    q = question.lower()
    matched = [s for s in skills if len(str(s)) >= 2 and str(s).lower() in q]
    if not matched:
        return None
    role = _primary_role(profile)
    skill = matched[0]
    if role:
        ans = (
            f"Yes. I used {skill} as {role['title']} at {role['company']}."
        )
        grounding = [f"skills.{skill}", f"experience.{role['company']}.{role['title']}"]
    else:
        # open-ended rule requires employer+title for long answers; for yes_no one sentence ok
        ans = f"Yes. {skill} is listed in my skills."
        grounding = [f"skills.{skill}"]
    return ans, grounding, 0.85


def _open_ended(profile: Dict[str, Any], question: str, job_title: str, company: str) -> Optional[Tuple[str, List[str], float]]:
    role = _primary_role(profile)
    if not role:
        return None  # cannot satisfy open-ended grounding rule
    skills = [str(s) for s in (profile.get("skills") or [])[:4]]
    skill_bit = ", ".join(skills[:3]) if skills else ""
    # Keep factual, no puffery. Do not narrate employer names from JOB_CONTEXT
    # (that would look like invented employment). Reference title only if given.
    target = (job_title or "this role").strip() or "this role"
    if skill_bit:
        ans = (
            f"In my role as {role['title']} at {role['company']}, I worked with {skill_bit}. "
            f"That background is relevant to a {target} role."
        )
        grounding = [
            f"experience.{role['company']}.{role['title']}",
            *[f"skills.{s}" for s in skills[:3]],
        ]
    else:
        ans = (
            f"As {role['title']} at {role['company']}, I handled day-to-day work "
            f"closest to a {target} role."
        )
        grounding = [f"experience.{role['company']}.{role['title']}"]
    # Ensure employer and title both appear
    if role["company"] not in ans or role["title"] not in ans:
        return None
    return ans, grounding, 0.75


def answer_screening_question(
    *,
    profile: Optional[Dict[str, Any]],
    question: str,
    question_type: str = "short_text",
    character_limit: Optional[int] = None,
    job_title: str = "",
    company: str = "",
) -> Dict[str, Any]:
    """
    Return {"answer", "reason", "grounding", "confidence"} per P4 v1.1.
    """
    profile = profile or {}
    question = (question or "").strip()
    qtype = (question_type or "short_text").lower().strip()

    if not question or question in ("{{QUESTION}}",):
        return _ask("empty_question")
    if not profile or profile == "{{PROFILE_JSON}}":
        return _ask("empty_profile")

    # Passwords / OTP — never answer
    if re.search(r"(?i)\b(password|otp|one[-\s]?time|2fa|mfa)\b", question):
        return _ask("never_class")

    # Legal / demographic
    if LEGAL_RE.search(question):
        stored = _legal_stored(profile, question)
        if stored:
            val, ref = stored
            text = _apply_limit(str(val), character_limit)
            return _ok(text, [ref], 0.95)
        return _ask("legal_requires_user")

    # Contact / structured short fields
    contact = _contact_answer(profile, question)
    if contact and qtype in ("short_text", "dropdown", "yes_no"):
        val, ref = contact
        if qtype == "yes_no" and val.lower() not in ("yes", "no", "y", "n", "true", "false"):
            # numeric/contact field mislabeled as yes_no — still return value for short
            pass
        return _ok(_apply_limit(str(val), character_limit), [ref], 0.9)

    # Yes/No skill or experience questions
    if qtype == "yes_no" or YES_NO_RE.search(question):
        skill_ans = _skill_yes_no(profile, question)
        if skill_ans:
            ans, grounding, conf = skill_ans
            return _ok(_apply_limit(ans, character_limit), grounding, conf)
        # notice period / willing to relocate style without facts → ASK_USER
        return _ask("yes_no_ungrounded")

    # Dropdown: only answer when option clearly matches a profile fact
    if qtype == "dropdown":
        contact = _contact_answer(profile, question)
        if contact:
            val, ref = contact
            return _ok(_apply_limit(str(val), character_limit), [ref], 0.85)
        return _ask("dropdown_ungrounded")

    # Open-ended short/long text
    if qtype in ("short_text", "long_text"):
        # Prefer contact-like short answers when the question is clearly a field
        contact = _contact_answer(profile, question)
        if contact and qtype == "short_text" and len(question.split()) <= 6:
            val, ref = contact
            return _ok(_apply_limit(str(val), character_limit), [ref], 0.9)

        open_ans = _open_ended(profile, question, job_title, company)
        if open_ans:
            ans, grounding, conf = open_ans
            return _ok(_apply_limit(ans, character_limit), grounding, conf)
        return _ask("open_ended_needs_experience")

    return _ask("unsupported_or_ungrounded")


def answer_from_profile_batch(
    profile: Dict[str, Any],
    questions: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Helper for multiple questions; each result follows P4 single-object shape."""
    out = []
    for q in questions:
        out.append(
            answer_screening_question(
                profile=profile,
                question=str(q.get("question") or q.get("label") or ""),
                question_type=str(q.get("type") or q.get("question_type") or "short_text"),
                character_limit=q.get("character_limit"),
                job_title=str(q.get("job_title") or ""),
                company=str(q.get("company") or ""),
            )
        )
    return out
