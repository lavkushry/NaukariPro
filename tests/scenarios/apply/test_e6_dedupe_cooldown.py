"""Family E6 — dedupe + 15-day cooldown (NP-0657–0666). trace: MP §4.6"""
import pytest
from naukari_pro.governed_apply.dedupe_rules import CompanyDedupeLedger, EXIT_HARD_SKIP

ROWS = [(f"NP-{657+i:04d}", i) for i in range(10)]

@pytest.mark.integration
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,idx", ROWS, ids=[r[0] for r in ROWS])
def test_e6_dedupe_cooldown(case_id, idx, tmp_path):
    ledger = CompanyDedupeLedger(db_path=tmp_path / "dedupe.db", cooldown_days=15)
    company = f"Acme{idx % 3}"
    first = ledger.check(company, employer_job_id=f"j-{idx}")
    assert first.allow is True, case_id
    ledger.record(company, employer_job_id=f"j-{idx}", job_url=f"https://x/{idx}")
    second = ledger.check(company, employer_job_id=f"j-{idx}")
    assert second.allow is False, case_id
    assert second.exit_code == EXIT_HARD_SKIP, case_id

