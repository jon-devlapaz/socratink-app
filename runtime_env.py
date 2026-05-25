from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values, load_dotenv


_TRUTHY = {"1", "true", "yes", "on"}
_FALSEY = {"0", "false", "no", "off"}
_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1", "testclient"}


@dataclass(frozen=True)
class EnvLoadReport:
    """Safe-to-log summary of app env loading.

    Precedence is intentionally:
    process env > .env.local > .env

    That keeps deployed/server-provided secrets authoritative while allowing
    ignored local overrides to replace template values from .env.
    """

    loaded_files: tuple[str, ...]
    skipped_local_reason: str | None = None


def _truthy_env(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in _TRUTHY


def _falsey_env(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in _FALSEY


def _production_runtime_detected() -> bool:
    if _truthy_env("VERCEL"):
        return True
    if os.getenv("VERCEL_ENV"):
        return True
    if _truthy_env("CI"):
        return True
    return False


def dev_autoguest_enabled() -> bool:
    """Local-only dev mode flag.

    When SOCRATINK_DEV_AUTOGUEST is truthy AND no production-shaped env
    markers are present (VERCEL, VERCEL_ENV, CI), the launcher has opted
    into local guest convenience. Request handlers must still call
    local_auth_bypass_enabled(hostname=..., client_host=...) before bypassing
    auth or exposing frontend dev_mode.

    Two effects depend on the request-aware local auth bypass:
      1. main.py auth gate trampolines the /login redirect through
         /auth/guest so agents and ad-hoc local browsing skip the wall.
      2. /api/me returns dev_mode=True as a compatibility signal for local
         tooling; current browser auth behavior is handled by the server-side
         auth routes and gate.

    SECURITY ASSUMPTION (load-bearing — read before changing).
    --------------------------------------------------------
    This launcher flag is DENY-LIST shaped: it is on for any environment
    that does not look like Vercel or CI. Today the assumption is safe because
    SOCRATINK_DEV_AUTOGUEST is only set by `scripts/dev.sh`, which only runs
    locally, and the actual bypass also requires SOCRATINK_LOCAL_AUTH_BYPASS
    not to be falsey plus loopback hostname/client checks.

    If you start setting SOCRATINK_DEV_AUTOGUEST anywhere other than a
    developer's local machine — e.g. a non-Vercel staging box, a
    self-hosted preview, a docker-compose'd integration env — this function
    may return True there, but local_auth_bypass_enabled must continue to
    reject non-loopback requests before /api/me exposes `dev_mode: true` or
    auth routes mint a local guest session. Either:

      (a) extend the deny-list with a marker for the new env (preferred:
          a positive `SOCRATINK_LOCAL=1` allow-list signal that
          `scripts/dev.sh` sets explicitly, then flip this function to
          allow-list shape — require BOTH SOCRATINK_DEV_AUTOGUEST AND
          SOCRATINK_LOCAL), OR
      (b) leave SOCRATINK_DEV_AUTOGUEST unset on the new env (the
          conservative default; production-shaped env markers below are
          a backstop, not the contract).

    Tests in tests/test_auth_gate_supabase.py cover the Vercel-shadowing
    case but cannot cover envs we have not invented yet.
    """
    if not _truthy_env("SOCRATINK_DEV_AUTOGUEST"):
        return False
    if _production_runtime_detected():
        return False
    return True


def _normalize_host(host: str | None) -> str:
    return (host or "").strip().lower().strip("[]")


def _is_loopback_host(host: str | None) -> bool:
    return _normalize_host(host) in _LOOPBACK_HOSTS


def local_auth_bypass_enabled(
    *, hostname: str | None = None, client_host: str | None = None
) -> bool:
    """Allow localhost development to enter as a sealed local guest.

    This is the request-aware replacement for relying solely on
    SOCRATINK_DEV_AUTOGUEST. Repo-owned local launchers opt into this path, but
    production-shaped runtimes and non-loopback requests must still see the
    normal auth wall.
    """
    if _production_runtime_detected():
        return False
    if _falsey_env("SOCRATINK_LOCAL_AUTH_BYPASS"):
        return False
    if not (dev_autoguest_enabled() or _truthy_env("SOCRATINK_LOCAL_AUTH_BYPASS")):
        return False
    return _is_loopback_host(hostname) and _is_loopback_host(client_host)


def _should_load_dotenv_local() -> tuple[bool, str | None]:
    if _truthy_env("SOCRATINK_DISABLE_DOTENV_LOCAL"):
        return False, "SOCRATINK_DISABLE_DOTENV_LOCAL is set"
    if _truthy_env("VERCEL") or os.getenv("VERCEL_ENV"):
        return False, "Vercel runtime env detected"
    if _truthy_env("CI"):
        return False, "CI runtime env detected"
    return True, None


def _apply_dotenv_local(path: Path, *, protected_keys: set[str]) -> bool:
    values = dotenv_values(path)
    applied = False
    for key, value in values.items():
        if not key or value is None:
            continue
        if key in protected_keys:
            continue
        os.environ[key] = value
        applied = True
    return applied


def load_app_env(root: str | Path | None = None) -> EnvLoadReport:
    """Load the app's dotenv files with production-safe local precedence.

    python-dotenv's plain override modes are not quite right for this app:
    `.env.local` must beat checked-in/template `.env` values on localhost, but
    a real process env var from Vercel, CI, or a developer's shell must still
    win. This helper preserves that ordering and is tested because auth startup
    depends on it.
    """

    repo_root = Path(root) if root is not None else Path(__file__).resolve().parent
    protected_keys = set(os.environ)
    loaded: list[str] = []

    env_path = repo_root / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)
        loaded.append(".env")

    local_path = repo_root / ".env.local"
    should_load_local, skip_reason = _should_load_dotenv_local()
    if not local_path.exists():
        skip_reason = ".env.local not found"
    elif should_load_local:
        if _apply_dotenv_local(local_path, protected_keys=protected_keys):
            loaded.append(".env.local")
        skip_reason = None

    return EnvLoadReport(
        loaded_files=tuple(loaded),
        skipped_local_reason=skip_reason,
    )
