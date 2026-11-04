"""Tier 5 — optional VLM/text-math helpers (default OFF)."""

from __future__ import annotations

import re
from typing import Optional


_MATH_RE = re.compile(
    r"(?:what\s+is|solve[:\s]*)\s*(\d+)\s*([+\-*/])\s*(\d+)",
    re.I,
)


def try_solve_text_math(prompt: str) -> Optional[str]:
    """Deterministic arithmetic parser for legacy text/math captchas."""
    m = _MATH_RE.search(prompt or "")
    if not m:
        return None
    a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
    if op == "+":
        return str(a + b)
    if op == "-":
        return str(a - b)
    if op == "*":
        return str(a * b)
    if op == "/" and b != 0:
        return str(a // b)
    return None
