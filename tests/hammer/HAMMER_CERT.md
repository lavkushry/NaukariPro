# NaukariPro Hammer Certificate

**Product:** NaukariPro v2.0  
**Date:** November 8, 2026  
**Scope:** Offline Big Hammer Protocol — Phases 1–5 (deepen-in-place)

## Claim (precise)

| Metric | Target | Evidence |
|--------|--------|----------|
| Blows delivered | 420/420 | `catalog.py` + `hammer_log.jsonl` unique H* IDs |
| Breaks found & fixed | regressions `NP-H*` / `test_p5*` | approval race, SSRF variants, confirmation, grounding, PII |
| Contained behaviors | per-blow `expect` | 319 contained / 101 survived (latest H* ledger) |
| Surviving mutants (safety) | **0** | `scripts/mutation_hammer.py` 8/8 KILLED |
| Invariant violations (chaos) | **0** | `check_invariants.py` + chaos seed 42 |
| Phase-5 new criticals (post fix-loop) | **0** | F1–F7 fixed; regressions green |
| `except: pass` in codebase | **0** | H11 lint blow |

Every blow in the catalog ends as **`survived`** or **`contained`**. Zero **`broke_unfixed`**.

The application **may stop or degrade**. Under these attacks it did **not**:

- accept SSRF/metadata/hex/octal/nip/Unicode-digit job URLs  
- accept YAML alias bombs or unbounded JSON depth  
- accept fabricated resume claims / unit-suffixed number mutations  
- treat React-uncommitted fills or negated “confirmation” pages as verified submits  
- honor a second consume of a single-use approval token under thread races  
- record `applied` without confirmation proof  
- follow path traversal, XXE, zip-slip, or symlinked ledgers  
- boot with `CAPTCHA_MODE=vendor` lacking key+allowlist  
- leave `AIza…` / sk- secrets unredacted in redaction helpers under test  

## Honest limits

| Gate | Status |
|------|--------|
| Phase 1 distinct catalog | **Complete** (420 unique attack keys) |
| Phase 2 combo matrix | **Complete** (`test_combos.py`) |
| Phase 3 15-minute chaos | **Wired nightly**; PR uses 30s smoke |
| Phase 4 safety mutants | **0 surviving** (DIY 8 needles; full mutmut corpus optional expansion) |
| Phase 5 fresh-agent exam | Fix loop closed; residual new criticals **0** |

> Every documented hammer blow fails closed or survives; Phase-5 criticals were fixed with regressions; safety mutants are killed; the certificate does **not** claim live-site or recruiter judgment immunity.

## Reproduce

```bash
.venv/bin/pytest tests/hammer -q
.venv/bin/python scripts/check_invariants.py
.venv/bin/python scripts/chaos_monkey.py --seed 42 --duration 30 --interval 2
.venv/bin/python scripts/mutation_hammer.py
```

**Signed-off by:** Cursor agent (Big Hammer deepen-in-place) — November 8, 2026.
