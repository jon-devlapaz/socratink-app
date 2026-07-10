const ROUTE_BOUND_NODE_KEY = 'seda_route_bound_node_id';
const ROUTE_BOUND_SESSION_KEY = 'seda_route_bound_session_id';
export const SOURCE_LESS_ROUTE_CONTRACT_VERSION = 1;

function clean(value) {
  return typeof value === 'string' ? value.trim() : '';
}

function invalidRoute(reason) {
  const error = new Error(`Invalid source-less SEDA route: ${reason}`);
  error.code = 'route_unavailable';
  error.reason = reason;
  return error;
}

export function hasBoundSourceLessSedaRoute(graphData) {
  return Boolean(boundSourceLessSedaNodeId(graphData));
}

export function boundSourceLessSedaNodeId(graphData) {
  return clean(graphData?.metadata?.[ROUTE_BOUND_NODE_KEY]);
}

export function boundSourceLessSedaSessionId(graphData) {
  return clean(graphData?.metadata?.[ROUTE_BOUND_SESSION_KEY]);
}

export function clearBoundSourceLessSedaRoute(graphData) {
  const metadata = graphData?.metadata && typeof graphData.metadata === 'object'
    ? { ...graphData.metadata }
    : {};
  delete metadata[ROUTE_BOUND_NODE_KEY];
  delete metadata[ROUTE_BOUND_SESSION_KEY];
  return {
    ...(graphData || {}),
    metadata: {
      ...metadata,
      route_status: 'pending_seda',
      graph_neutral: true,
    },
  };
}

export function readySourceLessSedaRoute(data) {
  const result = data?.sourceLessRoute;
  if (result?.status === 'route_unavailable' || result?.code === 'route_unavailable') {
    throw invalidRoute(result.reason || 'route_unavailable');
  }
  if (!result || typeof result !== 'object') throw invalidRoute('missing sourceLessRoute result');
  if (result.contractVersion !== SOURCE_LESS_ROUTE_CONTRACT_VERSION) {
    throw invalidRoute('unsupported sourceLessRoute contractVersion');
  }
  if (result.status !== 'ready') throw invalidRoute('sourceLessRoute is not ready');
  if (data?.awaiting?.key !== 'cold_attempt') {
    throw invalidRoute('ready route must await cold_attempt');
  }
  return {
    first_node: result.firstNode,
    provisional_map: result.provisionalMap,
  };
}

function appMetadata(existingMap, concept) {
  const metadata = existingMap?.metadata && typeof existingMap.metadata === 'object'
    ? existingMap.metadata
    : {};
  const values = {
    starting_map_context: clean(concept?.startingMapContext)
      || clean(metadata.starting_map_context),
    source_mode: clean(concept?.sourceMode)
      || clean(concept?.source_mode)
      || clean(metadata.source_mode)
      || 'source_less',
    map_maturity: clean(metadata.map_maturity) || clean(concept?.mapMaturity),
    learner_goal: clean(concept?.learnerGoal) || clean(metadata.learner_goal),
  };
  return Object.fromEntries(Object.entries(values).filter(([, value]) => value));
}

function boundNode(target, firstNode) {
  const scaffold = target?.learner_scaffold && typeof target.learner_scaffold === 'object'
    ? target.learner_scaffold
    : {};
  const evidenceGoal = clean(firstNode.evidence_goal) || clean(scaffold.evidence_goal);
  return {
    ...target,
    id: clean(firstNode.id),
    label: clean(firstNode.label),
    mechanism: clean(firstNode.mechanism),
    study_note: clean(firstNode.mechanism),
    purpose: evidenceGoal || clean(target?.purpose),
    learner_scaffold: {
      ...scaffold,
      task_label: clean(scaffold.task_label) || clean(firstNode.label),
      task_cue: clean(scaffold.task_cue) || evidenceGoal,
      entry_prompt: clean(firstNode.learner_prompt),
      evidence_goal: evidenceGoal,
    },
  };
}

/** Bind the first source-less Door session to the route SEDA actually chose. */
export function bindSourceLessSedaRoute({ data, existingMap = null, concept = null } = {}) {
  const sessionId = clean(data?.sessionId);
  if (!sessionId) throw invalidRoute('missing sessionId');
  const route = readySourceLessSedaRoute(data);
  const firstNode = route.first_node;
  const routeMap = route.provisional_map;
  if (!firstNode || typeof firstNode !== 'object') throw invalidRoute('missing first_node');
  for (const field of ['id', 'label', 'learner_prompt', 'mechanism']) {
    if (!clean(firstNode[field])) throw invalidRoute(`missing first_node.${field}`);
  }
  if (!routeMap || typeof routeMap !== 'object') throw invalidRoute('missing provisional_map');
  if (!Array.isArray(routeMap.backbone) || routeMap.backbone.length === 0) {
    throw invalidRoute('provisional_map.backbone must be non-empty');
  }
  if (!Array.isArray(routeMap.clusters)) {
    throw invalidRoute('provisional_map.clusters must be an array');
  }

  const firstNodeId = clean(firstNode.id);
  let matches = 0;
  let nodeType = null;
  const bindMatch = (node, type) => {
    if (clean(node?.id) !== firstNodeId) return { ...node };
    matches += 1;
    nodeType = type;
    return boundNode(node, firstNode);
  };
  const backbone = routeMap.backbone.map((node) => bindMatch(node, 'backbone'));
  const clusters = routeMap.clusters.map((cluster) => ({
    ...cluster,
    subnodes: Array.isArray(cluster?.subnodes)
      ? cluster.subnodes.map((node) => bindMatch(node, 'subnode'))
      : [],
  }));
  if (matches !== 1) {
    throw invalidRoute(matches ? 'first_node.id is duplicated in provisional_map' : 'first_node.id is absent from provisional_map');
  }

  const evidenceGoal = clean(firstNode.evidence_goal);
  return {
    graphData: {
      ...routeMap,
      metadata: {
        ...(routeMap.metadata && typeof routeMap.metadata === 'object' ? routeMap.metadata : {}),
        ...appMetadata(existingMap, concept),
        [ROUTE_BOUND_NODE_KEY]: firstNodeId,
        [ROUTE_BOUND_SESSION_KEY]: sessionId,
      },
      backbone,
      clusters,
    },
    nodeContext: {
      id: firstNodeId,
      type: nodeType,
      label: clean(firstNode.label),
      fullLabel: clean(firstNode.label),
      detail: clean(firstNode.mechanism),
      prompt: clean(firstNode.learner_prompt),
      purpose: evidenceGoal,
      learner_scaffold: {
        task_label: clean(firstNode.label),
        task_cue: evidenceGoal,
        entry_prompt: clean(firstNode.learner_prompt),
        evidence_goal: evidenceGoal,
      },
    },
  };
}
