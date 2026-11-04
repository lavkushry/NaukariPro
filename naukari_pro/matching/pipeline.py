"""End-to-end matching: Stage A → B → C → optional D → bandit context."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from naukari_pro.matching.stage_a import StageAFilter, StageAResult
from naukari_pro.matching.stage_b import structure_jd
from naukari_pro.matching.stage_c import score_fit_deterministic, score_fit_llm, to_bandit_context
from naukari_pro.matching.stage_d import optional_rubric


@dataclass
class MatchDecision:
    job: Dict[str, Any]
    stage_a: StageAResult
    structured_jd: Optional[Dict[str, Any]] = None
    stage_c: Optional[Dict[str, Any]] = None
    stage_d: Optional[Dict[str, Any]] = None
    bandit_job: Optional[Dict[str, Any]] = None
    final_decision: str = "SKIP"
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "company": self.job.get("company"),
            "title": self.job.get("title"),
            "url": self.job.get("url"),
            "stage_a_passed": self.stage_a.passed,
            "stage_a_reasons": self.stage_a.reasons,
            "structured_jd": self.structured_jd,
            "stage_c": self.stage_c,
            "stage_d": self.stage_d,
            "final_decision": self.final_decision,
            "errors": self.errors,
        }


class MatchingPipeline:
    def __init__(
        self,
        candidate_facts: Dict[str, Any],
        *,
        stage_a: Optional[StageAFilter] = None,
        use_llm: bool = False,
        gateway: Optional[Any] = None,
    ) -> None:
        self.candidate_facts = candidate_facts
        self.stage_a = stage_a or StageAFilter()
        self.use_llm = use_llm
        self.gateway = gateway

    def evaluate(self, job: Dict[str, Any]) -> MatchDecision:
        a = self.stage_a.evaluate(job)
        decision = MatchDecision(job=job, stage_a=a)
        if not a.passed:
            decision.final_decision = "SKIP"
            decision.stage_c = {
                "fit_score": 0,
                "coverage_pct": 0,
                "decision": "SKIP",
                "rationale": "Failed Stage A: " + ",".join(a.reasons),
                "must_have_coverage": {"direct": [], "transferable": [], "missing": []},
                "scorer": "stage_a",
            }
            return decision

        try:
            if self.use_llm:
                structured = structure_jd(
                    job,
                    gateway=self.gateway,
                    stage_a_hints={"seniority": a.seniority, "work_mode": a.work_mode},
                )
            else:
                structured = self._heuristic_structure(job, a)
            decision.structured_jd = structured
        except Exception as exc:  # noqa: BLE001
            decision.errors.append(f"stage_b:{exc}")
            structured = self._heuristic_structure(job, a)
            decision.structured_jd = structured

        try:
            # Merge job geo/title into structured for P2 location/role scoring
            structured_for_score = {
                **structured,
                "title": job.get("title") or structured.get("title"),
                "location": job.get("location") or structured.get("location"),
            }
            if self.use_llm:
                stage_c = score_fit_llm(
                    structured_for_score, self.candidate_facts, gateway=self.gateway
                )
            else:
                stage_c = score_fit_deterministic(
                    structured_for_score,
                    self.candidate_facts,
                    title_weight=a.title_weight,
                    job_title=str(job.get("title") or ""),
                    job_location=str(job.get("location") or ""),
                )
            decision.stage_c = stage_c
            decision.final_decision = (
                stage_c.get("recommendation") or stage_c.get("decision") or "REVIEW"
            )
        except Exception as exc:  # noqa: BLE001
            decision.errors.append(f"stage_c:{exc}")
            stage_c = score_fit_deterministic(
                structured,
                self.candidate_facts,
                title_weight=a.title_weight,
                job_title=str(job.get("title") or ""),
                job_location=str(job.get("location") or ""),
            )
            decision.stage_c = stage_c
            decision.final_decision = (
                stage_c.get("recommendation") or stage_c.get("decision") or "REVIEW"
            )

        decision.stage_d = optional_rubric(structured, stage_c, self.candidate_facts)
        decision.bandit_job = to_bandit_context(job, stage_c)
        return decision

    @staticmethod
    def _heuristic_structure(job: Dict[str, Any], a: StageAResult) -> Dict[str, Any]:
        """Offline / no-LLM P1 extract — truth-only; never invent must-haves from keywords."""
        from naukari_pro.matching.extract_p1 import extract_p1
        from naukari_pro.matching.stage_b import _normalize_p1

        structured = extract_p1(
            description=str(job.get("jd") or job.get("description_full") or ""),
            title=str(job.get("title") or ""),
            company=str(job.get("company") or ""),
            location=str(job.get("location") or ""),
        )
        structured = _normalize_p1(structured, job)
        # Stage A work_mode only fills when extract is unknown
        if structured.get("work_mode") == "unknown" and a.work_mode != "unknown":
            structured["work_mode"] = a.work_mode
        if structured.get("seniority") is None and a.seniority not in (None, "unknown"):
            legacy = {"junior": "entry", "mid": "mid", "senior": "senior", "staff": "staff"}
            structured["seniority"] = legacy.get(a.seniority)
        structured["_meta"] = {"scorer": "extract_p1", "cost_usd": 0.0}
        return structured
