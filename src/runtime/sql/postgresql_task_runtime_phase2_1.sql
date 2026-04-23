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

-- Phase2-2 SQL contract templates.
-- These statements are not executed in the current batch. They exist as
-- PostgreSQL-level contract artifacts so future driver work can prove that
-- claim/heartbeat/CAS reclaim guards match the file-backed runtime semantics
-- before any real DB cutover. The :bind markers are abstract placeholders,
-- not a frozen driver or migration-tool syntax choice.

-- contract: runtime_task_claim_by_id_cas
UPDATE runtime_task
SET status = 'leased',
    lease_owner = :worker_id,
    lease_expires_at = :lease_expires_at,
    updated_at = :updated_at
WHERE task_id = :task_id
  AND status IN ('queued', 'failed_retryable')
  AND available_at <= :current_time
  AND (lease_expires_at IS NULL OR lease_expires_at <= :current_time)
RETURNING task_id, status, lease_owner, lease_expires_at, updated_at;
-- end-contract: runtime_task_claim_by_id_cas

-- contract: runtime_task_claim_next_cas
WITH candidate AS (
    SELECT task_id
    FROM runtime_task
    WHERE status IN ('queued', 'failed_retryable')
      AND available_at <= :current_time
      AND (lease_expires_at IS NULL OR lease_expires_at <= :current_time)
    ORDER BY available_at, scheduled_at, task_id
    FOR UPDATE SKIP LOCKED
    LIMIT 1
)
UPDATE runtime_task
SET status = 'leased',
    lease_owner = :worker_id,
    lease_expires_at = :lease_expires_at,
    updated_at = :updated_at
WHERE task_id = (SELECT task_id FROM candidate)
RETURNING task_id, status, lease_owner, lease_expires_at, updated_at;
-- end-contract: runtime_task_claim_next_cas

-- contract: runtime_task_heartbeat_guard
UPDATE runtime_task
SET lease_expires_at = :lease_expires_at,
    updated_at = :updated_at
WHERE task_id = :task_id
  AND status IN ('leased', 'running')
  AND lease_owner = :worker_id
  AND lease_expires_at IS NOT NULL
  AND lease_expires_at > :current_time
RETURNING task_id, status, lease_owner, lease_expires_at, updated_at;
-- end-contract: runtime_task_heartbeat_guard

-- contract: runtime_task_reclaim_expired_cas
UPDATE runtime_task
SET status = 'leased',
    lease_owner = :worker_id,
    lease_expires_at = :lease_expires_at,
    updated_at = :updated_at
WHERE task_id = :task_id
  AND status IN ('leased', 'running')
  AND lease_expires_at IS NOT NULL
  AND lease_expires_at <= :current_time
  AND COALESCE((payload_json ->> 'idempotent_write')::boolean, false) IS TRUE
  AND COALESCE((payload_json ->> 'resume_checkpoint_verified')::boolean, true) IS TRUE
RETURNING task_id, status, lease_owner, lease_expires_at, updated_at;
-- end-contract: runtime_task_reclaim_expired_cas
