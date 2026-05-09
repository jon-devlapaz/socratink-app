# Wave 1 — Ignition + Launch Pad paper redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the Ignition view and Launch Pad view to mirror socratink.ai's paper journal identity. Behavioral pipeline (cap gate, source-attach, sessionStorage shell, telemetry, audio, /api/extract) preserved unchanged.

**Architecture:** Add a new `public/css/paper.css` registered in `@layer paper` so its rules win over `@layer legacy` (antigravity) on these two views. New BEM-style component classes (`.composer-card`, `.witness-anchor`, `.ig-title`, `.ig-button`, `.journal-meta`, etc.) reference only semantic tokens from Wave 0. Update view markup in `public/index.html`. Update `public/js/app.js` and `public/js/launch-pad.js` for the new visibility convention (`[hidden]` attribute), focus routing, and busy state. Delete the migrated rules from `public/antigravity.css` in the same PR.

**Tech Stack:** Vanilla CSS (no build step) using CSS Custom Properties + Cascade Layers from Wave 0; vanilla JS modules; FastAPI static-file serving via `public/`.

**Spec:** `docs/superpowers/specs/2026-05-09-ignition-paper-redesign-design.md`

**Umbrella:** `docs/superpowers/specs/2026-05-09-paper-migration-plan.md`

**Hard prerequisite:** Wave 0 plan completed and merged to `dev`. Verify by checking that `public/css/tokens.css` and `public/css/index.css` exist and `public/index.html` carries a single `<link>` to `/css/index.css`. Do NOT start this plan if Wave 0 is missing.

**Branch:** Work on `dev`. Commit straight to `dev` per project convention.

---

## File structure

| File | Action | Responsibility |
|---|---|---|
| `public/css/paper.css` | **create** | All new component CSS (composer-card, witness-anchor, ig-title, ig-button, journal-meta, ignition-cap-gate, source-panel restyle). Rules reference semantic tokens only. Loaded into `@layer paper`. |
| `public/css/index.css` | **modify** | Add `@import url('paper.css') layer(paper);` after the legacy import. |
| `public/css/layout.css` | **modify** | Replace existing `#ignition-view` + `#launch-pad-view` blocks with new shell rules using `:not([hidden])` selector + `ig-screen-in` keyframe. |
| `public/index.html` | **modify** | Replace `<section id="ignition-view">` and `<section id="launch-pad-view">` markup blocks with new versions. Remove the `<canvas id="intro-particle-canvas">` element. |
| `public/js/app.js` | **modify** | Update `showIgnition`, `hideIgnition`, `hidePrimaryViews`, `renderIgnitionGate` to drive visibility via `[hidden]` attribute and busy state via `data-state` attribute. |
| `public/js/launch-pad.js` | **modify** | Update `showLaunchPad` to use `[hidden]` and direct field focus; replace `is-building-route` class manipulation with `data-state="busy"`. |
| `public/antigravity.css` | **modify** | Delete migrated ignition + launch-pad rules. Other rules untouched. |

---

## Task 1: Verify Wave 0 prerequisite

**Files:** none modified.

- [ ] **Step 1: Confirm Wave 0 files exist**

Run: `ls public/css/tokens.css public/css/index.css`
Expected: both files exist.

- [ ] **Step 2: Confirm Wave 0 link in HTML**

Run: `grep -n 'rel="stylesheet"' public/index.html`
Expected: single line referencing `/css/index.css`. If multiple lines, Wave 0 was not merged — halt.

- [ ] **Step 3: Confirm cascade layer order in index.css**

Run: `grep -n '@layer' public/css/index.css`
Expected: `@layer tokens, components, utilities, legacy, paper;`. If order differs, halt.

- [ ] **Step 4: Confirm tokens are in scope**

Open the local dev server (`bash scripts/dev.sh`); in browser DevTools → Console:

```js
getComputedStyle(document.documentElement).getPropertyValue('--accent-deep')
```

Expected: `' #6f4da1'` (or `' #c8a8f7'` if dark theme is active). If empty, tokens.css isn't loading.

- [ ] **Step 5: No commit**

This task is verification-only.

---

## Task 2: Pre-deletion grep audit on antigravity selectors

**Files:** none modified — produces an audit log captured in commit messages.

- [ ] **Step 1: Audit each candidate selector**

For each selector below, run a grep across `public/index.html` and `public/js/`. The selector is **safe to delete** if matches appear only inside `#ignition-view` or `#launch-pad-view` markup. Otherwise flag for Wave 2+.

Definitely-delete candidates (per spec):

```bash
grep -n 'ignition-view\|ignition-title\|ignition-cap-gate\|ignition-view__inner' public/index.html public/js/*.js
grep -n 'launch-pad-view\|launch-pad-form\|launch-pad-input\|launch-pad-submit\|launch-pad-validation\|launch-pad-helper\|launch-pad-title\|launch-pad-concept-name\|launch-pad-footer\|launch-pad-view__inner\|ag-lp-arriving\|is-building-route' public/index.html public/js/*.js
grep -n 'intro-particles\|intro-particle-canvas' public/index.html public/js/*.js
```

Audit-before-deleting candidates (may be referenced by dashboard / hero card):

```bash
grep -n 'hero-single-input\|hero-source-attach\|hero-source-panel\|hero-eyebrow\|hero-state-chip\|hero-door-error' public/index.html public/js/*.js
```

- [ ] **Step 2: Record audit results**

Create a temporary file `/tmp/wave1-deletion-audit.txt` capturing the grep output for the audit-before-deleting candidates. The contents of this file will be summarized in the deletion commit message in Task 14.

For each audit candidate, record:
- Selector name
- Files where it appears
- Whether the appearances are confined to `#ignition-view` / `#launch-pad-view` markup, or spill into other views (dashboard `.hero-card`, library, settings, etc.)
- Verdict: DELETE in Wave 1 / DEFER to Wave 2

Example expected results based on current state:
- `.hero-single-input` — used by `#ignition-view` form id; if grep shows it only in the ignition section, **DELETE**.
- `.hero-source-attach` — used by `#ignition-view`; grep should confirm ignition-only, **DELETE**.
- `.hero-eyebrow`, `.hero-state-chip`, `.hero-door-error` — used by hero card on dashboard; **DEFER to Wave 2**.

- [ ] **Step 3: No commit**

Audit task; deletion happens in Task 14.

---

## Task 3: Create `public/css/paper.css` — composer card + textarea rule grid

**Files:**
- Create: `public/css/paper.css`

- [ ] **Step 1: Write the file with composer-card and field rules**

