# Wave 0 — Paper tokens + cascade layers refactor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install design-token + cascade-layer infrastructure with zero visible change to any view.

**Architecture:** Add `public/css/tokens.css` (primitives + semantic + dark overrides), add `public/css/index.css` as the single import root declaring `@layer tokens, components, utilities, legacy, paper`, replace four `<link>` tags in `public/index.html` with one. No new component CSS. No HTML or JS changes outside the `<link>` swap.

**Tech Stack:** Vanilla CSS (no build step), CSS Custom Properties, CSS Cascade Layers (`@layer`, `@import … layer(name)`), FastAPI static-file serving via `public/`.

**Spec:** `docs/superpowers/specs/2026-05-09-paper-tokens-cascade-layers-refactor-design.md`

**Umbrella:** `docs/superpowers/specs/2026-05-09-paper-migration-plan.md`

**Branch:** Work on `dev`. Commit straight to `dev` per project convention.

---

## File structure

| File | Action | Responsibility |
|---|---|---|
| `public/css/tokens.css` | **create** | Primitive + semantic design tokens. Light is default; `html[data-theme="dark"]` overrides semantic mappings for night paper. No selectors with side effects. |
| `public/css/index.css` | **create** | Single import root. Declares cascade-layer order. Imports all stylesheets into their assigned layers. |
| `public/index.html` | **modify** | Replace four `<link rel="stylesheet">` tags with one pointing to `/css/index.css`. |
| `public/antigravity.css` | **untouched** | Wrapped via `@import … layer(legacy)` in `index.css`; file content stays byte-identical. |
| `public/css/layout.css`, `public/css/components.css`, `public/styles.css` | **untouched** | Assigned to layers via the import statement; files themselves unchanged. |

---

## Task 1: Create `public/css/tokens.css`

**Files:**
- Create: `public/css/tokens.css`

- [ ] **Step 1: Write the file**

```css
/* ════════════════════════════════════════════════════════════════════
   tokens.css — Paper design system tokens.
   Layer assignment is established by index.css (@import layer(tokens)).
   This file declares custom properties only; no rules with side effects.
   See docs/superpowers/specs/2026-05-09-paper-tokens-cascade-layers-refactor-design.md
   ════════════════════════════════════════════════════════════════════ */

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

- [ ] **Step 2: Verify the file parses cleanly**

Run: `python3 -c "import re; open('public/css/tokens.css').read()"`
Expected: No exception (file exists and reads as text).

Browser parse check (no separate tool needed — Task 4 will surface CSS errors via DevTools).

- [ ] **Step 3: Commit**

```bash
git add public/css/tokens.css
git commit -m "css(tokens): introduce paper-system design tokens

