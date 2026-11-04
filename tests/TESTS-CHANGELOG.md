# Scenario Suite Changelog

## November 5, 2026

- P0: Added `tests/scenarios/` tree, socket-block conftest, fixtures (≥200 India board jobs, ATS form HTML, golden vectors, profile pack), `scripts/gen_manifest.py` (NP-0001–1000), pytest markers.
- P1–P3: Landed families A–K as parametrized offline scenarios (1,000 collected).
- Family F: No `naukaripro_captcha_module/`; implemented against `naukari_pro/captcha` + `governed_apply.attention` / `captcha_safety` shim. Extended detector needles for turnstile/arkose/geetest/text challenges.
- Bug fixes required by failing scenarios: captcha detector ordering/needles, path traversal backslash normalization, exit-code/cost float casts in A4, D2 faithful evidence alignment.
- Added `naukari_pro/security/{pii,paths}.py`, `naukari_pro/governed_apply/exit_codes.py`.
- `scripts/test_report.py` regenerates `tests/TEST_REPORT.md`.
- Gate tooling: `tests/gates/` (coverage helpers, T7 acceptance, mutation proofs), `tests/scenarios/redteam/ledger.json` (50), `.coveragerc`, `scripts/check_coverage_gate.py`, `scripts/simple_mutation_score.py`, `scripts/run_gates.py`.
- Bug-fix: removed unreachable second `fnmatch` branch in `captcha.safety.domain_allowed` (dead after domain lstrip) to achieve 100% branch on captcha safety.

No scenario IDs deleted. Removals require justification in this file.
