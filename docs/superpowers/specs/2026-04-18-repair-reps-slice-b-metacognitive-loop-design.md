# Socratink - Repair Reps Slice B: Metacognitive Loop Spec

## Agent Summary

> **What this document is**: This spec governs the *metacognitive loop* addition
> to the Repair Reps focused workbench: a pre-reveal confidence pill, a soft
> reveal gate enforced both in the UI and inside `revealRepairRep()`, a
> single-click lock-and-reveal mechanic with defined duration semantics, and a
> completion-summary calibration readout pairing predicted confidence with
> self-rated outcome. This is Slice B on top of already-specced Phase 1+2
> copy/layout work in `docs/product/repair-reps-focused-mode-spec.md`.
>
> **When to read it**:
> - Before changing `repairRepsMarkupForNode()` in `public/js/graph-view.js`.
> - Before changing `.graph-repair-card`, `.graph-repair-predict`, `.graph-repair-rating-group`, or `.graph-repair-summary` rules in `public/css/layout.css`.
> - Before extending the `learnops_repair_reps_v1` localStorage record shape.
> - Before changing the visible wording around "Before you peek", "Lock in and show reference bridge", or the per-rep calibration summary.
>
> **What it is NOT**: This does not replace or modify `docs/product/repair-reps-focused-mode-spec.md` (Phase 1+2 focused layout), `docs/product/repair-reps-card-stack-spec.md` (card-stack animation vocabulary), or `docs/product/repair-reps-self-rating-spec.md` (self-rating semantics, including the existing `Close match` / `Partly linked` / `Missed the link` visible labels and the `close_match` / `partial` / `missed` stored values). It does not change the Repair Reps backend generation contract in `main.py` or `ai_service.py`. It does not change `/api/repair-reps`, `RepairRepsRequest`, or `app_prompts/repair-reps-system-v1.md`.
>
> **Key constraints** (inherited and extended):
> - Repair Reps must not call `patchActiveConceptDrillOutcome()`, `recordInterleavingEvent()`, or `markNodeVisitedThisSession()`.
> - Repair Reps must not mutate `drill_status`, `drill_phase`, `study_completed_at`, `re_drill_eligible_after`, `gap_type`, or `gap_description`.
> - The reveal gate is enforced inside `revealRepairRep()`, not only by disabled-button UI. Direct JS calls to `revealRepairRep()` without a non-empty trimmed answer AND a valid `currentPreConfidence` MUST no-op.
> - `revealRepairRep()` MUST be idempotent: a second call when `repairRepsState.revealed === true` MUST no-op without rewriting `lockedAt`, `preConfidences`, or `lockDurationsMs`.
> - Pre-confidence and lock durations live as per-rep arrays in transient state. Completion writes those arrays to `learnops_repair_reps_v1`.
> - Lock duration is defined as `lockedAt - repStartedAt`, where `repStartedAt` is stamped when a rep becomes current (on `startRepairReps()` for rep 1 and on `nextRepairRep()` for subsequent reps).
> - Rating labels and stored values are unchanged from `docs/product/repair-reps-self-rating-spec.md`: visible `Close match` / `Partly linked` / `Missed the link`; stored `close_match` / `partial` / `missed`.
> - localStorage MUST NOT persist full learner answers, rep prompts, reference bridges, or feedback cues. Only confidence enum labels, lock durations in milliseconds, answer lengths (counts, not text), and existing fields are allowed.
> - Calibration readout must be observational ("Predicted: X / Rated: Y") - never judgmental ("overconfident", "miscalibrated"). No aggregate calibration score.
> - Confidence values must not mutate graph state, feed scheduling, or appear as progress/mastery evidence.
> - Copy must avoid score, correct, mastered, streak, win, or celebration language.

---

## Motivation

Today's Repair Reps workbench accepts a bridge, reveals a reference on demand, and logs a self-rating. It misses the metacognitive beat: the learner never has to declare a stance *before* seeing the answer, so the reveal becomes a peek rather than a commitment. Without commitment, the self-rating collapses into hindsight, and the founder using the product loses the calibration signal that separates "I thought I knew this" from "I knew this."

