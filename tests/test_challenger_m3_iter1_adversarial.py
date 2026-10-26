"""
Empirical Adversarial Challenge Suite: Milestone 3 Iteration 1
Autonomous LinkedIn Easy Apply Engine (Features 9-15)

Adversarially challenges:
1. Modal FSM & Step classification across varied DOM mock layouts
2. Auto-heal 2-attempt rule, error recovery, and clean discard without saving drafts on attempt 3
3. Radio option matching substring collisions ("no" in "technology", "innovation", "knowledge")
4. Standalone consent and certification checkboxes
5. Screening solver negative guards with adversarial phrasing
6. Integer vs float YOE conversion and HTML5 numeric validation compliance
"""

import os
import re
import asyncio
import functools
import inspect
from unittest.mock import MagicMock, AsyncMock, patch, call
import pytest

from naukari_pro.modules.linkedin_bot import (
    ModalState,
    EasyApplySelectors,
    LinkedInResumeManager,
    LinkedInCircuitBreaker,
    LinkedInScreeningSolver,
    LinkedInEasyApplyBot,
    LinkedInEasyApplyNavigator,
    get_candidate_profile
)

def run_async(coro):
    @functools.wraps(coro)
    def wrapper(*args, **kwargs):
        return asyncio.run(coro(*args, **kwargs))
    return wrapper

def make_async_locator(count: int = 1, visible: bool = True, text: str = "", attr_map: dict = None):
    """Creates a deterministic async Playwright locator mock."""
    loc = MagicMock()
    loc.count = AsyncMock(return_value=count)
    loc.is_visible = AsyncMock(return_value=visible)
    loc.inner_text = AsyncMock(return_value=text)
    attr_map = attr_map or {}
    loc.get_attribute = AsyncMock(side_effect=lambda a: attr_map.get(a, None))
    loc.first = loc
    loc.last = loc
    loc.nth = MagicMock(return_value=loc)
    loc.click = AsyncMock(return_value=None)
    loc.check = AsyncMock(return_value=None)
    loc.uncheck = AsyncMock(return_value=None)
    loc.fill = AsyncMock(return_value=None)
    loc.is_checked = AsyncMock(return_value=False)
    loc.select_option = AsyncMock(return_value=None)
    
    # Sub-locator mock (e.g. loc.locator(...))
    sub_loc = MagicMock()
    sub_loc.count = AsyncMock(return_value=0)
    sub_loc.is_visible = AsyncMock(return_value=False)
    sub_loc.inner_text = AsyncMock(return_value="")
    sub_loc.first = sub_loc
    sub_loc.nth = MagicMock(return_value=sub_loc)
    loc.locator = MagicMock(return_value=sub_loc)
    return loc


# ==============================================================================
# CHALLENGE AREA 1: STEP CLASSIFICATION ACROSS VARIED DOM LAYOUTS
# ==============================================================================

@run_async
async def test_challenge_step_classification_null_or_empty_modal():
    """Adversarial 1.1: classify_step on None or empty modal returns TERMINAL_FAILED."""
    bot = LinkedInEasyApplyBot()
    assert await bot.classify_step(None) == ModalState.TERMINAL_FAILED
    
    empty_modal = MagicMock()
    empty_modal.locator = MagicMock(return_value=make_async_locator(count=0, visible=False))
    assert await bot.classify_step(empty_modal) == ModalState.STEP_QUESTIONS

@run_async
async def test_challenge_step_classification_submit_button_precedence():
    """Adversarial 1.2: Visible Submit button overrides headers and classifies as STEP_REVIEW."""
    bot = LinkedInEasyApplyBot()
    
    submit_loc = make_async_locator(count=1, visible=True, text="Submit application")
    header_loc = make_async_locator(count=1, visible=True, text="Screening Questions")
    
    modal = MagicMock()
    def modal_locator(sel):
        if any(s in sel for s in ["submit", "Submit"]):
            return submit_loc
        if any(h in sel for h in ["h3", "h4"]):
            return header_loc
        return make_async_locator(count=0, visible=False)
    modal.locator = MagicMock(side_effect=modal_locator)
    
    classification = await bot.classify_step(modal)
    assert classification == ModalState.STEP_REVIEW

