# Pipette F1–F15 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship F1–F15 from `docs/pipeline/_meta/implementation-followups.md` as 6 chunked PRs (A→B→C→G→F→E), each with narrow per-fix tests, derived from the principles in `docs/superpowers/specs/2026-04-30-pipette-followups-design.md`.

**Architecture:** Six sequential PRs against `dev-fresh` (then merged to `main`), preceded by one tiny housekeeping PR for the lessons append. Each chunk's outputs become test infrastructure for later chunks. LLM-prompt changes (Chunk E) ship last with manual fixture verification only — no brittle mock-LLM tests.

**Tech Stack:** Python 3.13 (pyenv-managed), `pytest`, `argparse`, existing `tools/pipette/` modules (`cli.py`, `trace.py`, `doctor.py`, `orchestrator.py`, `subagent_stop.py`, `lockfile.py`, `sanity/`). Tests in `tests/pipette/`.

**Spec source of truth:** `docs/superpowers/specs/2026-04-30-pipette-followups-design.md`. Anywhere this plan diverges from the spec, the spec wins.

---

## File Structure

| Path | Status | Owned by chunk | Responsibility |
|---|---|---|---|
| `docs/pipeline/_meta/lessons.md` | modify | Pre-flight | Append the 3 lesson lines from `implementation-followups.md` |
| `~/.claude/skills/grill-with-docs/SKILL.md` | modify | A | Drop `disable-model-invocation: true` from frontmatter |
| `tools/pipette/cli.py` | modify | B, C | F4 `trace-append --data` parser; F3 build-coverage-map shape validation + warning |
| `tools/pipette/trace.py` | modify | B | Helper for parsing `--data 'k=v,...'` into the existing `Event.extra` dict |
| `tools/pipette/gemini_picker.py` | modify | B | Refactor to call shared trace helper; preserve existing `gemini_verdict` event shape |
| `tools/pipette/doctor.py` | modify | C | F1 in-session MCP probe |
| `tools/pipette/subagent_stop.py` | modify | C | F8 read step from lockfile instead of hardcoding 5 |
| `tools/pipette/sanity/reviewers/_shared/mcp-fallback.md` | create | C | F5 shared MCP-fallback reference |
| `tools/pipette/sanity/reviewers/{contracts,impact,glossary,coverage}.md` | modify | C | F5 add reference to shared block |
| `tools/pipette/sanity/verifier.md` | modify | C | F5 same reference |
| `tools/pipette/orchestrator.py` | modify | F, G | F10 archive list extension; F11/F12/F13 dispatch logic; F15 heuristic gate |
| `.claude/commands/pipette-lite.md` | create | G | F14 lite slash command |
| `tests/pipette/test_cli.py` | create | B (extended C, G) | trace-append parser; build-coverage-map validation; lite path |
| `tests/pipette/test_doctor.py` | create | C | F1 MCP probe behavior |
| `tests/pipette/test_subagent_stop.py` | create | C | F8 step-from-lockfile tagging |
| `tests/pipette/test_orchestrator_dispatch.py` | create | G, F | F15 heuristic; F11/F12/F13 dispatch decisions; F14 precedence |
| `tests/pipette/test_archive_for_loop_back.py` | create | F | F10 extended file list |
| `~/.claude/skills/grill-with-docs/SKILL.md` | modify | E | F6 verify-cited-symbols; F7 deployment topology block |

---

## Pre-flight: Lessons Append (Standalone PR to `main`)

**Files:**
- Modify: `docs/pipeline/_meta/lessons.md`

**Why standalone:** spec §"Out of scope" — preserves Chunk A independence by landing this housekeeping commit on `main` *before* any chunk branch is cut. Per Principle 5: this commit has a different reason to fail review than any chunk's substantive work.

- [ ] **Step 1: Read existing `_meta/lessons.md` to confirm append pattern**

Run: `head -20 docs/pipeline/_meta/lessons.md`
Expected: lines like `- 2026-MM-DD <topic>: <one-line lesson>` — matching the format in the lessons block at the bottom of `docs/pipeline/_meta/implementation-followups.md`.

- [ ] **Step 2: Append the three lessons from `implementation-followups.md`**

