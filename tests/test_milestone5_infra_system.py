"""
tests/test_milestone5_infra_system.py
Verification suite for Milestone 5 / R5:
1. Systemd service and timer unit file specifications and timing validation
2. CLI commands (label-outcomes, mine-keywords, attribution, policy-status, monday-digest)
3. Monday digest report generator and markdown schema integrity
4. Database schema verification & closed-loop SLA compliance
5. Candidate profile integrity & truth anchors
"""

import os
import re
import sys
import json
import sqlite3
import tempfile
import pytest
from datetime import datetime, timedelta

from naukari_pro.modules.db import init_db, get_db_connection, quarantine_item, get_quarantine_summary
from scripts.monday_digest import generate_monday_digest
from naukari_pro.cli import (
    handle_label_outcomes,
    handle_mine_keywords,
    handle_attribution,
    handle_policy_status,
    handle_monday_digest,
)
from naukari_pro.modules.learning.outcome_labeler import OutcomeLabeler
from naukari_pro.modules.learning.keyword_miner import KeywordMiner
from naukari_pro.modules.learning.attribution import AttributionEngine
from naukari_pro.modules.learning.policy import LinUCBBanditPolicy


class TestSystemdUnitFiles:
    """Verifies existence, syntax, and timing schedule for all Milestone 5 systemd units."""

    def test_unit_files_exist(self):
        systemd_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "systemd")
        expected_files = [
            "naukaripro-label.service",
            "naukaripro-label.timer",
            "naukaripro-mutate.service",
            "naukaripro-mutate.timer",
            "naukaripro-learn.service",
            "naukaripro-learn.timer",
        ]
        for f in expected_files:
            path = os.path.join(systemd_dir, f)
            assert os.path.exists(path), f"Missing systemd unit: {path}"
            assert os.path.getsize(path) > 50, f"Systemd unit file too small: {path}"

    def test_label_timer_schedule(self):
        systemd_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "systemd")
        timer_path = os.path.join(systemd_dir, "naukaripro-label.timer")
        with open(timer_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "OnCalendar=*-*-* 21:00:00 Asia/Kolkata" in content
        assert "Persistent=true" in content
        assert "PartOf=naukaripro-label.service" in content

    def test_mutate_timer_schedule(self):
        systemd_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "systemd")
        timer_path = os.path.join(systemd_dir, "naukaripro-mutate.timer")
        with open(timer_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "OnCalendar=Tue,Thu *-*-* 09:30:00 Asia/Kolkata" in content
        assert "Persistent=true" in content
        assert "PartOf=naukaripro-mutate.service" in content

    def test_learn_timer_schedule(self):
        systemd_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "systemd")
        timer_path = os.path.join(systemd_dir, "naukaripro-learn.timer")
        with open(timer_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "OnCalendar=Mon *-*-* 06:00:00 Asia/Kolkata" in content
        assert "Persistent=true" in content
        assert "PartOf=naukaripro-learn.service" in content

    def test_service_exec_commands(self):
        systemd_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "systemd")
        services = {
            "naukaripro-label.service": "label-outcomes",
            "naukaripro-mutate.service": "mutate --auto-bump",
            "naukaripro-learn.service": "monday-digest",
        }
        for svc_file, expected_cmd in services.items():
            path = os.path.join(systemd_dir, svc_file)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "[Service]" in content
            assert "Type=oneshot" in content
            assert expected_cmd in content


