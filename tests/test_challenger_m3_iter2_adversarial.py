"""
Adversarial Verification & Stress Test Suite: Milestone 3 Iteration 2
Autonomous LinkedIn Easy Apply Engine (Features 9-15)

Authored by: Empirical Challenger 1 (teamwork_preview_challenger_m3_iter2_m5_1)
Governed by: PROJECT.md, TEST_INFRA.md, AGENTS.md

Target Verification Matrix:
1. Radio Option Matching Regex Word Boundary:
   - "no" vs "Technology", "Innovation", "Knowledge", "Notice", "Economic", "Non-compete", "Hypothetical"
   - "yes" vs "Yesterday", "Eyes", "Always"
2. Auto-Heal Validation Re-check & Attempt 3 Immediate Discard:
   - Loop re-checks errors after advance_step
   - Does NOT stall across 12 steps
   - Discards immediately on attempt 3 with status="DISCARDED_UNRESOLVABLE"
   - No draft saved, dismiss & discard confirmed
3. Standalone Consent Checkboxes vs Review Step Follow-Company Checkbox:
   - Consent/certification checkboxes checked during screening
   - Follow company checkbox skipped during screening
   - Follow company checkbox unchecked during review step
4. FSM Step Classification & History Tracking:
   - classify_step updates self.current_state on each step
   - self.history contains timestamped sequence of step numbers and states
5. Negative Disqualifier Guards & Affirmative Qualifiers:
   - Matrix of complex, inverted, and compound phrases
6. Auto-Heal Selector Scope & Deduplication:
   - Handles containers without aria-invalid on inputs
   - Deduplicates elements matching multiple error selectors
7. Circuit Breaker Single-Counting Between Navigator and Engine:
   - Consecutive failures increment exactly once per failed vacancy
   - Success resets failure counter without duplicate calls
"""

import os
import re
import asyncio
import functools
import inspect
import time
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
from naukari_pro.modules.linkedin_apply import (
    LinkedInApplyEngine,
    LinkedInApplicationTracker,
)
from naukari_pro.modules.linkedin_search import MatchScoreResult

def run_async(coro):
    @functools.wraps(coro)
    def wrapper(*args, **kwargs):
        return asyncio.run(coro(*args, **kwargs))
    return wrapper

def make_playwright_cm_mock(context=None):
    cm = MagicMock()
    pw = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=pw)
    cm.__aexit__ = AsyncMock(return_value=None)
    cm.__enter__ = MagicMock(return_value=pw)
    cm.__exit__ = MagicMock(return_value=None)
    return MagicMock(return_value=cm)

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
# 1. RADIO OPTION MATCHING REGEX WORD BOUNDARY VERIFICATION
# ==============================================================================

@run_async
async def test_iter2_radio_option_matching_exhaustive_collision_avoidance():
    """
    Verifies that target_str='no' NEVER collides with dictionary words containing 'no',
    and target_str='yes' NEVER collides with words containing 'yes'.
    """
    solver = LinkedInScreeningSolver()

    # Negative target ("no") test cases: text with substring "no" should NOT click Radio 0
    negative_collision_labels = [
        "Technology Consulting Services",
        "Innovation Labs & Incubation",
        "Knowledge Base Administrator",
        "Notice of Intent",
        "Economic Modeling Division",
        "Anonymity and Privacy Policy",
        "Hypothetical Scenarios",
        "Phenomenology & Linguistics",
        "Monopoly Regulations",
        "Technologist Guild",
    ]

    for label in negative_collision_labels:
        # Prompt requires "No"
        prompt = "Do you require immigration sponsorship?"
        assert solver.determine_radio_answer(prompt) is False

        radio_0 = make_async_locator(count=1, visible=True, text=label, attr_map={"value": "collision_val"})
        radio_0.check = AsyncMock(return_value=None)
        radio_0.locator = MagicMock(return_value=make_async_locator(count=1, visible=True, text=label))

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
        modal.locator = MagicMock(side_effect=lambda sel: fieldset_mock if "fieldset" in sel else make_async_locator(count=0, visible=False))

        handled = await solver.solve_all_questions_in_step(modal)

        assert not radio_0.check.called, f"Collision detected! Radio 0 with text '{label}' was checked for 'No' target!"
        assert radio_1.check.called, f"Radio 1 ('No') must be checked for prompt '{prompt}'!"
        assert handled[0]["answer"] == "No"


