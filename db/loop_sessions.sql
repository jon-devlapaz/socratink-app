-- Durable, user-scoped app-local SEDA session journals.
-- Apply in the Supabase SQL editor before enabling the hosted loop runtime.

CREATE TABLE IF NOT EXISTS public.sources (
    source_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL DEFAULT auth.uid() REFERENCES auth.users (id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT sources_owner_identity UNIQUE (user_id, source_id)
);

CREATE TABLE IF NOT EXISTS public.source_revisions (
    revision_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL,
    user_id UUID NOT NULL DEFAULT auth.uid() REFERENCES auth.users (id) ON DELETE CASCADE,
    revision_number INTEGER NOT NULL DEFAULT 1 CHECK (revision_number > 0),
    normalized_text TEXT,
    checksum_sha256 TEXT,
    content_bytes BIGINT,
    normalization_version TEXT NOT NULL CHECK (normalization_version <> ''),
    extraction_version TEXT NOT NULL CHECK (extraction_version <> ''),
    parser_version TEXT NOT NULL CHECK (parser_version <> ''),
    source_kind TEXT NOT NULL CHECK (source_kind IN ('paste', 'txt', 'md', 'pdf')),
    provenance JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    erased_at TIMESTAMPTZ,
    CONSTRAINT source_revisions_owner_identity UNIQUE (user_id, revision_id),
    CONSTRAINT source_revisions_source_revision UNIQUE (source_id, revision_number),
    CONSTRAINT source_revisions_owner_source_fk
        FOREIGN KEY (user_id, source_id)
        REFERENCES public.sources (user_id, source_id)
        ON DELETE RESTRICT,
    CONSTRAINT source_revisions_provenance_object
        CHECK (
            jsonb_typeof(provenance) = 'object'
            AND octet_length(provenance::text) <= 8192
            AND provenance = jsonb_build_object(
                'intake_surface', 'promoted-alpha-file-intake',
                'input_method', CASE WHEN source_kind = 'paste' THEN 'paste' ELSE 'file' END
            )
        ),
    CONSTRAINT source_revisions_content_state
        CHECK (
            (
                normalized_text IS NOT NULL
                AND normalized_text <> ''
                AND octet_length(normalized_text) <= 65536
                AND checksum_sha256 ~ '^[0-9a-f]{64}$'
                AND checksum_sha256 = encode(sha256(convert_to(normalized_text, 'UTF8')), 'hex')
                AND content_bytes = octet_length(normalized_text)
                AND erased_at IS NULL
            )
            OR
            (
                normalized_text IS NULL
                AND checksum_sha256 IS NULL
                AND content_bytes IS NULL
                AND erased_at IS NOT NULL
            )
        )
);

CREATE UNIQUE INDEX IF NOT EXISTS source_revisions_owner_pipeline_checksum_idx
ON public.source_revisions (
    user_id,
    checksum_sha256,
    normalization_version,
    extraction_version,
    parser_version,
    source_kind
)
WHERE checksum_sha256 IS NOT NULL;
DROP INDEX IF EXISTS public.source_revisions_owner_checksum_idx;

CREATE INDEX IF NOT EXISTS source_revisions_owner_source_idx
ON public.source_revisions (user_id, source_id);

CREATE TABLE IF NOT EXISTS public.source_intake_requests (
    user_id UUID NOT NULL DEFAULT auth.uid() REFERENCES auth.users (id) ON DELETE CASCADE,
    idempotency_key UUID NOT NULL,
    payload_hash TEXT NOT NULL CHECK (payload_hash ~ '^[0-9a-f]{64}$'),
    source_id UUID NOT NULL,
    revision_id UUID NOT NULL,
    result_checksum_sha256 TEXT NOT NULL CHECK (result_checksum_sha256 ~ '^[0-9a-f]{64}$'),
    normalization_version TEXT NOT NULL,
    extraction_version TEXT NOT NULL,
    parser_version TEXT NOT NULL,
    source_kind TEXT NOT NULL,
    provenance JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, idempotency_key),
    CONSTRAINT source_intake_requests_owner_source_fk
        FOREIGN KEY (user_id, source_id)
        REFERENCES public.sources (user_id, source_id)
        ON DELETE RESTRICT,
    CONSTRAINT source_intake_requests_owner_revision_fk
        FOREIGN KEY (user_id, revision_id)
        REFERENCES public.source_revisions (user_id, revision_id)
        ON DELETE RESTRICT,
    CONSTRAINT source_intake_requests_provenance
        CHECK (
            source_kind IN ('paste', 'txt', 'md', 'pdf')
            AND provenance = jsonb_build_object(
                'intake_surface', 'promoted-alpha-file-intake',
                'input_method', CASE WHEN source_kind = 'paste' THEN 'paste' ELSE 'file' END
            )
        )
);

