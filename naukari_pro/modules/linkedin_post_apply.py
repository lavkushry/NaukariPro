"""
naukariPro LinkedIn Hiring Posts Auto-Applier (Stealth Mode)
===========================================================
Discovers fresh LinkedIn Hiring Posts for 2-4 YOE DevOps / Platform / MLOps /
Cloud / SRE / Azure Data Engineer roles across Hyderabad, Bengaluru, Pune,
Gurugram, and India Remote, extracts direct recruiter/HR email addresses and
embedded ATS/career links, and dispatches:
  1. Tailored direct emails with `Lavkush_Kumar_MLOps_Resume.pdf` attached
     via Gmail SMTP (using GMAIL_APP_PASSWORD).
  2. Embedded external ATS applications via CareerPortalFiller.
  3. Private ready-to-paste DM copy for DM-only posts (never auto-comments
     publicly so current employer CGI India never sees job-search activity).

100% fact-grounded in AGENTS.md / 01_FACT_MATRIX.md.
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import smtplib
import time
import urllib.parse
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, quote, unquote, urlparse

from naukari_pro.config import BASE_DIR, WORKSPACE_DIR, RESUME_PDF_PATH, load_config
from naukari_pro.modules.db import (
    DB_PATH,
    get_db_connection,
    init_db,
    is_job_already_applied,
    record_applied_job,
)
from naukari_pro.modules.linkedin_session import LinkedInSessionManager
from naukari_pro.modules.role_guard import FORBIDDEN_COMPANIES, is_strictly_data_or_cloud_role

logger = logging.getLogger("naukariPro.LinkedInPostApply")

DEFAULT_POST_QUERIES: Tuple[str, ...] = (
    "hiring devops engineer hyderabad",
    "hiring devops engineer bengaluru",
    "hiring mlops engineer india",
    "hiring platform engineer hyderabad OR bengaluru",
    "hiring cloud engineer devops hyderabad",
    "hiring azure data engineer hyderabad",
    "send resume devops india",
    "share cv devops OR mlops hyderabad OR bengaluru",
)

EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
TIMESTAMP_LINE_RE = re.compile(
    r"^\s*\d+\s*(?:m|min|mins|h|hr|hrs|d|w|mo)\b.*•?",
    re.IGNORECASE,
)

EXCLUDED_EMAILS = {
    "lav84095@gmail.com",
    "lavkushry@gmail.com",
}

EXCLUDED_EMAIL_LOCAL_PARTS = {
    "noreply",
    "no-reply",
    "donotreply",
    "do-not-reply",
    "support",
    "info",
    "privacy",
    "legal",
    "unsubscribe",
    "notifications",
    "notification",
}

EXCLUDED_EMAIL_DOMAINS = {
    "cgi.com",
    "example.com",
    "example.org",
    "test.com",
    "sentry.io",
    "linkedin.com",
}

FREE_WEBMAIL_DOMAINS = {
    "gmail.com",
    "yahoo.com",
    "yahoo.co.in",
    "outlook.com",
    "hotmail.com",
    "live.com",
    "protonmail.com",
    "proton.me",
    "rediffmail.com",
    "icloud.com",
}

KNOWN_ATS_DOMAINS = (
    "greenhouse.io",
    "lever.co",
    "ashbyhq.com",
    "myworkdayjobs.com",
    "myworkdaysite.com",
    "workdayjobs.com",
    "smartrecruiters.com",
    "icims.com",
    "bamboohr.com",
    "rippling.com",
    "workable.com",
    "recruitee.com",
    "teamtailor.com",
    "jobvite.com",
    "zohorecruit.",
)

BLOCKED_EXTERNAL_DOMAINS = (
    "whatsapp.com",
    "chat.whatsapp.com",
    "wa.me",
    "t.me",
    "telegram.me",
    "telegram.org",
    "youtube.com",
    "youtu.be",
    "instagram.com",
    "facebook.com",
    "twitter.com",
    "x.com",
    "discord.gg",
    "discord.com",
)

PROMO_LNKD_CONTEXT_KEYWORDS = (
    "whatsapp",
    "telegram",
    "channel",
    "community",
    "join our",
    "exclusive group",
    "interview prep",
    "mock interview",
    "course",
    "bootcamp",
    "webinar",
    "newsletter",
    "youtube",
)

HIRING_INTENT_KEYWORDS = (
    "hiring",
    "we are looking",
    "we're looking",
    "looking for",
    "open role",
    "open position",
    "job opening",
    "opening for",
    "vacancy",
    "vacancies",
    "share your resume",
    "send your resume",
    "share your cv",
    "send your cv",
    "drop your resume",
    "drop your cv",
    "dm your",
    "apply now",
    "apply here",
    "immediate joiner",
    "immediate requirement",
)

JOB_SEEKER_PHRASES = (
    "i am looking for",
    "i'm looking for",
    "looking for a job",
    "looking for new opportunities",
    "looking for my next role",
    "actively looking for",
    "open to work",
    "#opentowork",
    "seeking a new role",
    "any leads would be",
    "please help me find",
    "laid off",
    "recently graduated",
    "fresher looking for",
)

INDIA_LOCATIONS = (
    "hyderabad",
    "bengaluru",
    "bangalore",
    "pune",
    "gurugram",
    "gurgaon",
    "noida",
    "chennai",
    "mumbai",
    "india",
    "pan india",
)

FOREIGN_ONLY_MARKERS = (
    "us only",
    "usa",
    "us-based",
    "united states",
    "u.s.",
    "w2 only",
    "w2",
    "c2c",
    "usc only",
    "gc holder",
    "green card",
    "h1b",
    "opt/cpt",
    "uk only",
    "london",
    "canada",
    "dubai",
    "uae",
    "singapore",
    "poland",
    "germany",
    "australia",
    "europe only",
)

NON_TARGET_INFRA_TOKENS = (
    "l1/l2",
    "l2/l3",
    "l2 & l3",
    "soc analyst",
    "soc platform",
    "microsoft sentinel",
    "siem engineering",
    "soar automation",
)

INDIA_CITIES = (
    "hyderabad",
    "bengaluru",
    "bangalore",
    "pune",
    "gurugram",
    "gurgaon",
    "noida",
    "chennai",
    "mumbai",
    "india",
    "pan india",
)

SENIOR_HEADLINE_TOKENS = (
    "senior",
    "sr.",
    "sr ",
    "staff ",
    "principal",
    "lead ",
    "tech lead",
    "team lead",
    "architect",
    "manager",
    "director",
    "head of",
    "vp ",
    "freshers",
    "fresher",
    "intern",
    "internship",
)

SKILL_WEIGHTS: Dict[str, float] = {
    "kubernetes": 4.0,
    "eks": 3.0,
    "aks": 3.0,
    "docker": 3.0,
    "terraform": 4.0,
    "ansible": 3.0,
    "helm": 3.0,
    "argocd": 3.0,
    "aws": 3.0,
    "azure": 3.0,
    "ci/cd": 3.0,
    "github actions": 2.0,
    "jenkins": 2.0,
    "gitlab": 2.0,
    "python": 3.0,
    "mlops": 4.0,
    "prometheus": 2.0,
    "grafana": 2.0,
    "kafka": 2.0,
    "pyspark": 3.0,
    "databricks": 3.0,
    "sql": 2.0,
    "linux": 2.0,
    "rag": 2.0,
    "llm": 2.0,
    "sre": 3.0,
    "devops": 3.0,
    "platform": 2.0,
}

ROLE_PRIORITY_PHRASES: Tuple[str, ...] = (
    "Azure Data Engineer",
    "MLOps Engineer",
    "AI Infrastructure Engineer",
    "Platform Engineer",
    "DevOps Engineer",
    "Site Reliability Engineer",
    "Cloud Infrastructure Engineer",
    "Cloud Engineer",
    "Data Engineer",
    "ML Engineer",
    "SRE",
)


@dataclass
class LinkedInPostLead:
    post_id: str
    author_name: str
    author_profile_url: str
    author_headline: str
    post_age: str
    company: str
    role_title: str
    location: str
    min_yoe: Optional[float]
    max_yoe: Optional[float]
    salary_lpa_max: Optional[float]
    post_body: str
    emails: List[str] = field(default_factory=list)
    ats_urls: List[str] = field(default_factory=list)
    linkedin_job_urls: List[str] = field(default_factory=list)
    match_score: float = 0.0
    eligible: bool = False
    filter_reason: str = ""
    channel: str = "NONE"
    query_used: str = ""
    post_url: str = ""


def resolve_canonical_resume_pdf() -> str:
    """Prefers Lavkush_Kumar_MLOps_Resume.pdf when present, falling back to RESUME_PDF_PATH."""
    mlops_pdf = os.path.join(BASE_DIR, "Lavkush_Kumar_MLOps_Resume.pdf")
    if os.path.isfile(mlops_pdf) and os.path.getsize(mlops_pdf) > 1024:
        return mlops_pdf
    return RESUME_PDF_PATH


def split_card_header_and_body(raw_text: str) -> Tuple[str, str, str]:
    """
    Splits a LinkedIn SDUI listitem text into (author_header, post_age, post_body)
    so author bios ('Senior HR Manager | 10 Years Experience') never pollute
    role/YOE/salary checks.
    """
    if not raw_text:
        return "", "", ""
    lines = [ln.rstrip() for ln in str(raw_text).splitlines()]
    split_idx = -1
    post_age = ""

    for idx, line in enumerate(lines[:18]):
        stripped = line.strip()
        if TIMESTAMP_LINE_RE.match(stripped):
            post_age = stripped.split("•")[0].strip()
            split_idx = idx
            break

    if split_idx == -1:
        # Fallback: drop 'Feed post' prefix if present
        non_empty = [ln for ln in lines if ln.strip() and ln.strip().lower() != "feed post"]
        return "", "", "\n".join(non_empty).strip()

    header_lines = [ln.strip() for ln in lines[:split_idx] if ln.strip() and ln.strip().lower() != "feed post"]
    body_start = split_idx + 1
    while body_start < len(lines):
        cand = lines[body_start].strip()
        if not cand or cand.lower() in ("follow", "following", "join", "connect", "• 1st", "• 2nd", "• 3rd", "• 3rd+"):
            body_start += 1
            continue
        break

    # Trim trailing reaction/comment footer noise if present
    body_lines = lines[body_start:]
    cleaned_body: List[str] = []
    for ln in body_lines:
        low = ln.strip().lower()
        if low in ("like", "comment", "repost", "send", "copy link to post"):
            break
        cleaned_body.append(ln)

    return "\n".join(header_lines).strip(), post_age, "\n".join(cleaned_body).strip()


def extract_emails_from_post(
    post_body: str,
    mailto_hrefs: Optional[List[str]] = None,
) -> List[str]:
    """
    Extracts valid, deduplicated corporate/recruiter emails from mailto links
    and post body text. Excludes candidate's own email, CGI India, and noreply addresses.
    """
    candidates: List[str] = []
    for href in (mailto_hrefs or []):
        h = (href or "").strip()
        if h.lower().startswith("mailto:"):
            addr = h[7:].split("?")[0].strip()
            if addr:
                candidates.append(addr)

    for match in EMAIL_REGEX.findall(post_body or ""):
        candidates.append(match.strip(".,;:()[]<>"))

    seen = set()
    valid: List[str] = []
    for raw in candidates:
        em = raw.lower().strip()
        if not em or "@" not in em or em in seen:
            continue
        if em in EXCLUDED_EMAILS:
            continue
        local, domain = em.split("@", 1)
        if local in EXCLUDED_EMAIL_LOCAL_PARTS:
            continue
        if domain in EXCLUDED_EMAIL_DOMAINS or domain.endswith(".cgi.com") or "cgi.com" == domain:
            continue
        if any(domain.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")):
            continue
        seen.add(em)
        valid.append(em)
    return valid


def decode_linkedin_redirect(url: str) -> str:
    """Unwraps https://www.linkedin.com/safety/go/?url=... redirect URLs."""
    if not url:
        return ""
    u = url.strip()
    try:
        parsed = urlparse(u)
        if "linkedin.com" in parsed.netloc.lower() and "/safety/go" in parsed.path.lower():
            qs = parse_qs(parsed.query)
            if "url" in qs and qs["url"]:
                return unquote(qs["url"][0]).strip()
    except Exception:
        pass
    return u


