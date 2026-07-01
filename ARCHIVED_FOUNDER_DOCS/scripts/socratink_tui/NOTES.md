# Socratink TUI Working Notes

This folder is the working area for the founder-facing terminal dogfood app.
It is allowed to move faster than the browser product while still preserving
Socratink product truth.

## Learner Goal Rationale

Keep `learner_goal` as an optional but first-class field in the TUI.

Recommended learner-facing prompt:

```text
What do you want to be able to explain or do with this?
```

The field is pedagogically justified when used as personal relevance and
self-regulation context:

- Utility-value research supports asking learners to connect material to their
  own goals or uses. The likely product value is higher motivation, interest,
  and persistence because the route can feel personally useful rather than
  generic.
- Self-regulated learning models treat goals as anchors for planning,
  monitoring, and adaptation. In Socratink, the goal can help frame why a node
  matters and help the learner interpret the reconstruction loop.
- Goal-setting research supports specific accepted goals with feedback, but the
  TUI should avoid turning the field into performance pressure.
- Achievement-goal research favors mastery-oriented framing here. Ask what the
  learner wants to explain, use, or reconstruct; do not ask for a score, grade,
  credential, or proof of ability.

Product boundary:

- `learner_goal` may shape relevance, route emphasis, examples, prompt copy,
  and local framing.
- `learner_goal` is not evidence.
- `learner_goal` is not graded.
- `learner_goal` must not mutate graph truth.
- Derived state still comes only from the training record and learner
  reconstruction evidence.

Research anchors from the May 26, 2026 review:

- Utility-value interventions: Hulleman and Harackiewicz line of work; targeted
  interventions review; "Harnessing Values to Promote Motivation in Education".
- Self-regulated learning: goal setting as part of planning, monitoring, and
  adaptation.
- Goal-setting theory: Locke and Latham; specific accepted goals with feedback
  help performance, but learning contexts need care around task complexity.
- Achievement-goal theory: mastery-oriented goals fit Socratink better than
  performance-oriented goals.

## Iteration Log

### 2026-05-26: Inner Repair Dialogue Gate

Trigger:

- The founder-facing TUI made repair feel like a single vague text box followed
  by a terse pressure-check. That collapsed the actual learning object: a
  bounded dialogue around one missing causal operation.

What changed:

- Added a `repair-dialogue` bridge action on the existing Python LLM seam.
- Added graph-neutral `repair_dialogue_turn` events between `gap_identified`
  and final `repair`.
- Each turn logs `gap_id`, `missing_operation`, `support_level`,
  `causal_link_present`, `missing_operation_addressed`, `echo_risk`,
  `bridge_ready`, `next_dialogue_action`, and `not_mastery_reason`.
- Model Bridge is revealed only after the bridge-readiness rubric passes:
  `before state -> missing operation -> after state`.
- Renamed the old pressure-check surface to `post_bridge_transfer_check` so it
  cannot be mistaken for the inner drill.

Product boundary:

- Inner dialogue improves learning, but it is not mastery evidence.
- `repair_dialogue_turn` is always `score_eligible=false` and graph-neutral.
- Only the final bridge-ready learner-authored repair enters the existing
  training-store `repairs` array.
- Only spaced strong reconstruction may derive `solidified`.

Verification evidence:

- Added `tests/fixtures/socratink-tui/circular_repair_script.json`.
- Added bridge and TUI regression coverage for circular first repair, ready
  second repair, no Model Bridge before readiness, graph-neutral dialogue
  turns, and post-bridge transfer naming.
- Promoted replay case:
  `inner-repair-dialogue-gates-model-bridge-2026-05-26`.
- Focused result:
  `.venv/bin/pytest tests/test_socratink_tui.py -q --tb=short` -> `20 passed`.
- Harness result:
  `scripts/socratink-harness replay` -> `4 cases`, all PASS.

### 2026-05-26: Prompt-Level `/help`

Trigger:

- Founder dogfood needs a way to ask "what is expected here?" without breaking
  the learning loop or turning the TUI into a separate manual.

What changed:

- Added `/help` and `/help/` handling at every TUI input prompt.
- Help prints one brief explanation of the current step, then re-prompts for
  the same input.
- Scripted fixtures can now include `/help` before the real value to regression
  test the live prompt behavior.

Product boundary:

- `/help` is UI support, not learner evidence.
- Help text explains the step goal without revealing answer-key material.
- `/help` is not recorded in session events or training evidence.

Verification evidence:

- Added `tests/fixtures/socratink-tui/help_script.json`.
- Added `test_socratink_tui_help_command_explains_each_prompt_without_recording_help`.
- Focused result:
  `.venv/bin/pytest tests/test_socratink_tui.py -q --tb=short` -> `21 passed`.

### 2026-05-26: Cold Attempt Brief

Trigger:

- The cold attempt needed a little orientation so the learner knows what kind
  of response is expected without seeing the answer.

What changed:

- Added a static `[Cold Attempt Brief]` before the cold input.
- The brief shows the active node, learner goal, source-less provisional
  warning, and the instruction to try the current model before explanation.

Product boundary:

- The brief does not reveal the mechanism, expected causal steps, gap labels,
  or answer-shaped vocabulary.
- The brief is not logged as a training event.
- Cold attempt remains the first evidence event.

Verification evidence:

- Added assertions that the brief appears before `Cold attempt:` and that the
  hidden mechanism phrase does not appear before the learner answers.
- Focused result:
  `.venv/bin/pytest tests/test_socratink_tui.py -q --tb=short` -> `21 passed`.

### 2026-05-26: Own-Words Repair Before Model Bridge

What changed:

- Replaced the previous `Targeted Study -> Repair` order with
  `Delta -> Own-Words Repair -> Model Bridge`.
- The learner now sees a narrow missing-link cue before the full mechanism.
- The learner must try the repair in their own words before the model bridge is
  revealed.
- The Delta step records the study reveal in the training store while withholding
  the full model bridge until after the learner's own-words repair.
- Session logs now include a `product_loop` contract summary so each run records
  the science assumption under test.

Science rationale:

- A repair rep should start after a visible gap and ask for a small causal
  reconstruction, not ask the learner to paraphrase an already revealed answer.
- Self-explanation is useful when the learner generates the missing relation;
  answer-key preview turns the move into recognition.
- Corrective feedback stays targeted to the gap, then the model bridge gives
  comparison material after generation.
- This preserves the current training-store contract: repair happens after
  study reveal, while the answer-key bridge is withheld until after repair.

Product boundary:

- Delta cues are routing/scaffolding, not evidence.
- Own-words repair is useful practice, not graph truth.
- The model bridge is study reveal, not evidence of understanding.
- Study, repair, and pressure-checks do not produce `solidified`.
- Only spaced strong reconstruction can produce `solidified`.

### 2026-05-26: Persona Run Feedback

Run evidence:

- Prompt: `.qa-runs/socratink-tui-persona-prompt.md`
- Transcript: `.qa-runs/socratink-tui-user-try/2026-05-26T18-12-33Z/session.json`
- Persona output: `.qa-runs/personas/persona-20260526-131452.txt`

High-signal feedback:

- The Delta diagnostic is the sharpest part. The persona valued that Socratink
  named the structural gap: the learner named the actor but not the action.
- The current loop can feel like "guess the magic words" when it repeats
  "what do they do?" without giving a more structural scaffold.
- The current AI response style is too tutor-ish for founder dogfood. Cut
  praise preambles like "You're right..." and state the gap more directly.
- The own-words repair gate should challenge circular repairs before revealing
  the model bridge. If the learner writes "memory cells preserve the faster
  response," the system should say that is circular and ask for the mechanism.
- When the learner is stuck, the next experiment should show a small causal
  slot scaffold, not a broad paragraph:

```text
[Vaccine exposure] -> [Memory cells created] -> [ ??? ] -> [Rapid secondary response]
```

Candidate next product experiment:

- Add a `Mechanism Slot` repair step after Delta. It asks the learner to fill
  one missing causal action. If the repair is circular, push back once before
  revealing the model bridge. This should remain graph-neutral and must not
  produce `solidified`.

