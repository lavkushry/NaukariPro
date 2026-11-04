"""WS1 aggregation: honest fields, adapters, dedup, storage, fixtures (no live HTTP)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import patch

from naukari_pro.aggregation.base import AdapterRegistry, SourceRecord
from naukari_pro.aggregation.dedup import DedupEngine, company_role_key, hamming_similarity, simhash64
from naukari_pro.aggregation.liveness import looks_closed
from naukari_pro.aggregation.models import NormalizedJob, normalize_job_url
from naukari_pro.aggregation.storage import AggregationStore
from naukari_pro.modules.career_portals import CURATED_ATS_VACANCIES, fetch_live_ats_vacancies

import naukari_pro.aggregation.adapters  # noqa: F401 — register adapters

FIXTURES = Path(__file__).parent / "fixtures" / "aggregation"


def test_adapters_registered():
    expected = {
        "greenhouse", "ashby", "lever", "workday", "smartrecruiters",
        "workable", "recruitee", "teamtailor", "pinpoint", "bamboohr",
        "icims", "keka",
    }
    assert expected.issubset(set(AdapterRegistry.known()))


def test_normalize_job_url_strips_tracking():
    u = normalize_job_url(
        "https://WWW.Example.com/jobs/1/?utm_source=x&gh_src=abc&keep=1#frag"
    )
    assert "utm_source" not in u
    assert "gh_src" not in u
    assert "keep=1" in u
    assert "www." not in u
    assert "#" not in u


def test_normalized_job_never_invents_salary_exp():
    job = NormalizedJob(
        external_job_id="1",
        source_id="greenhouse:gitlab",
        company="GitLab",
        title="Engineer",
        url="https://job-boards.greenhouse.io/gitlab/jobs/1",
        ats_type="greenhouse",
    )
    legacy = job.to_legacy_vacancy()
    assert legacy["exp"] is None
    assert legacy["salary"] is None
    assert legacy["jd"] is None


def test_curated_vacancies_have_null_unfetched_fields():
    for v in CURATED_ATS_VACANCIES:
        assert v.get("exp") is None
        assert v.get("salary") is None
        assert v.get("jd") is None


def test_fetch_live_ats_vacancies_honest_nulls():
    mock_gh = {
        "jobs": [
            {
                "title": "Lead Cloud Data Engineer",
                "absolute_url": "https://job-boards.greenhouse.io/gitlab/jobs/99901",
                "location": {"name": "Remote"},
                "content": "<p>Real JD from Greenhouse</p>",
            },
            {
                "title": "Sales Representative",
                "absolute_url": "https://job-boards.greenhouse.io/gitlab/jobs/99902",
                "location": {"name": "Remote"},
            },
        ]
    }

    class _Resp:
        status_code = 200

        def __init__(self, payload):
            self._payload = payload

        def json(self):
            return self._payload

    def fake_get(url, timeout=5):
        if "greenhouse" in url:
            return _Resp(mock_gh)
        return _Resp({"jobs": []})

    def fake_post(url, json=None, timeout=6):
        return _Resp({"jobPostings": []})

    with patch("requests.get", side_effect=fake_get), patch("requests.post", side_effect=fake_post):
        vacancies = fetch_live_ats_vacancies(limit=5)
        assert len(vacancies) >= 1
        v = vacancies[0]
        assert "Data Engineer" in v["title"]
        assert v["ats"] == "Greenhouse"
        assert v["exp"] is None
        assert v["salary"] is None
        # JD only when API returned content
        assert v["jd"] == "<p>Real JD from Greenhouse</p>"


def test_greenhouse_adapter_fixture():
    payload = json.loads((FIXTURES / "greenhouse_gitlab_jobs.json").read_text())
    source = SourceRecord(
        company="GitLab",
        ats_type="greenhouse",
        board_identifier="gitlab",
    )
    adapter = AdapterRegistry.get("greenhouse")()

    async def fake_http_json(url, **kwargs):
        assert "content=true" in url
        return 200, payload

    async def _run():
        with patch(
            "naukari_pro.aggregation.adapters.greenhouse.http_json",
            side_effect=fake_http_json,
        ):
            return await adapter.fetch_jobs(source)

    result = asyncio.run(_run())
    assert result.status_code == 200
    assert len(result.jobs) == 2
    eng = result.jobs[0]
    assert eng.title == "Lead Cloud Data Engineer"
    assert eng.experience_required is None
    assert eng.salary is None
    assert eng.description_full and "Kubernetes" in eng.description_full


def test_dedup_url_ats_simhash(tmp_path):
    engine = DedupEngine(simhash_threshold=0.92)
    a = NormalizedJob(
        external_job_id="1",
        source_id="greenhouse:x",
        company="Acme",
        title="Data Engineer",
        url="https://boards.greenhouse.io/acme/jobs/1?utm_source=li",
        description_full="Build pipelines with Python Spark Airflow Azure Databricks Delta Lake SQL",
        ats_type="greenhouse",
    )
    engine.remember(a)
    # Same URL different query → duplicate
    b = NormalizedJob(
        external_job_id="2",
        source_id="greenhouse:x",
        company="Acme",
        title="Data Engineer",
        url="https://boards.greenhouse.io/acme/jobs/1",
        description_full="totally different text about sales quotas and CRM tools",
        ats_type="greenhouse",
    )
    d1 = engine.check(b)
    assert d1.is_duplicate and d1.reason == "url"

    # Near-identical JD → simhash duplicate (same token stream, trivial edit)
    engine2 = DedupEngine()
    engine2.remember(a)
    near = (
        "Build pipelines with Python Spark Airflow Azure Databricks Delta Lake SQL. "
        "Own ingestion reliability and lakehouse quality checks across Azure."
    )
    a_long = NormalizedJob(
        external_job_id="1b",
        source_id="greenhouse:x",
        company="Acme",
        title="Data Engineer",
        url="https://boards.greenhouse.io/acme/jobs/1b",
        description_full=near,
        ats_type="greenhouse",
    )
    engine2.remember(a_long)
    c = NormalizedJob(
        external_job_id="99",
        source_id="lever:y",
        company="OtherCo",
        title="Platform Engineer",
        url="https://jobs.lever.co/other/99",
        description_full=near + " ",  # whitespace-only edit; same shingles
        ats_type="lever",
    )
    d2 = engine2.check(c)
    assert d2.is_duplicate
    assert d2.reason == "simhash"
    assert d2.similarity is not None and d2.similarity >= 0.92


def test_simhash_identical_is_one():
    t = "alpha beta gamma delta epsilon zeta eta theta"
    assert hamming_similarity(simhash64(t), simhash64(t)) == 1.0


def test_storage_upsert_and_immutable_first_seen(tmp_path):
    store = AggregationStore(db_path=tmp_path / "agg.db")
    job = NormalizedJob(
        external_job_id="10",
        source_id="greenhouse:t",
        company="TestCo",
        title="Engineer",
        url="https://example.com/jobs/10",
        description_full="v1 description",
        ats_type="greenhouse",
        first_seen_at="2026-01-01T00:00:00+00:00",
    )
    r1 = store.upsert_job(job)
    assert r1.status == "inserted"
    job2 = NormalizedJob(
        external_job_id="10",
        source_id="greenhouse:t",
        company="TestCo",
        title="Engineer II",
        url="https://example.com/jobs/10",
        description_full="v2 description changed",
        ats_type="greenhouse",
        first_seen_at="2099-01-01T00:00:00+00:00",  # must not overwrite
    )
    r2 = store.upsert_job(job2)
    assert r2.status == "updated"
    active = store.list_active_jobs()
    assert len(active) == 1
    assert active[0].first_seen_at.startswith("2026-01-01")
    assert active[0].title == "Engineer II"


def test_liveness_closed_phrasings():
    assert looks_closed("Sorry, this job is no longer available on our site.")
    assert looks_closed("This posting has been closed.")
    assert not looks_closed("We are actively hiring for this role. Apply today.")


def test_company_role_key_stable():
    assert company_role_key("Acme Inc.", "Sr. Data Engineer") == company_role_key("acme inc", "sr data engineer")


def test_sources_json_seedable(tmp_path):
    from naukari_pro.aggregation.pipeline import AggregationPipeline

    store = AggregationStore(db_path=tmp_path / "agg.db")
    pipe = AggregationPipeline(store=store)
    n = pipe.seed_sources()
    assert n >= 50
    stats = store.stats()
    assert stats["active_sources"] >= 40
