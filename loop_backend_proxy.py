"""Proxy loop-backend routes using LOOP_BACKEND_URL (preview-safe)."""

from __future__ import annotations

import os
from typing import Mapping
import urllib3
from fastapi import HTTPException, Request
from starlette.responses import Response

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

_POOL = urllib3.PoolManager()


def _loop_backend_base() -> str:
    base = os.environ.get("LOOP_BACKEND_URL", "").strip().rstrip("/")
    if not base:
        raise HTTPException(
            status_code=503,
            detail="Loop backend is not configured for this deployment.",
        )
    return base


def _forward_headers(request: Request) -> dict[str, str]:
    headers: dict[str, str] = {}
    for key, value in request.headers.items():
        lowered = key.lower()
        if lowered in _HOP_BY_HOP:
            continue
        headers[key] = value
    return headers


def _response_headers(upstream: Mapping[str, str]) -> dict[str, str]:
    return {
        key: value
        for key, value in upstream.items()
        if key.lower() not in _HOP_BY_HOP
    }


async def proxy_loop_backend(request: Request, upstream_path: str) -> Response:
    base = _loop_backend_base()
    query = f"?{request.url.query}" if request.url.query else ""
    url = f"{base}{upstream_path}{query}"
    body = await request.body()
    try:
        upstream = _POOL.request(
            request.method,
            url,
            body=body or None,
            headers=_forward_headers(request),
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