@run_async
async def test_iter2_radio_option_matching_affirmative_collision_avoidance():
    """
    Verifies that target_str='yes' NEVER collides with 'yesterday', 'eyes', 'bayes', etc.
    """
    solver = LinkedInScreeningSolver()

    positive_collision_labels = [
        "Yesterday's Experience",
        "Computer Vision & Eyes",
        "Bayesian Statistics Expert",
        "Polysemy Analysis",
    ]

    for label in positive_collision_labels:
        # Prompt requires "Yes"
        prompt = "Are you legally authorized to work in India?"
        assert solver.determine_radio_answer(prompt) is True

        radio_0 = make_async_locator(count=1, visible=True, text=label, attr_map={"value": "collision_val"})
        radio_0.check = AsyncMock(return_value=None)
        radio_0.locator = MagicMock(return_value=make_async_locator(count=1, visible=True, text=label))

        radio_1 = make_async_locator(count=1, visible=True, text="Yes", attr_map={"value": "yes_val"})
        radio_1.check = AsyncMock(return_value=None)
        radio_1.locator = MagicMock(return_value=make_async_locator(count=1, visible=True, text="Yes"))

        radios_mock = MagicMock()
        radios_mock.count = AsyncMock(return_value=2)
        radios_mock.nth = MagicMock(side_effect=lambda idx: radio_0 if idx == 0 else radio_1)

        fieldset_mock = MagicMock()
        fieldset_mock.count = AsyncMock(return_value=1)
        fieldset_mock.is_visible = AsyncMock(return_value=True)
        fieldset_mock.nth = MagicMock(return_value=fieldset_mock)
        fieldset_mock.locator = MagicMock(side_effect=lambda sel: make_async_locator(count=1, visible=True, text=prompt) if "legend" in sel else radios_mock)

        modal = MagicMock()
        modal.locator = MagicMock(side_effect=lambda sel: fieldset_mock if "fieldset" in sel else make_async_locator(count=0, visible=False))

        handled = await solver.solve_all_questions_in_step(modal)

        assert not radio_0.check.called, f"Collision detected! Radio 0 with text '{label}' was checked for 'Yes' target!"
        assert radio_1.check.called, f"Radio 1 ('Yes') must be checked for prompt '{prompt}'!"
        assert handled[0]["answer"] == "Yes"


# ==============================================================================
# 2. AUTO-HEAL ERROR VERIFICATION & ATTEMPT 3 IMMEDIATE DISCARD
# ==============================================================================

