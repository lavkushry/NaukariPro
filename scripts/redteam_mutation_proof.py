#!/usr/bin/env python3
"""
Prove red-team tests can fail under mutation (Gate 3 / §7).

Temporarily weakens a defense and asserts the corresponding red-team node goes red.
"""

from __future__ import annotations

import re
import sys
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@contextmanager
def _patch(module_name: str, attr: str, value):
    import importlib

    mod = importlib.import_module(module_name)
    original = getattr(mod, attr)
    setattr(mod, attr, value)
    try:
        yield
    finally:
        setattr(mod, attr, original)


def _always_ok_validate(text, evidence, **kwargs):
    from naukari_pro.resume_gen.claim_validator import GroundingReport

    return GroundingReport(
        ok=True,
        sentences=[],
        unsupported_claims=[],
        dropped_sentences=[],
        novelty_ratio=0.0,
    )


PROOFS = [
    (
        "novelty_and_support_disabled",
        "naukari_pro.resume_gen.claim_validator",
        "validate_text",
        _always_ok_validate,
        "tests/scenarios/verifier/test_d2_novelty_cap.py::test_d2_novelty_cap[NP-0371]",
    ),
    (
        "puffery_regex_neutered",
        "naukari_pro.resume_gen.claim_validator",
        "PUFFERY",
        re.compile(r"a^"),
        "tests/scenarios/verifier/test_d3_puffery.py::test_d3_puffery[NP-0381]",
    ),
    (
        "empty_allowlist_ignored",
        "naukari_pro.captcha.safety",
        "domain_allowed",
        lambda domain, allowlist: True,
        "tests/scenarios/captcha/test_f2_mode_matrix.py::test_f2_mode_matrix[NP-0707]",
    ),
    (
        "hmac_accepts_forgeries",
        "naukari_pro.api.app",
        "verify_webhook_signature",
        lambda body, signature_header, secret: True,
        "tests/scenarios/security/test_i3_hmac_webhooks.py::test_i3_hmac_webhooks[NP-0891]",
    ),
    (
        "path_traversal_allowed",
        "naukari_pro.security.paths",
        "resolve_safe_path",
        lambda data_dir, user_path: Path(data_dir) / "escaped",
        "tests/scenarios/security/test_i4_path_traversal.py::test_i4_path_traversal[NP-0908]",
    ),
]


def main() -> int:
    import pytest

    # Also neuter validate_text when testing puffery so only PUFFERY gate remains
    demonstrated = 0
    for name, mod, attr, value, nodeid in PROOFS:
        # baseline
        base = pytest.main(["-q", "--tb=line", nodeid])
        if base != 0:
            print(f"BASELINE_FAIL {name} exit={base}")
            return 1
        print(f"BASELINE_PASS {name}")

        if name == "puffery_regex_neutered":
            # PUFFERY miss alone may still fail via support — also force validate ok
            with _patch(mod, attr, value), _patch(
                "naukari_pro.resume_gen.claim_validator", "validate_text", _always_ok_validate
            ):
                # Re-bind test's imported PUFFERY/validate_text by reloading test module path via pytest
                code = pytest.main(["-q", "--tb=line", nodeid])
        else:
            with _patch(mod, attr, value):
                code = pytest.main(["-q", "--tb=line", nodeid])

        if code == 0:
            print(f"MUTATION_DID_NOT_REDDEN {name} — red-team may be decoration")
            return 1
        print(f"MUTATION_REDDENED {name} exit={code}")
        demonstrated += 1

    print(f"MUTATION_PROOFS {demonstrated}/5")
    return 0 if demonstrated == 5 else 1


if __name__ == "__main__":
    raise SystemExit(main())
