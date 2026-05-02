import pytest

from models.identifiers import (
    BackboneId,
    ClusterId,
    SubnodeId,
    parse_id,
    IdKind,
    CORE_THESIS,
)


def test_core_thesis_is_a_known_id():
    kind, parsed = parse_id("core-thesis")
    assert kind is IdKind.CORE_THESIS
    assert parsed == "core-thesis"


@pytest.mark.parametrize("good_id", ["b1", "b2", "b10", "b99"])
def test_backbone_ids_parse(good_id):
    kind, parsed = parse_id(good_id)
    assert kind is IdKind.BACKBONE
    assert isinstance(parsed, BackboneId)
    assert str(parsed) == good_id


@pytest.mark.parametrize("good_id", ["c1", "c2", "c10", "c99"])
def test_cluster_ids_parse(good_id):
    kind, parsed = parse_id(good_id)
    assert kind is IdKind.CLUSTER
    assert isinstance(parsed, ClusterId)
    assert str(parsed) == good_id


@pytest.mark.parametrize("good_id", ["c1_s1", "c2_s5", "c10_s12"])
def test_subnode_ids_parse(good_id):
    kind, parsed = parse_id(good_id)
    assert kind is IdKind.SUBNODE
    assert isinstance(parsed, SubnodeId)
    assert parsed.cluster_id == good_id.split("_")[0]
    assert str(parsed) == good_id


@pytest.mark.parametrize(
    "bad_id",
    ["", "x1", "B1", "b", "c", "c1_s", "c1_s_1", "c-1", "1", "core_thesis", "framework_1"],
)
def test_invalid_ids_raise(bad_id):
    with pytest.raises(ValueError):
        parse_id(bad_id)


def test_core_thesis_constant():
    assert CORE_THESIS == "core-thesis"


# ---------------------------------------------------------------------------
# ProvisionalMap shape — Task 8.2
# ---------------------------------------------------------------------------

from models.provisional_map import ProvisionalMap


VALID_MAP = {
    "metadata": {
        "source_title": "Entropy in closed systems",
        "core_thesis": "Entropy increases in closed systems.",
        "architecture_type": "system_description",
        "difficulty": "medium",
        "governing_assumptions": ["The system is closed."],
        "low_density": False,
    },
    "backbone": [
        {
            "id": "b1",
            "principle": "Disorder grows over time in isolated systems.",
            "dependent_clusters": ["c1"],
        }
    ],
    "clusters": [
        {
            "id": "c1",
            "label": "Microstate counting drives entropy",
            "description": "Each macrostate corresponds to many microstates; entropy reflects that count.",
            "subnodes": [
                {
                    "id": "c1_s1",
                    "label": "Boltzmann distribution",
                    "mechanism": "Probability of a microstate is weighted by its energy.",
                    "drill_status": None,
                    "gap_type": None,
                    "gap_description": None,
                    "last_drilled": None,
                }
            ],
        }
    ],
    "relationships": {
        "domain_mechanics": [],
        "learning_prerequisites": [],
    },
    "frameworks": [],
}


def test_provisional_map_parses_valid_input():
    m = ProvisionalMap.model_validate(VALID_MAP)
    assert m.metadata.core_thesis.startswith("Entropy")
    assert len(m.backbone) == 1
    assert len(m.clusters) == 1
    assert len(m.clusters[0].subnodes) == 1
    assert m.frameworks == []


def test_provisional_map_rejects_bad_id():
    bad = {
        **VALID_MAP,
        "backbone": [{"id": "X1", "principle": "x", "dependent_clusters": ["c1"]}],
    }
    with pytest.raises(ValueError):
        ProvisionalMap.model_validate(bad)


def test_provisional_map_rejects_missing_metadata():
    bad = {k: v for k, v in VALID_MAP.items() if k != "metadata"}
    with pytest.raises(ValueError):
        ProvisionalMap.model_validate(bad)


def test_provisional_map_tolerates_unknown_field_for_gemini_compat():
    """Unknown fields must NOT raise — Gemini rejects extra='forbid' schemas
    (additionalProperties: false in JSON Schema). Field-level correctness is
    governed by the prompt + closure validators, not by extra='forbid'.
    See ai_service.py:_parse_repair_reps_response for precedent.
    """
    permissive = {**VALID_MAP, "unexpected_top_level": "ignored"}
    m = ProvisionalMap.model_validate(permissive)
    assert m.metadata.core_thesis == "Entropy increases in closed systems."


# ---------------------------------------------------------------------------
# Closure-violation tests — Task 8.3
# ---------------------------------------------------------------------------


