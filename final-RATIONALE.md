# motion/claude — final rationale

## What changed

**Stripped 5 untethered ambient animations** (`ag-bg-breathe`, `ag-orb-drift-a`, `ag-orb-drift-b`, `ag-grid-halo`, `ag-dot-pulse`). All five violated DESIGN.md §12 ("everything else lives at 140 / 220 / 320ms. No 1s+ animations") and were flagged in the persona test as "AI startup landing page" decoration. Their visual elements stay (the orb blobs, the grid halo glow, the eyebrow dot, the page gradient) — they just don't move anymore. Static atmosphere over animated theater.

**Deleted dead `.ignition-eyebrow` CSS** (5 rule blocks). No element in the markup carries that class.

**Added one earned-motion moment** — the ignition handoff. When `App.showLaunchPad()` mounts the launch-pad view (the result of the learner committing to a concept on the door), `launch-pad.js` adds `ag-lp-arriving` to `#launch-pad-view` for one paint frame. The CSS block (`public/antigravity.css` end-of-file) runs a staggered fade-up reveal:

| Element | Delay | Duration |
|---|---|---|
| `.launch-pad-concept-name` | 0ms | 320ms |
| `.launch-pad-title` | 80ms | 320ms |
| `.launch-pad-helper` | 160ms | 320ms |
| `.launch-pad-form` | 240ms | 320ms |
| `.launch-pad-footer` | 320ms | 320ms |

Each fades from `opacity: 0; translateY(8px)` to `opacity: 1; translateY(0)` on `cubic-bezier(0.16, 0.84, 0.44, 1)` (ease-out-expo-ish). Total stagger window: 640ms. Not an infinite loop; runs once per mount, the JS removes the class after 700ms so re-mounts re-trigger cleanly.

This is the wonder moment the user asked for. It's tied to a real event (the commitment to a concept). Reduced-motion `@media` AND `html[data-motion="reduced"]` both suppress it — elements snap to end-state.

**Added forced-colors fallback for `.ig-highlight`** so the underlined "understand" headline survives Windows high-contrast.

## §12 exceptions taken

None. The new animation is 320ms per element (top of the §12 budget). The stagger isn't a single 640ms animation — it's five 320ms animations with 80ms-spaced delays. That's exactly the §12 model: short individual durations, sequenced rather than extended.

## Strongest move

The trade. Every one of the PR's six animations was *infinite* and *event-untethered* — the page kept breathing whether the learner was active or away. This patch swaps that for *one* finite, *event-coupled* moment: the launch pad's arrival. The persona feedback was clear that decorative motion read as v0 reflex; this rewrites the motion budget around state changes the learner can feel.

The visual atmosphere (gradient blooms, orb blobs, grid halo) is preserved — they just don't move. This is the "warm light through paper, not Instagram filter" register that DESIGN.md §12 names verbatim.

## TODO if more time

- Locus B (threshold absorption on submit) and locus C (provisional graph reveal) would extend the same earned-motion logic to the next two beats of the create flow. Out of scope here; would land cleanest as a separate commit so the diff stays reviewable.
- The static atmospheric blobs and halo could be replaced with an SVG noise layer for a subtler reading-room effect — but that's a §12-exception conversation, not a clean-up.

## Files touched

- `public/antigravity.css` — strip 5 animations + delete dead `.ignition-eyebrow` + add `ag-lp-arrival` keyframes + a11y blocks
- `public/js/launch-pad.js` — add `ag-lp-arriving` class on mount, remove after 700ms
- `public/index.html` — bump `antigravity.css?v=7`
