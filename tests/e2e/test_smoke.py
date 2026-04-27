"""Smoke suite for socratink-app.

What this catches
-----------------
- Backend is up and the FastAPI app booted (health endpoint reachable)
- Frontend renders without a blank-page regression (critical DOM IDs present)
- No same-origin console errors during first paint
- No same-origin asset request failures during first paint
- The inline theme-preloader IIFE is resilient to a blank localStorage

What this deliberately does NOT cover
-------------------------------------
- Authenticated flows (will live in test_authenticated_flows.py later, using
  an `authenticated_page` fixture in conftest.py with stored storageState)
- The 4 critical flows: selectTile, runHeroAction, toggleTheme,
  importLibraryConcept (deeper e2e suite)
- Visual regression (screenshots are only saved on failure for debugging)
- Performance / lighthouse metrics

Run
---
    # local (uvicorn main:app --reload running)
    pytest tests/e2e/test_smoke.py -v

    # against a deployed environment
    SOCRATINK_BASE_URL=https://socratink.com pytest tests/e2e/test_smoke.py -v

Test ordering note
------------------
Tests run in source order. `test_health_endpoint_ok` is intentionally first
to absorb any serverless cold-start latency before the browser tests run.
"""
from __future__ import annotations

import time
from urllib.parse import urljoin

import pytest
import requests
from playwright.sync_api import Page, expect


# --- 1. Health check (also serves as serverless warm-up) -----------------

def test_health_endpoint_ok(base_url: str) -> None:
    """GET /api/health returns the expected shape. 3 retries with backoff."""
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = requests.get(urljoin(base_url + "/", "api/health"), timeout=15)
            response.raise_for_status()
            payload = response.json()
            assert payload.get("status") == "ok", f"unexpected status: {payload}"
            assert isinstance(payload.get("server_key_configured"), bool), (
                f"server_key_configured missing or wrong type: {payload}"
            )
            # Contract per ai_service.get_drill_session_time_limit_seconds:
            # int | None — None means "disabled by env var or unset".
            limit = payload.get("drill_session_time_limit_seconds")
            assert "drill_session_time_limit_seconds" in payload, (
                f"drill_session_time_limit_seconds key missing: {payload}"
            )
            assert limit is None or (isinstance(limit, int) and limit > 0), (
                f"drill_session_time_limit_seconds must be int>0 or None: {payload}"
            )
            return
        except (requests.RequestException, AssertionError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(0.3 * (attempt + 1))
    raise AssertionError(f"/api/health failed after 3 attempts: {last_error}")


# --- 2. Homepage renders critical DOM ------------------------------------

def test_homepage_loads_with_critical_dom(clean_page: Page, base_url: str) -> None:
    """Critical IDs are attached to the DOM after a fresh navigation."""
    clean_page.goto(base_url)
    
    # Fresh sessions are redirected to /login. Enter as guest to load the app shell.
    clean_page.locator("#guest-continue-link").click()

    # Auto-wait via expect() — Playwright polls for visibility.
    # Drawer is desktop sidebar; bottom-nav is mobile nav. At 1280px viewport
    # at least one of them should be present in the DOM (CSS may hide it).
    expect(clean_page.locator("#drawer")).to_be_attached()
    expect(clean_page.locator("#bottom-nav")).to_be_attached()
    expect(clean_page.locator("#concept-list")).to_be_attached()
    # Brand mark anchors that the head/sidebar mounted.
    expect(clean_page.locator(".sidebar-brand-mark").first).to_be_attached()


# --- 3. No console errors on first paint ---------------------------------

def test_no_console_errors_on_first_paint(
    clean_page: Page, base_url: str, captured: dict
) -> None:
    """Capture all console.error messages during navigation; expect none.

    Allow-list lives in conftest.CONSOLE_ERROR_ALLOW_LIST. Cross-origin
    errors (analytics, fonts, browser extensions) are filtered out by
    the listener — only same-origin error-level messages count.
    """
    clean_page.goto(base_url)
    # Settle: give the page a beat to finish any deferred error throws.
    clean_page.wait_for_load_state("networkidle")

    errors = captured["console_errors"]
    if errors:
        rendered = "\n".join(
            f"  - {m.text} (at {m.location})" for m in errors
        )
        pytest.fail(
            f"{len(errors)} same-origin console.error(s) during first paint:\n{rendered}"
        )


# --- 4. No failed same-origin asset requests -----------------------------

def test_no_failed_critical_asset_requests(
    clean_page: Page, base_url: str, captured: dict
) -> None:
    """No same-origin request fails during first paint.

    Cross-origin failures (analytics, third-party fonts) are ignored by the
    listener. Specific paths can be allow-listed via EXPECTED_404_PATHS in
    conftest.py.
    """
    clean_page.goto(base_url)
    clean_page.wait_for_load_state("networkidle")

    failed = captured["failed_requests"]
    if failed:
        rendered = "\n".join(
            f"  - {r.method} {r.url} ({r.failure})" for r in failed
        )
        pytest.fail(
            f"{len(failed)} same-origin request failure(s) during first paint:\n{rendered}"
        )


# --- 5. Theme preloader is resilient to blank localStorage ---------------

def test_theme_preloader_resilient_on_blank_localstorage(
    clean_page: Page, base_url: str, captured: dict
) -> None:
    """The inline IIFE at the top of <body> reads localStorage('learnops-theme').

    On a fresh visit (blank localStorage) it should resolve to "no theme set",
    apply default light mode, and produce zero console errors. The IIFE has
    a try/catch but should never enter the catch on blank state.
    """
    # clean_page already cleared storage. Navigate again to re-run the IIFE.
    clean_page.goto(base_url)
    clean_page.wait_for_load_state("networkidle")

    errors = captured["console_errors"]
    theme_related = [
        m for m in errors if "theme" in m.text.lower() or "learnops" in m.text.lower()
    ]
    assert not theme_related, (
        f"theme preloader produced console errors on blank state: "
        f"{[m.text for m in theme_related]}"
    )