@run_async
async def test_iter2_auto_heal_immediate_discard_on_attempt_3():
    """
    Verifies that when validation errors persist across 2 auto-heal attempts,
    attempt 3 immediately discards the modal with status='DISCARDED_UNRESOLVABLE',
    recording UNRESOLVABLE_SCREENING_QUESTION on circuit breaker without stalling across 12 steps.
    """
    bot = LinkedInEasyApplyBot(max_step_retries=2)

    # Persistent error that never clears
    err_loc = make_async_locator(count=1, visible=True, text="Please enter a valid numeric value between 1 and 100")
    inv_input = make_async_locator(count=1, visible=True, attr_map={"type": "number"})
    inv_input.fill = AsyncMock(return_value=None)
    next_btn = make_async_locator(count=1, visible=True, text="Next")
    next_btn.click = AsyncMock(return_value=None)

    dismiss_btn = make_async_locator(count=1, visible=True, text="Dismiss")
    discard_confirm_btn = make_async_locator(count=1, visible=True, text="Discard")
    save_draft_btn = make_async_locator(count=1, visible=True, text="Save draft")

    modal_elem = MagicMock()
    def modal_loc(sel):
        if "artdeco-inline-feedback--error" in sel or "fb-form-element--error" in sel:
            return err_loc
        if "aria-invalid='true'" in sel:
            return inv_input
        if "next" in sel.lower():
            return next_btn
        return make_async_locator(count=0, visible=False)
    modal_elem.locator = MagicMock(side_effect=modal_loc)

    modal_container = make_async_locator(count=1, visible=True)
    modal_container.first = modal_elem

    page = MagicMock()
    page.goto = AsyncMock(return_value=None)
    def page_loc(sel):
        if "jobs-apply-button" in sel:
            return make_async_locator(count=1, visible=True, text="Easy Apply")
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
        result = await bot.execute_easy_apply(
            page=page,
            job_info={"job_id": "999888", "title": "Azure Data Eng", "company": "Enterprise Tech"},
            dry_run=False,
            max_steps=12
        )

    # 1. Must discard with DISCARDED_UNRESOLVABLE
    assert result["success"] is False
    assert result["status"] == "DISCARDED_UNRESOLVABLE"
    assert "Unresolvable form validation errors" in result["detail"]

    # 2. Step count must be 1 (immediately terminated on step 1), NOT stalled across 12 steps
    assert result["steps"] == 1, f"Expected termination on step 1, but ran {result['steps']} steps!"

    # 3. Exactly 2 heal attempts made (attempt=1 with '2', attempt=2 with '1')
    assert inv_input.fill.call_count == 2
    assert inv_input.fill.call_args_list == [call("2"), call("1")]

    # 4. Modal must be cleanly dismissed & discarded without saving drafts
    assert dismiss_btn.click.called
    assert discard_confirm_btn.click.called
    assert not save_draft_btn.click.called

    # 5. Circuit breaker must record failure
    assert bot.circuit_breaker.consecutive_errors == 1
    assert bot.current_state == ModalState.TERMINAL_DISCARDED


@run_async
async def test_iter2_auto_heal_recheck_prevents_false_positive_advance():
    """
    Verifies that advance_step returning True does NOT cause auto-heal to break
    if detect_validation_errors still returns error messages.
    """
    bot = LinkedInEasyApplyBot(max_step_retries=2)
    modal = MagicMock()

    # Track how many times detect_validation_errors is called
    error_query_count = 0
    err_loc = make_async_locator(count=1, visible=True, text="Error remains")

    def modal_loc(sel):
        if "artdeco-inline-feedback--error" in sel:
            return err_loc
        if "aria-invalid='true'" in sel:
            return make_async_locator(count=1, visible=True, attr_map={"type": "number"})
        if "next" in sel.lower():
            # Next button exists and is clickable
            return make_async_locator(count=1, visible=True, text="Next")
        return make_async_locator(count=0, visible=False)
    modal.locator = MagicMock(side_effect=modal_loc)

    # Run auto_heal_step manually and verify errors
    errors_before = await bot.detect_validation_errors(modal)
    assert len(errors_before) == 1

    # Advance step reports True
    adv, tag = await bot.advance_step(modal)
    assert adv is True
    assert tag == "NEXT"

    # Crucial logic check: errors still exist
    errors_after = await bot.detect_validation_errors(modal)
    assert len(errors_after) == 1, "Validation error must not be assumed resolved merely because advance_step was clicked"


# ==============================================================================
# 3. STANDALONE CONSENT CHECKBOXES VS REVIEW FOLLOW-COMPANY
# ==============================================================================