Slice B adds the smallest possible pre-reveal commitment device (three pills), soft-gates the reveal behind that commitment plus a typed attempt, and surfaces predicted-vs-rated pairs in the completion summary. No new routes, no new backend, no new graph state. It is a frontend rendering and localStorage-shape change.

This slice is intentionally narrower than the full metacognitive-UX review (P0-P3, 30+ items). Deferred for future slices: split Claim/Mechanism fields, hedge-word detector, autosave, rep-dot hover explanations, "I don't know yet" help path, and analytics calibration tiles.

---

## Assumptions

- The implementation can use the existing `syncInteractionChrome()` mode hooks: `.graph-layout.mode-repair-reps` and `.graph-detail.is-repair-reps`.
- The existing `repairRepsState` shape can absorb new fields: per-rep arrays (`preConfidences`, `lockDurationsMs`), a per-rep working timestamp (`repStartedAt`), a per-rep working stance (`currentPreConfidence`), and a per-rep working draft (`currentAnswer`).
- The existing `learnops_repair_reps_v1` localStorage entry is readable by older callers that do not know about the new fields; missing arrays are treated as `[]`.
- Repair Reps evidence writes happen on completion only. No per-rep localStorage writes.
- No DB layer. localStorage is the sole persistence substrate for this slice.
- The founder is the only user during this slice's lifespan. No telemetry infrastructure is added.

---

## Behavior

### Primary Flow

1. The learner enters Repair Reps focused mode from an eligible node, per existing spec.
2. On `startRepairReps()`, the reducer stamps `repStartedAt = Date.now()` for rep 1 and initializes the per-rep working fields (`currentPreConfidence = null`, `currentAnswer = ""`).
3. The rep card renders the standard context strip, node title, rep prompt, and the Phase 1+2 "Your bridge" label / textarea / helper copy.
4. A new **"Before you peek"** section renders directly above the "Your bridge" label. It contains:
   - The kicker: `Before you peek`
   - A horizontal row of three pills: `Guessing` / `Have a hunch` / `Can explain`
5. The learner can type into the textarea at any time; typing does not require a pill selection. Order-independent: pill-then-type and type-then-pill are both valid.
6. Every `input` event on the textarea calls `setRepairRepsState({ currentAnswer: textarea.value })` so the latest draft survives re-renders caused by pill selection.
7. Every pill click calls `setRepairRepPreConfidence(value)` with `value in ("guessing" | "hunch" | "can_explain")`. The handler reads the live textarea value into `currentAnswer` before dispatching the state update, guaranteeing that an unsubmitted draft is preserved across the re-render triggered by the pill selection.
8. The **"Lock in and show reference bridge"** button is disabled until both conditions are true in state:
   - `currentPreConfidence !== null`
   - `currentAnswer.trim().length > 0`
9. On button click (single click), `revealRepairRep(answer)` fires. The function:
   - No-ops if `repairRepsState.revealed === true` (idempotent).
   - No-ops if the trimmed answer is empty.
   - No-ops if `repairRepsState.currentPreConfidence` is null or not in the enum.
   - Stamps `lockedAt = Date.now()`.
   - Pushes `currentPreConfidence` onto `preConfidences`.
   - Pushes `lockedAt - repStartedAt` onto `lockDurationsMs`.
   - Sets `revealed = true` and triggers the existing reveal path.
10. The textarea becomes `readonly`. The pill row receives `aria-disabled="true"` and `.is-locked`, keeping the selected pill visibly highlighted but non-interactive.
11. The reference bridge panel unfolds with the existing reveal animation. The self-rating row renders below using the existing `Close match` / `Partly linked` / `Missed the link` buttons, matching `docs/product/repair-reps-self-rating-spec.md`.
12. The learner selects one self-rating. The existing `rateRepairRep()` path is unchanged.
13. On `nextRepairRep()`, the reducer resets `currentPreConfidence = null`, `currentAnswer = ""`, `lockedAt = null`, stamps a new `repStartedAt = Date.now()` for the next rep, and advances `currentIndex`.
14. After the third rep rating, the card transitions to the Repair Reps complete state.
15. The complete state renders the existing `Practice logged` heading and context strip plus a new per-rep calibration summary block with three rows: `Rep N / Predicted: <label> / Rated: <label>`. Labels map from enum values via fixed lookup tables in `repairCalibrationSummaryMarkup()`.
16. `recordRepairRepsCompletion()` writes the extended record to `learnops_repair_reps_v1` (see Storage Schema).
17. The learner clicks `Back to graph`. State is released via the existing `exitRepairReps()` path.

