# tests/pipette/test_doctor.py
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
