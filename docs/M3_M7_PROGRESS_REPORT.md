# M3–M7 Progress Report

**Date:** November 5, 2026

## M3 — Search agent
- Added India-tuned `deterministic_score.py` (weighted keywords, niches, freshness split, consultancy penalty).
- Wired into MCP `score_job`.
- Existing Stage A–D matching pipeline + golden eval retained.

## M4 — Resume Studio (partial)
- Added `claim_validator.py` (support ≥0.25, novelty ≤0.34, puffery, unsourced numbers).
- Added `writing_lint.py` (PASS / REWRITE / DO NOT SEND).
- Fake-fact rejection covered by offline test.
- Full HTML→PDF/DOCX tailor contract (P3 1.1.0) still pending — resume_gen tailor/render remain truth-preserving WS4 baseline.

## M5 — Apply v2 (partial)
- Added 4-layer `fill_verify.py` + React commit-and-verify.
- Added `dedupe_rules.py` (employerJobId, 15-day cooldown, same-day freeze, lifetime max, interview-tracker skip → exit 2).
- Existing governed-apply dry-run + approval tokens retained.

## M6 — Tracker
- `screen_pass_rate()` with per-board / resume_version / answer_template segmentation.
- Dashboard `/api/screen-pass` + home pulse.
- Notification intent queue already present (`NotificationQueue`).

## M7 — Eval / India / Razorpay
- Razorpay ₹49/mo scaffold + single-use coupons + autofill/tailor meters.
- India geo aliases in M2 (`india_geo.py`).
- Gold dataset / India form corpus still to expand.

## Test slice (offline)

```
tests/test_ai_gateway_m1.py
tests/test_llm_gateway_ws2.py
tests/test_boards_registry_m2.py
tests/test_v2_grounding_apply_m345.py
tests/test_screen_pass_m6.py
tests/test_razorpay_scaffold_m7.py
```

## Changelog

### November 5, 2026 (later)

- P3/P5 bumped to **1.1.0** with `keyword_coverage` + auditable cover-letter claims.
- OpenAPI REST + HMAC webhooks (`naukariPro api-serve`).
- India form corpus starter fixtures.
- Offline focused suites green (API, grounding, boards, P3/P5, screen-pass).

### November 5, 2026

- Landed M3–M7 scaffolds and core gates.
