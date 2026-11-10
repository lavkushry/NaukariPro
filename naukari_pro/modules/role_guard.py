"""
Role Guard Module for NaukariPro
Enforces non-negotiable role family and domain constraints.
Strictly blocks non-Data Engineer / non-MLOps / non-DevOps roles.
Guarantees that universal apply NEVER bypasses core candidate domain alignment.
"""

import re
from typing import Tuple, Optional
import logging

logger = logging.getLogger("naukariPro.RoleGuard")

# Negative exclusions: Non-IT, non-data, clerical, healthcare, hospitality, service, sales, pure frontend, bulk fresher titles
FORBIDDEN_ROLE_KEYWORDS = (
    # BPO, Telecalling & Customer Service
    "telecalling", "telecaller", "tele-calling", "tele-caller", "tele caller", "call center",
    "bpo", "kpo", "customer care", "customer support", "customer success", "client support",
    "helpdesk", "technical support executive", "desktop support",
    # Non-software Engineering & CAD
    "mechanical", "civil engineer", "civil engineering", "electrical design", "hardware engineer",
    "embedded engineer", "vlsi", "pcb", "autocad", "structural engineer", "drafter", "draftsman",
    "cad designer", "cad engineer", "solidworks", "cad ", "autodesk",
    "manufacturing engineer", "chemical engineer", "automotive engineer", "drilling engineer",
    "mining engineer", "geotechnical engineer", "power systems engineer", "process engineer",
    "aerospace engineer", "marine engineer", "petroleum engineer",
    # Natural Sciences, Humanities, Academia & Freelance Annotation
    "biology", "physics", "chemistry", "history", "economics", "statistician", "economist",
    "environmental scientist", "geologist", "agriculture", "botanist", "zoologist", "journalist",
    "annotator", "annotation", "freelancer", "freelance",
    # Languages & Translation
    "german", "french", "spanish", "japanese", "mandarin", "russian", "chinese", "italian",
    "language processor", "translator", "linguist", "interpreter",
    # Non-Data ERP & Functional
    "sap mdg", "sap mm", "sap fico", "sap sd", "sap abap", "sap basis",
    "sap functional", "sap hcm", "salesforce functional",
    # Operations, Logistics & Procurement
    "procurement", "purchasing", "supply chain", "logistics", "inventory", "buyer",
    # Project, Product & Agile Management
    "product manager", "project manager", "program manager", "delivery manager",
    "scrum master", "agile coach", "release train engineer", "operations manager",
    "account manager",
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
    # QA, Automation Testing & SDET
    "qa", "qa engineer", "qa analyst", "qa lead", "qa manager", "qa automation",
    "quality assurance", "test engineer", "automation tester", "automation test",
    "automation testing", "automation engineer", "sdet", "tester", "testing",
    "software test", "software testing", "test analyst", "test lead",
    "manual tester", "manual qa", "qa manual", "functional tester",
    # Non-Data Software, Web & Mobile Development
    "full stack", "fullstack", "full-stack", "dot net", ".net", "dotnet", "c#", "asp.net",
    "node.js", "nodejs", "react", "react.js", "reactjs", "angular", "vue", "vue.js",
    "front end developer", "frontend developer", "front-end developer",
    "backend developer", "back end developer", "java developer", "java +", "java/j2ee", "j2ee",
    "golang developer", "go developer", "php developer", "php", "ruby developer", "ruby on rails",
    "android developer", "android engineer", "ios developer", "ios engineer", "mobile developer", "mobile app",
    "ui/ux", "graphic designer", "webmaster", "web developer", "ui developer",
    "wordpress", "magento", "drupal", "shopify",
    # Non-Data Enterprise / Domain Architectures & Solutions
    "braze", "speech analytics", "audio engineer", "speech engineer",
    "crm developer", "crm architect", "salesforce developer", "salesforce architect",
    "pega", "guidewire", "workday consultant", "servicenow developer",
    # Generic Fresher / Non-tech bulk hiring
    "bca freshers", "bsc freshers", "mca freshers", "freshers hiring",
    "hiring for bca", "hiring freshers", "freshers",
    # Clerical, Back Office & Admin
    "mis analyst", "data entry", "back office", "typist", "clerk",
    "receptionist", "office assistant", "executive assistant", "admin executive",
    # Non-Engineering Analyst
    "business analyst", "data analyst", "financial analyst", "operations analyst",
    "reporting analyst", "bi analyst", "risk analyst", "mis executive",
    # Finance, Accounting, Legal & HR
    "accountant", "chartered accountant", "bookkeeper", "tax consultant",
    "audit associate", "hr executive", "recruiter", "talent acquisition",
    "hr generalist", "paralegal", "lawyer", "legal associate"
)

