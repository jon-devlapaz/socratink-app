# Repair Reps — Unified Implementation Spec

This document consolidates the implementation spec for Repair Reps, governing focused layout, card-stack animations, and self-rating behavior.

---

# Socratink - Repair Reps Focused Mode Spec

## Agent Summary

> **What this document is**: This spec governs the focused workbench presentation for Repair Reps: the graph/detail layout while `interactionMode === "repair-reps"`, the context strip, the input/reveal copy contract, the reference-bridge comparison cue, and the completion copy. This is the document you read before changing Repair Reps focused layout or learner-facing Repair Reps copy.
>
> **When to read it**:
> - Before changing `repairRepsMarkupForNode()` in `public/js/graph-view.js`.
> - Before changing `.graph-layout.mode-repair-reps`, `.graph-detail.is-repair-reps`, or `.graph-repair-*` layout rules in `public/css/layout.css`.
> - Before changing the visible wording around "Your bridge", "Reference bridge", or Repair Reps completion.
>
> **What it is NOT**: This does not own the Repair Reps backend generation contract in `main.py` or `ai_service.py`. It does not own the card-stack animation vocabulary already specified in `docs/product/repair-reps-card-stack-spec.md`. It does not own the self-rating semantics or stored rating evidence already specified in `docs/product/repair-reps-self-rating-spec.md`. It does not govern the full three-phase graph progression contract in `docs/product/progressive-disclosure.md`.
>
> **Key constraints**:
> - Repair Reps must not call `patchActiveConceptDrillOutcome()`, `recordInterleavingEvent()`, or `markNodeVisitedThisSession()`.
> - Repair Reps must not mutate `drill_status`, `drill_phase`, `study_completed_at`, `re_drill_eligible_after`, `gap_type`, or `gap_description`.
> - The reference bridge must render only after the learner has typed an answer and clicked the reveal control.
> - The focused layout must use the existing `.mode-repair-reps` and `.is-repair-reps` hooks from `syncInteractionChrome()`.
> - Graph interactivity during focused Repair Reps must be controlled by CSS class state, not by JS `pointerEvents` mutation.
> - Copy must avoid score, correct, mastered, streak, win, or celebration language.

---

## Motivation

Repair Reps currently works as a truthful auxiliary practice lane, but the side-panel layout and placeholder copy make it feel like a form attached to the graph. Focused Repair Mode turns it into a temporary causal workbench: the learner generates a bridge, reveals a reference bridge, self-rates the structural match, and returns to the graph without implying graph progress.

---

## Assumptions

- The implementation can use the existing `syncInteractionChrome()` mode hooks: `.graph-layout.mode-repair-reps` and `.graph-detail.is-repair-reps`.
- The focused layout should de-emphasize the graph with CSS only. If dimming still leaves too much split attention, implementation may collapse the graph column more aggressively while preserving the context strip.
- The existing `feedback_cue` response field remains in the API payload but is not rendered as primary learner guidance in focused mode.
- No high-risk confirmation assumptions are present. This spec does not add new states, endpoints, storage keys, or backend behavior.

---

## Behavior

### Primary Flow

1. The learner starts Repair Reps from an eligible `primed/re_drill` or `drilled` node.
2. The graph enters focused repair mode using the existing `repair-reps` interaction mode. The graph is visually de-emphasized and non-interactive, while the Repair Reps workbench becomes the primary surface.
3. A quiet context strip appears above the rep card:
   `Node label - Repair Rep 1 of 3 - Practice only`
4. The learner sees the rep prompt, a persistent `Your bridge` label, an empty textarea, and the helper:
   `Trace the causal link in one or two sentences.`
5. The reveal control is visible but disabled until the learner types a non-empty answer:
   `Show reference bridge`
6. When the learner reveals, their answer remains visible and readonly. A `Reference bridge` panel unfolds below it with:
   `Compare the link, not the wording.`
7. The learner selects one self-rating and advances to the next rep. The card-stack transition remains restrained and non-celebratory.
8. On completion, the learner sees `Practice logged`, the self-rating breakdown, and:
   `These reps are saved. Graph progress comes from the next re-drill.`
9. The learner clicks `Back to graph`. `exitRepairReps()` restores normal graph interaction and the node state remains unchanged.

### Edge Cases

- **Loading state**: While reps load, show the context strip as `Node label - Repair Reps - Practice only` and keep the graph de-emphasized.
- **Error state**: If reps fail to load, show the existing error copy and an exit/reopen path. Exiting must restore normal graph interactivity through class removal, not JS pointer overrides.
- **Empty answer**: `revealRepairRep()` continues to no-op when the trimmed answer is empty. The textarea remains empty and no reference bridge appears.
- **Reduced motion**: All card and reveal animations remain suppressed under `prefers-reduced-motion: reduce`.
- **Mobile layout**: Repair Reps must place the workbench before the graph or hide/de-emphasize the graph enough that the textarea is not pushed below a large graph surface.
- **Old repair evidence**: Existing `learnops_repair_reps_v1` records without ratings or newer copy fields remain readable because this feature changes rendering only.

