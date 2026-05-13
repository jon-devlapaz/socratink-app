import json
import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK = REPO_ROOT / "scripts" / "git-hooks" / "pre-push"


def test_pre_push_rejects_without_authorization(tmp_path):
    result = subprocess.run(
        ["/bin/zsh", str(HOOK), "origin", "https://github.com/jon-devlapaz/socratink-app.git"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    assert "agent-push.py" in result.stderr


def test_pre_push_accepts_matching_authorization(tmp_path):
    runtime = tmp_path / ".agents" / "runtime"
    runtime.mkdir(parents=True)
    auth = runtime / "push-auth.json"
    auth.write_text(json.dumps({
        "branch": "dev",
        "head_sha": "abc1234",
        "dirty": False,
        "route": "origin/dev",
        "remote_url": "https://github.com/jon-devlapaz/socratink-app.git",
        "refspec": "dev",
        "diff_fingerprint": "fp",
        "risk_class": "confirm",
        "nonce": "n",
        "issued_at_epoch": 1,
    }), encoding="utf-8")
    env = os.environ | {"SOCRATINK_PUSH_AUTH_PATH": str(auth), "SOCRATINK_PUSH_SKIP_GIT_HEAD": "1"}
    result = subprocess.run(
        ["/bin/zsh", str(HOOK), "origin", "https://github.com/jon-devlapaz/socratink-app.git"],
        cwd=tmp_path,
        input="refs/heads/dev abc1234 refs/heads/dev 0000000\n",
        text=True,
        capture_output=True,
        env=env,
    )
    assert result.returncode == 0


def test_pre_push_rejects_mismatched_destination_ref(tmp_path):
    runtime = tmp_path / ".agents" / "runtime"
    runtime.mkdir(parents=True)
    auth = runtime / "push-auth.json"
    auth.write_text(json.dumps({
        "branch": "dev",
        "head_sha": "abc1234",
        "dirty": False,
        "route": "origin/dev",
        "remote_url": "https://github.com/jon-devlapaz/socratink-app.git",
        "refspec": "dev",
        "diff_fingerprint": "fp",
        "risk_class": "confirm",
        "nonce": "n",
        "issued_at_epoch": 1,
    }), encoding="utf-8")
    env = os.environ | {"SOCRATINK_PUSH_AUTH_PATH": str(auth), "SOCRATINK_PUSH_SKIP_GIT_HEAD": "1"}
    result = subprocess.run(
        ["/bin/zsh", str(HOOK), "origin", "https://github.com/jon-devlapaz/socratink-app.git"],
        cwd=tmp_path,
        input="refs/heads/dev abc1234 refs/heads/main 0000000\n",
        text=True,
        capture_output=True,
        env=env,
    )
    assert result.returncode == 1
    assert "authorized destination" in result.stderr
