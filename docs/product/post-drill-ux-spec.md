# socratink — Post-Drill UX Spec

## Agent Summary

> **What this document is**: The spec for what the learner sees after each phase of the three-phase node loop resolves. It governs panel copy, result-state visual treatment, sensory feedback, transcript visibility, tier/band trajectory display, and the handoff from drill mode back to graph navigation. This is the document you read before changing anything the learner sees after a cold attempt, study, re-drill, or session ending.
>
> **When to read it**: Before changing post-phase panel copy, result-state visuals, transcript policy, attribution framing on non-solid results, sensory celebration behavior, or session-ending UX.
>
> **What it is NOT**: It is not the routing/state implementation spec (read `progressive-disclosure.md`), the engineering invariants (read `../drill/engineering.md`), or the full UX philosophy (read `ux-framework.md`).
>
> **Key constraints an agent must follow**:
> - Five canonical result states: Primed, Solidified, Unresolved Exit, In-Progress, Session Complete. Each must look and feel distinct.
> - Cold attempts show NO score, NO classification, NO tier/band. Normalization message required.
> - Solidified gets the strongest sensory celebration, calibrated to cognitive load. Drilled gets NO celebration.
> - All non-solid copy uses wise feedback (strategy-focused, never ability-focused). No raw classifier labels in any learner-facing surface.
> - Side panel has six modes. Modes must be pure — no content bleed.

---

## Core Distinction

Post-phase UX must distinguish between three resolution types:

- cold attempt resolution (Phase 1 → primed)
- spaced re-drill with mastery (Phase 3 → solidified)
- spaced re-drill without mastery (Phase 3 → drilled)

These must look and feel completely different from each other. If the UI blurs these states, the graph stops telling the truth.

## Canonical Result States

### 1. Primed (Cold Attempt Complete)

Use when:

- Phase 1 cold attempt completes
- Node transitions from `locked` to `primed`

What it means:

- the learner entered the room
- the prediction error has been generated
- the study view is now unlocked
- no mastery has been assessed or claimed

Required visual treatment:

- node appears `primed` (warm, open, distinct from locked)
- side panel transitions to targeted study view automatically (after 2-3 second transition beat)
- the result framing emphasizes exploration, not evaluation
- no score, no tier/band, no performance metrics are shown
- a social normalization message should appear, rotated from variants

Required copy:

- headline: none — transition directly to study view
- normalization message (one of): "Your guess just primed your brain. Now let's see what's really going on." / "Most learners get this wrong the first time. That's by design." / "This is how your brain prepares to learn." / "That attempt just activated your semantic networks. The study material will land harder now."

Sensory treatment:

- subtle warm acknowledgment (brief animation on node state change)
- no celebration — this is entering a room, not clearing it

### 2. Solidified (Spaced Re-Drill Mastery)

Use when:

- Phase 3 spaced re-drill completes
- `routing === "NEXT"`
- `classification === "solid"`

What it means:

- the room is cleared
- the mechanism was reconstructed from long-term memory after genuine spacing
- downstream unlock checks may now re-evaluate

Required visual treatment:

- node appears `solidified`
- side panel headline says the room is cleared
- copy acknowledges genuine reconstruction — this is earned, not given
- result state remains visible until the learner presses `Continue`
- trajectory contrast is shown: "Your cold attempt: [band]. Your re-drill: [band]. That gap is real learning."

Required copy:

- headline: `Solidified`
- body: short, earned, non-generic acknowledgment
- trajectory contrast (if tier/band data available from both cold attempt and re-drill)
- wise feedback format: high standards acknowledged, specific achievement named

Sensory treatment:

- strongest celebration in the product — this is the line clear
- calibrated to cognitive load: a fluent, high-confidence solid gets a crisp, snapping animation; a heavily scaffolded, barely-solid gets a subdued, stabilizing effect. Both are truthful. The aesthetic mirrors the quality of the cognitive work.
- satisfying animation on the graph node
- brief confirmation sound (if audio enabled)
- haptic pulse timed to the moment of generation commit (if haptics enabled)
- moderate, not excessive — the inverted-U rule applies

### 3. Unresolved Exit (Spaced Re-Drill Without Mastery)

Use when:

- Phase 3 spaced re-drill completes
- `routing === "NEXT"`
- `classification !== "solid"`

What it means:

- the re-drill was genuine (spacing was valid)
- the room is still unresolved
- node should remain return-worthy, not shameful

Required visual treatment:

- node appears `drilled`
- side panel must explicitly say the room is not yet cleared
- panel should include one concise diagnosis framed as strategy data, not ability verdict
- result state remains visible until `Continue`

Required copy:

- headline: `Needs revisit`
- body: strategy-focused, not ability-focused. Use wise feedback: "This concept is designed to be challenging. The connection between [specific gap] needs a different angle. We know you can master it."
- include one specific next-step suggestion

Attribution framing (binding):

- frame the gap in terms of approach, never capacity
- good: "The causal link between step 2 and step 3 needs a different angle."
- bad: "You don't understand this concept."
- never use raw classifier labels (`deep`, `shallow`, `misconception`) as learner-facing badges

Sensory treatment:

- no celebration
- no consolation animation
- the sensory layer stays completely silent on unresolved outcomes
- the copy and framing handle the affect; the reward layer does not soften the signal

### 4. In-Progress Drill

Use when:

- `routing === "PROBE"` or `routing === "SCAFFOLD"` (during Phase 3 re-drill)

What it means:

- learner is still inside the room
- no graph mutation has happened

Required visual treatment:

- active drill context stays visible
- result framing must not appear yet
- node may be highlighted as the active room, but should not adopt result styling

### 5. Session Complete

Use when:

- `routing === "SESSION_COMPLETE"` or session guardrails trigger (time cap, node cap)

What it means:

- the session is ending
- no mastery is implied by session completion alone

Required visual treatment:

- session-ending card appears
- all node states reflect their current truthful status
- the ending should feel like a save point, not a punishment

Required copy:

- headline: `Session saved`
- body: "Progress locked in. Your brain consolidates during breaks. Spacing improves retention dramatically."
- if ending at engagement (not exhaustion): "You're building momentum. Come back tomorrow and this will be stronger."
- never end copy with a failure state or a diagnostic — end with forward-looking warmth

## Graph-State Meaning

The learner-facing graph should keep these meanings stable:

### `locked`

- unavailable
- low-information

### `primed`

- entered but not yet challenged
- study view available
- warm, open visual state

### `drilled`

- attempted but not solid
- unresolved stack pressure
- worth revisiting

### `solidified`

- cleared
- verified understanding from genuine long-term retrieval

## Side Panel Rules

The side panel should be mode-pure.

At any given moment it should be in one of these modes:

- inspect
- cold-attempt-active (Phase 1)
- study (Phase 2)
- re-drill-active (Phase 3)
- post-re-drill
- session-complete

The panel must not silently mix these modes.

### Inspect

- orientation only
- if `locked`: show label and prerequisite info
- if `primed`: show "Ready for re-drill" status and study view access
- if `drilled`: show revisit metadata and "Re-drill" affordance (if spacing met)
- if `solidified`: show cleared status and trajectory data

### Cold-Attempt-Active (Phase 1)

- one active target
- the AI's exploratory question is visible
- no mechanism text is shown
- no score or performance metrics
- transcript visible as conversation progresses

### Study (Phase 2)

- mechanism text for the attempted node is displayed
- anchored to the learner's cold attempt where possible
- normalization message visible
- no drill affordance for this node until spacing is satisfied
- the system may recommend the next cold attempt on a different node

### Re-Drill-Active (Phase 3)

- one active target
- transcript visible
- no result headline until routing resolves
- the AI demands multi-step causal reconstruction

### Post-Re-Drill

- result headline visible (Solidified or Needs Revisit)
- chat input hidden
- result remains sticky until `Continue`
- trajectory contrast visible (if tier/band data available)
- graph clicks should not silently collapse the result state

### Session-Complete

- session-ending card visible
- all node states reflect truthful status
- forward-looking copy
- no drill affordance until next session

## Transcript Policy

MVP-safe rule:

- unresolved and solid results may keep the transcript visible below the result card
- the result card must dominate the top of the panel

Recommended refinement:

- collapse the prior transcript behind a `Review attempt` affordance in post-re-drill mode

## Learner-Facing Labels

Do not expose raw backend terms like:

- `deep`
- `shallow`
- `gap: deep`
- `misconception`

Prefer translated labels framed as strategy guidance:

- `Needs revisit`
- `The causal link needs a different angle`
- `Needs a fuller mechanism`
- `One step needs correction`

## Tier/Band Display

The tier/band system (`spark → link → chain → clear → tetris`) is surfaced as trajectory contrast, not as a live score.

Rules:

- never show tier/band during an active drill attempt
- show trajectory only after a re-drill resolves: "Your cold attempt: spark. Your re-drill: chain. That gap is real learning."
- always pair with interpretive framing — raw numbers without meaning frames show null or negative effects

## Continue Behavior

`Continue` should mean:

- close the resolved session state
- return the panel to normal graph navigation
- preserve the truthful graph node state
- the system may now recommend the next interleaving step

It should not:

- silently start another node
- auto-hide the result before the learner sees it
- imply a recommended route unless a separate traversal cue exists

## Anti-Patterns

Do not ship:

- a cold-attempt result screen that shows a score or classification
- a resolved-session screen that looks identical for `solidified` and `drilled`
- a `drilled` node that reads like completion
- a `primed` node that reads like failure
- a graph click that silently erases the result state before `Continue`
- a post-re-drill panel dominated by transcript rather than outcome
- classifier jargon exposed as if it were a user-facing pedagogy model
- celebration or consolation animation on unresolved outcomes
- ability-framed copy on any non-solid result
- session endings that highlight what wasn't accomplished

## Current Decision Record

As of 2026-04-05:

- four-state model: `locked` → `primed` → `drilled` → `solidified`
- cold attempts are explicitly unscored
- spaced re-drill is the only phase that can produce `solidified`
- post-re-drill results stay sticky until `Continue`
- unresolved exits use strategy-focused wise feedback, never ability verdicts
- social normalization messages appear after every cold attempt
- trajectory contrast (tier/band) shown after re-drill, not during
- sensory celebration is success-dependent and calibrated to cognitive load
- session endings framed as save points with transparent learning science

## Next UX Slice

When bandwidth allows:

1. keep the result card at the top of post-re-drill
2. collapse old transcript content behind a `Review attempt` reveal
3. add trajectory contrast display with interpretive framing
4. add a single `Re-drill later` cue on unresolved nodes without implying failure
5. implement social normalization message rotation on cold attempt completion
6. add session-ending copy that explains spacing science
7. implement cognitive-load-calibrated sensory celebration (crisp vs subdued solidification)
