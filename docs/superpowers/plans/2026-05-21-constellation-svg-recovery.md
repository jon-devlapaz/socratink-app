# Constellation SVG Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the temporary Constellation placeholder with the visual-only SVG grammar recovered from the deleted `public/js/graph-view.js`, while preserving the current Route page as the default reconstruction surface.

**Architecture:** Keep Constellation as a sibling view inside `#map-view`, not inside the Route page. Add a focused `public/js/concept-constellation-view.js` renderer that receives parsed concept data, current training evidence, and active entry id, then returns safe SVG markup. The renderer must not import or revive old graph controller behavior, old detail panels, repair UI, or legacy `drill_status` truth.

**Tech Stack:** Vanilla JS ES modules, SVG, existing training store, existing `concept-page-view.js` helpers, Playwright/pytest e2e, frontend V8 diff coverage via `./scripts/check-coverage.sh`.

---

## Agy Risk Review Summary

**Verdict:** GO, with strict constraints.

Top risks to design against:

1. Information leakage through `detail`, `mechanism`, `fullLabel`, `title`, `aria-label`, or tooltip attributes.
2. State divergence if Constellation reads legacy `graphData.*.drill_status` instead of current training evidence.
3. Structural spoiler leakage from future node labels.
4. Renderer bloat if old `graph-view.js` is copied wholesale.
5. SVG clipping from old fixed coordinate assumptions.
6. Interaction hijacking if old `window.SocratinkApp.runInspectAction` or drill handlers return.
7. Motion accessibility regressions from beams, ripples, or starfield animation.
8. Starfield performance if regenerated on every active-node update.
9. CSS collisions if old `.graph-*` classes return globally.
10. Active-node disconnect if Constellation selection does not sync the hidden Route state.

Strict bans from old `graph-view.js`:

- `repairProgressMarkup`, repair calibration, confidence controls, and all repair panels.
- `detailMarkupForNode`, study panels, disclosure panels, and any content reveal UI.
- `deriveCoreState`, `deriveBackboneState`, `deriveSubnodeState`, `deriveClusterState`.
- Wheel zoom, pan timers, drag math, `panViewBoxTo`, and graph-controller lifecycle code.
- `window.SocratinkApp.runInspectAction`, direct drill triggers, chat/render side effects.
- Any DOM attribute containing mechanisms, study notes, definitions, or solved explanations before reconstruction.

## File Structure

- Modify `public/js/concept-page-view.js`
  - Export one small state helper so Route and Constellation derive entry state from the same logic.
- Create `public/js/concept-constellation-view.js`
  - Owns safe graph model building, static SVG layout, label redaction, starfield generation, and SVG markup.
- Modify `public/js/app.js`
  - Imports the new renderer, passes data/training/active id, wires safe node selection back to Route.
- Modify `public/css/concept-page.css`
  - Replaces placeholder Constellation styles with scoped `.concept-constellation__*` graph styles.
- Modify cache pins in `public/index.html`, `public/styles.css`, and `public/css/index.css`.
- Modify tests:
  - `tests/test_frontend_app_helper_modules.py`
  - `tests/e2e/test_smoke.py`

## Task 1: Export Route-Compatible Entry State

**Files:**
- Modify: `public/js/concept-page-view.js`
- Test: `tests/test_frontend_app_helper_modules.py`

- [ ] **Step 1: Write the failing helper export test**

Add a Node-based frontend module test that imports `deriveConceptEntryViewState` and checks locked/ready/primed state from the same contract Constellation will use:

```js
import assert from 'node:assert/strict';
import {
  deriveConceptEntryViewState,
  deriveConceptEntries,
} from './public/js/concept-page-view.js';

const data = {
  clusters: [{
    id: 'c1',
    label: 'Mechanism cluster',
    subnodes: [
      { id: 'gate', label: 'Sodium gate' },
      { id: 'spread', label: 'Signal spread' },
    ],
  }],
};

const entries = deriveConceptEntries(data);
assert.equal(deriveConceptEntryViewState(entries, 0, null).state, 'ready to reconstruct');
assert.equal(deriveConceptEntryViewState(entries, 1, null).state, 'locked');
assert.equal(
  deriveConceptEntryViewState(entries, 0, {
    node_records: {
      gate: {
        attempts: [{ at: '2026-05-21T00:00:00Z', classification: 'partial' }],
      },
    },
  }).state,
  'primed',
);
```

- [ ] **Step 2: Run the focused test and confirm it fails**

Run:

```bash
pytest tests/test_frontend_app_helper_modules.py -q
```

Expected: fail because `deriveConceptEntryViewState` is not exported.

- [ ] **Step 3: Add the minimal export**

In `public/js/concept-page-view.js`, export a wrapper around the existing private state derivation:

```js
export function deriveConceptEntryViewState(backbone, index, training = null, options = {}) {
  const entry = backbone[index] || null;
  const id = getConceptEntryId(entry, index);
  const derived = entryTraining(backbone, index, training, options);
  return {
    id,
    attempted: Boolean(derived.attempted),
    state: entryLearnerState(backbone, index, training, options),
    nextAction: derived.next_action || null,
  };
}
```

- [ ] **Step 4: Run the focused test and confirm it passes**

Run:

```bash
pytest tests/test_frontend_app_helper_modules.py -q
```

Expected: pass.

## Task 2: Create the Pure Constellation Renderer

**Files:**
- Create: `public/js/concept-constellation-view.js`
- Test: `tests/test_frontend_app_helper_modules.py`

- [ ] **Step 1: Write failing renderer tests**

Add a Node-based test that imports `renderConceptConstellationHtml` and verifies safe output:

```js
import assert from 'node:assert/strict';
import { renderConceptConstellationHtml } from './public/js/concept-constellation-view.js';

const data = {
  metadata: {
    source_title: 'How sodium channels create an action potential',
    core_thesis: 'Sodium channels open at threshold and sodium enters.',
  },
  clusters: [{
    id: 'gate-cluster',
    label: 'Gating mechanism',
    description: 'SOURCE PREVIEW SHOULD NOT APPEAR',
    subnodes: [
      {
        id: 'gate',
        label: 'Sodium gate',
        mechanism: 'Sodium channels open at threshold.',
        learner_scaffold: { task_label: 'Sodium gate' },
      },
      {
        id: 'spread',
        label: 'Signal spread',
        mechanism: 'The depolarization propagates.',
        learner_scaffold: { task_label: 'Signal spread' },
      },
    ],
  }],
};

const html = renderConceptConstellationHtml(data, {
  activeEntryId: 'gate',
  training: null,
});

assert.match(html, /concept-constellation__svg/);
assert.match(html, /Sodium gate/);
assert.match(html, /Entry 02/);
assert.doesNotMatch(html, /Sodium channels open at threshold/);
assert.doesNotMatch(html, /SOURCE PREVIEW SHOULD NOT APPEAR/);
assert.doesNotMatch(html, /The depolarization propagates/);
```

- [ ] **Step 2: Run the focused test and confirm it fails**

Run:

```bash
pytest tests/test_frontend_app_helper_modules.py -q
```

Expected: fail because `concept-constellation-view.js` does not exist.

- [ ] **Step 3: Implement `concept-constellation-view.js`**

Create a small pure renderer. Extract only these visual/layout primitives from old `graph-view.js`: `clamp`, `degToRad`, `polar`, `resolveBackboneAngles`, `resolveAngularSpread`, `buildCurvePath`, and seeded star generation. Do not copy old detail or state helpers.

Public API:

```js
import { escHtml } from './html.js';
import {
  deriveConceptEntries,
  deriveConceptEntryViewState,
  getConceptEntryId,
} from './concept-page-view.js?v=9';

export function renderConceptConstellationHtml(data = {}, options = {}) {
  const entries = deriveConceptEntries(data);
  const training = options.training || null;
  const activeEntryId = options.activeEntryId || getConceptEntryId(entries[0], 0);
  const model = buildConstellationModel(data, entries, training, activeEntryId);
  return renderConstellation(model);
}
```

Renderer rules:

- Active entry label may show the real label.
- Attempted entries may show the real label.
- Ready first entry may show the real label.
- Locked future entries render as `Entry 02`, `Entry 03`, etc.
- No `mechanism`, `study_note`, `description`, `detail`, or source preview is ever copied into markup.
- Use `data-entry-id`, `data-state`, and safe `aria-label` only.

- [ ] **Step 4: Run the focused test and confirm it passes**

Run:

```bash
pytest tests/test_frontend_app_helper_modules.py -q
```

Expected: pass.

## Task 3: Wire App Mode to the New Renderer

**Files:**
- Modify: `public/js/app.js`
- Test: `tests/e2e/test_smoke.py`

- [ ] **Step 1: Write failing e2e assertions**

Extend `test_concept_view_opens_to_route_margin_canvas`:

```python
clean_page.locator("#concept-view-switch").click()
constellation = clean_page.locator("#concept-constellation-content")
expect(constellation).to_be_visible()
expect(constellation.locator(".concept-constellation__node")).to_have_count(4)
expect(constellation).to_contain_text("Sodium gate")
expect(constellation).to_contain_text("Entry 02")
expect(constellation).not_to_contain_text("Opening rule")
expect(constellation).not_to_contain_text("Sodium channels open at threshold")
expect(constellation).not_to_contain_text("This generated summary must not")
```

- [ ] **Step 2: Run the focused e2e and confirm it fails**

Run:

```bash
pytest tests/e2e/test_smoke.py::test_concept_view_opens_to_route_margin_canvas -q
```

Expected: fail until `app.js` uses the new renderer and redacts locked entries.

- [ ] **Step 3: Replace placeholder rendering in `app.js`**

Import:

```js
import { renderConceptConstellationHtml } from './concept-constellation-view.js?v=1';
```

Change `renderConceptConstellationView` to delegate:

```js
function renderConceptConstellationView(mountEl, data, concept, training = null, options = {}) {
  if (!mountEl || !data) return;
  mountEl.innerHTML = renderConceptConstellationHtml(data, {
    concept,
    training,
    activeEntryId: options?.activeEntryId || _activeEntryId,
  });
  updateConstellationActiveEntry(options?.activeEntryId || _activeEntryId);
}
```

- [ ] **Step 4: Run the focused e2e and confirm it passes**

Run:

```bash
pytest tests/e2e/test_smoke.py::test_concept_view_opens_to_route_margin_canvas -q
```

Expected: pass.

## Task 4: Add Safe Node Selection

**Files:**
- Modify: `public/js/app.js`
- Test: `tests/e2e/test_smoke.py`

- [ ] **Step 1: Write failing e2e selection assertions**

Use a concept where the second entry has learner evidence, so it is safe to select and label:

```python
clean_page.locator("#concept-view-switch").click()
clean_page.locator('.concept-constellation__node[data-entry-id="opening-rule"]').click()
clean_page.locator("#concept-view-switch").click()
expect(clean_page.locator(".concept-page-b2__entry-title")).to_contain_text("Opening rule")
```

Also assert draft preservation if the first Route textarea had text before selecting.

- [ ] **Step 2: Run the focused e2e and confirm it fails**

Run:

```bash
pytest tests/e2e/test_smoke.py::test_concept_view_opens_to_route_margin_canvas -q
```

Expected: fail because Constellation nodes are not wired.

- [ ] **Step 3: Bind safe Constellation node clicks**

In `bindMapModeControls`, add a delegated listener branch:

```js
const constellationNode = event.target instanceof Element
  ? event.target.closest('.concept-constellation__node[data-entry-id]')
  : null;
if (constellationNode) {
  const entryId = constellationNode.getAttribute('data-entry-id');
  const concept = getActiveConcept();
  const data = parseConceptGraphData(concept);
  if (entryId && data && concept) {
    void trainingStore.loadTraining(concept.id)
      .then((training) => setActiveEntry(entryId, data, concept, training))
      .catch(() => setActiveEntry(entryId, data, concept, null));
  }
}
```

Do not auto-trigger study, drill, repair, chat, or content reveal.

- [ ] **Step 4: Run the focused e2e and confirm it passes**

Run:

```bash
pytest tests/e2e/test_smoke.py::test_concept_view_opens_to_route_margin_canvas -q
```

Expected: pass.

## Task 5: Replace Placeholder Styles With Scoped SVG Craft

**Files:**
- Modify: `public/css/concept-page.css`
- Modify: `public/styles.css`
- Modify: `public/css/index.css`
- Modify: `public/index.html`
- Test: browser visual check plus e2e

- [ ] **Step 1: Add scoped styles only**

Keep selectors under `.concept-constellation__*`. Do not introduce `.graph-node`, `.graph-edge`, `.graph-stage`, or global `.node-*` selectors.

Required style blocks:

- static starfield: `.concept-constellation__stars`
- SVG stage: `.concept-constellation__svg`
- structural edges: `.concept-constellation__edge`
- lateral edges: `.concept-constellation__edge--lateral`
- node groups: `.concept-constellation__node`
- active, ready, primed, needs-repair, solidified state variants
- reduced motion overrides under `@media (prefers-reduced-motion: reduce)` and `html[data-motion="reduced"]`

- [ ] **Step 2: Bump stylesheet cache pins**

Because `public/css/concept-page.css` is imported through `public/styles.css`, bump all three:

```text
public/styles.css: ./css/concept-page.css?v=N
public/css/index.css: ../styles.css?v=N
public/index.html: /css/index.css?v=N
```

- [ ] **Step 3: Run syntax and focused e2e**

Run:

```bash
node --check public/js/app.js
pytest tests/e2e/test_smoke.py::test_concept_view_opens_to_route_margin_canvas -q
```

Expected: pass.

## Task 6: Final Verification

**Files:**
- No new implementation files unless prior tasks identify test-only changes.

- [ ] **Step 1: Run focused frontend module tests**

Run:

```bash
pytest tests/test_frontend_app_helper_modules.py -q
```

Expected: pass.

- [ ] **Step 2: Run focused e2e**

Run:

```bash
pytest tests/e2e/test_smoke.py::test_concept_view_opens_to_route_margin_canvas -q
```

Expected: pass.

- [ ] **Step 3: Run full diff coverage gate**

Run:

```bash
./scripts/check-coverage.sh
```

Expected: 100% diff coverage.

- [ ] **Step 4: Browser visual review**

Open `http://localhost:8002/`, open a concept, click `Constellation`, and verify:

- Route is default.
- Current typed draft survives toggling.
- Constellation has recovered visual richness: starfield, central thesis, branch/orbit geometry, halos, and edges.
- Locked/future labels are redacted.
- No mechanism/study/source-preview text appears in the Constellation DOM before attempt.
- Reduced motion disables moving pips/ripples if those are included.

## Self-Review

- Spec coverage: sibling view contract, visual recovery, no content leakage, state parity, draft preservation, and motion/performance constraints are all mapped to tasks.
- Placeholder scan: no TBD/TODO placeholders remain.
- Type consistency: renderer API is `renderConceptConstellationHtml(data, options)`; app adapter is `renderConceptConstellationView(mountEl, data, concept, training, options)`.
- Scope check: this plan intentionally does not add Feynman notes, cross-concept connections, action cards, or automatic post-attempt transitions. Those are later product slices.