CREATE TABLE IF NOT EXISTS public.loop_sessions (
    session_id UUID PRIMARY KEY,
    user_id UUID NOT NULL DEFAULT auth.uid() REFERENCES auth.users (id) ON DELETE CASCADE,
    source_revision_id UUID,
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
    CONSTRAINT loop_sessions_expiry_after_creation CHECK (expires_at > created_at),
    CONSTRAINT loop_sessions_owner_identity UNIQUE (user_id, session_id),
    CONSTRAINT loop_sessions_source_revision_owner_fk
        FOREIGN KEY (user_id, source_revision_id)
        REFERENCES public.source_revisions (user_id, revision_id)
        ON DELETE RESTRICT
);

ALTER TABLE public.loop_sessions
ADD COLUMN IF NOT EXISTS source_revision_id UUID;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'public.loop_sessions'::regclass
          AND conname = 'loop_sessions_owner_identity'
    ) THEN
        ALTER TABLE public.loop_sessions
        ADD CONSTRAINT loop_sessions_owner_identity UNIQUE (user_id, session_id);
    END IF;
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'public.loop_sessions'::regclass
          AND conname = 'loop_sessions_source_revision_owner_fk'
    ) THEN
        ALTER TABLE public.loop_sessions
        ADD CONSTRAINT loop_sessions_source_revision_owner_fk
        FOREIGN KEY (user_id, source_revision_id)
        REFERENCES public.source_revisions (user_id, revision_id)
        ON DELETE RESTRICT;
    END IF;
END;
$$;

ALTER TABLE public.sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.source_revisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.source_intake_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.loop_sessions ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON public.sources FROM PUBLIC, anon;
REVOKE ALL ON public.source_revisions FROM PUBLIC, anon;
REVOKE ALL ON public.source_intake_requests FROM PUBLIC, anon;
REVOKE ALL ON public.loop_sessions FROM PUBLIC, anon;
GRANT SELECT, INSERT ON public.sources TO authenticated;
GRANT SELECT, INSERT ON public.source_revisions TO authenticated;
GRANT UPDATE (normalized_text, checksum_sha256, content_bytes, erased_at)
ON public.source_revisions TO authenticated;
GRANT SELECT, INSERT, DELETE ON public.source_intake_requests TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.loop_sessions TO authenticated;

DROP POLICY IF EXISTS "sources_select_own" ON public.sources;
DROP POLICY IF EXISTS "sources_insert_own" ON public.sources;
DROP POLICY IF EXISTS "source_revisions_select_own" ON public.source_revisions;
DROP POLICY IF EXISTS "source_revisions_insert_own" ON public.source_revisions;
DROP POLICY IF EXISTS "source_revisions_update_own" ON public.source_revisions;
DROP POLICY IF EXISTS "source_intake_requests_select_own" ON public.source_intake_requests;
DROP POLICY IF EXISTS "source_intake_requests_insert_own" ON public.source_intake_requests;
DROP POLICY IF EXISTS "source_intake_requests_delete_own" ON public.source_intake_requests;
DROP POLICY IF EXISTS "loop_sessions_select_own" ON public.loop_sessions;
DROP POLICY IF EXISTS "loop_sessions_insert_own" ON public.loop_sessions;
DROP POLICY IF EXISTS "loop_sessions_update_own" ON public.loop_sessions;
DROP POLICY IF EXISTS "loop_sessions_delete_own" ON public.loop_sessions;

