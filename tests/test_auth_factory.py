"""S14 — build_auth_service_from_env reads new Supabase env vars."""

import logging
import os
import unittest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from cryptography.fernet import Fernet

from auth import build_auth_service_from_env
from auth.service import AuthConfigurationError, SupabaseAuthService
from auth.session_seal import seal_session_tokens


SESSION_KEY = Fernet.generate_key().decode()


@contextmanager
def env(**values):
    original = {k: os.environ.get(k) for k in values}
    try:
        for k, v in values.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        yield
    finally:
        for k, v in original.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


class FactoryTests(unittest.TestCase):
    def test_builds_supabase_service_from_env(self):
        with env(
            AUTH_ENABLED="true",
            SUPABASE_URL="https://abc.supabase.co",
            SUPABASE_PUBLISHABLE_KEY="pk_test",
            SUPABASE_JWT_SECRET="jwt_secret",
            APP_BASE_URL="http://localhost:8000",
            SESSION_COOKIE_KEY=SESSION_KEY,
        ):
            svc = build_auth_service_from_env()
        self.assertIsInstance(svc, SupabaseAuthService)
        self.assertTrue(svc.enabled)

    def test_disabled_when_auth_enabled_false(self):
        with env(
            AUTH_ENABLED="false",
            SUPABASE_URL=None,
            SUPABASE_PUBLISHABLE_KEY=None,
            SUPABASE_JWT_SECRET=None,
            APP_BASE_URL=None,
            SESSION_COOKIE_KEY=None,
        ):
            svc = build_auth_service_from_env()
        self.assertFalse(svc.enabled)

    def test_missing_supabase_url_raises_when_enabled(self):
        with env(
            AUTH_ENABLED="true",
            SUPABASE_URL=None,
            SUPABASE_PUBLISHABLE_KEY="pk",
            SUPABASE_JWT_SECRET="js",
            APP_BASE_URL="http://localhost:8000",
            SESSION_COOKIE_KEY=SESSION_KEY,
        ):
            with self.assertRaises(AuthConfigurationError):
                build_auth_service_from_env().callback_redirect_uri()

    def test_missing_session_cookie_key_raises(self):
        with env(
            AUTH_ENABLED="true",
            SUPABASE_URL="https://abc.supabase.co",
            SUPABASE_PUBLISHABLE_KEY="pk",
            SUPABASE_JWT_SECRET="js",
            APP_BASE_URL="http://localhost:8000",
            SESSION_COOKIE_KEY=None,
        ):
            with self.assertRaises(AuthConfigurationError):
                build_auth_service_from_env().load_session("anything")


    def test_invalid_session_cookie_key_raises(self):
        with env(
            AUTH_ENABLED="true",
            SUPABASE_URL="https://abc.supabase.co",
            SUPABASE_PUBLISHABLE_KEY="pk",
            SUPABASE_JWT_SECRET="js",
            APP_BASE_URL="http://localhost:8000",
            SESSION_COOKIE_KEY="invalid-fernet-key",
        ):
            with self.assertRaisesRegex(AuthConfigurationError, "SESSION_COOKIE_KEY is not a valid Fernet key"):
                build_auth_service_from_env().load_session("anything")

<<<<<<< coderabbitai/utg/19c111b
    def test_valid_session_cookie_key_does_not_raise_at_config(self):
        """A proper Fernet key should pass _require_enabled() without AuthConfigurationError."""
        with env(
            AUTH_ENABLED="true",
            SUPABASE_URL="https://abc.supabase.co",
            SUPABASE_PUBLISHABLE_KEY="pk",
            SUPABASE_JWT_SECRET="js",
            APP_BASE_URL="http://localhost:8000",
            SESSION_COOKIE_KEY=SESSION_KEY,
        ):
            svc = build_auth_service_from_env()
            # load_session with None sealed cookie returns unauthenticated but
            # does NOT raise AuthConfigurationError about the key.
            state = svc.load_session(None)
            self.assertFalse(state.authenticated)
            self.assertTrue(state.auth_enabled)

    def test_invalid_sealed_cookie_returns_unauthenticated_state(self):
        """load_session with a corrupted sealed cookie returns unauthenticated, clear-cookie state."""
        with env(
            AUTH_ENABLED="true",
            SUPABASE_URL="https://abc.supabase.co",
            SUPABASE_PUBLISHABLE_KEY="pk",
            SUPABASE_JWT_SECRET="js",
            APP_BASE_URL="http://localhost:8000",
            SESSION_COOKIE_KEY=SESSION_KEY,
        ):
            svc = build_auth_service_from_env()
            state = svc.load_session("this-is-not-a-valid-fernet-token")
            self.assertFalse(state.authenticated)
            self.assertTrue(state.should_clear_cookie)
            self.assertEqual(state.error_reason, "session_cookie_invalid")

    def test_invalid_sealed_cookie_with_wrong_key_clears_cookie(self):
        """Cookie encrypted with a different key → clear-cookie, not an exception."""
        other_key = Fernet.generate_key().decode()
        sealed = seal_session_tokens(
            {"access_token": "at", "refresh_token": "rt", "expires_at": 0},
            key=other_key,
        )
        with env(
            AUTH_ENABLED="true",
            SUPABASE_URL="https://abc.supabase.co",
            SUPABASE_PUBLISHABLE_KEY="pk",
            SUPABASE_JWT_SECRET="js",
            APP_BASE_URL="http://localhost:8000",
            SESSION_COOKIE_KEY=SESSION_KEY,
        ):
            svc = build_auth_service_from_env()
            state = svc.load_session(sealed)
            self.assertFalse(state.authenticated)
            self.assertTrue(state.should_clear_cookie)
            self.assertEqual(state.error_reason, "session_cookie_invalid")


