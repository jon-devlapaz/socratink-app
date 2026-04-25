"""S3 — Supabase /auth/v1/authorize URL builder. Pure."""

import unittest
from urllib.parse import parse_qs, urlparse

from auth.supabase_urls import build_google_authorize_url


SUPABASE_URL = "https://abc123.supabase.co"
REDIRECT_URI = "http://localhost:8000/auth/callback"
CHALLENGE = "ch_abcdef0123456789"


class BuildAuthorizeUrlTests(unittest.TestCase):
    def setUp(self):
        url = build_google_authorize_url(
            supabase_url=SUPABASE_URL,
            redirect_to=REDIRECT_URI,
            code_challenge=CHALLENGE,
        )
        self.parsed = urlparse(url)
        self.qs = {k: v[0] for k, v in parse_qs(self.parsed.query).items()}

    def test_targets_supabase_authorize_endpoint(self):
        self.assertEqual(self.parsed.scheme, "https")
        self.assertEqual(self.parsed.netloc, "abc123.supabase.co")
        self.assertEqual(self.parsed.path, "/auth/v1/authorize")

    def test_provider_google(self):
        self.assertEqual(self.qs["provider"], "google")

    def test_redirect_to_unmodified(self):
        self.assertEqual(self.qs["redirect_to"], REDIRECT_URI)

    def test_no_state_param(self):
        # Supabase manages state internally; sending our own caused bad_oauth_state.
        self.assertNotIn("state", self.qs)

    def test_pkce_params_present(self):
        self.assertEqual(self.qs["code_challenge"], CHALLENGE)
        # Supabase server requires lowercase "s256" — uppercase falls through
        # to "plain" silently and breaks the exchange.
        self.assertEqual(self.qs["code_challenge_method"], "s256")

    def test_strips_trailing_slash_on_supabase_url(self):
        url = build_google_authorize_url(
            supabase_url=SUPABASE_URL + "/",
            redirect_to=REDIRECT_URI,
            code_challenge=CHALLENGE,
        )
        self.assertIn("https://abc123.supabase.co/auth/v1/authorize", url)
        self.assertNotIn("//auth/v1", url)


if __name__ == "__main__":
    unittest.main()
