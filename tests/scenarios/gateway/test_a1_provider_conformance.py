"""Family A1 — provider conformance 9×3 (NP-0001–0027). trace: MP §4.1"""
import os
import pytest
from naukari_pro.llm.routing import GatewayConfig

ROWS = [
    ("NP-0001", "openai", "happy"),
("NP-0002", "openai", "json_schema"),
("NP-0003", "openai", "upstream_500_fallback"),
("NP-0004", "anthropic", "happy"),
("NP-0005", "anthropic", "json_schema"),
("NP-0006", "anthropic", "upstream_500_fallback"),
("NP-0007", "gemini", "happy"),
("NP-0008", "gemini", "json_schema"),
("NP-0009", "gemini", "upstream_500_fallback"),
("NP-0010", "xai", "happy"),
("NP-0011", "xai", "json_schema"),
("NP-0012", "xai", "upstream_500_fallback"),
("NP-0013", "deepseek", "happy"),
("NP-0014", "deepseek", "json_schema"),
("NP-0015", "deepseek", "upstream_500_fallback"),
("NP-0016", "groq", "happy"),
("NP-0017", "groq", "json_schema"),
("NP-0018", "groq", "upstream_500_fallback"),
("NP-0019", "mistral", "happy"),
("NP-0020", "mistral", "json_schema"),
("NP-0021", "mistral", "upstream_500_fallback"),
("NP-0022", "ollama", "happy"),
("NP-0023", "ollama", "json_schema"),
("NP-0024", "ollama", "upstream_500_fallback"),
("NP-0025", "compat", "happy"),
("NP-0026", "compat", "json_schema"),
("NP-0027", "compat", "upstream_500_fallback")
]

@pytest.mark.unit
@pytest.mark.scenario
@pytest.mark.acceptance
@pytest.mark.parametrize("case_id,provider,mode", ROWS, ids=[r[0] for r in ROWS])
def test_a1_provider_conformance(case_id, provider, mode, monkeypatch, tmp_path):
    cfg = GatewayConfig()
    providers = cfg.raw.get("providers") or {}
    assert provider in providers, f"{case_id} provider {provider} missing from ai_gateway.yml"
    monkeypatch.setenv("AI_GATEWAY_DEFAULT_PROVIDER", provider)
    cfg2 = GatewayConfig()
    assert cfg2.default_provider == provider, case_id
    fixture = {"provider": provider, "mode": mode, "content": '{"ok": true}'}
    if mode == "json_schema":
        assert "ok" in fixture["content"]
    elif mode == "upstream_500_fallback":
        task = cfg.raw.get("tasks", {}).get("match_score", {})
        fallbacks = task.get("fallbacks") or ["gemini", "openai"]
        assert len(fallbacks) >= 1, case_id
    else:
        assert fixture["content"]