```css
/* ════════════════════════════════════════════════════════════════════
   paper.css — PAPER SYSTEM components.
   Imported via index.css into @layer paper, which beats @layer legacy
   (antigravity) on migrated surfaces. References only semantic tokens
   from tokens.css. No body.antigravity-theme ancestor.
   See docs/superpowers/specs/2026-05-09-ignition-paper-redesign-design.md
   ════════════════════════════════════════════════════════════════════ */

/* ── Composer card ──────────────────────────────────────────── */

.composer-card {
  width: 100%;
  max-width: 460px;
  margin: 0 auto;
  box-sizing: border-box;
  padding: var(--space-5);
  background: var(--surface-paper);
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-paper);
  box-shadow: var(--shadow-card);
  position: relative;
  isolation: isolate;
}

.composer-card__field {
  display: block;
  width: 100%;
  box-sizing: border-box;
  appearance: none;
  resize: none;
  border: 0;
  outline: none;
  background:
    repeating-linear-gradient(
      180deg,
      transparent 0,
      transparent calc(var(--rule-step) - 1px),
      var(--surface-rule) calc(var(--rule-step) - 1px),
      var(--surface-rule) var(--rule-step)
    ) local;
  background-position: 0 var(--composer-grid-offset, 0px);
  font-family: inherit;
  font-size: var(--text-md);
  line-height: var(--rule-step);
  color: var(--ink);
  padding: var(--composer-grid-offset, 8px) 0 0 0;
  min-height: calc(var(--rule-step) * 3);
}

.composer-card--tall .composer-card__field {
  min-height: calc(var(--rule-step) * 5);
}

.composer-card__field::placeholder {
  color: var(--ink-faint);
  font-style: italic;
}

.composer-card__field:focus-visible {
  box-shadow: var(--focus-ring);
}

.composer-card__actions {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--space-3);
}

/* ── Locked + busy states ──────────────────────────────────── */

.composer-card[data-state="locked"],
.composer-card[data-state="busy"] {
  opacity: 0.55;
  transition: opacity var(--duration-fast) var(--ease-out);
}
.composer-card[data-state="locked"] :is(button, textarea, input),
.composer-card[data-state="busy"]   :is(button, textarea, input) {
  pointer-events: none;
}
.composer-card__field:disabled {
  color: var(--ink-faint);
  -webkit-text-fill-color: var(--ink-faint);
  opacity: 1;
}
```

- [ ] **Step 2: Verify file parses cleanly**

Run: `python3 -c "open('public/css/paper.css').read()"`
Expected: no exception.

- [ ] **Step 3: Commit**

```bash
git add public/css/paper.css
git commit -m "css(paper): introduce paper.css with composer-card + field

First commit of the paper component system. Adds .composer-card and
.composer-card__field with the rule-grid background-attachment:local
pattern (rules scroll with content), plus locked/busy data-state
attributes for cap-gate and submit-in-flight states.

Not yet imported by index.css — that wiring lands in the next commit
group along with the rest of the paper components.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Add witness anchor + ig-title + eyebrow + concept-mark to `paper.css`

**Files:**
- Modify: `public/css/paper.css`

- [ ] **Step 1: Append to paper.css**

Append the following block to the end of `public/css/paper.css`:

```css
/* ── Witness anchor ────────────────────────────────────────── */

.witness-anchor {
  width: 28px;
  height: 28px;
  margin: 0 auto var(--space-3);
  display: grid;
  place-items: center;
}
.witness-anchor svg { display: block; }
.witness-anchor__shape {
  fill: none;
  stroke: var(--ink-faint);
  stroke-width: 1.2;
  vector-effect: non-scaling-stroke;
}

/* ── Title ─────────────────────────────────────────────────── */

.ig-title {
  margin: 0 0 var(--space-5);
  text-align: center;
  font-family: var(--font-display);
  font-size: var(--text-display);
  line-height: var(--leading-display);
  font-weight: var(--weight-bold);
  letter-spacing: -0.005em;
  color: var(--ink);
  text-wrap: balance;
  overflow-wrap: anywhere;
  word-break: break-word;
  hyphens: auto;
}
.ig-title__emphasis {
  font-style: italic;
  font-weight: var(--weight-bold);
  color: var(--accent-deep);
  text-decoration: underline;
  text-decoration-color: var(--accent-deep);
  text-decoration-color: color-mix(in srgb, var(--accent-deep) 55%, transparent);
  text-decoration-thickness: 0.08em;
  text-underline-offset: 0.16em;
  text-decoration-skip-ink: none;
}

/* ── Eyebrow (Screen 1) ────────────────────────────────────── */

.ig-eyebrow {
  margin: 0 0 var(--space-4);
  text-align: center;
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
  color: var(--accent-deep);
  letter-spacing: 0;
  overflow-wrap: anywhere;
}
.ig-eyebrow__dot {
  display: inline-block;
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: currentColor;
  margin: 0 6px;
  vertical-align: middle;
  opacity: 0.55;
}

/* ── Concept mark (Screen 2) ───────────────────────────────── */

.ig-concept-mark {
  margin: 0 0 var(--space-3);
  text-align: center;
  font-size: var(--text-sm);
  color: var(--ink-faint);
  overflow-wrap: anywhere;
}
.ig-concept-mark__key { font-style: italic; }
.ig-concept-mark__name {
  color: var(--ink);
  font-weight: var(--weight-medium);
  margin-left: 4px;
}

.launch-pad-view__inner > .ig-title {
  margin-top: var(--space-2);
}
```

- [ ] **Step 2: Commit**

```bash
git add public/css/paper.css
git commit -m "css(paper): add witness-anchor, ig-title, eyebrow, concept-mark

Witness anchor is an inert SVG diamond (no fill, no glow); .ig-title
carries the display heading with the violet-deep .ig-title__emphasis
span and a color-mix fallback to a solid underline color for older
browsers. Eyebrow is the Screen 1 step indicator; concept mark is
the Screen 2 plain-typeset 'on Photosynthesis' line.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Add helper + footnote + error + journal-meta to `paper.css`

**Files:**
- Modify: `public/css/paper.css`

- [ ] **Step 1: Append to paper.css**

```css
/* ── Helper + footnote + error ─────────────────────────────── */

.ig-helper {
  margin: 0 0 var(--space-4);
  text-align: center;
  font-size: var(--text-md);
  line-height: var(--leading-md);
  color: var(--ink-soft);
  overflow-wrap: anywhere;
}

.ig-footnote {
  margin: var(--space-3) auto 0;
  max-width: 460px;
  padding-left: var(--space-1);
  font-size: var(--text-xs);
  color: var(--ink-faint);
  overflow-wrap: anywhere;
}

.ig-error {
  margin: var(--space-3) 0 0;
  font-size: var(--text-xs);
  color: var(--ink-faint);
  min-height: 1em;          /* reserve space so live updates don't shift layout */
}
.ig-error:empty { margin-top: 0; }

/* ── Source-meta line (inside composer-card on Screen 1) ──── */

.composer-card .journal-meta {
  margin-top: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px solid var(--line);
  background: var(--surface-paper);
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
  font-size: var(--text-xs);
  color: var(--ink-faint);
}
.composer-card .journal-meta__key {
  color: var(--accent-deep);
  font-weight: var(--weight-bold);
}
.composer-card .journal-meta__value { font-style: italic; }
.composer-card .journal-meta__sep { color: var(--ink-faint); }
.composer-card .journal-meta__add {
  color: var(--accent-deep);
  font-weight: var(--weight-bold);
  text-decoration: underline;
  text-decoration-color: var(--accent-deep);
  text-decoration-color: color-mix(in srgb, var(--accent-deep) 40%, transparent);
  text-decoration-thickness: 0.06em;
  text-underline-offset: 0.2em;
  background: 0;
  border: 0;
  padding: 0;
  cursor: pointer;
  font: inherit;
}
.composer-card .journal-meta__add:hover {
  text-decoration-color: var(--accent-deep);
}
```

