"""Connector fleet repair R1–R6: board_health, contracts, workday caps, posture, gates."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from naukari_pro.aggregation.adapters.workday import (
    DETAIL_BUDGET,
    MAX_PAGES,
    PAGE_SIZE,
    WorkdayAdapter,
    parse_workday_posted_on,
    role_scope_g1_pass,
)
from naukari_pro.aggregation.base import AdapterRegistry, FetchResult, SourceRecord
from naukari_pro.aggregation.browser_posture import (
    MODE_FULL,
    MODE_LITE,
    ChallengeStop,
    DiscoveryLead,
    classify_parse_count,
    enable_linkedin_full,
    handle_challenge_stop,
    is_connector_disabled,
    leads_to_registry_candidates,
    linkedin_mode,
)
from naukari_pro.aggregation.gates import (
    MIN_HEALTHY_BOARDS_SUBMIT,
    SubmitBootBlocked,
    assert_submit_boot_healthy,
    dead_board_alarm,
    evaluate_gates,
)
from naukari_pro.aggregation.ingest_lock import IngestLockError, acquire_ingest_lock, release_ingest_lock
from naukari_pro.aggregation.models import NormalizedJob
from naukari_pro.aggregation.observe import build_7d_digest, write_7d_digest
from naukari_pro.aggregation.pipeline import AggregationPipeline
from naukari_pro.aggregation.storage import AggregationStore

import naukari_pro.aggregation.adapters  # noqa: F401

FIXTURES = Path(__file__).parent / "fixtures" / "aggregation"
LIVE_BOARDS = Path(__file__).parent / "fixtures" / "boards"
REPAIR_LOG = Path(__file__).resolve().parents[1] / "docs" / "CONNECTOR_REPAIR_LOG.md"


def test_g1_repair_log_bisect_recorded():
    text = REPAIR_LOG.read_text(encoding="utf-8")
    assert "Phase 0" in text
    assert "aggregator_ok" in text
    assert "Probe classification" in text


def test_golden_fixture_e2e_board_health_and_cycle(tmp_path):
    """G-5: golden greenhouse fixture → store + board_health.fetch_ok + cycle_log."""
    payload = json.loads((FIXTURES / "greenhouse_gitlab_jobs.json").read_text())
    db = tmp_path / "agg.db"
    store = AggregationStore(db_path=db)
    store.upsert_source(
        {
            "source_id": "greenhouse:gitlab",
            "company": "GitLab",
            "ats_type": "greenhouse",
            "board_identifier": "gitlab",
            "active": True,
        }
    )
    pipe = AggregationPipeline(store=store)

    async def fake_http_json(url, **kwargs):
        return 200, payload

    async def _run():
        with patch(
            "naukari_pro.aggregation.adapters.greenhouse.http_json",
            side_effect=fake_http_json,
        ):
            # Disable jitter for speed
            with patch.object(pipe, "_fetch_one", wraps=pipe._fetch_one):
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    return await pipe.run(limit_sources=1)

    stats = asyncio.run(_run())
    assert stats.inserted >= 1
    assert stats.sources_ok == 1
    assert stats.empty_success_rejected == 0
    with store._connect() as conn:
        health = conn.execute(
            "SELECT fetch_ok, jobs_new, jobs_seen FROM board_health WHERE source_id=?",
            ("greenhouse:gitlab",),
        ).fetchone()
        cycles = conn.execute("SELECT event FROM cycle_log ORDER BY id").fetchall()
        drops = conn.execute("SELECT COUNT(*) c FROM drop_events").fetchone()["c"]
    assert health is not None
    assert int(health["fetch_ok"]) >= 1
    assert int(health["jobs_new"]) >= 1
    assert [c["event"] for c in cycles] == ["cycle_started", "cycle_done"]
    assert drops >= 0  # may be zero if nothing filtered


def test_empty_board_fail_closed_emits_drop(tmp_path):
    db = tmp_path / "agg.db"
    store = AggregationStore(db_path=db)
    store.upsert_source(
        {
            "source_id": "lever:emptyco",
            "company": "EmptyCo",
            "ats_type": "lever",
            "board_identifier": "emptyco",
            "active": True,
        }
    )
    pipe = AggregationPipeline(store=store)

    async def fake_http_json(url, **kwargs):
        return 200, []

    async def _run():
        with patch(
            "naukari_pro.aggregation.adapters.lever.http_json",
            side_effect=fake_http_json,
        ), patch("asyncio.sleep", new_callable=AsyncMock):
            return await pipe.run(limit_sources=1)

    stats = asyncio.run(_run())
    assert stats.empty_success_rejected == 1
    assert stats.sources_ok == 0
    with store._connect() as conn:
        row = conn.execute(
            "SELECT reason FROM drop_events WHERE source_id=?",
            ("lever:emptyco",),
        ).fetchone()
        health = conn.execute(
            "SELECT fetch_ok, fetch_err FROM board_health WHERE source_id=?",
            ("lever:emptyco",),
        ).fetchone()
    assert row["reason"] == "empty_board"
    assert int(health["fetch_ok"]) == 0
    assert int(health["fetch_err"]) >= 1


@pytest.mark.parametrize(
    "ats,fixture,board_id,company,patch_target",
    [
        (
            "greenhouse",
            "greenhouse_live_2026-11-08.json",
            "gitlab",
            "GitLab",
            "naukari_pro.aggregation.adapters.greenhouse.http_json",
        ),
        (
            "lever",
            "lever_live_2026-11-08.json",
            "palantir",
            "Palantir",
            "naukari_pro.aggregation.adapters.lever.http_json",
        ),
        (
            "ashby",
            "ashby_live_2026-11-08.json",
            "ashby",
            "Ashby",
            "naukari_pro.aggregation.adapters.ashby.http_json",
        ),
    ],
)
def test_json_board_contract_live_fixture(ats, fixture, board_id, company, patch_target):
    path = LIVE_BOARDS / fixture
    assert path.exists(), f"missing live fixture {path}"
    payload = json.loads(path.read_text(encoding="utf-8"))
    source = SourceRecord(company=company, ats_type=ats, board_identifier=board_id)
    adapter = AdapterRegistry.get(ats)()

    async def fake_http_json(url, **kwargs):
        return 200, payload

    result = asyncio.run(
        asyncio.wait_for(
            _patched_fetch(adapter, source, patch_target, fake_http_json),
            timeout=5,
        )
    )
    assert result.status_code == 200
    assert result.jobs, f"{ats} contract: expected ≥1 job"
    job = result.jobs[0]
    assert job.ats_job_key.startswith(f"{ats}:")
    assert job.title
    assert job.url


async def _patched_fetch(adapter, source, patch_target, fake_http_json):
    with patch(patch_target, side_effect=fake_http_json):
        return await adapter.fetch_jobs(source)


def test_ashby_null_jobs_is_board_missing():
    source = SourceRecord(company="Bad", ats_type="ashby", board_identifier="nope")
    adapter = AdapterRegistry.get("ashby")()

    async def fake_http_json(url, **kwargs):
        return 200, {"jobs": None}

    result = asyncio.run(
        _patched_fetch(
            adapter,
            source,
            "naukari_pro.aggregation.adapters.ashby.http_json",
            fake_http_json,
        )
    )
    assert result.board_missing is True
    assert not result.jobs


def test_workday_page_cap_and_detail_budget():
    assert MAX_PAGES == 10
    assert PAGE_SIZE == 20
    assert DETAIL_BUDGET == 60
    assert role_scope_g1_pass("Senior Platform Engineer")
    assert not role_scope_g1_pass("Retail Sales Associate")
    assert parse_workday_posted_on("Posted 3 Days Ago") is not None
    assert parse_workday_posted_on("not-a-date-xyz") is None


def test_workday_identity_and_page_cap_enforced(tmp_path):
    source = SourceRecord(
        company="NVIDIA",
        ats_type="workday",
        board_identifier="nvidia.wd5.myworkdayjobs.com|nvidia|NVIDIAExternalCareerSite",
        domain="nvidia.wd5.myworkdayjobs.com",
    )
    adapter = WorkdayAdapter()
    pages_seen = {"n": 0}

    async def fake_http_json(url, method="GET", json_body=None, **kwargs):
        if method == "POST":
            pages_seen["n"] += 1
            # Always return a full page so adapter would keep paging without cap
            batch = [
                {
                    "title": f"Platform Engineer {i}",
                    "externalPath": f"/job/{i}",
                    "locationsText": "Remote",
                    "postedOn": "Posted Today",
                }
                for i in range(PAGE_SIZE)
            ]
            return 200, {"total": 5000, "jobPostings": batch}
        # detail GET
        return 200, {"jobPostingInfo": {"jobRequisitionId": "REQ-1", "jobDescription": "JD"}}

    result = asyncio.run(
        _patched_fetch(
            adapter,
            source,
            "naukari_pro.aggregation.adapters.workday.http_json",
            fake_http_json,
        )
    )
    assert pages_seen["n"] == MAX_PAGES
    assert len(result.jobs) == MAX_PAGES * PAGE_SIZE
    assert result.jobs[0].ats_job_key.startswith("workday:nvidia:NVIDIAExternalCareerSite:")


def test_linkedin_lite_default_and_full_opt_in(tmp_path):
    store = AggregationStore(db_path=tmp_path / "a.db")
    assert linkedin_mode(store) == MODE_LITE
    enable_linkedin_full(store, actor="test")
    assert linkedin_mode(store) == MODE_FULL
    leads = [
        DiscoveryLead(
            title="DevOps Engineer",
            company="Acme",
            location="Bengaluru",
            url="https://jobs.lever.co/acme/1",
        )
    ]
    cands = leads_to_registry_candidates(leads)
    assert cands[0]["needs_probe"] is True


def test_challenge_stop_self_disables_24h(tmp_path):
    store = AggregationStore(db_path=tmp_path / "b.db")
    stop = handle_challenge_stop(
        store,
        connector="linkedin",
        challenge_type="unusual_activity",
        screenshot_path="/tmp/shot.png",
    )
    assert isinstance(stop, ChallengeStop)
    assert is_connector_disabled(store, "linkedin") is True
    with store._connect() as conn:
        drop = conn.execute(
            "SELECT reason FROM drop_events WHERE reason='challenge_stop'"
        ).fetchone()
        health = conn.execute(
            "SELECT fetch_err FROM board_health WHERE source_id='browser:linkedin'"
        ).fetchone()
    assert drop is not None
    assert int(health["fetch_err"]) >= 1


def test_naukri_parse_minimum_f3():
    assert classify_parse_count(3) is not None
    assert classify_parse_count(5) is None


def test_discovery_verify_requires_jobs():
    from naukari_pro.aggregation.discovery import verify_board_live

    class _Adapter:
        async def fetch_jobs(self, source):
            return FetchResult(jobs=[], status_code=200)

    with patch.object(AdapterRegistry, "get", return_value=lambda: _Adapter()):
        ok = asyncio.run(verify_board_live("greenhouse", "empty", require_jobs=True, max_retries=2))
    assert ok is False


def test_ingest_lock_stale_and_busy(tmp_path):
    lock = tmp_path / "ingest.lock"
    acquire_ingest_lock(lock)
    with pytest.raises(IngestLockError):
        acquire_ingest_lock(lock)
    release_ingest_lock(lock)
    # stale clear
    lock.write_text(json.dumps({"pid": 99999999, "started_at": 0}), encoding="utf-8")
    path = acquire_ingest_lock(lock, stale_seconds=1)
    assert path.exists()
    release_ingest_lock(lock)


def test_submit_boot_requires_healthy_boards(tmp_path):
    store = AggregationStore(db_path=tmp_path / "c.db")
    with pytest.raises(SubmitBootBlocked):
        assert_submit_boot_healthy(store, minimum=MIN_HEALTHY_BOARDS_SUBMIT)
    for i in range(4):
        sid = f"greenhouse:board{i}"
        store.upsert_source(
            {
                "source_id": sid,
                "company": f"Co{i}",
                "ats_type": "greenhouse",
                "board_identifier": f"board{i}",
                "active": True,
            }
        )
        store.bump_board_health(sid, ats_type="greenhouse", fetch_ok=1, jobs_new=1, fetch_attempts=1)
    boards = assert_submit_boot_healthy(store)
    assert len(boards) >= 4


def test_gates_evaluate_and_observe(tmp_path):
    store = AggregationStore(db_path=tmp_path / "d.db")
    for i, ats in enumerate(("greenhouse", "lever", "ashby", "workday")):
        sid = f"{ats}:x{i}"
        store.upsert_source(
            {
                "source_id": sid,
                "company": f"C{i}",
                "ats_type": ats,
                "board_identifier": f"x{i}",
                "active": True,
            }
        )
        store.bump_board_health(sid, ats_type=ats, fetch_ok=1, jobs_new=1, fetch_attempts=1)
    store.record_cycle("c1", "cycle_started", {})
    store.record_cycle("c1", "cycle_done", {"jobs_new": 1})
    report = evaluate_gates(store, repair_log=REPAIR_LOG)
    assert report.to_dict()["gates"]
    assert any(g.gate_id == "G-1" and g.passed for g in report.gates)
    digest = build_7d_digest(store)
    assert "window_days" in digest
    path = write_7d_digest(store, dest_dir=tmp_path / "obs")
    assert path.exists()
    alarms = dead_board_alarm(store)
    assert isinstance(alarms, list)


def test_ats_job_key_shapes():
    gh = NormalizedJob(
        external_job_id="123",
        source_id="greenhouse:gitlab",
        company="GitLab",
        title="E",
        url="https://boards.greenhouse.io/gitlab/jobs/123",
        ats_type="greenhouse",
    )
    assert gh.ats_job_key == "greenhouse:123"
    wd = NormalizedJob(
        external_job_id="nvidia:NVIDIAExternalCareerSite:REQ9",
        source_id="workday:nvidia",
        company="NVIDIA",
        title="E",
        url="https://nvidia.wd5.myworkdayjobs.com/en-US/x/REQ9",
        ats_type="workday",
    )
    assert wd.ats_job_key == "workday:nvidia:NVIDIAExternalCareerSite:REQ9"


def test_boards_csv_has_three_workday_pairs():
    import csv

    path = Path(__file__).resolve().parents[1] / "config" / "boards.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    wd = [r for r in rows if (r.get("scraper_type") or "").lower() == "workday"]
    assert len(wd) >= 3
    lever = [r for r in rows if r.get("board_slug") == "palantir"]
    assert lever, "palantir lever board required (netflix 404)"


def test_list_active_sources_prioritizes_fetch_ok(tmp_path):
    store = AggregationStore(db_path=tmp_path / "prio.db")
    store.upsert_source(
        {
            "source_id": "greenhouse:zzzdead",
            "company": "Aaa Dead",
            "ats_type": "greenhouse",
            "board_identifier": "zzzdead",
            "active": True,
        }
    )
    store.upsert_source(
        {
            "source_id": "greenhouse:gitlab",
            "company": "Zzz GitLab",
            "ats_type": "greenhouse",
            "board_identifier": "gitlab",
            "active": True,
        }
    )
    store.bump_board_health(
        "greenhouse:gitlab", ats_type="greenhouse", fetch_ok=1, jobs_new=1, fetch_attempts=1
    )
    ordered = [r["source_id"] for r in store.list_active_sources()]
    assert ordered[0] == "greenhouse:gitlab"
    assert ordered[-1] == "greenhouse:zzzdead"
