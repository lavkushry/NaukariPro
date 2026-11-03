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
        "email": "lavkushry@gmail.com",
        "phone": "+91-9122036484",
        "city": "Hyderabad",
        "currentCompany": "CGI India (PNC Bank GCC)",
        "currentTitle": "DevOps Engineer / Azure Data Engineer",
        "linkedInUrl": "https://linkedin.com/in/lavkushry",
        "githubUrl": "https://github.com/lavkushry",
        "portfolioUrl": "https://github.com/lavkushry",
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
        assert "lavkushry@gmail.com" in vals

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
        assert "lavkushry@gmail.com" in filled_vals
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
        with patch("sys.platform", "linux"):
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