### Edge Cases

- **Learner never picks a pill**: Reveal button stays disabled. `revealRepairRep()` invoked directly via JS also no-ops. Pill is a hard prerequisite for reveal.
- **Learner picks pill, types, then clears the textarea**: Reveal button re-disables. Pill selection persists in `currentPreConfidence`.
- **Type-then-pill draft preservation**: Because every textarea `input` event updates `currentAnswer` in state, selecting a pill after typing does not wipe the textarea on re-render. The value is re-rendered from state.
- **Learner picks pill, types, reveals, then attempts to change pill**: The pill row is non-interactive after reveal via `aria-disabled="true"` and CSS `pointer-events: none` under `.is-locked`. Pre-confidence is frozen at reveal time.
- **Direct JS call to `revealRepairRep()` bypassing UI**: No-ops unless both non-empty trimmed answer AND valid `currentPreConfidence` are present, and state is not already revealed. UI disabled-button state is not the only gate.
- **Repeated calls to `revealRepairRep()` on the same rep**: Second call no-ops. `lockedAt`, `preConfidences`, and `lockDurationsMs` are written exactly once per rep.
- **Loading state**: The "Before you peek" section does not render during loading. The existing loading markup is unchanged.
- **Error state**: The pill section does not render. Existing error markup is unchanged.
- **Reduced motion**: The pill-row appearance, button-enable transition, and reveal animation all respect `prefers-reduced-motion: reduce`.
- **Old evidence records without `pre_confidences` / `lock_durations_ms`**: The calibration summary omits per-rep Predicted/Rated rows entirely, OR renders `Predicted: Not recorded` for missing values. Must not imply failure. Must not crash on missing arrays or length mismatches.
- **Mixed-length arrays**: If `pre_confidences.length != ratings.length` (legacy edge case), render up to `min(length)` rows with present data only.
- **Mobile layout**: Pill row wraps to a second line on narrow panels. The reveal button remains full-width below.

---

## Invariant Boundary

This slice must NOT:

- Call or modify `patchActiveConceptDrillOutcome()`, `recordInterleavingEvent()`, or `markNodeVisitedThisSession()`.
- Mutate `concept.graphData`, `drill_status`, `drill_phase`, `study_completed_at`, `re_drill_eligible_after`, `gap_type`, or `gap_description`.
- Treat `pre_confidences`, `lock_durations_ms`, or the calibration pairs as evidence of understanding.
- Display the calibration readout per-rep inline (only in the completion summary).
- Use judgmental labels in the calibration readout ("overconfident", "miscalibrated", "wrong"). Language stays observational.
- Route, filter, or prioritize nodes based on pre-confidence values. Scheduling is the re-drill system's job.
- Add a separate `Lock in` button. The single button `Lock in and show reference bridge` is the commitment point.
- Add a confirm modal, side-by-side diff view, or "I don't know yet" help path. Those are deferred.
- Rename or re-style the existing self-rating labels `Close match` / `Partly linked` / `Missed the link` or the stored values `close_match` / `partial` / `missed`.
- Persist full learner answer text, rep prompts, reference bridges, or AI feedback cues to localStorage. Answer lengths (counts, not text) remain allowed.
- Compute or display an aggregate calibration score.
- Rely on UI-disabled state as the reveal gate. `revealRepairRep()` itself validates preconditions.
- Change `/api/repair-reps`, `RepairRepsRequest`, `generate_repair_reps()`, `RepairRepsEvaluation`, or `app_prompts/repair-reps-system-v1.md`.
- Add manual JS `element.style.pointerEvents` mutations. Graph interactivity continues to flow through the existing `.mode-repair-reps` CSS gate.

