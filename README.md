# socratink-app

socratink-app is an MVP-stage learning product deployed on Vercel serverless.

The tracked repo contains the hosted product surface:

- the hosted app: FastAPI backend plus a vanilla JS frontend in `public/`
- production Gemini prompt assets in `app_prompts/`

The product doctrine is stable even while implementation is still moving:

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

## Local Run

```bash
bash scripts/bootstrap-python.sh
bash scripts/dev.sh
```

Then open [http://localhost:8000](http://localhost:8000).

`scripts/dev.sh` binds Uvicorn to `127.0.0.1` by default (loopback-only).
For on-device mobile testing (see `docs/qa/antigravity-mobile-qa-prompt.md`),
override with `HOST=0.0.0.0 bash scripts/dev.sh` so the dev server is also
reachable at `http://<your-LAN-IP>:8000`. The localhost auto-guest bypass stays
loopback-only: LAN/on-device requests use the normal login path unless routed
through a loopback tunnel.

`scripts/dev.sh` refuses to run without `.venv/` (to avoid accidentally using
global/pyenv site-packages). It runs `scripts/check-local-auth.py` before
starting Uvicorn to catch missing `.env` / `.env.local` auth configuration.

## Testing

End-to-End browser smoke tests are powered by Playwright and Pytest. To run them, make sure the development server is running in the background, or point the tests to the live production server.

```bash
# Test against local dev server (http://localhost:8000)
bash scripts/qa-smoke.sh local

# Test against the live production server (https://app.socratink.ai)
bash scripts/qa-smoke.sh live
```

### Diff coverage gate

Changed lines on this branch are required to be 100% covered across both the
Python backend and the JavaScript frontend. The gate runs in CI and locally:

```bash
bash scripts/test-cov.sh        # collect backend Python coverage with pytest-cov
bash scripts/check-coverage.sh  # collect full-stack coverage and enforce 100% diff coverage
```

`scripts/check-coverage.sh` calls the backend Python leg, generates frontend V8
coverage via `scripts/generate-frontend-coverage.js`, checks changed versioned
frontend assets with `scripts/check_frontend_cache_pins.py`, then runs
diff-cover against `COMPARE_BRANCH` when set or `origin/main` / `main` locally.
The default browser target is `http://localhost:8000`; for any
`http://localhost:<port>` or `http://127.0.0.1:<port>` target, the script
reuses a healthy app if one is already running, otherwise starts loopback
uvicorn on that port and writes its log to `.qa-runs/check-coverage-uvicorn.log`.
Set `SOCRATINK_BASE_URL` to a non-local target when the app should be provided
externally. The cache-pin check fails when a changed versioned frontend asset
keeps a stale parent `?v=` reference. The frontend leg requires Node (run
`npm install` once to fetch `monocart-coverage-reports`). The Python leg adds
`pytest-cov` and `diff-cover` from `requirements-dev.txt`.

### Type-check and PR preflight

The type-check baseline is two-tool: **pyrefly is the primary gate**, **mypy is
the cross-check**. Both must be green and both run in `scripts/doctor.sh` and
in CI. Run both from the repo root before pushing:

```bash
.venv/bin/pyrefly check   # honors project-includes in pyrefly.toml — do NOT pass `.`
mypy .                    # honors mypy.ini exclude list (.venv/, tests/e2e/, public/, scripts/, …)
```

- `pyrefly.toml` (Python 3.13, `preset = "legacy"`, `check-unannotated-defs = true`)
  uses positive `project-includes` to mirror mypy's effective scope. Passing
  `pyrefly check .` would override that scope and pull in `tests/` and `api/`,
  both of which are intentionally excluded.
- The pyrefly version is pinned in `scripts/doctor.sh` (`PYREFLY_VERSION`),
  not in `requirements-dev.txt`, so the gate auto-bootstraps the exact
  version it was authored against.
- `mypy.ini` (Python 3.13, `warn_unreachable`, `strict_optional`,
  `check_untyped_defs`, `warn_return_any`) stays the cross-check.

`.github/workflows/preflight.yml` runs two CI jobs on every `pull_request` and
on pushes to `main`/`dev`: the preflight job invokes `bash scripts/doctor.sh`
(which runs both checkers) plus `pytest -q --ignore=tests/e2e`, and the
coverage job installs Node/Chromium, starts a loopback app with
`SOCRATINK_E2E_LOCAL_GUEST=1`, selects `COMPARE_BRANCH`, and runs
`scripts/check-coverage.sh`. It is the public PR-time signal contributors will
see and is intentionally narrower than the local `scripts/preflight-deploy.sh`,
which additionally runs `vercel build` against real Vercel credentials and
stays local-only.

## Dependency Updates & Deployment

This repo keeps dependency management intentionally simple:

- `requirements.txt` is the Vercel runtime install surface.
- `requirements-dev.txt` is local-only test and tooling surface (includes
  `pytest-cov` and `diff-cover` for the coverage gate).
- `package.json` / `package-lock.json` carry the local-only Node tooling for
  the frontend coverage gate (`monocart-coverage-reports`); none of it ships
  to Vercel.
- Keep the Python files flat: one pinned package per line, no `-r` includes,
  no hash blocks.

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
