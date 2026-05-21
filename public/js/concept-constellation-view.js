import { escHtml } from './html.js';
import {
  deriveConceptEntries,
  deriveConceptEntryViewState,
  getConceptEntryId,
} from './concept-page-view.js';

const SVG_WIDTH = 800;
const SVG_HEIGHT = 560;
const CENTER = { x: 400, y: 282 };
const BACKBONE_RADIUS = 190;

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function degToRad(degrees) {
  return (degrees * Math.PI) / 180;
}

function polar(origin, radius, angleDegrees) {
  const angle = degToRad(angleDegrees);
  return {
    x: origin.x + Math.cos(angle) * radius,
    y: origin.y + Math.sin(angle) * radius,
  };
}

function resolveAngularSpread(count) {
  if (count <= 1) return 0;
  return clamp(42 * (count - 1), 86, 230);
}

function resolveBackboneAngles(count) {
  if (count <= 1) return [0];
  const spread = resolveAngularSpread(count);
  const start = -90 - (spread / 2);
  const step = spread / Math.max(1, count - 1);
  return Array.from({ length: count }, (_, index) => start + (step * index));
}

function buildCurvePath(from, to) {
  const mid = {
    x: (from.x + to.x) / 2,
    y: (from.y + to.y) / 2,
  };
  const pull = {
    x: CENTER.x + ((mid.x - CENTER.x) * 0.32),
    y: CENTER.y + ((mid.y - CENTER.y) * 0.32),
  };
  return [
    `M ${from.x.toFixed(1)} ${from.y.toFixed(1)}`,
    `C ${pull.x.toFixed(1)} ${pull.y.toFixed(1)}`,
    `${pull.x.toFixed(1)} ${pull.y.toFixed(1)}`,
    `${to.x.toFixed(1)} ${to.y.toFixed(1)}`,
  ].join(' ');
}

function diamondPath(size = 22) {
  const side = size * 0.82;
  return `M 0 ${-size} L ${side.toFixed(1)} 0 L 0 ${size} L ${(-side).toFixed(1)} 0 Z`;
}

function hashText(value) {
  return String(value || '').split('').reduce((hash, char) => {
    return ((hash << 5) - hash + char.charCodeAt(0)) >>> 0;
  }, 2166136261);
}

function seededRandom(seed) {
  let state = seed >>> 0;
  return () => {
    state = (state * 1664525 + 1013904223) >>> 0;
    return state / 4294967296;
  };
}

function buildStars(entries) {
  const seed = entries.reduce((acc, entry, index) => {
    return acc ^ hashText(getConceptEntryId(entry, index));
  }, 0x9e3779b9);
  const random = seededRandom(seed);
  const count = clamp(14 + (entries.length * 4), 14, 38);
  return Array.from({ length: count }, () => ({
    x: 42 + random() * (SVG_WIDTH - 84),
    y: 30 + random() * (SVG_HEIGHT - 60),
    r: 0.8 + random() * 1.6,
    opacity: 0.22 + random() * 0.42,
  }));
}

function organicOffset(entry, index) {
  const random = seededRandom(hashText(`${getConceptEntryId(entry, index)}:${index}`));
  return {
    x: (random() - 0.5) * 34,
    y: (random() - 0.5) * 28,
  };
}

function resolveNodePosition(entries, entry, index, angles) {
  if (entries.length === 1) return { ...CENTER };
  const base = polar(CENTER, BACKBONE_RADIUS, angles[index]);
  const offset = organicOffset(entry, index);
  return {
    x: clamp(base.x + offset.x, 96, SVG_WIDTH - 96),
    y: clamp(base.y + offset.y, 92, SVG_HEIGHT - 92),
  };
}

function entryFallbackLabel(index) {
  return `Entry ${String(index + 1).padStart(2, '0')}`;
}

function entryRealLabel(entry, index) {
  const label = String(entry?.label || '').trim();
  return label || entryFallbackLabel(index);
}

