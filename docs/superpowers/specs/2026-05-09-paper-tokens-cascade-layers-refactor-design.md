# Wave 0 — Paper tokens + cascade layers refactor

**Status:** ready for plan
**Owner:** Jon
**Created:** 2026-05-09
**Type:** pure refactor — zero visible change
**Umbrella:** `2026-05-09-paper-migration-plan.md`
**Next wave:** `2026-05-09-ignition-paper-redesign-design.md`

## Goal

Install the foundation that future paper-migration waves will use. No view changes. No new visual treatments. Every existing screen looks pixel-identical after this PR. Reviewers can verify by toggling between `main` and the PR branch and seeing nothing move.

## What this wave does

1. Add `public/css/tokens.css` — primitive + semantic design tokens for the paper system, with `html[data-theme="dark"]` semantic overrides for night paper.
2. Add `public/css/index.css` — single import root that declares cascade-layer order and pulls every stylesheet into its layer.
3. Wrap `public/antigravity.css` in `@layer legacy` so future paper rules win without specificity bumping.
4. Place `public/css/layout.css`, `public/css/components.css`, `public/styles.css` into `@layer components` / `@layer utilities`.
5. Replace the four `<link rel="stylesheet">` tags in `public/index.html` with one pointing to `index.css`.

## What this wave does NOT do

- Does not add any new component CSS rule. Tokens exist but no selector references them yet.
- Does not delete any rule from `antigravity.css`.
- Does not change any HTML markup outside the `<link>` swap.
- Does not change any JS.

## File-level changes

### `public/css/tokens.css` (new)

```css
:root {
  /* ── Color primitives ──────────────────────────────────────── */
  --violet-700: #6f4da1;
  --violet-500: #9067c6;
  --violet-300: #c8a8f7;
  --paper-warm: #fbfaf7;
  --page-cool: #f2f0f5;
  --ink-900: #242038;
  --ink-700: #514b66;
  --ink-500: #66617d;          /* AA Normal (4.91:1) over --paper-warm */
  --graphite-900: #18181b;
  --graphite-800: #1c1c20;
  --paper-night-100: #f2f0f5;
  --paper-night-300: #c9c5d4;
  --paper-night-500: rgba(242,240,245,0.55);
  --line-15: rgba(36,32,56,0.15);
  --line-28: rgba(36,32,56,0.28);
  --line-night-16: rgba(242,240,245,0.16);
  --line-night-28: rgba(242,240,245,0.28);
  --rule-line-light: rgba(36,32,56,0.07);
  --rule-line-night: rgba(242,240,245,0.10);

  /* ── Typography ────────────────────────────────────────────── */
  --font-body: "Geom", "Outfit", "Inter", ui-sans-serif, system-ui, sans-serif;
  --font-display: "Geom", "Outfit", "Inter", ui-sans-serif, system-ui, sans-serif;
  --text-xs: 12px;   --leading-xs: 1.45;
  --text-sm: 13px;   --leading-sm: 1.55;
  --text-md: 15px;   --leading-md: 1.55;
  --text-lg: 17px;   --leading-lg: 1.55;
  --text-xl: 21px;   --leading-xl: 1.55;
  --text-display: clamp(28px, 3.6vw, 38px);  --leading-display: 1.05;
  --weight-regular: 400;
  --weight-medium: 600;
  --weight-bold: 760;

  /* ── Spacing ───────────────────────────────────────────────── */
  --space-1: 4px;   --space-2: 8px;   --space-3: 12px;
  --space-4: 16px;  --space-5: 22px;  --space-6: 28px;
  --space-7: 34px;  --space-8: 48px;
  --rule-step: 32px;

  /* ── Radius + shadow ───────────────────────────────────────── */
  --radius-paper: 8px;
  --radius-pill: 999px;
  --shadow-paper: 0 18px 48px rgba(36,32,56,0.10);
  --shadow-paper-night: 0 18px 48px rgba(0,0,0,0.55);
  --shadow-button-hover: 0 4px 12px rgba(144,103,198,0.25);

  /* ── Motion ────────────────────────────────────────────────── */
  --duration-micro: 140ms;
  --duration-fast: 220ms;
  --duration-medium: 320ms;
  --ease-standard: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-out: cubic-bezier(0.2, 0.7, 0.3, 1);

  /* ── Focus ─────────────────────────────────────────────────── */
  --focus-ring-color: rgba(144,103,198,0.55);
  --focus-ring-width: 2px;

  /* ── Z-index scale ─────────────────────────────────────────── */
  --z-below: -1;
  --z-base: 0;
  --z-content: 1;
  --z-overlay: 10;
  --z-dropdown: 50;
  --z-modal: 100;
  --z-toast: 200;
}

/* ── Semantic — light default ──────────────────────────────── */
:root {
  --surface-page: var(--page-cool);
  --surface-paper: var(--paper-warm);
  --surface-rule: var(--rule-line-light);
  --ink: var(--ink-900);
  --ink-soft: var(--ink-700);
  --ink-faint: var(--ink-500);
  --accent: var(--violet-500);
  --accent-deep: var(--violet-700);
  --line: var(--line-15);
  --line-strong: var(--line-28);
  --shadow-card: var(--shadow-paper);
  --focus-ring: 0 0 0 var(--focus-ring-width) var(--focus-ring-color);
}

/* ── Semantic — night paper override ───────────────────────── */
html[data-theme="dark"] {
  --surface-page: var(--graphite-900);
  --surface-paper: var(--graphite-800);
  --surface-rule: var(--rule-line-night);
  --ink: var(--paper-night-100);
  --ink-soft: var(--paper-night-300);
  --ink-faint: var(--paper-night-500);
  --accent: var(--violet-300);
  --accent-deep: var(--violet-300);
  --line: var(--line-night-16);
  --line-strong: var(--line-night-28);
  --shadow-card: var(--shadow-paper-night);
}
```

