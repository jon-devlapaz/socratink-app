import { Bus } from './bus.js';
import { generateKnowledgeMap } from './ai_service.js';
import {
  getHealth,
  extractUrl,
  runRepairReps,
  runDrillTurn,
  loadLibraryConcept,
} from './api-client.js?v=1';
import { escHtml, mountKnowledgeGraph } from './graph-view.js?v=9';
import {
  bootstrapAuthUi,
  buildLoginHref,
  fetchAuthSession,
  isGuestSession,
  isIdentifiedUserSession,
  logout,
  redirectToLogin,
} from './auth.js?v=3';
import { maybeShowFirstRunWelcome } from './welcome.js?v=6';
import {
  STATES, generateId, loadConcepts, saveConcepts, normalizeGraphData,
  getActiveId, setActiveId, getActiveConcept,
  getActiveTileIdx, updateActiveConcept, contentStore
} from './store.js';

import {
  card, titleEl, descEl, primaryControls, drillControls,
  heroStateChipEl, heroPrimaryActionEl, consolidateControls, timerDisplay, devBtn, drawer, drawerToggle, conceptListEl,
  addTriggerArea, heroInfo, drillUi, chatHistory, chatInput, drillTitle,
  TILE_IDS, tileEls
} from './dom.js';

const App = (() => {
  const THEME_STORAGE_KEY = 'learnops-theme';
  const PHASE_B_SESSION_KEY_PREFIX = 'learnops-phase-b-session';
  const PHASE_B_RESUME_KEY = 'learnops-phase-b-resume';
  const REPAIR_REPS_STORE_KEY = 'learnops_repair_reps_v1';
  const FIRST_COLD_ATTEMPT_CREED_KEY = 'socratink:firstColdAttemptCreedSeen:v1';
  let currentGraphController = null;
  let currentMapMode = 'study';
  let activeDrillNode = null;
  let repairRepsState = null;
  let themePreference = 'light';
  let currentPrimaryNav = 'nav-dashboard';
  let sessionState = getDefaultPhaseBSessionState();
  let drillSessionTimeLimitSeconds = null;
  let firstColdAttemptCreedShownThisSession = false;

  function applyRuntimeConfig(config = {}) {
    const limitSeconds = Number(config.drill_session_time_limit_seconds);
    drillSessionTimeLimitSeconds = Number.isFinite(limitSeconds) && limitSeconds > 0
      ? limitSeconds
      : null;
  }

  async function refreshRuntimeConfig() {
    try {
      applyRuntimeConfig(await getHealth());
    } catch (err) {
      console.warn('Runtime config unavailable.', err);
    }
  }

  function hasDrillSessionTimeLimitElapsed(startedAt) {
    if (!drillSessionTimeLimitSeconds || !startedAt) return false;
    const startedAtMs = Date.parse(startedAt);
    if (Number.isNaN(startedAtMs)) return false;
    return Date.now() - startedAtMs > drillSessionTimeLimitSeconds * 1000;
  }

  function getPhaseBSessionStorageKey(conceptId = getActiveId()) {
    return conceptId ? `${PHASE_B_SESSION_KEY_PREFIX}:${conceptId}` : PHASE_B_SESSION_KEY_PREFIX;
  }

  function getDefaultPhaseBSessionState() {
    return {
      startedAt: null,
      nodesDrilled: 0,
      visitedNodeIds: [],
      retriesByNode: {},
      events: [],
    };
  }

  function loadPhaseBSessionState(conceptId = getActiveId()) {
    try {
      const raw = sessionStorage.getItem(getPhaseBSessionStorageKey(conceptId));
      if (!raw) return getDefaultPhaseBSessionState();
      const parsed = JSON.parse(raw);
      const visitedNodeIds = Array.isArray(parsed?.visitedNodeIds)
        ? parsed.visitedNodeIds.filter((id) => typeof id === 'string' && id)
        : [];
      return {
        startedAt: parsed?.startedAt || null,
        nodesDrilled: visitedNodeIds.length || (Number.isFinite(Number(parsed?.nodesDrilled)) ? Number(parsed.nodesDrilled) : 0),
        visitedNodeIds,
        retriesByNode: parsed?.retriesByNode && typeof parsed.retriesByNode === 'object' ? parsed.retriesByNode : {},
        events: Array.isArray(parsed?.events) ? parsed.events : [],
      };
    } catch (err) {
      console.warn('Phase B session state unavailable.', err);
      return getDefaultPhaseBSessionState();
    }
  }

  function persistPhaseBSessionState(sessionState, conceptId = getActiveId()) {
    try {
      sessionStorage.setItem(getPhaseBSessionStorageKey(conceptId), JSON.stringify(sessionState));
    } catch (err) {
      console.warn('Unable to persist Phase B session state.', err);
    }
  }

  function loadPhaseBResumeState() {
    try {
      const raw = sessionStorage.getItem(PHASE_B_RESUME_KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      if (!parsed?.conceptId || !parsed?.nodeId || parsed?.mode !== 'study') return null;
      return parsed;
    } catch (err) {
      console.warn('Phase B resume state unavailable.', err);
      return null;
    }
  }

  function persistPhaseBResumeState(nextState = null) {
    try {
      if (!nextState) {
        sessionStorage.removeItem(PHASE_B_RESUME_KEY);
        return;
      }
      sessionStorage.setItem(PHASE_B_RESUME_KEY, JSON.stringify(nextState));
    } catch (err) {
      console.warn('Unable to persist Phase B resume state.', err);
    }
  }

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
    remountOpenKnowledgeGraphForTheme();
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

  function buildKnowledgeGraphMountConfig(rawData) {
    const graphStage = document.getElementById('graph-stage');
    const graphNodeDetail = document.getElementById('graph-node-detail');
    if (!graphStage || !graphNodeDetail || !rawData) return null;
    return {
      container: graphStage,
      detailEl: graphNodeDetail,
      rawData,
      onNodeSelect: (nodeData) => startDrill(nodeData),
      onContinue: () => cancelDrill(),
    };
  }

  function destroyKnowledgeGraphController() {
    if (!currentGraphController) return;
    currentGraphController.destroy();
    currentGraphController = null;
  }

  function mountKnowledgeGraphController(rawData) {
    const config = buildKnowledgeGraphMountConfig(rawData);
    if (!config) return null;
    currentGraphController = mountKnowledgeGraph(config);
    return currentGraphController;
  }

  function captureKnowledgeGraphViewState() {
    if (!currentGraphController) return null;
    return {
      selectedElement: currentGraphController.getSelectedElement?.() || null,
      interactionMode: currentGraphController.getInteractionMode?.() || 'inspect',
      activeDrillNode: currentGraphController.getActiveDrillNode?.() || activeDrillNode || null,
    };
  }

  function restoreKnowledgeGraphViewState(viewState = null) {
    if (!currentGraphController || !viewState) return;
    const selectedElement = viewState.selectedElement?.id ? viewState.selectedElement : null;
    const fallbackSelection = viewState.activeDrillNode
      ? { type: 'node', id: viewState.activeDrillNode }
      : null;
    const selection = selectedElement || fallbackSelection;

    if (viewState.interactionMode && viewState.interactionMode !== 'inspect') {
      const selectedNodeId = selection?.type === 'node' ? selection.id : viewState.activeDrillNode;
      currentGraphController.setInteractionMode?.(viewState.interactionMode, selectedNodeId || null);
      return;
    }

    if (selection) {
      currentGraphController.selectElement?.(selection);
    }
  }

  function remountOpenKnowledgeGraphForTheme() {
    const mapView = document.getElementById('map-view');
    if (!mapView?.classList.contains('visible') || !currentGraphController) return;

    const concept = getActiveConcept();
    const rawData = concept?.graphData ? normalizeGraphData(concept.graphData).graphData : null;
    if (!rawData) return;

    const viewState = captureKnowledgeGraphViewState();
    destroyKnowledgeGraphController();
    mountKnowledgeGraphController(rawData);
    restoreKnowledgeGraphViewState(viewState);

    if (currentMapMode === 'graph' && currentGraphController) {
      requestAnimationFrame(() => currentGraphController?.resize());
    }
  }

  function setMapShellOpen(isOpen) {
    document.body.dataset.mapOpen = isOpen ? 'true' : 'false';
  }

  function getHeroStateLabel(state) {
    switch (state) {
      case 'instantiated': return 'source captured';
      case 'growing': return 'draft path';
      case 'fractured': return 'worth revisiting';
      case 'hibernating': return 'spacing';
      case 'actualized': return 'spaced evidence';
      default: return 'no map yet';
    }
  }

  function getHeroGuidance(concept) {
    if (!concept) return 'Name one concept. socratink helps you rebuild it from memory; the first room asks for a small cold attempt before any explanation appears.';
    switch (concept.state) {
      case 'instantiated':
        return concept.graphData
          ? 'Open the draft path. It is a hypothesis, not evidence yet.'
          : 'Map this source into a draft path. The draft is not learner evidence.';
      case 'growing':
        return concept.graphData
          ? 'Open the draft path. Start with one cold attempt before study appears.'
          : 'Continue by mapping this concept into a draft path.';
      case 'fractured':
        return 'A spaced re-drill found a gap worth repairing. Revisit the mechanism, then return under spacing.';
      case 'hibernating':
        return 'This room is spacing. Work elsewhere or return when re-drill is eligible.';
      case 'actualized':
        return 'Spaced evidence is on record. Re-drill later if you want to challenge it.';
      default:
        return 'Name one concept. The first room asks for a small cold attempt before any explanation appears.';
    }
  }

  function getHeroActionConfig(concept) {
    if (!concept) {
      return { label: 'Begin', action: 'add', disabled: false };
    }
    switch (concept.state) {
      case 'instantiated':
        return concept.graphData
          ? { label: 'Open Draft Path', action: 'open-map', disabled: false }
          : { label: 'Draft Map', action: 'extract', disabled: false };
      case 'growing':
        return concept.graphData
          ? { label: 'Open Draft Path', action: 'open-map', disabled: false }
          : { label: 'Draft Map', action: 'extract', disabled: false };
      case 'fractured':
        return { label: 'Repair Gap', action: 'drill', disabled: false };
      case 'hibernating':
        return concept.graphData
          ? { label: 'Open Evidence Map', action: 'open-map', disabled: false }
          : { label: 'Return Later', action: 'wait', disabled: true };
      case 'actualized':
        return concept.graphData
          ? { label: 'Open Evidence Map', action: 'open-map', disabled: false }
          : { label: 'Open Desk', action: 'wait', disabled: true };
      default:
        return { label: 'Begin', action: 'add', disabled: false };
    }
  }

  function renderHero(concept) {
    if (!concept) {
      titleEl.textContent = 'What do you want to understand?';
      descEl.textContent = getHeroGuidance(null);
      if (heroStateChipEl) {
        heroStateChipEl.textContent = 'no map yet';
        heroStateChipEl.dataset.state = 'empty';
      }
    } else {
      titleEl.textContent = concept.name;
      descEl.textContent = getHeroGuidance(concept);
      if (heroStateChipEl) {
        heroStateChipEl.textContent = getHeroStateLabel(concept.state);
        heroStateChipEl.dataset.state = concept.state;
      }
    }

    if (heroPrimaryActionEl) {
      const config = getHeroActionConfig(concept);
      const labelEl = heroPrimaryActionEl.querySelector('.hero-primary-action__label');
      if (labelEl) {
        labelEl.textContent = config.label;
      } else {
        heroPrimaryActionEl.textContent = config.label;
      }
      heroPrimaryActionEl.dataset.action = config.action;
      heroPrimaryActionEl.disabled = Boolean(config.disabled);
      heroPrimaryActionEl.title = config.disabled ? 'This action is unavailable right now.' : config.label;
    }
  }

  function runHeroAction(evtOrNothing) {
    // Empty-state form submit path: a Submit event comes in. Hero is single-purpose:
    // capture the concept name. Source material is attached on the modal's
    // source-material chip if the learner wants it.
    if (evtOrNothing && typeof evtOrNothing.preventDefault === 'function') {
      evtOrNothing.preventDefault();
      const field = document.getElementById('hero-single-input-field');
      const raw = (field ? field.value : '').trim();
      if (!raw) return false;
      showDashboard();
      openDrawer();
      startAddConcept({ name: raw });
      if (field) {
        field.value = '';
        field.style.height = '';
      }
      return false;
    }

    // Non-empty-state path: the Begin button drives Begin/Extract/Drill/Open-map.
    const concept = getActiveConcept();
    const action = heroPrimaryActionEl?.dataset.action || (!concept ? 'add' : '');
    if (action === 'add') {
      showDashboard();
      openDrawer();
      startAddConcept();
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

  // Wire up the empty-state single input: autogrow, enable Begin on non-empty,
  // and attach small source files by reading them into the prompt.
  function initHeroSingleInput() {
    const field = document.getElementById('hero-single-input-field');
    if (!(field instanceof HTMLTextAreaElement)) return;
    const form = document.getElementById('hero-single-input');
    const submit = form?.querySelector('.hero-single-input__submit');
    const autogrow = () => {
      field.style.height = 'auto';
      field.style.height = Math.min(field.scrollHeight, 240) + 'px';
    };
    const sync = () => {
      if (submit instanceof HTMLButtonElement) {
        submit.disabled = field.value.trim().length === 0;
      }
      autogrow();
    };
    field.addEventListener('input', sync);
    // Cmd/Ctrl+Enter to submit from textarea (since plain Enter adds a newline).
    field.addEventListener('keydown', (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter' && field.value.trim()) {
        e.preventDefault();
        form?.requestSubmit?.();
      }
    });
    const chips = document.querySelectorAll('[data-hero-example]');
    chips.forEach((chip) => {
      chip.addEventListener('click', () => {
        const value = chip.dataset.heroExample || '';
        if (!value) return;
        field.value = value;
        field.focus();
        field.setSelectionRange(value.length, value.length);
        sync();
      });
    });
    sync();
  }


  // ── 7. Animation helpers ───────────────────────────────────
  const ANIM_CLASSES = {
    emerge: 'anim-emerge', crack: 'anim-crack', cocoon: 'anim-cocoon',
    actualize: 'anim-actualize', repair: 'anim-repair',
  };

  function playAnim(name, tileIdx) {
    const cls = ANIM_CLASSES[name];
    if (!cls) return;
    const el = document.getElementById('concept-marker-anim-' + tileIdx);
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
  // Desk tiles are inventory/navigation. The pin marks that a concept
  // has earned a place here; it does not encode graph-truth evidence.
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

  function conceptPinSVG(idx, state) {
    return `
    <g class="concept-marker-anim" id="concept-marker-anim-${idx}">
      <g class="concept-pin" id="concept-pin-${idx}" data-state="${state}" style="pointer-events:none;">
        <ellipse class="concept-pin-shadow" cx="70" cy="43" rx="17" ry="3.5"/>
        <line class="concept-pin-line" x1="70" y1="-15" x2="70" y2="38"/>
        <circle class="concept-pin-head" cx="70" cy="-15" r="8.5"/>
        <circle class="concept-pin-core" cx="70" cy="-15" r="3.1"/>
      </g>
    </g>`;
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
      } else {
        tileEl.innerHTML = TILE_PLATFORM + conceptPinSVG(idx, concept.state);
      }
    });
  }

  // ── 10. Drawer ─────────────────────────────────────────────
  function openDrawer() {
    drawer.dataset.open = 'true';
    document.body.dataset.drawerOpen = 'true';
    if (drawerToggle) drawerToggle.setAttribute('aria-expanded', 'true');
  }
  function closeDrawer() {
    drawer.dataset.open = 'false';
    document.body.dataset.drawerOpen = 'false';
    if (drawerToggle) drawerToggle.setAttribute('aria-expanded', 'false');
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
        <button class="concept-delete" onclick="App.deleteConcept('${c.id}',this)" title="Delete concept">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>`;
      item.addEventListener('click', e => {
        if (e.target instanceof Element && e.target.closest('.concept-delete')) return;
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
      ? `<button class="add-trigger disabled" type="button" disabled aria-disabled="true" title="Library full. Remove a concept to add another.">
           <span class="add-trigger-icon" aria-hidden="true">
             <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round">
               <line x1="6" y1="2" x2="6" y2="10"/>
               <line x1="2" y1="6" x2="10" y2="6"/>
             </svg>
           </span>
           <span class="add-trigger-title">library full</span>
         </button>`
      : `<button class="add-trigger" id="add-trigger" type="button" onclick="App.startAddConcept()">
           <span class="add-trigger-icon" aria-hidden="true">
             <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round">
               <line x1="6" y1="2" x2="6" y2="10"/>
               <line x1="2" y1="6" x2="10" y2="6"/>
             </svg>
           </span>
           <span class="add-trigger-title">new tink</span>
         </button>`;
  }

  function isBlockedVideoUrl(value) {
    try {
      const parsed = new URL(value);
      const host = parsed.hostname.toLowerCase();
      return host === 'youtu.be'
        || host === 'youtube.com'
        || host.endsWith('.youtube.com')
        || host === 'youtube-nocookie.com'
        || host.endsWith('.youtube-nocookie.com');
    } catch {
      return false;
    }
  }

  function shortOnboardingText(value, maxLength = 180) {
    const text = String(value || '').replace(/\s+/g, ' ').trim();
    if (text.length <= maxLength) return text;
    return `${text.slice(0, maxLength - 3).trimEnd()}...`;
  }

  function hasStudyEvidence(node = {}) {
    return node.drill_status === 'primed'
      || node.drill_status === 'drilled'
      || node.drill_status === 'solidified'
      || node.drill_status === 'solid'
      || Boolean(node.gap_type);
  }

  // ── 12. CRUD ───────────────────────────────────────────────
  function buildContentInputUI(container, { onSubmit, onCancel, showClipboard }) {
    let uploadedText = '';
    let uploadedFilename = '';
    let fetchedUrlText = '';
    let fetchedUrlTitle = '';
    let fetchedUrl = '';
    let activeTab = 'paste';

    container.innerHTML = `
      <div class="overlay-tabs creation-source-tabs">
        <button class="overlay-tab active" data-tab="paste">Paste</button>
        <button class="overlay-tab" data-tab="url">URL</button>
        <button class="overlay-tab" data-tab="upload">Upload</button>
      </div>
      <div class="overlay-panel" data-panel="paste">
        <textarea class="overlay-textarea" placeholder="Paste source material here."></textarea>
        ${showClipboard ? '<div class="paste-actions"><button class="paste-clipboard-btn" type="button">Paste from clipboard</button></div>' : ''}
      </div>
      <div class="overlay-panel" data-panel="url" style="display:none">
        <input class="overlay-url-input" type="url" placeholder="https://example.com/article">
        <p class="overlay-dropfeedback overlay-url-feedback"></p>
      </div>
      <div class="overlay-panel" data-panel="upload" style="display:none">
        <div class="overlay-dropzone">
          Drop a file or click to browse<br>
          <span style="font-size:11px;opacity:0.65">.txt &nbsp; .md &nbsp; .pdf &nbsp; up to 2MB</span>
        </div>
        <input type="file" accept=".txt,.md,.pdf" style="display:none">
        <p class="overlay-dropfeedback overlay-file-feedback"></p>
      </div>
      <div class="overlay-footer">
        <button class="overlay-cancel">Cancel</button>
        <button class="overlay-extract" disabled>Extract</button>
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
    const cancelBtn = container.querySelector('.overlay-cancel');
    const submitBtn = container.querySelector('.overlay-extract');

    function hasContent() {
      if (activeTab === 'paste') return textarea.value.trim().length > 0;
      if (activeTab === 'url') {
        const rawUrl = urlInput.value.trim();
        return rawUrl.length > 0 && !isBlockedVideoUrl(rawUrl);
      }
      return uploadedText.length > 0;
    }
    function checkSubmitEnabled() {
      const blockedVideoUrl = activeTab === 'url' && isBlockedVideoUrl(urlInput.value.trim());
      submitBtn.disabled = !(hasContent() && !blockedVideoUrl);
      if (urlFeedback) {
        const rawUrl = urlInput.value.trim();
        urlFeedback.className = 'overlay-dropfeedback overlay-url-feedback';
        if (rawUrl && isBlockedVideoUrl(rawUrl)) {
          urlFeedback.classList.add('error');
          urlFeedback.textContent = 'Video links are not supported in this build. Paste notes or transcript text instead.';
        } else {
          urlFeedback.textContent = '';
        }
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

    textarea.addEventListener('input', checkSubmitEnabled);
    if (urlInput) {
      urlInput.addEventListener('input', () => {
        fetchedUrlText = '';
        fetchedUrlTitle = '';
        fetchedUrl = '';
        checkSubmitEnabled();
      });
      urlInput.addEventListener('keydown', e => {
        if (e.key === 'Enter' && !submitBtn.disabled) { e.preventDefault(); doSubmit(); }
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
          uploadedText = '';
          uploadedFilename = '';
          checkSubmitEnabled();
        }
      );
    }

    cancelBtn.addEventListener('click', () => {
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
      onSubmit({
        text,
        type,
        filename,
        url,
      });
    }

    textarea.focus();
    checkSubmitEnabled();
    return {
      destroy() {
        container.innerHTML = '';
      }
    };
  }

  // ── Dialog helpers (C6a) ─────────────────────────────────────
  let __dialogInertedNodes = [];
  function mountCreationDialog() {
    let node = document.getElementById('creation-dialog');
    const firstMount = !node;
    if (firstMount) {
      node = document.createElement('div');
      node.id = 'creation-dialog';
      node.className = 'creation-dialog';
      node.setAttribute('role', 'dialog');
      node.setAttribute('aria-modal', 'true');
      node.setAttribute('aria-labelledby', 'creation-dialog-title');
      node.innerHTML = `
        <div class="creation-dialog-scrim"></div>
        <div class="creation-dialog-shell">
          <div class="creation-dialog-header">
            <span class="creation-dialog-kicker">NEW CONCEPT</span>
            <button class="creation-dialog-close" type="button" aria-label="Close">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>
          <h3 id="creation-dialog-title" class="creation-dialog-title">Start a concept</h3>
          <div class="creation-dialog-banner-slot"></div>
          <div class="creation-dialog-content"></div>
          <p class="creation-dialog-meta">Study content stays locked until the cold attempt.</p>
        </div>
      `;
      document.body.appendChild(node);
      node.querySelector('.creation-dialog-close').addEventListener('click', () => closeCreationDialog());
      node.querySelector('.creation-dialog-scrim').addEventListener('click', () => closeCreationDialog());
      node.querySelector('.creation-dialog-shell').addEventListener('keydown', trapFocusHandler);
    }
    node.dataset.open = 'true';
    __dialogInertedNodes = Array.from(document.body.children).filter(
      (el) => el !== node && !el.hasAttribute('inert')
    );
    __dialogInertedNodes.forEach((el) => el.setAttribute('inert', ''));
    document.addEventListener('keydown', creationDialogKeyHandler);
    return {
      node,
      shell: node.querySelector('.creation-dialog-shell'),
      shellContent: node.querySelector('.creation-dialog-content'),
      bannerSlot: node.querySelector('.creation-dialog-banner-slot'),
    };
  }

  function closeCreationDialog() {
    const node = document.getElementById('creation-dialog');
    if (!node) return;
    node.dataset.open = 'false';
    __dialogInertedNodes.forEach((el) => el.removeAttribute('inert'));
    __dialogInertedNodes = [];
    document.removeEventListener('keydown', creationDialogKeyHandler);
    setTimeout(() => {
      if (node.dataset.open === 'false') {
        node.querySelector('.creation-dialog-banner-slot').innerHTML = '';
        node.querySelector('.creation-dialog-content').innerHTML = '';
      }
    }, 350);
    (window.__creationDialogTrigger || document.body).focus?.();
  }

  function creationDialogKeyHandler(e) {
    if (e.key === 'Escape') closeCreationDialog();
  }

  function trapFocusHandler(e) {
    if (e.key !== 'Tab') return;
    const container = e.currentTarget;
    const focusables = container.querySelectorAll(
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
    );
    if (!focusables.length) return;
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }

  function buildGuestBanner() {
    const banner = document.createElement('div');
    banner.className = 'creation-banner creation-banner--guest';
    banner.innerHTML = `
      <div>
        <strong>Guest mode uses sample maps.</strong><br>
        Sign in to extract your own content into a draft map.
      </div>
    `;
    return banner;
  }

  // Contract invariant — extraction success path must validate payload shape
  // BEFORE any state mutation. Prevents BLOCKER UX-todo #4 silent-discard
  // where an empty/malformed jsonPayload created a concept anyway.
  function isValidKnowledgeMap(map) {
    if (!map || typeof map !== 'object') return false;
    if (!Array.isArray(map.backbone) || map.backbone.length === 0) return false;
    if (!Array.isArray(map.clusters)) return false;
    return true;
  }

  // User-facing, never echoes raw err.message — auth headers / stack
  // fragments leak through otherwise.
  function sanitizeExtractError(err) {
    if (!err) return 'Something went wrong. Try again when ready.';
    const msg = String(err.message || '');
    if (/\b401|unauthor/i.test(msg)) return 'Sign in required to run extraction.';
    if (/\b403|forbidden/i.test(msg)) return 'That request was not allowed.';
    if (/\b429|rate limit/i.test(msg)) return 'Extraction service is throttled. Give it a minute and retry.';
    if (/\b5\d{2}|server error/i.test(msg)) return 'The extraction service hiccuped. Try again when ready.';
    if (/invalid map/i.test(msg)) return 'The extraction service returned an unexpected result. Try again when ready.';
    return 'The network or service was unreachable. Try again when ready.';
  }

  function buildErrorBanner(sanitizedMessage) {
    const banner = document.createElement('div');
    banner.className = 'creation-banner creation-banner--error';
    banner.innerHTML = `
      <div>
        <strong>Extraction stopped.</strong><br>
        ${escHtml(sanitizedMessage)}
      </div>
    `;
    return banner;
  }

  // Calm, seed-specific error banner used in error-recovery remount.
  // Distinct from buildErrorBanner (which prefixes "Extraction stopped.") to
  // avoid the console-y tone on what may be a transient model-output issue.
  function buildSeedFailureBanner(message) {
    const banner = document.createElement('div');
    banner.className = 'creation-banner creation-banner--error';
    banner.innerHTML = `
      <div>
        ${escHtml(message)}
      </div>
    `;
    return banner;
  }

  function buildGuestActions(loginHref) {
    const row = document.createElement('div');
    row.className = 'creation-guest-actions';
    row.innerHTML = `
      <button class="btn-browse-starters" type="button">Browse starter maps</button>
      <a class="auth-link" href="${escHtml(loginHref)}">Continue with Google</a>
    `;
    row.querySelector('.btn-browse-starters').addEventListener('click', () => {
      closeCreationDialog();
      showLibrary();
    });
    return row;
  }

  // ── mountExtractOverlay ─────────────────────────────────────
  // Mounts the full-viewport extract overlay and starts all animation
  // cycles. Returns an overlayHandle object with a single method:
  //   removeOverlay(success) — tears down the overlay.
  //     success=true  → sets 100% + “Draft ready”, waits 700ms, then fades.
  //     success=false → immediate fade-out (error path).
  //
  // The overlay mounts BEFORE the network call so learners see activity
  // immediately after clicking Build. (Option A refactor — 2026-05-04.)
  //
  // Callers must NOT call removeOverlay twice; the DOM element is removed
  // by the first call's scheduled timeout.
  function mountExtractOverlay({ name }) {
    const OVERLAY_TIPS = [
      'socratink is drafting your starting map.',
      'Spacing retrieval over time helps short-term recall become more durable.',
      'socratink is structuring the rooms.',
      'Answering before the explanation appears gives study something specific to repair.',
      'socratink is sketching the draft route.',
      'The graph records evidence from attempts and spaced reconstruction, not exposure.',
      'Reading is exposure. Reconstruction is evidence.',
    ];

    const META_STAGES = [
      'Mapping concept graph...',
      'Checking for contradictions...',
      'Synthesizing relationships...',
      'Drafting provisional route...',
      'Structuring final map...',
    ];

    const extractOverlay = document.createElement('div');
    extractOverlay.id = 'extract-overlay';
    extractOverlay.innerHTML = `
      <canvas class="eo-particle-canvas"></canvas>
      <div class="eo-glow-blob"></div>
      <header class="eo-header">
        <img src="/brand/socratink-mark-square.png?v=1" alt="" class="eo-brand-mark" aria-hidden="true">
        <h1 class="eo-brand">socratink</h1>
      </header>
      <div class="eo-focal">
        <div class="eo-radar"></div>
        <div class="eo-ring-outer"></div>
        <div class="eo-ring-inner"></div>
        <svg class="eo-crystal-svg" xmlns="http://www.w3.org/2000/svg" viewBox="54 65 92 110" overflow="hidden">
          <defs>
            <filter id="eo-glow" x="-40%" y="-40%" width="180%" height="180%">
              <feGaussianBlur stdDeviation="3" result="blur"/>
              <feComposite in="SourceGraphic" in2="blur" operator="over"/>
            </filter>
          </defs>
          <g class="eo-crystal-grow">
            <!-- glow halo — soft, no drop-shadow interference -->
            <polygon points="100,73 121,91 131,119 117,145 100,167 83,145 69,119 79,91" fill="hsl(270,55%,65%)" opacity="0.18" filter="url(#eo-glow)"/>
            <!-- lower-left -->
            <polygon points="100,119 69,119 83,145 100,167" fill="hsl(270,42%,52%)"/>
            <!-- lower-right -->
            <polygon points="100,119 100,167 117,145 131,119" fill="hsl(270,38%,42%)"/>
            <!-- upper-left -->
            <polygon points="100,73 79,91 69,119 100,119" fill="hsl(270,48%,62%)"/>
            <!-- upper-right -->
            <polygon points="100,73 100,119 131,119 121,91" fill="hsl(270,42%,52%)"/>
            <!-- bottom-tip -->
            <polygon points="83,145 100,167 117,145" fill="hsl(270,38%,42%)"/>
            <!-- top — brightest face -->
            <polygon points="100,73 79,91 100,119 121,91" fill="hsl(270,52%,74%)"/>
            <!-- specular -->
            <polygon points="104,77 114,94 112,85" fill="hsl(270,60%,92%)" opacity="0.7"/>
          </g>
        </svg>
        <div class="eo-pill eo-pill-top">
          <span class="material-symbols-outlined eo-pill-icon">auto_awesome</span>
          <span class="eo-status-label">Analyzing</span>
        </div>
        <div class="eo-pill eo-pill-bottom">
          <span class="material-symbols-outlined eo-pill-icon">memory</span>
          <span class="eo-concept-name">${escHtml(name)}</span>
        </div>
      </div>
      <div class="eo-meta-status">
        <span class="eo-meta-text">Parsing source content...</span>
      </div>
      <div class="eo-tip">
        <p class="eo-tip-text">&ldquo;socratink is drafting your starting map.&rdquo;</p>
      </div>
      <footer class="eo-footer">
        <div class="eo-progress-meta">
          <span class="eo-progress-label">Drafting</span>
          <span class="eo-progress-pct">20%</span>
        </div>
        <div class="eo-progress-track">
          <div class="eo-progress-bar" style="width:20%">
            <div class="eo-progress-shimmer"></div>
          </div>
        </div>
      </footer>
    `;
    document.body.appendChild(extractOverlay);

    let trickleInterval = null;
    let tipInterval = null;
    let metaInterval = null;
    let pgDots = [], pgCursor = null, pgRafId = null;

    const PG = {
      SPACING: 28, DOT_R: 1.2,
      BASE_OP: 0.14, MAX_OP: 0.38,
      INFLUENCE: 90, MAX_PUSH: 7, EASE: 0.07, OP_EASE: 0.10,
      SETTLE_THRESH: 0.12,
    };

    function setMetaStatus(txt) {
      const el = extractOverlay.querySelector('.eo-meta-text');
      if (!el) return;
      el.classList.add('eo-meta-exit');
      setTimeout(() => { el.textContent = txt; el.classList.remove('eo-meta-exit'); }, 260);
    }

    function startMetaCycle() {
      let idx = 0;
      setMetaStatus(META_STAGES[0]);
      metaInterval = setInterval(() => {
        idx = (idx + 1) % META_STAGES.length;
        setMetaStatus(META_STAGES[idx]);
      }, 3500);
    }

    function startTipCycle() {
      let idx = 0;
      tipInterval = setInterval(() => {
        const tipEl = extractOverlay.querySelector('.eo-tip-text');
        if (!tipEl) return;
        tipEl.classList.add('eo-tip-exit');
        setTimeout(() => {
          idx = (idx + 1) % OVERLAY_TIPS.length;
          tipEl.innerHTML = '"' + OVERLAY_TIPS[idx] + '"';
          tipEl.classList.remove('eo-tip-exit');
        }, 420);
      }, 5500);
    }

    function pgInit() {
      const canvas = extractOverlay.querySelector('.eo-particle-canvas');
      if (!canvas) return;
      const W = canvas.offsetWidth, H = canvas.offsetHeight;
      canvas.width = W; canvas.height = H;
      pgDots = [];
      for (let y = PG.SPACING / 2; y < H; y += PG.SPACING) {
        for (let x = PG.SPACING / 2; x < W; x += PG.SPACING) {
          pgDots.push({ ox: x, oy: y, x, y, op: PG.BASE_OP });
        }
      }
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = 'white';
      pgDraw(ctx);
      canvas.closest('#extract-overlay').addEventListener('mousemove', e => {
        const r = canvas.getBoundingClientRect();
        pgCursor = { x: e.clientX - r.left, y: e.clientY - r.top };
        if (!pgRafId) pgRafId = requestAnimationFrame(() => pgTick(ctx));
      });
      canvas.closest('#extract-overlay').addEventListener('mouseleave', () => {
        pgCursor = null;
        if (!pgRafId) pgRafId = requestAnimationFrame(() => pgTick(ctx));
      });
    }

    function pgUpdate() {
      const cx = pgCursor ? pgCursor.x : null;
      const cy = pgCursor ? pgCursor.y : null;
      for (const d of pgDots) {
        if (cx !== null) {
          const dx = d.ox - cx, dy = d.oy - cy;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < PG.INFLUENCE && dist > 0) {
            const s = (1 - dist / PG.INFLUENCE) * PG.MAX_PUSH;
            d.x += (d.ox + (dx / dist) * s - d.x) * 0.18;
            d.y += (d.oy + (dy / dist) * s - d.y) * 0.18;
            d.op += (PG.BASE_OP + (1 - dist / PG.INFLUENCE) * (PG.MAX_OP - PG.BASE_OP) - d.op) * PG.OP_EASE;
          } else {
            d.x += (d.ox - d.x) * PG.EASE;
            d.y += (d.oy - d.y) * PG.EASE;
            d.op += (PG.BASE_OP - d.op) * PG.OP_EASE;
          }
        } else {
          d.x += (d.ox - d.x) * PG.EASE;
          d.y += (d.oy - d.y) * PG.EASE;
          d.op += (PG.BASE_OP - d.op) * PG.OP_EASE;
        }
      }
    }

    function pgDraw(ctx) {
      ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
      for (const d of pgDots) {
        ctx.globalAlpha = d.op;
        ctx.beginPath();
        ctx.arc(d.x, d.y, PG.DOT_R, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    function pgSettled() {
      return pgDots.every(d =>
        Math.abs(d.x - d.ox) < PG.SETTLE_THRESH &&
        Math.abs(d.y - d.oy) < PG.SETTLE_THRESH &&
        Math.abs(d.op - PG.BASE_OP) < 0.004
      );
    }

    function pgTick(ctx) {
      pgUpdate();
      pgDraw(ctx);
      if (!pgSettled()) {
        pgRafId = requestAnimationFrame(() => pgTick(ctx));
      } else {
        pgRafId = null;
      }
    }

    function setCrystalScale(pct) {
      const grow = extractOverlay.querySelector('.eo-crystal-grow');
      if (!grow) return;
      const t = pct / 100;
      const scale = 0.025 + Math.pow(t, 2) * 0.975;
      const opacity = 0.35 + t * 0.65;
      grow.style.transform = `scale(${scale.toFixed(3)})`;
      grow.style.opacity = opacity.toFixed(2);
    }

    function setOverlayProgress(pct, statusText) {
      const bar = extractOverlay.querySelector('.eo-progress-bar');
      const pctEl = extractOverlay.querySelector('.eo-progress-pct');
      const statusEl = extractOverlay.querySelector('.eo-status-label');
      if (bar) bar.style.width = pct + '%';
      if (pctEl) pctEl.textContent = pct + '%';
      if (statusText && statusEl) statusEl.textContent = statusText;
      setCrystalScale(pct);
    }

    function startTrickle() {
      let current = 65;
      const target = 89;
      const tickMs = 1000;
      const increment = (target - current) / 28; // 28s matches CSS eoTrickle duration
      trickleInterval = setInterval(() => {
        current = Math.min(current + increment, target);
        const pctEl = extractOverlay.querySelector('.eo-progress-pct');
        if (pctEl) pctEl.textContent = Math.round(current) + '%';
        setCrystalScale(Math.round(current));
        if (current >= target) { clearInterval(trickleInterval); trickleInterval = null; }
      }, tickMs);
    }

    function removeOverlay(success = false) {
      if (trickleInterval) { clearInterval(trickleInterval); trickleInterval = null; }
      if (tipInterval) { clearInterval(tipInterval); tipInterval = null; }
      if (metaInterval) { clearInterval(metaInterval); metaInterval = null; }
      if (pgRafId) { cancelAnimationFrame(pgRafId); pgRafId = null; }
      if (success) {
        extractOverlay.classList.remove('eo-mapping');
        const bar = extractOverlay.querySelector('.eo-progress-bar');
        const pctEl = extractOverlay.querySelector('.eo-progress-pct');
        const statusEl = extractOverlay.querySelector('.eo-status-label');
        if (bar) bar.style.width = '100%';
        if (pctEl) pctEl.textContent = '100%';
        if (statusEl) statusEl.textContent = 'Draft ready';
        setCrystalScale(100);
        setTimeout(() => {
          extractOverlay.classList.remove('visible');
          setTimeout(() => { if (extractOverlay.parentNode) extractOverlay.parentNode.removeChild(extractOverlay); }, 400);
        }, 700);
      } else {
        extractOverlay.classList.remove('visible');
        setTimeout(() => { if (extractOverlay.parentNode) extractOverlay.parentNode.removeChild(extractOverlay); }, 400);
      }
    }

    requestAnimationFrame(() => {
      extractOverlay.classList.add('visible');
      startTipCycle();
      pgInit();
      setCrystalScale(20);
      setOverlayProgress(65, 'Drafting map');
      extractOverlay.classList.add('eo-mapping');
      startTrickle();
      startMetaCycle();
    });

    return { removeOverlay };
  }

  // ── finishConceptCreateAfterOverlay ──────────────────────────
  // Runs persistence + teardown AFTER the network call resolves.
  // The extract overlay is already mounted by the caller (via mountExtractOverlay)
  // before the network call. This function does NOT mount the overlay.
  //
  // Parameters:
  //   id            — pre-generated concept id (generateId())
  //   name          — concept name string
  //   knowledgeMap  — already-validated knowledge map object
  //   startedAtIso  — ISO timestamp of when creation began
  //   startedPerf   — performance.now() at creation start (preserved for
  //                   future duration telemetry)
  //   startingSketch — the learner's rough map text
  //   source        — resolved source object { type, text } from concept-create.js
  //   overlayHandle — { removeOverlay } returned by mountExtractOverlay
  function finishConceptCreateAfterOverlay({ id, name, knowledgeMap, startedAtIso, startedPerf, startingSketch, source, overlayHandle }) {
    const startingMapContext = String(startingSketch || '').trim().slice(0, 1200);

    // Derive content fields from source (URL already resolved by concept-create.js)
    const sourceText = (source && source.text) ? source.text : '';
    const sourceType = (source && source.type) ? source.type : 'text';
    const sourceFilename = (source && source.filename) ? source.filename : null;

    const jsonPayload = { ...knowledgeMap, metadata: { ...(knowledgeMap.metadata || {}) } };
    jsonPayload.metadata.starting_map_context = startingMapContext;
    jsonPayload.metadata.map_maturity = 'provisional';

    const concepts = loadConcepts();
    const concept = {
      id, name, state: 'growing',
      createdAt: Date.now(), timerStart: null,
      contentPreview: sourceText.slice(0, 500),
      contentType: sourceType,
      contentFilename: sourceFilename,
      sourceUrl: source?.url || null,
      startingMapContext,
      graphData: JSON.stringify(jsonPayload)
    };
    contentStore.set(id, sourceText);
    concepts.push(concept);
    saveConcepts(concepts);
    renderGrid(concepts);
    renderConceptList(concepts);
    selectConcept(concept.id);
    closeDrawer();
    overlayHandle.removeOverlay(true);
  }

  async function startAddConcept(seed) {
    window.__creationDialogTrigger = document.activeElement;
    const dialog = mountCreationDialog();
    let isGuest = false;
    let session = null;
    try {
      session = await fetchAuthSession();
      isGuest = !!(session && session.guest_mode);
    } catch (err) {
      console.warn('Auth fetch failed during concept creation:', err);
    }

    if (isGuest) {
      dialog.bannerSlot.appendChild(buildGuestBanner());
      dialog.shellContent.appendChild(buildGuestActions(buildLoginHref('/')));
      const firstFocusable = dialog.shell.querySelector('a, button:not([disabled])');
      firstFocusable?.focus();
      return;
    }

    const { buildConversationalCreateUI } = await import('./concept-create.js');

    // Re-mount the creation dialog at the summary card stage, preserving the
    // learner's concept, sketchTurns, and source from the failed submit.
    // Banner names two strategic paths without consoling or naming the provider.
    function remountWithError(err, preservedState) {
      const dialog2 = mountCreationDialog();
      dialog2.bannerSlot.appendChild(
        buildSeedFailureBanner(
          "socratink couldn't draft from this seed. You can try again, or attach source material for a different draft path."
        )
      );
      buildConversationalCreateUI(dialog2.shellContent, {
        seed: {
          name: preservedState?.name || seed?.name || "",
          sketchTurns: preservedState?.sketchTurns || [],
          source: preservedState?.source || null,
          stage: "summary",
          ctaOverrideCopy: "Try again",
        },
        onCancel: () => closeCreationDialog(),
        onBeforeSubmit: ({ name: n }) => {
          closeCreationDialog();
          return mountExtractOverlay({ name: n });
        },
        onSubmit: handleSubmit,
        onSubmitError: ({ overlayHandle, error, preservedState: ps }) => {
          if (overlayHandle) overlayHandle.removeOverlay(false);
          remountWithError(error, ps);
        },
      });
    }

    function handleSubmit({ name, startingSketch, source, provisionalMap, overlayHandle }) {
      if (!isValidKnowledgeMap(provisionalMap)) {
        // The dialog is already closed (onBeforeSubmit closed it). Tear down
        // the overlay and re-mount the dialog with an error banner.
        // Preserve the learner's sketch and source so the re-mounted summary
        // card is populated — same effort-preservation as the network-error path.
        if (overlayHandle) overlayHandle.removeOverlay(false);
        const preservedState = {
          name,
          sketchTurns: startingSketch ? [startingSketch] : [],
          source,
        };
        remountWithError(new Error('invalid map'), preservedState);
        return;
      }

      finishConceptCreateAfterOverlay({
        id: generateId(),
        name,
        knowledgeMap: provisionalMap,
        startedAtIso: new Date().toISOString(),
        startedPerf: performance.now(),
        startingSketch,
        source,
        overlayHandle,
      });
    }

    buildConversationalCreateUI(dialog.shellContent, {
      seed,
      onCancel: () => closeCreationDialog(),
      onBeforeSubmit: ({ name }) => {
        if (loadConcepts().length >= 4) {
          // Library is at the 4-concept cap. Don't pay for an LLM call.
          // Don't close the dialog. Surface the cap inline so the learner
          // can either remove a concept or cancel.
          dialog.bannerSlot.innerHTML = '';
          dialog.bannerSlot.appendChild(
            buildSeedFailureBanner('Library is full. Remove a concept first to add another.')
          );
          return null;
        }
        // Pre-flight: close the dialog and mount the overlay BEFORE the
        // network call so there is no silent-wait gap after clicking Build.
        closeCreationDialog();
        return mountExtractOverlay({ name });
      },
      onSubmit: handleSubmit,
      onSubmitError: ({ overlayHandle, error, preservedState }) => {
        if (overlayHandle) overlayHandle.removeOverlay(false);
        remountWithError(error, preservedState);
      },
    });
  }

  function deleteConcept(id, btnEl) {
    const concept = loadConcepts().find(c => c.id === id);
    if (!concept) return;

    const conceptName = concept.name || 'this concept';
    const confirmed = window.confirm(`Delete "${conceptName}"?\n\nThis removes its draft path and recorded evidence from this browser.`);
    if (!confirmed) return;

    const wasActive = getActiveId() === id;
    const item = btnEl?.closest?.('.concept-item');
    if (item) { item.style.transition = 'all 0.2s ease'; item.style.opacity = '0'; item.style.transform = 'translateX(-12px)'; }

    const finishDelete = () => {
      const concepts = loadConcepts().filter(c => c.id !== id);
      saveConcepts(concepts);
      clearRepairRepsStateForConcept(id);

      try {
        sessionStorage.removeItem(getPhaseBSessionStorageKey(id));
      } catch (err) {
        console.warn('Unable to clear deleted concept session state.', err);
      }

      const resumeState = loadPhaseBResumeState();
      if (resumeState?.conceptId === id) {
        persistPhaseBResumeState(null);
      }

      if (wasActive) {
        setActiveId(null);
        sessionState = getDefaultPhaseBSessionState();
        showDashboard();
        showEmptyState();
      }
      renderGrid(concepts);
      renderConceptList(concepts);
    };

    if (item) {
      setTimeout(finishDelete, 200);
    } else {
      finishDelete();
    }
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

  function syncSessionStateForActiveConcept(conceptId = getActiveId()) {
    sessionState = loadPhaseBSessionState(conceptId);
  }

  function activateConceptSelection(id) {
    setActiveId(id);
    syncSessionStateForActiveConcept(id);
    const concept = loadConcepts().find(c => c.id === id);
    if (!concept) return null;

    renderHero(concept);
    applyControlsForState(concept.state, concept);
    renderGrid();
    renderConceptList();
    return concept;
  }

  function selectConcept(id) {
    hideContentOverlay();
    hideMapView();
    setNavActive('nav-dashboard');
    const concept = activateConceptSelection(id);
    if (!concept) return;
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

    // Keep the dashboard marker in sync without turning the board into a graph-truth surface.
    const markerEl = document.getElementById('concept-pin-' + tileIdx);
    if (markerEl) {
      markerEl.dataset.state = newState;
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
    if (btnDrill) btnDrill.textContent = 'Start room';
    if (consolidateBtn) {
      consolidateBtn.disabled = true;
      consolidateBtn.textContent = 'Spacing gate unavailable';
      consolidateBtn.title = 'Spacing gate is not active in this MVP';
    }
    showControls(false, false, false, false, false);

    // The old spacing affordance is intentionally unavailable for the MVP.
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
      if (btnDrill) btnDrill.textContent = 'Start repair';
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
          onError('Could not natively extract text from this PDF. Try pasting the content manually.');
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
        core_thesis: "Raw visual structure. Draft map extraction pending or failed.",
        architecture_type: "prototype",
      };
    }

    const meta = data.metadata || {};
    const backbone = data.backbone || [];
    const clusters = data.clusters || [];
    const rels = data.relationships || { domain_mechanics: [], learning_prerequisites: [] };
    const fws = data.frameworks || [];

    const titleEl = document.getElementById('concept-header-title');
    const tagsEl = document.getElementById('concept-header-tags');
    const drillBtn = document.getElementById('concept-start-drill');
    if (titleEl) titleEl.textContent = meta.source_title || concept.name || '';
    if (tagsEl) {
      let tagsHtml = '';
      const stateLabel = getHeroStateLabel(concept.state);
      if (stateLabel && stateLabel !== 'no map yet') {
        tagsHtml += `<span class="map-badge state" data-state="${escHtml(concept.state || '')}"><span class="map-badge-dot" aria-hidden="true"></span>${escHtml(stateLabel)}</span>`;
      }
      if (meta.low_density) tagsHtml += `<span class="map-low-density">lightweight draft</span>`;
      tagsEl.innerHTML = tagsHtml;
    }
    if (drillBtn) {
      const showDrill = concept.state === 'growing' || concept.state === 'fractured';
      drillBtn.hidden = !showDrill;
      drillBtn.textContent = concept.state === 'fractured' ? 'Repair Gap' : 'Start Cold Attempt';
    }

    const domMechs = rels.domain_mechanics || [];
    const lrnPreqs = rels.learning_prerequisites || [];
    const nodeStateLabel = (status) => {
      if (status === 'solidified' || status === 'solid') return 'solidified through spaced reconstruction';
      if (status === 'drilled') return 'worth revisiting';
      if (status === 'primed') return 'primed for study';
      return 'ready for first attempt';
    };
    const nodeStateClass = (status) => {
      if (status === 'solidified' || status === 'solid') return 'solid';
      if (status === 'drilled') return 'drilled';
      if (status === 'primed') return 'primed';
      return 'locked';
    };
    const hasLearnerEvidence = (status) => (
      status === 'primed'
      || status === 'drilled'
      || status === 'solidified'
      || status === 'solid'
    );
    const allDrillRooms = [
      { label: 'Core thesis', drill_status: meta.drill_status },
      ...backbone.map((item, index) => ({
        label: `Suggested branch ${index + 1}`,
        drill_status: item?.drill_status || null,
      })),
      ...clusters.flatMap((cluster) => (cluster.subnodes || []).map((subnode) => ({
        label: subnode?.label || 'Drill room',
        drill_status: subnode?.drill_status || null,
      }))),
    ];
    const attemptedCount = allDrillRooms.filter((room) => (
      room.drill_status === 'primed'
      || room.drill_status === 'drilled'
      || room.drill_status === 'solidified'
      || room.drill_status === 'solid'
    )).length;
    const solidifiedCount = allDrillRooms.filter((room) => (
      room.drill_status === 'solidified'
      || room.drill_status === 'solid'
    )).length;

    let html = '';

    const startingMapContext = String(concept.startingMapContext || meta.starting_map_context || '').trim();
    const hasAnyAttemptEvidence = hasStudyEvidence(meta)
      || backbone.some((item) => hasStudyEvidence(item))
      || clusters.some((cluster) => hasStudyEvidence(cluster) || (cluster.subnodes || []).some((subnode) => hasStudyEvidence(subnode)));

    html += `
      <section class="map-zone map-threshold-zone">
        <div class="map-section-title">Concept Threshold</div>
        <div class="map-threshold-panel">
          <p class="map-threshold-lead">This is global context. The first room will ask one smaller question.</p>
          <blockquote class="map-threshold-quote">${escHtml(startingMapContext || 'No threshold context was captured for this concept.')}</blockquote>
        </div>
      </section>
      <section class="map-zone map-provisional-zone">
        <div class="map-section-title">Provisional Graph</div>
        <div class="map-provisional-panel">
          <p class="map-provisional-copy">The route below is a hypothesis from the source and your threshold. It has not changed graph truth.</p>
          <div class="map-provisional-legend" aria-label="Provisional graph legend">
            <span>draft route</span>
            <span>ready for first attempt</span>
            <span>locked</span>
          </div>
          ${meta.low_density
            ? `<p class="map-provisional-low-density">Drafted from a thin sketch. The route is intentionally sparse — your first cold attempt will fill in what the sketch left out.</p>`
            : ''}
        </div>
      </section>
      <section class="map-zone map-first-room-zone">
        <div class="map-section-title">First Cold Attempt</div>
        <div class="map-first-room">
          <div>
            <div class="map-first-room-kicker">Starting Room</div>
            <h3>Core thesis</h3>
            <p>The first room asks for the governing idea, not the whole source.</p>
          </div>
          <button class="btn-start-drill map-first-room-action" type="button" onclick="App.startDrillFromMap()">Start first room</button>
        </div>
      </section>
    `;

    if (backbone.length > 0) {
      html += '<div class="map-zone zone-2">';
      html += '<div class="map-section-title">Draft Route</div>';
      backbone.forEach((b, idx) => {
        const hasEvidence = hasStudyEvidence(b);
        const stateLabel = hasEvidence ? 'primed for study' : 'locked';
        const routeLabel = hasEvidence ? (b.principle || `Backbone room ${idx + 1}`) : `Backbone room ${idx + 1}`;
        html += `
          <div class="map-backbone-item">
            <span>${escHtml(shortOnboardingText(routeLabel, 110))}</span>
            <span class="map-route-state">${escHtml(stateLabel)}</span>
          </div>
        `;
      });
      html += '</div>';
    }

    if (clusters.length > 0) {
      html += '<div class="map-zone zone-3">';
      html += '<div class="map-section-title">Nearby Rooms</div>';
      clusters.forEach((c, idx) => {
        const isFirst = idx === 0 ? 'expanded' : '';
        const clusterHasEvidence = hasStudyEvidence(c) || (c.subnodes || []).some((subnode) => hasStudyEvidence(subnode));
        const clusterLabel = clusterHasEvidence ? (c.label || `Nearby room set ${idx + 1}`) : `Nearby room set ${idx + 1}`;
        html += `
          <div class="map-cluster-card ${isFirst}" onclick="App.toggleCluster(this)">
            <div class="map-cluster-header">
              <span>${escHtml(clusterLabel)}</span>
              <span class="map-cluster-icon">▾</span>
            </div>
            <div class="map-cluster-body" onclick="event.stopPropagation()">
              <div class="map-cluster-desc">${clusterHasEvidence ? escHtml(c.description || '') : 'Purpose only for now. Study content stays locked until a cold attempt creates something to repair.'}</div>
        `;
        const subnodes = c.subnodes || [];
        subnodes.forEach((sub, subIdx) => {
          const subHasEvidence = hasStudyEvidence(sub);
          const stateClass = nodeStateClass(sub.drill_status);
          const roomLabel = subHasEvidence ? (sub.label || `Room ${subIdx + 1}`) : `Locked room ${subIdx + 1}`;
          const mechanismCopy = subHasEvidence
            ? (sub.mechanism || 'Study material available after the recorded attempt.')
            : 'locked study silhouette. Enter the room before the mechanism appears.';
          html += `
             <div class="map-subnode-row">
               <div class="map-subnode-indicator" data-state="${escHtml(stateClass)}"></div>
               <div class="map-subnode-content">
                 <div class="map-subnode-label">${escHtml(roomLabel)}</div>
                 <div class="map-subnode-mech${subHasEvidence ? '' : ' is-locked'}">${escHtml(mechanismCopy)}</div>
               </div>
             </div>
           `;
        });
        html += `</div></div>`;
      });
      html += '</div>';
    }

    if (hasAnyAttemptEvidence && (domMechs.length > 0 || lrnPreqs.length > 0)) {
      html += '<div class="map-zone zone-4">';
      html += '<div class="map-section-title">Connection Hints</div>';
      if (domMechs.length) html += `<div class="map-cx-item"><strong>Domain links:</strong> ${escHtml(String(domMechs.length))} proposed source relationships.</div>`;
      if (lrnPreqs.length) html += `<div class="map-cx-item"><strong>Prerequisite links:</strong> ${escHtml(String(lrnPreqs.length))} proposed route constraints.</div>`;
      html += '</div>';
    }

    if (!hasAnyAttemptEvidence && (domMechs.length > 0 || lrnPreqs.length > 0 || fws.length > 0)) {
      html += `
        <div class="map-zone map-locked-study-zone">
          <div class="map-section-title">Locked Study Silhouette</div>
          <p class="map-locked-study-copy">Connections, frameworks, and solved mechanisms stay hidden until at least one room has a cold attempt on record.</p>
        </div>
      `;
    }

    if (hasAnyAttemptEvidence && fws.length > 0) {
      html += '<div class="map-zone zone-5">';
      html += '<div class="map-section-title">Framework Notes</div>';
      html += `<div class="map-fw-card">
        <div class="map-fw-name">${escHtml(`${fws.length} source frameworks held back`)}</div>
        <div class="map-fw-state">They stay out of the draft view so the cold attempt remains generative.</div>
      </div>`;
      html += '</div>';
    }

    mapContent.innerHTML = html;

    destroyKnowledgeGraphController();
    if (drillUi) drillUi.style.display = 'none';
    if (chatHistory) chatHistory.innerHTML = '';
    mountKnowledgeGraphController(data);

    clearSettingsPanel();
    setNavActive('nav-dashboard');
    const settingsView = document.getElementById('settings-view');
    if (libraryView) libraryView.classList.remove('visible');
    if (settingsView) settingsView.classList.remove('visible');
    heroCard.style.display = 'none';
    mapView.classList.add('visible');
    setMapShellOpen(true);
    if (graphContent) graphContent.hidden = false;
    if (window.innerWidth < 900) closeDrawer();
    setMapMode('study');
    restoreStudyResume(concept, data);
  }

  function teardownMapView({ showHero = false, navId = null } = {}) {
    const mapView = document.getElementById('map-view');
    const heroCard = document.querySelector('.hero-card');
    if (drillState.active || drillState.pending || drillState.node) {
      cancelDrill();
    }
    destroyKnowledgeGraphController();
    document.body.classList.remove('is-drilling');
    if (mapView) mapView.classList.remove('visible');
    setMapShellOpen(false);
    if (heroCard) heroCard.style.display = showHero ? 'flex' : 'none';
    if (navId) setNavActive(navId);
  }

  function hideMapView() {
    teardownMapView({ showHero: true, navId: 'nav-dashboard' });
  }

  function hidePrimaryViews() {
    const heroCard = document.querySelector('.hero-card');
    const libraryView = document.getElementById('library-view');
    const settingsView = document.getElementById('settings-view');
    if (heroCard) heroCard.style.display = 'none';
    if (libraryView) libraryView.classList.remove('visible');
    if (settingsView) settingsView.classList.remove('visible');
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
    ['nav-dashboard', 'nav-library', 'nav-settings'].forEach((navId) => {
      const el = document.getElementById(navId);
      if (el) el.classList.toggle('active', navId === currentPrimaryNav);
      
      const bnId = navId.replace('nav-', 'bn-');
      const bnEl = document.getElementById(bnId);
      if (bnEl) bnEl.classList.toggle('active', navId === currentPrimaryNav);
    });
  }

  function showDashboard() {
    setNavActive('nav-dashboard');
    const heroCard = document.querySelector('.hero-card');

    clearSettingsPanel();
    teardownMapView();
    hidePrimaryViews();
    if (heroCard) heroCard.style.display = 'flex';
    if (window.innerWidth < 900) closeDrawer();
  }

  const BUILT_IN_LIBRARY_CONCEPTS = [
    {
      file: 'hermes_agent.json',
      name: 'Hermes Agent',
      kicker: 'Documentation concept',
      summary: 'Reconstruct the Nous Research Hermes Agent system: persistent memory, skills, tools, providers, messaging gateways, environments, automations, and safety boundaries.',
      architecture: 'system description',
      sourceShape: 'dense documentation',
    },
  ];

  async function importLibraryConcept(filename, conceptName) {
    const concepts = loadConcepts();
    const existingConcept = concepts.find((concept) => concept.name === conceptName && concept.graphData);

    if (existingConcept) {
      selectConcept(existingConcept.id);
      hideLibrary();
      showMapView(existingConcept);
      setMapMode('graph');
      return;
    }

    try {
      const data = await loadLibraryConcept(filename);

      const newConcept = {
        id: generateId(),
        name: conceptName,
        createdAt: new Date().toISOString(),
        state: 'growing',
        contentPreview: data?.metadata?.core_thesis || '',
        contentType: 'library',
        contentFilename: 'Hermes Agent documentation',
        graphData: JSON.stringify(data),
      };

      concepts.push(newConcept);
      saveConcepts(concepts);

      renderGrid(concepts);
      renderConceptList(concepts);
      selectConcept(newConcept.id);
      hideLibrary();
      showMapView(newConcept);
      setMapMode('graph');
    } catch (error) {
      console.error('Error loading library concept:', error);
      alert('Failed to load this library concept.');
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
        : (metadata.source_title ? `Map: ${metadata.source_title}` : 'Draft map');

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
    const content = document.getElementById('library-content');

    clearSettingsPanel();
    teardownMapView();
    hidePrimaryViews();
    const concepts = loadConcepts().filter(c => c.graphData);
    const existingConceptNames = new Set(concepts.map((concept) => concept.name));

    let html = `
      <div class="library-kicker">Library</div>

      <div class="library-section">
        <h3 class="library-section-title">Documentation Concepts</h3>
        <p class="library-section-copy">Curated draft paths you can enter without treating the map as learner evidence.</p>
        <div class="library-vault-grid">
          ${BUILT_IN_LIBRARY_CONCEPTS.map((item) => {
            const alreadyAdded = existingConceptNames.has(item.name);
            return `
              <div class="library-card library-card-vault" style="cursor:pointer;" onclick="App.importLibraryConcept('${item.file}', '${item.name}')">
                <div class="library-card-header">
                  <div>
                    <div class="library-card-kicker">${escHtml(item.kicker)}</div>
                    <span class="library-card-name">${escHtml(item.name)}</span>
                  </div>
                  <span class="library-card-state">${alreadyAdded ? 'in library' : 'draft path'}</span>
                </div>
                <p class="library-card-summary">${escHtml(item.summary)}</p>
                <div class="library-card-meta">
                  <span class="library-card-pill">${escHtml(item.architecture)}</span>
                  <span class="library-card-pill">${escHtml(item.sourceShape)}</span>
                </div>
                <div class="library-card-cta">${alreadyAdded ? 'Open concept' : 'Add concept'}</div>
              </div>
            `;
          }).join('')}
        </div>
      </div>
      
      <div class="library-section" style="margin-top: 40px;">
        <h3 class="library-section-title">Your Library</h3>
        <p class="library-section-copy">Draft paths and evidence maps you can reopen.</p>
    `;

    if (concepts.length === 0) {
      html += '<p class="library-empty" style="margin-top:10px;">No draft paths yet. Add a concept on the desk to begin.</p>';
    } else {
      html += `<div class="library-vault-grid">` + concepts.map(c => {
        const meta = getLibraryConceptMeta(c);
        return `
          <div class="library-card library-card-vault" style="cursor:pointer;" onclick="App.openLibraryConcept('${c.id}')">
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

    libraryView.classList.add('visible');
    if (window.innerWidth < 900) closeDrawer();
  }

  function hideLibrary() {
    const libraryView = document.getElementById('library-view');
    if (libraryView) libraryView.classList.remove('visible');
  }

  function openLibraryConcept(id) {
    const concept = activateConceptSelection(id);
    if (!concept) return;
    hideLibrary();
    setNavActive('nav-dashboard');
    if (concept.graphData) {
      showMapView(concept);
      setMapMode('graph');
    } else {
      showDashboard();
    }
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
  void bootstrapAuthUi();
  void refreshDrawerFooter();
  bindMapModeControls();
  renderGrid();
  renderConceptList();
  initHeroSingleInput();

  // Restore selected concept
  const concepts = loadConcepts();
  const pendingResumeState = loadPhaseBResumeState();
  const resumeConcept = pendingResumeState
    ? concepts.find((concept) => concept.id === pendingResumeState.conceptId && concept.graphData)
    : null;
  const toLoad = resumeConcept || concepts.find(c => c.id === getActiveId()) || concepts[0] || null;

  if (pendingResumeState && !resumeConcept) {
    persistPhaseBResumeState(null);
  }

  if (!toLoad) {
    showEmptyState();
  } else {
    activateConceptSelection(toLoad.id);
    if (resumeConcept && resumeConcept.id === toLoad.id) {
      showMapView(toLoad);
    }
  }

  void maybeShowFirstRunWelcome({
    getSession: () => fetchAuthSession(),
    shouldShow: () => loadConcepts().length === 0 && heroStateChipEl?.dataset.state === 'empty',
  });

  sessionState = loadPhaseBSessionState(getActiveId());

  let drillState = {
    active: false,
    messages: [],
    node: null,
    logSessionId: null,
    pending: false,
    probeCount: 0,
    attemptTurnCount: 0,
    helpTurnCount: 0,
    sessionToken: 0,
    _normalizationIdx: 0,
    sessionCompletePending: false,
  };

  function createDrillLogSessionId() {
    if (window.crypto?.randomUUID) return window.crypto.randomUUID();
    return `drill-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  }

  function parseConceptGraphData(concept) {
    if (!concept?.graphData) return null;
    return normalizeGraphData(concept.graphData).graphData;
  }

  function persistActiveConceptGraphData(graphData) {
    const concepts = loadConcepts();
    const activeId = getActiveId();
    const conceptIdx = concepts.findIndex((concept) => concept.id === activeId);
    if (conceptIdx === -1) return null;

    const normalizedGraphData = normalizeGraphData(graphData).graphData;
    concepts[conceptIdx].graphData = JSON.stringify(normalizedGraphData);
    saveConcepts(concepts);
    return concepts[conceptIdx];
  }

  function resolveNodeData(knowledgeMap, nodeId) {
    if (nodeId === 'core-thesis') return knowledgeMap.metadata || {};
    for (const item of knowledgeMap?.backbone || []) {
      if (item?.id === nodeId) return item;
    }
    for (const cluster of knowledgeMap?.clusters || []) {
      if (cluster?.id === nodeId) return cluster;
      for (const subnode of cluster?.subnodes || []) {
        if (subnode?.id === nodeId) return subnode;
      }
    }
    return null;
  }

  function resolveNodeType(knowledgeMap, nodeId, fallbackType = null) {
    if (nodeId === 'core-thesis') return 'core';
    if ((knowledgeMap?.backbone || []).some((item) => item?.id === nodeId)) return 'backbone';
    if ((knowledgeMap?.clusters || []).some((cluster) => cluster?.id === nodeId)) return 'cluster';
    if ((knowledgeMap?.clusters || []).some((cluster) => (cluster?.subnodes || []).some((subnode) => subnode?.id === nodeId))) {
      return 'subnode';
    }
    return fallbackType || 'unknown';
  }

  function resolveClusterId(knowledgeMap, nodeId) {
    if (!nodeId || !knowledgeMap?.clusters) return null;
    const directCluster = (knowledgeMap.clusters || []).find((cluster) => cluster?.id === nodeId);
    if (directCluster) return directCluster.id;
    for (const cluster of knowledgeMap.clusters || []) {
      if ((cluster?.subnodes || []).some((subnode) => subnode?.id === nodeId)) {
        return cluster.id;
      }
    }
    return null;
  }

  function persistSessionState() {
    if (!Array.isArray(sessionState.visitedNodeIds)) {
      sessionState.visitedNodeIds = [];
    }
    sessionState.nodesDrilled = getSessionNodeCount();
    persistPhaseBSessionState(sessionState);
  }

  function getSessionNodeCount() {
    const visitedNodeIds = Array.isArray(sessionState.visitedNodeIds) ? sessionState.visitedNodeIds : [];
    if (visitedNodeIds.length) return visitedNodeIds.length;
    return Number.isFinite(Number(sessionState.nodesDrilled)) ? Number(sessionState.nodesDrilled) : 0;
  }

  function markNodeVisitedThisSession(nodeId) {
    if (!nodeId) return;
    sessionState.visitedNodeIds = Array.isArray(sessionState.visitedNodeIds) ? sessionState.visitedNodeIds : [];
    if (sessionState.visitedNodeIds.includes(nodeId)) return;
    sessionState.visitedNodeIds.push(nodeId);
    sessionState.nodesDrilled = sessionState.visitedNodeIds.length;
  }

  function recordInterleavingEvent(type, conceptId, nodeId, at = new Date().toISOString()) {
    sessionState.events = [
      ...(sessionState.events || []),
      { type, conceptId, nodeId, at },
    ].slice(-100);
    persistSessionState();
  }

  function hasInterleavingEventSince(nodeId, studyCompletedAt) {
    if (!studyCompletedAt) return false;

    const studyCompletedMs = Date.parse(studyCompletedAt);
    if (Number.isNaN(studyCompletedMs)) return false;

    if (!sessionState.startedAt) return true;

    const sessionStartedMs = Date.parse(sessionState.startedAt);
    if (Number.isNaN(sessionStartedMs) || studyCompletedMs < sessionStartedMs) {
      return true;
    }

    return (sessionState.events || []).some((event) => {
      if (!event?.nodeId || event.nodeId === nodeId) return false;
      if (event.type !== 'cold_attempt_complete' && event.type !== 'study_complete') return false;
      const eventMs = Date.parse(event.at || '');
      return !Number.isNaN(eventMs) && eventMs > studyCompletedMs;
    });
  }

  function isReDrillEligible(nodeData, nodeId) {
    if (!nodeData?.re_drill_eligible_after) return false;

    const eligibleAtMs = Date.parse(nodeData.re_drill_eligible_after);
    if (Number.isNaN(eligibleAtMs) || Date.now() < eligibleAtMs) {
      return false;
    }

    return hasInterleavingEventSince(nodeId, nodeData.study_completed_at);
  }

  function isRepairRepsEligible(nodeData) {
    return (
      (nodeData?.drill_status === 'primed' && nodeData?.drill_phase === 're_drill')
      || nodeData?.drill_status === 'drilled'
    );
  }

  function loadRepairRepsHistory() {
    try {
      const parsed = JSON.parse(localStorage.getItem(REPAIR_REPS_STORE_KEY) || '{}');
      return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {};
    } catch {
      return {};
    }
  }

  function saveRepairRepsHistory(history) {
    localStorage.setItem(REPAIR_REPS_STORE_KEY, JSON.stringify(history || {}));
  }

  const REPAIR_REP_PRE_CONFIDENCE_VALUES = new Set(['guessing', 'hunch', 'can_explain']);
  const REPAIR_REP_RATING_VALUES = new Set(['close_match', 'partial', 'missed']);

  function recordRepairRepsCompletion({
    conceptId, nodeId, repCount, promptVersion, gapType,
    answerLengths, ratings, preConfidences, lockDurationsMs,
  }) {
    if (!conceptId || !nodeId) return;
    const history = loadRepairRepsHistory();
    const key = `${conceptId}::${nodeId}`;
    const entries = Array.isArray(history[key]) ? history[key] : [];
    // pre_confidences and lock_durations_ms are practice metadata — a
    // calibration read-out for the learner. They MUST NOT feed scheduling,
    // node prioritization, drill_status, or any graph-truth mutation.
    // See spec §Invariant Boundary.
    history[key] = [
      ...entries,
      {
        completed_at: new Date().toISOString(),
        rep_count: repCount,
        prompt_version: promptVersion,
        gap_type: gapType || null,
        answer_lengths: Array.isArray(answerLengths) ? answerLengths : [],
        ratings: Array.isArray(ratings) ? ratings : [],
        pre_confidences: Array.isArray(preConfidences) ? preConfidences : [],
        lock_durations_ms: Array.isArray(lockDurationsMs) ? lockDurationsMs : [],
      },
    ].slice(-20);
    saveRepairRepsHistory(history);
  }

  function clearRepairRepsStateForConcept(conceptId) {
    if (repairRepsState?.conceptId === conceptId) {
      repairRepsState = null;
    }
    const history = loadRepairRepsHistory();
    const prefix = `${conceptId}::`;
    let changed = false;
    Object.keys(history).forEach((key) => {
      if (!key.startsWith(prefix)) return;
      delete history[key];
      changed = true;
    });
    if (changed) saveRepairRepsHistory(history);
  }

  function getRepairRepsState(nodeId = null) {
    if (!repairRepsState) return null;
    if (nodeId && repairRepsState.nodeId !== nodeId) return null;
    return repairRepsState;
  }

  function setRepairRepsState(nextState) {
    repairRepsState = nextState;
    currentGraphController?.setInteractionMode?.('repair-reps', nextState?.nodeId || activeDrillNode);
  }

  function getSpacingBlockReason(nodeData, nodeId) {
    if (!nodeData?.re_drill_eligible_after) {
      return {
        headline: 'Study this node first',
        body: 'Finish the study step before you try a spaced re-drill.',
      };
    }

    const eligibleAtMs = Date.parse(nodeData.re_drill_eligible_after);
    if (!Number.isNaN(eligibleAtMs) && Date.now() < eligibleAtMs) {
      return {
        headline: 'Work on another node first',
        body: 'This re-drill needs a short buffer before it counts. Work another node, then come back.',
      };
    }

    return {
      headline: 'Interleave one more node first',
      body: 'Finish one other cold attempt or study step before returning here. That buffer helps the graph tell the truth.',
    };
  }

  function getNextReachableInspectTarget(currentNodeId) {
    const graphSuggestion = currentGraphController?.getNextNodeSuggestion?.(currentNodeId);
    if (graphSuggestion?.id) return graphSuggestion;

    const concept = getActiveConcept();
    const graphData = parseConceptGraphData(concept) || {};

    const availableBackbone = (graphData.backbone || []).find((item) => {
      if (!item?.id || item.id === currentNodeId) return false;
      return (
        item.drill_status === 'primed'
        || item.drill_status === 'drilled'
        || item.drill_status === 'solidified'
        || item.drill_status === 'solid'
      );
    });
    if (availableBackbone) {
      return {
        id: availableBackbone.id,
        label: availableBackbone.principle || 'Next branch',
        action: 'review',
      };
    }

    const availableCluster = (graphData.clusters || []).find((cluster) => {
      if (!cluster?.id || cluster.id === currentNodeId) return false;
      const ownerBackboneIds = (graphData.backbone || [])
        .filter((item) => (item?.dependent_clusters || []).includes(cluster.id))
        .map((item) => item.id);
      if (!ownerBackboneIds.length) return Boolean(graphData?.metadata?.drill_status === 'solidified' || graphData?.metadata?.drill_status === 'solid');
      return ownerBackboneIds.some((backboneId) => {
        const backbone = (graphData.backbone || []).find((item) => item?.id === backboneId);
        return backbone?.drill_status === 'primed'
          || backbone?.drill_status === 'drilled'
          || backbone?.drill_status === 'solidified'
          || backbone?.drill_status === 'solid';
      });
    });
    if (availableCluster) {
      return {
        id: availableCluster.id,
        label: availableCluster.label || 'Next cluster',
        action: 'explore',
      };
    }

    for (const cluster of graphData.clusters || []) {
      const candidate = (cluster?.subnodes || []).find((subnode) => {
        if (!subnode?.id || subnode.id === currentNodeId) return false;
        return !subnode.drill_status || subnode.drill_status === 'locked';
      });
      if (candidate) {
        return {
          id: candidate.id,
          label: candidate.label || 'Next node',
          action: 'explore',
        };
      }
    }

    return null;
  }

  function getIncubationAction(nodeContext, nodeData) {
    const nextTarget = getNextReachableInspectTarget(nodeContext.id);
    const blocked = nodeContext.type === 'core' || nodeContext.type === 'backbone'
      ? {
          headline: 'Let this one incubate',
          body: nextTarget
            ? `This idea is primed. Shift to ${nextTarget.label} while this one settles, then come back for spaced re-drill.`
            : 'This idea is primed. Shift to another reachable branch while this one settles, then come back for spaced re-drill.',
        }
      : getSpacingBlockReason(nodeData, nodeContext.id);

    return {
      kind: nextTarget?.id ? 'focus-next' : 'resume-study',
      label: nextTarget?.id
        ? (nodeContext.type === 'core' ? 'Go to next reachable branch' : 'Go to next reachable node')
        : 'Reopen Study',
      targetNodeId: nextTarget?.id || null,
      secondaryAction: isRepairRepsEligible(nodeData)
        ? { kind: 'start-repair-reps', label: 'Start Repair Reps' }
        : null,
      blocked,
    };
  }

  function getNodeInspectAction(nodeContext) {
    const concept = getActiveConcept();
    if (!concept || !nodeContext?.id) return null;

    const graphData = parseConceptGraphData(concept);
    const nodeData = resolveNodeData(graphData || {}, nodeContext.id) || {};
    const drillStatus = nodeData.drill_status || 'locked';
    const drillPhase = nodeData.drill_phase || null;
    const isEligible = isReDrillEligible(nodeData, nodeContext.id);

    if (!nodeContext.available) return null;
    if (drillStatus === 'solidified') return null;

    if (drillStatus === 'primed') {
      if (drillPhase === 'study') {
        return {
          kind: 'resume-study',
          label: 'Resume Study',
        };
      }
      if (isEligible) {
        return {
          kind: 'start-redrill',
          label: 'Start Spaced Re-Drill',
          secondaryAction: isRepairRepsEligible(nodeData)
            ? { kind: 'start-repair-reps', label: 'Start Repair Reps' }
            : null,
        };
      }
      return getIncubationAction(nodeContext, nodeData);
    }

    if (drillStatus === 'drilled') {
      if (isEligible) {
        return {
          kind: 'start-redrill',
          label: 'Start Spaced Re-Drill',
          secondaryAction: isRepairRepsEligible(nodeData)
            ? { kind: 'start-repair-reps', label: 'Start Repair Reps' }
            : null,
        };
      }
      return getIncubationAction(nodeContext, nodeData);
    }

    return {
      kind: 'start-cold-attempt',
      label: nodeContext.type === 'core' ? 'Start With Core Thesis' : 'Start Cold Attempt',
    };
  }

  function runInspectAction(nodeContext, actionKind) {
    if (!nodeContext || !actionKind) return;
    if (actionKind === 'start-repair-reps') {
      startRepairReps(nodeContext);
      return;
    }
    if (actionKind === 'resume-study') {
      reopenStudy(nodeContext);
      return;
    }
    if (actionKind === 'focus-next') {
      const nextTarget = getNextReachableInspectTarget(nodeContext.id);
      if (nextTarget?.id) {
        currentGraphController?.selectNode?.(nextTarget.id);
        return;
      }
      reopenStudy(nodeContext);
      return;
    }
    startDrill(nodeContext);
  }

  function restoreStudyResume(concept, graphData) {
    const resumeState = loadPhaseBResumeState();
    if (!resumeState || resumeState.conceptId !== concept?.id || resumeState.mode !== 'study') {
      return false;
    }

    const nodeData = resolveNodeData(graphData || {}, resumeState.nodeId);
    if (!nodeData || nodeData.drill_phase !== 'study') {
      persistPhaseBResumeState(null);
      return false;
    }

    activeDrillNode = resumeState.nodeId;
    currentGraphController?.setActiveDrillNode?.(activeDrillNode);
    currentGraphController?.setInteractionMode?.('study', activeDrillNode);
    setMapMode('graph');
    return true;
  }

  async function startRepairReps(nodeContext) {
    const concept = getActiveConcept();
    if (!concept || !nodeContext?.id) return;

    const graphData = parseConceptGraphData(concept);
    const nodeData = resolveNodeData(graphData || {}, nodeContext.id) || {};
    if (!isRepairRepsEligible(nodeData)) {
      currentGraphController?.showBlockedMessage?.(
        'Repair Reps are not ready',
        'Finish targeted study first, or return after a non-solid re-drill. Repair work never changes graph truth.'
      );
      return;
    }

    const nodeLabel = nodeContext.fullLabel || nodeContext.label || concept.name || 'Repair target';
    activeDrillNode = nodeContext.id;
    currentGraphController?.setActiveDrillNode?.(activeDrillNode);
    setMapMode('graph');
    setRepairRepsState({
      status: 'loading',
      conceptId: concept.id,
      nodeId: nodeContext.id,
      nodeLabel,
      gapType: nodeData.gap_type || null,
      promptVersion: null,
      reps: [],
      currentIndex: 0,
      revealed: false,
      currentAnswer: '',
      answerLengths: [],
      ratings: [],
      ratingSelected: false,
      isDealing: false,
      isRevealing: false,
      error: null,
      currentPreConfidence: null,
      repStartedAt: null,
      lockedAt: null,
      preConfidences: [],
      lockDurationsMs: [],
    });

    try {
      const payload = await runRepairReps({
        concept_id: concept.id,
        node_id: nodeContext.id,
        node_label: nodeLabel,
        knowledge_map: graphData || {},
        gap_type: nodeData.gap_type || null,
        gap_description: nodeData.gap_description || null,
        count: 3,
        api_key: localStorage.getItem('gemini_key') || undefined,
      });
      const reps = Array.isArray(payload?.reps) ? payload.reps : [];
      if (reps.length !== 3) {
        throw new Error('Repair Reps returned an incomplete practice set.');
      }

      setRepairRepsState({
        status: 'ready',
        conceptId: concept.id,
        nodeId: nodeContext.id,
        nodeLabel,
        gapType: nodeData.gap_type || null,
        promptVersion: payload.prompt_version || 'repair-reps-system-v1',
        reps,
        currentIndex: 0,
        revealed: false,
        currentAnswer: '',
        answerLengths: [],
        ratings: [],
        ratingSelected: false,
        isDealing: true,
        isRevealing: false,
        error: null,
        currentPreConfidence: null,
        repStartedAt: Date.now(),
        lockedAt: null,
        preConfidences: [],
        lockDurationsMs: [],
      });
    } catch (err) {
      console.error(err);
      setRepairRepsState({
        status: 'error',
        conceptId: concept.id,
        nodeId: nodeContext.id,
        nodeLabel,
        gapType: nodeData.gap_type || null,
        promptVersion: null,
        reps: [],
        currentIndex: 0,
        revealed: false,
        currentAnswer: '',
        answerLengths: [],
        ratings: [],
        ratingSelected: false,
        isDealing: false,
        isRevealing: false,
        error: 'Repair Reps could not load. Reopen study and try again later.',
        currentPreConfidence: null,
        repStartedAt: null,
        lockedAt: null,
        preConfidences: [],
        lockDurationsMs: [],
      });
    }
  }

  function revealRepairRep(answerText = '') {
    if (!repairRepsState || repairRepsState.status !== 'ready') return;
    // Idempotency: second call on the same rep is a no-op so lockedAt,
    // preConfidences, and lockDurationsMs are written exactly once.
    if (repairRepsState.revealed === true) return;
    const answer = String(answerText || '').trim();
    if (!answer) return;
    if (!REPAIR_REP_PRE_CONFIDENCE_VALUES.has(repairRepsState.currentPreConfidence)) return;

    const currentIndex = repairRepsState.currentIndex || 0;
    const lockedAt = Date.now();
    const repStartedAt = Number.isFinite(repairRepsState.repStartedAt)
      ? repairRepsState.repStartedAt
      : lockedAt;
    const lockDuration = Math.max(0, lockedAt - repStartedAt);

    const answerLengths = [...(repairRepsState.answerLengths || [])];
    answerLengths[currentIndex] = answer.length;
    const preConfidences = [...(repairRepsState.preConfidences || []), repairRepsState.currentPreConfidence];
    const lockDurationsMs = [...(repairRepsState.lockDurationsMs || []), lockDuration];

    setRepairRepsState({
      ...repairRepsState,
      revealed: true,
      currentAnswer: answer,
      answerLengths,
      preConfidences,
      lockDurationsMs,
      lockedAt,
      ratingSelected: Boolean(repairRepsState.ratings?.[currentIndex]),
      isDealing: false,
      isRevealing: true,
    });
  }

  function setRepairRepPreConfidence(value) {
    if (!repairRepsState || repairRepsState.status !== 'ready') return;
    // Pill is frozen post-reveal. UI also suppresses via aria-disabled + pointer-events,
    // but gate here so direct JS calls cannot mutate the locked-in stance.
    if (repairRepsState.revealed === true) return;
    if (!REPAIR_REP_PRE_CONFIDENCE_VALUES.has(value)) return;
    setRepairRepsState({
      ...repairRepsState,
      currentPreConfidence: value,
    });
  }

  function setRepairRepDraft(value) {
    if (!repairRepsState || repairRepsState.status !== 'ready') return;
    if (repairRepsState.revealed === true) return;
    setRepairRepsState({
      ...repairRepsState,
      currentAnswer: typeof value === 'string' ? value : '',
    });
  }

  function rateRepairRep(rating) {
    if (!repairRepsState || repairRepsState.status !== 'ready' || !repairRepsState.revealed) return;
    if (!REPAIR_REP_RATING_VALUES.has(rating)) return;
    const currentIndex = repairRepsState.currentIndex || 0;
    const ratings = [...(repairRepsState.ratings || [])];
    ratings[currentIndex] = rating;
    setRepairRepsState({
      ...repairRepsState,
      ratings,
      ratingSelected: true,
      isDealing: false,
      isRevealing: false,
    });
  }

  function nextRepairRep() {
    if (!repairRepsState || repairRepsState.status !== 'ready') return;
    if (!repairRepsState.revealed || !repairRepsState.ratingSelected) return;
    const nextIndex = (repairRepsState.currentIndex || 0) + 1;
    if (nextIndex >= (repairRepsState.reps || []).length) {
      recordRepairRepsCompletion({
        conceptId: repairRepsState.conceptId,
        nodeId: repairRepsState.nodeId,
        repCount: repairRepsState.reps.length,
        promptVersion: repairRepsState.promptVersion,
        gapType: repairRepsState.gapType,
        answerLengths: repairRepsState.answerLengths,
        ratings: repairRepsState.ratings,
        preConfidences: repairRepsState.preConfidences,
        lockDurationsMs: repairRepsState.lockDurationsMs,
      });
      setRepairRepsState({
        ...repairRepsState,
        status: 'complete',
        revealed: true,
        isDealing: false,
        isRevealing: false,
      });
      return;
    }

    setRepairRepsState({
      ...repairRepsState,
      currentIndex: nextIndex,
      revealed: false,
      currentAnswer: '',
      ratingSelected: false,
      isDealing: true,
      isRevealing: false,
      currentPreConfidence: null,
      lockedAt: null,
      repStartedAt: Date.now(),
    });
  }

  function exitRepairReps() {
    repairRepsState = null;
    activeDrillNode = null;
    currentGraphController?.clearActiveDrillNode?.();
  }

  function reopenStudy(nodeContext) {
    const concept = getActiveConcept();
    if (!concept || !nodeContext?.id) return;

    activeDrillNode = nodeContext.id;
    persistPhaseBResumeState({ conceptId: concept.id, nodeId: nodeContext.id, mode: 'study' });
    currentGraphController?.setActiveDrillNode?.(activeDrillNode);
    currentGraphController?.setInteractionMode?.('study', activeDrillNode);
    setMapMode('graph');
  }

  function completeStudy(nodeId) {
    const concept = getActiveConcept();
    const graphData = parseConceptGraphData(concept);
    if (!graphData) return;

    let patched = false;
    const studyCompletedAt = new Date().toISOString();
    const fiveMinutes = 5 * 60 * 1000;
    const eligibleAfter = new Date(Date.now() + fiveMinutes).toISOString();

    const applySpacing = (targetObj) => {
      targetObj.study_completed_at = studyCompletedAt;
      targetObj.drill_phase = 're_drill';
      targetObj.re_drill_eligible_after = eligibleAfter;
    };

    if (nodeId === 'core-thesis') {
      if (graphData.metadata) applySpacing(graphData.metadata);
      patched = true;
    }
    (graphData.backbone || []).forEach((item) => {
      if (item?.id === nodeId) {
        applySpacing(item);
        patched = true;
      }
    });
    (graphData.clusters || []).forEach((cluster) => {
      (cluster.subnodes || []).forEach((subnode) => {
        if (subnode?.id === nodeId) {
          applySpacing(subnode);
          patched = true;
        }
      });
    });

    if (patched) {
      persistActiveConceptGraphData(graphData);
      recordInterleavingEvent('study_complete', concept.id, nodeId, studyCompletedAt);
      currentGraphController?.syncFromKnowledgeMap?.(graphData, null);
    }

    drillState.active = false;
    drillState.messages = [];
    drillState.node = null;
    drillState.logSessionId = null;
    drillState.pending = false;
    drillState.probeCount = 0;
    drillState.attemptTurnCount = 0;
    drillState.helpTurnCount = 0;
    drillState.sessionCompletePending = false;
    drillState.sessionToken += 1;
    if (drillUi) drillUi.style.display = 'none';
    if (chatHistory) chatHistory.innerHTML = '';
    if (chatInput) {
      chatInput.value = '';
      chatInput.disabled = true;
    }

    persistPhaseBResumeState(null);
    currentGraphController?.setInteractionMode?.('inspect');
    currentGraphController?.clearActiveDrillNode?.();
    activeDrillNode = null;
  }

  function patchActiveConceptDrillOutcome(result, drillMode) {
    const resolvedColdAttempt = drillMode === 'cold_attempt' && result?.generative_commitment === true;
    const isResolvedSessionComplete = result?.routing === 'SESSION_COMPLETE'
      && (drillMode === 'cold_attempt'
        ? result?.generative_commitment === true
        : Boolean(result?.classification));

    if ((!resolvedColdAttempt && result?.routing !== 'NEXT' && !isResolvedSessionComplete) || !result?.node_id) {
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
    const activeConceptId = concept.id;

    const applyPhaseUpdate = (targetObj) => {
      if (drillMode === 'cold_attempt' && result.generative_commitment === true) {
        targetObj.drill_phase = 'study';
        targetObj.drill_status = 'primed';
        targetObj.cold_attempt_at = drilledAt;
        targetObj.gap_type = null;
        targetObj.gap_description = null;
        recordInterleavingEvent('cold_attempt_complete', activeConceptId, result.node_id, drilledAt);
      } else if (drillMode === 're_drill') {
        if (result.classification === 'solid') {
          targetObj.drill_status = 'solidified';
          targetObj.drill_phase = null;
          targetObj.re_drill_band = result.response_band || null;
          targetObj.gap_type = null;
          targetObj.gap_description = null;
        } else if (result.classification) {
          targetObj.re_drill_count = (targetObj.re_drill_count || 0) + 1;
          targetObj.drill_status = 'drilled';
          targetObj.drill_phase = null;
          targetObj.re_drill_band = null;
          targetObj.gap_type = result.classification;
          targetObj.gap_description = result.gap_description || null;
          // Spacing calculation
          const backoffMinutes = 10 * Math.pow(2, targetObj.re_drill_count - 1);
          targetObj.re_drill_eligible_after = new Date(Date.now() + backoffMinutes * 60000).toISOString();
        }
      }
      targetObj.last_drilled = drilledAt;
    };

    if (result.node_id === 'core-thesis') {
      graphData.metadata = graphData.metadata || {};
      applyPhaseUpdate(graphData.metadata);
      patched = true;
    }

    (graphData.backbone || []).forEach((item) => {
      if (item?.id !== result.node_id) return;
      applyPhaseUpdate(item);
      patched = true;
    });

    (graphData.clusters || []).forEach((cluster) => {
      (cluster.subnodes || []).forEach((subnode) => {
        if (subnode?.id !== result.node_id) return;
        applyPhaseUpdate(subnode);
        patched = true;
      });
    });

    if (!patched) return null;

    const updatedConcept = persistActiveConceptGraphData(graphData);
    console.log(
      `[drill->graph] patched node=${result.node_id} classification=${result.classification ?? 'null'} routing=${result.routing ?? 'null'}`
    );
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
    const turnStartedAt = new Date().toISOString();
    const turnStartedPerf = performance.now();

    drillState.pending = true;
    if (chatInput) chatInput.disabled = true;
    showTypingIndicator();

    const outboundMessages = [...drillState.messages];
    if (userText) {
      outboundMessages.push({ role: 'user', content: userText });
    }
    const clientTurnIndex = outboundMessages.filter((msg) => msg?.role === 'user').length;

    const sessionPhase = !drillState.messages.length && !userText ? 'init' : 'turn';

    const knowledgeMap = parseConceptGraphData(concept) || {};
    const nodeType = resolveNodeType(knowledgeMap, drillState.node.id, drillState.node.type);
    const clusterId = resolveClusterId(knowledgeMap, drillState.node.id);
    const nodeLabel = drillState.node.fullLabel || drillState.node.label || concept.name;
    const bypassSessionLimits = false;

    const apiKey = localStorage.getItem('gemini_key') || undefined;
    const nodeData = resolveNodeData(knowledgeMap, drillState.node.id) || {};
    let drillMode = 'cold_attempt';
    let reDrillCount = nodeData.re_drill_count || 0;
    if (
      nodeData.drill_status === 'drilled'
      || (nodeData.drill_status === 'primed' && nodeData.drill_phase === 're_drill')
    ) {
      drillMode = 're_drill';
    }

    try {
      const data = await runDrillTurn({
        concept_id: concept.id,
        node_id: drillState.node.id,
        node_label: nodeLabel,
        node_mechanism: drillState.node.detail || '',
        drill_session_id: drillState.logSessionId,
        client_turn_index: clientTurnIndex,
        knowledge_map: knowledgeMap,
        messages: outboundMessages,
        session_phase: sessionPhase,
        drill_mode: drillMode,
        re_drill_count: reDrillCount,
        probe_count: drillState.probeCount,
        nodes_drilled: getSessionNodeCount(),
        attempt_turn_count: drillState.attemptTurnCount,
        help_turn_count: drillState.helpTurnCount,
        session_start_iso: sessionState.startedAt,
        bypass_session_limits: bypassSessionLimits,
        api_key: apiKey,
      });
      console.log(
        `[drill] answer_mode=${data?.answer_mode ?? 'null'} classification=${data?.classification ?? 'null'} routing=${data?.routing ?? 'null'} terminated=${Boolean(data?.session_terminated)}`
      );
      console.log('[drill] response', data);
      hideTypingIndicator();

      if (sessionToken !== drillState.sessionToken || !drillState.node) {
        return;
      }

      const graphMutationConcept = patchActiveConceptDrillOutcome(data, drillMode);
      const graphMutated = Boolean(graphMutationConcept);

      const handleVisualTransition = () => {
        if (graphMutated) {
          const freshGraphData = parseConceptGraphData(graphMutationConcept);
          currentGraphController?.syncFromKnowledgeMap?.(freshGraphData, activeDrillNode);
        }

        drillState.messages = outboundMessages;
        drillState.probeCount = data.probe_count ?? drillState.probeCount;
        persistSessionState();
        drillState.attemptTurnCount = data.attempt_turn_count ?? drillState.attemptTurnCount;
        drillState.helpTurnCount = data.help_turn_count ?? drillState.helpTurnCount;
        handleDrillAssistantMessage(data.agent_response || '');
        if (data.agent_response?.trim()) {
          drillState.messages.push({ role: 'assistant', content: data.agent_response.trim() });
        }
        drillState.pending = false;
        drillState.sessionCompletePending = data.routing === 'SESSION_COMPLETE' || Boolean(data.session_terminated);

        const completedColdAttempt = drillMode === 'cold_attempt' && data.generative_commitment === true;
        const completedReDrill = data.routing === 'NEXT'
          || (data.routing === 'SESSION_COMPLETE' && !!data.classification);
        const completedNodeTurn = completedColdAttempt || completedReDrill;
        if (completedColdAttempt) {
          persistPhaseBResumeState({ conceptId: concept.id, nodeId: drillState.node.id, mode: 'study' });
        } else if (completedReDrill) {
          persistPhaseBResumeState(null);
        }
        if (chatInput) {
          chatInput.disabled = completedNodeTurn || !!data.session_terminated;
          if (!completedNodeTurn && !data.session_terminated) {
            chatInput.focus();
          }
        }
        if (completedNodeTurn) {
          currentGraphController?.setInteractionMode?.(drillMode === 'cold_attempt' ? 'study' : 'post-drill', activeDrillNode);
          if (completedColdAttempt) {
            currentGraphController?.flashPrimed?.(activeDrillNode);
          }
          if (drillMode === 're_drill' && data.classification === 'solid') {
            currentGraphController?.flashSolidification?.(activeDrillNode);
          }
        } else {
          currentGraphController?.setInteractionMode?.(drillMode === 'cold_attempt' ? 'cold-attempt-active' : 're-drill-active', activeDrillNode);
        }
      };

      if (drillMode === 'cold_attempt' && data.generative_commitment === true) {
        const normalizationMessages = [
          'You made the first mark. Now the room can show the gap.',
          'That guess gives study something to work against.',
          'The first attempt gives this room a shape.',
          'The room stayed quiet until you tried. Now study has a target.',
        ];
        const msgIdx = drillState._normalizationIdx % normalizationMessages.length;
        drillState._normalizationIdx += 1;
        appendBubble('ai', normalizationMessages[msgIdx]);
        appendFirstColdAttemptCreed();
        if (chatInput) chatInput.disabled = true;
        drillState.pending = true;
        showTypingIndicator();
        setTimeout(() => {
          hideTypingIndicator();
          handleVisualTransition();
        }, 2200);
      } else {
        handleVisualTransition();
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

    const km = parseConceptGraphData(concept) || {};
    if (!nodeContext) {
      nodeContext = { 
        id: 'core-thesis',
        type: 'core',
        fullLabel: 'Core Thesis',
        detail: km?.metadata?.core_thesis || km?.metadata?.thesis || concept.contentPreview || 'Explain this core idea in your own words.',
      };
    }

    const nodeData = resolveNodeData(km, nodeContext.id) || {};
    if (nodeData.drill_status === 'solidified') {
      currentGraphController?.showBlockedMessage?.(
        'Solid evidence already recorded',
        'This room already has a solid spaced reconstruction on record. Pick a node without that record to keep the graph truthful.'
      );
      return;
    }

    if (nodeData.drill_status === 'primed' && nodeData.drill_phase === 'study') {
      reopenStudy(nodeContext);
      return;
    }

    if ((nodeData.drill_status === 'primed' || nodeData.drill_status === 'drilled') && !isReDrillEligible(nodeData, nodeContext.id)) {
      const blockReason = getSpacingBlockReason(nodeData, nodeContext.id);
      currentGraphController?.showBlockedMessage?.(blockReason.headline, blockReason.body);
      return;
    }

    const visitedNodeIds = Array.isArray(sessionState.visitedNodeIds) ? sessionState.visitedNodeIds : [];
    const isNewSessionNode = !visitedNodeIds.includes(nodeContext.id);
    const uniqueNodeCount = getSessionNodeCount();
    const bypassSessionLimits = false;

    if (!bypassSessionLimits && uniqueNodeCount >= 4 && isNewSessionNode) {
      currentGraphController?.showBlockedMessage?.(
        'Session node limit reached',
        'You have drilled 4 nodes this session. This is a good stopping point. Spacing retrieval across sessions improves long-term retention.'
      );
      return;
    }

    if (!bypassSessionLimits && hasDrillSessionTimeLimitElapsed(sessionState.startedAt)) {
      currentGraphController?.setInteractionMode?.('session-complete', activeDrillNode);
      return;
    }

    if (!bypassSessionLimits && (sessionState.retriesByNode[nodeContext.id] || 0) >= 3) {
      currentGraphController?.showBlockedMessage?.(
        'Retrieval ceiling reached',
        'You have attempted this node 3 times this session. Space your attempts and return in a future session.'
      );
      return;
    }

    if (isNewSessionNode) markNodeVisitedThisSession(nodeContext.id);
    sessionState.retriesByNode[nodeContext.id] = (sessionState.retriesByNode[nodeContext.id] || 0) + 1;
    if (!sessionState.startedAt) sessionState.startedAt = new Date().toISOString();
    persistSessionState();

    drillState.active = true;
    drillState.messages = [];
    drillState.node = nodeContext;
    drillState.logSessionId = createDrillLogSessionId();
    drillState.pending = false;
    drillState.probeCount = 0;
    drillState.attemptTurnCount = 0;
    drillState.helpTurnCount = 0;
    drillState.sessionCompletePending = false;
    drillState.sessionToken += 1;
    activeDrillNode = nodeContext?.id || null;

    if (drillUi) drillUi.style.display = 'flex';
    if (chatHistory) chatHistory.innerHTML = '';
    if (chatInput) {
      chatInput.value = '';
      chatInput.disabled = true;
    }
    if (drillTitle) {
      const label = nodeContext?.label || nodeContext?.fullLabel || concept.name;
      drillTitle.textContent = `Active room: ${label}`;
    }

    let initialMode = 'cold-attempt-active';
    if (nodeData.drill_status === 'primed' || nodeData.drill_status === 'drilled' || nodeData.drill_status === 'solidified') {
      initialMode = 're-drill-active';
    }
    if (nodeData.drill_phase === 're_drill') initialMode = 're-drill-active';

    currentGraphController?.setActiveDrillNode?.(activeDrillNode);
    currentGraphController?.setInteractionMode?.(initialMode, activeDrillNode);
    setMapMode('graph');
    document.body.classList.add('is-drilling');

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
    const shouldShowSessionComplete = drillState.sessionCompletePending;
    drillState.sessionToken += 1;
    drillState.active = false;
    drillState.messages = [];
    drillState.node = null;
    drillState.logSessionId = null;
    drillState.pending = false;
    drillState.probeCount = 0;
    drillState.helpTurnCount = 0;
    drillState.sessionCompletePending = false;
    if (drillUi) drillUi.style.display = 'none';
    document.body.classList.remove('is-drilling');
    activeDrillNode = null;
    if (chatHistory) chatHistory.innerHTML = '';
    if (chatInput) {
      chatInput.value = '';
      chatInput.disabled = true;
    }
    currentGraphController?.clearActiveDrillNode?.();
    currentGraphController?.setInteractionMode?.(shouldShowSessionComplete ? 'session-complete' : 'inspect');
    persistPhaseBResumeState(null);
  }

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

  function shouldShowFirstColdAttemptCreed() {
    if (firstColdAttemptCreedShownThisSession) return false;
    firstColdAttemptCreedShownThisSession = true;

    try {
      if (localStorage.getItem(FIRST_COLD_ATTEMPT_CREED_KEY)) return false;
      localStorage.setItem(FIRST_COLD_ATTEMPT_CREED_KEY, new Date().toISOString());
    } catch (err) {
      console.warn('First attempt note state could not be saved.', err);
    }

    return true;
  }

  function appendFirstColdAttemptCreed() {
    if (!chatHistory || !shouldShowFirstColdAttemptCreed()) return;

    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble ai first-attempt-creed';
    bubble.innerHTML = `
      <p class="first-attempt-creed__kicker">what you just did</p>
      <ul class="first-attempt-creed__list">
        <li>
          <span class="first-attempt-creed__diamond" aria-hidden="true"></span>
          <span><strong>You tried first.</strong> The room stayed quiet until your guess existed.</span>
        </li>
        <li>
          <span class="first-attempt-creed__diamond" aria-hidden="true"></span>
          <span><strong>Study has a target now.</strong> Repair the gap this room exposed.</span>
        </li>
        <li>
          <span class="first-attempt-creed__diamond" aria-hidden="true"></span>
          <span><strong>Return later.</strong> Only spaced re-drill can change the record.</span>
        </li>
      </ul>
    `;
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

  function getStoredGeminiKey() {
    try {
      return localStorage.getItem('gemini_key') || '';
    } catch (err) {
      console.warn('Gemini key unavailable.', err);
      return '';
    }
  }

  function setStatusBadge(target, tone, text) {
    if (!target) return;
    target.className = `settings-badge ${tone}`;
    target.textContent = text;
  }

  function renderAccountBody(container, session) {
    if (!container) return;

    if (isGuestSession(session)) {
      container.innerHTML = `
        <div class="settings-account-summary">
          <div class="settings-account-title">Guest mode is active</div>
          <p class="settings-subtext">This browser passed through the login wall as a guest. You can keep trying locally, upgrade into Google sign-in, or exit back to login.</p>
        </div>
        <div class="settings-actions">
          ${session.auth_enabled ? `<a class="auth-link" href="${escHtml(buildLoginHref('/'))}">Continue with Google</a>` : ''}
          <button id="settings-logout-btn" class="settings-test" type="button">Exit Guest</button>
        </div>
      `;
      const logoutBtn = container.querySelector('#settings-logout-btn');
      logoutBtn?.addEventListener('click', async () => {
        logoutBtn.disabled = true;
        try {
          await logout();
          redirectToLogin('/');
        } catch (err) {
          console.warn('Logout failed.', err);
          logoutBtn.disabled = false;
        }
      });
      return;
    }

    if (isIdentifiedUserSession(session)) {
      const label = session.user.first_name || session.user.email || 'Signed in';
      container.innerHTML = `
        <div class="settings-account-summary">
          <div class="settings-account-title">Signed in as ${escHtml(label)}</div>
          <p class="settings-subtext">This browser has an authenticated session. Logging out will send you back to the login decision screen.</p>
        </div>
        <div class="settings-actions">
          <button id="settings-logout-btn" class="settings-test" type="button">Log Out</button>
        </div>
      `;
      const logoutBtn = container.querySelector('#settings-logout-btn');
      logoutBtn?.addEventListener('click', async () => {
        logoutBtn.disabled = true;
        try {
          await logout();
          redirectToLogin('/');
        } catch (err) {
          console.warn('Logout failed.', err);
          logoutBtn.disabled = false;
        }
      });
      return;
    }

    container.innerHTML = `
      <div class="settings-account-summary">
        <div class="settings-account-title">Login required</div>
        <p class="settings-subtext">This app now requires an entry decision before use. Choose Google sign-in or guest mode to continue.</p>
      </div>
      <div class="settings-actions">
        <a class="auth-link" href="${escHtml(buildLoginHref('/'))}">${session?.auth_enabled ? 'Continue with Google' : 'Return to Login'}</a>
      </div>
    `;
  }

  async function renderSettingsView() {
    const settingsContent = document.getElementById('settings-content');
    if (!settingsContent) return;

    settingsContent.innerHTML = `
      <div class="settings-shell">
        <header class="settings-page-header">
          <div class="settings-page-kicker">Settings</div>
          <h2 class="settings-page-title">Setup for a truthful trial run</h2>
          <p class="settings-page-copy">Keep this page focused on what a friends-and-family user needs: backend reachability, Gemini key access, and account state.</p>
        </header>

        <div class="settings-page-grid">
          <article class="settings-page-card">
            <div class="settings-section-header">
              <h4>Runtime Access</h4>
              <span class="settings-dot" id="settings-dot"></span>
            </div>
            <p class="settings-subtext">Backend reachability and key availability are separate checks. A green backend alone does not mean extract or drill is fully working.</p>
            <div class="settings-health-list">
              <div class="settings-health-row">
                <span class="settings-health-label">Backend</span>
                <span id="settings-backend-badge" class="settings-badge neutral">Checking...</span>
              </div>
              <p id="settings-backend-detail" class="settings-subtext">Checking the local API.</p>
              <div class="settings-health-row">
                <span class="settings-health-label">Model Access</span>
                <span id="settings-ai-badge" class="settings-badge neutral">Checking...</span>
              </div>
              <p id="settings-ai-detail" class="settings-subtext">Looking for a server key or a locally saved Gemini key.</p>
            </div>
            <div class="settings-actions">
              <button id="settings-test-btn" class="settings-test" type="button">Check Backend</button>
            </div>
            <div id="settings-status" class="settings-status"></div>
          </article>

          <article class="settings-page-card">
            <div class="settings-section-header">
              <h4>Gemini API Key</h4>
            </div>
            <p class="settings-subtext">This key is stored only in this browser. If the server already has <code>GEMINI_API_KEY</code>, the app can use that instead.</p>
            <div class="settings-input-wrap">
              <input type="password" id="settings-key-input" class="settings-input" placeholder="Paste Gemini API key" autocomplete="off" spellcheck="false">
            </div>
            <div class="settings-actions">
              <button id="settings-key-save" class="settings-test" type="button">Save Key</button>
              <button id="settings-key-remove" class="settings-test" type="button">Remove Key</button>
            </div>
            <div id="settings-key-status" class="settings-status"></div>
          </article>

          <article class="settings-page-card">
            <div class="settings-section-header">
              <h4>Account</h4>
            </div>
            <p class="settings-subtext">Every user now enters through login first. This panel shows whether this browser is signed in, in guest mode, or needs to re-enter through the login wall.</p>
            <div id="settings-account-body" class="settings-account-body">
              <div class="settings-account-summary">
                <div class="settings-account-title">Loading account state...</div>
              </div>
            </div>
          </article>
        </div>
      </div>
    `;

    const dot = settingsContent.querySelector('#settings-dot');
    const testBtn = settingsContent.querySelector('#settings-test-btn');
    const statusBox = settingsContent.querySelector('#settings-status');
    const backendBadge = settingsContent.querySelector('#settings-backend-badge');
    const backendDetail = settingsContent.querySelector('#settings-backend-detail');
    const aiBadge = settingsContent.querySelector('#settings-ai-badge');
    const aiDetail = settingsContent.querySelector('#settings-ai-detail');
    const keyInput = settingsContent.querySelector('#settings-key-input');
    const keySave = settingsContent.querySelector('#settings-key-save');
    const keyRemove = settingsContent.querySelector('#settings-key-remove');
    const keyStatus = settingsContent.querySelector('#settings-key-status');
    const accountBody = settingsContent.querySelector('#settings-account-body');

    const refreshAiAccessUi = ({ backendReachable = false, serverKeyConfigured = false } = {}) => {
      const localKey = getStoredGeminiKey();
      if (!backendReachable) {
        setStatusBadge(aiBadge, 'danger', 'Blocked');
        aiDetail.textContent = 'The backend is unreachable, so extract and drill calls cannot run from this browser yet.';
        return;
      }
      if (serverKeyConfigured) {
        setStatusBadge(aiBadge, 'success', 'Server key active');
        aiDetail.textContent = 'The server has a Gemini key configured. This browser does not need its own key to try extraction.';
        return;
      }
      if (localKey) {
        setStatusBadge(aiBadge, 'success', 'Local key saved');
        aiDetail.textContent = 'This browser has a local Gemini key saved. The first real extract or drill still confirms provider access.';
        return;
      }
      setStatusBadge(aiBadge, 'neutral', 'Needs key');
      aiDetail.textContent = 'No server key is configured and this browser has no saved Gemini key yet.';
    };

    const refreshBackendStatus = async () => {
      testBtn.disabled = true;
      testBtn.textContent = 'Checking...';
      if (statusBox) {
        statusBox.textContent = '';
      }
      try {
        const data = await getHealth();
        applyRuntimeConfig(data);
        dot?.classList.add('connected');
        dot?.classList.remove('error');
        setStatusBadge(backendBadge, 'success', 'Connected');
        backendDetail.textContent = 'The app can reach the backend from this browser.';
        refreshAiAccessUi({ backendReachable: true, serverKeyConfigured: Boolean(data.server_key_configured) });
        if (statusBox) {
          statusBox.textContent = data.server_key_configured
            ? 'Backend reachable. Server-managed Gemini access is available.'
            : 'Backend reachable. Add a local Gemini key below or configure one on the server.';
          statusBox.style.color = 'var(--primary)';
        }
      } catch (err) {
        console.warn('Backend health check failed.', err);
        dot?.classList.add('error');
        dot?.classList.remove('connected');
        setStatusBadge(backendBadge, 'danger', 'Unavailable');
        backendDetail.textContent = 'Cannot reach the backend from this browser. Start the API before trying extract or drill.';
        refreshAiAccessUi({ backendReachable: false, serverKeyConfigured: false });
        if (statusBox) {
          statusBox.textContent = 'Backend check failed. Start the API and try again.';
          statusBox.style.color = 'var(--danger)';
        }
      } finally {
        testBtn.disabled = false;
        testBtn.textContent = 'Check Backend';
      }
    };

    keyInput.value = getStoredGeminiKey();

    keySave?.addEventListener('click', () => {
      const nextValue = keyInput.value.trim();
      if (!nextValue) {
        keyStatus.textContent = 'Enter a Gemini key before saving.';
        keyStatus.style.color = 'var(--danger)';
        return;
      }
      localStorage.setItem('gemini_key', nextValue);
      keyStatus.textContent = 'Key saved to this browser.';
      keyStatus.style.color = 'var(--primary)';
      refreshAiAccessUi({
        backendReachable: backendBadge?.textContent === 'Connected',
        serverKeyConfigured: aiBadge?.textContent === 'Server key active',
      });
    });

    keyRemove?.addEventListener('click', () => {
      localStorage.removeItem('gemini_key');
      keyInput.value = '';
      keyStatus.textContent = 'Local Gemini key removed from this browser.';
      keyStatus.style.color = 'var(--text-sub)';
      refreshAiAccessUi({
        backendReachable: backendBadge?.textContent === 'Connected',
        serverKeyConfigured: aiBadge?.textContent === 'Server key active',
      });
    });

    testBtn?.addEventListener('click', refreshBackendStatus);

    try {
      const session = await fetchAuthSession();
      renderAccountBody(accountBody, session);
    } catch (err) {
      console.warn('Settings account state unavailable.', err);
      renderAccountBody(accountBody, { auth_enabled: false, authenticated: false, guest_mode: false });
    }

    await refreshBackendStatus();
  }

  function showSettings() {
    setNavActive('nav-settings');
    teardownMapView();
    hidePrimaryViews();
    const settingsView = document.getElementById('settings-view');
    if (settingsView) settingsView.classList.add('visible');
    void renderSettingsView();
    if (window.innerWidth < 900) closeDrawer();
  }

  async function refreshDrawerFooter() {
    let session = null;
    try { session = await fetchAuthSession(); } catch (err) { console.warn('Drawer session fetch failed.', err); }
    const isGuest = !!(session && session.guest_mode);
    const authEnabled = !!(session && session.auth_enabled);
    const chip = document.getElementById('drawer-footer-chip');
    const exitBtn = document.getElementById('drawer-exit-btn');
    const signinLink = document.getElementById('drawer-signin-link');
    if (chip) chip.hidden = !isGuest;
    if (exitBtn) exitBtn.hidden = !isGuest;
    if (signinLink) {
      const show = isGuest && authEnabled;
      signinLink.hidden = !show;
      if (show) signinLink.href = buildLoginHref('/');
    }
  }

  async function exitGuestFromDrawer() {
    try { await logout(); } catch (err) { console.warn('Guest exit failed.', err); }
    closeDrawer();
    redirectToLogin('/');
  }

  void refreshRuntimeConfig();

  return {
    toggleDrawer, openDrawer, closeDrawer,
    refreshDrawerFooter,
    exitGuestFromDrawer,
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

    selectTile, selectConcept: (id) => { selectConcept(id); closeDrawer(); },
    reopenStudy,
    completeStudy,
    startRepairReps,
    getRepairRepsState,
    revealRepairRep,
    rateRepairRep,
    nextRepairRep,
    exitRepairReps,
    setRepairRepPreConfidence,
    setRepairRepDraft,
    getNodeInspectAction,
    runInspectAction,
    deleteConcept,
    startAddConcept,
    renderAddTrigger,
    extract, drill, drillFail, drillPass, consolidate,
    fastForward,
    hideMapView, setMapMode, toggleCluster,
    showLibrary, hideLibrary, openLibraryConcept, showDashboard, showSettings,
    importLibraryConcept,
    toggleTheme, runHeroAction
  };

})();

// Two deliberate browser globals (HTML and graph-view bridges).
// Removing either silently breaks production user flows — see below
// for the inventory of readers. Any new global on `window` MUST be
// justified the same way and added to this comment block.
//
// window.App — read by 18 inline onclick="App.foo()" handlers in
// public/index.html (bottom-nav, drawer, hero CTAs, drill controls,
// theme toggle, tile selection). HTML→JS bridge. Phase 2 keeps this
// intentional; a future micro-phase could rewrite the inline handlers
// as addEventListener wiring and drop the global.
//
// window.SocratinkApp — read by 17 call sites in graph-view.js as
// optional-chained intents (e.g. window.SocratinkApp?.startRepairReps,
// ?.runInspectAction, ?.completeStudy). Because every reader uses
// optional chaining (`?.`), removing this assignment will fail
// SILENTLY rather than throw — you would not see an error in the
// console, but repair-reps, study-completion, and inspect flows
// would all become no-ops. Graph-view is the renderer; it never
// owns truth. SocratinkApp is the intent-bridge that lets Cytoscape
// interaction events trigger app.js mutations without a circular
// import. Phase 3 of the lego-ification roadmap formalizes this
// contract (see docs/superpowers/plans/2026-04-26-lego-ification-roadmap.md).
window.App = App;
window.SocratinkApp = App;
