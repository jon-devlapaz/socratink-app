# Ignition as a Route Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Promote Concept Ignition from an embedded empty-state inside the Desk hero into its own first-class route, alongside Desk / Library / Settings, and remove the sidebar `+ new tink` add-trigger.

**Architecture:** The threshold composer DOM moves out of `.hero-card` into a new sibling view `#ignition-view` (peer of `#library-view`, `#settings-view`). A new `showIgnition()` function and `nav-ignition` / `bn-ignition` entries are added to the sidebar and bottom nav. `.hero-card` becomes pure Desk (iso board + concept-specific hero info). The sidebar `add-trigger-area` element is deleted. First-run routing prefers Ignition when there are zero concepts; otherwise Desk. The library cap (4 concepts) gates the Ignition nav entry to a disabled `library full` state and surfaces an inline explanation on Ignition itself, rather than at submit-time.

**Tech Stack:** Vanilla JS module (`public/js/app.js`), HTML (`public/index.html`), CSS modules (`public/css/components.css`, `public/css/layout.css`). No backend changes. Existing concept-create flow (`public/js/concept-create.js`) is reused unchanged via `startAddConcept({ name, sketchTurns, stage: "summary" })`.

---

## Pre-flight context

These facts are verified in the current codebase before this plan was written; if any have drifted, stop and reconcile before executing.

- `public/index.html:62-84` — sidebar contains nav-dashboard / nav-library / nav-settings / nav-feedback, then a "Concepts" section with `#concept-list` and `#add-trigger-area`.
- `public/index.html:46-60` — bottom nav contains `bn-dashboard` / `bn-library` / `bn-settings`. Three items.
- `public/index.html:209-279` — the threshold composer (`#hero-single-input` form with `#hero-single-input-field` and `#hero-starting-map-field`) is inside `.hero-card .intro-content .hero-info`.
- `public/index.html:221` — `#hero-state-chip[data-state="empty"]` is the CSS hook that toggles the threshold composer visibility via `:has()` rules in `components.css`.
- `public/js/app.js:619-641` — `renderAddTrigger()` renders the `+ new tink` / `library full` button.
- `public/js/app.js:580-586` — `clearSettingsPanel()` reads `#add-trigger-area` (because the settings panel reuses that area).
- `public/js/app.js:2113-2120` — `hidePrimaryViews()` hides hero-card / library-view / settings-view.
- `public/js/app.js:2152-2162` — `setNavActive(id)` toggles active class across `nav-*` and `bn-*` ids; the `nav-* → bn-*` mapping is `replace('nav-', 'bn-')`.
- `public/js/app.js:2164-2173` — `showDashboard()` calls `setNavActive('nav-dashboard')`, clears settings panel, tears down map view, hides primary views, then shows `.hero-card`.
- `public/js/app.js:347-410` — `runHeroAction()` reads the threshold composer fields, calls `showDashboard() → openDrawer() → startAddConcept({ name, sketchTurns: [startingMap], stage: 'summary' }, originRect)`. Submit is gated by `isSubstantiveSketch()` from `public/js/sketch-validation.js`.
- `public/js/concept-create.js:46-58` — the concept-create UI accepts `seed.stage === "summary"` and lands directly at the summary card. No change needed there.
- `public/js/dom.js:15` — `addTriggerArea` is exported and consumed by `app.js`.
- Library cap: `public/js/app.js:621` — hardcoded `loadConcepts().length >= 4` in `renderAddTrigger()`. Same threshold appears in concept-create's pre-flight at `app.js:1480` (`loadConcepts().length >= 4`).
- `public/css/components.css:2318` — `.hero-info:has(.hero-state-chip[data-state="empty"]) .hero-single-input { margin-top: 34px }` and the matching mobile rule at line 2323. These are the rules the Ignition view will replace with a simpler centered layout.
- Settings panel reuses `#add-trigger-area` as its container (`clearSettingsPanel` at app.js:579) — when we delete `add-trigger-area` we must point the settings panel elsewhere.

## Architectural decisions locked in

1. **Ignition is a peer view, not a modal.** It gets `#ignition-view` as a sibling of `#library-view` / `#settings-view`, with its own `.visible` toggle managed by `showIgnition()` / `hideIgnition()`.
2. **Threshold composer DOM moves wholesale.** The form node migrates from `.hero-info` into `#ignition-view`. CSS rules that reference `.hero-info:has(.hero-state-chip[data-state="empty"]) .hero-single-input` are replaced with rules scoped to `#ignition-view .hero-single-input`. Particles stay on the Desk hero only.
3. **Desk no longer has an empty-state hero variant for new users.** The empty-state branch in `renderHero()` is unused for the threshold case; if a learner with 0 concepts lands on Desk directly, Desk shows a quiet "Begin at Ignition" pointer and the iso board renders empty.
4. **First-run routing:** in `boot()`, after concepts load, route to Ignition if `loadConcepts().length === 0`, else Desk.
5. **Cap gating moves to the nav entry.** When `loadConcepts().length >= 4`, the Ignition sidebar/bottom-nav entries render a disabled "library full" state. Clicking the disabled entry is a no-op; the title attribute names the reason. The inline cap banner inside `concept-create.js` (`'Library is full. Remove a concept first to add another.'`) stays as a defense-in-depth fallback.
6. **`add-trigger-area` and `renderAddTrigger()` are removed.** The settings panel (which reused that container) is rehoused; see Task 7.
7. **Telemetry/event names unchanged.** Existing `concept_create.*` events keep firing from the same hero submit handler; only the DOM container changed.
8. **Feedback nav stays where it is.** `nav-feedback` is not promoted; only Ignition is added.

