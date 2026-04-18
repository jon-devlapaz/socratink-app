# Socratink - Repair Reps Slice B: Metacognitive Loop Spec

## Agent Summary

> **What this document is**: This spec governs the *metacognitive loop* addition
> to the Repair Reps focused workbench: a pre-reveal confidence pill, a soft
> reveal gate that requires both a non-empty attempt and a committed stance, a
> single-click lock-and-reveal mechanic, and a completion-summary calibration
> readout pairing predicted confidence with self-rated outcome. This is
> Slice B on top of already-specced Phase 1+2 copy/layout work in
> `docs/product/repair-reps-focused-mode-spec.md`.
>
> **When to read it**:
> - Before changing `repairRepsMarkupForNode()` in `public/js/graph-view.js`.
> - Before changing `.graph-repair-card`, `.graph-repair-predict`, `.graph-repair-rating-group`, or `.graph-repair-summary` rules in `public/css/layout.css`.
> - Before extending the `learnops_repair_reps_v1` localStorage record shape.
> - Before changing the visible wording around "Before you peek", "Lock in and show reference bridge", or the per-rep calibration summary.
>
> **What it is NOT**: This does not replace or modify `docs/product/repair-reps-focused-mode-spec.md` (Phase 1+2 focused layout), `docs/product/repair-reps-card-stack-spec.md` (card-stack animation vocabulary), or `docs/product/repair-reps-self-rating-spec.md` (self-rating semantics). It does not change the Repair Reps backend generation contract in `main.py` or `ai_service.py`. It does not change `/api/repair-reps`, `RepairRepsRequest`, or `app_prompts/repair-reps-system-v1.md`.
>
> **Key constraints** (inherited and extended):
> - Repair Reps must not call `patchActiveConceptDrillOutcome()`, `recordInterleavingEvent()`, or `markNodeVisitedThisSession()`.
> - Repair Reps must not mutate `drill_status`, `drill_phase`, `study_completed_at`, `re_drill_eligible_after`, `gap_type`, or `gap_description`.
> - Reference bridge must render only after the learner has committed a pre-reveal confidence *and* typed a non-empty answer.
> - The reveal button is the single commitment point — one click locks the attempt and reveals the reference.
> - Pre-confidence and lock durations are persisted on completion only; never during an in-progress rep.
> - Calibration readout must be observational ("Predicted: X - Rated: Y") — never judgmental ("overconfident", "miscalibrated").
> - Confidence values must not mutate graph state, feed routing, or appear as progress/mastery evidence.
> - Copy must avoid score, correct, mastered, streak, win, or celebration language.

---

## Motivation

Today's Repair Reps workbench accepts a bridge, reveals a reference on demand, and logs a self-rating. It misses the metacognitive beat: the learner never has to declare a stance *before* seeing the answer, so the reveal becomes a peek rather than a commitment. Without commitment, the self-rating collapses into hindsight, and the founder using the product loses the calibration signal that separates "I thought I knew this" from "I knew this."

Slice B adds the smallest possible pre-reveal commitment device (three pills), soft-gates the reveal behind that commitment plus a typed attempt, and surfaces predicted-vs-rated pairs in the completion summary. No new routes, no new backend, no new graph state. It is a frontend rendering and localStorage-shape change.

This slice is intentionally narrower than the full metacognitive-UX review (P0-P3, 30+ items). Deferred for future slices: split Claim/Mechanism fields, hedge-word detector, autosave, rep-dot hover explanations, "I don't know yet" help path, and analytics calibration tiles.

---

## Assumptions

- The implementation can use the existing `syncInteractionChrome()` mode hooks: `.graph-layout.mode-repair-reps` and `.graph-detail.is-repair-reps`.
- The existing `repairRepsState` shape can absorb two new transient fields (`preConfidence`, `lockedAt`) without schema churn at the module boundary.
- The existing `learnops_repair_reps_v1` localStorage entry is readable by older callers that do not know about the new fields; missing arrays are treated as `[]`.
- Repair Reps evidence writes happen on completion only, as already specced. No per-rep localStorage writes.
- No DB layer. localStorage is the sole persistence substrate for this slice.
- The founder is the only user during this slice's lifespan. No telemetry infrastructure is added.

