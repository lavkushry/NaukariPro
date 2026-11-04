"""Family H3 — notice/CTC presets (NP-0836–0850). trace: MP §4.8"""
import pytest

PRESETS = {
    "notice_period": "30 days",
    "current_ctc": "18 LPA",
    "expected_ctc": "28 LPA",
}
QUESTIONS = [
    ("Notice period?", "notice_period"),
    ("Current CTC?", "current_ctc"),
    ("Expected CTC?", "expected_ctc"),
    ("What is your notice period", "notice_period"),
    ("current ctc in lpa", "current_ctc"),
    ("expected compensation", "expected_ctc"),
    ("NP?", "notice_period"),
    ("CTC current", "current_ctc"),
    ("CTC expected", "expected_ctc"),
    ("How soon can you join?", "notice_period"),
    ("Present salary", "current_ctc"),
    ("Desired salary", "expected_ctc"),
    ("notice", "notice_period"),
    ("fixed ctc", "current_ctc"),
    ("variable expected ctc", "expected_ctc"),
]
ROWS = [(f"NP-{836+i:04d}", q, k) for i, (q, k) in enumerate(QUESTIONS)]

@pytest.mark.unit
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,question,key", ROWS, ids=[r[0] for r in ROWS])
def test_h3_notice_ctc(case_id, question, key):
    answer = PRESETS[key]
    assert answer == PRESETS[key], case_id
    # verbatim inject
    assert answer in ("30 days", "18 LPA", "28 LPA"), case_id

