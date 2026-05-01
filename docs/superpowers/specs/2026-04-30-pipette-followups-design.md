# Pipette implementation follow-ups — chunked execution design

**Date:** 2026-04-30
**Source findings:** `docs/pipeline/_meta/implementation-followups.md` (F1–F15 from 2026-04-28 admin-tink-todo-dashboard run)
**Goal:** ship F1–F15 as a small number of well-bounded PRs, each with narrow per-fix tests, derived from explicit principles rather than convention.

---

## Principles

These shape every chunk boundary and ordering decision below. Anywhere the chunking diverges from "obvious," the divergence cites the principle.

1. **Pure additions ship before behavior changes.** Smaller blast radius, cheaper to verify in isolation.
2. **Verifiability before priority.** An unverifiable high-severity fix lands later than a verifiable medium one — shipping unverifiable changes first taints later verification.
3. **Dependencies include verification, not just code.** If chunk X's tests rely on chunk Y's tools telling the truth, Y comes first.
4. **Coupling is shared state or contract, not shared file.** F4 and F9 share a contract (must ship together). F8 and F10 share a file but not state (can ship apart).
5. **One reason to fail review per chunk.** If a chunk could be rejected for two unrelated reasons, split it.
6. **Each chunk's outputs become test infrastructure for later chunks.** Order accordingly.
7. **Macro-gate before micro-optimization.** Fix what determines "do we even run Step 3" (F15) before optimizing Step 3 cost (F11/F12/F13).
8. **Prevent-future-false-signals beats recover-from-them.** Tools that lie get fixed early.
9. **Risk scales with hidden-state touched.** Frontmatter-line change ≠ orchestrator dispatch change.
10. **Don't fake test coverage you don't have.** LLM-prompt changes get manual fixtures, documented as such — no brittle mock-LLM tests.

---

## Test discipline (applies to every chunk)

- **Narrow per-fix tests.** Each fix ships with a regression case that fails on `main` before the fix and passes after. The exception is LLM-prompt changes (Chunk E), which get a documented manual fixture instead — see Principle 10.
- **One observable outcome per commit.** Where a chunk has multiple commits, each commit's test file grows by exactly one assertion-set, so a future `git bisect` lands on the precise commit.
- **Reproduce the failure mode on `main` before fixing.** Confirms the bug exists and gives a starting fixture for the test. Skipped only for trivially-correct fixes (F2 frontmatter deletion, F5 doc-only changes).
- **Test scope:** narrow per-fix only. No E2E smoke harness for pipette in this work — see scope cuts below.

---

## Chunks

Six chunks, in execution order. Each is one PR. Each can be reverted independently of the next.

### A — Unblock (F2)

**Contains:** F2. Drop `disable-model-invocation: true` from `~/.claude/skills/grill-with-docs/SKILL.md` frontmatter.

**Why this is its own chunk (P9):** trivial risk, no shared state, no other fix is gated on this — but every pipette run is currently gated on it. Ship immediately and independently.

**Files touched:** `~/.claude/skills/grill-with-docs/SKILL.md` (global, not in repo).

**Verification:** manual. Dispatch `Skill: grill-with-docs` from a throwaway invocation; confirm no `disable-model-invocation` error. No automated test possible (the file is outside the repo).

**Done signal:** the skill dispatches without error.

---

### B — Trace contract (F4 + F9)

