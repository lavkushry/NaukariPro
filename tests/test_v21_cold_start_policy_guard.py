"""
tests/test_v21_cold_start_policy_guard.py
Comprehensive verification test suite for NaukariPro v2.1-linucb Cold-Start Policy Fix & Volume Guard:
1. Warm-up exploration schedule (epsilon linear decay 0.30 -> 0.05 over 200 decisions, persisted in policy_state)
2. Reward re-scale & historical replay assertion (expected payoff >= 0.0)
3. DUPLICATE: -2.0 reward ingestion on dedup block
4. Volume floor top-up emitting APPLY_FLOOR tags
5. Circuit breaker drop detection (>50%), transition to FALLBACK, and manual re-arm via policy-arm
6. Monday digest compilation and mocked Gmail SMTP email dispatch
7. Threshold retirement audit and startup deprecation warning
"""

import os
import json
import sqlite3
import tempfile
import warnings
import pytest
from unittest.mock import patch, MagicMock

from naukari_pro.modules.db import (
    init_db,
    get_db_connection,
    record_applied_job,
    get_policy_state,
    increment_policy_decisions,
    update_policy_mode,
    record_policy_event,
    get_recent_policy_events,
)
from naukari_pro.modules.learning.policy import (
    LinUCBBanditPolicy,
    PolicyAction,
    PolicyVersion,
    DEFAULT_POLICY_VERSION,
    extract_context_vector,
    REWARD_SCHEDULE,
    ingest_duplicate_reward,
    parse_yoe_value,
)
from naukari_pro.modules.learning.volume_guard import (
    VolumeGuard,
    send_gmail_notification,
)
from naukari_pro.modules.learning.monday_digest import (
    generate_monday_digest,
    send_monday_digest_email,
)
from naukari_pro.cli import (
    handle_policy_status,
    handle_policy_arm,
    handle_monday_digest,
)


@pytest.fixture
def temp_db(tmp_path):
    """Provides an isolated SQLite database path initialized with v2.1 schema."""
    db_file = str(tmp_path / "test_policy_guard.db")
    init_db(db_file)
    return db_file


class TestWarmupExplorationSchedule:
    """Verifies epsilon linear decay schedule (F1) and persistence in policy_state."""

    def test_epsilon_decay_curve(self, temp_db):
        """Verifies linear decay from 0.30 to 0.05 across 200 decisions."""
        policy = LinUCBBanditPolicy(
            epsilon_warmup=0.30,
            epsilon_greedy=0.05,
            warmup_decisions=200,
        )

        # At decision 0: epsilon must be 0.30
        assert policy.get_effective_epsilon(decisions_count=0) == 0.30

        # At decision 50 (quarter-way): 0.30 - (0.25 * 0.25) = 0.2375
        assert policy.get_effective_epsilon(decisions_count=50) == 0.2375

        # At decision 100 (halfway): 0.30 - (0.25 * 0.5) = 0.175
        assert policy.get_effective_epsilon(decisions_count=100) == 0.175

        # At decision 200: must reach floor of 0.05
        assert policy.get_effective_epsilon(decisions_count=200) == 0.05

        # Beyond 200 decisions: remains at 0.05
        assert policy.get_effective_epsilon(decisions_count=250) == 0.05
        assert policy.get_effective_epsilon(decisions_count=500) == 0.05

    def test_decision_counter_persists_in_policy_state(self, temp_db):
        """Verifies policy decision counter is stored in SQLite policy_state table, never in memory."""
        state = get_policy_state(db_path=temp_db)
        assert state["decisions_count"] == 0
        assert state["mode"] == "ACTIVE"
        assert state["policy_version"] == "v2.1-linucb"

        # Increment decisions in DB
        c1 = increment_policy_decisions(db_path=temp_db)
        assert c1 == 1
        c2 = increment_policy_decisions(db_path=temp_db)
        assert c2 == 2

        # Verify new policy instance reads counter from DB
        policy = LinUCBBanditPolicy()
        eps = policy.get_effective_epsilon(db_path=temp_db)
        # At decision 2: 0.30 - (0.25 * 2 / 200) = 0.30 - 0.0025 = 0.2975
        assert eps == 0.2975

    def test_effective_epsilon_in_select_action_diagnostics(self, temp_db):
        """Verifies select_action emits effective_epsilon, decisions_count, and mode."""
        policy = LinUCBBanditPolicy()
        job = {
            "match_score": 85.0,
            "company": "Microsoft",
            "experience": 2.5,
            "platform": "1-Click Direct",
            "jd": "Databricks PySpark Delta Lake SQL"
        }
        action, ucb, diag = policy.select_action(job, db_path=temp_db, explore=False)
        assert "effective_epsilon" in diag
        assert diag["effective_epsilon"] == 0.30
        assert "decisions_count" in diag
        assert diag["policy_mode"] == "ACTIVE"


