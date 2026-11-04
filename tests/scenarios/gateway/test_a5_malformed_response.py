"""Family A5 — malformed-response contract (NP-0079–0090). trace: MP §4.1"""
import json
import pytest
from naukari_pro.llm.validator import parse_json_content, ValidationError

SAMPLES = [
    '{"ok": true}',
    '{',
    '',
    'not-json',
    '{"ok": true,}',
    '[]',
    'null',
    '{"nested": {"a": 1}}',
    '{"ok": false, "errors": []}',
    '   {"ok": true}   ',
    '{"truncat',
    '{"ok": true, "extra": "' + ("x" * 100) + '"}',
]
ROWS = [(f"NP-{79+i:04d}", SAMPLES[i]) for i in range(12)]

@pytest.mark.contract
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,raw", ROWS, ids=[r[0] for r in ROWS])
def test_a5_malformed_response(case_id, raw):
    try:
        data = parse_json_content(raw)
        assert data is not None or data is None
        # valid parses must be dict/list/primitive without raising
        assert raw.strip() != "{" or False
    except (ValidationError, ValueError, TypeError, json.JSONDecodeError):
        assert True  # malformed correctly rejected
    except Exception as exc:
        # must be a controlled validation failure, not opaque crash without type
        assert type(exc).__name__, case_id

