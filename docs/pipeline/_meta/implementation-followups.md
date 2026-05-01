# Pipette implementation follow-ups

Edge cases discovered while running real pipelines. Each item names the specific code/spec change needed. Captured per-run and rolled forward — newest at top.

Format: `## YYYY-MM-DD — <kebab-topic>` then one section per finding with **What broke**, **Where**, **Fix**, **Severity** for the pipette implementation.

---

## 2026-04-28 — admin-tink-todo-dashboard (Step 3 FAIL → loop-back)

### F1. Doctor PASSes when MCP `code-review-graph` tools are not exposed in the session

**What broke:** `pipette doctor` reports `✅ code-review-graph CLI + MCP wired: CLI status OK + MCP enabled in settings.local.json`. But the actual `mcp__code-review-graph__*` tools were not loaded into the Claude session — `ToolSearch` for them returned no matches. Step 0 was supposed to call them as the primary path; recovered via direct SQLite + CLI fallback.

**Where:** `tools/pipette/doctor.py` (or wherever the MCP-enabled check lives). The check inspects `~/.claude/settings.local.json` (or project-local equivalent) and confirms the server is configured. It does NOT confirm tools are exposed *in the running session*.

**Fix:** add an in-session probe to doctor: try a no-op call (e.g., `mcp__code-review-graph__status`) via the Claude harness or check the deferred-tool list for the prefix `mcp__code-review-graph__`. If not present, return `⚠️` (not `✅`) with the message: "MCP server configured but tools not exposed in session — restart Claude Code or check `claude --mcp-debug`."

**Severity:** medium. Pipeline degraded gracefully via fallback, but the doctor's `✅` was misleading.

---

### F2. `grill-with-docs` skill has `disable-model-invocation: true` — orchestrator can't drive it

**What broke:** Spec §3 Step 1 says "Invoke `Skill: grill-with-docs`". The skill at `~/.claude/skills/grill-with-docs/SKILL.md` carries `disable-model-invocation: true` in its frontmatter, which makes the Skill tool refuse:

```
Skill grill-with-docs cannot be used with Skill tool due to disable-model-invocation
```

The orchestrator hit a hard stop. Workaround: inlined the skill's procedure in the slash-command flow.

**Where:** EITHER `~/.claude/skills/grill-with-docs/SKILL.md` (drop the `disable-model-invocation` line), OR `.claude/skills/pipette/SKILL.md` + slash command (replace "Invoke Skill: grill-with-docs" with the inlined procedure).

**Fix:** prefer dropping the flag from the skill — the skill is designed to be driven, and pipette is a legitimate driver. If it must stay user-only, then the spec needs a fallback path: either inline the skill content in the slash command, OR pause the pipeline asking the user to type `/grill-with-docs` directly.

**Severity:** high. Without the inline workaround, every pipette run hard-pauses at Step 1.

---

### F3. `build-coverage-map` accepts malformed dump shape silently

**What broke:** the CLI expects `{edges: [{from: {source_file: "tests/..."}, to: {source_file: "..."}}, ...]}` with **relative paths** that start with `tests/`. The first dump from a SQL query used `{source_qualified, source_file, target_qualified, target_file}` keys with **absolute paths**. The CLI didn't error — it returned all 0.30 coverages because no edge matched its filter. False signal: would have triggered TDD enforcement and best-of-N for files that were actually well-tested.

**Where:** `tools/pipette/cli.py:229` (`if args.cmd == "build-coverage-map"`).

**Fix:** validate the dump shape before processing. If the dump has `edges` but zero of them have `from.source_file` starting with `tests/`, print `pipette: warning — coverage dump appears malformed (no test→source edges); coverage map will be all-uncovered. Verify dump shape: {edges:[{from:{source_file: "tests/..."}, to:{source_file: "..."}}]}` to stderr. Optionally exit nonzero if `--strict` flag passed.

**Severity:** medium. Silent shape mismatch is exactly the class of bug that causes pipeline-wide false alarms.

---

### F4. `trace-append` rejects `key=value` extras after `--event=...`

**What broke:** Tried `python -m tools.pipette trace-append --folder=X --step=3 --event=verdict_fail jump_back_to=1` to capture structured event data; got `pipette: error: unrecognized arguments: jump_back_to=1`. Trace events are flat strings — no structured payload supported.

**Where:** `tools/pipette/cli.py` trace-append parser.

