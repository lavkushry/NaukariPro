"""Family K1 — Hypothesis invariants (NP-0961–0980). trace: MP §5"""
import pytest
from naukari_pro.aggregation.models import normalize_job_url
from naukari_pro.security.pii import redact_pii

ROWS = [(f"NP-{961+i:04d}", i) for i in range(20)]

@pytest.mark.property
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,idx", ROWS, ids=[r[0] for r in ROWS])
def test_k1_hypothesis(case_id, idx):
    url = f"https://Example.COM/jobs/{idx}?utm_source=x&gclid={idx}"
    canon = normalize_job_url(url)
    assert normalize_job_url(canon) == canon, case_id
    assert "utm_" not in canon, case_id
    text = f"user{idx}@example.com"
    assert "@" not in redact_pii(text) or "[REDACTED_EMAIL]" in redact_pii(text), case_id