function entrySafeLabel(entry, index) {
  const scaffold = entry?.learner_scaffold && typeof entry.learner_scaffold === 'object'
    ? entry.learner_scaffold
    : null;
  const scaffoldLabel = String(scaffold?.task_label || scaffold?.learner_move || '').trim();
  if (scaffoldLabel) return scaffoldLabel;

  const label = entryRealLabel(entry, index);
  const clusterLabel = String(entry?.cluster_label || '').trim();
  const title = String(entry?.title || '').trim();
  if (!label || label === clusterLabel || label === title) return entryFallbackLabel(index);
  return label;
}

function entrySafePurpose(entry, viewState, index, isActive) {
  const selectable = isActive || viewState.attempted || (index === 0 && viewState.state === 'ready to reconstruct');
  if (!selectable) {
    return 'Future room. Study stays hidden until you draft from memory.';
  }

  const scaffold = entry?.learner_scaffold && typeof entry.learner_scaffold === 'object'
    ? entry.learner_scaffold
    : null;
  const scaffoldCue = String(scaffold?.task_cue || '').trim();
  if (scaffoldCue) return scaffoldCue;

  return index === 0
    ? 'Write the first useful reconstruction before study appears.'
    : 'Use this room to extend the route without reading ahead.';
}

function entryForTrainingState(entry) {
  if (!entry || typeof entry !== 'object') return entry;
  const {
    drill_status,
    drill_phase,
    re_drill_eligible_after,
    study_completed_at,
    last_drilled,
    ...safeEntry
  } = entry;
  return safeEntry;
}

function canShowEntryLabel(viewState, index, isActive) {
  const isLockedFuture = index > 0 && viewState.state === 'locked' && !viewState.attempted;
  if (isLockedFuture) return false;
  return Boolean(
    isActive
    || viewState.attempted
    || (index === 0 && viewState.state === 'ready to reconstruct')
  );
}

function stateClass(viewState, isActive) {
  return isActive ? 'is-active' : '';
}

function displayState(viewState) {
  if (viewState.state === 'ready to reconstruct') return 'ready';
  if (viewState.state === 'needs repair') return 'needs-repair';
  if (viewState.state === 'solidified') return 'solidified';
  if (viewState.state === 'primed') return 'primed';
  if (viewState.attempted) return 'primed';
  return 'locked';
}

function displayStateLabel(viewState) {
  const state = displayState(viewState);
  if (state === 'ready') return 'ready to reconstruct';
  if (state === 'primed') return 'primed for study';
  if (state === 'needs-repair') return 'needs repair';
  if (state === 'solidified') return 'solidified through spaced reconstruction';
  return 'future room';
}

function buildConstellationModel(entries, training, activeEntryId, options = {}) {
  const stateEntries = entries.map(entryForTrainingState);
  const angles = resolveBackboneAngles(entries.length);
  const nodes = entries.map((entry, index) => {
    const id = getConceptEntryId(entry, index);
    const viewState = deriveConceptEntryViewState(stateEntries, index, training, options);
    const isActive = id === activeEntryId;
    const position = resolveNodePosition(entries, entry, index, angles);
    const label = canShowEntryLabel(viewState, index, isActive)
      ? entrySafeLabel(entry, index)
      : entryFallbackLabel(index);
    const purpose = entrySafePurpose(entry, viewState, index, isActive);
    return {
      id,
      index,
      label,
      purpose,
      position,
      viewState,
      isActive,
      className: stateClass(viewState, isActive),
    };
  });

  return {
    nodes,
    selectedNode: nodes.find((node) => node.isActive) || nodes[0] || null,
    stars: buildStars(entries),
  };
}

function renderStars(stars) {
  return stars.map((star) => `
    <circle
      class="concept-constellation__star"
      cx="${star.x.toFixed(1)}"
      cy="${star.y.toFixed(1)}"
      r="${star.r.toFixed(1)}"
      opacity="${star.opacity.toFixed(2)}"
    />
  `).join('');
}

function renderConnectors(nodes) {
  return nodes.slice(1).map((node, index) => {
    const previous = nodes[index];
    const fromIndex = previous.index;
    const toIndex = node.index;
    const hasEvidence = Boolean(previous.viewState.attempted && node.viewState.attempted);
    const className = [
      'concept-constellation__edge',
      hasEvidence ? 'is-lit' : '',
    ].filter(Boolean).join(' ');
    return `
      <path
        class="${className}"
        data-edge="${fromIndex}-${toIndex}"
        data-edge-evidence="${hasEvidence ? 'true' : 'false'}"
        d="${buildCurvePath(previous.position, node.position)}"
        aria-hidden="true"
      />
    `;
  }).join('');
}

