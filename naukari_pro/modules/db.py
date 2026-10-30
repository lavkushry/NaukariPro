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
import unicodedata
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple, Union
from zoneinfo import ZoneInfo

from naukari_pro.config import BASE_DIR, TRACKER_PATH, load_config

DB_PATH = os.path.join(BASE_DIR, "applied_jobs.db")

try:
    IST_TZ = ZoneInfo("Asia/Kolkata")
except Exception:
    IST_TZ = timezone(timedelta(hours=5, minutes=30))

EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Returns a SQLite connection with row_factory set to sqlite3.Row."""
    target_path = db_path or DB_PATH
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None):
    """Initializes the applied_jobs database schema, quarantine table, and indexes."""
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
                raw_metadata TEXT,
                evidence_path TEXT,
                outcome_label TEXT,
                outcome_observed_at TIMESTAMP,
                policy_version TEXT
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_applied_jobs_job_id ON applied_jobs(job_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_applied_jobs_platform ON applied_jobs(platform);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_applied_jobs_company ON applied_jobs(company);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_applied_jobs_status ON applied_jobs(status);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_applied_jobs_applied_at ON applied_jobs(applied_at);")

        # Idempotent column migrations for existing databases
        existing_cols = [row[1] for row in conn.execute("PRAGMA table_info(applied_jobs);").fetchall()]
        if "evidence_path" not in existing_cols:
            conn.execute("ALTER TABLE applied_jobs ADD COLUMN evidence_path TEXT;")
        if "outcome_label" not in existing_cols:
            conn.execute("ALTER TABLE applied_jobs ADD COLUMN outcome_label TEXT;")
        if "outcome_observed_at" not in existing_cols:
            conn.execute("ALTER TABLE applied_jobs ADD COLUMN outcome_observed_at TIMESTAMP;")
        if "policy_version" not in existing_cols:
            conn.execute("ALTER TABLE applied_jobs ADD COLUMN policy_version TEXT;")

        conn.execute("CREATE INDEX IF NOT EXISTS idx_apps_status_time ON applied_jobs(status, applied_at);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_apps_evidence ON applied_jobs(evidence_path);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_applied_jobs_outcome ON applied_jobs(outcome_label);")

        # Profile mutations ledger table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS profile_mutations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL CHECK(platform IN ('naukri', 'linkedin', 'generic')),
                field TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT NOT NULL,
                old_hash TEXT NOT NULL,
                new_hash TEXT NOT NULL,
                is_keyword_mutation INTEGER NOT NULL DEFAULT 1 CHECK(is_keyword_mutation IN (0, 1)),
                mutation_type TEXT NOT NULL DEFAULT 'keyword_injection',
                rationale TEXT NOT NULL,
                expected_effect TEXT NOT NULL,
                approved_by TEXT NOT NULL DEFAULT 'auto_rule_engine',
                status TEXT NOT NULL DEFAULT 'APPLIED' CHECK(status IN ('PROPOSED', 'APPLIED', 'REVERTED', 'FAILED')),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                mutated_at TEXT,
                reverted_at TIMESTAMP,
                metadata TEXT
            );
        """)
        # Idempotent column check for profile_mutations
        mut_cols = [row[1] for row in conn.execute("PRAGMA table_info(profile_mutations);").fetchall()]
        if "mutated_at" not in mut_cols:
            conn.execute("ALTER TABLE profile_mutations ADD COLUMN mutated_at TEXT;")
            conn.execute("UPDATE profile_mutations SET mutated_at = COALESCE(applied_at, timestamp, datetime('now')) WHERE mutated_at IS NULL;")

        conn.execute("DROP INDEX IF EXISTS idx_mut_platform_time;")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mut_platform_time ON profile_mutations(platform, mutated_at);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mut_kw_platform_time ON profile_mutations(platform, is_keyword_mutation, timestamp);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mut_platform_applied_at ON profile_mutations(platform, applied_at);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mut_platform_field ON profile_mutations(platform, field, timestamp);")

        # Quarantine table (Milestone 2 - R2)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS quarantine (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL CHECK(category IN (
                    'screening_ambiguous',
                    'screening_unmatched',
                    'mutation_unwhitelisted',
                    'mutation_blacklisted',
                    'form_validation_error'
                )),
                platform TEXT NOT NULL,
                prompt_text TEXT NOT NULL,
                context_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN (
                    'PENDING',
                    'APPROVED',
                    'REJECTED',
                    'RESOLVED',
                    'EXPIRED'
                )),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                resolved_by TEXT
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_quarantine_status_time ON quarantine(status, created_at);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_quarantine_category ON quarantine(category);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_quarantine_platform ON quarantine(platform);")

        # Weekly search appearance telemetry (Milestone 3 / R3 & §4.7 spec alignment)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS search_appearance_weekly (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL DEFAULT 'naukri',
                week_start TEXT,
                week_start_date TEXT UNIQUE,
                appearances INTEGER NOT NULL DEFAULT 0,
                search_appearances INTEGER NOT NULL DEFAULT 0,
                profile_views INTEGER NOT NULL DEFAULT 0,
                contact_views INTEGER NOT NULL DEFAULT 0,
                captured_at TEXT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                screenshot_path TEXT
            );
        """)
        saw_cols = [row[1] for row in conn.execute("PRAGMA table_info(search_appearance_weekly);").fetchall()]
        for col, col_def in [
            ("id", "INTEGER"),
            ("platform", "TEXT DEFAULT 'naukri'"),
            ("week_start", "TEXT"),
            ("appearances", "INTEGER DEFAULT 0"),
            ("captured_at", "TEXT"),
            ("screenshot_path", "TEXT")
        ]:
            if col not in saw_cols:
                conn.execute(f"ALTER TABLE search_appearance_weekly ADD COLUMN {col} {col_def};")
        conn.execute("UPDATE search_appearance_weekly SET id = rowid WHERE id IS NULL;")
        conn.execute("UPDATE search_appearance_weekly SET week_start = week_start_date WHERE week_start IS NULL;")
        conn.execute("UPDATE search_appearance_weekly SET appearances = search_appearances WHERE appearances = 0 OR appearances IS NULL;")
        conn.execute("UPDATE search_appearance_weekly SET captured_at = recorded_at WHERE captured_at IS NULL;")
        conn.execute("UPDATE search_appearance_weekly SET platform = 'naukri' WHERE platform IS NULL;")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_saw_week ON search_appearance_weekly(week_start_date);")

        # Keyword utility mined table (Milestone 3 / R3 & §4.7 spec alignment)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS keyword_utility (
                token TEXT PRIMARY KEY,
                demand REAL DEFAULT 0.0,
                demand_frequency INTEGER NOT NULL DEFAULT 0,
                saturation REAL DEFAULT 0.0,
                saturation_count INTEGER NOT NULL DEFAULT 0,
                utility REAL DEFAULT 0.0,
                utility_score REAL NOT NULL DEFAULT 0.0,
                observations INTEGER NOT NULL DEFAULT 0,
                claimable INTEGER NOT NULL DEFAULT 1 CHECK(claimable IN (0, 1)),
                last_updated TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        kw_cols = [row[1] for row in conn.execute("PRAGMA table_info(keyword_utility);").fetchall()]
        for col, col_def in [
            ("demand", "REAL DEFAULT 0.0"),
            ("saturation", "REAL DEFAULT 0.0"),
            ("utility", "REAL DEFAULT 0.0"),
            ("observations", "INTEGER DEFAULT 0"),
            ("last_updated", "TEXT")
        ]:
            if col not in kw_cols:
                conn.execute(f"ALTER TABLE keyword_utility ADD COLUMN {col} {col_def};")
        conn.execute("UPDATE keyword_utility SET demand = CAST(demand_frequency AS REAL) WHERE demand = 0.0 OR demand IS NULL;")
        conn.execute("UPDATE keyword_utility SET saturation = CAST(saturation_count AS REAL) WHERE saturation = 0.0 OR saturation IS NULL;")
        conn.execute("UPDATE keyword_utility SET utility = utility_score WHERE utility = 0.0 OR utility IS NULL;")
        conn.execute("UPDATE keyword_utility SET observations = demand_frequency WHERE observations = 0 OR observations IS NULL;")
        conn.execute("UPDATE keyword_utility SET last_updated = updated_at WHERE last_updated IS NULL;")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_kw_utility ON keyword_utility(utility_score DESC);")

        # Policy State & Circuit Breaker Telemetry (v2.1-linucb)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS policy_state (
                id INTEGER PRIMARY KEY CHECK(id = 1),
                policy_version TEXT NOT NULL,
                decisions_count INTEGER NOT NULL DEFAULT 0,
                mode TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(mode IN ('ACTIVE', 'FALLBACK', 'PAUSED')),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("""
            INSERT OR IGNORE INTO policy_state (id, policy_version, decisions_count, mode, updated_at)
            VALUES (1, 'v2.1-linucb', 0, 'ACTIVE', CURRENT_TIMESTAMP);
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS policy_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                policy_version TEXT NOT NULL,
                mode TEXT NOT NULL,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_policy_events_type_time ON policy_events(event_type, created_at);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_policy_events_version ON policy_events(policy_version);")
    conn.close()


