# NaukariPro Big Hammer Protocol — Report

**Honest definition of unbreakable (Hammer Oath):**

> No software is unbreakable. NaukariPro is "break-proof" when every hammer blow ends FIXED (regression proves it) or CONTAINED (fails closed — never lies, corrupts, submits garbage, leaks, or silently swallows).

**Date:** November 5, 2026  
**Suite:** `tests/hammer/test_all_blows.py`  
**Ledger:** `tests/hammer/hammer_log.jsonl`

## Phase 1 — Singles (420/420)

| Metric | Result |
|--------|--------|
| Blows delivered | **420/420** (ledger-verified, unique blow_ids) |
| Outcomes | contained **319** · survived **101** · broke_unfixed **0** |
| Hammers | input 50 · llm 45 · form 45 · state 40 · security 40 · network 35 · concurrency 30 · resource 30 · runtime 30 · time 25 · identity 25 · operator 25 |
| pytest | `420 passed in ~11s` |
| Invariant checker | `scripts/check_invariants.py` → **OK — 0 violations** |

### Hardening landed with the arsenal

| Module | Role |
|--------|------|
| [`naukari_pro/errors.py`](../../naukari_pro/errors.py) | Typed `NaukariProError` hierarchy (parse/validation/approval/captcha/config) |
| [`naukari_pro/hammer_safe.py`](../../naukari_pro/hammer_safe.py) | Fail-closed parsers: string bounds, JSON depth, YAML alias cap, SSRF URL deny, salary gates, path traversal/symlink refuse, secret/PII redaction, boot config |
| Existing | Grounding validator, 4-layer fill verify, company dedupe exit 2, canary scan, captcha circuit, webhook HMAC, ApprovalQueue single-use `decide()` |

### Sample contained vectors

- H1: 10 MB string, null byte, YAML alias bomb, SSRF metadata/localhost, CSV formula neutralize
- H2: fabricated cert/metric, ₹12→₹21 mutation, prompt-injection JD canary, puffery
- H8: React commit wipe, validity false, DOM mismatch, error banners → exit-2 style refuse
- H10: path traversal, `; rm` filename, symlink ledger, forged HMAC → 401 semantics
- H12: `CAPTCHA_MODE=vendor` without key/allowlist → ConfigError exit 4; `--submit` without token refused

## Phase 2 — Combos

Scaffolded via chaos monkey selecting mixed fault+blow pairs. Full interactive combo matrix (LLM injection during network stall, etc.) remains an expansion track; short seeded run is green.

## Phase 3 — Sustained chaos

```
python scripts/chaos_monkey.py --seed 42 --duration 6 --interval 1
→ {"faults": 6, "invariant_violations": 0, "ok": true}
```

CI default should use `--duration 30`. Overnight `--duration 28800` is optional ops.

## Phase 4 — Mutation hammer

```
python scripts/mutation_hammer.py
→ ssrf_denylist_gutted: KILLED
→ size_cap_disabled: KILLED
→ yaml_alias_cap_disabled: KILLED
surviving_safety_mutants=0
```

DIY safety mutants on `hammer_safe.py` (SSRF gate, size cap, YAML alias cap). Full `mutmut` corpus across all safety modules remains optional expansion; **0 survivors** on the Phase-4 critical trio.

## Phase 5 — Independent examiner

**Status:** not run (requires fresh agent session). Certificate below does **not** claim Phase-5 zero-criticals.

## Anti-laws checklist

1. No skipped vector in the 420 ledger — OK  
2. No test deleted to go green — OK (`tests/TESTS-CHANGELOG.md`)  
3. No broad `except: pass` added — H11 lint blow asserts bare `except: pass` == 0  
4. Invariant checker not weakened — OK  
5. No `broke_unfixed` in final ledger — OK  

## What this certificate does *not* prove

Live-site DOM drift, real vendor captcha behavior, recruiter judgment — outside offline gauntlet (Master Prompt honesty appendix).
