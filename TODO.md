# TODO

Pre-build cleanup tasks. Recommended order: #2 → #1 → #3.

---

## #1 Fix: `present()` doesn't persist state

### Problem
`present()` updates UI text and enables the Drill button but never calls `setState()`. On reload, the crystal stays `growing` and Drill reverts to disabled — the stage-2 transition is invisible to the data model.

### Decision needed first
Choose one of two approaches:
- **Option A (add a state):** Add `presented` to the state machine (STATES config, GEO shape if needed, CSS selectors, `applyControlsForState`). `present()` calls `setState('presented')`.
- **Option B (collapse the step):** Remove the intermediate Present step. `extract()` transitions to `growing` and enables Drill directly. Present becomes a no-op button or is removed entirely.

For an MVP prototype, Option B is likely correct — Present has no distinct visual state and no data meaning today.

### Steps (if Option B)
1. Remove the `present()` function and the "2. Present" button from the HTML.
2. In `extract()`, call `setButtons(false, false, true)` after `setState('growing')` so Drill is immediately available.
3. Remove the `present` case from `applyControlsForState` (currently `growing` enables Present — change to enable Drill instead).
4. Update `STATES['growing'].desc` to reflect that drill is now available.
5. Verify reload after Extract shows Drill enabled.

---

## #2 Fix: delete `_activeState` shadow variable

### Problem
`_activeState` is a module-level variable that duplicates what's already in localStorage. It's set in `setState` and `applyControlsForState`, and read in exactly one place: `drillPass()` to detect if the prior state was `fractured` (to trigger the repair animation). It can drift out of sync with the real store.

### Steps
1. In `drillPass()`, replace:
   ```js
   const fromFractured = _activeState === 'fractured';
   ```
   with:
   ```js
   const fromFractured = getActiveConcept()?.state === 'fractured';
   ```
   This line must run **before** `setState('growing')` is called (which overwrites the stored state).

2. Delete the `let _activeState = null;` declaration.
3. Remove every assignment to `_activeState` (in `setState`, `applyControlsForState`, and `showEmptyState`).
4. Verify the repair animation still plays when drilling from a fractured state.

---

## #3 Fix: unify state transition path (`setState` should own control updates)

### Problem
Control update logic lives in two places:
- `applyControlsForState` — used when restoring from localStorage on load/select
- Inline `showControls` + `setButtons` calls after each `setState` in pipeline handlers

Adding or changing any state requires updating both paths. They can silently diverge.

### Steps
1. At the end of `setState(newState)`, add a call to `applyControlsForState(newState, getActiveConcept())`.
2. Remove the redundant `showControls(...)` and `setButtons(...)` calls from each pipeline handler:
   - `extract()` — remove the two lines after `playAnim`
   - `drillFail()` — remove `showControls` + `setButtons` + btn-drill label override (`applyControlsForState` handles the label for `fractured`)
   - `drillPass()` — remove `showControls` + `setButtons`
   - `consolidate()` — remove `showControls` + `startTimer` (`applyControlsForState` already handles hibernating)
3. Each handler should now only call `setState(newState)` (+ `playAnim` for animation). Nothing more.
4. Verify all state transitions still show the correct buttons and timer behavior.

### Watch out
- `consolidate()` sets `timerStart` on the concept **before** calling `setState`. That order must be preserved so `applyControlsForState` reads the correct `timerStart` when computing remaining time.
- `drillPass()` needs to read `fromFractured` before `setState` overwrites the stored state (see #2).