### 2026-05-26: Mechanism Slot Delta

Trigger:

- In a live neuroplasticity run, the Delta correctly identified the
  myelination-versus-synapse-strength confusion, but the repair target was too
  vague. The learner reasonably asked, "how do i know what to repair?"

What changed:

- Delta now asks the Python LLM bridge for a concrete `RepairScaffold`.
- The TUI prints a visible mechanism slot:

```text
Mechanism slot:
  Before: ...
  Missing: ...
  After: ...
```

- The repair prompt now says `Fill the missing link` instead of `Say that link
  in your own words`.

Product boundary:

- The slot should expose the shape of the missing causal relation, not write the
  answer for the learner.
- The slot remains graph-neutral. It records study reveal for the existing
  training-store contract, but does not produce `solidified`.

Run evidence:

- Script: `.qa-runs/neuroplasticity-tui-script.json`
- Log:
  `.qa-runs/socratink-tui-neuroplasticity-slot/2026-05-26T18-49-33Z/session.json`
- The new Delta was clearer:

```text
Mechanism slot:
  Before: Repeated activity between neurons...
  Missing: ...causes the effectiveness of their connection to...
  After: ...which impacts how signals are transmitted and stored.
```

- Final state stayed `primed` because the re-drill covered synaptic
  strengthening but not weakening. That is strict graph truth, but future UX
  should make bidirectional targets visible when the answer key requires both
  strengthen and weaken.

### 2026-05-26: Context Window Loop Run

Run evidence:

- Log:
  `.qa-runs/socratink-tui-together/2026-05-26T19-03-50Z/session.json`
- Concept: `context windows as it relates to AI`
- First node: `Context window as an AI's processing boundary`
- Final evaluator classification: `solid`
- Final derived state: `primed`

Product signal:

- The run exposed a mismatch between evaluator feedback and derivation. The
  evaluator said the spaced re-drill was solid, but the training derivation
  stayed `primed` because the cold attempt was not also strong. This is
  graph-truth conservative, but it reads confusingly in the TUI because the user
  sees a clear response and still does not get `solidified`.
- The model bridge over-focused on generic token-buffer mechanics and did not
  preserve the learner goal: context as an agent's attention substrate for
  bottleneck selection, not learner evidence.
- The route target was coherent but too narrow for the expressed product-lab
  purpose. It tested "what is a context window?" more than "how does context
  help an agent identify the one causal link?"

Candidate next experiment:

- When a first attempt is partial, a later spaced `solid` answer should either
  (a) explain why one more spaced strong attempt is required by graph truth, or
  (b) intentionally allow repaired-then-spaced strong reconstruction to
  solidify. Do not leave the user with "solid answer" copy plus `primed` state
  without explanation.

### 2026-05-26: Evidence Hold Minimum Fix

System design:

- Keep the training derivation as the source of graph truth.
- Treat the evaluator classification as an input signal, not the state engine.
- When evaluator and derivation appear to disagree, explain the boundary instead
  of silently overriding either layer.

What changed:

- If a spaced re-drill is classified `solid` but derived state is not
  `solidified`, the TUI now prints `[Evidence Hold]`.
- The session log now writes `evidence_holds[]` with the event, held state, and
  reason.
- The minimum fix preserves graph truth while removing the confusing hidden
  mismatch.

Example:

```text
[Evidence] primed
[Evidence Hold] The spaced answer was solid, but this node remains primed
because the first attempt was not strong. Current derivation requires two strong
reconstructions separated by spacing before solidified.
```

Open product question:

- The deeper design decision remains unresolved: should repaired-then-spaced
  strong reconstruction be enough to solidify, or does Socratink intentionally
  require two spaced/strong proof events after an initially weak cold attempt?

### 2026-05-26: Retrieval Practice Loop Run

Run evidence:

- Log:
  `.qa-runs/socratink-tui-together/2026-05-26T19-11-10Z/session.json`
- Concept: `retrieval practice with corrective feedback`
- First node: `Gap exposure through retrieval`
- Cold classification: `solid`
- Final state: `solidified`

Remarkable insight:

- The route was excellent: it selected the product's core mechanism, "retrieval
  exposes the gap."
