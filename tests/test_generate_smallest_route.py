"""Tests for the source-less smallest-route generation contract."""
from __future__ import annotations

from pathlib import Path

import pytest

from ai_service import _validate_smallest_route, SmallestRouteCapExceeded
from models.provisional_map import Cluster, LearnerScaffold, ProvisionalMap, Relationships, Subnode
from tests._helpers.provisional_map_factory import (
    provisional_map_with_node_count as _provisional_map_with_node_count,
)


REPO_ROOT = Path(__file__).resolve().parent.parent


def _learner_scaffold() -> LearnerScaffold:
    return LearnerScaffold(
        bloom_level="understand",
        learner_move="Say it",
        task_label="Starting model",
        task_cue="Put the relationship in your own words.",
        tailoring_anchor="You mentioned the input and output, so this starts there.",
        entry_prompt="How would you explain the relationship right now?",
        expected_shape="Write one or two sentences.",
        sentence_starter="My current guess is that...",
        blank_hint="Start with the part you named in your sketch.",
        evidence_goal="The learner states an initial model without reading source content.",
    )


def test_smallest_route_validator_accepts_one_node():
    """Suggested first target alone is allowed (n=1)."""
    pm = _provisional_map_with_node_count(1)
    _validate_smallest_route(pm)  # no raise


def test_smallest_route_validator_accepts_four_nodes():
    """1 first target + 3 backbone hints = 4. Allowed."""
    pm = _provisional_map_with_node_count(4)
    _validate_smallest_route(pm)  # no raise


def test_smallest_route_validator_rejects_five_nodes():
    """One over the cap. Must raise."""
    pm = _provisional_map_with_node_count(5)
    with pytest.raises(SmallestRouteCapExceeded):
        _validate_smallest_route(pm)


def test_smallest_route_validator_rejects_zero_nodes():
    """No drillable nodes is a malformed route (no first target)."""
    pm = _provisional_map_with_node_count(0)
    with pytest.raises(SmallestRouteCapExceeded):
        _validate_smallest_route(pm)


def test_smallest_route_validator_rejects_missing_learner_scaffold():
    pm = _provisional_map_with_node_count(1, include_learner_scaffold=False)

    with pytest.raises(SmallestRouteCapExceeded, match="learner_scaffold"):
        _validate_smallest_route(pm)


def test_smallest_route_validator_rejects_scaffold_that_copies_hidden_mechanism():
    scaffold = _learner_scaffold()
    scaffold.blank_hint = "Sodium channels open when membrane voltage reaches threshold."
    pm = ProvisionalMap(
        metadata={
            "source_title": "test",
            "core_thesis": "test thesis",
            "architecture_type": "causal_chain",
            "difficulty": "medium",
            "low_density": True,
        },
        backbone=[{"id": "b1", "principle": "Test backbone", "dependent_clusters": ["c1"]}],
        clusters=[
            Cluster(
                id="c1",
                label="Cluster 1",
                description="Test cluster 1",
                subnodes=[
                    Subnode(
                        id="c1_s1",
                        label="Node 1",
                        mechanism=(
                            "Sodium channels open when membrane voltage reaches threshold, "
                            "then sodium enters because the electrochemical gradient favors inward flow."
                        ),
                        learner_scaffold=scaffold,
                    ),
                ],
            )
        ],
        relationships=Relationships(),
        frameworks=[],
    )

    with pytest.raises(SmallestRouteCapExceeded, match="blank_hint.*copies hidden mechanism"):
        _validate_smallest_route(pm)


def test_smallest_route_validator_rejects_multiple_subnodes_per_cluster():
    pm = ProvisionalMap(
        metadata={
            "source_title": "test",
            "core_thesis": "test thesis",
            "architecture_type": "causal_chain",
            "difficulty": "medium",
            "low_density": True,
        },
        backbone=[{"id": "b1", "principle": "Test backbone", "dependent_clusters": ["c1"]}],
        clusters=[
            Cluster(
                id="c1",
                label="Cluster 1",
                description="Test cluster 1",
                subnodes=[
                    Subnode(
                        id="c1_s1",
                        label="Node 1",
                        mechanism="test mechanism",
                        learner_scaffold=_learner_scaffold(),
                    ),
                    Subnode(
                        id="c1_s2",
                        label="Node 2",
                        mechanism="test mechanism",
                        learner_scaffold=_learner_scaffold(),
                    ),
                ],
            )
        ],
        relationships=Relationships(),
        frameworks=[],
    )

    with pytest.raises(SmallestRouteCapExceeded, match="exactly one subnode"):
        _validate_smallest_route(pm)


