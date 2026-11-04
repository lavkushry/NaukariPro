"""Mechanical-first field inventory — DOM heuristics first, LLM fallback only on failure."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from naukari_pro.governed_apply.sensitivity import Sensitivity, classify_question


@dataclass
class FieldHint:
    field_id: str
    label: str
    input_type: str
    sensitivity: Sensitivity
    required: bool = False
    options: List[str] = field(default_factory=list)
    source: str = "heuristic"  # heuristic | llm | cache


# Per-host cached hints (in-memory; persist via store later)
_HOST_CACHE: Dict[str, List[Dict[str, Any]]] = {}


def cache_hints(host: str, hints: List[FieldHint]) -> None:
    _HOST_CACHE[host.lower()] = [
        {
            "field_id": h.field_id,
            "label": h.label,
            "input_type": h.input_type,
            "sensitivity": h.sensitivity.value,
            "required": h.required,
            "options": h.options,
            "source": "cache",
        }
        for h in hints
    ]


def cached_hints(host: str) -> Optional[List[FieldHint]]:
    raw = _HOST_CACHE.get(host.lower())
    if not raw:
        return None
    return [
        FieldHint(
            field_id=r["field_id"],
            label=r["label"],
            input_type=r["input_type"],
            sensitivity=Sensitivity(r["sensitivity"]),
            required=bool(r.get("required")),
            options=list(r.get("options") or []),
            source="cache",
        )
        for r in raw
    ]


def inventory_from_dom_snapshot(fields: List[Dict[str, Any]], *, host: str = "") -> List[FieldHint]:
    """
    Heuristic inventory from a Playwright-like field snapshot:
    [{name, id, type, label, required, options}]
    """
    cached = cached_hints(host) if host else None
    if cached:
        return cached

    out: List[FieldHint] = []
    for i, f in enumerate(fields):
        label = str(f.get("label") or f.get("aria_label") or f.get("name") or f.get("id") or f"field_{i}")
        fid = str(f.get("id") or f.get("name") or f"field_{i}")
        itype = str(f.get("type") or f.get("tag") or "text").lower()
        sens = classify_question(label)
        # Password inputs always NEVER
        if itype == "password" or "otp" in label.lower():
            sens = Sensitivity.NEVER
        out.append(
            FieldHint(
                field_id=fid,
                label=label,
                input_type=itype,
                sensitivity=sens,
                required=bool(f.get("required")),
                options=[str(o) for o in (f.get("options") or [])],
                source="heuristic",
            )
        )
    if host:
        cache_hints(host, out)
    return out


def needs_llm_fallback(hints: List[FieldHint], raw_fields: List[Dict[str, Any]]) -> bool:
    """LLM only when heuristics fail to label majority of fields."""
    if not raw_fields:
        return False
    unlabeled = sum(1 for h in hints if re.match(r"^field_\d+$", h.label))
    return unlabeled / max(len(raw_fields), 1) > 0.5
