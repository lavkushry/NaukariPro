"""Application funnel statuses and interview round types."""

from __future__ import annotations

from enum import Enum


class ApplicationStatus(str, Enum):
    SAVED = "saved"
    APPLIED = "applied"
    SCREENING = "screening"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    GHOSTED = "ghosted"


class InterviewRoundType(str, Enum):
    RECRUITER = "recruiter"
    HM = "hiring_manager"
    TECHNICAL = "technical"
    SYSTEM_DESIGN = "system_design"
    ONSITE = "onsite"
    OTHER = "other"
