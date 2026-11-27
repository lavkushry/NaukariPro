"""
Offline unit tests for naukari_pro.modules.linkedin_post_apply.
Covers header/body splitting, email & ATS link extraction, YOE/salary parsing,
role/company/location gating, factual email composition, DB deduplication, and SMTP caps.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from naukari_pro.modules.db import get_db_connection, init_db
from naukari_pro.modules.linkedin_post_apply import (
    LinkedInPostApplyEngine,
    LinkedInPostLead,
    compose_application_email,
    compose_manual_dm_and_comment,
    decode_linkedin_redirect,
    evaluate_hiring_post,
    extract_apply_links,
    extract_emails_from_post,
    extract_role_and_company,
    parse_disclosed_salary_lpa,
    parse_experience_range,
    split_card_header_and_body,
)


SAMPLE_SDUI_CARD_TEXT = """Feed post

Dhananjay H K
 • 2nd
Senior HR Manager | Freelance HR Consultant | 10 Years of Experience | Talent Acquisition

12m •

Follow

Hiring: DevOps Engineer
Location: Hyderabad (Hybrid)
Experience: 2-4 Years
Budget: 20-26 LPA

Required Skills:
Kubernetes (EKS), Docker, Terraform, Ansible, GitHub Actions, AWS, Prometheus, Python.

Interested candidates, please share your updated resume to hiring@acmecorp.in

