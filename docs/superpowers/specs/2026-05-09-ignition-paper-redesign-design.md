# Paper Wave 1 — Ignition + Launch Pad redesign

**Status:** ready for plan
**Owner:** Jon
**Created:** 2026-05-09
**Last revised:** 2026-05-09 — corrected after a fresh-subagent verification pass; original draft invented parallel token names that conflicted with the existing `public/css/variables.css`. This revision references only existing tokens (plus the two new ones added in Wave 0).
**Type:** redesign — visible change, scope-locked to ignition + launch-pad
**Umbrella:** `2026-05-09-paper-migration-plan.md`
**Prerequisite:** Wave 0 merged (`2026-05-09-paper-tokens-cascade-layers-refactor-design.md`).

## Goal

Redesign the `#ignition-view` (Screen 1: name the concept) and `#launch-pad-view` (Screen 2: starting sketch) so they read like a paper journal page — cream paper with hairline borders, ruled-paper textarea, witness-anchor diamond, violet accent, "actually explain" emphasis. The behavioral pipeline (cap gate, source-attach, sessionStorage shell, telemetry, audio, /api/extract) is preserved unchanged.

The redesign is mostly **deletion of antigravity overrides** plus a small amount of additive CSS in a new `paper.css` file. The base ignition styling already references the canonical token system (`--surface-card`, `--text-strong`, `--accent-primary`, etc.); once antigravity's overlay is removed, what remains IS the paper system.

## Decisions locked in brainstorm

| Decision | Choice |
|---|---|
| Composer card fidelity | Ruled paper, no redline |
| Dark mode | Existing graphite `[data-theme="dark"]` (no new tokens needed) |
| Source-attach trigger | Meta line inside card: `source: none yet — add` |
| Screen 2 eyebrow | Plain typeset: `on Photosynthesis` |
| Title verb | "actually **explain**" — italic violet emphasis with translucent underline |
| Witness anchor | Inert SVG diamond above title, both screens |
| Particle field | Removed from markup (`<canvas id="intro-particle-canvas">` deleted) |
| Gradient washes, glass cards, atmospherics | All removed via deletion of antigravity ignition rules |
| Calm-on-typing, ink-stroke animation | Removed (nothing to calm; static is the default) |

## Token references

Every CSS rule in this wave references the existing tokens defined in `public/css/variables.css`, plus the two paper-specific additions from Wave 0 (`--rule-line`, `--rule-step`). **No new tokens are introduced.**

Quick reference for the components below:

- Surfaces: `--surface-page` (cream/graphite), `--surface-card` (paper-0/graphite-800), `--rule-line` (faint horizontal rule color)
- Text: `--text-strong`, `--text-muted` (covers both "soft" and "faint" usage)
- Accent: `--accent-primary` (violet 600 — emphasis, links, eyebrow), `--primary-fill` (#7a59aa — button fill), `--primary-fill-hover` (#70529b — button hover), `--accent-soft-strong` (rgba violet 0.18 — translucent emphasis underline)
- Borders + shadow: `--border-subtle` (rgba ink 0.10 — hairlines), `--border-strong` (rgba ink 0.16 — card borders), `--shadow-card` (violet-tinted)
- Type: `--font-display` (Geom), `--font-body` (Inter), `--text-3xl` (title), `--text-base` (helper), `--text-sm` (eyebrow), `--text-xs` (footnote, meta)
- Spacing (rem): `--space-1`…`--space-12`. `--rule-step` for the ruled-paper line height (32px).
- Radius: `--radius-btn` (10px) for buttons, fields, card corners; `--radius-card` (16px) reserved for hero shells (not used in the composer here)
- Motion: `--duration-micro` (140ms), `--duration-quick` (220ms), `--duration-cozy` (320ms), `--ease-standard`, `--ease-spring`
- Focus: `--accent-ring` (= `0 0 0 3px rgba(violet, 0.14)`)
- Disabled: `var(--locked)` (= `--mauve-200`) — canonical disabled-control color in this design system

## What stays unchanged

- Backend (`/api/extract`, `/api/extract-url`, ProvisionalMap shape).
- `source-panel.js` — its rendered class names (`.creation-source-panel`, `.creation-source-panel-footer`, `.creation-source-panel-cancel`, `.creation-source-panel-attach`, `.overlay-tabs`, `.overlay-tab`, `.overlay-textarea`, `.overlay-url-input`, `.overlay-dropzone`, `.overlay-dropfeedback`) get paper styling; no JS changes.
- `audio.js` — focus tap, key click, click cue continue to fire on the new markup.
- `telemetry.js` — all 7 events fire at the same call sites with the same shape.
- sessionStorage `socratink:pendingShell` write/read/expire/bounce flow.
- 9-concept board cap (`BOARD_SLOT_COUNT`).
- 422 thin-sketch and 500 cap-exceeded server error handling.
- The existing `[hidden] { display: none !important; }` rule in `public/css/base.css` line 27 — visibility is driven by toggling the `[hidden]` attribute; no `:not([hidden])` workarounds.

## Files changed

### New file `public/css/paper.css`

Wave 0 reserved a `paper` layer at the top of the cascade. Wave 1 introduces this file and registers it in `index.css` as `@import url('paper.css?v=1') layer(paper);`. **All new component CSS goes here**, file-level, so it lands in the `paper` layer (which beats `legacy`).

File header:

```css
/* ════════════════════════════════════════════════════════════════════
   paper.css — PAPER SYSTEM components.
   Imported via index.css into @layer paper, which beats @layer legacy
   (antigravity.css) on migrated surfaces. References only tokens
   defined in variables.css plus --rule-line and --rule-step (added in
   Paper Wave 0).
   See docs/superpowers/specs/2026-05-09-ignition-paper-redesign-design.md
   ════════════════════════════════════════════════════════════════════ */
```

Full content of `paper.css`:

```css
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

/* Locked + busy states (cap-gate / submit-in-flight) */

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
  text-decoration-color: var(--accent-border-strong);  /* rgba(violet, 0.30) */
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
  min-height: 1em;          /* reserve space so live updates don't shift layout */
}
.ig-error:empty { margin-top: 0; }

/* ── Source-meta line (inside composer-card on Screen 1) ──── */

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
  text-decoration-color: var(--accent-border);  /* rgba(violet, 0.18) */
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

/* Ghost variant — cap-gate "Open library" CTA */

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

### Updated `public/css/index.css`

Uncomment the paper-layer `@import` and bump the version pin:

```css
@layer components, legacy, paper;

@import url('../styles.css?v=85')      layer(components);
@import url('../antigravity.css?v=13') layer(legacy);
@import url('paper.css?v=1')           layer(paper);   /* NEW in Wave 1 */
```

Also bump `index.css`'s own version in `public/index.html` from `?v=1` to `?v=2`.

### Updated `public/css/layout.css` view shells

Locate the existing `#ignition-view` and `#launch-pad-view` blocks (currently lines 2412–2505) and replace them with:

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

### Markup changes in `public/index.html`

#### `#ignition-view` section (replaces existing block ~lines 278–323)

```html
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

#### `#launch-pad-view` section (replaces existing block ~lines 326–353)

```html
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

#### Removals from `public/index.html`

- Delete `<div class="intro-particles">` and the `<canvas id="intro-particle-canvas">` element from the ignition-view block. (`intro-particles.js` will no-op since it queries the canvas and exits if not found.)

### Updated `public/js/app.js`

#### `showIgnition`

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
  // the heading text so screen readers announce on focus.
  const field = document.getElementById('hero-single-input-field');
  if (field) requestAnimationFrame(() => field.focus());
}
```

#### `hideIgnition`

```js
function hideIgnition() {
  document.getElementById('ignition-view').hidden = true;
}
```

#### `hidePrimaryViews` — drive ignition via `[hidden]`

Where the existing function does `ignitionView.classList.remove('visible')`, replace with `ignitionView.hidden = true`. Other view handlers in this function keep their existing convention.

#### `renderIgnitionGate`

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

#### Busy-state pattern

Where existing code sets `aria-busy` and `is-building-route`, replace the class-based pattern with a `data-state="busy"` attribute on the form:

```js
const form = document.getElementById('hero-single-input');
if (form) {
  form.setAttribute('aria-busy', 'true');
  form.dataset.state = 'busy';
}
// On completion / error:
if (form) {
  form.removeAttribute('aria-busy');
  form.dataset.state = '';
}
```

### Updated `public/js/launch-pad.js`

#### `showLaunchPad` — drive visibility via `[hidden]`, drop `ag-lp-arriving`

Replace the block that uses `view.removeAttribute('hidden')` + `ag-lp-arriving` class manipulation + `_lpArrivingCleanup` timer with:

```js
const view = document.getElementById('launch-pad-view');
if (!view) return;
view.hidden = false;
view.removeAttribute('aria-busy');
const form = document.getElementById('launch-pad-form');
if (form) form.dataset.state = '';
```

The `ig-screen-in` keyframe on `.launch-pad-view__inner` (added in `layout.css`) handles the entrance animation; the `ag-lp-arriving` class manipulation is no longer needed. Delete the module-scope `let _lpArrivingCleanup = null;` declaration and any cleanup code.

Focus routing on mount stays as-is (field-direct focus via `requestAnimationFrame`).

#### `runLaunchPadAction` — busy state on form, not view

Replace `view.classList.add('is-building-route')` with `form.dataset.state = 'busy'`, where `form = document.getElementById('launch-pad-form')`. Replace teardown likewise.

## Acceptance criteria

1. **Browser smoke (`bash scripts/qa-smoke.sh local`) passes clean.**
2. **Visual check, light + dark mode, on Chrome desktop:**
   - Empty Screen 1: witness anchor visible, "Ignition · 1 of 2" eyebrow, title with violet "actually explain" emphasis, helper, ruled-paper textarea, source-meta line, disabled submit (mauve `--locked` fill).
   - Type 2 chars: submit enables (violet `--primary-fill`).
   - Hover submit: 1px lift + violet shadow.
   - Click `add`: source panel expands inline below the meta line in paper styling.
   - Submit no-source: shell written; navigates to Screen 2 with `on Photosynthesis` concept-mark and tall composer.
   - Server 422: `.ig-error` shows the thin-sketch message; shell preserved; submit re-enabled.
   - Force 9 concepts: cap gate above composer; composer at `data-state="locked"`, dimmed and inert; focus on "Open library".
3. **Cross-browser:** Chrome, Safari, Firefox desktop; iOS Safari at 360px width.
4. **Reduced motion:** macOS Reduce Motion ON — no button hover lift, no source-panel transition, no screen-in animation.
5. **VoiceOver:** view mount announces the heading via the textarea's `aria-label`. Tab order matches spec.
6. **Lighthouse a11y:** ≥95 on both screens, both themes.
7. **axe DevTools:** zero serious / critical violations.
8. **Telemetry verification:** all 7 events fire with the same shape as before.
9. **Audio FX retention:** focus tap on field focus, key click on each printable keystroke, click cue on submit.
10. **Console clean** in any view, light or dark, on any flow.

## Deletions (Strangler Fig — same PR)

### Pre-deletion audit (required)

Before deleting any rule, grep `public/index.html` and `public/js/` for each candidate selector. Delete only if matches confirm the selector is used **only** by ignition + launch-pad markup.

```bash
grep -nF '<SEL>' public/index.html public/js/*.js
```

### Definitely-delete (ignition / launch-pad-only by name)

- All `body.antigravity-theme #ignition-view*` selectors (and their `::before` / `::after` blooms).
- All `body.antigravity-theme #launch-pad-view*` selectors and the `ag-lp-arriving`, `is-building-route` keyframes.
- All `body.antigravity-theme .ignition-title*`, `.ignition-cap-gate*`, `.ignition-view__inner*` selectors.
- All `body.antigravity-theme .launch-pad-*` selectors.
- All `body.antigravity-theme .intro-particles*` selectors (canvas markup is removed).

### Audit-before-deleting (may reach into dashboard hero card)

- `body.antigravity-theme .hero-single-input*` — likely ignition-only; confirm via grep.
- `body.antigravity-theme .hero-source-attach*` — same.
- `body.antigravity-theme .hero-eyebrow*`, `.hero-state-chip*`, `.hero-door-error*` — these likely reach into the dashboard. Defer to Wave 2 unless grep proves ignition-only.

For each "audit-before-deleting" item, the implementation plan must record the audit verdict (deleted vs deferred) in the PR description.

The `body.antigravity-theme` class itself stays on `<body>` — other waves still use it.

## Out-of-scope (Wave 2+)

- Dashboard / hero card / `.intro-page`
- Library view (`.library-card-*`, `.library-vault-grid`)
- Settings view (`.settings-shell`, `.settings-toggle`, etc.)
- Sidebar + bottom-nav active states
- `intro-particles.js` retirement
- Renaming / deleting `antigravity.css` (final wave)
- `audio.js`, `bus.js`, `telemetry.js`, `auth.js`, Python backend
- The unrelated "Wave 2" legacy-alias sweep already documented in `variables.css`

## Verification command summary

```bash
bash scripts/qa-smoke.sh local
bash scripts/dev.sh                # local dev for manual checks
# Browser DevTools: Lighthouse + axe extension
# VoiceOver pass on both screens
```
