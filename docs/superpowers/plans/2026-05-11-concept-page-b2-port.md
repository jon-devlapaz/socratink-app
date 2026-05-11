# Concept Page B-2 Port — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the founder-approved "B-2 Strip + page" concept-page design from the lab prototype (`public/_lab/concept-page-iterations.html?variant=page`) into production. Replaces the current `#map-content` Route-view card-stack (6 cards) with a single-document layout: sticky map strip + threshold quote + large active entry block + faint locked nearby list.

**Architecture:**
- Modify `#map-content`'s rendered structure (in `showMapView` and friends in `public/js/app.js`) to emit the B-2 sectional layout instead of the existing card stack
- Add new CSS file `public/css/concept-page.css` for the B-2 styles (ported from the lab, scoped under `.concept-page-b2`)
- Reuse the existing concept-header (`#concept-header`) — it already renders title + tags
- Reuse the existing `#graph-content` two-pane mount and the Route/Graph toggle infrastructure (B-2 replaces the Route content; Graph view stays intact)
- Strip rendering for v1: a horizontal SVG of progress dots derived from real backbone data (locked / primed / active states), NOT a full graph render. Compact, oriented, 110px tall
- Add the "Re-edit sketch" affordance (Jordan/Gemini's request) as a small text link near the threshold quote — opens the existing sketch-edit flow if available, otherwise renders as a non-functional placeholder for v1.1

**Tech Stack:**
- Vanilla JS in `public/js/app.js` (matches existing module style)
- CSS via cascade — link in `public/styles.css` chain
- Brand tokens (`--surface-page-theme`, `--text-strong`, `--accent-primary`, etc.) from `public/css/variables.css`

**Doctrinal guardrails (preserve all):**
- No praise / scoring / mastery copy
- No "AI is typing" indicator
- No "great job" or "you understand X" language
- No streaks / badges / progress bars / XP
- The threshold quote shows the learner's actual words, verbatim
- The active entry block is the single largest interactive surface
- Locked nearby entries stay locked-by-default (faint list, not actionable)

---

## File Structure

**Create:**
- `public/css/concept-page.css` — B-2 styles (concept-page__strip, __threshold, __entry, __nearby, etc.)
- `tests/e2e/test_concept_page_b2.py` — Playwright e2e covering: open a concept, see strip + threshold + active entry, click "Try from memory" → enters chamber

**Modify:**
- `public/index.html` — link the new CSS via `public/styles.css` chain; bump cache-busts
- `public/styles.css` — add `@import './css/concept-page.css?v=1';`
- `public/css/index.css` — bump styles.css `?v=` pin (per cache-bust both layers convention)
- `public/js/app.js` — replace the body of the Route-view rendering inside `showMapView` to emit the B-2 layout; add `renderConceptPageB2(mapContent, data, concept)` helper

**Untouched:**
- `public/js/graph-view.js` — Graph view stays as-is
- `#graph-content` markup in `index.html` — Graph view stays as-is
- The Route/Graph toggle (`#map-mode-study` / `#map-mode-graph`) — stays; Route now renders B-2
- Backend, /api/drill, /api/extract — unchanged

---

## Acceptance Criteria

1. Opening a concept page shows: header (title + crystal mark + pills) → map strip (110px, with backbone nodes as dots, active highlighted) → threshold quote (italic blockquote, violet left rule) → active entry block (eyebrow + H2 + purpose + "Try from memory →" CTA) → faint nearby-entries list at bottom
2. The layout works in BOTH light and dark modes (uses `--surface-page-theme` and `--text-strong` tokens)
3. The threshold quote shows `concept.threshold` text verbatim if it exists; otherwise shows a placeholder hint that the learner hasn't sketched yet
4. The active entry's title comes from the real LLM-generated entry data (NOT placeholder labels — this is the doctrinal trust gap from the codex synthesis; the agent must thread the real titles through)
5. The "Try from memory →" CTA calls `App.startDrillFromMap()` with the active node — opens the chamber via the same path as the existing entry-card CTA
6. The Route/Graph toggle still works; switching to Graph shows the existing `#graph-content` two-pane unchanged
7. Coverage gate (`./scripts/check-coverage.sh`) exits 0 (or documented as failing for the same worktree-vs-main reason)
8. The Playwright smoke (Task 8) passes against the worktree dev server on `:8001`

---

## Task 1: Pre-flight + read the lab

**Files:** none

- [ ] **Step 1: Confirm worktree state**

```bash
cd /Users/jondev/dev/socratink/prod/socratink-app/.worktrees/drill-chamber-port
git status --short
```

Expected: clean working tree on `feat/drill-chamber-port`. (Other lab + chamber commits already landed.)

- [ ] **Step 2: Read the lab page in full**

```bash
wc -l public/_lab/concept-page-iterations.html
```

Then read it. The B-2 variant section is your design-of-record. Identify the markup spine (`.v-page .doc`, `.doc__threshold`, `.doc__entry-eyebrow`, `.doc__entry-title`, `.doc__entry-purpose`, `.doc__entry-cta`, `.doc__nearby`, `.doc__nearby-list`, `.doc__nearby-item`) and the strip spine (`.map-strip__inner`, `.strip-edge`, `.strip-node--locked`, `.strip-node--primed`).

- [ ] **Step 3: Read the current showMapView**

In `public/js/app.js` find `showMapView(concept, opts = {})` (~line 1927). Read it through to its end. Identify where `#map-content` gets its inner HTML written. Note the data shape it consumes (`data.metadata`, `data.backbone`, `data.clusters`, `data.relationships`).

- [ ] **Step 4: Sample real concept data shape**

```bash
grep -n "core_thesis\|threshold\|sketch\|clusters\[" public/js/app.js | head -20
```

Identify which field on `concept` or `data.metadata` carries the learner's threshold sketch text. If there's no clear field, the threshold quote should fall back to `data.metadata.core_thesis` (already used elsewhere) for v1.

---

## Task 2: Create the CSS

**Files:** Create `public/css/concept-page.css`

- [ ] **Step 1: Create the file with the B-2 styles, ported from the lab**

Port the `.v-page` and `.map-strip` rules from `public/_lab/concept-page-iterations.html` (look for the comment block `/* B-2 — STRIP + PAGE */` and the SHARED `.map-strip` block above it).

Use these production-class names instead of the lab classes:
- `.v-page` → `.concept-page-b2`
- `.v-page .doc` → `.concept-page-b2__doc`
- `.v-page .doc__threshold` → `.concept-page-b2__threshold`
- `.v-page .doc__entry-eyebrow` → `.concept-page-b2__entry-eyebrow`
- `.v-page .doc__entry-title` → `.concept-page-b2__entry-title`
- `.v-page .doc__entry-purpose` → `.concept-page-b2__entry-purpose`
- `.v-page .doc__entry-cta` → `.concept-page-b2__entry-cta`
- `.v-page .doc__nearby` → `.concept-page-b2__nearby`
- `.v-page .doc__nearby-eyebrow` → `.concept-page-b2__nearby-eyebrow`
- `.v-page .doc__nearby-list` → `.concept-page-b2__nearby-list`
- `.v-page .doc__nearby-item` → `.concept-page-b2__nearby-item`
- `.v-page .doc__nearby-num` → `.concept-page-b2__nearby-num`
- `.v-page .doc__nearby-status` → `.concept-page-b2__nearby-status`
- `.map-strip` → `.concept-strip`
- `.map-strip__inner` → `.concept-strip__inner`
- `.map-strip__svg` → `.concept-strip__svg`
- `.map-strip__overlay` → `.concept-strip__overlay`
- `.map-strip__active-name` → `.concept-strip__active-name`
- `.strip-edge` → `.concept-strip__edge`
- `.strip-node` → `.concept-strip__node`
- `.strip-node--locked` → `.concept-strip__node--locked`
- `.strip-node--primed` → `.concept-strip__node--primed`

Add a small `.concept-page-b2__threshold-edit` link style:

```css
.concept-page-b2__threshold-edit {
  display: inline-block;
  margin-left: 12px;
  font-size: 11px;
  letter-spacing: 0.04em;
  color: var(--accent-primary);
  text-decoration: none;
  border-bottom: 1px dashed currentColor;
  padding-bottom: 1px;
  cursor: pointer;
}
.concept-page-b2__threshold-edit:hover { color: var(--text-strong); }
```

Header at the top of the file:

```css
/* concept-page.css
   Production styles for the B-2 "Strip + page" concept page layout.
   Design-of-record: public/_lab/concept-page-iterations.html?variant=page
   Synthesis from Linear (single-pane work column) + Heptabase
   (constellation as orientation) + Notion (faint nearby list).
   Founder pick. Customer-validated by Jordan/Gemini ADHD persona. */
```

- [ ] **Step 2: Wire the CSS into the cascade**

In `public/styles.css`, add at the end of the @import block:

```css
@import './css/concept-page.css?v=1';
```

In `public/css/index.css`, bump the `styles.css?v=` pin by +1.

In `public/index.html`, bump the outer `index.css?v=` pin by +1.

- [ ] **Step 3: Smoke test the CSS file is served**

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8001/css/concept-page.css
```

Expected: `200`.

- [ ] **Step 4: Commit**

```bash
git add public/css/concept-page.css public/styles.css public/css/index.css public/index.html
git commit -m "feat(concept-page): add B-2 styles (strip + page layout)"
```

---

## Task 3: Write the B-2 renderer in app.js

**Files:** Modify `public/js/app.js`

- [ ] **Step 1: Add the new renderer function**

Above `showMapView` in `app.js`, add a new function:

```js
/**
 * Render the B-2 "Strip + page" concept page layout into #map-content.
 * Replaces the prior Route view card stack.
 *
 * @param {HTMLElement} mountEl - The #map-content element
 * @param {Object} data - Parsed graphData (metadata, backbone, clusters, relationships)
 * @param {Object} concept - The full concept object (for threshold text + name)
 */
function renderConceptPageB2(mountEl, data, concept) {
  if (!mountEl || !data) return;
  const meta = data.metadata || {};
  const backbone = Array.isArray(data.backbone) ? data.backbone : [];

  // Threshold text -- use concept.threshold if present (the learner's sketch),
  // else fall back to data.metadata.core_thesis (the LLM-generated thesis).
  const thresholdText = (concept?.threshold || meta.core_thesis || '').trim();
  const conceptName = meta.source_title || concept?.name || 'Concept';

  // Identify the active entry. For v1: first backbone entry that isn't
  // 'solidified' (i.e., the next thing to attempt). Falls back to first
  // backbone entry, then to a synthetic core-thesis stub.
  const isActionable = (n) => {
    const status = n?.drill_status || 'locked';
    return status !== 'solidified';
  };
  const activeEntry = backbone.find(isActionable) || backbone[0] || {
    id: 'core-thesis',
    label: 'Core thesis',
    purpose: 'The first entry asks for the governing idea, not the whole source.',
    drill_status: 'locked',
  };
  const activeIdx = Math.max(0, backbone.indexOf(activeEntry));

  // Nearby entries: every backbone entry that isn't the active one
  const nearby = backbone.filter((n) => n !== activeEntry);

  // Build the strip SVG
  const stripWidth = 600;
  const stripHeight = 110;
  const strokeY = stripHeight / 2;
  const totalNodes = backbone.length || 1;
  const padX = 60;
  const span = stripWidth - 2 * padX;
  const stepX = totalNodes > 1 ? span / (totalNodes - 1) : 0;

  const stripNodes = backbone.map((node, i) => {
    const x = padX + i * stepX;
    const status = node.drill_status || 'locked';
    const isPrimed = status === 'primed' || status === 'drilled' || status === 'solidified';
    const isActive = i === activeIdx;
    const cls = ['concept-strip__node', isPrimed ? 'concept-strip__node--primed' : 'concept-strip__node--locked'];
    if (isActive) cls.push('is-active');
    const r = isActive ? 9 : (isPrimed ? 7 : 6);
    return `<g class="${cls.join(' ')}"><circle cx="${x}" cy="${strokeY}" r="${r}"></circle>${
      isActive ? `<text x="${x}" y="${strokeY + 25}">${escHtml(node.label || 'entry')}</text>` : ''
    }</g>`;
  }).join('');

  const stripEdges = backbone.slice(1).map((_, i) => {
    const x1 = padX + i * stepX;
    const x2 = padX + (i + 1) * stepX;
    const isActiveEdge = i + 1 === activeIdx;
    return `<line class="concept-strip__edge${isActiveEdge ? ' is-active' : ''}" x1="${x1}" y1="${strokeY}" x2="${x2}" y2="${strokeY}"></line>`;
  }).join('');

  const stripActiveLabel = activeEntry.label
    ? `${escHtml(activeEntry.label)} · ${activeIdx + 1} of ${totalNodes}`
    : `${activeIdx + 1} of ${totalNodes}`;

  // Build the threshold quote (with re-edit affordance)
  const thresholdHtml = thresholdText
    ? `
      <p class="concept-page-b2__threshold">
        ${escHtml(thresholdText)}
        <a class="concept-page-b2__threshold-edit" href="javascript:void(0)" data-edit-threshold>edit</a>
      </p>
    `
    : `
      <p class="concept-page-b2__threshold concept-page-b2__threshold--empty">
        You have not yet sketched what you think is inside this concept.
        <a class="concept-page-b2__threshold-edit" href="javascript:void(0)" data-edit-threshold>add sketch</a>
      </p>
    `;

  // Build the active entry block
  const entryEyebrow = `${escHtml(activeEntry.drill_status === 'primed' ? 're-drill ready · entry' : 'first cold attempt · entry')} ${activeIdx + 1} of ${totalNodes}`;
  const entryPurpose = activeEntry.purpose || 'The first entry asks for the governing idea, not the whole source. No study material yet — write what you can reconstruct from memory.';
  const ctaLabel = activeEntry.drill_status === 'primed' ? 'Re-drill from memory' : 'Try from memory';

  const activeHtml = `
    <span class="eyebrow concept-page-b2__entry-eyebrow">${entryEyebrow}</span>
    <h2 class="concept-page-b2__entry-title">${escHtml(activeEntry.label || 'Core thesis')}</h2>
    <p class="concept-page-b2__entry-purpose">${escHtml(entryPurpose)}</p>
    <button class="concept-page-b2__entry-cta" type="button" data-active-entry-id="${escHtml(activeEntry.id || 'core-thesis')}">${ctaLabel}</button>
  `;

  // Build the nearby list
  const nearbyHtml = nearby.length
    ? `
      <section class="concept-page-b2__nearby">
        <span class="eyebrow concept-page-b2__nearby-eyebrow">nearby entries · all locked until first attempt</span>
        <div class="concept-page-b2__nearby-list">
          ${nearby.map((n, i) => {
            const num = String(backbone.indexOf(n) + 1).padStart(2, '0');
            const label = escHtml(n.label || 'entry');
            const status = (n.drill_status || 'locked').toUpperCase();
            return `
              <div class="concept-page-b2__nearby-item">
                <span class="concept-page-b2__nearby-num">${num}</span>
                <span>${label}</span>
                <span class="concept-page-b2__nearby-status">${escHtml(status)}</span>
              </div>
            `;
          }).join('')}
        </div>
      </section>
    `
    : '';

  // Mount the whole thing
  mountEl.classList.add('concept-page-b2');
  mountEl.innerHTML = `
    <div class="concept-strip">
      <div class="concept-strip__inner">
        <svg class="concept-strip__svg" viewBox="0 0 ${stripWidth} ${stripHeight}" preserveAspectRatio="xMidYMid meet">
          ${stripEdges}
          ${stripNodes}
        </svg>
        <div class="concept-strip__overlay">
          <span class="eyebrow">draft route</span>
          <span class="concept-strip__active-name">${stripActiveLabel}</span>
        </div>
      </div>
    </div>
    <div class="concept-page-b2__doc">
      ${thresholdHtml}
      ${activeHtml}
      ${nearbyHtml}
    </div>
  `;

  // Wire the CTA. Reuse the existing startDrillFromMap path.
  const ctaBtn = mountEl.querySelector('.concept-page-b2__entry-cta');
  if (ctaBtn) {
    ctaBtn.addEventListener('click', () => {
      window.App?.startDrillFromMap?.();
    });
  }

  // Wire the re-edit affordance. v1: route to ignition launch pad with
  // the existing concept selected. If that route doesn't exist yet, log
  // a console hint and accept (placeholder for v1.1).
  const editLinks = mountEl.querySelectorAll('[data-edit-threshold]');
  editLinks.forEach((link) => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      if (typeof window.App?.editThresholdForActiveConcept === 'function') {
        window.App.editThresholdForActiveConcept();
      } else {
        console.info('[concept-page] re-edit sketch requested; route not wired (v1.1)');
      }
    });
  });
}

