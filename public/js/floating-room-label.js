// Floating UI–anchored room-label that tracks the actual <g> element,
// replacing the legacy #tile-tooltip's stale precomputed coords.
//
// One singleton .room-label element is appended to <body>. On hover/focus
// of a .tile-group, computePosition() places the label above the group;
// autoUpdate() keeps it correct under scroll/resize/transform.
// On leave/blur the label hides.
//
// Re-binds whenever app.js's renderGrid() emits Bus.emit('grid:rendered'),
// avoiding MutationObserver wake-ups on every tile innerHTML/class write.

import { Bus } from './bus.js';

(async function () {
  const STORE_KEY = 'learnops_concepts';

  function loadConcepts() {
    try {
      return JSON.parse(localStorage.getItem(STORE_KEY) || '[]');
    } catch (err) {
      return [];
    }
  }

  // Locally-bundled Floating UI (vendored from jsDelivr's @floating-ui/dom@1.6.3
  // ESM build). Vendoring removes the runtime CDN dependency — no silent
  // label loss when jsDelivr is blocked, down, or rate-limited.
  let floatingUi;
  try {
    floatingUi = await import('/vendor/floating-ui-dom-1.6.3.esm.js');
  } catch (err) {
    console.warn('[room-label] failed to load Floating UI', err);
    return;
  }
  const { computePosition, flip, shift, offset, autoUpdate } = floatingUi;

  // One singleton label element.
  function ensureLabel() {
    let el = document.querySelector('.room-label');
    if (el) return el;
    el = document.createElement('div');
    el.className = 'room-label';
    el.setAttribute('role', 'tooltip');
    el.dataset.show = 'false';
    el.innerHTML = `
      <span class="room-label__name"></span>
      <span class="room-label__action">Open room</span>
    `;
    document.body.appendChild(el);
    return el;
  }

  let activeCleanup = null;
  let activeAnchor = null;

  function show(anchor, { name, action, kind }) {
    if (activeCleanup) activeCleanup();
    const label = ensureLabel();
    label.dataset.kind = kind || 'room';
    label.querySelector('.room-label__name').textContent = name;
    label.querySelector('.room-label__action').textContent = action || '';
    activeAnchor = anchor;

    activeCleanup = autoUpdate(anchor, label, async () => {
      const { x, y } = await computePosition(anchor, label, {
        placement: 'top',
        middleware: [offset(14), flip(), shift({ padding: 12 })],
      });
      label.style.left = `${x}px`;
      label.style.top = `${y}px`;
    });
    // Defer the show flag one frame so the position lands before fade-in.
    requestAnimationFrame(() => {
      label.dataset.show = 'true';
    });
  }

  function hide(anchor) {
    if (anchor && anchor !== activeAnchor) return;
    const label = document.querySelector('.room-label');
    if (label) label.dataset.show = 'false';
    if (activeCleanup) {
      activeCleanup();
      activeCleanup = null;
    }
    activeAnchor = null;
  }

  function bindTile(tileGroup, conceptIdx) {
    if (tileGroup.dataset.roomLabelBound === '1') return;
    tileGroup.dataset.roomLabelBound = '1';
    // tabindex / role / aria-label are owned by app.js renderGrid() so
    // they survive every render and stay in sync with the concept name.

    const showForTile = () => {
      const concepts = loadConcepts();
      const concept = concepts[conceptIdx];
      show(tileGroup, concept
        ? { name: concept.name, action: 'Open room', kind: 'room' }
        : { name: 'Begin a concept', action: '', kind: 'empty' });
    };

    tileGroup.addEventListener('mouseenter', showForTile);
    tileGroup.addEventListener('mouseleave', () => hide(tileGroup));
    tileGroup.addEventListener('focus', showForTile);
    tileGroup.addEventListener('blur', () => hide(tileGroup));
  }

  function refresh() {
    const svg = document.getElementById('grid-svg');
    if (!svg) return;
    const tiles = svg.querySelectorAll('.tile-group');
    tiles.forEach((tile, idx) => {
      // Pull idx from id (tile-N) since DOM order can shift with re-renders.
      const m = /^tile-(\d+)$/.exec(tile.id);
      const conceptIdx = m ? Number(m[1]) : idx;
      bindTile(tile, conceptIdx);
    });
  }

  function watch() {
    const svg = document.getElementById('grid-svg');
    if (!svg) {
      requestAnimationFrame(watch);
      return;
    }
    refresh();
    Bus.on('grid:rendered', refresh);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', watch);
  } else {
    watch();
  }
})();
