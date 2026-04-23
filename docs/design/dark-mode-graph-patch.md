# Dark-Mode Graph Patch — Integration Guide

**Target repo:** `jon-devlapaz/socratink-app`
**Branch name (suggested):** `feat/dark-mode-graph`
**Scope:** Upgrades the knowledge-graph dark theme (obsidian base, crystal-node palette, panel seam-of-light linking active node to right-rail). Light mode is untouched.

This patch is **additive** — every new rule is scoped behind `[data-theme="dark"]` or introduces new tokens that no existing rule reads from. You can revert by deleting the named blocks below.

---

## Files touched

| # | File | What changes |
|---|---|---|
| 1 | `public/css/variables.css` | +1 block of dark-mode graph tokens |
| 2 | `public/css/layout.css` | +1 block of dark-mode stage + panel rules |
| 3 | `public/js/graph-view.js` | Five cytoscape style objects read new state colors from CSS tokens |
| 4 (optional) | `public/css/layout.css` + new markup | Starfield polish layer |

---

## Pre-flight

```bash
git checkout -b feat/dark-mode-graph
git status    # must be clean before starting
```

Verify these selectors exist in your tree before editing. If any are missing, stop and share — the file may have drifted since this patch was written.

```bash
grep -n '\[data-theme="dark"\]' public/css/variables.css
grep -n '\.graph-stage-wrap'     public/css/layout.css
grep -n '\.graph-detail '        public/css/layout.css
grep -n 'cytoscape'              public/js/graph-view.js
grep -n "node\[state = \"primed\"\]"      public/js/graph-view.js
grep -n "node\[state = \"solidified\"\]"  public/js/graph-view.js
grep -n "node\[state = \"drilled\"\]"     public/js/graph-view.js
```

Expected: matches in all four files.

---

## Patch 1 — Graph tokens (`public/css/variables.css`)

**Locate** your existing `[data-theme="dark"]` block (around line 347 per your snapshot; line number may drift). **Inside** that same selector, at the bottom just before the closing `}`, paste the block below.

Do NOT create a second `[data-theme="dark"]` block — add inside the existing one. If your existing block already defines `--node-locked`, keep this patch's definition (it's the new one).

```css
/* ──────────────────────────────────────────────────────────
   DARK MODE — Knowledge Graph
   Obsidian base + lavender spotlight + state palette.
   Read from public/js/graph-view.js via getComputedStyle.
   ────────────────────────────────────────────────────────── */

  /* Stage (the cytoscape canvas container) */
  --graph-stage-bg:
    radial-gradient(ellipse 50% 50% at 50% 40%, rgba(144, 103, 198, 0.22), transparent 60%),
    radial-gradient(circle at 50% 50%, rgba(30, 22, 58, 0.40), transparent 50%),
    linear-gradient(180deg, #07050f 0%, #0c0820 50%, #05030a 100%);
  --graph-stage-border: rgba(141, 134, 201, 0.20);

  /* Right-side detail panel */
  --graph-panel-bg:
    radial-gradient(ellipse 80% 40% at 50% 0%, rgba(144, 103, 198, 0.14), transparent 70%),
    linear-gradient(180deg, #120c24 0%, #07050f 100%);
  --graph-panel-border: rgba(144, 103, 198, 0.26);
  --graph-panel-shadow:
    inset 0 1px 0 rgba(247, 236, 225, 0.04),
    0 18px 48px rgba(0, 0, 0, 0.45);

  /* Seam of light — vertical sliver on the panel's left edge
     that visually "links" the active node to the detail panel. */
  --graph-seam-color: #d7beff;
  --graph-seam-glow:  rgba(215, 190, 255, 0.65);

  /* Node state palette — referenced by graph-view.js */
  --node-locked:       rgba(141, 134, 201, 0.40);
  --node-locked-ring:  rgba(141, 134, 201, 0.22);
  --node-primed:       #9fd5ed;
  --node-primed-halo:  rgba(159, 213, 237, 0.55);
  --node-drilled:      #f0c373;
  --node-drilled-halo: rgba(240, 195, 115, 0.50);
  --node-solid:        #d7beff;
  --node-solid-halo:   rgba(215, 190, 255, 0.70);

  /* Edge palette */
  --edge-structural: rgba(215, 190, 255, 0.45);
  --edge-subnode:    rgba(215, 190, 255, 0.22);
  --edge-locked:     rgba(141, 134, 201, 0.10);
  --edge-prereq:     rgba(215, 190, 255, 0.55);
  --edge-domain:     rgba(141, 208, 200, 0.50);
```

