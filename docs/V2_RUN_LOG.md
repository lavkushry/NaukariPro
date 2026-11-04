# NaukariPro v2.0 — Run Log

## M0 — Hygiene
- Secrets scrubbed to `.env` / `.env.example`; `.gitignore` hardened; GitHub Actions pytest CI.
- Report: prior session / `docs/M0_SECRETS_HYGIENE.md` if present.

## M1 — AI Gateway + MCP + Playbooks
- Files: `config/ai_gateway.yml`, `naukari_pro/llm/{providers,routing,provider_router,ai_calls_db}.py`, gateway/ledger upgrades, `naukari_pro/mcp/`, `playbooks/*`.
- CLI: `naukariPro llm-status`, `naukariPro mcp [--http|--list-tools]`.
- Tests: `test_ai_gateway_m1.py` + `test_llm_gateway_ws2.py` green.
- Report: `docs/M1_AI_GATEWAY_REPORT.md`.

## M2 — Aggregator extensions
- `config/boards.csv`, `boards_registry.py`, `india_geo.py`, NormalizedJob v2 fields, CDX host fixes, Ashby compensation/plain-text.
- CLI: `naukariPro boards-import`.
- Report: `docs/M2_AGGREGATOR_REPORT.md`.

## M3–M7
- Deterministic scorer, grounding validator, writing lint, 4-layer fill verify, company dedupe, screen-pass metric, Razorpay scaffold.
- Report: `docs/M3_M7_PROGRESS_REPORT.md`.

## Latest offline test slice

```
39 passed — M1/M2/M3–M7 focused suites (2026-11-05)
```

## Later additions (same session)
- OpenAPI REST: `naukari_pro/api/app.py` + `naukariPro api-serve` + HMAC webhooks
- Offline E2E chain in `tests/test_api_webhooks_m1.py`
- India form corpus starter: `naukari_pro/fixtures/india_forms/`

## Still open for full §9 acceptance
- Dual-runtime **live** MCP demo (Grok Bot + Antigravity sessions)
- P3/P5 contract 1.1.0 alignment
- Expanded India corpus + gold HF dataset
- Browser-extension bridge
- Full-repo pytest green (1825 tests; focused v2 slices green)
