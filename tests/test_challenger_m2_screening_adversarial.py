"""
Milestone 2 Iteration 2 Adversarial Stress Test Suite: Screening Chatbot Solver
Authored by Challenger 1 (teamwork_preview_challenger_m2_iter2_1)

Empirically tests and stress-tests:
1. Text Question Mapping:
   - "Current CTC", "Expected CTC", "Notice Period", "Total Experience",
     "Highest Qualification", "Current Organization" across varied phrasings.
2. Radio Button Solver (Semantic affirmative vs disqualifying options):
   - "No" vs "Yes"
   - "Not Comfortable" vs "Comfortable" (disqualifying option containing affirmative substring)
   - "Disagree" vs "Agree"
   - "Uncomfortable" vs "Comfortable"
   - "Not Flexible" vs "Flexible"
   - Experience bracket radios ("2-3 years" matching 2.5 YOE)
3. Dropdown Solver:
   - Native <select> with affirmative and disqualifying options
   - Custom container dropdowns (.custom-select, div[role="combobox"], div.naukri-select)
4. Full Multi-turn Chatbot Drawer Flow in PlaywrightRunner.handle_chatbot
"""

import os
import sys
import pytest
from playwright.sync_api import sync_playwright

from naukari_pro.modules.auto_apply import (
    solve_screening_text_question,
    CURRENT_CTC,
    EXPECTED_CTC,
    NOTICE_PERIOD,
    EXPERIENCE_YEARS,
    PlaywrightRunner,
    SCREENING_RADIO_JS,
    SCREENING_DROPDOWN_JS,
)


# ==============================================================================
# 1. TEXT QUESTION MAPPING SUITE
# ==============================================================================

class TestScreeningTextQuestionMapping:
    """Verifies solve_screening_text_question ground-truth mappings and phrasing robustness."""

    def test_current_ctc_mapping(self):
        """Current CTC must map to configured candidate CTC (12.0 LPA)."""
        variations = [
            "Current CTC",
            "What is your Current CTC?",
            "Current CTC (in Lakhs)",
            "What is your present CTC?",
            "Fixed CTC",
            "Current salary in INR",
            "Present salary (LPA)",
            "In-hand CTC"
        ]
        for q in variations:
            ans = solve_screening_text_question(q)
            assert ans == str(CURRENT_CTC), f"Failed for query '{q}': got '{ans}', expected '{CURRENT_CTC}'"

    def test_expected_ctc_mapping(self):
        """Expected CTC must map to configured candidate expected CTC (20.0 LPA)."""
        variations = [
            "Expected CTC",
            "What is your Expected CTC?",
            "Expected CTC (in LPA)",
            "Desired CTC",
            "CTC expectation",
            "Salary expectation",
            "Expected salary in lakhs"
        ]
        for q in variations:
            ans = solve_screening_text_question(q)
            assert ans == str(EXPECTED_CTC), f"Failed for query '{q}': got '{ans}', expected '{EXPECTED_CTC}'"

    def test_notice_period_mapping(self):
        """Notice Period must map to configured notice period days (15)."""
        variations = [
            "Notice Period",
            "What is your Notice Period?",
            "Notice Period in days",
            "Notice days",
            "How soon can you join?",
            "Joining time (in days)",
            "Lead time to join"
        ]
        for q in variations:
            ans = solve_screening_text_question(q)
            assert ans == str(NOTICE_PERIOD), f"Failed for query '{q}': got '{ans}', expected '{NOTICE_PERIOD}'"

    def test_total_experience_mapping(self):
        """Total Experience must map to candidate total experience (2.5 years)."""
        variations = [
            "Total Experience",
            "What is your Total Experience?",
            "Total experience in years",
            "Overall experience",
            "Experience in years",
            "Years of experience",
            "Relevant experience in data engineering",
            "YOE"
        ]
        for q in variations:
            ans = solve_screening_text_question(q)
            assert ans == str(EXPERIENCE_YEARS), f"Failed for query '{q}': got '{ans}', expected '{EXPERIENCE_YEARS}'"

    def test_highest_qualification_mapping(self):
        """Highest Qualification must map to candidate degree."""
        variations = [
            "Highest Qualification",
            "What is your Highest Qualification?",
            "Highest degree",
            "Education qualification",
            "Graduation details",
            "Degree attained",
            "College / University degree"
        ]
        for q in variations:
            ans = solve_screening_text_question(q)
            assert ans == "B.Tech in Computer Science and Engineering", f"Failed for query '{q}': got '{ans}'"

    def test_current_organization_mapping(self):
        """Current Organization must map to current employer."""
        variations = [
            "Current Organization",
            "What is your Current Organization?",
            "Current company",
            "Current employer",
            "Present company",
            "Organization name",
            "Company name",
            "Present employer"
        ]
        for q in variations:
            ans = solve_screening_text_question(q)
            assert ans == "CGI India (PNC Bank GCC)", f"Failed for query '{q}': got '{ans}'"

    def test_adversarial_na_and_id_questions(self):
        """Optional NA/ID fields must resolve to 'NA', never '2.5' or numeric values."""
        na_queries = [
            "Mention NA if not applicable",
            "Employee ID of referrer",
            "Ex-employee ID",
            "Referral code if any"
        ]
        for q in na_queries:
            ans = solve_screening_text_question(q)
            assert ans == "NA", f"Failed for NA query '{q}': got '{ans}'"

    def test_notice_serving_status(self):
        """Serving notice question must map to 'No' (candidate is not actively serving)."""
        queries = [
            "Are you currently serving notice period?",
            "Serving notice?",
            "Are you on notice?"
        ]
        for q in queries:
            ans = solve_screening_text_question(q)
            assert ans == "No", f"Failed for notice query '{q}': got '{ans}'"

    def test_technical_skills_experience_duration(self):
        """Specific technical skill queries asking for years must return experience years."""
        assert solve_screening_text_question("How many years of experience do you have in PySpark?") == "2.5"
        assert solve_screening_text_question("Years of experience in Azure Databricks?") == "2.5"
        assert solve_screening_text_question("Tenure in Delta Lake ETL pipelines?") == "2.5"


