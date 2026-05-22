import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "agent-push.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("agent_push", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_dev_branch_recommends_origin_dev_for_narrow_change(tmp_path):
    mod = _load_module()
    state = mod.PushState(
        branch="dev",
        head_sha="abc1234",
        dirty=False,
        changed_paths=["public/js/app.js"],
        remote_urls={"origin": "https://github.com/jon-devlapaz/socratink-app.git"},
    )
    recommendation = mod.recommend_route(state, explicit_target=None)
    assert recommendation.route == "origin/dev"


def test_feature_branch_recommends_origin_feature_branch(tmp_path):
    mod = _load_module()
    state = mod.PushState(
        branch="feat/demo-flow",
        head_sha="abc1234",
        dirty=False,
        changed_paths=["public/js/app.js"],
        remote_urls={"origin": "https://github.com/jon-devlapaz/socratink-app.git"},
    )
    recommendation = mod.recommend_route(state, explicit_target=None)
    assert recommendation.route == "origin/feat/demo-flow"


def test_high_risk_paths_recommend_no_mistakes(tmp_path):
    mod = _load_module()
    state = mod.PushState(
        branch="dev",
        head_sha="abc1234",
        dirty=False,
        changed_paths=["main.py", "docs/codex/onboarding.md"],
        remote_urls={
            "origin": "https://github.com/jon-devlapaz/socratink-app.git",
            "no-mistakes": "/Users/example/.no-mistakes/repos/deadbeef.git",
        },
    )
    recommendation = mod.recommend_route(state, explicit_target=None)
    assert recommendation.route == "no-mistakes/dev"


def test_publication_diff_paths_are_included_after_commit(monkeypatch):
    mod = _load_module()

    def fake_run_git(args, *, check=True):
        if args == ["symbolic-ref", "--short", "HEAD"]:
            return "dev"
        if args == ["diff", "--name-only", "origin/dev...HEAD"]:
            return "main.py\n"
        return ""

    monkeypatch.setattr(mod, "_run_git", fake_run_git)

    assert mod._changed_paths() == ["main.py"]


def test_refresh_publication_refs_updates_origin_dev(monkeypatch):
    mod = _load_module()
    calls = []

    def fake_run_git(args, *, check=True):
        calls.append(args)
        if args == ["remote", "-v"]:
            return "origin\thttps://github.com/jon-devlapaz/socratink-app.git (push)"
        return ""

    monkeypatch.setattr(mod, "_run_git", fake_run_git)

    mod.refresh_publication_refs()

    assert calls == [
        ["remote", "-v"],
        ["fetch", "origin", "+refs/heads/dev:refs/remotes/origin/dev"],
    ]


def test_refresh_publication_refs_updates_no_mistakes_dev_when_configured(monkeypatch):
    mod = _load_module()
    calls = []

    def fake_run_git(args, *, check=True):
        calls.append((args, check))
        if args == ["remote", "-v"]:
            return "\n".join(
                (
                    "origin\thttps://github.com/jon-devlapaz/socratink-app.git (push)",
                    "no-mistakes\t/tmp/.no-mistakes/repos/review-gate.git (push)",
                )
            )
        return ""

    monkeypatch.setattr(mod, "_run_git", fake_run_git)

    mod.refresh_publication_refs()

    assert calls == [
        (["remote", "-v"], True),
        (["fetch", "origin", "+refs/heads/dev:refs/remotes/origin/dev"], True),
        (["fetch", "no-mistakes", "+refs/heads/dev:refs/remotes/no-mistakes/dev"], False),
    ]


def test_explicit_target_records_override_against_recommendation(tmp_path):
    mod = _load_module()
    state = mod.PushState(
        branch="dev",
        head_sha="abc1234",
        dirty=False,
        changed_paths=["main.py"],
        remote_urls={
            "origin": "https://github.com/jon-devlapaz/socratink-app.git",
            "no-mistakes": "/tmp/.no-mistakes/repos/review-gate.git",
        },
    )

    intent = mod.resolve_publication_intent(state, explicit_target="origin/dev")

    assert intent.recommendation.route == "no-mistakes/dev"
    assert intent.chosen_route == "origin/dev"
    assert intent.override is True


