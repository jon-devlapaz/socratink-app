#!/usr/bin/env python3

import argparse
import base64
import hashlib
import json
import re
import secrets
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel


REPO_ROOT = Path(__file__).resolve().parent.parent
RUNTIME_DIR = REPO_ROOT / ".agents" / "runtime"
AUTH_PATH = RUNTIME_DIR / "push-auth.json"
LOG_PATH = RUNTIME_DIR / "push-decisions.jsonl"

PUBLIC_REMOTE_PATTERNS = [r"^https://github\.com/jon-devlapaz/socratink-app\.git$"]
NO_MISTAKES_PATTERNS = [r"(^|/|\\)\.no-mistakes([/\\])repos([/\\])[0-9a-f]+\.git$"]

HIGH_RISK_PREFIXES = (
    "main.py",
    "api/index.py",
    "ai_service.py",
    "auth/",
    "vercel.json",
    ".github/workflows/",
    "requirements.txt",
    "requirements-dev.txt",
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "agents/",
    "docs/codex/onboarding.md",
    "docs/codex/agent-quality.md",
    "scripts/bootstrap-python.sh",
    "scripts/doctor.sh",
    "scripts/check-coverage.sh",
    "scripts/git-hooks/",
)


@dataclass(frozen=True)
class PushState:
    branch: str
    head_sha: str
    dirty: bool
    changed_paths: list[str]
    remote_urls: dict[str, str]


@dataclass(frozen=True)
class RouteRecommendation:
    route: str
    risk_class: str
    triggers: list[str]


class AuthorizationPayload(BaseModel):
    branch: str
    head_sha: str
    dirty: bool
    route: str
    remote_url: str
    refspec: str
    diff_fingerprint: str
    risk_class: str
    nonce: str
    issued_at_epoch: int


