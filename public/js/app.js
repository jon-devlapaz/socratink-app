import { Bus } from './bus.js';
import { GEO, easeInOutCubic, interpCoords, coordsToPoints } from './geo.js';
import { Morph, crystalPolygons } from './morph.js';
import { escHtml, mountKnowledgeGraph } from './graph-view.js?v=2';
import {
  STATES, generateId, loadConcepts, saveConcepts,
  getActiveId, setActiveId, getActiveConcept,
  getActiveTileIdx, updateActiveConcept, contentStore
} from './store.js';

import {
  card, titleEl, descEl, conceptLabelEl, primaryControls, drillControls,
  heroStateChipEl, heroPrimaryActionEl, consolidateControls, timerDisplay, devBtn, drawer, drawerToggle, conceptListEl,
  addTriggerArea, heroInfo, drillUi, chatHistory, chatInput, drillTitle,
  TILE_IDS, tileEls, POLYGON_IDS
} from './dom.js';

const App = (() => {
  const THEME_STORAGE_KEY = 'learnops-theme';
  let currentGraphController = null;
  let currentMapMode = 'study';
  let activeDrillNode = null;
  let tutorialMode = false;
  let tutorialRefreshRaf = null;
  let activeTutorialTarget = null;
  let themePreference = 'light';
  let currentPrimaryNav = 'nav-dashboard';

  const themeToggleEl = document.getElementById('theme-toggle');

  function getStoredThemePreference() {
    try {
      const stored = localStorage.getItem(THEME_STORAGE_KEY);
      return stored === 'dark' ? 'dark' : 'light';
    } catch (err) {
      console.warn('Theme preference unavailable.', err);
      return 'light';
    }
  }

  function updateThemeToggleUi(resolvedTheme) {
    if (!themeToggleEl) return;
    const isDark = resolvedTheme === 'dark';
    const label = isDark ? 'Switch to light mode' : 'Switch to dark mode';
    themeToggleEl.dataset.theme = resolvedTheme;
    themeToggleEl.setAttribute('aria-pressed', String(isDark));
    themeToggleEl.setAttribute('aria-label', label);
    themeToggleEl.setAttribute('title', label);
  }

  function applyThemePreference(nextPreference, { persist = true } = {}) {
    themePreference = nextPreference === 'dark' ? 'dark' : 'light';
    const resolvedTheme = themePreference;
    document.body.classList.toggle('night', resolvedTheme === 'dark');
    document.body.dataset.theme = resolvedTheme;
    document.documentElement.dataset.theme = resolvedTheme;
    updateThemeToggleUi(resolvedTheme);
    if (!persist) return;
    try {
      localStorage.setItem(THEME_STORAGE_KEY, themePreference);
    } catch (err) {
      console.warn('Theme preference could not be saved.', err);
    }
  }

  function toggleTheme() {
    applyThemePreference(themePreference === 'dark' ? 'light' : 'dark');
  }

  function setMapShellOpen(isOpen) {
    document.body.dataset.mapOpen = isOpen ? 'true' : 'false';
    if (!drawerToggle) return;
    drawerToggle.setAttribute('aria-hidden', String(isOpen));
    drawerToggle.tabIndex = isOpen ? -1 : 0;
  }

  function getHeroStateLabel(state) {
    switch (state) {
      case 'instantiated': return 'Instantiated';
      case 'growing': return 'Growing';
      case 'fractured': return 'Fractured';
      case 'hibernating': return 'Consolidating';
      case 'actualized': return 'Actualized';
      default: return 'Board Empty';
    }
  }

  function getHeroGuidance(concept) {
    if (!concept) return 'Create a concept to start building your board.';
    switch (concept.state) {
      case 'instantiated':
        return concept.graphData
          ? 'Open the map to inspect structure before recall.'
          : 'Map this concept to turn it into a usable board node.';
      case 'growing':
        return concept.graphData
          ? 'Inspect the concept map, then test recall.'
          : 'Continue by mapping this concept into a board-ready structure.';
      case 'fractured':
        return 'This concept needs repair through another drill.';
      case 'hibernating':
        return 'This concept is consolidating and cannot be drilled yet.';
      case 'actualized':
        return 'Review the map or revisit recall if you need a refresh.';
      default:
        return 'Create a concept to start building your board.';
    }
  }

  function getHeroActionConfig(concept) {
    if (!concept) {
      return { label: 'Add Concept', action: 'add', disabled: false };
    }
    switch (concept.state) {
      case 'instantiated':
        return concept.graphData
          ? { label: 'Open Map', action: 'open-map', disabled: false }
          : { label: 'Map Concept', action: 'extract', disabled: false };
      case 'growing':
        return concept.graphData
          ? { label: 'Open Map', action: 'open-map', disabled: false }
          : { label: 'Map Concept', action: 'extract', disabled: false };
      case 'fractured':
        return { label: 'Start Drill', action: 'drill', disabled: false };
      case 'hibernating':
        return concept.graphData
          ? { label: 'Review Map', action: 'open-map', disabled: false }
          : { label: 'Return Later', action: 'wait', disabled: true };
      case 'actualized':
        return concept.graphData
          ? { label: 'Review Map', action: 'open-map', disabled: false }
          : { label: 'Open Board', action: 'wait', disabled: true };
      default:
        return { label: 'Add Concept', action: 'add', disabled: false };
    }
  }

  function renderHero(concept) {
    if (!concept) {
      conceptLabelEl.textContent = 'Dashboard';
      titleEl.textContent = 'Add your first socraTink';
      descEl.textContent = getHeroGuidance(null);
      if (heroStateChipEl) {
        heroStateChipEl.textContent = 'Board Empty';
        heroStateChipEl.dataset.state = 'empty';
      }
    } else {
      conceptLabelEl.textContent = 'Selected Concept';
      titleEl.textContent = concept.name;
      descEl.textContent = getHeroGuidance(concept);
      if (heroStateChipEl) {
        heroStateChipEl.textContent = getHeroStateLabel(concept.state);
        heroStateChipEl.dataset.state = concept.state;
      }
    }

    if (heroPrimaryActionEl) {
      const config = getHeroActionConfig(concept);
      heroPrimaryActionEl.textContent = config.label;
      heroPrimaryActionEl.dataset.action = config.action;
      heroPrimaryActionEl.disabled = Boolean(config.disabled);
      heroPrimaryActionEl.title = config.disabled ? 'This action is unavailable right now.' : config.label;
    }
  }

  function runHeroAction() {
    const concept = getActiveConcept();
    const action = heroPrimaryActionEl?.dataset.action || (!concept ? 'add' : '');
    if (action === 'add') {
      showDashboard();
      openDrawer();
      startAddConcept();
      requestAnimationFrame(() => {
        addTriggerArea.scrollIntoView({ block: 'end', behavior: 'smooth' });
        const nameInput = addTriggerArea.querySelector('.creation-name-input');
        if (nameInput instanceof HTMLInputElement) nameInput.focus();
      });
      return;
    }
    if (action === 'extract') {
      extract();
      return;
    }
    if (action === 'drill') {
      drill();
      return;
    }
    if (action === 'open-map') {
      if (!concept?.graphData) return;
      showMapView(concept);
      setMapMode('study');
    }
  }


  // ── 7. Animation helpers ───────────────────────────────────
  const ANIM_CLASSES = {
    emerge: 'anim-emerge', crack: 'anim-crack', cocoon: 'anim-cocoon',
    actualize: 'anim-actualize', repair: 'anim-repair',
  };

  function playAnim(name, tileIdx) {
    const cls = ANIM_CLASSES[name];
    if (!cls) return;
    const el = document.getElementById('crystal-anim-' + tileIdx);
    if (!el) return;
    function done() {
      el.classList.remove(cls);
      el.removeEventListener('animationend', done);
      el.removeEventListener('animationcancel', done);
    }
    Object.values(ANIM_CLASSES).forEach(c => el.classList.remove(c));
    el.addEventListener('animationend', done);
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
    <polygon class="tile-top-empty" points="70,0 140,40 70,80 0,40"/>
    <polygon class="tile-top-dash"  points="70,0 140,40 70,80 0,40"/>
    <polygon class="tile-hit"       points="70,0 140,40 70,80 0,40"/>`;

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
      document.getElementById('c' + tileIdx + '-' + id)
    );
  }

  function renderGrid(concepts = loadConcepts()) {

    const activeId = getActiveId();

    tileEls.forEach((tileEl, idx) => {
      const concept = concepts[idx] || null;
      const isSelected = concept && concept.id === activeId;
      const isEmpty = !concept;

      tileEl.setAttribute('class', 'tile-group' +
        (isEmpty ? ' empty' : '') +
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

  // ── 10. Drawer ─────────────────────────────────────────────
  function openDrawer() {
    drawer.dataset.open = 'true';
    document.body.dataset.drawerOpen = 'true';
    if (drawerToggle) drawerToggle.setAttribute('aria-expanded', 'true');
    scheduleTutorialRefresh();
  }
  function closeDrawer() {
    drawer.dataset.open = 'false';
    document.body.dataset.drawerOpen = 'false';
    if (drawerToggle) drawerToggle.setAttribute('aria-expanded', 'false');
    scheduleTutorialRefresh();
  }
  function toggleDrawer() { drawer.dataset.open === 'true' ? closeDrawer() : openDrawer(); }

  if (window.innerWidth >= 900) openDrawer();

  function clearSettingsPanel() {
    const triggerArea = document.getElementById('add-trigger-area');
    const settingsPanel = triggerArea?.querySelector('.settings-panel');
    if (!settingsPanel) return;
    const settingsBtn = document.getElementById('nav-settings');
    if (settingsBtn) delete settingsBtn.dataset.engaged;
    renderAddTrigger();
  }

  // ── 11. Concept list render ────────────────────────────────
  function renderConceptList(concepts = loadConcepts()) {

    const activeId = getActiveId();
    conceptListEl.innerHTML = '';

    concepts.forEach((c, i) => {
      const item = document.createElement('div');
      item.className = 'concept-item' + (c.id === activeId ? ' active' : '');
      item.innerHTML = `
        <div class="concept-dot" data-state="${c.state}"></div>
        <span class="concept-item-name">${escHtml(c.name)}</span>
        <button class="concept-delete" onclick="App.deleteConcept('${c.id}',this)">×</button>`;
      item.addEventListener('click', e => {
        if (e.target.classList.contains('concept-delete')) return;
        showDashboard();
        selectConcept(c.id);
        if (c.graphData) showMapView(c);
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
           <span class="add-trigger-icon">+</span>new socraTink
         </div>`;
    scheduleTutorialRefresh();
  }

  function isYouTubeUrl(value) {
    try {
      const parsed = new URL(value);
      const host = parsed.hostname.toLowerCase();
      return host.includes('youtube.com') || host.includes('youtu.be') || host.includes('youtube-nocookie.com');
    } catch {
      return false;
    }
  }

  // ── 12. CRUD ───────────────────────────────────────────────
  function buildContentInputUI(container, { onSubmit, onCancel, showNameField, showClipboard }) {
    let uploadedText = '';
    let uploadedFilename = '';
    let fetchedUrlText = '';
    let fetchedUrlTitle = '';
    let fetchedUrl = '';
    let activeTab = 'paste';

    container.innerHTML = `
      <div class="overlay-tabs" style="margin-bottom:12px;">
        <button class="overlay-tab active" data-tab="paste">${showNameField ? 'Text' : 'Paste'}</button>
        <button class="overlay-tab" data-tab="url">URL</button>
        <button class="overlay-tab" data-tab="upload">${showNameField ? 'File' : 'Upload'}</button>
      </div>
      <div class="overlay-panel" data-panel="paste">
        <textarea class="overlay-textarea" placeholder="${showNameField ? 'Paste a Wikipedia article…' : 'Paste content here…'}"></textarea>
        ${showClipboard ? '<div class="paste-actions"><button class="paste-clipboard-btn" type="button">⌘ Paste from clipboard</button><button class="wiki-random-btn" type="button">🔬 Random Science</button><button class="graph-preview-btn" type="button">⚡ Preview Graph</button></div>' : ''}
      </div>
      <div class="overlay-panel" data-panel="url" style="display:none">
        <input class="overlay-url-input" type="url" placeholder="https://example.com/article">
        <p class="overlay-dropfeedback overlay-url-feedback"></p>
      </div>
      <div class="overlay-panel" data-panel="upload" style="display:none">
        <div class="overlay-dropzone">
          Drop a file or click to browse<br>
          <span style="font-size:11px;opacity:0.65">.txt &nbsp; .md &nbsp; .pdf</span>
        </div>
        <input type="file" accept=".txt,.md,.pdf" style="display:none">
        <p class="overlay-dropfeedback overlay-file-feedback"></p>
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

    const tabs = container.querySelectorAll('.overlay-tab');
    const panels = container.querySelectorAll('.overlay-panel');
    const textarea = container.querySelector('.overlay-textarea');
    const dropzone = container.querySelector('.overlay-dropzone');
    const fileInput = container.querySelector('input[type="file"]');
    const feedback = container.querySelector('.overlay-file-feedback');
    const urlInput = container.querySelector('.overlay-url-input');
    const urlFeedback = container.querySelector('.overlay-url-feedback');
    const pasteClipBtn = container.querySelector('.paste-clipboard-btn');
    const wikiRandomBtn = container.querySelector('.wiki-random-btn');
    const graphPreviewBtn = container.querySelector('.graph-preview-btn');
    const nameInput = container.querySelector('.creation-name-input');
    const cancelBtn = container.querySelector(showNameField ? '.creation-cancel' : '.overlay-cancel');
    const submitBtn = container.querySelector(showNameField ? '.creation-submit' : '.overlay-extract');

    function hasContent() {
      if (activeTab === 'paste') return textarea.value.trim().length > 0;
      if (activeTab === 'url') return urlInput.value.trim().length > 0;
      return uploadedText.length > 0;
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

    const STEM_CATEGORIES = [
      'Quantum_mechanics', 'Thermodynamics', 'Electromagnetism',
      'Organic_chemistry', 'Biochemistry', 'Molecular_biology',
      'Neuroscience', 'Evolutionary_biology', 'Genetics', 'Ecology',
      'Calculus', 'Linear_algebra', 'Number_theory', 'Probability_theory',
      'Computer_algorithms', 'Machine_learning', 'Astronomy',
      'Particle_physics', 'Fluid_mechanics', 'Cell_biology'
    ];

    if (showClipboard && wikiRandomBtn) {
      wikiRandomBtn.addEventListener('click', async () => {
        const orig = wikiRandomBtn.textContent;
        wikiRandomBtn.disabled = true;
        wikiRandomBtn.textContent = 'Loading…';
        try {
          // Two-step: category members → article summary
          async function fetchStemArticle(attempt) {
            const cat = STEM_CATEGORIES[Math.floor(Math.random() * STEM_CATEGORIES.length)];
            const membersRes = await fetch(
              `https://en.wikipedia.org/w/api.php?action=query&list=categorymembers&cmtitle=Category:${cat}&cmlimit=50&cmtype=page&cmnamespace=0&format=json&origin=*`
            );
            if (!membersRes.ok) throw new Error(`HTTP ${membersRes.status}`);
            const membersData = await membersRes.json();
            const members = membersData.query?.categorymembers || [];
            // Retry once with a fresh category if this one is empty
            if (members.length === 0 && attempt < 2) return fetchStemArticle(attempt + 1);
            if (members.length === 0) throw new Error('No articles found');
            return members[Math.floor(Math.random() * members.length)];
          }

          const article = await fetchStemArticle(1);
          const summaryRes = await fetch(
            `https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(article.title)}`
          );
          if (!summaryRes.ok) throw new Error(`HTTP ${summaryRes.status}`);
          const data = await summaryRes.json();

          textarea.value = `${data.title}\n\n${data.extract}`;
          if (nameInput && !nameInput.value.trim()) nameInput.value = data.title;
          textarea.focus();
          checkSubmitEnabled();
        } catch (e) {
          wikiRandomBtn.textContent = 'Failed — retry';
          setTimeout(() => { wikiRandomBtn.textContent = orig; }, 2000);
        } finally {
          wikiRandomBtn.disabled = false;
          if (wikiRandomBtn.textContent === 'Loading…') wikiRandomBtn.textContent = orig;
        }
      });
    }

    if (showClipboard && graphPreviewBtn) {
      graphPreviewBtn.addEventListener('click', () => {
        const name = (nameInput && nameInput.value.trim()) || 'Photosynthesis';
        window.testGraph(name);
      });
    }

    textarea.addEventListener('input', checkSubmitEnabled);
    if (urlInput) {
      urlInput.addEventListener('input', () => {
        fetchedUrlText = '';
        fetchedUrlTitle = '';
        fetchedUrl = '';
        if (urlFeedback) {
          urlFeedback.className = 'overlay-dropfeedback overlay-url-feedback';
          urlFeedback.textContent = '';
        }
        checkSubmitEnabled();
      });
      urlInput.addEventListener('keydown', e => {
        if (e.key === 'Enter' && !submitBtn.disabled) { e.preventDefault(); doSubmit(); }
      });
    }
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
      let text, type, filename, url;
      if (activeTab === 'paste') {
        text = textarea.value.trim();
        type = 'text';
        filename = null;
        url = null;
      } else if (activeTab === 'url') {
        text = fetchedUrlText;
        type = 'url';
        filename = fetchedUrlTitle || null;
        url = urlInput.value.trim();
      } else {
        text = uploadedText;
        type = 'file';
        filename = uploadedFilename;
        url = null;
      }
      if (phTimer) clearInterval(phTimer);
      onSubmit({ text, type, filename, url, name: nameInput ? nameInput.value.trim() : null });
    }

    if (showNameField && nameInput) nameInput.focus();
    else textarea.focus();
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
      onSubmit: async ({ text, type, filename, url, name }) => {
        if (!name) return;
        const concepts = loadConcepts();
        if (concepts.length >= 4) { renderAddTrigger(); return; }

        const id = generateId();

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
          setTimeout(() => { if (extractOverlay.parentNode) extractOverlay.parentNode.removeChild(extractOverlay); }, 400);
        }

        try {
          let sourceText = text;
          let sourceFilename = filename;

          if (type === 'url') {
            if (!url) throw new Error('No URL provided.');
            const isYouTube = isYouTubeUrl(url);
            extractOverlay.querySelector('.extract-label').textContent = isYouTube
              ? 'Fetching transcript...'
              : 'Fetching page...';
            const response = await fetch(isYouTube ? '/api/extract-youtube' : '/api/extract-url', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ url })
            });
            const payload = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(payload.detail || 'Failed to fetch page.');
            sourceText = payload.text;
            sourceFilename = payload.title || url;
          }

          if (!sourceText) throw new Error('No content provided.');

          extractOverlay.querySelector('.extract-label').textContent = 'Mapping knowledge...';
          const jsonPayload = await window.AIService.generateKnowledgeMap(sourceText);

          removeOverlay();
          const concept = {
            id, name, state: 'growing',
            createdAt: Date.now(), timerStart: null,
            contentPreview: sourceText.slice(0, 500),
            contentType: type,
            contentFilename: sourceFilename,
            sourceUrl: type === 'url' ? url : null,
            graphData: JSON.stringify(jsonPayload)
          };
          contentStore.set(id, sourceText);
          concepts.push(concept);
          saveConcepts(concepts);
          renderGrid(concepts);
          renderConceptList(concepts);
          selectConcept(concept.id);
          closeDrawer();
        } catch (err) {
          removeOverlay();
          alert('Extraction Failed: ' + err.message);
        }
      },
      onCancel: () => {
        renderAddTrigger();
      }
    });
    scheduleTutorialRefresh();
  }

  function deleteConcept(id, btnEl) {
    const item = btnEl.closest('.concept-item');
    if (item) { item.style.transition = 'all 0.2s ease'; item.style.opacity = '0'; item.style.transform = 'translateX(-12px)'; }

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
    const concept = concepts[tileIdx];
    if (concept) {
      selectConcept(concept.id);
      if (concept.graphData) showMapView(concept);
    } else {
      openDrawer();
      startAddConcept();
    }
  }

  function selectConcept(id) {
    hideContentOverlay();
    hideMapView();
    setNavActive('nav-dashboard');
    setActiveId(id);
    const concept = loadConcepts().find(c => c.id === id);
    if (!concept) return;

    renderHero(concept);

    // Restore controls for this concept's state
    applyControlsForState(concept.state, concept);

    renderGrid();       // updates selection highlight
    renderConceptList();
  }

  // ── 13. setState + controls ────────────────────────────────
  function setState(newState) {
    const concepts = loadConcepts();
    const activeId = getActiveId();
    const tileIdx = concepts.findIndex(c => c.id === activeId);
    if (tileIdx === -1) return;

    const prevState = concepts[tileIdx].state;

    // Persist
    const patch = { state: newState };
    if (newState !== 'hibernating') patch.timerStart = null;
    updateActiveConcept(patch);

    // Update crystal group's data-state (drives CSS color transitions)
    const crystalEl = document.getElementById('crystal-' + tileIdx);
    if (crystalEl) {
      crystalEl.dataset.state = newState;
      if (prevState !== newState) Morph.start(tileIdx, prevState, newState);
    }

    // Update dot in list
    const dot = conceptListEl.querySelector(`.concept-item.active .concept-dot`);
    if (dot) dot.dataset.state = newState;

    Bus.emit('state:change', { from: prevState, to: newState, tileIdx });
    const activeConcept = getActiveConcept();
    renderHero(activeConcept);
    applyControlsForState(newState, activeConcept);
  }

  function applyControlsForState(state, concept) {
    stopTimer();
    const btnDrill = document.getElementById('btn-drill');
    const consolidateBtn = document.querySelector('#consolidate-controls button');
    if (btnDrill) btnDrill.textContent = '3. Drill (Recall)';
    if (consolidateBtn) {
      consolidateBtn.disabled = true;
      consolidateBtn.textContent = 'Consolidate (Coming Soon)';
      consolidateBtn.title = 'Consolidation is coming soon';
    }
    showControls(false, false, false, false, false);

    // Consolidation is intentionally unavailable for the MVP.
    const floatBtn = document.getElementById('btn-consolidate-float');
    if (floatBtn) {
      floatBtn.disabled = true;
      floatBtn.style.display = 'none';
      floatBtn.classList.remove('show');
    }

    if (state === 'instantiated') { showControls(false, false, false, false, false); setButtons(false, true); }
    else if (state === 'growing') { showControls(false, false, false, false, false); setButtons(false, true); }
    else if (state === 'fractured') {
      showControls(false, false, false, false, false); setButtons(false, true);
      if (btnDrill) btnDrill.textContent = '3. Drill (Repair)';
    }
    else if (state === 'hibernating') {
      let remaining = 24 * 60 * 60;
      if (concept && concept.timerStart) {
        const elapsed = Math.floor((Date.now() - concept.timerStart) / 1000);
        remaining = Math.max(0, 24 * 60 * 60 - elapsed);
      }
      if (remaining === 0) { completeConsolidation(); return; }
      timeLeft = remaining;
      showControls(false, false, false, true, true);
      startTimer();
    }
  }

  function showControls(primary, drill, consolidate, timer, dev) {
    if (primaryControls) primaryControls.style.display = primary ? 'flex' : 'none';
    if (drillControls) drillControls.style.display = drill ? 'flex' : 'none';
    if (consolidateControls) consolidateControls.style.display = consolidate ? 'flex' : 'none';
    if (timerDisplay) timerDisplay.style.display = timer ? 'block' : 'none';
    if (devBtn) devBtn.style.display = dev ? 'block' : 'none';
  }
  function setButtons(ex, dr) {
    const btnDr = document.getElementById('btn-drill');
    if (btnDr) btnDr.disabled = !dr;
  }

  function showEmptyState() {
    hideContentOverlay();
    stopTimer();
    renderHero(null);
    showControls(false, false, false, false, false);
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

    if (ext === 'pdf') {
      // Defer to pdf.js for robust client-side extraction natively in the browser
      if (typeof pdfjsLib === 'undefined') {
        onError('PDF engine failed to load. Please check your connection.'); return;
      }
      pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

      const fileReader = new FileReader();
      fileReader.onload = async (e) => {
        try {
          const pdfData = new Uint8Array(e.target.result);
          const pdf = await pdfjsLib.getDocument({ data: pdfData }).promise;

          let extractedText = '';
          for (let i = 1; i <= pdf.numPages; i++) {
            const page = await pdf.getPage(i);
            const textContent = await page.getTextContent();
            extractedText += textContent.items.map(item => item.str).join(' ') + '\n';
          }

          if (extractedText.trim().length < 50) {
            throw new Error("Scanned image or empty PDF.");
          }
          onSuccess(extractedText.trim(), file.name);
        } catch (err) {
          onError('Could not natively extract text from this PDF. Try pasting the content manually.', '[PDF Parsing Error]', file.name);
        }
      };
      fileReader.readAsArrayBuffer(file);
    } else {
      const reader = new FileReader();
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
    if (primaryControls) primaryControls.style.display = 'none';
    const conceptId = getActiveId();

    const overlay = document.createElement('div');
    overlay.id = 'content-overlay';

    if (primaryControls) {
      primaryControls.insertAdjacentElement('afterend', overlay);
    } else {
      document.querySelector('.hero-info').appendChild(overlay);
    }

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

  function drill() {
    const concept = getActiveConcept();
    if (!concept) return;
    
    // If we haven't mapped/extracted yet, trigger that first
    if (concept.state === 'instantiated') {
      extract();
      return;
    }

    if (!concept?.graphData) {
      showControls(false, true, false, false, false);
      return;
    }
    showMapView(concept);
    setMapMode('graph');
    const graphData = parseConceptGraphData(concept) || {};
    startDrill({
      id: 'core-thesis',
      type: 'core',
      label: 'Core Thesis',
      fullLabel: 'Core Thesis',
      detail: graphData?.metadata?.core_thesis || graphData?.metadata?.thesis || concept.contentPreview || 'Explain this core idea in your own words.',
    });
  }

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
    return;
  }

  // ── 15. Timer ──────────────────────────────────────────────
  let timerInterval = null;
  let timeLeft = 24 * 60 * 60;

  function startTimer() {
    stopTimer();
    updateTimerDisplay();
    timerInterval = setInterval(() => {
      timeLeft--;
      updateTimerDisplay();
      if (timeLeft <= 0) completeConsolidation();
    }, 1000);
  }
  function stopTimer() { clearInterval(timerInterval); timerInterval = null; }
  function updateTimerDisplay() {
    const h = Math.floor(timeLeft / 3600).toString().padStart(2, '0');
    const m = Math.floor((timeLeft % 3600) / 60).toString().padStart(2, '0');
    const s = (timeLeft % 60).toString().padStart(2, '0');
    timerDisplay.textContent = `${h}:${m}:${s}`;
  }
  function completeConsolidation() {
    stopTimer();
    updateActiveConcept({ timerStart: null });
    setState('actualized');
    playAnim('actualize', getActiveTileIdx());
  }
  function fastForward() { timeLeft = 3; }

  // ── 16. Map View UI ────────────────────────────────────────

  function showMapView(concept) {
    const mapView = document.getElementById('map-view');
    const mapContent = document.getElementById('map-content');
    const graphContent = document.getElementById('graph-content');
    const graphStage = document.getElementById('graph-stage');
    const graphNodeDetail = document.getElementById('graph-node-detail');
    const heroCard = document.querySelector('.hero-card');
    const libraryView = document.getElementById('library-view');

    if (!concept || !concept.graphData) return;

    let data;
    try {
      data = typeof concept.graphData === 'string' ? JSON.parse(concept.graphData) : concept.graphData;
    } catch (e) {
      console.error("Invalid JSON graphData", e);
      alert('This concept has malformed graph data from an earlier extraction. Re-extract it or delete and recreate the concept.');
      return;
    }

    if (!data.metadata) {
      data.metadata = {
        source_title: concept.name,
        core_thesis: "Raw visual structure. Deep Knowledge Map extraction pending or failed.",
        architecture_type: "prototype",
        difficulty: "unknown"
      };
    }

    const meta = data.metadata || {};
    const backbone = data.backbone || [];
    const clusters = data.clusters || [];
    const rels = data.relationships || { domain_mechanics: [], learning_prerequisites: [] };
    const fws = data.frameworks || [];

    let html = '<div class="map-zone zone-1">';
    html += '<div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; margin-right: 48px;">';
    html += `<div class="map-header-title" style="margin-bottom: 0;">${escHtml(meta.source_title || concept.name)}</div>`;

    if (concept.state === 'growing' || concept.state === 'fractured') {
      const btnText = concept.state === 'fractured' ? '✦ Repair (Drill)' : '✦ Start Drill';
      html += `<button class="btn-start-drill" onclick="App.startDrillFromMap()" title="Interactive Drill Session">${btnText}</button>`;
    }
    html += '</div>';

    html += `<div class="map-core-thesis">${escHtml(meta.core_thesis || '')}</div>`;

    html += '<div class="map-badges">';
    if (meta.architecture_type) html += `<div class="map-badge arch">${escHtml(meta.architecture_type.replace(/_/g, ' '))}</div>`;
    if (meta.difficulty) html += `<div class="map-badge diff">${escHtml(meta.difficulty)}</div>`;
    html += '</div>';

    if (meta.low_density) {
      html += '<div class="map-low-density">Lightweight map — source had limited content.</div>';
    }

    html += '</div>';

    if (backbone.length > 0) {
      html += '<div class="map-zone zone-2">';
      html += '<div class="map-section-title">Backbone Principles</div>';
      backbone.forEach(b => {
        html += `<div class="map-backbone-item">${escHtml(b.principle)}</div>`;
      });
      html += '</div>';
    }

    if (clusters.length > 0) {
      html += '<div class="map-zone zone-3">';
      html += '<div class="map-section-title">Clusters</div>';
      clusters.forEach((c, idx) => {
        const isFirst = idx === 0 ? 'expanded' : '';
        html += `
          <div class="map-cluster-card ${isFirst}" onclick="App.toggleCluster(this)">
            <div class="map-cluster-header">
              <span>${escHtml(c.label)}</span>
              <span class="map-cluster-icon">▾</span>
            </div>
            <div class="map-cluster-body" onclick="event.stopPropagation()">
              <div class="map-cluster-desc">${escHtml(c.description || '')}</div>
        `;
        const subnodes = c.subnodes || [];
        subnodes.forEach(sub => {
          const color = sub.drill_status ? 'var(--primary)' : '#c4c2d4';
          html += `
             <div class="map-subnode-row">
               <div class="map-subnode-indicator" style="background:${color};"></div>
               <div class="map-subnode-content">
                 <div class="map-subnode-label">${escHtml(sub.label)}</div>
                 <div class="map-subnode-mech">${escHtml(sub.mechanism || '')}</div>
               </div>
             </div>
           `;
        });
        html += `</div></div>`;
      });
      html += '</div>';
    }

    const domMechs = rels.domain_mechanics || [];
    const lrnPreqs = rels.learning_prerequisites || [];
    if (domMechs.length > 0 || lrnPreqs.length > 0) {
      html += '<div class="map-zone zone-4">';
      html += '<div class="map-section-title">Connections</div>';
      domMechs.forEach(rel => {
        const txt = rel.mechanism || rel.rationale || '';
        html += `<div class="map-cx-item"><strong>Domain:</strong> ${escHtml(txt)}</div>`;
      });
      lrnPreqs.forEach(rel => {
        const txt = rel.mechanism || rel.rationale || '';
        html += `<div class="map-cx-item"><strong>Prerequisite:</strong> ${escHtml(txt)}</div>`;
      });
      html += '</div>';
    }

    if (fws.length > 0) {
      html += '<div class="map-zone zone-5">';
      html += '<div class="map-section-title">Transferable Frameworks</div>';
      fws.forEach(fw => {
        html += `<div class="map-fw-card">
           <div class="map-fw-name">${escHtml(fw.name)}</div>
           <div class="map-fw-state">${escHtml(fw.statement)}</div>
         </div>`;
      });
      html += '</div>';
    }

    mapContent.innerHTML = html;

    if (currentGraphController) {
      currentGraphController.destroy();
      currentGraphController = null;
    }
    if (drillUi) drillUi.style.display = 'none';
    if (chatHistory) chatHistory.innerHTML = '';
    if (graphStage && graphNodeDetail) {
      currentGraphController = mountKnowledgeGraph({
        container: graphStage,
        detailEl: graphNodeDetail,
        rawData: data,
        onNodeSelect: (nodeData) => startDrill(nodeData),
        onContinue: () => cancelDrill(),
      });
    }

    clearSettingsPanel();
    setNavActive('nav-dashboard');
    if (libraryView) libraryView.classList.remove('visible');
    heroCard.style.display = 'none';
    mapView.classList.add('visible');
    setMapShellOpen(true);
    if (graphContent) graphContent.hidden = false;
    if (window.innerWidth < 900) closeDrawer();
    setMapMode('study');
    scheduleTutorialRefresh();
  }

  function hideMapView() {
    const mapView = document.getElementById('map-view');
    const heroCard = document.querySelector('.hero-card');
    if (drillState.active || drillState.pending || drillState.node) {
      cancelDrill();
    }
    if (currentGraphController) {
      currentGraphController.destroy();
      currentGraphController = null;
    }
    if (mapView) mapView.classList.remove('visible');
    setMapShellOpen(false);
    if (heroCard) heroCard.style.display = 'flex';
    setNavActive('nav-dashboard');
    scheduleTutorialRefresh();
  }

  function setMapMode(mode = 'study') {
    currentMapMode = mode === 'graph' ? 'graph' : 'study';
    const studyBtn = document.getElementById('map-mode-study');
    const graphBtn = document.getElementById('map-mode-graph');
    const mapContent = document.getElementById('map-content');
    const graphContent = document.getElementById('graph-content');

    if (studyBtn) studyBtn.classList.toggle('active', currentMapMode === 'study');
    if (graphBtn) graphBtn.classList.toggle('active', currentMapMode === 'graph');
    if (studyBtn) studyBtn.setAttribute('aria-pressed', String(currentMapMode === 'study'));
    if (graphBtn) graphBtn.setAttribute('aria-pressed', String(currentMapMode === 'graph'));
    if (mapContent) mapContent.hidden = currentMapMode !== 'study';
    if (graphContent) graphContent.hidden = currentMapMode !== 'graph';

    if (currentMapMode === 'graph' && currentGraphController) {
      requestAnimationFrame(() => currentGraphController?.resize());
    }
    scheduleTutorialRefresh();
  }

  function bindMapModeControls() {
    const modeButtons = document.querySelectorAll('[data-map-mode]');
    modeButtons.forEach((button) => {
      if (button.dataset.boundMapMode === 'true') return;
      button.dataset.boundMapMode = 'true';
      button.addEventListener('click', () => {
        setMapMode(button.dataset.mapMode);
      });
    });
  }

  function setNavActive(id) {
    currentPrimaryNav = id;
    ['nav-dashboard', 'nav-library'].forEach((navId) => {
      const el = document.getElementById(navId);
      if (el) el.classList.toggle('active', navId === currentPrimaryNav);
    });
  }

  function showDashboard() {
    setNavActive('nav-dashboard');
    const libraryView = document.getElementById('library-view');
    const mapView = document.getElementById('map-view');
    const heroCard = document.querySelector('.hero-card');

    clearSettingsPanel();
    if (libraryView) libraryView.classList.remove('visible');
    if (mapView) mapView.classList.remove('visible');
    setMapShellOpen(false);
    if (currentGraphController) {
      currentGraphController.destroy();
      currentGraphController = null;
    }
    if (heroCard) heroCard.style.display = 'flex';
    if (window.innerWidth < 900) closeDrawer();
    scheduleTutorialRefresh();
  }

  const STARTER_MAPS = [
    { file: 'thermostat_control.json', name: 'Thermostat Control Loop', desc: 'Simple feedback control with easy causal drill paths' },
    { file: 'espresso_physics.json', name: 'Physics of Espresso Extraction', desc: 'Grind size, channeling, and thermodynamics' },
    { file: 'mrna_vaccine.json', name: 'mRNA Vaccine Mechanism', desc: 'Lipid nanoparticles and ribosomal translation' },
    { file: 'options_trading.json', name: 'Options Trading Fundamentals', desc: 'Leveraged asymmetry and Theta decay' },
    { file: 'learnops_architecture.json', name: 'LearnOps Architecture', desc: 'The Generation Effect and Socratic Graphs' },
    { file: 'sourdough_science.json', name: 'Science of Sourdough Baking', desc: 'Symbiotic fermentation, rheology, and oven spring' }
  ];

  async function importStarterMap(filename, conceptName) {
    try {
      const response = await fetch(`/data/library/${filename}`);
      if (!response.ok) throw new Error('Network response was not ok');
      const data = await response.json();

      const newConcept = {
        id: generateId(),
        name: conceptName,
        createdAt: new Date().toISOString(),
        state: 'growing',
        graphData: JSON.stringify(data)
      };

      const concepts = loadConcepts();
      concepts.push(newConcept);
      saveConcepts(concepts);

      renderGrid(concepts);
      renderConceptList(concepts);
      selectConcept(newConcept.id);
      hideLibrary();

      showMapView(newConcept);
      setMapMode('graph');
    } catch (error) {
      console.error('Error loading starter map:', error);
      alert('Failed to load the starter map.');
    }
  }

  function getLibraryConceptMeta(concept) {
    let graph = null;
    try {
      graph = typeof concept.graphData === 'string' ? JSON.parse(concept.graphData) : concept.graphData;
    } catch {
      graph = null;
    }

    const metadata = graph?.metadata || {};
    const clusters = Array.isArray(graph?.clusters) ? graph.clusters : [];
    const subnodeCount = clusters.reduce((total, cluster) => total + ((cluster.subnodes || []).length), 0);
    const thesis = metadata.core_thesis || concept.contentPreview || 'No summary available yet.';
    const sourceLabel = concept.contentFilename
      ? `Source: ${concept.contentFilename}`
      : concept.contentType
        ? `Source: ${concept.contentType.toUpperCase()}`
        : (metadata.source_title ? `Map: ${metadata.source_title}` : 'Starter concept');

    return {
      thesis: thesis.length > 180 ? `${thesis.slice(0, 177).trimEnd()}...` : thesis,
      architecture: metadata.architecture_type ? metadata.architecture_type.replace(/_/g, ' ') : null,
      difficulty: metadata.difficulty || null,
      clusterCount: clusters.length,
      subnodeCount,
      sourceLabel,
    };
  }

  function showLibrary() {
    setNavActive('nav-library');
    const libraryView = document.getElementById('library-view');
    const mapView = document.getElementById('map-view');
    const heroCard = document.querySelector('.hero-card');
    const content = document.getElementById('library-content');

    clearSettingsPanel();
    if (mapView) mapView.classList.remove('visible');
    setMapShellOpen(false);
    if (currentGraphController) {
      currentGraphController.destroy();
      currentGraphController = null;
    }
    const concepts = loadConcepts().filter(c => c.graphData);

    let html = `
      <div class="library-kicker">Library</div>

      <div class="library-section">
        <h3 class="library-section-title">Starter Shelf</h3>
        <p class="library-section-copy">Preloaded concepts you can drop into the vault instantly.</p>
        <div class="library-starter-grid">
          ${STARTER_MAPS.map(s => `
            <div class="library-card-starter" onclick="App.importStarterMap('${s.file}', '${s.name}')">
              <div class="library-card-kicker">Starter</div>
              <div class="starter-card-title">${escHtml(s.name)}</div>
              <div class="starter-card-desc">${escHtml(s.desc)}</div>
              <div class="library-card-cta">Add to vault</div>
            </div>
          `).join('')}
        </div>
      </div>
      
      <div class="library-section" style="margin-top: 40px;">
        <h3 class="library-section-title">Your Vault</h3>
        <p class="library-section-copy">Mapped concepts ready to reopen and drill.</p>
    `;

    if (concepts.length === 0) {
      html += '<p class="library-empty" style="margin-top:10px;">No mapped concepts yet. Add a concept on the Dashboard or pull in a Starter Map to begin.</p>';
    } else {
      html += `<div class="library-vault-grid">` + concepts.map(c => {
        const meta = getLibraryConceptMeta(c);
        return `
          <div class="library-card library-card-vault" style="cursor:pointer;" onclick="App.selectConcept('${c.id}'); App.hideLibrary();">
            <div class="library-card-header">
              <div>
                <div class="library-card-kicker">${escHtml(meta.sourceLabel)}</div>
                <span class="library-card-name">${escHtml(c.name)}</span>
              </div>
              <span class="library-card-state">${escHtml(c.state)}</span>
            </div>
            <p class="library-card-summary">${escHtml(meta.thesis)}</p>
            <div class="library-card-meta">
              ${meta.architecture ? `<span class="library-card-pill">${escHtml(meta.architecture)}</span>` : ''}
              ${meta.difficulty ? `<span class="library-card-pill">${escHtml(meta.difficulty)}</span>` : ''}
              <span class="library-card-pill">${escHtml(`${meta.clusterCount} clusters`)}</span>
              <span class="library-card-pill">${escHtml(`${meta.subnodeCount} drill nodes`)}</span>
            </div>
            <div class="library-card-cta">Open concept</div>
          </div>`;
      }).join('') + `</div>`;
    }

    html += `</div>`;
    content.innerHTML = html;

    if (heroCard) heroCard.style.display = 'none';
    libraryView.classList.add('visible');
    if (window.innerWidth < 900) closeDrawer();
    scheduleTutorialRefresh();
  }

  function hideLibrary() {
    const libraryView = document.getElementById('library-view');
    const heroCard = document.querySelector('.hero-card');
    if (libraryView) libraryView.classList.remove('visible');
    if (heroCard) heroCard.style.display = 'flex';
    scheduleTutorialRefresh();
  }

  function toggleCluster(el) {
    const isExpanded = el.classList.contains('expanded');
    const parent = el.parentElement;
    parent.querySelectorAll('.map-cluster-card').forEach(c => c.classList.remove('expanded'));
    if (!isExpanded) {
      el.classList.add('expanded');
    }
  }

  // ── 17. Init + restore ─────────────────────────────────────





  // Migrate legacy single-concept storage
  const legacyState = localStorage.getItem('learnops-state');
  if (legacyState && STATES[legacyState]) {
    const c = {
      id: generateId(), name: 'My First Concept', state: legacyState,
      createdAt: Date.now(),
      timerStart: legacyState === 'hibernating'
        ? parseInt(localStorage.getItem('learnops-timer-start') || '0', 10) || null : null,
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
    { left: 140, top: 37 },  // tile-0 (back center)
    { left: 70, top: 77 },  // tile-1 (mid left)
    { left: 210, top: 77 },  // tile-2 (mid right)
    { left: 140, top: 117 },  // tile-3 (front center)
  ];

  function showTileTooltip(idx) {
    const c = loadConcepts()[idx];
    if (!c) return;
    const pos = TILE_TOOLTIP_POS[idx];
    tooltipEl.style.left = pos.left + 'px';
    tooltipEl.style.top = pos.top + 'px';
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
  themePreference = getStoredThemePreference();
  applyThemePreference(themePreference, { persist: false });
  bindMapModeControls();
  renderGrid();
  renderConceptList();

  // Restore selected concept
  const concepts = loadConcepts();
  const toLoad = concepts.find(c => c.id === getActiveId()) || concepts[0] || null;

  if (!toLoad) {
    showEmptyState();
  } else {
    setActiveId(toLoad.id);
    renderHero(toLoad);
    applyControlsForState(toLoad.state, toLoad);
    renderGrid(); // re-render to apply .selected class
  }

  let drillState = {
    active: false,
    messages: [],
    node: null,
    pending: false,
    probeCount: 0,
    nodesDrilled: 0,
    attemptTurnCount: 0,
    helpTurnCount: 0,
    sessionStartIso: null,
    sessionToken: 0,
  };

  function parseConceptGraphData(concept) {
    if (!concept?.graphData) return null;
    if (typeof concept.graphData === 'string') {
      return JSON.parse(concept.graphData);
    }
    return concept.graphData;
  }

  function persistActiveConceptGraphData(graphData) {
    const concepts = loadConcepts();
    const activeId = getActiveId();
    const conceptIdx = concepts.findIndex((concept) => concept.id === activeId);
    if (conceptIdx === -1) return null;

    concepts[conceptIdx].graphData = JSON.stringify(graphData);
    saveConcepts(concepts);
    return concepts[conceptIdx];
  }

  function patchActiveConceptDrillOutcome(result) {
    if (result?.routing !== 'NEXT' || !result?.node_id) {
      console.log(
        `[drill->graph] no mutation node=${result?.node_id ?? 'n/a'} classification=${result?.classification ?? 'null'} routing=${result?.routing ?? 'null'}`
      );
      console.log('[drill->graph] no graph mutation', {
        node_id: result?.node_id ?? null,
        classification: result?.classification ?? null,
        routing: result?.routing ?? null,
        reason: 'routing was not NEXT',
      });
      return null;
    }

    const concept = getActiveConcept();
    const graphData = parseConceptGraphData(concept);
    if (!graphData) return null;

    const drilledAt = new Date().toISOString();
    let patched = false;

    if (result.node_id === 'core-thesis') {
      graphData.metadata = graphData.metadata || {};
      graphData.metadata.drill_status = result.classification || graphData.metadata.drill_status || null;
      graphData.metadata.gap_type = result.classification && result.classification !== 'solid'
        ? result.classification
        : null;
      graphData.metadata.gap_description = result.classification && result.classification !== 'solid'
        ? (result.gap_description || null)
        : null;
      graphData.metadata.last_drilled = drilledAt;
      patched = true;
    }

    (graphData.backbone || []).forEach((item) => {
      if (item?.id !== result.node_id) return;

      if (result.classification === 'solid') {
        item.drill_status = 'solid';
        item.gap_type = null;
        item.gap_description = null;
      } else if (result.classification) {
        item.drill_status = result.classification;
        item.gap_type = result.classification;
        item.gap_description = result.gap_description || null;
      }

      item.last_drilled = drilledAt;
      patched = true;
    });

    (graphData.clusters || []).forEach((cluster) => {
      (cluster.subnodes || []).forEach((subnode) => {
        if (subnode?.id !== result.node_id) return;

        if (result.classification === 'solid') {
          subnode.drill_status = 'solid';
          subnode.gap_type = null;
          subnode.gap_description = null;
        } else if (result.classification) {
          subnode.drill_status = result.classification;
          subnode.gap_type = result.classification;
          subnode.gap_description = result.gap_description || null;
        } else {
          // Defensive no-op: NEXT without a classification should still record that the node was visited,
          // but should not overwrite the prior epistemic state until the backend provides a real judgment.
        }

        subnode.last_drilled = drilledAt;
        patched = true;
      });
    });

    if (!patched) return null;

    const updatedConcept = persistActiveConceptGraphData(graphData);
    console.log(
      `[drill->graph] patched node=${result.node_id} classification=${result.classification ?? 'null'} routing=${result.routing ?? 'null'}`
    );
    console.log('[drill->graph] patched node state', {
      node_id: result.node_id,
      classification: result.classification ?? null,
      routing: result.routing ?? null,
      gap_description: result.gap_description ?? null,
    });
    currentGraphController?.syncFromKnowledgeMap?.(graphData, activeDrillNode);
    return updatedConcept;
  }

  function extractSystemAction(rawText) {
    if (!rawText) return { visibleText: '', action: null };

    const match = rawText.match(/\[SYSTEM_ACTION:\s*(\{[\s\S]*?\})\s*\]\s*$/);
    if (!match) {
      return { visibleText: rawText.trim(), action: null };
    }

    let action = null;
    try {
      action = JSON.parse(match[1]);
    } catch (err) {
      console.warn('Failed to parse SYSTEM_ACTION payload', err);
    }

    const visibleText = rawText.replace(match[0], '').trim();
    return { visibleText, action };
  }

  function handleSystemAction(action) {
    if (!action) return;

    if (action.action === 'UPDATE_NODE_STATE' && action.id && action.newState) {
      currentGraphController?.updateNodeState?.(action.id, action.newState);

      if (action.newState === 'solidified' && activeDrillNode === action.id) {
        currentGraphController?.clearActiveDrillNode?.();
        activeDrillNode = null;
      }
    }
  }

  function handleDrillAssistantMessage(rawText) {
    const { visibleText, action } = extractSystemAction(rawText);

    if (visibleText) {
      appendBubble('ai', visibleText);
    }

    handleSystemAction(action);
  }

  async function requestDrillTurn(userText) {
    const concept = getActiveConcept();
    if (!concept || !drillState.node) return;
    const sessionToken = drillState.sessionToken;

    drillState.pending = true;
    if (chatInput) chatInput.disabled = true;
    showTypingIndicator();

    const outboundMessages = [...drillState.messages];
    if (userText) {
      outboundMessages.push({ role: 'user', content: userText });
    }

    const sessionPhase = !drillState.messages.length && !userText ? 'init' : 'turn';

    const knowledgeMap = typeof concept.graphData === 'string'
      ? JSON.parse(concept.graphData)
      : concept.graphData;

    const apiKey = localStorage.getItem('gemini_key') || undefined;
    try {
      const response = await fetch('/api/drill', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          concept_id: concept.id,
          node_id: drillState.node.id,
          node_label: drillState.node.fullLabel || drillState.node.label || concept.name,
          node_mechanism: drillState.node.detail || '',
          knowledge_map: knowledgeMap,
          messages: outboundMessages,
          session_phase: sessionPhase,
          probe_count: drillState.probeCount,
          nodes_drilled: drillState.nodesDrilled,
          attempt_turn_count: drillState.attemptTurnCount,
          help_turn_count: drillState.helpTurnCount,
          session_start_iso: drillState.sessionStartIso,
          api_key: apiKey,
        }),
      });

      if (!response.ok) {
        const err = await response.text().catch(() => '');
        throw new Error(`Drill request failed: ${response.status}: ${err}`);
      }

      const data = await response.json();
      console.log(
        `[drill] answer_mode=${data?.answer_mode ?? 'null'} classification=${data?.classification ?? 'null'} routing=${data?.routing ?? 'null'} terminated=${Boolean(data?.session_terminated)}`
      );
      console.log('[drill] response', data);
      hideTypingIndicator();

      if (sessionToken !== drillState.sessionToken || !drillState.node) {
        return;
      }

      patchActiveConceptDrillOutcome(data);
      drillState.messages = outboundMessages;
      drillState.probeCount = data.probe_count ?? drillState.probeCount;
      drillState.nodesDrilled = data.nodes_drilled ?? drillState.nodesDrilled;
      drillState.attemptTurnCount = data.attempt_turn_count ?? drillState.attemptTurnCount;
      drillState.helpTurnCount = data.help_turn_count ?? drillState.helpTurnCount;
      handleDrillAssistantMessage(data.agent_response || '');
      if (data.agent_response?.trim()) {
        drillState.messages.push({ role: 'assistant', content: data.agent_response.trim() });
      }
      drillState.pending = false;
      const completedNodeTurn = data.routing === 'NEXT'
        || (data.routing === 'SESSION_COMPLETE' && !!data.classification);
      if (chatInput) {
        chatInput.disabled = completedNodeTurn || !!data.session_terminated;
        if (!completedNodeTurn && !data.session_terminated) {
          chatInput.focus();
        }
      }
      if (completedNodeTurn) {
        currentGraphController?.setInteractionMode?.('post-drill', activeDrillNode);
      } else {
        currentGraphController?.setInteractionMode?.('drill-active', activeDrillNode);
      }
    } catch (err) {
      hideTypingIndicator();
      if (sessionToken !== drillState.sessionToken) {
        return;
      }
      drillState.pending = false;
      throw err;
    }
  }

  function startDrill(nodeContext = null) {
    const concept = getActiveConcept();
    if (!concept) return;

    if (!nodeContext) {
      const km = typeof concept.graphData === 'string' ? JSON.parse(concept.graphData || '{}') : (concept.graphData || {});
      nodeContext = { 
        id: 'core-thesis',
        type: 'core',
        fullLabel: 'Core Thesis',
        detail: km?.metadata?.core_thesis || km?.metadata?.thesis || concept.contentPreview || 'Explain this core idea in your own words.',
      };
    }

    drillState.active = true;
    drillState.messages = [];
    drillState.node = nodeContext;
    drillState.pending = false;
    drillState.probeCount = 0;
    drillState.nodesDrilled = 0;
    drillState.attemptTurnCount = 0;
    drillState.helpTurnCount = 0;
    drillState.sessionStartIso = new Date().toISOString();
    drillState.sessionToken += 1;
    activeDrillNode = nodeContext?.id || null;

    if (drillUi) drillUi.style.display = 'flex';
    if (chatHistory) chatHistory.innerHTML = '';
    if (chatInput) {
      chatInput.value = '';
      chatInput.disabled = true;
    }
    if (drillTitle) {
      const label = nodeContext?.fullLabel || nodeContext?.label || concept.name;
      drillTitle.textContent = `Drilling: ${label}`;
    }
    currentGraphController?.setActiveDrillNode?.(activeDrillNode);
    currentGraphController?.setInteractionMode?.('drill-active', activeDrillNode);
    setMapMode('graph');

    requestDrillTurn().catch((err) => {
      console.error(err);
      hideTypingIndicator();
      appendBubble('ai', 'The drill service failed to respond. Check the backend or API key and try again.');
      drillState.pending = false;
      if (chatInput) chatInput.disabled = false;
      currentGraphController?.setInteractionMode?.('inspect');
    });
  }

  function cancelDrill() {
    drillState.sessionToken += 1;
    drillState.active = false;
    drillState.messages = [];
    drillState.node = null;
    drillState.pending = false;
    drillState.probeCount = 0;
    drillState.nodesDrilled = 0;
    drillState.attemptTurnCount = 0;
    drillState.helpTurnCount = 0;
    drillState.sessionStartIso = null;
    if (drillUi) drillUi.style.display = 'none';
    activeDrillNode = null;
    if (chatHistory) chatHistory.innerHTML = '';
    if (chatInput) {
      chatInput.value = '';
      chatInput.disabled = true;
    }
    currentGraphController?.clearActiveDrillNode?.();
    currentGraphController?.setInteractionMode?.('inspect');
    scheduleTutorialRefresh();
  }

  const tutorialDirectives = [
    {
      id: 'quick-guide',
      sel: '#nav-guide',
      title: 'Use Quick Guide Beacons',
      text: 'Turn this on any time to see lightweight tips around the current screen. Hover or focus the glowing dots to read them.',
      when: () => true,
    },
    {
      id: 'library',
      sel: '#nav-library',
      title: 'Open The Library',
      text: 'Use starter maps for an instant demo, or reopen concepts you have already extracted.',
      when: () => true,
    },
    {
      id: 'analytics',
      sel: '#nav-analytics',
      title: 'Read Your Analytics',
      text: 'Analytics shows truthful learning state: what is solid, what is still in progress, and what you should revisit next.',
      when: () => true,
    },
    {
      id: 'new-concept',
      sel: '#add-trigger',
      title: 'Create A Concept',
      text: 'Start here with pasted text, notes, or a PDF. This is the fastest path into extraction.',
      when: () => !document.getElementById('map-view')?.classList.contains('visible')
        && !document.getElementById('library-view')?.classList.contains('visible'),
    },
    {
      id: 'concept-inputs',
      sel: '.creation-form .overlay-tabs',
      title: 'Choose Your Input',
      text: 'Use Text for pasted notes, URL for article pages or YouTube links with transcripts, and File for .txt, .md, or .pdf uploads up to 2MB.',
      when: () => !!document.querySelector('.creation-form')
        && !document.getElementById('map-view')?.classList.contains('visible')
        && !document.getElementById('library-view')?.classList.contains('visible'),
    },
    {
      id: 'drill',
      sel: '.tile-group:not(.empty)',
      title: 'Enter Concept Crystal',
      text: 'Click any active crystal on your board to enter its Socratic Map and start a recall drill.',
      when: () => !document.getElementById('map-view')?.classList.contains('visible')
        && !!document.querySelector('.tile-group:not(.empty)'),
    },
    {
      id: 'graph-view',
      sel: '#map-mode-graph',
      title: 'Switch To Graph View',
      text: 'Use Graph View to see what is locked, in progress, and solidified across the map.',
      when: () => document.getElementById('map-view')?.classList.contains('visible'),
    },
    {
      id: 'graph-stage',
      sel: '#graph-stage',
      title: 'Inspect The Knowledge Graph',
      text: 'Hover and click visible nodes to inspect them. A drill always targets one node at a time.',
      when: () => {
        const graphContent = document.getElementById('graph-content');
        return !!graphContent && !graphContent.hidden;
      },
    },
    {
      id: 'chat-input',
      sel: '#chat-input',
      title: 'Answer From Memory',
      text: 'Type your explanation in your own words. The graph updates only for the node you are drilling.',
      when: () => drillUi?.style.display === 'flex',
    },
  ];

  const tutorialLayerEl = document.createElement('div');
  tutorialLayerEl.className = 'tutorial-layer';
  document.body.appendChild(tutorialLayerEl);

  const tourTooltipEl = document.createElement('div');
  tourTooltipEl.className = 'tour-tooltip';
  tourTooltipEl.setAttribute('role', 'dialog');
  tourTooltipEl.setAttribute('aria-live', 'polite');
  document.body.appendChild(tourTooltipEl);

  function isTutorialTargetVisible(target) {
    if (!target || target.offsetParent === null) return false;
    const rect = target.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return false;
    if (rect.right < 0 || rect.left > window.innerWidth || rect.bottom < 0 || rect.top > window.innerHeight) return false;
    return true;
  }

  function cleanupTutorialHighlights() {
    document.querySelectorAll('.tutorial-target').forEach((el) => el.classList.remove('tutorial-target'));
    activeTutorialTarget = null;
  }

  function hideTooltip() {
    cleanupTutorialHighlights();
    tourTooltipEl.classList.remove('visible');
    tourTooltipEl.innerHTML = '';
  }

  function positionTooltip(rect) {
    const gap = 14;
    const maxWidth = 280;
    let left = rect.right + gap + window.scrollX;
    let top = rect.top + window.scrollY;

    tourTooltipEl.style.left = `${left}px`;
    tourTooltipEl.style.top = `${top}px`;

    const tooltipRect = tourTooltipEl.getBoundingClientRect();
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    if (tooltipRect.right > viewportWidth - 16) {
      left = rect.left + window.scrollX - Math.min(maxWidth, tooltipRect.width) - gap;
    }
    if (left < 16 + window.scrollX) {
      left = Math.max(16 + window.scrollX, rect.left + window.scrollX);
      top = rect.bottom + gap + window.scrollY;
    }
    if (top + tooltipRect.height > viewportHeight + window.scrollY - 16) {
      top = Math.max(16 + window.scrollY, rect.bottom + window.scrollY - tooltipRect.height);
    }

    tourTooltipEl.style.left = `${left}px`;
    tourTooltipEl.style.top = `${top}px`;
  }

  function showTooltipForDirective(target, directive) {
    if (!tutorialMode || !target || !directive) return;

    cleanupTutorialHighlights();
    activeTutorialTarget = target;
    target.classList.add('tutorial-target');

    tourTooltipEl.innerHTML = `
      <div class="tour-tooltip-kicker">Quick Guide</div>
      <div class="tour-tooltip-title">${escHtml(directive.title)}</div>
      <div class="tour-tooltip-body">${escHtml(directive.text)}</div>
    `;
    positionTooltip(target.getBoundingClientRect());
    tourTooltipEl.classList.add('visible');
  }

  function renderBeacons() {
    tutorialLayerEl.innerHTML = '';
    if (!tutorialMode) return;

    tutorialDirectives.forEach((directive, index) => {
      if (directive.when && !directive.when()) return;
      const target = document.querySelector(directive.sel);
      if (!isTutorialTargetVisible(target)) return;

      const rect = target.getBoundingClientRect();
      const beacon = document.createElement('button');
      beacon.type = 'button';
      beacon.className = 'beacon';
      beacon.setAttribute('aria-label', directive.title);
      beacon.dataset.beaconId = directive.id || `beacon-${index}`;
      beacon.style.left = `${rect.right + window.scrollX - 8}px`;
      beacon.style.top = `${rect.top + window.scrollY - 6}px`;

      beacon.addEventListener('mouseenter', () => showTooltipForDirective(target, directive));
      beacon.addEventListener('focus', () => showTooltipForDirective(target, directive));
      beacon.addEventListener('mouseleave', hideTooltip);
      beacon.addEventListener('blur', hideTooltip);

      tutorialLayerEl.appendChild(beacon);
    });

    if (activeTutorialTarget && activeTutorialTarget.classList.contains('tutorial-target')) {
      const activeDirective = tutorialDirectives.find((directive) => document.querySelector(directive.sel) === activeTutorialTarget);
      if (!isTutorialTargetVisible(activeTutorialTarget) || !activeDirective) {
        hideTooltip();
      } else {
        positionTooltip(activeTutorialTarget.getBoundingClientRect());
      }
    }
  }

  function scheduleTutorialRefresh() {
    if (!tutorialMode) return;
    if (tutorialRefreshRaf) window.cancelAnimationFrame(tutorialRefreshRaf);
    tutorialRefreshRaf = window.requestAnimationFrame(() => {
      tutorialRefreshRaf = null;
      renderBeacons();
    });
  }

  window.addEventListener('resize', scheduleTutorialRefresh);
  window.addEventListener('scroll', scheduleTutorialRefresh, { passive: true });
  if (drawer) {
    drawer.addEventListener('transitionend', scheduleTutorialRefresh);
  }
  if (conceptListEl) {
    conceptListEl.addEventListener('scroll', scheduleTutorialRefresh, { passive: true });
  }
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && tutorialMode) {
      App.toggleTutorial();
    }
  });

  let typingIndicatorElement = null;

  function showTypingIndicator() {
    if (typingIndicatorElement || !chatHistory) return;
    typingIndicatorElement = document.createElement('div');
    typingIndicatorElement.className = 'chat-bubble ai typing';
    typingIndicatorElement.innerHTML = `
      <span class="typing-dot"></span>
      <span class="typing-dot"></span>
      <span class="typing-dot"></span>
    `;
    chatHistory.appendChild(typingIndicatorElement);
    chatHistory.scrollTop = chatHistory.scrollHeight;
  }

  function hideTypingIndicator() {
    if (typingIndicatorElement && typingIndicatorElement.parentNode) {
      typingIndicatorElement.parentNode.removeChild(typingIndicatorElement);
    }
    typingIndicatorElement = null;
  }

  function formatChatText(text) {
    if (!text) return '';
    let safeText = escHtml(text);
    safeText = safeText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    safeText = safeText.replace(/\*(.*?)\*/g, '<strong><em>$1</em></strong>');
    return safeText;
  }

  function appendBubble(role, text) {
    if (!chatHistory) return;
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${role}`;
    bubble.innerHTML = formatChatText(text);
    chatHistory.appendChild(bubble);
    setTimeout(() => {
      chatHistory.scrollTop = chatHistory.scrollHeight;
    }, 50);
  }

  if (chatInput) {
    chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        const text = chatInput.value.trim();
        if (!text || drillState.pending) return;

        appendBubble('user', text);
        chatInput.value = '';
        chatInput.disabled = true;
        requestDrillTurn(text).catch((err) => {
          console.error(err);
          hideTypingIndicator();
          appendBubble('ai', 'The drill service failed to respond. Check the backend or API key and try again.');
          drillState.pending = false;
          if (chatInput) chatInput.disabled = false;
        });
      }
    });
  }

  return {
    toggleDrawer, openDrawer, closeDrawer,
    cancelDrill, startDrill, startDrillFromMap: () => {
      const concept = getActiveConcept();
      if (!concept?.graphData) return;
      showMapView(concept);
      setMapMode('graph');
      const graphData = parseConceptGraphData(concept) || {};
      startDrill({
        id: 'core-thesis',
        type: 'core',
        label: 'Core Thesis',
        fullLabel: 'Core Thesis',
        detail: graphData?.metadata?.core_thesis || graphData?.metadata?.thesis || concept.contentPreview || 'Explain this core idea in your own words.',
      });
    },

    toggleTutorial: () => {
      tutorialMode = !tutorialMode;
      const guideBtn = document.getElementById('nav-guide');
      if (guideBtn) {
        if (tutorialMode) guideBtn.dataset.engaged = 'true';
        else delete guideBtn.dataset.engaged;
        guideBtn.setAttribute('aria-pressed', String(tutorialMode));
      }
      if (window.innerWidth < 900) closeDrawer();

      if (!tutorialMode) {
        if (tutorialRefreshRaf) {
          window.cancelAnimationFrame(tutorialRefreshRaf);
          tutorialRefreshRaf = null;
        }
        tutorialLayerEl.innerHTML = '';
        hideTooltip();
        return;
      }
      scheduleTutorialRefresh();
    },

    selectTile, selectConcept: (id) => { selectConcept(id); closeDrawer(); },
    deleteConcept,
    startAddConcept,
    renderAddTrigger,
    extract, drill, drillFail, drillPass, consolidate,
    fastForward,
    hideMapView, setMapMode, toggleCluster,
    showLibrary, hideLibrary, showDashboard,
    importStarterMap,
    toggleTheme, runHeroAction
  };

})();
window.App = App;

function startSettings() {
  const triggerArea = document.getElementById('add-trigger-area');
  const settingsBtn = document.getElementById('nav-settings');
  const existingPanel = triggerArea?.querySelector('.settings-panel');

  if (existingPanel) {
    if (settingsBtn) delete settingsBtn.dataset.engaged;
    App.closeDrawer();
    App.renderAddTrigger();
    return;
  }

  if (settingsBtn) settingsBtn.dataset.engaged = 'true';
  App.openDrawer();
  triggerArea.style.overflowY = 'auto';
  triggerArea.innerHTML = `
    <div class="settings-panel">
      <div class="settings-header">
        <div class="settings-header-text">
          <h3>Settings</h3>
          <p class="settings-subtext">Configure your pipeline integrations.</p>
        </div>
        <button class="settings-close-btn" onclick="delete document.getElementById('nav-settings')?.dataset.engaged; App.closeDrawer(); App.renderAddTrigger();" aria-label="Close settings">×</button>
      </div>

      <div class="settings-box">
        <div class="settings-section-header">
          <h4>Backend</h4>
          <span class="settings-dot" id="settings-dot"></span>
        </div>
        <p class="settings-subtext">Start the server with <code>uvicorn main:app --reload</code>.</p>
        <div class="settings-actions">
          <button id="settings-test-btn" class="settings-test">Test Connection</button>
        </div>
        <div id="settings-status" class="settings-status"></div>
      </div>

      <div class="settings-box" id="key-box" style="margin-top:20px; display:none;">
        <div class="settings-section-header">
          <h4>Gemini API Key</h4>
        </div>
        <p class="settings-subtext">No server key detected. Enter your own to enable extraction.</p>
        <div class="settings-input-wrap">
          <input type="password" id="settings-key-input" class="settings-input" placeholder="Paste Gemini API key" autocomplete="off" spellcheck="false">
        </div>
        <div class="settings-actions">
          <button id="settings-key-save" class="settings-save">Save Key</button>
        </div>
        <div id="settings-key-status" class="settings-status"></div>
      </div>

    </div>
  `;

  App.openDrawer();

  const dot = triggerArea.querySelector('#settings-dot');
  const testBtn = triggerArea.querySelector('#settings-test-btn');
  const statusBox = triggerArea.querySelector('#settings-status');
  const keyBox = triggerArea.querySelector('#key-box');
  const keyInput = triggerArea.querySelector('#settings-key-input');
  const keySave = triggerArea.querySelector('#settings-key-save');
  const keyStatus = triggerArea.querySelector('#settings-key-status');

  // Pre-fill saved key if present
  const saved = localStorage.getItem('gemini_key');
  if (saved) keyInput.value = saved;

  keySave.addEventListener('click', () => {
    const val = keyInput.value.trim();
    if (!val) return;
    localStorage.setItem('gemini_key', val);
    keyStatus.textContent = 'Key saved.';
    keyStatus.style.color = 'var(--success)';
  });

  // Test connection and reveal key input only if server has no key of its own
  async function testConnection() {
    testBtn.disabled = true;
    testBtn.textContent = 'Testing…';
    try {
      const res = await fetch('/api/health');
      if (!res.ok) throw new Error(`Status ${res.status}`);
      const data = await res.json();
      dot.classList.add('connected');
      dot.classList.remove('error');
      if (data.server_key_configured) {
        statusBox.textContent = 'Backend connected. Server key active.';
        keyBox.style.display = 'none';
      } else {
        statusBox.textContent = 'Backend connected. No server key — use your own below.';
        keyBox.style.display = 'block';
      }
      statusBox.style.color = 'var(--success)';
    } catch {
      dot.classList.add('error');
      dot.classList.remove('connected');
      statusBox.textContent = 'Cannot reach backend. Is uvicorn running?';
      statusBox.style.color = 'var(--danger)';
    } finally {
      testBtn.disabled = false;
      testBtn.textContent = 'Test Connection';
    }
  }

  testBtn.addEventListener('click', testConnection);
}

window.startSettings = startSettings;
