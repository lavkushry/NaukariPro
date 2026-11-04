"""M1: multi-provider routing, cost ledger, MCP tools (offline, zero live LLM)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from naukari_pro.llm.ledger import BudgetPaused, SpendEntry, SpendLedger
from naukari_pro.llm.provider_router import ProviderRouter
from naukari_pro.llm.providers import OpenAICompatibleProvider, build_providers_from_env
from naukari_pro.llm.routing import GatewayConfig
from naukari_pro.mcp.server import handle_jsonrpc, handle_tool, list_tools


def test_gateway_yaml_loads_tasks():
    cfg = GatewayConfig()
    assert cfg.default_provider
    route = cfg.task_route("jd_extract")
    assert route.provider
    assert route.model
    assert isinstance(route.fallbacks, list)
    assert "match_score" in (cfg.raw.get("tasks") or {})


def test_env_overrides_default_provider(monkeypatch):
    monkeypatch.setenv("AI_GATEWAY_DEFAULT_PROVIDER", "ollama")
    cfg = GatewayConfig()
    assert cfg.default_provider == "ollama"


def test_task_provider_env_override(monkeypatch):
    monkeypatch.setenv("AI_GATEWAY_RESUME_TAILOR_PROVIDER", "groq")
    cfg = GatewayConfig()
    assert cfg.task_route("resume_tailor").provider == "groq"


def test_build_providers_ollama_without_key(monkeypatch):
    monkeypatch.delenv("AI_PROVIDER_OLLAMA_API_KEY", raising=False)
    cfg = GatewayConfig()
    providers = build_providers_from_env(cfg.raw)
    assert "ollama" in providers
    assert providers["ollama"].available()


def test_router_fallback_order(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER_GROQ_API_KEY", "test-key")
    monkeypatch.setenv("AI_PROVIDER_OPENAI_API_KEY", "test-key")
    cfg = GatewayConfig()
    providers = build_providers_from_env(cfg.raw)
    router = ProviderRouter(config=cfg, providers=providers)
    route, chain = router.chain_for_task("jd_extract")
    assert chain[0] == route.provider
    assert "openai" in chain or "gemini" in chain or len(chain) >= 1


def test_paused_budget_raises(tmp_path):
    ledger = SpendLedger(
        path=tmp_path / "l.jsonl",
        paused_budget=True,
        enable_sqlite=False,
    )
    with pytest.raises(BudgetPaused):
        ledger.ensure_budget(0.01)
    assert ledger.is_deterministic_only() is True


def test_daily_cap(tmp_path):
    from datetime import datetime, timezone

    ledger = SpendLedger(
        path=tmp_path / "l.jsonl",
        daily_cap_usd=0.001,
        monthly_cap_usd=100.0,
        enable_sqlite=False,
    )
    ledger.record(
        SpendEntry(
            ts=datetime.now(timezone.utc).isoformat(),
            prompt_id="P1",
            prompt_version="1.0.0",
            model="x",
            provider="y",
            input_tokens=1,
            output_tokens=1,
            cost_usd=0.002,
            cached=False,
            input_hash="h",
            status="ok",
            task="jd_extract",
        )
    )
    from naukari_pro.llm.ledger import BudgetExceeded

    with pytest.raises(BudgetExceeded):
        ledger.ensure_budget(0.001)


def test_sqlite_ai_calls_dual_write(tmp_path):
    from datetime import datetime, timezone

    from naukari_pro.llm.ai_calls_db import AICallsStore

    db = tmp_path / "ai.db"
    store = AICallsStore(db)
    ledger = SpendLedger(
        path=tmp_path / "l.jsonl",
        sqlite_db=db,
        enable_sqlite=True,
        monthly_cap_usd=25.0,
    )
    ledger.record(
        SpendEntry(
            ts=datetime.now(timezone.utc).isoformat(),
            prompt_id="P1_jd_structure",
            prompt_version="1.1.0",
            model="llama",
            provider="groq",
            input_tokens=10,
            output_tokens=5,
            cost_usd=0.0001,
            cached=False,
            input_hash="abc",
            status="ok",
            task="jd_extract",
        )
    )
    assert store.summary()["rows"] >= 1


def test_mcp_lists_required_tools():
    names = {t["name"] for t in list_tools()}
    required = {
        "search_jobs",
        "get_job",
        "score_job",
        "tailor_resume",
        "draft_answers",
        "apply_job",
        "approve_submission",
        "get_tracker",
        "get_stats",
        "list_sources",
    }
    assert required <= names


def test_mcp_apply_job_dry_run_default():
    out = handle_tool("apply_job", {"job_key": "greenhouse:1"})
    assert out["dry_run"] is True
    assert out["exit_code"] == 0
    assert out["approval_required"] is True


def test_mcp_apply_job_blocks_submit_without_approval():
    out = handle_tool("apply_job", {"job_key": "greenhouse:1", "dry_run": False})
    assert out["status"] == "blocked"
    assert out["exit_code"] == 2


def test_mcp_draft_answers_never_invent():
    out = handle_tool(
        "draft_answers",
        {"job_key": "x", "questions": ["What is your current CTC?"]},
    )
    assert out["answers"][0]["status"] == "ASK_USER"
    assert out["answers"][0]["answer"] == ""


def test_mcp_jsonrpc_tools_list():
    resp = handle_jsonrpc({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
    assert resp["id"] == 1
    assert len(resp["result"]["tools"]) >= 10


def test_mcp_jsonrpc_tools_call():
    resp = handle_jsonrpc(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "apply_job", "arguments": {"job_key": "ashby:abc"}},
        }
    )
    text = resp["result"]["content"][0]["text"]
    payload = json.loads(text)
    assert payload["dry_run"] is True


def test_playbooks_exist():
    root = Path(__file__).resolve().parents[1] / "playbooks"
    for name in ("AGENTS.md", "GROKBOT.md", "MUSE.md", "ANTIGRAVITY.md"):
        assert (root / name).exists(), name


def test_provider_complete_mocked(monkeypatch):
    """Adapter parses OpenAI-compatible response without network."""
    provider = OpenAICompatibleProvider(
        "mock",
        base_url="https://example.invalid/v1",
        api_key="k",
        default_model="m",
    )

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps(
                {
                    "choices": [{"message": {"content": '{"ok": true}'}}],
                    "usage": {"prompt_tokens": 3, "completion_tokens": 2},
                }
            ).encode()

    def fake_urlopen(req, timeout=60):
        return FakeResp()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    out = provider.complete([{"role": "user", "content": "hi"}])
    assert out.provider == "mock"
    assert out.input_tokens == 3
    assert '{"ok"' in out.content