@run_async
async def test_challenge_step_classification_varied_headers():
    """Adversarial 1.3: classify_step handles diverse real-world LinkedIn header texts."""
    bot = LinkedInEasyApplyBot()
    
    header_scenarios = [
        ("Contact info", ModalState.STEP_CONTACT),
        ("Primary Phone & Email Details", ModalState.STEP_CONTACT),
        ("Your Resume and Documents", ModalState.STEP_RESUME),
        ("Upload CV", ModalState.STEP_RESUME),
        ("Review your application", ModalState.STEP_REVIEW),
        ("Preview Application", ModalState.STEP_REVIEW),
        ("Additional Questions", ModalState.STEP_QUESTIONS),
        ("Work authorization & Experience", ModalState.STEP_QUESTIONS),
        ("Voluntary Self-Identification", ModalState.STEP_QUESTIONS),
    ]
    
    for header_text, expected_state in header_scenarios:
        h_loc = make_async_locator(count=1, visible=True, text=header_text)
        modal = MagicMock()
        def modal_loc(sel, h=h_loc):
            if any(h_sel in sel for h_sel in ["h3", "h4"]):
                return h
            return make_async_locator(count=0, visible=False)
        modal.locator = MagicMock(side_effect=modal_loc)
        
        result = await bot.classify_step(modal)
        assert result == expected_state, f"Failed for header: '{header_text}' -> Expected {expected_state}, got {result}"

@run_async
async def test_challenge_step_classification_element_fallback_without_header():
    """Adversarial 1.4: Fallback element inspection when heading text is absent or non-descriptive."""
    bot = LinkedInEasyApplyBot()
    
    # 1. No header, but file input present -> STEP_RESUME
    modal_resume = MagicMock()
    file_loc = make_async_locator(count=1, visible=True)
    modal_resume.locator = MagicMock(side_effect=lambda sel: file_loc if "input[type='file']" in sel or "jobs-document-upload" in sel else make_async_locator(count=0, visible=False))
    assert await bot.classify_step(modal_resume) == ModalState.STEP_RESUME
    
    # 2. No header, but tel input present -> STEP_CONTACT
    modal_contact = MagicMock()
    tel_loc = make_async_locator(count=1, visible=True)
    modal_contact.locator = MagicMock(side_effect=lambda sel: tel_loc if "input[type='tel']" in sel or "country" in sel else make_async_locator(count=0, visible=False))
    assert await bot.classify_step(modal_contact) == ModalState.STEP_CONTACT

@run_async
async def test_challenge_fsm_state_disconnection_in_execute_easy_apply():
    """
    Adversarial 1.5 (EMPIRICAL AUDIT):
    Tests whether bot.current_state properly reflects step transitions during execute_easy_apply.
    Reviewer 1 noted that classify_step is never invoked in execute_easy_apply, leaving
    bot.current_state in MODAL_MOUNTED until final review step.
    """
    bot = LinkedInEasyApplyBot()
    page = MagicMock()
    page.goto = AsyncMock(return_value=None)
    
    apply_btn = make_async_locator(count=1, visible=True, text="Easy Apply")
    submit_btn = make_async_locator(count=1, visible=True, text="Submit application")
    dismiss_btn = make_async_locator(count=1, visible=True, text="Dismiss")
    
    modal_elem = MagicMock()
    h_contact = make_async_locator(count=1, visible=True, text="Contact info")
    modal_elem.locator = MagicMock(side_effect=lambda sel: h_contact if "h3" in sel else submit_btn if "submit" in sel.lower() else make_async_locator(count=0, visible=False))
    
    modal_container = make_async_locator(count=1, visible=True)
    modal_container.first = modal_elem
    
    def page_loc(sel):
        if "jobs-apply-button" in sel:
            return apply_btn
        if "jobs-easy-apply-modal" in sel or "[data-test-modal]" in sel:
            return modal_container
        if "dismiss" in sel.lower():
            return dismiss_btn
        return make_async_locator(count=0, visible=False)
    page.locator = MagicMock(side_effect=page_loc)
    
    with patch("naukari_pro.modules.linkedin_apply.humanized_delay", AsyncMock()):
        res = await bot.execute_easy_apply(page=page, job_info={"job_id": "111", "title": "Dev", "company": "Co"}, dry_run=True)
    
    # REMEDIATION VERIFICATION:
    # bot.history is now populated by execute_easy_apply on each step transition!
    assert len(bot.history) > 0, "bot.history must record step transitions."
    assert bot.history[0]["step"] == 1
    assert bot.history[0]["state"] == ModalState.STEP_REVIEW.value


