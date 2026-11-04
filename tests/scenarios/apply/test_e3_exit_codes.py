"""Family E3 — exit codes 0/1/2/3/4 (NP-0615–0634). trace: MP §4.6"""
import pytest
from naukari_pro.governed_apply.exit_codes import (
    EXIT_OK, EXIT_SOFT_FAIL, EXIT_HARD_SKIP, EXIT_CAPTCHA_BLOCKED, EXIT_APPROVAL_DENIED, EXIT_LABELS,
)

MAPPING = [
    (0, EXIT_OK), (0, EXIT_OK), (0, EXIT_OK), (0, EXIT_OK),
    (1, EXIT_SOFT_FAIL), (1, EXIT_SOFT_FAIL), (1, EXIT_SOFT_FAIL), (1, EXIT_SOFT_FAIL),
    (2, EXIT_HARD_SKIP), (2, EXIT_HARD_SKIP), (2, EXIT_HARD_SKIP), (2, EXIT_HARD_SKIP),
    (3, EXIT_CAPTCHA_BLOCKED), (3, EXIT_CAPTCHA_BLOCKED), (3, EXIT_CAPTCHA_BLOCKED), (3, EXIT_CAPTCHA_BLOCKED),
    (4, EXIT_APPROVAL_DENIED), (4, EXIT_APPROVAL_DENIED), (4, EXIT_APPROVAL_DENIED), (4, EXIT_APPROVAL_DENIED),
]
ROWS = [(f"NP-{615+i:04d}", code, const) for i, (code, const) in enumerate(MAPPING)]

@pytest.mark.contract
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,code,const", ROWS, ids=[r[0] for r in ROWS])
def test_e3_exit_codes(case_id, code, const):
    assert code == const, case_id
    assert code in EXIT_LABELS, case_id
    assert EXIT_LABELS[code], case_id

