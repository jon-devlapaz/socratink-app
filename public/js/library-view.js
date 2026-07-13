import { escHtml } from './html.js';
import { deriveConceptBadge, parseConceptGraphData } from './concept-status.js';

const EMPTY_RECONSTRUCTION_COPY = 'Your first reconstruction will appear here.';

const ATTEMPT_CLASSIFICATION_RANK = {
  strong: 4,
  solid: 4,
  partial: 3,
  deep: 3,
  thin: 2,
  shallow: 2,
  wrong_direction: 1,
  misconception: 1,
};

function conceptStateLabel(state) {
  if (state === 'primed') return 'draft saved';
  if (state === 'solidified') return 'solid spaced reconstruction';
  return state;
}

function rankAttempt(attempt) {
  return ATTEMPT_CLASSIFICATION_RANK[attempt?.classification] || 0;
}

export function getBestLearnerAttempt(training) {
  const records = training?.node_records && typeof training.node_records === 'object'
    ? training.node_records
    : {};

  const attempts = Object.values(records)
    .flatMap((record) => Array.isArray(record?.attempts) ? record.attempts : [])
    .filter((attempt) => typeof attempt?.user_text === 'string' && attempt.user_text.trim() !== '');

  if (!attempts.length) return null;

  return [...attempts].sort((a, b) => {
    const rankDelta = rankAttempt(b) - rankAttempt(a);
    if (rankDelta !== 0) return rankDelta;
    const bMs = Date.parse(b?.at || '');
    const aMs = Date.parse(a?.at || '');
    return (Number.isFinite(bMs) ? bMs : 0) - (Number.isFinite(aMs) ? aMs : 0);
  })[0];
}

export function getLibraryConceptMeta(concept, training = null) {
  const graph = parseConceptGraphData(concept);

  const metadata = graph?.metadata || {};
  const clusters = Array.isArray(graph?.clusters) ? graph.clusters : [];
  const subnodeCount = clusters.reduce((total, cluster) => total + ((cluster.subnodes || []).length), 0);
  const bestAttempt = getBestLearnerAttempt(training);
  const thesis = bestAttempt?.user_text || EMPTY_RECONSTRUCTION_COPY;
  const sourceLabel = concept.contentFilename
    ? `Source: ${concept.contentFilename}`
    : concept.contentType
      ? `Source: ${concept.contentType.toUpperCase()}`
      : (metadata.source_title ? `Map: ${metadata.source_title}` : 'Draft map');

  return {
    thesis: thesis.length > 180 ? `${thesis.slice(0, 177).trimEnd()}...` : thesis,
    summarySource: bestAttempt ? 'learner_attempt' : 'none',
    architecture: metadata.architecture_type ? metadata.architecture_type.replace(/_/g, ' ') : null,
    difficulty: metadata.difficulty || null,
    clusterCount: clusters.length,
    subnodeCount,
    sourceLabel,
  };
}

export function buildLibraryHtml(concepts, trainingByConceptId = {}, options = {}) {
  const showLocalQaSeed = options?.showLocalQaSeed === true;
  const conceptCount = concepts.length;
  let html = `
      <div class="library-shell">
        <h2 class="library-page-title">Library</h2>
        ${showLocalQaSeed ? `
          <div class="library-qa-actions">
            <button type="button" class="ig-button" data-local-qa-seed onclick="App.seedLocalQaConcept()">Seed QA concept</button>
            <button type="button" class="ig-button" data-local-repair-qa-seed onclick="App.seedLocalRepairQaConcept()">Seed repair QA</button>
          </div>
        ` : ''}
        <section class="library-section${conceptCount === 0 ? ' library-section--empty' : ''}" aria-labelledby="library-concepts-title">
          <header class="library-index-header">
            <h3 class="library-index-title" id="library-concepts-title">Concepts</h3>
            <span class="library-index-count" aria-label="${conceptCount} ${conceptCount === 1 ? 'concept' : 'concepts'}">${conceptCount}</span>
          </header>
    `;

  if (conceptCount === 0) {
    html += `
        <div class="library-index-empty">
          <svg class="library-index-empty__icon" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M12 7v14"/>
            <path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z"/>
          </svg>
          <div class="library-index-empty__copy">
            <h4 class="library-index-empty__title">Your first reconstruction starts here</h4>
            <p class="library-index-empty__description">Write from memory. Your reconstruction will appear here.</p>
          </div>
          <button type="button" class="library-index-empty__action" onclick="App.showIgnition()">Start learning</button>
        </div>`;
  } else {
    html += `<div class="library-vault-grid">` + concepts.map(c => {
      const conceptId = String(c?.id ?? '');
      const conceptName = String(c?.name ?? '');
      const training = trainingByConceptId[conceptId] || null;
      const meta = getLibraryConceptMeta(c, training);
      const derivedState = deriveConceptBadge(c, training) || '';
      const stateBadge = derivedState
        ? `<span class="library-card-state" data-state="${escHtml(derivedState)}">${escHtml(conceptStateLabel(derivedState))}</span>`
        : '';
      return `
          <div class="library-card library-card-vault" role="button" tabindex="0" aria-label="Open concept ${escHtml(conceptName)}" data-state="${escHtml(derivedState)}" data-concept-id="${escHtml(conceptId)}" style="cursor:pointer;" onclick="App.openLibraryConcept(this.dataset.conceptId)" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();App.openLibraryConcept(this.dataset.conceptId)}">
            <div class="library-card-header">
              <div>
                <div class="library-card-kicker">${escHtml(meta.sourceLabel)}</div>
                <span class="library-card-name">${escHtml(conceptName)}</span>
              </div>
              ${stateBadge}
            </div>
            <p class="library-card-summary">${escHtml(meta.thesis)}</p>
            <div class="library-card-meta">
              ${meta.architecture ? `<span class="library-card-pill">${escHtml(meta.architecture)}</span>` : ''}
              <span class="library-card-pill">${escHtml(`${meta.clusterCount} ${meta.clusterCount === 1 ? 'section' : 'sections'}`)}</span>
              <span class="library-card-pill">${escHtml(`${meta.subnodeCount} ${meta.subnodeCount === 1 ? 'entry' : 'entries'}`)}</span>
            </div>
            <div class="library-card-cta">Open concept</div>
          </div>`;
    }).join('') + `</div>`;
  }

  html += `</section></div>`;
  return html;
}