def _run_git(args: list[str], *, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {message}")
    return result.stdout.strip()


def _split_lines(value: str) -> list[str]:
    return [line.strip() for line in value.splitlines() if line.strip()]


def _remote_urls() -> dict[str, str]:
    urls: dict[str, str] = {}
    for line in _split_lines(_run_git(["remote", "-v"])):
        parts = line.split()
        if len(parts) >= 3 and parts[2] == "(push)":
            urls[parts[0]] = parts[1]
    return urls


def _changed_paths() -> list[str]:
    paths: set[str] = set()
    for command in (
        ["diff", "--name-only", "--cached"],
        ["diff", "--name-only", "HEAD"],
        ["ls-files", "--others", "--exclude-standard"],
    ):
        paths.update(_split_lines(_run_git(command, check=False)))
    return sorted(paths)


def collect_state() -> PushState:
    branch = _run_git(["symbolic-ref", "--short", "HEAD"])
    head_sha = _run_git(["rev-parse", "HEAD"])
    dirty = bool(_run_git(["status", "--porcelain"], check=False))
    return PushState(
        branch=branch,
        head_sha=head_sha,
        dirty=dirty,
        changed_paths=_changed_paths(),
        remote_urls=_remote_urls(),
    )


def recommend_route(state: PushState, explicit_target: str | None) -> RouteRecommendation:
    if explicit_target:
        return _recommend_explicit_route(explicit_target)
    if state.branch.startswith("feat/"):
        return RouteRecommendation(
            route=f"origin/{state.branch}",
            risk_class="confirm",
            triggers=["feature_branch"],
        )
    high_risk = [path for path in state.changed_paths if path.startswith(HIGH_RISK_PREFIXES)]
    if high_risk:
        return RouteRecommendation(
            route="no-mistakes/dev",
            risk_class="confirm",
            triggers=high_risk,
        )
    return RouteRecommendation(
        route="origin/dev",
        risk_class="confirm",
        triggers=["default_dev_publication"],
    )


def _recommend_explicit_route(target: str) -> RouteRecommendation:
    if target in {"origin/main", "main"}:
        return RouteRecommendation(route="origin/main", risk_class="hard-confirm", triggers=["main"])
    if target in {"origin/dev", "dev"}:
        return RouteRecommendation(route="origin/dev", risk_class="confirm", triggers=["explicit_target"])
    if target in {"no-mistakes/dev", "no-mistakes"}:
        return RouteRecommendation(route="no-mistakes/dev", risk_class="confirm", triggers=["explicit_target"])
    if target.startswith("origin/feat/"):
        return RouteRecommendation(route=target, risk_class="confirm", triggers=["explicit_feature_target"])
    if target.startswith("feat/"):
        return RouteRecommendation(route=f"origin/{target}", risk_class="confirm", triggers=["explicit_feature_target"])
    raise ValueError(f"unsupported push target: {target}")


def route_to_remote_refspec(route: str) -> tuple[str, str]:
    if "/" not in route:
        raise ValueError(f"invalid route: {route}")
    remote, refspec = route.split("/", 1)
    if remote not in {"origin", "no-mistakes"}:
        raise ValueError(f"unsupported remote: {remote}")
    if refspec not in {"dev", "main"} and not refspec.startswith("feat/"):
        raise ValueError(f"unsupported refspec: {refspec}")
    return remote, refspec


def _trusted_remote(remote: str, url: str) -> bool:
    patterns = NO_MISTAKES_PATTERNS if remote == "no-mistakes" else PUBLIC_REMOTE_PATTERNS
    return any(re.search(pattern, url) for pattern in patterns)


def diff_fingerprint(state: PushState) -> str:
    payload = {
        "dirty": state.dirty,
        "changed_paths": sorted(state.changed_paths),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_payload(state: PushState, recommendation: RouteRecommendation) -> AuthorizationPayload:
    remote, refspec = route_to_remote_refspec(recommendation.route)
    remote_url = state.remote_urls.get(remote)
    if not remote_url:
        raise ValueError(f"remote {remote!r} is not configured")
    if not _trusted_remote(remote, remote_url):
        raise ValueError(f"remote {remote!r} URL is not trusted: {remote_url}")
    return AuthorizationPayload(
        branch=state.branch,
        head_sha=state.head_sha,
        dirty=state.dirty,
        route=recommendation.route,
        remote_url=remote_url,
        refspec=refspec,
        diff_fingerprint=diff_fingerprint(state),
        risk_class=recommendation.risk_class,
        nonce=secrets.token_urlsafe(16),
        issued_at_epoch=int(time.time()),
    )


def encode_ack(payload: AuthorizationPayload) -> str:
    raw = payload.model_dump_json().encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def decode_ack(token: str) -> AuthorizationPayload:
    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii"))
        return AuthorizationPayload.model_validate_json(raw)
    except Exception as exc:
        raise ValueError("invalid ack token") from exc


def intent_matches(original: AuthorizationPayload, current: AuthorizationPayload) -> bool:
    material_fields = (
        "branch",
        "head_sha",
        "dirty",
        "route",
        "remote_url",
        "refspec",
        "diff_fingerprint",
        "risk_class",
    )
    return all(getattr(original, field) == getattr(current, field) for field in material_fields)


def write_authorization(payload: AuthorizationPayload) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    AUTH_PATH.write_text(payload.model_dump_json(indent=2), encoding="utf-8")


def append_decision_log(payload: AuthorizationPayload, triggers: list[str], *, override: bool) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": int(time.time()),
        "branch": payload.branch,
        "target_remote": payload.route.split("/", 1)[0],
        "target_refspec": payload.refspec,
        "remote_url": payload.remote_url,
        "head_sha": payload.head_sha,
        "recommended_route": payload.route,
        "chosen_route": payload.route,
        "override": override,
        "triggered_rules": triggers,
        "ack_mode": "typed-token",
    }
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")


def _print_first_run(payload: AuthorizationPayload, recommendation: RouteRecommendation) -> None:
    token = encode_ack(payload)
    print(f"Recommended route: {recommendation.route}")
    print(f"Risk class: {recommendation.risk_class}")
    print(f"Triggered rules: {', '.join(recommendation.triggers)}")
    print("No push executed. Re-run with this ack token to publish:")
    print(f"python3 scripts/agent-push.py --target {recommendation.route} --ack {token}")


def _push(payload: AuthorizationPayload) -> int:
    remote, refspec = route_to_remote_refspec(payload.route)
    result = subprocess.run(["git", "push", remote, refspec], cwd=REPO_ROOT)
    if AUTH_PATH.exists():
        AUTH_PATH.unlink()
    return result.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Authorize and execute one Socratink git publication.")
    parser.add_argument("--target", help="publication target, e.g. origin/dev, origin/feat/name, no-mistakes/dev")
    parser.add_argument("--ack", help="ack token printed by the first run")
    args = parser.parse_args(argv)

    try:
        state = collect_state()
        recommendation = recommend_route(state, explicit_target=args.target)
        payload = build_payload(state, recommendation)
    except Exception as exc:
        print(f"[agent-push] ERROR: {exc}", file=sys.stderr)
        return 2

    if not args.ack:
        _print_first_run(payload, recommendation)
        return 1

    try:
        original = decode_ack(args.ack)
    except ValueError as exc:
        print(f"[agent-push] ERROR: {exc}", file=sys.stderr)
        return 2

    if not intent_matches(original, payload):
        print("[agent-push] ERROR: push intent changed since ack was issued", file=sys.stderr)
        return 2

    write_authorization(payload)
    append_decision_log(payload, recommendation.triggers, override=payload.route != recommendation.route)
    return _push(payload)


if __name__ == "__main__":
    raise SystemExit(main())
