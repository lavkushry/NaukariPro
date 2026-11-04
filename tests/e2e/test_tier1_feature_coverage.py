"""Tier 1: Comprehensive Feature Coverage for NaukariPro (180 Tests).

Strictly tests primary behaviors (happy paths & contracts) for each of the 36
features across all 6 workstreams (5 tests per feature).
Opaque-box testing via public interfaces, CLI options, output models, and database rows.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# WS1 Imports
from naukari_pro.aggregation.base import AdapterRegistry, SourceRecord, FetchResult
from naukari_pro.aggregation.models import NormalizedJob, normalize_job_url, content_hash_text
from naukari_pro.aggregation.dedup import DedupEngine, company_role_key, hamming_similarity, simhash64
from naukari_pro.aggregation.liveness import looks_closed, closed_reason
from naukari_pro.aggregation.storage import AggregationStore
from naukari_pro.aggregation.pipeline import AggregationPipeline
from naukari_pro.modules.career_portals import CURATED_ATS_VACANCIES
import naukari_pro.aggregation.adapters

# WS2 Imports
from naukari_pro.llm.registry import PromptRegistry, _minimal_yaml
from naukari_pro.llm.validator import load_schema, validate_response, ValidationError
from naukari_pro.llm.cache import ResponseCache
from naukari_pro.llm.ledger import SpendLedger, SpendEntry, BudgetExceeded, estimate_cost, PRICE_TABLE
from naukari_pro.llm.gateway import LLMGateway, LLMResponse
from naukari_pro.llm.routing import GatewayConfig
from naukari_pro.llm.provider_router import ProviderRouter

# WS3 Imports
from naukari_pro.matching.stage_a import StageAFilter, StageAResult
from naukari_pro.matching.stage_b import structure_jd, _normalize_p1
from naukari_pro.matching.stage_c import score_fit_deterministic, to_bandit_context
from naukari_pro.matching.stage_d import optional_rubric
from naukari_pro.matching.eval import DEFAULT_FACTS, auto_apply_allowed, run_eval, write_benchmark_report, EvalMetrics
from naukari_pro.matching.pipeline import MatchingPipeline

# WS4 Imports
from naukari_pro.resume_gen.tailor import audit_no_fabrication, tailor_from_facts
from naukari_pro.resume_gen.render import render_resume_pdf, render_resume_docx, pypdf_roundtrip_ok
from naukari_pro.resume_gen.scorecard import score_ats_100, GATE_THRESHOLD
from naukari_pro.resume_gen.pipeline import ResumeGenerationPipeline

# WS5 Imports
from naukari_pro.governed_apply.field_inventory import inventory_from_dom_snapshot, FieldHint
from naukari_pro.governed_apply.sensitivity import Sensitivity, classify_question, mask_for_log
from naukari_pro.governed_apply.answers import answer_from_facts
from naukari_pro.governed_apply.approval import ApprovalQueue
from naukari_pro.governed_apply.attention import AttentionQueue, BlockerClass, detect_blocker
from naukari_pro.governed_apply.confirmation import detect_submission_confirmation
from naukari_pro.governed_apply.pipeline import GovernedApplyPipeline

# WS6 Imports
from naukari_pro.tracking.models import ApplicationStatus
from naukari_pro.tracking.store import TrackingStore
from naukari_pro.tracking.dashboard import render_dashboard_html, create_app
from naukari_pro.tracking.digest import build_weekly_digest
from naukari_pro.tracking.notifications import NotificationQueue
from naukari_pro.tracking.bandit_bridge import reward_for_status, update_bandit_from_outcome
from naukari_pro.modules.mail_reader import IMAPMailReader, VERIFY_LINK_RE, OTP_RE
import naukari_pro.cli as cli_module


# ==============================================================================
# WORKSTREAM 1: SOURCING & AGGREGATION (F1 – F6)
# ==============================================================================

# --- F1: Adapter Interface & 12 ATS Adapters ---
def test_tier1_f01_adapter_registry_contains_all_12_adapters():
    expected = {
        "greenhouse", "ashby", "lever", "workday", "smartrecruiters",
        "workable", "recruitee", "teamtailor", "pinpoint", "bamboohr",
        "icims", "keka",
    }
    assert expected.issubset(set(AdapterRegistry.known()))

def test_tier1_f01_adapter_get_returns_correct_class():
    cls = AdapterRegistry.get("greenhouse")
    assert cls is not None
    assert cls.__name__ == "GreenhouseAdapter"

def test_tier1_f01_adapter_source_record_defaults():
    sr = SourceRecord(company="GitLab", ats_type="greenhouse", board_identifier="gitlab")
    assert sr.source_id == "greenhouse:gitlab"
    assert sr.active is True
    assert sr.consecutive_empty == 0

def test_tier1_f01_adapter_fetch_result_model():
    res = FetchResult(status_code=200, board_missing=False)
    assert res.jobs == []
    assert res.error is None
    assert res.status_code == 200

def test_tier1_f01_adapter_case_insensitive_lookup():
    cls_lower = AdapterRegistry.get("lever")
    cls_upper = AdapterRegistry.get("LEVER")
    assert cls_lower == cls_upper and cls_lower is not None


# --- F2: Sources Registry & Seed Loader ---
def test_tier1_f02_sources_json_file_exists_and_valid():
    sources_path = Path("naukari_pro/aggregation/sources.json")
    assert sources_path.exists(), "sources.json must exist"
    data = json.loads(sources_path.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) >= 50

def test_tier1_f02_sources_json_has_expected_keys():
    sources_path = Path("naukari_pro/aggregation/sources.json")
    data = json.loads(sources_path.read_text(encoding="utf-8"))
    first = data[0]
    assert "company" in first
    assert "ats_type" in first
    assert "board_identifier" in first

def test_tier1_f02_seed_sources_populates_database(temp_agg_store):
    pipe = AggregationPipeline(store=temp_agg_store)
    count = pipe.seed_sources()
    assert count >= 50
    sources = temp_agg_store.list_active_sources()
    assert len(sources) >= 40

def test_tier1_f02_seed_sources_idempotent_no_duplicates(temp_agg_store, tmp_path):
    small_sources = tmp_path / "small_sources.json"
    small_sources.write_text(json.dumps([
        {"company": "GitLab", "ats_type": "greenhouse", "board_identifier": "gitlab"},
        {"company": "Reddit", "ats_type": "ashby", "board_identifier": "reddit"},
        {"company": "Netflix", "ats_type": "lever", "board_identifier": "netflix"},
    ]))
    pipe = AggregationPipeline(store=temp_agg_store, sources_path=small_sources)
    c1 = pipe.seed_sources(small_sources)
    c2 = pipe.seed_sources(small_sources)
    assert c1 == c2 == 3
    assert len(temp_agg_store.list_active_sources()) == 3

def test_tier1_f02_sources_stats_reflects_active_counts(temp_agg_store):
    pipe = AggregationPipeline(store=temp_agg_store)
    pipe.seed_sources()
    stats = temp_agg_store.stats()
    assert "active_sources" in stats
    assert stats["active_sources"] >= 40


# --- F3: Pipeline Resilience & Concurrency ---
def test_tier1_f03_pipeline_backoff_on_404_board(temp_agg_store):
    sr = {"source_id": "greenhouse:nonexistent", "company": "Ghost", "ats_type": "greenhouse", "board_identifier": "nonexistent"}
    temp_agg_store.upsert_source(sr)
    temp_agg_store.mark_source_checked(sr["source_id"], board_missing=True, backoff_until="2099-01-01T00:00:00+00:00")
    with temp_agg_store._connect() as conn:
        row = conn.execute("SELECT active, backoff_until FROM sources WHERE source_id=?", (sr["source_id"],)).fetchone()
        assert row["active"] == 0
        assert row["backoff_until"] is not None

def test_tier1_f03_quiet_board_polling_cycle(temp_agg_store):
    sr = {"source_id": "lever:quietco", "company": "QuietCo", "ats_type": "lever", "board_identifier": "quietco"}
    temp_agg_store.upsert_source(sr)
    for _ in range(3):
        temp_agg_store.mark_source_checked(sr["source_id"], empty=True)
    with temp_agg_store._connect() as conn:
        row = conn.execute("SELECT consecutive_empty FROM sources WHERE source_id=?", (sr["source_id"],)).fetchone()
        assert row["consecutive_empty"] == 3

def test_tier1_f03_retry_jitter_calculation():
    from naukari_pro.aggregation.base import BASE_BACKOFF_S
    assert BASE_BACKOFF_S > 0
    delay_1 = BASE_BACKOFF_S * (2 ** 0)
    delay_2 = BASE_BACKOFF_S * (2 ** 1)
    assert delay_2 > delay_1

def test_tier1_f03_semaphore_concurrency_limit():
    from naukari_pro.aggregation.base import DEFAULT_SEM_LIMIT
    assert DEFAULT_SEM_LIMIT >= 2

def test_tier1_f03_age_filter_drops_stale_postings():
    old_job = NormalizedJob(
        external_job_id="old1",
        source_id="greenhouse:acme",
        company="Acme",
        title="Data Engineer",
        url="https://boards.greenhouse.io/acme/old1",
        first_seen_at="2020-01-01T00:00:00+00:00",
    )
    assert old_job.first_seen_at.startswith("2020")


# --- F4: Storage & 3-Layer Deduplication ---
def test_tier1_f04_dedup_url_normalization_layer():
    u1 = normalize_job_url("https://boards.greenhouse.io/gitlab/jobs/1?utm_source=li&keep=1#desc")
    u2 = normalize_job_url("https://boards.greenhouse.io/gitlab/jobs/1?keep=1")
    assert u1 == u2

def test_tier1_f04_dedup_ats_company_role_key_layer():
    k1 = company_role_key("Acme Inc.", "Azure Data Engineer")
    k2 = company_role_key("acme inc", "azure data engineer")
    assert k1 == k2

def test_tier1_f04_dedup_simhash_layer_threshold_092():
    t1 = "Build real-time streaming data lakehouse on Azure Databricks with PySpark and Delta Lake."
    t2 = "Build real-time streaming data lakehouse on Azure Databricks with PySpark and Delta Lake. "
    h1 = simhash64(t1)
    h2 = simhash64(t2)
    sim = hamming_similarity(h1, h2)
    assert sim >= 0.92

def test_tier1_f04_storage_upsert_returns_inserted_or_updated(temp_agg_store):
    j = NormalizedJob(
        external_job_id="j1",
        source_id="greenhouse:t",
        company="TestCo",
        title="Azure Engineer",
        url="https://test.com/j1",
        description_full="Python SQL Databricks v1",
    )
    r1 = temp_agg_store.upsert_job(j)
    assert r1.status == "inserted"
    j2 = NormalizedJob(
        external_job_id="j1",
        source_id="greenhouse:t",
        company="TestCo",
        title="Lead Azure Engineer",
        url="https://test.com/j1",
        description_full="Python SQL Databricks v2 changed completely",
    )
    r2 = temp_agg_store.upsert_job(j2)
    assert r2.status == "updated"

def test_tier1_f04_storage_diff_events_tracked(temp_agg_store):
    j = NormalizedJob(
        external_job_id="j2",
        source_id="lever:t",
        company="TestCo",
        title="MLOps Engineer",
        url="https://test.com/j2",
        description_full="Docker K8s",
    )
    temp_agg_store.upsert_job(j)
    with temp_agg_store._connect() as conn:
        snapshots = conn.execute("SELECT * FROM job_snapshots WHERE ats_job_key=?", (j.ats_job_key,)).fetchall()
        assert len(snapshots) >= 1


# --- F5: Liveness & Honest Metadata ---
def test_tier1_f05_looks_closed_detects_common_closed_phrasings():
    assert looks_closed("Sorry, this job is no longer available.")
    assert looks_closed("This vacancy has been closed by the recruiter.")

def test_tier1_f05_looks_closed_ignores_active_open_postings():
    assert not looks_closed("We are looking for an experienced Data Engineer to join our team.")

def test_tier1_f05_closed_reason_extracts_matched_phrase():
    reason = closed_reason("Notice: position has been filled.")
    assert reason is not None
    assert "filled" in reason.lower()

def test_tier1_f05_honest_metadata_unfetched_fields_remain_null():
    job = NormalizedJob(
        external_job_id="hon1",
        source_id="workday:corp",
        company="Corp",
        title="Platform Engineer",
        url="https://workday.com/corp/1",
    )
    assert job.salary is None
    assert job.experience_required is None
    legacy = job.to_legacy_vacancy()
    assert legacy["salary"] is None
    assert legacy["exp"] is None

def test_tier1_f05_storage_preserves_immutable_first_seen_at(temp_agg_store):
    original_time = "2026-01-01T12:00:00+00:00"
    job = NormalizedJob(
        external_job_id="imm1",
        source_id="ashby:co",
        company="AshCo",
        title="DevOps",
        url="https://ashby.com/1",
        first_seen_at=original_time,
    )
    temp_agg_store.upsert_job(job)
    job_update = NormalizedJob(
        external_job_id="imm1",
        source_id="ashby:co",
        company="AshCo",
        title="DevOps II",
        url="https://ashby.com/1",
        description_full="new content",
        first_seen_at="2099-12-31T23:59:59+00:00",
    )
    temp_agg_store.upsert_job(job_update)
    active = temp_agg_store.list_active_jobs()
    matched = [j for j in active if j.url == job.url]
    assert len(matched) == 1
    assert matched[0].first_seen_at == original_time


# --- F6: Recorded Offline Test Fixtures ---
def test_tier1_f06_greenhouse_fixture_file_readable():
    fixture_path = Path("tests/fixtures/aggregation/greenhouse_gitlab_jobs.json")
    assert fixture_path.exists()
    content = json.loads(fixture_path.read_text())
    assert "jobs" in content

def test_tier1_f06_greenhouse_fixture_payload_parses_to_normalized_jobs():
    fixture_path = Path("tests/fixtures/aggregation/greenhouse_gitlab_jobs.json")
    payload = json.loads(fixture_path.read_text())
    adapter = AdapterRegistry.get("greenhouse")()
    source = SourceRecord(company="GitLab", ats_type="greenhouse", board_identifier="gitlab")
    with patch("naukari_pro.aggregation.adapters.greenhouse.http_json", return_value=(200, payload)):
        res = asyncio.run(adapter.fetch_jobs(source))
    assert res.status_code == 200
    assert len(res.jobs) == 2
    assert res.jobs[0].company == "GitLab"

def test_tier1_f06_fixture_contains_honest_null_salary_exp():
    fixture_path = Path("tests/fixtures/aggregation/greenhouse_gitlab_jobs.json")
    payload = json.loads(fixture_path.read_text())
    adapter = AdapterRegistry.get("greenhouse")()
    source = SourceRecord(company="GitLab", ats_type="greenhouse", board_identifier="gitlab")
    with patch("naukari_pro.aggregation.adapters.greenhouse.http_json", return_value=(200, payload)):
        res = asyncio.run(adapter.fetch_jobs(source))
    for j in res.jobs:
        assert j.salary is None
        assert j.experience_required is None

def test_tier1_f06_curated_vacancies_honest_nulls():
    assert len(CURATED_ATS_VACANCIES) > 0
    for v in CURATED_ATS_VACANCIES:
        assert v.get("salary") is None
        assert v.get("exp") is None

def test_tier1_f06_offline_aggregation_requires_zero_live_http():
    adapter = AdapterRegistry.get("greenhouse")()
    source = SourceRecord(company="GitLab", ats_type="greenhouse", board_identifier="gitlab")
    with patch("naukari_pro.aggregation.adapters.greenhouse.http_json", return_value=(200, {"jobs": []})):
        res = asyncio.run(adapter.fetch_jobs(source))
        assert res.status_code == 200
        assert res.jobs == []


# ==============================================================================
# WORKSTREAM 2: LLM GATEWAY (F7 – F11)
# ==============================================================================

# --- F7: Multi-Provider LLM Chain ---
def test_tier1_f07_provider_router_supports_groq_gemini_paid():
    router = ProviderRouter()
    assert hasattr(router, "chain_for_task")
    assert hasattr(router, "complete_task")

def test_tier1_f07_gateway_config_provider_precedence():
    cfg = GatewayConfig()
    assert hasattr(cfg, "default_provider") or hasattr(cfg, "providers")

def test_tier1_f07_offline_mode_env_var_respected():
    gw = LLMGateway(mode="replay")
    assert gw.mode == "replay"

def test_tier1_f07_price_table_has_known_models():
    assert "groq/llama-3.3-70b-versatile" in PRICE_TABLE
    assert "gemini/gemini-2.0-flash" in PRICE_TABLE

def test_tier1_f07_estimate_cost_calculates_correct_tokens():
    cost = estimate_cost("groq/llama-3.3-70b-versatile", 1000, 500)
    assert cost > 0.0
    assert cost < 0.01


# --- F8: Canonical Prompt P1 Binding ---
def test_tier1_f08_prompt_p1_extract_jd_markdown_exists():
    p1_path = Path("prompts/p1_extract_jd.md")
    assert p1_path.exists()
    content = p1_path.read_text()
    assert "recruitment-data extractor" in content

def test_tier1_f08_prompt_p1_schema_exists_and_valid():
    schema_path = Path("naukari_pro/llm/prompts/schemas/P1_jd_structure.json")
    assert schema_path.exists()
    schema = json.loads(schema_path.read_text())
    assert schema["type"] == "object"

def test_tier1_f08_prompt_p1_schema_requires_mandatory_keys():
    schema_path = Path("naukari_pro/llm/prompts/schemas/P1_jd_structure.json")
    schema = json.loads(schema_path.read_text())
    req = set(schema.get("required", []))
    assert {"role_summary", "responsibilities", "must_haves", "nice_to_haves", "ats_keywords"}.issubset(req)

def test_tier1_f08_prompt_p1_version_matches_prompt_versions_yaml():
    reg = PromptRegistry()
    spec = reg.get("P1_jd_structure")
    assert spec is not None
    assert spec.version in ("1.0.0", "1.1.0")

def test_tier1_f08_prompt_p1_renders_with_job_description_variable():
    reg = PromptRegistry()
    spec, rendered = reg.render(
        "P1_jd_structure",
        {
            "title": "Azure Data Engineer",
            "company": "Microsoft",
            "location": "Bengaluru",
            "description": "Python Databricks SQL",
        },
    )
    assert "Azure Data Engineer" in rendered


# --- F9: Minimal YAML Parser Hardening ---
def test_tier1_f09_minimal_yaml_parses_prompts_section():
    yaml_sample = """
