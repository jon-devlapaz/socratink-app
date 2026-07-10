"""Tests for loop-backend proxy routes."""

from __future__ import annotations

import os
import shutil
import sys
import uuid
from unittest.mock import MagicMock, patch

import pytest
import urllib3
from fastapi.testclient import TestClient

import loop_backend_proxy
import main
from auth.service import AuthSessionState, AuthUser


class _GuestAuthService:
    cookie_name = "sb_session"
    cookie_samesite = "lax"
    cookie_max_age = 120

    def load_session(self, sealed_session: str | None):
        return AuthSessionState(
            auth_enabled=True,
            authenticated=True,
            guest_mode=True,
            user=AuthUser(id="anon-test-user"),
            access_token="supabase-user-token",
        )

    def resolve_cookie_secure(self, base_url: str) -> bool:
        return base_url.startswith("https://")


@pytest.fixture
def client() -> TestClient:
    return TestClient(main.app)


def test_loop_proxy_uses_vendored_backend_when_external_backend_unconfigured(
    client: TestClient,
) -> None:
    upstream = MagicMock()
    upstream.status = 200
    upstream.headers = {"content-type": "text/html"}
    upstream.read.return_value = b"<p>local loop</p>"
    upstream.release_conn = MagicMock()

    with (
        patch.dict("os.environ", {}, clear=False),
        patch("loop_backend_proxy._start_local_loop_backend", return_value="http://127.0.0.1:9999"),
        patch("loop_backend_proxy._POOL.request", return_value=upstream) as request,
    ):
        import os

        os.environ.pop("LOOP_BACKEND_URL", None)
        response = client.get("/loop", headers={"Accept": "*/*"})

    assert response.status_code == 200
    assert response.text == "<p>local loop</p>"
    assert request.call_args[0][1] == "http://127.0.0.1:9999/loop"


def test_direct_loop_document_request_redirects_to_app_shell(
    client: TestClient,
) -> None:
    with patch.dict("os.environ", {}, clear=False):
        with patch("loop_backend_proxy._POOL.request") as request:
            response = client.get(
                "/loop",
                headers={"Accept": "text/html"},
                follow_redirects=False,
            )

    assert response.status_code == 302
    assert response.headers["location"] == "/"
    request.assert_not_called()


def test_loop_proxy_reports_unavailable_to_non_browser_clients(client: TestClient) -> None:
    with patch.dict(
        "os.environ",
        {"SOCRATINK_LOOP_DISABLE_LOCAL": "1"},
        clear=False,
    ):
        import os

        os.environ.pop("LOOP_BACKEND_URL", None)
        response = client.get("/loop", headers={"Accept": "*/*"})
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_loop_proxy_forwards_to_configured_backend(client: TestClient) -> None:
    upstream = MagicMock()
    upstream.status = 200
    upstream.headers = {"content-type": "text/html", "content-encoding": "gzip"}
    upstream.read.return_value = b"<p>loop</p>"
    upstream.release_conn = MagicMock()

    with (
        patch.dict(
            "os.environ",
            {"LOOP_BACKEND_URL": "https://loop.example"},
            clear=False,
        ),
        patch("loop_backend_proxy._POOL.request", return_value=upstream) as request,
    ):
        response = client.get("/loop", params={"q": "1"})

    assert response.status_code == 200
    assert response.text == "<p>loop</p>"
    assert "content-encoding" not in response.headers
    request.assert_called_once()
    assert request.call_args[0][1] == "https://loop.example/loop?q=1"
    assert request.call_args.kwargs["retries"] is False
    timeout = request.call_args.kwargs["timeout"]
    assert timeout.connect_timeout == 5.0
    assert timeout.read_timeout == 55.0
    upstream.release_conn.assert_called_once()


def test_loop_proxy_turns_upstream_timeout_into_retryable_503(
    client: TestClient,
) -> None:
    timeout_error = urllib3.exceptions.ReadTimeoutError(
        None,
        "https://loop.example/api/session",
        "timed out",
    )
    with (
        patch.dict(
            "os.environ",
            {"LOOP_BACKEND_URL": "https://loop.example"},
            clear=False,
        ),
        patch("loop_backend_proxy._POOL.request", side_effect=timeout_error),
    ):
        response = client.get("/loop", headers={"Accept": "*/*"})

    assert response.status_code == 503
    assert response.json()["detail"] == "Loop backend request timed out."


