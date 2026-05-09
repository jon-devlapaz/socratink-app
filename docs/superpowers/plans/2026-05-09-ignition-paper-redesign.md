# Paper Wave 1 — Ignition + Launch Pad redesign — Implementation Plan

> **STATUS: SHIPPED on `dev` (2026-05-09).** Plan was executed in a single subagent dispatch; final state on `dev` differs from the original plan in five places (four post-shipping persona-driven subtractions + the launch-pad button rename). **Future implementers reading this plan: do NOT re-introduce the eyebrow, Screen 1 helper, button arrows, or "actually explain" emphasis. See the spec's "Post-shipping revisions" section for rationale, and the markup blocks in the spec (not this plan) as the canonical reference.** This plan is preserved as the build record; the spec carries the current truth.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the Ignition + Launch Pad views to mirror socratink.ai's paper journal identity. Behavioral pipeline preserved unchanged.

**Architecture:** Add a new `public/css/paper.css` registered in `@layer paper` (the layer reserved by Wave 0). New rules reference only the existing tokens in `variables.css` plus the two paper additions from Wave 0 (`--rule-line`, `--rule-step`). Update view shells in `layout.css`, markup in `index.html`, JS in `app.js` and `launch-pad.js`. Delete the corresponding rules from `antigravity.css` in the same PR (Strangler Fig amputation).

**Tech Stack:** Vanilla CSS (no build step). Existing tokens from `variables.css`. CSS Cascade Layers from Wave 0.

**Spec:** `docs/superpowers/specs/2026-05-09-ignition-paper-redesign-design.md`

**Umbrella:** `docs/superpowers/specs/2026-05-09-paper-migration-plan.md`

**Hard prerequisite:** Paper Wave 0 merged. Verify with: `ls public/css/index.css && grep -n '@layer components' public/css/index.css && grep -n 'rule-line' public/css/variables.css`. Do NOT start this plan if any of those checks fails.

**Branch:** Work on `dev`. Commit straight to `dev`. No worktree, no branch switch.

---

## File structure

| File | Action | Responsibility |
|---|---|---|
| `public/css/paper.css` | **create** | All new component CSS (composer-card, witness-anchor, ig-title, ig-button, journal-meta, ignition-cap-gate, source-panel restyle). References only existing tokens + `--rule-line` + `--rule-step`. Loaded into `@layer paper`. |
| `public/css/index.css` | **modify** | Uncomment / add the `@import url('paper.css?v=1') layer(paper);` line. Bump its own `?v=1` to `?v=2` in the `<link>` tag. |
| `public/index.html` | **modify** | Replace `#ignition-view` and `#launch-pad-view` markup blocks. Remove `<canvas id="intro-particle-canvas">`. Bump `<link>` version to `?v=2`. |
| `public/css/layout.css` | **modify** | Replace `#ignition-view` + `#launch-pad-view` shell rules + add `ig-screen-in` keyframe + reduced-motion. |
| `public/js/app.js` | **modify** | `showIgnition` / `hideIgnition` / `hidePrimaryViews` use `[hidden]` attribute. `renderIgnitionGate` sets `data-state="locked"` on the form (composer stays visible at cap). Busy state uses `data-state="busy"`. |
| `public/js/launch-pad.js` | **modify** | `showLaunchPad` uses `[hidden]`; drop `ag-lp-arriving` class manipulation; busy state uses `data-state="busy"` on form. |
| `public/antigravity.css` | **modify** | Delete migrated ignition + launch-pad rules. |

---

## Task 1: Verify Wave 0 prerequisite

**Files:** none modified.

- [ ] **Step 1: Confirm Wave 0 files exist and tokens are wired**

```bash
ls public/css/index.css                                    # exists
grep -n '@layer components, legacy, paper' public/css/index.css  # found
grep -n 'rule-line' public/css/variables.css               # found
grep -nF 'href="/css/index.css' public/index.html          # exactly one match
```

If any check fails, halt — Wave 0 was not merged.

- [ ] **Step 2: Verify tokens are visible in browser**

`bash scripts/dev.sh`. In DevTools → Console:

```js
getComputedStyle(document.documentElement).getPropertyValue('--rule-step')  // ' 32px'
getComputedStyle(document.documentElement).getPropertyValue('--rule-line')  // a non-empty rgba
getComputedStyle(document.documentElement).getPropertyValue('--accent-primary')  // ' #9067c6'
getComputedStyle(document.documentElement).getPropertyValue('--primary-fill')    // ' #7a59aa'
getComputedStyle(document.documentElement).getPropertyValue('--surface-card')    // a non-empty color
```

All five must return non-empty values.

- [ ] **Step 3: No commit.** Verification only.

---

