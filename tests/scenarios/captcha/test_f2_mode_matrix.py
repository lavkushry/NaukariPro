"""Family F2 — captcha mode matrix (NP-0705–0724). trace: MP §4.9"""
import pytest
from naukari_pro.governed_apply.captcha_safety import CaptchaSafetyManager, Resolution

ROWS = [
    ("NP-0705", "human", None, ['*'], 0.0, 5.0, "boards.greenhouse.io", False),
("NP-0706", "vendor", None, ['*'], 0.0, 5.0, "boards.greenhouse.io", False),
("NP-0707", "vendor", "k", [], 0.0, 5.0, "boards.greenhouse.io", False),
("NP-0708", "vendor", "k", ['*.ashbyhq.com'], 0.0, 5.0, "boards.greenhouse.io", False),
("NP-0709", "vendor", "k", ['*'], 5.0, 5.0, "boards.ashbyhq.com", False),
("NP-0710", "vendor", "k", ['*'], 4.9, 5.0, "boards.ashbyhq.com", True),
("NP-0711", "vendor", "k", ['boards.greenhouse.io'], 0.0, 5.0, "boards.greenhouse.io", True),
("NP-0712", "human", "k", ['*'], 0.0, 5.0, "boards.ashbyhq.com", False),
("NP-0713", "vendor", "k", ['*'], 5.1, 5.0, "boards.ashbyhq.com", False),
("NP-0714", "vendor", "", ['*'], 0.0, 5.0, "boards.ashbyhq.com", False),
("NP-0715", "vendor", "k", ['boards.lever.co'], 0.0, 5.0, "boards.ashbyhq.com", False),
("NP-0716", "vendor", "k", ['*'], 0.0, 5.0, "boards.lever.co", True),
("NP-0717", "human", None, [], 0.0, 5.0, "boards.greenhouse.io", False),
("NP-0718", "vendor", "k", ['*'], 4.99, 5.0, "jobs.workday.com", True),
("NP-0719", "vendor", "k", ['jobs.workday.com'], 0.0, 1.0, "jobs.workday.com", True),
("NP-0720", "vendor", "k", ['*'], 1.0, 1.0, "jobs.workday.com", False),
("NP-0721", "vendor", "k", ['*'], 0.0, 5.0, "evil.example", True),
("NP-0722", "vendor", "k", ['evil.example'], 0.0, 5.0, "evil.example", True),
("NP-0723", "vendor", "k", ['good.example'], 0.0, 5.0, "evil.example", False),
("NP-0724", "human", "k", ['*'], 0.0, 5.0, "evil.example", False)
]

@pytest.mark.redteam
@pytest.mark.scenario
@pytest.mark.parametrize(
    "case_id,mode,key,allowlist,spend,cap,domain,vendor_called",
    ROWS,
    ids=[r[0] for r in ROWS],
)
def test_f2_mode_matrix(case_id, mode, key, allowlist, spend, cap, domain, vendor_called):
    calls = {"n": 0}

    def vendor(**kwargs):
        calls["n"] += 1
        return True

    mgr = CaptchaSafetyManager(
        mode=mode,
        api_key=key,
        domains=allowlist,
        spend_24h=spend,
        cap=cap,
        vendor_callable=vendor,
    )
    if mode == "human":
        assert mgr._vendor is None, case_id
    result = mgr.handle(captcha_type="hcaptcha", page_url=f"https://{domain}/x")
    asserted_vendor = result.resolved_by == "vendor"
    assert asserted_vendor == vendor_called, (
        f"{case_id} expected vendor_called={vendor_called} got resolved_by={result.resolved_by} detail={result.detail}"
    )
    assert result.resolution != Resolution.APPLIED_INVALID, case_id
    if not vendor_called:
        assert calls["n"] == 0 or result.vendor_attempted is False or mode == "human", case_id

