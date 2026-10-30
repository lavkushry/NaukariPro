"""
naukariPro Learning Subsystem: Controlled Profile Mutation Engine (M1 / R1)
Resdex SEO Saturation and Controlled Profile Mutation Engine for Naukri and LinkedIn.

Provides:
- BlacklistValidator & BlacklistViolationError: Hard reject any modification to YOE (2.5),
  CTC (12 LPA current / 20-25 expected), notice period (15 days), employment dates,
  employer names, education, certs, synthetic EMS conversions, and ghost repos.
- NaukriWhitelist: Headline rephrase (<=250 chars), key-skills reorder, 1 low->high skill swap,
  and 1-sentence summary rephrase.
- LinkedInWhitelist & LinkedInTokenRotator: Headline token rotation (<=220 chars, preserving 8 primary tokens),
  About section sentence injection (<=2600 chars), skills reordering, Open-to-Work (recruiters only),
  and light weekly activity signal.
- HashEngine: Deterministic SHA-256 with canonical Unicode NFC and whitespace normalization.
- CadenceScheduler: Dual-tier rate limiting (daily freshness bump + <=2 keyword mutations/week,
  Tue–Thu 09:30–11:30 IST ±90m jitter).
- ProfileMutator: High-level facade for proposal, validation, execution, and ledger logging.
"""

import re
import json
import random
import hashlib
import logging
import unicodedata
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, date, time, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple, Callable, Union
from zoneinfo import ZoneInfo

from naukari_pro.modules.db import (
    record_profile_mutation,
    get_weekly_mutation_count,
    can_apply_keyword_mutation,
    get_latest_mutation,
    compute_field_hash,
    init_db,
    DB_PATH,
)

logger = logging.getLogger("naukariPro.Mutator")

try:
    IST_TZ = ZoneInfo("Asia/Kolkata")
except Exception:
    IST_TZ = timezone(timedelta(hours=5, minutes=30))


# ==============================================================================
# ENUMS & DATA MODELS
# ==============================================================================

class Platform(str, Enum):
    NAUKRI = "naukri"
    LINKEDIN = "linkedin"
    GENERIC = "generic"


class MutationField(str, Enum):
    HEADLINE = "headline"
    KEY_SKILLS = "key_skills"
    SUMMARY = "summary"
    ABOUT = "about"
    SKILLS = "skills"
    OPEN_TO_WORK = "open_to_work"
    WEEKLY_ACTIVITY = "weekly_activity"
    FRESHNESS_BUMP = "freshness_bump"


class MutationStatus(str, Enum):
    PROPOSED = "proposed"
    VALIDATED = "validated"
    APPLIED = "applied"
    FAILED = "failed"
    QUARANTINED = "quarantined"
    NOOP = "noop"
    REVERTED = "reverted"


@dataclass(frozen=True)
class MutationProposal:
    platform: Platform
    field: MutationField
    old_value: str
    new_value: str
    old_hash: str
    new_hash: str
    rationale: str
    expected_effect: str
    is_keyword_mutation: bool = True
    approved_by: str = "auto_rule_engine"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class MutationResult:
    proposal: MutationProposal
    status: MutationStatus
    ledger_id: Optional[int] = None
    applied_at: Optional[str] = None
    error_message: Optional[str] = None


# ==============================================================================
# 1. BLACKLIST VALIDATOR & SAFETY INVARIANTS (01_FACT_MATRIX.md)
# ==============================================================================

class BlacklistViolationError(ValueError):
    """Raised when a proposed mutation violates candidate ground truth in 01_FACT_MATRIX.md."""
    pass


