# tests/e2e — browser smoke suite

Industry-standard browser smoke for socratink-app. Built on **pytest +
playwright-python**. Designed to be run by anyone (human or AI agent) with
one shell command, against local dev / Vercel preview / production.

## What's covered

6 tests, runtime ~10s warm + ~30s cold, in source order:

1. **`test_health_endpoint_ok`** — backend reachable, `/api/health` shape valid.
   Runs first to absorb serverless cold-start latency.
2. **`test_homepage_loads_with_critical_dom`** — `#drawer`, `#bottom-nav`,
   `#concept-list`, `.sidebar-brand-mark` all attached after navigation.
3. **`test_guest_session_is_labeled_as_guest`** — anonymous Supabase sessions
   render as guest, not as signed-in users.
4. **`test_no_console_errors_on_first_paint`** — zero same-origin
   `console.error` during first paint.
5. **`test_no_failed_critical_asset_requests`** — zero same-origin
   `requestfailed` events during first paint.
6. **`test_theme_preloader_resilient_on_blank_localstorage`** — inline IIFE
   at top of `<body>` produces no errors on a fresh visit.

What's deliberately out of scope:
- Authenticated flows (extension point: `authenticated_page` fixture)
- Critical-flow exercise (`selectTile`, `runHeroAction`, `toggleTheme`,
  `importLibraryConcept`) — that's a deeper e2e suite, separate file
- Visual regression — Playwright captures a trace on failure for debugging
- Performance / Lighthouse

## First-time setup

```bash
pip install -r requirements-dev.txt
playwright install chromium
```

Browser binary (~150MB) is downloaded once into `~/.cache/ms-playwright/`.

## Running

The wrapper at `scripts/qa-smoke.sh` does setup + run in one command and is the
preferred entry point:

```bash
# Local — needs `uvicorn main:app --reload` in another shell
bash scripts/qa-smoke.sh local

# Production (https://app.socratink.ai)
bash scripts/qa-smoke.sh live

# Explicit URL (e.g. Vercel preview deployment)
bash scripts/qa-smoke.sh https://socratink-app-git-dev-fresh-jon-devlapaz.vercel.app
```

Raw pytest invocations (when you need flags the wrapper doesn't pass through):

```bash
# Local — needs `uvicorn main:app --reload` in another shell
pytest tests/e2e/test_smoke.py -v

# Against any URL via env var
SOCRATINK_BASE_URL=https://app.socratink.ai pytest tests/e2e/test_smoke.py -v

# Headed (browser visible — for debugging)
pytest tests/e2e/test_smoke.py -v --headed

# Full trace on every test (huge, debugging only)
PWDEBUG=1 pytest tests/e2e/test_smoke.py -v
```

## Output

Pass:

```
tests/e2e/test_smoke.py::test_health_endpoint_ok PASSED                 [ 20%]
tests/e2e/test_smoke.py::test_homepage_loads_with_critical_dom PASSED   [ 40%]
tests/e2e/test_smoke.py::test_no_console_errors_on_first_paint PASSED   [ 60%]
tests/e2e/test_smoke.py::test_no_failed_critical_asset_requests PASSED  [ 80%]
tests/e2e/test_smoke.py::test_theme_preloader_resilient_on_blank_localstorage PASSED [100%]

============================== 5 passed in 8.21s ==============================
```

Fail: pytest prints the offending console errors / failed requests verbatim,
and Playwright saves a trace under `test-results/` for `playwright show-trace`.

## Tuning knobs

In `conftest.py`:

- `CONSOLE_ERROR_ALLOW_LIST` — regex patterns of message substrings to
  ignore. Empty by default. Add only with a justifying comment / commit.
- `EXPECTED_404_PATHS` — paths whose 404s shouldn't fail the suite. Defaults
  to `("/_vercel/speed-insights/script.js",)` because Vercel injects that
  script in production but it's absent on local uvicorn — both the request
  failure and its console error are filtered for that path.

## Extending later

When you're ready for authenticated-flow tests, add this fixture to `conftest.py`:

```python
@pytest.fixture(scope="session")
def storage_state(base_url: str, ...) -> Path:
    # one-time login (UI or API), save to .auth/state.json
    ...

@pytest.fixture
def authenticated_page(browser: Browser, storage_state: Path) -> Page:
    context = browser.new_context(storage_state=str(storage_state))
    yield context.new_page()
    context.close()
```

Then a sibling `tests/e2e/test_critical_flows.py` can use
`authenticated_page` and exercise the four critical flows without paying the
login tax in every test.

## Why this stack

| Choice | Reason |
|---|---|
| Playwright | Microsoft-maintained, industry standard for browser automation in 2026; better auto-wait semantics than Selenium/Puppeteer; cross-browser without extra config. |
| Python binding | The repo is Python (FastAPI, pytest). Adding a Node toolchain for one test suite would be cargo-cult. |
| pytest | Already the project's test runner. Reuse fixtures, CLI flags, plugins, IDE integration. |
| Same-origin filtering | Cross-origin noise (browser extensions, third-party fonts/analytics) creates false failures. The `same_origin` predicate keeps the suite reliable across environments. |
| Test order absorbs cold start | `test_health_endpoint_ok` runs first; subsequent browser tests see a warm Lambda. Uses Playwright's default 30s navigation timeout (do not lower — Vercel cold starts can hit ~20s). |
