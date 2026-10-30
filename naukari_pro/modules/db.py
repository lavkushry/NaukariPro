"""
naukariPro Feature: Persistent SQLite Applied Jobs Database
Database file: applied_jobs.db
Ensures zero duplicate applications across Naukri, LinkedIn, and External Career Portals.
Maintains persistent audit trail and tracks application status, match scores, and timestamps.
"""

import os
import re
import json
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

from naukari_pro.config import BASE_DIR, TRACKER_PATH, load_config

DB_PATH = os.path.join(BASE_DIR, "applied_jobs.db")


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Returns a SQLite connection with row_factory set to sqlite3.Row."""
    target_path = db_path or DB_PATH
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None):
    """Initializes the applied_jobs database schema and indexes."""
    target_path = db_path or DB_PATH
    conn = get_db_connection(target_path)
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS applied_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT UNIQUE NOT NULL,
                platform TEXT NOT NULL,
                company TEXT NOT NULL,
                title TEXT NOT NULL,
                location TEXT,
                experience_req TEXT,
                match_score REAL,
                status TEXT NOT NULL,
                application_type TEXT,
                job_url TEXT,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                applicant_email TEXT DEFAULT 'lav84095@gmail.com',
                raw_metadata TEXT
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_applied_jobs_job_id ON applied_jobs(job_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_applied_jobs_platform ON applied_jobs(platform);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_applied_jobs_company ON applied_jobs(company);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_applied_jobs_status ON applied_jobs(status);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_applied_jobs_applied_at ON applied_jobs(applied_at);")
    conn.close()


def generate_job_id(title: str, company: str, job_url: Optional[str] = None) -> str:
    """
    Generates a deterministic unique job ID.
    If job_url contains an ID (e.g. naukri ID or linkedin numeric ID or greenhouse job ID), uses that.
    Otherwise hashes normalized title + company.
    """
    if job_url and str(job_url).strip() and job_url != "N/A":
        u = str(job_url).strip()
        # Naukri numeric ID at end of URL
        m_nk = re.search(r"-(\d{10,16})(?:\?|$)", u)
        if m_nk:
            return f"naukri_{m_nk.group(1)}"
        # LinkedIn job ID
        m_li = re.search(r"/jobs/view/(\d+)", u)
        if m_li:
            return f"linkedin_{m_li.group(1)}"
        # Greenhouse gh_jid
        m_gh = re.search(r"gh_jid=(\d+)", u)
        if m_gh:
            return f"greenhouse_{m_gh.group(1)}"
        # Ashby / Lever / Workday URL slug hash
        url_hash = hashlib.md5(u.encode("utf-8")).hexdigest()[:12]
        norm = re.sub(r"[^a-z0-9]+", "_", f"{title.lower().strip()}_{company.lower().strip()}")[:30]
        return f"{norm}_{url_hash}"

    norm = re.sub(r"[^a-z0-9]+", "_", f"{title.lower().strip()}_{company.lower().strip()}")
    norm_hash = hashlib.md5(norm.encode("utf-8")).hexdigest()[:8]
    return f"{norm[:40]}_{norm_hash}"


def record_applied_job(
    title: str,
    company: str,
    platform: str = "naukri",
    location: str = "Hyderabad / Remote",
    experience_req: str = "2-5 Yrs",
    match_score: Optional[float] = 85.0,
    status: str = "Submitted (Pending)",
    application_type: str = "1-Click Direct",
    job_url: Optional[str] = "N/A",
    applicant_email: str = "lav84095@gmail.com",
    raw_metadata: Optional[Dict[str, Any]] = None,
    applied_at: Optional[str] = None,
    job_id: Optional[str] = None,
    db_path: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Records or updates an applied job in SQLite DB.
    Returns: (success: bool, job_id: str)
    """
    init_db(db_path)
    final_id = job_id or generate_job_id(title, company, job_url)
    applied_time = applied_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    meta_json = json.dumps(raw_metadata or {}, ensure_ascii=False) if raw_metadata else None

    # Parse numeric score
    score_val = None
    if match_score is not None:
        try:
            if isinstance(match_score, str):
                score_val = float(match_score.replace("%", "").strip())
            else:
                score_val = float(match_score)
        except (ValueError, TypeError):
            score_val = None

    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute("""
                INSERT INTO applied_jobs (
                    job_id, platform, company, title, location,
                    experience_req, match_score, status, application_type,
                    job_url, applied_at, applicant_email, raw_metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    status=excluded.status,
                    match_score=COALESCE(excluded.match_score, applied_jobs.match_score),
                    application_type=COALESCE(excluded.application_type, applied_jobs.application_type),
                    job_url=COALESCE(excluded.job_url, applied_jobs.job_url),
                    raw_metadata=COALESCE(excluded.raw_metadata, applied_jobs.raw_metadata),
                    applied_at=COALESCE(applied_jobs.applied_at, excluded.applied_at);
            """, (
                final_id,
                platform.lower(),
                company.strip(),
                title.strip(),
                location,
                experience_req,
                score_val,
                status,
                application_type,
                str(job_url or "N/A"),
                applied_time,
                applicant_email,
                meta_json
            ))
        return True, final_id
    except Exception as e:
        print(f"  [DB ERROR] Failed to record applied job: {e}")
        return False, final_id
    finally:
        conn.close()


