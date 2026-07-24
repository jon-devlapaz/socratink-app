from __future__ import annotations

from pathlib import Path
import logging
import os
from typing import Literal, cast
from urllib.parse import parse_qs, urlencode, urlsplit

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from runtime_env import dev_autoguest_enabled, local_auth_bypass_enabled

from .service import AuthConfigurationError, AuthSessionState, SupabaseAuthService

auth_router = APIRouter()
_login_assets = Path(__file__).resolve().parent / "login_assets"
_login_css = _login_assets / "login.css"
_login_js = _login_assets / "login.js"
_login_html = _login_assets / "login.html"
logger = logging.getLogger(__name__)
GUEST_COOKIE_NAME = "socratink_guest"

_LOGIN_CSS_MARKER = "<!-- socratink-login-css -->"
_LOGIN_JS_MARKER = "<!-- socratink-login-js -->"


def _read_login_asset(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        logger.exception("Required login asset is unavailable at %s", path)
        raise


def _inline_login_assets(html: str, css: str, js: str) -> str:
    replacements = (
        (_LOGIN_CSS_MARKER, f"<style>{css}</style>"),
        (_LOGIN_JS_MARKER, f'<script type="module">{js}</script>'),
    )
    for marker, replacement in replacements:
        if html.count(marker) != 1:
            raise RuntimeError(
                f"Login template must contain exactly one {marker.strip()} marker."
            )
        html = html.replace(marker, replacement, 1)
    return html


def _render_login_html() -> str:
    return _inline_login_assets(
        _read_login_asset(_login_html),
        _read_login_asset(_login_css),
        _read_login_asset(_login_js),
    )


def sanitize_return_to_path(return_to: str | None) -> str:
    if not return_to:
        return "/"
    candidate = return_to.strip()
    if not candidate.startswith("/"):
        return "/"
    if candidate.startswith("//"):
        return "/"
    return candidate


def _build_login_redirect(
    *, return_to: str | None = None, auth_error: str | None = None
) -> str:
    query = {
        "return_to": sanitize_return_to_path(return_to),
    }
    if auth_error:
        query["auth_error"] = auth_error[:120]
    return f"/login?{urlencode(query)}"


def _query_has_auth_error(query: str) -> bool:
    return "auth_error" in parse_qs(query, keep_blank_values=True)


def _login_request_has_auth_error(
    request: Request, sanitized_return_to: str
) -> bool:
    return _query_has_auth_error(request.url.query) or _query_has_auth_error(
        urlsplit(sanitized_return_to).query
    )


def _get_auth_service(request: Request) -> SupabaseAuthService:
    service = cast(
        SupabaseAuthService | None,
        getattr(request.app.state, "auth_service", None),
    )
    if service is None:
        raise HTTPException(status_code=500, detail="Auth service is not configured.")
    return service


def _base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


def _apply_session_cookie(
    response: Response, request: Request, sealed_session: str
) -> None:
    service = _get_auth_service(request)
    response.set_cookie(
        service.cookie_name,
        sealed_session,
        secure=service.resolve_cookie_secure(_base_url(request)),
        httponly=True,
        samesite=cast(Literal["lax", "strict", "none"], service.cookie_samesite),
        max_age=service.cookie_max_age,
        path="/",
    )


def _clear_session_cookie(response: Response, request: Request) -> None:
    service = _get_auth_service(request)
    response.delete_cookie(service.cookie_name, path="/")


def _apply_oauth_state_cookie(
    response: Response, request: Request, signed_state: str
) -> None:
    service = _get_auth_service(request)
    response.set_cookie(
        service.oauth_state_cookie_name,
        signed_state,
        secure=service.resolve_cookie_secure(_base_url(request)),
        httponly=True,
        samesite="lax",
        max_age=service.oauth_state_ttl_seconds,
        path="/",
    )


def _clear_oauth_state_cookie(response: Response, request: Request) -> None:
    service = _get_auth_service(request)
    response.delete_cookie(service.oauth_state_cookie_name, path="/")


def _local_e2e_guest_bootstrap_enabled(request: Request) -> bool:
    if os.getenv("SOCRATINK_E2E_LOCAL_GUEST", "").strip().lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return False
    client_host = request.client.host if request.client else ""
    if client_host not in {"127.0.0.1", "::1", "testclient"}:
        return False
    if dev_autoguest_enabled():
        return True
    return (
        os.getenv("GITHUB_ACTIONS", "").strip().lower() == "true"
        and os.getenv("VERCEL", "").strip().lower() not in {"1", "true", "yes", "on"}
        and not os.getenv("VERCEL_ENV")
    )


def _local_dev_guest_bootstrap_enabled(request: Request) -> bool:
    client_host = request.client.host if request.client else ""
    return local_auth_bypass_enabled(
        hostname=request.url.hostname,
        client_host=client_host,
    )


def load_current_session_state(request: Request) -> AuthSessionState:
    service = _get_auth_service(request)
    sealed_session = request.cookies.get(service.cookie_name)
    try:
        state = service.load_session(sealed_session)
    except AuthConfigurationError:
        logger.warning("Auth session load failed because auth is not configured.")
        state = AuthSessionState(
            auth_enabled=service.enabled,
            authenticated=False,
            should_clear_cookie=bool(sealed_session),
            error_reason="auth_unavailable",
        )
    except Exception:
        logger.exception("Auth session load failed unexpectedly.")
        state = AuthSessionState(
            auth_enabled=service.enabled,
            authenticated=False,
            should_clear_cookie=bool(sealed_session),
            error_reason="auth_session_unavailable",
        )
    return state


@auth_router.get("/api/me")
def get_current_user(request: Request) -> Response:
    state = load_current_session_state(request)
    payload = state.to_public_dict()
    payload["loop_available"] = bool(os.environ.get("LOOP_BACKEND_URL", "").strip())
    client_host = request.client.host if request.client else None
    payload["dev_mode"] = local_auth_bypass_enabled(
        hostname=request.url.hostname,
        client_host=client_host,
    )
    response = JSONResponse(payload)
    if state.sealed_session:
        _apply_session_cookie(response, request, state.sealed_session)
    elif state.should_clear_cookie:
        _clear_session_cookie(response, request)
    return response


@auth_router.get("/login")
def login(request: Request, return_to: str | None = None) -> Response:
    current = load_current_session_state(request)
    sanitized_return_to = sanitize_return_to_path(return_to)
    if current.authenticated and not current.guest_mode:
        response: Response = RedirectResponse(url=sanitized_return_to, status_code=302)
    elif (
        not current.authenticated
        and _local_dev_guest_bootstrap_enabled(request)
        and not _login_request_has_auth_error(request, sanitized_return_to)
    ):
        response = RedirectResponse(
            url=f"/auth/guest?{urlencode({'return_to': sanitized_return_to})}",
            status_code=302,
        )
    else:
        response = HTMLResponse(_render_login_html())
    if current.should_clear_cookie:
        _clear_session_cookie(response, request)
    return response


@auth_router.get("/auth/guest")
def auth_guest(request: Request, return_to: str | None = None) -> Response:
    service = _get_auth_service(request)
    sanitized_return_to = sanitize_return_to_path(return_to)

    def local_dev_guest_response() -> Response | None:
        if not _local_dev_guest_bootstrap_enabled(request):
            return None
        try:
            local_state = service.build_local_dev_guest_session()
        except AuthConfigurationError as err:
            logger.warning("Local dev guest bootstrap failed (config): %s", err)
            return None
        if not local_state.sealed_session:
            logger.warning("Local dev guest bootstrap did not return a sealed session")
            return None
        response = RedirectResponse(url=sanitized_return_to, status_code=302)
        _apply_session_cookie(response, request, local_state.sealed_session)
        response.delete_cookie(GUEST_COOKIE_NAME, path="/")
        return response

    local_response = local_dev_guest_response()
    if local_response is not None:
        return local_response

    try:
        auth_state = service.sign_in_anonymously()
    except AuthConfigurationError as err:
        logger.warning("Anonymous sign-in failed (config): %s", err)
        local_response = local_dev_guest_response()
        if local_response is not None:
            return local_response
        return RedirectResponse(
            url=_build_login_redirect(
                return_to=sanitized_return_to,
                auth_error="guest_unavailable",
            ),
            status_code=302,
        )
    except Exception:
        logger.exception("Anonymous sign-in failed unexpectedly")
        local_response = local_dev_guest_response()
        if local_response is not None:
            return local_response
        return RedirectResponse(
            url=_build_login_redirect(
                return_to=sanitized_return_to,
                auth_error="authentication_failed",
            ),
            status_code=302,
        )

    response = RedirectResponse(url=sanitized_return_to, status_code=302)
    if (
        not auth_state.authenticated
        or not auth_state.guest_mode
        or not auth_state.sealed_session
    ):
        logger.warning("Anonymous sign-in did not return a guest session")
        local_response = local_dev_guest_response()
        if local_response is not None:
            return local_response
        return RedirectResponse(
            url=_build_login_redirect(
                return_to=sanitized_return_to,
                auth_error="authentication_failed",
            ),
            status_code=302,
        )
    _apply_session_cookie(response, request, auth_state.sealed_session)
    response.delete_cookie(GUEST_COOKIE_NAME, path="/")
    return response


@auth_router.get("/auth/e2e/guest")
def auth_e2e_guest(request: Request, return_to: str | None = None) -> Response:
    if not _local_e2e_guest_bootstrap_enabled(request):
        raise HTTPException(status_code=404, detail="Not found")

    service = _get_auth_service(request)
    sanitized_return_to = sanitize_return_to_path(return_to)
    try:
        auth_state = service.build_local_e2e_guest_session()
    except AuthConfigurationError as err:
        logger.warning("Local e2e guest bootstrap failed (config): %s", err)
        return RedirectResponse(
            url=_build_login_redirect(
                return_to=sanitized_return_to,
                auth_error="guest_unavailable",
            ),
            status_code=302,
        )

    if not auth_state.sealed_session:
        logger.warning("Local e2e guest bootstrap did not return a sealed session")
        return RedirectResponse(
            url=_build_login_redirect(
                return_to=sanitized_return_to,
                auth_error="authentication_failed",
            ),
            status_code=302,
        )

    response = RedirectResponse(url=sanitized_return_to, status_code=302)
    _apply_session_cookie(response, request, auth_state.sealed_session)
    response.delete_cookie(GUEST_COOKIE_NAME, path="/")
    return response


@auth_router.get("/auth/google")
def auth_google(request: Request, return_to: str | None = None) -> Response:
    service = _get_auth_service(request)
    sanitized_return_to = sanitize_return_to_path(return_to)
    try:
        _verifier, challenge, signed_state = service.build_oauth_state(
            return_to=sanitized_return_to
        )
        authorization_url = service.get_login_url(code_challenge=challenge)
    except AuthConfigurationError as err:
        logger.warning("Google auth start failed: %s", err)
        return RedirectResponse(
            url=_build_login_redirect(
                return_to=sanitized_return_to,
                auth_error="authentication_unavailable",
            ),
            status_code=302,
        )
    response = RedirectResponse(url=authorization_url, status_code=302)
    _apply_oauth_state_cookie(response, request, signed_state)
    return response


@auth_router.get("/auth/callback")
def auth_callback(
    request: Request,
    code: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
) -> Response:
    service = _get_auth_service(request)
    verified = service.verify_oauth_state(
        signed_cookie=request.cookies.get(service.oauth_state_cookie_name),
    )
    return_to = verified[0] if verified else "/"
    if error:
        logger.info(
            "Auth callback returned error=%s description=%s", error, error_description
        )
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
    if verified is None:
        logger.warning("Auth callback failed state verification")
        response = RedirectResponse(
            url=_build_login_redirect(return_to="/", auth_error="invalid_state"),
            status_code=302,
        )
        _clear_oauth_state_cookie(response, request)
        return response
    return_to, code_verifier = verified
    try:
        auth_state = service.exchange_code(
            code=code,
            code_verifier=code_verifier,
            redirect_uri=service.callback_redirect_uri(),
        )
    except AuthConfigurationError as err:
        logger.warning("Auth callback configuration failed: %s", err)
        response = RedirectResponse(
            url=_build_login_redirect(
                return_to=return_to,
                auth_error="authentication_unavailable",
            ),
            status_code=302,
        )
        _clear_oauth_state_cookie(response, request)
        return response
    except Exception:
        logger.exception("Auth callback code exchange failed")
        response = RedirectResponse(
            url=_build_login_redirect(
                return_to=return_to, auth_error="authentication_failed"
            ),
            status_code=302,
        )
        _clear_oauth_state_cookie(response, request)
        return response

    if not auth_state.authenticated or not auth_state.sealed_session:
        logger.warning("Auth callback returned unauthenticated state")
        response = RedirectResponse(
            url=_build_login_redirect(
                return_to=return_to, auth_error="authentication_failed"
            ),
            status_code=302,
        )
        _clear_oauth_state_cookie(response, request)
        return response

    response = RedirectResponse(url=return_to, status_code=302)
    _apply_session_cookie(response, request, auth_state.sealed_session)
    response.delete_cookie(GUEST_COOKIE_NAME, path="/")
    _clear_oauth_state_cookie(response, request)
    return response


@auth_router.post("/api/auth/logout")
def logout(request: Request) -> Response:
    service = _get_auth_service(request)
    service.logout(request.cookies.get(service.cookie_name))
    response = JSONResponse({"ok": True, "auth_enabled": service.enabled})
    _clear_session_cookie(response, request)
    response.delete_cookie(GUEST_COOKIE_NAME, path="/")
    return response
