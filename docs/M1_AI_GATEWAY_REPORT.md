# M1 — AI Gateway + MCP + Playbooks

**Date:** November 5, 2026  
**Status:** Complete (offline pytest green)

## Objective

Provider-agnostic AI gateway so every AI feature can run on any model, and external AI agents (Grok Bot, Muse, Antigravity, Claude Code, Cursor) can drive NaukariPro via MCP + markdown playbooks.

## Files changed / added

| Path | Change |
|------|--------|
| `config/ai_gateway.yml` | Per-task provider/model/fallback/cost routing |
| `naukari_pro/llm/providers.py` | OpenAI-compatible adapters (Groq, OpenAI, Gemini, xAI, DeepSeek, Mistral, Ollama, OpenRouter, compat) |
| `naukari_pro/llm/routing.py` | YAML + env loader (`AI_GATEWAY_DEFAULT_PROVIDER`, per-task overrides) |
| `naukari_pro/llm/provider_router.py` | Task → provider chain with fallbacks |
| `naukari_pro/llm/gateway.py` | Wired router into live calls; status(); prompt→task map |
| `naukari_pro/llm/ledger.py` | Daily + monthly caps, `paused_budget` → `BudgetPaused`, SQLite dual-write |
| `naukari_pro/llm/ai_calls_db.py` | `ai_calls` SQLite cost ledger table |
| `naukari_pro/mcp/` | MCP stdio JSON-RPC + HTTP `:7432` bridge + 10 tools |
| `playbooks/AGENTS.md` | Runtime-agnostic run contract |
| `playbooks/GROKBOT.md` | Grok / xAI mapping |
| `playbooks/MUSE.md` | Muse / Mistral / compat mapping |
| `playbooks/ANTIGRAVITY.md` | Antigravity MCP + CLI checklist |
| `CLAUDE.md` | Pointer to NaukariPro playbooks |
| `naukari_pro/cli.py` | `mcp` command; richer `llm-status` |
| `tests/test_ai_gateway_m1.py` | Offline M1 coverage |

## Acceptance checks (M1)

- [x] Switching `AI_GATEWAY_DEFAULT_PROVIDER` changes routing without app-code edits
- [x] Cost ledger JSONL + SQLite `ai_calls`
- [x] `paused_budget` / caps degrade to deterministic-only (`BudgetPaused`)
- [x] MCP tools include search/score/tailor/draft/apply(dry_run)/approve/tracker/stats/sources
- [x] `apply_job` dry-run default; `dry_run=false` blocked without approval
- [x] Playbooks for AGENTS / GROKBOT / MUSE / ANTIGRAVITY
- [x] Offline tests (no live network LLM)

## How to run

```bash
naukariPro llm-status
naukariPro mcp --list-tools
naukariPro mcp --http --port 7432
python -m naukari_pro.mcp.server          # stdio
```

## Test results

```
tests/test_ai_gateway_m1.py + tests/test_llm_gateway_ws2.py → 23 passed
```

Full suite run logged separately after this milestone.

## Changelog

### November 5, 2026

- Delivered M1 AI Gateway, MCP scaffold, and multi-runtime playbooks.