def is_job_already_applied(
    title: Optional[str] = None,
    company: Optional[str] = None,
    job_url: Optional[str] = None,
    job_id: Optional[str] = None,
    db_path: Optional[str] = None
) -> bool:
    """
    Checks if a job has already been applied across any platform.
    Checks by job_id, exact job_url, or normalized title + company.
    """
    init_db(db_path)
    conn = get_db_connection(db_path)
    try:
        # Check by job_id
        target_id = job_id or (generate_job_id(title, company, job_url) if title and company else None)
        if target_id:
            row = conn.execute("SELECT id, status FROM applied_jobs WHERE job_id = ?", (target_id,)).fetchone()
            if row:
                return True

        # Check by url if valid
        if job_url and str(job_url).strip() and job_url != "N/A":
            row = conn.execute("SELECT id FROM applied_jobs WHERE job_url = ?", (str(job_url).strip(),)).fetchone()
            if row:
                return True

        # Check by normalized title and company
        if title and company:
            t_norm = title.lower().strip()
            c_norm = company.lower().strip()
            row = conn.execute("""
                SELECT id FROM applied_jobs 
                WHERE LOWER(TRIM(title)) = ? AND LOWER(TRIM(company)) = ?
            """, (t_norm, c_norm)).fetchone()
            if row:
                return True

        return False
    finally:
        conn.close()


