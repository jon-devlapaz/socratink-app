import json
import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "git-founder-help.sh"


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)


def test_help_is_founder_facing_and_read_only() -> None:
    result = _run(["bash", str(SCRIPT)], REPO_ROOT)

    assert result.returncode == 0
    assert "Socratink git helper map" in result.stdout
    assert "gwip" in result.stdout
    assert "gpub" in result.stdout
    assert "gfinish" in result.stdout
    assert "gwt" in result.stdout
    assert "ghelp" in result.stdout
    assert "raw-pushes" in result.stdout


def test_help_json_lists_command_contracts() -> None:
    result = _run(["bash", str(SCRIPT), "--json"], REPO_ROOT)

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == 1
    assert payload["workflow"] == "socratink-founder-git"
    names = [command["name"] for command in payload["commands"]]
    assert names == ["gwip", "gpub", "gfinish", "gwt", "ghelp", "snm"]
    assert payload["commands"][0]["safe"] == "read-only"


def test_doctor_reports_helper_readiness() -> None:
    result = _run(["bash", str(SCRIPT), "doctor", "--json"], REPO_ROOT)

    assert result.returncode in {0, 1}
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == 1
    checks = {check["name"]: check for check in payload["checks"]}
    assert checks["git-wip-explain"]["ok"] is True
    assert checks["agent-push"]["ok"] is True
    assert checks["git-worktree-cleanup"]["ok"] is True
    assert checks["no-mistakes-finish-dev"]["ok"] is True
    assert "shell-shortcuts" in checks


def test_script_is_executable() -> None:
    assert SCRIPT.exists()
    assert os.access(SCRIPT, os.X_OK), "founder git help script must be executable"
