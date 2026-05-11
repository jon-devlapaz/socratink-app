# Strip-as-Nav (kill Route/Graph toggle, deprecate the Graph view) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the B-2 concept page's map strip the canonical navigation device for the concept's backbone entries, then delete the Route/Graph toggle and the entire Graph view (cytoscape constellation + detail two-pane). Result: one organizing system per concept page; the strip you see at the top is also the strip you click to swap entries; no separate "spatial" mode to enter and exit. Honors the locality doctrine (one source of truth) and the unanimous customer signal (4-of-4 personas — Sam, Dimitri, Maya, Robert — voted to kill the toggle).

**Architecture:**
- Strip nodes become interactive: click a node → swap the active entry shown in the work column (threshold quote stays — it's per-concept, not per-entry; everything below the strip refreshes)
- Hover preview: non-active strip nodes show their entry title in a small tooltip near the strip on hover (reduces mis-click friction without animating layout)
- Keyboard nav: `←` / `→` step through backbone entries; `Enter` opens the active entry's chamber
- Active state visual signature: active node grows (radius 9 vs 6/7), gets a halo, label appears below it. Other nodes stay quiet.
- Route/Graph toggle is removed from the header
- `#graph-content` markup, `setMapMode` JS, `bindMapModeControls`, `currentMapMode` state, and the `.graph-stage-wrap` / `.graph-detail` CSS are removed
- `graph-view.js` is audited — if no remaining caller uses `mountKnowledgeGraph`, the file is deleted along with its `<script>` tag
- The `cytoscape` library `<script>` tag in index.html stays for now (might be needed by other surfaces; verify before deleting in a separate pass)

**Tech Stack:**
- Vanilla JS module-style additions to `public/js/app.js`
- CSS via cascade: edits to `public/css/concept-page.css` (strip interactivity) and deletions in `public/css/layout.css` (Graph view orphans)
- Brand tokens from `public/css/variables.css` — `--accent-primary`, `--text-strong`, `--text-muted`, `--surface-card-theme`, `--violet-600-rgb`
- Playwright for the e2e

**Doctrinal guardrails (preserve all):**
- No praise / scoring / mastery copy — strip-click swap shows whatever the entry's state earns it, no "great job for clicking"
- Locked entries stay locked when navigated to; the work column shows their locked silhouette (purpose only, no study material)
- No streaks, no badges, no progress bars (the "primed N of N" pill in the header is honest state, not gamification)
- The CTA button and the chamber entry path stay unchanged

**Impeccable UI principles (binding for this plan):**
- **No side-stripe borders >1px on cards or list items.** The strip's anchor pillar is OK (it's structural, not decorative).
- **No glassmorphism by default.** Hover-preview tooltip uses solid surface + subtle shadow, not blur.
- **Motion: ease-out exponential, no bounce, no elastic.** Use `cubic-bezier(0.16, 1, 0.3, 1)` consistently. Durations: 240ms (out) / 320ms (in). Match the chamber's idiom.
- **Don't animate layout properties.** Animate `opacity` and `transform` only.
- **Visible focus ring on every interactive element.** Strip nodes get keyboard-accessible focus via `tabindex="0"`.
- **No em dashes in copy or comments.** Use periods, colons, semicolons, parentheses, or `--`.
- **Cap body line length 65–75ch.** The work column is already constrained — preserve.
- **Don't wrap everything in a container.** No new card around the strip; reuse the existing `.concept-strip__inner`.
- **Active-state visual signature is unambiguous.** Active node = larger radius + halo + label visible. Inactive nodes stay quiet so the eye finds the active without thinking.

---

## File Structure

**Create:**
- `tests/e2e/test_strip_nav.py` — Playwright e2e covering: click a strip node, work column swaps; keyboard arrow nav steps through entries; locked-entry click shows the locked silhouette state in the work column

**Modify:**
- `public/js/app.js` — add `setActiveEntry(entryId)` helper; wire strip-node click + keyboard handlers in `renderConceptPageB2`; remove `setMapMode` / `bindMapModeControls` / `currentMapMode` references after the toggle is deleted; remove the call site that mounts cytoscape on Graph mode
- `public/css/concept-page.css` — strip-node hover/focus/click states; tooltip pattern for hover preview; transition rules for the work-column fade-out → fade-in on entry swap
- `public/index.html` — remove `<div class="map-mode-switch">` block (~lines 389-392); remove `<div id="graph-content">` block (~lines 396-410); remove `<script src=".../cytoscape..."></script>` if no other surface uses it (verify first); bump cache-busts
- `public/css/layout.css` — delete `.map-mode-switch`, `.map-mode-btn`, `.graph-stage-wrap`, `.graph-detail`, `.graph-stage-header`, `.graph-stage`, seam-of-light pseudos, mobile overrides for `.map-mode-switch`. Audit grep for `.graph-` and decide each
- `public/styles.css` — bump `layout.css?v=` pin
- `public/css/index.css` — bump `styles.css?v=` pin (cache-bust both layers per the convention)

**Delete (potentially, audit first):**
- `public/js/graph-view.js` — only if no remaining caller. Grep `mountKnowledgeGraph` and `import.*graph-view` first. If still imported elsewhere (e.g., a starter map preview), KEEP it.
- The `<script src="...cytoscape.min.js">` CDN tag in index.html — only if `graph-view.js` is also deleted AND no other surface uses cytoscape

