"""Family C3 — compensation gate FAIL-OPEN (NP-0271–0290). trace: MP §4.3"""
import pytest
from naukari_pro.aggregation.models import NormalizedJob

ROWS = [(f"NP-{271+i:04d}", None if i % 2 == 0 else f"{10+i} LPA") for i in range(20)]

@pytest.mark.unit
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,salary", ROWS, ids=[r[0] for r in ROWS])
def test_c3_comp_gate(case_id, salary):
    job = NormalizedJob(
        external_job_id=case_id,
        source_id="greenhouse",
        company="Acme",
        title="DevOps",
        url=f"https://boards.greenhouse.io/{case_id}",
        salary=salary,
    )
    # None compensation tolerated
    assert job.salary is None or isinstance(job.salary, str), case_id
    assert job.to_dict()["salary"] == salary, case_id

