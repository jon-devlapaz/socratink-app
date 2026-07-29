// Desk iso-board state surface.
// Adds DOM-only state attributes, swaps circular pin heads for the existing
// dual-diamond crystal vocabulary, and adds a quiet empty-tile affordance.
//
// Re-syncs whenever app.js's renderGrid() emits Bus.emit('grid:rendered'),
// avoiding a MutationObserver self-trigger loop.

import { Bus } from './bus.js';
import { deriveConceptBadge } from './concept-status.js';
import { TRAINING_STORE_KEY_PREFIX } from './training-store.js';

(function () {
  const STORE_KEY = 'learnops_concepts';

  function loadConcepts() {
    try {
      const parsed = JSON.parse(localStorage.getItem(STORE_KEY) || '[]');
      return Array.isArray(parsed) ? parsed : [];
    } catch (err) {
      return [];
    }
  }

  function loadTraining(conceptId) {
    if (!conceptId) return null;
    try {
      const raw = localStorage.getItem(`${TRAINING_STORE_KEY_PREFIX}${conceptId}`);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      return parsed && typeof parsed === 'object' ? parsed : null;
    } catch {
      return null;
    }
  }

  function boardStateFromBadge(badge) {
    if (badge === 'solidified') return 'solidified';
    if (badge === 'needs repair') return 'fractured';
    if (badge === 'primed') return 'primed';
    return null;
  }

  function legacyBoardStateFromConceptState(state) {
    const normalized = String(state || '').toLowerCase();
    if (normalized === 'actualized') return 'solidified';
    if (normalized === 'fractured') return 'fractured';
    if (normalized === 'primed') return 'primed';
    return null;
  }

  function evidenceHintForBoardState(boardState) {
    if (boardState === 'solidified') return 'Spaced reconstruction is on record.';
    if (boardState === 'fractured') return 'A specific gap is ready to repair.';
    if (boardState === 'primed') return 'Reconstruction evidence is on record.';
    return '';
  }

  function syncEvidenceHint(tile, hint) {
    let title = tile.querySelector('.iso-board-state-title');
    if (!hint) {
      tile.removeAttribute('data-evidence-hint');
      tile.removeAttribute('aria-describedby');
      if (title) title.remove();
      return;
    }

    const titleId = `${tile.id}-evidence-hint`;
    tile.dataset.evidenceHint = hint;
    tile.setAttribute('aria-describedby', titleId);
    if (!title) {
      title = document.createElementNS('http://www.w3.org/2000/svg', 'title');
      title.classList.add('iso-board-state-title');
      tile.insertBefore(title, tile.firstChild);
    }
    title.id = titleId;
    title.textContent = hint;
  }

  function deriveBoardProjection(concept) {
    const training = loadTraining(concept?.id);
    const trainingBadge = training
      ? deriveConceptBadge({ ...concept, graphData: null }, training)
      : null;
    const trainingState = boardStateFromBadge(trainingBadge);
    const legacyBadge = deriveConceptBadge(concept, null);
    const boardState = trainingState
      || boardStateFromBadge(legacyBadge)
      || legacyBoardStateFromConceptState(concept?.state)
      || 'locked';
    return {
      boardState,
      evidenceHint: trainingState ? evidenceHintForBoardState(trainingState) : '',
    };
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

  function emptyAffordanceMarkup({ primary = false } = {}) {
    if (primary) {
      return `
        <g class="empty-tile-affordance empty-tile-affordance--primary" aria-hidden="true">
          <text class="empty-tile-affordance__label" x="70" y="63" text-anchor="middle">Choose a topic</text>
        </g>
      `;
    }
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
      const isFirstUse = concepts.length === 0;
      const isPrimaryEmpty = isFirstUse && idx === 4;
      tile.removeAttribute('data-source-state');
      tile.removeAttribute('data-board-state');
      syncEvidenceHint(tile, '');
      // Cross-tab storage events can call syncTile without a preceding
      // renderGrid(). When a tab deletes the concept that previously
      // owned this tile, the populated pin/crystal markup stays in the
      // DOM unless we explicitly clear it. Strip any populated children
      // here so the empty affordance is the only contents.
      const pin = tile.querySelector('.concept-pin');
      if (pin) {
        pin.removeAttribute('data-source-state');
        pin.removeAttribute('data-state');
        pin.querySelectorAll(
          '.concept-pin-head, .concept-pin-core, .concept-pin-crystal, .concept-pin-due-ring',
        ).forEach((el) => el.remove());
        const line = pin.querySelector('.concept-pin-line');
        if (line) line.remove();
      }
      const currentAffordance = tile.querySelector('.empty-tile-affordance');
      const currentIsPrimary = currentAffordance?.classList.contains('empty-tile-affordance--primary');
      const shouldShowAffordance = !isFirstUse || isPrimaryEmpty;
      if (currentAffordance && (!shouldShowAffordance || currentIsPrimary !== isPrimaryEmpty)) {
        currentAffordance.remove();
      }
      if (shouldShowAffordance && !tile.querySelector('.empty-tile-affordance')) {
        tile.insertAdjacentHTML('beforeend', emptyAffordanceMarkup({ primary: isPrimaryEmpty }));
      }
      return;
    }

    const { boardState, evidenceHint } = deriveBoardProjection(concept);
    tile.dataset.sourceState = concept.state || '';
    tile.dataset.boardState = boardState;
    syncEvidenceHint(tile, evidenceHint);

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
      line.setAttribute('y2', '56');
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

    // Route external learner-state changes back through app.js so the
    // canonical Desk renderer owns markup, due surfaces, and semantics.
    window.addEventListener('storage', (e) => {
      if (
        e.key === STORE_KEY
        || e.key === null
        || e.key?.startsWith(TRAINING_STORE_KEY_PREFIX)
      ) {
        Bus.emit('desk:external-state-change');
      }
    });
    window.addEventListener('focus', () => Bus.emit('desk:external-state-change'));
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) Bus.emit('desk:external-state-change');
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', watch);
  } else {
    watch();
  }
})();
