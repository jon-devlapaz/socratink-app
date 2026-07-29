# socratink-app

socratink-app is an MVP-stage learning product deployed on Vercel serverless.

The tracked repo contains the hosted product surface:

- the hosted app: FastAPI backend plus a vanilla JS frontend in `public/`
- production Gemini prompt assets in `app_prompts/`
- the app-local SEDA loop runtime used by learner concept sessions

The product doctrine is stable even while implementation is still moving.
Canonical north star: [`docs/product/north-star.md`](docs/product/north-star.md).

- generation before recognition
- the graph tells the truth
- AI should remove prep friction and increase truthful retrieval reps
- local success does not validate hosted behavior

## Repo Shape

- `main.py` and `api/`
  FastAPI app and Vercel entrypoint.
- `ai_service.py`
  Model-facing extraction and drill logic.
- `app_prompts/`
  Production prompt assets bundled with the Vercel serverless function.
- `public/`
  Hosted frontend.
- `lib/loop-public/`
  Standalone `/loop` terminal UI. This is debug/backcompat; the normal learner
  product flow enters SEDA through the app shell and `/api/session`.
- `lib/seda/`
  App-local SEDA state machine, handlers, session rehydration, and evidence
  record projection.
- `lib/loop-server/`
  HTTP wrapper around the SEDA runtime. `loop_backend_proxy.py` starts this
  vendored runtime locally with a file session store. On Vercel, FastAPI
  proxies learner sessions to a configured HTTPS loop service that can run
  both Node and the Python bridge. The service uses the authenticated user's
  Supabase token and `db/loop_sessions.sql`; it never falls back to serverless
  temporary storage.
- `bridge.py`, `bridge_lib/`, `vendor/python/`
  Python bridge seam used by the loop runtime for model calls and fake-loop
  fixtures. These are app-local vendored files; they must not depend on a
  sibling `socratink-tui-agent` checkout.
- `learning_cases/` and `pedagogical_agents/`
  Promoted SEDA regression cases and agent contracts used by the runtime and
  lab tooling.

## Local Run

```bash
bash scripts/bootstrap-python.sh
bash scripts/dev.sh
```

