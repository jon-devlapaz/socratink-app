"""S6 — Supabase client factory. Stateless, fresh per call, serverless-safe."""

import unittest
from unittest.mock import patch

from auth.supabase_client import build_supabase_client
from auth.service import AuthConfigurationError


URL = "https://abc123.supabase.co"
KEY = "test-publishable-key"


class BuildSupabaseClientTests(unittest.TestCase):
    def test_passes_persist_session_false(self):
        with patch("auth.supabase_client.create_client") as create:
            build_supabase_client(URL, KEY)
            _, kwargs = create.call_args
            options = kwargs.get("options") or create.call_args[0][2]
            # ClientOptions exposes persist_session and auto_refresh_token
            self.assertFalse(getattr(options, "persist_session", True))
            self.assertFalse(getattr(options, "auto_refresh_token", True))

    def test_returns_fresh_instance_per_call(self):
        with patch("auth.supabase_client.create_client") as create:
            create.side_effect = lambda *a, **kw: object()
            a = build_supabase_client(URL, KEY)
            b = build_supabase_client(URL, KEY)
            self.assertIsNot(a, b)

    def test_missing_url_raises(self):
        with self.assertRaises(AuthConfigurationError):
            build_supabase_client("", KEY)

    def test_missing_key_raises(self):
        with self.assertRaises(AuthConfigurationError):
            build_supabase_client(URL, "")


if __name__ == "__main__":
    unittest.main()
