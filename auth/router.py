from __future__ import annotations

from pathlib import Path
import logging
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from .service import AuthConfigurationError, AuthSessionState

auth_router = APIRouter()
_login_css = Path(__file__).resolve().parent.parent / "public" / "css" / "login.css"
_login_js = Path(__file__).resolve().parent.parent / "public" / "js" / "login.js"
logger = logging.getLogger(__name__)
GUEST_COOKIE_NAME = "socratink_guest"
GUEST_COOKIE_VALUE = "guest"


_EMBEDDED_LOGIN_CSS = """
:root {
  --surface: #fdf9f5;
  --surface-low: #f7f3ef;
  --surface-high: #ebe7e4;
  --surface-card: rgba(255, 255, 255, 0.76);
  --primary: #63469d;
  --primary-strong: #7c5fb8;
  --secondary: #68548d;
  --text: #1c1c19;
  --text-muted: #7b7582;
  --text-soft: #494551;
  --outline-soft: rgba(203, 196, 210, 0.9);
  --shadow-card: 0 8px 32px rgba(28, 28, 25, 0.06);
  --radius-card: 24px;
  --radius-pill: 999px;
}
* { box-sizing: border-box; }
html, body { margin: 0; min-height: 100%; }
body {
  position: relative;
  overflow: hidden;
  min-height: 100vh;
  background:
    radial-gradient(circle at 14% 18%, rgba(210, 187, 255, 0.34), transparent 26%),
    radial-gradient(circle at 88% 86%, rgba(210, 187, 255, 0.26), transparent 24%),
    linear-gradient(180deg, rgba(253, 249, 245, 0.98), rgba(249, 244, 239, 0.96));
  color: var(--text);
  font-family: Inter, sans-serif;
}
a { color: inherit; text-decoration: none; }
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
#stardust-container {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 1;
}
.star {
  position: absolute;
  border-radius: 50%;
  background: rgba(107, 78, 166, 0.34);
  animation: twinkle var(--duration) ease-in-out infinite;
}
@keyframes twinkle {
  0%, 100% { opacity: 0.18; transform: scale(1); }
  50% { opacity: 0.62; transform: scale(1.16); }
}
.aurora {
  position: absolute;
  border-radius: 999px;
  filter: blur(72px);
  opacity: 0.18;
  pointer-events: none;
  z-index: 0;
  transition: transform 160ms cubic-bezier(0.1, 0, 0.3, 1);
}
.aurora-a {
  top: -120px;
  left: -110px;
  width: 420px;
  height: 420px;
  background: rgba(124, 95, 184, 0.52);
}
.aurora-b {
  right: -60px;
  bottom: -60px;
  width: 320px;
  height: 320px;
  background: rgba(210, 187, 255, 0.6);
}
.aurora-c {
  top: 34%;
  left: 24%;
  width: 240px;
  height: 240px;
  background: rgba(99, 70, 157, 0.32);
}
.login-shell {
  position: relative;
  z-index: 2;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 24px;
}
.login-stage {
  width: 100%;
  max-width: 340px;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.brand-lockup {
  margin-bottom: 26px;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.brand-mark {
  width: 58px;
  height: 58px;
  margin-bottom: 14px;
  border-radius: 10px;
  object-fit: cover;
  box-shadow: 0 0 22px rgba(99, 70, 157, 0.18);
}
.brand-title {
  margin: 0;
  font-family: Manrope, sans-serif;
  font-size: 2.05rem;
  font-weight: 800;
  letter-spacing: -0.03em;
}
.brand-kicker {
  margin: 6px 0 0;
  color: var(--secondary);
  font-size: 0.82rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}
.login-card {
  width: 100%;
  border-radius: var(--radius-card);
  background: var(--surface-card);
  border: 1px solid rgba(255, 255, 255, 0.45);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  box-shadow: var(--shadow-card);
}
.login-card-inner { padding: 32px 30px 28px; }
.auth-status-banner {
  border-radius: 14px;
  font-size: 0.9rem;
  line-height: 1.45;
  margin-bottom: 18px;
  padding: 12px 14px;
  background: rgba(99, 70, 157, 0.08);
  color: var(--text-soft);
}
.auth-status-banner.is-error {
  background: rgba(186, 26, 26, 0.1);
  color: #8c2323;
}
.auth-status-banner.is-success {
  background: rgba(99, 70, 157, 0.1);
  color: var(--primary);
}
.social-stack {
  display: grid;
  gap: 12px;
  margin-bottom: 28px;
}
.google-button {
  appearance: none;
  border: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  width: 100%;
  min-height: 56px;
  padding: 0 22px;
  border-radius: var(--radius-pill);
  background: rgba(255, 255, 255, 0.56);
  box-shadow: inset 0 0 0 1px var(--outline-soft);
  color: var(--text);
  font-weight: 700;
  transition: transform 160ms ease, box-shadow 160ms ease, background 160ms ease;
}
.google-button:hover {
  transform: translateY(-1px);
  background: rgba(255, 255, 255, 0.84);
  box-shadow: inset 0 0 0 1px rgba(123, 117, 130, 0.34), 0 12px 28px rgba(28, 28, 25, 0.05);
}
.google-button.is-loading {
  pointer-events: none;
  opacity: 0.88;
}
.google-mark {
  width: 20px;
  height: 20px;
  flex: 0 0 20px;
}
.guest-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 52px;
  padding: 0 22px;
  border-radius: var(--radius-pill);
  background: rgba(255, 255, 255, 0.36);
  box-shadow: inset 0 0 0 1px rgba(123, 117, 130, 0.22);
  color: var(--text-soft);
  font-weight: 600;
  transition: transform 160ms ease, box-shadow 160ms ease, background 160ms ease, color 160ms ease;
}
.guest-button:hover {
  transform: translateY(-1px);
  background: rgba(255, 255, 255, 0.5);
  box-shadow: inset 0 0 0 1px rgba(123, 117, 130, 0.3), 0 10px 24px rgba(28, 28, 25, 0.04);
  color: var(--text);
}
.coffee-button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  min-height: 44px;
  padding: 0 18px;
  border-radius: var(--radius-pill);
  background: rgba(99, 70, 157, 0.06);
  box-shadow: inset 0 0 0 1px rgba(99, 70, 157, 0.16);
  color: #4f378b;
  font-size: 0.9rem;
  font-weight: 650;
  transition: transform 160ms ease, box-shadow 160ms ease, background 160ms ease, color 160ms ease;
}
.coffee-button:hover {
  transform: translateY(-1px);
  background: rgba(99, 70, 157, 0.11);
  box-shadow: inset 0 0 0 1px rgba(99, 70, 157, 0.3), 0 10px 22px rgba(99, 70, 157, 0.08);
  color: var(--primary);
}
.coffee-button:focus-visible {
  outline: 2px solid rgba(99, 70, 157, 0.58);
  outline-offset: 3px;
  background: rgba(99, 70, 157, 0.1);
  box-shadow: inset 0 0 0 1px rgba(99, 70, 157, 0.32), 0 0 0 5px rgba(99, 70, 157, 0.1);
}
.coffee-cup {
  width: 18px;
  height: 18px;
  flex: 0 0 18px;
}
.shimmer-btn {
  position: relative;
  overflow: hidden;
}
.shimmer-btn::after {
  content: "";
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: linear-gradient(to bottom right, rgba(255,255,255,0) 0%, rgba(255,255,255,0) 40%, rgba(255,255,255,0.35) 50%, rgba(255,255,255,0) 60%, rgba(255,255,255,0) 100%);
  transform: translateX(-150%) rotate(45deg);
  animation: shimmer 5s linear infinite;
}
@keyframes shimmer {
  0% { transform: translateX(-150%) rotate(45deg); }
  20%, 100% { transform: translateX(150%) rotate(45deg); }
}
@media (max-width: 600px) {
  .login-shell { padding: 24px 18px; }
  .login-card-inner { padding: 28px 22px 24px; }
  .brand-title { font-size: 1.8rem; }
}
"""