Then open [http://localhost:8000](http://localhost:8000).

`scripts/dev.sh` binds Uvicorn to `127.0.0.1` by default (loopback-only).
For on-device mobile testing, override with `HOST=0.0.0.0 bash scripts/dev.sh`
so the dev server is also
reachable at `http://<your-LAN-IP>:8000`. The localhost auto-guest bypass stays
loopback-only: LAN/on-device requests use the normal login path unless routed
through a loopback tunnel.

`scripts/dev.sh` refuses to run without `.venv/` (to avoid accidentally using
global/pyenv site-packages). It runs `scripts/check-local-auth.py` before
starting Uvicorn to catch missing `.env` / `.env.local` auth configuration.

## Testing

Tests exercise application logic: API behavior, validation, routing,
persistence, state transitions, parsing, recovery, and pure JavaScript modules.
They do not assert DOM structure, selectors, copy, layout, or visual output.
`scripts/check_logic_only_tests.py` enforces this boundary through
`scripts/doctor.sh` and CI.

```bash
.venv/bin/pytest -q
```

### Diff coverage gate

Changed Python lines on this branch are required to be 100% covered. The gate
runs in CI and locally:

```bash
bash scripts/test-cov.sh        # collect application-logic coverage
bash scripts/check-coverage.sh  # enforce 100% Python diff coverage
```

`scripts/check-coverage.sh` collects pytest coverage and runs diff-cover against
`COMPARE_BRANCH` when set or `origin/main` / `main` locally. Pure JavaScript
logic remains covered by Node-driven pytest tests, but the repository does not
collect browser or DOM coverage. The Python coverage tools are `pytest-cov` and
`diff-cover` from `requirements-dev.txt`.

### Type-check and PR preflight

The type-check baseline is two-tool: **pyrefly is the primary gate**, **mypy is
the cross-check**. Both must be green and both run in `scripts/doctor.sh` and
in CI. Run both from the repo root before pushing:

```bash
.venv/bin/pyrefly check   # honors project-includes in pyrefly.toml — do NOT pass `.`
mypy .                    # honors mypy.ini exclude list (.venv/, public/, scripts/, …)
```

- `pyrefly.toml` (Python 3.14, `preset = "legacy"`, `check-unannotated-defs = true`)
  uses positive `project-includes` to mirror mypy's effective scope. Passing
  `pyrefly check .` would override that scope and pull in `tests/` and `api/`,
  both of which are intentionally excluded.
- The pyrefly version is pinned in `scripts/doctor.sh` (`PYREFLY_VERSION`),
  not in `requirements-dev.txt`, so the gate auto-bootstraps the exact
  version it was authored against.
- `mypy.ini` (Python 3.14, `warn_unreachable`, `strict_optional`,
  `check_untyped_defs`, `warn_return_any`) stays the cross-check.

`.github/workflows/preflight.yml` runs two CI jobs on every `pull_request` and
on pushes to `main`/`dev`: the preflight job invokes `bash scripts/doctor.sh`
(which runs both checkers) plus `pytest -q`. The coverage job selects
`COMPARE_BRANCH` and runs `scripts/check-coverage.sh`. It is the public PR-time
signal contributors will see and is intentionally narrower than the local
`scripts/preflight-deploy.sh`, which additionally runs `vercel build` against
real Vercel credentials and stays local-only.

## Dependency Updates & Deployment

This repo keeps dependency management intentionally simple:

- `requirements.txt` is the Vercel runtime install surface.
- `requirements-dev.txt` is local-only test and tooling surface (includes
  `pytest-cov` and `diff-cover` for the coverage gate).
- `package.json` / `package-lock.json` carry the repo-pinned Context Hub wrapper
  (`@aisuite/chub`); it does not ship to Vercel.
- Keep the Python files flat: one pinned package per line, no `-r` includes,
  no hash blocks.

### Hosted loop persistence

Before deploying hosted `/api/session`, deploy the vendored loop runtime to a
trusted HTTPS service that includes Node, Python and the bridge dependencies.
Set `LOOP_BACKEND_URL` and the same `SOCRATINK_LOOP_API_KEY` on the Vercel app
and loop service. Set `SOCRATINK_LOOP_SESSION_STORE=supabase` on the service.
Apply `db/loop_sessions.sql` to Supabase. The service also needs `SUPABASE_URL`
and `SUPABASE_PUBLISHABLE_KEY`.

FastAPI forwards the sealed user's access token only to that configured loop
origin. The loop service uses it for row-level security. It rejects insecure
origins, and Vercel fails closed when the URL or loop API key is missing. Do
not configure a Supabase service-role or secret key for this path.
The proxy rejects bodies over 64 KiB, performs blocking HTTP work off the
FastAPI event loop, disables automatic retries for learner POSTs, and bounds
upstream connect/read waits at 5/55 seconds.

Local development keeps the file store under
`SOCRATINK_LOOP_SESSION_STORE_DIR` (or the operating-system temporary default).
`SOCRATINK_LOOP_SESSION_TTL_SECONDS` may override the hosted 30-day session
expiry. Production and Vercel fail closed when durable storage is unavailable.
Schedule `public.purge_expired_loop_sessions()` once a day from a trusted
Supabase database schedule so expired rows do not accumulate.

This makes the loop event journal durable and account-scoped. Concepts and the
app-shell training record are still browser `localStorage`; full cross-device
learner continuity is not yet complete.

For identified learners, source intake persists one owner-scoped immutable
SourceRevision containing only normalized extracted text and fixed pipeline
provenance. The session journal stores an opaque revision reference, never
source text, checksums, filenames, or full provenance. Reopening resolves the
revision through the current user's RLS identity and fails with recoverable
`source_unavailable` before bridge work when it is missing or erased. Legacy
text-backed preview events remain read-only and are not migrated. Erasing a
SourceRevision removes the exact stored extracted source and intake fingerprints
only; persisted source-derived AI or session outputs may quote or paraphrase the
source and are not erased. This is not a universal deletion or full
data-subject-erasure claim; a professional-pilot blocker or later whole-session
deletion policy must decide that boundary.

For source-less Door starts, `/api/extract` now returns only a deterministic
graph-neutral shell. It does not query Learning Commons or generate a route;
the typed SEDA `sourceLessRoute` is the single authoritative route owner. This
removes a duplicate model call from the first-session latency and cost path.

### Loop service container

`Dockerfile.loop` packages the existing Node loop server with the repo-pinned
Python 3.14 bridge environment. `requirements-loop.txt` contains only the
bridge's direct Python dependencies and keeps their versions aligned with the
app runtime. The build context is allowlisted by
`Dockerfile.loop.dockerignore`, so local `.env` files and other workspace files
cannot enter the image.

```bash
docker build --file Dockerfile.loop --tag socratink-loop .
docker run --rm --publish 8787:8787 \
  --env SOCRATINK_LOOP_API_KEY \
  --env SUPABASE_URL \
  --env SUPABASE_PUBLISHABLE_KEY \
  --env GEMINI_API_KEY \
  socratink-loop
```

Inject those four variables at runtime through the hosting platform's secret
store; do not pass secret values as Docker build arguments. The image sets
`NODE_ENV=production`, `SOCRATINK_LOOP_SESSION_STORE=supabase`,
`HOST=0.0.0.0`, and a default `PORT=8787`. A platform-provided `PORT` overrides
that default. Configure the platform's process health probe to `GET /health`.
That endpoint proves the process is up; an authenticated create-session smoke
test is still required to prove Supabase access, row ownership, and the live
model path.

After deployment, set the app's `LOOP_BACKEND_URL` to the service's HTTPS
origin and give the app the same `SOCRATINK_LOOP_API_KEY`. The service itself
does not need `LOOP_BACKEND_URL`. Optional runtime tuning such as
`SOCRATINK_LOOP_SESSION_TTL_SECONDS`, `LLM_MODEL`, and the bridge controls
remain environment-only. The bridge runs non-blocking child processes with
bounded defaults: `SOCRATINK_BRIDGE_TIMEOUT_MS=45000`,
`SOCRATINK_BRIDGE_MAX_CONCURRENCY=4`, `SOCRATINK_BRIDGE_MAX_QUEUE=16`, and
`SOCRATINK_BRIDGE_MAX_OUTPUT_BYTES=1048576`. Tune concurrency only after a
hosted load test confirms CPU, memory, model quota, and database behavior.

### Deployment Validation

When preparing and validating a deployment, clearly distinguish between these stages:

1. **Local prerequisite validation:**
   ```bash
   bash scripts/doctor.sh
   ```
2. **Vercel build readiness:**
   This proves local Vercel build readiness, not hosted production correctness.
   ```bash
   bash scripts/preflight-deploy.sh
   ```
3. **Hosted production validation after deployment:**
   ```bash
   bash scripts/verify-deploy.sh HEAD
   ```

Doc-only changes to this section still require `bash scripts/doctor.sh`, because agent and deploy instructions are part of the repository's executable workflow.
