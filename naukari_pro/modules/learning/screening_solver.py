"""
naukariPro Learning Subsystem: Fact-Matrix Anchored Screening Solver (M2 / R2)
Anchored strictly in candidate ground truth from 01_FACT_MATRIX.md.
Eliminates blind affirmative fallbacks ("Yes", radios[0], options[0], return True).
Routes ambiguous, conflicting, or out-of-bounds questions to the quarantine ledger.
"""

import os
import re
import json
import logging
import unicodedata
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple, Union

logger = logging.getLogger("naukariPro.ScreeningSolver")


class ScreeningCategory(str, Enum):
    IDENTITY = "identity"
    CONTACT = "contact"
    LOCATION = "location"
    NOTICE_PERIOD = "notice_period"
    COMPENSATION_CURRENT = "compensation_current"
    COMPENSATION_EXPECTED = "compensation_expected"
    EXPERIENCE_TOTAL = "experience_total"
    EXPERIENCE_TOOL = "experience_tool"
    WORK_AUTH = "work_authorization"
    VISA_SPONSORSHIP = "visa_sponsorship"
    RELOCATION_MOBILITY = "relocation_mobility"
    SHIFT_AVAILABILITY = "shift_availability"
    LEGAL_BACKGROUND = "legal_background"
    EDUCATION = "education"
    EMPLOYER_HISTORY = "employer_history"
    UNMATCHED = "unmatched"


class ScreeningInputType(str, Enum):
    TEXT = "text"
    NUMBER = "number"
    RADIO = "radio"
    DROPDOWN = "dropdown"
    CHECKBOX = "checkbox"
    TEXTAREA = "textarea"


@dataclass(frozen=True)
class ScreeningDecision:
    answer: Optional[str]
    confidence: float  # Range: 0.0 to 1.0
    is_ambiguous: bool
    category: ScreeningCategory
    rationale: str
    raw_question: str
    input_type: ScreeningInputType = ScreeningInputType.TEXT
    suggested_options: Optional[List[str]] = None


class AmbiguousScreeningException(Exception):
    """Raised when a screening question is ambiguous or unmapped and must halt automated submission."""
    pass


# ==============================================================================
# DETERMINISTIC REGEX PATTERNS HIERARCHY
# ==============================================================================

# Disqualifying Questions (Must answer "No" / False)
DISQUALIFIER_NEGATIVE_REGEX = re.compile(
    r"\b(convicted|conviction|felony|criminal|misdemeanor|guilty\s+plea|deferred\s+adjudication)\b|"
    r"\b(non-compete|noncompetition|non\s+competition|restrictive\s+covenant)\b|"
    r"\b(terminated\s+for\s+cause|involuntarily\s+separated|disciplinary\s+action)\b|"
    r"\b(relatives?|family\s+members?)\s+(currently\s+)?(working\s+at|employed\s+by)\b|"
    r"\b((active|other|competing)\s+)*(active\s+offer|competing\s+offer|other\s+offer|offers)\b|"
    r"\b(career|education|employment)\s+gaps?\b",
    re.IGNORECASE
)

# Policy Consent & Verification (Must answer "Yes" / True)
POLICY_CONSENT_AFFIRMATIVE_REGEX = re.compile(
    r"\b(background\s+check|background\s+verification|bgv)\b|"
    r"\b(drug\s+test|drug\s+screen|substance\s+test)\b|"
    r"\b(agree\s+to|consent\s+to|certify\s+that|confirm\s+that|acknowledge\s+that)\b|"
    r"\b(terms\s+and\s+conditions|company\s+policies|code\s+of\s+conduct)\b|"
    r"^\s*(i\s+agree|i\s+consent|i\s+confirm|i\s+certify)\b",
    re.IGNORECASE
)

# Foreign Jurisdiction Restrictions (Candidate is based in India -> "No")
FOREIGN_JURISDICTION_REGEX = re.compile(
    r"\b(authorized\s+to\s+work\s+in\s+(the\s+)?(united\s+states|us|usa|uk|united\s+kingdom|canada|eu|australia|singapore))\b|"
    r"\b(us\s+citizen|green\s+card|permanent\s+resident\s+of\s+the\s+us)\b|"
    r"\bcurrently\s+reside\s+in\s+(the\s+)?(us|united\s+states|uk|united\s+kingdom|canada|eu)\b|"
    r"\bdo\s+you\s+(currently\s+)?live\s+in\s+(the\s+)?(us|united\s+states|uk|united\s+kingdom)\b",
    re.IGNORECASE
)

