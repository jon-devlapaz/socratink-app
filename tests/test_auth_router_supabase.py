"""S9 + S10 + S11 — router endpoints under SupabaseAuthService.

Uses a fake service matching the SupabaseAuthService interface.
"""

import unittest
import os
from urllib.parse import parse_qs, urlparse

from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

from auth.router import GUEST_COOKIE_NAME, _local_e2e_guest_bootstrap_enabled, auth_router
from auth.service import (
    AuthConfigurationError,
    AuthSessionState,
    AuthUser,
    SupabaseAuthService,
)


class FakeSupabaseAuthService:
    def __init__(self, *, enabled=True):
        self.enabled = enabled
        self.cookie_name = "sb_session"
        self.cookie_samesite = "lax"
        self.cookie_max_age = 120
        self.oauth_state_cookie_name = "sb_oauth_state"
        self.oauth_state_ttl_seconds = 600
        self.app_base_url = "http://localhost:8000"
        self.callback_path = "/auth/callback"

        # Interaction recording
        self.last_built_state = None
        self.last_exchange_args = None
        self.last_logout_cookie = None
        self.oauth_state_valid = True

        self.current_state = AuthSessionState(auth_enabled=enabled, authenticated=False)
        self.callback_state = AuthSessionState(
            auth_enabled=enabled,
            authenticated=True,
            user=AuthUser(id="user_uuid_123", email="learner@example.com"),
            sealed_session="sealed-session-blob",
        )

    # --- supabase-shaped service interface ---

    def build_oauth_state(self, *, return_to: str):
        self.last_built_state = return_to
        return (
            "v_pkce_verifier_value",
            "ch_pkce_challenge_value",
            "signed-state-cookie",
        )

    def get_login_url(self, *, code_challenge: str) -> str:
        if not self.enabled:
            raise RuntimeError("disabled")
        return (
            "https://abc123.supabase.co/auth/v1/authorize"
            f"?provider=google&code_challenge={code_challenge}"
            "&code_challenge_method=s256"
            "&redirect_to=http%3A%2F%2Flocalhost%3A8000%2Fauth%2Fcallback"
        )

    def verify_oauth_state(self, *, signed_cookie: str | None):
        if not self.oauth_state_valid:
            return None
        if signed_cookie == "signed-state-cookie":
            return ("/library", "v_pkce_verifier_value")
        return None

    def exchange_code(self, *, code: str, code_verifier: str, redirect_uri: str):
        self.last_exchange_args = {
            "code": code,
            "code_verifier": code_verifier,
            "redirect_uri": redirect_uri,
        }
        return self.callback_state

    def load_session(self, sealed_session: str | None):
        return self.current_state

    def logout(self, sealed_session: str | None):
        self.last_logout_cookie = sealed_session

    def resolve_cookie_secure(self, base_url: str) -> bool:
        return base_url.startswith("https://")

    def callback_redirect_uri(self) -> str:
        return f"{self.app_base_url.rstrip('/')}{self.callback_path}"

    def build_local_dev_guest_session(self):
        return AuthSessionState(
            auth_enabled=True,
            authenticated=True,
            user=AuthUser(id="local_dev_guest"),
            guest_mode=True,
            sealed_session="sealed-local-dev-guest",
        )


def build_client(
    service: FakeSupabaseAuthService, *, base_url: str = "http://testserver"
) -> TestClient:
    app = FastAPI()
    app.state.auth_service = service
    app.include_router(auth_router)
    return TestClient(app, base_url=base_url)


