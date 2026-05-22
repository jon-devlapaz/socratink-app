# tests/e2e — browser smoke suite

Industry-standard browser smoke for socratink-app. Built on **pytest +
playwright-python**. Designed to be run by anyone (human or AI agent) with
one shell command, against local dev / Vercel preview / production.

## What's covered

The suite spans five files:

### `test_smoke.py` — 31 tests

Key checks include:

1. **`test_health_endpoint_ok`** — backend reachable, `/api/health` shape valid.
   Runs first to absorb serverless cold-start latency.
2. **`test_homepage_loads_with_critical_dom`** — `#drawer`, `#bottom-nav`,
   `#concept-list`, `.sidebar-brand-mark` all attached after navigation.
3. **`test_guest_session_is_labeled_as_guest`** — anonymous Supabase sessions
   render as guest, not as signed-in users.
4. **`test_launch_pad_accepts_any_non_empty_sketch`** —
   launch-pad validation enables any non-empty learner response and keeps empty
   sketches blocked.
5. **`test_drawer_toggle_remains_visible_in_concept_view`** — sidebar toggle
   stays available after opening a library concept (regression gate for the
   drawer-toggle visibility fix).
6. **`test_feedback_button_keeps_sidebar_open`** — feedback opens as an
   overlay action without collapsing the sidebar.
7. **`test_feedback_dialog_has_accessible_escape_close`** — feedback keeps the
   modal dialog role, Escape close behavior, and labeled title contract.
8. **`test_saved_library_concept_reopens_map_view`** — library cards reopen
   the concept-map view, not a stale shell, on the second click (regression
   gate for the library reopen fix).
9. **`test_active_concept_delete_confirms_then_returns_to_desk`** — deleting
   the open concept confirms via dialog and resets the workspace to the desk
   (regression gate for the active-concept delete flow).
10. **`test_desk_iso_board_state_surface_and_room_labels`** — desk iso board
   exposes truthful tile state and quiet hover/focus room labels.
11. **`test_desk_layout_identical_when_empty_or_populated`** — empty desk
   renders the same 9-tile iso-board geometry as a populated library
   (regression gate against the old empty-state hide rule).
12. **`test_no_console_errors_on_first_paint`** — zero same-origin
   `console.error` during first paint.
13. **`test_no_failed_critical_asset_requests`** — zero same-origin
    `requestfailed` events during first paint, except narrow Chromium
    `ERR_ABORTED` bootstrap noise for `/api/health` and `/api/me`.
14. **`test_theme_preloader_resilient_on_blank_localstorage`** — inline IIFE
    at top of `<body>` produces no errors on a fresh visit.
15. Additional smoke tests cover the inline concept-page reconstruction flow,
    study reveal persistence, repair QA seeding, Library reconstruction copy,
    active-entry preservation after sketch edits, training-store hydration,
    feedback submit/reopen and mobile access, and local guest bootstrap
    behavior.

### `test_drill_chamber.py` — 5 tests

Smoke gate for the full-screen drill chamber view (`#drill-chamber-view`) and
training-evidence persistence: hidden on initial load, opens and hides the map
when entered, exit restores the map, completed cold attempts update Library
training copy, and unrecordable drill results do not mutate graph state.

### `test_concept_page_b2.py` — 3 tests

B-2 concept page layout gate: route-margin layout renders, the reconstruction
CTA opens the inline attempt panel while the full-screen drill chamber stays
hidden, and the Route/Graph segmented toggle is absent.

### `test_strip_nav.py` — 7 tests

Route-margin behavior: click swaps the work column, keyboard navigation
walks the route, the first actionable entry exposes the inline draft surface,
locked entries show a disabled CTA, no Route/Graph toggle or `#graph-content`
section exists, and route items are focusable.

### `test_app_helper_modules.py` — 1 test

Helper-module browser-contract guard: imports the in-app JS modules
(`html.js`, `app-timer.js`, `app-hero.js`, `phase-b-session.js`,
`settings-view.js`, `library-view.js`, `source-input-ui.js`,
`board-grid.js`, `theme-preference.js`, `app-shell-ui.js`,
`training-store.js`, `training-derive.js`, `concept-page-view.js`) from the live page and exercises their pure
helpers against the real browser DOM/storage so renames or signature
drift fail the suite.

What's deliberately out of scope:
- Non-guest authenticated flows (extension point: `authenticated_page`
  fixture). Several tests use a guest Supabase session, so they exercise some
  in-app behavior, but real signed-in flows still need a separate suite.
- Full critical-flow exercise (`selectTile`, `runHeroAction`, `toggleTheme`)
  — only library reopen and concept delete are partially covered here.
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
preferred entry point. **Scope note:** the wrapper currently runs only
`test_smoke.py` (31 tests). Use the raw pytest invocations below to run the
full suite (47 tests across the five files).

Local runs use the repo-owned `/auth/e2e/guest` bootstrap when
`SOCRATINK_E2E_LOCAL_GUEST=1` is set. `scripts/dev.sh` enables this by default,
and `scripts/qa-smoke.sh` also sets it automatically for loopback targets, so
repeated browser tests do not create real Supabase anonymous users or trip the
anonymous sign-in rate limit.