def init_mutations_db(db_path: Optional[str] = None):
    """Alias for initializing profile_mutations table."""
    init_db(db_path)


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


COMPANY_CLEANUP_REGEX = re.compile(
    r"\b(inc|incorporated|llc|ltd|limited|pvt|private|corp|corporation|technologies|technology|tech|"
    r"solutions|services|systems|consulting|global|group|india|software)\b|[^\w\s]",
    re.IGNORECASE
)

ROLE_CLEANUP_REGEX = re.compile(
    r"\b(senior|sr|lead|principal|junior|jr|associate|staff)\b|"
    r"[-–/|].*$|"  # Strip trailing qualifiers e.g. - Remote, | Immediate Joiner
    r"\(.*?\)|"    # Strip parentheticals e.g. (ADF, Databricks)
    r"[^\w\s]",
    re.IGNORECASE
)


def normalize_company_name(company: Optional[str]) -> str:
    """Normalizes company name for robust deduplication matching."""
    if not company:
        return ""
    c = str(company).lower()
    c = re.sub(r"\(.*?\)", "", c)
    c = COMPANY_CLEANUP_REGEX.sub(" ", c)
    return " ".join(c.split())


def normalize_role_title(title: Optional[str]) -> str:
    """Normalizes role title to canonical engineering taxonomy."""
    if not title:
        return ""
    t = str(title).lower()
    t = ROLE_CLEANUP_REGEX.sub(" ", t)
    tokens = [tok for tok in t.split() if len(tok) > 1]
    return " ".join(tokens)


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
    evidence_path: Optional[str] = None,
    allow_duplicate: bool = False,
    policy_version: Optional[str] = None,
    db_path: Optional[str] = None,
    policy: Optional[Any] = None
) -> Tuple[bool, str]:
    """
    Records or updates an applied job in SQLite DB.
    Enforces repeat-application deduplication and evidence-first gatekeeper.
    Returns: (success: bool, job_id: str)
    """
    init_db(db_path)
    final_id = job_id or generate_job_id(title, company, job_url)
    applied_time = applied_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Gatekeeper 1: Repeat-application deduplication
    if not allow_duplicate:
        conn = get_db_connection(db_path)
        is_dup = False
        try:
            existing_row = conn.execute("SELECT job_id FROM applied_jobs WHERE job_id = ?", (final_id,)).fetchone()
            if existing_row:
                is_dup = True
            elif is_job_already_applied(title=title, company=company, db_path=db_path):
                is_dup = True
        finally:
            conn.close()

        if is_dup:
            # Wire DUPLICATE (-2.0) penalty to LinUCB policy if policy was provided or metadata chose APPLY
            meta = raw_metadata or {}
            policy_act = meta.get("policy_action") or meta.get("action")
            if policy is not None or policy_act in ("APPLY", 0):
                try:
                    from naukari_pro.modules.learning.policy import extract_context_vector, PolicyAction
                    job_ctx = {
                        "match_score": match_score or 70.0,
                        "required_yoe": experience_req,
                        "posting_age_hours": 24.0,
                        "company": company,
                        "platform": application_type or platform,
                        "salary_lpa": meta.get("salary_lpa", 20.0),
                        "jd": f"{title} {company}"
                    }
                    x = extract_context_vector(job_ctx)
                    if policy is not None:
                        policy.update(x, PolicyAction.APPLY, reward=-2.0)
                    record_policy_event(
                        event_type="DUPLICATE_PENALTY_INGESTED",
                        details={
                            "job_id": final_id,
                            "title": title,
                            "company": company,
                            "reward": -2.0,
                            "match_score": match_score or 70.0,
                            "experience_req": experience_req,
                            "platform": application_type or platform,
                            "salary_lpa": meta.get("salary_lpa", 20.0)
                        },
                        mode="ACTIVE",
                        policy_version=policy_version or "v2.1-linucb",
                        db_path=db_path
                    )
                except Exception as e_pol:
                    pass
            return False, f"BLOCKED_DUPLICATE_{final_id}"

    # Gatekeeper 2: Strict evidence verification gate
    if status == "Submitted (Confirmed)":
        is_valid = False
        if evidence_path and os.path.isfile(evidence_path) and os.path.getsize(evidence_path) >= 1024:
            try:
                with open(evidence_path, "rb") as f:
                    is_valid = (f.read(8) == b"\x89PNG\r\n\x1a\n")
            except Exception:
                is_valid = False
        if not is_valid:
            status = "Form Auto-Filled (Ready for Review)"
            evidence_path = None

    meta = raw_metadata or {}
    if evidence_path:
        meta["evidence_path"] = str(evidence_path)
        meta["evidence_verified_at"] = applied_time
    meta_json = json.dumps(meta, ensure_ascii=False) if meta else None

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
                    job_url, applied_at, applicant_email, raw_metadata, evidence_path, policy_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    status=excluded.status,
                    match_score=COALESCE(excluded.match_score, applied_jobs.match_score),
                    application_type=COALESCE(excluded.application_type, applied_jobs.application_type),
                    job_url=COALESCE(excluded.job_url, applied_jobs.job_url),
                    raw_metadata=COALESCE(excluded.raw_metadata, applied_jobs.raw_metadata),
                    applied_at=COALESCE(applied_jobs.applied_at, excluded.applied_at),
                    evidence_path=COALESCE(excluded.evidence_path, applied_jobs.evidence_path),
                    policy_version=COALESCE(excluded.policy_version, applied_jobs.policy_version);
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
                meta_json,
                evidence_path,
                policy_version
            ))
        return True, final_id
    except Exception as e:
        print(f"  [DB ERROR] Failed to record applied job: {e}")
        return False, final_id
    finally:
        conn.close()


