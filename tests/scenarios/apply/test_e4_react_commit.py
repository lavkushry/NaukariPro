"""Family E4 — React commit-and-verify (NP-0635–0646). trace: MP §4.6"""
import pytest
from naukari_pro.governed_apply.fill_verify import verify_field

ROWS = [(f"NP-{635+i:04d}", i % 2 == 0) for i in range(12)]

@pytest.mark.unit
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,committed", ROWS, ids=[r[0] for r in ROWS])
def test_e4_react_commit(case_id, committed):
    result = verify_field(
        field_id="react.name",
        expected="Lavkush",
        dom_value="Lavkush",  # page-visible
        check_validity=True,
        model_value="Lavkush" if committed else "",
        require_commit=True,
    )
    assert result.commit_verified is committed, case_id
    assert result.ok is committed, case_id

