"""Smoke suite for socratink-app.

What this catches
-----------------
- Backend is up and the FastAPI app booted (`/api/health` shape valid)
- Frontend renders without a blank-page regression (critical DOM IDs present)
- Anonymous Supabase sessions are labeled as guest, not signed-in users
- First-run guidance stays inline instead of regressing to a modal
- Library cards render training evidence instead of AI summary copy
- Launch-pad sketch validation accepts any non-empty learner response
- Inline concept-page attempts persist, retry, and preserve active-entry state
- Study reveal and repair records survive localStorage reload/reconstruction
- Drawer toggle stays visible after opening a library concept
- Feedback opens as an accessible overlay without collapsing the sidebar
- Library cards reopen the concept-map view (not a stale shell) on second click
- Deleting the active concept confirms via dialog and resets to the desk
- Desk tile states expose the expected learner-facing labels
- No same-origin console errors during first paint
- No same-origin asset request failures during first paint
- The inline theme-preloader IIFE is resilient to a blank localStorage

What this deliberately does NOT cover
-------------------------------------
- Non-guest authenticated flows (extension point: `authenticated_page`
  fixture in conftest.py with stored storageState). The guest-session tests
  here exercise some in-app behavior, but real signed-in flows still need a
  separate suite.
- Full critical-flow exercise (`selectTile`, `runHeroAction`, `toggleTheme`);
  smoke coverage is still targeted around shell, Library, desk, and inline
  concept-page regressions.
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

import json
import time
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import urlopen

import pytest
from playwright.sync_api import Error as PlaywrightError, Page, expect


# --- 1. Health check (also serves as serverless warm-up) -----------------


def test_health_endpoint_ok(base_url: str) -> None:
    """GET /api/health returns the expected shape. 3 retries with backoff."""
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urlopen(urljoin(base_url + "/", "api/health"), timeout=15) as response:
                payload = json.load(response)
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
        except (HTTPError, URLError, TimeoutError, AssertionError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(0.3 * (attempt + 1))
    raise AssertionError(f"/api/health failed after 3 attempts: {last_error}")


# --- 2. Homepage renders critical DOM ------------------------------------


_cached_guest_cookies = None


def _goto_with_retry(page: Page, url: str) -> None:
    """Retry transient production navigation aborts without masking HTTP failures."""
    retry_markers = (
        "net::ERR_ABORTED",
        "interrupted by another navigation",
    )
    last_error: PlaywrightError | None = None
    for attempt in range(3):
        try:
            page.goto(url)
            return
        except PlaywrightError as exc:
            if not any(marker in str(exc) for marker in retry_markers):
                raise
            last_error = exc
            if attempt < 2:
                page.wait_for_timeout(250 * (attempt + 1))
    assert last_error is not None
    raise last_error


def _enter_app_shell_as_guest(page: Page, base_url: str) -> None:
    """Navigate to base_url and bypass the /login redirect via the guest link.

    On Vercel, static `public/index.html` can take priority over the `/api`
    rewrite, so `/` may serve the app shell before the FastAPI redirect fires.
    In that case, explicitly check `/api/me` and enter through `/login`.
    """
    global _cached_guest_cookies
    if _cached_guest_cookies:
        page.context.add_cookies(_cached_guest_cookies)

    if os.getenv("SOCRATINK_E2E_LOCAL_GUEST"):
        _goto_with_retry(page, urljoin(base_url + "/", "auth/e2e/guest?return_to=%2F"))
        session = _fetch_browser_session(page)
        if session.get("authenticated") or session.get("guest_mode"):
            _cached_guest_cookies = page.context.cookies()
            _goto_with_retry(page, base_url)
            return

    _goto_with_retry(page, base_url)
    if "/login" not in page.url:
        session = _fetch_browser_session(page)
        if session.get("authenticated") or session.get("guest_mode"):
            if not _cached_guest_cookies:
                _cached_guest_cookies = page.context.cookies()
            return
        _goto_with_retry(page, urljoin(base_url + "/", "login?return_to=%2F"))
    if "/login" in page.url:
        expect(page.locator("#guest-continue-link")).to_be_visible()
        expect(page.locator("#guest-continue-link")).to_have_attribute("href", re.compile(r"^/auth/guest"))
        target_pattern = re.compile(r"^" + re.escape(base_url.rstrip("/")) + r"/?$")
        with page.expect_navigation(url=target_pattern, timeout=15_000):
            page.locator("#guest-continue-link").click()
        _cached_guest_cookies = page.context.cookies()


def _wait_for_app_settled(page: Page) -> None:
    """Deterministic replacement for `wait_for_load_state('networkidle')`.

    Why: networkidle is discouraged by Playwright — analytics beacons, retrying
    fetches, and websockets can keep the network "busy" forever and cause
    flakes. Instead: wait for the `load` event (resources done) and assert a
    critical app-shell element is attached. The `expect` call auto-retries,
    so deferred mount work has up to the default 5s to complete.
    """
    page.wait_for_load_state("load")
    expect(page.locator("#concept-list")).to_be_attached()
    page.wait_for_function("() => Boolean(window.App)")


def _fetch_browser_session(page: Page) -> dict:
    last_error: PlaywrightError | None = None
    for attempt in range(3):
        try:
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
        except PlaywrightError as exc:
            if "Failed to fetch" not in str(exc):
                raise
            last_error = exc
            if attempt < 2:
                page.wait_for_timeout(250 * (attempt + 1))
    assert last_error is not None
    raise last_error


def _is_loopback_base_url(base_url: str) -> bool:
    hostname = urlparse(base_url).hostname
    return hostname in {"localhost", "127.0.0.1", "::1"}


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


def test_first_run_guidance_is_inline_not_modal(clean_page: Page, base_url: str) -> None:
    """First-run orientation should not block the empty desk with a modal."""
    _enter_app_shell_as_guest(clean_page, base_url)

    expect(clean_page.locator(".first-run-welcome")).to_have_count(0)
    clean_page.locator("#nav-ignition").click()
    expect(clean_page.locator("#ignition-first-use")).to_have_text(
        "Write what you remember first. We'll show what to study — not a summary."
    )
    expect(clean_page.locator("#ignition-boundary")).to_have_text(
        "Add your first model to start."
    )


def test_guest_session_is_labeled_as_guest(
    clean_page: Page, base_url: str
) -> None:
    """Anonymous Supabase sessions must render as guest, not signed-in user."""
    _enter_app_shell_as_guest(clean_page, base_url)
    session = _fetch_browser_session(clean_page)

    assert session.get("authenticated") is True
    assert session.get("guest_mode") is True
    expect(clean_page.locator("#auth-status")).to_have_text("Guest mode")
    expect(clean_page.locator("#auth-login-link")).to_have_text("Save & Sync")
    expect(clean_page.locator("#auth-logout-btn")).to_have_text("Exit Guest")


def _seed_one_concept(page: Page, name: str = "Test Concept") -> None:
    """Seed the user's library with a single concept that can open a map.
    Used by smoke tests that need a concept on screen without going through
    the cold-attempt + extraction flow."""
    page.evaluate(
        f"""(() => {{
            const graphData = JSON.stringify({{
                metadata: {{ core_thesis: 'Seeded thesis for smoke fixture.' }},
                clusters: [],
            }});
            localStorage.setItem('learnops_concepts', JSON.stringify([{{
                id: 'fixture-concept',
                name: {name!r},
                createdAt: new Date().toISOString(),
                state: 'growing',
                contentPreview: 'Seeded thesis for smoke fixture.',
                contentType: 'fixture',
                graphData,
            }}]));
        }})()"""
    )


def _seed_route_margin_concept(page: Page) -> None:
    """Seed a cold concept with a route shape for the gestalt canvas."""
    page.evaluate(
        """(() => {
            const graphData = JSON.stringify({
                metadata: {
                    core_thesis: 'Sodium channels open at threshold and sodium enters the neuron.',
                    starting_map_context: 'I think sodium just rushes in.',
                },
                backbone: [
                    {
                        id: 'core-thesis',
                        label: 'Core thesis',
                        purpose: 'Name the first change in the signal without reading the study note.',
                        drill_status: null,
                    },
                    {
                        id: 'backbone-principle',
                        label: 'Backbone principle',
                        purpose: 'Explain the rule that holds the mechanism together.',
                        drill_status: null,
                    },
                    {
                        id: 'mechanism-cluster',
                        label: 'Mechanism cluster',
                        purpose: 'Connect the steps that cause the signal to move.',
                        drill_status: null,
                    },
                    {
                        id: 'transfer-check',
                        label: 'Transfer check',
                        purpose: 'Use the same idea in a nearby case.',
                        drill_status: null,
                    },
                ],
                clusters: [
                    {
                        id: 'c1',
                        label: 'Sodium channel gate',
                        description: 'Name what opens the channel.',
                        subnodes: [{
                            id: 'c1_s1',
                            label: 'Sodium channel gate',
                            mechanism: 'Sodium channels open when membrane voltage reaches threshold, then sodium enters because the electrochemical gradient favors inward flow.',
                            drill_status: null,
                            learner_scaffold: {
                                bloom_level: 'remember',
                                learner_move: 'Say it',
                                task_label: 'Sodium gate',
                                task_cue: 'Name what opens the channel.',
                                entry_prompt: 'What do you think makes the sodium channel open?',
                                expected_shape: 'Write one sentence. Name the trigger, even if you are guessing.',
                                sentence_starter: 'My current guess is that the sodium channel opens when...',
                                blank_hint: 'Think about the point where a small signal becomes enough to matter.',
                                evidence_goal: 'Learner names a trigger for channel opening before study content appears.',
                            },
                        }],
                    },
                    {
                        id: 'c2',
                        label: 'Backbone principle',
                        description: 'Explain the rule that holds the mechanism together.',
                        subnodes: [{
                            id: 'c2_s1',
                            label: 'Backbone principle',
                            mechanism: 'Voltage threshold changes the channel conformation before sodium flow begins.',
                            drill_status: null,
                            learner_scaffold: {
                                bloom_level: 'understand',
                                learner_move: 'Explain how',
                                task_label: 'Opening rule',
                                task_cue: 'Name what has to happen before flow.',
                                entry_prompt: 'How does threshold connect to sodium movement?',
                                expected_shape: 'Write a cause-then-effect sentence.',
                                sentence_starter: 'Threshold matters because...',
                                blank_hint: 'Separate opening the gate from sodium moving through it.',
                                evidence_goal: 'Learner separates gate opening from ion movement.',
                            },
                        }],
                    },
                    {
                        id: 'c3',
                        label: 'Mechanism cluster',
                        description: 'Connect the steps that cause the signal to move.',
                        subnodes: [{
                            id: 'c3_s1',
                            label: 'Mechanism cluster',
                            mechanism: 'After enough sodium enters, depolarization spreads and opens neighboring voltage-gated channels.',
                            drill_status: null,
                            learner_scaffold: {
                                bloom_level: 'apply',
                                learner_move: 'Use it',
                                task_label: 'Signal spread',
                                task_cue: 'Use the rule on the next channel.',
                                entry_prompt: 'What would make the next nearby channel open?',
                                expected_shape: 'Write a nearby-case prediction.',
                                sentence_starter: 'The next channel would open when...',
                                blank_hint: 'Use the same threshold idea one step later.',
                                evidence_goal: 'Learner applies threshold gating to neighboring channels.',
                            },
                        }],
                    },
                    {
                        id: 'c4',
                        label: 'Transfer check',
                        description: 'Use the same idea in a nearby case.',
                        subnodes: [{
                            id: 'c4_s1',
                            label: 'Transfer check',
                            mechanism: 'If sodium channels fail to open, the depolarizing current cannot propagate normally.',
                            drill_status: null,
                            learner_scaffold: {
                                bloom_level: 'apply',
                                learner_move: 'Test the edge',
                                task_label: 'Blocked gate',
                                task_cue: 'Predict what breaks if the gate stays shut.',
                                entry_prompt: 'What would happen if the sodium channel never opened?',
                                expected_shape: 'Write one consequence for the signal.',
                                sentence_starter: 'If the gate never opened...',
                                blank_hint: 'Ask what sodium can no longer do.',
                                evidence_goal: 'Learner predicts a failure case from the gating rule.',
                            },
                        }],
                    },
                ],
            });
            localStorage.setItem('learnops_concepts', JSON.stringify([{
                id: 'route-margin-concept',
                name: 'How sodium channels create an action potential',
                createdAt: new Date().toISOString(),
                state: 'growing',
                contentPreview: 'This generated summary must not be the first thing shown.',
                contentType: 'fixture',
                startingMapContext: 'I think sodium just rushes in.',
                graphData,
            }]));
            localStorage.setItem('socratink:training:v1:route-margin-concept', JSON.stringify({
                concept_id: 'route-margin-concept',
                schema_version: 1,
                source_mode: 'source_less',
                grounding: 'learner_sketch',
                source_ref: null,
                sketch: { text: 'I think sodium just rushes in.' },
                node_records: {
                    c2_s1: {
                        attempts: [{
                            id: 'attempt-opening-rule',
                            at: '2026-05-21T10:00:00.000Z',
                            user_text: 'Threshold opens the gate before sodium moves through.',
                            classification: 'partial',
                            grader_version: 'fixture',
                            gaps: [],
                            kind: 'cold',
                        }],
                        repairs: [],
                    },
                },
            }));
        })()"""
    )


def _seed_training_truth_concept(page: Page) -> None:
    """Seed one concept plus node-training evidence for Library truth checks."""
    page.evaluate(
        """(() => {
            const graphData = JSON.stringify({
                metadata: {
                    core_thesis: 'AI GENERATED CORE THESIS SHOULD NOT APPEAR',
                    architecture_type: 'cause_effect',
                    difficulty: 'medium',
                    source_title: 'QA fixture source',
                    starting_map_context: 'Learner rough sketch baseline.',
                    map_maturity: 'provisional',
                },
                backbone: [{
                    id: 'qa-node',
                    label: 'Target node',
                    purpose: 'Use this entry to name the target mechanism from memory before reading the study note.',
                    study_note: 'The revealed study note names the comparison target after the cold attempt: identify the mechanism, then mark any missing link for repair.',
                    drill_status: null,
                }],
                clusters: [
                    {
                        id: 'cluster-1',
                        subnodes: [{
                            id: 'qa-node',
                            label: 'Target node',
                            purpose: 'Use this entry to name the target mechanism from memory before reading the study note.',
                            study_note: 'The revealed study note names the comparison target after the cold attempt: identify the mechanism, then mark any missing link for repair.',
                            drill_status: null,
                        }],
                    },
                ],
            });
            localStorage.setItem('learnops_concepts', JSON.stringify([{
                id: 'qa-training-card',
                name: 'Training Truth QA',
                createdAt: Date.now(),
                state: 'growing',
                contentPreview: 'SOURCE PREVIEW SHOULD NOT APPEAR',
                contentType: null,
                sourceUrl: null,
                startingMapContext: 'Learner rough sketch baseline.',
                graphData,
            }]));
            localStorage.setItem('learnops_active', 'qa-training-card');
            localStorage.setItem('socratink:training:v1:qa-training-card', JSON.stringify({
                concept_id: 'qa-training-card',
                schema_version: 1,
                source_mode: 'source_less',
                grounding: 'learner_sketch',
                source_ref: null,
                sketch: {
                    text: 'Learner rough sketch baseline.',
                    at: '2026-05-15T09:00:00.000Z',
                },
                node_records: {
                    'qa-node': {
                        attempts: [{
                            id: 'attempt-1',
                            kind: 'cold',
                            at: '2026-05-15T10:00:00.000Z',
                            user_text: 'Learner-owned reconstruction visible in Library.',
                            classification: 'strong',
                            gaps: [],
                            grader_version: 'qa',
                        }],
                        repairs: [],
                    },
                },
            }));
        })()"""
    )


def test_empty_library_is_compact_mobile_concept_index(
    clean_page: Page, base_url: str, captured
) -> None:
    """First-use Library stays quiet, truthful, and immediately actionable."""
    clean_page.set_viewport_size({"width": 390, "height": 844})
    _enter_app_shell_as_guest(clean_page, base_url)
    _wait_for_app_settled(clean_page)
    clean_page.evaluate(
        """(() => {
            localStorage.removeItem('learnops_concepts');
            window.App.showLibrary();
        })()"""
    )

    content = clean_page.locator("#library-content")
    expect(content.locator(".library-page-title")).to_have_text("Library")
    expect(content.locator(".library-index-title")).to_have_text("Concepts")
    expect(content.locator(".library-index-count")).to_have_text("0")
    expect(content.locator(".library-index-count")).to_have_attribute(
        "aria-label", "0 concepts"
    )
    expect(content.locator(".library-index-empty__title")).to_have_text(
        "Your first reconstruction starts here"
    )
    expect(content.locator(".library-index-empty__description")).to_have_text(
        "Write from memory. Your reconstruction will appear here."
    )
    expect(content.locator(".witness-anchor")).to_have_count(0)
    expect(content).not_to_contain_text("Your Library")
    expect(content).not_to_contain_text("Drop a topic")

    empty_index = content.locator(".library-section--empty")
    empty_box = empty_index.bounding_box()
    action = content.locator(".library-index-empty__action")
    action_box = action.bounding_box()
    bottom_nav_box = clean_page.locator("#bottom-nav").bounding_box()
    assert empty_box is not None
    assert action_box is not None
    assert bottom_nav_box is not None
    assert empty_box["height"] < 240
    assert round(action_box["height"]) >= 44
    assert empty_box["y"] + empty_box["height"] < bottom_nav_box["y"]
    assert clean_page.evaluate(
        "document.documentElement.scrollWidth <= window.innerWidth"
    )

    action.click()
    expect(clean_page.locator("#ignition-view")).to_be_visible()
    assert captured["console_errors"] == []
    assert captured["failed_requests"] == []


def test_library_card_uses_training_evidence_not_ai_summary(
    page: Page, base_url: str
) -> None:
    """Library summaries must be learner evidence, not generated source text."""
    page.set_viewport_size({"width": 390, "height": 844})
    _enter_app_shell_as_guest(page, base_url)
    page.evaluate("localStorage.clear(); sessionStorage.clear();")
    _seed_training_truth_concept(page)
    page.reload()
    _wait_for_app_settled(page)

    sidebar_dot = page.locator(".concept-item", has_text="Training Truth QA").locator(".concept-dot")
    expect(sidebar_dot).to_have_attribute("data-state", "primed")

    page.locator("#bn-library").click()
    card = page.locator(".library-card-vault", has_text="Training Truth QA")
    expect(card).to_be_visible()
    expect(card).to_have_attribute("data-state", "primed")
    expect(card.locator(".library-card-state")).to_have_text("primed for study")
    expect(card.locator(".library-card-summary")).to_have_text(
        "Learner-owned reconstruction visible in Library."
    )
    expect(card).not_to_contain_text("growing")
    expect(card).not_to_contain_text("AI GENERATED CORE THESIS SHOULD NOT APPEAR")
    expect(card).not_to_contain_text("SOURCE PREVIEW SHOULD NOT APPEAR")
    expect(card.locator(".library-card-kicker")).to_have_count(0)
    expect(card.locator(".library-card-meta")).to_have_count(0)
    expect(card.locator(".library-card-cta")).to_have_count(0)

    card_style = card.evaluate(
        """element => {
            const style = getComputedStyle(element);
            return {
                backgroundImage: style.backgroundImage,
                borderRadius: style.borderRadius,
                boxShadow: style.boxShadow,
            };
        }"""
    )
    assert card_style == {
        "backgroundImage": "none",
        "borderRadius": "0px",
        "boxShadow": "none",
    }
    card_box = card.bounding_box()
    assert card_box is not None
    assert card_box["height"] < 170
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")


def test_library_training_render_survives_one_corrupt_record(
    page: Page, base_url: str
) -> None:
    """One bad training record must not hide valid learner evidence elsewhere."""
    _enter_app_shell_as_guest(page, base_url)
    page.evaluate("localStorage.clear(); sessionStorage.clear();")
    _seed_training_truth_concept(page)
    page.evaluate(
        """(() => {
            const concepts = JSON.parse(localStorage.getItem('learnops_concepts'));
            concepts.push({
                id: 'qa-corrupt-library-training',
                name: 'Corrupt Training QA',
                createdAt: Date.now(),
                state: 'growing',
                graphData: JSON.stringify({
                    metadata: { source_title: 'Corrupt source' },
                    backbone: [],
                    clusters: [],
                }),
            });
            localStorage.setItem('learnops_concepts', JSON.stringify(concepts));
            localStorage.setItem(
                'socratink:training:v1:qa-corrupt-library-training',
                '{'
            );
        })()"""
    )

    page.locator("#nav-library").click()
    valid_card = page.locator(".library-card-vault", has_text="Training Truth QA")
    corrupt_card = page.locator(".library-card-vault", has_text="Corrupt Training QA")
    expect(valid_card.locator(".library-card-summary")).to_have_text(
        "Learner-owned reconstruction visible in Library."
    )
    expect(corrupt_card.locator(".library-card-summary")).to_have_text(
        "Your first reconstruction will appear here."
    )


def test_localhost_library_qa_seed_creates_training_truth_concept(
    page: Page, base_url: str
) -> None:
    """Localhost QA can seed a concept with learner-owned training evidence."""
    if not _is_loopback_base_url(base_url):
        pytest.skip("local QA seed controls are intentionally loopback-only")
    feedback_payloads = []
    _enter_app_shell_as_guest(page, base_url)
    page.evaluate("localStorage.clear(); sessionStorage.clear();")
    page.route(
        "**/api/feedback",
        lambda route: (
            feedback_payloads.append(route.request.post_data_json),
            route.fulfill(
                status=200,
                content_type="application/json",
                body='{"ok": true}',
            ),
        ),
    )

    page.evaluate("localStorage.setItem('socratink.localQaSeed', '1')")
    page.locator("#nav-library").click()
    page.locator("[data-local-qa-seed]").click()

    card = page.locator(".library-card-vault", has_text="Training Truth QA")
    expect(card).to_be_visible()
    expect(card.locator(".library-card-summary")).to_have_text(
        "Learner-owned reconstruction visible in Library."
    )
    expect(card).not_to_contain_text("AI GENERATED CORE THESIS SHOULD NOT APPEAR")
    expect(card).not_to_contain_text("SOURCE PREVIEW SHOULD NOT APPEAR")

    training = page.evaluate(
        """JSON.parse(localStorage.getItem('socratink:training:v1:local-qa-training-concept'))"""
    )
    assert training["source_mode"] == "source_less"
    assert training["grounding"] == "learner_sketch"
    assert training["sketch"]["text"] == "Learner rough sketch baseline."
    assert training["node_records"]["qa-node"]["attempts"][0]["classification"] == "strong"

    card.click()
    expect(page.locator("#concept-header-title")).to_contain_text("QA fixture source")
    expect(page.locator("#concept-header-tags .map-badge.state")).to_have_count(0)
    expect(page.locator(".concept-page-b2__context-dock")).to_have_count(0)
    expect(page.locator("#map-content")).not_to_contain_text(
        "Learner rough sketch baseline."
    )
    expect(page.locator(".concept-page-b2__entry-eyebrow")).to_have_text(
        "Your draft"
    )
    expect(page.locator(".concept-page-b2__entry-cta")).to_have_text(
        "Reveal notes and compare"
    )
    expect(page.locator(".concept-page-b2__evidence")).to_contain_text(
        "Learner-owned reconstruction visible in Library."
    )
    page.locator(".concept-page-b2__entry-cta").click()
    expect(page.locator(".concept-page-b2__evidence")).to_contain_text(
        "Learner-owned reconstruction visible in Library."
    )
    expect(page.locator(".concept-page-b2__evidence")).not_to_contain_text(
        "No missing piece recorded for this draft."
    )
    expect(page.locator(".concept-page-b2__study-note")).to_contain_text(
        "The revealed study note names the comparison target after the cold attempt: identify the mechanism, then mark any missing link for repair."
    )
    expect(page.locator(".concept-page-b2__entry-eyebrow")).to_have_text(
        "Compare notes"
    )
    expect(page.locator(".concept-page-b2__entry-cta")).to_have_text("Return to route")
    expect(page.locator("[data-feedback-rating]")).to_have_count(0)
    assert feedback_payloads == []
    revealed_training = page.evaluate(
        """JSON.parse(localStorage.getItem('socratink:training:v1:local-qa-training-concept'))"""
    )
    assert (
        revealed_training["node_records"]["qa-node"]["study_revealed_at"]
        is not None
    )


def test_localhost_library_qa_seed_controls_hide_when_storage_unavailable(
    page: Page, base_url: str
) -> None:
    """Local QA seed controls fail closed if browser storage is unavailable."""
    if not _is_loopback_base_url(base_url):
        pytest.skip("local QA seed controls are intentionally loopback-only")
    page.add_init_script(
        """
        Object.defineProperty(window, 'localStorage', {
          configurable: true,
          get() { throw new Error('localStorage unavailable'); }
        });
        """
    )

    _enter_app_shell_as_guest(page, base_url)
    page.locator("#nav-library").click()

    expect(page.locator("[data-local-qa-seed]")).to_have_count(0)


def test_legacy_primed_study_node_reveals_study_without_fabricating_evidence(
    page: Page, base_url: str
) -> None:
    """Legacy primed/study nodes keep study before another reconstruction."""
    drill_calls: list[dict] = []

    def fulfill_drill(route):
        payload = route.request.post_data_json
        drill_calls.append(payload)
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "agent_response": "Repair the missing legacy link.",
                    "generative_commitment": False,
                    "answer_mode": "attempt",
                    "score_eligible": True,
                    "help_request_reason": "none",
                    "classification": "shallow",
                    "gap_description": "Names the fact but misses the causal link.",
                    "routing": "NEXT",
                    "response_tier": 2,
                    "response_band": "link",
                    "tier_reason": "The answer needs the causal link.",
                    "node_id": payload["node_id"],
                    "probe_count": 0,
                    "nodes_drilled": 1,
                    "attempt_turn_count": 2,
                    "help_turn_count": 0,
                    "graph_mutated": False,
                    "ux_reward_emitted": False,
                    "session_terminated": False,
                    "termination_reason": None,
                    "prompt_version": "qa-legacy-study-redrill",
                }
            ),
        )

    page.route("**/api/drill", fulfill_drill)
    _enter_app_shell_as_guest(page, base_url)
    page.evaluate("localStorage.clear(); sessionStorage.clear();")
    checked_at = page.evaluate(
        """async () => {
          const { mergeTrainingRecords } = await import('/js/learner-state-sync.js');
          const merged = mergeTrainingRecords(
            { concept_id: 'checked', node_records: { n1: { repair_checked_at: '2026-07-08T11:00:00.000Z' } } },
            { concept_id: 'checked', node_records: { n1: {} } },
          );
          return merged.node_records.n1.repair_checked_at;
        }"""
    )
    assert checked_at == "2026-07-08T11:00:00.000Z"
    page.evaluate(
        """(() => {
            const graphData = JSON.stringify({
                metadata: {
                    core_thesis: 'Global generated thesis should stay hidden.',
                    source_title: 'Legacy Study QA',
                    starting_map_context: 'Legacy learner sketch.',
                },
                backbone: [{
                    id: 'legacy-node',
                    label: 'Legacy node',
                    purpose: 'Legacy purpose.',
                    study_note: 'Legacy study note should appear before another reconstruction.',
                    drill_status: 'primed',
                    drill_phase: 'study',
                }],
                clusters: [],
            });
            localStorage.setItem('learnops_concepts', JSON.stringify([{
                id: 'legacy-study-concept',
                name: 'Legacy Study QA',
                createdAt: Date.now(),
                state: 'growing',
                contentPreview: 'Global source preview should stay hidden.',
                graphData,
            }]));
        })()"""
    )

    page.locator("#nav-library").click()
    page.locator(".library-card-vault", has_text="Legacy Study QA").click()
    expect(page.locator(".concept-page-b2__entry-eyebrow")).to_have_text(
        "Your draft"
    )
    expect(page.locator(".concept-page-b2__entry-cta")).to_have_text(
        "Reveal notes and compare"
    )

    page.locator(".concept-page-b2__entry-cta").click()
    expect(page.locator(".concept-page-b2__study-note")).to_contain_text(
        "Legacy study note should appear before another reconstruction."
    )
    expect(page.locator(".concept-page-b2__evidence")).to_have_count(0)
    expect(page.locator(".concept-page-b2__entry-cta")).to_have_text(
        "Reconstruct from memory"
    )
    revealed_training = page.evaluate(
        """() => JSON.parse(localStorage.getItem('socratink:training:v1:legacy-study-concept'))"""
    )
    assert revealed_training["node_records"]["legacy-node"]["attempts"] == []
    assert (
        revealed_training["node_records"]["legacy-node"]["study_revealed_at"]
        is not None
    )

    page.locator(".concept-page-b2__entry-cta").click()
    page.locator(".concept-page-b2__attempt-input").fill(
        "The legacy fact happens, but I am missing why."
    )
    page.locator(".concept-page-b2__attempt-save").click()
    expect(page.locator(".concept-page-b2__entry-eyebrow")).to_have_text(
        "Needs repair"
    )
    assert len(drill_calls) == 1
    assert drill_calls[0]["drill_mode"] == "re_drill"
    stored = page.evaluate(
        """() => JSON.parse(localStorage.getItem('socratink:training:v1:legacy-study-concept'))"""
    )
    assert (
        stored["node_records"]["legacy-node"]["attempts"][0]["user_text"]
        == "The legacy fact happens, but I am missing why."
    )


def test_localhost_concept_repair_appends_learner_gap_work(
    page: Page, base_url: str
) -> None:
    """A studied thin attempt can append repair text without faking mastery."""
    if not _is_loopback_base_url(base_url):
        pytest.skip("local QA seed controls are intentionally loopback-only")
    drill_calls: list[dict] = []

    def fulfill_drill(route):
        payload = route.request.post_data_json
        drill_calls.append(payload)
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "agent_response": "That repair is coherent enough to move on. The entry is still evidence-neutral until spaced reconstruction.",
                    "generative_commitment": False,
                    "answer_mode": "attempt",
                    "score_eligible": True,
                    "classification": "solid",
                    "gap_description": None,
                    "routing": "NEXT",
                    "response_tier": 3,
                    "response_band": "mechanism",
                    "tier_reason": "The answer names the condition, action, and downstream change.",
                    "node_id": payload["node_id"],
                    "probe_count": 1,
                    "nodes_drilled": 1,
                    "attempt_turn_count": 1,
                    "help_turn_count": 0,
                    "graph_mutated": False,
                    "ux_reward_emitted": False,
                    "session_terminated": False,
                    "termination_reason": None,
                    "prompt_version": "qa-pressure-check-terminal",
                }
            ),
        )

    page.route("**/api/drill", fulfill_drill)
    _enter_app_shell_as_guest(page, base_url)
    page.evaluate("localStorage.clear(); sessionStorage.clear();")

    page.evaluate("localStorage.setItem('socratink.localQaSeed', '1')")
    page.locator("#nav-library").click()
    page.locator("[data-local-repair-qa-seed]").click()
    page.locator(".library-card-vault", has_text="Repair Truth QA").click()
    expect(page.locator("#concept-header-title")).to_contain_text("Repair QA source")
    expect(page.locator("#concept-header-tags")).not_to_contain_text("thin sketch")
    expect(page.locator(".concept-page-b2__context-dock")).to_have_count(0)
    expect(page.locator(".concept-page-b2__entry-eyebrow")).to_have_text(
        "Your draft"
    )
    expect(page.locator(".concept-page-b2__evidence")).to_contain_text(
        "Your memory draft"
    )
    expect(page.locator(".concept-page-b2__evidence")).to_contain_text(
        "Sodium rushes in because there is more sodium outside."
    )

    page.locator(".concept-page-b2__entry-cta").click()
    expect(page.locator(".concept-page-b2__entry-eyebrow")).to_have_text(
        "Compare notes"
    )
    expect(page.locator(".concept-page-b2__evidence")).not_to_contain_text(
        "Missing piece"
    )
    expect(page.locator(".concept-page-b2__study-note")).not_to_have_class(
        re.compile(r"is-collapsed")
    )
    expect(page.locator("[data-study-note-toggle]")).to_have_text("Hide study note")
    expect(page.locator(".concept-page-b2__repair")).to_be_hidden()
    expect(page.locator(".concept-page-b2__entry-cta")).to_have_text("Write the repair")
    page.locator(".concept-page-b2__entry-cta").click()
    expect(page.locator(".concept-page-b2__repair")).to_be_visible()
    expect(page.locator(".concept-page-b2__repair-input")).to_be_focused()
    expect(page.locator(".concept-page-b2__study-note")).to_have_class(
        re.compile(r"is-collapsed")
    )
    expect(page.locator(".concept-page-b2__repair")).to_contain_text(
        "Missing link"
    )
    expect(page.locator(".concept-page-b2__repair")).to_contain_text(
        "Name that threshold opens the channel"
    )
    repair_surface_style = page.locator(".concept-page-b2__repair").evaluate(
        """(el) => {
            const style = window.getComputedStyle(el);
            const labelStyle = window.getComputedStyle(el.querySelector('.concept-page-b2__repair-target span'));
            const saveStyle = window.getComputedStyle(el.querySelector('.concept-page-b2__repair-save'));
            return {
                backgroundColor: style.backgroundColor,
                borderLeftWidth: style.borderLeftWidth,
                borderTopWidth: style.borderTopWidth,
                labelTextTransform: labelStyle.textTransform,
                labelLetterSpacing: labelStyle.letterSpacing,
                saveMinHeight: saveStyle.minHeight,
            };
        }"""
    )
    assert repair_surface_style == {
        "backgroundColor": "rgba(0, 0, 0, 0)",
        "borderLeftWidth": "2px",
        "borderTopWidth": "0px",
        "labelTextTransform": "none",
        "labelLetterSpacing": "normal",
        "saveMinHeight": "44px",
    }
    expect(page.locator(".concept-page-b2__entry-cta")).to_be_hidden()

    page.locator(".concept-page-b2__repair-save").click()
    expect(page.locator("[data-repair-error]")).to_be_visible()
    expect(page.locator("[data-repair-error]")).to_have_text(
        "Write the missing link before saving."
    )
    page.evaluate(
        """(() => {
            window.__qaOriginalSetItem = Storage.prototype.setItem;
            Storage.prototype.setItem = function () { throw new Error('forced repair storage failure'); };
        })()"""
    )
    page.locator(".concept-page-b2__repair-input").fill(
        "This save should fail before persistence."
    )
    expect(page.locator(".concept-page-b2__study-note")).to_have_class(
        re.compile(r"is-collapsed")
    )
    expect(page.locator("[data-study-note-toggle]")).to_have_text("Show study note")
    page.locator("[data-study-note-toggle]").click()
    expect(page.locator(".concept-page-b2__study-note")).not_to_have_class(
        re.compile(r"is-collapsed")
    )
    expect(page.locator("[data-study-note-toggle]")).to_have_text("Hide study note")
    page.locator(".concept-page-b2__repair-save").click()
    expect(page.locator("[data-repair-error]")).to_have_text(
        "Repair could not be saved. Try again."
    )
    page.evaluate(
        """(() => {
            Storage.prototype.setItem = window.__qaOriginalSetItem;
            delete window.__qaOriginalSetItem;
        })()"""
    )
    page.locator(".concept-page-b2__repair-input").fill(
        "Threshold opens voltage-gated sodium channels; the gradient drives sodium flow only after that gate opens."
    )
    page.locator(".concept-page-b2__repair-save").click()
    expect(page.locator(".concept-post-repair__rail")).to_be_focused()
    expect(page.locator(".concept-constellation__shell--bridge")).to_be_visible()
    expect(page.locator(".concept-post-repair__truth")).to_contain_text(
        "Your map is unchanged."
    )
    expect(page.locator(".concept-post-repair__truth")).to_contain_text(
        "Reconstruct this link later to test it."
    )
    expect(page.locator(".concept-post-repair__primary")).to_have_text(
        "Enter this room"
    )
    expect(page.locator(".concept-post-repair__primary")).to_have_attribute(
        "aria-label", "Enter this room: Membrane depolarization"
    )
    expect(page.locator(".concept-post-repair__break")).to_have_text(
        "Take a short break"
    )
    page.evaluate(
        """(() => {
          const concepts = JSON.parse(localStorage.getItem('learnops_concepts') || '[]');
          const concept = concepts.find((item) => item.id === 'qa-repair-concept');
          const graph = JSON.parse(concept.graphData);
          graph.backbone.push({ id: 'peripheral-node', label: 'Peripheral room' });
          concept.graphData = JSON.stringify(graph);
          localStorage.setItem('learnops_concepts', JSON.stringify(concepts));
        })()"""
    )
    page.reload()
    expect(page.locator(".concept-constellation__shell--bridge")).to_be_visible()
    suggested_node = page.locator(
        '.concept-post-repair-host .concept-constellation__node[data-bridge-target="true"]'
    )
    expect(suggested_node).to_be_visible()
    expect(suggested_node).to_have_attribute("role", "button")
    expect(suggested_node).to_have_attribute("tabindex", "0")
    expect(suggested_node).to_have_attribute(
        "aria-label", re.compile(r"Membrane depolarization.*ready to reconstruct")
    )
    repaired_label_fill = page.locator(
        ".concept-post-repair-host .concept-constellation__node.is-active "
        ".concept-constellation__label"
    ).evaluate("el => getComputedStyle(el).fill")
    assert repaired_label_fill == "rgba(36, 32, 56, 0.84)"
    suggested_eyebrow_color = page.locator(
        ".concept-post-repair__next > .eyebrow"
    ).evaluate("el => getComputedStyle(el).color")
    assert suggested_eyebrow_color == "rgb(112, 82, 155)"
    expect(
        page.locator('.concept-post-repair-host [data-edge-recommendation="true"]')
    ).to_be_visible()
    expect(
        page.locator('.concept-post-repair-host [data-edge-evidence="true"]')
    ).to_have_count(0)
    assert page.evaluate("window.scrollY") == 0

    page.locator(".concept-post-repair__break").click()
    expect(page.locator(".hero-card")).to_be_visible()
    page.locator("#nav-library").click()
    page.locator(".library-card-vault", has_text="Repair Truth QA").click()
    expect(page.locator(".concept-constellation__shell--bridge")).to_be_visible()

    # A failed room load stays on the handoff instead of losing the route.
    page.evaluate(
        """(() => {
          window.__qaOriginalGetItem = Storage.prototype.getItem;
          Storage.prototype.getItem = function (key) {
            if (String(key).startsWith('socratink:training:v1:')) {
              throw new Error('forced room load failure');
            }
            return window.__qaOriginalGetItem.call(this, key);
          };
        })()"""
    )
    suggested_node = page.locator(
        '.concept-post-repair-host .concept-constellation__node[data-bridge-target="true"]'
    )
    suggested_node.dispatch_event("click")
    expect(page.locator(".concept-constellation__shell--bridge")).to_be_visible()
    page.evaluate(
        """(() => {
          Storage.prototype.getItem = window.__qaOriginalGetItem;
          delete window.__qaOriginalGetItem;
        })()"""
    )
    suggested_node.dispatch_event("click")
    expect(page.locator(".concept-page-b2__entry-title")).to_have_text(
        "Membrane depolarization"
    )
    expect(page.locator(".concept-page-b2__attempt-input")).to_be_focused()
    expect(page.locator(".concept-constellation__shell--bridge")).to_have_count(0)

    page.reload()
    expect(page.locator(".concept-constellation__shell--bridge")).to_be_visible()

    # The graph itself is keyboard-operable and routes to the genuinely ready room.
    suggested_node = page.locator(
        '.concept-post-repair-host .concept-constellation__node[data-bridge-target="true"]'
    )
    suggested_node.focus()
    suggested_node.press("Enter")
    expect(page.locator(".concept-page-b2__entry-title")).to_have_text(
        "Membrane depolarization"
    )
    expect(page.locator(".concept-page-b2__attempt-input")).to_be_focused()
    expect(page.locator(".concept-constellation__shell--bridge")).to_have_count(0)

    # Reload returns to the pending repair handoff; pressure-check remains
    # available through progressive disclosure.
    page.reload()
    expect(page.locator(".concept-constellation__shell--bridge")).to_be_visible()
    # The primary action routes by entry identity, not by proxy-clicking the
    # decorative graph node. Removing that rendering detail must not dead-end
    # the learner's main path.
    page.evaluate(
        "document.querySelector('.concept-post-repair-host [data-bridge-target=\"true\"]')?.remove()"
    )
    page.locator(".concept-post-repair__primary").click()
    expect(page.locator(".concept-page-b2__entry-title")).to_have_text(
        "Membrane depolarization"
    )
    expect(page.locator(".concept-page-b2__attempt-input")).to_be_focused()

    page.reload()
    expect(page.locator(".concept-constellation__shell--bridge")).to_be_visible()
    page.locator(".concept-post-repair__options summary").click()
    expect(
        page.locator('[data-post-repair-action="pressure-check"]')
    ).to_be_visible()
    page.locator('[data-post-repair-action="pressure-check"]').click()
    expect(page.locator("#drill-chamber-view")).to_be_visible()
    expect(page.locator(".concept-page-b2__entry-eyebrow")).to_have_text(
        "Reconstruction"
    )
    expect(page.locator("#chamber-send")).to_have_text("Check the link")
    expect(page.locator(".drill-chamber__hint")).to_have_text("One clear connection is enough.")
    expect(
        page.locator(".concept-page-b2__active-entry--drilling #drill-chamber-view")
    ).to_be_visible()
    expect(page.locator(".concept-page-b2__attempt-input")).to_have_count(0)
    page.locator("#chamber-composer").fill(
        "Threshold opens the channel, then sodium moves through because the gradient can act."
    )
    page.locator("#chamber-send").click()
    expect(page.locator("#chamber-send")).to_have_text("Return to concept")
    page.locator("#chamber-send").click()
    expect(page.locator("#drill-chamber-view")).to_have_count(0)
    expect(page.locator(".concept-page-b2__entry-eyebrow")).to_have_text(
        "Repair checked"
    )
    expect(page.locator(".concept-page-b2__repair")).to_contain_text(
        "Repair checked for now."
    )
    expect(page.locator(".concept-page-b2__repair")).to_contain_text(
        "A strong later answer can update the record."
    )
    expect(page.locator(".concept-page-b2__study-note")).to_contain_text(
        "Study note stays hidden for later reconstruction."
    )
    expect(page.locator(".concept-page-b2__study-note")).not_to_contain_text(
        "while you repair"
    )
    expect(page.locator("[data-feedback-rating]")).to_have_count(0)
    expect(page.locator(".concept-page-b2__entry-cta")).to_have_text("Continue route")
    assert "/session/qa-repair-concept" in page.url
    page.reload()
    expect(page.locator(".concept-page-b2__entry-eyebrow")).to_have_text(
        "Repair checked"
    )
    expect(page.locator(".concept-page-b2__repair")).to_contain_text(
        "Repair checked for now."
    )
    expect(page.locator(".concept-page-b2__entry-cta")).to_have_text("Continue route")
    assert drill_calls[0]["drill_mode"] == "re_drill"
    repaired_training = page.evaluate(
        """JSON.parse(localStorage.getItem('socratink:training:v1:qa-repair-concept'))"""
    )
    assert repaired_training["node_records"]["repair-node"]["repairs"][0]["text"] == (
        "Threshold opens voltage-gated sodium channels; the gradient drives sodium flow only after that gate opens."
    )
    assert repaired_training["node_records"]["repair-node"]["repair_checked_at"]
    assert (
        repaired_training["node_records"]["repair-node"]["attempts"][0]["classification"]
        == "thin"
    )


def test_launch_pad_accepts_any_non_empty_sketch(
    page: Page, base_url: str
) -> None:
    """The launch-pad affordance should enable any non-empty learner response."""
    page.set_viewport_size({"width": 390, "height": 844})
    _enter_app_shell_as_guest(page, base_url)
    page.wait_for_function("() => window.App?.showLaunchPad")
    page.evaluate(
        """(() => {
            sessionStorage.setItem('socratink:pendingShell', JSON.stringify({
                name: 'ADHD',
                ts: Date.now(),
            }));
            window.App.showLaunchPad();
        })()"""
    )

    expect(page.locator("#bottom-nav")).not_to_be_visible()
    expect(page.locator("#drawer-toggle")).to_be_visible()
    launch_pad_box = page.locator("#launch-pad-view").bounding_box()
    assert launch_pad_box is not None
    assert launch_pad_box["height"] >= 844
    expect(page.locator("#launch-pad-input")).to_have_attribute(
        "placeholder",
        "Name parts, guesses, examples, or confusions. Concrete words help most.",
    )
    page.locator("#launch-pad-input").fill("parts guesses confusion")
    expect(page.locator("#launch-pad-submit")).to_be_enabled()
    expect(page.locator("#launch-pad-validation")).to_have_text("")

    page.locator("#launch-pad-input").fill("")
    expect(page.locator("#launch-pad-submit")).to_be_disabled()
    expect(page.locator("#launch-pad-validation")).to_have_text("")
    page.evaluate(
        """() => window.App.runLaunchPadAction({ preventDefault() {} })"""
    )
    expect(page.locator("#launch-pad-validation")).to_have_text(
        "Write anything you think about the concept before building the draft."
    )

    def fulfill_missing_sketch(route):
        route.fulfill(
            status=422,
            content_type="application/json",
            body=json.dumps({"detail": {"error": "missing_sketch"}}),
        )

    page.route("**/api/extract", fulfill_missing_sketch)
    page.locator("#launch-pad-input").fill("idk")
    expect(page.locator("#launch-pad-submit")).to_be_enabled()
    expect(page.locator("#launch-pad-validation")).to_have_text("")
    page.locator("#launch-pad-submit").click()
    expect(page.locator("#launch-pad-validation")).to_have_text(
        "Write anything you think about the concept before building the draft."
    )


def test_launch_pad_persistence_failure_is_retryable(
    page: Page, base_url: str
) -> None:
    """Board-capacity persistence failure leaves the launch sketch retryable."""
    _enter_app_shell_as_guest(page, base_url)
    page.wait_for_function("() => window.App?.showLaunchPad")

    def fulfill_extract(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "provisional_map": {
                    "metadata": {},
                    "backbone": [{"id": "b1", "principle": "First model", "dependent_clusters": []}],
                    "clusters": [],
                    "relationships": {"domain_mechanics": [], "learning_prerequisites": []},
                    "frameworks": [],
                },
            }),
        )

    page.route("**/api/extract", fulfill_extract)
    page.evaluate(
        """(() => {
            const concepts = Array.from({ length: 9 }, (_, index) => ({
                id: `full-board-${index}`,
                name: `Full board ${index + 1}`,
                graphData: JSON.stringify({ metadata: {}, backbone: [], clusters: [] }),
                createdAt: new Date().toISOString(),
            }));
            localStorage.setItem('learnops_concepts', JSON.stringify(concepts));
            sessionStorage.setItem('socratink:pendingShell', JSON.stringify({
                name: 'Persistence failure',
                goal: '',
                ts: Date.now(),
            }));
            window.App.showLaunchPad();
        })()"""
    )

    page.locator("#launch-pad-input").fill("My rough first model.")
    page.locator("#launch-pad-submit").click()

    expect(page.locator("#launch-pad-validation")).to_have_text(
        "The board holds nine concepts. Retire one in your library to start another."
    )
    assert page.evaluate("sessionStorage.getItem('socratink:pendingShell') !== null")


def test_start_learning_enters_seda_loop_from_product_flow(
    page: Page, base_url: str
) -> None:
    """Start learning should open the product chamber backed by /api/session."""
    _enter_app_shell_as_guest(page, base_url)
    resume_drill_requests: list[str] = []

    def remember_resume_drill(request) -> None:
        if request.method == "POST" and request.url.endswith("/api/drill"):
            resume_drill_requests.append(request.url)

    def fulfill_extract(route) -> None:
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "provisional_map": {
                    "metadata": {
                        "core_thesis": "Vaccines leave immune memory that speeds later response.",
                        "learner_goal": "Explain why a second exposure is faster.",
                    },
                    "backbone": [{
                        "id": "b1",
                        "principle": "Immune memory makes later response faster.",
                        "dependent_clusters": ["c1"],
                    }],
                    "clusters": [{
                        "id": "c1",
                        "label": "Memory cells",
                        "description": "Memory B and T cells persist after exposure.",
                        "subnodes": [{
                            "id": "c1_s1",
                            "label": "Memory cells",
                            "mechanism": "Memory cells persist after first exposure and respond faster later.",
                            "learner_scaffold": {
                                "entry_prompt": "Why is the second exposure faster?",
                                "task_cue": "Explain the role of memory cells.",
                            },
                        }, {
                            "id": "c1_s2",
                            "label": "Memory persistence",
                            "mechanism": "Memory cells stay available after the first exposure.",
                            "learner_scaffold": {
                                "entry_prompt": "What persists after the first exposure?",
                                "task_cue": "Name what remains available.",
                            },
                        }],
                    }],
                },
            }),
        )

    page.route("**/api/extract", fulfill_extract)
    page.locator("#nav-ignition").click()
    page.locator("#hero-single-input-field").fill(
        "I want to explain why vaccines create immune memory."
    )
    page.locator("#hero-cold-guess-field").fill(
        "The first exposure leaves cells that remember the pathogen."
    )
    expect(page.locator("#launch-pad-view")).to_be_hidden()
    page.locator("#hero-door-submit").click()

    expect(page.locator("#drill-chamber-view")).to_be_visible(timeout=20_000)
    expect(page.locator("#chamber-question")).not_to_have_text("—", timeout=20_000)
    state = page.wait_for_function(
        """() => {
          const conceptId = localStorage.getItem('learnops_active');
          const key = conceptId ? `socratink:seda-session:v1:${conceptId}` : null;
          if (!key) return null;
          const value = JSON.parse(localStorage.getItem(key));
          return value?.sessionId && value?.latest?.awaiting?.key === 'cold_attempt'
            ? value
            : null;
        }""",
        timeout=45_000,
    ).json_value()
    assert state["sessionId"]
    assert state["latest"]["awaiting"]["key"] == "cold_attempt"
    bound_study_note = page.evaluate(
        """(nodeId) => {
          const conceptId = localStorage.getItem('learnops_active');
          const concept = JSON.parse(localStorage.getItem('learnops_concepts') || '[]')
            .find((item) => item.id === conceptId);
          const graph = JSON.parse(concept?.graphData || 'null');
          const nodes = [
            ...(graph?.backbone || []),
            ...(graph?.clusters || []).flatMap((cluster) => cluster?.subnodes || []),
          ];
          const node = nodes.find((item) => item?.id === nodeId);
          return node?.study_note || node?.mechanism || '';
        }""",
        state["nodeId"],
    )
    assert bound_study_note
    page.locator("#chamber-send").click()
    expect(page.locator("#chamber-hint")).to_have_text(
        "Write a sentence before checking."
    )
    page.locator("#chamber-composer").fill(
        "Memory cells remain after the first exposure and make the second response faster."
    )
    expect(page.locator("#chamber-hint")).to_have_text("A sentence is enough.")
    page.locator("#chamber-send").click()
    advanced_state = page.wait_for_function(
        """() => {
          const conceptId = localStorage.getItem('learnops_active');
          const key = conceptId ? `socratink:seda-session:v1:${conceptId}` : null;
          if (!key) return null;
          const value = JSON.parse(localStorage.getItem(key));
          return value?.latest?.awaiting?.key !== 'cold_attempt' ? value : null;
        }""",
        timeout=45_000,
    ).json_value()
    assert advanced_state["sessionId"] == state["sessionId"]
    page.locator("#chamber-exit").click()
    expect(page.locator("#drill-chamber-view")).to_be_hidden()
    page.evaluate(
        """window.App.reopenStudy({
          id: 'c1_s1',
          label: 'Memory cells',
          fullLabel: 'Memory cells',
        })"""
    )
    expect(page.locator("#drill-chamber-view")).to_be_visible(timeout=20_000)
    reopened_state = page.wait_for_function(
        """() => {
          const conceptId = localStorage.getItem('learnops_active');
          const key = conceptId ? `socratink:seda-session:v1:${conceptId}` : null;
          if (!key) return null;
          const value = JSON.parse(localStorage.getItem(key));
          return value?.sessionId ? value : null;
        }""",
        timeout=20_000,
    ).json_value()
    assert reopened_state["sessionId"] == state["sessionId"]
    page.locator("#chamber-exit").click()
    page.evaluate(
        """window.App.reopenStudy({
          id: 'c1_s2',
          label: 'Memory persistence',
          fullLabel: 'Memory persistence',
          learner_scaffold: {
            entry_prompt: 'What persists after the first exposure?',
            task_cue: 'Name what remains available.',
          },
        })"""
    )
    expect(page.locator("#drill-chamber-view")).to_be_visible(timeout=20_000)
    expect(page.locator("#chamber-question")).to_have_text(
        "This learning route cannot be resumed. Your recorded work is still on the map.",
        timeout=20_000,
    )
    expect(page.locator("#chamber-send")).to_have_text("Return to map")
    different_node_state = page.wait_for_function(
        """() => {
          const conceptId = localStorage.getItem('learnops_active');
          const key = conceptId ? `socratink:seda-session:v1:${conceptId}` : null;
          if (!key) return null;
          const value = JSON.parse(localStorage.getItem(key));
          return value?.nodeId === 'c1_s1' && value?.sessionId ? value : null;
        }""",
        timeout=20_000,
    ).json_value()
    assert different_node_state["sessionId"] == state["sessionId"]
    page.locator("#chamber-send").click()
    page.reload()
    persisted_attempt = page.wait_for_function(
        """() => {
          const conceptId = localStorage.getItem('learnops_active');
          const key = conceptId ? `socratink:training:v1:${conceptId}` : null;
          if (!key) return null;
          const training = JSON.parse(localStorage.getItem(key) || 'null');
          return training?.node_records?.c1_s1?.attempts?.[0] || null;
        }""",
        timeout=20_000,
    ).json_value()
    assert persisted_attempt["user_text"] == (
        "Memory cells remain after the first exposure and make the second response faster."
    )
    expect(page.locator(".concept-page-b2__entry-cta")).to_have_text(
        "Reveal notes and compare", timeout=20_000
    )
    page.on("request", remember_resume_drill)
    page.locator(".concept-page-b2__entry-cta").click()
    expect(page.locator(".concept-page-b2__study-note")).to_contain_text(
        bound_study_note,
        timeout=20_000,
    )
    assert resume_drill_requests == []
    expect(page.locator("#nav-loop")).to_have_count(0)


def _seda_route_event(
    *,
    node_id: str = "c1_s1",
    label: str = "Memory cells",
    prompt: str = "Why is the second exposure faster?",
    mechanism: str = "Memory cells persist after exposure.",
) -> dict:
    """Small valid route event for source-less SEDA browser stubs."""
    cluster_id = node_id.split("_s", 1)[0]
    return {
        "type": "route_generated",
        "first_node": {
            "id": node_id,
            "kc_id": node_id,
            "label": label,
            "mechanism": mechanism,
            "learner_prompt": prompt,
            "evidence_goal": "Explain one causal link from memory.",
        },
        "node_ids": [node_id],
        "provisional_map": {
            "metadata": {"core_thesis": f"{label} changes the later response."},
            "backbone": [{"id": "b-route", "principle": "A retained change affects a later response."}],
            "clusters": [{
                "id": cluster_id,
                "label": label,
                "subnodes": [{"id": node_id, "label": label}],
            }],
        },
    }


def _seda_route_result(**kwargs) -> dict:
    """Versioned app-facing route result; raw events are audit-only."""
    event = _seda_route_event(**kwargs)
    return {
        "contractVersion": 1,
        "status": "ready",
        "firstNode": event["first_node"],
        "provisionalMap": event["provisional_map"],
    }


def test_source_less_first_chamber_answer_shows_verdict_and_study_cta(
    clean_page: Page, base_url: str
) -> None:
    """The real chamber carries one SEDA case through the nested learner loop."""
    page = clean_page
    _enter_app_shell_as_guest(page, base_url)

    def fulfill_extract(route) -> None:
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "provisional_map": {
                    "metadata": {"core_thesis": "Immune memory speeds the next response."},
                    "backbone": [{"id": "b1", "principle": "Immune memory persists."}],
                    "clusters": [{
                        "id": "c1",
                        "label": "Memory cells",
                        "subnodes": [{
                            "id": "c1_s1",
                            "label": "Memory cells",
                            "mechanism": "Door mechanism A should be replaced.",
                            "learner_scaffold": {
                                "entry_prompt": "Door prompt A should be replaced.",
                                "task_cue": "Explain the role of memory cells.",
                            },
                        }],
                    }],
                },
            }),
        )

    def fulfill_session(route) -> None:
        route.fulfill(
            status=201,
            content_type="application/json",
            body=json.dumps({
                "sessionId": "mid-loop-session",
                "sessionVersion": 1,
                "status": "awaiting_input",
                "awaiting": {"key": "launch_attempt", "ctaText": "Try your first explanation."},
                "learnerTranscript": [],
                "caseComplete": False,
                "record": None,
            }),
        )

    door_sketch = "The first exposure leaves memory cells."
    room_answer = (
        "Memory cells remain after the first exposure and make the second response faster."
    )
    repair_answer = "The retained cells recognize the antigen and activate sooner."
    transfer_answer = "A saved pattern can make a later matching response start sooner."
    routed_prompt = "Route prompt B: why does the later response happen faster?"
    routed_mechanism = (
        "Route mechanism B: memory cells persist and activate sooner on re-exposure."
    )
    turn_texts: list[str] = []
    turn_payloads: list[dict] = []

    def fulfill_turn(route) -> None:
        turn_payloads.append(route.request.post_data_json)
        turn_texts.append(route.request.post_data_json["text"])
        if len(turn_texts) == 1:
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({
                    "sessionId": "mid-loop-session",
                    "sessionVersion": 2,
                    "status": "awaiting_input",
                    "awaiting": {
                        "key": "cold_attempt",
                        "ctaText": "Why is the second exposure faster?",
                    },
                    "learnerTranscript": [],
                    "events": [_seda_route_event(
                        node_id="c9_s1",
                        label="Routed memory target",
                        prompt=routed_prompt,
                        mechanism=routed_mechanism,
                    )],
                    "sourceLessRoute": _seda_route_result(
                        node_id="c9_s1",
                        label="Routed memory target",
                        prompt=routed_prompt,
                        mechanism=routed_mechanism,
                    ),
                    "caseComplete": False,
                    "record": None,
                }),
            )
            return
        route_event = _seda_route_event(
            node_id="c9_s1", label="Routed memory target",
            prompt=routed_prompt, mechanism=routed_mechanism,
        )
        cold_event = {
            "type": "cold_attempt", "kc_id": "c9_s1", "text": room_answer,
            "evaluation": {
                "classification": "deep",
                "agent_response": (
                    "You connected memory cells to the faster response, "
                    "but not why they react sooner."
                ),
                "gap_description": "Name why memory cells respond faster.",
                "grader_version": "qa",
            },
        }
        gap_event = {
            "type": "gap_identified", "graph_neutral": True,
            "repair_scaffold": {
                "socratic_question": "What lets the retained cells react sooner?",
            },
            "gap_log": {"missing_operation": "recognition triggers faster activation"},
        }
        repair_turn = {
            "type": "repair_dialogue_turn", "text": repair_answer,
            "bridge_ready": True, "graph_neutral": True, "score_eligible": False,
        }
        repair_event = {"type": "repair", "text": repair_answer, "graph_neutral": True}
        bridge_event = {"type": "model_bridge", "text": routed_mechanism, "graph_neutral": True}
        decision_event = {
            "type": "post_bridge_transfer_decision", "run_gap": True,
            "graph_neutral": True, "score_eligible": False,
        }
        transfer_event = {
            "type": "post_bridge_transfer_check", "text": transfer_answer,
            "graph_neutral": True, "score_eligible": False,
            "evaluation": {"classification": "deep"},
        }
        turns = {
            2: ({"key": "continue", "ctaText": cold_event["evaluation"]["agent_response"]}, [route_event, cold_event]),
            3: ({"key": "repair", "ctaText": gap_event["repair_scaffold"]["socratic_question"]}, [route_event, cold_event, gap_event]),
            4: ({"key": "continue", "ctaText": "Continue."}, [route_event, cold_event, gap_event, repair_turn, repair_event]),
            5: ({"key": "run_gap_drill", "ctaText": "Try using it somewhere new?"}, [route_event, cold_event, gap_event, repair_turn, repair_event, bridge_event]),
            6: ({"key": "gap_attempt", "ctaText": "Use it somewhere new."}, [route_event, cold_event, gap_event, repair_turn, repair_event, bridge_event, decision_event]),
            7: ({"key": "spaced_attempt", "ctaText": "From memory, explain it again."}, [route_event, cold_event, gap_event, repair_turn, repair_event, bridge_event, decision_event, transfer_event]),
        }
        awaiting, events = turns[len(turn_texts)]
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "sessionId": "mid-loop-session",
                "sessionVersion": len(turn_texts) + 1,
                "status": "awaiting_input",
                "awaiting": awaiting,
                "learnerTranscript": [],
                "events": events,
                "caseComplete": False,
                "record": None,
            }),
        )

    page.route("**/api/extract", fulfill_extract)
    page.route(re.compile(r".*/api/session$"), fulfill_session)
    page.route(
        re.compile(r".*/api/session/mid-loop-session/turn$"),
        fulfill_turn,
    )
    page.evaluate(
        """() => {
          window.__sedaQuestionHistory = [];
          const remember = () => {
            const question = document.getElementById('chamber-question');
            const value = question?.textContent?.trim();
            if (value) window.__sedaQuestionHistory.push(value);
          };
          new MutationObserver(remember).observe(document.body, {
            childList: true, characterData: true, subtree: true,
          });
          remember();
        }"""
    )
    page.locator("#nav-ignition").click()
    page.locator("#hero-single-input-field").fill("why vaccines create immune memory")
    page.locator("#hero-cold-guess-field").fill(door_sketch)
    page.locator("#hero-door-submit").click()

    expect(page.locator("#drill-chamber-view")).to_be_visible(timeout=20_000)
    page.wait_for_function(
        """() => {
          const conceptId = localStorage.getItem('learnops_active');
          const key = conceptId ? `socratink:seda-session:v1:${conceptId}` : null;
          if (!key) return false;
          const value = JSON.parse(localStorage.getItem(key) || 'null');
          if (value?.sessionId !== 'mid-loop-session'
            || value?.latest?.awaiting?.key !== 'cold_attempt'
            || value?.nodeId !== 'c9_s1') return false;
          const concept = JSON.parse(localStorage.getItem('learnops_concepts') || '[]')
            .find((item) => item.id === conceptId);
          const graph = JSON.parse(concept?.graphData || 'null');
          return graph?.clusters?.[0]?.subnodes?.[0]?.id === 'c9_s1';
        }""",
        timeout=20_000,
    )
    assert turn_texts == [door_sketch]
    bootstrap_attempts = page.evaluate(
        """() => {
          const conceptId = localStorage.getItem('learnops_active');
          const key = conceptId ? `socratink:training:v1:${conceptId}` : null;
          const training = key ? JSON.parse(localStorage.getItem(key) || 'null') : null;
          return Object.values(training?.node_records || {})
            .flatMap((record) => record?.attempts || []).length;
        }"""
    )
    assert bootstrap_attempts == 0
    expect(page.locator("#chamber-question")).to_have_text(
        routed_prompt
    )
    question_history = page.evaluate("window.__sedaQuestionHistory")
    assert "Preparing your first question…" in question_history
    assert "Door prompt A should be replaced." not in question_history
    expect(page.locator("#chamber-entry-name")).to_have_text("Routed memory target")
    page.locator("#chamber-composer").fill(room_answer)
    expect(page.locator("#chamber-send")).to_be_enabled()
    page.locator("#chamber-composer").press("Control+Enter")
    expect(page.locator("#chamber-verdict")).to_have_text(
        re.compile(r"Checked.*Partly there"), timeout=2_000
    )
    expect(page.locator("#chamber-verdict")).not_to_contain_text(
        "You connected memory cells to the faster response, but not why they react sooner."
    )
    expect(page.locator("#chamber-send")).to_have_text("Work this link")
    expect(page.locator("#chamber-composer")).to_be_disabled()
    expect(page.locator("#chamber-question")).to_contain_text("not why they react sooner")
    assert turn_texts == [door_sketch, room_answer]
    assert [payload["expectedVersion"] for payload in turn_payloads] == [1, 2]
    projected = page.wait_for_function(
        """() => {
          const conceptId = localStorage.getItem('learnops_active');
          const key = conceptId ? `socratink:training:v1:${conceptId}` : null;
          if (!key) return null;
          const value = JSON.parse(localStorage.getItem(key) || 'null');
          const record = value?.node_records?.c9_s1;
          return record?.attempts?.length ? record.attempts[0] : null;
        }""",
        timeout=20_000,
    ).json_value()
    assert projected["classification"] == "partial"
    assert projected["kind"] == "cold"
    assert projected["gaps"] == [{
        "mechanism": "target mechanism",
        "correction": "Name why memory cells respond faster.",
    }]
    assert page.evaluate(
        """() => {
          const conceptId = localStorage.getItem('learnops_active');
          const key = `socratink:training:v1:${conceptId}`;
          const training = JSON.parse(localStorage.getItem(key) || 'null');
          return Boolean(training?.node_records?.c1_s1);
        }"""
    ) is False
    page.locator("#chamber-send").click()
    expect(page.locator("#drill-chamber-view")).to_have_attribute("data-loop-surface", "repair")
    expect(page.locator("#chamber-anchor-text")).to_have_text(room_answer)
    expect(page.locator("#chamber-question")).to_have_text("What lets the retained cells react sooner?")
    page.locator("#chamber-composer").fill(repair_answer)
    page.locator("#chamber-send").click()
    expect(page.locator("#drill-chamber-view")).to_have_attribute("data-loop-surface", "repair-ready")
    expect(page.locator("#chamber-anchor-label")).to_have_text("Your repair")
    expect(page.locator("#chamber-anchor-text")).to_have_text(repair_answer)
    expect(page.locator("#chamber-send")).to_have_text("See the connection")
    page.locator("#chamber-send").click()
    expect(page.locator("#drill-chamber-view")).to_have_attribute("data-loop-surface", "bridge")
    expect(page.locator("#chamber-anchor-label")).to_have_text("Your repair")
    expect(page.locator("#chamber-anchor-text")).to_have_text(repair_answer)
    expect(page.locator("#chamber-bridge-text")).to_have_text(routed_mechanism)
    page.locator("#chamber-send").click()
    expect(page.locator("#drill-chamber-view")).to_have_attribute("data-loop-surface", "transfer")
    expect(page.locator("#chamber-bridge")).to_be_hidden()
    page.locator("#chamber-composer").fill(transfer_answer)
    page.locator("#chamber-send").click()
    expect(page.locator("#drill-chamber-view")).to_have_attribute("data-loop-surface", "settle")
    expect(page.locator("#chamber-send")).to_have_text("Return to concept")
    page.locator("#chamber-send").click()
    expect(page.locator("#drill-chamber-view")).to_have_count(0)
    assert turn_texts == [
        door_sketch, room_answer, "continue", repair_answer, "continue", "y", transfer_answer,
    ]
    evidence = page.evaluate(
        """() => {
          const conceptId = localStorage.getItem('learnops_active');
          const training = JSON.parse(localStorage.getItem(`socratink:training:v1:${conceptId}`));
          return training.node_records.c9_s1;
        }"""
    )
    assert len(evidence["attempts"]) == 1
    assert [repair["text"] for repair in evidence["repairs"]] == [repair_answer]
    assert evidence["study_revealed_at"]


def test_late_source_less_route_cannot_overwrite_a_newly_selected_concept(
    clean_page: Page, base_url: str
) -> None:
    """A delayed route is discarded after exit instead of mutating active state."""
    page = clean_page
    _enter_app_shell_as_guest(page, base_url)
    page.evaluate(
        """() => {
          const safeGraph = {
            metadata: { core_thesis: 'Keep this graph unchanged.', sentinel: 'safe' },
            backbone: [{ id: 'b1', principle: 'Safe principle', dependent_clusters: ['c1'] }],
            clusters: [{
              id: 'c1', label: 'Safe cluster', description: 'Safe description',
              subnodes: [{ id: 'c1_s1', label: 'Safe node', mechanism: 'Safe mechanism.' }],
            }],
            relationships: { domain_mechanics: [], learning_prerequisites: [] },
            frameworks: [],
          };
          localStorage.setItem('learnops_concepts', JSON.stringify([{
            id: 'safe-concept', name: 'Safe concept', createdAt: Date.now(),
            state: 'growing', graphData: JSON.stringify(safeGraph),
          }]));
          localStorage.setItem('learnops_active', 'safe-concept');
        }"""
    )

    page.route(
        "**/api/extract",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "route_owner": "seda",
                "provisional_map": {
                    "metadata": {
                        "core_thesis": "Pending source-less shell.",
                        "route_status": "pending_seda",
                        "graph_neutral": True,
                    },
                    "backbone": [{
                        "id": "b1", "principle": "Pending shell",
                        "dependent_clusters": ["c1"],
                    }],
                    "clusters": [{
                        "id": "c1", "label": "Pending", "description": "Pending",
                        "subnodes": [{
                            "id": "c1_s1", "label": "Pending",
                            "mechanism": "Learner sketch only.",
                            "learner_scaffold": {"entry_prompt": "Provisional prompt must stay hidden."},
                        }],
                    }],
                    "relationships": {"domain_mechanics": [], "learning_prerequisites": []},
                    "frameworks": [],
                },
            }),
        ),
    )
    session_id = "66666666-6666-4666-8666-666666666666"
    page.route(
        re.compile(r".*/api/session$"),
        lambda route: route.fulfill(
            status=201,
            content_type="application/json",
            body=json.dumps({
                "sessionId": session_id,
                "sessionVersion": 1,
                "status": "awaiting_input",
                "awaiting": {"key": "launch_attempt", "ctaText": "First try"},
                "caseComplete": False,
            }),
        ),
    )
    held_turns = []
    page.route(
        re.compile(rf".*/api/session/{session_id}/turn$"),
        lambda route: held_turns.append(route),
    )

    page.locator("#nav-ignition").click()
    page.locator("#hero-single-input-field").fill("why immune memory persists")
    page.locator("#hero-cold-guess-field").fill(
        "The first exposure leaves something ready for the next one."
    )
    page.locator("#hero-door-submit").click()
    expect(page.locator("#chamber-question")).to_have_text(
        "Preparing your first question…", timeout=20_000
    )
    for _ in range(100):
        if held_turns:
            break
        page.wait_for_timeout(50)
    assert held_turns, "bootstrap turn never reached the held route"
    source_concept_id = page.evaluate("localStorage.getItem('learnops_active')")
    assert source_concept_id != "safe-concept"

    page.locator("#chamber-exit").click()
    page.evaluate("window.App.selectConcept('safe-concept')")
    expect(page.locator("#drill-chamber-view")).to_be_hidden()
    held_turns[0].fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({
            "sessionId": session_id,
            "sessionVersion": 2,
            "status": "awaiting_input",
            "awaiting": {"key": "cold_attempt", "ctaText": "Authoritative prompt"},
            "sourceLessRoute": _seda_route_result(
                node_id="route-node", prompt="Authoritative prompt",
            ),
            "events": [_seda_route_event(
                node_id="route-node", prompt="Authoritative prompt",
            )],
            "caseComplete": False,
        }),
    )
    page.wait_for_timeout(300)

    snapshot = page.evaluate(
        """(sourceId) => {
          const concepts = JSON.parse(localStorage.getItem('learnops_concepts') || '[]');
          const safe = concepts.find((concept) => concept.id === 'safe-concept');
          const source = concepts.find((concept) => concept.id === sourceId);
          const safeGraph = JSON.parse(safe.graphData);
          const sourceGraph = JSON.parse(source.graphData);
          return {
            activeId: localStorage.getItem('learnops_active'),
            safeSentinel: safeGraph.metadata.sentinel,
            safeBoundNode: safeGraph.metadata.seda_route_bound_node_id || null,
            sourceBoundNode: sourceGraph.metadata.seda_route_bound_node_id || null,
            sourceSession: localStorage.getItem(`socratink:seda-session:v1:${sourceId}`),
          };
        }""",
        source_concept_id,
    )
    assert snapshot == {
        "activeId": "safe-concept",
        "safeSentinel": "safe",
        "safeBoundNode": None,
        "sourceBoundNode": None,
        "sourceSession": None,
    }

    normal_drill_requests: list[dict] = []

    def reject_normal_drill(route) -> None:
        normal_drill_requests.append(route.request.post_data_json)
        route.fulfill(
            status=500,
            content_type="application/json",
            body=json.dumps({"error": "placeholder_shell_must_not_drill"}),
        )

    page.route("**/api/drill", reject_normal_drill)
    page.goto(f"{base_url}/session/{source_concept_id}")
    draft_after_reload = "This draft was written against the saved shell."
    expect(page.locator(".concept-page-b2__attempt-input")).to_be_visible(
        timeout=20_000
    )
    page.locator(".concept-page-b2__attempt-input").fill(draft_after_reload)
    page.locator(".concept-page-b2__attempt-save").click()
    expect(page.locator("#chamber-question")).to_have_text(
        "Preparing your first question…", timeout=20_000
    )
    for _ in range(100):
        if len(held_turns) >= 2:
            break
        page.wait_for_timeout(50)
    assert len(held_turns) == 2
    assert normal_drill_requests == []
    assert held_turns[1].request.post_data_json["text"] == (
        "The first exposure leaves something ready for the next one."
    )

    held_turns[1].fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({
            "sessionId": session_id,
            "sessionVersion": 2,
            "status": "awaiting_input",
            "awaiting": {"key": "cold_attempt", "ctaText": "Recovered route prompt"},
            "sourceLessRoute": _seda_route_result(
                node_id="route-node", prompt="Recovered route prompt",
            ),
            "events": [_seda_route_event(
                node_id="route-node", prompt="Recovered route prompt",
            )],
            "caseComplete": False,
        }),
    )
    expect(page.locator("#chamber-question")).to_have_text(
        "Recovered route prompt", timeout=20_000
    )
    expect(page.locator("#chamber-composer")).to_have_value(draft_after_reload)
    expect(page.locator("#chamber-verdict")).to_contain_text(
        "Not recorded against this question."
    )
    recovered = page.evaluate(
        """(sourceId) => {
          const concept = JSON.parse(localStorage.getItem('learnops_concepts') || '[]')
            .find((item) => item.id === sourceId);
          const graph = JSON.parse(concept.graphData);
          const training = JSON.parse(
            localStorage.getItem(`socratink:training:v1:${sourceId}`) || 'null'
          );
          return {
            boundNode: graph.metadata.seda_route_bound_node_id,
            attempts: Object.values(training?.node_records || {})
              .flatMap((record) => record.attempts || []).length,
          };
        }""",
        source_concept_id,
    )
    assert recovered == {"boundNode": "route-node", "attempts": 0}


def test_seda_support_turn_is_neutral_and_records_no_evidence(
    clean_page: Page, base_url: str
) -> None:
    """A support turn stays graph-neutral and returns to a new prompt."""
    page = clean_page
    _enter_app_shell_as_guest(page, base_url)

    def fulfill_extract(route) -> None:
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "provisional_map": {
                    "metadata": {"core_thesis": "Immune memory speeds later response."},
                    "backbone": [{
                        "id": "b1",
                        "principle": "Immune memory persists.",
                        "learner_scaffold": {
                            "entry_prompt": "Why is the second exposure faster?",
                            "task_cue": "Explain one causal link.",
                        },
                    }],
                    "clusters": [],
                },
            }),
        )

    def fulfill_session(route) -> None:
        route.fulfill(
            status=201,
            content_type="application/json",
            body=json.dumps({
                "sessionId": "support-turn-session",
                "sessionVersion": 1,
                "status": "awaiting_input",
                "awaiting": {"key": "launch_attempt", "ctaText": "Try your first explanation."},
                "learnerTranscript": [],
                "caseComplete": False,
                "record": None,
            }),
        )

    door_sketch = "The first exposure leaves memory cells."
    support_text = "I need one more cue."
    turn_texts: list[str] = []
    turn_payloads: list[dict] = []

    def fulfill_turn(route) -> None:
        turn_payloads.append(route.request.post_data_json)
        turn_texts.append(route.request.post_data_json["text"])
        if len(turn_texts) == 1:
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({
                    "sessionId": "support-turn-session",
                    "sessionVersion": 2,
                    "status": "awaiting_input",
                    "awaiting": {
                        "key": "cold_attempt",
                        "ctaText": "Why is the second exposure faster?",
                    },
                    "learnerTranscript": [],
                    "events": [_seda_route_event()],
                    "sourceLessRoute": _seda_route_result(),
                    "caseComplete": False,
                    "record": None,
                }),
            )
            return
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "sessionId": "support-turn-session",
                "sessionVersion": 3,
                "status": "awaiting_input",
                "awaiting": {
                    "key": "cold_attempt",
                    "ctaText": "Try one concrete cause.",
                },
                "learnerTranscript": [],
                "events": [{
                    "type": "cold_help_turn",
                    "text": support_text,
                    "answer_mode": "help_request",
                    "score_eligible": False,
                    "graph_neutral": True,
                    "agent_response": "Try one concrete cause.",
                }],
                "caseComplete": False,
                "record": None,
            }),
        )

    page.route("**/api/extract", fulfill_extract)
    page.route(re.compile(r".*/api/session$"), fulfill_session)
    page.route(re.compile(r".*/api/session/[^/]+/turn$"), fulfill_turn)
    page.locator("#nav-ignition").click()
    page.locator("#hero-single-input-field").fill("why vaccines create immune memory")
    page.locator("#hero-cold-guess-field").fill(door_sketch)
    page.locator("#hero-door-submit").click()

    page.wait_for_function(
        """() => {
          const conceptId = localStorage.getItem('learnops_active');
          const key = conceptId ? `socratink:seda-session:v1:${conceptId}` : null;
          const value = key ? JSON.parse(localStorage.getItem(key) || 'null') : null;
          return value?.latest?.awaiting?.key === 'cold_attempt';
        }""",
        timeout=20_000,
    )
    page.locator("#chamber-composer").fill(support_text)
    page.locator("#chamber-send").click()

    expect(page.locator("#chamber-verdict")).to_contain_text(
        "Use the next question to add one cause-and-effect link.", timeout=2_000
    )
    expect(page.locator("#chamber-verdict")).to_contain_text("Response received")
    expect(page.locator("#chamber-verdict")).not_to_contain_text("Gap found")
    expect(page.locator("#chamber-verdict")).not_to_contain_text("Study")
    expect(page.locator("#chamber-send")).to_have_text("Check the link")
    expect(page.locator("#chamber-question")).to_have_text("Try one concrete cause.")
    expect(page.locator("#chamber-composer")).to_be_enabled()
    assert turn_texts == [door_sketch, support_text]
    assert [payload["expectedVersion"] for payload in turn_payloads] == [1, 2]
    attempt_count = page.evaluate(
        """() => {
          const conceptId = localStorage.getItem('learnops_active');
          const key = conceptId ? `socratink:training:v1:${conceptId}` : null;
          const training = key ? JSON.parse(localStorage.getItem(key) || 'null') : null;
          return Object.values(training?.node_records || {})
            .flatMap((record) => record?.attempts || []).length;
        }"""
    )
    assert attempt_count == 0


def test_seda_start_failure_offers_retry_from_product_flow(
    page: Page, base_url: str
) -> None:
    """A failed app-local SEDA start should give the learner a retry action."""
    _enter_app_shell_as_guest(page, base_url)

    def fulfill_extract(route) -> None:
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "provisional_map": {
                    "metadata": {"core_thesis": "Immune memory speeds the next response."},
                    "backbone": [{"id": "b1", "principle": "Immune memory persists."}],
                    "clusters": [{
                        "id": "c1",
                        "label": "Memory cells",
                        "subnodes": [{
                            "id": "c1_s1",
                            "label": "Memory cells",
                            "mechanism": "Memory cells persist after exposure.",
                        }],
                    }],
                },
            }),
        )

    session_attempts = {"count": 0}

    def fulfill_session(route) -> None:
        session_attempts["count"] += 1
        if session_attempts["count"] == 1:
            route.fulfill(
                status=503,
                content_type="application/json",
                body=json.dumps({"detail": "Loop backend unavailable."}),
            )
            return
        route.fulfill(
            status=201,
            content_type="application/json",
            body=json.dumps({
                "sessionId": "retry-session",
                "sessionVersion": 1,
                "awaiting": {"key": "launch_attempt", "ctaText": "Try your first explanation."},
                "learnerTranscript": [],
                "caseComplete": False,
            }),
        )

    bootstrap_turns: list[str] = []
    turn_payloads: list[dict] = []

    def fulfill_turn(route) -> None:
        payload = route.request.post_data_json
        turn_payloads.append(payload)
        bootstrap_turns.append(payload["text"])
        if len(bootstrap_turns) == 2:
            route.fulfill(
                status=503,
                content_type="application/json",
                body=json.dumps({"detail": "Loop turn unavailable."}),
            )
            return
        if len(bootstrap_turns) > 2:
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({
                    "sessionId": "retry-session",
                    "sessionVersion": 3,
                    "status": "awaiting_input",
                    "awaiting": {"key": "cold_attempt", "ctaText": "Try one concrete cause."},
                    "events": [{
                        "type": "cold_help_turn", "text": payload["text"],
                        "answer_mode": "help_request", "score_eligible": False,
                        "graph_neutral": True, "agent_response": "Try one concrete cause.",
                    }],
                    "caseComplete": False,
                    "record": None,
                }),
            )
            return
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "sessionId": "retry-session",
                "sessionVersion": 2,
                "status": "awaiting_input",
                "awaiting": {
                    "key": "cold_attempt",
                    "ctaText": "Why is the second exposure faster?",
                },
                "learnerTranscript": [],
                "events": [_seda_route_event()],
                "sourceLessRoute": _seda_route_result(),
                "caseComplete": False,
                "record": None,
            }),
        )

    page.route("**/api/extract", fulfill_extract)
    page.route(re.compile(r".*/api/session$"), fulfill_session)
    page.route(re.compile(r".*/api/session/[^/]+/turn$"), fulfill_turn)
    page.locator("#nav-ignition").click()
    page.locator("#hero-single-input-field").fill("why vaccines create immune memory")
    page.locator("#hero-cold-guess-field").fill("The first exposure leaves memory cells.")
    page.locator("#hero-door-submit").click()
    expect(page.locator("#launch-pad-view")).to_be_hidden()

    expect(page.locator("#drill-chamber-view")).to_be_visible(timeout=20_000)
    expect(page.locator("#chamber-question")).to_contain_text(
        "The learning loop could not start. Try again when ready.",
        timeout=20_000,
    )
    expect(page.locator("#chamber-send")).to_have_text("Try again")
    page.locator("#chamber-send").click()
    expect(page.locator("#chamber-question")).to_have_text(
        "Why is the second exposure faster?",
        timeout=20_000,
    )
    expect(page.locator("#chamber-composer")).to_be_enabled()
    assert session_attempts["count"] == 2
    assert bootstrap_turns == ["The first exposure leaves memory cells."]

    learner_answer = "Memory cells make the next response faster."
    page.locator("#chamber-composer").fill(learner_answer)
    page.locator("#chamber-send").click()
    expect(page.locator("#chamber-verdict")).to_have_text(
        re.compile(r"Answer kept.*Not recorded.*The learning loop did not respond\."),
        timeout=20_000,
    )
    expect(page.locator("#chamber-send")).to_have_text("Try sending again")
    expect(page.locator("#chamber-composer")).to_be_disabled()
    expect(page.locator("#chamber-composer")).to_have_value(learner_answer)
    expect(page.locator("#chamber-active")).not_to_have_attribute(
        "data-loading", "true"
    )
    expect(page.locator("#chamber-hint")).to_have_text("One clear connection is enough.")
    page.locator("#chamber-send").click()
    expect(page.locator("#chamber-verdict")).to_contain_text(
        "Use the next question to add one cause-and-effect link.", timeout=2_000
    )
    assert [payload["text"] for payload in turn_payloads] == [
        "The first exposure leaves memory cells.", learner_answer, learner_answer,
    ]
    assert turn_payloads[1]["requestId"] == turn_payloads[2]["requestId"]
    assert turn_payloads[0]["requestId"] != turn_payloads[1]["requestId"]
    assert [payload["expectedVersion"] for payload in turn_payloads] == [1, 2, 2]


def test_missing_source_less_route_preserves_sketch_and_builds_fresh_question(
    clean_page: Page, base_url: str
) -> None:
    """A typed route failure offers a fresh route without evidence or lost Door work."""
    page = clean_page
    _enter_app_shell_as_guest(page, base_url)

    page.route(
        "**/api/extract",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "provisional_map": {
                    "metadata": {"core_thesis": "Immune memory changes later response."},
                    "backbone": [{"id": "b1", "principle": "Something persists."}],
                    "clusters": [],
                },
            }),
        ),
    )
    session_requests: list[dict] = []

    def fulfill_session(route) -> None:
        session_requests.append(route.request.post_data_json)
        session_number = len(session_requests)
        route.fulfill(
            status=201,
            content_type="application/json",
            body=json.dumps({
                "sessionId": f"route-recovery-{session_number}",
                "sessionVersion": 1,
                "status": "awaiting_input",
                "awaiting": {"key": "launch_attempt", "ctaText": "First try"},
                "learnerTranscript": [],
                "caseComplete": False,
            }),
        )

    turn_requests: list[dict] = []
    routed_prompt = "Why does retained memory speed the later response?"

    def fulfill_turn(route) -> None:
        turn_requests.append(route.request.post_data_json)
        if len(turn_requests) == 1:
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({
                    "sessionId": "route-recovery-1",
                    "sessionVersion": 2,
                    "status": "awaiting_input",
                    "awaiting": {"key": "cmd", "ctaText": "Choose what to do next."},
                    "sourceLessRoute": {
                        "contractVersion": 1,
                        "status": "route_unavailable",
                        "code": "route_unavailable",
                        "reason": "generation_failed",
                        "retryable": True,
                    },
                    "events": [{
                        "type": "bridge_error", "phase": "route",
                        "action": "generate-route", "graph_neutral": True,
                        "score_eligible": False,
                    }],
                    "caseComplete": False,
                }),
            )
            return
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "sessionId": "route-recovery-2",
                "sessionVersion": 2,
                "status": "awaiting_input",
                "awaiting": {"key": "cold_attempt", "ctaText": routed_prompt},
                "sourceLessRoute": _seda_route_result(prompt=routed_prompt),
                "events": [_seda_route_event(prompt=routed_prompt)],
                "caseComplete": False,
            }),
        )

    page.route(re.compile(r".*/api/session$"), fulfill_session)
    page.route(re.compile(r".*/api/session/[^/]+/turn$"), fulfill_turn)
    door_sketch = "The first exposure leaves something behind."
    page.locator("#nav-ignition").click()
    page.locator("#hero-single-input-field").fill("why vaccines create immune memory")
    page.locator("#hero-cold-guess-field").fill(door_sketch)
    page.locator("#hero-door-submit").click()

    expect(page.locator("#chamber-question")).to_have_text(
        "We could not build the first question. Your starting sketch is saved.",
        timeout=20_000,
    )
    expect(page.locator("#chamber-send")).to_have_text("Build the first question again")
    expect(page.locator("#chamber-composer")).to_be_disabled()
    assert page.evaluate(
        """() => {
          const conceptId = localStorage.getItem('learnops_active');
          const training = JSON.parse(localStorage.getItem(`socratink:training:v1:${conceptId}`) || 'null');
          return Object.values(training?.node_records || {})
            .flatMap((record) => record?.attempts || []).length;
        }"""
    ) == 0

    page.locator("#chamber-send").click()
    expect(page.locator("#chamber-question")).to_have_text(routed_prompt, timeout=20_000)
    expect(page.locator("#chamber-composer")).to_be_enabled()
    saved_sketch = page.evaluate(
        """() => {
          const conceptId = localStorage.getItem('learnops_active');
          return JSON.parse(localStorage.getItem('learnops_concepts'))
            .find((concept) => concept.id === conceptId)?.startingMapContext;
        }"""
    )
    assert saved_sketch == door_sketch
    assert session_requests == [
        {"sourceLessDoorBootstrap": True},
        {"sourceLessDoorBootstrap": True},
    ]
    assert [request["text"] for request in turn_requests] == [door_sketch, door_sketch]
    assert all(re.fullmatch(r"[0-9a-f-]{36}", request["requestId"], re.I) for request in turn_requests)
    assert turn_requests[0]["requestId"] != turn_requests[1]["requestId"]
    assert [request["expectedVersion"] for request in turn_requests] == [1, 1]


def test_unbound_source_less_map_with_evidence_is_never_replaced(
    clean_page: Page, base_url: str
) -> None:
    """Legacy node-keyed evidence blocks automatic first-route replacement."""
    page = clean_page
    _enter_app_shell_as_guest(page, base_url)
    page.evaluate("localStorage.clear(); sessionStorage.clear();")
    page.evaluate(
        """(() => {
          const conceptId = 'unbound-evidence-route';
          const graphData = JSON.stringify({
            metadata: {
              core_thesis: 'Memory changes later response.',
              starting_map_context: 'Something remains after exposure.',
              source_mode: 'source_less',
              route_status: 'pending_seda',
              graph_neutral: true,
            },
            backbone: [{
              id: 'legacy-node', label: 'Legacy target',
              mechanism: 'A prior mechanism.',
              learner_scaffold: { entry_prompt: 'What remains after exposure?' },
            }, {
              id: 'prior-node', label: 'Prior evidence target',
              mechanism: 'Earlier work stays keyed here.',
            }],
            clusters: [],
          });
          localStorage.setItem('learnops_concepts', JSON.stringify([{
            id: conceptId, name: 'Unbound evidence QA', createdAt: Date.now(),
            state: 'growing', startingMapContext: 'Something remains after exposure.',
            sourceMode: 'source_less', graphData,
          }]));
          localStorage.setItem('learnops_active', conceptId);
          localStorage.setItem(`socratink:training:v1:${conceptId}`, JSON.stringify({
            concept_id: conceptId, schema_version: 1,
            source_mode: 'source_less', grounding: 'learner_sketch',
            node_records: {
              'prior-node': { attempts: [{
                id: 'legacy-attempt', kind: 'cold', at: '2026-07-09T10:00:00.000Z',
                user_text: 'My earlier reconstruction.', classification: 'partial',
                gaps: [], grader_version: 'qa',
              }], repairs: [] },
            },
          }));
        })()"""
    )
    session_requests: list[str] = []
    page.on(
        "request",
        lambda request: session_requests.append(request.url)
        if "/api/session" in request.url
        else None,
    )
    page.goto(f"{base_url}/session/unbound-evidence-route")
    _wait_for_app_settled(page)
    page.evaluate(
        """window.App.reopenStudy({
          id: 'legacy-node', label: 'Legacy target', fullLabel: 'Legacy target',
          learner_scaffold: { entry_prompt: 'What remains after exposure?' },
        })"""
    )

    expect(page.locator("#chamber-question")).to_have_text(
        "This learning route cannot be resumed. Your recorded work is still on the map.",
        timeout=20_000,
    )
    expect(page.locator("#chamber-send")).to_have_text("Return to map")
    assert session_requests == []
    unchanged = page.evaluate(
        """() => {
          const concept = JSON.parse(localStorage.getItem('learnops_concepts'))[0];
          const graph = JSON.parse(concept.graphData);
          const training = JSON.parse(
            localStorage.getItem('socratink:training:v1:unbound-evidence-route')
          );
          return {
            nodeId: graph.backbone[0].id,
            boundNodeId: graph.metadata.seda_route_bound_node_id || null,
            attempt: training.node_records['prior-node'].attempts[0].user_text,
          };
        }"""
    )
    assert unchanged == {
        "nodeId": "legacy-node",
        "boundNodeId": None,
        "attempt": "My earlier reconstruction.",
    }
    page.locator("#chamber-send").click()


@pytest.mark.parametrize(
    "resume_case",
    [
        "unbound_without_confirmation",
        "missing_bound_session",
        "bound_session_mismatch",
        "bound_route_mismatch",
    ],
)
def test_invalid_source_less_resume_state_fails_closed(
    clean_page: Page, base_url: str, resume_case: str
) -> None:
    """Every stale/unconfirmed route shape keeps study closed and evidence empty."""
    page = clean_page
    _enter_app_shell_as_guest(page, base_url)
    page.evaluate("localStorage.clear(); sessionStorage.clear();")
    bound_session_id = "11111111-1111-4111-8111-111111111111"
    page.evaluate(
        """({ resumeCase, boundSessionId }) => {
          const conceptId = `invalid-resume-${resumeCase}`;
          const metadata = {
            core_thesis: 'Memory changes the later response.',
            starting_map_context: 'Something remains after exposure.',
            source_mode: 'source_less',
          };
          if (resumeCase !== 'unbound_without_confirmation') {
            metadata.seda_route_bound_node_id = 'bound-node';
          }
          if (!['unbound_without_confirmation', 'missing_bound_session'].includes(resumeCase)) {
            metadata.seda_route_bound_session_id = boundSessionId;
          }
          const graphData = JSON.stringify({
            metadata,
            backbone: [{
              id: 'bound-node', label: 'Bound target', mechanism: 'Memory cells persist.',
              learner_scaffold: { entry_prompt: 'Why is the next response faster?' },
            }],
            clusters: [],
          });
          localStorage.setItem('learnops_concepts', JSON.stringify([{
            id: conceptId, name: 'Invalid resume QA', createdAt: Date.now(),
            state: 'growing', sourceMode: 'source_less',
            startingMapContext: 'Something remains after exposure.', graphData,
          }]));
          localStorage.setItem('learnops_active', conceptId);
          localStorage.setItem(`socratink:training:v1:${conceptId}`, JSON.stringify({
            concept_id: conceptId, schema_version: 1,
            source_mode: 'source_less', grounding: 'learner_sketch', node_records: {},
          }));
          if (['bound_session_mismatch', 'bound_route_mismatch'].includes(resumeCase)) {
            localStorage.setItem(`socratink:seda-session:v1:${conceptId}`, JSON.stringify({
              sessionId: boundSessionId, sessionVersion: 2, nodeId: 'bound-node',
              latest: { caseComplete: false, sessionVersion: 2 },
            }));
          }
          return conceptId;
        }""",
        {"resumeCase": resume_case, "boundSessionId": bound_session_id},
    )

    if resume_case in {"bound_session_mismatch", "bound_route_mismatch"}:
        response_session_id = (
            "22222222-2222-4222-8222-222222222222"
            if resume_case == "bound_session_mismatch"
            else bound_session_id
        )
        route_node_id = (
            "different-node" if resume_case == "bound_route_mismatch" else "bound-node"
        )
        page.route(
            re.compile(rf".*/api/session/{bound_session_id}$"),
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({
                    "sessionId": response_session_id,
                    "sessionVersion": 2,
                    "status": "awaiting_input",
                    "awaiting": {
                        "key": "cold_attempt",
                        "ctaText": "Why is the next response faster?",
                    },
                    "sourceLessRoute": _seda_route_result(node_id=route_node_id),
                    "events": [_seda_route_event(node_id=route_node_id)],
                    "caseComplete": False,
                    "record": None,
                }),
            ),
        )

    concept_id = f"invalid-resume-{resume_case}"
    page.goto(f"{base_url}/session/{concept_id}")
    page.wait_for_function("() => Boolean(window.App?.reopenStudy)", timeout=20_000)
    page.evaluate(
        """() => window.App.reopenStudy({
          id: 'bound-node', label: 'Bound target', fullLabel: 'Bound target',
          learner_scaffold: { entry_prompt: 'Why is the next response faster?' },
        })"""
    )

    expect(page.locator("#chamber-question")).to_have_text(
        "We could not build the first question. Your starting sketch is saved.",
        timeout=20_000,
    )
    expect(page.locator("#chamber-send")).to_have_text(
        "Build the first question again"
    )
    expect(page.locator("#chamber-composer")).to_be_disabled()
    assert page.evaluate(
        """(conceptId) => {
          const training = JSON.parse(
            localStorage.getItem(`socratink:training:v1:${conceptId}`)
          );
          return Object.values(training.node_records || {})
            .flatMap((record) => record.attempts || []).length;
        }""",
        concept_id,
    ) == 0


def test_stale_bound_route_with_existing_evidence_returns_to_map(
    clean_page: Page, base_url: str
) -> None:
    """A stale bound session never replaces evidence with a freshly generated route."""
    page = clean_page
    _enter_app_shell_as_guest(page, base_url)
    page.evaluate("localStorage.clear(); sessionStorage.clear();")
    page.evaluate(
        """(() => {
          const conceptId = 'stale-bound-route';
          const graphData = JSON.stringify({
            metadata: {
              core_thesis: 'Memory changes later response.',
              starting_map_context: 'Something remains after the first exposure.',
              source_mode: 'source_less',
              seda_route_bound_node_id: 'c9_s1',
              seda_route_bound_session_id: '11111111-1111-4111-8111-111111111111',
            },
            backbone: [{
              id: 'c9_s1', label: 'Current memory target',
              mechanism: 'Memory cells persist.',
              learner_scaffold: { entry_prompt: 'Why is the next response faster?' },
            }, {
              id: 'prior-node', label: 'Prior evidence target',
              mechanism: 'A prior mechanism.',
            }],
            clusters: [],
          });
          localStorage.setItem('learnops_concepts', JSON.stringify([{
            id: conceptId, name: 'Stale route QA', createdAt: Date.now(),
            state: 'growing', startingMapContext: 'Something remains after the first exposure.',
            graphData,
          }]));
          localStorage.setItem('learnops_active', conceptId);
          localStorage.setItem(`socratink:seda-session:v1:${conceptId}`, JSON.stringify({
            sessionId: '11111111-1111-4111-8111-111111111111',
            nodeId: 'c9_s1', latest: { caseComplete: false },
          }));
          localStorage.setItem(`socratink:training:v1:${conceptId}`, JSON.stringify({
            concept_id: conceptId, schema_version: 1,
            source_mode: 'source_less', grounding: 'learner_sketch',
            sketch: { text: 'Something remains after the first exposure.' },
            node_records: {
              'prior-node': { attempts: [{
                id: 'prior-attempt', kind: 'cold', at: '2026-07-09T10:00:00.000Z',
                user_text: 'My earlier recorded reconstruction.', classification: 'partial',
                gaps: [], grader_version: 'qa',
              }], repairs: [] },
            },
          }));
        })()"""
    )
    page.route(
        re.compile(r".*/api/session/[^/]+$"),
        lambda route: route.fulfill(
            status=404,
            content_type="application/json",
            body=json.dumps({"error": "session not found"}),
        ),
    )
    page.goto(f"{base_url}/session/stale-bound-route")
    expect(page.locator(".concept-page-b2__attempt-input")).to_be_visible(timeout=20_000)
    page.locator(".concept-page-b2__attempt-input").fill("A new unsent line.")
    page.locator(".concept-page-b2__attempt-save").click()

    expect(page.locator("#chamber-question")).to_have_text(
        "This learning route cannot be resumed. Your recorded work is still on the map.",
        timeout=20_000,
    )
    expect(page.locator("#chamber-send")).to_have_text("Return to map")
    expect(page.locator("#chamber-composer")).to_be_disabled()
    page.locator("#chamber-send").click()
    expect(page.locator("#drill-chamber-view")).to_be_hidden()
    expect(page.locator(".concept-page-b2__attempt-input")).to_have_value(
        "A new unsent line."
    )
    preserved = page.evaluate(
        """() => JSON.parse(
          localStorage.getItem('socratink:training:v1:stale-bound-route')
        ).node_records['prior-node'].attempts"""
    )
    assert len(preserved) == 1
    assert preserved[0]["user_text"] == "My earlier recorded reconstruction."


def test_stale_tab_conflict_preserves_draft_and_requires_explicit_resubmit(
    clean_page: Page, base_url: str
) -> None:
    """A 409 refreshes the prompt without recording or replaying stale text."""
    page = clean_page
    _enter_app_shell_as_guest(page, base_url)
    page.evaluate("localStorage.clear(); sessionStorage.clear();")
    session_id = "33333333-3333-4333-8333-333333333333"
    page.evaluate(
        """(sessionId) => {
          const conceptId = 'stale-tab-conflict';
          const graphData = JSON.stringify({
            metadata: {
              core_thesis: 'Memory changes later response.',
              starting_map_context: 'Something remains after exposure.',
              source_mode: 'source_less',
              seda_route_bound_node_id: 'bound-node',
              seda_route_bound_session_id: sessionId,
            },
            backbone: [{
              id: 'bound-node', label: 'Bound target',
              mechanism: 'Memory cells persist.',
              learner_scaffold: { entry_prompt: 'Original prompt?' },
            }],
            clusters: [],
          });
          localStorage.setItem('learnops_concepts', JSON.stringify([{
            id: conceptId, name: 'Stale tab QA', createdAt: Date.now(),
            state: 'growing', sourceMode: 'source_less',
            startingMapContext: 'Something remains after exposure.', graphData,
          }]));
          localStorage.setItem('learnops_active', conceptId);
          localStorage.setItem(`socratink:seda-session:v1:${conceptId}`, JSON.stringify({
            sessionId, sessionVersion: 2, nodeId: 'bound-node',
            latest: { caseComplete: false, sessionVersion: 2 },
          }));
          localStorage.setItem(`socratink:training:v1:${conceptId}`, JSON.stringify({
            concept_id: conceptId, schema_version: 1,
            source_mode: 'source_less', grounding: 'learner_sketch', node_records: {},
          }));
        }""",
        session_id,
    )
    prompt_before = "Why does memory change the later response?"
    prompt_after = "What persists between the two exposures?"
    get_count = {"value": 0}

    def fulfill_get(route) -> None:
        get_count["value"] += 1
        version = 2 if get_count["value"] == 1 else 3
        prompt = prompt_before if version == 2 else prompt_after
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "sessionId": session_id,
                "sessionVersion": version,
                "status": "awaiting_input",
                "awaiting": {"key": "cold_attempt", "ctaText": prompt},
                "sourceLessRoute": _seda_route_result(
                    node_id="bound-node", label="Bound target", prompt=prompt,
                ),
                "events": [_seda_route_event(
                    node_id="bound-node", label="Bound target", prompt=prompt,
                )],
                "caseComplete": False,
                "record": None,
            }),
        )

    turn_payloads: list[dict] = []
    draft = "Memory cells remain ready for the second exposure."

    def fulfill_turn(route) -> None:
        payload = route.request.post_data_json
        turn_payloads.append(payload)
        if len(turn_payloads) == 1:
            route.fulfill(
                status=409,
                content_type="application/json",
                body=json.dumps({
                    "error": "session_conflict",
                    "code": "SessionConflict",
                    "message": "session changed after this prompt was shown",
                    "currentVersion": 3,
                }),
            )
            return
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "sessionId": session_id,
                "sessionVersion": 4,
                "status": "awaiting_input",
                "awaiting": {"key": "compare", "ctaText": "Compare with the note."},
                "events": [{
                    "type": "cold_attempt", "kc_id": "bound-node", "text": draft,
                    "evaluation": {
                        "classification": "deep", "gaps": [], "grader_version": "qa",
                    },
                }],
                "caseComplete": False,
                "record": None,
            }),
        )

    page.route(
        re.compile(rf".*/api/session/{session_id}$"),
        fulfill_get,
    )
    page.route(
        re.compile(rf".*/api/session/{session_id}/turn$"),
        fulfill_turn,
    )
    page.goto(f"{base_url}/session/stale-tab-conflict")
    page.wait_for_function("() => Boolean(window.App?.reopenStudy)", timeout=20_000)
    page.evaluate(
        """() => {
          window.App.cancelDrill({ restoreMap: false });
          window.App.reopenStudy({
            id: 'bound-node', label: 'Bound target', fullLabel: 'Bound target',
            learner_scaffold: { entry_prompt: 'Original prompt?' },
          });
        }"""
    )
    expect(page.locator("#chamber-question")).to_have_text(
        prompt_before, timeout=20_000
    )
    page.locator("#chamber-composer").fill(draft)
    page.locator("#chamber-send").evaluate("button => button.click()")

    expect(page.locator("#chamber-question")).to_have_text(
        prompt_after, timeout=20_000
    )
    expect(page.locator("#chamber-composer")).to_have_value(draft)
    expect(page.locator("#chamber-verdict")).to_contain_text(
        "Session changed in another tab"
    )
    expect(page.locator("#chamber-verdict")).to_contain_text(
        "check your draft again"
    )
    assert page.evaluate(
        """() => {
          const training = JSON.parse(
            localStorage.getItem('socratink:training:v1:stale-tab-conflict')
          );
          return Object.values(training.node_records || {})
            .flatMap((record) => record.attempts || []).length;
        }"""
    ) == 0

    page.locator("#chamber-send").evaluate("button => button.click()")
    expect(page.locator("#chamber-send")).to_have_text(
        "See what to study", timeout=2_000
    )
    assert [payload["expectedVersion"] for payload in turn_payloads] == [2, 3]
    assert turn_payloads[0]["requestId"] != turn_payloads[1]["requestId"]
    assert [payload["text"] for payload in turn_payloads] == [draft, draft]
    assert page.evaluate(
        """() => JSON.parse(
          localStorage.getItem('socratink:training:v1:stale-tab-conflict')
        ).node_records['bound-node'].attempts.length"""
    ) == 1


def test_evidence_persistence_failure_withholds_study_until_idempotent_retry(
    clean_page: Page, base_url: str
) -> None:
    """A server-accepted answer is not called recorded until local evidence saves."""
    page = clean_page
    _enter_app_shell_as_guest(page, base_url)
    page.evaluate("localStorage.clear(); sessionStorage.clear();")
    session_id = "44444444-4444-4444-8444-444444444444"
    page.evaluate(
        """(sessionId) => {
          const conceptId = 'projection-retry';
          const graphData = JSON.stringify({
            metadata: {
              core_thesis: 'Memory changes later response.',
              starting_map_context: 'Something remains after exposure.',
              source_mode: 'source_less',
              seda_route_bound_node_id: 'bound-node',
              seda_route_bound_session_id: sessionId,
            },
            backbone: [{
              id: 'bound-node', label: 'Bound target',
              mechanism: 'Memory cells persist.',
              learner_scaffold: { entry_prompt: 'Why is the later response faster?' },
            }],
            clusters: [],
          });
          localStorage.setItem('learnops_concepts', JSON.stringify([{
            id: conceptId, name: 'Projection retry QA', createdAt: Date.now(),
            state: 'growing', sourceMode: 'source_less',
            startingMapContext: 'Something remains after exposure.', graphData,
          }]));
          localStorage.setItem('learnops_active', conceptId);
          localStorage.setItem(`socratink:seda-session:v1:${conceptId}`, JSON.stringify({
            sessionId, sessionVersion: 2, nodeId: 'bound-node',
            latest: { caseComplete: false, sessionVersion: 2 },
          }));
          localStorage.setItem(`socratink:training:v1:${conceptId}`, JSON.stringify({
            concept_id: conceptId, schema_version: 1,
            source_mode: 'source_less', grounding: 'learner_sketch', node_records: {},
          }));
        }""",
        session_id,
    )
    prompt = "Why is the later response faster?"
    page.route(
        re.compile(rf".*/api/session/{session_id}$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "sessionId": session_id,
                "sessionVersion": 2,
                "status": "awaiting_input",
                "awaiting": {"key": "cold_attempt", "ctaText": prompt},
                "sourceLessRoute": _seda_route_result(
                    node_id="bound-node", label="Bound target", prompt=prompt,
                ),
                "events": [_seda_route_event(
                    node_id="bound-node", label="Bound target", prompt=prompt,
                )],
                "caseComplete": False,
                "record": None,
            }),
        ),
    )
    draft = "Memory cells persist and react sooner later."
    turn_payloads: list[dict] = []

    def fulfill_turn(route) -> None:
        turn_payloads.append(route.request.post_data_json)
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "sessionId": session_id,
                "sessionVersion": 3,
                "status": "awaiting_input",
                "awaiting": {"key": "compare", "ctaText": "Compare with the note."},
                "events": [{
                    "type": "cold_attempt", "kc_id": "bound-node", "text": draft,
                    "evaluation": {
                        "classification": "deep", "gaps": [], "grader_version": "qa",
                    },
                }],
                "caseComplete": False,
                "record": None,
            }),
        )

    page.route(
        re.compile(rf".*/api/session/{session_id}/turn$"),
        fulfill_turn,
    )
    page.goto(f"{base_url}/session/projection-retry")
    page.wait_for_function("() => Boolean(window.App?.reopenStudy)", timeout=20_000)
    page.evaluate(
        """() => {
          window.App.cancelDrill({ restoreMap: false });
          window.App.reopenStudy({
            id: 'bound-node', label: 'Bound target', fullLabel: 'Bound target',
            learner_scaffold: { entry_prompt: 'Why is the later response faster?' },
          });
        }"""
    )
    page.wait_for_function(
        """() => {
          const value = JSON.parse(
            localStorage.getItem('socratink:seda-session:v1:projection-retry') || 'null'
          );
          return value?.latest?.sessionVersion === 2
            && value?.latest?.awaiting?.key === 'cold_attempt';
        }""",
        timeout=20_000,
    )
    expect(page.locator("#chamber-composer")).to_be_enabled(timeout=20_000)
    page.evaluate(
        """() => {
          const original = Storage.prototype.setItem;
          let failNextTrainingWrite = true;
          Storage.prototype.setItem = function(key, value) {
            if (failNextTrainingWrite && String(key).startsWith('socratink:training:v1:')) {
              failNextTrainingWrite = false;
              throw new DOMException('QA quota failure', 'QuotaExceededError');
            }
            return original.call(this, key, value);
          };
        }"""
    )
    page.locator("#chamber-composer").fill(draft)
    page.locator("#chamber-send").evaluate("button => button.click()")

    expect(page.locator("#chamber-verdict")).to_contain_text(
        "Not saved in this browser yet.", timeout=5_000
    )
    expect(page.locator("#chamber-verdict")).not_to_contain_text("Recorded")
    expect(page.locator("#chamber-send")).to_have_text("Try saving again")
    assert page.evaluate(
        """() => {
          const training = JSON.parse(
            localStorage.getItem('socratink:training:v1:projection-retry')
          );
          return Object.values(training.node_records || {})
            .flatMap((record) => record.attempts || []).length;
        }"""
    ) == 0

    page.locator("#chamber-send").evaluate("button => button.click()")
    expect(page.locator("#chamber-send")).to_have_text(
        "See what to study", timeout=2_000
    )
    assert len(turn_payloads) == 2
    assert turn_payloads[0]["requestId"] == turn_payloads[1]["requestId"]
    assert [payload["expectedVersion"] for payload in turn_payloads] == [2, 2]
    assert page.evaluate(
        """() => JSON.parse(
          localStorage.getItem('socratink:training:v1:projection-retry')
        ).node_records['bound-node'].attempts.length"""
    ) == 1


def test_seda_transport_failure_keeps_draft_and_retries_same_turn(
    clean_page: Page, base_url: str
) -> None:
    """A failed network turn keeps visible effort and its idempotency key."""
    page = clean_page
    _enter_app_shell_as_guest(page, base_url)
    page.evaluate("localStorage.clear(); sessionStorage.clear();")
    session_id = "77777777-7777-4777-8777-777777777777"
    page.evaluate(
        """(sessionId) => {
          const conceptId = 'transport-retry';
          const graphData = JSON.stringify({
            metadata: {
              core_thesis: 'Memory changes later response.',
              starting_map_context: 'Something remains after exposure.',
              source_mode: 'source_less',
              seda_route_bound_node_id: 'bound-node',
              seda_route_bound_session_id: sessionId,
            },
            backbone: [{
              id: 'bound-node', label: 'Bound target', mechanism: 'Memory cells persist.',
              learner_scaffold: { entry_prompt: 'Why is the later response faster?' },
            }],
            clusters: [],
          });
          localStorage.setItem('learnops_concepts', JSON.stringify([{
            id: conceptId, name: 'Transport retry QA', createdAt: Date.now(),
            state: 'growing', sourceMode: 'source_less',
            startingMapContext: 'Something remains after exposure.', graphData,
          }]));
          localStorage.setItem('learnops_active', conceptId);
          localStorage.setItem(`socratink:seda-session:v1:${conceptId}`, JSON.stringify({
            sessionId, sessionVersion: 2, nodeId: 'bound-node',
            latest: { caseComplete: false, sessionVersion: 2 },
          }));
          localStorage.setItem(`socratink:training:v1:${conceptId}`, JSON.stringify({
            concept_id: conceptId, schema_version: 1,
            source_mode: 'source_less', grounding: 'learner_sketch', node_records: {},
          }));
        }""",
        session_id,
    )
    prompt = "Why is the later response faster?"
    page.route(
        re.compile(rf".*/api/session/{session_id}$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "sessionId": session_id,
                "sessionVersion": 2,
                "status": "awaiting_input",
                "awaiting": {"key": "cold_attempt", "ctaText": prompt},
                "sourceLessRoute": _seda_route_result(
                    node_id="bound-node", label="Bound target", prompt=prompt,
                ),
                "events": [_seda_route_event(
                    node_id="bound-node", label="Bound target", prompt=prompt,
                )],
                "caseComplete": False,
            }),
        ),
    )
    draft = "Memory cells remain ready and react sooner on the next exposure."
    turn_payloads: list[dict] = []

    def fulfill_turn(route) -> None:
        turn_payloads.append(route.request.post_data_json)
        if len(turn_payloads) == 1:
            route.fulfill(
                status=503,
                content_type="application/json",
                body=json.dumps({"error": "session_store_unavailable"}),
            )
            return
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "sessionId": session_id,
                "sessionVersion": 3,
                "status": "awaiting_input",
                "awaiting": {"key": "compare", "ctaText": "Compare with the note."},
                "events": [{
                    "type": "cold_attempt", "kc_id": "bound-node", "text": draft,
                    "evaluation": {
                        "classification": "deep", "gaps": [], "grader_version": "qa",
                    },
                }],
                "caseComplete": False,
            }),
        )

    page.route(
        re.compile(rf".*/api/session/{session_id}/turn$"),
        fulfill_turn,
    )
    page.goto(f"{base_url}/session/transport-retry")
    expect(page.locator(".concept-page-b2__attempt-input")).to_be_visible(
        timeout=20_000
    )
    page.wait_for_function("() => Boolean(window.App?.reopenStudy)", timeout=20_000)
    page.evaluate(
        """() => {
          window.App.cancelDrill({ restoreMap: false });
          window.App.reopenStudy({
            id: 'bound-node', label: 'Bound target', fullLabel: 'Bound target',
            learner_scaffold: { entry_prompt: 'Why is the later response faster?' },
          });
        }"""
    )
    page.wait_for_function(
        """() => {
          const state = JSON.parse(
            localStorage.getItem('socratink:seda-session:v1:transport-retry') || 'null'
          );
          return state?.latest?.sessionVersion === 2
            && state?.latest?.awaiting?.key === 'cold_attempt'
            && document.getElementById('chamber-question')?.textContent
              === 'Why is the later response faster?'
            && document.getElementById('chamber-composer')?.disabled === false
            && document.getElementById('chamber-send')?.textContent === 'Check the link';
        }""",
        timeout=20_000,
    )
    page.locator("#chamber-composer").fill(draft)
    page.locator("#chamber-send").evaluate("button => button.click()")

    for _ in range(100):
        if turn_payloads:
            break
        page.wait_for_timeout(25)
    assert turn_payloads, "failed SEDA turn never reached the transport stub"
    expect(page.locator("#chamber-verdict")).to_contain_text(
        "Answer kept", timeout=5_000
    )
    expect(page.locator("#chamber-verdict")).to_contain_text("Not recorded")
    expect(page.locator("#chamber-send")).to_have_text("Try sending again")
    expect(page.locator("#chamber-composer")).to_have_value(draft)
    assert page.evaluate(
        """() => Object.values(JSON.parse(
          localStorage.getItem('socratink:training:v1:transport-retry')
        ).node_records || {}).flatMap((record) => record.attempts || []).length"""
    ) == 0

    page.locator("#chamber-send").click()
    expect(page.locator("#chamber-send")).to_have_text(
        "See what to study", timeout=2_000
    )
    assert len(turn_payloads) == 2
    assert turn_payloads[0]["requestId"] == turn_payloads[1]["requestId"]
    assert [payload["expectedVersion"] for payload in turn_payloads] == [2, 2]


def test_stale_bound_route_without_evidence_builds_fresh_route(
    clean_page: Page, base_url: str
) -> None:
    """A stale pre-attempt binding is replaceable without losing the Door sketch."""
    page = clean_page
    _enter_app_shell_as_guest(page, base_url)
    page.evaluate("localStorage.clear(); sessionStorage.clear();")
    page.evaluate(
        """(() => {
          const conceptId = 'stale-empty-route';
          const sketch = 'Something remains after the first exposure.';
          const graphData = JSON.stringify({
            metadata: {
              core_thesis: 'Memory changes later response.',
              starting_map_context: sketch,
              source_mode: 'source_less',
              seda_route_bound_node_id: 'old-node',
              seda_route_bound_session_id: '11111111-1111-4111-8111-111111111111',
            },
            backbone: [{
              id: 'old-node', label: 'Old target', mechanism: 'Old mechanism.',
              learner_scaffold: { entry_prompt: 'Old question?' },
            }],
            clusters: [],
          });
          localStorage.setItem('learnops_concepts', JSON.stringify([{
            id: conceptId, name: 'Stale empty route QA', createdAt: Date.now(),
            state: 'growing', startingMapContext: sketch, graphData,
          }]));
          localStorage.setItem('learnops_active', conceptId);
          localStorage.setItem(`socratink:seda-session:v1:${conceptId}`, JSON.stringify({
            sessionId: '11111111-1111-4111-8111-111111111111',
            nodeId: 'old-node', latest: { caseComplete: false },
          }));
          localStorage.setItem(`socratink:training:v1:${conceptId}`, JSON.stringify({
            concept_id: conceptId, schema_version: 1,
            source_mode: 'source_less', grounding: 'learner_sketch',
            sketch: { text: sketch }, node_records: {},
          }));
        })()"""
    )
    page.route(
        re.compile(r".*/api/session/11111111-1111-4111-8111-111111111111$"),
        lambda route: route.fulfill(
            status=404,
            content_type="application/json",
            body=json.dumps({"error": "session not found"}),
        ),
    )
    fresh_sessions: list[dict] = []
    fresh_turns: list[dict] = []
    held_fresh_turns = []
    fresh_prompt = "Fresh question: why is the next response faster?"

    def fulfill_fresh_session(route) -> None:
        fresh_sessions.append(route.request.post_data_json)
        session_id = (
            "22222222-2222-4222-8222-222222222222"
            if len(fresh_sessions) == 1
            else "33333333-3333-4333-8333-333333333333"
        )
        route.fulfill(
            status=201,
            content_type="application/json",
            body=json.dumps({
                "sessionId": session_id,
                "sessionVersion": 1,
                "status": "awaiting_input",
                "awaiting": {"key": "launch_attempt", "ctaText": "First try"},
                "caseComplete": False,
            }),
        )

    def fulfill_fresh_turn(route) -> None:
        fresh_turns.append(route.request.post_data_json)
        if len(fresh_turns) == 1:
            held_fresh_turns.append(route)
            return
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "sessionId": "33333333-3333-4333-8333-333333333333",
                "sessionVersion": 2,
                "status": "awaiting_input",
                "awaiting": {"key": "cold_attempt", "ctaText": fresh_prompt},
                "sourceLessRoute": _seda_route_result(
                    node_id="fresh-node", prompt=fresh_prompt,
                ),
                "events": [_seda_route_event(node_id="fresh-node", prompt=fresh_prompt)],
                "caseComplete": False,
            }),
        )

    page.route(re.compile(r".*/api/session$"), fulfill_fresh_session)
    page.route(
        re.compile(r".*/api/session/[0-9a-f-]+/turn$"),
        fulfill_fresh_turn,
    )
    page.goto(f"{base_url}/session/stale-empty-route")
    page.locator(".concept-page-b2__attempt-input").fill("An unsent line.")
    page.locator(".concept-page-b2__attempt-save").click()
    expect(page.locator("#chamber-send")).to_have_text(
        "Build the first question again", timeout=20_000
    )
    expect(page.locator("#chamber-question")).not_to_contain_text("Try again")
    page.locator("#chamber-send").click()

    for _ in range(100):
        if held_fresh_turns:
            break
        page.wait_for_timeout(50)
    assert held_fresh_turns, "fresh route request was not held before reload"
    pending = page.evaluate(
        """() => {
          const concept = JSON.parse(localStorage.getItem('learnops_concepts'))[0];
          const graph = JSON.parse(concept.graphData);
          return {
            routeStatus: graph.metadata.route_status || null,
            graphNeutral: graph.metadata.graph_neutral ?? null,
            nodeId: graph.metadata.seda_route_bound_node_id || null,
            sessionId: graph.metadata.seda_route_bound_session_id || null,
          };
        }"""
    )
    assert pending == {
        "routeStatus": "pending_seda",
        "graphNeutral": True,
        "nodeId": None,
        "sessionId": None,
    }

    page.reload()
    reloaded_draft = "A draft written after the interrupted route request."
    expect(page.locator(".concept-page-b2__attempt-input")).to_be_visible(timeout=20_000)
    page.locator(".concept-page-b2__attempt-input").fill(reloaded_draft)
    page.locator(".concept-page-b2__attempt-save").click()

    expect(page.locator("#chamber-question")).to_have_text(fresh_prompt, timeout=20_000)
    expect(page.locator("#chamber-composer")).to_be_enabled()
    expect(page.locator("#chamber-composer")).to_have_value(reloaded_draft)
    expect(page.locator("#chamber-verdict")).to_contain_text(
        "Not recorded against this question."
    )
    assert fresh_sessions == [
        {"sourceLessDoorBootstrap": True},
        {"sourceLessDoorBootstrap": True},
    ]
    assert [turn["text"] for turn in fresh_turns] == [
        "Something remains after the first exposure.",
        "Something remains after the first exposure.",
    ]
    assert [turn["expectedVersion"] for turn in fresh_turns] == [1, 1]
    recovered = page.evaluate(
        """() => {
          const concept = JSON.parse(localStorage.getItem('learnops_concepts'))[0];
          const graph = JSON.parse(concept.graphData);
          const training = JSON.parse(localStorage.getItem('socratink:training:v1:stale-empty-route'));
          return {
            sketch: concept.startingMapContext,
            nodeId: graph.metadata.seda_route_bound_node_id,
            sessionId: graph.metadata.seda_route_bound_session_id,
            attempts: Object.values(training.node_records || {})
              .flatMap((record) => record.attempts || []).length,
          };
        }"""
    )
    assert recovered == {
        "sketch": "Something remains after the first exposure.",
        "nodeId": "fresh-node",
        "sessionId": "33333333-3333-4333-8333-333333333333",
        "attempts": 0,
    }


def test_completed_seda_case_projects_visible_evidence(
    page: Page, base_url: str
) -> None:
    """A completed SEDA case must surface as visible evidence, never solidified.

    The SEDA loop simulates spacing with fixed timestamps 20h apart. Projection
    must re-stamp attempts to real time so one sitting derives primed at most.
    """
    _enter_app_shell_as_guest(page, base_url)

    def fulfill_extract(route) -> None:
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "provisional_map": {
                    "metadata": {"core_thesis": "Immune memory speeds the next response."},
                    "backbone": [{"id": "b1", "principle": "Immune memory persists."}],
                    "clusters": [{
                        "id": "c1",
                        "label": "Memory cells",
                        "subnodes": [{
                            "id": "c1_s1",
                            "label": "Memory cells",
                            "mechanism": "Memory cells persist after exposure.",
                            "learner_scaffold": {
                                "entry_prompt": "Why is the second exposure faster?",
                                "task_cue": "Explain the role of memory cells.",
                            },
                        }],
                    }],
                },
            }),
        )

    def fulfill_session(route) -> None:
        route.fulfill(
            status=201,
            content_type="application/json",
            body=json.dumps({
                "sessionId": "projection-session-1",
                "sessionVersion": 1,
                "status": "awaiting_input",
                "awaiting": {"key": "launch_attempt", "ctaText": "Try your first explanation."},
                "learnerTranscript": [],
                "caseComplete": False,
                "record": None,
            }),
        )

    # The completed record carries backend node ids and the fixed simulated
    # timestamps (2026-05-15 cold, 2026-05-16 spaced) from lib/seda/constants.mjs.
    completed_record = {
        "sessionId": "projection-session-1",
        "sessionVersion": 3,
        "status": "complete",
        "awaiting": None,
        "learnerTranscript": [],
        "caseComplete": True,
        "record": {
            "concept_id": "immune-memory-persists",
            "training": {
                "node_records": {
                    "seda-node-1": {
                        "attempts": [
                            {
                                "id": "cold-1",
                                "at": "2026-05-15T10:00:00.000Z",
                                "user_text": "Memory cells remain after the first exposure.",
                                "classification": "strong",
                                "gaps": [],
                                "grader_version": "tui",
                                "kind": "cold",
                            },
                            {
                                "id": "spaced-1",
                                "at": "2026-05-16T06:00:00.000Z",
                                "user_text": "They respond faster on the next exposure.",
                                "classification": "strong",
                                "gaps": [],
                                "grader_version": "tui",
                                "kind": "spaced",
                            },
                        ],
                        "repairs": [],
                    },
                },
            },
        },
    }

    turn_texts: list[str] = []

    def fulfill_turn(route) -> None:
        turn_texts.append(route.request.post_data_json["text"])
        if len(turn_texts) == 1:
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({
                    "sessionId": "projection-session-1",
                    "sessionVersion": 2,
                    "status": "awaiting_input",
                    "awaiting": {
                        "key": "cold_attempt",
                        "ctaText": "Why is the second exposure faster?",
                    },
                    "learnerTranscript": [],
                    "events": [_seda_route_event()],
                    "sourceLessRoute": _seda_route_result(),
                    "caseComplete": False,
                    "record": None,
                }),
            )
            return
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(completed_record),
        )

    page.route("**/api/extract", fulfill_extract)
    page.route(re.compile(r".*/api/session$"), fulfill_session)
    page.route(re.compile(r".*/api/session/[^/]+/turn$"), fulfill_turn)

    page.locator("#nav-ignition").click()
    page.locator("#hero-single-input-field").fill(
        "I want to explain why vaccines create immune memory."
    )
    page.locator("#hero-cold-guess-field").fill(
        "The first exposure leaves cells that remember the pathogen."
    )
    page.locator("#hero-door-submit").click()
    expect(page.locator("#launch-pad-view")).to_be_hidden()

    expect(page.locator("#drill-chamber-view")).to_be_visible(timeout=20_000)
    # The Door sketch is consumed as the launch attempt before the room opens.
    # The first visible room answer must therefore be the recordable cold turn.
    page.wait_for_function(
        """() => {
          const conceptId = localStorage.getItem('learnops_active');
          const key = conceptId ? `socratink:seda-session:v1:${conceptId}` : null;
          if (!key) return false;
          const value = JSON.parse(localStorage.getItem(key) || 'null');
          return value?.sessionId && value?.latest?.awaiting?.key === 'cold_attempt';
        }""",
        timeout=20_000,
    )
    assert turn_texts == ["The first exposure leaves cells that remember the pathogen."]
    page.locator("#chamber-send").click()
    expect(page.locator("#chamber-hint")).to_have_text(
        "Write a sentence before checking."
    )
    page.locator("#chamber-composer").fill(
        "Memory cells remain after the first exposure and make the second response faster."
    )
    expect(page.locator("#chamber-hint")).to_have_text("A sentence is enough.")
    page.locator("#chamber-send").click()
    expect(page.locator("#chamber-verdict")).to_contain_text("Checked", timeout=20_000)
    expect(page.locator("#chamber-send")).to_have_text("See what to study")
    page.locator("#chamber-send").click()
    expect(page.locator("#drill-chamber-view")).to_be_hidden()

    projected = page.wait_for_function(
        """() => {
          const conceptId = localStorage.getItem('learnops_active');
          const key = conceptId ? `socratink:training:v1:${conceptId}` : null;
          if (!key) return null;
          const value = JSON.parse(localStorage.getItem(key) || 'null');
          const record = value?.node_records?.['c1_s1'];
          return record?.attempts?.length && record?.study_revealed_at
            ? { attempts: record.attempts, study_revealed_at: record.study_revealed_at }
            : null;
        }""",
        timeout=20_000,
    ).json_value()

    attempts = projected["attempts"]
    assert len(attempts) == 2
    assert attempts[0]["user_text"] == "Memory cells remain after the first exposure."
    # Product truth: re-stamped to real time, so the simulated ~20h gap is gone
    # and a single sitting cannot clear the 18h spacing gate for solidified.
    now_ms = page.evaluate("Date.now()")
    for attempt in attempts:
        stamped_ms = page.evaluate("(iso) => Date.parse(iso)", attempt["at"])
        assert abs(now_ms - stamped_ms) < 5 * 60 * 1000

    # Assert the projected *derived state* directly, not just the visible text:
    # one re-stamped sitting must derive `primed`, never `solidified`.
    derived_state = page.evaluate(
        """async () => {
          const { deriveNodeTraining } = await import('/js/training-derive.js');
          const conceptId = localStorage.getItem('learnops_active');
          const key = `socratink:training:v1:${conceptId}`;
          const training = JSON.parse(localStorage.getItem(key) || 'null');
          return deriveNodeTraining(training.node_records['c1_s1']).state;
        }"""
    )
    assert derived_state == "primed"

    page.reload()
    # The evidence artifact renders the strongest/latest reconstruction turn.
    expect(page.locator(".concept-page-b2__evidence")).to_contain_text(
        "They respond faster on the next exposure.", timeout=20_000
    )
    # Never solidified from one sitting.
    expect(page.locator(".concept-page-b2__evidence")).not_to_contain_text(
        "Solidified", timeout=20_000
    )

    # Exercise the pure projection contract across its remaining branches in the
    # browser: fresh-training fallback, the study-reveal carry, and the
    # per-session idempotency guard that stops resume from duplicating attempts.
    contract = page.evaluate(
        """async () => {
          const { projectCompletedSedaRecord } =
            await import('/js/seda-evidence-projection.js');
          const record = {
            training: {
              node_records: {
                'backend-node': {
                  attempts: [{
                    id: 'cold-1', at: '2026-05-15T10:00:00.000Z',
                    user_text: 'a', classification: 'strong', gaps: [],
                    grader_version: 'tui', kind: 'cold',
                  }],
                  repairs: [],
                  study_revealed_at: '2026-05-15T10:12:00.000Z',
                },
              },
            },
          };
          const now = new Date().toISOString();
          const first = projectCompletedSedaRecord({
            training: null, conceptId: 'c', nodeId: 'n', sessionId: 'sess-x', now, record,
          });
          const repeat = projectCompletedSedaRecord({
            training: first, conceptId: 'c', nodeId: 'n', sessionId: 'sess-x', now, record,
          });
          const node = first.node_records['n'];
          return {
            builtFreshConcept: first.concept_id === 'c',
            studyRevealedAt: node.study_revealed_at,
            attemptAt: node.attempts[0].at,
            now,
            idempotent: repeat === null,
          };
        }"""
    )
    assert contract["builtFreshConcept"] is True
    assert contract["idempotent"] is True
    # study_revealed_at is re-stamped to real time, not the simulated constant.
    assert contract["studyRevealedAt"] == contract["now"]
    assert contract["attemptAt"] == contract["now"]


def test_direct_loop_route_redirects_to_app_shell(
    page: Page, base_url: str
) -> None:
    """Backcompat /loop should not expose the terminal UI to learners by default."""
    _enter_app_shell_as_guest(page, base_url)
    page.goto(f"{base_url}/loop")
    expect(page).to_have_url(re.compile(r"/$"))
    expect(page.locator("body")).not_to_contain_text("socratink loop")
    expect(page.locator("#nav-ignition")).to_be_visible()


def test_concept_entry_mutation_preserves_active_later_entry(
    page: Page, base_url: str
) -> None:
    """Study reveal on a later entry must not snap back to an earlier gap."""
    _enter_app_shell_as_guest(page, base_url)
    page.evaluate("localStorage.clear(); sessionStorage.clear();")
    page.evaluate(
        """(() => {
            const graphData = JSON.stringify({
                metadata: {
                    source_title: 'Active Entry QA source',
                    starting_map_context: 'Learner rough sketch.',
                    map_maturity: 'provisional',
                },
                backbone: [
                    {
                        id: 'entry-one',
                        label: 'Earlier gap',
                        purpose: 'This earlier entry should not steal focus.',
                        study_note: 'Entry one note.',
                    },
                    {
                        id: 'entry-two',
                        label: 'Later target',
                        purpose: 'Reveal this later entry study note.',
                        study_note: 'Entry two note.',
                    },
                ],
                clusters: [],
            });
            localStorage.setItem('learnops_concepts', JSON.stringify([{
                id: 'qa-active-entry-concept',
                name: 'Active Entry QA',
                createdAt: Date.now(),
                state: 'growing',
                graphData,
            }]));
            localStorage.setItem('socratink:training:v1:qa-active-entry-concept', JSON.stringify({
                concept_id: 'qa-active-entry-concept',
                schema_version: 1,
                node_records: {
                    'entry-one': {
                        attempts: [{
                            id: 'entry-one-attempt',
                            at: '2026-05-15T10:00:00.000Z',
                            user_text: 'Earlier strong reconstruction.',
                            classification: 'strong',
                            gaps: [],
                            grader_version: 'qa',
                        }],
                        study_revealed_at: '2026-05-15T10:05:00.000Z',
                        repairs: [],
                    },
                    'entry-two': {
                        attempts: [{
                            id: 'entry-two-attempt',
                            at: '2026-05-15T10:10:00.000Z',
                            user_text: 'Later strong reconstruction.',
                            classification: 'strong',
                            gaps: [],
                            grader_version: 'qa',
                        }],
                        repairs: [],
                    },
                },
            }));
        })()"""
    )

    page.locator("#nav-library").click()
    page.locator(".library-card-vault", has_text="Active Entry QA").click()
    page.locator('.concept-page-b2__route-item[data-entry-id="entry-two"]').click()
    expect(page.locator(".concept-page-b2__entry-eyebrow")).to_have_text(
        "Your draft"
    )
    page.locator(".concept-page-b2__entry-cta").click()
    expect(page.locator(".concept-page-b2__route-item.is-active")).to_have_attribute(
        "data-entry-id", "entry-two"
    )
    expect(page.locator(".concept-page-b2__study-note")).to_contain_text(
        "Entry two note."
    )


def test_localhost_concept_page_cold_attempt_appends_training_evidence(
    page: Page, base_url: str
) -> None:
    """Concept-page memory attempt submits to the grader and stores verbatim text."""
    drill_calls: list[dict] = []

    def fulfill_drill(route):
        payload = route.request.post_data_json
        drill_calls.append(payload)
        if len(drill_calls) == 1:
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(
                    {
                        "agent_response": "Malformed grader response.",
                        "generative_commitment": True,
                        "answer_mode": "attempt",
                        "score_eligible": True,
                        "help_request_reason": "none",
                        "classification": None,
                        "gap_description": None,
                        "routing": "NEXT",
                        "response_tier": None,
                        "response_band": None,
                        "tier_reason": None,
                        "node_id": payload["node_id"],
                        "probe_count": 0,
                        "nodes_drilled": 1,
                        "attempt_turn_count": 1,
                        "help_turn_count": 0,
                        "graph_mutated": False,
                        "ux_reward_emitted": False,
                        "session_terminated": False,
                        "termination_reason": None,
                        "prompt_version": "qa-inline-malformed",
                    }
                ),
            )
            return
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "agent_response": "Your first attempt gives the study note a target.",
                    "generative_commitment": True,
                    "answer_mode": "attempt",
                    "score_eligible": True,
                    "help_request_reason": "none",
                    "classification": "shallow",
                    "gap_description": "Names sodium flow but misses that voltage threshold opens the gate.",
                    "routing": "NEXT",
                    "response_tier": 2,
                    "response_band": "link",
                    "tier_reason": "The answer misses the channel-opening mechanism.",
                    "node_id": payload["node_id"],
                    "probe_count": 0,
                    "nodes_drilled": 1,
                    "attempt_turn_count": 1,
                    "help_turn_count": 0,
                    "graph_mutated": False,
                    "ux_reward_emitted": False,
                    "session_terminated": False,
                    "termination_reason": None,
                    "prompt_version": "qa-inline-attempt",
                }
            ),
        )

    page.route("**/api/drill", fulfill_drill)
    _enter_app_shell_as_guest(page, base_url)
    page.evaluate("localStorage.clear(); sessionStorage.clear();")
    page.evaluate(
        """(() => {
            const graphData = JSON.stringify({
                metadata: {
                    source_title: 'Cold Attempt Truth QA source-less route',
                    starting_map_context: 'Learner only remembers sodium flow.',
                    map_maturity: 'provisional',
                },
                backbone: [{
                    id: 'cold-node',
                    label: 'Sodium threshold',
                    purpose: 'Explain what starts the sodium flow.',
                    study_note: 'Voltage threshold opens sodium channels before the gradient drives flow.',
                    drill_status: null,
                }],
                clusters: [],
            });
            localStorage.setItem('learnops_concepts', JSON.stringify([{
                id: 'qa-cold-attempt-concept',
                name: 'Cold Attempt Truth QA',
                createdAt: Date.now(),
                state: 'growing',
                contentPreview: 'SOURCE PREVIEW SHOULD NOT APPEAR',
                contentType: null,
                startingMapContext: 'Learner only remembers sodium flow.',
                graphData,
            }]));
        })()"""
    )

    page.locator("#nav-library").click()
    page.locator(".library-card-vault", has_text="Cold Attempt Truth QA").click()
    expect(page.locator("#concept-header-title")).to_have_text("Cold Attempt Truth QA")
    expect(page.locator(".concept-page-b2__attempt")).to_be_visible()
    expect(page.get_by_label("Your reconstruction")).to_be_visible()
    expect(page.locator(".concept-page-b2__attempt-field .concept-page-b2__field-label")).to_have_class(
        "concept-page-b2__field-label visually-hidden"
    )
    expect(page.locator(".concept-page-b2__study-note")).to_have_count(0)
    save_button = page.locator(".concept-page-b2__attempt-save")
    expect(save_button).to_be_disabled()
    expect(save_button).to_have_attribute("aria-disabled", "true")

    learner_text = "  Sodium flows in because there is more outside.  "
    page.locator(".concept-page-b2__attempt-input").fill(learner_text)
    expect(save_button).to_be_enabled()
    expect(save_button).to_have_attribute("aria-disabled", "false")
    save_button.click()
    expect(page.locator("[data-attempt-error]")).to_have_text(
        "The system could not record this yet. Try again."
    )
    expect(save_button).to_have_text("Save draft")
    expect(save_button).not_to_have_attribute("aria-busy", "true")
    page.locator(".concept-page-b2__attempt-save").click()
    expect(page.locator(".concept-page-b2__entry-eyebrow")).to_have_text(
        "Your draft"
    )
    expect(page.locator(".concept-page-b2__evidence")).to_be_focused()
    expect(page.locator(".concept-page-b2__entry-cta")).to_have_text(
        "Reveal notes and compare"
    )

    assert len(drill_calls) == 2
    assert drill_calls[1]["concept_id"] == "qa-cold-attempt-concept"
    assert drill_calls[1]["node_id"] == "cold-node"
    assert drill_calls[1]["messages"][-1]["content"] == learner_text
    stored = page.evaluate(
        """() => JSON.parse(localStorage.getItem('socratink:training:v1:qa-cold-attempt-concept'))"""
    )
    attempt = stored["node_records"]["cold-node"]["attempts"][0]
    assert attempt["kind"] == "cold"
    assert attempt["user_text"] == learner_text
    assert attempt["classification"] == "thin"
    assert attempt["gaps"][0]["description"] == (
        "Names sodium flow but misses that voltage threshold opens the gate."
    )


def test_concept_title_preserves_real_source_less_route_suffix(
    clean_page: Page, base_url: str
) -> None:
    """Only the exact legacy synthetic title is collapsed to the concept name."""
    _enter_app_shell_as_guest(clean_page, base_url)
    clean_page.evaluate("localStorage.clear(); sessionStorage.clear();")
    clean_page.evaluate(
        """(() => {
            const title = 'Designing a source-less route';
            const graphData = JSON.stringify({
                metadata: { source_title: title, map_maturity: 'provisional' },
                backbone: [{ id: 'title-node', label: 'Title node', purpose: 'Reconstruct it.' }],
                clusters: [],
            });
            localStorage.setItem('learnops_concepts', JSON.stringify([{
                id: 'qa-source-less-title',
                name: title,
                createdAt: Date.now(),
                state: 'growing',
                graphData,
            }]));
        })()"""
    )

    clean_page.locator("#nav-library").click()
    clean_page.locator(".library-card-vault", has_text="Designing a source-less route").click()
    expect(clean_page.locator("#concept-header-title")).to_have_text(
        "Designing a source-less route"
    )


def test_localhost_inline_attempt_stale_response_does_not_mutate_active_concept(
    page: Page, base_url: str
) -> None:
    """A late inline grader response cannot write through after concept switch."""
    _enter_app_shell_as_guest(page, base_url)
    page.evaluate("localStorage.clear(); sessionStorage.clear();")
    page.evaluate(
        """(() => {
            const originalFetch = window.fetch.bind(window);
            window.__staleDrillPayloads = [];
            window.__releaseStaleDrill = null;
            window.fetch = (input, init = {}) => {
                const path = typeof input === 'string' ? input : input?.url;
                if (path === '/api/drill') {
                    const payload = JSON.parse(init.body || '{}');
                    window.__staleDrillPayloads.push(payload);
                    return new Promise((resolve) => {
                        window.__releaseStaleDrill = () => resolve(new Response(JSON.stringify({
                            agent_response: 'Recorded too late.',
                            generative_commitment: true,
                            answer_mode: 'attempt',
                            score_eligible: true,
                            help_request_reason: 'none',
                            classification: 'shallow',
                            gap_description: 'The delayed response should be ignored.',
                            routing: 'NEXT',
                            response_tier: 2,
                            response_band: 'link',
                            tier_reason: 'Delayed fixture.',
                            node_id: payload.node_id,
                            probe_count: 0,
                            nodes_drilled: 1,
                            attempt_turn_count: 1,
                            help_turn_count: 0,
                            graph_mutated: false,
                            ux_reward_emitted: false,
                            session_terminated: false,
                            termination_reason: null,
                            prompt_version: 'qa-inline-stale',
                        }), {
                            status: 200,
                            headers: { 'Content-Type': 'application/json' },
                        }));
                    });
                }
                return originalFetch(input, init);
            };
        })()"""
    )
    page.evaluate(
        """(() => {
            const conceptA = {
                id: 'qa-stale-inline-a',
                name: 'Stale Inline A',
                createdAt: Date.now(),
                state: 'growing',
                contentPreview: 'A preview should stay hidden.',
                graphData: JSON.stringify({
                    metadata: {
                        source_title: 'Stale Inline A source',
                        starting_map_context: 'Learner starts on A.',
                    },
                    backbone: [{
                        id: 'stale-a-node',
                        label: 'Stale A node',
                        mechanism: 'A canonical mechanism.',
                        study_note: 'A study note.',
                        drill_status: null,
                    }],
                    clusters: [],
                }),
            };
            const conceptB = {
                id: 'qa-stale-inline-b',
                name: 'Stale Inline B',
                createdAt: Date.now() + 1,
                state: 'growing',
                contentPreview: 'B preview should stay hidden.',
                graphData: JSON.stringify({
                    metadata: {
                        source_title: 'Stale Inline B source',
                        starting_map_context: 'Learner switched to B.',
                    },
                    backbone: [{
                        id: 'stale-b-node',
                        label: 'Stale B node',
                        study_note: 'B study note.',
                        drill_status: null,
                    }],
                    clusters: [],
                }),
            };
            localStorage.setItem('learnops_concepts', JSON.stringify([conceptA, conceptB]));
        })()"""
    )

    page.locator("#nav-library").click()
    page.locator(".library-card-vault", has_text="Stale Inline A").click()
    expect(page.locator(".concept-page-b2__attempt")).to_be_visible()
    page.locator(".concept-page-b2__attempt-input").fill("A learner answer that returns late.")
    page.locator(".concept-page-b2__attempt-save").click()
    page.wait_for_function("() => window.__staleDrillPayloads?.length === 1")
    page.evaluate("App.openLibraryConcept('qa-stale-inline-b')")
    page.evaluate("window.__releaseStaleDrill()")

    expect(page.locator("#concept-header-title")).to_contain_text("Stale Inline B source")
    page.wait_for_timeout(250)
    assert (
        page.evaluate(
            """localStorage.getItem('socratink:training:v1:qa-stale-inline-a')"""
        )
        is None
    )
    concepts = page.evaluate("""JSON.parse(localStorage.getItem('learnops_concepts'))""")
    concept_a = next(item for item in concepts if item["id"] == "qa-stale-inline-a")
    concept_b = next(item for item in concepts if item["id"] == "qa-stale-inline-b")
    graph_a = json.loads(concept_a["graphData"])
    graph_b = json.loads(concept_b["graphData"])
    assert graph_a["backbone"][0]["drill_status"] is None
    assert graph_b["backbone"][0]["drill_status"] is None


def test_localhost_legacy_inline_redrill_keeps_spaced_semantics(
    page: Page, base_url: str
) -> None:
    """Legacy post-cold entries submit inline reconstruction as re-drill."""
    drill_calls: list[dict] = []

    def fulfill_drill(route):
        payload = route.request.post_data_json
        drill_calls.append(payload)
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "agent_response": "Solid re-drill.",
                    "generative_commitment": False,
                    "answer_mode": "attempt",
                    "score_eligible": True,
                    "help_request_reason": "none",
                    "classification": "solid",
                    "gap_description": None,
                    "routing": "NEXT",
                    "response_tier": 3,
                    "response_band": "mechanism",
                    "tier_reason": "The answer names the mechanism.",
                    "node_id": payload["node_id"],
                    "probe_count": 0,
                    "nodes_drilled": 1,
                    "attempt_turn_count": 2,
                    "help_turn_count": 0,
                    "graph_mutated": False,
                    "ux_reward_emitted": False,
                    "session_terminated": False,
                    "termination_reason": None,
                    "prompt_version": "qa-inline-redrill",
                }
            ),
        )

    page.route("**/api/drill", fulfill_drill)
    _enter_app_shell_as_guest(page, base_url)
    page.evaluate("localStorage.clear(); sessionStorage.clear();")
    page.evaluate(
        """(() => {
            const graphData = JSON.stringify({
                metadata: {
                    source_title: 'Legacy Re-drill QA source',
                    starting_map_context: 'The learner already made a cold attempt before this schema existed.',
                    map_maturity: 'provisional',
                },
                backbone: [{
                    id: 'legacy-redrill-node',
                    label: 'Legacy re-drill target',
                    purpose: 'Explain the mechanism in learner-facing words.',
                    mechanism: 'Canonical mechanism answer key.',
                    study_note: 'The target mechanism opens before downstream flow.',
                    drill_status: 'drilled',
                    drill_phase: null,
                }],
                clusters: [],
            });
            localStorage.setItem('learnops_concepts', JSON.stringify([{
                id: 'qa-legacy-redrill-concept',
                name: 'Legacy Re-drill Truth QA',
                createdAt: Date.now(),
                state: 'growing',
                contentPreview: 'SOURCE PREVIEW SHOULD NOT APPEAR',
                contentType: null,
                startingMapContext: 'The learner already made a cold attempt before this schema existed.',
                graphData,
            }]));
            localStorage.setItem('learnops_active', 'qa-legacy-redrill-concept');
            localStorage.setItem('socratink:training:v1:qa-legacy-redrill-concept', JSON.stringify({
                concept_id: 'qa-legacy-redrill-concept',
                schema_version: 1,
                source_mode: 'source_less',
                grounding: 'learner_sketch',
                source_ref: null,
                sketch: {
                    text: 'The learner already made a cold attempt before this schema existed.',
                    at: '2026-05-15T09:00:00.000Z',
                },
                node_records: {
                    'legacy-redrill-node': {
                        attempts: [{
                            id: 'legacy-cold',
                            kind: 'cold',
                            at: '2026-05-15T10:00:00.000Z',
                            user_text: 'The learner made a first attempt before this schema existed.',
                            classification: 'strong',
                            gaps: [],
                            grader_version: 'qa',
                        }],
                        repairs: [],
                    },
                },
            }));
        })()"""
    )
    inspect_action = page.evaluate(
        """() => App.getNodeInspectAction({
            id: 'legacy-redrill-node',
            type: 'backbone',
            available: true,
        })"""
    )
    assert inspect_action["kind"] == "resume-study"
    assert inspect_action["secondaryAction"]["kind"] == "start-repair-reps"

    page.locator("#nav-library").click()
    page.locator(".library-card-vault", has_text="Legacy Re-drill Truth QA").click()
    expect(page.locator(".concept-page-b2__entry-eyebrow")).to_have_text(
        "Compare notes"
    )
    expect(page.locator(".concept-page-b2__entry-cta")).to_have_text("Reconstruct from memory")
    page.locator(".concept-page-b2__entry-cta").click()
    page.locator(".concept-page-b2__attempt-input").fill(
        "The mechanism opens first, then the downstream flow follows."
    )
    page.locator(".concept-page-b2__attempt-save").click()

    expect(page.locator(".concept-page-b2__entry-eyebrow")).to_have_text("Solid spaced reconstruction")
    expect(page.locator(".concept-page-b2__entry-cta")).to_have_count(0)
    assert len(drill_calls) == 1
    assert drill_calls[0]["drill_mode"] == "re_drill"
    assert drill_calls[0]["client_turn_index"] == 2
    assert drill_calls[0]["attempt_turn_count"] == 1
    assert drill_calls[0]["node_mechanism"] == "Canonical mechanism answer key."
    graph = page.evaluate(
        """() => JSON.parse(JSON.parse(localStorage.getItem('learnops_concepts'))[0].graphData)"""
    )
    assert graph["backbone"][0]["drill_status"] == "solidified"
    stored = page.evaluate(
        """() => JSON.parse(localStorage.getItem('socratink:training:v1:qa-legacy-redrill-concept'))"""
    )
    assert len(stored["node_records"]["legacy-redrill-node"]["attempts"]) == 2
    assert (
        stored["node_records"]["legacy-redrill-node"]["attempts"][1]["user_text"]
        == "The mechanism opens first, then the downstream flow follows."
    )


def test_localhost_concept_page_corrupt_training_storage_recovers_and_records_attempt(
    page: Page, base_url: str
) -> None:
    """Corrupt local training storage should recover into a valid attempt record."""
    drill_calls: list[dict] = []

    def fulfill_drill(route):
        payload = route.request.post_data_json
        drill_calls.append(payload)
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "agent_response": "Recorded.",
                    "generative_commitment": True,
                    "answer_mode": "attempt",
                    "score_eligible": True,
                    "help_request_reason": "none",
                    "classification": "solid",
                    "gap_description": None,
                    "routing": "NEXT",
                    "response_tier": 3,
                    "response_band": "mechanism",
                    "tier_reason": "The answer names the mechanism.",
                    "node_id": payload["node_id"],
                    "probe_count": 0,
                    "nodes_drilled": 1,
                    "attempt_turn_count": 1,
                    "help_turn_count": 0,
                    "graph_mutated": False,
                    "ux_reward_emitted": False,
                    "session_terminated": False,
                    "termination_reason": None,
                    "prompt_version": "qa-inline-attempt",
                }
            ),
        )

    page.route("**/api/drill", fulfill_drill)
    _enter_app_shell_as_guest(page, base_url)
    page.evaluate("localStorage.clear(); sessionStorage.clear();")
    page.evaluate(
        """(() => {
            const graphData = JSON.stringify({
                metadata: {
                    source_title: 'Corrupt Storage QA source',
                    starting_map_context: 'Learner rough sketch.',
                    map_maturity: 'provisional',
                },
                backbone: [{
                    id: 'corrupt-node',
                    label: 'Corrupt storage target',
                    purpose: 'Explain the mechanism.',
                    study_note: 'The target mechanism opens before downstream flow.',
                    drill_status: null,
                }],
                clusters: [],
            });
            localStorage.setItem('learnops_concepts', JSON.stringify([{
                id: 'qa-corrupt-training-concept',
                name: 'Corrupt Training QA',
                createdAt: Date.now(),
                state: 'growing',
                contentPreview: 'SOURCE PREVIEW SHOULD NOT APPEAR',
                contentType: null,
                startingMapContext: 'Learner rough sketch.',
                graphData,
            }]));
            localStorage.setItem('socratink:training:v1:qa-corrupt-training-concept', '{');
        })()"""
    )

    page.locator("#nav-library").click()
    page.locator(".library-card-vault", has_text="Corrupt Training QA").click()
    expect(page.locator(".concept-page-b2__attempt")).to_be_visible()
    page.locator(".concept-page-b2__attempt-input").fill(
        "The mechanism opens first, then the downstream flow follows."
    )
    save_button = page.locator(".concept-page-b2__attempt-save")
    save_button.click()
    expect(page.locator(".concept-page-b2__entry-eyebrow")).to_have_text(
        "Your draft"
    )
    assert len(drill_calls) == 1
    assert drill_calls[0]["node_id"] == "corrupt-node"
    assert drill_calls[0]["drill_mode"] == "cold_attempt"
    assert drill_calls[0]["messages"][-1]["content"] == (
        "The mechanism opens first, then the downstream flow follows."
    )

    stored = page.evaluate(
        """() => JSON.parse(localStorage.getItem('socratink:training:v1:qa-corrupt-training-concept'))"""
    )
    attempt = stored["node_records"]["corrupt-node"]["attempts"][0]
    assert attempt["kind"] == "cold"
    assert attempt["classification"] == "strong"
    assert attempt["user_text"] == (
        "The mechanism opens first, then the downstream flow follows."
    )


def test_localhost_inline_scaffold_response_keeps_attempt_retryable(
    page: Page, base_url: str
) -> None:
    """Valid scaffold/help responses are nudges, not storage failures."""
    drill_calls: list[dict] = []

    def fulfill_drill(route):
        payload = route.request.post_data_json
        drill_calls.append(payload)
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "agent_response": "No problem at all. Let's think about how the mechanism could work before reading the answer.",
                    "generative_commitment": False,
                    "answer_mode": "help_request",
                    "score_eligible": False,
                    "help_request_reason": "explicit_unknown",
                    "classification": None,
                    "gap_description": "Learner produced zero schema; nudge to guess.",
                    "routing": "SCAFFOLD",
                    "response_tier": None,
                    "response_band": None,
                    "tier_reason": None,
                    "node_id": payload["node_id"],
                    "probe_count": 0,
                    "nodes_drilled": 1,
                    "attempt_turn_count": 0,
                    "help_turn_count": 1,
                    "graph_mutated": False,
                    "ux_reward_emitted": False,
                    "session_terminated": False,
                    "termination_reason": None,
                    "prompt_version": "qa-inline-scaffold",
                }
            ),
        )

    page.route("**/api/drill", fulfill_drill)
    _enter_app_shell_as_guest(page, base_url)
    _wait_for_app_settled(page)
    page.evaluate("localStorage.clear(); sessionStorage.clear();")
    page.evaluate(
        """(() => {
            const graphData = JSON.stringify({
                metadata: {
                    source_title: 'Inline Scaffold QA source',
                    starting_map_context: 'Learner rough sketch.',
                    map_maturity: 'provisional',
                },
                backbone: [{
                    id: 'scaffold-node',
                    label: 'Scaffold target',
                    purpose: 'Explain the mechanism.',
                    study_note: 'The target mechanism opens before downstream flow.',
                    drill_status: null,
                }],
                clusters: [],
            });
            localStorage.setItem('learnops_concepts', JSON.stringify([{
                id: 'qa-inline-scaffold-concept',
                name: 'Inline Scaffold QA',
                createdAt: Date.now(),
                state: 'growing',
                contentPreview: 'SOURCE PREVIEW SHOULD NOT APPEAR',
                contentType: null,
                startingMapContext: 'Learner rough sketch.',
                graphData,
            }]));
        })()"""
    )

    page.locator("#nav-library").click()
    page.locator(".library-card-vault", has_text="Inline Scaffold QA").click()
    expect(page.locator(".concept-page-b2__attempt")).to_be_visible()
    page.locator(".concept-page-b2__attempt-input").fill("I do not know.")
    save_button = page.locator(".concept-page-b2__attempt-save")
    save_button.click()

    expect(page.locator("[data-attempt-error]")).to_have_text(
        "Make one concrete guess before study appears."
    )
    expect(page.locator(".concept-page-b2__attempt")).not_to_contain_text(
        "No problem at all"
    )
    expect(save_button).to_be_enabled()
    expect(save_button).to_have_text("Save draft")
    expect(save_button).not_to_have_attribute("aria-busy", "true")
    assert len(drill_calls) == 1
    assert (
        page.evaluate(
            """localStorage.getItem('socratink:training:v1:qa-inline-scaffold-concept')"""
        )
        is None
    )


def test_localhost_inline_non_score_eligible_attempt_is_not_evidence(
    page: Page, base_url: str
) -> None:
    """A classified but non-score-eligible drill turn must not become evidence."""
    drill_calls: list[dict] = []

    def fulfill_drill(route):
        payload = route.request.post_data_json
        drill_calls.append(payload)
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "agent_response": "This turn is not eligible to score.",
                    "generative_commitment": False,
                    "answer_mode": "attempt",
                    "score_eligible": False,
                    "help_request_reason": "none",
                    "classification": "shallow",
                    "gap_description": "Classifier returned feedback for a non-recordable turn.",
                    "routing": "NEXT",
                    "response_tier": 2,
                    "response_band": "link",
                    "tier_reason": "Non-score eligible turn should remain non-evidence.",
                    "node_id": payload["node_id"],
                    "probe_count": 0,
                    "nodes_drilled": 1,
                    "attempt_turn_count": 0,
                    "help_turn_count": 0,
                    "graph_mutated": False,
                    "ux_reward_emitted": False,
                    "session_terminated": False,
                    "termination_reason": None,
                    "prompt_version": "qa-inline-unscored-attempt",
                }
            ),
        )

    page.route("**/api/drill", fulfill_drill)
    _enter_app_shell_as_guest(page, base_url)
    page.evaluate("localStorage.clear(); sessionStorage.clear();")
    page.evaluate(
        """(() => {
            const graphData = JSON.stringify({
                metadata: {
                    source_title: 'Unscored Attempt QA source',
                    starting_map_context: 'Learner rough sketch.',
                    map_maturity: 'provisional',
                },
                backbone: [{
                    id: 'unscored-node',
                    label: 'Unscored target',
                    purpose: 'Explain the mechanism.',
                    study_note: 'The target mechanism opens before downstream flow.',
                    drill_status: null,
                }],
                clusters: [],
            });
            localStorage.setItem('learnops_concepts', JSON.stringify([{
                id: 'qa-inline-unscored-concept',
                name: 'Inline Unscored QA',
                createdAt: Date.now(),
                state: 'growing',
                contentPreview: 'SOURCE PREVIEW SHOULD NOT APPEAR',
                contentType: null,
                startingMapContext: 'Learner rough sketch.',
                graphData,
            }]));
        })()"""
    )

    page.locator("#nav-library").click()
    page.locator(".library-card-vault", has_text="Inline Unscored QA").click()
    expect(page.locator(".concept-page-b2__attempt")).to_be_visible()
    page.locator(".concept-page-b2__attempt-input").fill(
        "The mechanism opens first."
    )
    save_button = page.locator(".concept-page-b2__attempt-save")
    save_button.click()

    expect(page.locator("[data-attempt-error]")).to_have_text(
        "The system could not record this yet. Try again."
    )
    expect(save_button).to_be_enabled()
    expect(save_button).to_have_text("Save draft")
    expect(save_button).not_to_have_attribute("aria-busy", "true")
    assert len(drill_calls) == 1
    assert (
        page.evaluate(
            """localStorage.getItem('socratink:training:v1:qa-inline-unscored-concept')"""
        )
        is None
    )


def test_drawer_toggle_remains_visible_in_concept_view(
    clean_page: Page, base_url: str
) -> None:
    """The sidebar control must stay available after entering a concept."""
    _seed_one_concept(clean_page)
    _enter_app_shell_as_guest(clean_page, base_url)

    toggle = clean_page.locator("#drawer-toggle")
    expect(toggle).to_be_visible()
    drawer = clean_page.locator("#drawer")
    assert drawer.get_attribute("data-open") == "true"
    drawer_box = drawer.bounding_box()
    toggle_box = toggle.bounding_box()
    assert drawer_box is not None
    assert toggle_box is not None
    assert toggle_box["x"] + toggle_box["width"] <= drawer_box["x"] + drawer_box["width"]

    clean_page.locator(".concept-item", has_text="Test Concept").click()
    expect(clean_page.locator("#concept-header-title")).to_contain_text("Test Concept")
    expect(toggle).to_be_visible()
    assert drawer.get_attribute("data-open") == "true"
    assert clean_page.locator("body").get_attribute("data-drawer-open") == "true"

    clean_page.locator("#nav-library").click()
    clean_page.locator(".library-card-vault", has_text="Test Concept").click()
    expect(clean_page.locator("#concept-header-title")).to_contain_text("Test Concept")
    expect(toggle).to_be_visible()


def test_feedback_button_keeps_sidebar_open(
    clean_page: Page, base_url: str
) -> None:
    """Feedback is an overlay action, not a navigation view that collapses the shell."""
    _enter_app_shell_as_guest(clean_page, base_url)

    expect(clean_page.locator("#drawer")).to_be_visible()
    assert clean_page.locator("#drawer").get_attribute("data-open") == "true"

    clean_page.locator("#nav-feedback").click()

    expect(clean_page.locator("#feedback-overlay")).to_be_visible()
    expect(clean_page.locator("#feedback-desc")).to_have_text(
        "Share a bug, rough edge, or idea. A 9 or 10 means the UX feels ready for a new customer."
    )
    expect(clean_page.locator("#feedback-submit")).to_have_text("Send Feedback")
    clean_page.locator("#feedback-submit").click()
    expect(clean_page.locator("#feedback-status")).to_have_text(
        "Message must be at least 10 characters."
    )
    assert clean_page.locator("#drawer").get_attribute("data-open") == "true"
    assert clean_page.locator("body").get_attribute("data-drawer-open") == "true"


def test_feedback_submit_reenables_on_reopen(
    clean_page: Page, base_url: str
) -> None:
    """A successful feedback send must not leave the next feedback modal disabled."""
    feedback_payloads = []
    _enter_app_shell_as_guest(clean_page, base_url)
    clean_page.route(
        "**/api/feedback",
        lambda route: (
            feedback_payloads.append(route.request.post_data_json),
            route.fulfill(
                status=200,
                content_type="application/json",
                body='{"ok": true}',
            ),
        ),
    )

    clean_page.locator("#nav-feedback").click()
    clean_page.locator("#feedback-ux-rating").select_option("9")
    clean_page.locator("#feedback-submit").click()

    expect(clean_page.locator("#feedback-status")).to_have_text(
        "Thank you! Feedback captured."
    )
    assert feedback_payloads == [{"message": "UX feel: 9/10"}]
    clean_page.locator(".modal-close").click()

    clean_page.locator("#nav-feedback").click()

    expect(clean_page.locator("#feedback-submit")).to_be_enabled()
    expect(clean_page.locator("#feedback-message")).to_have_value("")
    expect(clean_page.locator("#feedback-ux-rating")).to_have_value("")


def test_feedback_custom_moment_rejects_invalid_rating(
    clean_page: Page, base_url: str
) -> None:
    """Moment feedback should explain the moment and reject invalid scores."""
    _enter_app_shell_as_guest(clean_page, base_url)

    clean_page.evaluate("window.Feedback.show({ focus: 'rating', moment: 'focus mode' })")

    expect(clean_page.locator("#feedback-overlay")).to_be_visible()
    expect(clean_page.locator("#feedback-desc")).to_have_text(
        "How did the focus mode step feel? A 9 or 10 means the UX feels ready for a new customer."
    )
    clean_page.locator("#feedback-submit").click()
    expect(clean_page.locator("#feedback-status")).to_have_text(
        "Please rate this moment 1-10."
    )
    expect(clean_page.locator("#feedback-ux-rating")).to_be_focused()

    clean_page.evaluate(
        """() => {
            const rating = document.getElementById('feedback-ux-rating');
            rating.insertAdjacentHTML('beforeend', '<option value="11">11</option>');
            rating.value = '11';
        }"""
    )
    clean_page.locator("#feedback-submit").click()

    expect(clean_page.locator("#feedback-status")).to_have_text(
        "UX feel must be 1-10."
    )
    expect(clean_page.locator("#feedback-ux-rating")).to_be_focused()
    clean_page.locator("#feedback-ux-rating").select_option("9")
    clean_page.locator("#feedback-message").fill("x" * 1000)
    clean_page.locator("#feedback-submit").click()
    expect(clean_page.locator("#feedback-status")).to_have_text(
        "Feedback must be 1000 characters or fewer after rating details."
    )
    expect(clean_page.locator("#feedback-message")).to_be_focused()


def test_feedback_dialog_has_accessible_escape_close(
    clean_page: Page, base_url: str
) -> None:
    """Feedback is a modal dialog and should follow the standard Escape contract."""
    _enter_app_shell_as_guest(clean_page, base_url)

    clean_page.locator("#nav-feedback").click()

    expect(clean_page.locator("#feedback-overlay")).to_have_attribute("role", "dialog")
    expect(clean_page.locator("#feedback-overlay")).to_have_attribute("aria-modal", "true")
    expect(clean_page.locator("#feedback-overlay")).to_have_attribute("aria-labelledby", "feedback-title")
    expect(clean_page.locator("#feedback-overlay")).to_have_attribute("aria-describedby", "feedback-desc")
    expect(clean_page.locator("#feedback-title")).to_have_text("Feedback")
    expect(clean_page.locator("#feedback-status")).to_have_attribute("role", "status")
    expect(clean_page.locator("#feedback-status")).to_have_attribute("aria-live", "polite")

    clean_page.keyboard.press("Escape")

    expect(clean_page.locator("#feedback-overlay")).not_to_be_visible()


def test_feedback_dialog_returns_focus_to_opener(
    clean_page: Page, base_url: str
) -> None:
    """Closing feedback should return keyboard focus to the row that opened it."""
    _enter_app_shell_as_guest(clean_page, base_url)

    clean_page.locator("#nav-feedback").click()
    expect(clean_page.locator("#feedback-message")).to_be_focused()

    clean_page.keyboard.press("Escape")

    expect(clean_page.locator("#feedback-overlay")).not_to_be_visible()
    expect(clean_page.locator("#nav-feedback")).to_be_focused()


def test_mobile_drawer_keeps_feedback_accessible(
    page: Page, base_url: str
) -> None:
    """Mobile bottom nav replaces primary rows, but feedback still needs drawer access."""
    page.set_viewport_size({"width": 390, "height": 844})
    _enter_app_shell_as_guest(page, base_url)

    drawer = page.locator("#drawer")
    toggle = page.locator("#drawer-toggle")
    expect(drawer).not_to_be_visible()
    assert drawer.get_attribute("data-open") == "false"
    expect(drawer).to_have_attribute("aria-hidden", "true")
    expect(toggle).to_have_attribute("aria-expanded", "false")

    toggle.click()
    expect(drawer).to_be_visible()
    assert drawer.get_attribute("data-open") == "true"
    expect(drawer).to_have_attribute("aria-hidden", "false")
    expect(toggle).to_have_attribute("aria-expanded", "true")
    page.wait_for_function(
        """() => {
            const drawer = document.querySelector("#drawer");
            if (!drawer) return false;
            const rect = drawer.getBoundingClientRect();
            return rect.left >= 0 && rect.right <= window.innerWidth;
        }"""
    )
    drawer_box = drawer.bounding_box()
    assert drawer_box is not None
    assert drawer_box["x"] >= 0
    assert drawer_box["x"] + drawer_box["width"] <= 390
    expect(page.locator("#nav-loop")).to_have_count(0)
    expect(page.locator("#nav-feedback")).to_be_visible()

    page.locator("#nav-feedback").click()

    expect(page.locator("#feedback-overlay")).to_be_visible()
    assert page.locator("#drawer").get_attribute("data-open") == "true"


def test_mobile_concept_attempt_has_writing_width(
    page: Page, base_url: str
) -> None:
    """Mobile concept page keeps the cold-attempt writing surface usable."""
    page.set_viewport_size({"width": 390, "height": 844})
    _enter_app_shell_as_guest(page, base_url)
    page.evaluate("localStorage.clear(); sessionStorage.clear();")
    _seed_route_margin_concept(page)

    page.evaluate("window.App.showLibrary()")
    page.locator(".library-card-vault", has_text="How sodium channels").click()
    expect(page.locator("#concept-header-title")).to_contain_text(
        "How sodium channels create an action potential"
    )
    expect(page.locator(".concept-page-b2__attempt-input")).to_be_visible()
    expect(page.locator("#drawer-toggle")).to_be_visible()
    expect(page.locator("#bottom-nav")).to_be_visible()
    disabled_save_style = page.locator(".concept-page-b2__attempt-save").evaluate(
        """(el) => {
            const style = window.getComputedStyle(el);
            return {
                backgroundColor: style.backgroundColor,
                borderStyle: style.borderStyle,
            };
        }"""
    )
    assert disabled_save_style["backgroundColor"] != "rgba(0, 0, 0, 0)"
    assert disabled_save_style["borderStyle"] == "solid"
    page.locator(".concept-page-b2__attempt-input").fill(
        "Sodium channels probably open when voltage reaches a trigger."
    )
    save_button = page.locator(".concept-page-b2__attempt-save")
    cue_button = page.locator(".concept-page-b2__blank-start-button")
    page.keyboard.press("Tab")
    expect(cue_button).to_be_focused()
    page.keyboard.press("Tab")
    expect(save_button).to_be_focused()
    focus_style = save_button.evaluate(
        """(el) => {
            const style = window.getComputedStyle(el);
            return {
                outlineStyle: style.outlineStyle,
                outlineWidth: style.outlineWidth,
            };
        }"""
    )
    assert focus_style == {"outlineStyle": "solid", "outlineWidth": "3px"}
    expect(page.locator("#concept-view-switch")).to_be_hidden()

    toggle_box = page.locator("#drawer-toggle").bounding_box()
    assert toggle_box is not None
    assert toggle_box["width"] >= 44
    assert toggle_box["height"] >= 44
    title_box = page.locator("#concept-header-title").bounding_box()
    assert title_box is not None
    assert title_box["y"] > toggle_box["y"] + toggle_box["height"]
    expect(page.locator(".concept-page-b2__context-dock")).to_have_count(0)
    expect(page.locator(".concept-page-b2__route")).to_have_count(0)

    attempt_box = page.locator(".concept-page-b2__attempt-input").bounding_box()
    assert attempt_box is not None
    assert attempt_box["width"] >= 300
    assert attempt_box["height"] >= 140
    save_box = page.locator(".concept-page-b2__attempt-save").bounding_box()
    composer_box = page.locator(".concept-page-b2__attempt-composer").bounding_box()
    cue_box = page.locator(".concept-page-b2__blank-start-button").bounding_box()
    truth_note_box = page.locator(".concept-page-b2__truth-note").bounding_box()
    assert save_box is not None
    assert composer_box is not None
    assert cue_box is not None
    assert truth_note_box is not None
    assert save_box["width"] >= 132
    assert save_box["height"] >= 48
    assert save_box["x"] + save_box["width"] <= (
        composer_box["x"] + composer_box["width"]
    )
    assert save_box["y"] + save_box["height"] <= (
        composer_box["y"] + composer_box["height"]
    )
    assert cue_box["x"] >= composer_box["x"]
    assert cue_box["x"] + cue_box["width"] <= (
        composer_box["x"] + composer_box["width"]
    )
    assert cue_box["y"] + cue_box["height"] <= (
        composer_box["y"] + composer_box["height"]
    )
    assert cue_box["y"] + cue_box["height"] <= save_box["y"]
    assert truth_note_box["y"] >= composer_box["y"] + composer_box["height"]
    assert composer_box["height"] <= 300


def test_mobile_concept_nav_exits_and_history_stay_aligned(
    page: Page, base_url: str
) -> None:
    """Concept routes keep primary exits visible and browser history truthful."""
    page_errors: list[str] = []
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    page.set_viewport_size({"width": 390, "height": 844})
    _enter_app_shell_as_guest(page, base_url)
    page.evaluate("localStorage.clear(); sessionStorage.clear();")
    _seed_route_margin_concept(page)
    page.reload()
    _wait_for_app_settled(page)

    page.locator("#bn-library").click()
    page.locator(".library-card-vault", has_text="How sodium channels").click()
    expect(page.locator("#map-view")).to_be_visible()
    expect(page.locator("#bottom-nav")).to_be_visible()
    expect(page.locator("#bottom-nav .bottom-nav-item.active")).to_have_count(0)

    page.locator(".concept-page-b2__truth-note").scroll_into_view_if_needed()
    truth_note_box = page.locator(".concept-page-b2__truth-note").bounding_box()
    bottom_nav_box = page.locator("#bottom-nav").bounding_box()
    assert truth_note_box is not None
    assert bottom_nav_box is not None
    assert truth_note_box["y"] + truth_note_box["height"] <= bottom_nav_box["y"]

    page.evaluate(
        """() => App.startDrill({
            id: 'core-thesis',
            type: 'core',
            label: 'Core thesis',
            detail: 'Explain the current model.',
        })"""
    )
    expect(page.locator("body")).to_have_class(re.compile(r"\bis-drilling\b"))
    page.locator("#bn-library").click()
    expect(page.locator("body")).not_to_have_class(re.compile(r"\bis-drilling\b"))
    expect(page.locator("#library-view")).to_be_visible()
    expect(page.locator("#map-view")).not_to_be_visible()
    assert urlparse(page.url).path == "/"
    page.wait_for_timeout(100)
    expect(page.locator("#library-view")).to_be_visible()
    expect(page.locator("#map-view")).not_to_be_visible()

    page.locator(".library-card-vault", has_text="How sodium channels").click()
    expect(page.locator("#map-view")).to_be_visible()
    page.locator("#bn-dashboard").click()
    expect(page.locator(".hero-card")).to_be_visible()
    expect(page.locator("#map-view")).not_to_be_visible()
    assert urlparse(page.url).path == "/"

    page.locator("#tile-0").click()
    expect(page.locator("#map-view")).to_be_visible()
    assert urlparse(page.url).path == "/session/route-margin-concept"
    page.evaluate(
        """() => App.startDrill({
            id: 'core-thesis',
            type: 'core',
            label: 'Core thesis',
            detail: 'Explain the current model.',
        })"""
    )
    expect(page.locator("body")).to_have_class(re.compile(r"\bis-drilling\b"))
    history_length = page.evaluate("history.length")

    page.go_back()
    expect(page.locator("body")).not_to_have_class(re.compile(r"\bis-drilling\b"))
    expect(page.locator(".hero-card")).to_be_visible()
    expect(page.locator("#map-view")).not_to_be_visible()
    expect(page.locator("#bn-dashboard")).to_have_class(re.compile(r"\bactive\b"))
    assert urlparse(page.url).path == "/"
    assert page.evaluate("history.length") == history_length
    page.wait_for_timeout(100)
    expect(page.locator(".hero-card")).to_be_visible()
    expect(page.locator("#map-view")).not_to_be_visible()

    page.go_forward()
    expect(page.locator("#map-view")).to_be_visible()
    expect(page.locator("#concept-header-title")).to_contain_text(
        "How sodium channels create an action potential"
    )
    expect(page.locator("#bottom-nav .bottom-nav-item.active")).to_have_count(0)
    assert urlparse(page.url).path == "/session/route-margin-concept"
    assert page.evaluate("history.length") == history_length

    page.go_back()
    page.evaluate("localStorage.removeItem('learnops_concepts')")
    page.go_forward()
    expect(page.locator("#ignition-view")).to_be_visible()
    expect(page.locator("#hero-door-error")).to_have_text(
        "That session is not saved in this browser."
    )
    assert urlparse(page.url).path == "/"
    assert page.evaluate("history.length") == history_length

    history_length_before_missing_boot = page.evaluate("history.length")
    page.goto(urljoin(base_url + "/", "session/missing-concept"))
    _wait_for_app_settled(page)
    expect(page.locator("#ignition-view")).to_be_visible()
    expect(page.locator("#hero-door-error")).to_have_text(
        "That session is not saved in this browser."
    )
    assert urlparse(page.url).path == "/"
    assert page.evaluate("history.length") == history_length_before_missing_boot + 1

    history_length_before_malformed_boot = page.evaluate("history.length")
    page.evaluate(
        """() => {
          history.pushState({}, '', '/session/%E0%A4%A');
          window.dispatchEvent(new PopStateEvent('popstate'));
        }"""
    )
    expect(page.locator("#ignition-view")).to_be_visible()
    expect(page.locator("#hero-door-error")).to_have_text(
        "That session is not saved in this browser."
    )
    assert urlparse(page.url).path == "/"
    assert page.evaluate("history.length") == history_length_before_malformed_boot + 1
    assert page_errors == []


def test_saved_library_concept_reopens_map_view(
    clean_page: Page, base_url: str
) -> None:
    """Library entry points should open the concept map, not a stale shell."""
    _seed_one_concept(clean_page)
    _enter_app_shell_as_guest(clean_page, base_url)

    clean_page.locator("#nav-library").click()
    clean_page.locator(".library-card-vault", has_text="Test Concept").click()
    expect(clean_page.locator("#concept-header-title")).to_contain_text("Test Concept")
    assert clean_page.locator("body").get_attribute("data-map-open") == "true"
    expect(clean_page.locator("#nav-dashboard")).not_to_have_class(re.compile(r"\bactive\b"))
    expect(clean_page.locator(".concept-item.active")).to_have_count(1)

    clean_page.locator("#nav-library").click()
    your_library = clean_page.locator("#library-content .library-section", has_text="Concepts")
    your_library.locator(".library-card-vault", has_text="Test Concept").click()

    expect(clean_page.locator("#concept-header-title")).to_contain_text("Test Concept")
    assert clean_page.locator("body").get_attribute("data-map-open") == "true"
    expect(clean_page.locator("#nav-dashboard")).not_to_have_class(re.compile(r"\bactive\b"))
    expect(clean_page.locator(".concept-item.active")).to_have_count(1)

    clean_page.locator("#nav-dashboard").click()
    expect(clean_page.locator("#nav-dashboard")).to_have_class(re.compile(r"\bactive\b"))
    expect(clean_page.locator(".concept-item.active")).to_have_count(0)


def test_session_url_opens_saved_learning_surface(
    clean_page: Page, base_url: str
) -> None:
    """A saved learning object has a resumable /session/:id URL."""
    _enter_app_shell_as_guest(clean_page, base_url)
    clean_page.evaluate("localStorage.clear(); sessionStorage.clear();")
    _seed_route_margin_concept(clean_page)

    clean_page.goto(f"{base_url}/session/route-margin-concept")

    expect(clean_page.locator("#map-view")).to_have_class(re.compile(r"visible"))
    expect(clean_page.locator("#concept-header-title")).to_contain_text(
        "How sodium channels create an action potential"
    )
    expect(clean_page.locator(".concept-page-b2__attempt-input")).to_be_visible()


def test_concept_view_opens_to_route_margin_canvas(
    clean_page: Page, base_url: str
) -> None:
    """A cold source-less concept opens on one writing surface."""
    _seed_route_margin_concept(clean_page)
    _enter_app_shell_as_guest(clean_page, base_url)

    clean_page.locator(".concept-item", has_text="How sodium channels").click()
    expect(clean_page.locator("#concept-header-title")).to_contain_text(
        "How sodium channels create an action potential"
    )

    canvas = clean_page.locator(".concept-page-b2__gestalt")
    expect(canvas).to_be_visible()
    expect(clean_page.locator("#concept-view-switch")).to_be_hidden()
    expect(clean_page.locator("#concept-constellation-content")).to_be_hidden()
    expect(canvas.locator(".concept-page-b2__context-dock")).to_have_count(0)
    expect(canvas).not_to_contain_text("I think sodium just rushes in.")
    expect(canvas.locator(".concept-page-b2__route-item")).to_have_count(0)
    expect(canvas.locator(".concept-page-b2__route-marker-item")).to_have_count(0)
    expect(canvas).not_to_contain_text("Sodium channels open at threshold")
    expect(canvas).not_to_contain_text("This generated summary must not")
    expect(canvas).not_to_contain_text("bloom")

    expect(canvas.locator(".concept-page-b2__attempt-input")).to_be_visible()
    expect(canvas.locator(".concept-page-b2__attempt-input")).to_have_attribute(
        "placeholder",
        "My current guess is that the sodium channel opens when...",
    )
    expect(canvas.locator(".concept-page-b2__attempt")).to_contain_text(
        "What do you think makes the sodium channel open?"
    )
    expect(canvas.locator(".concept-page-b2__attempt")).not_to_contain_text(
        "Write one sentence. Name the trigger, even if you are guessing."
    )
    expect(canvas.locator(".concept-page-b2__attempt-save")).to_have_text("Save draft")
    expect(canvas.locator(".concept-page-b2__attempt-save")).to_be_disabled()
    expect(canvas.locator(".concept-page-b2__attempt-save")).to_have_attribute(
        "aria-disabled", "true"
    )
    expect(canvas.locator(".concept-page-b2__truth-note")).to_contain_text(
        "Study stays hidden until you save a draft. This is not a grade."
    )
    blank_start = canvas.locator("[data-blank-start]")
    expect(blank_start).to_have_text("Need a cue?")
    expect(blank_start).to_have_attribute("aria-expanded", "false")
    expect(canvas.locator("[data-blank-start-hint]")).to_be_hidden()
    attempt_input = canvas.locator(".concept-page-b2__attempt-input")
    attempt_input.fill("asdasdas")
    expect(canvas.locator(".concept-page-b2__attempt-save")).to_be_enabled()
    expect(canvas.locator(".concept-page-b2__attempt-save")).to_have_attribute(
        "aria-disabled", "false"
    )
    clean_page.keyboard.press("Tab")
    expect(blank_start).to_be_focused()
    clean_page.keyboard.press("Tab")
    expect(canvas.locator(".concept-page-b2__attempt-save")).to_be_focused()
    blank_start.click()
    expect(blank_start).to_be_hidden()
    expect(canvas.locator("[data-blank-start-hint]")).to_be_visible()
    expect(canvas.locator("[data-blank-start-hint]")).to_contain_text(
        "Think about the point where a small signal becomes enough to matter."
    )
    assert clean_page.evaluate(
        "() => document.activeElement === document.querySelector('.concept-page-b2__attempt-input')"
    )
    expect(attempt_input).to_have_value("asdasdas")
    attempt_input.fill("")
    fallback_html = clean_page.evaluate(
        """async () => {
            const mod = await import('/js/concept-page-view.js?v=22');
            const entries = mod.deriveConceptEntries({
                clusters: [{
                    id: 'c1',
                    subnodes: [{
                        id: 'c1_s1',
                        label: 'Fallback route',
                        learner_scaffold: {
                            bloom_level: 'understand',
                            learner_move: 'Say it',
                            task_label: 'Fallback route',
                            task_cue: 'Name the relationship.',
                            tailoring_anchor: '',
                            entry_prompt: 'What relationship do you think matters here?',
                            expected_shape: 'Write one relationship you suspect.',
                            sentence_starter: '',
                            blank_hint: '',
                            evidence_goal: 'Learner names a suspected relationship.',
                        },
                    }],
                }],
            });
            return mod.renderActiveEntryHtml(
                entries[0],
                0,
                entries,
                {},
                { metadata: {} },
                { source_mode: 'source_less', node_records: {} }
            );
        }"""
    )
    assert "Write one relationship you suspect." not in fallback_html
    assert "Type one relationship you suspect, even if it feels incomplete." in fallback_html
    empty_fallback_html = clean_page.evaluate(
        """async () => {
            const mod = await import('/js/concept-page-view.js?v=22');
            const entries = mod.deriveConceptEntries({
                clusters: [{
                    id: 'c1',
                    subnodes: [{
                        id: 'c1_s1',
                        label: 'Empty scaffold',
                        learner_scaffold: {
                            bloom_level: 'understand',
                            learner_move: 'Say it',
                            task_label: 'Empty scaffold',
                            task_cue: 'Name the relationship.',
                            tailoring_anchor: '',
                            entry_prompt: 'What relationship do you think matters here?',
                            expected_shape: '',
                            sentence_starter: '',
                            blank_hint: '',
                            evidence_goal: 'Learner names a suspected relationship.',
                        },
                    }],
                }],
            });
            return mod.renderActiveEntryHtml(
                entries[0],
                0,
                entries,
                {},
                { metadata: {} },
                { source_mode: 'source_less', node_records: {} }
            );
        }"""
    )
    assert "Write what you can explain right now." in empty_fallback_html
    canvas.locator(".concept-page-b2__attempt-input").fill(
        "Sodium channels probably open when voltage reaches a trigger."
    )
    expect(clean_page.locator("#concept-view-switch")).to_be_hidden()
    expect(clean_page.locator("#map-content")).to_be_visible()
    expect(clean_page.locator("#concept-constellation-content")).to_be_hidden()
    expect(clean_page.locator(".concept-page-b2__entry-title")).to_contain_text(
        "Sodium gate"
    )
    expect(clean_page.locator(".concept-page-b2__entry-title")).not_to_contain_text(
        "Signal spread"
    )
    expect(clean_page.locator(".concept-page-b2__study-note")).to_have_count(0)
    expect(clean_page.locator("body")).not_to_have_class(re.compile(r"\bis-drilling\b"))
    expect(clean_page.locator(".concept-page-b2__attempt-input")).to_have_value(
        "Sodium channels probably open when voltage reaches a trigger."
    )
    expect(canvas.locator(".concept-page-b2__attempt-save")).to_be_enabled()
    clean_page.locator(".concept-page-b2__attempt-input").fill("")
    expect(canvas.locator(".concept-page-b2__attempt-save")).to_be_disabled()
    expect(canvas.locator(".concept-page-b2__attempt-save")).to_have_attribute(
        "aria-disabled", "true"
    )


def test_source_concept_review_can_continue_to_next_entry(
    clean_page: Page, base_url: str
) -> None:
    """A source-backed concept must not dead-end after a strong first reveal."""
    clean_page.evaluate(
        """(() => {
            const now = new Date().toISOString();
            const graphData = JSON.stringify({
                metadata: {
                    core_thesis: 'A thermostat compares a room reading to a target before calling for heat.',
                    source_title: 'Thermostat source',
                },
                clusters: [
                    {
                        id: 'c1',
                        label: 'Thermostat comparison',
                        description: 'First source-backed entry.',
                        subnodes: [{
                            id: 'c1_s1',
                            label: 'Thermostat comparison',
                            mechanism: 'The thermostat compares measured room temperature with the set point.',
                        }],
                    },
                    {
                        id: 'c2',
                        label: 'Heat call',
                        description: 'Second source-backed entry.',
                        subnodes: [{
                            id: 'c2_s1',
                            label: 'Heat call',
                            mechanism: 'Below-target readings cause a heat call.',
                        }],
                    },
                ],
                relationships: { domain_mechanics: [], learning_prerequisites: [] },
                frameworks: [],
            });
            localStorage.setItem('learnops_concepts', JSON.stringify([{
                id: 'source-review-continue',
                name: 'Source Review Continue QA',
                createdAt: new Date().toISOString(),
                state: 'growing',
                contentPreview: 'Source summary.',
                contentType: 'text',
                contentFilename: 'thermostat.txt',
                graphData,
            }]));
            localStorage.setItem('socratink:training:v1:source-review-continue', JSON.stringify({
                concept_id: 'source-review-continue',
                schema_version: 1,
                source_mode: 'source_attached',
                grounding: 'source',
                source_ref: { type: 'text', filename: 'thermostat.txt' },
                node_records: {
                    c1_s1: {
                        attempts: [{
                            id: 'attempt-1',
                            kind: 'cold',
                            at: now,
                            user_text: 'It compares room temperature with the target.',
                            classification: 'strong',
                            gaps: [],
                            grader_version: 'qa',
                        }],
                        study_revealed_at: now,
                        repairs: [],
                    },
                },
            }));
        })()"""
    )
    _enter_app_shell_as_guest(clean_page, base_url)

    clean_page.locator(".concept-item", has_text="Source Review Continue QA").click()
    expect(clean_page.locator(".concept-page-b2__entry-eyebrow")).to_have_text(
        "Review later"
    )
    expect(clean_page.locator(".concept-page-b2__entry-cta")).to_have_text(
        "Continue route"
    )
    continue_cta_style = clean_page.locator(".concept-page-b2__entry-cta").evaluate(
        """(el) => {
            const style = window.getComputedStyle(el);
            return {
                backgroundColor: style.backgroundColor,
                borderStyle: style.borderStyle,
                minHeight: style.minHeight,
            };
        }"""
    )
    assert continue_cta_style["backgroundColor"] != "rgba(0, 0, 0, 0)"
    assert continue_cta_style["borderStyle"] == "solid"
    assert continue_cta_style["minHeight"] == "44px"
    clean_page.locator(".concept-page-b2__entry-cta").click()
    assert clean_page.evaluate(
        "localStorage.getItem('socratink:comparison_ack:v1:source-review-continue:c1_s1')"
    ) == "1"
    expect(clean_page.locator(".concept-page-b2__entry-title")).to_have_text(
        "Heat call"
    )
    attempt_input = clean_page.locator(".concept-page-b2__attempt-input")
    expect(attempt_input).to_be_visible()
    expect(attempt_input).to_be_focused()
    prompt_box = clean_page.locator(".concept-page-b2__attempt h3").bounding_box()
    drawer_box = clean_page.locator("#drawer-toggle").bounding_box()
    attempt_box = attempt_input.bounding_box()
    viewport = clean_page.viewport_size
    assert prompt_box is not None
    assert drawer_box is not None
    assert attempt_box is not None
    assert viewport is not None
    assert clean_page.evaluate("window.scrollY") == 0
    assert prompt_box["y"] > drawer_box["y"] + drawer_box["height"]
    assert 0 <= attempt_box["y"] < viewport["height"]


def test_source_less_launch_pad_sketch_preserves_gestalt_hybrid_loop(
    clean_page: Page, base_url: str
) -> None:
    """A realistic customer sketch enters through Ignition before the hybrid loop."""

    sketch_text = (
        "I manage facilities for a small clinic. I think thermostats turn heat on when "
        "the room feels cold, but I am fuzzy on what they compare."
    )

    def fulfill_extract(route) -> None:
        payload = route.request.post_data_json
        assert payload["name"] == "Thermostat feedback loop"
        assert payload["starting_sketch"] == sketch_text
        assert payload["source"] is None
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "provisional_map": {
                        "metadata": {
                            "source_title": "Thermostat feedback loop",
                            "core_thesis": "A thermostat compares a room reading to a target before calling for heat.",
                            "architecture_type": "causal_chain",
                            "difficulty": "easy",
                            "governing_assumptions": [
                                "Learner works from a clinic facilities example."
                            ],
                            "low_density": True,
                            "learner_goal": "explain thermostat feedback loops to a new technician",
                        },
                        "backbone": [
                            {
                                "id": "b1",
                                "principle": "Thermostat feedback starts with a comparison.",
                                "dependent_clusters": ["c1", "c2", "c3"],
                            }
                        ],
                        "clusters": [
                            {
                                "id": "c1",
                                "label": "Thermostat compares room temperature with set point",
                                "description": "Generated description should not leak before the draft.",
                                "subnodes": [
                                    {
                                        "id": "c1_s1",
                                        "label": "Thermostat compares room temperature with set point",
                                        "mechanism": "The thermostat compares measured room temperature with the set point before calling for heat.",
                                        "study_note": "The thermostat compares the measured room temperature with the set point. Heat starts only when the measured value is below that target.",
                                        "learner_scaffold": {
                                            "bloom_level": "understand",
                                            "learner_move": "Say it",
                                            "task_label": "Compare target",
                                            "task_cue": "Name what gets compared.",
                                            "tailoring_anchor": "You mentioned a clinic room feeling cold, so this starts with what the thermostat checks before heat starts.",
                                            "entry_prompt": "What do you think the thermostat checks before it calls for heat?",
                                            "expected_shape": "Write one sentence. Name the signal and the target if you can.",
                                            "sentence_starter": "I think it checks...",
                                            "blank_hint": "Use room temperature, target, or heat if one of those feels useful.",
                                            "evidence_goal": "Learner names a comparison before a heat call.",
                                        },
                                    }
                                ],
                            },
                            {
                                "id": "c2",
                                "label": "Below-target reading calls for heat",
                                "description": "Generated future description should not leak before expansion.",
                                "subnodes": [
                                    {
                                        "id": "c2_s1",
                                        "label": "Below-target reading calls for heat",
                                        "mechanism": "When measured temperature is below the set point, the thermostat calls for heat.",
                                        "study_note": "Hidden future study note.",
                                        "learner_scaffold": {
                                            "bloom_level": "understand",
                                            "learner_move": "Explain how",
                                            "task_label": "Call for heat",
                                            "task_cue": "Connect comparison to action.",
                                            "tailoring_anchor": "Your sketch mentioned heat turning on, so this later step connects the check to the heat call.",
                                            "entry_prompt": "How do you think the comparison turns into a heat call?",
                                            "expected_shape": "Write one cause-then-action sentence.",
                                            "sentence_starter": "When the room reading is...",
                                            "blank_hint": "Separate what is checked from what turns on.",
                                            "evidence_goal": "Learner connects comparison to heater action.",
                                        },
                                    }
                                ],
                            },
                            {
                                "id": "c3",
                                "label": "Reached set point stops heat",
                                "description": "Generated locked description should remain inert.",
                                "subnodes": [
                                    {
                                        "id": "c3_s1",
                                        "label": "Reached set point stops heat",
                                        "mechanism": "When measured temperature reaches the set point, the heat call stops.",
                                        "study_note": "Hidden locked study note.",
                                        "learner_scaffold": {
                                            "bloom_level": "apply",
                                            "learner_move": "Test the edge",
                                            "task_label": "Stop rule",
                                            "task_cue": "Predict when the call stops.",
                                            "tailoring_anchor": "Your sketch focused on heat starting, so this later step tests when the loop stops.",
                                            "entry_prompt": "What would make the thermostat stop calling for heat?",
                                            "expected_shape": "Write one stopping condition.",
                                            "sentence_starter": "It would stop when...",
                                            "blank_hint": "Ask what has to be true for heat to no longer be needed.",
                                            "evidence_goal": "Learner predicts the stopping condition.",
                                        },
                                    }
                                ],
                            },
                        ],
                        "relationships": {
                            "domain_mechanics": [
                                {
                                    "from": "c1",
                                    "to": "c2",
                                    "type": "causal",
                                    "mechanism": "The comparison determines whether heat is called.",
                                },
                                {
                                    "from": "c2",
                                    "to": "c3",
                                    "type": "causal",
                                    "mechanism": "Heating changes the room until the call can stop.",
                                },
                            ],
                            "learning_prerequisites": [
                                {
                                    "from": "c1",
                                    "to": "c2",
                                    "rationale": "The action depends on the comparison.",
                                },
                                {
                                    "from": "c2",
                                    "to": "c3",
                                    "rationale": "Stopping follows from understanding the call.",
                                },
                            ],
                        },
                        "frameworks": [],
                    }
                }
            ),
        )

    def fulfill_drill(route) -> None:
        payload = route.request.post_data_json
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "agent_response": "Draft saved. Compare it with the notes before repairing the missing link.",
                    "generative_commitment": True,
                    "classification": "partial",
                    "gap_description": "The sketch names current but misses comparison to a target set point.",
                    "gaps": [
                        {
                            "mechanism": "comparison target",
                            "correction": "Name that the thermostat compares room temperature with the set point.",
                        }
                    ],
                    "routing": "NEXT",
                    "node_id": payload["node_id"],
                    "answer_mode": "attempt",
                    "score_eligible": True,
                    "response_tier": "partial",
                    "response_band": "link",
                    "tier_reason": "The learner names the action but not the comparison rule.",
                    "probe_count": 0,
                    "nodes_drilled": 1,
                    "attempt_turn_count": 1,
                    "help_turn_count": 0,
                    "graph_mutated": False,
                    "ux_reward_emitted": False,
                    "session_terminated": False,
                    "termination_reason": None,
                    "prompt_version": "qa-gestalt-hybrid",
                }
            ),
        )

    def reopen_created_concept() -> None:
        clean_page.locator("#nav-library").click()
        clean_page.locator(
            ".library-card-vault",
            has_text="Thermostat feedback loop",
        ).click()

    clean_page.route("**/api/extract", fulfill_extract)
    clean_page.route("**/api/drill", fulfill_drill)
    _enter_app_shell_as_guest(clean_page, base_url)
    clean_page.evaluate("localStorage.clear(); sessionStorage.clear();")

    clean_page.locator("#nav-ignition").click()
    clean_page.locator("#hero-single-input-field").fill("Thermostat feedback loop")
    clean_page.locator("#hero-cold-guess-field").fill(sketch_text)
    expect(clean_page.locator("#hero-door-submit")).to_be_enabled()
    clean_page.locator("#hero-door-submit").click()
    expect(clean_page.locator("#launch-pad-view")).to_be_hidden()

    canvas = clean_page.locator(".concept-page-b2__gestalt")
    expect(canvas).to_be_visible(timeout=8_000)
    expect(clean_page.locator("#drill-chamber-view")).to_be_visible(timeout=10_000)
    seda_state = clean_page.wait_for_function(
        """() => {
          const key = Object.keys(localStorage).find((k) => k.startsWith('socratink:seda-session:v1:'));
          if (!key) return null;
          const value = JSON.parse(localStorage.getItem(key));
          return value?.sessionId && value?.latest?.awaiting?.key === 'cold_attempt'
            ? value
            : null;
        }""",
        timeout=45_000,
    ).json_value()
    assert seda_state["latest"]["awaiting"]["key"] == "cold_attempt"
    bound_surface = clean_page.evaluate(
        """(nodeId) => {
          const conceptId = localStorage.getItem('learnops_active');
          const concept = JSON.parse(localStorage.getItem('learnops_concepts') || '[]')
            .find((item) => item.id === conceptId);
          const graph = JSON.parse(concept?.graphData || 'null');
          const nodes = [
            ...(graph?.backbone || []),
            ...(graph?.clusters || []).flatMap((cluster) => cluster?.subnodes || []),
          ];
          const node = nodes.find((item) => item?.id === nodeId);
          return {
            prompt: node?.learner_scaffold?.entry_prompt || '',
            taskLabel: node?.learner_scaffold?.task_label || node?.label || '',
            mechanism: node?.study_note || node?.mechanism || '',
          };
        }""",
        seda_state["nodeId"],
    )
    assert bound_surface["prompt"]
    expect(clean_page.locator("#chamber-question")).to_have_text(
        bound_surface["prompt"], timeout=20_000
    )
    clean_page.locator("#chamber-exit").click()
    expect(clean_page.locator("#drill-chamber-view")).to_be_hidden()
    expect(canvas).to_be_visible(timeout=8_000)
    expect(canvas.locator(".concept-page-b2__attempt")).to_contain_text(
        bound_surface["prompt"]
    )
    expect(canvas).not_to_contain_text("Shaped by your sketch")
    expect(canvas).to_contain_text(bound_surface["taskLabel"])
    expect(canvas).not_to_contain_text("Call for heat")
    expect(canvas).not_to_contain_text(bound_surface["mechanism"])
    expect(canvas).not_to_contain_text("Generated description should not leak")
    expect(canvas.locator(".concept-page-b2__route-item")).to_have_count(0)
    expect(canvas.locator(".concept-page-b2__route-marker-item")).to_have_count(0)
    expect(canvas.locator(".concept-page-b2__nearby")).to_have_count(0)

    clean_page.locator(".concept-page-b2__attempt-input").fill(
        "It checks if the room is colder than what we wanted and then starts heat."
    )
    with clean_page.expect_request(
        lambda request: (
            request.method == "POST"
            and "/api/session/" in request.url
            and request.url.endswith("/turn")
        )
    ):
        clean_page.locator(".concept-page-b2__attempt-save").click()
    expect(clean_page.locator("#drill-chamber-view")).to_be_visible(timeout=10_000)
    expect(clean_page.locator(".concept-page-b2__route")).to_have_count(0)


def test_source_less_defensive_ui_paths_remain_inert(
    clean_page: Page, base_url: str
) -> None:
    """Defensive local UI paths do not mutate truth or leave drill state behind."""
    _seed_route_margin_concept(clean_page)
    _enter_app_shell_as_guest(clean_page, base_url)

    clean_page.locator(".concept-item", has_text="How sodium channels").click()
    expect(clean_page.locator(".concept-page-b2__context-dock")).to_have_count(0)

    _seed_route_margin_concept(clean_page)
    clean_page.locator("#nav-library").click()
    clean_page.locator(".concept-item", has_text="How sodium channels").click()
    clean_page.evaluate(
        """() => {
            App.startDrill({
                id: 'core-thesis',
                type: 'core',
                label: 'Core thesis',
                detail: 'Explain the current model.',
            });
        }"""
    )
    expect(clean_page.locator("body")).to_have_class(re.compile(r"\bis-drilling\b"))
    clean_page.evaluate("App.hideMapView()")
    expect(clean_page.locator("body")).not_to_have_class(re.compile(r"\bis-drilling\b"))
    clean_page.evaluate(
        """async () => {
            App.hideMapView();
            App.startDrill({
                id: 'c2_s1',
                type: 'subnode',
                label: 'Opening rule',
                detail: 'Explain the opening rule.',
            });
            App.cancelDrill({ restoreMap: false });
            await Promise.resolve();
        }"""
    )

    fallback_mode = clean_page.evaluate(
        """async () => {
            const view = await import('/js/concept-page-view.js?v=22');
            return view.deriveSourceLessViewMode({
                attempted: true,
                next_action: 'spaced_attempt',
                state: 'primed',
                record: { attempts: [{ id: 'a1', at: '2026-05-21T10:00:00.000Z' }] },
            });
        }"""
    )
    assert fallback_mode == "expanded-workspace"

    clean_page.evaluate(
        """async () => {
            const ack = await import('/js/comparison-acknowledgement.js');
            ack.markComparisonAcknowledged('route-margin-concept', 'c1_s1');
            ack.clearComparisonAcknowledgement('route-margin-concept', 'c1_s1');
        }"""
    )
    acknowledged = clean_page.evaluate(
        """async () => {
            const ack = await import('/js/comparison-acknowledgement.js');
            return ack.hasComparisonAcknowledgement('route-margin-concept', 'c1_s1');
        }"""
    )
    assert acknowledged is False


def test_concept_open_handles_missing_and_malformed_graph_metadata(
    clean_page: Page, base_url: str
) -> None:
    """Concept open covers fallback metadata and malformed graph guardrails."""
    clean_page.evaluate(
        """localStorage.setItem('learnops_concepts', JSON.stringify([
            {
                id: 'missing-metadata',
                name: 'Missing Metadata Concept',
                createdAt: Date.now(),
                state: 'growing',
                graphData: JSON.stringify({ backbone: [], clusters: [] }),
            },
            {
                id: 'malformed-graph',
                name: 'Malformed Graph Concept',
                createdAt: Date.now(),
                state: 'growing',
                graphData: '{',
            },
        ]))"""
    )
    _enter_app_shell_as_guest(clean_page, base_url)

    clean_page.locator("#nav-library").click()
    clean_page.locator(".library-card-vault", has_text="Missing Metadata Concept").click()
    expect(clean_page.locator("#concept-header-title")).to_contain_text(
        "Missing Metadata Concept"
    )
    assert clean_page.locator("body").get_attribute("data-map-open") == "true"
    expect(clean_page.locator(".concept-page-b2__attempt-input")).to_be_visible()
    clean_page.evaluate("window.App.startDrillFromMap()")
    assert clean_page.locator("body").get_attribute("data-map-open") == "true"
    clean_page.evaluate("window.App.cancelDrill()")

    clean_page.locator("#nav-library").click()

    def accept_malformed(dialog) -> None:
        assert "malformed graph data" in dialog.message
        dialog.accept()

    clean_page.once("dialog", accept_malformed)
    clean_page.locator(".library-card-vault", has_text="Malformed Graph Concept").click()
    expect(clean_page.locator("#concept-header-title")).to_contain_text(
        "Missing Metadata Concept"
    )


def test_active_concept_delete_confirms_then_returns_to_desk(
    clean_page: Page, base_url: str
) -> None:
    """Deleting the open concept must not leave stale concept content visible."""
    _seed_one_concept(clean_page)
    clean_page.evaluate(
        """localStorage.setItem('socratink:training:v1:fixture-concept', JSON.stringify({
            concept_id: 'fixture-concept',
            schema_version: 1,
            node_records: {
                'core-thesis': {
                    attempts: [{
                        id: 'attempt-1',
                        at: '2026-05-15T10:00:00.000Z',
                        user_text: 'Learner evidence that must be deleted with the concept.',
                        classification: 'strong',
                        gaps: [],
                        grader_version: 'qa',
                    }],
                    repairs: [],
                },
            },
        }))"""
    )
    _enter_app_shell_as_guest(clean_page, base_url)

    clean_page.locator("#nav-library").click()
    clean_page.locator(".library-card-vault", has_text="Test Concept").click()
    expect(clean_page.locator("#concept-header-title")).to_contain_text("Test Concept")

    concept_actions = clean_page.locator(".concept-item.active .concept-actions")
    delete_button = clean_page.locator(".concept-item.active .concept-delete")

    def dismiss_delete(dialog) -> None:
        assert "Delete \"Test Concept\"?" in dialog.message
        dialog.dismiss()

    clean_page.once("dialog", dismiss_delete)
    concept_actions.click()
    delete_button.click()
    expect(clean_page.locator("#concept-header-title")).to_contain_text("Test Concept")
    expect(clean_page.locator(".concept-item.active")).to_have_count(1)

    def accept_delete(dialog) -> None:
        assert "Delete \"Test Concept\"?" in dialog.message
        dialog.accept()

    clean_page.once("dialog", accept_delete)
    concept_actions.click()
    delete_button.click()
    expect(clean_page.locator("#title")).to_have_text("What are you trying to understand?")
    expect(clean_page.locator(".concept-item")).to_have_count(0)
    expect(clean_page.locator("#concept-header-title")).not_to_be_visible()
    assert clean_page.locator("body").get_attribute("data-map-open") != "true"
    assert (
        clean_page.evaluate(
            """localStorage.getItem('socratink:training:v1:fixture-concept')"""
        )
        is None
    )


def test_first_use_desk_has_one_start_socket(
    clean_page: Page, base_url: str, captured: dict
) -> None:
    """A blank Desk presents one accessible reconstruction plate."""

    clean_page.set_viewport_size({"width": 390, "height": 844})
    _enter_app_shell_as_guest(clean_page, base_url)
    clean_page.evaluate(
        """(() => {
            localStorage.removeItem('learnops_concepts');
            localStorage.removeItem('learnops_active');
        })()"""
    )
    clean_page.reload()
    _wait_for_app_settled(clean_page)
    clean_page.evaluate("App.showDashboard()")

    expect(clean_page.locator("#desk-title")).to_have_text("Desk")
    expect(clean_page.locator(".desk-helper")).to_have_text(
        "Then write what you remember."
    )
    expect(clean_page.locator(".desk-helper")).to_be_visible()
    expect(clean_page.locator(".desk-index-header")).to_be_hidden()
    expect(clean_page.locator("#grid-container")).to_have_class(re.compile(r"\bis-first-use\b"))
    expect(clean_page.locator("#grid-svg")).to_have_attribute("viewBox", "140 119 140 130")
    expect(clean_page.locator("#tile-4")).to_have_class(re.compile(r"\bis-primary-empty\b"))
    expect(clean_page.locator("#tile-4")).to_have_attribute("role", "button")
    expect(clean_page.locator("#tile-4")).to_have_attribute("tabindex", "0")
    expect(clean_page.locator("#tile-4")).to_have_attribute("aria-label", "Choose a topic")
    expect(clean_page.locator("#tile-4 .empty-tile-affordance__label")).to_have_text("Choose a topic")
    expect(clean_page.locator("#tile-4 .empty-tile-affordance__line")).to_have_count(0)
    expect(clean_page.locator("#bn-ignition .bottom-nav-label")).to_have_text("New")
    expect(clean_page.locator("body")).to_have_attribute("data-primary-view", "desk")
    expect(clean_page.locator("body")).to_have_attribute("data-desk-first-use", "true")
    expect(clean_page.locator("#bn-dashboard")).to_have_attribute("aria-current", "page")
    expect(clean_page.locator("#nav-dashboard")).to_have_attribute("aria-current", "page")
    expect(clean_page.locator("#bn-ignition")).not_to_have_attribute("aria-current", re.compile(r".+"))
    expect(clean_page.locator("#grid-svg .tile-group.is-capacity")).to_have_count(8)
    expect(clean_page.locator("#grid-svg .tile-group[role='button']")).to_have_count(1)
    expect(clean_page.locator("#grid-svg .tile-group[tabindex='0']")).to_have_count(1)
    expect(clean_page.locator("#grid-svg .tile-group.is-capacity[aria-hidden='true']")).to_have_count(8)
    expect(clean_page.locator("#grid-svg .is-capacity .empty-tile-affordance")).to_have_count(0)
    expect(clean_page.locator("#tile-4 .empty-tile-affordance--primary")).to_have_count(1)
    expect(clean_page.locator(".desk-legend")).to_have_count(0)
    expect(clean_page.locator(".desk-eyebrow")).to_have_count(0)

    mobile_layout = clean_page.evaluate(
        """(() => {
            const rect = (selector) => {
                const b = document.querySelector(selector)?.getBoundingClientRect();
                return b ? { left: b.left, right: b.right, top: b.top,
                             bottom: b.bottom, width: b.width, height: b.height } : null;
            };
            return {
                clientWidth: document.documentElement.clientWidth,
                scrollWidth: document.documentElement.scrollWidth,
                scrollHeight: document.documentElement.scrollHeight,
                helper: rect('.desk-helper'),
                helperFontSize: parseFloat(getComputedStyle(document.querySelector('.desk-helper')).fontSize),
                helperWhiteSpace: getComputedStyle(document.querySelector('.desk-helper')).whiteSpace,
                board: rect('#grid-svg'),
                boardOverflow: getComputedStyle(document.querySelector('#grid-svg')).overflow,
                start: rect('#tile-4'),
                nav: rect('#bottom-nav'),
                navLabelFontSizes: Array.from(document.querySelectorAll('.bottom-nav-label'))
                    .map((label) => parseFloat(getComputedStyle(label).fontSize)),
                activeLabelColor: getComputedStyle(document.querySelector('#bn-dashboard .bottom-nav-label')).color,
                primaryReadableColor: (() => {
                    const probe = document.createElement('span');
                    probe.style.color = 'var(--primary-readable)';
                    document.body.appendChild(probe);
                    const color = getComputedStyle(probe).color;
                    probe.remove();
                    return color;
                })(),
                hiddenCapacityCount: Array.from(document.querySelectorAll('.tile-group.is-capacity'))
                    .filter((tile) => getComputedStyle(tile).display === 'none').length,
                drawerToggleDisplay: getComputedStyle(document.querySelector('.drawer-toggle')).display,
            };
        })()"""
    )
    assert mobile_layout["scrollWidth"] == mobile_layout["clientWidth"] == 390
    assert mobile_layout["scrollHeight"] <= 844
    assert mobile_layout["helperFontSize"] >= 14
    assert mobile_layout["helperWhiteSpace"] != "nowrap"
    assert mobile_layout["boardOverflow"] == "visible"
    assert mobile_layout["hiddenCapacityCount"] == 8
    assert 184 <= mobile_layout["board"]["width"] <= 200
    assert mobile_layout["board"]["left"] >= 0
    assert mobile_layout["board"]["right"] <= 390
    assert mobile_layout["board"]["bottom"] <= mobile_layout["nav"]["top"]
    assert mobile_layout["start"]["width"] >= 44
    assert mobile_layout["start"]["height"] >= 44
    assert all(size >= 12 for size in mobile_layout["navLabelFontSizes"])
    assert mobile_layout["activeLabelColor"] == mobile_layout["primaryReadableColor"]
    assert mobile_layout["drawerToggleDisplay"] == "none"

    clean_page.set_viewport_size({"width": 320, "height": 720})
    narrow_layout = clean_page.evaluate(
        """(() => {
            const helper = document.querySelector('.desk-helper').getBoundingClientRect();
            const board = document.querySelector('#grid-svg').getBoundingClientRect();
            const nav = document.querySelector('#bottom-nav').getBoundingClientRect();
            return {
                clientWidth: document.documentElement.clientWidth,
                scrollWidth: document.documentElement.scrollWidth,
                helperLeft: helper.left,
                helperRight: helper.right,
                boardLeft: board.left,
                boardRight: board.right,
                boardBottom: board.bottom,
                boardWidth: board.width,
                navTop: nav.top,
            };
        })()"""
    )
    assert narrow_layout["scrollWidth"] == narrow_layout["clientWidth"] == 320
    assert narrow_layout["helperLeft"] >= 0
    assert narrow_layout["helperRight"] <= 320
    assert narrow_layout["boardLeft"] >= 0
    assert narrow_layout["boardRight"] <= 320
    assert narrow_layout["boardBottom"] <= narrow_layout["navTop"]
    assert 184 <= narrow_layout["boardWidth"] <= 200
    clean_page.set_viewport_size({"width": 390, "height": 844})

    clean_page.emulate_media(forced_colors="active")
    clean_page.locator("#tile-4").focus()
    tile_focus = clean_page.locator("#tile-4").evaluate(
        "el => ({ style: getComputedStyle(el).outlineStyle, "
        "width: parseFloat(getComputedStyle(el).outlineWidth) })"
    )
    clean_page.locator("#bn-dashboard").focus()
    nav_focus = clean_page.locator("#bn-dashboard").evaluate(
        "el => ({ style: getComputedStyle(el).outlineStyle, "
        "width: parseFloat(getComputedStyle(el).outlineWidth) })"
    )
    assert tile_focus["style"] == "solid" and tile_focus["width"] >= 2
    assert nav_focus["style"] == "solid" and nav_focus["width"] >= 2
    clean_page.emulate_media(forced_colors="none")

    # The retained inline handler still fails closed for visual-capacity tiles.
    clean_page.locator("#tile-0").evaluate(
        "el => el.dispatchEvent(new MouseEvent('click', { bubbles: true }))"
    )
    expect(clean_page.locator(".hero-card.intro-page")).to_be_visible()
    expect(clean_page.locator("#ignition-view")).to_be_hidden()

    clean_page.locator("#tile-4").click()
    expect(clean_page.locator("#ignition-view")).to_be_visible()
    expect(clean_page.locator("body")).to_have_attribute("data-primary-view", "ignition")
    expect(clean_page.locator(".drawer-toggle")).to_be_visible()
    clean_page.evaluate("App.showDashboard()")
    expect(clean_page.locator(".desk-index-header")).to_be_hidden()
    assert captured["console_errors"] == []
    assert captured["failed_requests"] == []


def test_first_use_desk_fits_desktop_without_inner_scroll(
    clean_page: Page, base_url: str, captured: dict
) -> None:
    """The one-screen empty Desk must not create a permanent desktop scrollbar."""

    clean_page.set_viewport_size({"width": 1280, "height": 720})
    _enter_app_shell_as_guest(clean_page, base_url)
    clean_page.evaluate(
        """(() => {
            localStorage.removeItem('learnops_concepts');
            localStorage.removeItem('learnops_active');
        })()"""
    )
    clean_page.reload()
    _wait_for_app_settled(clean_page)
    clean_page.evaluate("App.showDashboard()")

    card_size = clean_page.locator("#card").evaluate(
        "el => ({ scrollHeight: el.scrollHeight, clientHeight: el.clientHeight })"
    )
    assert card_size["scrollHeight"] <= card_size["clientHeight"]
    assert captured["console_errors"] == []
    assert captured["failed_requests"] == []


def test_desk_iso_board_state_surface_and_room_labels(
    clean_page: Page, base_url: str, captured: dict
) -> None:
    """Desk board exposes truthful tile state and quiet hover/focus labels."""

    def seed_board_concepts(count: int = 9) -> str:
        return f"""(() => {{
            const graph = (status = null, extra = {{}}) => JSON.stringify({{
                metadata: {{
                    core_thesis: 'Seeded thesis',
                    drill_status: status,
                    drill_phase: status === 'primed' ? 'study' : null,
                    ...extra,
                }},
                backbone: [],
                clusters: [],
            }});
            const iso = (hoursAgo) => new Date(Date.now() - hoursAgo * 60 * 60 * 1000).toISOString();
            const attempt = (classification, hoursAgo, gaps = []) => ({{
                id: `${{classification}}-${{hoursAgo}}`,
                at: iso(hoursAgo),
                user_text: `${{classification}} reconstruction`,
                classification,
                grader_version: 'fixture',
                gaps,
            }});
            const training = (conceptId, attempts) => ({{
                concept_id: conceptId,
                schema_version: 1,
                source_mode: 'source_less',
                grounding: 'learner_sketch',
                source_ref: null,
                sketch: null,
                node_records: {{
                    [`${{conceptId}}-node`]: {{
                        attempts,
                        repairs: [],
                    }},
                }},
            }});
            const concepts = [
                {{
                    id: 'locked-board-tile',
                    name: 'Locked Board Tile',
                    state: 'growing',
                    createdAt: Date.now(),
                    graphData: graph(null),
                }},
                {{
                    id: 'primed-board-tile',
                    name: 'Primed Board Tile',
                    state: 'growing',
                    createdAt: Date.now() + 1,
                    graphData: graph(null),
                }},
                {{
                    id: 'drilled-board-tile',
                    name: 'Drilled Board Tile',
                    state: 'fractured',
                    createdAt: Date.now() + 2,
                    graphData: graph('drilled', {{
                        gap_type: 'causal_link',
                        gap_description: 'A causal link needs another angle.',
                    }}),
                }},
                {{
                    id: 'solidified-board-tile',
                    name: 'Solidified Board Tile',
                    state: 'growing',
                    createdAt: Date.now() + 3,
                    graphData: graph(null),
                }},
                {{
                    id: 'hibernating-board-tile',
                    name: 'Hibernating Board Tile',
                    state: 'hibernating',
                    createdAt: Date.now() + 4,
                    graphData: graph(null),
                }},
                {{
                    id: 'legacy-locked-board-tile',
                    name: 'Legacy Locked Board Tile',
                    state: 'instantiated',
                    createdAt: Date.now() + 5,
                    graphData: graph(null),
                }},
                {{
                    id: 'direct-primed-board-tile',
                    name: 'Direct Primed Board Tile',
                    state: 'primed',
                    createdAt: Date.now() + 6,
                    graphData: graph(null),
                }},
                {{
                    id: 'solid-alias-board-tile',
                    name: 'Solid Alias Board Tile',
                    state: 'growing',
                    createdAt: Date.now() + 7,
                    graphData: graph('solid'),
                }},
                {{
                    id: 'front-board-tile',
                    name: 'Front Board Tile',
                    state: 'actualized',
                    createdAt: Date.now() + 8,
                    graphData: graph('solidified'),
                }},
            ].slice(0, {count});
            localStorage.setItem('learnops_concepts', JSON.stringify(concepts));
            localStorage.setItem('learnops_active', concepts[0]?.id || '');
            localStorage.setItem('socratink:training:v1:primed-board-tile', JSON.stringify(
                training('primed-board-tile', [attempt('strong', 1)])
            ));
            localStorage.setItem('socratink:training:v1:drilled-board-tile', JSON.stringify(
                training('drilled-board-tile', [
                    attempt('thin', 2, [{{ type: 'missing_link', detail: 'first miss' }}]),
                    attempt('thin', 1, [{{ type: 'missing_link', detail: 'second miss' }}]),
                ])
            ));
            localStorage.setItem('socratink:training:v1:solidified-board-tile', JSON.stringify(
                training('solidified-board-tile', [
                    attempt('strong', 20),
                    attempt('strong', 1),
                ])
            ));
            localStorage.setItem('socratink:training:v1:front-board-tile', JSON.stringify(
                training('front-board-tile', [
                    attempt('strong', 20),
                    attempt('strong', 1),
                ])
            ));
        }})()"""

    _enter_app_shell_as_guest(clean_page, base_url)
    clean_page.evaluate(seed_board_concepts(9))
    clean_page.reload()
    _wait_for_app_settled(clean_page)
    clean_page.locator("#nav-dashboard").click()
    expect(clean_page.locator("#grid-svg .tile-group")).to_have_count(9)

    expected_states = {
        "#tile-0": ("growing", "locked"),
        "#tile-1": ("growing", "primed"),
        "#tile-2": ("fractured", "fractured"),
        "#tile-3": ("growing", "solidified"),
        "#tile-4": ("hibernating", "locked"),
        "#tile-6": ("primed", "primed"),
        "#tile-7": ("growing", "solidified"),
        "#tile-8": ("actualized", "solidified"),
    }
    for selector, (source_state, board_state) in expected_states.items():
        tile = clean_page.locator(selector)
        expect(tile).to_have_attribute("data-source-state", source_state)
        expect(tile).to_have_attribute("data-board-state", board_state)

    expected_hints = {
        "#tile-1": "Reconstruction evidence is on record.",
        "#tile-2": "A specific gap is ready to repair.",
        "#tile-3": "Spaced reconstruction is on record.",
        "#tile-8": "Spaced reconstruction is on record.",
    }
    for selector, hint in expected_hints.items():
        expect(clean_page.locator(selector)).to_have_attribute("data-evidence-hint", hint)
        tile_id = selector.removeprefix("#")
        expect(clean_page.locator(selector)).to_have_attribute(
            "aria-describedby", f"{tile_id}-evidence-hint"
        )
        expect(clean_page.locator(f"#{tile_id}-evidence-hint")).to_have_text(hint)
    expect(clean_page.locator("#tile-0")).not_to_have_attribute("data-evidence-hint", re.compile(r".+"))
    expect(clean_page.locator("#tile-0")).not_to_have_attribute("aria-describedby", re.compile(r".+"))
    for selector in ("#tile-6", "#tile-7"):
        expect(clean_page.locator(selector)).not_to_have_attribute("data-evidence-hint", re.compile(r".+"))
        expect(clean_page.locator(selector)).not_to_have_attribute("aria-describedby", re.compile(r".+"))
        expect(clean_page.locator(f"{selector} .iso-board-state-title")).to_have_count(0)
    expect(clean_page.locator("#tile-7")).to_have_attribute("data-board-state", "solidified")

    # Button semantics so screen readers announce tiles as actionable.
    expect(clean_page.locator("#tile-1")).to_have_attribute("role", "button")
    expect(clean_page.locator("#tile-1")).to_have_attribute("tabindex", "0")
    expect(clean_page.locator("#tile-1")).to_have_attribute(
        "aria-label", "Resume Primed Board Tile"
    )

    # Populated tiles must not carry the empty "+" affordance from a prior
    # render — syncTile drops it defensively in case the canonical
    # renderGrid innerHTML rewrite was bypassed (cross-tab storage events).
    populated_with_orphan_affordance = clean_page.locator(
        "#grid-svg .tile-group:not(.empty) .empty-tile-affordance"
    )
    expect(populated_with_orphan_affordance).to_have_count(0)

    clean_page.locator("#tile-1").focus()
    expect(clean_page.locator(".room-label")).to_contain_text("Primed Board Tile")
    expect(clean_page.locator(".room-label")).to_contain_text("Resume")

    # Keyboard activation: SVG <g> doesn't fire click on Enter natively,
    # so app.js binds a keydown handler explicitly.
    clean_page.locator("#tile-8").focus()
    clean_page.keyboard.press("Enter")
    expect(clean_page.locator("#concept-header-title")).to_contain_text("Front Board Tile")
    assert clean_page.locator("body").get_attribute("data-map-open") == "true"

    clean_page.evaluate(seed_board_concepts(8))
    clean_page.reload()
    _wait_for_app_settled(clean_page)
    expect(clean_page.locator("#ignition-view")).to_be_visible()
    clean_page.locator("#nav-dashboard").click()
    clean_page.wait_for_function(
        """() => {
            const hero = document.querySelector('.hero-card.intro-page');
            const tile = document.getElementById('tile-8');
            return hero
                && window.getComputedStyle(hero).display !== 'none'
                && tile
                && tile.getClientRects().length > 0;
        }"""
    )
    empty_tile = clean_page.locator("#tile-8")
    expect(empty_tile).to_be_visible()
    expect(empty_tile).to_have_class(re.compile(r"\bempty\b"))
    expect(empty_tile).to_have_attribute(
        "aria-label", "Start from memory"
    )

    empty_tile.focus()
    clean_page.evaluate("App.showDashboard()")
    expect(clean_page.locator(".room-label")).to_contain_text("Start from memory")

    # A final-concept deletion arriving from another tab must route through
    # the canonical Desk renderer, not leave stale populated markup behind.
    expect(clean_page.locator("#tile-0 .tile-top")).to_have_count(1)
    clean_page.evaluate(
        """(() => {
            localStorage.setItem('learnops_concepts', '[]');
            window.dispatchEvent(new StorageEvent('storage', {
                key: 'learnops_concepts',
                newValue: '[]',
            }));
            document.getElementById('tile-0').insertAdjacentHTML(
                'beforeend', '<g class="empty-tile-affordance"></g>'
            );
        })()"""
    )
    expect(clean_page.locator("#tile-0 .empty-tile-affordance")).to_have_count(0)
    expect(clean_page.locator("#grid-container")).to_have_class(re.compile(r"\bis-first-use\b"))
    expect(clean_page.locator("#grid-svg .tile-group.is-capacity[aria-hidden='true']")).to_have_count(8)
    expect(clean_page.locator("#grid-svg .tile-group[role='button']")).to_have_count(1)
    expect(clean_page.locator("#tile-4")).to_have_attribute("aria-label", "Choose a topic")
    expect(clean_page.locator("#tile-0 .tile-top")).to_have_count(0)
    expect(clean_page.locator("#tile-0 .tile-top-empty")).to_have_count(1)
    expect(clean_page.locator("#concept-list .concept-item")).to_have_count(0)
    assert captured["console_errors"] == []
    assert captured["failed_requests"] == []


def test_desk_board_expands_after_first_saved_session(
    clean_page: Page, base_url: str, captured: dict
) -> None:
    """First use shows one plate; one saved session restores the full board."""

    # Tile bboxes intentionally NOT compared: populated tiles render a
    # crystal pin that extends above the iso platform, so their full bbox
    # is taller than empty tiles. We compare the iso platform (.tile-top
    # polygon — present in both states) instead, which captures the
    # structural layout the user cares about.
    sample_script = """(() => {
        if (typeof App !== 'undefined' && App.showDashboard) App.showDashboard();
        const r = (el) => {
            const b = el?.getBoundingClientRect();
            return b ? { x: Math.round(b.left), y: Math.round(b.top),
                         w: Math.round(b.width), h: Math.round(b.height) } : null;
        };
        const heroCard = document.querySelector('.hero-card.intro-page');
        const deskFrame = document.querySelector('.desk-frame');
        const gridContainer = document.getElementById('grid-container');
        const grid = document.getElementById('grid-svg');
        const tiles = Array.from(document.querySelectorAll('#grid-svg .tile-group'));
        const gridBox = grid?.getBoundingClientRect();
        return {
            heroCard: r(heroCard),
            heroDirection: heroCard ? getComputedStyle(heroCard).flexDirection : null,
            deskFrame: r(deskFrame),
            gridContainer: r(gridContainer),
            gridContainerDisplay: gridContainer
                ? window.getComputedStyle(gridContainer).display : null,
            svg: r(grid),
            viewBox: grid?.getAttribute('viewBox'),
            tileCount: tiles.length,
            visibleTileCount: tiles.filter(
                (tile) => window.getComputedStyle(tile).display !== 'none'
            ).length,
            helperText: document.querySelector('.desk-helper')?.textContent,
            helperDisplay: getComputedStyle(document.querySelector('.desk-helper')).display,
            indexHeaderDisplay: getComputedStyle(document.querySelector('.desk-index-header')).display,
            indexTitle: document.querySelector('.desk-index-title')?.textContent,
            conceptCount: document.querySelector('#desk-concept-count')?.textContent,
            conceptCountLabel: document.querySelector('#desk-concept-count')?.getAttribute('aria-label'),
            panel: r(document.querySelector('.intro-content')),
            primaryView: document.body.dataset.primaryView,
            deskFirstUse: document.body.dataset.deskFirstUse,
            drawerToggleDisplay: getComputedStyle(document.querySelector('.drawer-toggle')).display,
            tilePlatformPositions: tiles.map(t => {
                const top = t.querySelector('.tile-top, .tile-top-empty');
                const b = top?.getBoundingClientRect();
                const platform = b && gridBox ? {
                    x: Math.round(b.left - gridBox.left),
                    y: Math.round(b.top - gridBox.top),
                    w: Math.round(b.width),
                    h: Math.round(b.height),
                } : null;
                return { id: t.id, platform };
            }),
        };
    })()"""

    def seed_n_concepts(count: int) -> str:
        return f"""(() => {{
            const concepts = [];
            const states = ['growing', 'fractured', 'actualized', 'hibernating'];
            for (let i = 0; i < {count}; i++) {{
                concepts.push({{
                    id: 'seed-' + i,
                    name: 'Concept ' + (i + 1),
                    state: states[i % states.length],
                    createdAt: Date.now() + i,
                    graphData: JSON.stringify({{
                        metadata: {{ core_thesis: 'seed',
                                     drill_status: i % 2 ? 'primed' : null }},
                        backbone: [],
                        clusters: [],
                    }}),
                }});
            }}
            localStorage.setItem('learnops_concepts', JSON.stringify(concepts));
            if (concepts.length) {{
                localStorage.setItem('learnops_active', concepts[0].id);
            }} else {{
                localStorage.removeItem('learnops_active');
            }}
        }})()"""

    clean_page.set_viewport_size({"width": 390, "height": 844})
    _enter_app_shell_as_guest(clean_page, base_url)
    samples = {}
    for count in [0, 1, 5, 9]:
        clean_page.evaluate(seed_n_concepts(count))
        clean_page.reload()
        _wait_for_app_settled(clean_page)
        clean_page.evaluate("App.showDashboard()")
        samples[count] = clean_page.evaluate(sample_script)

    # Any saved session restores the existing full-board geometry. Only the
    # completely empty state collapses to the single centre plate.
    ref = samples[9]
    assert ref["tileCount"] == 9, "9-concept desk must render 9 tiles"
    assert ref["visibleTileCount"] == 9
    assert ref["viewBox"] == "0 0 420 365"
    assert ref["gridContainerDisplay"] == "block"
    assert ref["heroCard"] is not None
    assert ref["gridContainer"]["w"] > 0 and ref["gridContainer"]["h"] > 0
    assert ref["helperDisplay"] == "none"
    assert ref["indexHeaderDisplay"] == "flex"
    assert ref["indexTitle"] == "Concepts"
    assert ref["conceptCount"] == "9"
    assert ref["conceptCountLabel"] == "9 concepts"

    first_use = samples[0]
    assert first_use["tileCount"] == 9
    assert first_use["visibleTileCount"] == 1
    assert first_use["viewBox"] == "140 119 140 130"
    assert 184 <= first_use["gridContainer"]["w"] <= 200
    assert first_use["gridContainerDisplay"] == "block"
    assert first_use["helperText"] == "Then write what you remember."
    assert first_use["helperDisplay"] != "none"
    assert first_use["indexHeaderDisplay"] == "none"
    assert first_use["primaryView"] == "desk"
    assert first_use["deskFirstUse"] == "true"
    assert first_use["drawerToggleDisplay"] == "none"

    for count in (1, 5):
        sample = samples[count]
        assert sample["tileCount"] == 9, (
            f"desk at {count} concepts must still render all 9 tile slots, "
            f"got {sample['tileCount']}"
        )
        assert sample["visibleTileCount"] == 9
        assert sample["viewBox"] == "0 0 420 365"
        assert sample["helperText"] == "Choose a session to reconstruct from memory."
        assert sample["helperDisplay"] == "none"
        assert sample["indexHeaderDisplay"] == "flex"
        assert sample["indexTitle"] == "Concepts"
        assert sample["conceptCount"] == str(count)
        assert sample["conceptCountLabel"] == f"{count} {'concept' if count == 1 else 'concepts'}"
        assert sample["panel"]["x"] >= 0
        assert sample["panel"]["x"] + sample["panel"]["w"] <= 390
        assert sample["primaryView"] == "desk"
        assert sample["deskFirstUse"] == "false"
        assert sample["drawerToggleDisplay"] != "none"
        assert sample["gridContainerDisplay"] == "block", (
            f"#grid-container hidden at {count} concepts (was display="
            f"{sample['gridContainerDisplay']!r}); empty desk regression"
        )
        assert sample["heroCard"] == ref["heroCard"], (
            f"hero-card geometry differs at {count} concepts: "
            f"got {sample['heroCard']}, expected {ref['heroCard']}"
        )
        for dimension in ("x", "w", "h"):
            assert sample["gridContainer"][dimension] == ref["gridContainer"][dimension], (
                f"grid-container {dimension} differs at {count}: "
                f"got {sample['gridContainer']}, expected {ref['gridContainer']}"
            )
            assert sample["svg"][dimension] == ref["svg"][dimension], (
                f"grid-svg {dimension} differs at {count}: "
                f"got {sample['svg']}, expected {ref['svg']}"
            )
        for ref_tile, sample_tile in zip(
            ref["tilePlatformPositions"],
            sample["tilePlatformPositions"],
            strict=True,
        ):
            assert ref_tile["id"] == sample_tile["id"]
            assert ref_tile["platform"] == sample_tile["platform"], (
                f"tile {ref_tile['id']} iso platform drifted at {count} concepts: "
                f"got {sample_tile['platform']}, expected {ref_tile['platform']}"
            )

    clean_page.set_viewport_size({"width": 320, "height": 720})
    clean_page.evaluate(seed_n_concepts(1))
    clean_page.reload()
    _wait_for_app_settled(clean_page)
    clean_page.evaluate("App.showDashboard()")
    narrow = clean_page.evaluate(sample_script)
    assert narrow["panel"]["x"] >= 0
    assert narrow["panel"]["x"] + narrow["panel"]["w"] <= 320
    assert 254 <= narrow["svg"]["w"] <= 262
    assert clean_page.evaluate(
        "document.documentElement.scrollWidth <= window.innerWidth"
    )

    # The user's compact desktop viewport still has enough room for the
    # canonical board. Keep the Desk frame stacked so the header cannot split
    # the panel into a narrow second column.
    clean_page.set_viewport_size({"width": 1012, "height": 1114})
    clean_page.wait_for_function("window.innerWidth === 1012")
    compact_desktop = clean_page.evaluate(sample_script)
    assert compact_desktop["heroDirection"] == "column"
    assert compact_desktop["deskFrame"]["x"] == compact_desktop["panel"]["x"]
    assert compact_desktop["deskFrame"]["w"] == compact_desktop["panel"]["w"]
    assert compact_desktop["panel"]["w"] >= 520
    assert 400 <= compact_desktop["svg"]["w"] <= 420
    panel_center = compact_desktop["panel"]["x"] + compact_desktop["panel"]["w"] / 2
    board_center = compact_desktop["svg"]["x"] + compact_desktop["svg"]["w"] / 2
    assert abs(panel_center - board_center) <= 1
    assert clean_page.evaluate(
        "document.documentElement.scrollWidth <= window.innerWidth"
    )

    clean_page.set_viewport_size({"width": 1280, "height": 720})
    clean_page.wait_for_function("window.innerWidth === 1280")
    desktop = clean_page.evaluate(sample_script)
    assert desktop["panel"]["x"] >= 0
    assert desktop["panel"]["x"] + desktop["panel"]["w"] <= 1280
    assert 360 <= desktop["svg"]["w"] <= 420
    assert desktop["svg"]["x"] >= 0
    assert desktop["svg"]["x"] + desktop["svg"]["w"] <= 1280
    assert clean_page.evaluate(
        "document.documentElement.scrollWidth <= window.innerWidth"
    )

    clean_page.set_viewport_size({"width": 390, "height": 844})
    clean_page.wait_for_function("window.innerWidth === 390")
    clean_page.evaluate(
        "() => new Promise(resolve => requestAnimationFrame(() => "
        "requestAnimationFrame(resolve)))"
    )
    expect(clean_page.locator(".desk-index-header")).to_be_visible()

    assert captured["console_errors"] == []
    assert captured["failed_requests"] == []


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
    _wait_for_app_settled(clean_page)

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
    listener. Specific 404 paths can be allow-listed via EXPECTED_404_PATHS in
    conftest.py. Chromium ERR_ABORTED noise for narrow bootstrap API paths is
    filtered via EXPECTED_ABORTED_BOOTSTRAP_PATHS; actual HTTP failures and
    aborted app assets still count.
    """
    _enter_app_shell_as_guest(clean_page, base_url)
    _wait_for_app_settled(clean_page)

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
    _wait_for_app_settled(clean_page)

    errors = captured["console_errors"]
    theme_related = [
        m for m in errors if "theme" in m.text.lower() or "learnops" in m.text.lower()
    ]
    assert not theme_related, (
        f"theme preloader produced console errors on blank state: "
        f"{[m.text for m in theme_related]}"
    )
