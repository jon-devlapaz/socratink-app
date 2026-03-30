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

function getBackboneDetail(source) {
  const thesis = source?.metadata?.core_thesis?.trim();
  const backbonePrinciple = source?.backbone?.[0]?.principle?.trim();
  return backbonePrinciple || thesis || 'This node anchors the extracted concept map.';
}

function drillTone(subnode) {
  if (subnode?.gap_type) return 'gap';
  if (subnode?.drill_status) return 'drilled';
  return 'fresh';
}

export function transformKnowledgeMapToGraph(rawData) {
  const source = typeof rawData === 'string' ? JSON.parse(rawData) : rawData;
  const nodes = [];
  const edges = [];
  const clusters = Array.isArray(source?.clusters) ? source.clusters : [];
  const relationships = source?.relationships || {};
  const backboneId = 'core-thesis';
  const clusterMap = new Map();

  nodes.push({
    data: {
      id: backboneId,
      type: 'backbone',
      state: 'solidified',
      label: shortenLabel(getBackboneLabel(source), 40),
      fullLabel: source?.metadata?.source_title || 'Core Thesis',
      detail: getBackboneDetail(source),
      weight: 1,
    },
    classes: 'node-backbone',
  });

  clusters.forEach((cluster, clusterIndex) => {
    const clusterId = cluster.id || `cluster-${clusterIndex + 1}`;
    clusterMap.set(clusterId, cluster);

    nodes.push({
      data: {
        id: clusterId,
        type: 'cluster',
        state: 'locked',
        label: shortenLabel(cluster.label, 28),
        fullLabel: cluster.label || `Cluster ${clusterIndex + 1}`,
        detail: cluster.description || '',
        orbitLevel: 1,
        subnodeCount: Array.isArray(cluster.subnodes) ? cluster.subnodes.length : 0,
      },
      classes: 'node-cluster',
    });

    edges.push({
      data: {
        id: `struct-${backboneId}-${clusterId}`,
        source: backboneId,
        target: clusterId,
        type: 'structural',
        label: 'Backbone branch',
        description: `This cluster branches directly from the backbone thesis for this map.`,
      },
      classes: 'edge-structural',
    });

    (cluster.subnodes || []).forEach((subnode, subIndex) => {
      const subnodeId = subnode.id || `${clusterId}-sub-${subIndex + 1}`;
      nodes.push({
        data: {
          id: subnodeId,
          type: 'subnode',
          state: 'locked',
          label: shortenLabel(subnode.label, 24),
          fullLabel: subnode.label || `Drill Node ${subIndex + 1}`,
          detail: subnode.mechanism || '',
          parentCluster: clusterId,
          orbitLevel: 2,
          drillStatus: subnode.drill_status,
          gapType: subnode.gap_type,
          gapDescription: subnode.gap_description,
        },
        classes: `node-subnode tone-${drillTone(subnode)}`,
      });

      edges.push({
        data: {
          id: `struct-${clusterId}-${subnodeId}`,
          source: clusterId,
          target: subnodeId,
          type: 'structural',
          label: 'Drill branch',
          description: subnode.mechanism || 'This drill node belongs to the selected cluster.',
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
      },
      classes: 'edge-lateral edge-domain',
    });
  });

  return { source, nodes, edges, backboneId };
}

function detailMarkupForNode(node) {
  const data = node.data();
  if (data.type === 'backbone') {
    return `
      <div class="graph-detail-kicker">Backbone</div>
      <h3 class="graph-detail-title">${escHtml(data.fullLabel)}</h3>
      <p class="graph-detail-copy">${escHtml(data.detail)}</p>
    `;
  }

  const isLocked = data.state === 'locked';

  if (data.type === 'cluster') {
    return `
      <div class="graph-detail-kicker">Cluster</div>
      <h3 class="graph-detail-title">${escHtml(data.fullLabel)}</h3>
      <p class="graph-detail-copy">${isLocked ? 'This cluster is locked. Complete the drill to reveal the architectural summary.' : escHtml(data.detail || 'No cluster description available yet.')}</p>
      <div class="graph-detail-meta" style="flex-wrap:wrap; margin-bottom: 8px;">
        <span class="graph-detail-pill">${escHtml(`${data.subnodeCount || 0} drill nodes`)}</span>
      </div>
      ${isLocked ? `<button class="btn-start-drill trigger-drill" style="width:100%; margin-top: 16px;">✦ START DRILL</button>` : ''}
    `;
  }

  return `
    <div class="graph-detail-kicker">Drill Node</div>
    <h3 class="graph-detail-title">${escHtml(data.fullLabel)}</h3>
    <p class="graph-detail-copy">${isLocked ? 'The mechanism here is locked by the Fog of War. Drill to unlock.' : escHtml(data.detail || 'No mechanism extracted for this drill node yet.')}</p>
    <div class="graph-detail-meta" style="flex-wrap:wrap; margin-bottom: 8px;">
      ${data.drillStatus ? `<span class="graph-detail-pill">${escHtml(`status: ${data.drillStatus}`)}</span>` : ''}
      ${data.gapType ? `<span class="graph-detail-pill warning">${escHtml(`gap: ${data.gapType}`)}</span>` : ''}
    </div>
    ${isLocked ? `<button class="btn-start-drill trigger-drill" style="width:100%; margin-top: 16px;">✦ START DRILL</button>` : ''}
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

function setEmptyDetail(detailEl, source) {
  detailEl.innerHTML = `
    <div class="graph-detail-kicker">Graph View</div>
    <h3 class="graph-detail-title">Knowledge Architecture</h3>
    <p class="graph-detail-copy">${escHtml(getBackboneDetail(source))}</p>
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

function installHoverFocus(cy, detailEl) {
  cy.on('mouseover', 'node, edge', (event) => {
    applyGraphFocus(cy, event.target);
    detailEl.innerHTML = event.target.isNode()
      ? detailMarkupForNode(event.target)
      : detailMarkupForEdge(event.target, cy);
  });

  cy.on('mouseout', 'node, edge', () => {
    clearGraphFocus(cy);
  });
}

function installSelection(cy, detailEl, source, onNodeSelect) {
  cy.on('tap', 'node', (event) => {
    detailEl.innerHTML = detailMarkupForNode(event.target);
    const drillBtn = detailEl.querySelector('.trigger-drill');
    if (drillBtn) {
      drillBtn.addEventListener('click', () => {
        onNodeSelect?.(event.target.data());
      });
    }
  });

  cy.on('tap', 'edge', (event) => {
    detailEl.innerHTML = detailMarkupForEdge(event.target, cy);
  });

  cy.on('tap', (event) => {
    if (event.target === cy) {
      clearGraphFocus(cy);
      setEmptyDetail(detailEl, source);
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
  const clusterNodes = cy.nodes('.node-cluster');
  const subnodeNodes = cy.nodes('.node-subnode');
  const clusterCount = Math.max(clusterNodes.length, 1);
  const clusterRadius = Math.max(120, Math.min(220, 110 + clusterCount * 10));

  positions['core-thesis'] = { x: center.x, y: center.y };

  clusterNodes.forEach((clusterNode, clusterIndex) => {
    const clusterAngle = (-Math.PI / 2) + (Math.PI * 2 * clusterIndex) / clusterCount;
    const clusterX = center.x + Math.cos(clusterAngle) * clusterRadius;
    const clusterY = center.y + Math.sin(clusterAngle) * clusterRadius;

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
        const amplitudeX = node.hasClass('node-backbone') ? 2.6 : node.hasClass('node-cluster') ? 2.1 : 1.6;
        const amplitudeY = node.hasClass('node-backbone') ? 3.8 : node.hasClass('node-cluster') ? 3.0 : 2.2;
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

export function mountKnowledgeGraph({ container, detailEl, rawData, onNodeSelect }) {
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
        selector: '.node-backbone',
        style: {
          width: 72,
          height: 72,
          'font-size': 12,
          'text-max-width': 200,
          'text-margin-y': 22,
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
        selector: 'node[state = "locked"]',
        style: {
          'background-color': 'rgba(255,255,255,0.18)',
          'border-color': 'rgba(124,111,205,0.18)',
          'border-style': 'dashed',
          opacity: 0.28,
          label: '',
          color: 'rgba(66,60,88,0.08)',
          'text-opacity': 0,
          'overlay-opacity': 0,
          events: 'no',
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
        selector: '.tone-drilled',
        style: {
          'background-color': '#f1edff',
          'border-color': '#7c6fcd',
        },
      },
      {
        selector: '.tone-gap',
        style: {
          'background-color': '#fff0f3',
          'border-color': '#d9677d',
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
        selector: '.is-focus-target',
        style: {
          'text-opacity': 1,
        },
      },
      {
        selector: '.is-active-drill',
        style: {
          'border-color': '#7c6fcd',
          'border-width': 3,
          'background-color': '#f3efff',
          'overlay-color': '#7c6fcd',
          'overlay-opacity': 0.12,
          'overlay-padding': 16,
          'text-opacity': 0.08,
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

  const renderOrbit = (animate = false) => {
    const center = getCenter();
    const rootNode = cy.getElementById(transformed.backboneId);
    if (rootNode.length) rootNode.position(center);
    const positions = calculateSolarPositions(cy, center);

    if (animate) {
      applyEntryAnimation(cy, center);
      requestAnimationFrame(() => {
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
      window.setTimeout(() => {
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

  installHoverFocus(cy, detailEl);
  installSelection(cy, detailEl, transformed.source, onNodeSelect);
  installDragBehavior(cy);

  const root = cy.getElementById(transformed.backboneId);
  if (root.length) {
    detailEl.innerHTML = detailMarkupForNode(root);
  }

  renderOrbit(true);
  clearGraphFocus(cy);

  return {
    destroy() {
      ambientFloat.destroy();
      cy.destroy();
    },
    setActiveDrillNode(nodeId) {
      cy.nodes().removeClass('is-active-drill');
      if (!nodeId) return;
      const node = cy.getElementById(nodeId);
      if (node.length) node.addClass('is-active-drill');
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

      window.setTimeout(() => {
        ambientFloat.captureBasePositions();
        cy.fit(cy.elements(), 50);
      }, 1000);
    },
    clearActiveDrillNode() {
      cy.nodes().removeClass('is-active-drill');
    },
    resize() {
      renderOrbit(false);
      cy.fit(cy.elements(), 50);
    },
  };
}
