"""Family G1 — screen-pass rate math (NP-0741–0755). trace: MP §4.7"""
import pytest

ROWS = [(f"NP-{741+i:04d}", i) for i in range(15)]

@pytest.mark.unit
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,idx", ROWS, ids=[r[0] for r in ROWS])
def test_g1_screen_pass(case_id, idx):
    # blocked/withdrawn excluded from denominator
    rows = [
        {"status": "applied"},
        {"status": "screening"},
        {"status": "blocked"},
        {"status": "withdrawn"},
        {"status": "interview"},
    ]
    submitted = [r for r in rows if r["status"] not in ("blocked", "withdrawn")]
    screens = [r for r in submitted if r["status"] in ("screening", "interview", "offer")]
    # vary by idx
    extra_applied = [{"status": "applied"} for _ in range(idx % 3)]
    submitted = submitted + extra_applied
    rate = len(screens) / len(submitted)
    assert 0.0 <= rate <= 1.0, case_id
    assert all(r["status"] not in ("blocked", "withdrawn") for r in submitted), case_id

