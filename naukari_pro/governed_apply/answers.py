"""Answer routing with ASK_USER into quarantine — never guess missing evidence."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from naukari_pro.governed_apply.field_inventory import FieldHint
from naukari_pro.governed_apply.sensitivity import Sensitivity, mask_for_log


def answer_from_facts(
    hint: FieldHint,
    candidate_facts: Dict[str, Any],
    *,
    gateway: Optional[Any] = None,
    use_llm: bool = False,
) -> Dict[str, Any]:
    """
    Returns {action, value, sensitivity, evidence_ref, value_masked}
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
            "reason": "NEVER class — refuse",
        }

    # Deterministic map for CONTACT
    label_l = hint.label.lower()
    facts = candidate_facts or {}
    contact_map = {
        "email": facts.get("email") or facts.get("contact_email"),
        "phone": facts.get("phone") or facts.get("mobile"),
        "linkedin": facts.get("linkedin"),
        "github": facts.get("github"),
        "name": facts.get("name") or facts.get("full_name"),
        "city": facts.get("city") or facts.get("location"),
    }

    if sens == Sensitivity.CONTACT:
        for key, val in contact_map.items():
            if key in label_l and val:
                return {
                    "action": "ANSWER",
                    "value": str(val),
                    "sensitivity": sens.value,
                    "evidence_ref": f"facts.{key}",
                    "value_masked": mask_for_log(str(val), sens),
                }
        return _ask(hint, sens)

    if sens in (Sensitivity.LEGAL, Sensitivity.SENSITIVE):
        # Prefer ASK_USER unless an explicit fact key exists
        for key in ("authorized_to_work", "visa_status", "expected_ctc", "current_ctc", "notice_period"):
            if key.replace("_", " ") in label_l or key in label_l:
                val = facts.get(key)
                if val is not None and str(val).strip():
                    return {
                        "action": "ANSWER",
                        "value": str(val),
                        "sensitivity": sens.value,
                        "evidence_ref": f"facts.{key}",
                        "value_masked": mask_for_log(str(val), sens),
                    }
        return _ask(hint, sens)

    # JOB_SPECIFIC — only answer if keyword evidence exists in facts blob
    blob = " ".join(str(v) for v in facts.values() if not isinstance(v, (dict, list)))
    for skill in facts.get("skills") or []:
        if str(skill).lower() in label_l:
            return {
                "action": "ANSWER",
                "value": "Yes",
                "sensitivity": sens.value,
                "evidence_ref": f"skills.{skill}",
                "value_masked": "Yes",
            }
    if use_llm and gateway is not None:
        resp = gateway.call(
            "P4_application_answers",
            {
                "candidate_facts": facts,
                "questions": [{"question_id": hint.field_id, "label": hint.label}],
            },
        )
        answers = (resp.data or {}).get("answers") or []
        if answers:
            a = answers[0]
            action = a.get("action") or "ASK_USER"
            value = a.get("value")
            return {
                "action": action,
                "value": value,
                "sensitivity": sens.value,
                "evidence_ref": a.get("evidence_ref"),
                "value_masked": mask_for_log(value, sens) if value else "",
            }

    # years of experience heuristic
    if "year" in label_l and "experience" in label_l and facts.get("yoe") is not None:
        val = str(facts.get("yoe"))
        return {
            "action": "ANSWER",
            "value": val,
            "sensitivity": sens.value,
            "evidence_ref": "facts.yoe",
            "value_masked": val,
        }

    if blob and any(tok in blob.lower() for tok in label_l.split() if len(tok) > 3):
        return _ask(hint, sens)  # related but no clear answer → ask
    return _ask(hint, sens)


def _ask(hint: FieldHint, sens: Sensitivity) -> Dict[str, Any]:
    return {
        "action": "ASK_USER",
        "value": None,
        "sensitivity": sens.value,
        "evidence_ref": None,
        "value_masked": "",
        "reason": "missing_evidence",
    }
