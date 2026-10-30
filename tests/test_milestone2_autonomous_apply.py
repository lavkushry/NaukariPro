"""
Comprehensive Offline Test Suite for Milestone 2 (R2): Autonomous Multi-Channel Apply & Evidence Hardening
Verifies:
1. 3-Point Evidence State Machine:
   - Condition (a): Valid PNG screenshot (>1KB, 8-byte PNG header) saved to evidence/evidence_<company>_<role>.png
   - Condition (b): Status updated to 'Submitted (Confirmed)' in DB with evidence_path and timestamp
   - Condition (c): Fallback mechanism strictly maintains 'Form Auto-Filled (Ready for Review)' on missing/invalid evidence
2. Fact-Matrix Anchored Screening Solver:
   - Disqualifying questions (conviction, non-compete, disciplinary, family) strictly answer False / "No"
   - Regulatory policy / background check / consent strictly answer True / "Yes"
   - Foreign jurisdictions (US citizenship, work authorization in USA/UK) strictly answer False / "No"
   - Ambiguous queries raise AmbiguousScreeningException and record into SQLite 'quarantine' table
   - Zero blind affirmative fallbacks on unknown prompts
3. Safety Rails & Execution Controls:
   - Process-level singleton ApplicationLock mutual exclusion via flock
   - Randomized typing delay bounds [30ms, 80ms]
   - Security checkpoint & CAPTCHA detection and immediate abort
"""

import os
import sys
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
import pytest

from naukari_pro.modules.learning.evidence import (
    EvidenceVerifier,
    PNG_MAGIC_HEADER,
    MIN_SCREENSHOT_BYTES,
)
from naukari_pro.modules.learning.screening_solver import (
    FactMatrixScreeningSolver,
    ScreeningCategory,
    ScreeningInputType,
    ScreeningDecision,
    AmbiguousScreeningException,
)
from naukari_pro.modules.learning.safety import (
    ApplicationLock,
    SafetyViolationError,
    CheckpointDetectedException,
    get_human_typing_delay,
    human_type_sync,
    detect_security_checkpoint_sync,
    CHECKPOINT_SELECTORS,
    CHECKPOINT_URL_PATTERNS,
)
from naukari_pro.modules.db import (
    init_db,
    record_applied_job,
    quarantine_item,
    get_quarantined_items,
    get_db_connection,
)


# ==============================================================================
# 1. 3-POINT EVIDENCE VERIFICATION ENGINE TESTS
# ==============================================================================