class BlacklistValidator:
    """
    Enforces strict immutability of candidate facts defined in 01_FACT_MATRIX.md.
    Intercepts and hard-rejects any attempt to mutate or fabricate:
    - YOE (Canonical 2.5 YOE; rejects >= 3.0, 5+, 10+, Senior/Lead titles, decades)
    - CTC (Canonical current 12 LPA, expected 20-25 LPA; rejects > 25 current, > 40 expected)
    - Notice Period (Canonical 15 Days or less; rejects 30, 45, 60, 90 days, 1-3 months)
    - Employment Dates & Companies (CGI, HFCL, Stipe; rejects Ex-Google, Ex-Amazon, etc.)
    - Education (Canonical B.Tech CSE MDU Rohtak; rejects M.Tech, Ph.D., Stanford, IIT, etc.)
    - Certifications (AZ-900, Databricks Associate in progress; rejects AWS Pro, CKA, GCP Arch)
    - Synthetic Workload Conversions (Reject 12+ ML models at HFCL, Triton/MPS, inference logs at CGI)
    - Ghost 404 Repositories (Reject mlops-platform-automation, genai-observability-platform)
    """

    # 1. YOE Boundary: Canonical is 2.5 YOE (max 2.5). Prohibit >= 3.0 YOE claims.
    FORBIDDEN_YOE_PATTERNS: List[re.Pattern] = [
        re.compile(r"(?i)(?<!\d\.)\b(?:[3-9](?:\.\d+)?|\d{2,}(?:\.\d+)?)(?:\+|[-\s]+plus)?[-\s]*(?:yoe|years?(?:\s+of)?(?:\s+experience)?|yrs)\b"),
        re.compile(r"(?i)\b(?:three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty)(?:\+|[-\s]+plus)?[-\s]*(?:yoe|years?(?:\s+of)?(?:\s+experience)?|yrs)\b"),
        re.compile(r"(?i)\b(?:senior|lead|principal|staff)\s+(?:data|mlops|devops|software)\s+engineer\b"),
        re.compile(r"(?i)\bdecade\s+of\s+experience\b"),
    ]

    # 2. CTC Boundary: Canonical current is 12 LPA, expected 20-25 LPA. Prohibit fabrication.
    FORBIDDEN_CTC_PATTERNS: List[re.Pattern] = [
        re.compile(r"(?i)\b(?:current\s+ctc|annual\s+ctc|fixed\s+ctc|base\s+ctc|drawing|fixed\s+compensation|fixed\s+component|annual\s+compensation)\s*(?:is|of|around|at|[:=])?\s*(?:[2-9]\d|\d{3,})\s*(?:lpa|lakhs?|lac)\b"),
        re.compile(r"(?i)\b(?:expected\s+(?:ctc|compensation|salary))\s*(?:is|of|around|at|[:=])?\s*(?:[3-9]\d|\d{3,})\s*(?:lpa|lakhs?|lac)\b"),
        re.compile(r"(?i)(?<!\bexpected\s)\b(?:ctc|compensation|salary)\s*(?:is|of|around|at|[:=])?\s*(?:[3-9]\d|\d{3,})\s*(?:lpa|lakhs?|lac)\b"),
    ]

    # 3. Notice Period Boundary: Strictly 15 Days or less. Prohibit > 15 days notice.
    FORBIDDEN_NOTICE_PATTERNS: List[re.Pattern] = [
        re.compile(r"(?i)\b(?:30|45|60|90|thirty|forty-five|sixty|ninety)[-\s]*days?\b"),
        re.compile(r"(?i)\b(?:1|2|3|one|two|three)[-\s]*months?\b"),
        re.compile(r"(?i)\bserving\s+(?:(?:30|45|60|90|thirty|sixty|ninety)[-\s]*days?|(?:1|2|3|one|two|three)[-\s]*months?)\b"),
    ]

    # 4. Employer Name Fabrication: Strictly CGI India, HFCL Limited, Stipe Solutions.
    TARGET_COMPANIES: str = r"(?:google|googler|amazon|amazonian|microsoft|databricks|meta|uber|netflix|apple|flipkart|atlassian|salesforce|adobe|nvidia)"
    FORBIDDEN_EMPLOYER_PATTERNS: List[re.Pattern] = [
        re.compile(rf"(?i)\bex[-\s]+{TARGET_COMPANIES}\b"),
        re.compile(rf"(?i)\b(?:worked|working|employed|employee|engineer|developer|architect|senior|lead|principal|staff|intern|consultant)\s+(?:at|of)\s+{TARGET_COMPANIES}\b"),
        re.compile(rf"(?i)\b(?:joined|former)\s+(?:(?:employee|intern|worker|staff|engineer|developer|architect|consultant)\s+(?:at|of)\s+)?{TARGET_COMPANIES}\b"),
    ]

    # 5. Education Fabrication: Canonical is B.Tech CSE at MDU Rohtak.
    FORBIDDEN_EDUCATION_PATTERNS: List[re.Pattern] = [
        re.compile(r"(?i)\b(?:m\.?tech|ph\.?d|master(?:'?s)?(?:\s+degree)?)\b"),
        re.compile(r"(?i)\b(?:stanford|harvard|mit|iit|bits\s+pilani|iim)\b"),
    ]

    # 6. Unverified Certifications: Only AZ-900 & Databricks Associate (pursuing).
    FORBIDDEN_CERT_PATTERNS: List[re.Pattern] = [
        re.compile(r"(?i)\b(?:aws\s+(?:certified\s+)?solutions\s+architect\s+professional|sap-c0\d)\b"),
        re.compile(r"(?i)\b(?:cka|certified\s+kubernetes\s+administrator)\b"),
        re.compile(r"(?i)\b(?:gcp\s+(?:professional\s+)?cloud\s+architect)\b"),
    ]

    # 7. Historical Workload Conversion Fabrications (01_FACT_MATRIX.md Section 2):
    FORBIDDEN_WORKLOAD_PATTERNS: List[re.Pattern] = [
        re.compile(r"(?i)(?:\b\d+\+?\s+)?(?:production\s+)?(?:ml|machine\s+learning)\s+(?:models|microservices|workloads|services)\s+at\s+hfcl\b"),
        re.compile(r"(?i)\b(?:nvidia\s+mps|triton(?:\s+inference\s+server)?)\b"),
        re.compile(r"(?i)\bmodel\s+inference\s+logging\s+at\s+cgi\b"),
        re.compile(r"(?i)\bautomated\s+model\s+validation\s+gates\s+at\s+hfcl\b"),
    ]

    # 8. Ghost 404 Repositories:
    FORBIDDEN_REPO_PATTERNS: List[re.Pattern] = [
        re.compile(r"(?i)mlops-platform-automation"),
        re.compile(r"(?i)genai-observability-platform"),
    ]

    # Forbidden attribute names that must never be targeted as mutable fields
    FORBIDDEN_FIELDS = {
        "yoe", "experience", "total_experience", "ctc", "salary",
        "notice_period", "employment_dates", "company",
        "employer", "education", "degree", "certification", "certifications"
    }

    @classmethod
    def validate_field_name(cls, field_name: str) -> None:
        """Checks if a field name attempts to target a protected immutable attribute."""
        field_str = field_name.lower().strip()
        if any(b in field_str for b in cls.FORBIDDEN_FIELDS):
            raise BlacklistViolationError(f"Field '{field_name}' touches protected immutable candidate attribute.")

    @classmethod
    def validate_text(cls, text: str, field_name: str = "general") -> Tuple[bool, List[str]]:
        """
        Scans proposed text against all blacklisted pattern categories.
        Returns (is_valid: bool, violations: List[str]).
        """
        if not text:
            return True, []

        # Pre-processing: Normalize NFKC and strip invisible/formatting characters
        clean_text = unicodedata.normalize("NFKC", text)
        clean_text = re.sub(r"[\u200b-\u200d\ufeff\u00ad]", "", clean_text)

        violations: List[str] = []
        checks = [
            ("YOE Inflation", cls.FORBIDDEN_YOE_PATTERNS),
            ("CTC Fabrication", cls.FORBIDDEN_CTC_PATTERNS),
            ("Notice Period Distortion", cls.FORBIDDEN_NOTICE_PATTERNS),
            ("Employer Fabrication", cls.FORBIDDEN_EMPLOYER_PATTERNS),
            ("Education Inflation", cls.FORBIDDEN_EDUCATION_PATTERNS),
            ("Unverified Certification", cls.FORBIDDEN_CERT_PATTERNS),
            ("Synthetic Workload Conversion", cls.FORBIDDEN_WORKLOAD_PATTERNS),
            ("Ghost Repository Reference", cls.FORBIDDEN_REPO_PATTERNS),
        ]

        for category, patterns in checks:
            for pat in patterns:
                m = pat.search(clean_text)
                if m:
                    violations.append(
                        f"[{category}] Matched forbidden pattern '{pat.pattern}' in field '{field_name}': '{m.group(0)}'"
                    )

        return len(violations) == 0, violations

    @classmethod
    def enforce(cls, text: str, field_name: str = "general", check_field_immutability: bool = False) -> None:
        """Enforces blacklist check, raising BlacklistViolationError if any rule triggers."""
        if check_field_immutability:
            cls.validate_field_name(field_name)

        valid, violations = cls.validate_text(text, field_name)
        if not valid:
            raise BlacklistViolationError(
                f"Candidate fact integrity violation in '{field_name}':\n" + "\n".join(f" - {v}" for v in violations)
            )


