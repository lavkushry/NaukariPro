"""WS2: prompt registry, schema validation, spend ledger, record/replay (zero live calls)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from naukari_pro.llm.cache import ResponseCache
from naukari_pro.llm.gateway import LLMGateway
from naukari_pro.llm.ledger import BudgetExceeded, SpendLedger, estimate_cost
from naukari_pro.llm.registry import PromptRegistry
from naukari_pro.llm.validator import ValidationError, validate_response, load_schema


def test_all_runtime_prompts_registered():
    reg = PromptRegistry()
    for pid in (
        "P1_jd_structure",
        "P2_fit_score",
        "P3_resume_tailor",
        "P4_application_answers",
        "P5_cover_letter",
    ):
        spec = reg.get(pid)
        assert spec.file.exists()
        assert spec.schema_path and spec.schema_path.exists()
        assert spec.version


def test_render_and_input_hash_stable():
    reg = PromptRegistry()
    spec, rendered = reg.render(
        "P1_jd_structure",
        {
            "title": "Data Engineer",
            "company": "Acme",
            "location": "Remote",
            "description": "Python SQL Azure",
        },
    )
    assert "Data Engineer" in rendered
    assert "{{title}}" not in rendered
    h1 = reg.input_hash(spec.prompt_version_key, rendered, spec.schema_path.name)
    h2 = reg.input_hash(spec.prompt_version_key, rendered, spec.schema_path.name)
    assert h1 == h2


def test_schema_validator_rejects_extra_and_missing():
    schema = load_schema(
        Path(__file__).resolve().parents[1]
        / "naukari_pro/llm/prompts/schemas/P2_fit_score.json"
    )
    ok, errs = validate_response({"fit_score": 50}, schema)
    assert not ok
    assert any("missing" in e for e in errs)

    good = {
        "fit_score": 55,
        "must_have_coverage": 0.5,
        "coverage_detail": [
            {"must_have": "Python", "evidence": "direct", "profile_fact": "Python dev"},
            {"must_have": "K8s", "evidence": "missing", "profile_fact": None},
        ],
        "role_family_match": 0.8,
        "location_workmode_fit": 1.0,
        "seniority_fit": 0.9,
        "compensation_vs_floor": 1.0,
        "recommendation": "REVIEW",
        "flags": ["missing_k8s"],
        "rationale": "Partial coverage of must-haves.",
    }
    ok2, errs2 = validate_response(good, schema)
    assert ok2 and not errs2


def test_spend_ledger_cap(tmp_path):
    ledger = SpendLedger(path=tmp_path / "ledger.jsonl", monthly_cap_usd=0.001, alert_at_usd=0.0005)
    from naukari_pro.llm.ledger import SpendEntry
    from datetime import datetime, timezone

    ledger.record(
        SpendEntry(
            ts=datetime.now(timezone.utc).isoformat(),
            prompt_id="P1",
            prompt_version="1.0.0",
            model="x",
            provider="y",
            input_tokens=1000,
            output_tokens=1000,
            cost_usd=0.002,
            cached=False,
            input_hash="abc",
            status="ok",
        )
    )
    with pytest.raises(BudgetExceeded):
        ledger.ensure_budget(0.001)


def test_gateway_replay_zero_live_calls(tmp_path):
    reg = PromptRegistry()
    spec, rendered = reg.render(
        "P1_jd_structure",
        {
            "title": "Data Engineer",
            "company": "Acme",
            "location": "Remote",
            "description": "Build Azure Databricks pipelines with PySpark and Delta Lake.",
        },
    )
    schema_name = spec.schema_path.name
    input_hash = reg.input_hash(spec.prompt_version_key, rendered, schema_name)

    fixture = {
        "data": {
            "role_summary": "Build lakehouse pipelines on Azure Databricks.",
            "responsibilities": ["Build pipelines"],
            "must_haves": ["Python", "Databricks", "Delta Lake"],
            "nice_to_haves": ["Kafka"],
            "ats_keywords": ["python", "databricks", "delta", "pyspark", "azure"],
            "seniority": "mid",
            "work_mode": "remote",
            "salary_signals": [],
            "min_years_experience": None,
        },
        "model": "llama-3.3-70b-versatile",
        "provider": "groq",
        "input_tokens": 120,
        "output_tokens": 80,
        "cost_usd": 0.0001,
        "prompt_id": "P1_jd_structure",
        "prompt_version": "1.1.0",
        "input_hash": input_hash,
    }
    cache = ResponseCache(cache_dir=tmp_path / "cache")
    cache.put(spec.prompt_version_key, input_hash, fixture)
    ledger = SpendLedger(path=tmp_path / "ledger.jsonl", monthly_cap_usd=25.0)

    class BoomClient:
        def complete(self, *a, **k):
            raise AssertionError("live LLM call not allowed in replay test")

    gw = LLMGateway(
        registry=reg,
        client=BoomClient(),  # type: ignore[arg-type]
        ledger=ledger,
        cache=cache,
        mode="replay",
    )
    resp = gw.call(
        "P1_jd_structure",
        {
            "title": "Data Engineer",
            "company": "Acme",
            "location": "Remote",
            "description": "Build Azure Databricks pipelines with PySpark and Delta Lake.",
        },
    )
    assert resp.cached is True
    assert resp.validated is True
    assert resp.data["salary_signals"] == []
    assert resp.data["seniority"] == "mid"
    assert resp.data["min_years_experience"] is None
    assert ledger.month_spend() == 0.0  # replay does not bill


def test_gateway_replay_miss_raises(tmp_path):
    gw = LLMGateway(
        cache=ResponseCache(cache_dir=tmp_path / "empty"),
        ledger=SpendLedger(path=tmp_path / "l.jsonl"),
        mode="replay",
    )
    with pytest.raises(FileNotFoundError):
        gw.call(
            "P1_jd_structure",
            {"title": "x", "company": "y", "location": "z", "description": "d"},
        )


def test_estimate_cost_positive():
    assert estimate_cost("groq/llama-3.3-70b-versatile", 1000, 500) > 0
