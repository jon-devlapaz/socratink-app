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
