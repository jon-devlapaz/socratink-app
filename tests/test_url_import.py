import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import main
from auth import GUEST_COOKIE_NAME
from auth.service import AuthSessionState


class FakeAuthService:
    def __init__(self, *, enabled=True):
        self.enabled = enabled
        self.cookie_name = "wos_session"
        self.cookie_samesite = "lax"
        self.cookie_max_age = 120
        self.oauth_state_cookie_name = "wos_oauth_state"
        self.oauth_state_ttl_seconds = 600
        self.current_state = AuthSessionState(auth_enabled=enabled, authenticated=False)

    def load_session(self, sealed_session: str | None):
        return self.current_state

    def resolve_cookie_secure(self, base_url: str) -> bool:
        return base_url.startswith("https://")


class FakeHeaders(dict):
    def get_content_charset(self):
        return "utf-8"


class FakeUrlResponse:
    def __init__(self, body: str):
        self.headers = FakeHeaders({"Content-Type": "text/html; charset=utf-8"})
        self._body = body.encode("utf-8")

    def read(self, _size=None):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class UrlImportTests(unittest.TestCase):
    def setUp(self):
        self.original_service = main.app.state.auth_service

    def tearDown(self):
        main.app.state.auth_service = self.original_service

    def build_client(self) -> TestClient:
        main.app.state.auth_service = FakeAuthService(enabled=True)
        client = TestClient(main.app)
        client.cookies.set(GUEST_COOKIE_NAME, "guest")
        return client

    def test_extract_url_blocks_youtube_hosts(self):
        client = self.build_client()

        response = client.post(
            "/api/extract-url", json={"url": "https://www.youtube.com/watch?v=abc123"}
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"],
            "Video links are not supported in this deployment. Paste the text directly instead.",
        )

    def test_extract_url_does_not_block_non_youtube_domains(self):
        client = self.build_client()
        fake_html = """
        <html>
          <title>Demo</title>
          <p>
            This page has enough readable text to import into Socratink for testing purposes.
            It intentionally includes multiple sentences so the extractor clears the readable-text
            threshold and exercises the non-YouTube URL import path without making an external network call.
          </p>
        </html>
        """

        with (
            patch("main._is_private_url", return_value=False),
            patch(
                "main.urlopen",
                return_value=FakeUrlResponse(fake_html),
            ),
        ):
            response = client.post(
                "/api/extract-url", json={"url": "https://notyoutube.com/article"}
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["title"], "Demo")
        self.assertIn("enough readable text", payload["text"])


if __name__ == "__main__":
    unittest.main()
