-- Migration 002: Learning Subsystem Tables & Indexes (Milestones 3, 4, 5 / §4.7 Specification)
-- Ensures outcome labels, weekly telemetry, and keyword utility tables exist with exact schema contracts

-- 1. Applied Jobs Learning Columns & Indexes
CREATE INDEX IF NOT EXISTS idx_apps_status_time ON applied_jobs(status, applied_at);
CREATE INDEX IF NOT EXISTS idx_apps_evidence ON applied_jobs(evidence_path);
CREATE INDEX IF NOT EXISTS idx_applied_jobs_outcome ON applied_jobs(outcome_label);

-- 2. Profile Mutations Ledger Table
CREATE TABLE IF NOT EXISTS profile_mutations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL CHECK(platform IN ('naukri', 'linkedin', 'generic')),
    field TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT NOT NULL,
    old_hash TEXT,
    new_hash TEXT,
    mutated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_keyword_mutation INTEGER NOT NULL DEFAULT 1 CHECK(is_keyword_mutation IN (0, 1)),
    mutation_type TEXT NOT NULL DEFAULT 'keyword_injection',
    rationale TEXT,
    expected_effect TEXT,
    approved_by TEXT NOT NULL DEFAULT 'auto_rule_engine',
    status TEXT NOT NULL DEFAULT 'APPLIED' CHECK(status IN ('PROPOSED', 'APPLIED', 'REVERTED', 'FAILED')),
    reverted_at TIMESTAMP,
    metadata TEXT
);
CREATE INDEX IF NOT EXISTS idx_mut_platform_time ON profile_mutations(platform, mutated_at);
CREATE INDEX IF NOT EXISTS idx_mut_kw_platform_time ON profile_mutations(platform, is_keyword_mutation, timestamp);
CREATE INDEX IF NOT EXISTS idx_mut_platform_applied_at ON profile_mutations(platform, applied_at);
CREATE INDEX IF NOT EXISTS idx_mut_platform_field ON profile_mutations(platform, field, timestamp);

-- 3. Weekly Search Appearance Telemetry Table (§4.7 spec alignment + legacy compatibility)
CREATE TABLE IF NOT EXISTS search_appearance_weekly (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL DEFAULT 'naukri',
    week_start TEXT NOT NULL,
    week_start_date TEXT,
    appearances INTEGER NOT NULL DEFAULT 0,
    search_appearances INTEGER NOT NULL DEFAULT 0,
    profile_views INTEGER NOT NULL DEFAULT 0,
    contact_views INTEGER NOT NULL DEFAULT 0,
    captured_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    screenshot_path TEXT
);
CREATE INDEX IF NOT EXISTS idx_saw_week ON search_appearance_weekly(week_start_date);

-- 4. Keyword Utility Table (§4.7 spec alignment + legacy compatibility)
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
    last_updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_kw_utility ON keyword_utility(utility_score DESC);

-- 5. Quarantine Ledger Table
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
CREATE INDEX IF NOT EXISTS idx_quarantine_status_time ON quarantine(status, created_at);
CREATE INDEX IF NOT EXISTS idx_quarantine_category ON quarantine(category);
CREATE INDEX IF NOT EXISTS idx_quarantine_platform ON quarantine(platform);
