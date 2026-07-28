#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
schema_fixture="$repo_root/db/loop_sessions.sql"
container="socratink-source-rls-$$-$(date +%s)"
scratch="$(mktemp -d "${TMPDIR:-/tmp}/socratink-source-rls.XXXXXX")"

cleanup() {
  docker rm -f "$container" >/dev/null 2>&1 || true
  rm -rf "$scratch"
}
trap cleanup EXIT INT TERM

test -f "$schema_fixture"
docker run \
  --detach \
  --name "$container" \
  --pull=never \
  --env POSTGRES_PASSWORD=source-proof \
  postgres:16-alpine >/dev/null

for _ in $(seq 1 60); do
  if docker exec "$container" pg_isready -U postgres -d postgres >/dev/null 2>&1; then
    break
  fi
  sleep 0.25
done
docker exec "$container" pg_isready -U postgres -d postgres >/dev/null

docker exec -i "$container" psql -U postgres -d postgres -v ON_ERROR_STOP=1 <<'SQL'
CREATE ROLE anon NOLOGIN;
CREATE ROLE authenticated NOLOGIN;
CREATE SCHEMA auth;
CREATE TABLE auth.users (id UUID PRIMARY KEY);
CREATE FUNCTION auth.uid()
RETURNS UUID
LANGUAGE sql
STABLE
AS $$
    SELECT nullif(current_setting('request.jwt.claim.sub', TRUE), '')::UUID
$$;
GRANT USAGE ON SCHEMA auth TO anon, authenticated;
GRANT SELECT ON auth.users TO authenticated;
GRANT EXECUTE ON FUNCTION auth.uid() TO anon, authenticated;
SQL

docker cp "$schema_fixture" "$container:/tmp/loop_sessions.sql" >/dev/null
docker exec -i "$container" psql \
  -U postgres \
  -d postgres \
  -v ON_ERROR_STOP=1 \
  -f /tmp/loop_sessions.sql >/dev/null

docker exec -i "$container" psql -U postgres -d postgres -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO auth.users (id) VALUES
    ('10000000-0000-4000-8000-000000000001'),
    ('20000000-0000-4000-8000-000000000002');

DO $$
DECLARE
    intake_is_definer BOOLEAN;
    intake_config TEXT[];
    anon_can_execute BOOLEAN;
BEGIN
    SELECT prosecdef, proconfig
    INTO intake_is_definer, intake_config
    FROM pg_proc
    WHERE oid = 'public.intake_source_revision(uuid,text,text,text,text,text,text,jsonb)'::regprocedure;
    IF intake_is_definer OR intake_config IS DISTINCT FROM ARRAY['search_path=""']::TEXT[] THEN
        RAISE EXCEPTION 'intake must be SECURITY INVOKER with an empty search_path';
    END IF;
    SELECT has_function_privilege(
        'anon',
        'public.intake_source_revision(uuid,text,text,text,text,text,text,jsonb)',
        'EXECUTE'
    ) INTO anon_can_execute;
    IF anon_can_execute THEN
        RAISE EXCEPTION 'anon must not execute source intake';
    END IF;
END;
$$;

SET ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '10000000-0000-4000-8000-000000000001', FALSE);

SELECT public.intake_source_revision(
    'a0000000-0000-4000-8000-000000000001',
    E'Alpha β\nline two SOURCE_TEXT_CANARY',
    encode(sha256(convert_to(E'Alpha β\nline two SOURCE_TEXT_CANARY', 'UTF8')), 'hex'),
    'source-text-v1',
    'browser-paste-v1',
    'plain-text-v1',
    'paste',
    '{"input_method":"paste","intake_surface":"promoted-alpha-file-intake"}'::jsonb
) AS intake_result \gset

SELECT :'intake_result'::jsonb ->> 'sourceId' AS a_source_id,
       :'intake_result'::jsonb ->> 'revisionId' AS a_revision_id,
       :'intake_result'::jsonb ->> 'checksumSha256' AS a_checksum \gset
SELECT set_config('proof.a_source_id', :'a_source_id', FALSE),
       set_config('proof.a_revision_id', :'a_revision_id', FALSE),
       set_config('proof.a_checksum', :'a_checksum', FALSE);