**Rationale for each token** — so reviewers understand:
- `--graph-stage-bg`: three-layer gradient (spotlight + mid-blur + base) — replaces the previous washed-lavender feel with a deep obsidian glow.
- `--graph-panel-*`: darker-than-surface-card, with a top bloom that anchors the panel title.
- `--graph-seam-*`: used by the `::before` pseudo in Patch 2.
- `--node-*` / `--edge-*`: consumed by `graph-view.js` in Patch 3. Keeping them in CSS means future theme tweaks don't require JS edits.

---

## Patch 2 — Stage + panel styles (`public/css/layout.css`)

**Locate** the end of the block containing `.graph-stage-wrap` and `.graph-detail` (around line 877–1008 per your snapshot). **Append** this block at the end of that section (or anywhere after both selectors are defined — specificity is handled by the attribute selector):

```css
/* ──────────────────────────────────────────────────────────
   DARK MODE — Knowledge Graph stage + detail panel
   Scoped to [data-theme="dark"]; light mode is unaffected.
   ────────────────────────────────────────────────────────── */

[data-theme="dark"] .graph-stage-wrap {
  background: var(--graph-stage-bg);
  border-color: var(--graph-stage-border);
}

[data-theme="dark"] .graph-detail {
  background: var(--graph-panel-bg);
  border-color: var(--graph-panel-border);
  box-shadow: var(--graph-panel-shadow);
  position: relative; /* anchor for ::before seam + ::after bloom */
}

/* Seam of light on the panel's left edge */
[data-theme="dark"] .graph-detail::before {
  content: "";
  position: absolute;
  left: -1px;
  top: 34%;
  width: 2px;
  height: 28%;
  background: linear-gradient(
    180deg,
    transparent,
    var(--graph-seam-color),
    transparent
  );
  box-shadow: 0 0 20px 3px var(--graph-seam-glow);
  z-index: 2;
  pointer-events: none;
}

/* Subtle ambient bloom that anchors the panel title */
[data-theme="dark"] .graph-detail::after {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 120px;
  background: radial-gradient(
    ellipse at 30% 0%,
    rgba(215, 190, 255, 0.08),
    transparent 70%
  );
  pointer-events: none;
  z-index: 1;
}

/* Keep panel content above the decorative layers */
[data-theme="dark"] .graph-detail > * {
  position: relative;
  z-index: 3;
}

/* Accessibility: honor reduced-motion (no animated seam today,
   but reserves the selector so we never add motion that ignores it) */
@media (prefers-reduced-motion: reduce) {
  [data-theme="dark"] .graph-detail::before {
    background: var(--graph-seam-color);
    box-shadow: none;
  }
}
```

**Gotchas**:
- If your existing `.graph-detail` rule sets `position: relative` already, this is a no-op (fine).
- If it sets `overflow: hidden`, the seam will be clipped — change that to `overflow: visible` on `.graph-detail` in dark mode:
  ```css
  [data-theme="dark"] .graph-detail { overflow: visible; }
  ```
  Only add this if you can visually confirm the seam is cut off.

---

## Patch 3 — Cytoscape stylesheet (`public/js/graph-view.js`)

This is the only non-CSS change. Cytoscape runs on canvas, so its styles live in JS.

### 3a — Add a token reader

**Locate** `export function mountKnowledgeGraph(...)`. Immediately after the early-return guards (after the `if (!transformed.nodes.length)` block, before `container.innerHTML = '';`), insert:

```js
  // ── Dark-mode token bridge ───────────────────────────────
  // cytoscape styles are evaluated once at construction, so we
  // read the current theme's tokens into a closure. Changing the
  // theme requires re-mounting the graph (standard pattern).
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  const readToken = (name, fallback) => {
    const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return v || fallback;
  };

  const T = isDark ? {
    nodeLocked:      readToken('--node-locked',       'rgba(141,134,201,0.40)'),
    nodeLockedRing:  readToken('--node-locked-ring',  'rgba(141,134,201,0.22)'),
    nodePrimed:      readToken('--node-primed',       '#9fd5ed'),
    nodePrimedHalo:  readToken('--node-primed-halo',  'rgba(159,213,237,0.55)'),
    nodeDrilled:     readToken('--node-drilled',      '#f0c373'),
    nodeDrilledHalo: readToken('--node-drilled-halo', 'rgba(240,195,115,0.50)'),
    nodeSolid:       readToken('--node-solid',        '#d7beff'),
    nodeSolidHalo:   readToken('--node-solid-halo',   'rgba(215,190,255,0.70)'),
    edgeStructural:  readToken('--edge-structural',   'rgba(215,190,255,0.45)'),
    edgeSubnode:     readToken('--edge-subnode',      'rgba(215,190,255,0.22)'),
    edgeLocked:      readToken('--edge-locked',       'rgba(141,134,201,0.10)'),
    edgePrereq:      readToken('--edge-prereq',       'rgba(215,190,255,0.55)'),
    edgeDomain:      readToken('--edge-domain',       'rgba(141,208,200,0.50)'),
    textStrong:      readToken('--text-strong',       '#f7ece1'),
    textMuted:       readToken('--text-muted',        'rgba(247,236,225,0.72)'),
  } : {
    // Light-mode values — preserve the existing hard-coded defaults
    // so nothing changes for light users.
    nodeLocked:      'rgba(255,255,255,0.08)',
    nodeLockedRing:  'rgba(124,111,205,0.24)',
    nodePrimed:      '#d9eef8',
    nodePrimedHalo:  'rgba(109,176,213,0.18)',
    nodeDrilled:     '#d9a14a',
    nodeDrilledHalo: 'rgba(217,161,74,0.18)',
    nodeSolid:       '#7c6fcd',
    nodeSolidHalo:   'rgba(124,111,205,0.22)',
    edgeStructural:  'rgba(124,111,205,0.10)',
    edgeSubnode:     'rgba(124,111,205,0.08)',
    edgeLocked:      'rgba(124,111,205,0.05)',
    edgePrereq:      'rgba(124,111,205,0.44)',
    edgeDomain:      'rgba(114,160,154,0.42)',
    textStrong:      '#4f4384',
    textMuted:       '#7c6fcd',
  };
```

### 3b — Replace the five state selectors in the `style:` array

Find the style entries that match these selectors and replace their style objects with the values below. Keep the `selector` key; only edit the `style` object. Everything else in the array (core-thesis size, backbone size, base `node`, `.is-dimmed`, etc.) stays as-is.

**`node[state = "locked"][available = 0]`** — faint but structurally visible:
```js
style: {
  'background-color': T.nodeLocked,
  'border-color': T.nodeLockedRing,
  'border-style': 'dashed',
  'border-width': 1.5,
  opacity: isDark ? 0.4 : 0.22,
  label: 'data(teaserLabel)',
  color: T.textMuted,
  'text-opacity': 0.56,
  'overlay-opacity': 0,
  'text-outline-width': 0,
  events: 'no',
},
```

**`node[state = "primed"]`** — cyan glow:
```js
style: {
  'background-color': T.nodePrimed,
  'border-color': T.nodePrimed,
  'border-width': 2.2,
  'border-style': 'solid',
  opacity: 0.97,
  label: 'data(label)',
  color: T.textStrong,
  'text-opacity': 1,
  'overlay-color': T.nodePrimedHalo,
  'overlay-opacity': isDark ? 0.25 : 0.05,
  'overlay-padding': 6,
  events: 'yes',
},
```

**`node[state = "drilled"]`** — amber warning:
```js
style: {
  'background-color': T.nodeDrilled,
  'border-color': T.nodeDrilled,
  'border-width': 2.2,
  'border-style': 'solid',
  opacity: 0.95,
  label: 'data(label)',
  color: T.textStrong,
  'text-opacity': 1,
  'overlay-color': T.nodeDrilledHalo,
  'overlay-opacity': isDark ? 0.22 : 0.04,
  'overlay-padding': 6,
},
```

**`node[state = "solidified"]`** — lavender + halo:
```js
style: {
  'background-color': T.nodeSolid,
  'border-color': T.nodeSolid,
  'border-width': 2.4,
  'border-style': 'solid',
  opacity: 1,
  label: 'data(label)',
  color: T.textStrong,
  'text-opacity': 1,
  'overlay-color': T.nodeSolidHalo,
  'overlay-opacity': isDark ? 0.30 : 0.06,
  'overlay-padding': 8,
},
```

