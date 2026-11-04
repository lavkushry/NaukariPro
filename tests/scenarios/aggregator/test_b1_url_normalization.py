"""Family B1 — URL normalization (NP-0091–0130). trace: MP §4.2"""
import pytest
from naukari_pro.aggregation.models import normalize_job_url

ROWS = [
    ("NP-0091", "https://Boards.Greenhouse.io/Acme/jobs/1/?utm_source=x&gclid=abc", "https://boards.greenhouse.io/Acme/jobs/1"),
    ("NP-0092", "https://boards.greenhouse.io/Acme/jobs/1", "https://boards.greenhouse.io/Acme/jobs/1"),
    ("NP-0093", "https://boards.greenhouse.io/Acme/jobs/1/", "https://boards.greenhouse.io/Acme/jobs/1"),
    ("NP-0094", "HTTP://BOARDS.GREENHOUSE.IO/Acme/jobs/1", "http://boards.greenhouse.io/Acme/jobs/1"),
    ("NP-0095", "https://www.boards.ashbyhq.com/co/job?ref=tw&fbclid=1", "https://boards.ashbyhq.com/co/job"),
    ("NP-0096", "https://jobs.lever.co/co/abc?utm_campaign=c", "https://jobs.lever.co/co/abc"),
    ("NP-0097", "https://company.wd1.myworkdayjobs.com/en-US/Careers/job/X?source=LinkedIn", "https://company.wd1.myworkdayjobs.com/en-US/Careers/job/X"),
    ("NP-0098", "https://boards.greenhouse.io/x/jobs/9#section", "https://boards.greenhouse.io/x/jobs/9"),
    ("NP-0099", "https://Boards.Greenhouse.io/Acme/jobs/1/?utm_source=x&gclid=abc&utm_term=y", None),
    ("NP-0100", "https://boards.greenhouse.io/Acme/jobs/1", None),
    ("NP-0101", "https://boards.greenhouse.io/Acme/jobs/1/?utm_term=y", None),
    ("NP-0102", "HTTP://BOARDS.GREENHOUSE.IO/Acme/jobs/1", None),
    ("NP-0103", "https://www.boards.ashbyhq.com/co/job?ref=tw&fbclid=1&utm_term=y", None),
    ("NP-0104", "https://jobs.lever.co/co/abc?utm_campaign=c", None),
    ("NP-0105", "https://company.wd1.myworkdayjobs.com/en-US/Careers/job/X?source=LinkedIn&utm_term=y", None),
    ("NP-0106", "https://boards.greenhouse.io/x/jobs/9#section", None),
    ("NP-0107", "https://Boards.Greenhouse.io/Acme/jobs/1/?utm_source=x&gclid=abc&utm_term=y", None),
    ("NP-0108", "https://boards.greenhouse.io/Acme/jobs/1", None),
    ("NP-0109", "https://boards.greenhouse.io/Acme/jobs/1/?utm_term=y", None),
    ("NP-0110", "HTTP://BOARDS.GREENHOUSE.IO/Acme/jobs/1", None),
    ("NP-0111", "https://www.boards.ashbyhq.com/co/job?ref=tw&fbclid=1&utm_term=y", None),
    ("NP-0112", "https://jobs.lever.co/co/abc?utm_campaign=c", None),
    ("NP-0113", "https://company.wd1.myworkdayjobs.com/en-US/Careers/job/X?source=LinkedIn&utm_term=y", None),
    ("NP-0114", "https://boards.greenhouse.io/x/jobs/9#section", None),
    ("NP-0115", "https://Boards.Greenhouse.io/Acme/jobs/1/?utm_source=x&gclid=abc&utm_term=y", None),
    ("NP-0116", "https://boards.greenhouse.io/Acme/jobs/1", None),
    ("NP-0117", "https://boards.greenhouse.io/Acme/jobs/1/?utm_term=y", None),
    ("NP-0118", "HTTP://BOARDS.GREENHOUSE.IO/Acme/jobs/1", None),
    ("NP-0119", "https://www.boards.ashbyhq.com/co/job?ref=tw&fbclid=1&utm_term=y", None),
    ("NP-0120", "https://jobs.lever.co/co/abc?utm_campaign=c", None),
    ("NP-0121", "https://company.wd1.myworkdayjobs.com/en-US/Careers/job/X?source=LinkedIn&utm_term=y", None),
    ("NP-0122", "https://boards.greenhouse.io/x/jobs/9#section", None),
    ("NP-0123", "https://Boards.Greenhouse.io/Acme/jobs/1/?utm_source=x&gclid=abc&utm_term=y", None),
    ("NP-0124", "https://boards.greenhouse.io/Acme/jobs/1", None),
    ("NP-0125", "https://boards.greenhouse.io/Acme/jobs/1/?utm_term=y", None),
    ("NP-0126", "HTTP://BOARDS.GREENHOUSE.IO/Acme/jobs/1", None),
    ("NP-0127", "https://www.boards.ashbyhq.com/co/job?ref=tw&fbclid=1&utm_term=y", None),
    ("NP-0128", "https://jobs.lever.co/co/abc?utm_campaign=c", None),
    ("NP-0129", "https://company.wd1.myworkdayjobs.com/en-US/Careers/job/X?source=LinkedIn&utm_term=y", None),
    ("NP-0130", "https://boards.greenhouse.io/x/jobs/9#section", None)
]

@pytest.mark.unit
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,raw,expected", ROWS, ids=[r[0] for r in ROWS])
def test_b1_url_normalization(case_id, raw, expected):
    got = normalize_job_url(raw)
    assert "utm_" not in got.lower(), case_id
    assert "gclid" not in got.lower(), case_id
    assert "fbclid" not in got.lower(), case_id
    if expected:
        assert got == expected, f"{case_id} {got} != {expected}"
    # canonical form stable
    assert normalize_job_url(got) == got, case_id

