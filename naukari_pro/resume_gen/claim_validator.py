"""
Grounding validator (snapply claim_validator pattern).

- Per-sentence support ≥ 0.25
- Novelty-ratio cap 0.34
- PUFFERY regex blocks unsupported quality words
- Numbers/credentials must appear verbatim in evidence
- TAIL regex trims invented trailing clauses
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence


PUFFERY = re.compile(
    r"\b("
    r"effective|crucial|proven\s+track\s+record|fostered|synergy|robust|"
    r"best[-\s]?in[-\s]?class|world[-\s]?class|cutting[-\s]?edge|leveraged|"
    r"spearheaded\s+transformational|highly\s+skilled|passionate"
    r")\b",
    re.I,
)

TAIL = re.compile(
    r",\s*which\s+helped\b.*$|"
    r",\s*thereby\s+\w+ing\b.*$|"
    r",\s*ensuring\b.*$|"
    r",\s*resulting\s+in\s+(?:significant|improved|better)\b.*$",
    re.I,
)

# Include unit suffixes (ms/s/x) so fabricated latency metrics cannot slip (Phase-5 F3).
NUMBER_RE = re.compile(
    r"\b\d+(?:\.\d+)?(?:%|ms|s|x)?\b|\b\d+\s*(?:k|m|lpa|lakhs?|ms|sec(?:onds?)?)\b",
    re.I,
)
TOKEN_RE = re.compile(r"[a-z0-9]+", re.I)


@dataclass
class SentenceReport:
    sentence: str
    support: float
    novelty: float
    ok: bool
    reasons: List[str] = field(default_factory=list)


@dataclass
class GroundingReport:
    ok: bool
    sentences: List[SentenceReport]
    unsupported_claims: List[str]
    dropped_sentences: List[str]
    novelty_ratio: float
    provider: str = "deterministic"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "novelty_ratio": self.novelty_ratio,
            "unsupported_claims": list(self.unsupported_claims),
            "dropped_sentences": list(self.dropped_sentences),
            "provider": self.provider,
            "sentences": [
                {
                    "sentence": s.sentence,
                    "support": s.support,
                    "novelty": s.novelty,
                    "ok": s.ok,
                    "reasons": s.reasons,
                }
                for s in self.sentences
            ],
        }


def _tokens(text: str) -> List[str]:
    return [t.lower() for t in TOKEN_RE.findall(text or "")]


def sentence_support(sentence: str, evidence_blob: str) -> float:
    sent_toks = _tokens(sentence)
    if not sent_toks:
        return 1.0
    ev = set(_tokens(evidence_blob))
    overlap = sum(1 for t in sent_toks if t in ev)
    denom = min(len(sent_toks), 8)
    return overlap / float(denom) if denom else 0.0


def novelty_ratio(sentence: str, evidence_blob: str) -> float:
    sent_toks = _tokens(sentence)
    if not sent_toks:
        return 0.0
    ev = set(_tokens(evidence_blob))
    novel = sum(1 for t in sent_toks if t not in ev)
    return novel / float(len(sent_toks))


def split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    return [p.strip() for p in parts if p.strip()]


def trim_tail(sentence: str) -> str:
    return TAIL.sub("", sentence).rstrip(" ,;")


def validate_text(
    text: str,
    evidence: Sequence[str],
    *,
    support_threshold: float = 0.25,
    novelty_cap: float = 0.34,
    drop_ungrounded: bool = True,
) -> GroundingReport:
    evidence_blob = "\n".join(evidence or [])
    reports: List[SentenceReport] = []
    unsupported: List[str] = []
    dropped: List[str] = []

    for raw in split_sentences(text):
        sentence = trim_tail(raw)
        reasons: List[str] = []
        support = sentence_support(sentence, evidence_blob)
        novelty = novelty_ratio(sentence, evidence_blob)

        if support < support_threshold:
            reasons.append(f"support<{support_threshold}")
        if novelty > novelty_cap:
            reasons.append(f"novelty>{novelty_cap}")
        if PUFFERY.search(sentence):
            # puffery only fails when not supported by evidence tokens
            if support < 0.5:
                reasons.append("puffery")
        evidence_nums = {n.lower() for n in NUMBER_RE.findall(evidence_blob)}
        for num in NUMBER_RE.findall(sentence):
            # Exact numeric token match — reject substring tricks (1 in 10).
            if num.lower() not in evidence_nums:
                reasons.append(f"unsourced_number:{num}")

        ok = len(reasons) == 0
        reports.append(
            SentenceReport(
                sentence=sentence,
                support=round(support, 4),
                novelty=round(novelty, 4),
                ok=ok,
                reasons=reasons,
            )
        )
        if not ok:
            unsupported.append(sentence)
            if drop_ungrounded:
                dropped.append(sentence)

    # Document-level novelty: share of novel tokens across all sentences
    all_sent = " ".join(r.sentence for r in reports if r.ok or not drop_ungrounded)
    doc_novelty = novelty_ratio(all_sent, evidence_blob) if all_sent else 0.0
    ok = len(unsupported) == 0 and doc_novelty <= novelty_cap
    return GroundingReport(
        ok=ok,
        sentences=reports,
        unsupported_claims=unsupported,
        dropped_sentences=dropped,
        novelty_ratio=round(doc_novelty, 4),
    )


def validate_resume_bullets(
    bullets: Sequence[str],
    evidence: Sequence[str],
) -> GroundingReport:
    return validate_text(" ".join(bullets), evidence)
