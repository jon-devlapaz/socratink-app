"""CLI tests for tools.pipette.cli — added/extended in Chunks B (F4) and C (F3)."""
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
# Chunk B.3 — gemini_picker event shape regression (F9)
# ---------------------------------------------------------------------------

def test_gemini_picker_event_shape_preserved():
    """F9: a NAMING regression test (not a runtime shape test).

    Pins two facts about gemini_picker:
      1. The literal event name `"gemini_verdict"` still appears in source.
      2. `append_event` is actually called (not just imported), so the
         event-write path still routes through trace.append_event.

    What this does NOT verify: the runtime trace.jsonl record shape (keys,
    types). For that, an integration test would need to invoke gemini_picker
    with a mocked subprocess.run. This test's stated job is to catch
    rename/removal regressions only. Downstream readers (e.g., weekly
    aggregator) that depend on the {ts, step, event, decision, jump_back_to}
    shape need their own integration coverage."""
    import ast
    import inspect
    from tools.pipette import gemini_picker as gp
    src = inspect.getsource(gp)
    # 1. Event name is referenced verbatim somewhere in the module.
    assert '"gemini_verdict"' in src or "'gemini_verdict'" in src, \
        "gemini_picker no longer references the gemini_verdict event name"
    # 2. append_event is actually CALLED (not merely imported). Defends
    #    against a refactor that imports the symbol but routes writes
    #    elsewhere (raw json.dumps, a different helper, etc.).
    tree = ast.parse(src)
    called_names = {
        (n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", None))
        for n in ast.walk(tree) if isinstance(n, ast.Call)
    }
    assert "append_event" in called_names, \
        "gemini_picker must call append_event (not just import it) to keep the event-write path consistent with `pipette trace-append --data`"


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