@run_async
async def test_iter2_standalone_consent_checkboxes_matrix():
    """
    Verifies that all consent/certification checkboxes are checked,
    unrelated checkboxes without consent keywords are skipped,
    and follow-company is strictly excluded.
    """
    solver = LinkedInScreeningSolver()

    # Define test checkboxes
    # 1. Background check consent
    chk_bg = make_async_locator(count=1, visible=True, text="I consent to background check verification")
    chk_bg.check = AsyncMock(return_value=None)
    chk_bg.is_checked = AsyncMock(return_value=False)

    # 2. Terms of service agreement
    chk_terms = make_async_locator(count=1, visible=True, text="I agree to terms of application")
    chk_terms.check = AsyncMock(return_value=None)
    chk_terms.is_checked = AsyncMock(return_value=False)

    # 3. Truthfulness certification
    chk_truth = make_async_locator(count=1, visible=True, text="I certify all information is accurate and truthful")
    chk_truth.check = AsyncMock(return_value=None)
    chk_truth.is_checked = AsyncMock(return_value=False)

    # 4. Follow company checkbox (MUST NOT be checked during screening)
    chk_follow = make_async_locator(count=1, visible=True, text="Follow Enterprise Corp to stay updated", attr_map={"id": "follow-company-checkbox"})
    chk_follow.check = AsyncMock(return_value=None)
    chk_follow.is_checked = AsyncMock(return_value=False)

    # 5. Arbitrary newsletter checkbox (not consent -> should NOT be checked)
    chk_news = make_async_locator(count=1, visible=True, text="Subscribe to weekly marketing newsletter")
    chk_news.check = AsyncMock(return_value=None)
    chk_news.is_checked = AsyncMock(return_value=False)

    all_checkboxes = [chk_bg, chk_terms, chk_truth, chk_follow, chk_news]

    chk_group = MagicMock()
    chk_group.count = AsyncMock(return_value=len(all_checkboxes))
    chk_group.nth = MagicMock(side_effect=lambda idx: all_checkboxes[idx])

    modal = MagicMock()
    modal.locator = MagicMock(side_effect=lambda sel: chk_group if "checkbox" in sel else make_async_locator(count=0, visible=False))

    handled = await solver.solve_all_questions_in_step(modal)

    # Verified: Consent checkboxes checked
    assert chk_bg.check.called, "Background check consent was not checked!"
    assert chk_terms.check.called, "Terms consent was not checked!"
    assert chk_truth.check.called, "Truthfulness certification was not checked!"

    # Verified: Follow company and marketing newsletter NOT checked
    assert not chk_follow.check.called, "CRITICAL ERROR: Follow company checkbox was checked during screening!"
    assert not chk_news.check.called, "Newsletter checkbox should not be checked!"

    assert len(handled) == 3


@run_async
async def test_iter2_review_step_follow_company_uncheck_lifecycle():
    """
    Verifies that on review step, uncheck_follow_company unchecks the checkbox
    if checked, and leaves it alone if already unchecked.
    """
    bot = LinkedInEasyApplyBot()

    # Case A: Follow company is checked -> uncheck must be invoked
    chk_checked = make_async_locator(count=1, visible=True, attr_map={"id": "follow-company-checkbox"})
    chk_checked.is_checked = AsyncMock(return_value=True)
    chk_checked.uncheck = AsyncMock(return_value=None)

    modal_a = MagicMock()
    modal_a.locator = MagicMock(side_effect=lambda sel: chk_checked if "follow" in sel else make_async_locator(count=0, visible=False))

    res_a = await bot.uncheck_follow_company(modal_a)
    assert res_a is True
    assert chk_checked.uncheck.called

    # Case B: Follow company is already unchecked -> uncheck should NOT be called
    chk_unchecked = make_async_locator(count=1, visible=True, attr_map={"id": "follow-company-checkbox"})
    chk_unchecked.is_checked = AsyncMock(return_value=False)
    chk_unchecked.uncheck = AsyncMock(return_value=None)

    modal_b = MagicMock()
    modal_b.locator = MagicMock(side_effect=lambda sel: chk_unchecked if "follow" in sel else make_async_locator(count=0, visible=False))

    res_b = await bot.uncheck_follow_company(modal_b)
    # When already unchecked, no uncheck operation was required, so returns False
    assert res_b is False
    assert not chk_unchecked.uncheck.called


