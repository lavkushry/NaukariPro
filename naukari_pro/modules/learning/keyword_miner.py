"""
naukariPro Learning Subsystem: Keyword & Skill Utility Miner (Milestone 3 / R3)
Implements:
1. Token frequency analysis over fresh Job Descriptions
2. Keyword Utility formula: U = Demand / Saturation
3. Claimable token validation anchored strictly in 01_FACT_MATRIX.md & candidate competencies
4. Idempotently populates and queries the keyword_utility SQLite table
"""

import os
import re
import math
import sqlite3
import logging
from collections import Counter
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple, Set

from naukari_pro.config import DB_PATH, load_config
from naukari_pro.modules.db import get_db_connection, init_db

logger = logging.getLogger("naukariPro.KeywordMiner")

# Candidate Verified Claimable Core Competencies (from 01_FACT_MATRIX.md)
VERIFIED_CLAIMABLE_SKILLS: Set[str] = {
    "pyspark",
    "databricks",
    "azure databricks",
    "delta lake",
    "azure data factory",
    "adf",
    "adls gen2",
    "apache kafka",
    "kafka",
    "sql",
    "spark sql",
    "terraform",
    "kubernetes",
    "docker",
    "python",
    "etl",
    "elt",
    "medallion architecture",
    "unity catalog",
    "dataops",
    "ci/cd",
    "jenkins",
    "gitlab ci",
    "redis",
    "postgresql",
    "timescaledb",
    "mongodb",
    "ansible",
    "prometheus",
    "grafana",
    "linux",
    "bash",
    "git",
}

# Strictly Forbidden / Synthetic Skills (per 01_FACT_MATRIX.md & AGENTS.md)
FORBIDDEN_UNCLAIMABLE_SKILLS: Set[str] = {
    "triton",
    "triton inference server",
    "nvidia mps",
    "gpu slicing",
    "cuda",
    "model validation gates",
    "deepspeed",
    "vllm",
    "tensorrt",
    "kserve",
}


def is_token_claimable(token: str) -> bool:
    """
    Checks if a token can be claimed by the candidate without violating 01_FACT_MATRIX.md.
    Returns True if token represents a legitimate skill of candidate (2.5 YOE Azure DE).
    Returns False if token represents unverified, senior-level, or forbidden modeling claims.
    """
    t = token.lower().strip()
    if any(fb in t for fb in FORBIDDEN_UNCLAIMABLE_SKILLS):
        return False
    if t in VERIFIED_CLAIMABLE_SKILLS:
        return True
    # Word-level check for verified skills
    for v in VERIFIED_CLAIMABLE_SKILLS:
        if v in t or t in v:
            return True
    return False


def calculate_utility(demand: int, saturation: int) -> float:
    """
    Computes keyword utility score: U = Demand / Saturation.
    Safe bounded division (saturation >= 1).
    """
    safe_sat = max(1, saturation)
    safe_demand = max(0, demand)
    return round(float(safe_demand) / float(safe_sat), 3)


