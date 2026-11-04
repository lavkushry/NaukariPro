"""Family A3 — budget ledger (NP-0052–0066). trace: MP §4.1"""
import pytest
from naukari_pro.llm.ledger import SpendLedger, SpendEntry, estimate_cost

ROWS = [(f"NP-{52+i:04d}", i) for i in range(15)]

@pytest.mark.integration
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,idx", ROWS, ids=[r[0] for r in ROWS])
def test_a3_budget_ledger(case_id, idx, tmp_path):
    from datetime import datetime, timezone
    ledger = SpendLedger(path=tmp_path / "spend.jsonl", enable_sqlite=False)
    cost = estimate_cost("openai/gpt-4o-mini", 100 + idx, 50 + idx)
    assert cost >= 0, case_id
    entry = SpendEntry(
        ts=datetime.now(timezone.utc).isoformat(),
        prompt_id="P2",
        prompt_version="1",
        model="gpt-4o-mini",
        provider="openai",
        input_tokens=100,
        output_tokens=50,
        cost_usd=float(cost),
        cached=False,
        input_hash=f"h{{idx}}",
        status="ok",
        task="match_score",
    )
    ledger.record(entry)
    dumped = (tmp_path / "spend.jsonl").read_text(encoding="utf-8")
    assert "sk-" not in dumped, case_id
    assert "openai" in dumped, case_id