Like
Comment
"""


def test_split_card_header_and_body_ignores_author_bio():
    header, age, body = split_card_header_and_body(SAMPLE_SDUI_CARD_TEXT)
    assert "Senior HR Manager" in header
    assert "10 Years of Experience" in header
    assert age == "12m"
    assert "Senior HR Manager" not in body
    assert "10 Years of Experience" not in body
    assert body.startswith("Hiring: DevOps Engineer")
    assert "Like" not in body


def test_extract_emails_filters_own_cgi_and_noreply():
    body = (
        "Send CVs to hr@targetcloud.io, lav84095@gmail.com, lavkushry@gmail.com, "
        "talent@cgi.com, noreply@targetcloud.io, and careers@targetcloud.io."
    )
    emails = extract_emails_from_post(
        body,
        mailto_hrefs=["mailto:hr@targetcloud.io", "mailto:support@example.com"],
    )
    assert emails == ["hr@targetcloud.io", "careers@targetcloud.io"]


def test_extract_apply_links_decodes_safety_go_and_blocks_whatsapp():
    raw_links = [
        {
            "href": "https://www.linkedin.com/in/someone/",
            "text": "Recruiter Name",
        },
        {
            "href": "https://www.linkedin.com/safety/go/?url=https%3A%2F%2Fboards.greenhouse.io%2Fdataco%2Fjobs%2F123456&urlhash=abc",
            "text": "https://boards.greenhouse.io/dataco/jobs/123456",
        },
        {
            "href": "https://www.linkedin.com/safety/go/?url=https%3A%2F%2Fchat.whatsapp.com%2FXYZ123&urlhash=xyz",
            "text": "WhatsApp group",
        },
        {
            "href": "https://www.linkedin.com/safety/go/?url=https%3A%2F%2Flnkd.in%2FgczAaNqT&urlhash=8IDp",
            "text": "https://lnkd.in/gczAaNqT",
        },
        {
            "href": "https://www.linkedin.com/jobs/view/4495310364/?trackingId=abc",
            "text": "View job",
        },
    ]
    post_body = "Join our exclusive WhatsApp group for job updates:\nhttps://lnkd.in/gczAaNqT"
    li_jobs, ats_urls = extract_apply_links(raw_links, post_body=post_body)
    assert li_jobs == ["https://www.linkedin.com/jobs/view/4495310364/"]
    assert ats_urls == ["https://boards.greenhouse.io/dataco/jobs/123456"]
    assert decode_linkedin_redirect(raw_links[1]["href"]) == "https://boards.greenhouse.io/dataco/jobs/123456"


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Experience: 2-4 Years", (2.0, 4.0)),
        ("Exp: 2–5 yrs", (2.0, 5.0)),
        ("1 to 3 years experience", (1.0, 3.0)),
        ("Experience: 5+ Years", (5.0, None)),
        ("Minimum 3+ yrs in K8s", (3.0, None)),
        ("20 LPA budget with no experience range", (None, None)),
    ],
)
def test_parse_experience_range(text, expected):
    assert parse_experience_range(text) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Up to ₹20 LPA", 20.0),
        ("Salary: 12-18 LPA", 18.0),
        ("Budget: 20-26 LPA", 26.0),
        ("CTC: ₹25 Lakhs per annum", 25.0),
        ("Competitive compensation", None),
    ],
)
def test_parse_disclosed_salary_lpa(text, expected):
    assert parse_disclosed_salary_lpa(text) == expected


def _make_lead(**overrides) -> LinkedInPostLead:
    defaults = dict(
        post_id="li_post_test01",
        author_name="Ananya Verma",
        author_profile_url="https://www.linkedin.com/in/ananya-verma/",
        author_headline="Senior Talent Acquisition Specialist | 10 Years",
        post_age="15m",
        company="AcmeCloud",
        role_title="DevOps Engineer",
        location="Hyderabad",
        min_yoe=2.0,
        max_yoe=4.0,
        salary_lpa_max=25.0,
        post_body=(
            "We are hiring for DevOps Engineer in Hyderabad!\n"
            "Experience: 2-4 years\nBudget: 20-25 LPA\n"
            "Skills: AWS, Kubernetes, Terraform, Ansible, Docker, CI/CD, Python.\n"
            "Send your resume to hiring@acmecloud.io"
        ),
        emails=["hiring@acmecloud.io"],
        ats_urls=[],
        linkedin_job_urls=[],
    )
    defaults.update(overrides)
    return LinkedInPostLead(**defaults)


def test_evaluate_hiring_post_gates():
    # Eligible Hyderabad 2-4 YOE 25 LPA DevOps post passes even though author bio has 'Senior'
    ok, score, _ = evaluate_hiring_post(_make_lead())
    assert ok is True
    assert score >= 75.0

    # 5+ years rejected
    ok_exp, _, r_exp = evaluate_hiring_post(_make_lead(min_yoe=5.0, max_yoe=8.0))
    assert ok_exp is False and "YOE" in r_exp

    # Senior title in post body rejected
    ok_sen, _, _ = evaluate_hiring_post(
        _make_lead(
            role_title="Senior DevOps Engineer",
            post_body="We're hiring Senior DevOps Engineer in Hyderabad 2-4 years hr@acme.io",
        )
    )
    assert ok_sen is False

    # Below 20 LPA rejected
    ok_sal, _, r_sal = evaluate_hiring_post(_make_lead(salary_lpa_max=15.0))
    assert ok_sal is False and "LPA" in r_sal

    # Employer CGI safety exclusion
    ok_cgi, _, _ = evaluate_hiring_post(_make_lead(company="CGI India", emails=["hr@cgi.com"]))
    assert ok_cgi is False

    # Job seeker post rejected
    ok_seeker, _, _ = evaluate_hiring_post(
        _make_lead(
            post_body="I am looking for a DevOps Engineer role in Hyderabad 2.5 years #opentowork email test@acme.io",
        )
    )
    assert ok_seeker is False

    # Foreign W2 role rejected
    ok_us, _, _ = evaluate_hiring_post(
        _make_lead(
            location="Texas, USA",
            post_body="Hiring DevOps Engineer in Austin Texas US only W2/C2C 2-4 years send resume hr@usco.com",
        )
    )
    assert ok_us is False

    # Data Scientist / QA rejected by role_guard
    ok_qa, _, _ = evaluate_hiring_post(
        _make_lead(
            role_title="QA Automation Engineer",
            post_body="Hiring QA Automation Engineer in Hyderabad 2-4 years send resume hr@acmecloud.io",
        )
    )
    assert ok_qa is False


def test_extract_role_and_company_parses_email_domain():
    role, company = extract_role_and_company(
        "We're Hiring | MLOps Engineer | Hyderabad | 2-4 Years\nShare CV at talent@cloudscale.ai",
        emails=["talent@cloudscale.ai"],
        company_links=[],
    )
    assert "MLOps Engineer" in role
    assert company == "Cloudscale"


def test_compose_application_email_and_manual_dm_are_factual():
    lead = _make_lead(role_title="MLOps & Platform Engineer", company="CloudScale")
    subject, body = compose_application_email(lead)
    assert "MLOps & Platform Engineer" in subject
    assert "CloudScale" in subject
    assert "CGI India" in body
    assert "HFCL Limited" in body
    assert "2.5 Years" in body
    assert "Hyderabad" in body
    assert "15 Days" in body
    assert "https://www.linkedin.com/in/lavkushry/" in body
    assert "https://github.com/lavkushry" in body
    assert "Lavkush_Kumar_MLOps_Resume.pdf" in body
    assert "AegisAgent" in body

    dm_pack = compose_manual_dm_and_comment(lead)
    assert "CGI India" in dm_pack["dm"]
    assert len(dm_pack["dm"]) < 400


def test_engine_send_direct_email_dry_run_dedup_and_cap(tmp_path: Path, monkeypatch):
    db_file = str(tmp_path / "test_jobs.db")
    pdf_file = tmp_path / "Lavkush_Kumar_MLOps_Resume.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\n%mock-resume-payload\n" + b"0" * 1500)
    init_db(db_file)

    monkeypatch.setenv("GMAIL_USER", "lav84095@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "test_app_pw")

    engine = LinkedInPostApplyEngine(
        db_path=db_file,
        resume_path=str(pdf_file),
        max_daily_emails=1,
    )
    lead1 = _make_lead(post_id="li_post_001", emails=["hr1@acmecloud.io"])

    # Dry-run does not invoke SMTP and does not insert DB row
    with patch("naukari_pro.modules.linkedin_post_apply.smtplib.SMTP") as mock_smtp:
        res_dry = engine.send_direct_email(lead1, "hr1@acmecloud.io", dry_run=True)
        assert res_dry["status"] == "DRY_RUN_READY"
        assert res_dry["resume"] == "Lavkush_Kumar_MLOps_Resume.pdf"
        assert mock_smtp.call_count == 0

    # Live send attaches PDF, calls SMTP once, records platform='linkedin_post'
    smtp_inst = MagicMock()
    smtp_ctx = MagicMock()
    smtp_ctx.__enter__.return_value = smtp_inst
    smtp_ctx.__exit__.return_value = False
    with patch("naukari_pro.modules.linkedin_post_apply.smtplib.SMTP", return_value=smtp_ctx) as mock_smtp:
        res_live = engine.send_direct_email(lead1, "hr1@acmecloud.io", dry_run=False)
        assert res_live["status"] == "APPLIED"
        assert res_live["sent"] is True
        assert res_live["db_recorded"] is True
        assert mock_smtp.call_count == 1
        assert smtp_inst.sendmail.call_count == 1
        raw_mime = smtp_inst.sendmail.call_args[0][2]
        assert "Lavkush_Kumar_MLOps_Resume.pdf" in raw_mime

        conn = get_db_connection(db_file)
        row = conn.execute("SELECT platform, status, job_url FROM applied_jobs WHERE job_id = ?", ("li_post_001",)).fetchone()
        conn.close()
        assert row is not None
        assert row["platform"] == "linkedin_post"
        assert row["status"] == "APPLIED"
        assert row["job_url"] == "mailto:hr1@acmecloud.io"

        # Same recipient blocked by cooldown/dedup on second attempt
        res_dup = engine.send_direct_email(lead1, "hr1@acmecloud.io", dry_run=False)
        assert res_dup["status"] == "SKIPPED_COOLDOWN"

        # Different recipient hits max_daily_emails=1 cap
        lead2 = _make_lead(post_id="li_post_002", emails=["hr2@othercloud.io"])
        res_cap = engine.send_direct_email(lead2, "hr2@othercloud.io", dry_run=False)
        assert res_cap["status"] == "DAILY_CAP_REACHED"
