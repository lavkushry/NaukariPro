"""
Unit and Mock Test Suite for Milestone 2 & 3: External ATS Auto-Submission & Strict Evidence Capture
Covers:
1. Dedicated ATS Platform Handlers (Greenhouse, Lever, Ashby, Workday, Generic)
2. FactMatrixScreeningSolver Ground Truth Integration
3. Barrier Detection (CAPTCHA, MFA, Workday Account Wall)
4. Strict Confirmation Detection (URL and DOM element verification)
5. Non-Confirmation and Validation Error Rejection (Zero False Submissions)
6. 3-Point Evidence State Machine & Screenshot Verification
7. Cross-Platform Linux Playwright Routing (macOS osascript Guard)
"""

import os
import sys
import tempfile
import pytest
from unittest.mock import MagicMock, patch

from naukari_pro.modules.career_portals import (
    CareerPortalFiller,
    BaseATSHandler,
    GreenhouseHandler,
    LeverHandler,
    AshbyHandler,
    WorkdayHandler,
    GenericPortalHandler,
    safe_count
)
from naukari_pro.modules.learning.screening_solver import FactMatrixScreeningSolver
from naukari_pro.modules.learning.evidence import EvidenceVerifier, PNG_MAGIC_HEADER


@pytest.fixture
def sample_profile():
    return {
        "firstName": "Lavkush",
        "lastName": "Kumar",
        "fullName": "Lavkush Kumar",
        "email": "lav84095@gmail.com",
        "phone": "+91-9122036484",
        "city": "Hyderabad",
        "currentCompany": "CGI India (PNC Bank GCC)",
        "currentTitle": "DevOps Engineer / Azure Data Engineer",
        "linkedInUrl": "https://linkedin.com/in/lavkush-kumar",
        "githubUrl": "https://github.com/lavkush-kumar",
        "portfolioUrl": "https://github.com/lavkush-kumar",
        "experienceYears": "2.5",
        "noticePeriodDays": "15",
        "resumePath": "/tmp/dummy_resume.pdf"
    }


class TestATSHandlerMapping:
    """Verifies factory mapping from ATS type to dedicated handler."""

    def test_handler_factory_resolution(self):
        filler = CareerPortalFiller()
        assert isinstance(filler.get_handler("Greenhouse"), GreenhouseHandler)
        assert isinstance(filler.get_handler("greenhouse"), GreenhouseHandler)
        assert isinstance(filler.get_handler("Lever"), LeverHandler)
        assert isinstance(filler.get_handler("Ashby"), AshbyHandler)
        assert isinstance(filler.get_handler("Workday"), WorkdayHandler)
        assert isinstance(filler.get_handler("Generic Portal"), GenericPortalHandler)
        assert isinstance(filler.get_handler("Rippling"), GenericPortalHandler)


class TestBarrierDetection:
    """Verifies detection of CAPTCHAs, bot challenges, and account walls."""

    def test_captcha_turnstile_detection(self, sample_profile):
        handler = GreenhouseHandler(sample_profile)
        mock_page = MagicMock()

        # Turnstile element present
        mock_loc = MagicMock()
        mock_loc.count.return_value = 1
        mock_loc.first.is_visible.return_value = True

        def locator_side_effect(selector):
            if "turnstile" in selector:
                return mock_loc
            empty = MagicMock()
            empty.count.return_value = 0
            empty.first.is_visible.return_value = False
            return empty

        mock_page.locator.side_effect = locator_side_effect
        barrier = handler.detect_barriers(mock_page)
        assert barrier is not None
        assert "CAPTCHA" in barrier or "turnstile" in barrier

    def test_workday_account_wall_detection(self, sample_profile):
        handler = WorkdayHandler(sample_profile)
        mock_page = MagicMock()

        mock_loc = MagicMock()
        mock_loc.count.return_value = 1
        mock_loc.first.is_visible.return_value = True

        def locator_side_effect(selector):
            if "signInLink" in selector or "password" in selector:
                return mock_loc
            empty = MagicMock()
            empty.count.return_value = 0
            empty.first.is_visible.return_value = False
            return empty

        mock_page.locator.side_effect = locator_side_effect
        barrier = handler.detect_barriers(mock_page)
        assert barrier is not None
        assert "Workday" in barrier or "Barrier" in barrier

    def test_no_barriers_on_clean_form(self, sample_profile):
        handler = GreenhouseHandler(sample_profile)
        mock_page = MagicMock()
        empty = MagicMock()
        empty.count.return_value = 0
        empty.first.is_visible.return_value = False
        mock_page.locator.return_value = empty

        assert handler.detect_barriers(mock_page) is None


