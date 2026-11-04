"""Family C6 — SKIP vs NEEDS-HUMAN (NP-0321–0340). trace: MP §4.3"""
import pytest
from naukari_pro.governed_apply.attention import detect_blocker, BlockerClass

CASES = [
    ("clean apply form", None, "OK"),
    ("please solve captcha", BlockerClass.CAPTCHA, "NEEDS_HUMAN"),
    ("sign in to continue", BlockerClass.AUTH, "NEEDS_HUMAN"),
    ("two-factor authentication required", BlockerClass.MFA, "NEEDS_HUMAN"),
    ("I attest under penalty", BlockerClass.LEGAL_ATTESTATION, "NEEDS_HUMAN"),
    ("upload your aadhaar government id", BlockerClass.GOVERNMENT_ID, "NEEDS_HUMAN"),
    ("credit card payment required", BlockerClass.PAYMENT, "NEEDS_HUMAN"),
    ("create an account to apply", BlockerClass.ACCOUNT_CREATE, "NEEDS_HUMAN"),
    ("too many requests rate limit", BlockerClass.RATE_LIMIT, "NEEDS_HUMAN"),
    ("not available in your region geo", BlockerClass.GEO_BLOCK, "NEEDS_HUMAN"),
    ("equal opportunity race gender identity", BlockerClass.DEMOGRAPHIC, "NEEDS_HUMAN"),
    ("hcaptcha widget", BlockerClass.CAPTCHA, "NEEDS_HUMAN"),
    ("normal JD text kubernetes", None, "OK"),
    ("cf-challenge page", BlockerClass.CAPTCHA, "NEEDS_HUMAN"),
    ("authenticator app code", BlockerClass.MFA, "NEEDS_HUMAN"),
    ("log in with SSO", BlockerClass.AUTH, "NEEDS_HUMAN"),
    ("driver license upload", BlockerClass.GOVERNMENT_ID, "NEEDS_HUMAN"),
    ("try again later rate limit", BlockerClass.RATE_LIMIT, "NEEDS_HUMAN"),
    ("pay to apply fee", BlockerClass.PAYMENT, "NEEDS_HUMAN"),
    ("sign up to apply today", BlockerClass.ACCOUNT_CREATE, "NEEDS_HUMAN"),
]
ROWS = [(f"NP-{321+i:04d}", t, b, d) for i, (t, b, d) in enumerate(CASES)]

@pytest.mark.contract
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,text,blocker,decision", ROWS, ids=[r[0] for r in ROWS])
def test_c6_skip_vs_needs_human(case_id, text, blocker, decision):
    got = detect_blocker(text)
    assert got == blocker, case_id
    if decision == "NEEDS_HUMAN":
        assert got is not None, case_id
    else:
        assert got is None, case_id

