# SQL applied in the Supabase project (not auto-migrated by the app).

- `feedback.sql` — public feedback capture
- `learner_state.sql` — auth-bound concepts + training continuity blob
- `loop_sessions.sql` — RLS-scoped SEDA journals with expiry, bounded payloads,
  a bounded recent turn-receipt history, and optimistic concurrency

Hosted `/api/session` requires `loop_sessions.sql` to be applied. The trusted
HTTPS loop service uses `SUPABASE_URL` plus `SUPABASE_PUBLISHABLE_KEY`; FastAPI
forwards the authenticated user access token only to that configured origin.
Do not configure a Supabase service-role or secret key for this path.

Each session keeps at most 16 recent turn receipts under a 2 MiB database
ceiling. This lets a delayed network retry replay its original response after a
newer turn without letting receipt history grow without bound. Metadata-only
updates preserve the receipts.

Schedule `public.purge_expired_loop_sessions()` from a trusted Supabase database
schedule. Application roles cannot execute it. The expiry index keeps the
cleanup bounded, but rows are not removed until the schedule exists.
