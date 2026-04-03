const EXTRACT_STORAGE_KEY = 'learnops_extract_runs_v1';
const DRILL_STORAGE_KEY = 'learnops_drill_runs_v1';
const EXTRACT_LIMIT = 200;
const DRILL_LIMIT = 2000;

function parseTimestamp(value) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function latestTimestamp(rows) {
  let latest = null;
  for (const row of rows || []) {
    const current = parseTimestamp(row?.timestamp);
    if (!current) continue;
    if (!latest || current > latest) latest = current;
  }
  return latest ? latest.toISOString() : null;
}

function pct(numerator, denominator) {
  if (!denominator || denominator <= 0) return 0;
  return (Number(numerator || 0) / Number(denominator || 0)) * 100;
}

function safeMean(values) {
  const numeric = (values || [])
    .map((value) => Number(value))
    .filter((value) => Number.isFinite(value));
  if (!numeric.length) return 0;
  return numeric.reduce((sum, value) => sum + value, 0) / numeric.length;
}

function topCounter(counter, limit = 5) {
  return Object.entries(counter || {})
    .sort((a, b) => Number(b[1]) - Number(a[1]) || String(a[0]).localeCompare(String(b[0])))
    .slice(0, limit);
}

function incrementCounter(counter, key) {
  const safeKey = String(key || 'unknown');
  counter[safeKey] = (counter[safeKey] || 0) + 1;
}

function readRows(key) {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((row) => row && typeof row === 'object') : [];
  } catch (error) {
    console.warn(`Failed to read analytics storage key ${key}`, error);
    return [];
  }
}

function writeRows(key, rows) {
  try {
    localStorage.setItem(key, JSON.stringify(rows));
  } catch (error) {
    console.warn(`Failed to write analytics storage key ${key}`, error);
  }
}

function appendRow(key, payload, limit) {
  const rows = readRows(key);
  rows.push({
    timestamp: payload?.timestamp || new Date().toISOString(),
    ...payload,
  });
  const trimmed = rows.slice(-limit);
  writeRows(key, trimmed);
  return trimmed;
}

export function loadBrowserExtractRuns() {
  return readRows(EXTRACT_STORAGE_KEY);
}

export function loadBrowserDrillRuns() {
  return readRows(DRILL_STORAGE_KEY);
}

export function recordExtractRun(payload) {
  appendRow(EXTRACT_STORAGE_KEY, payload, EXTRACT_LIMIT);
}

export function recordDrillRun(payload) {
  appendRow(DRILL_STORAGE_KEY, payload, DRILL_LIMIT);
}

function buildExtractSummary(rows) {
  const successRows = rows.filter((row) => row.status === 'success');
  const errorRows = rows.filter((row) => row.status === 'error');
  const architecture = {};
  const difficulty = {};
  const errorTypes = {};
  const topSourcesCounter = {};

  successRows.forEach((row) => {
    incrementCounter(architecture, row.architecture_type || 'unknown');
    incrementCounter(difficulty, row.difficulty || 'unknown');
    incrementCounter(topSourcesCounter, row.source_title || 'unknown');
  });
  errorRows.forEach((row) => {
    incrementCounter(errorTypes, row.error_type || 'unknown');
  });

  return {
    total_runs: rows.length,
    success_count: successRows.length,
    error_count: errorRows.length,
    success_rate: pct(successRows.length, rows.length),
    avg_duration_ms: safeMean(successRows.map((row) => row.duration_ms || 0)),
    avg_cluster_count: safeMean(successRows.map((row) => row.cluster_count || 0)),
    avg_backbone_count: safeMean(successRows.map((row) => row.backbone_count || 0)),
    avg_subnode_count: safeMean(successRows.map((row) => row.subnode_count || 0)),
    low_density_rate: pct(successRows.filter((row) => row.low_density === true).length, successRows.length),
    latest_run_at: latestTimestamp(rows),
    latest_success_at: latestTimestamp(successRows),
    latest_error_at: latestTimestamp(errorRows),
    architecture_distribution: architecture,
    difficulty_distribution: difficulty,
    error_types: errorTypes,
    top_sources: topCounter(topSourcesCounter),
  };
}

