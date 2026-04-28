# CODEX REVIEW — pipette B-revision (grill-with-docs swap)

You are an independent reviewer. The pipette implementation plan
(`docs/superpowers/plans/2026-04-28-pipette.md`) was hardened over 28
rounds of prior gemini sanity-checks plus a ChatGPT audit. Phases B, C,
S, F all shipped (codex prompts at
`2026-04-28-phase-{b,c,s,f}-review.md`). 93 tests passed before this
revision; 93 tests pass after.

This review covers the **B-revision** (single commit `ef83756`): swapping
the Step 1 skill from `grill-me` to `grill-with-docs` and collapsing
Step 1.5 into Step 1, since `grill-with-docs` updates the project
glossary inline during grilling.

## What the B-revision was supposed to deliver

**Naming convention change:**
- `docs/pipeline/_meta/UBIQUITOUS_LANGUAGE.md` → `docs/pipeline/_meta/CONTEXT.md`
  (renamed via `git mv`; content updated to describe grill-with-docs ownership).
- Per-feature `01b-glossary-delta.md` artifact REMOVED. Glossary lives
  only in `_meta/CONTEXT.md` (single source of truth).

**State machine changes:**
- `jump_back_to` valid values reduced from `{1, 1.5, 2}` → `{1, 2}`.
  Touched: `sanity/schema.py:_ALLOWED_JUMP`, `cli.py` argparse choices on
  `archive-for-loop-back`, `cli.py` `parse-jump` regex,
  `orchestrator.py:archive_for_loop_back` `affected` dict
  (now raises `ValueError` on `jump_back_to=1.5`).
- `pipeline_graph.json`: dropped `step_1_5_glossary` and `gate_glossary`
  nodes plus their edges. The `gate_grill → step_1_5_glossary` edge
  re-routed to `gate_grill → step_2_diagram`. Added a top-level
  `_revision: "B (2026-04-28)"` annotation.
- `validate_pipeline_graph.py:ALLOWED_LOOP_BACK_EDGES` dropped the two
  `gate_glossary` entries and `gate_sanity → step_1_5_glossary`.

**Doctor changes:**
- Dropped `_verify_ubiquitous_language_skill` Check entry from CHECKS list
  (the function still exists as a deprecated stub returning True/note).
