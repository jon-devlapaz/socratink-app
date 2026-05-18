"""Smoke suite for socratink-app.

What this catches
-----------------
- Backend is up and the FastAPI app booted (`/api/health` shape valid)
- Frontend renders without a blank-page regression (critical DOM IDs present)
- Anonymous Supabase sessions are labeled as guest, not signed-in users
- First-run guidance stays inline instead of regressing to a modal
- Library cards render training evidence instead of AI summary copy
- Inline concept-page attempts persist, retry, and preserve active-entry state
- Study reveal and repair records survive localStorage reload/reconstruction
- Drawer toggle stays visible after opening a library concept
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
from urllib.parse import urljoin, urlparse

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


_cached_guest_cookies = None

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
        page.goto(urljoin(base_url + "/", "auth/e2e/guest?return_to=%2F"))
        session = _fetch_browser_session(page)
        if session.get("authenticated") or session.get("guest_mode"):
            _cached_guest_cookies = page.context.cookies()
            return

    page.goto(base_url)
    if "/login" not in page.url:
        session = _fetch_browser_session(page)
        if session.get("authenticated") or session.get("guest_mode"):
            if not _cached_guest_cookies:
                _cached_guest_cookies = page.context.cookies()
            return
        page.goto(urljoin(base_url + "/", "login?return_to=%2F"))
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
        "Name the concept first. socratink will ask for your starting map before study content appears."
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


def test_library_card_uses_training_evidence_not_ai_summary(
    page: Page, base_url: str
) -> None:
    """Library summaries must be learner evidence, not generated source text."""
    _enter_app_shell_as_guest(page, base_url)
    page.evaluate("localStorage.clear(); sessionStorage.clear();")
    _seed_training_truth_concept(page)

    page.locator("#nav-library").click()
    card = page.locator(".library-card-vault", has_text="Training Truth QA")
    expect(card).to_be_visible()
    expect(card.locator(".library-card-summary")).to_have_text(
        "Learner-owned reconstruction visible in Library."
    )
    expect(card).not_to_contain_text("AI GENERATED CORE THESIS SHOULD NOT APPEAR")
    expect(card).not_to_contain_text("SOURCE PREVIEW SHOULD NOT APPEAR")


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
    _enter_app_shell_as_guest(page, base_url)
    page.evaluate("localStorage.clear(); sessionStorage.clear();")

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
    assert training["node_records"]["qa-node"]["attempts"][0]["classification"] == "strong"

    card.click()
    expect(page.locator("#concept-header-title")).to_contain_text("QA fixture source")
    expect(page.locator(".concept-page-b2__provenance")).to_have_text(
        "Shaped from your launch attempt, not verified against a source."
    )
    expect(page.locator(".concept-page-b2__entry-eyebrow")).to_have_text(
        "Study the gap"
    )
    expect(page.locator(".concept-page-b2__entry-cta")).to_have_text(
        "Compare with notes"
    )
    page.locator(".concept-page-b2__entry-cta").click()
    expect(page.locator(".concept-page-b2__evidence")).to_contain_text(
        "Learner-owned reconstruction visible in Library."
    )
    expect(page.locator(".concept-page-b2__evidence")).to_contain_text(
        "No repair hinge recorded for this reconstruction."
    )
    expect(page.locator(".concept-page-b2__study-note")).to_contain_text(
        "The revealed study note names the comparison target after the cold attempt: identify the mechanism, then mark any missing link for repair."
    )
    expect(page.locator(".concept-page-b2__entry-eyebrow")).to_have_text(
        "review pending"
    )
    expect(page.locator(".concept-page-b2__entry-cta")).to_have_count(0)
    revealed_training = page.evaluate(
        """JSON.parse(localStorage.getItem('socratink:training:v1:local-qa-training-concept'))"""
    )
    assert (
        revealed_training["node_records"]["qa-node"]["study_revealed_at"]
        is not None
    )
    page.locator("[data-edit-threshold]").click()
    page.locator(".concept-page-b2__threshold-input").fill("Temporary learner sketch.")
    page.keyboard.press("Escape")
    expect(page.locator(".concept-page-b2__threshold")).to_contain_text(
        "Learner rough sketch baseline."
    )
    page.locator("[data-edit-threshold]").click()
    page.locator(".concept-page-b2__threshold-input").fill("Updated learner sketch.")
    page.locator(".concept-page-b2__threshold-save").click()
    expect(page.locator(".concept-page-b2__threshold")).to_contain_text(
        "Updated learner sketch."
    )
    expect(page.locator(".concept-page-b2__entry-eyebrow")).to_have_text(
        "review pending"
    )
    edited_training = page.evaluate(
        """JSON.parse(localStorage.getItem('socratink:training:v1:local-qa-training-concept'))"""
    )
    assert edited_training["sketch"]["text"] == "Updated learner sketch."


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
        "Study the gap"
    )
    expect(page.locator(".concept-page-b2__entry-cta")).to_have_text(
        "Compare with notes"
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
    _enter_app_shell_as_guest(page, base_url)
    page.evaluate("localStorage.clear(); sessionStorage.clear();")

    page.locator("#nav-library").click()
    page.locator("[data-local-repair-qa-seed]").click()
    page.locator(".library-card-vault", has_text="Repair Truth QA").click()
    expect(page.locator("#concept-header-title")).to_contain_text("Repair QA source")
    expect(page.locator(".concept-page-b2__entry-eyebrow")).to_have_text(
        "Study the gap"
    )

    page.locator(".concept-page-b2__entry-cta").click()
    expect(page.locator(".concept-page-b2__entry-eyebrow")).to_have_text(
        "Needs repair"
    )
    expect(page.locator(".concept-page-b2__repair")).to_contain_text(
        "voltage-gated sodium channels"
    )
    expect(page.locator(".concept-page-b2__repair")).to_contain_text(
        "Name that threshold opens the channel"
    )

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
    expect(page.locator(".concept-page-b2__entry-eyebrow")).to_have_text(
        "Needs repair"
    )
    expect(page.locator(".concept-page-b2__entry-cta")).to_have_text(
        "Try from memory again"
    )
    expect(page.locator(".concept-page-b2__repair")).to_be_visible()
    page.locator(".concept-page-b2__entry-cta").click()
    expect(page.locator(".concept-page-b2__attempt-input")).to_be_visible()
    expect(page.locator(".concept-page-b2__repair")).to_have_count(0)
    repaired_training = page.evaluate(
        """JSON.parse(localStorage.getItem('socratink:training:v1:qa-repair-concept'))"""
    )
    assert repaired_training["node_records"]["repair-node"]["repairs"][0]["text"] == (
        "Threshold opens voltage-gated sodium channels; the gradient drives sodium flow only after that gate opens."
    )
    assert (
        repaired_training["node_records"]["repair-node"]["attempts"][0]["classification"]
        == "thin"
    )


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
    page.locator('.concept-strip__node[data-entry-id="entry-two"]').click()
    expect(page.locator(".concept-page-b2__entry-eyebrow")).to_have_text(
        "Study the gap"
    )
    page.locator(".concept-page-b2__entry-cta").click()
    expect(page.locator(".concept-strip__active-name")).to_contain_text(
        "Later target · 2 of 2"
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
                    source_title: 'Cold Attempt QA source',
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
    expect(page.locator("#concept-header-title")).to_contain_text(
        "Cold Attempt QA source"
    )
    page.locator(".concept-page-b2__entry-cta").click()
    expect(page.locator(".concept-page-b2__attempt")).to_be_visible()
    expect(page.locator(".concept-page-b2__study-note")).to_have_count(0)
    page.locator(".concept-page-b2__attempt-save").click()
    expect(page.locator("[data-attempt-error]")).to_have_text(
        "Put down the part you can explain, even if it is incomplete."
    )

    learner_text = "  Sodium flows in because there is more outside.  "
    page.locator(".concept-page-b2__attempt-input").fill(learner_text)
    page.locator(".concept-page-b2__attempt-save").click()
    expect(page.locator("[data-attempt-error]")).to_have_text(
        "The system could not record this yet. Try again."
    )
    page.locator(".concept-page-b2__attempt-save").click()
    expect(page.locator(".concept-page-b2__entry-eyebrow")).to_have_text(
        "Study the gap"
    )
    expect(page.locator(".concept-page-b2__entry-cta")).to_have_text(
        "Compare with notes"
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
    page.locator(".concept-page-b2__entry-cta").click()
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
        "Ready to reconstruct again"
    )
    page.locator(".concept-page-b2__entry-cta").click()
    page.locator(".concept-page-b2__attempt-input").fill(
        "The mechanism opens first, then the downstream flow follows."
    )
    page.locator(".concept-page-b2__attempt-save").click()

    expect(page.locator(".concept-page-b2__entry-eyebrow")).to_have_text(
        "solidified"
    )
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
    page.locator(".concept-page-b2__entry-cta").click()
    page.locator(".concept-page-b2__attempt-input").fill(
        "The mechanism opens first, then the downstream flow follows."
    )
    save_button = page.locator(".concept-page-b2__attempt-save")
    save_button.click()
    expect(page.locator(".concept-page-b2__entry-eyebrow")).to_have_text(
        "Study the gap"
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
                    "agent_response": "Make one concrete guess about the mechanism before reading.",
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
    page.locator(".concept-page-b2__entry-cta").click()
    page.locator(".concept-page-b2__attempt-input").fill("I do not know.")
    save_button = page.locator(".concept-page-b2__attempt-save")
    save_button.click()

    expect(page.locator("[data-attempt-error]")).to_have_text(
        "Make one concrete guess about the mechanism before reading."
    )
    expect(save_button).to_be_enabled()
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
    page.locator(".concept-page-b2__entry-cta").click()
    page.locator(".concept-page-b2__attempt-input").fill(
        "The mechanism opens first."
    )
    save_button = page.locator(".concept-page-b2__attempt-save")
    save_button.click()

    expect(page.locator("[data-attempt-error]")).to_have_text(
        "The system could not record this yet. Try again."
    )
    expect(save_button).to_be_enabled()
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

    clean_page.locator("#nav-library").click()
    clean_page.locator(".library-card-vault", has_text="Test Concept").click()
    expect(clean_page.locator("#concept-header-title")).to_contain_text("Test Concept")
    expect(toggle).to_be_visible()


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
    your_library = clean_page.locator("#library-content .library-section", has_text="Your Library")
    your_library.locator(".library-card-vault", has_text="Test Concept").click()

    expect(clean_page.locator("#concept-header-title")).to_contain_text("Test Concept")
    assert clean_page.locator("body").get_attribute("data-map-open") == "true"
    expect(clean_page.locator("#nav-dashboard")).not_to_have_class(re.compile(r"\bactive\b"))
    expect(clean_page.locator(".concept-item.active")).to_have_count(1)

    clean_page.locator("#nav-dashboard").click()
    expect(clean_page.locator("#nav-dashboard")).to_have_class(re.compile(r"\bactive\b"))
    expect(clean_page.locator(".concept-item.active")).to_have_count(0)


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
    clean_page.locator(".concept-page-b2__entry-cta").click()
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

    delete_button = clean_page.locator(".concept-item.active .concept-delete")

    def dismiss_delete(dialog) -> None:
        assert "Delete \"Test Concept\"?" in dialog.message
        dialog.dismiss()

    clean_page.once("dialog", dismiss_delete)
    delete_button.click()
    expect(clean_page.locator("#concept-header-title")).to_contain_text("Test Concept")
    expect(clean_page.locator(".concept-item.active")).to_have_count(1)

    def accept_delete(dialog) -> None:
        assert "Delete \"Test Concept\"?" in dialog.message
        dialog.accept()

    clean_page.once("dialog", accept_delete)
    delete_button.click()
    expect(clean_page.locator("#title")).to_have_text("What do you want to understand?")
    expect(clean_page.locator(".concept-item")).to_have_count(0)
    expect(clean_page.locator("#concept-header-title")).not_to_be_visible()
    assert clean_page.locator("body").get_attribute("data-map-open") != "true"
    assert (
        clean_page.evaluate(
            """localStorage.getItem('socratink:training:v1:fixture-concept')"""
        )
        is None
    )


def test_desk_iso_board_state_surface_and_room_labels(
    clean_page: Page, base_url: str, captured: dict
) -> None:
    """Desk board exposes truthful tile state and quiet hover/focus labels."""

    def seed_board_concepts(count: int = 9) -> str:
        return f"""(() => {{
            const graph = (status, extra = {{}}) => JSON.stringify({{
                metadata: {{
                    core_thesis: 'Seeded thesis',
                    drill_status: status,
                    drill_phase: status === 'primed' ? 'study' : null,
                    ...extra,
                }},
                backbone: [],
                clusters: [],
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
                    graphData: graph('primed'),
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
                    state: 'actualized',
                    createdAt: Date.now() + 3,
                    graphData: graph('solidified'),
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
        "#tile-2": ("fractured", "drilled"),
        "#tile-3": ("actualized", "solidified"),
        "#tile-4": ("hibernating", "locked"),
        "#tile-7": ("growing", "solidified"),
        "#tile-8": ("actualized", "solidified"),
    }
    for selector, (source_state, board_state) in expected_states.items():
        tile = clean_page.locator(selector)
        expect(tile).to_have_attribute("data-source-state", source_state)
        expect(tile).to_have_attribute("data-board-state", board_state)

    # Button semantics so screen readers announce tiles as actionable.
    expect(clean_page.locator("#tile-1")).to_have_attribute("role", "button")
    expect(clean_page.locator("#tile-1")).to_have_attribute("tabindex", "0")
    expect(clean_page.locator("#tile-1")).to_have_attribute(
        "aria-label", "Open Primed Board Tile"
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
    expect(clean_page.locator(".room-label")).to_contain_text("Open entry")

    # Keyboard activation: SVG <g> doesn't fire click on Enter natively,
    # so app.js binds a keydown handler explicitly.
    clean_page.locator("#tile-8").focus()
    clean_page.keyboard.press("Enter")
    expect(clean_page.locator("#concept-header-title")).to_contain_text("Front Board Tile")
    assert clean_page.locator("body").get_attribute("data-map-open") == "true"

    clean_page.evaluate(seed_board_concepts(8))
    clean_page.reload()
    _wait_for_app_settled(clean_page)
    clean_page.locator("#nav-dashboard").click()
    expect(clean_page.locator("#tile-8")).to_have_class(re.compile(r"\bempty\b"))
    expect(clean_page.locator("#tile-8")).to_have_attribute(
        "aria-label", "New concept"
    )

    clean_page.locator("#tile-8").focus()
    expect(clean_page.locator(".room-label")).to_contain_text("New concept")
    assert captured["console_errors"] == []
    assert captured["failed_requests"] == []


def test_desk_layout_identical_when_empty_or_populated(
    clean_page: Page, base_url: str, captured: dict
) -> None:
    """Empty desk (0 concepts) renders the same iso board geometry as populated.

    Regression: the layout.css empty-state rule used to hide #grid-container
    entirely, leaving an empty desk blank. The iso-board state-surface
    experiment overrides that so the 9-tile board is visible at all sizes
    of the library — its empty tiles invite creation via the + affordance.
    This guards that the hero-card, grid-container, svg, and per-tile
    positions are pixel-identical regardless of how many concepts exist.
    """

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
        const gridContainer = document.getElementById('grid-container');
        const grid = document.getElementById('grid-svg');
        const tiles = Array.from(document.querySelectorAll('#grid-svg .tile-group'));
        return {
            heroCard: r(heroCard),
            gridContainer: r(gridContainer),
            gridContainerDisplay: gridContainer
                ? window.getComputedStyle(gridContainer).display : null,
            svg: r(grid),
            tileCount: tiles.length,
            tilePlatformPositions: tiles.map(t => {
                const top = t.querySelector('.tile-top, .tile-top-empty');
                const b = top ? r(top) : null;
                return { id: t.id, platform: b };
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

    _enter_app_shell_as_guest(clean_page, base_url)
    samples = {}
    for count in [0, 1, 5, 9]:
        clean_page.evaluate(seed_n_concepts(count))
        clean_page.reload()
        _wait_for_app_settled(clean_page)
        clean_page.locator("#nav-dashboard").click()
        samples[count] = clean_page.evaluate(sample_script)

    # Reference is the populated state (9 concepts) — that's the layout
    # contract everyone expects. Empty (0) and partial (1, 5) must match.
    ref = samples[9]
    assert ref["tileCount"] == 9, "9-concept desk must render 9 tiles"
    assert ref["gridContainerDisplay"] == "block"
    assert ref["heroCard"] is not None
    assert ref["gridContainer"]["w"] > 0 and ref["gridContainer"]["h"] > 0

    for count, sample in samples.items():
        if count == 9:
            continue
        assert sample["tileCount"] == 9, (
            f"desk at {count} concepts must still render all 9 tile slots, "
            f"got {sample['tileCount']}"
        )
        assert sample["gridContainerDisplay"] == "block", (
            f"#grid-container hidden at {count} concepts (was display="
            f"{sample['gridContainerDisplay']!r}); empty desk regression"
        )
        assert sample["heroCard"] == ref["heroCard"], (
            f"hero-card geometry differs at {count} concepts: "
            f"got {sample['heroCard']}, expected {ref['heroCard']}"
        )
        assert sample["gridContainer"] == ref["gridContainer"], (
            f"grid-container geometry differs at {count}: "
            f"got {sample['gridContainer']}, expected {ref['gridContainer']}"
        )
        assert sample["svg"] == ref["svg"], (
            f"grid-svg geometry differs at {count}: "
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