---

## Invariant Boundary

This feature must NOT:

- Call or modify `patchActiveConceptDrillOutcome()` in `public/js/app.js`, because Repair Reps is not a scored drill outcome.
- Call or modify `recordInterleavingEvent()` in `public/js/app.js`, because Repair Reps never counts as interleaving.
- Call or modify `markNodeVisitedThisSession()` in `public/js/app.js`, because Repair Reps must not count toward node/session progression.
- Call `completeStudy()` when launching or completing Repair Reps, because study completion remains the study flow's job.
- Change `isRepairRepsEligible()` to include `locked`, `solidified`, or `primed/study` nodes.
- Mutate `concept.graphData`, `drill_status`, `drill_phase`, `study_completed_at`, `re_drill_eligible_after`, `gap_type`, or `gap_description`.
- Change `/api/repair-reps`, `RepairRepsRequest`, `generate_repair_reps()`, or `app_prompts/repair-reps-system-v1.md`; this is a frontend rendering/layout pass.
- Add JS code that manually sets `element.style.pointerEvents` for the graph stage. Graph pointer behavior must follow `.graph-layout.mode-repair-reps` CSS so exit paths restore automatically.

---

## State Changes

### New or Modified State

None - this feature uses existing state:

```
interactionMode: string = "repair-reps" - existing graph interaction mode that produces .mode-repair-reps and .is-repair-reps classes.
repairRepsState.status: "loading" | "ready" | "error" | "complete" - existing transient UI state.
repairRepsState.currentIndex: number = 0 - existing rep index for context strip copy.
repairRepsState.revealed: boolean = false - existing reveal gate for Generation Before Recognition.
repairRepsState.currentAnswer: string = "" - existing transient typed answer that survives reveal.
repairRepsState.isDealing: boolean = false - existing card-stack transition flag.
repairRepsState.isRevealing: boolean = false - existing reveal transition flag.
repairRepsState.ratings: Array<"close_match"|"partial"|"missed"> = [] - existing self-rating evidence.
repairRepsState.ratingSelected: boolean = false - existing advance gate.
```

### New or Modified Functions

**`repairRepsMarkupForNode(data, repairState = {})`** in `public/js/graph-view.js`:
Modify markup and copy for loading, ready, revealed, error, and complete states. It continues to read existing `repairRepsState` through `options.repairRepsState`.

**`repairRatingMarkup(state, currentIndex)`** in `public/js/graph-view.js`:
May keep the same labels and event hooks, but CSS may present the buttons as compact neutral chips.

**`repairContextStripMarkup(state, nodeLabel, currentIndex, total)`** in `public/js/graph-view.js`:
New optional helper. If added, it should return only static context strip markup and must not mutate state.

### Storage Schema

None - this feature has no new persistent storage.

Existing Repair Reps evidence under `learnops_repair_reps_v1` remains unchanged:

```json
{
  "concept_id::node_id": [
    {
      "completed_at": "ISO timestamp",
      "rep_count": 3,
      "prompt_version": "repair-reps-system-v1",
      "gap_type": "string|null",
      "answer_lengths": [0, 0, 0],
      "ratings": ["close_match", "partial", "missed"]
    }
  ]
}
```

---

## API Changes

None - this feature does not change API routes, request models, response models, auth, prompt files, or AI generation behavior.

---

## Markup / UI

### Repair Reps - Loading State

**Produced by**: `repairRepsMarkupForNode()` in `public/js/graph-view.js`

```html
<div class="graph-repair-context-strip">
  <span>Node label</span>
  <span>Repair Reps</span>
  <span>Practice only</span>
</div>
<section class="graph-detail-surface graph-repair-card">
  <div class="graph-detail-kicker">Repair Reps</div>
  <div class="graph-repair-progress" aria-label="Repair Reps progress">...</div>
  <h3 class="graph-detail-title">Node label</h3>
  <p class="graph-detail-copy">Building three causal reps for this node. This is practice, not mastery credit.</p>
</section>
```

### Repair Reps - Ready Before Reveal

**Produced by**: `repairRepsMarkupForNode()` in `public/js/graph-view.js`

```html
<div class="graph-repair-context-strip">
  <span>Node label</span>
  <span>Repair Rep 1 of 3</span>
  <span>Practice only</span>
</div>
<div class="graph-study-shell graph-repair-shell">
  <section class="graph-detail-surface graph-repair-card is-dealing">
    <div class="graph-detail-kicker">Repair Rep 1 of 3</div>
    <div class="graph-repair-progress" aria-label="Repair Reps progress">...</div>
    <h3 class="graph-detail-title">Node label</h3>
    <p class="graph-detail-copy">Rep prompt</p>
    <div class="graph-detail-kicker">Your bridge</div>
    <textarea class="graph-repair-input" rows="4"></textarea>
    <p class="graph-detail-copy graph-repair-helper">Trace the causal link in one or two sentences.</p>
  </section>
  <section class="graph-detail-surface graph-study-next graph-repair-next">
    <p class="graph-detail-copy graph-repair-truth-line">Practice only. Graph progress comes from re-drill.</p>
    <button class="btn-start-drill graph-detail-action trigger-repair-reveal" disabled>Show reference bridge</button>
  </section>
</div>
```