class LoginRouteTests(unittest.TestCase):
    def setUp(self):
        self._env_keys = (
            "SOCRATINK_DEV_AUTOGUEST",
            "SOCRATINK_LOCAL_AUTH_BYPASS",
            "VERCEL",
            "VERCEL_ENV",
            "CI",
        )
        self._env_snapshot = {key: os.environ.get(key) for key in self._env_keys}

    def tearDown(self):
        for key, value in self._env_snapshot.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _set_env(self, **values):
        for key in self._env_keys:
            os.environ.pop(key, None)
        for key, value in values.items():
            if value is not None:
                os.environ[key] = value

    def test_identified_user_redirects_from_login(self):
        service = FakeSupabaseAuthService(enabled=True)
        service.current_state = AuthSessionState(
            auth_enabled=True,
            authenticated=True,
            user=AuthUser(id="user_uuid_123", email="learner@example.com"),
            guest_mode=False,
        )
        client = build_client(service)

        response = client.get("/login?return_to=/library", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "/library")

    def test_guest_can_open_login_to_upgrade(self):
        service = FakeSupabaseAuthService(enabled=True)
        service.current_state = AuthSessionState(
            auth_enabled=True,
            authenticated=True,
            user=AuthUser(id="anon_uuid_456"),
            guest_mode=True,
        )
        client = build_client(service)

        response = client.get("/login?return_to=/", follow_redirects=False)

        self.assertEqual(response.status_code, 200)
        body = response.text
        self.assertIn("Continue with Google", body)
        self.assertIn("continue as guest", body)

    def test_dev_autoguest_login_redirects_to_guest_without_error(self):
        self._set_env(SOCRATINK_DEV_AUTOGUEST="1")
        service = FakeSupabaseAuthService(enabled=True)
        client = build_client(service, base_url="http://localhost:8000")

        response = client.get("/login?return_to=/", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "/auth/guest?return_to=%2F")

    def test_loopback_login_requires_dev_opt_in(self):
        self._set_env()
        service = FakeSupabaseAuthService(enabled=True)
        client = build_client(service, base_url="http://localhost:8000")

        response = client.get("/login?return_to=/", follow_redirects=False)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Continue with Google", response.text)

    def test_dev_autoguest_login_error_renders_login(self):
        self._set_env(SOCRATINK_DEV_AUTOGUEST="1")
        service = FakeSupabaseAuthService(enabled=True)
        client = build_client(service, base_url="http://localhost:8000")

        response = client.get(
            "/login?return_to=/&auth_error=authentication_failed",
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Continue with Google", response.text)
        self.assertIn("continue as guest", response.text)

    def test_dev_autoguest_return_to_error_renders_login(self):
        self._set_env(SOCRATINK_DEV_AUTOGUEST="1")
        service = FakeSupabaseAuthService(enabled=True)
        client = build_client(service)

        response = client.get(
            "/login?return_to=/login%3Fauth_error%3Dguest_unavailable",
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Continue with Google", response.text)
        self.assertIn("continue as guest", response.text)

    def test_login_clears_invalid_session_cookie_on_html_response(self):
        service = FakeSupabaseAuthService(enabled=True)
        service.current_state = AuthSessionState(
            auth_enabled=True,
            authenticated=False,
            should_clear_cookie=True,
        )
        client = build_client(service)
        client.cookies.set(service.cookie_name, "invalid-session")

        response = client.get("/login?return_to=/", follow_redirects=False)

        self.assertEqual(response.status_code, 200)
        cookies = response.headers.get("set-cookie", "")
        self.assertIn("sb_session=", cookies)
        self.assertIn("Max-Age=0", cookies)


class GoogleAuthStartTests(unittest.TestCase):
    def test_redirects_to_supabase_authorize_with_pkce(self):
        service = FakeSupabaseAuthService(enabled=True)
        client = build_client(service)

        response = client.get(
            "/auth/google?return_to=/library", follow_redirects=False
        )

        self.assertEqual(response.status_code, 302)
        location = response.headers["location"]
        parsed = urlparse(location)
        self.assertEqual(parsed.netloc, "abc123.supabase.co")
        self.assertEqual(parsed.path, "/auth/v1/authorize")
        qs = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        self.assertEqual(qs["provider"], "google")
        self.assertEqual(qs["code_challenge_method"], "s256")
        self.assertIn("code_challenge", qs)
        # Supabase manages state internally; sending our own caused bad_oauth_state.
        self.assertNotIn("state", qs)

    def test_state_cookie_set_with_signed_payload(self):
        service = FakeSupabaseAuthService(enabled=True)
        client = build_client(service)

        response = client.get("/auth/google", follow_redirects=False)

        self.assertIn(
            f"{service.oauth_state_cookie_name}=signed-state-cookie",
            response.headers.get("set-cookie", ""),
        )

    def test_state_cookie_always_uses_lax_samesite(self):
        service = FakeSupabaseAuthService(enabled=True)
        service.cookie_samesite = "strict"
        client = build_client(service)

        response = client.get("/auth/google", follow_redirects=False)

        cookies = response.headers.get("set-cookie", "")
        self.assertIn(f"{service.oauth_state_cookie_name}=signed-state-cookie", cookies)
        self.assertIn("SameSite=lax", cookies)
        self.assertNotIn("SameSite=strict", cookies)

    def test_open_redirect_return_to_sanitized(self):
        service = FakeSupabaseAuthService(enabled=True)
        client = build_client(service)

        client.get(
            "/auth/google?return_to=https://evil.test", follow_redirects=False
        )

        self.assertEqual(service.last_built_state, "/")


class CallbackTests(unittest.TestCase):
    def test_success_sets_session_cookie_and_redirects(self):
        service = FakeSupabaseAuthService(enabled=True)
        client = build_client(service)
        client.cookies.set(service.oauth_state_cookie_name, "signed-state-cookie")

        response = client.get(
            "/auth/callback?code=abc123", follow_redirects=False
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "/library")
        self.assertIn(
            "sb_session=sealed-session-blob", response.headers.get("set-cookie", "")
        )
        self.assertEqual(
            service.last_exchange_args,
            {
                "code": "abc123",
                "code_verifier": "v_pkce_verifier_value",
                "redirect_uri": "http://localhost:8000/auth/callback",
            },
        )

    def test_invalid_state_redirects_with_error(self):
        service = FakeSupabaseAuthService(enabled=True)
        service.oauth_state_valid = False
        client = build_client(service)
        client.cookies.set(service.oauth_state_cookie_name, "signed-state-cookie")

        response = client.get(
            "/auth/callback?code=abc", follow_redirects=False
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("auth_error=invalid_state", response.headers["location"])

    def test_missing_code_redirects_with_error(self):
        service = FakeSupabaseAuthService(enabled=True)
        client = build_client(service)
        client.cookies.set(service.oauth_state_cookie_name, "signed-state-cookie")

        response = client.get("/auth/callback", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertIn("auth_error=missing_code", response.headers["location"])

    def test_provider_error_propagates(self):
        service = FakeSupabaseAuthService(enabled=True)
        client = build_client(service)
        client.cookies.set(service.oauth_state_cookie_name, "signed-state-cookie")

        response = client.get(
            "/auth/callback?error=access_denied",
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("auth_error=access_denied", response.headers["location"])

    def test_exchange_failure_redirects_with_error(self):
        service = FakeSupabaseAuthService(enabled=True)

        def boom(**_kwargs):
            raise RuntimeError("supabase down")

        service.exchange_code = boom  # type: ignore[assignment]
        client = build_client(service)
        client.cookies.set(service.oauth_state_cookie_name, "signed-state-cookie")

        response = client.get(
            "/auth/callback?code=abc", follow_redirects=False
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("auth_error=authentication_failed", response.headers["location"])

    def test_unauthenticated_exchange_state_redirects_with_error(self):
        service = FakeSupabaseAuthService(enabled=True)
        service.callback_state = AuthSessionState(
            auth_enabled=True,
            authenticated=False,
            user=AuthUser(id="user_uuid_123", email="learner@example.com"),
        )
        client = build_client(service)
        client.cookies.set(service.oauth_state_cookie_name, "signed-state-cookie")

        response = client.get("/auth/callback?code=abc", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertIn("auth_error=authentication_failed", response.headers["location"])
        self.assertNotIn("sb_session=", response.headers.get("set-cookie", ""))


class ApiMeAndLogoutTests(unittest.TestCase):
    def test_api_me_returns_user_when_authenticated(self):
        service = FakeSupabaseAuthService(enabled=True)
        service.current_state = AuthSessionState(
            auth_enabled=True,
            authenticated=True,
            user=AuthUser(id="user_uuid_123", email="learner@example.com"),
        )
        client = build_client(service)

        response = client.get("/api/me")
        body = response.json()
        self.assertTrue(body["authenticated"])
        self.assertEqual(body["user"]["email"], "learner@example.com")

    def test_api_me_writes_back_refreshed_cookie(self):
        service = FakeSupabaseAuthService(enabled=True)
        service.current_state = AuthSessionState(
            auth_enabled=True,
            authenticated=True,
            user=AuthUser(id="user_uuid_123", email="learner@example.com"),
            sealed_session="sealed-refreshed-blob",
        )
        client = build_client(service)

        response = client.get("/api/me")
        self.assertIn(
            "sb_session=sealed-refreshed-blob",
            response.headers.get("set-cookie", ""),
        )

    def test_api_me_clears_invalid_session_cookie(self):
        service = FakeSupabaseAuthService(enabled=True)
        service.current_state = AuthSessionState(
            auth_enabled=True,
            authenticated=False,
            should_clear_cookie=True,
        )
        client = build_client(service)
        client.cookies.set(service.cookie_name, "invalid-session")

        response = client.get("/api/me")

        self.assertEqual(response.status_code, 200)
        cookies = response.headers.get("set-cookie", "")
        self.assertIn("sb_session=", cookies)
        self.assertIn("Max-Age=0", cookies)

    def test_logout_clears_session_and_guest_cookies(self):
        service = FakeSupabaseAuthService(enabled=True)
        client = build_client(service)
        client.cookies.set(service.cookie_name, "sealed-session-blob")
        client.cookies.set(GUEST_COOKIE_NAME, "guest")

        response = client.post("/api/auth/logout")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(service.last_logout_cookie, "sealed-session-blob")
        cookies = response.headers.get("set-cookie", "")
        self.assertIn("sb_session=", cookies)
        self.assertIn(f"{GUEST_COOKIE_NAME}=", cookies)
        self.assertIn("Max-Age=0", cookies)

class AnonymousGuestTests(unittest.TestCase):
    def setUp(self):
        self._env_keys = (
            "SOCRATINK_DEV_AUTOGUEST",
            "SOCRATINK_LOCAL_AUTH_BYPASS",
            "VERCEL",
            "VERCEL_ENV",
            "CI",
        )
        self._env_snapshot = {key: os.environ.get(key) for key in self._env_keys}

    def tearDown(self):
        for key, value in self._env_snapshot.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _set_env(self, **values):
        for key in self._env_keys:
            os.environ.pop(key, None)
        for key, value in values.items():
            if value is not None:
                os.environ[key] = value

    def test_guest_calls_sign_in_anonymously_and_sets_session_cookie(self):
        service = FakeSupabaseAuthService(enabled=True)
        called = {}

        def fake_anon():
            called["yes"] = True
            return AuthSessionState(
                auth_enabled=True,
                authenticated=True,
                user=AuthUser(id="anon_uuid_456"),
                guest_mode=True,
                sealed_session="sealed-anon-blob",
            )

        service.sign_in_anonymously = fake_anon  # type: ignore[assignment]
        client = build_client(service)

        response = client.get("/auth/guest?return_to=/library", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "/library")
        self.assertTrue(called.get("yes"))
        self.assertIn(
            "sb_session=sealed-anon-blob", response.headers.get("set-cookie", "")
        )

    def test_loopback_guest_uses_local_session_without_supabase_call(self):
        self._set_env(SOCRATINK_DEV_AUTOGUEST="1")
        service = FakeSupabaseAuthService(enabled=True)

        def fail_if_called():
            raise AssertionError("localhost guest bootstrap must not call Supabase")

        service.sign_in_anonymously = fail_if_called  # type: ignore[assignment]
        client = build_client(service, base_url="http://localhost:8000")

        response = client.get("/auth/guest?return_to=/library", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "/library")
        self.assertIn(
            "sb_session=sealed-local-dev-guest",
            response.headers.get("set-cookie", ""),
        )

    def test_guest_open_redirect_sanitized(self):
        service = FakeSupabaseAuthService(enabled=True)
        service.sign_in_anonymously = lambda: AuthSessionState(  # type: ignore[assignment]
            auth_enabled=True,
            authenticated=True,
            user=AuthUser(id="anon_uuid_456"),
            guest_mode=True,
            sealed_session="sealed-anon-blob",
        )
        client = build_client(service)

        response = client.get(
            "/auth/guest?return_to=https://evil.test", follow_redirects=False
        )

        self.assertEqual(response.headers["location"], "/")

    def test_guest_failure_redirects_to_login_with_error(self):
        service = FakeSupabaseAuthService(enabled=True)

        def boom():
            raise RuntimeError("supabase down")

        service.sign_in_anonymously = boom  # type: ignore[assignment]
        client = build_client(service)

        response = client.get("/auth/guest?return_to=/", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("auth_error=authentication_failed", response.headers["location"])

    def test_dev_autoguest_falls_back_to_local_guest_when_supabase_guest_fails(self):
        self._set_env(SOCRATINK_DEV_AUTOGUEST="1")
        service = FakeSupabaseAuthService(enabled=True)

        def boom():
            raise RuntimeError("supabase anonymous sign-in disabled")

        service.sign_in_anonymously = boom  # type: ignore[assignment]
        client = build_client(service, base_url="http://localhost:8000")

        response = client.get("/auth/guest?return_to=/", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "/")
        self.assertIn(
            "sb_session=sealed-local-dev-guest", response.headers.get("set-cookie", "")
        )

    def test_dev_autoguest_does_not_fallback_to_local_guest_for_remote_host(self):
        self._set_env(SOCRATINK_DEV_AUTOGUEST="1")
        service = FakeSupabaseAuthService(enabled=True)

        def boom():
            raise RuntimeError("supabase anonymous sign-in disabled")

        service.sign_in_anonymously = boom  # type: ignore[assignment]
        client = build_client(service, base_url="http://192.0.2.10:8000")

        response = client.get("/auth/guest?return_to=/", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertIn("auth_error=authentication_failed", response.headers["location"])
        self.assertNotIn("sealed-local-dev-guest", response.headers.get("set-cookie", ""))

    def test_dev_autoguest_falls_back_to_local_guest_when_guest_config_fails(self):
        self._set_env(SOCRATINK_DEV_AUTOGUEST="1")
        service = FakeSupabaseAuthService(enabled=True)

        def boom():
            raise AuthConfigurationError("anonymous sign-in unavailable")

        service.sign_in_anonymously = boom  # type: ignore[assignment]
        client = build_client(service, base_url="http://localhost:8000")

        response = client.get("/auth/guest?return_to=/", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "/")
        self.assertIn(
            "sb_session=sealed-local-dev-guest", response.headers.get("set-cookie", "")
        )

    def test_dev_autoguest_keeps_error_when_local_guest_config_fails(self):
        self._set_env(SOCRATINK_DEV_AUTOGUEST="1")
        service = FakeSupabaseAuthService(enabled=True)

        def boom():
            raise RuntimeError("supabase anonymous sign-in disabled")

        def local_boom():
            raise AuthConfigurationError("local guest config missing")

        service.sign_in_anonymously = boom  # type: ignore[assignment]
        service.build_local_dev_guest_session = local_boom  # type: ignore[method-assign]
        client = build_client(service, base_url="http://localhost:8000")

        response = client.get("/auth/guest?return_to=/", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertIn("auth_error=authentication_failed", response.headers["location"])

    def test_dev_autoguest_keeps_error_when_local_guest_has_no_cookie(self):
        self._set_env(SOCRATINK_DEV_AUTOGUEST="1")
        service = FakeSupabaseAuthService(enabled=True)

        def boom():
            raise RuntimeError("supabase anonymous sign-in disabled")

        service.sign_in_anonymously = boom  # type: ignore[assignment]
        service.build_local_dev_guest_session = lambda: AuthSessionState(  # type: ignore[method-assign]
            auth_enabled=True,
            authenticated=True,
            guest_mode=True,
            user=AuthUser(id="local_dev_guest"),
        )
        client = build_client(service, base_url="http://localhost:8000")

        response = client.get("/auth/guest?return_to=/", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertIn("auth_error=authentication_failed", response.headers["location"])

    def test_dev_autoguest_falls_back_when_supabase_guest_state_is_incomplete(self):
        self._set_env(SOCRATINK_DEV_AUTOGUEST="1")
        service = FakeSupabaseAuthService(enabled=True)
        service.sign_in_anonymously = lambda: AuthSessionState(  # type: ignore[assignment]
            auth_enabled=True,
            authenticated=False,
            user=AuthUser(id="anon_uuid_456"),
        )
        client = build_client(service, base_url="http://localhost:8000")

        response = client.get("/auth/guest?return_to=/", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "/")
        self.assertIn(
            "sb_session=sealed-local-dev-guest", response.headers.get("set-cookie", "")
        )

    def test_guest_configuration_failure_uses_guest_error(self):
        service = FakeSupabaseAuthService(enabled=True)

        def boom():
            raise AuthConfigurationError("missing anon auth config")

        service.sign_in_anonymously = boom  # type: ignore[assignment]
        client = build_client(service)

        response = client.get("/auth/guest?return_to=/", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertIn("auth_error=guest_unavailable", response.headers["location"])

    def test_guest_unauthenticated_state_redirects_without_session_cookie(self):
        service = FakeSupabaseAuthService(enabled=True)
        service.sign_in_anonymously = lambda: AuthSessionState(  # type: ignore[assignment]
            auth_enabled=True,
            authenticated=False,
            user=AuthUser(id="anon_uuid_456"),
        )
        client = build_client(service)

        response = client.get("/auth/guest?return_to=/library", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertIn("auth_error=authentication_failed", response.headers["location"])
        self.assertNotIn("sb_session=", response.headers.get("set-cookie", ""))

    def test_guest_non_anonymous_state_redirects_without_session_cookie(self):
        service = FakeSupabaseAuthService(enabled=True)
        service.sign_in_anonymously = lambda: AuthSessionState(  # type: ignore[assignment]
            auth_enabled=True,
            authenticated=True,
            guest_mode=False,
            user=AuthUser(id="user_uuid_123", email="learner@example.com"),
            sealed_session="sealed-user-blob",
        )
        client = build_client(service)

        response = client.get("/auth/guest?return_to=/library", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertIn("auth_error=authentication_failed", response.headers["location"])
        self.assertNotIn("sb_session=", response.headers.get("set-cookie", ""))

    def test_login_html_has_motion_bootstrap(self):
        """The login page must honor a user-set socratink.motion preference.

        The override is stored in localStorage by Settings; when the user logs
        out and lands on /login, that preference must continue to set
        html[data-motion='reduced'] before first paint. Without this script,
        the login page would briefly run full motion until the inline
        script tag executed.
        """
        service = FakeSupabaseAuthService(enabled=True)
        client = build_client(service)

        response = client.get("/login")
        assert response.status_code == 200
        body = response.text
        assert "socratink.motion" in body, "motion key not referenced in login HTML"
        assert "dataset.motion" in body, "data-motion override not wired in login bootstrap"


class LocalE2EGuestBootstrapTests(unittest.TestCase):
    def setUp(self):
        self._env_keys = (
            "SOCRATINK_E2E_LOCAL_GUEST",
            "SOCRATINK_DEV_AUTOGUEST",
            "GITHUB_ACTIONS",
            "VERCEL",
            "VERCEL_ENV",
            "CI",
        )
        self._env_snapshot = {key: os.environ.get(key) for key in self._env_keys}

    def tearDown(self):
        for key, value in self._env_snapshot.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _set_env(self, **values):
        for key in self._env_keys:
            os.environ.pop(key, None)
        for key, value in values.items():
            if value is not None:
                os.environ[key] = value

    def _client(self, *, client_address=("testclient", 50000)) -> TestClient:
        app = FastAPI()
        app.state.auth_service = SupabaseAuthService(
            enabled=True,
            supabase_url="https://abc123.supabase.co",
            publishable_key="pk_test",
            jwt_secret="auth-router-e2e-guest-jwt-secret-test-fixture",
            session_cookie_key=Fernet.generate_key().decode(),
            app_base_url="http://localhost:8000",
        )
        app.include_router(auth_router)
        return TestClient(app, client=client_address)

    def test_e2e_guest_route_hidden_by_default(self):
        self._set_env()
        client = self._client()

        response = client.get("/auth/e2e/guest?return_to=/", follow_redirects=False)

        self.assertEqual(response.status_code, 404)

    def test_e2e_guest_route_hidden_in_ci_shape(self):
        self._set_env(
            SOCRATINK_E2E_LOCAL_GUEST="1",
            SOCRATINK_DEV_AUTOGUEST="1",
            CI="true",
        )
        client = self._client()

        response = client.get("/auth/e2e/guest?return_to=/", follow_redirects=False)

        self.assertEqual(response.status_code, 404)

    def test_e2e_guest_route_hidden_for_remote_clients(self):
        self._set_env(SOCRATINK_E2E_LOCAL_GUEST="1", SOCRATINK_DEV_AUTOGUEST="1")
        client = self._client(client_address=("203.0.113.10", 50000))

        response = client.get("/auth/e2e/guest?return_to=/", follow_redirects=False)

        self.assertEqual(response.status_code, 404)

    def test_e2e_guest_route_enabled_for_loopback_github_actions(self):
        self._set_env(
            SOCRATINK_E2E_LOCAL_GUEST="1",
            GITHUB_ACTIONS="true",
            CI="true",
        )
        client = self._client()

        response = client.get("/auth/e2e/guest?return_to=/", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "/")
        self.assertIn("sb_session=", response.headers.get("set-cookie", ""))

    def test_e2e_guest_route_rejects_non_loopback_github_actions_request(self):
        self._set_env(
            SOCRATINK_E2E_LOCAL_GUEST="1",
            GITHUB_ACTIONS="true",
            CI="true",
        )
        request = Request(
            {
                "type": "http",
                "method": "GET",
                "path": "/auth/e2e/guest",
                "headers": [],
                "client": ("203.0.113.10", 12345),
            }
        )

        self.assertIs(_local_e2e_guest_bootstrap_enabled(request), False)

    def test_e2e_guest_configuration_failure_uses_guest_error(self):
        self._set_env(SOCRATINK_E2E_LOCAL_GUEST="1", SOCRATINK_DEV_AUTOGUEST="1")
        service = FakeSupabaseAuthService(enabled=True)

        def boom():
            raise AuthConfigurationError("missing local e2e config")

        service.build_local_e2e_guest_session = boom  # type: ignore[attr-defined]
        client = build_client(service)

        response = client.get("/auth/e2e/guest?return_to=/", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertIn("auth_error=guest_unavailable", response.headers["location"])

    def test_e2e_guest_without_sealed_session_redirects_with_error(self):
        self._set_env(SOCRATINK_E2E_LOCAL_GUEST="1", SOCRATINK_DEV_AUTOGUEST="1")
        service = FakeSupabaseAuthService(enabled=True)
        service.build_local_e2e_guest_session = lambda: AuthSessionState(  # type: ignore[attr-defined]
            auth_enabled=True,
            authenticated=True,
            guest_mode=True,
            user=AuthUser(id="local_e2e_guest"),
        )
        client = build_client(service)

        response = client.get("/auth/e2e/guest?return_to=/", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertIn("auth_error=authentication_failed", response.headers["location"])

    def test_e2e_guest_sets_cookie_readable_by_api_me(self):
        self._set_env(SOCRATINK_E2E_LOCAL_GUEST="1", SOCRATINK_DEV_AUTOGUEST="1")
        client = self._client()

        response = client.get("/auth/e2e/guest?return_to=/", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "/")
        self.assertIn("sb_session=", response.headers.get("set-cookie", ""))

        session = client.get("/api/me")
        self.assertEqual(session.status_code, 200)
        payload = session.json()
        self.assertIs(payload.get("authenticated"), True)
        self.assertIs(payload.get("guest_mode"), True)

    def test_local_dev_guest_alias_builds_same_local_session_shape(self):
        self._set_env(SOCRATINK_DEV_AUTOGUEST="1")
        service = SupabaseAuthService(
            enabled=True,
            supabase_url="https://abc123.supabase.co",
            publishable_key="pk_test",
            jwt_secret="auth-router-e2e-guest-jwt-secret-test-fixture",
            session_cookie_key=Fernet.generate_key().decode(),
            app_base_url="http://localhost:8000",
        )

        state = service.build_local_dev_guest_session()

        self.assertTrue(state.authenticated)
        self.assertTrue(state.guest_mode)
        self.assertIsNotNone(state.sealed_session)


if __name__ == "__main__":
    unittest.main()
