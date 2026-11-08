# NaukariPro Big Hammer Protocol — Report

**Honest definition of unbreakable (Hammer Oath):**

> No software is unbreakable. NaukariPro is "break-proof" when every hammer blow ends FIXED (regression proves it) or CONTAINED (fails closed — never lies, corrupts, submits garbage, leaks, or silently swallows).

**Date:** November 8, 2026  
**Suite:** `tests/hammer/` (catalog-backed 420 distinct blows)  
**Ledger:** `tests/hammer/hammer_log.jsonl`

## Phase 1 — Singles (420/420)

| Metric | Result |
|--------|--------|
| Blows delivered | **420/420** (ledger-verified unique blow_ids; **420 unique attack keys**, **84 kinds**) |
| Outcomes (latest H* rows) | contained **319** · survived **101** · broke_unfixed **0** |
| Hammers | input 50 · llm 45 · form 45 · state 40 · security 40 · network 35 · concurrency 30 · resource 30 · runtime 30 · time 25 · identity 25 · operator 25 |
| pytest | `tests/hammer` → **436 passed** (420 blows + combos + phase5 regressions) |
| Invariant checker | `scripts/check_invariants.py` → **OK — 0 violations** |

### Hardening landed with the deepen-in-place pass

| Module | Role |
|--------|------|
| [`naukari_pro/errors.py`](../../naukari_pro/errors.py) | Typed `NaukariProError` hierarchy |
| [`naukari_pro/hammer_safe.py`](../../naukari_pro/hammer_safe.py) | Parsers, SSRF (hex/octal/nip/Unicode digits), network sim, XXE/zip-slip, path gates |
| [`naukari_pro/governed_apply/approval.py`](../../naukari_pro/governed_apply/approval.py) | Atomic single-use `decide()` (`BEGIN IMMEDIATE`); confirmation proof required to record applied |
| [`naukari_pro/governed_apply/confirmation.py`](../../naukari_pro/governed_apply/confirmation.py) | Negation voids text **and** URL confirmation |
| [`naukari_pro/security/canary.py`](../../naukari_pro/security/canary.py) | Prompt-injection / exfil patterns |
| [`naukari_pro/security/pii.py`](../../naukari_pro/security/pii.py) | `AIza…` secret redaction |
| [`naukari_pro/resume_gen/claim_validator.py`](../../naukari_pro/resume_gen/claim_validator.py) | `NUMBER_RE` includes `ms`/unit suffixes |
| Catalog | [`tests/hammer/catalog.py`](catalog.py) — no `__mutNN` seed-rotation padding |

### Sample contained vectors

- H1: oversized string, null byte, YAML alias bomb, SSRF metadata/localhost/hex/nip/Unicode
- H2: fabricated cert/metric, ₹12→₹21 mutation, prompt-injection JD canary
- H3: kill-sim uncommitted invisible; corrupt DB reopen refuse
- H4: threaded token race → exactly one approval
- H7: reset/stall/429/gzip/redirect-loop typed refuse
- H8: React commit wipe, validity, DOM mismatch, captcha step → exit 2/3
- H10: path traversal, XXE, zip-slip, symlink ledger, forged HMAC
- H12: vendor captcha without key → ConfigError; `--submit` without token refused

## Phase 2 — Combos

[`tests/hammer/test_combos.py`](test_combos.py): LLM inject + network stall; kill + remount; disk-full + retry storm; expired token + race; SSRF + XXE; fabrication + budget. All fail-closed + invariants green.

## Phase 3 — Sustained chaos

```
python scripts/chaos_monkey.py --seed 42 --duration 6 --interval 1
→ {"faults": 6, "invariant_violations": 0, "ok": true, "pipeline": true}
```

PR CI: `--duration 30`. Nightly: [`hammer-nightly.yml`](../../.github/workflows/hammer-nightly.yml) `--duration 900 --interval 30`. Overnight `--duration 28800` is optional ops.

## Phase 4 — Mutation hammer

```
python scripts/mutation_hammer.py
→ 8/8 safety mutants KILLED
surviving_safety_mutants=0
kill_rate=100.00%
```

Modules covered: `hammer_safe` (SSRF, size, YAML, path, redirects), `fill_verify`, `approval` pending guard, `canary` injection gate.

## Phase 5 — Independent examiner

| Pass | Result |
|------|--------|
| First exam ([Phase-5 hammer examiner](a9d270ab-69dc-4198-a5dc-b3fc23f1d4cc)) | **5 criticals** → fixed + `test_p5b_*` regressions |
| Re-exam ([Phase-5 re-exam](a85d9851-1414-4c78-896d-d75eccdb7880)) | F1–F5 hold; **2 new** (F6/F7) → fixed + `test_p5c_*` |
| Residual new criticals after fix loop | **0** |

Findings: `PHASE5_EXAM_2026-11-08.md`, `PHASE5_REEXAM_2026-11-08.md`.

## Anti-laws checklist

1. No skipped vector in the 420 catalog — OK (distinct vectors/kinds)  
2. No test deleted to go green — OK  
3. No broad `except: pass` added — H11 lint blow asserts bare `except: pass` == 0  
4. Invariant checker not weakened — expanded to I1–I10 with fixture DB  
5. No `broke_unfixed` in final ledger — OK  

## What this certificate does *not* prove

Live-site DOM drift, real vendor captcha behavior, recruiter judgment — outside offline gauntlet (prompt honesty appendix).

## Changelog

### November 8, 2026

- Deepen-in-place: catalog of 420 distinct blows; real invariants; combos; chaos pipeline; 8 mutants; Phase-5 fix loop (F1–F7).