**Fix:** EITHER (a) accept `--data 'key=value,key2=value2'` and write it as JSON in the trace event; OR (b) update the spec to make explicit that event is a snake_case string with all context inlined (e.g., `verdict_fail_jump_back_to_1` instead of `verdict_fail` + `jump_back_to=1`). (b) is simpler and matches the existing convention in trace.jsonl.

**Severity:** low. Workaround is trivial (collapse into the event name), but the error message could hint at it.

---

### F5. Reviewers and verifier prompts hard-code MCP usage with no fallback

**What broke:** `tools/pipette/sanity/reviewers/impact.md` says "re-running `mcp__code-review-graph__get_affected_flows`" and `verifier.md` says "Use the `code-review-graph` MCP". When MCP isn't exposed (see F1), each subagent has to figure out the fallback (SQLite or Grep) on its own. They did, but it cost extra tool turns.

**Where:** `tools/pipette/sanity/reviewers/{impact,verifier}.md`.

**Fix:** add a "MCP fallback" section to each reviewer prompt that names the SQLite path, schema, and Grep alternative — so subagents don't waste turns rediscovering it. Could also be one shared block in `tools/pipette/sanity/reviewers/_shared/mcp-fallback.md` referenced by each reviewer.

**Severity:** low. Doesn't break anything, just costs tokens.

---

### F6. Step 3 design-bug pattern: state-shape contracts not pre-checked

**What broke (case the user asked to capture):** the grill summary at Step 1 wrote a code snippet (`if state.email != ADMIN_EMAIL`) that referenced a non-existent attribute. The grill confidently exited; only the contracts reviewer caught it at Step 3 with `confidence: 0.98`. The grill's R1 said "the session state has `email` field per Supabase" — but `AuthSessionState` exposes email via `state.user.email`, where `user` may be None.

**Where:** Step 1 grill procedure (`grill-with-docs` skill OR the inlined version in the pipette slash command).

**Fix options:**
- (a) **Lightweight:** before Step 1 produces its design summary, the grill must run `Read` on the **single most-cited symbol** in its code snippet and confirm the field/method shape. The grill should fail to advance until this round-trip is done.
- (b) **Heavyweight:** add a 5th reviewer "schema-shape" specifically focused on attribute access on dataclasses/Pydantic models, run in parallel at Step 3.
- (c) **Best:** require the grill to write any handler-shaped pseudocode in `01-grill.md` *as a `<verify-this>` block* — Step 0 then auto-extracts these blocks and writes test harnesses that import the cited symbols and call `getattr` to confirm they exist. Empty failure list = green; any failure = grill must revise before Step 1 user gate fires.

(a) is cheapest; (c) is the design that prevents this class of bug systemically. Recommend (a) for v1, (c) for v2.

**Severity:** high. This was the most embarrassing finding — Step 1 produced code that wouldn't survive `python -c "from auth.service import AuthSessionState; AuthSessionState(...).email"`. The pipeline caught it at Step 3, but Step 1 should have.

---

### F7. Step 3 design-bug pattern: deploy-target reasoning not stress-tested

**What broke:** Vercel CDN serves static files in `public/` *before* FastAPI middleware fires. The grill's R2 said "Dev-only Route registration: refuses to register if `APP_BASE_URL` ≠ localhost OR file doesn't exist." But that guard is inside the FastAPI app — irrelevant for static-file CDN delivery. The grill missed this because it framed `public/` files as part of the FastAPI surface, when in fact they're a separate hosting layer.

**Where:** Step 1 grill procedure.

**Fix:** when the grill marks a route as **Dev-only Route** (per CONTEXT.md), it must produce a "deployment topology check" that names every layer that could intercept the request between client and the FastAPI handler. For socratink-app, that's: `Vercel CDN → FastAPI middleware → handler`. Vercel CDN serving `public/*` directly bypasses everything below it. Either: (a) the route's HTML shell is served by the FastAPI handler itself (`HTMLResponse`), not from `public/`; (b) the `vercel.json` rewrites must be inspected and confirmed to forward `/admin/*` to the function.

**Severity:** high. This is the second class of recurring grill bug — confidently reasoning about gating without modeling the full request topology.

---

### F8. SubagentStop hook fires at every subagent dispatch and logs `step=5` regardless of actual step

