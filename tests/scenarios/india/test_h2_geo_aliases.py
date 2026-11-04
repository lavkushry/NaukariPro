"""Family H2 — geo aliases (NP-0816–0835). trace: MP §4.8"""
import pytest
from naukari_pro.aggregation.india_geo import normalize_location

PAIRS = [
    ("Bengaluru", "bengaluru"), ("Bangalore", "bengaluru"), ("BLR", "bengaluru"),
    ("NCR", "ncr"), ("Delhi", "ncr"), ("Gurugram", "ncr"), ("Gurgaon", "ncr"),
    ("Noida", "ncr"), ("New Delhi", "ncr"), ("Pune", "pune"), ("Hyderabad", "hyderabad"),
    ("Mumbai", "mumbai"), ("Bombay", "mumbai"), ("Chennai", "chennai"), ("Madras", "chennai"),
    ("Remote (India)", "remote_india"), ("WFH India", "remote_india"),
    ("Bengaluru, Karnataka, India", "bengaluru"), ("Delhi-NCR", "ncr"), ("Ghaziabad", "ncr"),
]
ROWS = [(f"NP-{816+i:04d}", a, b) for i, (a, b) in enumerate(PAIRS)]

@pytest.mark.unit
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,raw,canon", ROWS, ids=[r[0] for r in ROWS])
def test_h2_geo_aliases(case_id, raw, canon):
    assert normalize_location(raw) == canon, case_id

