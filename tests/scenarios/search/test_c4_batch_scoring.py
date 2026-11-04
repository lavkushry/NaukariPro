"""Family C4 — batch scoring JSON schema (NP-0291–0305). trace: MP §4.3"""
import json
import pytest
from pathlib import Path
from naukari_pro.matching.deterministic_score import score_job

ROWS = [(f"NP-{291+i:04d}", i) for i in range(15)]

@pytest.mark.contract
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,idx", ROWS, ids=[r[0] for r in ROWS])
def test_c4_batch_scoring(case_id, idx, fixtures_root):
    jobs = json.loads((fixtures_root / "boards" / "india_jobs_200.json").read_text())
    job = jobs[idx]
    s = score_job(job)
    payload = {"job_id": job["external_job_id"], "score": s.total, "flags": s.flags}
    assert isinstance(payload["score"], (int, float)), case_id
    assert isinstance(payload["flags"], list), case_id
    json.dumps(payload)