## Open questions surfaced for Gemini sanity check

These are flagged inline in the plan but worth listing:

- **First-run welcome interaction:** `maybeShowFirstRunWelcome()` runs on boot. Does it assume the Desk hero is the first surface? If yes, does it need to be re-anchored to Ignition?
- **Empty-Desk pointer copy:** what does Desk look like at 0 concepts after this change? Recommend a tiny banner ("Start at Ignition →") rather than a full empty illustration; pick one.
- **In-app entry points to `startAddConcept()`:** are there any *other* call sites besides the hero form, the deleted `+`, and the seed-failure remount? Grep confirms three; verify none missed.
- **Smoke / e2e tests:** `tests/e2e/test_smoke.py` mentions `runHeroAction` (README line 21). Does it click the threshold from the dashboard? It will need to navigate to Ignition first.
- **Map-view "back" navigation:** does any "exit map → return to dashboard" path assume the threshold appears on Desk? It shouldn't — concept-selected Desks already render the iso/hero state.
- **Particles:** the intro-particles canvas lives in `.hero-card`. Should particles also appear on Ignition (where the typing reactions matter most), or is Desk-only acceptable? Recommend Ignition-only or Ignition+Desk; not a blocker either way.

---

## File Structure

**Modified:**
- `public/index.html` — add `#ignition-view` section; add `nav-ignition` and `bn-ignition` entries; remove `#add-trigger-area`; move threshold composer DOM out of `.hero-card`.
- `public/js/app.js` — add `showIgnition()` / `hideIgnition()` / `renderIgnitionGate()`; remove `renderAddTrigger()`; update `setNavActive()`, `hidePrimaryViews()`, `clearSettingsPanel()`, `showDashboard()`, `boot()`-equivalent first-run routing; relocate threshold-composer wiring (`initHeroSingleInput`, `clearHeroThresholdComposer`, particle bindings) to operate on the moved nodes.
- `public/js/dom.js` — remove `addTriggerArea` export; add `ignitionView` export.
- `public/js/intro-particles.js` — confirm typing-reaction binding still finds the threshold fields (they will be in `#ignition-view` now, not `.hero-card`).
- `public/css/components.css` — replace `.hero-info:has(.hero-state-chip[data-state="empty"]) .hero-single-input` rules with `#ignition-view .hero-single-input` equivalents; remove `.add-trigger*` styles; add `.ignition-view` container styles.
- `public/css/layout.css` — add layout for `#ignition-view` (centered, full-card analogous to library/settings).
- `public/styles.css` — bump cache-buster query strings on imported modules that changed.

**Untouched:**
- `public/js/concept-create.js` — already supports `seed.stage === "summary"`. No change.
- `public/js/sketch-validation.js` — substantiveness gate unchanged.
- `models/sketch_validation.py`, `tests/fixtures/sketch_validation_parity.json` — unchanged.

---

## Task breakdown

### Task 1: Add Ignition nav entries (sidebar + bottom-nav)

**Files:**
- Modify: `public/index.html:46-60` (bottom-nav)
- Modify: `public/index.html:69-78` (sidebar nav)

- [ ] **Step 1: Add `bn-ignition` to bottom-nav between Desk and Library**

```html
<a class="bottom-nav-item" href="javascript:void(0)" onclick="App.showIgnition()" id="bn-ignition">
  <span class="material-symbols-outlined">bolt</span>
  <span class="bottom-nav-label">Ignition</span>
</a>
```

Insert immediately after the Desk `<a>` (the one with `id="bn-dashboard"`).

- [ ] **Step 2: Add `nav-ignition` to sidebar between Desk and Library**

```html
<a id="nav-ignition" class="sidebar-nav-item" href="javascript:void(0)"
  onclick="App.showIgnition()"><span class="material-symbols-outlined">bolt</span> Ignition</a>
```

Insert immediately after the Desk `<a>` (the one with `id="nav-dashboard"`).

- [ ] **Step 3: Verify HTML parses**