# ==============================================================================
# CHALLENGE AREA 2: AUTO-HEAL 2-ATTEMPT RULE AND CLEAN DISCARD (NO SAVE DRAFT)
# ==============================================================================

@run_async
async def test_challenge_auto_heal_exact_two_attempt_boundary():
    """
    Adversarial 2.1: Auto-heal must execute exactly 2 attempts (attempt 1 and 2),
    and when unhealed, must transition directly to clean discard on attempt 3 without saving draft.
    """
    bot = LinkedInEasyApplyBot(max_step_retries=2)
    
    err_loc = make_async_locator(count=1, visible=True, text="Please enter a valid numeric value")
    inv_input = make_async_locator(count=1, visible=True, attr_map={"type": "number"})
    inv_input.fill = AsyncMock(return_value=None)
    
    modal_elem = MagicMock()
    def modal_loc(sel):
        if "artdeco-inline-feedback--error" in sel:
            return err_loc
        if "input[aria-invalid='true']" in sel:
            return inv_input
        # Notice: When an inline error blocks advancement, Next button click fails to advance
        return make_async_locator(count=0, visible=False)
    modal_elem.locator = MagicMock(side_effect=modal_loc)
    
    modal_container = make_async_locator(count=1, visible=True)
    modal_container.first = modal_elem
    
    apply_btn = make_async_locator(count=1, visible=True, text="Easy Apply")
    dismiss_btn = make_async_locator(count=1, visible=True, text="Dismiss")
    discard_confirm_btn = make_async_locator(count=1, visible=True, text="Discard")
    save_draft_btn = make_async_locator(count=1, visible=True, text="Save draft")
    
    page = MagicMock()
    page.goto = AsyncMock(return_value=None)
    def page_loc(sel):
        if "jobs-apply-button" in sel:
            return apply_btn
        if "jobs-easy-apply-modal" in sel or "[data-test-modal]" in sel:
            return modal_container
        if "dismiss" in sel.lower():
            return dismiss_btn
        if "discard" in sel.lower():
            return discard_confirm_btn
        if "save" in sel.lower() or "draft" in sel.lower():
            return save_draft_btn
        return make_async_locator(count=0, visible=False)
    page.locator = MagicMock(side_effect=page_loc)
    
    with patch("naukari_pro.modules.linkedin_apply.humanized_delay", AsyncMock()):
        result = await bot.execute_easy_apply(page=page, job_info={"job_id": "222", "title": "Eng", "company": "Corp"}, dry_run=False)
    
    # 1. Verification of outcome
    assert result["success"] is False
    assert result["status"] == "DISCARDED_UNRESOLVABLE"
    
    # 2. Verification of exactly 2 auto-heal fill attempts (attempt 1 -> "2", attempt 2 -> "1")
    assert inv_input.fill.call_count == 2, f"Expected exactly 2 heal attempts, got {inv_input.fill.call_count}"
    assert inv_input.fill.call_args_list == [call("2"), call("1")], f"Incorrect fill progression: {inv_input.fill.call_args_list}"
    
    # 3. Verification of clean discard without saving draft
    assert dismiss_btn.click.called, "Dismiss button was not clicked"
    assert discard_confirm_btn.click.called, "Discard confirmation button was not clicked"
    assert not save_draft_btn.click.called, "CRITICAL VIOLATION: Save draft button was clicked!"
    assert bot.current_state == ModalState.TERMINAL_DISCARDED