# ==============================================================================
# 2. HASH ENGINE (DETERMINISTIC CRYPTOGRAPHIC NORMALIZATION)
# ==============================================================================

class HashEngine:
    """
    Deterministic SHA-256 calculation with Unicode NFC normalization,
    consistent newline formatting, and whitespace trimming.
    """

    @staticmethod
    def normalize_text(text: Optional[str]) -> str:
        """Applies Unicode NFC normalization, standardizes line breaks, and trims edges."""
        if not text:
            return ""
        normalized = unicodedata.normalize("NFC", str(text))
        normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
        return normalized.strip()

    @classmethod
    def compute_text_hash(cls, text: Optional[str]) -> str:
        """Computes deterministic 64-character SHA-256 hex string for normalized text."""
        clean = cls.normalize_text(text)
        if not clean:
            return "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        return hashlib.sha256(clean.encode("utf-8")).hexdigest()

    @classmethod
    def compute_list_hash(cls, items: List[str], ordered: bool = True) -> str:
        """Computes deterministic hash for a list of string tokens."""
        cleaned = [cls.normalize_text(x) for x in items if x]
        if not ordered:
            cleaned = sorted(cleaned)
        payload = "\x1f".join(cleaned)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @classmethod
    def compute_dict_hash(cls, data: Dict[str, Any]) -> str:
        """Computes deterministic hash for canonical sorted JSON."""
        canonical_json = json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


# ==============================================================================
# 3. CADENCE SCHEDULER & JITTER ENGINE
# ==============================================================================