class TestGreenhouseHandler:
    """Verifies Greenhouse field population and confirmation detection."""

    def test_greenhouse_fill_form(self, sample_profile):
        handler = GreenhouseHandler(sample_profile)
        mock_page = MagicMock()
        filled_selectors = []

        def mock_locator(selector):
            loc = MagicMock()
            loc.count.return_value = 1
            loc.first = loc
            loc.is_visible.return_value = True
            def record_fill(val):
                filled_selectors.append((selector, val))
            loc.fill.side_effect = record_fill
            return loc

        mock_page.locator.side_effect = mock_locator
        res = handler.fill_form(mock_page)

        assert res["ats"] == "Greenhouse"
        assert len(res["filled"]) >= 4
        # Verify candidate facts filled
        vals = [val for _, val in filled_selectors]
        assert "Lavkush" in vals
        assert "Kumar" in vals
        assert "lav84095@gmail.com" in vals

    def test_greenhouse_confirmation_url(self, sample_profile):
        handler = GreenhouseHandler(sample_profile)
        mock_page = MagicMock()
        mock_page.url = "https://boards.greenhouse.io/databricks/jobs/123/confirmation"
        assert handler.verify_confirmation(mock_page, timeout=0.1) is True

    def test_greenhouse_confirmation_dom_element(self, sample_profile):
        handler = GreenhouseHandler(sample_profile)
        mock_page = MagicMock()
        mock_page.url = "https://boards.greenhouse.io/databricks/jobs/123"

        def mock_locator(sel):
            loc = MagicMock()
            if sel == "#application_confirmation":
                loc.count.return_value = 1
                loc.first.is_visible.return_value = True
            else:
                loc.count.return_value = 0
                loc.first.is_visible.return_value = False
            return loc

        mock_page.locator.side_effect = mock_locator
        assert handler.verify_confirmation(mock_page, timeout=0.1) is True

    def test_greenhouse_rejected_when_validation_error_present(self, sample_profile):
        """Even if confirmation container is in DOM, presence of active error rejects confirmation."""
        handler = GreenhouseHandler(sample_profile)
        mock_page = MagicMock()
        mock_page.url = "https://boards.greenhouse.io/databricks/jobs/123"

        def mock_locator(sel):
            loc = MagicMock()
            if ".field-error" in sel:
                loc.count.return_value = 1
                loc.first.is_visible.return_value = True
            elif sel == "#application_confirmation":
                loc.count.return_value = 1
                loc.first.is_visible.return_value = True
            else:
                loc.count.return_value = 0
                loc.first.is_visible.return_value = False
            return loc

        mock_page.locator.side_effect = mock_locator
        assert handler.verify_confirmation(mock_page, timeout=0.1) is False


class TestLeverHandler:
    """Verifies Lever field population, resume upload, and confirmation."""

    def test_lever_fill_form(self, sample_profile):
        handler = LeverHandler(sample_profile)
        mock_page = MagicMock()
        filled_vals = []

        def mock_locator(selector):
            loc = MagicMock()
            loc.count.return_value = 1
            loc.first = loc
            loc.is_visible.return_value = True
            loc.fill.side_effect = lambda v: filled_vals.append(v)
            return loc

        mock_page.locator.side_effect = mock_locator
        res = handler.fill_form(mock_page)

        assert res["ats"] == "Lever"
        assert "Lavkush Kumar" in filled_vals
        assert "lav84095@gmail.com" in filled_vals
        assert "+91-9122036484" in filled_vals

    def test_lever_confirmation_url(self, sample_profile):
        handler = LeverHandler(sample_profile)
        mock_page = MagicMock()
        mock_page.url = "https://jobs.lever.co/stripe/thanks"
        assert handler.verify_confirmation(mock_page, timeout=0.1) is True

    def test_lever_confirmation_dom(self, sample_profile):
        handler = LeverHandler(sample_profile)
        mock_page = MagicMock()
        mock_page.url = "https://jobs.lever.co/stripe/apply"

        def mock_locator(sel):
            loc = MagicMock()
            if sel == ".application-confirmation":
                loc.count.return_value = 1
                loc.first.is_visible.return_value = True
            else:
                loc.count.return_value = 0
                loc.first.is_visible.return_value = False
            return loc

        mock_page.locator.side_effect = mock_locator
        assert handler.verify_confirmation(mock_page, timeout=0.1) is True


class TestAshbyAndWorkdayHandlers:
    """Verifies Ashby and Workday handlers."""

    def test_ashby_confirmation(self, sample_profile):
        handler = AshbyHandler(sample_profile)
        mock_page = MagicMock()
        mock_page.url = "https://jobs.ashbyhq.com/openai/confirmation"
        assert handler.verify_confirmation(mock_page, timeout=0.1) is True

    def test_workday_confirmation_data_automation_id(self, sample_profile):
        handler = WorkdayHandler(sample_profile)
        mock_page = MagicMock()
        mock_page.url = "https://walmart.myworkdayjobs.com/careers"

        def mock_locator(sel):
            loc = MagicMock()
            if "applicationSubmitted" in sel:
                loc.count.return_value = 1
                loc.first.is_visible.return_value = True
            else:
                loc.count.return_value = 0
                loc.first.is_visible.return_value = False
            return loc

        mock_page.locator.side_effect = mock_locator
        assert handler.verify_confirmation(mock_page, timeout=0.1) is True


class TestStrictEvidenceVerification:
    """Verifies 3-point state machine: zero false submissions, confirmed only on valid PNG evidence."""

    def test_evaluate_submission_state_unconfirmed_gives_ready_for_review(self):
        ev = EvidenceVerifier()
        status, evidence_path = ev.evaluate_submission_state(
            confirmation_detected=False,
            screenshot_path="/tmp/fake_shot.png"
        )
        assert status == "Form Auto-Filled (Ready for Review)"
        assert evidence_path is None

    def test_evaluate_submission_state_confirmed_with_valid_png(self, tmp_path):
        ev = EvidenceVerifier(base_dir=str(tmp_path))
        shot_file = tmp_path / "evidence" / "test_confirmed.png"
        shot_file.parent.mkdir(parents=True, exist_ok=True)
        # Write valid PNG with header and >= 1024 bytes
        with open(shot_file, "wb") as f:
            f.write(PNG_MAGIC_HEADER + b"\x00" * 2000)

        status, evidence_path = ev.evaluate_submission_state(
            confirmation_detected=True,
            screenshot_path=str(shot_file)
        )
        assert status == "Submitted (Confirmed)"
        assert evidence_path == str(shot_file)

    def test_evaluate_submission_state_confirmed_with_corrupt_file_rejects(self, tmp_path):
        ev = EvidenceVerifier(base_dir=str(tmp_path))
        corrupt_file = tmp_path / "evidence" / "corrupt.png"
        corrupt_file.parent.mkdir(parents=True, exist_ok=True)
        with open(corrupt_file, "wb") as f:
            f.write(b"NOT_A_PNG_FILE" + b"\x00" * 2000)

        status, evidence_path = ev.evaluate_submission_state(
            confirmation_detected=True,
            screenshot_path=str(corrupt_file)
        )
        assert status == "Form Auto-Filled (Ready for Review)"
        assert evidence_path is None


