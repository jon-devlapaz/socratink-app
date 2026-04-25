"""URL builders for Supabase auth endpoints."""

from __future__ import annotations

from urllib.parse import urlencode


def build_google_authorize_url(
    *,
    supabase_url: str,
    redirect_to: str,
    state_nonce: str,
    code_challenge: str,
) -> str:
    """Return the GET URL for `/auth/v1/authorize` with provider=google + PKCE params."""
    base = supabase_url.rstrip("/")
    qs = urlencode(
        {
            "provider": "google",
            "redirect_to": redirect_to,
            "state": state_nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
    )
    return f"{base}/auth/v1/authorize?{qs}"
