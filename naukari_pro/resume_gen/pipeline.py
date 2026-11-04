"""Resume generation pipeline: tailor → render → score gate (>=85)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from naukari_pro.resume_gen.claim_validator import validate_text
from naukari_pro.resume_gen.render import pypdf_roundtrip_ok, render_resume_docx, render_resume_pdf
from naukari_pro.resume_gen.scorecard import GATE_THRESHOLD, score_ats_100
from naukari_pro.resume_gen.tailor import audit_no_fabrication, tailor_from_facts
from naukari_pro.resume_gen.writing_lint import lint_text


@dataclass
class ResumeArtifact:
    pdf_path: Optional[Path] = None
    docx_path: Optional[Path] = None
    tailored: Dict[str, Any] = field(default_factory=dict)
    score: Dict[str, Any] = field(default_factory=dict)
    fabrication_violations: List[str] = field(default_factory=list)
    dispatch_allowed: bool = False
    gaps_reported: List[str] = field(default_factory=list)
    grounding: Dict[str, Any] = field(default_factory=dict)
    lint: Dict[str, Any] = field(default_factory=dict)


class ResumeGenerationPipeline:
    def __init__(
        self,
        master_facts: Dict[str, Any],
        candidate: Dict[str, Any],
        *,
        output_dir: Optional[Path] = None,
        use_llm: bool = False,
        gateway: Optional[Any] = None,
    ) -> None:
        self.master_facts = master_facts
        self.candidate = candidate
        self.output_dir = Path(output_dir) if output_dir else Path("output") / "tailored_resumes"
        self.use_llm = use_llm
        self.gateway = gateway

    def generate(
        self,
        structured_jd: Dict[str, Any],
        *,
        role: str = "Role",
        company: str = "Company",
        also_docx: bool = True,
    ) -> ResumeArtifact:
        tailored = tailor_from_facts(
            self.master_facts,
            structured_jd,
            use_llm=self.use_llm,
            gateway=self.gateway,
        )
        violations = audit_no_fabrication(tailored, self.master_facts)
        evidence = _facts_to_evidence(self.master_facts)
        bullet_text = " ".join(
            str(b)
            for exp in (tailored.get("experience") or [])
            for b in (exp.get("bullets") or [])
        )
        if not bullet_text:
            bullet_text = str(tailored.get("summary") or "")
        grounding = validate_text(bullet_text, evidence) if bullet_text else None
        lint = lint_text(bullet_text, evidence=evidence) if bullet_text else None
        art = ResumeArtifact(
            tailored=tailored,
            fabrication_violations=violations,
            gaps_reported=list(tailored.get("gaps_reported") or []),
            grounding=grounding.to_dict() if grounding else {},
            lint=lint.to_dict() if lint else {},
        )
        if violations or (grounding and not grounding.ok) or (lint and lint.verdict == "DO NOT SEND"):
            if grounding and not grounding.ok:
                art.fabrication_violations = list(violations) + [
                    f"ungrounded:{c[:80]}" for c in grounding.unsupported_claims[:5]
                ]
            art.dispatch_allowed = False
            return art

        pdf = render_resume_pdf(
            self.candidate, tailored, output_dir=self.output_dir, role=role, company=company
        )
        art.pdf_path = pdf
        if also_docx:
            try:
                art.docx_path = render_resume_docx(
                    self.candidate, tailored, output_dir=self.output_dir, role=role, company=company
                )
            except RuntimeError:
                art.docx_path = None

        kws = list(structured_jd.get("ats_keywords") or []) + list(structured_jd.get("must_haves") or [])
        score = score_ats_100(
            pdf_path=pdf,
            candidate=self.candidate,
            tailored=tailored,
            jd_keywords=[str(k) for k in kws],
        )
        # Round-trip integrity
        if not pypdf_roundtrip_ok(pdf):
            score["gate_passed"] = False
            score["roundtrip_ok"] = False
        else:
            score["roundtrip_ok"] = True

        art.score = score
        art.dispatch_allowed = bool(score.get("gate_passed")) and not violations
        return art


def _facts_to_evidence(master_facts: Dict[str, Any]) -> List[str]:
    """Flatten master profile facts into evidence strings for grounding."""
    out: List[str] = []
    if not master_facts:
        return out
    for k, v in master_facts.items():
        if isinstance(v, str) and v.strip():
            out.append(v.strip())
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, str):
                    out.append(item)
                elif isinstance(item, dict):
                    out.extend(str(x) for x in item.values() if isinstance(x, str))
                    for b in item.get("bullets") or []:
                        out.append(str(b))
        elif isinstance(v, dict):
            out.extend(str(x) for x in v.values() if isinstance(x, (str, int, float)))
    return out


def assert_dispatch_gate(artifact: ResumeArtifact) -> None:
    if not artifact.dispatch_allowed:
        raise RuntimeError(
            f"Resume dispatch blocked: score={artifact.score.get('overall_score')} "
            f"(need >={GATE_THRESHOLD}) violations={artifact.fabrication_violations}"
        )