- [ ] **Step 2: Commit**

```bash
git add public/css/paper.css
git commit -m "css(paper): add helper, footnote, error, journal-meta

Live-region .ig-error reserves a one-em min-height so 422 messages
don't shift layout when they appear. .journal-meta is the source-
attach affordance line that lives inside the composer card with a
hairline separator above; matches the landing page's journal meta
pattern.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Add `ig-button` + ghost variant to `paper.css`

**Files:**
- Modify: `public/css/paper.css`

- [ ] **Step 1: Append to paper.css**

```css
/* ── Primary action button ─────────────────────────────────── */

.ig-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  min-height: 40px;
  padding: 0 var(--space-4);
  background: var(--accent);
  color: var(--surface-paper);
  border: 1px solid var(--accent-deep);
  border-radius: var(--radius-paper);
  font-family: inherit;
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
  line-height: 1;
  cursor: pointer;
  transition:
    background var(--duration-fast) var(--ease-out),
    transform var(--duration-micro) var(--ease-out),
    box-shadow var(--duration-fast) var(--ease-out);
}
.ig-button:hover:not(:disabled) {
  background: var(--accent-deep);
  transform: translateY(-1px);
  box-shadow: var(--shadow-button-hover);
}
.ig-button:active:not(:disabled) {
  transform: translateY(0);
}
.ig-button:focus-visible {
  outline: none;
  transform: none;
  box-shadow: var(--focus-ring), var(--shadow-button-hover);
}
.ig-button:disabled {
  background: var(--surface-rule);
  color: var(--ink-faint);
  border-color: transparent;
  cursor: not-allowed;
  box-shadow: none;
  -webkit-text-fill-color: var(--ink-faint);
  opacity: 1;
}

/* Dark-mode hover: the night palette has only one violet tier, so
   darken via opacity blend rather than swapping to a deeper token. */
html[data-theme="dark"] .ig-button:hover:not(:disabled) {
  background: rgba(200, 168, 247, 0.85);
  background: color-mix(in srgb, var(--accent) 85%, transparent);
}

/* ── Ghost variant (cap-gate CTA) ──────────────────────────── */

.ig-button--ghost {
  background: transparent;
  color: var(--accent-deep);
  border-color: var(--line-strong);
}
.ig-button--ghost:hover:not(:disabled) {
  background: rgba(144, 103, 198, 0.06);
  background: color-mix(in srgb, var(--accent-deep) 6%, transparent);
  border-color: var(--accent);
  transform: translateY(-1px);
}
.ig-button--ghost:focus-visible {
  outline: none;
  transform: none;
  box-shadow: var(--focus-ring);
}

/* ── Reduced motion ────────────────────────────────────────── */

