"""WS4: truth-preserving tailor, ATS PDF round-trip, score gate, no fabrication."""

from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader

from naukari_pro.config import load_config
from naukari_pro.modules.candidate_profile import load_hybrid_profile
from naukari_pro.modules.resume_maker import AIResumeMaker
from naukari_pro.resume_gen.pipeline import ResumeGenerationPipeline
from naukari_pro.resume_gen.render import render_resume_pdf
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


def test_render_resume_pdf_emits_clickable_uris_and_no_empty_dates(tmp_path):
    cfg = load_config()
    cand = dict(cfg["candidate"])
    cand["email"] = "lav84095@gmail.com"
    cand["linkedin"] = "https://www.linkedin.com/in/lavkushry/"
    cand["github"] = "https://github.com/lavkushry"
    facts = {
        "summary": cfg["profile_summary"],
        "skills": cfg["default_keywords"],
        "experience": cfg["experience"],
        "projects": cfg["projects"],
        "education": cfg["education"],
        "certifications": cfg["certifications"],
    }
    tailored = tailor_from_facts(
        facts,
        {"must_haves": ["Kubernetes", "Terraform"], "ats_keywords": ["Docker", "Kafka"]},
    )
    pdf_path = render_resume_pdf(cand, tailored, output_dir=tmp_path, role="Platform_Engineer", company="Target")
    reader = PdfReader(str(pdf_path))
    txt = "\n".join((p.extract_text() or "") for p in reader.pages)
    assert "( – )" not in txt
    assert "None – None" not in txt
    assert "Jun 2026" in txt

    uris = {
        annot.get_object()["/A"]["/URI"]
        for page in reader.pages
        for annot in (page.get("/Annots") or [])
        if annot.get_object().get("/Subtype") == "/Link"
    }
    assert "mailto:lav84095@gmail.com" in uris
    assert "https://www.linkedin.com/in/lavkushry/" in uris
    assert "https://github.com/lavkushry" in uris
    assert "https://github.com/lavkushry/AegisAgent" in uris
    assert "https://github.com/lavkushry/vulcan" in uris
    assert "https://github.com/lavkushry/Azure-Data-Engineering-Medallion-Lakehouse-Project" in uris


def test_resume_maker_pdf_has_clickable_uris_and_fact_compliance(tmp_path):
    cfg = load_config()
    cfg["candidate"]["email"] = "lav84095@gmail.com"
    cfg["candidate"]["linkedin"] = "https://www.linkedin.com/in/lavkushry/"
    cfg["candidate"]["github"] = "https://github.com/lavkushry"
    out_pdf = tmp_path / "maker.pdf"
    AIResumeMaker(output_pdf_path=str(out_pdf)).build_ats_resume_pdf(config=cfg)
    reader = PdfReader(str(out_pdf))
    assert len(reader.pages) == 1
    txt = reader.pages[0].extract_text() or ""
    bad_slug = "lavkush" + "-kumar"
    assert bad_slug not in txt
    assert "mlops-platform-automation" not in txt
    assert "genai-observability-platform" not in txt

    uris = {
        annot.get_object()["/A"]["/URI"]
        for annot in (reader.pages[0].get("/Annots") or [])
        if annot.get_object().get("/Subtype") == "/Link"
    }
    assert "https://www.linkedin.com/in/lavkushry/" in uris
    assert "https://github.com/lavkushry" in uris
    assert "https://github.com/lavkushry/AegisAgent" in uris
    assert "https://github.com/lavkushry/vulcan" in uris
    assert "https://github.com/lavkushry/Azure-Data-Engineering-Medallion-Lakehouse-Project" in uris


def test_candidate_profile_env_override_takes_precedence_over_json(tmp_path, monkeypatch):
    prof_file = tmp_path / "profile.json"
    prof_file.write_text(
        json.dumps(
            {
                "linkedInUrl": "https://linkedin.com/in/stale-override",
                "githubUrl": "https://github.com/stale-override",
                "portfolioUrl": "https://github.com/stale-override",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("CANDIDATE_LINKEDIN", "https://www.linkedin.com/in/lavkushry/")
    monkeypatch.setenv("CANDIDATE_GITHUB", "https://github.com/lavkushry")
    monkeypatch.setenv("CANDIDATE_PORTFOLIO", "https://github.com/lavkushry")
    prof = load_hybrid_profile(profile_path=prof_file)
    assert prof["linkedInUrl"] == "https://www.linkedin.com/in/lavkushry/"
    assert prof["githubUrl"] == "https://github.com/lavkushry"
    assert prof["portfolioUrl"] == "https://github.com/lavkushry"
