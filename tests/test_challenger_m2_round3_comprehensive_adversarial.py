"""
Milestone 2 Round 3 Final Adversarial Verification Test Suite
Authored by Challenger 1 (teamwork_preview_challenger_m2_round3_1)

Adversarial Stress Scenarios:
1. Radio Solver Edge Cases:
   - ['No', 'Rotational shifts']
   - ['Cannot relocate', 'Willing to relocate']
   - ['Not willing to relocate', 'Open to relocation']
   - ['Inflexible with shift timings', 'Flexible hours']
   - ['Reluctant to travel', 'Willing to travel']
   - ['More than 30 days', '15 days', 'Immediate']
   - Uppercase & punctuation: ['NO.', 'ROTATIONAL SHIFTS']
   - Nested spans in label without radio value: <label><input type="radio"><span>Cannot relocate</span></label>
   - Experience brackets in radio: ['0-1 years', '2-3 years', '5+ years']

2. Native Select and Custom Dropdown Edge Cases:
   - ['-- Select --', 'Cannot relocate', 'Willing to relocate']
   - ['Select', 'No', 'Day shift', 'Night shift']
   - ['Choose', 'More than 30 days', '30 days', '15 days']
   - Custom combobox: ['Not comfortable', 'Comfortable']
   - Custom combobox: ['Disagree', 'Agree']
   - Custom dropdown: ['Cannot join immediately', 'Available within 15 days']
   - Custom dropdown with location: ['-- Select Location --', 'Hyderabad', 'Bengaluru']

3. Checkbox Solver Edge Cases:
   - Multi-select with negative phrases: 'No prior experience in Azure', 'Azure Data Factory'
   - 'I do not know Python', 'Python ETL', 'Kafka streaming'
   - 'Never used Databricks', 'Databricks Lakehouse'
   - 'Zero experience with SQL', 'SQL Server / PostgreSQL'
   - Single checkbox: 'I agree to terms'

4. Text Question Classifier (solve_screening_text_question) Edge Cases:
   - Comprehensive CTC variations (Current vs Expected)
   - Comprehensive Notice Period variations (Serving status vs Duration)
   - Comprehensive Experience variations (Bracketed, technical, hands-on, duration)
   - Identity & Contact variations (Applicant name vs Company name collision safety)
   - Highest qualification, location, mobility, and NA patterns
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
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        yield b
        b.close()


class TestAdversarialRadioScenarios:
    """Stress tests radio solver across nuanced and tricky option layouts."""

    def test_radio_rotational_shifts_vs_exact_no(self, browser):
        page = browser.new_page()
        page.set_content("""
        <div class="chatbot_Drawer">
            <li class="botItem">Are you comfortable working in rotational shifts?</li>
            <div class="singleSelectRadioButton">
                <label id="r1"><input type="radio" name="opt" value="no">No</label>
                <label id="r2"><input type="radio" name="opt" value="rotational">Rotational shifts</label>
            </div>
        </div>
        """)
        res = page.evaluate(SCREENING_RADIO_JS, "Are you comfortable working in rotational shifts?")
        c0 = page.evaluate('() => document.querySelectorAll("input[type=radio]")[0].checked')
        c1 = page.evaluate('() => document.querySelectorAll("input[type=radio]")[1].checked')
        page.close()
        assert res["handled"] is True
        assert c0 is False
        assert c1 is True
        assert res["chosenText"] == "Rotational shifts"

    def test_radio_cannot_relocate_vs_willing_to_relocate(self, browser):
        page = browser.new_page()
        page.set_content("""
        <div class="chatbot_Drawer">
            <li class="botItem">Relocation Preference</li>
            <div class="singleSelectRadioButton">
                <label><input type="radio" name="reloc">Cannot relocate</label>
                <label><input type="radio" name="reloc">Willing to relocate</label>
            </div>
        </div>
        """)
        res = page.evaluate(SCREENING_RADIO_JS, "Relocation Preference")
        c0 = page.evaluate('() => document.querySelectorAll("input[type=radio]")[0].checked')
        c1 = page.evaluate('() => document.querySelectorAll("input[type=radio]")[1].checked')
        page.close()
        assert res["handled"] is True
        assert c0 is False
        assert c1 is True
        assert "willing" in res["chosenText"].lower()

    def test_radio_not_willing_vs_open_to_relocation(self, browser):
        page = browser.new_page()
        page.set_content("""
        <div class="chatbot_Drawer">
            <li class="botItem">Are you open to relocation?</li>
            <div class="singleSelectRadioButton">
                <label><input type="radio" name="r">Not willing to relocate</label>
                <label><input type="radio" name="r">Open to relocation</label>
            </div>
        </div>
        """)
        res = page.evaluate(SCREENING_RADIO_JS, "Are you open to relocation?")
        c0 = page.evaluate('() => document.querySelectorAll("input[type=radio]")[0].checked')
        c1 = page.evaluate('() => document.querySelectorAll("input[type=radio]")[1].checked')
        page.close()
        assert res["handled"] is True
        assert c0 is False
        assert c1 is True
        assert "open" in res["chosenText"].lower()

    def test_radio_inflexible_vs_flexible_hours(self, browser):
        page = browser.new_page()
        page.set_content("""
        <div class="chatbot_Drawer">
            <li class="botItem">Working hours flexibility</li>
            <div class="singleSelectRadioButton">
                <label><input type="radio" name="f">Inflexible with shift timings</label>
                <label><input type="radio" name="f">Flexible hours</label>
            </div>
        </div>
        """)
        res = page.evaluate(SCREENING_RADIO_JS, "Working hours flexibility")
        c0 = page.evaluate('() => document.querySelectorAll("input[type=radio]")[0].checked')
        c1 = page.evaluate('() => document.querySelectorAll("input[type=radio]")[1].checked')
        page.close()
        assert res["handled"] is True
        assert c0 is False
        assert c1 is True
        assert "flexible" in res["chosenText"].lower()

    def test_radio_reluctant_vs_willing_to_travel(self, browser):
        page = browser.new_page()
        page.set_content("""
        <div class="chatbot_Drawer">
            <li class="botItem">Travel requirements</li>
            <div class="singleSelectRadioButton">
                <label><input type="radio" name="t">Reluctant to travel</label>
                <label><input type="radio" name="t">Willing to travel</label>
            </div>
        </div>
        """)
        res = page.evaluate(SCREENING_RADIO_JS, "Travel requirements")
        c0 = page.evaluate('() => document.querySelectorAll("input[type=radio]")[0].checked')
        c1 = page.evaluate('() => document.querySelectorAll("input[type=radio]")[1].checked')
        page.close()
        assert res["handled"] is True
        assert c0 is False
        assert c1 is True
        assert "willing" in res["chosenText"].lower()

    def test_radio_nested_span_without_value(self, browser):
        page = browser.new_page()
        page.set_content("""
        <div class="chatbot_Drawer">
            <div class="singleSelectRadioButton">
                <label><input type="radio" name="s"><span>No</span></label>
                <label><input type="radio" name="s"><span>Yes</span></label>
            </div>
        </div>
        """)
        res = page.evaluate(SCREENING_RADIO_JS, "Do you have valid passport?")
        c0 = page.evaluate('() => document.querySelectorAll("input[type=radio]")[0].checked')
        c1 = page.evaluate('() => document.querySelectorAll("input[type=radio]")[1].checked')
        page.close()
        assert res["handled"] is True
        assert c0 is False
        assert c1 is True
        assert res["chosenText"].lower() == "yes"

    def test_radio_notice_period_options(self, browser):
        page = browser.new_page()
        page.set_content("""
        <div class="chatbot_Drawer">
            <li class="botItem">Notice period</li>
            <div class="singleSelectRadioButton">
                <label><input type="radio" name="np">More than 30 days</label>
                <label><input type="radio" name="np">15 days</label>
                <label><input type="radio" name="np">Immediate</label>
            </div>
        </div>
        """)
        res = page.evaluate(SCREENING_RADIO_JS, "Notice period")
        c0 = page.evaluate('() => document.querySelectorAll("input[type=radio]")[0].checked')
        page.close()
        assert res["handled"] is True
        assert c0 is False
        assert res["chosenText"] in ("15 days", "Immediate")

    def test_radio_experience_bracket_selection(self, browser):
        page = browser.new_page()
        page.set_content("""
        <div class="chatbot_Drawer">
            <li class="botItem">Total Experience (Years)</li>
            <div class="singleSelectRadioButton">
                <label><input type="radio" name="exp">0-1 years</label>
                <label><input type="radio" name="exp">2-3 years</label>
                <label><input type="radio" name="exp">5+ years</label>
            </div>
        </div>
        """)
        res = page.evaluate(SCREENING_RADIO_JS, "Total Experience (Years)")
        c1 = page.evaluate('() => document.querySelectorAll("input[type=radio]")[1].checked')
        page.close()
        assert res["handled"] is True
        assert c1 is True
        assert "2-3" in res["chosenText"]


class TestAdversarialDropdownScenarios:
    """Stress tests native select and custom dropdowns."""

    def test_native_select_relocation(self, browser):
        page = browser.new_page()
        page.set_content("""
        <div class="chatbot_Drawer">
            <select>
                <option value="">-- Select --</option>
                <option value="no_reloc">Cannot relocate</option>
                <option value="yes_reloc">Willing to relocate</option>
            </select>
        </div>
        """)
        res = page.evaluate(SCREENING_DROPDOWN_JS)
        val = page.evaluate('() => document.querySelector("select").value')
        page.close()
        assert res["handled"] is True
        assert val == "yes_reloc"
        assert res["chosenText"] == "Willing to relocate"

    def test_native_select_notice_period(self, browser):
        page = browser.new_page()
        page.set_content("""
        <div class="chatbot_Drawer">
            <select>
                <option value="select">Select Option</option>
                <option value="90">More than 30 days</option>
                <option value="15">15 days</option>
            </select>
        </div>
        """)
        res = page.evaluate(SCREENING_DROPDOWN_JS)
        val = page.evaluate('() => document.querySelector("select").value')
        page.close()
        assert res["handled"] is True
        assert val == "15"
        assert res["chosenText"] == "15 days"

    def test_custom_combobox_disagree_vs_agree(self, browser):
        page = browser.new_page()
        page.set_content("""
        <div class="chatbot_Drawer">
            <div role="combobox" class="custom-select">Select</div>
            <ul role="listbox">
                <li role="option">Disagree</li>
                <li role="option">Agree</li>
            </ul>
        </div>
        """)
        res = page.evaluate(SCREENING_DROPDOWN_JS)
        page.close()
        assert res["handled"] is True
        assert res["chosenText"] == "Agree"

    def test_custom_dropdown_relocation(self, browser):
        page = browser.new_page()
        page.set_content("""
        <div class="chatbot_Drawer">
            <div class="naukri-select">Choose</div>
            <div class="dropdown-menu">
                <li class="optionItem">Cannot relocate</li>
                <li class="optionItem">Willing to relocate anywhere</li>
            </div>
        </div>
        """)
        res = page.evaluate(SCREENING_DROPDOWN_JS)
        page.close()
        assert res["handled"] is True
        assert "willing" in res["chosenText"].lower()


class TestAdversarialCheckboxScenarios:
    """Stress tests multi-select checkbox negative phrase rejection."""

    def test_multiple_negative_skills_rejection(self, browser):
        page = browser.new_page()
        page.set_content("""
        <div class="chatbot_Drawer">
            <div class="multicheckboxes-container">
                <label><input type="checkbox">No knowledge of Azure</label>
                <label><input type="checkbox">Azure Data Factory</label>
                <label><input type="checkbox">I do not know Python</label>
                <label><input type="checkbox">Python and PySpark</label>
                <label><input type="checkbox">Zero experience with SQL</label>
                <label><input type="checkbox">SQL and Delta Lake</label>
            </div>
        </div>
        """)
        res = page.evaluate(SCREENING_CHECKBOX_JS)
        states = page.evaluate('() => Array.from(document.querySelectorAll("input[type=checkbox]")).map(c => c.checked)')
        page.close()
        assert res["handled"] is True
        assert states[0] is False, "Defect: 'No knowledge of Azure' was checked!"
        assert states[1] is True, "'Azure Data Factory' should be checked"
        assert states[2] is False, "Defect: 'I do not know Python' was checked!"
        assert states[3] is True, "'Python and PySpark' should be checked"
        assert states[4] is False, "Defect: 'Zero experience with SQL' was checked!"
        assert states[5] is True, "'SQL and Delta Lake' should be checked"


class TestAdversarialTextClassificationScenarios:
    """Stress tests solve_screening_text_question across tricky phrasings."""

    def test_ctc_financial_variations(self):
        curr_ctc_str = str(CURRENT_CTC)
        exp_ctc_str = str(EXPECTED_CTC)

        # Current CTC questions
        assert solve_screening_text_question("Current CTC (LPA)") == curr_ctc_str
        assert solve_screening_text_question("Present CTC") == curr_ctc_str
        assert solve_screening_text_question("Fixed CTC") == curr_ctc_str
        assert solve_screening_text_question("Current remuneration") == curr_ctc_str
        assert solve_screening_text_question("Present salary package") == curr_ctc_str
        assert solve_screening_text_question("Current compensation package") == curr_ctc_str

        # Expected CTC questions
        assert solve_screening_text_question("Expected CTC (LPA)") == exp_ctc_str
        assert solve_screening_text_question("Desired CTC") == exp_ctc_str
        assert solve_screening_text_question("CTC Expectation") == exp_ctc_str
        assert solve_screening_text_question("Expected remuneration") == exp_ctc_str
        assert solve_screening_text_question("Expected compensation") == exp_ctc_str
        assert solve_screening_text_question("Expected package") == exp_ctc_str
        assert solve_screening_text_question("What salary are you looking for?") == exp_ctc_str

    def test_notice_period_vs_serving_status(self):
        np_str = str(NOTICE_PERIOD)

        # Notice duration questions
        assert solve_screening_text_question("Notice period (days)") == np_str
        assert solve_screening_text_question("Notice period in days?") == np_str
        assert solve_screening_text_question("Official notice period") == np_str
        assert solve_screening_text_question("Joining availability in days") == np_str
        assert solve_screening_text_question("Lead time to join") == np_str
        assert solve_screening_text_question("How soon can you join?") == np_str

        # Notice serving boolean questions
        assert solve_screening_text_question("Are you currently serving notice period?") == "No"
        assert solve_screening_text_question("Currently serving notice period?") == "No"
        assert solve_screening_text_question("Are you on notice?") == "No"

    def test_experience_variations_and_non_collisions(self):
        exp_str = str(EXPERIENCE_YEARS)

        # Duration/numeric experience questions
        assert solve_screening_text_question("Total Experience (Years)") == exp_str
        assert solve_screening_text_question("Relevant Experience (Years)") == exp_str
        assert solve_screening_text_question("Total YOE") == exp_str
        assert solve_screening_text_question("Overall Exp in Years") == exp_str
        assert solve_screening_text_question("How many years of experience in Azure?") == exp_str
        assert solve_screening_text_question("PySpark experience duration") == exp_str

        # Boolean technical skill questions
        assert "Yes, 2.5 years" in solve_screening_text_question("Do you have experience in Azure Databricks?")
        assert "Yes, 2.5 years" in solve_screening_text_question("Have you worked on Delta Lake?")
        assert "Yes, 2.5 years" in solve_screening_text_question("Do you know Apache Kafka?")

    def test_identity_and_organization_collision_safety(self):
        cand_name = _CANDIDATE.get("name", "Lavkush Kumar")
        cand_phone = _CANDIDATE.get("phone", "+91 9122036484")
        cand_email = _CANDIDATE.get("email", "lavkushry@gmail.com")
        cand_company = _CANDIDATE.get("current_company", "CGI India (PNC Bank GCC)")

        # Candidate identity
        assert solve_screening_text_question("Applicant Name") == cand_name
        assert solve_screening_text_question("Name of candidate") == cand_name
        assert solve_screening_text_question("Name of applicant") == cand_name
        assert solve_screening_text_question("Full Name") == cand_name
        assert solve_screening_text_question("Your Name") == cand_name

        # Company identity (must NOT collide with candidate name)
        assert solve_screening_text_question("Current Company") == cand_company
        assert solve_screening_text_question("Current Organization") == cand_company
        assert solve_screening_text_question("Present Employer") == cand_company
        assert solve_screening_text_question("Organization Name") == cand_company

        # Contact info
        assert solve_screening_text_question("Mobile Number") == cand_phone
        assert solve_screening_text_question("WhatsApp Number") == cand_phone
        assert solve_screening_text_question("Cell Phone") == cand_phone
        assert solve_screening_text_question("Email Address") == cand_email

    def test_education_location_and_na_patterns(self):
        assert "B.Tech" in solve_screening_text_question("Highest qualification")
        assert "B.Tech" in solve_screening_text_question("Highest Degree")
        assert "B.Tech" in solve_screening_text_question("Graduation details")
        assert solve_screening_text_question("Current City") == "Hyderabad"
        assert solve_screening_text_question("Are you open to relocate?") == "Yes"
        assert solve_screening_text_question("Employee ID (Mention NA if not applicable)") == "NA"
        assert solve_screening_text_question("Referral Code") == "NA"
