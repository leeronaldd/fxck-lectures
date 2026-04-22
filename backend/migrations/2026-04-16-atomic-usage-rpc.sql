-- Atomic usage tracking — closes two loopholes:
--
-- 1. Race condition: five parallel clicks can all pass "count < limit"
--    before any of them INSERT, so a user gets 5 runs on a 2-cap. The RPC
--    uses a pg_advisory_xact_lock keyed on user_id, so parallel calls for
--    the same user serialize (different users don't contend).
--
-- 2. Disconnect = free run: the old flow counted the row in the SSE path;
--    if the user closed the tab, the row never got inserted. The new flow
--    RESERVES a slot up front and REFUNDS on pipeline failure. Tab close
--    no longer skips the counter.
--
-- Run in Supabase SQL editor (project husdhmaijvughqezlmjt).
-- Safe to re-run: uses CREATE OR REPLACE.

-- ─── try_record_usage ──────────────────────────────────────────────────────
-- Atomic "check count, insert row" for a single user.
-- Returns the new row's UUID if inserted (caller proceeds), NULL if limit
-- would be exceeded (caller returns 403). SECURITY DEFINER bypasses RLS so
-- the function can INSERT regardless of the calling user's row policies —
-- the user_id parameter is checked against auth.uid() for safety.
CREATE OR REPLACE FUNCTION try_record_usage(
  p_user_id uuid,
  p_email text,
  p_limit int
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
  -- Only the authenticated user may reserve their own slot. Prevents a
  -- malicious client from POSTing someone else's user_id.
  IF auth.uid() IS DISTINCT FROM p_user_id THEN
    RAISE EXCEPTION 'user_id mismatch — cannot reserve slot for another user';
  END IF;

  -- Serialize concurrent calls for this user_id. The hash collision rate
  -- is astronomically low; different users proceed in parallel. Lock
  -- auto-releases at transaction end.
  PERFORM pg_advisory_xact_lock(hashtextextended(p_user_id::text, 0));

  SELECT count(*) INTO current_count FROM usage WHERE user_id = p_user_id;
  IF current_count >= p_limit THEN
    RETURN NULL;  -- limit exceeded
  END IF;

  INSERT INTO usage (user_id, email)
  VALUES (p_user_id, p_email)
  RETURNING id INTO new_id;

  RETURN new_id;
END;
$$;

-- ─── refund_usage ──────────────────────────────────────────────────────────
-- Deletes a specific usage row (the one created by try_record_usage) if
-- the pipeline fails after reservation. Scoped to auth.uid() so a user
-- can't refund someone else's slot.
CREATE OR REPLACE FUNCTION refund_usage(p_usage_id uuid)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  DELETE FROM usage
   WHERE id = p_usage_id
     AND user_id = auth.uid();
END;
$$;

-- Grant execute to the authenticated role (not anon). Service role is
-- implicit superuser and doesn't need a grant.
GRANT EXECUTE ON FUNCTION try_record_usage(uuid, text, int) TO authenticated;
GRANT EXECUTE ON FUNCTION refund_usage(uuid) TO authenticated;
