-- Migration 003: Policy Guard, State & Circuit Breaker Telemetry (v2.1-linucb)
-- Implements policy_state for persistent decision counter & mode, and policy_events audit ledger

CREATE TABLE IF NOT EXISTS policy_state (
    id INTEGER PRIMARY KEY CHECK(id = 1),
    policy_version TEXT NOT NULL,
    decisions_count INTEGER NOT NULL DEFAULT 0,
    mode TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(mode IN ('ACTIVE', 'FALLBACK', 'PAUSED')),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO policy_state (id, policy_version, decisions_count, mode, updated_at)
VALUES (1, 'v2.1-linucb', 0, 'ACTIVE', CURRENT_TIMESTAMP);

CREATE TABLE IF NOT EXISTS policy_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    mode TEXT NOT NULL,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_policy_events_type_time ON policy_events(event_type, created_at);
CREATE INDEX IF NOT EXISTS idx_policy_events_version ON policy_events(policy_version);
