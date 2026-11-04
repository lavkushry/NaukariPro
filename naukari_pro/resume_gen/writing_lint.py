"""AI-tell writing lint (please-hire-me app_docs pattern). Verdict: PASS / REWRITE / DO NOT SEND."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

BANNED_PHRASES = [
    "as an ai",
    "written with ai",
    "i am an ai",
    "language model",
    "in today's fast-paced",
    "in conclusion",
    "it is worth noting",
    "delve into",
    "tapestry",
    "multifaceted",
    "leverage synergies",
    "robust solution",
    "seamless integration",
    "cutting-edge",
    "game-changer",
    "passionate about",
    "thrilled to",
    "excited to apply",
    "perfect fit",
    "dynamic environment",
    "hit the ground running",
    "synergistic",
    "holistic approach",
    "paradigm shift",
    "utilize my skills",
    "keen eye for detail",
    "proven track record of excellence",
    "results-driven professional",
    "self-starter with",
    "team player who",
    "think outside the box",
    "move the needle",
    "circle back",
    "low-hanging fruit",
    "best practices and methodologies",
    "spearheaded initiatives that",
    "fostered a culture",
    "drove impactful",
    "empowered stakeholders",
    "unlock value",
    "at the end of the day",
    "going forward",
    "please find attached",
    "i believe i would be",
    "with that being said",
    "first and foremost",
    "it goes without saying",
    "needless to say",
    "in order to effectively",
    "very unique",
    "literally revolutionized",
    "highly effective communicator",
    "here's",
]

AI_LEAK = re.compile(
    r"(written with ai|as an ai|language model|chatgpt|here's what|i hope this helps)",
    re.I,
)
EM_DASH = re.compile(r"—")
BALANCED_TRIAD = re.compile(
    r"\b(\w+),\s+(\w+),\s+and\s+(\w+)\b",
    re.I,
)
FLATTERY = re.compile(
    r"^(dear hiring|i was thrilled|your esteemed|world[- ]class company)",
    re.I,
)
UNSOURCED_NUM = re.compile(r"\b\d{2,}%|\b\d+\s*[xX]\b|\b₹?\d+\s*(?:lakh|lpa|crore)\b")


@dataclass
class LintResult:
    verdict: str  # PASS | REWRITE | DO NOT SEND
    hits: List[str] = field(default_factory=list)

    def to_dict(self):
        return {"verdict": self.verdict, "hits": list(self.hits)}


def lint_text(text: str, *, evidence: Optional[Sequence[str]] = None) -> LintResult:
    hits: List[str] = []
    low = (text or "").lower()
    for phrase in BANNED_PHRASES:
        if phrase in low:
            hits.append(f"banned:{phrase}")
    if AI_LEAK.search(text or ""):
        hits.append("ai_leak")
    if EM_DASH.search(text or ""):
        hits.append("em_dash")
    if FLATTERY.search((text or "").strip()):
        hits.append("flattery_opener")
    # Heuristic: many balanced triads look AI-generated
    if len(BALANCED_TRIAD.findall(text or "")) >= 3:
        hits.append("balanced_triads")

    evidence_blob = "\n".join(evidence or []).lower()
    for m in UNSOURCED_NUM.finditer(text or ""):
        token = m.group(0).lower()
        if evidence is not None and token not in evidence_blob:
            hits.append(f"unsourced_number:{m.group(0)}")

    if any(h.startswith("ai_leak") or h.startswith("banned:as an ai") for h in hits):
        verdict = "DO NOT SEND"
    elif len(hits) >= 3:
        verdict = "REWRITE"
    elif hits:
        verdict = "REWRITE"
    else:
        verdict = "PASS"
    return LintResult(verdict=verdict, hits=hits)
