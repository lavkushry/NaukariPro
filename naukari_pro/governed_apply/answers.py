"""Answer routing with ASK_USER into quarantine — never guess missing evidence."""

from __future__ import annotations

from typing import Any, Dict, Optional

from naukari_pro.governed_apply.field_inventory import FieldHint
from naukari_pro.governed_apply.screening_answers import answer_screening_question
from naukari_pro.governed_apply.sensitivity import Sensitivity, mask_for_log


def answer_from_facts(
    hint: FieldHint,
    candidate_facts: Dict[str, Any],
    *,
    gateway: Optional[Any] = None,
    use_llm: bool = False,
    job_title: str = "",
    company: str = "",
    question_type: Optional[str] = None,
    character_limit: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Returns governed fill payload plus P4 contract fields.
    action: ANSWER | ASK_USER | SKIP
    """
    sens = hint.sensitivity
    if sens == Sensitivity.NEVER:
        return {
            "action": "SKIP",
            "value": None,
            "sensitivity": sens.value,
            "evidence_ref": None,
            "value_masked": "",
            "reason": "ASK_USER",
            "answer": None,
            "grounding": [],
            "confidence": 0.0,
        }

    qtype = question_type or _infer_type(hint)
    if use_llm and gateway is not None:
        try:
            resp = gateway.call(
                "P4_application_answers",
                {
                    "candidate_facts": candidate_facts or {},
                    "question": hint.label,
                    "question_type": qtype,
                    "character_limit": character_limit if character_limit is not None else "null",
                    "job_title": job_title or "",
                    "company": company or "",
                },
            )
            data = dict(resp.data)
            # Server-side: never accept invented legal answers
            if sens == Sensitivity.LEGAL and data.get("reason") != "ASK_USER":
                legal = (candidate_facts or {}).get("legal_answers") or {}
                if not legal:
                    data = {
                        "answer": None,
                        "reason": "ASK_USER",
                        "grounding": [],
                        "confidence": 0.0,
                    }
            return _to_governed(data, sens)
        except Exception:
            pass  # fall through to deterministic

    result = answer_screening_question(
        profile=candidate_facts or {},
        question=hint.label,
        question_type=qtype,
        character_limit=character_limit,
        job_title=job_title,
        company=company,
    )
    return _to_governed(result, sens)


def _infer_type(hint: FieldHint) -> str:
    t = (hint.input_type or "").lower()
    if t in ("checkbox", "radio") or t == "yes_no":
        return "yes_no"
    if t in ("select", "dropdown") or hint.options:
        return "dropdown"
    if t in ("textarea", "long_text"):
        return "long_text"
    return "short_text"


def _to_governed(p4: Dict[str, Any], sens: Sensitivity) -> Dict[str, Any]:
    reason = p4.get("reason") or "ASK_USER"
    answer = p4.get("answer")
    grounding = list(p4.get("grounding") or [])
    if reason == "ASK_USER" or answer is None:
        action = "ASK_USER"
        value = None
    else:
        action = "ANSWER"
        value = str(answer)
    return {
        "action": action,
        "value": value,
        "sensitivity": sens.value,
        "evidence_ref": grounding[0] if grounding else None,
        "value_masked": mask_for_log(value, sens) if value else "",
        "reason": reason,
        "answer": answer,
        "grounding": grounding,
        "confidence": float(p4.get("confidence") or 0.0),
    }
