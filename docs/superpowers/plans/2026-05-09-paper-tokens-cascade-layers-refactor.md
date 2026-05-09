# Paper Wave 0 — cascade-layer infrastructure + paper tokens — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install CSS Cascade Layer infrastructure and add the two paper-specific tokens needed by Wave 1, with zero visible change to any view.

**Architecture:** Add two new CSS custom properties (`--rule-line`, `--rule-step`) to the existing `public/css/variables.css`. Create `public/css/index.css` as a small import root that declares `@layer components, legacy, paper` and `@imports` `styles.css` and `antigravity.css` into their layers. Replace the two existing `<link>` tags in `public/index.html` with one pointing to `index.css`.

**Tech Stack:** Vanilla CSS, no build step. CSS Custom Properties, CSS Cascade Layers (`@layer`, `@import … layer(name)`). FastAPI static-file serving via `public/`.

**Spec:** `docs/superpowers/specs/2026-05-09-paper-tokens-cascade-layers-refactor-design.md`

**Umbrella:** `docs/superpowers/specs/2026-05-09-paper-migration-plan.md`

**Branch:** Work on `dev`. Commit straight to `dev` per project convention. Do NOT create a worktree, do NOT switch branches.

---

## File structure

| File | Action | Responsibility |
|---|---|---|
| `public/css/variables.css` | **modify** | Add `--rule-line` and `--rule-step` to the primitive section. Add a paired `--rule-line` override under `[data-theme="dark"]`. |
| `public/css/index.css` | **create** | Single import root. Declares cascade-layer order. Imports `styles.css` and `antigravity.css` into their assigned layers. Reserves `paper` layer (no import yet — Wave 1 introduces `paper.css`). |
| `public/index.html` | **modify** | Replace the existing two `<link rel="stylesheet">` tags (`/styles.css?v=85`, `/antigravity.css?v=13`) with one pointing to `/css/index.css?v=1`. |
| Everything else | **untouched** | `public/styles.css` and its 8-file import chain, `public/antigravity.css`, `public/css/tokens.css` (the existing login-safe font subset) — all stay byte-identical. |

---

## Task 1: Add `--rule-line` and `--rule-step` tokens to `public/css/variables.css`

**Files:**
- Modify: `public/css/variables.css`

- [ ] **Step 1: Locate the primitive section**

Run: `grep -n 'border-subtle' public/css/variables.css | head -5`
Expected: a match around line 58 in the `:root` block, where `--border-subtle: rgba(var(--ink-900-rgb), 0.10);` is defined.

- [ ] **Step 2: Add the two new primitives**

Find the line `--border-subtle:      rgba(var(--ink-900-rgb), 0.10);`. Immediately after `--border-strong: rgba(var(--ink-900-rgb), 0.16);` (next line), add:

```css
  /* Paper-system additions (Paper Wave 0) — used by ruled-paper composer
     in the Ignition + Launch Pad views. See:
     docs/superpowers/specs/2026-05-09-ignition-paper-redesign-design.md */
  --rule-line:          rgba(var(--ink-900-rgb), 0.07);
  --rule-step:          32px;
```

Match the existing two-space-then-aligned-colon indentation.

- [ ] **Step 3: Add the dark-mode override**

Locate the `[data-theme="dark"] {` block (around line 453). Find the dark-mode `--border-strong: rgba(var(--cream-50-rgb), 0.22);` line. Immediately after it, add:

```css
  --rule-line:     rgba(var(--cream-50-rgb), 0.10);
```

`--rule-step` is a length, not a color — no dark-mode override needed.

- [ ] **Step 4: Verify the file still parses**

Run: `python3 -c "open('public/css/variables.css').read()"`
Expected: no exception.

- [ ] **Step 5: Verify the new tokens are accessible in browser**

Run: `bash scripts/dev.sh` and open `http://localhost:8000/`. In DevTools → Console:

```js
getComputedStyle(document.documentElement).getPropertyValue('--rule-line')
```

Expected: a non-empty rgba value (`' rgba(36, 32, 56, 0.07)'` in light, `' rgba(247, 236, 225, 0.10)'` in dark).

```js
getComputedStyle(document.documentElement).getPropertyValue('--rule-step')
```

Expected: `' 32px'`.

- [ ] **Step 6: Commit**

```bash
git add public/css/variables.css
git commit -m "css(tokens): add --rule-line and --rule-step for paper composer

Two new primitives added to variables.css for the Paper Wave 1
ruled-paper textarea: --rule-line (faint horizontal-rule color,
rgba(ink, 0.07) light / rgba(cream, 0.10) dark) and --rule-step
(32px line spacing).

These are the only token additions needed for the paper migration;
all other paper-system rules introduced in later waves reuse the
existing --surface-*, --text-*, --accent-*, --border-*, --shadow-*
families.

Paper Wave 0.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Create `public/css/index.css`

**Files:**
- Create: `public/css/index.css`

- [ ] **Step 1: Write the file**

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

- [ ] **Step 2: Verify file parses cleanly**

Run: `python3 -c "open('public/css/index.css').read()"`
Expected: no exception.

- [ ] **Step 3: Commit**

```bash
git add public/css/index.css
git commit -m "css(index): introduce cascade-layer import root

Adds public/css/index.css declaring layer order:
  @layer components, legacy, paper

This order preserves the pre-migration cascade exactly:
- legacy (antigravity.css) loads later than components, so its
  body.antigravity-theme rules continue to win on every unmigrated
  view (dashboard, library, settings).
- paper layer is reserved for Paper Wave 1; no import yet.

The HTML <link> swap that activates this file is the next commit.

Paper Wave 0.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Update `public/index.html` to use the single import root

**Files:**
- Modify: `public/index.html`

- [ ] **Step 1: Locate the existing link tags**