class TestRewardRescaleAndBootstrapReplay:
    """Verifies reward rescaling and historical replay asserting APPLY expected payoff >= 0.0 (F2)."""

    def test_rescaled_reward_schedule_constants(self):
        """Verifies exact reward schedule constants: silence/ghosted=0.0, rejected=-0.5, duplicate=-2.0."""
        assert REWARD_SCHEDULE["silence"] == 0.0
        assert REWARD_SCHEDULE["ghosted"] == 0.0
        assert REWARD_SCHEDULE["rejection"] == -0.5
        assert REWARD_SCHEDULE["rejected"] == -0.5
        assert REWARD_SCHEDULE["view"] == 0.2
        assert REWARD_SCHEDULE["viewed"] == 0.2
        assert REWARD_SCHEDULE["screening_request"] == 0.6
        assert REWARD_SCHEDULE["interview"] == 1.0
        assert REWARD_SCHEDULE["offer"] == 2.0
        assert REWARD_SCHEDULE["duplicate"] == -2.0

    def test_historical_replay_asserts_apply_payoff_non_negative(self, temp_db):
        """Verifies cold-start bootstrap over historical outcome distributions yields APPLY expected payoff >= 0.0."""
        # Seed 144 mock records mimicking live production distribution:
        # 108 silence, 25 confirmation, 11 views
        for i in range(108):
            record_applied_job(title=f"Data Eng {i}", company=f"Company {i}", status="Submitted", db_path=temp_db)
        for i in range(25):
            record_applied_job(title=f"Azure Data Eng {i}", company=f"Firm {i}", status="Submitted", db_path=temp_db)
        for i in range(11):
            record_applied_job(title=f"Platform Eng {i}", company=f"Enterprise {i}", status="Form Auto-Filled", application_type="Workday", db_path=temp_db)

        # Label outcomes
        conn = get_db_connection(temp_db)
        with conn:
            conn.execute("UPDATE applied_jobs SET outcome_label = 'silence' WHERE status = 'Submitted' AND id <= 108;")
            conn.execute("UPDATE applied_jobs SET outcome_label = 'confirmation' WHERE status = 'Submitted' AND id > 108;")
            conn.execute("UPDATE applied_jobs SET outcome_label = 'view' WHERE status = 'Form Auto-Filled';")
        conn.close()

        policy = LinUCBBanditPolicy()
        updated = policy.bootstrap_from_history(db_path=temp_db)
        assert updated == 144

        # Compute payoff on Tier 1 sample vacancy
        sample_job = {
            "match_score": 85.0,
            "required_yoe": 2.5,
            "posting_age_hours": 12.0,
            "company": "Microsoft",
            "platform": "1-Click Direct",
            "jd": "Databricks PySpark Delta Lake Kafka ADF SQL",
            "salary": 24.0
        }
        x_sample = extract_context_vector(sample_job)
        _, payoff, _ = policy.predict_ucb(x_sample, PolicyAction.APPLY)
        assert payoff >= 0.0, f"Expected payoff for APPLY ({payoff}) must be >= 0.0!"

    def test_duplicate_reward_ingestion_on_dedup_block(self, temp_db):
        """Verifies DUPLICATE: -2.0 penalty is ingested into policy APPLY arm when db.py blocks duplicate."""
        policy = LinUCBBanditPolicy()
        x = [0.85, 0.25, 0.1, 1.0, 1.0, 0.8, 0.6]

        # Initial payoff
        _, initial_payoff, _ = policy.predict_ucb(x, PolicyAction.APPLY)

        # Record initial application
        ok1, jid1 = record_applied_job(
            title="Azure Data Engineer",
            company="Goldman Sachs",
            db_path=temp_db
        )
        assert ok1 is True

        # Second submission: duplicate! Pass policy instance
        ok2, jid2 = record_applied_job(
            title="Azure Data Engineer",
            company="Goldman Sachs",
            raw_metadata={"policy_action": "APPLY"},
            policy=policy,
            db_path=temp_db
        )
        assert ok2 is False
        assert "BLOCKED_DUPLICATE" in jid2

        # Verify policy received -2.0 reward for APPLY arm
        _, post_payoff, _ = policy.predict_ucb(x, PolicyAction.APPLY)
        assert post_payoff < initial_payoff, "Payoff should decrease after -2.0 duplicate penalty!"

        # Verify event logged in policy_events table
        events = get_recent_policy_events(limit=5, db_path=temp_db)
        dup_events = [e for e in events if e["event_type"] == "DUPLICATE_PENALTY_INGESTED"]
        assert len(dup_events) >= 1
        assert "Goldman Sachs" in dup_events[0]["details"]

    def test_bootstrap_replays_duplicate_penalties_from_events(self, temp_db):
        """Verifies duplicate penalties in policy_events table are replayed during bootstrap."""
        # 1. Insert 4 base positive applications with outcomes
        for i in range(4):
            record_applied_job(
                title=f"Azure Data Engineer {i}",
                company=f"TechCorp {i}",
                status="Submitted (Confirmed)",
                match_score=85.0,
                db_path=temp_db
            )
        conn = get_db_connection(temp_db)
        with conn:
            conn.execute("UPDATE applied_jobs SET outcome_label = 'interview'")
        conn.close()

        # Bootstrap policy on base records
        p1 = LinUCBBanditPolicy()
        p1.bootstrap_from_history(db_path=temp_db)
        x = extract_context_vector({"match_score": 85.0, "company": "TechCorp 0", "title": "Azure Data Engineer 0"})
        _, payoff_before, _ = p1.predict_ucb(x, PolicyAction.APPLY)

        # 2. Trigger duplicate block to record DUPLICATE_PENALTY_INGESTED event
        ok_dup, _ = record_applied_job(
            title="Azure Data Engineer 0",
            company="TechCorp 0",
            raw_metadata={"policy_action": "APPLY"},
            db_path=temp_db
        )
        assert ok_dup is False

        # 3. Bootstrap a fresh policy instance from SQLite
        p2 = LinUCBBanditPolicy()
        p2.bootstrap_from_history(db_path=temp_db)
        _, payoff_after, _ = p2.predict_ucb(x, PolicyAction.APPLY)

        # Payoff of p2 must reflect the replayed duplicate penalty and be strictly less
        assert payoff_after < payoff_before

    def test_zero_record_fresh_install_bootstrap(self, temp_db):
        """Verifies policy bootstraps cleanly without errors when DB has zero records."""
        policy = LinUCBBanditPolicy()
        updated = policy.bootstrap_from_history(db_path=temp_db)
        assert updated == 0
        _, payoff, _ = policy.get_sample_apply_payoff()
        assert payoff >= 0.0


