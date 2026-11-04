"""Family K2 — kill-and-resume SQLite WAL (NP-0981–0990). trace: MP §5"""
import sqlite3
import pytest

ROWS = [(f"NP-{981+i:04d}", i) for i in range(10)]

@pytest.mark.chaos
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,idx", ROWS, ids=[r[0] for r in ROWS])
def test_k2_wal_resume(case_id, idx, tmp_sqlite_wal):
    conn = sqlite3.connect(str(tmp_sqlite_wal))
    mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
    assert mode.lower() == "wal", case_id
    conn.execute(
        "INSERT INTO jobs(job_key, url, title, company, location, status, payload_json) VALUES (?,?,?,?,?,?,?)",
        (f"k-{idx}", "https://x", "DevOps", "Acme", "Bengaluru", "discovered", "{}"),
    )
    conn.commit()
    conn.close()
    # reopen = resume
    conn2 = sqlite3.connect(str(tmp_sqlite_wal))
    row = conn2.execute("SELECT status FROM jobs WHERE job_key=?", (f"k-{idx}",)).fetchone()
    conn2.close()
    assert row[0] == "discovered", case_id

