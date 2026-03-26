// Graph Engine and AI Extraction Component

const GEMINI_MODEL = 'gemini-2.5-flash';

// ── Tunable animation constants ─────────────────────────────────
// Adjust these to change the feel of the graph reveal.
const GRAPH_NODE_INTERVAL_MS   = 220;  // ms between each node appearing
const GRAPH_EDGE_DELAY_MS      = 300;  // ms pause after last node before edges wire up
const GRAPH_EDGE_INTERVAL_MS   = 80;   // ms between each edge appearing
const GRAPH_NODE_ENTRANCE_MS   = 280;  // ms for the pop-in scale animation
const GRAPH_EDGE_FADE_MS       = 250;  // ms for edge fade-in
const GRAPH_COMPLETION_HOLD_MS = 1100; // ms between phase-3 signal and handing back to app
// ────────────────────────────────────────────────────────────────

function easeOutBack(t) {
  const c1 = 1.70158, c3 = c1 + 1;
  return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
}

function getGeminiKey() { return localStorage.getItem('gemini_key') || ''; }

const GraphEngine = (() => {
  let canvas, ctx, animFrame, w, h;
  let nodes = [], edges = [];
  let primaryColor;

  function init() {
    primaryColor = getComputedStyle(document.body).getPropertyValue('--primary').trim() || '#7c6fcd';

    
    if(!document.getElementById('ai-debug-modal')) {
      const debugModal = document.createElement('div');
      debugModal.id = 'ai-debug-modal';
      debugModal.style.position = 'fixed';
      debugModal.style.bottom = '20px';
      debugModal.style.left = '20px';
      debugModal.style.width = '420px';
      debugModal.style.height = '280px';
      debugModal.style.background = 'rgba(0,0,0,0.85)';
      debugModal.style.color = '#00ffcc';
      debugModal.style.fontFamily = 'monospace';
      debugModal.style.fontSize = '12px';
      debugModal.style.padding = '12px';
      debugModal.style.borderRadius = '8px';
      debugModal.style.overflowY = 'auto';
      debugModal.style.zIndex = '300';
      debugModal.style.pointerEvents = 'all';
      debugModal.style.lineHeight = '1.4';
      document.body.appendChild(debugModal);
      
      const title = document.createElement('div');
      title.textContent = 'AI Stream Debugger';
      title.style.color = '#fff';
      title.style.marginBottom = '8px';
      title.style.fontWeight = 'bold';
      title.style.borderBottom = '1px solid #555';
      title.style.paddingBottom = '4px';
      debugModal.appendChild(title);
      
      const content = document.createElement('div');
      content.id = 'ai-debug-content';
      content.style.whiteSpace = 'pre-wrap';
      debugModal.appendChild(content);
    }
    document.getElementById('ai-debug-modal').style.display = 'block';
    const dbg = document.getElementById('ai-debug-content');
    if(dbg) dbg.textContent = 'Awaiting connection...\n';

    if(!canvas) {
      canvas = document.createElement('canvas');
      canvas.style.position = 'fixed';
      canvas.style.top = '0';
      canvas.style.left = '0';
      canvas.style.width = '100%';
      canvas.style.height = '100%';
      canvas.style.zIndex = '200';
      canvas.style.pointerEvents = 'none';
      canvas.style.background = 'transparent';
      canvas.style.opacity = '1';
      canvas.style.transition = 'opacity 0.6s ease';
      ctx = canvas.getContext('2d');
    }
    nodes = []; edges = [];
    document.body.appendChild(canvas);
    w = canvas.width = window.innerWidth;
    h = canvas.height = window.innerHeight;
    loop();
  }

  function addNode(label) {
    if (nodes.find(n => n.label === label)) return;
    
    let spawnX = w/2;
    let spawnY = h/2;
    if (nodes.length > 0) {
      spawnX = nodes.reduce((sum, n) => sum + n.x, 0) / nodes.length;
      spawnY = nodes.reduce((sum, n) => sum + n.y, 0) / nodes.length;
    }
    
    spawnX += (Math.random()-0.5) * 5;
    spawnY += (Math.random()-0.5) * 5;
    
    nodes.push({ id: label, label, x: spawnX, y: spawnY, vx: 0, vy: 0, born: performance.now() });
  }

  function addEdge(source, target, label) {
    let s = nodes.find(n => n.label === source);
    if(!s) { addNode(source); s = nodes.find(n => n.label === source); }
    let t = nodes.find(n => n.label === target);
    if(!t) { addNode(target); t = nodes.find(n => n.label === target); }
    
    if(s && t && !edges.find(e => e.source === s && e.target === t)) {
      edges.push({ source: s, target: t, label, born: performance.now() });
    }
  }

  function loop(now) {
    ctx.clearRect(0,0,w,h);

    for(let i=0; i<nodes.length; i++) {
      for(let j=i+1; j<nodes.length; j++) {
        let dx = nodes[i].x - nodes[j].x;
        let dy = nodes[i].y - nodes[j].y;
        let distSq = dx*dx + dy*dy;
        if(distSq < 1) distSq = 1;
        if(distSq < 50000) {
          let f = 1500 / distSq;
          nodes[i].vx += (dx/Math.sqrt(distSq)) * f;
          nodes[i].vy += (dy/Math.sqrt(distSq)) * f;
          nodes[j].vx -= (dx/Math.sqrt(distSq)) * f;
          nodes[j].vy -= (dy/Math.sqrt(distSq)) * f;
        }
      }
    }
    for(let e of edges) {
      let dx = e.target.x - e.source.x;
      let dy = e.target.y - e.source.y;
      let dist = Math.sqrt(dx*dx + dy*dy);
      if(dist < 1) dist = 1;
      let f = (dist - 120) * 0.05;
      e.source.vx += (dx/dist)*f;
      e.source.vy += (dy/dist)*f;
      e.target.vx -= (dx/dist)*f;
      e.target.vy -= (dy/dist)*f;
    }

    // Draw edges — fade in over 250ms from born
    ctx.lineWidth = 1.5;
    for(let e of edges) {
      const alpha = Math.min(0.38, ((now - e.born) / GRAPH_EDGE_FADE_MS) * 0.38);
      ctx.strokeStyle = `rgba(180,170,230,${alpha.toFixed(3)})`;
      ctx.beginPath();
      ctx.moveTo(e.source.x, e.source.y);
      ctx.lineTo(e.target.x, e.target.y);
      ctx.stroke();
    }

    // Draw nodes — pop in with easeOutBack scale over 280ms
    ctx.font = '600 12px system-ui, sans-serif';
    ctx.textAlign = 'center';
    for(let n of nodes) {
      n.vx += (w/2 - n.x) * 0.005;
      n.vy += (h/2 - n.y) * 0.005;
      n.vx *= 0.85; n.vy *= 0.85;
      n.x += n.vx; n.y += n.vy;

      const t = Math.max(0, Math.min(1, (now - n.born) / GRAPH_NODE_ENTRANCE_MS));
      if(t < 0.02) continue; // skip nodes not yet born — prevents ghost labels
      const scale = easeOutBack(t);

      ctx.beginPath();
      ctx.arc(n.x, n.y, 7 * scale, 0, Math.PI * 2);
      ctx.fillStyle = primaryColor;
      ctx.fill();

      ctx.globalAlpha = Math.min(1, t * 1.5); // label fades in slightly faster than dot
      ctx.fillStyle = 'rgba(255,255,255,0.9)';
      ctx.fillText(n.label, n.x, n.y - 13);
      ctx.globalAlpha = 1;
    }
    animFrame = requestAnimationFrame(loop);
  }

  function stop() {
    cancelAnimationFrame(animFrame);
    const dbgModal = document.getElementById('ai-debug-modal');
    if(dbgModal) dbgModal.style.display = 'none';

    if(canvas) {
      canvas.style.opacity = '0';
      setTimeout(() => {
        if(canvas && canvas.parentNode) canvas.parentNode.removeChild(canvas);
        canvas = null;
      }, 600);
    }
  }

  return { init, addNode, addEdge, stop, getGraph: () => ({ nodes, edges }) };
})();

