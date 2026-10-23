"""
Adversarial Stress Test Suite for Milestone 1 (SEO & Profile Ranking Optimization)
Authored by Challenger 1 (teamwork_preview_challenger_m1_1)
Validates boundary conditions, text extractability, keyword coverage, and mutation robustness.
"""

import json
import os
import re
import subprocess
import pypdf
import pytest

from naukari_pro.config import load_config
from naukari_pro.modules.resume_maker import AIResumeMaker
from naukari_pro.modules.profile_enhancer import ProfileEnhancerEngine


# ==============================================================================
# CHALLENGE 1: Profile Summary & Headline Boundary Limits
# ==============================================================================

def test_naukri_update_guide_headline_character_limit():
    """Verify headline in NAUKRI update guide stays strictly <= 250 characters."""
    guide_path = "NAUKRI_PROFILE_COMPLETE_UPDATE_DATA_ENGINEER.md"
    assert os.path.exists(guide_path)
    with open(guide_path, "r", encoding="utf-8") as f:
        content = f.read()

    m = re.search(r'## 2\. RESUME HEADLINE.*?\`\`\`text\n(.*?)\n\`\`\`', content, re.DOTALL)
    assert m is not None, "Headline block not found in update guide"
    headline = m.group(1).strip()
    assert len(headline) <= 250, f"Headline is {len(headline)} chars (max 250 allowed)"


def test_naukri_update_guide_summary_character_limit():
    """
    CRITICAL CHALLENGE: Verify profile summary in NAUKRI update guide stays strictly <= 1,000 characters.
    Naukri Resdex profile summary enforces a hard 1,000 character limit.
    """
    guide_path = "NAUKRI_PROFILE_COMPLETE_UPDATE_DATA_ENGINEER.md"
    with open(guide_path, "r", encoding="utf-8") as f:
        content = f.read()

    m = re.search(r'## 4\. PROFILE SUMMARY.*?\`\`\`text\n(.*?)\n\`\`\`', content, re.DOTALL)
    assert m is not None, "Summary block not found in update guide"
    summary = m.group(1).strip()
    # This will expose Bug 1 if summary > 1000 chars
    assert len(summary) <= 1000, f"Summary is {len(summary)} chars, exceeding Naukri's 1,000 char limit by {len(summary) - 1000} chars!"


# ==============================================================================
# CHALLENGE 2: PDF Text Extraction & Kerning Artifacts
# ==============================================================================

def test_reportlab_pdf_clean_text_extraction_and_no_kerning_splits():
    """Verify ReportLab PDF extracts text cleanly without letter-split kerning artifacts."""
    maker = AIResumeMaker()
    pdf_path = maker.build_ats_resume_pdf()
    assert os.path.exists(pdf_path)

    reader = pypdf.PdfReader(pdf_path)
    assert len(reader.pages) == 1, "ReportLab PDF must be strictly 1 page"

    text = reader.pages[0].extract_text()
    forbidden_splits = [
        "SUMMAR Y", "F actory", "T erraform", "EDUCA TION", "CER TIFICA TIONS",
        "B.T ech", "A, z, u, r, e", "D, a, t, a"
    ]
    for split in forbidden_splits:
        assert split not in text, f"Found kerning split artifact '{split}' in ReportLab PDF"


def test_latex_pdf_clean_text_extraction_and_no_kerning_splits(tmp_path):
    """
    CRITICAL CHALLENGE: Verify LaTeX PDF compiled with Tectonic extracts text cleanly without kerning splits.
    Specifically checks for 'B.T ech' degree split artifact.
    """
    tex_path = "Azure_Data_Engineer_Resume.tex"
    assert os.path.exists(tex_path)

    out_dir = str(tmp_path)
    cmd = ["/opt/homebrew/bin/tectonic", "-o", out_dir, tex_path]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"Tectonic compilation failed: {res.stderr}"

    compiled_pdf = os.path.join(out_dir, "Azure_Data_Engineer_Resume.pdf")
    reader = pypdf.PdfReader(compiled_pdf)
    assert len(reader.pages) == 1, "LaTeX PDF must be strictly 1 page"

    text = reader.pages[0].extract_text()
    forbidden_splits = [
        "SUMMAR Y", "F actory", "T erraform", "EDUCA TION", "CER TIFICA TIONS",
        "B.T ech", "A, z, u, r, e"
    ]
    for split in forbidden_splits:
        assert split not in text, f"Found kerning split artifact '{split}' in LaTeX PDF"


# ==============================================================================
# CHALLENGE 3: 17 Bullets 5-Stage Formula & Mutation Resilience
# ==============================================================================

