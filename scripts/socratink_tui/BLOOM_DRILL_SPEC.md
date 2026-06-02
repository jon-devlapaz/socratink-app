# Bloom-Guided Drill Shape Spec

Status: draft for TUI product lab
Date: 2026-05-26
Scope: source-less Socratink TUI and replay harness

## Thesis

Bloom taxonomy is useful only as an internal drill-shape grammar. It should not
appear in learner-facing copy.

Socratink should use Bloom to choose the kind of cognitive pressure a logged
gap needs, then display plain reconstruction prompts that keep the learner
focused on the smallest missing operation.

The lens is selected after the cold attempt from the observed gap and current
phase. The learner goal may shape the scenario or relevance, but must not pull
the drill away from the bottleneck.

## Product Rule

Socratink diagnoses the bottleneck, logs the gap, then asks the smallest
question that forces the learner to generate the missing operation.

The learner should see:

```text
[Delta]
Gap logged: ...
  Before: ...
  Missing operation: ...
  After: ...

[Socratic Repair Drill]
What must happen to ... before ...?
```

The learner should not see:

```text
Bloom level: Analyze
This is an application drill.
Now evaluate your metacognitive gap.
```

## Truth Boundary

Bloom metadata is routing context, not evidence.

- `learner_goal` may shape relevance and transfer pressure.
- `gap_identified` logs product/routing state.
- `repair` is graph-neutral practice under the current training-store contract.
- `model_bridge` is comparison material after generation.
- `gap_drill` / pressure-check is graph-neutral.
- Only spaced strong reconstruction can derive `solidified`.

Agents may propose Bloom-shaped moves. Training store records events. Derivation
decides truth. Graph displays only derived evidence.

## Internal Drill Grammar

| Internal Bloom Lens | Learner-Facing Move | Best Use | Forbidden Use |
|---|---|---|---|
| Remember | Use the term in the link | Missing vocabulary prerequisite | Treat naming as understanding |
| Understand | Explain how | Default causal reconstruction | Accept vague paraphrase |
| Apply | Use it here | Transfer to a nearby case | Drift away from the logged gap |
| Analyze | Find why this fails | Repair misconception or missing operation | Reveal the full mechanism before repair |
| Evaluate | Judge if this works | Later re-drill or founder/job transfer | Grade before generation |
| Create | Design a loop | Advanced transfer after mechanism is stable | Replace evidence with project enthusiasm |

The TUI may log the internal lens for product research, but should not show the
taxonomy label to the learner.

If vocabulary is the bottleneck, the repair still requires a causal relation.
Do not accept term recall as repair.

Good:

```text
Use "feedback loop" to explain why the next agent action changes.
```

Bad:

```text
What is the name of this process?
```

## Gap Logging Contract

`gap_identified` should store:

```json
{
  "type": "gap_identified",
  "surface": "delta",
  "graph_neutral": true,
  "gap_log": {
    "before": "what the learner already generated",
    "missing_operation": "short functional label, not answer prose",
    "after": "what the operation must connect to",
    "internal_bloom_lens": "understand|apply|analyze|evaluate|create"
  },
  "prompt": "one Socratic question"
}
```

The `missing_operation` should name the role of the gap, not complete the chain.
The visible `Before / Missing operation / After` fields must pass a leakage
check before printing. They may expose the boundary of the gap; they must not
complete the hidden mechanism.

Good:

```text
Missing operation: using the result
```

Too answer-shaped:

```text
Missing operation: observation and reflection
```

Bad:

```text
Missing operation: observe the tool result, compare it to the goal, update
context, refine the plan, and choose the next action
```

Deterministic leak checks should reject or retry scaffolds when:

- `missing_operation` contains an action chain instead of a short functional
  label;
- `before`, `missing_operation`, and `after` together paraphrase the answer key;
- the Socratic question includes the answer steps;
- the learner could pass by repeating the scaffold without adding a generated
  operation.

## Training-Store Compatibility Trap

The current TUI may set `study_revealed_at` internally at `gap_identified`
because `appendRepair` requires study reveal in the existing training-store
contract.

This is compatibility state, not product truth.

No renderer, analytics surface, harness report, or future TUI branch may treat
that timestamp as:

- the learner studied the answer;
- the learner made progress;
- the learner gained evidence;
- the node is closer to mastery.

The visible event remains `gap_identified` until the Model Bridge is actually
shown after generation.

## Socratic Repair Drill Contract

