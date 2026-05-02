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
