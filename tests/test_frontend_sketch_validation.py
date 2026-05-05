"""JS parity test for is_substantive_sketch.

Loads the shared fixture (used by both Python tests and this JS harness),
shells out to a small node runner, and asserts byte-for-byte verdict parity.
A divergence is a release-blocker per spec §5.3 / handoff §2.

Skipped when `node` is unavailable (mirrors tests/test_frontend_syntax.py).
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "sketch_validation_parity.json"
RUNNER = REPO_ROOT / "tests" / "_helpers" / "run_sketch_parity.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_js_sketch_validation_matches_python_for_every_fixture_entry() -> None:
    assert FIXTURE.exists(), f"fixture missing: {FIXTURE}"
    assert RUNNER.exists(), f"node runner missing: {RUNNER}"

    result = subprocess.run(
        ["node", str(RUNNER)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (
        f"node runner failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )

    rows = json.loads(result.stdout)
    assert isinstance(rows, list) and rows, "runner produced no rows"

    mismatches = [r for r in rows if r["expected"] != r["actual"]]
    if mismatches:
        msg = "\n".join(
            f"  idx={r['idx']} text={r['text']!r} expected={r['expected']} actual={r['actual']}"
            for r in mismatches
        )
        pytest.fail(
            f"JS sketch_validation diverges from Python on {len(mismatches)}/{len(rows)} entries:\n{msg}"
        )
