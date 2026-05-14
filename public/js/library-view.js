import { escHtml } from './html.js';

export function getLibraryConceptMeta(concept) {
  let graph = null;
  try {
    graph = typeof concept.graphData === 'string' ? JSON.parse(concept.graphData) : concept.graphData;
  } catch {
    graph = null;
  }

  const metadata = graph?.metadata || {};
  const clusters = Array.isArray(graph?.clusters) ? graph.clusters : [];
  const subnodeCount = clusters.reduce((total, cluster) => total + ((cluster.subnodes || []).length), 0);
  const thesis = metadata.core_thesis || concept.contentPreview || 'No summary available yet.';
  const sourceLabel = concept.contentFilename
    ? `Source: ${concept.contentFilename}`
    : concept.contentType
      ? `Source: ${concept.contentType.toUpperCase()}`
      : (metadata.source_title ? `Map: ${metadata.source_title}` : 'Draft map');

  return {
    thesis: thesis.length > 180 ? `${thesis.slice(0, 177).trimEnd()}...` : thesis,
    architecture: metadata.architecture_type ? metadata.architecture_type.replace(/_/g, ' ') : null,
    difficulty: metadata.difficulty || null,
    clusterCount: clusters.length,
    subnodeCount,
    sourceLabel,
  };
}

export function buildLibraryHtml(concepts) {
  let html = `
      <div class="library-kicker">Library</div>

      <div class="library-section">
        <h2 class="library-section-title">Your Library</h2>
        <p class="library-section-copy">Your library shows what you've reconstructed, not what you've saved.</p>
    `;

  if (concepts.length === 0) {
    html += `
        <div class="library-empty library-empty--ignition">
          <div class="witness-anchor" aria-hidden="true">
            <svg viewBox="0 0 28 28" width="28" height="28">
              <polygon class="witness-anchor__shape" points="14,2 26,14 14,26 2,14"/>
            </svg>
          </div>
          <h3 class="library-empty-headline">Begin a reconstruction.</h3>
          <p class="library-empty-sub">Drop a topic. The drill makes the gap inspectable.</p>
          <button type="button" class="ig-button" onclick="App.showIgnition()">New concept</button>
        </div>`;
  } else {
    html += `<div class="library-vault-grid">` + concepts.map(c => {
      const meta = getLibraryConceptMeta(c);
      return `
          <div class="library-card library-card-vault" data-state="${escHtml(c.state || '')}" data-concept-id="${escHtml(String(c?.id ?? ''))}" style="cursor:pointer;" onclick="App.openLibraryConcept(this.dataset.conceptId)">
            <div class="library-card-header">
              <div>
                <div class="library-card-kicker">${escHtml(meta.sourceLabel)}</div>
                <span class="library-card-name">${escHtml(c.name)}</span>
              </div>
              <span class="library-card-state">${escHtml(c.state)}</span>
            </div>
            <p class="library-card-summary">${escHtml(meta.thesis)}</p>
            <div class="library-card-meta">
              ${meta.architecture ? `<span class="library-card-pill">${escHtml(meta.architecture)}</span>` : ''}
              ${meta.difficulty ? `<span class="library-card-pill">${escHtml(meta.difficulty)}</span>` : ''}
              <span class="library-card-pill">${escHtml(`${meta.clusterCount} ${meta.clusterCount === 1 ? 'section' : 'sections'}`)}</span>
              <span class="library-card-pill">${escHtml(`${meta.subnodeCount} ${meta.subnodeCount === 1 ? 'entry' : 'entries'}`)}</span>
            </div>
            <div class="library-card-cta">Open concept</div>
          </div>`;
    }).join('') + `</div>`;
  }

  html += `</div>`;
  return html;
}
