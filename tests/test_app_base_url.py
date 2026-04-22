"""S13 — APP_BASE_URL is the source of truth for OAuth redirect URIs.

Prevents host-header spoofing on Vercel.
"""

import unittest

from cryptography.fernet import Fernet

from auth.service import AuthConfigurationError, SupabaseAuthService


SESSION_KEY = Fernet.generate_key().decode()


class AppBaseUrlTests(unittest.TestCase):
    def test_redirect_uri_uses_env_app_base_url(self):
        svc = SupabaseAuthService(
            enabled=True,
            supabase_url="https://abc.supabase.co",
            publishable_key="pk",
            jwt_secret="js",
            session_cookie_key=SESSION_KEY,
            app_base_url="https://socratink.app",
        )
        self.assertEqual(
            svc.callback_redirect_uri(),
            "https://socratink.app/auth/callback",
        )

    def test_trailing_slash_normalized(self):
        svc = SupabaseAuthService(
            enabled=True,
            supabase_url="https://abc.supabase.co",
            publishable_key="pk",
            jwt_secret="js",
            session_cookie_key=SESSION_KEY,
            app_base_url="https://socratink.app/",
        )
        self.assertEqual(
            svc.callback_redirect_uri(),
            "https://socratink.app/auth/callback",
        )

    def test_missing_app_base_url_raises_when_enabled(self):
        svc = SupabaseAuthService(
            enabled=True,
            supabase_url="https://abc.supabase.co",
            publishable_key="pk",
            jwt_secret="js",
            session_cookie_key=SESSION_KEY,
            app_base_url=None,
        )
        with self.assertRaises(AuthConfigurationError):
            svc.callback_redirect_uri()


if __name__ == "__main__":
    unittest.main()
