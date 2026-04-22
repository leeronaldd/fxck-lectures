-- Paid tier: add Stripe subscription fields to user_profiles and teach
-- try_record_usage to count runs within a billing period instead of always
-- counting lifetime.
--
-- Run AFTER 2026-04-16-atomic-usage-rpc.sql.
-- Run in Supabase SQL editor (project husdhmaijvughqezlmjt).
-- Safe to re-run: uses IF NOT EXISTS and CREATE OR REPLACE.

-- ─── Subscription columns on user_profiles ─────────────────────────────────
-- Kept on user_profiles (1:1 with user) rather than a separate table.
-- subscription_status mirrors Stripe's status string: 'active' | 'past_due'
-- | 'canceled' | 'trialing' | 'incomplete' | 'unpaid' | NULL. We treat
-- only 'active' and 'trialing' as paid; everything else falls back to
-- the free-tier lifetime cap.
ALTER TABLE user_profiles
  ADD COLUMN IF NOT EXISTS stripe_customer_id        TEXT,
  ADD COLUMN IF NOT EXISTS stripe_subscription_id    TEXT,
  ADD COLUMN IF NOT EXISTS subscription_status       TEXT,
  ADD COLUMN IF NOT EXISTS subscription_period_start TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS subscription_period_end   TIMESTAMPTZ;

-- Index for webhook lookups (stripe_customer_id → user row)
CREATE INDEX IF NOT EXISTS user_profiles_stripe_customer_idx
  ON user_profiles (stripe_customer_id)
  WHERE stripe_customer_id IS NOT NULL;

-- ─── Window-aware try_record_usage ─────────────────────────────────────────
-- When p_period_start IS NULL → count lifetime (free tier, 2 lifetime cap).
-- When p_period_start IS set  → count runs created at-or-after that time
--                              (paid tier, 15 per billing period cap).
-- Returns the new row's UUID on success, NULL if limit would be exceeded.
CREATE OR REPLACE FUNCTION try_record_usage(
  p_user_id uuid,
  p_email text,
  p_limit int,
  p_period_start timestamptz DEFAULT NULL
)
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  new_id uuid;
  current_count int;
BEGIN
  -- Only the authenticated user may reserve their own slot.
  IF auth.uid() IS DISTINCT FROM p_user_id THEN
    RAISE EXCEPTION 'user_id mismatch — cannot reserve slot for another user';
  END IF;

  -- Serialize concurrent calls for this user_id.
  PERFORM pg_advisory_xact_lock(hashtextextended(p_user_id::text, 0));

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
  try_record_usage(uuid, text, int, timestamptz) TO authenticated;

-- Keep the 3-arg signature as a thin wrapper so any deployed backend in
-- the middle of a rollout doesn't 503 while the new code ships.
CREATE OR REPLACE FUNCTION try_record_usage(
  p_user_id uuid,
  p_email text,
  p_limit int
)
RETURNS uuid
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT try_record_usage(p_user_id, p_email, p_limit, NULL::timestamptz);
$$;

GRANT EXECUTE ON FUNCTION
  try_record_usage(uuid, text, int) TO authenticated;