function buildDrillSummary(rows) {
  const successRows = rows.filter((row) => row.status === 'success');
  const errorRows = rows.filter((row) => row.status === 'error');
  const turnRows = successRows.filter((row) => row.session_phase === 'turn');
  const attemptTurns = turnRows.filter((row) => row.answer_mode === 'attempt');
  const helpTurns = turnRows.filter((row) => row.answer_mode === 'help_request');
  const classifiedTurns = attemptTurns.filter((row) => row.classification);

  const classification = {};
  const routing = {};
  const nodeTypes = {};
  const answerModes = {};
  const helpReasons = {};
  const responseTiers = {};
  const responseBands = {};
  const terminations = {};
  const errorTypes = {};
  const runModes = {};
  const byNode = {};
  const byCluster = {};
  const byNodeType = {};

  classifiedTurns.forEach((row) => incrementCounter(classification, row.classification || 'none'));
  turnRows.forEach((row) => {
    incrementCounter(routing, row.routing || 'none');
    incrementCounter(nodeTypes, row.node_type || 'unknown');
    incrementCounter(answerModes, row.answer_mode || 'none');
    incrementCounter(runModes, row.run_mode || 'default');
  });
  helpTurns.forEach((row) => incrementCounter(helpReasons, row.help_request_reason || 'none'));
  attemptTurns.forEach((row) => {
    if (row.response_tier != null) incrementCounter(responseTiers, String(row.response_tier));
    if (row.response_band) incrementCounter(responseBands, row.response_band);
  });
  successRows
    .filter((row) => row.session_terminated)
    .forEach((row) => incrementCounter(terminations, row.termination_reason || 'none'));
  errorRows.forEach((row) => incrementCounter(errorTypes, row.error_type || 'unknown'));

  classifiedTurns.forEach((row) => {
    const nodeId = row.node_id || 'unknown';
    const clusterId = row.cluster_id || 'none';
    const nodeType = row.node_type || 'unknown';
    byNode[nodeId] = byNode[nodeId] || {
      label: row.node_label || '',
      turns: 0,
      solid: 0,
      misconception: 0,
      force_advanced: 0,
    };
    byCluster[clusterId] = byCluster[clusterId] || {
      turns: 0,
      solid: 0,
      misconception: 0,
      force_advanced: 0,
    };
    byNodeType[nodeType] = byNodeType[nodeType] || {
      turns: 0,
      solid: 0,
      non_solid: 0,
      force_advanced: 0,
    };

    byNode[nodeId].turns += 1;
    byCluster[clusterId].turns += 1;
    byNodeType[nodeType].turns += 1;

    if (row.classification === 'solid') {
      byNode[nodeId].solid += 1;
      byCluster[clusterId].solid += 1;
      byNodeType[nodeType].solid += 1;
    } else {
      byNodeType[nodeType].non_solid += 1;
    }

    if (row.classification === 'misconception') {
      byNode[nodeId].misconception += 1;
      byCluster[clusterId].misconception += 1;
    }

    if (row.force_advanced === true) {
      byNode[nodeId].force_advanced += 1;
      byCluster[clusterId].force_advanced += 1;
      byNodeType[nodeType].force_advanced += 1;
    }
  });

  const solidTurns = classifiedTurns.filter((row) => row.classification === 'solid').length;
  const nonSolidNext = classifiedTurns.filter((row) => row.routing === 'NEXT' && row.classification !== 'solid').length;
  const forceAdvanced = classifiedTurns.filter((row) => row.force_advanced === true).length;
  const attemptForceAdvanced = attemptTurns.filter((row) => row.force_advanced === true).length;
  const helpForceAdvanced = helpTurns.filter((row) => row.force_advanced === true).length;
  const oneTurnSolids = classifiedTurns.filter((row) => row.classification === 'solid' && Number(row.probe_count_in || 0) === 0).length;
  const rewardEmitted = attemptTurns.filter((row) => row.ux_reward_emitted === true).length;

  const sessions = {};
  turnRows.forEach((row) => {
    const sessionKey = [
      String(row.concept_id || 'unknown'),
      String(row.node_id || 'unknown'),
      String(row.session_start_iso || 'missing'),
    ].join('::');
    sessions[sessionKey] = sessions[sessionKey] || [];
    sessions[sessionKey].push(row);
  });
  const helpOnlySessionCount = Object.values(sessions).filter((sessionRows) => (
    sessionRows.length && sessionRows.every((row) => row.answer_mode === 'help_request')
  )).length;

  const hotspotNodes = Object.entries(byNode)
    .map(([node_id, stats]) => ({
      node_id,
      label: stats.label,
      turns: stats.turns,
      solid_rate: pct(stats.solid, stats.turns),
      misconception_rate: pct(stats.misconception, stats.turns),
      force_advance_rate: pct(stats.force_advanced, stats.turns),
    }))
    .filter((row) => row.turns >= 2)
    .sort((a, b) => b.force_advance_rate - a.force_advance_rate || b.misconception_rate - a.misconception_rate || a.solid_rate - b.solid_rate)
    .slice(0, 5);

  const hotspotClusters = Object.entries(byCluster)
    .map(([cluster_id, stats]) => ({
      cluster_id,
      turns: stats.turns,
      solid_rate: pct(stats.solid, stats.turns),
      misconception_rate: pct(stats.misconception, stats.turns),
      force_advance_rate: pct(stats.force_advanced, stats.turns),
    }))
    .filter((row) => row.turns >= 2 && row.cluster_id !== 'none')
    .sort((a, b) => b.force_advance_rate - a.force_advance_rate || b.misconception_rate - a.misconception_rate || a.solid_rate - b.solid_rate)
    .slice(0, 5);

  const nodeTypeBenchmarks = Object.entries(byNodeType)
    .map(([node_type, stats]) => ({
      node_type,
      turns: stats.turns,
      solid_rate: pct(stats.solid, stats.turns),
      non_solid_rate: pct(stats.non_solid, stats.turns),
      force_advance_rate: pct(stats.force_advanced, stats.turns),
    }))
    .filter((row) => row.turns > 0)
    .sort((a, b) => String(a.node_type).localeCompare(String(b.node_type)));

  return {
    total_runs: rows.length,
    success_count: successRows.length,
    error_count: errorRows.length,
    success_rate: pct(successRows.length, rows.length),
    turn_count: turnRows.length,
    attempt_turn_count: attemptTurns.length,
    help_turn_count: helpTurns.length,
    classified_turn_count: classifiedTurns.length,
    avg_duration_ms: safeMean(successRows.map((row) => row.duration_ms || 0)),
    avg_attempt_learner_chars: safeMean(attemptTurns.map((row) => row.latest_learner_chars || 0)),
    avg_help_learner_chars: safeMean(helpTurns.map((row) => row.latest_learner_chars || 0)),
    latest_run_at: latestTimestamp(rows),
    latest_turn_at: latestTimestamp(turnRows),
    latest_success_at: latestTimestamp(successRows),
    latest_error_at: latestTimestamp(errorRows),
    classification_distribution: classification,
    routing_distribution: routing,
    node_type_distribution: nodeTypes,
    answer_mode_distribution: answerModes,
    help_request_reason_distribution: helpReasons,
    run_mode_distribution: runModes,
    response_tier_distribution: responseTiers,
    response_band_distribution: responseBands,
    termination_distribution: terminations,
    error_types: errorTypes,
    attempt_rate: pct(attemptTurns.length, turnRows.length),
    help_request_rate: pct(helpTurns.length, turnRows.length),
    solid_rate: pct(solidTurns, classifiedTurns.length),
    non_solid_next_rate: pct(nonSolidNext, classifiedTurns.length),
    force_advance_rate: pct(forceAdvanced, classifiedTurns.length),
    attempt_force_advance_rate: pct(attemptForceAdvanced, attemptTurns.length),
    help_force_advance_rate: pct(helpForceAdvanced, helpTurns.length),
    one_turn_solid_rate: pct(oneTurnSolids, classifiedTurns.length),
    reward_emit_rate: pct(rewardEmitted, attemptTurns.length),
    help_only_session_count: helpOnlySessionCount,
    hotspot_nodes: hotspotNodes,
    hotspot_clusters: hotspotClusters,
    node_type_benchmarks: nodeTypeBenchmarks,
  };
}

