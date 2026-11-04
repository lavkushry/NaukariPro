"""Family I3 — HMAC webhooks (NP-0891–0905). trace: MP §6"""
import hashlib, hmac, json, time
import pytest
from naukari_pro.api.app import verify_webhook_signature

ROWS = [(f"NP-{891+i:04d}", i) for i in range(15)]

@pytest.mark.redteam
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,idx", ROWS, ids=[r[0] for r in ROWS])
def test_i3_hmac_webhooks(case_id, idx):
    secret = "test-secret"
    payload = {"event": "job.found", "job_key": f"ashby:{idx}", "ts": 1_700_000_000}
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    good = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    assert verify_webhook_signature(raw, good, secret) is True, case_id
    if idx % 3 == 0:
        assert verify_webhook_signature(raw, "deadbeef", secret) is False, case_id
    elif idx % 3 == 1:
        tampered = raw + b"x"
        assert verify_webhook_signature(tampered, good, secret) is False, case_id
    else:
        assert verify_webhook_signature(raw, f"sha256={good}", secret) is True, case_id

