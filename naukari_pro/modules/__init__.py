"""
naukari_pro.modules: Core automation, search, session, and application modules.
"""

from naukari_pro.modules.linkedin_session import (
    LinkedInSessionManager,
    LinkedInError,
    LinkedInSessionError,
    LinkedInCookieMissingError,
    LinkedInCookieExpiredError,
    LinkedInCheckpointError,
)

from naukari_pro.modules.linkedin_search import (
    TECH_HUBS,
    CANONICAL_LOCATIONS,
    LOCATION_ALIASES,
    DEFAULT_KEYWORDS,
    TARGET_KEYWORDS_TIER1,
    TARGET_KEYWORDS_TIER2,
    ALL_TARGET_KEYWORDS,
    LinkedInSearchUrlBuilder,
    JobDeduplicator,
    LinkedInJobDeduplicator,
    JobMatchScorer,
    PrecisionMatchScorer,
    MatchScoreResult,
    LinkedInJobCardParser,
    LinkedInSearchEngine,
    LinkedInSearchError,
    LinkedInInvalidLocationError,
)

from naukari_pro.modules.linkedin_apply import (
    LinkedInScreeningSolver,
    LinkedInEasyApplyNavigator,
    LinkedInApplicationTracker,
    LinkedInApplyEngine,
    LinkedInApplyError,
    LinkedInModalNotFoundError,
    LinkedInSubmissionFailedError,
    get_candidate_profile,
)

__all__ = [
    "LinkedInSessionManager",
    "LinkedInError",
    "LinkedInSessionError",
    "LinkedInCookieMissingError",
    "LinkedInCookieExpiredError",
    "LinkedInCheckpointError",
    "TECH_HUBS",
    "CANONICAL_LOCATIONS",
    "LOCATION_ALIASES",
    "DEFAULT_KEYWORDS",
    "TARGET_KEYWORDS_TIER1",
    "TARGET_KEYWORDS_TIER2",
    "ALL_TARGET_KEYWORDS",
    "LinkedInSearchUrlBuilder",
    "JobDeduplicator",
    "LinkedInJobDeduplicator",
    "JobMatchScorer",
    "PrecisionMatchScorer",
    "MatchScoreResult",
    "LinkedInJobCardParser",
    "LinkedInSearchEngine",
    "LinkedInSearchError",
    "LinkedInInvalidLocationError",
    "LinkedInScreeningSolver",
    "LinkedInEasyApplyNavigator",
    "LinkedInApplicationTracker",
    "LinkedInApplyEngine",
    "LinkedInApplyError",
    "LinkedInModalNotFoundError",
    "LinkedInSubmissionFailedError",
    "get_candidate_profile",
]