def update_application_evidence(
    job_id: str,
    status: str,
    evidence_path: Optional[str] = None,
    applied_at: Optional[str] = None,
    policy_version: Optional[str] = None,
    db_path: Optional[str] = None
) -> bool:
    """
    Atomically updates status and evidence_path for an applied job.
    Enforces evidence verification if status is 'Submitted (Confirmed)'.
    """
    init_db(db_path)
    if status == "Submitted (Confirmed)":
        is_valid = False
        if evidence_path and os.path.isfile(evidence_path) and os.path.getsize(evidence_path) >= 1024:
            try:
                with open(evidence_path, "rb") as f:
                    is_valid = (f.read(8) == b"\x89PNG\r\n\x1a\n")
            except Exception:
                is_valid = False
        if not is_valid:
            status = "Form Auto-Filled (Ready for Review)"
            evidence_path = None

    update_time = applied_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection(db_path)
    try:
        with conn:
            cursor = conn.execute("""
                UPDATE applied_jobs
                SET status = ?,
                    evidence_path = COALESCE(?, evidence_path),
                    applied_at = COALESCE(?, applied_at),
                    policy_version = COALESCE(?, policy_version)
                WHERE job_id = ?
            """, (status, evidence_path, update_time, policy_version, job_id))
            return cursor.rowcount > 0
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
    Multi-tier deduplication check across all channels:
    1. Direct job_id lookup.
    2. Exact job_url lookup.
    3. Exact title and company lookup.
    4. Normalized canonical role + company lookup.
    """
    init_db(db_path)
    conn = get_db_connection(db_path)
    try:
        # Tier 1: job_id
        target_id = job_id or (generate_job_id(title, company, job_url) if title and company else None)
        if target_id:
            row = conn.execute("SELECT id, status FROM applied_jobs WHERE job_id = ?", (target_id,)).fetchone()
            if row:
                return True

        # Tier 2: job_url
        if job_url and str(job_url).strip() and job_url != "N/A":
            row = conn.execute("SELECT id FROM applied_jobs WHERE job_url = ?", (str(job_url).strip(),)).fetchone()
            if row:
                return True

        # Tier 3 & 4: Title + Company
        if title and company:
            # Exact match check
            row = conn.execute("""
                SELECT id FROM applied_jobs 
                WHERE LOWER(TRIM(title)) = ? AND LOWER(TRIM(company)) = ?
            """, (title.lower().strip(), company.lower().strip())).fetchone()
            if row:
                return True

            # Fuzzy normalized match check
            norm_comp = normalize_company_name(company)
            norm_role = normalize_role_title(title)
            if norm_comp and norm_role:
                for existing in conn.execute("SELECT title, company FROM applied_jobs"):
                    ex_c = normalize_company_name(existing[1])
                    ex_r = normalize_role_title(existing[0])
                    if ex_c and ex_r and ex_c == norm_comp and ex_r == norm_role:
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


class MutationRecordResult(int):
    """
    Dual-compatible result object representing a profile mutation record ID.
    Can be used directly as an int (row_id > 0) or unpacked as a tuple (success, id, message).
    """
    def __new__(cls, val: int, message: str = "Mutation recorded successfully"):
        obj = super().__new__(cls, val)
        obj.message = message
        return obj

    def __iter__(self):
        yield int(self) > 0
        yield int(self)
        yield self.message


class MutationRecordFailure(int):
    """
    Dual-compatible failure object. Evaluates as -1 / False and unpacks as (False, -1, error_message).
    """
    def __new__(cls, error_message: str):
        obj = super().__new__(cls, -1)
        obj.error_message = error_message
        return obj

    def __bool__(self):
        return False

    def __iter__(self):
        yield False
        yield -1
        yield self.error_message


def compute_field_hash(value: Optional[str]) -> str:
    """Computes a deterministic SHA-256 hash for normalized profile field text."""
    if value is None:
        return EMPTY_SHA256
    normalized = unicodedata.normalize("NFC", str(value))
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return EMPTY_SHA256
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def record_profile_mutation(
    platform: str,
    field: str,
    *args,
    new_value: Optional[str] = None,
    rationale: str = "keyword_injection",
    expected_effect: str = "boost_search_appearances",
    old_value: Optional[str] = None,
    old_hash: Optional[str] = None,
    new_hash: Optional[str] = None,
    is_keyword_mutation: bool = True,
    mutation_type: str = "keyword_injection",
    approved_by: str = "auto_rule_engine",
    status: str = "APPLIED",
    metadata: Optional[Dict[str, Any]] = None,
    timestamp: Optional[str] = None,
    applied_at: Optional[str] = None,
    db_path: Optional[str] = None,
    **kwargs
) -> MutationRecordResult:
    """
    Records a profile mutation event in the persistent ledger profile_mutations.
    Returns: MutationRecordResult (int subclass yielding (success, id, msg)).
    """
    init_db(db_path)
    platform_norm = platform.lower().strip()
    if platform_norm not in ("naukri", "linkedin", "generic"):
        return MutationRecordFailure(f"Invalid platform '{platform_norm}'")

    # Resolve positional arguments if provided
    if args:
        if len(args) == 1:
            if new_value is None:
                new_value = args[0]
        elif len(args) == 2:
            if len(str(args[0])) == 64 and len(str(args[1])) == 64 and old_hash is None and new_hash is None:
                old_hash = args[0]
                new_hash = args[1]
            else:
                if new_value is None:
                    new_value = args[0]
                if old_value is None:
                    old_value = args[1]
        elif len(args) >= 3:
            if new_value is None:
                new_value = args[0]
            if old_value is None:
                old_value = args[1]
            if rationale == "keyword_injection" and len(args) > 2:
                rationale = args[2]
            if expected_effect == "boost_search_appearances" and len(args) > 3:
                expected_effect = args[3]

    new_val_str = str(new_value) if new_value is not None else ""
    o_hash = old_hash or compute_field_hash(old_value)
    n_hash = new_hash or compute_field_hash(new_val_str)

    # Detect NOOP on keyword mutations
    if o_hash == n_hash and status == "APPLIED" and is_keyword_mutation:
        return MutationRecordFailure("Identical old and new content hash; no-op mutation rejected")

    app_time = applied_at or timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    meta_json = json.dumps(metadata or {}, ensure_ascii=False) if metadata else None
    kw_flag = 1 if is_keyword_mutation else 0

    conn = get_db_connection(db_path)
    try:
        with conn:
            cursor = conn.execute("""
                INSERT INTO profile_mutations (
                    platform, field, old_value, new_value, old_hash, new_hash,
                    is_keyword_mutation, mutation_type, rationale, expected_effect,
                    approved_by, status, timestamp, applied_at, mutated_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                platform_norm, field.lower().strip(), old_value, new_val_str,
                o_hash, n_hash, kw_flag, mutation_type, rationale,
                expected_effect, approved_by, status, app_time, app_time, app_time, meta_json
            ))
            mut_id = cursor.lastrowid
        return MutationRecordResult(mut_id, "Mutation recorded successfully")
    except Exception as e:
        return MutationRecordFailure(f"Failed to record mutation: {e}")
    finally:
        conn.close()


