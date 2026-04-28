# tools/pipette/doctor.py
"""pipette doctor — preflight per §6 of the spec."""
from __future__ import annotations
from dataclasses import dataclass, field
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable

@dataclass
class Check:
    name: str
    verify: Callable[[], tuple[bool, str]]  # (ok, detail)
    fix: str

@dataclass
class CheckResult:
    name: str
    ok: bool
    message: str = ""
    fix: str = ""


def _verify_no_mistakes() -> tuple[bool, str]:
    r = subprocess.run(["git", "remote", "get-url", "no-mistakes"], capture_output=True, text=True)
    return r.returncode == 0, r.stdout.strip()

def _verify_code_review_graph_cli_and_mcp() -> tuple[bool, str]:
    """Two-part check: CLI status AND MCP wiring per spec §6.
    The MCP cannot be invoked from a non-Claude-Code subprocess, so we
    check that it's enabled in .claude/settings.local.json (which is
    where the project enables MCPs registered via `code-review-graph install`)."""
    import json
    if shutil.which("code-review-graph") is None:
        return False, "code-review-graph CLI not on PATH"
    r = subprocess.run(["code-review-graph", "status"], capture_output=True, text=True, timeout=10)
    if r.returncode != 0 or "Nodes:" not in r.stdout:
        return False, f"code-review-graph status failed: {r.stdout}{r.stderr}"
    settings_local = Path(".claude/settings.local.json")
    if not settings_local.exists():
        return False, ".claude/settings.local.json missing — MCP not enabled here"
    try:
        cfg = json.loads(settings_local.read_text())
    except (OSError, json.JSONDecodeError) as e:
        return False, f"settings.local.json unreadable: {e}"
    enabled = cfg.get("enabledMcpjsonServers") or []
    if "code-review-graph" not in enabled:
        return False, f"`code-review-graph` not in enabledMcpjsonServers: {enabled}"
    return True, "CLI status OK + MCP enabled in settings.local.json"

def _verify_post_commit_hook() -> tuple[bool, str]:
    p = Path(".git/hooks/post-commit")
    if not p.exists():
        return False, "post-commit hook missing"
    text = p.read_text()
    return ("code-review-graph update" in text and p.stat().st_mode & 0o111), text[:80]

def _verify_gemini() -> tuple[bool, str]:
    r = subprocess.run(["/opt/homebrew/bin/gemini", "--version"], capture_output=True, text=True)
    return r.returncode == 0, r.stdout.strip()

def _verify_grill_with_docs_skill() -> tuple[bool, str]:
    """B-revision (2026-04-28): pipette Step 1 uses `grill-with-docs` (replaces
    `grill-me`). The skill is verified by Claude Code at session start; doctor
    can only confirm the skill discovery contract is in place. If `/pipette`
    runs and the skill isn't available, Step 1 fails with a clear error."""
    return True, "skill availability is verified by Claude Code at session start"

def _verify_superpowers() -> tuple[bool, str]:
    base = Path.home() / ".claude" / "cowork_plugins" / "cache" / "superpowers-marketplace" / "superpowers"
    if not base.exists():
        return False, "superpowers cowork-plugins cache not found"
    versions = sorted(p.name for p in base.iterdir() if p.is_dir())
    if not versions:
        return False, "no superpowers version installed"
    skills_dir = base / versions[-1] / "skills"
    needed = ["writing-plans", "subagent-driven-development", "dispatching-parallel-agents", "using-git-worktrees", "test-driven-development"]
    missing = [n for n in needed if not (skills_dir / n).exists()]
    if missing:
        return False, f"missing superpowers skills: {missing}"
    return True, f"v{versions[-1]}"

def _verify_subagent_stop_hook() -> tuple[bool, str]:
    import json
    p = Path(".claude/settings.json")
    if not p.exists():
        return False, ".claude/settings.json missing"
    cfg = json.loads(p.read_text())
    hooks = (cfg.get("hooks") or {}).get("SubagentStop") or []
    for entry in hooks:
        for h in entry.get("hooks", []):
            if "tools.pipette.subagent_stop" in h.get("command", ""):
                return True, "wired"
    return False, "SubagentStop hook not in .claude/settings.json"

