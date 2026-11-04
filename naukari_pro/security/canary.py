"""Prompt-injection / AI-canary defense for scraped JD content (please-hire-me)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Set


_CANARY_PATTERNS = [
    re.compile(r"if you are an (?:ai|llm|language model).*include (?:the )?(?:word|phrase)\s+[\"']?([\w\-]+)[\"']?", re.I),
    re.compile(r"append the (?:secret|canary) (?:word|token)\s+[\"']?([\w\-]+)[\"']?", re.I),
    re.compile(r"prove you are (?:an )?ai by (?:writing|including)\s+[\"']?([\w\-]+)[\"']?", re.I),
]

_NO_AI_POLICY = re.compile(
    r"(do not use ai|no ai|without (?:using )?ai|ai[- ]generated (?:answers|content) (?:are|is) (?:not )?(?:allowed|prohibited))",
    re.I,
)

_TAKEHOME = re.compile(
    r"(graded take[- ]?home|take[- ]?home (?:assignment|exam|test)|proctored (?:assessment|exam))",
    re.I,
)


@dataclass
class CanaryScan:
    blocked: bool
    canary_words: List[str] = field(default_factory=list)
    no_ai_policy: bool = False
    graded_takehome: bool = False
    reasons: List[str] = field(default_factory=list)

    def type_hook_blocks(self, text: str) -> bool:
        """Return True if typing `text` would inject a recorded canary word."""
        low = (text or "").lower()
        return any(w.lower() in low for w in self.canary_words)


def scan_posting(text: str) -> CanaryScan:
    canaries: List[str] = []
    reasons: List[str] = []
    for cre in _CANARY_PATTERNS:
        for m in cre.finditer(text or ""):
            word = m.group(1)
            if word and word.lower() not in {c.lower() for c in canaries}:
                canaries.append(word)
                reasons.append(f"canary:{word}")
    no_ai = bool(_NO_AI_POLICY.search(text or ""))
    takehome = bool(_TAKEHOME.search(text or ""))
    if no_ai:
        reasons.append("no_ai_policy")
    if takehome:
        reasons.append("graded_takehome")
    blocked = bool(canaries or no_ai or takehome)
    return CanaryScan(
        blocked=blocked,
        canary_words=canaries,
        no_ai_policy=no_ai,
        graded_takehome=takehome,
        reasons=reasons,
    )


class CanaryTypeHook:
    """Blocks typing recorded canary words into application forms."""

    def __init__(self) -> None:
        self._banned: Set[str] = set()

    def remember(self, scan: CanaryScan) -> None:
        for w in scan.canary_words:
            self._banned.add(w.lower())

    def allow_type(self, text: str) -> bool:
        low = (text or "").lower()
        return not any(w in low for w in self._banned)