DO $$
DECLARE
    persisted_text TEXT;
    persisted_checksum TEXT;
BEGIN
    SELECT normalized_text, checksum_sha256
    INTO persisted_text, persisted_checksum
    FROM public.source_revisions
    WHERE revision_id = current_setting('proof.a_revision_id')::UUID;
    IF convert_to(persisted_text, 'UTF8') IS DISTINCT FROM convert_to(E'Alpha β\nline two SOURCE_TEXT_CANARY', 'UTF8') THEN
        RAISE EXCEPTION 'normalized UTF-8 text did not round-trip byte-for-byte';
    END IF;
    IF persisted_checksum <> encode(sha256(convert_to(persisted_text, 'UTF8')), 'hex') THEN
        RAISE EXCEPTION 'persisted checksum mismatch';
    END IF;
END;
$$;

SELECT public.intake_source_revision(
    'a0000000-0000-4000-8000-000000000001',
    E'Alpha β\nline two SOURCE_TEXT_CANARY',
    :'a_checksum',
    'source-text-v1',
    'browser-paste-v1',
    'plain-text-v1',
    'paste',
    '{"input_method":"paste","intake_surface":"promoted-alpha-file-intake"}'::jsonb
) AS retry_result \gset
SELECT set_config('proof.retry_result', :'retry_result', FALSE);

DO $$
BEGIN
    IF (current_setting('proof.retry_result')::jsonb ->> 'revisionId')
          <> current_setting('proof.a_revision_id')
       OR (current_setting('proof.retry_result')::jsonb ->> 'replayed')::BOOLEAN IS NOT TRUE THEN
        RAISE EXCEPTION 'same idempotency key and body did not replay';
    END IF;
    BEGIN
        PERFORM public.intake_source_revision(
            'a0000000-0000-4000-8000-000000000001',
            'different body',
            encode(sha256(convert_to('different body', 'UTF8')), 'hex'),
            'source-text-v1',
            'browser-paste-v1',
            'plain-text-v1',
            'paste',
            '{"input_method":"paste","intake_surface":"promoted-alpha-file-intake"}'::jsonb
        );
        RAISE EXCEPTION 'idempotency mismatch unexpectedly succeeded';
    EXCEPTION WHEN SQLSTATE 'PT409' THEN
        IF SQLERRM <> 'idempotency_key_reused' THEN
            RAISE;
        END IF;
    END;
    BEGIN
        INSERT INTO public.sources (user_id)
        VALUES ('20000000-0000-4000-8000-000000000002');
        RAISE EXCEPTION 'forged owner insert unexpectedly succeeded';
    EXCEPTION WHEN insufficient_privilege THEN
        NULL;
    END;
    BEGIN
        PERFORM public.intake_source_revision(
            'a0000000-0000-4000-8000-000000000003',
            'filename rejection proof',
            encode(sha256(convert_to('filename rejection proof', 'UTF8')), 'hex'),
            'source-text-v1',
            'pdfjs-3.11.174',
            'pdfjs-3.11.174',
            'pdf',
            '{"input_method":"file","intake_surface":"promoted-alpha-file-intake","filename":"CLIENT_SECRET_PROJECT.pdf"}'::jsonb
        );
        RAISE EXCEPTION 'filename provenance unexpectedly persisted';
    EXCEPTION WHEN SQLSTATE '22023' THEN
        NULL;
    END;
END;
$$;

SELECT public.intake_source_revision(
    'a0000000-0000-4000-8000-000000000002',
    E'Alpha β\nline two SOURCE_TEXT_CANARY',
    :'a_checksum',
    'source-text-v1',
    'browser-paste-v1',
    'plain-text-v1',
    'paste',
    '{"input_method":"paste","intake_surface":"promoted-alpha-file-intake"}'::jsonb
) AS dedupe_result \gset
SELECT set_config('proof.dedupe_result', :'dedupe_result', FALSE);

DO $$
BEGIN
    IF (current_setting('proof.dedupe_result')::jsonb ->> 'revisionId')
          <> current_setting('proof.a_revision_id')
       OR (current_setting('proof.dedupe_result')::jsonb ->> 'deduplicated')::BOOLEAN IS NOT TRUE THEN
        RAISE EXCEPTION 'owner-scoped checksum dedupe failed';
    END IF;
