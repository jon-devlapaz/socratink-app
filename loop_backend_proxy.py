"""Proxy loop-backend routes.

Uses LOOP_BACKEND_URL when configured. Otherwise starts the vendored loop
runtime from this repo and proxies to it over loopback.
"""

from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import sys
import time
import atexit
from pathlib import Path
from typing import Mapping
from urllib.parse import urlsplit
import urllib3
from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, Response

_HOP_BY_HOP = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
        "host",
        "content-length",
    }
)

_REQUEST_HEADER_ALLOWLIST = {"accept", "content-type"}
_RESPONSE_HEADER_DENYLIST = _HOP_BY_HOP | {"content-encoding"}

_POOL = urllib3.PoolManager()
_LOOP_PROXY_TIMEOUT = urllib3.Timeout(connect=5.0, read=55.0)
_MAX_LOOP_REQUEST_BODY_BYTES = 64 * 1024
_REPO_ROOT = Path(__file__).resolve().parent
_LOCAL_LOOP_PROCESS: subprocess.Popen | None = None
_LOCAL_LOOP_BASE: str | None = None


def _stop_local_loop_backend() -> None:
    global _LOCAL_LOOP_BASE, _LOCAL_LOOP_PROCESS
    process = _LOCAL_LOOP_PROCESS
    _LOCAL_LOOP_PROCESS = None
    _LOCAL_LOOP_BASE = None
    if process and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)


atexit.register(_stop_local_loop_backend)


def _free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _local_loop_env(port: int) -> dict[str, str]:
    env = os.environ.copy()
    env["PORT"] = str(port)
    env["HOST"] = "127.0.0.1"
    env.setdefault("PYTHON", sys.executable)
    return env