function buildRecentEvents(extractRows, drillRows, limit = 12) {
  const events = [];

  extractRows.forEach((row) => {
    events.push({
      timestamp: row.timestamp,
      stage: 'extract',
      status: row.status,
      title: row.source_title || row.fixture_title || 'Extraction',
      summary: row.reason || row.architecture_type || 'Extraction run',
      run_mode: row.run_mode || 'default',
      fixture_id: row.fixture_id || null,
    });
  });

  drillRows.forEach((row) => {
    events.push({
      timestamp: row.timestamp,
      stage: 'drill',
      status: row.status,
      title: row.node_label || row.node_id || 'Drill turn',
      summary: row.reason || row.classification || row.routing || 'Drill turn',
      run_mode: row.run_mode || 'default',
      fixture_id: row.fixture_id || null,
    });
  });

  return events
    .sort((a, b) => {
      const aTime = parseTimestamp(a.timestamp)?.getTime() || 0;
      const bTime = parseTimestamp(b.timestamp)?.getTime() || 0;
      return bTime - aTime;
    })
    .slice(0, limit);
}

function daysBetween(now, timestamp) {
  const value = parseTimestamp(timestamp);
  if (!value) return null;
  return Math.max(Math.floor((now.getTime() - value.getTime()) / 86400000), 0);
}