## Task 2: Pre-deletion grep audit on antigravity selectors

**Files:** none modified — produces an audit log captured in commit messages.

- [ ] **Step 1: Audit each candidate selector**

For each selector below, grep `public/index.html` and `public/js/`. Selector is **safe to delete** in this PR if matches appear only inside `#ignition-view` or `#launch-pad-view` markup. Otherwise flag for Wave 2+.

```bash
grep -n 'ignition-view\|ignition-title\|ignition-cap-gate\|ignition-view__inner' public/index.html public/js/*.js
grep -n 'launch-pad-view\|launch-pad-form\|launch-pad-input\|launch-pad-submit\|launch-pad-validation\|launch-pad-helper\|launch-pad-title\|launch-pad-concept-name\|launch-pad-footer\|launch-pad-view__inner\|ag-lp-arriving\|is-building-route' public/index.html public/js/*.js
grep -n 'intro-particles\|intro-particle-canvas' public/index.html public/js/*.js
grep -n 'hero-single-input\|hero-source-attach\|hero-source-panel\|hero-eyebrow\|hero-state-chip\|hero-door-error' public/index.html public/js/*.js
```

- [ ] **Step 2: Record audit results**

Create `/tmp/wave1-deletion-audit.txt` capturing the grep output for the audit-before-deleting candidates. For each, record:

- Selector name
- Files where it appears
- Whether the appearances are confined to `#ignition-view` / `#launch-pad-view` markup
- Verdict: DELETE in this wave / DEFER to Wave 2

Expected verdicts:
- `.hero-single-input`, `.hero-source-attach`, `.hero-source-panel` — used only by ignition's form. **DELETE.**
- `.hero-eyebrow`, `.hero-state-chip` — used by dashboard hero card. **DEFER.**
- `.hero-door-error` — used by ignition only (despite the `hero-` prefix); confirm via grep. Likely **DELETE**.
- `.intro-particles`, `intro-particle-canvas` — markup is removed in this PR; CSS rules can be deleted from antigravity. **DELETE.**

- [ ] **Step 3: No commit.** Audit task; deletion happens in Task 14.

---

## Task 3: Create `public/css/paper.css` — full file

**Files:**
- Create: `public/css/paper.css`

- [ ] **Step 1: Write the file**

Write the entire spec content from `docs/superpowers/specs/2026-05-09-ignition-paper-redesign-design.md` (the `paper.css` block) to `public/css/paper.css`. The full content is:

```css
/* ════════════════════════════════════════════════════════════════════
   paper.css — PAPER SYSTEM components.
   Imported via index.css into @layer paper, which beats @layer legacy
   (antigravity.css) on migrated surfaces. References only tokens
   defined in variables.css plus --rule-line and --rule-step (added in
   Paper Wave 0).
   See docs/superpowers/specs/2026-05-09-ignition-paper-redesign-design.md
   ════════════════════════════════════════════════════════════════════ */

/* ── Composer card ──────────────────────────────────────────── */

.composer-card {
  width: 100%;
  max-width: 460px;
  margin: 0 auto;
  box-sizing: border-box;
  padding: var(--space-5);
  background: var(--surface-card);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-btn);
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
      var(--rule-line) calc(var(--rule-step) - 1px),
      var(--rule-line) var(--rule-step)
    ) local;
  background-position: 0 var(--composer-grid-offset, 0px);
  font-family: inherit;
  font-size: var(--text-base);
  line-height: var(--rule-step);
  color: var(--text-strong);
  padding: var(--composer-grid-offset, 8px) 0 0 0;
  min-height: calc(var(--rule-step) * 3);
}

.composer-card--tall .composer-card__field {
  min-height: calc(var(--rule-step) * 5);
}

.composer-card__field::placeholder {
  color: var(--text-muted);
  font-style: italic;
}

.composer-card__field:focus-visible {
  box-shadow: var(--accent-ring);
}

.composer-card__actions {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--space-3);
}

.composer-card[data-state="locked"],
.composer-card[data-state="busy"] {
  opacity: 0.55;
  transition: opacity var(--duration-quick) var(--ease-standard);
}
.composer-card[data-state="locked"] :is(button, textarea, input),
.composer-card[data-state="busy"]   :is(button, textarea, input) {
  pointer-events: none;
}
.composer-card__field:disabled {
  color: var(--text-muted);
  -webkit-text-fill-color: var(--text-muted);
  opacity: 1;
}

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
  stroke: var(--text-muted);
  stroke-width: 1.2;
  vector-effect: non-scaling-stroke;
}

/* ── Title ─────────────────────────────────────────────────── */

.ig-title {
  margin: 0 0 var(--space-5);
  text-align: center;
  font-family: var(--font-display);
  font-size: var(--text-3xl);
  line-height: var(--leading-tight);
  font-weight: 700;
  letter-spacing: var(--tracking-tight);
  color: var(--text-strong);
  text-wrap: balance;
  overflow-wrap: anywhere;
  word-break: break-word;
  hyphens: auto;
}
.ig-title__emphasis {
  font-style: italic;
  font-weight: 700;
  color: var(--accent-primary);
  text-decoration: underline;
  text-decoration-color: var(--accent-border-strong);
  text-decoration-thickness: 0.08em;
  text-underline-offset: 0.16em;
  text-decoration-skip-ink: none;
}

/* ── Eyebrow (Screen 1) ────────────────────────────────────── */

.ig-eyebrow {
  margin: 0 0 var(--space-4);
  text-align: center;
  font-size: var(--text-sm);
  font-weight: 700;
  color: var(--accent-primary);
  letter-spacing: var(--tracking-kicker);
  text-transform: uppercase;
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
  color: var(--text-muted);
  overflow-wrap: anywhere;
}
.ig-concept-mark__key { font-style: italic; }
.ig-concept-mark__name {
  color: var(--text-strong);
  font-weight: 600;
  margin-left: 4px;
}

.launch-pad-view__inner > .ig-title {
  margin-top: var(--space-2);
}

/* ── Helper + footnote + error ─────────────────────────────── */

.ig-helper {
  margin: 0 0 var(--space-4);
  text-align: center;
  font-size: var(--text-base);
  line-height: var(--leading-normal);
  color: var(--text-muted);
  overflow-wrap: anywhere;
}

.ig-footnote {
  margin: var(--space-3) auto 0;
  max-width: 460px;
  padding-left: var(--space-1);
  font-size: var(--text-xs);
  color: var(--text-muted);
  overflow-wrap: anywhere;
}

.ig-error {
  margin: var(--space-3) 0 0;
  font-size: var(--text-xs);
  color: var(--text-muted);
  min-height: 1em;
}
.ig-error:empty { margin-top: 0; }

/* ── Source-meta line ──────────────────────────────────────── */

.composer-card .journal-meta {
  margin-top: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px solid var(--border-subtle);
  background: var(--surface-card);
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
  font-size: var(--text-xs);
  color: var(--text-muted);
}
.composer-card .journal-meta__key {
  color: var(--accent-primary);
  font-weight: 700;
}
.composer-card .journal-meta__value { font-style: italic; }
.composer-card .journal-meta__sep { color: var(--text-muted); }
.composer-card .journal-meta__add {
  color: var(--accent-primary);
  font-weight: 700;
  text-decoration: underline;
  text-decoration-color: var(--accent-border);
  text-decoration-thickness: 0.06em;
  text-underline-offset: 0.2em;
  background: 0;
  border: 0;
  padding: 0;
  cursor: pointer;
  font: inherit;
}
.composer-card .journal-meta__add:hover {
  text-decoration-color: var(--accent-primary);
}

/* ── Primary action button ─────────────────────────────────── */

.ig-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  min-height: 40px;
  padding: 0 var(--space-4);
  background: var(--primary-fill);
  color: var(--text-on-primary);
  border: 1px solid var(--primary-fill);
  border-radius: var(--radius-btn);
  font-family: inherit;
  font-size: var(--text-sm);
  font-weight: 700;
  line-height: 1;
  cursor: pointer;
  transition:
    background var(--duration-quick) var(--ease-standard),
    transform  var(--duration-micro) var(--ease-standard),
    box-shadow var(--duration-quick) var(--ease-standard);
}
.ig-button:hover:not(:disabled) {
  background: var(--primary-fill-hover);
  border-color: var(--primary-fill-hover);
  transform: translateY(-1px);
  box-shadow: var(--accent-shadow-md);
}
.ig-button:active:not(:disabled) {
  transform: translateY(0);
}
.ig-button:focus-visible {
  outline: none;
  transform: none;
  box-shadow: var(--accent-ring), var(--accent-shadow-md);
}
.ig-button:disabled {
  background: var(--locked);
  color: var(--text-muted);
  border-color: transparent;
  cursor: not-allowed;
  box-shadow: none;
  -webkit-text-fill-color: var(--text-muted);
  opacity: 1;
}

.ig-button--ghost {
  background: transparent;
  color: var(--accent-primary);
  border-color: var(--border-strong);
}
.ig-button--ghost:hover:not(:disabled) {
  background: var(--accent-soft);
  border-color: var(--accent-primary);
  transform: translateY(-1px);
  box-shadow: none;
}
.ig-button--ghost:focus-visible {
  outline: none;
  transform: none;
  box-shadow: var(--accent-ring);
}

/* ── Cap gate ──────────────────────────────────────────────── */

.ignition-cap-gate {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-5);
  background: var(--surface-card);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-btn);
  box-shadow: var(--shadow-card);
}
.ignition-cap-gate__message {
  margin: 0;
  font-size: var(--text-base);
  line-height: var(--leading-normal);
  color: var(--text-strong);
  overflow-wrap: anywhere;
}

/* ── Source panel restyle (uses source-panel.js's existing class names) ── */

.creation-source-panel {
  margin-top: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px solid var(--border-subtle);
  background: var(--surface-card);
}
.creation-source-panel .overlay-tabs {
  display: flex;
  gap: var(--space-1);
  border-bottom: 1px solid var(--border-subtle);
  margin-bottom: var(--space-3);
}
.creation-source-panel .overlay-tab {
  background: transparent;
  border: 0;
  border-bottom: 2px solid transparent;
  padding: var(--space-2) var(--space-3);
  font: inherit;
  font-size: var(--text-xs);
  font-weight: 700;
  color: var(--text-muted);
  cursor: pointer;
  margin-bottom: -1px;
}
.creation-source-panel .overlay-tab.active,
.creation-source-panel .overlay-tab[aria-selected="true"] {
  color: var(--accent-primary);
  border-bottom-color: var(--accent-primary);
}
.creation-source-panel .overlay-textarea,
.creation-source-panel .overlay-url-input {
  width: 100%;
  box-sizing: border-box;
  padding: var(--space-2) var(--space-3);
  background: var(--surface-card);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-btn);
  font: inherit;
  font-size: var(--text-sm);
  color: var(--text-strong);
  resize: none;
}
.creation-source-panel .overlay-textarea:focus-visible,
.creation-source-panel .overlay-url-input:focus-visible {
  outline: none;
  border-color: var(--accent-primary);
  box-shadow: var(--accent-ring);
}
.creation-source-panel .overlay-dropzone {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 80px;
  padding: var(--space-4);
  border: 1px dashed var(--border-strong);
  border-radius: var(--radius-btn);
  color: var(--text-muted);
  background: transparent;
  cursor: pointer;
}
.creation-source-panel .overlay-dropzone:focus-visible {
  outline: none;
  border-color: var(--accent-primary);
  box-shadow: var(--accent-ring);
}
.creation-source-panel .overlay-dropfeedback {
  margin: var(--space-2) 0 0;
  font-size: var(--text-xs);
  color: var(--text-muted);
}
.creation-source-panel .overlay-dropfeedback.ok    { color: var(--accent-primary); }
.creation-source-panel .overlay-dropfeedback.error { color: var(--danger); }

.creation-source-panel-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  margin-top: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px solid var(--border-subtle);
}
.creation-source-panel-cancel {
  background: transparent;
  color: var(--text-strong);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-btn);
  padding: var(--space-2) var(--space-3);
  font: inherit;
  font-size: var(--text-sm);
  font-weight: 700;
  cursor: pointer;
}
.creation-source-panel-cancel:hover {
  border-color: var(--accent-primary);
  background: var(--accent-soft);
}
.creation-source-panel-attach {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  background: var(--primary-fill);
  color: var(--text-on-primary);
  border: 1px solid var(--primary-fill);
  border-radius: var(--radius-btn);
  padding: var(--space-2) var(--space-4);
  font: inherit;
  font-size: var(--text-sm);
  font-weight: 700;
  cursor: pointer;
}
.creation-source-panel-attach:disabled {
  background: var(--locked);
  color: var(--text-muted);
  border-color: transparent;
  cursor: not-allowed;
  -webkit-text-fill-color: var(--text-muted);
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

- [ ] **Step 2: Verify file parses cleanly**

Run: `python3 -c "open('public/css/paper.css').read()"`

- [ ] **Step 3: Commit**

```bash
git add public/css/paper.css
git commit -m "css(paper): introduce paper.css with all Wave 1 components