def _start_local_loop_backend() -> str:
    global _LOCAL_LOOP_BASE, _LOCAL_LOOP_PROCESS
    if _LOCAL_LOOP_PROCESS and _LOCAL_LOOP_PROCESS.poll() is None and _LOCAL_LOOP_BASE:
        return _LOCAL_LOOP_BASE

    server = _REPO_ROOT / "loop-server.mjs"
    if not server.exists():
        raise HTTPException(
            status_code=503,
            detail="Vendored loop runtime is missing.",
        )

    port = _free_loopback_port()
    base = f"http://127.0.0.1:{port}"
    try:
        _LOCAL_LOOP_PROCESS = subprocess.Popen(
            ["node", "--no-warnings", str(server)],
            cwd=_REPO_ROOT,
            env=_local_loop_env(port),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as err:
        raise HTTPException(
            status_code=503,
            detail="Vendored loop runtime could not start.",
        ) from err
    _LOCAL_LOOP_BASE = base

    deadline = time.monotonic() + float(os.environ.get("SOCRATINK_LOOP_BOOT_TIMEOUT", "10"))
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if _LOCAL_LOOP_PROCESS.poll() is not None:
            raise HTTPException(
                status_code=503,
                detail="Vendored loop runtime exited during startup.",
            )
        try:
            health = _POOL.request(
                "GET",
                f"{base}/health",
                timeout=urllib3.Timeout(connect=0.2, read=0.5),
            )
            if health.status == 200:
                return base
        except urllib3.exceptions.HTTPError as err:
            last_error = err
        time.sleep(0.1)

    _LOCAL_LOOP_PROCESS.terminate()
    raise HTTPException(
        status_code=503,
        detail="Vendored loop runtime did not become ready.",
    ) from last_error


def is_vercel_runtime() -> bool:
    return bool(os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"))


def _validated_hosted_loop_base(raw_base: str) -> str:
    base = raw_base.strip().rstrip("/")
    parsed = urlsplit(base)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise HTTPException(
            status_code=503,
            detail="Hosted loop backend must be a trusted HTTPS origin.",
        )
    return base


def _loop_backend_base(
    *,
    request: Request,
    force_local_runtime: bool = False,
) -> str:
    if force_local_runtime:
        if is_vercel_runtime():
            hosted_base = os.environ.get("LOOP_BACKEND_URL", "").strip()
            if not hosted_base or not os.environ.get("SOCRATINK_LOOP_API_KEY", "").strip():
                raise HTTPException(
                    status_code=503,
                    detail="Hosted loop backend is not configured.",
                )
            return _validated_hosted_loop_base(hosted_base)
        return _start_local_loop_backend()
    base = os.environ.get("LOOP_BACKEND_URL", "").strip().rstrip("/")
    if base:
        return base
    if os.environ.get("SOCRATINK_LOOP_DISABLE_LOCAL") == "1":
        raise HTTPException(
            status_code=503,
            detail="Loop backend is not configured for this deployment.",
        )
    return _start_local_loop_backend()


def _loop_unavailable_response(request: Request, err: HTTPException) -> Response:
    accepts_html = "text/html" in request.headers.get("accept", "")
    if not accepts_html or request.url.path != "/loop":
        raise err
    return HTMLResponse(
        """
        <!doctype html>
        <html lang="en">
          <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>socratink loop unavailable</title>
            <style>
              body {
                min-height: 100vh;
                margin: 0;
                display: grid;
                place-items: center;
                background: #f7ece1;
                color: #242038;
                font: 16px/1.5 Inter, system-ui, sans-serif;
              }
              main {
                max-width: 34rem;
                padding: 2rem;
              }
              h1 {
                margin: 0 0 0.75rem;
                font-size: clamp(2rem, 7vw, 4rem);
                line-height: 0.95;
              }
              p { margin: 0 0 1rem; color: rgba(36, 32, 56, 0.74); }
              a { color: #5f4bb6; font-weight: 700; }
            </style>
          </head>
          <body>
            <main>
              <h1>Learning loop unavailable</h1>
              <p>This preview is not connected to the loop backend right now.</p>
              <a href="/">Return to socratink</a>
            </main>
          </body>
        </html>
        """,
        status_code=503,
    )


def _forward_headers(
    request: Request,
    *,
    include_user_token: bool = False,
) -> dict[str, str]:
    headers: dict[str, str] = {}
    for key, value in request.headers.items():
        lowered = key.lower()
        if lowered in _REQUEST_HEADER_ALLOWLIST:
            headers[key] = value
    api_key = os.environ.get("SOCRATINK_LOOP_API_KEY", "").strip()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if include_user_token:
        session = getattr(request.state, "auth_session", None)
        user_access_token = getattr(session, "access_token", None)
        if not user_access_token:
            raise HTTPException(
                status_code=401,
                detail="Authenticated session required for durable loop storage.",
            )
        headers["X-Socratink-User-Access-Token"] = user_access_token
    return headers


def _response_headers(upstream: Mapping[str, str]) -> dict[str, str]:
    return {
        key: value
        for key, value in upstream.items()
        if key.lower() not in _RESPONSE_HEADER_DENYLIST
    }


async def _bounded_request_body(request: Request) -> bytes:
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > _MAX_LOOP_REQUEST_BODY_BYTES:
                raise HTTPException(status_code=413, detail="Loop request body is too large.")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Content-Length header.")

    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > _MAX_LOOP_REQUEST_BODY_BYTES:
            raise HTTPException(status_code=413, detail="Loop request body is too large.")
        chunks.append(chunk)
    return b"".join(chunks)


async def proxy_loop_backend(
    request: Request,
    upstream_path: str,
    *,
    force_local_runtime: bool = False,
) -> Response:
    try:
        base = _loop_backend_base(
            request=request,
            force_local_runtime=force_local_runtime,
        )
    except HTTPException as err:
        return _loop_unavailable_response(request, err)
    query = f"?{request.url.query}" if request.url.query else ""
    url = f"{base}{upstream_path}{query}"
    body = await _bounded_request_body(request)
    try:
        upstream = await asyncio.to_thread(
            _POOL.request,
            request.method,
            url,
            body=body or None,
            headers=_forward_headers(
                request,
                include_user_token=(
                    force_local_runtime and is_vercel_runtime()
                ),
            ),
            redirect=False,
            preload_content=False,
            retries=False,
            timeout=_LOOP_PROXY_TIMEOUT,
        )
    except urllib3.exceptions.TimeoutError as err:
        raise HTTPException(
            status_code=503,
            detail="Loop backend request timed out.",
        ) from err
    except urllib3.exceptions.HTTPError as err:
        raise HTTPException(
            status_code=502,
            detail="Loop backend request failed.",
        ) from err
    try:
        payload = await asyncio.to_thread(upstream.read)
    except urllib3.exceptions.TimeoutError as err:
        raise HTTPException(
            status_code=503,
            detail="Loop backend response timed out.",
        ) from err
    except urllib3.exceptions.HTTPError as err:
        raise HTTPException(
            status_code=502,
            detail="Loop backend response read failed.",
        ) from err
    finally:
        upstream.release_conn()
    return Response(
        content=payload,
        status_code=upstream.status,
        headers=_response_headers(upstream.headers),
        media_type=upstream.headers.get("content-type"),
    )
