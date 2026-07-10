from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "Dockerfile.loop"
DOCKERIGNORE = ROOT / "Dockerfile.loop.dockerignore"
LOOP_REQUIREMENTS = ROOT / "requirements-loop.txt"


def test_loop_container_uses_supported_runtime_and_durable_store_defaults():
    dockerfile = DOCKERFILE.read_text()

    assert "FROM node:22-bookworm-slim AS node-runtime" in dockerfile
    assert "FROM python:3.14-slim-bookworm" in dockerfile
    assert "NODE_ENV=production" in dockerfile
    assert "SOCRATINK_LOOP_SESSION_STORE=supabase" in dockerfile
    assert "HOST=0.0.0.0" in dockerfile
    assert "PYTHON=/app/.venv/bin/python" in dockerfile
    assert 'CMD ["node", "loop-server.mjs"]' in dockerfile
    assert "USER socratink" in dockerfile


def test_loop_container_context_is_allowlisted_and_cannot_copy_env_files():
    dockerfile = DOCKERFILE.read_text()
    ignore_rules = DOCKERIGNORE.read_text().splitlines()

    assert ignore_rules[0] == "**"
    assert not any(rule == "!.env" or rule.startswith("!.env.") for rule in ignore_rules)
    assert "COPY . ." not in dockerfile
    for required_path in (
        "!requirements-loop.txt",
        "!loop-server.mjs",
        "!bridge.py",
        "!prompt_templates.py",
        "!bridge_lib/**",
        "!lib/**",
        "!pedagogical_agents/contracts.json",
        "!vendor/python/**",
    ):
        assert required_path in ignore_rules
    assert ignore_rules[-3:] == [
        "**/__pycache__/",
        "**/*.pyc",
        "**/*.pyo",
    ]


def test_loop_bridge_dependencies_match_the_app_pins():
    app_pins = set((ROOT / "requirements.txt").read_text().splitlines())
    loop_pins = set(LOOP_REQUIREMENTS.read_text().splitlines())

    assert loop_pins == {"google-genai==1.74.0", "pydantic==2.13.3"}
    assert loop_pins <= app_pins
