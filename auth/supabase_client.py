"""Stateless per-call Supabase client factory.

Vercel-serverless-safe: never reuse client across requests; never persist sessions.
"""

from __future__ import annotations

from supabase import ClientOptions, create_client

from auth.service import AuthConfigurationError


def build_supabase_client(supabase_url: str, publishable_key: str):
    """Return a fresh Supabase client with persist_session and auto_refresh disabled."""
    if not supabase_url:
        raise AuthConfigurationError("SUPABASE_URL is required.")
    if not publishable_key:
        raise AuthConfigurationError("SUPABASE_PUBLISHABLE_KEY is required.")
    options = ClientOptions(persist_session=False, auto_refresh_token=False)
    return create_client(supabase_url, publishable_key, options=options)