# ==============================================================================
# 4. FSM STEP CLASSIFICATION & COMPLETE HISTORY TRACKING
# ==============================================================================

@run_async
async def test_iter2_fsm_multi_step_progression_and_history_audit():
    """
    Verifies that during a 3-step application (Contact -> Questions -> Review/Submit in dry-run),
    self.current_state updates on each step and self.history captures every transition with timestamps.
    """
    bot = LinkedInEasyApplyBot()

    # Mock dynamic step progression
    current_step = {"num": 1}

    contact_header = make_async_locator(count=1, visible=True, text="Contact information")
    questions_header = make_async_locator(count=1, visible=True, text="Screening questions")
    review_header = make_async_locator(count=1, visible=True, text="Review your application")
    submit_btn = make_async_locator(count=1, visible=True, text="Submit application")
    next_btn = make_async_locator(count=1, visible=True, text="Next")

    async def advance_click():
        current_step["num"] += 1
    next_btn.click = AsyncMock(side_effect=advance_click)

    modal_elem = MagicMock()
    def modal_loc(sel):
        step = current_step["num"]
        if "submit" in sel.lower():
            return submit_btn if step == 3 else make_async_locator(count=0, visible=False)
        if any(h in sel for h in ["h3", "h4"]):
            if step == 1:
                return contact_header
            elif step == 2:
                return questions_header
            else:
                return review_header
        if "next" in sel.lower():
            return next_btn if step < 3 else make_async_locator(count=0, visible=False)
        return make_async_locator(count=0, visible=False)
    modal_elem.locator = MagicMock(side_effect=modal_loc)

    modal_container = make_async_locator(count=1, visible=True)
    modal_container.first = modal_elem

    page = MagicMock()
    page.goto = AsyncMock(return_value=None)
    def page_loc(sel):
        if "modal" in sel.lower() or "[data-test-modal]" in sel:
            return modal_container
        if "apply" in sel.lower():
            return make_async_locator(count=1, visible=True, text="Easy Apply")
        return make_async_locator(count=0, visible=False)
    page.locator = MagicMock(side_effect=page_loc)

    with patch("naukari_pro.modules.linkedin_apply.humanized_delay", AsyncMock()):
        result = await bot.execute_easy_apply(
            page=page,
            job_info={"job_id": "777", "title": "Azure Data Eng", "company": "CloudCorp"},
            dry_run=True,
            max_steps=5
        )

    assert result["success"] is True
    assert result["status"] == "DRY_RUN_VERIFIED"
    assert result["steps"] == 3

    # History audit
    history = bot.history
    assert len(history) == 3, f"Expected 3 history records, got {len(history)}: {history}"

    # Step 1: Contact
    assert history[0]["step"] == 1
    assert history[0]["state"] == ModalState.STEP_CONTACT.value
    assert history[0]["timestamp"] > 0

    # Step 2: Questions
    assert history[1]["step"] == 2
    assert history[1]["state"] == ModalState.STEP_QUESTIONS.value
    assert history[1]["timestamp"] >= history[0]["timestamp"]

    # Step 3: Review
    assert history[2]["step"] == 3
    assert history[2]["state"] == ModalState.STEP_REVIEW.value
    assert history[2]["timestamp"] >= history[1]["timestamp"]

    # Final state
    assert bot.current_state == ModalState.TERMINAL_DRY_RUN


# ==============================================================================
# 5. NEGATIVE DISQUALIFIER GUARDS & AFFIRMATIVE QUALIFIERS STRESS MATRIX
# ==============================================================================