@run_async
async def test_challenge_auto_heal_successful_recovery_on_attempt_2():
    """
    Adversarial 2.2: If validation errors clear on attempt 2, the bot successfully recovers and advances.
    """
    bot = LinkedInEasyApplyBot(max_step_retries=2)
    
    error_state = {"count": 1}
    def get_err_loc():
        cnt = error_state["count"]
        return make_async_locator(count=cnt, visible=(cnt > 0), text="Invalid value" if cnt > 0 else "")
    
    inv_input = make_async_locator(count=1, visible=True, attr_map={"type": "number"})
    
    async def mock_fill(val):
        if val == "1":  # Fixed on attempt 2
            error_state["count"] = 0
    inv_input.fill = AsyncMock(side_effect=mock_fill)
    
    submit_btn = make_async_locator(count=1, visible=True, text="Submit application")
    dismiss_btn = make_async_locator(count=1, visible=True, text="Dismiss")
    apply_btn = make_async_locator(count=1, visible=True, text="Easy Apply")
    
    modal_elem = MagicMock()
    def modal_loc(sel):
        if "artdeco-inline-feedback--error" in sel:
            return get_err_loc()
        if "input[aria-invalid='true']" in sel:
            return inv_input if error_state["count"] > 0 else make_async_locator(count=0, visible=False)
        if "submit" in sel.lower():
            # Submit becomes visible once error clears
            return submit_btn if error_state["count"] == 0 else make_async_locator(count=0, visible=False)
        return make_async_locator(count=0, visible=False)
    modal_elem.locator = MagicMock(side_effect=modal_loc)
    
    modal_container = make_async_locator(count=1, visible=True)
    modal_container.first = modal_elem
    
    page = MagicMock()
    page.goto = AsyncMock(return_value=None)
    def page_loc(sel):
        if "jobs-apply-button" in sel:
            return apply_btn
        if "jobs-easy-apply-modal" in sel or "[data-test-modal]" in sel:
            return modal_container
        if "dismiss" in sel.lower():
            return dismiss_btn
        # Ensure security checkpoint elements are absent
        return make_async_locator(count=0, visible=False)
    page.locator = MagicMock(side_effect=page_loc)
    
    with patch("naukari_pro.modules.linkedin_apply.humanized_delay", AsyncMock()):
        result = await bot.execute_easy_apply(page=page, job_info={"job_id": "333", "title": "Eng", "company": "Corp"}, dry_run=True)
    
    assert result["success"] is True
    assert result["status"] == "DRY_RUN_VERIFIED"
    assert inv_input.fill.call_count == 2

@run_async
async def test_challenge_auto_heal_premature_break_on_next_button_click():
    """
    Adversarial 2.3 (EMPIRICAL AUDIT OF AUTO-HEAL LOOP BUG):
    Demonstrates that in execute_easy_apply (lines 1569-1572), advance_step() is called
    and 'if advanced: healed = True; break' exits the retry loop immediately on attempt 1
    without verifying whether errors actually cleared, because advance_step returns True
    whenever a Next button exists to click.
    """
    bot = LinkedInEasyApplyBot(max_step_retries=2)
    
    # Validation error persists regardless of fill
    err_loc = make_async_locator(count=1, visible=True, text="Please enter valid number")
    inv_input = make_async_locator(count=1, visible=True, attr_map={"type": "number"})
    inv_input.fill = AsyncMock(return_value=None)
    next_btn = make_async_locator(count=1, visible=True, text="Next")
    next_btn.click = AsyncMock(return_value=None)
    
    modal_elem = MagicMock()
    def modal_loc(sel):
        if "artdeco-inline-feedback--error" in sel:
            return err_loc
        if "input[aria-invalid='true']" in sel:
            return inv_input
        if "next" in sel.lower():
            return next_btn
        return make_async_locator(count=0, visible=False)
    modal_elem.locator = MagicMock(side_effect=modal_loc)
    
    modal_container = make_async_locator(count=1, visible=True)
    modal_container.first = modal_elem
    
    page = MagicMock()
    page.goto = AsyncMock(return_value=None)
    page.locator = MagicMock(side_effect=lambda sel: modal_container if "modal" in sel else make_async_locator(count=1, visible=True) if "apply" in sel else make_async_locator(count=0, visible=False))
    
    with patch("naukari_pro.modules.linkedin_apply.humanized_delay", AsyncMock()):
        # Run execute_easy_apply with max_steps=3
        res = await bot.execute_easy_apply(page=page, job_info={"job_id": "444", "title": "Dev", "company": "Co"}, dry_run=False, max_steps=3)
    
    # REMEDIATION VERIFICATION:
    # Auto-heal rechecks validation errors and aborts cleanly with DISCARDED_UNRESOLVABLE
    # after exactly 2 attempts instead of stalling across 12 steps.
    assert res["status"] == "DISCARDED_UNRESOLVABLE"
    assert inv_input.fill.call_count == 2  # Exactly 2 attempts executed on the step