```bash
# Local — needs `bash scripts/dev.sh` in another shell (runs the
# local-auth preflight, then `uvicorn main:app --reload`)
bash scripts/qa-smoke.sh local

# Production (https://app.socratink.ai)
bash scripts/qa-smoke.sh live

# Explicit URL (e.g. Vercel preview deployment)
bash scripts/qa-smoke.sh https://socratink-app-git-dev-fresh-jon-devlapaz.vercel.app
```

Raw pytest invocations (when you need flags the wrapper doesn't pass through,
or want the full five-file suite the wrapper doesn't yet cover):

```bash
# Full suite (all five files, 47 tests) — needs `bash scripts/dev.sh` in another shell
pytest tests/e2e/ -v

# Smoke file only (matches what the wrapper runs)
pytest tests/e2e/test_smoke.py -v

# Against any URL via env var
SOCRATINK_BASE_URL=https://app.socratink.ai pytest tests/e2e/ -v

# Headed (browser visible — for debugging)
pytest tests/e2e/ -v --headed

# Full trace on every test (huge, debugging only)
PWDEBUG=1 pytest tests/e2e/ -v
```

## Output

Abbreviated pass shape (47 tests across the five files):

```text
tests/e2e/test_smoke.py::test_health_endpoint_ok PASSED
tests/e2e/test_smoke.py::test_homepage_loads_with_critical_dom PASSED
tests/e2e/test_smoke.py::test_first_run_guidance_is_inline_not_modal PASSED
tests/e2e/test_smoke.py::test_guest_session_is_labeled_as_guest PASSED
tests/e2e/test_smoke.py::test_launch_pad_accepts_any_non_empty_sketch PASSED
tests/e2e/test_smoke.py::test_drawer_toggle_remains_visible_in_concept_view PASSED
tests/e2e/test_smoke.py::test_feedback_button_keeps_sidebar_open PASSED
tests/e2e/test_smoke.py::test_feedback_dialog_has_accessible_escape_close PASSED
tests/e2e/test_smoke.py::test_saved_library_concept_reopens_map_view PASSED
tests/e2e/test_smoke.py::test_active_concept_delete_confirms_then_returns_to_desk PASSED
tests/e2e/test_smoke.py::test_desk_iso_board_state_surface_and_room_labels PASSED
tests/e2e/test_smoke.py::test_desk_layout_identical_when_empty_or_populated PASSED
tests/e2e/test_smoke.py::test_no_console_errors_on_first_paint PASSED
tests/e2e/test_smoke.py::test_no_failed_critical_asset_requests PASSED
tests/e2e/test_smoke.py::test_theme_preloader_resilient_on_blank_localstorage PASSED
tests/e2e/test_drill_chamber.py::test_drill_chamber_view_hidden_on_load PASSED
tests/e2e/test_drill_chamber.py::test_drill_chamber_opens_and_hides_map PASSED
tests/e2e/test_drill_chamber.py::test_drill_chamber_exit_restores_map PASSED
tests/e2e/test_concept_page_b2.py::test_b2_layout_renders PASSED
tests/e2e/test_concept_page_b2.py::test_b2_cta_opens_inline_attempt PASSED
tests/e2e/test_concept_page_b2.py::test_b2_no_route_graph_toggle PASSED
tests/e2e/test_strip_nav.py::test_route_margin_click_swaps_work_column PASSED
tests/e2e/test_strip_nav.py::test_route_margin_keyboard_nav PASSED
tests/e2e/test_strip_nav.py::test_first_actionable_entry_shows_try_from_memory PASSED
tests/e2e/test_strip_nav.py::test_locked_entry_shows_disabled_cta PASSED
tests/e2e/test_strip_nav.py::test_no_route_graph_toggle PASSED
tests/e2e/test_strip_nav.py::test_no_graph_content_section PASSED
tests/e2e/test_strip_nav.py::test_route_items_are_focusable PASSED
tests/e2e/test_app_helper_modules.py::test_app_helper_modules_preserve_browser_contracts PASSED

============================== 47 passed ==============================
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
- `EXPECTED_ABORTED_BOOTSTRAP_PATHS` — bootstrap API paths whose Chromium
  `ERR_ABORTED` request failures are ignored when tests deliberately navigate
  or reload during guest setup. Defaults to `("/api/health", "/api/me")`;
  actual HTTP failures and aborted app assets still fail the suite.

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
`authenticated_page` and exercise the still-uncovered critical flows
(`selectTile`, `runHeroAction`, `toggleTheme`) without paying the login tax
in every test.

## Why this stack

| Choice | Reason |
|---|---|
| Playwright | Microsoft-maintained, industry standard for browser automation in 2026; better auto-wait semantics than Selenium/Puppeteer; cross-browser without extra config. |
| Python binding | The repo is Python (FastAPI, pytest). Adding a Node toolchain for one test suite would be cargo-cult. |
| pytest | Already the project's test runner. Reuse fixtures, CLI flags, plugins, IDE integration. |
| Same-origin filtering | Cross-origin noise (browser extensions, third-party fonts/analytics) creates false failures. The `same_origin` predicate keeps the suite reliable across environments. |
| Test order absorbs cold start | `test_health_endpoint_ok` runs first; subsequent browser tests see a warm Lambda. Uses Playwright's default 30s navigation timeout (do not lower — Vercel cold starts can hit ~20s). |