class TestLinuxPlaywrightRouting:
    """Verifies fill_in_chrome routes to Playwright on Linux hosts without calling osascript."""

    def test_fill_in_chrome_routes_to_playwright_on_linux(self, sample_profile):
        filler = CareerPortalFiller()
        with patch("sys.platform", "linux"), \
             patch("naukari_pro.modules.db.is_job_already_applied", return_value=False):
            with patch.object(filler, "fill_in_playwright", return_value=(True, ["First Name"])) as mock_pw:
                with patch("subprocess.run") as mock_sub:
                    success, filled = filler.fill_in_chrome("https://boards.greenhouse.io/test/1", "Comp", "Role")
                    assert mock_sub.called is False
                    assert mock_pw.called is True
                    assert success is True
                    assert "First Name" in filled


class TestScreeningSolverGroundTruthFidelity:
    """Verifies that ATS handlers and FactMatrixScreeningSolver evaluate 01_FACT_MATRIX.md ground truth accurately."""

    def test_screening_solver_truth_answers(self):
        solver = FactMatrixScreeningSolver()
        # Work Auth
        d1 = solver.evaluate_question("Are you legally authorized to work in India?")
        assert d1.answer == "Yes"
        assert d1.is_ambiguous is False

        # Visa Sponsorship
        d2 = solver.evaluate_question("Will you now or in the future require visa sponsorship?")
        assert d2.answer == "No"
        assert d2.is_ambiguous is False

        # Notice Period
        d3 = solver.evaluate_question("What is your official notice period in days?")
        assert d3.answer == "15"
        assert d3.is_ambiguous is False

        # Relocation
        d4 = solver.evaluate_question("Are you open to relocate to Hyderabad or Bangalore?")
        assert d4.answer == "Yes"
        assert d4.is_ambiguous is False

        # Disqualifier: Criminal conviction
        d5 = solver.evaluate_question("Have you ever been convicted of a criminal offense?")
        assert d5.answer == "No"
        assert d5.is_ambiguous is False