@run_async
async def test_challenge_auto_heal_missing_aria_invalid_attribute_gap():
    """
    Adversarial 2.4 (EMPIRICAL AUDIT OF REVIEWER FINDING 5):
    LinkedIn ArtDeco often attaches error classes to the enclosing container without
    setting aria-invalid="true" on the <input>. Tests whether auto_heal_step finds elements.
    """
    bot = LinkedInEasyApplyBot()
    modal = MagicMock()
    
    # Input has NO aria-invalid attribute, but is inside an error container
    input_no_aria = make_async_locator(count=1, visible=True, attr_map={"type": "number"})
    input_no_aria.fill = AsyncMock(return_value=None)
    
    def modal_loc(sel):
        if "aria-invalid='true'" in sel:
            # Selector queries input[aria-invalid='true'] -> returns 0 elements!
            return make_async_locator(count=0, visible=False)
        return make_async_locator(count=0, visible=False)
    modal.locator = MagicMock(side_effect=modal_loc)
    
    healed = await bot.auto_heal_step(modal, attempt=1)
    assert healed is True
    assert input_no_aria.fill.call_count == 0, "Expected 0 fills because input lacked aria-invalid='true'."


# ==============================================================================
# CHALLENGE AREA 3: RADIO OPTION SUBSTRING COLLISION ("no" in "technology", etc.)
# ==============================================================================

@run_async
async def test_challenge_radio_matching_substring_collision_empirical_proof():
    """
    Adversarial 3.1 (CRITICAL EMPIRICAL BUG REPRODUCTION):
    Tests whether target_str == "no" falsely triggers on radio labels containing
    "technology", "innovation", "knowledge", "notice", or "economic" due to
    'if target_str in combined:' substring matching in linkedin_bot.py:921.
    """
    solver = LinkedInScreeningSolver()
    
    collision_words = [
        "Technology Engineering",
        "Continuous Innovation Team",
        "Knowledge Management",
        "Notice of Acceptance",
        "Economic Analysis Division",
    ]
    
    for word in collision_words:
        # Prompt requires a "No" answer
        prompt = "Do you require immigration sponsorship?"
        assert solver.determine_radio_answer(prompt) is False, "Solver must want 'No'"
        
        # Radio 0: Option containing the collision word (e.g. "Technology")
        # Radio 1: Option "No"
        radio_0 = make_async_locator(count=1, visible=True, text=word, attr_map={"value": "tech_val"})
        radio_0.check = AsyncMock(return_value=None)
        radio_0.locator = MagicMock(return_value=make_async_locator(count=1, visible=True, text=word))
        
        radio_1 = make_async_locator(count=1, visible=True, text="No", attr_map={"value": "no_val"})
        radio_1.check = AsyncMock(return_value=None)
        radio_1.locator = MagicMock(return_value=make_async_locator(count=1, visible=True, text="No"))
        
        radios_mock = MagicMock()
        radios_mock.count = AsyncMock(return_value=2)
        radios_mock.nth = MagicMock(side_effect=lambda idx: radio_0 if idx == 0 else radio_1)
        
        fieldset_mock = MagicMock()
        fieldset_mock.count = AsyncMock(return_value=1)
        fieldset_mock.is_visible = AsyncMock(return_value=True)
        fieldset_mock.nth = MagicMock(return_value=fieldset_mock)
        fieldset_mock.locator = MagicMock(side_effect=lambda sel: make_async_locator(count=1, visible=True, text=prompt) if "legend" in sel else radios_mock)
        
        modal = MagicMock()
        def modal_loc(sel):
            if "fieldset" in sel:
                return fieldset_mock
            return make_async_locator(count=0, visible=False)
        modal.locator = MagicMock(side_effect=modal_loc)
        
        handled = await solver.solve_all_questions_in_step(modal)
        
        # REMEDIATION VERIFICATION:
        # Word boundary regex prevents "no" from matching "Technology", "Innovation", etc.
        # Radio 1 ("No") is correctly clicked instead of Radio 0!
        assert not radio_0.check.called, (
            f"REMEDIATION VIOLATION: Radio 0 ('{word}') was falsely clicked for 'no'!"
        )
        assert radio_1.check.called, f"Radio 1 ('No') must be clicked for prompt '{prompt}'!"
        assert len(handled) == 1
        assert handled[0]["answer"] == "No"

