from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
TEST_NODE_TIMEOUT_SECONDS = 30


def run_node_module(script: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["node", "--input-type=module", "-e", script],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=TEST_NODE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        pytest.fail(
            f"Node helper module test timed out after {TEST_NODE_TIMEOUT_SECONDS}s",
            pytrace=False,
        )
