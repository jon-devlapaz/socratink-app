import { Bus } from './bus.js';
import { generateKnowledgeMap } from './ai_service.js';
import {
  playAnim,
  renderGrid as renderDeskGrid,
} from './board-grid.js';
import {
  clearSettingsPanel as clearShellSettingsPanel,
  closeDrawer as closeShellDrawer,
  openDrawer as openShellDrawer,
  renderConceptList as renderShellConceptList,
  toggleDrawer as toggleShellDrawer,
} from './app-shell-ui.js';
import { escHtml } from './html.js';
import {
  describeDoorSource,
  getHeroActionConfig,
  getHeroGuidance,
  getHeroStateLabel,
} from './app-hero.js';
import { createCountdownTimer } from './app-timer.js';
import {
  findConceptEntryById,
  getConceptEntryId,
  renderActiveEntryHtml,
  renderConceptStripHtml,
  selectInitialConceptEntry,
} from './concept-page-view.js?v=6';
import {
  getDefaultPhaseBSessionState,
  getPhaseBSessionStorageKey,
  loadPhaseBResumeState as loadStoredPhaseBResumeState,
  loadPhaseBSessionState as loadStoredPhaseBSessionState,
  persistPhaseBResumeState as persistStoredPhaseBResumeState,
  persistPhaseBSessionState as persistStoredPhaseBSessionState,
} from './phase-b-session.js';
import { buildLibraryHtml } from './library-view.js';
import { createTrainingStore } from './training-store.js';
import {
  buildContentInputUI,
  hasStudyEvidence,
  isBlockedVideoUrl,
  shortOnboardingText,
} from './source-input-ui.js';
import { renderSettingsView as renderSettingsContent } from './settings-view.js';
import {
  applyThemePreference as applyStoredThemePreference,
  getStoredThemePreference as getStoredThemePreferenceFromStorage,
  getToggledTheme,
  normalizeThemePreference,
} from './theme-preference.js';
import {
  getHealth,
  extractUrl,
  runRepairReps,
  runDrillTurn,
} from './api-client.js?v=1';
import {
  bootstrapAuthUi,
  buildLoginHref,
  fetchAuthSession,
  isGuestSession,
  isIdentifiedUserSession,
  logout,
  redirectToLogin,
} from './auth.js?v=3';
import { prefersReducedMotion } from './motion.js';
import {
  STATES, generateId, loadConcepts, saveConcepts, normalizeGraphData,
  getActiveId, setActiveId, getActiveConcept,
  getActiveTileIdx, updateActiveConcept, contentStore
} from './store.js';
import { AudioFX } from './audio.js?v=4';
import { showLaunchPad as _showLaunchPad, runLaunchPadAction as _runLaunchPadAction } from './launch-pad.js';
import { emitTelemetry } from './telemetry.js';

import {
  card, titleEl, descEl, primaryControls, drillControls,
  heroStateChipEl, heroPrimaryActionEl, consolidateControls, timerDisplay, devBtn, drawer, drawerToggle, conceptListEl,
  ignitionView, heroInfo, drillUi, chatHistory, chatInput, drillTitle,
  TILE_IDS, tileEls
} from './dom.js';