Single commit for the full paper component set: composer-card +
field with rule-grid background-attachment:local, witness-anchor,
ig-title + ig-title__emphasis, ig-eyebrow + concept-mark, helper +
footnote + error live region, journal-meta source line, ig-button
primary + ghost variants, ignition-cap-gate, source-panel restyle
(uses source-panel.js's existing .creation-source-panel and
.overlay-* class names so JS is untouched), reduced-motion block.

References only existing tokens from variables.css plus --rule-line
and --rule-step from Paper Wave 0. No new token vocabulary.

Not yet imported by index.css — wiring lands in the next commit.

Paper Wave 1.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Update `public/css/index.css` to import paper.css

**Files:**
- Modify: `public/css/index.css`

- [ ] **Step 1: Add the paper import**

Find the commented line:

```css
/* @import url('paper.css') layer(paper);  — reserved; introduced in Wave 1 */
```

Replace with:

```css
@import url('paper.css?v=1')           layer(paper);
```

- [ ] **Step 2: Verify import resolves**

Run: `bash scripts/dev.sh` and open `http://localhost:8000/`. DevTools Network: confirm `/css/paper.css?v=1` returns 200.

- [ ] **Step 3: Bump index.css version in `public/index.html`**

Find: `<link rel="stylesheet" href="/css/index.css?v=1">`

