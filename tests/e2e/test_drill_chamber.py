"""Drill chamber smoke suite.

What this covers
----------------
- Chamber view exists in the DOM and is hidden by default after load
- Starting a drill opens the chamber and hides the map
- Exiting the chamber (via the exit link) restores the map

Known limitation
----------------
These tests target localhost:8000 which serves the main-branch code at the
time of writing. The drill-chamber-view markup and DrillChamber JS module
are only present on the feat/drill-chamber-port branch. Until that branch
is deployed or merged, the chamber-specific assertions will fail against the
live server. The tests are committed now so they run green once the branch
lands in production.

Run
---
    # local (start the app first: `bash scripts/dev.sh`)
    pytest tests/e2e/test_drill_chamber.py -v

    # against a deployed environment
    SOCRATINK_BASE_URL=https://socratink.com pytest tests/e2e/test_drill_chamber.py -v
"""

from __future__ import annotations

import json
import os
from typing import Any

import pytest
from playwright.sync_api import Page, expect


# --- helpers shared with smoke suite (duplicated to keep this file standalone) ---


def _enter_app_shell_as_guest(page: Page, base_url: str) -> None:
    """Navigate to base_url and land in the app shell as a guest session."""
    import re
    from urllib.parse import urljoin

    if os.getenv("SOCRATINK_E2E_LOCAL_GUEST"):
        page.goto(urljoin(base_url + "/", "auth/e2e/guest?return_to=%2F"))
        payload = page.evaluate(
            """async () => {
                const r = await fetch('/api/me', {
                  credentials: 'same-origin',
                  headers: { Accept: 'application/json' },
                });
                if (!r.ok) return {};
                return r.json();
            }"""
        )
        session = payload if isinstance(payload, dict) else {}
        if session.get("authenticated") or session.get("guest_mode"):
            return

    page.goto(base_url)
    if "/login" not in page.url:
        payload = page.evaluate(
            """async () => {
                const r = await fetch('/api/me', {
                  credentials: 'same-origin',
                  headers: { Accept: 'application/json' },
                });
                if (!r.ok) return {};
                return r.json();
            }"""
        )
        session = payload if isinstance(payload, dict) else {}
        if session.get("authenticated") or session.get("guest_mode"):
            return
        page.goto(urljoin(base_url + "/", "login?return_to=%2F"))
    if "/login" in page.url:
        expect(page.locator("#guest-continue-link")).to_be_visible()
        target_pattern = re.compile(r"^" + re.escape(base_url.rstrip("/")) + r"/?$")
        with page.expect_navigation(url=target_pattern, timeout=15_000):
            page.locator("#guest-continue-link").click()


def _seed_concept_with_graph(page: Page, concept_id: str = "drill-test-concept") -> None:
    """Seed a concept that has graph data and at least one drillable node."""
    page.evaluate(
        f"""(() => {{
            const now = new Date().toISOString();
            const graphData = JSON.stringify({{
                metadata: {{
                    core_thesis: 'Seeded thesis for drill chamber smoke.',
                    drill_status: null,
                    drill_phase: null,
                }},
                backbone: [{{
                    id: 'entry-a',
                    label: 'Entry A',
                    detail: 'Describe what Entry A means in your own words.',
                    drill_status: null,
                }}],
                clusters: [],
            }});
            localStorage.setItem('learnops_concepts', JSON.stringify([{{
                id: {json.dumps(concept_id)},
                name: 'Chamber Test Concept',
                createdAt: now,
                state: 'growing',
                contentPreview: 'Seeded thesis for drill chamber smoke.',
                contentType: 'fixture',
                graphData,
            }}]));
            localStorage.setItem('learnops_active', {json.dumps(concept_id)});
        }})()"""
    )


# --- tests -------------------------------------------------------------------


def test_drill_chamber_view_hidden_on_load(
    clean_page: Page, base_url: str
) -> None:
    """The chamber view must be present in the DOM but hidden on page load.

    This is a structural guard: the element must exist (so the JS module can
    bind to it) but must not be visible before a drill session starts.
    """
    _enter_app_shell_as_guest(clean_page, base_url)

    chamber = clean_page.locator("#drill-chamber-view")
    # Element must be in the DOM so the JS module can bind on first show().
    expect(chamber).to_be_attached()
    # Must not be visible to the user before any drill starts.
    expect(chamber).to_be_hidden()


def test_drill_chamber_opens_and_hides_map(
    clean_page: Page, base_url: str
) -> None:
    """Starting a drill opens the chamber view and hides the map stage.

    Sequence:
      1. Seed a concept with a graph and navigate to its map view.
      2. Invoke App.startDrill() via the browser to simulate the user
         clicking a drill-ready graph node.
      3. Assert the chamber is visible and the graph map stage is gone.

    Note: this test exercises the JS wiring (startDrill -> DrillChamber.show)
    without making a real network call to the drill API. The typing indicator
    may appear while the (mocked/unreachable) API request is in flight; the
    chamber visibility assertion passes regardless.
    """
    _seed_concept_with_graph(clean_page)
    _enter_app_shell_as_guest(clean_page, base_url)

    # Navigate to the concept map.
    clean_page.locator("#nav-library").click()
    clean_page.locator(".library-card-vault", has_text="Chamber Test Concept").click()
    expect(clean_page.locator("#concept-header-title")).to_contain_text(
        "Chamber Test Concept"
    )

    # Invoke startDrill with a minimal node context matching the seeded data.
    # DrillChamber.show() will fire synchronously; the API call is async.
    clean_page.evaluate(
        """(() => {
            if (typeof App === 'undefined' || typeof App.startDrill !== 'function') return;
            App.startDrill({
                id: 'entry-a',
                label: 'Entry A',
                fullLabel: 'Entry A',
                detail: 'Describe what Entry A means in your own words.',
            });
        })()"""
    )

    # Chamber must be visible after startDrill.
    expect(clean_page.locator("#drill-chamber-view")).to_be_visible()
    # Map stage must be hidden during an active drill.
    expect(clean_page.locator("#map-view")).to_be_hidden()


