"""Tests for loop-backend proxy routes."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture
def client() -> TestClient:
    return TestClient(main.app)


def test_loop_proxy_returns_503_when_backend_unconfigured(client: TestClient) -> None:
    with patch.dict("os.environ", {}, clear=False):
        import os

        os.environ.pop("LOOP_BACKEND_URL", None)
        response = client.get("/loop")
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_loop_proxy_forwards_to_configured_backend(client: TestClient) -> None:
    upstream = MagicMock()
    upstream.status = 200
    upstream.headers = {"content-type": "text/html"}
    upstream.read.return_value = b"<p>loop</p>"
    upstream.release_conn = MagicMock()

    with (
        patch.dict("os.environ", {"LOOP_BACKEND_URL": "https://loop.example"}, clear=False),
        patch("loop_backend_proxy._POOL.request", return_value=upstream) as request,
    ):
        response = client.get("/loop", params={"q": "1"})

    assert response.status_code == 200
    assert response.text == "<p>loop</p>"
    request.assert_called_once()
    assert request.call_args[0][1] == "https://loop.example/loop?q=1"
