const App = (() => {

  

  /* ┌──────────────────────────────────────────────────────────┐
     │  JS TABLE OF CONTENTS                                    │
     │  1. DOM references                                       │
     │  2. Pub/sub Bus                                          │
     │  3. GEO — polygon coordinate arrays (5 states × 8 polys) │
     │  4. STATES — display config                              │
     │  5. Coordinate utilities + easing                        │
     │  6. MorphEngine — shared rAF, multiple crystal tasks     │
     │  7. Transition animation helpers                         │
     │  8. Grid rendering — tiles + crystals                    │
     │  9. Data store                                           │
     │  10. Drawer                                              │
     │  11. Concept list render                                 │
     │  12. CRUD — add / delete / selectTile                    │
     │  13. setState + control helpers                          │
     │  14. Pipeline action handlers                            │
     │  15. Timer                                               │
     │  16. Init + restore                                      │
     └──────────────────────────────────────────────────────────┘ */

  // ── 1. DOM references ──────────────────────────────────────
  const card                = document.getElementById('card');
  const titleEl             = document.getElementById('title');
  const descEl              = document.getElementById('desc');
  const conceptLabelEl      = document.getElementById('concept-label');
  const primaryControls     = document.getElementById('primary-controls');
  const drillControls       = document.getElementById('drill-controls');
  const consolidateControls = document.getElementById('consolidate-controls');
  const timerDisplay        = document.getElementById('timer-display');
  const devBtn              = document.getElementById('dev-btn');
  const drawer              = document.getElementById('drawer');
  const conceptListEl       = document.getElementById('concept-list');
  const addTriggerArea      = document.getElementById('add-trigger-area');

  // Transient content store — full text, NOT in localStorage. Keyed by concept ID.
  const contentStore = new Map();

  const TILE_IDS = ['tile-0','tile-1','tile-2','tile-3'];
  const tileEls  = TILE_IDS.map(id => document.getElementById(id));

  // polygons[tileIdx][polyIdx] — rebuilt by renderGrid()
  const crystalPolygons = [null, null, null, null];

  const POLYGON_IDS = [
    'cp-top','cp-upper-left','cp-upper-right',
    'cp-lower-left','cp-lower-right',
    'cp-bottom-tip','cp-specular','cp-glow',
  ];

  // ── 2. Bus ─────────────────────────────────────────────────
  const Bus = (() => {
    const L = {};
    return {
      on:   (ev, fn) => (L[ev] ??= []).push(fn),
      emit: (ev, d)  => (L[ev]||[]).forEach(fn => fn(d)),
    };
  })();

  // ── 3. GEO ─────────────────────────────────────────────────
  // Index order: [0]cp-top [1]cp-upper-left [2]cp-upper-right
  //              [3]cp-lower-left [4]cp-lower-right
  //              [5]cp-bottom-tip [6]cp-specular [7]cp-glow
  const GEO = {
    instantiated: [
      [100,90,  85,108, 100,130, 115,108],
      [100,90,  85,108,  82,130, 100,130],
      [100,90, 100,130, 118,130, 115,108],
      [100,130,  82,130,  88,152, 100,168],
      [100,130, 100,168, 112,152, 118,130],
      [88,152, 100,168, 112,152],
      [106,96, 105,112, 109,103],
      [100,90, 115,108, 118,130, 112,152, 100,168, 88,152, 82,130, 85,108],
    ],
    growing: [
      [100,73,  79,91, 100,119, 121,91],
      [100,73,  79,91,  69,119, 100,119],
      [100,73, 100,119, 131,119, 121,91],
      [100,119,  69,119,  83,145, 100,167],
      [100,119, 100,167, 117,145, 131,119],
      [83,145, 100,167, 117,145],
      [104,77, 114,94, 112,85],
      [100,73, 121,91, 131,119, 117,145, 100,167, 83,145, 69,119, 79,91],
    ],
    fractured: [
      [101,73,  77,93, 101,119, 123,89],
      [101,73,  77,93,  66,120, 101,119],
      [101,73, 101,119, 134,117, 123,89],
      [101,119,  66,120,  82,143, 100,168],
      [101,119, 100,168, 116,147, 134,117],
      [82,143, 100,168, 116,147],
      [105,76, 117,91, 114,83],
      [101,73, 123,89, 134,117, 116,147, 100,168, 82,143, 66,120, 77,93],
    ],
    hibernating: [
      [100,38,  64,70, 100,118, 136,70],
      [100,38,  64,70,  48,118, 100,118],
      [100,38, 100,118, 152,118, 136,70],
      [100,118,  48,118,  72,165, 100,205],
      [100,118, 100,205, 128,165, 152,118],
      [72,165, 100,205, 128,165],
      [106,44, 126,74, 120,58],
      [100,38, 136,70, 152,118, 128,165, 100,205, 72,165, 48,118, 64,70],
    ],
    actualized: [
      [100,22,  52,60, 100,118, 148,60],
      [100,22,  52,60,  32,118, 100,118],
      [100,22, 100,118, 168,118, 148,60],
      [100,118,  32,118,  62,172, 100,215],
      [100,118, 100,215, 138,172, 168,118],
      [62,172, 100,215, 138,172],
      [106,28, 138,64, 126,45],
      [100,22, 148,60, 168,118, 138,172, 100,215, 62,172, 32,118, 52,60],
    ],
  };

  // ── 4. STATES config ───────────────────────────────────────
  const STATES = {
    instantiated: { title:'Raw Concept',            desc:'Causal architecture not yet extracted.' },
    growing:      { title:'Structurally Sound',     desc:'Facets forming. Ready to drill.' },
    fractured:    { title:'Misconception Detected', desc:'Knowledge gap found. Drill again to repair.' },
    hibernating:  { title:'Consolidating…',         desc:'Synaptic lockout enforced. Return tomorrow.' },
    actualized:   { title:'Consolidated',           desc:'Converted into durable understanding.' },
  };

  // ── 5. Coordinate utilities ────────────────────────────────
  function easeInOutCubic(t) { return t < 0.5 ? 4*t*t*t : 1-Math.pow(-2*t+2,3)/2; }

  function interpCoords(from, to, t) { return from.map((v,i)=>v+(to[i]-v)*t); }

  function coordsToPoints(arr) {
    const pts = [];
    for (let i=0; i<arr.length; i+=2) pts.push(arr[i]+','+arr[i+1]);
    return pts.join(' ');
  }

  // ── 6. MorphEngine — shared rAF loop ──────────────────────
  const Morph = (() => {
    const DUR = 620;
    let tasks = [];
    let raf   = null;

    function tick(now) {
      tasks = tasks.filter(task => {
        if (!task.t0) task.t0 = now;
        const t = easeInOutCubic(Math.min((now-task.t0)/DUR, 1));
        task.polys.forEach((el,i) => {
          if (el) el.setAttribute('points', coordsToPoints(interpCoords(task.from[i], task.to[i], t)));
        });
        return t < 1;
      });
      if (tasks.length > 0) { raf = requestAnimationFrame(tick); }
      else                  { raf = null; }
    }

    return {
      start(tileIdx, fromState, toState) {
        // Cancel any existing task for this tile
        tasks = tasks.filter(t => t.idx !== tileIdx);
        tasks.push({
          idx:   tileIdx,
          polys: crystalPolygons[tileIdx] || [],
          from:  GEO[fromState],
          to:    GEO[toState],
          t0:    null,
        });
        if (!raf) raf = requestAnimationFrame(tick);
      },
      snap(tileIdx, state) {
        // Remove any pending task for this tile
        tasks = tasks.filter(t => t.idx !== tileIdx);
        const polys = crystalPolygons[tileIdx];
        if (!polys) return;
        GEO[state].forEach((coords,i) => {
          if (polys[i]) polys[i].setAttribute('points', coordsToPoints(coords));
        });
      },
    };
  })();

  // ── 7. Animation helpers ───────────────────────────────────
  const ANIM_CLASSES = {
    emerge:'anim-emerge', crack:'anim-crack', cocoon:'anim-cocoon',
    actualize:'anim-actualize', repair:'anim-repair',
  };

  function playAnim(name, tileIdx) {
    const cls = ANIM_CLASSES[name];
    if (!cls) return;
    const el = document.getElementById('crystal-anim-'+tileIdx);
    if (!el) return;
    function done() {
      el.classList.remove(cls);
      el.removeEventListener('animationend',    done);
      el.removeEventListener('animationcancel', done);
    }
    Object.values(ANIM_CLASSES).forEach(c => el.classList.remove(c));
    el.addEventListener('animationend',    done);
    el.addEventListener('animationcancel', done);
    el.classList.add(cls);
  }

  // ── 8. Grid rendering ──────────────────────────────────────
  const TILE_PLATFORM = `
    <polygon class="tile-left"  points="0,40 70,80 70,90 0,50"/>
    <polygon class="tile-right" points="140,40 70,80 70,90 140,50"/>
    <polygon class="tile-top"   points="70,0 140,40 70,80 0,40"/>
    <polygon class="tile-highlight" points="70,0 140,40 70,80 0,40"/>
    <polygon class="tile-hit"   points="70,0 140,40 70,80 0,40"/>`;

  const EMPTY_TILE = `
    <polygon class="tile-left"      points="0,40 70,80 70,90 0,50"/>
    <polygon class="tile-right"     points="140,40 70,80 70,90 140,50"/>
    <polygon class="tile-top-dash"  points="70,0 140,40 70,80 0,40"/>`;

  function crystalSVG(idx, state) {
    const G = GEO[state];
    const p = coordsToPoints;
    // Visual paint order: glow → lower faces → upper faces → tip → top → specular
    return `
    <g class="crystal-anim" id="crystal-anim-${idx}">
      <g class="crystal-instance" id="crystal-${idx}" data-state="${state}"
         transform="translate(35,-39.8) scale(0.35)" style="pointer-events:none;">
        <ellipse cx="100" cy="228" rx="46" ry="7" fill="rgba(60,40,120,0.10)"/>
        <polygon id="c${idx}-cp-glow"        class="cp-glow"        points="${p(G[7])}" fill="hsl(270,20%,60%)" opacity="0.10" filter="url(#glow-filter)"/>
        <polygon id="c${idx}-cp-lower-left"  class="cp-lower-left"  points="${p(G[3])}" fill="hsl(270,16%,46%)" opacity="0.82"/>
        <polygon id="c${idx}-cp-lower-right" class="cp-lower-right" points="${p(G[4])}" fill="hsl(270,14%,38%)" opacity="0.82"/>
        <polygon id="c${idx}-cp-upper-left"  class="cp-upper-left"  points="${p(G[1])}" fill="hsl(270,18%,55%)" opacity="0.82"/>
        <polygon id="c${idx}-cp-upper-right" class="cp-upper-right" points="${p(G[2])}" fill="hsl(270,16%,46%)" opacity="0.82"/>
        <polygon id="c${idx}-cp-bottom-tip"  class="cp-bottom-tip"  points="${p(G[5])}" fill="hsl(270,14%,38%)" opacity="0.82"/>
        <polygon id="c${idx}-cp-top"         class="cp-top"         points="${p(G[0])}" fill="hsl(270,20%,68%)" opacity="0.88"/>
        <polygon id="c${idx}-cp-specular"    class="cp-specular"    points="${p(G[6])}" fill="hsl(270,30%,85%)" opacity="0.35"/>
      </g>
    </g>`;
  }

  function refreshPolygonRefs(tileIdx) {
    crystalPolygons[tileIdx] = POLYGON_IDS.map(id =>
      document.getElementById('c'+tileIdx+'-'+id)
    );
  }

  function renderGrid(concepts = loadConcepts()) {

    const activeId = getActiveId();

    tileEls.forEach((tileEl, idx) => {
      const concept   = concepts[idx] || null;
      const isSelected = concept && concept.id === activeId;
      const isEmpty   = !concept;

      tileEl.setAttribute('class', 'tile-group' +
        (isEmpty    ? ' empty'    : '') +
        (isSelected ? ' selected' : ''));

      if (isEmpty) {
        tileEl.innerHTML = EMPTY_TILE;
        crystalPolygons[idx] = null;
      } else {
        tileEl.innerHTML = TILE_PLATFORM + crystalSVG(idx, concept.state);
        refreshPolygonRefs(idx);
      }
    });
  }

  // ── 9. Data store ──────────────────────────────────────────
  const STORE_KEY = 'learnops_concepts';
  const ACTIVE_KEY = 'learnops_active';

  function generateId() {
    if (typeof crypto.randomUUID === 'function') return crypto.randomUUID();
    return Date.now().toString(36) + Math.random().toString(36).slice(2);
  }

  function loadConcepts() {
    try { return JSON.parse(localStorage.getItem(STORE_KEY)) || []; }
    catch { return []; }
  }
  function saveConcepts(arr) { localStorage.setItem(STORE_KEY, JSON.stringify(arr)); }
  function getActiveId()     { return localStorage.getItem(ACTIVE_KEY) || null; }
  function setActiveId(id)   { id ? localStorage.setItem(ACTIVE_KEY,id) : localStorage.removeItem(ACTIVE_KEY); }

  function getActiveConcept() {
    const id = getActiveId();
    return loadConcepts().find(c => c.id === id) || null;
  }
  function getActiveTileIdx() {
    const id = getActiveId();
    return loadConcepts().findIndex(c => c.id === id);
  }
  function updateActiveConcept(patch) {
    const concepts = loadConcepts();
    const id = getActiveId();
    const idx = concepts.findIndex(c => c.id === id);
    if (idx === -1) return;
    Object.assign(concepts[idx], patch);
    saveConcepts(concepts);
  }

  // ── 10. Drawer ─────────────────────────────────────────────
  function openDrawer()   { drawer.dataset.open='true';  document.body.dataset.drawerOpen='true';  }
  function closeDrawer()  { drawer.dataset.open='false'; document.body.dataset.drawerOpen='false'; }
  function toggleDrawer() { drawer.dataset.open==='true' ? closeDrawer() : openDrawer(); }

  // ── 11. Concept list render ────────────────────────────────
  function renderConceptList(concepts = loadConcepts()) {

    const activeId = getActiveId();
    conceptListEl.innerHTML = '';

    concepts.forEach((c,i) => {
      const item = document.createElement('div');
      item.className = 'concept-item' + (c.id === activeId ? ' active' : '');
      item.innerHTML = `
        <div class="concept-dot" data-state="${c.state}"></div>
        <span class="concept-item-name">${escHtml(c.name)}</span>
        <button class="concept-delete" onclick="App.deleteConcept('${c.id}',this)">×</button>`;
      item.addEventListener('click', e => {
        if (e.target.classList.contains('concept-delete')) return;
        selectConcept(c.id);
        closeDrawer();
      });
      conceptListEl.appendChild(item);
    });

    renderAddTrigger();
  }

  function renderAddTrigger() {
    addTriggerArea.style.overflowY = '';
    const full = loadConcepts().length >= 4;
    addTriggerArea.innerHTML = full
      ? `<div class="add-trigger disabled"><span class="add-trigger-icon">+</span>Grid full (4/4)</div>`
      : `<div class="add-trigger" id="add-trigger" onclick="App.startAddConcept()">
           <span class="add-trigger-icon">+</span>New concept
         </div>`;
  }

  function escHtml(s) {
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  // ── 12. CRUD ───────────────────────────────────────────────
  function buildContentInputUI(container, { onSubmit, onCancel, showNameField, showClipboard }) {
    let uploadedText = '';
    let uploadedFilename = '';
    let activeTab = 'paste';

    container.innerHTML = `
      <div class="overlay-tabs" style="margin-bottom:12px;">
        <button class="overlay-tab active" data-tab="paste">${showNameField ? 'Text' : 'Paste'}</button>
        <button class="overlay-tab" data-tab="upload">${showNameField ? 'File' : 'Upload'}</button>
      </div>
      <div class="overlay-panel" data-panel="paste">
        <textarea class="overlay-textarea" placeholder="${showNameField ? 'Paste a Wikipedia article…' : 'Paste content here…'}"></textarea>
        ${showClipboard ? '<div class="paste-actions"><button class="paste-clipboard-btn" type="button">⌘ Paste from clipboard</button><button class="wiki-random-btn" type="button">🎲 Random Wikipedia</button></div>' : ''}
      </div>
      <div class="overlay-panel" data-panel="upload" style="display:none">
        <div class="overlay-dropzone">
          Drop a file or click to browse<br>
          <span style="font-size:11px;opacity:0.65">.txt &nbsp; .md &nbsp; .pdf</span>
        </div>
        <input type="file" accept=".txt,.md,.pdf" style="display:none">
        <p class="overlay-dropfeedback"></p>
      </div>
      ${showNameField ? `
        <span class="creation-section-label">Name this concept</span>
        <input class="creation-name-input" type="text" placeholder="e.g. Photosynthesis" maxlength="80">
      ` : ''}
      <div class="${showNameField ? 'creation-footer' : 'overlay-footer'}">
        <button class="${showNameField ? 'creation-cancel' : 'overlay-cancel'}">Cancel</button>
        <button class="${showNameField ? 'creation-submit' : 'overlay-extract'}" disabled>${showNameField ? 'Add Concept →' : 'Extract →'}</button>
      </div>
    `;

    const tabs      = container.querySelectorAll('.overlay-tab');
    const panels    = container.querySelectorAll('.overlay-panel');
    const textarea  = container.querySelector('.overlay-textarea');
    const dropzone  = container.querySelector('.overlay-dropzone');
    const fileInput = container.querySelector('input[type="file"]');
    const feedback  = container.querySelector('.overlay-dropfeedback');
    const pasteClipBtn = container.querySelector('.paste-clipboard-btn');
    const wikiRandomBtn = container.querySelector('.wiki-random-btn');
    const nameInput = container.querySelector('.creation-name-input');
    const cancelBtn = container.querySelector(showNameField ? '.creation-cancel' : '.overlay-cancel');
    const submitBtn = container.querySelector(showNameField ? '.creation-submit' : '.overlay-extract');

    function hasContent() {
      return activeTab === 'paste'
        ? textarea.value.trim().length > 0
        : uploadedText.length > 0;
    }
    function checkSubmitEnabled() {
      if (showNameField) {
        submitBtn.disabled = !(hasContent() && nameInput.value.trim().length > 0);
      } else {
        submitBtn.disabled = !hasContent();
      }
    }

    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        activeTab = tab.dataset.tab;
        tabs.forEach(t => t.classList.toggle('active', t.dataset.tab === activeTab));
        panels.forEach(p => { p.style.display = p.dataset.panel === activeTab ? '' : 'none'; });
        checkSubmitEnabled();
      });
    });

    let phTimer = null;
    if (showNameField) {
      const PLACEHOLDERS = [
        'Paste a Wikipedia article…', 'Paste a research paper…',
        'Paste a meeting transcript…', 'Paste a textbook chapter…', 'Paste lecture notes…'
      ];
      let phIdx = 0;
      phTimer = setInterval(() => {
        if (!document.contains(textarea)) { clearInterval(phTimer); return; }
        if (textarea.value.length > 0) return;
        phIdx = (phIdx + 1) % PLACEHOLDERS.length;
        textarea.placeholder = PLACEHOLDERS[phIdx];
      }, 2500);
    }

    if (showClipboard && pasteClipBtn) {
      pasteClipBtn.addEventListener('click', () => {
        navigator.clipboard.readText().then(text => {
          textarea.value = text;
          textarea.focus();
          checkSubmitEnabled();
        }).catch(() => {
          textarea.focus();
          document.execCommand('paste');
        });
      });
    }

    if (showClipboard && wikiRandomBtn) {
      wikiRandomBtn.addEventListener('click', async () => {
        const orig = wikiRandomBtn.textContent;
        wikiRandomBtn.disabled = true;
        wikiRandomBtn.textContent = 'Loading…';
        try {
          const res = await fetch('https://en.wikipedia.org/api/rest_v1/page/random/summary');
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const data = await res.json();
          textarea.value = `${data.title}\n\n${data.extract}`;
          if (nameInput && !nameInput.value.trim()) nameInput.value = data.title;
          textarea.focus();
          checkSubmitEnabled();
        } catch(e) {
          wikiRandomBtn.textContent = 'Failed — retry';
          setTimeout(() => { wikiRandomBtn.textContent = orig; }, 2000);
        } finally {
          wikiRandomBtn.disabled = false;
          if (wikiRandomBtn.textContent === 'Loading…') wikiRandomBtn.textContent = orig;
        }
      });
    }

    textarea.addEventListener('input', checkSubmitEnabled);
    if (nameInput) {
      nameInput.addEventListener('input', checkSubmitEnabled);
      nameInput.addEventListener('keydown', e => {
        if (e.key === 'Enter' && !submitBtn.disabled) { e.preventDefault(); doSubmit(); }
        if (e.key === 'Escape') {
          if (phTimer) clearInterval(phTimer);
          onCancel();
        }
      });
    }

    dropzone.addEventListener('click', () => fileInput.click());
    dropzone.addEventListener('dragover', e => { e.preventDefault(); dropzone.classList.add('dragover'); });
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
    dropzone.addEventListener('drop', e => {
      e.preventDefault();
      dropzone.classList.remove('dragover');
      if (e.dataTransfer.files[0]) processUpload(e.dataTransfer.files[0]);
    });
    fileInput.addEventListener('change', () => {
      if (fileInput.files[0]) processUpload(fileInput.files[0]);
    });

    function processUpload(file) {
      uploadedText = '';
      uploadedFilename = '';
      feedback.className = 'overlay-dropfeedback';
      feedback.textContent = '';
      submitBtn.disabled = true;
      _readFile(file,
        (text, filename) => {
          uploadedText = text; uploadedFilename = filename;
          feedback.className = 'overlay-dropfeedback ok';
          feedback.textContent = `${filename} · ${text.length.toLocaleString()} chars`;
          checkSubmitEnabled();
        },
        (errMsg, fallbackText, filename) => {
          feedback.className = 'overlay-dropfeedback error';
          feedback.textContent = errMsg;
          if (fallbackText !== undefined) {
            uploadedText = fallbackText; uploadedFilename = filename;
            checkSubmitEnabled();
          }
        }
      );
    }

    cancelBtn.addEventListener('click', () => {
      if (phTimer) clearInterval(phTimer);
      onCancel();
    });

    submitBtn.addEventListener('mousedown', e => {
      e.preventDefault();
      doSubmit();
    });

    function doSubmit() {
      let text, type, filename;
      if (activeTab === 'paste') {
        text = textarea.value.trim();
        type = 'text';
        filename = null;
      } else {
        text = uploadedText;
        type = 'file';
        filename = uploadedFilename;
      }
      if (phTimer) clearInterval(phTimer);
      onSubmit({ text, type, filename, name: nameInput ? nameInput.value.trim() : null });
    }

    textarea.focus();
    return {
      destroy() {
        if (phTimer) clearInterval(phTimer);
        container.innerHTML = '';
      }
    };
  }

  function startAddConcept() {
    addTriggerArea.style.overflowY = 'auto';
    addTriggerArea.innerHTML = '<div class="creation-form"></div>';
    const form = addTriggerArea.querySelector('.creation-form');
    
    buildContentInputUI(form, {
      showNameField: true,
      showClipboard: true,
      onSubmit: ({ text, type, filename, name }) => {
        if (!name || !text) return;
        const concepts = loadConcepts();
        if (concepts.length >= 4) { renderAddTrigger(); return; }

        const id = generateId();

        // Show full-screen extraction overlay immediately
        const extractOverlay = document.createElement('div');
        extractOverlay.id = 'extract-overlay';
        extractOverlay.innerHTML = `
          <div class="extract-body">
            <div class="extract-spinner"></div>
            <p class="extract-label">Extracting concepts</p>
            <p class="extract-name">${escHtml(name)}</p>
          </div>
        `;
        document.body.appendChild(extractOverlay);
        requestAnimationFrame(() => extractOverlay.classList.add('visible'));

        function removeOverlay() {
          extractOverlay.classList.remove('visible');
          setTimeout(() => { if(extractOverlay.parentNode) extractOverlay.parentNode.removeChild(extractOverlay); }, 400);
        }

        performAIExtraction(text, (graphData) => {
          removeOverlay();
          const concept = {
            id, name, state: 'growing',
            createdAt: Date.now(), timerStart: null,
            contentPreview: text.slice(0, 500),
            contentType: type,
            contentFilename: filename,
            graphData: graphData
          };
          contentStore.set(id, text);
          concepts.push(concept);
          saveConcepts(concepts);
          renderGrid(concepts);
          renderConceptList(concepts);
          selectConcept(concept.id);
          closeDrawer();
        }, (errMsg) => {
          removeOverlay();
          alert('Extraction Failed: ' + errMsg);
        });
      },
      onCancel: () => {
        renderAddTrigger();
      }
    });
  }

  function deleteConcept(id, btnEl) {
    const item = btnEl.closest('.concept-item');
    if (item) { item.style.transition='all 0.2s ease'; item.style.opacity='0'; item.style.transform='translateX(-12px)'; }

    setTimeout(() => {
      const concepts = loadConcepts().filter(c => c.id !== id);
      saveConcepts(concepts);

      if (getActiveId() === id) {
        if (concepts.length > 0) { selectConcept(concepts[0].id); }
        else { setActiveId(null); showEmptyState(); }
      }
      renderGrid();
      renderConceptList();
    }, 200);
  }

  function selectTile(tileIdx) {
    const concepts = loadConcepts();
    const concept  = concepts[tileIdx];
    if (concept)  { selectConcept(concept.id); }
    else          { openDrawer(); }
  }

  function selectConcept(id) {
    hideContentOverlay();
    setActiveId(id);
    const concept = loadConcepts().find(c => c.id === id);
    if (!concept) return;

    // Update card info
    conceptLabelEl.textContent = concept.name;
    titleEl.textContent = STATES[concept.state].title;
    descEl.textContent  = STATES[concept.state].desc;

    // Night mode
    document.body.classList.toggle('night', concept.state === 'hibernating');

    // Restore controls for this concept's state
    applyControlsForState(concept.state, concept);

    renderGrid();       // updates selection highlight
    renderConceptList();
  }

  // ── 13. setState + controls ────────────────────────────────
  function setState(newState) {
    const concepts = loadConcepts();
    const activeId = getActiveId();
    const tileIdx  = concepts.findIndex(c => c.id === activeId);
    if (tileIdx === -1) return;

    const prevState = concepts[tileIdx].state;

    // Persist
    const patch = { state: newState };
    if (newState !== 'hibernating') patch.timerStart = null;
    updateActiveConcept(patch);

    // Update crystal group's data-state (drives CSS color transitions)
    const crystalEl = document.getElementById('crystal-'+tileIdx);
    if (crystalEl) {
      crystalEl.dataset.state = newState;
      if (prevState !== newState) Morph.start(tileIdx, prevState, newState);
    }

    // Update dot in list
    const dot = conceptListEl.querySelector(`.concept-item.active .concept-dot`);
    if (dot) dot.dataset.state = newState;

    // Card text + night mode
    titleEl.textContent = STATES[newState].title;
    descEl.textContent  = STATES[newState].desc;
    document.body.classList.toggle('night', newState === 'hibernating');

    Bus.emit('state:change', { from:prevState, to:newState, tileIdx });
    applyControlsForState(newState, getActiveConcept());
  }

  function applyControlsForState(state, concept) {
    stopTimer();
    removeRestartButton();
    document.getElementById('btn-drill').textContent = '3. Drill (Recall)';
    showControls(false,false,false,false,false);

    if      (state==='instantiated') { showControls(true,false,false,false,false); setButtons(true,false); }
    else if (state==='growing')      { showControls(true,false,true,false,false);  setButtons(false,true); }
    else if (state==='fractured') {
      showControls(true,false,false,false,false); setButtons(false,true);
      document.getElementById('btn-drill').textContent = '3. Drill (Repair)';
    }
    else if (state==='hibernating') {
      let remaining = 24*60*60;
      if (concept && concept.timerStart) {
        const elapsed = Math.floor((Date.now()-concept.timerStart)/1000);
        remaining = Math.max(0, 24*60*60-elapsed);
      }
      if (remaining === 0) { completeConsolidation(); return; }
      timeLeft = remaining;
      showControls(false,false,false,true,true);
      startTimer();
    }
    else if (state==='actualized') { showRestartButton(); }
  }

  function showControls(primary, drill, consolidate, timer, dev) {
    primaryControls.style.display     = primary     ? 'flex'  : 'none';
    drillControls.style.display       = drill       ? 'flex'  : 'none';
    consolidateControls.style.display = consolidate ? 'flex'  : 'none';
    timerDisplay.style.display        = timer       ? 'block' : 'none';
    devBtn.style.display              = dev         ? 'block' : 'none';
  }
  function setButtons(ex, dr) {
    document.getElementById('btn-extract').disabled = !ex;
    document.getElementById('btn-drill').disabled   = !dr;
  }

  function showEmptyState() {
    hideContentOverlay();
    stopTimer();
    removeRestartButton();
    conceptLabelEl.textContent = '';
    titleEl.textContent = 'LearnOps';
    descEl.textContent  = 'Open the menu to add your first concept.';
    document.body.classList.remove('night');
    showControls(false,false,false,false,false);
  }

  function showRestartButton() {
    removeRestartButton();
    const btn = document.createElement('button');
    btn.id = 'restart-btn';
    btn.textContent = 'Add Another Concept';
    btn.style.marginTop = '10px';
    btn.onclick = () => openDrawer();
    card.appendChild(btn);
  }
  function removeRestartButton() {
    const b = document.getElementById('restart-btn');
    if (b) b.remove();
  }

  // ── 14. Pipeline handlers ──────────────────────────────────

  // Shared file reader. onSuccess(text, filename), onError(msg) or onError(msg, fallbackText, filename).
  function _readFile(file, onSuccess, onError) {
    const ext = file.name.split('.').pop().toLowerCase();
    if (!['txt', 'md', 'pdf'].includes(ext)) {
      onError('Unsupported file type. Use .txt, .md, or .pdf.'); return;
    }
    if (file.size > 2 * 1024 * 1024) {
      onError('File too large. Maximum size is 2MB.'); return;
    }
    const reader = new FileReader();
    if (ext === 'pdf') {
      reader.onload = e => {
        const bytes = new Uint8Array(e.target.result);
        let raw = '';
        for (let i = 0; i < bytes.length; i++) {
          if (bytes[i] >= 32 && bytes[i] < 128) raw += String.fromCharCode(bytes[i]);
        }
        const matches = raw.match(/BT[\s\S]*?ET/g) || [];
        let extracted = matches.join(' ')
          .replace(/\(([^)]+)\)/g, '$1 ')
          .replace(/[^a-zA-Z0-9 \n.,!?;:'"()-]/g, ' ')
          .replace(/\s+/g, ' ').trim();
        if (extracted.length < 50) {
          const fallback = '[PDF attached — extraction pending]';
          onError('Could not extract text from this PDF. Try pasting the content instead.', fallback, file.name);
        } else {
          onSuccess(extracted, file.name);
        }
      };
      reader.readAsArrayBuffer(file);
    } else {
      reader.onload = e => onSuccess(e.target.result, file.name);
      reader.readAsText(file);
    }
  }

  function hideContentOverlay() {
    const overlay = document.getElementById('content-overlay');
    if (!overlay) return;
    overlay.remove();
    const concept = getActiveConcept();
    if (concept) applyControlsForState(concept.state, concept);
  }

  function showContentOverlay() {
    primaryControls.style.display = 'none';
    const conceptId = getActiveId();
    
    const overlay = document.createElement('div');
    overlay.id = 'content-overlay';
    primaryControls.insertAdjacentElement('afterend', overlay);

    buildContentInputUI(overlay, {
      showNameField: false,
      showClipboard: false,
      onSubmit: ({ text, type, filename }) => {
        if (!text) return;
        contentStore.set(conceptId, text);
        updateActiveConcept({
          contentPreview: text.slice(0, 500),
          contentType: type,
          contentFilename: filename,
        });
        overlay.remove();
        setState('growing');
        playAnim('emerge', getActiveTileIdx());
      },
      onCancel: hideContentOverlay
    });
  }

  function extract() {
    const concept = getActiveConcept();
    if (!concept) return;
    if (concept.contentPreview) {
      setState('growing');
      playAnim('emerge', getActiveTileIdx());
      return;
    }
    showContentOverlay();
  }

  function drill()     { showControls(false,true,false,false,false); }

  function drillFail() {
    setState('fractured');
    playAnim('crack', getActiveTileIdx());
  }

  function drillPass() {
    const fromFractured = getActiveConcept()?.state === 'fractured';
    setState('growing');
    if (fromFractured) playAnim('repair', getActiveTileIdx());
  }

  function consolidate() {
    updateActiveConcept({ timerStart:Date.now() });
    setState('hibernating');
    playAnim('cocoon', getActiveTileIdx());
  }

  // ── 15. Timer ──────────────────────────────────────────────
  let timerInterval = null;
  let timeLeft      = 24*60*60;

  function startTimer() {
    stopTimer();
    updateTimerDisplay();
    timerInterval = setInterval(() => {
      timeLeft--;
      updateTimerDisplay();
      if (timeLeft <= 0) completeConsolidation();
    }, 1000);
  }
  function stopTimer()  { clearInterval(timerInterval); timerInterval = null; }
  function updateTimerDisplay() {
    const h = Math.floor(timeLeft/3600).toString().padStart(2,'0');
    const m = Math.floor((timeLeft%3600)/60).toString().padStart(2,'0');
    const s = (timeLeft%60).toString().padStart(2,'0');
    timerDisplay.textContent = `${h}:${m}:${s}`;
  }
  function completeConsolidation() {
    stopTimer();
    updateActiveConcept({ timerStart:null });
    setState('actualized');
    playAnim('actualize', getActiveTileIdx());
  }
  function fastForward() { timeLeft = 3; }

  // ── 16. Init + restore ─────────────────────────────────────





  // Migrate legacy single-concept storage
  const legacyState = localStorage.getItem('learnops-state');
  if (legacyState && STATES[legacyState]) {
    const c = {
      id: generateId(), name: 'My First Concept', state: legacyState,
      createdAt: Date.now(),
      timerStart: legacyState==='hibernating'
        ? parseInt(localStorage.getItem('learnops-timer-start')||'0',10)||null : null,
    };
    saveConcepts([c]);
    setActiveId(c.id);
    localStorage.removeItem('learnops-state');
    localStorage.removeItem('learnops-timer-start');
  }

  // Tile tooltip hover/tap
  const tooltipEl = document.getElementById('tile-tooltip');
  let tooltipTimeout = null;

  // Pixel coords (left, top) — tooltip bottom-center above each crystal apex within #grid-container
  const TILE_TOOLTIP_POS = [
    { left: 140, top: 37  },  // tile-0 (back center)
    { left: 70,  top: 77  },  // tile-1 (mid left)
    { left: 210, top: 77  },  // tile-2 (mid right)
    { left: 140, top: 117 },  // tile-3 (front center)
  ];

  function showTileTooltip(idx) {
    const c = loadConcepts()[idx];
    if (!c) return;
    const pos = TILE_TOOLTIP_POS[idx];
    tooltipEl.style.left = pos.left + 'px';
    tooltipEl.style.top  = pos.top  + 'px';
    tooltipEl.textContent = c.name + '  ·  ' + STATES[c.state].title;
    tooltipEl.classList.add('visible');
  }
  function hideTileTooltip() {
    tooltipEl.classList.remove('visible');
  }

  tileEls.forEach((el, idx) => {
    el.addEventListener('mouseenter', () => showTileTooltip(idx));
    el.addEventListener('mouseleave', hideTileTooltip);
    el.addEventListener('touchstart', () => {
      showTileTooltip(idx);
      clearTimeout(tooltipTimeout);
      tooltipTimeout = setTimeout(hideTileTooltip, 1800);
    }, { passive: true });
  });

  // Render grid first (populates polygon DOM nodes)
  renderGrid();
  renderConceptList();

  // Restore selected concept
  const concepts  = loadConcepts();
  const toLoad    = concepts.find(c => c.id === getActiveId()) || concepts[0] || null;

  if (!toLoad) {
    showEmptyState();
  } else {
    setActiveId(toLoad.id);
    conceptLabelEl.textContent = toLoad.name;
    titleEl.textContent = STATES[toLoad.state].title;
    descEl.textContent  = STATES[toLoad.state].desc;
    document.body.classList.toggle('night', toLoad.state === 'hibernating');
    applyControlsForState(toLoad.state, toLoad);
    renderGrid(); // re-render to apply .selected class
  }

  return {
    toggleDrawer, openDrawer, closeDrawer,
    selectTile, selectConcept: (id) => { selectConcept(id); closeDrawer(); },
    deleteConcept,
    startAddConcept,
    renderAddTrigger,
    extract, drill, drillFail, drillPass, consolidate,
    fastForward,
  };

})();
window.App = App;