**`edge` (base edge)** — state-aware:
```js
style: {
  width: 1.4,
  'curve-style': 'bezier',
  'line-color': T.edgeStructural,
  'target-arrow-shape': 'none',
  opacity: 0.85,
  'transition-property': 'opacity, line-color, width',
  'transition-duration': '180ms',
},
```

**`.edge-structural`**, **`.edge-subnode-link`**, **`.edge-prerequisite`**, **`.edge-domain`** — point each at its matching token:
```js
{ selector: '.edge-structural',  style: { width: 1.5, 'line-color': T.edgeStructural } },
{ selector: '.edge-subnode-link', style: { width: 1.2, 'line-color': T.edgeSubnode } },
{ selector: '.edge-prerequisite', style: {
    'line-color': T.edgePrereq, 'target-arrow-color': T.edgePrereq,
}},
{ selector: '.edge-domain', style: {
    'line-color': T.edgeDomain, 'target-arrow-color': T.edgeDomain,
}},
```

### 3c — Active-drill glow (optional enhancement)

Find `.is-active-drill` and bump the overlay so the selected node pops harder in dark mode:

```js
{
  selector: '.is-active-drill',
  style: {
    'border-color': T.nodeSolid,
    'border-width': 4,
    'background-color': T.nodeSolid,
    opacity: 1,
    'z-index': 9999,
    'overlay-color': T.nodeSolidHalo,
    'overlay-opacity': isDark ? 0.35 : 0.12,
    'overlay-padding': isDark ? 22 : 16,
    'text-opacity': 1,
  },
},
```

### 3d — Theme-change hot-swap (optional, recommended)

If your app toggles dark mode without a reload (most apps do), cytoscape styles won't update live. Add this listener near the `destroy()` method in the returned object, and expose a `rethemeToken` method:

```js
// At the top of mountKnowledgeGraph, set up the observer
const themeObserver = new MutationObserver((mutations) => {
  for (const m of mutations) {
    if (m.attributeName === 'data-theme') {
      // Cheap path: update the top-level data and let classes re-evaluate.
      // For full fidelity, the simplest move is a remount:
      window.dispatchEvent(new CustomEvent('socratink:theme-change'));
      break;
    }
  }
});
themeObserver.observe(document.documentElement, { attributes: true });
```

Then in the `destroy()` method add `themeObserver.disconnect();`.

In your app shell, on that event, call the existing graph-mount cycle:
```js
window.addEventListener('socratink:theme-change', () => {
  // If you store the mount result as `graphInstance`, just remount:
  graphInstance?.destroy();
  graphInstance = mountKnowledgeGraph({ /* same args */ });
});
```

If you'd rather ship without the hot-swap for now, users will see the new theme on next reload — acceptable for an MVP.

---

## Patch 4 (optional) — Starfield polish layer

Adds a CSS-animated twinkle behind the cytoscape canvas. Pure decoration, skip if you want the smallest patch.

**In your graph-view template** (wherever `<div class="graph-stage-wrap">` lives), add a sibling just inside:

```html
<div class="graph-stage-wrap">
  <div class="graph-stars" aria-hidden="true"></div>
  <!-- existing cytoscape container -->
</div>
```

**CSS** (append to `layout.css` after Patch 2):

```css
[data-theme="dark"] .graph-stars {
  position: absolute; inset: 0;
  pointer-events: none;
  z-index: 0;
  overflow: hidden;
  background-image:
    radial-gradient(1.5px 1.5px at 12% 20%, #f7ece1 50%, transparent 100%),
    radial-gradient(1px 1px at 32% 68%, #f7ece1 50%, transparent 100%),
    radial-gradient(1.5px 1.5px at 48% 14%, #f7ece1 50%, transparent 100%),
    radial-gradient(1px 1px at 62% 82%, #f7ece1 50%, transparent 100%),
    radial-gradient(1.2px 1.2px at 78% 28%, #f7ece1 50%, transparent 100%),
    radial-gradient(1px 1px at 88% 58%, #f7ece1 50%, transparent 100%),
    radial-gradient(1.5px 1.5px at 22% 90%, #f7ece1 50%, transparent 100%),
    radial-gradient(1px 1px at 92% 12%, #f7ece1 50%, transparent 100%);
  opacity: 0.6;
  animation: graphTwinkle 6s ease-in-out infinite;
}
[data-theme="dark"] .graph-stars::after {
  /* second layer, offset timing, for parallax feel */
  content: "";
  position: absolute; inset: 0;
  background-image:
    radial-gradient(1px 1px at 18% 44%, #d7beff 50%, transparent 100%),
    radial-gradient(1.2px 1.2px at 54% 58%, #d7beff 50%, transparent 100%),
    radial-gradient(1px 1px at 76% 72%, #d7beff 50%, transparent 100%);
  opacity: 0.4;
  animation: graphTwinkle 8s ease-in-out 1s infinite;
}
@keyframes graphTwinkle {
  0%, 100% { opacity: 0.25; }
  50%      { opacity: 0.72; }
}
@media (prefers-reduced-motion: reduce) {
  [data-theme="dark"] .graph-stars,
  [data-theme="dark"] .graph-stars::after { animation: none; opacity: 0.4; }
}
```

