# Wave 1 — Ignition + Launch Pad paper redesign

**Status:** ready for plan
**Owner:** Jon
**Created:** 2026-05-09
**Type:** redesign — visible change
**Umbrella:** `2026-05-09-paper-migration-plan.md`
**Prerequisite:** Wave 0 merged (`2026-05-09-paper-tokens-cascade-layers-refactor-design.md`)

## Goal

Redesign the `#ignition-view` (Screen 1: name the concept) and `#launch-pad-view` (Screen 2: starting sketch) to mirror the visual identity of socratink.ai's marketing page — cream paper with hairline borders, ruled-paper composer, violet-deep accent, Geom typography, witness anchor placeholder, no atmospherics. Persona-tested. Behavioral pipeline (cap gate, source-attach, sessionStorage shell, telemetry, audio, /api/extract) preserved unchanged.

## What's locked (decision summary)

| Decision | Choice |
|---|---|
| Composer card fidelity | Ruled paper, no redline |
| Dark mode | Night paper (graphite, faint rules, lighter violet) |
| Source-attach trigger | Meta line inside card: `source: none yet — add` |
| Screen 2 eyebrow | Plain typeset: `on Photosynthesis` |
| Title verb | "actually explain" — italic, violet-deep, translucent underline |
| Witness anchor | Inert SVG diamond above title, both screens |
| Particle field | Removed from markup (`<canvas id="intro-particle-canvas">` deleted) |
| Gradient washes, glass cards, atmospherics | All removed |
| Calm-on-typing, ink-stroke animation | Removed (nothing to calm) |

## What stays unchanged

- Backend (`/api/extract`, `/api/extract-url`, ProvisionalMap shape).
- `source-panel.js` JS — used as-is. Its rendered classes (`.creation-source-panel`, `.overlay-tabs`, `.overlay-tab`, `.overlay-textarea`, `.overlay-url-input`, `.overlay-dropzone`, `.creation-source-panel-footer`, `.creation-source-panel-cancel`, `.creation-source-panel-attach`) get paper styling; no JS changes.
- `audio.js` — focus tap, key click, click cue continue to fire on the new markup.
- `telemetry.js` — all 7 events (`concept_create.door.submit`, `launch_pad.entered`, `launch_pad.submit`, `bypass_rejected`, `cap_exceeded`, `evaporated`, persistence) emitted at the same call sites with the same shape.
- sessionStorage `socratink:pendingShell` write/read/expire/bounce flow.
- 9-concept board cap (`BOARD_SLOT_COUNT`).
- 422 thin-sketch and 500 cap-exceeded server error handling.

## Files changed

### New file `public/css/paper.css`

Wave 0 reserved a `paper` layer at the top of the cascade. Wave 1 introduces this file and registers it in `index.css` as `@import url('paper.css') layer(paper);`. **All new rules go in this file**, not in `components.css` — the layer assignment is what makes them beat the `legacy` layer (antigravity), and only file-level `@import layer(paper)` puts them there. Adding `@layer paper { … }` *inside* `components.css` would create a `components.paper` sublayer that still loses to `legacy` (sublayers inherit parent-layer ordering).

File header:

```css
/* ════════════════════════════════════════════════════════════════════
   PAPER SYSTEM — composer-card, witness-anchor, ig-title, journal-meta,
   source-panel restyle, ig-button. References only semantic tokens.
   No body.antigravity-theme ancestor. Imported via index.css into
   @layer paper, which beats @layer legacy on migrated surfaces.
   See docs/superpowers/specs/2026-05-09-paper-migration-plan.md
   ════════════════════════════════════════════════════════════════════ */
```

### Updated `public/css/index.css`

Add the paper import after the legacy import:

```css
@import url('../antigravity.css') layer(legacy);
@import url('paper.css')          layer(paper);   /* NEW in Wave 1 */
```

### Components in `paper.css` (all reference semantic tokens; no body.antigravity-theme ancestor)

- `.composer-card` — paper background, hairline border, soft shadow, 8px radius
- `.composer-card__field` — `<textarea>` with rule-grid background-attachment:local
- `.composer-card__actions` — flex row, justify-content flex-end
- `.composer-card[data-state="locked" | "busy"]` — opacity dip + pointer-events:none
- `.composer-card--tall` — modifier; min-height = 5 rule lines (Launch Pad)
- `.witness-anchor`, `.witness-anchor__shape` — inert diamond SVG
- `.ig-title`, `.ig-title__emphasis` — display heading + violet-deep italic emphasis
- `.ig-eyebrow`, `.ig-eyebrow__dot` — Screen 1 step indicator (`Ignition · 1 of 2`)
- `.ig-concept-mark`, `.ig-concept-mark__key`, `.ig-concept-mark__name` — Screen 2 plain-typeset eyebrow
- `.ig-helper`, `.ig-footnote`
- `.ig-error` — live region styling
- `.ig-button`, `.ig-button--ghost` — primary action
- `.journal-meta`, `.journal-meta__key`, `.journal-meta__value`, `.journal-meta__sep`, `.journal-meta__add` — source meta row inside composer
- `.creation-source-panel` and the `.overlay-*` children — restyled to paper
- `.ignition-cap-gate`, `.ignition-cap-gate__message`

