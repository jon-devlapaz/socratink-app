"""CLI tests for tools.pipette.cli — added in Chunk B (F4) and extended in C (F3) and G (F14)."""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Chunk B.1 — parse_extra_kv helper (F4)
# ---------------------------------------------------------------------------

def test_parse_extra_kv_simple():
    from tools.pipette.trace import parse_extra_kv
    assert parse_extra_kv("jump_back_to=1") == {"jump_back_to": "1"}


def test_parse_extra_kv_multi():
    from tools.pipette.trace import parse_extra_kv
    assert parse_extra_kv("jump_back_to=1,reason=verdict_fail") == {
        "jump_back_to": "1",
        "reason": "verdict_fail",
    }


def test_parse_extra_kv_empty_returns_empty_dict():
    from tools.pipette.trace import parse_extra_kv
    assert parse_extra_kv("") == {}
    assert parse_extra_kv(None) == {}


def test_parse_extra_kv_rejects_no_equals():
    from tools.pipette.trace import parse_extra_kv
    with pytest.raises(ValueError, match="expected key=value"):
        parse_extra_kv("just_a_key")


# ---------------------------------------------------------------------------
# Chunk B.2 — trace-append --data wiring (F4)
# ---------------------------------------------------------------------------

def test_trace_append_writes_structured_data(tmp_path: Path):
    """trace-append --data k=v writes the keys into trace.jsonl."""
    from tools.pipette.cli import main
    folder = tmp_path / "feature-x"
    folder.mkdir()
    rc = main([
        "trace-append",
        "--folder", str(folder),
        "--step", "3",
        "--event", "verdict_fail",
        "--data", "jump_back_to=1,reason=contracts_critical",
    ])
    assert rc == 0
    line = (folder / "trace.jsonl").read_text().strip()
    rec = json.loads(line)
    assert rec["event"] == "verdict_fail"
    assert rec["jump_back_to"] == "1"
    assert rec["reason"] == "contracts_critical"


def test_trace_append_rejects_malformed_data(tmp_path: Path):
    from tools.pipette.cli import main
    folder = tmp_path / "feature-x"
    folder.mkdir()
    rc = main([
        "trace-append",
        "--folder", str(folder),
        "--step", "3",
        "--event", "x",
        "--data", "no_equals_here",
    ])
    assert rc != 0


# ---------------------------------------------------------------------------
# Pre-existing subprocess-style tests
# ---------------------------------------------------------------------------

def _run(*args, cwd=None, input=None):
    return subprocess.run(
        [sys.executable, "-m", "tools.pipette", *args],
        capture_output=True, text=True, cwd=cwd, input=input,
    )

def test_no_args_prints_usage():
    r = _run()
    assert r.returncode == 0
    assert "Usage:" in r.stdout or "usage:" in r.stdout

def test_unknown_subcommand_exits_2():
    r = _run("does-not-exist")
    assert r.returncode == 2

def test_doctor_subcommand_exists():
    r = _run("doctor", "--help")
    assert r.returncode == 0
    assert "preflight" in r.stdout.lower()

def test_start_subcommand_requires_topic():
    r = _run("start")
    assert r.returncode == 2  # argparse error

def test_build_coverage_map_no_tested_files(tmp_path: Path):
    """Affected file with no test edges → coverage 0.30."""
    import json
    dump = tmp_path / "dump.json"
    dump.write_text(json.dumps({"edges": []}))
    out = tmp_path / "coverage.json"
    r = _run("build-coverage-map", "--dump-file", str(dump),
             "--affected-files", "src/foo.py",
             "--output", str(out))
    assert r.returncode == 0, r.stderr
    cov = json.loads(out.read_text())
    assert cov["_method"] == "graph_approx_v1"
    assert cov["files"]["src/foo.py"] == 0.30

def test_build_coverage_map_tested_files(tmp_path: Path):
    """Affected file with a test edge from tests/* → coverage 0.85."""
    import json
    dump = tmp_path / "dump.json"
    dump.write_text(json.dumps({"edges": [
        {"from": {"source_file": "tests/test_foo.py"}, "to": {"source_file": "src/foo.py"}},
    ]}))
    out = tmp_path / "coverage.json"
    r = _run("build-coverage-map", "--dump-file", str(dump),
             "--affected-files", "src/foo.py", "src/bar.py",
             "--output", str(out))
    assert r.returncode == 0, r.stderr
    cov = json.loads(out.read_text())
    assert cov["files"]["src/foo.py"] == 0.85
    assert cov["files"]["src/bar.py"] == 0.30

def test_build_coverage_map_ignores_non_test_edges(tmp_path: Path):
    """Edges from non-tests/ files don't count as coverage."""
    import json
    dump = tmp_path / "dump.json"
    dump.write_text(json.dumps({"edges": [
        {"from": {"source_file": "src/utils.py"}, "to": {"source_file": "src/foo.py"}},
    ]}))
    out = tmp_path / "coverage.json"
    r = _run("build-coverage-map", "--dump-file", str(dump),
             "--affected-files", "src/foo.py",
             "--output", str(out))
    assert r.returncode == 0
    cov = json.loads(out.read_text())
    assert cov["files"]["src/foo.py"] == 0.30
