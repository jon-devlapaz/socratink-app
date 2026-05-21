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

export function deriveConceptBadge(concept, training = null, options = {}) {
  if (!training) return null;
  const graphData = parseConceptGraphData(concept);
  const nodeIds = collectTrainingNodeIds(graphData, training);
  return deriveConceptStatus(training, nodeIds, options).badge;
}
