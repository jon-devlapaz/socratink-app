import importlib.util
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
