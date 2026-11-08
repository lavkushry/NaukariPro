"""Phase-5 examiner findings — regression blows (must stay contained)."""

from __future__ import annotations

import os

import pytest

from naukari_pro.errors import ValidationError
from naukari_pro.hammer_safe import validate_job_url
from naukari_pro.resume_gen.claim_validator import validate_text
from naukari_pro.governed_apply.fill_verify import verify_field
from naukari_pro.captcha.resolver import CaptchaResolverChain


@pytest.mark.hammer
def test_p5_f1_empty_expected_rejects_fabricated_dom():
    r = verify_field(
        field_id="ctc",
        expected="",
        dom_value="99999999",
        model_value="",
        check_validity=True,
    )
    assert r.ok is False
    assert r.layer1_dom is False


@pytest.mark.hammer
def test_p5_f2_number_substring_rejected():
    report = validate_text("Reduced costs by 1%.", ["Reduced costs by 10%."])
    assert report.ok is False
    assert any("unsourced_number" in r for s in report.sentences for r in s.reasons)


@pytest.mark.hammer
def test_p5_f3_loopback_variants_blocked():
    for url in (
        "http://127.1.1.1:8080/admin",
        "http://127.255.255.255/",
        "http://2130706433/",
    ):
        with pytest.raises(ValidationError):
            validate_job_url(url)


@pytest.mark.hammer
def test_p5_f4_empty_token_passthrough_fails_closed():
    html = '<input name="g-recaptcha-response" value=""><div data-size="invisible"></div>'
    r = CaptchaResolverChain(mode="human").resolve_html(
        html, page_url="https://boards.example.com/apply"
    )
    assert r.resolved is False
    assert r.exit_code == 3


@pytest.mark.hammer
def test_p5_f5_api_requires_key(monkeypatch):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from naukari_pro.api.app import create_api_app

    monkeypatch.delenv("NAUKARI_API_KEY", raising=False)
    monkeypatch.delenv("NAUKARI_API_DEV_OPEN", raising=False)
    # Recreate with clean env
    os.environ.pop("NAUKARI_API_KEY", None)
    os.environ.pop("NAUKARI_API_DEV_OPEN", None)
    app = create_api_app()
    client = TestClient(app)
    assert client.get("/tools").status_code == 401


# --- Phase-5 re-exam 2026-11-08 (a9d270ab) ---------------------------------


@pytest.mark.hammer
def test_p5b_f1_negated_confirmation_not_applied():
    from naukari_pro.governed_apply.confirmation import detect_submission_confirmation

    r = detect_submission_confirmation(page_text="error: application submitted failed")
    assert r.confirmed is False


@pytest.mark.hammer
def test_p5b_f2_hex_octal_nip_ssrf_blocked():
    for url in (
        "http://0x7f000001/",
        "http://0177.0.0.1/",
        "http://127.0.0.1.nip.io/",
    ):
        with pytest.raises(ValidationError):
            validate_job_url(url)


@pytest.mark.hammer
def test_p5b_f3_ms_suffix_numbers_grounded():
    report = validate_text(
        "Reduced latency from 400ms to 999ms.",
        ["Reduced latency from 400ms to 180ms"],
    )
    assert report.ok is False


@pytest.mark.hammer
def test_p5b_f4_aiza_redacted_in_pii_module():
    from naukari_pro.security.pii import redact_pii, secrets_in_text

    leak = "AIzaSyAbCdEfGhIjKlMnOpQrStUvWxYz123456"
    assert "[REDACTED" in redact_pii(leak)
    assert secrets_in_text(leak)


@pytest.mark.hammer
def test_p5b_f5_submit_requires_confirmation_proof(tmp_path):
    from naukari_pro.errors import IntegrityError
    from naukari_pro.governed_apply.approval import ApprovalQueue

    q = ApprovalQueue(db_path=tmp_path / "a.db")
    with pytest.raises(IntegrityError):
        q.record_confirmed_submit(
            job_url="https://example.com/j",
            company="Co",
            title="Eng",
            confirmation_text=None,
            confirmation_url=None,
        )


@pytest.mark.hammer
def test_p5c_f6_url_confirm_voided_by_error_text():
    from naukari_pro.governed_apply.confirmation import detect_submission_confirmation

    r = detect_submission_confirmation(
        page_text="error: submission failed",
        page_url="https://boards.example.com/thanks",
    )
    assert r.confirmed is False


@pytest.mark.hammer
def test_p5c_f7_unicode_digit_ssrf_blocked():
    for url in (
        "http://①②⑦.⓪.⓪.①/",
        "http://１２７.０.０.１/",
    ):
        with pytest.raises(ValidationError):
            validate_job_url(url)
