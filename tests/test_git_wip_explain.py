import os
import json
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
    assert "Next: python3 scripts/agent-push.py --target no-mistakes/dev" in result.stdout
    assert "Blocks no-mistakes finish helper: yes" in result.stdout


def test_short_mode_summarizes_state_and_next_command(tmp_path: Path) -> None:
    origin = tmp_path / "origin.git"
    repo = _init_repo(tmp_path)
    _run(["git", "init", "--bare", str(origin)], tmp_path)
    _git(repo, "remote", "add", "origin", str(origin))
    _git(repo, "push", "-u", "origin", "dev")
    (repo / "local.txt").write_text("local\n", encoding="utf-8")
    _git(repo, "add", "local.txt")
    _git(repo, "commit", "-m", "local work")

    result = _run(["bash", str(SCRIPT), "--short"], repo)

    assert result.returncode == 0
    assert "dev @" in result.stdout
    assert "upstream=behind:0 ahead:1" in result.stdout
    assert "Next: python3 scripts/agent-push.py --target no-mistakes/dev" in result.stdout
    assert "Known worktrees:" not in result.stdout


def test_json_mode_returns_stable_state_contract(tmp_path: Path) -> None:
    origin = tmp_path / "origin.git"
    repo = _init_repo(tmp_path)
    _run(["git", "init", "--bare", str(origin)], tmp_path)
    _git(repo, "remote", "add", "origin", str(origin))
    _git(repo, "push", "-u", "origin", "dev")
    (repo / "local.txt").write_text("local\n", encoding="utf-8")
    _git(repo, "add", "local.txt")
    _git(repo, "commit", "-m", "local work")

    result = _run(["bash", str(SCRIPT), "--json"], repo)

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == 1
    assert payload["branch"] == "dev"
    assert payload["upstream"]["name"] == "origin/dev"
    assert payload["upstream"]["ahead"] == 1
    assert payload["upstream"]["behind"] == 0
    assert payload["worktree"]["dirty_count"] == 0
    assert payload["finish"]["blocked"] is True
    assert payload["recommended_next"] == "python3 scripts/agent-push.py --target no-mistakes/dev"
    assert "[git-wip-explain]" not in result.stdout


def test_feature_branch_ahead_recommends_feature_publication(tmp_path: Path) -> None:
    origin = tmp_path / "origin.git"
    repo = _init_repo(tmp_path)
    _run(["git", "init", "--bare", str(origin)], tmp_path)
    _git(repo, "remote", "add", "origin", str(origin))
    _git(repo, "push", "-u", "origin", "dev")
    _git(repo, "checkout", "-b", "feat/demo")
    _git(repo, "push", "-u", "origin", "feat/demo")
    (repo / "feature.txt").write_text("feature\n", encoding="utf-8")
    _git(repo, "add", "feature.txt")
    _git(repo, "commit", "-m", "feature work")

    result = _run(["bash", str(SCRIPT), "--short"], repo)

    assert result.returncode == 0
    assert "feat/demo @" in result.stdout
    assert "upstream=behind:0 ahead:1" in result.stdout
    assert "Next: python3 scripts/agent-push.py --target origin/feat/demo" in result.stdout
    assert "no-mistakes/dev" not in result.stdout


def test_diverged_branch_recommends_inspection_not_publish(tmp_path: Path) -> None:
    origin = tmp_path / "origin.git"
    repo = _init_repo(tmp_path)
    _run(["git", "init", "--bare", str(origin)], tmp_path)
    _git(repo, "remote", "add", "origin", str(origin))
    _git(repo, "push", "-u", "origin", "dev")

    remote_clone = tmp_path / "remote-clone"
    _run(["git", "clone", "-b", "dev", str(origin), str(remote_clone)], tmp_path)
    _git(remote_clone, "config", "user.email", "remote@example.com")
    _git(remote_clone, "config", "user.name", "Remote User")
    (remote_clone / "remote.txt").write_text("remote\n", encoding="utf-8")
    _git(remote_clone, "add", "remote.txt")
    _git(remote_clone, "commit", "-m", "remote work")
    _git(remote_clone, "push", "origin", "dev")

    (repo / "local.txt").write_text("local\n", encoding="utf-8")
    _git(repo, "add", "local.txt")
    _git(repo, "commit", "-m", "local work")
    _git(repo, "fetch", "origin", "dev:refs/remotes/origin/dev")

    result = _run(["bash", str(SCRIPT), "--short"], repo)

    assert result.returncode == 0
    assert "upstream=behind:1 ahead:1" in result.stdout
    assert "Next: git fetch && git status --short --branch && git diff @{u}...HEAD" in result.stdout
    assert "agent-push.py" not in result.stdout


