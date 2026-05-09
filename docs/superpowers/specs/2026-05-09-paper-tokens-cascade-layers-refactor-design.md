# Paper Wave 0 — cascade-layer infrastructure + paper tokens

**Status:** ready for plan
**Owner:** Jon
**Created:** 2026-05-09
**Last revised:** 2026-05-09 — corrected after a fresh-subagent verification pass; original draft assumed a parallel token system that conflicted with the existing `public/css/variables.css`.
**Type:** pure refactor — zero visible change
**Umbrella:** `2026-05-09-paper-migration-plan.md`
**Next wave:** `2026-05-09-ignition-paper-redesign-design.md`

## Goal

Install CSS Cascade Layer infrastructure around the existing stylesheet structure and add the two paper-specific tokens needed by Wave 1. Every existing view stays pixel-identical. Reviewers can verify by toggling between `main` and the PR branch and seeing nothing move.

## What this wave does

1. Add two new tokens to the existing `public/css/variables.css` primitive section: `--rule-line` and `--rule-step`.
2. Create `public/css/index.css` — a small import-orchestrator that declares cascade-layer order (`@layer components, legacy, paper`) and `@imports` the existing `styles.css` and `antigravity.css` into their layers.
3. Replace the two `<link rel="stylesheet">` tags in `public/index.html` with one `<link>` to `/css/index.css`.

## What this wave does NOT do

- Does not create a parallel `tokens.css`. The existing `public/css/tokens.css` (login-safe font subset) stays byte-identical.
- Does not change `public/css/layout.css`, `public/css/components.css`, `public/css/base.css`, `public/css/crystal.css`, or any of `public/styles.css`'s import chain.
- Does not delete any rule from `antigravity.css`.
- Does not change any HTML markup outside the `<link>` swap.
- Does not change any JS.
- Does not introduce any token names other than `--rule-line` and `--rule-step`. New components introduced in Wave 1 reuse the existing semantic tokens (`--surface-page`, `--surface-card`, `--text-strong`, `--text-muted`, `--accent-primary`, `--primary-fill`, `--border-subtle`, `--border-strong`, `--shadow-card`, `--font-display`, `--font-body`, `--text-{xs..3xl}`, `--space-{1..12}`, `--radius-btn`, `--radius-card`, `--ease-standard`, `--duration-{micro,quick,cozy}`, `--accent-ring`).

## File-level changes

### `public/css/variables.css` — token additions only

Add the following two declarations to the existing primitive section (near `--border-subtle`, around variables.css line 58):

```css
/* Paper-system additions (Paper Wave 0) — used by ruled-paper composer
   in the Ignition + Launch Pad views. See:
   docs/superpowers/specs/2026-05-09-ignition-paper-redesign-design.md */
--rule-line: rgba(var(--ink-900-rgb), 0.07);
--rule-step: 32px;
```

The dark-mode override section (`[data-theme="dark"]` starting around line 453) needs a paired override:

```css
--rule-line: rgba(var(--cream-50-rgb), 0.10);
```