function journalOutcome(row, convertedNodeKeys) {
  const key = `${row.concept_id || ''}::${row.node_id || ''}`;
  if (row.answer_mode === 'help_request') {
    return ['Used scaffolding', 'Try this node again from memory.'];
  }
  if (row.classification === 'solid' && convertedNodeKeys.has(key)) {
    return ['Solidified on return', 'Keep your momentum and take the next reachable node.'];
  }
  if (row.classification === 'solid') {
    return ['Verified understanding', 'Advance to the next reachable node.'];
  }
  if (row.classification === 'misconception') {
    return ['Misconception caught', 'Revisit this mechanism soon while the gap is fresh.'];
  }
  if (row.classification) {
    return ['Still in progress', 'Return for one more clean pass.'];
  }
  return ['Activity logged', 'Choose one reachable node and reconstruct it from memory.'];
}

export function buildBrowserAiRunsPayload() {
  const extractRows = loadBrowserExtractRuns();
  const drillRows = loadBrowserDrillRuns();

  return {
    source: 'browser_local_storage',
    extract: buildExtractSummary(extractRows),
    drill: buildDrillSummary(drillRows),
    recent_events: buildRecentEvents(extractRows, drillRows),
    paths: {
      extract_log: 'browser_local_storage',
      drill_log: 'browser_local_storage',
    },
  };
}

