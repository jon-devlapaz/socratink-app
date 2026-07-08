export const ANIM_CLASSES = {
  emerge: 'anim-emerge', crack: 'anim-crack', cocoon: 'anim-cocoon',
  actualize: 'anim-actualize', repair: 'anim-repair',
};

export function playAnim(name, tileIdx, { documentRef = document } = {}) {
  const cls = ANIM_CLASSES[name];
  if (!cls) return;
  const el = documentRef.getElementById('concept-marker-anim-' + tileIdx);
  if (!el) return;
  function done() {
    el.classList.remove(cls);
    el.removeEventListener('animationend', done);
    el.removeEventListener('animationcancel', done);
  }
  Object.values(ANIM_CLASSES).forEach(c => el.classList.remove(c));
  el.addEventListener('animationend', done);
  el.addEventListener('animationcancel', done);
  el.classList.add(cls);
}

// Desk tiles are inventory/navigation. The pin marks that a concept
// has earned a place here; it does not encode graph-truth evidence.
export const TILE_PLATFORM = `
    <polygon class="tile-left"  points="0,40 70,80 70,90 0,50"/>
    <polygon class="tile-right" points="140,40 70,80 70,90 140,50"/>
    <polygon class="tile-top"   points="70,0 140,40 70,80 0,40"/>
    <polygon class="tile-highlight" points="70,0 140,40 70,80 0,40"/>
    <polygon class="tile-hit"   points="70,0 140,40 70,80 0,40"/>`;

export const EMPTY_TILE = `
    <polygon class="tile-left"      points="0,40 70,80 70,90 0,50"/>
    <polygon class="tile-right"     points="140,40 70,80 70,90 140,50"/>
    <polygon class="tile-top-empty" points="70,0 140,40 70,80 0,40"/>
    <polygon class="tile-top-dash"  points="70,0 140,40 70,80 0,40"/>
    <polygon class="tile-hit"       points="70,0 140,40 70,80 0,40"/>`;

export function conceptPinSVG(idx, state, { isDue = false } = {}) {
  const dueRing = isDue
    ? `<ellipse class="concept-pin-due-ring" cx="70" cy="43" rx="22" ry="5.5" aria-hidden="true"/>`
    : '';
  return `
    <g class="concept-marker-anim" id="concept-marker-anim-${idx}">
      <g class="concept-pin" id="concept-pin-${idx}" data-state="${state}" style="pointer-events:none;">
        <ellipse class="concept-pin-shadow" cx="70" cy="43" rx="17" ry="3.5"/>
        ${dueRing}
        <line class="concept-pin-line" x1="70" y1="-15" x2="70" y2="38"/>
        <circle class="concept-pin-head" cx="70" cy="-15" r="8.5"/>
        <circle class="concept-pin-core" cx="70" cy="-15" r="3.1"/>
      </g>
    </g>`;
}

export function renderGrid({
  concepts,
  tileEls,
  activeId,
  bus,
  dueConceptIds = null,
  readyFilterActive = false,
}) {
  const dueIds = dueConceptIds instanceof Set ? dueConceptIds : new Set();
  tileEls.forEach((tileEl, idx) => {
    const concept = concepts[idx] || null;
    const isSelected = concept && concept.id === activeId;
    const isEmpty = !concept;
    const isDue = Boolean(concept && dueIds.has(concept.id));
    const isFilteredOut = readyFilterActive && (!concept || !isDue);

    tileEl.setAttribute('class', 'tile-group' +
      (isEmpty ? ' empty' : '') +
      (isSelected ? ' selected' : '') +
      (isDue ? ' is-due' : '') +
      (isFilteredOut ? ' is-filtered-out' : ''));

    if (isDue) tileEl.setAttribute('data-due', '');
    else tileEl.removeAttribute('data-due');
    if (isFilteredOut) tileEl.setAttribute('data-ready-filtered', 'out');
    else tileEl.removeAttribute('data-ready-filtered');

    // Button semantics for keyboard + assistive-tech parity with the
    // SVG <g onclick> handler. tabindex is set here (not in the
    // floating-room-label experiment) so it survives every render.
    // Filtered-out tiles stay in the DOM but leave the tab order.
    tileEl.setAttribute('role', 'button');
    tileEl.setAttribute('tabindex', isFilteredOut ? '-1' : '0');
    if (isFilteredOut) tileEl.setAttribute('aria-disabled', 'true');
    else tileEl.removeAttribute('aria-disabled');
    tileEl.setAttribute(
      'aria-label',
      isEmpty
        ? 'Start learning'
        : isDue
          ? `Resume ${concept.name}, due for spaced reconstruction`
          : `Resume ${concept.name}`
    );

    if (isEmpty) {
      tileEl.innerHTML = EMPTY_TILE;
    } else {
      tileEl.innerHTML = TILE_PLATFORM + conceptPinSVG(idx, concept.state, { isDue });
    }
  });

  // Listened to by iso-board-state-surface.js to re-derive
  // board-state attrs / re-inject crystal pin without a MutationObserver.
  bus.emit('grid:rendered');
}
