"""Proxy loop-backend routes.

Uses LOOP_BACKEND_URL when configured. Otherwise starts the vendored loop
runtime from this repo and proxies to it over loopback.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import atexit
from pathlib import Path
from typing import Mapping
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


def _vercel_internal_loop_base(request: Request) -> str | None:
    if not force_vercel_internal_loop():
        return None
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    if not host:
        return None
    proto = request.headers.get("x-forwarded-proto") or "https"
    return f"{proto}://{host}/api/internal-loop"


def force_vercel_internal_loop() -> bool:
    return bool(os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"))


def _loop_backend_base(
    *,
    request: Request,
    force_local_runtime: bool = False,
) -> tuple[str, bool]:
    if force_local_runtime:
        internal_base = _vercel_internal_loop_base(request)
        if internal_base:
            return internal_base, True
    base = os.environ.get("LOOP_BACKEND_URL", "").strip().rstrip("/")
    if base and not force_local_runtime:
        return base, False
    if os.environ.get("SOCRATINK_LOOP_DISABLE_LOCAL") == "1":
        raise HTTPException(
            status_code=503,
            detail="Loop backend is not configured for this deployment.",
        )
    return _start_local_loop_backend(), False


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


def _internal_loop_token() -> str:
    return (
        os.environ.get("SOCRATINK_LOOP_API_KEY", "").strip()
        or os.environ.get("SESSION_COOKIE_KEY", "").strip()
    )


def _forward_headers(request: Request, *, internal_loop: bool = False) -> dict[str, str]:
    headers: dict[str, str] = {}
    for key, value in request.headers.items():
        lowered = key.lower()
        if lowered in _REQUEST_HEADER_ALLOWLIST:
            headers[key] = value
    if internal_loop:
        token = _internal_loop_token()
        if token:
            headers["X-Socratink-Internal-Loop-Token"] = token
        return headers
    api_key = os.environ.get("SOCRATINK_LOOP_API_KEY", "").strip()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _response_headers(upstream: Mapping[str, str]) -> dict[str, str]:
    return {
        key: value
        for key, value in upstream.items()
        if key.lower() not in _RESPONSE_HEADER_DENYLIST
    }


async def proxy_loop_backend(
    request: Request,
    upstream_path: str,
    *,
    force_local_runtime: bool = False,
) -> Response:
    try:
        base, internal_loop = _loop_backend_base(
            request=request,
            force_local_runtime=force_local_runtime,
        )
    except HTTPException as err:
        return _loop_unavailable_response(request, err)
    query = f"?{request.url.query}" if request.url.query else ""
    url = f"{base}{upstream_path}{query}"
    body = await request.body()
    try:
        upstream = _POOL.request(
            request.method,
            url,
            body=body or None,
            headers=_forward_headers(request, internal_loop=internal_loop),
            redirect=False,
            preload_content=False,
        )
    except urllib3.exceptions.HTTPError as err:
        raise HTTPException(
            status_code=502,
            detail="Loop backend request failed.",
        ) from err
    try:
        payload = upstream.read()
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
