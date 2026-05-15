import pytest

from models.knowledge_map_context import (
    knowledge_map_has_node,
    prune_context,
    resolve_target_cluster_id,
    validate_knowledge_map,
)


def sample_map() -> dict:
    return {
        "metadata": {
            "core_thesis": "The thermostat closes a feedback loop.",
            "governing_assumptions": ["Room temperature can be measured."],
            "starting_map_context": "Thermostat control",
        },
        "backbone": [
            {
                "id": "b1",
                "principle": "Feedback depends on comparing actual and desired state.",
                "dependent_clusters": ["c1"],
            }
        ],
        "clusters": [
            {
                "id": "c1",
                "label": "Setpoint comparison",
                "description": "How the loop decides whether heat is needed.",
                "subnodes": [
                    {
                        "id": "c1_s1",
                        "label": "Below setpoint",
                        "mechanism": "A gap between current and desired temperature turns heat on.",
                    }
                ],
            },
            {
                "id": "c2",
                "label": "Unused shell",
                "description": "A cluster outside the target context.",
                "subnodes": [],
            },
        ],
        "relationships": {
            "learning_prerequisites": [
                {"from": "c1", "to": "c2"},
                {"from": "c2", "to": "c3"},
            ],
            "domain_mechanics": [{"from": "c1_s1", "to": "c2"}],
        },
        "frameworks": [
            {"name": "feedback", "source_clusters": ["c1"]},
            {"name": "other", "source_clusters": ["c2"]},
        ],
    }


@pytest.mark.parametrize(
    ("knowledge_map", "message"),
    [
        (None, "knowledge_map must be an object."),
        ({"metadata": None, "backbone": [], "clusters": []}, "knowledge_map.metadata"),
        ({"metadata": {}, "backbone": None, "clusters": []}, "knowledge_map.backbone"),
        ({"metadata": {}, "backbone": [], "clusters": None}, "knowledge_map.clusters"),
        (
            {"metadata": {}, "backbone": [], "clusters": [], "relationships": []},
            "knowledge_map.relationships",
        ),
        (
            {"metadata": {}, "backbone": [], "clusters": [], "frameworks": {}},
            "knowledge_map.frameworks",
        ),
    ],
)
def test_validate_knowledge_map_rejects_malformed_wire_shape(
    knowledge_map: dict, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        validate_knowledge_map(knowledge_map)


def test_validate_knowledge_map_accepts_minimal_wire_shape() -> None:
    validate_knowledge_map({"metadata": {}, "backbone": [], "clusters": []})


def test_validate_knowledge_map_accepts_empty_optional_sections() -> None:
    validate_knowledge_map(
        {
            "metadata": {},
            "backbone": [],
            "clusters": [],
            "relationships": {},
            "frameworks": [],
        }
    )


@pytest.mark.parametrize(
    ("node_id", "expected"),
    [
        ("core-thesis", True),
        ("b1", True),
        ("c1", True),
        ("c1_s1", True),
        ("missing", False),
    ],
)
def test_knowledge_map_has_node_checks_backbone_clusters_and_subnodes(
    node_id: str, expected: bool
) -> None:
    knowledge_map = sample_map()
    knowledge_map["clusters"].append("not-a-cluster")

    assert knowledge_map_has_node(knowledge_map, node_id) is expected


@pytest.mark.parametrize(
    ("target_node_id", "expected"),
    [
        ("c1", "c1"),
        ("c1_s1", "c1"),
        ("missing", None),
    ],
)
def test_resolve_target_cluster_id(target_node_id: str, expected: str | None) -> None:
    assert resolve_target_cluster_id(sample_map(), target_node_id) == expected


def test_resolve_target_cluster_id_skips_malformed_clusters_and_accepts_exact_id() -> None:
    knowledge_map = sample_map()
    knowledge_map["clusters"] = [
        "not-a-cluster",
        {"id": "custom_s_cluster", "subnodes": []},
    ]

    assert (
        resolve_target_cluster_id(knowledge_map, "custom_s_cluster")
        == "custom_s_cluster"
    )


def test_prune_context_for_backbone_target_keeps_dependent_cluster_shells() -> None:
    pruned = prune_context(sample_map(), "b1")

    assert pruned["metadata"] == {
        "thesis": "The thermostat closes a feedback loop.",
        "governing_assumptions": ["Room temperature can be measured."],
        "starting_map_context": "Thermostat control",
    }
    assert pruned["backbone"][0]["id"] == "b1"
    assert pruned["clusters"] == [
        {
            "id": "c1",
            "label": "Setpoint comparison",
            "description": "How the loop decides whether heat is needed.",
        }
    ]
    assert pruned["relationships"] == sample_map()["relationships"]
    assert pruned["frameworks"] == sample_map()["frameworks"]


def test_prune_context_for_core_thesis_with_malformed_backbone_falls_back() -> None:
    knowledge_map = sample_map()
    knowledge_map["backbone"] = ["not-a-backbone-item"]

    pruned = prune_context(knowledge_map, "core-thesis")

    assert pruned["backbone"] == ["not-a-backbone-item"]
    assert pruned["clusters"] == []


def test_prune_context_for_subnode_keeps_target_cluster_edges_and_frameworks() -> None:
    pruned = prune_context(sample_map(), "c1_s1")

    assert [cluster["id"] for cluster in pruned["clusters"]] == ["c1"]
    assert [item["id"] for item in pruned["backbone"]] == ["b1"]
    assert pruned["relationships"] == {
        "learning_prerequisites": [{"from": "c1", "to": "c2"}]
    }
    assert pruned["frameworks"] == [{"name": "feedback", "source_clusters": ["c1"]}]


def test_prune_context_for_missing_target_returns_empty_target_context() -> None:
    pruned = prune_context(sample_map(), "missing")

    assert pruned["clusters"] == []
    assert pruned["backbone"] == []
    assert pruned["relationships"] == {"learning_prerequisites": []}
    assert pruned["frameworks"] == []
