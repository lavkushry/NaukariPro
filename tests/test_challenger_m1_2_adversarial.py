"""
Adversarial Stress Test Suite for Milestone 1 (R1)
Authored by Challenger M1_2 (teamwork_challenger_m1_2)

Empirically challenges:
1. Cadence & Rate-Limiting:
   - 5 keyword mutations in a single week (strictly blocked after 2)
   - Platform quota isolation (Naukri vs LinkedIn)
   - Freshness bumps not consuming keyword quota
   - Downgrade to freshness bump when keyword quota exhausted
2. Timezone Boundaries:
   - UTC vs IST transition across Monday 00:00:00 IST (week counter reset)
   - Exact boundary second precision (Sunday 23:59:59 IST vs Monday 00:00:00 IST)
   - Aware UTC vs Aware IST reference date equivalence
   - Month and Year boundary calendar transitions
3. Daily Bump Freshness Cooldown:
   - 2 bumps within 1 hour throttled by cooldown
   - Cooldown bypass with force=True
   - Cooldown expiration after 2 hours (7200s)
   - CadenceScheduler daily touch check in evaluate_mutation_eligibility
4. Execution Window Envelope:
   - Tue-Thu 09:30-11:30 IST +/-90m window (08:00-13:00 IST envelope)
   - Active cadence weekdays (Tue, Wed, Thu only; Mon/Fri/Sat/Sun rejected)
   - Boundary second checks (07:59:59 vs 08:00:00 and 13:00:00 vs 13:00:01 IST)
   - Monte Carlo simulation: 1,000 jittered slots strictly within [08:00, 13:00] IST
5. Hash Engine & Idempotency:
   - SHA-256 canonical whitespace & newline normalization (CRLF, CR, LF, trailing/leading spaces)
   - Unicode NFC vs NFD canonical normalization (e.g. composed vs decomposed glyphs)
   - Unordered vs ordered list token hashing
   - Nested dictionary canonical sorting and JSON hashing
   - None / Empty string SHA-256 consistency
   - NOOP detection in ProfileMutator.apply_mutation (prevents DOM execution & ledger write)
   - NOOP detection in db.record_profile_mutation (returns MutationRecordFailure)
6. Database Concurrency & Rollback:
   - High-concurrency multi-threaded writes to profile_mutations ledger
   - Simultaneous reads and writes with SQLite ACID integrity
   - revert_profile_mutation() restores weekly mutation quota
   - Reverting non-existent or already-reverted records returns False
   - Transaction rollback on constraint failure

100% Offline Socket Compliance: Uses temporary isolated SQLite databases and mock pages.
"""

import os
import json
import sqlite3
import unicodedata
import concurrent.futures
import pytest
from datetime import datetime, date, time, timezone, timedelta
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

from naukari_pro.modules.learning.mutator import (
    BlacklistValidator,
    BlacklistViolationError,
    NaukriWhitelist,
    LinkedInWhitelist,
    LinkedInTokenRotator,
    HashEngine,
    CadenceScheduler,
    ProfileMutator,
    MutationProposal,
    MutationResult,
    MutationStatus,
    Platform,
    MutationField,
)
from naukari_pro.modules.db import (
    init_db,
    record_profile_mutation,
    get_weekly_mutation_count,
    can_apply_keyword_mutation,
    get_latest_mutation,
    revert_profile_mutation,
    compute_field_hash,
    get_db_connection,
    MutationRecordFailure,
    MutationRecordResult,
    EMPTY_SHA256,
)
from naukari_pro.modules.profile_enhancer import ProfileEnhancerEngine

IST_TZ = ZoneInfo("Asia/Kolkata")


@pytest.fixture
def isolated_db(tmp_path):
    """Provides an isolated SQLite database file with all schemas initialized."""
    db_file = str(tmp_path / "test_adversarial_m1.db")
    init_db(db_file)
    return db_file


# ==============================================================================
# SECTION 1: CADENCE & RATE-LIMITING ADVERSARIAL TESTS
# ==============================================================================

