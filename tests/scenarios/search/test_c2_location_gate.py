"""Family C2 — location gate FAIL-CLOSED (NP-0251–0270). trace: MP §4.3"""
import pytest
from naukari_pro.aggregation.india_geo import location_allows_india

ROWS = [
    (f"NP-{251+i:04d}", loc, expect)
    for i, (loc, expect) in enumerate([
        ("Bengaluru", True), ("Bangalore", True), ("NCR", True), ("", False),
        (None, False), ("   ", False), ("London", False), ("Remote (India)", True),
        ("Pune", True), ("Ambiguous", False), ("India", True), ("Gurugram", True),
        ("SF Bay Area", False), ("Remote", True), ("Hyderabad", True),
        ("Singapore", False), ("Delhi", True), ("unknown city xyz", False),
        ("Work from India", True), ("Toronto", False),
    ])
]

@pytest.mark.unit
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,loc,expect", ROWS, ids=[r[0] for r in ROWS])
def test_c2_location_gate(case_id, loc, expect):
    allowed = location_allows_india(loc, allow_unspecified=False)
    assert allowed is expect, f"{case_id} loc={loc!r} got={allowed}"

