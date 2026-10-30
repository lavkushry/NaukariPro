"""
naukariPro Learning Subsystem (Milestones 1, 3, 4)
Closed-Loop Self-Improving Job-Application ML System:
- mutator: Controlled profile mutation engine (M1 / R1)
- outcome_labeler: Telemetry and outcome labeling (M3 / R3)
- keyword_miner: TF-IDF and utility mining (M3 / R3)
- attribution: Difference-in-differences attribution (M3 / R3)
- policy: LinUCB contextual bandit selection policy (M4 / R4)
- digest: Monday digest reporting (M5 / R5)
"""

from naukari_pro.modules.learning.mutator import (
    BlacklistValidator,
    BlacklistViolationError,
    NaukriWhitelist,
    LinkedInWhitelist,
    LinkedInTokenRotator,
    HashEngine,
    CadenceScheduler,
    ProfileMutator,
    MutationProposal,
    MutationResult,
    MutationStatus,
    Platform,
    MutationField,
)

from naukari_pro.modules.learning.screening_solver import (
    ScreeningCategory,
    ScreeningInputType,
    ScreeningDecision,
    AmbiguousScreeningException,
    FactMatrixScreeningSolver,
)
from naukari_pro.modules.learning.evidence import (
    EvidenceVerifier,
    PNG_MAGIC_HEADER,
    MIN_SCREENSHOT_BYTES,
)

__all__ = [
    "BlacklistValidator",
    "BlacklistViolationError",
    "NaukriWhitelist",
    "LinkedInWhitelist",
    "LinkedInTokenRotator",
    "HashEngine",
    "CadenceScheduler",
    "ProfileMutator",
    "MutationProposal",
    "MutationResult",
    "MutationStatus",
    "Platform",
    "MutationField",
    "ScreeningCategory",
    "ScreeningInputType",
    "ScreeningDecision",
    "AmbiguousScreeningException",
    "FactMatrixScreeningSolver",
    "EvidenceVerifier",
    "PNG_MAGIC_HEADER",
    "MIN_SCREENSHOT_BYTES",
]

