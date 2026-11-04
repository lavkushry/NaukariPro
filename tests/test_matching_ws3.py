"""WS3 matching: Stage A gates, deterministic Stage C thresholds, golden eval gate."""

from __future__ import annotations

from naukari_pro.matching.eval import DEFAULT_FACTS, auto_apply_allowed, run_eval, write_benchmark_report
from naukari_pro.matching.pipeline import MatchingPipeline
from naukari_pro.matching.stage_a import StageAFilter
from naukari_pro.matching.stage_c import score_fit_deterministic


def test_stage_a_title_and_null_salary():
    filt = StageAFilter()
    ok = filt.evaluate({
        "title": "Azure Data Engineer",
        "company": "Acme",
        "location": "Bengaluru",
        "salary": None,
        "jd": "Azure Databricks Python",
    })
    assert ok.passed
    # Null salary must not invent a floor failure
    assert not any(r.startswith("comp_floor") for r in ok.reasons)

    bad = filt.evaluate({
        "title": "Retail Store Manager",
        "company": "Shop",
        "location": "Mumbai",
        "jd": "retail",
    })
    assert not bad.passed


def test_stage_c_thresholds():
    structured = {
        "must_haves": ["Python", "Databricks", "Delta Lake", "Kubernetes"],
        "ats_keywords": ["Python", "Databricks", "Azure"],
        "title": "Azure Data Engineer",
        "seniority": "mid",
        "work_mode": "remote",
    }
    facts = {
        "skills": ["Python", "Databricks", "Delta Lake", "Azure"],
        "titles": ["Azure Data Engineer"],
        "yoe": 2.5,
        "seniority": "mid",
    }
    scored = score_fit_deterministic(structured, facts, title_weight=0.9)
    assert "Kubernetes" in scored["must_have_coverage_lists"]["missing"]
    assert scored["decision"] in ("REVIEW", "SKIP", "AUTO_APPLY")
    # With 3/4 covered, coverage high — but missing blocks AUTO_APPLY
    assert scored["coverage_pct"] >= 70
    assert scored["recommendation"] != "AUTO_APPLY"


def test_pipeline_auto_apply_requires_coverage():
    pipe = MatchingPipeline(DEFAULT_FACTS, use_llm=False)
    strong = pipe.evaluate({
        "title": "Azure Data Engineer",
        "company": "Databricks",
        "location": "Bengaluru",
        "salary": None,
        "jd": "Azure Databricks PySpark Delta Lake SQL Python Terraform ADF Kafka Docker CI/CD",
    })
    assert strong.stage_c is not None
    assert strong.final_decision in ("AUTO_APPLY", "REVIEW")
    if strong.final_decision == "AUTO_APPLY":
        assert strong.stage_c["coverage_pct"] >= 70
        assert strong.stage_c["fit_score"] >= 80


def test_golden_eval_writes_report(tmp_path):
    metrics = run_eval(use_llm=False, expand_to=100)
    assert metrics.n == 100
    report = write_benchmark_report(metrics, path=tmp_path / "matching_benchmark.md")
    text = report.read_text(encoding="utf-8")
    assert "Act-now precision" in text
    assert "AUTO_APPLY" in text
    # Gate helper uses same threshold
    allowed = auto_apply_allowed(metrics)
    assert allowed == (metrics.precision_act_now >= 0.9)