def test_dev_ahead_blocks_no_mistakes_push_when_gate_ref_is_diverged(tmp_path: Path) -> None:
    origin = tmp_path / "origin.git"
    gate = tmp_path / "gate.git"
    repo = _init_repo(tmp_path)
    _run(["git", "init", "--bare", str(origin)], tmp_path)
    _run(["git", "init", "--bare", str(gate)], tmp_path)
    _git(repo, "remote", "add", "origin", str(origin))
    _git(repo, "remote", "add", "no-mistakes", str(gate))
    _git(repo, "push", "-u", "origin", "dev")

    gate_clone = tmp_path / "gate-clone"
    _run(["git", "clone", "-b", "dev", str(origin), str(gate_clone)], tmp_path)
    _git(gate_clone, "config", "user.email", "gate@example.com")
    _git(gate_clone, "config", "user.name", "No Mistakes")
    (gate_clone / "gate.txt").write_text("gate\n", encoding="utf-8")
    _git(gate_clone, "add", "gate.txt")
    _git(gate_clone, "commit", "-m", "gate rewrite")
    _git(gate_clone, "push", str(gate), "dev")
    _git(repo, "fetch", "no-mistakes", "dev:refs/remotes/no-mistakes/dev")

    (repo / "local.txt").write_text("local\n", encoding="utf-8")
    _git(repo, "add", "local.txt")
    _git(repo, "commit", "-m", "local work")

    result = _run(["bash", str(SCRIPT), "--short"], repo)

    assert result.returncode == 0
    assert "upstream=behind:0 ahead:1" in result.stdout
    assert "Next: git cherry -v no-mistakes/dev HEAD" in result.stdout
    assert "agent-push.py" not in result.stdout


def test_behind_feature_branch_recommends_inspection_not_dev_finish(tmp_path: Path) -> None:
    origin = tmp_path / "origin.git"
    repo = _init_repo(tmp_path)
    _run(["git", "init", "--bare", str(origin)], tmp_path)
    _git(repo, "remote", "add", "origin", str(origin))
    _git(repo, "push", "-u", "origin", "dev")
    _git(repo, "checkout", "-b", "feat/demo")
    _git(repo, "push", "-u", "origin", "feat/demo")

    remote_clone = tmp_path / "remote-clone"
    _run(["git", "clone", "-b", "feat/demo", str(origin), str(remote_clone)], tmp_path)
    _git(remote_clone, "config", "user.email", "remote@example.com")
    _git(remote_clone, "config", "user.name", "Remote User")
    (remote_clone / "remote.txt").write_text("remote\n", encoding="utf-8")
    _git(remote_clone, "add", "remote.txt")
    _git(remote_clone, "commit", "-m", "remote feature work")
    _git(remote_clone, "push", "origin", "feat/demo")
    _git(repo, "fetch", "origin", "feat/demo:refs/remotes/origin/feat/demo")

    result = _run(["bash", str(SCRIPT), "--short"], repo)

    assert result.returncode == 0
    assert "feat/demo @" in result.stdout
    assert "upstream=behind:1 ahead:0" in result.stdout
    assert "Next: git fetch && git status --short --branch && git log --oneline HEAD..@{u}" in result.stdout
    assert "no-mistakes-finish-dev.sh" not in result.stdout


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
    assert "Recommended next command:" in result.stdout
    assert "git diff && git status --short" in result.stdout
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
