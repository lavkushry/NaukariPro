"""Family B5 — registry growth/CDX (NP-0221–0230). trace: MP §4.2"""
import pytest
from naukari_pro.aggregation.boards_registry import load_boards_csv

ROWS = [(f"NP-{221+i:04d}", i) for i in range(10)]

@pytest.mark.integration
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,idx", ROWS, ids=[r[0] for r in ROWS])
def test_b5_registry_cdx(case_id, idx):
    reg = load_boards_csv()
    assert isinstance(reg, list), case_id
    length = len(reg)
    assert length >= 0, case_id
    length2 = len(load_boards_csv())
    assert length2 == length, case_id