CREATE POLICY "sources_select_own"
ON public.sources
FOR SELECT
TO authenticated
USING (auth.uid() IS NOT NULL AND auth.uid() = user_id);

CREATE POLICY "sources_insert_own"
ON public.sources
FOR INSERT
TO authenticated
WITH CHECK (auth.uid() IS NOT NULL AND auth.uid() = user_id);

CREATE POLICY "source_revisions_select_own"
ON public.source_revisions
FOR SELECT
TO authenticated
USING (auth.uid() IS NOT NULL AND auth.uid() = user_id);

CREATE POLICY "source_revisions_insert_own"
ON public.source_revisions
FOR INSERT
TO authenticated
WITH CHECK (auth.uid() IS NOT NULL AND auth.uid() = user_id);

CREATE POLICY "source_revisions_update_own"
ON public.source_revisions
FOR UPDATE
TO authenticated
USING (auth.uid() IS NOT NULL AND auth.uid() = user_id)
WITH CHECK (auth.uid() IS NOT NULL AND auth.uid() = user_id);

CREATE POLICY "source_intake_requests_select_own"
ON public.source_intake_requests
FOR SELECT
TO authenticated
USING (auth.uid() IS NOT NULL AND auth.uid() = user_id);

CREATE POLICY "source_intake_requests_insert_own"
ON public.source_intake_requests
FOR INSERT
TO authenticated
WITH CHECK (auth.uid() IS NOT NULL AND auth.uid() = user_id);

CREATE POLICY "source_intake_requests_delete_own"
ON public.source_intake_requests
FOR DELETE
TO authenticated
USING (auth.uid() IS NOT NULL AND auth.uid() = user_id);

CREATE POLICY "loop_sessions_select_own"
ON public.loop_sessions
FOR SELECT
TO authenticated
USING (auth.uid() IS NOT NULL AND auth.uid() = user_id);

CREATE POLICY "loop_sessions_insert_own"
ON public.loop_sessions
FOR INSERT
TO authenticated
WITH CHECK (auth.uid() IS NOT NULL AND auth.uid() = user_id);

CREATE POLICY "loop_sessions_update_own"
ON public.loop_sessions
FOR UPDATE
TO authenticated
USING (auth.uid() IS NOT NULL AND auth.uid() = user_id)
WITH CHECK (auth.uid() IS NOT NULL AND auth.uid() = user_id);

CREATE POLICY "loop_sessions_delete_own"
ON public.loop_sessions
FOR DELETE
TO authenticated
USING (auth.uid() IS NOT NULL AND auth.uid() = user_id);

CREATE OR REPLACE FUNCTION public.protect_source_revision_update()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
    IF OLD.erased_at IS NOT NULL
       OR NEW.revision_id IS DISTINCT FROM OLD.revision_id
       OR NEW.source_id IS DISTINCT FROM OLD.source_id
       OR NEW.user_id IS DISTINCT FROM OLD.user_id
       OR NEW.revision_number IS DISTINCT FROM OLD.revision_number
       OR NEW.normalization_version IS DISTINCT FROM OLD.normalization_version
       OR NEW.extraction_version IS DISTINCT FROM OLD.extraction_version
       OR NEW.parser_version IS DISTINCT FROM OLD.parser_version
       OR NEW.source_kind IS DISTINCT FROM OLD.source_kind
       OR NEW.provenance IS DISTINCT FROM OLD.provenance
       OR NEW.created_at IS DISTINCT FROM OLD.created_at
       OR NEW.normalized_text IS NOT NULL
       OR NEW.checksum_sha256 IS NOT NULL
       OR NEW.content_bytes IS NOT NULL
       OR NEW.erased_at IS NULL THEN
        RAISE EXCEPTION 'source revision is immutable';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS source_revisions_immutable
ON public.source_revisions;
CREATE TRIGGER source_revisions_immutable
BEFORE UPDATE ON public.source_revisions
FOR EACH ROW
EXECUTE FUNCTION public.protect_source_revision_update();

