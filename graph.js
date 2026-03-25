// Graph Engine and AI Extraction Component

function getGeminiKey() { return localStorage.getItem('gemini_key') || ''; }

const GraphEngine = (() => {
  let canvas, ctx, animFrame, w, h;
  let nodes = [], edges = [];
  let bgColor, primaryColor, textColor;
  
  function init() {
    bgColor = getComputedStyle(document.body).getPropertyValue('--surface-card').trim() || '#ffffff';
    primaryColor = getComputedStyle(document.body).getPropertyValue('--primary').trim() || '#7c6fcd';
    textColor = getComputedStyle(document.body).getPropertyValue('--text').trim() || '#2d2b3d';

    if(!canvas) {
      canvas = document.createElement('canvas');
      canvas.style.position = 'absolute';
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
    
    nodes.push({ id: label, label, x: spawnX, y: spawnY, vx: 0, vy: 0 });
  }

  function addEdge(source, target, label) {
    let s = nodes.find(n => n.label === source);
    if(!s) { addNode(source); s = nodes.find(n => n.label === source); }
    let t = nodes.find(n => n.label === target);
    if(!t) { addNode(target); t = nodes.find(n => n.label === target); }
    
    if(s && t && !edges.find(e => e.source === s && e.target === t)) {
      edges.push({ source: s, target: t, label });
    }
  }

  function loop() {
    ctx.clearRect(0,0,w,h);
    ctx.fillStyle = bgColor;
    ctx.fillRect(0,0,w,h);
    
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
    
    ctx.strokeStyle = '#c4c2d4';
    ctx.lineWidth = 1.5;
    for(let e of edges) {
      ctx.beginPath();
      ctx.moveTo(e.source.x, e.source.y);
      ctx.lineTo(e.target.x, e.target.y);
      ctx.stroke();
    }
    
    ctx.font = '12px sans-serif';
    ctx.textAlign = 'center';
    for(let n of nodes) {
      n.vx += (w/2 - n.x) * 0.005;
      n.vy += (h/2 - n.y) * 0.005;
      n.vx *= 0.85; n.vy *= 0.85;
      n.x += n.vx; n.y += n.vy;
      
      ctx.beginPath();
      ctx.arc(n.x, n.y, 8, 0, Math.PI*2);
      ctx.fillStyle = primaryColor;
      ctx.fill();
      ctx.fillStyle = textColor;
      ctx.fillText(n.label, n.x, n.y - 14);
    }
    animFrame = requestAnimationFrame(loop);
  }

  function stop() {
    cancelAnimationFrame(animFrame);
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

async function performAIExtraction(text, onSuccess, onError) {
  const key = getGeminiKey();
  if(!key) {
    onError('Extraction paused: Please configure your Gemini API Key in the Settings menu.');
    return;
  }
  
  GraphEngine.init();

  const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:streamGenerateContent?key=${key}&alt=sse`;
  const prompt = `You are a cognitive extractor analyzing text. Output EXACTLY ONE item per line using ONLY these formats:
NODE: <Concept Name>
EDGE: <Source Concept> -> <Target Concept> | <Relationship>

Do not write markdown or bullet points. Just lines starting with NODE: or EDGE:.

Text to analyze:
${text.slice(0, 10000)}`;

  try {
    console.log("Connecting to Gemini API...");
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] })
    });
    
    if(!response.ok) throw new Error("API Error: " + response.statusText);
    console.log("Connection established! Streaming data...");

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    let streamBuffer = '';
    let textBuffer = '';

    while(true) {
      const { done, value } = await reader.read();
      if(done) break;
      streamBuffer += decoder.decode(value, { stream: true });
      
      let lines = streamBuffer.split('\n\n');
      streamBuffer = lines.pop(); 
      
      for(const line of lines) {
        if(line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            const chunkText = data.candidates?.[0]?.content?.parts?.[0]?.text || '';
            if(chunkText) {
              console.log("Chunk received:", chunkText.replace(/\n/g, ' '));
              textBuffer += chunkText;
              let parts = textBuffer.split('\n');
              textBuffer = parts.pop();
              for(let p of parts) {
                p = p.trim();
                if(p.startsWith('NODE:')) {
                  GraphEngine.addNode(p.substring(5).trim());
                } else if(p.startsWith('EDGE:')) {
                  let split1 = p.substring(5).split('->');
                  if(split1.length === 2) {
                    let source = split1[0].trim();
                    let split2 = split1[1].split('|');
                    if(split2.length === 2) {
                      let target = split2[0].trim();
                      let label = split2[1].trim();
                      GraphEngine.addEdge(source, target, label);
                    }
                  }
                }
              }
            }
          } catch(e) {}
        }
      }
    }
    
    if(textBuffer.trim().startsWith('NODE:')) { GraphEngine.addNode(textBuffer.substring(5).trim()); }
    
    setTimeout(() => {
      GraphEngine.stop();
      onSuccess(GraphEngine.getGraph());
    }, 1500);

  } catch (err) {
    GraphEngine.stop();
    onError(err.message);
  }
}

function startSettings() {
  const triggerArea = document.getElementById('add-trigger-area');
  triggerArea.style.overflowY = 'auto';
  
  const key = getGeminiKey();
  const masked = key ? key.slice(0, 6) + '••••••••••••••••' : '';
  
  triggerArea.innerHTML = `
    <div class="settings-panel">
      <h3>Settings</h3>
      <p class="settings-subtext">Configure your neurocognitive pipeline and integration hooks.</p>
      
      <div class="settings-box">
        <h4>Gemini Connection</h4>
        <input type="password" id="settings-key-input" class="settings-input" placeholder="Paste Gemini API Key" value="${masked}">
        <div class="settings-actions">
           <button id="settings-key-save">Save Key</button>
           <button id="settings-key-test">Test Connection</button>
        </div>
        <div id="settings-api-status" class="settings-status"></div>
      </div>
      
      <button class="settings-close" onclick="App.closeDrawer(); App.renderAddTrigger();">Close Settings</button>
    </div>
  `;

  App.openDrawer();

  const inp = triggerArea.querySelector('#settings-key-input');
  const saveBtn = triggerArea.querySelector('#settings-key-save');
  const testBtn = triggerArea.querySelector('#settings-key-test');
  const statusBox = triggerArea.querySelector('#settings-api-status');

  saveBtn.addEventListener('click', () => {
    const val = inp.value.trim();
    if(val && !val.includes('••••')) {
      localStorage.setItem('gemini_key', val);
      statusBox.textContent = 'Key saved to browser!';
      statusBox.style.color = 'var(--text-sub)';
    }
  });

  testBtn.addEventListener('click', async () => {
    const currentKey = getGeminiKey();
    if(!currentKey) {
      statusBox.textContent = '🔴 Disconnected: No key saved.';
      statusBox.style.color = 'var(--danger)';
      return;
    }

    testBtn.disabled = true;
    testBtn.textContent = 'Testing...';
    statusBox.textContent = '🟠 Pinging Gemini API...';
    statusBox.style.color = 'var(--text-sub)';

    try {
      const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${currentKey}`;
      const payload = { contents: [{ parts: [{ text: "Reply OK" }] }] };
      const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      if(!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}`);
      await res.json();
      
      statusBox.textContent = '🟢 Connected Successfully';
      statusBox.style.color = '#10b981';
    } catch(err) {
      statusBox.textContent = '🔴 Disconnected: ' + err.message;
      statusBox.style.color = 'var(--danger)';
    } finally {
      testBtn.disabled = false;
      testBtn.textContent = 'Test Connection';
    }
  });
}
