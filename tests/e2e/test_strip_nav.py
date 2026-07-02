"""End-to-end smoke for route-margin navigation on the concept page.

Covers: click a route item swaps the work column; click a
locked route item shows the locked silhouette state; keyboard arrow nav
steps through backbone entries; the first actionable entry enables
the inline draft-from-memory surface; the legacy Route/Graph toggle and
#graph-content section are absent. The live Route/Constellation switch is
covered in test_smoke.py.

Uses the same seed-via-localStorage + guest-auth pattern as the
existing e2e suite. The seeded concept has three backbone entries so
click and keyboard nav tests can exercise more than one entry.
"""
from __future__ import annotations

import re
import os
from urllib.parse import urljoin

import pytest
from playwright.sync_api import Page, expect


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_strip_guest_cookies: list | None = None


def _enter_app_shell_as_guest(page: Page, base_url: str) -> None:
    """Navigate to the app shell as a guest user.

    Uses a module-level cookie cache (same pattern as the existing smoke suite)
    so only the first test in a pytest run needs to click the guest link.
    Subsequent tests re-use the cached session cookies.
    """
    global _strip_guest_cookies
    if _strip_guest_cookies:
        page.context.add_cookies(_strip_guest_cookies)

    if os.getenv("SOCRATINK_E2E_LOCAL_GUEST"):
        page.goto(urljoin(base_url.rstrip("/") + "/", "auth/e2e/guest?return_to=%2F"))
        result = page.evaluate(
            """async () => {
                const r = await fetch('/api/me', {
                  credentials: 'same-origin',
                  headers: { Accept: 'application/json' },
                });
                if (!r.ok) return {};
                return r.json();
            }"""
        )
        session = result if isinstance(result, dict) else {}
        if session.get("authenticated") or session.get("guest_mode"):
            _strip_guest_cookies = page.context.cookies()
            return

    page.goto(base_url)
    if "/login" not in page.url:
        result = page.evaluate(
            """async () => {
                const r = await fetch('/api/me', {
                  credentials: 'same-origin',
                  headers: { Accept: 'application/json' },
                });
                if (!r.ok) return {};
                return r.json();
            }"""
        )
        session = result if isinstance(result, dict) else {}
        if session.get("authenticated") or session.get("guest_mode"):
            if not _strip_guest_cookies:
                _strip_guest_cookies = page.context.cookies()
            return
        page.goto(urljoin(base_url.rstrip("/") + "/", "login?return_to=%2F"))

    if "/login" in page.url:
        expect(page.locator("#guest-continue-link")).to_be_visible(timeout=8_000)
        target_pattern = re.compile(r"^" + re.escape(base_url.rstrip("/")) + r"/?$")
        with page.expect_navigation(url=target_pattern, timeout=15_000):
            page.locator("#guest-continue-link").click()
        _strip_guest_cookies = page.context.cookies()


def _seed_concept_with_backbone(page: Page) -> None:
    """Seed a concept with three backbone entries (first locked, second primed,
    third locked). Seeding happens before navigation so it is picked up on load.
    """
    page.evaluate(
        """(() => {
            const graphData = JSON.stringify({
                metadata: {
                  source_title: 'Photosynthesis',
                  core_thesis: 'Plants convert light energy into chemical energy.',
                  starting_map_context: 'I think photosynthesis uses light to make sugar from CO2.',
                },
                backbone: [
                  { id: 'b1', label: 'Light reactions', drill_status: 'locked',
                    purpose: 'The first entry asks for the governing idea.' },
                  { id: 'b2', drill_status: 'primed',
                    purpose: 'Carbon fixation via RuBisCO.' },
                  { id: 'b3', drill_status: 'locked',
                    purpose: 'ATP synthesis via the proton gradient.' },
                  { id: 'b4', drill_status: 'locked',
                    purpose: 'Oxygen accepts electrons at the end of the chain.' },
                ],
                clusters: [],
            });
            localStorage.setItem('learnops_concepts', JSON.stringify([{
                id: 'fixture-strip-nav',
                name: 'Photosynthesis',
                createdAt: new Date().toISOString(),
                state: 'growing',
                contentPreview: 'Plants convert light energy into chemical energy.',
                contentType: 'fixture',
                startingMapContext: 'I think photosynthesis uses light to make sugar from CO2.',
                graphData,
            }]));
        })()"""
    )


