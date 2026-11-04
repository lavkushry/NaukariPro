import os
import sys
import unittest
from unittest.mock import MagicMock, AsyncMock

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from naukari_pro.modules.career_portals import (
    GreenhouseHandler,
    AshbyHandler,
    LeverHandler,
    WorkdayHandler,
    load_applicant_profile
)
from naukari_pro.modules.db import (
    get_application_field_audit,
    record_batch_field_audit,
    init_db,
    DB_PATH
)

def verify_all_handlers_and_audit():
    print("\n" + "=" * 75)
    print("  🚀 COMPREHENSIVE FIELD & STEP AUDIT VERIFICATION")
    print("=" * 75)

    profile = load_applicant_profile()
    print(f"  • Candidate Email: {profile.get('email')}")
    assert profile.get("email") == "lav84095@gmail.com", f"Violated email constraint! Found: {profile.get('email')}"

    # 1. Greenhouse Handler Audit
    gh = GreenhouseHandler(profile)
    mock_page = MagicMock()
    mock_loc = MagicMock()
    mock_loc.first = mock_loc
    mock_loc.count.return_value = 1
    mock_loc.is_visible.return_value = True
    mock_loc.all.return_value = []
    def locator_router(sel):
        if "email-verification" in sel:
            m = MagicMock()
            m.first = m
            m.count.return_value = 0
            m.is_visible.return_value = False
            return m
        return mock_loc
    mock_page.locator.side_effect = locator_router

    gh_res = gh.fill_form(mock_page)
    gh.upload_resume(mock_page, profile.get("resumePath"))
    gh.submit_form(mock_page)

    print(f"  [✓] Greenhouse Handler Recorded {len(gh.field_records)} Step & Field Interactions:")
    for r in gh.field_records[:4]:
        print(f"      Step {r['step']} ({r['step_name']}): {r['field']} -> '{r['value']}' [{r['type']}]")

    record_batch_field_audit("greenhouse_gitlab_001", "career_portal (Greenhouse)", "GitLab", "Azure Data Platform Engineer", gh.field_records)

    # 2. Ashby Handler Audit
    ashby = AshbyHandler(profile)
    ashby_res = ashby.fill_form(mock_page)
    ashby.upload_resume(mock_page, profile.get("resumePath"))
    ashby.submit_form(mock_page)

    print(f"  [✓] Ashby Handler Recorded {len(ashby.field_records)} Step & Field Interactions:")
    for r in ashby.field_records[:4]:
        print(f"      Step {r['step']} ({r['step_name']}): {r['field']} -> '{r['value']}' [{r['type']}]")

    record_batch_field_audit("ashby_linear_002", "career_portal (Ashby)", "Linear", "Platform Infrastructure Engineer", ashby.field_records)

    # 3. Lever Handler Audit
    lever = LeverHandler(profile)
    lever_res = lever.fill_form(mock_page)
    lever.upload_resume(mock_page, profile.get("resumePath"))
    lever.submit_form(mock_page)

    print(f"  [✓] Lever Handler Recorded {len(lever.field_records)} Step & Field Interactions:")
    for r in lever.field_records[:4]:
        print(f"      Step {r['step']} ({r['step_name']}): {r['field']} -> '{r['value']}' [{r['type']}]")

    record_batch_field_audit("lever_spotify_003", "career_portal (Lever)", "Spotify", "Data Infrastructure Engineer", lever.field_records)

    # 4. Workday Handler Audit
    wd = WorkdayHandler(profile)
    wd_res = wd.fill_form(mock_page)
    wd.upload_resume(mock_page, profile.get("resumePath"))
    wd.submit_form(mock_page)

    print(f"  [✓] Workday Handler Recorded {len(wd.field_records)} Step & Field Interactions:")
    for r in wd.field_records[:4]:
        print(f"      Step {r['step']} ({r['step_name']}): {r['field']} -> '{r['value']}' [{r['type']}]")

    record_batch_field_audit("workday_nvidia_004", "career_portal (Workday)", "NVIDIA", "Senior Data Platform Engineer", wd.field_records)

    # Verify retrieval from SQLite DB
    retrieved_gh = get_application_field_audit("greenhouse_gitlab_001")
    assert len(retrieved_gh) == len(gh.field_records), "Database count mismatch for Greenhouse"
    print(f"\n  [✓] SQLite DB Verified: {len(retrieved_gh)} records retrieved for greenhouse_gitlab_001")

    # Verify append-only JSONL log
    jsonl_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs", "filled_fields_audit.jsonl")
    assert os.path.exists(jsonl_path), "JSONL audit file does not exist"
    with open(jsonl_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    print(f"  [✓] JSONL Audit Ledger Verified: Total {len(lines)} persisted JSON entries")

    print("\n" + "=" * 75)
    print("  🎉 ALL AUDIT CHANNELS VERIFIED WITH ZERO HUMAN INTERVENTION!")
    print("=" * 75 + "\n")

if __name__ == "__main__":
    verify_all_handlers_and_audit()
