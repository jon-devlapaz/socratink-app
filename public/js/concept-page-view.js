import { escHtml } from './html.js';

export function renderConceptStripHtml(backbone, activeEntry, activeIdx) {
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
    const predecessorsAttempted = i === 0 || backbone
      .slice(0, i)
      .every((n) => (n?.drill_status || 'locked') !== 'locked');
    const isReady = status === 'locked' && predecessorsAttempted;
    const isBlocked = status === 'locked' && !predecessorsAttempted;
    const isActive = i === activeIdx;
    const cls = [
      'concept-strip__node',
      isPrimed
        ? 'concept-strip__node--primed'
        : (isReady ? 'concept-strip__node--ready' : 'concept-strip__node--locked'),
    ];
    if (isActive) cls.push('is-active');
    const r = isActive ? 9 : (isPrimed ? 7 : (isReady ? 7 : 6));
    const entryId = node.id || `entry-${i}`;
    const label = escHtml(node.label || `entry ${i + 1}`);
    const learnerState = isPrimed
      ? status
      : (isReady ? 'ready for first attempt' : 'locked');
    const ariaLabel = `${node.label || 'entry'}, ${learnerState}${isActive ? ', current' : ''}`;
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

  const stripNodesHtml = backbone.length > 0
    ? stripNodes
    : `<g class="concept-strip__node concept-strip__node--ready is-active" role="button" tabindex="0" data-entry-id="core-thesis" data-entry-index="0" aria-label="core thesis, ready for first attempt, current"><rect x="${padX - 14}" y="${strokeY - 14}" width="28" height="28" fill="transparent" pointer-events="all"></rect><circle cx="${padX}" cy="${strokeY}" r="9"></circle><text x="${padX}" y="${strokeY + 25}">core thesis</text></g>`;

  const stripEdges = backbone.slice(1).map((_, i) => {
    const x1 = padX + i * stepX;
    const x2 = padX + (i + 1) * stepX;
    const isActiveEdge = i + 1 === activeIdx;
    return `<line class="concept-strip__edge${isActiveEdge ? ' is-active' : ''}" x1="${x1}" y1="${strokeY}" x2="${x2}" y2="${strokeY}"></line>`;
  }).join('');

  const stripActiveLabel = activeEntry.label
    ? `${escHtml(activeEntry.label)} · ${activeIdx + 1} of ${totalNodes}`
    : `${activeIdx + 1} of ${totalNodes}`;

  return `
    <div class="concept-strip">
      <div class="concept-strip__inner">
        <div class="concept-strip__tooltip" id="concept-strip-tooltip" hidden></div>
        <svg class="concept-strip__svg" viewBox="0 0 ${stripWidth} ${stripHeight}" preserveAspectRatio="xMidYMid meet">
          ${stripEdges}
          ${stripNodesHtml}
        </svg>
        <div class="concept-strip__overlay">
          <span class="eyebrow">draft route</span>
          <span class="concept-strip__active-name">${stripActiveLabel}</span>
        </div>
      </div>
    </div>
  `;
}

export function renderActiveEntryHtml(activeEntry, activeIdx, backbone, concept, data) {
  const meta = data?.metadata || {};
  const thresholdText = (concept?.startingMapContext || meta.starting_map_context || meta.core_thesis || '').trim();
  const totalNodes = backbone.length || 1;

  // A locked entry is blocked only if any predecessor in the backbone has not
  // yet been attempted. Entry 0 has no predecessors, so it remains attemptable.
  const isLocked = (activeEntry.drill_status || 'locked') === 'locked';
  const predecessorsAttempted = activeIdx === 0 || backbone
    .slice(0, activeIdx)
    .every((n) => (n?.drill_status || 'locked') !== 'locked');
  const isBlocked = isLocked && !predecessorsAttempted;

  const entryEyebrow = isBlocked
    ? `locked entry ${activeIdx + 1} of ${totalNodes}`
    : (activeEntry.drill_status === 'primed'
      ? `re-drill ready entry ${activeIdx + 1} of ${totalNodes}`
      : `first cold attempt entry ${activeIdx + 1} of ${totalNodes}`);
  const entryPurpose = activeEntry.purpose
    || (isBlocked
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

  const ctaButton = isBlocked
    ? `<button class="concept-page-b2__entry-cta concept-page-b2__entry-cta--disabled" type="button" disabled aria-disabled="true" title="Cold attempt on the entry above unlocks this one">Locked</button>`
    : `<button class="concept-page-b2__entry-cta" type="button" data-active-entry-id="${escHtml(activeEntry.id || 'core-thesis')}">${ctaLabel}</button>`;

  const activeHtml = `
    <span class="eyebrow concept-page-b2__entry-eyebrow">${escHtml(entryEyebrow)}</span>
    <h2 class="concept-page-b2__entry-title">${escHtml(activeEntry.label || 'Core thesis')}</h2>
    <p class="concept-page-b2__entry-purpose">${escHtml(entryPurpose)}</p>
    ${ctaButton}
  `;

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