Run: `python3 -c "from html.parser import HTMLParser; p=HTMLParser(); p.feed(open('public/index.html').read()); print('ok')"`
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add public/index.html
git commit -m "feat(ia): add Ignition nav entries to sidebar and bottom-nav"
```

### Task 2: Add `#ignition-view` shell and move threshold DOM into it

**Files:**
- Modify: `public/index.html:209-279` (extract threshold composer)
- Modify: `public/index.html` (insert `#ignition-view` near other primary views)

- [ ] **Step 1: Locate where `#library-view` and `#settings-view` siblings live**

Run: `grep -n 'id="library-view"\|id="settings-view"' public/index.html`
Expected: line numbers for both.

- [ ] **Step 2: Insert `#ignition-view` as a sibling, immediately before `#library-view`**

```html
<section id="ignition-view" class="primary-view ignition-view" aria-labelledby="ignition-title">
  <div class="ignition-view__inner">
    <p class="ignition-eyebrow">Start here</p>
    <h1 class="ignition-title" id="ignition-title">What do you want to understand?</h1>
    <p class="ignition-guidance" id="ignition-guidance">Name one concept and sketch your starting map. The draft path is a hypothesis until reconstruction creates evidence.</p>
    <p class="ignition-voice-line">The map stays honest because evidence comes from your reconstruction.</p>

    <!-- Library-cap gate. Hidden by default; shown by renderIgnitionGate() when loadConcepts().length >= 4. -->
    <div class="ignition-cap-gate" id="ignition-cap-gate" hidden>
      <p class="ignition-cap-gate__message">Library is full (4 concepts). Retire one before starting another.</p>
      <button class="ignition-cap-gate__cta" type="button" onclick="App.showLibrary()">Open Library</button>
    </div>

    <!-- Threshold composer. Hidden by renderIgnitionGate() when at cap. -->
    <form class="hero-single-input" id="hero-single-input" onsubmit="return App.runHeroAction(event)" autocomplete="off">
      <div class="hero-threshold-fields">
        <label class="hero-threshold-field" for="hero-single-input-field">
          <span class="hero-threshold-field__label">Concept</span>
          <textarea class="hero-single-input__field hero-single-input__field--concept"
                    id="hero-single-input-field"
                    rows="1"
                    maxlength="200"
                    placeholder='e.g. Photosynthesis'
                    aria-label="What do you want to understand?"
                    aria-describedby="hero-threshold-helper hero-threshold-validation"></textarea>
        </label>
        <label class="hero-threshold-field hero-threshold-field--sketch" for="hero-starting-map-field">
          <span class="hero-threshold-field__label">Write what you already think: parts, guesses, examples, confusions.</span>
          <textarea class="hero-single-input__field hero-single-input__field--sketch"
                    id="hero-starting-map-field"
                    rows="3"
                    maxlength="1200"
                    placeholder="No polished answer needed."
                    aria-describedby="hero-threshold-helper hero-threshold-validation"></textarea>
        </label>
        <p class="hero-threshold-helper" id="hero-threshold-helper">This is global context. The first room will ask one smaller question.</p>
        <p class="hero-threshold-validation" id="hero-threshold-validation" aria-live="polite"></p>
      </div>
      <div class="hero-single-input__row">
        <div class="hero-example-chips" aria-label="Try one of these">
          <span class="hero-example-chips__label">Try</span>
          <button type="button" class="hero-example-chip" data-hero-example="Photosynthesis">Photosynthesis</button>
          <button type="button" class="hero-example-chip" data-hero-example="Entropy">Entropy</button>
          <button type="button" class="hero-example-chip" data-hero-example="The French Revolution">The French Revolution</button>
        </div>
        <button type="submit" class="hero-single-input__submit" disabled>
          <span>Create draft path</span>
          <svg class="hero-single-input__submit-icon" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M5 12h13"></path>
            <path d="m13 6 6 6-6 6"></path>
          </svg>
        </button>
      </div>
    </form>
  </div>
</section>
```

- [ ] **Step 3: Delete the old threshold composer block from `.hero-info`**

Remove `public/index.html:240-279` (the entire `<form class="hero-single-input" ...>` and its empty-state comment on line 239).

- [ ] **Step 4: Delete the empty-state hero copy that was specific to the threshold**

The hero-card's eyebrow/title/desc that referenced "Start here" / "What do you want to understand?" / the empty-state guidance now belongs on Ignition. Replace the Desk hero copy with a concept-context-aware default; if no concept is selected, show a minimal "Open the Desk" voice line and a "Begin at Ignition →" link button.

```html
<!-- inside .hero-info, replacing the old empty-state title/desc/voice/actions block -->
<div class="hero-eyebrow-row">
  <div class="hero-eyebrow" id="hero-eyebrow">Desk</div>
</div>
<h1 class="hero-title" id="title">Your draft paths.</h1>
<p class="desc hero-guidance" id="desc" aria-live="polite">Pick a tile to enter a room, or start a new draft path at Ignition.</p>
<p class="hero-voice-line">The map stays honest because evidence comes from your reconstruction.</p>
<div class="hero-actions">
  <button class="hero-primary-action" type="button" onclick="App.showIgnition()">
    <span class="hero-primary-action__label">Begin at Ignition</span>
    <svg class="hero-primary-action__arrow" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M5 12h13"></path>
      <path d="m13 6 6 6-6 6"></path>
    </svg>
  </button>
</div>
```

