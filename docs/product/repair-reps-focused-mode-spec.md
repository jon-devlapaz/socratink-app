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