@media (prefers-reduced-motion: reduce) {
  .ig-button,
  .ig-button:hover:not(:disabled),
  .ig-button:focus-visible,
  .ig-button:active:not(:disabled),
  .ig-button--ghost,
  .ig-button--ghost:hover:not(:disabled),
  .ig-button--ghost:focus-visible {
    transition: none;
    transform: none;
  }
  .composer-card[data-state="locked"],
  .composer-card[data-state="busy"] {
    transition: none;
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add public/css/paper.css
git commit -m "css(paper): add ig-button primary + ghost variants

Primary fill matches landing page button-primary (violet fill,
violet-deep border, 8px radius, 1px translate on hover). Disabled
state goes solid --surface-rule fill (keeps button silhouette) with
explicit color override of UA disabled GrayText. Ghost variant for
cap-gate CTA. Reduced-motion suppresses transforms and transitions.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Add `ignition-cap-gate` + source-panel restyle to `paper.css`

**Files:**
- Modify: `public/css/paper.css`

- [ ] **Step 1: Append to paper.css**

```css
/* ── Cap gate ──────────────────────────────────────────────── */

.ignition-cap-gate {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-5);
  background: var(--surface-paper);
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-paper);
  box-shadow: var(--shadow-card);
}
.ignition-cap-gate__message {
  margin: 0;
  font-size: var(--text-md);
  line-height: var(--leading-md);
  color: var(--ink);
  overflow-wrap: anywhere;
}

/* ── Source panel (restyle of source-panel.js's existing render) ──
   Class names match what source-panel.js emits today; no JS change. */

.creation-source-panel {
  margin-top: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px solid var(--line);
  background: var(--surface-paper);
}
.creation-source-panel .overlay-tabs {
  display: flex;
  gap: var(--space-1);
  border-bottom: 1px solid var(--line);
  margin-bottom: var(--space-3);
}
.creation-source-panel .overlay-tab {
  background: transparent;
  border: 0;
  border-bottom: 2px solid transparent;
  padding: var(--space-2) var(--space-3);
  font: inherit;
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  color: var(--ink-faint);
  cursor: pointer;
  margin-bottom: -1px;
}
.creation-source-panel .overlay-tab.active,
.creation-source-panel .overlay-tab[aria-selected="true"] {
  color: var(--accent-deep);
  border-bottom-color: var(--accent-deep);
}
.creation-source-panel .overlay-textarea,
.creation-source-panel .overlay-url-input {
  width: 100%;
  box-sizing: border-box;
  padding: var(--space-2) var(--space-3);
  background: var(--surface-paper);
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-paper);
  font: inherit;
  font-size: var(--text-sm);
  color: var(--ink);
  resize: none;
}
.creation-source-panel .overlay-textarea:focus-visible,
.creation-source-panel .overlay-url-input:focus-visible {
  outline: none;
  border-color: var(--accent);
  box-shadow: var(--focus-ring);
}
.creation-source-panel .overlay-dropzone {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 80px;
  padding: var(--space-4);
  border: 1px dashed var(--line-strong);
  border-radius: var(--radius-paper);
  color: var(--ink-faint);
  background: transparent;
  cursor: pointer;
}
.creation-source-panel .overlay-dropzone:focus-visible {
  outline: none;
  border-color: var(--accent);
  box-shadow: var(--focus-ring);
}
.creation-source-panel .overlay-dropfeedback {
  margin: var(--space-2) 0 0;
  font-size: var(--text-xs);
  color: var(--ink-faint);
}
.creation-source-panel .overlay-dropfeedback.ok    { color: var(--accent-deep); }
.creation-source-panel .overlay-dropfeedback.error { color: #b9444f; }

.creation-source-panel-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  margin-top: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px solid var(--line);
}
.creation-source-panel-cancel {
  background: transparent;
  color: var(--ink);
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-paper);
  padding: var(--space-2) var(--space-3);
  font: inherit;
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
  cursor: pointer;
}
.creation-source-panel-cancel:hover {
  border-color: var(--accent);
  background: rgba(144, 103, 198, 0.06);
  background: color-mix(in srgb, var(--accent-deep) 6%, transparent);
}
.creation-source-panel-attach {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  background: var(--accent);
  color: var(--surface-paper);
  border: 1px solid var(--accent-deep);
  border-radius: var(--radius-paper);
  padding: var(--space-2) var(--space-4);
  font: inherit;
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
  cursor: pointer;
}
.creation-source-panel-attach:disabled {
  background: var(--surface-rule);
  color: var(--ink-faint);
  border-color: transparent;
  cursor: not-allowed;
  -webkit-text-fill-color: var(--ink-faint);
}
```

- [ ] **Step 2: Commit**

```bash
git add public/css/paper.css
git commit -m "css(paper): cap-gate paper card + source-panel paper restyle

Cap gate is a standard paper card; no special left gutter motif.
Source panel selectors target the existing class names emitted by
source-panel.js (.creation-source-panel, .creation-source-panel-*,
.overlay-*) so JS logic is untouched — only the rendered look
changes. .overlay-dropfeedback.error keeps the existing semantic
red for accessibility consistency with current behavior.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Update `public/css/layout.css` view shells

**Files:**
- Modify: `public/css/layout.css` (lines 2412–2505 currently contain the old `#ignition-view` block; the `#launch-pad-view` block lives near the same area)

- [ ] **Step 1: Locate the existing blocks**

Run: `grep -n '#ignition-view\b\|#launch-pad-view\b\|.ignition-view__inner\|.launch-pad-view__inner\|@keyframes ig-screen-in' public/css/layout.css`

Note the line ranges. The current block contains rules like `display: none` on `#ignition-view` and `#ignition-view.visible { display: flex }` etc.

- [ ] **Step 2: Delete the existing blocks**

Remove every selector that matches `#ignition-view`, `#ignition-view.visible`, `#launch-pad-view`, `#launch-pad-view:not([hidden])`, `.ignition-view__inner`, `.launch-pad-view__inner`, and any `@keyframes ig-screen-in` block currently in `public/css/layout.css`.

These are being replaced. Do not also delete unrelated rules nearby (e.g., `.ignition-cap-gate` if any remains in layout.css — that lives in paper.css now).

- [ ] **Step 3: Add the new blocks**

In the same location (or wherever feels right within layout.css), add:

```css
/* ── Ignition + Launch Pad view shells ─────────────────────────
   :not([hidden]) is required so the [hidden] attribute (UA
   display:none, specificity 0,1,0) wins over the ID-based
   display:flex (specificity 1,0,0) when JS toggles the attribute.
   See docs/superpowers/specs/2026-05-09-ignition-paper-redesign-design.md
   ──────────────────────────────────────────────────────────── */

#ignition-view:not([hidden]),
#launch-pad-view:not([hidden]) {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: clamp(56px, 10vh, 96px) var(--space-5) clamp(80px, 14vh, 128px);
  position: relative;
  isolation: isolate;
  overflow-x: hidden;
  overflow-y: auto;
  background: var(--surface-page);
}

.ignition-view__inner,
.launch-pad-view__inner {
  width: min(100%, 480px);
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: var(--space-4);
  animation: ig-screen-in var(--duration-medium) var(--ease-out) both;
}

@keyframes ig-screen-in {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}

@media (prefers-reduced-motion: reduce) {
  .ignition-view__inner,
  .launch-pad-view__inner { animation: none; }
}
```

- [ ] **Step 4: Commit**

```bash
git add public/css/layout.css
git commit -m "css(layout): paper view shells with [hidden] visibility

Replaces the old #ignition-view / #launch-pad-view blocks (which
relied on a .visible class toggle) with :not([hidden]) selectors so
the [hidden] attribute drives visibility natively. Adds the
ig-screen-in keyframe + reduced-motion suppression. Page background
is now solid var(--surface-page); no gradient washes, no positioned
::before/::after blooms, no canvas.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: Register `paper.css` in `public/css/index.css`

**Files:**
- Modify: `public/css/index.css`

- [ ] **Step 1: Add the import**

Open `public/css/index.css`. Find this line:

```css
@import url('../antigravity.css') layer(legacy);
```

Add immediately below it:

```css
@import url('paper.css')          layer(paper);
```

The paper-layer reservation comment at the bottom can stay or be deleted — your call (recommend deleting it since the layer is now used).

- [ ] **Step 2: Verify import resolves**

Run: `bash scripts/dev.sh` and open `http://localhost:8000/`. DevTools Network: confirm `/css/paper.css` returns 200.

- [ ] **Step 3: Commit**

```bash
git add public/css/index.css
git commit -m "css(index): import paper.css into @layer paper

Activates the paper layer reserved in Wave 0. paper.css now wins
over @layer legacy (antigravity.css) on every selector it defines —
which is exactly the right behavior for migrated surfaces. Other
views (dashboard, library, settings) continue to be styled by
antigravity since paper.css contains no rules targeting their DOM.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 10: Update `#ignition-view` markup in `public/index.html`

**Files:**
- Modify: `public/index.html` (the existing `<section id="ignition-view">` block, currently lines 278–323)

- [ ] **Step 1: Locate the block**

Run: `grep -n '<section id="ignition-view"' public/index.html`
Note the line number.

Read the section from that line to the closing `</section>` to confirm the boundaries.

- [ ] **Step 2: Replace with the new markup**

Delete from `<section id="ignition-view"` through its matching `</section>`, and replace with:

```html
<!-- Ignition View: door for new concept entry (paper system) -->
<section id="ignition-view" class="primary-view ignition-view"
         aria-labelledby="ignition-title" hidden>
  <div class="ignition-view__inner">
    <div class="witness-anchor" aria-hidden="true">
      <svg viewBox="0 0 28 28" width="28" height="28">
        <polygon class="witness-anchor__shape" points="14,2 26,14 14,26 2,14"/>
      </svg>
    </div>

    <p class="ig-eyebrow">
      <span>Ignition</span>
      <span class="ig-eyebrow__dot" aria-hidden="true"></span>
      <span>1 of 2</span>
    </p>

    <h1 class="ig-title" id="ignition-title" tabindex="-1">
      What do you want to <span class="ig-title__emphasis">actually explain</span>?
    </h1>

    <p class="ig-helper">
      This is global context. The first room will ask one smaller question.
    </p>

    <!-- Cap gate — rendered ABOVE the composer; composer locks but stays visible -->
    <div class="ignition-cap-gate" id="ignition-cap-gate" hidden>
      <p class="ignition-cap-gate__message">
        The board holds nine concepts. Retire one to start another.
      </p>
      <button type="button" class="ig-button ig-button--ghost"
              onclick="App.showLibrary()">Open library</button>
    </div>

    <form class="composer-card" id="hero-single-input"
          onsubmit="return App.runHeroAction(event)" autocomplete="off">
      <textarea class="composer-card__field" id="hero-single-input-field"
                rows="2" maxlength="200"
                placeholder="e.g. photosynthesis, the Krebs cycle, recursion in Python…"
                aria-label="What do you want to actually explain?"></textarea>

      <div class="journal-meta">
        <span class="journal-meta__key">source</span>
        <span class="journal-meta__value" id="hero-source-value">none yet</span>
        <span class="journal-meta__sep" aria-hidden="true">—</span>
        <button type="button" class="journal-meta__add"
                id="hero-source-attach" aria-expanded="false"
                aria-controls="hero-source-panel">add</button>
      </div>

      <div class="creation-source-panel" id="hero-source-panel" hidden></div>

      <p class="ig-error" id="hero-door-error"
         role="status" aria-live="polite"></p>

      <div class="composer-card__actions">
        <button type="submit" class="ig-button" id="hero-door-submit"
                disabled aria-label="Continue to sketch">
          <span>Continue</span>
          <svg viewBox="0 0 24 24" width="16" height="16"
               fill="none" stroke="currentColor" stroke-width="2.2"
               stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <line x1="5" y1="12" x2="19" y2="12"/>
            <polyline points="12 5 19 12 12 19"/>
          </svg>
        </button>
      </div>
    </form>
  </div>
</section>
```

- [ ] **Step 3: Verify the previous `<canvas id="intro-particle-canvas">` is gone**

Run: `grep -n 'intro-particle-canvas\|intro-particles' public/index.html`
Expected: no matches. (`intro-particles.js` will no-op since it queries the canvas element and exits if not found.)

- [ ] **Step 4: Verify no orphaned classes**

Run: `grep -n 'ignition-eyebrow\|ig-highlight\|hero-threshold-field' public/index.html`
Expected: no matches in the new ignition-view block. (Old classes — should not remain.)

- [ ] **Step 5: Commit**

```bash
git add public/index.html
git commit -m "html: ignition-view markup — paper composer + witness anchor

Replaces the old hero-threshold-field markup with the paper composer
(.composer-card + .composer-card__field). Adds the witness anchor
inert SVG diamond above the title. Title carries the violet-deep
.ig-title__emphasis span on 'actually explain'. Source-attach is now
a journal-meta line inside the card; the source panel is reused as-
is via #hero-source-panel. Cap gate renders above the form (composer
locks but stays visible at 9-concept board cap). #ignition-view now
carries the [hidden] attribute by default.

The <canvas id=intro-particle-canvas> is removed; intro-particles.js
no-ops cleanly without it.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 11: Update `#launch-pad-view` markup in `public/index.html`

**Files:**
- Modify: `public/index.html` (the existing `<section id="launch-pad-view">` block, currently around lines 326–353)

- [ ] **Step 1: Locate the block**

Run: `grep -n '<section id="launch-pad-view"' public/index.html`

- [ ] **Step 2: Replace with the new markup**

Replace the entire `<section id="launch-pad-view">` block through its closing `</section>` with:

```html
<!-- Launch Pad: starting-sketch capture (paper system) -->
<section id="launch-pad-view" class="primary-view launch-pad-view"
         aria-labelledby="launch-pad-title" hidden>
  <div class="launch-pad-view__inner">
    <div class="witness-anchor" aria-hidden="true">
      <svg viewBox="0 0 28 28" width="28" height="28">
        <polygon class="witness-anchor__shape" points="14,2 26,14 14,26 2,14"/>
      </svg>
    </div>

    <p class="ig-concept-mark">
      <span class="ig-concept-mark__key">on </span><span
        class="ig-concept-mark__name" id="launch-pad-concept-name"></span>
    </p>

    <h1 class="ig-title" id="launch-pad-title" tabindex="-1">
      What do you already think<br>is inside this concept?
    </h1>

    <p class="ig-helper">
      Name the parts, guesses, examples, or confusions you have.
    </p>

    <form class="composer-card composer-card--tall" id="launch-pad-form"
          onsubmit="return App.runLaunchPadAction(event)" autocomplete="off">
      <textarea class="composer-card__field" id="launch-pad-input"
                rows="5" maxlength="1200"
                placeholder="A sentence or two is plenty — be specific over comprehensive."
                aria-describedby="launch-pad-validation"
                aria-label="What do you already think is inside this concept?"></textarea>

      <p class="ig-error" id="launch-pad-validation"
         role="status" aria-live="polite"></p>

      <div class="composer-card__actions">
        <button type="submit" class="ig-button" id="launch-pad-submit" disabled>
          <span>Build my map</span>
          <svg viewBox="0 0 24 24" width="14" height="14"
               fill="none" stroke="currentColor" stroke-width="2.2"
               stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <line x1="5" y1="12" x2="19" y2="12"/>
            <polyline points="12 5 19 12 12 19"/>
          </svg>
        </button>
      </div>
    </form>

    <p class="ig-footnote">
      Study content stays locked until the cold attempt.
    </p>
  </div>
</section>
```

- [ ] **Step 3: Commit**

```bash
git add public/index.html
git commit -m "html: launch-pad-view markup — paper composer (tall) + concept mark

Replaces the old launch-pad-form markup with the paper composer
in --tall variant (5 ruled lines). Adds the witness anchor and the
.ig-concept-mark plain-typeset 'on Photosynthesis' line above the
title. Footnote 'Study content stays locked until the cold attempt.'
sits below the form. Textarea aria-label matches the heading text
so screen readers announce identical context whether focus lands on
the heading or the field.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 12: Update `public/js/app.js`

**Files:**
- Modify: `public/js/app.js` (the existing `showIgnition`, `hideIgnition`, `hidePrimaryViews`, `renderIgnitionGate` functions, plus busy-state callsites in `runSourceAttachedSubmit` if any)

- [ ] **Step 1: Locate the existing functions**

Run: `grep -n 'function showIgnition\|function hideIgnition\|function renderIgnitionGate\|function hidePrimaryViews\|is-building-route\|aria-busy' public/js/app.js`

Note the line ranges of `showIgnition`, `hideIgnition`, `renderIgnitionGate`, and `hidePrimaryViews`.

- [ ] **Step 2: Replace `showIgnition`**

Find the existing `function showIgnition()` and replace its body with:

```js
function showIgnition() {
  setNavActive('nav-ignition');
  clearSettingsPanel();
  teardownMapView();
  hidePrimaryViews();
  document.getElementById('ignition-view').hidden = false;
  renderIgnitionGate();
  if (window.innerWidth < 900) closeDrawer();
  // Focus the writing surface directly. The textarea's aria-label carries
  // the heading text so screen readers announce on focus. A heading-first
  // bounce would interrupt the announcement.
  const field = document.getElementById('hero-single-input-field');
  if (field) requestAnimationFrame(() => field.focus());
}
```

- [ ] **Step 3: Replace `hideIgnition`**

```js
function hideIgnition() {
  document.getElementById('ignition-view').hidden = true;
}
```

- [ ] **Step 4: Update `hidePrimaryViews` to use `[hidden]` for ignition**

Find `hidePrimaryViews`. The existing function probably contains a line like:

```js
if (ignitionView) ignitionView.classList.remove('visible');
```

Replace with:

```js
if (ignitionView) ignitionView.hidden = true;
```

Other view handlers in this function keep their existing convention.

- [ ] **Step 5: Replace `renderIgnitionGate`**

Find the existing `function renderIgnitionGate()` and replace its body with:

```js
function renderIgnitionGate() {
  const atCap = loadConcepts().length >= BOARD_SLOT_COUNT;
  const gate = document.getElementById('ignition-cap-gate');
  const form = document.getElementById('hero-single-input');
  const field = document.getElementById('hero-single-input-field');
  const submit = document.getElementById('hero-door-submit');
  const capCta = gate?.querySelector('.ig-button');

  if (gate) gate.hidden = !atCap;
  if (form) form.dataset.state = atCap ? 'locked' : '';
  if (field) field.disabled = atCap;
  if (submit) {
    const fieldValue = (field?.value || '').trim();
    const ready = fieldValue.length >= 2;
    submit.disabled = atCap || !ready;
  }

  if (atCap && document.activeElement === field && capCta) {
    capCta.focus();
  }

  ['nav-ignition', 'bn-ignition'].forEach((id) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.toggle('at-cap', atCap);
    el.title = atCap ? 'Library full. Retire a concept to add another.' : '';
  });
}
```

- [ ] **Step 6: Update busy-state setters**

Search for sites that currently set `aria-busy` and `is-building-route`:

Run: `grep -n 'is-building-route\|aria-busy' public/js/app.js`

For each site that toggles the busy state on the ignition form, replace patterns like:

```js
view.setAttribute('aria-busy', 'true');
view.classList.add('is-building-route');
```

with:

```js
form.setAttribute('aria-busy', 'true');
form.dataset.state = 'busy';
```

…where `form = document.getElementById('hero-single-input')`. And replace teardown pairs:

```js
view.removeAttribute('aria-busy');
view.classList.remove('is-building-route');
```

with:

```js
form.removeAttribute('aria-busy');
form.dataset.state = '';
```

If the existing code has helper functions `clearBuildingState()`, update them in place rather than rewriting callers.

- [ ] **Step 7: Verify the dev server still loads without console errors**

Run: `bash scripts/dev.sh` and open `http://localhost:8000/` → click "New concept" in the sidebar.

Expected: ignition view appears (paper composer, witness anchor, ruled paper textarea); no console errors. Type a 2-char concept name; confirm submit becomes enabled. Click submit; launch-pad view appears.

- [ ] **Step 8: Commit**

```bash
git add public/js/app.js
git commit -m "js(app): drive ignition visibility via [hidden] + data-state

- showIgnition / hideIgnition / hidePrimaryViews now toggle the
  [hidden] attribute on #ignition-view, replacing the prior
  classList.add('visible') / remove('visible') pattern.
- showIgnition focuses the field directly on next animation frame;
  no heading-first bounce (aria-label provides SR announcement).
- renderIgnitionGate now sets data-state='locked' on the composer
  (instead of hiding it) so the user keeps the spatial cue at 9-
  concept cap. Routes focus to the cap-gate CTA when the field was
  active at the moment cap engaged.
- Busy state on the door is form.dataset.state='busy' + aria-busy
  on the form; replaces the prior is-building-route class.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 13: Update `public/js/launch-pad.js`

**Files:**
- Modify: `public/js/launch-pad.js`

- [ ] **Step 1: Locate the relevant blocks**

Run: `grep -n 'export function showLaunchPad\|ag-lp-arriving\|is-building-route\|_lpArrivingCleanup\|export async function runLaunchPadAction' public/js/launch-pad.js`

- [ ] **Step 2: Replace the showLaunchPad reveal block**

Find the block that currently does:

```js
const view = document.getElementById('launch-pad-view');
if (!view) return;
view.removeAttribute('hidden');
view.removeAttribute('aria-busy');
view.classList.remove('is-building-route');

// Earned-motion ignition handoff. ...
view.classList.remove('ag-lp-arriving');
void view.offsetWidth;
view.classList.add('ag-lp-arriving');
if (_lpArrivingCleanup) window.clearTimeout(_lpArrivingCleanup);
_lpArrivingCleanup = window.setTimeout(() => {
  view.classList.remove('ag-lp-arriving');
  _lpArrivingCleanup = null;
}, 700);
```

Replace with:

```js
const view = document.getElementById('launch-pad-view');
if (!view) return;
view.hidden = false;
view.removeAttribute('aria-busy');
const form = document.getElementById('launch-pad-form');
if (form) form.dataset.state = '';
```

(The `ig-screen-in` keyframe on `.launch-pad-view__inner` now handles the entrance animation; no class manipulation needed.)

Delete the module-scope `let _lpArrivingCleanup = null;` declaration and its corresponding cleanup.

- [ ] **Step 3: Replace the input wiring + focus call**

Find the block at the end of `showLaunchPad` that currently does:

```js
if (input) {
  const fresh = input.cloneNode(true);
  input.parentNode.replaceChild(fresh, input);
  // ... event listeners ...
  requestAnimationFrame(() => fresh.focus());
}
```

Keep the cloneNode + listener-rebinding logic exactly as-is. The only change is to make sure the final focus is on the textarea (`fresh.focus()`); no heading-first bounce. The current code already focuses the field directly — just confirm the spec lines up.

- [ ] **Step 4: Update `runLaunchPadAction` busy-state lines**

Find:

```js
const view = document.getElementById('launch-pad-view');
if (view) {
  view.setAttribute('aria-busy', 'true');
  view.classList.add('is-building-route');
}
const clearBuildingState = () => {
  if (!view) return;
  view.removeAttribute('aria-busy');
  view.classList.remove('is-building-route');
};
```

Replace with:

```js
const form = document.getElementById('launch-pad-form');
if (form) {
  form.setAttribute('aria-busy', 'true');
  form.dataset.state = 'busy';
}
const clearBuildingState = () => {
  if (!form) return;
  form.removeAttribute('aria-busy');
  form.dataset.state = '';
};
```

- [ ] **Step 5: Verify there are no remaining `ag-lp-arriving` or `is-building-route` references in this file**

Run: `grep -n 'ag-lp-arriving\|is-building-route\|_lpArrivingCleanup' public/js/launch-pad.js`
Expected: no matches.

- [ ] **Step 6: Manual verification — Screen 1 → Screen 2 flow**

Run: `bash scripts/dev.sh`. Open `http://localhost:8000/`. Click "New concept" → type "Photosynthesis" → click Continue.

Expected: launch-pad view appears with witness anchor, "on Photosynthesis" concept mark, "What do you already think is inside this concept?" title, and tall paper composer with ruled lines. Console clean.

Type "leaves convert sunlight to sugar" → submit. Expected: brief busy state on the form (composer dims to 0.55 opacity), then graph view appears.

- [ ] **Step 7: Commit**

```bash
git add public/js/launch-pad.js
git commit -m "js(launch-pad): drive visibility via [hidden] + form.data-state

- showLaunchPad uses view.hidden = false (replacing
  removeAttribute('hidden')) and drops the ag-lp-arriving class +
  _lpArrivingCleanup timer entirely; the new .launch-pad-view__inner
  ig-screen-in keyframe in layout.css handles the entrance.
- runLaunchPadAction busy state is now form.dataset.state='busy' on
  #launch-pad-form, mirroring the door's pattern. Removed
  is-building-route from all callsites in this file.
- Focus routing on mount is unchanged (field-direct focus); the
  cloneNode listener-rebind pattern is preserved.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 14: Delete migrated rules from `public/antigravity.css`

**Files:**
- Modify: `public/antigravity.css`

This is the Strangler Fig amputation step. Use the audit results from Task 2.

- [ ] **Step 1: Open antigravity.css and identify rule blocks to delete**

Run: `grep -n 'body\.antigravity-theme #ignition-view\|body\.antigravity-theme #launch-pad-view\|body\.antigravity-theme \.ignition-title\|body\.antigravity-theme \.ignition-cap-gate\|body\.antigravity-theme \.ignition-view__inner\|body\.antigravity-theme \.intro-particles\|body\.antigravity-theme \.launch-pad-' public/antigravity.css`

Plus, for the audit-confirmed delete candidates from Task 2:

```bash
grep -n 'body\.antigravity-theme \.hero-single-input\|body\.antigravity-theme \.hero-source-attach' public/antigravity.css
```

(Do NOT include `.hero-eyebrow`, `.hero-state-chip`, `.hero-door-error` unless the Task 2 audit confirmed they are ignition-only — these are likely shared with the dashboard hero card and stay until Wave 2.)

- [ ] **Step 2: Delete each identified rule block**

For each grep hit, delete the entire CSS rule (from the `body.antigravity-theme …` selector through the closing `}` brace, including any media-query wrappers if the rule lives inside one).

If multiple selectors share a rule (comma-separated), you can either delete the whole rule (if all selectors are in scope) or strip just the in-scope selector(s) from the list.

Also delete:
- The `@keyframes ag-lp-arriving` keyframe block.
- Any `body.antigravity-theme #ignition-view::before` / `::after` / `#launch-pad-view::before` / `::after` blocks.
- Any block targeting `.intro-particles`.

