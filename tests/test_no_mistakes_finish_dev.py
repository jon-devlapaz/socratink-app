import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "no-mistakes-finish-dev.sh"


def _run(args: list[str], cwd: Path, **kwargs) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False, **kwargs)


def _git(repo: Path, *args: str) -> str:
    result = _run(["git", *args], repo)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _commit(repo: Path, message: str, filename: str, content: str) -> str:
    path = repo / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    _git(repo, "add", filename)
    _git(repo, "commit", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _stub_no_mistakes(tmp_path: Path, output: str) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "no-mistakes"
    stub.write_text(f"#!/usr/bin/env bash\ncat <<'EOF'\n{output}\nEOF\n", encoding="utf-8")
    stub.chmod(0o755)
    return bin_dir


def _init_repo(tmp_path: Path) -> tuple[Path, Path]:
    origin = tmp_path / "origin.git"
    local = tmp_path / "local"
    _run(["git", "init", "--bare", str(origin)], tmp_path)
    _run(["git", "init", "-b", "dev", str(local)], tmp_path)
    _git(local, "config", "user.email", "test@example.com")
    _git(local, "config", "user.name", "Test User")
    _git(local, "remote", "add", "origin", str(origin))
    _commit(local, "base", "README.md", "base\n")
    _git(local, "push", "-u", "origin", "dev")
    return local, origin


def _env_with_no_mistakes(tmp_path: Path, output: str) -> dict[str, str]:
    bin_dir = _stub_no_mistakes(tmp_path, output)
    return os.environ | {"PATH": f"{bin_dir}:{os.environ['PATH']}"}


def test_refuses_when_no_mistakes_run_is_active(tmp_path: Path) -> None:
    local, _origin = _init_repo(tmp_path)
    env = _env_with_no_mistakes(tmp_path, "Active run\nbranch: dev\n")

    result = _run(["bash", str(SCRIPT)], local, env=env)

    assert result.returncode == 2
    assert "no-mistakes attach" in result.stdout


def test_refuses_dirty_worktree_before_reset(tmp_path: Path) -> None:
    local, _origin = _init_repo(tmp_path)
    (local / "scratch.txt").write_text("dirty\n", encoding="utf-8")
    env = _env_with_no_mistakes(tmp_path, "no active run\n")

    result = _run(["bash", str(SCRIPT)], local, env=env)

    assert result.returncode == 2
    assert "working tree is not clean" in result.stdout
    assert "scratch.txt" in result.stdout


def test_resets_when_local_commit_is_folded_by_daemon(tmp_path: Path) -> None:
    local, origin = _init_repo(tmp_path)
    local_sha = _commit(local, "docs update", "docs/a.md", "folded\n")

    daemon = tmp_path / "daemon"
    _run(["git", "clone", str(origin), str(daemon)], tmp_path)
    _git(daemon, "switch", "dev")
    _git(daemon, "config", "user.email", "daemon@example.com")
    _git(daemon, "config", "user.name", "No Mistakes")
    _commit(daemon, "docs update", "docs/a.md", "folded\n")
    daemon_tip = _commit(daemon, "no-mistakes(document): follow-up", "docs/follow-up.md", "daemon\n")
    _git(daemon, "push", "origin", "dev")

    env = _env_with_no_mistakes(tmp_path, "no active run\n")
    result = _run(["bash", str(SCRIPT)], local, env=env)

    assert result.returncode == 0, result.stderr + result.stdout
    assert "local commits are patch-equivalent" in result.stdout
    assert _git(local, "rev-parse", "HEAD") == daemon_tip
    assert _git(local, "rev-list", "--left-right", "--count", "origin/dev...HEAD") == "0\t0"
    assert _git(local, "rev-parse", local_sha)


def test_refuses_unique_local_work(tmp_path: Path) -> None:
    local, origin = _init_repo(tmp_path)
    _commit(local, "local only", "docs/local.md", "local\n")

    daemon = tmp_path / "daemon"
    _run(["git", "clone", str(origin), str(daemon)], tmp_path)
    _git(daemon, "switch", "dev")
    _git(daemon, "config", "user.email", "test@example.com")
    _git(daemon, "config", "user.name", "Test User")
    _commit(daemon, "daemon only", "docs/daemon.md", "daemon\n")
    _git(daemon, "push", "origin", "dev")

    env = _env_with_no_mistakes(tmp_path, "no active run\n")
    result = _run(["bash", str(SCRIPT)], local, env=env)

    assert result.returncode == 2
    assert "refusing to discard unique local work" in result.stderr
    assert _git(local, "log", "-1", "--pretty=%s") == "local only"


def test_script_is_executable() -> None:
    assert SCRIPT.exists()
    assert os.access(SCRIPT, os.X_OK), "finish script must be executable"
