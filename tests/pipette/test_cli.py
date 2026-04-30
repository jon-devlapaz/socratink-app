import subprocess
import sys
from pathlib import Path

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


def test_step3_heuristic_check_cli_returns_json_decision(tmp_path: Path):
    """F15 CLI: step3-heuristic-check prints a JSON decision and exits 0."""
    import json
    folder = tmp_path / "feature-x"
    folder.mkdir()
    # Write coverage_map.json and 01-grill.md so all thresholds pass.
    (folder / "coverage_map.json").write_text(
        json.dumps({"_method": "graph_approx_v1", "files": {"src/foo.py": 0.95}})
    )
    (folder / "01-grill.md").write_text(
        "# Grill\n\n<!-- pipette-meta total_changed_lines=10 max_risk_score=0.10 -->\n"
    )
    r = _run("step3-heuristic-check", "--folder", str(folder))
    assert r.returncode == 0, r.stderr
    decision = json.loads(r.stdout.strip())
    assert decision["auto_pass"] is True
    assert decision["reason"] == "heuristic_auto_pass"