class TestMondayDigestGenerator:
    """Verifies Monday digest markdown compilation, section schema, and quantitative metrics."""

    @pytest.fixture
    def test_db(self, tmp_path):
        db_file = str(tmp_path / "test_digest.db")
        init_db(db_file)
        conn = get_db_connection(db_file)
        with conn:
            # Seed applications
            conn.execute("""
                INSERT INTO applied_jobs (job_id, platform, company, title, applied_at, match_score, status, outcome_label, evidence_path)
                VALUES
                ('job-1', 'naukri', 'Microsoft', 'Azure Data Engineer', datetime('now', '-2 days'), 88.0, 'Applied', 'view', '/tmp/ev1.png'),
                ('job-2', 'linkedin', 'Amazon', 'Data Platform Engineer', datetime('now', '-5 days'), 82.0, 'Applied', 'callback', '/tmp/ev2.png'),
                ('job-3', 'career_portal', 'Walmart', 'Lakehouse Engineer', datetime('now', '-10 days'), 78.0, 'Applied', 'silence', ''),
                ('job-4', 'naukri', 'Google', 'Cloud Data Engineer', datetime('now', '-1 days'), 90.0, 'Applied', 'confirmation', '/tmp/ev4.png')
            """)
            # Seed weekly appearances
            conn.execute("""
                INSERT INTO search_appearance_weekly (week_start_date, search_appearances, profile_views, contact_views)
                VALUES
                ('2026-10-05', 450, 42, 8),
                ('2026-10-12', 480, 49, 10),
                ('2026-10-19', 510, 55, 12),
                ('2026-10-26', 560, 64, 15)
            """)
            # Seed keyword utilities
            conn.execute("""
                INSERT INTO keyword_utility (token, demand_frequency, saturation_count, utility_score, claimable)
                VALUES
                ('databricks', 12, 1, 12.0, 1),
                ('delta lake', 9, 1, 9.0, 1),
                ('kafka', 6, 2, 3.0, 1)
            """)
            # Seed quarantine
            conn.execute("""
                INSERT INTO quarantine (category, platform, prompt_text, context_json, status)
                VALUES
                ('screening_ambiguous', 'greenhouse', 'Will you now or in the future require visa sponsorship in the US?', '{}', 'PENDING')
            """)
        conn.close()
        return db_file

    def test_generate_monday_digest_content(self, test_db, tmp_path):
        out_file = str(tmp_path / "Monday_Digest_2026-10-30.md")
        digest = generate_monday_digest(db_path=test_db, output_path=out_file, as_of_date="2026-10-30")

        # Verify output file was created
        assert os.path.exists(out_file)
        assert len(digest) > 500

        # Section 1: Header & Candidate Profile Integrity
        assert "Lavkush Kumar" in digest
        assert "2.5 YOE Azure Data Engineer" in digest
        assert "lavkushry@gmail.com" in digest
        assert "lav84095@gmail.com" in digest

        # Section 2: Application Volume
        assert "Total Applications Tracked:** 4" in digest
        assert "Verified Cryptographic Evidence" in digest
        assert "75.0%" in digest  # 3 of 4 have evidence

        # Section 3: Recruitment Outcomes
        assert "Callbacks / Recruiter Direct:** 1" in digest
        assert "Recruiter Profile Views:** 1" in digest
        assert "Silence / Auto-Timed Out (>72h):** 1" in digest
        assert "Confirmation Pending Review (<72h):** 1" in digest
        assert "SLA Compliance (Unlabeled >72h):** **0**" in digest

        # Section 4: Search Appearance & DiD
        assert "560" in digest  # Latest appearances
        assert "DiD Metric Evaluation" in digest

        # Section 5: Keyword Utility Table
        assert "`databricks`" in digest
        assert "12.00" in digest
        assert "`delta lake`" in digest

        # Section 6: Quarantine Queue
        assert "Total Quarantined Prompts:** 1" in digest
        assert "Pending Ambiguous Reviews:** 1" in digest
        assert "`screening_ambiguous`: 1" in digest


class TestCLICommands:
    """Verifies that all 5 CLI subcommands execute cleanly and return structured data."""

    @pytest.fixture
    def test_db(self, tmp_path):
        db_file = str(tmp_path / "test_cli.db")
        init_db(db_file)
        conn = get_db_connection(db_file)
        with conn:
            conn.execute("""
                INSERT INTO applied_jobs (job_id, platform, company, title, applied_at, match_score, status)
                VALUES
                ('test-1', 'naukri', 'TCS', 'Data Engineer', datetime('now', '-48 hours'), 75.0, 'Applied'),
                ('test-2', 'naukri', 'Infosys', 'ETL Dev', datetime('now', '-96 hours'), 72.0, 'Rejected')
            """)
        conn.close()
        return db_file

    def test_handle_label_outcomes(self, test_db):
        res = handle_label_outcomes(min_age_hours=24.0, dry_run=True, db_path=test_db)
        assert isinstance(res, dict)
        assert res["scanned"] == 2
        assert res["labeled"] == 2
        assert res["breakdown"]["rejection"] == 1

    def test_handle_mine_keywords(self, test_db):
        top = handle_mine_keywords(limit=5, claimable_only=True, db_path=test_db)
        assert isinstance(top, list)
        assert len(top) > 0
        assert all(k["claimable"] for k in top)

    def test_handle_attribution(self, test_db):
        res = handle_attribution(db_path=test_db)
        assert isinstance(res, dict)
        assert "did_estimate" in res
        assert "status" in res

    def test_handle_policy_status(self, test_db):
        policy = handle_policy_status(db_path=test_db)
        assert isinstance(policy, LinUCBBanditPolicy)
        assert policy.policy_version == "v2.0-linucb"

    def test_handle_monday_digest(self, test_db, tmp_path):
        out = str(tmp_path / "test_digest.md")
        digest = handle_monday_digest(output=out, db_path=test_db)
        assert isinstance(digest, str)
        assert "# 📊 NaukariPro Learning Loop — Weekly Monday Digest" in digest
        assert os.path.exists(out)