Token reference: see Wave 0 (`tokens.css`).

### Updated view shells in `public/css/layout.css`

Replace the existing `#ignition-view` and `#launch-pad-view` blocks (currently lines 2412–2505) with:

```css
/* The :not([hidden]) scope ensures the [hidden] attribute (UA `display:none`)
   beats this rule when the view is hidden. Without :not(), the ID-selector
   specificity (1,0,0) would override [hidden] (0,1,0) and the views would
   never actually hide. */
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

Remove the `display: none` / `.visible` toggle from the base CSS — visibility is driven entirely by the `[hidden]` attribute now.

### Markup changes in `public/index.html`

#### `#ignition-view` section (replaces current lines 278–323)

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

#### `#launch-pad-view` section (replaces current lines 326–353)

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

#### Removals from `public/index.html`

- Delete `<div class="intro-particles">` and the `<canvas id="intro-particle-canvas">` element from the ignition-view block. (`intro-particles.js` will no-op since it queries the canvas element and exits if not found.)

### Updated `public/js/app.js`

#### `showIgnition` / `hideIgnition`

```js
function showIgnition() {
  setNavActive('nav-ignition');
  clearSettingsPanel();
  teardownMapView();
  hidePrimaryViews();
  document.getElementById('ignition-view').hidden = false;
  renderIgnitionGate();
  if (window.innerWidth < 900) closeDrawer();
  // Focus the writing surface directly. Its aria-label carries the same text
  // as the heading, so screen readers announce "What do you want to actually
  // explain?" on focus. A separate heading-focus + rAF bounce would interrupt
  // the SR announcement; that pattern is rejected on purpose.
  const field = document.getElementById('hero-single-input-field');
  if (field) requestAnimationFrame(() => field.focus());
}

function hideIgnition() {
  document.getElementById('ignition-view').hidden = true;
}
```

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
  if (submit) submit.disabled = atCap || !isReady();

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

`isReady()` is a small helper extracted from existing submit-gate logic; if no extraction is desired, inline the trim-length check.

#### `hidePrimaryViews` updated to drive ignition via `[hidden]`

The existing function uses `view.classList.remove('visible')` for ignition. Replace with `view.hidden = true`. Other views that this function manages keep their existing convention.

#### Busy state on submit

Where `runSourceAttachedSubmit` and persistence currently set `aria-busy` and `is-building-route`, simplify to a single `data-state="busy"` toggle on the composer:

```js
form.dataset.state = 'busy';
form.setAttribute('aria-busy', 'true');
// … on completion or error …
form.dataset.state = '';
form.removeAttribute('aria-busy');
```

The busy CSS handles the visual via the locked/busy attribute selector in `components.css`.

### Updated `public/js/launch-pad.js`

#### `showLaunchPad` — focus the field directly

```js
const view = document.getElementById('launch-pad-view');
view.hidden = false;
view.removeAttribute('aria-busy');
view.dataset.state = '';
// Same rationale as showIgnition: focus the field directly. The textarea's
// aria-label provides the announcement; a heading-bounce would interrupt SR.
const field = document.getElementById('launch-pad-input');
if (field) requestAnimationFrame(() => field.focus());
```

Drop the `ag-lp-arriving` class manipulation and the `_lpArrivingCleanup` timer — animation now lives on `.launch-pad-view__inner` via the `ig-screen-in` keyframe (Section 3 layout).

#### `runLaunchPadAction` — `data-state="busy"`

Replace `view.classList.add('is-building-route')` with `view.dataset.state = 'busy'`. Replace `clearBuildingState` to set `view.dataset.state = ''`.

## Acceptance criteria

1. **Browser smoke (`bash scripts/qa-smoke.sh local`) passes clean.**
2. **Visual check, light + dark, on Chrome desktop:**
   - Empty Screen 1: witness anchor visible, eyebrow `Ignition · 1 of 2`, title with violet-deep "actually explain", helper, composer card with ruled-paper textarea, source meta line, disabled submit. No gradients, no glass, no glows.
   - Type 2 chars: submit enables (violet fill, hover lift on hover, no transform on focus).
   - Click `add`: source panel expands inline below the meta line; URL/Upload tabs in paper style.
   - Submit no-source: shell written; navigates to Screen 2; `on Photosynthesis` concept-mark; tall textarea on rules; "Build my map" button.
   - Type sketch (≥3 substantive words): submit enables.
   - Server 422: `.ig-error` shows `THIN_THRESHOLD_COPY`, shell preserved, submit re-enabled.
   - Force 9 concepts: cap gate above composer, composer at `data-state="locked"`, dimmed and inert, focus on "Open library".
