// Desk iso-board state surface.
// Adds DOM-only state attributes, swaps circular pin heads for the existing
// dual-diamond crystal vocabulary, and adds a quiet empty-tile affordance.
//
// Re-syncs whenever app.js's renderGrid() emits Bus.emit('grid:rendered'),
// avoiding a MutationObserver self-trigger loop.

import { Bus } from './bus.js';

(function () {
  const STORE_KEY = 'learnops_concepts';
  const BOARD_STATES = new Set(['solidified', 'drilled', 'primed', 'locked', 'fractured']);

  function loadConcepts() {
    try {
      const parsed = JSON.parse(localStorage.getItem(STORE_KEY) || '[]');
      return Array.isArray(parsed) ? parsed : [];
    } catch (err) {
      return [];
    }
  }

  function parseGraphData(concept) {
    if (!concept?.graphData) return null;
    try {
      return typeof concept.graphData === 'string'
        ? JSON.parse(concept.graphData)
        : concept.graphData;
    } catch (err) {
      return null;
    }
  }

  function collectDrillNodes(graphData) {
    if (!graphData || typeof graphData !== 'object') return [];
    const nodes = [];
    if (graphData.metadata && typeof graphData.metadata === 'object') {
      nodes.push(graphData.metadata);
    }
    (graphData.backbone || []).forEach((item) => {
      if (item && typeof item === 'object') nodes.push(item);
    });
    (graphData.clusters || []).forEach((cluster) => {
      if (cluster && typeof cluster === 'object') nodes.push(cluster);
      (cluster?.subnodes || []).forEach((subnode) => {
        if (subnode && typeof subnode === 'object') nodes.push(subnode);
      });
    });
    return nodes;
  }

  // Maps the concept-shell state (legacy + live mix) onto the live five-state
  // board vocabulary defined in docs/design/socratink-ux.md §5 and UBIQUITOUS_LANGUAGE.md.
  // 'actualized' is sanctioned legacy for 'solidified'. 'hibernating' is a
  // legacy alias-to-avoid (UBIQUITOUS_LANGUAGE.md:80) with no live equivalent
  // — defaulting to 'locked' avoids overclaiming readiness on the board.
  function fallbackBoardState(sourceState) {
    if (sourceState === 'actualized') return 'solidified';
    if (sourceState === 'fractured') return 'fractured';
    if (BOARD_STATES.has(sourceState)) return sourceState;
    return 'locked';
  }

  function deriveBoardState(concept) {
    const graphData = parseGraphData(concept);
    const drillNodes = collectDrillNodes(graphData);
    const statuses = drillNodes.map((node) => node?.drill_status).filter(Boolean);

    if (statuses.some((status) => status === 'solidified' || status === 'solid')) {
      return 'solidified';
    }
    if (statuses.includes('drilled') || drillNodes.some((node) => node?.gap_type || node?.gap_description)) {
      return 'drilled';
    }
    if (statuses.includes('primed')) {
      return 'primed';
    }
    return fallbackBoardState(concept?.state);
  }

  function crystalMarkup(state) {
    return `
      <g class="concept-pin-crystal crystal-instance" data-state="${state}" aria-hidden="true">
        <ellipse class="cp-glow" cx="70" cy="-8" rx="22" ry="19"></ellipse>
        <polygon class="cp-top" points="70,-38 84,-24 70,-15 56,-24"></polygon>
        <polygon class="cp-upper-left" points="56,-24 70,-15 70,1 51,-11"></polygon>
        <polygon class="cp-upper-right" points="84,-24 89,-11 70,1 70,-15"></polygon>
        <polygon class="cp-lower-left" points="51,-11 70,1 70,18 57,6"></polygon>
        <polygon class="cp-lower-right" points="89,-11 83,6 70,18 70,1"></polygon>
        <polygon class="cp-bottom-tip" points="57,6 70,18 83,6 70,27"></polygon>
        <path class="cp-specular" d="M62 -25 70 -34 78 -25 70 -20Z"></path>
      </g>
    `;
  }

  function emptyAffordanceMarkup() {
    return `
      <g class="empty-tile-affordance" aria-hidden="true">
        <line class="empty-tile-affordance__line" x1="58" y1="40" x2="82" y2="40"></line>
        <line class="empty-tile-affordance__line" x1="70" y1="33" x2="70" y2="47"></line>
      </g>
    `;
  }

  function syncTile(tile, idx, concepts) {
    const concept = concepts[idx] || null;

    if (!concept) {
      tile.removeAttribute('data-source-state');
      tile.removeAttribute('data-board-state');
      // Cross-tab storage events can call syncTile without a preceding
      // renderGrid(). When a tab deletes the concept that previously
      // owned this tile, the populated pin/crystal markup stays in the
      // DOM unless we explicitly clear it. Strip any populated children
      // here so the empty affordance is the only contents.
      const pin = tile.querySelector('.concept-pin');
      if (pin) {
        pin.removeAttribute('data-source-state');
        pin.removeAttribute('data-state');
        pin.querySelectorAll('.concept-pin-head, .concept-pin-core, .concept-pin-crystal')
           .forEach((el) => el.remove());
        const line = pin.querySelector('.concept-pin-line');
        if (line) line.remove();
      }
      if (!tile.querySelector('.empty-tile-affordance')) {
        tile.insertAdjacentHTML('beforeend', emptyAffordanceMarkup());
      }
      return;
    }

    const boardState = deriveBoardState(concept);
    tile.dataset.sourceState = concept.state || '';
    tile.dataset.boardState = boardState;

    // Defensive: drop any stale empty affordance the previous render may
    // have inserted. Canonical renderGrid flow wipes innerHTML before
    // syncTile runs, but cross-tab storage events can fire syncTile
    // without a preceding render and leave the "+" marker orphaned.
    const staleAffordance = tile.querySelector('.empty-tile-affordance');
    if (staleAffordance) staleAffordance.remove();

    const pin = tile.querySelector('.concept-pin');
    if (!pin) return;

    pin.dataset.sourceState = concept.state || '';
    pin.dataset.state = boardState;

    pin.querySelectorAll('.concept-pin-head, .concept-pin-core').forEach((el) => el.remove());
    const line = pin.querySelector('.concept-pin-line');
    if (line) {
      line.setAttribute('y1', '22');
      line.setAttribute('y2', '38');
    }

    let crystal = pin.querySelector('.concept-pin-crystal');
    if (!crystal) {
      pin.insertAdjacentHTML('beforeend', crystalMarkup(boardState));
      crystal = pin.querySelector('.concept-pin-crystal');
    }
    if (crystal) {
      crystal.dataset.state = boardState;
    }
  }

  let refreshQueued = false;

  function refresh() {
    refreshQueued = false;
    const svg = document.getElementById('grid-svg');
    if (!svg) return;
    const concepts = loadConcepts();
    svg.querySelectorAll('.tile-group').forEach((tile, fallbackIdx) => {
      const match = /^tile-(\d+)$/.exec(tile.id || '');
      const idx = match ? Number(match[1]) : fallbackIdx;
      syncTile(tile, idx, concepts);
    });
  }

  function scheduleRefresh() {
    if (refreshQueued) return;
    refreshQueued = true;
    requestAnimationFrame(refresh);
  }

  function watch() {
    const svg = document.getElementById('grid-svg');
    if (!svg) {
      requestAnimationFrame(watch);
      return;
    }

    // Initial sync in case renderGrid() already ran before this module loaded.
    refresh();

    // Deterministic re-sync: app.js emits 'grid:rendered' at the tail of
    // renderGrid(), so we never observe our own writes.
    Bus.on('grid:rendered', scheduleRefresh);

    // Filter on STORE_KEY so unrelated cross-tab writes (theme, sound,
    // motion preferences) don't trigger a board re-render. RAF
    // throttling helps but the wake-up itself is wasted work.
    window.addEventListener('storage', (e) => {
      if (e.key === STORE_KEY || e.key === null) scheduleRefresh();
    });
    window.addEventListener('focus', scheduleRefresh);
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) scheduleRefresh();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', watch);
  } else {
    watch();
  }
})();
