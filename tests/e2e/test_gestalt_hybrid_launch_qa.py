"""QA browser pass for the source-less sketch-to-scaffold loop.

Run against a local dev server:

    SOCRATINK_E2E_LOCAL_GUEST=1 pytest tests/e2e/test_gestalt_hybrid_launch_qa.py -v

This test uses the real Ignition and Launch Pad UI. It mocks only the two AI
network seams so the pass is fast and deterministic while still catching
frontend regressions, console errors, failed requests, and unexpected 4xx/5xx
responses.
"""

from __future__ import annotations

import json
import re
from urllib.parse import urljoin

import pytest
from playwright.sync_api import Page, expect


def _enter_app_shell_as_guest(page: Page, base_url: str) -> None:
    page.goto(urljoin(base_url + "/", "auth/e2e/guest?return_to=%2F"))
    expect(page.locator("#drawer")).to_be_attached()
    expect(page.locator("#nav-ignition")).to_be_attached()


def _same_origin_response_failures(page: Page, same_origin) -> list[str]:
    failures: list[str] = []

    def _on_response(response) -> None:
        if same_origin(response.url) and response.status >= 400:
            failures.append(f"{response.status} {response.url}")

    page.on("response", _on_response)
    return failures


def _page_errors(page: Page) -> list[str]:
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    return errors


def _mock_extract_response() -> dict:
    return {
        "provisional_map": {
            "metadata": {
                "source_title": "Thermostat feedback loop",
                "core_thesis": "A thermostat compares a room reading to a target before calling for heat.",
                "architecture_type": "causal_chain",
                "difficulty": "easy",
                "governing_assumptions": ["Learner works from a clinic facilities example."],
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
            "relationships": {"domain_mechanics": [], "learning_prerequisites": []},
            "frameworks": [],
        }
    }


def test_source_less_launch_pad_end_to_end_qa(
    clean_page: Page,
    base_url: str,
    captured: dict,
    same_origin,
) -> None:
    """Real browser QA pass: sketch -> tailored prompt -> draft -> reveal -> repair."""

    sketch_text = (
        "I manage facilities for a small clinic. I think thermostats turn heat on when "
        "the room feels cold, but I am fuzzy on what they compare."
    )
    page_errors = _page_errors(clean_page)
    bad_responses = _same_origin_response_failures(clean_page, same_origin)
    requests_seen: list[str] = []
    drill_payloads: list[dict] = []

    def fulfill_extract(route) -> None:
        payload = route.request.post_data_json
        requests_seen.append(f"POST /api/extract {payload['name']}")
        assert payload["name"] == "Thermostat feedback loop"
        assert payload["starting_sketch"] == sketch_text
        assert payload["source"] is None
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(_mock_extract_response()),
        )

    def fulfill_drill(route) -> None:
        payload = route.request.post_data_json
        drill_payloads.append(payload)
        requests_seen.append(f"POST /api/drill {payload['node_id']}")
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

    clean_page.route("**/api/extract", fulfill_extract)
    clean_page.route("**/api/drill", fulfill_drill)

    _enter_app_shell_as_guest(clean_page, base_url)
    clean_page.evaluate("localStorage.clear(); sessionStorage.clear();")

    clean_page.locator("#nav-ignition").click()
    expect(clean_page.locator("#ignition-title")).to_have_text("What are you trying to explain?")
    clean_page.locator("#hero-single-input-field").fill("Thermostat feedback loop")
    expect(clean_page.locator("#hero-door-submit")).to_be_enabled()
    clean_page.locator("#hero-door-submit").click()

    expect(clean_page.locator("#launch-pad-view")).to_be_visible()
    expect(clean_page.locator("#launch-pad-concept-name")).to_have_text(
        "Thermostat feedback loop"
    )
    clean_page.locator("#launch-pad-input").fill(sketch_text)
    expect(clean_page.locator("#launch-pad-submit")).to_be_enabled()
    clean_page.locator("#launch-pad-submit").click()

    canvas = clean_page.locator(".concept-page-b2__gestalt")
    expect(canvas).to_be_visible(timeout=10_000)
    expect(clean_page.locator("#drill-chamber-view")).to_be_visible(timeout=10_000)
    expect(clean_page.locator("#chamber-question")).to_contain_text(
        "What do you think the thermostat checks before it calls for heat?",
        timeout=20_000,
    )
    seda_state = clean_page.wait_for_function(
        """() => {
          const key = Object.keys(localStorage).find((k) => k.startsWith('socratink:seda-session:v1:'));
          if (!key) return null;
          const value = JSON.parse(localStorage.getItem(key));
          return value?.sessionId && value?.latest ? value : null;
        }""",
        timeout=20_000,
    ).json_value()
    assert seda_state["latest"]["awaiting"]["key"] in {"learner_goal", "launch_attempt"}
    clean_page.locator("#chamber-exit").click()
    expect(clean_page.locator("#drill-chamber-view")).to_be_hidden()
    expect(canvas).to_be_visible(timeout=10_000)
    expect(canvas).not_to_contain_text("Shaped by your sketch")
    expect(canvas.locator(".concept-page-b2__attempt")).to_contain_text(
        "What do you think the thermostat checks before it calls for heat?"
    )
    expect(canvas).to_contain_text("Compare target")
    expect(canvas).not_to_contain_text("Call for heat")
    expect(canvas).not_to_contain_text("compares measured room temperature")
    expect(canvas).not_to_contain_text("Generated description should not leak")
    expect(canvas.locator(".concept-page-b2__route-item")).to_have_count(0)

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
    expect(clean_page.locator("#concept-view-switch")).to_be_hidden()

    assert "POST /api/extract Thermostat feedback loop" in requests_seen
    assert drill_payloads == []

    if page_errors:
        pytest.fail("pageerror events:\n" + "\n".join(f"  - {err}" for err in page_errors))
    if captured["console_errors"]:
        rendered = "\n".join(
            f"  - {msg.text} (at {msg.location})" for msg in captured["console_errors"]
        )
        pytest.fail(f"same-origin console errors:\n{rendered}")
    if captured["failed_requests"]:
        rendered = "\n".join(
            f"  - {req.method} {req.url} ({req.failure})"
            for req in captured["failed_requests"]
        )
        pytest.fail(f"same-origin failed requests:\n{rendered}")
    if bad_responses:
        pytest.fail("same-origin 4xx/5xx responses:\n" + "\n".join(bad_responses))
