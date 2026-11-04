"""WS5: sensitivity, dry-run audit, filled!=applied, approval expiry."""

from __future__ import annotations

from naukari_pro.governed_apply.approval import ApprovalQueue
from naukari_pro.governed_apply.attention import detect_blocker, BlockerClass
from naukari_pro.governed_apply.confirmation import detect_submission_confirmation
from naukari_pro.governed_apply.pipeline import GovernedApplyPipeline
from naukari_pro.governed_apply.sensitivity import Sensitivity, classify_question, mask_for_log


def test_sensitivity_classes():
    assert classify_question("Enter password") == Sensitivity.NEVER
    assert classify_question("Are you authorized to work in India?") == Sensitivity.LEGAL
    assert classify_question("Expected CTC") == Sensitivity.SENSITIVE
    assert classify_question("Email address") == Sensitivity.CONTACT
    assert classify_question("Years of Spark experience") == Sensitivity.JOB_SPECIFIC
    assert "***" in mask_for_log("secretvalue", Sensitivity.SENSITIVE)


def test_dry_run_audits_zero_submissions(tmp_path):
    store = ApprovalQueue(db_path=tmp_path / "gov.db")
    pipe = GovernedApplyPipeline(
        {"email": "a@b.com", "phone": "999", "name": "Lavkush", "skills": ["Python"], "yoe": 2.5},
        dry_run=True,
        auto_submit=False,
        store=store,
    )
    fields = [
        {"id": "email", "label": "Email", "type": "email", "required": True},
        {"id": "phone", "label": "Phone", "type": "tel"},
        {"id": "yoe", "label": "Years of experience", "type": "text"},
        {"id": "pwd", "label": "Password", "type": "password"},
    ]
    result = pipe.run_job(
        {
            "url": "https://boards.greenhouse.io/acme/jobs/1",
            "company": "Acme",
            "title": "Data Engineer",
            "fit_score": 90,
            "coverage_pct": 80,
            "ats": "greenhouse",
        },
        dom_fields=fields,
        host="boards.greenhouse.io",
    )
    assert result.status == "filled"
    assert result.submitted is False
    assert result.field_audits == 4
    assert store.submission_count() == 0
    audits = store.field_audit_rows(result.job_url)
    assert len(audits) == 4
    assert all(a["dry_run"] == 1 for a in audits)
    # password skipped / never answered in cleartext
    pwd_row = next(a for a in audits if a["field_id"] == "pwd")
    assert pwd_row["action"] == "SKIP"


def test_confirmation_required_for_applied(tmp_path):
    store = ApprovalQueue(db_path=tmp_path / "gov.db")
    pipe = GovernedApplyPipeline(
        {"email": "a@b.com", "name": "Lavkush"},
        dry_run=False,
        auto_submit=True,
        store=store,
    )
    job = {
        "url": "https://jobs.lever.co/acme/2",
        "company": "Acme",
        "title": "Engineer",
        "fit_score": 85,
        "coverage_pct": 75,
        "ats": "lever",
    }
    fields = [{"id": "email", "label": "Email", "type": "email"}]
    # No confirmation → filled only
    r1 = pipe.run_job(job, dom_fields=fields, page_text="Please review", page_url=job["url"], approved=True)
    assert r1.status == "filled"
    assert store.submission_count() == 0
    # With confirmation → applied
    r2 = pipe.run_job(
        {**job, "url": job["url"] + "/x"},
        dom_fields=fields,
        page_text="Thank you for your application!",
        page_url="https://jobs.lever.co/acme/2/confirmation",
        approved=True,
    )
    assert r2.status == "applied"
    assert r2.submitted is True
    assert store.submission_count() == 1


def test_captcha_never_silent():
    assert detect_blocker("Please complete the reCAPTCHA to continue") == BlockerClass.CAPTCHA


def test_detect_confirmation_patterns():
    ok = detect_submission_confirmation(
        page_text="Your application has been submitted successfully.",
        page_url="https://example.com/jobs/1",
    )
    assert ok.confirmed
