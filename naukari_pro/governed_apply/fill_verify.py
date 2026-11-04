"""
Four-layer fill verification (autoapplycv pattern).

1) DOM readback
2) checkValidity()
3) ARIA state (aria-checked/selected/pressed)
4) visible error banners

Plus commit-and-verify for React forms: page-visible value is not enough until
the form model holds it (caller supplies model_value).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class FieldVerifyResult:
    field_id: str
    expected: str
    layer1_dom: bool
    layer2_validity: bool
    layer3_aria: bool
    layer4_no_errors: bool
    commit_verified: bool
    ok: bool
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field_id": self.field_id,
            "expected": self.expected,
            "layer1_dom": self.layer1_dom,
            "layer2_validity": self.layer2_validity,
            "layer3_aria": self.layer3_aria,
            "layer4_no_errors": self.layer4_no_errors,
            "commit_verified": self.commit_verified,
            "ok": self.ok,
            "details": self.details,
        }


def _norm(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v).strip()


def verify_field(
    *,
    field_id: str,
    expected: str,
    dom_value: Any = None,
    check_validity: Optional[bool] = None,
    aria: Optional[Dict[str, Any]] = None,
    error_banners: Optional[List[str]] = None,
    model_value: Any = None,
    require_commit: bool = True,
) -> FieldVerifyResult:
    exp = _norm(expected)
    # Empty expected means the field must be blank — never a tautology that
    # accepts attacker-controlled DOM (Phase-5 F1).
    layer1 = _norm(dom_value) == exp
    layer2 = True if check_validity is None else bool(check_validity)
    aria = aria or {}
    # For checkboxes/radios, ARIA must reflect selection when expected truthy
    if exp.lower() in ("true", "yes", "1", "on", "checked"):
        layer3 = bool(
            aria.get("aria-checked") in (True, "true")
            or aria.get("aria-selected") in (True, "true")
            or aria.get("aria-pressed") in (True, "true")
            or _norm(dom_value).lower() in ("true", "yes", "1", "on", "checked")
        )
    else:
        layer3 = True  # text fields: ARIA layer N/A → pass
    banners = [b for b in (error_banners or []) if b and str(b).strip()]
    layer4 = len(banners) == 0
    if require_commit:
        commit_ok = _norm(model_value) == exp
    else:
        commit_ok = True
    ok = layer1 and layer2 and layer3 and layer4 and commit_ok
    return FieldVerifyResult(
        field_id=field_id,
        expected=exp,
        layer1_dom=layer1,
        layer2_validity=layer2,
        layer3_aria=layer3,
        layer4_no_errors=layer4,
        commit_verified=commit_ok,
        ok=ok,
        details={"error_banners": banners, "dom_value": dom_value, "model_value": model_value},
    )


def verify_form(fields: List[Dict[str, Any]]) -> Dict[str, Any]:
    results = [verify_field(**f) for f in fields]
    passed = sum(1 for r in results if r.ok)
    return {
        "passed": passed,
        "total": len(results),
        "all_ok": passed == len(results) and len(results) > 0,
        "layers_summary": f"{passed}/{len(results)}",
        "fields": [r.to_dict() for r in results],
    }