async function performAIExtraction(text, onSuccess, onError, onPhaseChange) {
  const key = getGeminiKey();
  if(!key) {
    onError('Extraction paused: Please configure your Gemini API Key in the Settings menu.');
    return;
  }

  GraphEngine.init();
  const dbg = document.getElementById('ai-debug-content');

  function log(msg) {
    console.log('[AIExtract]', msg);
    if(dbg) {
      dbg.textContent += msg + '\n';
      dbg.parentElement.scrollTop = dbg.parentElement.scrollHeight;
    }
  }

  const url = `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent?key=${key}`;
  const prompt = `You are a cognitive extractor analyzing text. Output EXACTLY ONE item per line using ONLY these formats:
NODE: <Concept Name>
EDGE: <Source Concept> -> <Target Concept> | <Relationship>

Do not write markdown, asterisks, or bullet points. Just strict lines starting exactly with NODE: or EDGE:.

Text to analyze:
${text.slice(0, 10000)}`;

  log(`Model: ${GEMINI_MODEL}`);
  log(`Text length: ${text.length} chars (sending first ${Math.min(text.length, 10000)})`);
  log('Sending request...');

  let cancelled = false;

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] })
    });

    log(`Response status: ${response.status} ${response.statusText}`);

    if(!response.ok) {
      let errBody = '(could not read body)';
      try { errBody = await response.text(); } catch(_) {}
      log(`Error body: ${errBody.slice(0, 300)}`);
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    const fullText = data.candidates?.[0]?.content?.parts?.[0]?.text || '';

    log(`Received ${fullText.length} chars`);

    // Two-pass: all nodes queued first, then edges (edges only ref known nodes)
    const nodeQueue = [];
    const edgeQueue = [];
    const knownNodes = new Set();

    for(let p of fullText.split('\n')) {
      p = p.trim().replace(/\*\*/g, '');
      if(p.startsWith('NODE:')) {
        const label = p.substring(5).trim();
        if(label) { nodeQueue.push(label); knownNodes.add(label); }
      } else if(p.startsWith('EDGE:')) {
        const split1 = p.substring(5).split('->');
        if(split1.length === 2) {
          const source = split1[0].trim();
          const split2 = split1[1].split('|');
          if(split2.length === 2) {
            const target = split2[0].trim();
            const edgeLabel = split2[1].trim();
            if(knownNodes.has(source) && knownNodes.has(target)) {
              edgeQueue.push({ source, target, label: edgeLabel });
            }
          }
        }
      }
    }

    log(`Queued: ${nodeQueue.length} nodes, ${edgeQueue.length} edges`);

    // Timing: compress interval for large graphs so reveal stays engaging
    const NODE_INTERVAL = nodeQueue.length > 20
      ? Math.max(120, GRAPH_NODE_INTERVAL_MS - (nodeQueue.length - 20) * 5)
      : GRAPH_NODE_INTERVAL_MS;
    const EDGE_INTERVAL = GRAPH_EDGE_INTERVAL_MS;

    let delay = 0;

    // Stagger nodes — each one gets its own moment
    nodeQueue.forEach((label, i) => {
      setTimeout(() => {
        if(cancelled) return;
        GraphEngine.addNode(label);
        log(`NODE(${i + 1}): ${label}`);
        if(i === 0 && onPhaseChange) onPhaseChange(2);
      }, delay);
      delay += NODE_INTERVAL;
    });

    // Edges wire up after last node lands
    delay += GRAPH_EDGE_DELAY_MS;
    edgeQueue.forEach((edge, i) => {
      setTimeout(() => {
        if(cancelled) return;
        GraphEngine.addEdge(edge.source, edge.target, edge.label);
        log(`EDGE(${i + 1}): ${edge.source} -> ${edge.target} | ${edge.label}`);
      }, delay);
      delay += EDGE_INTERVAL;
    });

    // Completion: phase 3 signal, then 1100ms breath before handing back
    setTimeout(() => {
      if(cancelled) return;
      log(`\nComplete. Nodes: ${nodeQueue.length} | Edges: ${edgeQueue.length}`);
      if(onPhaseChange) onPhaseChange(3);
      setTimeout(() => {
        if(cancelled) return;
        GraphEngine.stop();
        onSuccess(GraphEngine.getGraph());
      }, GRAPH_COMPLETION_HOLD_MS);
    }, delay + 400);

  } catch(err) {
    cancelled = true;
    log(`\nFATAL: ${err.message}`);
    GraphEngine.stop();
    onError(err.message);
  }
}

