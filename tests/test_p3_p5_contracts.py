"""P3/P5 v1.1.0 contract: keyword_coverage, empty placeholders, auditable cover letter."""

from __future__ import annotations

from naukari_pro.llm.registry import PromptRegistry
from naukari_pro.llm.validator import load_schema, validate_response
from naukari_pro.resume_gen.cover_letter import draft_cover_letter
from naukari_pro.resume_gen.tailor import audit_no_fabrication, tailor_from_facts

FACTS = {
    "summary": "DevOps engineer focused on Kubernetes and Azure pipelines.",
    "skills": ["Python", "Kubernetes", "Azure", "Docker"],
    "experience": [
        {
            "company": "HFCL Limited",
            "title": "Engineer 1 — DevOps",
            "bullets": [
                "Containerized services with Docker on Azure.",
                "Automated CI/CD with GitHub Actions for platform services.",
            ],
        },
        {
            "company": "CGI India",
            "title": "Security Analyst Apprentice",
            "bullets": ["Supported vulnerability scanning workflows."],
        },
    ],
    "experience_bullets": [
        "Containerized services with Docker on Azure.",
        "Automated CI/CD with GitHub Actions for platform services.",
        "Supported vulnerability scanning workflows.",
    ],
}


def test_p3_and_p5_versions():
    reg = PromptRegistry()
    assert reg.get("P3_resume_tailor").version == "1.1.0"
    assert reg.get("P5_cover_letter").version == "1.1.0"


def test_tailor_emits_keyword_coverage_and_reorders():
    jd = {
        "must_haves": ["Kubernetes", "Terraform"],
        "ats_keywords": ["Azure", "Docker", "Python"],
        "nice_to_haves": ["Kafka"],
    }
    tailored = tailor_from_facts(FACTS, jd)
    assert "keyword_coverage" in tailored
    assert "Kubernetes" in tailored["keyword_coverage"]["have"]
    assert "Terraform" in tailored["keyword_coverage"]["gap"]
    assert "Terraform" in tailored["gaps_reported"]
    assert tailored["experience"][0]["company"] == "HFCL Limited"
    assert not audit_no_fabrication(tailored, FACTS)
    schema = load_schema(reg_schema_path())
    ok, errs = validate_response(tailored, schema)
    assert ok, errs


def reg_schema_path():
    from pathlib import Path

    return (
        Path(__file__).resolve().parents[1]
        / "naukari_pro/llm/prompts/schemas/P3_resume_tailor.json"
    )


def test_empty_placeholder_does_not_invent_summary():
    facts = {"skills": ["Python"], "experience_bullets": ["Built Python CLIs."]}
    tailored = tailor_from_facts(facts, {"must_haves": ["Python"], "ats_keywords": []})
    assert tailored["summary"] == ""
    assert tailored["keyword_coverage"]["have"] == ["Python"]


def test_cover_letter_lists_unsupported_must_haves():
    letter = draft_cover_letter(
        FACTS,
        company="Acme",
        title="Platform Engineer",
        must_haves=["Kubernetes", "Rust"],
    )
    assert letter["cover_letter"]
    assert "summary" in letter["claims_used"]
    assert "Rust" in letter["unsupported_claims"]
    assert "Kubernetes" not in letter["unsupported_claims"]
    schema = load_schema(
        __import__("pathlib").Path(__file__).resolve().parents[1]
        / "naukari_pro/llm/prompts/schemas/P5_cover_letter.json"
    )
    ok, errs = validate_response(letter, schema)
    assert ok, errs
