"""Family H4 — consultancy flagging (NP-0851–0860). trace: MP §4.8"""
import pytest
from naukari_pro.aggregation.india_geo import is_recruiter_consultancy

CASES = [
    ("TeamLease staffing for DevOps", True),
    ("Randstad recruitment agency", True),
    ("Flipkart Platform Engineering", False),
    ("body shop contract staffing", True),
    ("Razorpay Infrastructure", False),
    ("Quess manpower services", True),
    ("Google Hyderabad", False),
    ("third party payroll consultancy", True),
    ("Adecco hiring partner", True),
    ("Freshworks Engineering", False),
]
ROWS = [(f"NP-{851+i:04d}", t, e) for i, (t, e) in enumerate(CASES)]

@pytest.mark.unit
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,text,expect", ROWS, ids=[r[0] for r in ROWS])
def test_h4_consultancy(case_id, text, expect):
    assert is_recruiter_consultancy(text) is expect, case_id

