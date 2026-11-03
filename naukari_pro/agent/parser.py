"""
naukariPro Agent Subsystem: Dynamic Intent Parser
Module: naukari_pro.agent.parser
Converts CLI argparse namespaces, JSON configuration files, dictionaries,
and conversational natural-language inputs into validated CandidateIntent objects.
"""

import os
import re
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from naukari_pro.agent.intent import (
    CandidateIntent,
    DEFAULT_TARGET_ROLES,
    DEFAULT_TARGET_LOCATIONS,
    SUPPORTED_PLATFORMS
)


class IntentParser:
    """
    Translates diverse input sources (CLI args, JSON configs, dicts, natural language)
    into validated CandidateIntent instances.
    """

    KNOWN_ROLE_PATTERNS = [
        (r"mlops(\s+engineer|\s+platform)?", "MLOps Engineer"),
        (r"ml\s+platform(\s+engineer)?", "ML Platform Engineer"),
        (r"ai\s+infrastructure(\s+engineer)?|ai\s+infra", "AI Infrastructure Engineer"),
        (r"devops\s+for\s+ai", "DevOps for AI"),
        (r"devops(\s+engineer)?", "DevOps Engineer"),
        (r"data\s+platform(\s+engineer)?", "Data Platform Engineer"),
        (r"azure\s+data\s+engineer", "Azure Data Engineer"),
        (r"azure\s+databricks(\s+engineer)?|databricks(\s+engineer)?", "Databricks Engineer"),
        (r"pyspark(\s+developer|\s+engineer)?", "PySpark Developer"),
        (r"delta\s+lake(\s+engineer)?", "Delta Lake Engineer"),
    ]

    KNOWN_LOCATION_PATTERNS = [
        (r"bengaluru|bangalore", "Bengaluru"),
        (r"hyderabad", "Hyderabad"),
        (r"pune", "Pune"),
        (r"gurugram|gurgaon", "Gurugram"),
        (r"noida", "Noida"),
        (r"mumbai", "Mumbai"),
        (r"chennai", "Chennai"),
        (r"remote|wfh|work\s+from\s+home", "Remote"),
    ]

    KNOWN_PLATFORM_PATTERNS = [
        (r"naukri|naukari", "naukri"),
        (r"linkedin(\s+easy\s+apply)?", "linkedin"),
        (r"greenhouse(\.io)?", "greenhouse"),
        (r"lever(\.co)?", "lever"),
        (r"ashby(hq)?", "ashby"),
        (r"workday|myworkdayjobs", "workday"),
        (r"career_portals|external\s+portals?|ats", "career_portals"),
    ]

    @classmethod
    def from_args(cls, args: argparse.Namespace, **overrides) -> CandidateIntent:
        """Constructs CandidateIntent from CLI argparse.Namespace."""
        base_data: Dict[str, Any] = {}

        # 1. Config file preload if provided
        config_path = (
            getattr(args, "config_path", None)
            or getattr(args, "config", None)
            or getattr(args, "intent_file", None)
        )
        if config_path:
            p = Path(config_path)
            if not p.is_file():
                raise FileNotFoundError(f"Intent config file not found: {config_path}")
            with open(p, "r", encoding="utf-8") as f:
                base_data.update(json.load(f))

        # 2. Extract CLI arguments
        cli_roles = getattr(args, "roles", None)
        if cli_roles:
            base_data["target_roles"] = cli_roles if isinstance(cli_roles, list) else [cli_roles]

        cli_locs = getattr(args, "locations", None)
        if cli_locs:
            base_data["target_locations"] = cli_locs if isinstance(cli_locs, list) else [cli_locs]

        cli_plats = getattr(args, "platforms", None)
        if cli_plats:
            base_data["platforms"] = cli_plats if isinstance(cli_plats, list) else [cli_plats]

        # Limit / Max applications
        limit_val = getattr(args, "limit", None) or getattr(args, "max_applications", None)
        if limit_val is not None:
            base_data["max_applications"] = int(limit_val)

        # Salary expectations
        min_sal = getattr(args, "min_salary_lpa", None) or getattr(args, "min_salary", None)
        if min_sal is not None:
            base_data["min_salary_lpa"] = float(min_sal)

        max_sal = getattr(args, "max_salary_lpa", None) or getattr(args, "max_salary", None)
        if max_sal is not None:
            base_data["max_salary_lpa"] = float(max_sal)

        # Threshold
        thresh = (
            getattr(args, "strict_match_threshold", None)
            or getattr(args, "min_score", None)
            or getattr(args, "threshold", None)
        )
        if thresh is not None:
            base_data["strict_match_threshold"] = float(thresh)

        # Execution flags
        if hasattr(args, "dry_run") and args.dry_run is not None:
            base_data["dry_run"] = bool(args.dry_run)

        if hasattr(args, "headed") and args.headed:
            base_data["headless"] = False
        elif hasattr(args, "headless") and args.headless is not None:
            base_data["headless"] = bool(args.headless)

        # Natural language prompt parameter
        intent_text = getattr(args, "intent", None) or getattr(args, "prompt", None) or ""
        if intent_text.strip():
            text_intent = cls.from_text(intent_text)
            for field_name in ["target_roles", "target_locations", "platforms", "ats_filters"]:
                if field_name not in base_data and getattr(text_intent, field_name):
                    base_data[field_name] = getattr(text_intent, field_name)
            base_data["raw_intent"] = intent_text.strip()

        # Work authorization
        work_auth = getattr(args, "work_authorization", None) or getattr(args, "work_auth", None)
        if work_auth:
            base_data["work_authorization"] = str(work_auth).strip()

        if hasattr(args, "requires_sponsorship") and args.requires_sponsorship is not None:
            base_data["requires_sponsorship"] = bool(args.requires_sponsorship)

        # 3. Apply explicit overrides
        base_data.update(overrides)

        return CandidateIntent.from_dict(base_data)

    @classmethod
    def from_json_file(cls, file_path: Union[str, Path], **overrides) -> CandidateIntent:
        """Parses a JSON file into CandidateIntent."""
        p = Path(file_path)
        if not p.is_file():
            raise FileNotFoundError(f"Intent JSON file not found: {file_path}")
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.update(overrides)
        return CandidateIntent.from_dict(data)

    @classmethod
    def from_json(cls, json_str: str, **overrides) -> CandidateIntent:
        """Parses a JSON string into CandidateIntent."""
        data = json.loads(json_str)
        data.update(overrides)
        return CandidateIntent.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], **overrides) -> CandidateIntent:
        """Instantiates CandidateIntent from dictionary with overrides."""
        merged = dict(data)
        merged.update(overrides)
        return CandidateIntent.from_dict(merged)

    @classmethod
    def from_text(cls, text: str, **overrides) -> CandidateIntent:
        """Parses conversational natural-language prompt into CandidateIntent."""
        clean = text.strip()
        lowered = clean.lower()

        # 1. Roles extraction
        extracted_roles = []
        for pat, canonical in cls.KNOWN_ROLE_PATTERNS:
            if re.search(r"\b" + pat + r"\b", lowered):
                if canonical not in extracted_roles:
                    extracted_roles.append(canonical)
        if not extracted_roles:
            extracted_roles = list(DEFAULT_TARGET_ROLES)

        # 2. Locations extraction
        extracted_locations = []
        for pat, canonical in cls.KNOWN_LOCATION_PATTERNS:
            if re.search(r"\b" + pat + r"\b", lowered):
                if canonical not in extracted_locations:
                    extracted_locations.append(canonical)
        if not extracted_locations:
            extracted_locations = list(DEFAULT_TARGET_LOCATIONS)

        # 3. Platforms extraction
        extracted_platforms = []
        ats_filters = []
        for pat, plat in cls.KNOWN_PLATFORM_PATTERNS:
            if re.search(r"\b" + pat + r"\b", lowered):
                if plat in ("greenhouse", "lever", "ashby", "workday"):
                    ats_filters.append(plat)
                    if plat not in extracted_platforms:
                        extracted_platforms.append(plat)
                elif plat in SUPPORTED_PLATFORMS:
                    if plat not in extracted_platforms:
                        extracted_platforms.append(plat)

        if not extracted_platforms:
            extracted_platforms = ["naukri", "linkedin", "workday", "greenhouse", "lever"]

        # 4. Salary parsing
        min_salary = 20.0
        max_salary = None
        range_match = re.search(
            r"(\d{1,2}(?:\.\d+)?)\s*(?:-|to)\s*(\d{1,2}(?:\.\d+)?)\s*(?:lpa|lakhs|lac)",
            lowered
        )
        if range_match:
            try:
                min_salary = float(range_match.group(1))
                max_salary = float(range_match.group(2))
            except (ValueError, IndexError):
                pass
        else:
            sal_match = re.search(
                r"(?:min(?:imum)?\s+)?(?:salary\s*(?:>=|>|of)?\s*)?(\d{1,2}(?:\.\d+)?)\s*(?:lpa|lakhs|lac)",
                lowered
            )
            if sal_match:
                try:
                    min_salary = float(sal_match.group(1))
                except (ValueError, IndexError):
                    min_salary = 20.0

        # 5. Score threshold parsing
        min_score = 70.0
        score_match = re.search(
            r"(?:match|score|threshold)?\s*(?:>=|>|above|minimum|min)?\s*(\d{2}(?:\.\d+)?)\s*(?:%|percent)?",
            lowered
        )
        if score_match:
            try:
                val = float(score_match.group(1))
                if 0.0 <= val <= 100.0:
                    min_score = val
            except (ValueError, IndexError):
                min_score = 70.0

        # 6. Limit parsing
        limit = 15
        limit_match = re.search(r"\b(?:limit|apply\s+to|max|count)\s*(?:of)?\s*(\d{1,3})\b", lowered)
        if limit_match:
            try:
                limit = int(limit_match.group(1))
            except (ValueError, IndexError):
                limit = 15

        # 7. Flags
        dry_run = bool(re.search(r"\b(dry[- ]?run|simulate|simulation|offline|test[- ]mode)\b", lowered))
        headless = not bool(re.search(r"\b(headed|interactive|visible|show\s+browser)\b", lowered))

        data = {
            "target_roles": extracted_roles,
            "target_locations": extracted_locations,
            "platforms": extracted_platforms,
            "min_salary_lpa": min_salary,
            "max_salary_lpa": max_salary,
            "strict_match_threshold": min_score,
            "max_applications": limit,
            "dry_run": dry_run,
            "headless": headless,
            "raw_intent": clean,
            "ats_filters": ats_filters
        }
        data.update(overrides)
        return CandidateIntent.from_dict(data)

    @classmethod
    def parse(cls, source: Any = None, **overrides) -> CandidateIntent:
        """Universal parser intelligently dispatching based on input type."""
        if source is None or source == "":
            return CandidateIntent(**overrides)
        if isinstance(source, CandidateIntent):
            data = source.to_dict()
            data.update(overrides)
            return CandidateIntent.from_dict(data)
        if isinstance(source, argparse.Namespace):
            return cls.from_args(source, **overrides)
        if isinstance(source, dict):
            return cls.from_dict(source, **overrides)
        if isinstance(source, (str, Path)):
            str_src = str(source).strip()
            if str_src.endswith(".json") and os.path.isfile(str_src):
                return cls.from_json_file(str_src, **overrides)
            if str_src.startswith("{") and str_src.endswith("}"):
                return cls.from_json(str_src, **overrides)
            return cls.from_text(str_src, **overrides)
        raise TypeError(f"Cannot parse CandidateIntent from unsupported type: {type(source)}")