**What broke:** trace.jsonl shows 6 `step=5 event=subagent_stop_hook decision=allow reason="no current_task.json — orchestrator hasn't dispatched"` entries. They fired during Step 3 (when the 4 reviewers and the verifier subagent stopped). The hook hardcodes `step=5` and only relies on the `current_task.json` presence to decide allow/deny.

This is correct behavior on the deny gate (no false positives), but the trace is misleading: 6 events tagged `step=5` happened during Step 3.

**Where:** the SubagentStop hook handler — wherever it writes the trace event (likely `tools/pipette/hooks/subagent_stop.py` or similar).

**Fix:** read the lockfile to determine the current pipeline step at hook-fire time and tag the event with that step. Reviewer subagents would log `step=3 event=subagent_stop_hook ...`; only Step-5 subagents would log `step=5`. Easier to filter the trace and reason about hook activity.

**Severity:** low. Cosmetic — events are correctly recorded, just mis-labeled by step.

---

### F10. `archive-for-loop-back` only archives the 3 named artifacts, not Step 3 scratch

**What broke:** on `loop`-back from a Step 3 FAIL, `archive-for-loop-back --jump-back-to=N` moves only `01-grill.md`, `02-diagram.mmd`, and `03-gemini-verdict.md` to `_attempts/N-<ts>/`. It leaves behind `_reviewer-*.json` (4 files), `_verifier-output.json`, `_verifier-prompt.txt`, `_verifier-survivors.json`, `_step3-prompt.txt`, and `_gemini-stdout.log` in the main folder. The next Step 3 run overwrites all of these — destroying the audit trail for attempt 1's reasoning.

To fully reconstruct attempt 1, you'd need the reviewer JSONs and verifier output (the surviving findings the gemini picker actually saw). `03-gemini-verdict.md` captures a summary, but the structured data is lost.

**Where:** `tools/pipette/orchestrator.py` (`archive_for_loop_back` function, wherever it picks the file list).

**Fix:** also archive `_reviewer-contracts.json`, `_reviewer-impact.json`, `_reviewer-glossary.json`, `_reviewer-coverage.json`, `_verifier-output.json`, `_verifier-survivors.json`, `_step3-prompt.txt`, `_gemini-stdout.log`. These are scratch but they ARE the audit trail. After archiving, the main folder should have only the persistent run artifacts (`00-graph-context.md`, `coverage_map.json`, `trace.jsonl`, `_graph_test_coverage_dump.json`).

**Severity:** medium. Audit trail completeness matters for post-hoc analysis of why a design failed and what changed in the revised attempt.

---

### F9. `gemini-picker` writes structured trace events; `trace-append` CLI does not

**What broke:** the gemini-picker auto-logged `{"ts":"...","step":3,"event":"gemini_verdict","decision":"FAIL","jump_back_to":1.0}` to trace.jsonl — a structured event with multiple keys. But `python -m tools.pipette trace-append --event=...` only accepts `--event` as a flat string (see F4).

**Where:** `tools/pipette/gemini_picker.py` writes structured events directly via Python; `tools/pipette/cli.py` `trace-append` only accepts the flat-event form.

**Fix:** unify. Either add `--data` to the CLI (per F4) so external callers can write structured events, or document that all Python-side events should use a shared `trace.append_event(folder, step, event, **kwargs)` helper and the CLI is intentionally simpler. Pick one and document.

**Severity:** low. Inconsistency, not a break.

---

### F11. Step 3 reviewer redispatch on loop-back is too aggressive

**What broke:** on `loop`-back, all 4 reviewers re-run regardless of whether they had findings in the prior attempt. In this run, the glossary reviewer found nothing critical/high in attempt 1, but was still dispatched in attempt 2 (53k tokens). Verifier coverage of glossary's attempt-2 findings (1 medium + 2 low + 3 polish) added zero design-fork signal.

**Where:** orchestrator's Step 3 dispatch logic.

**Fix:** add `--smart-reviewers` flag (default ON for attempts ≥ 2). On loop-back, only redispatch reviewers that flagged a `>= medium` finding in the immediately-prior attempt's verifier-survivors. Reviewers that came up clean in the prior round can carry forward unchanged. Estimated savings: 30-50% of Step 3 cost on loop-back attempts.

**Severity:** medium. Cost-driver. Not breaking — just expensive.

---

### F12. Step 3 verifier on attempt 2+ is largely redundant