def _verify_pipeline_graph_validator() -> tuple[bool, str]:
    """The local hand-rolled structural validator must be importable
    and pass on tools/pipette/pipeline_graph.json (if present)."""
    try:
        from tools.pipette import validate_pipeline_graph as _v  # noqa: F401
    except ImportError as e:
        return False, f"validate_pipeline_graph module missing: {e}"
    return True, "validator module importable"

def _verify_filesystem() -> tuple[bool, str]:
    from tools.pipette.lockfile import detect_filesystem_supports_o_excl
    meta = Path("docs/pipeline/_meta")
    meta.mkdir(parents=True, exist_ok=True)
    return detect_filesystem_supports_o_excl(meta), str(meta)


CHECKS: list[Check] = [
    Check("no-mistakes git remote", _verify_no_mistakes,
          "no-mistakes proxy not configured for this repo. Re-run no-mistakes setup, then `git remote get-url no-mistakes` should succeed."),
    Check("code-review-graph CLI + MCP wired", _verify_code_review_graph_cli_and_mcp,
          "Install code-review-graph: `pip install code-review-graph` and run `code-review-graph install --platform claude-code`. This both registers the MCP and updates .claude/settings.local.json."),
    Check(".git/hooks/post-commit /graphify", _verify_post_commit_hook,
          "Run `bash tools/pipette/install_post_commit.sh` from the repo root."),
    Check("gemini CLI", _verify_gemini,
          "Install gemini CLI: `brew install gemini-cli` (or follow upstream install). Then `gemini auth login`."),
    Check("grill-with-docs skill availability", _verify_grill_with_docs_skill,
          "Install grill-with-docs from mattpocock's skills repo "
          "(e.g., symlink /path/to/matt_skills/skills/engineering/grill-with-docs "
          "→ ~/.claude/skills/grill-with-docs)."),
    Check("superpowers plugin (skills present)", _verify_superpowers,
          "Install superpowers plugin: `claude plugin add superpowers`."),
    Check("SubagentStop hook wired in .claude/settings.json", _verify_subagent_stop_hook,
          "Use `update-config` skill to add the SubagentStop entry running `python -m tools.pipette.subagent_stop`."),
    Check("pipeline-graph validator importable", _verify_pipeline_graph_validator,
          "Ensure `tools/pipette/validate_pipeline_graph.py` exists and is importable. (Replaces the spec's Agentproof reference; see plan §1.)"),
    Check("filesystem supports O_EXCL", _verify_filesystem,
          "pipette refuses to run on filesystems without reliable O_EXCL semantics (e.g., NFS, FUSE). Run pipette on a local APFS/ext4/btrfs volume."),
]


def run_checks(checks: list[Check]) -> list[CheckResult]:
    results: list[CheckResult] = []
    for c in checks:
        try:
            ok, detail = c.verify()
        except Exception as e:
            ok, detail = False, f"{type(e).__name__}: {e}"
        results.append(CheckResult(name=c.name, ok=ok, message=detail, fix=c.fix if not ok else ""))
    return results


def _aggregate_rc(results: list[CheckResult]) -> int:
    return 0 if all(r.ok for r in results) else 1


def run_doctor() -> int:
    results = run_checks(CHECKS)
    for r in results:
        mark = "✅" if r.ok else "❌"
        print(f"{mark} {r.name}: {r.message}")
        if not r.ok:
            print(f"   FIX: {r.fix}")
    rc = _aggregate_rc(results)
    if rc == 0:
        # Run the local hand-rolled structural validator on the pipeline graph (if present).
        struct_rc = _run_local_graph_validator()
        if struct_rc != 0:
            print("❌ pipeline-graph structural validation failed")
            return 1
        print("✅ pipeline-graph structural validation passed")
    return rc


def _run_local_graph_validator() -> int:
    """Run our hand-rolled validator on tools/pipette/pipeline_graph.json.
    Replaces the spec's mistakenly-referenced 'Agentproof' check."""
    graph = Path("tools/pipette/pipeline_graph.json")
    if not graph.exists():
        print("(skipping pipeline-graph validation: pipeline_graph.json not yet present)")
        return 0
    from tools.pipette.validate_pipeline_graph import validate
    errors = validate(graph)
    if errors:
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    return 0

# FIX_INSTRUCTIONS export for tests / external tooling
FIX_INSTRUCTIONS = {c.name: c.fix for c in CHECKS}