Note: this default copy is overwritten by `renderHero()` once a concept is selected. The point is only that an empty Desk no longer shows the threshold composer; it shows a calm pointer to Ignition.

- [ ] **Step 5: Verify the page loads without script errors**

Run: `python3 -m http.server -d public 8765` (background), then `curl -s http://localhost:8765/ | grep -c 'id="ignition-view"'`
Expected: `1`. Kill the server.

- [ ] **Step 6: Commit**

```bash
git add public/index.html
git commit -m "feat(ia): add Ignition view shell and move threshold composer DOM"
```

### Task 3: Wire `showIgnition()` / `hideIgnition()` / `renderIgnitionGate()`

**Files:**
- Modify: `public/js/app.js` (around the existing `showDashboard()` / `showLibrary()` cluster, ~lines 2113-2173)
- Modify: `public/js/dom.js:15`

- [ ] **Step 1: Update `dom.js` exports**

Replace `public/js/dom.js:15`:

```js
// Before
export const addTriggerArea      = document.getElementById('add-trigger-area');

// After
export const ignitionView        = document.getElementById('ignition-view');
```

- [ ] **Step 2: Update the import block in `app.js` to drop `addTriggerArea` and add `ignitionView`**

In `public/js/app.js`, find the import line for `addTriggerArea` from `./dom.js` and replace it with `ignitionView`. (If `addTriggerArea` is not currently imported by name, just remove any references; the deletion in Task 7 will catch them.)

- [ ] **Step 3: Add `setNavActive()` to include `nav-ignition`**

Find `public/js/app.js:2154` and replace the array literal:

```js
// Before
['nav-dashboard', 'nav-library', 'nav-settings'].forEach((navId) => {

// After
['nav-dashboard', 'nav-ignition', 'nav-library', 'nav-settings'].forEach((navId) => {
```

- [ ] **Step 4: Update `hidePrimaryViews()` to also hide `#ignition-view`**

Find `public/js/app.js:2113-2120` and update:

```js
function hidePrimaryViews() {
  const heroCard = document.querySelector('.hero-card');
  const ignitionView = document.getElementById('ignition-view');
  const libraryView = document.getElementById('library-view');
  const settingsView = document.getElementById('settings-view');
  if (heroCard) heroCard.style.display = 'none';
  if (ignitionView) ignitionView.classList.remove('visible');
  if (libraryView) libraryView.classList.remove('visible');
  if (settingsView) settingsView.classList.remove('visible');
}
```

- [ ] **Step 5: Add `showIgnition()` / `hideIgnition()` / `renderIgnitionGate()`**

Insert after `showDashboard()` (after line 2173):

```js
function showIgnition() {
  setNavActive('nav-ignition');
  clearSettingsPanel();
  teardownMapView();
  hidePrimaryViews();
  const view = document.getElementById('ignition-view');
  if (view) view.classList.add('visible');
  renderIgnitionGate();
  if (window.innerWidth < 900) closeDrawer();
  // Focus the concept field so the threshold composer is immediately usable.
  const conceptField = document.getElementById('hero-single-input-field');
  if (conceptField instanceof HTMLTextAreaElement) {
    requestAnimationFrame(() => conceptField.focus());
  }
}

function hideIgnition() {
  const view = document.getElementById('ignition-view');
  if (view) view.classList.remove('visible');
}

function renderIgnitionGate() {
  const atCap = loadConcepts().length >= 4;
  const gate = document.getElementById('ignition-cap-gate');
  const form = document.getElementById('hero-single-input');
  if (gate) gate.hidden = !atCap;
  if (form) form.hidden = atCap;
  // Also disable the Ignition nav entry visually when at cap.
  ['nav-ignition', 'bn-ignition'].forEach((id) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.toggle('disabled', atCap);
    el.setAttribute('aria-disabled', atCap ? 'true' : 'false');
    el.title = atCap ? 'Library full. Retire a concept to add another.' : '';
  });
}
```

- [ ] **Step 6: Export `showIgnition` from the module-level return**

Find `public/js/app.js:4028-4035` (the `return { ... }` of the IIFE / module exports) and add `showIgnition` to the list:

```js
// Before (relevant slice)
showLibrary, hideLibrary, openLibraryConcept, showDashboard, showSettings,

// After
showLibrary, hideLibrary, openLibraryConcept, showDashboard, showIgnition, showSettings,
```

- [ ] **Step 7: Call `renderIgnitionGate()` after every concept-list mutation**

