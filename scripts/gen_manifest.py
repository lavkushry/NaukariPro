#!/usr/bin/env python3
"""Pre-allocate NP-0001…NP-1000 into tests/scenarios/manifest.jsonl."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "scenarios" / "manifest.jsonl"

# (family, module, count, tier, risk, trace, file)
FAMILIES = [
    ("A1", "gateway", 27, "unit", "high", "MP §4.1", "tests/scenarios/gateway/test_a1_provider_conformance.py"),
    ("A2", "gateway", 24, "unit", "high", "MP §4.1", "tests/scenarios/gateway/test_a2_task_routing.py"),
    ("A3", "gateway", 15, "integration", "high", "MP §4.1", "tests/scenarios/gateway/test_a3_budget_ledger.py"),
    ("A4", "gateway", 12, "contract", "normal", "MP §4.1", "tests/scenarios/gateway/test_a4_retry_timeout.py"),
    ("A5", "gateway", 12, "contract", "high", "MP §4.1", "tests/scenarios/gateway/test_a5_malformed_response.py"),
    ("B1", "aggregator", 40, "unit", "high", "MP §4.2", "tests/scenarios/aggregator/test_b1_url_normalization.py"),
    ("B2", "aggregator", 40, "unit", "high", "MP §4.2", "tests/scenarios/aggregator/test_b2_dedupe_identity.py"),
    ("B3", "aggregator", 30, "contract", "normal", "MP §4.2", "tests/scenarios/aggregator/test_b3_board_adapters.py"),
    ("B4", "aggregator", 20, "property", "normal", "MP §4.2", "tests/scenarios/aggregator/test_b4_schema_fuzz.py"),
    ("B5", "aggregator", 10, "integration", "normal", "MP §4.2", "tests/scenarios/aggregator/test_b5_registry_cdx.py"),
    ("C1", "search", 20, "unit", "high", "MP §4.3", "tests/scenarios/search/test_c1_title_gate.py"),
    ("C2", "search", 20, "unit", "critical", "MP §4.3", "tests/scenarios/search/test_c2_location_gate.py"),
    ("C3", "search", 20, "unit", "high", "MP §4.3", "tests/scenarios/search/test_c3_comp_gate.py"),
    ("C4", "search", 15, "contract", "normal", "MP §4.3", "tests/scenarios/search/test_c4_batch_scoring.py"),
    ("C5", "search", 15, "unit", "high", "MP §4.3", "tests/scenarios/search/test_c5_hiring_signal_decay.py"),
    ("C6", "search", 20, "contract", "high", "MP §4.3", "tests/scenarios/search/test_c6_skip_vs_needs_human.py"),
    ("D1", "verifier", 20, "unit", "critical", "MP §4.5", "tests/scenarios/verifier/test_d1_sentence_support.py"),
    ("D2", "verifier", 20, "unit", "critical", "MP §4.5", "tests/scenarios/verifier/test_d2_novelty_cap.py"),
    ("D3", "verifier", 20, "redteam", "critical", "MP §4.5", "tests/scenarios/verifier/test_d3_puffery.py"),
    ("D4", "verifier", 25, "unit", "critical", "MP §4.5", "tests/scenarios/verifier/test_d4_verbatim_numbers.py"),
    ("D5", "verifier", 15, "contract", "high", "MP §4.5", "tests/scenarios/verifier/test_d5_answer_contract.py"),
    ("D6", "verifier", 30, "unit", "high", "MP §4.5", "tests/scenarios/verifier/test_d6_writing_lint.py"),
    ("D7", "verifier", 20, "unit", "high", "MP §4.4", "tests/scenarios/verifier/test_d7_tailoring_determinism.py"),
    ("E1", "apply", 100, "integration", "critical", "MP §4.6", "tests/scenarios/apply/test_e1_form_fill_matrix.py"),
    ("E2", "apply", 24, "unit", "critical", "MP §4.6", "tests/scenarios/apply/test_e2_four_layer_verify.py"),
    ("E3", "apply", 20, "contract", "critical", "MP §4.6", "tests/scenarios/apply/test_e3_exit_codes.py"),
    ("E4", "apply", 12, "unit", "high", "MP §4.6", "tests/scenarios/apply/test_e4_react_commit.py"),
    ("E5", "apply", 10, "redteam", "critical", "MP §4.6", "tests/scenarios/apply/test_e5_approval_tokens.py"),
    ("E6", "apply", 10, "integration", "high", "MP §4.6", "tests/scenarios/apply/test_e6_dedupe_cooldown.py"),
    ("E7", "apply", 14, "redteam", "critical", "MP §4.6", "tests/scenarios/apply/test_e7_injection_canary.py"),
    ("F1", "captcha", 24, "unit", "critical", "MP §4.9", "tests/scenarios/captcha/test_f1_detector.py"),
    ("F2", "captcha", 20, "redteam", "critical", "MP §4.9", "tests/scenarios/captcha/test_f2_mode_matrix.py"),
    ("F3", "captcha", 16, "integration", "critical", "MP §4.9", "tests/scenarios/captcha/test_f3_ledger_breaker.py"),
    ("G1", "tracker", 15, "unit", "high", "MP §4.7", "tests/scenarios/tracker/test_g1_screen_pass.py"),
    ("G2", "tracker", 20, "contract", "critical", "MP §4.7", "tests/scenarios/tracker/test_g2_status_machine.py"),
    ("G3", "tracker", 15, "unit", "normal", "MP §4.7", "tests/scenarios/tracker/test_g3_aggregation.py"),
    ("G4", "tracker", 10, "integration", "normal", "MP §4.7", "tests/scenarios/tracker/test_g4_notifications.py"),
    ("H1", "india", 15, "unit", "high", "MP §4.8", "tests/scenarios/india/test_h1_kolkata_tz.py"),
    ("H2", "india", 20, "unit", "high", "MP §4.8", "tests/scenarios/india/test_h2_geo_aliases.py"),
    ("H3", "india", 15, "unit", "normal", "MP §4.8", "tests/scenarios/india/test_h3_notice_ctc.py"),
    ("H4", "india", 10, "unit", "normal", "MP §4.8", "tests/scenarios/india/test_h4_consultancy.py"),
    ("I1", "security", 20, "redteam", "critical", "MP §6", "tests/scenarios/security/test_i1_pii_redaction.py"),
    ("I2", "security", 10, "unit", "critical", "MP §6", "tests/scenarios/security/test_i2_secrets_hygiene.py"),
    ("I3", "security", 15, "redteam", "critical", "MP §6", "tests/scenarios/security/test_i3_hmac_webhooks.py"),
    ("I4", "security", 15, "redteam", "critical", "MP §6", "tests/scenarios/security/test_i4_path_traversal.py"),
    ("J1", "e2e", 8, "e2e_mock", "high", "MP §9", "tests/scenarios/e2e/test_j1_search_score.py"),
    ("J2", "e2e", 8, "e2e_mock", "critical", "MP §9", "tests/scenarios/e2e/test_j2_tailor_vet.py"),
    ("J3", "e2e", 8, "e2e_mock", "critical", "MP §9", "tests/scenarios/e2e/test_j3_fill_dryrun.py"),
    ("J4", "e2e", 8, "e2e_mock", "critical", "MP §9", "tests/scenarios/e2e/test_j4_approval_submit.py"),
    ("J5", "e2e", 8, "e2e_mock", "critical", "MP §9", "tests/scenarios/e2e/test_j5_blocked_captcha.py"),
    ("K1", "chaos", 20, "property", "normal", "MP §5", "tests/scenarios/chaos/test_k1_hypothesis.py"),
    ("K2", "chaos", 10, "chaos", "high", "MP §5", "tests/scenarios/chaos/test_k2_wal_resume.py"),
    ("K3", "chaos", 10, "chaos", "high", "MP §5", "tests/scenarios/chaos/test_k3_determinism.py"),
]


def main() -> None:
    rows = []
    n = 1
    for family, module, count, tier, risk, trace, file in FAMILIES:
        for _ in range(count):
            rows.append(
                {
                    "id": f"NP-{n:04d}",
                    "module": module,
                    "family": family,
                    "tier": tier,
                    "risk": risk,
                    "trace": trace,
                    "file": file,
                    "status": "pending",
                }
            )
            n += 1
    assert len(rows) == 1000, f"expected 1000, got {len(rows)}"
    assert n == 1001
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(rows)} rows → {OUT}")


if __name__ == "__main__":
    main()
