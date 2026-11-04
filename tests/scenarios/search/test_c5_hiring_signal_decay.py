"""Family C5 — hiring-signal decay math (NP-0306–0320). trace: MP §4.3"""
import json
import pytest

def decay(weight, strength, age_days):
    return weight * strength * (0.5 ** (age_days / 45.0))

ROWS = [(f"NP-{306+i:04d}", i) for i in range(15)]

@pytest.mark.unit
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,idx", ROWS, ids=[r[0] for r in ROWS])
def test_c5_hiring_signal_decay(case_id, idx, fixtures_root):
    vectors = json.loads((fixtures_root / "golden" / "vectors.json").read_text())["decay_vectors"]
    v = vectors[idx % len(vectors)]
    got = decay(v["weight"], v["strength"], v["age_days"])
    assert abs(got - v["expected"]) < 1e-6, f"{case_id} {got} != {v['expected']}"

