"""
Offline Test Suite for naukariPro
Asserts that offline intelligence modules:
- Config single source of truth
- Resume Maker (PDF generation, JD tailoring, Quality Scorecard)
- Server Entitlement & JWT Session Inspector (ud_isPaidClient detection)
- Interactive AI Interview Prep Answer Evaluator
- Skill Insights & Hiring Trends data matrices
- Salary parsing, filtering, and deterministic ID generation
- Profile Enhancer factual completeness audit
all operate predictably without requiring live network or external Naukri portal calls.
"""

import os
import pypdf
import pytest
from naukari_pro.config import load_config
from naukari_pro.modules.resume_maker import AIResumeMaker
from naukari_pro.modules.skill_insights import SkillInsightsEngine
from naukari_pro.modules.hiring_trends import HiringTrendsEngine
from naukari_pro.modules.interview_prep import InterviewPrepEngine, INTERVIEW_TRACKS
from naukari_pro.modules.auto_apply import is_salary_acceptable, make_job_id, parse_salary
from naukari_pro.modules.profile_performance import ProfilePerformanceEngine, decode_naukri_jwt
from naukari_pro.modules.profile_enhancer import ProfileEnhancerEngine
from naukari_pro.modules.job_alerts import InstantAlertsEngine

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
    assert cand.get("expected_ctc_lakhs") == 20

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
    assert "Hyderabad, India" in extracted_text
    assert "CGI India" in extracted_text
    assert "HFCL" in extracted_text
    assert "Jun 2026" in extracted_text
    assert "Enterprise Medallion Lakehouse Platform on Azure" in extracted_text
    assert "A, z, u, r, e" not in extracted_text
    assert "Azure Databricks, PySpark" in extracted_text

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

def test_resume_quality_scorecard():
    """Assert resume maker calculates an objective, multi-factor ATS quality score."""
    maker = AIResumeMaker()
    score = maker.calculate_resume_quality_score(jd_text="Azure Databricks PySpark Delta Lake Kafka")

    assert "overall_score" in score
    assert score["overall_score"] >= 70.0
    assert "ats_compliance_score" in score
    assert "quantified_metrics_score" in score
    assert "keyword_alignment_score" in score
    assert len(score["matched_keywords"]) > 0
    assert len(score["recommendations"]) > 0

def test_server_entitlements_jwt_inspection():
    """Verify that ProfilePerformanceEngine decodes nauk_at JWT and inspects ud_isPaidClient."""
    engine = ProfilePerformanceEngine()
    entitlements = engine.get_session_entitlements()

    assert "tier" in entitlements
    assert "is_paid_client" in entitlements
    assert "authenticated" in entitlements
    # In cookies_seed.json, ud_isPaidClient is false (Standard Free Account)
    assert entitlements["is_paid_client"] is False
    assert "Standard Free Account" in entitlements["tier"]
    assert entitlements["user_id"] == 239235296
    assert entitlements["server_entitlements"]["featured_flag_resdex"] is False
    assert entitlements["server_entitlements"]["priority_applicant_flag"] is False

def test_interview_prep_answer_evaluator():
    """Verify AI mock interview evaluator scores technical accuracy, metrics, and key concepts."""
    engine = InterviewPrepEngine()
    q = INTERVIEW_TRACKS["1. Azure Databricks & PySpark Core"][0]
    
    # Strong answer
    strong_ans = (
        "I inspect stage execution in Spark UI to identify the skewed task. "
        "For small tables under 100MB I use a broadcast join to eliminate shuffle. "
        "For large tables, I apply salting by adding a random prefix to distribute the key. "
        "In Spark 3, I enable AQE skewJoin configuration to split partitions automatically."
    )
    res = engine.score_candidate_answer(q, strong_ans)
    assert res["score"] >= 8.0
    assert "spark ui" in res["concepts_covered"]
    assert "salting" in res["concepts_covered"]
    assert "broadcast" in res["concepts_covered"]
    assert "Excellent response" in res["feedback"]

    # Weak/empty answer
    weak_res = engine.score_candidate_answer(q, "")
    assert weak_res["score"] == 0
    assert len(weak_res["concepts_missed"]) > 0

def test_profile_enhancer_audit_offline():
    """Verify profile enhancer evaluates actual config fields rather than returning dummy 100."""
    engine = ProfileEnhancerEngine()
    audit = engine.audit_profile_strength()

    assert "score" in audit
    assert "tier" in audit
    assert "checklist" in audit
    assert audit["score"] >= 75  # Factual earned points for complete profile facts
    assert len(audit["checklist"]) >= 5

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

