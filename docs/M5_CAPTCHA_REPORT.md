# M5 — Captcha Resolution Pipeline (§4.9)

**Date:** November 5, 2026  
**Status:** Package landed; human-default; vendor triple-gated

## Package

| File | Role |
|------|------|
| `naukari_pro/captcha/detector.py` | Tier 2 classify |
| `naukari_pro/captcha/resolver.py` | Chain: passthrough → vendor → vlm → human |
| `naukari_pro/captcha/vendor.py` | Opt-in stub; never built in human mode |
| `naukari_pro/captcha/vlm.py` | Text/math deterministic parser |
| `naukari_pro/captcha/events.py` | `captcha_events` + `captcha_ledger` + JSONL |
| `naukari_pro/captcha/circuit.py` | ≥5 unresolved/24h → open |
| `naukari_pro/captcha/safety.py` | Policy manager (shimmed via `governed_apply/captcha_safety.py`) |

## Acceptance #7 proofs (offline)

- `CAPTCHA_MODE=human` → `build_vendor_client` returns `None`
- Vendor denied without allowlist / key / under-cap (three asserts in `tests/test_captcha_pipeline_m5.py`)
- Circuit breaker trips after 5 unresolved → exit 3

## Changelog

### November 5, 2026

- Formalized §4.9 captcha package; preserved Family F scenario compatibility.