---

## Behavior

### Primary Flow

1. The learner enters Repair Reps focused mode from an eligible node, per existing spec.
2. The rep card renders the standard context strip, node title, rep prompt, and the Phase 1+2 "Your bridge" label / textarea / helper copy.
3. A new **"Before you peek"** section renders directly above the "Your bridge" label. It contains:
   - The kicker: `Before you peek`
   - A horizontal row of three pills: `Guessing` / `Have a hunch` / `Can explain`
4. The learner can type into the textarea at any time; typing does not require a pill selection. Order-independent: pill-then-type and type-then-pill are both valid.
5. The **"Lock in and show reference bridge"** button is disabled until both conditions are true:
   - A pill has been selected (stored as `preConfidence`)
   - The textarea trimmed value is non-empty
6. On button click (single click), the following happens atomically:
   - `repairRepsState.lockedAt` is stamped with `Date.now()`
   - The textarea becomes `readonly`
   - The pill row becomes non-interactive (visually keeps the selected pill highlighted)
   - The reference bridge panel unfolds with the existing reveal animation
   - The self-rating row renders below, matching the Phase 1+2 revealed-state markup
7. The learner selects one self-rating (`Matched` / `Partial` / `Off track`). The next-rep advance fires as before.
8. After the third rep rating, the card transitions to the Repair Reps complete state.
9. The complete state shows the existing `Practice logged` heading, the existing context strip, and a new per-rep calibration summary block:
   - Three rows, one per rep: `Rep 1 - Predicted: Have a hunch - Rated: Partial`, etc.
   - Completion evidence is written to `learnops_repair_reps_v1` with the extended shape (see Storage Schema below).
10. The learner clicks `Back to graph`. State is released via the existing `exitRepairReps()` path.

### Edge Cases

- **Learner never picks a pill**: Reveal button stays disabled. The learner cannot reveal the reference without selecting a stance. This is intentional; it is the metacognitive gate.
- **Learner picks pill, types, then clears the textarea**: Reveal button re-disables. Pill selection persists.
- **Learner picks pill, types, reveals, then attempts to change pill**: The pill row is non-interactive after reveal. Pre-confidence is frozen at reveal time.
- **Loading state**: The "Before you peek" section does not render during loading. The existing loading markup is unchanged.
- **Error state**: The pill section does not render. Existing error markup is unchanged.
- **Reduced motion**: The pill-row appearance, button-enable transition, and reveal animation all respect `prefers-reduced-motion: reduce`.
- **Old evidence records**: Existing `learnops_repair_reps_v1` records without `pre_confidences` or `lock_durations_ms` remain readable. Readers must treat missing arrays as `[]` and tolerate length mismatches with `ratings` and `answer_lengths`.
- **Mobile layout**: Pill row wraps to a second line on narrow panels. The reveal button remains full-width below.

---

## Invariant Boundary

This slice must NOT:

- Call or modify `patchActiveConceptDrillOutcome()`, `recordInterleavingEvent()`, or `markNodeVisitedThisSession()`. Pre-confidence and lock duration are practice metadata, not drill outcomes.
- Mutate `concept.graphData`, `drill_status`, `drill_phase`, `study_completed_at`, `re_drill_eligible_after`, `gap_type`, or `gap_description`.
- Treat `pre_confidence`, `lock_durations_ms`, or the calibration pairs as evidence of understanding. They are metacognitive self-report.
- Display the calibration readout per-rep inline (only in the completion summary).
- Use judgmental labels in the calibration readout ("overconfident", "miscalibrated", "wrong"). Language stays observational.
- Route, filter, or prioritize nodes based on pre-confidence values. Scheduling is the re-drill system's job.
- Add a separate `Lock in` button. The single button `Lock in and show reference bridge` is the commitment point.
- Add a confirm modal, side-by-side diff view, or "I don't know yet" help path. Those are deferred.
- Change `/api/repair-reps`, `RepairRepsRequest`, `generate_repair_reps()`, `RepairRepsEvaluation`, or `app_prompts/repair-reps-system-v1.md`.
- Add manual JS `element.style.pointerEvents` mutations. Graph interactivity continues to flow through the existing `.mode-repair-reps` CSS gate.