def test_provisional_map_accepts_learner_scaffold_on_subnodes():
    """Source-less routes carry a non-revealing learner task contract per node."""
    node = Subnode(
        id="c1_s1",
        label="Starting model",
        mechanism="Hermes works by composing memory, skills, tools, routing, and deployment into one agent loop.",
        learner_scaffold={
            "bloom_level": "understand",
            "learner_move": "Say it",
            "task_label": "Starting model",
            "task_cue": "Put the system in your words.",
            "tailoring_anchor": "You mentioned a self-improving agent, so this starts by naming what parts are working together.",
            "entry_prompt": "How would you explain Hermes Agent to a classmate right now?",
            "expected_shape": "Write 1-2 sentences. Name what it does and one fuzzy part.",
            "sentence_starter": "My current guess is that Hermes Agent works by...",
            "blank_hint": "Pick one phrase from your sketch and say what role it plays.",
            "evidence_goal": "The learner states an initial model without reading source content.",
        },
    )

    graph = ProvisionalMap(
        metadata={
            "source_title": "Hermes Agent",
            "core_thesis": "Hermes Agent composes durable agent capabilities into one working system.",
            "architecture_type": "system_description",
            "difficulty": "medium",
            "low_density": True,
        },
        backbone=[{"id": "b1", "principle": "Starting model", "dependent_clusters": ["c1"]}],
        clusters=[
            Cluster(
                id="c1",
                label="Starting model",
                description="State the system in your own words.",
                subnodes=[node],
            )
        ],
        relationships=Relationships(),
        frameworks=[],
    )

    scaffold = graph.clusters[0].subnodes[0].learner_scaffold
    assert scaffold is not None
    assert scaffold.bloom_level == "understand"
    assert scaffold.learner_move == "Say it"
    assert scaffold.tailoring_anchor.startswith("You mentioned a self-improving agent")
    assert scaffold.entry_prompt.startswith("How would you explain")


def test_smallest_route_prompt_requires_internal_bloom_scaffold_contract():
    """The Ignition prompt must ask for task shape, not just vague labels."""
    prompt = (REPO_ROOT / "app_prompts/generate-smallest-route-system-v1.txt").read_text()

    for required in (
        "learner_scaffold",
        "bloom_level",
        "learner_move",
        "task_label",
        "task_cue",
        "tailoring_anchor",
        "entry_prompt",
        "expected_shape",
        "sentence_starter",
        "blank_hint",
        "evidence_goal",
    ):
        assert required in prompt

    assert "remember | understand | apply" in prompt
    assert "Do not use evaluate or create" in prompt
    assert "Do not show Bloom" in prompt
    assert "<learner_goal>" in prompt
    assert "not evidence" in prompt
    assert "Do not copy any contiguous clause from `mechanism`" in prompt
    assert "conceptual foothold" in prompt
    assert "not sentence-writing instructions" in prompt


# ---------------------------------------------------------------------------
# Task 3 — wiring tests for generate_smallest_provisional_map
# ---------------------------------------------------------------------------

from unittest.mock import MagicMock  # noqa: E402
from ai_service import generate_smallest_provisional_map  # noqa: E402


def test_generate_smallest_provisional_map_uses_new_prompt():
    """Verifies the new function loads the smallest-route prompt, not the
    existing sketch prompt, and routes the generated map through
    _validate_smallest_route."""
    fake_pm = _provisional_map_with_node_count(2)
    fake_result = MagicMock(parsed=fake_pm)

    captured = {}

    class FakeClient:
        def generate_structured(self, request):
            captured["system_prompt"] = request.system_prompt
            captured["user_prompt"] = request.user_prompt
            captured["task_name"] = request.task_name
            return fake_result

    out = generate_smallest_provisional_map(
        concept="Photosynthesis",
        threshold="plants take in light and somehow make sugar",
        learner_goal="I want to understand why leaves make sugar.",
        llm=FakeClient(),
    )

    assert out is fake_pm
    # New prompt is loaded, not the from-sketch one
    assert "smallest actionable route" in captured["system_prompt"].lower()
    assert "<learner_goal>I want to understand why leaves make sugar.</learner_goal>" in captured["user_prompt"]
    # Task name is distinct so telemetry can distinguish stages
    assert captured["task_name"] == "smallest_route_from_threshold"


def test_generate_smallest_provisional_map_rejects_oversized():
    """If the model returns a 5-node map, the wrapper raises."""
    oversized = _provisional_map_with_node_count(5)
    fake_result = MagicMock(parsed=oversized)

    class FakeClient:
        def generate_structured(self, request):
            return fake_result

    with pytest.raises(SmallestRouteCapExceeded):
        generate_smallest_provisional_map(
            concept="X",
            threshold="abc def ghi",
            llm=FakeClient(),
        )