END;
$$;

INSERT INTO public.source_revisions (
    source_id,
    revision_number,
    normalized_text,
    checksum_sha256,
    content_bytes,
    normalization_version,
    extraction_version,
    parser_version,
    source_kind,
    provenance
) VALUES (
    :'a_source_id',
    2,
    'corrected source revision',
    encode(sha256(convert_to('corrected source revision', 'UTF8')), 'hex'),
    octet_length('corrected source revision'),
    'source-text-v1',
    'browser-paste-v1',
    'plain-text-v1',
    'paste',
    '{"input_method":"paste","intake_surface":"promoted-alpha-file-intake"}'::jsonb
);

INSERT INTO public.loop_sessions (
    session_id,
    source_revision_id,
    metadata,
    events,
    version,
    turn_receipts
) VALUES (
    'a1000000-0000-4000-8000-000000000001',
    :'a_revision_id',
    jsonb_build_object(
        'source_revision',
        jsonb_build_object(
            'source_id', :'a_source_id',
            'revision_id', :'a_revision_id',
            'normalization_version', 'source-text-v1',
            'extraction_version', 'browser-paste-v1',
            'parser_version', 'plain-text-v1',
            'source_kind', 'paste'
        )
    ),
    jsonb_build_array(
        jsonb_build_object(
            'type', 'source_submitted',
            'source_revision', jsonb_build_object(
                'source_id', :'a_source_id',
                'revision_id', :'a_revision_id',
                'normalization_version', 'source-text-v1',
                'extraction_version', 'browser-paste-v1',
                'parser_version', 'plain-text-v1',
                'source_kind', 'paste'
            )
        ),
        '{"type":"initial_reconstruction_submitted","text":"learner evidence","at":"2026-07-28T00:00:00Z","phase":"initial_reconstruction"}'::jsonb
    ),
    2,
    '[{"request_id":"a2000000-0000-4000-8000-000000000001","request_hash":"opaque","response":{"saved":true}}]'::jsonb
);

SELECT metadata::TEXT AS metadata_before,
       events::TEXT AS events_before,
       turn_receipts::TEXT AS receipts_before,
       version AS version_before
FROM public.loop_sessions
WHERE session_id = 'a1000000-0000-4000-8000-000000000001' \gset
SELECT set_config('proof.metadata_before', :'metadata_before', FALSE),
       set_config('proof.events_before', :'events_before', FALSE),
       set_config('proof.receipts_before', :'receipts_before', FALSE),
       set_config('proof.version_before', :'version_before', FALSE);

SELECT set_config('request.jwt.claim.sub', '20000000-0000-4000-8000-000000000002', FALSE);
SELECT public.intake_source_revision(
    'b0000000-0000-4000-8000-000000000001',
    E'Alpha β\nline two SOURCE_TEXT_CANARY',
    :'a_checksum',
    'source-text-v1',
    'browser-paste-v1',
    'plain-text-v1',
    'paste',
    '{"input_method":"paste","intake_surface":"promoted-alpha-file-intake"}'::jsonb
) AS b_result \gset
SELECT set_config('proof.b_result', :'b_result', FALSE);

DO $$
DECLARE
    visible_a INTEGER;
BEGIN
    IF (current_setting('proof.b_result')::jsonb ->> 'revisionId')
          = current_setting('proof.a_revision_id')
       OR (current_setting('proof.b_result')::jsonb ->> 'sourceId')
          = current_setting('proof.a_source_id') THEN
        RAISE EXCEPTION 'cross-tenant dedupe leaked owner identity';
    END IF;
    SELECT count(*) INTO visible_a
    FROM public.source_revisions
    WHERE revision_id = current_setting('proof.a_revision_id')::UUID;
    IF visible_a <> 0 THEN
        RAISE EXCEPTION 'user B can read user A revision';
    END IF;
    BEGIN
        INSERT INTO public.loop_sessions (session_id, source_revision_id)
        VALUES (
            'b1000000-0000-4000-8000-000000000001',
            current_setting('proof.a_revision_id')::UUID
        );
        RAISE EXCEPTION 'cross-owner session reference unexpectedly succeeded';
    EXCEPTION WHEN foreign_key_violation THEN
        NULL;
    END;
