#!/usr/bin/env python3
"""
Autonomous 50-Job External Career Portal Batch Execution Engine.
Strict Constraints Enforced:
1. At least 50 applications in External Career Portals MUST reach 'Submitted (Confirmed)'.
2. Zero 'ℹ️ Final submit button requires manual review' or '⚠️ Submit clicked but confirmation not detected' accepted.
3. Strict Deduplication: Never apply to the same job again.
4. Remote jobs prioritized first.
5. All applications attached with candidate resume (100% saturation).
6. Full step & field audit trail recorded in SQLite and JSONL.
7. Zero human intervention: automated Gmail IMAP OTP retrieval for security codes.
"""

import sys
import os
import time
import sqlite3
from pathlib import Path
from typing import List, Dict, Any

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from naukari_pro.modules.career_portals import (
    ExternalPortalBatchRunner,
    fetch_live_ats_vacancies,
    CareerPortalManager
)
from naukari_pro.config import DB_PATH

TARGET_CONFIRMED = 50

def get_confirmed_count(db_path: str = DB_PATH) -> int:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    cnt = c.execute(
        "SELECT COUNT(*) FROM applied_jobs WHERE status = 'Submitted (Confirmed)' AND platform LIKE '%career_portal%'"
    ).fetchone()[0]
    conn.close()
    return cnt

def main():
    print("=" * 80)
    print(f"🚀 Launching Autonomous 50 Confirmed External Applications Goal...")
    print(f"Target: At least {TARGET_CONFIRMED} 'Submitted (Confirmed)' Career Portal Applications")
    print(f"Constraint: Zero Manual Review, Zero Unconfirmed Timeouts, Remote First strictly")
    print("=" * 80)

    current_confirmed = get_confirmed_count()
    print(f"[*] Initial Confirmed Applications in DB: {current_confirmed}/{TARGET_CONFIRMED}")

    iteration = 1
    t_start = time.time()

    while current_confirmed < TARGET_CONFIRMED:
        needed = TARGET_CONFIRMED - current_confirmed
        print(f"\n--- Batch Round {iteration}: Need {needed} more confirmed applications ---")
        
        runner = ExternalPortalBatchRunner(headless=True, limit=needed)
        # Target Greenhouse boards where autonomous email verification & zero-captcha apply is 100% reliable
        stats = runner.run_batch(ats_types=["Greenhouse"])
        
        current_confirmed = get_confirmed_count()
        print(f"Round {iteration} complete. Stats: submitted={stats['submitted']}, skipped={stats['skipped']}")
        print(f"Current DB Total Confirmed: {current_confirmed}/{TARGET_CONFIRMED}")
        
        if current_confirmed >= TARGET_CONFIRMED:
            break
            
        iteration += 1
        time.sleep(3)
        if iteration > 10:
            print("[!] Maximum iteration limit reached.")
            break

    elapsed = time.time() - t_start
    print("\n" + "=" * 80)
    print(f"🏁 Goal Run Complete in {elapsed:.1f}s ({elapsed/60:.2f} mins)")
    print(f"Final Confirmed Applications in DB: {current_confirmed}/{TARGET_CONFIRMED}")
    print("=" * 80)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    rows = c.execute(
        "SELECT company, title, applied_at, evidence_path, job_url FROM applied_jobs "
        "WHERE status = 'Submitted (Confirmed)' AND platform LIKE '%career_portal%' "
        "ORDER BY applied_at ASC"
    ).fetchall()
    conn.close()

    print(f"\nTotal Confirmed Dossier Records: {len(rows)}")
    for idx, r in enumerate(rows, 1):
        print(f"  {idx:2d}. {r[0]} | {r[1]} | {r[2]} | {os.path.basename(r[3] or '')}")

if __name__ == "__main__":
    main()
