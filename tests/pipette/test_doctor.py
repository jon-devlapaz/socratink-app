# tests/pipette/test_doctor.py
"""Unit tests for tools.pipette.doctor — added in Chunk C (F1)."""
from __future__ import annotations

import pytest

from tools.pipette.doctor import Check, run_checks


def test_check_passes_when_command_succeeds():
    c = Check(name="x", verify=lambda: (True, ""), fix="run x")
    results = run_checks([c])
    assert all(r.ok for r in results)

def test_check_fails_with_fix_instruction():
    c = Check(name="x", verify=lambda: (False, "missing"), fix="brew install x")
    results = run_checks([c])
    assert not results[0].ok
    assert results[0].fix == "brew install x"

def test_doctor_aggregate_returns_zero_on_all_pass():
    from tools.pipette.doctor import _aggregate_rc
    assert _aggregate_rc([]) == 0

def test_doctor_aggregate_returns_one_on_any_fail():
    from tools.pipette.doctor import CheckResult, _aggregate_rc
    assert _aggregate_rc([CheckResult(name="a", ok=True), CheckResult(name="b", ok=False, message="x", fix="y")]) == 1


def test_mcp_probe_warns_when_tools_absent_in_session(monkeypatch):
    """F1: when MCP is configured but the running session doesn't expose
    the mcp__code-review-graph__* tools, doctor must return WARN, not OK."""
    from tools.pipette import doctor

    # Simulate: MCP configured per settings.local.json (the CLI+settings part
    # of the existing check passes), but no in-session tools exposed.
    monkeypatch.setattr(doctor, "_session_exposes_mcp_tools",
                        lambda prefix: False, raising=False)
    ok, msg = doctor._verify_code_review_graph_session_probe()
    assert ok is False
    assert "tools not exposed" in msg


def test_mcp_probe_ok_when_tools_present_in_session(monkeypatch):
    from tools.pipette import doctor
    monkeypatch.setattr(doctor, "_session_exposes_mcp_tools",
                        lambda prefix: True, raising=False)
    ok, msg = doctor._verify_code_review_graph_session_probe()
    assert ok is True