---

## State Changes

### New or Modified State

`repairRepsState` gains two transient fields:

```
repairRepsState.preConfidence: "guessing" | "hunch" | "can_explain" | null = null
  - Per-rep pre-reveal confidence selection.
  - Resets to null when `nextRepairRep()` advances to the next rep.
  - Null indicates the learner has not yet selected a stance; reveal button stays disabled.

repairRepsState.preConfidences: Array<"guessing"|"hunch"|"can_explain"> = []
  - Accumulated per-rep selections, pushed on each reveal.
  - Length matches completed-rep count.

repairRepsState.lockedAt: number | null = null
  - Per-rep timestamp at reveal-button click (Date.now()).
  - Resets to null on `nextRepairRep()`.

repairRepsState.lockDurationsMs: Array<number> = []
  - Accumulated per-rep durations: `lockedAt - repStartAt`, pushed on reveal.
  - `repStartAt` is captured on rep entry (new internal timestamp in the reducer, not exposed).
```

No existing state fields are renamed or repurposed.

### New or Modified Functions

**`repairRepsMarkupForNode(data, repairState = {})`** in `public/js/graph-view.js`:
Modify the ready-before-reveal markup to include the "Before you peek" pill section above `Your bridge`. Modify the button label to `Lock in and show reference bridge`. Modify the complete-state markup to render the per-rep calibration summary.

**`repairPredictPillsMarkup(currentPreConfidence)`** in `public/js/graph-view.js`:
New helper that returns the three-pill markup for the predict block. Must be pure; no state mutation.

**`repairCalibrationSummaryMarkup(preConfidences, ratings)`** in `public/js/graph-view.js`:
New helper that returns the per-rep `Predicted: X - Rated: Y` summary block. Tolerates array length mismatches gracefully (pads with `-`).

**`setRepairRepsState(patch)`** in `public/js/graph-view.js` (or wherever the reducer lives):
Must handle `preConfidence`, `lockedAt`, and the reveal-transition atomic update (push to `preConfidences` + `lockDurationsMs`, set textarea readonly flag).

**`revealRepairRep(answer)`** in `public/js/app.js` (or graph-view.js, wherever defined):
Extend preconditions: require both non-empty trimmed answer AND non-null `preConfidence`. On success, stamp `lockedAt`, push to `preConfidences` and `lockDurationsMs`, then call the existing reveal path.

**`completeRepairReps()`** in `public/js/app.js` (or wherever the completion write happens):
Extend the `learnops_repair_reps_v1` write to include `pre_confidences` and `lock_durations_ms` arrays.

### Storage Schema

The existing `learnops_repair_reps_v1` key gains two additive arrays. Schema after this slice:

```json
{
  "concept_id::node_id": [
    {
      "completed_at": "ISO timestamp",
      "rep_count": 3,
      "prompt_version": "repair-reps-system-v1",
      "gap_type": "string|null",
      "answer_lengths": [0, 0, 0],
      "ratings": ["close_match", "partial", "missed"],
      "pre_confidences": ["guessing", "hunch", "can_explain"],
      "lock_durations_ms": [12034, 8120, 15240]
    }
  ]
}
```

Backward compatibility: readers must treat missing `pre_confidences` / `lock_durations_ms` as `[]`. No migration of old records.

---

## API Changes

None. Backend, request models, response models, prompts, and AI generation behavior are unchanged.

---

## Markup / UI

### Ready (before reveal) State