Do NOT delete:
- `body.antigravity-theme` itself (the body class stays for other waves).
- Any selector for `#grid-container`, `.hero-card`, `.hero-primary-action`, `.library-*`, `.settings-*`, `.sidebar-nav-item`, `.bottom-nav-item`, `.hero-eyebrow`, `.hero-state-chip`, `.hero-door-error`, `#timer-display`, or generic `h1, h2, h3` rules — those belong to other waves.

- [ ] **Step 3: Run a final grep to confirm zero ignition / launch-pad references remain**

Run:

```bash
grep -nE 'antigravity-theme [^{}]*(ignition|launch-pad|intro-particles|ag-lp-arriving|is-building-route|ignition-cap-gate)' public/antigravity.css
```

Expected: zero matches. If any remain, delete them.

For the audit-deferred selectors:

```bash
grep -nE 'antigravity-theme [^{}]*(hero-eyebrow|hero-state-chip|hero-door-error)' public/antigravity.css
```

Expected: matches still present (deferred to Wave 2).

- [ ] **Step 4: Manual verification — light + dark, every primary view**

Run: `bash scripts/dev.sh`. Open `http://localhost:8000/`.

Visit each primary view in light mode AND dark mode:

- **Dashboard:** unchanged from before this PR. Glass hero card still glassy.
- **Ignition view:** new paper system. Cream paper background (graphite in dark), witness anchor, ruled-paper composer, violet-deep "actually explain" emphasis. NO leftover gradient washes, NO particle canvas, NO glass card.
- **Launch pad view:** paper system, tall composer, "on Photosynthesis" plain typeset eyebrow.
- **Library view:** unchanged from before this PR.
- **Settings view:** unchanged from before this PR.