---

## State Changes

### New or Modified State

`repairRepsState` gains these fields:

```
// Per-rep working fields (reset per rep)
repairRepsState.currentPreConfidence: "guessing" | "hunch" | "can_explain" | null = null
  - Stance for the current rep.
  - Set by setRepairRepPreConfidence().
  - Reset to null on startRepairReps() and nextRepairRep().

repairRepsState.currentAnswer: string = ""
  - Live textarea draft for the current rep.
  - Updated by the textarea input listener on every keystroke.
  - Reset to "" on startRepairReps() and nextRepairRep().

repairRepsState.repStartedAt: number | null = null
  - Timestamp (Date.now()) when the current rep became active.
  - Stamped on startRepairReps() for rep 1 and on nextRepairRep() for subsequent reps.
  - Used as the denominator for lock-duration calculation.

repairRepsState.lockedAt: number | null = null
  - Timestamp at reveal-button click for the current rep.
  - Set by revealRepairRep() inside the atomic reveal transition.
  - Reset to null on nextRepairRep() and startRepairReps().

// Accumulated per-rep arrays (grow across reps)
repairRepsState.preConfidences: Array<"guessing"|"hunch"|"can_explain"> = []
  - Pushed on each successful revealRepairRep().
  - Length matches completed-rep count.

repairRepsState.lockDurationsMs: Array<number> = []
  - Pushed on each successful revealRepairRep() as lockedAt - repStartedAt.
  - Length matches completed-rep count. Invariant: length === preConfidences.length === ratings.length at completion.
```

No existing state fields are renamed or repurposed. Existing `ratings`, `ratingSelected`, `currentIndex`, `revealed`, `status`, `answerLengths` are unchanged.

### New or Modified Functions

**`startRepairReps()`** (existing, in `public/js/app.js`):
Extend to initialize `preConfidences = []`, `lockDurationsMs = []`, `currentPreConfidence = null`, `currentAnswer = ""`, `lockedAt = null`, and stamp `repStartedAt = Date.now()`.

**`nextRepairRep()`** (existing, in `public/js/app.js`):
Extend to reset `currentPreConfidence = null`, `currentAnswer = ""`, `lockedAt = null`, and re-stamp `repStartedAt = Date.now()` before advancing `currentIndex`.

**`setRepairRepPreConfidence(value)`** (new, in `public/js/app.js`, exported on `window.SocratinkApp`):
```
setRepairRepPreConfidence(value: "guessing" | "hunch" | "can_explain")
  - Validate value is in the enum; otherwise no-op.
  - No-op if repairRepsState.revealed === true (pill frozen post-reveal).
  - Read current textarea.value into currentAnswer first, so the re-render
    caused by the state update does not wipe the draft.
  - setRepairRepsState({ currentPreConfidence: value, currentAnswer: latestValue }).
```

**`revealRepairRep(answer)`** (existing, in `public/js/app.js`):
Replace preconditions with:
```
  - If repairRepsState.revealed === true: no-op. (Idempotency.)
  - If repairRepsState.status !== "ready": no-op.
  - If typeof answer !== "string" or answer.trim().length === 0: no-op.
  - If repairRepsState.currentPreConfidence not in enum: no-op.
  - Stamp lockedAt = Date.now().
  - Push currentPreConfidence onto preConfidences.
  - Push (lockedAt - repStartedAt) onto lockDurationsMs.
  - Existing: push answer.trim().length onto answerLengths.
  - Set revealed = true, apply existing reveal path.
```

**`recordRepairRepsCompletion()`** (existing, in `public/js/app.js`):
Extend the persisted record to include `pre_confidences: [...preConfidences]` and `lock_durations_ms: [...lockDurationsMs]`. No other fields change.

**`repairRepsMarkupForNode(data, repairState = {})`** (existing, in `public/js/graph-view.js`):
Extend ready-before-reveal markup with the "Before you peek" pill section above `Your bridge`. Update the reveal button label to `Lock in and show reference bridge`. In revealed state, render the pill row with `aria-disabled="true"` and `.is-locked`. Textarea uses `value="${escHtml(state.currentAnswer || "")}"` so draft preservation re-render works. Extend complete-state markup with `repairCalibrationSummaryMarkup()`.

