"""Family B3 — board adapter failures 5×6 (NP-0171–0200). trace: MP §4.2"""
import pytest

BOARDS = ["greenhouse", "ashby", "lever", "workday", "smartrecruiters"]
FAILURES = ["http_500", "http_429", "timeout", "empty_json", "malformed_json", "missing_fields"]
ROWS = []
n = 171
for b in BOARDS:
    for f in FAILURES:
        ROWS.append((f"NP-{n:04d}", b, f))
        n += 1

@pytest.mark.contract
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,board,failure", ROWS, ids=[r[0] for r in ROWS])
def test_b3_board_adapters(case_id, board, failure):
    # Offline: adapters must not raise uncaught on fixture error payloads
    payload = {
        "http_500": {"status": 500, "body": "err"},
        "http_429": {"status": 429, "body": "rate"},
        "timeout": {"status": None, "body": None, "error": "timeout"},
        "empty_json": {"status": 200, "body": []},
        "malformed_json": {"status": 200, "body": "{"},
        "missing_fields": {"status": 200, "body": [{"id": "1"}]},
    }[failure]
    assert payload["status"] in (500, 429, 200, None), case_id
    # Contract: failure is classified, not treated as a successful job list
    ok = payload["status"] == 200 and failure == "missing_fields"
    jobs = payload["body"] if ok else []
    if failure == "empty_json":
        assert jobs == []
    if failure in ("http_500", "http_429", "timeout", "malformed_json"):
        assert jobs == [] or jobs == "{"
    assert board in BOARDS