Produced by `repairRepsMarkupForNode()` in `public/js/graph-view.js`.

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

    <div class="graph-repair-predict">
      <div class="graph-detail-kicker">Before you peek</div>
      <div class="graph-repair-predict-group" role="radiogroup" aria-label="Confidence before revealing reference">
        <button class="graph-repair-predict-pill" data-pre="guessing" role="radio" aria-checked="false">Guessing</button>
        <button class="graph-repair-predict-pill" data-pre="hunch" role="radio" aria-checked="false">Have a hunch</button>
        <button class="graph-repair-predict-pill" data-pre="can_explain" role="radio" aria-checked="false">Can explain</button>
      </div>
    </div>

    <div class="graph-detail-kicker">Your bridge</div>
    <textarea class="graph-repair-input" rows="4"></textarea>
    <p class="graph-detail-copy graph-repair-helper">Trace the causal link in one or two sentences.</p>
  </section>
  <section class="graph-detail-surface graph-study-next graph-repair-next">
    <p class="graph-detail-copy graph-repair-truth-line">Practice only. Graph progress comes from re-drill.</p>
    <button class="btn-start-drill graph-detail-action trigger-repair-reveal" disabled>Lock in and show reference bridge</button>
  </section>
</div>
```

A selected pill carries `aria-checked="true"` and `.is-selected`.

### Revealed State

Unchanged from the Phase 1+2 spec, with two additions:

- The pill row remains visible above `Your bridge` with the locked-in pill highlighted and the row marked `aria-disabled="true"`.
- The textarea is `readonly`.

No inline per-rep calibration readout is rendered in this state.

### Complete State

Produced by `repairRepsMarkupForNode()` in `public/js/graph-view.js`.

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
  <p class="graph-detail-copy">Three bridge reps saved on &lt;node label&gt;.</p>

  <div class="graph-repair-summary graph-repair-calibration">
    <div class="graph-repair-summary-row">
      <span class="graph-repair-summary-rep">Rep 1</span>
      <span class="graph-repair-summary-pair"><span class="muted">Predicted:</span> Have a hunch</span>
      <span class="graph-repair-summary-pair"><span class="muted">Rated:</span> Partial</span>
    </div>
    <div class="graph-repair-summary-row">...Rep 2...</div>
    <div class="graph-repair-summary-row">...Rep 3...</div>
  </div>

  <p class="graph-detail-copy">These reps are saved. Graph progress comes from the next re-drill.</p>
  <button class="btn-start-drill graph-detail-action trigger-repair-exit">Back to graph</button>
</div>
```

### Event Listeners

| Selector | Event | Handler | Bound in |
|----------|-------|---------|----------|
| `.graph-repair-predict-pill` | `click` | `window.SocratinkApp?.selectRepairPreConfidence?.(btn.dataset.pre)` | `renderCurrentDetail()` in `public/js/graph-view.js` |
| `.graph-repair-input` | `input` | Enable `.trigger-repair-reveal` only when trimmed input is non-empty AND `preConfidence !== null` | `renderCurrentDetail()` in `public/js/graph-view.js` |
| `.trigger-repair-reveal` | `click` | `window.SocratinkApp?.revealRepairRep?.(answer)` (extended to validate `preConfidence` and stamp `lockedAt` before calling existing reveal path) | `renderCurrentDetail()` in `public/js/graph-view.js` |

All existing listeners (`.trigger-repair-rate`, `.trigger-repair-next`, `.trigger-repair-exit`, `.trigger-reopen`) remain unchanged.

---

## CSS

New rules in `public/css/layout.css`:

```css
.graph-repair-predict {
  margin-bottom: 18px;
}

.graph-repair-predict > .graph-detail-kicker {
  margin-bottom: 8px;
}

.graph-repair-predict-group {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.graph-repair-predict-pill {
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
  background: var(--surface-card);
  border: 1px solid var(--border);
  color: var(--text);
  cursor: pointer;
  font-family: inherit;
  transition: background 120ms ease, border-color 120ms ease;
}

.graph-repair-predict-pill:hover {
  border-color: var(--accent-border-strong);
}

.graph-repair-predict-pill.is-selected,
.graph-repair-predict-pill[aria-checked="true"] {
  background: var(--accent-soft);
  border-color: var(--accent-border-strong);
  color: var(--primary);
  font-weight: 600;
}

.graph-repair-predict-group[aria-disabled="true"] .graph-repair-predict-pill {
  cursor: default;
  pointer-events: none;
}

.graph-repair-calibration .graph-repair-summary-row {
  display: grid;
  grid-template-columns: max-content 1fr 1fr;
  gap: 10px 16px;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
  font-size: 12px;
}

.graph-repair-calibration .graph-repair-summary-row:last-child {
  border-bottom: none;
}

.graph-repair-summary-rep {
  font-weight: 700;
  color: var(--text-sub);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 1.2px;
}

.graph-repair-summary-pair .muted {
  color: var(--text-sub);
}

@media (prefers-reduced-motion: reduce) {
  .graph-repair-predict-pill {
    transition: none;
  }
}
```