The textarea must not have a placeholder. The helper text stays visible while the learner types.

### Repair Reps - Revealed State

**Produced by**: `repairRepsMarkupForNode()` in `public/js/graph-view.js`

```html
<section class="graph-detail-surface graph-repair-card">
  <div class="graph-detail-kicker">Repair Rep 1 of 3</div>
  <div class="graph-repair-progress" aria-label="Repair Reps progress">...</div>
  <h3 class="graph-detail-title">Node label</h3>
  <p class="graph-detail-copy">Rep prompt</p>
  <div class="graph-detail-kicker">Your bridge</div>
  <textarea class="graph-repair-input" rows="4" readonly>Learner answer</textarea>
  <div class="graph-repair-bridge is-revealing">
    <div class="graph-detail-kicker">Reference bridge</div>
    <p class="graph-detail-copy">Reference bridge text</p>
    <p class="graph-detail-copy graph-repair-compare-cue">Compare the link, not the wording.</p>
  </div>
  <div class="graph-repair-rating">
    <div class="graph-detail-kicker">How close was your bridge?</div>
    <div class="graph-repair-rating-group">...</div>
  </div>
</section>
```

Do not render `rep.feedback_cue` as primary visible copy in this state. The static comparison cue is the primary instruction.

### Repair Reps - Complete State

**Produced by**: `repairRepsMarkupForNode()` in `public/js/graph-view.js`

```html
<div class="graph-repair-context-strip">
  <span>Node label</span>
  <span>Repair Reps complete</span>
  <span>Practice only</span>
</div>
<div class="graph-repair-complete">
  <div class="graph-detail-kicker">Repair Reps</div>
  <div class="graph-repair-progress" aria-label="Repair Reps progress">...</div>
  <h3 class="graph-detail-title">Practice logged</h3>
  <div class="graph-repair-summary">...</div>
  <p class="graph-detail-copy">These reps are saved. Graph progress comes from the next re-drill.</p>
  <button class="btn-start-drill graph-detail-action trigger-repair-exit">Back to graph</button>
</div>
```

### Event Listeners

No new event listeners are required. Existing listeners remain:

| Selector | Event | Handler | Bound in |
|----------|-------|---------|----------|
| `.trigger-repair-reveal` | `click` | `window.SocratinkApp?.revealRepairRep?.(answer)` | `renderCurrentDetail()` in `public/js/graph-view.js` |
| `.graph-repair-input` | `input` | Enable `.trigger-repair-reveal` only when trimmed input is non-empty | `renderCurrentDetail()` in `public/js/graph-view.js` |
| `.trigger-repair-rate` | `click` | `window.SocratinkApp?.rateRepairRep?.(btn.dataset.rating)` | `renderCurrentDetail()` in `public/js/graph-view.js` |
| `.trigger-repair-next` | `click` | `window.SocratinkApp?.nextRepairRep?.()` | `renderCurrentDetail()` in `public/js/graph-view.js` |
| `.trigger-repair-exit` | `click` | `window.SocratinkApp?.exitRepairReps?.()` | `renderCurrentDetail()` in `public/js/graph-view.js` |
| `.trigger-reopen` | `click` | `window.SocratinkApp?.reopenStudy?.(activeNode.data())` | `renderCurrentDetail()` in `public/js/graph-view.js` |

---

## CSS

Implementation should add or modify these structural rules in `public/css/layout.css`:

```css
.graph-layout.mode-repair-reps {
  grid-template-columns: minmax(160px, 0.42fr) minmax(520px, 1.58fr);
}

.graph-layout.mode-repair-reps .graph-stage-wrap {
  opacity: 0.34;
  pointer-events: none;
  filter: saturate(0.72);
}

.graph-detail.is-repair-reps {
  padding: 24px;
}

.graph-detail.is-repair-reps .graph-node-detail {
  flex: 1;
  border-bottom: none;
  overflow-y: auto;
}

.graph-repair-context-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 12px;
  color: var(--text-sub);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0;
}

.graph-repair-context-strip span {
  display: inline-flex;
  align-items: center;
}

.graph-repair-context-strip span + span::before {
  content: "/";
  margin-right: 8px;
  color: var(--border);
}

.graph-repair-helper,
.graph-repair-compare-cue,
.graph-repair-truth-line {
  color: var(--text-sub);
}

.graph-repair-rating-group {
  flex-wrap: wrap;
}

.graph-repair-next .trigger-repair-reveal:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  transform: none;
}

.graph-repair-rating-btn {
  flex: 0 1 auto;
  border-radius: 8px;
}

.graph-repair-rating-btn.is-selected {
  background: rgba(110, 174, 209, 0.14);
  color: var(--text);
  border-color: rgba(110, 174, 209, 0.52);
}

.graph-repair-summary-rating.close_match,
.graph-repair-summary-rating.partial,
.graph-repair-summary-rating.missed {
  color: var(--text-sub);
  opacity: 1;
}

@media (max-width: 899px) {
  .graph-layout.mode-repair-reps {
    grid-template-columns: 1fr;
  }

  .graph-layout.mode-repair-reps .graph-stage-wrap {
    display: none;
  }

  .graph-detail.is-repair-reps {
    min-height: 520px;
    height: auto;
  }
}
```