END;
$$;

SELECT set_config('request.jwt.claim.sub', '10000000-0000-4000-8000-000000000001', FALSE);
DO $$
BEGIN
    BEGIN
        UPDATE public.source_revisions
        SET normalized_text = normalized_text
        WHERE revision_id = current_setting('proof.a_revision_id')::UUID;
        RAISE EXCEPTION 'immutable revision update unexpectedly succeeded';
    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM <> 'source revision is immutable' THEN
            RAISE;
        END IF;
    END;
END;
$$;

SELECT public.erase_source_revision(:'a_revision_id') AS erase_result \gset
SELECT set_config('proof.erase_result', :'erase_result', FALSE);
DO $$
DECLARE
    owner_id UUID := '10000000-0000-4000-8000-000000000001';
    revision_count INTEGER;
    request_count INTEGER;
    remaining_text TEXT;
    remaining_checksum TEXT;
    remaining_bytes BIGINT;
    session_row public.loop_sessions%ROWTYPE;
BEGIN
    IF (current_setting('proof.erase_result')::jsonb ->> 'erased')::BOOLEAN IS NOT TRUE THEN
        RAISE EXCEPTION 'controlled erasure failed';
    END IF;
    SELECT count(*), max(normalized_text), max(checksum_sha256), max(content_bytes)
    INTO revision_count, remaining_text, remaining_checksum, remaining_bytes
    FROM public.source_revisions
    WHERE revision_id = current_setting('proof.a_revision_id')::UUID;
    IF revision_count <> 1
       OR remaining_text IS NOT NULL
       OR remaining_checksum IS NOT NULL
       OR remaining_bytes IS NOT NULL THEN
        RAISE EXCEPTION 'erased revision retained content or fingerprint';
    END IF;
    SELECT count(*) INTO request_count
    FROM public.source_intake_requests
    WHERE revision_id = current_setting('proof.a_revision_id')::UUID;
    IF request_count <> 0 THEN
        RAISE EXCEPTION 'erased revision retained intake fingerprint';
    END IF;
    SELECT * INTO session_row
    FROM public.loop_sessions
    WHERE session_id = 'a1000000-0000-4000-8000-000000000001';
    IF session_row.metadata::TEXT <> current_setting('proof.metadata_before')
       OR session_row.events::TEXT <> current_setting('proof.events_before')
       OR session_row.turn_receipts::TEXT <> current_setting('proof.receipts_before')
       OR session_row.version <> current_setting('proof.version_before')::BIGINT THEN
        RAISE EXCEPTION 'controlled erasure rewrote append-only session state';
    END IF;
    IF session_row.source_revision_id <> current_setting('proof.a_revision_id')::UUID
       OR session_row.events @> '[{"type":"initial_reconstruction_submitted","text":"learner evidence"}]'::jsonb IS NOT TRUE THEN
        RAISE EXCEPTION 'controlled erasure did not preserve source-unavailable reference and learner evidence';
    END IF;
    IF session_row.metadata::TEXT ~* 'checksum|fingerprint|SOURCE_TEXT_CANARY|CLIENT_SECRET_PROJECT'
       OR session_row.events::TEXT ~* 'checksum|fingerprint|SOURCE_TEXT_CANARY|CLIENT_SECRET_PROJECT'
       OR session_row.turn_receipts::TEXT ~* 'checksum|fingerprint|SOURCE_TEXT_CANARY|CLIENT_SECRET_PROJECT'
       OR EXISTS (
            SELECT 1
            FROM public.source_revisions
            WHERE user_id = owner_id
              AND (
                  coalesce(normalized_text, '') LIKE '%SOURCE_TEXT_CANARY%'
                  OR provenance::TEXT LIKE '%CLIENT_SECRET_PROJECT%'
              )
       )
       OR EXISTS (
            SELECT 1
            FROM public.source_intake_requests
            WHERE user_id = owner_id
              AND provenance::TEXT LIKE '%CLIENT_SECRET_PROJECT%'
       ) THEN
        RAISE EXCEPTION 'session state retained a content fingerprint';
    END IF;