class TestCandidateIntegrityAndForbiddenVerbs:
    """Verifies that candidate integrity constraints from AGENTS.md & 01_FACT_MATRIX.md are respected."""

    FORBIDDEN_VERBS = [
        r"\bhelped\b",
        r"\bworked on\b",
        r"\bresponsible for\b",
        r"\bassisted\b",
        r"\bhandled\b",
        r"\bparticipated in\b",
    ]

    def test_monday_digest_free_of_forbidden_verbs(self, tmp_path):
        db_file = str(tmp_path / "clean.db")
        init_db(db_file)
        digest = generate_monday_digest(db_path=db_file)
        digest_lower = digest.lower()
        for verb_pattern in self.FORBIDDEN_VERBS:
            match = re.search(verb_pattern, digest_lower)
            assert match is None, f"Found forbidden verb matching pattern '{verb_pattern}' in digest"

    def test_candidate_truth_anchors(self, tmp_path):
        db_file = str(tmp_path / "clean.db")
        init_db(db_file)
        digest = generate_monday_digest(db_path=db_file)
        assert "2.5 YOE" in digest
        assert "lavkushry@gmail.com" in digest
        assert "lav84095@gmail.com" in digest

    def test_spec_4_7_schema_queries(self, tmp_path):
        """Verifies exact schema queries from §4.7 execute cleanly on SQLite."""
        db_file = str(tmp_path / "schema_test.db")
        init_db(db_file)

        # Record sample mutation
        from naukari_pro.modules.db import record_profile_mutation, record_applied_job
        record_profile_mutation(
            platform="naukri",
            field="headline",
            new_value="Azure Data Engineer | 2.5 YOE",
            rationale="spec_test",
            expected_effect="boost_searches",
            db_path=db_file
        )

        # Record sample appearance
        from naukari_pro.modules.profile_performance import ProfilePerformanceEngine
        perf = ProfilePerformanceEngine()
        perf.record_weekly_telemetry(
            week_start="2026-10-26",
            appearances=520,
            platform="naukri",
            screenshot_path="evidence/perf.png",
            db_path=db_file
        )

        # Record sample keyword utility
        from naukari_pro.modules.learning.keyword_miner import KeywordMiner
        miner = KeywordMiner(db_path=db_file)
        miner.mine_and_store(["Azure Databricks PySpark Delta Lake Kafka"])

        # Record sample applied job with policy_version
        record_applied_job(
            title="Azure Data Engineer",
            company="Microsoft GCC",
            status="Submitted (Confirmed)",
            evidence_path=None,  # will downgrade to Form Auto-Filled if invalid, or test with policy_version
            policy_version="v2.0-linucb",
            db_path=db_file
        )

        conn = get_db_connection(db_file)
        try:
            # 1. Profile mutations exact spec query
            q1 = conn.execute("SELECT id, platform, field, old_hash, new_hash, mutated_at, rationale, expected_effect, approved_by FROM profile_mutations;").fetchall()
            assert len(q1) == 1
            assert q1[0]["mutated_at"] is not None

            # 2. Search appearance weekly exact spec query
            q2 = conn.execute("SELECT id, platform, week_start, appearances, captured_at, screenshot_path FROM search_appearance_weekly;").fetchall()
            assert len(q2) == 1
            assert q2[0]["appearances"] == 520

            # 3. Keyword utility exact spec query
            q3 = conn.execute("SELECT token, demand, saturation, utility, observations, last_updated FROM keyword_utility;").fetchall()
            assert len(q3) > 0
            assert q3[0]["utility"] >= 0.0

            # 4. P0 SLA query
            q4 = conn.execute("SELECT COUNT(*) FROM applied_jobs WHERE outcome_label IS NULL AND applied_at < datetime('now','-72 hours');").fetchone()[0]
            assert q4 == 0

            # 5. Policy version persistence check
            q5 = conn.execute("SELECT policy_version FROM applied_jobs WHERE company = 'Microsoft GCC';").fetchone()[0]
            assert q5 == "v2.0-linucb"
        finally:
            conn.close()

    def test_naukri_system_config_learning_and_mutation_keys(self):
        """Verifies learning and mutation keys are present in config.json with reconciled threshold."""
        from naukari_pro.config import load_config
        cfg = load_config()
        assert "learning" in cfg
        assert cfg["learning"]["enabled"] is True
        assert cfg["learning"]["policy_algorithm"] == "LinUCB"
        assert cfg["learning"]["threshold_reconciliation"]["reconciled_threshold"] == 70.0
        assert "mutation" in cfg
        assert cfg["mutation"]["weekly_keyword_limit"] == 2