Replace with: `<link rel="stylesheet" href="/css/index.css?v=2">`

- [ ] **Step 4: Commit**

```bash
git add public/css/index.css public/index.html
git commit -m "css(index): import paper.css into @layer paper

Activates the paper layer reserved in Wave 0. paper.css now wins
over @layer legacy (antigravity.css) on every selector it defines,
which is exactly the right behavior for migrated surfaces. Other
views (dashboard, library, settings) continue to be styled by
antigravity since paper.css contains no rules targeting their DOM.

Bumps index.css <link> version from ?v=1 to ?v=2.

Paper Wave 1.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Update `public/css/layout.css` view shells

**Files:**
- Modify: `public/css/layout.css` (lines 2412–2505 currently)

- [ ] **Step 1: Locate the existing blocks**

Run: `grep -n '#ignition-view\b\|#launch-pad-view\b\|.ignition-view__inner\|.launch-pad-view__inner\|@keyframes ig-screen-in' public/css/layout.css`

- [ ] **Step 2: Delete the existing blocks**

Remove every selector matching `#ignition-view`, `#ignition-view.visible`, `#launch-pad-view`, `#launch-pad-view:not([hidden])`, `.ignition-view__inner`, `.launch-pad-view__inner`, and any `@keyframes ig-screen-in` block currently in `public/css/layout.css`.

Do NOT remove unrelated rules nearby (e.g., `.ignition-cap-gate` rules — those move to paper.css and were styled differently in layout.css; remove them too if they exist there).

- [ ] **Step 3: Add the new blocks**

In the same location (or wherever feels right within layout.css), add:

```css
/* ── Ignition + Launch Pad view shells (paper system) ──────────
   Visibility is driven by the [hidden] attribute, which base.css
   already declares as `display: none !important`. No display:none
   toggle on these IDs.
   See docs/superpowers/specs/2026-05-09-ignition-paper-redesign-design.md
   ─────────────────────────────────────────────────────────── */

#ignition-view,
#launch-pad-view {
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
  animation: ig-screen-in var(--duration-cozy) var(--ease-standard) both;
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

Replaces the old #ignition-view / #launch-pad-view blocks with new
shells that reference paper-system tokens directly (--surface-page,
--space-5, etc). Adds the ig-screen-in keyframe + reduced-motion
suppression. Page background is now solid var(--surface-page) on
both views; no gradient washes, no positioned ::before/::after
blooms, no canvas.

Visibility is driven by the [hidden] attribute, leveraging base.css
line 27's existing [hidden]{display:none!important} rule. No
display:none toggle on the view IDs.

Paper Wave 1.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Update `#ignition-view` markup in `public/index.html`

**Files:**
- Modify: `public/index.html` (existing `<section id="ignition-view">` block, currently lines 278–323)

- [ ] **Step 1: Locate the block**

Run: `grep -n '<section id="ignition-view"' public/index.html`. Confirm boundaries (closing `</section>`).

- [ ] **Step 2: Replace with the new markup**

Replace the entire `<section id="ignition-view">` block through its closing `</section>` with:

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

- [ ] **Step 3: Verify intro-particles markup is removed**

Run: `grep -n 'intro-particle-canvas\|intro-particles' public/index.html`
Expected: no matches.

- [ ] **Step 4: Commit**

```bash
git add public/index.html
git commit -m "html: ignition-view markup — paper composer + witness anchor

Replaces the old hero-threshold-field markup with the paper
composer (.composer-card + .composer-card__field). Adds the
witness anchor inert SVG diamond above the title. Title carries
the violet .ig-title__emphasis span on 'actually explain'.
Source-attach is a journal-meta line inside the card; the source
panel is reused as-is via #hero-source-panel. Cap gate renders
above the form (composer locks but stays visible at 9-concept
board cap). #ignition-view now carries the [hidden] attribute.

The <canvas id=intro-particle-canvas> is removed; intro-particles.js
no-ops cleanly without it.

Paper Wave 1.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Update `#launch-pad-view` markup in `public/index.html`

**Files:**
- Modify: `public/index.html` (existing `<section id="launch-pad-view">` block, currently around lines 326–353)

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
          <span>Save sketch</span>
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