END;
$$;

RESET ROLE;
SET ROLE anon;
DO $$
BEGIN
    BEGIN
        PERFORM public.intake_source_revision(
            'f0000000-0000-4000-8000-000000000001',
            'anon',
            encode(sha256(convert_to('anon', 'UTF8')), 'hex'),
            'source-text-v1',
            'browser-paste-v1',
            'plain-text-v1',
            'paste',
            '{}'::jsonb
        );
        RAISE EXCEPTION 'anon intake unexpectedly succeeded';
    EXCEPTION WHEN insufficient_privilege THEN
        NULL;
    END;
END;
$$;
RESET ROLE;
SQL

run_intake() {
  local key="$1"
  local text="$2"
  local output="$3"
  docker exec -i "$container" psql -U postgres -d postgres -v ON_ERROR_STOP=1 >"$output" 2>&1 <<SQL
\set VERBOSITY verbose
SET ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '10000000-0000-4000-8000-000000000001', FALSE);
SELECT public.intake_source_revision(
    '$key',
    '$text',
    encode(sha256(convert_to('$text', 'UTF8')), 'hex'),
    'source-text-v1',
    'browser-paste-v1',
    'plain-text-v1',
    'paste',
    '{"input_method":"paste","intake_surface":"promoted-alpha-file-intake"}'::jsonb
);
SQL
}

run_intake "c0000000-0000-4000-8000-000000000001" \
  "concurrent payload alpha" "$scratch/key-alpha.out" &
alpha_pid=$!
run_intake "c0000000-0000-4000-8000-000000000001" \
  "concurrent payload beta" "$scratch/key-beta.out" &
beta_pid=$!

set +e
wait "$alpha_pid"
alpha_status=$?
wait "$beta_pid"
beta_status=$?
set -e

if ! { { test "$alpha_status" -eq 0 && test "$beta_status" -ne 0; } \
  || { test "$alpha_status" -ne 0 && test "$beta_status" -eq 0; }; }; then
  cat "$scratch/key-alpha.out" "$scratch/key-beta.out"
  echo "concurrent idempotency did not produce exactly one winner" >&2
  exit 1
fi
if ! grep -q "PT409.*idempotency_key_reused" "$scratch/key-alpha.out" "$scratch/key-beta.out"; then
  cat "$scratch/key-alpha.out" "$scratch/key-beta.out"
  echo "concurrent idempotency mismatch did not return PT409" >&2
  exit 1
fi
if grep -Eqi "duplicate key|unique constraint" "$scratch/key-alpha.out" "$scratch/key-beta.out"; then
  cat "$scratch/key-alpha.out" "$scratch/key-beta.out"
  echo "raw unique violation leaked from concurrent idempotency" >&2
  exit 1
fi

run_intake "d0000000-0000-4000-8000-000000000001" \
  "concurrent checksum payload" "$scratch/checksum-one.out" &
one_pid=$!
run_intake "d0000000-0000-4000-8000-000000000002" \
  "concurrent checksum payload" "$scratch/checksum-two.out" &
two_pid=$!
wait "$one_pid"
wait "$two_pid"

docker exec -i "$container" psql -U postgres -d postgres -v ON_ERROR_STOP=1 <<'SQL'
SET ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '10000000-0000-4000-8000-000000000001', FALSE);
DO $$
DECLARE
    matching_revisions INTEGER;
    matching_requests INTEGER;
BEGIN
    SELECT count(*) INTO matching_revisions
    FROM public.source_revisions
    WHERE checksum_sha256 = encode(
        sha256(convert_to('concurrent checksum payload', 'UTF8')),
        'hex'
    );
    SELECT count(*) INTO matching_requests
    FROM public.source_intake_requests
    WHERE idempotency_key IN (
        'd0000000-0000-4000-8000-000000000001',
        'd0000000-0000-4000-8000-000000000002'
    );
    IF matching_revisions <> 1 OR matching_requests <> 2 THEN
        RAISE EXCEPTION 'owner-checksum serialization did not deduplicate concurrent intake';
    END IF;
END;
$$;
SQL

echo "source RLS verification passed"
