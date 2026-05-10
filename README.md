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
reachable at `http://<your-LAN-IP>:8000`.

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
bash scripts/test-cov.sh        # collect Python (pytest-cov) + frontend (monocart) coverage
bash scripts/check-coverage.sh  # enforce 100% diff coverage vs. main using diff-cover
```

The frontend leg (`scripts/generate-frontend-coverage.js`) requires Node (run
`npm install` once to fetch `monocart-coverage-reports`). The Python leg adds
`pytest-cov` and `diff-cover` from `requirements-dev.txt`.

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