Console clean across all views.

If the ignition view shows any residual glass / glow / radial-gradient backdrop, an antigravity rule was missed — return to Step 1 and re-grep.

- [ ] **Step 5: Commit (with audit summary in message)**

```bash
git add public/antigravity.css
git commit -m "css(antigravity): delete ignition + launch-pad rules

Strangler Fig amputation step — these rules are replaced by the
paper layer. Deleted:

- All body.antigravity-theme #ignition-view* (incl. ::before, ::after)
- All body.antigravity-theme #launch-pad-view* (incl. ::before, ::after)
- @keyframes ag-lp-arriving
- All body.antigravity-theme .ignition-title*, .ignition-cap-gate*,
  .ignition-view__inner*, .intro-particles*, .launch-pad-* blocks
- All body.antigravity-theme .hero-single-input* (audited: only used
  in #ignition-view markup; safe to delete)
- All body.antigravity-theme .hero-source-attach* (same audit verdict)

Deferred to later waves (audit found these reach into the dashboard
hero card or other views, NOT just ignition):
- .hero-eyebrow* — used by hero card
- .hero-state-chip* — used by hero card
- .hero-door-error* — used by hero card

The body.antigravity-theme class itself remains; later waves remove it.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 15: Browser smoke + a11y + cross-browser verification

**Files:** none modified — verification only.

- [ ] **Step 1: Local browser smoke**

Run: `bash scripts/qa-smoke.sh local`
Expected: pass clean. Investigate any failure before continuing.

- [ ] **Step 2: Manual flow verification — light mode**

Run: `bash scripts/dev.sh`. In Chrome:

- Click "New concept" — Ignition view appears with paper composer, witness anchor visible, "Ignition · 1 of 2" eyebrow, title with violet "actually explain", helper, ruled-paper textarea, source meta line `source: none yet — add`, disabled submit.
- Type "p" — submit stays disabled.
- Type "ph" — submit enables (violet fill).
- Hover submit — translateY(-1px) lift + soft violet shadow.
- Tab to submit — focus ring appears, no transform jitter.
- Tab back to source-meta `add` — click expands the source panel inline.
- URL tab → paste URL → click Attach → confirm flow continues normally.
- Cancel out of source panel → submit "Photosynthesis" with no source.
- Launch pad appears: "on Photosynthesis", tall composer.
- Type a sketch ≥3 substantive words → "Build my map" enables.
- Submit → composer dims to 0.55 opacity (busy state) → graph view appears on success.

- [ ] **Step 3: Manual flow verification — dark mode**

Toggle dark theme. Repeat Step 2. Confirm:

- Page background is graphite-900 (#18181b).
- Composer card is graphite-800 (#1c1c20) with faint ruled lines.
- "actually explain" is violet-300 (#c8a8f7).
- Submit hover is violet-300 at 85% opacity (slight darken).
- Console clean.

- [ ] **Step 4: Reduced motion check**

System Settings → Display → Reduce Motion ON (macOS) or DevTools → Rendering → Emulate `prefers-reduced-motion: reduce`.

Reload Ignition view. Confirm:

- No `ig-screen-in` fade-up on view mount.
- Submit hover does not lift.
- Source-panel expand / collapse: instant (no transition).
- Composer dim on busy state: still applies (it's a transition, not animation, but spec accepts the dim as a useful signal — confirm transition is suppressed if the spec demanded that; otherwise the dim is OK).

- [ ] **Step 5: Cap-state verification**

Open DevTools console:

```js
// Force 9 concepts onto the board for testing.
const fake = Array.from({length: 9}, (_, i) => ({
  id: `test-${i}`, name: `Concept ${i}`, createdAt: new Date().toISOString(),
  state: 'growing', contentPreview: '', graphData: null,
}));
localStorage.setItem('socratink:concepts', JSON.stringify(fake));
location.reload();
```

Click "New concept". Expected:

- Cap gate visible above composer.
- Composer dimmed to opacity 0.55 (`data-state="locked"`).
- Textarea + submit disabled (cannot type, cannot click).
- "Open library" focused if focus was on textarea when cap engaged.

Restore: `localStorage.removeItem('socratink:concepts'); location.reload();`

- [ ] **Step 6: Lighthouse a11y audit**

DevTools → Lighthouse → Accessibility audit on Ignition view, then Launch Pad view, in light mode and dark mode.

Expected: ≥95 on each.

- [ ] **Step 7: axe DevTools audit**

Install the axe DevTools browser extension if not already installed. Run on Ignition view and Launch Pad view in both modes.

Expected: zero "serious" or "critical" issues.

- [ ] **Step 8: Cross-browser smoke**

Open Ignition view + Launch Pad view in:

- Chrome (already verified above).
- Safari desktop.
- Firefox desktop.
- iOS Safari at 360px viewport (DevTools device emulator → iPhone SE).

Each browser must render correctly. The 360px width test is critical — confirm the title doesn't overflow and the composer card sits within the viewport.

- [ ] **Step 9: Telemetry verification**

Watch the telemetry queue while running flows:

```js
JSON.parse(localStorage.getItem('socratink:telemetry') || '[]').slice(-10)
```

Confirm the seven event names fire as expected:

- `concept_create.door.submit` — on Screen 1 submit
- `concept_create.launch_pad.entered` — on launch pad mount
- `concept_create.launch_pad.submit` — on Screen 2 submit
- `concept_create.bypass_rejected` — on a thin sketch
- `concept_create.cap_exceeded` — on board cap

(`evaporated` fires when shell expires; `persistence` events fire on success — both harder to induce manually but verify against the source.)

- [ ] **Step 10: Audio FX smoke**

With volume on, focus the Ignition textarea. Confirm a "tap" sound plays. Type a few keystrokes. Confirm "click" sounds play. Click submit (when enabled). Confirm a tap.

- [ ] **Step 11: No commit**

This task is verification-only. If anything in Steps 1–10 fails, return to the relevant earlier task and fix. Re-run smoke before proceeding to Task 16.

---

## Task 16: Push to dev + verify Vercel preview

**Files:** none modified.

- [ ] **Step 1: Final preflight**

Run: `bash scripts/qa-smoke.sh local`
Expected: pass.

Run: `git log -20 --oneline`
Expected: all commits from this plan are present in order.

Run: `grep -rn '<<<<<<\|>>>>>>\|=======' public/css/ public/js/ public/index.html public/antigravity.css 2>/dev/null`
Expected: no matches (no conflict markers).

- [ ] **Step 2: Push to dev**

Run: `git push origin dev`

- [ ] **Step 3: Wait for Vercel preview deployment**

Watch the Vercel dashboard for the dev preview to deploy. Once green, open the preview URL.

- [ ] **Step 4: Repeat verification on Vercel preview**

Visit Ignition view + Launch Pad view on the live preview URL. Repeat Steps 2–3 of Task 15 (light + dark flow).

If the preview shows a regression that didn't appear locally, it's likely a `vercel.json` rewrite or asset-path issue with the new `index.css` `@import` paths. Check:
- `vercel.json` `routes` / `rewrites` section.
- That `public/css/paper.css` is included in the deployed serverless function (look at `vercel.json` `functions[].includeFiles`).

- [ ] **Step 5: Smoke against deployed preview**

Run: `bash scripts/qa-smoke.sh https://<vercel-preview-url>`
Expected: pass clean.