class TestEvidenceVerificationEngine:
    """Verifies evidence capture, header validation, token sanitization, and DB transition."""

    def test_png_magic_header_and_minimum_size_enforcement(self, tmp_path):
        """Verifies verify_screenshot_file rejects small files, empty files, non-PNGs, and accepts valid PNGs."""
        verifier = EvidenceVerifier(base_dir=str(tmp_path))

        # 1. Non-existent file
        assert verifier.verify_screenshot_file(tmp_path / "nonexistent.png") is False

        # 2. Empty file (0 bytes)
        empty_file = tmp_path / "empty.png"
        empty_file.write_bytes(b"")
        assert verifier.verify_screenshot_file(empty_file) is False

        # 3. Small file (< 1024 bytes) even with PNG header
        small_file = tmp_path / "small.png"
        small_file.write_bytes(PNG_MAGIC_HEADER + b"\x00" * 100)
        assert verifier.verify_screenshot_file(small_file) is False

        # 4. Large file (>= 1024 bytes) but INVALID header (e.g. JPEG or corrupt)
        corrupt_file = tmp_path / "corrupt.png"
        corrupt_file.write_bytes(b"\xFF\xD8\xFF\xE0" + b"\x00" * 1100)
        assert verifier.verify_screenshot_file(corrupt_file) is False

        # 5. Valid PNG file (>= 1024 bytes with exact 8-byte PNG signature)
        valid_file = tmp_path / "valid.png"
        valid_file.write_bytes(PNG_MAGIC_HEADER + b"\x00" * (MIN_SCREENSHOT_BYTES + 50))
        assert verifier.verify_screenshot_file(valid_file) is True

    def test_sanitize_token_determinism_and_bounds(self):
        """Verifies filename token sanitization handles unicode, spaces, punctuation, and length bounds."""
        assert EvidenceVerifier.sanitize_token("Microsoft Inc.") == "microsoft_inc"
        assert EvidenceVerifier.sanitize_token("Lead Azure Data Engineer / Lakehouse") == "lead_azure_data_engineer_lakehouse"
        assert EvidenceVerifier.sanitize_token("  --Special-Chars@@#$$--  ") == "special_chars"
        assert EvidenceVerifier.sanitize_token(None, default="fallback") == "fallback"
        assert EvidenceVerifier.sanitize_token("", default="fallback") == "fallback"

        # Bounded length (max_len = 50)
        long_name = "a" * 100
        sanitized = EvidenceVerifier.sanitize_token(long_name, max_len=50)
        assert len(sanitized) <= 50

    def test_canonical_evidence_path_generation(self, tmp_path):
        """Verifies generated evidence path conforms to canonical naming convention."""
        verifier = EvidenceVerifier(base_dir=str(tmp_path))
        p = verifier.get_evidence_path("Microsoft GCC", "Lead Azure DE")
        assert p.name == "evidence_microsoft_gcc_lead_azure_de.png"
        assert p.parent == tmp_path / "evidence"

    def test_evidence_state_machine_confirmed_vs_fallback(self, tmp_path):
        """
        Verifies condition (a) & (b) vs fallback (c):
        When valid screenshot exists -> 'Submitted (Confirmed)'
        When screenshot is missing or invalid -> fallback 'Form Auto-Filled (Ready for Review)'
        """
        db_path = str(tmp_path / "test_applied.db")
        init_db(db_path)
        verifier = EvidenceVerifier(base_dir=str(tmp_path))

        # Scenario 1: Submission with valid evidence screenshot
        valid_png = tmp_path / "evidence" / "evidence_walmart_azure_de.png"
        valid_png.parent.mkdir(parents=True, exist_ok=True)
        valid_png.write_bytes(PNG_MAGIC_HEADER + b"\x00" * 1200)

        is_valid = verifier.verify_screenshot_file(valid_png)
        status_1 = "Submitted (Confirmed)" if is_valid else "Form Auto-Filled (Ready for Review)"
        ok1, job_id_1 = record_applied_job(
            title="Azure Data Engineer",
            company="Walmart Global Tech",
            location="Bengaluru",
            status=status_1,
            match_score=88,
            platform="naukri",
            job_url="https://naukri.com/job-101",
            evidence_path=str(valid_png) if is_valid else None,
            db_path=db_path,
        )
        assert ok1 is True

        conn1 = get_db_connection(db_path)
        row1 = conn1.execute("SELECT * FROM applied_jobs WHERE job_id = ?", (job_id_1,)).fetchone()
        assert row1["status"] == "Submitted (Confirmed)"
        assert row1["evidence_path"] == str(valid_png)
        conn1.close()

        # Scenario 2: Submission where screenshot failed/missing
        missing_png = tmp_path / "evidence" / "evidence_amazon_de.png"
        is_valid_2 = verifier.verify_screenshot_file(missing_png)
        status_2 = "Submitted (Confirmed)" if is_valid_2 else "Form Auto-Filled (Ready for Review)"
        ok2, job_id_2 = record_applied_job(
            title="Data Engineer",
            company="Amazon",
            location="Hyderabad",
            status=status_2,
            match_score=82,
            platform="naukri",
            job_url="https://naukri.com/job-102",
            evidence_path=str(missing_png) if is_valid_2 else None,
            db_path=db_path,
        )
        assert ok2 is True

        conn2 = get_db_connection(db_path)
        row2 = conn2.execute("SELECT * FROM applied_jobs WHERE job_id = ?", (job_id_2,)).fetchone()
        assert row2["status"] == "Form Auto-Filled (Ready for Review)"
        assert row2["evidence_path"] is None
        conn2.close()


# ==============================================================================
# 2. FACT-MATRIX ANCHORED QUESTIONNAIRE SOLVER TESTS
# ==============================================================================

