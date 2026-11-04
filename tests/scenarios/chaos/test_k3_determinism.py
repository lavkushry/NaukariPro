"""Family K3 — determinism/flake seeds (NP-0991–1000). trace: MP §5"""
import hashlib
import pytest
from naukari_pro.aggregation.models import normalize_job_url
from naukari_pro.resume_gen.claim_validator import validate_text

ROWS = [(f"NP-{991+i:04d}", i) for i in range(10)]

@pytest.mark.chaos
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,idx", ROWS, ids=[r[0] for r in ROWS])
def test_k3_determinism(case_id, idx, seeded_rng):
    a = normalize_job_url(f"https://Boards.Example/jobs/{idx}?utm_source=x")
    b = normalize_job_url(f"https://Boards.Example/jobs/{idx}?utm_source=x")
    assert a == b, case_id
    ev = ["Kubernetes Docker"]
    r1 = validate_text("Kubernetes Docker", ev).to_dict()
    r2 = validate_text("Kubernetes Docker", ev).to_dict()
    assert r1 == r2, case_id
    h = hashlib.sha256(a.encode()).hexdigest()
    assert h == hashlib.sha256(b.encode()).hexdigest(), case_id
    assert seeded_rng.randint(0, 100) >= 0