_EMBEDDED_LOGIN_JS = """
function qs(name) {
  return new URLSearchParams(window.location.search).get(name);
}
function safeReturnTo() {
  const raw = qs("return_to") || "/";
  return raw.startsWith("/") && !raw.startsWith("//") ? raw : "/";
}
function setBanner(message, kind = "default") {
  const banner = document.getElementById("auth-status-banner");
  if (!banner) return;
  if (!message) {
    banner.hidden = true;
    banner.textContent = "";
    banner.className = "auth-status-banner";
    return;
  }
  banner.hidden = false;
  banner.textContent = message;
  banner.className = `auth-status-banner${kind === "error" ? " is-error" : kind === "success" ? " is-success" : ""}`;
}
function applyAuthErrorFromQuery() {
  const authError = qs("auth_error");
  if (!authError) return;
  const messages = {
    access_denied: "Google sign-in was cancelled. You can try again.",
    user_cancelled: "Google sign-in was cancelled. You can try again.",
    authentication_failed: "We couldn't complete sign-in. Please try again.",
    authentication_unavailable: "Google sign-in is not configured correctly right now. Continue as guest or try again later.",
    missing_code: "Sign-in did not complete. Please try again.",
    invalid_state: "Sign-in could not be verified safely. Please try again.",
  };
  setBanner(messages[authError] || "Sign-in was interrupted. Please try again.", "error");
}
function initStardust() {
  const container = document.getElementById("stardust-container");
  if (!container) return;
  container.innerHTML = "";
  for (let i = 0; i < 50; i += 1) {
    const star = document.createElement("div");
    const size = (Math.random() * 2 + 1).toFixed(2);
    star.className = "star";
    star.style.width = `${size}px`;
    star.style.height = `${size}px`;
    star.style.left = `${(Math.random() * 100).toFixed(3)}%`;
    star.style.top = `${(Math.random() * 100).toFixed(3)}%`;
    star.style.setProperty("--duration", `${(Math.random() * 3 + 2).toFixed(3)}s`);
    container.appendChild(star);
  }
}
function initParallax() {
  document.addEventListener("mousemove", (event) => {
    const moveX = event.clientX - window.innerWidth / 2;
    const moveY = event.clientY - window.innerHeight / 2;
    document.querySelectorAll("[data-parallax]").forEach((element) => {
      const factor = Number(element.getAttribute("data-parallax") || "0");
      element.style.transform = `translate(${moveX * factor}px, ${moveY * factor}px)`;
    });
  });
}
async function fetchSession() {
  const response = await fetch("/api/me", {
    method: "GET",
    credentials: "same-origin",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Auth session fetch failed with status ${response.status}`);
  }
  return response.json();
}
async function bootstrap() {
  initStardust();
  initParallax();
  applyAuthErrorFromQuery();
  const googleLink = document.getElementById("google-login-link");
  const googleLabel = document.getElementById("google-label");
  const guestLink = document.getElementById("guest-continue-link");
  if (googleLink && googleLabel) {
    googleLink.href = `/auth/google?return_to=${encodeURIComponent(safeReturnTo())}`;
    googleLink.addEventListener("click", () => {
      googleLink.classList.add("is-loading");
      googleLabel.textContent = "Connecting to Google...";
    });
  }
  if (guestLink) {
    guestLink.href = `/auth/guest?return_to=${encodeURIComponent(safeReturnTo())}`;
  }
  try {
    const session = await fetchSession();
    if (session.authenticated) {
      setBanner("You are already signed in. Redirecting...", "success");
      window.location.assign(safeReturnTo());
      return;
    }
    if (session.guest_mode) {
      setBanner("Guest mode is already active in this browser. Redirecting...", "success");
      window.location.assign(safeReturnTo());
      return;
    }
    if (session.auth_enabled === false) {
      if (googleLink) {
        googleLink.setAttribute("aria-disabled", "true");
        googleLink.classList.add("is-disabled");
        googleLink.removeAttribute("href");
      }
      setBanner("Google sign-in is not configured here yet. Continue as guest to enter.", "default");
    } else if (session.authenticated) {
      setBanner("You are already signed in. Redirecting...", "success");
      window.location.assign(safeReturnTo());
    }
  } catch (err) {
    setBanner("Authentication is temporarily unavailable. Continue as guest or try Google sign-in again.", "error");
  }
}
void bootstrap();
"""