def get_applied_stats(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Returns application statistics from SQLite DB."""
    init_db(db_path)
    conn = get_db_connection(db_path)
    try:
        total = conn.execute("SELECT COUNT(*) FROM applied_jobs").fetchone()[0]

        # By platform
        platforms = {}
        for row in conn.execute("SELECT platform, COUNT(*) FROM applied_jobs GROUP BY platform"):
            platforms[row[0]] = row[1]

        # By status
        statuses = {}
        for row in conn.execute("SELECT status, COUNT(*) FROM applied_jobs GROUP BY status"):
            statuses[row[0]] = row[1]

        # Top recent
        recent = []
        for row in conn.execute("""
            SELECT job_id, platform, company, title, status, match_score, applied_at, job_url 
            FROM applied_jobs 
            ORDER BY applied_at DESC LIMIT 10
        """):
            recent.append(dict(row))

        return {
            "total_applications": total,
            "by_platform": platforms,
            "by_status": statuses,
            "recent": recent
        }
    finally:
        conn.close()


def sync_from_excel_tracker(excel_path: Optional[str] = None, db_path: Optional[str] = None) -> int:
    """
    Backfills/synchronizes existing live applications from Naukri_Live_Application_Tracker.xlsx
    into applied_jobs.db.
    Ignores dry runs and errors.
    """
    import openpyxl
    target_excel = excel_path or TRACKER_PATH
    if not os.path.exists(target_excel):
        print(f"  [DB SYNC] Tracker file {target_excel} not found.")
        return 0

    init_db(db_path)
    wb = openpyxl.load_workbook(target_excel, data_only=True)
    synced_count = 0

    # 1. Sync Applications_Log (Naukri & External Portals)
    if "Applications_Log" in wb.sheetnames:
        ws = wb["Applications_Log"]
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or not any(row):
                continue
            date_str = str(row[0]) if len(row) > 0 and row[0] else ""
            company = str(row[1]) if len(row) > 1 and row[1] else ""
            title = str(row[2]) if len(row) > 2 and row[2] else ""
            score = row[3] if len(row) > 3 else None
            role_cat = str(row[4]) if len(row) > 4 and row[4] else "Azure Data Engineer"
            exp_req = str(row[5]) if len(row) > 5 and row[5] else "2-5 Yrs"
            location = str(row[6]) if len(row) > 6 and row[6] else "Hyderabad / Bengaluru"
            app_type = str(row[7]) if len(row) > 7 and row[7] else "1-Click Direct"
            status = str(row[8]) if len(row) > 8 and row[8] else "Submitted"
            url = str(row[9]) if len(row) > 9 and row[9] else "N/A"

            if not title or not company:
                continue

            # Skip errors from legacy batch (they are not successfully applied jobs)
            if status == "Error":
                continue

            # Detect platform
            if "career portal" in app_type.lower() or "external" in app_type.lower():
                platform = "career_portal"
            elif "linkedin" in app_type.lower() or "linkedin" in url.lower():
                platform = "linkedin"
            else:
                platform = "naukri"

            ok, _ = record_applied_job(
                title=title,
                company=company,
                platform=platform,
                location=location,
                experience_req=exp_req,
                match_score=score,
                status=status,
                application_type=app_type,
                job_url=url,
                applied_at=date_str if len(date_str) >= 10 else None,
                db_path=db_path
            )
            if ok:
                synced_count += 1

    # 2. Sync LinkedIn_Applications_Log (Live submissions only)
    if "LinkedIn_Applications_Log" in wb.sheetnames:
        ws_li = wb["LinkedIn_Applications_Log"]
        for row in ws_li.iter_rows(min_row=2, values_only=True):
            if not row or not any(row):
                continue
            # Header: Job ID, Platform, Company, Job Title, Location, Match Score, Status, Steps Completed, Applied Timestamp, Job URL
            j_id = str(row[0]) if len(row) > 0 and row[0] else ""
            comp = str(row[2]) if len(row) > 2 and row[2] else ""
            ttl = str(row[3]) if len(row) > 3 and row[3] else ""
            loc = str(row[4]) if len(row) > 4 and row[4] else ""
            score = row[5] if len(row) > 5 else None
            stat = str(row[6]) if len(row) > 6 and row[6] else "Applied"
            time_str = str(row[8]) if len(row) > 8 and row[8] else ""
            u = str(row[9]) if len(row) > 9 and row[9] else "N/A"

            if not ttl or not comp:
                continue
            if "dry_run" in stat.lower():
                continue

            ok, _ = record_applied_job(
                title=ttl,
                company=comp,
                platform="linkedin",
                location=loc,
                experience_req="2-5 Yrs",
                match_score=score,
                status=stat,
                application_type="Easy Apply",
                job_url=u,
                applied_at=time_str if len(time_str) >= 10 else None,
                job_id=f"linkedin_{j_id}" if j_id and j_id.isdigit() else None,
                db_path=db_path
            )
            if ok:
                synced_count += 1

    return synced_count


if __name__ == "__main__":
    init_db()
    count = sync_from_excel_tracker()
    print(f"[✓] Initialized applied_jobs.db and synced {count} historical applications from tracker.")
    stats = get_applied_stats()
    print(f"Total Applications in DB: {stats['total_applications']}")
    print(f"By Platform: {stats['by_platform']}")
    print(f"By Status: {stats['by_status']}")