**`repairPredictPillsMarkup(currentPreConfidence, isLocked)`** (new, in `public/js/graph-view.js`):
Pure helper returning the three-pill `<div role="radiogroup">` markup with `aria-checked` reflecting selection and `aria-disabled` reflecting lock state. No state mutation.

**`repairCalibrationSummaryMarkup(preConfidences, ratings)`** (new, in `public/js/graph-view.js`):
Pure helper returning the per-rep `Rep N / Predicted: X / Rated: Y` rows. Handles missing/short arrays by rendering up to `min(length)` complete rows, or by omitting the block entirely if both arrays are empty. Uses fixed lookup tables for enum-to-label translation.

**`setRepairRepsState(patch)`** (existing):
No signature change. Must preserve existing behavior of merging patches and triggering re-render.

### Storage Schema

The existing `learnops_repair_reps_v1` key gains two additive arrays. Schema after this slice:

```json
{
  "concept_id::node_id": [
    {
      "completed_at": "2026-04-18T17:12:03.410Z",
      "rep_count": 3,
      "prompt_version": "repair-reps-system-v1",
      "gap_type": "mechanism",
      "answer_lengths": [42, 37, 51],
      "ratings": ["close_match", "partial", "missed"],
      "pre_confidences": ["guessing", "hunch", "can_explain"],
      "lock_durations_ms": [12000, 18000, 9000]
    }
  ]
}
```

**Explicit ban**: Full learner answers, rep prompts, reference bridges, and AI feedback cues MUST NOT be persisted to localStorage. Only confidence enum labels, lock durations, answer lengths (counts), ratings (enum labels), and the existing metadata are allowed. This preserves the privacy boundary already set by `answer_lengths`.

**Backward compatibility**: Readers must treat missing `pre_confidences` and `lock_durations_ms` as `[]`. No migration of old records. Length mismatches (legacy edge) are handled by rendering `min(length)` complete rows.

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
        <button type="button" class="graph-repair-predict-pill trigger-repair-predict" data-pre="guessing" role="radio" aria-checked="false">Guessing</button>
        <button type="button" class="graph-repair-predict-pill trigger-repair-predict" data-pre="hunch" role="radio" aria-checked="false">Have a hunch</button>
        <button type="button" class="graph-repair-predict-pill trigger-repair-predict" data-pre="can_explain" role="radio" aria-checked="false">Can explain</button>
      </div>
    </div>

    <div class="graph-detail-kicker">Your bridge</div>
    <textarea class="graph-repair-input" rows="4" aria-describedby="repair-reveal-helper">${escHtml(state.currentAnswer || "")}</textarea>
    <p class="graph-detail-copy graph-repair-helper">Trace the causal link in one or two sentences.</p>
  </section>
  <section class="graph-detail-surface graph-study-next graph-repair-next">
    <p class="graph-detail-copy graph-repair-truth-line">Practice only. Graph progress comes from re-drill.</p>
    <button class="btn-start-drill graph-detail-action trigger-repair-reveal" disabled aria-describedby="repair-reveal-helper">Lock in and show reference bridge</button>
    <p class="graph-repair-reveal-helper" id="repair-reveal-helper">Pick a stance and type your bridge to continue.</p>
  </section>