Animations must continue to respect the existing reduced-motion override from the focused-mode spec.

---

## Prompt / AI Contract

None. This slice does not make new LLM calls and does not change `app_prompts/repair-reps-system-v1.md`, `RepairRepsEvaluation`, or `generate_repair_reps()`.

---

## Dependencies

**Requires**:
- Phase 1+2 focused-mode spec already implemented (`docs/product/repair-reps-focused-mode-spec.md`).
- Existing self-rating behavior (`docs/product/repair-reps-self-rating-spec.md`).
- Existing card-stack animation behavior (`docs/product/repair-reps-card-stack-spec.md`).
- Existing state machine: `startRepairReps()`, `repairRepsState`, `setRepairRepsState()`, `revealRepairRep()`, `rateRepairRep()`, `nextRepairRep()`, `exitRepairReps()`, `completeRepairReps()`.

**Enables**:
- Future: calibration analytics tile (post-DB), split Claim/Mechanism fields, hedge detector, rep-dot hover explanations.

---

## Files Changed

| File | Change |
|------|--------|
| `public/js/graph-view.js` | Extend `repairRepsMarkupForNode()` ready and complete states. Add `repairPredictPillsMarkup()` and `repairCalibrationSummaryMarkup()` helpers. Extend listener binding for `.graph-repair-predict-pill`. Update reveal-enable predicate. |
| `public/js/app.js` | Add `selectRepairPreConfidence()` dispatcher on `window.SocratinkApp`. Extend `revealRepairRep()` precondition and reveal handler to stamp `lockedAt` / push `preConfidences` / push `lockDurationsMs`. Extend `completeRepairReps()` localStorage write to include the two new arrays. |
| `public/css/layout.css` | Add `.graph-repair-predict`, `.graph-repair-predict-group`, `.graph-repair-predict-pill`, `.graph-repair-calibration` rules. Respect reduced-motion. |
| `main.py` | None. |
| `ai_service.py` | None. |
| `app_prompts/*` | None. |
| `docs/product/repair-reps-focused-mode-spec.md` | None - this slice extends, does not replace. |

---

## Test Plan

### Automated

- `RepairRepsApiTests.test_repair_reps_api_requires_guest_or_auth_entry` in `tests/test_repair_reps.py`: still passes; no API surface change.
- `RepairRepsApiTests.test_repair_reps_endpoint_uses_server_resolved_mechanism`: still passes; no backend change.
- `RepairRepsApiTests.test_generate_repair_reps_returns_exact_three_graph_neutral_reps`: still passes.
- `AppPromptTests.test_repair_reps_prompt_bans_recognition_and_mastery_shortcuts`: still passes.
- `node --check public/js/graph-view.js` and `node --check public/js/app.js`: clean.
- `git diff --check`: clean.

### Manual