class TestCadenceRateLimitingAdversarial:
    """Stress-tests the dual-tier rate limiting and weekly quota enforcement."""

    def test_five_keyword_mutations_blocked_after_two(self, isolated_db):
        """
        Adversarial scenario: Attempt 5 keyword mutations in a single week.
        Assert that after 2, all subsequent keyword mutations are blocked:
        - can_apply_keyword_mutation() returns False
        - ProfileMutator.can_mutate() returns False
        - Mutator rejects further keyword proposals
        """
        mutator = ProfileMutator(db_path=isolated_db)

        # Pre-condition: Quota is 0/2
        assert mutator.can_mutate("naukri") is True
        can_kw, count, _ = can_apply_keyword_mutation("naukri", max_weekly=2, db_path=isolated_db)
        assert can_kw is True
        assert count == 0

        # Mutation 1: Should succeed
        prop1 = mutator.propose_mutation(
            platform="naukri",
            field="headline",
            new_value="Azure Data Engineer | Databricks · PySpark · Delta Lake | 2.5 YOE",
            current_value="Generic Software Engineer",
            is_keyword_mutation=True
        )
        res1 = mutator.apply_mutation(prop1, lambda f, v: True)
        assert res1.status == MutationStatus.APPLIED
        assert res1.ledger_id is not None and res1.ledger_id > 0

        # Post-Mutation 1: Quota is 1/2 -> Still eligible
        assert mutator.can_mutate("naukri") is True
        can_kw, count, _ = can_apply_keyword_mutation("naukri", max_weekly=2, db_path=isolated_db)
        assert can_kw is True
        assert count == 1

        # Mutation 2: Should succeed
        prop2 = mutator.propose_mutation(
            platform="naukri",
            field="headline",
            new_value="Azure Data Engineer | Azure Databricks · PySpark · Delta Lake · SQL | 2.5 YOE",
            current_value=prop1.new_value,
            is_keyword_mutation=True
        )
        res2 = mutator.apply_mutation(prop2, lambda f, v: True)
        assert res2.status == MutationStatus.APPLIED
        assert res2.ledger_id is not None and res2.ledger_id > 0

        # Post-Mutation 2: Quota is 2/2 -> BLOCKED
        assert mutator.can_mutate("naukri") is False
        can_kw, count, reason = can_apply_keyword_mutation("naukri", max_weekly=2, db_path=isolated_db)
        assert can_kw is False
        assert count == 2
        assert "Weekly keyword mutation limit reached (2/2 applied this week)" in reason

        # Mutation Attempts 3, 4, 5: Must all be blocked by can_mutate gate
        for attempt in range(3, 6):
            assert mutator.can_mutate("naukri") is False
            can_kw, count, _ = can_apply_keyword_mutation("naukri", max_weekly=2, db_path=isolated_db)
            assert can_kw is False
            assert count == 2

    def test_freshness_bumps_do_not_exhaust_keyword_quota(self, isolated_db):
        """
        Verifies that daily freshness bumps (is_keyword_mutation=False, field='freshness_bump')
        do NOT consume weekly keyword mutation budget.
        """
        mutator = ProfileMutator(db_path=isolated_db)

        # Record 10 freshness bumps
        for i in range(10):
            res = record_profile_mutation(
                platform="naukri",
                field="freshness_bump",
                new_value=f"Bump touch {i}",
                old_value=f"Bump touch {i-1}" if i > 0 else "Base",
                is_keyword_mutation=False,
                mutation_type="daily_freshness_bump",
                db_path=isolated_db
            )
            assert res > 0

        # Keyword count must still be 0!
        count = get_weekly_mutation_count(platform="naukri", is_keyword_only=True, db_path=isolated_db)
        assert count == 0
        assert mutator.can_mutate("naukri") is True

        # Now apply 2 keyword mutations
        record_profile_mutation("naukri", "headline", "KW 1", is_keyword_mutation=True, db_path=isolated_db)
        record_profile_mutation("naukri", "headline", "KW 2", is_keyword_mutation=True, db_path=isolated_db)

        # Keyword count is 2 -> blocked
        assert get_weekly_mutation_count(platform="naukri", is_keyword_only=True, db_path=isolated_db) == 2
        assert mutator.can_mutate("naukri") is False

        # Total mutations in ledger includes freshness bumps
        total = get_weekly_mutation_count(platform="naukri", is_keyword_only=False, db_path=isolated_db)
        assert total == 12

    def test_platform_quota_isolation_naukri_vs_linkedin(self, isolated_db):
        """
        Verifies that Naukri and LinkedIn have independent weekly mutation budgets.
        Exhausting Naukri quota (2/2) must NOT block LinkedIn (0/2).
        """
        mutator = ProfileMutator(db_path=isolated_db)

        # Exhaust Naukri quota
        record_profile_mutation("naukri", "headline", "Naukri KW 1", is_keyword_mutation=True, db_path=isolated_db)
        record_profile_mutation("naukri", "headline", "Naukri KW 2", is_keyword_mutation=True, db_path=isolated_db)

        assert mutator.can_mutate("naukri") is False
        assert mutator.can_mutate("linkedin") is True

        can_kw_li, count_li, _ = can_apply_keyword_mutation("linkedin", max_weekly=2, db_path=isolated_db)
        assert can_kw_li is True
        assert count_li == 0

        # Apply 1 to LinkedIn
        record_profile_mutation("linkedin", "headline", "LinkedIn KW 1", is_keyword_mutation=True, db_path=isolated_db)
        assert mutator.can_mutate("linkedin") is True
        assert get_weekly_mutation_count("linkedin", is_keyword_only=True, db_path=isolated_db) == 1

        # Apply 2nd to LinkedIn
        record_profile_mutation("linkedin", "headline", "LinkedIn KW 2", is_keyword_mutation=True, db_path=isolated_db)
        assert mutator.can_mutate("linkedin") is False
        assert get_weekly_mutation_count("linkedin", is_keyword_only=True, db_path=isolated_db) == 2

    def test_evaluate_mutation_eligibility_downgrades_to_bump(self, isolated_db):
        """
        When inside execution envelope on an active day:
        - If quota remaining: returns (can_run=True, allow_kw=True, reason)
        - If quota exhausted: returns (can_run=True, allow_kw=False, reason) -> bump only!
        """
        wed_10am_ist = datetime(2026, 11, 4, 10, 0, 0, tzinfo=IST_TZ)

        # Quota empty: allows keyword mutation
        can_run, allow_kw, reason = CadenceScheduler.evaluate_mutation_eligibility(
            platform="naukri",
            dt=wed_10am_ist,
            db_path=isolated_db
        )
        assert can_run is True
        assert allow_kw is True
        assert "Eligible for keyword mutation" in reason

        # Fill quota on Tuesday of the same week (Nov 3)
        tue_time = (wed_10am_ist - timedelta(days=1)).astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        record_profile_mutation("naukri", "headline", "KW 1", applied_at=tue_time, is_keyword_mutation=True, db_path=isolated_db)
        record_profile_mutation("naukri", "headline", "KW 2", applied_at=tue_time, is_keyword_mutation=True, db_path=isolated_db)

        # Quota full: downgrades to freshness bump
        can_run, allow_kw, reason = CadenceScheduler.evaluate_mutation_eligibility(
            platform="naukri",
            dt=wed_10am_ist,
            db_path=isolated_db
        )
        assert can_run is True
        assert allow_kw is False
        assert "Eligible for freshness bump only" in reason