Replaces the old launch-pad-form markup with the paper composer in
--tall variant (5 ruled lines). Adds witness anchor and the
.ig-concept-mark plain-typeset 'on Photosynthesis' line above the
title. Footnote sits below the form. Textarea aria-label matches
the heading text so screen readers announce identical context.

Paper Wave 1.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Update `public/js/app.js`

**Files:**
- Modify: `public/js/app.js`

- [ ] **Step 1: Locate functions**

Run: `grep -n 'function showIgnition\|function hideIgnition\|function renderIgnitionGate\|function hidePrimaryViews\|is-building-route\|aria-busy' public/js/app.js`

- [ ] **Step 2: Replace `showIgnition`**

Replace its body with:

```js
function showIgnition() {
  setNavActive('nav-ignition');
  clearSettingsPanel();
  teardownMapView();
  hidePrimaryViews();
  document.getElementById('ignition-view').hidden = false;
  renderIgnitionGate();
  if (window.innerWidth < 900) closeDrawer();
  // Focus the writing surface directly; aria-label provides SR announcement.
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

- [ ] **Step 4: Update `hidePrimaryViews`**

Find the line `if (ignitionView) ignitionView.classList.remove('visible');` and replace with `if (ignitionView) ignitionView.hidden = true;`. Other view handlers in this function keep their existing convention.

- [ ] **Step 5: Replace `renderIgnitionGate`**

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

Search for sites that toggle `aria-busy` and `is-building-route` on the ignition flow. Replace patterns like:

```js
view.setAttribute('aria-busy', 'true');
view.classList.add('is-building-route');
```

with:

```js
form.setAttribute('aria-busy', 'true');
form.dataset.state = 'busy';
```

…where `form = document.getElementById('hero-single-input')`. Replace teardown pairs similarly.

- [ ] **Step 7: Manual flow verification**

Run: `bash scripts/dev.sh`. Open `http://localhost:8000/` → click "New concept" in the sidebar. Confirm: paper composer renders, no console errors, type 2 chars enables submit, submit navigates to launch-pad.

- [ ] **Step 8: Commit**

```bash
git add public/js/app.js
git commit -m "js(app): drive ignition visibility via [hidden] + data-state

- showIgnition / hideIgnition / hidePrimaryViews use the [hidden]
  attribute on #ignition-view (replacing classList.add('visible')).
- showIgnition focuses the field directly; the textarea's aria-label
  provides the SR announcement without a heading-bounce.
- renderIgnitionGate sets data-state='locked' on the composer at cap
  (instead of hiding it) so the user keeps the spatial cue. Routes
  focus to the cap-gate CTA when the field was active at the moment
  cap engaged.
- Door busy state is form.dataset.state='busy' + aria-busy on the
  form element; replaces the prior is-building-route class.

Paper Wave 1.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: Update `public/js/launch-pad.js`

**Files:**
- Modify: `public/js/launch-pad.js`

- [ ] **Step 1: Locate the relevant blocks**

Run: `grep -n 'export function showLaunchPad\|ag-lp-arriving\|is-building-route\|_lpArrivingCleanup\|export async function runLaunchPadAction' public/js/launch-pad.js`

- [ ] **Step 2: Replace the showLaunchPad reveal block**

Find the block that uses `view.removeAttribute('hidden')` followed by `ag-lp-arriving` class manipulation + `_lpArrivingCleanup`. Replace with:

```js
const view = document.getElementById('launch-pad-view');
if (!view) return;
view.hidden = false;
view.removeAttribute('aria-busy');
const form = document.getElementById('launch-pad-form');
if (form) form.dataset.state = '';
```

Delete the module-scope `let _lpArrivingCleanup = null;` declaration.

- [ ] **Step 3: Replace runLaunchPadAction busy-state lines**

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

- [ ] **Step 4: Verify zero remaining references**

Run: `grep -n 'ag-lp-arriving\|is-building-route\|_lpArrivingCleanup' public/js/launch-pad.js`
Expected: no matches.

- [ ] **Step 5: Manual flow verification**

`bash scripts/dev.sh`. Click "New concept" → type "Photosynthesis" → Continue. Launch pad appears with witness anchor, "on Photosynthesis" mark, tall composer. Type "leaves convert sunlight to sugar" → submit. Composer dims (busy state), then graph view appears.

- [ ] **Step 6: Commit**

```bash
git add public/js/launch-pad.js
git commit -m "js(launch-pad): drive visibility via [hidden] + form.data-state

- showLaunchPad uses view.hidden = false (replacing
  removeAttribute('hidden')) and drops the ag-lp-arriving class +
  _lpArrivingCleanup timer entirely; the new
  .launch-pad-view__inner ig-screen-in keyframe in layout.css
  handles the entrance.
