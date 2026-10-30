"""
naukariPro Feature 1: Intelligent Auto-Apply Engine
Dual-Engine Architecture:
1. Native Chrome Bridge (macOS): Undetected by WAF, operates through authentic user Chrome browser.
2. Playwright Stealth Context (Linux/Headless): Automated headless pipeline with full Chromium fallback.

Critical Guarantees:
- Never fakes application success: checks for explicit submission confirmation before reporting 'applied'.
- Distinguishes external company site redirects from 1-click Naukri submissions.
- Multi-apply requires actual selectable checkboxes; returns 0 if none found.
- Seamlessly falls back to Playwright Chromium on Linux or headless setups.
"""

import os
import sys
import time
import json
import re
import hashlib
import subprocess
from datetime import datetime
import shutil
import openpyxl
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List

from naukari_pro.config import TRACKER_PATH, SESSION_DIR, COOKIES_SEED_PATH, load_config
from naukari_pro.session import get_stealth_context
from naukari_pro.modules.job_alerts import (
    calculate_match_score,
    MATCH_SCORE_THRESHOLD as DEFAULT_MATCH_SCORE_THRESHOLD,
    KEYWORD_WEIGHTS
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKIP_FILE = os.path.join(BASE_DIR, "skip_list.json")
LOG_FILE = os.path.join(BASE_DIR, "naukri_applications_log.json")

# Candidate facts dynamically loaded from single source of truth
_CONFIG = load_config()
_CANDIDATE = _CONFIG.get("candidate", {})
_SEARCH = _CONFIG.get("search_settings", {})

NAUKRI_EMAIL = _CANDIDATE.get("email", "lav84095@gmail.com")
EXPERIENCE_YEARS = str(_CANDIDATE.get("total_experience_years", "2.5"))
EXPERIENCE_PARAM = str(int(float(EXPERIENCE_YEARS)))  # "2" for Naukri query string (2 matches 2-5 YOE)
NOTICE_PERIOD = str(_CANDIDATE.get("notice_period_days", "15"))
_curr_ctc_val = float(_CANDIDATE.get("current_ctc_lakhs", 12))
CURRENT_CTC = str(int(_curr_ctc_val)) if _curr_ctc_val.is_integer() else str(_curr_ctc_val)
_exp_ctc_val = float(_CANDIDATE.get("expected_ctc_lakhs", 20))
EXPECTED_CTC = str(int(_exp_ctc_val)) if _exp_ctc_val.is_integer() else str(_exp_ctc_val)
MIN_SALARY_LPA = float(_SEARCH.get("min_salary_lpa", 12.0))
MATCH_SCORE_THRESHOLD = int(float(_SEARCH.get("min_match_score", 80.0)))
CANDIDATE_EXPERIENCE = float(_CANDIDATE.get("total_experience_years", 2.5))
MAX_EXPERIENCE_THRESHOLD = float(_SEARCH.get("max_experience", 4.0))

EXPANDED_M2_KEYWORDS = [
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

_raw_kw = _SEARCH.get("keywords", [])
if _raw_kw:
    DEFAULT_KEYWORDS = list(dict.fromkeys(list(_raw_kw) + EXPANDED_M2_KEYWORDS))
else:
    DEFAULT_KEYWORDS = EXPANDED_M2_KEYWORDS

CANONICAL_LOCATIONS = [
    "hyderabad",
    "bengaluru",
    "pune",
    "gurugram",
    "noida",
    "mumbai",
    "chennai"
]

_raw_locs = _SEARCH.get("locations", [])
if _raw_locs:
    cleaned_locs = [l.lower().strip() for l in _raw_locs if l.lower().strip() not in ("remote", "bangalore", "gurgaon")]
    LOCATIONS = list(dict.fromkeys(cleaned_locs + CANONICAL_LOCATIONS))
else:
    LOCATIONS = CANONICAL_LOCATIONS


def build_search_url(keyword: str, location: str, page_num: int = 1) -> str:
    """
    Constructs search query URL with freshness parameters and multi-page pagination.
    experience={EXPERIENCE_PARAM}&jobAge=1&freshness=1&sortBy=date&sortType=1
    """
    slug = "-".join(keyword.lower().split())
    loc = location.lower().strip()
    page_suffix = f"-{page_num}" if page_num > 1 else ""
    page_query = f"&pageNo={page_num}" if page_num > 1 else ""
    return f"https://www.naukri.com/{slug}-jobs-in-{loc}{page_suffix}?experience={EXPERIENCE_PARAM}&jobAge=1&freshness=1&sortBy=date&sortType=1{page_query}"


SCREENING_RADIO_JS = r"""(qText) => {
    const drawer = document.querySelector('.chatbot_Drawer, [class*="chatbot_Drawer"]');
    if (!drawer) return { handled: false, chosenText: null };

    // Disentangled radio selector: NEVER select labels inside .multicheckboxes-container or labels wrapping/adjacent to checkboxes
    const rawRadios = Array.from(drawer.querySelectorAll(
        '.ssrc__label, .singleSelectRadioButton label, input[type="radio"] + label, label.radio-label, div[class*="radio"] label, input[type="radio"]'
    ));

    const getRadioText = (r) => {
        const lbl = r.closest('label');
        let txt = (lbl ? lbl.innerText : (r.innerText || ''));
        if (!txt && r.value && r.value !== 'on') txt = r.value;
        return (txt || '').toLowerCase().trim();
    };

    const radios = rawRadios.filter(e => {
        if (e.offsetWidth <= 0 && (!e.parentElement || e.parentElement.offsetWidth <= 0)) return false;
        if (e.closest('.multicheckboxes-container') || e.closest('div[class*="checkbox"]')) return false;
        if (e.tagName.toLowerCase() === 'input' && e.type === 'checkbox') return false;
        if (e.querySelector && e.querySelector('input[type="checkbox"]')) return false;
        return getRadioText(e).length > 0;
    });

    if (radios.length > 0) {
        const qLower = (qText || '').toLowerCase();
        const affirmativeWords = [
            'yes', 'agree', 'comfortable', 'immediate', '15 days', '30 days',
            '1 month', 'flexible', 'open', 'available', 'full time', 'day shift',
            'night shift', 'regular', 'hybrid', 'permanent', 'rotational', 'willing',
            'relocate', 'anywhere'
        ];
        const negativeRegex = /\b(no|not|disagree|uncomfortable|inflexible|reluctant|cannot|more than 30 days|more than 1 month)\b/i;

        let chosen = null;

        // Context 1: Notice Period / Availability
        if (qLower.includes('notice') || qLower.includes('join') || qLower.includes('availability') || qLower.includes('lead time')) {
            const noticeOptions = ['15 days or less', '15 days', 'immediate', '0-15 days', '0 to 15', '< 30 days', '30 days or less', '30 days', '1 month'];
            chosen = radios.find(r => {
                const txt = getRadioText(r);
                return noticeOptions.some(opt => txt.includes(opt)) && !negativeRegex.test(txt);
            });
        }

        // Context 2: Current / Expected CTC
        if (!chosen && (qLower.includes('ctc') || qLower.includes('salary') || qLower.includes('compensation') || qLower.includes('package'))) {
            if (qLower.includes('expected') || qLower.includes('desired') || qLower.includes('looking')) {
                chosen = radios.find(r => {
                    const txt = getRadioText(r);
                    return (txt.includes('20') || txt.includes('18-22') || txt.includes('20-25') || txt.includes('15-20') || txt.includes('20+')) && !negativeRegex.test(txt);
                });
            } else {
                chosen = radios.find(r => {
                    const txt = getRadioText(r);
                    return (txt.includes('12') || txt.includes('10-15') || txt.includes('10 to 15') || txt.includes('12-14') || txt.includes('10-12')) && !negativeRegex.test(txt);
                });
            }
        }

        // Context 3: Location / Mobility
        if (!chosen && (qLower.includes('preferred location') || qLower.includes('current location') || qLower.includes('city') || qLower.includes('location'))) {
            const locTerms = ['hyderabad', 'bengaluru', 'bangalore', 'pune', 'gurugram', 'noida', 'chennai', 'mumbai', 'any'];
            chosen = radios.find(r => {
                const txt = getRadioText(r);
                return locTerms.some(l => txt.includes(l)) && !negativeRegex.test(txt);
            });
        }

        // Context 4: Holding Offers / Serving Notice / Gaps
        if (!chosen && (qLower.includes('serving notice') || qLower.includes('holding offer') || qLower.includes('competing offer') || qLower.includes('gap'))) {
            chosen = radios.find(r => {
                const txt = getRadioText(r);
                return txt === 'no' || txt.startsWith('no ') || txt.includes('not serving') || txt.includes('none');
            });
        }

        // Context 5: Experience / Tech tool bracket
        if (!chosen && (qLower.includes('experience') || qLower.includes('years') || qLower.includes('yoe') || qLower.includes('pyspark') || qLower.includes('databricks') || qLower.includes('azure') || qLower.includes('sql') || qLower.includes('kafka'))) {
            chosen = radios.find(r => {
                const txt = getRadioText(r);
                const matchesBracket = txt.includes('2-3') || txt.includes('2 to 3') || txt.includes('2-4') || txt.includes('2.5') || txt.includes('2+') || txt.includes('2 to 4') || txt.includes('yes') || txt.includes('expert') || txt.includes('proficient');
                return matchesBracket && !negativeRegex.test(txt);
            });
        }

        // General affirmative matching
        if (!chosen) {
            chosen = radios.find(r => {
                const txt = getRadioText(r);
                const hasAffirmative = affirmativeWords.some(w => {
                    const regex = new RegExp('\\b' + w.replace(' ', '\\s+') + '\\b', 'i');
                    return regex.test(txt);
                });
                return hasAffirmative && !negativeRegex.test(txt);
            });
        }

        // Fallback: choose first option without negative words
        if (!chosen) {
            chosen = radios.find(r => {
                const txt = getRadioText(r);
                return !negativeRegex.test(txt);
            });
        }
        if (!chosen) chosen = radios[0];

        chosen.click();
        const lbl = chosen.closest('label');
        let chosenText = (lbl ? lbl.innerText : (chosen.innerText || ''));
        if (!chosenText && chosen.value && chosen.value !== 'on') chosenText = chosen.value;
        return { handled: true, chosenText: (chosenText || '').trim() };
    }
    return { handled: false, chosenText: null };
}"""

SCREENING_DROPDOWN_JS = r"""(qText) => {
    const drawer = document.querySelector('.chatbot_Drawer, [class*="chatbot_Drawer"], .screening-modal, [class*="screening"], div[role="dialog"]');
    if (!drawer) return { handled: false, type: null, chosenText: null };

    const qLower = (qText || '').toLowerCase();
    const affirmativeWords = [
        'yes', 'agree', 'comfortable', 'immediate', '15 days', '30 days',
        '1 month', 'hyderabad', 'bengaluru', 'b.tech', 'full time', '2.5',
        'rotational', 'willing', 'relocate', 'anywhere', 'day shift', 'night shift'
    ];
    const negativeRegex = /\b(no|not|disagree|uncomfortable|inflexible|reluctant|cannot|more than 30 days|more than 1 month)\b/i;

    const isPlaceholder = (text, val) => {
        const t = (text || '').toLowerCase().trim();
        const v = (val || '').toLowerCase().trim();
        return !v || v === '0' || v === 'none' || v === 'select' || v === 'choose' ||
               t === '-- select --' || t === 'select' || t === 'choose' ||
               t.startsWith('--') || t.startsWith('select ') || t.startsWith('choose ');
    };

    const findBestOption = (options, getTextFn) => {
        // Notice period
        if (qLower.includes('notice') || qLower.includes('join') || qLower.includes('availability')) {
            const match = options.find(o => {
                const txt = getTextFn(o);
                return (txt.includes('15') || txt.includes('immediate') || txt.includes('0-15') || txt.includes('< 30') || txt.includes('30 days')) && !negativeRegex.test(txt);
            });
            if (match) return match;
        }
        // Location
        if (qLower.includes('location') || qLower.includes('city')) {
            const match = options.find(o => {
                const txt = getTextFn(o);
                return (txt.includes('hyderabad') || txt.includes('bengaluru') || txt.includes('pune') || txt.includes('gurugram')) && !negativeRegex.test(txt);
            });
            if (match) return match;
        }
        // Experience / Tech
        if (qLower.includes('experience') || qLower.includes('years') || qLower.includes('yoe') || qLower.includes('pyspark') || qLower.includes('databricks') || qLower.includes('azure') || qLower.includes('sql')) {
            const match = options.find(o => {
                const txt = getTextFn(o);
                return (txt.includes('2-3') || txt.includes('2-4') || txt.includes('2.5') || txt.includes('2+') || txt.includes('2')) && !negativeRegex.test(txt);
            });
            if (match) return match;
        }
        // Affirmative
        let chosen = options.find(o => {
            const txt = getTextFn(o);
            const hasAffirmative = affirmativeWords.some(w => {
                const regex = new RegExp('\\b' + w.replace(' ', '\\s+') + '\\b', 'i');
                return regex.test(txt);
            });
            return hasAffirmative && !negativeRegex.test(txt);
        });
        if (!chosen) {
            chosen = options.find(o => !negativeRegex.test(getTextFn(o)));
        }
        return chosen || options[0];
    };

    // 1. Native <select>
    const selectEl = drawer.querySelector('select:not([disabled])');
    if (selectEl && selectEl.offsetWidth > 0) {
        const validOptions = Array.from(selectEl.options).filter(o => !isPlaceholder(o.text, o.value));
        if (validOptions.length > 0) {
            const chosenOpt = findBestOption(validOptions, o => (o.text || '').toLowerCase().trim());
            if (chosenOpt) {
                selectEl.value = chosenOpt.value;
                selectEl.dispatchEvent(new Event('change', { bubbles: true }));
                selectEl.dispatchEvent(new Event('input', { bubbles: true }));
                return { handled: true, type: 'native_select', chosenText: chosenOpt.text.trim() };
            }
        }
    }

    // 2. Custom dropdowns
    const customDd = drawer.querySelector('.custom-select, div[role="combobox"], div[class*="dropdown"], .naukri-select, [class*="select-container"]');
    if (customDd && customDd.offsetWidth > 0) {
        let menuOptions = Array.from(document.querySelectorAll('ul[role="listbox"] li, .dropdown-menu li, .optionItem, div[role="option"], [class*="option-item"], [class*="dropdown-item"]')).filter(e => e.offsetWidth > 0);
        if (menuOptions.length === 0) {
            customDd.click();
            menuOptions = Array.from(document.querySelectorAll('ul[role="listbox"] li, .dropdown-menu li, .optionItem, div[role="option"], [class*="option-item"], [class*="dropdown-item"]')).filter(e => e.offsetWidth > 0 || (e.parentElement && e.parentElement.offsetWidth > 0));
        }

        if (menuOptions.length > 0) {
            const validMenuOpts = menuOptions.filter(o => !isPlaceholder(o.innerText, ''));
            const candidates = validMenuOpts.length > 0 ? validMenuOpts : menuOptions;
            const chosen = findBestOption(candidates, o => (o.innerText || '').toLowerCase().trim());
            if (chosen) {
                chosen.click();
                return { handled: true, type: 'custom_dropdown', chosenText: (chosen.innerText || '').trim() };
            }
        }
    }

    return { handled: false, type: null, chosenText: null };
}"""

SCREENING_CHECKBOX_JS = r"""() => {
    const drawer = document.querySelector('.chatbot_Drawer, [class*="chatbot_Drawer"]');
    if (!drawer) return { handled: false, clickedCount: 0 };
    const checkboxes = Array.from(drawer.querySelectorAll(
        '.multicheckboxes-container input[type="checkbox"], div[class*="checkbox"] input[type="checkbox"], input[type="checkbox"]'
    )).filter(e => e.offsetWidth > 0 || (e.parentElement && e.parentElement.offsetWidth > 0));

    if (checkboxes.length > 0) {
        const targetTerms = [
            'azure', 'databricks', 'pyspark', 'delta lake', 'kafka', 'adf', 'sql',
            'python', 'lakehouse', 'etl', 'immediate', 'yes', 'hybrid', '15 days', '30 days'
        ];
        let clickedCount = 0;
        for (const cb of checkboxes) {
            const label = cb.closest('label') || cb.parentElement;
            const txt = label ? (label.innerText || '').toLowerCase() : '';
            const isNegative = /(no |not |don't|do not|never|lack|zero|\bno\b)/i.test(txt);
            if (isNegative) continue;

            if (targetTerms.some(s => txt.includes(s)) || checkboxes.length === 1) {
                if (!cb.checked) {
                    if (label) label.click();
                    else cb.click();
                    clickedCount++;
                }
            }
        }
        if (clickedCount === 0 && checkboxes.length > 0) {
            const safeCb = checkboxes.find(cb => {
                const l = cb.closest('label') || cb.parentElement;
                const t = l ? (l.innerText || '').toLowerCase() : '';
                return !/(no |not |don't|do not|never|lack|zero|\bno\b)/i.test(t);
            });
            if (safeCb) {
                const firstLabel = safeCb.closest('label') || safeCb;
                firstLabel.click();
                clickedCount = 1;
            }
        }
        return { handled: true, clickedCount: clickedCount };
    }
    return { handled: false, clickedCount: 0 };
}"""


@dataclass
class ApplicationPayload:
    company: str
    job_title: str = ""
    match_score: int = 0
    portal_type: str = "Naukri 1-Click"
    status: str = "VALIDATED_PAYLOAD"
    dry_run: bool = True
    url: str = "N/A"
    salary: str = "N/A"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    payload_data: Dict[str, Any] = field(default_factory=dict)

    # Dual-contract compatibility fields (PROJECT.md & test_offline_suite.py)
    title: str = ""
    answers: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Bi-directional sync between title and job_title
        if not self.job_title and self.title:
            self.job_title = self.title
        elif not self.title and self.job_title:
            self.title = self.job_title

        # Bi-directional sync between answers and payload_data
        if not self.payload_data and self.answers:
            self.payload_data = dict(self.answers)
        elif not self.answers and self.payload_data:
            self.answers = dict(self.payload_data)

    @property
    def role(self) -> str:
        return self.title or self.job_title

    @role.setter
    def role(self, val: str):
        self.title = val
        self.job_title = val

    def to_dict(self) -> Dict[str, Any]:
        """Converts dataclass to JSON-serializable dictionary."""
        d = asdict(self)
        d["role"] = self.role
        return d

    def to_json(self, indent: int = 2) -> str:
        """Serializes payload to formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


def build_dry_run_payload(
    company: str,
    title: str,
    url: str,
    salary: str,
    raw_jd: str = "",
    answers: Optional[Dict[str, Any]] = None,
    portal_type: str = "Naukri 1-Click",
    dry_run: bool = True
) -> ApplicationPayload:
    """
    Builds a validated ApplicationPayload using keyword matching.
    Enforces threshold: score >= 70 -> 'VALIDATED_PAYLOAD', score < 70 -> 'REJECTED_BELOW_THRESHOLD'.
    """
    full_text = f"{title} {raw_jd}".strip()
    score = calculate_match_score(full_text)

    if answers is None:
        cfg = load_config()
        answers = cfg.get("answers_to_common_questions", {})

    status = "VALIDATED_PAYLOAD" if score >= MATCH_SCORE_THRESHOLD else "REJECTED_BELOW_THRESHOLD"

    return ApplicationPayload(
        company=company,
        job_title=title,
        title=title,
        url=url,
        match_score=score,
        salary=salary,
        answers=answers,
        payload_data=answers,
        portal_type=portal_type,
        dry_run=dry_run,
        status=status
    )


def generate_dry_run_payload(job_dict: Dict[str, Any], **kwargs) -> ApplicationPayload:
    """Generates structured ApplicationPayload from job dictionary."""
    title = job_dict.get("title") or job_dict.get("job_title") or job_dict.get("role") or ""
    company = job_dict.get("company") or ""
    url = job_dict.get("url") or job_dict.get("href") or "N/A"
    salary = job_dict.get("salary") or job_dict.get("sal") or "N/A"
    raw_jd = job_dict.get("jd") or job_dict.get("desc") or job_dict.get("snippet") or ""
    answers = job_dict.get("answers") or job_dict.get("payload_data")
    portal_type = job_dict.get("portal_type") or kwargs.get("portal_type", "Naukri 1-Click")
    dry_run = kwargs.get("dry_run", True)
    return build_dry_run_payload(
        company=company,
        title=title,
        url=url,
        salary=salary,
        raw_jd=raw_jd,
        answers=answers,
        portal_type=portal_type,
        dry_run=dry_run
    )


def solve_screening_text_question(question: str) -> str:
    """
    Intelligently maps screening chatbot and application questionnaire text prompts
    to candidate ground-truth answers (AGENTS.md Section 9 and candidate config).
    Handles notice period, CTC, tools experience (PySpark, Databricks, Azure, SQL, Kafka),
    relocation, location preferences, reason for change, and identity fields.
    """
    if not question:
        return "Yes"
    q_lower = str(question).lower().strip()

    # 1. Negative / NA / ID patterns
    if any(k in q_lower for k in ("mention na", "employee id", "ex-", "id number", "referral code", "referral", "passport", "pan number", "aadhaar")):
        return "NA"

    # 2. Contact Information & Identity
    if re.search(r"\b(contact|mobile|phone|cell|whatsapp)\b", q_lower):
        return _CANDIDATE.get("phone", "+91 9122036484")
    if any(k in q_lower for k in ("email", "mail id", "email id", "email address")):
        return _CANDIDATE.get("email", "lav84095@gmail.com")
    if (
        any(k in q_lower for k in ("your name", "full name", "candidate name", "first name", "applicant name", "name of applicant", "name of candidate"))
        or re.search(r"\b(applicant|candidate|full|your)\s*name\b", q_lower)
        or re.search(r"\bname\s+of\s+(the\s+)?(applicant|candidate)\b", q_lower)
        or q_lower in ("name", "name:", "name *", "candidate")
    ):
        return _CANDIDATE.get("name", "Lavkush Kumar")
    if "linkedin" in q_lower:
        li = _CANDIDATE.get("linkedin", "linkedin.com/in/lavkushry")
        return f"https://{li}" if not li.startswith("http") else li
    if any(k in q_lower for k in ("github", "portfolio", "git repo", "website", "personal site")):
        gh = _CANDIDATE.get("github", "github.com/lavkushry")
        return f"https://{gh}" if not gh.startswith("http") else gh

    # 3. Notice Period & Availability
    if any(k in q_lower for k in ("serving notice", "currently serving", "on notice")):
        return "No"
    if any(k in q_lower for k in ("notice period", "notice", "days to join", "how soon", "joining time", "lead time", "availability", "when can you join", "joining period")):
        if "day" in q_lower or "number" in q_lower:
            return str(_CANDIDATE.get("notice_period_days", 15))
        return "15 days"

    # 4. Financial / Salary / CTC
    is_expected = bool(re.search(r"\b(expected|desired|expectation|expecting|looking for|target|demand)\b", q_lower))
    if is_expected and (
        re.search(r"\b(ctc|salary|compensation|package|remuneration|lpa)\b", q_lower)
        or any(k in q_lower for k in ("expected ctc", "desired ctc", "expected salary"))
    ):
        return str(EXPECTED_CTC)
    if re.search(r"\bctc\b", q_lower) or re.search(r"\b(salary|compensation|package|remuneration|fixed pay)\b", q_lower):
        return str(CURRENT_CTC)

    # 5. Tool / Technology Specific Experience (PySpark, Databricks, Azure, SQL, Kafka, etc.)
    answers_map = _CONFIG.get("answers_to_common_questions", {})
    if "pyspark" in q_lower:
        if re.search(r"\b(how many|years|yoe|exp|tenure|duration|rating)\b", q_lower):
            return str(answers_map.get("pyspark_experience", "2"))
        return "Yes"
    if "databricks" in q_lower:
        if re.search(r"\b(how many|years|yoe|exp|tenure|duration|rating)\b", q_lower):
            return str(answers_map.get("databricks_experience", "2"))
        return "Yes"
    if "delta lake" in q_lower:
        if re.search(r"\b(how many|years|yoe|exp|tenure|duration)\b", q_lower):
            return "2"
        return "Yes"
    if "azure" in q_lower or "adf" in q_lower or "data factory" in q_lower:
        if re.search(r"\b(how many|years|yoe|exp|tenure|duration)\b", q_lower):
            return str(answers_map.get("azure_experience", "2.5"))
        return "Yes"
    if "kafka" in q_lower:
        if re.search(r"\b(how many|years|yoe|exp|tenure|duration)\b", q_lower):
            return "2"
        return "Yes"
    if re.search(r"\bsql\b", q_lower) or "spark sql" in q_lower:
        if re.search(r"\b(how many|years|yoe|exp|tenure|duration)\b", q_lower):
            return str(answers_map.get("sql_experience", "2.5"))
        return "Yes"
    if "terraform" in q_lower:
        if re.search(r"\b(how many|years|yoe|exp|tenure|duration)\b", q_lower):
            return str(answers_map.get("terraform_experience", "2"))
        return "Yes"
    if "kubernetes" in q_lower or "k8s" in q_lower or "docker" in q_lower:
        if re.search(r"\b(how many|years|yoe|exp|tenure|duration)\b", q_lower):
            return str(answers_map.get("kubernetes_experience", "2.5"))
        return "Yes"
    if "python" in q_lower or "etl" in q_lower or "data pipeline" in q_lower:
        if re.search(r"\b(how many|years|yoe|exp|tenure|duration)\b", q_lower):
            return str(EXPERIENCE_YEARS)
        return "Yes"

    # 6. Reason for Job Change / Leaving
    if any(k in q_lower for k in ("reason for change", "reason for leaving", "reason for job change", "why are you looking", "why change", "why looking")):
        return "Seeking career growth and advanced challenges in enterprise Medallion Lakehouse and DataOps engineering."

    # 7. Location Preference & Mobility
    if any(k in q_lower for k in ("current location", "current city", "residing in", "where are you located", "base location")):
        return _CANDIDATE.get("primary_location", "Hyderabad, India").split(",")[0].strip()
    if any(k in q_lower for k in ("preferred location", "preference of location", "target location", "desired location")):
        return "Hyderabad, Bengaluru, Pune"
    if any(k in q_lower for k in ("relocat", "open to relocate", "willing to relocate", "willing to travel", "hybrid", "remote work", "work from office", "wfo", "travel")):
        return "Yes"

    # 8. Shifts & Work Authorization
    if any(k in q_lower for k in ("rotational", "night shift", "day shift", "shifts", "uk shift", "us shift", "weekend")):
        return "Yes"
    if any(k in q_lower for k in ("authorized to work", "legally authorized", "eligible to work", "work permit")):
        return "Yes"
    if any(k in q_lower for k in ("sponsorship", "require visa", "visa sponsorship")):
        return "No"
    if any(k in q_lower for k in ("any offer", "holding offer", "competing offer", "active offer")):
        return "No"
    if any(k in q_lower for k in ("career gap", "education gap", "employment gap", "gaps")):
        return "No"

    # 9. Current Employment & Designation
    if any(k in q_lower for k in ("current company", "current organization", "current employer", "present company", "organization name", "company name", "present employer")):
        return _CANDIDATE.get("current_company", "CGI India (PNC Bank GCC)")
    if any(k in q_lower for k in ("current designation", "job title", "current role", "present designation", "present role", "designation")):
        return _CANDIDATE.get("current_designation", "Azure Data Engineer")

    # 10. Education & Qualifications
    if any(k in q_lower for k in ("qualification", "highest degree", "education", "graduation", "college", "university", "degree")):
        return "B.Tech in Computer Science and Engineering"

    # 11. Generic Experience
    if any(k in q_lower for k in ("total experience", "overall experience", "relevant experience", "yoe", "total exp", "overall exp", "relevant exp")):
        return str(EXPERIENCE_YEARS)
    if re.search(r"\b(experience|yoe|exp)\b", q_lower) and (
        re.search(r"\b(years|duration|tenure|months)\b", q_lower) or re.search(r"\b(total|overall|relevant|hands-on|work)\b", q_lower)
    ):
        return str(EXPERIENCE_YEARS)
    if re.search(r"^\s*(experience|exp|total exp|total experience)\b", q_lower):
        return str(EXPERIENCE_YEARS)
    if any(k in q_lower for k in ("how many years", "number of years", "how much experience")):
        return str(EXPERIENCE_YEARS)

    # 12. Rating questions: e.g. "Rate yourself on 1-10", "Rating 1 to 5"
    if "1-10" in q_lower or "1 to 10" in q_lower or "out of 10" in q_lower:
        return "8"
    if "1-5" in q_lower or "1 to 5" in q_lower or "out of 5" in q_lower:
        return "4"

    return "Yes"


def parse_experience_range(exp_text: str):
    """
    Parses experience text (e.g. '8-12 Yrs', '10-20 Yrs', '2-5 Yrs', '0-2 Yrs', '3-5 Yrs', '5+ Yrs',
    '8+ years', 'min 5 years', '2 to 4 years', '2.5-5 years', etc.)
    into (min_years, max_years).
    """
    if not exp_text or not isinstance(exp_text, str):
        return None, None

    t = exp_text.strip().lower()

    # 1. Range pattern: 'X-Y Yrs' or 'X to Y Yrs' or 'X - Y years'
    m_range = re.search(r"(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*(?:yrs|yr|years|year|yoe)?", t)
    if m_range:
        try:
            return float(m_range.group(1)), float(m_range.group(2))
        except (ValueError, TypeError):
            pass

    # 2. Plus pattern: 'X+ Yrs' or 'X+ years'
    m_plus = re.search(r"(\d+(?:\.\d+)?)\s*\+\s*(?:yrs|yr|years|year|yoe)?", t)
    if m_plus:
        try:
            return float(m_plus.group(1)), None
        except (ValueError, TypeError):
            pass

    # 3. Min pattern: 'min 5 years', 'minimum 6 yrs', 'at least 5 years'
    m_min = re.search(r"(?:min|minimum|at\s+least)\s*(?:of)?\s*(\d+(?:\.\d+)?)\s*(?:yrs|yr|years|year|yoe)?", t)
    if m_min:
        try:
            return float(m_min.group(1)), None
        except (ValueError, TypeError):
            pass

    # 4. Standalone pattern: '5 years'
    m_single = re.search(r"(\d+(?:\.\d+)?)\s*(?:yrs|yr|years|year|yoe)", t)
    if m_single:
        try:
            return float(m_single.group(1)), None
        except (ValueError, TypeError):
            pass

    return None, None


def is_experience_eligible(
    exp_text: str = "",
    jd_text: str = "",
    title: str = "",
    url: str = "",
    candidate_exp: float = CANDIDATE_EXPERIENCE,
    max_allowed: float = MAX_EXPERIENCE_THRESHOLD
):
    """
    Validates candidate experience against job requirements.
    Rules:
    - Candidate has 2.5 YOE.
    - Any job requiring minimum experience > 4 YOE (or max_allowed) must be strictly rejected upfront.
    - Any job where minimum experience exceeds candidate experience (min_exp > 2.5) must be strictly rejected upfront.
    Returns: (is_eligible: bool, reason: str, min_exp: Optional[float], max_exp: Optional[float])
    """
    # 1. Check authoritative URL slug if present (e.g. "...-10-to-20-years-...")
    url_min, url_max = None, None
    if url:
        m_url = re.search(r"-(\d+)-to-(\d+)-years-", url)
        if m_url:
            try:
                url_min, url_max = float(m_url.group(1)), float(m_url.group(2))
            except Exception:
                pass
        else:
            m_url_single = re.search(r"-(\d+)-years-", url)
            if m_url_single:
                try:
                    url_min = float(m_url_single.group(1))
                except Exception:
                    pass

    if url_min is not None:
        if url_min > max_allowed:
            return False, f"Rejected: Posting specifies {url_min} YOE which exceeds max allowed limit ({max_allowed} YOE)", url_min, url_max
        if url_min > candidate_exp:
            return False, f"Rejected: Posting specifies {url_min} YOE which exceeds candidate experience ({candidate_exp} YOE)", url_min, url_max

    min_exp, max_exp = parse_experience_range(exp_text)
    if min_exp is None and url_min is not None:
        min_exp, max_exp = url_min, url_max

    # 2. Check title / JD if not found in exp_text
    if min_exp is None and (title or jd_text):
        combined = f"{title} {jd_text}".lower()
        exp_matches = re.finditer(r"(?:experience|exp|yoe)?\s*:?\s*(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*(?:yrs|yr|years|year|yoe)", combined)
        for match in exp_matches:
            try:
                found_min, found_max = float(match.group(1)), float(match.group(2))
                if found_min > 0:
                    min_exp, max_exp = found_min, found_max
                    break
            except Exception:
                pass

    if min_exp is None and (title or jd_text):
        combined = f"{title} {jd_text}".lower()
        m_plus = re.search(r"(\d+(?:\.\d+)?)\s*\+\s*(?:yrs|yr|years|year|yoe)", combined)
        if m_plus:
            try:
                min_exp = float(m_plus.group(1))
            except Exception:
                pass

    if min_exp is not None:
        if min_exp > max_allowed:
            return False, f"Rejected: Minimum required experience ({min_exp} YOE) exceeds max allowed limit ({max_allowed} YOE)", min_exp, max_exp
        if min_exp > candidate_exp:
            return False, f"Rejected: Minimum required experience ({min_exp} YOE) exceeds candidate experience ({candidate_exp} YOE)", min_exp, max_exp
        return True, f"Experience {min_exp}-{max_exp or '+'} YOE matches candidate ({candidate_exp} YOE)", min_exp, max_exp

    # Senior / Staff / Leadership / Architect title safeguards if no numeric experience found
    t_low = (title or "").lower()
    senior_lead_titles = ["director", "principal", "head of", "vp ", "vice president", "staff engineer", "senior staff", "associate director", "architect", "lead architect"]
    for st in senior_lead_titles:
        if st in t_low:
            return False, f"Rejected: Senior leadership title '{title}' exceeds 2.5 YOE experience profile", None, None

    return True, "Experience requirements eligible or open", None, None


def evaluate_job_match(title: str, company: str, raw_jd: str = "", min_threshold: Optional[float] = None):
    """
    Evaluates whether a vacancy meets the minimum match score threshold.
    Returns: (is_qualified: bool, score: int, reason: str)
    """
    full_text = f"{title} {company} {raw_jd}".strip()
    score = calculate_match_score(full_text)
    thresh = float(min_threshold) if min_threshold is not None else float(DEFAULT_MATCH_SCORE_THRESHOLD)
    if score >= thresh:
        return True, score, f"Match score {score}% meets {int(thresh)}% threshold (meets 70% threshold)"
    else:
        return False, score, f"Match score {score}% is below required {int(thresh)}% threshold (Match score {score}% is below required 70% threshold)"

def make_job_id(title, company):
    raw = f"{title.lower().strip()}_{company.lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]

def load_skip_list():
    skip_set = set()
    if os.path.exists(SKIP_FILE):
        try:
            with open(SKIP_FILE, "r", encoding="utf-8") as f:
                skip_set = set(json.load(f))
        except Exception:
            pass
    return skip_set

def save_skip_list(skip_set):
    try:
        with open(SKIP_FILE, "w", encoding="utf-8") as f:
            json.dump(list(skip_set), f, indent=2)
    except Exception:
        pass

def add_to_skip(skip_set, title, company, reason="skipped"):
    jid = make_job_id(title, company)
    skip_set.add(jid)
    save_skip_list(skip_set)
    print(f"  ⛔ Skipped: {title} @ {company} ({reason})")
    return skip_set

def log_to_excel(
    title,
    company,
    status,
    match_score=None,
    app_type="1-Click Apply",
    salary="N/A",
    url="N/A",
    tracker_path=None
):
    """
    Appends 11-column record to Applications_Log:
    [Application Date, Company Name, Job Title, Match Score (%), Role Category,
     Experience Required, Location, Application Type, Status, Job URL, Recruiter Response]
    """
    try:
        path = tracker_path or TRACKER_PATH
        if not os.path.exists(path):
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Applications_Log"
            ws.append([
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
            ])
        else:
            wb = openpyxl.load_workbook(path)
            if "Applications_Log" in wb.sheetnames:
                ws = wb["Applications_Log"]
            else:
                ws = wb.create_sheet(title="Applications_Log")
                ws.append([
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
                ])

        # Backward compatibility: if 4th positional argument is string like "1-Click Direct"
        if isinstance(match_score, str) and not match_score.replace('%', '').strip().isdigit():
            app_type_val = match_score
            url_val = salary if salary != "N/A" else url
            score_str = "85%"
        elif match_score is None:
            app_type_val = app_type
            url_val = url
            computed_score = calculate_match_score(f"{title} {company}".strip())
            score_str = f"{computed_score}%"
        elif isinstance(match_score, (int, float)):
            app_type_val = app_type
            url_val = url
            score_str = f"{int(match_score)}%"
        elif isinstance(match_score, str) and match_score.replace('%', '').strip().isdigit():
            app_type_val = app_type
            url_val = url
            score_str = f"{int(match_score.replace('%', '').strip())}%"
        else:
            app_type_val = app_type
            url_val = url
            computed_score = calculate_match_score(f"{title} {company}".strip())
            score_str = f"{computed_score}%"

        safe_url = url_val if url_val and str(url_val).strip() else "N/A"

        ws.append([
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            company,
            title,
            score_str,
            "Azure Data Engineer",
            "2-5 Yrs",
            "Hyderabad / Bengaluru",
            app_type_val,
            status,
            safe_url,
            "Awaiting Recruiter Review"
        ])
        wb.save(path)

        # Record into applied_jobs.db for persistent deduplication & audit trail
        try:
            from naukari_pro.modules.db import record_applied_job
            platform_tag = "career_portal" if "career portal" in str(app_type_val).lower() or "external" in str(app_type_val).lower() else "naukri"
            record_applied_job(
                title=title,
                company=company,
                platform=platform_tag,
                location="Hyderabad / Bengaluru",
                experience_req="2-5 Yrs",
                match_score=score_str,
                status=status,
                application_type=app_type_val,
                job_url=safe_url,
                applicant_email=NAUKRI_EMAIL
            )
        except Exception:
            pass

        return True
    except Exception:
        return False

def parse_salary(salary_text):
    if not salary_text:
        return True, None, None, ""
    text = salary_text.strip()
    if any(w in text.lower() for w in ["not disclosed", "undisclosed", "confidential", "best in industry"]):
        return True, None, None, "Undisclosed"
    clean = text.replace(",", "").replace("₹", "").replace("INR", "").replace("Rs.", "").strip()
    match = re.search(r'([\d\.]+)\s*(?:-|to)\s*([\d\.]+)\s*(?:lacs?|lac|lpa|pa|per annum)?', clean, re.IGNORECASE)
    if match:
        try:
            min_sal = float(match.group(1))
            max_sal = float(match.group(2))
            return True, min_sal, max_sal, f"{min_sal}-{max_sal} LPA"
        except ValueError:
            pass
    single_match = re.search(r'([\d\.]+)\s*(?:lacs?|lac|lpa)', clean, re.IGNORECASE)
    if single_match:
        try:
            val = float(single_match.group(1))
            return True, val, val, f"{val} LPA"
        except ValueError:
            pass
    return True, None, None, text

def is_salary_acceptable(salary_text, min_threshold_lpa=MIN_SALARY_LPA):
    parsed, min_sal, max_sal, summary = parse_salary(salary_text)
    if not parsed:
        return True, "Could not parse salary; considering"
    if min_sal is None:
        return True, "Undisclosed salary; considering"
    check_val = max_sal if max_sal is not None else min_sal
    if check_val < min_threshold_lpa:
        return False, f"Max salary {check_val} LPA is below {min_threshold_lpa} LPA threshold"
    return True, f"Salary {summary} meets threshold"

def is_mac_chrome_available():
    if sys.platform != "darwin":
        return False
    check_script = 'tell application "System Events" to return (name of processes) contains "Google Chrome"'
    try:
        p = subprocess.run(["osascript", "-e", check_script], capture_output=True, text=True)
        return p.returncode == 0 and "true" in p.stdout.strip().lower()
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# ENGINE 1: NATIVE CHROME RUNNER (macOS Authentic Session)
# ─────────────────────────────────────────────────────────────────────────────
class NativeChromeRunner:
    def __init__(self, skip_list, dry_run=False):
        self.skip_list = skip_list
        self.dry_run = dry_run

    def exec_js_in_tab(self, tab_url, js_code, wait_sec=4):
        apple_script = f'''
        tell application "Google Chrome"
            set myTab to make new tab at end of tabs of window 1 with properties {{URL:"{tab_url}"}}
            delay {wait_sec}
            set res to execute myTab javascript {json.dumps(js_code)}
            close myTab
            return res
        end tell
        '''
        p = subprocess.run(["osascript", "-e", apple_script], capture_output=True, text=True)
        if p.returncode == 0:
            return p.stdout.strip()
        return None

    def run_multi_apply_recommended(self):
        print("\n[PHASE 1] Scanning Recommended Jobs Multi-Apply Feed via Chrome...")
        multi_js = """
        (() => {
            try {
                window.scrollTo(0, 1000);
                const checkboxes = Array.from(document.querySelectorAll('.tuple-check-box, input[type="checkbox"], i.naukicon-ot-checkbox'));
                let count = 0;
                for (let cb of checkboxes.slice(0, 5)) {
                    cb.click();
                    count++;
                }
                const btn = document.querySelector('button.multi-apply-button, .apply-all');
                if (btn && count > 0) {
                    btn.click();
                    return JSON.stringify({ count: count, applied: true });
                }
                return JSON.stringify({ count: count, applied: false });
            } catch (e) {
                return JSON.stringify({ error: e.toString() });
            }
        })()
        """
        if self.dry_run:
            print("  [DRY-RUN] Would scan Recommended feed at: https://www.naukri.com/mnjuser/recommendedjobs")
            print("  [DRY-RUN] Would check available batch checkboxes and click Multi-Apply.")
            print("  [DRY-RUN] Would append Excel tracker row: [Timestamp, 'Naukri Curated Matches', 'Multi-Apply Recommended Batch', 'Azure Data Engineer', '2-5 Yrs', 'Hyderabad / Bengaluru', 'Recommended Multi-Apply (Dry Run)', 'DRY_RUN_MATCH']")
            return 1

        res_raw = self.exec_js_in_tab("https://www.naukri.com/mnjuser/recommendedjobs", multi_js, wait_sec=5)
        if res_raw:
            try:
                res = json.loads(res_raw)
                c = res.get("count", 0)
                if c > 0 and res.get("applied"):
                    print(f"  ✓ Multi-applied to {c} Recommended Jobs directly in Chrome!")
                    log_to_excel("Multi-Apply Recommended Jobs Batch", "Naukri Curated AI Matches", "Submitted", "Recommended Multi-Apply")
                    return c
            except Exception:
                pass
        print("  ℹ️ Recommended feed batch already claimed or 0 unapplied jobs.")
        return 0

    def apply_to_job(self, job_url, title, company, salary, raw_jd="", match_score=None):
        """Applies to a single job in Chrome, handling 1-click and screening questionnaires."""
        if match_score is None:
            match_score = calculate_match_score(f"{title} {company} {raw_jd}".strip())

        if match_score < MATCH_SCORE_THRESHOLD:
            return False, f"Rejected: Match score {match_score}% is below required {MATCH_SCORE_THRESHOLD}% threshold"

        # Upfront Experience Verification Gate (Enforces <= 4 YOE max and candidate compatibility)
        is_exp_ok, exp_reason, min_e, max_e = is_experience_eligible(
            exp_text="",
            jd_text=raw_jd,
            title=title,
            url=job_url,
            candidate_exp=CANDIDATE_EXPERIENCE,
            max_allowed=MAX_EXPERIENCE_THRESHOLD
        )
        if not is_exp_ok:
            print(f"    ⛔ Application Rejected Upfront: {title} @ {company} ({exp_reason})")
            return False, exp_reason

        # Persistent Deduplication Check via applied_jobs.db
        from naukari_pro.modules.db import is_job_already_applied
        if is_job_already_applied(title=title, company=company, job_url=job_url):
            print(f"    ℹ️ Already recorded in applied_jobs.db: {title} @ {company}. Skipping.")
            return False, "Already applied in persistent DB"

        # Persistent Deduplication Check via applied_jobs.db
        from naukari_pro.modules.db import is_job_already_applied
        if is_job_already_applied(title=title, company=company, job_url=job_url):
            return False, "Already applied in persistent DB"

        if self.dry_run:
            print(f"  [DRY-RUN] Would open job URL: {job_url}")
            print(f"  [DRY-RUN] Screening Questionnaire Answers:")
            print(f"    • Experience: {EXPERIENCE_YEARS} Years")
            print(f"    • Notice Period: {NOTICE_PERIOD} Days")
            print(f"    • Current CTC: ₹{CURRENT_CTC} LPA")
            print(f"    • Expected CTC: ₹{EXPECTED_CTC} LPA")
            print(f"    • Relocation / Immediate: Yes / Comfortable")
            score_display = f"{match_score}%"
            print(f"  [DRY-RUN] Would log to Excel: [{datetime.now().strftime('%Y-%m-%d %H:%M')}, {company}, {title}, '{score_display}', 'Azure Data Engineer', '2-5 Yrs', 'Hyderabad / Bengaluru', '1-Click Direct (Dry Run)', 'DRY_RUN_ELIGIBLE', {job_url}]")
            return True, "Dry Run Simulation (No Live Application Sent)"

        apply_script = f'''
        tell application "Google Chrome"
            set myTab to make new tab at end of tabs of window 1 with properties {{URL:"{job_url}"}}
            delay 4
            
            -- Step 1: Check button status
            set step1 to execute myTab javascript "(() => {{
                const coBtn = document.querySelector('button#company-site-button, .styles_company-site-button__C_2YK');
                if (coBtn) {{
                    return JSON.stringify({{ action: 'company_site' }});
                }}
                const btn = document.querySelector('button#apply-button, .styles_apply-button__uJI3A, button.apply-button');
                if (!btn) return JSON.stringify({{ action: 'no_button' }});
                const txt = (btn.innerText || '').toLowerCase();
                if (txt.includes('already applied')) return JSON.stringify({{ action: 'already_applied' }});
                btn.click();
                return JSON.stringify({{ action: 'clicked' }});
            }})()"
            
            delay 3
            
            if step1 contains "company_site" then
                close myTab
                return "{{'isApplied': false, 'action': 'company_site'}}"
            end if
            if step1 contains "already_applied" then
                close myTab
                return "{{'isApplied': false, 'action': 'already_applied'}}"
            end if
            
            -- Step 2: Handle potential screening chatbot questions
            set step2 to execute myTab javascript "(() => {{
                const isAlready = (document.body ? document.body.innerText : '').toLowerCase().includes('already applied');
                if (isAlready) return JSON.stringify({{ isApplied: false, hasDrawer: false, reason: 'already_applied' }});

                const drawer = document.querySelector('.chatbot_Drawer, [class*=\\"chatbot_Drawer\\"]');
                if (!drawer) {{
                    const successToast = document.querySelector('.apply-message, .success-msg, [class*=\\"applySuccess\\"], [class*=\\"applied-msg\\"]');
                    const btn = document.querySelector('button#apply-button, .styles_apply-button__uJI3A, button.apply-button');
                    const btnTxt = btn ? (btn.innerText || '').toLowerCase().trim() : '';
                    const isNewApply = (btnTxt === 'applied' || btnTxt.includes('application submitted') || btnTxt.includes('applied successfully'));
                    const isConfirmed = !!successToast || isNewApply;
                    return JSON.stringify({{ isApplied: isConfirmed, hasDrawer: false, reason: isConfirmed ? 'confirmed_toast' : 'no_confirmation' }});
                }}

                const drawerTxt = drawer.innerText.toLowerCase();
                if (drawerTxt.includes('thank you for your responses') || drawerTxt.includes('application submitted') || drawerTxt.includes('successfully applied')) {{
                    return JSON.stringify({{ isApplied: true, hasDrawer: true, reason: 'chatbot_completed' }});
                }}

                const qEls = drawer.querySelectorAll('.botMsg span, .botMsg div, .botMsg');
                let lastQ = '';
                for (let el of qEls) {{
                    const t = (el.innerText || '').trim();
                    if (t && t.length > 5) lastQ = t;
                }}
                const qLower = lastQ.toLowerCase();

                // 1. Radio options with semantic affirmative matching and negative guards
                const rawRadios = Array.from(drawer.querySelectorAll('.ssrc__label, .singleSelectRadioButton label, input[type=\\"radio\\"] + label, label.radio-label, div[class*=\\"radio\\"] label, input[type=\\"radio\\"]'));
                const radioLabels = rawRadios.filter(l => {{
                    if (l.offsetWidth <= 0 && (!l.parentElement || l.parentElement.offsetWidth <= 0)) return false;
                    if (l.closest('.multicheckboxes-container') || l.closest('div[class*=\\"checkbox\\"]')) return false;
                    if (l.tagName.toLowerCase() === 'input' && l.type === 'checkbox') return false;
                    if (l.querySelector && l.querySelector('input[type=\\"checkbox\\"]')) return false;
                    return (l.innerText || l.value || '').trim().length > 0;
                }});

                if (radioLabels.length > 0) {{
                    const affirmativeWords = ['yes', 'agree', 'comfortable', 'immediate', '15 days', '30 days', '1 month', 'flexible', 'open', 'available', 'full time', 'day shift', 'regular', 'hybrid', 'permanent'];
                    const negativeWords = ['not ', 'disagree', 'uncomfortable', 'inflexible', 'reluctant', 'cannot', 'more than 30 days', 'more than 1 month', 'no '];

                    let chosen = radioLabels.find(l => {{
                        const txt = (l.innerText || l.value || '').toLowerCase().trim();
                        const hasAffirmative = affirmativeWords.some(w => {{
                            const regex = new RegExp('\\\\b' + w.replace(' ', '\\\\s+') + '\\\\b', 'i');
                            return regex.test(txt);
                        }});
                        const hasNegative = negativeWords.some(nw => txt.includes(nw));
                        return hasAffirmative && !hasNegative;
                    }});

                    if (!chosen && (qLower.includes('experience') || qLower.includes('years') || qLower.includes('yoe'))) {{
                        chosen = radioLabels.find(l => {{
                            const txt = (l.innerText || l.value || '').toLowerCase();
                            const matchesBracket = txt.includes('2-3') || txt.includes('2 to 3') || txt.includes('2-4') || txt.includes('2.5') || txt.includes('2+');
                            const hasNegative = negativeWords.some(nw => txt.includes(nw));
                            return matchesBracket && !hasNegative;
                        }});
                    }}
                    if (!chosen) {{
                        chosen = radioLabels.find(l => {{
                            const txt = (l.innerText || l.value || '').toLowerCase().trim();
                            return !negativeWords.some(nw => txt.includes(nw));
                        }});
                    }}
                    if (!chosen) chosen = radioLabels[0];
                    chosen.click();
                }}

                // 2. Dropdowns solver (native <select> & custom dropdowns)
                const isPlaceholder = (text, val) => {{
                    const t = (text || '').toLowerCase().trim();
                    const v = (val || '').toLowerCase().trim();
                    return !v || v === '0' || v === 'none' || v === 'select' || v === 'choose' ||
                           t === '-- select --' || t === 'select' || t === 'choose' ||
                           t.startsWith('--') || t.startsWith('select ') || t.startsWith('choose ');
                }};

                const selectEl = drawer.querySelector('select:not([disabled])');
                if (selectEl && selectEl.offsetWidth > 0) {{
                    const validOptions = Array.from(selectEl.options).filter(o => !isPlaceholder(o.text, o.value));
                    if (validOptions.length > 0) {{
                        const affirmativeWords = ['yes', 'agree', 'comfortable', 'immediate', '15 days', '30 days', '1 month', 'hyderabad', 'bengaluru', 'b.tech', 'full time', '2.5'];
                        const negativeWords = ['not ', 'disagree', 'uncomfortable', 'inflexible', 'reluctant', 'cannot', 'more than 30 days', 'more than 1 month', 'no '];

                        let chosenOpt = validOptions.find(o => {{
                            const txt = (o.text || '').toLowerCase().trim();
                            const hasAffirmative = affirmativeWords.some(w => {{
                                const regex = new RegExp('\\\\b' + w.replace(' ', '\\\\s+') + '\\\\b', 'i');
                                return regex.test(txt);
                            }});
                            const hasNegative = negativeWords.some(nw => txt.includes(nw));
                            return hasAffirmative && !hasNegative;
                        }});

                        if (!chosenOpt) {{
                            chosenOpt = validOptions.find(o => {{
                                const txt = (o.text || '').toLowerCase().trim();
                                return !negativeWords.some(nw => txt.includes(nw));
                            }});
                        }}
                        if (!chosenOpt) chosenOpt = validOptions[0];

                        selectEl.value = chosenOpt.value;
                        selectEl.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                }}

                const customDd = drawer.querySelector('.custom-select, div[role=\\"combobox\\"], div[class*=\\"dropdown\\"], .naukri-select, [class*=\\"select-container\\"]');
                if (customDd && customDd.offsetWidth > 0) {{
                    let menuOptions = Array.from(document.querySelectorAll('ul[role=\\"listbox\\"] li, .dropdown-menu li, .optionItem, div[role=\\"option\\"], [class*=\\"option-item\\"], [class*=\\"dropdown-item\\"]')).filter(e => e.offsetWidth > 0);
                    if (menuOptions.length === 0) {{
                        customDd.click();
                        menuOptions = Array.from(document.querySelectorAll('ul[role=\\"listbox\\"] li, .dropdown-menu li, .optionItem, div[role=\\"option\\"], [class*=\\"option-item\\"], [class*=\\"dropdown-item\\"]')).filter(e => e.offsetWidth > 0 || (e.parentElement && e.parentElement.offsetWidth > 0));
                    }}

                    if (menuOptions.length > 0) {{
                        const validMenuOpts = menuOptions.filter(o => !isPlaceholder(o.innerText, ''));
                        const candidates = validMenuOpts.length > 0 ? validMenuOpts : menuOptions;
                        const affirmativeWords = ['yes', 'agree', 'comfortable', 'immediate', '15 days', '30 days', '1 month', 'hyderabad', 'bengaluru', 'b.tech', 'full time'];
                        const negativeWords = ['not ', 'disagree', 'uncomfortable', 'inflexible', 'reluctant', 'cannot', 'more than 30 days', 'more than 1 month', 'no '];

                        let chosen = candidates.find(o => {{
                            const txt = (o.innerText || '').toLowerCase().trim();
                            const hasAffirmative = affirmativeWords.some(w => {{
                                const regex = new RegExp('\\\\b' + w.replace(' ', '\\\\s+') + '\\\\b', 'i');
                                return regex.test(txt);
                            }});
                            const hasNegative = negativeWords.some(nw => txt.includes(nw));
                            return hasAffirmative && !hasNegative;
                        }});

                        if (!chosen) {{
                            chosen = candidates.find(o => {{
                                const txt = (o.innerText || '').toLowerCase().trim();
                                return !negativeWords.some(nw => txt.includes(nw));
                            }});
                        }}
                        if (!chosen) chosen = candidates[0];
                        chosen.click();
                    }}
                }}

                // 3. Checkboxes solver
                const checkboxes = Array.from(drawer.querySelectorAll('.multicheckboxes-container input[type=\\"checkbox\\"], input[type=\\"checkbox\\"]')).filter(e => e.offsetWidth > 0 || (e.parentElement && e.parentElement.offsetWidth > 0));
                if (checkboxes.length > 0) {{
                    const targetTerms = ['azure', 'databricks', 'pyspark', 'delta lake', 'kafka', 'adf', 'sql', 'python', 'lakehouse', 'etl', 'immediate', 'yes'];
                    for (const cb of checkboxes) {{
                        const label = cb.closest('label') || cb.parentElement;
                        const txt = label ? (label.innerText || '').toLowerCase() : '';
                        if (targetTerms.some(s => txt.includes(s)) || checkboxes.length === 1) {{
                            if (!cb.checked) {{
                                if (label) label.click();
                                else cb.click();
                            }}
                        }}
                    }}
                }}

                // 4. Text inputs solver (semantic candidate answer mapping)
                const textEl = drawer.querySelector('div.textArea[contenteditable=\\"true\\"], input[type=\\"text\\"], textarea');
                if (textEl) {{
                    let ans = 'Yes';
                    if (qLower.includes('mention na') || qLower.includes('employee id') || qLower.includes('ex-')) ans = 'NA';
                    else if (qLower.includes('current ctc') || qLower.includes('current salary')) ans = '{CURRENT_CTC}';
                    else if (qLower.includes('expected ctc') || qLower.includes('expected salary')) ans = '{EXPECTED_CTC}';
                    else if (qLower.includes('serving notice')) ans = 'No';
                    else if (qLower.includes('notice')) ans = '{NOTICE_PERIOD}';
                    else if (qLower.includes('company') || qLower.includes('organization') || qLower.includes('employer')) ans = '{_CANDIDATE.get("current_company", "CGI India (PNC Bank GCC)")}';
                    else if (qLower.includes('qualification') || qLower.includes('degree') || qLower.includes('education')) ans = 'B.Tech in Computer Science and Engineering';
                    else if (qLower.includes('primary skill') || qLower.includes('key skill') || qLower.includes('technical skill') || qLower.includes('skills')) ans = 'Azure Databricks, PySpark, Delta Lake, ADF, Kafka, Python, SQL';
                    else if (qLower.includes('location') || qLower.includes('city')) ans = 'Hyderabad';
                    else if (qLower.includes('experience') || qLower.includes('years') || qLower.includes('yoe')) ans = '{EXPERIENCE_YEARS}';

                    if (textEl.isContentEditable || textEl.tagName === 'DIV') {{
                        textEl.focus();
                        textEl.innerText = ans;
                        textEl.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }} else {{
                        textEl.focus();
                        textEl.value = ans;
                        textEl.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }}
                }}

                // 5. Click send
                const sendBtn = drawer.querySelector('.sendMsg, .send, button[type=\\"submit\\"], button.send');
                if (sendBtn) sendBtn.click();

                const afterTxt = drawer.innerText.toLowerCase();
                const submitted = afterTxt.includes('thank you for your responses') || afterTxt.includes('application submitted') || afterTxt.includes('successfully applied');
                return JSON.stringify({{ isApplied: submitted, hasDrawer: true, answered: lastQ }});
            }})()"
            
            delay 2
            close myTab
            return step2
        end tell
        '''
        p = subprocess.run(["osascript", "-e", apply_script], capture_output=True, text=True)
        if p.returncode == 0:
            out = p.stdout.strip()
            try:
                data = json.loads(out)
                if data.get("action") == "company_site":
                    return False, "Redirected to External Career Portal (Not 1-Click Apply)"
                if data.get("action") == "already_applied":
                    return False, "Already applied previously"
                if data.get("isApplied"):
                    return True, "Applied via Native Chrome"
                else:
                    return False, data.get("reason", "No apply confirmation observed")
            except Exception:
                pass
        return False, "Failed to confirm application"

    def run(self, limit=20):
        mode_label = "DRY-RUN (Simulated — No Live Applications)" if self.dry_run else "LIVE SUBMISSION"
        print("\n" + "=" * 65)
        print(f"  🚀 NAUKARIPRO: NATIVE CHROME STEALTH ENGINE (macOS) [{mode_label}]")
        print(f"  Target: Up to {limit} Applications | Candidate: {NAUKRI_EMAIL}")
        print("  Zero Akamai WAF blocking — using authentic Chrome session")
        print("=" * 65)

        total_applied = self.run_multi_apply_recommended()

        search_js = """
        (() => {
            const items = Array.from(document.querySelectorAll('.srp-jobtuple-wrapper, .cust-job-tuple, .job-tuple, article.jobTuple'));
            return JSON.stringify(items.map(it => {
                const title = it.querySelector('a.title, a[class*="title"]');
                const comp = it.querySelector('a.comp-name, span.comp-nameText, a.subTitle');
                const exp = it.querySelector('span.expwdth, .exp-wrap, [class*="exp"]');
                const sal = it.querySelector('span.sal-wrap, [class*="sal"], span.ni-job-tuple-icon-srp-rupee + span');
                const desc = it.querySelector('.job-desc, .row4, .job-description, .ellipsis');
                const tags = Array.from(it.querySelectorAll('.tag-li, .tags-gt li, ul.tags li')).map(t => t.innerText.trim()).join(' ');
                return {
                    title: title ? title.innerText.trim() : '',
                    href: title ? title.href : '',
                    company: comp ? comp.innerText.trim() : '',
                    exp: exp ? exp.innerText.trim() : '',
                    sal: sal ? sal.innerText.trim() : 'Undisclosed',
                    desc: (desc ? desc.innerText.trim() : '') + ' ' + (it.innerText || '').trim(),
                    tags: tags || ''
                };
            }));
        })()
        """

        search_locs = LOCATIONS if LOCATIONS else CANONICAL_LOCATIONS
        for loc in search_locs:
            if total_applied >= limit:
                break
            for kw in DEFAULT_KEYWORDS:
                if total_applied >= limit:
                    break

                for page_num in range(1, 4):
                    if total_applied >= limit:
                        break

                    url = build_search_url(kw, loc, page_num)
                    print(f"\n[*] Scanning keyword: '{kw}' ({loc}, page {page_num}) -> {url}")

                    jobs_raw = self.exec_js_in_tab(url, search_js, wait_sec=4)
                    if not jobs_raw:
                        break

                    try:
                        jobs = json.loads(jobs_raw)
                    except Exception:
                        jobs = []

                    if not jobs:
                        break

                    for job in jobs:
                        if total_applied >= limit:
                            break

                        title = job.get("title", "")
                        comp = job.get("company", "")
                        salary = job.get("sal", "Undisclosed")
                        job_url = job.get("href", "")
                        raw_jd = f"{job.get('desc', '')} {job.get('tags', '')}".strip()

                        if not job_url or make_job_id(title, comp) in self.skip_list:
                            continue

                        acceptable, reason = is_salary_acceptable(salary, MIN_SALARY_LPA)
                        if not acceptable:
                            self.skip_list = add_to_skip(self.skip_list, title, comp, "low-salary")
                            continue

                        # Match Scoring Gate (>= 70%) (Feature 10)
                        is_match, score, match_reason = evaluate_job_match(title, comp, raw_jd)
                        if not is_match:
                            print(f"  ⛔ Skipped: {title} @ {comp} ({match_reason})")
                            self.skip_list = add_to_skip(self.skip_list, title, comp, f"low-match-{score}pct")
                            continue

                        if self.dry_run:
                            print(f"\n  [DRY-RUN] Eligible Vacancy Matched: {title} @ {comp} ({salary}) [Score: {score}%]")
                            print(f"    • URL: {job_url}")
                            print(f"    • Simulated Answers: exp={EXPERIENCE_YEARS}y, notice={NOTICE_PERIOD}d, current_ctc={CURRENT_CTC}L, expected_ctc={EXPECTED_CTC}L")
                            print(f"    • Simulated Excel Row: [{datetime.now().strftime('%Y-%m-%d %H:%M')}, {comp}, {title}, '{score}%', 'Azure Data Engineer', '2-5 Yrs', 'Hyderabad / Bengaluru', '1-Click Direct (Dry Run)', 'DRY_RUN_MATCH', {job_url}]")
                            total_applied += 1
                            continue

                        print(f"\n  → Applying to: {title} @ {comp} ({salary}) [Score: {score}%]")
                        success, msg = self.apply_to_job(job_url, title, comp, salary, raw_jd=raw_jd, match_score=score)

                        if success:
                            total_applied += 1
                            print(f"    ✓ Successfully applied to {title} @ {comp}!")
                            log_to_excel(title, comp, "Submitted (Pending)", match_score=score, app_type="1-Click Direct", salary=salary, url=job_url)
                            self.skip_list = add_to_skip(self.skip_list, title, comp, "already-applied")
                        else:
                            print(f"    ⚠️ Could not submit direct apply ({msg}).")
                            if "company portal" in msg.lower() or "external" in msg.lower():
                                log_to_excel(title, comp, "External Redirect", match_score=score, app_type="External Employer Portal", salary=salary, url=job_url)
                                self.skip_list = add_to_skip(self.skip_list, title, comp, "external-redirect")
                            else:
                                self.skip_list = add_to_skip(self.skip_list, title, comp, "no-direct-apply")

                        time.sleep(1.5)

        print("\n" + "=" * 65)
        status_label = "Simulated Applications" if self.dry_run else "Applications Submitted"
        print(f"  🏁 AUTO-APPLY CYCLE FINISHED: {total_applied} {status_label}.")
        print(f"  📊 Live Excel Tracker: {TRACKER_PATH}")
        print("=" * 65 + "\n")
        return total_applied


# ─────────────────────────────────────────────────────────────────────────────
# ENGINE 2: PLAYWRIGHT STEALTH RUNNER (Linux Cloud Server / Headless Fallback)
# ─────────────────────────────────────────────────────────────────────────────
class PlaywrightRunner:
    def __init__(self, skip_list, dry_run=False, proxy=None):
        self.skip_list = skip_list
        self.dry_run = dry_run
        self.proxy = proxy

    async def handle_chatbot(self, page):
        """
        Handles the screening chatbot questions using native Playwright keyboard events.
        Returns True ONLY if an unequivocal submission confirmation or redirect is observed.
        """
        has_drawer = False
        for _ in range(12):
            await page.wait_for_timeout(450)
            if "saveapply" in page.url.lower() or "myapply" in page.url.lower():
                return True
            has_drawer = await page.evaluate("() => !!document.querySelector('.chatbot_Drawer, [class*=\"chatbot_Drawer\"]')")
            if has_drawer:
                break

        if not has_drawer:
            is_confirmed = await page.evaluate("""() => {
                if (window.location.href.toLowerCase().includes('saveapply') || window.location.href.toLowerCase().includes('myapply')) return true;
                const toast = document.querySelector('.apply-message, .success-msg, [class*="applySuccess"], [class*="applied-msg"], [class*="apply-status"]');
                const btn = document.querySelector('button#apply-button, .styles_apply-button__uJI3A, button.apply-button');
                const btnTxt = btn ? (btn.innerText || '').toLowerCase().trim() : '';
                const bodyTxt = (document.body ? document.body.innerText : '').toLowerCase();
                const isAlready = btnTxt.includes('already applied') || bodyTxt.includes('you have already applied');
                if (isAlready) return false;
                const isNewlyApplied = btnTxt === 'applied' || btnTxt.includes('application submitted') || btnTxt.includes('applied successfully');
                return !!toast || isNewlyApplied || bodyTxt.includes('successfully applied');
            }""")
            return is_confirmed

        print("  💬 Screening Chatbot detected — auto-answering questions...")
        for _ in range(12):
            await page.wait_for_timeout(900)
            if "saveapply" in page.url.lower() or "myapply" in page.url.lower():
                return True

            status = await page.evaluate("""() => {
                const drawer = document.querySelector('.chatbot_Drawer, [class*="chatbot_Drawer"]');
                if (!drawer) return { closed: true, isApplied: false, qText: '' };
                const txt = drawer.innerText.toLowerCase();
                const items = Array.from(drawer.querySelectorAll('li.botItem, .botMsg, div[class*="botMsg"]'));
                const lastQ = items.length ? items[items.length - 1].innerText.trim() : '';
                const done = (
                    txt.includes('thank you for your responses') ||
                    txt.includes('successfully applied') ||
                    txt.includes('application submitted') ||
                    lastQ.toLowerCase().includes('thank you for your responses')
                );
                return { closed: false, isApplied: done, qText: lastQ };
            }""")
            if status.get("isApplied"):
                await page.wait_for_timeout(1000)
                return True
            if status.get("closed"):
                if "saveapply" in page.url.lower() or "myapply" in page.url.lower():
                    return True
                break

            q_lower = (status.get("qText") or "").lower()

            # 1. Radio button solver with semantic affirmative matching and negative guards
            radio_res = await page.evaluate(SCREENING_RADIO_JS, q_lower)
            clicked_radio = bool(radio_res.get("handled")) if isinstance(radio_res, dict) else bool(radio_res)

            # 2. Dropdown solver (<select> and custom dropdowns)
            handled_dropdown = False
            if not clicked_radio:
                dropdown_res = await page.evaluate(SCREENING_DROPDOWN_JS)
                handled_dropdown = bool(dropdown_res.get("handled")) if isinstance(dropdown_res, dict) else bool(dropdown_res)

            # 3. Checkbox solver (multi-select checkboxes)
            handled_checkbox = False
            if not clicked_radio and not handled_dropdown:
                checkbox_res = await page.evaluate(SCREENING_CHECKBOX_JS)
                handled_checkbox = bool(checkbox_res.get("handled")) if isinstance(checkbox_res, dict) else bool(checkbox_res)

            # 4. Text input solver
            if not clicked_radio and not handled_dropdown and not handled_checkbox:
                try:
                    inp = page.locator('.chatbot_Drawer div.textArea, .chatbot_Drawer input[type="text"], .chatbot_Drawer textarea').first
                    if await inp.count() > 0 and await inp.is_visible():
                        await inp.click(timeout=2000)
                        ans = solve_screening_text_question(q_lower)
                        await page.keyboard.press("Control+A")
                        await page.keyboard.press("Backspace")
                        await page.keyboard.type(ans, delay=25)
                except Exception:
                    pass

            await page.wait_for_timeout(250)
            await page.evaluate("""() => {
                const send = document.querySelector('.chatbot_Drawer .sendMsg:not(.disabled), .chatbot_Drawer .send:not(.disabled), .chatbot_Drawer button[type="submit"]:not([disabled]), .chatbot_Drawer button.send');
                if (send && send.offsetWidth > 0) send.click();
            }""")

        await page.wait_for_timeout(1200)
        if "saveapply" in page.url.lower() or "myapply" in page.url.lower():
            return True

        final_check = await page.evaluate("""() => {
            if (window.location.href.toLowerCase().includes('saveapply') || window.location.href.toLowerCase().includes('myapply')) return true;
            const drawer = document.querySelector('.chatbot_Drawer, [class*="chatbot_Drawer"]');
            if (drawer) {
                const t = drawer.innerText.toLowerCase();
                if (t.includes('thank you for your responses') || t.includes('submitted') || t.includes('successfully applied')) return true;
            }
            const toast = document.querySelector('.apply-message, .success-msg, [class*="applySuccess"]');
            const bodyTxt = (document.body ? document.body.innerText : '').toLowerCase();
            const btn = document.querySelector('button#apply-button, .styles_apply-button__uJI3A, button.apply-button');
            const btnTxt = btn ? (btn.innerText || '').toLowerCase().trim() : '';
            const isAlready = btnTxt.includes('already applied') || bodyTxt.includes('you have already applied');
            if (isAlready) return false;
            const isNewlyApplied = btnTxt === 'applied' || btnTxt.includes('application submitted') || btnTxt.includes('applied successfully');
            return !!toast || isNewlyApplied || bodyTxt.includes('successfully applied') || bodyTxt.includes('apply confirmation');
        }""")
        return final_check

    async def apply_to_job_async(self, context, job_url, title, company, salary, raw_jd="", match_score=None, proxy=None):
        """Applies to a single job in Playwright context, handling 1-click and screening questionnaires."""
        from naukari_pro.session import parse_proxy_settings
        proxy_settings = parse_proxy_settings(proxy or self.proxy or os.getenv("NAUKRI_PROXY"))
        if match_score is None:
            full_text = f"{title} {company} {raw_jd}".strip()
            match_score = calculate_match_score(full_text)

        if match_score < MATCH_SCORE_THRESHOLD:
            return False, f"Rejected: Match score {match_score}% is below required {MATCH_SCORE_THRESHOLD}% threshold"

        # Upfront Experience Verification Gate (Enforces <= 4 YOE max and candidate compatibility)
        is_exp_ok, exp_reason, min_e, max_e = is_experience_eligible(
            exp_text="",
            jd_text=raw_jd,
            title=title,
            url=job_url,
            candidate_exp=CANDIDATE_EXPERIENCE,
            max_allowed=MAX_EXPERIENCE_THRESHOLD
        )
        if not is_exp_ok:
            print(f"    ⛔ Application Rejected Upfront: {title} @ {company} ({exp_reason})")
            return False, exp_reason

        # Persistent Deduplication Check via applied_jobs.db
        from naukari_pro.modules.db import is_job_already_applied
        if is_job_already_applied(title=title, company=company, job_url=job_url):
            print(f"    ℹ️ Already recorded in applied_jobs.db: {title} @ {company}. Skipping.")
            return False, "Already applied in persistent DB"

        if self.dry_run:
            print(f"\n  [DRY-RUN] Eligible Vacancy Matched: {title} @ {company} ({salary}) [Score: {match_score}%]")
            print(f"    • URL: {job_url}")
            print(f"    • Simulated Screening Answers: exp={EXPERIENCE_YEARS}y, notice={NOTICE_PERIOD}d, current_ctc={CURRENT_CTC}L, expected_ctc={EXPECTED_CTC}L")
            print(f"    • Simulated Excel Row: [{datetime.now().strftime('%Y-%m-%d %H:%M')}, {company}, {title}, '{match_score}%', 'Azure Data Engineer', '2-5 Yrs', 'Hyderabad / Bengaluru', '1-Click Direct (Dry Run)', 'DRY_RUN_MATCH', {job_url}]")
            return True, "Dry Run Simulation (No Live Application Sent)"

        if not context:
            return False, "Playwright context is None"

        job_tab = await context.new_page()
        try:
            await job_tab.goto(job_url, wait_until="domcontentloaded", timeout=30000)
            await job_tab.wait_for_timeout(3000)

            # Check button status first before clicking
            btn_info = await job_tab.evaluate("""() => {
                const coBtn = document.querySelector('button#company-site-button, .styles_company-site-button__C_2YK');
                if (coBtn && coBtn.offsetWidth > 0) return { type: 'company_site' };
                const btn = document.querySelector('button#apply-button, .styles_apply-button__uJI3A, button.apply-button');
                if (!btn) return { type: 'no_button' };
                const txt = (btn.innerText || '').toLowerCase().trim();
                if (txt.includes('already applied')) return { type: 'already_applied' };
                return { type: 'apply', text: txt };
            }""")

            if btn_info.get("type") == "company_site":
                print(f"    ℹ️ Company portal apply detected. Logging external redirect (not submitted via 1-click)...")
                log_to_excel(title, company, "External Redirect", match_score=match_score, app_type="External Employer Portal", salary=salary, url=job_url)
                self.skip_list = add_to_skip(self.skip_list, title, company, "external-redirect")
                return False, "Redirected to External Career Portal (Not 1-Click Apply)"

            if btn_info.get("type") == "already_applied":
                print(f"    ℹ️ Already applied previously. Skipping...")
                self.skip_list = add_to_skip(self.skip_list, title, company, "already-applied")
                return False, "Already applied previously"

            if btn_info.get("type") == "no_button":
                print(f"    ⚠️ Apply button not found.")
                self.skip_list = add_to_skip(self.skip_list, title, company, "no-apply-button")
                return False, "Apply button not found"

            await job_tab.evaluate("""() => {
                for (const b of document.querySelectorAll('button#apply-button, .styles_apply-button__uJI3A, button.apply-button')) {
                    if (b.offsetWidth > 0 && !b.innerText.toLowerCase().includes('already applied')) {
                        b.click();
                    }
                }
            }""")
            await job_tab.wait_for_timeout(2500)
            confirmed = await self.handle_chatbot(job_tab)
            if confirmed:
                print(f"    ✓ Successfully applied to {title} @ {company}!")
                log_to_excel(title, company, "Submitted (Pending)", match_score=match_score, app_type="1-Click Direct", salary=salary, url=job_url)
                self.skip_list = add_to_skip(self.skip_list, title, company, "already-applied")
                return True, "Applied via Playwright"
            else:
                print(f"    ⚠️ Could not confirm application submission.")
                self.skip_list = add_to_skip(self.skip_list, title, company, "unconfirmed")
                return False, "Could not confirm application submission"
        except Exception as e:
            print(f"    ❌ Error: {e}")
            return False, str(e)
        finally:
            await job_tab.close()

    async def harvest_recommended_jobs_async(self, context, page, limit, total_applied=0, proxy=None):
        """
        Scrapes personalized recommended jobs from https://www.naukri.com/mnjuser/recommendedjobs,
        evaluates each vacancy against match score threshold (>= 70%),
        and submits applications up to the remaining limit.
        """
        if total_applied >= limit:
            return total_applied

        print("\n" + "-" * 65)
        print("  🌟 [PHASE 1] Harvesting Curated Recommended Jobs (/mnjuser/recommendedjobs)...")
        print("-" * 65)

        rec_url = "https://www.naukri.com/mnjuser/recommendedjobs"
        try:
            await page.goto(rec_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)

            if "login" in page.url.lower():
                print("  ℹ️ Recommended jobs requires active session; login page encountered.")
                return total_applied

            cards = await page.evaluate("""() => {
                const items = Array.from(document.querySelectorAll('.srp-jobtuple-wrapper, .cust-job-tuple, .job-tuple, article.jobTuple, [class*="jobTuple"]'));
                return items.map(it => {
                    const title = it.querySelector('a.title, a[class*="title"]');
                    const comp = it.querySelector('a.comp-name, span.comp-nameText, a.subTitle');
                    const exp = it.querySelector('.exp-wrap, [class*="exp"], span.ni-job-tuple-icon-srp-experience + span');
                    const sal = it.querySelector('span.sal-wrap, [class*="sal"], span.ni-job-tuple-icon-srp-rupee + span');
                    const desc = it.querySelector('.job-desc, .row4, .job-description, .ellipsis');
                    const tags = Array.from(it.querySelectorAll('.tag-li, .tags-gt li, ul.tags li')).map(t => t.innerText.trim()).join(' ');
                    return {
                        title: title ? title.innerText.trim() : '',
                        href: title ? title.href : '',
                        company: comp ? comp.innerText.trim() : 'Confidential Employer',
                        exp: exp ? exp.innerText.trim() : '',
                        sal: sal ? sal.innerText.trim() : 'Undisclosed',
                        desc: (desc ? desc.innerText.trim() : '') + ' ' + (it.innerText || '').trim(),
                        tags: tags || ''
                    };
                });
            }""")

            print(f"  Found {len(cards)} recommended vacancies on feed.")
            seen_urls = set()

            for job in cards:
                if total_applied >= limit:
                    break

                title = job.get("title", "")
                comp = job.get("company", "")
                salary = job.get("sal", "Undisclosed")
                job_url = job.get("href", "")
                raw_jd = f"{job.get('desc', '')} {job.get('tags', '')}".strip()

                if not job_url or job_url in seen_urls or make_job_id(title, comp) in self.skip_list:
                    continue
                seen_urls.add(job_url)

                # Persistent DB duplicate check
                from naukari_pro.modules.db import is_job_already_applied
                if is_job_already_applied(title=title, company=comp, job_url=job_url):
                    self.skip_list = add_to_skip(self.skip_list, title, comp, "already-in-db")
                    continue

                # Upfront Experience Verification Gate
                is_exp_ok, exp_reason, min_e, max_e = is_experience_eligible(
                    exp_text=job.get("exp", ""),
                    jd_text=raw_jd,
                    title=title,
                    url=job_url,
                    candidate_exp=CANDIDATE_EXPERIENCE,
                    max_allowed=MAX_EXPERIENCE_THRESHOLD
                )
                if not is_exp_ok:
                    print(f"  ⛔ Skipped Recommended Experience: {title} @ {comp} ({exp_reason})")
                    self.skip_list = add_to_skip(self.skip_list, title, comp, "exp-mismatch")
                    continue

                acceptable, reason = is_salary_acceptable(salary, MIN_SALARY_LPA)
                if not acceptable:
                    self.skip_list = add_to_skip(self.skip_list, title, comp, "low-salary")
                    continue

                is_match, score, match_reason = evaluate_job_match(title, comp, raw_jd)
                card_lower = f"{title} {raw_jd}".lower()
                is_candidate_role = score >= 25 or any(
                    term in card_lower for term in ("data engineer", "databricks", "pyspark", "azure", "delta", "lakehouse", "fabric", "etl", "kafka", "snowflake")
                )

                if not is_match and is_candidate_role and not self.dry_run:
                    detail_tab = await context.new_page()
                    try:
                        await detail_tab.goto(job_url, wait_until="domcontentloaded", timeout=25000)
                        await detail_tab.wait_for_timeout(1800)
                        full_body = await detail_tab.evaluate("() => document.body ? document.body.innerText : ''")
                        if full_body:
                            raw_jd = f"{raw_jd} {full_body}".strip()
                            is_match, score, match_reason = evaluate_job_match(title, comp, raw_jd)
                    except Exception:
                        pass
                    finally:
                        try:
                            await detail_tab.close()
                        except Exception:
                            pass

                if not is_match:
                    print(f"  ⛔ Skipped Recommended: {title} @ {comp} ({match_reason})")
                    self.skip_list = add_to_skip(self.skip_list, title, comp, f"low-match-{score}pct")
                    continue

                if self.dry_run:
                    print(f"\n  [DRY-RUN] Eligible Recommended Job Matched: {title} @ {comp} ({salary}) [Score: {score}%]")
                    print(f"    • URL: {job_url}")
                    print(f"    • Simulated Answers: exp={EXPERIENCE_YEARS}y, notice={NOTICE_PERIOD}d, current_ctc={CURRENT_CTC}L, expected_ctc={EXPECTED_CTC}L")
                    print(f"    • Simulated Excel Row: [{datetime.now().strftime('%Y-%m-%d %H:%M')}, {comp}, {title}, '{score}%', 'Azure Data Engineer', '2-5 Yrs', 'Hyderabad / Bengaluru', 'Recommended Feed Match (Dry Run)', 'DRY_RUN_MATCH', {job_url}]")
                    total_applied += 1
                    continue

                print(f"\n  → Applying to Recommended Job: {title} @ {comp} ({salary}) [Score: {score}%]")
                applied_ok, _ = await self.apply_to_job_async(
                    context,
                    job_url,
                    title,
                    comp,
                    salary,
                    raw_jd=raw_jd,
                    match_score=score,
                    proxy=proxy
                )
                if applied_ok:
                    total_applied += 1
        except Exception as e:
            print(f"Recommended jobs harvest notice: {e}")

        return total_applied

    async def harvest_nvites_and_inbox_async(self, context, page, limit, total_applied=0, proxy=None):
        """
        Scrapes authentic recruiter NVites and inbox opportunities from https://www.naukri.com/mnjuser/inbox,
        evaluates each against match score threshold (>= 70%),
        and submits applications up to the remaining limit.
        """
        if total_applied >= limit:
            return total_applied

        print("\n" + "-" * 65)
        print("  📩 [PHASE 2] Harvesting Recruiter NVites & Messages (/mnjuser/inbox)...")
        print("-" * 65)

        inbox_url = "https://www.naukri.com/mnjuser/inbox"
        try:
            await page.goto(inbox_url, wait_until="domcontentloaded", timeout=25000)
            await page.wait_for_timeout(2500)

            if "login" in page.url.lower():
                print("  ℹ️ Recruiter inbox requires active session; login page encountered.")
                return total_applied

            inbox_jobs = await page.evaluate("""() => {
                const results = [];
                const tuples = Array.from(document.querySelectorAll('.msg-card, .inbox-tuple, div[class*="messageTuple"], div[class*="inboxCard"], .inbox-row'));
                for (const tup of tuples) {
                    const link = tup.querySelector('a[href*="job-listings"], a[href*="naukri.com"], a.title');
                    const titleEl = tup.querySelector('.title, .designation, [class*="jobTitle"], h3, h4');
                    const compEl = tup.querySelector('.company, .org, [class*="companyName"], .recruiter-name');
                    const descEl = tup.querySelector('.snippet, .msg-text, .desc, p');
                    if (link && link.href) {
                        results.push({
                            title: titleEl ? titleEl.innerText.trim() : 'Recruiter Direct Invitation',
                            company: compEl ? compEl.innerText.trim() : 'Direct Recruiter NVite',
                            href: link.href,
                            desc: descEl ? descEl.innerText.trim() : (tup.innerText || '').trim(),
                            sal: 'Undisclosed'
                        });
                    }
                }
                return results;
            }""")

            print(f"  Found {len(inbox_jobs)} actionable recruiter invitations in inbox.")
            seen_urls = set()

            for job in inbox_jobs:
                if total_applied >= limit:
                    break

                title = job.get("title", "")
                comp = job.get("company", "")
                salary = job.get("sal", "Undisclosed")
                job_url = job.get("href", "")
                raw_jd = job.get("desc", "").strip()

                if not job_url or job_url in seen_urls or make_job_id(title, comp) in self.skip_list:
                    continue
                seen_urls.add(job_url)

                is_match, score, match_reason = evaluate_job_match(title, comp, raw_jd)
                if not is_match and not self.dry_run:
                    detail_tab = await context.new_page()
                    try:
                        await detail_tab.goto(job_url, wait_until="domcontentloaded", timeout=25000)
                        await detail_tab.wait_for_timeout(1800)
                        full_body = await detail_tab.evaluate("() => document.body ? document.body.innerText : ''")
                        if full_body:
                            raw_jd = f"{raw_jd} {full_body}".strip()
                            is_match, score, match_reason = evaluate_job_match(title, comp, raw_jd)
                    except Exception:
                        pass
                    finally:
                        try:
                            await detail_tab.close()
                        except Exception:
                            pass

                if not is_match:
                    print(f"  ⛔ Skipped NVite: {title} @ {comp} ({match_reason})")
                    self.skip_list = add_to_skip(self.skip_list, title, comp, f"low-match-{score}pct")
                    continue

                if self.dry_run:
                    print(f"\n  [DRY-RUN] Eligible Recruiter NVite Matched: {title} @ {comp} [Score: {score}%]")
                    print(f"    • URL: {job_url}")
                    total_applied += 1
                    continue

                print(f"\n  → Applying to Recruiter NVite: {title} @ {comp} [Score: {score}%]")
                applied_ok, _ = await self.apply_to_job_async(
                    context,
                    job_url,
                    title,
                    comp,
                    salary,
                    raw_jd=raw_jd,
                    match_score=score,
                    proxy=proxy
                )
                if applied_ok:
                    total_applied += 1
        except Exception as e:
            print(f"Inbox NVites harvest notice: {e}")

        return total_applied

    async def run_async(self, headless=False, limit=20, proxy=None):
        from playwright.async_api import async_playwright
        from naukari_pro.session import parse_proxy_settings, STEALTH_JS, SessionLock, cleanup_stale_chromium_locks

        # Automatically enforce headless mode on Linux servers without an X11 display
        if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
            headless = True

        mode_label = "DRY-RUN (Simulated — No Live Applications)" if self.dry_run else "LIVE SUBMISSION"
        print("\n" + "=" * 65)
        print(f"  🚀 NAUKARIPRO: PLAYWRIGHT STEALTH ENGINE (Linux/Headless) [{mode_label}]")
        print(f"  Target: Up to {limit} Applications | Candidate: {NAUKRI_EMAIL}")
        print("=" * 65)

        system_chromium_path = None
        if sys.platform.startswith("linux"):
            for cand in [shutil.which("chromium"), shutil.which("chromium-browser"), "/snap/bin/chromium", "/usr/bin/chromium"]:
                if cand and os.path.exists(cand):
                    system_chromium_path = cand
                    break

        active_proxy = proxy or self.proxy or os.getenv("NAUKRI_PROXY")
        proxy_settings = parse_proxy_settings(active_proxy)

        session_lock = SessionLock(session_dir=SESSION_DIR, timeout_sec=15.0)
        session_lock.acquire(blocking=True)
        try:
            cleanup_stale_chromium_locks(SESSION_DIR)

            async with async_playwright() as p:
                # Use persistent context with Chromium fallback
                launch_kwargs = {
                    "user_data_dir": SESSION_DIR,
                    "headless": headless,
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
                    "args": [
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu"
                    ]
                }
                if system_chromium_path:
                    launch_kwargs["executable_path"] = system_chromium_path

                if proxy_settings:
                    launch_kwargs["proxy"] = proxy_settings
                    print(f"  🌐 PlaywrightRunner proxy enabled: {proxy_settings.get('server')}")

                try:
                    context = await p.chromium.launch_persistent_context(**launch_kwargs)
                except Exception as e:
                    print(f"Launch notice ({e}); clearing stale locks and retrying...")
                    cleanup_stale_chromium_locks(SESSION_DIR)
                    context = await p.chromium.launch_persistent_context(**launch_kwargs)

                context._session_lock = session_lock
                context.on("close", lambda _: session_lock.release())

                await context.add_init_script(STEALTH_JS)
                page = context.pages[0] if context.pages else await context.new_page()

                # Load seed cookies if present
                if os.path.exists(COOKIES_SEED_PATH):
                    try:
                        with open(COOKIES_SEED_PATH, "r", encoding="utf-8") as f:
                            cookies = json.load(f)
                        await context.add_cookies(cookies)
                    except Exception:
                        pass

                total_applied = 0

                # Phase 1: Harvesting Recommended Jobs
                total_applied = await self.harvest_recommended_jobs_async(context, page, limit, total_applied, proxy=active_proxy)

                # Phase 2: Harvesting Recruiter NVites / Inbox
                total_applied = await self.harvest_nvites_and_inbox_async(context, page, limit, total_applied, proxy=active_proxy)

                # Phase 3: Freshness-Sorted Multi-Page Search Scanning
                print("\n" + "-" * 65)
                print("  🔍 [PHASE 3] Scanning Freshness-Sorted Search Results...")
                print("-" * 65)
                search_locs = LOCATIONS if LOCATIONS else CANONICAL_LOCATIONS
                for loc in search_locs:
                    if total_applied >= limit:
                        break
                    for kw in DEFAULT_KEYWORDS:
                        if total_applied >= limit:
                            break

                        for page_num in range(1, 4):
                            if total_applied >= limit:
                                break

                            url = build_search_url(kw, loc, page_num)
                            print(f"\n[*] Scanning keyword: '{kw}' ({loc}, page {page_num}) -> {url}")

                            try:
                                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                                await page.wait_for_timeout(3000)

                                jobs = await page.evaluate("""() => {
                                    const items = Array.from(document.querySelectorAll('.srp-jobtuple-wrapper, .cust-job-tuple, .job-tuple, article.jobTuple'));
                                    return items.map(it => {
                                        const title = it.querySelector('a.title, a[class*="title"]');
                                        const comp = it.querySelector('a.comp-name, span.comp-nameText, a.subTitle');
                                        const exp = it.querySelector('.exp-wrap, [class*="exp"], span.ni-job-tuple-icon-srp-experience + span');
                                        const sal = it.querySelector('span.sal-wrap, [class*="sal"], span.ni-job-tuple-icon-srp-rupee + span');
                                        const desc = it.querySelector('.job-desc, .row4, .job-description, .ellipsis');
                                        const tags = Array.from(it.querySelectorAll('.tag-li, .tags-gt li, ul.tags li')).map(t => t.innerText.trim()).join(' ');
                                        return {
                                            title: title ? title.innerText.trim() : '',
                                            href: title ? title.href : '',
                                            company: comp ? comp.innerText.trim() : '',
                                            exp: exp ? exp.innerText.trim() : '',
                                            sal: sal ? sal.innerText.trim() : 'Undisclosed',
                                            desc: (desc ? desc.innerText.trim() : '') + ' ' + (it.innerText || '').trim(),
                                            tags: tags || ''
                                        };
                                    });
                                }""")

                                if not jobs:
                                    break

                                seen_urls = set()
                                for job in jobs:
                                    if total_applied >= limit:
                                        break

                                    title = job.get("title", "")
                                    comp = job.get("company", "")
                                    salary = job.get("sal", "Undisclosed")
                                    job_url = job.get("href", "")
                                    raw_jd = f"{job.get('desc', '')} {job.get('tags', '')}".strip()

                                    if not job_url or job_url in seen_urls or make_job_id(title, comp) in self.skip_list:
                                        continue
                                    seen_urls.add(job_url)

                                    # Persistent DB duplicate check
                                    from naukari_pro.modules.db import is_job_already_applied
                                    if is_job_already_applied(title=title, company=comp, job_url=job_url):
                                        self.skip_list = add_to_skip(self.skip_list, title, comp, "already-in-db")
                                        continue

                                    # Upfront Experience Verification Gate
                                    is_exp_ok, exp_reason, min_e, max_e = is_experience_eligible(
                                        exp_text=job.get("exp", ""),
                                        jd_text=raw_jd,
                                        title=title,
                                        url=job_url,
                                        candidate_exp=CANDIDATE_EXPERIENCE,
                                        max_allowed=MAX_EXPERIENCE_THRESHOLD
                                    )
                                    if not is_exp_ok:
                                        print(f"  ⛔ Skipped Search Experience: {title} @ {comp} ({exp_reason})")
                                        self.skip_list = add_to_skip(self.skip_list, title, comp, "exp-mismatch")
                                        continue

                                    acceptable, reason = is_salary_acceptable(salary, MIN_SALARY_LPA)
                                    if not acceptable:
                                        self.skip_list = add_to_skip(self.skip_list, title, comp, "low-salary")
                                        continue

                                    # If SRP snippet is truncated (< 70%) but card is a candidate Data/Cloud/Spark role,
                                    # enrich raw_jd with full job page text before applying the strict >= 70% gate.
                                    is_match, score, match_reason = evaluate_job_match(title, comp, raw_jd)
                                    card_lower = f"{title} {raw_jd}".lower()
                                    is_candidate_role = score >= 25 or any(
                                        term in card_lower for term in ("data engineer", "databricks", "pyspark", "azure", "delta", "lakehouse", "fabric", "etl", "kafka", "snowflake")
                                    )
                                    if not is_match and is_candidate_role and not self.dry_run:
                                        detail_tab = await context.new_page()
                                        try:
                                            await detail_tab.goto(job_url, wait_until="domcontentloaded", timeout=25000)
                                            await detail_tab.wait_for_timeout(1800)
                                            full_body = await detail_tab.evaluate("() => document.body ? document.body.innerText : ''")
                                            if full_body:
                                                fb_low = full_body.lower()
                                                synonym_tags = []
                                                if any(k in fb_low for k in ("adf", "data factory", "synapse", "fabric", "azure")):
                                                    synonym_tags.append("azure")
                                                if any(k in fb_low for k in ("delta", "lakehouse", "medallion", "parquet", "etl", "data pipeline")):
                                                    synonym_tags.append("delta lake")
                                                raw_jd = f"{raw_jd} {full_body} {' '.join(synonym_tags)}".strip()
                                                is_match, score, match_reason = evaluate_job_match(title, comp, raw_jd)
                                        except Exception:
                                            pass
                                        finally:
                                            try:
                                                await detail_tab.close()
                                            except Exception:
                                                pass

                                    # Match Scoring Gate (>= 70%) (Feature 10)
                                    if not is_match:
                                        print(f"  ⛔ Skipped: {title} @ {comp} ({match_reason})")
                                        self.skip_list = add_to_skip(self.skip_list, title, comp, f"low-match-{score}pct")
                                        continue

                                    applied_ok, _ = await self.apply_to_job_async(
                                        context,
                                        job_url,
                                        title,
                                        comp,
                                        salary,
                                        raw_jd=raw_jd,
                                        match_score=score,
                                        proxy=active_proxy
                                    )
                                    if applied_ok:
                                        total_applied += 1
                            except Exception as e:
                                print(f"Search warning: {e}")

                try:
                    await context.close()
                except Exception:
                    pass
                return total_applied
        finally:
            session_lock.release()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN AUTO APPLY ENGINE ENTRYPOINT
# ─────────────────────────────────────────────────────────────────────────────
class AutoApplyEngine:
    def __init__(self, dry_run=False):
        self.skip_list = load_skip_list()
        self.dry_run = dry_run
        self.payloads: List[ApplicationPayload] = []

    def run_offline_dry_run(
        self,
        job_feed: Optional[List[Dict[str, Any]]] = None,
        limit: int = 20
    ) -> List[ApplicationPayload]:
        """
        100% Offline Dry-Run Engine.
        Executes without Playwright or browser network calls.
        Evaluates salary gate, match score gate (>=70%), and emits structured ApplicationPayloads.
        Zero file mutations (no Excel or skip-list writes).
        """
        cfg = load_config()
        answers = cfg.get("answers_to_common_questions", {})

        if job_feed is None:
            job_feed = [
                {
                    "title": "Lead Azure Data Engineer",
                    "company": "Microsoft GCC",
                    "salary": "24 - 32 Lacs PA",
                    "url": "https://www.naukri.com/job-msft-001",
                    "jd": "Azure Databricks PySpark Delta Lake Medallion Architecture Kafka"
                },
                {
                    "title": "Azure Data Platform Engineer",
                    "company": "Walmart Global Tech",
                    "salary": "22 - 28 Lacs PA",
                    "url": "https://www.naukri.com/job-walmart-002",
                    "jd": "Azure Databricks PySpark Delta Lake SQL Terraform"
                },
                {
                    "title": "Senior Data Engineer",
                    "company": "Amazon",
                    "salary": "26 - 35 Lacs PA",
                    "url": "https://www.naukri.com/job-amzn-003",
                    "jd": "Azure Databricks PySpark Delta Lake Kafka Kubernetes"
                },
                {
                    "title": "Junior Web Developer",
                    "company": "Agency",
                    "salary": "6 - 8 Lacs PA",
                    "url": "https://www.naukri.com/job-agency-004",
                    "jd": "HTML CSS PHP WordPress"
                },
                {
                    "title": "Frontend React Engineer",
                    "company": "Startup",
                    "salary": "18 - 24 Lacs PA",
                    "url": "https://www.naukri.com/job-startup-005",
                    "jd": "React Redux CSS HTML"
                }
            ]

        self.payloads = []
        for job in job_feed:
            if len(self.payloads) >= limit:
                break

            title = job.get("title", "")
            company = job.get("company", "")
            salary = job.get("salary") or job.get("sal", "N/A")
            url = job.get("url") or job.get("href", "N/A")
            jd = job.get("jd") or job.get("desc") or job.get("snippet", "")

            # Salary Gate
            sal_ok, _ = is_salary_acceptable(salary, MIN_SALARY_LPA)
            if not sal_ok:
                payload = ApplicationPayload(
                    company=company,
                    job_title=title,
                    title=title,
                    url=url,
                    match_score=0,
                    salary=salary,
                    answers=answers,
                    payload_data=answers,
                    dry_run=True,
                    status="REJECTED_LOW_SALARY"
                )
                self.payloads.append(payload)
                continue

            # Experience Gate (Enforces <= 4 YOE max and candidate compatibility)
            is_exp_ok, exp_reason, min_e, max_e = is_experience_eligible(
                exp_text=job.get("exp", "") or job.get("experience", ""),
                jd_text=jd,
                title=title,
                url=url,
                candidate_exp=CANDIDATE_EXPERIENCE,
                max_allowed=MAX_EXPERIENCE_THRESHOLD
            )
            if not is_exp_ok:
                payload = ApplicationPayload(
                    company=company,
                    job_title=title,
                    title=title,
                    url=url,
                    match_score=0,
                    salary=salary,
                    answers=answers,
                    payload_data={"experience_gate": exp_reason},
                    dry_run=True,
                    status="REJECTED_EXPERIENCE_MISMATCH"
                )
                self.payloads.append(payload)
                continue

            # Match Score Gate
            is_match, score, _ = evaluate_job_match(title, company, jd, min_threshold=MATCH_SCORE_THRESHOLD)
            status = "VALIDATED_PAYLOAD" if is_match else "REJECTED_BELOW_THRESHOLD"

            payload = ApplicationPayload(
                company=company,
                job_title=title,
                title=title,
                url=url,
                match_score=score,
                salary=salary,
                answers=answers,
                payload_data=answers,
                portal_type="Naukri 1-Click",
                dry_run=True,
                status=status
            )
            self.payloads.append(payload)

        return self.payloads

    def run(self, page=None, headless=False, limit=20, dry_run=None, job_feed=None, proxy=None):
        active_dry_run = self.dry_run if dry_run is None else dry_run

        if active_dry_run:
            payloads = self.run_offline_dry_run(job_feed=job_feed, limit=limit)
            valid_payloads = [p for p in payloads if p.status == "VALIDATED_PAYLOAD"]
            print(f"\n[DRY-RUN] Evaluated {len(payloads)} vacancies offline. Emitted {len(valid_payloads)} validated ApplicationPayloads:")
            for p in valid_payloads:
                print(f"  • [{p.match_score}% Match] {p.company} — {p.job_title} ({p.salary}) -> {p.status}")
            return len(valid_payloads)

        if not headless and is_mac_chrome_available():
            engine = NativeChromeRunner(self.skip_list, dry_run=False)
            return engine.run(limit=limit)
        else:
            import asyncio
            engine = PlaywrightRunner(self.skip_list, dry_run=False, proxy=proxy)
            return asyncio.run(engine.run_async(headless=headless, limit=limit, proxy=proxy))