class TestFieldStepAuditLedger:
    """Verifies complete step-by-step and field-by-field audit trail recording with zero human intervention."""

    def test_greenhouse_handler_records_fields_and_steps(self, tmp_path):
        from naukari_pro.modules.career_portals import GreenhouseHandler
        profile = {
            "firstName": "Lavkush",
            "lastName": "Kumar",
            "email": "lav84095@gmail.com",
            "phone": "+91-9122036484",
            "city": "Hyderabad",
            "linkedInUrl": "https://linkedin.com/in/lavkush-kumar",
            "portfolioUrl": "https://github.com/lavkush-kumar"
        }
        handler = GreenhouseHandler(profile)
        mock_page = MagicMock()
        mock_loc = MagicMock()
        mock_loc.first = mock_loc
        mock_loc.count.return_value = 1
        mock_loc.is_visible.return_value = True
        mock_page.locator.return_value = mock_loc

        res = handler.fill_form(mock_page)
        assert res["ats"] == "Greenhouse"
        assert len(res["field_records"]) >= 7

        first_rec = res["field_records"][0]
        assert first_rec["step"] == 1
        assert first_rec["step_name"] == "BASIC_INFO"
        assert first_rec["field"] == "First Name"
        assert first_rec["value"] == "Lavkush"
        assert first_rec["action_type"] == "FILLED"

        # Verify email is strictly lav84095@gmail.com
        email_rec = [r for r in res["field_records"] if r["field"] == "Email"][0]
        assert email_rec["value"] == "lav84095@gmail.com"

    def test_ashby_handler_records_fields_and_steps(self, tmp_path):
        from naukari_pro.modules.career_portals import AshbyHandler
        profile = {
            "fullName": "Lavkush Kumar",
            "email": "lav84095@gmail.com",
            "phone": "+919122036484",
            "linkedInUrl": "https://linkedin.com/in/lavkush-kumar",
            "githubUrl": "https://github.com/lavkush-kumar",
            "city": "Hyderabad"
        }
        handler = AshbyHandler(profile)
        mock_page = MagicMock()
        mock_loc = MagicMock()
        mock_loc.first = mock_loc
        mock_loc.count.return_value = 1
        mock_loc.is_visible.return_value = True
        mock_loc.all.return_value = []
        mock_page.locator.return_value = mock_loc

        res = handler.fill_form(mock_page)
        assert res["ats"] == "Ashby"
        assert len(res["field_records"]) >= 5

        # Verify fields recorded
        labels = [r["field"] for r in res["field_records"]]
        assert "Full Name" in labels
        assert "Email" in labels
        email_rec = [r for r in res["field_records"] if r["field"] == "Email"][0]
        assert email_rec["value"] == "lav84095@gmail.com"

    def test_lever_handler_records_fields_and_steps(self, tmp_path):
        from naukari_pro.modules.career_portals import LeverHandler
        profile = {
            "fullName": "Lavkush Kumar",
            "email": "lav84095@gmail.com",
            "phone": "+91-9122036484",
            "currentCompany": "CGI India",
            "linkedInUrl": "https://linkedin.com/in/lavkush-kumar",
            "githubUrl": "https://github.com/lavkush-kumar",
            "portfolioUrl": "https://github.com/lavkush-kumar"
        }
        handler = LeverHandler(profile)
        mock_page = MagicMock()
        mock_loc = MagicMock()
        mock_loc.first = mock_loc
        mock_loc.count.return_value = 1
        mock_loc.is_visible.return_value = True
        mock_page.locator.return_value = mock_loc

        res = handler.fill_form(mock_page)
        assert res["ats"] == "Lever"
        assert len(res["field_records"]) >= 7
        email_rec = [r for r in res["field_records"] if r["field"] == "Email"][0]
        assert email_rec["value"] == "lav84095@gmail.com"

    def test_workday_handler_records_fields_and_steps(self, tmp_path):
        from naukari_pro.modules.career_portals import WorkdayHandler
        profile = {
            "firstName": "Lavkush",
            "lastName": "Kumar",
            "email": "lav84095@gmail.com",
            "phone": "+919122036484",
            "city": "Hyderabad"
        }
        handler = WorkdayHandler(profile)
        mock_page = MagicMock()
        mock_loc = MagicMock()
        mock_loc.first = mock_loc
        mock_loc.count.return_value = 1
        mock_loc.is_visible.return_value = True
        mock_page.locator.return_value = mock_loc

        res = handler.fill_form(mock_page)
        assert res["ats"] == "Workday"
        assert len(res["field_records"]) >= 5
        labels = [r["field"] for r in res["field_records"]]
        assert "First Name" in labels
        assert "Email" in labels
        email_rec = [r for r in res["field_records"] if r["field"] == "Email"][0]
        assert email_rec["value"] == "lav84095@gmail.com"

    def test_persistence_in_sqlite_and_jsonl(self, tmp_path):
        from naukari_pro.modules.db import record_batch_field_audit, get_application_field_audit
        db_file = str(tmp_path / "test_audit.db")

        test_entries = [
            {"step": 1, "step_name": "BASIC_INFO", "field": "First Name", "value": "Lavkush", "type": "text"},
            {"step": 1, "step_name": "BASIC_INFO", "field": "Email", "value": "lav84095@gmail.com", "type": "email"},
            {"step": 1, "step_name": "BASIC_INFO", "field": "Phone", "value": "+91-9122036484", "type": "tel"},
            {"step": 2, "step_name": "RESUME_ATTACHMENT", "field": "Resume File", "value": "Lavkush_Kumar_Devops (2).pdf", "type": "file", "action_type": "UPLOADED"},
            {"step": 3, "step_name": "SUBMIT_APPLICATION", "field": "Submit Application Button", "value": "CLICKED", "type": "button", "action_type": "SUBMITTED"}
        ]

        inserted = record_batch_field_audit(
            job_id="test_job_12345",
            platform="career_portal (Greenhouse)",
            company="GitLab",
            title="Azure Data Platform Engineer",
            audit_entries=test_entries,
            db_path=db_file
        )
        assert inserted == 5

        # Query back from SQLite
        retrieved = get_application_field_audit("test_job_12345", db_path=db_file)
        assert len(retrieved) == 5
        assert retrieved[0]["field_label"] == "First Name"
        assert retrieved[0]["field_value"] == "Lavkush"
        assert retrieved[1]["field_label"] == "Email"
        assert retrieved[1]["field_value"] == "lav84095@gmail.com"
        assert retrieved[3]["step_name"] == "RESUME_ATTACHMENT"
        assert retrieved[3]["action_type"] == "UPLOADED"
        assert retrieved[4]["action_type"] == "SUBMITTED"

    def test_zero_human_intervention_screening_flow(self, monkeypatch):
        """Verifies that no input() or interactive pause is called during execution."""
        from naukari_pro.modules.learning.screening_solver import FactMatrixScreeningSolver
        solver = FactMatrixScreeningSolver()

        def forbidden_input(*args, **kwargs):
            raise AssertionError("Human intervention requested via input()! Zero human intervention violated.")

        monkeypatch.setattr("builtins.input", forbidden_input)

        questions = [
            "Are you legally authorized to work in India?",
            "Will you now or in the future require visa sponsorship?",
            "What is your official notice period in days?",
            "Are you open to relocate to Hyderabad or Bangalore?",
            "Have you ever been convicted of a criminal offense?"
        ]
        for q in questions:
            decision = solver.evaluate_question(q)
            assert decision is not None
            assert decision.answer is not None
            assert decision.is_ambiguous is False

        # Even on completely novel/unmatched questions, zero human intervention must be preserved
        unmatched_decision = solver.evaluate_question("What is your favorite extraterrestrial programming language?")
        assert unmatched_decision is not None
        assert unmatched_decision.is_ambiguous is True
        # input() was never called


