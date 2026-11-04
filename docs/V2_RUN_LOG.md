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

## M5 captcha (§4.9) + §9 surface (2026-11-05)
- Package: `naukari_pro/captcha/` (detector, resolver chain, vendor/vlm, events, circuit).
- Schemas: `profile` / `match_decisions` / `resumes` via `schema/v2_tables.py`.
- CLIs: `ats-score`, `e2e-demo` (dry-run default; exit 0), `browser-bridge` (:7433).
- Canary defense + Anthropic Messages adapter; India adapter stubs; dual MCP offline harness (grok_bot + antigravity).
- Report: `docs/M5_CAPTCHA_REPORT.md`.

### Focused §9 evidence slice (green)

```
207 passed — captcha + dual MCP/bridge + screen-pass + API + gateway + India + grounding + boards + razorpay + dedupe + verifier scenarios
23 passed — grounding fake-fact / puffery / 4-layer fill / company cooldown exit 2 / captcha triple-gate / screen-pass
e2e-demo CLI → status=dry_run_ok, fill_layers=4/4, grounding_ok=true, exit 0
```

### Full-repo pytest (2026-11-05)

```
1549 passed, 67 failed, 29 errors, 4 warnings in 2877.77s (~48m)
```

Failures concentrate in pre-existing challenger / LinkedIn / intent-agent / Excel-tracker / offline screening suites — **not** the v2 §9 captcha/MCP/grounding/dedupe/screen-pass slice. Full-suite green remains open for §9 criterion #1.

## Full-suite remediation (in progress, 2026-11-05)

Fixed since the 1549/67/29 run:
- Stale LinkedIn/GitHub slug asserts → `lavkush-kumar` (`test_challenger_m3_adversarial`).
- Playwright Chromium installed for offline screening tests.
- Gate tests: `universal_apply=False` + DB isolation (`test_challenger_m3_gate_adversarial`, `test_f10`).
- Intent/portal crash: None-safe `.lower()` on title/jd/location/ats (`career_portals.py`).

## Big Hammer Protocol (2026-11-05)

- Scaffold: `naukari_pro/errors.py`, `naukari_pro/hammer_safe.py`, `tests/hammer/` (420 blows).
- `pytest tests/hammer/ -q` → **420 passed**; ledger 319 contained / 101 survived / 0 broke_unfixed.
- `scripts/check_invariants.py` → OK; chaos smoke seed=42 → 0 violations.
- Reports: `tests/hammer/HAMMER_REPORT.md`, `HAMMER_CERT.md`.
- Phase-4 smoke: `scripts/mutation_hammer.py` → **0 surviving** safety mutants (SSRF/size/YAML).

## Still open
- Hammer Phase 5 (fresh-agent independent exam — requires new session).
- Remaining full-repo failures (Excel tracker schema, LinkedIn harvesting mocks, session flock).
- Live dual MCP sessions; Next.js UI; git history scrub (needs explicit approval).