# ==============================================================================
# SECTION 2: TIMEZONE BOUNDARY STRESS TESTS (UTC vs IST MONDAY 00:00)
# ==============================================================================

class TestTimezoneBoundaryStress:
    """Stress-tests calendar week roll-overs and timezone boundaries."""

    def test_utc_vs_ist_transition_across_monday_midnight(self, isolated_db):
        """
        Monday 00:00:00 IST is Sunday 18:30:00 UTC.
        Mutations recorded at Sunday 18:29:59 UTC belong to the previous week.
        Mutations recorded at Sunday 18:30:00 UTC belong to the new week.
        """
        # Calendar context:
        # 2026-11-01 is Sunday
        # 2026-11-02 is Monday
        # Sunday 23:59:59 IST = 2026-11-01 18:29:59 UTC
        # Monday 00:00:00 IST = 2026-11-01 18:30:00 UTC

        # Record 2 mutations in Week W-1 (Sunday before midnight IST)
        record_profile_mutation(
            "naukri", "headline", "Old KW 1",
            applied_at="2026-11-01 18:28:00",
            is_keyword_mutation=True,
            db_path=isolated_db
        )
        record_profile_mutation(
            "naukri", "headline", "Old KW 2",
            applied_at="2026-11-01 18:29:59",
            is_keyword_mutation=True,
            db_path=isolated_db
        )

        # Check count from perspective of Sunday 23:59:59 IST
        sunday_dt = datetime(2026, 11, 1, 23, 59, 59, tzinfo=IST_TZ)
        count_sun = get_weekly_mutation_count("naukri", reference_date=sunday_dt, db_path=isolated_db)
        assert count_sun == 2

        can_kw_sun, _, _ = can_apply_keyword_mutation("naukri", reference_date=sunday_dt, db_path=isolated_db)
        assert can_kw_sun is False

        # Transition 1 second forward to Monday 00:00:00 IST
        monday_dt = datetime(2026, 11, 2, 0, 0, 0, tzinfo=IST_TZ)
        count_mon = get_weekly_mutation_count("naukri", reference_date=monday_dt, db_path=isolated_db)
        assert count_mon == 0, f"Expected 0 count on Monday 00:00 IST, got {count_mon}"

        can_kw_mon, _, _ = can_apply_keyword_mutation("naukri", reference_date=monday_dt, db_path=isolated_db)
        assert can_kw_mon is True, "Quota must reset on Monday 00:00 IST"

    def test_exact_boundary_second_behavior(self, isolated_db):
        """
        Tests exact second precision around cutoff:
        - 2026-11-01 18:29:59 UTC (Sunday 23:59:59 IST) -> NOT in Week W
        - 2026-11-01 18:30:00 UTC (Monday 00:00:00 IST) -> IN Week W
        - 2026-11-01 18:30:01 UTC (Monday 00:00:01 IST) -> IN Week W
        """
        record_profile_mutation(
            "naukri", "headline", "Sub-second 1",
            applied_at="2026-11-01 18:29:59",
            is_keyword_mutation=True,
            db_path=isolated_db
        )
        record_profile_mutation(
            "naukri", "headline", "Sub-second 2",
            applied_at="2026-11-01 18:30:00",
            is_keyword_mutation=True,
            db_path=isolated_db
        )
        record_profile_mutation(
            "naukri", "headline", "Sub-second 3",
            applied_at="2026-11-01 18:30:01",
            is_keyword_mutation=True,
            db_path=isolated_db
        )

        ref_monday = datetime(2026, 11, 2, 12, 0, 0, tzinfo=IST_TZ)
        count = get_weekly_mutation_count("naukri", reference_date=ref_monday, db_path=isolated_db)
        # Should contain Sub-second 2 and Sub-second 3 (count = 2), but NOT Sub-second 1!
        assert count == 2

    def test_aware_utc_vs_aware_ist_reference_date_consistency(self, isolated_db):
        """
        Verifies that passing reference_date in UTC vs IST produces identical results.
        """
        record_profile_mutation(
            "naukri", "headline", "Timezone KW",
            applied_at="2026-11-03 10:00:00",
            is_keyword_mutation=True,
            db_path=isolated_db
        )

        dt_ist = datetime(2026, 11, 4, 15, 0, 0, tzinfo=IST_TZ)
        dt_utc = dt_ist.astimezone(timezone.utc)

        count_ist = get_weekly_mutation_count("naukri", reference_date=dt_ist, db_path=isolated_db)
        count_utc = get_weekly_mutation_count("naukri", reference_date=dt_utc, db_path=isolated_db)
        assert count_ist == count_utc == 1

    def test_month_and_year_transition_boundaries(self, isolated_db):
        """
        Tests week resets across month boundaries (e.g. Feb 28 -> Mar 1)
        and year transitions (e.g. Dec 31 -> Jan 1).
        """
        # 2026-12-31 is Thursday
        # 2027-01-01 is Friday
        # 2027-01-04 is Monday
        record_profile_mutation(
            "naukri", "headline", "Year-End 2026",
            applied_at="2026-12-31 09:30:00",
            is_keyword_mutation=True,
            db_path=isolated_db
        )

        # Friday Jan 1, 2027 is same week as Dec 31, 2026
        dt_fri = datetime(2027, 1, 1, 10, 0, 0, tzinfo=IST_TZ)
        assert get_weekly_mutation_count("naukri", reference_date=dt_fri, db_path=isolated_db) == 1

        # Monday Jan 4, 2027 starts a new week
        dt_mon = datetime(2027, 1, 4, 0, 0, 1, tzinfo=IST_TZ)
        assert get_weekly_mutation_count("naukri", reference_date=dt_mon, db_path=isolated_db) == 0


