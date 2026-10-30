"""
naukariPro Feature: LinkedIn Precision Job Search & Discovery Module
Milestone 2: High-Yield Precision Job Discovery Across 7 Tech Hubs & Remote

Provides:
- Exact geoId mapping for 7 Indian tech hubs + Remote
- Parameterized LinkedIn Job Search URL Builder
- Robust DOM Job Card Parser with progressive virtual-scroll hydration
- Two-tier atomic JSON & Excel Job Deduplicator
- Precision Multi-Component Match Scoring Engine (strict cutoff >= 70.0%)
- Unified LinkedInSearchEngine orchestrating discovery, parsing, deduplication, and gating
"""

import os
import re
import json
import time
import shutil
import inspect
import logging
import threading
import copy
import urllib.parse
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union, Tuple, Set

try:
    import fcntl
except ImportError:
    fcntl = None

logger = logging.getLogger("naukariPro.LinkedInSearch")

# Root Exception Hierarchy
try:
    from naukari_pro.modules.linkedin_session import LinkedInError
except ImportError:
    class LinkedInError(Exception):
        """Fallback root exception if imported standalone."""
        pass


class LinkedInSearchError(LinkedInError):
    """Base exception for search URL construction, parsing, and scoring errors."""
    pass


class LinkedInInvalidLocationError(LinkedInSearchError):
    """Raised when an invalid or unsupported location identifier is provided in strict mode."""
    pass


# ==============================================================================
# GEOGRAPHIC ENTITY CONSTANTS & TECH HUB TAXONOMY
# ==============================================================================

# Exact dictionary specified in PROJECT.md interface contract
TECH_HUBS: Dict[str, str] = {
    "Bengaluru": "105214831",
    "Hyderabad": "105556953",
    "Pune": "103503673",
    "Gurugram": "104113038",
    "Noida": "100450919",
    "Mumbai": "106155005",
    "Chennai": "105822989",
    "Remote": "102713980",
}

# Canonical human-readable location strings for LinkedIn job search
CANONICAL_LOCATIONS: Dict[str, str] = {
    "Bengaluru": "Bengaluru, Karnataka, India",
    "Hyderabad": "Hyderabad, Telangana, India",
    "Pune": "Pune, Maharashtra, India",
    "Gurugram": "Gurugram, Haryana, India",
    "Noida": "Noida, Uttar Pradesh, India",
    "Mumbai": "Mumbai, Maharashtra, India",
    "Chennai": "Chennai, Tamil Nadu, India",
    "Remote": "India",
}

# Normalization map for fuzzy and case-insensitive user inputs
LOCATION_ALIASES: Dict[str, str] = {
    "bengaluru": "Bengaluru",
    "bangalore": "Bengaluru",
    "blr": "Bengaluru",
    "bengaluru, karnataka, india": "Bengaluru",
    "hyderabad": "Hyderabad",
    "hyd": "Hyderabad",
    "hyderabad, telangana, india": "Hyderabad",
    "pune": "Pune",
    "pun": "Pune",
    "pune, maharashtra, india": "Pune",
    "gurugram": "Gurugram",
    "gurgaon": "Gurugram",
    "ggn": "Gurugram",
    "gurugram, haryana, india": "Gurugram",
    "noida": "Noida",
    "noida, uttar pradesh, india": "Noida",
    "delhi ncr": "Noida",
    "mumbai": "Mumbai",
    "bombay": "Mumbai",
    "bom": "Mumbai",
    "mumbai, maharashtra, india": "Mumbai",
    "chennai": "Chennai",
    "madras": "Chennai",
    "maa": "Chennai",
    "chennai, tamil nadu, india": "Chennai",
    "remote": "Remote",
    "remote india": "Remote",
    "india remote": "Remote",
    "pan-india remote": "Remote",
    "pan-india": "Remote",
    "india": "Remote",
}

# ==============================================================================
# KEYWORD TAXONOMY FOR LAVKUSH KUMAR (Azure Data Engineer, 2.5 YOE)
# ==============================================================================

DEFAULT_KEYWORDS: List[str] = [
    "Azure Data Engineer",
    "Databricks",
    "PySpark",
    "Delta Lake",
    "Azure Data Factory",
    "ADF",
    "Medallion Architecture",
]

TARGET_KEYWORDS_TIER1: List[str] = [
    "Azure Data Engineer",
    "Azure Databricks",
    "PySpark",
    "Azure Data Factory",
]

TARGET_KEYWORDS_TIER2: List[str] = [
    "Delta Lake",
    "ADF",
    "Medallion Architecture",
    "Data Engineer",
]

TARGET_KEYWORDS_BOOLEAN: List[str] = [
    '"Azure Data Engineer" AND PySpark',
    '"Azure" AND "Databricks" AND "Data Factory"',
    '"PySpark" AND ("Delta Lake" OR "Databricks")',
    '"Data Engineer" AND ("ADF" OR "Azure Data Factory")',
]

ALL_TARGET_KEYWORDS: List[str] = (
    TARGET_KEYWORDS_TIER1 + TARGET_KEYWORDS_TIER2 + TARGET_KEYWORDS_BOOLEAN
)

FRESHNESS_MAP: Dict[str, str] = {
    "24h": "r86400",
    "past_24h": "r86400",
    "1d": "r86400",
    "day": "r86400",
    "past_day": "r86400",
    "7d": "r604800",
    "past_week": "r604800",
    "week": "r604800",
    "30d": "r2592000",
    "past_month": "r2592000",
    "month": "r2592000",
}


# ==============================================================================
# URL BUILDER CLASS IMPLEMENTATION
# ==============================================================================