function renderNode(node) {
  const label = escHtml(node.label);
  const purpose = escHtml(node.purpose);
  const state = escHtml(displayState(node.viewState));
  const stateLabel = escHtml(displayStateLabel(node.viewState));
  const entryId = escHtml(node.id);
  const selectable = state !== 'locked';
  const ariaLabel = escHtml(`${node.label}, ${stateLabel}${node.isActive ? ', current room' : ''}`);
  const className = ['concept-constellation__node', node.className].filter(Boolean).join(' ');
  return `
    <g
      class="${className}"
      data-entry-id="${entryId}"
      data-entry-index="${node.index}"
      data-state="${state}"
      data-state-label="${stateLabel}"
      data-selected-name="${label}"
      data-selected-purpose="${purpose}"
      role="${selectable ? 'button' : 'listitem'}"
      tabindex="${selectable ? '0' : '-1'}"
      focusable="${selectable ? 'true' : 'false'}"
      aria-label="${ariaLabel}"
      transform="translate(${node.position.x.toFixed(1)} ${node.position.y.toFixed(1)})"
    >
      <circle class="concept-constellation__halo" r="42" aria-hidden="true" />
      <path class="concept-constellation__dot" d="${diamondPath(node.isActive ? 26 : 22)}" aria-hidden="true" />
      <path class="concept-constellation__facet" d="M 0 -22 L 0 22 M -18 0 L 18 0" aria-hidden="true" />
      <text class="concept-constellation__index" x="-44" y="-34">${String(node.index + 1).padStart(2, '0')}</text>
      <text class="concept-constellation__label" y="52" text-anchor="middle">${label}</text>
    </g>
  `;
}

function renderSelectedDetail(node) {
  if (!node) return '';
  const title = escHtml(node.label);
  const purpose = escHtml(node.purpose);
  const state = escHtml(displayStateLabel(node.viewState));
  return `
    <article class="concept-constellation__selected" aria-live="polite">
      <span class="eyebrow" data-constellation-selected-state>${state}</span>
      <h4 data-constellation-selected-name>${title}</h4>
      <p data-constellation-selected-purpose>${purpose}</p>
      <div class="concept-constellation__selected-actions">
        <button class="concept-constellation__return" type="button" data-map-mode="route">Return to route</button>
      </div>
    </article>
  `;
}

function renderConstellation(model) {
  return `
    <div class="concept-constellation__shell" aria-label="Concept constellation">
      <div class="concept-constellation__copy">
        <span class="eyebrow">constellation</span>
        <h3>Concept constellation</h3>
        <p>Draft structure only. The route remains where you reconstruct from memory.</p>
      </div>
      <div class="concept-constellation__note">
        <strong>Overview first.</strong>
        <span>Select a room to orient, then return to the route to write.</span>
      </div>
      <svg
          class="concept-constellation__svg"
          viewBox="0 0 ${SVG_WIDTH} ${SVG_HEIGHT}"
          aria-labelledby="concept-constellation-title concept-constellation-desc"
          xmlns="http://www.w3.org/2000/svg"
        >
          <title id="concept-constellation-title">Concept constellation</title>
          <desc id="concept-constellation-desc">A draft map of concept rooms. Future rooms hide study content until reconstruction evidence exists.</desc>
          <g class="concept-constellation__stars" aria-hidden="true">
            ${renderStars(model.stars)}
          </g>
          <g class="concept-constellation__links" aria-hidden="true">
            ${renderConnectors(model.nodes)}
          </g>
          <g class="concept-constellation__entries" role="list">
            ${model.nodes.map(renderNode).join('')}
          </g>
        </svg>
      ${renderSelectedDetail(model.selectedNode)}
    </div>
  `;
}

export function renderConceptConstellationHtml(data = {}, options = {}) {
  const entries = deriveConceptEntries(data);
  const training = options.training || null;
  const activeEntryId = options.activeEntryId || getConceptEntryId(entries[0], 0);
  const model = buildConstellationModel(entries, training, activeEntryId, options);
  return renderConstellation(model);
}
