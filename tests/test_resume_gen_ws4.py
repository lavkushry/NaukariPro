"""WS4: truth-preserving tailor, ATS PDF round-trip, score gate, no fabrication."""

from __future__ import annotations

from pathlib import Path

from naukari_pro.resume_gen.pipeline import ResumeGenerationPipeline
from naukari_pro.resume_gen.tailor import audit_no_fabrication, tailor_from_facts


FACTS = {
    "summary": "DevOps / Azure data platform engineer (2.5 YOE) focused on Databricks lakehouse pipelines.",
    "skills": ["Python", "SQL", "Azure", "Databricks", "PySpark", "Delta Lake", "Terraform", "Docker", "CI/CD", "ADF"],
    "experience": [
        {
            "title": "DevOps Engineer",
            "company": "CGI India",
            "dates": "Jun 2026 – Present",
            "bullets": [
                "Automated CI/CD for 5 Azure services, cutting deploy time from 45 min to 12 min (73%).",
                "Instrumented Databricks jobs with monitoring, sustaining 99.5% pipeline uptime.",
            ],
        },
        {
            "title": "Engineer 1 — DevOps / Platform Engineering",
            "company": "HFCL Limited",
            "dates": "Aug 2025 – Jun 2026",
            "bullets": [
                "Provisioned Terraform modules for 3 environments, reducing drift incidents by 40%.",
                "Containerized internal tools with Docker, improving rebuild speed 2x.",
            ],
        },
    ],
    "education": [{"degree": "B.Tech", "school": "University"}],
    "certifications": [],
}

CANDIDATE = {
    "name": "Lavkush Kumar",
    "email": "candidate@example.com",
    "phone": "+91-0000000000",
    "location": "India",
    "linkedin": "linkedin.com/in/example",
    "github": "github.com/example",
}

JD = {
    "must_haves": ["Python", "Databricks", "Delta Lake", "Azure"],
    "ats_keywords": ["Python", "Databricks", "PySpark", "Delta", "Azure", "Terraform", "SQL"],
    "nice_to_haves": ["Kafka"],
}


def test_tailor_never_adds_uncovered_keywords():
    tailored = tailor_from_facts(FACTS, {**JD, "must_haves": JD["must_haves"] + ["Kubernetes"]})
    assert "Kubernetes" in tailored["gaps_reported"]
    assert "Kubernetes" not in tailored["keywords_mirrored"]
    assert not audit_no_fabrication(tailored, FACTS)


def test_pipeline_pdf_roundtrip_and_gate(tmp_path):
    pipe = ResumeGenerationPipeline(FACTS, CANDIDATE, output_dir=tmp_path / "out", use_llm=False)
    art = pipe.generate(JD, role="Azure_Data_Engineer", company="Databricks", also_docx=False)
    assert art.pdf_path and art.pdf_path.exists()
    assert art.score.get("roundtrip_ok") is True
    assert art.fabrication_violations == []
    assert art.score["overall_score"] >= 0
    # Strong quantified + keyword overlap should pass gate
    assert art.dispatch_allowed is True
    assert art.score["overall_score"] >= 85
    assert "Name_Role" not in art.pdf_path.name  # uses real name/role/company
    assert "Lavkush" in art.pdf_path.name
