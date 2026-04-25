"""URL builders for Supabase auth endpoints."""

from __future__ import annotations

from urllib.parse import urlencode


def build_google_authorize_url(
    *,
    supabase_url: str,
    redirect_to: str,
    code_challenge: str,
) -> str:
    """Return the GET URL for `/auth/v1/authorize` with provider=google + PKCE params.

    Note: we deliberately do NOT pass a `state` query param. Supabase Auth
    manages its own JWT-encoded state cookie internally and rejects the flow
    with bad_oauth_state if our state collides with theirs. CSRF protection
    on our side comes from the signed (HMAC) cookie that carries the
    code_verifier and return_to — see auth/oauth_state.py.
    """
    base = supabase_url.rstrip("/")
    qs = urlencode(
        {
            "provider": "google",
            "redirect_to": redirect_to,
            "code_challenge": code_challenge,
            # Supabase auth server expects lowercase "s256"; uppercase "S256"
            # silently falls through to "plain" mode and the verifier never
            # matches the challenge at exchange time. The supabase-py SDK
            # itself sends "s256" (gotrue_client.py:1175).
            "code_challenge_method": "s256",
        }
    )
    return f"{base}/auth/v1/authorize?{qs}"