def test_challenge_radio_matching_word_boundary_mitigation_proof():
    """
    Adversarial 3.2: Demonstrates that word-boundary regex r'\\bno\\b' prevents
    false positive matches on 'technology', 'innovation', 'knowledge', etc.
    """
    target = "no"
    regex = r"\b" + re.escape(target) + r"\b"
    
    test_cases = [
        ("technology platform", False),
        ("innovation division", False),
        ("knowledge worker", False),
        ("notice period", False),
        ("economic factor", False),
        ("no, i do not", True),
        ("no", True),
        ("No", True),
        ("NO", True),
        ("yes", False),
    ]
    
    for text, expected in test_cases:
        matched = bool(re.search(regex, text, re.IGNORECASE))
        assert matched == expected, f"Regex word boundary failed for text '{text}': expected {expected}, got {matched}"


# ==============================================================================
# CHALLENGE AREA 4: STANDALONE CONSENT & CERTIFICATION CHECKBOXES
# ==============================================================================

@run_async
async def test_challenge_standalone_checkboxes_omitted_in_solve_all_questions():
    """
    Adversarial 4.1 (EMPIRICAL AUDIT OF REVIEWER FINDING 2):
    Tests whether solve_all_questions_in_step processes standalone consent/certification checkboxes.
    """
    solver = LinkedInScreeningSolver()
    
    chk_consent = make_async_locator(count=1, visible=True, text="I consent to a background check")
    chk_consent.check = AsyncMock(return_value=None)
    
    modal = MagicMock()
    def modal_loc(sel):
        if "checkbox" in sel:
            return chk_consent
        return make_async_locator(count=0, visible=False)
    modal.locator = MagicMock(side_effect=modal_loc)
    
    handled = await solver.solve_all_questions_in_step(modal)
    
    # REMEDIATION VERIFICATION:
    # solve_all_questions_in_step now queries standalone consent/certification checkboxes!
    assert chk_consent.check.call_count == 1, (
        "Consent checkbox was not checked by solve_all_questions_in_step!"
    )
    assert len(handled) == 1
    assert handled[0]["type"] == "checkbox"
    assert handled[0]["answer"] is True