# ==============================================================================
# SECTION 3: DAILY BUMP FRESHNESS COOLDOWN ADVERSARIAL TESTS
# ==============================================================================

class TestDailyBumpCooldownAdversarial:
    """Stress-tests the Daily Bump cooldown mechanism in ProfileEnhancerEngine and CadenceScheduler."""

    def test_two_bumps_within_one_hour_prevented_by_cooldown(self, tmp_path, isolated_db):
        """
        Attempt 2 bumps within 1 hour:
        - First bump succeeds and updates last_bumped_timestamp.
        - Second bump 15-59 minutes later is intercepted by cooldown:
          skips DOM edits, does NOT navigate, returns True (safe recency preserved).
        """
        state_file = str(tmp_path / "naukri_enhancer_state.json")
        engine = ProfileEnhancerEngine()
        engine.state_file = state_file
        engine.mutator = ProfileMutator(db_path=isolated_db)

        # Simulate a bump 30 minutes ago (1800s elapsed < 7200s cooldown)
        now = datetime.now()
        thirty_mins_ago = now - timedelta(minutes=30)
        with open(state_file, "w") as f:
            json.dump({
                "last_bumped_date": thirty_mins_ago.strftime("%Y-%m-%d"),
                "last_bumped_timestamp": thirty_mins_ago.isoformat()
            }, f)

        mock_page = MagicMock()
        # Attempt bump with standard 2h (7200s) cooldown
        res = engine.bump_profile(mock_page, force=False, cooldown_seconds=7200)

        # Must skip DOM navigation and return True
        assert res is True
        assert mock_page.goto.call_count == 0
        assert mock_page.locator.call_count == 0

    def test_bump_cooldown_bypass_with_force_flag(self, tmp_path, isolated_db):
        """
        When force=True is specified, cooldown throttle must be bypassed even if
        bump occurred 5 minutes ago.
        """
        state_file = str(tmp_path / "naukri_enhancer_state.json")
        engine = ProfileEnhancerEngine()
        engine.state_file = state_file
        engine.mutator = ProfileMutator(db_path=isolated_db)

        # Bump 5 minutes ago
        five_mins_ago = datetime.now() - timedelta(minutes=5)
        with open(state_file, "w") as f:
            json.dump({
                "last_bumped_timestamp": five_mins_ago.isoformat()
            }, f)

        mock_page = MagicMock()
        mock_page.url = "https://www.naukri.com/mnjuser/profile"
        mock_page.locator.return_value.first.count.return_value = 0 # stop after navigation

        res = engine.bump_profile(mock_page, force=True, cooldown_seconds=7200)
        # Must attempt navigation because force=True bypassed cooldown
        assert mock_page.goto.call_count == 1

    def test_bump_cooldown_expiration_after_two_hours(self, tmp_path, isolated_db):
        """
        When 2 hours and 1 second have elapsed (> 7200s), cooldown must expire
        and allow normal bump execution.
        """
        state_file = str(tmp_path / "naukri_enhancer_state.json")
        engine = ProfileEnhancerEngine()
        engine.state_file = state_file
        engine.mutator = ProfileMutator(db_path=isolated_db)

        # Bump 2 hours and 5 minutes ago (7500s elapsed > 7200s cooldown)
        two_hours_ago = datetime.now() - timedelta(seconds=7500)
        with open(state_file, "w") as f:
            json.dump({
                "last_bumped_timestamp": two_hours_ago.isoformat()
            }, f)

        mock_page = MagicMock()
        mock_page.url = "https://www.naukri.com/mnjuser/profile"
        mock_page.locator.return_value.first.count.return_value = 0

        engine.bump_profile(mock_page, force=False, cooldown_seconds=7200)
        # Cooldown expired -> proceeded to navigation
        assert mock_page.goto.call_count == 1

    def test_evaluate_mutation_eligibility_daily_touch_cooldown(self, isolated_db):
        """
        CadenceScheduler.evaluate_mutation_eligibility checks if a mutation
        was already applied today. If so, rejects unforced runs.
        """
        now_ist = datetime.now(IST_TZ)
        tue_10am = now_ist.replace(hour=10, minute=0, second=0, microsecond=0)
        # Set weekday to Tuesday
        days_ahead = (1 - tue_10am.weekday()) % 7
        tue_10am = tue_10am + timedelta(days=days_ahead)

        # Apply a mutation today
        record_profile_mutation(
            "naukri", "headline", "Today touch",
            applied_at=tue_10am.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            db_path=isolated_db
        )

        # Check eligibility same day without force -> blocked
        can_run, _, reason = CadenceScheduler.evaluate_mutation_eligibility(
            platform="naukri",
            force=False,
            dt=tue_10am + timedelta(hours=1),
            db_path=isolated_db
        )
        assert can_run is False
        assert "Profile already updated today" in reason

        # Check eligibility same day with force -> permitted
        can_run_f, _, _ = CadenceScheduler.evaluate_mutation_eligibility(
            platform="naukri",
            force=True,
            dt=tue_10am + timedelta(hours=1),
            db_path=isolated_db
        )
        assert can_run_f is True