class KeywordMiner:
    """
    Token frequency analysis and utility scoring over market JDs.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DB_PATH
        init_db(self.db_path)
        self.config = load_config()
        self.candidate_summary = self.config.get("profile_summary", "").lower()

    def extract_keywords_from_text(self, text: str) -> List[str]:
        """Extracts normalized technical tokens from job descriptions."""
        if not text:
            return []
        norm = text.lower()
        # Find multi-word technical patterns
        multi_patterns = [
            r"\bazure data factory\b",
            r"\bazure databricks\b",
            r"\bdelta lake\b",
            r"\bmedallion architecture\b",
            r"\badls gen2\b",
            r"\bapache kafka\b",
            r"\bspark sql\b",
            r"\bunity catalog\b",
            r"\bci/cd\b",
        ]
        found = []
        for pat in multi_patterns:
            matches = re.findall(pat, norm)
            found.extend(matches)

        # Single word technical tokens
        words = re.findall(r"\b[a-zA-Z0-9\+#\.-]{2,20}\b", norm)
        stopwords = {
            "and", "the", "for", "with", "experience", "years", "work", "team", "strong",
            "working", "skills", "data", "engineer", "role", "must", "have", "ability", "etc"
        }
        for w in words:
            if w not in stopwords and len(w) > 2:
                found.append(w)
        return found

    def compute_candidate_saturation(self, token: str) -> int:
        """Counts how many times a token appears in candidate's current profile/summary."""
        t = token.lower().strip()
        count = len(re.findall(r"\b" + re.escape(t) + r"\b", self.candidate_summary))
        return max(1, count)

    def mine_and_store(
        self,
        job_descriptions: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Processes JDs, calculates demand, saturation, and utility,
        and saves records to the keyword_utility table.
        """
        if not job_descriptions:
            # Fallback sample of realistic market JDs for Azure Data Engineer
            job_descriptions = [
                "Azure Databricks PySpark Delta Lake Kafka ADF ADLS Gen2 Medallion Architecture",
                "Azure Data Factory ADF PySpark Databricks SQL Terraform CI/CD",
                "PySpark Spark SQL Delta Lake Databricks Unity Catalog DataOps",
                "Kafka Streaming Azure Databricks Delta Lake Redis PostgreSQL",
                "Azure Cloud Data Engineer PySpark ADF Terraform Docker Kubernetes",
                "Triton Inference Server NVIDIA MPS GPU Slicing CUDA",  # Adversarial forbidden JD
            ]

        token_counter: Counter = Counter()
        for jd in job_descriptions:
            tokens = self.extract_keywords_from_text(jd)
            token_counter.update(tokens)

        records = []
        conn = get_db_connection(self.db_path)
        try:
            with conn:
                for token, demand in token_counter.most_common(100):
                    sat = self.compute_candidate_saturation(token)
                    u_score = calculate_utility(demand, sat)
                    claimable = 1 if is_token_claimable(token) else 0

                    conn.execute("""
                        INSERT INTO keyword_utility (
                            token, demand, demand_frequency, saturation, saturation_count,
                            utility, utility_score, observations, claimable, last_updated, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                        ON CONFLICT(token) DO UPDATE SET
                            demand = excluded.demand,
                            demand_frequency = excluded.demand_frequency,
                            saturation = excluded.saturation,
                            saturation_count = excluded.saturation_count,
                            utility = excluded.utility,
                            utility_score = excluded.utility_score,
                            observations = excluded.observations,
                            claimable = excluded.claimable,
                            last_updated = datetime('now'),
                            updated_at = datetime('now')
                    """, (token, float(demand), demand, float(sat), sat, float(u_score), float(u_score), demand, claimable))

                    records.append({
                        "token": token,
                        "demand": demand,
                        "saturation": sat,
                        "utility": u_score,
                        "claimable": bool(claimable)
                    })
        finally:
            conn.close()

        return records

    def get_top_utility_keywords(
        self,
        limit: int = 10,
        claimable_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Queries the top utility keywords from database."""
        conn = get_db_connection(self.db_path)
        try:
            where_clause = "WHERE claimable = 1" if claimable_only else ""
            query = f"""
                SELECT token, demand_frequency, saturation_count, utility_score, claimable, updated_at
                FROM keyword_utility
                {where_clause}
                ORDER BY utility_score DESC, demand_frequency DESC
                LIMIT ?
            """
            rows = conn.execute(query, (limit,)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


def mine_keywords(job_descriptions: Optional[List[str]] = None, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Functional convenience facade for KeywordMiner."""
    miner = KeywordMiner(db_path=db_path)
    return miner.mine_and_store(job_descriptions=job_descriptions)


def get_top_keywords(limit: int = 10, claimable_only: bool = True, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Functional convenience facade to retrieve top keywords."""
    miner = KeywordMiner(db_path=db_path)
    return miner.get_top_utility_keywords(limit=limit, claimable_only=claimable_only)
