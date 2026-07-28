# SQL applied in the Supabase project (not auto-migrated by the app).

- `feedback.sql` — public feedback capture
- `learner_state.sql` — auth-bound concepts + training continuity blob
- `loop_sessions.sql` — RLS-scoped SEDA journals with expiry, bounded payloads,
  a bounded recent turn-receipt history, optimistic concurrency, and
  owner-scoped immutable SourceRevision rows

Hosted `/api/session` requires `loop_sessions.sql` to be applied. The trusted
HTTPS loop service uses `SUPABASE_URL` plus `SUPABASE_PUBLISHABLE_KEY`; FastAPI
forwards the authenticated user access token only to that configured origin.
Do not configure a Supabase service-role or secret key for this path.

Authenticated source intake stores normalized extracted UTF-8 text only; it
does not retain raw files or filenames. Session metadata and append-only events
keep only opaque source/revision IDs plus pipeline version and source-kind
fields. `bash scripts/verify-source-rls.sh` applies the real schema to an
isolated `postgres:16-alpine` container and proves RLS, concurrent idempotency,
dedupe, immutability, exact hashing, reference ownership, and erasure.

Controlled erasure applies only to new authenticated SourceRevision writes
created after this boundary. It clears the revision content and fingerprints
and deletes its intake-request fingerprint without rewriting the append-only
session journal or learner attempts. Legacy `source_submitted.text` events and
excluded local preview rows remain read-only, are not migrated, and are not
covered by a universal deletion claim.

Each session keeps at most 16 recent turn receipts under a 2 MiB database
ceiling. This lets a delayed network retry replay its original response after a
newer turn without letting receipt history grow without bound. Metadata-only
updates preserve the receipts.

Schedule `public.purge_expired_loop_sessions()` from a trusted Supabase database
schedule. Application roles cannot execute it. The expiry index keeps the
cleanup bounded, but rows are not removed until the schedule exists.