def test_session_proxy_uses_vendored_backend_even_when_external_backend_configured(
    client: TestClient,
) -> None:
    upstream = MagicMock()
    upstream.status = 201
    upstream.headers = {"content-type": "application/json"}
    upstream.read.return_value = b'{"sessionId":"local-session","status":"active"}'
    upstream.release_conn = MagicMock()

    original_service = main.app.state.auth_service
    main.app.state.auth_service = _GuestAuthService()
    try:
        with (
            patch.dict(
                "os.environ",
                {"LOOP_BACKEND_URL": "https://stale-loop.example"},
                clear=False,
            ),
            patch(
                "loop_backend_proxy._start_local_loop_backend",
                return_value="http://127.0.0.1:9999",
            ),
            patch("loop_backend_proxy._POOL.request", return_value=upstream) as request,
        ):
            response = client.post("/api/session", json={})
    finally:
        main.app.state.auth_service = original_service

    assert response.status_code == 201
    assert response.json()["sessionId"] == "local-session"
    assert request.call_args[0][1] == "http://127.0.0.1:9999/api/session"


def test_session_proxy_uses_trusted_hosted_loop_service_on_vercel(
    client: TestClient,
) -> None:
    upstream = MagicMock()
    upstream.status = 201
    upstream.headers = {"content-type": "application/json"}
    upstream.read.return_value = b'{"sessionId":"internal-session","status":"active"}'
    upstream.release_conn = MagicMock()

    original_service = main.app.state.auth_service
    main.app.state.auth_service = _GuestAuthService()
    try:
        with (
            patch.dict(
                "os.environ",
                {
                    "LOOP_BACKEND_URL": "https://loop-runtime.example",
                    "SOCRATINK_LOOP_API_KEY": "loop-token",
                    "SESSION_COOKIE_KEY": "internal-token",
                    "VERCEL": "1",
                },
                clear=False,
            ),
            patch("loop_backend_proxy._POOL.request", return_value=upstream) as request,
        ):
            response = client.post(
                "/api/session",
                json={},
                headers={
                    "host": "attacker.example",
                    "x-forwarded-host": "attacker.example",
                    "x-forwarded-proto": "https",
                    "authorization": "Bearer browser-token",
                    "cookie": "sb_session=sealed",
                },
            )
    finally:
        main.app.state.auth_service = original_service

    assert response.status_code == 201
    assert response.json()["sessionId"] == "internal-session"
    assert request.call_args[0][1] == "https://loop-runtime.example/api/session"
    forwarded = {key.lower(): value for key, value in request.call_args.kwargs["headers"].items()}
    assert forwarded["content-type"] == "application/json"
    assert forwarded["authorization"] == "Bearer loop-token"
    assert forwarded["x-socratink-user-access-token"] == "supabase-user-token"
    assert "x-socratink-internal-loop-token" not in forwarded
    assert "cookie" not in forwarded


def test_session_proxy_requires_user_token_for_vercel_internal_store(
    client: TestClient,
) -> None:
    service = _GuestAuthService()
    service.load_session = lambda _sealed: AuthSessionState(
        auth_enabled=True,
        authenticated=True,
        guest_mode=True,
        user=AuthUser(id="anon-test-user"),
    )
    original_service = main.app.state.auth_service
    main.app.state.auth_service = service
    try:
        with (
            patch.dict(
                "os.environ",
                {
                    "LOOP_BACKEND_URL": "https://loop-runtime.example",
                    "SOCRATINK_LOOP_API_KEY": "loop-token",
                    "SESSION_COOKIE_KEY": "internal-token",
                    "VERCEL": "1",
                },
                clear=False,
            ),
            patch("loop_backend_proxy._POOL.request") as request,
        ):
            response = client.post("/api/session", json={})
    finally:
        main.app.state.auth_service = original_service

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Authenticated session required for durable loop storage."
    )
    request.assert_not_called()


