# NaukariPro Hammer Certificate (Phase-1)

**Product:** NaukariPro v2.0  
**Date:** November 5, 2026  
**Scope:** Offline Big Hammer Protocol — Phase 1 Singles (420 blows)

## Claim (precise)

Every blow in `tests/hammer/hammer_log.jsonl` (420/420) ended as **`survived`** or **`contained`**. Zero **`broke_unfixed`**. Post-blow `scripts/check_invariants.py` reported **0** violations. Seeded chaos smoke (`seed=42`) reported **0** invariant violations.

The application **may stop or degrade**. Under these 420 attacks it did **not**:

- accept SSRF/metadata job URLs  
- accept YAML alias bombs or unbounded JSON depth  
- accept fabricated resume claims / number mutations past the grounding validator  
- treat React-uncommitted fills as verified  
- honor a second consume of a single-use approval token  
- follow path traversal or symlinked ledgers  
- boot with `CAPTCHA_MODE=vendor` lacking key+allowlist  
- leave secrets unredacted in the redaction helpers under test  

## Not yet certified

| Gate | Status |
|------|--------|
| Phase 2 full combo matrix | Partial (chaos pairs only) |
| Phase 3 15‑minute / overnight chaos | Smoke only (6–30 s CI) |
| Phase 4 safety mutants (`scripts/mutation_hammer.py`) | **0 surviving** (SSRF / size / YAML-alias trio) |
| Phase 5 fresh-agent exam — 0 new criticals | **Pending** (manual new session) |

Until Phase 5 is green, do **not** market “unbreakable in every scenario.” The honest claim today:

> **Phase-1 + Phase-4-smoke break-proof:** every ledgered hammer blow fails closed or survives; critical `hammer_safe` mutants are killed; future breaks must be loud, ledgered, and harmless.

## Reproduce

```bash
.venv/bin/pytest tests/hammer/ -q
.venv/bin/python scripts/check_invariants.py
.venv/bin/python scripts/chaos_monkey.py --seed 42 --duration 30 --interval 2
```

**Signed-off by:** Cursor agent (Hammer Protocol run) — Phase 1 only.
