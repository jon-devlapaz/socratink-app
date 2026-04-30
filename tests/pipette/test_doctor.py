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


def test_mcp_probe_warns_when_server_not_configured(monkeypatch):
    """F1: when `claude mcp get code-review-graph` exits nonzero (server
    not configured), doctor must return WARN, not OK."""
    from tools.pipette import doctor

    monkeypatch.setattr(doctor, "_probe_mcp_via_claude_cli",
                        lambda name: (False, f"{name} MCP not configured"),
                        raising=False)
    ok, msg = doctor._verify_code_review_graph_session_probe()
    assert ok is False
    assert "not configured" in msg


def test_mcp_probe_warns_when_server_disconnected(monkeypatch):
    """F1: when the server is configured but the probe doesn't see
    `Connected`, doctor must WARN."""
    from tools.pipette import doctor

    monkeypatch.setattr(doctor, "_probe_mcp_via_claude_cli",
                        lambda name: (False, f"{name} MCP configured but not connected"),
                        raising=False)
    ok, msg = doctor._verify_code_review_graph_session_probe()
    assert ok is False
    assert "not connected" in msg


def test_mcp_probe_ok_when_server_connected(monkeypatch):
    """F1: when `claude mcp get code-review-graph` returns rc=0 with
    `Status: ✓ Connected`, doctor must return OK."""
    from tools.pipette import doctor

    monkeypatch.setattr(doctor, "_probe_mcp_via_claude_cli",
                        lambda name: (True, f"{name} MCP connected"),
                        raising=False)
    ok, msg = doctor._verify_code_review_graph_session_probe()
    assert ok is True
    assert "connected" in msg.lower()


def test_mcp_probe_handles_missing_claude_cli(monkeypatch):
    """F1: if the `claude` CLI is not on PATH (rare, but possible in CI),
    the probe must WARN with a clear message rather than crash."""
    import tools.pipette.doctor as doctor_mod
    # shutil.which is the gate; force it to return None.
    monkeypatch.setattr("shutil.which", lambda name: None)
    ok, msg = doctor_mod._probe_mcp_via_claude_cli("code-review-graph")
    assert ok is False
    assert "claude CLI not on PATH" in msg


def test_mcp_probe_treats_subprocess_failure_as_warn(monkeypatch):
    """F1: timeout/FileNotFoundError from subprocess.run must surface as
    WARN, not propagate."""
    import tools.pipette.doctor as doctor_mod
    import subprocess as _sp

    def boom(*args, **kwargs):
        raise _sp.TimeoutExpired(cmd=args[0], timeout=15)
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/claude")
    monkeypatch.setattr("subprocess.run", boom)
    ok, msg = doctor_mod._probe_mcp_via_claude_cli("code-review-graph")
    assert ok is False
    assert "TimeoutExpired" in msg or "claude mcp probe failed" in msg
