import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "git-wip-explain.sh"


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)


def _git(repo: Path, *args: str) -> str:
    result = _run(["git", *args], repo)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    _run(["git", "init", "-b", "dev", str(repo)], tmp_path)
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    (repo / "tracked.txt").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "tracked.txt")
    _git(repo, "commit", "-m", "base")
    return repo


def test_explains_clean_tree(tmp_path: Path) -> None:
    origin = tmp_path / "origin.git"
    repo = _init_repo(tmp_path)
    _run(["git", "init", "--bare", str(origin)], tmp_path)
    _git(repo, "remote", "add", "origin", str(origin))
    _git(repo, "push", "-u", "origin", "dev")

    result = _run(["bash", str(SCRIPT)], repo)

    assert result.returncode == 0
    assert "[git-wip-explain] head:" in result.stdout
    assert "Known worktrees:" in result.stdout
    assert "* current worktree" in result.stdout
    assert "Health summary:" in result.stdout
    assert "[OK] Worktree: clean" in result.stdout
    assert "[OK] Upstream: aligned with upstream" in result.stdout
    assert "[OK] Finish helper: safe to run when no-mistakes is finished" in result.stdout
    assert "Working tree is clean." in result.stdout
    assert "Blocks no-mistakes finish helper: no" in result.stdout


def test_shows_upstream_local_and_remote_commit_orientation(tmp_path: Path) -> None:
    origin = tmp_path / "origin.git"
    repo = _init_repo(tmp_path)
    _run(["git", "init", "--bare", str(origin)], tmp_path)
    _git(repo, "remote", "add", "origin", str(origin))
    _git(repo, "push", "-u", "origin", "dev")
    (repo / "local.txt").write_text("local\n", encoding="utf-8")
    _git(repo, "add", "local.txt")
    _git(repo, "commit", "-m", "local work")

    result = _run(["bash", str(SCRIPT)], repo)

    assert result.returncode == 0
    assert "upstream: origin/dev (behind=0 ahead=1)" in result.stdout
    assert "Local commits not on origin/dev (1):" in result.stdout
    assert "local work" in result.stdout
    assert "Remote commits not in local HEAD (0):" in result.stdout
    assert "[WARN] Upstream: local branch has 1 unpublished commit(s)" in result.stdout
    assert "[BLOCKED] Finish helper: local commits are not on origin/dev" in result.stdout
    assert "Blocks no-mistakes finish helper: yes" in result.stdout


def test_classifies_staged_unstaged_and_untracked_work(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "tracked.txt").write_text("base\nunstaged\n", encoding="utf-8")
    (repo / "staged.txt").write_text("staged\n", encoding="utf-8")
    (repo / "untracked.txt").write_text("untracked\n", encoding="utf-8")
    _git(repo, "add", "staged.txt")

    result = _run(["bash", str(SCRIPT)], repo)

    assert result.returncode == 0
    assert "Staged for commit (1):" in result.stdout
    assert "A staged.txt" in result.stdout
    assert "Unstaged changes (1):" in result.stdout
    assert "M tracked.txt" in result.stdout
    assert "Untracked files (1):" in result.stdout
    assert "untracked.txt" in result.stdout
    assert "[BLOCKED] Worktree: 3 staged/unstaged/untracked item(s)" in result.stdout
    assert "[BLOCKED] Finish helper: dirty working tree" in result.stdout
    assert "Blocks no-mistakes finish helper: yes" in result.stdout


def test_handles_no_staged_changes(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "tracked.txt").write_text("base\nunstaged\n", encoding="utf-8")
    (repo / "untracked.txt").write_text("untracked\n", encoding="utf-8")

    result = _run(["bash", str(SCRIPT)], repo)

    assert result.returncode == 0
    assert "Staged for commit (0):" in result.stdout
    assert "Unstaged changes (1):" in result.stdout
    assert "Untracked files (1):" in result.stdout


def test_rejects_unexpected_args(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)

    result = _run(["bash", str(SCRIPT), "--unknown"], repo)

    assert result.returncode == 2
    assert "Usage:" in result.stderr


def test_script_is_executable() -> None:
    assert SCRIPT.exists()
    assert os.access(SCRIPT, os.X_OK), "wip explain script must be executable"
