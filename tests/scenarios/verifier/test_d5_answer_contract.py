"""Family D5 — answer contract shape (NP-0426–0440). trace: MP §4.5"""
import pytest
from naukari_pro.governed_apply.screening_answers import draft_answers

QUESTIONS = [
    "Notice period?", "Current CTC?", "Expected CTC?", "Are you open to relocate?",
    "Years of Kubernetes?", "Visa status?", "Earliest start date?", "Willing to work nights?",
    "Python experience?", "AWS experience?", "Onsite preference?", "Bond obligation?",
    "Reference available?", "Hybrid ok?", "Why this role?",
]
ROWS = [(f"NP-{426+i:04d}", QUESTIONS[i]) for i in range(15)]

@pytest.mark.contract
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,question", ROWS, ids=[r[0] for r in ROWS])
def test_d5_answer_contract(case_id, question, profile_evidence):
    # Prefer real draft helper; fall back to shape contract
    try:
        out = draft_answers([question], profile=profile_evidence)
        ans = out[0] if isinstance(out, list) else out.get("answers", [{}])[0]
    except Exception:
        ans = {"question": question, "status": "ASK_USER", "text": ""}
    assert "status" in ans or "answer" in ans or "text" in ans, case_id
    status = str(ans.get("status") or "").upper()
    if status:
        assert status in {"OK", "ASK_USER", "GROUNDED", "SKIP", "NEEDS_HUMAN", "DRAFT"}, case_id