class LinkedInSearchUrlBuilder:
    """
    Dedicated builder for parameterized LinkedIn Job Search URLs.
    Adheres strictly to LinkedIn web query conventions and RFC 3986 encoding.
    """

    BASE_URL: str = "https://www.linkedin.com/jobs/search/"

    @classmethod
    def resolve_location(
        cls,
        location: str,
        custom_geo_id: Optional[str] = None,
        strict: bool = False
    ) -> Tuple[str, Optional[str], bool]:
        """
        Resolves input location string to (canonical_location_string, geoId, is_remote).
        """
        cleaned = location.strip().lower()
        if cleaned in LOCATION_ALIASES:
            canonical_hub = LOCATION_ALIASES[cleaned]
            geo_id = custom_geo_id or TECH_HUBS[canonical_hub]
            loc_str = CANONICAL_LOCATIONS[canonical_hub]
            is_remote = (canonical_hub == "Remote")
            return loc_str, geo_id, is_remote

        # Direct match in TECH_HUBS
        for hub_key, gid in TECH_HUBS.items():
            if hub_key.lower() == cleaned:
                geo_id = custom_geo_id or gid
                loc_str = CANONICAL_LOCATIONS[hub_key]
                is_remote = (hub_key == "Remote")
                return loc_str, geo_id, is_remote

        if strict:
            raise LinkedInInvalidLocationError(
                f"Location '{location}' is not recognized among supported tech hubs: "
                f"{list(TECH_HUBS.keys())}"
            )

        # Fallback: Treat as custom freeform location
        return location.strip(), custom_geo_id, False

    @classmethod
    def format_freshness(cls, freshness: Optional[Union[int, str]]) -> Optional[str]:
        """
        Normalizes freshness input (int seconds, 'r86400', or semantic aliases) to 'r<seconds>' or None.
        """
        if freshness is None or freshness == 0 or freshness == "all" or freshness == "any":
            return None

        if isinstance(freshness, int):
            if freshness <= 0:
                return None
            return f"r{freshness}"

        if isinstance(freshness, str):
            f_clean = freshness.strip().lower()
            if f_clean in FRESHNESS_MAP:
                return FRESHNESS_MAP[f_clean]
            if f_clean.startswith("r") and f_clean[1:].isdigit():
                return f_clean
            if f_clean.isdigit():
                return f"r{f_clean}"

        return None

    @classmethod
    def build(
        cls,
        keyword: str,
        location: str = "Bengaluru",
        freshness_sec: Optional[Union[int, str]] = 86400,
        easy_apply_only: bool = True,
        experience_levels: Optional[str] = "2,3",
        workplace_types: Optional[str] = None,
        sort_by: str = "DD",
        start: int = 0,
        page: Optional[int] = None,
        geo_id: Optional[str] = None,
        include_remote_cf: bool = True,
        strict_location: bool = False,
    ) -> str:
        """
        Constructs a complete, deterministic LinkedIn search URL.
        """
        if not keyword or not str(keyword).strip():
            raise ValueError("Keyword parameter must be a non-empty string.")

        # Compute pagination offset
        if page is not None:
            if page < 1:
                raise ValueError("Page number must be >= 1.")
            offset = (page - 1) * 25
        else:
            if start < 0:
                raise ValueError("Pagination start offset must be >= 0.")
            offset = start

        loc_str, resolved_geo_id, is_remote = cls.resolve_location(
            location=location,
            custom_geo_id=geo_id,
            strict=strict_location,
        )

        params: Dict[str, str] = {}
        params["keywords"] = str(keyword).strip()
        params["location"] = loc_str

        if resolved_geo_id:
            params["geoId"] = resolved_geo_id

        if easy_apply_only:
            params["f_AL"] = "true"

        f_tpr = cls.format_freshness(freshness_sec)
        if f_tpr:
            params["f_TPR"] = f_tpr

        if experience_levels:
            params["f_E"] = str(experience_levels).strip()

        if is_remote:
            params["f_WT"] = workplace_types or "2"
            if include_remote_cf:
                params["f_CF"] = "f_WRA"
        elif workplace_types:
            params["f_WT"] = str(workplace_types).strip()

        if sort_by:
            params["sortBy"] = str(sort_by).strip()

        if offset > 0:
            params["start"] = str(offset)

        # Deterministic encoding with safe commas for filter clarity
        query_string = urllib.parse.urlencode(
            params,
            quote_via=urllib.parse.quote,
            safe=","
        )
        return f"{cls.BASE_URL}?{query_string}"

    @classmethod
    def parse(cls, url: str) -> Dict[str, Any]:
        """
        Reverse-parses a LinkedIn job search URL into constituent parameter dictionary.
        """
        parsed = urllib.parse.urlparse(url)
        qs = urllib.parse.parse_qs(parsed.query)
        result: Dict[str, Any] = {}
        for k, v in qs.items():
            result[k] = v[0] if len(v) == 1 else v
        return result

    @classmethod
    def generate_matrix(
        cls,
        keywords: Optional[List[str]] = None,
        locations: Optional[List[str]] = None,
        freshness_sec: Optional[Union[int, str]] = 86400,
        easy_apply_only: bool = True,
        tier: int = 1,
    ) -> List[Dict[str, str]]:
        """
        Generates a matrix of search target dictionaries.
        """
        if keywords is None:
            if tier == 1:
                kws = TARGET_KEYWORDS_TIER1
            elif tier == 2:
                kws = TARGET_KEYWORDS_TIER2
            else:
                kws = ALL_TARGET_KEYWORDS
        else:
            kws = keywords

        locs = locations or list(TECH_HUBS.keys())

        targets: List[Dict[str, str]] = []
        for kw in kws:
            for loc in locs:
                url = cls.build(
                    keyword=kw,
                    location=loc,
                    freshness_sec=freshness_sec,
                    easy_apply_only=easy_apply_only,
                )
                targets.append({
                    "keyword": kw,
                    "location": loc,
                    "url": url,
                })
        return targets


# ==============================================================================
# DEDUPLICATION ENGINE
# ==============================================================================

DEFAULT_APPLIED_FILE = "linkedin_system/applied_jobs.json"
DEFAULT_SEEN_FILE = "linkedin_system/seen_jobs.json"


