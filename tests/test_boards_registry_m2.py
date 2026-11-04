"""M2: boards.csv registry + India geo aliases + CDX URL patterns (offline)."""

from __future__ import annotations

from pathlib import Path

from naukari_pro.aggregation.boards_registry import import_boards_csv, load_boards_csv, row_to_source
from naukari_pro.aggregation.discovery import parse_ats_from_url
from naukari_pro.aggregation.india_geo import (
    is_recruiter_consultancy,
    location_allows_india,
    normalize_location,
)
from naukari_pro.aggregation.models import NormalizedJob
from naukari_pro.aggregation.storage import AggregationStore


def test_boards_csv_loads():
    rows = load_boards_csv()
    assert len(rows) >= 4
    assert any(r["ats_type"] == "greenhouse" for r in rows)
    assert any(r["ats_type"] == "ashby" for r in rows)


def test_row_to_source_identity():
    src = row_to_source(
        {
            "company_slug": "notion",
            "board_slug": "notion",
            "board_url": "https://jobs.ashbyhq.com/notion",
            "monitor_type": "json_api",
            "monitor_config": '{"includeCompensation":true}',
            "scraper_type": "ashby",
        }
    )
    assert src["source_id"] == "ashby:notion"
    assert src["board_identifier"] == "notion"


def test_import_boards_into_store(tmp_path):
    store = AggregationStore(db_path=tmp_path / "agg.db")
    n = import_boards_csv(store=store)
    assert n >= 4
    sources = store.list_active_sources(include_quiet_every_n=1, cycle=0)
    ids = {s["source_id"] for s in sources}
    assert "greenhouse:gitlab" in ids


def test_cdx_patterns_workday_smartrecruiters_keka():
    assert parse_ats_from_url("https://acme.myworkdayjobs.com/en-US/Careers") == (
        "workday",
        "acme",
    )
    assert parse_ats_from_url("https://jobs.smartrecruiters.com/AcmeCorp") == (
        "smartrecruiters",
        "AcmeCorp",
    )
    assert parse_ats_from_url("https://foo.keka.com/careers") == ("keka", "foo")


def test_india_geo_aliases():
    assert normalize_location("Bangalore") == "bengaluru"
    assert normalize_location("Gurugram, Haryana") == "ncr"
    assert normalize_location("Remote (India)") == "remote_india"
    assert location_allows_india("Bengaluru") is True
    assert location_allows_india("Austin, TX") is False
    assert is_recruiter_consultancy("TeamLease staffing solutions") is True


def test_normalized_job_v2_fields_default_honest():
    job = NormalizedJob(
        external_job_id="1",
        source_id="greenhouse:x",
        company="X",
        title="Engineer",
        url="https://boards.greenhouse.io/x/jobs/1",
        ats_type="greenhouse",
    )
    assert job.apply_url is None
    assert job.salary_min is None
    assert job.salary_currency is None
    assert job.status == "active"