def _load_login_asset(path: Path, embedded: str) -> str:
    try:
        if path.exists():
            return path.read_text(encoding="utf-8")
    except OSError:
        logger.exception("Failed to read login asset at %s", path)
    return embedded


def _render_login_html() -> str:
    css = _load_login_asset(_login_css, _EMBEDDED_LOGIN_CSS)
    js = _load_login_asset(_login_js, _EMBEDDED_LOGIN_JS)
    return f"""<!DOCTYPE html>
<html lang="en" class="light">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="theme-color" content="#f7ece1">
  <meta name="application-name" content="Socratink">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-title" content="Socratink">
  <title>Socratink - The Socratic Canvas</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Manrope:wght@700;800&display=swap" rel="stylesheet">
  <link rel="manifest" href="/manifest.webmanifest?v=1">
  <link rel="icon" type="image/png" sizes="192x192" href="/favicon-192x192.png?v=6">
  <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png?v=6">
  <link rel="apple-touch-icon" href="/apple-touch-icon.png?v=6">
  <style>{css}</style>
</head>
<body data-mode="signin">
  <div id="stardust-container" aria-hidden="true"></div>
  <div class="aurora aurora-a" data-parallax="0.05"></div>
  <div class="aurora aurora-b" data-parallax="0.03"></div>
  <div class="aurora aurora-c" data-parallax="0.08"></div>

  <main class="login-shell">
    <div class="login-stage">
      <div class="brand-lockup">
        <img src="/brand/socratink-mark-square.png?v=1" alt="Socratink brand mark" class="brand-mark">
        <h1 class="brand-title">socratink</h1>
        <p class="brand-kicker">guess wrong. learn faster.</p>
      </div>

      <section class="login-card" aria-labelledby="login-heading">
        <div class="login-card-inner">
          <h2 id="login-heading" class="sr-only">Login</h2>
          <div id="auth-status-banner" class="auth-status-banner" hidden></div>
          <div class="social-stack">
            <a id="google-login-link" class="google-button shimmer-btn" href="/auth/google">
              <svg class="google-mark" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"></path>
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"></path>
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"></path>
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.66l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"></path>
              </svg>
              <span id="google-label">Continue with Google</span>
            </a>
            <a id="guest-continue-link" class="guest-button" href="/">
              Continue as Guest
            </a>
            <a class="coffee-button" href="https://buymeacoffee.com/socratink" target="_blank" rel="noopener noreferrer">
              <svg class="coffee-cup" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M6.75 8.5h8.5v5.25a4.25 4.25 0 0 1-8.5 0V8.5Z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"></path>
                <path d="M15.25 10h1.25a2 2 0 0 1 0 4h-1.25" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"></path>
                <path d="M5.5 18.5h11.75" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"></path>
                <path d="M8.5 5.5c0-.9.75-1.1.75-2M12 5.5c0-.9.75-1.1.75-2" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"></path>
              </svg>
              Support the build
            </a>
          </div>
        </div>
      </section>
    </div>
  </main>
  <script type="module">{js}</script>
</body>
</html>"""


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