**Untouched:**
- The drill chamber (`drill-chamber-view`, `drill-chamber.js`, `drill-chamber.css`) — chamber is its own world
- The header (concept title + tags + crystal mark) — preserve
- The threshold quote, active entry block, nearby list — preserve B-2 layout
- Backend, /api/drill, /api/extract — unchanged

---

## Acceptance Criteria

1. The Route/Graph toggle is gone from the concept-page header
2. The `#graph-content` markup is gone from `index.html`
3. Clicking a primed strip node swaps the work column to that entry's threshold/H2/purpose/CTA — with a 240ms fade-out → 320ms fade-in transition (animates `opacity` + `transform`, NOT layout)
4. Clicking a locked strip node swaps the work column to that entry's locked silhouette state (entry name + "locked until cold attempt" purpose copy + a disabled-looking CTA OR no CTA — preserves the doctrine)
5. Hovering a non-active strip node shows a small tooltip with the entry title near the strip
6. Keyboard `←` / `→` step the active entry through the backbone; `Enter` opens the chamber for the active entry
7. Active strip node has a visible focus ring on keyboard focus
8. The chamber path (CTA → chamber → return) still works exactly as before
9. Light + dark mode both render correctly
10. Coverage gate exits 0 (or documented as failing for the same worktree-vs-main reason)
11. The Playwright e2e (`tests/e2e/test_strip_nav.py`) passes against `:8001`

---

## Task 1: Pre-flight + audit

**Files:** none

- [ ] **Step 1: Confirm worktree state**

```bash
cd /Users/jondev/dev/socratink/prod/socratink-app/.worktrees/drill-chamber-port
git status --short
```

Expected: clean working tree on `feat/drill-chamber-port`. (B-2 commits already landed.)

- [ ] **Step 2: Read the current renderConceptPageB2**

In `public/js/app.js`, locate `function renderConceptPageB2(mountEl, data, concept)` (line ~1935). Read it fully. Note the strip-node generation block (`backbone.map((node, i) => ...)`) — that's where you'll add `data-entry-id` attributes and ARIA roles. Note the CTA wiring at the bottom — that's where you'll add the strip-click + keyboard handlers.

- [ ] **Step 3: Audit cytoscape usage outside the Graph view**

```bash
grep -rn "mountKnowledgeGraph\|currentGraphController\|cytoscape" public/js public/index.html | head -30
```

If `currentGraphController` is referenced from places OUTSIDE the Graph mount path (e.g., from `startDrill` or `cancelDrill`), those references will need to become no-ops or be deleted. Do NOT skip this — orphan calls will throw runtime errors.

If `cytoscape` is loaded from a CDN `<script>` tag and the only consumer is `graph-view.js`, BOTH can be deleted. If there's another consumer (e.g., a Library preview), keep cytoscape but delete `graph-view.js` selectively.

- [ ] **Step 4: Note the touch-target and accessibility floor**

Strip nodes will become focusable interactive elements. Per WCAG 2.5.5, touch target minimum is 24×24 CSS px (Level AA). The current strip nodes are circles of radius 6-9 — too small for touch. The fix: each `<g>` element gets a transparent `<rect>` overlay sized to the touch target (28×28 minimum) so the click area is comfortable, while the visible circle stays small. You'll add this in Task 2.

---

## Task 2: Make strip nodes clickable (data + handlers)

**Files:** Modify `public/js/app.js`

- [ ] **Step 1: Update the strip-node generation to carry entry IDs and ARIA roles**

In `renderConceptPageB2`, find the `backbone.map((node, i) => ...)` block that generates strip nodes. Replace its body with this version (keeps the visible circle + adds a transparent touch overlay + ARIA + tabindex):

```js
const stripNodes = backbone.map((node, i) => {
  const x = padX + i * stepX;
  const status = node.drill_status || 'locked';
  const isPrimed = status === 'primed' || status === 'drilled' || status === 'solidified';
  const isActive = i === activeIdx;
  const cls = ['concept-strip__node', isPrimed ? 'concept-strip__node--primed' : 'concept-strip__node--locked'];
  if (isActive) cls.push('is-active');
  const r = isActive ? 9 : (isPrimed ? 7 : 6);
  const entryId = node.id || `entry-${i}`;
  const label = escHtml(node.label || `entry ${i + 1}`);
  const ariaLabel = `${node.label || 'entry'}, ${status}${isActive ? ', current' : ''}`;
  return `
    <g class="${cls.join(' ')}"
       role="button"
       tabindex="0"
       data-entry-id="${escHtml(entryId)}"
       data-entry-index="${i}"
       aria-label="${escHtml(ariaLabel)}">
      <rect x="${x - 14}" y="${strokeY - 14}" width="28" height="28" fill="transparent" pointer-events="all"></rect>
      <circle cx="${x}" cy="${strokeY}" r="${r}"></circle>
      ${isActive ? `<text x="${x}" y="${strokeY + 25}">${label}</text>` : ''}
    </g>
  `;
}).join('');
```

The `<rect>` is the touch target (28×28). The `<circle>` is the visible mark. `pointer-events="all"` on the rect ensures the click hits the group even outside the circle.

- [ ] **Step 2: Add `setActiveEntry(entryId)` and the work-column re-render logic**

