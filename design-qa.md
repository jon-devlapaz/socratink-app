# Desk reconstruction instrument — design QA

Date: 2026-07-12

## Visual proof

- Rejected first implementation: `.qa-runs/desk-reconstruction-instrument/final-tactile-390x844.png`
- Refined mobile capture: `.qa-runs/desk-reconstruction-instrument/revision-refined-390x844.png`
- Narrow mobile capture: `.qa-runs/desk-reconstruction-instrument/revision-refined-320x720.png`
- Rejected/refined comparison: `.qa-runs/desk-reconstruction-instrument/rejected-vs-refined-390x844.png`

### Occupied Desk Library frame

- Source visual: `/Users/jondev/dev/socratink/prod/socratink-app-library-session-index/.qa-runs/library-session-index/after-empty-390x844.png`
- Implementation visual: `.qa-runs/desk-library-frame/final-occupied-artifacts/tests-e2e-test-smoke-py-test-desk-board-expands-after-first-saved-session-chromium/test-finished-1.png`
- Full-view comparison: `.qa-runs/desk-library-frame/final-library-vs-desk-390x844.png`
- State and viewport: Library empty and Desk with one concept, both at 390×844.
- No separate crop is needed. The complete index frame fits in the shared viewport, and a crop would hide the page and navigation alignment used for comparison.
- First comparison found the crystal tip and glow too close to the index divider. Increasing the occupied board's top margin from 20px to 32px restored a quiet boundary without shrinking the instrument.
- The final comparison has no visible border, radius, gutter, title-scale, index-row, or overflow mismatch that blocks this slice.

## Viewport checks

- 320×720: helper wraps naturally; the plate stays inside the viewport and above navigation.
- 390×844: one 184–200px reconstruction plate occupies a balanced central field.
- 1280×720: the empty Desk fits without an inner scrollbar.
- The mobile hamburger is suppressed only on the empty Desk and returns on the Door and populated Desk.

## Contract checks

- A completely empty Desk exposes one accessible `Choose a topic` action; eight future-capacity sockets are hidden and inert.
- The action opens the existing Door. A saved session restores the existing 3×3 board.
- Partial Desk empty slots remain actionable; populated and Ready/due behavior is unchanged.
- Tile state may retain documented legacy visual compatibility, but evidence descriptions appear only when persisted training attempts support them.
- Keyboard and forced-colors focus remain visible; active destinations expose `aria-current="page"`.
- No scores, mastery/completion language, diagnostic labels, study-before-attempt content, or fabricated training evidence were added.

## Review gates

- Initial adversarial Taste Gate: rejected at 18/40; the nine-slot first-use board was ornamental capacity rather than a learning instrument.
- Intermediate independent Taste Gate: rejected at 22/40; the single plate was too small, the tap outcome was ambiguous, and mobile chrome competed with the task.
- Final independent Taste Gate: passed at 34/40 with low cognitive load, no AI-slop verdict, and no remaining P1/P2 issues.
- Final independent code/contract gate: passed with no P1/P2 regressions.
- Focused unit, browser-contract, and Desk E2E checks pass; `scripts/doctor.sh`, diff whitespace, and worktree guard are clean.

User approval remains open.

final result: passed