def _build_login_redirect(
    *, return_to: str | None = None, auth_error: str | None = None
) -> str:
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


def _apply_session_cookie(
    response: Response, request: Request, sealed_session: str
) -> None:
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


def _apply_oauth_state_cookie(
    response: Response, request: Request, signed_state: str
) -> None:
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


def _has_guest_session(request: Request) -> bool:
    return request.cookies.get(GUEST_COOKIE_NAME) == GUEST_COOKIE_VALUE


def _apply_guest_cookie(response: Response, request: Request) -> None:
    service = _get_auth_service(request)
    response.set_cookie(
        GUEST_COOKIE_NAME,
        GUEST_COOKIE_VALUE,
        secure=service.resolve_cookie_secure(_base_url(request)),
        httponly=True,
        samesite=service.cookie_samesite,
        path="/",
    )


def _clear_guest_cookie(response: Response) -> None:
    response.delete_cookie(GUEST_COOKIE_NAME, path="/")


def _load_current_session_state(request: Request) -> AuthSessionState:
    service = _get_auth_service(request)
    sealed_session = request.cookies.get(service.cookie_name)
    guest_mode = _has_guest_session(request)
    try:
        state = service.load_session(sealed_session)
    except AuthConfigurationError:
        logger.warning(
            "Auth session load failed because auth is not configured correctly."
        )
        state = AuthSessionState(
            auth_enabled=service.enabled,
            authenticated=False,
            guest_mode=guest_mode,
            should_clear_cookie=bool(sealed_session),
            error_reason="auth_unavailable",
        )
    except Exception:
        logger.exception("Auth session load failed unexpectedly.")
        state = AuthSessionState(
            auth_enabled=service.enabled,
            authenticated=False,
            guest_mode=guest_mode,
            should_clear_cookie=bool(sealed_session),
            error_reason="auth_session_unavailable",
        )
    state.guest_mode = not state.authenticated and guest_mode
    return state


