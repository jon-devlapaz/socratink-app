import json
from pathlib import Path
from tools.pipette.trace import append_event, Event

def test_append_writes_one_line_per_event(tmp_path: Path):
    p = tmp_path / "trace.jsonl"
    append_event(p, Event(step=0, event="started"))
    append_event(p, Event(step=0, event="finished"))
    lines = p.read_text().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["event"] == "started"

def test_event_includes_required_fields(tmp_path: Path):
    p = tmp_path / "trace.jsonl"
    append_event(p, Event(step=3, event="gate", decision="FAIL", jump_back_to=1))
    rec = json.loads(p.read_text().splitlines()[0])
    assert "ts" in rec and rec["ts"].endswith("Z")
    assert rec["step"] == 3
    assert rec["decision"] == "FAIL"
    assert rec["jump_back_to"] == 1

def test_extra_fields_round_trip(tmp_path: Path):
    p = tmp_path / "trace.jsonl"
    append_event(p, Event(step=5, event="hook", extra={"tokens": 12340, "latency_ms": 8200}))
    rec = json.loads(p.read_text().splitlines()[0])
    assert rec["tokens"] == 12340
    assert rec["latency_ms"] == 8200

def test_append_creates_parent_dir_if_missing(tmp_path: Path):
    p = tmp_path / "deep" / "nested" / "trace.jsonl"
    append_event(p, Event(step=0, event="x"))
    assert p.exists()
