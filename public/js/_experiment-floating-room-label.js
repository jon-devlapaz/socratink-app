// EXPERIMENTAL — NOT COMMITTED.
// Replaces the legacy #tile-tooltip's stale precomputed coords with a
// Floating UI–anchored room-label that tracks the actual <g> element.
//
// One singleton .room-label element is appended to <body>. On hover/focus
// of a non-empty .tile-group, computePosition() places the label above
// the group; autoUpdate() keeps it correct under scroll/resize/transform.
// On leave/blur the label hides.

(async function () {
  const STORE_KEY = 'learnops_concepts';

  function loadConcepts() {
    try {
      return JSON.parse(localStorage.getItem(STORE_KEY) || '[]');
    } catch (err) {
      return [];
    }
  }

  // Same import URL the rest of the app uses.
  let floatingUi;
  try {
    floatingUi = await import('https://cdn.jsdelivr.net/npm/@floating-ui/dom@1.6.3/+esm');
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
      <span class="room-label__action">Open room →</span>
    `;
    document.body.appendChild(el);
    return el;
  }

  let activeCleanup = null;
  let activeAnchor = null;

  function show(anchor, conceptName) {
    if (activeCleanup) activeCleanup();
    const label = ensureLabel();
    label.querySelector('.room-label__name').textContent = conceptName;
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
    tileGroup.setAttribute('tabindex', '0');

    tileGroup.addEventListener('mouseenter', () => {
      const concepts = loadConcepts();
      const concept = concepts[conceptIdx];
      if (!concept) return;
      show(tileGroup, concept.name);
    });
    tileGroup.addEventListener('mouseleave', () => hide(tileGroup));
    tileGroup.addEventListener('focus', () => {
      const concepts = loadConcepts();
      const concept = concepts[conceptIdx];
      if (!concept) return;
      show(tileGroup, concept.name);
    });
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
      if (tile.classList.contains('empty')) return; // bind only non-empty
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
    const observer = new MutationObserver(() => refresh());
    observer.observe(svg, { childList: true, subtree: true, attributes: true, attributeFilter: ['class'] });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', watch);
  } else {
    watch();
  }
})();
