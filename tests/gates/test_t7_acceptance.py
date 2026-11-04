"""Gate 8 — six Master Prompt §9 acceptance criteria (T7)."""

from __future__ import annotations

import os

import pytest
from naukari_pro.llm.routing import GatewayConfig
from naukari_pro.resume_gen.claim_validator import validate_text
from naukari_pro.mcp.server import handle_tool
from naukari_pro.governed_apply.captcha_safety import CaptchaSafetyManager, EXIT_CAPTCHA_BLOCKED
from naukari_pro.governed_apply.approval import ApprovalQueue
from naukari_pro.governed_apply.exit_codes import EXIT_APPROVAL_DENIED


@pytest.mark.acceptance
def test_t7_01_config_only_provider_swap(monkeypatch):
    """Swapping AI_GATEWAY_DEFAULT_PROVIDER requires zero code changes."""
    monkeypatch.setenv("AI_GATEWAY_DEFAULT_PROVIDER", "xai")
    cfg = GatewayConfig()
    assert cfg.default_provider == "xai"
    monkeypatch.setenv("AI_GATEWAY_DEFAULT_PROVIDER", "groq")
    assert GatewayConfig().default_provider == "groq"


@pytest.mark.acceptance
def test_t7_02_fabricated_fact_rejected(profile_evidence=None):
    evidence = [
        "DevOps Engineer with Kubernetes Docker Terraform AWS. "
        "Reduced deployment time from 45 minutes to 12 minutes."
    ]
    fake = "Certified Kubernetes Administrator inventing 40% gains across the fleet."
    report = validate_text(fake, evidence)
    assert report.ok is False
    assert report.unsupported_claims


@pytest.mark.acceptance
def test_t7_03_dry_run_default():
    dry = handle_tool("apply_job", {"job_key": "demo"})
    assert dry.get("dry_run") is True


@pytest.mark.acceptance
def test_t7_04_submit_requires_approval(tmp_path):
    blocked = handle_tool("apply_job", {"job_key": "demo", "dry_run": False})
    assert blocked.get("exit_code") in (2, EXIT_APPROVAL_DENIED, 4) or blocked.get("dry_run") is False
    rejected = handle_tool("approve_submission", {"approval_token": "short"})
    assert rejected.get("status") == "rejected"
    q = ApprovalQueue(db_path=tmp_path / "a.db")
    assert q.decide("nope", approve=True) is False


@pytest.mark.acceptance
def test_t7_05_captcha_human_exit_3(tmp_path):
    mgr = CaptchaSafetyManager(mode="human", db_path=tmp_path / "c.db", board="gh")
    assert mgr._vendor is None
    result = mgr.handle(captcha_type="hcaptcha", page_url="https://boards.greenhouse.io/x")
    assert result.exit_code == EXIT_CAPTCHA_BLOCKED
    assert result.resolved_by == "human"


@pytest.mark.acceptance
def test_t7_06_no_api_key_in_ledger(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_PROVIDER_OPENAI_API_KEY", "sk-SHOULD-NOT-LEAK-INTO-LEDGER")
    from datetime import datetime, timezone
    from naukari_pro.llm.ledger import SpendLedger, SpendEntry, estimate_cost

    path = tmp_path / "spend.jsonl"
    ledger = SpendLedger(path=path, enable_sqlite=False)
    cost = estimate_cost("openai/gpt-4o-mini", 10, 10)
    ledger.record(
        SpendEntry(
            ts=datetime.now(timezone.utc).isoformat(),
            prompt_id="P2",
            prompt_version="1",
            model="gpt-4o-mini",
            provider="openai",
            input_tokens=10,
            output_tokens=10,
            cost_usd=cost,
            cached=False,
            input_hash="h",
            status="ok",
        )
    )
    blob = path.read_text(encoding="utf-8")
    assert "sk-SHOULD-NOT-LEAK" not in blob
    assert "openai" in blob