- runLaunchPadAction busy state is now form.dataset.state='busy' on
  #launch-pad-form, mirroring the door's pattern.
- Removed is-building-route from all callsites in this file.

Paper Wave 1.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 10: Delete migrated rules from `public/antigravity.css`

**Files:**
- Modify: `public/antigravity.css`

Use the audit results from Task 2 to drive this step.

- [ ] **Step 1: Identify rule blocks to delete**

```bash
grep -n 'body\.antigravity-theme #ignition-view\|body\.antigravity-theme #launch-pad-view\|body\.antigravity-theme \.ignition-title\|body\.antigravity-theme \.ignition-cap-gate\|body\.antigravity-theme \.ignition-view__inner\|body\.antigravity-theme \.intro-particles\|body\.antigravity-theme \.launch-pad-' public/antigravity.css

grep -n 'body\.antigravity-theme \.hero-single-input\|body\.antigravity-theme \.hero-source-attach\|body\.antigravity-theme \.hero-door-error' public/antigravity.css

grep -n '@keyframes ag-lp-arriving' public/antigravity.css
```

- [ ] **Step 2: Delete each identified rule block**

For each grep hit confirmed by the Task 2 audit as ignition/launch-pad-only, delete the entire CSS rule (selector through closing `}`). For comma-separated selectors, either delete the whole rule or strip just the in-scope selector(s).

Also delete:
- `@keyframes ag-lp-arriving`
- All `body.antigravity-theme #ignition-view::before / ::after / #launch-pad-view::before / ::after` blocks
- `.intro-particles` rules

Do NOT delete (defer to Wave 2):
- `body.antigravity-theme .hero-eyebrow*`
- `body.antigravity-theme .hero-state-chip*`
- Selectors for `#grid-container`, `.hero-card`, `.hero-primary-action`, `.library-*`, `.settings-*`, `.sidebar-nav-item`, `.bottom-nav-item`, `#timer-display`, generic `h1, h2, h3` rules.

- [ ] **Step 3: Verify zero remaining references**

```bash
grep -nE 'antigravity-theme [^{}]*(ignition|launch-pad|intro-particles|ag-lp-arriving|is-building-route)' public/antigravity.css
```

Expected: zero matches.

- [ ] **Step 4: Manual verification — light + dark, every primary view**

`bash scripts/dev.sh`. Visit each view:

- **Dashboard:** unchanged from before this PR.
- **Ignition view:** new paper system. Cream paper background (graphite in dark), witness anchor, ruled-paper composer, violet "actually explain" emphasis. NO leftover gradient washes, NO particle canvas, NO glass card.
- **Launch pad view:** paper system, tall composer, "on Photosynthesis" plain-typeset eyebrow.
- **Library / Settings views:** unchanged.

Console clean across all views. If ignition shows residual glass / glow / radial-gradient, an antigravity rule was missed — return to Step 1.

- [ ] **Step 5: Commit (with audit summary in message)**