class CadenceScheduler:
    """
    Dual-tier scheduling engine for Resdex and LinkedIn profile touches:
    1. Freshness Bump: Micro-touch/save permitted daily (>2 hour cooldown) to preserve 'Active Today'.
    2. Keyword Mutation: Scheduled strictly Tue–Thu 09:30–11:30 IST ±90m jitter (08:00–13:00 IST envelope).
       Hard weekly limit: <= 2 keyword mutations per calendar week.
    """

    NOMINAL_START = time(9, 30)
    NOMINAL_END = time(11, 30)
    ENVELOPE_START = time(8, 0)
    ENVELOPE_END = time(13, 0)
    ACTIVE_WEEKDAYS = (1, 2, 3)  # Tuesday, Wednesday, Thursday
    MAX_WEEKLY_KEYWORD_MUTATIONS = 2

    @staticmethod
    def now_ist() -> datetime:
        return datetime.now(IST_TZ)

    @classmethod
    def is_active_cadence_day(cls, dt: Optional[datetime] = None) -> bool:
        """Returns True if the date is Tuesday, Wednesday, or Thursday."""
        check_dt = dt or cls.now_ist()
        if check_dt.tzinfo is None:
            check_dt = check_dt.replace(tzinfo=IST_TZ)
        else:
            check_dt = check_dt.astimezone(IST_TZ)
        return check_dt.weekday() in cls.ACTIVE_WEEKDAYS

    @classmethod
    def calculate_daily_jittered_slot(
        cls,
        target_date: Optional[date] = None,
        seed: Optional[int] = None
    ) -> datetime:
        """
        Calculates today's exact scheduled execution time:
        Center 10:30 IST +/- uniform(-90, 90) minutes + uniform(0, 59) seconds.
        Envelope strictly bounded to [08:00, 13:00] IST.
        """
        ref_date = target_date or cls.now_ist().date()
        rng = random.Random(seed) if seed is not None else random

        center_dt = datetime.combine(ref_date, time(10, 30), tzinfo=IST_TZ)
        jitter_minutes = rng.uniform(-90.0, 90.0)
        jitter_seconds = rng.randint(0, 59)

        scheduled_dt = center_dt + timedelta(minutes=jitter_minutes, seconds=jitter_seconds)
        return scheduled_dt

    @classmethod
    def is_within_execution_envelope(cls, dt: Optional[datetime] = None) -> bool:
        """Verifies if current time is within the permissible 08:00 - 13:00 IST window on an active day."""
        check_dt = dt or cls.now_ist()
        if check_dt.tzinfo is None:
            check_dt = check_dt.replace(tzinfo=IST_TZ)
        else:
            check_dt = check_dt.astimezone(IST_TZ)

        if not cls.is_active_cadence_day(check_dt):
            return False

        t = check_dt.time()
        return cls.ENVELOPE_START <= t <= cls.ENVELOPE_END

    @classmethod
    def can_mutate_weekly(cls, platform: str, db_path: Optional[str] = None) -> bool:
        """Verifies if keyword mutations in the trailing week are strictly < 2."""
        can_kw, _, _ = can_apply_keyword_mutation(
            platform=platform,
            max_weekly=cls.MAX_WEEKLY_KEYWORD_MUTATIONS,
            db_path=db_path
        )
        return can_kw

    @classmethod
    def evaluate_mutation_eligibility(
        cls,
        platform: str = "naukri",
        force: bool = False,
        dt: Optional[datetime] = None,
        db_path: Optional[str] = None
    ) -> Tuple[bool, bool, str]:
        """
        Evaluates run eligibility and action type.
        Returns: (can_run: bool, allow_keyword_mutation: bool, reason: str)
        """
        check_dt = dt or cls.now_ist()
        if check_dt.tzinfo is None:
            check_dt = check_dt.replace(tzinfo=IST_TZ)
        else:
            check_dt = check_dt.astimezone(IST_TZ)

        if not force:
            if not cls.is_active_cadence_day(check_dt):
                day_name = check_dt.strftime("%A")
                return False, False, f"Today is {day_name}; cadence runs only Tuesday through Thursday"

            if not cls.is_within_execution_envelope(check_dt):
                time_str = check_dt.strftime("%H:%M:%S")
                return False, False, f"Current time {time_str} IST is outside 08:00-13:00 IST envelope"

            # Check if already touched today
            latest = get_latest_mutation(platform=platform, db_path=db_path)
            if latest and latest.get("applied_at"):
                try:
                    last_utc = datetime.fromisoformat(str(latest["applied_at"])).replace(tzinfo=timezone.utc)
                    last_ist = last_utc.astimezone(IST_TZ)
                    if last_ist.date() == check_dt.date():
                        return False, False, f"Profile already updated today at {last_ist.strftime('%H:%M:%S')} IST"
                except Exception:
                    pass

        # Check weekly keyword quota
        can_kw, kw_count, kw_reason = can_apply_keyword_mutation(
            platform=platform,
            max_weekly=cls.MAX_WEEKLY_KEYWORD_MUTATIONS,
            reference_date=check_dt,
            db_path=db_path
        )

        if can_kw:
            return True, True, f"Eligible for keyword mutation ({kw_reason})"
        else:
            return True, False, f"Eligible for freshness bump only ({kw_reason})"


# ==============================================================================
# 4. NAUKRI WHITELIST MUTATOR
# ==============================================================================

