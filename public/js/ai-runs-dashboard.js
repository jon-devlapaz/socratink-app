import { buildBrowserAiRunsPayload } from './browser-analytics.js';

const metricGrid = document.getElementById('metric-grid');
const extractPanel = document.getElementById('extract-panel');
const drillPanel = document.getElementById('drill-panel');
const extractDistributions = document.getElementById('extract-distributions');
const drillDistributions = document.getElementById('drill-distributions');
const hotspotNodes = document.getElementById('hotspot-nodes');
const hotspotClusters = document.getElementById('hotspot-clusters');
const nodeTypeBenchmarks = document.getElementById('node-type-benchmarks');
const recentEvents = document.getElementById('recent-events');
const statusChip = document.getElementById('status-chip');
const statusMeta = document.getElementById('status-meta');
const refreshButton = document.getElementById('refresh-button');

function fmtNumber(value, digits = 1) {
  const numeric = Number(value || 0);
  return Number.isFinite(numeric) ? numeric.toFixed(digits) : '0.0';
}

function fmtPercent(value) {
  return `${fmtNumber(value, 1)}%`;
}

function fmtTimestamp(value) {
  if (!value) return 'No runs yet';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

function counterEntries(counter) {
  if (!counter || typeof counter !== 'object') return [];
  return Object.entries(counter);
}

function createBarGroup(title, counter) {
  const entries = counterEntries(counter);
  if (!entries.length) {
    return `<div class="empty-state">${title}: not enough data yet.</div>`;
  }

  const max = Math.max(...entries.map(([, value]) => Number(value || 0)), 1);
  const rows = entries
    .sort((a, b) => Number(b[1]) - Number(a[1]))
    .map(([label, value]) => {
      const width = (Number(value || 0) / max) * 100;
      return `
        <div class="bar-row">
          <div class="bar-label-row">
            <span class="bar-label">${escapeHtml(label)}</span>
            <span class="bar-value">${value}</span>
          </div>
          <div class="bar-track">
            <div class="bar-fill" style="width:${width}%"></div>
          </div>
        </div>
      `;
    })
    .join('');

  return `
    <section class="bar-group">
      <div class="stat-tile-label">${escapeHtml(title)}</div>
      ${rows}
    </section>
  `;
}

function createStatGrid(items) {
  return `
    <div class="stat-grid">
      ${items.map((item) => `
        <div class="stat-tile">
          <div class="stat-tile-label">${escapeHtml(item.label)}</div>
          <div class="stat-tile-value">${escapeHtml(item.value)}</div>
        </div>
      `).join('')}
    </div>
  `;
}

function createList(items, emptyMessage, renderItem) {
  if (!items?.length) {
    return `<div class="empty-state">${escapeHtml(emptyMessage)}</div>`;
  }
  return `<div class="list-stack">${items.map(renderItem).join('')}</div>`;
}

function createMetricCards(payload) {
  const cards = [
    {
      label: 'Extract Success',
      value: fmtPercent(payload.extract.success_rate),
      note: `${payload.extract.success_count}/${payload.extract.total_runs} runs`,
    },
    {
      label: 'Drill Success',
      value: fmtPercent(payload.drill.success_rate),
      note: `${payload.drill.success_count}/${payload.drill.total_runs} runs`,
    },
    {
      label: 'Attempt Rate',
      value: fmtPercent(payload.drill.attempt_rate),
      note: `${payload.drill.attempt_turn_count} scored attempts`,
    },
    {
      label: 'Help Request Rate',
      value: fmtPercent(payload.drill.help_request_rate),
      note: `${payload.drill.help_turn_count} help turns`,
    },
  ];

  return cards.map((card) => `
    <article class="metric-card">
      <div class="metric-label">${escapeHtml(card.label)}</div>
      <div class="metric-value">${escapeHtml(card.value)}</div>
      <div class="metric-note">${escapeHtml(card.note)}</div>
    </article>
  `).join('');
}

function renderExtractPanel(extract) {
  extractPanel.innerHTML = `
    ${createStatGrid([
      { label: 'Runs', value: String(extract.total_runs) },
      { label: 'Avg Duration', value: `${fmtNumber(extract.avg_duration_ms)} ms` },
      { label: 'Avg Clusters', value: fmtNumber(extract.avg_cluster_count) },
      { label: 'Avg Subnodes', value: fmtNumber(extract.avg_subnode_count) },
      { label: 'Low-Density Rate', value: fmtPercent(extract.low_density_rate) },
      { label: 'Latest Success', value: fmtTimestamp(extract.latest_success_at) },
    ])}
    ${createList(
      extract.top_sources,
      'No successful extraction runs yet.',
      ([title, count]) => `
        <div class="list-card">
          <div class="list-card-title-row">
            <div class="list-card-title">${escapeHtml(title)}</div>
            <div class="metric-pill">${count} runs</div>
          </div>
        </div>
      `
    )}
  `;
}

function renderDrillPanel(drill) {
  drillPanel.innerHTML = `
    ${createStatGrid([
      { label: 'Turn Count', value: String(drill.turn_count) },
      { label: 'Scored Attempts', value: String(drill.classified_turn_count) },
      { label: 'Solid Rate', value: fmtPercent(drill.solid_rate) },
      { label: 'Force Advance', value: fmtPercent(drill.attempt_force_advance_rate) },
      { label: 'Reward Emit', value: fmtPercent(drill.reward_emit_rate) },
      { label: 'Latest Turn', value: fmtTimestamp(drill.latest_turn_at) },
    ])}
    <div class="list-card">
      <div class="list-card-title">Current Pulse</div>
      <div class="list-card-metrics">
        <span class="metric-pill">One-turn solid ${fmtPercent(drill.one_turn_solid_rate)}</span>
        <span class="metric-pill">Help-only sessions ${drill.help_only_session_count}</span>
        <span class="metric-pill">Avg attempt length ${fmtNumber(drill.avg_attempt_learner_chars)} chars</span>
      </div>
    </div>
  `;
}

function renderHotspots(container, items, emptyMessage, kind) {
  container.innerHTML = createList(
    items,
    emptyMessage,
    (item) => `
      <div class="list-card">
        <div class="list-card-title-row">
          <div class="list-card-title">${escapeHtml(item.label || item.node_id || item.cluster_id || kind)}</div>
          <div class="metric-pill">${item.turns} turns</div>
        </div>
        <div class="list-card-meta">
          ${item.node_id ? `Node: ${escapeHtml(item.node_id)}` : `Cluster: ${escapeHtml(item.cluster_id || 'unknown')}`}
        </div>
        <div class="list-card-metrics">
          <span class="metric-pill">Solid ${fmtPercent(item.solid_rate)}</span>
          <span class="metric-pill">Misconception ${fmtPercent(item.misconception_rate)}</span>
          <span class="metric-pill">Force advance ${fmtPercent(item.force_advance_rate)}</span>
        </div>
      </div>
    `,
  );
}

function renderBenchmarks(items) {
  nodeTypeBenchmarks.innerHTML = createList(
    items,
    'Not enough scored drill volume yet.',
    (item) => `
      <div class="list-card">
        <div class="list-card-title-row">
          <div class="list-card-title">${escapeHtml(item.node_type)}</div>
          <div class="metric-pill">${item.turns} turns</div>
        </div>
        <div class="list-card-metrics">
          <span class="metric-pill">Solid ${fmtPercent(item.solid_rate)}</span>
          <span class="metric-pill">Non-solid ${fmtPercent(item.non_solid_rate)}</span>
          <span class="metric-pill">Force advance ${fmtPercent(item.force_advance_rate)}</span>
        </div>
      </div>
    `,
  );
}

function renderRecentEvents(items) {
  recentEvents.innerHTML = createList(
    items,
    'No analytics events yet.',
    (item) => `
      <div class="event-item">
        <div class="event-topline">
          <div class="event-stage">${escapeHtml(item.stage)} · ${escapeHtml(item.status || 'unknown')}</div>
          <div class="event-meta">${escapeHtml(fmtTimestamp(item.timestamp))}</div>
        </div>
        <div class="event-title">${escapeHtml(item.title || 'Untitled event')}</div>
        <div class="event-summary">${escapeHtml(item.summary || 'No summary')}</div>
        <div class="event-meta">run_mode=${escapeHtml(item.run_mode || 'default')}${item.fixture_id ? ` · fixture=${escapeHtml(item.fixture_id)}` : ''}</div>
      </div>
    `,
  );
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

async function loadDashboard() {
  statusChip.textContent = 'Loading…';
  statusChip.dataset.tone = '';
  statusMeta.textContent = 'Fetching analytics payload';

  try {
    const browserPayload = buildBrowserAiRunsPayload();
    let payload = browserPayload;

    if (
      (browserPayload?.extract?.total_runs || 0) === 0
      && (browserPayload?.drill?.total_runs || 0) === 0
    ) {
      const response = await fetch('/api/analytics/ai-runs');
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      payload = {
        source: 'server_logs',
        ...(await response.json()),
      };
    }
    metricGrid.innerHTML = createMetricCards(payload);
    renderExtractPanel(payload.extract);
    renderDrillPanel(payload.drill);

    extractDistributions.innerHTML = [
      createBarGroup('Architecture', payload.extract.architecture_distribution),
      createBarGroup('Difficulty', payload.extract.difficulty_distribution),
      createBarGroup('Extract Errors', payload.extract.error_types),
    ].join('');

    drillDistributions.innerHTML = [
      createBarGroup('Answer Modes', payload.drill.answer_mode_distribution),
      createBarGroup('Classification', payload.drill.classification_distribution),
      createBarGroup('Routing', payload.drill.routing_distribution),
      createBarGroup('Response Tiers', payload.drill.response_tier_distribution),
      createBarGroup('Run Modes', payload.drill.run_mode_distribution),
    ].join('');

    renderHotspots(hotspotNodes, payload.drill.hotspot_nodes, 'Not enough drill volume to identify friction nodes yet.', 'node');
    renderHotspots(hotspotClusters, payload.drill.hotspot_clusters, 'Not enough drill volume to identify friction clusters yet.', 'cluster');
    renderBenchmarks(payload.drill.node_type_benchmarks);
    renderRecentEvents(payload.recent_events);

    const latestTimestamp = payload.drill.latest_run_at || payload.extract.latest_run_at;
    statusChip.textContent = 'Live';
    statusMeta.textContent = `Showing ${payload?.source === 'browser_local_storage' ? 'browser-local telemetry' : 'server analytics'}. Last activity: ${fmtTimestamp(latestTimestamp)}`;
  } catch (error) {
    console.error(error);
    statusChip.textContent = 'Load Failed';
    statusChip.dataset.tone = 'error';
    statusMeta.textContent = 'Could not load AI runs analytics.';

    const errorState = `<div class="empty-state">Analytics payload failed to load. Confirm the backend is running or that browser telemetry exists for this browser profile.</div>`;
    metricGrid.innerHTML = '';
    extractPanel.innerHTML = errorState;
    drillPanel.innerHTML = errorState;
    extractDistributions.innerHTML = errorState;
    drillDistributions.innerHTML = errorState;
    hotspotNodes.innerHTML = errorState;
    hotspotClusters.innerHTML = errorState;
    nodeTypeBenchmarks.innerHTML = errorState;
    recentEvents.innerHTML = errorState;
  }
}

refreshButton?.addEventListener('click', () => {
  loadDashboard();
});

loadDashboard();
