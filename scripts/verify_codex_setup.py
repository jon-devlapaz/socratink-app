#!/usr/bin/env python3

from __future__ import annotations

import sys
import tomllib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CODEX_DIR = REPO_ROOT / ".codex"
CONFIG_PATH = CODEX_DIR / "config.toml"
REQUIRED_AGENTS = {
    "orchestrator",
    "theta",
    "sherlock",
    "elliot",
    "rob",
    "thurman",
    "glenna",
}
HANDOFF_AGENTS = {"elliot", "sherlock", "theta", "thurman", "rob"}
STATEFUL_AGENTS = {"orchestrator", "elliot", "sherlock"}
GLENNA_SCHEMA_HEADINGS = (
    "## Date",
    "## Workflow Traced",
    "## Outcome Reviewed",
    "## Agents Involved",
    "## Context Reviewed",
    "## What Went Well",
    "## Failure Modes",
    "## Suggested Prompt Fixes",
    "## Suggested Workflow Fixes",
    "## Suggested Owners",
    "## Confidence",
    "## Follow-Up Prompts",
)


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def ok(message: str) -> None:
    print(f"OK: {message}")


def expect(condition: bool, message: str) -> None:
    if not condition:
        fail(message)
    ok(message)


def expect_contains(text: str, needle: str, message: str) -> None:
    expect(needle in text, message)


def load_toml(path: Path) -> dict:
    try:
        return tomllib.loads(path.read_text())
    except FileNotFoundError:
        fail(f"missing TOML file: {path.relative_to(REPO_ROOT)}")


def repo_path(relative: str) -> Path:
    return REPO_ROOT / relative


def config_relative_path(relative: str) -> Path:
    return CODEX_DIR / relative


def expect_existing_file(path: Path, label: str) -> None:
    expect(path.is_file(), f"{label} exists at {path.relative_to(REPO_ROOT)}")


def expect_existing_dir(path: Path, label: str) -> None:
    expect(path.is_dir(), f"{label} exists at {path.relative_to(REPO_ROOT)}")


def expect_same_target(left: Path, right: Path, label: str) -> None:
    expect(left.resolve() == right.resolve(), label)