@pytest.fixture(scope="module")
def browser_context():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


# ==============================================================================
# 2. RADIO BUTTON SOLVER ADVERSARIAL EMPIRICAL TESTS
# ==============================================================================

class TestScreeningRadioSolverAdversarial:
    """
    Stress-tests the radio button selection JS evaluate snippet executed in handle_chatbot.
    Evaluates whether disqualifying options ('Not Comfortable', 'Disagree', 'Uncomfortable')
    are incorrectly clicked due to affirmative substring matching.
    """

    def _eval_radio(self, page, question_text=""):
        """Executes the production radio solver JS evaluate code from auto_apply.py."""
        return page.evaluate(SCREENING_RADIO_JS, question_text)

    def test_radio_no_vs_yes(self, browser_context):
        """When options are 'No' vs 'Yes', solver must choose 'Yes'."""
        page = browser_context.new_page()
        page.set_content("""
        <div class="chatbot_Drawer" style="display:block; width:500px; height:500px;">
            <li class="botItem">Are you willing to relocate to Bengaluru?</li>
            <div class="singleSelectRadioButton">
                <label class="radio-label" id="r1"><input type="radio" name="opt" value="no">No</label>
                <label class="radio-label" id="r2"><input type="radio" name="opt" value="yes">Yes</label>
            </div>
        </div>
        """)
        res = self._eval_radio(page, "Are you willing to relocate to Bengaluru?")
        page.close()
        assert res["handled"] is True
        assert res["chosenText"] == "Yes"

    def test_radio_comfortable_when_first(self, browser_context):
        """When options are ['Comfortable', 'Not Comfortable'], solver chooses 'Comfortable'."""
        page = browser_context.new_page()
        page.set_content("""
        <div class="chatbot_Drawer" style="display:block; width:500px; height:500px;">
            <li class="botItem">Are you comfortable working hybrid?</li>
            <div class="singleSelectRadioButton">
                <label class="radio-label" id="r1"><input type="radio" name="opt" value="c">Comfortable</label>
                <label class="radio-label" id="r2"><input type="radio" name="opt" value="nc">Not Comfortable</label>
            </div>
        </div>
        """)
        res = self._eval_radio(page, "Are you comfortable working hybrid?")
        page.close()
        assert res["handled"] is True
        assert res["chosenText"] == "Comfortable"

    def test_radio_not_comfortable_when_first_adversarial(self, browser_context):
        """
        ADVERSARIAL STRESS TEST:
        When options are ['Not Comfortable', 'Comfortable'],
        the solver must choose the affirmative option ('Comfortable').
        If it selects 'Not Comfortable', the candidate is disqualified!
        """
        page = browser_context.new_page()
        page.set_content("""
        <div class="chatbot_Drawer" style="display:block; width:500px; height:500px;">
            <li class="botItem">Are you comfortable working in rotational shifts?</li>
            <div class="singleSelectRadioButton">
                <label class="radio-label" id="r1"><input type="radio" name="opt" value="nc">Not Comfortable</label>
                <label class="radio-label" id="r2"><input type="radio" name="opt" value="c">Comfortable</label>
            </div>
        </div>
        """)
        res = self._eval_radio(page, "Are you comfortable working in rotational shifts?")
        page.close()
        assert res["handled"] is True
        # EMPIRICAL ORACLE: Must choose 'Comfortable', NOT 'Not Comfortable'
        assert res["chosenText"] == "Comfortable", (
            f"Screening Radio Solver BUG: Selected disqualifying option '{res['chosenText']}' "
            "because 'not comfortable'.includes('comfortable') evaluated to true!"
        )

    def test_radio_disagree_when_first_adversarial(self, browser_context):
        """
        ADVERSARIAL STRESS TEST:
        When options are ['Disagree', 'Agree'], solver must choose 'Agree'.
        If it selects 'Disagree', candidate is disqualified.
        """
        page = browser_context.new_page()
        page.set_content("""
        <div class="chatbot_Drawer" style="display:block; width:500px; height:500px;">
            <li class="botItem">Do you agree to background verification?</li>
            <div class="singleSelectRadioButton">
                <label class="radio-label" id="r1"><input type="radio" name="opt" value="d">Disagree</label>
                <label class="radio-label" id="r2"><input type="radio" name="opt" value="a">Agree</label>
            </div>
        </div>
        """)
        res = self._eval_radio(page, "Do you agree to background verification?")
        page.close()
        assert res["handled"] is True
        assert res["chosenText"] == "Agree", (
            f"Screening Radio Solver BUG: Selected disqualifying option '{res['chosenText']}' "
            "because 'disagree'.includes('agree') evaluated to true!"
        )

    def test_radio_experience_bracket_selection(self, browser_context):
        """When given experience range brackets, solver must pick the 2-3 / 2.5 YOE bracket."""
        page = browser_context.new_page()
        page.set_content("""
        <div class="chatbot_Drawer" style="display:block; width:500px; height:500px;">
            <li class="botItem">Select your total years of experience</li>
            <div class="singleSelectRadioButton">
                <label class="radio-label" id="r1"><input type="radio" name="exp" value="0">0-1 Years</label>
                <label class="radio-label" id="r2"><input type="radio" name="exp" value="1">1-2 Years</label>
                <label class="radio-label" id="r3"><input type="radio" name="exp" value="2">2-3 Years</label>
                <label class="radio-label" id="r4"><input type="radio" name="exp" value="5">5+ Years</label>
            </div>
        </div>
        """)
        res = self._eval_radio(page, "Select your total years of experience")
        page.close()
        assert res["handled"] is True
        assert res["chosenText"] == "2-3 Years"


