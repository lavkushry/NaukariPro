"""Family D5 — answer contract shape (NP-0426–0440). trace: MP §4.5"""
import pytest
from naukari_pro.governed_apply.screening_answers import answer_screening_question

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
    ans = answer_screening_question(profile=profile_evidence, question=question)
    assert isinstance(ans, dict), case_id
    assert "reason" in ans and "answer" in ans, case_id
    assert ans["reason"] in ("ok", "ASK_USER"), case_id