def _open_seeded_concept(page: Page, base_url: str) -> None:
    """Seed then open the concept via the sidebar concept-item click."""
    page.goto(base_url)
    _seed_concept_with_backbone(page)
    _enter_app_shell_as_guest(page, base_url)
    page.evaluate("document.querySelector('#concept-list .concept-item')?.click()")
    expect(page.locator(".concept-page-b2__route")).to_be_visible(timeout=8_000)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_route_margin_click_swaps_work_column(page: Page, base_url: str) -> None:
    """Clicking a different route item updates the work column entry title."""
    _open_seeded_concept(page, base_url)
    initial_title = page.locator(".concept-page-b2__entry-title").text_content()
    items = page.locator(".concept-page-b2__route-item")
    count = items.count()
    if count < 2:
        pytest.skip("concept has fewer than 2 backbone entries")
    # Click the second route item (index 1)
    items.nth(1).click()
    # Wait for the 240ms fade-out + 320ms fade-in to settle
    page.wait_for_timeout(700)
    new_title = page.locator(".concept-page-b2__entry-title").text_content()
    assert new_title != initial_title, "work column did not swap on route-margin click"
    expect(page.locator(".concept-page-b2__route-item.is-active")).to_have_attribute(
        "aria-label", "Explain how, primed, current"
    )
    expect(page.locator(".concept-page-b2__route-item.is-active .concept-page-b2__route-title")).to_have_text("Explain how")
    items = page.locator(".concept-page-b2__route-item")
    items.nth(3).click()
    page.wait_for_timeout(700)
    expect(page.locator(".concept-page-b2__route-item.is-active")).to_have_attribute(
        "aria-label", "Test the edge, locked, current"
    )
    expect(page.locator(".concept-page-b2__route-item.is-active .concept-page-b2__route-title")).to_have_text("Test the edge")


def test_route_margin_keyboard_nav(page: Page, base_url: str) -> None:
    """ArrowDown advances the active entry; title changes in the work column."""
    _open_seeded_concept(page, base_url)
    items = page.locator(".concept-page-b2__route-item")
    if items.count() < 2:
        pytest.skip("concept has fewer than 2 backbone entries")
    initial_title = page.locator(".concept-page-b2__entry-title").text_content()
    # Focus the first item and press ArrowDown
    items.first.focus()
    page.keyboard.press(" ")
    page.keyboard.press("ArrowDown")
    page.wait_for_timeout(700)
    new_title = page.locator(".concept-page-b2__entry-title").text_content()
    assert new_title != initial_title, "ArrowDown did not advance the active entry"


def test_first_actionable_entry_shows_try_from_memory(page: Page, base_url: str) -> None:
    """The first unattempted actionable entry is ready, not blocked locked."""
    _open_seeded_concept(page, base_url)
    expect(page.locator(".concept-page-b2__attempt-input")).to_be_visible()
    expect(page.locator(".concept-page-b2__attempt-save")).to_have_text("Save draft")
    expect(page.locator(".concept-page-b2__attempt-save")).to_be_disabled()
    expect(page.locator(".concept-page-b2__entry-cta")).to_have_count(0)


def test_locked_entry_shows_disabled_cta(page: Page, base_url: str) -> None:
    """Clicking a blocked locked route item shows a disabled 'Locked' CTA."""
    _open_seeded_concept(page, base_url)
    locked_items = page.locator('.concept-page-b2__route-item[data-route-state="locked"]')
    if locked_items.count() == 0:
        pytest.skip("no locked entries available to test")
    locked_items.first.click()
    page.wait_for_timeout(700)
    cta = page.locator(".concept-page-b2__entry-cta")
    expect(cta).to_have_attribute("disabled", "")
    expect(cta).to_have_text("Locked")


def test_no_route_graph_toggle(page: Page, base_url: str) -> None:
    """The Route/Graph toggle markup is absent from the concept page."""
    _open_seeded_concept(page, base_url)
    expect(page.locator("#map-mode-graph")).to_have_count(0)
    expect(page.locator("#map-mode-study")).to_have_count(0)
    expect(page.locator(".map-mode-switch")).to_have_count(0)


def test_no_graph_content_section(page: Page, base_url: str) -> None:
    """The #graph-content section has been removed from the DOM."""
    _open_seeded_concept(page, base_url)
    expect(page.locator("#graph-content")).to_have_count(0)


def test_route_items_are_focusable(page: Page, base_url: str) -> None:
    """All route items have tabindex=0 and role=button (keyboard accessible)."""
    _open_seeded_concept(page, base_url)
    items = page.locator(".concept-page-b2__route-item")
    count = items.count()
    if count == 0:
        pytest.skip("no route items found")
    for i in range(count):
        item = items.nth(i)
        expect(item).to_have_attribute("tabindex", "0")
        expect(item).to_have_attribute("role", "button")