# ==============================================================================
# 3. DROPDOWN SOLVER ADVERSARIAL EMPIRICAL TESTS
# ==============================================================================

class TestScreeningDropdownSolverAdversarial:
    """
    Stress-tests Native <select> and Custom Container Dropdowns in handle_chatbot.
    """

    def _eval_dropdown(self, page):
        """Executes the production dropdown solver JS evaluate code from auto_apply.py."""
        return page.evaluate(SCREENING_DROPDOWN_JS)

    def test_native_select_no_vs_yes(self, browser_context):
        """Native <select> with No vs Yes selects 'Yes'."""
        page = browser_context.new_page()
        page.set_content("""
        <div class="chatbot_Drawer" style="display:block; width:500px; height:500px;">
            <li class="botItem">Are you willing to work from office?</li>
            <select id="sel" style="display:block; width:200px; height:40px;">
                <option value="">-- Select --</option>
                <option value="no">No</option>
                <option value="yes">Yes</option>
            </select>
        </div>
        """)
        res = self._eval_dropdown(page)
        page.close()
        assert res["handled"] is True
        assert res["type"] == "native_select"
        assert res["chosenText"] == "Yes"

    def test_native_select_not_comfortable_when_first_adversarial(self, browser_context):
        """
        ADVERSARIAL STRESS TEST:
        Native <select> with ['Not Comfortable', 'Comfortable'] must select 'Comfortable'.
        """
        page = browser_context.new_page()
        page.set_content("""
        <div class="chatbot_Drawer" style="display:block; width:500px; height:500px;">
            <li class="botItem">Are you comfortable with night shifts?</li>
            <select id="sel" style="display:block; width:200px; height:40px;">
                <option value="">-- Select --</option>
                <option value="nc">Not Comfortable</option>
                <option value="c">Comfortable</option>
            </select>
        </div>
        """)
        res = self._eval_dropdown(page)
        page.close()
        assert res["handled"] is True
        assert res["chosenText"] == "Comfortable", (
            f"Native Select Solver BUG: Selected disqualifying option '{res['chosenText']}' "
            "because 'not comfortable'.includes('comfortable') evaluated to true!"
        )

    def test_custom_dropdown_not_comfortable_when_first_adversarial(self, browser_context):
        """
        ADVERSARIAL STRESS TEST:
        Custom container dropdown with ['Not Comfortable', 'Comfortable'] must select 'Comfortable'.
        """
        page = browser_context.new_page()
        page.set_content("""
        <div class="chatbot_Drawer" style="display:block; width:500px; height:500px;">
            <li class="botItem">Are you comfortable working in rotational shifts?</li>
            <div class="custom-select" id="dd" style="display:block; width:200px; height:40px;">Select</div>
            <ul role="listbox" style="display:block;">
                <li role="option" style="display:block; width:200px; height:30px;">Not Comfortable</li>
                <li role="option" style="display:block; width:200px; height:30px;">Comfortable</li>
            </ul>
        </div>
        """)
        res = self._eval_dropdown(page)
        page.close()
        assert res["handled"] is True
        assert res["type"] == "custom_dropdown"
        assert res["chosenText"] == "Comfortable", (
            f"Custom Dropdown Solver BUG: Selected disqualifying option '{res['chosenText']}' "
            "because 'not comfortable'.includes('comfortable') evaluated to true!"
        )

    def test_custom_dropdown_disagree_when_first_adversarial(self, browser_context):
        """
        ADVERSARIAL STRESS TEST:
        Custom container dropdown with ['Disagree', 'Agree'] must select 'Agree'.
        """
        page = browser_context.new_page()
        page.set_content("""
        <div class="chatbot_Drawer" style="display:block; width:500px; height:500px;">
            <li class="botItem">Do you agree to company policies?</li>
            <div class="naukri-select" id="dd" style="display:block; width:200px; height:40px;">Select</div>
            <ul role="listbox" style="display:block;">
                <li role="option" style="display:block; width:200px; height:30px;">Disagree</li>
                <li role="option" style="display:block; width:200px; height:30px;">Agree</li>
            </ul>
        </div>
        """)
        res = self._eval_dropdown(page)
        page.close()
        assert res["handled"] is True
        assert res["chosenText"] == "Agree", (
            f"Custom Dropdown Solver BUG: Selected disqualifying option '{res['chosenText']}' "
            "because 'disagree'.includes('agree') evaluated to true!"
        )

    def test_custom_dropdown_notice_period(self, browser_context):
        """Custom container dropdown with notice options picks 15 days."""
        page = browser_context.new_page()
        page.set_content("""
        <div class="chatbot_Drawer" style="display:block; width:500px; height:500px;">
            <li class="botItem">Select Notice Period</li>
            <div class="custom-select" id="dd" style="display:block; width:200px; height:40px;">Select</div>
            <ul role="listbox" style="display:block;">
                <li role="option" style="display:block; width:200px; height:30px;">60 Days</li>
                <li role="option" style="display:block; width:200px; height:30px;">30 Days</li>
                <li role="option" style="display:block; width:200px; height:30px;">15 Days</li>
            </ul>
        </div>
        """)
        res = self._eval_dropdown(page)
        page.close()
        assert res["handled"] is True
        assert res["chosenText"] in ("15 Days", "30 Days")