The cap state changes when concepts are added or deleted. Find every call site of `renderConceptList(` and add a sibling `renderIgnitionGate()` call right after. Confirmed call sites (verify before editing):

```bash
grep -n 'renderConceptList(' public/js/app.js
```

For each line, after the call, insert `renderIgnitionGate();` on the following line.

- [ ] **Step 8: Verify no syntax errors**

Run: `node --check public/js/app.js`
Expected: no output (silent success).

Run: `node --check public/js/dom.js`
Expected: no output.

- [ ] **Step 9: Commit**

```bash
git add public/js/app.js public/js/dom.js
git commit -m "feat(ia): add showIgnition route with library-cap gate"
```

### Task 4: Update first-run routing and welcome predicate

**Files:**
- Modify: `public/js/app.js:2439-2440` (boot landing branch)
- Modify: `public/js/app.js:2448-2451` (welcome predicate)
- Modify: `public/js/app.js:1382-1388` (post-create navigation)

**Pre-flight context (verified via Gemini sanity-check):** `showDashboard()` is NOT called on boot. The boot path at `app.js:2433-2440` evaluates `const toLoad = resumeConcept || concepts.find(c => c.id === getActiveId()) || concepts[0] || null;` and then `if (!toLoad) { showEmptyState(); }`. The `.hero-card` is the implicit default-visible surface (no `hidePrimaryViews` runs at boot). `showEmptyState()` just paints copy via `renderHero(null)`; it does not toggle view visibility. `!toLoad` is equivalent to `concepts.length === 0`.

- [ ] **Step 1: Replace the boot empty-state landing with `showIgnition()`**

Find `public/js/app.js:2439-2441`:

```js
// Before
if (!toLoad) {
  showEmptyState();
} else {
```

Replace with:

```js
// After
if (!toLoad) {
  showIgnition();
} else {
```

(`showEmptyState()` is still invoked elsewhere — by `finishDelete` at line 1535 — and remains intact.)

- [ ] **Step 2: Update `maybeShowFirstRunWelcome` `shouldShow` predicate**

Find `public/js/app.js:2448-2451`:

```js
// Before
void maybeShowFirstRunWelcome({
  getSession: () => fetchAuthSession(),
  shouldShow: () => loadConcepts().length === 0 && heroStateChipEl?.dataset.state === 'empty',
});
```

Replace with:

```js
// After
void maybeShowFirstRunWelcome({
  getSession: () => fetchAuthSession(),
  shouldShow: () => loadConcepts().length === 0,
});
```

The `heroStateChipEl?.dataset.state === 'empty'` clause was redundant in the new IA — the hero state chip lives on a hidden Desk surface when the user lands on Ignition. Concept count is the single source of truth for "this is a brand-new learner."

- [ ] **Step 3: After successful concept creation, navigate to Desk and select the new concept**

Find `finishConceptCreateAfterOverlay` (around `app.js:1382-1388`). Insert `showDashboard();` before `selectConcept(concept.id);` so a learner who created their first concept from Ignition lands on the Desk with that concept active.

```js
renderGrid(concepts);
renderConceptList(concepts);
showDashboard();           // <-- add this line
selectConcept(concept.id);
clearHeroThresholdComposer();
closeDrawer();
overlayHandle.removeOverlay(true);
```

- [ ] **Step 4: Decide finishDelete behavior (no change required)**

`finishDelete()` at `app.js:1515-1544` calls `showDashboard()` followed by `showEmptyState()` when the last concept is deleted. After this refactor, the empty Desk renders the new "Pick a tile to enter a room, or start a new draft path at Ignition" copy from Task 2 step 4 — calm, location-respecting, with a path forward. **No change to `finishDelete` is required.** A test assertion update is required instead (Task 9 step 1a).

If during execution this UX feels wrong, the alternative is a one-line change: replace `showDashboard(); showEmptyState();` inside `finishDelete` with `showIgnition();`. Decide live; don't pre-decide.

- [ ] **Step 5: Verify boot works for both states**

Manual smoke (auto-mode acceptable):

Run: `python3 -m http.server -d public 8765` (background)
- Open `http://localhost:8765/` in browser; with empty localStorage should land on Ignition.
- Add a concept; reload; should land on Desk.
- Delete the concept; should remain on Desk with empty-state copy pointing at Ignition.

- [ ] **Step 6: Commit**

```bash
git add public/js/app.js
git commit -m "feat(ia): route to Ignition on first run, Desk thereafter"
```

### Task 5: Move threshold-composer JS bindings to operate on Ignition

**Files:**
- Modify: `public/js/app.js` (`runHeroAction`, `initHeroSingleInput`, `clearHeroThresholdComposer`)
- Modify: `public/js/intro-particles.js` (typing reaction binding)

- [ ] **Step 1: Update `runHeroAction()` to navigate to Desk after submit, not call `showDashboard()` mid-submit**