def test_auto_apply_salary_and_id_logic():
    """Verify salary threshold filtering, undisclosed handling, and deterministic job ID."""
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

    # Parse salary checks
    parsed, min_s, max_s, summary = parse_salary("₹ 18 - 26 Lacs P.A.")
    assert min_s == 18.0
    assert max_s == 26.0

    # Deterministic job ID
    id1 = make_job_id("Azure Data Engineer", "Microsoft")
    id2 = make_job_id("azure data engineer", "MICROSOFT ")
    assert id1 == id2
    assert len(id1) == 12

def test_job_alerts_match_score():
    """Verify keyword scoring in job alerts engine."""
    engine = InstantAlertsEngine()
    score = engine.calculate_match_score("Senior Azure Data Engineer Databricks PySpark Delta Lake SQL")
    assert score >= 70

    score_low = engine.calculate_match_score("Manual QA Tester")
    assert score_low == 0

def test_unified_title_and_ctc_calibration():
    """Verify single title Azure Data Engineer and calibrated expected CTC."""
    cfg = load_config()
    cand = cfg.get("candidate", {})

    assert cand.get("target_title") == "Azure Data Engineer"
    assert cand.get("current_designation") == "Azure Data Engineer"
    assert cand.get("expected_ctc_lakhs") == 20
    assert cand.get("notice_period_days") == 30

def test_keyword_diff_engine():
    """Verify Keyword Diff matches high-intent terms and produces recommended headline."""
    engine = ProfilePerformanceEngine()
    diff = engine.generate_keyword_diff_report(live_search_terms=["Azure Databricks", "PySpark", "Delta Lake", "ADF"])

    assert "Azure Databricks" in diff["matched_terms"]
    assert "PySpark" in diff["matched_terms"]
    assert "Azure Data Engineer" in diff["recommended_headline"]
    assert "PySpark" in diff["recommended_key_skills"]
    assert "Azure Databricks" in diff["recommended_key_skills"]

def test_profile_bump_once_a_day_throttle(tmp_path):
    """Verify once-a-day bump throttle skips redundant edits if already bumped today."""
    from datetime import datetime
    test_state_file = str(tmp_path / "test_session_state.json")
    engine = ProfileEnhancerEngine(state_file=test_state_file)
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Save simulated state as already bumped today
    engine._save_state({"last_bumped_date": today, "last_bumped_timestamp": f"{today}T09:15:00"})
    
    # Second bump should cleanly return True without needing page interaction
    result = engine.bump_profile(None, force=False)
    assert result is True

def test_boosted_profile_summary_and_keywords():
    """Verify profile summary is enriched with core keywords and realistic metrics."""
    cfg = load_config()
    summary = cfg.get("profile_summary", "")
    assert len(summary) >= 150, "Profile summary must be substantial"
    
    # Must-have recruiter keywords
    keywords = [
        "Azure Data Engineer",
        "Databricks",
        "PySpark",
        "Delta Lake",
        "ADF",
        "Medallion",
        "Kafka",
        "Terraform",
        "CI/CD"
    ]
    for kw in keywords:
        assert kw.lower() in summary.lower(), f"Keyword '{kw}' missing from profile summary"

def test_agents_md_compliance_no_forbidden_verbs_and_quantified_metrics():
    """Verify all experience and project bullets adhere strictly to AGENTS.md rules."""
    import re
    cfg = load_config()
    forbidden_verbs = ["helped", "worked on", "responsible for", "assisted", "handled", "participated in"]
    
    all_bullets = []
    for exp in cfg.get("experience", []):
        all_bullets.extend(exp.get("bullets", []))
    for proj in cfg.get("projects", []):
        all_bullets.extend(proj.get("bullets", []))

    assert len(all_bullets) >= 10, "Should have at least 10 bullets across experience and projects"

    for b in all_bullets:
        b_lower = b.lower()
        # 1. No forbidden verbs
        for fv in forbidden_verbs:
            assert fv not in b_lower, f"Forbidden verb phrase '{fv}' found in bullet: {b}"

        # 2. Must start with a capitalized Tier 1/2 action verb
        first_word = b.split()[0].rstrip(",.:")
        tier_verbs = [
            "Architected", "Spearheaded", "Orchestrated", "Pioneered", "Scaled", "Transformed",
            "Engineered", "Automated", "Shipped", "Deployed", "Refactored", "Optimized",
            "Slashed", "Containerized", "Instrumented", "Provisioned", "Built", "Integrated",
            "Configured", "Standardized", "Hardened"
        ]
        assert first_word in tier_verbs, f"Bullet should begin with Tier 1/2 verb, got '{first_word}': {b}"

        # 3. Quantified metrics
        has_metric = bool(re.search(r'\d+(?:\.\d+)?\s*(?:[kmgtb]\+?|%)|\$\d+|\d+\s*(?:ms|min|sec|hours?|h|x|gb|tb|lpa|nodes?|microservices|events?|roles?|days?|environments?)', b, re.IGNORECASE))
        assert has_metric, f"Bullet must contain a quantified metric: {b}"