- The cold attempt was already `solid`, but the TUI still forced Delta,
  own-words repair, model bridge, and pressure-check. That made the loop feel
  ceremonial instead of adaptive.
- The current derivation says `primed -> study` after any first attempt,
  including a strong one. Product-wise, strong cold attempts should not skip
  spacing, but they probably should skip repair unless the agent can pose a
  harder transfer or edge-case prompt.

Candidate minimum system fix:

- Add a `strong_cold_path` in the TUI: if cold classification is `solid`, show
  a compact confirmation, skip Delta/Repair/Model Bridge by default, and move
  to spacing or a harder transfer check. This preserves graph truth because
  `solidified` still requires spaced reconstruction, but removes fake repair.

### 2026-05-26: Strong Cold Path Minimum Fix

What changed:

- The TUI now branches when the cold attempt evaluator returns `solid`.
- The branch emits a graph-neutral `strong_cold_path` event.
- Delta, Own-Words Repair, Model Bridge, and Pressure-check are skipped for
  that node.
- The node still does not become `solidified` at cold attempt time. It only
  reaches `solidified` after a later spaced reconstruction is also classified
  strong by the existing training derivation.

Why it matters:

- A strong cold reconstruction means the immediate bottleneck was already
  reconstructed. Forcing a repair in that case made the loop ceremonial.
- The product move is not "trust the judge." The judge only routes the next
  move; the training store plus derivation still decide graph truth.
- This keeps the TUI adaptive without weakening Generation Before Recognition
  or the Evidence Weighted Map contract.

Run evidence:

- Portable trace:
  `scripts/socratink_tui/learning_cases/traces/strong-cold-skips-repair-until-spacing-2026-05-26/session.json`
- Regression case:
  `strong-cold-skips-repair-until-spacing-2026-05-26`
- Harness assertion: no `study_reveal`, `repair`, `repair_abandoned`,
  `model_bridge`, or `gap_drill` events occur before spacing in the strong-cold
  path.

### 2026-05-26: Gap Log Before Socratic Repair

Trigger:

- In a live agentic-engineering run, the Delta step exposed too much of the
  answer shape. The repair then felt like recognition/paraphrase instead of
  generation.

What changed:

- Delta now logs `gap_identified` instead of surfacing a learner-facing
  `study_reveal` event.
- The visible Delta prints `Gap logged`, then only the boundary:
  `Before`, `Missing operation`, and `After`.
- A separate `[Socratic Repair Drill]` begins with one narrow question such as
  `What must happen to ... before ...?`
- The Model Bridge remains hidden until after an own-words repair.

Product boundary:

- `gap_identified` is product/routing state, not evidence.
- The Socratic question should force the learner to generate the missing
  operation. It must not complete the causal chain.
- The training store still uses `study_revealed_at` internally to preserve the
  existing `appendRepair` contract, but the visible product event is gap
  identification, not recognition material.

### 2026-05-26: Hidden Bloom Drill Shape

What changed:

- Captured the hidden Bloom drill-shape rationale; the standalone spec file was later pruned after the behavior landed.
- Added hidden `internal_bloom_lens` metadata to `gap_identified`.
- Kept Bloom labels out of learner-facing TUI output.
- Added deterministic rejection for answer-shaped repair scaffolds before they
  can be printed.
- Pressure-check prompts now reference the logged missing operation instead of
  broadening back to the whole concept.

Product boundary:

- Bloom is routing context, not evidence.
- The lens is selected from the observed gap and phase. Learner goal may shape
  relevance, but cannot pull the prompt away from the bottleneck.
- Vocabulary gaps still require causal use; term recall alone is not repair.
- The existing `study_revealed_at` write remains compatibility state only, not
  visible study/progress/evidence.

Validation evidence:

- `tests/test_socratink_tui.py` now asserts no visible Bloom labels, hidden
  lens in session logs, leak rejection, and pressure-check containment.
- Portable traces were regenerated under
  `scripts/socratink_tui/learning_cases/traces/`.

### 2026-05-26: DeepSeek R1 Local Critique

Run evidence:

- Local helper: `/Users/jondev/bin/deepseek-local`
- Required env: `OLLAMA_HOST=http://127.0.0.1:11434`
- Model check: `ok: deepseek-r1:14b at http://127.0.0.1:11434`

Advisory findings:

- Hidden Bloom routing needs alignment checks, or it can quietly choose the
  wrong drill shape.
- One Socratic repair question may be too rigid when the learner has multiple
  linked gaps.
- Pressure-checks tied only to the logged missing operation may miss deeper
  implicit misunderstandings.
- The system needs feedback on whether `internal_bloom_lens` actually matched
  the learner's need.

Discarded/muddled finding:

- DeepSeek described a "model_bridge dependency on training-store derivation."
  That is not Socratink's contract. Model Bridge is comparison material after
  generation; training derivation owns graph truth.

Product implication:

- Treat local-model critique as a cheap red-team signal for the harness, not as
  evidence of learner understanding or product truth.

### 2026-05-26: DeepSeek Simulated Learner Attempt

Goal:

- Use local DeepSeek R1 as the simulated learner while the Socratink TUI
  administers the loop.

Attempted path:

- Checked local helper with
  `OLLAMA_HOST=http://127.0.0.1:11434 /Users/jondev/bin/deepseek-local --check`.
- Result: `ok: deepseek-r1:14b at http://127.0.0.1:11434`.
- Asked DeepSeek for an agentic-engineering learner launch attempt.
- First response was a question, not a generative attempt:
  `What are the core principles of agentic engineering?`
- Retried with a stricter learner-only prompt.
- DeepSeek produced a vague job-application-style launch attempt.
- Real TUI route generation failed with strict hidden-mechanism validation:
  `SmallestRouteCapExceeded: smallest route subnode 'c3_s1' sentence_starter copies hidden mechanism`.
- Retried with a more technical DeepSeek launch attempt.
- Real TUI route generation failed again:
  `SmallestRouteCapExceeded: smallest route subnode 'c1_s1' sentence_starter copies hidden mechanism`.
- Tried the fixture/fake LLM seam to keep the shell moving, but it generated the
  hardcoded immune-memory route, so the run was stopped as misleading.

Product findings:

- Local model simulated learners need output-shape guardrails because they may
  ask for recognition instead of generating a cold attempt.
- The real route generator needs a recoverable retry path when strict hidden
  mechanism validation fails.
- The fake route seam is useful for regression tests but not acceptable for
  topic-faithful simulated learner dogfood.

Next implementation target:

- Add route-generation retry/rewrite handling for
  `SmallestRouteCapExceeded`, then rerun the DeepSeek simulated learner flow
  on agentic engineering with the real route/evaluator seam.

### 2026-05-26: Founder Dashboard

What changed:

- Added `scripts/socratink-dashboard`.
- Added `scripts/socratink_tui/dashboard.mjs`.
- The dashboard summarizes the local harness state from tracked cases, portable
  traces, pedagogical agent contracts, and this notes file.

Founder-facing sections:

- Truth Contract
- Harness Cases
- Latest Portable Trace
- DeepSeek Simulated Learner
- Next Product Target
- Commands

Current dashboard finding:

- The next product target is route retry/rewrite handling for
  `SmallestRouteCapExceeded`, then rerunning the DeepSeek simulated learner
  flow.

Validation evidence:

- `scripts/socratink-dashboard --color=never`
- `.venv/bin/pytest tests/test_socratink_tui.py tests/test_cli_kernel_harness.py tests/test_training_store.py tests/test_training_derivation.py -q --tb=short`
- `bash scripts/doctor.sh`
- `git diff --check`

### 2026-05-26: Route Retry Implementation

What changed:

- Route generation now treats `SmallestRouteCapExceeded` as a recoverable
  generation failure in the TUI.
- The TUI logs a graph-neutral `route_retry` event and retries once with an
  explicit guardrail to regenerate learner scaffolds without copying hidden
  mechanism answer phrases.
- The Python bridge passes retry guidance into the existing
  `generate_smallest_provisional_map` seam instead of duplicating route
  generation or weakening validation.