def test_all_17_bullets_pass_formula_and_reject_mutations():
    """Verify all 17 bullets in config.json satisfy the 5-stage formula and reject mutations."""
    with open("naukri_system/config.json", "r", encoding="utf-8") as f:
        cfg = json.load(f)

    exp_bullets = [b for e in cfg.get("experience", []) for b in e.get("bullets", [])]
    proj_bullets = [b for p in cfg.get("projects", []) for b in p.get("bullets", [])]
    all_bullets = exp_bullets + proj_bullets
    assert len(all_bullets) == 17, f"Expected 17 bullets, got {len(all_bullets)}"

    tier1_verbs = {"Architected", "Spearheaded", "Orchestrated", "Pioneered", "Scaled", "Transformed"}
    tier2_verbs = {
        "Engineered", "Automated", "Shipped", "Deployed", "Refactored", "Optimized",
        "Slashed", "Containerized", "Instrumented", "Provisioned", "Built",
        "Integrated", "Configured", "Standardized", "Hardened"
    }
    allowed_verbs = tier1_verbs | tier2_verbs
    forbidden_verbs = ["helped", "worked on", "responsible for", "assisted", "handled", "participated in", "used"]
    metric_regex = re.compile(
        r'\d+(?:\.\d+)?\s*(?:[kmgtb]\+?|%)|\$\d+|\d+\s*(?:ms|min|sec|hours?|h|x|gb|tb|lpa|nodes?|microservices|events?|roles?|days?|environments?|users?|screens?|datasets?)',
        re.IGNORECASE
    )

    def validate(b):
        first_word = b.split()[0].rstrip(",.:")
        if first_word not in allowed_verbs:
            return False
        if any(re.search(r'\b' + re.escape(fv) + r'\b', b, re.IGNORECASE) for fv in forbidden_verbs):
            return False
        if not metric_regex.search(b):
            return False
        return True

    for b in all_bullets:
        assert validate(b), f"Bullet failed validation: {b}"

    # Mutation test: Inject forbidden verbs
    for b in all_bullets:
        for fv in forbidden_verbs:
            mutated_start = fv.capitalize() + " " + " ".join(b.split()[1:])
            assert not validate(mutated_start), f"Validation failed to reject mutation: {mutated_start}"

            words = b.split()
            insert_pos = len(words) // 2
            mutated_mid = " ".join(words[:insert_pos] + [fv] + words[insert_pos:])
            assert not validate(mutated_mid), f"Validation failed to reject mid mutation: {mutated_mid}"

    # Mutation test: Strip metrics
    for b in all_bullets:
        mutated_no_digits = re.sub(r'\d+', 'several', b).replace('%', 'percent').replace('$', 'USD ')
        assert not validate(mutated_no_digits), f"Validation failed to reject stripped metrics: {mutated_no_digits}"


# ==============================================================================
# CHALLENGE 4: Top 25 Keyword Saturation in config.json
# ==============================================================================

def test_top_25_keywords_saturated_in_config():
    """Verify 100% of top 25 Azure Data Engineering keywords are present in config.json."""
    with open("naukri_system/config.json", "r", encoding="utf-8") as f:
        cfg = json.load(f)

    top_25_keywords = [
        "Azure Data Factory", "Azure Databricks", "PySpark", "Delta Lake",
        "Medallion Architecture", "ADLS Gen2", "Apache Kafka", "SQL",
        "Python", "Apache Spark", "Azure Synapse Analytics", "Microsoft Fabric",
        "Terraform", "ETL", "Star Schema Data Modeling", "DataOps",
        "Docker", "Kubernetes", "Unity Catalog", "Schema Enforcement",
        "Partition Pruning", "Streaming Ingestion", "Change Data Capture",
        "dbt", "Observability"
    ]

    config_str = json.dumps(cfg).lower()
    missing = [kw for kw in top_25_keywords if kw.lower() not in config_str]
    assert len(missing) == 0, f"Missing keywords in config.json: {missing}"


# ==============================================================================
# CHALLENGE 5: AIResumeMaker Output Directory Resilience
# ==============================================================================

def test_airesumemaker_creates_nested_directories(tmp_path):
    """
    CRITICAL CHALLENGE: AIResumeMaker should automatically create nonexistent parent directories.
    Tests boundary condition when output_pdf_path has nested directories that do not exist yet.
    """
    nested_pdf = str(tmp_path / "deep" / "nested" / "dir" / "resume.pdf")
    maker = AIResumeMaker(output_pdf_path=nested_pdf)
    res_path = maker.build_ats_resume_pdf()
    assert os.path.exists(res_path), "Failed to build PDF in nested nonexistent directory"


# ==============================================================================
# CHALLENGE 6: AIResumeMaker Quality Score Return Types
# ==============================================================================

def test_resume_quality_score_types():
    """
    CRITICAL CHALLENGE: calculate_resume_quality_score sub-scores should be numeric or castable.
    Currently returns strings like '30/30' causing TypeError when compared with floats in assertions.
    """
    maker = AIResumeMaker()
    scorecard = maker.calculate_resume_quality_score("Azure Data Engineer Databricks PySpark Delta Lake Kafka")
    assert isinstance(scorecard.get("overall_score"), (int, float))

    ats_comp = scorecard.get("ats_compliance_score")
    # Exposes Bug 2: ats_compliance_score is '30/30' string instead of float
    assert isinstance(ats_comp, (int, float)), f"ats_compliance_score should be numeric, got {type(ats_comp)}: {ats_comp}"