### `public/css/index.css` (new)

```css
@layer tokens, components, utilities, legacy, paper;

@import url('tokens.css')         layer(tokens);
@import url('layout.css')         layer(components);
@import url('components.css')     layer(components);
@import url('../styles.css')      layer(utilities);
@import url('../antigravity.css') layer(legacy);
/* paper layer reserved for Wave 1; no import yet */
```

**Layer order is critical and must match this exactly.** In CSS Cascade Layers, *later layers win over earlier layers regardless of selector specificity*. The order above preserves current cascade behavior on every unmigrated view:

- `tokens` (layer 1) — only `:root` custom property declarations, no rules with side effects.
- `components` (layer 2) — base component styles in `layout.css` and `components.css`.
- `utilities` (layer 3) — `styles.css` glue.
- `legacy` (layer 4) — `antigravity.css`. Loads later than `components`, so its `body.antigravity-theme …` theme overrides still beat the base components, exactly as in the pre-migration cascade.
- `paper` (layer 5) — reserved. Wave 1 introduces `paper.css` here. Paper rules will beat `legacy`, which is exactly what we want for migrated surfaces.

If the order were `tokens, legacy, components, utilities` (legacy before components), `components.css` would override every antigravity theme rule on the dashboard, library, and settings — instantly violating the "zero visible change" mandate of this wave. **Do not flip this order.**

### `public/index.html` change

```html
<!-- Replace these four lines: -->
<link rel="stylesheet" href="/css/layout.css">
<link rel="stylesheet" href="/css/components.css">
<link rel="stylesheet" href="/styles.css">
<link rel="stylesheet" href="/antigravity.css">

<!-- With this one: -->
<link rel="stylesheet" href="/css/index.css">
```

### `public/antigravity.css` (no content change)

Wrap the entire content in `@layer legacy`? **No.** The `@import` in `index.css` does the wrapping (`@import url('../antigravity.css') layer(legacy)`). The file's content stays byte-identical. Reviewers can verify with `git diff` showing the file unchanged.

### `public/css/layout.css`, `public/css/components.css`, `public/styles.css` (no content change)

Same — assigned to layers via the import statement, files themselves unchanged.

## Acceptance criteria

1. `git diff public/antigravity.css public/css/layout.css public/css/components.css public/styles.css` shows zero changes.
2. `public/index.html` `<head>` carries exactly one stylesheet `<link>`, pointing to `/css/index.css`.
3. `public/css/tokens.css` and `public/css/index.css` exist and parse cleanly.
4. **Browser smoke** (`bash scripts/qa-smoke.sh local`) passes against `dev` HEAD.
5. **Manual visual verification:** open the dashboard, ignition view, library view, settings view in light AND dark mode. Each view is pixel-identical to `main`. (Open both branches in two browser windows side by side.)
6. **DevTools cascade panel verification:** inspect any `.hero-card` rule on the dashboard. Confirm `@layer legacy` is shown as the source layer in DevTools' Computed > Cascade pane, and that it sits *above* `@layer components` in the layer-order display (later layer wins).
7. **No console errors** in any view, light or dark.

## Browser support

Cascade Layers are universally supported as of:

- Chrome 99+ (March 2022)
- Firefox 97+ (February 2022)
- Safari 15.4+ (March 2022)
- Edge 99+ (March 2022)

If support older than this is required, fall back to the audit-and-bump-specificity approach. Default assumption: not required.

## Failure modes and rollback

- If any view regresses visually, the rollback is `git revert` of the single PR — restores the four `<link>` tags and deletes the two new CSS files.
- If a stylesheet fails to load (e.g., `@import` path wrong), `index.css` will silently miss it. Manual verification (#3 above) catches this before merge.
- If `body.antigravity-theme` selectors stop applying because of a layer ordering bug, every dashboard/library/settings view loses its theme. Manual verification (#5) catches this immediately.

## Out-of-scope (deferred to Wave 1+)

- Any new component CSS using the tokens.
- Any markup change to `#ignition-view`, `#launch-pad-view`, the witness anchor, the composer card, etc.
- Any `app.js` or `launch-pad.js` change.
- Renaming `antigravity.css` (we delete it eventually, never rename it).

## Verification command summary

```bash
# From repo root
bash scripts/qa-smoke.sh local           # smoke pass
git diff main -- public/antigravity.css   # zero
git diff main -- public/css/layout.css    # zero
git diff main -- public/css/components.css # zero
git diff main -- public/styles.css         # zero
git diff main -- public/index.html         # only the <link> swap
ls public/css/tokens.css public/css/index.css  # both exist
```
