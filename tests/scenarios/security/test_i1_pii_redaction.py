"""Family I1 — PII redaction (NP-0861–0880). trace: MP §6"""
import pytest
from naukari_pro.security.pii import redact_pii

SAMPLES = [
    "email me at candidate@example.com please",
    "call +91-9876543210 now",
    "PAN ABCDE1234F on file",
    "Aadhaar 1234 5678 9012",
    "phone 9876543210 and mail a@b.co",
    "secret sk-abcdefghijklmnopqrstuvwxyz",
    "Authorization: Bearer SUPERSECRETTOKEN123",
    "contact: test.user+tag@gmail.com",
    "mobile 919876543210",
    "id XYABC1234Z",
    "aadhaar 999988887777",
    "plain text with no pii here",
    "mixed candidate@x.com and 9123456789",
    "ghp_abcdefghijklmnopqrstuv",
    "xai-abcdefghijklmnopqrst",
    "email root@localhost.localdomain",
    "+1 415-555-0100 US number",
    "PAN aaapa1234a",
    "nothing sensitive",
    "candidate@example.com +91 98765 43210",
]
ROWS = [(f"NP-{861+i:04d}", SAMPLES[i]) for i in range(20)]

@pytest.mark.redteam
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,raw", ROWS, ids=[r[0] for r in ROWS])
def test_i1_pii_redaction(case_id, raw):
    out = redact_pii(raw)
    if "@" in raw and "example" in raw or "candidate@" in raw:
        assert "[REDACTED_EMAIL]" in out or "@" not in out, case_id
    if "9876543210" in raw.replace(" ", "").replace("-", ""):
        assert "[REDACTED_PHONE]" in out or "9876543210" not in out.replace("-", ""), case_id
    if "sk-" in raw or "ghp_" in raw or "xai-" in raw:
        assert "[REDACTED_SECRET]" in out, case_id
    assert "SUPERSECRETTOKEN123" not in out, case_id