def test_explicit_origin_main_payload_escalates_to_hard_confirm(tmp_path):
    mod = _load_module()
    state = mod.PushState(
        branch="dev",
        head_sha="abc1234",
        dirty=False,
        changed_paths=["public/js/app.js"],
        remote_urls={"origin": "https://github.com/jon-devlapaz/socratink-app.git"},
    )

    intent = mod.resolve_publication_intent(state, explicit_target="origin/main")
    payload = mod.build_payload(state, intent)

    assert intent.recommendation.route == "origin/dev"
    assert intent.chosen_route == "origin/main"
    assert intent.override is True
    assert payload.risk_class == "hard-confirm"


def test_explicit_non_main_payload_targets_remain_confirm(tmp_path):
    mod = _load_module()
    state = mod.PushState(
        branch="dev",
        head_sha="abc1234",
        dirty=False,
        changed_paths=["public/js/app.js"],
        remote_urls={
            "origin": "https://github.com/jon-devlapaz/socratink-app.git",
            "no-mistakes": "/tmp/.no-mistakes/repos/review-gate.git",
        },
    )

    for target in ("origin/dev", "origin/feat/demo-flow", "no-mistakes/dev"):
        intent = mod.resolve_publication_intent(state, explicit_target=target)
        payload = mod.build_payload(state, intent)
        assert payload.route == target
        assert payload.risk_class == "confirm"


def test_decision_log_preserves_recommended_and_chosen_routes(tmp_path, monkeypatch):
    mod = _load_module()
    monkeypatch.setattr(mod, "RUNTIME_DIR", tmp_path)
    monkeypatch.setattr(mod, "LOG_PATH", tmp_path / "push-decisions.jsonl")
    recommendation = mod.RouteRecommendation(
        route="no-mistakes/dev",
        risk_class="confirm",
        triggers=["main.py"],
    )
    intent = mod.PublicationIntent(recommendation=recommendation, chosen_route="origin/dev")
    payload = mod.AuthorizationPayload(
        branch="dev",
        head_sha="abc1234",
        dirty=False,
        route="origin/dev",
        remote_url="https://github.com/jon-devlapaz/socratink-app.git",
        refspec="dev",
        diff_fingerprint="fingerprint-1",
        risk_class="confirm",
        nonce="nonce-1",
        issued_at_epoch=1,
    )

    mod.append_decision_log(payload, intent)

    entry = json.loads((tmp_path / "push-decisions.jsonl").read_text(encoding="utf-8"))
    assert entry["recommended_route"] == "no-mistakes/dev"
    assert entry["chosen_route"] == "origin/dev"
    assert entry["override"] is True


def test_trusted_remote_patterns_accept_forks_ssh_and_generic_no_mistakes(tmp_path):
    mod = _load_module()

    assert mod._trusted_remote("origin", "git@github.com:someone/socratink-app.git")
    assert mod._trusted_remote("origin", "https://github.com/someone/socratink-app.git")
    assert mod._trusted_remote("no-mistakes", "/tmp/.no-mistakes/repos/review-gate.git")


def test_ack_payload_invalidates_when_head_changes(tmp_path):
    mod = _load_module()
    payload = mod.AuthorizationPayload(
        branch="dev",
        head_sha="abc1234",
        dirty=False,
        route="origin/dev",
        remote_url="https://github.com/jon-devlapaz/socratink-app.git",
        refspec="dev",
        diff_fingerprint="fingerprint-1",
        risk_class="confirm",
        nonce="nonce-1",
        issued_at_epoch=1,
    )
    current = payload.model_copy(update={"head_sha": "fffffff"})
    assert not mod.intent_matches(payload, current)


def test_dev_publication_blocks_when_origin_dev_is_ahead(monkeypatch):
    mod = _load_module()
    state = mod.PushState(
        branch="dev",
        head_sha="abc1234",
        dirty=False,
        changed_paths=["docs/project/state.md"],
        remote_urls={"origin": "https://github.com/jon-devlapaz/socratink-app.git"},
    )
    intent = mod.resolve_publication_intent(state, explicit_target="origin/dev")

    def fake_run_git(args, *, check=True):
        if args == ["rev-parse", "--verify", "origin/dev"]:
            return "origin/dev"
        if args == ["rev-list", "--left-right", "--count", "origin/dev...HEAD"]:
            return "3\t1"
        raise AssertionError(f"unexpected git call: {args}")

    monkeypatch.setattr(mod, "_run_git", fake_run_git)

    try:
        mod.ensure_current_dev_base(state, intent)
    except RuntimeError as exc:
        assert "local dev is behind origin/dev by 3 commit(s)" in str(exc)
    else:
        raise AssertionError("stale dev publication was not blocked")


