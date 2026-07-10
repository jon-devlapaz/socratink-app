-- Durable, user-scoped app-local SEDA session journals.
-- Apply in the Supabase SQL editor before enabling the hosted loop runtime.

CREATE TABLE IF NOT EXISTS public.loop_sessions (
    session_id UUID PRIMARY KEY,
    user_id UUID NOT NULL DEFAULT auth.uid() REFERENCES auth.users (id) ON DELETE CASCADE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    events JSONB NOT NULL DEFAULT '[]'::jsonb,
    version BIGINT NOT NULL DEFAULT 0,
    turn_receipts JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + INTERVAL '30 days'),
    CONSTRAINT loop_sessions_metadata_object
        CHECK (
            jsonb_typeof(metadata) = 'object'
            AND octet_length(metadata::text) <= 262144
        ),
    CONSTRAINT loop_sessions_events_array
        CHECK (
            jsonb_typeof(events) = 'array'
            AND jsonb_array_length(events) <= 128
            AND octet_length(events::text) <= 524288
        ),
    CONSTRAINT loop_sessions_transcript_tail_bounded
        CHECK (
            NOT (metadata ? 'transcript_tail')
            OR (
                jsonb_typeof(metadata -> 'transcript_tail') = 'array'
                AND jsonb_array_length(metadata -> 'transcript_tail') <= 80
                AND octet_length((metadata -> 'transcript_tail')::text) <= 131072
            )
        ),
    CONSTRAINT loop_sessions_version_nonnegative CHECK (version >= 0),
    CONSTRAINT loop_sessions_turn_receipts_bounded
        CHECK (
            jsonb_typeof(turn_receipts) = 'array'
            AND jsonb_array_length(turn_receipts) <= 16
            AND octet_length(turn_receipts::text) <= 2097152
        ),
    CONSTRAINT loop_sessions_expiry_after_creation CHECK (expires_at > created_at)
);

ALTER TABLE public.loop_sessions ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON public.loop_sessions FROM PUBLIC, anon;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.loop_sessions TO authenticated;

DROP POLICY IF EXISTS "loop_sessions_select_own" ON public.loop_sessions;
DROP POLICY IF EXISTS "loop_sessions_insert_own" ON public.loop_sessions;
DROP POLICY IF EXISTS "loop_sessions_update_own" ON public.loop_sessions;
DROP POLICY IF EXISTS "loop_sessions_delete_own" ON public.loop_sessions;

CREATE POLICY "loop_sessions_select_own"
ON public.loop_sessions
FOR SELECT
TO authenticated
USING (auth.uid() = user_id);

CREATE POLICY "loop_sessions_insert_own"
ON public.loop_sessions
FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "loop_sessions_update_own"
ON public.loop_sessions
FOR UPDATE
TO authenticated
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "loop_sessions_delete_own"
ON public.loop_sessions
FOR DELETE
TO authenticated
USING (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS loop_sessions_user_id_idx
ON public.loop_sessions (user_id);

CREATE INDEX IF NOT EXISTS loop_sessions_expires_at_idx
ON public.loop_sessions (expires_at);

CREATE INDEX IF NOT EXISTS loop_sessions_user_updated_at_idx
ON public.loop_sessions (user_id, updated_at DESC);

-- Call this from a trusted Supabase database schedule. It is deliberately not
-- executable by application roles.
CREATE OR REPLACE FUNCTION public.purge_expired_loop_sessions()
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM public.loop_sessions WHERE expires_at <= now();
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$;

REVOKE ALL ON FUNCTION public.purge_expired_loop_sessions()
FROM PUBLIC, anon, authenticated;