**Contains:** F4 (`trace-append` accepts structured `--data 'k=v,k2=v2'`) and F9 (unify gemini_picker's structured-event writes through the same path).

**Why grouped (P4):** F4 and F9 share a contract — the trace event-write API. Shipping them apart leaves an inconsistency window where Python-side and CLI-side disagree on event shape. **Why before C/G/F (P6):** later chunks' tests need to assert structured trace events; this chunk gives them the API to do so.

**Files touched:** `tools/pipette/cli.py`, `tools/pipette/trace.py`, `tools/pipette/gemini_picker.py`.

**Verification:**
- New `tests/pipette/test_cli.py` with parser tests for `trace-append --data 'k=v,k2=v2'`.
- Assertion: structured event lands in `trace.jsonl` with the expected JSON keys.
- Refactor gemini_picker to call the shared helper; existing structured-event behavior preserved. Regression test asserts gemini_picker still produces the documented `gemini_verdict` event shape: `{"ts","step":3,"event":"gemini_verdict","decision","jump_back_to"}`.

**Done signal:** `pytest tests/pipette/test_cli.py` green; gemini_picker still produces the same trace event shape.

---

### C — Signal honesty (F1 + F3 + F5 + F8)

**Contains:** F1 (doctor in-session MCP probe), F3 (build-coverage-map malformed-dump warning), F5 (shared MCP-fallback section in reviewer prompts), F8 (subagent_stop hook reads lockfile for current step).

**Why grouped (P8):** all four are "the tool must stop lying." Different files, shared theme.

**Tension with P5 (acknowledged):** strict P5 would split this into four chunks (one per fix). We trade strict P5 for fewer PRs by relying on per-commit revertibility as the mitigation: each fix is its own commit, with its own test, so a reviewer can request changes to commit 3 without blocking commits 1, 2, or 4. If review feedback on any single commit becomes contentious, that commit splits out into its own PR rather than holding the chunk hostage.

**Why before E (P3, gemini's hazard):** Chunk E debugs grill behavior; if doctor lies about MCP availability, every grill verification is suspect. **Why before G (P3):** F15's heuristic auto-pass uses coverage data; if coverage dumps are silently malformed (F3), the auto-pass makes wrong decisions.

**Files touched:**
- `tools/pipette/doctor.py` (F1)
- `tools/pipette/cli.py` (F3, additive — separate command path from B's changes)
- `tools/pipette/sanity/reviewers/_shared/mcp-fallback.md` (F5, new file) and `tools/pipette/sanity/reviewers/{contracts,impact,glossary,coverage,verifier}.md` (F5, reference the shared block)
- `tools/pipette/subagent_stop.py` (F8) and `tools/pipette/lockfile.py` (read helper if needed)

**Verification:**
- F1: new `tests/pipette/test_doctor.py`. Probe returns `⚠` when the deferred-tool list lacks `mcp__code-review-graph__` prefix; returns `✅` when present. Mock the tool list as a fixture.
- F3: in `tests/pipette/test_cli.py`, fixture with a malformed dump (no `tests/`-prefixed `from.source_file` edges). Assert stderr warning is printed; `--strict` flag (if added) returns nonzero.
- F5: doc-only, no automated test. Manual diff review.
- F8: new `tests/pipette/test_subagent_stop.py`. Hook reads lockfile, tags trace event with the current step (e.g., `step=3` during reviewer dispatch, not hardcoded `step=5`).

**Done signal:** all four commits' tests green; doctor manually re-run shows correct ⚠/✅ behavior; reviewer prompt diff is reviewable.

---

### G — Macro gate (F15 + F14)

**Contains:** F15 (heuristic auto-pass at Step 3 entry) and F14 (`pipette-lite` slash command).

**Why grouped (P4):** F14 is the explicit lite mode; F15 is the heuristic that makes lite mode meaningful. They share the "skip Step 3 hard gate" decision surface. **Why before F (P7, gemini's hazard):** F15 determines which runs go through Step 3 at all. Building F15 first means F11/F12/F13 are correctly scoped to "the runs that still need Step 3" — narrower surface, easier tests, no risk of optimizing dead code paths.

**Files touched:** `tools/pipette/orchestrator.py`, new `.claude/commands/pipette-lite.md` (or wherever the existing pipette command lives), possibly `tools/pipette/cli.py` for a `pipette-lite` entry point.

**Heuristic thresholds (hardcoded constants, per scope cuts):**
```
auto-pass IFF
  all_affected_files.coverage >= 0.80
  AND max_risk_score < 0.30
  AND total_changed_lines < 50
```
No scoring module, no configuration file. Constants live next to the gate function.

**Verification:**
- New `tests/pipette/test_orchestrator_dispatch.py` with five cases:
  1. All thresholds pass → auto-pass; `03-gemini-verdict.md` written with `heuristic auto-pass`; reviewers/verifier never dispatched.
  2. One threshold fails → fall through to full Step 3 ceremony; trace event `autopass_rejected` written with `reason` naming the failed threshold (`coverage_below_80`, `risk_above_30`, `lines_above_50`). Required for future threshold tuning without guessing.
  3. Coverage data malformed (depends on F3's warning path) → fall through to full Step 3 with `autopass_rejected reason=coverage_malformed`.
  4. F14 vs F15 precedence: `pipette-lite <topic>` invoked with synthetic high-risk-score input; the lite path bypasses Step 3 unconditionally, ignoring F15's heuristic. Lite mode is an absolute manual override.
  5. Lite path integration: `pipette-lite <topic>` runs Steps 0, 1, 2, 4, 5, 6, 7 (single-subagent, no best-of-N) and never enters Step 3 dispatch.

**Done signal:** dispatch tests green; manual lite run on a trivial change completes in expected token budget.

---

### F — Step 3 surface (F13 + F11 + F12 + F10)

**Contains:** F13 (per-reviewer artifact subsets), F11 (smart redispatch on loop-back), F12 (skip verifier on attempt ≥ 2), F10 (archive reviewer/verifier scratch on loop-back).

**Why grouped (P4):** all four touch Step 3 dispatch and archive state. They share a state machine, not just a file. F10 in particular is Step 3 archiving — gemini correctly flagged that grouping it with hook-cosmetic F8 was a grab-bag.

**Why four commits inside one PR (P5):** each fix is independently revertible and has its own test, but they ship together because reviewing the dispatch state machine in four separate PRs would be more expensive than reviewing it once with four commits.

**Order of commits inside the PR:** F13 → F11 → F12 → F10 (least to most state-touching).

**Why after G (P7):** F15 narrows the surface that F11/F12/F13 optimize. Building this on top of G means we're optimizing the runs that actually need optimization, not the runs the auto-pass already short-circuits.

**Files touched:** `tools/pipette/orchestrator.py` exclusively.

**Verification:**
- F13: per-reviewer artifact lookup table. Test: each reviewer's prompt context contains only the expected artifacts; e.g., glossary reviewer never sees `00-graph-context.md`.
- F11: `--smart-reviewers` flag (default ON for attempts ≥ 2). Test: on loop-back, only reviewers that flagged ≥ medium in the prior attempt's verifier-survivors are redispatched. **Fallback:** if `_verifier-survivors.json` is malformed or missing on loop-back, default to full reviewer dispatch with a logged warning (`smart_reviewers_fallback reason=survivors_unparseable`). Test: malformed-fixture case asserts full dispatch + warning event.
- F12: skip verifier on attempt ≥ 2 **only if** attempt 1's `_verifier-survivors.json` exists and parses cleanly. If attempt 1's verifier crashed or output was malformed, attempt 2 still runs the verifier (the verification chain isn't broken silently). Test: dispatch decision under both conditions; reviewer outputs are filtered by 0.8 confidence directly when skip is allowed.
- F10: archive function file list extended. Test: after a loop-back, `_attempts/N-<ts>/` contains `_reviewer-*.json`, `_verifier-output.json`, `_verifier-survivors.json`, `_step3-prompt.txt`, `_gemini-stdout.log` in addition to the original three artifacts.

**Done signal:** four commits' tests green; a loop-back regression run on the same fixture used to motivate F11/F12 shows reduced total token count vs. the run captured in `implementation-followups.md` (rough — not strict pass/fail).

---

### E — Grill quality (F6 + F7)

**Contains:** F6 (verify-cited-symbols round-trip in grill — option (a) lightweight version) and F7 (deployment topology check for Dev-only Routes).

**Why grouped (P4):** both are grill-procedure changes — they modify the same skill (or inlined slash command) prompt. Shipping them together means one revision of the grill spec, not two.

**Why ships option (a), not (c):** scope cut. The `<verify-this>` block design is captured below as future work but not implemented in this round.

**Why last (P2, P9):** highest blast radius (LLM-prompt change), no deterministic test possible (P10), so it lands when the deterministic-test infrastructure from B/C/G/F is in place to detect grill regressions in later runs through observability rather than unit tests.

**Files touched:** `~/.claude/skills/grill-with-docs/SKILL.md` (global) OR `.claude/skills/pipette/SKILL.md` + the inlined slash-command flow, depending on whether F2 (Chunk A) restored the skill's invocability. If A succeeded, the canonical fix lives in the grill skill; if it didn't, fix the inlined version in pipette.

**F6 fix (option a):** before Step 1 produces its design summary, the grill must Read the single most-cited symbol in its code snippet and confirm the field/method shape exists. The grill prompt instructs the model to log this round-trip as a structured trace event (`grill_symbol_verified` with the symbol name) and refuse to write `01-grill.md` without it. **Enforcement is prompt-level, not orchestrator-level** — the grill's discipline is what holds the gate, with the trace event providing observability so we can audit whether it skipped. A hard orchestrator-side gate (parsing `01-grill.md` for the verification block, refusing to advance Step 2 if absent) is captured in Future work.

**F7 fix:** when the grill marks a route as **Dev-only Route** per CONTEXT.md, it must (1) Read `vercel.json` (or equivalent config — the grill prompt names the file explicitly so the LLM doesn't hallucinate routing layers from pre-training), then (2) produce a deployment-topology block that names every layer between client and FastAPI handler (e.g., `Vercel CDN → FastAPI middleware → handler`). Either the route's HTML shell is served by a FastAPI handler (`HTMLResponse`), or the cited `vercel.json` rewrites confirm forwarding the path to the function. Mirrors F6's "Read the cited symbol before claiming its shape" discipline.

**Verification:** manual fixture, documented in the PR description.
- **F6 fixture:** the literal admin-tink-todo state.email failure. A grill output that names `state.email` when `AuthSessionState.email` doesn't exist (only `state.user.email`) — orchestrator must refuse to advance Step 1.
- **F7 fixture:** a grill output for an `/admin/*` route that places gating in FastAPI middleware while the HTML lives in `public/` — grill must produce the topology block and either move the HTML to a handler or cite `vercel.json` rewrites.

No automated test (P10). The PR description includes screenshots / log excerpts of both fixtures running on `main` and failing, then running on the branch and passing.

**Done signal:** both manual fixtures pass on the branch; PR description documents them.

---

## Out of scope (explicit YAGNI)

- **No automated regression tests for LLM-prompt changes** (Chunk E). Manual fixture verification only, documented in PR. Brittle mock-LLM tests are worse than admitting the gap.
- **No E2E pipette smoke harness.** Pipette is still evolving fast; a harness now would create churn.
- **No `orchestrator.py` architectural refactor.** Chunks C/F/G all touch it — we change behavior only, not structure.
- **No new MCP tooling.** F1's probe checks the existing tool list; it doesn't try to fix MCP server lifecycle.
- **No Step 1 "v2" rewrite (F6 option c).** The `<verify-this>` block design is captured in "Future work" below; this round ships option (a) only.
- **No retroactive lessons curation.** The lessons block at the bottom of `implementation-followups.md` is appended once to `_meta/lessons.md` as a standalone tiny PR landed to `main` *before* any chunk branch is cut. Each chunk then branches from updated `main` and carries only its own commits — Chunk A's PR independence (P9) is preserved. After this one-shot housekeeping, we close the loop.
- **No backwards compatibility for in-flight pipeline scratch files.** Local `_reviewer-*.json` / `_verifier-*.json` files from prior runs may not be readable post-Chunk-F. Users delete and re-run.
- **F15 thresholds are hardcoded constants, not a configurable scoring module.** No risk-scoring abstraction. The thresholds (`coverage ≥ 0.80`, `risk < 0.30`, `lines < 50`) live as constants in the gate function.

---

## Future work (deferred, not part of this spec)

- **F6 option (c)** — `<verify-this>` blocks in `01-grill.md` extracted by Step 0 into auto-generated test harnesses. The systemic fix; option (a) is the lightweight version.
- **Hard orchestrator-side gate for F6/F7** — parse `01-grill.md` for the verification block / topology block; refuse to advance Step 2 if absent. Currently enforcement is prompt-level discipline + observability via trace events. If the trace shows the grill skipping verification under load, escalate to a hard gate.
- **E2E pipette smoke harness** — fixture-based dry-run walking Steps 0→7 with stub LLMs. Worth building once the surface stabilizes.
- **Configurable F15 risk scoring** — if hardcoded thresholds prove too rigid in practice, generalize into a small scoring module with weights.

---

## Execution order summary

```
A (F2)
  → B (F4 + F9)
    → C (F1 + F3 + F5 + F8)
      → G (F15 + F14)
        → F (F13 + F11 + F12 + F10)
          → E (F6 + F7)
```

Each arrow is a strict dependency: the next chunk's verification relies on outputs of the previous one.