The current `runHeroAction()` (around `app.js:362`) calls `showDashboard()` then `openDrawer()` then `startAddConcept`. Since the threshold now lives on Ignition, the final landing should be Desk *after* concept creation completes (already wired in Task 4 step 3 via `finishConceptCreateAfterOverlay`). Remove the inline `showDashboard()` and `openDrawer()` calls inside `runHeroAction` — they were navigation side-effects from the old hero context.

```js
// Before (around line 362)
showDashboard();
openDrawer();
startAddConcept({ ... }, originRect);

// After
startAddConcept({
  name: conceptName,
  sketchTurns: [startingMap],
  stage: 'summary',
}, originRect);
```

- [ ] **Step 2: Verify `initHeroSingleInput()` still finds its elements**

`initHeroSingleInput` queries by id (`hero-single-input-field`, `hero-starting-map-field`, `.hero-single-input__submit`). Since IDs are preserved, no change is needed. Confirm by reading the function (around `app.js:418`) and verifying every `getElementById` / `querySelector` returns a node when Ignition mounts.

- [ ] **Step 3: Verify `intro-particles.js` typing-reaction still finds the threshold fields**

`getThresholdFields()` queries by id. The fields moved DOM containers but kept their ids, so the binding still works. Confirm by reading `public/js/intro-particles.js:80-99` — no change needed.

However, the canvas `#intro-particle-canvas` lives inside `.hero-card`. When the user is on Ignition (not Desk), the canvas is not visible. Decision: leave canvas on Desk only for this slice. Typing-reaction will compute against an off-screen canvas and visually do nothing — harmless but wasted work. Document as known quirk; revisit if it bothers the user.

- [ ] **Step 4: Verify**

Run: `node --check public/js/app.js && node --check public/js/intro-particles.js`
Expected: silent success.

- [ ] **Step 5: Commit**

```bash
git add public/js/app.js
git commit -m "refactor(ia): scope hero submit handler to Ignition mount"
```

### Task 6: CSS — replace empty-state hero rules with Ignition-scoped rules

**Files:**
- Modify: `public/css/components.css:2318-2326` (replace `:has()` rules)
- Modify: `public/css/components.css:1009-1043` (keep `.creation-chip-action` reset; unrelated)
- Modify: `public/css/layout.css` (add `#ignition-view.primary-view` layout)

- [ ] **Step 1: Replace the empty-state `:has()` rules with Ignition-scoped rules**

Find:
```css
.hero-info:has(.hero-state-chip[data-state="empty"]) .hero-single-input {
  margin-top: 34px;
}
@media (max-width: 720px) {
  .hero-info:has(.hero-state-chip[data-state="empty"]) .hero-single-input {
    margin-top: 28px;
  }
  ...
}
```

Replace with:
```css
.ignition-view .hero-single-input {
  margin-top: 12px;
}
@media (max-width: 720px) {
  .ignition-view .hero-single-input {
    margin-top: 8px;
  }
}
```

- [ ] **Step 2: Add `#ignition-view` container styles**

Append to `public/css/layout.css`:

```css
#ignition-view {
  display: none;
  flex-direction: column;
  align-items: center;
  padding: 48px 24px 96px;
}
#ignition-view.visible {
  display: flex;
}
.ignition-view__inner {
  width: min(100%, 720px);
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.ignition-eyebrow {
  margin: 0;
  font-family: var(--font-body);
  font-size: var(--text-xs, 12px);
  font-weight: 760;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--text-sub);
}
.ignition-title {
  margin: 0;
  font-family: var(--font-display, var(--font-body));
  font-size: var(--text-3xl, 32px);
  line-height: var(--leading-tight, 1.18);
  color: var(--text);
}
.ignition-guidance,
.ignition-voice-line {
  margin: 0;
  color: var(--text-sub);
  font-family: var(--font-body);
  line-height: var(--leading-relaxed, 1.55);
}
.ignition-cap-gate {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 12px;
  padding: 20px;
  border: 1px solid var(--border, rgba(255,255,255,0.08));
  border-radius: 8px;
  background: var(--surface-2, rgba(255,255,255,0.02));
}
.ignition-cap-gate__cta {
  appearance: none;
  border: 1px solid var(--primary);
  background: transparent;
  color: var(--primary);
  padding: 8px 14px;
  border-radius: 6px;
  font: inherit;
  cursor: pointer;
}
```

- [ ] **Step 3: Add disabled-state styling for Ignition nav entries**

Append to `public/css/components.css` (or wherever `.sidebar-nav-item` lives):

```css
.sidebar-nav-item.disabled,
.bottom-nav-item.disabled {
  opacity: 0.45;
  pointer-events: none;
  cursor: not-allowed;
}
```

- [ ] **Step 4: Bump cache-buster**