Run: `grep -n 'rel="stylesheet"' public/index.html`
Expected: exactly two matches — `styles.css?v=85` and `antigravity.css?v=13` — at consecutive lines (currently 26–27).

- [ ] **Step 2: Replace the two tags with one**

Find the block:

```html
<link rel="stylesheet" href="styles.css?v=85">
<link rel="stylesheet" href="antigravity.css?v=13">
```

Replace with:

```html
<link rel="stylesheet" href="/css/index.css?v=1">
```

Preserve surrounding indentation.

- [ ] **Step 3: Verify exactly one stylesheet link remains in `<head>`**

Run: `grep -n 'rel="stylesheet"' public/index.html`
Expected: exactly one match referencing `/css/index.css?v=1`.

- [ ] **Step 4: Run the local dev server and load the home page**

Run: `bash scripts/dev.sh`
In a browser: open `http://localhost:8000/`.

DevTools Network tab — confirm:
- `/css/index.css?v=1` returns 200.
- `/styles.css?v=85` returns 200 (loaded transitively via @import).
- `/antigravity.css?v=13` returns 200 (loaded transitively via @import).
- All 8 files in styles.css's import chain (variables.css, base.css, crystal.css, components.css, layout.css, board-first.css, approach-reveals.css, iso-board-state-surface.css) return 200.
- Zero 404s on stylesheet requests.

- [ ] **Step 5: Verify cascade layer attribution in DevTools**

DevTools → Elements. Inspect any element on the dashboard that's themed by antigravity (e.g., the empty-state hero card on the home page). In the Computed pane → Cascade section:
- An `@layer legacy` entry appears for `body.antigravity-theme …` rules.
- An `@layer components` entry appears for base `.hero-card`-style rules.
- The cascade pane lists `@layer legacy` *after* `@layer components` (later layer wins).

If either layer attribution is missing or order is wrong, halt — investigate `index.css` import paths.

- [ ] **Step 6: Commit**

```bash
git add public/index.html
git commit -m "css(index): swap two link tags for single index.css

Replaces the two <link rel=stylesheet> tags in public/index.html
(/styles.css?v=85, /antigravity.css?v=13) with a single <link>
to /css/index.css?v=1, which @imports each of them into its
assigned cascade layer.

This activates the layer architecture from the prior commits.
Cascade behavior on every unmigrated view is preserved exactly:
@layer legacy (antigravity) loads after @layer components, so
theme overrides continue to win as before.

Paper Wave 0.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Verify zero visual regression

**Files:** none modified — verification only.

- [ ] **Step 1: Local browser smoke**

Run: `bash scripts/qa-smoke.sh local`
Expected: pass clean. Investigate any failure; do NOT proceed if smoke fails.

- [ ] **Step 2: Manual visual diff — light mode**

With `bash scripts/dev.sh` running, open `http://localhost:8000/` in Chrome.

Compare each of these views against `main` (open a second browser window pointed at production, or check out `main` in a separate worktree):

- Dashboard / hero card (the empty-state hero on the home page)
- Ignition view (sidebar → "New concept", or click the dashboard CTA)
- Launch pad view (submit a concept name to land on it)
- Library view (sidebar → Library)
- Settings view (sidebar → Settings)
- Login page (logout, then `/login`)

Each view must be **pixel-identical** to `main`. If any differs, halt — review layer order and DevTools cascade attribution.

- [ ] **Step 3: Manual visual diff — dark mode**

Toggle dark theme (Settings → Theme → Dark, or `html[data-theme="dark"]` via DevTools). Repeat the per-view check from Step 2.

- [ ] **Step 4: Console check**

DevTools → Console: zero errors and zero new warnings on every view, both themes. CSS parse warnings on `@import` are red flags — investigate.

- [ ] **Step 5: Cross-browser quick check**

Open the Ignition view in Safari and Firefox (still on `dev` branch / local server). Confirm no rendering differences vs Chrome.

- [ ] **Step 6: No commit**

This task is verification-only.

---

## Task 5: Final preflight + push

**Files:** none modified.

- [ ] **Step 1: Re-run smoke**

Run: `bash scripts/qa-smoke.sh local`
Expected: pass.

- [ ] **Step 2: Confirm git status**

Run: `git status --short`
Expected: clean (no uncommitted tracked changes).

Run: `git log -3 --oneline`
Expected: three new commits — `css(tokens): add --rule-line and --rule-step …`, `css(index): introduce cascade-layer import root`, `css(index): swap two link tags for single index.css`.

Run: `grep -rn '<<<<<<\|>>>>>>\|=======' public/css/variables.css public/css/index.css public/index.html 2>/dev/null`
Expected: no matches (no conflict markers).

- [ ] **Step 3: Push to dev**

Run: `git push origin dev`

- [ ] **Step 4: Verify Vercel preview**

Wait for Vercel preview deployment of `dev`. Open the preview URL. Repeat the manual visual diff from Task 4 against the deployed preview.

If a regression appears only on Vercel preview (not local), it's likely an asset-path or `@import` resolution issue — check `vercel.json` rewrites and the relative paths in `index.css`.

---

## Self-review checklist

- **Spec coverage:**
  - `--rule-line` + `--rule-step` token additions to variables.css → Task 1
  - `public/css/index.css` with cascade-layer order → Task 2
  - `<link>` swap in index.html → Task 3
  - Smoke + visual diff verification → Task 4 + 5
  - DevTools cascade attribution check → Task 3 Step 5
- **No placeholders:** Every step contains either runnable commands or full code.
- **Type consistency:** Token names (`--rule-line`, `--rule-step`) match across spec and plan. Layer order (`components, legacy, paper`) consistent.
- **Frequent commits:** 3 commits during implementation + verification + push.
