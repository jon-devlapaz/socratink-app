import { loadConcepts, getActiveId, setActiveId } from './store.js';
import { escHtml, transformKnowledgeMapToGraph } from './graph-view.js?v=3';
import { buildBrowserLearnerSummaryPayload } from './browser-analytics.js';

let conceptSelect = null;
let statusChip = null;
let statusMeta = null;
let refreshButton = null;

let metricGrid = null;
let truthOverview = null;
let nextBestMove = null;
let revisitQueue = null;
let retrievalHabits = null;
let branchFriction = null;
let conversionHistory = null;
let cadencePanel = null;
let sessionJournal = null;
let analyticsHelpTooltip = null;

let analyticsCallbacks = {
  onConceptChange: null,
};

let dashboardMounted = false;

function cacheDomRefs(root = document) {
  const lookup = (id) => root.getElementById ? root.getElementById(id) : root.querySelector(`#${id}`);
  conceptSelect = lookup('concept-select');
  statusChip = lookup('status-chip');
  statusMeta = lookup('status-meta');
  refreshButton = lookup('refresh-button');
  metricGrid = lookup('metric-grid');
  truthOverview = lookup('truth-overview');
  nextBestMove = lookup('next-best-move');
  revisitQueue = lookup('revisit-queue');
  retrievalHabits = lookup('retrieval-habits');
  branchFriction = lookup('branch-friction');
  conversionHistory = lookup('conversion-history');
  cadencePanel = lookup('cadence-panel');
  sessionJournal = lookup('session-journal');
  analyticsHelpTooltip = lookup('analytics-help-tooltip');
}

function fmtNumber(value, digits = 1) {
  const numeric = Number(value || 0);
  return Number.isFinite(numeric) ? numeric.toFixed(digits) : '0.0';
}

function fmtPercent(value) {
  return `${fmtNumber(value, 1)}%`;
}