Adds public/css/tokens.css with primitive + semantic CSS custom
properties for the paper migration. Light theme is default;
html[data-theme=\"dark\"] overrides the semantic layer for night
paper. No selectors with side effects — file is variables only.

Layer assignment is wired in the next commit via index.css.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Create `public/css/index.css`

**Files:**
- Create: `public/css/index.css`

- [ ] **Step 1: Write the file**

```css
/* ════════════════════════════════════════════════════════════════════
   index.css — Single import root for all paper-system stylesheets.
   Declares @layer order; imports each stylesheet into its layer.
   See docs/superpowers/specs/2026-05-09-paper-tokens-cascade-layers-refactor-design.md
   ════════════════════════════════════════════════════════════════════ */

@layer tokens, components, utilities, legacy, paper;

@import url('tokens.css')         layer(tokens);
@import url('layout.css')         layer(components);
@import url('components.css')     layer(components);
@import url('../styles.css')      layer(utilities);
@import url('../antigravity.css') layer(legacy);
/* paper layer reserved for Wave 1; no import yet */
```

- [ ] **Step 2: Verify the file parses cleanly**

Run: `python3 -c "open('public/css/index.css').read()"`
Expected: No exception.

- [ ] **Step 3: Commit**

```bash
git add public/css/index.css
git commit -m "css(index): introduce cascade-layer import root

Adds public/css/index.css declaring layer order:
  @layer tokens, components, utilities, legacy, paper

This order preserves the pre-migration cascade exactly:
- legacy (antigravity.css) loads later than components, so its
  body.antigravity-theme rules continue to win on every unmigrated
  view (dashboard, library, settings).
- paper layer is reserved for Wave 1; no import yet.

The HTML <link> swap that activates this file is the next commit.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Update `public/index.html` to use the single import root

**Files:**
- Modify: `public/index.html` (the four `<link rel="stylesheet">` tags in `<head>`)

- [ ] **Step 1: Locate the existing link tags**

Run: `grep -n 'rel="stylesheet"' public/index.html`
Expected: Four matching lines for `/css/layout.css`, `/css/components.css`, `/styles.css`, `/antigravity.css`. Note their exact order and indentation.

- [ ] **Step 2: Replace the four tags with one**

Edit `public/index.html`. Find the block:

```html
<link rel="stylesheet" href="/css/layout.css">
<link rel="stylesheet" href="/css/components.css">
<link rel="stylesheet" href="/styles.css">
<link rel="stylesheet" href="/antigravity.css">
```

Replace with:

```html
<link rel="stylesheet" href="/css/index.css">
```

Preserve surrounding indentation. If link tags also have other attributes (`integrity`, `crossorigin`, etc.), match the style of the surrounding head; otherwise keep simple.

- [ ] **Step 3: Verify exactly one stylesheet link remains**

Run: `grep -c 'rel="stylesheet"' public/index.html`
Expected: `1`

Run: `grep -n 'rel="stylesheet"' public/index.html`
Expected: A single line referencing `/css/index.css`.

- [ ] **Step 4: Run the local dev server and load the home page**

Run: `bash scripts/dev.sh`
In a browser: open `http://localhost:8000/`.

Open DevTools Network tab. Confirm:
- `/css/index.css` returns 200.
- `/css/tokens.css`, `/css/layout.css`, `/css/components.css`, `/styles.css`, `/antigravity.css` all return 200 (the @imports cascade fetch).
- Zero 404s on stylesheet requests.

- [ ] **Step 5: Verify cascade layer attribution in DevTools**

In DevTools → Elements → Computed → expand Cascade pane on `body` or `.hero-card`:
- Confirm an `@layer legacy` entry appears for any `body.antigravity-theme …` rule.
- Confirm an `@layer components` entry appears for `.hero-card`-style base rules.
- Confirm `@layer legacy` is listed *after* `@layer components` in the layer-order display (later layer wins).

If either layer attribution is missing or order is wrong, halt — investigate `index.css` import paths before proceeding.

- [ ] **Step 6: Commit**

```bash
git add public/index.html
git commit -m "css(index): swap four link tags for single index.css

Replaces the four <link rel=stylesheet> tags in public/index.html
(/css/layout.css, /css/components.css, /styles.css, /antigravity.css)
with a single <link> to /css/index.css, which @imports each of them
into its assigned cascade layer.

This activates the layer architecture from the prior commits.
Cascade behavior on every unmigrated view is preserved exactly:
@layer legacy (antigravity) loads after @layer components, so
theme overrides continue to win as before.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Verify zero visual regression

**Files:** none modified — verification only.

- [ ] **Step 1: Local dev server smoke**

Run: `bash scripts/qa-smoke.sh local`
Expected: All tests pass. Investigate any failure; do NOT proceed if smoke fails.

- [ ] **Step 2: Manual visual diff — light mode**

With `bash scripts/dev.sh` running, open `http://localhost:8000/` in a browser.

Compare each of these views against `main` (open a second browser window pointed at production or check out `main` in a separate worktree):

- Dashboard / hero card (the empty-state hero with `.intro-page`)
- Ignition view (sidebar → "New concept", or click the dashboard CTA)
- Launch pad view (submit a concept name to land on it)
- Library view (sidebar → Library)
- Settings view (sidebar → Settings)

Each view must be **pixel-identical** to `main`. If any view differs, halt — review the layer order in `index.css` and DevTools cascade attribution.

- [ ] **Step 3: Manual visual diff — dark mode**

Toggle dark theme (Settings → Theme → Dark, or `html[data-theme="dark"]` via DevTools).

Repeat the per-view check from Step 2. Each view must be pixel-identical to `main` in dark mode.

- [ ] **Step 4: Console check**

DevTools → Console: zero errors and zero new warnings on every view, both themes. CSS parse warnings on `@import` are red flags — investigate.

- [ ] **Step 5: Cross-browser quick check**

If feasible, open the Ignition view in Safari and Firefox (still on `dev` branch / local server). Confirm no rendering differences vs. Chrome.

- [ ] **Step 6: No commit**

This task is verification-only. Nothing to commit.

---

## Task 5: Final preflight + push

**Files:** none modified.

- [ ] **Step 1: Re-run smoke**

Run: `bash scripts/qa-smoke.sh local`
Expected: pass.

- [ ] **Step 2: Confirm git status**

Run: `git status --short`
Expected: clean (no uncommitted tracked changes). Untracked files unrelated to this work may remain — leave them.

Run: `git log -3 --oneline`
Expected: three new commits — `css(tokens): …`, `css(index): introduce …`, `css(index): swap four …`.

- [ ] **Step 3: Push to dev**

Run: `git push origin dev`

Per project convention, dev is the integration branch. Production promotion happens via dev → main PR in a separate step.

- [ ] **Step 4: Verify Vercel preview**

Wait for Vercel preview deployment of `dev`. Open the preview URL. Repeat the manual visual diff from Task 4 against the deployed preview. Confirm no regressions vs. production.

If a regression appears only on Vercel preview (not local), it's likely an asset-path or `@import` resolution issue — check `vercel.json` rewrites and the relative paths in `index.css`.

---

## Self-review checklist

- Spec coverage: Each acceptance criterion in `paper-tokens-cascade-layers-refactor-design.md` maps to a step above (`tokens.css` exists → Task 1; `index.css` exists with correct layer order → Task 2; index.html `<link>` swap → Task 3; smoke + visual diff → Task 4 + 5; DevTools cascade attribution → Task 3 Step 5).
- No placeholders: Every step has either runnable commands or full code.
- Type consistency: file paths consistent across tasks (`public/css/tokens.css`, `public/css/index.css`, `public/index.html`, `public/antigravity.css`); layer name list `tokens, components, utilities, legacy, paper` consistent in `tokens.css` reference and `index.css` declaration.
- Frequent commits: 3 commits during implementation + verification + push.
