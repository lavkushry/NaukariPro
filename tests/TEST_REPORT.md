# NaukariPro v2 — Scenario Suite Test Report

Generated: 2026-11-08 05:43 UTC
Manifest hash: `699ab10fd9138a04`
Collected tests: 1000

## Honest framing

1,000 passing tests alone do not prove the app "works surely." Confidence comes from the combination of behavior-asserting scenarios, coverage, mutation kill rate, red-team rejects, zero-flake determinism, and live canaries (Appendix C). This report never claims more than the evidence supports.

## 9 Gates of Done

| # | Gate | Threshold | Status | Evidence |
|---|---|---|---|---|
| 1 | Green | 1,000/1,000 pass, offline, one command | **PASS** | pytest `tests/scenarios` → collect 1000; manifest pass=1000 pending=0 |
| 2 | Coverage | ≥90% lines every module; 100% branch on verifier/approval/captcha/exit | **PENDING** | Run `coverage run -m pytest tests/scenarios` in CI; not asserted in this regeneration |
| 3 | Mutation | ≥70% overall; ≥90% verifier+captcha; 5 red-team mutable proofs | **PENDING** | mutmut + 5 intentional mutation proofs still to land in CI |
| 4 | Zero flakes | 3 consecutive seeded runs identical | **PENDING** | Re-run thrice with fixed seed; compare JUnit/manifest hash |
| 5 | Speed | ≤10 min on 4 cores; no test >2s | **PASS** | Full suite ~5s single-core in local run (well under 10 min) |
| 6 | Traceability | 1,000 unique IDs, zero orphans/dupes | **PASS** | issues=none; families={'A1': 27, 'A2': 24, 'A3': 15, 'A4': 12, 'A5': 12, 'B1': 40, 'B2': 40, 'B3': 30, 'B4': 20, 'B5': 10, 'C1': 20, 'C2': 20, 'C3': 20, 'C4': 15, 'C5': 15, 'C6': 20, 'D1': 20, 'D2': 20, 'D3': 20, 'D4': 25, 'D5': 15, 'D6': 30, 'D7': 20, 'E1': 100, 'E2': 24, 'E3': 20, 'E4': 12, 'E5': 10, 'E6': 10, 'E7': 14, 'F1': 24, 'F2': 20, 'F3': 16, 'G1': 15, 'G2': 20, 'G3': 15, 'G4': 10, 'H1': 15, 'H2': 20, 'H3': 15, 'H4': 10, 'I1': 20, 'I2': 10, 'I3': 15, 'I4': 15, 'J1': 8, 'J2': 8, 'J3': 8, 'J4': 8, 'J5': 8, 'K1': 20, 'K2': 10, 'K3': 10} |
| 7 | Red-team | 50/50 reject under socket-block | **PARTIAL** | Red-team markers present in D/E/F/I; dedicated 50-ledger audit TBD |
| 8 | Acceptance | 6 T7 acceptance criteria | **PARTIAL** | Provider config-swap marked acceptance on A1; fabricated-fact / dry-run covered in J/D/E |
| 9 | Honesty | Appendix C + known gaps | **PASS** | See below |

## Manifest audit

- Rows: 1000
- Status counts: {'pass': 1000}
- Issues: none

## Family counts

| Family | Count |
|---|---|
| A1 | 27 |
| A2 | 24 |
| A3 | 15 |
| A4 | 12 |
| A5 | 12 |
| B1 | 40 |
| B2 | 40 |
| B3 | 30 |
| B4 | 20 |
| B5 | 10 |
| C1 | 20 |
| C2 | 20 |
| C3 | 20 |
| C4 | 15 |
| C5 | 15 |
| C6 | 20 |
| D1 | 20 |
| D2 | 20 |
| D3 | 20 |
| D4 | 25 |
| D5 | 15 |
| D6 | 30 |
| D7 | 20 |
| E1 | 100 |
| E2 | 24 |
| E3 | 20 |
| E4 | 12 |
| E5 | 10 |
| E6 | 10 |
| E7 | 14 |
| F1 | 24 |
| F2 | 20 |
| F3 | 16 |
| G1 | 15 |
| G2 | 20 |
| G3 | 15 |
| G4 | 10 |
| H1 | 15 |
| H2 | 20 |
| H3 | 15 |
| H4 | 10 |
| I1 | 20 |
| I2 | 10 |
| I3 | 15 |
| I4 | 15 |
| J1 | 8 |
| J2 | 8 |
| J3 | 8 |
| J4 | 8 |
| J5 | 8 |
| K1 | 20 |
| K2 | 10 |
| K3 | 10 |

## Appendix C — What 1,000 tests cannot prove

1. **Live vendor/LLM drift** — fixtures age. Mitigation: weekly canary dry-run vs fixtures.
2. **Real captcha behavior** — detectors use captured HTML, not live challenges. Mitigation: human-default never depends on solver correctness.
3. **Recruiter judgment** — screen-pass rate is production-measured. Mitigation: tracker dashboards from Day 1.
4. **Site DOM changes** — form fixtures freeze a moment. Mitigation: 4-layer fill fails closed + fixture refresh chore.

## Known gaps

- Coverage (Gate 2) and mutmut (Gate 3) not yet wired as hard CI fail.
- Red-team 50-case ledger not separately enumerated beyond markers.
- `naukaripro_captcha_module` path from the original brief was absent; Family F uses `naukari_pro/captcha` + `governed_apply` surfaces.
- Live job-board URL is fixture inspiration only — never called from tests.

## Changelog

### November 5, 2026

- Initial report generator and first offline 1,000-scenario collection.
