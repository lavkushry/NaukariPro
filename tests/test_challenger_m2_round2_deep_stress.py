"""
Milestone 2 Round 2 Deep Adversarial Stress Suite: Screening Chatbot Solvers
Authored by Challenger 1 (teamwork_preview_challenger_m2_round2_1)

Empirically challenges:
1. Radio solver:
   - Negative options with exact 'No' (without trailing space)
   - Radio inputs with default value='on' inside labels
   - 'Cannot relocate' vs 'Willing to relocate'
   - 'No shift work' vs 'Rotational shifts'
2. Native <select> and Custom Dropdowns:
   - Options starting with exact 'No' vs affirmative non-keyword options
   - Dropdown options where negative choice is listed first
3. Checkbox solver:
   - Multi-select checkboxes containing negative keyword phrases ('No knowledge of Azure')
4. Screening text question solver:
   - CTC variations: 'What is your CTC?', 'Your CTC', 'CTC', 'Annual CTC', 'Gross CTC'
   - Salary variations: 'What is your salary?', 'Salary', 'Annual Salary'
   - Notice variations: 'How many days notice?' (verifying no collision with 'how many' -> 2.5)
   - Experience variations: 'Experience (Years)', 'Years of Exp', 'Exp in years'
   - Contact & identity variations: 'Contact no', 'Name of applicant'
"""

import pytest
from playwright.sync_api import sync_playwright

from naukari_pro.modules.auto_apply import (
    solve_screening_text_question,
    CURRENT_CTC,
    EXPECTED_CTC,
    NOTICE_PERIOD,
    EXPERIENCE_YEARS,
    _CANDIDATE,
    SCREENING_RADIO_JS,
    SCREENING_DROPDOWN_JS,
    SCREENING_CHECKBOX_JS,
)


@pytest.fixture(scope="module")
def browser_context():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


# ==============================================================================
# 1. RADIO SOLVER ADVERSARIAL STRESS TESTS
# ==============================================================================

class TestRadioSolverAdversarialStress:
    """Stress tests radio solver with edge-case negative options and HTML value defaults."""

    def test_radio_exact_no_vs_rotational_shifts(self, browser_context):
        """
        When options are ['No', 'Rotational shifts'], solver must NOT select 'No'.
        Exposes Bug: 'negativeWords' uses 'no ' with trailing space, so exact 'No' is not filtered.
        """
        page = browser_context.new_page()
        page.set_content("""
        <div class="chatbot_Drawer">
            <li class="botItem">Are you comfortable working in rotational shifts?</li>
            <div class="singleSelectRadioButton">
                <label class="radio-label" id="r1"><input type="radio" name="opt" value="no">No</label>
                <label class="radio-label" id="r2"><input type="radio" name="opt" value="rotational">Rotational shifts</label>
            </div>
        </div>
        """)
        res = page.evaluate(SCREENING_RADIO_JS, "Are you comfortable working in rotational shifts?")
        c0 = page.evaluate('() => document.querySelectorAll("input[type=radio]")[0].checked')
        c1 = page.evaluate('() => document.querySelectorAll("input[type=radio]")[1].checked')
        page.close()

        assert res["handled"] is True
        assert c0 is False, "Defect: Disqualifying option 'No' was checked!"
        assert c1 is True, "Defect: Affirmative option 'Rotational shifts' was not checked!"
        assert res["chosenText"].lower() != "no"

    def test_radio_cannot_relocate_with_default_input_value(self, browser_context):
        """
        When options are ['Cannot relocate', 'Willing to relocate'] with default radio value ('on'),
        solver must NOT select 'Cannot relocate'.
        Exposes Bug: input[type="radio"] has value='on' which bypasses negative filter in fallback.
        """
        page = browser_context.new_page()
        page.set_content("""
        <div class="chatbot_Drawer">
            <li class="botItem">Are you open to relocation?</li>
            <div class="singleSelectRadioButton">
                <label class="radio-label" id="r1"><input type="radio" name="opt">Cannot relocate</label>
                <label class="radio-label" id="r2"><input type="radio" name="opt">Willing to relocate</label>
            </div>
        </div>
        """)
        res = page.evaluate(SCREENING_RADIO_JS, "Are you open to relocation?")
        c0 = page.evaluate('() => document.querySelectorAll("input[type=radio]")[0].checked')
        c1 = page.evaluate('() => document.querySelectorAll("input[type=radio]")[1].checked')
        page.close()

        assert res["handled"] is True
        assert c0 is False, "Defect: Disqualifying option 'Cannot relocate' was checked via value='on'!"
        assert c1 is True, "Defect: Option 'Willing to relocate' was not checked!"
        assert "cannot" not in res["chosenText"].lower()

    def test_radio_no_shift_work_vs_rotational_shifts(self, browser_context):
        """
        When options are ['No shift work', 'Rotational shifts'], solver must select 'Rotational shifts'.
        """
        page = browser_context.new_page()
        page.set_content("""
        <div class="chatbot_Drawer">
            <li class="botItem">Are you comfortable working in rotational shifts?</li>
            <div class="singleSelectRadioButton">
                <label class="radio-label" id="r1"><input type="radio" name="opt">No shift work</label>
                <label class="radio-label" id="r2"><input type="radio" name="opt">Rotational shifts</label>
            </div>
        </div>
        """)
        res = page.evaluate(SCREENING_RADIO_JS, "Are you comfortable working in rotational shifts?")
        c0 = page.evaluate('() => document.querySelectorAll("input[type=radio]")[0].checked')
        c1 = page.evaluate('() => document.querySelectorAll("input[type=radio]")[1].checked')
        page.close()

        assert res["handled"] is True
        assert c0 is False, "Defect: Disqualifying option 'No shift work' was checked!"
        assert c1 is True, "Defect: Option 'Rotational shifts' was not checked!"