```bash
git add public/antigravity.css
git commit -m "css(antigravity): delete migrated ignition + launch-pad rules

Strangler Fig amputation step — these rules are replaced by paper.css
in @layer paper. Deleted:

- All body.antigravity-theme #ignition-view* (incl. ::before, ::after)
- All body.antigravity-theme #launch-pad-view* (incl. ::before, ::after)
- @keyframes ag-lp-arriving
- All body.antigravity-theme .ignition-title*, .ignition-cap-gate*,
  .ignition-view__inner*, .intro-particles*, .launch-pad-* blocks
- body.antigravity-theme .hero-single-input* (audited: ignition-only)
- body.antigravity-theme .hero-source-attach* (same audit verdict)
- body.antigravity-theme .hero-door-error* (same audit verdict)

Deferred to Wave 2 (audit found these reach the dashboard hero card):
- .hero-eyebrow*
- .hero-state-chip*

The body.antigravity-theme class itself remains; the final paper
wave removes it.

Paper Wave 1.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 11: Browser smoke + a11y + cross-browser verification

**Files:** none modified — verification only.

- [ ] **Step 1: Local browser smoke**

`bash scripts/qa-smoke.sh local` — pass clean.

- [ ] **Step 2: Manual flow — light mode (Chrome)**

`bash scripts/dev.sh`. Then:

- Click "New concept" — Ignition view appears with paper composer, witness anchor, "Ignition · 1 of 2" eyebrow, title with violet "actually explain", helper, ruled-paper textarea, source-meta line `source: none yet — add`, disabled submit (mauve `--locked` fill).
- Type 2 chars — submit enables (violet `--primary-fill`).
- Hover submit — translateY(-1px) lift + violet shadow.
- Tab to submit — `--accent-ring` visible, no transform jitter.
- Click `add` — source panel expands inline, focus moves to URL input.
- URL flow → submit with no source → launch-pad appears: "on Photosynthesis", tall composer.
- Type 3+ words → "Save sketch" enables.
- Submit → composer dims (`data-state="busy"`) → graph view appears on success.

- [ ] **Step 3: Manual flow — dark mode**

Toggle dark theme. Repeat Step 2. Confirm:
- Page background is graphite-900 (#18181b).
- Composer card is graphite-800 (#27272a) with faint ruled lines.
- Console clean.

- [ ] **Step 4: Reduced motion check**

System Settings → Display → Reduce Motion ON (or DevTools → Rendering → Emulate `prefers-reduced-motion: reduce`).

- No `ig-screen-in` fade-up on view mount.
- Submit hover does not lift.
- Composer dim on busy state still applies (transition is suppressed; the dim is via opacity, which persists).

- [ ] **Step 5: Cap-state verification**

DevTools console:

```js
const fake = Array.from({length: 9}, (_, i) => ({
  id: `test-${i}`, name: `Concept ${i}`, createdAt: new Date().toISOString(),
  state: 'growing', contentPreview: '', graphData: null,
}));
localStorage.setItem('socratink:concepts', JSON.stringify(fake));
location.reload();
```

Click "New concept". Cap gate visible above composer. Composer dimmed (`data-state="locked"`). Field + submit disabled. Restore: `localStorage.removeItem('socratink:concepts'); location.reload();`

- [ ] **Step 6: Lighthouse a11y audit**

DevTools → Lighthouse → Accessibility on Ignition view + Launch Pad view, light + dark. Score ≥95 each.

- [ ] **Step 7: axe DevTools audit**

Run on Ignition view + Launch Pad view, both modes. Zero serious / critical violations.

- [ ] **Step 8: Cross-browser**

Chrome (verified above), Safari, Firefox desktop, iOS Safari at 360px.

- [ ] **Step 9: Telemetry verification**

Watch `JSON.parse(localStorage.getItem('socratink:telemetry') || '[]').slice(-10)`. Confirm event names fire as expected: `concept_create.door.submit`, `concept_create.launch_pad.entered`, `concept_create.launch_pad.submit`, `concept_create.bypass_rejected`, `concept_create.cap_exceeded`.

- [ ] **Step 10: Audio FX smoke**

Volume on. Focus textarea — focus tap. Type — key click. Click submit (when enabled) — focus tap.

- [ ] **Step 11: No commit.** Verification only.

---

## Task 12: Push to dev + verify Vercel preview

**Files:** none modified.

- [ ] **Step 1: Final preflight**

```bash
bash scripts/qa-smoke.sh local
git log -20 --oneline    # all commits present
grep -rn '<<<<<<\|>>>>>>\|=======' public/css/ public/js/ public/index.html public/antigravity.css 2>/dev/null
```

- [ ] **Step 2: Push**

`git push origin dev`

- [ ] **Step 3: Vercel preview**

Wait for preview deployment. Open URL. Repeat Manual Flow steps 2–3 against live preview.

- [ ] **Step 4: Smoke against preview**

`bash scripts/qa-smoke.sh https://<vercel-preview-url>`

- [ ] **Step 5: No commit.** Wave 1 complete on `dev`. Production promotion via dev → main PR is a separate decision.

---

## Self-review checklist

- **Spec coverage:**
  - paper.css component creation → Task 3
  - index.css paper import + version bump → Task 4
  - Layout view shells → Task 5
  - HTML markup updates → Tasks 6, 7
  - JS visibility / focus / cap-gate / busy-state → Tasks 8, 9
  - Antigravity deletion (Strangler Fig) → Tasks 2 (audit), 10 (delete)
  - Browser smoke + a11y + cross-browser + telemetry + audio → Task 11
  - Push + Vercel preview → Task 12
- **No placeholders:** every step has runnable commands or full code.
- **Type consistency:** every CSS rule references existing tokens (`--surface-card`, `--text-strong`, `--text-muted`, `--accent-primary`, `--primary-fill`, `--primary-fill-hover`, `--border-subtle`, `--border-strong`, `--shadow-card`, `--accent-shadow-md`, `--accent-ring`, `--accent-soft`, `--accent-border`, `--accent-border-strong`, `--font-display`, `--font-body`, `--text-xs/sm/base/3xl`, `--leading-tight/normal`, `--tracking-tight/kicker`, `--space-1/2/3/4/5/6`, `--radius-btn`, `--ease-standard`, `--duration-micro/quick/cozy`, `--locked`, `--text-on-primary`, `--danger`) plus the two Wave 0 additions (`--rule-line`, `--rule-step`). No invented token names.
- **Frequent commits:** 8 commits during implementation (Tasks 3–10).
