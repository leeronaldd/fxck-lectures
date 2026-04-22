-- Adds current_stage column to sessions table so the backend can persist
-- the active pipeline stage name ("Transcribing lecture", "Generating
-- lecture", etc.) and the reader can display it on reload.
--
-- Run once via Supabase SQL Editor (Dashboard → SQL Editor → paste → Run).
-- Safe to re-run — IF NOT EXISTS guard prevents errors on second apply.

ALTER TABLE public.sessions
  ADD COLUMN IF NOT EXISTS current_stage TEXT NULL;

-- Backfill existing rows to NULL explicitly (no-op but documents intent).
UPDATE public.sessions
  SET current_stage = NULL
  WHERE current_stage IS DISTINCT FROM NULL AND status = 'ready';