`--rule-step` does not need a dark-mode override (it's a length, not a color).

### `public/css/index.css` (new)

```css
/* ════════════════════════════════════════════════════════════════════
   index.css — Single import root for the app stylesheet bundle.
   Declares cascade-layer order; imports the existing styles.css chain
   and the antigravity overlay into their respective layers, plus
   reserves a 'paper' layer for Wave 1+ to introduce new component
   rules that beat the antigravity overlay.

   Layer order (later wins regardless of selector specificity):
     components — base layout/components/etc. via styles.css chain
     legacy     — antigravity.css; wins over components on every
                  unmigrated view, exactly as before
     paper      — reserved; first consumed in Paper Wave 1

   Cache-busting query strings on @imports preserve the prior link-tag
   versioning behavior. Bump them when shipping a stylesheet update.

   See docs/superpowers/specs/2026-05-09-paper-tokens-cascade-layers-refactor-design.md
   ════════════════════════════════════════════════════════════════════ */

@layer components, legacy, paper;

@import url('../styles.css?v=85')      layer(components);
@import url('../antigravity.css?v=13') layer(legacy);
/* @import url('paper.css') layer(paper);  — reserved; introduced in Wave 1 */
```

The version strings (`?v=85`, `?v=13`) match the values currently on the `<link>` tags in `public/index.html`. Keep them in sync with whatever versioning workflow the project uses.

### `public/index.html` change

Replace the existing two `<link rel="stylesheet">` tags (currently around lines 26–27):

```html
<link rel="stylesheet" href="styles.css?v=85">
<link rel="stylesheet" href="antigravity.css?v=13">
```

With one:

```html
<link rel="stylesheet" href="/css/index.css?v=1">
```

(The `?v=1` is a fresh version pin for the new file. Subsequent edits to `index.css` should bump it.)

### Files NOT changed

- `public/styles.css` — unchanged. Still chains 8 imports.
- `public/antigravity.css` — unchanged. Still 1955 lines. Wrapped via `layer(legacy)` in `index.css`'s `@import`, not by editing the file.
- `public/css/tokens.css` — unchanged. Still the login-safe font-loader subset.
- All 8 files in `styles.css`'s import chain — unchanged.

## Acceptance criteria

1. `git diff main -- public/styles.css public/antigravity.css public/css/tokens.css public/css/base.css public/css/crystal.css public/css/components.css public/css/layout.css public/css/board-first.css public/css/approach-reveals.css public/css/iso-board-state-surface.css` shows zero changes to any of those files.
2. `git diff main -- public/css/variables.css` shows ONLY the two `--rule-line` declarations and `--rule-step` declaration added; no other lines changed.
3. `public/css/index.css` exists, parses cleanly, and contains exactly the layer declaration and three `@import` lines (one commented).
4. `public/index.html` has exactly one stylesheet `<link>` in `<head>`, pointing to `/css/index.css?v=1`.
5. **Browser smoke** (`bash scripts/qa-smoke.sh local`) passes against current `dev` HEAD.
6. **Manual visual diff (light + dark mode):** dashboard, ignition view, library view, settings view, login page — each pixel-identical to `main`.
7. **DevTools cascade-layer verification:** inspect any `body.antigravity-theme` rule in the dashboard. The DevTools cascade pane shows `@layer legacy` as the source layer, listed *after* `@layer components` (later layer wins).
8. **Network panel verification:** all stylesheets in the import chain load with HTTP 200.
9. **Console clean:** zero errors and zero new CSS-parse warnings on every view, both themes.

## Browser support

Cascade Layers are universally supported as of Chrome 99 / Firefox 97 / Safari 15.4 / Edge 99 (all early 2022). If support older than this is required, fall back to a specificity-bump approach in Wave 1 instead of cascade layers.

## Failure modes and rollback

- Visual regression on any view → `git revert` the PR (restores the two `<link>` tags and removes the new files / token additions).
- Network 404 on a child stylesheet → `@import` path resolution issue. Verify `public/css/index.css`'s `../styles.css` and `../antigravity.css` paths are correct.
- Antigravity rules suddenly fail to apply → cascade-layer ordering bug; confirm `@layer components, legacy, paper;` order and that antigravity.css imports with `layer(legacy)`.

## Out-of-scope (deferred to Wave 1+)

- Any new component CSS using the tokens.
- Any markup change to `#ignition-view`, `#launch-pad-view`, the witness anchor, the composer card, etc.
- Any `app.js` or `launch-pad.js` change.
- Renaming `antigravity.css` (we delete it eventually, never rename it).
- Touching the `--bg`, `--card-bg`, `--text`, `--text-sub` legacy aliases in variables.css — that's a separate (unrelated) Wave-2 sweep already documented in variables.css.

## Verification command summary

```bash
# From repo root, after edits:
bash scripts/qa-smoke.sh local                          # smoke pass
git diff main -- public/styles.css public/antigravity.css public/css/tokens.css public/css/base.css public/css/crystal.css public/css/components.css public/css/layout.css   # zero
git diff main -- public/css/variables.css               # only the additions
git diff main -- public/index.html                      # only the <link> swap
ls public/css/index.css                                  # exists
```
