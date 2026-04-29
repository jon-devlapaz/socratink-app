export function escHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function slugify(value) {
  return String(value ?? '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

function shortenLabel(label, maxLength = 32) {
  const text = String(label || '').trim();
  if (!text) return 'Untitled';
  if (text.length <= maxLength) return text;

  const clause = text.split(/[.:;,-]/)[0]?.trim();
  if (clause && clause.length <= maxLength) return clause;

  const words = text.split(/\s+/);
  let compact = '';
  for (const word of words) {
    const next = compact ? `${compact} ${word}` : word;
    if (next.length > maxLength) break;
    compact = next;
  }
  return compact || text.slice(0, maxLength - 3).trimEnd() + '...';
}

function getBackboneLabel(source) {
  const backbonePrinciple = source?.backbone?.[0]?.principle?.trim();
  const thesis = source?.metadata?.core_thesis?.trim();
  return backbonePrinciple || thesis || source?.metadata?.source_title || 'Core Thesis';
}

function getCoreThesisDetail(source) {
  const thesis = source?.metadata?.core_thesis?.trim() || source?.metadata?.thesis?.trim();
  return thesis || 'This node anchors the extracted concept map.';
}

function getStatusLabel(status) {
  if (status === 'solidified' || status === 'solid') return 'solidified through spaced reconstruction';
  if (status === 'primed') return 'primed for study';
  if (status === 'drilled') return 'worth revisiting';
  return status ? shortenLabel(String(status), 24) : '';
}

function getGapLabel(gapType) {
  if (gapType === 'deep') return 'Needs one more clean pass';
  if (gapType === 'shallow') return 'Needs a fuller mechanism';
  if (gapType === 'misconception') return 'Needs correction';
  return gapType ? shortenLabel(String(gapType), 28) : '';
}

function buildOutcomeMeta(data, { includeGapDescription = false } = {}) {
  const pills = [];
  const descriptionPills = [];
  const statusLabel = getStatusLabel(data?.drillStatus);
  const gapLabel = getGapLabel(data?.gapType);

  if (data?.drillStatus === 'solidified' || data?.drillStatus === 'solid') {
    pills.push(`<span class="graph-detail-pill success">${escHtml(statusLabel)}</span>`);
  } else if (data?.state === 'primed' || data?.drillStatus === 'primed') {
    pills.push('<span class="graph-detail-pill" style="background:#e0d8f0;color:#2c1b4d;">primed for study</span>');
  } else if (data?.state === 'drilled' || data?.drillStatus === 'drilled' || data?.gapType) {
    pills.push('<span class="graph-detail-pill warning">worth revisiting</span>');
    if (gapLabel) {
      pills.push(`<span class="graph-detail-pill">${escHtml(gapLabel)}</span>`);
    } else if (statusLabel && statusLabel !== 'Primed') {
      pills.push(`<span class="graph-detail-pill">${escHtml(statusLabel)}</span>`);
    }
  }

  if (includeGapDescription && data?.gapDescription) {
    descriptionPills.push(`<span class="graph-detail-pill">${escHtml(data.gapDescription)}</span>`);
  }

  return {
    pills: pills.join(''),
    descriptionPills: descriptionPills.join(''),
  };
}

function getReachabilityPill(data) {
  if (data?.available && data?.state === 'locked') {
    return '<span class="graph-detail-pill">ready for first attempt</span>';
  }
  return '';
}

function getInspectPrompt(data) {
  if (!data) return 'Start here and rebuild the mechanism from memory.';

  if (data.drillPhase === 'study') {
    return 'Targeted study is open for this node. Re-enter the mechanism view, then return to the map when you are ready to let it incubate.';
  }

  if (data.drillStatus === 'primed') {
    return data.type === 'core' || data.type === 'backbone'
      ? 'Study is on record. Let this idea incubate while you work another reachable branch, then return for spaced re-drill.'
      : 'This room is primed. Work another reachable node before coming back for spaced re-drill.';
  }

  if (data.drillStatus === 'drilled') {
    return data.type === 'core' || data.type === 'backbone'
      ? 'This idea is still settling. Shift outward to another branch, then come back for a cleaner reconstruction.'
      : 'This room still needs another pass. Interleave a different node, then come back for the next re-drill.';
  }

  if (data.type === 'core') {
    return 'What governing idea explains how this whole system behaves? Start here with a cold attempt.';
  }

  if (data.type === 'backbone') {
    return data.available
      ? 'What principle governs this branch, and why does the rest of this territory depend on it?'
      : 'Engage the core thesis first to reveal this backbone branch.';
  }

  if (data.type === 'cluster') {
    return data.available
      ? 'This branch is open. The drill happens inside its rooms, not in the container itself.'
      : 'Work the prerequisite rooms to reveal this branch.';
  }

  if (data.type === 'subnode') {
    return data.available
      ? 'This room is available. Enter with your current model. Study stays hidden until you attempt.'
      : 'Work the branch before drilling this room.';
  }

  return 'Choose a reachable room and make the next attempt.';
}

function getInspectHeading(data) {
  if (!data) return '';
  if (data.state === 'locked' && !data.available && data.type !== 'core') {
    if (data.type === 'cluster') return 'Locked branch container';
    if (data.type === 'backbone') return 'Locked branch';
    return 'Locked drill room';
  }
  if (data.type === 'backbone') return data.label || data.fullLabel || 'Backbone Principle';
  return data.fullLabel || data.label || '';
}

function getInspectReferenceDisclosure(data) {
  const learnedState = data?.drillStatus === 'primed'
    || data?.drillStatus === 'drilled'
    || data?.drillStatus === 'solidified'
    || data?.drillStatus === 'solid';
  const hasReferenceText = Boolean(data?.fullLabel && data?.label && data.fullLabel !== data.label);
  if (data?.type !== 'backbone' || !learnedState || !hasReferenceText) return '';

  return `
    <details class="graph-detail-disclosure">
      <summary>Reference Statement</summary>
      <div class="graph-detail-disclosure-body">${escHtml(data.fullLabel)}</div>
    </details>
  `;
}

function getStudyHeading(data) {
  if (!data) return '';
  if (data.type === 'backbone') return data.label || data.fullLabel || 'Backbone Principle';
  return data.fullLabel || data.label || '';
}

function getStudyBodyMarkup(data) {
  const mechanismText = data?.detail || 'Mechanism not specified.';
  const hasBackboneReference = data?.type === 'backbone'
    && data?.fullLabel
    && data.fullLabel !== data.label;

  if (hasBackboneReference) {
    return `
      <div class="graph-study-reference">
        <div class="graph-detail-kicker">Reference Statement</div>
        <p class="graph-detail-copy graph-study-mechanism">${escHtml(data.fullLabel)}</p>
      </div>
    `;
  }

  return `<p class="graph-detail-copy graph-study-mechanism">${escHtml(mechanismText)}</p>`;
}

function deriveNodeState(status, gapType = null) {
  if (status === 'solidified' || status === 'solid') return 'solidified';
  if (status === 'primed') return 'primed';
  if (status === 'drilled' || gapType) return 'drilled';
  return 'locked';
}

function deriveCoreState(source) {
  return deriveNodeState(source?.metadata?.drill_status, source?.metadata?.gap_type);
}

function deriveBackboneState(item) {
  return deriveNodeState(item?.drill_status, item?.gap_type);
}

function deriveSubnodeState(subnode) {
  return deriveNodeState(subnode?.drill_status, subnode?.gap_type);
}

function deriveClusterState(cluster) {
  const subnodes = Array.isArray(cluster?.subnodes) ? cluster.subnodes : [];
  if (!subnodes.length) return 'locked';
  if (subnodes.every((subnode) => subnode?.drill_status === 'solidified' || subnode?.drill_status === 'solid')) return 'solidified';
  if (subnodes.some((subnode) => subnode?.drill_status === 'primed' || subnode?.drill_status === 'drilled' || subnode?.gap_type)) return 'drilled';
  return 'locked';
}

function isTraversalReadySubnode(subnode) {
  return subnode?.drill_status === 'primed'
    || subnode?.drill_status === 'drilled'
    || subnode?.drill_status === 'solidified'
    || subnode?.drill_status === 'solid'
    || Boolean(subnode?.gap_type);
}

function isClusterTraversalReady(cluster) {
  const subnodes = Array.isArray(cluster?.subnodes) ? cluster.subnodes : [];
  if (!subnodes.length) return false;
  return subnodes.every((subnode) => isTraversalReadySubnode(subnode));
}

export function transformKnowledgeMapToGraph(rawData) {
  const source = typeof rawData === 'string' ? JSON.parse(rawData) : rawData;
  const nodes = [];
  const edges = [];
  const clusters = Array.isArray(source?.clusters) ? source.clusters : [];
  const backboneItems = Array.isArray(source?.backbone) ? source.backbone : [];
  const relationships = source?.relationships || {};
  const coreId = 'core-thesis';
  const clusterMap = new Map();
  const coreState = deriveCoreState(source);
  const coreUnlocked = source?.metadata?.drill_status === 'primed'
    || source?.metadata?.drill_status === 'drilled'
    || source?.metadata?.drill_status === 'solidified'
    || source?.metadata?.drill_status === 'solid';
  const coreSolid = source?.metadata?.drill_status === 'solidified' || source?.metadata?.drill_status === 'solid';
  const unlockedBackboneIds = new Set(
    backboneItems
      .filter((item) => (
        item?.drill_status === 'primed'
        || item?.drill_status === 'drilled'
        || item?.drill_status === 'solidified'
        || item?.drill_status === 'solid'
      ) && item?.id)
      .map((item) => item.id)
  );
  const solidBackboneIds = new Set(
    backboneItems
      .filter((item) => (item?.drill_status === 'solidified' || item?.drill_status === 'solid') && item?.id)
      .map((item) => item.id)
  );
  const clusterToBackbones = new Map();
  const solidClusterIds = new Set(
    clusters
      .filter((cluster) => deriveClusterState(cluster) === 'solidified' && cluster?.id)
      .map((cluster) => cluster.id)
  );
  const traversalReadyClusterIds = new Set(
    clusters
      .filter((cluster) => isClusterTraversalReady(cluster) && cluster?.id)
      .map((cluster) => cluster.id)
  );
  const incomingPrereqs = new Map();

  backboneItems.forEach((item) => {
    (item?.dependent_clusters || []).forEach((clusterId) => {
      const owners = clusterToBackbones.get(clusterId) || [];
      owners.push(item.id);
      clusterToBackbones.set(clusterId, owners);
    });
  });

  (relationships.learning_prerequisites || []).forEach((rel) => {
    if (!rel?.to || !rel?.from) return;
    const reqs = incomingPrereqs.get(rel.to) || [];
    reqs.push(rel.from);
    incomingPrereqs.set(rel.to, reqs);
  });

  nodes.push({
    data: {
      id: coreId,
      type: 'core',
      state: coreState,
      available: 1,
      label: 'Core Thesis',
      fullLabel: 'Core Thesis',
      detail: getCoreThesisDetail(source),
      drillStatus: source?.metadata?.drill_status || null,
      drillPhase: source?.metadata?.drill_phase || null,
      coldAttemptAt: source?.metadata?.cold_attempt_at || null,
      studyCompletedAt: source?.metadata?.study_completed_at || null,
      reDrillEligibleAfter: source?.metadata?.re_drill_eligible_after || null,
      reDrillCount: source?.metadata?.re_drill_count || 0,
      reDrillBand: source?.metadata?.re_drill_band || null,
      gapType: source?.metadata?.gap_type || null,
      gapDescription: source?.metadata?.gap_description || null,
      weight: 1,
    },
    classes: 'node-core-thesis',
  });

  backboneItems.forEach((item, index) => {
    const backboneId = item.id || `backbone-${index + 1}`;
    const backboneState = deriveBackboneState(item);
    const backboneAvailable = coreUnlocked ? 1 : 0;
    const backboneLabel = shortenLabel(item.principle, 32);

    nodes.push({
      data: {
        id: backboneId,
        type: 'backbone',
        state: backboneState,
        available: backboneAvailable,
        label: backboneLabel,
        teaserLabel: 'Locked branch',
        fullLabel: item.principle || `Backbone Principle ${index + 1}`,
        detail: item.principle || '',
        dependentClusters: item.dependent_clusters || [],
        drillStatus: item.drill_status || null,
        drillPhase: item.drill_phase || null,
        coldAttemptAt: item.cold_attempt_at || null,
        studyCompletedAt: item.study_completed_at || null,
        reDrillEligibleAfter: item.re_drill_eligible_after || null,
        reDrillCount: item.re_drill_count || 0,
        reDrillBand: item.re_drill_band || null,
        gapType: item.gap_type || null,
        gapDescription: item.gap_description || null,
        weight: 0.72,
      },
      classes: 'node-backbone',
    });

    edges.push({
      data: {
        id: `struct-${coreId}-${backboneId}`,
        source: coreId,
        target: backboneId,
        type: 'structural',
        label: 'Backbone branch',
        description: 'This backbone principle branches from the core thesis.',
        available: backboneAvailable,
      },
      classes: 'edge-structural edge-core-link',
    });
  });

  clusters.forEach((cluster, clusterIndex) => {
    const clusterId = cluster.id || `cluster-${clusterIndex + 1}`;
    clusterMap.set(clusterId, cluster);
    const ownerBackbones = clusterToBackbones.get(clusterId) || [];
    const backboneGateOpen = ownerBackbones.length
      ? ownerBackbones.some((backboneId) => unlockedBackboneIds.has(backboneId))
      : coreSolid;
    const prerequisites = incomingPrereqs.get(clusterId) || [];
    const prereqGateOpen = prerequisites.every((sourceId) => traversalReadyClusterIds.has(sourceId));
    const clusterAvailable = backboneGateOpen && prereqGateOpen;
    const clusterLabel = shortenLabel(cluster.label, 28);

    nodes.push({
      data: {
        id: clusterId,
        type: 'cluster',
        state: deriveClusterState(cluster),
        available: clusterAvailable ? 1 : 0,
        label: clusterLabel,
        teaserLabel: 'Locked container',
        fullLabel: cluster.label || `Cluster ${clusterIndex + 1}`,
        detail: cluster.description || '',
        orbitLevel: 1,
        subnodeCount: Array.isArray(cluster.subnodes) ? cluster.subnodes.length : 0,
        ownerBackbones,
      },
      classes: 'node-cluster',
    });

    if (ownerBackbones.length) {
      ownerBackbones.forEach((backboneId) => {
        edges.push({
          data: {
            id: `struct-${backboneId}-${clusterId}`,
            source: backboneId,
            target: clusterId,
            type: 'structural',
            label: 'Backbone branch',
            description: 'This cluster depends on the connected backbone principle.',
            available: clusterAvailable ? 1 : 0,
          },
          classes: 'edge-structural',
        });
      });
    } else {
      edges.push({
        data: {
          id: `struct-${coreId}-${clusterId}`,
          source: coreId,
          target: clusterId,
          type: 'structural',
          label: 'Backbone branch',
          description: 'This cluster branches from the core thesis.',
          available: clusterAvailable ? 1 : 0,
        },
        classes: 'edge-structural',
      });
    }

    (cluster.subnodes || []).forEach((subnode, subIndex) => {
      const subnodeId = subnode.id || `${clusterId}-sub-${subIndex + 1}`;
      const subnodeLabel = shortenLabel(subnode.label, 24);
      nodes.push({
        data: {
          id: subnodeId,
          type: 'subnode',
          state: deriveSubnodeState(subnode),
          available: clusterAvailable ? 1 : 0,
          label: subnodeLabel,
          teaserLabel: 'Locked room',
          fullLabel: subnode.label || `Drill Node ${subIndex + 1}`,
          detail: subnode.mechanism || '',
          parentCluster: clusterId,
          orbitLevel: 2,
          drillStatus: subnode.drill_status,
          drillPhase: subnode.drill_phase,
          coldAttemptAt: subnode.cold_attempt_at,
          studyCompletedAt: subnode.study_completed_at,
          reDrillEligibleAfter: subnode.re_drill_eligible_after,
          reDrillCount: subnode.re_drill_count || 0,
          reDrillBand: subnode.re_drill_band || null,
          gapType: subnode.gap_type,
          gapDescription: subnode.gap_description,
        },
        classes: 'node-subnode',
      });

      edges.push({
        data: {
          id: `struct-${clusterId}-${subnodeId}`,
          source: clusterId,
          target: subnodeId,
          type: 'structural',
          label: 'Drill branch',
          description: subnode.mechanism || 'This drill node belongs to the selected cluster.',
          available: clusterAvailable ? 1 : 0,
        },
        classes: 'edge-structural edge-subnode-link',
      });
    });
  });

  (relationships.learning_prerequisites || []).forEach((rel, index) => {
    if (!clusterMap.has(rel.from) || !clusterMap.has(rel.to)) return;
    edges.push({
      data: {
        id: `rel-prereq-${index}-${slugify(`${rel.from}-${rel.to}`)}`,
        source: rel.from,
        target: rel.to,
        type: 'prerequisite',
        label: 'Prerequisite',
        description: rel.rationale || '',
        available: 1,
      },
      classes: 'edge-lateral edge-prerequisite',
    });
  });

  (relationships.domain_mechanics || []).forEach((rel, index) => {
    if (!clusterMap.has(rel.from) || !clusterMap.has(rel.to)) return;
    edges.push({
      data: {
        id: `rel-domain-${index}-${slugify(`${rel.from}-${rel.to}`)}`,
        source: rel.from,
        target: rel.to,
        type: rel.type || 'domain mechanic',
        label: rel.type || 'Domain mechanic',
        description: rel.mechanism || '',
        available: 1,
      },
      classes: 'edge-lateral edge-domain',
    });
  });

  return { source, nodes, edges, coreId, backboneIds: backboneItems.map((item, index) => item.id || `backbone-${index + 1}`) };
}

function repairProgressMarkup({ currentIndex = -1, total = 3, complete = false } = {}) {
  const dotCount = Math.max(Number(total) || 3, 3);
  return `
    <div class="graph-repair-progress" aria-label="Repair Reps progress">
      ${Array.from({ length: dotCount }, (_, index) => (
        `<span class="graph-repair-dot ${complete || currentIndex >= index ? 'is-done' : ''}"></span>`
      )).join('')}
    </div>
  `;
}

function repairContextStripMarkup({ nodeLabel = 'this node', phaseLabel = 'Repair Reps' } = {}) {
  return `
    <div class="graph-repair-context-strip">
      <span>${escHtml(nodeLabel)}</span>
      <span>${escHtml(phaseLabel)}</span>
      <span>Practice only</span>
    </div>
  `;
}

function repairKindLabel(kind) {
  if (kind === 'missing_bridge') return 'Bridge';
  if (kind === 'next_step') return 'Next Step';
  if (kind === 'cause_effect') return 'Cause -> Effect';
  return 'Repair';
}

function repairRatingLabel(rating) {
  if (rating === 'close_match') return 'Close match';
  if (rating === 'partial') return 'Partly linked';
  if (rating === 'missed') return 'Missed the link';
  return 'Not rated';
}

function repairRatingMarkup(state, currentIndex) {
  const ratings = Array.isArray(state.ratings) ? state.ratings : [];
  const selected = ratings[currentIndex] || '';
  const button = (rating, label) => `
    <button class="graph-repair-rating-btn trigger-repair-rate ${selected === rating ? 'is-selected' : ''}" data-rating="${rating}">
      ${escHtml(label)}
    </button>
  `;
  return `
    <div class="graph-repair-rating">
      <div class="graph-detail-kicker">How close was your bridge?</div>
      <div class="graph-repair-rating-group">
        ${button('close_match', 'Close match')}
        ${button('partial', 'Partly linked')}
        ${button('missed', 'Missed the link')}
      </div>
    </div>
  `;
}

const REPAIR_PRE_CONFIDENCE_LABELS = {
  guessing: 'Guessing',
  hunch: 'Have a hunch',
  can_explain: 'Can explain',
};

const REPAIR_RATING_SUMMARY_LABELS = {
  close_match: 'Close match',
  partial: 'Partly linked',
  missed: 'Missed the link',
};

function repairPredictPillsMarkup(currentPreConfidence, isLocked) {
  const selected = typeof currentPreConfidence === 'string' ? currentPreConfidence : '';
  const lockedAttr = isLocked ? ' aria-disabled="true"' : '';
  const lockedClass = isLocked ? ' is-locked' : '';
  const pill = (value, label) => {
    const checked = selected === value ? 'true' : 'false';
    const selClass = selected === value ? ' is-selected' : '';
    return `<button type="button" class="graph-repair-predict-pill trigger-repair-predict${selClass}" data-pre="${value}" role="radio" aria-checked="${checked}">${label}</button>`;
  };
  return `
    <div class="graph-repair-predict">
      <div class="graph-detail-kicker">Before you peek</div>
      <div class="graph-repair-predict-group${lockedClass}" role="radiogroup" aria-label="Confidence before revealing reference"${lockedAttr}>
        ${pill('guessing', 'Guessing')}
        ${pill('hunch', 'Have a hunch')}
        ${pill('can_explain', 'Can explain')}
      </div>
    </div>
  `;
}

function repairCalibrationSummaryMarkup(preConfidences, ratings) {
  const preList = Array.isArray(preConfidences) ? preConfidences : [];
  const rateList = Array.isArray(ratings) ? ratings : [];
  const rowCount = Math.min(preList.length, rateList.length);
  if (rowCount === 0) return '';
  const rows = [];
  for (let i = 0; i < rowCount; i += 1) {
    const preLabel = REPAIR_PRE_CONFIDENCE_LABELS[preList[i]] || 'Not recorded';
    const rateLabel = REPAIR_RATING_SUMMARY_LABELS[rateList[i]] || 'Not recorded';
    rows.push(`
      <div class="graph-repair-summary-row">
        <span class="graph-repair-summary-rep">Rep ${i + 1}</span>
        <span class="graph-repair-summary-pair"><span class="muted">Predicted:</span> ${escHtml(preLabel)}</span>
        <span class="graph-repair-summary-pair"><span class="muted">Rated:</span> ${escHtml(rateLabel)}</span>
      </div>
    `);
  }
  return `<div class="graph-repair-summary graph-repair-calibration">${rows.join('')}</div>`;
}

function repairRepsMarkupForNode(data, repairState = {}) {
  const state = repairState || {};
  const actionButtonClass = 'btn-start-drill graph-detail-action';
  const nodeLabel = state.nodeLabel || data.fullLabel || data.label || 'this node';
  const status = state.status || 'idle';

  if (status === 'loading') {
    return `
      ${repairContextStripMarkup({ nodeLabel, phaseLabel: 'Repair Reps' })}
      <section class="graph-detail-surface graph-repair-card">
        <div class="graph-detail-kicker">Repair Reps</div>
        ${repairProgressMarkup({ currentIndex: -1, total: 3 })}
        <h3 class="graph-detail-title">${escHtml(nodeLabel)}</h3>
        <p class="graph-detail-copy">Building three causal reps for this node. This is practice, not graph-truth evidence.</p>
      </section>
    `;
  }

  if (status === 'error') {
    return `
      ${repairContextStripMarkup({ nodeLabel, phaseLabel: 'Repair Reps' })}
      <div class="graph-detail-kicker">Repair Reps</div>
      <h3 class="graph-detail-title">Reps did not load</h3>
      <p class="graph-detail-copy">${escHtml(state.error || 'Repair Reps could not load. Reopen study and try again later.')}</p>
      <button class="${actionButtonClass} trigger-reopen">Reopen Study</button>
      <button class="${actionButtonClass} trigger-repair-exit graph-detail-secondary-action graph-repair-secondary-action">Back to graph</button>
    `;
  }

  if (status === 'complete') {
    const reps = Array.isArray(state.reps) ? state.reps : [];
    const ratings = Array.isArray(state.ratings) ? state.ratings : [];
    const preConfidences = Array.isArray(state.preConfidences) ? state.preConfidences : [];
    const calibrationMarkup = repairCalibrationSummaryMarkup(preConfidences, ratings);
    const legacySummaryRows = reps.length && !calibrationMarkup
      ? reps.map((rep, index) => {
        const rating = ratings[index] || '';
        return `
          <div class="graph-repair-summary-row">
            <span class="graph-detail-pill">${escHtml(repairKindLabel(rep.kind))}</span>
            <span class="graph-repair-summary-rating ${escHtml(rating)}">${escHtml(repairRatingLabel(rating))}</span>
          </div>
        `;
      }).join('')
      : '';
    return `
      ${repairContextStripMarkup({ nodeLabel, phaseLabel: 'Repair Reps logged' })}
      <div class="graph-repair-complete">
        <div class="graph-detail-kicker">Repair Reps</div>
        ${repairProgressMarkup({ currentIndex: 2, total: Math.max(reps.length, 3), complete: true })}
        <h3 class="graph-detail-title">Practice logged</h3>
        <p class="graph-detail-copy">Three bridge reps saved on ${escHtml(nodeLabel)}.</p>
        ${calibrationMarkup || (legacySummaryRows ? `<div class="graph-repair-summary">${legacySummaryRows}</div>` : '')}
        <p class="graph-detail-copy">These reps are saved. Graph truth comes from the next re-drill.</p>
        <button class="${actionButtonClass} trigger-repair-exit">Back to graph</button>
      </div>
    `;
  }

  const reps = Array.isArray(state.reps) ? state.reps : [];
  const currentIndex = Math.min(Math.max(Number(state.currentIndex || 0), 0), Math.max(reps.length - 1, 0));
  const rep = reps[currentIndex] || null;
  if (!rep) {
    return `
      ${repairContextStripMarkup({ nodeLabel, phaseLabel: 'Repair Reps' })}
      <div class="graph-detail-kicker">Repair Reps</div>
      <h3 class="graph-detail-title">${escHtml(nodeLabel)}</h3>
      <p class="graph-detail-copy">Repair Reps are not ready for this node yet.</p>
      <button class="${actionButtonClass} trigger-repair-exit">Back to graph</button>
    `;
  }

  const revealed = Boolean(state.revealed);
  const typedAnswer = escHtml(state.currentAnswer || '');
  const ratingSelected = Boolean(state.ratingSelected || state.ratings?.[currentIndex]);
  const preConfidence = state.currentPreConfidence || '';
  const pillsMarkup = repairPredictPillsMarkup(preConfidence, revealed);
  const preConfidenceValid = preConfidence === 'guessing' || preConfidence === 'hunch' || preConfidence === 'can_explain';
  const hasAnswer = typeof state.currentAnswer === 'string' && state.currentAnswer.trim().length > 0;
  const revealReady = preConfidenceValid && hasAnswer;
  return `
    ${repairContextStripMarkup({ nodeLabel, phaseLabel: `Repair Rep ${currentIndex + 1} of ${reps.length}` })}
    <div class="graph-study-shell graph-repair-shell">
      <section class="graph-detail-surface graph-repair-card ${state.isDealing ? 'is-dealing' : ''}">
        ${repairProgressMarkup({ currentIndex, total: reps.length })}
        <div class="graph-detail-kicker">Causal bridge</div>
        <p class="graph-detail-copy">${escHtml(rep.prompt)}</p>
        ${pillsMarkup}
        <div class="graph-detail-kicker">Your bridge</div>
        <textarea class="graph-repair-input" rows="4" aria-describedby="repair-reveal-helper" ${revealed ? 'readonly' : ''}>${typedAnswer}</textarea>
        ${revealed ? '' : '<p class="graph-detail-copy graph-repair-helper">Trace the causal link in one or two sentences.</p>'}
        ${revealed ? `
          <div class="graph-repair-bridge ${state.isRevealing ? 'is-revealing' : ''}">
            <div class="graph-detail-kicker">Reference bridge</div>
            <p class="graph-detail-copy">${escHtml(rep.target_bridge)}</p>
            <p class="graph-detail-copy graph-repair-compare-cue">Compare the link, not the wording.</p>
          </div>
          ${repairRatingMarkup(state, currentIndex)}
        ` : ''}
      </section>
      <section class="graph-detail-surface graph-study-next graph-repair-next">
        <p class="graph-detail-copy graph-repair-truth-line">Practice only. Graph truth comes from re-drill.</p>
        ${revealed
          ? (ratingSelected
            ? `<button class="${actionButtonClass} trigger-repair-next">${currentIndex + 1 >= reps.length ? 'Finish Reps' : 'Next Rep'}</button>`
            : '<p class="graph-detail-copy graph-repair-rating-hint">Choose the closest comparison before moving on.</p>')
          : `
            <button class="${actionButtonClass} trigger-repair-reveal" ${revealReady ? '' : 'disabled'} aria-describedby="repair-reveal-helper">Lock in and show reference bridge</button>
            <p class="graph-repair-reveal-helper" id="repair-reveal-helper">Pick a stance and type your bridge to continue.</p>
          `}
      </section>
    </div>
  `;
}

function detailMarkupForNode(node, mode = 'inspect', options = {}) {
  const data = node.data();
  const isDrillActive = mode === 'drill-active' || mode === 'cold-attempt-active' || mode === 're-drill-active';
  const isPostDrill = mode === 'post-drill';
  const outcomeMeta = buildOutcomeMeta(data, { includeGapDescription: !isPostDrill });
  const inspectAction = options.inspectAction || null;
  const actionButtonClass = 'btn-start-drill graph-detail-action';
  const inspectButtonHtml = inspectAction
    ? `<button class="${actionButtonClass} trigger-drill" data-action-kind="${escHtml(inspectAction.kind)}">${escHtml(inspectAction.label)}</button>`
    : '';
  const secondaryActionClass = inspectAction?.secondaryAction?.kind === 'start-repair-reps'
    ? ' graph-repair-secondary-action'
    : '';
  const secondaryInspectButtonHtml = inspectAction?.secondaryAction
    ? `<button class="${actionButtonClass} trigger-drill graph-detail-secondary-action${secondaryActionClass}" data-action-kind="${escHtml(inspectAction.secondaryAction.kind)}">${escHtml(inspectAction.secondaryAction.label)}</button>`
    : '';
  const blockedInspectHtml = inspectAction?.blocked
    ? `
      <div class="graph-detail-block">
        <div class="graph-detail-kicker">${escHtml(inspectAction.blocked.headline || 'Not Yet')}</div>
        <p class="graph-detail-copy">${escHtml(inspectAction.blocked.body)}</p>
      </div>
    `
    : '';

  if (mode === 'session-complete') {
    return `
      <div class="graph-detail-kicker">Session Save Point</div>
      <h3 class="graph-detail-title">Enough for this pass</h3>
      <p class="graph-detail-copy">This session has enough retrieval on record. Return later so spaced reconstruction can carry the evidence.</p>
      <button class="${actionButtonClass} trigger-continue">Return to Map</button>
    `;
  }

  if (mode === 'repair-reps') {
    return repairRepsMarkupForNode(data, options.repairRepsState || {});
  }

  if (mode === 'study') {
    const next = options.nextNodeSuggestion;
    const nextStepCopy = next
      ? (next.action === 're-drill'
          ? `Next evidence move: spaced re-drill ${escHtml(next.label)}.`
          : `Next spacing move: enter ${escHtml(next.label)}.`)
      : 'Leave this node to incubate. Work on other nodes before returning to re-drill.';
    return `
      <div class="graph-study-shell">
        <section class="graph-detail-surface graph-study-card">
          <div class="graph-detail-kicker">Targeted Study</div>
          <h3 class="graph-detail-title">${escHtml(getStudyHeading(data))}</h3>
          ${getStudyBodyMarkup(data)}
          <div class="graph-detail-meta graph-detail-meta-compact">
            <span class="graph-detail-pill">primed for study</span>
          </div>
        </section>
        <section class="graph-detail-surface graph-study-next">
          <div class="graph-detail-kicker">Next Step</div>
          <p class="graph-detail-copy">${nextStepCopy}</p>
          <button class="${actionButtonClass} trigger-continue">Return to Map</button>
        </section>
      </div>
    `;
  }

  if (isDrillActive) {
    const kicker = data.type === 'core'
      ? 'Core Thesis'
      : data.type === 'backbone'
        ? 'Backbone Principle'
        : data.type === 'cluster'
          ? 'Cluster Focus'
          : 'Drill Node';
    return `
      <div class="graph-detail-kicker">${escHtml(kicker)}</div>
      <h3 class="graph-detail-title">${escHtml(getInspectHeading(data))}</h3>
      <p class="graph-detail-copy">${mode === 'cold-attempt-active' ? 'Make your best initial attempt. Study opens only after you try.' : 'Reconstruct this from memory. The map stays in the background until the drill resolves.'}</p>
      <div class="graph-detail-meta" style="flex-wrap:wrap; margin-bottom: 8px;">
        ${outcomeMeta.pills}
      </div>
    `;
  }

  if (isPostDrill) {
    const isSolid = data.drillStatus === 'solidified' || data.drillStatus === 'solid';
    const kicker = data.type === 'core'
      ? 'Core Thesis Result'
      : data.type === 'backbone'
      ? 'Backbone Result'
        : data.type === 'cluster'
          ? 'Cluster Result'
          : 'Drill Result';
    const trajectoryHtml = isSolid && data.reDrillBand
      ? `<p class="graph-detail-copy" style="margin-top: 10px; font-size: 0.85em; color: var(--text-secondary);">
           Cold attempt: exploratory guess. Spaced re-drill: <strong>${escHtml(data.reDrillBand)}</strong>. That change is the evidence on record.
         </p>`
      : '';
    return `
      <div class="graph-detail-kicker">${escHtml(kicker)}</div>
      <h3 class="graph-detail-title">${escHtml(data.fullLabel)}</h3>
      <p class="graph-detail-copy">${isSolid ? 'Solidified through spaced reconstruction. This is evidence, not a permanent claim.' : 'Attempt logged. This room is worth revisiting.'}</p>
      <div class="graph-detail-meta" style="flex-wrap:wrap; margin-bottom: 8px;">
        ${isSolid
          ? '<span class="graph-detail-pill success">solidified through spacing</span>'
          : outcomeMeta.pills}
      </div>
      ${trajectoryHtml}
      ${data.gapDescription && !isSolid ? `<p class="graph-detail-copy">${escHtml(data.gapDescription)}</p>` : ''}
      ${!isSolid ? `
        <div class="graph-detail-block">
            <div class="graph-detail-kicker">Reopen Targeted Study</div>
            <p class="graph-detail-copy" style="opacity: 1; color: var(--text-primary);">
               ${escHtml(data.detail || 'Mechanism not specified.')}
            </p>
            <button class="${actionButtonClass} trigger-reopen">Reopen Study</button>
            <button class="${actionButtonClass} trigger-repair graph-detail-secondary-action graph-repair-secondary-action">Start Repair Reps</button>
        </div>
      ` : ''}
      <button class="${actionButtonClass} trigger-continue">Return to Map</button>
    `;
  }

  if (data.type === 'core') {
    return `
      <div class="graph-detail-kicker">Core Thesis</div>
      <h3 class="graph-detail-title">${escHtml(getInspectHeading(data))}</h3>
      <p class="graph-detail-copy">${escHtml(getInspectPrompt(data))}</p>
      <div class="graph-detail-meta" style="flex-wrap:wrap; margin-bottom: 8px;">
        ${outcomeMeta.pills}
        ${outcomeMeta.descriptionPills}
      </div>
      ${inspectButtonHtml || `<button class="${actionButtonClass} trigger-drill" data-action-kind="start-drill">Start With Core Thesis</button>`}
      ${secondaryInspectButtonHtml}
    `;
  }

  if (data.type === 'backbone') {
    return `
      <div class="graph-detail-kicker">Backbone Principle</div>
      <h3 class="graph-detail-title">${escHtml(getInspectHeading(data))}</h3>
      <p class="graph-detail-copy">${escHtml(getInspectPrompt(data))}</p>
      ${getInspectReferenceDisclosure(data)}
      <div class="graph-detail-meta" style="flex-wrap:wrap; margin-bottom: 8px;">
        ${outcomeMeta.pills}
        ${outcomeMeta.descriptionPills}
      </div>
      ${data.available ? (inspectButtonHtml || `<button class="${actionButtonClass} trigger-drill" data-action-kind="start-drill">Start Cold Attempt</button>`) : ''}
      ${data.available ? secondaryInspectButtonHtml : ''}
    `;
  }

  const isLocked = data.state === 'locked';
  const isDrilled = data.state === 'drilled';
  const isAvailable = Boolean(data.available);

  if (data.type === 'cluster') {
    return `
      <div class="graph-detail-kicker">Cluster</div>
      <h3 class="graph-detail-title">${escHtml(getInspectHeading(data))}</h3>
      <p class="graph-detail-copy">${escHtml(getInspectPrompt(data))}</p>
      <div class="graph-detail-meta" style="flex-wrap:wrap; margin-bottom: 8px;">
        <span class="graph-detail-pill">${escHtml(`${data.subnodeCount || 0} drill nodes`)}</span>
        ${getReachabilityPill(data)}
        ${isDrilled ? '<span class="graph-detail-pill warning">In progress</span>' : ''}
      </div>
    `;
  }

  return `
    <div class="graph-detail-kicker">Drill Node</div>
    <h3 class="graph-detail-title">${escHtml(getInspectHeading(data))}</h3>
    <p class="graph-detail-copy">${escHtml(getInspectPrompt(data))}</p>
    <div class="graph-detail-meta" style="flex-wrap:wrap; margin-bottom: 8px;">
      ${getReachabilityPill(data)}
      ${outcomeMeta.pills}
      ${outcomeMeta.descriptionPills}
    </div>
    ${blockedInspectHtml}
    ${isAvailable ? inspectButtonHtml : ''}
    ${isAvailable ? secondaryInspectButtonHtml : ''}
  `;
}

function detailMarkupForEdge(edge, cy) {
  const data = edge.data();
  const source = cy.getElementById(data.source);
  const target = cy.getElementById(data.target);
  const sourceData = source.data();
  const targetData = target.data();
  const hasLockedEndpoint = [sourceData, targetData].some((nodeData) => (
    nodeData?.state === 'locked' && !nodeData?.available
  ));
  const sourceLabel = hasLockedEndpoint
    ? 'Draft connection'
    : (source.data('fullLabel') || source.data('label'));
  const targetLabel = hasLockedEndpoint
    ? 'held until attempt'
    : (target.data('label') || data.target);
  const body = hasLockedEndpoint
    ? 'This connection is part of the proposed route. Its mechanism stays out of view until the adjacent rooms have learner evidence.'
    : (data.description || 'No explanatory text available for this relationship.');

  return `
    <div class="graph-detail-kicker">Connection</div>
    <h3 class="graph-detail-title">${escHtml(sourceLabel)}</h3>
    <p class="graph-detail-copy">${escHtml(body)}</p>
    <div class="graph-detail-meta">
      <span class="graph-detail-pill">${escHtml(data.label || data.type)}</span>
      <span class="graph-detail-pill">${escHtml(targetLabel)}</span>
    </div>
  `;
}

function setEmptyDetail(detailEl, source, mode = 'inspect') {
  if (mode === 'drill-active') {
    detailEl.innerHTML = `
      <div class="graph-detail-kicker">Active Drill</div>
      <h3 class="graph-detail-title">One node at a time</h3>
      <p class="graph-detail-copy">Use the chat to reconstruct the active node from memory. The graph updates only when the outcome provides evidence.</p>
    `;
    return;
  }

  const backboneTitle = escHtml('Core Thesis');
  const starterPrompt = escHtml('What governing idea explains how this whole system behaves? Start here with a cold attempt.');
  detailEl.innerHTML = `
    <div class="graph-detail-kicker">Starting Room</div>
    <h3 class="graph-detail-title">${backboneTitle}</h3>
    <p class="graph-detail-copy">${starterPrompt}</p>
    <div class="graph-detail-meta">
      <span class="graph-detail-pill">core thesis first</span>
      <span class="graph-detail-pill">bright means ready</span>
      <span class="graph-detail-pill">ghosted means locked</span>
    </div>
    <button class="btn-start-drill trigger-drill" style="width:100%; margin-top: 16px;">Start With Core Thesis</button>
  `;
}

function applyEntryAnimation(cy, center) {
  cy.batch(() => {
    cy.nodes().forEach((node) => {
      node.position({ x: center.x, y: center.y });
      node.addClass('is-entering');
    });
  });
}

function applyGraphFocus(cy, activeElement) {
  const neighborhood = activeElement.closedNeighborhood();
  cy.elements().addClass('is-dimmed');
  neighborhood.removeClass('is-dimmed');
  cy.elements().removeClass('is-focus-target');
  activeElement.addClass('is-focus-target');

  if (activeElement.isNode()) {
    const connectedEdges = activeElement.connectedEdges();
    connectedEdges.removeClass('is-dimmed');
    connectedEdges.connectedNodes().removeClass('is-dimmed');
    connectedEdges.addClass('is-focus-target');
    connectedEdges.connectedNodes().addClass('is-focus-target');
  }
}

function clearGraphFocus(cy) {
  cy.elements().removeClass('is-dimmed');
  cy.elements().removeClass('is-focus-target');
}

function syncSelectedElement(cy, selectedElement) {
  cy.elements().removeClass('is-selection-anchor');
  if (!selectedElement?.id) return;

  const element = cy.getElementById(selectedElement.id);
  if (element.length) {
    element.addClass('is-selection-anchor');
  }
}

function readGraphStyleToken(styles, name, fallback) {
  const value = styles.getPropertyValue(name).trim();
  return value || fallback;
}

function readGraphNumberToken(styles, name, fallback) {
  const raw = styles.getPropertyValue(name).trim();
  const parsed = Number.parseFloat(raw);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function getGraphThemeTokens() {
  const styles = getComputedStyle(document.documentElement);
  return {
    nodeBaseFill: readGraphStyleToken(styles, '--graph-node-base-fill', '#ffffff'),
    nodeBaseBorder: readGraphStyleToken(styles, '--graph-node-base-border', '#d7d0f1'),
    nodeBaseText: readGraphStyleToken(styles, '--graph-node-base-text', '#423c58'),

    nodeLockedFill: readGraphStyleToken(styles, '--graph-node-locked-fill', 'rgba(255, 255, 255, 0.08)'),
    nodeLockedRing: readGraphStyleToken(styles, '--graph-node-locked-ring', 'rgba(124, 111, 205, 0.24)'),
    nodeLockedText: readGraphStyleToken(styles, '--graph-node-locked-text', 'rgba(91, 84, 121, 0.42)'),
    nodeLockedOpacity: readGraphNumberToken(styles, '--graph-node-locked-opacity', 0.22),
    nodeLockedTextOpacity: readGraphNumberToken(styles, '--graph-node-locked-text-opacity', 0.56),

    nodeReachableFill: readGraphStyleToken(styles, '--graph-node-reachable-fill', 'rgba(252, 247, 255, 0.99)'),
    nodeReachableRing: readGraphStyleToken(styles, '--graph-node-reachable-ring', '#7c6fcd'),
    nodeReachableHalo: readGraphStyleToken(styles, '--graph-node-reachable-halo', 'rgba(124, 111, 205, 0.48)'),
    nodeReachableText: readGraphStyleToken(styles, '--graph-node-reachable-text', '#4f4384'),
    nodeReachableOverlayOpacity: readGraphNumberToken(styles, '--graph-node-reachable-overlay-opacity', 0.10),

    clusterReachableFill: readGraphStyleToken(styles, '--graph-cluster-reachable-fill', '#f7f2ff'),
    clusterReachableRing: readGraphStyleToken(styles, '--graph-cluster-reachable-ring', '#7c6fcd'),
    clusterReachableText: readGraphStyleToken(styles, '--graph-cluster-reachable-text', '#55488e'),

    nodePrimedFill: readGraphStyleToken(styles, '--graph-node-primed-fill', '#d9eef8'),
    nodePrimedRing: readGraphStyleToken(styles, '--graph-node-primed-ring', '#6eaed1'),
    nodePrimedHalo: readGraphStyleToken(styles, '--graph-node-primed-halo', 'rgba(110, 174, 209, 0.42)'),
    nodePrimedText: readGraphStyleToken(styles, '--graph-node-primed-text', '#215777'),
    nodePrimedOverlayOpacity: readGraphNumberToken(styles, '--graph-node-primed-overlay-opacity', 0.05),
    nodePrimedFlashFill: readGraphStyleToken(styles, '--graph-node-primed-flash-fill', '#eef8fd'),

    nodeDrilledFill: readGraphStyleToken(styles, '--graph-node-drilled-fill', '#d9a14a'),
    nodeDrilledRing: readGraphStyleToken(styles, '--graph-node-drilled-ring', '#e5be78'),
    nodeDrilledHalo: readGraphStyleToken(styles, '--graph-node-drilled-halo', 'rgba(217, 161, 74, 0.40)'),
    nodeDrilledText: readGraphStyleToken(styles, '--graph-node-drilled-text', '#8f5f16'),
    nodeDrilledOverlayOpacity: readGraphNumberToken(styles, '--graph-node-drilled-overlay-opacity', 0.04),

    nodeSolidFill: readGraphStyleToken(styles, '--graph-node-solid-fill', '#7c6fcd'),
    nodeSolidRing: readGraphStyleToken(styles, '--graph-node-solid-ring', '#988be4'),
    nodeSolidHalo: readGraphStyleToken(styles, '--graph-node-solid-halo', 'rgba(124, 111, 205, 0.44)'),
    nodeSolidText: readGraphStyleToken(styles, '--graph-node-solid-text', '#7c6fcd'),
    nodeSolidOverlayOpacity: readGraphNumberToken(styles, '--graph-node-solid-overlay-opacity', 0.06),
    nodeSolidFlashFill: readGraphStyleToken(styles, '--graph-node-solid-flash-fill', '#a895ea'),

    nodeActiveFill: readGraphStyleToken(styles, '--graph-node-active-fill', '#f3efff'),
    nodeActiveRing: readGraphStyleToken(styles, '--graph-node-active-ring', '#7c6fcd'),
    nodeActiveHalo: readGraphStyleToken(styles, '--graph-node-active-halo', 'rgba(124, 111, 205, 0.52)'),
    nodeActiveOverlayOpacity: readGraphNumberToken(styles, '--graph-node-active-overlay-opacity', 0.12),

    nodeSelectionRing: readGraphStyleToken(styles, '--graph-node-selection-ring', '#5b518f'),
    nodeSelectionGlow: readGraphStyleToken(styles, '--graph-node-selection-glow', 'rgba(124, 111, 205, 0.45)'),
    nodeSelectionOverlayOpacity: readGraphNumberToken(styles, '--graph-node-selection-overlay-opacity', 0.08),
    starOpacityMin: readGraphNumberToken(styles, '--graph-star-opacity-min', 0.05),
    starOpacityMax: readGraphNumberToken(styles, '--graph-star-opacity-max', 0.18),

    edgeBase: readGraphStyleToken(styles, '--graph-edge-base', 'rgba(124, 111, 205, 0.10)'),
    edgeStructural: readGraphStyleToken(styles, '--graph-edge-structural', 'rgba(124, 111, 205, 0.10)'),
    edgeSubnode: readGraphStyleToken(styles, '--graph-edge-subnode', 'rgba(124, 111, 205, 0.08)'),
    edgeLateral: readGraphStyleToken(styles, '--graph-edge-lateral', 'rgba(124, 111, 205, 0.45)'),
    edgePrereq: readGraphStyleToken(styles, '--graph-edge-prereq', 'rgba(124, 111, 205, 0.44)'),
    edgeDomain: readGraphStyleToken(styles, '--graph-edge-domain', 'rgba(114, 160, 154, 0.42)'),
    edgeSelection: readGraphStyleToken(styles, '--graph-edge-selection', 'rgba(124, 111, 205, 0.66)'),

    drillMutedFill: readGraphStyleToken(styles, '--graph-drill-muted-fill', 'rgba(226, 226, 226, 1)'),
    drillMutedEdge: readGraphStyleToken(styles, '--graph-drill-muted-edge', 'rgba(200, 200, 200, 0.10)'),

    focusGlowRadius: readGraphNumberToken(styles, '--graph-focus-glow-radius', 120),
    focusGlowOpacity: readGraphNumberToken(styles, '--graph-focus-glow-opacity', 0.5),
  };
}

function installHoverFocus(cy, getInteractionMode) {
  cy.on('mouseover', 'node, edge', (event) => {
    if (getInteractionMode() !== 'inspect') return;
    applyGraphFocus(cy, event.target);
  });

  cy.on('mouseout', 'node, edge', () => {
    if (getInteractionMode() !== 'inspect') return;
    clearGraphFocus(cy);
  });
}

function installSelection(cy, detailEl, source, defaultNodeId, onNodeSelect, onContinue, getInteractionMode, setInteractionMode, setSelectedElement) {
  cy.on('tap', 'node', (event) => {
    setSelectedElement({ type: 'node', id: event.target.id() });
    if (getInteractionMode() !== 'inspect') return;
    const inspectAction = window.SocratinkApp?.getNodeInspectAction?.(event.target.data()) || null;
    detailEl.innerHTML = detailMarkupForNode(event.target, 'inspect', { inspectAction });
    const data = event.target.data();
    const drillBtn = detailEl.querySelector('.trigger-drill');
    if (drillBtn) {
      drillBtn.addEventListener('click', () => {
        const actionKind = drillBtn.dataset.actionKind || 'start-drill';
        if (window.SocratinkApp?.runInspectAction) {
          window.SocratinkApp.runInspectAction(data, actionKind);
          return;
        }
        onNodeSelect?.(data);
      });
    }
  });

  cy.on('tap', 'edge', (event) => {
    setSelectedElement({ type: 'edge', id: event.target.id() });
    if (getInteractionMode() !== 'inspect') return;
    detailEl.innerHTML = detailMarkupForEdge(event.target, cy);
  });

  cy.on('tap', (event) => {
    if (event.target === cy) {
      setSelectedElement({ type: 'node', id: defaultNodeId });
      clearGraphFocus(cy);
      if (getInteractionMode() !== 'inspect') return;
      setEmptyDetail(detailEl, source);
      const drillBtn = detailEl.querySelector('.trigger-drill');
      if (drillBtn) drillBtn.addEventListener('click', () => onNodeSelect?.(null));
    }
  });
}

function installDragBehavior(cy) {
  cy.on('dragfree', 'node', (event) => {
    const node = event.target;
    const neighbors = node.closedNeighborhood().nodes();
    neighbors.forEach((neighbor) => {
      if (neighbor.id() === node.id()) return;
      const current = neighbor.position();
      const anchor = node.position();
      neighbor.animate(
        {
          position: {
            x: current.x + (anchor.x - current.x) * 0.08,
            y: current.y + (anchor.y - current.y) * 0.08,
          },
        },
        {
          duration: 220,
          easing: 'ease-out-cubic',
        }
      );
    });
  });
}

function calculateSolarPositions(cy, center) {
  const positions = {};
  const backboneNodes = cy.nodes('.node-backbone');
  const clusterNodes = cy.nodes('.node-cluster');
  const subnodeNodes = cy.nodes('.node-subnode');
  const backboneCount = Math.max(backboneNodes.length, 1);
  const backboneRadius = Math.max(110, Math.min(170, 90 + backboneCount * 18));

  positions['core-thesis'] = { x: center.x, y: center.y };

  backboneNodes.forEach((backboneNode, backboneIndex) => {
    const backboneAngle = (-Math.PI / 2) + (Math.PI * 2 * backboneIndex) / backboneCount;
    const backboneX = center.x + Math.cos(backboneAngle) * backboneRadius;
    const backboneY = center.y + Math.sin(backboneAngle) * backboneRadius;
    positions[backboneNode.id()] = { x: backboneX, y: backboneY };

    const ownedClusters = clusterNodes.filter((clusterNode) => {
      const owners = clusterNode.data('ownerBackbones') || [];
      return owners.includes(backboneNode.id());
    });
    const ownedCount = ownedClusters.length;
    if (!ownedCount) return;

    const clusterRadius = Math.max(88, Math.min(132, 78 + ownedCount * 8));
    ownedClusters.forEach((clusterNode, clusterIndex) => {
      const spread = ownedCount === 1 ? 0 : ((clusterIndex / (ownedCount - 1)) - 0.5) * 1.1;
      const clusterAngle = backboneAngle + spread;
      const clusterX = backboneX + Math.cos(clusterAngle) * clusterRadius;
      const clusterY = backboneY + Math.sin(clusterAngle) * clusterRadius;
      positions[clusterNode.id()] = { x: clusterX, y: clusterY };

      const satellites = subnodeNodes.filter((subnode) => subnode.data('parentCluster') === clusterNode.id());
      const satelliteCount = satellites.length;
      if (!satelliteCount) return;

      const localRadius = Math.max(42, Math.min(76, 34 + satelliteCount * 4));
      satellites.forEach((subnode, subIndex) => {
        const subAngle = clusterAngle + (Math.PI * 2 * subIndex) / satelliteCount;
        positions[subnode.id()] = {
          x: clusterX + Math.cos(subAngle) * localRadius,
          y: clusterY + Math.sin(subAngle) * localRadius,
        };
      });
    });
  });

  return positions;
}

function installAmbientFloat(cy) {
  const basePositions = new Map();
  const pausedUntil = new Map();
  const draggingIds = new Set();
  let frameId = null;
  let running = true;

  function now() {
    return Date.now();
  }

  function pauseNode(nodeId, duration = 1200) {
    pausedUntil.set(nodeId, now() + duration);
  }

  function captureBasePositions() {
    cy.nodes().forEach((node) => {
      basePositions.set(node.id(), { ...node.position() });
    });
  }

  function syncBasePosition(node) {
    basePositions.set(node.id(), { ...node.position() });
  }

  function tick() {
    if (!running) return;

    const time = now() * 0.001;
    cy.batch(() => {
      cy.nodes().forEach((node, index) => {
        const nodeId = node.id();
        if (draggingIds.has(nodeId)) return;

        const base = basePositions.get(nodeId);
        if (!base) return;

        if ((pausedUntil.get(nodeId) || 0) > now()) {
          node.position(base);
          return;
        }

        const phase = index * 0.9;
        const amplitudeX = node.hasClass('node-core-thesis') ? 2.6 : node.hasClass('node-backbone') ? 2.2 : node.hasClass('node-cluster') ? 2.1 : 1.6;
        const amplitudeY = node.hasClass('node-core-thesis') ? 3.8 : node.hasClass('node-backbone') ? 3.2 : node.hasClass('node-cluster') ? 3.0 : 2.2;
        node.position({
          x: base.x + Math.sin(time * 0.72 + phase) * amplitudeX,
          y: base.y + Math.cos(time * 0.58 + phase) * amplitudeY,
        });
      });
    });

    frameId = window.requestAnimationFrame(tick);
  }

  cy.on('tap', 'node', (event) => {
    pauseNode(event.target.id(), 1400);
  });

  cy.on('grab', 'node', (event) => {
    const node = event.target;
    draggingIds.add(node.id());
    pauseNode(node.id(), 1600);
  });

  cy.on('drag', 'node', (event) => {
    syncBasePosition(event.target);
  });

  cy.on('free', 'node', (event) => {
    const node = event.target;
    draggingIds.delete(node.id());
    syncBasePosition(node);
    pauseNode(node.id(), 1600);
  });

  frameId = window.requestAnimationFrame(tick);

  return {
    captureBasePositions,
    destroy() {
      running = false;
      if (frameId) window.cancelAnimationFrame(frameId);
    },
  };
}

export function mountKnowledgeGraph({ container, detailEl, rawData, onNodeSelect, onContinue }) {
  if (!container || !detailEl) return null;

  const transformed = transformKnowledgeMapToGraph(rawData);
  if (!transformed.nodes.length) {
    container.innerHTML = '<div class="graph-empty">No extracted graph data is available yet.</div>';
    setEmptyDetail(detailEl, transformed.source);
    return {
      destroy() {},
      resize() {},
      getSelectedElement() { return null; },
      getInteractionMode() { return 'inspect'; },
      getActiveDrillNode() { return null; },
      selectElement() {},
    };
  }

  const VIEWBOX = { width: 760, height: 560, centerX: 380, centerY: 280 };
  const DRILL_CONTEXT_MODES = new Set(['drill-active', 'cold-attempt-active', 're-drill-active', 'study', 'repair-reps']);
  const splitClasses = (value = '') => String(value || '').split(/\s+/).filter(Boolean);
  const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
  const degToRad = (degrees) => (degrees * Math.PI) / 180;
  const polar = (origin, angle, distance) => ({
    x: origin.x + Math.cos(angle) * distance,
    y: origin.y + Math.sin(angle) * distance,
    angle,
  });

  const createSeededRandom = (seedSource = 'graph') => {
    let seed = 2166136261;
    for (const char of String(seedSource)) {
      seed ^= char.charCodeAt(0);
      seed = Math.imul(seed, 16777619);
    }
    return () => {
      seed += 0x6D2B79F5;
      let t = seed;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  };

  const buildModel = (nextTransformed) => {
    const nodes = nextTransformed.nodes.map((entry, order) => ({
      ...entry.data,
      classes: splitClasses(entry.classes),
      order,
    }));
    const edges = nextTransformed.edges.map((entry, order) => ({
      ...entry.data,
      classes: splitClasses(entry.classes),
      order,
    }));
    const nodeById = new Map(nodes.map((node) => [node.id, node]));
    const edgeById = new Map(edges.map((edge) => [edge.id, edge]));
    const edgeIdsByNode = new Map(nodes.map((node) => [node.id, new Set()]));
    const neighborIdsByNode = new Map(nodes.map((node) => [node.id, new Set()]));
    const clusterIdsByBackbone = new Map(
      nodes.filter((node) => node.type === 'backbone').map((node) => [node.id, []])
    );
    const subnodeIdsByCluster = new Map(
      nodes.filter((node) => node.type === 'cluster').map((node) => [node.id, []])
    );
    const structuralParentByNodeId = new Map();
    const unownedClusterIds = [];

    edges.forEach((edge) => {
      if (edgeIdsByNode.has(edge.source)) edgeIdsByNode.get(edge.source).add(edge.id);
      if (edgeIdsByNode.has(edge.target)) edgeIdsByNode.get(edge.target).add(edge.id);
      if (neighborIdsByNode.has(edge.source)) neighborIdsByNode.get(edge.source).add(edge.target);
      if (neighborIdsByNode.has(edge.target)) neighborIdsByNode.get(edge.target).add(edge.source);
      if (edge.classes.includes('edge-structural')) {
        structuralParentByNodeId.set(edge.target, edge.source);
      }
    });

    nodes.filter((node) => node.type === 'cluster').forEach((cluster) => {
      const owners = Array.isArray(cluster.ownerBackbones)
        ? cluster.ownerBackbones.filter((ownerId) => clusterIdsByBackbone.has(ownerId))
        : [];
      if (owners.length) {
        owners.forEach((ownerId) => clusterIdsByBackbone.get(ownerId).push(cluster.id));
        return;
      }
      const structuralParent = structuralParentByNodeId.get(cluster.id);
      if (clusterIdsByBackbone.has(structuralParent)) {
        clusterIdsByBackbone.get(structuralParent).push(cluster.id);
        return;
      }
      unownedClusterIds.push(cluster.id);
    });

    nodes.filter((node) => node.type === 'subnode').forEach((subnode) => {
      const parentCluster = subnode.parentCluster;
      if (!subnodeIdsByCluster.has(parentCluster)) {
        subnodeIdsByCluster.set(parentCluster, []);
      }
      subnodeIdsByCluster.get(parentCluster).push(subnode.id);
    });

    return {
      source: nextTransformed.source,
      coreId: nextTransformed.coreId,
      backboneIds: [...nextTransformed.backboneIds],
      nodes,
      edges,
      nodeById,
      edgeById,
      edgeIdsByNode,
      neighborIdsByNode,
      clusterIdsByBackbone,
      subnodeIdsByCluster,
      structuralParentByNodeId,
      unownedClusterIds,
    };
  };

  const createEmptyRef = () => ({
    length: 0,
    data(key) {
      return typeof key === 'string' ? undefined : {};
    },
    id() {
      return '';
    },
  });

  const createNodeRef = (node) => (
    node ? {
      length: 1,
      data(key) {
        return typeof key === 'string' ? node[key] : node;
      },
      id() {
        return node.id;
      },
    } : createEmptyRef()
  );

  const createEdgeRef = (edge) => (
    edge ? {
      length: 1,
      data(key) {
        return typeof key === 'string' ? edge[key] : edge;
      },
      id() {
        return edge.id;
      },
    } : createEmptyRef()
  );

  const createLookup = (model) => ({
    getElementById(id) {
      if (model.nodeById.has(id)) return createNodeRef(model.nodeById.get(id));
      if (model.edgeById.has(id)) return createEdgeRef(model.edgeById.get(id));
      return createEmptyRef();
    },
  });

  const buildStarsMarkup = (seedSource, count = 80, sizeFloor = 1, sizeRange = 2.2) => {
    const rand = createSeededRandom(seedSource);
    const minOpacity = Math.min(graphTheme.starOpacityMin, graphTheme.starOpacityMax);
    const maxOpacity = Math.max(graphTheme.starOpacityMin, graphTheme.starOpacityMax);
    return Array.from({ length: count }, () => {
      const left = (rand() * 100).toFixed(3);
      const top = (rand() * 100).toFixed(3);
      const size = (sizeFloor + rand() * sizeRange).toFixed(2);
      const delay = (rand() * 4).toFixed(2);
      const duration = (2.4 + rand() * 3.2).toFixed(2);
      const opacity = (minOpacity + rand() * (maxOpacity - minOpacity)).toFixed(2);
      return `<span style="left:${left}%;top:${top}%;width:${size}px;height:${size}px;opacity:${opacity};animation-delay:${delay}s;animation-duration:${duration}s;"></span>`;
    }).join('');
  };

  const phaseForId = (id) => {
    let h = 0;
    const s = String(id || '');
    for (let i = 0; i < s.length; i += 1) h = (h * 31 + s.charCodeAt(i)) | 0;
    const frac = ((h >>> 0) % 1000) / 1000;
    return `-${(frac * 6.5).toFixed(2)}s`;
  };

  const getNodeRadius = (node) => {
    if (node.type === 'core') return 14;
    if (node.type === 'backbone') return 9;
    if (node.type === 'cluster') return 7;
    return 3.5;
  };

  const getNodeLabelOffset = (node) => {
    if (node.type === 'core') return 34;
    if (node.type === 'backbone' || node.type === 'cluster') return 26;
    return 14;
  };

  const getNodeLabelSize = (node) => {
    if (node.type === 'core') return 11;
    return 10;
  };

  const buildLabelLines = (text, maxLength = 24) => {
    const cleaned = String(text || '').trim();
    if (!cleaned) return [];
    if (cleaned.length <= maxLength) return [cleaned];

    const words = cleaned.split(/\s+/);
    const lines = [];
    let current = '';
    let index = 0;

    for (; index < words.length; index += 1) {
      const word = words[index];
      const candidate = current ? `${current} ${word}` : word;
      if (candidate.length > maxLength && current) {
        lines.push(current);
        current = word;
        if (lines.length === 1) continue;
        break;
      }
      current = candidate;
    }

    if (current && lines.length < 2) {
      lines.push(current);
    }

    if (index < words.length - 1 && lines.length) {
      lines[lines.length - 1] = shortenLabel(
        `${lines[lines.length - 1]} ${words.slice(index + 1).join(' ')}`.trim(),
        maxLength
      );
    }

    return lines.slice(0, 2);
  };

  const resolveBackboneAngles = (count) => {
    const presets = {
      1: [-90],
      2: [-118, 28],
      3: [-90, 30, 150],
      4: [-122, -38, 42, 142],
      5: [-132, -66, 0, 66, 132],
    };
    if (presets[count]) return presets[count].map(degToRad);
    const spanStart = degToRad(-136);
    const spanEnd = degToRad(136);
    return Array.from({ length: count }, (_, index) => (
      spanStart + ((spanEnd - spanStart) * index) / Math.max(count - 1, 1)
    ));
  };

  const resolveAngularSpread = (count, maxSpread) => {
    if (count <= 1) return [0];
    return Array.from({ length: count }, (_, index) => (
      ((index / (count - 1)) - 0.5) * maxSpread * 2
    ));
  };

  const calculateLayout = (model) => {
    const positions = new Map();
    const center = { x: VIEWBOX.centerX, y: VIEWBOX.centerY, angle: 0 };
    positions.set(model.coreId, center);

    const backbones = model.nodes.filter((node) => node.type === 'backbone');
    const backboneAngles = resolveBackboneAngles(backbones.length || 1);
    const backboneRadius = clamp(144 + backbones.length * 4, 150, 184);

    backbones.forEach((backbone, index) => {
      const angle = backboneAngles[index] ?? degToRad(-90);
      positions.set(backbone.id, polar(center, angle, backboneRadius));
    });

    backbones.forEach((backbone) => {
      const backbonePos = positions.get(backbone.id);
      if (!backbonePos) return;
      const clusterIds = model.clusterIdsByBackbone.get(backbone.id) || [];
      const spread = resolveAngularSpread(clusterIds.length, 0.68);
      const distance = clamp(92 + clusterIds.length * 12, 94, 136);
      clusterIds.forEach((clusterId, index) => {
        positions.set(clusterId, polar(backbonePos, backbonePos.angle + spread[index], distance));
      });
    });

    const unownedSpread = resolveAngularSpread(model.unownedClusterIds.length, 1.12);
    model.unownedClusterIds.forEach((clusterId, index) => {
      const angle = degToRad(90) + (unownedSpread[index] || 0);
      positions.set(clusterId, polar(center, angle, 208));
    });

    model.nodes.filter((node) => node.type === 'cluster').forEach((cluster) => {
      const clusterPos = positions.get(cluster.id);
      if (!clusterPos) return;
      const subnodeIds = model.subnodeIdsByCluster.get(cluster.id) || [];
      const radius = clamp(36 + subnodeIds.length * 6, 42, 72);
      const angleSeed = clusterPos.angle + Math.PI / 4;
      subnodeIds.forEach((subnodeId, index) => {
        const angle = angleSeed + ((Math.PI * 2 * index) / Math.max(subnodeIds.length, 1));
        positions.set(subnodeId, polar(clusterPos, angle, radius));
      });
    });

    return positions;
  };

  const buildCurvePath = (sourcePos, targetPos, direction = 1) => {
    const dx = targetPos.x - sourcePos.x;
    const dy = targetPos.y - sourcePos.y;
    const length = Math.hypot(dx, dy) || 1;
    const normalX = -dy / length;
    const normalY = dx / length;
    const curve = clamp(length * 0.22, 32, 86) * direction;
    const midX = (sourcePos.x + targetPos.x) / 2 + normalX * curve;
    const midY = (sourcePos.y + targetPos.y) / 2 + normalY * curve;
    return `M ${sourcePos.x} ${sourcePos.y} Q ${midX} ${midY} ${targetPos.x} ${targetPos.y}`;
  };

  const getInspectFocus = (model, focusElement) => {
    if (!focusElement?.id) return null;
    if (focusElement.type === 'edge') {
      const edge = model.edgeById.get(focusElement.id);
      if (!edge) return null;
      return {
        nodeIds: new Set([edge.source, edge.target]),
        edgeIds: new Set([edge.id]),
      };
    }

    const nodeId = focusElement.id;
    const nodeIds = new Set([nodeId]);
    const edgeIds = new Set(model.edgeIdsByNode.get(nodeId) || []);
    for (const neighborId of model.neighborIdsByNode.get(nodeId) || []) {
      nodeIds.add(neighborId);
    }
    return { nodeIds, edgeIds };
  };

  const getDrillContext = (model, nodeId) => {
    if (!nodeId) return null;
    const activeNode = model.nodeById.get(nodeId);
    if (!activeNode) return null;

    const activeNodeIds = new Set([activeNode.id]);
    const contextNodeIds = new Set();
    const prereqNodeIds = new Set();
    const contextEdgeIds = new Set();
    const prereqEdgeIds = new Set();
    const anchorId = activeNode.type === 'subnode' && activeNode.parentCluster
      ? activeNode.parentCluster
      : activeNode.id;

    if (anchorId && anchorId !== activeNode.id) {
      contextNodeIds.add(anchorId);
    }

    model.edges.forEach((edge) => {
      if (edge.classes.includes('edge-subnode-link') && (edge.source === activeNode.id || edge.target === activeNode.id)) {
        contextEdgeIds.add(edge.id);
        contextNodeIds.add(edge.source);
        contextNodeIds.add(edge.target);
      }
      if (edge.classes.includes('edge-prerequisite') && (edge.source === anchorId || edge.target === anchorId)) {
        prereqEdgeIds.add(edge.id);
        prereqNodeIds.add(edge.source);
        prereqNodeIds.add(edge.target);
      }
    });

    activeNodeIds.forEach((id) => {
      contextNodeIds.delete(id);
      prereqNodeIds.delete(id);
    });
    contextNodeIds.delete(anchorId);

    return {
      activeNodeIds,
      contextNodeIds,
      prereqNodeIds,
      contextEdgeIds,
      prereqEdgeIds,
      anchorId,
    };
  };

  const resolveNodePalette = (theme, node, flashKind = null) => {
    const isLockedUnavailable = node.state === 'locked' && !node.available;
    const isReachableLocked = node.state === 'locked' && node.available;
    if (isLockedUnavailable) {
      return {
        fill: theme.nodeLockedFill,
        ring: theme.nodeLockedRing,
        halo: theme.nodeLockedRing,
        label: theme.nodeLockedText,
        bodyOpacity: theme.nodeLockedOpacity,
        labelOpacity: theme.nodeLockedTextOpacity,
        highlightOpacity: 0.05,
        haloOpacity: 0.18,
      };
    }
    if (isReachableLocked) {
      return {
        fill: node.type === 'cluster' ? theme.clusterReachableFill : theme.nodeReachableFill,
        ring: node.type === 'cluster' ? theme.clusterReachableRing : theme.nodeReachableRing,
        halo: theme.nodeReachableHalo,
        label: node.type === 'cluster' ? theme.clusterReachableText : theme.nodeReachableText,
        bodyOpacity: 1,
        labelOpacity: 1,
        highlightOpacity: 0.24,
        haloOpacity: 0.55,
      };
    }
    if (node.state === 'primed') {
      return {
        fill: flashKind === 'primed' ? theme.nodePrimedFlashFill : theme.nodePrimedFill,
        ring: theme.nodePrimedRing,
        halo: theme.nodePrimedHalo,
        label: theme.nodePrimedText,
        bodyOpacity: 1,
        labelOpacity: 1,
        highlightOpacity: 0.24,
        haloOpacity: 0.55,
      };
    }
    if (node.state === 'drilled') {
      return {
        fill: theme.nodeDrilledFill,
        ring: theme.nodeDrilledRing,
        halo: theme.nodeDrilledHalo,
        label: theme.nodeDrilledText,
        bodyOpacity: 1,
        labelOpacity: 1,
        highlightOpacity: 0.24,
        haloOpacity: 0.55,
      };
    }
    if (node.state === 'solidified') {
      return {
        fill: flashKind === 'solid' ? theme.nodeSolidFlashFill : theme.nodeSolidFill,
        ring: theme.nodeSolidRing,
        halo: theme.nodeSolidHalo,
        label: theme.nodeSolidText,
        bodyOpacity: 1,
        labelOpacity: 1,
        highlightOpacity: 0.24,
        haloOpacity: 0.55,
      };
    }
    return {
      fill: theme.nodeBaseFill,
      ring: theme.nodeBaseBorder,
      halo: theme.nodeSelectionGlow,
      label: theme.nodeBaseText,
      bodyOpacity: 1,
      labelOpacity: 1,
      highlightOpacity: 0.18,
      haloOpacity: 0.22,
    };
  };

  const buildNodeAriaLabel = (node) => {
    const stateLabel = node.state === 'solidified'
      ? 'solidified through spaced reconstruction'
      : node.state === 'drilled'
        ? 'worth revisiting'
        : node.state === 'primed'
          ? 'primed for study'
          : node.available
            ? 'ready for first attempt'
            : 'locked';
    if (node.state === 'locked' && !node.available && node.type !== 'core') {
      const kind = node.type === 'cluster'
        ? 'locked branch container'
        : node.type === 'backbone'
          ? 'locked branch'
          : 'locked drill room';
      return `${kind}, ${stateLabel}`;
    }
    return `${node.fullLabel || node.label || node.id}, ${stateLabel}`;
  };

  const isBeamEligible = (edge) => Boolean(
    edge
    && edge.classes.includes('edge-structural')
    && edge.available === 1
  );

  const graphTheme = getGraphThemeTokens();
  const prefersReducedMotion = Boolean(window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches);
  const rewardTimeoutIds = [];
  const flashTimeoutByNodeId = new Map();
  const freshSolidIds = new Set();
  const freshSolidTimeouts = new Map();
  let activePathIds = new Set();
  let freshlyFocusedNodeId = null;
  let arrivalGlowTimeoutId = null;
  let panRafId = null;
  let breadcrumbRafId = null;
  let currentViewBox = { x: 0, y: 0, w: VIEWBOX.width, h: VIEWBOX.height };
  let model = buildModel(transformed);
  let lookup = createLookup(model);
  let positions = calculateLayout(model);
  let selectedElement = { type: 'node', id: model.coreId };
  let hoveredElement = null;
  let interactionMode = 'inspect';
  let activeDrillNodeId = null;
  let destroyed = false;
  const flashKindsByNodeId = new Map();

  const starSeed = `${model.source?.metadata?.source_title || 'graph'}:${model.backboneIds.join('|')}`;
  container.innerHTML = `
    <div class="graph-stage-stars" aria-hidden="true">
      ${buildStarsMarkup(starSeed, 80)}
    </div>
    <div class="graph-stage-stars graph-stage-stars-far" aria-hidden="true">
      ${buildStarsMarkup(`${starSeed}:far`, 28, 0.8, 1.4)}
    </div>
    <svg class="graph-svg" viewBox="0 0 ${VIEWBOX.width} ${VIEWBOX.height}" preserveAspectRatio="xMidYMid meet"></svg>
  `;
  const svgEl = container.querySelector('.graph-svg');
  currentViewBox = { x: 0, y: 0, w: VIEWBOX.width, h: VIEWBOX.height };
  if (!svgEl) {
    container.innerHTML = '<div class="graph-empty">Graph renderer failed to mount. Draft view is still available.</div>';
    setEmptyDetail(detailEl, rawData);
    return {
      destroy() {},
      resize() {},
      getSelectedElement() { return null; },
      getInteractionMode() { return 'inspect'; },
      getActiveDrillNode() { return null; },
      selectElement() {},
    };
  }

  const syncInteractionChrome = () => {
    const graphDetail = detailEl.closest('.graph-detail');
    if (graphDetail) {
      graphDetail.className = 'graph-detail';
      if (interactionMode !== 'inspect') graphDetail.classList.add('is-' + interactionMode);
    }

    const graphLayout = detailEl.closest('.graph-layout');
    if (graphLayout) {
      graphLayout.className = 'graph-layout';
      if (interactionMode !== 'inspect') graphLayout.classList.add('mode-' + interactionMode);
    }
  };

  const clearRewardPanelClasses = () => {
    detailEl.classList.remove('is-primed-reward-panel', 'is-solid-reward-panel');
  };

  const triggerPanelReward = (kind) => {
    clearRewardPanelClasses();
    const className = kind === 'solid' ? 'is-solid-reward-panel' : 'is-primed-reward-panel';
    detailEl.classList.add(className);
    const timeoutId = window.setTimeout(() => {
      detailEl.classList.remove(className);
    }, prefersReducedMotion ? 180 : (kind === 'solid' ? 920 : 760));
    rewardTimeoutIds.push(timeoutId);
  };

  const queueFlash = (nodeId, kind, duration) => {
    if (!nodeId || !model.nodeById.has(nodeId)) return;
    flashKindsByNodeId.set(nodeId, kind);
    if (flashTimeoutByNodeId.has(nodeId)) {
      window.clearTimeout(flashTimeoutByNodeId.get(nodeId));
    }
    const timeoutId = window.setTimeout(() => {
      flashKindsByNodeId.delete(nodeId);
      flashTimeoutByNodeId.delete(nodeId);
      renderGraph();
    }, duration);
    flashTimeoutByNodeId.set(nodeId, timeoutId);
    if (kind === 'solid' && !prefersReducedMotion) {
      markFreshSolid(nodeId);
    }
  };

  const markFreshSolid = (nodeId) => {
    freshSolidIds.add(nodeId);
    if (freshSolidTimeouts.has(nodeId)) {
      window.clearTimeout(freshSolidTimeouts.get(nodeId));
    }
    const tid = window.setTimeout(() => {
      freshSolidIds.delete(nodeId);
      freshSolidTimeouts.delete(nodeId);
      if (!destroyed) renderGraph();
    }, 10000);
    freshSolidTimeouts.set(nodeId, tid);
  };

  const easeStandard = (u) => {
    // Approximation of cubic-bezier(0.2, 0.8, 0.2, 1) — fast start, smooth settle.
    const t = Math.max(0, Math.min(1, u));
    return 1 - Math.pow(1 - t, 3);
  };

  const setViewBoxAttr = (box) => {
    svgEl.setAttribute('viewBox', `${box.x} ${box.y} ${box.w} ${box.h}`);
    currentViewBox = { ...box };
  };

  const centerViewBoxOn = (pos, w, h) => ({
    x: pos.x - w / 2,
    y: pos.y - h / 2,
    w,
    h,
  });

  const markFreshlyFocused = (nodeId) => {
    if (!nodeId) return;
    freshlyFocusedNodeId = nodeId;
    renderGraph();
    if (arrivalGlowTimeoutId) window.clearTimeout(arrivalGlowTimeoutId);
    arrivalGlowTimeoutId = window.setTimeout(() => {
      freshlyFocusedNodeId = null;
      arrivalGlowTimeoutId = null;
      if (!destroyed) renderGraph();
    }, 450);
  };

  const panViewBoxTo = (pos, durationMs = 900) => {
    if (!pos) return;
    const target = centerViewBoxOn(pos, VIEWBOX.width, VIEWBOX.height);
    if (prefersReducedMotion) {
      setViewBoxAttr(target);
      markFreshlyFocused(activeDrillNodeId);
      return;
    }
    const start = { ...currentViewBox };
    const t0 = performance.now();
    if (panRafId) cancelAnimationFrame(panRafId);
    const tick = (now) => {
      if (destroyed) return;
      const u = Math.min(1, (now - t0) / durationMs);
      const e = easeStandard(u);
      setViewBoxAttr({
        x: start.x + (target.x - start.x) * e,
        y: start.y + (target.y - start.y) * e,
        w: start.w + (target.w - start.w) * e,
        h: start.h + (target.h - start.h) * e,
      });
      if (u < 1) {
        panRafId = requestAnimationFrame(tick);
      } else {
        panRafId = null;
        markFreshlyFocused(activeDrillNodeId);
      }
    };
    panRafId = requestAnimationFrame(tick);
  };

  const startBreadcrumbAnimation = () => {
    if (breadcrumbRafId) { cancelAnimationFrame(breadcrumbRafId); breadcrumbRafId = null; }
    const pip = svgEl.querySelector('.graph-breadcrumb-pip');
    if (!pip || prefersReducedMotion) return;
    const fromX = parseFloat(pip.dataset.fromX);
    const fromY = parseFloat(pip.dataset.fromY);
    const toX = parseFloat(pip.dataset.toX);
    const toY = parseFloat(pip.dataset.toY);
    if (!Number.isFinite(fromX + fromY + toX + toY)) return;
    const periodMs = 3600;
    const t0 = performance.now();
    const tick = (now) => {
      if (destroyed) return;
      const live = svgEl.querySelector('.graph-breadcrumb-pip');
      if (!live) { breadcrumbRafId = null; return; }
      const u = ((now - t0) % periodMs) / periodMs;
      // Travel on 0..0.85; dormant 0.85..1. Ease-in-out along travel window.
      let progress = 0;
      let opacity = 0;
      if (u < 0.85) {
        const w = u / 0.85;
        progress = w < 0.5 ? 2 * w * w : 1 - Math.pow(-2 * w + 2, 2) / 2;
        if (u < 0.08) opacity = u / 0.08 * 0.9;
        else if (u > 0.75) opacity = Math.max(0, (0.85 - u) / 0.10 * 0.9);
        else opacity = 0.9;
      }
      const cx = fromX + (toX - fromX) * progress;
      const cy = fromY + (toY - fromY) * progress;
      live.setAttribute('cx', cx.toFixed(2));
      live.setAttribute('cy', cy.toFixed(2));
      live.style.opacity = opacity.toFixed(3);
      breadcrumbRafId = requestAnimationFrame(tick);
    };
    breadcrumbRafId = requestAnimationFrame(tick);
  };

  const findNextNodeSuggestion = (activeNodeId) => {
    const coldCandidate = model.nodes.find((node) => (
      node.id !== activeNodeId
      && node.available === 1
      && node.state === 'locked'
      && (node.type === 'subnode' || node.type === 'backbone')
    ));
    if (!coldCandidate) return null;
    return {
      id: coldCandidate.id,
      label: coldCandidate.fullLabel || coldCandidate.label,
      action: 'explore',
    };
  };

  const updateSelectedElement = (nextSelected) => {
    if (nextSelected?.id) {
      selectedElement = { type: nextSelected.type === 'edge' ? 'edge' : 'node', id: nextSelected.id };
      return;
    }
    selectedElement = { type: 'node', id: model.coreId };
  };

  const renderDetail = () => {
    const getSelectedNodeId = () => (
      selectedElement.type === 'node' && selectedElement.id ? selectedElement.id : model.coreId
    );

    const wireInspectActions = (nodeRef) => {
      const data = nodeRef.data();
      detailEl.querySelectorAll('.trigger-drill').forEach((drillBtn) => {
        drillBtn.addEventListener('click', () => {
          const actionKind = drillBtn.dataset.actionKind || 'start-drill';
          if (window.SocratinkApp?.runInspectAction) {
            window.SocratinkApp.runInspectAction(data, actionKind);
            return;
          }
          onNodeSelect?.(data);
        });
      });
    };

    const wireOutcomeActions = (nodeRef, mode) => {
      const data = nodeRef.data();
      const continueBtn = detailEl.querySelector('.trigger-continue');
      if (continueBtn) {
        if (mode === 'study') {
          continueBtn.addEventListener('click', () => { window.SocratinkApp?.completeStudy?.(nodeRef.id()); });
        } else {
          continueBtn.addEventListener('click', () => { onContinue?.(); });
        }
      }

      const reopenBtn = detailEl.querySelector('.trigger-reopen');
      if (reopenBtn) reopenBtn.addEventListener('click', () => { window.SocratinkApp?.reopenStudy?.(data); });

      const repairBtn = detailEl.querySelector('.trigger-repair');
      if (repairBtn) repairBtn.addEventListener('click', () => { window.SocratinkApp?.startRepairReps?.(data); });

      const repairInput = detailEl.querySelector('.graph-repair-input');
      const repairRevealBtn = detailEl.querySelector('.trigger-repair-reveal');
      const repairState = window.SocratinkApp?.getRepairRepsState?.(nodeRef.id()) || null;
      const preConfidenceValid = repairState
        && (repairState.currentPreConfidence === 'guessing'
          || repairState.currentPreConfidence === 'hunch'
          || repairState.currentPreConfidence === 'can_explain');

      if (repairInput && repairRevealBtn) {
        const syncRevealReadiness = () => {
          const hasAnswer = repairInput.value.trim().length > 0;
          repairRevealBtn.disabled = !(preConfidenceValid && hasAnswer);
        };
        syncRevealReadiness();
        repairInput.addEventListener('input', syncRevealReadiness);
      }

      if (repairRevealBtn) {
        repairRevealBtn.addEventListener('click', () => {
          window.SocratinkApp?.revealRepairRep?.(repairInput?.value || '');
        });
      }

      detailEl.querySelectorAll('.trigger-repair-predict').forEach((btn) => {
        btn.addEventListener('click', () => {
          window.SocratinkApp?.setRepairRepDraft?.(repairInput?.value || '');
          window.SocratinkApp?.setRepairRepPreConfidence?.(btn.dataset.pre);
        });
      });

      const repairNextBtn = detailEl.querySelector('.trigger-repair-next');
      if (repairNextBtn) repairNextBtn.addEventListener('click', () => { window.SocratinkApp?.nextRepairRep?.(); });

      detailEl.querySelectorAll('.trigger-repair-rate').forEach((btn) => {
        btn.addEventListener('click', () => {
          window.SocratinkApp?.rateRepairRep?.(btn.dataset.rating);
        });
      });

      const repairExitBtn = detailEl.querySelector('.trigger-repair-exit');
      if (repairExitBtn) repairExitBtn.addEventListener('click', () => { window.SocratinkApp?.exitRepairReps?.(); });
    };

    if (interactionMode === 'drill-active' || interactionMode === 'cold-attempt-active' || interactionMode === 're-drill-active') {
      const activeRef = lookup.getElementById(getSelectedNodeId());
      if (activeRef.length) {
        detailEl.innerHTML = detailMarkupForNode(activeRef, interactionMode);
      } else {
        setEmptyDetail(detailEl, model.source, 'drill-active');
      }
      return;
    }

    if (interactionMode === 'post-drill' || interactionMode === 'study' || interactionMode === 'session-complete' || interactionMode === 'repair-reps') {
      const activeRef = lookup.getElementById(getSelectedNodeId());
      if (!activeRef.length) {
        setEmptyDetail(detailEl, model.source, 'inspect');
        return;
      }
      const options = interactionMode === 'study'
        ? { nextNodeSuggestion: findNextNodeSuggestion(activeRef.id()) }
        : interactionMode === 'repair-reps'
          ? { repairRepsState: window.SocratinkApp?.getRepairRepsState?.(activeRef.id()) || null }
          : {};
      detailEl.innerHTML = detailMarkupForNode(activeRef, interactionMode, options);
      wireOutcomeActions(activeRef, interactionMode);
      return;
    }

    if (selectedElement.type === 'node' && selectedElement.id) {
      const nodeRef = lookup.getElementById(selectedElement.id);
      if (nodeRef.length) {
        const inspectAction = window.SocratinkApp?.getNodeInspectAction?.(nodeRef.data()) || null;
        detailEl.innerHTML = detailMarkupForNode(nodeRef, 'inspect', { inspectAction });
        wireInspectActions(nodeRef);
        return;
      }
    }

    if (selectedElement.type === 'edge' && selectedElement.id) {
      const edgeRef = lookup.getElementById(selectedElement.id);
      if (edgeRef.length) {
        detailEl.innerHTML = detailMarkupForEdge(edgeRef, lookup);
        return;
      }
    }

    setEmptyDetail(detailEl, model.source, 'inspect');
    const drillBtn = detailEl.querySelector('.trigger-drill');
    if (drillBtn) {
      drillBtn.addEventListener('click', () => onNodeSelect?.(null));
    }
  };

  const computeActivePathIds = (drillContext) => {
    const MAX_ANIMATED = 7;
    const animatableNodes = model.nodes.filter((n) => (n.state === 'primed' || n.state === 'drilled') && n.available);
    if (drillContext) {
      const ids = new Set();
      drillContext.activeNodeIds?.forEach?.((id) => ids.add(id));
      drillContext.prereqNodeIds?.forEach?.((id) => ids.add(id));
      drillContext.contextNodeIds?.forEach?.((id) => ids.add(id));
      if (ids.size <= MAX_ANIMATED) return ids;
      const cx = currentViewBox.x + currentViewBox.w / 2;
      const cy = currentViewBox.y + currentViewBox.h / 2;
      const sorted = [...ids]
        .map((id) => {
          const p = positions.get(id);
          const d = p ? Math.hypot(p.x - cx, p.y - cy) : Infinity;
          return { id, d };
        })
        .sort((a, b) => a.d - b.d)
        .slice(0, MAX_ANIMATED);
      return new Set(sorted.map((e) => e.id));
    }
    if (animatableNodes.length <= MAX_ANIMATED) return new Set(animatableNodes.map((n) => n.id));
    const cx = currentViewBox.x + currentViewBox.w / 2;
    const cy = currentViewBox.y + currentViewBox.h / 2;
    return new Set(
      animatableNodes
        .map((n) => {
          const p = positions.get(n.id);
          const d = p ? Math.hypot(p.x - cx, p.y - cy) : Infinity;
          return { id: n.id, d };
        })
        .sort((a, b) => a.d - b.d)
        .slice(0, MAX_ANIMATED)
        .map((e) => e.id)
    );
  };

  const renderGraph = () => {
    if (destroyed) return;
    const inspectFocus = interactionMode === 'inspect'
      ? getInspectFocus(model, hoveredElement || selectedElement)
      : null;
    const drillContext = DRILL_CONTEXT_MODES.has(interactionMode)
      ? getDrillContext(model, activeDrillNodeId || (selectedElement.type === 'node' ? selectedElement.id : null))
      : null;
    activePathIds = computeActivePathIds(drillContext);
    const hoveredNodeId = hoveredElement?.type === 'node' ? hoveredElement.id : null;
    const focusNodeId = activeDrillNodeId || (selectedElement.type === 'node' ? selectedElement.id : model.coreId);
    const focusNode = model.nodeById.get(focusNodeId) || model.nodeById.get(model.coreId);
    const focusPalette = focusNode ? resolveNodePalette(graphTheme, focusNode, flashKindsByNodeId.get(focusNode.id)) : null;

    const BRIDGE_MODES = new Set(['inspect', 'post-drill', 'study', 'session-complete', 'repair-reps']);
    const breadcrumbEdge = (() => {
      if (!BRIDGE_MODES.has(interactionMode)) return null;
      // Skip when active drill is running — drill beam owns the edge-motion slot
      if (DRILL_CONTEXT_MODES.has(interactionMode)) return null;
      // Focus must be a node the learner has already engaged with (primed/drilled/solidified)
      // so we don't nag when they're just looking at a fresh graph.
      const focusNode = model.nodeById.get(focusNodeId);
      const engaged = focusNode && (focusNode.state === 'primed' || focusNode.state === 'drilled' || focusNode.state === 'solidified');
      if (!engaged) return null;
      const suggestion = findNextNodeSuggestion(focusNodeId);
      if (!suggestion?.id) return null;
      return model.edges.find((edge) => (
        edge.classes.includes('edge-structural')
        && ((edge.source === focusNodeId && edge.target === suggestion.id)
          || (edge.target === focusNodeId && edge.source === suggestion.id))
      )) || null;
    })();

    const beamEdge = (() => {
      if (activeDrillNodeId) {
        const parentId = model.structuralParentByNodeId.get(activeDrillNodeId) || '';
        return model.edges.find((edge) => (
          edge.source === parentId
          && edge.target === activeDrillNodeId
          && edge.classes.includes('edge-structural')
        )) || null;
      }
      if (selectedElement.type !== 'edge' || !selectedElement.id) return null;
      const selectedEdge = model.edgeById.get(selectedElement.id) || null;
      return isBeamEligible(selectedEdge) ? selectedEdge : null;
    })();

    const focusGlowMarkup = focusNode
      ? `<defs>
          <linearGradient id="graph-beam-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="${graphTheme.nodeSelectionRing}" stop-opacity="0"></stop>
            <stop offset="50%" stop-color="${graphTheme.nodeSelectionRing}" stop-opacity="0.95"></stop>
            <stop offset="100%" stop-color="${graphTheme.nodeSelectionRing}" stop-opacity="0"></stop>
          </linearGradient>
          <radialGradient id="graph-focus-glow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stop-color="${focusPalette?.ring || graphTheme.nodeSelectionRing}" stop-opacity="${graphTheme.focusGlowOpacity}"></stop>
            <stop offset="100%" stop-color="${focusPalette?.ring || graphTheme.nodeSelectionRing}" stop-opacity="0"></stop>
          </radialGradient>
        </defs>
        <circle cx="${positions.get(focusNode.id)?.x ?? VIEWBOX.centerX}" cy="${positions.get(focusNode.id)?.y ?? VIEWBOX.centerY}" r="${graphTheme.focusGlowRadius}" fill="url(#graph-focus-glow)"></circle>`
      : '';

    const edgeMarkup = model.edges.map((edge, index) => {
      const sourcePos = positions.get(edge.source);
      const targetPos = positions.get(edge.target);
      if (!sourcePos || !targetPos) return '';

      const isSelected = selectedElement.type === 'edge' && selectedElement.id === edge.id;
      let stroke = graphTheme.edgeBase;
      let strokeWidth = 1;
      let opacity = edge.available ? 0.92 : 0.16;
      let pathMarkup = '';
      let dashArray = '';

      if (edge.classes.includes('edge-structural')) {
        stroke = edge.classes.includes('edge-subnode-link') ? graphTheme.edgeSubnode : graphTheme.edgeStructural;
        strokeWidth = edge.classes.includes('edge-subnode-link') ? 0.7 : 1.2;
        if (!edge.available) {
          opacity = edge.classes.includes('edge-subnode-link') ? 0.18 : 0.28;
        }
        pathMarkup = `<line x1="${sourcePos.x}" y1="${sourcePos.y}" x2="${targetPos.x}" y2="${targetPos.y}" stroke="${stroke}" stroke-width="${strokeWidth}" stroke-linecap="round" opacity="${opacity}"></line>`;
      } else {
        const curveDirection = index % 2 === 0 ? 1 : -1;
        stroke = edge.classes.includes('edge-domain') ? graphTheme.edgeDomain : graphTheme.edgePrereq;
        strokeWidth = 1;
        dashArray = '2 5';
        opacity = 0.8;
        pathMarkup = `<path d="${buildCurvePath(sourcePos, targetPos, curveDirection)}" fill="none" stroke="${stroke}" stroke-width="${strokeWidth}" stroke-dasharray="${dashArray}" opacity="${opacity}"></path>`;
      }

      if (drillContext) {
        if (drillContext.contextEdgeIds.has(edge.id)) {
          opacity = 0.48;
        } else if (drillContext.prereqEdgeIds.has(edge.id)) {
          opacity = 0.56;
          stroke = graphTheme.edgePrereq;
        } else {
          opacity = 0.08;
          stroke = graphTheme.drillMutedEdge;
        }
      } else if (inspectFocus && !inspectFocus.edgeIds.has(edge.id)) {
        opacity *= 0.22;
      }

      if (isSelected) {
        opacity = 1;
        stroke = graphTheme.edgeSelection;
        strokeWidth = edge.classes.includes('edge-lateral') ? 1.8 : 2.2;
      }

      const isNextSuggestion = breadcrumbEdge && edge.id === breadcrumbEdge.id;
      const edgeClass = `graph-edge${isNextSuggestion ? ' is-next-suggestion' : ''}`;

      if (edge.classes.includes('edge-structural')) {
        return `<g class="${edgeClass}" data-graph-kind="edge" data-graph-id="${escHtml(edge.id)}" tabindex="0" role="button" aria-label="${escHtml(edge.label || edge.type || 'Connection')}">
          <line x1="${sourcePos.x}" y1="${sourcePos.y}" x2="${targetPos.x}" y2="${targetPos.y}" stroke="${stroke}" stroke-width="${strokeWidth}" stroke-linecap="round" opacity="${opacity}"></line>
          <line x1="${sourcePos.x}" y1="${sourcePos.y}" x2="${targetPos.x}" y2="${targetPos.y}" stroke="rgba(255,255,255,0.001)" stroke-width="${Math.max(strokeWidth * 10, 14)}" stroke-linecap="round" opacity="1"></line>
        </g>`;
      }

      return `<g class="${edgeClass}" data-graph-kind="edge" data-graph-id="${escHtml(edge.id)}" tabindex="0" role="button" aria-label="${escHtml(edge.label || edge.type || 'Connection')}">
        <path d="${buildCurvePath(sourcePos, targetPos, index % 2 === 0 ? 1 : -1)}" fill="none" stroke="${stroke}" stroke-width="${strokeWidth}" stroke-dasharray="${dashArray}" opacity="${opacity}"></path>
        <path d="${buildCurvePath(sourcePos, targetPos, index % 2 === 0 ? 1 : -1)}" fill="none" stroke="rgba(255,255,255,0.001)" stroke-width="14" opacity="1"></path>
      </g>`;
    }).join('');

    const beamMarkup = (() => {
      if (!beamEdge || prefersReducedMotion) return '';
      const sourcePos = positions.get(beamEdge.source);
      const targetPos = positions.get(beamEdge.target);
      if (!sourcePos || !targetPos) return '';
      const arrivalCircle = `<circle class="graph-beam-arrival" cx="${targetPos.x}" cy="${targetPos.y}" r="2" fill="${graphTheme.nodeSelectionRing}"></circle>`;
      if (beamEdge.classes.includes('edge-lateral')) {
        return `<path class="graph-beam" d="${buildCurvePath(sourcePos, targetPos, 1)}" fill="none" stroke="url(#graph-beam-gradient)" stroke-width="2.5" stroke-dasharray="10 180"></path>${arrivalCircle}`;
      }
      return `<line class="graph-beam" x1="${sourcePos.x}" y1="${sourcePos.y}" x2="${targetPos.x}" y2="${targetPos.y}" stroke="url(#graph-beam-gradient)" stroke-width="2.5" stroke-dasharray="10 180"></line>${arrivalCircle}`;
    })();

    const breadcrumbMarkup = (() => {
      if (!breadcrumbEdge || prefersReducedMotion) return '';
      const src = positions.get(breadcrumbEdge.source);
      const tgt = positions.get(breadcrumbEdge.target);
      if (!src || !tgt) return '';
      const from = breadcrumbEdge.source === focusNodeId ? src : tgt;
      const to   = breadcrumbEdge.source === focusNodeId ? tgt : src;
      // Stash endpoints on the element so RAF driver can read them without re-lookup
      return `
        <circle class="graph-breadcrumb-pip" r="3.2" cx="${from.x}" cy="${from.y}"
                data-from-x="${from.x}" data-from-y="${from.y}"
                data-to-x="${to.x}" data-to-y="${to.y}"></circle>
        <circle class="graph-breadcrumb-arrival" cx="${to.x}" cy="${to.y}" r="10" fill="none" stroke="var(--accent-secondary)" stroke-width="1.2"></circle>
      `;
    })();

    const nodeMarkup = model.nodes.map((node) => {
      const position = positions.get(node.id);
      if (!position) return '';
      const radius = getNodeRadius(node);
      const flashKind = flashKindsByNodeId.get(node.id) || null;
      const palette = resolveNodePalette(graphTheme, node, flashKind);
      const isSelected = selectedElement.type === 'node' && selectedElement.id === node.id;
      const isActive = activeDrillNodeId === node.id;
      const showLabel = node.type !== 'subnode' || isSelected || isActive;
      let nodeOpacity = palette.bodyOpacity;
      let labelOpacity = palette.labelOpacity;
      let haloOpacity = palette.haloOpacity;

      if (drillContext) {
        if (drillContext.activeNodeIds.has(node.id)) {
          nodeOpacity = 1;
          labelOpacity = 1;
          haloOpacity = 0.72;
        } else if (drillContext.contextNodeIds.has(node.id) || node.id === drillContext.anchorId) {
          nodeOpacity = 0.52;
          labelOpacity = node.type === 'subnode' ? 0 : 0.32;
          haloOpacity = 0.22;
        } else if (drillContext.prereqNodeIds.has(node.id)) {
          nodeOpacity = 0.6;
          labelOpacity = node.type === 'subnode' ? 0 : 0.38;
          haloOpacity = 0.22;
        } else {
          nodeOpacity = Math.min(nodeOpacity, 0.16);
          labelOpacity = 0;
          haloOpacity = 0.06;
        }
      } else if (inspectFocus && !inspectFocus.nodeIds.has(node.id)) {
        nodeOpacity *= 0.22;
        labelOpacity = 0;
        haloOpacity *= 0.12;
      }

      const maskLockedLabel = node.state === 'locked' && !node.available && node.type !== 'core';
      const label = node.type === 'core'
        ? String(node.label || 'Core Thesis').toUpperCase()
        : maskLockedLabel
          ? String(node.teaserLabel || 'locked room')
          : String(node.label || node.fullLabel || '');
      const labelLines = node.type === 'core'
        ? [label]
        : buildLabelLines(label, node.type === 'backbone' ? 24 : 20);
      const labelColor = palette.label;
      const highlightOpacity = node.state === 'locked' && !node.available ? 0.05 : palette.highlightOpacity;
      const selectionRadius = radius * (node.type === 'core' ? 2.8 : 2.3);
      const pulseRadius = radius * (node.type === 'core' ? 2.6 : 2.2);
      const haloRadius = radius * (node.type === 'core' ? 2.4 : 2.4);

      const stateAttr = node.state || (node.available ? 'reachable' : 'locked');
      const hasMotion = !prefersReducedMotion && activePathIds.has(node.id) ? '1' : '0';
      const isFreshSolid = freshSolidIds.has(node.id) && !prefersReducedMotion ? '1' : '0';
      const isFreshFocus = freshlyFocusedNodeId === node.id && !prefersReducedMotion;
      const phase = phaseForId(node.id);
      const nodeClass = [
        'graph-node',
        isFreshFocus ? 'is-freshly-focused' : '',
      ].filter(Boolean).join(' ');

      return `<g class="${nodeClass}" data-graph-kind="node" data-graph-id="${escHtml(node.id)}" data-state="${escHtml(stateAttr)}" data-available="${node.available ? 1 : 0}" data-has-motion="${hasMotion}" data-is-fresh-solid="${isFreshSolid}" style="--node-phase:${phase};--halo-rest:${haloOpacity.toFixed(3)};--node-halo-color:${palette.halo};" tabindex="0" role="button" aria-label="${escHtml(buildNodeAriaLabel(node))}">
        <title>${escHtml(maskLockedLabel ? 'locked room' : (node.fullLabel || node.label || node.id))}</title>
        ${haloOpacity > 0.03 ? `<circle class="graph-node-halo" cx="${position.x}" cy="${position.y}" r="${haloRadius}" fill="${palette.halo}" opacity="${haloOpacity}" style="filter: blur(var(--graph-halo-blur, 6px));"></circle>` : ''}
        <circle class="graph-node-arrival-glow" cx="${position.x}" cy="${position.y}" r="${haloRadius * 1.15}" fill="${palette.halo}" style="filter: blur(8px);"></circle>
        ${(isActive || isSelected) && !prefersReducedMotion ? (() => {
          const rippleStroke = isActive ? graphTheme.nodeActiveRing : graphTheme.nodeSelectionRing;
          const startR = radius * 1.4;
          const endR = selectionRadius * 1.8;
          const scale = (endR / startR).toFixed(2);
          const rippleStyle = `--ripple-scale:${scale};`;
          return `
            <circle class="graph-node-ripple" cx="${position.x}" cy="${position.y}" r="${startR}" fill="none" stroke="${rippleStroke}" stroke-width="1.4" style="${rippleStyle}"></circle>
            <circle class="graph-node-ripple is-delayed" cx="${position.x}" cy="${position.y}" r="${startR}" fill="none" stroke="${rippleStroke}" stroke-width="1.4" style="${rippleStyle}"></circle>
          `;
        })() : ''}
        <circle class="graph-node-body" cx="${position.x}" cy="${position.y}" r="${radius}" fill="${palette.fill}" stroke="${isActive ? graphTheme.nodeActiveRing : isSelected ? graphTheme.nodeSelectionRing : palette.ring}" stroke-width="${isActive ? 1.3 : 0.8}" opacity="${nodeOpacity}"></circle>
        ${stateAttr !== 'locked' ? `<circle class="graph-node-core" cx="${position.x}" cy="${position.y}" r="${Math.max(radius * 0.35, 2.2)}" opacity="${nodeOpacity}"></circle>` : ''}
        <circle cx="${position.x - radius * 0.25}" cy="${position.y - radius * 0.25}" r="${radius * 0.35}" fill="#ffffff" opacity="${highlightOpacity * (labelOpacity > 0 ? 1 : 0.8) * 0.5}"></circle>
        <circle cx="${position.x}" cy="${position.y}" r="${Math.max(radius + 12, 16)}" fill="transparent" pointer-events="all"></circle>
        ${showLabel ? `<text x="${position.x}" y="${position.y + getNodeLabelOffset(node) - (labelLines.length > 1 ? 6 : 0)}" text-anchor="middle" class="node-label" fill="${labelColor}" opacity="${labelOpacity}" style="font-size:${getNodeLabelSize(node)}px;${node.type === 'core' ? 'letter-spacing:0.06em;' : ''}">
          ${labelLines.map((line, index) => (
            `<tspan x="${position.x}" dy="${index === 0 ? 0 : 10}">${escHtml(line)}</tspan>`
          )).join('')}
        </text>` : ''}
      </g>`;
    }).join('');

    svgEl.innerHTML = `${focusGlowMarkup}${edgeMarkup}${beamMarkup}${breadcrumbMarkup}${nodeMarkup}`;
    startBreadcrumbAnimation();
  };

  const selectGraphElement = (kind, id, { preserveMode = false } = {}) => {
    if (!id) return;
    if (!preserveMode) {
      interactionMode = 'inspect';
      activeDrillNodeId = null;
      syncInteractionChrome();
    }
    updateSelectedElement({ type: kind, id });
    hoveredElement = null;
    renderGraph();
    renderDetail();
  };

  const setHoverClass = (kind, id) => {
    if (prefersReducedMotion) return;
    const prev = svgEl.querySelector('.graph-node.is-hover, .graph-edge.is-hover');
    if (prev) prev.classList.remove('is-hover');
    if (kind === 'node' && id) {
      const next = svgEl.querySelector(`.graph-node[data-graph-id="${CSS.escape(id)}"]`);
      if (next) next.classList.add('is-hover');
    }
  };

  const handlePointerOver = (event) => {
    const target = event.target.closest?.('[data-graph-kind]');
    if (!target) return;
    const nextHovered = { type: target.dataset.graphKind === 'edge' ? 'edge' : 'node', id: target.dataset.graphId };
    if (hoveredElement?.type === nextHovered.type && hoveredElement?.id === nextHovered.id) return;
    hoveredElement = nextHovered;
    setHoverClass(nextHovered.type, nextHovered.id);
  };

  const handlePointerOut = (event) => {
    const currentTarget = event.target.closest?.('[data-graph-kind]');
    if (!currentTarget) return;
    const related = event.relatedTarget?.closest?.('[data-graph-kind]');
    if (related && related.dataset.graphKind === currentTarget.dataset.graphKind && related.dataset.graphId === currentTarget.dataset.graphId) {
      return;
    }
    hoveredElement = null;
    setHoverClass(null, null);
  };

  const handleClick = (event) => {
    const target = event.target.closest?.('[data-graph-kind]');
    if (!target) {
      hoveredElement = null;
      selectedElement = { type: 'node', id: model.coreId };
      interactionMode = 'inspect';
      activeDrillNodeId = null;
      syncInteractionChrome();
      renderGraph();
      setEmptyDetail(detailEl, model.source, 'inspect');
      const drillBtn = detailEl.querySelector('.trigger-drill');
      if (drillBtn) {
        drillBtn.addEventListener('click', () => onNodeSelect?.(null));
      }
      return;
    }
    const nextType = target.dataset.graphKind === 'edge' ? 'edge' : 'node';
    selectGraphElement(nextType, target.dataset.graphId, { preserveMode: false });
  };

  const handleKeyDown = (event) => {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    const target = event.target.closest?.('[data-graph-kind]');
    if (!target) return;
    event.preventDefault();
    selectGraphElement(target.dataset.graphKind === 'edge' ? 'edge' : 'node', target.dataset.graphId, { preserveMode: false });
  };

  container.addEventListener('pointerover', handlePointerOver);
  container.addEventListener('pointerout', handlePointerOut);
  container.addEventListener('click', handleClick);
  container.addEventListener('keydown', handleKeyDown);

  // ── Wheel-zoom + drag-pan ────────────────────────────────
  const ZOOM_MIN = 0.4;
  const ZOOM_MAX = 3.0;
  let dragState = null;

  const clientToSvgPoint = (clientX, clientY) => {
    const rect = svgEl.getBoundingClientRect();
    if (!rect.width || !rect.height) return { x: currentViewBox.x, y: currentViewBox.y };
    const u = (clientX - rect.left) / rect.width;
    const v = (clientY - rect.top) / rect.height;
    return {
      x: currentViewBox.x + u * currentViewBox.w,
      y: currentViewBox.y + v * currentViewBox.h,
    };
  };

  const handleWheel = (event) => {
    if (prefersReducedMotion) return;
    event.preventDefault();
    if (panRafId) { cancelAnimationFrame(panRafId); panRafId = null; }
    const factor = Math.exp(event.deltaY * 0.0015);
    const baseW = VIEWBOX.width;
    const baseH = VIEWBOX.height;
    const nextW = Math.max(baseW / ZOOM_MAX, Math.min(baseW / ZOOM_MIN, currentViewBox.w * factor));
    const nextH = nextW * (baseH / baseW);
    const focal = clientToSvgPoint(event.clientX, event.clientY);
    const ratioX = (focal.x - currentViewBox.x) / currentViewBox.w;
    const ratioY = (focal.y - currentViewBox.y) / currentViewBox.h;
    setViewBoxAttr({
      x: focal.x - ratioX * nextW,
      y: focal.y - ratioY * nextH,
      w: nextW,
      h: nextH,
    });
  };

  const handlePointerDown = (event) => {
    if (event.button !== 0) return;
    if (event.target.closest?.('[data-graph-kind]')) return; // let click select
    dragState = {
      startX: event.clientX,
      startY: event.clientY,
      originX: currentViewBox.x,
      originY: currentViewBox.y,
      pointerId: event.pointerId,
      moved: false,
    };
    if (panRafId) { cancelAnimationFrame(panRafId); panRafId = null; }
    container.setPointerCapture?.(event.pointerId);
    container.style.cursor = 'grabbing';
  };

  const handlePointerMove = (event) => {
    if (!dragState || event.pointerId !== dragState.pointerId) return;
    const rect = svgEl.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const dx = (event.clientX - dragState.startX) * (currentViewBox.w / rect.width);
    const dy = (event.clientY - dragState.startY) * (currentViewBox.h / rect.height);
    if (Math.abs(event.clientX - dragState.startX) > 3 || Math.abs(event.clientY - dragState.startY) > 3) {
      dragState.moved = true;
    }
    setViewBoxAttr({
      x: dragState.originX - dx,
      y: dragState.originY - dy,
      w: currentViewBox.w,
      h: currentViewBox.h,
    });
  };

  const handlePointerUp = (event) => {
    if (!dragState || event.pointerId !== dragState.pointerId) return;
    container.releasePointerCapture?.(event.pointerId);
    container.style.cursor = '';
    const moved = dragState.moved;
    dragState = null;
    if (moved) {
      // Suppress the click that follows a drag
      const stop = (e) => { e.stopPropagation(); container.removeEventListener('click', stop, true); };
      container.addEventListener('click', stop, true);
    }
  };

  svgEl.addEventListener('wheel', handleWheel, { passive: false });
  container.addEventListener('pointerdown', handlePointerDown);
  container.addEventListener('pointermove', handlePointerMove);
  container.addEventListener('pointerup', handlePointerUp);
  container.addEventListener('pointercancel', handlePointerUp);

  syncInteractionChrome();
  renderGraph();
  renderDetail();

  return {
    destroy() {
      destroyed = true;
      rewardTimeoutIds.forEach((timeoutId) => window.clearTimeout(timeoutId));
      flashTimeoutByNodeId.forEach((timeoutId) => window.clearTimeout(timeoutId));
      flashTimeoutByNodeId.clear();
      freshSolidTimeouts.forEach((timeoutId) => window.clearTimeout(timeoutId));
      freshSolidTimeouts.clear();
      freshSolidIds.clear();
      if (arrivalGlowTimeoutId) window.clearTimeout(arrivalGlowTimeoutId);
      if (panRafId) cancelAnimationFrame(panRafId);
      if (breadcrumbRafId) cancelAnimationFrame(breadcrumbRafId);
      container.removeEventListener('pointerover', handlePointerOver);
      container.removeEventListener('pointerout', handlePointerOut);
      container.removeEventListener('click', handleClick);
      container.removeEventListener('keydown', handleKeyDown);
      svgEl.removeEventListener('wheel', handleWheel);
      container.removeEventListener('pointerdown', handlePointerDown);
      container.removeEventListener('pointermove', handlePointerMove);
      container.removeEventListener('pointerup', handlePointerUp);
      container.removeEventListener('pointercancel', handlePointerUp);
      container.innerHTML = '';
    },
    setActiveDrillNode(nodeId) {
      const prev = activeDrillNodeId;
      activeDrillNodeId = nodeId && model.nodeById.has(nodeId) ? nodeId : null;
      if (activeDrillNodeId) {
        updateSelectedElement({ type: 'node', id: activeDrillNodeId });
      }
      renderGraph();
      renderDetail();
      if (activeDrillNodeId && activeDrillNodeId !== prev) {
        const pos = positions.get(activeDrillNodeId);
        if (pos) panViewBoxTo(pos, 900);
      }
    },
    setInteractionMode(mode = 'inspect', nodeId = null) {
      const prevActive = activeDrillNodeId;
      interactionMode = mode;
      syncInteractionChrome();
      if (nodeId && model.nodeById.has(nodeId)) {
        updateSelectedElement({ type: 'node', id: nodeId });
        if (DRILL_CONTEXT_MODES.has(mode) || mode === 'post-drill') {
          activeDrillNodeId = nodeId;
        }
      }
      if (!DRILL_CONTEXT_MODES.has(mode) && mode !== 'post-drill') {
        if (mode === 'inspect') activeDrillNodeId = null;
      }
      hoveredElement = null;
      renderGraph();
      renderDetail();
      if (activeDrillNodeId && activeDrillNodeId !== prevActive) {
        const pos = positions.get(activeDrillNodeId);
        if (pos) panViewBoxTo(pos, 900);
      } else if (!activeDrillNodeId && prevActive) {
        panViewBoxTo({ x: VIEWBOX.centerX, y: VIEWBOX.centerY }, 900);
      }
    },
    updateNodeState(nodeId, newState) {
      const node = model.nodeById.get(nodeId);
      if (!node) return;
      node.state = newState;
      if (newState === 'solidified') {
        activeDrillNodeId = activeDrillNodeId === nodeId ? null : activeDrillNodeId;
      }
      queueFlash(nodeId, newState === 'solidified' ? 'solid' : 'primed', prefersReducedMotion ? 200 : 820);
      renderGraph();
      renderDetail();
    },
    clearActiveDrillNode() {
      activeDrillNodeId = null;
      interactionMode = 'inspect';
      syncInteractionChrome();
      hoveredElement = null;
      renderGraph();
      renderDetail();
    },
    syncFromKnowledgeMap(nextRawData, activeNodeId = null) {
      const nextTransformed = transformKnowledgeMapToGraph(nextRawData);
      model = buildModel(nextTransformed);
      lookup = createLookup(model);
      positions = calculateLayout(model);

      if (!model.nodeById.has(selectedElement.id) && !model.edgeById.has(selectedElement.id)) {
        selectedElement = { type: 'node', id: model.coreId };
      }
      if (activeNodeId && model.nodeById.has(activeNodeId)) {
        activeDrillNodeId = activeNodeId;
      } else if (activeDrillNodeId && !model.nodeById.has(activeDrillNodeId)) {
        activeDrillNodeId = null;
      }
      hoveredElement = null;
      renderGraph();
      renderDetail();
    },
    resize() {
      renderGraph();
    },
    showBlockedMessage(headline, body) {
      interactionMode = 'inspect';
      activeDrillNodeId = null;
      syncInteractionChrome();
      hoveredElement = null;
      renderGraph();
      detailEl.innerHTML = `
        <div class="graph-detail-kicker">Not yet</div>
        <h3 class="graph-detail-title">${escHtml(headline)}</h3>
        <p class="graph-detail-copy">${escHtml(body)}</p>
      `;
    },
    getNextNodeSuggestion(nodeId = null) {
      return findNextNodeSuggestion(nodeId);
    },
    getSelectedElement() {
      return selectedElement?.id ? { ...selectedElement } : null;
    },
    getInteractionMode() {
      return interactionMode;
    },
    getActiveDrillNode() {
      return activeDrillNodeId || null;
    },
    selectElement(nextSelected = null) {
      const target = nextSelected?.id ? { type: nextSelected.type === 'edge' ? 'edge' : 'node', id: nextSelected.id } : { type: 'node', id: model.coreId };
      interactionMode = 'inspect';
      activeDrillNodeId = null;
      syncInteractionChrome();
      updateSelectedElement(target);
      hoveredElement = null;
      renderGraph();
      renderDetail();
    },
    selectNode(nodeId) {
      if (!nodeId || !model.nodeById.has(nodeId)) return;
      this.selectElement({ type: 'node', id: nodeId });
    },
    flashSolidification(nodeId) {
      triggerPanelReward('solid');
      if (!nodeId || prefersReducedMotion) return;
      queueFlash(nodeId, 'solid', 860);
      renderGraph();
    },
    flashPrimed(nodeId) {
      triggerPanelReward('primed');
      if (!nodeId || prefersReducedMotion) return;
      queueFlash(nodeId, 'primed', 620);
      renderGraph();
    },
  };
}
