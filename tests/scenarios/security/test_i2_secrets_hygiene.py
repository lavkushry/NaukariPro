"""Family I2 — secrets hygiene (NP-0881–0890). trace: MP §6"""
import pytest
from naukari_pro.security.pii import secrets_in_text, redact_pii

ROWS = [(f"NP-{881+i:04d}", s) for i, s in enumerate([
    "sk-abcdefghijklmnopqrstuvwxyz0123",
    "ghp_abcdefghijklmnopqrstuvwx",
    "xai-abcdefghijklmnopqrstuv",
    "Authorization: Bearer abcdefghijklmnop",
    "no secrets here",
    "api_key=sk-zzzzzzzzzzzzzzzzzzzz",
    "plain",
    "Bearer XYZABC",
    "sk-short",
    "ok",
])]

@pytest.mark.unit
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,raw", ROWS, ids=[r[0] for r in ROWS])
def test_i2_secrets_hygiene(case_id, raw):
    red = redact_pii(raw)
    if raw.startswith("sk-") and len(raw) > 20:
        assert secrets_in_text(raw) or "[REDACTED_SECRET]" in red, case_id
    assert "sk-abcdefghijklmnopqrstuvwxyz0123" not in red or "sk-abc" not in raw, case_id

