-- Daily cap + multiple paid tiers.
--
-- Adds a per-user `subscription_tier` ('pro' | 'max' | NULL) so the backend
-- can apply tier-specific limits without hardcoding price IDs in SQL, and
-- extends try_record_usage with an optional daily cap (atomically checked
-- alongside the period limit so the same advisory lock guards both).
--
-- Run AFTER 2026-04-16-paid-tier.sql.
-- Run in Supabase SQL editor (project husdhmaijvughqezlmjt).
-- Safe to re-run: uses IF NOT EXISTS / CREATE OR REPLACE.

-- ─── Tier column ───────────────────────────────────────────────────────────
ALTER TABLE user_profiles
  ADD COLUMN IF NOT EXISTS subscription_tier TEXT;

-- ─── Window-aware + daily-capped try_record_usage ──────────────────────────
-- p_period_start: NULL → lifetime count, set → count from that timestamp.
-- p_daily_cap:    NULL → no daily limit, set → also blocks if user has run
--                 that many in the last 24 hours.
-- Both checks happen inside the same advisory lock so a parallel run can't
-- slip past either limit. Returns NULL on either limit hit (caller can show
-- a generic "you've hit your limit" message).
CREATE OR REPLACE FUNCTION try_record_usage(
  p_user_id uuid,
  p_email text,
  p_limit int,
  p_period_start timestamptz DEFAULT NULL,
  p_daily_cap int DEFAULT NULL
)
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  new_id uuid;
  current_count int;
  daily_count int;
BEGIN
  IF auth.uid() IS DISTINCT FROM p_user_id THEN
    RAISE EXCEPTION 'user_id mismatch — cannot reserve slot for another user';
  END IF;

  PERFORM pg_advisory_xact_lock(hashtextextended(p_user_id::text, 0));

  -- Daily cap check (paid tier abuse guard)
  IF p_daily_cap IS NOT NULL THEN
    SELECT count(*) INTO daily_count
      FROM usage
     WHERE user_id = p_user_id
       AND created_at >= NOW() - INTERVAL '24 hours';
    IF daily_count >= p_daily_cap THEN
      RETURN NULL;
    END IF;
  END IF;

  -- Period (or lifetime) cap check
  IF p_period_start IS NULL THEN
    SELECT count(*) INTO current_count
      FROM usage
     WHERE user_id = p_user_id;
  ELSE
    SELECT count(*) INTO current_count
      FROM usage
     WHERE user_id = p_user_id
       AND created_at >= p_period_start;
  END IF;

  IF current_count >= p_limit THEN
    RETURN NULL;
  END IF;

  INSERT INTO usage (user_id, email)
  VALUES (p_user_id, p_email)
  RETURNING id INTO new_id;

  RETURN new_id;
END;
$$;

GRANT EXECUTE ON FUNCTION
  try_record_usage(uuid, text, int, timestamptz, int) TO authenticated;
