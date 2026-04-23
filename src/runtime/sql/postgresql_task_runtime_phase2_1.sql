-- Phase2-1 DB runtime kickoff scaffold.
-- This SQL stays tool-agnostic on purpose: it defines the PostgreSQL 17 task-table
-- baseline without freezing a migration framework or managed vendor choice.

CREATE TABLE IF NOT EXISTS runtime_task (
    task_id TEXT PRIMARY KEY,
    task_type TEXT NOT NULL,
    task_scope TEXT NOT NULL,
    source_id TEXT,
    target_type TEXT,
    target_id TEXT,
    window_start TIMESTAMPTZ,
    window_end TIMESTAMPTZ,
    payload_json JSONB NOT NULL,
    status TEXT NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    scheduled_at TIMESTAMPTZ NOT NULL,
    available_at TIMESTAMPTZ NOT NULL,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    lease_owner TEXT,
    lease_expires_at TIMESTAMPTZ,
    parent_task_id TEXT REFERENCES runtime_task (task_id),
    last_error_type TEXT,
    last_error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CHECK (
        status IN (
            'queued',
            'leased',
            'running',
            'succeeded',
            'failed_retryable',
            'failed_terminal',
            'blocked',
            'cancelled'
        )
    ),
    CHECK (attempt_count >= 0),
    CHECK (max_attempts >= 0),
    CHECK (window_start IS NULL OR window_end IS NULL OR window_start <= window_end)
);

CREATE INDEX IF NOT EXISTS runtime_task_status_available_idx
    ON runtime_task (status, available_at);

CREATE INDEX IF NOT EXISTS runtime_task_source_window_idx
    ON runtime_task (source_id, window_start, window_end);

CREATE INDEX IF NOT EXISTS runtime_task_parent_idx
    ON runtime_task (parent_task_id);

CREATE INDEX IF NOT EXISTS runtime_task_lease_expiry_idx
    ON runtime_task (lease_expires_at)
    WHERE status IN ('leased', 'running');