class JobDeduplicator:
    """
    High-performance two-tier deduplication cache:
    1. In-memory Set[str] for O(1) membership checks.
    2. Atomic disk persistence in applied_jobs.json and seen_jobs.json.
    3. Bi-directional synchronization with Naukri_Live_Application_Tracker.xlsx.
    """

    def __init__(
        self,
        applied_file: str = DEFAULT_APPLIED_FILE,
        seen_file: str = DEFAULT_SEEN_FILE,
        tracker_path: Optional[str] = None
    ):
        self.applied_file = applied_file
        self.seen_file = seen_file
        self.tracker_path = tracker_path
        self._lock = threading.Lock()

        self._applied_ids: Set[str] = set()
        self._applied_records: Dict[str, Dict[str, Any]] = {}
        self._seen_ids: Set[str] = set()
        self._seen_records: Dict[str, Dict[str, Any]] = {}

        self.load_cache()

    def load_cache(self) -> None:
        """Loads applied and seen records from disk; auto-creates directories if missing."""
        applied_dir = os.path.dirname(os.path.abspath(self.applied_file))
        seen_dir = os.path.dirname(os.path.abspath(self.seen_file))
        if applied_dir:
            os.makedirs(applied_dir, exist_ok=True)
        if seen_dir:
            os.makedirs(seen_dir, exist_ok=True)

        with self._lock:
            # Load applied jobs
            if os.path.exists(self.applied_file):
                try:
                    with open(self.applied_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            self._applied_ids = {str(item).strip() for item in data}
                        elif isinstance(data, dict):
                            self._applied_ids = {str(item).strip() for item in data.get("applied_job_ids", [])}
                            self._applied_records = data.get("records", {})
                except Exception as e:
                    logger.warning("Error reading applied_jobs.json: %s", e)
                    corrupt_path = f"{self.applied_file}.corrupt.{int(time.time())}"
                    try:
                        shutil.copy2(self.applied_file, corrupt_path)
                        logger.warning("Quarantined corrupted applied cache to %s", corrupt_path)
                    except Exception as ce:
                        logger.error("Failed to quarantine %s: %s", self.applied_file, ce)
                    self._applied_ids = set()
                    self._applied_records = {}

            # Load seen jobs
            if os.path.exists(self.seen_file):
                try:
                    with open(self.seen_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            self._seen_ids = {str(item).strip() for item in data}
                        elif isinstance(data, dict):
                            self._seen_ids = {str(item).strip() for item in data.get("seen_job_ids", [])}
                            self._seen_records = data.get("records", {})
                except Exception as e:
                    logger.warning("Error reading seen_jobs.json: %s", e)
                    corrupt_path = f"{self.seen_file}.corrupt.{int(time.time())}"
                    try:
                        shutil.copy2(self.seen_file, corrupt_path)
                        logger.warning("Quarantined corrupted seen cache to %s", corrupt_path)
                    except Exception as ce:
                        logger.error("Failed to quarantine %s: %s", self.seen_file, ce)
                    self._seen_ids = set()
                    self._seen_records = {}

    def is_applied(self, job_id: str) -> bool:
        """Returns True if job_id was already applied to in this or any prior run."""
        clean_id = str(job_id).strip()
        with self._lock:
            return clean_id in self._applied_ids

    def is_seen(self, job_id: str) -> bool:
        """Returns True if job_id was already evaluated during search harvesting."""
        clean_id = str(job_id).strip()
        with self._lock:
            return clean_id in self._seen_ids or clean_id in self._applied_ids

    def mark_applied(self, job_id: str, job_info: Optional[Dict[str, Any]] = None) -> None:
        """Records an authentic application into in-memory set and flushes atomically to disk."""
        clean_id = str(job_id).strip()
        with self._lock:
            self._applied_ids.add(clean_id)
            info = dict(job_info or {})
            info["applied_at"] = datetime.now(timezone.utc).isoformat()
            self._applied_records[clean_id] = info
            data_to_save = {
                "applied_job_ids": sorted(list(self._applied_ids)),
                "records": copy.deepcopy(self._applied_records),
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
        self._atomic_save(self.applied_file, data_to_save)

    def mark_seen(self, job_id: str, job_info: Optional[Dict[str, Any]] = None, status: str = "EVALUATED") -> None:
        """Records a job as seen/evaluated with its status (e.g. SKIPPED_LOW_MATCH)."""
        clean_id = str(job_id).strip()
        with self._lock:
            self._seen_ids.add(clean_id)
            info = dict(job_info or {})
            info["status"] = status
            info["seen_at"] = datetime.now(timezone.utc).isoformat()
            self._seen_records[clean_id] = info
            data_to_save = {
                "seen_job_ids": sorted(list(self._seen_ids)),
                "records": copy.deepcopy(self._seen_records),
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
        self._atomic_save(self.seen_file, data_to_save)

    def get_unseen(self, job_ids: List[str]) -> List[str]:
        """Returns subset of job_ids that are not yet seen or applied."""
        return [str(jid).strip() for jid in job_ids if not self.is_seen(str(jid).strip())]

    def filter_unapplied_jobs(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filters a list of parsed job dictionaries, removing already-applied roles."""
        unapplied = []
        for j in jobs:
            jid = j.get("job_id")
            if not jid:
                continue
            if not self.is_applied(str(jid)):
                unapplied.append(j)
        return unapplied

    def sync_from_excel_tracker(self, tracker_path: Optional[str] = None) -> int:
        """
        Scans Naukri_Live_Application_Tracker.xlsx under LinkedIn_Applications_Log
        and Applications_Log to backfill any applied job IDs missing from JSON cache.
        """
        path = tracker_path or self.tracker_path or "Naukri_Live_Application_Tracker.xlsx"
        if not os.path.exists(path):
            return 0
        try:
            import openpyxl
            wb = openpyxl.load_workbook(path, read_only=True)
            added_count = 0
            for sheetname in ["LinkedIn_Applications_Log", "Applications_Log"]:
                if sheetname in wb.sheetnames:
                    ws = wb[sheetname]
                    for row in ws.iter_rows(values_only=True):
                        for cell in row:
                            if cell and isinstance(cell, str) and "linkedin.com/jobs/view/" in cell:
                                match = re.search(r"/jobs/view/(\d+)", cell)
                                if match:
                                    jid = match.group(1)
                                    if jid not in self._applied_ids:
                                        self._applied_ids.add(jid)
                                        added_count += 1
            if added_count > 0:
                self._atomic_save(self.applied_file, {
                    "applied_job_ids": sorted(list(self._applied_ids)),
                    "records": self._applied_records,
                    "last_updated": datetime.now(timezone.utc).isoformat()
                })
            return added_count
        except Exception as e:
            logger.warning("Error syncing deduplicator from Excel: %s", e)
            return 0

    def prune_seen_jobs(self, retention_days: int = 30) -> int:
        """Prunes seen jobs older than retention_days to keep JSON files compact."""
        cutoff = datetime.now(timezone.utc).timestamp() - (retention_days * 86400)
        pruned_count = 0
        new_records = {}
        new_ids = set()
        for jid, rec in self._seen_records.items():
            seen_at_str = rec.get("seen_at", "")
            try:
                dt = datetime.fromisoformat(seen_at_str)
                if dt.timestamp() >= cutoff:
                    new_records[jid] = rec
                    new_ids.add(jid)
                else:
                    pruned_count += 1
            except Exception:
                new_records[jid] = rec
                new_ids.add(jid)
        if pruned_count > 0:
            with self._lock:
                self._seen_records = new_records
                self._seen_ids = new_ids
                data_to_save = {
                    "seen_job_ids": sorted(list(self._seen_ids)),
                    "records": copy.deepcopy(self._seen_records),
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }
            self._atomic_save(self.seen_file, data_to_save)
        return pruned_count

    def _atomic_save(self, file_path: str, data: Dict[str, Any]) -> None:
        """Writes to a unique temporary file and atomically renames to target file with file locking."""
        dir_name = os.path.dirname(os.path.abspath(file_path))
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        lock_path = f"{file_path}.lock"
        tmp_path = f"{file_path}.tmp.{os.getpid()}.{threading.get_ident()}.{time.time_ns()}"

        lock_fd = None
        try:
            if fcntl is not None:
                lock_fd = open(lock_path, "w")
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)

            # Merge any concurrent on-disk updates before writing
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as existing_f:
                        disk_data = json.load(existing_f)
                        if isinstance(disk_data, dict):
                            if "applied_job_ids" in data:
                                disk_ids = set(str(x).strip() for x in disk_data.get("applied_job_ids", []))
                                merged_ids = disk_ids.union(data["applied_job_ids"])
                                disk_records = disk_data.get("records", {})
                                merged_records = dict(disk_records)
                                merged_records.update(data.get("records", {}))
                                data["applied_job_ids"] = sorted(list(merged_ids))
                                data["records"] = merged_records
                                with self._lock:
                                    self._applied_ids.update(merged_ids)
                                    self._applied_records.update(merged_records)
                            elif "seen_job_ids" in data:
                                disk_ids = set(str(x).strip() for x in disk_data.get("seen_job_ids", []))
                                merged_ids = disk_ids.union(data["seen_job_ids"])
                                disk_records = disk_data.get("records", {})
                                merged_records = dict(disk_records)
                                merged_records.update(data.get("records", {}))
                                data["seen_job_ids"] = sorted(list(merged_ids))
                                data["records"] = merged_records
                                with self._lock:
                                    self._seen_ids.update(merged_ids)
                                    self._seen_records.update(merged_records)
                except Exception as e:
                    logger.debug("Could not merge existing file %s: %s", file_path, e)

            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
                f.flush()
                os.fsync(f.fileno())

            os.replace(tmp_path, file_path)
        except Exception as e:
            logger.error("Failed atomic write to %s: %s", file_path, e)
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
        finally:
            if lock_fd is not None:
                try:
                    if fcntl is not None:
                        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
                    lock_fd.close()
                except Exception:
                    pass


# Backward-compatibility alias
LinkedInJobDeduplicator = JobDeduplicator


# ==============================================================================
# PRECISION MATCH SCORING ENGINE
# ==============================================================================

@dataclass
class MatchScoreResult:
    score: float                         # 0.0 to 100.0
    passed: bool                        # True if score >= 70.0
    match_reasons: List[str]            # Detailed audit trace of sub-scores and decisions
    breakdown: Dict[str, float]         # {"title": ..., "tech": ..., "experience": ..., "penalty": ..., "total": ...}
    job_title: str
    extracted_experience: Optional[str] = None
    matched_skills: List[str] = field(default_factory=list)


class JobMatchScorer:
    """
    Evaluates vacancy alignment for Lavkush Kumar (Azure Data Engineer, 2.5 YOE).
    Weights: Title (35%), Tech Stack (45%), Experience (20%). Strict Cutoff >= 70.0%.
    """

    NEGATIVE_TITLE_PATTERNS: List[str] = [
        r"\b(frontend|front-end|react|angular|vue|ui[/-]ux|designer|web developer)\b",
        r"\b(android|ios|swift|flutter|mobile developer)\b",
        r"\b(hr|human\s+resources|recruiter|recruiting|sourcing|talent\s+acquisition|headhunter)\b",
        r"\b(financial|finance|accounting|auditor|compliance|legal|sales|marketing|account\s+manager|account\s+executive|business\s+development|content\s+writer|copywriter|wordpress)\b",
        r"\b(director|vp|vice president|head of data|engineering manager|principal|staff engineer|chief architect)\b",
        r"\b(embedded|firmware|hardware|mechanical|civil)\b",
    ]

    TIER1_TITLE_PATTERNS: List[str] = [
        r"\bazure\s+data\s+engineer\b",
        r"\bdatabricks\s+(data\s+)?engineer\b",
        r"\bpyspark\s+(data\s+)?engineer\b",
        r"\bdelta\s+lake\s+engineer\b",
        r"\bazure\s+databricks\s+engineer\b",
        r"\bdata\s+engineer\s*-\s*azure\b",
        r"\bcloud\s+data\s+engineer\b.*azure",
    ]

    TIER2_TITLE_PATTERNS: List[str] = [
        r"\bdata\s+engineer\b",
        r"\bbig\s+data\s+engineer\b",
        r"\betl\s+developer\b",
        r"\betl\s+engineer\b",
        r"\bdata\s+platform\s+engineer\b",
        r"\bdata\s+pipeline\s+engineer\b",
        r"\bdataops\s+engineer\b",
        r"\blakehouse\s+engineer\b",
        r"\bcloud\s+data\s+engineer\b",
    ]

    TIER3_TITLE_PATTERNS: List[str] = [
        r"\banalytics\s+engineer\b",
        r"\bdatabase\s+(engineer|developer)\b",
        r"\b(dwh|data\s+warehouse)\s+engineer\b",
        r"\bdevops\s+engineer\b",
        r"\bcloud\s+engineer\b",
        r"\bpython\s+data\s+developer\b",
        r"\bsoftware\s+engineer\s*-\s*data\b",
    ]

    def _evaluate_title(self, job_title: str) -> Tuple[float, float, bool, List[str]]:
        """
        Evaluates title alignment against engineering taxonomy and negative patterns.
        Returns: (title_score, penalty, disqualified, reasons)
        """
        title_clean = str(job_title or "").strip()
        title_lower = title_clean.lower()
        reasons: List[str] = []
        title_score = 0.0
        penalty = 0.0
        disqualified = False

        # Evaluate NEGATIVE_TITLE_PATTERNS FIRST
        for pat in self.NEGATIVE_TITLE_PATTERNS:
            m = re.search(pat, title_lower)
            if m:
                title_score = 0.0
                penalty = 50.0
                disqualified = True
                reasons.append(
                    f"DISQUALIFIED_TITLE: Title '{title_clean}' matched negative pattern '{m.group(0)}' (-50pt penalty)"
                )
                return title_score, penalty, disqualified, reasons

        # Positive Title Tiers
        if any(re.search(pat, title_lower) for pat in self.TIER1_TITLE_PATTERNS):
            title_score = 35.0
            reasons.append("TITLE_MATCH_TIER1: Direct title alignment with Azure Data Engineer profile (35.0/35.0)")
        elif any(re.search(pat, title_lower) for pat in self.TIER2_TITLE_PATTERNS):
            title_score = 26.25
            reasons.append("TITLE_MATCH_TIER2: General Data Engineering title alignment (26.25/35.0)")
        elif any(re.search(pat, title_lower) for pat in self.TIER3_TITLE_PATTERNS):
            title_score = 14.0
            reasons.append("TITLE_MATCH_TIER3: Adjacent technical title alignment (14.0/35.0)")
        elif re.search(r"\b(software\s+engineer|data\s+analyst|bi\s+analyst|business\s+intelligence\s+analyst|etl\s+developer|data\s+consultant)\b", title_lower):
            title_score = 5.25
            reasons.append("TITLE_MATCH_TIER4: Generic technical title (5.25/35.0)")
        else:
            title_score = 0.0
            reasons.append("TITLE_MATCH_NONE: Title did not match data engineering taxonomy (0.0/35.0)")

        return title_score, penalty, disqualified, reasons

    def _extract_experience(self, jd_text: str, title_text: str = "") -> Tuple[float, Optional[str], float, List[str]]:
        """
        Extracts and scores required experience with ReDoS-bounded regexes.
        Returns: (exp_score, extracted_exp, exp_penalty, reasons)
        """
        jd_lower = str(jd_text or "").lower()
        title_lower = str(title_text or "").lower()
        reasons: List[str] = []
        exp_score = 0.0
        exp_penalty = 0.0
        extracted_exp = None

        # Bounded quantifiers preventing ReDoS catastrophic backtracking
        range_match = re.search(
            r"\b(\d{1,2}(?:\.\d+)?)\s*(?:-|to)\s*(\d{1,2}(?:\.\d+)?)\s*(?:\+)?\s*(?:years|yrs|year|yr)\b",
            jd_lower
        )
        plus_match = re.search(
            r"(?:min|minimum|at least)?\s*(\d{1,2}(?:\.\d+)?)\s*\+\s*(?:years|yrs|year|yr)\b",
            jd_lower
        )
        single_match = re.search(
            r"\b(\d{1,2}(?:\.\d+)?)\s*(?:\+)?\s*(?:years|yrs|year|yr)\b",
            jd_lower
        )

        if range_match:
            min_y = float(range_match.group(1))
            max_y = float(range_match.group(2))
            extracted_exp = f"{min_y}-{max_y} YOE"
            if min_y >= 7.0 or max_y >= 8.0:
                exp_score = 0.0
                exp_penalty = 20.0
                reasons.append(f"EXP_DISQUALIFIED: Required {extracted_exp} exceeds 2.5 YOE (-20pt penalty)")
            elif 1.0 <= min_y <= 4.0 and max_y <= 5.0:
                exp_score = 20.0
                reasons.append(f"EXP_MATCH_IDEAL: Required {extracted_exp} matches candidate's 2.5 YOE (20.0/20.0)")
            elif min_y <= 3.0 and max_y <= 4.0:
                exp_score = 18.0
                reasons.append(f"EXP_MATCH_ENTRY: Required {extracted_exp}, candidate is well-qualified (18.0/20.0)")
            elif 3.0 <= min_y <= 5.0 and max_y <= 6.0:
                exp_score = 12.0
                reasons.append(f"EXP_MATCH_STRETCH: Required {extracted_exp} is a moderate stretch (12.0/20.0)")
            elif 5.0 <= min_y <= 7.0 and max_y <= 8.0:
                exp_score = 5.0
                reasons.append(f"EXP_MATCH_HIGH: Required {extracted_exp} is a high stretch (5.0/20.0)")
            else:
                exp_score = 14.0
                reasons.append(f"EXP_MATCH_GENERAL: Range {extracted_exp} evaluated at baseline (14.0/20.0)")
        elif plus_match:
            req_y = float(plus_match.group(1))
            extracted_exp = f"{req_y}+ YOE"
            if req_y >= 7.0:
                exp_score = 0.0
                exp_penalty = 20.0
                reasons.append(f"EXP_DISQUALIFIED: Required {extracted_exp} exceeds 2.5 YOE (-20pt penalty)")
            elif req_y <= 3.0:
                exp_score = 20.0
                reasons.append(f"EXP_MATCH_IDEAL: Required {extracted_exp} matches candidate (20.0/20.0)")
            elif req_y <= 5.0:
                exp_score = 12.0
                reasons.append(f"EXP_MATCH_STRETCH: Required {extracted_exp} is a moderate stretch (12.0/20.0)")
            else:
                exp_score = 5.0
                reasons.append(f"EXP_MATCH_HIGH: Required {extracted_exp} is high for 2.5 YOE (5.0/20.0)")
        elif single_match:
            req_y = float(single_match.group(1))
            extracted_exp = f"{req_y} YOE"
            if req_y >= 7.0:
                exp_score = 0.0
                exp_penalty = 20.0
                reasons.append(f"EXP_DISQUALIFIED: Required {extracted_exp} exceeds 2.5 YOE (-20pt penalty)")
            elif 1.0 <= req_y <= 4.0:
                exp_score = 20.0
                reasons.append(f"EXP_MATCH_IDEAL: Required {extracted_exp} matches candidate (20.0/20.0)")
            elif req_y < 1.0:
                exp_score = 18.0
                reasons.append(f"EXP_MATCH_ENTRY: Required {extracted_exp}, candidate is well-qualified (18.0/20.0)")
            elif req_y <= 6.0:
                exp_score = 12.0
                reasons.append(f"EXP_MATCH_STRETCH: Required {extracted_exp} is a moderate stretch (12.0/20.0)")
            else:
                exp_score = 5.0
                reasons.append(f"EXP_MATCH_HIGH: Required {extracted_exp} is a high stretch (5.0/20.0)")
        else:
            # Imputed default from title
            if "senior" in title_lower:
                exp_score = 10.0
                reasons.append("EXP_DEFAULT_SENIOR: Imputed 10.0/20.0 for Senior role without explicit JD YOE")
            elif "junior" in title_lower or "associate" in title_lower:
                exp_score = 18.0
                reasons.append("EXP_DEFAULT_JUNIOR: Imputed 18.0/20.0 for Associate/Junior role")
            else:
                exp_score = 14.0
                reasons.append("EXP_DEFAULT_NEUTRAL: Imputed 14.0/20.0 baseline for unspecified YOE")

        return exp_score, extracted_exp, exp_penalty, reasons

    def evaluate(
        self,
        job_title: Any,
        job_description: Any,
        candidate_skills: Optional[List[Any]] = None
    ) -> MatchScoreResult:
        """
        Evaluates match score for a job posting.
        Returns MatchScoreResult with score, passed, breakdown, and audit reasons.
        """
        # Defensive input validation
        job_title_str = str(job_title or "").strip()
        job_description_str = str(job_description or "").strip()
        title_lower = job_title_str.lower()
        jd_lower = job_description_str.lower()
        full_text = f"{title_lower} {jd_lower}"

        clean_candidate_skills: List[str] = []
        if candidate_skills:
            clean_candidate_skills = [
                str(s).strip().lower()
                for s in candidate_skills
                if s is not None and str(s).strip()
            ]

        reasons: List[str] = []
        penalty: float = 0.0

        # ---------------------------------------------------------
        # 1. TITLE ALIGNMENT SCORE (35.0 pts max)
        # ---------------------------------------------------------
        title_score, title_penalty, disqualified_title, title_reasons = self._evaluate_title(job_title_str)
        penalty += title_penalty
        reasons.extend(title_reasons)

        # ---------------------------------------------------------
        # 2. CORE TECH STACK SCORE (45.0 pts max)
        # ---------------------------------------------------------
        # Cluster 1: Azure Ecosystem & Ingestion (10.0 pts)
        has_azure = bool(re.search(r"\b(azure|microsoft azure)\b", full_text))
        has_ingestion = bool(re.search(
            r"\b(adf|azure data factory|adls|adls gen2|synapse|azure synapse|fabric|microsoft fabric)\b",
            full_text
        ))
        if has_azure and has_ingestion:
            c1_score = 10.0
        elif has_azure or has_ingestion:
            c1_score = 6.0
        else:
            c1_score = 0.0

        # Cluster 2: Databricks & Delta Lake Lakehouse (10.0 pts)
        has_dbx = bool(re.search(r"\b(databricks|azure databricks)\b", full_text))
        has_delta = bool(re.search(
            r"\b(delta lake|lakehouse|medallion|medallion architecture|unity catalog|bronze|silver|gold)\b",
            full_text
        ))
        if has_dbx and has_delta:
            c2_score = 10.0
        elif has_dbx or has_delta:
            c2_score = 6.0
        else:
            c2_score = 0.0

        # Cluster 3: Distributed Data Processing - PySpark (10.0 pts)
        if re.search(r"\bpyspark\b", full_text):
            c3_score = 10.0
        elif re.search(r"\b(spark|apache spark|spark sql)\b", full_text):
            c3_score = 7.0
        else:
            c3_score = 0.0

        # Cluster 4: Programming & Querying Languages (10.0 pts)
        has_py = bool(re.search(r"\bpython\b", full_text))
        has_sql = bool(re.search(r"\b(sql|spark sql|pl/sql|tsql|postgres|postgresql)\b", full_text))
        if has_py and has_sql:
            c4_score = 10.0
        elif has_py or has_sql:
            c4_score = 5.0
        else:
            c4_score = 0.0

        # Cluster 5: DataOps, Streaming & Architecture (5.0 pts)
        dataops_matches = re.findall(
            r"\b(kafka|event hubs|streaming|terraform|ci/cd|docker|git|data modeling|star schema|dbt|etl|elt)\b",
            full_text
        )
        distinct_ops = set(dataops_matches)
        if len(distinct_ops) >= 2:
            c5_score = 5.0
        elif len(distinct_ops) == 1:
            c5_score = 3.0
        else:
            c5_score = 0.0

        # If candidate_skills are provided explicitly, allow them to augment matched competencies
        if clean_candidate_skills:
            for s_clean in clean_candidate_skills:
                if s_clean in full_text and s_clean not in distinct_ops:
                    distinct_ops.add(s_clean)

        tech_score = min(45.0, c1_score + c2_score + c3_score + c4_score + c5_score)
        matched_skills_list = []
        if has_azure:
            matched_skills_list.append("Azure")
        if has_ingestion:
            matched_skills_list.append("ADF/Synapse")
        if has_dbx:
            matched_skills_list.append("Databricks")
        if has_delta:
            matched_skills_list.append("Delta Lake")
        if c3_score > 0:
            matched_skills_list.append("PySpark/Spark")
        if has_py:
            matched_skills_list.append("Python")
        if has_sql:
            matched_skills_list.append("SQL")
        if distinct_ops:
            matched_skills_list.extend(list(distinct_ops)[:3])

        reasons.append(
            f"TECH_STACK_MATCH: Clusters [Azure: {c1_score}/10, Databricks/Delta: {c2_score}/10, "
            f"Spark: {c3_score}/10, Py/SQL: {c4_score}/10, DataOps: {c5_score}/5] -> {tech_score}/45.0 pts"
        )

        # ---------------------------------------------------------
        # 3. EXPERIENCE RANGE SCORE (20.0 pts max)
        # ---------------------------------------------------------
        exp_score, extracted_exp, exp_penalty, exp_reasons = self._extract_experience(jd_lower, title_lower)
        penalty += exp_penalty
        reasons.extend(exp_reasons)

        # ---------------------------------------------------------
        # 4. FINAL AGGREGATION & HARD GATE EVALUATION
        # ---------------------------------------------------------
        if disqualified_title:
            raw_total = 0.0
            final_score = 0.0
            passed = False
        else:
            raw_total = title_score + tech_score + exp_score - penalty
            final_score = round(max(0.0, min(100.0, raw_total)), 1)
            passed = (final_score >= 70.0)

        if not passed:
            reasons.append(f"GATE_REJECTED: Final score {final_score}% < 70.0% threshold")
        else:
            reasons.append(f"GATE_PASSED: Final score {final_score}% >= 70.0% threshold")

        return MatchScoreResult(
            score=final_score,
            passed=passed,
            match_reasons=reasons,
            breakdown={
                "title": round(title_score, 2),
                "tech": round(tech_score, 2),
                "experience": round(exp_score, 2),
                "penalty": round(penalty, 2),
                "total": final_score
            },
            job_title=job_title_str,
            extracted_experience=extracted_exp,
            matched_skills=matched_skills_list
        )

    def evaluate_match_score(
        self,
        job_title: str,
        job_description: str,
        candidate_skills: Optional[List[str]] = None
    ) -> MatchScoreResult:
        """Alias for evaluate."""
        return self.evaluate(job_title, job_description, candidate_skills)

    def score_job(
        self,
        title: str,
        description_snippet: str = "",
        candidate_skills: Optional[List[str]] = None
    ) -> MatchScoreResult:
        """Alias for evaluate with title and description_snippet."""
        return self.evaluate(job_title=title, job_description=description_snippet, candidate_skills=candidate_skills)


# Backward-compatibility alias
PrecisionMatchScorer = JobMatchScorer


# ==============================================================================
# ASYNC & PLAYWRIGHT MOCK TOLERANT DOM EXTRACTION HELPERS
# ==============================================================================

async def safe_inner_text(loc: Any, default: str = "") -> str:
    try:
        res = loc.inner_text()
        if inspect.isawaitable(res):
            text = await res
        else:
            text = str(res)
        return (text or "").strip()
    except Exception:
        return default


async def safe_get_attribute(loc: Any, attr: str, default: Optional[str] = None) -> Optional[str]:
    try:
        res = loc.get_attribute(attr)
        if inspect.isawaitable(res):
            val = await res
        else:
            val = res
        return val.strip() if val else default
    except Exception:
        return default


async def safe_count(loc: Any) -> int:
    try:
        res = loc.count()
        if inspect.isawaitable(res):
            return await res
        return int(res)
    except Exception:
        return 0


async def safe_is_visible(loc: Any) -> bool:
    try:
        res = loc.is_visible()
        if inspect.isawaitable(res):
            return await res
        return bool(res)
    except Exception:
        return False


# ==============================================================================
# DOM JOB CARD PARSER
# ==============================================================================

class LinkedInJobCardParser:
    """
    Parses LinkedIn job search result cards using cascaded selector fallbacks,
    progressive container scrolling for de-occlusion, and strict job ID normalization.
    """

    CONTAINER_SELECTORS = [
        "div.jobs-search-results-list",
        "div.scaffold-layout__list",
        "div.scaffold-layout__list-detail",
        "ul.scaffold-layout__list-container",
    ]

    CARD_SELECTORS = [
        "li.jobs-search-results__list-item",
        "li.scaffold-layout__list-item",
        "div.job-card-container[data-job-id]",
        "li[data-occludable-job-id]",
    ]

    ZERO_RESULTS_SELECTORS = [
        "div.jobs-search-no-results-banner",
        "div.jobs-search-two-pane__no-results-banner",
        "div.jobs-search-no-results",
        "h1.jobs-search-no-results__title",
        "h1.artdeco-empty-state__headline",
        "div.artdeco-empty-state",
    ]

    async def parse_job_cards(
        self,
        page: Any,
        scroll_to_load: bool = True,
        max_cards: int = 25
    ) -> List[Dict[str, Any]]:
        """
        Extracts up to max_cards from the search results page.
        Handles zero-result banners, container scrolling, and progressive de-occlusion.
        """
        # 1. Zero-results check
        for z_sel in self.ZERO_RESULTS_SELECTORS:
            if hasattr(page, "locator"):
                cnt = await safe_count(page.locator(z_sel))
                if cnt > 0:
                    logger.info("Zero-results banner detected (%s). No jobs to parse.", z_sel)
                    return []

        # 2. Hybrid de-occlusion collection
        collected_jobs: Dict[str, Dict[str, Any]] = {}

        active_card_sel = None
        if hasattr(page, "locator"):
            for sel in self.CARD_SELECTORS:
                if await safe_count(page.locator(sel)) > 0:
                    active_card_sel = sel
                    break
        if not active_card_sel:
            active_card_sel = "li.jobs-search-results__list-item, div.job-card-container"

        max_scroll_passes = 12 if scroll_to_load else 1

        for pass_idx in range(max_scroll_passes):
            card_loc = page.locator(active_card_sel) if hasattr(page, "locator") else None
            card_cnt = await safe_count(card_loc) if card_loc else 0
            if card_cnt == 0:
                break

            for i in range(card_cnt):
                if len(collected_jobs) >= max_cards:
                    break
                card = card_loc.nth(i) if hasattr(card_loc, "nth") else card_loc

                # Scroll individual card into view to trigger DOM hydration
                if hasattr(card, "scroll_into_view_if_needed"):
                    try:
                        res_scroll = card.scroll_into_view_if_needed(timeout=1000)
                        if inspect.isawaitable(res_scroll):
                            await res_scroll
                    except Exception:
                        pass

                job_data = await self.parse_single_card(card, page=page)
                if job_data and job_data.get("job_id"):
                    collected_jobs[job_data["job_id"]] = job_data

            if len(collected_jobs) >= max_cards or not scroll_to_load:
                break

            # Scroll container downwards
            if hasattr(page, "evaluate"):
                try:
                    res_eval = page.evaluate("""
                        () => {
                            const el = document.querySelector('div.jobs-search-results-list') 
                                    || document.querySelector('div.scaffold-layout__list')
                                    || document.querySelector('ul.scaffold-layout__list-container');
                            if (el) {
                                el.scrollBy({ top: 400, behavior: 'smooth' });
                                return el.scrollTop + el.clientHeight >= el.scrollHeight - 20;
                            }
                            return true;
                        }
                    """)
                    if inspect.isawaitable(res_eval):
                        is_bottom = await res_eval
                    else:
                        is_bottom = res_eval
                except Exception:
                    is_bottom = True
            else:
                is_bottom = True

            # Short humanized delay for DOM hydration
            if hasattr(page, "wait_for_timeout"):
                try:
                    res_wait = page.wait_for_timeout(350)
                    if inspect.isawaitable(res_wait):
                        await res_wait
                except Exception:
                    pass

            if is_bottom and pass_idx >= 3:
                break

        return list(collected_jobs.values())

    async def parse_single_card(self, card: Any, page: Optional[Any] = None) -> Optional[Dict[str, Any]]:
        """Parses an individual job card locator into a structured dictionary."""
        try:
            # 1. Job ID Extraction
            job_id = await self.extract_job_id(card, page=page)
            if not job_id:
                return None

            # 2. Title Extraction
            title = await self.extract_title(card)

            # 3. Company Extraction
            company = await self.extract_company(card)

            # 4. Location & Workplace Type Extraction
            location, workplace_type = await self.extract_location_and_workplace(card)

            # 5. Easy Apply & Applied Status Extraction
            is_easy_apply = await self.check_easy_apply(card)
            is_already_applied = await self.check_already_applied(card)

            # 6. Time Posted & Raw Text
            time_posted = await self.extract_time_posted(card)
            raw_text = await safe_inner_text(card)

            return {
                "job_id": job_id,
                "title": title or "Azure Data Engineer",
                "company": company or "Unknown Employer",
                "location": location or "India",
                "workplace_type": workplace_type,
                "url": f"https://www.linkedin.com/jobs/view/{job_id}/",
                "is_easy_apply": is_easy_apply,
                "is_already_applied": is_already_applied,
                "time_posted": time_posted,
                "raw_snippet": " ".join(raw_text.split()[:40]) if raw_text else ""
            }
        except Exception as e:
            logger.debug("Error parsing single card: %s", e)
            return None

    async def extract_job_id(self, card: Any, page: Optional[Any] = None) -> Optional[str]:
        """Extracts and normalizes numeric job ID following 5-tier priority hierarchy."""
        # Tier 1: data-job-id attribute on card
        val = await safe_get_attribute(card, "data-job-id")
        if val and re.match(r"^\d{8,12}$", val):
            return val

        # Tier 2: data-occludable-job-id attribute
        val = await safe_get_attribute(card, "data-occludable-job-id")
        if val and re.match(r"^\d{8,12}$", val):
            return val

        # Tier 3: data-entity-urn attribute
        urn = await safe_get_attribute(card, "data-entity-urn")
        if urn:
            m = re.search(r"jobPosting:(\d{8,12})", urn)
            if m:
                return m.group(1)

        # Tier 4: Title link href
        if hasattr(card, "locator"):
            for sel in ["a.job-card-list__title", "a.job-card-container__link", "a[href*='/jobs/view/']"]:
                link_loc = card.locator(sel)
                if await safe_count(link_loc) > 0:
                    first_link = link_loc.first if hasattr(link_loc, "first") else link_loc
                    href = await safe_get_attribute(first_link, "href")
                    if href:
                        m = re.search(r"/jobs/view/(\d{8,12})", href) or re.search(r"currentJobId=(\d{8,12})", href)
                        if m:
                            return m.group(1)

        # Tier 5: Internal container element with data-job-id
        if hasattr(card, "locator"):
            sub_container = card.locator("div[data-job-id], div.job-card-container")
            if await safe_count(sub_container) > 0:
                first_sub = sub_container.first if hasattr(sub_container, "first") else sub_container
                val = await safe_get_attribute(first_sub, "data-job-id")
                if val and re.match(r"^\d{8,12}$", val):
                    return val

        return None

    async def extract_title(self, card: Any) -> str:
        """Extracts job title using prioritized selector fallbacks."""
        title_selectors = [
            "a.job-card-list__title",
            "a.job-card-container__link",
            "a.job-card-list__title span[aria-hidden='true']",
            "span.job-card-list__title",
            "strong.job-card-list__title",
            "div.artdeco-entity-lockup__title a",
        ]
        if hasattr(card, "locator"):
            for sel in title_selectors:
                loc = card.locator(sel)
                if await safe_count(loc) > 0:
                    first_loc = loc.first if hasattr(loc, "first") else loc
                    text = await safe_inner_text(first_loc)
                    if text and len(text) > 2 and not re.match(r"^view\s+(?:job|details|role|more)\b", text, re.I):
                        cleaned = text.split("\n")[0].strip()
                        return cleaned
        return ""

    async def extract_company(self, card: Any) -> str:
        """Extracts company name."""
        company_selectors = [
            "span.job-card-container__primary-description",
            "div.artdeco-entity-lockup__subtitle",
            "span.job-card-container__company-name",
            "a.job-card-container__company-link",
            "div.job-card-container__company-name",
        ]
        if hasattr(card, "locator"):
            for sel in company_selectors:
                loc = card.locator(sel)
                if await safe_count(loc) > 0:
                    first_loc = loc.first if hasattr(loc, "first") else loc
                    text = await safe_inner_text(first_loc)
                    if text:
                        return text.split("\n")[0].strip()
        return ""

    async def extract_location_and_workplace(self, card: Any) -> Tuple[str, str]:
        """Extracts location string and workplace type (On-site, Hybrid, Remote)."""
        loc_text = ""
        location_selectors = [
            "li.job-card-container__metadata-item",
            "span.job-card-container__metadata-wrapper",
            "div.artdeco-entity-lockup__caption li",
            "div.artdeco-entity-lockup__caption",
        ]
        if hasattr(card, "locator"):
            for sel in location_selectors:
                loc = card.locator(sel)
                if await safe_count(loc) > 0:
                    first_loc = loc.first if hasattr(loc, "first") else loc
                    text = await safe_inner_text(first_loc)
                    if text:
                        loc_text = text
                        break

        # Detect workplace type
        full_card_text = await safe_inner_text(card)
        workplace_type = "Hybrid"
        if re.search(r"\bRemote\b", full_card_text, re.I) or re.search(r"\bRemote\b", loc_text, re.I):
            workplace_type = "Remote"
        elif re.search(r"\bOn[\s-]site\b", full_card_text, re.I) or re.search(r"\bOn[\s-]site\b", loc_text, re.I):
            workplace_type = "On-site"
        elif re.search(r"\bHybrid\b", full_card_text, re.I) or re.search(r"\bHybrid\b", loc_text, re.I):
            workplace_type = "Hybrid"

        return loc_text.strip(), workplace_type

    async def check_easy_apply(self, card: Any) -> bool:
        """Determines if the card supports Easy Apply."""
        if hasattr(card, "locator"):
            for sel in [
                "li.job-card-container__apply-method",
                "li:has-text('Easy Apply')",
                "span.job-card-container__apply-method",
                "svg[data-test-icon='linkedin-bug']",
            ]:
                if await safe_count(card.locator(sel)) > 0:
                    return True
        card_text = await safe_inner_text(card)
        return bool(re.search(r"Easy\s+Apply", card_text, re.I))

    async def check_already_applied(self, card: Any) -> bool:
        """Determines if the card indicates already applied status."""
        if hasattr(card, "locator"):
            footer_selectors = [
                "span.job-card-container__footer-job-state",
                "li.job-card-container__footer-item",
                "div.job-card-container__footer-item",
            ]
            for sel in footer_selectors:
                loc = card.locator(sel)
                count = await safe_count(loc)
                if count > 0:
                    for idx in range(count):
                        nth_loc = loc.nth(idx) if hasattr(loc, "nth") else loc
                        text = (await safe_inner_text(nth_loc)).strip()
                        if re.search(r"\bApplied\b", text, re.I):
                            return True

        # Anchored pattern on card text to prevent false positive on company names like 'Applied Materials'
        card_text = await safe_inner_text(card)
        return bool(re.search(
            r"\bApplied\s+\d+\s+(?:day|hour|week|month|minute)s?\s+ago\b|\bApplied\s+on\b|\bStatus:\s*Applied\b",
            card_text,
            re.I
        ))

    async def extract_time_posted(self, card: Any) -> str:
        """Extracts relative posting date string (e.g. 1 day ago)."""
        if hasattr(card, "locator"):
            time_loc = card.locator("time, span.job-card-container__listed-date")
            if await safe_count(time_loc) > 0:
                first_time = time_loc.first if hasattr(time_loc, "first") else time_loc
                return await safe_inner_text(first_time)
        return ""


# ==============================================================================
# UNIFIED LINKEDIN SEARCH ENGINE (PROJECT.MD INTERFACE CONTRACT)
# ==============================================================================

class LinkedInSearchEngine:
    """
    Search & Vacancy Discovery Engine for LinkedIn.
    Fulfills interface contract defined in PROJECT.md:
    - TECH_HUBS dictionary
    - build_search_url() method
    - evaluate_match_score() method (gating at >= 70.0%)
    - parse_job_cards() method
    - search_jobs() orchestration method
    """

    TECH_HUBS = TECH_HUBS
    CANONICAL_LOCATIONS = CANONICAL_LOCATIONS
    LOCATION_ALIASES = LOCATION_ALIASES
    DEFAULT_KEYWORDS = DEFAULT_KEYWORDS
    TARGET_KEYWORDS_TIER1 = TARGET_KEYWORDS_TIER1
    TARGET_KEYWORDS_TIER2 = TARGET_KEYWORDS_TIER2
    ALL_TARGET_KEYWORDS = ALL_TARGET_KEYWORDS

    def __init__(
        self,
        deduplicator: Optional[JobDeduplicator] = None,
        scorer: Optional[JobMatchScorer] = None,
        card_parser: Optional[LinkedInJobCardParser] = None,
        policy: Optional[Any] = None,
    ):
        self.url_builder = LinkedInSearchUrlBuilder()
        self.deduplicator = deduplicator or JobDeduplicator()
        self.scorer = scorer or JobMatchScorer()
        self.card_parser = card_parser or LinkedInJobCardParser()
        self.policy = policy

    def build_search_url(
        self,
        keyword: str,
        location: str = "Bengaluru",
        freshness_sec: int = 86400,
        easy_apply_only: bool = True,
        **kwargs
    ) -> str:
        """
        Builds LinkedIn search URL adhering to PROJECT.md interface contract.
        """
        return self.url_builder.build(
            keyword=keyword,
            location=location,
            freshness_sec=freshness_sec,
            easy_apply_only=easy_apply_only,
            **kwargs
        )

    def generate_search_matrix(
        self,
        keywords: Optional[List[str]] = None,
        locations: Optional[List[str]] = None,
        freshness_sec: int = 86400,
        easy_apply_only: bool = True,
        tier: int = 1,
    ) -> List[Dict[str, str]]:
        """Generates full query matrix across target keywords and tech hubs."""
        return self.url_builder.generate_matrix(
            keywords=keywords,
            locations=locations,
            freshness_sec=freshness_sec,
            easy_apply_only=easy_apply_only,
            tier=tier,
        )

    def parse_search_url(self, url: str) -> Dict[str, Any]:
        """Reverse-parses search URL for inspection or verification."""
        return self.url_builder.parse(url)

    def evaluate_match_score(
        self,
        job_title: str,
        job_description: str,
        candidate_skills: Optional[List[str]] = None
    ) -> float:
        """
        Evaluates match score between 0.0 and 100.0, fulfilling PROJECT.md interface contract.
        """
        res = self.scorer.evaluate(
            job_title=job_title,
            job_description=job_description,
            candidate_skills=candidate_skills
        )
        return res.score

    def evaluate_match(
        self,
        job_title: str,
        job_description: str,
        candidate_skills: Optional[List[str]] = None
    ) -> MatchScoreResult:
        """Rich match evaluation returning full MatchScoreResult dataclass."""
        return self.scorer.evaluate(
            job_title=job_title,
            job_description=job_description,
            candidate_skills=candidate_skills
        )

    async def parse_job_cards(
        self,
        page: Any,
        scroll_to_load: bool = True,
        max_cards: int = 25
    ) -> List[Dict[str, Any]]:
        """Parses job cards from search results list."""
        return await self.card_parser.parse_job_cards(
            page=page,
            scroll_to_load=scroll_to_load,
            max_cards=max_cards
        )

    async def search_jobs(
        self,
        page: Any,
        keyword: str,
        location: str = "Bengaluru",
        max_pages: int = 1,
        easy_apply_only: bool = True,
        freshness_sec: int = 86400,
        min_match_score: float = 70.0,
        candidate_skills: Optional[List[str]] = None,
        policy: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        Orchestrates full search execution:
        1. Generates search URLs across requested pages.
        2. Navigates page and extracts job cards via progressive de-occlusion.
        3. Deduplicates against seen and applied IDs.
        4. Evaluates match score and gates at >= min_match_score (default 70.0%).
        5. Intercepts match gate with LinUCB contextual bandit selection policy when available.
        6. Marks evaluated jobs in deduplication cache.
        7. Returns list of qualified, unapplied jobs (re-ranked by policy score).
        """
        qualified_jobs: List[Dict[str, Any]] = []
        seen_batch_ids: Set[str] = set()
        active_policy = policy if policy is not None else self.policy
        policy_skipped_jobs: List[Dict[str, Any]] = []

        for page_idx in range(1, max_pages + 1):
            url = self.build_search_url(
                keyword=keyword,
                location=location,
                freshness_sec=freshness_sec,
                easy_apply_only=easy_apply_only,
                page=page_idx,
            )
            logger.info("Navigating to LinkedIn search page %d: %s", page_idx, url)

            if hasattr(page, "goto"):
                try:
                    res_goto = page.goto(url)
                    if inspect.isawaitable(res_goto):
                        await res_goto
                except Exception as e:
                    logger.warning("Error navigating to %s: %s", url, e)
                    continue

            cards = await self.parse_job_cards(page=page, scroll_to_load=True)
            if not cards:
                logger.info("No cards found on page %d for %s in %s.", page_idx, keyword, location)
                break

            # Filter against already applied jobs
            unapplied = self.deduplicator.filter_unapplied_jobs(cards)

            for card in unapplied:
                jid = card.get("job_id")
                if not jid or jid in seen_batch_ids:
                    continue
                seen_batch_ids.add(jid)

                if card.get("is_already_applied"):
                    self.deduplicator.mark_applied(jid, job_info=card)
                    continue

                if easy_apply_only and not card.get("is_easy_apply"):
                    self.deduplicator.mark_seen(jid, job_info=card, status="SKIPPED_NOT_EASY_APPLY")
                    continue

                title = card.get("title", "")
                snippet = card.get("raw_snippet", "")
                match_res = self.scorer.evaluate(
                    job_title=title,
                    job_description=snippet,
                    candidate_skills=candidate_skills
                )

                card["match_score"] = match_res.score
                card["match_result"] = asdict(match_res)

                if active_policy is not None:
                    job_ctx = {
                        "match_score": match_res.score,
                        "required_yoe": 2.5,
                        "posting_age_hours": 24.0,
                        "company": card.get("company", ""),
                        "platform": "LinkedIn Easy Apply",
                        "salary_lpa": 20.0,
                        "jd": f"{title} {snippet}",
                    }
                    action, ucb_score, diag = active_policy.select_action(job_ctx, explore=True, increment_decision=True)
                    card["policy_version"] = getattr(active_policy, "policy_version", "v2.1-linucb")
                    card["policy_action"] = action.name if hasattr(action, "name") else str(action)
                    card["policy_score"] = ucb_score
                    card["policy_propensity"] = diag.get("propensity", 1.0)
                    card["policy_diagnostics"] = diag

                    if match_res.score >= min_match_score:
                        if card["policy_action"] == "SKIP":
                            policy_skipped_jobs.append(card)
                            self.deduplicator.mark_seen(jid, job_info=card, status="SKIPPED_POLICY_BANDIT")
                            continue
                        self.deduplicator.mark_seen(jid, job_info=card, status="QUALIFIED")
                        qualified_jobs.append(card)
                    else:
                        self.deduplicator.mark_seen(jid, job_info=card, status="SKIPPED_LOW_MATCH")
                else:
                    if match_res.score >= min_match_score:
                        self.deduplicator.mark_seen(jid, job_info=card, status="QUALIFIED")
                        qualified_jobs.append(card)
                    else:
                        self.deduplicator.mark_seen(jid, job_info=card, status="SKIPPED_LOW_MATCH")

        if active_policy is not None:
            # Volume floor enforcement: top up with highest match_score skipped jobs if below floor
            try:
                from naukari_pro.modules.learning.volume_guard import VolumeGuard
                vg = VolumeGuard()
                qualified_jobs, promoted = vg.enforce_volume_floor(qualified_jobs, policy_skipped_jobs)
                for pj in promoted:
                    pjid = pj.get("job_id")
                    if pjid:
                        self.deduplicator.mark_seen(pjid, job_info=pj, status="QUALIFIED_APPLY_FLOOR")
            except Exception as e_vg:
                logger.debug("Volume guard check notice: %s", e_vg)

            if qualified_jobs:
                # Re-rank decisions by policy UCB score
                qualified_jobs.sort(key=lambda j: j.get("policy_score", 0.0), reverse=True)

        return qualified_jobs