export function buildBrowserLearnerSummaryPayload(conceptIds = null) {
  const conceptFilter = Array.isArray(conceptIds) && conceptIds.length
    ? new Set(conceptIds.map((value) => String(value)))
    : null;
  const allRows = loadBrowserDrillRuns();
  const turnRows = allRows.filter((row) => (
    row.status === 'success'
    && row.session_phase === 'turn'
    && (!conceptFilter || conceptFilter.has(String(row.concept_id || '')))
  ));

  const now = new Date();
  const recentWindow = new Date(now.getTime() - (14 * 86400000));
  const dueThresholdDays = 3;

  const attemptTurns = turnRows.filter((row) => row.answer_mode === 'attempt');
  const helpTurns = turnRows.filter((row) => row.answer_mode === 'help_request');
  const recentTurns = turnRows.filter((row) => {
    const value = parseTimestamp(row.timestamp);
    return value && value >= recentWindow;
  });

  const sessionKeys = new Set(
    turnRows.map((row) => [
      String(row.concept_id || 'unknown'),
      String(row.node_id || 'unknown'),
      String(row.session_start_iso || 'missing'),
    ].join('::'))
  );

  const activeDays = Array.from(new Set(
    turnRows
      .map((row) => parseTimestamp(row.timestamp))
      .filter(Boolean)
      .map((date) => date.toISOString().slice(0, 10))
  )).sort();

  const activeDaysLast7 = new Set(
    turnRows
      .map((row) => parseTimestamp(row.timestamp))
      .filter((date) => date && date >= new Date(now.getTime() - (7 * 86400000)))
      .map((date) => date.toISOString().slice(0, 10))
  );

  const activeDaysLast14 = new Set(
    turnRows
      .map((row) => parseTimestamp(row.timestamp))
      .filter((date) => date && date >= recentWindow)
      .map((date) => date.toISOString().slice(0, 10))
  );

  const groupedRows = {};
  turnRows.forEach((row) => {
    const key = `${String(row.concept_id || '')}::${String(row.node_id || '')}`;
    groupedRows[key] = groupedRows[key] || [];
    groupedRows[key].push(row);
  });

  const nodeHistory = [];
  const conversionHistory = [];
  const convertedNodeKeys = new Set();

  Object.entries(groupedRows).forEach(([key, rows]) => {
    const orderedRows = [...rows].sort((a, b) => {
      const aTime = parseTimestamp(a.timestamp)?.getTime() || 0;
      const bTime = parseTimestamp(b.timestamp)?.getTime() || 0;
      return aTime - bTime;
    });
    const [conceptId, nodeId] = key.split('::');
    const history = {
      concept_id: conceptId,
      node_id: nodeId,
      node_label: orderedRows[orderedRows.length - 1]?.node_label || nodeId,
      cluster_id: orderedRows[orderedRows.length - 1]?.cluster_id || null,
      node_type: orderedRows[orderedRows.length - 1]?.node_type || 'unknown',
      attempt_count: 0,
      help_count: 0,
      solid_count: 0,
      non_solid_count: 0,
      misconception_count: 0,
      last_attempt_at: null,
      last_help_at: null,
      last_turn_at: null,
      latest_classification: null,
    };

    let seenNonSolidAt = null;
    let seenNonSolidLabel = null;

    orderedRows.forEach((row) => {
      history.last_turn_at = row.timestamp || history.last_turn_at;

      if (row.answer_mode === 'help_request') {
        history.help_count += 1;
        history.last_help_at = row.timestamp || history.last_help_at;
        return;
      }

      if (row.answer_mode !== 'attempt') return;

      history.attempt_count += 1;
      history.last_attempt_at = row.timestamp || history.last_attempt_at;
      history.latest_classification = row.classification || history.latest_classification;

      if (row.classification === 'solid') {
        history.solid_count += 1;
        if (seenNonSolidAt && !convertedNodeKeys.has(key)) {
          conversionHistory.push({
            concept_id: conceptId,
            node_id: nodeId,
            node_label: history.node_label,
            converted_at: row.timestamp,
            last_non_solid_at: seenNonSolidAt,
            previous_gap_type: seenNonSolidLabel,
          });
          convertedNodeKeys.add(key);
        }
      } else if (row.classification) {
        history.non_solid_count += 1;
        seenNonSolidAt = row.timestamp;
        seenNonSolidLabel = row.classification;
        if (row.classification === 'misconception') {
          history.misconception_count += 1;
        }
      }
    });

    history.days_since_attempt = daysBetween(now, history.last_attempt_at);
    nodeHistory.push(history);
  });

  const dueNodes = nodeHistory
    .filter((row) => row.latest_classification && row.latest_classification !== 'solid' && (row.days_since_attempt || 0) >= dueThresholdDays)
    .map((row) => ({
      concept_id: row.concept_id,
      node_id: row.node_id,
      node_label: row.node_label,
      days_since_attempt: row.days_since_attempt,
      latest_classification: row.latest_classification,
    }))
    .sort((a, b) => (b.days_since_attempt || 0) - (a.days_since_attempt || 0) || String(a.node_label).localeCompare(String(b.node_label)));

  const conceptSessions = {};
  const conceptStatsMap = {};
  turnRows.forEach((row) => {
    const conceptId = String(row.concept_id || '');
    conceptSessions[conceptId] = conceptSessions[conceptId] || new Set();
    conceptSessions[conceptId].add([
      conceptId,
      String(row.node_id || 'unknown'),
      String(row.session_start_iso || 'missing'),
    ].join('::'));

    const stats = conceptStatsMap[conceptId] || {
      concept_id: conceptId,
      turn_count: 0,
      attempt_turn_count: 0,
      help_turn_count: 0,
      solid_attempt_count: 0,
      latest_activity_at: null,
      active_days_last_14: new Set(),
    };

    stats.turn_count += 1;
    if (!stats.latest_activity_at || (parseTimestamp(row.timestamp)?.getTime() || 0) > (parseTimestamp(stats.latest_activity_at)?.getTime() || 0)) {
      stats.latest_activity_at = row.timestamp || stats.latest_activity_at;
    }

    const rowDate = parseTimestamp(row.timestamp);
    if (rowDate && rowDate >= recentWindow) {
      stats.active_days_last_14.add(rowDate.toISOString().slice(0, 10));
    }

    if (row.answer_mode === 'attempt') {
      stats.attempt_turn_count += 1;
      if (row.classification === 'solid') stats.solid_attempt_count += 1;
    } else if (row.answer_mode === 'help_request') {
      stats.help_turn_count += 1;
    }

    conceptStatsMap[conceptId] = stats;
  });

  const conceptStats = Object.values(conceptStatsMap)
    .map((stats) => ({
      ...stats,
      session_count: conceptSessions[stats.concept_id]?.size || 0,
      active_days_last_14: stats.active_days_last_14.size,
      attempt_before_help_rate: pct(stats.attempt_turn_count, stats.turn_count),
      verified_reconstruction_rate: pct(stats.solid_attempt_count, stats.attempt_turn_count),
    }))
    .sort((a, b) => (parseTimestamp(b.latest_activity_at)?.getTime() || 0) - (parseTimestamp(a.latest_activity_at)?.getTime() || 0));

  const sessionJournal = [...turnRows]
    .sort((a, b) => (parseTimestamp(b.timestamp)?.getTime() || 0) - (parseTimestamp(a.timestamp)?.getTime() || 0))
    .slice(0, 40)
    .map((row) => {
      const [outcomeLabel, nextAction] = journalOutcome(row, convertedNodeKeys);
      return {
        timestamp: row.timestamp,
        concept_id: row.concept_id,
        node_id: row.node_id,
        node_label: row.node_label || row.node_id || 'Untitled node',
        cluster_id: row.cluster_id || null,
        classification: row.classification || null,
        answer_mode: row.answer_mode || null,
        help_request_reason: row.help_request_reason || null,
        outcome_label: outcomeLabel,
        next_action: nextAction,
        gap_label: row.classification && row.classification !== 'solid' ? row.classification : null,
      };
    });

  return {
    source: 'browser_local_storage',
    retrieval_habits: {
      turn_count: turnRows.length,
      attempt_turn_count: attemptTurns.length,
      help_turn_count: helpTurns.length,
      attempt_before_help_rate: pct(attemptTurns.length, turnRows.length),
      help_usage_rate: pct(helpTurns.length, turnRows.length),
      verified_reconstruction_rate_14d: pct(
        recentTurns.filter((row) => row.answer_mode === 'attempt' && row.classification === 'solid').length,
        recentTurns.filter((row) => row.answer_mode === 'attempt').length,
      ),
    },
    cadence: {
      window_days: 14,
      revisit_due_days: dueThresholdDays,
      session_count: sessionKeys.size,
      active_days: activeDays,
      active_days_last_7: activeDaysLast7.size,
      active_days_last_14: activeDaysLast14.size,
      overdue_revisit_count: dueNodes.length,
      due_nodes: dueNodes.slice(0, 8),
      latest_activity_at: latestTimestamp(turnRows),
    },
    conversion_history: {
      conversion_count: conversionHistory.length,
      recent_conversions: conversionHistory
        .sort((a, b) => (parseTimestamp(b.converted_at)?.getTime() || 0) - (parseTimestamp(a.converted_at)?.getTime() || 0))
        .slice(0, 24),
    },
    session_journal: sessionJournal,
    node_history: [...nodeHistory].sort((a, b) => (parseTimestamp(b.last_turn_at)?.getTime() || 0) - (parseTimestamp(a.last_turn_at)?.getTime() || 0)),
    concept_stats: conceptStats,
    paths: {
      drill_log: 'browser_local_storage',
    },
  };
}
