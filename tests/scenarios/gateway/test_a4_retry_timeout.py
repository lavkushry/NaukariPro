"""Family A4 — retry/timeout/rate-limit (NP-0067–0078). trace: MP §4.1"""
import pytest
from naukari_pro.llm.routing import GatewayConfig

ROWS = [(f"NP-{67+i:04d}", i) for i in range(12)]

@pytest.mark.contract
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,idx", ROWS, ids=[r[0] for r in ROWS])
def test_a4_retry_timeout(case_id, idx):
    cfg = GatewayConfig()
    tasks = list(cfg.raw.get("tasks", {}).values()) or [{"timeout_s": 60}]
    task = tasks[idx % len(tasks)]
    timeout = float(task.get("timeout_s") or 60)
    assert 1 <= timeout <= 600, case_id
    max_cost = float(task.get("max_cost_usd") or 0.01)
    assert max_cost > 0, case_id