// ── Dev test harness — bypasses Gemini API entirely ─────────────
// Call window.testGraph() from the browser console to preview the
// full extraction animation with canned data. No API key required.
const MOCK_GRAPH_DATA = `
NODE: Photosynthesis
NODE: Chlorophyll
NODE: Light Reactions
NODE: Calvin Cycle
NODE: ATP
NODE: NADPH
NODE: Carbon Dioxide
NODE: Glucose
NODE: Thylakoid Membrane
NODE: Stroma
NODE: Electron Transport Chain
NODE: Water Splitting
EDGE: Photosynthesis -> Chlorophyll | requires pigment
EDGE: Chlorophyll -> Light Reactions | absorbs photons for
EDGE: Light Reactions -> ATP | produces
EDGE: Light Reactions -> NADPH | produces
EDGE: Light Reactions -> Thylakoid Membrane | occurs in
EDGE: Light Reactions -> Water Splitting | drives
EDGE: Calvin Cycle -> Carbon Dioxide | fixes
EDGE: Calvin Cycle -> ATP | consumes
EDGE: Calvin Cycle -> NADPH | consumes
EDGE: Calvin Cycle -> Glucose | synthesises
EDGE: Calvin Cycle -> Stroma | occurs in
EDGE: Light Reactions -> Electron Transport Chain | drives
`.trim();

