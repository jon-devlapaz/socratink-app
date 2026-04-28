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
