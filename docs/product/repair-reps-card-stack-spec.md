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
