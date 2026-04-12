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
uvicorn main:app --reload
```

Then open [http://localhost:8000](http://localhost:8000).