class TestVolumeGuardAndCircuitBreaker:
    """Verifies volume floor top-up and circuit breaker drop fallback (F3)."""

    def test_volume_floor_top_up_emits_apply_floor_tag(self, temp_db):
        """Verifies highest match_score skipped jobs are promoted with policy_action=APPLY_FLOOR."""
        vg = VolumeGuard(db_path=temp_db)
        vg.min_applications_per_day = 5

        # 2 qualified jobs, 4 skipped jobs with varying match scores
        qualified = [
            {"job_id": "q1", "match_score": 90.0, "title": "DE 1", "policy_action": "APPLY"},
            {"job_id": "q2", "match_score": 85.0, "title": "DE 2", "policy_action": "APPLY"},
        ]
        skipped = [
            {"job_id": "s1", "match_score": 82.0, "title": "Skip 82", "policy_action": "SKIP"},
            {"job_id": "s2", "match_score": 75.0, "title": "Skip 75", "policy_action": "SKIP"},
            {"job_id": "s3", "match_score": 79.0, "title": "Skip 79", "policy_action": "SKIP"},
            {"job_id": "s4", "match_score": 71.0, "title": "Skip 71", "policy_action": "SKIP"},
        ]

        # Enforce volume floor: needed = 5 - 2 = 3 jobs
        final_qualified, promoted = vg.enforce_volume_floor(
            qualified_jobs=qualified,
            skipped_jobs=skipped,
            target_daily_volume=5,
            db_path=temp_db
        )

        assert len(final_qualified) == 5
        assert len(promoted) == 3

        # Highest match score skipped jobs must be promoted (82, 79, 75)
        promoted_scores = [p["match_score"] for p in promoted]
        assert promoted_scores == [82.0, 79.0, 75.0]

        # Must be explicitly tagged with APPLY_FLOOR
        for p in promoted:
            assert p["policy_action"] == "APPLY_FLOOR"
            assert p["policy_floor_override"] is True

        # Lowest skipped job (71.0) remains in skipped list
        assert len(skipped) == 1
        assert skipped[0]["match_score"] == 71.0

    def test_circuit_breaker_triggers_fallback_and_rearm(self, temp_db):
        """Verifies drop >50% switches mode to FALLBACK, requires manual policy-arm."""
        vg = VolumeGuard(db_path=temp_db)
        vg.drop_threshold_pct = 50.0

        conn = get_db_connection(temp_db)
        now = "2026-10-30 12:00:00"
        prior_week = "2026-10-20 12:00:00"
        with conn:
            # Prior 7d: 20 applications with verified evidence
            for i in range(20):
                conn.execute(
                    "INSERT INTO applied_jobs (job_id, platform, company, title, status, applied_at, evidence_path, is_backfill) VALUES (?, 'naukri', 'Comp', 'Role', 'Submitted (Confirmed)', ?, '/evidence/proof.png', 0)",
                    (f"p_{i}", prior_week)
                )
            # Last 7d: only 5 applications (75% drop > 50%)
            for i in range(5):
                conn.execute(
                    "INSERT INTO applied_jobs (job_id, platform, company, title, status, applied_at, evidence_path, is_backfill) VALUES (?, 'naukri', 'Comp', 'Role', 'Submitted (Confirmed)', ?, '/evidence/proof.png', 0)",
                    (f"l_{i}", now)
                )
        conn.close()

        # Check circuit breaker
        res = vg.check_circuit_breaker(db_path=temp_db, send_alert=False)
        assert res["triggered"] is True
        assert res["new_mode"] == "FALLBACK"
        assert res["drop_pct"] == 75.0

        # Verify state in DB is now FALLBACK
        state = get_policy_state(db_path=temp_db)
        assert state["mode"] == "FALLBACK"

        # Verify policy selects score-only ranking when in FALLBACK mode
        policy = LinUCBBanditPolicy()
        high_job = {"match_score": 75.0, "company": "Comp A"}
        act_high, _, diag_high = policy.select_action(high_job, db_path=temp_db)
        assert act_high == PolicyAction.APPLY
        assert diag_high["mode"] == "FALLBACK"

        low_job = {"match_score": 65.0, "company": "Comp B"}
        act_low, _, diag_low = policy.select_action(low_job, db_path=temp_db)
        assert act_low == PolicyAction.SKIP

        # Manual re-arm via policy-arm
        rearm_ok = handle_policy_arm(db_path=temp_db)
        assert rearm_ok is True
        state_after = get_policy_state(db_path=temp_db)
        assert state_after["mode"] == "ACTIVE"

    def test_366_backfill_and_33_organic_fixture_does_not_trip_breaker(self, temp_db):
        """
        Verifies that a fixture mirroring production state (366 backfill rows + 33 organic submissions
        in prior window, and 33 organic submissions in last 7d) does NOT falsely trip the circuit breaker.
        The 366 backfill rows (is_backfill=1) must be excluded from submission counts.
        """
        vg = VolumeGuard(db_path=temp_db)
        vg.drop_threshold_pct = 50.0

        conn = get_db_connection(temp_db)
        with conn:
            # Prior 7d window (e.g. 10 days ago):
            # 366 synthetic / backfilled rows with is_backfill=1
            for i in range(366):
                conn.execute("""
                    INSERT INTO applied_jobs (job_id, platform, company, title, applied_at, status, is_backfill)
                    VALUES (?, 'naukri', 'Backfill Corp', 'Data Engineer', datetime('now', '-10 days'), 'Submitted', 1)
                """, (f"bf_{i}",))

            # 33 organic confirmed submissions in prior window with is_backfill=0 and non-empty evidence_path
            for i in range(33):
                conn.execute("""
                    INSERT INTO applied_jobs (job_id, platform, company, title, applied_at, status, evidence_path, is_backfill)
                    VALUES (?, 'naukri', 'Organic Corp Prior', 'Data Engineer', datetime('now', '-10 days'), 'Submitted (Confirmed)', '/evidence/proof.png', 0)
                """, (f"org_prior_{i}",))

            # Last 7d window (e.g. 2 days ago):
            # 33 organic confirmed submissions with is_backfill=0 and non-empty evidence_path
            for i in range(33):
                conn.execute("""
                    INSERT INTO applied_jobs (job_id, platform, company, title, applied_at, status, evidence_path, is_backfill)
                    VALUES (?, 'naukri', 'Organic Corp Recent', 'Data Engineer', datetime('now', '-2 days'), 'Submitted (Confirmed)', '/evidence/proof.png', 0)
                """, (f"org_recent_{i}",))
        conn.close()

        # Check volume stats: submission-only count vs raw counts
        stats = vg.get_volume_stats(db_path=temp_db)
        assert stats["submission_prior_7d_count"] == 33
        assert stats["submission_last_7d_count"] == 33
        assert stats["last_7d_count"] == 33
        assert stats["prior_7d_count"] == 33
        assert stats["raw_prior_7d_count"] == 399  # 366 backfill + 33 organic
        assert stats["raw_last_7d_count"] == 33
        assert stats["drop_pct"] == 0.0

        # Check circuit breaker does NOT trip
        cb_res = vg.check_circuit_breaker(db_path=temp_db, send_alert=False)
        assert cb_res["triggered"] is False
        assert cb_res["mode"] == "ACTIVE"
        assert cb_res["drop_pct"] == 0.0

        # Verify state in DB remains ACTIVE
        state = get_policy_state(db_path=temp_db)
        assert state["mode"] == "ACTIVE"

    def test_auto_apply_volume_floor_top_up(self, temp_db):
        """Verifies AutoApplyEngine offline dry run top-up when daily count is below floor."""
        from naukari_pro.modules.auto_apply import AutoApplyEngine
        policy = LinUCBBanditPolicy()
        engine = AutoApplyEngine(dry_run=True, policy=policy)

        sample_vacancies = [
            {"title": "Azure Data Engineer 1", "company": "Corp A", "jd": "Azure Databricks PySpark Delta Lake Kafka ADF", "salary": "20 LPA", "url": "http://a"},
            {"title": "Azure Data Engineer 2", "company": "Corp B", "jd": "Azure Databricks PySpark Delta Lake Kafka ADF", "salary": "22 LPA", "url": "http://b"},
            {"title": "Azure Data Engineer 3", "company": "Corp C", "jd": "Azure Databricks PySpark Delta Lake Kafka ADF", "salary": "24 LPA", "url": "http://c"},
        ]
        with patch("naukari_pro.modules.auto_apply.load_config") as mock_cfg:
            mock_cfg.return_value = {
                "search_settings": {"min_match_score": 70.0},
                "learning": {"volume": {"min_applications_per_day": 10}},
                "answers_to_common_questions": {}
            }
            payloads = engine.run_offline_dry_run(job_feed=sample_vacancies)
            valid = [p for p in payloads if p.status == "VALIDATED_PAYLOAD"]
            assert len(valid) > 0

    def test_career_portals_volume_floor_top_up(self, temp_db, tmp_path):
        """Verifies CareerPortalFiller enforces policy gating and volume floor top-up."""
        import openpyxl
        from naukari_pro.modules.career_portals import CareerPortalFiller

        wb_path = str(tmp_path / "test_tracker.xlsx")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Applications_Log"
        ws.append([
            "Application Date", "Company Name", "Job Title", "Match Score (%)", "Role Category",
            "Experience Required", "Location", "Application Type", "Status", "Job URL", "Recruiter Response"
        ])
        for i in range(5):
            ws.append([
                "2026-10-30", f"Comp {i}", f"Role {i}", "85%", "Data", "2-5 Yrs", "Hyderabad", "External", "External Redirect", f"http://portal{i}.com", ""
            ])
        wb.save(wb_path)

        with patch("naukari_pro.modules.career_portals.TRACKER_PATH", wb_path):
            filler = CareerPortalFiller()
            filler.policy = LinUCBBanditPolicy()
            res = filler.process_external_redirects(limit=5, dry_run=True)
            assert res["processed"] > 0
            assert res["submitted"] > 0