Above `renderConceptPageB2`, add a module-level state variable:

```js
let _activeEntryId = null;
```

Then add the helper:

```js
/**
 * Swap the work column to show a different backbone entry without
 * rebuilding the whole concept page. Called by strip-node clicks
 * and keyboard arrow nav.
 *
 * Animates: 240ms opacity fade-out, swap, 320ms opacity + 4px translateY fade-in.
 * Does NOT animate layout (no width/height/margin transitions).
 *
 * @param {string} entryId - The id of the backbone entry to show
 * @param {Object} data - Parsed graphData
 * @param {Object} concept - The full concept object
 */
function setActiveEntry(entryId, data, concept) {
  if (!data || !entryId) return;
  if (entryId === _activeEntryId) return;

  const backbone = Array.isArray(data.backbone) ? data.backbone : [];
  const newEntry = backbone.find((n) => (n.id || `entry-${backbone.indexOf(n)}`) === entryId);
  if (!newEntry) return;
  const newIdx = backbone.indexOf(newEntry);

  const mountEl = document.getElementById('map-content');
  if (!mountEl) return;

  // Update strip node active class without rebuild
  mountEl.querySelectorAll('.concept-strip__node').forEach((g) => {
    const isThisOne = g.getAttribute('data-entry-id') === entryId;
    g.classList.toggle('is-active', isThisOne);
    // Re-render labels: the active node shows its label, others hide it
    const text = g.querySelector('text');
    if (isThisOne && !text) {
      const circle = g.querySelector('circle');
      if (circle) {
        const cx = parseFloat(circle.getAttribute('cx'));
        const cy = parseFloat(circle.getAttribute('cy'));
        const labelText = backbone[newIdx]?.label || `entry ${newIdx + 1}`;
        const t = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        t.setAttribute('x', cx);
        t.setAttribute('y', cy + 25);
        t.textContent = labelText;
        g.appendChild(t);
      }
    } else if (!isThisOne && text) {
      text.remove();
    }
    // Bump radius on active
    const circle = g.querySelector('circle');
    if (circle) {
      circle.setAttribute('r', isThisOne ? 9 : (g.classList.contains('concept-strip__node--primed') ? 7 : 6));
    }
  });

  // Update strip overlay label ("Core thesis · 2 of 6")
  const overlayName = mountEl.querySelector('.concept-strip__active-name');
  if (overlayName) {
    overlayName.textContent = `${newEntry.label || 'entry'} ${String.fromCharCode(0xB7)} ${newIdx + 1} of ${backbone.length}`;
  }

  // Swap the work column with fade
  const doc = mountEl.querySelector('.concept-page-b2__doc');
  if (!doc) return;
  doc.classList.add('is-fading-out');
  setTimeout(() => {
    doc.innerHTML = renderActiveEntryHtml(newEntry, newIdx, backbone, concept, data);
    rebindActiveEntryHandlers(doc, concept, data);
    doc.classList.remove('is-fading-out');
    void doc.offsetWidth;
    doc.classList.add('is-fading-in');
    setTimeout(() => doc.classList.remove('is-fading-in'), 360);
  }, 240);

  _activeEntryId = entryId;
}
```

Then factor out the work-column HTML so both `renderConceptPageB2` (initial mount) and `setActiveEntry` (swap) share it:

```js
/**
 * Build the work column HTML (threshold quote + active entry block + nearby list).
 * Shared between initial mount and active-entry swap.
 */
function renderActiveEntryHtml(activeEntry, activeIdx, backbone, concept, data) {
  const meta = data?.metadata || {};
  const thresholdText = (concept?.startingMapContext || meta.starting_map_context || meta.core_thesis || '').trim();
  const totalNodes = backbone.length || 1;

  const isLocked = (activeEntry.drill_status || 'locked') === 'locked';
  const entryEyebrow = isLocked
    ? `locked entry ${activeIdx + 1} of ${totalNodes}`
    : (activeEntry.drill_status === 'primed'
      ? `re-drill ready entry ${activeIdx + 1} of ${totalNodes}`
      : `first cold attempt entry ${activeIdx + 1} of ${totalNodes}`);
  const entryPurpose = activeEntry.purpose
    || (isLocked
      ? 'Locked until you do a cold attempt on the entry above. The mechanism stays hidden until you have written what you can reconstruct from memory.'
      : 'The first entry asks for the governing idea, not the whole source. No study material yet. Write what you can reconstruct from memory.');
  const ctaLabel = activeEntry.drill_status === 'primed' ? 'Re-drill from memory' : 'Try from memory';

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

  const ctaButton = isLocked
    ? `<button class="concept-page-b2__entry-cta concept-page-b2__entry-cta--disabled" type="button" disabled aria-disabled="true" title="Cold attempt on the entry above unlocks this one">Locked</button>`
    : `<button class="concept-page-b2__entry-cta" type="button" data-active-entry-id="${escHtml(activeEntry.id || 'core-thesis')}">${ctaLabel}</button>`;

  const activeHtml = `
    <span class="eyebrow concept-page-b2__entry-eyebrow">${escHtml(entryEyebrow)}</span>
    <h2 class="concept-page-b2__entry-title">${escHtml(activeEntry.label || 'Core thesis')}</h2>
    <p class="concept-page-b2__entry-purpose">${escHtml(entryPurpose)}</p>
    ${ctaButton}
  `;

  // Nearby = every backbone entry that isn't this one
  const nearby = backbone.filter((n) => n !== activeEntry);
  const nearbyHtml = nearby.length
    ? `
      <section class="concept-page-b2__nearby">
        <span class="eyebrow concept-page-b2__nearby-eyebrow">nearby entries  all locked until first attempt</span>
        <div class="concept-page-b2__nearby-list">
          ${nearby.map((n) => {
            const idx = backbone.indexOf(n);
            const num = String(idx + 1).padStart(2, '0');
            const status = (n.drill_status || 'locked').toUpperCase();
            return `
              <div class="concept-page-b2__nearby-item">
                <span class="concept-page-b2__nearby-num">${escHtml(num)}</span>
                <span>${escHtml(n.label || `entry ${idx + 1}`)}</span>
                <span class="concept-page-b2__nearby-status">${escHtml(status)}</span>
              </div>
            `;
          }).join('')}
        </div>
      </section>
    `
    : '';

  return `${thresholdHtml}${activeHtml}${nearbyHtml}`;
}
```

