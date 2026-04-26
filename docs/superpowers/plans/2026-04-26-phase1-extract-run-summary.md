# Phase 1: Extract `analytics/run_summary` From `scripts/` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the production-callable summary payload builders (`build_summary_payload`, `build_learner_summary_payload`) out of `scripts/summarize_ai_runs.py` into a production-owned module `analytics/run_summary.py`, leaving the script as a thin CLI shim.

**Architecture:** Extract-and-preserve refactor. Behavior must not change. Pre-existing public function signatures stay identical. The script becomes an importer of the production module, not the other way around. Establishes the repo-wide rule: **scripts call production, never the reverse**.

**Tech Stack:** Python 3.10+, FastAPI, pytest.

**Roadmap context:** Phase 1 of `docs/superpowers/plans/2026-04-26-lego-ification-roadmap.md`.

---

## Prerequisites

- Working directory: repo root (`/Users/jondev/dev/socratink/prod/socratink-app`).
- Branch: `dev-fresh` (or a feature branch off it — agent's call).
- Tests run with: `pytest tests/test_run_summary.py -v` (single file) or `pytest -v` (full suite).
- Dev server (for manual smoke check): `uvicorn main:app --reload --port 8000`.
- `pytest.ini` already exists at repo root. Tests live under `tests/`.

## Pre-Flight Findings (already gathered, do not repeat)

| Item | Value |
|---|---|
| Public production-callable functions | `build_summary_payload()`, `build_learner_summary_payload(concept_ids)` |
| Production call sites | `main.py:35`, `main.py:36`, `main.py:319`, `main.py:337` |
| CLI-only code in `scripts/summarize_ai_runs.py` | `render_markdown` (line 741), `main` (line 859), `if __name__ == "__main__"` (line 881) |
| Existing tests | None for these functions |
| Path constants | `REPO_ROOT`, `LOG_DIR`, `EXTRACT_LOG`, `DRILL_LOG` use `Path(__file__).resolve().parents[1]` — works unchanged from `analytics/` |
| Module-level imports | `argparse`, `json`, `Counter`, `defaultdict`, `datetime`, `timedelta`, `timezone`, `Path`, `mean` — only `argparse` is CLI-only |
| Routes wrap in try/except → HTTP 500 | `main.py:317-324` and `main.py:327-342` — preserve all exception types |

---

## File Structure

| Path | Action | Owns |
|---|---|---|
| `analytics/__init__.py` | **Create** (empty file) | Marks `analytics` as a package |
| `analytics/run_summary.py` | **Create** | All production summary logic (constants, util fns, aggregators, public builders) |
| `scripts/summarize_ai_runs.py` | **Modify** (shrink to ~30 lines) | CLI wrapper only: re-imports from `analytics.run_summary`, owns `render_markdown` + `main` + `__main__` block |
| `main.py` | **Modify** (lines 35-36) | Update imports from `scripts.summarize_ai_runs` → `analytics.run_summary` |
| `tests/test_run_summary.py` | **Create** | Characterization tests pinning current behavior of both public builders |
| `docs/superpowers/plans/2026-04-26-lego-ification-roadmap.md` | **Modify** | Update Phase 1 status to Complete with commit SHA, fix the stale "2 calls" reference (it's actually 4) |

---

## Tasks

### Task 1: Write characterization tests against the **current** module location

Characterization tests pin existing behavior so the move can be verified. They must pass *before* anything moves.

**Files:**
- Create: `tests/test_run_summary.py`

- [ ] **Step 1: Create the test file with characterization tests**

```python
# tests/test_run_summary.py
"""Characterization tests for the analytics summary payload builders.

These tests pin current behavior so the Phase 1 extraction
(scripts/summarize_ai_runs.py -> analytics/run_summary.py) can be
verified safely. Behavior must not change between this commit and
the post-extraction commit.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

# NOTE: this import path will change in Task 4 to
# `from analytics.run_summary import ...` — that swap is the verification.
from scripts.summarize_ai_runs import (
    build_summary_payload,
    build_learner_summary_payload,
)


EXTRACT_FIXTURE = [
    {
        "timestamp": "2026-04-20T10:00:00Z",
        "status": "success",
        "architecture_type": "linear",
        "difficulty": "intro",
        "duration_ms": 1200,
        "cluster_count": 3,
        "backbone_count": 5,
        "subnode_count": 8,
        "low_density": False,
        "source_title": "Photosynthesis primer",
    },
    {
        "timestamp": "2026-04-21T11:00:00Z",
        "status": "error",
        "error_type": "schema_validation",
        "reason": "missing field",
    },
]

DRILL_FIXTURE = [
    {
        "timestamp": "2026-04-22T09:00:00Z",
        "status": "success",
        "session_phase": "turn",
        "answer_mode": "attempt",
        "classification": "solid",
        "routing": "NEXT",
        "node_id": "n1",
        "node_label": "Light reactions",
        "node_type": "mechanism",
        "cluster_id": "c1",
        "concept_id": "concept-a",
        "session_start_iso": "2026-04-22T09:00:00Z",
        "duration_ms": 800,
        "latest_learner_chars": 240,
    },
    {
        "timestamp": "2026-04-22T09:05:00Z",
        "status": "success",
        "session_phase": "turn",
        "answer_mode": "help_request",
        "help_request_reason": "stuck",
        "node_id": "n2",
        "node_label": "Calvin cycle",
        "node_type": "mechanism",
        "cluster_id": "c1",
        "concept_id": "concept-a",
        "session_start_iso": "2026-04-22T09:00:00Z",
        "duration_ms": 600,
        "latest_learner_chars": 60,
    },
]


@pytest.fixture
def synthetic_logs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Write fixture JSONL into tmp dir and rebind module constants."""
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    extract_log = logs_dir / "extract-runs.jsonl"
    drill_log = logs_dir / "drill-runs.jsonl"
    extract_log.write_text(
        "\n".join(json.dumps(row) for row in EXTRACT_FIXTURE) + "\n",
        encoding="utf-8",
    )
    drill_log.write_text(
        "\n".join(json.dumps(row) for row in DRILL_FIXTURE) + "\n",
        encoding="utf-8",
    )
    # Rebind whichever module currently owns the constants.
    # In Task 4 this import path changes, but the symbol names stay the same.
    import scripts.summarize_ai_runs as mod
    monkeypatch.setattr(mod, "EXTRACT_LOG", extract_log)
    monkeypatch.setattr(mod, "DRILL_LOG", drill_log)
    monkeypatch.setattr(mod, "LOG_DIR", logs_dir)
    return logs_dir


def test_build_summary_payload_has_top_level_keys(synthetic_logs: Path) -> None:
    payload = build_summary_payload()
    assert set(payload.keys()) == {"extract", "drill", "recent_events", "paths"}


def test_build_summary_payload_extract_aggregates(synthetic_logs: Path) -> None:
    payload = build_summary_payload()
    extract = payload["extract"]
    assert extract["total_runs"] == 2
    assert extract["success_count"] == 1
    assert extract["error_count"] == 1
    assert extract["success_rate"] == pytest.approx(50.0)
    assert extract["avg_duration_ms"] == pytest.approx(1200.0)


def test_build_summary_payload_drill_aggregates(synthetic_logs: Path) -> None:
    payload = build_summary_payload()
    drill = payload["drill"]
    assert drill["turn_count"] == 2
    assert drill["attempt_turn_count"] == 1
    assert drill["help_turn_count"] == 1
    assert drill["classified_turn_count"] == 1
    assert drill["solid_rate"] == pytest.approx(100.0)


def test_build_summary_payload_paths_are_strings(synthetic_logs: Path) -> None:
    payload = build_summary_payload()
    assert isinstance(payload["paths"]["extract_log"], str)
    assert isinstance(payload["paths"]["drill_log"], str)


def test_build_summary_payload_empty_logs_returns_zero_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import scripts.summarize_ai_runs as mod
    empty_extract = tmp_path / "missing-extract.jsonl"
    empty_drill = tmp_path / "missing-drill.jsonl"
    monkeypatch.setattr(mod, "EXTRACT_LOG", empty_extract)
    monkeypatch.setattr(mod, "DRILL_LOG", empty_drill)
    payload = build_summary_payload()
    assert payload["extract"]["total_runs"] == 0
    assert payload["drill"]["total_runs"] == 0
    assert payload["recent_events"] == []


def test_build_learner_summary_payload_has_top_level_keys(synthetic_logs: Path) -> None:
    payload = build_learner_summary_payload()
    expected = {
        "retrieval_habits",
        "cadence",
        "conversion_history",
        "session_journal",
        "node_history",
        "concept_stats",
        "paths",
    }
    assert set(payload.keys()) == expected


def test_build_learner_summary_payload_filters_by_concept_id(
    synthetic_logs: Path,
) -> None:
    payload_all = build_learner_summary_payload()
    payload_filtered = build_learner_summary_payload(["concept-a"])
    payload_other = build_learner_summary_payload(["concept-zzz"])
    assert payload_all["retrieval_habits"]["turn_count"] == 2
    assert payload_filtered["retrieval_habits"]["turn_count"] == 2
    assert payload_other["retrieval_habits"]["turn_count"] == 0


def test_build_learner_summary_payload_concept_stats_shape(
    synthetic_logs: Path,
) -> None:
    payload = build_learner_summary_payload()
    stats = payload["concept_stats"]
    assert len(stats) == 1
    row = stats[0]
    assert row["concept_id"] == "concept-a"
    assert row["turn_count"] == 2
    assert row["attempt_turn_count"] == 1
    assert row["help_turn_count"] == 1
```

- [ ] **Step 2: Run the tests to verify they pass against the current location**

Run: `pytest tests/test_run_summary.py -v`

Expected: 8 passed.

If any fail, **stop**. The test fixtures may have made assumptions about behavior that don't hold. Investigate before proceeding — the whole extraction depends on these tests being correct against the unmoved code.

- [ ] **Step 3: Commit the characterization tests**

```bash
git add tests/test_run_summary.py
git commit -m "test(analytics): characterize run_summary payload builders before extract"
```

---

### Task 2: Create the `analytics` package with the moved code

Move all production-relevant code into `analytics/run_summary.py`. Leave `scripts/summarize_ai_runs.py` untouched in this task — it'll briefly contain the same code in two places. Task 3 collapses the duplication.

**Files:**
- Create: `analytics/__init__.py`
- Create: `analytics/run_summary.py`

- [ ] **Step 1: Create the empty package marker**

```bash
touch analytics/__init__.py
```

(Or use Write with empty content. Either works.)

- [ ] **Step 2: Create `analytics/run_summary.py`**

The new module must contain **exactly the same code** as `scripts/summarize_ai_runs.py` for these symbols (preserve verbatim, including module docstring style, blank lines, and order):

- imports (lines 5-12 of the original) — but **drop `import argparse`** (CLI-only)
- constants `REPO_ROOT`, `LOG_DIR`, `EXTRACT_LOG`, `DRILL_LOG` (lines 15-18)
- `load_jsonl` (lines 21-44)
- `pct` (lines 47-50)
- `safe_mean` (lines 53-56)
- `top_counter` (lines 59-60)
- `latest_timestamp` (lines 63-67)
- `parse_timestamp` (lines 70-73)
- `extract_summary` (lines 76-117)
- `drill_summary` (lines 120-343)
- `recent_events` (lines 346-385)
- `build_summary_payload` (lines 388-402)
- `_normalize_concept_ids` (lines 405-410)
- `_filter_turn_rows` (lines 413-423)
- `_days_between` (lines 426-430)
- `_journal_outcome` (lines 433-461)
- `learner_summary` (lines 464-727)
- `build_learner_summary_payload` (lines 730-738)

Replace the original module-level docstring (`# BML: Measure ...`) at the top of the new file with:

```python
"""Production analytics: summary payload builders for /api/analytics/* endpoints.

Pure aggregation over the extract and drill JSONL logs. No request objects,
no CLI concerns. The CLI lives in scripts/summarize_ai_runs.py and re-imports
from here.
"""
```

**Do not include** `render_markdown`, `main`, or the `__main__` block — those are CLI-only and stay in `scripts/`.

- [ ] **Step 3: Confirm the new module is importable**

Run: `python -c "from analytics.run_summary import build_summary_payload, build_learner_summary_payload; print('ok')"`

Expected: `ok`

If you see `ModuleNotFoundError`, the most likely cause is that `analytics/__init__.py` doesn't exist or is wrong. If you see `ImportError` for a symbol, you missed copying a function — re-check Step 2's list against the original file.

- [ ] **Step 4: Sanity-check with a single-line equivalence smoke**

Run: `python -c "import analytics.run_summary as new, scripts.summarize_ai_runs as old; assert sorted(s for s in dir(new) if not s.startswith('_')) == sorted(s for s in dir(old) if not s.startswith('_') and s not in ('argparse', 'render_markdown', 'main')); print('symbols match')"`

Expected: `symbols match`

If this fails, the symbol set diverges — fix before moving on.

- [ ] **Step 5: Commit**

```bash
git add analytics/__init__.py analytics/run_summary.py
git commit -m "feat(analytics): add run_summary module (extracted from scripts/summarize_ai_runs)"
```

---

### Task 3: Switch tests to the new module + verify

Repoint the characterization tests at `analytics.run_summary`. They must still pass — that's the whole point of Phase 1.

**Files:**
- Modify: `tests/test_run_summary.py`

- [ ] **Step 1: Update the import line**

In `tests/test_run_summary.py`, change:

```python
from scripts.summarize_ai_runs import (
    build_summary_payload,
    build_learner_summary_payload,
)
```

to:

```python
from analytics.run_summary import (
    build_summary_payload,
    build_learner_summary_payload,
)
```

And update the two `import scripts.summarize_ai_runs as mod` lines (in `synthetic_logs` and `test_build_summary_payload_empty_logs_returns_zero_counts`) to:

```python
import analytics.run_summary as mod
```

- [ ] **Step 2: Run the tests against the new module**

Run: `pytest tests/test_run_summary.py -v`

Expected: 8 passed. Same numbers as Task 1 Step 2.

If any test fails, the move was not behavior-preserving. **Stop and diff** the two files (`diff scripts/summarize_ai_runs.py analytics/run_summary.py`) — the production code in both should be byte-equivalent for the moved symbols.

- [ ] **Step 3: Commit**

```bash
git add tests/test_run_summary.py
git commit -m "test(analytics): point characterization tests at analytics.run_summary"
```

---

### Task 4: Convert `scripts/summarize_ai_runs.py` to a thin CLI shim

Now collapse the duplication. The script becomes an importer of the production module, keeping only the CLI surface.

**Files:**
- Modify: `scripts/summarize_ai_runs.py` (rewrite — the shim is short enough to write whole)

- [ ] **Step 1: Replace the script content with the shim**

Write the **entire** file as:

```python
#!/usr/bin/env python3
"""CLI for analytics summary. Production logic lives in analytics.run_summary."""

from __future__ import annotations

import argparse
import json

from analytics.run_summary import build_summary_payload
# Re-exported so any transitional caller still importing from this module path
# keeps working until Task 5 lands. Removed once main.py is updated.
from analytics.run_summary import build_learner_summary_payload  # noqa: F401


def render_markdown(extract_data: dict, drill_data: dict) -> str:
    lines: list[str] = []

    lines.append("**AI Run Summary**")
    lines.append("")
    lines.append("**Extraction**")
    lines.append(
        f"- Runs: {extract_data['total_runs']} ({extract_data['success_count']} success, {extract_data['error_count']} error, {extract_data['success_rate']:.1f}% success)"
    )
    lines.append(f"- Avg duration: {extract_data['avg_duration_ms']:.1f} ms")
    lines.append(
        f"- Avg map size: {extract_data['avg_backbone_count']:.1f} backbone, {extract_data['avg_cluster_count']:.1f} clusters, {extract_data['avg_subnode_count']:.1f} subnodes"
    )
    lines.append(f"- Low-density success rate: {extract_data['low_density_rate']:.1f}%")
    if extract_data["architecture_distribution"]:
        lines.append(
            f"- Architecture mix: {dict(extract_data['architecture_distribution'])}"
        )
    if extract_data["difficulty_distribution"]:
        lines.append(
            f"- Difficulty mix: {dict(extract_data['difficulty_distribution'])}"
        )
    if extract_data["error_types"]:
        lines.append(f"- Error types: {dict(extract_data['error_types'])}")
    if extract_data["top_sources"]:
        lines.append(f"- Top sources: {extract_data['top_sources']}")

    lines.append("")
    lines.append("**Drill**")
    lines.append(
        f"- Runs: {drill_data['total_runs']} ({drill_data['success_count']} success, {drill_data['error_count']} error, {drill_data['success_rate']:.1f}% success)"
    )
    lines.append(
        f"- Turns: {drill_data['turn_count']} ({drill_data['attempt_turn_count']} attempts, {drill_data['help_turn_count']} help requests)"
    )
    lines.append(f"- Scored attempt turns: {drill_data['classified_turn_count']}")
    lines.append(f"- Avg duration: {drill_data['avg_duration_ms']:.1f} ms")
    lines.append(
        f"- Avg learner response length: {drill_data['avg_attempt_learner_chars']:.1f} chars on attempts, {drill_data['avg_help_learner_chars']:.1f} chars on help requests"
    )
    lines.append(f"- Attempt rate: {drill_data['attempt_rate']:.1f}%")
    lines.append(f"- Help-request rate: {drill_data['help_request_rate']:.1f}%")
    lines.append(f"- Solid rate: {drill_data['solid_rate']:.1f}%")
    lines.append(f"- Non-solid NEXT rate: {drill_data['non_solid_next_rate']:.1f}%")
    lines.append(
        f"- Force-advance rate: {drill_data['force_advance_rate']:.1f}% on scored attempts"
    )
    lines.append(
        f"- Attempt force-advance rate: {drill_data['attempt_force_advance_rate']:.1f}%"
    )
    lines.append(
        f"- Help force-advance rate: {drill_data['help_force_advance_rate']:.1f}%"
    )
    lines.append(f"- One-turn solid rate: {drill_data['one_turn_solid_rate']:.1f}%")
    lines.append(
        f"- Reward emit rate: {drill_data['reward_emit_rate']:.1f}% of attempts"
    )
    lines.append(f"- Help-only sessions: {drill_data['help_only_session_count']}")
    if drill_data["classification_distribution"]:
        lines.append(
            f"- Classification mix: {dict(drill_data['classification_distribution'])}"
        )
    if drill_data["routing_distribution"]:
        lines.append(f"- Routing mix: {dict(drill_data['routing_distribution'])}")
    if drill_data["node_type_distribution"]:
        lines.append(f"- Node-type mix: {dict(drill_data['node_type_distribution'])}")
    if drill_data["answer_mode_distribution"]:
        lines.append(
            f"- Answer-mode mix: {dict(drill_data['answer_mode_distribution'])}"
        )
    if drill_data["help_request_reason_distribution"]:
        lines.append(
            f"- Help-request reasons: {dict(drill_data['help_request_reason_distribution'])}"
        )
    if drill_data["response_tier_distribution"]:
        lines.append(
            f"- Response-tier mix: {dict(drill_data['response_tier_distribution'])}"
        )
    if drill_data["response_band_distribution"]:
        lines.append(
            f"- Response-band mix: {dict(drill_data['response_band_distribution'])}"
        )
    if drill_data["termination_distribution"]:
        lines.append(f"- Terminations: {dict(drill_data['termination_distribution'])}")
    if drill_data["error_types"]:
        lines.append(f"- Error types: {dict(drill_data['error_types'])}")

    lines.append("")
    lines.append("**Product Signals**")
    if drill_data["hotspot_nodes"]:
        lines.append("- Friction nodes:")
        for row in drill_data["hotspot_nodes"]:
            label = row["label"] or row["node_id"]
            lines.append(
                f"  - {label} ({row['node_id']}): turns={row['turns']}, solid={row['solid_rate']:.1f}%, misconception={row['misconception_rate']:.1f}%, force-advance={row['force_advance_rate']:.1f}%"
            )
    else:
        lines.append("- Friction nodes: not enough drill volume yet")

    if drill_data["hotspot_clusters"]:
        lines.append("- Friction clusters:")
        for row in drill_data["hotspot_clusters"]:
            lines.append(
                f"  - {row['cluster_id']}: turns={row['turns']}, solid={row['solid_rate']:.1f}%, misconception={row['misconception_rate']:.1f}%, force-advance={row['force_advance_rate']:.1f}%"
            )
    else:
        lines.append("- Friction clusters: not enough drill volume yet")

    if drill_data["node_type_benchmarks"]:
        lines.append("- Node-type benchmarks:")
        for row in drill_data["node_type_benchmarks"]:
            lines.append(
                f"  - {row['node_type']}: turns={row['turns']}, solid={row['solid_rate']:.1f}%, non-solid={row['non_solid_rate']:.1f}%, force-advance={row['force_advance_rate']:.1f}%"
            )

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Summarize extraction and drill telemetry logs."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of markdown.",
    )
    args = parser.parse_args()

    payload = build_summary_payload()
    extract_data = payload["extract"]
    drill_data = payload["drill"]

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    print(render_markdown(extract_data, drill_data))


if __name__ == "__main__":
    main()
```

The file should now be roughly 145 lines (down from 882) — a CLI shim that owns only the markdown rendering and argparse plumbing.

- [ ] **Step 2: Verify the CLI still works (markdown mode)**

Run: `python scripts/summarize_ai_runs.py 2>&1 | head -5`

Expected: Output starts with `**AI Run Summary**` (or, if `logs/` is empty, output that begins with `**AI Run Summary**` and shows `Runs: 0`). No tracebacks.

- [ ] **Step 3: Verify the CLI still works (JSON mode)**

Run: `python scripts/summarize_ai_runs.py --json | python -c "import sys, json; payload = json.load(sys.stdin); assert set(payload.keys()) == {'extract', 'drill', 'recent_events', 'paths'}; print('json shape ok')"`

Expected: `json shape ok`

- [ ] **Step 4: Run the characterization tests again**

Run: `pytest tests/test_run_summary.py -v`

Expected: 8 passed (unchanged from Task 3).

- [ ] **Step 5: Verify `main.py` still imports cleanly through the shim**

This is the critical check. `main.py` still has `from scripts.summarize_ai_runs import build_learner_summary_payload` at this point — the unused-looking re-export in the shim is what keeps that working until Task 5 lands.

Run: `python -c "from main import app; print(type(app).__name__)"`

Expected: `FastAPI`

If this fails with `ImportError: cannot import name 'build_learner_summary_payload' from 'scripts.summarize_ai_runs'`, the re-export line was dropped — re-add it before committing.

- [ ] **Step 6: Commit**

```bash
git add scripts/summarize_ai_runs.py
git commit -m "refactor(scripts): convert summarize_ai_runs to thin CLI shim over analytics.run_summary"
```

---

### Task 5: Update `main.py` imports to point at the production module

This is the change that actually closes the smell. After this commit, `main.py` no longer imports from `scripts/`.

**Files:**
- Modify: `main.py:35-36`

- [ ] **Step 1: Update the imports in `main.py`**

Replace `main.py` lines 35-36:

```python
from scripts.summarize_ai_runs import build_summary_payload
from scripts.summarize_ai_runs import build_learner_summary_payload
```

with:

```python
from analytics.run_summary import build_summary_payload
from analytics.run_summary import build_learner_summary_payload
```

- [ ] **Step 1b: Drop the transitional re-export from the CLI shim**

Now that nothing in production imports from `scripts.summarize_ai_runs`, the unused re-export added in Task 4 can go.

In `scripts/summarize_ai_runs.py`, delete these two lines:

```python
# Re-exported so any transitional caller still importing from this module path
# keeps working until Task 5 lands. Removed once main.py is updated.
from analytics.run_summary import build_learner_summary_payload  # noqa: F401
```

- [ ] **Step 2: Verify FastAPI app still starts**

Run: `python -c "from main import app; print(type(app).__name__)"`

Expected: `FastAPI`

If you see `ImportError`, the new module is missing a symbol or `analytics/__init__.py` is missing.

- [ ] **Step 3: Run the full test suite**

Run: `pytest -v 2>&1 | tail -30`

Expected: All previously-passing tests still pass. The 8 characterization tests pass. No new failures attributable to the import change. (If unrelated tests were already failing on `dev-fresh` before this work, they may still fail — investigate only the tests that touch analytics or main.)

- [ ] **Step 4: Manual smoke check the two affected endpoints**

Start the dev server in one terminal: `uvicorn main:app --port 8000`

Then in another terminal:

```bash
curl -s http://localhost:8000/api/analytics/ai-runs | python -c "import sys, json; payload = json.load(sys.stdin); assert set(payload.keys()) == {'extract', 'drill', 'recent_events', 'paths'}; print('/api/analytics/ai-runs ok')"
curl -s "http://localhost:8000/api/analytics/learner-runs" | python -c "import sys, json; payload = json.load(sys.stdin); assert 'retrieval_habits' in payload and 'cadence' in payload; print('/api/analytics/learner-runs ok')"
curl -s "http://localhost:8000/api/analytics/learner-runs?concept_ids=concept-a,concept-b" | python -c "import sys, json; payload = json.load(sys.stdin); assert 'retrieval_habits' in payload; print('/api/analytics/learner-runs filtered ok')"
```

Expected: three lines of `ok` output. Stop the server.

If any endpoint returns `{"detail": "Could not build ..."}` (HTTP 500), check `main.py`'s logger output for the exception — it'll point at the broken import or symbol.

- [ ] **Step 5: Commit**

```bash
git add main.py scripts/summarize_ai_runs.py
git commit -m "refactor(main): import analytics builders from analytics.run_summary"
```

---

### Task 6: Verify the metric and clean up the roadmap

- [ ] **Step 1: Verify production has zero imports from `scripts/`**

Run: `grep -rn "from scripts\." --include="*.py" --exclude-dir=scripts --exclude-dir=tests --exclude-dir=.venv .`

Expected: empty output. No production module imports from `scripts/`.

If there are matches, they are additional smells outside Phase 1 scope — note them in the roadmap as future work. Do not fix them in this plan.

- [ ] **Step 2: Verify the line-count metric**

Run: `wc -l scripts/summarize_ai_runs.py analytics/run_summary.py`

Record the numbers. Expected approximately:
- `scripts/summarize_ai_runs.py`: ~145 lines (was 882)
- `analytics/run_summary.py`: ~740 lines

- [ ] **Step 3: Update the roadmap**

Edit `docs/superpowers/plans/2026-04-26-lego-ification-roadmap.md`:

1. Find the Phase 1 section header. Change `**Status:** Ready to execute. Smallest phase; warm-up lap.` to `**Status:** ✅ Complete (commit <SHA>). Warm-up lap.` — replacing `<SHA>` with `git rev-parse --short HEAD`.

2. Find the Phase 1 scope bullet `Move scripts/summarize_ai_runs.py::build_summary_payload (and any data-shape helpers it depends on) into a production-owned module`. Replace it with: `Moved both build_summary_payload and build_learner_summary_payload (4 call sites in main.py, not the 2 the initial graph reported) into analytics/run_summary.py.`

3. In the Diagnosis section, change `2 calls` to `4 calls` in the smell line.

4. In the Success Metric table, fill in the row for "Production imports from `scripts/`" under "Phase 2 target" with the now-confirmed `0`.

- [ ] **Step 4: Commit the roadmap update**

```bash
git add docs/superpowers/plans/2026-04-26-lego-ification-roadmap.md
git commit -m "docs(roadmap): mark Phase 1 complete and correct call-site count"
```

---

## Definition of Done

- [ ] `analytics/run_summary.py` exists and owns the production summary logic.
- [ ] `scripts/summarize_ai_runs.py` is a thin CLI shim (~145 lines).
- [ ] `main.py` imports from `analytics.run_summary`, not `scripts.summarize_ai_runs`.
- [ ] All 8 characterization tests pass.
- [ ] Full test suite has no new failures.
- [ ] Both `/api/analytics/ai-runs` and `/api/analytics/learner-runs` (with and without `concept_ids`) return correctly-shaped payloads via curl smoke check.
- [ ] CLI still works in both markdown and `--json` modes.
- [ ] `grep "from scripts\." --include="*.py" --exclude-dir=scripts --exclude-dir=tests` returns empty.
- [ ] Roadmap updated with completion SHA and corrected call-count.

## Rollback

If the work is interrupted mid-plan:

- After Task 1: tests added, no production change. Safe to leave as-is or `git revert` the test commit.
- After Task 2: new module exists alongside old code. No behavior change yet (nothing imports the new module). Safe to leave or `git revert` Tasks 1+2.
- After Task 3: tests target new module. CLI shim not yet in place. `main.py` still imports from scripts. The duplication is temporary but harmless. Safe to leave or revert.
- After Task 4: CLI shim in place. `main.py` still imports from scripts. Production behavior unchanged because the shim re-exports. Safe to leave.
- After Task 5: Phase 1 logically complete. Roadmap update is paperwork; not a blocker.

## Anti-Patterns to Avoid (Phase 1 Specific)

- **Do not parameterize the log paths "while you're in there."** That's a contract change; it belongs in a separate plan if needed.
- **Do not move `render_markdown` into `analytics/`** even though it could conceivably be used by an HTML rendering route someday. YAGNI. It's CLI presentation today.
- **Do not introduce a `BaseSummary` class or any abstraction.** Two functions don't need a class hierarchy.
- **Do not "improve" the existing aggregation code.** Even if you spot a `Counter()` that could be a `defaultdict(int)`, leave it. This commit is an extraction, not a tidy-up.
- **Do not add type hints, validation, or Pydantic models** to the moved functions. Same reason.

## Notes

- The CLI shim duplicates the rendering logic verbatim from the original script — no extraction of `render_markdown` happens. This is intentional. `render_markdown` is presentation, has no production callers, and would only become a candidate for extraction if a future endpoint also needed markdown rendering (it doesn't).
- The empty `analytics/__init__.py` is intentional. We do not re-export symbols from the package because callers will import the explicit module path. (Re-exports through `__init__.py` are an anti-pattern in this style — they hide the dependency and complicate static analysis.)
- The post-phase architecture snapshot will show `analytics-run_summary` as a new node in the graph. The next time the code-review-graph rebuilds, the Phase 1 section of the roadmap should be re-checked: the cross-community edge that was `main.py → scripts/summarize_ai_runs.py` should now be `main.py → analytics/run_summary.py` (and the production-from-scripts edge should be gone).