- [ ] **Step 6: No commit**

Wave 1 is complete on `dev`. Production promotion happens via dev → main PR per project convention; that's a separate decision out of this plan's scope.

---

## Self-review checklist

- **Spec coverage:**
  - paper.css component creation → Tasks 3–7
  - Layout view shell update → Task 8
  - index.css paper layer registration → Task 9
  - HTML markup updates (ignition + launch-pad) → Tasks 10, 11
  - JS visibility / focus / cap-gate / busy-state changes → Tasks 12, 13
  - Antigravity rule deletion (Strangler Fig) → Tasks 2 (audit), 14 (delete)
  - Browser smoke + a11y + cross-browser + telemetry + audio → Task 15
  - Push + Vercel preview verification → Task 16
- **No placeholders:** Every step contains either runnable commands or full code. No "implement appropriate validation" — explicit.
- **Type consistency:** Class names match across spec sections and code blocks (`.composer-card`, `.composer-card__field`, `.composer-card--tall`, `.witness-anchor`, `.witness-anchor__shape`, `.ig-title`, `.ig-title__emphasis`, `.ig-eyebrow`, `.ig-eyebrow__dot`, `.ig-concept-mark`, `.ig-concept-mark__key`, `.ig-concept-mark__name`, `.ig-helper`, `.ig-footnote`, `.ig-error`, `.ig-button`, `.ig-button--ghost`, `.journal-meta`, `.journal-meta__key`, `.journal-meta__value`, `.journal-meta__sep`, `.journal-meta__add`, `.ignition-cap-gate`, `.ignition-cap-gate__message`, `.creation-source-panel*`, `.overlay-*`). Consistent.
- **Frequent commits:** 12 commits during implementation (Tasks 3–14), each scoped to a single logical step.