def test_session_proxy_fails_closed_without_hosted_loop_service(
    client: TestClient,
) -> None:
    original_service = main.app.state.auth_service
    main.app.state.auth_service = _GuestAuthService()
    try:
        with (
            patch.dict(
                "os.environ",
                {"SESSION_COOKIE_KEY": "internal-token", "VERCEL": "1"},
                clear=False,
            ),
            patch("loop_backend_proxy._POOL.request") as request,
        ):
            os.environ.pop("LOOP_BACKEND_URL", None)
            os.environ.pop("SOCRATINK_LOOP_API_KEY", None)
            response = client.post(
                "/api/session",
                json={},
                headers={"host": "attacker.example"},
            )
    finally:
        main.app.state.auth_service = original_service

    assert response.status_code == 503
    assert response.json()["detail"] == "Hosted loop backend is not configured."
    request.assert_not_called()


def test_session_proxy_rejects_request_body_over_64_kib_before_upstream(
    client: TestClient,
) -> None:
    original_service = main.app.state.auth_service
    main.app.state.auth_service = _GuestAuthService()
    try:
        with (
            patch("loop_backend_proxy._start_local_loop_backend", return_value="http://127.0.0.1:9999"),
            patch("loop_backend_proxy._POOL.request") as request,
        ):
            response = client.post(
                "/api/session",
                content=b"x" * (64 * 1024 + 1),
                headers={"content-type": "application/octet-stream"},
            )
    finally:
        main.app.state.auth_service = original_service

    assert response.status_code == 413
    assert response.json()["detail"] == "Loop request body is too large."
    request.assert_not_called()


def test_session_proxy_rejects_insecure_hosted_loop_origin(
    client: TestClient,
) -> None:
    original_service = main.app.state.auth_service
    main.app.state.auth_service = _GuestAuthService()
    try:
        with (
            patch.dict(
                "os.environ",
                {
                    "LOOP_BACKEND_URL": "http://attacker.example",
                    "SOCRATINK_LOOP_API_KEY": "loop-token",
                    "VERCEL": "1",
                },
                clear=False,
            ),
            patch("loop_backend_proxy._POOL.request") as request,
        ):
            response = client.post("/api/session", json={})
    finally:
        main.app.state.auth_service = original_service

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Hosted loop backend must be a trusted HTTPS origin."
    )
    request.assert_not_called()