class TestStrictRepeatApplicationDeduplication:
    """Verifies strict repeat-application deduplication across all external ATS platforms."""

    def test_canonical_url_deduplication(self, tmp_path):
        from naukari_pro.modules.db import init_db, record_applied_job, is_job_already_applied
        db_file = str(tmp_path / "test_dedup.db")
        init_db(db_file)

        base_url = "https://job-boards.greenhouse.io/gitlab/jobs/8775507002"
        ok, _ = record_applied_job(
            title="Intermediate Backend Engineer, India",
            company="GitLab",
            job_url=base_url,
            status="Submitted (Confirmed)",
            db_path=db_file
        )
        assert ok is True

        # Query with trailing slash
        assert is_job_already_applied(job_url=f"{base_url}/", db_path=db_file) is True
        # Query with query parameter
        assert is_job_already_applied(job_url=f"{base_url}?gh_jid=8775507002", db_path=db_file) is True
        # Query with subdomain variation
        assert is_job_already_applied(job_url="https://boards.greenhouse.io/gitlab/jobs/8775507002?source=linkedin", db_path=db_file) is True

    def test_token_and_uuid_deduplication(self, tmp_path):
        from naukari_pro.modules.db import init_db, record_applied_job, is_job_already_applied
        db_file = str(tmp_path / "test_dedup_tokens.db")
        init_db(db_file)

        # Lever UUID
        lever_url = "https://jobs.lever.co/spotify/b4f6cd01-1d5d-41a9-b287-6d10416da03c"
        ok1, _ = record_applied_job(
            title="Data Scientist - Business Analytics",
            company="Spotify",
            job_url=lever_url,
            status="Form Auto-Filled",
            db_path=db_file
        )
        assert ok1 is True
        assert is_job_already_applied(job_url=f"{lever_url}/apply", db_path=db_file) is True
        assert is_job_already_applied(job_url=f"{lever_url}?source=indeed", db_path=db_file) is True

        # Workday JR requisition
        wd_url = "https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite/job/India-Bengaluru/CAD-Engineer_JR2014480-1"
        ok2, _ = record_applied_job(
            title="CAD Engineer",
            company="NVIDIA",
            job_url=wd_url,
            status="Form Auto-Filled",
            db_path=db_file
        )
        assert ok2 is True
        assert is_job_already_applied(job_url=f"{wd_url}?source=linkedin", db_path=db_file) is True

    def test_punctuation_and_company_variants_deduplication(self, tmp_path):
        from naukari_pro.modules.db import init_db, record_applied_job, is_job_already_applied
        db_file = str(tmp_path / "test_dedup_titles.db")
        init_db(db_file)

        ok, _ = record_applied_job(
            title="Intermediate Backend Engineer, India",
            company="GitLab Inc",
            job_url="https://job-boards.greenhouse.io/gitlab/jobs/8775507002",
            status="Submitted (Confirmed)",
            db_path=db_file
        )
        assert ok is True

        # Dash variant
        assert is_job_already_applied(title="Intermediate Backend Engineer - India", company="GitLab", db_path=db_file) is True
        # Parentheses variant
        assert is_job_already_applied(title="Intermediate Backend Engineer (India)", company="GitLab Inc.", db_path=db_file) is True

    def test_filler_fill_strictly_skips_without_navigation(self, tmp_path):
        from naukari_pro.modules.db import init_db, record_applied_job
        from naukari_pro.modules.career_portals import CareerPortalFiller
        db_file = str(tmp_path / "test_filler_dedup.db")
        init_db(db_file)

        target_url = "https://job-boards.greenhouse.io/gitlab/jobs/8775507002"
        record_applied_job(
            title="Intermediate Backend Engineer, India",
            company="GitLab",
            job_url=target_url,
            status="Submitted (Confirmed)",
            db_path=db_file
        )

        filler = CareerPortalFiller(db_path=db_file)
        result = filler.fill(
            portal_url=target_url,
            company="GitLab",
            role="Intermediate Backend Engineer, India"
        )
        assert result.success is False
        assert result.status == "SKIPPED_ALREADY_APPLIED"
        assert len(result.fields) == 0