def main() -> None:
    expect_existing_file(CONFIG_PATH, "repo Codex config")

    config = load_toml(CONFIG_PATH)
    agents = config.get("agents", {})
    paths = config.get("paths", {})
    project = config.get("project", {})
    skills = config.get("skills", {})

    expect(project.get("default_agent") in agents, "default_agent is registered")
    expect(project.get("default_agent") == "orchestrator", "default_agent is orchestrator")
    expect(set(agents) == REQUIRED_AGENTS, "expected project agents are registered")

    agents_md = repo_path("AGENTS.md")
    expect_existing_file(agents_md, "repo AGENTS.md")
    expect_existing_file(repo_path("docs/theta/state.md"), "theta state doc")
    expect_existing_file(repo_path("agents/README.md"), "agent compatibility README")
    expect_existing_file(repo_path("docs/codex/agent-onboarding.md"), "agent onboarding doc")
    expect_existing_file(repo_path("docs/codex/agent-review-log.md"), "agent review log")

    agents_md_text = agents_md.read_text()
    expect_contains(
        agents_md_text,
        "`orchestrator` owns final consolidation of `docs/project/state.md`",
        "AGENTS.md documents final project-state ownership",
    )
    expect_contains(
        agents_md_text,
        "Resolve specialist disagreement with an explicit decision record.",
        "AGENTS.md documents disagreement handling",
    )

    bootstrap_repo = repo_path(paths["bootstrap"])
    bootstrap_codex = config_relative_path(paths["bootstrap"])
    expect_existing_file(bootstrap_repo, "bootstrap doc from repo-root path")
    expect_existing_file(bootstrap_codex, "bootstrap doc from .codex-relative path")
    expect_same_target(
        bootstrap_repo,
        bootstrap_codex,
        "bootstrap doc resolves to one shared target",
    )

    project_state_repo = repo_path(paths["project_state"])
    project_state_codex = config_relative_path(paths["project_state"])
    expect_existing_file(project_state_repo, "project state from repo-root path")
    expect_existing_file(project_state_codex, "project state from .codex-relative path")
    expect_same_target(
        project_state_repo,
        project_state_codex,
        "project state resolves to one shared target",
    )

    skills_repo = repo_path(skills["directory"])
    skills_codex = config_relative_path(skills["directory"])
    expect_existing_dir(skills_repo, "skills directory from repo-root path")
    expect_existing_dir(skills_codex, "skills directory from .codex-relative path")
    expect_same_target(
        skills_repo,
        skills_codex,
        "skills directory resolves to one shared target",
    )

    expect("theta-research" in {p.name for p in skills_repo.iterdir() if p.is_dir()}, "theta-research skill is present")
    expect("glenna-review" in {p.name for p in skills_repo.iterdir() if p.is_dir()}, "glenna-review skill is present")

    bootstrap_text = bootstrap_repo.read_text()
    expect(bootstrap_text.count("```") % 2 == 0, "session bootstrap markdown code fences are balanced")
    expect_contains(
        bootstrap_text,
        "When specialists disagree, produce a short decision record",
        "session bootstrap encodes disagreement handling",
    )
    expect_contains(
        bootstrap_text,
        "`orchestrator` owns final consolidation of `docs/project/state.md`",
        "session bootstrap encodes final project-state ownership",
    )

    onboarding_text = repo_path("docs/codex/agent-onboarding.md").read_text()
    expect_contains(
        onboarding_text,
        "let `orchestrator` own final consolidation of `docs/project/state.md`",
        "agent onboarding documents final project-state ownership",
    )
    expect_contains(
        onboarding_text,
        "write down the disputed point, evidence, chosen path, owner, and resulting state/doc updates",
        "agent onboarding documents disagreement handling",
    )

    review_log_text = repo_path("docs/codex/agent-review-log.md").read_text()
    expect_contains(
        review_log_text,
        "use the strict markdown schema defined in `.codex/agents/glenna.toml`",
        "agent review log requires the strict Glenna schema",
    )

    glenna_template_text = repo_path(
        ".agents/skills/glenna-review/assets/review-template.md"
    ).read_text()
    for heading in GLENNA_SCHEMA_HEADINGS:
        expect_contains(
            glenna_template_text,
            heading,
            f"Glenna review template includes {heading}",
        )

    for agent_name, agent_config in sorted(agents.items()):
        config_file = agent_config["config_file"]
        repo_config = repo_path(config_file)
        codex_config = config_relative_path(config_file)

        expect_existing_file(repo_config, f"{agent_name} config from repo-root path")
        expect_existing_file(codex_config, f"{agent_name} config from .codex-relative path")
        expect_same_target(
            repo_config,
            codex_config,
            f"{agent_name} config resolves to one shared target",
        )

        agent_doc = load_toml(codex_config)
        expect(agent_doc.get("name") == agent_name, f"{agent_name} config name matches registration")
        expect(bool(agent_doc.get("description")), f"{agent_name} config has a description")
        instructions = agent_doc.get("developer_instructions", "")
        expect(
            bool(instructions.strip()),
            f"{agent_name} config has developer instructions",
        )

        if agent_name in HANDOFF_AGENTS:
            expect_contains(
                instructions,
                "do not imply a silent persona-to-persona transfer",
                f"{agent_name} config forbids silent handoff",
            )
            expect_contains(
                instructions,
                "copy-ready prompt the user can send next",
                f"{agent_name} config requires a copy-ready handoff prompt",
            )

        if agent_name in STATEFUL_AGENTS:
            expect_contains(
                instructions,
                "`docs/project/state.md`",
                f"{agent_name} config references project-state upkeep",
            )

    orchestrator_instructions = load_toml(config_relative_path(agents["orchestrator"]["config_file"]))[
        "developer_instructions"
    ]
    expect_contains(
        orchestrator_instructions,
        "present a short decision record covering:",
        "orchestrator config requires an explicit decision record",
    )
    expect_contains(
        orchestrator_instructions,
        "own the final consolidation of `docs/project/state.md`",
        "orchestrator config owns final project-state consolidation",
    )

    glenna_instructions = load_toml(config_relative_path(agents["glenna"]["config_file"]))[
        "developer_instructions"
    ]
    for heading in GLENNA_SCHEMA_HEADINGS:
        expect_contains(
            glenna_instructions,
            heading,
            f"glenna config includes {heading}",
        )

    print("PASS: Codex agent setup verification succeeded")


if __name__ == "__main__":
    main()
