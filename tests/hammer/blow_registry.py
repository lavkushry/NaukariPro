"""
Blow registry for Big Hammer Protocol — 420 blows across H1–H12.

Each entry: (blow_id, hammer, vector, target, attack_factory_name)
Attack implementations live in tests/hammer/attacks.py
"""

from __future__ import annotations

from typing import Dict, List, Tuple

# Counts per master prompt
HAMMER_COUNTS = {
    "H1": 50,  # input
    "H2": 45,  # llm
    "H3": 40,  # state
    "H4": 30,  # concurrency
    "H5": 30,  # resource
    "H6": 25,  # time
    "H7": 35,  # network
    "H8": 45,  # form
    "H9": 25,  # identity
    "H10": 40,  # security
    "H11": 30,  # runtime-chaos
    "H12": 25,  # operator
}

HAMMER_NAMES = {
    "H1": "input",
    "H2": "llm",
    "H3": "state",
    "H4": "concurrency",
    "H5": "resource",
    "H6": "time",
    "H7": "network",
    "H8": "form",
    "H9": "identity",
    "H10": "security",
    "H11": "runtime",
    "H12": "operator",
}

# Named seed vectors (first N per hammer); remaining are mutations of the seeds.
SEED_VECTORS: Dict[str, List[Tuple[str, str, str]]] = {
    "H1": [
        ("unicode_zalgo_name", "naukari_pro.hammer_safe.assert_safe_string", "assert_safe_string"),
        ("emoji_rtl_override", "naukari_pro.hammer_safe.assert_safe_string", "assert_safe_string"),
        ("10mb_string", "naukari_pro.hammer_safe.assert_safe_string", "assert_safe_oversized"),
        ("null_byte_field", "naukari_pro.hammer_safe.assert_safe_string", "assert_null_byte"),
        ("json_depth_1000", "naukari_pro.hammer_safe.parse_json_safe", "json_deep_nest"),
        ("yaml_alias_bomb", "naukari_pro.hammer_safe.parse_yaml_safe", "yaml_alias_bomb"),
        ("csv_formula_injection", "naukari_pro.hammer_safe.sanitize_csv_cell", "csv_formula"),
        ("ssrf_metadata_url", "naukari_pro.hammer_safe.validate_job_url", "ssrf_metadata"),
        ("ssrf_localhost", "naukari_pro.hammer_safe.validate_job_url", "ssrf_localhost"),
        ("xss_in_title", "naukari_pro.hammer_safe.assert_safe_string", "xss_script"),
        ("negative_salary", "naukari_pro.hammer_safe.validate_salary", "salary_negative"),
        ("huge_salary", "naukari_pro.hammer_safe.validate_salary", "salary_huge"),
        ("nan_salary", "naukari_pro.hammer_safe.validate_salary", "salary_nan"),
        ("bool_salary", "naukari_pro.hammer_safe.validate_salary", "salary_bool"),
        ("empty_present_json", "naukari_pro.hammer_safe.parse_json_safe", "json_empty_object"),
        ("utf16_as_utf8", "naukari_pro.hammer_safe.parse_json_safe", "json_bad_utf8"),
        ("malformed_json", "naukari_pro.hammer_safe.parse_json_safe", "json_truncated"),
        ("cli_null_arg", "naukari_pro.hammer_safe.assert_safe_string", "assert_null_byte"),
        ("board_json_array_bomb", "naukari_pro.hammer_safe.parse_json_safe", "json_deep_nest"),
        ("mixed_rtl_ltr", "naukari_pro.hammer_safe.assert_safe_string", "assert_safe_string"),
    ],
    "H2": [
        ("malformed_llm_json", "naukari_pro.hammer_safe.parse_json_safe", "json_truncated"),
        ("refusal_text", "naukari_pro.resume_gen.claim_validator", "llm_refusal_text"),
        ("wrong_schema_json", "naukari_pro.hammer_safe.parse_json_safe", "json_wrong_schema"),
        ("prompt_injection_jd", "naukari_pro.security.canary", "prompt_injection_jd"),
        ("fabricated_cert", "naukari_pro.resume_gen.claim_validator", "fabricated_cert"),
        ("fabricated_metric", "naukari_pro.resume_gen.claim_validator", "fabricated_metric"),
        ("number_mutation_12_to_21", "naukari_pro.resume_gen.claim_validator", "number_mutation"),
        ("answer_flood_10k", "naukari_pro.hammer_safe.clamp_answer", "answer_flood"),
        ("empty_llm_answer", "naukari_pro.hammer_safe.clamp_answer", "answer_empty"),
        ("identical_loop_answers", "naukari_pro.resume_gen.claim_validator", "identical_answers"),
        ("hallucinated_company", "naukari_pro.resume_gen.claim_validator", "hallucinated_company"),
        ("puffery_injection", "naukari_pro.resume_gen.claim_validator", "puffery"),
    ],
    "H3": [
        ("wal_integrity_after_write", "sqlite3", "sqlite_integrity"),
        ("idempotent_apply_key", "naukari_pro.governed_apply.dedupe_rules", "dedupe_idempotent"),
        ("interrupted_ledger_row", "naukari_pro.governed_apply.dedupe_rules", "interrupted_mark"),
        ("approval_token_after_kill", "naukari_pro.governed_apply.approvals", "approval_missing"),
        ("jsonl_partial_line", "tests.hammer.attacks", "jsonl_partial_refuse"),
    ],
    "H4": [
        ("double_approval_token", "naukari_pro.governed_apply.approvals", "token_single_use"),
        ("two_agents_same_job", "naukari_pro.governed_apply.dedupe_rules", "concurrent_dedupe"),
        ("same_second_token_race", "naukari_pro.governed_apply.approvals", "token_single_use"),
        ("sqlite_busy_retry", "sqlite3", "sqlite_busy"),
    ],
    "H5": [
        ("answer_over_cap", "naukari_pro.hammer_safe.clamp_answer", "answer_flood"),
        ("oversized_string", "naukari_pro.hammer_safe.assert_safe_string", "assert_safe_oversized"),
        ("budget_to_zero", "naukari_pro.llm", "budget_degrade"),
        ("form_field_count_cap", "naukari_pro.hammer_safe", "form_field_cap"),
    ],
    "H6": [
        ("cooldown_decay_0", "naukari_pro.matching", "hiring_decay_0"),
        ("cooldown_decay_45", "naukari_pro.matching", "hiring_decay_45"),
        ("cooldown_decay_90", "naukari_pro.matching", "hiring_decay_90"),
        ("ist_schedule_pin", "naukari_pro.hammer_safe", "ist_pin"),
        ("expired_approval", "naukari_pro.governed_apply.approvals", "approval_expired"),
        ("negative_age", "naukari_pro.matching", "hiring_decay_neg"),
    ],
    "H7": [
        ("retry_after_cap", "naukari_pro.hammer_safe", "retry_cap"),
        ("empty_200_body", "naukari_pro.hammer_safe", "empty_body"),
        ("circuit_after_storm", "naukari_pro.captcha.circuit", "circuit_trip"),
        ("timeout_not_hang", "naukari_pro.hammer_safe", "timeout_bound"),
    ],
    "H8": [
        ("react_commit_mismatch", "naukari_pro.governed_apply.fill_verify", "react_remount"),
        ("error_banner_blocks", "naukari_pro.governed_apply.fill_verify", "error_banner"),
        ("validity_false", "naukari_pro.governed_apply.fill_verify", "validity_fail"),
        ("dom_readback_mismatch", "naukari_pro.governed_apply.fill_verify", "dom_mismatch"),
        ("new_required_mid_fill", "naukari_pro.governed_apply.fill_verify", "unknown_required"),
    ],
    "H9": [
        ("company_cooldown_cross_board", "naukari_pro.governed_apply.dedupe_rules", "company_cooldown"),
        ("resume_jd_mismatch", "naukari_pro.resume_gen", "resume_bind"),
        ("evidence_hash_mismatch", "naukari_pro.hammer_safe", "evidence_hash"),
        ("wrong_candidate_field", "naukari_pro.hammer_safe", "wrong_candidate"),
    ],
    "H10": [
        ("path_traversal", "naukari_pro.hammer_safe.safe_evidence_path", "path_traversal"),
        ("cmd_injection_filename", "naukari_pro.hammer_safe.safe_evidence_path", "cmd_filename"),
        ("symlink_ledger", "naukari_pro.hammer_safe.safe_evidence_path", "symlink_ledger"),
        ("secret_redaction", "naukari_pro.hammer_safe.redact_secrets", "secret_redact"),
        ("pii_redaction", "naukari_pro.hammer_safe.redact_pii", "pii_redact"),
        ("hmac_forge_reject", "naukari_pro.api", "hmac_forge"),
    ],
    "H11": [
        ("no_except_pass", "lint", "except_pass_lint"),
        ("chaos_raises_logged", "naukari_pro.errors", "typed_raise"),
        ("missing_env_boot", "naukari_pro.hammer_safe.validate_boot_config", "boot_vendor_no_key"),
        ("invalid_yaml_config", "naukari_pro.hammer_safe.parse_yaml_safe", "yaml_invalid"),
    ],
    "H12": [
        ("submit_without_approval", "cli", "submit_no_approval"),
        ("captcha_vendor_no_key", "naukari_pro.hammer_safe.validate_boot_config", "boot_vendor_no_key"),
        ("captcha_vendor_empty_allowlist", "naukari_pro.hammer_safe.validate_boot_config", "boot_vendor_no_allow"),
        ("contradictory_flags", "cli", "submit_no_approval"),
        ("empty_first_run", "naukari_pro.schema.v2_tables", "empty_schema"),
    ],
}


def _mutate_label(seed: str, i: int) -> str:
    return f"{seed}__mut{i:02d}"


def build_all_blows() -> List[Dict[str, str]]:
    blows: List[Dict[str, str]] = []
    for hid, count in HAMMER_COUNTS.items():
        seeds = SEED_VECTORS.get(hid, [("generic", "naukari_pro", "noop")])
        for n in range(1, count + 1):
            seed = seeds[(n - 1) % len(seeds)]
            vector, target, attack = seed
            if n > len(seeds):
                mut_i = (n - 1) // len(seeds)
                vector = _mutate_label(vector, mut_i)
            blows.append(
                {
                    "blow_id": f"{hid}-{n:02d}",
                    "hammer": HAMMER_NAMES[hid],
                    "vector": vector,
                    "target": target,
                    "attack": attack,
                }
            )
    assert len(blows) == 420, len(blows)
    return blows


ALL_BLOWS = build_all_blows()
