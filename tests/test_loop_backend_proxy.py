"""Tests for loop-backend proxy routes."""

from __future__ import annotations

import os
import shutil
import sys
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
    upstream.release_conn.assert_called_once()


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
                    json={"text": text},
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