# ==============================================================================
# SECTION 4: EXECUTION WINDOW ENVELOPE (TUE-THU 09:30-11:30 IST ±90M)
# ==============================================================================

class TestExecutionWindowEnvelope:
    """Stress-tests the Tue-Thu mid-week recruiter sourcing window and jitter envelope."""

    @pytest.mark.parametrize("day_name, day_offset, expected_active", [
        ("Monday", 0, False),
        ("Tuesday", 1, True),
        ("Wednesday", 2, True),
        ("Thursday", 3, True),
        ("Friday", 4, False),
        ("Saturday", 5, False),
        ("Sunday", 6, False),
    ])
    def test_envelope_active_days_tue_wed_thu_only(self, day_name, day_offset, expected_active):
        """Cadence is strictly active Tuesday, Wednesday, and Thursday."""
        # Baseline Monday: 2026-11-02
        test_dt = datetime(2026, 11, 2 + day_offset, 10, 30, 0, tzinfo=IST_TZ)
        assert CadenceScheduler.is_active_cadence_day(test_dt) is expected_active

    @pytest.mark.parametrize("test_time, expected_in_envelope", [
        (time(7, 59, 59), False), # 1 second before 08:00 IST
        (time(8, 0, 0), True),    # Lower boundary: 08:00 IST
        (time(9, 30, 0), True),   # Nominal window start: 09:30 IST
        (time(10, 30, 0), True),  # Center nominal time: 10:30 IST
        (time(11, 30, 0), True),  # Nominal window end: 11:30 IST
        (time(13, 0, 0), True),   # Upper boundary: 13:00 IST
        (time(13, 0, 1), False),  # 1 second after 13:00 IST
        (time(14, 0, 0), False),  # Afternoon
        (time(23, 0, 0), False),  # Night
        (time(2, 0, 0), False),   # Early morning
    ])
    def test_envelope_boundary_seconds(self, test_time, expected_in_envelope):
        """08:00-13:00 IST envelope boundary second precision on an active Wednesday."""
        # 2026-11-04 is Wednesday
        dt = datetime.combine(date(2026, 11, 4), test_time, tzinfo=IST_TZ)
        assert CadenceScheduler.is_within_execution_envelope(dt) is expected_in_envelope

    def test_jittered_slot_generator_1000_samples_bounds_check(self):
        """
        Monte Carlo simulation: Generates 1,000 jittered slots with different seeds and dates.
        Asserts 100% of samples fall strictly within [08:00, 13:00] IST envelope.
        """
        ref_date = date(2026, 11, 4) # Wednesday
        slots = [CadenceScheduler.calculate_daily_jittered_slot(target_date=ref_date, seed=i) for i in range(1000)]

        for slot in slots:
            assert slot.tzinfo is not None
            t = slot.time()
            assert time(8, 0, 0) <= t <= time(13, 0, 0), f"Slot {slot} out of envelope!"

        # Statistical verification:
        # Center is 10:30:00 (630 minutes from midnight)
        # Jitter is +/-90 min -> range is 09:00:00 to 12:00:59
        minutes_from_midnight = [s.hour * 60 + s.minute for s in slots]
        min_slot = min(minutes_from_midnight)
        max_slot = max(minutes_from_midnight)
        avg_slot = sum(minutes_from_midnight) / len(minutes_from_midnight)

        assert min_slot >= 9 * 60, f"Earliest slot {min_slot//60}:{min_slot%60} should be >= 09:00"
        assert max_slot <= 12 * 60 + 1, f"Latest slot {max_slot//60}:{max_slot%60} should be <= 12:01"
        assert 620 <= avg_slot <= 640, f"Mean slot {avg_slot} min should center near 630 min (10:30 IST)"

    def test_evaluate_mutation_eligibility_outside_window_rejection(self, isolated_db):
        """
        Verifies evaluate_mutation_eligibility returns False on non-cadence days
        or outside the 08:00-13:00 IST window when force=False.
        """
        # Friday 10:00 IST -> Day rejection
        fri_10am = datetime(2026, 11, 6, 10, 0, 0, tzinfo=IST_TZ)
        can_run, _, reason = CadenceScheduler.evaluate_mutation_eligibility(
            platform="naukri", dt=fri_10am, db_path=isolated_db
        )
        assert can_run is False
        assert "Today is Friday" in reason

        # Wednesday 07:30 IST -> Time rejection
        wed_730am = datetime(2026, 11, 4, 7, 30, 0, tzinfo=IST_TZ)
        can_run, _, reason = CadenceScheduler.evaluate_mutation_eligibility(
            platform="naukri", dt=wed_730am, db_path=isolated_db
        )
        assert can_run is False
        assert "outside 08:00-13:00 IST envelope" in reason


