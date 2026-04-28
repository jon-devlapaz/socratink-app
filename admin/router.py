"""Admin Surface router — /admin/todo dashboard for the Tink TODO file.

Dev-only Route. The router is included into the FastAPI app only when:
    1. The runtime appears to be local dev (APP_BASE_URL points at localhost
       or 127.0.0.1, or is unset).
    2. The Tink TODO file is readable on disk.

Even when included, every handler also runs the Admin Gate (single-user
email allowlist). Any failure path returns 404 to avoid leaking the
existence of the Admin Surface to non-admins.
"""

from __future__ import annotations

import logging
import os
import tempfile
from datetime import date
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel
from starlette.responses import HTMLResponse, JSONResponse

from auth import load_current_session_state
from .static import ADMIN_TODO_HTML
from .todo_parser import (
    edit_item_body,
    move_item,
    parse_tink_todo,
    toggle_item,
)

logger = logging.getLogger(__name__)

ADMIN_EMAIL = "jonathan10620@gmail.com"
# Default path for local dev, but configurable for other environments.
DEFAULT_TODO_PATH = "/Users/jondev/dev/socratink/todo.md"
TINK_TODO_PATH = Path(os.getenv("TINK_TODO_PATH", DEFAULT_TODO_PATH))

admin_router = APIRouter()


def _is_dev_environment() -> bool:
    """Return True if this process should expose the Admin Surface.

    Safe against missing or empty APP_BASE_URL. Localhost and 127.0.0.1 are
    treated as equivalent (matches how the codebase handles CORS_ORIGINS).
    """
    base = (os.getenv("APP_BASE_URL") or "").strip().lower()
    if not base:
        # In tests and bare-uvicorn runs we usually have no APP_BASE_URL.
        # Permissive default: assume dev. The handler-level Admin Gate is
        # the load-bearing security control, not registration.
        return True
    if base.startswith("http://localhost"):
        return True
    if base.startswith("http://127.0.0.1"):
        return True
    return False


def _require_admin(request: Request) -> None:
    """Admin Gate. Raises HTTPException(404) on any non-admin path."""
    state = load_current_session_state(request)
    if not state.authenticated:
        raise HTTPException(status_code=404)
    user = state.user
    if user is None or not user.email or user.email.lower() != ADMIN_EMAIL.lower():
        raise HTTPException(status_code=404)


def _read_todo() -> tuple[str, float]:
    if not TINK_TODO_PATH.exists():
        raise HTTPException(status_code=404)
    text = TINK_TODO_PATH.read_text(encoding="utf-8")
    mtime = TINK_TODO_PATH.stat().st_mtime
    return text, mtime


def _atomic_write_todo(text: str) -> float:
    parent = TINK_TODO_PATH.parent
    fd, tmp_path = tempfile.mkstemp(prefix=".todo.", suffix=".tmp", dir=str(parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp_path, TINK_TODO_PATH)
    except Exception:
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass
        raise
    return TINK_TODO_PATH.stat().st_mtime


def _payload(text: str, mtime: float) -> dict:
    doc = parse_tink_todo(text)
    out = doc.public_dict()
    out["mtime"] = mtime
    return out


class ToggleRequest(BaseModel):
    line_index: int
    expected_mtime: float | None = None


class MoveRequest(BaseModel):
    line_index: int
    target_bucket_line: int
    after_item_line: int | None = None
    expected_mtime: float | None = None


class EditRequest(BaseModel):
    line_index: int
    new_body: str
    expected_mtime: float | None = None


@admin_router.get("/admin/todo", response_class=HTMLResponse)
def admin_todo_page(request: Request):
    _require_admin(request)
    html = ADMIN_TODO_HTML.replace("{{TINK_TODO_PATH}}", str(TINK_TODO_PATH))
    return HTMLResponse(html)


@admin_router.get("/api/admin/todo")
def admin_todo_data(request: Request):
    _require_admin(request)
    text, mtime = _read_todo()
    return JSONResponse(_payload(text, mtime))


@admin_router.get("/api/admin/todo/mtime")
def admin_todo_mtime(request: Request):
    _require_admin(request)
    if not TINK_TODO_PATH.exists():
        raise HTTPException(status_code=404)
    return JSONResponse({"mtime": TINK_TODO_PATH.stat().st_mtime})


@admin_router.patch("/api/admin/todo/toggle")
def admin_todo_toggle(payload: ToggleRequest, request: Request):
    _require_admin(request)
    text, mtime = _read_todo()
    if payload.expected_mtime is not None and abs(payload.expected_mtime - mtime) > 1e-3:
        raise HTTPException(status_code=409, detail="file changed on disk")
    doc = parse_tink_todo(text)
    if payload.line_index not in doc.items:
        raise HTTPException(status_code=422, detail="line is not a TODO Item")
    toggle_item(doc, payload.line_index, today=date.today())
    new_text = doc.serialize()
    new_mtime = _atomic_write_todo(new_text)
    return JSONResponse(_payload(new_text, new_mtime))


@admin_router.patch("/api/admin/todo/edit")
def admin_todo_edit(payload: EditRequest, request: Request):
    _require_admin(request)
    text, mtime = _read_todo()
    if payload.expected_mtime is not None and abs(payload.expected_mtime - mtime) > 1e-3:
        raise HTTPException(status_code=409, detail="file changed on disk")
    doc = parse_tink_todo(text)
    if payload.line_index not in doc.items:
        raise HTTPException(status_code=422, detail="line is not a TODO Item")
    try:
        edit_item_body(doc, payload.line_index, payload.new_body)
    except ValueError as err:
        raise HTTPException(status_code=422, detail=str(err))
    new_text = doc.serialize()
    new_mtime = _atomic_write_todo(new_text)
    return JSONResponse(_payload(new_text, new_mtime))


@admin_router.patch("/api/admin/todo/move")
def admin_todo_move(payload: MoveRequest, request: Request):
    _require_admin(request)
    text, mtime = _read_todo()
    if payload.expected_mtime is not None and abs(payload.expected_mtime - mtime) > 1e-3:
        raise HTTPException(status_code=409, detail="file changed on disk")
    doc = parse_tink_todo(text)
    try:
        move_item(
            doc,
            line_index=payload.line_index,
            target_bucket_line=payload.target_bucket_line,
            after_item_line=payload.after_item_line,
        )
    except ValueError as err:
        raise HTTPException(status_code=422, detail=str(err))
    except KeyError as err:
        raise HTTPException(status_code=422, detail=str(err))
    new_text = doc.serialize()
    new_mtime = _atomic_write_todo(new_text)
    return JSONResponse(_payload(new_text, new_mtime))


def register_admin_router(app: FastAPI) -> bool:
    """Include admin_router into `app` IFF dev-environment + Tink TODO file exists.

    Must be called BEFORE any catch-all StaticFiles mount. Returns True if
    the router was registered, False otherwise (caller may log the skip).
    """
    if not _is_dev_environment():
        logger.info("admin: skipping registration — not a dev environment")
        return False
    if not TINK_TODO_PATH.exists():
        logger.info("admin: skipping registration — Tink TODO not found at %s", TINK_TODO_PATH)
        return False
    app.include_router(admin_router)
    logger.info("admin: /admin/todo registered (Tink TODO at %s)", TINK_TODO_PATH)
    return True
