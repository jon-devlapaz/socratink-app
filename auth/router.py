from __future__ import annotations

from pathlib import Path
import logging
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from starlette.responses import FileResponse, JSONResponse, RedirectResponse, Response

from .service import AuthConfigurationError

auth_router = APIRouter()
_login_page = Path(__file__).resolve().parent.parent / "public" / "login.html"
logger = logging.getLogger(__name__)


class MagicAuthSendRequest(BaseModel):
    email: str = Field(..., max_length=320)


class MagicAuthVerifyRequest(BaseModel):
    email: str = Field(..., max_length=320)
    code: str = Field(..., min_length=6, max_length=12)
    return_to: str | None = Field(default="/", max_length=500)


def sanitize_return_to_path(return_to: str | None) -> str:
    if not return_to:
        return "/"
    candidate = return_to.strip()
    if not candidate.startswith("/"):
        return "/"
    if candidate.startswith("//"):
        return "/"
    return candidate


def _build_login_redirect(*, return_to: str | None = None, auth_error: str | None = None) -> str:
    query = {
        "return_to": sanitize_return_to_path(return_to),
    }
    if auth_error:
        query["auth_error"] = auth_error[:120]
    return f"/login?{urlencode(query)}"


def _get_auth_service(request: Request):
    service = getattr(request.app.state, "auth_service", None)
    if service is None:
        raise HTTPException(status_code=500, detail="Auth service is not configured.")
    return service


def _base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:100]
    if request.client and request.client.host:
        return request.client.host[:100]
    return None


def _user_agent(request: Request) -> str | None:
    raw = request.headers.get("user-agent")
    return raw[:500] if raw else None


def _apply_session_cookie(response: Response, request: Request, sealed_session: str) -> None:
    service = _get_auth_service(request)
    response.set_cookie(
        service.cookie_name,
        sealed_session,
        secure=service.resolve_cookie_secure(_base_url(request)),
        httponly=True,
        samesite=service.cookie_samesite,
        max_age=service.cookie_max_age,
        path="/",
    )


def _clear_session_cookie(response: Response, request: Request) -> None:
    service = _get_auth_service(request)
    response.delete_cookie(service.cookie_name, path="/")


def _apply_oauth_state_cookie(response: Response, request: Request, signed_state: str) -> None:
    service = _get_auth_service(request)
    response.set_cookie(
        service.oauth_state_cookie_name,
        signed_state,
        secure=service.resolve_cookie_secure(_base_url(request)),
        httponly=True,
        samesite=service.cookie_samesite,
        max_age=service.oauth_state_ttl_seconds,
        path="/",
    )


def _clear_oauth_state_cookie(response: Response, request: Request) -> None:
    service = _get_auth_service(request)
    response.delete_cookie(service.oauth_state_cookie_name, path="/")


@auth_router.get("/api/me")
def get_current_user(request: Request):
    service = _get_auth_service(request)
    state = service.load_session(request.cookies.get(service.cookie_name))
    response = JSONResponse(state.to_public_dict())
    if state.sealed_session:
        _apply_session_cookie(response, request, state.sealed_session)
    elif state.should_clear_cookie:
        _clear_session_cookie(response, request)
    return response


@auth_router.get("/login")
def login(request: Request, return_to: str | None = None):
    service = _get_auth_service(request)
    current = service.load_session(request.cookies.get(service.cookie_name))
    if current.authenticated:
        return RedirectResponse(url=sanitize_return_to_path(return_to), status_code=302)
    return FileResponse(_login_page)


@auth_router.get("/auth/google")
def auth_google(request: Request, return_to: str | None = None):
    service = _get_auth_service(request)
    sanitized_return_to = sanitize_return_to_path(return_to)
    try:
        state_nonce, signed_state = service.build_oauth_state(return_to=sanitized_return_to)
        authorization_url = service.get_login_url(
            base_url=_base_url(request),
            return_to=state_nonce,
            provider="GoogleOAuth",
        )
    except AuthConfigurationError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    response = RedirectResponse(url=authorization_url, status_code=302)
    _apply_oauth_state_cookie(response, request, signed_state)
    return response


@auth_router.get("/auth/callback")
def auth_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
):
    service = _get_auth_service(request)
    verified_return_to = service.verify_oauth_state(
        state=state,
        signed_cookie=request.cookies.get(service.oauth_state_cookie_name),
    )
    return_to = verified_return_to or "/"
    if error:
        logger.info("Auth callback returned error=%s description=%s", error, error_description)
        response = RedirectResponse(
            url=_build_login_redirect(return_to=return_to, auth_error=error),
            status_code=302,
        )
        _clear_oauth_state_cookie(response, request)
        return response
    if not code:
        response = RedirectResponse(
            url=_build_login_redirect(return_to=return_to, auth_error="missing_code"),
            status_code=302,
        )
        _clear_oauth_state_cookie(response, request)
        return response
    if verified_return_to is None:
        logger.warning("Auth callback failed state verification")
        response = RedirectResponse(
            url=_build_login_redirect(return_to="/", auth_error="invalid_state"),
            status_code=302,
        )
        _clear_oauth_state_cookie(response, request)
        return response
    try:
        auth_state = service.exchange_code(
            code=code,
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
        )
    except AuthConfigurationError as err:
        raise HTTPException(status_code=503, detail=str(err)) from err
    except Exception as err:
        logger.exception("Auth callback code exchange failed")
        response = RedirectResponse(
            url=_build_login_redirect(return_to=return_to, auth_error="authentication_failed"),
            status_code=302,
        )
        _clear_oauth_state_cookie(response, request)
        return response

    response = RedirectResponse(url=return_to, status_code=302)
    if auth_state.sealed_session:
        _apply_session_cookie(response, request, auth_state.sealed_session)
    _clear_oauth_state_cookie(response, request)
    return response


@auth_router.post("/api/auth/logout")
def logout(request: Request):
    service = _get_auth_service(request)
    service.logout(request.cookies.get(service.cookie_name))
    response = JSONResponse({"ok": True, "auth_enabled": service.enabled})
    _clear_session_cookie(response, request)
    return response


@auth_router.post("/api/auth/magic-auth/send")
def send_magic_auth(request: Request, body: MagicAuthSendRequest):
    raise HTTPException(status_code=503, detail="Email sign-in is not enabled in this release.")


@auth_router.post("/api/auth/magic-auth/verify")
def verify_magic_auth(request: Request, body: MagicAuthVerifyRequest):
    raise HTTPException(status_code=503, detail="Email sign-in is not enabled in this release.")