def test_loop_proxy_does_not_forward_accept_encoding(client: TestClient) -> None:
    upstream = MagicMock()
    upstream.status = 200
    upstream.headers = {"content-type": "application/json"}
    upstream.read.return_value = b'{"status":"ok"}'
    upstream.release_conn = MagicMock()

    with (
        patch.dict("os.environ", {"LOOP_BACKEND_URL": "https://loop.example"}, clear=False),
        patch("loop_backend_proxy._POOL.request", return_value=upstream) as request,
    ):
        response = client.get("/health", headers={"Accept-Encoding": "gzip, deflate, br"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    headers = request.call_args.kwargs["headers"]
    assert "Accept-Encoding" not in headers
    assert "accept-encoding" not in {key.lower() for key in headers}


def test_loop_proxy_does_not_forward_browser_credentials(client: TestClient) -> None:
    upstream = MagicMock()
    upstream.status = 200
    upstream.headers = {"content-type": "application/json"}
    upstream.read.return_value = b'{"status":"ok"}'
    upstream.release_conn = MagicMock()

    with (
        patch.dict("os.environ", {"LOOP_BACKEND_URL": "https://loop.example"}, clear=False),
        patch("loop_backend_proxy._POOL.request", return_value=upstream) as request,
    ):
        response = client.get(
            "/health",
            headers={
                "Accept": "application/json",
                "Authorization": "Bearer browser-token",
                "Cookie": "sb_session=sealed",
                "X-Forwarded-For": "198.51.100.4",
            },
        )

    assert response.status_code == 200
    forwarded = {key.lower(): value for key, value in request.call_args.kwargs["headers"].items()}
    assert forwarded == {"accept": "application/json"}


def test_loop_proxy_uses_configured_loop_api_key(client: TestClient) -> None:
    upstream = MagicMock()
    upstream.status = 200
    upstream.headers = {"content-type": "application/json"}
    upstream.read.return_value = b'{"status":"ok"}'
    upstream.release_conn = MagicMock()

    with (
        patch.dict(
            "os.environ",
            {
                "LOOP_BACKEND_URL": "https://loop.example",
                "SOCRATINK_LOOP_API_KEY": "loop-secret",
            },
            clear=False,
        ),
        patch("loop_backend_proxy._POOL.request", return_value=upstream) as request,
    ):
        response = client.get(
            "/health",
            headers={"Authorization": "Bearer browser-token"},
        )

    assert response.status_code == 200
    headers = request.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer loop-secret"


def test_local_loop_backend_binds_to_loopback() -> None:
    env = loop_backend_proxy._local_loop_env(8765)

    assert env["PORT"] == "8765"
    assert env["HOST"] == "127.0.0.1"


def test_stop_local_loop_backend_clears_cached_process() -> None:
    process = MagicMock()
    process.poll.return_value = None
    loop_backend_proxy._LOCAL_LOOP_PROCESS = process
    loop_backend_proxy._LOCAL_LOOP_BASE = "http://127.0.0.1:8765"

    loop_backend_proxy._stop_local_loop_backend()

    process.terminate.assert_called_once()
    process.wait.assert_called_once_with(timeout=2)
    assert loop_backend_proxy._LOCAL_LOOP_PROCESS is None
    assert loop_backend_proxy._LOCAL_LOOP_BASE is None


def test_loop_proxy_releases_connection_when_read_fails(client: TestClient) -> None:
    upstream = MagicMock()
    upstream.read.side_effect = urllib3.exceptions.ProtocolError("broken pipe")
    upstream.release_conn = MagicMock()

    with (
        patch.dict(
            "os.environ",
            {"LOOP_BACKEND_URL": "https://loop.example"},
            clear=False,
        ),
        patch("loop_backend_proxy._POOL.request", return_value=upstream),
    ):
        response = client.get("/loop", headers={"Accept": "*/*"})

    assert response.status_code == 502
    assert "read failed" in response.json()["detail"]
    upstream.release_conn.assert_called_once()


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_vendored_loop_backend_runs_pedagogical_session(
    client: TestClient,
) -> None:
    turns = [
        "Immune memory",
        "I want to explain why a second exposure gets handled faster.",
        "First exposure activates B and T cells; some become memory cells that stay around.",
        "Memory cells stay after the first infection, so later the body does not start from scratch.",
        "Continue",
        "The missing link is that some activated cells persist as memory cells after the first exposure.",
        "Those memory cells persist and respond faster when the same pathogen returns.",
        "Continue",
        "Continue",
        (
            "The first exposure leaves memory B and T cells behind. On a later exposure "
            "those memory cells recognize the pathogen quickly, expand, and make a faster "
            "stronger response."
        ),
    ]
    with patch.dict(
        os.environ,
        {
            "SOCRATINK_TUI_FAKE_LLM": "1",
            "PYTHON": sys.executable,
            "SOCRATINK_LOOP_BOOT_TIMEOUT": "20",
        },
        clear=False,
    ):
        os.environ.pop("LOOP_BACKEND_URL", None)
        os.environ.pop("SOCRATINK_LOOP_DISABLE_LOCAL", None)
        original_service = main.app.state.auth_service
        main.app.state.auth_service = _GuestAuthService()
        try:
            start = client.post("/api/session", json={})
            assert start.status_code == 201
            session_id = start.json()["sessionId"]

            body = start.json()
            for text in turns:
                response = client.post(
                    f"/api/session/{session_id}/turn",
                    json={
                        "text": text,
                        "requestId": str(uuid.uuid4()),
                        "expectedVersion": body["sessionVersion"],
                    },
                )
                assert response.status_code == 200
                body = response.json()
                if body["caseComplete"]:
                    break
        finally:
            main.app.state.auth_service = original_service

    try:
        assert body["caseComplete"] is True
        assert body["record"]["derived"][0]["nodes"]["c1_s1"]["state"] == "primed"
    finally:
        loop_backend_proxy._stop_local_loop_backend()
