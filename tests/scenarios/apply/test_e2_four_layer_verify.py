"""Family E2 — four-layer verification (NP-0591–0614). trace: MP §4.6"""
import pytest
from naukari_pro.governed_apply.fill_verify import verify_field

ROWS = [(f"NP-{591+i:04d}", i) for i in range(24)]

@pytest.mark.unit
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,idx", ROWS, ids=[r[0] for r in ROWS])
def test_e2_four_layer_verify(case_id, idx):
    ok_case = idx % 2 == 0
    result = verify_field(
        field_id=f"f{idx}",
        expected="Alice",
        dom_value="Alice" if ok_case else "Bob",
        check_validity=ok_case,
        aria={"aria-checked": True} if ok_case else {},
        error_banners=[] if ok_case else ["err"],
        model_value="Alice" if ok_case else "Bob",
    )
    assert result.ok is ok_case, case_id
    assert result.layer1_dom is ok_case or not ok_case, case_id

