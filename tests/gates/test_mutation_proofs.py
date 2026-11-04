"""
Gate 3 / §7 — prove five red-team scenarios go red when their defense is mutated.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from naukari_pro.resume_gen.claim_validator import GroundingReport


def _always_ok(text, evidence, **kwargs):
    return GroundingReport(
        ok=True,
        sentences=[],
        unsupported_claims=[],
        dropped_sentences=[],
        novelty_ratio=0.0,
    )


@pytest.mark.redteam
def test_mutation_novelty_reddens(monkeypatch):
    import naukari_pro.resume_gen.claim_validator as cv
    from tests.scenarios.verifier import test_d2_novelty_cap as mod

    monkeypatch.setattr(cv, "validate_text", _always_ok)
    monkeypatch.setattr(mod, "validate_text", _always_ok)
    with pytest.raises(AssertionError):
        mod.test_d2_novelty_cap(
            "NP-0371",
            "I orchestrated a world-class synergy of container orchestration paradigms across polyglot estates.",
            False,
        )


@pytest.mark.redteam
def test_mutation_puffery_reddens(monkeypatch):
    import naukari_pro.resume_gen.claim_validator as cv
    from tests.scenarios.verifier import test_d3_puffery as mod

    never = re.compile(r"a^")
    monkeypatch.setattr(cv, "PUFFERY", never)
    monkeypatch.setattr(mod, "PUFFERY", never)
    monkeypatch.setattr(cv, "validate_text", _always_ok)
    monkeypatch.setattr(mod, "validate_text", _always_ok)
    with pytest.raises(AssertionError):
        mod.test_d3_puffery("NP-0381", "world-class")


@pytest.mark.redteam
def test_mutation_allowlist_reddens(monkeypatch):
    import naukari_pro.captcha.safety as safety
    from tests.scenarios.captcha import test_f2_mode_matrix as mod

    monkeypatch.setattr(safety, "domain_allowed", lambda domain, allowlist: True)
    # Rebuild manager uses domain_allowed from safety module at call time — patch CaptchaSafetyManager.handle path
    monkeypatch.setattr(mod, "CaptchaSafetyManager", safety.CaptchaSafetyManager)
    with pytest.raises(AssertionError):
        # empty allowlist should deny; with always-allow, vendor may be called
        mod.test_f2_mode_matrix(
            "NP-0707",
            "vendor",
            "k",
            [],
            0.0,
            5.0,
            "boards.greenhouse.io",
            False,
        )


@pytest.mark.redteam
def test_mutation_hmac_reddens(monkeypatch):
    import naukari_pro.api.app as app
    from tests.scenarios.security import test_i3_hmac_webhooks as mod

    monkeypatch.setattr(app, "verify_webhook_signature", lambda *a, **k: True)
    monkeypatch.setattr(mod, "verify_webhook_signature", lambda *a, **k: True)
    with pytest.raises(AssertionError):
        mod.test_i3_hmac_webhooks("NP-0891", 0)  # idx%3==0 → forged sig must be False


@pytest.mark.redteam
def test_mutation_path_reddens(monkeypatch, tmp_path):
    import naukari_pro.security.paths as paths
    from tests.scenarios.security import test_i4_path_traversal as mod

    monkeypatch.setattr(
        paths,
        "resolve_safe_path",
        lambda data_dir, user_path: Path(data_dir) / "x",
    )
    monkeypatch.setattr(
        mod,
        "resolve_safe_path",
        lambda data_dir, user_path: Path(data_dir) / "x",
    )
    with pytest.raises((AssertionError, pytest.fail.Exception)):
        mod.test_i4_path_traversal("NP-0908", "../etc/passwd", False, tmp_path)
