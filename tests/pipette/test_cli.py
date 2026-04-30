"""CLI tests for tools.pipette.cli — extended in Chunk C (F3)."""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

import pytest

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


def test_build_coverage_map_warns_on_malformed_dump(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    """F3: when the dump's edges have NO `from.source_file` starting with
    'tests/', every affected file gets the uncovered default. That's a
    silent failure mode that triggered TDD enforcement spuriously in the
    2026-04-28 run. Emit a stderr warning when the shape looks wrong."""
    from tools.pipette.cli import main

    bad_dump = tmp_path / "bad.json"
    # Absolute paths, no 'tests/' prefix — the symptom from F3.
    bad_dump.write_text(json.dumps({
        "edges": [
            {"from": {"source_file": "/abs/path/foo.py"},
             "to": {"source_file": "/abs/path/bar.py"}}
        ]
    }))
    out_path = tmp_path / "coverage_map.json"
    rc = main([
        "build-coverage-map",
        "--dump-file", str(bad_dump),
        "--affected-files", "src/foo.py",
        "--output", str(out_path),
    ])
    assert rc == 0  # warning, not error
    err = capsys.readouterr().err
    assert "warning" in err.lower()
    assert "malformed" in err.lower() or "no test→source edges" in err.lower()