- Added `_verify_grill_with_docs_skill` Check (mirrors grill-me's "verified
  by Claude Code at session start" pattern; FIX message points users to
  symlink mattpocock's skills repo).

**Reviewer prompt updates** (`tools/pipette/sanity/reviewers/{contracts,
impact,glossary,coverage}.md`): artifact stack now lists
`00-graph-context.md, 01-grill.md, 02-diagram.{mmd|excalidraw},
_meta/CONTEXT.md` (was `..., 01b-glossary-delta.md, _meta/UBIQUITOUS_LANGUAGE.md`).
The `glossary` reviewer's body text rewritten to check terms against
`_meta/CONTEXT.md`.

**Slash command (`.claude/commands/pipette.md`) updates:**
- Frontmatter description: dropped "→ glossary delta", changed "grill" to
  "grill-with-docs (glossary updated inline)".
- Step 1 section rewritten to invoke `Skill: grill-with-docs`, pass
  `_meta/CONTEXT.md` to the skill, and note that grill-with-docs writes
  to CONTEXT.md inline + may emit ADRs.
- Step 1.5 section REMOVED entirely.
- All references to `paused_at_step ∈ {1, 1.5, 3}` → `{1, 3}`.
- All references to `jump_back_to ∈ {1, 1.5, 2}` → `{1, 2}`.
- Step 3 artifact stack and gemini-picker prompt updated to
  drop `01b-glossary-delta.md` and reference `_meta/CONTEXT.md`.
- Step 7 eval YAML drops `glossary` from `self_report` keys and `1.5`
  from `gemini_jump_back_distribution`.
- The slash command DOES still mention "Step 1.5" in B-revision-note
  paragraphs (intentional; explains what changed for future readers).

**Test updates:**
- `test_orchestrator.py::test_archive_for_loop_back_step_1_5_no_longer_valid`
  inverted — now asserts `ValueError` raised on `jump_back_to=1.5`.
- `test_e2e_integration.py::test_full_lifecycle_against_fakes`
  parse-jump assertions updated: `--jump-to 2` valid, `--jump-to 1.5` invalid.
- `test_command_file.py::test_pipette_command_references_each_step`
  step_marker list dropped "Step 1.5".

**What was NOT changed in this commit (deferred for follow-up):**
- The plan `docs/superpowers/plans/2026-04-28-pipette.md` still describes
  the pre-revision pipeline (Step 1.5, UBIQUITOUS_LANGUAGE.md).
- The spec `docs/superpowers/specs/2026-04-28-pipette-design.md` still
  describes the pre-revision pipeline.
- The codex review prompts for prior phases are historical artifacts and
  were not edited.

## What to flag

Real defects only:

- Stragglers: any reference to `01b-glossary-delta.md`,
  `UBIQUITOUS_LANGUAGE.md`, `step_1_5_glossary`, or `gate_glossary` in
  live code (NOT in B-revision-note paragraphs explaining the change)
- `jump_back_to=1.5` accepted anywhere it shouldn't be
- `1.5` accepted by the `parse-jump` regex
- `archive_for_loop_back(jump_back_to=1.5)` returning a path instead of
  raising
- Pipeline graph: any orphan reference to dropped nodes; cycles introduced
  by the edge re-route; reachability broken
- Reviewer prompt body text still mentioning the dropped per-feature
  glossary delta as input
- Slash command Step 1 not actually invoking `Skill: grill-with-docs`
  (e.g., missing the `Skill:` keyword, wrong skill name)
- Schema invariants on Verdict: NEEDS_RESEARCH should still require a
  `research_brief` object; PASS still must NOT set `jump_back_to`
- `_verify_grill_with_docs_skill` returning False or wrong format
- Tests that should pass but fail (e.g., the inverted
  archive_for_loop_back step 1.5 test)
- Test counts: should still be 93 total

What NOT to flag:

- Deferred plan + spec doc updates — those are explicitly out of scope
- The deprecated `_verify_ubiquitous_language_skill` stub kept for
  backwards-compatible imports — it's no longer in CHECKS
- The slash command's B-revision-note paragraphs that mention "Step 1.5"
  — they explain what changed and are load-bearing for future readers
- The `pipeline_graph.json` `_revision` annotation — JSON-with-comments
  isn't standard but pyyaml parses it and it's documentation
- The grill-with-docs skill not being registered in Claude Code yet —
  that's the user's environment setup, not a code defect

## Required output

Emit ONE YAML object and nothing else:

```yaml
verdict: PASS | NEEDS_CHANGES
confidence: 0.0–1.0
findings:
  - severity: critical | high | medium | low
    location: <commit SHA + file path + line if known>
    claim: <one sentence>
    evidence: <quoted line from diff>
    suggested_fix: <concrete>
notes: <one paragraph if cross-cutting>
```

`PASS` with empty findings is allowed. `NEEDS_CHANGES` requires ≥1
critical or high finding.

## Git range

Single commit: `ef83756`. The 1b1d8ee (TODO.md) and 60540a0 (cycle fix)
commits before it are already covered by the prior Phase S codex review.

To capture log + diff:

```bash
git show ef83756 --stat > /tmp/b_revision.txt
git show ef83756 >> /tmp/b_revision.txt
```

Or pipe directly:

```bash
{ git show ef83756 --stat; echo; echo "=== DIFF ==="; echo;
  git show ef83756; } | codex exec --prompt-file - \
  docs/superpowers/plans/codex-prompts/2026-04-28-b-revision-review.md
```

(Adjust `codex` invocation to match your local CLI.)