def test_dev_publication_allows_origin_dev_ancestor(monkeypatch):
    mod = _load_module()
    state = mod.PushState(
        branch="dev",
        head_sha="abc1234",
        dirty=False,
        changed_paths=["docs/project/state.md"],
        remote_urls={"origin": "https://github.com/jon-devlapaz/socratink-app.git"},
    )
    intent = mod.resolve_publication_intent(state, explicit_target="no-mistakes/dev")

    def fake_run_git(args, *, check=True):
        if args == ["rev-parse", "--verify", "origin/dev"]:
            return "origin/dev"
        if args == ["rev-list", "--left-right", "--count", "origin/dev...HEAD"]:
            return "0\t2"
        raise AssertionError(f"unexpected git call: {args}")

    monkeypatch.setattr(mod, "_run_git", fake_run_git)

    mod.ensure_current_dev_base(state, intent)


def test_no_mistakes_publication_blocks_when_destination_is_not_ancestor(monkeypatch):
    mod = _load_module()
    state = mod.PushState(
        branch="dev",
        head_sha="abc1234",
        dirty=False,
        changed_paths=["main.py"],
        remote_urls={
            "origin": "https://github.com/jon-devlapaz/socratink-app.git",
            "no-mistakes": "/tmp/.no-mistakes/repos/review-gate.git",
        },
    )
    intent = mod.resolve_publication_intent(state, explicit_target="no-mistakes/dev")

    def fake_run_git(args, *, check=True):
        if args == ["rev-parse", "--verify", "refs/remotes/no-mistakes/dev"]:
            return "refs/remotes/no-mistakes/dev"
        if args == [
            "rev-list",
            "--left-right",
            "--count",
            "refs/remotes/no-mistakes/dev...HEAD",
        ]:
            return "14\t2"
        raise AssertionError(f"unexpected git call: {args}")

    monkeypatch.setattr(mod, "_run_git", fake_run_git)
    monkeypatch.setattr(mod, "_git_succeeds", lambda args: False)

    try:
        mod.ensure_destination_fast_forward(state, intent)
    except RuntimeError as exc:
        message = str(exc)
        assert "destination no-mistakes/dev is not an ancestor of local dev" in message
        assert "git cherry -v no-mistakes/dev HEAD" in message
    else:
        raise AssertionError("non-fast-forward no-mistakes destination was not blocked")


def test_publication_allows_destination_ancestor(monkeypatch):
    mod = _load_module()
    state = mod.PushState(
        branch="dev",
        head_sha="abc1234",
        dirty=False,
        changed_paths=["main.py"],
        remote_urls={"no-mistakes": "/tmp/.no-mistakes/repos/review-gate.git"},
    )
    intent = mod.resolve_publication_intent(state, explicit_target="no-mistakes/dev")

    def fake_run_git(args, *, check=True):
        if args == ["rev-parse", "--verify", "refs/remotes/no-mistakes/dev"]:
            return "refs/remotes/no-mistakes/dev"
        raise AssertionError(f"unexpected git call: {args}")

    monkeypatch.setattr(mod, "_run_git", fake_run_git)
    monkeypatch.setattr(mod, "_git_succeeds", lambda args: True)

    mod.ensure_destination_fast_forward(state, intent)


def test_dev_publication_skips_divergence_check_without_origin(monkeypatch):
    mod = _load_module()
    state = mod.PushState(
        branch="dev",
        head_sha="abc1234",
        dirty=False,
        changed_paths=["docs/project/state.md"],
        remote_urls={"some": "https://example.com/some.git"},
    )
    intent = mod.resolve_publication_intent(state, explicit_target="no-mistakes/dev")

    def fake_run_git(args, *, check=True):
        raise AssertionError(f"unexpected git call: {args}")

    monkeypatch.setattr(mod, "_run_git", fake_run_git)

    mod.ensure_current_dev_base(state, intent)


def test_dev_publication_skips_divergence_check_without_origin_dev_ref(monkeypatch):
    mod = _load_module()
    state = mod.PushState(
        branch="dev",
        head_sha="abc1234",
        dirty=False,
        changed_paths=["docs/project/state.md"],
        remote_urls={"origin": "https://github.com/jon-devlapaz/socratink-app.git"},
    )
    intent = mod.resolve_publication_intent(state, explicit_target="origin/dev")

    def fake_run_git(args, *, check=True):
        if args == ["rev-parse", "--verify", "origin/dev"]:
            return ""
        raise AssertionError(f"unexpected git call: {args}")

    monkeypatch.setattr(mod, "_run_git", fake_run_git)

    mod.ensure_current_dev_base(state, intent)