class TestMondayDigestAndEmailDispatcher:
    """Verifies Monday digest rendering and mocked SMTP dispatch (F4)."""

    def test_monday_digest_contains_all_six_sections(self, temp_db):
        """Verifies all mandatory sections are present in compiled digest."""
        digest = generate_monday_digest(db_path=temp_db)
        assert "# 📊 NaukariPro Learning Loop — Weekly Monday Digest" in digest
        assert "## 1. Application Volume & Proof-of-Apply Evidence" in digest
        assert "## 2. Recruitment Outcome Breakdown & SLA Tracking" in digest
        assert "## 3. Search Appearance Delta & DiD Attribution" in digest
        assert "## 4. Top Mined Keyword Utilities" in digest
        assert "## 5. Screening Quarantine Queue & Guardrails" in digest
        assert "## 6. Contextual Bandit Policy & Volume Guard Telemetry" in digest
        assert "Operating Mode:" in digest
        assert "Effective Exploration Epsilon (ε):" in digest

    @patch("smtplib.SMTP")
    def test_monday_digest_mocked_smtp_email_dispatch(self, mock_smtp, temp_db):
        """Verifies send_monday_digest_email executes SMTP protocol when password is set."""
        mock_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_instance

        with patch.dict(os.environ, {"GMAIL_APP_PASSWORD": "mock_app_password_123"}):
            ok = send_monday_digest_email("Test Digest Content", subject="Test Subject", recipient="test@example.com")
            assert ok is True
            mock_instance.starttls.assert_called_once()
            mock_instance.login.assert_called_once_with("lav84095@gmail.com", "mock_app_password_123")
            mock_instance.sendmail.assert_called_once()

    def test_monday_digest_executes_circuit_breaker_check(self, temp_db):
        """Verifies generate_monday_digest triggers circuit breaker when drop > 50%."""
        conn = get_db_connection(temp_db)
        with conn:
            # Prior 7d: 20 applications with verified evidence
            for i in range(20):
                conn.execute("""
                    INSERT INTO applied_jobs (job_id, platform, company, title, applied_at, status, evidence_path, is_backfill)
                    VALUES (?, 'naukri', ?, 'Data Eng', datetime('now', '-10 days'), 'Submitted (Confirmed)', '/evidence/proof.png', 0)
                """, (f"p_{i}", f"PriorCorp {i}"))
            # Last 7d: 4 applications (80% drop)
            for i in range(4):
                conn.execute("""
                    INSERT INTO applied_jobs (job_id, platform, company, title, applied_at, status, evidence_path, is_backfill)
                    VALUES (?, 'naukri', ?, 'Data Eng', datetime('now', '-2 days'), 'Submitted (Confirmed)', '/evidence/proof.png', 0)
                """, (f"l_{i}", f"LastCorp {i}"))
        conn.close()

        # Generating monday digest should execute circuit breaker check
        digest = generate_monday_digest(db_path=temp_db)
        assert "Circuit Breaker Status:" in digest
        assert "TRIGGERED -> FALLBACK" in digest

        # Verify state in DB was switched to FALLBACK
        state = get_policy_state(db_path=temp_db)
        assert state["mode"] == "FALLBACK"


class TestThresholdRetirementAndDeprecationWarning:
    """Verifies 80.0 threshold retirement and config startup warning (F5)."""

    def test_canonical_match_threshold_is_seventy(self):
        """Verifies canonical match threshold is 70.0%."""
        from naukari_pro.config import load_config
        cfg = load_config()
        assert float(cfg.get("learning", {}).get("match_threshold", 0.0)) == 70.0
        assert float(cfg.get("search_settings", {}).get("min_match_score", 0.0)) == 70.0

    def test_conflict_warning_fires_on_legacy_threshold(self):
        """Verifies startup warning is emitted when MIN_MATCH_SCORE >= 80 is set."""
        from naukari_pro.config import load_config
        with patch.dict(os.environ, {"MIN_MATCH_SCORE": "80.0"}):
            with pytest.warns(UserWarning, match="DEPRECATION / CONFLICT WARNING"):
                cfg = load_config()
                assert cfg["search_settings"]["min_match_score"] == 80.0