const App = (() => {
  const REPAIR_REPS_STORE_KEY = 'learnops_repair_reps_v1';
  const FIRST_COLD_ATTEMPT_CREED_KEY = 'socratink:firstColdAttemptCreedSeen:v1';
  const BOARD_SLOT_COUNT = TILE_IDS.length;
  const LOCAL_QA_CONCEPT_ID = 'local-qa-training-concept';
  const LOCAL_QA_NODE_ID = 'qa-node';
  const LOCAL_REPAIR_QA_CONCEPT_ID = 'qa-repair-concept';
  const LOCAL_REPAIR_QA_NODE_ID = 'repair-node';
  const trainingStore = createTrainingStore();
  let currentGraphController = null;
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

  async function initializeConceptTraining({ conceptId, provenance, sketchText, sketchAt }) {
    await trainingStore.setProvenance(conceptId, provenance);
    if (sketchText) {
      await trainingStore.setSketch(conceptId, {
        text: sketchText,
        at: sketchAt,
      });
    }
  }

  function mapDrillClassificationForTraining(classification) {
    if (classification === 'solid' || classification === 'strong') return 'strong';
    if (classification === 'deep' || classification === 'partial') return 'partial';
    if (classification === 'shallow' || classification === 'thin') return 'thin';
    if (classification === 'misconception' || classification === 'wrong_direction') return 'wrong_direction';
    /* c8 ignore next -- defensive guard for malformed drill API classifications */
    return null;
  }

  function buildTrainingGapsFromDrillResult(result) {
    if (!result?.gap_description) return [];
    return [{
      classification: result.classification || null,
      description: result.gap_description,
    }];
  }

  async function appendTrainingAttemptFromDrillTurn({
    conceptId,
    nodeId,
    userText,
    result,
    at,
  }) {
    const classification = mapDrillClassificationForTraining(result?.classification);
    if (!classification || typeof userText !== 'string' || userText.trim() === '') return null;
    return trainingStore.appendAttempt(conceptId, nodeId, {
      id: `attempt-${at}-${Math.random().toString(36).slice(2, 10)}`,
      at,
      user_text: userText,
      classification,
      gaps: buildTrainingGapsFromDrillResult(result),
      grader_version: result?.prompt_version || result?.grader_version || 'drill-system-v1',
    });
  }

  function isLocalDevHost() {
    return ['localhost', '127.0.0.1', '::1'].includes(window.location.hostname);
  }

  function buildLocalQaConcept(nowMs) {
    const graphData = {
      metadata: {
        core_thesis: 'AI GENERATED CORE THESIS SHOULD NOT APPEAR',
        architecture_type: 'cause_effect',
        difficulty: 'medium',
        source_title: 'QA fixture source',
        starting_map_context: 'Learner rough sketch baseline.',
        map_maturity: 'provisional',
      },
      backbone: [{ id: LOCAL_QA_NODE_ID, label: 'Target node', drill_status: null }],
      clusters: [
        {
          id: 'cluster-1',
          title: 'QA target',
          subnodes: [{ id: LOCAL_QA_NODE_ID, label: 'Target node', drill_status: null }],
        },
      ],
    };
    graphData.backbone[0].purpose = 'Use this entry to name the target mechanism from memory before reading the study note.';
    graphData.backbone[0].study_note = 'The revealed study note names the comparison target after the cold attempt: identify the mechanism, then mark any missing link for repair.';
    graphData.clusters[0].subnodes[0].purpose = graphData.backbone[0].purpose;
    graphData.clusters[0].subnodes[0].study_note = graphData.backbone[0].study_note;

    return {
      id: LOCAL_QA_CONCEPT_ID,
      name: 'Training Truth QA',
      createdAt: nowMs,
      state: 'growing',
      timerStart: null,
      contentPreview: 'SOURCE PREVIEW SHOULD NOT APPEAR',
      contentType: null,
      contentFilename: null,
      sourceUrl: null,
      startingMapContext: 'Learner rough sketch baseline.',
      graphData: JSON.stringify(graphData),
    };
  }

  function buildLocalRepairQaConcept(nowMs) {
    const studyNote = 'Voltage-gated sodium channels open when membrane voltage reaches threshold; the concentration gradient drives flow after the gate opens.';
    const purpose = 'Name what opens the channel before reading the study note.';
    const graphData = {
      metadata: {
        source_title: 'Repair QA source',
        starting_map_context: 'Learner thinks sodium just rushes in.',
        map_maturity: 'provisional',
      },
      backbone: [{
        id: LOCAL_REPAIR_QA_NODE_ID,
        label: 'Sodium channel gate',
        purpose,
        study_note: studyNote,
        drill_status: null,
      }],
      clusters: [{
        id: 'cluster-1',
        subnodes: [{
          id: LOCAL_REPAIR_QA_NODE_ID,
          label: 'Sodium channel gate',
          purpose,
          study_note: studyNote,
          drill_status: null,
        }],
      }],
    };

    return {
      id: LOCAL_REPAIR_QA_CONCEPT_ID,
      name: 'Repair Truth QA',
      createdAt: nowMs,
      state: 'growing',
      timerStart: null,
      contentPreview: 'SOURCE PREVIEW SHOULD NOT APPEAR',
      contentType: null,
      contentFilename: null,
      sourceUrl: null,
      startingMapContext: 'Learner thinks sodium just rushes in.',
      graphData: JSON.stringify(graphData),
    };
  }

  function upsertLocalQaConcept(concepts, concept) {
    const existingIndex = concepts.findIndex((item) => item.id === concept.id);
    /* c8 ignore start -- avoids destructive local QA seeding when the board is full */
    if (existingIndex === -1 && concepts.length >= BOARD_SLOT_COUNT) {
      console.warn('Local QA concept seed skipped: board is at capacity.');
      return null;
    }
    /* c8 ignore stop */
    return existingIndex === -1
      ? [concept, ...concepts]
      : concepts.map((item, index) => index === existingIndex ? concept : item);
  }

  async function seedLocalQaConcept() {
    /* c8 ignore next -- localhost-only guard; exercised positively by e2e */
    if (!isLocalDevHost()) return;

    const concepts = loadConcepts();
    const now = new Date();
    const concept = buildLocalQaConcept(now.getTime());
    const nextConcepts = upsertLocalQaConcept(concepts, concept);
    if (!nextConcepts) return;

    saveConcepts(nextConcepts);
    setActiveId(LOCAL_QA_CONCEPT_ID);
    await trainingStore.saveTraining({
      concept_id: LOCAL_QA_CONCEPT_ID,
      schema_version: 1,
      source_mode: 'source_less',
      grounding: 'learner_sketch',
      source_ref: null,
      sketch: {
        text: 'Learner rough sketch baseline.',
        at: now.toISOString(),
      },
      node_records: {
        [LOCAL_QA_NODE_ID]: {
          attempts: [{
            id: 'local-qa-attempt-1',
            kind: 'cold',
            at: now.toISOString(),
            user_text: 'Learner-owned reconstruction visible in Library.',
            classification: 'strong',
            gaps: [],
            grader_version: 'local-qa',
          }],
          repairs: [],
        },
      },
    });

    renderGrid(nextConcepts);
    renderConceptList(nextConcepts);
    renderIgnitionGate();
    showLibrary();
  }

  async function seedLocalRepairQaConcept() {
    /* c8 ignore next -- localhost-only guard; exercised positively by e2e */
    if (!isLocalDevHost()) return;

    const concepts = loadConcepts();
    const now = new Date();
    const concept = buildLocalRepairQaConcept(now.getTime());
    const nextConcepts = upsertLocalQaConcept(concepts, concept);
    if (!nextConcepts) return;

    saveConcepts(nextConcepts);
    setActiveId(LOCAL_REPAIR_QA_CONCEPT_ID);
    await trainingStore.saveTraining({
      concept_id: LOCAL_REPAIR_QA_CONCEPT_ID,
      schema_version: 1,
      source_mode: 'source_less',
      grounding: 'learner_sketch',
      source_ref: null,
      sketch: {
        text: 'Learner thinks sodium just rushes in.',
        at: now.toISOString(),
      },
      node_records: {
        [LOCAL_REPAIR_QA_NODE_ID]: {
          attempts: [{
            id: 'local-repair-attempt-1',
            kind: 'cold',
            at: now.toISOString(),
            user_text: 'Sodium rushes in because there is more sodium outside.',
            classification: 'thin',
            gaps: [{
              mechanism: 'voltage-gated sodium channels',
              correction: 'Name that threshold opens the channel; the gradient only drives flow after the gate opens.',
            }],
            grader_version: 'local-qa',
          }],
          repairs: [],
        },
      },
    });

    renderGrid(nextConcepts);
    renderConceptList(nextConcepts);
    renderIgnitionGate();
    showLibrary();
  }

  async function refreshRuntimeConfig() {
    try {
      applyRuntimeConfig(await getHealth());
    } catch (err) {
      console.warn('Runtime config unavailable.', err);
    }
  }

  /* c8 ignore start -- pre-existing bypassSessionLimits=true makes this helper unreachable in app flow. */
  function hasDrillSessionTimeLimitElapsed(startedAt) {
    if (!drillSessionTimeLimitSeconds || !startedAt) return false;
    const startedAtMs = Date.parse(startedAt);
    if (Number.isNaN(startedAtMs)) return false;
    return Date.now() - startedAtMs > drillSessionTimeLimitSeconds * 1000;
  }
  /* c8 ignore stop */

  function loadPhaseBSessionState(conceptId = getActiveId()) {
    return loadStoredPhaseBSessionState({ conceptId });
  }

  function persistPhaseBSessionState(sessionState, conceptId = getActiveId()) {
    persistStoredPhaseBSessionState(sessionState, { conceptId });
  }

  function loadPhaseBResumeState() {
    return loadStoredPhaseBResumeState();
  }

  function persistPhaseBResumeState(nextState = null) {
    persistStoredPhaseBResumeState(nextState);
  }

  const themeToggleEl = document.getElementById('theme-toggle');

  function getStoredThemePreference() {
    return getStoredThemePreferenceFromStorage();
  }

  function applyThemePreference(nextPreference, { persist = true } = {}) {
    themePreference = applyStoredThemePreference(nextPreference, {
      persist,
      themeToggleEl,
      onRemount: remountOpenKnowledgeGraphForTheme,
    });
  }

  function toggleTheme() {
    applyThemePreference(getToggledTheme(themePreference));
  }

  // Single entry point for callers that know which theme they want
  // (e.g. the Settings Theme row). applyThemePreference is the
  // canonical implementation; this is just a stable, intent-revealing
  // alias. Both this and toggleTheme write to localStorage["learnops-theme"]
  // and update the corner toggle UI.
  function setTheme(nextPreference) {
    applyThemePreference(normalizeThemePreference(nextPreference));
  }

  // Graph controller stubs: graph-view.js and the cytoscape constellation
  // were deleted in the strip-as-nav port (2026-05-11). These stubs keep
  // the many call sites in startDrill, cancelDrill, and repair-reps from
  // throwing; they will be cleaned up in a follow-up refactor pass.
  function buildKnowledgeGraphMountConfig() { return null; }
  function destroyKnowledgeGraphController() { currentGraphController = null; }
  function mountKnowledgeGraphController() { return null; }
  function captureKnowledgeGraphViewState() { return null; }
  function restoreKnowledgeGraphViewState() {}
  function remountOpenKnowledgeGraphForTheme() {}

  function setMapShellOpen(isOpen) {
    document.body.dataset.mapOpen = isOpen ? 'true' : 'false';
  }

  function renderHero(concept) {
    if (!concept) {
      titleEl.textContent = 'What do you want to understand?';
      // Empty-state desc dropped per silent-surface principle: the iso
      // board's nine empty slots make the affordance obvious; a
      // narrator line "Pick a tile to enter…" is unearned chrome.
      // Populated states still get state-specific guidance (the else
      // branch below still calls getHeroGuidance(concept)).
      descEl.textContent = '';
      if (heroStateChipEl) {
        heroStateChipEl.textContent = 'no concepts yet';
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

  function clearHeroThresholdComposer() {
    // C-prime door: only one text field (concept). Clear it and reset submit.
    const conceptField = document.getElementById('hero-single-input-field');
    if (conceptField) {
      conceptField.value = '';
      conceptField.style.height = '';
    }
    // Reset any pending source selection from the door affordance.
    App._pendingDoorSource = null;
    const sourceAttachBtn = document.getElementById('hero-source-attach');
    const sourcePanel = document.getElementById('hero-source-panel');
    const sourceValue = document.getElementById('hero-source-value');
    if (sourceAttachBtn) {
      sourceAttachBtn.setAttribute('aria-expanded', 'false');
      sourceAttachBtn.textContent = 'add';
    }
    if (sourceValue) sourceValue.textContent = 'none yet';
    if (sourcePanel) {
      sourcePanel.hidden = true;
      sourcePanel.innerHTML = '';
    }
    const submitBtn = document.getElementById('hero-door-submit');
    if (submitBtn instanceof HTMLButtonElement) {
      submitBtn.disabled = true;
    }
  }

  function runHeroAction(evtOrNothing) {
    // C-prime door submit handler. Reads the concept input and the pending
    // source (if the learner expanded the source-attach panel). Branches:
    //   source attached → existing concept-create modal flow (source path)
    //   no source       → write sessionStorage pending shell → showLaunchPad()
    if (evtOrNothing && typeof evtOrNothing.preventDefault === 'function') {
      evtOrNothing.preventDefault();
      const conceptField = document.getElementById('hero-single-input-field');
      const name = (conceptField ? conceptField.value : '').trim();
      if (!name) return false;

      const sourcePayload = App._pendingDoorSource || null;

      if (sourcePayload) {
        // Source-attached path: skip the (now-retired) conversational modal
        // and run the extract pipeline directly. The learner already supplied
        // name + source on the door; the modal's summary-card review step was
        // pure friction. runSourceAttachedSubmit mounts the extract overlay,
        // posts /api/extract (with the URL two-step when applicable), and
        // either navigates to the graph view on success or surfaces the error
        // inline on the door so the learner can retry without a modal remount.
        emitTelemetry('concept_create.door.submit', {
          has_source: true,
          source_type: sourcePayload?.type || null,
          sourceless: false,
        });
        runSourceAttachedSubmit({ name, source: sourcePayload });
        return false;
      }

      // Source-less path: write pending shell to sessionStorage, then navigate
      // to the launch pad. DO NOT call /api/extract here — the launch pad
      // captures the learner's threshold first (C-prime principle #2).
      try {
        sessionStorage.setItem(
          'socratink:pendingShell',
          JSON.stringify({ name, ts: Date.now() }),
        );
      } catch (err) {
        // sessionStorage unavailable (disabled by the browser, quota exceeded, etc.)
        // Surface the error without navigating — the learner must be able to retry.
        console.error('socratink: sessionStorage unavailable', err);
        const errEl = document.getElementById('hero-door-error');
        if (errEl) {
          errEl.textContent = 'Your browser has storage disabled. Enable session storage to continue.';
          errEl.hidden = false;
        }
        return false;
      }
      emitTelemetry('concept_create.door.submit', {
        has_source: false,
        source_type: null,
        sourceless: true,
      });
      App.showLaunchPad();
      return false;
    }

    // Non-form path: the Begin button drives Begin/Extract/Drill/Open-map.
    const concept = getActiveConcept();
    const action = heroPrimaryActionEl?.dataset.action || (!concept ? 'add' : '');
    if (action === 'add') {
      // The conversational creation modal is retired. The Begin button's
      // "add" action lands the learner on the New-concept (ignition) view —
      // the same single canonical entry that the sidebar's New concept link
      // and empty desk tiles use.
      showIgnition();
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

  // ── C-prime door wiring ────────────────────────────────────────────────
  // Wires the concept input → submit-state and the source-attach toggle.
  // Replaces the old two-field initHeroSingleInput (sketch field removed in C-prime).

  // Single source of truth for "is the door ready to submit?".
  // Used by _doorUpdateSubmitState (input handler) AND by
  // renderIgnitionGate (cap-state computation) so the button-disabled
  // logic and the keyboard-submit gate share the same predicate.
  // ≥2 trimmed chars matches the brainstorm spec for the door.
  function _doorReady() {
    const f = document.getElementById('hero-single-input-field');
    return !!f && (f.value || '').trim().length >= 2;
  }
  function _doorUpdateSubmitState() {
    const submitBtn = document.getElementById('hero-door-submit');
    if (!submitBtn) return;
    // Mirror the at-cap gate: if at cap, stay disabled regardless of input.
    const atCap = loadConcepts().length >= BOARD_SLOT_COUNT;
    submitBtn.disabled = atCap || !_doorReady();
  }

  let _sourcePanelGen = 0;

  function _bindDoorSourceAttach() {
    const btn = document.getElementById('hero-source-attach');
    const panel = document.getElementById('hero-source-panel');
    if (!btn || !panel) return;

    btn.addEventListener('click', () => {
      const isOpen = btn.getAttribute('aria-expanded') === 'true';
      const hasSource = !!App._pendingDoorSource;
      const valueEl = document.getElementById('hero-source-value');
      if (isOpen) {
        // Panel is open — collapse and abandon any in-progress source pick.
        // Bump generation so any in-flight dynamic import bails on resolve.
        _sourcePanelGen += 1;
        panel.hidden = true;
        panel.innerHTML = '';
        btn.setAttribute('aria-expanded', 'false');
        btn.textContent = 'add';
        if (valueEl) valueEl.textContent = 'none yet';
        App._pendingDoorSource = null;
        _doorUpdateSubmitState();
      } else if (hasSource) {
        // Panel is closed and a source is attached — the button is the
        // "remove" affordance. Click clears the source without re-opening.
        btn.textContent = 'add';
        if (valueEl) valueEl.textContent = 'none yet';
        App._pendingDoorSource = null;
        _doorUpdateSubmitState();
      } else {
        // Panel is closed and no source — expand and mount the source panel
        // module (extracted in Round B).
        const myGen = ++_sourcePanelGen;
        panel.hidden = false;
        btn.setAttribute('aria-expanded', 'true');
        import('./source-panel.js').then(({ mountSourcePanel }) => {
          // If the user collapsed before the import resolved, bail out.
          if (myGen !== _sourcePanelGen) return;
          mountSourcePanel(panel, {
            onAttach(payload) {
              // Collapse the panel on attach (chip-style); the button label
              // becomes the persistent affordance for clearing.
              App._pendingDoorSource = payload;
              panel.hidden = true;
              panel.innerHTML = '';
              btn.setAttribute('aria-expanded', 'false');
              // Paper-style source-meta line: value span shows source ID,
              // button toggles to "remove" (matches the "add" ↔ "remove"
              // affordance pattern persona-validated in Paper Wave 1).
              btn.textContent = 'remove';
              const v = document.getElementById('hero-source-value');
              if (v) v.textContent = describeDoorSource(payload);
              _doorUpdateSubmitState();
            },
            onCancel() {
              panel.hidden = true;
              panel.innerHTML = '';
              btn.setAttribute('aria-expanded', 'false');
              btn.textContent = 'add';
              const v = document.getElementById('hero-source-value');
              if (v) v.textContent = 'none yet';
              App._pendingDoorSource = null;
              _doorUpdateSubmitState();
            },
          });
        }).catch((err) => {
          // If the module fails to load, collapse gracefully.
          console.error('socratink: failed to load source-panel.js', err);
          panel.hidden = true;
          btn.setAttribute('aria-expanded', 'false');
        });
      }
    });
  }

  function initHeroSingleInput() {
    // C-prime door: one concept textarea + source-attach toggle.
    const conceptField = document.getElementById('hero-single-input-field');
    if (!(conceptField instanceof HTMLTextAreaElement)) return;

    const form = document.getElementById('hero-single-input');

    // Enable/disable submit based on non-empty concept input.
    conceptField.addEventListener('input', _doorUpdateSubmitState);
    _doorUpdateSubmitState();

    // Audio feedback (preserve existing behavior).
    const isPrintable = (e) =>
      !e.metaKey && !e.ctrlKey && !e.altKey && !e.repeat &&
      (e.key.length === 1 || e.key === 'Backspace' || e.key === 'Enter');

    conceptField.addEventListener('focus', () => AudioFX.playFocusTap());
    conceptField.addEventListener('keydown', (e) => {
      if (isPrintable(e)) {
        AudioFX.playKeyClick();
      }
      // Cmd/Ctrl+Enter submits — but only if the same gate the submit
      // button uses says we're ready (≥2 chars trimmed AND not at the
      // 9-concept cap). Previously this check just truthy-checked the
      // trimmed value, which let a 1-char concept submit via keyboard
      // even though the button was correctly disabled, AND let a kb
      // user bypass cap-state by hitting Cmd+Enter.
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        const atCap = loadConcepts().length >= BOARD_SLOT_COUNT;
        if (!atCap && _doorReady()) {
          e.preventDefault();
          form?.requestSubmit?.();
        }
      }
    });

    // Wire the source-attach toggle.
    _bindDoorSourceAttach();

  }


  // ── 8. Grid rendering ──────────────────────────────────────
  function renderGrid(concepts = loadConcepts()) {
    renderDeskGrid({ concepts, tileEls, activeId: getActiveId(), bus: Bus });
  }

  function getSidebarActiveConceptId() {
    return currentPrimaryNav === null ? getActiveId() : null;
  }

  function syncConceptListActiveState() {
    const sidebarActiveId = getSidebarActiveConceptId();
    document.querySelectorAll('#concept-list .concept-item').forEach((item) => {
      const conceptId = item.dataset.conceptId || item.querySelector('.concept-delete')?.dataset.conceptId;
      item.classList.toggle('active', conceptId === sidebarActiveId);
    });
  }

  // ── 10. Drawer ─────────────────────────────────────────────
  function openDrawer() {
    openShellDrawer({ drawer, drawerToggle });
  }
  function closeDrawer() {
    closeShellDrawer({ drawer, drawerToggle });
  }
  function toggleDrawer() {
    toggleShellDrawer({ drawer, drawerToggle, audio: AudioFX });
  }

  if (window.innerWidth >= 900) openDrawer();

  function clearSettingsPanel() {
    clearShellSettingsPanel();
  }

  // ── 11. Concept list render ────────────────────────────────
  function renderConceptList(concepts = loadConcepts()) {
    renderShellConceptList({
      concepts,
      activeId: getSidebarActiveConceptId(),
      conceptListEl,
      onOpenConcept(c) {
        showDashboard();
        selectConcept(c.id);
        if (c.graphData) showMapView(c);
        closeDrawer();
      },
    });
  }

  // ── 12. CRUD ───────────────────────────────────────────────
  // Contract invariant — extraction success path must validate payload shape
  // BEFORE any state mutation. Prevents BLOCKER UX-todo #4 silent-discard
  // where an empty/malformed jsonPayload created a concept anyway. Used by
  // both the launch-pad persistence path and runSourceAttachedSubmit.
  function isValidKnowledgeMap(map) {
    if (!map || typeof map !== 'object') return false;
    if (!Array.isArray(map.backbone) || map.backbone.length === 0) return false;
    if (!Array.isArray(map.clusters)) return false;
    return true;
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
      'socratink is drafting your starting sketch.',
      'Spacing retrieval over time helps short-term recall become more durable.',
      'socratink is structuring the entries.',
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
          <span class="eo-status-label">Drafting</span>
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
        <p class="eo-tip-text">&ldquo;socratink is drafting your starting sketch.&rdquo;</p>
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

    // Derive content fields from source (URL already resolved by concept-create.js
    // — resolvedSource.type was rewritten "url"→"text" before submit, but
    // resolvedSource.url is preserved. Recover the original type for the
    // library card label by checking source.url presence first).
    const sourceText = (source && source.text) ? source.text : '';
    const sourceType = (source && source.url)
      ? 'url'
      : (source && source.type) ? source.type : 'text';
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
    /* c8 ignore start -- source-attached creation requires the live extraction path; the store contract is covered directly. */
    void initializeConceptTraining({
      conceptId: id,
      provenance: {
        source_mode: 'source_attached',
        grounding: 'source',
        source_ref: {
          type: sourceType,
          url: source?.url || null,
          filename: sourceFilename,
        },
      },
      sketchText: startingMapContext,
      sketchAt: new Date(concept.createdAt).toISOString(),
    }).catch((err) => console.warn('Training initialization failed.', err));
    /* c8 ignore stop */
    renderGrid(concepts);
    renderConceptList(concepts);
    renderIgnitionGate();
    showDashboard();
    selectConcept(concept.id);
    clearHeroThresholdComposer();
    closeDrawer();
    overlayHandle.removeOverlay(true);
  }

  // ── persistCreatedConceptFromLaunchPad ────────────────────────────────────
  // Mirrors the persistence phase of finishConceptCreateAfterOverlay for the
  // C-prime launch-pad flow. No overlay to tear down; no source material.
  // Caller (launch-pad.js) clears the pending shell ONLY AFTER this returns
  // without throwing, maintaining the persistence-then-clear ordering contract.
  //
  // Parameters:
  //   map       — ProvisionalMap object returned by /api/extract.
  //   shell     — pending shell { name, ts } read from sessionStorage.
  //   threshold — the learner's raw threshold text (stored as startingMapContext).
  function persistCreatedConceptFromLaunchPad(map, shell, threshold) {
    // Defensive shell guard: refuse to persist a nameless concept rather
    // than create a confusing record with name === undefined / empty if
    // the caller somehow lost track of the pending shell.
    if (!shell || typeof shell.name !== 'string' || shell.name.trim() === '') {
      const err = new Error('launch_pad: invalid shell (missing or empty name)');
      err.code = 'invalid_shell';
      throw err;
    }
    if (!map || typeof map !== 'object') {
      throw new Error('launch_pad: invalid map returned from /api/extract');
    }
    if (!isValidKnowledgeMap(map)) {
      throw new Error('invalid map shape from launch-pad generation');
    }
    const concepts = loadConcepts();
    if (concepts.length >= BOARD_SLOT_COUNT) {
      const err = new Error('board is at capacity (' + BOARD_SLOT_COUNT + ')');
      err.code = 'board_at_capacity';
      throw err;
    }

    const id = generateId();
    const startingMapContext = String(threshold || '').trim().slice(0, 1200);

    const jsonPayload = { ...map, metadata: { ...(map.metadata || {}) } };
    jsonPayload.metadata.starting_map_context = startingMapContext;
    jsonPayload.metadata.map_maturity = 'provisional';

    const concept = {
      id,
      name: shell.name,
      state: 'growing',
      createdAt: Date.now(),
      timerStart: null,
      contentPreview: '',
      contentType: null,
      contentFilename: null,
      sourceUrl: null,
      startingMapContext,
      graphData: JSON.stringify(jsonPayload),
    };
    // No source text — contentStore is not written for source-less concepts.
    concepts.push(concept);
    saveConcepts(concepts);
    void initializeConceptTraining({
      conceptId: id,
      provenance: {
        source_mode: 'source_less',
        grounding: startingMapContext ? 'learner_sketch' : 'ungrounded',
        source_ref: null,
      },
      sketchText: startingMapContext,
      sketchAt: new Date(concept.createdAt).toISOString(),
    }).catch((err) => console.warn('Training initialization failed.', err));
    // Post-save side effects (render, composer-clear, active-concept set) are
    // wrapped in try/catch so a render hiccup doesn't propagate as a
    // persistence failure. The concept is already on disk; treating a render
    // throw as failure would cause runLaunchPadAction to leave the pending
    // shell intact, and a retry would either duplicate the concept or hit
    // BOARD_SLOT_COUNT. Logged but swallowed; the next render cycle picks
    // up the new concept correctly.
    try {
      renderGrid(concepts);
      renderConceptList(concepts);
      renderIgnitionGate();
      clearHeroThresholdComposer();
      // Select the concept so it becomes the active concept for subsequent
      // showMapView/setMapMode calls. setActiveId via activateConceptSelection.
      activateConceptSelection(id);
    } catch (renderErr) {
      console.error(
        'persistCreatedConceptFromLaunchPad: post-save render failed (concept saved successfully)',
        renderErr,
      );
    }
  }

  // ── navigateToGraphViewFromLaunchPad ──────────────────────────────────────
  // Navigate to the graph view after a successful launch-pad submit.
  // Passes opts.fromLaunchPad = true so Round E's skeleton-line hook can
  // detect a fresh-route arrival (Task 8 of the implementation plan).
  //
  // Parameters:
  //   opts — { fromLaunchPad: boolean }
  function renderSkeletonLineIfFresh(opts) {
    const banner = document.getElementById("graph-skeleton-line");
    if (!banner) return;
    if (opts && opts.fromLaunchPad) {
      banner.textContent = "This is the skeleton. It will grow as you reconstruct.";
      banner.hidden = false;
    } else {
      banner.hidden = true;
    }
  }

  function navigateToGraphViewFromLaunchPad(opts) {
    const concept = getActiveConcept();
    if (!concept) {
      // No active concept — likely activateConceptSelection was inside the
      // post-save try/catch in persistCreatedConceptFromLaunchPad and
      // threw. The concept IS saved (saveConcepts ran first), so falling
      // back to the desk lets the user see and click their newly-saved
      // concept rather than getting stuck on the launch-pad with no
      // feedback (the shell was already cleared by the caller).
      console.warn('navigateToGraphViewFromLaunchPad: no active concept; falling back to desk');
      showDashboard();
      return;
    }
    hidePrimaryViews();
    // Pass opts through so showMapView decides skeleton-line state itself
    // (no implicit hide-then-show via teardown ordering).
    showMapView(concept, opts);
  }

  // ── runSourceAttachedSubmit ─────────────────────────────────────────────
  // Direct source-attached extract path. Replaces the conversational modal
  // for the door's "name + source" submit: the learner already typed the
  // concept name and attached source via the inline source-panel, so the
  // modal's chat + summary card was pure ceremony. We mount the extract
  // overlay, run the same submit pipeline as the launch pad / former modal
  // (URL fetch → /api/extract → persist → navigate), and surface failures
  // back on the door so the learner can retry without a modal remount.
  //
  // Inputs:
  //   name   — non-empty trimmed concept name string from the door
  //   source — { type: 'text'|'url'|'file', text?, url?, filename? } payload
  //            captured by the door's source-panel.
  async function runSourceAttachedSubmit({ name, source }) {
    const setDoorError = (msg) => {
      const errEl = document.getElementById('hero-door-error');
      if (errEl) {
        errEl.textContent = msg;
        errEl.hidden = !msg;
      }
    };
    setDoorError('');

    if (loadConcepts().length >= BOARD_SLOT_COUNT) {
      // Library is at the visible board cap. Don't pay for an LLM call.
      setDoorError('The board holds nine concepts. Retire one to start another.');
      return;
    }

    AudioFX.playSubmitChime();
    const overlayHandle = mountExtractOverlay({ name });

    let resolvedSource = source;

    // URL source path: hop through /api/extract-url first to materialise text,
    // mirroring the former modal's doSubmit flow. The /api/extract dispatcher
    // rejects URL sources directly (see main.py _resolve_extract_path).
    if (resolvedSource && resolvedSource.type === 'url' && !resolvedSource.text) {
      try {
        const { extractUrl } = await import('./api-client.js');
        const fetched = await extractUrl({ url: resolvedSource.url });
        resolvedSource = {
          type: 'text',
          text: String(fetched.text || ''),
          url: resolvedSource.url,
        };
      } catch (err) {
        overlayHandle.removeOverlay(false);
        emitTelemetry('concept_create.build_failed', {
          stage: 'submit',
          error_kind: 'url_fetch',
        });
        setDoorError("Couldn't fetch that URL. Check the link and try again.");
        return;
      }
    }

    try {
      const { submitConceptCreate } = await import('./ai_service.js');
      const apiKey =
        (typeof localStorage !== 'undefined' && localStorage.getItem('gemini_key')) ||
        undefined;
      const data = await submitConceptCreate({
        name,
        startingSketch: '',
        source: resolvedSource,
        apiKey,
      });
      const provisionalMap = data.provisional_map || data.knowledge_map || null;
      // Same shape gate the (now-retired) modal handleSubmit applied. Without
      // it a malformed extract result would still persist a corrupt concept.
      if (!isValidKnowledgeMap(provisionalMap)) {
        overlayHandle.removeOverlay(false);
        setDoorError(
          'The extraction service returned an unexpected result. Try again, or attach a different source.',
        );
        return;
      }
      finishConceptCreateAfterOverlay({
        id: generateId(),
        name,
        knowledgeMap: provisionalMap,
        startedAtIso: new Date().toISOString(),
        startedPerf: performance.now(),
        startingSketch: '',
        source: resolvedSource,
        overlayHandle,
      });
    } catch (err) {
      overlayHandle.removeOverlay(false);
      const status = err && err.status;
      const code = err && err.body && err.body.error;
      const message = (err && err.body && err.body.message)
        ? String(err.body.message)
        : 'Something went wrong. Try again.';
      if (status === 422) {
        emitTelemetry('concept_create.build_blocked', {
          reason: code || 'unknown_422',
          origin: 'server',
        });
      } else {
        emitTelemetry('concept_create.build_failed', {
          stage: 'submit',
          error_kind: status ? `http_${status}` : 'transport',
        });
      }
      setDoorError(message);
    }
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
      void trainingStore.deleteTraining(id).catch((err) => {
        /* c8 ignore next -- defensive localStorage deletion failure branch */
        console.warn('Unable to clear deleted concept training evidence.', err);
      });

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
      renderIgnitionGate();
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
      AudioFX.playTileClick();
      selectConcept(concept.id);
      if (concept.graphData) showMapView(concept);
    } else {
      // Empty tile → route straight to the New-concept (ignition) view
      // rather than opening the conversational creation modal. Same surface
      // the sidebar's "New concept" link uses; keeps a single canonical
      // entry into concept creation and avoids the modal layer entirely.
      AudioFX.playTileClick();
      showIgnition();
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
    renderIgnitionGate();
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
    if (btnDrill) btnDrill.textContent = 'Start entry';
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
      showControls(false, false, false, true, true);
      startTimer(remaining);
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
      readFile: _readFile,
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
  const consolidationTimer = createCountdownTimer({
    timerDisplay,
    onComplete: completeConsolidation,
  });

  function startTimer(seconds) { consolidationTimer.start(seconds); }
  function stopTimer() { consolidationTimer.stop(); }
  function completeConsolidation() {
    stopTimer();
    updateActiveConcept({ timerStart: null });
    setState('actualized');
    playAnim('actualize', getActiveTileIdx());
  }
  function fastForward() { consolidationTimer.fastForward(); }

  // ── 16. Map View UI ────────────────────────────────────────

  // Module-level state: which backbone entry is currently shown in the
  // work column. Set on initial mount and updated by setActiveEntry.
  let _activeEntryId = null;

  /**
   * Wire event handlers on the work column after a swap or initial mount.
   * Handles the CTA (start drill) and the threshold re-edit affordance.
   *
   * @param {HTMLElement} docEl - The .concept-page-b2__doc element
   * @param {Object} concept - The full concept object
   * @param {Object} data - Parsed graphData
   */
  function rebindActiveEntryHandlers(docEl, concept, data, training = null) {
    const ctaBtn = docEl.querySelector('.concept-page-b2__entry-cta:not([disabled])');
    if (ctaBtn) {
      ctaBtn.addEventListener('click', () => {
        if (ctaBtn.dataset.activeEntryAction === 'study') {
          void revealStudyForEntry(ctaBtn.dataset.activeEntryId, concept, data);
          return;
        }
        showInlineAttemptForEntry(ctaBtn.dataset.activeEntryId, concept, data, training);
      });
    }
    const attemptBtn = docEl.querySelector('.concept-page-b2__attempt-save');
    if (attemptBtn) {
      attemptBtn.addEventListener('click', () => {
        void submitInlineAttemptForEntry(attemptBtn, concept, data);
      });
    }
    const repairBtn = docEl.querySelector('.concept-page-b2__repair-save');
    if (repairBtn) {
      repairBtn.addEventListener('click', () => {
        void saveRepairForEntry(repairBtn, concept, data);
      });
    }
    docEl.querySelectorAll('[data-edit-threshold]').forEach((link) => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        enterThresholdEditMode(docEl, concept, data, training);
      });
    });
  }

  function renderActiveEntryWorkColumn(entryId, concept, data, training = null, options = {}) {
    const docEl = document.querySelector('.concept-page-b2__doc');
    const backbone = Array.isArray(data?.backbone) ? data.backbone : [];
    const match = findConceptEntryById(backbone, entryId);
    if (!docEl || !match) return;
    docEl.innerHTML = renderActiveEntryHtml(
      match.entry,
      match.index,
      backbone,
      concept,
      data,
      training,
      options,
    );
    rebindActiveEntryHandlers(docEl, concept, data, training);
  }

  function showInlineAttemptForEntry(entryId, concept, data, training = null) {
    if (!entryId || !concept?.id) return;
    renderActiveEntryWorkColumn(entryId, concept, data, training, { attemptEntryId: entryId });
    requestAnimationFrame(() => {
      document.querySelector('.concept-page-b2__attempt-input')?.focus?.();
    });
  }

  async function revealStudyForEntry(entryId, concept, data) {
    if (!entryId || !concept?.id) return;
    const graphData = parseConceptGraphData(concept) || data || {};
    const backbone = Array.isArray(graphData.backbone) ? graphData.backbone : [];
    const entry = findConceptEntryById(backbone, entryId)?.entry || null;
    try {
      const loadedTraining = await trainingStore.loadTraining(concept.id);
      const attempts = loadedTraining?.node_records?.[entryId]?.attempts;
      if (
        entry?.drill_status === 'primed'
        && entry?.drill_phase === 'study'
        && !(Array.isArray(attempts) && attempts.length)
      ) {
        const training = {
          ...(loadedTraining || {}),
          node_records: {
            ...(loadedTraining?.node_records || {}),
            [entryId]: {
              ...(loadedTraining?.node_records?.[entryId] || {}),
              attempts: [],
              repairs: [],
              study_revealed_at: new Date().toISOString(),
            },
          },
        };
        renderActiveEntryWorkColumn(entryId, concept, graphData, training);
        return;
      }
      const training = await trainingStore.setStudyRevealed(
        concept.id,
        entryId,
        new Date().toISOString(),
      );
      const mountEl = document.getElementById('map-content');
      if (mountEl) renderConceptPageB2(mountEl, data, concept, training);
    } catch (err) {
      /* c8 ignore next -- defensive storage/invariant failure branch */
      console.warn('Study reveal failed.', err);
    }
  }

  async function submitInlineAttemptForEntry(button, concept, data) {
    const panel = button?.closest?.('.concept-page-b2__attempt');
    const entryId = button?.dataset?.attemptEntryId || panel?.dataset?.attemptEntryId || null;
    const input = panel?.querySelector?.('.concept-page-b2__attempt-input');
    const errorEl = panel?.querySelector?.('[data-attempt-error]');
    const userText = input?.value || '';
    if (!entryId || !concept?.id) return;
    if (userText.trim() === '') {
      if (errorEl) {
        errorEl.textContent = 'Put down the part you can explain, even if it is incomplete.';
        errorEl.hidden = false;
      }
      input?.focus?.();
      return;
    }
    if (errorEl) errorEl.hidden = true;
    button.disabled = true;

    const graphData = parseConceptGraphData(concept) || data || {};
    const backbone = Array.isArray(graphData.backbone) ? graphData.backbone : [];
    const match = findConceptEntryById(backbone, entryId);
    const entry = match?.entry || {};
    const nodeLabel = entry.label || concept.name || 'Concept entry';
    const at = new Date().toISOString();

    try {
      const loadedTraining = await trainingStore.loadTraining(concept.id);
      const record = loadedTraining?.node_records?.[entryId] || {};
      const attempts = Array.isArray(record.attempts) ? record.attempts : [];
      const legacyStatus = String(entry?.drill_status || '').toLowerCase();
      const legacyAttemptCount = (
        legacyStatus === 'primed'
        || legacyStatus === 'drilled'
        || legacyStatus === 'solidified'
        || legacyStatus === 'solid'
      ) ? 1 : 0;
      const logicalAttemptCount = attempts.length || legacyAttemptCount;
      const drillMode = logicalAttemptCount === 0 ? 'cold_attempt' : 're_drill';
      const result = await runDrillTurn({
        concept_id: concept.id,
        node_id: entryId,
        node_label: nodeLabel,
        node_mechanism: entry.mechanism || entry.principle || entry.study_note || entry.detail || entry.purpose || '',
        drill_session_id: `inline-${concept.id}-${entryId}-${Date.now()}`,
        client_turn_index: logicalAttemptCount + 1,
        knowledge_map: graphData,
        messages: [{ role: 'user', content: userText }],
        session_phase: 'turn',
        drill_mode: drillMode,
        re_drill_count: Math.max(0, logicalAttemptCount - 1),
        probe_count: 0,
        nodes_drilled: 1,
        attempt_turn_count: logicalAttemptCount,
        help_turn_count: 0,
        session_start_iso: at,
        bypass_session_limits: true,
        api_key: localStorage.getItem('gemini_key') || undefined,
      });
      if (getActiveId() !== concept.id) return;
      const training = await appendTrainingAttemptFromDrillTurn({
        conceptId: concept.id,
        nodeId: entryId,
        userText,
        result,
        at,
      });
      if (!training) throw new Error('attempt-not-recorded');
      if (getActiveId() !== concept.id) return;
      const legacyGraphPatchedConcept = drillMode === 're_drill' && !attempts.length
        ? patchActiveConceptDrillOutcome({ ...result, node_id: result?.node_id || entryId }, drillMode)
        : null;
      const renderConcept = legacyGraphPatchedConcept || concept;
      const renderGraphData = legacyGraphPatchedConcept
        ? parseConceptGraphData(legacyGraphPatchedConcept) || graphData
        : graphData;
      const mountEl = document.getElementById('map-content');
      if (mountEl) renderConceptPageB2(mountEl, renderGraphData, renderConcept, training);
    } catch (err) {
      console.warn('Memory attempt failed.', err);
      button.disabled = false;
      if (errorEl) {
        errorEl.textContent = 'The system could not record this yet. Try again.';
        errorEl.hidden = false;
      }
    }
  }

  async function saveRepairForEntry(button, concept, data) {
    const panel = button?.closest?.('.concept-page-b2__repair');
    const entryId = button?.dataset?.repairEntryId || panel?.dataset?.repairEntryId || null;
    const input = panel?.querySelector?.('.concept-page-b2__repair-input');
    const errorEl = panel?.querySelector?.('[data-repair-error]');
    const text = (input?.value || '').trim().slice(0, 1200);
    if (!entryId || !concept?.id) return;
    if (!text) {
      if (errorEl) errorEl.hidden = false;
      input?.focus?.();
      return;
    }
    if (errorEl) errorEl.hidden = true;

    try {
      const training = await trainingStore.appendRepair(concept.id, entryId, {
        id: `repair-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        at: new Date().toISOString(),
        text,
      });
      const mountEl = document.getElementById('map-content');
      if (mountEl) renderConceptPageB2(mountEl, data, concept, training);
    } catch (err) {
      /* c8 ignore next -- defensive storage/invariant failure branch */
      console.warn('Repair save failed.', err);
      if (errorEl) {
        errorEl.textContent = 'Repair could not be saved. Try again.';
        errorEl.hidden = false;
      }
    }
  }

  /**
   * Replace the threshold paragraph with an inline edit textarea + Save/Cancel.
   * On Save: persist the new text to the active concept (both the
   * concept.startingMapContext field and graphData.metadata.starting_map_context)
   * via saveConcepts(), then re-render the threshold + work column.
   *
   * Doctrine: editing the sketch is allowed at any time. The active entry
   * stays the same; only the threshold text changes.
   */
  function enterThresholdEditMode(docEl, concept, data, training = null) {
    const currentText = (concept?.startingMapContext
      || data?.metadata?.starting_map_context
      || data?.metadata?.core_thesis
      || '').trim();
    const thresholdEl = docEl.querySelector('.concept-page-b2__threshold');
    if (!thresholdEl) return;

    const editorHtml = `
      <div class="concept-page-b2__threshold-editor">
        <textarea
          class="concept-page-b2__threshold-input"
          aria-label="Edit your concept sketch"
          rows="4"
          maxlength="1200"
          placeholder="Name the parts, guesses, examples, or confusions you have."
        >${escHtml(currentText)}</textarea>
        <div class="concept-page-b2__threshold-actions">
          <button type="button" class="concept-page-b2__threshold-cancel">Cancel</button>
          <button type="button" class="concept-page-b2__threshold-save">Save sketch</button>
        </div>
      </div>
    `;
    thresholdEl.insertAdjacentHTML('afterend', editorHtml);
    thresholdEl.hidden = true;

    const editorEl = thresholdEl.nextElementSibling;
    const textarea = editorEl.querySelector('.concept-page-b2__threshold-input');
    const cancelBtn = editorEl.querySelector('.concept-page-b2__threshold-cancel');
    const saveBtn = editorEl.querySelector('.concept-page-b2__threshold-save');

    requestAnimationFrame(() => {
      textarea.focus();
      textarea.setSelectionRange(textarea.value.length, textarea.value.length);
    });

    const teardown = () => {
      editorEl.remove();
      thresholdEl.hidden = false;
    };

    cancelBtn.addEventListener('click', teardown);

    textarea.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        teardown();
      } else if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault();
        saveBtn.click();
      }
    });

    saveBtn.addEventListener('click', () => {
      const next = (textarea.value || '').trim().slice(0, 1200);
      const concepts = loadConcepts();
      const liveConcept = concepts.find((c) => c.id === concept.id);
      if (!liveConcept) {
        teardown();
        return;
      }
      liveConcept.startingMapContext = next;
      try {
        const liveData = typeof liveConcept.graphData === 'string'
          ? JSON.parse(liveConcept.graphData)
          : (liveConcept.graphData || {});
        if (!liveData.metadata) liveData.metadata = {};
        liveData.metadata.starting_map_context = next;
        liveConcept.graphData = JSON.stringify(liveData);
      } catch (err) {
        /* c8 ignore next -- defensive malformed graphData fallback */
        console.warn('[concept-page] graphData parse failed; saved startingMapContext only.', err);
      }
      saveConcepts(concepts);

      // Re-render the work column with the fresh data so the quote updates
      // in place. Use the same active entry id we were on.
      const freshData = typeof liveConcept.graphData === 'string'
        ? JSON.parse(liveConcept.graphData)
        : liveConcept.graphData;
      // Mutate the closed-over concept/data references in place so the
      // strip-node click and keyboard handlers wired in renderConceptPageB2
      // see the just-saved threshold on subsequent navigation. Without
      // this, those handlers re-render via setActiveEntry using stale
      // references and the edit appears to vanish until full reload.
      concept.startingMapContext = liveConcept.startingMapContext;
      concept.graphData = liveConcept.graphData;
      if (data) {
        if (!data.metadata) data.metadata = {};
        data.metadata.starting_map_context = next;
        if (freshData?.backbone) data.backbone = freshData.backbone;
        if (freshData?.clusters) data.clusters = freshData.clusters;
        if (freshData?.relationships) data.relationships = freshData.relationships;
      }
      const backbone = Array.isArray(freshData?.backbone) ? freshData.backbone : [];
      const activeIdx = Math.max(
        0,
        backbone.findIndex((n) => (n.id || `entry-${backbone.indexOf(n)}`) === _activeEntryId)
      );
      const activeEntry = backbone[activeIdx] || backbone[0] || { id: 'core-thesis', label: 'Core thesis' };
      docEl.innerHTML = renderActiveEntryHtml(activeEntry, activeIdx, backbone, liveConcept, freshData, training);
      rebindActiveEntryHandlers(docEl, liveConcept, freshData, training);
    });
  }

  /**
   * Swap the work column to show a different backbone entry without
   * rebuilding the whole concept page. Called by strip-node clicks
   * and keyboard arrow nav.
   *
   * Animates: 240ms opacity fade-out, swap, 320ms opacity + 4px
   * translateY fade-in. Does NOT animate layout properties.
   *
   * @param {string} entryId - The id of the backbone entry to show
   * @param {Object} data - Parsed graphData
   * @param {Object} concept - The full concept object
   */
  function setActiveEntry(entryId, data, concept, training = null) {
    if (!data || !entryId) return;
    if (entryId === _activeEntryId) return;

    const backbone = Array.isArray(data.backbone) ? data.backbone : [];
    const activeMatch = findConceptEntryById(backbone, entryId);
    if (!activeMatch) return;
    const newEntry = activeMatch.entry;
    const newIdx = activeMatch.index;

    const mountEl = document.getElementById('map-content');
    if (!mountEl) return;

    // Update strip node active class without full rebuild
    mountEl.querySelectorAll('.concept-strip__node').forEach((g) => {
      const isThisOne = g.getAttribute('data-entry-id') === entryId;
      g.classList.toggle('is-active', isThisOne);
      // Update label: active node shows its label; others hide it
      const text = g.querySelector('text');
      if (isThisOne && !text) {
        const circle = g.querySelector('circle');
        if (circle) {
          const cx = parseFloat(circle.getAttribute('cx'));
          const cy = parseFloat(circle.getAttribute('cy'));
          const labelText = backbone[newIdx]?.label || `entry ${newIdx + 1}`;
          const t = document.createElementNS('http://www.w3.org/2000/svg', 'text');
          t.setAttribute('x', cx);
          t.setAttribute('y', cy + 25);
          t.textContent = labelText;
          g.appendChild(t);
        }
      } else if (!isThisOne && text) {
        text.remove();
      }
      // Bump radius on active
      const circle = g.querySelector('circle');
      if (circle) {
        circle.setAttribute('r', isThisOne ? 9 : (g.classList.contains('concept-strip__node--primed') ? 7 : 6));
      }
    });

    // Update strip overlay label
    const overlayName = mountEl.querySelector('.concept-strip__active-name');
    if (overlayName) {
      overlayName.textContent = `${newEntry.label || 'entry'} · ${newIdx + 1} of ${backbone.length}`;
    }

    // Swap the work column with a fade transition
    const doc = mountEl.querySelector('.concept-page-b2__doc');
    if (!doc) return;
    doc.classList.add('is-fading-out');
    setTimeout(() => {
      doc.innerHTML = renderActiveEntryHtml(newEntry, newIdx, backbone, concept, data, training);
      rebindActiveEntryHandlers(doc, concept, data, training);
      doc.classList.remove('is-fading-out');
      void doc.offsetWidth; // force reflow so the fade-in animates
      doc.classList.add('is-fading-in');
      setTimeout(() => doc.classList.remove('is-fading-in'), 360);
    }, 240);

    _activeEntryId = entryId;
  }

  /**
   * Render the B-2 "Strip + page" concept page layout into #map-content.
   * Replaces the prior Route view card stack.
   *
   * @param {HTMLElement} mountEl - The #map-content element
   * @param {Object} data - Parsed graphData (metadata, backbone, clusters, relationships)
   * @param {Object} concept - The full concept object (for threshold text + name)
   */
  function renderConceptPageB2(mountEl, data, concept, training = null) {
    if (!mountEl || !data) return;
    const backbone = Array.isArray(data.backbone) ? data.backbone : [];

    const {
      entry: activeEntry,
      index: activeIdx,
      id: activeEntryId,
    } = selectInitialConceptEntry(backbone, training);

    // Build the work column HTML via the shared helper
    const stripHtml = renderConceptStripHtml(backbone, activeEntry, activeIdx, training);
    const docHtml = renderActiveEntryHtml(activeEntry, activeIdx, backbone, concept, data, training);

    // Mount the whole thing
    mountEl.classList.add('concept-page-b2');
    mountEl.innerHTML = `
      ${stripHtml}
      <div class="concept-page-b2__doc">
        ${docHtml}
      </div>
    `;

    // Set module-level active entry state
    _activeEntryId = activeEntryId;

    // Wire CTA and re-edit affordance
    const docEl = mountEl.querySelector('.concept-page-b2__doc');
    if (docEl) rebindActiveEntryHandlers(docEl, concept, data, training);

    // Wire strip-node click + keyboard nav
    const stripContainer = mountEl.querySelector('.concept-strip__inner');
    const tooltip = mountEl.querySelector('#concept-strip-tooltip');
    if (stripContainer) {
      stripContainer.addEventListener('click', (e) => {
        const node = e.target.closest('.concept-strip__node');
        if (!node) return;
        const id = node.getAttribute('data-entry-id');
        if (id) setActiveEntry(id, data, concept, training);
      });

      stripContainer.addEventListener('keydown', (e) => {
        const node = e.target.closest('.concept-strip__node');
        if (e.key === 'Enter' || e.key === ' ') {
          const id = node?.getAttribute('data-entry-id');
          if (id) {
            e.preventDefault();
            setActiveEntry(id, data, concept, training);
          }
        } else if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
          e.preventDefault();
          const dir = e.key === 'ArrowLeft' ? -1 : 1;
          const currentMatch = findConceptEntryById(backbone, _activeEntryId);
          const currentIdx = currentMatch ? currentMatch.index : -1;
          const nextIdx = Math.max(0, Math.min(backbone.length - 1, currentIdx + dir));
          const nextNode = backbone[nextIdx];
          if (nextNode) {
            const nextId = getConceptEntryId(nextNode, nextIdx);
            setActiveEntry(nextId, data, concept, training);
            // Move keyboard focus to the new active node
            const nextG = mountEl.querySelector(`.concept-strip__node[data-entry-id="${nextId}"]`);
            nextG?.focus();
          }
        }
      });

      // Hover tooltip for non-active nodes
      if (tooltip) {
        stripContainer.addEventListener('mouseover', (e) => {
          const node = e.target.closest('.concept-strip__node');
          if (!node || node.classList.contains('is-active')) {
            tooltip.removeAttribute('data-visible');
            tooltip.hidden = true;
            return;
          }
          const idx = parseInt(node.getAttribute('data-entry-index'), 10);
          const entry = backbone[idx];
          if (!entry) return;
          const circle = node.querySelector('circle');
          if (!circle) return;
          const containerRect = stripContainer.getBoundingClientRect();
          const circleRect = circle.getBoundingClientRect();
          tooltip.textContent = entry.label || `entry ${idx + 1}`;
          tooltip.style.left = `${circleRect.left + circleRect.width / 2 - containerRect.left}px`;
          tooltip.style.top = `${circleRect.top - containerRect.top - 8}px`;
          tooltip.hidden = false;
          requestAnimationFrame(() => tooltip.setAttribute('data-visible', 'true'));
        });

        stripContainer.addEventListener('mouseleave', () => {
          tooltip.removeAttribute('data-visible');
          setTimeout(() => { tooltip.hidden = true; }, 200);
        });
      }
    }
  }

  function showMapView(concept, opts = {}) {
    const mapView = document.getElementById('map-view');
    const mapContent = document.getElementById('map-content');
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

    const titleEl = document.getElementById('concept-header-title');
    const tagsEl = document.getElementById('concept-header-tags');
    if (titleEl) titleEl.textContent = meta.source_title || concept.name || '';
    if (tagsEl) {
      let tagsHtml = '';
      const stateLabel = getHeroStateLabel(concept.state);
      if (stateLabel && stateLabel !== 'no concepts yet') {
        tagsHtml += `<span class="map-badge state" data-state="${escHtml(concept.state || '')}"><span class="map-badge-dot" aria-hidden="true"></span>${escHtml(stateLabel)}</span>`;
      }
      if (meta.low_density) tagsHtml += `<span class="map-low-density">thin sketch</span>`;
      tagsEl.innerHTML = tagsHtml;
    }

    renderConceptPageB2(mapContent, data, concept);
    void trainingStore.loadTraining(concept.id)
      .then((training) => {
        if (!training) return;
        if (getActiveId() !== concept.id || document.body.dataset.mapOpen !== 'true') return;
        renderConceptPageB2(mapContent, data, concept, training);
      })
      .catch((err) => {
        /* c8 ignore next -- defensive localStorage failure branch */
        console.warn('Training records unavailable for concept page render.', err);
      });

    // Graph view deleted (strip-as-nav port). The knowledge graph controller
    // is retained in case other surfaces still reference it; it becomes a
    // no-op when graph-stage is absent from the DOM.
    destroyKnowledgeGraphController();
    if (drillUi) drillUi.style.display = 'none';
    if (chatHistory) chatHistory.innerHTML = '';

    clearSettingsPanel();
    setNavActive(null);
    const settingsView = document.getElementById('settings-view');
    if (libraryView) libraryView.classList.remove('visible');
    if (settingsView) settingsView.classList.remove('visible');
    heroCard.style.display = 'none';
    mapView.classList.add('visible');
    setMapShellOpen(true);
    if (mapContent) mapContent.hidden = false;
    if (window.innerWidth < 900) closeDrawer();
    restoreStudyResume(concept, data);
    // Skeleton-line is opt-in via opts.fromLaunchPad (default off). Centralised
    // here so callers don't have to hide-then-show after the teardown that
    // hidePrimaryViews triggers.
    renderSkeletonLineIfFresh(opts);
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
    renderSkeletonLineIfFresh({ fromLaunchPad: false });
  }

  function hideMapView() {
    teardownMapView({ showHero: true, navId: 'nav-dashboard' });
  }

  function hidePrimaryViews() {
    const heroCard = document.querySelector('.hero-card');
    const ignitionView = document.getElementById('ignition-view');
    const libraryView = document.getElementById('library-view');
    const settingsView = document.getElementById('settings-view');
    const launchPadView = document.getElementById('launch-pad-view');
    if (heroCard) heroCard.style.display = 'none';
    if (ignitionView) ignitionView.hidden = true;
    if (libraryView) libraryView.classList.remove('visible');
    if (settingsView) settingsView.classList.remove('visible');
    // C-prime launch pad: uses [hidden] attribute (not .visible class) to match
    // its aria-labelledby pattern and align with the HTML hidden attribute.
    if (launchPadView) launchPadView.setAttribute('hidden', '');
  }

  // setMapMode: formerly switched between the Route and Graph views.
  // The Graph view has been deleted (strip-as-nav port, 2026-05-11).
  // Retained as a no-op so call sites in startDrill, restoreStudyResume,
  // etc. continue to compile without a cascade of edits; they will be
  // cleaned up when those flows are refactored in a follow-up.
  function setMapMode() {
    const mapContent = document.getElementById('map-content');
    if (mapContent) mapContent.hidden = false;
  }

  // bindMapModeControls: no longer needed (toggle markup deleted).
  // Retained as a no-op so the initialization block can stay untouched.
  function bindMapModeControls() {}

  function setNavActive(id) {
    currentPrimaryNav = id;
    ['nav-dashboard', 'nav-ignition', 'nav-library', 'nav-settings'].forEach((navId) => {
      const el = document.getElementById(navId);
      if (el) el.classList.toggle('active', navId === currentPrimaryNav);
      
      const bnId = navId.replace('nav-', 'bn-');
      const bnEl = document.getElementById(bnId);
      if (bnEl) bnEl.classList.toggle('active', navId === currentPrimaryNav);
    });
    syncConceptListActiveState();
  }

  function showDashboard() {
    setNavActive('nav-dashboard');
    const heroCard = document.querySelector('.hero-card');

    clearSettingsPanel();
    teardownMapView();
    hidePrimaryViews();
    if (heroCard) heroCard.style.display = 'flex';
    renderDeskDate();
    if (window.innerWidth < 900) closeDrawer();
  }

  function renderDeskDate() {
    const el = document.getElementById('desk-date');
    if (!el) return;
    const d = new Date();
    const months = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'];
    el.textContent = `${months[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}`;
    el.dateTime = d.toISOString().slice(0, 10);
  }

  function showIgnition() {
    setNavActive('nav-ignition');
    clearSettingsPanel();
    teardownMapView();
    hidePrimaryViews();
    document.getElementById('ignition-view').hidden = false;
    renderIgnitionGate();
    if (window.innerWidth < 900) closeDrawer();
    // Focus the writing surface directly; aria-label provides SR announcement.
    const field = document.getElementById('hero-single-input-field');
    if (field) requestAnimationFrame(() => field.focus());
  }

  function hideIgnition() {
    document.getElementById('ignition-view').hidden = true;
  }

  function renderIgnitionGate() {
    const atCap = loadConcepts().length >= BOARD_SLOT_COUNT;
    const gate = document.getElementById('ignition-cap-gate');
    const form = document.getElementById('hero-single-input');
    const field = document.getElementById('hero-single-input-field');
    const submit = document.getElementById('hero-door-submit');
    const sourceAttach = document.getElementById('hero-source-attach');
    const capCta = gate?.querySelector('.ig-button');

    if (gate) gate.hidden = !atCap;
    if (form) form.dataset.state = atCap ? 'locked' : '';

    // Focus handoff MUST run BEFORE disabling the field. Setting
    // .disabled on a focused element synchronously blurs it, which
    // shifts document.activeElement to <body> immediately. If we
    // disable first, the activeElement === field check below always
    // fails and the keyboard user gets stranded with focus on body.
    if (atCap && document.activeElement === field && capCta) {
      /* c8 ignore next -- browser focus handoff is covered by manual QA */
      capCta.focus();
    }

    if (field) field.disabled = atCap;
    // pointer-events:none on the form's data-state="locked" stops mouse
    // input but does not prevent keyboard focus; setting disabled also
    // removes the button from the tab order so kb users can't Enter it
    // and accidentally expand the source panel while at cap.
    if (sourceAttach) sourceAttach.disabled = atCap;
    if (submit) {
      submit.disabled = atCap || !_doorReady();
    }

    ['nav-ignition', 'bn-ignition'].forEach((id) => {
      const el = document.getElementById(id);
      if (!el) return;
      el.classList.toggle('at-cap', atCap);
      el.title = atCap ? 'Library full. Retire a concept to add another.' : '';
    });
  }

  function showLibrary() {
    setNavActive('nav-library');
    const libraryView = document.getElementById('library-view');
    const content = document.getElementById('library-content');

    clearSettingsPanel();
    teardownMapView();
    hidePrimaryViews();
    const concepts = loadConcepts().filter(c => c.graphData);
    const libraryOptions = { showLocalQaSeed: isLocalDevHost() };

    content.innerHTML = buildLibraryHtml(concepts, {}, libraryOptions);

    libraryView.classList.add('visible');
    if (window.innerWidth < 900) closeDrawer();

    if (!concepts.length) return;

    Promise.all(concepts.map(async (concept) => [
      String(concept.id),
      await trainingStore.loadTraining(concept.id),
    ]))
      .then((entries) => {
        const trainingByConceptId = Object.fromEntries(entries.filter(([, training]) => training));
        const currentContent = document.getElementById('library-content');
        const currentLibraryView = document.getElementById('library-view');
        if (!currentContent || !currentLibraryView?.classList.contains('visible')) return;
        currentContent.innerHTML = buildLibraryHtml(concepts, trainingByConceptId, libraryOptions);
      })
      .catch((err) => {
        /* c8 ignore next -- defensive localStorage failure branch */
        console.warn('Training records unavailable for library render.', err);
      });
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

  // Tile hover labels are owned by floating-room-label.js
  // (Floating-UI anchored to each <g class="tile-group">). The legacy
  // #tile-tooltip path with precomputed pixel coords was deleted.

  // Keyboard parity for the SVG <g onclick> handler. SVG groups don't
  // fire click on Enter/Space natively, so wire it explicitly.
  tileEls.forEach((el, idx) => {
    el.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') {
        e.preventDefault();
        selectTile(idx);
      }
    });
  });

  // Side-menu tap sound. Bind to every sidebar nav item AND every
  // bottom-nav item so a click on Desk / Library / Settings / Feedback
  // gets the same paper-tap that Ignition incidentally got via its
  // auto-focus on the hero input. Single throttled fire (150ms) means
  // the nav-click + downstream auto-focus on a view collapses into one.
  document
    .querySelectorAll('.sidebar-nav-item, .bottom-nav-item')
    .forEach((el) => {
      el.addEventListener('click', () => AudioFX.playFocusTap());
    });

  // Render grid first (populates polygon DOM nodes)
  themePreference = getStoredThemePreference();
  applyThemePreference(themePreference, { persist: false });
  void bootstrapAuthUi();
  void refreshDrawerFooter();
  bindMapModeControls();
  renderGrid();
  renderConceptList();
  renderIgnitionGate();
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

  // Tracks the last AI question shown in the chamber so the next learner
  // turn can be paired with it in history. Owned by requestDrillTurn.
  let chamberLastShownQuestion = '';

  // Boot routing runs AFTER drillState is initialized because showIgnition()
  // calls teardownMapView() which reads drillState — TDZ-unsafe earlier.
  if (!toLoad) {
    showIgnition();
  } else {
    activateConceptSelection(toLoad.id);
    if (resumeConcept && resumeConcept.id === toLoad.id) {
      showMapView(toLoad);
    }
  }

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
        headline: 'Study this entry first',
        body: 'Finish the study step before you try a spaced re-drill.',
      };
    }

    const eligibleAtMs = Date.parse(nodeData.re_drill_eligible_after);
    if (!Number.isNaN(eligibleAtMs) && Date.now() < eligibleAtMs) {
      return {
        headline: 'Work on another entry first',
        body: 'This re-drill needs a short buffer before it counts. Work another entry, then come back.',
      };
    }

    return {
      headline: 'Interleave one more entry first',
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
      label: nodeContext.type === 'core' ? 'Start With Core Thesis' : 'Write what you remember',
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
    // TODO(post-launch): re-enable session limits with friendlier copy.
    // Doctrinally the per-entry retry cap (3) and per-session entry cap (4)
    // are real spaced-retrieval guards. For MVP they block the founder's
    // own iteration loop and confuse first learners with "Retrieval ceiling
    // reached" blocks. Re-introduce as soft suggestions, not hard gates.
    const bypassSessionLimits = true;

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
        /* c8 ignore next -- stale async drill responses are timing-dependent */
        return;
      }

      const completedColdAttempt = drillMode === 'cold_attempt' && data.generative_commitment === true;
      const completedReDrill = data.routing === 'NEXT'
        || (data.routing === 'SESSION_COMPLETE' && !!data.classification);
      const completedNodeTurn = completedColdAttempt || completedReDrill;

      if (completedNodeTurn && userText) {
        const training = await appendTrainingAttemptFromDrillTurn({
          conceptId: concept.id,
          nodeId: drillState.node.id,
          userText,
          result: data,
          at: turnStartedAt,
        });
        if (!training) throw new Error('attempt-not-recorded');
      }

      const graphMutationConcept = patchActiveConceptDrillOutcome(data, drillMode);
      const graphMutated = Boolean(graphMutationConcept);

      const handleVisualTransition = async () => {
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
        // Mirror disabled state to the chamber composer. The first AI
        // response also tears down the "preparing your first question"
        // loading placeholder.
        if (window.DrillChamber) {
          window.DrillChamber.setLoading?.(false);
          window.DrillChamber.setComposerEnabled(!(completedNodeTurn || !!data.session_terminated));
        }
        if (completedNodeTurn) {
          currentGraphController?.setInteractionMode?.(drillMode === 'cold_attempt' ? 'study' : 'post-drill', activeDrillNode);
          if (completedColdAttempt) {
            currentGraphController?.flashPrimed?.(activeDrillNode);
          }
          if (drillMode === 're_drill' && data.classification === 'solid') {
            /* c8 ignore next -- optional graph animation; state mutation is covered */
            currentGraphController?.flashSolidification?.(activeDrillNode);
          }
        } else {
          currentGraphController?.setInteractionMode?.(drillMode === 'cold_attempt' ? 'cold-attempt-active' : 're-drill-active', activeDrillNode);
        }
      };

      if (drillMode === 'cold_attempt' && data.generative_commitment === true) {
        const normalizationMessages = [
          'You made the first mark. Now the entry can show the gap.',
          'That guess gives study something to work against.',
          'The first attempt gives this entry a shape.',
          'The entry stayed quiet until you tried. Now study has a target.',
        ];
        const msgIdx = drillState._normalizationIdx % normalizationMessages.length;
        drillState._normalizationIdx += 1;
        appendBubble('ai', normalizationMessages[msgIdx]);
        if (window.DrillChamber && typeof window.DrillChamber.appendCreed === 'function') {
          window.DrillChamber.appendCreed();
        } else if (chatHistory) {
          appendFirstColdAttemptCreed(); // legacy fallback (chat-history present)
        }
        if (chatInput) chatInput.disabled = true;
        drillState.pending = true;
        showTypingIndicator();
        setTimeout(() => {
          hideTypingIndicator();
          handleVisualTransition().catch((err) => {
            /* c8 ignore next -- defensive transition failure branch */
            console.warn('Drill visual transition failed.', err);
          });
        }, 2200);
      } else {
        await handleVisualTransition();
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
        'This entry already has a solid spaced reconstruction on record. Pick an entry without that record to keep the graph truthful.'
      );
      return;
    }

    if (nodeData.drill_status === 'primed' && nodeData.drill_phase === 'study') {
      reopenStudy(nodeContext);
      return;
    }

    // TODO(post-launch): see paired comment ~line 3592. All four guards
    // below (re-drill spacing, 4-entries-per-session, time limit,
    // 3-retries-per-entry) are doctrinally sound but block iteration.
    // Re-introduce as suggestions when we add real telemetry.
    const bypassSessionLimits = true;

    if (!bypassSessionLimits && (nodeData.drill_status === 'primed' || nodeData.drill_status === 'drilled') && !isReDrillEligible(nodeData, nodeContext.id)) {
      const blockReason = getSpacingBlockReason(nodeData, nodeContext.id);
      currentGraphController?.showBlockedMessage?.(blockReason.headline, blockReason.body);
      return;
    }

    const visitedNodeIds = Array.isArray(sessionState.visitedNodeIds) ? sessionState.visitedNodeIds : [];
    const isNewSessionNode = !visitedNodeIds.includes(nodeContext.id);
    const uniqueNodeCount = getSessionNodeCount();

    if (!bypassSessionLimits && uniqueNodeCount >= 4 && isNewSessionNode) {
      currentGraphController?.showBlockedMessage?.(
        'Session node limit reached',
        'You have drilled 4 entries this session. This is a good stopping point. Spacing retrieval across sessions improves long-term retention.'
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
        'You have attempted this entry 3 times this session. Space your attempts and return in a future session.'
      );
      return;
    }

    // sessionState.startedAt MUST be initialised before any /api/drill turn call,
    // independent of bypass mode. Backend's contract for session_phase="turn" is
    // that session_start_iso is non-null. Bypass mode only disables the *enforcement*
    // of session limits (node cap, time cap, retry cap), not the timestamp wiring.
    if (!sessionState.startedAt) sessionState.startedAt = new Date().toISOString();

    if (!bypassSessionLimits) {
      if (isNewSessionNode) markNodeVisitedThisSession(nodeContext.id);
      sessionState.retriesByNode[nodeContext.id] = (sessionState.retriesByNode[nodeContext.id] || 0) + 1;
    }
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
      drillTitle.textContent = `Active entry: ${label}`;
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

    // Show the ironclad chamber view.
    const conceptName = concept?.name || concept?.metadata?.name || 'Concept';
    const entryName = nodeContext.fullLabel || nodeContext.id || 'Entry';
    if (window.DrillChamber) {
      window.DrillChamber.show({
        conceptName,
        entryName,
        question: nodeContext.detail || 'Explain this in your own words.',
      });
      // Seed the last-shown question so the FIRST history pair records
      // the actual question the learner saw (the seed prompt from the
      // node detail). Without this, chamberLastShownQuestion is '' on
      // the first send because appendBubble('ai',...) hasn't run yet
      // (it fires after requestDrillTurn resolves, not before).
      chamberLastShownQuestion = nodeContext.detail || 'Explain this in your own words.';
      // Show "preparing your first question" placeholder while the
      // initial /api/drill round trip lands. The Gemini cold-start can
      // be 5-10s; without a visible state, the disabled composer reads
      // as broken. setLoading flips the placeholder + disables input.
      window.DrillChamber.setLoading?.(true);

      window.DrillChamber.onSend(async (text) => {
        if (!text || drillState.pending) {
          // Belt-and-suspenders with the chamber's own validation:
          // if a turn is mid-flight (drillState.pending) the chamber
          // already disabled its UI synchronously on click. Re-enable
          // here so the user is never left looking at a stuck composer.
          window.DrillChamber.setComposerEnabled(true);
          return;
        }
        // Accumulate the completed turn into history before the next round trip.
        // The AI side is the question we'd just been asking the learner;
        // the learner side is what they just wrote.
        window.DrillChamber.appendHistoryTurn('ai', chamberLastShownQuestion || '');
        window.DrillChamber.appendHistoryTurn('learner', text);
        window.DrillChamber.setComposerEnabled(false);
        try {
          await requestDrillTurn(text);
        } catch (err) {
          console.error(err);
          window.DrillChamber.swapQuestion('The drill service failed to respond. Try again when ready.');
          window.DrillChamber.setComposerEnabled(true);
        }
      });

      window.DrillChamber.onExit(() => {
        cancelDrill();
      });
    }

    requestDrillTurn().catch((err) => {
      console.error(err);
      hideTypingIndicator();
      if (window.DrillChamber) {
        window.DrillChamber.setLoading?.(false);
        window.DrillChamber.swapQuestion('The drill service failed to respond. Try again when ready.');
        window.DrillChamber.setComposerEnabled(true);
      } else {
        appendBubble('ai', 'The drill service failed to respond. Try again when ready.');
      }
      drillState.pending = false;
      if (chatInput) chatInput.disabled = false;
      currentGraphController?.setInteractionMode?.('inspect');
    });
  }

  function cancelDrill() {
    // Hide the chamber first, before any other state cleanup.
    if (window.DrillChamber) {
      window.DrillChamber.hide();
    }

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
    chamberLastShownQuestion = '';
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

    // Restore the concept page view (map + detail).
    const activeConcept = getActiveConcept();
    if (activeConcept) {
      showMapView(activeConcept);
    }
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
    if (role === 'ai' && window.DrillChamber) {
      // Route AI messages through the chamber view instead of the old chat history.
      // Note: composer enable/disable state is set by the calling context
      // (handleVisualTransition), not here, so the completedNodeTurn path is honoured.
      chamberLastShownQuestion = text || '';
      window.DrillChamber.swapQuestion(text || '');
      return;
    }
    // Fallback: render into the legacy embedded chat history if present.
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
          <span><strong>You tried first.</strong> The entry stayed quiet until your guess existed.</span>
        </li>
        <li>
          <span class="first-attempt-creed__diamond" aria-hidden="true"></span>
          <span><strong>Study has a target now.</strong> Repair the gap this entry exposed.</span>
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
          appendBubble('ai', 'The drill service failed to respond. Try again when ready.');
          drillState.pending = false;
          if (chatInput) chatInput.disabled = false;
        });
      }
    });
  }

  async function renderSettingsView() {
    return renderSettingsContent({
      fetchAuthSession,
      isGuestSession,
      isIdentifiedUserSession,
      buildLoginHref,
      logout,
      redirectToLogin,
      getStoredThemePreference,
      setTheme,
      AudioFX,
    });
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
    const signinLink = document.getElementById('drawer-signin-link');
    if (chip) chip.hidden = !isGuest;
    if (signinLink) {
      const show = isGuest && authEnabled;
      signinLink.hidden = !show;
      if (show) signinLink.href = buildLoginHref('/');
    }
  }

  void refreshRuntimeConfig();

  return {
    toggleDrawer, openDrawer, closeDrawer,
    refreshDrawerFooter,
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
    extract, drill, drillFail, drillPass, consolidate,
    fastForward,
    hideMapView, setMapMode, toggleCluster,
    showLibrary, hideLibrary, openLibraryConcept, seedLocalQaConcept, seedLocalRepairQaConcept, showDashboard, showIgnition, showSettings,
    hidePrimaryViews,  // exposed for launch-pad.js to avoid enumerating view IDs directly
    toggleTheme, setTheme, runHeroAction,
    _readFile,  // exposed for concept-create.js's source-panel file uploader
    // C-prime door state: pending source from the door's + add source material panel.
    // Set by the source-attach onAttach callback; cleared by clearHeroThresholdComposer.
    // Null when no source is attached at the door.
    _pendingDoorSource: null,
    // C-prime launch pad — Round D implementation.
    // showLaunchPad is called by the no-source door path in runHeroAction after
    // writing the pending shell to sessionStorage. It hides the ignition view and
    // mounts the threshold-capture surface via launch-pad.js.
    showLaunchPad() { _showLaunchPad(App); },
    // runLaunchPadAction is called by the launch-pad form onsubmit handler.
    // It reads the pending shell, posts to /api/extract, persists, and navigates.
    runLaunchPadAction(event) { return _runLaunchPadAction(event, App); },
    // persistCreatedConceptFromLaunchPad — called by launch-pad.js after a
    // successful /api/extract response. Performs localStorage write, grid
    // refresh, and concept selection. Throws on invalid map so launch-pad.js
    // can leave the pending shell in place for retry.
    persistCreatedConceptFromLaunchPad,
    // navigateToGraphViewFromLaunchPad — called by launch-pad.js after
    // persistence succeeds and the shell has been cleared.
    navigateToGraphViewFromLaunchPad,
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
