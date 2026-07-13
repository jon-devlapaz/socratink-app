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
    <polygon class="tile-left"  points="2,58 70,114 70,127 2,71"/>
    <polygon class="tile-right" points="138,58 70,114 70,127 138,71"/>
    <polygon class="tile-top"   points="70,2 138,58 70,114 2,58"/>
    <polygon class="tile-highlight" points="70,2 138,58 70,114 2,58"/>
    <polygon class="tile-hit"   points="70,2 138,58 70,114 2,58"/>`;

export const EMPTY_TILE = `
    <polygon class="tile-left"      points="2,58 70,114 70,127 2,71"/>
    <polygon class="tile-right"     points="138,58 70,114 70,127 138,71"/>
    <polygon class="tile-top-empty" points="70,2 138,58 70,114 2,58"/>
    <polygon class="tile-top-dash"  points="70,2 138,58 70,114 2,58"/>
    <polygon class="tile-hit"       points="70,2 138,58 70,114 2,58"/>`;

export function conceptPinSVG(idx, state, { isDue = false } = {}) {
  const dueRing = isDue
    ? `<ellipse class="concept-pin-due-ring" cx="70" cy="61" rx="22" ry="5.5" aria-hidden="true"/>`
    : '';
  return `
    <g class="concept-marker-anim" id="concept-marker-anim-${idx}">
      <g class="concept-pin" id="concept-pin-${idx}" data-state="${state}" style="pointer-events:none;">
        <ellipse class="concept-pin-shadow" cx="70" cy="61" rx="17" ry="3.5"/>
        ${dueRing}
        <line class="concept-pin-line" x1="70" y1="-15" x2="70" y2="56"/>
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
  const isFirstUse = concepts.length === 0;
  tileEls.forEach((tileEl, idx) => {
    const concept = concepts[idx] || null;
    const isSelected = concept && concept.id === activeId;
    const isEmpty = !concept;
    const isDue = Boolean(concept && dueIds.has(concept.id));
    const isFilteredOut = readyFilterActive && (!concept || !isDue);
    const isPrimaryEmpty = isFirstUse && idx === 4;
    const isCapacity = isFirstUse && idx !== 4;

    tileEl.setAttribute('class', 'tile-group' +
      (isEmpty ? ' empty' : '') +
      (isPrimaryEmpty ? ' is-primary-empty' : '') +
      (isCapacity ? ' is-capacity' : '') +
      (isSelected ? ' selected' : '') +
      (isDue ? ' is-due' : '') +
      (isFilteredOut ? ' is-filtered-out' : ''));

    if (isDue) tileEl.setAttribute('data-due', '');
    else tileEl.removeAttribute('data-due');
    if (isFilteredOut) tileEl.setAttribute('data-ready-filtered', 'out');
    else tileEl.removeAttribute('data-ready-filtered');

    // A blank desk has one action, not nine duplicates. The centre socket
    // starts learning; the other eight are visual capacity and deliberately
    // stay out of the accessibility tree and tab order. Partial desks retain
    // the existing behaviour where any unassigned slot can start a session.
    if (isCapacity) {
      tileEl.removeAttribute('role');
      tileEl.removeAttribute('tabindex');
      tileEl.removeAttribute('aria-label');
      tileEl.removeAttribute('aria-disabled');
      tileEl.setAttribute('aria-hidden', 'true');
    } else {
      tileEl.removeAttribute('aria-hidden');
      tileEl.setAttribute('role', 'button');
      tileEl.setAttribute('tabindex', isFilteredOut ? '-1' : '0');
      if (isFilteredOut) tileEl.setAttribute('aria-disabled', 'true');
      else tileEl.removeAttribute('aria-disabled');
      tileEl.setAttribute(
        'aria-label',
        isEmpty
          ? isPrimaryEmpty ? 'Choose a topic' : 'Start from memory'
          : isDue
            ? `Resume ${concept.name}, due for spaced reconstruction`
            : `Resume ${concept.name}`
      );
    }

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
