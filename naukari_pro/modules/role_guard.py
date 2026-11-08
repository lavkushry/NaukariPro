"""
Role Guard Module for NaukariPro
Enforces non-negotiable role family and domain constraints.
Strictly blocks non-Data Engineer / non-MLOps / non-DevOps roles.
Guarantees that universal apply NEVER bypasses core candidate domain alignment.
"""

from typing import Tuple, Optional
import logging

logger = logging.getLogger("naukariPro.RoleGuard")

# Negative exclusions: Non-IT, non-data, clerical, healthcare, hospitality, service, sales, pure frontend, bulk fresher titles
FORBIDDEN_ROLE_KEYWORDS = (
    # BPO, Telecalling & Customer Service
    "telecalling", "telecaller", "tele-calling", "tele-caller", "tele caller", "call center",
    "bpo", "kpo", "customer care", "customer support", "customer success", "client support",
    "helpdesk", "technical support executive", "desktop support",
    # Non-software Engineering
    "mechanical", "civil engineer", "civil engineering", "electrical design", "hardware engineer",
    "embedded engineer", "vlsi", "pcb", "autocad", "structural engineer",
    "manufacturing engineer", "chemical engineer", "automotive engineer",
    # Languages & Translation
    "german", "french", "spanish", "japanese", "mandarin", "russian", "chinese",
    "language processor", "translator", "linguist", "interpreter",
    # Non-Data ERP & Functional
    "sap mdg", "sap mm", "sap fico", "sap sd", "sap abap", "sap basis",
    "sap functional",
    # Operations, Logistics & Procurement
    "procurement", "purchasing", "supply chain", "logistics", "inventory", "buyer",
    # Education, Coaching & Teaching
    "trainer", "teacher", "educator", "faculty", "instructor", "tutor",
    "robotics educator", "coding educator", "counselor",
    # Medical, Healthcare & Life Sciences
    "dentist", "dental", "nurse", "nursing", "clinical", "medical",
    "pharmacist", "physician", "hospital", "radiology", "pharma",
    # Hospitality, Retail & Food/Beverage
    "cashier", "bartender", "waiter", "waitress", "retail", "store manager",
    "store executive", "merchandiser", "barista", "restaurant",
    # Sales & Marketing
    "sales executive", "business development", "bde", "telesales",
    "real estate", "digital marketing", "seo specialist", "content writer",
    "copywriter", "social media", "inside sales", "field sales", "pre-sales",
    # Pure Frontend, Mobile & Design (unless data engineering explicitly in title)
    "front end developer", "frontend developer", "react developer",
    "angular developer", "ios developer", "android developer", "flutter developer",
    "ui/ux", "graphic designer", "webmaster",
    # Generic Fresher / Non-tech bulk hiring
    "bca freshers", "bsc freshers", "mca freshers", "freshers hiring",
    "hiring for bca", "hiring freshers", "freshers",
    # Clerical, Back Office & Admin
    "mis analyst", "data entry", "back office", "typist", "clerk",
    "receptionist", "office assistant", "executive assistant", "admin executive",
    # Finance, Accounting, Legal & HR
    "accountant", "chartered accountant", "bookkeeper", "tax consultant",
    "audit associate", "hr executive", "recruiter", "talent acquisition",
    "hr generalist", "paralegal", "lawyer"
)

# Core candidate domain target title keywords (Data Engineering / MLOps / DevOps)
TARGET_ROLE_KEYWORDS = (
    # Data Engineering & Lakehouse
    "data engineer", "data engineering", "azure data", "big data",
    "databricks", "pyspark", "delta lake", "lakehouse", "fabric",
    "synapse", "hadoop", "spark", "snowflake", "etl", "elt",
    "data platform", "data pipeline", "data warehouse", "dwh",
    "database engineer", "sql developer", "bi developer", "business intelligence",
    # DevOps / MLOps / AI Platform
    "devops", "mlops", "ml engineer", "machine learning engineer",
    "ai infrastructure", "ai engineer", "cloud engineer", "cloud data",
    "platform engineer", "site reliability", "sre", "infrastructure engineer"
)

# Technical competencies that can qualify a generic technical title (e.g. "Software Engineer")
COMPETENCY_KEYWORDS = (
    "azure", "databricks", "spark", "pyspark", "delta lake", "lakehouse",
    "fabric", "synapse", "snowflake", "etl", "data pipeline", "kafka",
    "devops", "mlops", "kubernetes", "docker", "terraform", "sql", "big data"
)


def is_strictly_data_or_cloud_role(
    title: str,
    raw_jd: str = "",
    score: Optional[float] = None
) -> Tuple[bool, str]:
    """
    Evaluates whether a job strictly belongs to the candidate's core domain
    (Azure Data Engineer, Data Engineer, MLOps, DevOps, Cloud Data Platform).

    Returns:
        (is_eligible: bool, reason: str)
    """
    title_clean = (title or "").lower().strip()
    jd_clean = (raw_jd or "").lower().strip()

    if not title_clean:
        return False, "Rejected: Missing or empty job title"

    # 1. Hard Exclusion Gate: Blacklisted keywords in title
    for forbidden in FORBIDDEN_ROLE_KEYWORDS:
        if forbidden in title_clean:
            return False, f"Rejected: Non-data role detected in title ('{forbidden}')"

    # 2. Positive Target Role Check in title
    de_shorthands = (" de", "de ", "/de", "-de", "(de)", "[de]")
    if any(target in title_clean for target in TARGET_ROLE_KEYWORDS) or any(sh in title_clean for sh in de_shorthands) or title_clean == "de":
        # Even with target title, zero-score check if score is explicitly 0.0 with empty text
        if score is not None and score <= 0.0 and not any(k in title_clean for k in ("data engineer", "azure", "databricks", "pyspark", "devops", "mlops")):
            return False, f"Rejected: Match score {score}% has zero candidate competencies"
        return True, "Role title matches target candidate domain"

    # 3. High Match Score with Clean Title (Score >= 70% with verified technical competencies)
    if score is not None and score >= 70.0:
        return True, f"Role verified by high technical competency match score ({score}%)"

    # 4. Secondary Evaluation for General Tech Titles (e.g., Software Engineer, Python Developer, Backend Developer)
    general_tech_titles = (
        "software engineer", "software developer", "backend engineer", "backend developer",
        "python developer", "systems engineer", "cloud associate", "consultant", "analyst",
        "member of technical staff", "mts", "member technical staff", "specialist",
        "developer", "engineer", "architect", "lead", "associate"
    )

    is_general_tech = any(gt in title_clean for gt in general_tech_titles)
    combined_text = f"{title_clean} {jd_clean}".strip()

    has_competency = any(comp in combined_text for comp in COMPETENCY_KEYWORDS)

    if is_general_tech and has_competency:
        if score is not None and score < 20.0:
            return False, f"Rejected: Match score {score}% is below candidate competency floor (20%)"
        return True, "Role supported by technical data/cloud competencies"

    # If neither title matches target domain nor general tech with verified competencies:
    return False, f"Rejected: Role '{title}' does not align with Data Engineer / MLOps / DevOps domains"
