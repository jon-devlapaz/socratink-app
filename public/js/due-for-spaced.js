import { deriveNodeTraining } from './training-derive.js';
import {
  deriveConceptEntries,
  getConceptEntryId,
} from './concept-page-view.js';

function parseGraphData(raw) {
  if (!raw) return null;
  if (typeof raw === 'object') return raw;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

/**
 * Drillable IDs must match concept-page route entries exactly
 * (`deriveConceptEntries`). Never invent IDs the map cannot focus.
 */
export function collectDrillableNodeIds(graphData) {
  if (!graphData || typeof graphData !== 'object') return [];
  const entries = deriveConceptEntries(graphData);
  if (!entries.length) return ['core-thesis'];
  return entries.map((entry, index) => getConceptEntryId(entry, index));
}

function labelForNode(graphData, nodeId) {
  const entries = deriveConceptEntries(graphData || {});
  const match = entries.find((entry, index) => getConceptEntryId(entry, index) === nodeId);
  if (match) {
    return match.label || match.name || nodeId;
  }
  if (nodeId === 'core-thesis') {
    return graphData?.metadata?.label
      || graphData?.metadata?.name
      || graphData?.metadata?.source_title
      || 'Core thesis';
  }
  return nodeId;
}

/**
 * Due means deriveNodeTraining(...).next_action === 'spaced_attempt'.
 * Oldest-due first.
 */
export function listDueForSpaced({
  concepts = [],
  trainingByConceptId = {},
  now = new Date().toISOString(),
} = {}) {
  const due = [];
  (Array.isArray(concepts) ? concepts : []).forEach((concept) => {
    if (!concept?.id) return;
    const graphData = parseGraphData(concept.graphData);
    const training = trainingByConceptId[concept.id] || null;
    const nodeRecords = training?.node_records && typeof training.node_records === 'object'
      ? training.node_records
      : {};
    collectDrillableNodeIds(graphData).forEach((nodeId) => {
      const derived = deriveNodeTraining(nodeRecords[nodeId] || null, { now });
      if (derived.next_action !== 'spaced_attempt') return;
      due.push({
        concept_id: concept.id,
        concept_name: concept.name || concept.title || 'Untitled concept',
        node_id: nodeId,
        node_label: labelForNode(graphData, nodeId),
        last_attempt_at: derived.last_attempt_at,
      });
    });
  });
  return due.sort((a, b) => (Date.parse(a.last_attempt_at || '') || 0) - (Date.parse(b.last_attempt_at || '') || 0));
}

export function dueConceptIdSet(dueItems = []) {
  return new Set(
    (Array.isArray(dueItems) ? dueItems : [])
      .map((item) => item?.concept_id)
      .filter(Boolean),
  );
}

export function dueItemsForConcept(dueItems = [], conceptId) {
  if (!conceptId) return [];
  return (Array.isArray(dueItems) ? dueItems : []).filter((item) => item.concept_id === conceptId);
}

/**
 * Linear-style filter chip. Count is due *sessions* (concepts), matching
 * board marks. Hidden when count is 0.
 */
export function renderReadyFilterHtml({ count = 0, active = false } = {}) {
  if (!count) return '';
  const label = 'Due';
  const ariaLabel = active
    ? `Showing ${count} session${count === 1 ? '' : 's'} due for spaced reconstruction. Clear filter.`
    : `Show only ${count} session${count === 1 ? '' : 's'} due for spaced reconstruction.`;
  return `
    <button
      type="button"
      class="desk-ready-filter${active ? ' is-active' : ''}"
      id="desk-ready-filter"
      aria-pressed="${active ? 'true' : 'false'}"
      aria-label="${ariaLabel}"
      data-ready-count="${count}"
    >
      <span class="desk-ready-filter__label">${label}</span>
      <span class="desk-ready-filter__count">${count}</span>
    </button>
  `;
}

/**
 * Selection strip under the board — one next reconstruction for the
 * selected concept. Empty when the selection has nothing due.
 */
export function renderDueSelectionHtml(dueItems = []) {
  if (!Array.isArray(dueItems) || dueItems.length === 0) return '';
  const next = dueItems[0];
  const meta = dueItems.length > 1
    ? `${dueItems.length} nodes due · oldest first`
    : 'Spacing window open · reconstruct before study';
  const actionLabel = `Reconstruct ${next.node_label} from memory`;

  return `
    <div class="desk-due-selection" data-concept-id="${escapeAttr(next.concept_id)}">
      <div class="desk-due-selection__copy">
        <p class="desk-due-selection__kicker">Up next from memory</p>
        <p class="desk-due-selection__node">${escapeHtml(next.node_label)}</p>
        <span class="desk-due-selection__meta">${meta}</span>
      </div>
      <button
        type="button"
        class="desk-due-selection__action"
        data-concept-id="${escapeAttr(next.concept_id)}"
        data-node-id="${escapeAttr(next.node_id)}"
        aria-label="${escapeAttr(actionLabel)}"
      >
        Reconstruct
      </button>
    </div>
  `;
}

function escapeHtml(value) {
  return String(value || '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

function escapeAttr(value) {
  return escapeHtml(value).replaceAll("'", '&#39;');
}
