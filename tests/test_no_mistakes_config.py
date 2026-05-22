import os
import stat
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG = REPO_ROOT / ".no-mistakes.yaml"
ENV_SCRIPT = REPO_ROOT / "scripts" / "no-mistakes-env.sh"
TEST_SCRIPT = REPO_ROOT / "scripts" / "no-mistakes-test.sh"
LINT_SCRIPT = REPO_ROOT / "scripts" / "no-mistakes-lint.sh"


def _run(
    args: list[str],
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        args,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        env=merged_env,
    )


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


def test_no_mistakes_config_uses_repo_wrapper_commands() -> None:
    text = CONFIG.read_text(encoding="utf-8")

    assert 'test: "bash scripts/no-mistakes-test.sh"' in text
    assert 'lint: "bash scripts/no-mistakes-lint.sh"' in text
    assert "format:" not in text
    assert 'agents/superpowers/**' in text


def test_no_mistakes_scripts_are_executable() -> None:
    for script in (ENV_SCRIPT, TEST_SCRIPT, LINT_SCRIPT):
        mode = script.stat().st_mode
        assert mode & stat.S_IXUSR, f"{script} must be user-executable"


def test_no_mistakes_env_preserves_existing_values() -> None:
    result = _run(
        [
            "bash",
            "-c",
            (
                "source scripts/no-mistakes-env.sh; "
                "printf '%s\\n' "
                "\"$AUTH_ENABLED\" "
                "\"$SUPABASE_URL\" "
                "\"$SESSION_COOKIE_KEY\" "
                "\"$SOCRATINK_E2E_LOCAL_GUEST\""
            ),
        ],
        REPO_ROOT,
        {
            "AUTH_ENABLED": "false",
            "SUPABASE_URL": "https://real.example",
            "SESSION_COOKIE_KEY": "keep-this-key",
            "SOCRATINK_E2E_LOCAL_GUEST": "0",
        },
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        "false",
        "https://real.example",
        "keep-this-key",
        "0",
    ]


def test_no_mistakes_env_uses_test_safe_guest_defaults() -> None:
    result = _run(
        [
            "bash",
            "-c",
            (
                "unset GITHUB_ACTIONS SOCRATINK_DEV_AUTOGUEST SOCRATINK_E2E_LOCAL_GUEST; "
                "source scripts/no-mistakes-env.sh; "
                "printf '%s\\n' "
                "\"$GITHUB_ACTIONS\" "
                "\"$SOCRATINK_DEV_AUTOGUEST\" "
                "\"$SOCRATINK_E2E_LOCAL_GUEST\""
            ),
        ],
        REPO_ROOT,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["true", "0", "1"]


def test_no_mistakes_lint_diff_check_uses_compare_branch_merge_base(
    tmp_path: Path,
) -> None:
    repo = _init_repo(tmp_path)
    _git(repo, "checkout", "-b", "origin/dev")
    (repo / "remote.txt").write_text("remote\n", encoding="utf-8")
    _git(repo, "add", "remote.txt")
    _git(repo, "commit", "-m", "remote work")
    _git(repo, "checkout", "dev")
    (repo / "local.txt").write_text("bad trailing whitespace \n", encoding="utf-8")
    _git(repo, "add", "local.txt")
    _git(repo, "commit", "-m", "local whitespace")

    result = _run(
        [
            "bash",
            "-c",
            (
                f"source {LINT_SCRIPT}; "
                "base=$(resolve_no_mistakes_diff_base); "
                "run_no_mistakes_diff_check \"$base\""
            ),
        ],
        repo,
        {"COMPARE_BRANCH": "origin/dev"},
    )

    assert result.returncode != 0
    assert "trailing whitespace" in result.stdout
    assert "remote.txt" not in result.stdout