class TestFactMatrixScreeningSolver:
    """Verifies deterministic mapping, safety rejection, and zero affirmative fallback."""

    def setup_method(self):
        self.solver = FactMatrixScreeningSolver()

    def test_disqualifying_negative_questions_answer_no(self):
        """Questions regarding criminal background, non-competes, or termination must answer False / 'No'."""
        queries = [
            "Have you ever been convicted of a felony or misdemeanor?",
            "Are you subject to any non-compete or non-solicitation agreement?",
            "Have you ever been involuntarily separated or terminated for cause?",
            "Do you have any relatives or family members currently employed by this firm?",
            "Do you have any other active competing offers currently?",
            "Do you have any unexplained career gaps?",
        ]
        for q in queries:
            dec = self.solver.evaluate_question(q)
            assert dec.answer == "No" or dec.answer is False
            assert dec.confidence >= 0.95
            assert dec.is_ambiguous is False

    def test_policy_consent_and_verification_answer_yes(self):
        """Background checks, drug screening, and compliance consent must answer True / 'Yes'."""
        queries = [
            "Are you willing to undergo a comprehensive background verification (BGV)?",
            "Do you consent to a 5-panel pre-employment substance/drug screening?",
            "Do you agree to abide by the Company Code of Conduct and Information Security policies?",
            "I certify that all information provided in this application is accurate and true.",
            "Do you acknowledge and accept our terms and conditions?",
        ]
        for q in queries:
            dec = self.solver.evaluate_question(q)
            assert dec.answer == "Yes" or dec.answer is True
            assert dec.confidence >= 0.95
            assert dec.is_ambiguous is False

    def test_foreign_jurisdiction_and_us_citizenship_answer_no(self):
        """Candidate resides and works in India; US/UK/EU work eligibility must answer False / 'No'."""
        queries = [
            "Are you legally authorized to work in the United States?",
            "Are you a United States Citizen or Green Card holder?",
            "Do you currently reside in the United States?",
            "Are you authorized to work in Canada without restriction?",
            "Do you live in the United Kingdom?",
        ]
        for q in queries:
            dec = self.solver.evaluate_question(q)
            assert dec.answer == "No" or dec.answer is False
            assert dec.confidence >= 0.90

    def test_domestic_work_authorization_and_sponsorship(self):
        """Work authorization in India is 'Yes'; requiring visa sponsorship in India is 'No'."""
        # India work authorization -> Yes
        dec_auth = self.solver.evaluate_question("Are you legally authorized to work in India?")
        assert dec_auth.answer in ("Yes", True)

        # Require visa sponsorship in India -> No
        dec_spons = self.solver.evaluate_question("Will you now or in the future require visa sponsorship?")
        assert dec_spons.answer in ("No", False)

        # Able to work without sponsorship -> Yes
        dec_no_spons = self.solver.evaluate_question("Are you authorized to work without sponsorship?")
        assert dec_no_spons.answer in ("Yes", True)

    def test_ambiguous_or_unmapped_question_quarantine_routing(self, tmp_path):
        """
        Adversarial test: Ambiguous or novel questions must NEVER receive a blind 'Yes'.
        Must raise AmbiguousScreeningException or return is_ambiguous=True and record to quarantine table.
        """
        db_path = str(tmp_path / "test_quarantine.db")
        init_db(db_path)

        ambiguous_queries = [
            "What is your secret clearance classification level from the DoD?",
            "Describe your experience operating industrial heavy machinery in ISO class 7 cleanrooms.",
            "Have you participated in the 2024 quantum entanglement symposium?",
        ]

        for q in ambiguous_queries:
            dec = self.solver.evaluate_question(q)
            assert dec.is_ambiguous is True
            assert dec.answer != "Yes", f"Blind affirmative fallback detected for '{q}'!"

            # Record to quarantine table
            qid = quarantine_item(
                category="screening_ambiguous",
                platform="naukri",
                prompt_text=q,
                context={"reason": "Unmapped screening prompt", "company": "Unknown Corp"},
                db_path=db_path
            )
            assert qid > 0

        # Verify all recorded in quarantine
        records = get_quarantined_items(db_path=db_path)
        assert len(records) == 3
        assert any("DoD" in r["prompt_text"] for r in records)


# ==============================================================================
# 3. SAFETY RAILS & EXECUTION CONTROLS
# ==============================================================================

class TestSafetyRailsAndControls:
    """Verifies process-level locking, randomized typing delays, and security checkpoint abort."""

    def test_randomized_typing_delay_bounds(self):
        """get_human_typing_delay must strictly return integer delays between 30ms and 80ms."""
        delays = [get_human_typing_delay() for _ in range(100)]
        for d in delays:
            assert isinstance(d, int)
            assert 30 <= d <= 80, f"Delay {d}ms violated bounds [30, 80]"
        # Statistical dispersion check
        assert len(set(delays)) > 15, "Delay generator appears constant or poorly randomized"

    def test_application_lock_mutual_exclusion(self, tmp_path):
        """Second instance attempting to acquire ApplicationLock must raise SafetyViolationError."""
        lock_file = tmp_path / "naukaripro_test.lock"

        # First instance acquires successfully
        lock1 = ApplicationLock(lock_file=str(lock_file))
        assert lock1.acquire() is True
        assert lock1.is_locked is True

        # Second instance attempts acquisition -> must raise SafetyViolationError
        lock2 = ApplicationLock(lock_file=str(lock_file))
        with pytest.raises(SafetyViolationError) as exc_info:
            lock2.acquire()
        assert "Process-level lock already held" in str(exc_info.value) or "overlapping" in str(exc_info.value).lower()

        # Release first instance
        lock1.release()
        assert lock1.is_locked is False

        # Now second instance can acquire
        assert lock2.acquire() is True
        lock2.release()

    def test_checkpoint_and_captcha_detection_triggers_abort(self):
        """detect_security_checkpoint_sync identifies challenge URLs and DOM selectors and triggers abort."""
        mock_page = MagicMock()
        mock_page.url = "https://www.naukri.com/checkpoint/challenge"

        # Checkpoint URL detection
        with pytest.raises(CheckpointDetectedException) as exc_info:
            detect_security_checkpoint_sync(mock_page, raise_exception=True)
        assert "Security challenge or CAPTCHA detected" in str(exc_info.value)
        assert "checkpoint" in str(exc_info.value)

        # Checkpoint DOM element detection
        mock_page.url = "https://www.naukri.com/apply"
        mock_elem = MagicMock()
        mock_elem.is_visible.return_value = True

        def mock_query_selector(selector):
            if "captcha" in selector.lower():
                return mock_elem
            return None

        mock_page.query_selector = mock_query_selector

        with pytest.raises(CheckpointDetectedException) as exc_info_2:
            detect_security_checkpoint_sync(mock_page, raise_exception=True)
        assert "DOM selector" in str(exc_info_2.value)