def test_challenge_solve_question_direct_checkbox_contract():
    """
    Adversarial 4.2: Direct solve_question helper correctly handles checkbox type.
    """
    bot = LinkedInEasyApplyBot()
    # Positive consent / certification
    assert bot.solve_question("I certify that all statements are true", input_type="checkbox") is True
    assert bot.solve_question("I agree to terms and conditions", input_type="checkbox") is True
    assert bot.solve_question("Consent to background verification", input_type="checkbox") is True
    
    # Negative disqualifying checkboxes
    assert bot.solve_question("I have a criminal conviction", input_type="checkbox") is False
    assert bot.solve_question("I am bound by an active non-compete", input_type="checkbox") is False
    assert bot.solve_question("I require sponsorship now or in the future", input_type="checkbox") is False


# ==============================================================================
# CHALLENGE AREA 5: SCREENING SOLVER NEGATIVE GUARDS WITH ADVERSARIAL PHRASING
# ==============================================================================

def test_challenge_negative_guards_disqualifying_queries():
    """
    Adversarial 5.1: Negative guards must return False for all disqualifying queries.
    """
    solver = LinkedInScreeningSolver()
    
    disqualifiers = [
        "Have you ever been convicted of a felony?",
        "Do you have any criminal convictions on your record?",
        "Have you been convicted of a misdemeanor or felony?",
        "Are you bound by an active non-compete clause?",
        "Are you bound by any restrictive covenant?",
        "Have you ever been terminated for cause?",
        "Have you ever faced disciplinary action from an employer?",
        "Do you require immigration sponsorship?",
        "Do you need visa sponsorship to work in India?",
        "Will you now or in the future require employer sponsorship?",
        "Will you require visa sponsorship for employment?",
        "Do you have a family member working at this company?",
        "Is any relative working at this organization?",
    ]
    
    for prompt in disqualifiers:
        ans = solver.determine_radio_answer(prompt)
        assert ans is False, f"Negative guard failed for disqualifier: '{prompt}' (returned {ans})"

def test_challenge_affirmative_qualifiers_positive_controls():
    """
    Adversarial 5.2: Affirmative qualifiers must return True for candidate ground truth.
    """
    solver = LinkedInScreeningSolver()
    
    affirmative_queries = [
        "Are you legally authorized to work in India?",
        "Do you have the right to work in India?",
        "Are you eligible to work in India without restrictions?",
        "Are you willing to relocate to Hyderabad?",
        "Are you comfortable with a hybrid / on-site work model?",
        "Are you willing to commute to the office?",
        "Do you consent to a standard background check?",
        "Do you agree to drug testing as part of onboarding?",
        "Do you certify that all information provided is accurate?",
        "Have you completed a Bachelor's degree in Engineering?",
        "Can you join within 15 days or immediately?",
        "Are you at least 18 years of age?",
        "Are you seeking full-time employment?",
    ]
    
    for prompt in affirmative_queries:
        ans = solver.determine_radio_answer(prompt)
        assert ans is True, f"Affirmative qualifier failed for prompt: '{prompt}' (returned {ans})"

def test_challenge_adversarial_phrasing_edge_cases():
    """
    Adversarial 5.3: Stress-tests complex, inverted, or subtle phrasing.
    """
    solver = LinkedInScreeningSolver()
    
    # 1. "noncompetition" without hyphen:
    ans_noncomp = solver.determine_radio_answer("Are you bound by a noncompetition agreement?")
    assert ans_noncomp is False, "Negative guard must catch 'noncompetition'"

    # 2. "disciplinary proceedings":
    ans_disc = solver.determine_radio_answer("Have you ever been subject to disciplinary proceedings?")
    assert ans_disc is False, "Negative guard must catch 'disciplinary proceedings'"

    # 3. "without requiring sponsorship":
    ans_without = solver.determine_radio_answer("Are you authorized to work in India without requiring employer sponsorship?")
    assert ans_without is True, "Affirmative qualifier must handle 'without requiring sponsorship'"


# ==============================================================================
# CHALLENGE AREA 6: INTEGER VS FLOAT YOE CONVERSION
# ==============================================================================