# ==============================================================================
# 2. DROPDOWN SOLVER ADVERSARIAL STRESS TESTS
# ==============================================================================

class TestDropdownSolverAdversarialStress:
    """Stress tests native and custom dropdown solvers with edge-case negative options."""

    def test_native_select_exact_no_vs_rotational(self, browser_context):
        """
        When select options are ['-- Select --', 'No', 'Rotational shifts'],
        solver must NOT select 'No'.
        """
        page = browser_context.new_page()
        page.set_content("""
        <div class="chatbot_Drawer">
            <select>
                <option value="">-- Select --</option>
                <option value="no">No</option>
                <option value="rotational">Rotational shifts</option>
            </select>
        </div>
        """)
        res = page.evaluate(SCREENING_DROPDOWN_JS)
        val = page.evaluate('() => document.querySelector("select").value')
        page.close()

        assert res["handled"] is True
        assert val != "no", "Defect: Native select chose disqualifying option 'No'!"
        assert val == "rotational"

    def test_custom_dropdown_exact_no_vs_rotational(self, browser_context):
        """
        When custom dropdown options are ['No', 'Rotational shifts'],
        solver must NOT select 'No'.
        """
        page = browser_context.new_page()
        page.set_content("""
        <div class="chatbot_Drawer">
            <div class="custom-select">Select</div>
            <ul role="listbox">
                <li role="option">No</li>
                <li role="option">Rotational shifts</li>
            </ul>
        </div>
        """)
        res = page.evaluate(SCREENING_DROPDOWN_JS)
        page.close()

        assert res["handled"] is True
        assert res["chosenText"].lower() != "no", "Defect: Custom dropdown chose disqualifying option 'No'!"
        assert res["chosenText"] == "Rotational shifts"


# ==============================================================================
# 3. CHECKBOX SOLVER ADVERSARIAL STRESS TESTS
# ==============================================================================

class TestCheckboxSolverAdversarialStress:
    """Stress tests multi-select checkbox solver with negative keyword phrases."""

    def test_checkbox_does_not_click_negative_phrases(self, browser_context):
        """
        When options include 'I have no knowledge of Azure' and 'PySpark Production Experience',
        solver must only check 'PySpark', never the negative option.
        Exposes Bug: SCREENING_CHECKBOX_JS matches 'azure' substring without negative filter.
        """
        page = browser_context.new_page()
        page.set_content("""
        <div class="chatbot_Drawer">
            <div class="multicheckboxes-container">
                <label><input type="checkbox" name="cb">I have no knowledge of Azure</label>
                <label><input type="checkbox" name="cb">PySpark Production Experience</label>
            </div>
        </div>
        """)
        res = page.evaluate(SCREENING_CHECKBOX_JS)
        c0 = page.evaluate('() => document.querySelectorAll("input[type=checkbox]")[0].checked')
        c1 = page.evaluate('() => document.querySelectorAll("input[type=checkbox]")[1].checked')
        page.close()

        assert res["handled"] is True
        assert c0 is False, "Defect: Multi-select checkbox checked 'I have no knowledge of Azure'!"
        assert c1 is True, "Defect: Valid skill 'PySpark Production Experience' was not checked!"


# ==============================================================================
# 4. TEXT QUESTION SOLVER ADVERSARIAL STRESS TESTS
# ==============================================================================

class TestTextQuestionSolverAdversarialStress:
    """Stress tests solve_screening_text_question across realistic recruiter phrasings."""

    def test_ctc_shorthand_and_annual_variations(self):
        """Common CTC variations must return candidate CURRENT_CTC, never 'Yes'."""
        ctc_queries = [
            "What is your CTC?",
            "Your CTC",
            "CTC",
            "Annual CTC",
            "Gross CTC",
            "Total CTC"
        ]
        for q in ctc_queries:
            ans = solve_screening_text_question(q)
            assert ans == str(CURRENT_CTC), f"Defect: '{q}' returned '{ans}' instead of '{CURRENT_CTC}'"

    def test_salary_variations(self):
        """Salary variations must return candidate CURRENT_CTC, never 'Yes'."""
        salary_queries = [
            "What is your salary?",
            "Annual Salary",
            "Gross salary"
        ]
        for q in salary_queries:
            ans = solve_screening_text_question(q)
            assert ans == str(CURRENT_CTC), f"Defect: '{q}' returned '{ans}' instead of '{CURRENT_CTC}'"

    def test_notice_period_how_many_days_does_not_collide_with_experience(self):
        """
        'How many days notice?' must return NOTICE_PERIOD ('15'),
        NOT EXPERIENCE_YEARS ('2.5') via 'how many' fallback collision.
        """
        ans = solve_screening_text_question("How many days notice?")
        assert ans == str(NOTICE_PERIOD), f"Defect: 'How many days notice?' returned '{ans}' instead of '{NOTICE_PERIOD}'"

    def test_experience_bracket_text_variations(self):
        """Parenthesized or abbreviated experience questions must return EXPERIENCE_YEARS ('2.5')."""
        exp_queries = [
            "Experience (Years)",
            "Years of Exp",
            "Exp in years"
        ]
        for q in exp_queries:
            ans = solve_screening_text_question(q)
            assert ans == str(EXPERIENCE_YEARS), f"Defect: '{q}' returned '{ans}' instead of '{EXPERIENCE_YEARS}'"

    def test_contact_and_identity_variations(self):
        """Contact variations must return phone and name, never 'Yes'."""
        assert solve_screening_text_question("Contact no") == _CANDIDATE.get("phone", "+91 9122036484")
        assert solve_screening_text_question("Name of applicant") == _CANDIDATE.get("name", "Lavkush Kumar")