class LogoutTests(unittest.TestCase):
    """Tests for the sign-out logging behavior added in this PR."""

    def _make_svc(self):
        return SupabaseAuthService(
            enabled=True,
            supabase_url="https://abc.supabase.co",
            publishable_key="pk",
            jwt_secret="js",
            session_cookie_key=SESSION_KEY,
            app_base_url="http://localhost:8000",
        )

    def test_logout_with_no_sealed_session_is_noop(self):
        """logout(None) does nothing and does not raise."""
        svc = self._make_svc()
        svc.logout(None)  # should not raise

    def test_logout_with_bad_sealed_session_is_noop(self):
        """logout with a garbled token silently does nothing (unseal returns None)."""
        svc = self._make_svc()
        svc.logout("garbage-token")  # should not raise

    @patch("auth.service.SupabaseAuthService._make_supabase_client")
    def test_logout_sign_out_failure_is_logged_at_debug(self, mock_make_client):
        """When Supabase sign_out raises, the exception is logged at DEBUG level, not re-raised."""
        mock_client = MagicMock()
        mock_client.auth.sign_out.side_effect = RuntimeError("network error")
        mock_make_client.return_value = mock_client

        sealed = seal_session_tokens(
            {"access_token": "at", "refresh_token": "rt", "expires_at": 0},
            key=SESSION_KEY,
        )
        svc = self._make_svc()

        with self.assertLogs("auth.service", level=logging.DEBUG) as log_ctx:
            svc.logout(sealed)  # must not raise

        self.assertTrue(
            any("sign-out" in msg.lower() or "sign_out" in msg.lower() or "supabase" in msg.lower()
                for msg in log_ctx.output),
            f"Expected debug log about sign-out failure, got: {log_ctx.output}",
        )

    @patch("auth.service.SupabaseAuthService._make_supabase_client")
    def test_logout_sign_out_failure_does_not_raise(self, mock_make_client):
        """Supabase sign_out failure must never propagate to the caller."""
        mock_client = MagicMock()
        mock_client.auth.sign_out.side_effect = Exception("supabase unreachable")
        mock_make_client.return_value = mock_client

        sealed = seal_session_tokens(
            {"access_token": "at", "refresh_token": "rt", "expires_at": 0},
            key=SESSION_KEY,
        )
        svc = self._make_svc()
        # This must complete without raising
        try:
            svc.logout(sealed)
        except Exception as exc:
            self.fail(f"logout() raised unexpectedly: {exc}")


class UnsealOrNoneTests(unittest.TestCase):
    """Tests for _unseal_or_none — the ValueError-catch path added in this PR."""

    def _make_svc(self):
        return SupabaseAuthService(
            enabled=True,
            supabase_url="https://abc.supabase.co",
            publishable_key="pk",
            jwt_secret="js",
            session_cookie_key=SESSION_KEY,
            app_base_url="http://localhost:8000",
        )

    def test_valid_sealed_session_returns_tokens(self):
        tokens = {"access_token": "at", "refresh_token": "rt", "expires_at": 123}
        sealed = seal_session_tokens(tokens, key=SESSION_KEY)
        svc = self._make_svc()
        result = svc._unseal_or_none(sealed)
        self.assertEqual(result, tokens)

    def test_garbage_sealed_session_returns_none(self):
        """Garbage input should return None, not raise."""
        svc = self._make_svc()
        result = svc._unseal_or_none("totally-not-fernet")
        self.assertIsNone(result)

    def test_wrong_key_sealed_session_returns_none(self):
        """Cookie sealed with a different key returns None rather than raising."""
        other_key = Fernet.generate_key().decode()
        sealed = seal_session_tokens(
            {"access_token": "at", "refresh_token": "rt", "expires_at": 0},
            key=other_key,
        )
        svc = self._make_svc()
        result = svc._unseal_or_none(sealed)
        self.assertIsNone(result)

=======
>>>>>>> main

if __name__ == "__main__":
    unittest.main()
