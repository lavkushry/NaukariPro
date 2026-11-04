"""Family D7 — tailoring determinism (NP-0471–0490). trace: MP §4.4"""
import pytest
from naukari_pro.resume_gen.claim_validator import validate_text

ROWS = [(f"NP-{471+i:04d}", i) for i in range(20)]
TEXT = "Reduced deployment time from 45 minutes to 12 minutes using Kubernetes."
EV = ["Reduced deployment time from 45 minutes to 12 minutes", "Kubernetes"]

@pytest.mark.unit
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,idx", ROWS, ids=[r[0] for r in ROWS])
def test_d7_tailoring_determinism(case_id, idx):
    a = validate_text(TEXT, EV).to_dict()
    b = validate_text(TEXT, EV).to_dict()
    assert a == b, case_id
    assert a["ok"] is True, case_id