Animations must continue to respect the existing reduced-motion override:

```css
@media (prefers-reduced-motion: reduce) {
  .graph-repair-card.is-dealing,
  .graph-repair-bridge.is-revealing,
  .graph-repair-complete {
    animation: none !important;
  }
}
```

---

## Prompt / AI Contract

None - this feature does not make new LLM calls and does not change `app_prompts/repair-reps-system-v1.md`, `RepairRepsEvaluation`, or `generate_repair_reps()`.

The UI continues to consume the existing `target_bridge` field. The existing `feedback_cue` field remains in the response contract but is not rendered as primary comparison guidance in the focused-mode UI.

---

## Dependencies

**Requires**:
- Existing Repair Reps MVP state and API: `startRepairReps()`, `repairRepsState`, `setRepairRepsState()`, and `/api/repair-reps`.
- Existing mode chrome: `syncInteractionChrome()` adding `.mode-repair-reps` and `.is-repair-reps`.
- Existing self-rating behavior from `docs/product/repair-reps-self-rating-spec.md`.
- Existing card-stack animation behavior from `docs/product/repair-reps-card-stack-spec.md`.

**Enables**:
- None - no downstream features are blocked on this focused-mode pass.

---

## Files Changed

| File | Change |
|------|--------|
| `public/js/graph-view.js` | Modify `repairRepsMarkupForNode()` copy and structure; optionally add `repairContextStripMarkup()`; stop rendering `rep.feedback_cue` as primary visible guidance; change completion CTA to `Back to graph`. |
| `public/css/layout.css` | Add focused mode layout rules for `.graph-layout.mode-repair-reps` and `.graph-detail.is-repair-reps`; add `.graph-repair-context-strip`, helper/cue/truth-line styling; neutralize selected/rating summary colors; preserve reduced-motion behavior. |
| `public/js/app.js` | None expected. Only touch if implementation reveals an existing state restoration bug; do not change repair evidence schema or graph mutation paths. |
| `main.py` | None - explicitly out of scope. |
| `ai_service.py` | None - explicitly out of scope. |

---

## Test Plan

### Automated

- **`RepairRepsApiTests.test_repair_reps_api_requires_guest_or_auth_entry`** in `tests/test_repair_reps.py`: Asserts the repair endpoint remains auth-gated.
- **`RepairRepsApiTests.test_repair_reps_endpoint_uses_server_resolved_mechanism`** in `tests/test_repair_reps.py`: Asserts frontend copy/layout changes did not alter backend mechanism resolution.
- **`RepairRepsApiTests.test_generate_repair_reps_returns_exact_three_graph_neutral_reps`** in `tests/test_repair_reps.py`: Asserts the response remains exactly three graph-neutral reps.
- **`AppPromptTests.test_repair_reps_prompt_bans_recognition_and_mastery_shortcuts`** in `tests/test_app_prompts.py`: Asserts prompt boundaries still reject recognition/mastery shortcuts.
- Run `node --check public/js/app.js` and `node --check public/js/graph-view.js`.
- Run `git diff --check`.

### Manual

1. Start Repair Reps from a `primed` node with `drill_phase === "re_drill"` -> focused mode appears, graph is de-emphasized/non-interactive, context strip shows node label and `Repair Rep 1 of 3`.
2. Start Repair Reps from a `drilled` node -> focused mode appears and existing `gap_type` / `gap_description` remain unchanged in `concept.graphData`.
3. Inspect a `solidified` node -> Repair Reps CTA is absent or blocked.
4. Before typing -> textarea has no placeholder; `Your bridge` label and helper remain visible.
5. Type an answer and click `Show reference bridge` -> typed answer persists readonly above the `Reference bridge`; static cue reads `Compare the link, not the wording.`
6. Select each self-rating state during a three-rep run -> selection is neutral/repair-tinted, not green/red, and the next action remains gated until a rating is selected.
7. Complete the final rep -> completion reads `Practice logged` and `These reps are saved. Graph progress comes from the next re-drill.`
8. Click `Back to graph` from completion and from an error/no-reps state -> graph pointer behavior and normal layout return through class removal.
9. Check `localStorage.learnops_repair_reps_v1` -> evidence contains completion facts only and no full answers.
10. Enable reduced motion -> deal/reveal/settle animations are suppressed.

### Regression

- `python -m unittest tests.test_app_prompts tests.test_repair_reps -v` should pass.
- `python -m unittest discover -s tests -v` should be run before merge; call out the known pre-existing telemetry failures if still present.
- Normal graph inspect, study, post-drill, cold-attempt-active, and re-drill-active modes should retain their existing layouts.
- `patchActiveConceptDrillOutcome`, `recordInterleavingEvent`, and `markNodeVisitedThisSession` should not appear in any new Repair Reps call path.