</div>
```

A selected pill carries `aria-checked="true"` and `.is-selected`. The aria-describedby helper names both requirements for the disabled button.

### Revealed State

Unchanged from Phase 1+2 focused-mode spec, with these additions:

- Pill row remains visible above `Your bridge` with the locked-in pill highlighted and the row marked `aria-disabled="true"` and class `.is-locked` (CSS sets `pointer-events: none` and `cursor: default` on children).
- Textarea is rendered with the `readonly` attribute.
- Self-rating row continues to use the existing `Close match` / `Partly linked` / `Missed the link` labels and `rateRepairRep()` handler from `docs/product/repair-reps-self-rating-spec.md`. No label changes.

No inline per-rep calibration readout is rendered in this state.

### Complete State

Produced by `repairRepsMarkupForNode()` in `public/js/graph-view.js`. Rating labels in the summary use the existing mapping: `close_match -> Close match`, `partial -> Partly linked`, `missed -> Missed the link`. Pre-confidence labels use: `guessing -> Guessing`, `hunch -> Have a hunch`, `can_explain -> Can explain`.

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
  <p class="graph-detail-copy">Three bridge reps saved on <node label>.</p>

  <div class="graph-repair-summary graph-repair-calibration">
    <div class="graph-repair-summary-row">
      <span class="graph-repair-summary-rep">Rep 1</span>
      <span class="graph-repair-summary-pair"><span class="muted">Predicted:</span> Have a hunch</span>
      <span class="graph-repair-summary-pair"><span class="muted">Rated:</span> Partly linked</span>
    </div>
    <div class="graph-repair-summary-row">...Rep 2...</div>
    <div class="graph-repair-summary-row">...Rep 3...</div>
  </div>

  <p class="graph-detail-copy">These reps are saved. Graph progress comes from the next re-drill.</p>
  <button class="btn-start-drill graph-detail-action trigger-repair-exit">Back to graph</button>
</div>
```

If `pre_confidences` is missing from a legacy record, render the rep row with `Predicted: Not recorded` OR omit the Predicted span entirely, per the Edge Cases rule.

### Event Listeners

| Selector | Event | Handler | Bound in |
|----------|-------|---------|----------|
| `.trigger-repair-predict` | `click` | `window.SocratinkApp?.setRepairRepPreConfidence?.(btn.dataset.pre)` | `renderCurrentDetail()` in `public/js/graph-view.js` |
| `.graph-repair-input` | `input` | `window.SocratinkApp?.setRepairRepsDraft?.(textarea.value)` (a thin wrapper that calls `setRepairRepsState({ currentAnswer: value })`) plus the existing enable/disable predicate that checks non-empty input AND non-null `currentPreConfidence` | `renderCurrentDetail()` in `public/js/graph-view.js` |
| `.trigger-repair-reveal` | `click` | `window.SocratinkApp?.revealRepairRep?.(textarea.value.trim())` (now gated inside the function, not only by button `disabled`) | `renderCurrentDetail()` in `public/js/graph-view.js` |
| `.trigger-repair-rate` | `click` | `window.SocratinkApp?.rateRepairRep?.(btn.dataset.rating)` (unchanged) | `renderCurrentDetail()` in `public/js/graph-view.js` |
| `.trigger-repair-next` | `click` | `window.SocratinkApp?.nextRepairRep?.()` (unchanged; reducer resets per-rep fields and restamps `repStartedAt`) | `renderCurrentDetail()` in `public/js/graph-view.js` |
| `.trigger-repair-exit` | `click` | `window.SocratinkApp?.exitRepairReps?.()` (unchanged) | `renderCurrentDetail()` in `public/js/graph-view.js` |

`setRepairRepsDraft` may be inlined if `setRepairRepsState` is already safe to call from a listener.

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

.graph-repair-predict-group.is-locked,
.graph-repair-predict-group[aria-disabled="true"] {
  pointer-events: none;
}
.graph-repair-predict-group.is-locked .graph-repair-predict-pill,
.graph-repair-predict-group[aria-disabled="true"] .graph-repair-predict-pill {
  cursor: default;
}

