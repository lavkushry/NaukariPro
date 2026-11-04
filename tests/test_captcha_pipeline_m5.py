"""§4.9 captcha package — human default, vendor triple-gate, circuit breaker (offline)."""

from __future__ import annotations

from pathlib import Path

from naukari_pro.captcha.detector import detect_captcha
from naukari_pro.captcha.events import CaptchaEventsStore
from naukari_pro.captcha.resolver import CaptchaResolverChain
from naukari_pro.captcha.safety import CaptchaSafetyManager, Resolution
from naukari_pro.captcha.vendor import build_vendor_client
from naukari_pro.captcha.vlm import try_solve_text_math


def test_human_mode_never_builds_vendor_client(monkeypatch):
    monkeypatch.setenv("CAPTCHA_MODE", "human")
    monkeypatch.setenv("CAPTCHA_VENDOR_API_KEY", "secret-key")
    assert build_vendor_client(mode="human", api_key="secret-key") is None


def test_vendor_requires_mode_allowlist_and_cap(tmp_path):
    db = tmp_path / "c.db"
    # missing allowlist → denied
    mgr = CaptchaSafetyManager(
        mode="vendor",
        api_key="k",
        domains=[],  # empty = deny everywhere
        db_path=db,
        board="gh",
        vendor_callable=lambda **k: True,
    )
    r = mgr.handle(captcha_type="recaptcha_v2", page_url="https://boards.greenhouse.io/x")
    assert r.resolution == Resolution.VENDOR_DENIED
    assert "domain_denied" in r.detail or r.detail.startswith("domain")

    # allowlist + key but over cap
    mgr2 = CaptchaSafetyManager(
        mode="vendor",
        api_key="k",
        domains=["*"],
        spend_24h=9.0,
        cap=5.0,
        db_path=db,
        board="gh",
        vendor_callable=lambda **k: True,
    )
    r2 = mgr2.handle(captcha_type="recaptcha_v2", page_url="https://boards.greenhouse.io/x")
    assert r2.resolution == Resolution.VENDOR_DENIED
    assert r2.detail == "spend_cap"

    # all three satisfied → vendor ok
    mgr3 = CaptchaSafetyManager(
        mode="vendor",
        api_key="k",
        domains=["boards.greenhouse.io"],
        spend_24h=0.0,
        cap=5.0,
        db_path=db,
        board="gh",
        vendor_callable=lambda **k: True,
    )
    r3 = mgr3.handle(captcha_type="recaptcha_v2", page_url="https://boards.greenhouse.io/x")
    assert r3.resolution == Resolution.VENDOR_OK
    assert r3.vendor_attempted is True


def test_detector_and_math_vlm():
    html = '<div class="g-recaptcha" data-sitekey="abc123"></div><script src="recaptcha/api.js"></script>'
    det = detect_captcha(html, page_url="https://example.com/apply")
    assert det is not None
    assert det.type == "recaptcha_v2"
    assert det.sitekey == "abc123"
    assert try_solve_text_math("What is 7 + 5?") == "12"


def test_resolver_chain_defaults_to_human(tmp_path):
    store = CaptchaEventsStore(tmp_path / "c.db", jsonl_path=tmp_path / "c.jsonl")
    chain = CaptchaResolverChain(mode="human", store=store, board="ashby")
    html = '<div class="h-captcha" data-sitekey="xyz"></div>'
    result = chain.resolve_html(html, page_url="https://jobs.ashbyhq.com/x")
    assert result.resolved is False
    assert result.resolved_by == "human"
    assert result.exit_code == 3
    rates = store.rate_by_board()
    assert "ashby" in rates


def test_circuit_breaker_trips(tmp_path):
    db = tmp_path / "c.db"
    for _ in range(5):
        CaptchaSafetyManager(mode="human", db_path=db, board="gh").handle(
            captcha_type="recaptcha_v2", page_url="https://x.com"
        )
    tripped = CaptchaSafetyManager(
        mode="vendor",
        api_key="k",
        domains=["*"],
        db_path=db,
        board="gh",
        vendor_callable=lambda **k: True,
    ).handle(captcha_type="recaptcha_v2", page_url="https://x.com")
    assert tripped.resolution == Resolution.CIRCUIT_OPEN
    assert tripped.exit_code == 3