---

## Constraints Checklist

1. Does it preserve the three-phase loop? **Yes** - Repair Reps remains optional practice outside cold attempt, study, and scored re-drill transitions.
2. Does it make the current target and phase clearer? **Yes** - the context strip identifies the node, rep index, and practice-only status.
3. Does it reward real reconstruction or buffer echo? **Yes** - the learner must type before the reference bridge appears, preserving Generation Before Recognition.
4. Does the AI support the loop or replace the thinking? **Yes** - the AI-generated reference bridge appears only after learner generation and does not score the answer.
5. Does it frame difficulty as exploration or evaluation? **Yes** - copy uses bridge, reference, and comparison language instead of score or correctness language.
6. Does the graph tell the truth? **Yes** - the graph is de-emphasized during practice and restored unchanged; no graph mutation paths are touched.
7. Would the learner still choose this behavior if they knew how the system influenced them? **Yes** - the UI plainly frames the mode as practice and tells the learner graph progress comes from re-drill.

---

## Agent Routing

| Phase | Owner | Action |
|-------|-------|--------|
| Spec review | **elliot** | Validate that focused-mode ownership does not conflict with the card-stack or self-rating specs and that copy preserves graph truth. |
| Investigation (if needed) | **sherlock** | Trace `syncInteractionChrome()`, `setInteractionMode()`, and `exitRepairReps()` if graph restoration or pointer behavior is unclear during implementation. |
| Implementation | **socratinker** | Edit `public/js/graph-view.js` first for copy/context markup, then `public/css/layout.css` for focused layout and neutral rating styles. Avoid backend and persistence changes. |
| QA / release gate | **thurman** | Run the automated checks and manual browser flow, especially graph state unchanged, reduced-motion behavior, and exit from completion/error states. |
| Post-implementation review | **glenna** | Review whether the multi-agent handoff kept role boundaries clear and whether the final implementation followed the focused-mode spec without scope creep. |


---


# Repair Reps — Card-Stack Visual Spec

## Agent Summary

> **What this document is**: The spec for making the Repair Reps UI feel like a physical card deck rather than a panel view. Cards deal in, flip on reveal, and stack on completion. The goal is mechanical distinctness from the conversational drill mode.
>
> **When to read it**: Before changing repair-reps CSS, the `repairRepsMarkupForNode()` markup, or any animation in the repair lane.
>
> **What it is NOT**: It does not change data flow, state shape, API contracts, or storage. This is a visual-only change.
>
> **Key constraints**:
> - All animations must respect `prefers-reduced-motion: reduce` (set `animation: none !important`).
> - No layout shifts that move interactive elements (buttons, textarea) after they are visible.
> - Card transitions must complete within 400ms so the UI feels snappy, not theatrical.
> - Do not reuse the solidified celebration animations (`graphSolidSnap`, `graphSolidGlow`, `graphSolidInk`). Those belong to mastery. Repair gets its own vocabulary.

---

## Visual Concept

Drill is a **conversation** — a back-and-forth chat panel. Repair Reps are a **deck** — three cards dealt one at a time, flipped to reveal the bridge, then stacked as complete.

The learner should feel the difference immediately: drill = dialogue, repair = cards.

---

## Card Entrance (Deal)

### When

Each time a new rep becomes current: initial load (rep 1) and each `nextRepairRep()` transition (reps 2, 3).

### Animation

The `.graph-repair-card` element enters with a slide-up + fade:

```css
@keyframes repairDeal {
  0% {
    opacity: 0;
    transform: translateY(12px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

.graph-repair-card.is-dealing {
  animation: repairDeal 280ms cubic-bezier(0.2, 0.8, 0.2, 1) both;
}
```

The `.is-dealing` class is added only when `currentIndex` changes (new rep dealt), not on reveal. The markup must track the previous `currentIndex` and add `.is-dealing` only when it differs from the last render. On reveal (same `currentIndex`, `revealed` flips true), the card re-renders without `.is-dealing`, so no animation replays. This prevents the deal animation from firing mid-reveal, which would shift the textarea and bridge while the learner is comparing.

### Rep Counter

The existing kicker "Repair Rep 1 of 3" is sufficient. Add a visual progress indicator below it — three small dots, the current one filled:

```html
<div class="graph-repair-progress">
  <span class="graph-repair-dot ${currentIndex >= 0 ? 'is-done' : ''}"></span>
  <span class="graph-repair-dot ${currentIndex >= 1 ? 'is-done' : ''}"></span>
  <span class="graph-repair-dot ${currentIndex >= 2 ? 'is-done' : ''}"></span>
</div>
```

A dot is `is-done` for all reps at or before `currentIndex`. The current dot is the active one. On the completion screen, all three are filled.

```css
.graph-repair-progress {
  display: flex;
  gap: 6px;
  margin-top: 4px;
}
.graph-repair-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--border);
  transition: background 0.2s ease;
}
.graph-repair-dot.is-done {
  background: var(--primary);
}
```

