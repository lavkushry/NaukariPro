"""Family G4 — notification triggers (NP-0791–0800). trace: MP §4.7"""
import pytest
from naukari_pro.tracking.notifications import NotificationQueue

ROWS = [(f"NP-{791+i:04d}", i) for i in range(10)]

@pytest.mark.integration
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,idx", ROWS, ids=[r[0] for r in ROWS])
def test_g4_notifications(case_id, idx, tmp_path):
    q = NotificationQueue(db_path=tmp_path / "n.db")
    channel = ["screen_pass", "blocked", "submitted"][idx % 3]
    ok = q.enqueue(user_id="u1", job_key=f"j-{idx}", channel=channel, payload="{{}}")
    assert ok is True, case_id
    dup = q.enqueue(user_id="u1", job_key=f"j-{idx}", channel=channel, payload="{{}}")
    assert dup is False, case_id

