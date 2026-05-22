import { deriveConceptStatus } from './training-derive.js';

export function parseConceptGraphData(concept) {
  if (!concept?.graphData) return null;
  try {
    return typeof concept.graphData === 'string'
      ? JSON.parse(concept.graphData)
      : concept.graphData;
  } catch {
    return null;
  }
}

export function collectTrainingNodeIds(graphData, training = null) {
  const ids = [];
  const addId = (value) => {
    if (typeof value !== 'string' || value.trim() === '') return;
    if (!ids.includes(value)) ids.push(value);
  };

  (graphData?.backbone || []).forEach((item) => addId(item?.id));
  (graphData?.clusters || []).forEach((cluster) => {
    addId(cluster?.id);
    (cluster?.subnodes || []).forEach((subnode) => addId(subnode?.id));
  });

  if (!ids.length && training?.node_records && typeof training.node_records === 'object') {
    Object.keys(training.node_records).forEach(addId);
  }

  return ids;
}

function legacyBadgeForDrillStatus(status) {
  const normalized = String(status || '').toLowerCase();
  if (normalized === 'solidified' || normalized === 'solid') return 'solidified';
  if (normalized === 'drilled') return 'needs repair';
  if (normalized === 'primed') return 'primed';
  return null;
}

function deriveLegacyConceptBadge(graphData) {
  const badges = [];
  const addBadge = (status) => {
    const badge = legacyBadgeForDrillStatus(status);
    if (badge) badges.push(badge);
  };

  addBadge(graphData?.metadata?.drill_status);
  (graphData?.backbone || []).forEach((item) => addBadge(item?.drill_status));
  (graphData?.clusters || []).forEach((cluster) => {
    addBadge(cluster?.drill_status);
    (cluster?.subnodes || []).forEach((subnode) => addBadge(subnode?.drill_status));
  });

  if (badges.includes('needs repair')) return 'needs repair';
  if (badges.includes('primed')) return 'primed';
  if (badges.includes('solidified')) return 'solidified';
  return null;
}

export function deriveConceptBadge(concept, training = null, options = {}) {
  const graphData = parseConceptGraphData(concept);
  const nodeIds = collectTrainingNodeIds(graphData, training);
  const badge = training ? deriveConceptStatus(training, nodeIds, options).badge : null;
  return badge || deriveLegacyConceptBadge(graphData);
}
