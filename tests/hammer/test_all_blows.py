"""Big Hammer Protocol — all 420 blows parametrized."""

from __future__ import annotations

import pytest

from tests.hammer.attacks import ATTACKS
from tests.hammer.blow_registry import ALL_BLOWS
from tests.hammer.harness import check_basic_invariants, run_blow


@pytest.mark.hammer
@pytest.mark.parametrize(
    "blow",
    ALL_BLOWS,
    ids=[b["blow_id"] for b in ALL_BLOWS],
)
def test_hammer_blow(blow: dict) -> None:
    attack_name = blow["attack"]
    attack = ATTACKS.get(attack_name) or ATTACKS["noop"]
    # Hostile vectors expect typed refuse / fail-closed
    refuse_names = {
        "assert_safe_oversized",
        "assert_null_byte",
        "json_deep_nest",
        "yaml_alias_bomb",
        "ssrf_metadata",
        "ssrf_localhost",
        "salary_negative",
        "salary_huge",
        "salary_nan",
        "salary_bool",
        "json_bad_utf8",
        "json_truncated",
        "json_wrong_schema",
        "answer_flood",
        "form_field_cap",
        "hiring_decay_neg",
        "approval_expired",
        "approval_missing",
        "empty_body",
        "unknown_required",
        "resume_bind",
        "evidence_hash",
        "wrong_candidate",
        "path_traversal",
        "cmd_filename",
        "symlink_ledger",
        "typed_raise",
        "boot_vendor_no_key",
        "boot_vendor_no_allow",
        "yaml_invalid",
        "submit_no_approval",
        "llm_refusal_text",
        "prompt_injection_jd",
        "fabricated_cert",
        "fabricated_metric",
        "number_mutation",
        "identical_answers",
        "hallucinated_company",
        "puffery",
        "dedupe_idempotent",
        "concurrent_dedupe",
        "company_cooldown",
        "token_single_use",
        "circuit_trip",
        "react_remount",
        "error_banner",
        "validity_fail",
        "dom_mismatch",
        "secret_redact",
        "pii_redact",
        "hmac_forge",
        "csv_formula",
        "jsonl_partial_refuse",
    }
    expect = "contained" if attack_name in refuse_names else "survived"
    result = run_blow(
        blow_id=blow["blow_id"],
        hammer=blow["hammer"],
        vector=blow["vector"],
        target=blow["target"],
        attack=attack,
        expect=expect,
    )
    assert result.outcome != "broke_unfixed"
    # Refuse vectors must stay fail-closed — weak asserts let safety mutants survive.
    if expect == "contained":
        assert result.outcome == "contained", (
            f"{blow['blow_id']} expected contained refuse, got {result.outcome}: {result.observed}"
        )
    else:
        assert result.outcome in ("survived", "contained", "broke_fixed")
    violations = check_basic_invariants()
    assert not violations, violations
