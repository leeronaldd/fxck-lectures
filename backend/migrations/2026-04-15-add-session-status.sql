-- Add status + error_message columns to sessions so the frontend can show
-- spinner / error / content correctly instead of silent "No lecture loaded".
--
-- Run in Supabase SQL editor (project husdhmaijvughqezlmjt).
-- Safe to re-run: uses IF NOT EXISTS guards.

ALTER TABLE sessions
  ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'ready',
  ADD COLUMN IF NOT EXISTS error_message TEXT;

-- Backfill: existing rows are completed lectures, leave them as 'ready' (the default).
-- New empty sessions created via /api/sessions will get 'ready' too, but the
-- pipeline runner will immediately flip them to 'processing' before generation
-- starts, then 'ready' on success or 'failed' on exception.

-- Optional: index for "show me my in-flight runs" queries on the dashboard.
CREATE INDEX IF NOT EXISTS sessions_user_status_idx
  ON sessions (user_id, status);