def _is_promo_shortlink(url: str, raw_link_text: str, post_body: str) -> bool:
    u_low = url.lower()
    if "lnkd.in/" not in u_low and "bit.ly/" not in u_low:
        return False
    # Check surrounding line in post_body for WhatsApp / Telegram / course / channel promo
    needle = (raw_link_text or url).strip().lower()
    for line in (post_body or "").splitlines():
        low_line = line.lower()
        if needle and needle in low_line:
            if any(kw in low_line for kw in PROMO_LNKD_CONTEXT_KEYWORDS):
                return True
    # Also check preceding line when link stands alone on its own line
    lines = (post_body or "").splitlines()
    for idx, line in enumerate(lines):
        if needle and needle in line.lower() and idx > 0:
            prev_low = lines[idx - 1].lower()
            if any(kw in prev_low for kw in PROMO_LNKD_CONTEXT_KEYWORDS):
                return True
    return False


def extract_apply_links(
    raw_links: List[Dict[str, str]],
    post_body: str = "",
) -> Tuple[List[str], List[str]]:
    """
    Returns (linkedin_job_urls, ats_urls) extracted from card links.
    Strictly filters out hashtags, profiles, ads, WhatsApp/Telegram/social links.
    """
    li_jobs: List[str] = []
    ats_urls: List[str] = []
    seen_li = set()
    seen_ats = set()

    for item in (raw_links or []):
        href = (item.get("href") or "").strip()
        link_text = (item.get("text") or "").strip()
        if not href or href.lower().startswith("mailto:"):
            continue
        decoded = decode_linkedin_redirect(href)
        low = decoded.lower()

        if any(bad in low for bad in BLOCKED_EXTERNAL_DOMAINS):
            continue

        # LinkedIn job links
        if "linkedin.com/jobs/view/" in low:
            clean_li = decoded.split("?")[0].rstrip("/") + "/"
            if clean_li not in seen_li:
                seen_li.add(clean_li)
                li_jobs.append(clean_li)
            continue

        # Ignore internal LinkedIn chrome (/in/, /company/, /groups/, /search/, /services/)
        if "linkedin.com/" in low:
            continue

        if not low.startswith(("http://", "https://")):
            continue

        if _is_promo_shortlink(decoded, link_text, post_body):
            continue

        # Keep known ATS portals or explicit career/job links
        parsed = urlparse(decoded)
        host_and_path = f"{parsed.netloc.lower()}{parsed.path.lower()}"
        is_ats = any(dom in host_and_path for dom in KNOWN_ATS_DOMAINS)
        is_career_url = any(tok in host_and_path for tok in ("careers.", "jobs.", "/careers", "/jobs", "/apply", "lnkd.in/"))
        if is_ats or is_career_url:
            if decoded not in seen_ats:
                seen_ats.add(decoded)
                ats_urls.append(decoded)

    return li_jobs, ats_urls


