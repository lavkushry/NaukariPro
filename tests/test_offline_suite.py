"""
Offline Test Suite for naukariPro
Asserts that offline intelligence modules (resume-maker, skill-insights, hiring-trends, interview-prep)
and config single-source-of-truth operate predictably without needing live network or Naukri portal sessions.
"""

import os
import pypdf
import pytest
from naukari_pro.config import load_config
from naukari_pro.modules.resume_maker import AIResumeMaker
from naukari_pro.modules.skill_insights import SkillInsightsEngine
from naukari_pro.modules.hiring_trends import HiringTrendsEngine
from naukari_pro.modules.interview_prep import InterviewPrepEngine
from naukari_pro.modules.auto_apply import is_salary_acceptable, make_job_id

def test_config_single_source_of_truth():
    """Verify that configuration loads facts and derives screening answers from candidate data."""
    cfg = load_config()
    cand = cfg.get("candidate", {})

    assert cand.get("name") == "Lavkush Kumar"
    assert cand.get("email") == "lavkushry@gmail.com"
    assert "9122036484" in cand.get("phone", "")
    assert cand.get("total_experience_years") == 2.5
    assert cand.get("notice_period_days") == 30
    assert cand.get("current_ctc_lakhs") == 12
    assert cand.get("expected_ctc_lakhs") == 25

    # Verify dynamic linkage in screening answers
    answers = cfg.get("answers_to_common_questions", {})
    assert answers.get("experience") == str(cand.get("total_experience_years"))
    assert answers.get("notice_period") == f"{cand.get('notice_period_days')} days"
    assert answers.get("current_ctc") == str(cand.get("current_ctc_lakhs"))
    assert answers.get("expected_ctc") == str(cand.get("expected_ctc_lakhs"))

def test_resume_maker_pdf_generation(tmp_path):
    """Assert resume generates valid PDF, stays strictly 1-page, and contains config facts."""
    output_pdf = str(tmp_path / "test_resume.pdf")
    cfg = load_config()
    maker = AIResumeMaker(output_pdf_path=output_pdf)
    res_path = maker.build_ats_resume_pdf(config=cfg)

    assert os.path.exists(res_path)
    with open(res_path, "rb") as f:
        header = f.read(4)
        assert header == b"%PDF", "Output must be a valid PDF starting with %PDF"

    reader = pypdf.PdfReader(res_path)
    assert len(reader.pages) == 1, f"Resume must strictly be 1 page, got {len(reader.pages)}"

    extracted_text = reader.pages[0].extract_text()
    assert "LAVKUSH" in extracted_text.upper()
    assert "lavkushry@gmail.com" in extracted_text
    assert "9122036484" in extracted_text
    assert "CGI India" in extracted_text
    assert "HFCL" in extracted_text
    assert "Enterprise Medallion Lakehouse Platform on Azure" in extracted_text

def test_resume_maker_tailoring_with_jd(tmp_path):
    """Assert resume maker accepts a JD, reorders skills/bullets, and stays 1-page."""
    output_pdf = str(tmp_path / "tailored_resume.pdf")
    maker = AIResumeMaker(output_pdf_path=output_pdf)
    sample_jd = (
        "Seeking an Azure Data Engineer with strong experience in Apache Kafka, "
        "Azure Databricks, PySpark batch pipelines, and Delta Lake Medallion architecture."
    )
    res_path = maker.build_ats_resume_pdf(jd_text=sample_jd)

    assert os.path.exists(res_path)
    reader = pypdf.PdfReader(res_path)
    assert len(reader.pages) == 1, f"Tailored resume must strictly be 1 page, got {len(reader.pages)}"

def test_skill_insights_offline():
    """Verify in-demand skill insights load without network calls."""
    engine = SkillInsightsEngine()
    matrix = engine.get_skill_matrix()
    assert isinstance(matrix, dict)
    assert "Core Data Engineering" in matrix
    skills = [s["skill"] for s in matrix["Core Data Engineering"]]
    assert any("PySpark" in s for s in skills)
    assert any("Databricks" in s for s in skills)

def test_hiring_trends_offline():
    """Verify salary benchmarks and GCC company lists load without network calls."""
    engine = HiringTrendsEngine()
    benchmarks = engine.get_benchmarks()
    assert "Bengaluru" in benchmarks
    assert "Hyderabad" in benchmarks
    assert benchmarks["Hyderabad"]["median"] >= 20

    companies = engine.get_top_companies()
    assert len(companies) >= 5
    assert any("PNC Bank" in c["name"] for c in companies)

def test_interview_prep_offline():
    """Verify interview master bank loads technical questions for Azure Data Engineering."""
    engine = InterviewPrepEngine()
    assert len(engine.q_and_a_bank) >= 5
    first_q = engine.q_and_a_bank[0]
    assert "topic" in first_q
    assert "q" in first_q
    assert "ans" in first_q

def test_auto_apply_salary_and_id_logic():
    """Verify salary threshold filtering and deterministic job ID generation."""
    # High salary
    acceptable, _ = is_salary_acceptable("18 - 26 Lacs PA", min_threshold_lpa=12.0)
    assert acceptable is True

    # Low salary (below 12 LPA threshold)
    acceptable, reason = is_salary_acceptable("5 - 8 Lacs PA", min_threshold_lpa=12.0)
    assert acceptable is False
    assert "below 12.0 LPA threshold" in reason

    # Undisclosed salary (should consider)
    acceptable, reason = is_salary_acceptable("Not Disclosed", min_threshold_lpa=12.0)
    assert acceptable is True

    # Deterministic job ID
    id1 = make_job_id("Azure Data Engineer", "Microsoft")
    id2 = make_job_id("azure data engineer", "MICROSOFT ")
    assert id1 == id2
    assert len(id1) == 12
