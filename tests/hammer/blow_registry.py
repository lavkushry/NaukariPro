"""
Blow registry for Big Hammer Protocol — 420 distinct blows across H1–H12.

Backed by tests.hammer.catalog (no seed-rotation / __mutNN padding).
"""

from __future__ import annotations

from typing import Dict, List

from tests.hammer.catalog import CATALOG

# Counts per master prompt (kept for scripts)
HAMMER_COUNTS = {
    "H1": 50,
    "H2": 45,
    "H3": 40,
    "H4": 30,
    "H5": 30,
    "H6": 25,
    "H7": 35,
    "H8": 45,
    "H9": 25,
    "H10": 40,
    "H11": 30,
    "H12": 25,
}

HAMMER_NAMES = {
    "H1": "input",
    "H2": "llm",
    "H3": "state",
    "H4": "concurrency",
    "H5": "resource",
    "H6": "time",
    "H7": "network",
    "H8": "form",
    "H9": "identity",
    "H10": "security",
    "H11": "runtime",
    "H12": "operator",
}


def build_all_blows() -> List[Dict[str, str]]:
    blows: List[Dict[str, str]] = []
    for spec in CATALOG:
        blows.append(
            {
                "blow_id": spec["blow_id"],
                "hammer": spec["hammer"],
                "vector": spec["vector"],
                "target": spec["target"],
                "attack": spec["attack"],
                "kind": spec["kind"],
                "expect": spec["expect"],
            }
        )
    assert len(blows) == 420, len(blows)
    return blows


ALL_BLOWS = build_all_blows()
