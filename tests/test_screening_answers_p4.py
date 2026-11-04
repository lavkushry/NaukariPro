"""P4 screening answers: profile-only, ASK_USER when empty/legal, no invention."""

from __future__ import annotations

from naukari_pro.governed_apply.screening_answers import answer_screening_question
from naukari_pro.llm.registry import PromptRegistry
from naukari_pro.llm.validator import load_schema, validate_response


PROFILE = {
    "name": "Lavkush Kumar",
    "email": "candidate@example.com",
    "phone": "+91-9000000000",
    "yoe": 2.5,
    "skills": ["Python", "Azure", "Databricks", "SQL"],
    "experience": [
        {
            "title": "DevOps Engineer",
            "company": "CGI India",
            "bullets": ["Automated CI/CD for Azure services."],
        },
        {
            "title": "Engineer 1 — DevOps / Platform Engineering",
            "company": "HFCL Limited",
        },
    ],
    "legal_answers": {
        "authorized_to_work": "Yes",
    },
}


def test_empty_placeholders_ask_user():
    out = answer_screening_question(
        profile={},
        question="{{QUESTION}}",
        question_type="short_text",
        character_limit=None,
        job_title="Azure Data Engineer",
        company="Acme",
    )
    assert out["answer"] is None
    assert out["reason"] == "ASK_USER"
    assert out["confidence"] == 0.0


def test_yes_no_grounds_with_employer_and_title():
    out = answer_screening_question(
        profile=PROFILE,
        question="Do you have experience with Databricks?",
        question_type="yes_no",
        job_title="Azure Data Engineer",
        company="Acme",
    )
    assert out["reason"] == "ok"
    assert out["answer"] is not None
    assert out["answer"].lower().startswith("yes")
    assert "CGI India" in out["answer"]
    assert "DevOps Engineer" in out["answer"]
    assert "—" not in out["answer"]
    assert "passionate about" not in out["answer"].lower()


def test_open_ended_requires_experience_grounding():
    out = answer_screening_question(
        profile=PROFILE,
        question="Why are you a good fit for this role?",
        question_type="long_text",
        character_limit=280,
        job_title="Azure Data Engineer",
        company="Databricks",
    )
    assert out["reason"] == "ok"
    assert "CGI India" in (out["answer"] or "")
    assert "DevOps Engineer" in (out["answer"] or "")
    assert any(g.startswith("experience.") for g in out["grounding"])


def test_open_ended_without_experience_asks_user():
    bare = {"skills": ["Python"]}
    out = answer_screening_question(
        profile=bare,
        question="Tell us about yourself",
        question_type="long_text",
    )
    assert out["reason"] == "ASK_USER"
    assert out["answer"] is None


def test_legal_without_stored_answer_asks_user():
    out = answer_screening_question(
        profile=PROFILE,
        question="What is your ethnicity?",
        question_type="dropdown",
    )
    assert out["reason"] == "ASK_USER"


def test_legal_with_stored_answer_ok():
    out = answer_screening_question(
        profile=PROFILE,
        question="Are you authorized to work in India?",
        question_type="yes_no",
    )
    assert out["reason"] == "ok"
    assert out["answer"] == "Yes"
    assert "legal_answers.authorized_to_work" in out["grounding"]


def test_never_invent_metrics_or_employers():
    out = answer_screening_question(
        profile=PROFILE,
        question="Describe a time you saved $5 million with Kubernetes at Google",
        question_type="long_text",
        job_title="SRE",
        company="Google",
    )
    # May answer with real CGI grounding, but must not invent Google employment or $5M
    assert out["reason"] == "ok"
    ans = out["answer"] or ""
    assert "CGI India" in ans and "DevOps Engineer" in ans
    assert "million" not in ans.lower()
    assert "$5" not in ans
    assert "Google" not in ans
    assert "Kubernetes" not in ans  # not in profile skills; do not invent stack


def test_character_limit_respected():
    out = answer_screening_question(
        profile=PROFILE,
        question="Why this role?",
        question_type="long_text",
        character_limit=80,
        job_title="DE",
        company="Acme",
    )
    assert out["reason"] == "ok"
    assert len(out["answer"] or "") <= 80


def test_p4_schema_validates():
    reg = PromptRegistry()
    assert reg.get("P4_application_answers").version == "1.1.0"
    schema = load_schema(reg.get("P4_application_answers").schema_path)
    out = answer_screening_question(
        profile=PROFILE,
        question="Email",
        question_type="short_text",
    )
    payload = {k: out[k] for k in ("answer", "reason", "grounding", "confidence")}
    ok, errs = validate_response(payload, schema)
    assert ok, errs
