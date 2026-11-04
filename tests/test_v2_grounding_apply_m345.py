"""M3–M5 core gates: deterministic score, grounding (fake-fact reject), fill verify, company cooldown."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from naukari_pro.governed_apply.dedupe_rules import CompanyDedupeLedger, EXIT_HARD_SKIP
from naukari_pro.governed_apply.fill_verify import verify_field, verify_form
from naukari_pro.matching.deterministic_score import freshness_boost, score_job
from naukari_pro.resume_gen.claim_validator import validate_text
from naukari_pro.resume_gen.writing_lint import lint_text


def test_deterministic_score_india_and_negatives():
    s = score_job(
        {
            "title": "Junior DevOps Engineer",
            "location": "Bengaluru",
            "description_full": "Kubernetes Python fresher friendly Azure",
            "company": "Acme",
        }
    )
    assert s.total > 20
    assert "location_india_or_remote" in s.flags

    bad = score_job(
        {
            "title": "Staff Principal Intern",
            "location": "Austin, TX",
            "description_full": "staff principal intern",
            "company": "TeamLease staffing",
        }
    )
    assert bad.score < 0
    assert any("consultancy" in f for f in bad.flags)


def test_freshness_boost_recomputed():
    now = datetime(2026, 11, 5, tzinfo=timezone.utc)
    recent = (now - timedelta(hours=12)).isoformat()
    old = (now - timedelta(days=10)).isoformat()
    assert freshness_boost(recent, now=now) > 0
    assert freshness_boost(old, now=now) == 0.0


def test_grounding_rejects_fake_fact():
    evidence = [
        "Engineered Kubernetes CI/CD at HFCL Limited using GitHub Actions.",
        "Deployed FastAPI services on Azure with 99.5% uptime.",
    ]
    good = validate_text(
        "Engineered Kubernetes CI/CD at HFCL Limited using GitHub Actions.",
        evidence,
    )
    assert good.ok is True

    fake = validate_text(
        "Led a 50-person org at Google and saved $5 million with sub-1ms latency.",
        evidence,
    )
    assert fake.ok is False
    assert fake.unsupported_claims
    assert any("Google" in c or "million" in c.lower() or fake.novelty_ratio > 0.34 for c in fake.unsupported_claims) or fake.novelty_ratio > 0.34


def test_puffery_and_unsourced_number_blocked():
    evidence = ["Built Docker images for internal tools."]
    report = validate_text(
        "Delivered a proven track record and improved latency by 99%.",
        evidence,
    )
    assert report.ok is False
    reasons = [r for s in report.sentences for r in s.reasons]
    assert any("puffery" in r or "unsourced_number" in r for r in reasons)


def test_writing_lint_ai_tell():
    bad = lint_text("As an AI I was thrilled to delve into your cutting-edge tapestry.")
    assert bad.verdict == "DO NOT SEND"
    good = lint_text(
        "Deployed the HFCL pipeline on Kubernetes.",
        evidence=["Deployed the HFCL pipeline on Kubernetes."],
    )
    assert good.verdict == "PASS"


def test_four_layer_fill_verification():
    ok = verify_field(
        field_id="email",
        expected="a@b.com",
        dom_value="a@b.com",
        check_validity=True,
        aria={},
        error_banners=[],
        model_value="a@b.com",
    )
    assert ok.ok is True

    # React commit mismatch
    bad = verify_field(
        field_id="phone",
        expected="+919999999999",
        dom_value="+919999999999",
        check_validity=True,
        aria={},
        error_banners=[],
        model_value="",  # model not committed
    )
    assert bad.ok is False
    assert bad.layer1_dom is True
    assert bad.commit_verified is False

    form = verify_form(
        [
            {
                "field_id": "email",
                "expected": "a@b.com",
                "dom_value": "a@b.com",
                "check_validity": True,
                "error_banners": [],
                "model_value": "a@b.com",
            },
            {
                "field_id": "name",
                "expected": "Lavkush",
                "dom_value": "Lavkush",
                "check_validity": True,
                "error_banners": [],
                "model_value": "Lavkush",
            },
        ]
    )
    assert form["all_ok"] is True
    assert form["passed"] == 2


def test_company_cooldown_hard_skip(tmp_path):
    ledger = CompanyDedupeLedger(db_path=tmp_path / "dedupe.db", cooldown_days=15, max_lifetime=2)
    assert ledger.check("Acme Corp").allow is True
    ledger.record("Acme Corp", employer_job_id="req-1", job_url="https://example.com/1")
    second = ledger.check("Acme Corp", employer_job_id="req-2")
    assert second.allow is False
    assert second.exit_code == EXIT_HARD_SKIP
    assert "same_day" in second.reason or "cooldown" in second.reason

    # exact employer job id duplicate
    ledger2 = CompanyDedupeLedger(db_path=tmp_path / "dedupe2.db")
    ledger2.record("Beta", employer_job_id="E1")
    dup = ledger2.check("Beta", employer_job_id="E1")
    assert dup.allow is False
    assert dup.exit_code == 2