Open `docs/pipeline/_meta/lessons.md` and append (newest at top per the doc's existing convention; if the file uses oldest-first, match that):

```
- 2026-04-28 admin-tink-todo-dashboard: Step 3 caught 2 critical design bugs (state.email AttributeError; Vercel CDN bypass) that Step 1 grill should have caught — see implementation-followups.md F6, F7
- 2026-04-28 admin-tink-todo-dashboard: doctor PASSes on MCP-configured even when tools aren't exposed in-session — see implementation-followups.md F1
- 2026-04-28 admin-tink-todo-dashboard: `grill-with-docs` skill has `disable-model-invocation: true`, blocks orchestrator dispatch — see implementation-followups.md F2
```

- [ ] **Step 3: Verify diff**

Run: `git diff docs/pipeline/_meta/lessons.md`
Expected: only the three lines above are added.

- [ ] **Step 4: Commit**

```bash
git checkout dev-fresh
git pull
git checkout -b housekeeping/lessons-append-2026-04-28
git add docs/pipeline/_meta/lessons.md
git commit -m "docs(pipette): append 2026-04-28 lessons from implementation-followups.md"
git push -u origin housekeeping/lessons-append-2026-04-28
gh pr create --base dev-fresh --title "docs(pipette): append 2026-04-28 lessons" --body "Closes the lessons loop from the 2026-04-28 admin-tink-todo-dashboard pipette run. See implementation-followups.md F1, F2, F6, F7."
```

- [ ] **Step 5: Wait for merge to `main` before starting Chunk A.**

---

## Chunk A — Unblock (F2)

**Goal:** Restore `grill-with-docs` skill's invocability so the pipette orchestrator can drive Step 1 directly.

**Files:**
- Modify: `~/.claude/skills/grill-with-docs/SKILL.md` (global, not in repo)

**No automated test possible** — the file lives outside the repo. Verification is manual.

- [ ] **Step 1: Read current frontmatter**

Run: `head -10 ~/.claude/skills/grill-with-docs/SKILL.md`
Expected: YAML frontmatter contains a line `disable-model-invocation: true` (this is the line F2 reports).

- [ ] **Step 2: Reproduce the failure (per spec test discipline)**

Open a throwaway Claude Code session and dispatch:

```
Skill: grill-with-docs
```

Expected error: `Skill grill-with-docs cannot be used with Skill tool due to disable-model-invocation`. This confirms the bug.

- [ ] **Step 3: Remove the line**

Edit `~/.claude/skills/grill-with-docs/SKILL.md`. Remove the `disable-model-invocation: true` line from the frontmatter. Leave all other frontmatter keys (`name`, `description`, etc.) intact.

- [ ] **Step 4: Verify**

In a fresh Claude Code session (skill files load at session start, so a fresh session is required), dispatch:

```
Skill: grill-with-docs
```

Expected: skill content loads without error. Note: this is a global skill change — there is no git commit for this chunk. Document the change in a tracking issue or the next chunk's PR description.

- [ ] **Step 5: Move on to Chunk B.** No PR to land for Chunk A.

---

## Chunk B — Trace Contract (F4 + F9)

**Goal:** Add `--data 'k=v,k2=v2'` to `trace-append`; refactor `gemini_picker` to use the shared helper. Unblocks structured-event assertions in later chunks.

**Files:**
- Modify: `tools/pipette/trace.py` (add `parse_extra_kv` helper)
- Modify: `tools/pipette/cli.py` (add `--data` to `trace-append` parser; pipe into `Event.extra`)
- Modify: `tools/pipette/gemini_picker.py` (route writes through `append_event` if not already)
- Create: `tests/pipette/test_cli.py`

### Task B.1 — Helper for parsing `--data` strings

- [ ] **Step 1: Create test file with first failing test**

Create `tests/pipette/test_cli.py`:

```python
"""CLI tests for tools.pipette.cli — added in Chunk B (F4) and extended in C (F3) and G (F14)."""
from __future__ import annotations
import json
from pathlib import Path

import pytest


def test_parse_extra_kv_simple():
    from tools.pipette.trace import parse_extra_kv
    assert parse_extra_kv("jump_back_to=1") == {"jump_back_to": "1"}


def test_parse_extra_kv_multi():
    from tools.pipette.trace import parse_extra_kv
    assert parse_extra_kv("jump_back_to=1,reason=verdict_fail") == {
        "jump_back_to": "1",
        "reason": "verdict_fail",
    }


def test_parse_extra_kv_empty_returns_empty_dict():
    from tools.pipette.trace import parse_extra_kv
    assert parse_extra_kv("") == {}
    assert parse_extra_kv(None) == {}


def test_parse_extra_kv_rejects_no_equals():
    from tools.pipette.trace import parse_extra_kv
    with pytest.raises(ValueError, match="expected key=value"):
        parse_extra_kv("just_a_key")
```

- [ ] **Step 2: Run to confirm failure**

Run: `pytest tests/pipette/test_cli.py -v`
Expected: 4 failures, all `ImportError: cannot import name 'parse_extra_kv' from 'tools.pipette.trace'`.

- [ ] **Step 3: Add `parse_extra_kv` to `tools/pipette/trace.py`**

Append to `tools/pipette/trace.py`:

```python
def parse_extra_kv(s: str | None) -> dict[str, str]:
    """Parse `'k=v,k2=v2'` into a dict of strings.

    Used by `pipette trace-append --data ...` (F4) so external callers can
    write structured trace events through the same path that gemini_picker
    uses. Values are kept as strings — callers that need typed values should
    cast on read; trace.jsonl is a string-keyed JSON record.
    """
    if not s:
        return {}
    out: dict[str, str] = {}
    for chunk in s.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "=" not in chunk:
            raise ValueError(f"expected key=value in --data; got {chunk!r}")
        k, _, v = chunk.partition("=")
        out[k.strip()] = v.strip()
    return out
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/pipette/test_cli.py -v`
Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/pipette/trace.py tests/pipette/test_cli.py
git commit -m "feat(pipette): add parse_extra_kv helper for structured trace data (F4)"
```

### Task B.2 — Wire `--data` into the `trace-append` CLI

- [ ] **Step 1: Add failing test for end-to-end CLI behavior**

Append to `tests/pipette/test_cli.py`:

```python
def test_trace_append_writes_structured_data(tmp_path: Path):
    """trace-append --data k=v writes the keys into trace.jsonl."""
    from tools.pipette.cli import main
    folder = tmp_path / "feature-x"
    folder.mkdir()
    rc = main([
        "trace-append",
        "--folder", str(folder),
        "--step", "3",
        "--event", "verdict_fail",
        "--data", "jump_back_to=1,reason=contracts_critical",
    ])
    assert rc == 0
    line = (folder / "trace.jsonl").read_text().strip()
    rec = json.loads(line)
    assert rec["event"] == "verdict_fail"
    assert rec["jump_back_to"] == "1"
    assert rec["reason"] == "contracts_critical"


def test_trace_append_rejects_malformed_data(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    from tools.pipette.cli import main
    folder = tmp_path / "feature-x"
    folder.mkdir()
    with pytest.raises(SystemExit) as exc:
        main([
            "trace-append",
            "--folder", str(folder),
            "--step", "3",
            "--event", "x",
            "--data", "no_equals_here",
        ])
    assert exc.value.code != 0
```

- [ ] **Step 2: Run to confirm failure**

Run: `pytest tests/pipette/test_cli.py::test_trace_append_writes_structured_data -v`
Expected: failure on `unrecognized arguments: --data`.

- [ ] **Step 3: Edit `tools/pipette/cli.py` — add `--data` to the `trace-append` subparser**

In `tools/pipette/cli.py`, find the `ta = sub.add_parser("trace-append", ...)` block (around line 86–91) and add this line at the end of the block, alongside `--decision` and `--jump-back-to`:

```python
    ta.add_argument("--data", default=None, help="extra structured fields as 'k=v,k2=v2' (F4)")
```

- [ ] **Step 4: Wire the `--data` string into `Event.extra`**

In the `if args.cmd == "trace-append":` block (around line 185–191), replace the existing `append_event(...)` call with:

```python
    if args.cmd == "trace-append":
        from tools.pipette.trace import append_event, Event, parse_extra_kv
        try:
            extra = parse_extra_kv(args.data)
        except ValueError as e:
            print(f"pipette: {e}", file=sys.stderr)
            return 2
        append_event(
            Path(args.folder) / "trace.jsonl",
            Event(step=args.step, event=args.event, decision=args.decision,
                  jump_back_to=args.jump_back_to, extra=extra),
        )
        return 0
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/pipette/test_cli.py -v`
Expected: 6 PASS (4 from B.1 + 2 from B.2).

- [ ] **Step 6: Commit**

```bash
git add tools/pipette/cli.py tests/pipette/test_cli.py
git commit -m "feat(pipette): trace-append accepts --data k=v structured fields (F4)"
```

### Task B.3 — Verify `gemini_picker` event shape preserved (F9)

- [ ] **Step 1: Read `tools/pipette/gemini_picker.py` to inspect current event-write path**

Run: `head -80 tools/pipette/gemini_picker.py`
Expected: identify the `append_event(... Event(... extra={...}))` call that writes the `gemini_verdict` event.

- [ ] **Step 2: Add regression test for the event shape**

Append to `tests/pipette/test_cli.py`:

```python
def test_gemini_picker_event_shape_preserved():
    """F9: gemini_picker must keep emitting `gemini_verdict` with keys
    {ts, step, event, decision, jump_back_to}. This is the canonical
    structured-event reference for trace.jsonl readers (e.g., weekly
    aggregator); changing it would silently break downstream tools."""
    import inspect
    from tools.pipette import gemini_picker as gp
    src = inspect.getsource(gp)
    # The event name must appear verbatim somewhere in the module.
    assert '"gemini_verdict"' in src or "'gemini_verdict'" in src, \
        "gemini_picker no longer references the gemini_verdict event name"
    # The event must be written via append_event so it goes through the
    # same path as `pipette trace-append --data ...`.
    assert "append_event" in src, \
        "gemini_picker should write events via trace.append_event for consistency with --data CLI path"
```

- [ ] **Step 3: Run the test — should pass on the existing implementation**

Run: `pytest tests/pipette/test_cli.py::test_gemini_picker_event_shape_preserved -v`
Expected: PASS (gemini_picker already uses `append_event` per `subagent_stop.py:30` import pattern). If FAIL: edit `gemini_picker.py` so it writes via `append_event(folder / "trace.jsonl", Event(step=3, event="gemini_verdict", decision=..., jump_back_to=..., extra={...}))` rather than writing JSON to the file directly.

- [ ] **Step 4: Commit (test only, even if no impl change was needed)**

```bash
git add tests/pipette/test_cli.py
git commit -m "test(pipette): pin gemini_verdict event shape and append_event usage (F9)"
```

- [ ] **Step 5: Open PR for Chunk B**

```bash
git push -u origin feat/pipette-chunk-b-trace-contract
gh pr create --base dev-fresh --title "feat(pipette): trace contract — F4 --data flag + F9 event shape pinned" --body "Implements Chunk B from docs/superpowers/plans/2026-04-30-pipette-followups.md. Adds 'pipette trace-append --data k=v,k2=v2' so external callers can write structured trace events; pins gemini_picker's gemini_verdict event shape via regression test."
```

---

## Chunk C — Signal Honesty (F1 + F3 + F5 + F8)

**Goal:** Make doctor, build-coverage-map, the SubagentStop hook, and reviewer prompts stop lying. Four commits inside one PR. Per spec §"Tension with P5": each commit is independently revertible.

**Files:**
- Modify: `tools/pipette/doctor.py` (F1)
- Modify: `tools/pipette/cli.py` (F3 — additive)
- Create: `tools/pipette/sanity/reviewers/_shared/mcp-fallback.md` (F5)
- Modify: `tools/pipette/sanity/reviewers/{contracts,impact,glossary,coverage}.md` and `tools/pipette/sanity/verifier.md` (F5)
- Modify: `tools/pipette/subagent_stop.py` (F8)
- Create: `tests/pipette/test_doctor.py` (F1)
- Create: `tests/pipette/test_subagent_stop.py` (F8)

### Task C.1 — F1 doctor in-session MCP probe

The current check verifies MCP is *configured* but not that tools are *exposed* in the running session. We add a probe that returns `⚠` when configured-but-not-exposed.

- [ ] **Step 1: Create the failing test**

Create `tests/pipette/test_doctor.py`:

```python
"""Unit tests for tools.pipette.doctor — added in Chunk C (F1)."""
from __future__ import annotations

import pytest


def test_mcp_probe_warns_when_tools_absent_in_session(monkeypatch):
    """F1: when MCP is configured but the running session doesn't expose
    the mcp__code-review-graph__* tools, doctor must return WARN, not OK."""
    from tools.pipette import doctor

    # Simulate: MCP configured per settings.local.json (the CLI+settings part
    # of the existing check passes), but no in-session tools exposed.
    monkeypatch.setattr(doctor, "_session_exposes_mcp_tools",
                        lambda prefix: False, raising=False)
    ok, msg = doctor._verify_code_review_graph_session_probe()
    assert ok is False
    assert "tools not exposed" in msg


def test_mcp_probe_ok_when_tools_present_in_session(monkeypatch):
    from tools.pipette import doctor
    monkeypatch.setattr(doctor, "_session_exposes_mcp_tools",
                        lambda prefix: True, raising=False)
    ok, msg = doctor._verify_code_review_graph_session_probe()
    assert ok is True
```

- [ ] **Step 2: Run to confirm failure**

Run: `pytest tests/pipette/test_doctor.py -v`
Expected: failure on `AttributeError: module 'tools.pipette.doctor' has no attribute '_verify_code_review_graph_session_probe'`.

- [ ] **Step 3: Implement the probe**

In `tools/pipette/doctor.py`, after `_verify_code_review_graph_cli_and_mcp`, add:

```python
def _session_exposes_mcp_tools(prefix: str) -> bool:
    """Probe whether the running Claude Code session has tools matching
    `prefix` exposed (e.g., 'mcp__code-review-graph__'). Implementation
    detail: Claude Code writes the deferred-tool list to an env var or a
    well-known path on session start. If we can't read it, return False
    (which downstream `_verify_code_review_graph_session_probe` interprets
    as 'not exposed' → WARN). This is patchable in tests."""
    import os
    # Claude Code exposes the available tool prefixes via this env var when
    # the session starts. Best-effort: if it's missing, treat as "tools not
    # exposed" (the conservative answer for F1).
    raw = os.environ.get("CLAUDE_CODE_AVAILABLE_TOOL_PREFIXES", "")
    return prefix in {p.strip() for p in raw.split(",") if p.strip()}


def _verify_code_review_graph_session_probe() -> tuple[bool, str]:
    """F1: in-session probe — confirms the mcp__code-review-graph__ tools
    are actually exposed in the running session, not just configured.
    Returns (False, msg) when configured-but-not-exposed; the caller's
    Check should classify this as WARN, not FAIL — fallback paths (SQLite,
    Grep) still let the pipeline run."""
    if _session_exposes_mcp_tools("mcp__code-review-graph__"):
        return True, "mcp__code-review-graph__ tools exposed in session"
    return False, ("MCP server configured but tools not exposed in session — "
                   "restart Claude Code or check `claude --mcp-debug`")
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/pipette/test_doctor.py -v`
Expected: 2 PASS.

- [ ] **Step 5: Wire the probe into `run_doctor`'s output**

Find the `CHECKS = [...]` list (or wherever the existing checks are registered) in `doctor.py`. Add a new entry that calls `_verify_code_review_graph_session_probe`. Render its result with a `⚠` glyph when False (not `❌` — see test docstring: this is WARN, not FAIL).

If the doctor's existing rendering only supports OK/FAIL (two states), extend `CheckResult` to carry a third state. Recommended: add `severity: str = "fail"` to `CheckResult` and let session-probe emit `severity="warn"`.

Example:

```python
# in doctor.py, near CheckResult:
@dataclass
class CheckResult:
    name: str
    ok: bool
    message: str = ""
    fix: str = ""
    severity: str = "fail"  # 'fail' (❌) or 'warn' (⚠) when ok is False
```

In the renderer, branch on `severity` when `not r.ok`:

```python
if r.ok:
    glyph = "✅"
elif r.severity == "warn":
    glyph = "⚠"
else:
    glyph = "❌"
```

- [ ] **Step 6: Manual verify**

Run: `python -m tools.pipette doctor` in a session where `mcp__code-review-graph__*` tools are NOT exposed.
Expected: a `⚠` line for the new check; the rest of doctor unchanged.

- [ ] **Step 7: Commit**

```bash
git add tools/pipette/doctor.py tests/pipette/test_doctor.py
git commit -m "feat(pipette): doctor warns when MCP tools not exposed in-session (F1)"
```

### Task C.2 — F3 build-coverage-map malformed-dump warning

- [ ] **Step 1: Add failing test**

Append to `tests/pipette/test_cli.py`:

```python
def test_build_coverage_map_warns_on_malformed_dump(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    """F3: when the dump's edges have NO `from.source_file` starting with
    'tests/', every affected file gets the uncovered default. That's a
    silent failure mode that triggered TDD enforcement spuriously in the
    2026-04-28 run. Emit a stderr warning when the shape looks wrong."""
    import json
    from tools.pipette.cli import main

    bad_dump = tmp_path / "bad.json"
    # Absolute paths, no 'tests/' prefix — the symptom from F3.
    bad_dump.write_text(json.dumps({
        "edges": [
            {"from": {"source_file": "/abs/path/foo.py"},
             "to": {"source_file": "/abs/path/bar.py"}}
        ]
    }))
    out_path = tmp_path / "coverage_map.json"
    rc = main([
        "build-coverage-map",
        "--dump-file", str(bad_dump),
        "--affected-files", "src/foo.py",
        "--output", str(out_path),
    ])
    assert rc == 0  # warning, not error
    err = capsys.readouterr().err
    assert "warning" in err.lower()
    assert "malformed" in err.lower() or "no test→source edges" in err.lower()
```

- [ ] **Step 2: Run to confirm failure**

Run: `pytest tests/pipette/test_cli.py::test_build_coverage_map_warns_on_malformed_dump -v`
Expected: FAIL — warning is silently swallowed.

- [ ] **Step 3: Edit `tools/pipette/cli.py` build-coverage-map block (around line 229–246)**

After the loop that populates `tested_files`, insert the validation:

```python
        edges = dump.get("edges") if isinstance(dump, dict) else dump
        tested_files: set[str] = set()
        edges_with_tests_prefix = 0
        if isinstance(edges, list):
            for e in edges:
                src = (e.get("from") or {}).get("source_file") if isinstance(e, dict) else None
                dst = (e.get("to") or {}).get("source_file") if isinstance(e, dict) else None
                if src and dst and src.startswith("tests/"):
                    tested_files.add(dst)
                    edges_with_tests_prefix += 1
        # F3: shape validation. If the dump claims edges but none have a
        # tests/-prefixed source_file, the dump shape is malformed and the
        # coverage map will be all-uncovered — silently triggering TDD
        # enforcement spuriously. Warn loudly to stderr.
        if isinstance(edges, list) and len(edges) > 0 and edges_with_tests_prefix == 0:
            print(
                "pipette: warning — coverage dump appears malformed "
                "(no test→source edges with `from.source_file` starting with 'tests/'); "
                "coverage map will be all-uncovered. "
                "Verify dump shape: {edges:[{from:{source_file:'tests/...'}, to:{source_file:'...'}}]}",
                file=sys.stderr,
            )
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/pipette/test_cli.py -v`
Expected: all CLI tests PASS, including the new F3 case.

- [ ] **Step 5: Commit**

```bash
git add tools/pipette/cli.py tests/pipette/test_cli.py
git commit -m "feat(pipette): build-coverage-map warns on malformed dump shape (F3)"
```

### Task C.3 — F8 SubagentStop hook reads step from lockfile

The hook currently emits `step=5` always (see `subagent_stop.py:87` and the trace line `extra={"task_id": ..., "reason": ...}`). We change this to read the current step from the lockfile.

- [ ] **Step 1: Create the failing test**

Create `tests/pipette/test_subagent_stop.py`:

```python
"""Unit tests for tools.pipette.subagent_stop — added in Chunk C (F8)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def lockfile_at_step_3(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Build a fixture lockfile + folder representing 'pipeline paused at step 3'."""
    folder = tmp_path / "feature-x"
    folder.mkdir()
    lock = tmp_path / ".lock"
    lock.write_text(yaml.safe_dump({
        "topic": "feature-x",
        "folder": str(folder),
        "state": "running",
        "current_step": 3,  # the new field the hook should read
        "acquired_at": "2026-04-30T00:00:00Z",
        "lock_written_at": "2026-04-30T00:00:00Z",
    }))
    monkeypatch.setenv("PIPETTE_LOCK_PATH", str(lock))
    return folder


def test_emit_uses_step_from_lockfile_not_hardcoded_5(lockfile_at_step_3: Path):
    """F8: the trace event the hook writes must carry the actual step
    (3 in this fixture), not a hardcoded 5."""
    from tools.pipette.subagent_stop import _emit
    from tools.pipette.trace import Event  # noqa: F401 — used via _emit's append_event call

    rc = _emit("allow", "test", folder=lockfile_at_step_3, task_id="t.1")
    assert rc == 0
    trace_line = (lockfile_at_step_3 / "trace.jsonl").read_text().strip().splitlines()[-1]
    rec = json.loads(trace_line)
    assert rec["event"] == "subagent_stop_hook"
    assert rec["step"] == 3, f"expected step=3 from lockfile, got step={rec['step']}"
```

- [ ] **Step 2: Run to confirm failure**

Run: `pytest tests/pipette/test_subagent_stop.py -v`
Expected: FAIL — `step` is hardcoded to `5` in the existing `_emit` (line 87).

- [ ] **Step 3: Modify `_emit` to read current step from lockfile**

In `tools/pipette/subagent_stop.py`, replace the existing `_emit` (lines 80–92) with:

```python
def _read_current_step_from_lockfile(default: float = 5) -> float:
    """F8: hook tags trace events with the actual pipeline step rather than
    a hardcoded 5. The lockfile carries `current_step` (set by the orchestrator
    on each step transition); read it here. Returns `default` if the lockfile
    is missing or doesn't carry the field — preserves prior behavior on
    unrecognized state rather than failing the hook."""
    try:
        cur = yaml.safe_load(_lock_path().read_text()) or {}
    except (OSError, yaml.YAMLError):
        return default
    val = cur.get("current_step")
    if isinstance(val, (int, float)):
        return float(val)
    # Fallback to paused_at_step if running-state field is missing
    paused = cur.get("paused_at_step")
    if isinstance(paused, (int, float)):
        return float(paused)
    return default


def _emit(decision: str, reason: str, *, folder: Path | None = None, task_id: str | None = None) -> int:
    out = {"permissionDecision": decision, "reason": reason}
    json.dump(out, sys.stdout)
    if folder is not None:
        try:
            step = _read_current_step_from_lockfile(default=5)
            append_event(
                folder / "trace.jsonl",
                Event(step=step, event="subagent_stop_hook", decision=decision,
                      extra={"task_id": task_id, "reason": reason}),
            )
        except OSError:
            pass
    return 0
```

- [ ] **Step 4: Verify the orchestrator writes `current_step` on transitions**

Run: `grep -n "current_step" tools/pipette/orchestrator.py tools/pipette/lockfile.py`
Expected: at least one writer. If none, add an `update_state(lock_path, current_step=N)` call at each step transition in `orchestrator.py`. Otherwise, the hook will fall back to `default=5` and the test will fail.

If the field doesn't exist yet, add a wrapper in `lockfile.py`:

```python
def set_current_step(lock_path: Path, step: float) -> None:
    """F8 helper: orchestrator calls this on each step transition so the
    SubagentStop hook can tag trace events with the right step."""
    update_state(lock_path, current_step=step)
```

And invoke it from `orchestrator.py` at the start of each step (the orchestrator's existing transition prose calls it as part of the step dispatch).

- [ ] **Step 5: Run tests**

Run: `pytest tests/pipette/test_subagent_stop.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tools/pipette/subagent_stop.py tools/pipette/lockfile.py tools/pipette/orchestrator.py tests/pipette/test_subagent_stop.py
git commit -m "feat(pipette): SubagentStop hook tags events with actual pipeline step (F8)"
```

### Task C.4 — F5 Shared MCP-fallback section in reviewer prompts

This is doc-only. No automated test.

- [ ] **Step 1: Create the shared block**

Create `tools/pipette/sanity/reviewers/_shared/mcp-fallback.md`:

```markdown
# MCP fallback for `code-review-graph`

If `mcp__code-review-graph__*` tools are not exposed in the running session
(the doctor's F1 in-session probe will WARN about this), use one of these
fallbacks instead of waiting on tool turns to rediscover them:

## SQLite fallback

The graph database lives at `.code-review-graph/graph.db` (relative to repo
root). Open with:

```bash
sqlite3 .code-review-graph/graph.db
```

Useful schemas:
- `nodes(id, kind, qualified_name, source_file, line_start, line_end)`
- `edges(id, kind, src_id, dst_id)` where `kind` includes `calls`, `imports`, `tests`

Example query (test→source coverage):

```sql
SELECT n_src.source_file AS test_file, n_dst.source_file AS source_file
FROM edges e
JOIN nodes n_src ON e.src_id = n_src.id
JOIN nodes n_dst ON e.dst_id = n_dst.id
WHERE e.kind = 'tests';
```

## Grep fallback

For a quick "where is this symbol used?" the Grep tool with a fully
qualified name (`MyClass.my_method` or `module.function`) is fast and cheap.
Trade-off: misses dynamic dispatch and indirect call sites — Grep is a
floor, not a ceiling. (See user memory: "Graph counts are a floor, not a
ceiling.")
```

- [ ] **Step 2: Reference the shared block from each reviewer prompt**

In each of these files:
- `tools/pipette/sanity/reviewers/contracts.md`
- `tools/pipette/sanity/reviewers/impact.md`
- `tools/pipette/sanity/reviewers/glossary.md`
- `tools/pipette/sanity/reviewers/coverage.md`
- `tools/pipette/sanity/verifier.md`

Find the section that currently says "use `code-review-graph` MCP" or "re-running `mcp__code-review-graph__...`". Append (or insert just below that line):

```markdown

If the MCP tools are not exposed in this session, use the fallbacks
documented in `tools/pipette/sanity/reviewers/_shared/mcp-fallback.md`
(SQLite + Grep) rather than burning tool turns rediscovering them.
```

- [ ] **Step 3: Verify diffs**

Run: `git diff tools/pipette/sanity/`
Expected: 5 reviewer/verifier prompts each gain ~3 lines of reference; one new file.

- [ ] **Step 4: Commit**

```bash
git add tools/pipette/sanity/reviewers/_shared/mcp-fallback.md tools/pipette/sanity/reviewers/*.md tools/pipette/sanity/verifier.md
git commit -m "docs(pipette): shared MCP-fallback reference for reviewer prompts (F5)"
```

- [ ] **Step 5: Open PR for Chunk C**

```bash
git push -u origin feat/pipette-chunk-c-signal-honesty
gh pr create --base dev-fresh --title "feat(pipette): signal honesty — F1 doctor probe + F3 dump validation + F5 reviewer fallbacks + F8 hook step-tag" --body "Implements Chunk C from docs/superpowers/plans/2026-04-30-pipette-followups.md. Four independent commits, each addressing one place where pipette's tooling silently lied; per-commit revertibility is the mitigation for the P5 tension acknowledged in the spec."
```

---

## Chunk G — Macro Gate (F15 + F14)

**Goal:** Add the heuristic auto-pass at Step 3 entry, plus the `pipette-lite` slash command that bypasses Step 3 unconditionally.

**Files:**
- Modify: `tools/pipette/orchestrator.py` (heuristic gate)
- Create: `.claude/commands/pipette-lite.md` (slash command)
- Create: `tests/pipette/test_orchestrator_dispatch.py`

### Task G.1 — F15 heuristic auto-pass at Step 3 entry

- [ ] **Step 1: Create the failing test**

Create `tests/pipette/test_orchestrator_dispatch.py`:

```python
"""Tests for orchestrator dispatch decisions — Chunk G (F15, F14) and Chunk F (F11–F13)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


# F15 thresholds (hardcoded constants per spec scope cuts)
COVERAGE_FLOOR = 0.80
RISK_CEILING = 0.30
LINES_CEILING = 50


@pytest.fixture
def folder_with_artifacts(tmp_path: Path):
    """A pipeline folder with the artifacts F15 inspects."""
    folder = tmp_path / "feature-x"
    folder.mkdir()
    return folder


def _write_coverage_map(folder: Path, files_map: dict[str, float]):
    (folder / "coverage_map.json").write_text(
        json.dumps({"_method": "graph_approx_v1", "files": files_map})
    )


def _write_grill_summary(folder: Path, total_changed_lines: int, max_risk_score: float):
    (folder / "01-grill.md").write_text(
        f"# Grill summary\n\n"
        f"<!-- pipette-meta total_changed_lines={total_changed_lines} max_risk_score={max_risk_score} -->\n"
        f"...\n"
    )


def test_f15_auto_pass_when_all_thresholds_met(folder_with_artifacts: Path):
    from tools.pipette.orchestrator import step3_heuristic_decision

    _write_coverage_map(folder_with_artifacts, {"src/foo.py": 0.95, "src/bar.py": 0.88})
    _write_grill_summary(folder_with_artifacts, total_changed_lines=20, max_risk_score=0.10)
    decision = step3_heuristic_decision(folder=folder_with_artifacts)
    assert decision.auto_pass is True
    assert decision.reason == "heuristic_auto_pass"


def test_f15_falls_through_on_low_coverage(folder_with_artifacts: Path):
    from tools.pipette.orchestrator import step3_heuristic_decision

    _write_coverage_map(folder_with_artifacts, {"src/foo.py": 0.50})
    _write_grill_summary(folder_with_artifacts, total_changed_lines=10, max_risk_score=0.10)
    decision = step3_heuristic_decision(folder=folder_with_artifacts)
    assert decision.auto_pass is False
    assert decision.reason == "coverage_below_80"


def test_f15_falls_through_on_high_risk(folder_with_artifacts: Path):
    from tools.pipette.orchestrator import step3_heuristic_decision

    _write_coverage_map(folder_with_artifacts, {"src/foo.py": 0.95})
    _write_grill_summary(folder_with_artifacts, total_changed_lines=10, max_risk_score=0.50)
    decision = step3_heuristic_decision(folder=folder_with_artifacts)
    assert decision.auto_pass is False
    assert decision.reason == "risk_above_30"


def test_f15_falls_through_on_large_diff(folder_with_artifacts: Path):
    from tools.pipette.orchestrator import step3_heuristic_decision

    _write_coverage_map(folder_with_artifacts, {"src/foo.py": 0.95})
    _write_grill_summary(folder_with_artifacts, total_changed_lines=200, max_risk_score=0.10)
    decision = step3_heuristic_decision(folder=folder_with_artifacts)
    assert decision.auto_pass is False
    assert decision.reason == "lines_above_50"


def test_f15_falls_through_on_malformed_coverage(folder_with_artifacts: Path):
    """F15 + F3 dependency: malformed coverage data → fall through with logged reason."""
    from tools.pipette.orchestrator import step3_heuristic_decision

    (folder_with_artifacts / "coverage_map.json").write_text("{not json}")
    _write_grill_summary(folder_with_artifacts, total_changed_lines=10, max_risk_score=0.10)
    decision = step3_heuristic_decision(folder=folder_with_artifacts)
    assert decision.auto_pass is False
    assert decision.reason == "coverage_malformed"


def test_f15_emits_autopass_rejected_trace_event(folder_with_artifacts: Path):
    """Per spec enhancement: each fall-through writes a structured event."""
    from tools.pipette.orchestrator import step3_heuristic_decision

    _write_coverage_map(folder_with_artifacts, {"src/foo.py": 0.40})
    _write_grill_summary(folder_with_artifacts, total_changed_lines=10, max_risk_score=0.10)
    step3_heuristic_decision(folder=folder_with_artifacts, write_trace=True)
    line = (folder_with_artifacts / "trace.jsonl").read_text().strip().splitlines()[-1]
    rec = json.loads(line)
    assert rec["event"] == "autopass_rejected"
    assert rec["reason"] == "coverage_below_80"
```

- [ ] **Step 2: Run to confirm failure**

Run: `pytest tests/pipette/test_orchestrator_dispatch.py -v`
Expected: 6 failures, all `ImportError: cannot import name 'step3_heuristic_decision'`.

- [ ] **Step 3: Implement the heuristic**

Append to `tools/pipette/orchestrator.py`:

```python
from dataclasses import dataclass


# F15 thresholds — hardcoded constants per spec scope cuts.
# Tuning requires editing this file (deliberate; no scoring module).
F15_COVERAGE_FLOOR = 0.80
F15_RISK_CEILING = 0.30
F15_LINES_CEILING = 50


@dataclass
class Step3HeuristicDecision:
    auto_pass: bool
    reason: str  # "heuristic_auto_pass" | "coverage_below_80" | "risk_above_30" | "lines_above_50" | "coverage_malformed"


def _read_grill_meta(folder: Path) -> tuple[int | None, float | None]:
    """Parse the `<!-- pipette-meta total_changed_lines=N max_risk_score=F -->`
    annotation that the grill writes into 01-grill.md. The grill prompt
    instructs it to emit this block; if missing, both values are None and
    F15 falls through (no auto-pass without a grounded count)."""
    import re
    p = folder / "01-grill.md"
    if not p.exists():
        return None, None
    text = p.read_text()
    m = re.search(r"pipette-meta\s+total_changed_lines=(\d+)\s+max_risk_score=([\d.]+)", text)
    if not m:
        return None, None
    return int(m.group(1)), float(m.group(2))


def _read_coverage_min(folder: Path) -> tuple[float | None, str | None]:
    """Returns (min_coverage_across_affected, error_reason). On malformed
    JSON or missing file, returns (None, 'coverage_malformed')."""
    import json as _json
    p = folder / "coverage_map.json"
    if not p.exists():
        return None, "coverage_malformed"
    try:
        data = _json.loads(p.read_text())
    except _json.JSONDecodeError:
        return None, "coverage_malformed"
    files = data.get("files") if isinstance(data, dict) else None
    if not isinstance(files, dict) or not files:
        return None, "coverage_malformed"
    return min(float(v) for v in files.values()), None


def step3_heuristic_decision(*, folder: Path, write_trace: bool = False) -> Step3HeuristicDecision:
    """F15: gate at Step 3 entry. Auto-pass IFF all thresholds met.

    On fall-through, optionally emits an `autopass_rejected` trace event
    naming the failed threshold — needed for future threshold tuning.
    """
    from tools.pipette.trace import append_event, Event

    cov_min, cov_err = _read_coverage_min(folder)
    if cov_err:
        decision = Step3HeuristicDecision(auto_pass=False, reason=cov_err)
    elif cov_min < F15_COVERAGE_FLOOR:
        decision = Step3HeuristicDecision(auto_pass=False, reason="coverage_below_80")
    else:
        lines, risk = _read_grill_meta(folder)
        if lines is None or risk is None:
            decision = Step3HeuristicDecision(auto_pass=False, reason="grill_meta_missing")
        elif risk >= F15_RISK_CEILING:
            decision = Step3HeuristicDecision(auto_pass=False, reason="risk_above_30")
        elif lines >= F15_LINES_CEILING:
            decision = Step3HeuristicDecision(auto_pass=False, reason="lines_above_50")
        else:
            decision = Step3HeuristicDecision(auto_pass=True, reason="heuristic_auto_pass")

    if write_trace and not decision.auto_pass:
        try:
            append_event(folder / "trace.jsonl",
                         Event(step=3, event="autopass_rejected",
                               extra={"reason": decision.reason}))
        except OSError:
            pass
    return decision
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/pipette/test_orchestrator_dispatch.py -v`
Expected: 6 PASS.

- [ ] **Step 5: Wire the heuristic into Step 3 entry**

Find the Step 3 dispatch site in `tools/pipette/orchestrator.py` (or in the slash-command markdown that drives Step 3). Insert at the very start of the Step 3 block:

```python
# F15: heuristic auto-pass before any reviewer/verifier dispatch.
decision = step3_heuristic_decision(folder=folder, write_trace=True)
if decision.auto_pass:
    (folder / "03-gemini-verdict.md").write_text(
        f"# Step 3 verdict (heuristic auto-pass)\n\n"
        f"Reason: {decision.reason}\n"
        f"All F15 thresholds met (coverage ≥ {F15_COVERAGE_FLOOR}, "
        f"risk < {F15_RISK_CEILING}, lines < {F15_LINES_CEILING}). "
        f"Reviewers and verifier were not dispatched.\n"
    )
    return  # advance to Step 4 in the orchestrator's caller
```

If Step 3 is driven by markdown rather than Python, document the Python entrypoint and have the markdown call it before reviewer dispatch.

- [ ] **Step 6: Commit**

```bash
git add tools/pipette/orchestrator.py tests/pipette/test_orchestrator_dispatch.py
git commit -m "feat(pipette): F15 heuristic auto-pass at Step 3 entry with autopass_rejected trace events"
```

### Task G.2 — F14 `pipette-lite` slash command

- [ ] **Step 1: Add the failing precedence test**

Append to `tests/pipette/test_orchestrator_dispatch.py`:

```python
def test_f14_lite_mode_overrides_f15_unconditionally(folder_with_artifacts: Path):
    """Spec enhancement: lite mode is an absolute manual override.
    Even synthetic high-risk-score input that would fail F15 must still
    bypass Step 3 in lite mode."""
    from tools.pipette.orchestrator import should_run_step3

    _write_coverage_map(folder_with_artifacts, {"src/foo.py": 0.40})
    _write_grill_summary(folder_with_artifacts, total_changed_lines=999, max_risk_score=0.99)
    # Lite mode: never run Step 3, regardless of heuristic.
    assert should_run_step3(folder=folder_with_artifacts, lite_mode=True) is False
    # Default: F15 fall-through → run Step 3.
    assert should_run_step3(folder=folder_with_artifacts, lite_mode=False) is True


def test_lite_mode_runs_correct_step_subset(folder_with_artifacts: Path, monkeypatch: pytest.MonkeyPatch):
    """Lite path runs Steps 0, 1, 2, 4, 5, 6, 7 — never Step 3."""
    from tools.pipette.orchestrator import lite_pipeline_steps
    steps = lite_pipeline_steps()
    assert 3 not in steps
    assert {0, 1, 2, 4, 5, 6, 7}.issubset(set(steps))
```

- [ ] **Step 2: Run to confirm failure**

Run: `pytest tests/pipette/test_orchestrator_dispatch.py -v`
Expected: 2 failures on the new tests (`should_run_step3` and `lite_pipeline_steps` undefined).

- [ ] **Step 3: Implement the lite-mode helpers**

Append to `tools/pipette/orchestrator.py`:

```python
def should_run_step3(*, folder: Path, lite_mode: bool) -> bool:
    """Combined gate. Lite mode is an absolute manual override (P-spec
    enhancement #5): even if F15 demands a full review, lite skips Step 3.
    Default path: respect F15 — auto-pass means skip, fall-through means run."""
    if lite_mode:
        return False
    return not step3_heuristic_decision(folder=folder, write_trace=False).auto_pass


def lite_pipeline_steps() -> list[float]:
    """Steps that pipette-lite runs. Step 3 is unconditionally skipped;
    best-of-N is disabled (single-subagent only) — the integration layer
    is responsible for honoring the latter."""
    return [0, 1, 2, 4, 5, 6, 7]
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/pipette/test_orchestrator_dispatch.py -v`
Expected: all PASS (8 total: 6 from G.1 + 2 from G.2).

- [ ] **Step 5: Create the slash command**

Create `.claude/commands/pipette-lite.md`:

```markdown
---
description: Heavy-planning pipeline (lite). Skips Step 3 hard gate unconditionally — for low-stakes runs.
---

# pipette-lite

Run the pipette pipeline without the Step 3 hard gate.

**When to use:** bug fixes, single-file features, dev-tooling — anything that
doesn't touch prod customer surface. F15's heuristic auto-pass already
short-circuits well-tested low-risk runs in default `/pipette`; reach for
`/pipette-lite` only when you've consciously decided the topic doesn't need
multi-reviewer review even if F15 wouldn't auto-pass.

**Cost:** ~60–100k tokens for a small task vs. ~500k for full pipette.

**What's preserved:** Steps 0, 1, 2, 4, 5, 6, 7. Single-subagent only — no
best-of-N. Lockfile, trace.jsonl, and audit trail behave identically to
default `/pipette`.

**What's skipped:** Step 3 hard gate (no reviewers, no verifier, no gemini
critique). The orchestrator records `step3_skipped reason=lite_mode` on the
trace so the audit log captures the override.

## Procedure

Invoke the same pipette orchestrator with `--lite` (or equivalent flag)
that calls `lite_pipeline_steps()` and `should_run_step3(..., lite_mode=True)`.
The orchestrator markdown for `/pipette` is the source of truth for the
step-by-step procedure; this command differs only in the Step 3 gate.
```

- [ ] **Step 6: Add the lite-mode trace event in the orchestrator dispatch**

Where Step 3 would have started in lite mode, add:

```python
if lite_mode:
    from tools.pipette.trace import append_event, Event
    append_event(folder / "trace.jsonl",
                 Event(step=3, event="step3_skipped",
                       extra={"reason": "lite_mode"}))
    return  # advance to Step 4
```

- [ ] **Step 7: Commit**

```bash
git add tools/pipette/orchestrator.py .claude/commands/pipette-lite.md tests/pipette/test_orchestrator_dispatch.py
git commit -m "feat(pipette): pipette-lite slash command bypasses Step 3 unconditionally (F14)"
```

- [ ] **Step 8: Open PR for Chunk G**

```bash
git push -u origin feat/pipette-chunk-g-macro-gate
gh pr create --base dev-fresh --title "feat(pipette): macro gate — F15 heuristic + F14 lite mode" --body "Implements Chunk G from docs/superpowers/plans/2026-04-30-pipette-followups.md. Adds F15 hardcoded-threshold auto-pass at Step 3 entry with autopass_rejected telemetry, and F14 pipette-lite slash command that bypasses Step 3 unconditionally per spec enhancement #5."
```

---

## Chunk F — Step 3 Surface (F13 + F11 + F12 + F10)

**Goal:** Trim Step 3 cost on loop-back, extend the audit-trail archive. Four commits inside one PR; commits ordered F13 → F11 → F12 → F10.

**Files:**
- Modify: `tools/pipette/orchestrator.py` exclusively
- Extend: `tests/pipette/test_orchestrator_dispatch.py` (F11/F12/F13)
- Create: `tests/pipette/test_archive_for_loop_back.py` (F10)

### Task F.1 — F13 per-reviewer artifact subsets

- [ ] **Step 1: Add failing test**

Append to `tests/pipette/test_orchestrator_dispatch.py`:

```python
def test_f13_glossary_reviewer_does_not_get_graph_context():
    """F13: per-reviewer artifact subsets. Glossary reviewer never sees
    00-graph-context.md (graph data, not glossary)."""
    from tools.pipette.orchestrator import reviewer_artifacts
    artifacts = reviewer_artifacts("glossary")
    assert "00-graph-context.md" not in artifacts


def test_f13_impact_reviewer_gets_full_artifact_stack():
    """F13: impact is the only reviewer that needs all four artifacts."""
    from tools.pipette.orchestrator import reviewer_artifacts
    artifacts = reviewer_artifacts("impact")
    assert {"00-graph-context.md", "01-grill.md", "02-diagram.mmd",
            "_meta/CONTEXT.md"}.issubset(set(artifacts))


def test_f13_unknown_reviewer_gets_full_stack():
    """Defensive: an unknown reviewer name falls back to the full stack
    rather than raising — preserves backward compatibility if a future
    reviewer is added without updating the lookup table."""
    from tools.pipette.orchestrator import reviewer_artifacts
    artifacts = reviewer_artifacts("future_reviewer")
    assert "00-graph-context.md" in artifacts
```

- [ ] **Step 2: Run to confirm failure**

Run: `pytest tests/pipette/test_orchestrator_dispatch.py -v`
Expected: 3 failures on `ImportError: cannot import name 'reviewer_artifacts'`.

- [ ] **Step 3: Implement the lookup table**

Append to `tools/pipette/orchestrator.py`:

```python
# F13: per-reviewer artifact subsets. Spec recommendation:
#   contracts: needs symbols → [00, 01]
#   impact: needs everything → [00, 01, 02, _meta/CONTEXT.md]
#   glossary: terminology, not graph → [01, 02, _meta/CONTEXT.md]
#   coverage: tests, not graph → [00, 01, coverage_map.json]
# Saves ~30% on per-reviewer context.
_REVIEWER_ARTIFACTS = {
    "contracts": ["00-graph-context.md", "01-grill.md"],
    "impact": ["00-graph-context.md", "01-grill.md", "02-diagram.mmd", "_meta/CONTEXT.md"],
    "glossary": ["01-grill.md", "02-diagram.mmd", "_meta/CONTEXT.md"],
    "coverage": ["00-graph-context.md", "01-grill.md", "coverage_map.json"],
}

_FULL_ARTIFACT_STACK = ["00-graph-context.md", "01-grill.md", "02-diagram.mmd", "_meta/CONTEXT.md"]


def reviewer_artifacts(reviewer: str) -> list[str]:
    """Return the artifact list passed to a reviewer subagent's context.
    Unknown reviewer names fall back to the full stack rather than raising,
    preserving backward compatibility if a new reviewer is added without
    updating this table."""
    return _REVIEWER_ARTIFACTS.get(reviewer, _FULL_ARTIFACT_STACK)
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/pipette/test_orchestrator_dispatch.py -v`
Expected: PASS (11 total now).

- [ ] **Step 5: Wire the lookup into reviewer dispatch**

Find where reviewer subagents are dispatched in `orchestrator.py` (or the Step 3 markdown). Replace any "pass all artifacts" call with:

```python
artifacts = reviewer_artifacts(reviewer_name)
# build the subagent prompt using only `artifacts`
```

- [ ] **Step 6: Commit**

```bash
git add tools/pipette/orchestrator.py tests/pipette/test_orchestrator_dispatch.py
git commit -m "feat(pipette): per-reviewer artifact subsets (F13)"
```

### Task F.2 — F11 smart-reviewers redispatch on loop-back

- [ ] **Step 0: Confirm `_verifier-survivors.json` shape**

Run: `python -c "from tools.pipette.sanity import verifier; help(verifier)"` and read `tools/pipette/sanity/verifier.py` (or the writer that produces `_verifier-survivors.json`). The tests below assume the file is shaped as `{reviewer_name: [{"severity": "...", ...}, ...]}`. If the actual writer produces a different shape (e.g., a flat list with a `reviewer` key per finding), adjust both the test fixtures and `reviewers_to_redispatch` accordingly. Record the actual shape in the commit message so future readers don't have to re-discover it.

- [ ] **Step 1: Add failing tests**

Append to `tests/pipette/test_orchestrator_dispatch.py`:

```python
def test_f11_smart_reviewers_skips_clean_reviewers_on_loopback(folder_with_artifacts: Path):
    """F11: a reviewer with no >= medium findings in attempt 1 is not
    redispatched in attempt 2."""
    from tools.pipette.orchestrator import reviewers_to_redispatch
    survivors = {
        "contracts": [{"severity": "critical"}],
        "impact":    [{"severity": "low"}],
        "glossary":  [],
        "coverage":  [{"severity": "medium"}],
    }
    to_dispatch = reviewers_to_redispatch(survivors)
    assert set(to_dispatch) == {"contracts", "coverage"}
    assert "glossary" not in to_dispatch
    assert "impact" not in to_dispatch  # only `low` findings, no medium+


def test_f11_falls_back_to_full_dispatch_when_survivors_malformed(folder_with_artifacts: Path):
    """Spec enhancement: malformed/missing _verifier-survivors.json defaults to
    full reviewer dispatch with a logged warning."""
    from tools.pipette.orchestrator import reviewers_to_redispatch_from_folder

    (folder_with_artifacts / "_verifier-survivors.json").write_text("{not json}")
    result = reviewers_to_redispatch_from_folder(folder_with_artifacts)
    assert set(result.reviewers) == {"contracts", "impact", "glossary", "coverage"}
    assert result.fallback_reason == "survivors_unparseable"
```

- [ ] **Step 2: Run to confirm failure**

Run: `pytest tests/pipette/test_orchestrator_dispatch.py -v`
Expected: failures on the new helpers.

- [ ] **Step 3: Implement**

Append to `tools/pipette/orchestrator.py`:

```python
@dataclass
class ReviewerRedispatchPlan:
    reviewers: list[str]
    fallback_reason: str | None  # None on happy path; non-None when full-dispatch fallback fired


_ALL_REVIEWERS = ["contracts", "impact", "glossary", "coverage"]
_MEDIUM_OR_HIGHER = {"medium", "high", "critical"}


def reviewers_to_redispatch(survivors_by_reviewer: dict[str, list[dict]]) -> list[str]:
    """F11: only redispatch reviewers that flagged ≥ medium in the prior attempt."""
    out: list[str] = []
    for reviewer in _ALL_REVIEWERS:
        findings = survivors_by_reviewer.get(reviewer) or []
        if any((f.get("severity") or "").lower() in _MEDIUM_OR_HIGHER for f in findings):
            out.append(reviewer)
    return out


def reviewers_to_redispatch_from_folder(folder: Path) -> ReviewerRedispatchPlan:
    """Read `_verifier-survivors.json` from `folder`. On malformed/missing,
    fall back to full dispatch and log the reason — spec enhancement.
    The orchestrator emits a `smart_reviewers_fallback` trace event when
    `fallback_reason` is non-None."""
    import json as _json
    p = folder / "_verifier-survivors.json"
    if not p.exists():
        return ReviewerRedispatchPlan(reviewers=list(_ALL_REVIEWERS),
                                      fallback_reason="survivors_missing")
    try:
        data = _json.loads(p.read_text())
    except _json.JSONDecodeError:
        return ReviewerRedispatchPlan(reviewers=list(_ALL_REVIEWERS),
                                      fallback_reason="survivors_unparseable")
    if not isinstance(data, dict):
        return ReviewerRedispatchPlan(reviewers=list(_ALL_REVIEWERS),
                                      fallback_reason="survivors_unexpected_shape")
    return ReviewerRedispatchPlan(reviewers=reviewers_to_redispatch(data),
                                  fallback_reason=None)
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/pipette/test_orchestrator_dispatch.py -v`
Expected: PASS (13 total).

- [ ] **Step 5: Wire into orchestrator's loop-back path**

Find the Step 3 dispatch on attempts ≥ 2 in `orchestrator.py`. Replace the existing "redispatch all 4 reviewers" with:

```python
plan = reviewers_to_redispatch_from_folder(folder)
if plan.fallback_reason:
    from tools.pipette.trace import append_event, Event
    append_event(folder / "trace.jsonl",
                 Event(step=3, event="smart_reviewers_fallback",
                       extra={"reason": plan.fallback_reason}))
# dispatch only `plan.reviewers` (still uses reviewer_artifacts() per F13)
```

- [ ] **Step 6: Commit**

```bash
git add tools/pipette/orchestrator.py tests/pipette/test_orchestrator_dispatch.py
git commit -m "feat(pipette): smart-reviewers redispatch on loop-back with fallback (F11)"
```

### Task F.3 — F12 skip verifier on attempt ≥ 2 (with safety condition)

- [ ] **Step 1: Add failing tests**

Append to `tests/pipette/test_orchestrator_dispatch.py`:

```python
def test_f12_skips_verifier_when_prior_survivors_clean(folder_with_artifacts: Path):
    """F12: skip verifier on attempt 2 IFF attempt 1's survivors file
    exists and parses cleanly."""
    import json
    from tools.pipette.orchestrator import should_run_verifier_on_attempt
    (folder_with_artifacts / "_verifier-survivors.json").write_text(
        json.dumps({"contracts": [], "impact": [], "glossary": [], "coverage": []})
    )
    assert should_run_verifier_on_attempt(folder=folder_with_artifacts, attempt=2) is False


def test_f12_runs_verifier_when_prior_survivors_missing(folder_with_artifacts: Path):
    """Spec enhancement: if attempt 1's verifier crashed (no survivors file),
    don't silently skip in attempt 2."""
    from tools.pipette.orchestrator import should_run_verifier_on_attempt
    assert should_run_verifier_on_attempt(folder=folder_with_artifacts, attempt=2) is True


def test_f12_runs_verifier_when_prior_survivors_malformed(folder_with_artifacts: Path):
    from tools.pipette.orchestrator import should_run_verifier_on_attempt
    (folder_with_artifacts / "_verifier-survivors.json").write_text("not json")
    assert should_run_verifier_on_attempt(folder=folder_with_artifacts, attempt=2) is True


def test_f12_always_runs_verifier_on_attempt_1(folder_with_artifacts: Path):
    from tools.pipette.orchestrator import should_run_verifier_on_attempt
    assert should_run_verifier_on_attempt(folder=folder_with_artifacts, attempt=1) is True
```

- [ ] **Step 2: Run to confirm failure**

Run: `pytest tests/pipette/test_orchestrator_dispatch.py -v`
Expected: 4 failures.

- [ ] **Step 3: Implement**

Append to `tools/pipette/orchestrator.py`:

```python
def should_run_verifier_on_attempt(*, folder: Path, attempt: int) -> bool:
    """F12: skip the verifier on attempt ≥ 2 only if attempt 1 produced a
    clean `_verifier-survivors.json`. Spec enhancement: if attempt 1's
    verifier crashed or output was malformed, run the verifier in attempt 2
    rather than silently breaking the verification chain."""
    import json as _json
    if attempt < 2:
        return True
    p = folder / "_verifier-survivors.json"
    if not p.exists():
        return True
    try:
        data = _json.loads(p.read_text())
    except _json.JSONDecodeError:
        return True
    return not isinstance(data, dict)  # well-formed dict → safe to skip
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/pipette/test_orchestrator_dispatch.py -v`
Expected: PASS (17 total).

- [ ] **Step 5: Wire into orchestrator**

In `orchestrator.py` Step 3 dispatch path:

```python
if should_run_verifier_on_attempt(folder=folder, attempt=current_attempt):
    # existing verifier dispatch
else:
    # apply 0.8 confidence filter directly to reviewer outputs
```

- [ ] **Step 6: Commit**

```bash
git add tools/pipette/orchestrator.py tests/pipette/test_orchestrator_dispatch.py
git commit -m "feat(pipette): skip verifier on clean attempt-1 survivors (F12)"
```

### Task F.4 — F10 archive reviewer/verifier scratch on loop-back

- [ ] **Step 1: Create the failing test**

Create `tests/pipette/test_archive_for_loop_back.py`:

```python
"""Tests for archive_for_loop_back — Chunk F (F10)."""
from __future__ import annotations
from pathlib import Path

import pytest


SCRATCH_FILES = [
    "_reviewer-contracts.json",
    "_reviewer-impact.json",
    "_reviewer-glossary.json",
    "_reviewer-coverage.json",
    "_verifier-output.json",
    "_verifier-survivors.json",
    "_step3-prompt.txt",
    "_gemini-stdout.log",
]

ORIGINAL_ARTIFACTS = ["01-grill.md", "02-diagram.mmd", "03-gemini-verdict.md"]


def _populate(folder: Path):
    folder.mkdir(parents=True, exist_ok=True)
    for f in SCRATCH_FILES + ORIGINAL_ARTIFACTS:
        (folder / f).write_text("placeholder")


def test_archive_includes_step3_scratch(tmp_path: Path):
    """F10: loop-back archive must include reviewer JSONs, verifier outputs,
    Step 3 prompt, and gemini stdout — the audit trail for attempt 1."""
    from tools.pipette.orchestrator import archive_for_loop_back
    folder = tmp_path / "feature-x"
    _populate(folder)
    arch = archive_for_loop_back(folder=folder, jump_back_to=1.0)
    archived = {p.name for p in arch.iterdir()}
    for scratch in SCRATCH_FILES:
        assert scratch in archived, f"F10: {scratch} should be archived but wasn't"
    for original in ORIGINAL_ARTIFACTS:
        assert original in archived, f"original artifact {original} should still be archived"


def test_archive_does_not_fail_on_missing_scratch(tmp_path: Path):
    """If a scratch file doesn't exist (e.g., Step 3 was a heuristic auto-pass),
    archive_for_loop_back must not raise."""
    from tools.pipette.orchestrator import archive_for_loop_back
    folder = tmp_path / "feature-x"
    folder.mkdir()
    for f in ORIGINAL_ARTIFACTS:
        (folder / f).write_text("placeholder")
    arch = archive_for_loop_back(folder=folder, jump_back_to=1.0)
    archived = {p.name for p in arch.iterdir()}
    for original in ORIGINAL_ARTIFACTS:
        assert original in archived
```

- [ ] **Step 2: Run to confirm failure**

Run: `pytest tests/pipette/test_archive_for_loop_back.py -v`
Expected: failure on missing scratch files in the archive (current implementation only archives 4 named files).

- [ ] **Step 3: Modify `archive_for_loop_back` in `tools/pipette/orchestrator.py`**

Replace the `affected = {...}` lookup (around line 142–148) with an extended one:

```python
    affected = {
        1.0: ["01-grill.md", "02-diagram.mmd", "02-diagram.excalidraw", "03-gemini-verdict.md",
              # F10: Step 3 scratch — preserves the audit trail for attempt 1.
              "_reviewer-contracts.json", "_reviewer-impact.json",
              "_reviewer-glossary.json", "_reviewer-coverage.json",
              "_verifier-output.json", "_verifier-survivors.json",
              "_step3-prompt.txt", "_gemini-stdout.log"],
        2.0: ["02-diagram.mmd", "02-diagram.excalidraw", "03-gemini-verdict.md",
              # F10: same scratch list — Step 3 ran in attempt 1 of jump=2 too.
              "_reviewer-contracts.json", "_reviewer-impact.json",
              "_reviewer-glossary.json", "_reviewer-coverage.json",
              "_verifier-output.json", "_verifier-survivors.json",
              "_step3-prompt.txt", "_gemini-stdout.log"],
    }
```

The existing loop already calls `if src.exists(): move(...)` — missing files are skipped, so the second test (missing scratch) passes without code change.

- [ ] **Step 4: Run tests**

Run: `pytest tests/pipette/test_archive_for_loop_back.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/pipette/orchestrator.py tests/pipette/test_archive_for_loop_back.py
git commit -m "feat(pipette): archive Step 3 scratch on loop-back for audit trail (F10)"
```

- [ ] **Step 6: Open PR for Chunk F**

```bash
git push -u origin feat/pipette-chunk-f-step3-surface
gh pr create --base dev-fresh --title "feat(pipette): Step 3 surface — F13 artifacts + F11 smart redispatch + F12 verifier skip + F10 audit archive" --body "Implements Chunk F from docs/superpowers/plans/2026-04-30-pipette-followups.md. Four commits: per-reviewer artifact subsets, smart-reviewers redispatch with fallback, verifier-skip with prior-attempt safety condition, and Step 3 scratch archiving. Each commit independently revertible."
```

---

## Chunk E — Grill Quality (F6 + F7)

**Goal:** Patch the grill skill so it Reads cited symbols and inspects deployment topology before producing its design summary. Manual fixture verification only — no automated tests (P10).

**Files:**
- Modify: `~/.claude/skills/grill-with-docs/SKILL.md` (canonical fix, assuming Chunk A succeeded)
- If Chunk A's fix did not propagate, alternative: modify the inlined grill procedure in `.claude/skills/pipette/SKILL.md` or the slash command. Decide based on observed Chunk A outcome.

**Verification:** documented manual fixture in the PR description. **Enforcement is prompt-level**, not orchestrator-level — see spec §"Future work" for the deferred hard gate.

### Task E.1 — F6 verify-cited-symbols round-trip

- [ ] **Step 1: Read the current grill procedure**

Run: `cat ~/.claude/skills/grill-with-docs/SKILL.md` (or wherever the grill procedure currently lives — confirm with: `find ~/.claude/skills -name "SKILL.md" -path "*grill*"`).

Find the section where the grill is instructed to produce its design summary / `01-grill.md`. Locate the step that names code snippets / cited symbols.

- [ ] **Step 2: Add the verify-cited-symbols block to the grill prompt**

Insert this block in the grill procedure, *before* the step that produces `01-grill.md`:

```markdown
## Step 0.5: Verify cited symbols (F6)

Before writing your design summary, identify the **single most-cited
symbol** in your draft code snippet (the field, method, or function your
reasoning hinges on most). Then:

1. Use the `Read` tool on the file that defines that symbol.
2. Confirm the field/method shape exists exactly as you cited it (e.g.,
   if your snippet says `state.email`, confirm `state.email` resolves on
   the actual class — not `state.user.email` or some other indirection).
3. Log the round-trip as a structured trace event:

   ```
   pipette trace-append --folder=<FOLDER> --step=1 \
     --event=grill_symbol_verified --data=symbol=<the.symbol.you.checked>
   ```

4. **Refuse to write `01-grill.md` until this round-trip is logged.** If
   the cited symbol does not exist on the class, revise your snippet to
   reference the actual shape, then re-verify and re-log.

This is prompt-level discipline, not an orchestrator gate. The trace event
provides observability so we can audit whether you skipped this step (see
spec §"Future work" — a hard orchestrator-side gate is deferred until
the trace shows the grill skipping verification under load).
```

- [ ] **Step 3: Manual fixture verification (the F6 fixture)**

In a fresh Claude Code session, invoke the grill on the literal admin-tink-todo failure case:

> Topic: "show admin todo dashboard at /admin/tink-todo when state.email == ADMIN_EMAIL"

Expected behavior:
1. Grill reads `auth/service.py` (or wherever `AuthSessionState` lives)
2. Finds that `email` is on `state.user`, not `state` directly
3. Logs `grill_symbol_verified symbol=AuthSessionState.user.email`
4. Revises the snippet from `state.email` to `state.user.email if state.user else None`
5. Only THEN writes `01-grill.md`

Capture the trace.jsonl line as evidence. Without this fix on `main`, the grill writes the broken snippet and Step 3 catches it (per the original failure).

- [ ] **Step 4: Document the fixture in the PR**

In the PR description, paste:
- The trace.jsonl line proving `grill_symbol_verified` was logged
- The revised snippet showing `state.user.email` (correct shape)

### Task E.2 — F7 deployment topology check

- [ ] **Step 1: Add the deployment-topology block to the grill prompt**

Insert this block in the grill procedure, immediately after the verify-cited-symbols block from E.1:

```markdown
## Step 0.6: Deployment topology check (F7)

If your design marks any route as a **Dev-only Route** per
`docs/pipeline/_meta/CONTEXT.md`, you must:

1. Use the `Read` tool on `vercel.json` (or the deployment config the repo
   actually uses — confirm the filename rather than assuming).
2. Identify every layer that could intercept the request between client
   and the FastAPI handler. For socratink-app this is typically:
   `Vercel CDN → FastAPI middleware → handler`.
3. Produce an explicit topology block in `01-grill.md`:

   ```
   ## Deployment topology
   - Path: /admin/tink-todo
   - Layers: Vercel CDN (serves public/* directly) → FastAPI middleware → handler
   - Gating placement: <where is the gate? in middleware? in handler? in vercel.json rewrites?>
   - Risk: if HTML lives in public/, the CDN bypasses the FastAPI gate
   ```

4. Either: (a) the route's HTML shell is served by a FastAPI handler
   (`HTMLResponse`), not from `public/`; OR (b) the cited `vercel.json`
   rewrites must be inspected and confirmed to forward the path to the
   function.

This is the same "Read the cited config before claiming its shape"
discipline as F6, applied to deployment layers rather than code symbols.
The Read of `vercel.json` is mandatory — do not write the topology block
from pre-training knowledge.
```

- [ ] **Step 2: Manual fixture verification (the F7 fixture)**

In a fresh Claude Code session, invoke the grill on a route that places gating in FastAPI middleware while the HTML lives in `public/`:

> Topic: "add /admin/tink-todo route, gated by middleware, HTML in public/admin-tink-todo.html"

Expected behavior:
1. Grill Reads `vercel.json`
2. Identifies that `public/*` is served directly by Vercel CDN
3. Produces the topology block flagging the CDN-bypass risk
4. Revises the design to either serve HTML via FastAPI handler or cite a `vercel.json` rewrite

- [ ] **Step 3: Document both fixtures in the PR**

The PR description for Chunk E carries both fixtures' before/after evidence. No git commit for the SKILL.md change in the repo — it's a global file. Mention the global change in the PR description so reviewers know what changed even though there's no diff.

- [ ] **Step 4: Open PR for Chunk E**

If E touches only the global SKILL.md, the chunk has no in-repo diff. In that case, open a documentation-only PR that:
- References the spec
- Documents the manual fixtures
- Captures `01-grill.md` outputs from before/after for both fixtures

Title: `docs(pipette): Chunk E — F6/F7 grill quality (manual fixture documentation)`

If E falls back to the inlined grill procedure (because Chunk A's fix didn't propagate), the chunk has a real diff in `.claude/skills/pipette/SKILL.md` — open a normal PR.

---

## Self-Review Checklist (run before claiming the plan is done)

- [ ] **Spec coverage:** every fix F1–F15 maps to a specific task above. Verify by grepping this plan: `grep -c "F[0-9]" plan.md` should equal 15+ (one per fix, sometimes more).
- [ ] **Type consistency:** `step3_heuristic_decision`, `Step3HeuristicDecision`, `reviewers_to_redispatch`, `should_run_verifier_on_attempt`, `lite_pipeline_steps`, `should_run_step3` — all referenced by name match their definitions above.
- [ ] **Placeholder scan:** no "TODO", "TBD", "fill in details", "similar to Task N", or vague "add error handling" — every step shows the actual code or command.
- [ ] **Test discipline:** every chunk except A and E has automated tests; E ships with manual fixtures documented in the PR.
- [ ] **Order:** A → B → C → G → F → E. No chunk depends on a chunk that comes after it.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-30-pipette-followups.md`. Two execution options:

**1. Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