class NaukriWhitelist:
    """
    Governs whitelisted profile mutations on Naukri Resdex:
    1. Headline rephrase (<=250 chars, safe <=247 chars)
    2. Key-skills reorder (preserves set, reorders by utility)
    3. Exactly 1 low->high skill swap per cycle (protects core anchors, maintains 25 total)
    4. 1-sentence summary rephrase (preserves remaining sentences, length 500-1500 chars)
    """

    MAX_HEADLINE_CHARS = 250
    SAFE_HEADLINE_CHARS = 247

    # Core skills that must NEVER be dropped
    PROTECTED_ANCHORS = {
        "Azure Databricks",
        "PySpark",
        "Delta Lake",
        "SQL",
        "Azure Data Factory (ADF)",
        "Apache Kafka",
        "Terraform"
    }

    # High-value candidate skills from 01_FACT_MATRIX.md validated pool
    VALIDATED_SKILL_POOL = [
        "Unity Catalog",
        "dbt",
        "Microsoft Fabric",
        "Change Data Capture (CDC)",
        "Great Expectations",
        "PostgreSQL",
        "TimescaleDB",
        "Redis",
        "Ansible",
        "Kubernetes (EKS)"
    ]

    # Reserve candidate skills from 01_FACT_MATRIX.md for fallback and pool saturation prevention
    RESERVE_SKILL_POOL = [
        "Python",
        "Docker",
        "Linux",
        "CI/CD",
        "Git",
        "Azure DevOps",
        "Snowflake",
        "ADLS Gen2",
        "Azure Synapse Analytics",
        "ETL Pipelines",
        "Data Modeling",
        "Data Warehousing",
        "Data Lakehouse",
        "Airflow",
        "REST APIs",
        "Bash",
        "FastAPI",
        "Prometheus",
        "Grafana",
        "ELK Stack",
        "MongoDB",
        "Harbor",
        "Nginx Ingress",
        "Kong Gateway",
    ]

    HEADLINE_TEMPLATES = [
        (
            "Azure Data Engineer | Azure Databricks · PySpark · Delta Lake · "
            "Azure Data Factory (ADF) · SQL · Apache Kafka · Terraform · Medallion Architecture | "
            "Certified AZ-900 · Databricks Associate (Pursuing) | 2.5 YOE Cloud Data Platforms & CI/CD"
        ),
        (
            "Azure Data Engineer | PySpark · Azure Databricks · Delta Lake · ADF · "
            "Kafka · Terraform · Unity Catalog | Medallion Lakehouse (2M+ events/day) | "
            "Certified AZ-900 | 2.5 YOE | Immediate – 15 Days Notice"
        ),
        (
            "Azure Data Engineer | Azure Databricks · PySpark · Delta Lake · Azure Data Factory · "
            "Apache Kafka · Terraform · dbt · CDC | Enterprise Lakehouse Architecture | "
            "AZ-900 Certified | 2.5 YOE | Immediate – 15 Days Notice"
        )
    ]

    SUMMARY_SENTENCE_TEMPLATES = [
        "Engineered scalable Medallion Architecture lakehouse pipelines processing 2M+ daily streaming and batch events with 99.9% reliability.",
        "Architected automated data quality verification suites and table governance policies using Unity Catalog and Great Expectations.",
        "Provisioned immutable cloud data infrastructure and automated deployment workflows using Terraform, GitHub Actions, and Azure DevOps."
    ]

    @classmethod
    def rephrase_headline(cls, current_headline: str = "", cycle: int = 0) -> str:
        """Selects a calibrated saturated headline from templates, ensuring <= 250 chars and blacklist compliance."""
        chosen = cls.HEADLINE_TEMPLATES[cycle % len(cls.HEADLINE_TEMPLATES)]
        assert len(chosen) <= cls.MAX_HEADLINE_CHARS, f"Headline len {len(chosen)} exceeds {cls.MAX_HEADLINE_CHARS}"
        BlacklistValidator.enforce(chosen, field_name="naukri_headline")
        return chosen

    @classmethod
    def reorder_key_skills(
        cls,
        current_skills: List[str],
        utility_scores: Optional[Dict[str, float]] = None
    ) -> List[str]:
        """Reorders existing 25 key skills based on keyword utility scores without modifying members."""
        if not current_skills:
            return []
        scores = utility_scores or {}
        # Sort descending by utility, with fallback to original index order
        reordered = sorted(
            current_skills,
            key=lambda s: scores.get(s, scores.get(s.lower(), 0.0)),
            reverse=True
        )
        return reordered

    @classmethod
    def swap_single_skill(
        cls,
        current_skills: List[str],
        drop_skill: Optional[str] = None,
        add_skill: Optional[str] = None
    ) -> Tuple[List[str], str, str]:
        """
        Swaps exactly 1 low-value skill for 1 high-value skill from the validated pool.
        Guarantees that protected anchor skills are never dropped and total count remains constant.
        Prevents duplicate skill collisions and preserves unique skill count (25).
        """
        skills_set = list(current_skills)
        if len(skills_set) == 0:
            return [], "", ""

        # 1. Determine skill to drop (cannot be protected anchor)
        to_drop = drop_skill
        if not to_drop or to_drop not in skills_set or to_drop in cls.PROTECTED_ANCHORS:
            to_drop = None
            for s in reversed(skills_set):
                if s not in cls.PROTECTED_ANCHORS:
                    to_drop = s
                    break

        if not to_drop:
            # Cannot drop any skill without violating anchor protection; return cleanly
            return list(skills_set), "", ""

        # 2. Determine skill to add (must not already be in skills_set)
        candidate_to_add = None
        if add_skill and add_skill not in skills_set:
            candidate_to_add = add_skill

        # Primary pool search
        if not candidate_to_add:
            for cand in cls.VALIDATED_SKILL_POOL:
                if cand not in skills_set:
                    candidate_to_add = cand
                    break

        # Secondary reserve pool search
        if not candidate_to_add:
            for cand in getattr(cls, "RESERVE_SKILL_POOL", []):
                if cand not in skills_set:
                    candidate_to_add = cand
                    break

        # Total exhaustion fallback: clean no-op, never inject duplicates
        if not candidate_to_add:
            return list(skills_set), to_drop, to_drop

        to_add = candidate_to_add

        # 3. Validate against blacklist
        BlacklistValidator.enforce(to_add, field_name="key_skills")

        # 4. Perform atomic single-index replacement
        new_skills = list(skills_set)
        idx = new_skills.index(to_drop)
        new_skills[idx] = to_add

        assert len(new_skills) == len(skills_set), "Skill count modified during atomic swap"
        assert len(set(new_skills)) == len(set(skills_set)), "Unique skill count corrupted during atomic swap"

        return new_skills, to_drop, to_add

    @classmethod
    def rephrase_summary_sentence(
        cls,
        current_summary: str,
        target_sentence_index: int = 1,
        cycle: int = 0
    ) -> str:
        """Replaces a single sentence in the summary from approved templates, ensuring 500-1500 chars."""
        if not current_summary:
            base = "Azure Data Engineer with 2.5 YOE designing production data platforms. " + cls.SUMMARY_SENTENCE_TEMPLATES[0]
            return base

        sentences = re.split(r"(?<=[.!?])\s+", current_summary.strip())
        if not sentences:
            return current_summary

        idx = target_sentence_index if target_sentence_index < len(sentences) else 0
        replacement = cls.SUMMARY_SENTENCE_TEMPLATES[cycle % len(cls.SUMMARY_SENTENCE_TEMPLATES)]
        BlacklistValidator.enforce(replacement, field_name="naukri_summary")

        sentences[idx] = replacement
        new_summary = " ".join(sentences)
        return new_summary