**What broke:** the verifier's purpose ("re-check each finding against the actual codebase, drop hallucinations") was load-bearing for attempt 1. For attempt 2, the reviewers already had attempt 1's verifier-survivors as context (so they're already grounded against real code). The attempt-2 verifier (128k tokens) dropped 0 findings — confirming everything the reviewers already verified.

**Where:** orchestrator's Step 3 dispatch logic, specifically the verifier subagent dispatch.

**Fix:** skip the verifier on attempt ≥ 2 IF the reviewers had access to the prior attempt's verified findings as context. Apply the 0.8 confidence filter directly to reviewer outputs. Saves 80-130k tokens per loop-back. Risk: small chance of re-introducing hallucination if a reviewer drifts; mitigated by the fact that loop-back reviewers explicitly cite attempt-1 verified findings.

**Severity:** medium. Same as F11 — not breaking, just expensive.

---

### F13. Reviewers receive the full artifact stack regardless of relevance

**What broke:** every reviewer (contracts, impact, glossary, coverage) reads `00-graph-context.md` + `01-grill.md` + `02-diagram.mmd` + `_meta/CONTEXT.md` ≈ 20k bytes input even before they Grep/Read more. But:
- Glossary reviewer doesn't need `00-graph-context.md` (graph data, not glossary)
- Coverage reviewer doesn't need `_meta/CONTEXT.md` (terminology, not test coverage)
- Contracts reviewer doesn't need `02-diagram.mmd` directly (the grill names the symbols)
- Impact reviewer is the only one that genuinely needs all 4

**Where:** orchestrator dispatches identical artifact lists to each reviewer.

**Fix:** per-reviewer artifact subsets. Wire as a small lookup in the orchestrator: `{contracts: [00, 01], impact: [00, 01, 02, ctx], glossary: [01, 02, ctx], coverage: [00, 01, coverage_map]}`. Saves ~30% on per-reviewer context. Compounds with F11+F12.

**Severity:** low. Easy win.

---

### F14. Add a `pipette-lite` mode

**What broke (proactive):** for low-stakes runs, the full ceremony (4 reviewers + verifier + gemini hard gate, parallel subagents at K=3, full audit trail) is overkill. The current minimum cost of a pipette run is ~500k tokens regardless of payload size.

**Where:** new orchestrator mode.

**Fix:** add `pipette-lite <topic>` slash command. Drops Step 3 hard gate entirely (or reduces it to a single gemini critique against the artifact stack — no reviewers, no verifier). Keeps Steps 0, 1, 2, 4, 5 (single-subagent only, no best-of-N), 6, 7. Estimated cost: 60-100k tokens for a small task. Use cases: bug fixes, single-file features, dev-tooling, anything that doesn't touch prod customer surface.

Differentiator from default: doctor still required, design-tracked, lessons captured — just without the multi-reviewer hard gate.

**Severity:** medium. Currently no graceful low-cost path; users either run full pipette or skip the ceremony entirely. The middle ground would see use.

---

### F15. Add a heuristic-pass shortcut at Step 3

**What broke (proactive):** Step 3 hard gate runs even when the topic has trivial blast radius. Example: a 5-line bug fix to a file with 0.95 coverage and risk_score 0.1 still triggers 4 reviewers + verifier + gemini.

**Where:** orchestrator's Step 3 entry.

**Fix:** before dispatching reviewers, compute heuristic gate:
```
if all_affected_files.coverage >= 0.8 AND max_risk_score < 0.3 AND total_changed_lines < 50:
    auto-PASS, write 03-gemini-verdict.md with "heuristic auto-pass"
    advance to Step 4
```
The thresholds are tunable; the existence of the shortcut is the value. Pairs naturally with F14 (pipette-lite by default uses the heuristic; pipette default falls through to full ceremony if heuristic doesn't match).

**Severity:** medium. Not a breaking change; cost optimization for the well-tested-low-risk path that pipette currently penalises.

---

## Lessons (one-liners for `_meta/lessons.md`)

(Step 7 normally appends these; capturing here in case the run aborts before Step 7.)

- 2026-04-28 admin-tink-todo-dashboard: Step 3 caught 2 critical design bugs (state.email AttributeError; Vercel CDN bypass) that Step 1 grill should have caught — see F6, F7
- 2026-04-28 admin-tink-todo-dashboard: doctor PASSes on MCP-configured even when tools aren't exposed in-session — see F1
- 2026-04-28 admin-tink-todo-dashboard: `grill-with-docs` skill has `disable-model-invocation: true`, blocks orchestrator dispatch — see F2