---

## Bridge Reveal (Flip)

### When

The learner clicks "Reveal Bridge" and `revealed` becomes `true`.

### Animation

The `.graph-repair-bridge` element (the target bridge + feedback cue container) enters with a vertical unfold + fade. This mimics flipping the back of the card into view:

```css
@keyframes repairReveal {
  0% {
    opacity: 0;
    transform: scaleY(0.92);
    transform-origin: top center;
  }
  100% {
    opacity: 1;
    transform: scaleY(1);
    transform-origin: top center;
  }
}

.graph-repair-bridge {
  animation: repairReveal 320ms cubic-bezier(0.2, 0.8, 0.2, 1) both;
}
```

The bridge container already has a distinct background (`rgba(var(--lavender-500-rgb), 0.05)`) and border, so no color change is needed. The animation adds the motion.

### Textarea After Reveal

When `revealed === true`, the textarea should become `readonly` and slightly dim to shift focus to the bridge. Do not hide or remove it — the learner needs to compare their answer to the bridge.

```css
.graph-repair-input[readonly] {
  opacity: 0.65;
  cursor: default;
  resize: none;
}
```

The `readonly` attribute is set in the markup when `revealed === true`.

---

## Completion (Stack Settle)

### When

The final `nextRepairRep()` call sets `status: 'complete'`.

### Animation

The completion card uses a subtler entrance than the deal — a gentle scale-in to signal "set done":

```css
@keyframes repairSettle {
  0% {
    opacity: 0;
    transform: scale(0.97);
  }
  100% {
    opacity: 1;
    transform: scale(1);
  }
}

.graph-repair-complete {
  animation: repairSettle 360ms ease-out both;
}
```

Add class `graph-repair-complete` to the completion-state wrapper in `repairRepsMarkupForNode()`.

### Completion Copy

Keep the existing text: "Practice logged" / "The graph still waits for a spaced re-drill." These reinforce that repair is not mastery.

---

## Reduced Motion

All three keyframes must be suppressed:

```css
@media (prefers-reduced-motion: reduce) {
  .graph-repair-card.is-dealing,
  .graph-repair-bridge,
  .graph-repair-complete {
    animation: none !important;
  }
}
```

---

## Markup Changes

### `repairRepsMarkupForNode()` — Ready State

Add the progress dots after the kicker. Add `readonly` to textarea when revealed:

```html
<section class="graph-detail-surface graph-repair-card ${isNewRep ? 'is-dealing' : ''}">
  <div class="graph-detail-kicker">Repair Rep ${currentIndex + 1} of ${reps.length}</div>
  <div class="graph-repair-progress">
    <span class="graph-repair-dot ${currentIndex >= 0 ? 'is-done' : ''}"></span>
    <span class="graph-repair-dot ${currentIndex >= 1 ? 'is-done' : ''}"></span>
    <span class="graph-repair-dot ${currentIndex >= 2 ? 'is-done' : ''}"></span>
  </div>
  <h3 class="graph-detail-title">${escHtml(nodeLabel)}</h3>
  <p class="graph-detail-copy">${escHtml(rep.prompt)}</p>
  <textarea class="graph-repair-input" rows="4"
    ${revealed ? 'readonly' : ''}
    placeholder="Type the causal link in your own words">${revealed ? escHtml(state.currentAnswer || '') : ''}</textarea>
  ${revealed ? `
    <div class="graph-repair-bridge">
      <div class="graph-detail-kicker">Target bridge</div>
      <p class="graph-detail-copy">${escHtml(rep.target_bridge)}</p>
      <p class="graph-detail-copy">${escHtml(rep.feedback_cue)}</p>
    </div>
  ` : ''}
</section>
```

### `repairRepsMarkupForNode()` — Complete State

Wrap in `.graph-repair-complete`:

```html
<div class="graph-repair-complete">
  <div class="graph-detail-kicker">Repair Reps</div>
  <div class="graph-repair-progress">
    <span class="graph-repair-dot is-done"></span>
    <span class="graph-repair-dot is-done"></span>
    <span class="graph-repair-dot is-done"></span>
  </div>
  <h3 class="graph-detail-title">Practice logged</h3>
  <p class="graph-detail-copy">These reps repaired the path back to the mechanism. The graph still waits for a spaced re-drill.</p>
  <button class="... trigger-repair-exit">Return to Map</button>
</div>
```

### Loading State

Add the progress dots (all unfilled) to the loading state for visual continuity.

---

## Files Changed

| File | Change |
|------|--------|
| `public/js/graph-view.js` | Modify `repairRepsMarkupForNode()`: add progress dots to ready/loading/complete states, add `readonly` to textarea when revealed, add `.graph-repair-complete` wrapper to complete state. |
| `public/css/layout.css` | Add `@keyframes repairDeal`, `repairReveal`, `repairSettle`. Add `.graph-repair-progress`, `.graph-repair-dot`, `.graph-repair-complete`, `.graph-repair-input[readonly]` rules. Add `prefers-reduced-motion` overrides. |