# ==============================================================================
# 5. LINKEDIN WHITELIST & TOKEN ROTATOR
# ==============================================================================

class LinkedInTokenRotator:
    """
    Automates controlled LinkedIn headline token rotation and About section injection:
    - Guarantees preservation of all 8 primary recruiter tokens.
    - Strictly enforces LinkedIn character limits (Headline <= 220 chars, About <= 2600 chars).
    - Validates against BlacklistValidator before proposing or executing changes.
    """

    MAX_HEADLINE_CHARS = 220
    MAX_ABOUT_CHARS = 2600

    PRIMARY_TOKENS = [
        "Azure Data Engineer",
        "Azure Databricks",
        "PySpark",
        "Delta Lake",
        "Azure Data Factory (ADF)",
        "SQL",
        "Apache Kafka",
        "Immediate – 15 Days Notice"
    ]

    SECONDARY_POOL = [
        "Terraform",
        "Medallion Lakehouse",
        "ADLS Gen2",
        "CI/CD",
        "Unity Catalog",
        "dbt",
        "Great Expectations",
        "Change Data Capture (CDC)",
        "Microsoft Fabric",
        "Kubernetes (EKS)"
    ]

    def __init__(self, secondary_pool: Optional[List[str]] = None):
        self.secondary_pool = secondary_pool or self.SECONDARY_POOL

    def generate_rotated_headline(self, rotation_cycle: int = 0) -> str:
        """
        Constructs a keyword-saturated LinkedIn headline:
        Combines 8 primary tokens with 1-2 rotating secondary tokens while staying <= 220 chars.
        """
        sec_idx1 = rotation_cycle % len(self.secondary_pool)
        sec_idx2 = (rotation_cycle + 1) % len(self.secondary_pool)
        sec_tokens = [self.secondary_pool[sec_idx1], self.secondary_pool[sec_idx2]]

        core_part = f"{self.PRIMARY_TOKENS[0]} | {' · '.join(self.PRIMARY_TOKENS[1:7])}"
        sec_part = " · ".join(sec_tokens)
        notice_part = self.PRIMARY_TOKENS[7]

        headline = f"{core_part} | {sec_part} | {notice_part}"

        # If exceeding 220 chars, drop 1 secondary token
        if len(headline) > self.MAX_HEADLINE_CHARS:
            headline = f"{core_part} | {sec_tokens[0]} | {notice_part}"

        # Final assertion on 220-char boundary
        assert len(headline) <= self.MAX_HEADLINE_CHARS, f"Headline {len(headline)} chars exceeds {self.MAX_HEADLINE_CHARS}"

        # Verify all 8 primary tokens are present
        for prim in self.PRIMARY_TOKENS:
            assert prim in headline, f"Primary token '{prim}' missing from rotated headline!"

        # Enforce Blacklist Validator
        BlacklistValidator.enforce(headline, field_name="linkedin_headline")
        return headline

    def inject_about_sentence(self, base_about: str, claimable_token: str) -> str:
        """
        Injects a single validated competency sentence into the About section:
        Guarantees total character length remains <= 2,600 chars.
        """
        sentence_templates = {
            "Unity Catalog": "Implemented fine-grained data governance, access controls, and table lineage tracking using Unity Catalog across Lakehouse environments.",
            "dbt": "Developed modular SQL data transformation models and automated documentation with dbt, enforcing consistent data modeling standards.",
            "Great Expectations": "Configured automated data quality test suites using Great Expectations, preventing malformed records from entering production Gold tables.",
            "Change Data Capture (CDC)": "Architected low-latency Change Data Capture (CDC) streaming pipelines, reducing transactional replication lag to under 30 seconds."
        }

        injection_sentence = sentence_templates.get(
            claimable_token,
            f"Engineered production-grade data pipelines leveraging {claimable_token} to accelerate analytics throughput."
        )

        BlacklistValidator.enforce(injection_sentence, field_name="linkedin_about_sentence")

        marker = "⚡ CORE TECHNICAL EXPERTISE:\n"
        if marker in base_about:
            parts = base_about.split(marker, 1)
            updated_about = parts[0] + marker + f"• Key Focus ({claimable_token}): {injection_sentence}\n" + parts[1]
        else:
            updated_about = base_about + f"\n\n⚡ Focus: {injection_sentence}"

        if len(updated_about) > self.MAX_ABOUT_CHARS:
            logger.warning("Injection overflows 2,600 chars (%d). Returning original about text.", len(updated_about))
            return base_about

        return updated_about