// Tiny html-escape helper if escHtml isn't already in scope. If escHtml
// already exists in app.js (it does -- search), reuse it and delete this.
function _escHtmlB2(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
```

**Audit before pasting:** `escHtml` already exists in app.js. Use the existing one and DELETE the `_escHtmlB2` fallback above.

- [ ] **Step 2: Replace the existing Route-view render with renderConceptPageB2**

In `showMapView`, find where `mapContent.innerHTML = ...` (or similar) populates the Route view's cards. Replace that body with:

```js
renderConceptPageB2(mapContent, data, concept);
```

If the existing code does additional setup AFTER injecting the HTML (e.g., binds event handlers on now-removed elements), audit and update accordingly. Common: a `bindStartFirstEntry()` call or similar — that handler is now bound inside `renderConceptPageB2` itself, so the outer call becomes redundant. Remove if redundant.

- [ ] **Step 3: Smoke test in browser via Playwright**

Use Playwright to navigate to `http://localhost:8001/`, open a seeded concept (Photosynthesis if present), and verify:

```python
expect(page.locator('.concept-page-b2__entry-title')).to_be_visible()
expect(page.locator('.concept-strip__inner')).to_be_visible()
```

Or via DOM evaluate:

```js
({
  hasStrip: !!document.querySelector('.concept-strip__inner'),
  hasThreshold: !!document.querySelector('.concept-page-b2__threshold'),
  hasEntry: !!document.querySelector('.concept-page-b2__entry-title'),
  hasNearby: !!document.querySelector('.concept-page-b2__nearby-list'),
  ctaText: document.querySelector('.concept-page-b2__entry-cta')?.textContent,
})
```

All four `has*` should be true. CTA text should be `Try from memory` or `Re-drill from memory`.

- [ ] **Step 4: Bump cache-bust on app.js**

In `public/index.html`, bump `app.js?v=84` → `app.js?v=85`.

- [ ] **Step 5: Commit**

```bash
git add public/js/app.js public/index.html
git commit -m "feat(concept-page): wire B-2 renderer; replace card-stack with strip + page"
```

---

## Task 4: Verify both modes + click-through

- [ ] **Step 1: Light-mode visual verify**

Navigate to a concept in light mode. Confirm:
- Concept header renders with title + crystal mark + pills
- Map strip renders with backbone nodes (active highlighted)
- Threshold quote shows the learner's sketch text in italic with the violet left rule
- Active entry block has the H2 + purpose + violet primary CTA "Try from memory →"
- Nearby list at bottom is faint (0.62 opacity), with locked status pills

- [ ] **Step 2: Dark-mode visual verify**

Toggle theme to dark via the existing theme toggle (top of the app shell). Repeat the verify above. Specifically check:
- Body background is graphite (`#18181B`)
- Threshold text is cream at 72% opacity (readable)
- Strip nodes show cyan for primed, lavender at 40% for locked
- The CTA button stays violet (brand primary)
- Hairline rules between nearby items are cream at 14% (visible)

If any element is invisible / wrong-color in dark mode, the dark scope is missing the corresponding override; add it to `concept-page.css` under `[data-theme="dark"] .concept-page-b2 ...`.

- [ ] **Step 3: Click-through verify**

Click the "Try from memory →" button. Expected: the drill chamber opens (`#drill-chamber-view` becomes visible, `#map-view` hides). This proves the existing `startDrillFromMap` path is wired correctly.

Click "Return to map" in the chamber. Expected: chamber closes, B-2 layout restores.

- [ ] **Step 4: Toggle Route/Graph verify**

Click "Graph" in the Route/Graph toggle. Expected: B-2 hides (because `#map-content` becomes `hidden`), `#graph-content` appears with the cytoscape constellation.

Click back to "Route". B-2 returns.

---

## Task 5: Playwright e2e

**Files:** Create `tests/e2e/test_concept_page_b2.py`

- [ ] **Step 1: Write the smoke**

```python
"""End-to-end smoke for the B-2 concept page layout.

Covers: open a concept page; strip, threshold, active entry, and
nearby list all render; click 'Try from memory' opens the chamber.
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


@pytest.fixture
def base_url() -> str:
    return "http://localhost:8001"


def test_b2_layout_renders(page: Page, base_url: str) -> None:
    page.goto(base_url)
    if page.url.endswith("/login"):
        page.locator("#guest-continue-link").click()
    page.locator('aside .concept-item:has-text("Photosynthesis")').first.click()
    expect(page.locator(".concept-strip__inner")).to_be_visible(timeout=8_000)
    expect(page.locator(".concept-page-b2__entry-title")).to_be_visible()
    expect(page.locator(".concept-page-b2__entry-cta")).to_be_visible()
    expect(page.locator(".concept-page-b2__nearby-list")).to_be_visible()


def test_b2_cta_opens_chamber(page: Page, base_url: str) -> None:
    page.goto(base_url)
    if page.url.endswith("/login"):
        page.locator("#guest-continue-link").click()
    page.locator('aside .concept-item:has-text("Photosynthesis")').first.click()
    expect(page.locator(".concept-page-b2__entry-cta")).to_be_visible(timeout=8_000)
    page.locator(".concept-page-b2__entry-cta").click()
    expect(page.locator("#drill-chamber-view")).to_be_visible(timeout=8_000)


def test_b2_route_graph_toggle_preserved(page: Page, base_url: str) -> None:
    page.goto(base_url)
    if page.url.endswith("/login"):
        page.locator("#guest-continue-link").click()
    page.locator('aside .concept-item:has-text("Photosynthesis")').first.click()
    expect(page.locator(".concept-strip__inner")).to_be_visible(timeout=8_000)
    page.locator("#map-mode-graph").click()
    expect(page.locator("#graph-content")).to_be_visible()
    page.locator("#map-mode-study").click()
    expect(page.locator(".concept-strip__inner")).to_be_visible()
```

- [ ] **Step 2: Run the smoke**

```bash
pytest tests/e2e/test_concept_page_b2.py -v
```

Expected: all 3 tests PASS against `localhost:8001`.

If any fail, fix the implementation (NOT the test), then re-run.

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/test_concept_page_b2.py
git commit -m "test(e2e): B-2 concept page layout -- strip, CTA, toggle"
```

---

## Task 6: Coverage gate + push + update PR

- [ ] **Step 1: Coverage gate**

```bash
./scripts/check-coverage.sh
```

If exit 0: proceed. If non-zero, document the failure in the PR body update (likely the same worktree-vs-main issue documented in the chamber port).

- [ ] **Step 2: Push**

```bash
git push origin feat/drill-chamber-port
```

- [ ] **Step 3: Update PR description**

The PR (#236) is already open. Append a section to the body via `gh pr edit`:

```bash
gh pr edit 236 --body-file - <<'EOF'
[append the existing body, then add a new section]

## Concept page B-2 port (added 2026-05-11)

Replaces the previous Route view card-stack with the founder-approved
"B-2 Strip + page" layout from the lab prototype. Synthesizes Linear
+ Heptabase + Notion idioms into a single-document concept page:

- Sticky map strip at top (110px, real backbone data, active node highlighted)
- Threshold quote in italic with violet left rule (the "we saw what you wrote" moment)
- Active entry block: large H2 + purpose + primary CTA "Try from memory →"
- Faint locked nearby-entries list at bottom (0.62 opacity, reads as legend)
- Re-edit sketch affordance per Jordan/Gemini's request

Light mode is canonical; dark mode supported. Route/Graph toggle preserved.

Customer feedback (Jordan/Gemini ADHD persona): positive on all four
core moments. Quote: "It feels like the rest of the building is dark
and only the room I'm in has the lights on."

Lab artifact at public/_lab/concept-page-iterations.html (force-added
past .git/info/exclude).
EOF
```

OR if appending is awkward, just add the new section and let the existing body stand:

```bash
gh pr view 236 --json body --jq .body > /tmp/pr-body.txt
echo "" >> /tmp/pr-body.txt
echo "## Concept page B-2 port (added 2026-05-11)" >> /tmp/pr-body.txt
# ... append rest as above ...
gh pr edit 236 --body-file /tmp/pr-body.txt
```

---

## Self-review

**Spec coverage:**
- ✓ Acceptance #1 (layout): Tasks 2, 3
- ✓ Acceptance #2 (light + dark): Tasks 2, 4
- ✓ Acceptance #3 (threshold text): Task 3
- ✓ Acceptance #4 (real LLM titles, not placeholders): Task 3 (renderConceptPageB2 uses `node.label`)
- ✓ Acceptance #5 (CTA opens chamber): Task 3 (wires startDrillFromMap)
- ✓ Acceptance #6 (toggle preserved): Task 4
- ✓ Acceptance #7 (coverage gate): Task 6
- ✓ Acceptance #8 (e2e): Task 5

**Open question for the executor:** Where is the learner's threshold sketch text actually stored? The plan defaults to `concept.threshold` then falls back to `data.metadata.core_thesis`. If the actual field name is different, swap the fallback chain in renderConceptPageB2 Step 1. Use `grep -rn "threshold" public/js/app.js` to find the right field if needed.

**Out of scope for this plan:**
- Auto-scrolling the active entry into view (Gemini's flagged mitigation from the button-removal commit) — separate plan
- Strip interactivity (clicking a node to swap the active entry) — v1 reads as orientation only
- Editing the threshold (the affordance exists; the actual route is left unwired with a console hint for v1.1)
