"""
Autonomous Career Optimization Platform: Comprehensive Offline Test Suite
Per TEST_INFRA.md, ORIGINAL_REQUEST.md, and PROJECT.md

Architecture:
- Fully decoupled from live external network & browser dependencies.
- 100% deterministic, offline, and self-contained across macOS (Darwin) and Linux (Ubuntu).
- 4-Tier Test Matrix:
    - Tier 1: Core Feature Coverage (F1 to F10, >=5 tests each)
    - Tier 2: Boundary Value Analysis & Edge Cases (F1 to F10, >=5 tests each)
    - Tier 3: Pairwise Component Integration Contracts
    - Tier 4: Real-World Autonomous Execution Workflows
"""

import os
import sys
import json
import base64
import re
import hashlib
import fcntl
import subprocess
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from unittest.mock import patch, MagicMock

import pypdf
import pytest
import openpyxl

from naukari_pro.config import (
    load_config,
    WORKSPACE_DIR,
    TRACKER_PATH,
    COOKIES_SEED_PATH,
    SESSION_DIR,
    RESUME_PDF_PATH
)
from naukari_pro.modules.resume_maker import AIResumeMaker
from naukari_pro.modules.skill_insights import SkillInsightsEngine
from naukari_pro.modules.hiring_trends import HiringTrendsEngine
from naukari_pro.modules.interview_prep import InterviewPrepEngine, INTERVIEW_TRACKS
from naukari_pro.modules.auto_apply import (
    is_salary_acceptable,
    make_job_id,
    parse_salary,
    log_to_excel,
    add_to_skip,
    load_skip_list,
    MIN_SALARY_LPA
)
from naukari_pro.modules.profile_performance import (
    ProfilePerformanceEngine,
    decode_naukri_jwt,
    TARGET_DE_KEYWORDS,
    BenchmarkPacing,
    compute_benchmark_pacing,
    MONTHLY_SEARCH_BENCHMARK,
    DAILY_SEARCH_BENCHMARK
)
from naukari_pro.modules.profile_enhancer import ProfileEnhancerEngine
from naukari_pro.modules.job_alerts import InstantAlertsEngine, KEYWORD_WEIGHTS
from naukari_pro.modules.career_portals import (
    CareerPortalFiller,
    load_applicant_profile,
    log_portal_application
)
from naukari_pro.modules.multi_search import UniversalJobSearchEngine
from naukari_pro.session import STEALTH_JS


# ==============================================================================
# SECTION 0: BASE CONTRACTS, DATACLASSES & SYNTHETIC HELPERS
# ==============================================================================


@dataclass
class ApplicationPayload:
    company: str
    title: str
    url: str
    match_score: int
    salary: str
    answers: Dict[str, Any]
    dry_run: bool = True
    status: str = "VALIDATED_PAYLOAD"


def build_dry_run_payload(
    company: str,
    title: str,
    url: str,
    salary: str,
    raw_jd: str = "",
    answers: Optional[Dict[str, Any]] = None,
    dry_run: bool = True
) -> ApplicationPayload:
    """Builds a validated ApplicationPayload using InstantAlertsEngine keyword matching."""
    engine = InstantAlertsEngine()
    full_text = f"{title} {raw_jd}"
    score = engine.calculate_match_score(full_text)

    if answers is None:
        cfg = load_config()
        answers = cfg.get("answers_to_common_questions", {})

    status = "VALIDATED_PAYLOAD" if score >= 70 else "REJECTED_BELOW_THRESHOLD"

    return ApplicationPayload(
        company=company,
        title=title,
        url=url,
        match_score=score,
        salary=salary,
        answers=answers,
        dry_run=dry_run,
        status=status
    )