# Known gig annotation / crowd-task / spam vendors
FORBIDDEN_COMPANIES = (
    "soul ai",
    "clickerscabin",
    "nextgen education foundation",
    "gratitude india",
    "wonksknow technologies",
    "remotasks",
    "appen",
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
    score: Optional[float] = None,
    company: str = ""
) -> Tuple[bool, str]:
    """
    Evaluates whether a job strictly belongs to the candidate's core domain
    (Azure Data Engineer, Data Engineer, MLOps, DevOps, Cloud Data Platform).

    Returns:
        (is_eligible: bool, reason: str)
    """
    title_clean = (title or "").lower().strip()
    jd_clean = (raw_jd or "").lower().strip()
    comp_clean = (company or "").lower().strip()

    if not title_clean:
        return False, "Rejected: Missing or empty job title"

    # 0. Excluded Companies Gate (Known gig annotators / crowd spam)
    for forbidden_co in FORBIDDEN_COMPANIES:
        if forbidden_co in comp_clean:
            return False, f"Rejected: Excluded non-target / gig annotator employer ('{forbidden_co}')"

    # 1. Hard Exclusion Gate: Blacklisted keywords in title
    for forbidden in FORBIDDEN_ROLE_KEYWORDS:
        if len(forbidden) <= 4 or forbidden.startswith(".") or forbidden.startswith("c#"):
            if re.search(rf"(?:\b|^|\s){re.escape(forbidden)}(?:\b|$|\s)", title_clean):
                return False, f"Rejected: Non-data role detected in title ('{forbidden}')"
        else:
            if forbidden in title_clean:
                return False, f"Rejected: Non-data role detected in title ('{forbidden}')"

    # 2. Positive Target Role Check in title
    has_target = any(target in title_clean for target in TARGET_ROLE_KEYWORDS) or bool(re.search(r"\bde\b", title_clean))
    if has_target:
        # Even with target title, zero-score check if score is explicitly 0.0 with empty text
        if score is not None and score <= 0.0 and not any(k in title_clean for k in ("data engineer", "azure", "databricks", "pyspark", "devops", "mlops")):
            return False, f"Rejected: Match score {score}% has zero candidate competencies"
        return True, "Role title matches target candidate domain"

    # 3. High Match Score with Clean Title (Score >= 70% with verified technical competencies)
    if score is not None and score >= 70.0:
        return True, f"Role verified by high technical competency match score ({score}%)"

    # 4. Secondary Evaluation for General Tech Titles (Strictly Software / Systems Engineer with Data Focus)
    general_tech_titles = (
        "software engineer", "software developer", "backend engineer",
        "systems engineer", "member of technical staff", "mts", "member technical staff"
    )

    is_general_tech = any(gt in title_clean for gt in general_tech_titles)
    combined_text = f"{title_clean} {jd_clean}".strip()

    # Must contain at least 2 candidate technical data/cloud platform competencies
    matched_competencies = [comp for comp in COMPETENCY_KEYWORDS if comp in combined_text]

    if is_general_tech and len(matched_competencies) >= 2:
        if score is not None and score < 50.0:
            return False, f"Rejected: Match score {score}% is below candidate competency floor (50%) for general tech title"
        return True, "Role supported by technical data/cloud competencies"

    # If neither title matches target domain nor general tech with verified competencies:
    return False, f"Rejected: Role '{title}' does not align with Data Engineer / MLOps / DevOps domains"