No JS logic changes. No state shape changes. No API changes.

---

## Test Plan

- **Visual**: Step through all 3 reps. Verify card deals in on each rep, bridge reveals with unfold animation, and completion settles.
- **Progress dots**: Confirm dots fill left-to-right as reps advance. All three filled on completion.
- **Textarea**: Confirm textarea becomes readonly + dimmed after reveal. Confirm the learner's typed text remains visible (not cleared).
- **Reduced motion**: Set `prefers-reduced-motion: reduce` in OS/browser. Verify all three animations are suppressed.
- **Regression**: Drill mode, study mode, and post-drill mode are visually unchanged. No new animations leak into those modes.
- **Mobile**: Verify the progress dots and card animations work on narrow viewports. The dots should not wrap.

---

## Constraints Checklist

1. Does it preserve the three-phase loop? **Yes** — visual only, no state changes.
2. Does the graph tell the truth? **Yes** — no graph mutation.
3. Does it make the current target and phase clearer? **Yes** — the card metaphor and progress dots make the current rep and total count immediately visible.
4. Does the AI support the loop or replace the thinking? **N/A** — no AI involvement.
5. Would the learner still choose this behavior if they knew how the system influenced them? **Yes** — animations are informational (progress, transition), not manipulative.


---


# Repair Reps — Self-Rating Spec

## Agent Summary

> **What this document is**: The spec for adding a learner self-rating step to the Repair Reps reveal flow. After the target bridge is shown, the learner rates their own reconstruction before advancing to the next rep. Ratings are stored in repair evidence and surfaced on the completion screen.
>
> **When to read it**: Before changing the repair-reps reveal flow, the repair evidence schema, or the completion screen in `repairRepsMarkupForNode()`.
>
> **What it is NOT**: It is not a mastery signal. Self-ratings never flow into `drill_status`, graph state, or interleaving logic. They are metacognitive self-assessment only.
>
> **Key constraints**:
> - Self-ratings are learner-assigned, never AI-scored. No LLM call per rep.
> - Ratings must not use mastery language ("you mastered this", "correct", "score").
> - No graph mutation, no `patchActiveConceptDrillOutcome()`, no `recordInterleavingEvent()`.
> - Completion screen shows a rep-kind breakdown with self-ratings but no aggregate score or percentage.

---

## Rating Step

### When It Appears

After the learner clicks "Reveal Bridge" and the `target_bridge` + `feedback_cue` are shown, a rating prompt appears between the bridge and the "Next Rep" / "Finish Reps" button.

### Rating Options

Three options, rendered as a horizontal button group:

| Value | Label | Meaning |
|-------|-------|---------|
| `close_match` | "Close match" | The causal link I typed captures the bridge. |
| `partial` | "Partly linked" | I got part of the chain but missed a step. |
| `missed` | "Missed the link" | My answer didn't capture the causal bridge. |

- Exactly one must be selected before "Next Rep" / "Finish Reps" is enabled.
- No default selection. The learner must actively choose.
- Selection is visually distinct (filled/highlighted state) but not celebratory. Use the existing `.graph-detail-secondary-action` styling as the base, with an `.is-selected` modifier that uses `var(--primary)` background.

### Interaction Flow

1. Learner types answer, clicks "Reveal Bridge".
2. Bridge and feedback cue appear. Rating buttons appear. "Next Rep" button is hidden or disabled.
3. Learner taps a rating. The button gets `.is-selected`. "Next Rep" / "Finish Reps" button appears.
4. Learner clicks "Next Rep" — rating is recorded, next rep loads.

---

## State Changes

### `repairRepsState` Additions

Add two fields:

```javascript
{
  ...existingFields,
  ratings: [],        // Array<'close_match'|'partial'|'missed'>, one per rep
  ratingSelected: false  // Whether the current rep has a rating selected
}
```

- `ratings` is initialized as `[]` and grows as reps are completed.
- `ratingSelected` resets to `false` on each `nextRepairRep()` call.

### `revealRepairRep()` Change

No change beyond existing behavior. The rating UI appears in the markup when `revealed === true`.

### New Function: `rateRepairRep(rating)`

```
rateRepairRep(rating: 'close_match' | 'partial' | 'missed')
```

- Validates `repairRepsState.status === 'ready'` and `repairRepsState.revealed === true`.
- Sets `repairRepsState.ratings[currentIndex] = rating`.
- Sets `repairRepsState.ratingSelected = true`.
- Calls `setRepairRepsState()` to re-render.

### `nextRepairRep()` Change

- Guard: do not advance if `repairRepsState.ratingSelected === false`. Silent no-op.
- On advance, reset `ratingSelected` to `false`.
- On completion (final rep), pass `ratings` to `recordRepairRepsCompletion()`.

### `recordRepairRepsCompletion()` Change

Add `ratings` to the stored evidence:

```javascript
{
  completed_at: new Date().toISOString(),
  rep_count: number,
  prompt_version: string,
  gap_type: string | null,
  answer_lengths: number[],
  ratings: ('close_match' | 'partial' | 'missed')[]  // NEW
}
```

