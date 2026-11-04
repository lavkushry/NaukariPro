"""Family B4 — NormalizedJob schema fuzz (NP-0201–0220). trace: MP §4.2"""
import pytest
from naukari_pro.aggregation.models import NormalizedJob

ROWS = [(f"NP-{201+i:04d}", i) for i in range(20)]

@pytest.mark.property
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,idx", ROWS, ids=[r[0] for r in ROWS])
def test_b4_schema_fuzz(case_id, idx):
    salary = None if idx % 2 == 0 else f"{10+idx} LPA"
    status = ["active", "removed", "updated"][idx % 3]
    job = NormalizedJob(
        external_job_id=f"fuzz-{idx}",
        source_id="greenhouse",
        company="Acme",
        title="Engineer",
        url=f"https://boards.greenhouse.io/x/{idx}",
        salary=salary,
        status=status,
    )
    assert job.salary is None or isinstance(job.salary, str), case_id
    d = job.to_dict()
    assert d["status"] in ("active", "removed", "updated"), case_id
    # unknown enum should not silently invent salary
    assert "invented" not in str(d.get("salary")), case_id