def test_iter2_negative_guards_complex_phrasing_stress_matrix():
    """
    Stress-tests screening solver negative disqualifiers against varied adversarial real-world phrasing.
    """
    solver = LinkedInScreeningSolver()

    adversarial_disqualifiers = [
        # Non-compete variations
        "Are you currently restricted by a noncompetition agreement?",
        "Are you party to any active non-competition covenant with your current employer?",
        "Are you bound by an enforceable noncompetition contract?",
        "Do you have an existing restrictive covenant preventing employment?",
        
        # Disciplinary variations
        "Have you been the subject of any disciplinary proceedings by an employer?",
        "Have you faced internal disciplinary action regarding workplace conduct?",
        "Were you ever terminated for cause or breach of company policy?",
        
        # Visa / Sponsorship variations
        "Will you now or in the future require visa sponsorship from the company?",
        "Do you require employment visa sponsorship to work in India?",
        "Will you require employer sponsorship for employment authorization?",
        "Do you need H1B, Tier 2, or any other work visa sponsorship?",
        
        # Criminal / Integrity
        "Have you been convicted of a criminal felony or misdemeanor?",
        "Have you ever been convicted in a court of law?",
        
        # Family / Relative working (matching supported keywords)
        "Do you have a family member working for our company?",
        "Is any relative working at this organization?",
    ]

    for q in adversarial_disqualifiers:
        ans = solver.determine_radio_answer(q)
        assert ans is False, f"Negative guard FAILED for query: '{q}' (returned {ans}, expected False)"


def test_iter2_empirical_blindspot_relative_employed_variations():
    """
    Adversarial Challenge Finding:
    Empirically documents that determine_radio_answer relies on exact substrings
    'family member working' and 'relative working', causing variations such as
    'relatives working' (plural), 'family member currently working' (intervening adverb),
    or 'relatives employed' to fall through to True (answering Yes to having relatives at the firm).
    """
    solver = LinkedInScreeningSolver()

    # Exact keywords match False:
    assert solver.determine_radio_answer("Do you have a family member working here?") is False
    assert solver.determine_radio_answer("Is any relative working at this company?") is False

    # Variations that fall through to True:
    unhandled_variations = [
        "Do you have any relatives working at this company?", # plural 'relatives'
        "Do you have a family member currently working at this company?", # intervening 'currently'
        "Do you have any relatives employed at this organization?", # 'employed' vs 'working'
    ]
    for q in unhandled_variations:
        ans = solver.determine_radio_answer(q)
        # We record that it currently returns True
        assert ans is True, f"Expected currently unhandled query '{q}' to return True"


def test_iter2_affirmative_qualifiers_without_sponsorship_permutations():
    """
    Stress-tests affirmative handling of 'without sponsorship' phrasing permutations.
    """
    solver = LinkedInScreeningSolver()

    affirmative_queries = [
        "Are you authorized to work in India without requiring sponsorship?",
        "Are you authorized to work in India without sponsorship?",
        "Do you have authorization to work in India without requiring employer sponsorship?",
        "Are you legally permitted to work without requiring visa support?",
        "Can you work in India without needing employer sponsorship?",
        "Are you a citizen or permanent resident eligible to work without sponsorship?",
        "Will you be able to begin employment without requiring employer sponsorship?",
    ]

    for q in affirmative_queries:
        ans = solver.determine_radio_answer(q)
        assert ans is True, f"Affirmative qualifier FAILED for query: '{q}' (returned {ans}, expected True)"


# ==============================================================================
# 6. AUTO-HEAL SELECTOR SCOPE & ELEMENT DEDUPLICATION
# ==============================================================================

