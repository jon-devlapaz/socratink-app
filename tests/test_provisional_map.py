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
