"""
naukariPro Agent Subsystem: CandidateIntent Data Model
Module: naukari_pro.agent.intent
Governed by: 01_FACT_MATRIX.md & AGENTS.md
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import json
from typing import List, Optional, Dict, Any, Set, Union

# Canonical ground truth defaults per 01_FACT_MATRIX.md & AGENTS.md
DEFAULT_TARGET_ROLES: List[str] = [
    "MLOps Engineer",
    "ML Platform Engineer",
    "AI Infrastructure Engineer",
    "DevOps Engineer"
]

DEFAULT_TARGET_LOCATIONS: List[str] = [
    "Bengaluru",
    "Pune",
    "Hyderabad",
    "Remote"
]

SUPPORTED_PLATFORMS: Set[str] = {
    "naukri",
    "linkedin",
    "workday",
    "greenhouse",
    "lever",
    "ashby",
    "career_portals"
}

LOCATION_CANONICAL_MAP: Dict[str, str] = {
    "bangalore": "Bengaluru",
    "bengaluru": "Bengaluru",
    "pune": "Pune",
    "hyderabad": "Hyderabad",
    "gurgaon": "Gurugram",
    "gurugram": "Gurugram",
    "noida": "Noida",
    "mumbai": "Mumbai",
    "chennai": "Chennai",
    "remote": "Remote",
    "wfh": "Remote"
}


@dataclass
class CandidateIntent:
    """
    Structured, validated representation of candidate application intent.
    Encapsulates role targets, location preferences, compensation constraints,
    portal targets, and safety execution switches.
    """
    target_roles: List[str] = field(default_factory=lambda: list(DEFAULT_TARGET_ROLES))
    target_locations: List[str] = field(default_factory=lambda: list(DEFAULT_TARGET_LOCATIONS))
    min_salary_lpa: float = 20.0
    max_salary_lpa: Optional[float] = None
    min_experience_years: float = 2.0
    max_experience_years: float = 3.0
    work_authorization: str = "India"
    requires_sponsorship: bool = False
    platforms: List[str] = field(default_factory=lambda: ["naukri", "linkedin", "workday", "greenhouse", "lever"])
    max_applications: int = 15
    dry_run: bool = False
    strict_match_threshold: float = 70.0
    headless: bool = True
    raw_intent: str = ""
    ats_filters: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self):
        self.validate()

    def validate(self) -> None:
        """Validates all fields and normalizes values to canonical representations."""
        # 1. Normalize and validate target_roles
        if isinstance(self.target_roles, str):
            parsed_roles = [r.strip() for r in self.target_roles.split(",") if r.strip()]
            self.target_roles = parsed_roles if parsed_roles else list(DEFAULT_TARGET_ROLES)
        elif not self.target_roles:
            self.target_roles = list(DEFAULT_TARGET_ROLES)
        else:
            self.target_roles = [str(r).strip() for r in self.target_roles if str(r).strip()]
            if not self.target_roles:
                self.target_roles = list(DEFAULT_TARGET_ROLES)

        # 2. Normalize and validate target_locations
        if isinstance(self.target_locations, str):
            parsed_locs = [loc.strip() for loc in self.target_locations.split(",") if loc.strip()]
            raw_locs = parsed_locs if parsed_locs else list(DEFAULT_TARGET_LOCATIONS)
        elif not self.target_locations:
            raw_locs = list(DEFAULT_TARGET_LOCATIONS)
        else:
            raw_locs = [str(loc).strip() for loc in self.target_locations if str(loc).strip()]
            if not raw_locs:
                raw_locs = list(DEFAULT_TARGET_LOCATIONS)

        normalized_locs = []
        for loc in raw_locs:
            canon = LOCATION_CANONICAL_MAP.get(loc.lower(), loc)
            if canon not in normalized_locs:
                normalized_locs.append(canon)
        self.target_locations = normalized_locs

        # 3. Validate salary expectations
        try:
            self.min_salary_lpa = float(self.min_salary_lpa)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid min_salary_lpa: {self.min_salary_lpa}")

        if self.min_salary_lpa < 0.0:
            raise ValueError(f"min_salary_lpa cannot be negative: {self.min_salary_lpa}")

        if self.max_salary_lpa is not None:
            try:
                self.max_salary_lpa = float(self.max_salary_lpa)
            except (ValueError, TypeError):
                raise ValueError(f"Invalid max_salary_lpa: {self.max_salary_lpa}")

            if self.max_salary_lpa < self.min_salary_lpa:
                raise ValueError(
                    f"max_salary_lpa ({self.max_salary_lpa}) cannot be less than min_salary_lpa ({self.min_salary_lpa})"
                )

        # 4. Validate experience bounds
        try:
            self.min_experience_years = float(self.min_experience_years)
            self.max_experience_years = float(self.max_experience_years)
        except (ValueError, TypeError):
            raise ValueError("Experience bounds must be numeric values")

        if self.min_experience_years < 0.0 or self.max_experience_years < 0.0:
            raise ValueError("Experience bounds cannot be negative")
        if self.max_experience_years < self.min_experience_years:
            raise ValueError("max_experience_years cannot be less than min_experience_years")

        # 5. Normalize and validate platforms
        if isinstance(self.platforms, str):
            raw_plats = [p.strip().lower() for p in self.platforms.split(",") if p.strip()]
            if not raw_plats:
                raw_plats = ["naukri", "linkedin", "workday", "greenhouse", "lever"]
        elif not self.platforms:
            raw_plats = ["naukri", "linkedin", "workday", "greenhouse", "lever"]
        else:
            raw_plats = [str(p).strip().lower() for p in self.platforms if str(p).strip()]
            if not raw_plats:
                raw_plats = ["naukri", "linkedin", "workday", "greenhouse", "lever"]

        normalized_plats = []
        for p in raw_plats:
            if p not in SUPPORTED_PLATFORMS:
                raise ValueError(
                    f"Unsupported platform '{p}'. Supported platforms: {sorted(list(SUPPORTED_PLATFORMS))}"
                )
            if p not in normalized_plats:
                normalized_plats.append(p)
        self.platforms = normalized_plats

        # 6. Validate application limits
        try:
            self.max_applications = int(self.max_applications)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid max_applications: {self.max_applications}")

        if self.max_applications < 1:
            raise ValueError(f"max_applications must be at least 1 (got {self.max_applications})")
        if self.max_applications > 100:
            raise ValueError(f"max_applications exceeds safety limit of 100 (got {self.max_applications})")

        # 7. Validate strict match threshold
        try:
            self.strict_match_threshold = float(self.strict_match_threshold)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid strict_match_threshold: {self.strict_match_threshold}")

        if not (0.0 <= self.strict_match_threshold <= 100.0):
            raise ValueError(
                f"strict_match_threshold must be between 0.0 and 100.0 (got {self.strict_match_threshold})"
            )

        # 8. Type casts
        self.dry_run = bool(self.dry_run)
        self.headless = bool(self.headless)
        self.requires_sponsorship = bool(self.requires_sponsorship)
        self.work_authorization = str(self.work_authorization).strip() or "India"

    # Compatibility Aliases for ApplicationIntent interoperability
    @property
    def roles(self) -> List[str]:
        return self.target_roles

    @property
    def locations(self) -> List[str]:
        return self.target_locations

    @property
    def limit(self) -> int:
        return self.max_applications

    @property
    def min_match_score(self) -> float:
        return self.strict_match_threshold

    def to_dict(self) -> Dict[str, Any]:
        """Exports intent to serializable dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CandidateIntent":
        """Instantiates CandidateIntent from dictionary, resolving aliases."""
        clean: Dict[str, Any] = {}
        alias_map = {
            "roles": "target_roles",
            "locations": "target_locations",
            "limit": "max_applications",
            "min_match_score": "strict_match_threshold",
            "min_score": "strict_match_threshold",
            "threshold": "strict_match_threshold",
            "min_salary": "min_salary_lpa",
            "max_salary": "max_salary_lpa",
            "query": "raw_intent",
            "intent": "raw_intent",
            "work_auth": "work_authorization"
        }
        for k, v in data.items():
            target_key = alias_map.get(k, k)
            if target_key in cls.__dataclass_fields__:
                clean[target_key] = v
        return cls(**clean)

    def to_json(self, indent: int = 2) -> str:
        """Serializes intent to formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> "CandidateIntent":
        """Deserializes JSON string into validated CandidateIntent."""
        data = json.loads(json_str)
        return cls.from_dict(data)