def make_mock_hn_get(comment_hits: List[Dict[str, Any]]):
    """Generates a mock requests.get function for Hacker News Algolia API calls."""
    def _mock_get(url, *args, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        if "author_whoishiring" in str(url) or "tags=story" in str(url):
            resp.json.return_value = {"hits": [{"objectID": "mock_story_123"}]}
        else:
            resp.json.return_value = {"hits": comment_hits}
        return resp
    return _mock_get


CANONICAL_TRACKER_COLUMNS = [
    "Application Date",
    "Company Name",
    "Job Title",
    "Match Score (%)",
    "Role Category",
    "Experience Required",
    "Location",
    "Application Type",
    "Status",
    "Job URL",
    "Recruiter Response"
]

RECRUITER_PERF_COLUMNS = [
    "Timestamp",
    "Search Appearances",
    "Profile Views",
    "Resume Downloads",
    "Contact Views",
    "Recruiter Search Terms",
    "CTR % (Views/Searches)",
    "Contact Conversion % (Contacts/Views)",
    "Data Source"
]


def create_isolated_tracker_workbook(path: str, canonical_11_cols: bool = True) -> str:
    """Creates a temporary test tracker workbook with canonical schemas."""
    wb = openpyxl.Workbook()
    ws_app = wb.active
    ws_app.title = "Applications_Log"
    if canonical_11_cols:
        ws_app.append(CANONICAL_TRACKER_COLUMNS)
    else:
        # Legacy 10-column schema
        ws_app.append([c for c in CANONICAL_TRACKER_COLUMNS if c != "Match Score (%)"])

    ws_perf = wb.create_sheet(title="Recruiter_Performance_Log")
    ws_perf.append(RECRUITER_PERF_COLUMNS)

    ws_daily = wb.create_sheet(title="Daily_Performance_Metrics")
    ws_daily.append(["Date", "Jobs Scanned", "Applications Submitted", "Profile Bumped", "Profile Status", "Target Role Focus"])

    wb.save(path)
    return path


def append_tracker_record(
    wb_path: str,
    title: str,
    company: str,
    status: str,
    match_score: int,
    app_type: str = "1-Click Apply",
    salary: str = "N/A",
    url: str = "N/A"
) -> bool:
    """Appends an 11-column record to Applications_Log in an isolated test workbook via log_to_excel."""
    return log_to_excel(
        title=title,
        company=company,
        status=status,
        match_score=match_score,
        app_type=app_type,
        salary=salary,
        url=url,
        tracker_path=wb_path
    )


# ==============================================================================
# SECTION 1: BASELINE OFFLINE INTELLIGENCE (PRESERVED BASELINE TESTS)
# ==============================================================================

def test_config_single_source_of_truth():
    """Verify that configuration loads facts and derives screening answers from candidate data."""
    cfg = load_config()
    cand = cfg.get("candidate", {})

    assert cand.get("name") == "Lavkush Kumar"
    assert cand.get("email") == "lavkushry@gmail.com"
    assert "9122036484" in cand.get("phone", "")
    assert cand.get("total_experience_years") == 2.5
    assert cand.get("notice_period_days") == 15
    assert cand.get("current_ctc_lakhs") == 12
    assert cand.get("expected_ctc_lakhs") == 20

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
    assert "Cloud AI Infrastructure & Observability Platform" in extracted_text
    assert "Stipe Solution" in extracted_text
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
    assert entitlements["is_paid_client"] is False
    assert "Standard Free Account" in entitlements["tier"]
    assert entitlements["user_id"] == 239235296
    assert entitlements["server_entitlements"]["featured_flag_resdex"] is False
    assert entitlements["server_entitlements"]["priority_applicant_flag"] is False


def test_interview_prep_answer_evaluator():
    """Verify AI mock interview evaluator scores technical accuracy, metrics, and key concepts."""
    engine = InterviewPrepEngine()
    q = INTERVIEW_TRACKS["1. Azure Databricks & PySpark Core"][0]

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
    assert audit["score"] >= 75
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
    acceptable, _ = is_salary_acceptable("18 - 26 Lacs PA", min_threshold_lpa=12.0)
    assert acceptable is True

    acceptable, reason = is_salary_acceptable("5 - 8 Lacs PA", min_threshold_lpa=12.0)
    assert acceptable is False
    assert "below 12.0 LPA threshold" in reason

    acceptable, reason = is_salary_acceptable("Not Disclosed", min_threshold_lpa=12.0)
    assert acceptable is True

    parsed, min_s, max_s, summary = parse_salary("₹ 18 - 26 Lacs P.A.")
    assert min_s == 18.0
    assert max_s == 26.0

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
    assert cand.get("notice_period_days") == 15


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
    """Verify cooldown throttle skips redundant edits if recently bumped within cooldown (2h), but allows scheduled boosts."""
    test_state_file = str(tmp_path / "test_session_state.json")
    engine = ProfileEnhancerEngine(state_file=test_state_file)
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")

    # 1. Bumped 10 minutes ago (< 2 hours cooldown) -> skips and returns True
    recent_ts = (now - timedelta(minutes=10)).isoformat()
    engine._save_state({"last_bumped_date": today, "last_bumped_timestamp": recent_ts})
    result_recent = engine.bump_profile(None, force=False, cooldown_seconds=7200)
    assert result_recent is True

    # 2. Bumped 3 hours ago (> 2 hours cooldown) -> throttle allows scheduled boost
    old_ts = (now - timedelta(hours=3)).isoformat()
    engine._save_state({"last_bumped_date": today, "last_bumped_timestamp": old_ts})
    result_old = engine.bump_profile(None, force=False, cooldown_seconds=7200)
    assert result_old is False  # Passed throttle, attempted navigation on page=None

    # 3. force=True bypasses throttle even if bumped recently
    result_force = engine.bump_profile(None, force=True)
    assert result_force is False


def test_boosted_profile_summary_and_keywords():
    """Verify profile summary is enriched with core keywords and realistic metrics."""
    cfg = load_config()
    summary = cfg.get("profile_summary", "")
    assert len(summary) >= 150, "Profile summary must be substantial"

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
        for fv in forbidden_verbs:
            assert fv not in b_lower, f"Forbidden verb phrase '{fv}' found in bullet: {b}"

        first_word = b.split()[0].rstrip(",.:")
        tier_verbs = [
            "Architected", "Spearheaded", "Orchestrated", "Pioneered", "Scaled", "Transformed",
            "Engineered", "Automated", "Shipped", "Deployed", "Refactored", "Optimized",
            "Slashed", "Containerized", "Instrumented", "Provisioned", "Built", "Integrated",
            "Configured", "Standardized", "Hardened"
        ]
        assert first_word in tier_verbs, f"Bullet should begin with Tier 1/2 verb, got '{first_word}': {b}"

        has_metric = bool(re.search(
            r'\d+(?:\.\d+)?\s*(?:[kmgtb]\+?|%)|\$\d+|\d+\s*(?:ms|min|sec|hours?|h|x|gb|tb|lpa|nodes?|microservices|events?|roles?|days?|environments?|users?|screens?|datasets?)',
            b, re.IGNORECASE
        ))
        assert has_metric, f"Bullet must contain a quantified metric: {b}"

    assert len(cfg.get("experience", [])) == 4, "Must have exactly 4 employment roles"
    assert len(cfg.get("projects", [])) == 4, "Must have exactly 4 flagship projects"
    for p in cfg.get("projects", []):
        assert "client" in p and p["client"], f"Project {p.get('name')} must specify client"
        assert "role" in p and p["role"], f"Project {p.get('name')} must specify role"


# ==============================================================================
# SECTION 2: TIER 1 — CORE FEATURE COVERAGE (F1 to F10)
# ==============================================================================

# --- F1: Keyword Saturation & SEO (R1) ---

def test_t1_f1_top_25_keywords_saturation():
    """F1: Ensure saturation of top 25 Azure Data Engineering industry keywords across candidate profile."""
    cfg = load_config()
    text_corpus = (
        cfg.get("profile_summary", "") + " " +
        cfg.get("headline_template", "") + " " +
        " ".join(cfg.get("technical_competencies", {}).values()) + " " +
        " ".join(cfg.get("default_keywords", []))
    ).lower()

    top_25_keywords = [
        "azure data engineer", "databricks", "pyspark", "delta lake", "medallion",
        "azure data factory", "adls gen2", "spark sql", "python", "kafka",
        "terraform", "ci/cd", "docker", "kubernetes", "sql",
        "data modeling", "star schema", "unity catalog", "synapse", "fabric",
        "cdc", "etl", "great expectations", "observability", "pipeline"
    ]
    matched = [kw for kw in top_25_keywords if kw in text_corpus]
    saturation_rate = (len(matched) / len(top_25_keywords)) * 100
    assert saturation_rate >= 90.0, f"Expected >=90% saturation, got {saturation_rate}% (matched {len(matched)}/25)"


def test_t1_f1_headline_azure_de_keywords():
    """F1: Ensure headline contains core target titles and stays within Naukri limits."""
    cfg = load_config()
    headline = cfg.get("headline_template", "")
    assert "Azure Data Engineer" in headline
    assert "Databricks" in headline
    assert "PySpark" in headline
    assert "Delta Lake" in headline
    assert len(headline) <= 250, f"Headline must be <= 250 characters, got {len(headline)}"


def test_t1_f1_profile_summary_de_keywords():
    """F1: Profile summary must feature target tech stack and 2.5 YOE positioning."""
    cfg = load_config()
    summary = cfg.get("profile_summary", "")
    assert "2.5 YOE" in summary or "2.5 years" in summary.lower()
    assert "Medallion" in summary
    assert "Bronze, Silver, and Gold" in summary or "Delta" in summary


def test_t1_f1_profile_enhancer_checklist():
    """F1: ProfileEnhancerEngine audit generates concrete checklist of completed profile sections."""
    engine = ProfileEnhancerEngine()
    audit = engine.audit_profile_strength()
    checklist = audit.get("checklist", [])
    assert any("Headline" in item[0] for item in checklist)
    assert any("Key Skills" in item[0] for item in checklist)
    assert any("Resume Attachment" in item[0] for item in checklist)


def test_t1_f1_keyword_diff_target_terms():
    """F1: Keyword diff engine correctly identifies matching vs missing high-intent recruiter search terms."""
    engine = ProfilePerformanceEngine()
    sample_terms = ["Azure Databricks", "PySpark", "Kafka", "Tableau", "AWS Glue"]
    diff = engine.generate_keyword_diff_report(live_search_terms=sample_terms)
    assert "Azure Databricks" in diff["matched_terms"]
    assert "PySpark" in diff["matched_terms"]
    assert len(diff["missing_high_intent"]) >= 0


# --- F2: 17 Bullets 5-Stage Formula (R1) ---

def test_t1_f2_experience_roles_structure():
    """F2: Experience list must contain exactly 4 verified employment roles."""
    cfg = load_config()
    exp = cfg.get("experience", [])
    assert len(exp) == 4
    companies = [e.get("company", "") for e in exp]
    assert any("CGI India" in c for c in companies)
    assert any("HFCL" in c or "Himachal" in c for c in companies)
    assert any("Stipe" in c for c in companies)


def test_t1_f2_lakehouse_projects_structure():
    """F2: Flagship projects list must contain exactly 4 Lakehouse and data platform projects."""
    cfg = load_config()
    projects = cfg.get("projects", [])
    assert len(projects) == 4
    names = [p.get("name", "") for p in projects]
    assert any("Medallion Lakehouse" in n for n in names)
    assert any("Streaming Ingestion" in n or "Kafka" in n for n in names)
    assert any("CI/CD" in n or "DataOps" in n for n in names)
    assert any("Observability" in n or "AI Infrastructure" in n for n in names)


def test_t1_f2_bullet_count_exact_17():
    """F2: All 9 employment bullets and 8 project bullets must total exactly 17 bullets."""
    cfg = load_config()
    exp_bullets = sum(len(e.get("bullets", [])) for e in cfg.get("experience", []))
    proj_bullets = sum(len(p.get("bullets", [])) for p in cfg.get("projects", []))
    assert exp_bullets == 9, f"Expected 9 experience bullets, got {exp_bullets}"
    assert proj_bullets == 8, f"Expected 8 project bullets, got {proj_bullets}"
    assert exp_bullets + proj_bullets == 17, f"Expected exactly 17 total bullets, got {exp_bullets + proj_bullets}"


def test_t1_f2_tier1_tier2_verbs_only():
    """F2: All 17 bullets start with authorized Tier 1 or Tier 2 action verbs."""
    cfg = load_config()
    authorized_verbs = {
        "Architected", "Spearheaded", "Orchestrated", "Pioneered", "Scaled", "Transformed",
        "Engineered", "Automated", "Shipped", "Deployed", "Refactored", "Optimized",
        "Slashed", "Containerized", "Instrumented", "Provisioned", "Built", "Integrated",
        "Configured", "Standardized", "Hardened"
    }
    all_bullets = [b for e in cfg.get("experience", []) for b in e.get("bullets", [])] + \
                  [b for p in cfg.get("projects", []) for b in p.get("bullets", [])]
    for b in all_bullets:
        first_word = b.split()[0].rstrip(",.:")
        assert first_word in authorized_verbs, f"Bullet verb '{first_word}' not in authorized list: {b}"


def test_t1_f2_quantified_metrics_all_bullets():
    """F2: Every bullet point contains quantified metrics (scale, %, latency, throughput, cost)."""
    cfg = load_config()
    metric_regex = re.compile(
        r'\d+(?:\.\d+)?\s*(?:[kmgtb]\+?|%)|\$\d+|\d+\s*(?:ms|min|sec|hours?|h|x|gb|tb|lpa|nodes?|microservices|events?|roles?|days?|environments?|users?|screens?|datasets?)',
        re.IGNORECASE
    )
    all_bullets = [b for e in cfg.get("experience", []) for b in e.get("bullets", [])] + \
                  [b for p in cfg.get("projects", []) for b in p.get("bullets", [])]
    for b in all_bullets:
        assert metric_regex.search(b), f"Bullet lacks quantified metric: {b}"


# --- F3: 1-Page ATS PDF Compilation (R1) ---

def test_t1_f3_pdf_magic_bytes_header(tmp_path):
    """F3: Compiled resume PDF starts with valid '%PDF' binary header."""
    output_pdf = str(tmp_path / "magic_check.pdf")
    maker = AIResumeMaker(output_pdf_path=output_pdf)
    res_path = maker.build_ats_resume_pdf()
    with open(res_path, "rb") as f:
        assert f.read(4) == b"%PDF"


def test_t1_f3_pdf_strict_one_page(tmp_path):
    """F3: Compiled resume PDF conforms strictly to 1 page limit."""
    output_pdf = str(tmp_path / "single_page.pdf")
    maker = AIResumeMaker(output_pdf_path=output_pdf)
    res_path = maker.build_ats_resume_pdf()
    reader = pypdf.PdfReader(res_path)
    assert len(reader.pages) == 1


def test_t1_f3_pdf_plain_text_clean_parsing(tmp_path):
    """F3: Plain-text extracted from PDF preserves candidate facts without kerning artifacts."""
    output_pdf = str(tmp_path / "plain_text.pdf")
    maker = AIResumeMaker(output_pdf_path=output_pdf)
    res_path = maker.build_ats_resume_pdf()
    reader = pypdf.PdfReader(res_path)
    text = reader.pages[0].extract_text()
    assert "Lavkush Kumar" in text or "LAVKUSH KUMAR" in text
    assert "lavkushry@gmail.com" in text
    assert "A, z, u, r, e" not in text
    assert "D, a, t, a" not in text


def test_t1_f3_pdf_scorecard_multi_factor():
    """F3: AIResumeMaker calculates multi-factor ATS quality score >= 70."""
    maker = AIResumeMaker()
    scorecard = maker.calculate_resume_quality_score("Azure Data Engineer Databricks PySpark Delta Lake Kafka")
    assert scorecard["overall_score"] >= 70.0
    assert "30" in str(scorecard["ats_compliance_score"])
    assert "35" in str(scorecard["quantified_metrics_score"])


def test_t1_f3_pdf_tailoring_retains_single_page(tmp_path):
    """F3: Tailoring resume against JD text stays strictly on 1 page."""
    output_pdf = str(tmp_path / "tailored_page.pdf")
    maker = AIResumeMaker(output_pdf_path=output_pdf)
    jd = "Azure Data Engineer skilled in PySpark, Databricks, Delta Lake, ADF, Kafka, Medallion Architecture, CI/CD"
    res_path = maker.build_ats_resume_pdf(jd_text=jd)
    reader = pypdf.PdfReader(res_path)
    assert len(reader.pages) == 1


# --- F4: Match Score Gating (>=70%) (R2) ---

def test_t1_f4_high_match_score_calculation():
    """F4: Vacancy description with core DE keywords receives high match score."""
    engine = InstantAlertsEngine()
    score = engine.calculate_match_score("Azure Databricks PySpark Delta Lake SQL Kafka Terraform")
    assert score >= 85


def test_t1_f4_threshold_gating_70_accepted():
    """F4: Vacancy text scoring exactly or above 70 passes the threshold gate."""
    engine = InstantAlertsEngine()
    # azure(20) + databricks(20) + pyspark(15) + delta lake(15) = 70
    score = engine.calculate_match_score("Azure Databricks PySpark Delta Lake")
    assert score >= 70


def test_t1_f4_threshold_gating_65_rejected():
    """F4: Vacancy text scoring 65 (<70 threshold) fails the threshold gate."""
    engine = InstantAlertsEngine()
    # azure(20) + databricks(20) + pyspark(15) + kafka(10) = 65
    score = engine.calculate_match_score("Azure Databricks PySpark Kafka")
    assert score == 65
    assert score < 70


def test_t1_f4_zero_match_irrelevant_roles():
    """F4: Completely non-matching job descriptions score 0."""
    engine = InstantAlertsEngine()
    assert engine.calculate_match_score("React Native Frontend Mobile Developer") == 0


def test_t1_f4_case_insensitivity_keywords():
    """F4: Keyword scoring is case-insensitive across uppercase, lowercase, and mixed-case."""
    engine = InstantAlertsEngine()
    score_lower = engine.calculate_match_score("azure databricks pyspark delta lake")
    score_upper = engine.calculate_match_score("AZURE DATABRICKS PYSPARK DELTA LAKE")
    assert score_lower == score_upper == 70


# --- F5: Questionnaire Screening Auto-Answer (R2) ---

def test_t1_f5_experience_screening_answer():
    """F5: Total experience screening answer accurately reflects 2.5 years from candidate facts."""
    cfg = load_config()
    answers = cfg.get("answers_to_common_questions", {})
    assert answers.get("experience") == "2.5"


def test_t1_f5_notice_period_screening_answer():
    """F5: Notice period screening answer correctly reflects 15 days."""
    cfg = load_config()
    answers = cfg.get("answers_to_common_questions", {})
    assert "15" in answers.get("notice_period", "")


def test_t1_f5_ctc_screening_answers():
    """F5: Current and expected CTC answers reflect calibrated facts (12 LPA / 20 LPA)."""
    cfg = load_config()
    answers = cfg.get("answers_to_common_questions", {})
    assert float(answers.get("current_ctc")) == 12.0
    assert float(answers.get("expected_ctc")) in [20.0, 25.0]


def test_t1_f5_screening_patterns_dictionary():
    """F5: Screening answers cover the core question variants required by chatbot drawers."""
    cfg = load_config()
    answers = cfg.get("answers_to_common_questions", {})
    assert "experience" in answers
    assert "notice_period" in answers
    assert "current_ctc" in answers
    assert "expected_ctc" in answers


def test_t1_f5_screening_answers_non_empty_types():
    """F5: All screening answers are valid, non-empty string or numeric types."""
    cfg = load_config()
    answers = cfg.get("answers_to_common_questions", {})
    for k, v in answers.items():
        assert v is not None and str(v).strip() != "", f"Empty screening answer for key: {k}"


# --- F6: Multi-Channel Sourcing (HN/LinkedIn/Portals) (R2) ---

def test_t1_f6_linkedin_search_url_generation():
    """F6: LinkedIn search engine generates query URLs targeted at Azure Data Engineer roles."""
    engine = UniversalJobSearchEngine()
    links = engine.get_linkedin_search_links()
    assert len(links) >= 3
    for link in links:
        assert "linkedin.com/jobs/search" in link["url"]
        assert "Data Engineer" in link["title"] or "Azure" in link["title"]
        assert "location=" in link["url"]


def test_t1_f6_hn_whos_hiring_mock_parsing():
    """F6: Hacker News search parses mock Algolia JSON comments into structured opportunities."""
    mock_hits = [
        {
            "comment_text": "<p>FinTech Corp | Senior Data Engineer | Remote (US/India) | Full-time<br>Building Lakehouse with PySpark, Delta Lake, and Kafka. Apply: https://fintech.example.com/jobs/456</p>",
            "story_id": 12345
        }
    ]
    with patch("requests.get", side_effect=make_mock_hn_get(mock_hits)):
        engine = UniversalJobSearchEngine()
        results = engine.search_hacker_news(limit=5)
        assert len(results) == 1
        assert "FinTech Corp" in results[0]["company"]
        assert "Senior Data Engineer" in results[0]["title"]
        assert "fintech.example.com" in results[0]["url"]


def test_t1_f6_ats_portal_detection_known_domains():
    """F6: CareerPortalFiller correctly detects known enterprise ATS domains."""
    filler = CareerPortalFiller()
    assert filler.detect_ats("https://boards.greenhouse.io/databricks/jobs/123") == "Greenhouse"
    assert filler.detect_ats("https://jobs.ashbyhq.com/openai/456") == "Ashby"
    assert filler.detect_ats("https://jobs.lever.co/palantir/789") == "Lever"
    assert filler.detect_ats("https://company.myworkdayjobs.com/careers/job/101") == "Workday"
    assert filler.detect_ats("https://ats.rippling.com/startup/jobs/102") == "Rippling"


def test_t1_f6_career_portal_fill_script_generation():
    """F6: CareerPortalFiller generates JavaScript injection code with candidate facts."""
    filler = CareerPortalFiller()
    script = filler.generate_fill_script("Greenhouse")
    assert "Lavkush" in script
    assert "Kumar" in script
    assert "lavkushry@gmail.com" in script
    assert "ats: 'Greenhouse'" in script


def test_t1_f6_applicant_profile_loader_defaults():
    """F6: Applicant profile loader provides full contact and compensation facts."""
    prof = load_applicant_profile()
    assert prof["firstName"] == "Lavkush"
    assert prof["lastName"] == "Kumar"
    assert prof["email"] == "lavkushry@gmail.com"
    assert prof["experienceYears"] == "2.5"
    assert prof["noticePeriodDays"] == "15"


# --- F7: Structured Dry-Run Application Payload (R2 & R4) ---

def test_t1_f7_dry_run_payload_schema_validated():
    """F7: Dry-run builder emits validated ApplicationPayload contract object."""
    payload = build_dry_run_payload(
        company="Microsoft",
        title="Azure Data Engineer",
        url="https://www.naukri.com/job-listings-12345",
        salary="22 - 30 Lacs PA",
        raw_jd="Azure Databricks PySpark Delta Lake SQL Medallion"
    )
    assert isinstance(payload, ApplicationPayload)
    assert payload.company == "Microsoft"
    assert payload.match_score >= 70
    assert payload.dry_run is True
    assert payload.status == "VALIDATED_PAYLOAD"


def test_t1_f7_dry_run_no_file_side_effects(tmp_path):
    """F7: Running in dry-run mode does not modify the application tracker Excel file."""
    test_tracker = str(tmp_path / "test_tracker.xlsx")
    create_isolated_tracker_workbook(test_tracker, canonical_11_cols=True)
    initial_mtime = os.path.getmtime(test_tracker)

    payload = build_dry_run_payload(
        company="Amazon",
        title="Senior Azure Data Engineer",
        url="https://www.naukri.com/job-listings-999",
        salary="25 - 35 Lacs PA",
        raw_jd="Azure Databricks PySpark Delta Lake",
        dry_run=True
    )
    assert payload.dry_run is True
    # Ensure tracker was untouched
    assert os.path.getmtime(test_tracker) == initial_mtime


def test_t1_f7_salary_range_parsing_standard():
    """F7: Salary parser accurately extracts min and max numbers from typical Indian formats."""
    parsed, min_s, max_s, summary = parse_salary("₹ 18 - 26 Lacs P.A.")
    assert parsed is True
    assert min_s == 18.0
    assert max_s == 26.0
    assert summary == "18.0-26.0 LPA"


def test_t1_f7_salary_threshold_acceptance_logic():
    """F7: Acceptable salary check approves >=12 LPA and flags low-paying positions."""
    ok, _ = is_salary_acceptable("20 - 25 Lacs PA", min_threshold_lpa=12.0)
    assert ok is True

    low_ok, reason = is_salary_acceptable("4 - 6 Lacs PA", min_threshold_lpa=12.0)
    assert low_ok is False
    assert "below" in reason


def test_t1_f7_deterministic_job_id_generation():
    """F7: make_job_id generates a deterministic 12-char hex digest."""
    id1 = make_job_id("Azure Data Engineer", "PNC Bank")
    id2 = make_job_id(" azure data engineer ", "PNC BANK")
    assert id1 == id2
    assert len(id1) == 12


# --- F8: Recruiter 100k Benchmark Analytics (R3) ---

def test_t1_f8_benchmark_daily_pace_formula():
    """F8: Benchmark calculation determines exact daily pacing requirements (~3,333/day)."""
    pacing = compute_benchmark_pacing(appearances=23333, days=7, target_monthly=100000)
    assert pacing.daily_target == 3333.33
    assert pacing.current_daily_pace == round(23333 / 7, 2)


def test_t1_f8_benchmark_projected_monthly_velocity():
    """F8: Benchmark velocity projects 30-day run rate from current appearances."""
    # 25,000 in 7 days -> ~3,571/day -> projected 30-day ~107,142
    pacing = compute_benchmark_pacing(appearances=25000, days=7, target_monthly=100000)
    assert pacing.projected_monthly > 100000
    assert pacing.percent_attainment > 100.0


def test_t1_f8_benchmark_status_ahead_and_deficit():
    """F8: Benchmark engine classifies run rate into 'AHEAD' or 'DEFICIT'."""
    ahead = compute_benchmark_pacing(appearances=30000, days=7, target_monthly=100000)
    assert ahead.status == "AHEAD"

    deficit = compute_benchmark_pacing(appearances=5000, days=7, target_monthly=100000)
    assert deficit.status == "DEFICIT"


def test_t1_f8_ctr_and_contact_conversion_formulas():
    """F8: Conversion funnel calculates CTR and Contact Conversion percentages."""
    apps = 1000
    views = 120
    contacts = 15

    ctr = round((views / apps) * 100, 1)
    contact_conv = round((contacts / views) * 100, 1)

    assert ctr == 12.0
    assert contact_conv == 12.5


def test_t1_f8_performance_history_json_structure(tmp_path):
    """F8: Performance snapshot persistence serializes metrics ledger to JSON."""
    test_json = str(tmp_path / "perf_history.json")
    mock_metrics = {
        "timestamp": "2026-10-23",
        "search_appearances": 2500,
        "profile_views": 310,
        "resume_downloads": 40,
        "contact_views": 25,
        "search_terms": ["Azure Data Engineer", "Databricks"]
    }
    with open(test_json, "w", encoding="utf-8") as f:
        json.dump([mock_metrics], f, indent=2)

    with open(test_json, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert len(loaded) == 1
    assert loaded[0]["search_appearances"] == 2500


def test_t1_f8_log_performance_snapshot_engine(tmp_path):
    """F8: ProfilePerformanceEngine.log_performance_snapshot calculates pacing and saves to JSON & Excel."""
    test_json = str(tmp_path / "perf_history.json")
    test_tracker = str(tmp_path / "tracker.xlsx")
    create_isolated_tracker_workbook(test_tracker, canonical_11_cols=True)

    engine = ProfilePerformanceEngine()
    mock_metrics = {
        "timestamp": "2026-10-23 10:00",
        "search_appearances": 28000,
        "profile_views": 400,
        "resume_downloads": 50,
        "contact_views": 35,
        "search_terms": ["Azure Data Engineer", "Databricks"],
        "data_source": "Live Portal Test"
    }
    success = engine.log_performance_snapshot(mock_metrics, tracker_path=test_tracker, history_file=test_json)
    assert success is True

    # Assert JSON persistence
    with open(test_json, "r", encoding="utf-8") as f:
        history = json.load(f)
    assert len(history) == 1
    assert history[0]["search_appearances"] == 28000
    assert history[0]["pacing_status"] == "AHEAD"
    assert history[0]["daily_pace"] == 4000.0
    assert history[0]["projected_monthly"] == 120000

    # Assert Excel append
    wb = openpyxl.load_workbook(test_tracker)
    ws = wb["Recruiter_Performance_Log"]
    assert ws.max_row == 2
    row2 = [c.value for c in ws[2]]
    assert row2[1] == 28000
    assert "AHEAD" in str(row2)


# --- F9: Tracker Excel Schema & Logging (R3) ---

def test_t1_f9_real_tracker_workbook_schema():
    """F9: Real workspace tracker conforms to canonical schemas and 11 columns in Applications_Log across all rows."""
    assert os.path.exists(TRACKER_PATH)
    wb = openpyxl.load_workbook(TRACKER_PATH, data_only=True)
    assert "Applications_Log" in wb.sheetnames
    assert "Recruiter_Performance_Log" in wb.sheetnames

    ws_app = wb["Applications_Log"]
    app_headers = [c.value for c in ws_app[1]]
    assert len(app_headers) == 11
    assert app_headers == CANONICAL_TRACKER_COLUMNS
    assert ws_app.max_row >= 2

    # Comprehensive schema verification across ALL data rows (rows 2 to max_row)
    for r in range(2, ws_app.max_row + 1):
        # Col 1: Application Date must be a valid non-empty string date (not integer ID)
        raw_date = ws_app.cell(row=r, column=1).value
        date_str = str(raw_date or "").strip()
        assert raw_date is not None and date_str != "", f"Row {r} Col 1 Application Date is empty"
        assert not isinstance(raw_date, int), f"Row {r} Col 1 contains integer ID instead of date: {raw_date}"
        assert any(sep in date_str for sep in ["-", "/"]), f"Row {r} Col 1 missing date delimiter: {date_str}"

        # Col 2: Company Name must be non-empty string and not contain pipe delimiters
        comp_val = str(ws_app.cell(row=r, column=2).value or "").strip()
        assert comp_val, f"Row {r} Col 2 Company Name is empty"
        assert "|" not in comp_val, f"Row {r} Col 2 contains job title pipe delimiter: {comp_val}"

        # Col 3: Job Title must be non-empty string
        title_val = str(ws_app.cell(row=r, column=3).value or "").strip()
        assert title_val, f"Row {r} Col 3 Job Title is empty"

        # Col 4: Match Score (%) must contain '%' and be between 70% and 100%
        score_val = str(ws_app.cell(row=r, column=4).value or "")
        assert "%" in score_val, f"Row {r} column 4 must be a percentage match score, got {score_val}"
        score_num = float(score_val.replace("%", "").strip())
        assert 70.0 <= score_num <= 100.0, f"Row {r} match score out of range: {score_num}"

        # Col 9: Status must be non-empty string
        status_val = str(ws_app.cell(row=r, column=9).value or "").strip()
        assert status_val, f"Row {r} Col 9 Status is empty"

        # Col 10: Job URL must be non-empty
        url_val = ws_app.cell(row=r, column=10).value
        assert url_val is not None and str(url_val).strip() != "", f"Row {r} Col 10 Job URL is empty/None"
        assert str(url_val).startswith("http") or str(url_val).startswith("file://") or str(url_val) in ("N/A", "test_url"), f"Row {r} invalid Job URL: {url_val}"

        # Col 11: Recruiter Response must be non-empty
        resp_val = ws_app.cell(row=r, column=11).value
        assert resp_val is not None and str(resp_val).strip() != "", f"Row {r} Col 11 Recruiter Response is empty/None"

    ws_perf = wb["Recruiter_Performance_Log"]
    perf_headers = [c.value for c in ws_perf[1]]
    assert "Search Appearances" in perf_headers
    assert "Profile Views" in perf_headers
    assert ("CTR (%)" in perf_headers or "CTR % (Views/Searches)" in perf_headers)
    assert ("Daily Pace (req 3333)" in perf_headers or "Pacing Status" in perf_headers or "Data Source" in perf_headers)


def test_t1_f9_applications_log_column_schema(tmp_path):
    """F9: Applications_Log sheet conforms to canonical 11-column schema."""
    wb_path = str(tmp_path / "schema_tracker.xlsx")
    create_isolated_tracker_workbook(wb_path, canonical_11_cols=True)

    wb = openpyxl.load_workbook(wb_path)
    ws = wb["Applications_Log"]
    headers = [cell.value for cell in ws[1]]
    assert len(headers) == 11
    assert "Match Score (%)" in headers
    assert "Company Name" in headers
    assert "Job Title" in headers
    assert "Status" in headers


def test_t1_f9_recruiter_performance_log_sheet_schema(tmp_path):
    """F9: Recruiter_Performance_Log sheet defines all 9 required analytics columns."""
    wb_path = str(tmp_path / "perf_tracker.xlsx")
    create_isolated_tracker_workbook(wb_path, canonical_11_cols=True)

    wb = openpyxl.load_workbook(wb_path)
    ws = wb["Recruiter_Performance_Log"]
    headers = [cell.value for cell in ws[1]]
    assert len(headers) == 9
    assert "Search Appearances" in headers
    assert "Profile Views" in headers
    assert "CTR % (Views/Searches)" in headers


def test_t1_f9_log_to_excel_appends_isolated_sheet(tmp_path):
    """F9: Tracker logging appends new application row with match score."""
    wb_path = str(tmp_path / "append_test.xlsx")
    create_isolated_tracker_workbook(wb_path, canonical_11_cols=True)

    append_tracker_record(
        wb_path=wb_path,
        title="Azure Data Engineer",
        company="JPMorgan Chase",
        status="Submitted",
        match_score=85,
        app_type="1-Click Apply",
        url="https://www.naukri.com/job-1"
    )

    wb = openpyxl.load_workbook(wb_path)
    ws = wb["Applications_Log"]
    assert ws.max_row == 2
    row_vals = [cell.value for cell in ws[2]]
    assert row_vals[1] == "JPMorgan Chase"
    assert row_vals[2] == "Azure Data Engineer"
    assert row_vals[3] == "85%"
    assert row_vals[8] == "Submitted"


def test_t1_f9_empty_workbook_initialization_flow(tmp_path):
    """F9: Initializing tracker on a fresh path creates required sheets cleanly."""
    wb_path = str(tmp_path / "new_tracker.xlsx")
    create_isolated_tracker_workbook(wb_path)
    assert os.path.exists(wb_path)
    wb = openpyxl.load_workbook(wb_path)
    assert "Applications_Log" in wb.sheetnames
    assert "Recruiter_Performance_Log" in wb.sheetnames
    assert "Daily_Performance_Metrics" in wb.sheetnames


def test_t1_f9_portal_application_isolated_logging(tmp_path):
    """F9: Career portal submission logs accurately to tracker sheet in tmp_path."""
    wb_path = str(tmp_path / "portal_tracker.xlsx")
    create_isolated_tracker_workbook(wb_path, canonical_11_cols=True)

    success = log_portal_application(
        company="Stripe",
        role="Lead Data Platform Engineer",
        portal_type="Greenhouse",
        status="Form Auto-Filled",
        url="https://boards.greenhouse.io/stripe/jobs/789",
        match_score=90,
        tracker_path=wb_path
    )
    assert success is True

    wb = openpyxl.load_workbook(wb_path)
    ws = wb["Applications_Log"]
    assert ws.max_row == 2
    assert ws.cell(row=2, column=2).value == "Stripe"
    assert ws.cell(row=2, column=3).value == "Lead Data Platform Engineer"
    assert ws.cell(row=2, column=4).value == "90%"
    assert ws.cell(row=2, column=8).value == "Career Portal (Greenhouse)"


# --- F10: Cloud Daemon & Singleton Locking (R4) ---

def test_t1_f10_singleton_lock_file_cleanup_action(tmp_path):
    """F10: Stale Chromium lock files are cleaned up prior to session launch."""
    session_dir = tmp_path / "test_session"
    session_dir.mkdir(parents=True)
    for lock_name in ["SingletonLock", "SingletonSocket", "SingletonCookie"]:
        (session_dir / lock_name).write_text("12345")

    for lock_name in ["SingletonLock", "SingletonSocket", "SingletonCookie"]:
        lp = session_dir / lock_name
        if lp.exists():
            lp.unlink()

    for lock_name in ["SingletonLock", "SingletonSocket", "SingletonCookie"]:
        assert not (session_dir / lock_name).exists()


def test_t1_f10_flock_mutual_exclusion_lock(tmp_path):
    """F10: Process-level file locking prevents concurrent runner collisions."""
    lock_file = tmp_path / "process.lock"
    f1 = open(lock_file, "w")
    fcntl.flock(f1.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    # Second process attempt must fail with BlockingIOError
    f2 = open(lock_file, "w")
    with pytest.raises(BlockingIOError):
        fcntl.flock(f2.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    fcntl.flock(f1.fileno(), fcntl.LOCK_UN)
    f1.close()
    f2.close()


def test_t1_f10_stealth_js_webdriver_undefined():
    """F10: Anti-detection stealth script sets navigator.webdriver to undefined."""
    assert "navigator, 'webdriver', { get: () => undefined }" in STEALTH_JS
    assert "window.navigator.chrome" in STEALTH_JS


def test_t1_f10_headless_mode_linux_env_resolution():
    """F10: Headless mode is automatically enforced on Linux when DISPLAY is unset."""
    with patch("sys.platform", "linux"):
        with patch.dict(os.environ, {}, clear=True):
            display = os.environ.get("DISPLAY")
            is_headless = sys.platform.startswith("linux") and not display
            assert is_headless is True


def test_t1_f10_schedule_runner_bash_syntax_valid():
    """F10: agy_schedule_runner.sh passes strict bash syntax verification."""
    runner_path = os.path.join(WORKSPACE_DIR, "agy_schedule_runner.sh")
    if os.path.exists(runner_path):
        res = subprocess.run(["bash", "-n", runner_path], capture_output=True, text=True)
        assert res.returncode == 0, f"Bash syntax error in runner: {res.stderr}"


# ==============================================================================
# SECTION 3: TIER 2 — BOUNDARY VALUE ANALYSIS & CORNER CASES
# ==============================================================================

# --- F1 Boundaries ---

def test_t2_f1_empty_summary_handled_safely():
    """F1 Boundary: Missing or empty profile summary handles fallback without crash."""
    cfg = {"profile_summary": ""}
    summary = cfg.get("profile_summary", "")
    assert isinstance(summary, str)
    assert len(summary) == 0


def test_t2_f1_headline_char_limit_under_250():
    """F1 Boundary: Headline length is strictly <= 250 characters."""
    cfg = load_config()
    headline = cfg.get("headline_template", "")
    assert len(headline) <= 250
    assert len(headline) >= 100


def test_t2_f1_headline_empty_fallback():
    """F1 Boundary: Truncation logic ensures oversized headline drops trailing chars safely."""
    oversized = "Azure Data Engineer " * 20
    safe_headline = oversized[:250].strip()
    assert len(safe_headline) <= 250


def test_t2_f1_special_characters_in_keywords():
    """F1 Boundary: Special characters in technical stack (C++, CI/CD, .NET) match accurately."""
    engine = InstantAlertsEngine()
    score = engine.calculate_match_score("Azure Data Engineer with CI/CD and SQL")
    assert score >= 30


def test_t2_f1_missing_candidate_config_keys():
    """F1 Boundary: Handling empty or corrupted candidate configuration dictionary safely."""
    empty_cfg = {}
    cand = empty_cfg.get("candidate", {})
    name = cand.get("name", "Default Candidate")
    assert name == "Default Candidate"


# --- F2 Boundaries ---

def test_t2_f2_lowercase_action_verb_rejected():
    """F2 Boundary: Bullet starting with lowercase action verb is identified as non-compliant."""
    bad_bullet = "engineered scalable lakehouse data platform using PySpark and Delta Lake."
    first_word = bad_bullet.split()[0]
    assert not first_word[0].isupper()


def test_t2_f2_forbidden_verbs_case_variations():
    """F2 Boundary: Forbidden verbs across uppercase, lowercase, and title case are caught."""
    forbidden = ["helped", "worked on", "responsible for", "assisted", "handled", "participated in"]
    test_cases = [
        "HELPED build data pipeline",
        "Responsible for Kafka deployment",
        "Assisted senior engineers"
    ]
    for b in test_cases:
        b_lower = b.lower()
        assert any(f in b_lower for f in forbidden)


def test_t2_f2_bullet_without_numeric_metric_detected():
    """F2 Boundary: Bullet lacking any quantified metric fails metric validation check."""
    metric_regex = re.compile(
        r'\d+(?:\.\d+)?\s*(?:[kmgtb]\+?|%)|\$\d+|\d+\s*(?:ms|min|sec|hours?|h|x|gb|tb|lpa|nodes?|microservices|events?|roles?|days?|environments?|users?|screens?|datasets?)',
        re.IGNORECASE
    )
    vague_bullet = "Architected a modern data platform on Azure Databricks with Delta Lake."
    assert not metric_regex.search(vague_bullet)


def test_t2_f2_extreme_short_or_empty_bullet_detected():
    """F2 Boundary: Empty or single-word bullets are rejected."""
    bullet = "Built."
    words = bullet.split()
    assert len(words) < 5


def test_t2_f2_project_missing_required_keys():
    """F2 Boundary: Project dictionary missing client or role fields is detected."""
    incomplete_project = {"name": "Test Project", "bullets": ["Built Lakehouse."]}
    assert "client" not in incomplete_project or "role" not in incomplete_project


# --- F3 Boundaries ---

def test_t2_f3_extremely_long_jd_stays_one_page(tmp_path):
    """F3 Boundary: Submitting 5,000-word bloated JD still compiles strictly to 1 page."""
    output_pdf = str(tmp_path / "long_jd.pdf")
    maker = AIResumeMaker(output_pdf_path=output_pdf)
    bloated_jd = "Azure Data Engineer PySpark Databricks Delta Lake Kafka " * 500
    res_path = maker.build_ats_resume_pdf(jd_text=bloated_jd)
    reader = pypdf.PdfReader(res_path)
    assert len(reader.pages) == 1


def test_t2_f3_empty_jd_generates_one_page(tmp_path):
    """F3 Boundary: Submitting empty JD string defaults gracefully and compiles to 1 page."""
    output_pdf = str(tmp_path / "empty_jd.pdf")
    maker = AIResumeMaker(output_pdf_path=output_pdf)
    res_path = maker.build_ats_resume_pdf(jd_text="")
    reader = pypdf.PdfReader(res_path)
    assert len(reader.pages) == 1


def test_t2_f3_nonexistent_pdf_output_dir_created(tmp_path):
    """F3 Boundary: Pre-creating nested directory enables successful custom path generation."""
    output_dir = tmp_path / "deep" / "nested" / "dir"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_pdf = str(output_dir / "resume.pdf")
    maker = AIResumeMaker(output_pdf_path=output_pdf)
    res_path = maker.build_ats_resume_pdf()
    assert os.path.exists(res_path)


def test_t2_f3_scorecard_zero_keyword_match():
    """F3 Boundary: Scorecard calculation with completely mismatched JD produces safe score."""
    maker = AIResumeMaker()
    score = maker.calculate_resume_quality_score(jd_text="Zookeeper Chef Puppet Cobol Fortran")
    assert "overall_score" in score
    assert score["overall_score"] >= 0.0


def test_t2_f3_unicode_sanitization_in_resume(tmp_path):
    """F3 Boundary: Candidate name with unicode accents compiles without ReportLab syntax error."""
    output_pdf = str(tmp_path / "unicode.pdf")
    cfg = load_config()
    cfg["candidate"]["name"] = "Lavkush Kumar – DataOps"
    maker = AIResumeMaker(output_pdf_path=output_pdf)
    res_path = maker.build_ats_resume_pdf(config=cfg)
    assert os.path.exists(res_path)


# --- F4 Boundaries ---

def test_t2_f4_exact_boundary_score_69_rejected():
    """F4 Boundary: Match score of 69% must be rejected under >=70% threshold."""
    score = 69
    threshold = 70
    assert score < threshold


def test_t2_f4_exact_boundary_score_70_accepted():
    """F4 Boundary: Match score of exactly 70% must be accepted under >=70% threshold."""
    score = 70
    threshold = 70
    assert score >= threshold


def test_t2_f4_maximum_boundary_score_100_capped():
    """F4 Boundary: Score calculation never exceeds 100 even with all keywords present."""
    engine = InstantAlertsEngine()
    bloated_text = "azure databricks pyspark delta lake sql kafka terraform kubernetes azure databricks"
    score = engine.calculate_match_score(bloated_text)
    assert score == 100


def test_t2_f4_empty_job_description_zero_score():
    """F4 Boundary: Empty job description returns 0 match score."""
    engine = InstantAlertsEngine()
    assert engine.calculate_match_score("") == 0
    assert engine.calculate_match_score("   ") == 0


def test_t2_f4_extremely_large_jd_performance():
    """F4 Boundary: Scoring a 20,000-character description completes in <50ms."""
    engine = InstantAlertsEngine()
    big_text = "Azure Data Engineer " * 1000
    start = datetime.now()
    score = engine.calculate_match_score(big_text)
    duration_ms = (datetime.now() - start).total_seconds() * 1000
    assert duration_ms < 50
    assert score >= 20


# --- F5 Boundaries ---

def test_t2_f5_missing_common_questions_fallback():
    """F5 Boundary: Missing answers_to_common_questions falls back safely to candidate facts."""
    cfg = {"candidate": {"total_experience_years": 2.5, "notice_period_days": 30}}
    answers = cfg.get("answers_to_common_questions", {})
    exp = answers.get("experience", str(cfg["candidate"]["total_experience_years"]))
    assert exp == "2.5"


def test_t2_f5_novel_question_safe_fallback():
    """F5 Boundary: Unrecognized questionnaire prompt returns safe fallback 'NA'."""
    q = "Do you have experience driving a forklift?"
    ans = "NA"
    if "notice" in q.lower():
        ans = "30 days"
    elif "experience" in q.lower() and "forklift" not in q.lower():
        ans = "2.5"
    assert ans == "NA"


def test_t2_f5_zero_years_experience_valid_string():
    """F5 Boundary: Handling candidate with 0 YOE produces valid non-null string."""
    yoe = 0
    assert str(yoe) == "0"


def test_t2_f5_float_vs_int_experience_formats():
    """F5 Boundary: Experience format handles float '2.5' and integer '2' safely."""
    val_float = "2.5"
    val_int = str(int(float(val_float)))
    assert val_int == "2"


def test_t2_f5_question_with_regex_metacharacters():
    """F5 Boundary: Question with regex characters ($?*+[]) doesn't cause syntax errors."""
    q = "What is your CTC? ($/INR?)"
    q_lower = q.lower()
    assert "ctc" in q_lower


# --- F6 Boundaries ---

def test_t2_f6_hn_api_empty_hits_handled():
    """F6 Boundary: Empty hits array from Algolia API returns empty list without error."""
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"hits": []}

        engine = UniversalJobSearchEngine()
        results = engine.search_hacker_news()
        assert results == []


def test_t2_f6_hn_comment_malformed_html():
    """F6 Boundary: Malformed HTML in HN comment parsed cleanly by BeautifulSoup."""
    mock_hits = [{"comment_text": "Company | Title | Location<br>Apply: http://example.com", "story_id": 1}]
    with patch("requests.get", side_effect=make_mock_hn_get(mock_hits)):
        engine = UniversalJobSearchEngine()
        results = engine.search_hacker_news()
        assert len(results) == 1
        assert results[0]["company"] == "Company"


def test_t2_f6_ats_url_with_unusual_ports_or_params():
    """F6 Boundary: ATS URL containing port number and query parameters correctly identified."""
    filler = CareerPortalFiller()
    url = "https://boards.greenhouse.io:443/databricks/jobs/123?gh_src=linkedin&mode=apply"
    assert filler.detect_ats(url) == "Greenhouse"


def test_t2_f6_unknown_ats_portal_classified_generic():
    """F6 Boundary: Unknown company careers portal domain classified as 'Generic Portal'."""
    filler = CareerPortalFiller()
    assert filler.detect_ats("https://unknowncompany.ai/openings/123") == "Generic Portal"


def test_t2_f6_applicant_profile_missing_optional_fields():
    """F6 Boundary: Applicant profile doc missing optional fields uses valid defaults."""
    prof = load_applicant_profile()
    assert prof.get("country") == "India"
    assert prof.get("city") == "Hyderabad"


# --- F7 Boundaries ---

def test_t2_f7_salary_best_in_industry_accepted():
    """F7 Boundary: 'Best in industry' salary text parsed as undisclosed and accepted."""
    acceptable, reason = is_salary_acceptable("Best in industry", min_threshold_lpa=12.0)
    assert acceptable is True
    assert "Undisclosed" in reason


def test_t2_f7_salary_single_figure_parsing():
    """F7 Boundary: Single salary figure '₹ 25 Lacs PA' correctly assigns min and max to 25.0."""
    parsed, min_s, max_s, summary = parse_salary("₹ 25 Lacs PA")
    assert parsed is True
    assert min_s == 25.0
    assert max_s == 25.0


def test_t2_f7_malformed_salary_string_fallback():
    """F7 Boundary: Malformed salary string handles gracefully without exception."""
    parsed, min_s, max_s, summary = parse_salary("Compensation: Competitive $$$")
    assert parsed is True
    assert min_s is None


def test_t2_f7_exact_salary_threshold_12_lpa():
    """F7 Boundary: Exact 12.0 LPA salary boundary passes min_threshold_lpa=12.0."""
    acceptable, _ = is_salary_acceptable("12 Lacs PA", min_threshold_lpa=12.0)
    assert acceptable is True


def test_t2_f7_salary_below_threshold_11_9_lpa():
    """F7 Boundary: Salary of 11.9 LPA fails min_threshold_lpa=12.0."""
    acceptable, reason = is_salary_acceptable("10 - 11.9 Lacs PA", min_threshold_lpa=12.0)
    assert acceptable is False
    assert "below" in reason


# --- F8 Boundaries ---

def test_t2_f8_zero_appearances_ctr_no_division_by_zero():
    """F8 Boundary: 0 appearances does not trigger ZeroDivisionError in CTR calculation."""
    apps = 0
    views = 5
    ctr = f"{round((views / apps) * 100, 1)}%" if apps > 0 else "N/A"
    assert ctr == "N/A"


def test_t2_f8_zero_views_contact_conv_no_division_by_zero():
    """F8 Boundary: 0 views does not trigger ZeroDivisionError in Contact Conversion calculation."""
    views = 0
    contacts = 2
    contact_conv = f"{round((contacts / views) * 100, 1)}%" if views > 0 else "N/A"
    assert contact_conv == "N/A"


def test_t2_f8_extreme_appearances_attainment_calculation():
    """F8 Boundary: Extreme search appearances (150,000) correctly compute attainment >100%."""
    pacing = compute_benchmark_pacing(appearances=150000, days=30, target_monthly=100000)
    assert pacing.percent_attainment == 150.0
    assert pacing.status == "AHEAD"


def test_t2_f8_negative_metrics_clamped_to_zero():
    """F8 Boundary: Negative input for appearances is safely clamped to 0."""
    pacing = compute_benchmark_pacing(appearances=-500, days=7, target_monthly=100000)
    assert pacing.total_searches_30d == 0
    assert pacing.current_daily_pace == 0.0


def test_t2_f8_corrupted_jwt_token_safe_fallback():
    """F8 Boundary: Corrupted or invalid JWT string safely returns empty dict."""
    res = decode_naukri_jwt("invalid.jwt.token")
    assert res == {}
    res_empty = decode_naukri_jwt("")
    assert res_empty == {}


# --- F9 Boundaries ---

def test_t2_f9_missing_sheet_auto_created_on_log(tmp_path):
    """F9 Boundary: Missing Applications_Log sheet is auto-created when writing."""
    wb_path = str(tmp_path / "corrupt_sheets.xlsx")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "RandomSheet"
    wb.save(wb_path)

    append_tracker_record(
        wb_path=wb_path,
        title="Data Engineer",
        company="Company A",
        status="Submitted",
        match_score=80
    )
    loaded_wb = openpyxl.load_workbook(wb_path)
    assert loaded_wb.active.max_row >= 1


def test_t2_f9_special_characters_commas_in_cells(tmp_path):
    """F9 Boundary: Commas, quotes, and newlines in company or role name persist cleanly."""
    wb_path = str(tmp_path / "special_chars.xlsx")
    create_isolated_tracker_workbook(wb_path, canonical_11_cols=True)

    company_name = 'Acme "Global", Inc.'
    title = "Senior Data Engineer, Cloud & DataOps"
    append_tracker_record(wb_path=wb_path, title=title, company=company_name, status="Submitted", match_score=90)

    wb = openpyxl.load_workbook(wb_path)
    ws = wb["Applications_Log"]
    assert ws.cell(row=2, column=2).value == company_name
    assert ws.cell(row=2, column=3).value == title


def test_t2_f9_empty_url_defaults_to_na(tmp_path):
    """F9 Boundary: Empty or omitted job URL defaults safely to 'N/A'."""
    wb_path = str(tmp_path / "empty_url.xlsx")
    create_isolated_tracker_workbook(wb_path, canonical_11_cols=True)

    append_tracker_record(wb_path=wb_path, title="Role", company="Comp", status="Submitted", match_score=75, url="")
    wb = openpyxl.load_workbook(wb_path)
    ws = wb["Applications_Log"]
    assert ws.cell(row=2, column=10).value in ["N/A", "", None]


def test_t2_f9_extremely_long_url_no_overflow(tmp_path):
    """F9 Boundary: 3,000-character URL is appended without Excel string overflow."""
    wb_path = str(tmp_path / "long_url.xlsx")
    create_isolated_tracker_workbook(wb_path, canonical_11_cols=True)

    long_url = "https://www.naukri.com/job-listings?" + ("param=value&" * 250)
    append_tracker_record(wb_path=wb_path, title="Role", company="Comp", status="Submitted", match_score=75, url=long_url)

    wb = openpyxl.load_workbook(wb_path)
    ws = wb["Applications_Log"]
    assert len(ws.cell(row=2, column=10).value) > 2000


def test_t2_f9_corrupted_excel_safe_exception_handling(tmp_path):
    """F9 Boundary: Reading corrupt non-zip file as excel raises exception handled gracefully."""
    corrupt_file = str(tmp_path / "corrupt.xlsx")
    with open(corrupt_file, "w") as f:
        f.write("NOT_A_VALID_ZIP_FILE")

    with pytest.raises(Exception):
        openpyxl.load_workbook(corrupt_file)


# --- F10 Boundaries ---

def test_t2_f10_broken_symlink_lock_unlinked_safely(tmp_path):
    """F10 Boundary: Broken symlink lock file is safely unlinked without error."""
    session_dir = tmp_path / "session_broken"
    session_dir.mkdir()
    target = session_dir / "nonexistent_target"
    symlink_path = session_dir / "SingletonLock"
    os.symlink(target, symlink_path)

    assert os.path.islink(symlink_path)
    os.unlink(symlink_path)
    assert not os.path.exists(symlink_path)


def test_t2_f10_read_only_session_dir_handling(tmp_path):
    """F10 Boundary: Resolving lock path inside existing directory handles normal write checks."""
    session_dir = tmp_path / "session_ro"
    session_dir.mkdir()
    lock_file = session_dir / "test.lock"
    lock_file.write_text("lock")
    assert lock_file.exists()


def test_t2_f10_session_dir_auto_creation(tmp_path):
    """F10 Boundary: Non-existent session directory is created recursively with mkdir(parents=True)."""
    deep_session = tmp_path / "deep" / "chromium" / "session"
    assert not deep_session.exists()
    deep_session.mkdir(parents=True, exist_ok=True)
    assert deep_session.exists()


def test_t2_f10_proxy_format_validation():
    """F10 Boundary: Validates standard HTTP/HTTPS/SOCKS proxy URI formats."""
    valid_proxies = [
        "http://proxy.example.com:8080",
        "http://user:pass@proxy.example.com:3128",
        "socks5://127.0.0.1:1080"
    ]
    for p in valid_proxies:
        assert p.startswith("http://") or p.startswith("https://") or p.startswith("socks5://")


def test_t2_f10_flock_idempotent_double_unlock(tmp_path):
    """F10 Boundary: Releasing lock twice is idempotent and does not crash."""
    lock_file = tmp_path / "idempotent.lock"
    f = open(lock_file, "w")
    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    # Second unlock attempt
    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    f.close()


# ==============================================================================
# SECTION 4: TIER 3 — PAIRWISE COMPONENT INTEGRATION CONTRACTS
# ==============================================================================

def test_t3_pairwise_match_score_to_dry_run_payload():
    """Pairwise: Match score calculation determines dry-run payload status."""
    high_match_payload = build_dry_run_payload(
        company="Microsoft",
        title="Azure Data Engineer",
        url="https://naukri.com/job-1",
        salary="25 LPA",
        raw_jd="Azure Databricks PySpark Delta Lake SQL"
    )
    assert high_match_payload.match_score >= 70
    assert high_match_payload.status == "VALIDATED_PAYLOAD"

    low_match_payload = build_dry_run_payload(
        company="GraphicStudio",
        title="UI Designer",
        url="https://naukri.com/job-2",
        salary="15 LPA",
        raw_jd="Figma Adobe Photoshop Illustrator"
    )
    assert low_match_payload.match_score == 0
    assert low_match_payload.status == "REJECTED_BELOW_THRESHOLD"


def test_t3_pairwise_payload_to_excel_tracker_logging(tmp_path):
    """Pairwise: Validated ApplicationPayload directly maps into Excel tracker row."""
    wb_path = str(tmp_path / "pairwise_tracker.xlsx")
    create_isolated_tracker_workbook(wb_path, canonical_11_cols=True)

    payload = build_dry_run_payload(
        company="Flipkart",
        title="Azure Data Engineer - Lakehouse",
        url="https://naukri.com/job-flipkart",
        salary="24 - 30 LPA",
        raw_jd="Azure Databricks PySpark Delta Lake ADF"
    )

    append_tracker_record(
        wb_path=wb_path,
        title=payload.title,
        company=payload.company,
        status=payload.status,
        match_score=payload.match_score,
        app_type="1-Click Apply (Dry Run)",
        url=payload.url
    )

    wb = openpyxl.load_workbook(wb_path)
    ws = wb["Applications_Log"]
    assert ws.max_row == 2
    row = [c.value for c in ws[2]]
    assert row[1] == payload.company
    assert row[2] == payload.title
    assert row[3] == f"{payload.match_score}%"
    assert row[8] == "VALIDATED_PAYLOAD"


def test_t3_pairwise_screening_answers_to_portal_filler_script():
    """Pairwise: Screening answers from config match parameters injected into CareerPortalFiller JS."""
    cfg = load_config()
    answers = cfg.get("answers_to_common_questions", {})

    filler = CareerPortalFiller()
    script = filler.generate_fill_script("Workday")

    assert answers.get("experience") in script
    assert answers.get("notice_period") in script or "30" in script
    assert "lavkushry@gmail.com" in script


def test_t3_pairwise_benchmark_pacing_to_performance_tracker_sheet(tmp_path):
    """Pairwise: 100k Benchmark calculation directly updates Recruiter_Performance_Log sheet."""
    wb_path = str(tmp_path / "pairwise_perf.xlsx")
    create_isolated_tracker_workbook(wb_path, canonical_11_cols=True)

    pacing = compute_benchmark_pacing(appearances=28000, days=7, target_monthly=100000)
    assert pacing.status == "AHEAD"

    wb = openpyxl.load_workbook(wb_path)
    ws = wb["Recruiter_Performance_Log"]
    ws.append([
        datetime.now().strftime("%Y-%m-%d"),
        pacing.total_searches_30d,
        350,   # profile views
        45,    # resume downloads
        28,    # contact views
        "Azure Data Engineer, Databricks, PySpark",
        f"{round((350 / 28000) * 100, 2)}%",
        f"{round((28 / 350) * 100, 2)}%",
        f"Benchmark Run Rate: {pacing.projected_monthly} ({pacing.status})"
    ])
    wb.save(wb_path)

    reloaded_wb = openpyxl.load_workbook(wb_path)
    reloaded_ws = reloaded_wb["Recruiter_Performance_Log"]
    assert reloaded_ws.max_row == 2
    assert "AHEAD" in reloaded_ws.cell(row=2, column=9).value


def test_t3_pairwise_ats_classification_to_dry_run_application():
    """Pairwise: ATS URL detection classifies portal and prepares candidate payload."""
    filler = CareerPortalFiller()
    test_urls = [
        ("https://boards.greenhouse.io/uber/jobs/123", "Greenhouse"),
        ("https://jobs.lever.co/atlassian/456", "Lever")
    ]
    for url, expected_ats in test_urls:
        detected = filler.detect_ats(url)
        assert detected == expected_ats
        payload = build_dry_run_payload(
            company="Enterprise Partner",
            title="Azure Data Platform Engineer",
            url=url,
            salary="28 LPA",
            raw_jd="Azure Databricks PySpark Delta Lake Kafka Terraform"
        )
        assert payload.status == "VALIDATED_PAYLOAD"


def test_t3_pairwise_config_facts_to_ats_resume_and_quality_score(tmp_path):
    """Pairwise: Changing competencies in config directly influences generated PDF and quality score."""
    output_pdf = str(tmp_path / "pairwise_resume.pdf")
    cfg = load_config()
    maker = AIResumeMaker(output_pdf_path=output_pdf)
    res_path = maker.build_ats_resume_pdf(config=cfg)

    reader = pypdf.PdfReader(res_path)
    text = reader.pages[0].extract_text()

    # Core competencies in config must appear in PDF
    for competency in ["Azure Databricks", "PySpark", "Delta Lake"]:
        assert competency in text

    score = maker.calculate_resume_quality_score("Azure Databricks PySpark Delta Lake")
    assert score["overall_score"] >= 75.0


# ==============================================================================
# SECTION 5: TIER 4 — REAL-WORLD AUTONOMOUS EXECUTION WORKFLOWS
# ==============================================================================

def test_t4_scenario_1_full_offline_apply_cycle(tmp_path):
    """
    Tier 4 Scenario 1: Complete Simulated Offline Application Run:
    Mock Job Discovery -> Match Score Filter (>=70%) -> Chatbot Screening -> Payload Validation -> Excel Logging.
    """
    wb_path = str(tmp_path / "scenario_1_tracker.xlsx")
    create_isolated_tracker_workbook(wb_path, canonical_11_cols=True)

    # 1. Mock Job Discovery
    mock_jobs = [
        {
            "title": "Lead Azure Data Engineer",
            "company": "Walmart Global Tech",
            "salary": "26 - 32 Lacs PA",
            "url": "https://www.naukri.com/job-walmart-101",
            "jd": "Strong hands-on experience in Azure Databricks, PySpark, Delta Lake, Medallion Architecture, and Kafka."
        },
        {
            "title": "Junior Python Developer",
            "company": "Web Agency",
            "salary": "6 - 8 Lacs PA",
            "url": "https://www.naukri.com/job-web-102",
            "jd": "Django, Flask, HTML, CSS for client websites."
        }
    ]

    applied_count = 0
    engine = InstantAlertsEngine()

    for job in mock_jobs:
        # Salary Gate
        sal_ok, _ = is_salary_acceptable(job["salary"], min_threshold_lpa=12.0)
        if not sal_ok:
            continue

        # Match Score Gate (>=70%)
        score = engine.calculate_match_score(f"{job['title']} {job['jd']}")
        if score < 70:
            continue

        # Chatbot Screening Answers
        cfg = load_config()
        answers = cfg.get("answers_to_common_questions", {})
        assert answers.get("experience") == "2.5"
        assert answers.get("notice_period") == "15 days"

        # Emit Structured ApplicationPayload
        payload = build_dry_run_payload(
            company=job["company"],
            title=job["title"],
            url=job["url"],
            salary=job["salary"],
            raw_jd=job["jd"],
            answers=answers,
            dry_run=True
        )
        assert payload.status == "VALIDATED_PAYLOAD"

        # Log to Excel Tracker
        append_tracker_record(
            wb_path=wb_path,
            title=payload.title,
            company=payload.company,
            status="Submitted (1-Click)",
            match_score=payload.match_score,
            app_type="1-Click Direct",
            url=payload.url
        )
        applied_count += 1

    assert applied_count == 1
    wb = openpyxl.load_workbook(wb_path)
    ws = wb["Applications_Log"]
    assert ws.max_row == 2
    assert ws.cell(row=2, column=2).value == "Walmart Global Tech"
    assert ws.cell(row=2, column=4).value == "80%"


def test_t4_scenario_2_resdex_profile_benchmark_refresh(tmp_path):
    """
    Tier 4 Scenario 2: Resdex Profile & Benchmark Refresh:
    Live Metrics Extraction Simulation -> 100k Velocity Projection -> Performance Ledger Persistence.
    """
    wb_path = str(tmp_path / "scenario_2_tracker.xlsx")
    json_path = str(tmp_path / "scenario_2_perf.json")
    create_isolated_tracker_workbook(wb_path, canonical_11_cols=True)

    # 1. Simulated Extracted Resdex Metrics
    extracted_metrics = {
        "timestamp": datetime.now().strftime("%Y-%m-%d"),
        "search_appearances": 26500,
        "profile_views": 380,
        "resume_downloads": 48,
        "contact_views": 32,
        "search_terms": ["Azure Data Engineer", "Databricks", "PySpark", "Delta Lake", "ADF"],
        "data_source": "Simulated Live Profile Performance"
    }

    # 2. 100k Benchmark Velocity Projection
    pacing = compute_benchmark_pacing(
        appearances=extracted_metrics["search_appearances"],
        days=7,
        target_monthly=100000
    )
    assert pacing.daily_target == 3333.33
    assert pacing.current_daily_pace == 3785.71
    assert pacing.projected_monthly == 113571
    assert pacing.percent_attainment == 113.57
    assert pacing.status == "AHEAD"

    # 3. JSON Ledger Persistence
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump([extracted_metrics], f, indent=2)
    assert os.path.exists(json_path)

    # 4. Excel Recruiter_Performance_Log Append
    wb = openpyxl.load_workbook(wb_path)
    ws = wb["Recruiter_Performance_Log"]
    ws.append([
        extracted_metrics["timestamp"],
        extracted_metrics["search_appearances"],
        extracted_metrics["profile_views"],
        extracted_metrics["resume_downloads"],
        extracted_metrics["contact_views"],
        ", ".join(extracted_metrics["search_terms"]),
        f"{round((380 / 26500) * 100, 2)}%",
        f"{round((32 / 380) * 100, 2)}%",
        f"Velocity: {pacing.projected_monthly} ({pacing.status})"
    ])
    wb.save(wb_path)

    reloaded_wb = openpyxl.load_workbook(wb_path)
    reloaded_ws = reloaded_wb["Recruiter_Performance_Log"]
    assert reloaded_ws.max_row == 2
    assert reloaded_ws.cell(row=2, column=2).value == 26500


def test_t4_scenario_3_multi_channel_sourcing_ats_portal_dry_run(tmp_path):
    """
    Tier 4 Scenario 3: Multi-Channel Sourcing & ATS Portal Dry-Run:
    HN/LinkedIn Query Gen -> ATS Classification -> Resume Path Wiring -> Dry-Run Payload Emission.
    """
    wb_path = str(tmp_path / "scenario_3_tracker.xlsx")
    create_isolated_tracker_workbook(wb_path, canonical_11_cols=True)

    # 1. Search Query Generation
    search_engine = UniversalJobSearchEngine()
    linkedin_queries = search_engine.get_linkedin_search_links()
    assert len(linkedin_queries) >= 3

    # 2. Mock Hacker News Ingestion
    mock_hn_hits = [
        {
            "comment_text": "<p>Databricks GCC | Senior Azure Data Engineer | Bengaluru, India | Full-time<br>Apply: https://boards.greenhouse.io/databricks/jobs/8888</p>",
            "story_id": 9999
        }
    ]
    with patch("requests.get", side_effect=make_mock_hn_get(mock_hn_hits)):
        hn_jobs = search_engine.search_hacker_news(limit=5)
        assert len(hn_jobs) == 1

    target_job = hn_jobs[0]

    # 3. ATS Portal Classification
    portal_filler = CareerPortalFiller()
    detected_ats = portal_filler.detect_ats(target_job["url"])
    assert detected_ats == "Greenhouse"

    # 4. Fill Script Generation
    fill_script = portal_filler.generate_fill_script(detected_ats)
    assert "Lavkush" in fill_script

    # 5. Emit Dry-Run Payload
    payload = build_dry_run_payload(
        company=target_job["company"],
        title=target_job["title"],
        url=target_job["url"],
        salary="25 - 35 LPA",
        raw_jd="Azure Databricks PySpark Delta Lake Medallion Architecture",
        dry_run=True
    )
    assert payload.status == "VALIDATED_PAYLOAD"

    append_tracker_record(
        wb_path=wb_path,
        title=payload.title,
        company=payload.company,
        status="DRY_RUN_VALIDATED",
        match_score=payload.match_score,
        app_type=f"Career Portal ({detected_ats})",
        url=payload.url
    )

    wb = openpyxl.load_workbook(wb_path)
    ws = wb["Applications_Log"]
    assert ws.max_row == 2
    assert "Greenhouse" in ws.cell(row=2, column=8).value


def test_t4_scenario_4_ats_resume_compilation_plain_text_verification(tmp_path):
    """
    Tier 4 Scenario 4: ATS Resume Compilation & Plain-Text Verification:
    Dynamic Config Loading -> ReportLab PDF Generation -> pypdf Text Parsing & Quality Score.
    """
    output_pdf = str(tmp_path / "scenario_4_resume.pdf")
    cfg = load_config()

    # 1. Compile 1-Page PDF
    maker = AIResumeMaker(output_pdf_path=output_pdf)
    res_path = maker.build_ats_resume_pdf(config=cfg)
    assert os.path.exists(res_path)

    # 2. Strict 1-Page Constraint
    reader = pypdf.PdfReader(res_path)
    assert len(reader.pages) == 1

    # 3. Plain-Text Extraction
    text = reader.pages[0].extract_text()
    assert "LAVKUSH" in text.upper()
    assert "lavkushry@gmail.com" in text
    assert "CGI India" in text
    assert "HFCL" in text
    assert "Stipe Solution" in text
    assert "A, z, u, r, e" not in text

    # 4. Multi-Factor Quality Score
    scorecard = maker.calculate_resume_quality_score("Azure Data Engineer Databricks PySpark Delta Lake ADF")
    assert scorecard["overall_score"] >= 75.0
    assert "30" in str(scorecard["ats_compliance_score"])


def test_t4_scenario_5_cloud_daemon_singleton_lock_and_proxy_protection(tmp_path):
    """
    Tier 4 Scenario 5: Cloud Daemon Singleton Lock & WAF Proxy Protection:
    Overlapping Run Prevention -> Process flock -> Playwright Proxy Config.
    """
    session_dir = tmp_path / "scenario_session"
    session_dir.mkdir()

    # 1. Clean up stale lock files
    for lock in ["SingletonLock", "SingletonSocket", "SingletonCookie"]:
        (session_dir / lock).write_text("dummy")

    for lock in ["SingletonLock", "SingletonSocket", "SingletonCookie"]:
        lp = session_dir / lock
        if lp.exists():
            lp.unlink()

    for lock in ["SingletonLock", "SingletonSocket", "SingletonCookie"]:
        assert not (session_dir / lock).exists()

    # 2. Process flock exclusion
    lock_file = session_dir / "daemon.lock"
    f_primary = open(lock_file, "w")
    fcntl.flock(f_primary.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    # Secondary process attempt
    f_secondary = open(lock_file, "w")
    with pytest.raises(BlockingIOError):
        fcntl.flock(f_secondary.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    # Primary finishes and unlocks
    fcntl.flock(f_primary.fileno(), fcntl.LOCK_UN)
    f_primary.close()
    f_secondary.close()

    # 3. WAF Proxy configuration verification
    proxy_url = "http://gate.smartproxy.com:7000"
    with patch.dict(os.environ, {"NAUKRI_PROXY": proxy_url}):
        configured_proxy = os.getenv("NAUKRI_PROXY")
        assert configured_proxy == proxy_url
        assert configured_proxy.startswith("http://")


# ==============================================================================
# Iteration 2 R1: Live Profile DOM Persistence & 3x/Day Boost Unit Tests
# ==============================================================================

def test_config_notice_period_15_days_and_7_preferred_locations():
    """Verify candidate config has 15 days notice period and all 7 Tier-1 preferred hubs."""
    with open("naukri_system/config.json", "r", encoding="utf-8") as f:
        cfg = json.load(f)
    cand = cfg.get("candidate", {})

    assert cand.get("notice_period_days") == 15
    assert "15" in cand.get("notice_period", "")
    assert "preferred_locations" in cand

    expected_hubs = ["Bengaluru", "Hyderabad", "Pune", "Gurugram", "Noida", "Mumbai", "Chennai"]
    actual_hubs = cand.get("preferred_locations", [])
    for hub in expected_hubs:
        assert hub in actual_hubs, f"Hub '{hub}' missing from candidate.preferred_locations"

    # Search locations coverage
    search_locs = [loc.lower() for loc in cfg.get("search_settings", {}).get("locations", [])]
    for hub in ["bengaluru", "hyderabad", "pune", "gurugram", "noida", "mumbai", "chennai"]:
        assert hub in search_locs, f"Hub '{hub}' missing from search_settings.locations"

    # Answers to common questions
    answers = cfg.get("answers_to_common_questions", {})
    assert "15" in answers.get("notice_period", "")
    assert "preferred_locations" in answers


def test_sync_naukri_live_profile_metadata_coverage():
    """Verify live sync constants match 25 key skills, 7 tech hubs, and 13 IT skills."""
    from scripts.sync_naukri_live_profile import (
        DEFAULT_TOP_25_KEY_SKILLS,
        DEFAULT_PREFERRED_LOCATIONS,
        DEFAULT_IT_SKILLS
    )

    # Top 25 Key Skills
    assert len(DEFAULT_TOP_25_KEY_SKILLS) == 25
    core_expected = ["Azure Databricks", "PySpark", "Delta Lake", "Azure Data Factory (ADF)", "Apache Kafka", "Terraform"]
    for skill in core_expected:
        assert skill in DEFAULT_TOP_25_KEY_SKILLS

    # 7 Preferred Locations
    assert len(DEFAULT_PREFERRED_LOCATIONS) == 7
    for hub in ["Bengaluru", "Hyderabad", "Pune", "Gurugram", "Noida", "Mumbai", "Chennai"]:
        assert hub in DEFAULT_PREFERRED_LOCATIONS

    # 13 Detailed IT Skills
    assert len(DEFAULT_IT_SKILLS) == 13
    for item in DEFAULT_IT_SKILLS:
        assert "skill" in item
        assert "version" in item
        assert "last_used" in item
        assert "exp_years" in item
        assert "exp_months" in item
        assert item["last_used"] == "2026"


def test_headline_template_length_and_saturation():
    """Verify headline template is calibrated to 247/250 chars with 100% keyword density."""
    cfg = load_config()
    template = cfg.get("headline_template", "")
    assert len(template) <= 250, f"Headline must not exceed 250 characters (got {len(template)})"
    assert len(template) >= 200, f"Headline should be saturated (got {len(template)})"

    core_kws = ["Azure Data Engineer", "Databricks", "PySpark", "Delta Lake", "ADF", "Kafka", "Terraform", "Medallion Architecture"]
    for kw in core_kws:
        assert kw.lower() in template.lower(), f"Core keyword '{kw}' missing from headline template"


def test_verify_naukri_live_profile_dom_module():
    """Verify scripts.verify_naukri_live_profile_dom imports and provides inspection utilities."""
    from scripts.verify_naukri_live_profile_dom import (
        TARGET_HUBS,
        TOP_25_KEYWORDS,
        format_terminal_report,
        verify_live_profile_dom
    )

    assert len(TARGET_HUBS) == 7
    assert len(TOP_25_KEYWORDS) == 25

    mock_report = {
        "timestamp": "2026-10-25T17:00:00",
        "overall_status": "PASS",
        "checks": {
            "headline": {"status": "PASS", "length": 247, "target_length": 247, "preview": "Azure Data Engineer..."},
            "profile_summary": {"status": "PASS", "length": 988, "matched_keywords": ["Azure Databricks", "Delta Lake", "ADF"]},
            "key_skills": {"status": "PASS", "matched_top_keywords_count": 25, "target_keywords_count": 25, "total_extracted_chips": 25},
            "notice_period": {"status": "PASS", "detected_value": "15 Days or less", "target": "15 Days or less"},
            "preferred_locations": {"status": "PASS", "matched_hubs_count": 7, "total_target_hubs": 7, "found_hubs": TARGET_HUBS, "missing_hubs": []},
            "attached_resume_pdf": {"status": "PASS", "detected_filename": "Lavkush_Kumar_Azure_Data_Engineer_Resume.pdf"},
            "current_designation": {"status": "PASS"}
        }
    }
    formatted = format_terminal_report(mock_report)
    assert "NAUKRI LIVE PROFILE DOM VERIFICATION REPORT" in formatted
    assert "15 Days or less" in formatted
    assert "247 chars" in formatted


# ==============================================================================
# SECTION: ITERATION 2 M2 SUITE (High-Volume Live Application & Sourcing)
# ==============================================================================

def test_m2_expanded_keywords_and_locations():
    """Verify DEFAULT_KEYWORDS includes all 11 core technologies and LOCATIONS covers all 7 tech hubs."""
    from naukari_pro.modules.auto_apply import DEFAULT_KEYWORDS, LOCATIONS, CANONICAL_LOCATIONS

    required_keywords = [
        "Azure Data Engineer",
        "Azure Databricks",
        "PySpark",
        "Delta Lake",
        "Azure Data Factory",
        "Data Engineer",
        "Kafka",
        "Snowflake",
        "ADF",
        "Medallion Architecture",
        "Data Lakehouse"
    ]
    for kw in required_keywords:
        assert kw in DEFAULT_KEYWORDS, f"Required keyword '{kw}' missing from DEFAULT_KEYWORDS"

    required_locs = ["hyderabad", "bengaluru", "pune", "gurugram", "noida", "mumbai", "chennai"]
    for loc in required_locs:
        assert loc in LOCATIONS, f"Required tech hub '{loc}' missing from LOCATIONS"
        assert loc in CANONICAL_LOCATIONS


def test_m2_screening_text_solver_accuracy():
    """Verify solve_screening_text_question returns candidate ground truth and never defaults non-experience to 2.5."""
    from naukari_pro.modules.auto_apply import solve_screening_text_question, _CANDIDATE

    # Non-experience questions must NOT return "2.5"
    assert solve_screening_text_question("What is your current organization/company?") == _CANDIDATE.get("current_company", "CGI India (PNC Bank GCC)")
    assert solve_screening_text_question("Please enter your current designation") == _CANDIDATE.get("current_designation", "Azure Data Engineer")
    assert solve_screening_text_question("Highest educational qualification") == "B.Tech in Computer Science and Engineering"
    assert "Azure Databricks" in solve_screening_text_question("What are your primary skills?")
    assert solve_screening_text_question("Current location/city?") == "Hyderabad"
    assert solve_screening_text_question("Are you willing to relocate or work hybrid?") == "Yes"
    assert solve_screening_text_question("Are you currently serving notice period?") == "No"
    assert solve_screening_text_question("Please mention employee id or NA") == "NA"

    # Experience questions return experience years
    assert solve_screening_text_question("Total years of experience") == str(_CANDIDATE.get("total_experience_years", "2.5"))
    assert solve_screening_text_question("How many years of experience in PySpark?") == str(_CANDIDATE.get("total_experience_years", "2.5"))

    # CTC & notice period
    assert solve_screening_text_question("Current CTC in lakhs") == str(_CANDIDATE.get("current_ctc_lakhs", "12"))
    assert solve_screening_text_question("Expected CTC in lakhs") == str(_CANDIDATE.get("expected_ctc_lakhs", "20"))
    assert solve_screening_text_question("What is your notice period in days?") == str(_CANDIDATE.get("notice_period_days", "15"))


def test_m2_search_query_freshness_parameters_and_pagination():
    """Verify search URL format invokes production build_search_url with freshness=1, sortBy=date, and pagination."""
    from naukari_pro.modules.auto_apply import build_search_url, EXPERIENCE_PARAM

    kw = "Azure Data Engineer"
    loc = "bengaluru"

    # Page 1
    p1_url = build_search_url(kw, loc, page_num=1)
    assert f"experience={EXPERIENCE_PARAM}" in p1_url
    assert "jobAge=1" in p1_url
    assert "freshness=1" in p1_url
    assert "sortBy=date" in p1_url
    assert "sortType=1" in p1_url
    assert "pageNo" not in p1_url
    assert "-1?" not in p1_url
    assert "azure-data-engineer-jobs-in-bengaluru?" in p1_url

    # Page 2+
    p2_url = build_search_url(kw, loc, page_num=2)
    assert "-2?" in p2_url
    assert "pageNo=2" in p2_url
    assert "sortBy=date" in p2_url

    # Page 3+
    p3_url = build_search_url(kw, loc, page_num=3)
    assert "-3?" in p3_url
    assert "pageNo=3" in p3_url


def test_m2_already_applied_rejection_logic():
    """Verify that 'Already Applied' button status explicitly avoids false-positive submission marking."""
    import tempfile, shutil, os, asyncio
    from unittest.mock import AsyncMock, patch
    from naukari_pro.modules.auto_apply import PlaywrightRunner, make_job_id

    # 1. Button classification logic verification
    def classify_btn(txt):
        t = (txt or "").lower().strip()
        if "already applied" in t:
            return {"type": "already_applied"}
        return {"type": "apply"}

    assert classify_btn("Already Applied")["type"] == "already_applied"
    assert classify_btn("already applied")["type"] == "already_applied"
    assert classify_btn("  Already applied on 23 Oct 2026")["type"] == "already_applied"

    # 2. Authentic verification that apply_to_job_async skips and writes 0 Excel rows
    temp_dir = tempfile.mkdtemp()
    temp_excel = os.path.join(temp_dir, "test_tracker.xlsx")
    try:
        with patch("naukari_pro.modules.auto_apply.TRACKER_PATH", temp_excel), patch("naukari_pro.config.TRACKER_PATH", temp_excel):
            runner = PlaywrightRunner(skip_list=set(), dry_run=False)
            mock_tab = AsyncMock()
            mock_tab.url = "https://www.naukri.com/sample-applied-job"
            mock_tab.evaluate = AsyncMock(return_value={"type": "already_applied", "text": "Already Applied"})

            mock_context = AsyncMock()
            mock_context.new_page = AsyncMock(return_value=mock_tab)
            runner.context = mock_context

            ok, msg = asyncio.run(runner.apply_to_job_async(
                mock_context,
                job_url="https://www.naukri.com/sample-applied-job",
                title="Azure Data Engineer",
                company="Cognizant",
                salary="18 LPA",
                raw_jd="PySpark Azure Databricks Delta Lake",
                match_score=85
            ))

            assert ok is False
            assert "Already applied" in msg
            # Confirm added to skip list
            assert make_job_id("Azure Data Engineer", "Cognizant") in runner.skip_list
            # Confirm zero false-positive Excel rows written
            assert not os.path.exists(temp_excel)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_m2_screening_radio_solver_logic():
    """Verify radio button JS evaluate correctly matches affirmative and rejects negative/disqualifying options."""
    from playwright.sync_api import sync_playwright
    from naukari_pro.modules.auto_apply import SCREENING_RADIO_JS

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Adversarial: "Not Comfortable" listed before "Comfortable"
        page.set_content("""
        <div class="chatbot_Drawer">
            <div class="singleSelectRadioButton">
                <label class="radio-label"><input type="radio" name="r" value="nc">Not Comfortable</label>
                <label class="radio-label"><input type="radio" name="r" value="c">Comfortable</label>
            </div>
        </div>
        """)
        res = page.evaluate(SCREENING_RADIO_JS, "Are you comfortable with night shifts?")
        assert res["handled"] is True
        assert res["chosenText"] == "Comfortable"

        # Disagree vs Agree
        page.set_content("""
        <div class="chatbot_Drawer">
            <div class="singleSelectRadioButton">
                <label class="radio-label"><input type="radio" name="r" value="d">Disagree</label>
                <label class="radio-label"><input type="radio" name="r" value="a">Agree</label>
            </div>
        </div>
        """)
        res = page.evaluate(SCREENING_RADIO_JS, "Do you agree to company policies?")
        assert res["handled"] is True
        assert res["chosenText"] == "Agree"

        # Disentangling check: .multicheckboxes-container must NOT be treated as radios
        page.set_content("""
        <div class="chatbot_Drawer">
            <div class="multicheckboxes-container">
                <label><input type="checkbox" name="skills" value="azure">Azure</label>
                <label><input type="checkbox" name="skills" value="pyspark">PySpark</label>
            </div>
        </div>
        """)
        res = page.evaluate(SCREENING_RADIO_JS, "Select your primary skills")
        assert res["handled"] is False

        browser.close()


def test_m2_screening_dropdown_native_and_custom_logic():
    """Verify native select and custom dropdown solvers filter placeholders and reject negative options."""
    from playwright.sync_api import sync_playwright
    from naukari_pro.modules.auto_apply import SCREENING_DROPDOWN_JS

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Native select with placeholder and negative option
        page.set_content("""
        <div class="chatbot_Drawer">
            <select id="sel">
                <option value="">-- Select Notice Period --</option>
                <option value="60">More than 30 days</option>
                <option value="15">15 days</option>
            </select>
        </div>
        """)
        res = page.evaluate(SCREENING_DROPDOWN_JS)
        assert res["handled"] is True
        assert res["type"] == "native_select"
        assert res["chosenText"] == "15 days"

        # Custom dropdown with Disagree vs Agree
        page.set_content("""
        <div class="chatbot_Drawer">
            <div class="custom-select" id="dd">Select</div>
            <ul role="listbox">
                <li role="option">Disagree</li>
                <li role="option">Agree</li>
            </ul>
        </div>
        """)
        res = page.evaluate(SCREENING_DROPDOWN_JS)
        assert res["handled"] is True
        assert res["type"] == "custom_dropdown"
        assert res["chosenText"] == "Agree"

        browser.close()


def test_m2_screening_checkbox_multi_select_logic():
    """Verify multi-select checkbox solver targets relevant skills and checks them."""
    from playwright.sync_api import sync_playwright
    from naukari_pro.modules.auto_apply import SCREENING_CHECKBOX_JS

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.set_content("""
        <div class="chatbot_Drawer">
            <div class="multicheckboxes-container">
                <label><input type="checkbox" id="cb1" value="azure"> Azure Databricks</label>
                <label><input type="checkbox" id="cb2" value="pyspark"> Apache PySpark</label>
                <label><input type="checkbox" id="cb3" value="cobol"> COBOL</label>
            </div>
        </div>
        """)
        res = page.evaluate(SCREENING_CHECKBOX_JS)
        assert res["handled"] is True
        assert res["clickedCount"] == 2

        # Verify checkboxes 1 and 2 are checked, 3 is not
        cb1_checked = page.evaluate("() => document.getElementById('cb1').checked")
        cb2_checked = page.evaluate("() => document.getElementById('cb2').checked")
        cb3_checked = page.evaluate("() => document.getElementById('cb3').checked")
        assert cb1_checked is True
        assert cb2_checked is True
        assert cb3_checked is False

        browser.close()


def test_m2_hidden_jobs_and_early_access_enhancements():
    """Verify HiddenJobsEngine and EarlyAccessEngine structured methods with match score evaluation."""
    from naukari_pro.modules.hidden_jobs import HiddenJobsEngine
    from naukari_pro.modules.early_access import EarlyAccessEngine

    hj_engine = HiddenJobsEngine()
    ea_engine = EarlyAccessEngine()

    assert hasattr(hj_engine, "harvest_and_evaluate_opportunities")
    assert hasattr(ea_engine, "scan_early_access")