# Visa Sponsorship: "without sponsorship" -> "Yes"
WITHOUT_SPONSORSHIP_REGEX = re.compile(
    r"\b(without|not\s+requiring|no\s+need\s+for)\s*(employer\s+|visa\s+)?sponsorship\b|"
    r"\bauthorized\s+to\s+work\s+without\s+(requiring\s+)?sponsorship\b",
    re.IGNORECASE
)

# Visa Sponsorship Required: candidate does NOT require sponsorship in India -> "No"
REQUIRES_SPONSORSHIP_REGEX = re.compile(
    r"\b(will\s+you\s+now\s+or\s+in\s+the\s+future\s+)?require\s+(visa\s+|work\s+authorization\s+)?sponsorship\b|"
    r"\b(need|require)\s+(visa\s+sponsorship|work\s+permit|h1b|sponsorship)\b|"
    r"\bdo\s+you\s+require\s+(visa\s+)?sponsorship\b|"
    r"\brequire\s+visa\b",
    re.IGNORECASE
)

# Work Authorization in India: candidate IS authorized -> "Yes"
AUTHORIZED_WORK_INDIA_REGEX = re.compile(
    r"\b(legally\s+authorized|authorized\s+to\s+work|eligible\s+to\s+work|right\s+to\s+work)\b.*?"
    r"(\b(india|in\s+india)\b)?"
    r"|^\s*(are\s+you\s+authorized\s+to\s+work|work\s+authorization)\s*\??\s*$",
    re.IGNORECASE
)

# Notice Period Queries
SERVING_NOTICE_REGEX = re.compile(
    r"\b(serving\s+(your\s+)?notice|currently\s+(serving|on)\s+notice|are\s+you\s+on\s+notice)\b",
    re.IGNORECASE
)

NOTICE_PERIOD_REGEX = re.compile(
    r"\b(notice\s*period|notice\s*days|days\s+to\s+join|how\s+soon(\s+can\s+you\s+join)?|"
    r"joining\s*(time|period|lead\s*time|availability)|availability\s+to\s+join|"
    r"earliest\s+joining\s+date|official\s+notice\s+period|lead\s*time)\b",
    re.IGNORECASE
)

# Salary / Compensation Queries
EXPECTED_CTC_REGEX = re.compile(
    r"\b(expected|desired|expectation|expecting|looking\s+for|target|demand)\b.*?"
    r"\b(ctc|salary|compensation|package|remuneration|fixed\s+pay|lpa)\b|"
    r"\b(ctc|salary|compensation|package)\s+(expectation|desired|expected)\b",
    re.IGNORECASE
)

CURRENT_CTC_REGEX = re.compile(
    r"\b(current|present|existing|drawn|in-hand|inhand)\b.*?"
    r"\b(ctc|salary|compensation|package|remuneration|pay|fixed\s+pay|lpa)\b|"
    r"^\s*(ctc|current\s+ctc|fixed\s+ctc|present\s+ctc|fixed\s+salary)\s*(\(in\s+lakhs?\))?\s*$",
    re.IGNORECASE
)

ANNUAL_INR_REGEX = re.compile(r"\b(annual|inr|per\s+annum|in\s+rupees)\b", re.IGNORECASE)
LAKHS_LPA_REGEX = re.compile(r"\b(lakhs?|lpa|in\s+lakhs?)\b", re.IGNORECASE)
FOREIGN_CURRENCY_REGEX = re.compile(r"\b(usd|\$|eur|€|gbp|£|aud|cad)\b", re.IGNORECASE)

# Relocation and Shifts
RELOCATION_REGEX = re.compile(
    r"\b(willing\s+to\s+relocate|open\s+to\s+relocat(e|ion)|ready\s+to\s+relocate|"
    r"willingness\s+to\s+relocate|comfortable\s+relocating|open\s+for\s+relocation)\b",
    re.IGNORECASE
)

