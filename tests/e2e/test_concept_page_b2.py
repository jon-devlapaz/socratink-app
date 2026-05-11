"""End-to-end smoke for the B-2 concept page layout.

Covers: open a concept page; strip, threshold, active entry, and
nearby list all render; click 'Try from memory' opens the chamber;
Route/Graph toggle is preserved.

Uses the same seed-via-localStorage + guest-auth pattern as test_smoke.py.
The seeded concept has backbone entries so the nearby list renders.

Navigation: uses the sidebar concept-item click (not the library card),
because openLibraryConcept() immediately sets graph mode after calling
showMapView(), which hides #map-content. The sidebar path calls showMapView()
and stays in study mode (the B-2 layout path).
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

import pytest
from playwright.sync_api import Page, expect


# ---------------------------------------------------------------------------
# Helpers -- reuse patterns from test_smoke.py without importing them
# ---------------------------------------------------------------------------

_cached_guest_cookies = None


def _enter_app_shell_as_guest(page: Page, base_url: str) -> None:
    global _cached_guest_cookies
    if _cached_guest_cookies:
        page.context.add_cookies(_cached_guest_cookies)

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
            if not _cached_guest_cookies:
                _cached_guest_cookies = page.context.cookies()
            return
        page.goto(urljoin(base_url + "/", "login?return_to=%2F"))

    if "/login" in page.url:
        expect(page.locator("#guest-continue-link")).to_be_visible()
        target_pattern = re.compile(r"^" + re.escape(base_url.rstrip("/")) + r"/?$")
        with page.expect_navigation(url=target_pattern, timeout=15_000):
            page.locator("#guest-continue-link").click()
        _cached_guest_cookies = page.context.cookies()


def _seed_concept_with_backbone(page: Page, name: str = "Photosynthesis") -> None:
    """Seed a concept with backbone entries so the nearby list renders.
    Seeding happens BEFORE navigation so it is picked up on page load."""
    page.evaluate(
        f"""(() => {{
            const graphData = JSON.stringify({{
                metadata: {{
                  source_title: {name!r},
                  core_thesis: 'Plants convert light energy into chemical energy.',
                  starting_map_context: 'I think photosynthesis uses light to make sugar from CO2.',
                }},
                backbone: [
                  {{ id: 'b1', label: 'Light reactions', drill_status: 'locked',
                     purpose: 'The first entry asks for the governing idea.' }},
                  {{ id: 'b2', label: 'Calvin cycle', drill_status: 'locked',
                     purpose: 'Carbon fixation via RuBisCO.' }},
                  {{ id: 'b3', label: 'Electron transport', drill_status: 'locked',
                     purpose: 'ATP synthesis via the proton gradient.' }},
                ],
                clusters: [],
            }});
            localStorage.setItem('learnops_concepts', JSON.stringify([{{
                id: 'fixture-b2-concept',
                name: {name!r},
                createdAt: new Date().toISOString(),
                state: 'growing',
                contentPreview: 'Plants convert light energy into chemical energy.',
                contentType: 'fixture',
                startingMapContext: 'I think photosynthesis uses light to make sugar from CO2.',
                graphData,
            }}]));
        }})()"""
    )


def _open_seeded_concept_via_sidebar(page: Page, base_url: str) -> None:
    """Open the seeded concept by clicking its sidebar item.

    Uses the sidebar path (not openLibraryConcept) because the sidebar
    calls showMapView() and leaves the map in study mode -- showing the
    B-2 strip + page layout in #map-content.
    """
    # Seed before navigating so localStorage is already set when app loads.
    page.goto(base_url)
    _seed_concept_with_backbone(page)
    _enter_app_shell_as_guest(page, base_url)
    # Click via JS to avoid Playwright pointer interception issues with the
    # overlay buttons, matching what the real click event path does.
    page.evaluate("document.querySelector('#concept-list .concept-item')?.click()")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_b2_layout_renders(clean_page: Page, base_url: str) -> None:
    """Strip, threshold, active entry, and nearby list all render."""
    _open_seeded_concept_via_sidebar(clean_page, base_url)
    expect(clean_page.locator(".concept-strip__inner")).to_be_visible(timeout=8_000)
    expect(clean_page.locator(".concept-page-b2__entry-title")).to_be_visible()
    expect(clean_page.locator(".concept-page-b2__entry-cta")).to_be_visible()
    # threshold must be present (either with learner text or empty-state)
    expect(clean_page.locator(".concept-page-b2__threshold")).to_be_visible()
    # 3-entry backbone: 1 active + 2 nearby
    expect(clean_page.locator(".concept-page-b2__nearby-list")).to_be_visible()


def test_b2_cta_opens_chamber(clean_page: Page, base_url: str) -> None:
    """Clicking 'Try from memory' opens the drill chamber."""
    _open_seeded_concept_via_sidebar(clean_page, base_url)
    expect(clean_page.locator(".concept-page-b2__entry-cta")).to_be_visible(timeout=8_000)
    clean_page.locator(".concept-page-b2__entry-cta").click()
    expect(clean_page.locator("#drill-chamber-view")).to_be_visible(timeout=8_000)


def test_b2_route_graph_toggle_preserved(clean_page: Page, base_url: str) -> None:
    """Route/Graph toggle still works; switching to Graph shows graph-content."""
    _open_seeded_concept_via_sidebar(clean_page, base_url)
    expect(clean_page.locator(".concept-strip__inner")).to_be_visible(timeout=8_000)
    # Toggle to Graph
    clean_page.evaluate("document.querySelector('#map-mode-graph')?.click()")
    expect(clean_page.locator("#graph-content")).to_be_visible()
    # Toggle back to Route
    clean_page.evaluate("document.querySelector('#map-mode-study')?.click()")
    expect(clean_page.locator(".concept-strip__inner")).to_be_visible()