3. **Cross-browser:** repeat #2 on Safari + Firefox desktop, plus iOS Safari at 360px width.
4. **Reduced motion:** macOS Reduce Motion ON — no button hover lift, no source-panel expand transition, no screen-in animation.
5. **VoiceOver:** view mount announces "What do you want to actually explain?". Tab routes through textarea → source-add → (when expanded) source-panel inputs → submit. Error live region announces 422 message.
6. **Lighthouse a11y:** ≥95 on both screens, both themes.
7. **axe DevTools:** zero serious / critical violations on either view.
8. **Telemetry verification:** all 7 events fire with the same shape as before (use existing telemetry inspector or check ingestion logs).
9. **Audio FX retention:** focus on the field plays focus tap; printable keystrokes play key click; submit click plays focus tap.
10. **Console clean:** no errors in any view, light or dark, on any flow.

## Failure modes

- **Cascade-layer regression:** if Wave 0's `@layer` orchestration is somehow broken in this PR, antigravity's old ignition rules could resurface. Mitigation: this PR also DELETES the old ignition + launch-pad rules from `antigravity.css` (see "Deletions" below). Once deleted, there's nothing to resurface.
- **`source-panel.js` class-name drift:** if a future `source-panel.js` change renames its rendered classes, our paper restyling silently breaks. Mitigation: a comment in `components.css` notes the dependency, and the spec lists the exact class names this PR depends on.
- **Audio FX silent regression:** if a markup change accidentally moves the textarea outside the click region `audio.js` queries, sound stops without error. Mitigation: explicit verification step (#9) in acceptance criteria.

## Deletions (Strangler Fig — same PR)

### Pre-deletion audit (required step)

Before deleting any rule from `public/antigravity.css`, grep `public/index.html` and `public/js/` for each candidate selector to confirm it's *only* used by ignition + launch-pad markup. Selectors used by any out-of-scope view (dashboard, library, settings, nav) are NOT deleted in this PR — those are Wave 2+ concerns.

Specifically, for each rule below:

```bash
# For each selector candidate <SEL>:
grep -nF "<SEL>" public/index.html public/js/*.js
# If the only matches sit inside #ignition-view or #launch-pad-view → safe to delete.
# If matches appear elsewhere → leave the antigravity rule, note in Wave 2 spec.
```

### Definitely-delete (these only style ignition + launch-pad surfaces)

- All `body.antigravity-theme #ignition-view*` selectors (and their `::before` / `::after` blooms).
- All `body.antigravity-theme #launch-pad-view*` selectors and the `ag-lp-arriving`, `is-building-route` keyframes.
- All `body.antigravity-theme .ignition-title*`, `.ignition-cap-gate*`, `.ignition-view__inner*` selectors.
- All `body.antigravity-theme .launch-pad-*` selectors (entire family — Launch Pad is uniquely scoped to this view).
- All `body.antigravity-theme .intro-particles*` selectors (the canvas is removed from markup).

### Audit-before-deleting (these MAY be referenced by dashboard or hero card — verify first)

- `body.antigravity-theme .hero-single-input*` — almost certainly ignition-only, but `.hero-single-input` originated as the dashboard's threshold composer; confirm via grep before deleting.
- `body.antigravity-theme .hero-source-attach*` — same lineage.
- `body.antigravity-theme .hero-eyebrow*`, `.hero-state-chip*`, `.hero-door-error*` — `.hero-*` is a shared family on the dashboard. Likely needs to stay until Wave 2; confirm via grep.

For each "audit-before-deleting" item, the implementation plan must record the audit result (deleted vs deferred to Wave N) in the PR description.

The `body.antigravity-theme` class itself stays on `<body>` — other waves still use it.

## Out-of-scope (Wave 2+)

Same as in `paper-migration-plan.md`. Reiterating to be explicit:

- Dashboard / hero card / `.intro-page`
- Library view
- Settings view
- Sidebar + bottom-nav active states
- `intro-particles.js` retirement (kept as no-op when its canvas is gone)
- Renaming antigravity.css (we delete it eventually)
- `audio.js` / `bus.js` / `telemetry.js` / `auth.js` / Python backend — no changes

## Verification command summary

```bash
bash scripts/qa-smoke.sh local             # smoke pass
bash scripts/dev.sh                         # local dev server for manual checks
# Browser DevTools: Lighthouse + axe extension passes
# VoiceOver pass on both screens
# Telemetry inspection: localStorage 'socratink:telemetry' or backend log
```
