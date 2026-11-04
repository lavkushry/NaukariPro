"""P2 hiring-fit judge: evidence gates, formula weights, downgrade-when-unsure."""

from __future__ import annotations

import json

from naukari_pro.llm.registry import PromptRegistry
from naukari_pro.llm.validator import load_schema, validate_response
from naukari_pro.matching.stage_c import judge_fit, score_fit_deterministic


def test_empty_placeholders_skip():
    out = judge_fit({}, {})
    assert out["recommendation"] == "SKIP"
    assert out["fit_score"] == 0
    assert out["must_have_coverage"] == 0.0
    assert "empty_profile" in out["flags"] or "empty_requirements" in out["flags"]


def test_auto_apply_requires_zero_missing_and_thresholds():
    profile = {
        "skills": ["Python", "Databricks", "Delta Lake", "SQL", "Azure"],
        "titles": ["Azure Data Engineer"],
        "yoe": 3,
        "seniority": "mid",
        "work_mode": "hybrid",
        "location": "Bengaluru India",
        "salary_floor_lpa": 20,
    }
    job = {
        "title": "Azure Data Engineer",
        "must_haves": ["Python", "Databricks", "Delta Lake", "SQL"],
        "work_mode": "hybrid",
        "location": "Bengaluru",
        "seniority": "mid",
        "salary_signals": ["22-28 Lacs PA"],
        "role_summary": "Build Azure Databricks lakehouse pipelines.",
    }
    out = judge_fit(profile, job)
    assert out["must_have_coverage"] == 1.0
    assert all(d["evidence"] != "missing" for d in out["coverage_detail"])
    assert out["fit_score"] >= 80
    assert out["recommendation"] == "AUTO_APPLY"
    assert len(out["rationale"].split()) <= 30


def test_any_missing_blocks_auto_apply():
    profile = {"skills": ["Python"], "titles": ["Data Engineer"], "yoe": 2.5, "seniority": "mid"}
    job = {
        "title": "Data Engineer",
        "must_haves": ["Python", "Kubernetes"],
        "work_mode": "remote",
        "seniority": "mid",
        "role_summary": "Data engineering role",
    }
    out = judge_fit(profile, job)
    assert any(d["evidence"] == "missing" for d in out["coverage_detail"])
    assert out["recommendation"] != "AUTO_APPLY"


def test_transferable_counts_as_covered():
    profile = {"skills": ["Kubernetes"], "titles": ["DevOps Engineer"], "yoe": 3, "seniority": "mid"}
    job = {
        "title": "DevOps Engineer",
        "must_haves": ["k8s"],
        "work_mode": "remote",
        "seniority": "mid",
        "role_summary": "Platform devops",
    }
    out = judge_fit(profile, job)
    assert out["coverage_detail"][0]["evidence"] == "transferable"
    assert out["must_have_coverage"] == 1.0


def test_schema_validates_judge_output():
    reg = PromptRegistry()
    spec = reg.get("P2_fit_score")
    assert spec.version == "1.1.0"
    schema = load_schema(spec.schema_path)
    out = judge_fit(
        {"skills": ["Python"], "titles": ["Data Engineer"], "yoe": 2},
        {"must_haves": ["Python"], "title": "Data Engineer", "work_mode": "remote", "seniority": "mid"},
    )
    ok, errs = validate_response(out, schema)
    assert ok, errs


def test_score_fit_deterministic_legacy_decision_alias():
    scored = score_fit_deterministic(
        {"must_haves": ["Python", "Databricks", "Delta Lake", "Kubernetes"], "title": "DE", "seniority": "mid", "work_mode": "remote"},
        {"skills": ["Python", "Databricks", "Delta Lake", "Azure"], "titles": ["Data Engineer"], "yoe": 2.5, "seniority": "mid"},
    )
    assert "Kubernetes" in scored["must_have_coverage_lists"]["missing"]
    assert scored["decision"] == scored["recommendation"]
    assert scored["coverage_pct"] == round(scored["must_have_coverage"] * 100, 1)
    assert scored["coverage_pct"] >= 70
