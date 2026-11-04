# Phase 5 Independent Hammer Exam — Findings

**Examiner:** Independent red-team subagent ([Phase-5 hammer examiner](abdfc2f3-f2f8-4114-b84d-85b54017c0eb))  
**Date:** November 5, 2026  
**Critical count:** 5 (all returned to Phase-1 fix loop)

| ID | Vector | Module |
|----|--------|--------|
| F1 | Empty `expected` bypasses DOM verify | `fill_verify.py` |
| F2 | Substring number match (`1` in `10`) | `claim_validator.py` |
| F3 | SSRF misses 127.0.0.0/8 variants | `hammer_safe.py` |
| F4 | Captcha passthrough on empty token HTML | `captcha/resolver.py` |
| F5 | API open when `NAUKARI_API_KEY` unset | `api/app.py` |

See parent agent fix commits / this session patches + `tests/hammer/test_phase5_regressions.py`.
