# socratink-app

socratink-app is an MVP-stage learning product deployed on Vercel serverless.

The repo contains two closely related layers:

- the hosted app: FastAPI backend plus a vanilla JS frontend in `public/`
- the socratink prompt and skill assets in `learnops/` that shape extraction and drill behavior

The product doctrine is stable even while implementation is still moving:

- generation before recognition
- the graph tells the truth
- AI should remove prep friction and increase truthful retrieval reps
- local success does not validate hosted behavior

## Start Here

- Read [AGENTS.md](./AGENTS.md) for repo constraints, agent routing, and workflow ownership.
- Read [docs/project/state.md](./docs/project/state.md) for current MVP priorities and target-user signals.
- Read [docs/theta/state.md](./docs/theta/state.md) when the task touches learning claims or product science.
- Read [docs/drill/graph-invariants.md](./docs/drill/graph-invariants.md) before changing drill or graph behavior.

## Repo Shape

- `main.py` and `api/`
  FastAPI app and Vercel entrypoint.
- `ai_service.py`
  Model-facing extraction and drill logic.
- `public/`
  Hosted frontend.
- `learnops/`
  Prompt assets and skill artifacts used by the product.
- `docs/`
  Product, drill, project, and agent workflow docs.

## Local Run

```bash
uvicorn main:app --reload
```

Then open [http://localhost:8000](http://localhost:8000).
