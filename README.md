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

## Dependency Updates & Deployment

This repo keeps Python dependency management intentionally simple:

- `requirements.txt` is the Vercel runtime install surface.
- `requirements-dev.txt` is local-only test and tooling surface.
- Keep both files flat: one pinned package per line, no `-r` includes, no hash blocks.

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