function fmtTimestamp(value) {
  if (!value) return 'No activity yet';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

function fmtDayDistance(days) {
  if (days == null) return 'No prior attempt';
  if (days <= 0) return 'today';
  if (days === 1) return '1 day ago';
  return `${days} days ago`;
}

function parseConceptGraphData(concept) {
  if (!concept?.graphData) return null;
  try {
    return typeof concept.graphData === 'string'
      ? JSON.parse(concept.graphData)
      : concept.graphData;
  } catch (error) {
    console.error('Invalid concept graphData', error);
    return null;
  }
}

function getMappedConcepts() {
  return loadConcepts().filter((concept) => Boolean(parseConceptGraphData(concept)));
}

function getCurrentConcept(concepts) {
  const activeId = getActiveId();
  return concepts.find((concept) => concept.id === activeId)
    || concepts[0]
    || null;
}

function createEmptyState(message) {
  return `<div class="empty-state">${escHtml(message)}</div>`;
}

function createMetricCards(items) {
  return items.map((item) => `
    <article class="metric-card">
      <div class="metric-label">${escHtml(item.label)}</div>
      <div class="metric-value">${escHtml(item.value)}</div>
      <div class="metric-note">${escHtml(item.note)}</div>
    </article>
  `).join('');
}

function createStatGrid(items) {
  return `
    <div class="stat-grid">
      ${items.map((item) => `
        <div class="stat-tile">
          <div class="stat-tile-label">${escHtml(item.label)}</div>
          <div class="stat-tile-value">${escHtml(item.value)}</div>
          ${item.note ? `<div class="stat-tile-note">${escHtml(item.note)}</div>` : ''}
        </div>
      `).join('')}
    </div>
  `;
}

function createList(items, emptyMessage, renderItem) {
  if (!items?.length) return createEmptyState(emptyMessage);
  return `<div class="list-stack">${items.map(renderItem).join('')}</div>`;
}

function createBarGroup(title, items) {
  if (!items?.length) return createEmptyState(`${title}: not enough data yet.`);

  const max = Math.max(...items.map((item) => Number(item.value || 0)), 1);
  return `
    <section class="bar-group">
      <div class="stat-tile-label">${escHtml(title)}</div>
      ${items.map((item) => {
        const width = (Number(item.value || 0) / max) * 100;
        return `
          <div class="bar-row">
            <div class="bar-label-row">
              <span class="bar-label">${escHtml(item.label)}</span>
              <span class="bar-value">${escHtml(item.note || String(item.value))}</span>
            </div>
            <div class="bar-track">
              <div class="bar-fill" style="width:${width}%"></div>
            </div>
          </div>
        `;
      }).join('')}
    </section>
  `;
}

function toNodeHistoryMap(items) {
  const map = new Map();
  for (const item of items || []) {
    map.set(`${item.concept_id}::${item.node_id}`, item);
  }
  return map;
}

function toConceptStatsMap(items) {
  const map = new Map();
  for (const item of items || []) {
    map.set(item.concept_id, item);
  }
  return map;
}

function getNodeTypeLabel(type) {
  if (type === 'core') return 'Core thesis';
  if (type === 'backbone') return 'Backbone';
  if (type === 'subnode') return 'Drill node';
  return 'Node';
}

function getStateCounts(nodes) {
  return nodes.reduce((acc, node) => {
    const state = node.state || 'locked';
    if (state === 'primed') {
      acc.primed = (acc.primed || 0) + 1;
      return acc;
    }
    acc[state] = (acc[state] || 0) + 1;
    return acc;
  }, { locked: 0, primed: 0, drilled: 0, solidified: 0 });
}

function getRevisitReason(node, history, dueDays) {
  if ((history?.misconception_count || 0) > 0) {
    return 'A misconception showed up here, so this is the highest-value repair target.';
  }
  if ((history?.non_solid_count || 0) >= 2) {
    return 'This node has stayed unresolved across multiple attempts.';
  }
  if ((history?.days_since_attempt || 0) >= dueDays) {
    return 'This node is due for a spaced return.';
  }
  if ((history?.help_count || 0) > 0) {
    return 'You have leaned on help here; another clean attempt is worth it.';
  }
  return 'This node is still in progress and worth revisiting.';
}

function getAdvanceReason(node) {
  if (node.type === 'core') {
    return 'Start with the core thesis so the rest of the map can open truthfully.';
  }
  if (node.type === 'backbone') {
    return 'This backbone branch is reachable and unlocks its dependent territory.';
  }
  return 'This is the next reachable room in your current branch.';
}

function getNodeRank(node, history, dueDays) {
  let score = 0;
  score += (history?.misconception_count || 0) * 48;
  score += (history?.non_solid_count || 0) * 16;
  score += (history?.help_count || 0) * 6;
  score += Math.min(history?.days_since_attempt || 0, 21);
  if ((history?.days_since_attempt || 0) >= dueDays) score += 12;
  if (node.type === 'subnode') score += 4;
  return score;
}

function buildConceptPayload(concept, remoteData) {
  const graphData = parseConceptGraphData(concept);
  if (!graphData) return null;

  const transformed = transformKnowledgeMapToGraph(graphData);
  const nodeHistoryMap = toNodeHistoryMap(remoteData.node_history || []);
  const conceptStatsMap = toConceptStatsMap(remoteData.concept_stats || []);
  const conceptStats = conceptStatsMap.get(concept.id) || null;
  const dueDays = remoteData.cadence?.revisit_due_days || 3;

  const drillableNodes = transformed.nodes
    .map((node) => node.data)
    .filter((node) => node.type !== 'cluster');
  const stateCounts = getStateCounts(drillableNodes);
  const availableLockedNodes = drillableNodes.filter((node) => node.available && node.state === 'locked');
  const unresolvedNodes = drillableNodes
    .filter((node) => node.state === 'primed' || node.state === 'drilled')
    .map((node) => {
      const history = nodeHistoryMap.get(`${concept.id}::${node.id}`) || {};
      return {
        ...node,
        history,
        score: getNodeRank(node, history, dueDays),
        reason: node.state === 'primed'
          ? 'Study is complete, but this node is still in progress until you return after enough spacing and interleaving.'
          : getRevisitReason(node, history, dueDays),
      };
    })
    .sort((a, b) => b.score - a.score || a.fullLabel.localeCompare(b.fullLabel));

  const nextMove = (() => {
    const nextAvailable = availableLockedNodes[0];
    if (nextAvailable) {
      return {
        label: nextAvailable.fullLabel,
        route: nextAvailable.type === 'subnode' ? 'Continue current path' : 'Open truthful territory',
        reason: getAdvanceReason(nextAvailable),
        nodeType: getNodeTypeLabel(nextAvailable.type),
      };
    }

    const returnCandidate = unresolvedNodes.find((node) => node.state === 'drilled' && (node.history?.days_since_attempt || 0) >= dueDays)
      || unresolvedNodes.find((node) => node.state === 'drilled' && (node.history?.misconception_count || 0) > 0)
      || unresolvedNodes.find((node) => node.state === 'drilled')
      || unresolvedNodes.find((node) => node.state === 'primed');
    if (returnCandidate) {
      return {
        label: returnCandidate.fullLabel,
        route: returnCandidate.state === 'primed' ? 'Let it incubate, then return' : 'Revisit weak point',
        reason: returnCandidate.reason,
        nodeType: getNodeTypeLabel(returnCandidate.type),
      };
    }

    return null;
  })();

  const clusterOwners = new Map();
  for (const backbone of graphData.backbone || []) {
    for (const clusterId of backbone.dependent_clusters || []) {
      const owners = clusterOwners.get(clusterId) || [];
      owners.push(backbone.principle || backbone.id || 'Backbone');
      clusterOwners.set(clusterId, owners);
    }
  }

  const branchRows = (graphData.clusters || []).map((cluster) => {
    const subnodes = cluster.subnodes || [];
    const counts = subnodes.reduce((acc, subnode) => {
      if (subnode.drill_status === 'solid' || subnode.drill_status === 'solidified') {
        acc.solidified += 1;
      } else if (subnode.drill_status === 'primed') {
        acc.primed += 1;
      } else if (subnode.drill_status || subnode.gap_type) {
        acc.drilled += 1;
      } else {
        acc.locked += 1;
      }
      return acc;
    }, { solidified: 0, primed: 0, drilled: 0, locked: 0 });

    const history = subnodes.reduce((acc, subnode) => {
      const row = nodeHistoryMap.get(`${concept.id}::${subnode.id}`) || {};
      acc.attempt_count += row.attempt_count || 0;
      acc.help_count += row.help_count || 0;
      acc.misconception_count += row.misconception_count || 0;
      return acc;
    }, { attempt_count: 0, help_count: 0, misconception_count: 0 });

    return {
      cluster_id: cluster.id,
      label: cluster.label || cluster.id || 'Untitled branch',
      owners: clusterOwners.get(cluster.id) || [],
      counts,
      history,
    };
  }).sort((a, b) => {
    if (b.counts.drilled !== a.counts.drilled) return b.counts.drilled - a.counts.drilled;
    if (b.history.misconception_count !== a.history.misconception_count) {
      return b.history.misconception_count - a.history.misconception_count;
    }
    return a.label.localeCompare(b.label);
  });

  const conceptConversions = (remoteData.conversion_history?.recent_conversions || [])
    .filter((item) => item.concept_id === concept.id);
  const conceptJournal = (remoteData.session_journal || [])
    .filter((item) => item.concept_id === concept.id);
  const conceptDueNodes = (remoteData.cadence?.due_nodes || [])
    .filter((item) => item.concept_id === concept.id);

  return {
    concept,
    graphData,
    truth_overview: {
      state_counts: stateCounts,
      reachable_now: availableLockedNodes.length,
      total_nodes: drillableNodes.length,
    },
    next_best_move: nextMove,
    revisit_queue: unresolvedNodes.slice(0, 6),
    retrieval_habits: {
      attempt_turn_count: conceptStats?.attempt_turn_count || 0,
      help_turn_count: conceptStats?.help_turn_count || 0,
      attempt_before_help_rate: conceptStats?.attempt_before_help_rate || 0,
      verified_reconstruction_rate: conceptStats?.verified_reconstruction_rate || 0,
      active_days_last_14: conceptStats?.active_days_last_14 || 0,
      session_count: conceptStats?.session_count || 0,
    },
    conversion_history: {
      conversion_count: conceptConversions.length,
      recent_conversions: conceptConversions,
    },
    branch_friction: branchRows.slice(0, 6),
    session_journal: conceptJournal.slice(0, 8),
    cadence: {
      revisit_due_days: dueDays,
      latest_activity_at: conceptStats?.latest_activity_at || remoteData.cadence?.latest_activity_at || null,
      overdue_revisit_count: conceptDueNodes.length,
      due_nodes: conceptDueNodes.slice(0, 5),
    },
  };
}

function renderConceptOptions(concepts, activeConcept) {
  if (!conceptSelect) return;
  conceptSelect.innerHTML = concepts.map((concept) => `
    <option value="${escHtml(concept.id)}"${concept.id === activeConcept?.id ? ' selected' : ''}>
      ${escHtml(concept.name)}
    </option>
  `).join('');
}

function renderMetricGrid(payload) {
  const inProgressCount = (payload.truth_overview.state_counts.primed || 0) + (payload.truth_overview.state_counts.drilled || 0);
  metricGrid.innerHTML = createMetricCards([
    {
      label: 'Verified Understanding',
      value: String(payload.truth_overview.state_counts.solidified || 0),
      note: 'Nodes that are genuinely solidified',
    },
    {
      label: 'In Progress',
      value: String(inProgressCount),
      note: 'Primed or unresolved nodes that still need a return',
    },
    {
      label: 'Worth Revisiting',
      value: String(payload.revisit_queue.length),
      note: 'Highest-value unresolved nodes right now',
    },
    {
      label: 'Attempted Before Help',
      value: fmtPercent(payload.retrieval_habits.attempt_before_help_rate),
      note: `${payload.retrieval_habits.attempt_turn_count} attempt turns`,
    },
  ]);
}

function renderTruthOverview(payload) {
  const counts = payload.truth_overview.state_counts;
  const totalNodes = Math.max(payload.truth_overview.total_nodes, 1);
  const inProgressCount = (counts.primed || 0) + (counts.drilled || 0);
  truthOverview.innerHTML = `
    ${createStatGrid([
      {
        label: 'Verified',
        value: String(counts.solidified || 0),
        note: `${fmtPercent(((counts.solidified || 0) / totalNodes) * 100)} of drillable nodes`,
      },
      {
        label: 'In Progress',
        value: String(inProgressCount),
        note: `${counts.primed || 0} primed, ${counts.drilled || 0} unresolved`,
      },
      {
        label: 'Locked',
        value: String(counts.locked || 0),
        note: 'Not yet opened truthfully',
      },
      {
        label: 'Reachable Now',
        value: String(payload.truth_overview.reachable_now || 0),
        note: 'Open nodes you can drill next',
      },
    ])}
    ${createBarGroup('Current Truth', [
      { label: 'Solidified', value: counts.solidified || 0, note: `${counts.solidified || 0} nodes` },
      { label: 'Primed', value: counts.primed || 0, note: `${counts.primed || 0} nodes` },
      { label: 'Drilled', value: counts.drilled || 0, note: `${counts.drilled || 0} nodes` },
      { label: 'Locked', value: counts.locked || 0, note: `${counts.locked || 0} nodes` },
    ])}
  `;
}

function renderNextBestMove(payload) {
  const move = payload.next_best_move;
  if (!move) {
    nextBestMove.innerHTML = createEmptyState('No truthful next move is available yet. Start by drilling the core thesis from the app.');
    return;
  }

  nextBestMove.innerHTML = `
    <article class="callout-card">
      <div class="callout-kicker">${escHtml(move.route)}</div>
      <h3 class="callout-title">${escHtml(move.label)}</h3>
      <p class="callout-copy">${escHtml(move.reason)}</p>
      <div class="list-card-metrics">
        <span class="metric-pill">${escHtml(move.nodeType)}</span>
        <span class="metric-pill">One node at a time</span>
      </div>
    </article>
  `;
}

function renderRevisitQueue(payload) {
  revisitQueue.innerHTML = createList(
    payload.revisit_queue,
    'Nothing is waiting in the revisit queue right now.',
    (item) => `
      <div class="list-card">
        <div class="list-card-title-row">
          <div class="list-card-title">${escHtml(item.fullLabel)}</div>
          <div class="metric-pill">${escHtml(getNodeTypeLabel(item.type))}</div>
        </div>
        <div class="list-card-meta">${escHtml(item.reason)}</div>
        <div class="list-card-metrics">
          <span class="metric-pill">${escHtml(item.state === 'primed' ? 'Primed' : 'Needs revisit')}</span>
          <span class="metric-pill">Attempts ${item.history?.attempt_count || 0}</span>
          <span class="metric-pill">Help ${item.history?.help_count || 0}</span>
          <span class="metric-pill">Last attempt ${escHtml(fmtDayDistance(item.history?.days_since_attempt))}</span>
        </div>
      </div>
    `,
  );
}

function renderRetrievalHabits(payload) {
  const habits = payload.retrieval_habits;
  retrievalHabits.innerHTML = `
    ${createStatGrid([
      {
        label: 'Attempt First',
        value: fmtPercent(habits.attempt_before_help_rate),
        note: 'Retrieval before scaffolding',
      },
      {
        label: 'Used Scaffolding',
        value: String(habits.help_turn_count || 0),
        note: 'Help-request turns so far',
      },
      {
        label: 'Verified Reconstructions',
        value: fmtPercent(habits.verified_reconstruction_rate),
        note: `${habits.attempt_turn_count || 0} scored attempts`,
      },
      {
        label: 'Return Rhythm',
        value: `${habits.active_days_last_14 || 0} days`,
        note: `${habits.session_count || 0} sessions in the recent log`,
      },
    ])}
    <div class="list-card">
      <div class="list-card-title">Why this matters</div>
      <div class="list-card-meta">This panel tracks learning behavior, not mastery. Attempt-first behavior protects generation before recognition.</div>
    </div>
  `;
}

function renderBranchFriction(payload) {
  branchFriction.innerHTML = createList(
    payload.branch_friction,
    'No branch friction data yet. Start drilling to see where understanding feels fragile.',
    (item) => `
      <div class="list-card">
        <div class="list-card-title-row">
          <div class="list-card-title">${escHtml(item.label)}</div>
          <div class="metric-pill">${item.counts.drilled} revisit${item.counts.drilled === 1 ? '' : 's'}</div>
        </div>
        <div class="list-card-meta">
          ${escHtml(item.owners.length ? `Backbone: ${item.owners.join(', ')}` : 'Available from the core thesis.')}
        </div>
        <div class="list-card-metrics">
          <span class="pill pill--solid">Solid ${item.counts.solidified}</span>
          <span class="pill pill--primed">Primed ${item.counts.primed}</span>
          <span class="pill pill--drilled">In progress ${item.counts.drilled}</span>
          <span class="pill pill--danger">Misconceptions ${item.history.misconception_count}</span>
        </div>
      </div>
    `,
  );
}

function renderConversionHistory(payload) {
  const conversions = payload.conversion_history.recent_conversions;
  conversionHistory.innerHTML = `
    ${createStatGrid([
      {
        label: 'Conversions',
        value: String(payload.conversion_history.conversion_count || 0),
        note: 'Previously unresolved nodes that later became solid',
      },
      {
        label: 'Latest Activity',
        value: fmtTimestamp(payload.cadence.latest_activity_at),
        note: 'Recent drill activity for this concept',
      },
    ])}
    ${createList(
      conversions,
      'No drilled-to-solid conversions yet. The first clean return will show up here.',
      (item) => `
        <div class="event-item">
          <div class="event-topline">
            <div class="event-stage">Conversion</div>
            <div class="event-meta">${escHtml(fmtTimestamp(item.converted_at))}</div>
          </div>
          <div class="event-title">${escHtml(item.node_label)}</div>
          <div class="event-summary">
            ${escHtml(item.previous_gap_type ? `Returned after ${item.previous_gap_type}.` : 'Returned after an unresolved attempt.')}
          </div>
        </div>
      `,
    )}
  `;
}

function renderCadence(payload) {
  cadencePanel.innerHTML = `
    ${createStatGrid([
      {
        label: 'Overdue Revisits',
        value: String(payload.cadence.overdue_revisit_count || 0),
        note: `Using a ${payload.cadence.revisit_due_days}-day spaced return heuristic`,
      },
      {
        label: 'Latest Activity',
        value: fmtTimestamp(payload.cadence.latest_activity_at),
        note: 'Recent drill activity tied to this concept',
      },
    ])}
    ${createList(
      payload.cadence.due_nodes,
      'Nothing is overdue for return yet.',
      (item) => `
        <div class="list-card">
          <div class="list-card-title-row">
            <div class="list-card-title">${escHtml(item.node_label)}</div>
            <div class="metric-pill">${escHtml(fmtDayDistance(item.days_since_attempt))}</div>
          </div>
          <div class="list-card-meta">Still unresolved and due for a clean return.</div>
        </div>
      `,
    )}
  `;
}

function renderSessionJournal(payload) {
  sessionJournal.innerHTML = createList(
    payload.session_journal,
    'No learner journal entries yet. Start a drill and this timeline will appear.',
    (item) => `
      <div class="event-item">
        <div class="event-topline">
          <div class="event-stage">${escHtml(item.outcome_label)}</div>
          <div class="event-meta">${escHtml(fmtTimestamp(item.timestamp))}</div>
        </div>
        <div class="event-title">${escHtml(item.node_label)}</div>
        <div class="event-summary">${escHtml(item.next_action)}</div>
        <div class="list-card-metrics">
          ${item.gap_label ? `<span class="metric-pill">${escHtml(item.gap_label)}</span>` : ''}
          ${item.answer_mode ? `<span class="metric-pill">${escHtml(item.answer_mode === 'help_request' ? 'Scaffolded' : 'Attempt')}</span>` : ''}
        </div>
      </div>
    `,
  );
}

async function fetchLearnerHistory(concepts) {
  if (!concepts.length) {
    return {
      source: 'empty',
      retrieval_habits: {},
      cadence: {},
      conversion_history: { recent_conversions: [] },
      session_journal: [],
      node_history: [],
      concept_stats: [],
    };
  }

  const conceptIds = concepts.map((concept) => concept.id);
  const browserPayload = buildBrowserLearnerSummaryPayload(conceptIds);
  if ((browserPayload?.retrieval_habits?.turn_count || 0) > 0) {
    return browserPayload;
  }

  try {
    const response = await fetch(`/api/analytics/learner-runs?concept_ids=${encodeURIComponent(conceptIds.join(','))}`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const payload = await response.json();
    return {
      source: 'server_logs',
      ...payload,
    };
  } catch (error) {
    if ((browserPayload?.retrieval_habits?.turn_count || 0) > 0) {
      return browserPayload;
    }
    throw error;
  }
}

function renderEmptyDashboard(message) {
  statusChip.textContent = 'Waiting';
  statusChip.dataset.tone = '';
  statusMeta.textContent = message;
  metricGrid.innerHTML = '';
  truthOverview.innerHTML = createEmptyState(message);
  nextBestMove.innerHTML = createEmptyState(message);
  revisitQueue.innerHTML = createEmptyState(message);
  retrievalHabits.innerHTML = createEmptyState(message);
  branchFriction.innerHTML = createEmptyState(message);
  conversionHistory.innerHTML = createEmptyState(message);
  cadencePanel.innerHTML = createEmptyState(message);
  sessionJournal.innerHTML = createEmptyState(message);
}

function positionHelpTooltip(target) {
  if (!analyticsHelpTooltip || !target) return;
  const gap = 14;
  const rect = target.getBoundingClientRect();
  let left = rect.right + gap + window.scrollX;
  let top = rect.top + window.scrollY;

  analyticsHelpTooltip.style.left = `${left}px`;
  analyticsHelpTooltip.style.top = `${top}px`;

  const tooltipRect = analyticsHelpTooltip.getBoundingClientRect();
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;

  if (tooltipRect.right > viewportWidth - 16) {
    left = rect.left + window.scrollX - tooltipRect.width - gap;
  }
  if (left < 16 + window.scrollX) {
    left = Math.max(16 + window.scrollX, rect.left + window.scrollX);
    top = rect.bottom + gap + window.scrollY;
  }
  if (top + tooltipRect.height > viewportHeight + window.scrollY - 16) {
    top = Math.max(16 + window.scrollY, rect.bottom + window.scrollY - tooltipRect.height);
  }

  analyticsHelpTooltip.style.left = `${left}px`;
  analyticsHelpTooltip.style.top = `${top}px`;
}

function hideHelpTooltip() {
  if (!analyticsHelpTooltip) return;
  analyticsHelpTooltip.classList.remove('visible');
  analyticsHelpTooltip.innerHTML = '';
}

function showHelpTooltip(target) {
  if (!analyticsHelpTooltip || !target) return;
  const title = target.dataset.helpTitle || 'Quick Guide';
  const body = target.dataset.helpBody || '';
  analyticsHelpTooltip.innerHTML = `
    <div class="tour-tooltip-kicker">Quick Guide</div>
    <div class="tour-tooltip-title">${escHtml(title)}</div>
    <div class="tour-tooltip-body">${escHtml(body)}</div>
  `;
  positionHelpTooltip(target);
  analyticsHelpTooltip.classList.add('visible');
}

function initInlineHelp() {
  const buttons = document.querySelectorAll('.analytics-help-button');
  buttons.forEach((button) => {
    if (button.dataset.bound === 'true') return;
    button.dataset.bound = 'true';
    button.addEventListener('mouseenter', () => showHelpTooltip(button));
    button.addEventListener('focus', () => showHelpTooltip(button));
    button.addEventListener('mouseleave', hideHelpTooltip);
    button.addEventListener('blur', hideHelpTooltip);
    button.addEventListener('click', (event) => {
      event.preventDefault();
      showHelpTooltip(button);
    });
  });
}

async function loadDashboard() {
  if (!statusChip || !statusMeta || !metricGrid) return;
  statusChip.textContent = 'Loading…';
  statusChip.dataset.tone = '';
  statusMeta.textContent = 'Reading your saved concept maps and recent drill history.';

  try {
    const concepts = getMappedConcepts();
    const activeConcept = getCurrentConcept(concepts);

    if (!concepts.length || !activeConcept) {
      renderEmptyDashboard('No mapped concepts yet. Create or open a concept first, then come back for analytics.');
      if (conceptSelect) conceptSelect.innerHTML = '';
      return;
    }

    renderConceptOptions(concepts, activeConcept);
    const remoteData = await fetchLearnerHistory(concepts);
    const payload = buildConceptPayload(activeConcept, remoteData);

    if (!payload) {
      renderEmptyDashboard('This concept does not have usable graph data yet.');
      return;
    }

    renderMetricGrid(payload);
    renderTruthOverview(payload);
    renderNextBestMove(payload);
    renderRevisitQueue(payload);
    renderRetrievalHabits(payload);
    renderBranchFriction(payload);
    renderConversionHistory(payload);
    renderCadence(payload);
    renderSessionJournal(payload);

    const sourceLabel = remoteData?.source === 'browser_local_storage'
      ? 'browser-local telemetry'
      : 'server drill history';
    statusChip.textContent = 'Ready';
    statusMeta.textContent = `Showing "${activeConcept.name}" from local graph truth plus ${sourceLabel}. Last activity: ${fmtTimestamp(payload.cadence.latest_activity_at)}`;
  } catch (error) {
    console.error(error);
    statusChip.textContent = 'Load Failed';
    statusChip.dataset.tone = 'error';
    statusMeta.textContent = 'Could not load learner analytics.';
    const errorState = 'Learner analytics failed to load. Check that your concept data and browser telemetry are available.';
    renderEmptyDashboard(errorState);
    statusChip.textContent = 'Load Failed';
    statusChip.dataset.tone = 'error';
    statusMeta.textContent = errorState;
  }
}

export function mountLearnerAnalyticsDashboard({ root = document, autoLoad = true, onConceptChange = null } = {}) {
  cacheDomRefs(root);
  if (!conceptSelect || !statusChip || !statusMeta || !metricGrid) {
    return null;
  }

  analyticsCallbacks.onConceptChange = onConceptChange;

  if (!dashboardMounted) {
    conceptSelect.addEventListener('change', () => {
      const nextId = conceptSelect.value || null;
      if (analyticsCallbacks.onConceptChange) {
        analyticsCallbacks.onConceptChange(nextId);
      } else {
        setActiveId(nextId);
      }
      loadDashboard();
    });

    refreshButton?.addEventListener('click', () => {
      loadDashboard();
    });

    window.addEventListener('resize', hideHelpTooltip);
    window.addEventListener('scroll', hideHelpTooltip, { passive: true });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') hideHelpTooltip();
    });

    initInlineHelp();
    dashboardMounted = true;
  }

  const api = {
    loadDashboard,
  };

  if (typeof window !== 'undefined') {
    window.LearnerAnalytics = api;
  }

  if (autoLoad) {
    loadDashboard();
  }

  return api;
}

if (document.querySelector('[data-learner-analytics-autoload="true"]')) {
  mountLearnerAnalyticsDashboard();
}