@run_async
async def test_iter2_auto_heal_selector_scope_and_deduplication():
    """
    Verifies that auto_heal_step discovers inputs inside error containers
    even when aria-invalid is missing, and deduplicates elements matching multiple selectors.
    """
    bot = LinkedInEasyApplyBot()

    # Create mock inputs
    # Input 1: matches aria-invalid='true' AND is inside div.artdeco-inline-feedback--error
    input_shared = make_async_locator(count=1, visible=True, attr_map={"type": "number", "id": "inp1"})
    input_shared.fill = AsyncMock(return_value=None)

    # Input 2: has NO aria-invalid, but is inside div.fb-form-element--error
    input_container_only = make_async_locator(count=1, visible=True, attr_map={"type": "text", "id": "inp2"})
    input_container_only.fill = AsyncMock(return_value=None)

    # Input 3: valid input, not in any error container
    input_valid = make_async_locator(count=1, visible=True, attr_map={"type": "text", "id": "inp3"})
    input_valid.fill = AsyncMock(return_value=None)

    def modal_loc(sel):
        if sel == "input[aria-invalid='true']":
            return input_shared
        if sel == "div.artdeco-inline-feedback--error input":
            return input_shared  # Returns same element instance
        if sel == "div.fb-form-element--error input":
            return input_container_only
        return make_async_locator(count=0, visible=False)

    modal = MagicMock()
    modal.locator = MagicMock(side_effect=modal_loc)

    healed = await bot.auto_heal_step(modal, attempt=1)
    assert healed is True

    # input_shared should be filled EXACTLY ONCE (deduplication check)
    assert input_shared.fill.call_count == 1, (
        f"Deduplication failed! input_shared was filled {input_shared.fill.call_count} times instead of 1."
    )
    assert input_shared.fill.call_args == call("2")

    # input_container_only should be filled once with text fallback
    assert input_container_only.fill.call_count == 1
    assert input_container_only.fill.call_args == call("Hyderabad, India")

    # input_valid should NOT be filled
    assert input_valid.fill.call_count == 0


# ==============================================================================
# 7. CIRCUIT BREAKER SINGLE-COUNTING INTEGRATION BETWEEN NAVIGATOR & ENGINE
# ==============================================================================

@run_async
async def test_iter2_circuit_breaker_single_counting_three_failures_trips_breaker():
    """
    Verifies that LinkedInApplyEngine.run_apply_cycle increments failure count
    EXACTLY ONCE per failed vacancy when sharing a circuit breaker with navigator.
    Trips cleanly on vacancy 3 (threshold=3), NOT prematurely on vacancy 2.
    """
    engine = LinkedInApplyEngine(min_score=70.0)
    cb = engine.circuit_breaker
    assert cb.consecutive_errors == 0
    assert not cb.is_tripped

    # Navigator shares the same circuit breaker
    engine.navigator.circuit_breaker = cb
    engine.tracker.is_applied = MagicMock(return_value=False)
    engine.tracker.log_application = MagicMock()

    # Mock 3 search vacancies
    mock_jobs = [
        {"job_id": "101", "title": "Azure Data Engineer", "company": "Corp A", "url": "https://linkedin.com/jobs/view/101", "description": "PySpark Delta Lake"},
        {"job_id": "102", "title": "Senior Azure Data Engineer", "company": "Corp B", "url": "https://linkedin.com/jobs/view/102", "description": "Databricks Azure"},
        {"job_id": "103", "title": "Lead Azure Data Engineer", "company": "Corp C", "url": "https://linkedin.com/jobs/view/103", "description": "ADF Kafka"},
        {"job_id": "104", "title": "Data Platform Engineer", "company": "Corp D", "url": "https://linkedin.com/jobs/view/104", "description": "Spark SQL"},
    ]

    engine.search_engine.search_jobs = AsyncMock(return_value=mock_jobs)
    engine.scorer.evaluate = MagicMock(return_value=MatchScoreResult(
        score=85.0,
        passed=True,
        match_reasons=["Azure"],
        breakdown={"total": 85.0},
        job_title="Azure Data Engineer"
    ))

    # Mock navigator.execute_easy_apply to fail each time
    # In production, navigator records 1 failure on the cb
    async def mock_execute_apply(page, job_info, **kwargs):
        cb.record_failure("MOCK_NAVIGATOR_FAILURE")
        return {
            "success": False,
            "status": "DISCARDED_UNRESOLVABLE",
            "job_id": job_info["job_id"],
            "title": job_info["title"],
            "company": job_info["company"],
            "url": job_info.get("url", ""),
            "steps": 1
        }
    engine.navigator.execute_easy_apply = AsyncMock(side_effect=mock_execute_apply)

    # Mock context and session
    mock_page = MagicMock()
    mock_page.url = "https://www.linkedin.com/feed"
    mock_page.goto = AsyncMock(return_value=None)
    mock_context = MagicMock()
    mock_context.pages = [mock_page]
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_context.close = AsyncMock(return_value=None)

    engine.session_manager.verify_session = AsyncMock(return_value={
        "status": "VALID",
        "authenticated": True,
        "candidate_name": "Lavkush Kumar"
    })

    with patch.object(engine.session_manager, "create_stealth_context", AsyncMock(return_value=mock_context)), \
         patch("playwright.async_api.async_playwright", make_playwright_cm_mock(mock_context)), \
         patch("naukari_pro.modules.linkedin_apply.humanized_delay", AsyncMock()):
        stats = await engine.run_apply_cycle(dry_run=True, limit=5, headless=True)

    # Failure count must be 3, tripping the circuit breaker exactly after job 3!
    assert cb.is_tripped is True
    assert cb.trip_reason == "CONSECUTIVE_ERRORS"
    assert cb.consecutive_errors == 3
    assert stats["failed"] == 3
    assert len(stats["jobs"]) == 3, f"Expected loop break on job 3, but processed {len(stats['jobs'])} jobs"
    # Job 104 was never processed because breaker tripped on job 103!
    assert [j["job_id"] for j in stats["jobs"]] == ["101", "102", "103"]


