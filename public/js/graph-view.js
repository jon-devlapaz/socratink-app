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

function generateTeaser(text) {
  if (!text) return '???';
  return text.split(/\s+/).map((word) => {
    if (word.length <= 1) return word;
    return word.charAt(0) + '•'.repeat(word.length - 1);
  }).join(' ');
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
  if (status === 'solid') return 'Solidified';
  if (status === 'deep') return 'Partial mechanism';
  if (status === 'shallow') return 'Surface recall';
  if (status === 'misconception') return 'Misconception';
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

  if (data?.drillStatus === 'solid') {
    pills.push(`<span class="graph-detail-pill success">${escHtml(statusLabel)}</span>`);
  } else if (data?.state === 'drilled' || data?.drillStatus || data?.gapType) {
    pills.push('<span class="graph-detail-pill warning">Needs revisit</span>');
    if (gapLabel) {
      pills.push(`<span class="graph-detail-pill">${escHtml(gapLabel)}</span>`);
    } else if (statusLabel) {
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

function getInspectPrompt(data) {
  if (!data) return 'Start here and rebuild the mechanism from memory.';

  if (data.type === 'core') {
    return 'What governing idea explains how this whole system behaves? Start here, then prove it from memory.';
  }

  if (data.type === 'backbone') {
    return data.available
      ? 'What principle governs this branch, and why does the rest of this territory depend on it?'
      : 'Solidify the core thesis first to reveal this backbone branch.';
  }

  if (data.type === 'cluster') {
    return data.available
      ? 'This branch is open. The drill happens inside its rooms, not in the container itself.'
      : 'Clear the governing dependencies to reveal this branch.';
  }

  if (data.type === 'subnode') {
    return data.available
      ? 'This room is available. Can you reconstruct the mechanism from memory before entering the drill?'
      : 'Unlock this branch before drilling this room.';
  }

  return 'Choose a reachable room and rebuild it from memory.';
}

function deriveNodeState(status, gapType = null) {
  if (status === 'solid') return 'solidified';
  if (status || gapType) return 'drilled';
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
  if (subnodes.every((subnode) => subnode?.drill_status === 'solid')) return 'solidified';
  if (subnodes.some((subnode) => subnode?.drill_status || subnode?.gap_type)) return 'drilled';
  return 'locked';
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
  const coreSolid = source?.metadata?.drill_status === 'solid';
  const solidBackboneIds = new Set(
    backboneItems
      .filter((item) => item?.drill_status === 'solid' && item?.id)
      .map((item) => item.id)
  );
  const clusterToBackbones = new Map();
  const solidClusterIds = new Set(
    clusters
      .filter((cluster) => deriveClusterState(cluster) === 'solidified' && cluster?.id)
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
      gapType: source?.metadata?.gap_type || null,
      gapDescription: source?.metadata?.gap_description || null,
      weight: 1,
    },
    classes: 'node-core-thesis',
  });

  backboneItems.forEach((item, index) => {
    const backboneId = item.id || `backbone-${index + 1}`;
    const backboneState = deriveBackboneState(item);
    const backboneAvailable = coreSolid ? 1 : 0;
    const backboneLabel = shortenLabel(item.principle, 32);

    nodes.push({
      data: {
        id: backboneId,
        type: 'backbone',
        state: backboneState,
        available: backboneAvailable,
        label: backboneLabel,
        teaserLabel: generateTeaser(backboneLabel),
        fullLabel: item.principle || `Backbone Principle ${index + 1}`,
        detail: item.principle || '',
        dependentClusters: item.dependent_clusters || [],
        drillStatus: item.drill_status || null,
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
      ? ownerBackbones.some((backboneId) => solidBackboneIds.has(backboneId))
      : coreSolid;
    const prerequisites = incomingPrereqs.get(clusterId) || [];
    const prereqGateOpen = prerequisites.every((sourceId) => solidClusterIds.has(sourceId));
    const clusterAvailable = backboneGateOpen && prereqGateOpen;
    const clusterLabel = shortenLabel(cluster.label, 28);

    nodes.push({
      data: {
        id: clusterId,
        type: 'cluster',
        state: deriveClusterState(cluster),
        available: clusterAvailable ? 1 : 0,
        label: clusterLabel,
        teaserLabel: generateTeaser(clusterLabel),
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
          teaserLabel: generateTeaser(subnodeLabel),
          fullLabel: subnode.label || `Drill Node ${subIndex + 1}`,
          detail: subnode.mechanism || '',
          parentCluster: clusterId,
          orbitLevel: 2,
          drillStatus: subnode.drill_status,
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

function detailMarkupForNode(node, mode = 'inspect') {
  const data = node.data();
  const isDrillActive = mode === 'drill-active';
  const isPostDrill = mode === 'post-drill';
  const outcomeMeta = buildOutcomeMeta(data, { includeGapDescription: !isPostDrill });

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
      <h3 class="graph-detail-title">${escHtml(data.fullLabel)}</h3>
      <p class="graph-detail-copy">Explain this from memory. The map stays in the background until the drill resolves.</p>
      <div class="graph-detail-meta" style="flex-wrap:wrap; margin-bottom: 8px;">
        ${outcomeMeta.pills}
      </div>
    `;
  }

  if (isPostDrill) {
    const isSolid = data.drillStatus === 'solid';
    const kicker = data.type === 'core'
      ? 'Core Thesis Result'
      : data.type === 'backbone'
      ? 'Backbone Result'
        : data.type === 'cluster'
          ? 'Cluster Result'
          : 'Drill Result';
    return `
      <div class="graph-detail-kicker">${escHtml(kicker)}</div>
      <h3 class="graph-detail-title">${escHtml(data.fullLabel)}</h3>
      <p class="graph-detail-copy">${isSolid ? 'Solidified. You rebuilt this from scratch.' : 'Attempt logged. This room is still unresolved.'}</p>
      <div class="graph-detail-meta" style="flex-wrap:wrap; margin-bottom: 8px;">
        ${isSolid
          ? '<span class="graph-detail-pill success">Solidified</span>'
          : outcomeMeta.pills}
      </div>
      ${data.gapDescription ? `<p class="graph-detail-copy">${escHtml(data.gapDescription)}</p>` : ''}
      <button class="btn-start-drill trigger-continue" style="width:100%; margin-top: 16px;">Continue</button>
    `;
  }

  if (data.type === 'core') {
    return `
      <div class="graph-detail-kicker">Core Thesis</div>
      <h3 class="graph-detail-title">${escHtml(data.fullLabel)}</h3>
      <p class="graph-detail-copy">${escHtml(getInspectPrompt(data))}</p>
      <div class="graph-detail-meta" style="flex-wrap:wrap; margin-bottom: 8px;">
        ${outcomeMeta.pills}
        ${outcomeMeta.descriptionPills}
      </div>
      <button class="btn-start-drill trigger-drill" style="width:100%; margin-top: 16px;">✦ START WITH CORE THESIS</button>
    `;
  }

  if (data.type === 'backbone') {
    return `
      <div class="graph-detail-kicker">Backbone Principle</div>
      <h3 class="graph-detail-title">${escHtml(data.fullLabel)}</h3>
      <p class="graph-detail-copy">${escHtml(getInspectPrompt(data))}</p>
      <div class="graph-detail-meta" style="flex-wrap:wrap; margin-bottom: 8px;">
        ${outcomeMeta.pills}
        ${outcomeMeta.descriptionPills}
      </div>
      ${data.available ? `<button class="btn-start-drill trigger-drill" style="width:100%; margin-top: 16px;">✦ START DRILL</button>` : ''}
    `;
  }

  const isLocked = data.state === 'locked';
  const isDrilled = data.state === 'drilled';
  const isAvailable = Boolean(data.available);

  if (data.type === 'cluster') {
    return `
      <div class="graph-detail-kicker">Cluster</div>
      <h3 class="graph-detail-title">${escHtml(data.fullLabel)}</h3>
      <p class="graph-detail-copy">${escHtml(getInspectPrompt(data))}</p>
      <div class="graph-detail-meta" style="flex-wrap:wrap; margin-bottom: 8px;">
        <span class="graph-detail-pill">${escHtml(`${data.subnodeCount || 0} drill nodes`)}</span>
        ${isDrilled ? '<span class="graph-detail-pill warning">In progress</span>' : ''}
      </div>
    `;
  }

  return `
    <div class="graph-detail-kicker">Drill Node</div>
    <h3 class="graph-detail-title">${escHtml(data.fullLabel)}</h3>
    <p class="graph-detail-copy">${escHtml(getInspectPrompt(data))}</p>
    <div class="graph-detail-meta" style="flex-wrap:wrap; margin-bottom: 8px;">
      ${outcomeMeta.pills}
      ${outcomeMeta.descriptionPills}
    </div>
    ${isAvailable ? `<button class="btn-start-drill trigger-drill" style="width:100%; margin-top: 16px;">✦ START DRILL</button>` : ''}
  `;
}

function detailMarkupForEdge(edge, cy) {
  const data = edge.data();
  const source = cy.getElementById(data.source);
  const target = cy.getElementById(data.target);

  return `
    <div class="graph-detail-kicker">Connection</div>
    <h3 class="graph-detail-title">${escHtml(source.data('fullLabel') || source.data('label'))}</h3>
    <p class="graph-detail-copy">${escHtml(data.description || 'No explanatory text available for this relationship.')}</p>
    <div class="graph-detail-meta">
      <span class="graph-detail-pill">${escHtml(data.label || data.type)}</span>
      <span class="graph-detail-pill">${escHtml(target.data('label') || data.target)}</span>
    </div>
  `;
}

function setEmptyDetail(detailEl, source, mode = 'inspect') {
  if (mode === 'drill-active') {
    detailEl.innerHTML = `
      <div class="graph-detail-kicker">Active Drill</div>
      <h3 class="graph-detail-title">One node at a time</h3>
      <p class="graph-detail-copy">Use the chat to reconstruct the active node from memory. The graph will update after the drill outcome lands.</p>
    `;
    return;
  }

  const backboneTitle = escHtml('Core Thesis');
  const starterPrompt = escHtml('What governing idea explains how this whole system behaves? Start here, then prove it from memory.');
  detailEl.innerHTML = `
    <div class="graph-detail-kicker">Starting Room</div>
    <h3 class="graph-detail-title">${backboneTitle}</h3>
    <p class="graph-detail-copy">${starterPrompt}</p>
    <div class="graph-detail-meta">
      <span class="graph-detail-pill">Core thesis first</span>
    </div>
    <button class="btn-start-drill trigger-drill" style="width:100%; margin-top: 16px;">✦ START WITH CORE THESIS</button>
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

function installHoverFocus(cy, getInteractionMode) {
  cy.on('mouseover', 'node, edge', (event) => {
    if (getInteractionMode() === 'drill-active') return;
    applyGraphFocus(cy, event.target);
  });

  cy.on('mouseout', 'node, edge', () => {
    if (getInteractionMode() === 'drill-active') return;
    clearGraphFocus(cy);
  });
}

function installSelection(cy, detailEl, source, defaultNodeId, onNodeSelect, onContinue, getInteractionMode, setInteractionMode, setSelectedElement) {
  cy.on('tap', 'node', (event) => {
    setSelectedElement({ type: 'node', id: event.target.id() });
    if (getInteractionMode() === 'drill-active' || getInteractionMode() === 'post-drill') return;
    detailEl.innerHTML = detailMarkupForNode(event.target);
    const data = event.target.data();
    const drillBtn = detailEl.querySelector('.trigger-drill');
    if (drillBtn) {
      drillBtn.addEventListener('click', () => {
        onNodeSelect?.(data);
      });
    }
  });

  cy.on('tap', 'edge', (event) => {
    setSelectedElement({ type: 'edge', id: event.target.id() });
    if (getInteractionMode() === 'drill-active' || getInteractionMode() === 'post-drill') return;
    detailEl.innerHTML = detailMarkupForEdge(event.target, cy);
  });

  cy.on('tap', (event) => {
    if (event.target === cy) {
      setSelectedElement({ type: 'node', id: defaultNodeId });
      clearGraphFocus(cy);
      if (getInteractionMode() === 'drill-active' || getInteractionMode() === 'post-drill') return;
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

  if (typeof window === 'undefined' || typeof window.cytoscape !== 'function') {
    container.innerHTML = '<div class="graph-empty">Graph library failed to load. Study view is still available.</div>';
    setEmptyDetail(detailEl, rawData);
    return { destroy() {}, resize() {} };
  }

  const transformed = transformKnowledgeMapToGraph(rawData);
  if (!transformed.nodes.length) {
    container.innerHTML = '<div class="graph-empty">No extracted graph data is available yet.</div>';
    setEmptyDetail(detailEl, transformed.source);
    return { destroy() {}, resize() {} };
  }

  container.innerHTML = '';
  setEmptyDetail(detailEl, transformed.source);
  const emptyDrillBtn = detailEl.querySelector('.trigger-drill');
  if (emptyDrillBtn) emptyDrillBtn.addEventListener('click', () => onNodeSelect?.(null));

  const cy = window.cytoscape({
    container,
    elements: [...transformed.nodes, ...transformed.edges],
    layout: { name: 'preset' },
    wheelSensitivity: 0.18,
    minZoom: 0.42,
    maxZoom: 1.8,
    style: [
      {
        selector: 'node',
        style: {
          width: 'mapData(weight, 0, 1, 18, 68)',
          height: 'mapData(weight, 0, 1, 18, 68)',
          shape: 'ellipse',
          'background-color': '#ffffff',
          'border-width': 1.5,
          'border-color': '#d7d0f1',
          label: 'data(label)',
          'font-family': 'Manrope, sans-serif',
          'font-size': 11,
          'font-weight': 700,
          color: '#423c58',
          'text-wrap': 'wrap',
          'text-max-width': 160,
          'text-valign': 'bottom',
          'text-halign': 'center',
          'text-margin-y': 18,
          opacity: 1,
          'transition-property': 'opacity, background-color, border-color, text-opacity',
          'transition-duration': '180ms',
        },
      },
      {
        selector: '.node-core-thesis',
        style: {
          width: 72,
          height: 72,
          'font-size': 12,
          'text-max-width': 200,
          'text-margin-y': 22,
        },
      },
      {
        selector: '.node-backbone',
        style: {
          width: 42,
          height: 42,
          'font-size': 10,
          'text-max-width': 120,
          'text-margin-y': 18,
        },
      },
      {
        selector: '.node-cluster',
        style: {
          width: 34,
          height: 34,
          'font-size': 10,
          'text-max-width': 100,
          'text-margin-y': 16,
        },
      },
      {
        selector: '.node-subnode',
        style: {
          width: 16,
          height: 16,
          'font-size': 8,
          'text-max-width': 84,
          'text-margin-y': 12,
        },
      },
      {
        selector: 'node[state = "locked"][available = 0]',
        style: {
          'background-color': 'rgba(255,255,255,0.18)',
          'border-color': 'rgba(124,111,205,0.18)',
          'border-style': 'dashed',
          opacity: 0.35,
          label: 'data(teaserLabel)',
          color: 'rgba(66,60,88,0.5)',
          'text-opacity': 0.8,
          'overlay-opacity': 0,
          events: 'no',
        },
      },
      {
        selector: 'node[state = "locked"][available = 1]',
        style: {
          'background-color': 'rgba(255,255,255,0.85)',
          'border-color': 'rgba(124,111,205,0.42)',
          'border-style': 'solid',
          opacity: 0.9,
          label: 'data(label)',
          color: '#6d64a6',
          'text-opacity': 0.92,
          'overlay-opacity': 0.03,
          events: 'yes',
        },
      },
      {
        selector: 'node[state = "solidified"]',
        style: {
          'background-color': '#7c6fcd',
          'border-color': '#988be4',
          'border-style': 'solid',
          opacity: 1,
          label: 'data(label)',
          color: '#7c6fcd',
          'text-opacity': 1,
          'overlay-opacity': 0.06,
        },
      },
      {
        selector: 'node[state = "drilled"]',
        style: {
          'background-color': '#d9a14a',
          'border-color': '#e5be78',
          'border-style': 'solid',
          opacity: 0.95,
          label: 'data(label)',
          color: '#8f5f16',
          'text-opacity': 1,
          'overlay-opacity': 0.04,
        },
      },
      {
        selector: 'node[state = "active_drill"]',
        style: {
          'background-color': '#7c6fcd',
          'border-color': '#b3a7f2',
          'border-width': 3,
          opacity: 1,
          label: 'data(label)',
          color: '#7c6fcd',
          'text-opacity': 0.08,
          'overlay-color': '#7c6fcd',
          'overlay-opacity': 0.12,
          'overlay-padding': 18,
        },
      },
      {
        selector: 'edge',
        style: {
          width: 1.4,
          'curve-style': 'bezier',
          'line-color': 'rgba(124,111,205,0.10)',
          'target-arrow-shape': 'none',
          opacity: 0.85,
          'transition-property': 'opacity, line-color, width',
          'transition-duration': '180ms',
        },
      },
      {
        selector: 'edge[available = 0]',
        style: {
          opacity: 0.08,
        },
      },
      {
        selector: 'edge[available = 1]',
        style: {
          opacity: 0.78,
        },
      },
      {
        selector: '.edge-structural',
        style: {
          width: 1.5,
          'line-color': 'rgba(124,111,205,0.10)',
        },
      },
      {
        selector: '.edge-subnode-link',
        style: {
          width: 1.2,
          'line-color': 'rgba(124,111,205,0.08)',
        },
      },
      {
        selector: '.edge-lateral',
        style: {
          width: 1.6,
          'line-style': 'dashed',
          'curve-style': 'unbundled-bezier',
          'control-point-distances': [-20, 20],
          'control-point-weights': [0.25, 0.75],
          'target-arrow-shape': 'triangle',
          'arrow-scale': 0.7,
          'target-arrow-color': 'rgba(124,111,205,0.45)',
        },
      },
      {
        selector: '.edge-prerequisite',
        style: {
          'line-color': 'rgba(124,111,205,0.44)',
          'target-arrow-color': 'rgba(124,111,205,0.44)',
        },
      },
      {
        selector: '.edge-domain',
        style: {
          'line-color': 'rgba(114,160,154,0.42)',
          'target-arrow-color': 'rgba(114,160,154,0.42)',
        },
      },
      {
        selector: '.is-dimmed',
        style: {
          opacity: 0.1,
        },
      },
      {
        selector: '.is-drill-muted',
        style: {
          opacity: 0.05,
          'text-opacity': 0,
          events: 'no',
          'background-color': '#e2e2e2',
          'line-color': 'rgba(200, 200, 200, 0.1)',
          'target-arrow-color': 'rgba(200, 200, 200, 0.1)',
        },
      },
      {
        selector: '.is-drill-context',
        style: {
          opacity: 0.44,
          'text-opacity': 0.22,
        },
      },
      {
        selector: '.is-drill-prereq',
        style: {
          opacity: 0.52,
          'text-opacity': 0.34,
        },
      },
      {
        selector: '.is-focus-target',
        style: {
          'text-opacity': 1,
        },
      },
      {
        selector: 'node.is-selection-anchor',
        style: {
          'border-color': '#5b518f',
          'border-width': 3,
          'overlay-color': '#7c6fcd',
          'overlay-opacity': 0.08,
          'overlay-padding': 14,
          'text-opacity': 1,
          'z-index': 9998,
        },
      },
      {
        selector: 'edge.is-selection-anchor',
        style: {
          width: 2.6,
          'line-color': 'rgba(124,111,205,0.66)',
          'target-arrow-color': 'rgba(124,111,205,0.66)',
          opacity: 1,
          'z-index': 9998,
        },
      },
      {
        selector: '.is-active-drill',
        style: {
          'border-color': '#7c6fcd',
          'border-width': 4,
          'background-color': '#f3efff',
          opacity: 1,
          'z-index': 9999,
          'overlay-color': '#7c6fcd',
          'overlay-opacity': 0.12,
          'overlay-padding': 16,
          'text-opacity': 1,
        },
      },
      {
        selector: '.is-entering',
        style: {
          opacity: 0.001,
        },
      },
      {
        selector: ':selected',
        style: {
          'overlay-color': '#7c6fcd',
          'overlay-opacity': 0.06,
          'overlay-padding': 12,
        },
      },
    ],
  });

  const getCenter = () => ({
    x: container.clientWidth / 2 || 420,
    y: container.clientHeight / 2 || 300,
  });

  const ambientFloat = installAmbientFloat(cy);
  let destroyed = false;
  let entryTimeoutId = null;
  let updateTimeoutId = null;
  let interactionMode = 'inspect';
  let selectedElement = { type: 'node', id: transformed.coreId };
  const updateSelectedElement = (nextSelected) => {
    selectedElement = nextSelected;
    syncSelectedElement(cy, selectedElement);
  };

  const clearDrillContext = () => {
    cy.elements().removeClass('is-drill-muted');
    cy.elements().removeClass('is-drill-context');
    cy.elements().removeClass('is-drill-prereq');
    cy.elements().removeClass('is-active-drill');
  };

  const applyDrillContext = (nodeId) => {
    clearDrillContext();
    clearGraphFocus(cy);
    if (!nodeId) return;

    const activeNode = cy.getElementById(nodeId);
    if (!activeNode.length) return;

    cy.batch(() => {
      cy.elements().addClass('is-drill-muted');
      activeNode.removeClass('is-drill-muted').addClass('is-active-drill');

      const anchorNode = activeNode.data('type') === 'subnode' && activeNode.data('parentCluster')
        ? cy.getElementById(activeNode.data('parentCluster'))
        : activeNode;

      if (anchorNode.length && anchorNode.id() !== activeNode.id()) {
        anchorNode.removeClass('is-drill-muted').addClass('is-drill-context');
      }

      const structuralEdges = activeNode.connectedEdges('.edge-subnode-link');
      structuralEdges.removeClass('is-drill-muted').addClass('is-drill-context');

      const prerequisiteEdges = cy.edges('.edge-prerequisite').filter((edge) => (
        edge.data('source') === anchorNode.id() || edge.data('target') === anchorNode.id()
      ));
      prerequisiteEdges.removeClass('is-drill-muted').addClass('is-drill-prereq');
      prerequisiteEdges.connectedNodes().removeClass('is-drill-muted').addClass('is-drill-prereq');
    });
  };

  const renderCurrentDetail = () => {
    if (interactionMode === 'drill-active') {
      const activeId = selectedElement.type === 'node' && selectedElement.id ? selectedElement.id : transformed.coreId;
      const activeNode = cy.getElementById(activeId);
      if (activeNode.length) {
        detailEl.innerHTML = detailMarkupForNode(activeNode, 'drill-active');
      } else {
        setEmptyDetail(detailEl, transformed.source, 'drill-active');
      }
      return;
    }

    if (interactionMode === 'post-drill') {
      const activeId = selectedElement.type === 'node' && selectedElement.id ? selectedElement.id : transformed.coreId;
      const activeNode = cy.getElementById(activeId);
      if (activeNode.length) {
        detailEl.innerHTML = detailMarkupForNode(activeNode, 'post-drill');
        const continueBtn = detailEl.querySelector('.trigger-continue');
        if (continueBtn) continueBtn.addEventListener('click', () => onContinue?.());
      } else {
        setEmptyDetail(detailEl, transformed.source, 'inspect');
      }
      return;
    }

    if (selectedElement.type === 'node' && selectedElement.id) {
      const node = cy.getElementById(selectedElement.id);
      if (node.length) {
        detailEl.innerHTML = detailMarkupForNode(node, 'inspect');
        const data = node.data();
        const drillBtn = detailEl.querySelector('.trigger-drill');
        if (drillBtn) {
          drillBtn.addEventListener('click', () => onNodeSelect?.(data));
        }
        return;
      }
    }

    if (selectedElement.type === 'edge' && selectedElement.id) {
      const edge = cy.getElementById(selectedElement.id);
      if (edge.length) {
        detailEl.innerHTML = detailMarkupForEdge(edge, cy);
        return;
      }
    }

    setEmptyDetail(detailEl, transformed.source, 'inspect');
    const drillBtn = detailEl.querySelector('.trigger-drill');
    if (drillBtn) drillBtn.addEventListener('click', () => onNodeSelect?.(null));
  };

  const renderOrbit = (animate = false) => {
    if (destroyed) return;
    const center = getCenter();
    const rootNode = cy.getElementById(transformed.coreId);
    if (rootNode.length) rootNode.position(center);
    const positions = calculateSolarPositions(cy, center);

    if (animate) {
      applyEntryAnimation(cy, center);
      requestAnimationFrame(() => {
        if (destroyed) return;
        cy.nodes().forEach((node, index) => {
          const target = positions[node.id()] || center;
          node.animate(
            {
              position: target,
              style: { opacity: 1 },
            },
            {
              duration: 520 + index * 18,
              easing: 'ease-out-cubic',
            }
          );
        });
      });
      entryTimeoutId = window.setTimeout(() => {
        if (destroyed) return;
        cy.nodes().removeClass('is-entering');
        ambientFloat.captureBasePositions();
        cy.fit(cy.elements(), 50);
      }, 900);
      return;
    }

    cy.batch(() => {
      cy.nodes().positions((node) => positions[node.id()] || center);
    });
    ambientFloat.captureBasePositions();
    cy.fit(cy.elements(), 50);
  };

  installHoverFocus(cy, () => interactionMode);
  installSelection(
    cy,
    detailEl,
    transformed.source,
    transformed.coreId,
    onNodeSelect,
    onContinue,
    () => interactionMode,
    (nextMode) => {
      interactionMode = nextMode;
      const graphDetail = detailEl.closest('.graph-detail');
      if (graphDetail) {
        graphDetail.classList.toggle('is-drill-active', interactionMode === 'drill-active');
        graphDetail.classList.toggle('is-post-drill', interactionMode === 'post-drill');
      }
      if (interactionMode === 'drill-active') {
        applyDrillContext(selectedElement.id);
      } else {
        clearDrillContext();
      }
    },
    updateSelectedElement
  );
  installDragBehavior(cy);

  const root = cy.getElementById(transformed.coreId);
  if (root.length) {
    renderCurrentDetail();
  } else {
    setEmptyDetail(detailEl, transformed.source, 'inspect');
  }

  syncSelectedElement(cy, selectedElement);
  renderOrbit(true);
  clearGraphFocus(cy);

  return {
    destroy() {
      destroyed = true;
      if (entryTimeoutId) window.clearTimeout(entryTimeoutId);
      if (updateTimeoutId) window.clearTimeout(updateTimeoutId);
      ambientFloat.destroy();
      cy.destroy();
    },
    setActiveDrillNode(nodeId) {
      cy.nodes().removeClass('is-active-drill');
      if (!nodeId) return;
      const node = cy.getElementById(nodeId);
      if (node.length) {
        updateSelectedElement({ type: 'node', id: nodeId });
        node.addClass('is-active-drill');
      }
    },
    setInteractionMode(mode = 'inspect', nodeId = null) {
      interactionMode = mode === 'drill-active' ? 'drill-active' : mode === 'post-drill' ? 'post-drill' : 'inspect';
      const graphDetail = detailEl.closest('.graph-detail');
      if (graphDetail) {
        graphDetail.classList.toggle('is-drill-active', interactionMode === 'drill-active');
        graphDetail.classList.toggle('is-post-drill', interactionMode === 'post-drill');
      }
      if (nodeId) {
        updateSelectedElement({ type: 'node', id: nodeId });
      }
      if (interactionMode === 'drill-active') {
        applyDrillContext(selectedElement.id);
      } else {
        clearDrillContext();
      }
      renderCurrentDetail();
    },
    updateNodeState(nodeId, newState) {
      const node = cy.getElementById(nodeId);
      if (!node.length) return;

      node.data('state', newState);

      // Unlock text + visual state immediately.
      if (newState === 'solidified') {
        node.removeClass('is-active-drill');
      }

      // Brief physics "bloom" so the graph settles organically around the new node.
      const bloomLayout = cy.layout({
        name: 'cose',
        animate: true,
        animationDuration: 900,
        fit: false,
        padding: 40,
        randomize: false,
        componentSpacing: 80,
        nodeRepulsion: 9000,
        idealEdgeLength: (edge) => edge.hasClass('edge-subnode-link') ? 55 : 120,
        edgeElasticity: (edge) => edge.hasClass('edge-subnode-link') ? 0.18 : 0.08,
        gravity: 0.12,
        numIter: 400,
        initialTemp: 80,
        coolingFactor: 0.95,
        minTemp: 1.0,
      });

      bloomLayout.run();

      updateTimeoutId = window.setTimeout(() => {
        if (destroyed) return;
        ambientFloat.captureBasePositions();
        cy.fit(cy.elements(), 50);
      }, 1000);
    },
    clearActiveDrillNode() {
      cy.nodes().removeClass('is-active-drill');
      interactionMode = 'inspect';
      const graphDetail = detailEl.closest('.graph-detail');
      if (graphDetail) {
        graphDetail.classList.remove('is-drill-active');
        graphDetail.classList.remove('is-post-drill');
      }
      clearDrillContext();
      renderCurrentDetail();
    },
    syncFromKnowledgeMap(rawData, activeNodeId = null) {
      const next = transformKnowledgeMapToGraph(rawData);
      let changed = false;

      cy.batch(() => {
        next.nodes.forEach((nextNode) => {
          const node = cy.getElementById(nextNode.data.id);
          if (!node.length) return;

          if (node.data('state') !== nextNode.data.state) {
            changed = true;
          }

          Object.entries(nextNode.data).forEach(([key, value]) => {
            node.data(key, value);
          });
          node.classes(nextNode.classes);
          if (activeNodeId && nextNode.data.id === activeNodeId) {
            node.addClass('is-active-drill');
          }
        });
      });

      syncSelectedElement(cy, selectedElement);
      renderCurrentDetail();

      if (changed) {
        const bloomLayout = cy.layout({
          name: 'cose',
          animate: true,
          animationDuration: 700,
          fit: false,
          padding: 40,
          randomize: false,
          componentSpacing: 80,
          nodeRepulsion: 9000,
          idealEdgeLength: (edge) => edge.hasClass('edge-subnode-link') ? 55 : 120,
          edgeElasticity: (edge) => edge.hasClass('edge-subnode-link') ? 0.18 : 0.08,
          gravity: 0.12,
          numIter: 300,
          initialTemp: 60,
          coolingFactor: 0.95,
          minTemp: 1.0,
        });
        bloomLayout.run();
      }

      ambientFloat.captureBasePositions();
    },
    resize() {
      renderOrbit(false);
      cy.fit(cy.elements(), 50);
    },
  };
}