function runGraphReveal(rawText, onSuccess, onError, onPhaseChange) {
  const nodeQueue = [];
  const edgeQueue = [];
  const knownNodes = new Set();

  for(let p of rawText.split('\n')) {
    p = p.trim();
    if(p.startsWith('NODE:')) {
      const label = p.substring(5).trim();
      if(label) { nodeQueue.push(label); knownNodes.add(label); }
    } else if(p.startsWith('EDGE:')) {
      const split1 = p.substring(5).split('->');
      if(split1.length === 2) {
        const source = split1[0].trim();
        const split2 = split1[1].split('|');
        if(split2.length === 2) {
          const target = split2[0].trim();
          const edgeLabel = split2[1].trim();
          if(knownNodes.has(source) && knownNodes.has(target)) {
            edgeQueue.push({ source, target, label: edgeLabel });
          }
        }
      }
    }
  }

  const NODE_INTERVAL = nodeQueue.length > 20
    ? Math.max(120, GRAPH_NODE_INTERVAL_MS - (nodeQueue.length - 20) * 5)
    : GRAPH_NODE_INTERVAL_MS;

  let delay = 0;
  let cancelled = false;

  nodeQueue.forEach((label, i) => {
    setTimeout(() => {
      if(cancelled) return;
      GraphEngine.addNode(label);
      if(i === 0 && onPhaseChange) onPhaseChange(2);
    }, delay);
    delay += NODE_INTERVAL;
  });

  delay += GRAPH_EDGE_DELAY_MS;
  edgeQueue.forEach(edge => {
    setTimeout(() => {
      if(cancelled) return;
      GraphEngine.addEdge(edge.source, edge.target, edge.label);
    }, delay);
    delay += GRAPH_EDGE_INTERVAL_MS;
  });

  setTimeout(() => {
    if(cancelled) return;
    if(onPhaseChange) onPhaseChange(3);
    setTimeout(() => {
      if(cancelled) return;
      GraphEngine.stop();
      onSuccess(GraphEngine.getGraph());
    }, GRAPH_COMPLETION_HOLD_MS);
  }, delay + 400);

  return () => { cancelled = true; };
}

window.testGraph = function(conceptName) {
  const name = conceptName || 'Photosynthesis';
  console.log('[testGraph] Starting preview with mock data — concept:', name);

  // Build overlay the same way app.js does
  const existing = document.getElementById('extract-overlay');
  if(existing) existing.parentNode.removeChild(existing);

  const overlay = document.createElement('div');
  overlay.id = 'extract-overlay';
  overlay.innerHTML = `
    <div class="extract-body">
      <div class="extract-spinner"></div>
      <p class="extract-label">Extracting concepts</p>
      <p class="extract-name">${name}</p>
    </div>
  `;
  document.body.appendChild(overlay);
  requestAnimationFrame(() => overlay.classList.add('visible'));

  function removeOverlay() {
    overlay.classList.remove('visible');
    setTimeout(() => { if(overlay.parentNode) overlay.parentNode.removeChild(overlay); }, 400);
  }

  function onPhaseChange(phase) {
    overlay.dataset.phase = String(phase);
    if(phase === 2) overlay.querySelector('.extract-label').textContent = name;
    if(phase === 3) {
      overlay.querySelector('.extract-label').textContent = 'Mapped';
      const ring = document.createElement('div');
      ring.className = 'extract-complete-ring';
      overlay.appendChild(ring);
    }
  }

  GraphEngine.init();
  // Simulate a brief "API wait" before nodes appear
  setTimeout(() => {
    runGraphReveal(MOCK_GRAPH_DATA, (graphData) => {
      removeOverlay();
      console.log('[testGraph] Complete:', graphData.nodes.length, 'nodes,', graphData.edges.length, 'edges');
    }, (err) => {
      removeOverlay();
      console.error('[testGraph] Error:', err);
    }, onPhaseChange);
  }, 800);
};
// ────────────────────────────────────────────────────────────────