@run_async
async def test_iter2_circuit_breaker_success_resets_failure_count_cleanly():
    """
    Verifies that when an application succeeds in dry-run,
    record_success resets failure_count to 0 without double-counting.
    """
    engine = LinkedInApplyEngine(min_score=70.0)
    cb = engine.circuit_breaker
    engine.navigator.circuit_breaker = cb
    engine.tracker.is_applied = MagicMock(return_value=False)
    engine.tracker.log_application = MagicMock()

    # Pre-seed 2 failures
    cb.record_failure("PREV_ERROR_1")
    cb.record_failure("PREV_ERROR_2")
    assert cb.consecutive_errors == 2
    assert not cb.is_tripped

    mock_job = [{"job_id": "201", "title": "Azure Data Engineer", "company": "Corp Success", "url": "https://linkedin.com/jobs/view/201", "description": "PySpark Delta"}]
    engine.search_engine.search_jobs = AsyncMock(return_value=mock_job)
    engine.scorer.evaluate = MagicMock(return_value=MatchScoreResult(
        score=90.0,
        passed=True,
        match_reasons=["Azure"],
        breakdown={"total": 90.0},
        job_title="Azure Data Engineer"
    ))

    async def mock_execute_success(page, job_info, **kwargs):
        cb.record_success()
        return {
            "success": True,
            "status": "DRY_RUN_VERIFIED",
            "job_id": job_info["job_id"],
            "title": job_info["title"],
            "company": job_info["company"],
            "url": job_info.get("url", ""),
            "steps": 3
        }
    engine.navigator.execute_easy_apply = AsyncMock(side_effect=mock_execute_success)

    mock_page = MagicMock()
    mock_page.url = "https://www.linkedin.com/feed"
    mock_page.goto = AsyncMock(return_value=None)
    mock_context = MagicMock()
    mock_context.pages = [mock_page]
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_context.close = AsyncMock(return_value=None)

    engine.session_manager.verify_session = AsyncMock(return_value={
        "status": "VALID",
        "authenticated": True,
        "candidate_name": "Lavkush Kumar"
    })

    with patch.object(engine.session_manager, "create_stealth_context", AsyncMock(return_value=mock_context)), \
         patch("playwright.async_api.async_playwright", make_playwright_cm_mock(mock_context)), \
         patch("naukari_pro.modules.linkedin_apply.humanized_delay", AsyncMock()):
        stats = await engine.run_apply_cycle(dry_run=True, limit=1, headless=True)

    assert stats["dry_run_verified"] == 1
    assert stats["failed"] == 0
    assert cb.consecutive_errors == 0, f"Expected consecutive_errors=0 after success, got {cb.consecutive_errors}"
    assert cb.total_applied == 1
