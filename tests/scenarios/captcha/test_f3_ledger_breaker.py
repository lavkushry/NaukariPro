"""Family F3 — ledger + circuit breaker + exit 3 (NP-0725–0740). trace: MP §4.9"""
import pytest
from naukari_pro.governed_apply.captcha_safety import (
    CaptchaSafetyManager,
    EXIT_CAPTCHA_BLOCKED,
    Resolution,
)

ROWS = [(f"NP-{725+i:04d}", i) for i in range(16)]

@pytest.mark.integration
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,idx", ROWS, ids=[r[0] for r in ROWS])
def test_f3_ledger_breaker(case_id, idx, tmp_sqlite_wal):
    board = f"board-{idx % 3}"
    mgr = CaptchaSafetyManager(mode="human", db_path=tmp_sqlite_wal, board=board)
    # seed unresolved
    for _ in range(min(idx, 6)):
        CaptchaSafetyManager(mode="human", db_path=tmp_sqlite_wal, board=board).handle(
            captcha_type="hcaptcha", page_url="https://boards.greenhouse.io/x"
        )
    result = mgr.handle(captcha_type="hcaptcha", page_url="https://boards.greenhouse.io/x")
    assert result.exit_code == EXIT_CAPTCHA_BLOCKED, case_id
    assert result.resolution in (Resolution.NEEDS_HUMAN, Resolution.CIRCUIT_OPEN, Resolution.VENDOR_DENIED), case_id
    if idx >= 5:
        # after ≥5 unresolved, circuit should open on subsequent handle
        tripped = CaptchaSafetyManager(mode="vendor", api_key="k", domains=["*"], db_path=tmp_sqlite_wal, board=board, vendor_callable=lambda **k: True).handle(
            captcha_type="hcaptcha", page_url="https://boards.greenhouse.io/x"
        )
        assert tripped.resolution == Resolution.CIRCUIT_OPEN or tripped.exit_code == EXIT_CAPTCHA_BLOCKED, case_id