def get_weekly_mutation_count(
    platform: Optional[str] = None,
    is_keyword_only: bool = True,
    since_days: Optional[int] = None,
    reference_date: Optional[datetime] = None,
    db_path: Optional[str] = None
) -> int:
    """
    Calculates the number of applied mutations in the current calendar week or trailing days.
    """
    init_db(db_path)
    conn = get_db_connection(db_path)
    try:
        if since_days is not None:
            cutoff_dt = datetime.now(timezone.utc) - timedelta(days=since_days)
            cutoff_str = cutoff_dt.strftime("%Y-%m-%d %H:%M:%S")
        else:
            ref_dt = reference_date or datetime.now(IST_TZ)
            if ref_dt.tzinfo is None:
                ref_dt = ref_dt.replace(tzinfo=IST_TZ)
            else:
                ref_dt = ref_dt.astimezone(IST_TZ)
            days_since_monday = ref_dt.weekday()
            monday_ist = (ref_dt - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_str = monday_ist.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        query = """
            SELECT COUNT(*) FROM profile_mutations
            WHERE status = 'APPLIED'
              AND (timestamp >= ? OR applied_at >= ?)
        """
        params: List[Any] = [cutoff_str, cutoff_str]

        if platform:
            query += " AND LOWER(platform) = ?"
            params.append(platform.lower().strip())

        if is_keyword_only:
            query += " AND is_keyword_mutation = 1 AND field != 'freshness_bump'"

        count = conn.execute(query, params).fetchone()[0]
        return int(count)
    finally:
        conn.close()


def can_apply_keyword_mutation(
    platform: str,
    max_weekly: int = 2,
    reference_date: Optional[datetime] = None,
    db_path: Optional[str] = None
) -> Tuple[bool, int, str]:
    """
    Enforces the weekly keyword mutation quota (default <= 2/week).
    Returns: (can_mutate: bool, current_weekly_count: int, reason: str)
    """
    current_count = get_weekly_mutation_count(
        platform=platform,
        is_keyword_only=True,
        reference_date=reference_date,
        db_path=db_path
    )
    if current_count < max_weekly:
        return True, current_count, f"Within weekly budget ({current_count}/{max_weekly} applied this week)"
    return False, current_count, f"Weekly keyword mutation limit reached ({current_count}/{max_weekly} applied this week)"


def get_latest_mutation(
    platform: str,
    field: Optional[str] = None,
    db_path: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Retrieves the most recent applied mutation record for a platform and optional field."""
    init_db(db_path)
    conn = get_db_connection(db_path)
    try:
        query = "SELECT * FROM profile_mutations WHERE LOWER(platform) = LOWER(?) AND status = 'APPLIED'"
        params: List[Any] = [platform.lower().strip()]
        if field:
            query += " AND LOWER(field) = LOWER(?)"
            params.append(field.strip())
        query += " ORDER BY id DESC LIMIT 1"

        row = conn.execute(query, params).fetchone()
        if not row:
            return None
        res = dict(row)
        if res.get("metadata"):
            try:
                res["metadata"] = json.loads(res["metadata"])
            except Exception:
                pass
        return res
    finally:
        conn.close()


def revert_profile_mutation(
    mutation_id: int,
    reason: str = "Rollback requested",
    db_path: Optional[str] = None
) -> bool:
    """Marks a mutation record as REVERTED with timestamp and rollback reason."""
    init_db(db_path)
    conn = get_db_connection(db_path)
    rev_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    try:
        with conn:
            cursor = conn.execute("""
                UPDATE profile_mutations
                SET status = 'REVERTED',
                    reverted_at = ?
                WHERE id = ? AND status = 'APPLIED'
            """, (rev_time, mutation_id))
            return cursor.rowcount > 0
    finally:
        conn.close()


def init_quarantine_table(db_path: Optional[str] = None) -> None:
    """Initializes the quarantine table and indexes in SQLite DB."""
    init_db(db_path)


def quarantine_item(
    category: str,
    platform: str,
    prompt_text: str,
    context: Union[str, Dict[str, Any]],
    status: str = "PENDING",
    db_path: Optional[str] = None
) -> int:
    """
    Inserts an ambiguous or unwhitelisted item into the quarantine table.
    Returns: quarantine_id (int)
    """
    init_db(db_path)
    allowed_categories = {
        "screening_ambiguous", "screening_unmatched",
        "mutation_unwhitelisted", "mutation_blacklisted",
        "form_validation_error"
    }
    if category not in allowed_categories:
        raise ValueError(f"Invalid quarantine category: {category}")

    context_str = json.dumps(context, ensure_ascii=False) if isinstance(context, dict) else str(context)
    conn = get_db_connection(db_path)
    try:
        with conn:
            cursor = conn.execute("""
                INSERT INTO quarantine (category, platform, prompt_text, context_json, status)
                VALUES (?, ?, ?, ?, ?)
            """, (category, platform.lower().strip(), prompt_text.strip(), context_str, status.upper().strip()))
            return cursor.lastrowid
    finally:
        conn.close()


def get_quarantined_items(
    status: Optional[str] = "PENDING",
    category: Optional[str] = None,
    platform: Optional[str] = None,
    limit: int = 50,
    db_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieves quarantined items filtered by status, category, or platform."""
    init_db(db_path)
    conn = get_db_connection(db_path)
    try:
        query = "SELECT * FROM quarantine WHERE 1=1"
        params: List[Any] = []
        if status:
            query += " AND status = ?"
            params.append(status.upper().strip())
        if category:
            query += " AND category = ?"
            params.append(category.strip())
        if platform:
            query += " AND LOWER(platform) = LOWER(?)"
            params.append(platform.strip())
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            try:
                d["context"] = json.loads(d["context_json"])
            except Exception:
                d["context"] = d["context_json"]
            results.append(d)
        return results
    finally:
        conn.close()


def resolve_quarantined_item(
    quarantine_id: int,
    resolution_status: str = "RESOLVED",
    resolved_by: str = "human_operator",
    db_path: Optional[str] = None
) -> bool:
    """Updates quarantine item status and records resolution audit info."""
    init_db(db_path)
    allowed_resolutions = {"APPROVED", "REJECTED", "RESOLVED", "EXPIRED"}
    res_clean = resolution_status.upper().strip()
    if res_clean not in allowed_resolutions:
        raise ValueError(f"Invalid resolution status: {resolution_status}")

    conn = get_db_connection(db_path)
    res_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    try:
        with conn:
            cursor = conn.execute("""
                UPDATE quarantine
                SET status = ?, resolved_at = ?, resolved_by = ?
                WHERE id = ? AND status = 'PENDING'
            """, (res_clean, res_time, resolved_by, quarantine_id))
            return cursor.rowcount > 0
    finally:
        conn.close()


def get_quarantine_summary(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Provides summary counts of quarantine records for digests and monitoring."""
    init_db(db_path)
    conn = get_db_connection(db_path)
    try:
        total = conn.execute("SELECT COUNT(*) FROM quarantine").fetchone()[0]
        pending = conn.execute("SELECT COUNT(*) FROM quarantine WHERE status = 'PENDING'").fetchone()[0]
        resolved = conn.execute("SELECT COUNT(*) FROM quarantine WHERE status != 'PENDING'").fetchone()[0]

        cat_rows = conn.execute("SELECT category, COUNT(*) FROM quarantine GROUP BY category").fetchall()
        by_category = {r[0]: r[1] for r in cat_rows}

        plat_rows = conn.execute("SELECT platform, COUNT(*) FROM quarantine GROUP BY platform").fetchall()
        by_platform = {r[0]: r[1] for r in plat_rows}

        return {
            "total": total,
            "pending": pending,
            "resolved": resolved,
            "by_category": by_category,
            "by_platform": by_platform
        }
    finally:
        conn.close()


def get_daily_application_count(
    platform: Optional[str] = None,
    target_date: Optional[str] = None,
    db_path: Optional[str] = None
) -> int:
    """
    Returns the count of live applications submitted on a given date (defaults to today IST).
    Counts verified and submitted applications.
    """
    init_db(db_path)
    conn = get_db_connection(db_path)
    try:
        if not target_date:
            now_ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
            date_filter = now_ist.strftime("%Y-%m-%d")
        else:
            date_filter = target_date[:10]

        query = """
            SELECT COUNT(*) FROM applied_jobs
            WHERE substr(applied_at, 1, 10) = ?
              AND (
                  status LIKE 'Submitted%'
                  OR status LIKE 'Applied%'
                  OR status IN ('APPLIED', 'Submitted (Confirmed)', 'Submitted (Pending)', 'Form Auto-Filled (Ready for Review)')
              )
        """
        params: List[Any] = [date_filter]
        if platform:
            query += " AND LOWER(platform) = LOWER(?)"
            params.append(platform.strip())

        row = conn.execute(query, params).fetchone()
        return int(row[0]) if row else 0
    finally:
        conn.close()


def can_apply_today(
    platform: Optional[str] = None,
    limit: Optional[int] = None,
    db_path: Optional[str] = None
) -> Tuple[bool, int, int]:
    """
    Checks if additional applications can be submitted today under DAILY_APPLICATION_LIMIT.
    Returns: (can_apply: bool, current_daily_count: int, max_limit: int)
    """
    if limit is None:
        try:
            cfg = load_config()
            configured_limit = cfg.get("search_settings", {}).get("daily_application_limit", 15)
            max_limit = int(configured_limit)
        except Exception:
            max_limit = 15
    else:
        max_limit = limit

    current_count = get_daily_application_count(platform=platform, db_path=db_path)
    can_apply = current_count < max_limit
    return can_apply, current_count, max_limit


def get_policy_state(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Retrieves current policy state (decisions_count, mode, version, updated_at)."""
    target_path = db_path or DB_PATH
    init_db(target_path)
    conn = get_db_connection(target_path)
    try:
        row = conn.execute("SELECT id, policy_version, decisions_count, mode, updated_at FROM policy_state WHERE id = 1").fetchone()
        if row:
            return dict(row)
        with conn:
            conn.execute("""
                INSERT OR IGNORE INTO policy_state (id, policy_version, decisions_count, mode, updated_at)
                VALUES (1, 'v2.1-linucb', 0, 'ACTIVE', CURRENT_TIMESTAMP)
            """)
        row = conn.execute("SELECT id, policy_version, decisions_count, mode, updated_at FROM policy_state WHERE id = 1").fetchone()
        return dict(row) if row else {"id": 1, "policy_version": "v2.1-linucb", "decisions_count": 0, "mode": "ACTIVE", "updated_at": None}
    finally:
        conn.close()


def increment_policy_decisions(db_path: Optional[str] = None, policy_version: str = "v2.1-linucb") -> int:
    """Atomically increments the policy decision counter in SQLite and returns the new count."""
    target_path = db_path or DB_PATH
    init_db(target_path)
    conn = get_db_connection(target_path)
    try:
        with conn:
            conn.execute("""
                UPDATE policy_state
                SET decisions_count = decisions_count + 1,
                    policy_version = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
            """, (policy_version,))
            row = conn.execute("SELECT decisions_count FROM policy_state WHERE id = 1").fetchone()
            return int(row[0]) if row else 1
    finally:
        conn.close()


def update_policy_mode(mode: str, reason: str = "", policy_version: str = "v2.1-linucb", db_path: Optional[str] = None) -> bool:
    """Updates the policy mode (ACTIVE, FALLBACK, PAUSED) and logs a policy event."""
    target_path = db_path or DB_PATH
    init_db(target_path)
    clean_mode = str(mode).upper().strip()
    if clean_mode not in ("ACTIVE", "FALLBACK", "PAUSED"):
        raise ValueError(f"Invalid mode '{mode}'. Must be ACTIVE, FALLBACK, or PAUSED.")
    conn = get_db_connection(target_path)
    try:
        with conn:
            conn.execute("""
                UPDATE policy_state
                SET mode = ?,
                    policy_version = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
            """, (clean_mode, policy_version))
    finally:
        conn.close()

    record_policy_event(
        event_type=f"MODE_CHANGE_{clean_mode}",
        details={"reason": reason, "new_mode": clean_mode},
        mode=clean_mode,
        policy_version=policy_version,
        db_path=target_path
    )
    return True


def record_policy_event(
    event_type: str,
    details: Union[Dict[str, Any], str],
    mode: str = "ACTIVE",
    policy_version: str = "v2.1-linucb",
    db_path: Optional[str] = None
) -> int:
    """Appends an event record to policy_events audit table."""
    target_path = db_path or DB_PATH
    init_db(target_path)
    details_str = json.dumps(details) if isinstance(details, (dict, list)) else str(details)
    conn = get_db_connection(target_path)
    try:
        with conn:
            cur = conn.execute("""
                INSERT INTO policy_events (event_type, policy_version, mode, details, created_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (event_type, policy_version, mode, details_str))
            return cur.lastrowid or 0
    finally:
        conn.close()


def get_recent_policy_events(limit: int = 20, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves recent policy events."""
    target_path = db_path or DB_PATH
    init_db(target_path)
    conn = get_db_connection(target_path)
    try:
        rows = conn.execute("""
            SELECT id, event_type, policy_version, mode, details, created_at
            FROM policy_events
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    count = sync_from_excel_tracker()
    print(f"[✓] Initialized applied_jobs.db and synced {count} historical applications from tracker.")
    stats = get_applied_stats()
    print(f"Total Applications in DB: {stats['total_applications']}")
    print(f"By Platform: {stats['by_platform']}")
    print(f"By Status: {stats['by_status']}")

