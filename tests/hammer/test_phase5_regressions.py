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
