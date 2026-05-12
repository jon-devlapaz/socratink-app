# admin/

The Admin Surface. A dev-and-local-only dashboard for the Tink TODO file,
gated by an email allowlist. Not part of the product surface — exists to
keep Jon's executive workflow inside the repo rather than in a separate
tool.

## Public surface

Import from `admin` directly.

| Export | What it is |
| :--- | :--- |
| `admin_router` | The FastAPI `APIRouter` for `/admin/todo` and its API endpoints. |
| `register_admin_router(app)` | Conditional registration. Called from `main.py`; **only attaches the router when local-dev + TODO file present.** Returns whether it registered. |

## Files

| File | Role |
| :--- | :--- |
| `router.py` | All `/admin/*` handlers. Owns the Admin Gate. |
| `static.py` | Inlined HTML+CSS+JS for the dashboard. Single `HTMLResponse`. |
| `todo_parser.py` | Pure-function parser + line-aware mutator for the Tink TODO markdown. |

## Footguns

- **Two-layer gating, both must pass.** (1) `register_admin_router` only
  attaches when `APP_BASE_URL` points at localhost/127.0.0.1 (or is unset)
  AND the Tink TODO file is readable. (2) Every handler then runs the
  Admin Gate (single-user email allowlist). Don't loosen either.
- **`register_admin_router(app)` must run BEFORE any catch-all
  StaticFiles mount.** FastAPI routes register in declaration order; a
  catch-all mounted first will swallow `/admin/*` requests before the
  admin router ever sees them. The function's docstring states this
  explicitly; preserve the call order in `main.py`.
- **Failure paths return 404, not 401/403.** This is deliberate — we
  avoid leaking the existence of the Admin Surface to non-admins. Any
  refactor that "improves" the error response by adding 403s is a
  regression.
- **`todo_parser` round-trip fidelity is load-bearing.** `parse(text)` →
  `serialize()` returns **byte-identical text** when no mutations have
  been applied. Mutations are line-level rewrites (toggle) or multi-line
  cut+insert (move) that preserve all surrounding context. Do not
  re-implement as a markdown AST + render — the byte-identity guarantee
  is what makes the dashboard non-destructive on a file Jon edits by hand.
- **`static.py` is inlined HTML on purpose.** Inlining keeps the page
  eligible for the handler-level Admin Gate; if you serve it from
  `public/` a guest could fetch the shell. Inlining also pins the
  page's DESIGN.md compliance (see the module docstring for the
  honored rules).
- **`admin/static.py` is the largest file in the codebase (1,172 LOC).**
  Most of it is HTML/CSS/JS string content, not Python logic. Splitting
  it into `static_html.py` + `static_css.py` + `static_js.py` is on the
  AI-readiness Phase 2 list.

## Related

- Tink TODO: `/Users/jondev/dev/socratink/todo.md` (outside the repo).
- Glossary terms used by the parser: `docs/pipeline/_meta/CONTEXT.md`.
- Tests: `tests/test_admin_router.py`, parser tests collocated.