def test_challenge_yoe_integer_vs_float_conversion():
    """
    Adversarial 6.1: Validates integer_only=True rounds correctly to avoid HTML5 validation errors,
    while integer_only=False preserves calibrated decimals.
    """
    solver = LinkedInScreeningSolver()
    
    # 1. Total Experience: 2.5 YOE
    assert solver.get_numeric_experience_for_skill("General experience", integer_only=True) == "2"
    assert solver.get_numeric_experience_for_skill("General experience", integer_only=False) == "2.5"
    
    # 2. PySpark: 2.0 YOE (is_integer() is True)
    assert solver.get_numeric_experience_for_skill("PySpark", integer_only=True) == "2"
    assert solver.get_numeric_experience_for_skill("PySpark", integer_only=False) == "2"
    
    # 3. Python: 2.5 YOE
    assert solver.get_numeric_experience_for_skill("Python", integer_only=True) == "2"
    assert solver.get_numeric_experience_for_skill("Python", integer_only=False) == "2.5"
    
    # 4. Azure: 2.5 YOE
    assert solver.get_numeric_experience_for_skill("Azure", integer_only=True) == "2"
    assert solver.get_numeric_experience_for_skill("Azure", integer_only=False) == "2.5"
    
    # 5. Kafka: 1.5 YOE (round(1.5) in Python is 2 due to round-to-even)
    assert solver.get_numeric_experience_for_skill("Kafka", integer_only=True) == "2"
    assert solver.get_numeric_experience_for_skill("Kafka", integer_only=False) == "1.5"
    
    # 6. Terraform: 1.5 YOE
    assert solver.get_numeric_experience_for_skill("Terraform", integer_only=True) == "2"
    assert solver.get_numeric_experience_for_skill("Terraform", integer_only=False) == "1.5"
    
    # 7. ADF: 2.0 YOE
    assert solver.get_numeric_experience_for_skill("Azure Data Factory", integer_only=True) == "2"
    assert solver.get_numeric_experience_for_skill("Azure Data Factory", integer_only=False) == "2"

def test_challenge_determine_text_answer_numeric_input_handling():
    """
    Adversarial 6.2: determine_text_answer adheres to integer_only flag across fields.
    """
    solver = LinkedInScreeningSolver()
    
    # Notice Period
    assert solver.determine_text_answer("Notice period in days", integer_only=True) == "15"
    assert solver.determine_text_answer("Notice period (numeric)", integer_only=True) == "15"
    
    # CTC
    assert solver.determine_text_answer("Current CTC in LPA", integer_only=True) == "12"
    assert solver.determine_text_answer("Expected CTC in LPA", integer_only=True) == "20"
    
    # Years of experience via determine_text_answer
    assert solver.determine_text_answer("How many years of experience do you have with Databricks?", integer_only=True) == "2"
    assert solver.determine_text_answer("How many years of experience do you have with Python?", integer_only=True) == "2"
    assert solver.determine_text_answer("How many years of experience do you have with Python?", integer_only=False) == "2.5"

@run_async
async def test_challenge_html5_input_type_number_detection_in_solver():
    """
    Adversarial 6.3: solve_all_questions_in_step inspects input type attribute and sets integer_only=True
    for <input type='number'>, preventing HTML5 step mismatch errors.
    """
    solver = LinkedInScreeningSolver()
    
    label = make_async_locator(count=1, visible=True, text="Years of experience with SQL")
    
    num_input = make_async_locator(count=1, visible=True, attr_map={"type": "number", "id": "sql_yoe"})
    num_input.input_value = AsyncMock(return_value="")
    num_input.fill = AsyncMock(return_value=None)
    
    modal = MagicMock()
    def modal_loc(sel):
        if "input[type='number']" in sel:
            return num_input
        if "label[for='sql_yoe']" in sel:
            return label
        return make_async_locator(count=0, visible=False)
    modal.locator = MagicMock(side_effect=modal_loc)
    
    handled = await solver.solve_all_questions_in_step(modal)
    
    # SQL YOE is 2.5, but type='number' forces integer_only=True -> fills "2"
    assert len(handled) == 1
    assert handled[0]["answer"] == "2", f"Expected integer '2' for type='number', got {handled[0]['answer']}"
    assert num_input.fill.call_args == call("2")