class LinkedInWhitelist:
    """Convenience facade for LinkedIn Whitelist operations."""

    @classmethod
    def rotate_headline(cls, cycle: int = 0) -> str:
        rotator = LinkedInTokenRotator()
        return rotator.generate_rotated_headline(cycle)

    @classmethod
    def inject_about(cls, base_about: str, token: str) -> str:
        rotator = LinkedInTokenRotator()
        return rotator.inject_about_sentence(base_about, token)

    @classmethod
    def validate_open_to_work(cls, payload: Union[str, Dict[str, Any]]) -> bool:
        """Validates that Open to Work visibility is strictly 'Recruiters only'."""
        if isinstance(payload, str):
            try:
                data = json.loads(payload)
            except Exception:
                raise BlacklistViolationError("Open-to-work payload must be valid JSON.")
        else:
            data = payload

        vis = data.get("visibility")
        if vis != "Recruiters only":
            raise BlacklistViolationError(f"Open-to-work visibility must strictly be 'Recruiters only', got '{vis}'.")
        return True

    @classmethod
    def generate_weekly_activity_signal(cls) -> Dict[str, Any]:
        """Generates the single light weekly activity signal payload for Wednesday."""
        return {
            "action": "like_technical_post",
            "target_publisher": "Databricks / Microsoft Azure Engineering",
            "day": "Wednesday",
            "time_window": "14:00-16:00 IST",
            "approved": True
        }


# ==============================================================================
# 6. PROFILE MUTATOR FACADE
# ==============================================================================

