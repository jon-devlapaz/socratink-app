# tests/pipette/test_validate_pipeline_graph.py
import json
from pathlib import Path
from tools.pipette.validate_pipeline_graph import validate

def _write(tmp_path: Path, graph: dict) -> Path:
    p = tmp_path / "g.json"
    p.write_text(json.dumps(graph))
    return p

def test_valid_minimal_graph(tmp_path: Path):
    g = {
        "nodes": [{"id": "start", "type": "entry"}, {"id": "exit_clean", "type": "exit"}],
        "edges": [{"from": "start", "to": "exit_clean"}],
    }
    assert validate(_write(tmp_path, g)) == []

def test_orphan_node_fails(tmp_path: Path):
    g = {
        "nodes": [{"id": "start", "type": "entry"}, {"id": "orphan", "type": "task"}, {"id": "exit_clean", "type": "exit"}],
        "edges": [{"from": "start", "to": "exit_clean"}, {"from": "orphan", "to": "exit_clean"}],
    }
    errs = validate(_write(tmp_path, g))
    assert any("unreachable" in e and "orphan" in e for e in errs)

def test_dead_end_fails(tmp_path: Path):
    g = {
        "nodes": [{"id": "start", "type": "entry"}, {"id": "stuck", "type": "task"}],
        "edges": [{"from": "start", "to": "stuck"}],
    }
    errs = validate(_write(tmp_path, g))
    assert any("no outgoing edges" in e and "stuck" in e for e in errs)

def test_gate_missing_label_fails(tmp_path: Path):
    g = {
        "nodes": [
            {"id": "start", "type": "entry"},
            {"id": "g", "type": "automated_gate", "decision": "PASS|FAIL"},
            {"id": "exit_clean", "type": "exit"},
        ],
        "edges": [{"from": "start", "to": "g"}, {"from": "g", "to": "exit_clean", "label": "PASS"}],
    }
    errs = validate(_write(tmp_path, g))
    assert any("FAIL" in e for e in errs)

def test_real_pipette_graph_validates(tmp_path: Path):
    """Run the validator against the actual pipeline_graph.json shipped with this plan."""
    p = Path(__file__).resolve().parents[2] / "tools" / "pipette" / "pipeline_graph.json"
    if not p.exists():
        return  # B1.b hasn't been run yet
    assert validate(p) == []

def test_illegal_two_node_cycle_detected(tmp_path: Path):
    """Codex Phase-S regression: start -> a -> b -> a is a cycle that the
    iterative-DFS draft missed (BLACK-marking before child traversal).
    The recursive form must catch it."""
    g = {
        "nodes": [
            {"id": "start", "type": "entry"},
            {"id": "a", "type": "task"},
            {"id": "b", "type": "task"},
            {"id": "exit_clean", "type": "exit"},
        ],
        "edges": [
            {"from": "start", "to": "a"},
            {"from": "a", "to": "b"},
            {"from": "b", "to": "a"},      # illegal back-edge (not whitelisted)
            {"from": "a", "to": "exit_clean"},
        ],
    }
    errs = validate(_write(tmp_path, g))
    assert any("cycle" in e and "a" in e and "b" in e for e in errs)


def test_illegal_three_node_cycle_detected(tmp_path: Path):
    """Cycle through three nodes — also previously missed."""
    g = {
        "nodes": [
            {"id": "start", "type": "entry"},
            {"id": "a", "type": "task"},
            {"id": "b", "type": "task"},
            {"id": "c", "type": "task"},
            {"id": "exit_clean", "type": "exit"},
        ],
        "edges": [
            {"from": "start", "to": "a"},
            {"from": "a", "to": "b"},
            {"from": "b", "to": "c"},
            {"from": "c", "to": "a"},      # back-edge through 3 nodes
            {"from": "a", "to": "exit_clean"},
        ],
    }
    errs = validate(_write(tmp_path, g))
    assert any("cycle" in e for e in errs)


def test_whitelisted_loop_back_does_not_flag(tmp_path: Path):
    """Sanity check: legitimate loop-backs (gate_sanity → step_1_grill etc.)
    must NOT be flagged. The cycle filter is supposed to remove them."""
    # Use a gate_sanity loop-back that's in ALLOWED_LOOP_BACK_EDGES
    g = {
        "nodes": [
            {"id": "start", "type": "entry"},
            {"id": "step_1_grill", "type": "task"},
            {"id": "gate_sanity", "type": "automated_gate", "decision": "PASS|FAIL"},
            {"id": "exit_clean", "type": "exit"},
        ],
        "edges": [
            {"from": "start", "to": "step_1_grill"},
            {"from": "step_1_grill", "to": "gate_sanity"},
            {"from": "gate_sanity", "to": "step_1_grill", "label": "FAIL"},  # whitelisted
            {"from": "gate_sanity", "to": "exit_clean", "label": "PASS"},
        ],
    }
    errs = validate(_write(tmp_path, g))
    # No "cycle" error — the back-edge is whitelisted
    assert not any("cycle" in e for e in errs)
