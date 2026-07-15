from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
QA_SMOKE = REPO_ROOT / "scripts" / "qa-smoke.sh"


def test_local_smoke_runner_owns_missing_server_lifecycle() -> None:
    script = QA_SMOKE.read_text()

    assert 'trap cleanup EXIT' in script
    assert 'target.hostname in {"localhost", "127.0.0.1"}' in script
    assert '"$REPO_ROOT/$UVICORN_BIN" main:app' in script
    assert 'exec "$PYTEST_BIN"' not in script