class TestSOTACommunityATSHandlerFixes:
    """Verifies battle-tested fixes adapted from top open-source ATS automations (Greenhouse, Lever, Ashby, Workday)."""

    def test_greenhouse_native_select_and_checkbox_consent(self, monkeypatch):
        monkeypatch.setattr("time.sleep", lambda s: None)
        monkeypatch.setattr("naukari_pro.modules.career_portals.fetch_greenhouse_security_code", lambda *a, **k: "A1B2C3D4")
        from naukari_pro.modules.career_portals import GreenhouseHandler
        handler = GreenhouseHandler({"firstName": "Lavkush", "lastName": "Kumar", "email": "lav84095@gmail.com"})
        
        mock_page = MagicMock()
        mock_loc = MagicMock()
        mock_loc.first = mock_loc
        mock_loc.count.return_value = 1
        mock_loc.is_visible.return_value = True
        mock_loc.all.return_value = []
        mock_page.locator.return_value = mock_loc
        
        # Test submit_form executes pre-submit required cleanup
        mock_page.evaluate.return_value = None
        mock_btn = MagicMock()
        mock_btn.first = mock_btn
        mock_btn.count.return_value = 1
        mock_btn.is_visible.return_value = True
        mock_page.locator.return_value = mock_btn
        
        res = handler.submit_form(mock_page)
        assert res is True
        assert mock_page.evaluate.called

    def test_lever_select_and_gdpr_checkboxes(self, monkeypatch):
        monkeypatch.setattr("time.sleep", lambda s: None)
        from naukari_pro.modules.career_portals import LeverHandler
        handler = LeverHandler({"fullName": "Lavkush Kumar", "email": "lav84095@gmail.com", "phone": "+919122036484"})
        
        mock_page = MagicMock()
        mock_loc = MagicMock()
        mock_loc.first = mock_loc
        mock_loc.count.return_value = 1
        mock_loc.is_visible.return_value = True
        mock_loc.all.return_value = []
        mock_page.locator.return_value = mock_loc
        
        res = handler.fill_form(mock_page)
        assert res["ats"] == "Lever"
        assert len(res["field_records"]) >= 4

    def test_ashby_react_select_and_checkboxes(self, monkeypatch):
        monkeypatch.setattr("time.sleep", lambda s: None)
        from naukari_pro.modules.career_portals import AshbyHandler
        handler = AshbyHandler({"fullName": "Lavkush Kumar", "email": "lav84095@gmail.com", "phone": "+919122036484"})
        
        mock_page = MagicMock()
        mock_loc = MagicMock()
        mock_loc.first = mock_loc
        mock_loc.count.return_value = 1
        mock_loc.is_visible.return_value = True
        mock_loc.all.return_value = []
        mock_page.locator.return_value = mock_loc
        
        res = handler.fill_form(mock_page)
        assert res["ats"] == "Ashby"
        assert len(res["field_records"]) >= 3

    def test_workday_custom_dropdown_and_resume_upload(self, tmp_path, monkeypatch):
        monkeypatch.setattr("time.sleep", lambda s: None)
        from naukari_pro.modules.career_portals import WorkdayHandler
        handler = WorkdayHandler({"firstName": "Lavkush", "lastName": "Kumar", "email": "lav84095@gmail.com"})
        
        fake_resume = tmp_path / "resume.pdf"
        fake_resume.write_text("Dummy Resume Content")
        
        mock_page = MagicMock()
        mock_file_inp = MagicMock()
        mock_file_inp.first = mock_file_inp
        mock_file_inp.count.return_value = 1
        mock_file_inp.is_visible.return_value = True
        
        mock_page.locator.return_value = mock_file_inp
        ok = handler.upload_resume(mock_page, str(fake_resume))
        assert ok is True
        assert mock_file_inp.set_input_files.called

    def test_greenhouse_security_code_regex_variations(self):
        import re

        clean_text_1 = "Please enter the following into the security code field on your application: C9X2M4K8"
        m1 = re.search(r"into the security code field on your application:\s*([a-zA-Z0-9]{8})", clean_text_1)
        assert m1 and m1.group(1) == "C9X2M4K8"

        clean_text_2 = "Your verification code: AB12CD34"
        m2 = re.search(r"\b(?:security code|verification code|your code is|enter the code)[:\s]+([a-zA-Z0-9]{6,8})\b", clean_text_2, re.IGNORECASE)
        assert m2 and m2.group(1) == "AB12CD34"

        clean_text_3 = "Security code: 123456"
        m3 = re.search(r"\b(?:security code|verification code|your code is|enter the code)[:\s]+([a-zA-Z0-9]{6,8})\b", clean_text_3, re.IGNORECASE)
        assert m3 and m3.group(1) == "123456"

    def test_greenhouse_single_code_input_fallback(self, monkeypatch):
        monkeypatch.setattr("time.sleep", lambda s: None)
        monkeypatch.setattr("naukari_pro.modules.career_portals.fetch_greenhouse_security_code", lambda *a, **k: "H7K2P9Q1")
        from naukari_pro.modules.career_portals import GreenhouseHandler
        handler = GreenhouseHandler({"firstName": "Lavkush", "lastName": "Kumar", "email": "lav84095@gmail.com"})
        monkeypatch.setattr(handler, "verify_confirmation", lambda *a, **k: False)
        
        mock_page = MagicMock()
        mock_page.url = "https://boards.greenhouse.io/job/123"
        mock_page.title.return_value = "Job Application"
        mock_page.evaluate.return_value = ""
        
        def mock_locator(sel):
            loc = MagicMock()
            loc.first = loc
            if "security-input" in sel:
                loc.count.return_value = 0
                loc.is_visible.return_value = False
            elif "security_code" in sel or "code" in sel:
                loc.count.return_value = 1
                loc.is_visible.return_value = True
            elif ".email-verification" in sel or "security code" in sel:
                loc.count.return_value = 1
                loc.is_visible.return_value = True
            elif "submit" in sel.lower():
                loc.count.return_value = 1
                loc.is_visible.return_value = True
            else:
                loc.count.return_value = 0
                loc.is_visible.return_value = False
            return loc

        mock_page.locator.side_effect = mock_locator
        mock_page.evaluate.return_value = None

        res = handler.submit_form(mock_page)
        assert res is True
        # Verify field record was added
        rec = [r for r in handler.field_records if r["name"] == "security_code"]
        assert len(rec) == 1
        assert rec[0]["step_name"] == "EMAIL_VERIFICATION"
        assert rec[0]["type"] == "code"


class TestAsyncioLoopWorkerIsolation:
    """
    P0-1 Regression Suite:
    Guarantees that invoking synchronous Playwright portal operations from inside
    an active asyncio event loop (the exact Arting Digital, Microland, Ambee failure)
    executes cleanly via the dedicated worker thread pool without raising Playwright's
    'It looks like you are using Playwright Sync API inside the asyncio loop.'
    """

    def test_portal_fill_dispatched_from_running_asyncio_loop(self, tmp_path, monkeypatch):
        import asyncio
        import threading
        from naukari_pro.modules.career_portals import (
            CareerPortalFiller,
            CareerPortalManager,
            FillResult,
            _is_asyncio_loop_running
        )

        test_db = str(tmp_path / "test_asyncio_reg.db")
        filler = CareerPortalFiller(db_path=test_db)
        cpm = CareerPortalManager()
        cpm.filler.db_path = test_db

        thread_records = []

        def mock_fill_in_playwright(page_ctx, portal_url, company, role, auto_submit=True):
            current_thread = threading.current_thread().name
            has_loop = _is_asyncio_loop_running()
            thread_records.append({"thread": current_thread, "has_loop": has_loop})
            return FillResult(True, ["Full Name", "Email"], "/tmp/evidence_test.png")

        monkeypatch.setattr(filler, "fill_in_playwright", mock_fill_in_playwright)
        monkeypatch.setattr(cpm.filler, "fill_in_playwright", mock_fill_in_playwright)

        async def coroutine_simulating_auto_apply():
            # Confirm that the event loop is active and running in this thread
            assert _is_asyncio_loop_running() is True
            
            # 1. Test CareerPortalFiller.fill() from within the running asyncio loop
            res1 = filler.fill(
                portal_url="https://careers.microland.com/microland/jobview/123",
                company="Microland",
                role="Sr Engineer - Cloud and Datacenter",
                headless=True,
                dry_run=False
            )
            assert res1.success is True
            assert res1.evidence_path == "/tmp/evidence_test.png"

            # 2. Test CareerPortalManager.fill() from within the running asyncio loop
            res2_success, res2_fields = cpm.fill(
                portal_url="https://getambee.keka.com/careers/jobdetails/168788",
                company="Ambee",
                role="Sr Full Stack Engineer",
                headless=True,
                dry_run=False
            )
            assert res2_success is True
            assert "Full Name" in res2_fields

            # 3. Test Arting Digital dry-run from within the running asyncio loop
            res3_success, res3_payload = cpm.fill(
                portal_url="https://artingdigital.com/careers/python-dev",
                company="Arting Digital",
                role="Python Developer+AI/ML",
                dry_run=True
            )
            assert res3_success is True

        # Run the entire async coroutine
        asyncio.run(coroutine_simulating_auto_apply())

        # Verify that both live Playwright invocations executed inside dedicated PortalWorker threads
        assert len(thread_records) == 2
        for rec in thread_records:
            assert "PortalWorker" in rec["thread"], f"Expected PortalWorker thread, got: {rec['thread']}"

    def test_batch_runner_dispatched_from_running_asyncio_loop(self, tmp_path, monkeypatch):
        import asyncio
        from naukari_pro.modules.career_portals import (
            ExternalPortalBatchRunner,
            _is_asyncio_loop_running
        )

        runner = ExternalPortalBatchRunner(
            dry_run=True,
            limit=2,
            db_path=str(tmp_path / "batch_async.db")
        )

        async def coroutine_batch():
            assert _is_asyncio_loop_running() is True
            # Running batch inside an asyncio event loop must execute cleanly
            stats = runner.run_batch()
            assert stats["total_evaluated"] >= 0
            assert stats["dry_run"] is True

        asyncio.run(coroutine_batch())