function startSettings() {
  const triggerArea = document.getElementById('add-trigger-area');
  triggerArea.style.overflowY = 'auto';

  const key = getGeminiKey();
  const masked = key ? key.slice(0, 6) + '••••••••••••••••' : '';

  const eyeOpen = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`;
  const eyeOff  = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/></svg>`;

  triggerArea.innerHTML = `
    <div class="settings-panel">
      <div class="settings-header">
        <div class="settings-header-text">
          <h3>Settings</h3>
          <p class="settings-subtext">Configure your neurocognitive pipeline and integration hooks.</p>
        </div>
        <button class="settings-close-btn" onclick="App.closeDrawer(); App.renderAddTrigger();" aria-label="Close settings">×</button>
      </div>

      <div class="settings-box">
        <div class="settings-section-header">
          <h4>Gemini Connection</h4>
          <span class="settings-dot" id="settings-dot"></span>
        </div>
        <div class="settings-input-wrap">
          <input type="password" id="settings-key-input" class="settings-input" placeholder="Paste Gemini API Key" value="${masked}" autocomplete="off" spellcheck="false">
          <button class="settings-eye" id="settings-eye" type="button" aria-label="Toggle key visibility">${eyeOpen}</button>
        </div>
        <a class="settings-helper" href="https://aistudio.google.com/app/apikey" target="_blank" rel="noopener noreferrer">Get your free Gemini API key →</a>
        <div class="settings-actions">
          <button id="settings-key-save" class="settings-save">Save Key</button>
          <button id="settings-key-test" class="settings-test">Test Connection</button>
        </div>
        <div id="settings-api-status" class="settings-status"></div>
      </div>
    </div>
  `;

  App.openDrawer();

  const inp       = triggerArea.querySelector('#settings-key-input');
  const eyeBtn    = triggerArea.querySelector('#settings-eye');
  const dot       = triggerArea.querySelector('#settings-dot');
  const saveBtn   = triggerArea.querySelector('#settings-key-save');
  const testBtn   = triggerArea.querySelector('#settings-key-test');
  const statusBox = triggerArea.querySelector('#settings-api-status');

  eyeBtn.addEventListener('click', () => {
    const isRevealed = inp.type === 'text';
    inp.type = isRevealed ? 'password' : 'text';
    eyeBtn.innerHTML = isRevealed ? eyeOpen : eyeOff;
    eyeBtn.classList.toggle('revealed', !isRevealed);
  });

  saveBtn.addEventListener('click', () => {
    const val = inp.value.trim();
    if (val && !val.includes('••••')) {
      localStorage.setItem('gemini_key', val);
      dot.classList.remove('connected', 'error');
      statusBox.textContent = 'Key saved.';
      statusBox.style.color = 'var(--text-sub)';
    }
  });

  testBtn.addEventListener('click', async () => {
    const currentKey = getGeminiKey();
    if (!currentKey) {
      dot.classList.remove('connected');
      dot.classList.add('error');
      statusBox.textContent = 'No key saved.';
      statusBox.style.color = 'var(--danger)';
      return;
    }

    testBtn.disabled = true;
    testBtn.innerHTML = `<span class="settings-spinner"></span>Testing…`;
    statusBox.textContent = '';

    try {
      const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${currentKey}`;
      const payload = { contents: [{ parts: [{ text: 'Reply OK' }] }] };
      const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await res.json();
      dot.classList.remove('error');
      dot.classList.add('connected');
      statusBox.textContent = 'Connected successfully.';
      statusBox.style.color = 'var(--success)';
    } catch(err) {
      dot.classList.remove('connected');
      dot.classList.add('error');
      statusBox.textContent = err.message;
      statusBox.style.color = 'var(--danger)';
    } finally {
      testBtn.disabled = false;
      testBtn.textContent = 'Test Connection';
    }
  });
}