### Exported API

Export `rateRepairRep` on the `SocratinkApp` public interface alongside the existing repair functions.

---

## Markup Changes

### `repairRepsMarkupForNode()` — Ready + Revealed State

After the `.graph-repair-bridge` div and before the `.graph-study-next` section, insert the rating group:

```html
<div class="graph-repair-rating">
  <div class="graph-detail-kicker">How close was your bridge?</div>
  <div class="graph-repair-rating-group">
    <button class="graph-repair-rating-btn trigger-repair-rate ${state.ratings[currentIndex] === 'close_match' ? 'is-selected' : ''}" data-rating="close_match">Close match</button>
    <button class="graph-repair-rating-btn trigger-repair-rate ${state.ratings[currentIndex] === 'partial' ? 'is-selected' : ''}" data-rating="partial">Partly linked</button>
    <button class="graph-repair-rating-btn trigger-repair-rate ${state.ratings[currentIndex] === 'missed' ? 'is-selected' : ''}" data-rating="missed">Missed the link</button>
  </div>
</div>
```

Only render the rating group when `revealed === true`.

Gate the "Next Rep" / "Finish Reps" button on `ratingSelected === true`.

### `repairRepsMarkupForNode()` — Complete State

Replace the current completion message with a rep-kind breakdown:

```html
<div class="graph-detail-kicker">Repair Reps</div>
<h3 class="graph-detail-title">Practice logged</h3>
<div class="graph-repair-summary">
  ${reps.map((rep, i) => `
    <div class="graph-repair-summary-row">
      <span class="graph-detail-pill">${kindLabel(rep.kind)}</span>
      <span class="graph-repair-summary-rating ${ratings[i]}">${ratingLabel(ratings[i])}</span>
    </div>
  `).join('')}
</div>
<p class="graph-detail-copy">The graph still waits for a spaced re-drill.</p>
<button class="... trigger-repair-exit">Return to Map</button>
```

Kind labels: `missing_bridge` → "Bridge", `next_step` → "Next Step", `cause_effect` → "Cause → Effect".

Rating labels: `close_match` → "Close match", `partial` → "Partly linked", `missed` → "Missed the link".

### Event Listeners

In `graph-view.js` `renderCurrentDetail()`, add listener for `.trigger-repair-rate` buttons:

```javascript
detailEl.querySelectorAll('.trigger-repair-rate').forEach((btn) => {
  btn.addEventListener('click', () => {
    window.SocratinkApp?.rateRepairRep?.(btn.dataset.rating);
  });
});
```

---

## CSS

### New Rules

```css
.graph-repair-rating {
  margin-top: 8px;
}
.graph-repair-rating-group {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}
.graph-repair-rating-btn {
  flex: 1;
  padding: 8px 4px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--surface-nested);
  color: var(--text);
  font: inherit;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}
.graph-repair-rating-btn.is-selected {
  background: var(--primary);
  color: var(--surface-card);
  border-color: var(--primary);
}
.graph-repair-summary {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 12px 0;
}
.graph-repair-summary-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.graph-repair-summary-rating {
  font-size: 12px;
  font-weight: 600;
}
.graph-repair-summary-rating.close_match { color: var(--success, #4caf50); }
.graph-repair-summary-rating.partial { color: var(--text-sub); }
.graph-repair-summary-rating.missed { color: var(--text-sub); opacity: 0.7; }
```

Respect `prefers-reduced-motion`: no animations to suppress here (static UI).

---

## Files Changed

| File | Change |
|------|--------|
| `public/js/app.js` | Add `rateRepairRep()`. Modify `repairRepsState` shape, `nextRepairRep()`, `recordRepairRepsCompletion()`. Export `rateRepairRep`. |
| `public/js/graph-view.js` | Modify `repairRepsMarkupForNode()` ready+revealed and complete states. Add `.trigger-repair-rate` event listener in `renderCurrentDetail()`. |
| `public/css/layout.css` | Add `.graph-repair-rating-*` and `.graph-repair-summary-*` rules. |

---

## Test Plan

- **Manual**: Complete a 3-rep set. Verify each rep requires a rating before "Next Rep" enables. Verify completion screen shows all 3 rep kinds with corresponding ratings.
- **Storage**: Check `learnops_repair_reps_v1` in localStorage. Confirm `ratings` array appears in the stored evidence with exactly 3 entries.
- **Regression**: Repair Reps without this change still function (the `ratings` field is absent in old records — code must tolerate `undefined`).
- **No graph mutation**: Verify self-ratings do not call any drill outcome, interleaving, or node-visit function.

---

## Constraints Checklist

1. Does it preserve the three-phase loop? **Yes** — repair reps remain outside the loop.
2. Does the graph tell the truth? **Yes** — self-ratings never touch graph state.
3. Does the AI support the loop or replace the thinking? **N/A** — no AI call involved.
4. Would the learner still choose this behavior if they knew how the system influenced them? **Yes** — the learner is the one assigning the rating.