def _two_cluster_map():
    """Returns a deep-copied valid two-cluster map for closure-violation tests."""
    import copy
    return copy.deepcopy(
        {
            "metadata": VALID_MAP["metadata"],
            "backbone": [
                {"id": "b1", "principle": "x", "dependent_clusters": ["c1", "c2"]}
            ],
            "clusters": [
                {
                    "id": "c1",
                    "label": "x",
                    "description": "x",
                    "subnodes": [
                        {
                            "id": "c1_s1",
                            "label": "x",
                            "mechanism": "x",
                            "drill_status": None,
                            "gap_type": None,
                            "gap_description": None,
                            "last_drilled": None,
                        }
                    ],
                },
                {
                    "id": "c2",
                    "label": "y",
                    "description": "y",
                    "subnodes": [
                        {
                            "id": "c2_s1",
                            "label": "y",
                            "mechanism": "y",
                            "drill_status": None,
                            "gap_type": None,
                            "gap_description": None,
                            "last_drilled": None,
                        }
                    ],
                },
            ],
            "relationships": {"domain_mechanics": [], "learning_prerequisites": []},
            "frameworks": [],
        }
    )


def test_subnode_in_wrong_cluster_rejected():
    bad = _two_cluster_map()
    # Move c1_s1 into c2 — it does not belong there.
    bad["clusters"][0]["subnodes"] = []  # c1 needs at least 1 subnode → must keep one
    bad["clusters"][1]["subnodes"].append(
        {
            "id": "c1_s2",  # subnode of c1, but inside c2
            "label": "x",
            "mechanism": "x",
            "drill_status": None,
            "gap_type": None,
            "gap_description": None,
            "last_drilled": None,
        }
    )
    # Restore c1's subnode to satisfy the drillability rule
    bad["clusters"][0]["subnodes"] = [
        {
            "id": "c1_s1",
            "label": "x",
            "mechanism": "x",
            "drill_status": None,
            "gap_type": None,
            "gap_description": None,
            "last_drilled": None,
        }
    ]
    with pytest.raises(ValueError, match="does not belong to cluster"):
        ProvisionalMap.model_validate(bad)


def test_backbone_pointing_at_unknown_cluster_rejected():
    bad = _two_cluster_map()
    bad["backbone"][0]["dependent_clusters"] = ["c1", "c9"]  # c9 unknown
    with pytest.raises(ValueError, match="unknown dependent_cluster"):
        ProvisionalMap.model_validate(bad)


def test_orphan_cluster_rejected():
    bad = _two_cluster_map()
    bad["backbone"][0]["dependent_clusters"] = ["c1"]  # c2 now uncovered
    with pytest.raises(ValueError, match="not covered by any backbone"):
        ProvisionalMap.model_validate(bad)


def test_cluster_without_subnode_rejected():
    bad = _two_cluster_map()
    bad["clusters"][0]["subnodes"] = []  # empty cluster
    with pytest.raises(ValueError, match="must contain at least one subnode"):
        ProvisionalMap.model_validate(bad)


def test_learning_prerequisite_self_loop_rejected():
    bad = _two_cluster_map()
    bad["relationships"]["learning_prerequisites"] = [
        {"from": "c1", "to": "c1", "rationale": "x"}
    ]
    with pytest.raises(ValueError, match="self-loop"):
        ProvisionalMap.model_validate(bad)


def test_learning_prerequisite_reciprocal_rejected():
    bad = _two_cluster_map()
    bad["relationships"]["learning_prerequisites"] = [
        {"from": "c1", "to": "c2", "rationale": "x"},
        {"from": "c2", "to": "c1", "rationale": "y"},
    ]
    with pytest.raises(ValueError, match="reciprocal"):
        ProvisionalMap.model_validate(bad)


def test_learning_prerequisite_cycle_rejected():
    """A 3-node cycle: c1 -> c2 -> c3 -> c1."""
    bad = _two_cluster_map()
    bad["clusters"].append(
        {
            "id": "c3",
            "label": "z",
            "description": "z",
            "subnodes": [
                {
                    "id": "c3_s1",
                    "label": "z",
                    "mechanism": "z",
                    "drill_status": None,
                    "gap_type": None,
                    "gap_description": None,
                    "last_drilled": None,
                }
            ],
        }
    )
    bad["backbone"][0]["dependent_clusters"] = ["c1", "c2", "c3"]
    bad["relationships"]["learning_prerequisites"] = [
        {"from": "c1", "to": "c2", "rationale": "x"},
        {"from": "c2", "to": "c3", "rationale": "y"},
        {"from": "c3", "to": "c1", "rationale": "z"},
    ]
    with pytest.raises(ValueError, match="cycle"):
        ProvisionalMap.model_validate(bad)


def test_framework_source_clusters_must_exist():
    bad = _two_cluster_map()
    bad["frameworks"] = [
        {
            "id": "f1",
            "name": "Test framework",
            "statement": "x",
            "source_clusters": ["c9"],  # unknown
            "external_application": "x",
        }
    ]
    with pytest.raises(ValueError, match="references unknown cluster"):
        ProvisionalMap.model_validate(bad)


def test_duplicate_cluster_ids_rejected():
    bad = _two_cluster_map()
    # Duplicate the first cluster wholesale — same id, same subnodes — so the
    # cluster-level validators all pass and only the top-level duplicate-id
    # check is left to fire.
    bad["clusters"][1] = {**bad["clusters"][0]}
    with pytest.raises(ValueError, match="duplicate cluster ids"):
        ProvisionalMap.model_validate(bad)