CREATE OR REPLACE FUNCTION public.protect_loop_session_source_revision()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
    IF NEW.source_revision_id IS DISTINCT FROM OLD.source_revision_id THEN
        RAISE EXCEPTION 'session source revision is immutable';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS loop_sessions_source_revision_immutable
ON public.loop_sessions;
CREATE TRIGGER loop_sessions_source_revision_immutable
BEFORE UPDATE ON public.loop_sessions
FOR EACH ROW
EXECUTE FUNCTION public.protect_loop_session_source_revision();

CREATE OR REPLACE FUNCTION public.intake_source_revision(
    p_idempotency_key UUID,
    p_normalized_text TEXT,
    p_checksum_sha256 TEXT,
    p_normalization_version TEXT,
    p_extraction_version TEXT,
    p_parser_version TEXT,
    p_source_kind TEXT,
    p_provenance JSONB
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY INVOKER
VOLATILE
SET search_path = ''
AS $$
DECLARE
    owner_id UUID := auth.uid();
    prior public.source_intake_requests%ROWTYPE;
    revision public.source_revisions%ROWTYPE;
    created_source_id UUID;
    was_deduplicated BOOLEAN := FALSE;
    payload_hash TEXT;
BEGIN
    IF owner_id IS NULL THEN
        RAISE EXCEPTION 'authentication required' USING ERRCODE = '42501';
    END IF;
    IF p_checksum_sha256 !~ '^[0-9a-f]{64}$'
       OR p_normalized_text IS NULL
       OR p_normalized_text = ''
       OR octet_length(p_normalized_text) > 65536
       OR p_checksum_sha256 <> encode(sha256(convert_to(p_normalized_text, 'UTF8')), 'hex')
       OR coalesce(p_normalization_version, '') = ''
       OR coalesce(p_extraction_version, '') = ''
       OR coalesce(p_parser_version, '') = ''
       OR p_source_kind NOT IN ('paste', 'txt', 'md', 'pdf')
       OR jsonb_typeof(p_provenance) <> 'object'
       OR p_provenance <> jsonb_build_object(
            'intake_surface', 'promoted-alpha-file-intake',
            'input_method', CASE WHEN p_source_kind = 'paste' THEN 'paste' ELSE 'file' END
       ) THEN
        RAISE EXCEPTION 'invalid source intake payload' USING ERRCODE = '22023';
    END IF;

    payload_hash := encode(sha256(convert_to(jsonb_build_object(
        'normalizedText', p_normalized_text,
        'normalizationVersion', p_normalization_version,
        'extractionVersion', p_extraction_version,
        'parserVersion', p_parser_version,
        'sourceKind', p_source_kind,
        'provenance', p_provenance
    )::text, 'UTF8')), 'hex');

    PERFORM pg_advisory_xact_lock(
        hashtextextended(owner_id::text || ':' || p_idempotency_key::text, 0)
    );
    SELECT *
    INTO prior
    FROM public.source_intake_requests
    WHERE user_id = owner_id
      AND idempotency_key = p_idempotency_key;

    IF FOUND THEN
        IF prior.payload_hash <> payload_hash THEN
            RAISE EXCEPTION 'idempotency_key_reused' USING ERRCODE = 'PT409';
        END IF;
        RETURN jsonb_build_object(
            'sourceId', prior.source_id,
            'revisionId', prior.revision_id,
            'checksumSha256', prior.result_checksum_sha256,
            'normalizationVersion', prior.normalization_version,
            'extractionVersion', prior.extraction_version,
            'parserVersion', prior.parser_version,
            'sourceKind', prior.source_kind,
            'provenance', prior.provenance,
            'replayed', TRUE,
            'deduplicated', FALSE
        );
    END IF;

    PERFORM pg_advisory_xact_lock(
        hashtextextended(
            owner_id::text
            || ':' || p_checksum_sha256
            || ':' || p_normalization_version
            || ':' || p_extraction_version
            || ':' || p_parser_version
            || ':' || p_source_kind,
            0
        )
    );
    SELECT *
    INTO revision
    FROM public.source_revisions
    WHERE user_id = owner_id
      AND checksum_sha256 = p_checksum_sha256
      AND normalization_version = p_normalization_version
      AND extraction_version = p_extraction_version
      AND parser_version = p_parser_version
      AND source_kind = p_source_kind
      AND erased_at IS NULL;

    IF FOUND THEN
        was_deduplicated := TRUE;
    ELSE
        INSERT INTO public.sources (user_id)
        VALUES (owner_id)
        RETURNING source_id INTO created_source_id;

        INSERT INTO public.source_revisions (
            source_id,
            user_id,
            normalized_text,
            checksum_sha256,
            content_bytes,
            normalization_version,
            extraction_version,
            parser_version,
            source_kind,
            provenance
        )
        VALUES (
            created_source_id,
            owner_id,
            p_normalized_text,
            p_checksum_sha256,
            octet_length(p_normalized_text),
            p_normalization_version,
            p_extraction_version,
            p_parser_version,
            p_source_kind,
            p_provenance
        )
        RETURNING * INTO revision;
    END IF;

    INSERT INTO public.source_intake_requests (
        user_id,
        idempotency_key,
        payload_hash,
        source_id,
        revision_id,
        result_checksum_sha256,
        normalization_version,
        extraction_version,
        parser_version,
        source_kind,
        provenance
    )
    VALUES (
        owner_id,
        p_idempotency_key,
        payload_hash,
        revision.source_id,
        revision.revision_id,
        revision.checksum_sha256,
        revision.normalization_version,
        revision.extraction_version,
        revision.parser_version,
        revision.source_kind,
        revision.provenance
    );

    RETURN jsonb_build_object(
        'sourceId', revision.source_id,
        'revisionId', revision.revision_id,
        'checksumSha256', revision.checksum_sha256,
        'normalizationVersion', revision.normalization_version,
        'extractionVersion', revision.extraction_version,
        'parserVersion', revision.parser_version,
        'sourceKind', revision.source_kind,
        'provenance', revision.provenance,
        'replayed', FALSE,
        'deduplicated', was_deduplicated
    );
END;
$$;

CREATE OR REPLACE FUNCTION public.erase_source_revision(p_revision_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
    owner_id UUID := auth.uid();
    erased_id UUID;
BEGIN
    IF owner_id IS NULL THEN
        RETURN jsonb_build_object('erased', FALSE);
    END IF;
    UPDATE public.source_revisions
    SET normalized_text = NULL,
        checksum_sha256 = NULL,
        content_bytes = NULL,
        erased_at = now()
    WHERE revision_id = p_revision_id
      AND user_id = owner_id
      AND erased_at IS NULL
    RETURNING revision_id INTO erased_id;

    DELETE FROM public.source_intake_requests
    WHERE user_id = owner_id
      AND revision_id = p_revision_id;

    RETURN jsonb_build_object('erased', erased_id IS NOT NULL);
END;
$$;

REVOKE ALL ON FUNCTION public.protect_source_revision_update()
FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.protect_loop_session_source_revision()
FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.intake_source_revision(
    UUID, TEXT, TEXT, TEXT, TEXT, TEXT, TEXT, JSONB
) FROM PUBLIC, anon;
REVOKE ALL ON FUNCTION public.erase_source_revision(UUID)
FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.intake_source_revision(
    UUID, TEXT, TEXT, TEXT, TEXT, TEXT, TEXT, JSONB
) TO authenticated;
GRANT EXECUTE ON FUNCTION public.erase_source_revision(UUID)
TO authenticated;

CREATE INDEX IF NOT EXISTS loop_sessions_user_id_idx
ON public.loop_sessions (user_id);

CREATE INDEX IF NOT EXISTS loop_sessions_expires_at_idx
ON public.loop_sessions (expires_at);

CREATE INDEX IF NOT EXISTS loop_sessions_user_updated_at_idx
ON public.loop_sessions (user_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS loop_sessions_user_source_revision_idx
ON public.loop_sessions (user_id, source_revision_id)
WHERE source_revision_id IS NOT NULL;

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
