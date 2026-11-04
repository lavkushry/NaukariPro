"""Family E5 — approval tokens (NP-0647–0656). trace: MP §4.6"""
import pytest
from naukari_pro.governed_apply.approval import ApprovalQueue
from naukari_pro.governed_apply.exit_codes import EXIT_APPROVAL_DENIED

ROWS = [(f"NP-{647+i:04d}", i) for i in range(10)]

@pytest.mark.redteam
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,idx", ROWS, ids=[r[0] for r in ROWS])
def test_e5_approval_tokens(case_id, idx, tmp_path):
    q = ApprovalQueue(db_path=tmp_path / "appr.db")
    items = q.enqueue_batch([{"url": f"https://job/{idx}", "company": "Acme", "title": "DevOps", "fit_score": 0.8}])
    token = items[0].token
    if idx == 0:
        assert q.decide("", approve=True) is False, case_id
        assert EXIT_APPROVAL_DENIED == 4
    elif idx == 1:
        assert q.decide(token, approve=True) is True, case_id
    elif idx == 2:
        assert q.decide(token, approve=True) is True
        assert q.decide(token, approve=True) is False, case_id  # reuse denied
    else:
        assert q.decide("totally-wrong-token", approve=True) is False, case_id
        assert token != "totally-wrong-token", case_id