The Socratic repair question must:

- start from the logged gap,
- ask for one missing operation,
- use analogical pressure when the learner's current model is vague or
  low-resolution,
- use direct causal pressure when the learner is close but missing one
  operation,
- avoid answer lists,
- avoid praise,
- avoid Bloom labels,
- preserve the model bridge until after own-words repair.

## Inner Repair Dialogue Contract

The Socratic repair drill is a bounded dialogue, not a single ceremonial text
box. It stays on one `gap_id` and one `missing_operation` until the learner
reconstructs:

```text
before state -> missing operation -> after state
```

Each `repair_dialogue_turn` must be graph-neutral and `score_eligible=false`.
It may route the next prompt, but it must not append training attempts or derive
mastery. The bridge-readiness judge records:

- `support_level`
- `causal_link_present`
- `missing_operation_addressed`
- `echo_risk`
- `bridge_ready`
- `next_dialogue_action`
- `not_mastery_reason`

Only a bridge-ready own-words turn can be committed as `repair`. If the learner
loops, echoes, or gives uncertainty through the bounded turn budget, the session
exits as `repair_abandoned` / `unresolved_gap` without Model Bridge.

Good:

```text
What must happen to the tool result before the agent can choose the next action?
```

Too broad:

```text
What are all the stages of an agentic loop?
```

Too revealing:

```text
How does the agent observe, reflect, update context, and refine the plan?
```

Analogical for vague models:

```text
If a harness is like a flight recorder plus test track, what must it capture
and replay so we can tell whether the agent actually improved?
```

## Post-Bridge Transfer Check Contract

The post-bridge transfer check is not the inner drill. It happens only after
Model Bridge and should usually be `Apply` or `Analyze`, but only against the
logged gap.

For the agentic engineering run:

Logged gap:

```text
The learner named tool calls and self-prompting, but did not explain how the
tool result changes the next action.
```

Good post-bridge transfer check:

```text
Why would an agent that calls tools but never inspects results fail?
```

Bad post-bridge transfer check:

```text
List every stage in the complete agentic loop.
```

Post-bridge transfer output may inform the next prompt, but must not mutate
graph truth or produce `solidified`.

## Spaced Re-Drill Contract

Spaced re-drill should vary pressure based on the logged gap, current phase,
learner goal, and internal Bloom lens, in that order:

- job-readiness goal: favor `Apply`, `Evaluate`, or `Create` only after the
  missing operation has been repaired;
- fragile mechanism: favor `Understand` or `Analyze`;
- prior strong cold path: skip repair and use spaced reconstruction;
- prior repair-abandon: return to Socratic repair or micro-scaffold, not model
  bridge.

Even when the evaluator says `solid`, derivation may hold the node at `primed`
if the training record does not satisfy the evidence contract. The TUI must
explain that hold.

## Required Acceptance Tests

Do not implement Bloom routing until the TUI/harness proves:

- no learner-facing output contains `Bloom`, `taxonomy`, `remember`,
  `understand`, `apply`, `analyze`, `evaluate`, or `create` as rubric labels;
- `gap_identified` contains `internal_bloom_lens` only in the session log;
- answer-shaped scaffolds are rejected or retried before being printed;
- `gap_identified`, `repair`, `model_bridge`, and `gap_drill` never produce
  `solidified`;
- model bridge is forbidden after `repair_abandoned`;
- pressure-check prompt references the logged missing operation;
- strong cold reconstruction skips repair but still waits for spaced proof;
- replay cases assert event order, forbidden events, and derived state rather
  than agent prose.

## Open Design Questions

1. Should `internal_bloom_lens` be selected by the Delta Agent and verified by
   deterministic orchestrator policy, or selected entirely by the orchestrator?
2. What deterministic leak-check threshold catches answer-shaped scaffolds
   without blocking useful gap boundaries?
3. Should a shallow pressure-check ever ask for the whole loop, or should it
   always stay inside the logged gap?
4. Should repaired-then-spaced solid reconstruction ever be enough for
   `solidified`, or should the current two-strong-attempt derivation remain
   strict?

## Steelman Findings Incorporated

Subagent red-team review found five breakage risks, now reflected above:

- visible gap fields can become answer reveal unless leak-checked;
- `study_revealed_at` can be misread as study/progress/evidence;
- Bloom can pull prompts away from the logged bottleneck;
- vocabulary drills can collapse into recognition;
- acceptance tests must gate implementation, not trail it.
