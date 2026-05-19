import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "git-worktree-cleanup.sh"


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
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "base")
    return repo


def test_lists_worktrees_without_removing(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    wt = tmp_path / "feature"
    _git(repo, "worktree", "add", "-b", "feature/demo", str(wt))

    result = _run(["bash", str(SCRIPT)], repo)

    assert result.returncode == 0
    assert "registered worktrees" in result.stdout
    assert "clean-removable" in result.stdout
    assert str(wt) in result.stdout
    assert wt.exists()


def test_remove_requires_apply(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    wt = tmp_path / "feature"
    _git(repo, "worktree", "add", "-b", "feature/demo", str(wt))

    result = _run(["bash", str(SCRIPT), "--remove", str(wt)], repo)

    assert result.returncode == 2
    assert "requires --apply" in result.stderr
    assert wt.exists()


def test_removes_clean_registered_worktree_with_apply(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    wt = tmp_path / "feature"
    _git(repo, "worktree", "add", "-b", "feature/demo", str(wt))

    result = _run(["bash", str(SCRIPT), "--remove", str(wt), "--apply"], repo)

    assert result.returncode == 0, result.stderr + result.stdout
    assert "removed" in result.stdout
    assert not wt.exists()


def test_refuses_dirty_worktree(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    wt = tmp_path / "feature"
    _git(repo, "worktree", "add", "-b", "feature/demo", str(wt))
    (wt / "scratch.txt").write_text("dirty\n", encoding="utf-8")

    result = _run(["bash", str(SCRIPT), "--remove", str(wt), "--apply"], repo)

    assert result.returncode == 2
    assert "refusing dirty worktree" in result.stdout
    assert wt.exists()


def test_refuses_current_worktree(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)

    result = _run(["bash", str(SCRIPT), "--remove", str(repo), "--apply"], repo)

    assert result.returncode == 2
    assert "current worktree" in result.stderr or "main worktree" in result.stderr
    assert repo.exists()


def test_script_is_executable() -> None:
    assert SCRIPT.exists()
    assert os.access(SCRIPT, os.X_OK), "worktree cleanup script must be executable"