Make sure cytoscape's container has `position: relative; z-index: 1;` so it sits above the stars.

---

## Verification checklist

Run through this with the browser devtools open.

**Light mode (regression check — should look identical to today):**
- [ ] Toggle to light. Stage, panel, nodes, edges all match the current light palette
- [ ] No console errors on graph mount

**Dark mode (the payoff):**
- [ ] Stage has the obsidian gradient — NOT the old washed lavender
- [ ] Right panel is dark, with the vertical **seam of light** on its left edge
- [ ] **Locked** nodes: faint violet, dashed border, dimmed but still visible
- [ ] **Primed** nodes: cyan fill with a soft halo
- [ ] **Drilled** nodes: amber fill with a soft halo
- [ ] **Solidified** nodes: lavender fill with a stronger halo
- [ ] Edges between solidified nodes are clearly visible (not ghosts)
- [ ] Active node has a bigger violet overlay than non-active
- [ ] Hover on any node — dim/focus behavior still works (that's existing code, Patch 3 doesn't touch it)
- [ ] Drag a node — no flicker, ambient drift resumes
- [ ] Resize the window — graph re-fits

**Accessibility:**
- [ ] OS-level `prefers-reduced-motion` disables the starfield animation (if Patch 4 applied)
- [ ] Keyboard focus ring on action buttons in the panel is still visible (deep navy on lavender — should pass contrast)

---

## Rollback

Every change is isolated. To revert:

```bash
git revert <commit-sha>
# or, cherry-pick off:
git checkout main -- public/css/variables.css public/css/layout.css public/js/graph-view.js
```

No dependencies added. No data-format changes. No breaking API surface.

---

## Known non-issues / explicit trade-offs

- **Crystal-facet nodes from V3** are not in this patch. Cytoscape's canvas renderer doesn't support the polygon facet/shading trick without a custom renderer. Future work: swap cytoscape for an SVG-based graph in a separate epic.
- **Traveling edge beam** from V3 is not in this patch for the same reason. If you want the effect, it'd be an absolutely-positioned SVG overlay on top of cytoscape, sized to match the active edge — a second epic.
- **Theme hot-swap (3d)** is optional. Without it, users who toggle theme mid-session need to navigate away from the graph and back, or refresh, to pick up the new colors.

---

## If anything breaks

1. `console.log(T)` at the top of `mountKnowledgeGraph` — every value should be non-empty. Empty string means a CSS token failed to resolve; check variables.css loaded first.
2. If edges look washed out, your `layout.css` `!important` rules may be winning. Search for `!important` on `.graph-stage-wrap` or `.graph-detail` and reconcile.
3. If the seam doesn't appear, your existing `.graph-detail` has `overflow: hidden`. Add `[data-theme="dark"] .graph-detail { overflow: visible; }` (see Patch 2 gotcha).

---

**Commit message:**
```
feat(graph): dark-mode atlas — obsidian stage, state-colored crystal palette, seam-of-light panel

- Adds graph-scoped dark tokens in variables.css (stage, panel, node state, edges)
- layout.css dark overrides for .graph-stage-wrap and .graph-detail (+ seam pseudo)
- graph-view.js reads new tokens via getComputedStyle and threads them through
  the cytoscape stylesheet for locked/primed/drilled/solidified/active states
- Light mode untouched; all changes scoped behind [data-theme="dark"]
- Optional starfield polish layer behind Patch 4
```