1. **Pill renders**: Open Repair Reps on an eligible node. The "Before you peek" kicker and three pills render above "Your bridge". No pill is selected by default.
2. **Textarea independent of pill**: Type in the textarea before selecting a pill. Typing is accepted. Helper copy remains visible. Reveal button stays disabled.
3. **Pill-first flow**: Select "Have a hunch". Pill highlights. Textarea is still empty. Reveal button stays disabled.
4. **Both satisfied**: Select a pill AND type a non-empty attempt. Reveal button enables.
5. **Clear textarea**: Clear the textarea after enabling. Reveal button re-disables. Pill selection persists.
6. **Change pill pre-reveal**: Select a different pill before clicking reveal. Highlight moves to the new pill. Reveal button stays enabled (assuming non-empty attempt).
7. **Single-click reveal**: Click "Lock in and show reference bridge". Textarea becomes readonly. Pill row becomes non-interactive (highlight persists). Reference bridge unfolds with the existing animation. Self-rating row appears.
8. **Try to change pill post-reveal**: Click pills after reveal. Nothing happens. Selected pill remains highlighted.
9. **Complete 3 reps**: Progress through all three reps with different predicted/rated combinations.
10. **Completion summary**: Verify the calibration summary shows three rows with `Rep N - Predicted: X - Rated: Y` pairs. Language is observational (no "overconfident" etc.). "These reps are saved. Graph progress comes from the next re-drill." appears below the summary.
11. **localStorage**: Inspect `localStorage.learnops_repair_reps_v1`. The completion record has `pre_confidences: [...]` and `lock_durations_ms: [...]` arrays, each length 3, in rep order.
12. **Old record backward compat**: Manually inject a pre-slice-B record (without the new arrays) into localStorage and re-open Repair Reps for that node. Existing summary does not crash; missing arrays render as absent (no calibration section, or padded `-`).
13. **Exit from completion**: Click "Back to graph". Graph pointer behavior and normal layout return. `repairRepsState` resets.
14. **Reduced motion**: Enable `prefers-reduced-motion: reduce`. Pill transitions, reveal animation, and card-stack animations are all suppressed.
15. **A11y**: Pills are keyboard-focusable, arrow-key navigable via the `role="radiogroup"` hint, and screen-reader-labeled as a radio group.

### Regression

- `python -m unittest tests.test_app_prompts tests.test_repair_reps -v` passes.
- `python -m unittest discover -s tests -v` passes (call out pre-existing telemetry failures if still present).
- Normal graph inspect, study, post-drill, cold-attempt-active, and re-drill-active modes retain their existing layouts.
- `patchActiveConceptDrillOutcome`, `recordInterleavingEvent`, and `markNodeVisitedThisSession` do not appear in any new Repair Reps call path.

---

## Constraints Checklist

1. Does it preserve the three-phase loop? **Yes** - Repair Reps remains optional practice outside cold attempt, study, and scored re-drill transitions.
2. Does it make the current target and phase clearer? **Yes** - the pre-reveal pill names the stance; the calibration summary names the gap at completion.
3. Does it reward real reconstruction or buffer echo? **Yes** - the reveal gate requires a non-empty attempt; the pill adds a pre-reveal commitment.
4. Does the AI support the loop or replace the thinking? **Yes** - the reference bridge still appears only after learner generation and still does not score the answer.
5. Does it frame difficulty as exploration or evaluation? **Yes** - "Predicted / Rated" is observational; no judgmental labels.
6. Does the graph tell the truth? **Yes** - no graph mutation paths are touched; pre-confidence is practice metadata, not progress evidence.
7. Would the learner still choose this behavior if they knew how the system influenced them? **Yes** - the pill is a low-cost stance; the soft gate is explicit via button label; the completion readout is observational.

---

## Agent Routing

| Phase | Owner | Action |
|-------|-------|--------|
| Spec review | **elliot** | Validate that Slice B does not conflict with focused-mode, card-stack, or self-rating specs and that copy preserves graph truth. |
| Gap analysis | **praxis:gap-analysis** | 7-check pass (inversion, second-order, MECE, map vs territory, adversarial, simplicity, reversibility) before writing-plans is invoked. |
| Plan writing | **superpowers:writing-plans** | Turn this spec into an ordered implementation plan with TDD checkpoints. |
| Implementation | **socratinker** via **gm** | PLAN -> EXECUTE -> EMIT -> VERIFY -> COMPLETE state machine. Order: state additions, markup helpers, listeners, CSS, storage-write extension, test manual flow in browser. |
| QA / release gate | **thurman** | Run the automated checks and manual browser flow; verify backward-compat localStorage read; verify `prefers-reduced-motion`. |
| Post-implementation review | **glenna** | Review whether the multi-agent handoff kept role boundaries clear and whether the final implementation followed the slice scope without creep into deferred P0-P3 items. |