def parse_experience_range(post_body: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Extracts (min_yoe, max_yoe) from hiring post body.
    Checks explicit Experience/Exp labels first, then general ranges and N+ thresholds.
    """
    if not post_body:
        return None, None
    text = post_body.lower()

    # 1. Explicit labelled range: 'Experience: 2-4 Years', 'Exp - 2–5 yrs'
    m_lbl_range = re.search(
        r"(?:experience|exp|yoe)\s*[:\-–]?\s*(\d{1,2}(?:\.\d+)?)\s*(?:-|–|—|to)\s*(\d{1,2}(?:\.\d+)?)",
        text,
    )
    if m_lbl_range:
        lo = float(m_lbl_range.group(1))
        hi = float(m_lbl_range.group(2))
        if 0 <= lo <= 30 and lo <= hi <= 35:
            return lo, hi

    # 2. Explicit labelled threshold: 'Exp - 5+ Years', 'Experience: 6+ years'
    m_lbl_plus = re.search(
        r"(?:experience|exp|yoe)\s*[:\-–]?\s*(\d{1,2}(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?|yoe)\b",
        text,
    )
    if m_lbl_plus:
        lo = float(m_lbl_plus.group(1))
        if 0 <= lo <= 30:
            return lo, None

    # 3. Unlabelled explicit year range: '2-4 years', '1 to 3 years'
    m_range = re.search(
        r"\b(\d{1,2}(?:\.\d+)?)\s*(?:-|–|—|to)\s*(\d{1,2}(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?|yoe)\b",
        text,
    )
    if m_range:
        lo = float(m_range.group(1))
        hi = float(m_range.group(2))
        if 0 <= lo <= 30 and lo <= hi <= 35:
            return lo, hi

    # 4. Single N+ years threshold: '5+ Years', 'minimum 3+ yrs'
    m_plus = re.search(
        r"(?:min(?:imum)?\s+)?(\d{1,2}(?:\.\d+)?)\s*\+\s*(?:years?|yrs?|yoe)\b",
        text,
    )
    if m_plus:
        lo = float(m_plus.group(1))
        if 0 <= lo <= 30:
            return lo, None

    return None, None


def parse_disclosed_salary_lpa(post_body: str) -> Optional[float]:
    """
    Parses disclosed annual CTC/budget in LPA from post body.
    Returns the upper bound in LPA (e.g. '12-18 LPA' -> 18.0, 'Up to ₹25 LPA' -> 25.0),
    or None if undisclosed.
    """
    if not post_body:
        return None
    text = post_body.lower()

    # Range: 15-22 LPA / 15 – 25 Lakhs / ₹18 to 24 LPA
    m_range = re.search(
        r"(?:₹|rs\.?|inr)?\s*(\d{1,2}(?:\.\d+)?)\s*(?:-|–|—|to)\s*(?:₹|rs\.?|inr)?\s*(\d{1,2}(?:\.\d+)?)\s*(?:lpa|lakhs?\b|lac\b)",
        text,
    )
    if m_range:
        hi = float(m_range.group(2))
        if 1.0 <= hi <= 200.0:
            return hi

    # Single / 'Up to ₹20 LPA'
    m_single = re.search(
        r"(?:up\s*to|upto|max(?:imum)?|budget|ctc|package|salary)?\s*[:\-–]?\s*(?:₹|rs\.?|inr)?\s*(\d{1,2}(?:\.\d+)?)\s*\+?\s*(?:lpa|lakhs?\s*(?:per\s*annum|pa)?)\b",
        text,
    )
    if m_single:
        val = float(m_single.group(1))
        if 1.0 <= val <= 200.0:
            return val

    return None


def _extract_location_from_body(post_body: str) -> str:
    if not post_body:
        return "India"
    # Prefer explicit Location: line
    m = re.search(r"(?:location|locations|work\s*location)\s*[:\-–|]\s*([^\n]+)", post_body, re.IGNORECASE)
    if m:
        loc_val = m.group(1).strip()
        if loc_val:
            return loc_val[:120]

    low = post_body.lower()
    found: List[str] = []
    for city in ("Hyderabad", "Bengaluru", "Bangalore", "Pune", "Gurugram", "Gurgaon", "Noida", "Chennai", "Mumbai", "Remote"):
        if re.search(rf"\b{city.lower()}\b", low):
            norm = "Bengaluru" if city.lower() == "bangalore" else city
            if norm not in found:
                found.append(norm)
    return " / ".join(found) if found else "India"


def _company_from_email(emails: List[str]) -> str:
    for em in (emails or []):
        if "@" not in em:
            continue
        domain = em.split("@", 1)[1].lower().strip()
        if domain in FREE_WEBMAIL_DOMAINS:
            continue
        parts = [p for p in domain.split(".") if p]
        # Skip short country/subdomain prefixes like in.experis.com, careers.acme.io, hr.acme.co.in
        skip_prefixes = {"in", "us", "uk", "hr", "jobs", "careers", "talent", "mail", "tech"}
        root = parts[0] if parts else ""
        if len(parts) >= 3 and (root in skip_prefixes or len(root) <= 2):
            root = parts[1]
        elif len(parts) >= 3 and parts[-2] in ("co", "com", "org", "net"):
            root = parts[-3]
        if root and len(root) > 1:
            return root.capitalize()
    return ""


def extract_role_and_company(
    post_body: str,
    emails: Optional[List[str]] = None,
    company_links: Optional[List[Dict[str, str]]] = None,
) -> Tuple[str, str]:
    """
    Extracts normalized role title and hiring company from post body, company links,
    or corporate email domain.
    """
    body = post_body or ""
    role_title = ""

    # 1. Explicit Role / Position / Hiring header line
    role_patterns = (
        r"(?:hiring\s*(?:for)?|we(?:'re|\s+are)\s+hiring\s*(?:for)?|position|role|job\s*title|opening\s*(?:for)?)\s*[:\-–|]\s*([^\n]+)",
        r"we(?:'re|\s+are)\s+hiring\s*\|\s*([^\n|]+)",
        r"hiring\s*\|\s*([^\n|]+)",
    )
    for pat in role_patterns:
        m = re.search(pat, body, re.IGNORECASE)
        if m:
            raw_role = m.group(1).strip(" |•🚀🔥✨-*#!?.,;:")
            # Split off trailing "| Bengaluru | 2-4 Yrs" segments
            parts = [p.strip() for p in re.split(r"\s*[|•]\s*", raw_role) if p.strip()]
            if parts:
                candidate_role = parts[0].strip(" !?.,;:-–")
                if 3 <= len(candidate_role) <= 85:
                    role_title = candidate_role
                    break

    # 2. Fallback to matched priority role phrase in post_body
    if not role_title:
        low_body = body.lower()
        for phrase in ROLE_PRIORITY_PHRASES:
            if re.search(rf"\b{re.escape(phrase.lower())}\b", low_body):
                role_title = phrase
                break

    if not role_title:
        # Check for non-target roles like Data Science so role_guard rejects them accurately
        if "data science" in body.lower() or "data scientist" in body.lower():
            role_title = "Data Scientist"
        else:
            role_title = "Unspecified Role"

    # Company extraction
    company = ""
    m_co_label = re.search(r"(?:company|organization|organisation|client)\s*[:\-–|]\s*([^\n|]+)", body, re.IGNORECASE)
    if m_co_label:
        cand_co = m_co_label.group(1).strip(" .|•")
        if 2 <= len(cand_co) <= 50:
            company = cand_co

    if not company:
        m_co = re.search(
            r"\b([A-Z][A-Za-z0-9&.\- ]{1,35}?)\s+(?:is|are)\s+(?:actively\s+)?(?:hiring|looking\s+for)\b",
            body,
        )
        if m_co:
            cand_co = m_co.group(1).strip()
            if cand_co.lower() not in ("we", "our team", "my team", "our client", "team", "currently", "i"):
                company = cand_co

    if not company and company_links:
        for cl in company_links:
            txt = (cl.get("text") or "").strip()
            if txt and len(txt) <= 50 and txt.lower() not in ("view", "follow"):
                company = txt
                break

    if not company:
        company = _company_from_email(emails or [])

    if not company:
        company = "Hiring Team (LinkedIn Post)"

    return role_title, company


def evaluate_hiring_post(
    lead: LinkedInPostLead,
    max_min_yoe: float = 3.0,
    min_salary_lpa: float = 20.0,
) -> Tuple[bool, float, str]:
    """
    Determines whether a LinkedIn post is an eligible hiring opportunity for a ~2.5 YOE
    DevOps / Platform / MLOps / Cloud / Data Engineer based in Hyderabad targeting 20+ LPA.
    Returns (eligible, match_score, reason).
    """
    body_low = (lead.post_body or "").lower()
    if len(body_low.strip()) < 40:
        return False, 0.0, "Rejected: Empty or too-short post body"

    # 1. Hiring intent vs job seeker post
    if any(seeker in body_low for seeker in JOB_SEEKER_PHRASES):
        return False, 0.0, "Rejected: Candidate/job-seeker post, not a hiring post"
    if not any(sig in body_low for sig in HIRING_INTENT_KEYWORDS):
        return False, 0.0, "Rejected: Missing explicit hiring/application intent"

    # Must have at least ONE actionable channel (email, ATS URL, LinkedIn job URL, or DM)
    has_email = bool(lead.emails)
    has_ats = bool(lead.ats_urls)
    has_li_job = bool(lead.linkedin_job_urls)
    has_dm_signal = any(k in body_low for k in ("dm ", "direct message", "inbox", "comment interested", "reach out"))
    if not (has_email or has_ats or has_li_job or has_dm_signal):
        return False, 0.0, "Rejected: No contact email, ATS link, job link, or DM instruction"

    # 2. Employer safety (never apply to own company CGI or forbidden gig-spam companies)
    comp_low = (lead.company or "").lower()
    if "cgi" in comp_low or any(em.endswith("@cgi.com") for em in (lead.emails or [])):
        return False, 0.0, "Rejected: Current employer (CGI) safety exclusion"
    for bad_co in FORBIDDEN_COMPANIES:
        if bad_co in comp_low:
            return False, 0.0, f"Rejected: Excluded company ('{bad_co}')"

    # 3. Seniority in first 3 lines of post_body (guards against "Hiring: Senior DevOps Engineer")
    top_lines = " ".join((lead.post_body or "").splitlines()[:4]).lower()
    for sen_tok in SENIOR_HEADLINE_TOKENS:
        if sen_tok.strip() in ("sr", "sr.", "vp", "lead"):
            if re.search(rf"\b{re.escape(sen_tok.strip())}\b", top_lines):
                return False, 0.0, f"Rejected: Senior/Lead/Intern title token '{sen_tok.strip()}' in headline"
        else:
            if sen_tok in top_lines:
                return False, 0.0, f"Rejected: Senior/Lead/Intern title token '{sen_tok.strip()}' in headline"

    # 3b. Non-target SOC / L1-L3 support operations exclusion
    if any(tok in body_low for tok in NON_TARGET_INFRA_TOKENS):
        return False, 0.0, "Rejected: SOC / L1-L3 support operations role"

    # 4. Canonical Role Guard check
    is_role_ok, role_reason = is_strictly_data_or_cloud_role(
        lead.role_title,
        raw_jd=lead.post_body,
        company=lead.company,
    )
    if not is_role_ok:
        return False, 0.0, role_reason

    # 5. Experience window check for 2.5 YOE candidate
    if lead.min_yoe is not None and lead.min_yoe > max_min_yoe:
        return False, 0.0, f"Rejected: Minimum YOE {lead.min_yoe:g}+ exceeds candidate ceiling ({max_min_yoe:g} YOE)"
    if lead.max_yoe is not None and lead.max_yoe < 2.0:
        return False, 0.0, f"Rejected: Fresher/junior max YOE {lead.max_yoe:g} below 2.5 YOE target"

    # 6. Location check: India hub required (bare "remote" alone is NOT enough); block US/W2/foreign
    loc_low = (lead.location or "").lower()
    loc_has_foreign = any(
        re.search(rf"\b{re.escape(marker)}\b", loc_low) if len(marker) <= 4 else (marker in loc_low)
        for marker in FOREIGN_ONLY_MARKERS
    )
    loc_has_india = any(re.search(rf"\b{re.escape(city)}\b", loc_low) for city in INDIA_CITIES)
    if loc_has_foreign and not loc_has_india:
        return False, 0.0, f"Rejected: Explicit non-India location '{lead.location}'"

    if any(
        phrase in body_low
        for phrase in (
            "from india not considered",
            "india not considered",
            "not open to india",
            "usa-based candidates only",
            "only candidates currently residing in the united states",
            "us citizens only",
        )
    ):
        return False, 0.0, "Rejected: Post explicitly excludes India applicants"

    combined_loc = f"{lead.location} {body_low}".lower()
    has_india = any(
        re.search(rf"\b{re.escape(loc)}\b", combined_loc)
        for loc in INDIA_LOCATIONS
    )
    if not has_india:
        return False, 0.0, f"Rejected: Location '{lead.location}' not in India"

    has_foreign = any(
        re.search(rf"\b{re.escape(marker)}\b", combined_loc) if len(marker) <= 4 else (marker in combined_loc)
        for marker in FOREIGN_ONLY_MARKERS
    )
    has_india_city = any(re.search(rf"\b{re.escape(city)}\b", combined_loc) for city in INDIA_CITIES)
    if has_foreign and not has_india_city:
        return False, 0.0, "Rejected: Non-India / US W2/C2C role"

    # 7. Disclosed salary floor (20 LPA+)
    if lead.salary_lpa_max is not None and lead.salary_lpa_max < min_salary_lpa:
        return False, 0.0, f"Rejected: Disclosed budget ₹{lead.salary_lpa_max:g} LPA below ₹{min_salary_lpa:g} LPA floor"

    # Score (60 base + stack overlap + Hyderabad/corporate email/immediate joiner bonuses)
    score = 60.0
    skill_pts = 0.0
    for kw, pts in SKILL_WEIGHTS.items():
        if re.search(rf"\b{re.escape(kw)}\b", body_low):
            skill_pts += pts
    score += min(22.0, skill_pts)

    if "hyderabad" in combined_loc:
        score += 10.0
    if any(em.split("@", 1)[1] not in FREE_WEBMAIL_DOMAINS for em in (lead.emails or []) if "@" in em):
        score += 5.0
    if "immediate" in body_low or "15 days" in body_low or "notice" in body_low:
        score += 3.0

    score = round(min(99.0, score), 1)
    return True, score, "Eligible target role + India location + 2.5 YOE fit"


def _build_candidate_snapshot(candidate: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    cfg = load_config()
    cand = candidate or cfg.get("candidate") or {}
    return {
        "name": str(cand.get("name") or "Lavkush Kumar"),
        "email": str(cand.get("email") or "lav84095@gmail.com"),
        "phone": str(cand.get("phone") or "+91-9122036484"),
        "linkedin": str(cand.get("linkedin") or "https://www.linkedin.com/in/lavkushry/"),
        "github": str(cand.get("github") or "https://github.com/lavkushry"),
        "location": str(cand.get("primary_location") or "Hyderabad, India"),
        "notice": "15 Days or less (Immediate Joiner)",
        "yoe": "2.5 Years",
    }


def _select_role_highlights(lead: LinkedInPostLead) -> List[str]:
    text_low = f"{lead.role_title} {lead.post_body}".lower()
    if any(tok in text_low for tok in ("data engineer", "pyspark", "databricks", "spark", "etl", "lakehouse")):
        return [
            "Current DevOps Engineer at CGI India (Jun 2026 - Present) & former Engineer 1 - Platform/DevOps at HFCL Limited (Aug 2025 - Jun 2026) with 2.5 YOE.",
            "Production Infrastructure: Operated 50-node Kubernetes clusters, 40+ Ansible roles (provisioning 2 days -> 4 hours), Velero/etcd DR (RTO 8h -> 30m), and Kafka + ELK telemetry across distributed pipelines.",
            "Data & AI Engineering Proof: Built Azure Medallion Lakehouse (35% ETL runtime reduction with Databricks & Delta Lake), Vulcan (autonomous SRE remediation <2m), and AegisAgent (<75ms Cedar policy control plane).",
        ]
    if any(tok in text_low for tok in ("mlops", "ai ", "llm", "rag", "bedrock", "sagemaker", "inference")):
        return [
            "Current DevOps Engineer at CGI India (Jun 2026 - Present) & former Engineer 1 - Platform/DevOps at HFCL Limited (Aug 2025 - Jun 2026) with 2.5 YOE.",
            "Production Kubernetes & Platform Reliability: Operated 50-node Kubernetes clusters, 40+ modular Ansible roles (cluster bootstrap 2 days -> 4 hours), Velero/etcd DR (RTO 8h -> 30m), maintaining 99.95% uptime and 45% lower MTTR.",
            "AI Infra & MLOps Proof: Built AegisAgent (runtime policy control plane for AI agents in Python/FastAPI/Redis with <75ms Cedar evaluation) and Vulcan (automated SRE/incident remediation in Rust/Python under 2m).",
        ]
    return [
        "Current DevOps Engineer at CGI India (Jun 2026 - Present) & former Engineer 1 - DevOps/Platform at HFCL Limited (Aug 2025 - Jun 2026) with 2.5 YOE.",
        "Kubernetes, IaC & CI/CD in Production: Managed 50-node Kubernetes clusters (EKS/kubeadm), 40+ Ansible roles (cluster bootstrap 2 days -> 4 hours), GitLab CI/Jenkins/GitHub Actions/ArgoCD, and Terraform modules.",
        "Observability & DR + Engineering Proof: Cut RTO 8h -> 30m via Velero/etcd DR with 99.95% uptime and 45% MTTR reduction; open-source projects include AegisAgent (AI control plane) and Vulcan (autonomous SRE agent).",
    ]


def compose_application_email(
    lead: LinkedInPostLead,
    candidate: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str]:
    """
    Composes a concise, 100%-factual application email (subject, body_text)
    referencing exact AGENTS.md / 01_FACT_MATRIX.md facts.
    """
    snap = _build_candidate_snapshot(candidate)
    role_clean = re.sub(r"\s+", " ", (lead.role_title or "DevOps / Platform Engineer")).strip()
    comp_clean = re.sub(r"\s+", " ", (lead.company or "")).strip()

    first_name = ""
    if lead.author_name:
        tok = lead.author_name.strip().split()[0]
        if tok.isalpha() and len(tok) >= 2:
            first_name = tok
    greeting = f"Hi {first_name}," if first_name else "Hi Hiring Team,"

    if comp_clean and "linkedin post" not in comp_clean.lower():
        subject = f"Application: {role_clean} @ {comp_clean} | Lavkush Kumar (2.5 YOE | Hyderabad | 15-Day Notice)"
    else:
        subject = f"Application: {role_clean} | Lavkush Kumar (2.5 YOE | DevOps/Platform/MLOps | 15-Day Notice)"

    bullets = _select_role_highlights(lead)
    body_lines = [
        greeting,
        "",
        f"I noticed your LinkedIn hiring post for {role_clean}"
        + (f" at {comp_clean}" if comp_clean and "linkedin post" not in comp_clean.lower() else "")
        + " and wanted to share my profile directly.",
        "",
        "Quick Snapshot:",
        f"- Experience: {snap['yoe']} (CGI India - DevOps Engineer | Ex-HFCL Limited - Platform/DevOps)",
        f"- Current Location: {snap['location']} (Open to Hyderabad / Bengaluru / Hybrid / Remote)",
        f"- Notice Period: {snap['notice']}",
        "- Core Stack: AWS, Azure, Kubernetes (EKS/AKS), Docker, Helm, Terraform, Ansible, ArgoCD, CI/CD, Python, Prometheus/Grafana, Kafka",
        "",
        "Relevant Production Highlights:",
        *[f"- {b}" for b in bullets],
        "",
        "I have attached my updated 1-page resume PDF (Lavkush_Kumar_MLOps_Resume.pdf) for your review. Please let me know a convenient time for a brief call.",
        "",
        "Best regards,",
        snap["name"],
        f"Phone: {snap['phone']} | Email: {snap['email']}",
        f"LinkedIn: {snap['linkedin']}",
        f"GitHub: {snap['github']}",
    ]
    return subject, "\n".join(body_lines)


def compose_manual_dm_and_comment(lead: LinkedInPostLead) -> Dict[str, str]:
    """
    Returns ready-to-paste private DM and optional comment text for DM-only posts.
    Never posted automatically.
    """
    role_clean = (lead.role_title or "DevOps / Platform Engineer").strip()
    first = (lead.author_name or "").strip().split()[0] if lead.author_name else ""
    hi = f"Hi {first}" if first and first.isalpha() else "Hi"
    dm = (
        f"{hi}, saw your post hiring for {role_clean}. I'm a DevOps & Platform Engineer at CGI India "
        f"(ex-HFCL, 2.5 YOE) in Hyderabad (15-day notice). Hands-on with 50-node K8s, Terraform, Ansible, "
        f"CI/CD, AWS/Azure & Python/MLOps. Would love to share my CV (lav84095@gmail.com | +91-9122036484)."
    )
    comment = (
        f"Interested in the {role_clean} role — 2.5 YOE across Kubernetes (50-node clusters), Terraform, "
        f"Ansible, CI/CD, AWS/Azure & Python (Hyderabad | 15-day notice). Shared my resume / sent a connect note!"
    )
    return {"dm": dm, "comment": comment}


def _compute_post_id(author_url: str, post_body: str, post_url: str = "") -> str:
    seed = f"{post_url or author_url}|{re.sub(r'\s+', ' ', post_body[:240]).strip().lower()}"
    return "li_post_" + hashlib.md5(seed.encode("utf-8")).hexdigest()[:12]


class LinkedInPostApplyEngine:
    """
    End-to-end engine for finding fresh LinkedIn Hiring Posts and applying via
    direct email (+ resume PDF attachment) and embedded ATS URLs.
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        resume_path: Optional[str] = None,
        max_daily_emails: int = 15,
        email_cooldown_days: int = 14,
        max_min_yoe: float = 3.0,
        min_salary_lpa: float = 20.0,
    ):
        self.db_path = db_path or DB_PATH
        self.resume_path = resume_path or resolve_canonical_resume_pdf()
        self.max_daily_emails = int(max_daily_emails)
        self.email_cooldown_days = int(email_cooldown_days)
        self.max_min_yoe = float(max_min_yoe)
        self.min_salary_lpa = float(min_salary_lpa)
        self.session_manager = LinkedInSessionManager()
        init_db(self.db_path)

    def _emails_sent_today_count(self) -> int:
        today_str = datetime.now().strftime("%Y-%m-%d")
        conn = get_db_connection(self.db_path)
        try:
            row = conn.execute(
                """
                SELECT COUNT(*) FROM applied_jobs
                WHERE platform = 'linkedin_post'
                  AND status IN ('APPLIED', 'Submitted (Confirmed)')
                  AND DATE(applied_at) = ?
                """,
                (today_str,),
            ).fetchone()
            return int(row[0] or 0) if row else 0
        finally:
            conn.close()

    def _is_recipient_recently_emailed(self, recipient_email: str) -> bool:
        target = f"mailto:{recipient_email.lower().strip()}"
        cutoff = (datetime.now() - timedelta(days=self.email_cooldown_days)).strftime("%Y-%m-%d %H:%M:%S")
        conn = get_db_connection(self.db_path)
        try:
            row = conn.execute(
                """
                SELECT id FROM applied_jobs
                WHERE platform = 'linkedin_post'
                  AND LOWER(job_url) = ?
                  AND status IN ('APPLIED', 'Submitted (Confirmed)')
                  AND applied_at >= ?
                LIMIT 1
                """,
                (target, cutoff),
            ).fetchone()
            return row is not None
        finally:
            conn.close()

    def _build_lead_from_card(self, card: Dict[str, Any], query_used: str) -> LinkedInPostLead:
        raw_text = card.get("text") or ""
        links = card.get("links") or []
        header, post_age, post_body = split_card_header_and_body(raw_text)

        # Author extraction
        author_name = (card.get("author_name") or "").strip()
        author_url = ""
        company_links: List[Dict[str, str]] = []
        mailto_hrefs: List[str] = []
        post_url = ""

        for lk in links:
            href = (lk.get("href") or "").strip()
            txt = (lk.get("text") or "").strip()
            low = href.lower()
            if low.startswith("mailto:"):
                mailto_hrefs.append(href)
            elif "/in/" in low and not author_url:
                author_url = href.split("?")[0]
                if not author_name and txt:
                    author_name = txt.splitlines()[0].split("•")[0].strip()
            elif "/company/" in low:
                company_links.append(lk)
            elif ("/feed/update/" in low or "/posts/" in low) and not post_url:
                post_url = href.split("?")[0]

        header_lines = [ln.strip() for ln in header.splitlines() if ln.strip() and "•" not in ln[:4]]
        if not author_name and header_lines:
            author_name = header_lines[0].split("•")[0].strip()
        author_headline = header_lines[1] if len(header_lines) > 1 else ""

        emails = extract_emails_from_post(post_body, mailto_hrefs=mailto_hrefs)
        li_job_urls, ats_urls = extract_apply_links(links, post_body=post_body)
        min_yoe, max_yoe = parse_experience_range(post_body)
        salary_max = parse_disclosed_salary_lpa(post_body)
        role_title, company = extract_role_and_company(post_body, emails=emails, company_links=company_links)
        location = _extract_location_from_body(post_body)

        if emails:
            channel = "EMAIL"
        elif ats_urls:
            channel = "ATS_URL"
        elif li_job_urls:
            channel = "LINKEDIN_JOB"
        else:
            channel = "DM_MANUAL"

        lead = LinkedInPostLead(
            post_id=_compute_post_id(author_url or author_name, post_body, post_url=post_url),
            author_name=author_name or "Hiring Contact",
            author_profile_url=author_url,
            author_headline=author_headline,
            post_age=post_age,
            company=company,
            role_title=role_title,
            location=location,
            min_yoe=min_yoe,
            max_yoe=max_yoe,
            salary_lpa_max=salary_max,
            post_body=post_body,
            emails=emails,
            ats_urls=ats_urls,
            linkedin_job_urls=li_job_urls,
            channel=channel,
            query_used=query_used,
            post_url=post_url,
        )
        eligible, score, reason = evaluate_hiring_post(
            lead,
            max_min_yoe=self.max_min_yoe,
            min_salary_lpa=self.min_salary_lpa,
        )
        lead.eligible = eligible
        lead.match_score = score
        lead.filter_reason = reason
        return lead

    async def discover_hiring_posts(
        self,
        queries: Optional[List[str]] = None,
        date_posted: str = "past-week",
        max_posts_per_query: int = 20,
        headless: bool = True,
    ) -> List[LinkedInPostLead]:
        """
        Searches LinkedIn content posts across queries using Playwright stealth session,
        expands truncated cards, parses structured leads, and evaluates eligibility.
        """
        from playwright.async_api import async_playwright

        active_queries = list(queries) if queries else list(DEFAULT_POST_QUERIES)
        leads_by_id: Dict[str, LinkedInPostLead] = {}

        async with async_playwright() as p:
            ctx = await self.session_manager.create_stealth_context(p, headless=headless)
            try:
                page = ctx.pages[0] if ctx.pages else await ctx.new_page()
                for q in active_queries:
                    enc_q = quote(q)
                    url = (
                        f"https://www.linkedin.com/search/results/content/"
                        f"?keywords={enc_q}&sortBy=%22date_posted%22&datePosted=%22{quote(date_posted)}%22"
                    )
                    try:
                        await page.goto(url, wait_until="domcontentloaded", timeout=35000)
                        await asyncio.sleep(3.5)
                        cur_url = (page.url or "").lower()
                        if "/login" in cur_url or "/authwall" in cur_url or "/checkpoint" in cur_url or "/challenge" in cur_url:
                            logger.warning("LinkedIn session checkpoint/authwall at %s; stopping discovery safely.", page.url)
                            break

                        # Scroll to load ~10-15 cards
                        for _ in range(3):
                            await page.mouse.wheel(0, 1800)
                            await asyncio.sleep(1.5)

                        # Expand truncated "... more" buttons inside feed cards (short timeout, never stall)
                        more_btns = page.locator("main div[role='listitem'] button:has-text('more')")
                        try:
                            n_more = min(await more_btns.count(), max_posts_per_query)
                            for idx in range(n_more):
                                btn = more_btns.nth(idx)
                                try:
                                    if await btn.is_visible(timeout=500):
                                        await btn.click(timeout=800)
                                        await asyncio.sleep(0.25)
                                except Exception:
                                    pass
                        except Exception:
                            pass

                        raw_cards = await page.evaluate(
                            """(maxN) => {
                                const main = document.querySelector('main') || document.body;
                                const nodes = Array.from(main.querySelectorAll('div[role="listitem"]'));
                                const out = [];
                                for (const el of nodes) {
                                    if (out.length >= maxN) break;
                                    const t = (el.innerText || '').trim();
                                    if (!t || t.length < 80) continue;
                                    if (t.includes('Hide or report this ad') || t.includes('Are these results helpful')) continue;
                                    const ctrlBtn = el.querySelector('button[aria-label^="Open control menu for post by "]');
                                    let authorName = '';
                                    if (ctrlBtn) {
                                        const aria = ctrlBtn.getAttribute('aria-label') || '';
                                        authorName = aria.replace(/^Open control menu for post by\\s+/i, '').trim();
                                    }
                                    const links = Array.from(el.querySelectorAll('a[href]')).map(a => ({
                                        href: a.getAttribute('href') || '',
                                        text: (a.innerText || '').trim().slice(0, 100)
                                    }));
                                    out.push({ text: t.slice(0, 5000), author_name: authorName, links });
                                }
                                return out;
                            }""",
                            int(max_posts_per_query),
                        )

                        for card in (raw_cards or []):
                            lead = self._build_lead_from_card(card, query_used=q)
                            if lead.post_id not in leads_by_id:
                                leads_by_id[lead.post_id] = lead
                    except Exception as e_q:
                        logger.warning("Query discovery notice for '%s': %s", q[:50], e_q)
                        continue
            finally:
                try:
                    await ctx.close()
                except Exception:
                    pass
                try:
                    if hasattr(ctx, "_session_lock") and ctx._session_lock:
                        ctx._session_lock.release()
                except Exception:
                    pass

        return list(leads_by_id.values())

    def send_direct_email(
        self,
        lead: LinkedInPostLead,
        recipient_email: str,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Sends an application email directly to the recruiter/HR contact with
        Lavkush_Kumar_MLOps_Resume.pdf attached, enforcing daily cap and dedup.
        """
        recipient = (recipient_email or "").strip().lower()
        if not recipient or "@" not in recipient:
            return {"status": "INVALID_EMAIL", "recipient": recipient_email, "sent": False}

        if self._is_recipient_recently_emailed(recipient):
            return {"status": "SKIPPED_COOLDOWN", "recipient": recipient, "sent": False}

        if is_job_already_applied(
            job_id=lead.post_id,
            job_url=f"mailto:{recipient}",
            db_path=self.db_path,
        ):
            return {"status": "SKIPPED_DUPLICATE", "recipient": recipient, "sent": False}

        sent_today = self._emails_sent_today_count()
        if sent_today >= self.max_daily_emails:
            return {
                "status": "DAILY_CAP_REACHED",
                "recipient": recipient,
                "sent": False,
                "detail": f"Daily cap {sent_today}/{self.max_daily_emails} reached",
            }

        if not self.resume_path or not os.path.isfile(self.resume_path):
            return {"status": "RESUME_MISSING", "recipient": recipient, "sent": False}

        subject, body_text = compose_application_email(lead)
        if dry_run:
            return {
                "status": "DRY_RUN_READY",
                "recipient": recipient,
                "subject": subject,
                "body_preview": body_text[:300],
                "resume": os.path.basename(self.resume_path),
                "sent": False,
                "dry_run": True,
            }

        sender = os.getenv("GMAIL_USER") or os.getenv("CANDIDATE_EMAIL") or "lav84095@gmail.com"
        password = os.getenv("GMAIL_APP_PASSWORD") or ""
        if not password:
            return {
                "status": "SMTP_CREDENTIALS_MISSING",
                "recipient": recipient,
                "sent": False,
                "detail": "GMAIL_APP_PASSWORD not set in environment",
            }

        msg = MIMEMultipart()
        msg["From"] = f"Lavkush Kumar <{sender}>"
        msg["To"] = recipient
        msg["Reply-To"] = sender
        msg["Subject"] = subject
        msg.attach(MIMEText(body_text, "plain", "utf-8"))

        with open(self.resume_path, "rb") as f_pdf:
            pdf_part = MIMEApplication(f_pdf.read(), _subtype="pdf")
            pdf_part.add_header(
                "Content-Disposition",
                "attachment",
                filename=os.path.basename(self.resume_path),
            )
            msg.attach(pdf_part)

        try:
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
                server.starttls()
                server.login(sender, password)
                server.sendmail(sender, [recipient], msg.as_string())
        except Exception as e_smtp:
            logger.error("SMTP dispatch failed for %s: %s", recipient, e_smtp)
            return {
                "status": "SMTP_ERROR",
                "recipient": recipient,
                "sent": False,
                "detail": str(e_smtp),
            }

        exp_label = (
            f"{lead.min_yoe:g}-{lead.max_yoe:g} Yrs"
            if lead.min_yoe is not None and lead.max_yoe is not None
            else (f"{lead.min_yoe:g}+ Yrs" if lead.min_yoe is not None else "2-4 Yrs")
        )
        ok, saved_id = record_applied_job(
            title=lead.role_title,
            company=lead.company,
            platform="linkedin_post",
            location=lead.location,
            experience_req=exp_label,
            match_score=lead.match_score,
            status="APPLIED",
            application_type="LinkedIn Post Direct Email",
            job_url=f"mailto:{recipient}",
            applicant_email=sender,
            raw_metadata={
                "post_id": lead.post_id,
                "author_name": lead.author_name,
                "author_profile_url": lead.author_profile_url,
                "post_age": lead.post_age,
                "recipient_email": recipient,
                "subject": subject,
                "resume_attached": os.path.basename(self.resume_path),
                "post_url": lead.post_url,
                "query_used": lead.query_used,
            },
            job_id=lead.post_id,
            db_path=self.db_path,
        )
        return {
            "status": "APPLIED",
            "recipient": recipient,
            "company": lead.company,
            "role_title": lead.role_title,
            "location": lead.location,
            "match_score": lead.match_score,
            "subject": subject,
            "resume": os.path.basename(self.resume_path),
            "db_recorded": ok,
            "job_id": saved_id,
            "sent": True,
        }

    def write_digest_report(self, result: Dict[str, Any]) -> str:
        """Writes markdown and JSON digests under logs/ for review and manual DMs."""
        log_dir = os.path.join(WORKSPACE_DIR, "logs")
        os.makedirs(log_dir, exist_ok=True)
        md_path = os.path.join(log_dir, "linkedin_post_applications_latest.md")
        json_path = os.path.join(log_dir, "linkedin_post_leads.json")

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M IST")
        lines = [
            f"# LinkedIn Hiring Posts Application Digest ({now_str})",
            "",
            f"- **Mode:** {'DRY-RUN' if result.get('dry_run') else 'LIVE'}",
            f"- **Discovered Posts:** {result.get('discovered', 0)}",
            f"- **Eligible Matches:** {result.get('eligible', 0)}",
            f"- **Direct Emails Sent:** {result.get('emails_sent', 0)}",
            f"- **ATS Links Applied:** {result.get('ats_applied', 0)}",
            f"- **DM-Only Leads:** {len(result.get('dm_leads', []))}",
            "",
            "## Direct Email Applications",
        ]
        email_ops = result.get("email_results") or []
        if email_ops:
            for op in email_ops:
                lines.append(
                    f"- **{op.get('status')}** | `{op.get('recipient')}` | "
                    f"{op.get('role_title', 'Role')} @ {op.get('company', 'Company')} "
                    f"({op.get('location', 'India')}, score={op.get('match_score', '-')})"
                )
        else:
            lines.append("- None this run.")

        dm_leads = result.get("dm_leads") or []
        lines.extend(["", "## DM-Only Hiring Leads (Manual Private DM Recommended — Never Auto-Commented)"])
        if dm_leads:
            for item in dm_leads[:15]:
                lines.extend([
                    f"### {item.get('role_title')} @ {item.get('company')} ({item.get('location')}, score={item.get('match_score')})",
                    f"- **Author:** {item.get('author_name')} ({item.get('post_age')}) — {item.get('author_profile_url') or 'N/A'}",
                    f"- **Post Links:** {', '.join(item.get('linkedin_job_urls') or []) or 'DM author directly'}",
                    f"- **Suggested Private DM:** `{item.get('suggested_dm', '')}`",
                    f"- **Optional Comment (only if explicitly requested):** `{item.get('suggested_comment', '')}`",
                    "",
                ])
        else:
            lines.append("- None this run.")

        with open(md_path, "w", encoding="utf-8") as f_md:
            f_md.write("\n".join(lines).strip() + "\n")

        with open(json_path, "w", encoding="utf-8") as f_js:
            json.dump(result, f_js, indent=2, default=str)

        return md_path

    def run_cycle(
        self,
        limit: int = 10,
        queries: Optional[List[str]] = None,
        date_posted: str = "past-week",
        dry_run: bool = False,
        headless: bool = True,
        apply_ats_links: bool = True,
    ) -> Dict[str, Any]:
        """
        Executes discovery + filtering + direct email dispatch (with resume PDF) +
        optional embedded external ATS link applications + digest report generation.
        """
        try:
            running = asyncio.get_running_loop().is_running()
        except RuntimeError:
            running = False

        if running:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=1) as pool:
                leads = pool.submit(
                    lambda: asyncio.run(
                        self.discover_hiring_posts(
                            queries=queries,
                            date_posted=date_posted,
                            headless=headless,
                        )
                    )
                ).result()
        else:
            leads = asyncio.run(
                self.discover_hiring_posts(
                    queries=queries,
                    date_posted=date_posted,
                    headless=headless,
                )
            )

        eligible_leads = [ld for ld in leads if ld.eligible]
        rejected_leads = [ld for ld in leads if not ld.eligible]

        # Prioritize: has direct email -> Hyderabad -> highest match score
        eligible_leads.sort(
            key=lambda ld: (
                1 if ld.emails else 0,
                1 if "hyderabad" in (ld.location or "").lower() else 0,
                ld.match_score,
            ),
            reverse=True,
        )

        email_results: List[Dict[str, Any]] = []
        emails_sent = 0
        emails_dry_ready = 0
        ats_results: List[Dict[str, Any]] = []
        ats_applied = 0
        dm_leads: List[Dict[str, Any]] = []

        for ld in eligible_leads:
            if ld.emails:
                if (emails_sent + emails_dry_ready) >= int(limit):
                    continue
                target_email = ld.emails[0]
                res = self.send_direct_email(ld, target_email, dry_run=dry_run)
                res.setdefault("company", ld.company)
                res.setdefault("role_title", ld.role_title)
                res.setdefault("location", ld.location)
                res.setdefault("match_score", ld.match_score)
                res.setdefault("author_name", ld.author_name)
                res.setdefault("post_age", ld.post_age)
                email_results.append(res)
                if res.get("status") == "APPLIED":
                    emails_sent += 1
                    if not dry_run:
                        time.sleep(3.0)
                elif res.get("status") == "DRY_RUN_READY":
                    emails_dry_ready += 1
                elif res.get("status") == "DAILY_CAP_REACHED":
                    break
                continue

            # Embedded external ATS URLs (Greenhouse / Lever / Ashby / Workday)
            if ld.ats_urls:
                from naukari_pro.modules.career_portals import CareerPortalFiller
                filler = CareerPortalFiller(db_path=self.db_path)
                handled_ats = False
                for ats_url in ld.ats_urls[:2]:
                    ats_name = filler.detect_ats(ats_url)
                    if ats_name in ("Generic Portal", "LinkedIn"):
                        continue
                    handled_ats = True
                    if not apply_ats_links:
                        continue
                    try:
                        fill_res = filler.fill(
                            portal_url=ats_url,
                            company=ld.company,
                            role=ld.role_title,
                            headless=headless,
                            dry_run=dry_run,
                            raw_jd=ld.post_body,
                            match_score=int(ld.match_score),
                            auto_submit=True,
                        )
                        submitted = bool(getattr(fill_res, "submitted", False))
                        status_str = getattr(fill_res, "status", None) or ("SUBMITTED" if submitted else "PROCESSED")
                        ats_results.append({
                            "url": ats_url,
                            "ats": ats_name,
                            "company": ld.company,
                            "role_title": ld.role_title,
                            "submitted": submitted,
                            "status": status_str,
                        })
                        if submitted:
                            ats_applied += 1
                    except Exception as e_ats:
                        ats_results.append({
                            "url": ats_url,
                            "ats": ats_name,
                            "company": ld.company,
                            "role_title": ld.role_title,
                            "submitted": False,
                            "status": f"ERROR: {e_ats}",
                        })
                    break
                if handled_ats and apply_ats_links:
                    continue

            # DM / manual application leads (never auto-commented publicly)
            templates = compose_manual_dm_and_comment(ld)
            dm_leads.append({
                "post_id": ld.post_id,
                "author_name": ld.author_name,
                "author_profile_url": ld.author_profile_url,
                "post_age": ld.post_age,
                "company": ld.company,
                "role_title": ld.role_title,
                "location": ld.location,
                "match_score": ld.match_score,
                "linkedin_job_urls": ld.linkedin_job_urls,
                "ats_urls": ld.ats_urls,
                "suggested_dm": templates["dm"],
                "suggested_comment": templates["comment"],
            })

        result = {
            "status": "DRY_RUN_COMPLETED" if dry_run else "COMPLETED",
            "dry_run": dry_run,
            "discovered": len(leads),
            "eligible": len(eligible_leads),
            "rejected": len(rejected_leads),
            "emails_sent": emails_sent,
            "emails_dry_ready": emails_dry_ready,
            "ats_applied": ats_applied,
            "email_results": email_results,
            "ats_results": ats_results,
            "dm_leads": dm_leads,
            "rejected_sample": [
                {
                    "author": r.author_name,
                    "role": r.role_title,
                    "company": r.company,
                    "min_yoe": r.min_yoe,
                    "salary_lpa_max": r.salary_lpa_max,
                    "emails": r.emails,
                    "reason": r.filter_reason,
                }
                for r in rejected_leads[:20]
            ],
            "eligible_leads": [asdict(ld) for ld in eligible_leads],
        }
        digest_path = self.write_digest_report(result)
        result["digest_path"] = digest_path
        return result
