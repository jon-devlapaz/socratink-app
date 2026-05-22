"""Shared test helpers for constructing ProvisionalMap fixtures.

Promoted out of tests/test_generate_smallest_route.py so other test modules
can import without depending on cross-test discovery order.
"""
from __future__ import annotations

from models.provisional_map import (
    BackboneItem,
    Cluster,
    LearnerScaffold,
    Metadata,
    ProvisionalMap,
    Relationships,
    Subnode,
)


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


def provisional_map_with_node_count(n: int, *, include_learner_scaffold: bool = True) -> ProvisionalMap:
    """Build a ProvisionalMap with `n` drillable cluster nodes for the cap test.

    n must be >= 0. Raises ValueError for negative values.
    Each cluster has one subnode (satisfying the drillability rule).
    The backbone covers all clusters. Relationships and frameworks are empty.
    """
    if n < 0:
        raise ValueError(f"n must be >= 0, got {n}")
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
                    learner_scaffold=_learner_scaffold() if include_learner_scaffold else None,
                )
            ],
        )
        for i in range(n)
    ]

    if n == 0:
        # An empty cluster list would fail the backbone coverage rule, so we
        # short-circuit via model_construct to skip validators entirely and
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
