"""Shared test helpers for constructing ProvisionalMap fixtures.

Promoted out of tests/test_generate_smallest_route.py so other test modules
can import without depending on cross-test discovery order.
"""
from __future__ import annotations

from models.provisional_map import (
    BackboneItem,
    Cluster,
    Metadata,
    ProvisionalMap,
    Relationships,
    Subnode,
)


def provisional_map_with_node_count(n: int) -> ProvisionalMap:
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