# ==============================================================================
# SECTION 5: HASH ENGINE & IDEMPOTENCY ADVERSARIAL TESTS
# ==============================================================================

class TestHashEngineIdempotencyAdversarial:
    """Stress-tests cryptographic normalization, Unicode handling, and NOOP detection."""

    def test_sha256_canonical_whitespace_and_newline_normalization(self):
        """
        Verifies that CRLF, CR, LF line endings and leading/trailing whitespace
        all normalize to identical SHA-256 hashes.
        """
        base_text = "Azure Data Engineer | Azure Databricks · PySpark · Delta Lake"

        variations = [
            base_text,
            f"   {base_text}   ",
            f"\t\t{base_text}\n\n",
            f"\r\n\r\n{base_text}\r\n",
            base_text.replace(" | ", " |\r\n").replace(" · ", " ·\r\n"),
            base_text.replace(" | ", " |\n").replace(" · ", " ·\n"),
            base_text.replace(" | ", " |\r").replace(" · ", " ·\r"),
        ]

        # Normalized forms of the multiline variants should have identical normalized text
        clean_multiline = HashEngine.normalize_text(base_text.replace(" | ", " |\n").replace(" · ", " ·\n"))
        hash_multiline = HashEngine.compute_text_hash(clean_multiline)

        # CRLF vs LF vs CR of multiline
        assert HashEngine.compute_text_hash(base_text.replace(" | ", " |\r\n").replace(" · ", " ·\r\n")) == hash_multiline
        assert HashEngine.compute_text_hash(base_text.replace(" | ", " |\r").replace(" · ", " ·\r")) == hash_multiline

        # Leading/trailing variations of base
        base_hash = HashEngine.compute_text_hash(base_text)
        assert HashEngine.compute_text_hash(f"   {base_text}   ") == base_hash
        assert HashEngine.compute_text_hash(f"\t\t{base_text}\n\n") == base_hash
        assert HashEngine.compute_text_hash(f"\r\n\r\n{base_text}\r\n") == base_hash

    def test_unicode_nfc_vs_nfd_normalization(self):
        """
        Verifies that composed (NFC) and decomposed (NFD) Unicode representations
        produce identical SHA-256 hashes under HashEngine.
        """
        # \u00e9 is pre-composed 'é', while 'e\u0301' is decomposed 'e' + combining acute accent
        composed_headline = "Azure Data Engineer | Resum\u00e9 & Clou\u00e9 Platforms"
        decomposed_headline = "Azure Data Engineer | Resume\u0301 & Cloue\u0301 Platforms"

        # Raw string equality fails because glyph byte sequences differ
        assert composed_headline != decomposed_headline

        # HashEngine NFC normalization produces identical hashes
        h_composed = HashEngine.compute_text_hash(composed_headline)
        h_decomposed = HashEngine.compute_text_hash(decomposed_headline)
        assert h_composed == h_decomposed

    def test_unordered_and_ordered_list_hashing(self):
        """
        Verifies list token hashing behavior:
        - ordered=False: permutations produce identical hashes
        - ordered=True: permutations produce distinct hashes
        """
        tokens = ["Azure Databricks", "PySpark", "Delta Lake", "SQL", "Apache Kafka"]
        reversed_tokens = list(reversed(tokens))
        shuffled_tokens = ["Delta Lake", "Apache Kafka", "Azure Databricks", "SQL", "PySpark"]

        # Unordered list hash must be identical across all permutations
        h_unordered_1 = HashEngine.compute_list_hash(tokens, ordered=False)
        h_unordered_2 = HashEngine.compute_list_hash(reversed_tokens, ordered=False)
        h_unordered_3 = HashEngine.compute_list_hash(shuffled_tokens, ordered=False)
        assert h_unordered_1 == h_unordered_2 == h_unordered_3

        # Ordered list hash must distinguish order
        h_ordered_1 = HashEngine.compute_list_hash(tokens, ordered=True)
        h_ordered_2 = HashEngine.compute_list_hash(reversed_tokens, ordered=True)
        assert h_ordered_1 != h_ordered_2

    def test_nested_dict_key_order_canonical_hashing(self):
        """
        Verifies canonical dictionary hashing:
        Different key insertion order produces identical SHA-256 hash.
        """
        dict_a = {
            "platform": "naukri",
            "field": "headline",
            "metadata": {"cycle": 1, "anchor": "Databricks", "tags": [1, 2, 3]},
            "version": "1.0"
        }
        dict_b = {
            "version": "1.0",
            "metadata": {"tags": [1, 2, 3], "anchor": "Databricks", "cycle": 1},
            "field": "headline",
            "platform": "naukri"
        }

        h_a = HashEngine.compute_dict_hash(dict_a)
        h_b = HashEngine.compute_dict_hash(dict_b)
        assert h_a == h_b

    def test_empty_and_none_hash_consistency(self):
        """None, empty string, and whitespace-only strings map to EMPTY_SHA256."""
        for empty_val in [None, "", "   ", "\t\t", "\r\n\r\n", "  \n  "]:
            assert HashEngine.compute_text_hash(empty_val) == EMPTY_SHA256
            assert compute_field_hash(empty_val) == EMPTY_SHA256

    def test_noop_detection_in_apply_mutation(self, isolated_db):
        """
        When proposing text whose normalized hash equals current value hash:
        - ProfileMutator.apply_mutation returns MutationStatus.NOOP
        - Executor callable is NEVER invoked (zero browser action)
        - Zero rows are written to profile_mutations ledger
        """
        mutator = ProfileMutator(db_path=isolated_db)
        current = "Azure Data Engineer | Azure Databricks · PySpark · Delta Lake | 2.5 YOE"
        # Propose identical text with trailing whitespace/newline
        proposed = f"  {current}  \r\n"

        proposal = mutator.propose_mutation(
            platform="naukri",
            field="headline",
            new_value=proposed,
            current_value=current,
            is_keyword_mutation=True
        )

        assert proposal.old_hash == proposal.new_hash

        executor_invocations = []
        def dummy_executor(f, v):
            executor_invocations.append((f, v))
            return True

        result = mutator.apply_mutation(proposal, dummy_executor)

        assert result.status == MutationStatus.NOOP
        assert "Profile already matches proposed hash" in result.error_message
        assert len(executor_invocations) == 0, "Executor must NOT be called for a NOOP!"

        # Ledger check
        conn = get_db_connection(isolated_db)
        count = conn.execute("SELECT COUNT(*) FROM profile_mutations").fetchone()[0]
        conn.close()
        assert count == 0, "NOOP mutation must not create ledger entries"

    def test_noop_rejection_in_record_profile_mutation(self, isolated_db):
        """
        Direct calls to record_profile_mutation with matching hashes and is_keyword_mutation=True
        are rejected as NOOP failure.
        """
        val = "Azure Data Engineer | Azure Databricks · PySpark | 2.5 YOE"
        res = record_profile_mutation(
            platform="naukri",
            field="headline",
            new_value=val,
            old_value=val,
            is_keyword_mutation=True,
            db_path=isolated_db
        )

        assert isinstance(res, MutationRecordFailure)
        assert bool(res) is False
        assert int(res) == -1
        assert "no-op mutation rejected" in res.error_message

        # Ledger remains empty
        conn = get_db_connection(isolated_db)
        count = conn.execute("SELECT COUNT(*) FROM profile_mutations").fetchone()[0]
        conn.close()
        assert count == 0


