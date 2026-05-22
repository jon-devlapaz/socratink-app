import os
import json
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


def test_json_mode_lists_worktrees_with_status_contract(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    wt = tmp_path / "feature"
    _git(repo, "worktree", "add", "-b", "feature/demo", str(wt))

    result = _run(["bash", str(SCRIPT), "--json"], repo)

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == 1
    assert payload["repo"] == str(repo)
    statuses = {entry["path"]: entry["status"] for entry in payload["worktrees"]}
    assert statuses[str(repo)] in {"current", "main"}
    assert statuses[str(wt)] == "clean-removable"
    assert "registered worktrees" not in result.stdout
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


def test_bulk_remove_clean_requires_apply(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    wt = tmp_path / "feature"
    _git(repo, "worktree", "add", "-b", "feature/demo", str(wt))

    result = _run(["bash", str(SCRIPT), "--remove-clean"], repo)

    assert result.returncode == 2
    assert "bulk removal requires --apply" in result.stderr
    assert wt.exists()


def test_bulk_remove_clean_removes_only_clean_removable_worktrees(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    clean_one = tmp_path / "clean-one"
    clean_two = tmp_path / "clean-two"
    dirty = tmp_path / "dirty"
    detached = tmp_path / "detached"
    _git(repo, "worktree", "add", "-b", "feature/clean-one", str(clean_one))
    _git(repo, "worktree", "add", "-b", "feature/clean-two", str(clean_two))
    _git(repo, "worktree", "add", "-b", "feature/dirty", str(dirty))
    _git(repo, "worktree", "add", "--detach", str(detached), "dev")
    (dirty / "scratch.txt").write_text("dirty\n", encoding="utf-8")
    (detached / "detached.txt").write_text("detached\n", encoding="utf-8")
    _git(detached, "add", "detached.txt")
    _git(detached, "commit", "-m", "detached work")

    result = _run(["bash", str(SCRIPT), "--remove-clean", "--apply"], repo)

    assert result.returncode == 0, result.stderr + result.stdout
    assert "removing 2 clean-removable worktree(s)" in result.stdout
    assert not clean_one.exists()
    assert not clean_two.exists()
    assert dirty.exists()
    assert detached.exists()
    assert repo.exists()


def test_bulk_remove_clean_noops_when_none_found(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)

    result = _run(["bash", str(SCRIPT), "--remove-clean", "--apply"], repo)

    assert result.returncode == 0
    assert "no clean-removable worktrees found" in result.stdout
    assert repo.exists()


def test_refuses_current_worktree(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)

    result = _run(["bash", str(SCRIPT), "--remove", str(repo), "--apply"], repo)

    assert result.returncode == 2
    assert "current worktree" in result.stderr or "main worktree" in result.stderr
    assert repo.exists()


def test_refuses_clean_detached_worktree_with_unique_commit(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    wt = tmp_path / "detached"
    _git(repo, "worktree", "add", "--detach", str(wt), "dev")
    (wt / "detached.txt").write_text("detached\n", encoding="utf-8")
    _git(wt, "add", "detached.txt")
    _git(wt, "commit", "-m", "detached work")

    result = _run(["bash", str(SCRIPT), "--remove", str(wt), "--apply"], repo)

    assert result.returncode == 2
    assert "refusing to remove detached HEAD worktree" in result.stderr
    assert wt.exists()


def test_script_is_executable() -> None:
    assert SCRIPT.exists()
    assert os.access(SCRIPT, os.X_OK), "worktree cleanup script must be executable"