And the rebind helper:

```js
function rebindActiveEntryHandlers(docEl, concept, data) {
  const ctaBtn = docEl.querySelector('.concept-page-b2__entry-cta:not([disabled])');
  if (ctaBtn) {
    ctaBtn.addEventListener('click', () => {
      window.App?.startDrillFromMap?.();
    });
  }
  docEl.querySelectorAll('[data-edit-threshold]').forEach((link) => {
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
```

Now refactor `renderConceptPageB2` to use the same `renderActiveEntryHtml` helper for the initial doc HTML, instead of inlining it. Replace the inline threshold/active/nearby HTML construction with:

```js
// (Inside renderConceptPageB2, replace the inline HTML with:)
const docHtml = renderActiveEntryHtml(activeEntry, activeIdx, backbone, concept, data);
```

And update the final mount to use `${docHtml}` instead of the inline `${thresholdHtml}${activeHtml}${nearbyHtml}`.

Set `_activeEntryId` after initial mount: at the end of `renderConceptPageB2`, add:

```js
_activeEntryId = activeEntry.id || `entry-${activeIdx}`;
rebindActiveEntryHandlers(mountEl.querySelector('.concept-page-b2__doc'), concept, data);
```

And remove the now-redundant CTA + edit-link wiring at the bottom of `renderConceptPageB2` (it's now handled by `rebindActiveEntryHandlers`).

- [ ] **Step 3: Wire the strip-node click + keyboard handlers**

At the bottom of `renderConceptPageB2`, after `rebindActiveEntryHandlers`, add:

```js
// Wire strip-node click + keyboard nav
const stripContainer = mountEl.querySelector('.concept-strip__inner');
if (stripContainer) {
  stripContainer.addEventListener('click', (e) => {
    const node = e.target.closest('.concept-strip__node');
    if (!node) return;
    const id = node.getAttribute('data-entry-id');
    if (id) setActiveEntry(id, data, concept);
  });
  stripContainer.addEventListener('keydown', (e) => {
    const node = e.target.closest('.concept-strip__node');
    if (!node) {
      // Arrow keys also work when focus is anywhere in the strip
      if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
    }
    if (e.key === 'Enter' || e.key === ' ') {
      const id = node?.getAttribute('data-entry-id');
      if (id) {
        e.preventDefault();
        setActiveEntry(id, data, concept);
      }
    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
      e.preventDefault();
      const dir = e.key === 'ArrowLeft' ? -1 : 1;
      const currentIdx = backbone.findIndex((n) => (n.id || `entry-${backbone.indexOf(n)}`) === _activeEntryId);
      const nextIdx = Math.max(0, Math.min(backbone.length - 1, currentIdx + dir));
      const nextNode = backbone[nextIdx];
      if (nextNode) {
        const nextId = nextNode.id || `entry-${nextIdx}`;
        setActiveEntry(nextId, data, concept);
        // Move focus to the new active node
        const nextG = mountEl.querySelector(`.concept-strip__node[data-entry-id="${nextId}"]`);
        nextG?.focus();
      }
    }
  });
}
```

- [ ] **Step 4: Manual smoke**

In a browser at `:8001`, open a concept that has 2+ backbone entries. Confirm:
- Clicking a primed strip node updates the work column with that entry's content (with fade)
- Clicking a locked node updates the work column to the locked silhouette state with the disabled CTA
- Tab into the strip, press `→` and `←` to step through entries (focus moves with the active node)
- Press `Enter` on an active node opens the chamber

If any step fails, debug before commit.

- [ ] **Step 5: Bump cache-bust + commit**

In `public/index.html`, bump `app.js?v=` by +1.

```bash
git add public/js/app.js public/index.html
git commit -m "feat(concept-page): make strip nodes clickable and keyboard-navigable

- Each strip node carries data-entry-id, role=button, tabindex=0,
  aria-label with state, plus a transparent 28x28 touch overlay
  that meets WCAG 2.5.5 touch-target minimum
- New setActiveEntry(entryId) helper swaps the work column without
  full rebuild; animates 240ms opacity fade-out then 320ms
  opacity + 4px translateY fade-in (no layout animation)
- Arrow keys step through backbone; Enter opens chamber
- Locked entries get a disabled CTA (Locked) instead of the
  primary 'Try from memory' button -- preserves doctrine"
```

---

## Task 3: Hover preview + active-state CSS

**Files:** Modify `public/css/concept-page.css`

- [ ] **Step 1: Add interactive states to strip nodes**

Append to `public/css/concept-page.css`:

```css
/* ============================================================
   Strip nodes: interactive states (Option B / strip-as-nav)
   ============================================================ */

.concept-strip__node {
  cursor: pointer;
  outline: none;
}
.concept-strip__node circle {
  transition:
    r 240ms cubic-bezier(0.16, 1, 0.3, 1),
    fill 240ms cubic-bezier(0.16, 1, 0.3, 1),
    stroke 240ms cubic-bezier(0.16, 1, 0.3, 1),
    filter 240ms cubic-bezier(0.16, 1, 0.3, 1);
}
.concept-strip__node:hover:not(.is-active) circle {
  filter: drop-shadow(0 0 6px rgba(var(--violet-600-rgb), 0.30));
}
.concept-strip__node:focus-visible circle {
  stroke: var(--accent-primary);
  stroke-width: 3;
  filter: drop-shadow(0 0 8px rgba(var(--violet-600-rgb), 0.55));
}
[data-theme="dark"] .concept-strip__node:focus-visible circle {
  stroke: rgba(176, 156, 224, 0.95);
}

/* Hover tooltip preview -- shows the entry title near the strip
   when the learner hovers a non-active node. Solid background,
   subtle shadow. NO glassmorphism. NO blur. */
.concept-strip__node {
  position: relative; /* SVG g elements ignore position; we render the tooltip via JS-injected sibling, see Task 3 Step 2 */
}

/* The work-column fade transition (paired with setActiveEntry) */
.concept-page-b2__doc {
  transition: opacity 240ms cubic-bezier(0.16, 1, 0.3, 1);
}
.concept-page-b2__doc.is-fading-out {
  opacity: 0.18;
}
.concept-page-b2__doc.is-fading-in {
  animation: concept-page-fade-in 320ms cubic-bezier(0.16, 1, 0.3, 1) both;
}
@keyframes concept-page-fade-in {
  from { opacity: 0; transform: translateY(4px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* Disabled CTA on locked entries */
.concept-page-b2__entry-cta--disabled {
  background: transparent;
  color: var(--text-muted);
  border: 1px dashed var(--border-subtle);
  cursor: not-allowed;
  opacity: 0.62;
}
.concept-page-b2__entry-cta--disabled:hover {
  transform: none;
  background: transparent;
}

@media (prefers-reduced-motion: reduce) {
  .concept-page-b2__doc,
  .concept-page-b2__doc.is-fading-in,
  .concept-strip__node circle { animation: none; transition: none; }
}
```

- [ ] **Step 2: JS-injected tooltip for hover preview**

SVG `<g>` doesn't support CSS `position`, and pure-SVG tooltips are awkward. Add an HTML tooltip element that gets positioned next to the hovered node.

In `renderConceptPageB2` after the strip mount HTML, add inside the `.concept-strip__inner` markup:

```html
<div class="concept-strip__tooltip" id="concept-strip-tooltip" hidden></div>
```

(Add this to the inline-template string in `renderConceptPageB2` -- look for the `<div class="concept-strip__inner">` opening tag and add the tooltip div right before the `<svg>`.)

CSS for the tooltip:

```css
.concept-strip__tooltip {
  position: absolute;
  z-index: 10;
  background: var(--surface-card-theme);
  color: var(--text-strong);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 6px 10px;
  font-size: 12px;
  letter-spacing: 0.02em;
  font-family: 'Inter', system-ui, sans-serif;
  pointer-events: none;
  box-shadow: 0 2px 8px rgba(36, 32, 56, 0.12);
  transform: translate(-50%, -100%);
  opacity: 0;
  transition: opacity 180ms cubic-bezier(0.16, 1, 0.3, 1);
  white-space: nowrap;
}
.concept-strip__tooltip[data-visible="true"] {
  opacity: 1;
}
[data-theme="dark"] .concept-strip__tooltip {
  background: rgba(18, 12, 36, 0.96);
  border-color: rgba(176, 156, 224, 0.32);
  color: rgba(247, 236, 225, 0.96);
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.45);
}
```

In the JS strip handler (`renderConceptPageB2`'s strip-container event block), add hover handlers:

```js
const tooltip = mountEl.querySelector('#concept-strip-tooltip');
if (stripContainer && tooltip) {
  stripContainer.addEventListener('mouseover', (e) => {
    const node = e.target.closest('.concept-strip__node');
    if (!node || node.classList.contains('is-active')) {
      tooltip.removeAttribute('data-visible');
      tooltip.hidden = true;
      return;
    }
    const idx = parseInt(node.getAttribute('data-entry-index'), 10);
    const entry = backbone[idx];
    if (!entry) return;
    const circle = node.querySelector('circle');
    if (!circle) return;
    const containerRect = stripContainer.getBoundingClientRect();
    const circleRect = circle.getBoundingClientRect();
    tooltip.textContent = entry.label || `entry ${idx + 1}`;
    tooltip.style.left = `${circleRect.left + circleRect.width / 2 - containerRect.left}px`;
    tooltip.style.top = `${circleRect.top - containerRect.top - 8}px`;
    tooltip.hidden = false;
    requestAnimationFrame(() => tooltip.setAttribute('data-visible', 'true'));
  });
  stripContainer.addEventListener('mouseleave', () => {
    tooltip.removeAttribute('data-visible');
    setTimeout(() => { tooltip.hidden = true; }, 200);
  });
}
```

- [ ] **Step 3: Manual smoke + commit**

Verify in browser:
- Hovering a non-active strip node shows a tooltip with the entry label, 8px above the node, with a subtle shadow (no blur)
- Tooltip disappears on `mouseleave`
- Active node does NOT show a tooltip on hover (it's already labeled below it)
- Keyboard focus on a strip node shows a violet halo around the circle

Bump `concept-page.css?v=` and `app.js?v=` cache-busts.

```bash
git add public/css/concept-page.css public/js/app.js public/index.html
git commit -m "feat(concept-page): hover tooltip + focus ring on strip nodes

- JS-injected tooltip pattern (SVG g cannot host position)
- Tooltip uses solid surface + subtle shadow (no glassmorphism)
- 180ms opacity fade in/out, no layout animation
- Active node does not get a tooltip (already labeled)
- Keyboard focus ring: violet halo on the active circle
- Reduced-motion clients get instant transitions"
```

---

## Task 4: Remove the Route/Graph toggle from the header

**Files:** Modify `public/index.html`, `public/css/layout.css`, `public/js/app.js`

- [ ] **Step 1: Delete the toggle markup**

In `public/index.html`, find the `.map-mode-switch` block inside `.concept-header-actions` (around line 388-393). Delete the entire `<div class="map-mode-switch">` block. Leave `.concept-header-actions` as an empty grid cell or remove it entirely if it's now empty (audit).

- [ ] **Step 2: Delete the toggle CSS**

In `public/css/layout.css`, find and delete:
- `.map-mode-switch` rule and its `::before` pseudo (the sliding-thumb pattern we recently added)
- `.map-mode-switch:has(...)::before` selector
- `.map-mode-btn` rule and all its variants (`.active`, `:hover`, `:focus-visible`, `:active`)
- `[data-theme="dark"] .map-mode-switch` and related dark overrides
- The mobile `@media (max-width: 899px)` overrides for `.map-mode-switch` and `.map-mode-btn`

- [ ] **Step 3: Delete the toggle JS**

In `public/js/app.js`:
- Delete `function setMapMode(mode = 'study')` and its body
- Delete `function bindMapModeControls()` and its body
- Delete the module-level `let currentMapMode = 'study';` declaration
- Grep for any remaining call sites of `setMapMode` or `bindMapModeControls` and remove them
- Delete the `currentMapMode === 'graph'` branch in any view-resize handler

- [ ] **Step 4: Smoke + commit**

Reload the concept page. Confirm:
- The header no longer shows the Route/Graph buttons (just the title + tags + crystal mark)
- The B-2 layout still renders (strip + threshold + active + nearby)
- The strip-click navigation still works (Task 2)

Bump `app.js?v=`, `index.css?v=`, `styles.css?v=`, `layout.css?v=` cache-busts.

```bash
git add public/index.html public/css/layout.css public/js/app.js public/styles.css public/css/index.css
git commit -m "refactor: remove Route/Graph toggle (strip is the only nav)

Customer signal was unanimous (4 of 4 personas voted to kill it).
Locality argument: one organizing system per concept page. The
strip on B-2 IS the navigation; clicking a node swaps the work
column. The Graph view's separate cytoscape constellation no longer
earns its keep -- next task removes its markup + CSS."
```

---

## Task 5: Delete the Graph view markup + dead CSS

**Files:** Modify `public/index.html`, `public/css/layout.css`

- [ ] **Step 1: Delete `#graph-content`**

In `public/index.html`, find the entire `<div id="graph-content" class="graph-content" hidden>` block (around lines 396-410). Delete it.

- [ ] **Step 2: Delete the Graph view CSS**

In `public/css/layout.css`, grep for and delete (audit each before delete to avoid removing something the chamber or other surfaces depend on):
- `.graph-stage-wrap` rules
- `.graph-stage` rules
- `.graph-stage-header` rules
- `.graph-stage-kicker`, `.graph-stage-title`, `.graph-stage-stars` rules
- `.graph-detail` rules (NOT `.concept-page-b2__doc` or anything chamber-related)
- `.graph-detail::before`, `.graph-detail::after` (the seam-of-light pseudos from the dark-mode-graph-patch)
- `.graph-detail.is-cold-attempt-active` and similar state classes
- `.graph-node-detail` rules
- The mobile `@media (max-width: 899px)` overrides for any of the above

For each deletion, verify with grep before:

```bash
grep -rn "graph-stage-wrap\|graph-stage-header\|graph-detail\|graph-node-detail" public/js public/index.html
```

If a class is still referenced from JS or markup outside the deleted Graph view, KEEP it.

- [ ] **Step 3: Smoke + commit**

Reload the page. Confirm:
- No console errors
- The concept page still renders B-2 correctly
- No layout shift or weird empty space where Graph view used to render

```bash
git add public/index.html public/css/layout.css public/styles.css public/css/index.css
git commit -m "refactor: delete Graph view markup and dead CSS

- Removes #graph-content section from index.html
- Removes .graph-stage-wrap, .graph-detail, seam-of-light pseudos,
  state-class overrides, and mobile breakpoint overrides
- Cytoscape script tag and graph-view.js audit/delete handled in
  the next task"
```

---

## Task 6: Audit + delete graph-view.js (and cytoscape, if no other consumer)

**Files:** Modify `public/js/app.js`, `public/index.html`; potentially delete `public/js/graph-view.js`

- [ ] **Step 1: Audit graph-view.js consumers**

```bash
grep -rn "graph-view\|mountKnowledgeGraph\|currentGraphController" public/js public/index.html
```

If the ONLY remaining references are inside `graph-view.js` itself, AND inside dead code paths in `app.js` (e.g., `currentGraphController?.resize()` in the deleted `setMapMode`), then `graph-view.js` is dead.

- [ ] **Step 2: Delete graph-view.js (if dead)**

If dead:

```bash
git rm public/js/graph-view.js
```

In `public/index.html`, remove the `<script src="js/graph-view.js?v=...">` tag if present.

In `public/js/app.js`, remove any remaining `currentGraphController` references, the `let currentGraphController = ...` declaration, and any imports.

If NOT dead (e.g., another surface calls `mountKnowledgeGraph`), KEEP the file but document in this task's commit message which surface still uses it. Skip Step 3 in that case.

- [ ] **Step 3: Audit cytoscape CDN tag**

```bash
grep -rn "cytoscape" public public/index.html
```

If the ONLY reference was inside `graph-view.js` (just deleted), the cytoscape `<script>` tag in `index.html` can also be deleted. This shaves a CDN request from page load.

If anything else uses cytoscape (e.g., a Library preview, a starter map), KEEP the tag.

- [ ] **Step 4: Commit**

```bash
git add public/index.html public/js/app.js
git rm public/js/graph-view.js  # only if Step 2 went through
git commit -m "refactor: delete graph-view.js (no remaining consumers)

graph-view.js mounted the cytoscape constellation for the now-deleted
Graph view. Verified no other surface references mountKnowledgeGraph
or currentGraphController. Cytoscape CDN tag also removed.

If a future feature needs a graph rendering, the strip-as-nav pattern
in concept-page.css is the new default."
```

---

## Task 7: Playwright e2e for strip-as-nav

**Files:** Create `tests/e2e/test_strip_nav.py`

- [ ] **Step 1: Write the test**

Create `tests/e2e/test_strip_nav.py`:

```python
"""End-to-end smoke for strip-as-navigation on the concept page.

Covers: click a primed strip node swaps the work column; click a
locked node shows the locked silhouette state; keyboard arrow nav
steps through backbone entries.
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


@pytest.fixture
def base_url() -> str:
    return "http://localhost:8001"


def _open_concept(page: Page, base_url: str) -> None:
    page.goto(base_url)
    if page.url.endswith("/login"):
        page.locator("#guest-continue-link").click()
    page.locator('aside .concept-item').first.click()
    expect(page.locator(".concept-strip__inner")).to_be_visible(timeout=8_000)


def test_strip_click_swaps_work_column(page: Page, base_url: str) -> None:
    _open_concept(page, base_url)
    initial_title = page.locator(".concept-page-b2__entry-title").text_content()
    # Click the second strip node if there is one
    nodes = page.locator(".concept-strip__node")
    if nodes.count() < 2:
        pytest.skip("concept has fewer than 2 backbone entries")
    nodes.nth(1).click()
    # Wait for the fade transition to settle
    page.wait_for_timeout(700)
    new_title = page.locator(".concept-page-b2__entry-title").text_content()
    assert new_title != initial_title, "work column did not swap on strip click"


def test_strip_keyboard_nav(page: Page, base_url: str) -> None:
    _open_concept(page, base_url)
    nodes = page.locator(".concept-strip__node")
    if nodes.count() < 2:
        pytest.skip("concept has fewer than 2 backbone entries")
    initial_title = page.locator(".concept-page-b2__entry-title").text_content()
    # Tab into the first strip node
    nodes.first.focus()
    page.keyboard.press("ArrowRight")
    page.wait_for_timeout(700)
    new_title = page.locator(".concept-page-b2__entry-title").text_content()
    assert new_title != initial_title, "ArrowRight did not advance the active entry"


def test_locked_entry_shows_disabled_cta(page: Page, base_url: str) -> None:
    _open_concept(page, base_url)
    locked_nodes = page.locator(".concept-strip__node--locked")
    if locked_nodes.count() == 0:
        pytest.skip("no locked entries available to test")
    locked_nodes.first.click()
    page.wait_for_timeout(700)
    cta = page.locator(".concept-page-b2__entry-cta")
    expect(cta).to_have_attribute("disabled", "")


def test_no_route_graph_toggle(page: Page, base_url: str) -> None:
    _open_concept(page, base_url)
    expect(page.locator("#map-mode-graph")).to_have_count(0)
    expect(page.locator("#map-mode-study")).to_have_count(0)
    expect(page.locator(".map-mode-switch")).to_have_count(0)


def test_no_graph_content_section(page: Page, base_url: str) -> None:
    _open_concept(page, base_url)
    expect(page.locator("#graph-content")).to_have_count(0)
```

- [ ] **Step 2: Run the smoke**

```bash
pytest tests/e2e/test_strip_nav.py -v
```

Expected: tests pass. Skips are acceptable if the seeded concept doesn't have enough backbone entries (the agent should create or use a multi-entry concept for the click + keyboard tests to actually exercise).

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/test_strip_nav.py
git commit -m "test(e2e): strip-as-nav -- click, keyboard, locked, no toggle"
```

---

## Task 8: Coverage gate + push + PR update + impeccable polish pass

**Files:** none (verification only)

- [ ] **Step 1: Coverage gate**

```bash
./scripts/check-coverage.sh
```

If exit 0: proceed. If non-zero, document the failure in the PR body update with the same worktree-vs-main caveat.

- [ ] **Step 2: Impeccable polish pass**

Re-read your full diff (`git diff dev..HEAD --stat` then inspect changed files). Cross-check against the impeccable bans:

- [ ] No side-stripe borders >1px on cards or list items? (The 1px anchor pillar is OK.)
- [ ] No glassmorphism by default? (The hover tooltip uses solid bg + subtle shadow, no blur.)
- [ ] No em dashes in copy or comments? Grep: `git diff dev..HEAD | grep -E "[^-]—[^-]" || echo clean`
- [ ] All motion uses ease-out-expo `cubic-bezier(0.16, 1, 0.3, 1)`?
- [ ] No `transition` on `width` / `height` / `margin` / `padding`? Grep: `git diff dev..HEAD public/css/concept-page.css | grep -E "transition.*(width|height|margin|padding)"` — should return nothing
- [ ] Visible focus ring on every interactive element? Verify `.concept-strip__node:focus-visible` is defined; verify `.concept-page-b2__entry-cta:focus-visible` exists or inherits a default
- [ ] Brand tokens (not raw hex) used wherever possible? Audit any `#XXXXXX` literals; convert to `var(--*-theme)` references where a token exists

If any check fails, fix in a small follow-up commit before push.

- [ ] **Step 3: Push**

```bash
git push origin feat/drill-chamber-port
```

- [ ] **Step 4: Update PR description**

```bash
gh pr view 236 --json body --jq .body > /tmp/pr-body.txt
cat >> /tmp/pr-body.txt <<'EOF'

## Strip-as-nav port (added 2026-05-11)

Makes the B-2 map strip the canonical navigation device for the
concept page's backbone entries. Removes the Route/Graph toggle
and deletes the entire Graph view (cytoscape constellation +
detail two-pane).

Customer signal was unanimous (4 of 4 personas -- Sam, Dimitri,
Maya, Robert -- voted to kill the toggle: "one organizing system,
not two").

What ships:
- Strip nodes are clickable; click swaps the work column with a
  240ms opacity fade-out / 320ms fade-in (no layout animation)
- Hover tooltip on non-active nodes (solid bg + subtle shadow,
  no glassmorphism)
- Keyboard arrow nav steps through backbone; Enter opens chamber
- Active node has visible focus ring (WCAG)
- Locked entries show a disabled CTA (preserves doctrine)
- Light + dark modes both render

What's deleted:
- Route/Graph toggle (markup + CSS + JS)
- #graph-content section + cytoscape stage + detail pane
- graph-view.js (no remaining consumers)
- Cytoscape CDN <script> (no remaining consumers)
- Dead CSS for .graph-stage-wrap, .graph-detail, seam-of-light pseudos

Doctrine preserved:
- No praise / scoring / mastery / streaks
- Locked entries stay locked; the work column just shows their state
- Locality: one organizing system per concept page
EOF
gh pr edit 236 --body-file /tmp/pr-body.txt
```

---

## Self-review

**Spec coverage:**
- ✓ Acceptance #1 (toggle gone): Task 4
- ✓ Acceptance #2 (graph-content gone): Task 5
- ✓ Acceptance #3 (strip click swaps + transition): Tasks 2, 3
- ✓ Acceptance #4 (locked click → silhouette): Task 2 (`renderActiveEntryHtml` branches on `isLocked`)
- ✓ Acceptance #5 (hover tooltip): Task 3
- ✓ Acceptance #6 (keyboard nav): Task 2
- ✓ Acceptance #7 (focus ring): Task 3 CSS
- ✓ Acceptance #8 (chamber path unchanged): Tasks 2 (uses `App.startDrillFromMap`)
- ✓ Acceptance #9 (light + dark): Task 3 CSS dark overrides
- ✓ Acceptance #10 (coverage gate): Task 8
- ✓ Acceptance #11 (e2e): Task 7

**Open question for the executor:**
- The "ADHD" concept currently in the live DB has only 1 backbone entry. To exercise the strip-click + keyboard tests, either seed a multi-entry concept fixture OR mark the multi-entry tests as `xfail` for v1 with a TODO to add a fixture in a follow-up.

**Out of scope for this plan:**
- Auto-scrolling the active entry into view on initial mount (Gemini's flagged mitigation from earlier; v1.1 if needed)
- Re-edit sketch route (still a console.info stub from the B-2 plan; needs its own plan)
- Strip-node deeplinking via URL hash (`?entry=core-thesis`); v1.1
- The Targeted Study mirror (Dimitri's diagnostic-accuracy demand); separate plan
- Replacing the cytoscape constellation with an SVG renderer for a future "Atlas" view; not needed for MVP since the strip carries the metaphor at the right scale
