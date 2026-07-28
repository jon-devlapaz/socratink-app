from __future__ import annotations

import os
import shutil
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
QA_SMOKE = REPO_ROOT / "scripts" / "qa-smoke.sh"


class _SmokeTargetHandler(BaseHTTPRequestHandler):
    homepage = b"<html><body>Sign in required</body></html>"

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        if self.path == "/api/health":
            body = b'{"status":"ok"}'
            content_type = "application/json"
        else:
            body = self.homepage
            content_type = "text/html"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def _run_smoke_fixture(
    tmp_path: Path,
    handler: type[_SmokeTargetHandler],
) -> tuple[subprocess.CompletedProcess[str], bool]:
    repo = tmp_path / "repo"
    scripts = repo / "scripts"
    bin_dir = repo / ".venv" / "bin"
    scripts.mkdir(parents=True)
    bin_dir.mkdir(parents=True)
    shutil.copy2(QA_SMOKE, scripts / "qa-smoke.sh")

    python = bin_dir / "python"
    python.write_text(
        "#!/bin/sh\n"
        "if [ \"${1:-}\" = \"-c\" ]; then exit 0; fi\n"
        f"exec {os.sys.executable} \"$@\"\n"
    )
    python.chmod(0o755)

    pytest_marker = repo / "pytest-ran"
    pytest = bin_dir / "pytest"
    pytest.write_text(f"#!/bin/sh\ntouch {pytest_marker!s}\nexit 0\n")
    pytest.chmod(0o755)
    for command in ("playwright", "uvicorn"):
        path = bin_dir / command
        path.write_text("#!/bin/sh\nexit 99\n")
        path.chmod(0o755)

    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = subprocess.run(
            ["bash", "scripts/qa-smoke.sh", f"http://127.0.0.1:{server.server_port}"],
            cwd=repo,
            text=True,
            capture_output=True,
            timeout=15,
        )
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    return result, pytest_marker.exists()


def test_local_smoke_runner_owns_missing_server_lifecycle() -> None:
    script = QA_SMOKE.read_text()

    assert "trap cleanup EXIT" in script
    assert 'target.hostname in {"localhost", "127.0.0.1"}' in script
    assert '"$REPO_ROOT/$UVICORN_BIN" main:app' in script
    assert 'exec "$PYTEST_BIN"' not in script


def test_qa_smoke_rejects_healthy_server_without_guest_entry(tmp_path: Path) -> None:
    result, pytest_ran = _run_smoke_fixture(tmp_path, _SmokeTargetHandler)

    assert result.returncode != 0
    assert "not ready for local guest smoke tests" in result.stderr
    assert not pytest_ran


def test_qa_smoke_accepts_healthy_server_with_guest_entry(tmp_path: Path) -> None:
    class GuestReadyHandler(_SmokeTargetHandler):
        homepage = b'<html><body><a id="guest-continue-link">Continue</a></body></html>'

    result, pytest_ran = _run_smoke_fixture(tmp_path, GuestReadyHandler)

    assert result.returncode == 0
    assert pytest_ran
