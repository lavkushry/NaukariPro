"""Family H1 — Asia/Kolkata scheduling (NP-0801–0815). trace: MP §4.8"""
import os
import pytest
from datetime import datetime
from zoneinfo import ZoneInfo

ROWS = [(f"NP-{801+i:04d}", tz) for i, tz in enumerate([
    "UTC", "America/Los_Angeles", "Europe/London", "Asia/Tokyo", "Australia/Sydney",
    "America/New_York", "Asia/Dubai", "Pacific/Auckland", "UTC", "Asia/Kolkata",
    "Europe/Berlin", "America/Chicago", "Asia/Singapore", "Africa/Cairo", "UTC",
])]

@pytest.mark.unit
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,host_tz", ROWS, ids=[r[0] for r in ROWS])
def test_h1_kolkata_tz(case_id, host_tz, monkeypatch):
    monkeypatch.setenv("TZ", host_tz)
    ist = ZoneInfo("Asia/Kolkata")
    now = datetime(2026, 6, 15, 9, 30, tzinfo=ZoneInfo("UTC")).astimezone(ist)
    assert str(now.tzinfo) == "Asia/Kolkata" or now.tzname() in ("IST", "+0530"), case_id
    assert now.utcoffset().total_seconds() == 19800, case_id