@auth_router.get("/api/me")
def get_current_user(request: Request):
    state = _load_current_session_state(request)
    response = JSONResponse(state.to_public_dict())
    if state.sealed_session:
        _apply_session_cookie(response, request, state.sealed_session)
    elif state.should_clear_cookie:
        _clear_session_cookie(response, request)
    return response


@auth_router.get("/login")
def login(request: Request, return_to: str | None = None):
    current = _load_current_session_state(request)
    sanitized_return_to = sanitize_return_to_path(return_to)
    if current.authenticated or current.guest_mode:
        response = RedirectResponse(url=sanitized_return_to, status_code=302)
    else:
        response = HTMLResponse(_render_login_html())
    if current.should_clear_cookie:
        _clear_session_cookie(response, request)
    return response


@auth_router.get("/auth/guest")
def auth_guest(request: Request, return_to: str | None = None):
    sanitized_return_to = sanitize_return_to_path(return_to)
    response = RedirectResponse(url=sanitized_return_to, status_code=302)
    _apply_guest_cookie(response, request)
    return response


@auth_router.get("/auth/google")
def auth_google(request: Request, return_to: str | None = None):
    service = _get_auth_service(request)
    sanitized_return_to = sanitize_return_to_path(return_to)
    try:
        state_nonce, signed_state = service.build_oauth_state(
            return_to=sanitized_return_to
        )
        authorization_url = service.get_login_url(
            base_url=_base_url(request),
            return_to=state_nonce,
            provider="GoogleOAuth",
        )
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

    response = RedirectResponse(url=return_to, status_code=302)
    if auth_state.sealed_session:
        _apply_session_cookie(response, request, auth_state.sealed_session)
    _clear_guest_cookie(response)
    _clear_oauth_state_cookie(response, request)
    return response


@auth_router.post("/api/auth/logout")
def logout(request: Request):
    service = _get_auth_service(request)
    service.logout(request.cookies.get(service.cookie_name))
    response = JSONResponse({"ok": True, "auth_enabled": service.enabled})
    _clear_session_cookie(response, request)
    _clear_guest_cookie(response)
    return response


@auth_router.post("/api/auth/magic-auth/send")
def send_magic_auth(request: Request, body: MagicAuthSendRequest):
    raise HTTPException(
        status_code=503, detail="Email sign-in is not enabled in this release."
    )


@auth_router.post("/api/auth/magic-auth/verify")
def verify_magic_auth(request: Request, body: MagicAuthVerifyRequest):
    raise HTTPException(
        status_code=503, detail="Email sign-in is not enabled in this release."
    )
