import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "local-ai-review.sh"


def _run(args: list[str], cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)


def test_check_mode_is_disabled_noop() -> None:
    result = _run(["bash", str(SCRIPT), "check"])

    assert result.returncode == 0
    assert "disabled; skipping advisory review" in result.stdout


def test_publish_diff_mode_is_disabled_noop() -> None:
    result = _run(["bash", str(SCRIPT), "publish-diff", "origin/main"])

    assert result.returncode == 0
    assert "disabled; skipping advisory review" in result.stdout


def test_pytest_mode_keeps_argument_validation() -> None:
    result = _run(["bash", str(SCRIPT), "pytest", "pytest"])

    assert result.returncode == 2
    assert "pytest mode requires" in result.stderr


def test_script_does_not_reference_removed_local_model() -> None:
    text = SCRIPT.read_text(encoding="utf-8").lower()

    assert "deepseek" not in text
    assert "ollama" not in text


def test_script_does_not_contain_git_mutation_commands() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    forbidden = (
        "git add",
        "git commit",
        "git push",
        "git reset",
        "git stash",
        "git checkout",
        "git worktree remove",
        "agent-push.py --ack",
    )
    for phrase in forbidden:
        assert phrase not in text


def test_script_is_executable() -> None:
    assert SCRIPT.exists()
    assert os.access(SCRIPT, os.X_OK), "local AI review script must be executable"