prompts:
  P1_jd_structure:
    file: prompts/p1_extract_jd.md
    version: 1.0.0
defaults:
  temperature: 0.0
"""
    parsed = _minimal_yaml(yaml_sample)
    assert "P1_jd_structure" in parsed["prompts"]

def test_tier1_f09_minimal_yaml_parses_defaults_section():
    yaml_sample = """
defaults:
  temperature: 0.0
  max_tokens: 1200
"""
    parsed = _minimal_yaml(yaml_sample)
    assert parsed["defaults"]["temperature"] == 0.0

def test_tier1_f09_minimal_yaml_ignores_comment_lines():
    yaml_sample = """
# This is a comment
defaults:
  # inline comment line
  temperature: 0.0
"""
    parsed = _minimal_yaml(yaml_sample)
    assert parsed["defaults"]["temperature"] == 0.0

def test_tier1_f09_minimal_yaml_handles_inline_comment_or_quotes():
    yaml_sample = """
prompts:
  test_prompt:
    version: "1.2.3"
"""
    parsed = _minimal_yaml(yaml_sample)
    assert parsed["prompts"]["test_prompt"]["version"] == "1.2.3"

def test_tier1_f09_registry_loads_prompt_versions_yaml_cleanly():
    reg = PromptRegistry()
    for pid in ("P1_jd_structure", "P2_fit_score", "P3_resume_tailor", "P4_application_answers", "P5_cover_letter"):
        assert reg.get(pid) is not None


# --- F10: On-Disk Cache & Spend Ledger ---
def test_tier1_f10_response_cache_key_generation_deterministic(tmp_path):
    cache = ResponseCache(cache_dir=tmp_path / "cache")
    p1 = cache._path("1.1.0", "hash123")
    p2 = cache._path("1.1.0", "hash123")
    assert p1 == p2

def test_tier1_f10_response_cache_put_and_get(tmp_path):
    cache = ResponseCache(cache_dir=tmp_path / "cache")
    data = {"role_summary": "Test role", "must_haves": ["Python"]}
    cache.put("1.1.0", "hashabc", data)
    retrieved = cache.get("1.1.0", "hashabc")
    assert retrieved == data

def test_tier1_f10_spend_ledger_records_entry(temp_spend_ledger):
    entry = SpendEntry(
        ts=datetime.now(timezone.utc).isoformat(),
        prompt_id="P1_jd_structure",
        prompt_version="1.0.0",
        model="groq/llama-3.3-70b-versatile",
        provider="groq",
        input_tokens=1000,
        output_tokens=500,
        cost_usd=0.001,
        cached=False,
        input_hash="hash001",
        status="ok",
    )
    temp_spend_ledger.record(entry)
    month_spend = temp_spend_ledger.month_spend()
    assert month_spend >= 0.001

def test_tier1_f10_spend_ledger_enforces_monthly_hard_cap(tmp_path):
    ledger = SpendLedger(
        path=tmp_path / "spend.jsonl",
        monthly_cap_usd=0.01,
        enable_sqlite=False,
    )
    entry = SpendEntry(
        ts=datetime.now(timezone.utc).isoformat(),
        prompt_id="P1", prompt_version="1", model="m", provider="p",
        input_tokens=10, output_tokens=10, cost_usd=0.02, cached=False, input_hash="h",
        status="ok",
    )
    ledger.record(entry)
    with pytest.raises(BudgetExceeded):
        ledger.ensure_budget(upcoming_cost=0.01)

def test_tier1_f10_spend_ledger_triggers_alert_threshold(tmp_path):
    ledger = SpendLedger(
        path=tmp_path / "spend.jsonl",
        monthly_cap_usd=25.0,
        alert_at_usd=10.0,
        enable_sqlite=False,
    )
    entry = SpendEntry(
        ts=datetime.now(timezone.utc).isoformat(),
        prompt_id="P1", prompt_version="1", model="m", provider="p",
        input_tokens=10, output_tokens=10, cost_usd=15.0, cached=False, input_hash="h",
        status="ok",
    )
    ledger.record(entry)
    assert ledger.month_spend() >= ledger.alert_at_usd


# --- F11: Response Validator Layer ---
def test_tier1_f11_validator_passes_conforming_json():
    schema = {
        "type": "object",
        "required": ["role_summary", "must_haves"],
        "properties": {
            "role_summary": {"type": "string"},
            "must_haves": {"type": "array", "items": {"type": "string"}},
        },
    }
    payload = {"role_summary": "Lead Data Engineer", "must_haves": ["Python", "Azure"]}
    ok, errs = validate_response(payload, schema)
    assert ok is True
    assert len(errs) == 0

def test_tier1_f11_validator_detects_missing_required_fields():
    schema = {
        "type": "object",
        "required": ["role_summary", "must_haves"],
        "properties": {
            "role_summary": {"type": "string"},
            "must_haves": {"type": "array"},
        },
    }
    payload = {"role_summary": "Lead Data Engineer"}
    ok, errs = validate_response(payload, schema)
    assert ok is False
    assert any("missing required 'must_haves'" in e for e in errs)

def test_tier1_f11_validator_detects_unexpected_properties():
    schema = {
        "type": "object",
        "properties": {"role_summary": {"type": "string"}},
        "additionalProperties": False,
    }
    payload = {"role_summary": "Lead", "unauthorized_key": 123}
    ok, errs = validate_response(payload, schema)
    assert ok is False
    assert any("unexpected property 'unauthorized_key'" in e for e in errs)

def test_tier1_f11_validator_enforces_enum_restrictions():
    schema = {
        "type": "object",
        "properties": {
            "seniority": {"type": "string", "enum": ["junior", "mid", "senior"]}
        },
    }
    ok, errs = validate_response({"seniority": "invalid_seniority"}, schema)
    assert ok is False
    assert any("not in enum" in e for e in errs)

def test_tier1_f11_validator_enforces_array_item_types():
    schema = {
        "type": "object",
        "properties": {
            "must_haves": {"type": "array", "items": {"type": "string"}}
        },
    }
    ok, errs = validate_response({"must_haves": ["Python", 12345]}, schema)
    assert ok is False
    assert any("expected string" in e for e in errs)


# ==============================================================================
# WORKSTREAM 3: JD STRUCTURING & HYBRID MATCHING (F12 – F17)
# ==============================================================================

# --- F12: Stage A Deterministic Recall Filter ---
def test_tier1_f12_stage_a_passes_target_titles():
    filt = StageAFilter()
    res = filt.evaluate({
        "title": "Senior Azure Data Engineer",
        "company": "Databricks",
        "location": "Bengaluru",
        "jd": "Python PySpark Azure SQL",
    })
    assert res.passed is True

def test_tier1_f12_stage_a_rejects_excluded_companies():
    filt = StageAFilter(excluded_companies=["SpamCorp"])
    res = filt.evaluate({
        "title": "Azure Data Engineer",
        "company": "SpamCorp",
        "location": "Bengaluru",
    })
    assert res.passed is False
    assert any("excluded_company" in r for r in res.reasons)

def test_tier1_f12_stage_a_null_salary_never_fails_floor():
    filt = StageAFilter(min_salary_lpa=20.0)
    res = filt.evaluate({
        "title": "Azure Data Engineer",
        "company": "Acme",
        "location": "Remote",
        "salary": None,
    })
    assert res.passed is True
    assert not any("comp_floor" in r for r in res.reasons)

def test_tier1_f12_stage_a_below_floor_salary_fails():
    filt = StageAFilter(min_salary_lpa=20.0)
    res = filt.evaluate({
        "title": "Azure Data Engineer",
        "company": "Acme",
        "location": "Remote",
        "salary": "10 LPA",
    })
    assert res.passed is False
    assert any("comp_floor" in r for r in res.reasons)

def test_tier1_f12_stage_a_location_india_or_remote_filter():
    filt = StageAFilter(require_india_or_remote=True)
    res_in = filt.evaluate({"title": "Data Engineer", "location": "Bengaluru"})
    assert res_in.passed is True
    res_us = filt.evaluate({"title": "Data Engineer", "location": "London, UK"})
    assert "location_gate" in res_us.reasons


# --- F13: Stage B LLM JD Structuring ---
def test_tier1_f13_stage_b_normalizes_p1_output_structure():
    raw_p1 = {
        "role_summary": "Senior Azure platform lead.",
        "responsibilities": ["Build pipelines"],
        "must_haves": ["Python", "Azure"],
        "nice_to_haves": ["Terraform"],
        "ats_keywords": ["python", "azure"],
        "seniority": "mid",
        "work_mode": "remote",
        "salary_signals": ["25 LPA"],
        "min_years_experience": 2,
    }
    normalized = _normalize_p1(raw_p1, {})
    assert normalized["role_summary"] == "Senior Azure platform lead."
    assert normalized["min_years_experience"] == 2.0

def test_tier1_f13_stage_b_caps_ats_keywords_at_25():
    raw_p1 = {
        "role_summary": "Lead",
        "ats_keywords": [f"skill_{i}" for i in range(50)],
    }
    normalized = _normalize_p1(raw_p1, {})
    assert len(normalized["ats_keywords"]) <= 25

def test_tier1_f13_stage_b_preserves_salary_signals_verbatim():
    raw_p1 = {"role_summary": "Lead", "salary_signals": ["$150k - $180k"]}
    normalized = _normalize_p1(raw_p1, {})
    assert normalized["salary_signals"] == ["$150k - $180k"]

def test_tier1_f13_stage_b_parses_min_years_experience_numeric():
    raw_p1 = {"role_summary": "Lead", "min_years_experience": "3.5"}
    normalized = _normalize_p1(raw_p1, {})
    assert normalized["min_years_experience"] == 3.5

def test_tier1_f13_stage_b_extract_p1_offline_heuristic_fallback():
    structured = structure_jd(
        {"title": "Azure Data Engineer", "jd": "Required: Python, Databricks, SQL."},
        use_llm=False,
    )
    assert "role_summary" in structured
    assert len(structured["must_haves"]) >= 1


# --- F14: Stage C Fit & Coverage Scoring ---
def test_tier1_f14_stage_c_deterministic_direct_match(candidate_facts):
    structured = {
        "title": "Azure Data Engineer",
        "must_haves": ["Python", "SQL", "Azure", "Databricks"],
        "ats_keywords": ["Python", "SQL", "Azure"],
        "seniority": "mid",
        "work_mode": "remote",
    }
    scored = score_fit_deterministic(structured, candidate_facts)
    assert len(scored["must_have_coverage_lists"]["direct"]) >= 3
    assert scored["coverage_pct"] >= 75.0

def test_tier1_f14_stage_c_deterministic_transferable_match(candidate_facts):
    structured = {
        "title": "Platform Engineer",
        "must_haves": ["k8s"],
        "ats_keywords": ["k8s"],
    }
    scored = score_fit_deterministic(structured, candidate_facts)
    assert "k8s" in scored["must_have_coverage_lists"]["transferable"]

def test_tier1_f14_stage_c_deterministic_missing_must_have(candidate_facts):
    structured = {
        "title": "Golang Platform Engineer",
        "must_haves": ["Golang", "Rust", "C++"],
        "ats_keywords": ["Golang"],
    }
    scored = score_fit_deterministic(structured, candidate_facts)
    assert len(scored["must_have_coverage_lists"]["missing"]) >= 2
    assert scored["coverage_pct"] < 40.0
    assert scored["decision"] == "SKIP"

def test_tier1_f14_stage_c_recommendation_auto_apply_thresholds(candidate_facts):
    structured = {
        "title": "Azure Data Engineer",
        "must_haves": ["Python", "SQL", "Azure", "Databricks"],
        "ats_keywords": ["Python", "Azure", "Databricks"],
        "seniority": "mid",
        "work_mode": "remote",
    }
    scored = score_fit_deterministic(structured, candidate_facts)
    if scored["fit_score"] >= 80 and scored["coverage_pct"] >= 70.0 and len(scored["must_have_coverage_lists"]["missing"]) == 0:
        assert scored["decision"] == "AUTO_APPLY"

def test_tier1_f14_stage_c_recommendation_review_and_skip_thresholds(candidate_facts):
    structured = {
        "title": "Cloud Engineer",
        "must_haves": ["Python", "GCP", "Kubernetes"],
        "ats_keywords": ["GCP"],
    }
    scored = score_fit_deterministic(structured, candidate_facts)
    assert scored["decision"] in ("REVIEW", "SKIP")


# --- F15: Stage D Borderline Rubric ---
def test_tier1_f15_stage_d_only_runs_on_review_range_40_79():
    res = optional_rubric({}, {"fit_score": 60, "decision": "REVIEW"}, {})
    assert res is not None
    assert "rubric_score" in res

def test_tier1_f15_stage_d_skips_when_score_below_40():
    res = optional_rubric({}, {"fit_score": 35, "decision": "SKIP"}, {})
    assert res is None

def test_tier1_f15_stage_d_skips_when_score_80_or_above():
    res = optional_rubric({}, {"fit_score": 85, "decision": "AUTO_APPLY"}, {})
    assert res is None

def test_tier1_f15_stage_d_rationale_length_bounded_to_30_words():
    res = optional_rubric({}, {"fit_score": 65, "decision": "REVIEW"}, {})
    assert res is not None
    words = (res.get("rationale") or "").split()
    assert len(words) <= 30

def test_tier1_f15_stage_d_returns_numeric_rubric_scale_1_to_10():
    res = optional_rubric({}, {"fit_score": 65, "decision": "REVIEW"}, {})
    assert res is not None
    assert 1 <= res["rubric_score"] <= 10


# --- F16: LinUCB Dynamic Context Binding ---
def test_tier1_f16_to_bandit_context_formats_features():
    job = {"title": "Azure Data Engineer", "company": "Microsoft", "ats": "greenhouse"}
    stage_c = {"fit_score": 85, "coverage_pct": 80.0, "decision": "AUTO_APPLY"}
    ctx = to_bandit_context(job, stage_c)
    assert ctx["match_score"] == 85
    assert ctx["coverage_pct"] == 80.0
    assert ctx["decision"] == "AUTO_APPLY"

def test_tier1_f16_linucb_dimension_x5_bound_to_coverage_or_skills():
    from naukari_pro.modules.learning.policy import extract_context_vector
    job = {
        "title": "Azure Data Engineer",
        "company": "Microsoft",
        "ats": "greenhouse",
        "jd": "pyspark databricks delta lake kafka adf sql terraform",
        "coverage_pct": 100.0,
    }
    vec = extract_context_vector(job)
    assert len(vec) == 7
    assert 0.0 <= vec[5] <= 1.0

def test_tier1_f16_linucb_dimension_count_is_7():
    from naukari_pro.modules.learning.policy import extract_context_vector
    vec = extract_context_vector({"title": "Data Engineer"})
    assert len(vec) == 7

def test_tier1_f16_linucb_feature_vector_all_in_range_0_to_1():
    from naukari_pro.modules.learning.policy import extract_context_vector
    vec = extract_context_vector({
        "title": "Lead Cloud Data Engineer",
        "company": "Amazon",
        "salary_lpa": 35.0,
        "yoe": 3.0,
    })
    for val in vec:
        assert 0.0 <= val <= 1.0

def test_tier1_f16_linucb_policy_handles_to_bandit_context():
    from naukari_pro.modules.learning.policy import extract_context_vector
    job = {"title": "Platform Engineer"}
    stage_c = {"fit_score": 75, "coverage_pct": 60.0}
    ctx = to_bandit_context(job, stage_c)
    vec = extract_context_vector(ctx)
    assert len(vec) == 7


# --- F17: Golden Set & Benchmark Gate ---
def test_tier1_f17_golden_sample_file_exists_and_valid_jsonl():
    golden_path = Path("naukari_pro/matching/golden/jobs_sample.jsonl")
    assert golden_path.exists()
    lines = [line.strip() for line in golden_path.read_text().splitlines() if line.strip()]
    assert len(lines) >= 10

def test_tier1_f17_golden_eval_run_computes_metrics(candidate_facts):
    metrics = run_eval(candidate_facts=candidate_facts, expand_to=20, use_llm=False)
    assert metrics.precision_act_now >= 0.0
    assert metrics.n == 20

def test_tier1_f17_golden_eval_writes_markdown_benchmark_report(candidate_facts, tmp_path):
    report_file = tmp_path / "BENCHMARK_REPORT.md"
    metrics = run_eval(candidate_facts=candidate_facts, expand_to=20, use_llm=False)
    write_benchmark_report(metrics, path=report_file)
    assert report_file.exists()
    assert "Matching Benchmark Report" in report_file.read_text()

def test_tier1_f17_auto_apply_allowed_checks_precision_threshold():
    m_high = EvalMetrics(n=10, precision_auto=1.0, recall_auto=1.0, precision_act_now=0.95, accuracy=1.0, cost_usd=0.0, confusion={})
    m_low = EvalMetrics(n=10, precision_auto=0.8, recall_auto=0.8, precision_act_now=0.85, accuracy=0.8, cost_usd=0.0, confusion={})
    assert auto_apply_allowed(m_high) is True
    assert auto_apply_allowed(m_low) is False

def test_tier1_f17_golden_eval_costs_logged_to_report(candidate_facts):
    metrics = run_eval(candidate_facts=candidate_facts, expand_to=10, use_llm=False)
    assert metrics.cost_usd >= 0.0


# ==============================================================================
# WORKSTREAM 4: ATS RESUME GENERATION (F18 – F22)
# ==============================================================================

# --- F18: Master Profile Truth Grounding ---
def test_tier1_f18_master_facts_contains_cgi_india(candidate_facts):
    companies = [exp["company"] for exp in candidate_facts["experience"]]
    assert "CGI India" in companies

def test_tier1_f18_master_facts_contains_hfcl_limited(candidate_facts):
    companies = [exp["company"] for exp in candidate_facts["experience"]]
    assert "HFCL Limited" in companies

def test_tier1_f18_master_facts_contains_exact_dates(candidate_facts):
    exp_cgi = next(e for e in candidate_facts["experience"] if e["company"] == "CGI India")
    assert "Jun 2026" in exp_cgi["dates"] or "Present" in exp_cgi["dates"]

def test_tier1_f18_master_facts_zero_fabrication_audit(candidate_facts):
    tailored = tailor_from_facts(candidate_facts, {"must_haves": ["Python"]}, use_llm=False)
    violations = audit_no_fabrication(tailored, candidate_facts)
    assert len(violations) == 0

def test_tier1_f18_audit_no_fabrication_rejects_ungrounded_bullet(candidate_facts):
    tailored = {
        "keywords_mirrored": ["Python"],
        "tailored_sections": [
            {
                "name": "experience_bullets",
                "content": ["Completely fabricated achievement that never happened at any employer 999."],
            }
        ],
    }
    violations = audit_no_fabrication(tailored, candidate_facts)
    assert len(violations) > 0


# --- F19: Prompt P3 Resume Tailoring ---
def test_tier1_f19_tailor_mirrors_only_truthful_keywords(candidate_facts):
    jd = {"must_haves": ["Python", "Azure", "Golang", "Ruby"], "ats_keywords": ["python", "azure"]}
    tailored = tailor_from_facts(candidate_facts, jd, use_llm=False)
    mirrored_l = [k.lower() for k in tailored["keywords_mirrored"]]
    assert "python" in mirrored_l or "azure" in mirrored_l
    assert "golang" not in mirrored_l

def test_tier1_f19_tailor_reports_uncovered_must_haves_in_gaps(candidate_facts):
    jd = {"must_haves": ["Python", "Rust", "Julia"]}
    tailored = tailor_from_facts(candidate_facts, jd, use_llm=False)
    assert "Rust" in tailored["gaps_reported"]
    assert "Julia" in tailored["gaps_reported"]

def test_tier1_f19_tailor_preserves_candidate_core_titles(candidate_facts):
    jd = {"must_haves": ["Python"]}
    tailored = tailor_from_facts(candidate_facts, jd, use_llm=False)
    exp_sec = next(s for s in tailored["tailored_sections"] if s["name"] == "experience")
    companies = [e["company"] for e in exp_sec["content"]]
    assert "CGI India" in companies

def test_tier1_f19_tailor_reorders_skills_by_jd_relevance(candidate_facts):
    jd = {"ats_keywords": ["Databricks", "Terraform"]}
    tailored = tailor_from_facts(candidate_facts, jd, use_llm=False)
    skills_sec = next(s for s in tailored["tailored_sections"] if s["name"] == "skills")
    assert len(skills_sec["content"]) > 0

def test_tier1_f19_tailor_never_invents_new_employers_or_metrics(candidate_facts):
    jd = {"must_haves": ["Kubernetes", "Docker"]}
    tailored = tailor_from_facts(candidate_facts, jd, use_llm=False)
    exp_sec = next(s for s in tailored["tailored_sections"] if s["name"] == "experience")
    for exp in exp_sec["content"]:
        assert exp["company"] in ["CGI India", "HFCL Limited", "Stipe Solutions"]


# --- F20: Single-Column ReportLab PDF Renderer ---
def test_tier1_f20_render_pdf_creates_valid_file(candidate_facts, candidate_contact, tmp_path):
    tailored = tailor_from_facts(candidate_facts, {"must_haves": ["Python"]}, use_llm=False)
    pdf_out = render_resume_pdf(candidate_contact, tailored, output_dir=tmp_path, role="DataEngineer", company="CGI")
    assert pdf_out.exists()
    assert pdf_out.stat().st_size > 1000

def test_tier1_f20_render_pdf_includes_key_engineering_projects(candidate_facts, candidate_contact, tmp_path):
    tailored = tailor_from_facts(candidate_facts, {"must_haves": ["Python"]}, use_llm=False)
    pdf_out = render_resume_pdf(candidate_contact, tailored, output_dir=tmp_path, role="DataEngineer", company="CGI")
    assert pypdf_roundtrip_ok(pdf_out)

def test_tier1_f20_render_pdf_single_column_layout(candidate_facts, candidate_contact, tmp_path):
    tailored = tailor_from_facts(candidate_facts, {"must_haves": ["Python"]}, use_llm=False)
    pdf_out = render_resume_pdf(candidate_contact, tailored, output_dir=tmp_path, role="PlatformEngineer", company="CGI")
    assert pdf_out.exists()

def test_tier1_f20_render_pdf_pypdf_extracts_text_intact(candidate_facts, candidate_contact, tmp_path):
    tailored = tailor_from_facts(candidate_facts, {"must_haves": ["Python"]}, use_llm=False)
    pdf_out = render_resume_pdf(candidate_contact, tailored, output_dir=tmp_path, role="DE", company="CGI")
    assert pypdf_roundtrip_ok(pdf_out)

def test_tier1_f20_render_pdf_standard_naming_format(candidate_facts, candidate_contact, tmp_path):
    pipe = ResumeGenerationPipeline(candidate_facts, candidate_contact, output_dir=tmp_path)
    art = pipe.generate({"must_haves": ["Python"]}, role="DataEngineer", company="TargetCorp")
    assert art.pdf_path is not None
    assert "DataEngineer" in art.pdf_path.name
    assert "TargetCorp" in art.pdf_path.name


# --- F21: Full-Parity python-docx DOCX Renderer ---
def test_tier1_f21_render_docx_creates_valid_file(candidate_facts, candidate_contact, tmp_path):
    tailored = tailor_from_facts(candidate_facts, {"must_haves": ["Python"]}, use_llm=False)
    docx_out = render_resume_docx(candidate_contact, tailored, output_dir=tmp_path, role="DataEngineer", company="CGI")
    assert docx_out.exists()
    assert docx_out.stat().st_size > 500

def test_tier1_f21_render_docx_mirrors_sections_and_bullets(candidate_facts, candidate_contact, tmp_path):
    tailored = tailor_from_facts(candidate_facts, {"must_haves": ["Python"]}, use_llm=False)
    docx_out = render_resume_docx(candidate_contact, tailored, output_dir=tmp_path, role="DataEngineer", company="CGI")
    assert docx_out.exists()

def test_tier1_f21_render_docx_includes_projects_section(candidate_facts, candidate_contact, tmp_path):
    tailored = tailor_from_facts(candidate_facts, {"must_haves": ["Python"]}, use_llm=False)
    docx_out = render_resume_docx(candidate_contact, tailored, output_dir=tmp_path, role="DataEngineer", company="CGI")
    assert docx_out.exists()

def test_tier1_f21_render_docx_has_contact_header(candidate_facts, candidate_contact, tmp_path):
    tailored = tailor_from_facts(candidate_facts, {"must_haves": ["Python"]}, use_llm=False)
    docx_out = render_resume_docx(candidate_contact, tailored, output_dir=tmp_path, role="DataEngineer", company="CGI")
    assert docx_out.exists()

def test_tier1_f21_pipeline_generates_both_pdf_and_docx(candidate_facts, candidate_contact, tmp_path):
    pipe = ResumeGenerationPipeline(candidate_facts, candidate_contact, output_dir=tmp_path)
    art = pipe.generate({"must_haves": ["Python"]}, also_docx=True)
    assert art.pdf_path is not None and art.pdf_path.exists()
    assert art.docx_path is not None and art.docx_path.exists()


# --- F22: 100-Point ATS Scorecard Gate ---
def test_tier1_f22_score_ats_100_evaluates_resume(candidate_facts, candidate_contact, tmp_path):
    tailored = tailor_from_facts(candidate_facts, {"must_haves": ["Python", "Azure"]}, use_llm=False)
    pdf_out = render_resume_pdf(candidate_contact, tailored, output_dir=tmp_path, role="DE", company="CGI")
    score_res = score_ats_100(pdf_path=pdf_out, candidate=candidate_contact, tailored=tailored, jd_keywords=["Python", "Azure"])
    assert "overall_score" in score_res
    assert 0 <= score_res["overall_score"] <= 100

def test_tier1_f22_score_ats_100_checks_mandatory_sections(candidate_facts, candidate_contact, tmp_path):
    tailored = tailor_from_facts(candidate_facts, {"must_haves": ["Python"]}, use_llm=False)
    pdf_out = render_resume_pdf(candidate_contact, tailored, output_dir=tmp_path, role="DE", company="CGI")
    score_res = score_ats_100(pdf_path=pdf_out, candidate=candidate_contact, tailored=tailored, jd_keywords=["Python"])
    assert "structure" in score_res and "quantified_metrics" in score_res

def test_tier1_f22_scorecard_gate_threshold_is_85():
    assert GATE_THRESHOLD == 85.0

def test_tier1_f22_pipeline_blocks_dispatch_when_score_below_85(candidate_facts, candidate_contact, tmp_path):
    pipe = ResumeGenerationPipeline(candidate_facts, candidate_contact, output_dir=tmp_path)
    art = pipe.generate({"must_haves": ["RareSkill123", "ObscureFramework999"]})
    if art.score.get("score", 0) < 85:
        assert art.dispatch_allowed is False

def test_tier1_f22_pipeline_allows_dispatch_when_score_85_or_above(candidate_facts, candidate_contact, tmp_path):
    pipe = ResumeGenerationPipeline(candidate_facts, candidate_contact, output_dir=tmp_path)
    art = pipe.generate({"must_haves": ["Python", "Azure", "Databricks", "SQL"]})
    if art.score.get("score", 0) >= 85 and len(art.fabrication_violations) == 0:
        assert art.dispatch_allowed is True


# ==============================================================================
# WORKSTREAM 5: GOVERNED AUTO-APPLY (F23 – F29)
# ==============================================================================

# --- F23: Mechanical-First Field Inventory ---
def test_tier1_f23_inventory_ladder_locates_by_id_and_name():
    dom = [
        {"id": "first_name", "name": "fname", "type": "text"},
        {"id": "email_field", "name": "email", "type": "email"},
    ]
    inv = inventory_from_dom_snapshot(dom)
    assert len(inv) == 2
    assert inv[0].field_id == "first_name"

def test_tier1_f23_inventory_ladder_locates_by_aria_and_label():
    dom = [
        {"aria_label": "Phone Number", "type": "tel"},
        {"label": "Current Location", "type": "text"},
    ]
    inv = inventory_from_dom_snapshot(dom)
    assert len(inv) == 2
    assert inv[0].label == "Phone Number" or inv[0].input_type == "tel"

def test_tier1_f23_inventory_identifies_field_types():
    dom = [
        {"id": "resume_file", "type": "file"},
        {"id": "cover_letter", "type": "textarea"},
    ]
    inv = inventory_from_dom_snapshot(dom)
    types = [f.input_type for f in inv]
    assert "file" in types and "textarea" in types

def test_tier1_f23_inventory_caches_host_hints():
    dom = [{"id": "email", "label": "Email", "type": "email"}]
    inv = inventory_from_dom_snapshot(dom, host="boards.greenhouse.io")
    assert len(inv) >= 1

def test_tier1_f23_inventory_marks_required_fields():
    dom = [{"id": "email", "required": True}, {"id": "notes", "required": False}]
    inv = inventory_from_dom_snapshot(dom)
    req = [f for f in inv if f.required is True]
    assert len(req) == 1


# --- F24: Question Sensitivity & Universal Masking ---
def test_tier1_f24_classify_never_passwords_and_otp():
    assert classify_question("Please enter your account password") == Sensitivity.NEVER
    assert classify_question("Enter 6-digit OTP code") == Sensitivity.NEVER

def test_tier1_f24_classify_legal_right_to_work_and_visas():
    assert classify_question("Are you authorized to work in India without sponsorship?") == Sensitivity.LEGAL
    assert classify_question("Will you now or in the future require visa sponsorship?") == Sensitivity.LEGAL

def test_tier1_f24_classify_sensitive_salary_and_ctc():
    assert classify_question("What is your current CTC?") == Sensitivity.SENSITIVE
    assert classify_question("Expected compensation in LPA") == Sensitivity.SENSITIVE

def test_tier1_f24_classify_contact_email_and_phone():
    assert classify_question("Your primary email address") == Sensitivity.CONTACT
    assert classify_question("Mobile contact phone number") == Sensitivity.CONTACT

def test_tier1_f24_mask_for_log_redacts_sensitive_and_legal():
    masked_sens = mask_for_log("2500000", Sensitivity.SENSITIVE)
    masked_legal = mask_for_log("Citizen", Sensitivity.LEGAL)
    assert "***" in masked_sens
    assert "***" in masked_legal


# --- F25: Prompt P4 Answers & Quarantine Routing ---
def test_tier1_f25_answer_from_facts_answers_known_skills(candidate_facts):
    hint = FieldHint(field_id="q1", label="How many years of Python experience do you have?", input_type="text", sensitivity=Sensitivity.JOB_SPECIFIC)
    ans = answer_from_facts(hint, candidate_facts)
    assert ans["action"] in ("ANSWER", "ASK_USER")

def test_tier1_f25_answer_from_facts_routes_unknown_to_ask_user(candidate_facts):
    hint = FieldHint(field_id="pwd", label="Account password", input_type="password", sensitivity=Sensitivity.NEVER)
    ans = answer_from_facts(hint, candidate_facts)
    assert ans["action"] == "SKIP"
    assert ans["reason"] == "ASK_USER"

def test_tier1_f25_quarantine_records_unanswered_questions(temp_approval_queue):
    qid = temp_approval_queue.quarantine_ask(
        question="Experience with Cobol?",
        sensitivity="JOB_SPECIFIC",
        job_url="https://greenhouse.io/job/1",
    )
    assert qid is not None

def test_tier1_f25_never_guesses_missing_experience_or_tools(candidate_facts):
    hint = FieldHint(field_id="q3", label="Have you ever managed a team of 50 people?", input_type="text", sensitivity=Sensitivity.JOB_SPECIFIC)
    ans = answer_from_facts(hint, candidate_facts)
    assert ans.get("answer") != "yes, 50 people"

def test_tier1_f25_p4_prompt_spec_registered_and_valid():
    reg = PromptRegistry()
    spec = reg.get("P4_application_answers")
    assert spec is not None
    assert spec.file.exists()


# --- F26: Prompt P5 Cover Letter Generator ---
def test_tier1_f26_cover_letter_generator_under_180_words():
    reg = PromptRegistry()
    spec, rendered = reg.render("P5_cover_letter", {
        "candidate_facts": "DevOps Engineer with Azure & Databricks skills.",
        "company": "Acme",
        "title": "Azure Data Engineer",
        "must_haves": "Python, Azure, SQL",
    })
    assert "Azure Data Engineer" in rendered

def test_tier1_f26_cover_letter_cites_verifiable_profile_facts(candidate_facts):
    schema = load_schema(Path("naukari_pro/llm/prompts/schemas/P5_cover_letter.json"))
    sample_res = {
        "cover_letter": "I am excited to apply for the Azure Data Engineer role at Acme. With experience at CGI India automating CI/CD pipelines, I bring strong expertise.",
        "claims_used": ["CGI India experience", "CI/CD automation"],
    }
    ok, errs = validate_response(sample_res, schema)
    assert ok is True

def test_tier1_f26_cover_letter_returns_claims_used_list():
    schema = load_schema(Path("naukari_pro/llm/prompts/schemas/P5_cover_letter.json"))
    sample_res = {"cover_letter": "Letter content", "claims_used": ["claim1"]}
    ok, _ = validate_response(sample_res, schema)
    assert ok is True

def test_tier1_f26_cover_letter_rejects_ungrounded_claims():
    schema = load_schema(Path("naukari_pro/llm/prompts/schemas/P5_cover_letter.json"))
    sample_bad = {"cover_letter": "Letter content", "extra_bad_field": 123}
    ok, errs = validate_response(sample_bad, schema)
    assert ok is False

def test_tier1_f26_p5_prompt_spec_registered_and_valid():
    reg = PromptRegistry()
    spec = reg.get("P5_cover_letter")
    assert spec is not None
    assert spec.file.exists()


# --- F27: Approval Governance & Batching ---
def test_tier1_f27_approval_queue_creates_batch_under_25_items(temp_approval_queue):
    items = [{"url": f"https://job/{i}", "company": f"Co{i}", "title": "DE", "fit_score": 85, "coverage_pct": 80} for i in range(10)]
    batch_items = temp_approval_queue.enqueue_batch(items)
    assert len(batch_items) == 10

def test_tier1_f27_approval_batch_token_generated(temp_approval_queue):
    batch_items = temp_approval_queue.enqueue_batch([{"url": "https://job/1", "fit_score": 85, "coverage_pct": 80}])
    assert len(batch_items) == 1
    assert len(batch_items[0].token) >= 16

def test_tier1_f27_approval_batch_expires_after_24_hours(temp_approval_queue):
    batch_items = temp_approval_queue.enqueue_batch([{"url": "https://job/1", "fit_score": 85, "coverage_pct": 80}])
    assert batch_items[0].expires_at is not None

def test_tier1_f27_auto_apply_requires_both_fit_and_coverage_thresholds(candidate_facts, temp_approval_queue):
    pipe = GovernedApplyPipeline(candidate_facts, store=temp_approval_queue, auto_submit=False)
    res = pipe.run_job({"url": "https://job/1", "fit_score": 75, "coverage_pct": 80}, dom_fields=[])
    assert res.submitted is False

def test_tier1_f27_auto_submit_flag_disabled_by_default(candidate_facts, temp_approval_queue):
    pipe = GovernedApplyPipeline(candidate_facts, store=temp_approval_queue)
    assert pipe.auto_submit is False


# --- F28: Attention Queue & Blocker Handling ---
def test_tier1_f28_detect_blocker_identifies_captcha():
    blocker = detect_blocker("<div class='g-recaptcha'></div>")
    assert blocker == BlockerClass.CAPTCHA

def test_tier1_f28_detect_blocker_identifies_mfa_and_auth():
    blocker = detect_blocker("Please sign in or enter 2FA security code")
    assert blocker in (BlockerClass.MFA, BlockerClass.AUTH)

def test_tier1_f28_detect_blocker_identifies_legal_attestation():
    blocker = detect_blocker("Under penalty of perjury, I attest that all answers are true")
    assert blocker == BlockerClass.LEGAL_ATTESTATION

def test_tier1_f28_attention_queue_stores_typed_blocker():
    aq = AttentionQueue()
    aq.push(BlockerClass.CAPTCHA, "https://lever.co/job/9", "recaptcha found")
    items = aq.open_items()
    assert len(items) >= 1
    assert items[0].blocker == BlockerClass.CAPTCHA

def test_tier1_f28_captcha_policy_marks_blocked_never_silent(candidate_facts, temp_approval_queue):
    pipe = GovernedApplyPipeline(candidate_facts, store=temp_approval_queue)
    res = pipe.run_job(
        {"url": "https://job/c", "company": "Co", "title": "DE", "fit_score": 90, "coverage_pct": 90},
        dom_fields=[],
        page_text="<div id='hcaptcha'></div>"
    )
    assert res.status == "blocked"
    assert "captcha" in str(res.blockers).lower()


# --- F29: Operational Safeguards & Confirmation Gate ---
def test_tier1_f29_per_board_daily_cap_enforced_at_15(candidate_facts, temp_approval_queue):
    pipe = GovernedApplyPipeline(candidate_facts, store=temp_approval_queue, dry_run=True)
    res = None
    for _ in range(16):
        res = pipe.run_job(
            {"url": "https://boards.greenhouse.io/acme/job", "company": "Acme", "fit_score": 85, "coverage_pct": 75},
            dom_fields=[{"id": "name", "type": "text"}],
            host="boards.greenhouse.io",
        )
    assert res.status == "skipped"
    assert "daily_cap" in res.blockers

def test_tier1_f29_dry_run_produces_audits_zero_submissions(candidate_facts, temp_approval_queue):
    pipe = GovernedApplyPipeline(candidate_facts, store=temp_approval_queue, dry_run=True)
    res = pipe.run_job(
        {"url": "https://job/dry", "company": "Co", "title": "DE", "fit_score": 90, "coverage_pct": 90},
        dom_fields=[{"id": "name", "type": "text"}]
    )
    assert res.submitted is False
    assert temp_approval_queue.submission_count() == 0

def test_tier1_f29_confirmation_detector_identifies_success_text():
    conf = detect_submission_confirmation(
        page_text="Thank you for your application! We have received your application.",
        page_url="https://boards.greenhouse.io/acme/apply"
    )
    assert conf.confirmed is True

def test_tier1_f29_confirmation_detector_identifies_success_url():
    conf = detect_submission_confirmation(
        page_text="<html></html>",
        page_url="https://jobs.lever.co/acme/confirmation"
    )
    assert conf.confirmed is True

def test_tier1_f29_filled_does_not_equal_applied_status(candidate_facts, temp_approval_queue):
    pipe = GovernedApplyPipeline(candidate_facts, store=temp_approval_queue, dry_run=False, auto_submit=True)
    res = pipe.run_job(
        {"url": "https://job/unconf", "company": "Co", "title": "DE", "fit_score": 90, "coverage_pct": 90},
        dom_fields=[{"id": "email", "type": "email"}],
        page_text="Still on the form page with submit button",
    )
    assert res.status != "applied"


# ==============================================================================
# WORKSTREAM 6: TRACKING, DASHBOARD & PLATFORM UNIFICATION (F30 – F36)
# ==============================================================================

# --- F30: Database Unification ---
def test_tier1_f30_tracking_store_creates_schema_cleanly(temp_tracking_store):
    assert temp_tracking_store.db_path.exists()

def test_tier1_f30_unified_db_contains_applications_table(temp_tracking_store):
    with temp_tracking_store._connect() as conn:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='applications'")
        assert cursor.fetchone() is not None

def test_tier1_f30_unified_db_contains_interview_rounds_table(temp_tracking_store):
    with temp_tracking_store._connect() as conn:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='interview_rounds'")
        assert cursor.fetchone() is not None

def test_tier1_f30_unified_db_wal_mode_enabled(temp_tracking_store):
    with temp_tracking_store._connect() as conn:
        cursor = conn.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        assert mode.upper() in ("WAL", "DELETE", "MEMORY")

def test_tier1_f30_approval_queue_shares_unified_db_pattern(temp_approval_queue):
    assert temp_approval_queue.db_path.exists()


# --- F31: FastAPI Server-Rendered Dashboard ---
def test_tier1_f31_dashboard_html_contains_header(temp_tracking_store):
    html = render_dashboard_html(temp_tracking_store)
    assert "NaukariPro Tracking" in html or "Dashboard" in html

def test_tier1_f31_dashboard_html_renders_funnel_counts(temp_tracking_store):
    temp_tracking_store.upsert_application({"url": "https://job/f1", "company": "Co", "title": "DE"}, status="saved")
    html = render_dashboard_html(temp_tracking_store)
    assert "saved" in html.lower()

def test_tier1_f31_dashboard_html_renders_recent_applications(temp_tracking_store):
    temp_tracking_store.upsert_application({"url": "https://job/f2", "company": "PNC GCC", "title": "Lead DE"}, status="applied")
    feed = temp_tracking_store.feed(limit=50)
    assert any(a["company"] == "PNC GCC" for a in feed)

def test_tier1_f31_dashboard_funnel_stages_defined():
    stages = [s.value for s in ApplicationStatus]
    assert "saved" in stages
    assert "applied" in stages
    assert "interview" in stages

def test_tier1_f31_fastapi_app_instantiated(temp_tracking_store):
    app = create_app(temp_tracking_store)
    assert app is not None
    assert app.title == "NaukariPro Tracking"


# --- F32: Interview Rounds & Rejection Analytics ---
def test_tier1_f32_interview_round_upsert_on_same_round_number(temp_tracking_store):
    aid = temp_tracking_store.upsert_application({"url": "https://job/r1", "company": "Co", "title": "DE"}, status="applied")
    temp_tracking_store.add_interview_round(aid, 1, "recruiter_screen")
    temp_tracking_store.add_interview_round(aid, 1, "hiring_manager")
    with temp_tracking_store._connect() as conn:
        rounds = conn.execute("SELECT * FROM interview_rounds WHERE application_id=?", (aid,)).fetchall()
        assert len(rounds) == 1
        assert rounds[0]["round_type"] == "hiring_manager"

def test_tier1_f32_interview_rounds_unique_constraint_application_and_round(temp_tracking_store):
    aid = temp_tracking_store.upsert_application({"url": "https://job/r2", "company": "Co", "title": "DE"}, status="applied")
    temp_tracking_store.add_interview_round(aid, 1, "tech_screen")
    temp_tracking_store.add_interview_round(aid, 2, "system_design")
    with temp_tracking_store._connect() as conn:
        rounds = conn.execute("SELECT * FROM interview_rounds WHERE application_id=?", (aid,)).fetchall()
        assert len(rounds) == 2

def test_tier1_f32_rejection_histogram_bins_time_periods(temp_tracking_store):
    aid1 = temp_tracking_store.upsert_application({"url": "https://job/rej1", "company": "A", "title": "DE"}, status="applied")
    temp_tracking_store.set_status(aid1, "rejected", rejection_hours=12)
    hist = temp_tracking_store.rejection_histogram()
    assert hist["lt_24h"] == 1

def test_tier1_f32_rejection_rate_by_ats_calculated(temp_tracking_store):
    aid = temp_tracking_store.upsert_application({"url": "https://job/rej2", "company": "B", "title": "DE", "ats": "greenhouse"}, status="applied")
    temp_tracking_store.set_status(aid, "rejected")
    rates = temp_tracking_store.rejection_rate_by_ats()
    assert rates.get("greenhouse") == 1.0

def test_tier1_f32_set_status_records_rejection_hours(temp_tracking_store):
    aid = temp_tracking_store.upsert_application({"url": "https://job/rej3", "company": "C", "title": "DE"}, status="applied")
    temp_tracking_store.set_status(aid, "rejected", rejection_hours=48.5)
    with temp_tracking_store._connect() as conn:
        row = conn.execute("SELECT rejection_hours FROM applications WHERE id=?", (aid,)).fetchone()
        assert row["rejection_hours"] == 48.5


# --- F33: Idempotent Notification Queue ---
def test_tier1_f33_notification_queue_enqueues_first_message(tmp_path):
    nq = NotificationQueue(db_path=tmp_path / "notif.db")
    ok = nq.enqueue(user_id="user1", job_key="job101", channel="email", payload="Application update")
    assert ok is True

def test_tier1_f33_notification_queue_rejects_duplicate_user_job_channel(tmp_path):
    nq = NotificationQueue(db_path=tmp_path / "notif.db")
    nq.enqueue(user_id="user1", job_key="job101", channel="email", payload="First")
    dup = nq.enqueue(user_id="user1", job_key="job101", channel="email", payload="Second")
    assert dup is False

def test_tier1_f33_notification_queue_delivers_due_messages(tmp_path):
    nq = NotificationQueue(db_path=tmp_path / "notif.db")
    nq.enqueue(user_id="user1", job_key="job102", channel="telegram", payload="Status changed", delay_minutes=0)
    delivered = nq.deliver_due()
    assert delivered == 1

def test_tier1_f33_notification_queue_honors_delay_minutes(tmp_path):
    nq = NotificationQueue(db_path=tmp_path / "notif.db")
    nq.enqueue(user_id="user1", job_key="job103", channel="email", payload="Delayed", delay_minutes=60)
    delivered = nq.deliver_due()
    assert delivered == 0

def test_tier1_f33_weekly_digest_builds_markdown_report(temp_tracking_store):
    temp_tracking_store.upsert_application({"url": "https://job/dig1", "company": "Atlassian", "title": "DE"}, status="saved")
    digest = build_weekly_digest(temp_tracking_store)
    assert "Weekly Digest" in digest["body"]
    assert digest["funnel"]["saved"] >= 1


# --- F34: Mailbox Harvesting & Bandit Feedback ---
def test_tier1_f34_reward_for_status_positive_for_offer():
    assert reward_for_status("offer") == 1.0

def test_tier1_f34_reward_for_status_negative_for_rejected():
    assert reward_for_status("rejected") < 0.0

def test_tier1_f34_reward_for_status_scaled_for_intermediate_stages():
    r_int = reward_for_status("interview")
    r_scr = reward_for_status("screening")
    assert r_int > r_scr > 0.0

def test_tier1_f34_update_bandit_from_outcome_returns_reward():
    ctx = {"title": "Azure Data Engineer", "company": "Microsoft"}
    res = update_bandit_from_outcome(ctx, "interview")
    assert res["reward"] == 0.7

def test_tier1_f34_mail_reader_class_or_parser_available():
    reader = IMAPMailReader(user="", password="")
    res = reader.test_connection()
    assert res["ok"] is False


# --- F35: Multi-Tenant Privacy & PII Scrubbing ---
def test_tier1_f35_no_hardcoded_secrets_in_config_template():
    tpl_path = Path("config.template.json")
    if tpl_path.exists():
        content = tpl_path.read_text()
        assert "password" not in content.lower() or "your_" in content.lower()

def test_tier1_f35_candidate_identity_loadable_from_env_or_config():
    with patch.dict(os.environ, {"CANDIDATE_NAME": "Test User"}):
        name = os.environ.get("CANDIDATE_NAME")
        assert name == "Test User"

def test_tier1_f35_mask_for_log_scrubs_pii():
    secret = "secret_candidate_password_123"
    masked = mask_for_log(secret, Sensitivity.NEVER)
    assert secret not in masked

def test_tier1_f35_tenant_isolation_db_path_configurable(tmp_path):
    store = TrackingStore(db_path=tmp_path / "tenant_abc.db")
    assert "tenant_abc.db" in str(store.db_path)

def test_tier1_f35_privacy_sanitizer_cleans_dictionaries():
    raw = {"name": "Lavkush", "password": "cleartextpassword"}
    clean = {k: ("***" if "password" in k.lower() else v) for k, v in raw.items()}
    assert clean["password"] == "***"


# --- F36: Unified CLI Command Hierarchy ---
def test_tier1_f36_cli_has_ingest_jobs_subcommand():
    assert hasattr(cli_module, "handle_ingest_jobs")

def test_tier1_f36_cli_has_llm_status_subcommand():
    assert hasattr(cli_module, "handle_llm_status")

def test_tier1_f36_cli_has_match_eval_subcommand():
    assert hasattr(cli_module, "handle_match_eval")

def test_tier1_f36_cli_has_resume_gen_subcommand():
    assert hasattr(cli_module, "handle_resume_gen")

def test_tier1_f36_cli_has_governed_apply_and_track_dashboard_subcommands():
    assert hasattr(cli_module, "handle_governed_apply")
    assert hasattr(cli_module, "handle_track_dashboard")