In `public/styles.css`, bump the `?v=` suffix on `components.css` and `layout.css` to a fresh value (e.g. `?v=74`). In `public/index.html`, bump `styles.css?v=73` to `?v=74`.

- [ ] **Step 5: Visual verify**

Run: `python3 -m http.server -d public 8765` (background); load `/`; confirm Ignition view renders centered, the threshold composer is visible, the cap gate is hidden.

- [ ] **Step 6: Commit**

```bash
git add public/css/components.css public/css/layout.css public/styles.css public/index.html
git commit -m "feat(ia): style Ignition view and disabled nav state"
```

### Task 7: Remove `add-trigger-area` and rehouse settings panel

**Files:**
- Modify: `public/index.html:84` (delete `<div id="add-trigger-area"></div>`)
- Modify: `public/js/app.js:579-586` (`clearSettingsPanel`), `:619-641` (`renderAddTrigger`), call sites
- Modify: `public/css/components.css` (remove `.add-trigger*` rules)

- [ ] **Step 1: Find `clearSettingsPanel` consumer**

Run: `grep -n 'add-trigger-area\|renderAddTrigger\|clearSettingsPanel\|settings-panel' public/js/app.js`
Expected: list of references. Read each to understand the settings panel's container assumption.

- [ ] **Step 2: Decide settings-panel container**

