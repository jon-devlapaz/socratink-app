# tests/pipette/test_subagent_stop_wiring.py
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

def test_stub_returns_allow():
    r = subprocess.run(
        [sys.executable, "-m", "tools.pipette.subagent_stop"],
        input='{"diff": "", "task_id": "stub"}',
        capture_output=True,
        text=True,
        cwd=REPO,
    )
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert out["permissionDecision"] == "allow"
