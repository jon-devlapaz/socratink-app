"""CLI golden tests for the local reconstruction-state loop."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CLI = REPO_ROOT / "scripts" / "cli-kernel-harness.mjs"
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "cli-kernel"
TEST_NODE_TIMEOUT_SECONDS = 30


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["node", str(CLI), *args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=TEST_NODE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        pytest.fail(
            f"CLI kernel harness timed out after {TEST_NODE_TIMEOUT_SECONDS}s",
            pytrace=False,
        )


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_cli_kernel_source_backed_flow_keeps_repair_and_gap_drill_graph_neutral() -> None:
    result = run_cli("--json", str(FIXTURES / "source_backed_repair_loop.json"))

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)

    assert payload["concept_id"] == "source-backed-action-potential"
    assert payload["source_mode"] == "source_attached"
    assert [step["event"] for step in payload["trace"]] == [
        "initial",
        "cold_attempt",
        "study_reveal",
        "repair",
        "gap_drill_noop",
        "spaced_redrill",
    ]
    assert [
        step["nodes"]["threshold-gating"]["state"]
        for step in payload["trace"]
    ] == [None, "needs repair", "needs repair", "needs repair", "needs repair", "primed"]
    assert [
        step["nodes"]["threshold-gating"]["next_action"]
        for step in payload["trace"]
    ] == ["cold_attempt", "study", "repair", "repair", "repair", "repair"]
    assert payload["trace"][3]["nodes"]["threshold-gating"]["attempt_count"] == 1
    assert payload["trace"][4]["nodes"]["threshold-gating"]["attempt_count"] == 1
    assert payload["trace"][-1]["concept_status"]["badge"] == "primed"
    assert payload["training"]["node_records"]["threshold-gating"]["repairs"][0]["text"].startswith(
        "Threshold opens"
    )


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_cli_kernel_source_less_flow_only_solidifies_after_spaced_strong_reconstruction() -> None:
    result = run_cli("--json", str(FIXTURES / "source_less_solidification_loop.json"))

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)

    assert payload["concept_id"] == "source-less-vaccine-memory"
    assert payload["source_mode"] == "source_less"
    assert payload["grounding"] == "learner_sketch"
    assert [
        step["nodes"]["immune-memory"]["state"]
        for step in payload["trace"]
    ] == [None, "primed", "primed", "primed", "primed", "solidified"]
    assert [
        step["nodes"]["immune-memory"]["next_action"]
        for step in payload["trace"]
    ] == ["cold_attempt", "study", "spaced_attempt", "spaced_attempt", "spaced_attempt", None]
    assert payload["trace"][3]["nodes"]["immune-memory"]["attempt_count"] == 1
    assert payload["trace"][4]["nodes"]["immune-memory"]["attempt_count"] == 1
    assert payload["trace"][-1]["concept_status"]["badge"] == "solidified"
    assert payload["training"]["sketch"]["text"].startswith("I think vaccines")


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_cli_kernel_tui_static_output_is_founder_facing_and_accepts_fixture_alias() -> None:
    result = run_cli("--tui-static", "source-less")

    assert result.returncode == 0, result.stderr
    assert "MODULE_TYPELESS_PACKAGE_JSON" not in result.stderr
    assert "Socratink Kernel TUI" in result.stdout
    assert "Concept: source-less-vaccine-memory" in result.stdout
    assert "Mode: source_less / learner_sketch" in result.stdout
    assert "Final badge: solidified" in result.stdout
    assert "Controls: up/down or j/k step through events, q quits" in result.stdout
    assert "> spaced_redrill" in result.stdout
    assert re.search(r"immune-memory\s+solidified\s+next none", result.stdout)
    assert "Attempts: 2  Repairs: 1" in result.stdout
    assert "Only spaced strong reconstruction produced solidified." in result.stdout