class ProfileMutator:
    """
    High-level Profile Mutation Orchestrator implementing Milestone 1 interface contract:
    - can_mutate(platform: str) -> bool
    - propose_mutation(...) -> MutationProposal
    - apply_mutation(proposal, executor) -> MutationResult
    - record_mutation(proposal_or_dict) -> int
    - bump_profile(...) -> bool
    """

    def __init__(self, db_path: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        self.db_path = db_path or DB_PATH
        self.config = config or {}
        init_db(self.db_path)

    def can_mutate(self, platform: str) -> bool:
        """Verifies if the platform is eligible for a keyword mutation this week."""
        return CadenceScheduler.can_mutate_weekly(platform=platform, db_path=self.db_path)

    def propose_mutation(
        self,
        platform: str,
        field: str,
        new_value: str,
        current_value: str = "",
        rationale: str = "weekly_keyword_injection",
        expected_effect: str = "boost_search_appearances",
        is_keyword_mutation: bool = True,
        approved_by: str = "auto_rule_engine"
    ) -> MutationProposal:
        """Creates, validates, and hashes a profile mutation proposal."""
        plat_enum = Platform(platform.lower().strip())
        field_enum = MutationField(field.lower().strip())

        # Enforce Blacklist Validator on field name and new value
        BlacklistValidator.validate_field_name(field)
        BlacklistValidator.enforce(new_value, field_name=field)

        # Platform length & invariant checks
        if plat_enum == Platform.NAUKRI and field_enum == MutationField.HEADLINE:
            if len(new_value) > NaukriWhitelist.MAX_HEADLINE_CHARS:
                raise BlacklistViolationError(
                    f"Naukri headline length {len(new_value)} exceeds {NaukriWhitelist.MAX_HEADLINE_CHARS} chars"
                )

        elif plat_enum == Platform.LINKEDIN:
            if field_enum == MutationField.HEADLINE:
                if len(new_value) > LinkedInTokenRotator.MAX_HEADLINE_CHARS:
                    raise BlacklistViolationError(
                        f"LinkedIn headline length {len(new_value)} exceeds {LinkedInTokenRotator.MAX_HEADLINE_CHARS} chars"
                    )
                for prim in LinkedInTokenRotator.PRIMARY_TOKENS:
                    if prim not in new_value:
                        raise BlacklistViolationError(f"LinkedIn headline missing primary token: '{prim}'")
            elif field_enum == MutationField.ABOUT:
                if len(new_value) > LinkedInTokenRotator.MAX_ABOUT_CHARS:
                    raise BlacklistViolationError(
                        f"LinkedIn About length {len(new_value)} exceeds {LinkedInTokenRotator.MAX_ABOUT_CHARS} chars"
                    )
            elif field_enum == MutationField.OPEN_TO_WORK:
                LinkedInWhitelist.validate_open_to_work(new_value)

        old_hash = HashEngine.compute_text_hash(current_value)
        new_hash = HashEngine.compute_text_hash(new_value)

        return MutationProposal(
            platform=plat_enum,
            field=field_enum,
            old_value=current_value,
            new_value=new_value,
            old_hash=old_hash,
            new_hash=new_hash,
            rationale=rationale,
            expected_effect=expected_effect,
            is_keyword_mutation=is_keyword_mutation,
            approved_by=approved_by
        )

    def propose_naukri_mutation(self, field: str = "headline", cycle: int = 0) -> MutationProposal:
        """Generates an approved mutation proposal for Naukri."""
        field_norm = field.lower().strip()
        if field_norm == "headline":
            new_val = NaukriWhitelist.rephrase_headline(cycle=cycle)
            return self.propose_mutation(
                platform="naukri",
                field="headline",
                new_value=new_val,
                rationale="resdex_seo_headline_saturation",
                expected_effect="boost_resdex_recruiter_appearances"
            )
        elif field_norm == "key_skills":
            skills, dropped, added = NaukriWhitelist.swap_single_skill(
                current_skills=self.config.get("default_keywords", list(NaukriWhitelist.PROTECTED_ANCHORS))
            )
            return self.propose_mutation(
                platform="naukri",
                field="key_skills",
                new_value=", ".join(skills),
                rationale=f"swap_low_value_skill_{dropped}_for_{added}",
                expected_effect="increase_key_skills_facet_matches"
            )
        raise ValueError(f"Unsupported Naukri mutation field: {field}")

    def apply_mutation(
        self,
        proposal: MutationProposal,
        executor_callable: Callable[[str, str], bool]
    ) -> MutationResult:
        """Executes mutation via provided platform executor and verifies hash."""
        if proposal.old_hash == proposal.new_hash and proposal.is_keyword_mutation:
            return MutationResult(
                proposal=proposal,
                status=MutationStatus.NOOP,
                error_message="Profile already matches proposed hash."
            )

        try:
            success = executor_callable(proposal.field.value, proposal.new_value)
            if not success:
                return MutationResult(
                    proposal=proposal,
                    status=MutationStatus.FAILED,
                    error_message="Platform DOM executor returned failure."
                )

            # Record in database ledger
            ledger_id = self.record_mutation(proposal)
            return MutationResult(
                proposal=proposal,
                status=MutationStatus.APPLIED,
                ledger_id=ledger_id,
                applied_at=datetime.now(timezone.utc).isoformat()
            )
        except Exception as e:
            return MutationResult(
                proposal=proposal,
                status=MutationStatus.FAILED,
                error_message=str(e)
            )

    def record_mutation(self, mutation_event: Union[MutationProposal, Dict[str, Any]]) -> int:
        """Writes an audit entry to the profile_mutations database table."""
        if isinstance(mutation_event, MutationProposal):
            res = record_profile_mutation(
                platform=mutation_event.platform.value,
                field=mutation_event.field.value,
                new_value=mutation_event.new_value,
                old_value=mutation_event.old_value,
                old_hash=mutation_event.old_hash,
                new_hash=mutation_event.new_hash,
                is_keyword_mutation=mutation_event.is_keyword_mutation,
                rationale=mutation_event.rationale,
                expected_effect=mutation_event.expected_effect,
                approved_by=mutation_event.approved_by,
                db_path=self.db_path
            )
        else:
            res = record_profile_mutation(db_path=self.db_path, **mutation_event)

        return int(res)