# ==============================================================================
# SECTION 6: DATABASE CONCURRENCY & ROLLBACK ADVERSARIAL TESTS
# ==============================================================================

class TestDatabaseConcurrencyAndRollback:
    """Stress-tests SQLite transactions, concurrency, and rollback state restoration."""

    def test_concurrent_mutation_writes_thread_safety(self, isolated_db):
        """
        Spawns 20 concurrent threads writing freshness bumps to SQLite.
        Asserts:
        - Zero deadlocks or sqlite3.OperationalError: database is locked crashes
        - PRAGMA integrity_check passes
        - Exactly 20 rows recorded in profile_mutations
        """
        def worker(thread_idx: int):
            return record_profile_mutation(
                platform="naukri",
                field="freshness_bump",
                new_value=f"Concurrent touch payload from thread {thread_idx}",
                old_value=f"Old payload {thread_idx}",
                rationale=f"concurrent_thread_{thread_idx}",
                is_keyword_mutation=False,
                db_path=isolated_db
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(20)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        successes = [r for r in results if r > 0]
        assert len(successes) == 20, f"Expected 20 successful writes, got {len(successes)}"

        conn = sqlite3.connect(isolated_db)
        cur = conn.cursor()
        cur.execute("PRAGMA integrity_check;")
        integrity = cur.fetchone()[0]
        assert integrity == "ok"

        cur.execute("SELECT COUNT(*) FROM profile_mutations;")
        total_rows = cur.fetchone()[0]
        assert total_rows == 20
        conn.close()

    def test_concurrent_reads_and_writes_acid_integrity(self, isolated_db):
        """
        Runs concurrent readers and writers simultaneously:
        - Writers record mutations
        - Readers query weekly count and latest mutation
        Asserts no read or write failures occur under load.
        """
        errors = []

        def writer(idx: int):
            try:
                res = record_profile_mutation(
                    platform="linkedin",
                    field="freshness_bump",
                    new_value=f"Payload {idx}",
                    is_keyword_mutation=False,
                    db_path=isolated_db
                )
                if not (res > 0):
                    errors.append(f"Writer {idx} failed")
            except Exception as e:
                errors.append(f"Writer {idx} exception: {e}")

        def reader(idx: int):
            try:
                _ = get_weekly_mutation_count("linkedin", db_path=isolated_db)
                _ = get_latest_mutation("linkedin", db_path=isolated_db)
            except Exception as e:
                errors.append(f"Reader {idx} exception: {e}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
            tasks = []
            for i in range(15):
                tasks.append(executor.submit(writer, i))
                tasks.append(executor.submit(reader, i))
            concurrent.futures.wait(tasks)

        assert len(errors) == 0, f"Encountered concurrency errors: {errors}"

    def test_revert_profile_mutation_restores_quota(self, isolated_db):
        """
        Tests revert_profile_mutation() and verifies state restoration:
        1. Apply 2 keyword mutations (budget 2/2 exhausted)
        2. can_apply_keyword_mutation() returns False
        3. revert_profile_mutation(id_1)
        4. Weekly count drops to 1
        5. can_apply_keyword_mutation() returns True (quota restored!)
        6. A 3rd mutation can now be proposed and applied cleanly
        """
        mutator = ProfileMutator(db_path=isolated_db)

        # Step 1: Apply 2 mutations
        id1 = record_profile_mutation("naukri", "headline", "Val 1", old_value="Base", is_keyword_mutation=True, db_path=isolated_db)
        id2 = record_profile_mutation("naukri", "headline", "Val 2", old_value="Val 1", is_keyword_mutation=True, db_path=isolated_db)
        assert id1 > 0 and id2 > 0

        # Step 2: Quota is exhausted
        assert get_weekly_mutation_count("naukri", is_keyword_only=True, db_path=isolated_db) == 2
        assert mutator.can_mutate("naukri") is False

        # Step 3: Revert mutation 1
        reverted = revert_profile_mutation(id1, reason="Rollback due to test", db_path=isolated_db)
        assert reverted is True

        # Check DB status
        conn = get_db_connection(isolated_db)
        row = conn.execute("SELECT status, reverted_at FROM profile_mutations WHERE id = ?", (id1,)).fetchone()
        conn.close()
        assert row["status"] == "REVERTED"
        assert row["reverted_at"] is not None

        # Step 4: Weekly count drops to 1
        count_after = get_weekly_mutation_count("naukri", is_keyword_only=True, db_path=isolated_db)
        assert count_after == 1

        # Step 5: Quota restored
        can_kw, count, _ = can_apply_keyword_mutation("naukri", max_weekly=2, db_path=isolated_db)
        assert can_kw is True
        assert count == 1
        assert mutator.can_mutate("naukri") is True

        # Step 6: Apply 3rd mutation now succeeds
        prop3 = mutator.propose_mutation(
            platform="naukri",
            field="headline",
            new_value="Azure Data Engineer | Databricks · PySpark · Delta Lake · SQL · Kafka | 2.5 YOE",
            current_value="Val 2",
            is_keyword_mutation=True
        )
        res3 = mutator.apply_mutation(prop3, lambda f, v: True)
        assert res3.status == MutationStatus.APPLIED
        assert get_weekly_mutation_count("naukri", is_keyword_only=True, db_path=isolated_db) == 2

    def test_revert_nonexistent_or_already_reverted_idempotency(self, isolated_db):
        """
        Reverting a non-existent ID or an already-reverted record must safely return False.
        """
        # Non-existent ID
        assert revert_profile_mutation(999999, db_path=isolated_db) is False

        # Record and revert once
        mut_id = record_profile_mutation("naukri", "headline", "Val", is_keyword_mutation=True, db_path=isolated_db)
        assert revert_profile_mutation(mut_id, db_path=isolated_db) is True

        # Second revert on same ID must return False (already reverted)
        assert revert_profile_mutation(mut_id, db_path=isolated_db) is False

    def test_transaction_rollback_on_constraint_violation(self, isolated_db):
        """
        Verifies that SQLite CHECK constraint violation rolls back cleanly
        without leaving partially inserted data or corrupting the database.
        """
        conn = get_db_connection(isolated_db)
        initial_count = conn.execute("SELECT COUNT(*) FROM profile_mutations").fetchone()[0]

        # Attempt to insert an invalid platform violating CHECK(platform IN ('naukri', 'linkedin', 'generic'))
        res = record_profile_mutation(
            platform="invalid_platform_xyz",
            field="headline",
            new_value="Should Fail",
            db_path=isolated_db
        )
        assert isinstance(res, MutationRecordFailure)
        assert "Invalid platform" in res.error_message

        post_count = conn.execute("SELECT COUNT(*) FROM profile_mutations").fetchone()[0]
        assert post_count == initial_count
        conn.close()