- Session logs now include `route.retry_count` and `route.retry_reasons`.

Product boundary:

- This does not relax hidden-mechanism validation.
- A retry is not learner evidence.
- The learner sketch remains unchanged; retry guidance is generation guardrail
  context, not learner context.

Validation evidence:

- `test_tui_bridge_can_surface_retryable_route_validation_failure`
- `test_socratink_tui_retries_route_validation_failure_and_logs_recovery`

Next product target:

- Rerun the DeepSeek simulated learner against the real route/evaluator seam
  and promote any new failure into a replay case.

### 2026-05-26: DeepSeek Retry Rerun

Run evidence:

- Log:
  `.qa-runs/socratink-tui-deepseek-learner-retry/2026-05-26T21-43-43Z/session.json`
- Concept: `agentic engineering`
- Learner goal: `get a job applying agentic engineering`
- Route: `The Agent Loop Cycle`
- Final derived state: `primed`

What changed:

- The real route/evaluator seam completed the run after route retry
  implementation. The earlier validation crash did not recur in this run.
- The strong-cold path fired, so the TUI skipped ceremonial repair and moved to
  spacing.

Product findings:

- DeepSeek still behaves more like a tutor than a novice learner. It ignored
  the request for a concise incomplete cold attempt and generated a structured
  full-answer response.
- The spaced answer compressed the loop too much and omitted early sensing /
  perception detail, so the evaluator held the node at `primed`.
- The next harness target is simulated learner output-shape guardrails:
  detect question-asking, over-complete tutor answers, and answer formats that
  are not plausible learner attempts before feeding them into the TUI.

### 2026-05-26: Analogical Repair Questions

Trigger:

- In a live harness-engineering run, the repair question was too direct:
  `What must happen for an agent to receive input, process information, manage
  its internal state, and produce output?`

Product rule:

- Repair questions should prefer analogical pressure when the learner's current
  model is vague or low-resolution.
- Repair questions should use direct causal pressure when the learner is close
  but missing one operation.

Example:

```text
If a harness is like a flight recorder plus test track, what must it capture
and replay so we can tell whether the agent actually improved?
```

What changed:

- `RepairScaffold` now includes `question_style` as `direct` or `analogical`.
- The repair-scaffold prompt instructs the LLM to choose analogical questions
  for vague attempts and direct questions for near-miss attempts.
- The fake seam has a regression path for vague learner attempts.
- `gap_identified.gap_log.question_style` records the chosen style for product
  analysis without exposing pedagogy labels as learner-facing UI.

### 2026-05-26: Pedagogical Agent Contracts

What changed:

- Added `scripts/socratink_tui/pedagogical_agents/contracts.json`.
- Added `scripts/socratink_tui/pedagogical_agents/README.md`.
- Each TUI LLM/agent-like stage now logs its pedagogical agent contract:
  `agent`, `agent_id`, `job`, `required_outputs`, `may_propose_events`,
  `truth_permission`, and `failure_mode_to_guard`.

System design:

```text
Agents propose moves.
Training store records events.
Derivation decides truth.
Graph displays only derived evidence.
```

Minimum viable stance:

- These are contracts, not an external multi-agent runtime.
- The orchestrator remains deterministic code.
- Every subagent has `truth_permission: "none"` and `may_write_events: []`.
- The Evidence Judge classifies attempts but cannot mutate graph truth directly.

Why this matters:

- It makes the learning architecture inspectable without patching the browser
  UI or adding a framework.
- It creates a stable place to iterate on Route, Delta, Repair, Model Bridge,
  Re-Drill, and Evidence Judge responsibilities while preserving the real
  training-store/training-derive contract.

### 2026-05-26: Learning Cases Regression Harness

What changed:

- Added `scripts/socratink_tui/learning_cases/README.md`.
- Added `scripts/socratink_tui/learning_cases/schema.json`.
- Added the first `scripts/socratink_tui/learning_cases/cases.jsonl` entry.

First promoted case:

- `evidence-hold-solid-spaced-primed-2026-05-26`
- Type: `regression`
- Source: `regression_trace`
- Trace:
  `scripts/socratink_tui/learning_cases/traces/evidence-hold-solid-spaced-primed-2026-05-26/session.json`