SHIFT_REGEX = re.compile(
    r"\b(rotational\s*shifts?|night\s*shifts?|day\s*shifts?|flexible\s*shifts?|"
    r"24/7\s*shifts?|uk\s*shift|us\s*shift|weekend\s*shifts?|comfortable\s+with\s+shifts)\b",
    re.IGNORECASE
)

WORK_MODE_REGEX = re.compile(
    r"\b(work\s+from\s+office|wfo|hybrid\s*model|in-office|on-site|onsite|flexible\s+work)\b",
    re.IGNORECASE
)

# Total Experience
TOTAL_EXP_REGEX = re.compile(
    r"\b(total|overall|relevant|hands-on|industry|work)\s*(years\s+of\s+)?(experience|exp|yoe)\b|"
    r"\bhow\s+many\s+years\s+(of\s+experience)?\b|"
    r"^\s*(total\s+experience|overall\s+experience|experience|yoe|exp)\s*(\(in\s+years?\))?\s*$",
    re.IGNORECASE
)

# Tool Specific Experience Patterns
TOOL_EXP_PATTERNS = {
    "pyspark": (re.compile(r"\b(pyspark|spark)\b", re.IGNORECASE), "2.5"),
    "databricks": (re.compile(r"\b(databricks|azure\s+databricks)\b", re.IGNORECASE), "2.5"),
    "delta_lake": (re.compile(r"\b(delta\s*lake|lakehouse)\b", re.IGNORECASE), "2.5"),
    "azure_adf": (re.compile(r"\b(azure|data\s*factory|adf)\b", re.IGNORECASE), "2.5"),
    "kafka": (re.compile(r"\b(kafka|apache\s*kafka|streaming)\b", re.IGNORECASE), "2"),
    "sql": (re.compile(r"\b(sql|spark\s*sql|tsql|transact-sql)\b", re.IGNORECASE), "2.5"),
    "kubernetes": (re.compile(r"\b(kubernetes|k8s|kubeadm|eks)\b", re.IGNORECASE), "2.5"),
    "docker": (re.compile(r"\b(docker|containers?|containerd|helm)\b", re.IGNORECASE), "2.5"),
    "terraform": (re.compile(r"\b(terraform|iac)\b", re.IGNORECASE), "2"),
    "ansible": (re.compile(r"\b(ansible|configuration\s+management)\b", re.IGNORECASE), "2"),
    "python": (re.compile(r"\b(python)\b", re.IGNORECASE), "2.5"),
    "elk": (re.compile(r"\b(elk|elasticsearch|logstash|kibana|grok)\b", re.IGNORECASE), "1.5"),
}

# Forbidden / Synthetic Skills (per 01_FACT_MATRIX.md -> Return "0" or Quarantine)
FORBIDDEN_TECH_REGEX = re.compile(
    r"\b(triton\s*(inference\s*server)?|nvidia\s*mps|gpu\s*slicing|model\s*validation\s*gates)\b",
    re.IGNORECASE
)

# Open-ended / Subjective Prompts (Must Quarantine)
SUBJECTIVE_PROMPT_REGEX = re.compile(
    r"\b(why\s+do\s+you\s+want\s+to\s+join|"
    r"why\s+should\s+we\s+hire\s+you|"
    r"tell\s+(me|us)\s+about\s+yourself|"
    r"describe\s+a\s+(time|project|challenge)|"
    r"what\s+is\s+your\s+greatest\s+(strength|weakness)|"
    r"cover\s+letter|additional\s+info(rmation)?)\b",
    re.IGNORECASE
)