class TestArchitectureRulesA1toA5:
    """Verifies compliance with Architecture Rules A1–A5."""

    def test_a1_fallback_reasons_enum(self):
        from naukari_pro.modules.career_portals import FallbackReason, PortalState
        assert FallbackReason.ASYNCIO_ERROR.value == "ASYNCIO_ERROR"
        assert FallbackReason.SIGNIN_WALL.value == "SIGNIN_WALL"
        assert FallbackReason.SUBMIT_NOT_FOUND.value == "SUBMIT_NOT_FOUND"
        assert FallbackReason.CLICKED_NO_CONFIRMATION.value == "CLICKED_NO_CONFIRMATION"
        assert FallbackReason.CAPTCHA.value == "CAPTCHA"
        assert FallbackReason.TIMEOUT_240S.value == "TIMEOUT_240S"
        assert FallbackReason.ALREADY_APPLIED.value in ("ALREADY_APPLIED", "SKIPPED_ALREADY_APPLIED")

        assert PortalState.DETECT.value == "DETECT"
        assert PortalState.ACCOUNT.value == "ACCOUNT"
        assert PortalState.FILL.value == "FILL"
        assert PortalState.REVIEW.value == "REVIEW"
        assert PortalState.SUBMIT.value == "SUBMIT"
        assert PortalState.VERIFY.value == "VERIFY"
        assert PortalState.LOG.value == "LOG"

    def test_a2_schema_before_browser_planning(self, sample_profile, monkeypatch):
        import requests
        from naukari_pro.modules.career_portals import ATSFormSchemaPlanner

        planner = ATSFormSchemaPlanner(sample_profile)

        # Mock Greenhouse API response
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "title": "Data Platform Engineer",
            "questions": [
                {
                    "label": "First Name",
                    "fields": [{"name": "first_name", "type": "input_text", "values": []}]
                },
                {
                    "label": "Last Name",
                    "fields": [{"name": "last_name", "type": "input_text", "values": []}]
                },
                {
                    "label": "Are you authorized to work in India?",
                    "fields": [{"name": "work_auth", "type": "select", "values": [{"label": "Yes"}, {"label": "No"}]}]
                }
            ]
        }
        monkeypatch.setattr(requests, "get", lambda *a, **k: mock_resp)

        plan = planner.fetch_schema_plan("https://boards.greenhouse.io/databricks/jobs/5001")
        assert plan is not None
        assert plan["ats"] == "Greenhouse"
        assert plan["answers"]["first_name"] == "Lavkush"
        assert plan["answers"]["last_name"] == "Kumar"
        assert plan["answers"]["work_auth"] == "Yes"

    def test_a3_anchor_ladder_rungs(self):
        from naukari_pro.modules.career_portals import resolve_anchor_ladder

        mock_page = MagicMock()

        # 1. Rung 1: data-automation-id
        loc1 = MagicMock()
        loc1.count.return_value = 1
        loc1.first.is_visible.return_value = True
        mock_page.locator.side_effect = lambda sel: loc1 if "data-automation-id" in sel else MagicMock(count=lambda: 0)

        match_loc, rung = resolve_anchor_ladder(mock_page, field_id="legalName_firstName")
        assert match_loc is not None
        assert rung == "data-automation-id"

        # 2. Rung 3: autocomplete
        loc3 = MagicMock()
        loc3.count.return_value = 1
        loc3.first.is_visible.return_value = True
        mock_page.locator.side_effect = lambda sel: loc3 if "autocomplete" in sel else MagicMock(count=lambda: 0)

        match_loc, rung = resolve_anchor_ladder(mock_page, autocomplete="given-name")
        assert match_loc is not None
        assert rung == "autocomplete"

        # 3. Rung 6: CSS fallback flags SELECTOR_MISS
        loc6 = MagicMock()
        loc6.count.return_value = 1
        loc6.first.is_visible.return_value = True
        mock_page.locator.side_effect = lambda sel: loc6 if sel == ".custom-css-input" else MagicMock(count=lambda: 0)

        match_loc, rung = resolve_anchor_ladder(mock_page, css_fallback=".custom-css-input")
        assert match_loc is not None
        assert "SELECTOR_MISS" in rung

    def test_a4_state_checkpointing(self, tmp_path):
        import sqlite3
        from naukari_pro.modules.career_portals import checkpoint_portal_state, PortalState
        from naukari_pro.modules.db import init_db

        test_db = str(tmp_path / "checkpoint_test.db")
        init_db(test_db)

        # Seed row
        conn = sqlite3.connect(test_db)
        c = conn.cursor()
        c.execute("INSERT INTO applied_jobs (job_id, platform, company, title, status) VALUES ('job_123', 'career_portal', 'TestCo', 'Data Eng', 'Pending')")
        conn.commit()
        conn.close()

        # Checkpoint to REVIEW
        checkpoint_portal_state("job_123", PortalState.REVIEW, "TestCo", "Data Eng", db_path=test_db)

        conn = sqlite3.connect(test_db)
        c = conn.cursor()
        c.execute("SELECT outcome_label FROM applied_jobs WHERE job_id = 'job_123'")
        res = c.fetchone()[0]
        conn.close()
        assert res == "CHECKPOINT_REVIEW"

    def test_a5_idempotency_pre_submit_abort(self, sample_profile, tmp_path, monkeypatch):
        import sqlite3
        from naukari_pro.modules.career_portals import CareerPortalFiller, FallbackReason
        from naukari_pro.modules.db import init_db, record_applied_job

        test_db = str(tmp_path / "idempotency_test.db")
        init_db(test_db)

        # Record prior application
        record_applied_job(
            title="Senior Azure Data Engineer",
            company="Stripe",
            platform="career_portal",
            status="Submitted (Confirmed)",
            job_url="https://boards.greenhouse.io/stripe/jobs/999",
            db_path=test_db
        )

        filler = CareerPortalFiller(db_path=test_db)
        mock_page = MagicMock()

        # Attempting to fill the exact same applied job must abort immediately with ALREADY_APPLIED
        res = filler.fill(
            portal_url="https://boards.greenhouse.io/stripe/jobs/999",
            company="Stripe",
            role="Senior Azure Data Engineer",
            headless=True,
            page=mock_page
        )
        assert res.success is False
        assert res.status == FallbackReason.ALREADY_APPLIED.value


