#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from auth.service import AuthConfigurationError, build_auth_service_from_env
from runtime_env import load_app_env


def _is_local_app_base_url(value: str | None, *, port: str) -> bool:
    if value is None:
        return False
    normalized = value.rstrip("/")
    return normalized in {
        f"http://localhost:{port}",
        f"http://127.0.0.1:{port}",
    }


def _status_line(name: str, present: bool) -> str:
    return f"  {name}: {'present' if present else 'missing'}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate localhost auth config without printing secrets."
    )
    parser.add_argument(
        "--probe-guest",
        action="store_true",
        help="Also call Supabase anonymous sign-in to prove guest login works.",
    )
    parser.add_argument(
        "--port",
        default=os.getenv("PORT", "8000"),
        help="Local server port expected in APP_BASE_URL.",
    )
    args = parser.parse_args(argv)

    report = load_app_env(REPO_ROOT)
    service = build_auth_service_from_env()
    missing = service.missing_required_settings()
    issues: list[str] = []

    print("Local auth preflight")
    print("Loaded env files: " + (", ".join(report.loaded_files) or "none"))
    if report.skipped_local_reason:
        print("Skipped .env.local: " + report.skipped_local_reason)
    print(f"AUTH_ENABLED: {str(service.enabled).lower()}")
    for name, present in [
        ("SUPABASE_URL", bool(service.supabase_url)),
        ("SUPABASE_PUBLISHABLE_KEY", bool(service.publishable_key)),
        ("SUPABASE_JWT_SECRET", bool(service.jwt_secret)),
        ("SESSION_COOKIE_KEY", bool(service.session_cookie_key)),
        ("APP_BASE_URL", bool(service.app_base_url)),
    ]:
        print(_status_line(name, present))

    if not service.enabled:
        issues.append("AUTH_ENABLED must be true for the localhost login wall.")
    if missing:
        issues.append("Missing required auth settings: " + ", ".join(missing))
    if service.app_base_url and not _is_local_app_base_url(
        service.app_base_url, port=args.port
    ):
        issues.append(
            f"APP_BASE_URL should be http://localhost:{args.port} for this local server."
        )

    if issues:
        print("\nFAIL")
        for issue in issues:
            print(f"- {issue}")
        print("\nFix .env or .env.local, then restart uvicorn.")
        return 1

    try:
        callback_uri = service.callback_redirect_uri()
    except AuthConfigurationError as err:
        print("\nFAIL")
        print(f"- {err}")
        return 1

    print(f"Callback URI: {callback_uri}")

    if args.probe_guest:
        try:
            state = service.sign_in_anonymously()
        except Exception as err:
            print("\nFAIL")
            print(f"- Guest sign-in probe failed: {type(err).__name__}")
            return 1
        if not (state.authenticated and state.guest_mode and state.sealed_session):
            print("\nFAIL")
            print("- Guest sign-in did not return an anonymous session.")
            return 1
        print("Guest sign-in probe: ok")

    print("\nOK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