The settings panel currently mounts inside `#add-trigger-area`. Options:
- **A:** Mount inside `#concept-list` parent (the sidebar's "Concepts" section). Drop-in replacement.
- **B:** Promote settings-panel to its own `#sidebar-settings-host` div in the sidebar.

Pick A for minimum churn. Replace the `#add-trigger-area` div with `<div id="sidebar-settings-host"></div>` so the settings-panel has a stable container.

```html
<!-- Before -->
<div id="add-trigger-area"></div>

<!-- After -->
<div id="sidebar-settings-host"></div>
```

- [ ] **Step 3: Update `clearSettingsPanel` to read the new id**

```js
function clearSettingsPanel() {
  const host = document.getElementById('sidebar-settings-host');
  const settingsPanel = host?.querySelector('.settings-panel');
  if (!settingsPanel) return;
  const settingsBtn = document.getElementById('nav-settings');
  if (settingsBtn) delete settingsBtn.dataset.engaged;
  host.innerHTML = '';
}
```

Note: `clearSettingsPanel` previously called `renderAddTrigger()` to repaint the area. After removal, just clearing the host's contents is sufficient.

- [ ] **Step 4: Remove `renderAddTrigger()` and all call sites**

```bash
grep -n 'renderAddTrigger\(' public/js/app.js
```

Delete the function (`app.js:619-641`) and every call (typically inside `renderConceptList` at line ~616). Also remove the `addTriggerArea` declaration (`app.js` near top, imported from `./dom.js`).

- [ ] **Step 5: Update the settings-panel mount point in `showSettings()`**

The settings panel is mounted by `showSettings()` at `public/js/app.js:3960`. Read that function and update any reference to `#add-trigger-area` (or `addTriggerArea`) to `#sidebar-settings-host`. Also grep belt-and-suspenders:

```bash
grep -n 'settings-panel\|appendChild.*addTriggerArea\|add-trigger-area' public/js/app.js
```

Expected: zero remaining references to `add-trigger-area` after this step.

- [ ] **Step 6: Remove `.add-trigger*` CSS rules**

```bash
grep -n '\.add-trigger' public/css/components.css
```

Delete all matched rules (the button styles for `+ new tink` / `library full`).

- [ ] **Step 7: Verify**

Run: `node --check public/js/app.js`
Expected: silent success.

Manual smoke: open the app, click Settings nav — settings panel mounts in sidebar; click another nav — settings panel clears.

- [ ] **Step 8: Commit**

```bash
git add public/index.html public/js/app.js public/css/components.css
git commit -m "refactor(ia): remove + add-trigger and rehouse settings panel"
```

### Task 8: Update existing copy that references the old "+" or empty-state Desk

**Files:**
- Modify: `public/js/app.js:2302` (`'No draft paths yet. Add a concept on the desk to begin.'`)
- Modify: `public/js/app.js:268-292` (`getHeroGuidance` empty-state copy)

- [ ] **Step 1: Update library empty copy**

```js
// Before (line 2302)
html += '<p class="library-empty" style="margin-top:10px;">No draft paths yet. Add a concept on the desk to begin.</p>';

// After
html += '<p class="library-empty" style="margin-top:10px;">No draft paths yet. Begin one at <a href="javascript:void(0)" onclick="App.showIgnition()">Ignition</a>.</p>';
```

- [ ] **Step 2: Update `getHeroGuidance` empty branch**

```js
// Before
if (!concept) return 'Name one concept and sketch your starting map. The draft path is a hypothesis until reconstruction creates evidence.';

// After
if (!concept) return 'Pick a tile to enter a room, or start a new draft path at Ignition.';
```

The matching `default:` branch should be updated identically.

- [ ] **Step 3: Commit**

```bash
git add public/js/app.js
git commit -m "feat(copy): point empty Desk and Library at Ignition"
```

### Task 9: Smoke test the IA changes end-to-end

**Files:**
- None (manual / scripted smoke)

- [ ] **Step 1: Update the known-failing e2e assertion**

`tests/e2e/test_smoke.py:230` asserts:

```python
expect(clean_page.locator("#title")).to_have_text("What do you want to understand?")
```

This assertion runs after a concept is deleted (returning the user to an empty Desk). Task 2 step 4 changed the empty Desk title to "Your draft paths." Update the assertion:

```python
# Before (line 230)
expect(clean_page.locator("#title")).to_have_text("What do you want to understand?")

# After
expect(clean_page.locator("#title")).to_have_text("Your draft paths.")
```

If `finishDelete` was changed in Task 4 step 4 to route to Ignition instead, the assertion should target the Ignition title selector instead — but the default decision in this plan is no change to `finishDelete`, so the Desk-title assertion is correct.

- [ ] **Step 1a: Search for any other tests that touch the threshold or "+"**

Run:
```bash
grep -rn 'add-trigger\|hero-single-input\|hero-starting-map\|runHeroAction\|nav-dashboard\|new tink\|What do you want to understand' tests/
```

Note any additional tests to update. Update any test that relied on the threshold appearing inside `.hero-card` to first navigate to Ignition (`page.locator("#nav-ignition").click()`).

- [ ] **Step 2: Run the existing parity test**

Run: `python3 -m pytest tests/test_frontend_sketch_validation.py -x`
Expected: PASS.

- [ ] **Step 3: Run any e2e smoke if present**

Run: `python3 -m pytest tests/e2e/test_smoke.py -x` (only if test infrastructure is up — skip otherwise and document).
Expected: PASS or list of failures to triage.

- [ ] **Step 4: Manual flow check**

In a browser:
1. Empty localStorage → loads Ignition. ✓
2. Type concept + insubstantive sketch → submit disabled. ✓
3. Type concept + substantive sketch → submit enabled → click → summary card appears with starting map preloaded → confirm → Desk shows new tile, threshold composer cleared. ✓
4. With 1+ concept, Desk loads on reload. ✓
5. With 4 concepts, Ignition nav entry shows disabled `library full`; clicking does nothing. Click Ignition directly via URL or focus — see cap-gate banner with "Open Library" CTA. ✓
6. Settings panel still mounts/clears in sidebar. ✓
7. No `+ new tink` button anywhere. ✓

- [ ] **Step 5: Commit any test updates**

```bash
git add tests/
git commit -m "test(ia): adapt smoke test to Ignition route"
```

(Skip if no test files changed.)

### Task 10: Final pass — grep for orphans and verify

**Files:**
- None (verification only)

- [ ] **Step 1: Grep for orphan references**

```bash
grep -rn 'add-trigger\|addTriggerArea\|renderAddTrigger\|new tink' public/ tests/ docs/
```

Expected: no matches in `public/` or `tests/`. (docs/ may still have prose references; leave for a separate copy pass.)

- [ ] **Step 2: Grep for conflict markers**

```bash
grep -rn '<<<<<<<\|=======\|>>>>>>>' public/ tests/
```

Expected: no matches. (Per global memory: never commit conflict markers.)

- [ ] **Step 3: Final commit if any cleanup needed**

```bash
git status
git diff
# only commit if there's leftover work
```

---

## Self-review

**Spec coverage:**
- Delete the in-dashboard "+": Task 7. ✓
- Add separate menu item for concept ignition: Task 1 (nav entries) + Task 2 (view shell) + Task 3 (route function). ✓
- Desk remains the isometric dashboard: Tasks 2, 5, 8 (remove threshold from Desk; keep iso board; update copy). ✓
- Library cap gating handled before submit: Task 3 step 5 (`renderIgnitionGate`) + Task 6 (disabled nav state). ✓
- Preserve effort principle (cap surfaced before learner sinks effort): Task 3 step 5 ✓.
- First-run routing: Task 4. ✓
- Tests not broken: Task 9. ✓

**Placeholder scan:**
- No "TBD", no "implement later", no "fill in details" in any task body. Code shown for every step.

**Type/symbol consistency:**
- `showIgnition` defined in Task 3, exported in Task 3 step 6, called from Tasks 1, 4, 8. Same name throughout. ✓
- `renderIgnitionGate` defined in Task 3, called from Tasks 3, 4. ✓
- `#ignition-view` id used consistently. ✓
- `#sidebar-settings-host` id introduced in Task 7 step 2, referenced in step 3. ✓

---

## Execution handoff

After Gemini sanity check + any plan revisions: subagent-driven execution recommended (10 small tasks, easy to review per-task). Inline execution acceptable if the user wants to iterate live.
