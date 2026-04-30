"""Smoke suite for socratink-app.

What this catches
-----------------
- Backend is up and the FastAPI app booted (`/api/health` shape valid)
- Frontend renders without a blank-page regression (critical DOM IDs present)
- Anonymous Supabase sessions are labeled as guest, not signed-in users
- Drawer toggle stays visible after opening a library concept
- Library cards reopen the concept-map view (not a stale shell) on second click
- Deleting the active concept confirms via dialog and resets to the desk
- No same-origin console errors during first paint
- No same-origin asset request failures during first paint
- The inline theme-preloader IIFE is resilient to a blank localStorage

What this deliberately does NOT cover
-------------------------------------
- Non-guest authenticated flows (extension point: `authenticated_page`
  fixture in conftest.py with stored storageState). The guest-session tests
  here exercise some in-app behavior, but real signed-in flows still need a
  separate suite.
- Full critical-flow exercise (`selectTile`, `runHeroAction`, `toggleTheme`)
  — only library reopen and active-concept delete are partially covered here.
- Visual regression (screenshots are only saved on failure for debugging)
- Performance / lighthouse metrics

Run
---
    # local (start the app first: `bash scripts/dev.sh`)
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


def _enter_app_shell_as_guest(page: Page, base_url: str) -> None:
    """Navigate to base_url and bypass the /login redirect via the guest link.

    On Vercel, static `public/index.html` can take priority over the `/api`
    rewrite, so `/` may serve the app shell before the FastAPI redirect fires.
    In that case, explicitly check `/api/me` and enter through `/login`.
    """
    page.goto(base_url)
    if "/login" not in page.url:
        session = _fetch_browser_session(page)
        if session.get("authenticated") or session.get("guest_mode"):
            return
        page.goto(urljoin(base_url + "/", "login?return_to=%2F"))
    if "/login" in page.url:
        expect(page.locator("#guest-continue-link")).to_be_visible()
        page.locator("#guest-continue-link").click()
        page.wait_for_url(lambda url: "/login" not in url, timeout=15_000)


def _fetch_browser_session(page: Page) -> dict:
    payload = page.evaluate(
        """async () => {
            const response = await fetch('/api/me', {
              credentials: 'same-origin',
              headers: { Accept: 'application/json' },
            });
            if (!response.ok) return {};
            return response.json();
        }"""
    )
    return payload if isinstance(payload, dict) else {}


def test_homepage_loads_with_critical_dom(clean_page: Page, base_url: str) -> None:
    """Critical IDs are attached to the DOM after a fresh navigation."""
    _enter_app_shell_as_guest(clean_page, base_url)

    # Auto-wait via expect() — Playwright polls for visibility.
    # Drawer is desktop sidebar; bottom-nav is mobile nav. At 1280px viewport
    # at least one of them should be present in the DOM (CSS may hide it).
    expect(clean_page.locator("#drawer")).to_be_attached()
    expect(clean_page.locator("#bottom-nav")).to_be_attached()
    expect(clean_page.locator("#concept-list")).to_be_attached()
    # Brand mark anchors that the head/sidebar mounted.
    expect(clean_page.locator(".sidebar-brand-mark").first).to_be_attached()


def test_guest_session_is_labeled_as_guest(
    clean_page: Page, base_url: str
) -> None:
    """Anonymous Supabase sessions must render as guest, not signed-in user."""
    clean_page.on("console", lambda msg: print(f"PAGE LOG: {msg.type} {msg.text}"))
    clean_page.on("pageerror", lambda exc: print(f"PAGE ERROR: {exc}"))
    clean_page.on("response", lambda r: print(f"RES: {r.status} {r.url}") if r.status >= 400 else None)
    _enter_app_shell_as_guest(clean_page, base_url)
    session = _fetch_browser_session(clean_page)

    assert session.get("authenticated") is True
    assert session.get("guest_mode") is True
    expect(clean_page.locator("#auth-status")).to_have_text("Guest mode")
    expect(clean_page.locator("#auth-login-link")).to_have_text("Save & Sync")
    expect(clean_page.locator("#auth-logout-btn")).to_have_text("Exit Guest")


def test_drawer_toggle_remains_visible_in_concept_view(
    clean_page: Page, base_url: str
) -> None:
    """The sidebar control must stay available after entering a concept."""
    clean_page.evaluate(
        """localStorage.setItem(
            'socratink:firstSeenAt:v1:guest',
            new Date().toISOString()
        );"""
    )
    _enter_app_shell_as_guest(clean_page, base_url)

    toggle = clean_page.locator("#drawer-toggle")
    expect(toggle).to_be_visible()

    clean_page.locator("#nav-library").click()
    expect(clean_page.get_by_text("Documentation Concepts")).to_be_visible()

    clean_page.locator(".library-card-vault", has_text="Hermes Agent").click()
    expect(clean_page.locator("#concept-header-title")).to_contain_text("Hermes Agent")
    expect(toggle).to_be_visible()


def test_saved_library_concept_reopens_map_view(
    clean_page: Page, base_url: str
) -> None:
    """Library entry points should both open the concept map, not a stale shell."""
    clean_page.evaluate(
        """localStorage.setItem(
            'socratink:firstSeenAt:v1:guest',
            new Date().toISOString()
        );"""
    )
    _enter_app_shell_as_guest(clean_page, base_url)

    clean_page.locator("#nav-library").click()
    clean_page.locator(".library-card-vault", has_text="Hermes Agent").click()
    expect(clean_page.locator("#concept-header-title")).to_contain_text("Hermes Agent")
    assert clean_page.locator("body").get_attribute("data-map-open") == "true"

    clean_page.locator("#nav-library").click()
    your_library = clean_page.locator("#library-content .library-section", has_text="Your Library")
    your_library.locator(".library-card-vault", has_text="Hermes Agent").click()

    expect(clean_page.locator("#concept-header-title")).to_contain_text("Hermes Agent")
    assert clean_page.locator("body").get_attribute("data-map-open") == "true"
    expect(clean_page.locator("#map-mode-graph")).to_have_attribute("aria-pressed", "true")


def test_active_concept_delete_confirms_then_returns_to_desk(
    clean_page: Page, base_url: str
) -> None:
    """Deleting the open concept must not leave stale concept content visible."""
    clean_page.evaluate(
        """localStorage.setItem(
            'socratink:firstSeenAt:v1:guest',
            new Date().toISOString()
        );"""
    )
    _enter_app_shell_as_guest(clean_page, base_url)

    clean_page.locator("#nav-library").click()
    clean_page.locator(".library-card-vault", has_text="Hermes Agent").click()
    expect(clean_page.locator("#concept-header-title")).to_contain_text("Hermes Agent")

    delete_button = clean_page.locator(".concept-item.active .concept-delete")

    def dismiss_delete(dialog) -> None:
        assert "Delete \"Hermes Agent\"?" in dialog.message
        dialog.dismiss()

    clean_page.once("dialog", dismiss_delete)
    delete_button.click()
    expect(clean_page.locator("#concept-header-title")).to_contain_text("Hermes Agent")
    expect(clean_page.locator(".concept-item.active")).to_have_count(1)

    def accept_delete(dialog) -> None:
        assert "Delete \"Hermes Agent\"?" in dialog.message
        dialog.accept()

    clean_page.once("dialog", accept_delete)
    delete_button.click()
    expect(clean_page.locator("#title")).to_have_text("What do you want to understand?")
    expect(clean_page.locator(".concept-item")).to_have_count(0)
    expect(clean_page.locator("#concept-header-title")).not_to_be_visible()
    assert clean_page.locator("body").get_attribute("data-map-open") != "true"


# --- 3. No console errors on first paint ---------------------------------


def test_no_console_errors_on_first_paint(
    clean_page: Page, base_url: str, captured: dict
) -> None:
    """Capture all console.error messages during navigation; expect none.

    Allow-list lives in conftest.CONSOLE_ERROR_ALLOW_LIST. Cross-origin
    errors (analytics, fonts, browser extensions) are filtered out by
    the listener — only same-origin error-level messages count.
    """
    _enter_app_shell_as_guest(clean_page, base_url)
    # Settle: give the page a beat to finish any deferred error throws.
    clean_page.wait_for_load_state("networkidle")

    errors = captured["console_errors"]
    if errors:
        rendered = "\n".join(f"  - {m.text} (at {m.location})" for m in errors)
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
    _enter_app_shell_as_guest(clean_page, base_url)
    clean_page.wait_for_load_state("networkidle")

    failed = captured["failed_requests"]
    if failed:
        rendered = "\n".join(f"  - {r.method} {r.url} ({r.failure})" for r in failed)
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
    # clean_page already cleared storage. Enter the app shell so the IIFE runs.
    _enter_app_shell_as_guest(clean_page, base_url)
    clean_page.wait_for_load_state("networkidle")

    errors = captured["console_errors"]
    theme_related = [
        m for m in errors if "theme" in m.text.lower() or "learnops" in m.text.lower()
    ]
    assert not theme_related, (
        f"theme preloader produced console errors on blank state: "
        f"{[m.text for m in theme_related]}"
    )
