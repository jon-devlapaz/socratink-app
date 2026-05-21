import os
import stat
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "local-ai-review.sh"


def _run(args: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False, env=merged_env)


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


def _fake_deepseek(tmp_path: Path) -> tuple[Path, Path]:
    capture = tmp_path / "deepseek-capture.txt"
    fake = tmp_path / "fake-deepseek"
    fake.write_text(
        "#!/usr/bin/env bash\n"
        "printf 'ARGV:%s\\n' \"$*\" > \"$DEEPSEEK_CAPTURE\"\n"
        "printf 'STDIN_START\\n' >> \"$DEEPSEEK_CAPTURE\"\n"
        "cat >> \"$DEEPSEEK_CAPTURE\"\n"
        "printf 'fake local review\\n'\n",
        encoding="utf-8",
    )
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
    return fake, capture


def test_check_refuses_broad_ollama_host(tmp_path: Path) -> None:
    fake, capture = _fake_deepseek(tmp_path)
    repo = _init_repo(tmp_path)

    result = _run(
        ["bash", str(SCRIPT), "check"],
        repo,
        {
            "DEEPSEEK_LOCAL_BIN": str(fake),
            "DEEPSEEK_CAPTURE": str(capture),
            "OLLAMA_HOST": "0.0.0.0:11434",
        },
    )

    assert result.returncode == 2
    assert "refusing broad OLLAMA_HOST" in result.stderr
    assert not capture.exists()


def test_staged_mode_sends_canned_prompt_and_staged_diff(tmp_path: Path) -> None:
    fake, capture = _fake_deepseek(tmp_path)
    repo = _init_repo(tmp_path)
    (repo / "tracked.txt").write_text("base\nchanged\n", encoding="utf-8")
    _git(repo, "add", "tracked.txt")

    result = _run(
        ["bash", str(SCRIPT), "staged"],
        repo,
        {"DEEPSEEK_LOCAL_BIN": str(fake), "DEEPSEEK_CAPTURE": str(capture)},
    )

    assert result.returncode == 0
    assert "[local-ai-review] mode: staged" in result.stdout
    assert "ADVISORY ONLY" in result.stdout
    captured = capture.read_text(encoding="utf-8")
    assert "Review this staged diff for behavior-breaking bugs only" in captured
    assert "diff --git" in captured
    assert "+changed" in captured


def test_refuses_secret_like_payload_before_model_call(tmp_path: Path) -> None:
    fake, capture = _fake_deepseek(tmp_path)
    repo = _init_repo(tmp_path)
    (repo / "leak.txt").write_text("OPENAI_API_KEY=sk-test\n", encoding="utf-8")
    _git(repo, "add", "leak.txt")

    result = _run(
        ["bash", str(SCRIPT), "staged"],
        repo,
        {"DEEPSEEK_LOCAL_BIN": str(fake), "DEEPSEEK_CAPTURE": str(capture)},
    )

    assert result.returncode == 2
    assert "refusing to send possible secret" in result.stderr
    assert not capture.exists()


def test_wip_mode_uses_repo_wip_helper_when_available(tmp_path: Path) -> None:
    fake, capture = _fake_deepseek(tmp_path)
    repo = _init_repo(tmp_path)
    scripts_dir = repo / "scripts"
    scripts_dir.mkdir()
    helper = scripts_dir / "git-wip-explain.sh"
    helper.write_text("#!/usr/bin/env bash\nprintf 'wip-helper-output\\n'\n", encoding="utf-8")
    helper.chmod(helper.stat().st_mode | stat.S_IXUSR)

    result = _run(
        ["bash", str(SCRIPT), "wip"],
        repo,
        {"DEEPSEEK_LOCAL_BIN": str(fake), "DEEPSEEK_CAPTURE": str(capture)},
    )

    assert result.returncode == 0
    captured = capture.read_text(encoding="utf-8")
    assert "Explain the safest next git action" in captured
    assert "wip-helper-output" in captured


def test_pytest_mode_summarizes_failing_command_output(tmp_path: Path) -> None:
    fake, capture = _fake_deepseek(tmp_path)
    repo = _init_repo(tmp_path)
    failing = tmp_path / "failing-pytest"
    failing.write_text(
        "#!/usr/bin/env bash\n"
        "printf 'FAILED tests/demo.py::test_demo\\n'\n"
        "exit 1\n",
        encoding="utf-8",
    )
    failing.chmod(failing.stat().st_mode | stat.S_IXUSR)

    result = _run(
        ["bash", str(SCRIPT), "pytest", "--", str(failing)],
        repo,
        {"DEEPSEEK_LOCAL_BIN": str(fake), "DEEPSEEK_CAPTURE": str(capture)},
    )

    assert result.returncode == 0
    captured = capture.read_text(encoding="utf-8")
    assert "Summarize this pytest output" in captured
    assert "FAILED tests/demo.py::test_demo" in captured


def test_publish_preview_redacts_ack_token_before_model_call(tmp_path: Path) -> None:
    fake, capture = _fake_deepseek(tmp_path)
    repo = _init_repo(tmp_path)
    scripts_dir = repo / "scripts"
    scripts_dir.mkdir()
    helper = scripts_dir / "agent-push.py"
    helper.write_text(
        "print('Recommended route: no-mistakes/dev')\n"
        "print('python3 scripts/agent-push.py --target no-mistakes/dev --ack live-token-123')\n"
        "raise SystemExit(1)\n",
        encoding="utf-8",
    )

    result = _run(
        ["bash", str(SCRIPT), "publish-preview"],
        repo,
        {"DEEPSEEK_LOCAL_BIN": str(fake), "DEEPSEEK_CAPTURE": str(capture)},
    )

    assert result.returncode == 0
    captured = capture.read_text(encoding="utf-8")
    assert "[ACK_TOKEN_REDACTED]" in captured
    assert "live-token-123" not in captured


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