class FactMatrixScreeningSolver:
    """
    Ground-truth screening solver anchored in 01_FACT_MATRIX.md.
    Provides deterministic question mapping and strict quarantine gating.
    """

    CONFIDENCE_THRESHOLD: float = 0.70

    def __init__(self, config_data: Optional[Dict[str, Any]] = None):
        if config_data:
            self.config = config_data
        else:
            try:
                from naukari_pro.config import load_config
                self.config = load_config()
            except Exception:
                self.config = {}

        candidate = self.config.get("candidate", {})
        self.candidate_name = candidate.get("name", "Lavkush Kumar")
        self.candidate_email = candidate.get("email", "lav84095@gmail.com")
        self.candidate_phone = candidate.get("phone", "+91 9122036484")
        self.candidate_linkedin = candidate.get("linkedin", "https://linkedin.com/in/lavkushry")
        self.candidate_github = candidate.get("github", "https://github.com/lavkushry")
        self.total_exp = str(candidate.get("total_experience_years", "2.5"))
        self.notice_days = str(candidate.get("notice_period_days", "15"))
        
        curr_ctc = candidate.get("current_ctc_lakhs", 12)
        try:
            val = float(curr_ctc)
            self.current_ctc_lpa = str(int(val)) if val.is_integer() else str(val)
        except Exception:
            self.current_ctc_lpa = str(curr_ctc)

        exp_ctc = candidate.get("expected_ctc_lakhs", 20)
        try:
            val_e = float(exp_ctc)
            self.expected_ctc_lpa = str(int(val_e)) if val_e.is_integer() else str(val_e)
        except Exception:
            self.expected_ctc_lpa = str(exp_ctc)

        self.current_company = candidate.get("current_company", "CGI India")
        self.current_designation = candidate.get("current_title", "DevOps Engineer")
        self.degree = candidate.get("degree", "B.Tech in Computer Science and Engineering")
        self.university = candidate.get("university", "Maharishi Dayanand University")
        self.graduation_year = str(candidate.get("graduation_year", "2023"))

    def solve_question(
        self,
        question_text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[str], float, bool]:
        """
        Public contract per orchestrator/PROJECT.md:
        Returns: (answer: Optional[str], confidence: float, is_ambiguous: bool)
        """
        decision = self.evaluate_question(question_text, context)
        return decision.answer, decision.confidence, decision.is_ambiguous

    def evaluate_question(
        self,
        question_text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ScreeningDecision:
        """Evaluates question and returns rich, typed ScreeningDecision."""
        ctx = context or {}
        raw = question_text or ""
        q = raw.strip()
        q_lower = q.lower()

        # 0. Empty or whitespace prompt
        if not q:
            return ScreeningDecision(
                answer=None,
                confidence=0.0,
                is_ambiguous=True,
                category=ScreeningCategory.UNMATCHED,
                rationale="Empty question prompt",
                raw_question=raw
            )

        # 1. Subjective / open-ended questions -> Route to quarantine
        if SUBJECTIVE_PROMPT_REGEX.search(q_lower):
            return ScreeningDecision(
                answer=None,
                confidence=0.2,
                is_ambiguous=True,
                category=ScreeningCategory.UNMATCHED,
                rationale="Subjective open-ended question requires human approval",
                raw_question=raw
            )

        # 2. Negative Disqualifiers -> Must answer "No"
        if DISQUALIFIER_NEGATIVE_REGEX.search(q_lower):
            return ScreeningDecision(
                answer="No",
                confidence=1.0,
                is_ambiguous=False,
                category=ScreeningCategory.LEGAL_BACKGROUND,
                rationale="Disqualifier question mapped to ground truth 'No'",
                raw_question=raw
            )

        # 3. Foreign Jurisdiction Restrictions -> Candidate resides in India -> "No"
        if FOREIGN_JURISDICTION_REGEX.search(q_lower):
            return ScreeningDecision(
                answer="No",
                confidence=1.0,
                is_ambiguous=False,
                category=ScreeningCategory.WORK_AUTH,
                rationale="Candidate resides in India and lacks foreign work authorization",
                raw_question=raw
            )

        # 4. Visa Sponsorship
        if WITHOUT_SPONSORSHIP_REGEX.search(q_lower):
            return ScreeningDecision(
                answer="Yes",
                confidence=1.0,
                is_ambiguous=False,
                category=ScreeningCategory.VISA_SPONSORSHIP,
                rationale="Candidate authorized to work without sponsorship",
                raw_question=raw
            )

        if REQUIRES_SPONSORSHIP_REGEX.search(q_lower):
            return ScreeningDecision(
                answer="No",
                confidence=1.0,
                is_ambiguous=False,
                category=ScreeningCategory.VISA_SPONSORSHIP,
                rationale="Candidate does not require visa sponsorship in India",
                raw_question=raw
            )

        if AUTHORIZED_WORK_INDIA_REGEX.search(q_lower):
            return ScreeningDecision(
                answer="Yes",
                confidence=1.0,
                is_ambiguous=False,
                category=ScreeningCategory.WORK_AUTH,
                rationale="Candidate legally authorized to work in India",
                raw_question=raw
            )

        # 5. Policy Consent & Background Checks
        if POLICY_CONSENT_AFFIRMATIVE_REGEX.search(q_lower):
            return ScreeningDecision(
                answer="Yes",
                confidence=1.0,
                is_ambiguous=False,
                category=ScreeningCategory.LEGAL_BACKGROUND,
                rationale="Candidate consents to background checks and standard policies",
                raw_question=raw
            )

        # 6. Mobility, Relocation, and Shift Flexibility
        if RELOCATION_REGEX.search(q_lower):
            return ScreeningDecision(
                answer="Yes",
                confidence=1.0,
                is_ambiguous=False,
                category=ScreeningCategory.RELOCATION_MOBILITY,
                rationale="Candidate willing to relocate to major tech hubs",
                raw_question=raw
            )

        if SHIFT_REGEX.search(q_lower) or WORK_MODE_REGEX.search(q_lower):
            return ScreeningDecision(
                answer="Yes",
                confidence=1.0,
                is_ambiguous=False,
                category=ScreeningCategory.SHIFT_AVAILABILITY,
                rationale="Candidate flexible with shifts and work modes (hybrid/WFO)",
                raw_question=raw
            )

        # 7. Notice Period & Availability
        if SERVING_NOTICE_REGEX.search(q_lower):
            return ScreeningDecision(
                answer="No",
                confidence=1.0,
                is_ambiguous=False,
                category=ScreeningCategory.NOTICE_PERIOD,
                rationale="Candidate is actively employed and not currently serving notice",
                raw_question=raw
            )

        if NOTICE_PERIOD_REGEX.search(q_lower):
            # Formats: numeric "15" or text "15 days"
            opts = ctx.get("options")
            if opts:
                opts_low = [str(o).lower().strip() for o in opts]
                for target in ["15 days", "immediate", "less than 15", "0-15", "15-30", "< 30", "30 days"]:
                    for idx, o in enumerate(opts_low):
                        if target in o:
                            return ScreeningDecision(
                                answer=opts[idx],
                                confidence=0.95,
                                is_ambiguous=False,
                                category=ScreeningCategory.NOTICE_PERIOD,
                                rationale=f"Matched notice period dropdown option '{opts[idx]}'",
                                raw_question=raw
                            )

            # In text inputs, default to clean numeric notice period string ("15")
            return ScreeningDecision(
                answer=str(self.notice_days),
                confidence=1.0,
                is_ambiguous=False,
                category=ScreeningCategory.NOTICE_PERIOD,
                rationale="Notice period anchored at candidate truth (15 days)",
                raw_question=raw
            )

        # 8. Financial / Compensation / CTC
        # Check foreign currency first -> Quarantine if asked for USD/EUR/etc.
        if FOREIGN_CURRENCY_REGEX.search(q_lower) and not LAKHS_LPA_REGEX.search(q_lower):
            return ScreeningDecision(
                answer=None,
                confidence=0.3,
                is_ambiguous=True,
                category=ScreeningCategory.COMPENSATION_EXPECTED,
                rationale="Candidate compensation is calibrated in INR (LPA), foreign currency query requires operator review",
                raw_question=raw
            )

        if EXPECTED_CTC_REGEX.search(q_lower):
            if ANNUAL_INR_REGEX.search(q_lower) and not LAKHS_LPA_REGEX.search(q_lower):
                ans = f"{int(float(self.expected_ctc_lpa) * 100000)}"
            else:
                ans = self.expected_ctc_lpa
            return ScreeningDecision(
                answer=ans,
                confidence=1.0,
                is_ambiguous=False,
                category=ScreeningCategory.COMPENSATION_EXPECTED,
                rationale="Expected CTC anchored at candidate truth (20 LPA)",
                raw_question=raw
            )

        if CURRENT_CTC_REGEX.search(q_lower):
            if ANNUAL_INR_REGEX.search(q_lower) and not LAKHS_LPA_REGEX.search(q_lower):
                ans = f"{int(float(self.current_ctc_lpa) * 100000)}"
            else:
                ans = self.current_ctc_lpa
            return ScreeningDecision(
                answer=ans,
                confidence=1.0,
                is_ambiguous=False,
                category=ScreeningCategory.COMPENSATION_CURRENT,
                rationale="Current CTC anchored at candidate truth (12 LPA)",
                raw_question=raw
            )

        # 9. Technical Skills Experience Duration
        if FORBIDDEN_TECH_REGEX.search(q_lower):
            return ScreeningDecision(
                answer="0",
                confidence=0.9,
                is_ambiguous=False,
                category=ScreeningCategory.EXPERIENCE_TOOL,
                rationale="Synthetic skill claim disallowed under 01_FACT_MATRIX.md",
                raw_question=raw
            )

        for tool_key, (pat, duration) in TOOL_EXP_PATTERNS.items():
            if pat.search(q_lower) and any(w in q_lower for w in ("experience", "exp", "yoe", "years", "tenure", "duration")):
                # Check if integer only
                ans = duration
                if ctx.get("integer_only"):
                    ans = str(int(float(duration)))
                return ScreeningDecision(
                    answer=ans,
                    confidence=0.95,
                    is_ambiguous=False,
                    category=ScreeningCategory.EXPERIENCE_TOOL,
                    rationale=f"Verified technical experience for {tool_key}: {ans} years",
                    raw_question=raw
                )

        # 10. Total Experience
        if TOTAL_EXP_REGEX.search(q_lower):
            opts = ctx.get("options")
            if opts:
                opts_low = [str(o).lower().strip() for o in opts]
                for target in ["2-3", "2 to 3", "2-4", "2 to 4", "2+", "2.5", "1-3"]:
                    for idx, o in enumerate(opts_low):
                        if target in o:
                            return ScreeningDecision(
                                answer=opts[idx],
                                confidence=0.95,
                                is_ambiguous=False,
                                category=ScreeningCategory.EXPERIENCE_TOTAL,
                                rationale=f"Matched experience dropdown option '{opts[idx]}'",
                                raw_question=raw
                            )

            ans = self.total_exp
            if ctx.get("integer_only"):
                ans = str(int(float(self.total_exp)))
            return ScreeningDecision(
                answer=ans,
                confidence=1.0,
                is_ambiguous=False,
                category=ScreeningCategory.EXPERIENCE_TOTAL,
                rationale="Total experience anchored at candidate truth (2.5 years)",
                raw_question=raw
            )

        # 11. Identity and Contact Details
        if re.search(r"\b(applicant|candidate|full|your)\s*name\b|^name\??$", q_lower):
            return ScreeningDecision(
                answer=self.candidate_name,
                confidence=1.0,
                is_ambiguous=False,
                category=ScreeningCategory.IDENTITY,
                rationale="Candidate full name",
                raw_question=raw
            )

        if re.search(r"\b(email|mail\s*id|email\s*address)\b", q_lower):
            return ScreeningDecision(
                answer=self.candidate_email,
                confidence=1.0,
                is_ambiguous=False,
                category=ScreeningCategory.CONTACT,
                rationale="Candidate email address",
                raw_question=raw
            )

        if re.search(r"\b(phone|mobile|cell|contact\s*number|whatsapp)\b", q_lower):
            return ScreeningDecision(
                answer=self.candidate_phone,
                confidence=1.0,
                is_ambiguous=False,
                category=ScreeningCategory.CONTACT,
                rationale="Candidate contact number",
                raw_question=raw
            )

        if "linkedin" in q_lower:
            return ScreeningDecision(
                answer=self.candidate_linkedin,
                confidence=1.0,
                is_ambiguous=False,
                category=ScreeningCategory.CONTACT,
                rationale="Candidate LinkedIn URL",
                raw_question=raw
            )

        if any(w in q_lower for w in ("github", "git repo", "portfolio", "code sample")):
            return ScreeningDecision(
                answer=self.candidate_github,
                confidence=1.0,
                is_ambiguous=False,
                category=ScreeningCategory.CONTACT,
                rationale="Candidate GitHub URL",
                raw_question=raw
            )

        # 12. Employer History & Education
        if re.search(r"\b(current|present)\s*(company|employer|organization|org)\b", q_lower):
            return ScreeningDecision(
                answer=self.current_company,
                confidence=1.0,
                is_ambiguous=False,
                category=ScreeningCategory.EMPLOYER_HISTORY,
                rationale="Current verified employer (CGI India)",
                raw_question=raw
            )

        if re.search(r"\b(current|present)\s*(designation|job\s*title|role)\b", q_lower):
            return ScreeningDecision(
                answer=self.current_designation,
                confidence=1.0,
                is_ambiguous=False,
                category=ScreeningCategory.EMPLOYER_HISTORY,
                rationale="Current verified designation (DevOps Engineer)",
                raw_question=raw
            )

        if re.search(r"\b(degree|qualification|highest\s*education|highest\s*degree)\b", q_lower):
            opts = ctx.get("options")
            if opts:
                opts_low = [str(o).lower().strip() for o in opts]
                for target in ["bachelor", "b.tech", "graduate", "engineering", "b.e."]:
                    for idx, o in enumerate(opts_low):
                        if target in o:
                            return ScreeningDecision(
                                answer=opts[idx],
                                confidence=0.95,
                                is_ambiguous=False,
                                category=ScreeningCategory.EDUCATION,
                                rationale=f"Matched education dropdown option '{opts[idx]}'",
                                raw_question=raw
                            )
            return ScreeningDecision(
                answer=self.degree,
                confidence=1.0,
                is_ambiguous=False,
                category=ScreeningCategory.EDUCATION,
                rationale="Candidate education degree (B.Tech in CSE)",
                raw_question=raw
            )

        if re.search(r"\b(college|university|institute)\b", q_lower):
            return ScreeningDecision(
                answer=self.university,
                confidence=1.0,
                is_ambiguous=False,
                category=ScreeningCategory.EDUCATION,
                rationale="Candidate university",
                raw_question=raw
            )

        if re.search(r"\b(passing\s*year|year\s+of\s+passing|graduation\s*year)\b", q_lower):
            return ScreeningDecision(
                answer=self.graduation_year,
                confidence=1.0,
                is_ambiguous=False,
                category=ScreeningCategory.EDUCATION,
                rationale="Candidate graduation year (2023)",
                raw_question=raw
            )

        # 13. Location Preferences
        if re.search(r"\b(current\s*location|current\s*city|residing\s*city)\b", q_lower):
            return ScreeningDecision(
                answer="Bangalore",
                confidence=1.0,
                is_ambiguous=False,
                category=ScreeningCategory.LOCATION,
                rationale="Candidate primary base location",
                raw_question=raw
            )

        # 14. Unmatched prompt -> Ambiguous, confidence < threshold
        return ScreeningDecision(
            answer=None,
            confidence=0.0,
            is_ambiguous=True,
            category=ScreeningCategory.UNMATCHED,
            rationale="Unmatched screening question; refused blind affirmative fallback",
            raw_question=raw
        )

    def route_to_quarantine(
        self,
        question_text: str,
        role_info: Optional[Dict[str, Any]] = None,
        reason: str = "ambiguous_screening_question",
        category: str = "screening_ambiguous",
        platform: str = "generic",
        db_path: Optional[str] = None
    ) -> int:
        """
        Routes an ambiguous question to the persistent SQLite quarantine table.
        Returns: quarantine_id (int)
        """
        from naukari_pro.modules.db import quarantine_item
        ctx = role_info or {}
        ctx["reason"] = reason
        q_id = quarantine_item(
            category=category,
            platform=platform,
            prompt_text=question_text,
            context=ctx,
            status="PENDING",
            db_path=db_path
        )
        logger.warning(
            "QUARANTINED prompt #%d: '%s' (Platform: %s, Reason: %s)",
            q_id, question_text, platform, reason
        )
        return q_id