.graph-repair-reveal-helper {
  font-size: 11px;
  color: var(--text-sub);
  margin: 6px 0 0;
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

Animations continue to respect the existing reduced-motion override from the focused-mode spec.

---

## Prompt / AI Contract

None. This slice does not make new LLM calls and does not change `app_prompts/repair-reps-system-v1.md`, `RepairRepsEvaluation`, or `generate_repair_reps()`.

---

## Dependencies

**Requires**:
- Phase 1+2 focused-mode spec already implemented (`docs/product/repair-reps-focused-mode-spec.md`).
- Existing self-rating behavior with its labels and stored values (`docs/product/repair-reps-self-rating-spec.md`).
- Existing card-stack animation behavior (`docs/product/repair-reps-card-stack-spec.md`).
- Existing state machine: `startRepairReps()`, `repairRepsState`, `setRepairRepsState()`, `revealRepairRep()`, `rateRepairRep()`, `nextRepairRep()`, `exitRepairReps()`, `recordRepairRepsCompletion()`.

**Enables**:
- Future: calibration analytics tile (post-DB), split Claim/Mechanism fields, hedge detector, rep-dot hover explanations.

---

## Files Changed

| File | Change |
|------|--------|
| `public/js/graph-view.js` | Extend `repairRepsMarkupForNode()` ready and complete states. Add `repairPredictPillsMarkup()` and `repairCalibrationSummaryMarkup()` helpers. Extend listener binding for `.trigger-repair-predict` and extend the `.graph-repair-input` listener to update `currentAnswer`. Update reveal-enable predicate to require both conditions. Render textarea value from state for draft preservation. |
| `public/js/app.js` | Add `setRepairRepPreConfidence()` and `setRepairRepsDraft()` (or inline `setRepairRepsState` use). Extend `startRepairReps()` and `nextRepairRep()` reducer paths to initialize/reset per-rep fields and stamp `repStartedAt`. Extend `revealRepairRep()` preconditions (idempotency + pre-confidence requirement) and body (push to `preConfidences` / `lockDurationsMs`). Extend `recordRepairRepsCompletion()` persisted record. Export new handlers on `window.SocratinkApp`. |
| `public/css/layout.css` | Add `.graph-repair-predict`, `.graph-repair-predict-group`, `.graph-repair-predict-pill`, `.graph-repair-reveal-helper`, `.graph-repair-calibration` rules. Respect reduced-motion. |
| `main.py` | None. |
| `ai_service.py` | None. |
| `app_prompts/*` | None. |
| `docs/product/repair-reps-focused-mode-spec.md` | None - this slice extends, does not replace. |
| `docs/product/repair-reps-self-rating-spec.md` | None - labels and values are consumed as-is. |

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

1. **Pill renders**: Open Repair Reps on an eligible node. "Before you peek" kicker and three pills render above "Your bridge". No pill selected. Reveal button disabled. Helper text reads `Pick a stance and type your bridge to continue.`
2. **Textarea independent of pill**: Type before selecting a pill. Helper copy remains visible. Reveal button stays disabled.
3. **Pill-first flow**: Select `Have a hunch`. Pill highlights with `aria-checked="true"`. Textarea still empty. Reveal button stays disabled.
4. **Type-then-pill draft preservation**: Type `test draft`, THEN select `Guessing`. Verify the textarea still reads `test draft` after the re-render. This is the draft-preservation test.
5. **Both satisfied**: Pill + non-empty trimmed attempt. Reveal button enables.
6. **Clear textarea**: Clear after enabling. Reveal button re-disables. Pill selection persists.
7. **Change pill pre-reveal**: Select different pill. Highlight moves. Reveal stays enabled.
8. **Single-click reveal**: Click `Lock in and show reference bridge`. Textarea becomes `readonly`. Pill row gets `aria-disabled="true"` and `.is-locked`; clicking pills now does nothing. Reference unfolds. Self-rating row (`Close match` / `Partly linked` / `Missed the link`) appears.
9. **Post-reveal pill attempt**: Click pills after reveal. Nothing happens (pointer-events:none).
10. **Direct revealRepairRep bypass test (console)**: From DevTools, call `window.SocratinkApp.revealRepairRep("something")` BEFORE selecting a pill. Reveal does NOT happen. Then call it again AFTER selecting a pill with a non-empty answer - reveal does happen.
11. **Idempotency**: After reveal, call `window.SocratinkApp.revealRepairRep(...)` again from DevTools. Assert `lockedAt`, `preConfidences`, and `lockDurationsMs` are each written exactly once for this rep.
12. **Lock duration**: Use DevTools to confirm `lockedAt - repStartedAt > 0` and that `repStartedAt` resets on `nextRepairRep()`.
13. **Complete 3 reps**: Progress through all three with different predicted/rated combinations (at least one of each enum).
14. **Completion summary**: Three rows with `Rep N` / `Predicted: <label>` / `Rated: <label>` using the fixed label map. Language observational, no "overconfident" / "miscalibrated". "These reps are saved. Graph progress comes from the next re-drill." visible below the summary.
15. **localStorage record**: Inspect `localStorage.learnops_repair_reps_v1`. Completion record has `pre_confidences` (length 3), `lock_durations_ms` (length 3, all positive integers), alongside existing `ratings`, `answer_lengths`. No `answer`, `prompt`, `target_bridge`, or `feedback_cue` fields present.
16. **Old record backward compat**: Inject a pre-slice-B record (without the two new arrays) into localStorage and re-open Repair Reps on a completed node if the UI surfaces history. Rendering must not crash. Calibration section either omits the rows entirely or renders `Predicted: Not recorded`.
17. **Length-mismatch legacy**: Inject a record with `pre_confidences.length === 2` but `ratings.length === 3`. Summary renders 2 complete rows, no crash.
18. **Exit**: `Back to graph` releases focused mode. State resets.
19. **Reduced motion**: Pill transitions, reveal animation, card-stack animations all suppressed under `prefers-reduced-motion: reduce`.
20. **A11y**: Tab cycles into the pill group. Pills are keyboard activatable via Space/Enter. Selected pill has `aria-checked="true"`. Disabled reveal button announces helper text via `aria-describedby`.

### Regression

- `python -m unittest tests.test_app_prompts tests.test_repair_reps -v` passes.
- `python -m unittest discover -s tests -v` passes (call out pre-existing telemetry failures if still present).
- Normal graph inspect, study, post-drill, cold-attempt-active, and re-drill-active modes retain their existing layouts.
- `patchActiveConceptDrillOutcome`, `recordInterleavingEvent`, and `markNodeVisitedThisSession` do not appear in any new Repair Reps call path.

---

## Constraints Checklist

1. Does it preserve the three-phase loop? **Yes** - Repair Reps remains optional practice outside cold attempt, study, and scored re-drill transitions.
2. Does it make the current target and phase clearer? **Yes** - the pre-reveal pill names the stance; the calibration summary names the gap at completion.
3. Does it reward real reconstruction or buffer echo? **Yes** - the reveal gate requires a non-empty attempt AND a committed stance, enforced in `revealRepairRep()`.
4. Does the AI support the loop or replace the thinking? **Yes** - the reference bridge still appears only after learner generation and still does not score the answer.
5. Does it frame difficulty as exploration or evaluation? **Yes** - `Predicted / Rated` is observational; no judgmental labels.
6. Does the graph tell the truth? **Yes** - no graph mutation paths are touched; pre-confidence is practice metadata, not progress evidence.
7. Would the learner still choose this behavior if they knew how the system influenced them? **Yes** - the pill is a low-cost stance; the gate is explicit via button label and helper text; the completion readout is observational.

---

## Agent Routing

| Phase | Owner | Action |
|-------|-------|--------|
| Spec review | **elliot** | Validate that Slice B does not conflict with focused-mode, card-stack, or self-rating specs and that copy preserves graph truth. |
| Gap analysis | **praxis:gap-analysis** | 7-check pass (inversion, second-order, MECE, map vs territory, adversarial, simplicity, reversibility) before writing-plans is invoked. |
| Plan writing | **superpowers:writing-plans** | Turn this spec into an ordered implementation plan with TDD checkpoints. |
| Implementation | **socratinker** via **gm** | PLAN -> EXECUTE -> EMIT -> VERIFY -> COMPLETE state machine. Order: state additions + reducer, markup helpers, listeners, CSS, storage-write extension, manual browser flow. |
| QA / release gate | **thurman** | Run the automated checks and full manual browser flow; verify backward-compat localStorage read, idempotency, direct-call bypass, draft preservation, and `prefers-reduced-motion`. |
| Post-implementation review | **glenna** | Review whether the multi-agent handoff kept role boundaries clear and whether the final implementation followed the slice scope without creep into deferred P0-P3 items. |
