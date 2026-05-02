"""Coverage map generation from graph dump."""
from __future__ import annotations
import json
import sys
from pathlib import Path

def build_coverage_map(dump_file: Path, affected_files: list[str], output_file: Path) -> int:
    dump = json.loads(dump_file.read_text())
    
    # The dump is whatever the orchestrator pipes from MCP query_graph. We
    # accept either a list of edges [{"from": {"source_file": "tests/foo.py"}, "to": {"source_file": "src/foo.py"}}, ...]
    # OR a flat list of nodes with a `tested_files` field. Support both.
    edges = dump.get("edges") if isinstance(dump, dict) else dump
    tested_files: set[str] = set()
    edges_with_tests_prefix = 0
    if isinstance(edges, list):
        for e in edges:
            src = (e.get("from") or {}).get("source_file") if isinstance(e, dict) else None
            dst = (e.get("to") or {}).get("source_file") if isinstance(e, dict) else None
            if src and dst and src.startswith("tests/"):
                tested_files.add(dst)
                edges_with_tests_prefix += 1

    # F3: shape validation. The coverage map is silently wrong when
    # the dump's edges lack `tests/`-prefixed source_files. Two warning
    # tiers:
    #   (1) all-or-nothing — len > 0 and zero tests-prefixed → almost
    #       certainly malformed (the 2026-04-28 silent-failure shape).
    #   (2) majority-non-test — len >= 5 and ratio < 50% → likely
    #       partial corruption (e.g., dump producer mid-refactor).
    # Both warn loudly to stderr; rc unchanged (warning, not error).
    if isinstance(edges, list) and len(edges) > 0:
        ratio = edges_with_tests_prefix / len(edges)
        if edges_with_tests_prefix == 0:
            print(
                "pipette: warning — coverage dump appears malformed "
                "(no test→source edges with `from.source_file` starting with 'tests/'); "
                "coverage map will be all-uncovered. "
                "Verify dump shape: {edges:[{from:{source_file:'tests/...'}, to:{source_file:'...'}}]}",
                file=sys.stderr,
            )
        elif len(edges) >= 5 and ratio < 0.5:
            print(
                f"pipette: warning — coverage dump appears partially malformed "
                f"(only {edges_with_tests_prefix}/{len(edges)} edges = "
                f"{ratio:.0%} have `from.source_file` starting with 'tests/'); "
                f"the coverage map for non-tests/-prefixed source files will be all-uncovered. "
                f"Verify dump shape: {{edges:[{{from:{{source_file:'tests/...'}}, to:{{source_file:'...'}}}}]}}",
                file=sys.stderr,
            )

    files_map = {f: (0.85 if f in tested_files else 0.30) for f in affected_files}
    out = {"_method": "graph_approx_v1", "files": files_map}
    output_file.write_text(json.dumps(out, indent=2))
    return 0