def test_drill_chamber_exit_restores_map(
    clean_page: Page, base_url: str
) -> None:
    """Clicking the chamber exit link cancels the drill and restores the map.

    Sequence:
      1. Open a concept map, start a drill (same setup as the round-trip test).
      2. Click the #chamber-exit link inside the chamber.
      3. Assert the chamber hides and the map view returns.
    """
    _seed_concept_with_graph(clean_page)
    _enter_app_shell_as_guest(clean_page, base_url)

    clean_page.locator("#nav-library").click()
    clean_page.locator(".library-card-vault", has_text="Chamber Test Concept").click()
    expect(clean_page.locator("#concept-header-title")).to_contain_text(
        "Chamber Test Concept"
    )

    clean_page.evaluate(
        """(() => {
            if (typeof App === 'undefined' || typeof App.startDrill !== 'function') return;
            App.startDrill({
                id: 'entry-a',
                label: 'Entry A',
                fullLabel: 'Entry A',
                detail: 'Describe what Entry A means in your own words.',
            });
        })()"""
    )

    expect(clean_page.locator("#drill-chamber-view")).to_be_visible()

    # Click the exit link; this fires the onExit handler -> cancelDrill().
    clean_page.locator("#chamber-exit").click()

    # Chamber must hide after exit.
    expect(clean_page.locator("#drill-chamber-view")).to_be_hidden()
    # Map view must be restored.
    expect(clean_page.locator("#map-view")).to_be_visible()


def test_completed_cold_attempt_updates_training_library_card(
    page: Page, base_url: str
) -> None:
    """A completed drill turn must become learner-owned Library evidence."""
    drill_calls: list[dict[str, Any]] = []

    def fulfill_drill(route):
        payload = route.request.post_data_json
        drill_calls.append(payload)
        if payload.get("session_phase") == "init":
            body = {
                "agent_response": "What causes the thermostat to turn heat on?",
                "generative_commitment": None,
                "answer_mode": None,
                "score_eligible": False,
                "help_request_reason": None,
                "classification": None,
                "gap_description": None,
                "routing": None,
                "response_tier": None,
                "response_band": None,
                "tier_reason": None,
                "node_id": payload["node_id"],
                "probe_count": 0,
                "nodes_drilled": 0,
                "attempt_turn_count": 0,
                "help_turn_count": 0,
                "graph_mutated": False,
                "ux_reward_emitted": False,
                "session_terminated": False,
                "termination_reason": None,
            }
        else:
            body = {
                "agent_response": "You made the first mark. Study can target the missing causal step.",
                "generative_commitment": True,
                "answer_mode": "attempt",
                "score_eligible": True,
                "help_request_reason": "none",
                "classification": "shallow",
                "gap_description": "The response names comparison but misses the resulting heater state.",
                "routing": "NEXT",
                "response_tier": 2,
                "response_band": "link",
                "tier_reason": "The answer names comparison but not the full causal transition.",
                "node_id": payload["node_id"],
                "probe_count": 0,
                "nodes_drilled": 1,
                "attempt_turn_count": 1,
                "help_turn_count": 0,
                "graph_mutated": True,
                "ux_reward_emitted": True,
                "session_terminated": False,
                "termination_reason": None,
            }
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(body),
        )

    page.route("**/api/drill", fulfill_drill)
    _enter_app_shell_as_guest(page, base_url)
    page.evaluate("localStorage.clear(); sessionStorage.clear();")
    _seed_concept_with_graph(page, "drill-training-concept")

    page.locator("#nav-library").click()
    page.locator(".library-card-vault", has_text="Chamber Test Concept").click()
    expect(page.locator("#concept-header-title")).to_contain_text(
        "Chamber Test Concept"
    )
    page.evaluate(
        """(() => {
            App.startDrill({
                id: 'entry-a',
                label: 'Entry A',
                fullLabel: 'Entry A',
                detail: 'Describe what Entry A means in your own words.',
            });
        })()"""
    )

    expect(page.locator("#chamber-composer")).to_be_enabled(timeout=8_000)
    learner_text = "The thermostat compares the room temperature to the setpoint."
    page.locator("#chamber-composer").fill(learner_text)
    page.locator("#chamber-send").click()

    expect(page.locator("#chamber-composer")).to_be_disabled(timeout=8_000)
    page.wait_for_function(
        """() => Boolean(localStorage.getItem('socratink:training:v1:drill-training-concept'))""",
        timeout=8_000,
    )
    assert len(drill_calls) == 2
    page.locator("#chamber-exit").click()
    page.locator("#nav-library").click()

    card = page.locator(".library-card-vault", has_text="Chamber Test Concept")
    expect(card.locator(".library-card-summary")).to_have_text(learner_text)
    stored = page.evaluate(
        """() => JSON.parse(localStorage.getItem('socratink:training:v1:drill-training-concept'))"""
    )
    assert stored["node_records"]["entry-a"]["attempts"][0]["classification"] == "thin"
    assert stored["node_records"]["entry-a"]["attempts"][0]["user_text"] == learner_text
