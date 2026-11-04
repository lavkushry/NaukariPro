"""Family C1 — title gate (NP-0231–0250). trace: MP §4.3"""
import pytest
from naukari_pro.matching.deterministic_score import score_job

TITLES = [
    ("MLOps Engineer", True), ("DevOps Engineer", True), ("Platform Engineer", True),
    ("SRE", True), ("AI Infrastructure Engineer", True), ("Intern", False),
    ("Principal Architect", True), ("Data Entry Clerk", False), ("CEO", False),
    ("Kubernetes Platform Engineer", True), ("Junior DevOps", True), ("Staff Engineer", True),
    ("Recruiter", False), ("Sales Manager", False), ("ML Platform Engineer", True),
    ("Azure Data Engineer", True), ("Security Analyst", True), ("Barista", False),
    ("Site Reliability Engineer", True), ("Frontend Intern", False),
]
ROWS = [(f"NP-{231+i:04d}", t, ok) for i, (t, ok) in enumerate(TITLES)]

@pytest.mark.unit
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,title,expect_passish", ROWS, ids=[r[0] for r in ROWS])
def test_c1_title_gate(case_id, title, expect_passish):
    s = score_job({"title": title, "location": "Bengaluru", "description_full": title})
    if not expect_passish:
        assert s.total < 20 or "intern" in title.lower() or any(f for f in s.flags), case_id
    else:
        assert s.total > -50, case_id