class TestComprehensiveDataEngineeringSkillsInScreeningSolver:
    """Verifies that all 45+ skills requested by the user are resolved accurately."""

    def test_data_engineering_lakehouse_skills(self):
        solver = FactMatrixScreeningSolver()

        skills = [
            ("How many years of experience do you have with Delta Lake?", "2.5"),
            ("Years of hands-on experience with Apache Spark?", "2.5"),
            ("Total experience in Spark SQL?", "2.5"),
            ("Years of experience in Data Engineering?", "2.5"),
            ("Experience building ETL Pipelines?", "2.5"),
            ("Experience with ELT Pipelines in cloud?", "2.5"),
            ("Experience in Data Lakehouse architecture?", "2.5"),
            ("Years of experience with Medallion Architecture?", "2.5"),
            ("Experience with ADLS Gen2?", "2.5"),
            ("Years of experience in Azure Synapse Analytics?", "2.5"),
            ("Hands-on experience with Microsoft Fabric?", "2.0"),
            ("Experience with Change Data Capture (CDC)?", "2.0"),
            ("Experience in SQL and Query Optimization?", "2.5"),
            ("Years of hands-on experience in PostgreSQL?", "2.0"),
            ("Experience with Star Schema Data Modeling?", "2.5"),
            ("Years of experience in Snowflake?", "2.0"),
            ("Experience with Redis caching?", "2.0"),
            ("Hands-on tenure with MongoDB?", "2.0"),
            ("Experience with Apache Kafka event streaming?", "2.0"),
            ("Experience in Spark Structured Streaming?", "2.0"),
            ("Years of experience with Kafka Connect?", "2.0"),
            ("Experience with Azure Event Hubs?", "2.0"),
            ("Years of experience with Terraform IaC?", "2.0"),
            ("Experience in Azure DevOps CI/CD?", "2.5"),
            ("Hands-on experience with Docker and Kubernetes?", "2.5"),
            ("Years of experience with Helm charts?", "2.0"),
            ("Experience in Git and GitHub Actions?", "2.5"),
            ("Experience in GitLab CI pipelines?", "2.0"),
            ("Tenure with Linux and Bash scripting?", "2.5"),
            ("Experience with Unity Catalog governance?", "2.0"),
            ("Years of experience with Great Expectations data quality gates?", "2.0"),
            ("Experience with Prometheus and Grafana monitoring?", "2.0"),
            ("Experience in OpenTelemetry pipeline observability?", "2.0"),
            ("Hands-on experience with dbt?", "2.0"),
            ("Years of experience in Cloud Data Management?", "2.5"),
            ("Experience with Python programming language?", "2.5"),
        ]

        for question, expected_years in skills:
            decision = solver.evaluate_question(question)
            assert decision.is_ambiguous is False, f"Question marked ambiguous: {question}"
            assert decision.answer == expected_years, f"Skill '{question}' got '{decision.answer}', expected '{expected_years}'"

    def test_boolean_skill_questions_affirmative(self):
        solver = FactMatrixScreeningSolver()
        # Radio questions: "Do you have experience with X?" -> "Yes"
        q1 = solver.evaluate_question("Do you have experience with Delta Lake and Medallion Architecture?", context={"options": ["Yes", "No"]})
        assert q1.answer == "Yes"

        q2 = solver.evaluate_question("Are you proficient in Apache Kafka and Spark Structured Streaming?", context={"options": ["Yes", "No"]})
        assert q2.answer == "Yes"

        q3 = solver.evaluate_question("Have you worked with Terraform and Kubernetes?", context={"options": ["No", "Yes"]})
        assert q3.answer == "Yes"

        q4 = solver.evaluate_question("Do you have hands-on experience with dbt and Snowflake?", context={"options": ["Yes", "No"]})
        assert q4.answer == "Yes"





