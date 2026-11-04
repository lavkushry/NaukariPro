"""Workstream 5 — governed auto-apply (HITL, sensitivity, dry-run audit)."""

from naukari_pro.governed_apply.sensitivity import Sensitivity, classify_question
from naukari_pro.governed_apply.approval import ApprovalQueue
from naukari_pro.governed_apply.pipeline import GovernedApplyPipeline

__all__ = [
    "Sensitivity",
    "classify_question",
    "ApprovalQueue",
    "GovernedApplyPipeline",
]
