"""S14 — build_auth_service_from_env reads new Supabase env vars."""

import os
import unittest
from contextlib import contextmanager

from cryptography.fernet import Fernet

from auth import build_auth_service_from_env
from auth.service import AuthConfigurationError, SupabaseAuthService


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


if __name__ == "__main__":
    unittest.main()
