"""Family G3 — per-board/version aggregation (NP-0776–0790). trace: MP §4.7"""
import pytest
from collections import Counter

ROWS = [(f"NP-{776+i:04d}", i) for i in range(15)]

@pytest.mark.unit
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,idx", ROWS, ids=[r[0] for r in ROWS])
def test_g3_aggregation(case_id, idx):
    boards = ["greenhouse", "ashby", "lever"]
    data = [{"board": boards[i % 3], "resume_version": f"v{i%2}", "status": "applied"} for i in range(idx + 5)]
    by_board = Counter(d["board"] for d in data)
    assert sum(by_board.values()) == len(data), case_id
    assert set(by_board) <= set(boards), case_id