Why it matters:

- This protects the boundary found during the context-window run: evaluator
  classification is an input signal, but training derivation owns graph truth.
- The case asserts event order, final derived state, spaced evaluator
  classification, and the requirement that an evidence hold exists.

Red-team guardrails applied:

- No golden cases yet.
- No agent prose or model bridge text is expected truth.
- Case truth can only reference event order and derived state from the saved
  training-store/training-derive trace.
- Research notes remain separate from regression gates.
- Promoted cases now point at portable traces under
  `scripts/socratink_tui/learning_cases/traces/` so replay does not depend on
  ignored `.qa-runs/` evidence.

### 2026-05-26: Repair Abandoned Gate

Trigger:

- In a live Socratink run, the learner entered `i am not sure.` at the
  Own-Words Repair step. The TUI still appended a repair and revealed the model
  bridge.

What changed:

- The TUI now detects conservative uncertainty strings such as `i am not sure`,
  `idk`, `i don't know`, `no idea`, and `unsure`.
- Uncertain repair text produces a graph-neutral `repair_abandoned` event.
- The TUI skips `store.appendRepair`, skips Model Bridge, skips pressure-check,
  skips spacing/re-drill, saves `session.json`, and stops.

Product boundary:

- Uncertainty is useful learner signal, but it is not repair evidence.
- Model Bridge reveals only after generation.
- The next product step is a micro-scaffold path, not answer reveal.

Smoke evidence:

- `.qa-runs/socratink-tui-repair-abandoned-smoke/2026-05-26T19-58-35Z/session.json`
- Portable trace:
  `scripts/socratink_tui/learning_cases/traces/repair-abandoned-no-model-bridge-2026-05-26/session.json`
- Regression case: `repair-abandoned-no-model-bridge-2026-05-26`

### 2026-05-26: Minimal Replay Harness

What changed:

- Added `scripts/socratink-harness`.
- Added `scripts/socratink_tui/harness/replay.mjs`.
- Added a regression test that runs `scripts/socratink-harness replay`.

Harness behavior:

```text
Socratink Harness
3 cases

PASS evidence-hold-solid-spaced-primed-2026-05-26
  event order ok
  final state: primed
  evaluator: solid
  evidence hold: present
  truth source: training_derivation
```

Scope:

- Replays saved traces only.
- Checks deterministic invariants only.
- Checks forbidden events and forbidden LLM stages as negative controls for
  graph-truth boundaries.
- Uses no LLM judge.
- Exits nonzero on failure.

### 2026-05-26: Agentic Engineering Completion Run

Run evidence:

- Script: `.qa-runs/agentic-engineering-tui-script.json`
- Successful log:
  `.qa-runs/socratink-tui-agentic-engineering/2026-05-26T18-21-22Z/session.json`
- Failed first attempt: route generation rejected a generated scaffold because
  `entry_prompt` copied the hidden mechanism.
- Successful first node: `Agent Task Execution and Reporting`
- Final state: `solidified`

What worked:

- The TUI can complete a source-less concept end to end on an abstract founder
  topic.
- The graph truth contract held: study reveal, repair, model bridge, and
  pressure-check stayed `primed`; only spaced re-drill produced `solidified`.
- The saved log is useful enough to audit event order, derived states, and the
  exact learner text that earned final evidence.

Brutal product read:

- Completion was too easy when the learner already gave a strong cold attempt.
  The Delta fallback became generic instead of naming a real missing link.
- The LLM voice is still too congratulatory. Founder dogfood should use less
  "That's a clear explanation!" and more direct evidence language.
- The route generator's strict validation is good for graph truth, but in a TUI
  it currently feels like a crash instead of a recoverable generation retry.
- The repair step is not yet adaptive. If the cold attempt is already strong,
  the product should either skip repair into spacing or ask a sharper transfer
  / edge-case repair, not force a ceremonial repair.
- `solidified` can be technically correct while still feeling shallow if the
  re-drill answer closely resembles the scripted cold attempt. Future runs need
  prompt variation that changes angle, not just elapsed time.
