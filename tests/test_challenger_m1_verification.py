"""
Empirical Challenge Verification Suite: Milestone 1
Adversarial & Empirical verification of ATS compliance, section ordering, candidate integrity, and page geometry.
Created by Challenger 2 (Milestone 1).
"""

import os
import re
import subprocess
from pathlib import Path
import pypdf
import pytest

from naukari_pro.config import load_config
from naukari_pro.modules.resume_maker import AIResumeMaker

WORKSPACE_DIR = Path("/Users/lavkushkumar/Desktop/Resume")
LATEX_SOURCE = WORKSPACE_DIR / "Azure_Data_Engineer_Resume.tex"
LATEX_PDF = WORKSPACE_DIR / "Azure_Data_Engineer_Resume.pdf"
REPORTLAB_PDF = WORKSPACE_DIR / "Lavkush_Kumar_Azure_Data_Engineer_Resume.pdf"
CONFIG_FILE = WORKSPACE_DIR / "naukri_system" / "config.json"


# ==============================================================================
# TEST 1: LIVE TECTONIC COMPILATION & PAGE GEOMETRY
# ==============================================================================
def test_tectonic_compilation_and_page_geometry(tmp_path):
    """Compiles Azure_Data_Engineer_Resume.tex with tectonic and verifies geometry."""
    assert LATEX_SOURCE.exists(), f"Missing {LATEX_SOURCE}"
    out_dir = tmp_path / "build"
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = ["/opt/homebrew/bin/tectonic", "-o", str(out_dir), str(LATEX_SOURCE)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"Tectonic compilation failed: {res.stderr}"

    compiled_pdf = out_dir / "Azure_Data_Engineer_Resume.pdf"
    assert compiled_pdf.exists(), "Compiled PDF not produced"

    reader = pypdf.PdfReader(str(compiled_pdf))
    # 1-page requirement
    assert len(reader.pages) == 1, f"Expected exactly 1 page, got {len(reader.pages)}"

    # Dimensions
    page = reader.pages[0]
    box = page.mediabox
    width = float(box.width)
    height = float(box.height)
    # A4 is 595.28 x 841.89 points
    assert abs(width - 595.28) < 1.0, f"Unexpected width: {width}"
    assert abs(height - 841.89) < 1.0, f"Unexpected height: {height}"

    # Verify margin declarations in LaTeX source
    content = LATEX_SOURCE.read_text(encoding="utf-8")
    margin_match = re.search(r"\\usepackage\[.*?left=([0-9.]+)in.*?right=([0-9.]+)in.*?top=([0-9.]+)in.*?bottom=([0-9.]+)in.*?\]\{geometry\}", content)
    assert margin_match, "Geometry package margin declaration not found"
    left, right, top, bottom = [float(x) for x in margin_match.groups()]
    assert all(m >= 0.25 for m in [left, right, top, bottom]), f"Margins below 0.25in: {left}, {right}, {top}, {bottom}"


# ==============================================================================
# TEST 2: REPORTLAB RESUME COMPILATION & PAGE COUNT
# ==============================================================================
def test_reportlab_generation_and_page_count(tmp_path):
    """Builds ATS resume using AIResumeMaker and verifies page count."""
    out_pdf = str(tmp_path / "output_resume.pdf")
    maker = AIResumeMaker(output_pdf_path=out_pdf)
    res_path = maker.build_ats_resume_pdf()
    assert os.path.exists(res_path), "ReportLab PDF build failed"

    reader = pypdf.PdfReader(res_path)
    assert len(reader.pages) == 1, f"ReportLab PDF has {len(reader.pages)} pages, expected 1"


# ==============================================================================
# TEST 3: EMPIRICAL ATS TEXT EXTRACTION & SPLIT-WORD DETECTION
# ==============================================================================
def test_ats_text_extraction_and_split_artifacts():
    """Extracts text from both PDFs and verifies zero letter-splitting artifacts."""
    for pdf_path in [LATEX_PDF, REPORTLAB_PDF]:
        assert pdf_path.exists(), f"PDF missing: {pdf_path}"
        reader = pypdf.PdfReader(str(pdf_path))
        text = reader.pages[0].extract_text()
        assert len(text) > 1000, f"Text too short ({len(text)} chars) in {pdf_path.name}"

        # Common kerning split artifacts
        forbidden_splits = [
            "SUMMAR Y", "F actory", "T erraform", "EDUCA TION", "CER TIFICA TIONS",
            "A, z, u, r, e", "D a t a b r i c k s", "P y S p a r k"
        ]
        for split in forbidden_splits:
            assert split not in text, f"Found letter-split artifact '{split}' in {pdf_path.name}"


# ==============================================================================
# TEST 4: ATS CONTACT INFORMATION EXTRACTION
# ==============================================================================
def test_ats_contact_info_extraction():
    """Verifies contact metadata parseability across both PDFs."""
    for pdf_path in [LATEX_PDF, REPORTLAB_PDF]:
        reader = pypdf.PdfReader(str(pdf_path))
        text = reader.pages[0].extract_text()

        # Name
        assert "LAVKUSH KUMAR" in text.upper(), f"Name missing in {pdf_path.name}"
        # Email
        email_match = re.search(r"lavkushry@gmail\.com", text, re.IGNORECASE)
        assert email_match, f"Email missing in {pdf_path.name}"
        # Phone
        phone_match = re.search(r"(?:\+91[- ]?)?9122036484", text)
        assert phone_match, f"Phone missing in {pdf_path.name}"
        # Location
        assert "Hyderabad" in text or "Bangalore" in text, f"Location missing in {pdf_path.name}"
        # LinkedIn & GitHub
        assert "linkedin.com/in/lavkushry" in text, f"LinkedIn missing in {pdf_path.name}"
        assert "github.com/lavkushry" in text, f"GitHub missing in {pdf_path.name}"


# ==============================================================================
# TEST 5: TOP 25 AZURE DATA ENGINEERING KEYWORD SATURATION
# ==============================================================================
def test_keyword_saturation_top_25():
    """Checks presence of top 25 Azure Data Engineering keywords."""
    top_25_keywords = [
        "Azure Data Factory", "ADF", "Azure Databricks", "PySpark", "Delta Lake",
        "Medallion Architecture", "ADLS Gen2", "Apache Kafka", "SQL", "Spark SQL",
        "Python", "Apache Spark", "Azure Synapse Analytics", "Microsoft Fabric",
        "Terraform", "ETL", "ELT", "Data Modeling", "Star Schema",
        "DataOps", "CI/CD", "Docker", "Kubernetes", "Unity Catalog",
        "Change Data Capture"
    ]

    cfg = load_config()
    default_kws = cfg.get("default_keywords", [])

    # Check config.json has >= 25 keywords
    assert len(default_kws) >= 25, f"config.json only has {len(default_kws)} keywords"

    # Check LaTeX PDF coverage
    reader = pypdf.PdfReader(str(LATEX_PDF))
    text_latex = reader.pages[0].extract_text()

    matched_latex = [kw for kw in top_25_keywords if re.search(r"\b" + re.escape(kw) + r"\b", text_latex, re.IGNORECASE)]
    # At least 20 of 25 keywords should appear in 1-page resume
    assert len(matched_latex) >= 20, f"Only matched {len(matched_latex)} / 25 in LaTeX PDF: {matched_latex}"


# ==============================================================================
# TEST 6: SECTION ORDERING PER AGENTS.MD SECTION 2
# ==============================================================================
def test_section_ordering_latex():
    """
    Verifies section ordering in Azure_Data_Engineer_Resume.tex against AGENTS.md §2:
    1. HEADER
    2. PROFESSIONAL SUMMARY
    3. TECHNICAL SKILLS
    4. PROFESSIONAL EXPERIENCE
    5. KEY PROJECTS
    6. EDUCATION
    7. CERTIFICATIONS
    """
    reader = pypdf.PdfReader(str(LATEX_PDF))
    text = reader.pages[0].extract_text()

    pos_summary = text.find("PROFESSIONAL SUMMARY")
    pos_skills = text.find("TECHNICAL SKILLS")
    pos_exp = text.find("PROFESSIONAL EXPERIENCE")
    pos_proj = text.find("KEY ENGINEERING PROJECTS")
    pos_edu = text.find("EDUCATION")
    pos_cert = text.find("CERTIFICATIONS")

    assert pos_summary != -1, "PROFESSIONAL SUMMARY not found in LaTeX PDF"
    assert pos_skills != -1, "TECHNICAL SKILLS not found in LaTeX PDF"
    assert pos_exp != -1, "PROFESSIONAL EXPERIENCE not found in LaTeX PDF"
    assert pos_proj != -1, "KEY ENGINEERING PROJECTS not found in LaTeX PDF"
    assert pos_edu != -1, "EDUCATION not found in LaTeX PDF"
    assert pos_cert != -1, "CERTIFICATIONS not found in LaTeX PDF"

    # Order verification
    assert pos_summary < pos_skills < pos_exp < pos_proj < pos_edu < pos_cert, "LaTeX sections out of order!"


def test_section_ordering_reportlab():
    """
    Audits section ordering in Lavkush_Kumar_Azure_Data_Engineer_Resume.pdf.
    Verifies that PROFESSIONAL SUMMARY is present and sections follow AGENTS.md §2.
    """
    reader = pypdf.PdfReader(str(REPORTLAB_PDF))
    text = reader.pages[0].extract_text()

    pos_summary = text.find("PROFESSIONAL SUMMARY")
    pos_skills = text.find("TECHNICAL COMPETENCIES")
    pos_exp = text.find("PROFESSIONAL EXPERIENCE")
    pos_proj = text.find("KEY ENGINEERING PROJECTS")
    pos_edu = text.find("EDUCATION")
    pos_cert = text.find("CERTIFICATIONS")

    assert pos_summary != -1, "PROFESSIONAL SUMMARY missing"
    assert pos_skills != -1, "TECHNICAL COMPETENCIES missing"
    assert pos_exp != -1, "PROFESSIONAL EXPERIENCE missing"
    assert pos_proj != -1, "KEY ENGINEERING PROJECTS missing"
    assert pos_edu != -1, "EDUCATION missing"
    assert pos_cert != -1, "CERTIFICATIONS missing"

    assert pos_summary < pos_skills < pos_exp < pos_proj < pos_edu < pos_cert, "ReportLab sections out of order!"


# ==============================================================================
# TEST 7: CANDIDATE PROFILE INTEGRITY PER AGENTS.MD SECTION 9
# ==============================================================================
def test_candidate_profile_integrity_companies_and_dates():
    """
    Checks company names and dates against AGENTS.md §9:
    - CGI India (Jun 2026 – Present)
    - HFCL Limited (Aug 2025 – Jun 2026)
    - CGI India Apprentice (Sep 2024 – Aug 2025)
    - Stipe Solutions (Mar 2024 – Sep 2024)
    """
    cfg = load_config()
    exps = cfg["experience"]

    companies = [e["company"] for e in exps]
    durations = [e["duration"] for e in exps]

    assert any("CGI" in c for c in companies)
    assert any("HFCL" in c or "Himachal Futuristic" in c for c in companies)
    assert any("Stipe" in c for c in companies)

    assert any("2026" in d and ("Present" in d or "Current" in d) for d in durations)
    assert any("Aug 2025" in d and "Jun 2026" in d for d in durations)
    assert any("Sep 2024" in d and "Aug 2025" in d for d in durations)
    assert any("Mar 2024" in d and "Sep 2024" in d for d in durations)


# ==============================================================================
# TEST 8: 17 BULLETS 5-STAGE FORMULA & ZERO FORBIDDEN VERBS
# ==============================================================================
def test_17_bullets_compliance_in_config():
    """Verifies all 17 bullets in config.json conform strictly to standards."""
    cfg = load_config()
    exp_bullets = [b for e in cfg["experience"] for b in e["bullets"]]
    proj_bullets = [b for p in cfg["projects"] for b in p["bullets"]]
    all_bullets = exp_bullets + proj_bullets

    assert len(all_bullets) == 17, f"Expected 17 bullets, got {len(all_bullets)}"

    forbidden_verbs = ["helped", "worked on", "responsible for", "assisted", "handled", "participated in", "used"]
    tier_verbs = [
        "Architected", "Spearheaded", "Orchestrated", "Pioneered", "Scaled", "Transformed",
        "Engineered", "Automated", "Shipped", "Deployed", "Refactored", "Optimized",
        "Slashed", "Containerized", "Instrumented", "Provisioned", "Built", "Integrated",
        "Configured", "Standardized", "Hardened"
    ]

    metric_pattern = re.compile(
        r'\d+(?:\.\d+)?\s*(?:[kmgtb]\+?|%)|\$\d+|\d+\s*(?:ms|min|sec|hours?|h|x|gb|tb|lpa|nodes?|microservices|events?|roles?|days?|environments?|users?|screens?)',
        re.IGNORECASE
    )

    for i, b in enumerate(all_bullets):
        first_word = b.split()[0].rstrip(",.:")
        assert first_word in tier_verbs, f"Bullet {i+1} starts with non-tier verb '{first_word}': {b}"
        for fv in forbidden_verbs:
            assert fv not in b.lower(), f"Bullet {i+1} contains forbidden verb '{fv}': {b}"
        assert metric_pattern.search(b), f"Bullet {i+1} lacks quantified metric: {b}"


# ==============================================================================
# TEST 9: EMPIRICAL ATS DEGREE EXTRACTION (EXPOSES B.T ECH DEFECT)
# ==============================================================================
def test_ats_degree_extraction_kerning_defect():
    """
    Simulates ATS education parser searching for 'B.Tech' degree.
    Verifies that both LaTeX and ReportLab extract 'B.Tech' cleanly without
    kerning split artifacts ('B.T ech').
    """
    reader_latex = pypdf.PdfReader(str(LATEX_PDF))
    text_latex = reader_latex.pages[0].extract_text()

    reader_rl = pypdf.PdfReader(str(REPORTLAB_PDF))
    text_rl = reader_rl.pages[0].extract_text()

    # ReportLab correctly extracts 'B.Tech'
    assert "B.Tech" in text_rl, "ReportLab unexpectedly failed to extract 'B.Tech'"
    assert "B.T ech" not in text_rl, "ReportLab has 'B.T ech' kerning split"

    # LaTeX PDF extracts 'B.Tech' cleanly
    assert "B.Tech" in text_latex, "LaTeX PDF failed to extract clean 'B.Tech'"
    assert "B.T ech" not in text_latex, "Found kerning split artifact 'B.T ech' in LaTeX PDF"


# ==============================================================================
# TEST 10: ATS PROFESSIONAL SUMMARY EXTRACTION
# ==============================================================================
def test_ats_summary_section_presence():
    """
    Simulates ATS profile parser extracting candidate summary statement.
    Verifies that both LaTeX and ReportLab PDFs contain the PROFESSIONAL SUMMARY section.
    """
    reader_rl = pypdf.PdfReader(str(REPORTLAB_PDF))
    text_rl = reader_rl.pages[0].extract_text()

    reader_latex = pypdf.PdfReader(str(LATEX_PDF))
    text_latex = reader_latex.pages[0].extract_text()

    assert "PROFESSIONAL SUMMARY" in text_latex, "LaTeX PDF missing PROFESSIONAL SUMMARY"
    assert "PROFESSIONAL SUMMARY" in text_rl, "ReportLab PDF missing PROFESSIONAL SUMMARY"


# ==============================================================================
# TEST 11: SEPARATE EDUCATION & CERTIFICATIONS SECTIONS (AGENTS.MD §2)
# ==============================================================================
def test_separate_education_and_certifications_sections():
    """
    AGENTS.md §2 mandates distinct sections:
      6. EDUCATION (1–2 lines)
      7. CERTIFICATIONS (1 line, 2–3 max)
    Verifies that both PDFs maintain separate sections.
    """
    for pdf_path in [LATEX_PDF, REPORTLAB_PDF]:
        reader = pypdf.PdfReader(str(pdf_path))
        text = reader.pages[0].extract_text()
        assert "EDUCATION" in text, f"EDUCATION section missing in {pdf_path.name}"
        assert "CERTIFICATIONS" in text, f"CERTIFICATIONS section missing in {pdf_path.name}"
        assert "EDUCATION & CERTIFICATIONS" not in text, f"Merged section still present in {pdf_path.name}"


# ==============================================================================
# TEST 12: CANDIDATE PROFILE TITLE INTEGRITY (AGENTS.MD §9)
# ==============================================================================
def test_candidate_profile_title_audit():
    """
    Audits candidate's current role title against AGENTS.md §9.
    AGENTS.md §9 explicitly records: 'Current Role: DevOps Engineer at CGI India'.
    Checks whether current title in config.json and LaTeX maintains the verified DevOps Engineer base title.
    """
    cfg = load_config()
    current_role = cfg["experience"][0]
    title = current_role["title"]

    assert "Azure Data Engineer" in title
    has_devops = "DevOps" in title
    assert has_devops, "Title must retain DevOps Engineer to protect background check fidelity"

