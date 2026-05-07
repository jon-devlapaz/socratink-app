"""Tests for the ≤4-node cap on source-less generation per C-prime spec §5.1."""
from __future__ import annotations

import pytest

from ai_service import _validate_smallest_route, SmallestRouteCapExceeded
from models.provisional_map import (
    BackboneItem,
    Cluster,
    Metadata,
    ProvisionalMap,
    Relationships,
    Subnode,
)


def _provisional_map_with_node_count(n: int) -> ProvisionalMap:
    """Build a ProvisionalMap with `n` drillable cluster nodes for the cap test.

    Each cluster has one subnode (satisfying the drillability rule).
    The backbone covers all clusters. Relationships and frameworks are empty.
    """
    clusters = [
        Cluster(
            id=f"c{i + 1}",
            label=f"Cluster {i + 1}",
            description=f"Test cluster {i + 1}",
            subnodes=[
                Subnode(
                    id=f"c{i + 1}_s1",
                    label=f"Node {i + 1}",
                    mechanism="test mechanism",
                )
            ],
        )
        for i in range(n)
    ]

    if n == 0:
        # An empty cluster list would fail the backbone coverage rule, so we
        # short-circuit: build a ProvisionalMap that has no clusters by
        # bypassing normal model validation. We use object.__setattr__ to
        # inject the empty list after construction of a 1-node map, then
        # replace it — but that would mutate a frozen model.
        #
        # Instead: use model_construct to skip validators entirely so we can
        # produce a deliberately malformed object that _validate_smallest_route
        # must catch.
        return ProvisionalMap.model_construct(
            metadata=Metadata(
                source_title="test",
                core_thesis="test thesis",
                architecture_type="causal_chain",
                difficulty="medium",
            ),
            backbone=[],
            clusters=[],
            relationships=Relationships(),
            frameworks=[],
        )

    backbone = [
        BackboneItem(
            id="b1",
            principle="Test backbone",
            dependent_clusters=[f"c{i + 1}" for i in range(n)],
        )
    ]

    return ProvisionalMap(
        metadata=Metadata(
            source_title="test",
            core_thesis="test thesis",
            architecture_type="causal_chain",
            difficulty="medium",
        ),
        backbone=backbone,
        clusters=clusters,
        relationships=Relationships(),
        frameworks=[],
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


# ---------------------------------------------------------------------------
# Task 3 — wiring tests for generate_smallest_provisional_map
# ---------------------------------------------------------------------------

from unittest.mock import MagicMock, patch  # noqa: E402
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
            captured["task_name"] = request.task_name
            return fake_result

    out = generate_smallest_provisional_map(
        concept="Photosynthesis",
        threshold="plants take in light and somehow make sugar",
        llm=FakeClient(),
    )

    assert out is fake_pm
    # New prompt is loaded, not the from-sketch one
    assert "smallest actionable route" in captured["system_prompt"].lower()
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
