import { Bus } from './bus.js';
import {
  createSedaTurnSubmission,
  createSedaSession,
  getSedaSession,
  sessionSourceTextFitsRequest,
  sedaTurnTextFitsRequest,
  sendSedaTurn,
  submitConceptCreate,
} from './ai_service.js?v=10';
import {
  playAnim,
  renderGrid as renderDeskGrid,
} from './board-grid.js?v=5';
import {
  clearSettingsPanel as clearShellSettingsPanel,
  closeDrawer as closeShellDrawer,
  openDrawer as openShellDrawer,
  renderConceptList as renderShellConceptList,
  toggleDrawer as toggleShellDrawer,
} from './app-shell-ui.js?v=2';
import { escHtml } from './html.js';
import {
  getHeroActionConfig,
  getHeroGuidance,
  getHeroStateLabel,
} from './app-hero.js';
import { createCountdownTimer } from './app-timer.js';
import {
  deriveConceptEntries,
  deriveConceptEntryViewState,
  findConceptEntryById,
  getConceptEntryId,
  renderActiveEntryHtml,
  selectInitialConceptEntry,
} from './concept-page-view.js?v=43';
import {
  clearComparisonAcknowledgementsForConcept,
  hasComparisonAcknowledgement,
  markComparisonAcknowledged,
} from './comparison-acknowledgement.js';
import {
  derivePostRepairBridge,
  renderConceptConstellationHtml,
} from './concept-constellation-view.js?v=7';
import { deriveConceptBadge } from './concept-status.js';
import {
  getDefaultPhaseBSessionState,
  getPhaseBSessionStorageKey,
  loadPhaseBResumeState as loadStoredPhaseBResumeState,
  loadPhaseBSessionState as loadStoredPhaseBSessionState,
  persistPhaseBResumeState as persistStoredPhaseBResumeState,
  persistPhaseBSessionState as persistStoredPhaseBSessionState,
} from './phase-b-session.js';
import { buildLibraryHtml } from './library-view.js?v=6';
import { createTrainingStore, TRAINING_SCHEMA_VERSION, TRAINING_STORE_KEY_PREFIX } from './training-store.js';
import {
  hydrateAndSyncLearnerState,
  pushLocalLearnerState,
} from './learner-state-sync.js?v=4';
import {
  listDueForSpaced,
  dueConceptIdSet,
  dueItemsForConcept,
  renderReadyFilterHtml,
  renderDueSelectionHtml,
} from './due-for-spaced.js?v=8';
import { mountSourcePanel } from './source-panel.js?v=4';
import { createDoorSourceController, FILE_SOURCE_TOO_LARGE, PASTED_SOURCE_TOO_LARGE } from './door-source.js?v=4';
import { renderSettingsView as renderSettingsContent } from './settings-view.js?v=1';
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
} from './api-client.js?v=2';
import {
  sedaSurfaceFromResponse,
  visibleSedaPromptFromResponse,
} from './seda-visible-prompt.js?v=5';
import {
  projectCompletedSedaRecord,
  projectLatestSedaAttemptEvent,
} from './seda-evidence-projection.js?v=2';
import {
  bindSourceLessSedaRoute,
  boundSourceLessSedaNodeId,
  boundSourceLessSedaSessionId,
  clearBoundSourceLessSedaRoute,
  hasBoundSourceLessSedaRoute,
  readySourceLessSedaRoute,
} from './seda-route-binding.js?v=1';
import {
  bootstrapAuthUi,
  buildLoginHref,
  fetchAuthSession,
  isGuestSession,
  isIdentifiedUserSession,
  logout,
  requireAppEntrySession,
  redirectToLogin,
} from './auth.js?v=5';
import { prefersReducedMotion } from './motion.js';
import {
  STATES, generateId, loadConcepts, saveConcepts as persistConcepts,
  normalizeGraphData,
  getActiveId, setActiveId, getActiveConcept,
  getActiveTileIdx, updateActiveConcept, contentStore
} from './store.js';
import { AudioFX } from './audio.js?v=4';
import {
  showLaunchPad as _showLaunchPad,
  runLaunchPadAction as _runLaunchPadAction,
} from './launch-pad.js?v=9';
import {
  coldAttemptCompletionLabel,
  nextSedaPromptAfterVerdict,
  sedaCompleteCompletionLabel,
  verdictCopy,
} from './drill-verdict.js?v=6';
import { emitTelemetry } from './telemetry.js';

import {
  card, titleEl, descEl, primaryControls, drillControls,
  heroStateChipEl, heroPrimaryActionEl, consolidateControls, timerDisplay, devBtn, drawer, drawerToggle, conceptListEl,
  ignitionView, heroInfo, drillUi, chatHistory, chatInput, drillTitle,
  TILE_IDS, tileEls
} from './dom.js';

await requireAppEntrySession();

const App = (() => {
  const NORTH_STAR_SESSION_KEY = 'socratink:north-star-session:v1';
  const REPAIR_REPS_STORE_KEY = 'learnops_repair_reps_v1';
  const FIRST_COLD_ATTEMPT_CREED_KEY = 'socratink:firstColdAttemptCreedSeen:v1';
  const SEDA_SESSION_STORE_KEY_PREFIX = 'socratink:seda-session:v1:';
  const BOARD_SLOT_COUNT = TILE_IDS.length;
  const LOCAL_QA_CONCEPT_ID = 'local-qa-training-concept';
  const LOCAL_QA_NODE_ID = 'qa-node';
  const LOCAL_REPAIR_QA_CONCEPT_ID = 'qa-repair-concept';
  const LOCAL_REPAIR_QA_NODE_ID = 'repair-node';
  const LOCAL_REPAIR_QA_NEXT_NODE_ID = 'depolarization-node';
  const DRILL_NODE_MECHANISM_MAX_CHARS = 10000;
  const SOURCE_NORMALIZATION_VERSION = 'source-text-v1';
  const trainingStore = createTrainingStore();
  let learnerStatePushTimer = null;
  let readyFilterActive = false;
  let cachedDueItems = [];
  let northStarSession = null;
  let northStarBusy = false;
  const doorSource = createDoorSourceController({
    normalizationVersion: SOURCE_NORMALIZATION_VERSION,
    sourceFits: (text) => sedaTurnTextFitsRequest(text, northStarSession?.sessionVersion ?? 1),
    onChange: () => _doorUpdateSubmitState(),
  });
  const freshSourceLessConceptIds = new Set();

  function saveConcepts(arr) {
    persistConcepts(arr);
    scheduleLearnerStatePush();
    renderDeskDueSurfaces();
  }

  function scheduleLearnerStatePush() {
    if (learnerStatePushTimer) clearTimeout(learnerStatePushTimer);
    learnerStatePushTimer = setTimeout(() => {
      learnerStatePushTimer = null;
      void pushLearnerStateIfIdentified();
    }, 800);
  }

  const _appendAttempt = trainingStore.appendAttempt.bind(trainingStore);
  const _setStudyRevealed = trainingStore.setStudyRevealed.bind(trainingStore);
  const _appendRepair = trainingStore.appendRepair.bind(trainingStore);
  const _saveTraining = trainingStore.saveTraining.bind(trainingStore);
  const _markRepairChecked = trainingStore.markRepairChecked.bind(trainingStore);
  const _setProvenance = trainingStore.setProvenance.bind(trainingStore);
  const _setSketch = trainingStore.setSketch.bind(trainingStore);
  trainingStore.appendAttempt = async (...args) => {
    const result = await _appendAttempt(...args);
    scheduleLearnerStatePush();
    renderDeskDueSurfaces();
    return result;
  };
  trainingStore.setStudyRevealed = async (...args) => {
    const result = await _setStudyRevealed(...args);
    scheduleLearnerStatePush();
    renderDeskDueSurfaces();
    return result;
  };
  trainingStore.appendRepair = async (...args) => {
    const result = await _appendRepair(...args);
    scheduleLearnerStatePush();
    return result;
  };
  trainingStore.saveTraining = async (...args) => {
    const result = await _saveTraining(...args);
    scheduleLearnerStatePush();
    renderDeskDueSurfaces();
    return result;
  };
  trainingStore.markRepairChecked = async (...args) => {
    const result = await _markRepairChecked(...args);
    scheduleLearnerStatePush();
    return result;
  };
  trainingStore.setProvenance = async (...args) => {
    const result = await _setProvenance(...args);
    scheduleLearnerStatePush();
    return result;
  };
  trainingStore.setSketch = async (...args) => {
    const result = await _setSketch(...args);
    scheduleLearnerStatePush();
    return result;
  };

  let activeDrillNode = null;
  let repairRepsState = null;
  let themePreference = 'light';
  let currentPrimaryNav = 'nav-dashboard';
  let sessionState = getDefaultPhaseBSessionState();
  let drillSessionTimeLimitSeconds = null;
  let firstColdAttemptCreedShownThisSession = false;
  let conceptListRenderSeq = 0;
  let currentMapMode = 'route';

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
    if (Array.isArray(result?.gaps) && result.gaps.length) {
      return result.gaps
        .map((gap) => {
          if (gap && typeof gap === 'object') {
            return {
              mechanism: gap.mechanism || gap.label || gap.type || null,
              correction: gap.correction || gap.description || gap.detail || gap.text || '',
            };
          }
          return {
            mechanism: null,
            correction: String(gap || ''),
          };
        })
        .filter((gap) => gap.correction.trim() !== '');
    }
    if (!result?.gap_description) return [];
    return [{
      classification: result.classification || null,
      description: result.gap_description,
    }];
  }

  function isRecordableDrillAttempt(result) {
    return result?.answer_mode === 'attempt' && result?.score_eligible === true;
  }

  async function appendTrainingAttemptFromDrillTurn({
    conceptId,
    nodeId,
    userText,
    result,
    at,
  }) {
    if (!isRecordableDrillAttempt(result)) return null;
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

  function inlineAttemptNudgeFromDrillResult(result) {
    const isScaffold = result?.routing === 'SCAFFOLD' || result?.answer_mode === 'help_request';
    if (!isScaffold) return null;
    return 'Make one concrete guess before study appears.';
  }

  function isLocalDevHost() {
    return ['localhost', '127.0.0.1', '::1'].includes(window.location.hostname);
  }

  function localQaSeedControlsEnabled() {
    if (!isLocalDevHost()) return false;
    try {
      const params = new URLSearchParams(window.location.search);
      return params.get('localQaSeed') === '1'
        || window.localStorage.getItem('socratink.localQaSeed') === '1';
    } catch (err) {
      /* c8 ignore next -- browser storage denial is fail-closed defensive glue. */
      return false;
    }
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
    const nextStudyNote = 'Sodium entry makes the membrane voltage less negative and begins depolarization.';
    const nextPurpose = 'Explain what changes the membrane voltage from memory.';
    const graphData = {
      metadata: {
        source_title: 'Repair QA source',
        starting_map_context: 'I think sodium just rushes in.',
        map_maturity: 'provisional',
      },
      backbone: [
        {
          id: LOCAL_REPAIR_QA_NODE_ID,
          label: 'Sodium channel gate',
          purpose,
          study_note: studyNote,
          drill_status: null,
        },
        {
          id: LOCAL_REPAIR_QA_NEXT_NODE_ID,
          label: 'Membrane depolarization',
          purpose: nextPurpose,
          study_note: nextStudyNote,
          drill_status: null,
        },
      ],
      clusters: [{
        id: 'cluster-1',
        subnodes: [
          {
            id: LOCAL_REPAIR_QA_NODE_ID,
            label: 'Sodium channel gate',
            purpose,
            study_note: studyNote,
            drill_status: null,
          },
          {
            id: LOCAL_REPAIR_QA_NEXT_NODE_ID,
            label: 'Membrane depolarization',
            purpose: nextPurpose,
            study_note: nextStudyNote,
            drill_status: null,
          },
        ],
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
      startingMapContext: 'I think sodium just rushes in.',
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
      schema_version: TRAINING_SCHEMA_VERSION,
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
      schema_version: TRAINING_SCHEMA_VERSION,
      source_mode: 'source_less',
      grounding: 'learner_sketch',
      source_ref: null,
      sketch: {
        text: 'I think sodium just rushes in.',
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

  function setMapShellOpen(isOpen) {
    document.body.dataset.mapOpen = isOpen ? 'true' : 'false';
  }

  function conceptViewSwitchButton() {
    return document.getElementById('concept-view-switch');
  }

  function hasActiveEntryReconstructionEvidence(training) {
    const records = training?.node_records && typeof training.node_records === 'object'
      ? training.node_records
      : {};
    const record = _activeEntryId ? records[_activeEntryId] : null;
    if (!record || typeof record !== 'object') return false;
    if (Array.isArray(record.attempts) && record.attempts.length > 0) return true;
    return Boolean(record.attempt_text || record.latest_attempt || record.study_revealed_at);
  }

  function hasActiveAttemptDraft() {
    const input = document.querySelector('.concept-page-b2__attempt-input');
    return Boolean((input?.value || '').trim());
  }

  function normalizeSourceModeToken(value) {
    const mode = typeof value === 'string' ? value.trim() : '';
    return mode === 'source_less' || mode === 'source_attached' ? mode : '';
  }

  function isSourceLessConcept(concept, data, training = null) {
    const explicitMode = normalizeSourceModeToken(training?.source_mode)
      || normalizeSourceModeToken(concept?.sourceMode)
      || normalizeSourceModeToken(concept?.source_mode)
      || normalizeSourceModeToken(data?.metadata?.source_mode);
    if (explicitMode) return explicitMode === 'source_less';

    const hasNullContentType = Object.prototype.hasOwnProperty.call(concept || {}, 'contentType')
      && concept?.contentType === null;
    const hasNullSourceUrl = Object.prototype.hasOwnProperty.call(concept || {}, 'sourceUrl')
      && concept?.sourceUrl === null;
    const hasSourceMarker = Boolean(
      (concept?.contentType || '').trim?.()
      || (concept?.contentFilename || '').trim?.()
      || (concept?.sourceUrl || '').trim?.()
      || (data?.metadata?.source_url || '').trim?.()
    );
    return hasNullContentType && hasNullSourceUrl && !hasSourceMarker;
  }

  function setActiveConceptSourceMode(concept, data, training = null) {
    document.body.dataset.conceptSourceMode = isSourceLessConcept(concept, data, training)
      ? 'source_less'
      : '';
  }

  function setConstellationAvailable(available) {
    const switchBtn = conceptViewSwitchButton();
    if (!switchBtn) return;
    switchBtn.hidden = !available;
    switchBtn.disabled = !available;
    switchBtn.setAttribute('aria-disabled', available ? 'false' : 'true');
    if (!available && currentMapMode === 'constellation') {
      /* c8 ignore next -- defensive recovery if constellation becomes unavailable while selected */
      setMapMode('route');
    }
  }

  function refreshConstellationAvailability(training = null) {
    if (document.querySelector('.concept-page-b2__doc--post-repair')) {
      setConstellationAvailable(false);
      return;
    }
    if (document.body.dataset.conceptSourceMode === 'source_less') {
      setConstellationAvailable(false);
      return;
    }
    setConstellationAvailable(hasActiveEntryReconstructionEvidence(training) || hasActiveAttemptDraft());
  }

  function renderHero(concept) {
    if (!concept) {
      titleEl.textContent = 'What are you trying to understand?';
      // Empty-state desc dropped per silent-surface principle: the iso
      // board's nine empty slots make the affordance obvious; a
      // narrator line "Pick a tile to enter…" is unearned chrome.
      // Populated states still get state-specific guidance (the else
      // branch below still calls getHeroGuidance(concept)).
      descEl.textContent = '';
      if (heroStateChipEl) {
        heroStateChipEl.textContent = 'no sessions yet';
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
    const conceptField = document.getElementById('hero-single-input-field');
    if (conceptField) {
      conceptField.value = '';
      conceptField.style.height = '';
    }
    const guessField = document.getElementById('hero-cold-guess-field');
    if (guessField) {
      guessField.value = '';
      guessField.style.height = '';
    }
    doorSource.clear();
    const submitBtn = document.getElementById('hero-door-submit');
    if (submitBtn instanceof HTMLButtonElement) {
      submitBtn.disabled = true;
    }
  }

  async function runHeroAction(evtOrNothing) {
    if (evtOrNothing && typeof evtOrNothing.preventDefault === 'function') {
      evtOrNothing.preventDefault();
      if (!_doorReady() || northStarBusy) return false;
      const source = northStarSourceText();
      const target = document.getElementById('hero-cold-guess-field')?.value || '';
      const error = document.getElementById('hero-door-error');
      setNorthStarBusy(true);
      if (error) error.textContent = '';
      try {
        const authSession = await fetchAuthSession();
        let data = northStarSession;
        if (!data && isIdentifiedUserSession(authSession)) {
          doorSource.intakeKey ||= globalThis.crypto?.randomUUID?.();
          if (!doorSource.intakeKey) throw new Error('Secure source intake is unavailable.');
          const sourcePayload = doorSource.payload(doorSource.intakeKey);
          if (!sessionSourceTextFitsRequest(sourcePayload)) {
            doorSource.showSource();
            setNorthStarSourceError(doorSource.fileSource ? FILE_SOURCE_TOO_LARGE : PASTED_SOURCE_TOO_LARGE);
            return;
          }
          data = await createSedaSession({
            northStarIntake: true,
            sourceIntake: sourcePayload,
          });
        }
        data ||= await createSedaSession({ northStarIntake: true });
        northStarSession = data;
        rememberNorthStarSession(data.sessionId);
        if (data.awaiting?.key === 'source') data = await sendNorthStarText(data, source);
        if (data.awaiting?.key === 'target') data = await sendNorthStarText(data, target);
        renderNorthStarState(data);
      } catch (err) {
        if (error) error.textContent = err?.message || 'The session could not be saved. Try again.';
        if (northStarSession) renderNorthStarState(northStarSession);
      } finally {
        setNorthStarBusy(false);
      }
      return false;
    }

    // Non-form path: the Begin button drives Begin/Extract/Drill/Open-map.
    /* v8 ignore next -- active concept comes from browser-owned board state. */
    const concept = getActiveConcept();
    const action = heroPrimaryActionEl?.dataset.action || (!concept ? 'add' : '');
    if (action === 'add') {
      // The conversational creation modal is retired; this is the single
      // start-learning surface.
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

  function northStarSourceText() {
    return doorSource.sourceText();
  }

  function setNorthStarSourceError(message) {
    const error = document.getElementById('hero-source-error');
    if (error) error.textContent = message;
  }

  function _doorReady() {
    return doorSource.ready(northStarSession);
  }

  function reconstructionReady() {
    return Boolean(document.getElementById('north-star-explanation-field')?.value.trim());
  }

  function repairReady() {
    return Boolean(document.getElementById('north-star-repair-field')?.value.trim());
  }

  function _doorUpdateSubmitState() {
    const sourceNext = document.getElementById('hero-source-next');
    const submitBtn = document.getElementById('hero-door-submit');
    if (sourceNext) {
      sourceNext.disabled = northStarBusy || !doorSource.sourceReady(northStarSession);
    }
    if (submitBtn) submitBtn.disabled = northStarBusy || !_doorReady();
  }

  function setNorthStarBusy(value) {
    northStarBusy = Boolean(value);
    const capture = document.getElementById('hero-single-input');
    const reconstruction = document.getElementById('north-star-reconstruction-form');
    const repair = document.getElementById('north-star-repair-form');
    if (capture) {
      capture.dataset.state = northStarBusy ? 'busy' : '';
      capture.setAttribute('aria-busy', northStarBusy ? 'true' : 'false');
    }
    if (reconstruction) reconstruction.dataset.state = northStarBusy ? 'busy' : '';
    if (repair) repair.dataset.state = northStarBusy ? 'busy' : '';
    doorSource.render(northStarSession?.awaiting?.key === 'target', northStarBusy);
    _doorUpdateSubmitState();
    const reconstructionSubmit = document.getElementById('north-star-reconstruction-submit');
    if (reconstructionSubmit) reconstructionSubmit.disabled = northStarBusy || !reconstructionReady();
    const repairSubmit = document.getElementById('north-star-repair-submit');
    if (repairSubmit) repairSubmit.disabled = northStarBusy || !repairReady();
  }

  function rememberNorthStarSession(sessionId) {
    if (!sessionId) return;
    try { sessionStorage.setItem(NORTH_STAR_SESSION_KEY, sessionId); } catch { /* reload resume unavailable */ }
  }

  async function sendNorthStarText(session, text) {
    const response = await sendSedaTurn(
      session.sessionId,
      createSedaTurnSubmission(text, session.sessionVersion),
    );
    northStarSession = response;
    rememberNorthStarSession(response.sessionId);
    return response;
  }

  function targetFromSession(session) {
    return session?.savedReconstruction?.target
      || session?.events?.findLast?.((event) => event?.type === 'target_submitted')?.text
      || '';
  }

  function showNorthStarPanel(panel) {
    const capture = document.getElementById('hero-single-input');
    const reconstruction = document.getElementById('north-star-reconstruction');
    const saved = document.getElementById('north-star-saved');
    if (capture) capture.hidden = panel !== 'capture';
    if (reconstruction) reconstruction.hidden = panel !== 'reconstruction';
    if (saved) saved.hidden = panel !== 'saved';
  }

  async function evaluateNorthStarGap() {
    if (!northStarSession || northStarBusy) return;
    const error = document.getElementById('north-star-gap-error');
    setNorthStarBusy(true);
    if (error) error.textContent = '';
    try {
      const retrying = northStarSession.awaiting?.key === 'retry_reconstruction_gap';
      renderNorthStarState(await sendNorthStarText(northStarSession, retrying ? 'retry' : ''));
    } catch (err) {
      if (error) error.textContent = err?.message || 'The gap could not be generated. Try again.';
    } finally {
      setNorthStarBusy(false);
    }
  }

  function renderNorthStarRepair(session) {
    const result = session.reconstructionRepair;
    const gapText = document.getElementById('north-star-gap-text');
    const gapError = document.getElementById('north-star-gap-error');
    const retry = document.getElementById('north-star-gap-retry');
    const form = document.getElementById('north-star-repair-form');
    const saved = document.getElementById('north-star-repair-saved');

    if (gapError) gapError.textContent = '';
    if (retry) retry.hidden = true;
    if (form) form.hidden = true;
    if (saved) saved.hidden = true;

    if (result?.status === 'unavailable') {
      if (gapText) gapText.textContent = '';
      if (gapError) gapError.textContent = result.message;
      if (retry) retry.hidden = false;
      requestAnimationFrame(() => retry?.focus());
      return;
    }

    if (!result) {
      if (gapText) gapText.textContent = 'Finding one consequential gap…';
      if (session.awaiting?.key === 'evaluate_reconstruction_gap') {
        queueMicrotask(() => void evaluateNorthStarGap());
      }
      return;
    }

    if (gapText) gapText.textContent = result.gap;
    if (result.status === 'saved') {
      if (saved) saved.hidden = false;
      document.getElementById('north-star-repair-saved-text').textContent = result.repair;
      return;
    }

    if (form) form.hidden = false;
    requestAnimationFrame(() => document.getElementById('north-star-repair-field')?.focus());
  }

  function renderNorthStarState(session) {
    if (!session) return;
    northStarSession = session;
    rememberNorthStarSession(session.sessionId);
    const target = targetFromSession(session);

    if (session.savedReconstruction) {
      showNorthStarPanel('saved');
      document.getElementById('north-star-saved-target').textContent = session.savedReconstruction.target;
      document.getElementById('north-star-saved-explanation').textContent = session.savedReconstruction.explanation;
      const recorded = new Date(session.savedReconstruction.submittedAt);
      document.getElementById('north-star-saved-time').textContent = Number.isNaN(recorded.valueOf())
        ? session.savedReconstruction.submittedAt
        : recorded.toLocaleString();
      renderNorthStarRepair(session);
      return;
    }

    if (session.awaiting?.key === 'initial_reconstruction') {
      showNorthStarPanel('reconstruction');
      document.getElementById('north-star-target-text').textContent = target;
      requestAnimationFrame(() => document.getElementById('north-star-explanation-field')?.focus());
      return;
    }

    showNorthStarPanel('capture');
    const targetField = document.getElementById('hero-cold-guess-field');
    const submit = document.getElementById('hero-door-submit');
    const waitingForTarget = session.awaiting?.key === 'target';
    doorSource.render(waitingForTarget, northStarBusy);
    if (submit) {
      submit.setAttribute('aria-label', 'Start');
    }
    if (waitingForTarget) requestAnimationFrame(() => targetField?.focus());
  }

  async function restoreNorthStarSession() {
    let sessionId = '';
    try { sessionId = sessionStorage.getItem(NORTH_STAR_SESSION_KEY) || ''; } catch { return; }
    if (!sessionId) return;
    try {
      renderNorthStarState(await getSedaSession(sessionId));
    } catch (err) {
      const error = document.getElementById('hero-door-error');
      if (error && err?.code === 'source_unavailable') {
        error.textContent = 'The saved source is no longer available. Attach or paste it again.';
      } else if (error && ![400, 404].includes(err?.status)) {
        error.textContent = 'The saved session could not be reopened.';
      }
      try { sessionStorage.removeItem(NORTH_STAR_SESSION_KEY); } catch { /* no-op */ }
      northStarSession = null;
    }
  }

  function initHeroSingleInput() {
    doorSource.init({ isBusy: () => northStarBusy, session: () => northStarSession });

    const reconstructionForm = document.getElementById('north-star-reconstruction-form');
    const reconstructionField = document.getElementById('north-star-explanation-field');
    const reconstructionSubmit = document.getElementById('north-star-reconstruction-submit');
    const repairForm = document.getElementById('north-star-repair-form');
    const repairField = document.getElementById('north-star-repair-field');
    const repairSubmit = document.getElementById('north-star-repair-submit');
    const updateReconstruction = () => {
      if (reconstructionSubmit) reconstructionSubmit.disabled = northStarBusy || !reconstructionReady();
    };
    reconstructionField?.addEventListener('input', updateReconstruction);
    reconstructionField?.addEventListener('keydown', (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key === 'Enter' && reconstructionReady()) {
        event.preventDefault();
        reconstructionForm?.requestSubmit?.();
      }
    });
    reconstructionForm?.addEventListener('submit', async (event) => {
      event.preventDefault();
      if (!northStarSession || !reconstructionReady() || northStarBusy) return;
      const error = document.getElementById('north-star-reconstruction-error');
      setNorthStarBusy(true);
      if (error) error.textContent = '';
      try {
        renderNorthStarState(await sendNorthStarText(northStarSession, reconstructionField.value));
      } catch (err) {
        if (error) error.textContent = err?.message || 'The explanation could not be saved. Try again.';
      } finally {
        setNorthStarBusy(false);
      }
    });
    const updateRepair = () => {
      if (repairSubmit) repairSubmit.disabled = northStarBusy || !repairReady();
    };
    repairField?.addEventListener('input', updateRepair);
    repairField?.addEventListener('keydown', (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key === 'Enter' && repairReady()) {
        event.preventDefault();
        repairForm?.requestSubmit?.();
      }
    });
    repairForm?.addEventListener('submit', async (event) => {
      event.preventDefault();
      if (!northStarSession || !repairReady() || northStarBusy) return;
      const error = document.getElementById('north-star-repair-error');
      setNorthStarBusy(true);
      if (error) error.textContent = '';
      try {
        renderNorthStarState(await sendNorthStarText(northStarSession, repairField.value));
      } catch (err) {
        if (error) error.textContent = err?.message || 'The repair could not be saved. Try again.';
      } finally {
        setNorthStarBusy(false);
      }
    });
    document.getElementById('north-star-gap-retry')
      ?.addEventListener('click', () => void evaluateNorthStarGap());
    void restoreNorthStarSession();
  }


  // ── 8. Grid rendering ──────────────────────────────────────
  function renderGrid(concepts = loadConcepts()) {
    const grid = document.getElementById('grid-container');
    const gridSvg = document.getElementById('grid-svg');
    const deskHelper = document.querySelector('.desk-helper');
    const deskConceptCount = document.getElementById('desk-concept-count');
    const isFirstUse = concepts.length === 0;
    if (grid) grid.classList.toggle('is-first-use', isFirstUse);
    document.body.dataset.deskFirstUse = String(isFirstUse);
    if (deskConceptCount) {
      deskConceptCount.textContent = String(concepts.length);
      deskConceptCount.setAttribute(
        'aria-label',
        `${concepts.length} ${concepts.length === 1 ? 'concept' : 'concepts'}`,
      );
    }
    if (gridSvg) {
      gridSvg.setAttribute('viewBox', isFirstUse ? '140 119 140 130' : '0 0 420 365');
    }
    if (deskHelper) {
      deskHelper.textContent = isFirstUse
        ? 'Then write what you remember.'
        : 'Choose a session to reconstruct from memory.';
    }
    const dueIds = dueConceptIdSet(cachedDueItems);
    renderDeskGrid({
      concepts,
      tileEls,
      activeId: getActiveId(),
      bus: Bus,
      dueConceptIds: dueIds,
      readyFilterActive,
    });
  }

  function getSidebarActiveConceptId() {
    return currentPrimaryNav === null ? getActiveId() : null;
  }

  function syncConceptListActiveState() {
    const sidebarActiveId = getSidebarActiveConceptId();
    document.querySelectorAll('#concept-list .concept-item').forEach((item) => {
      const conceptId = item.dataset.conceptId || item.querySelector('.concept-actions')?.dataset.conceptId;
      item.classList.toggle('active', conceptId === sidebarActiveId);
    });
  }

  function closeConceptActionMenus() {
    document.querySelectorAll('#concept-list .concept-item.menu-open').forEach((item) => {
      const menu = item.querySelector('.concept-action-menu');
      const trigger = item.querySelector('.concept-actions');
      if (menu) menu.hidden = true;
      if (trigger) trigger.setAttribute('aria-expanded', 'false');
      item.classList.remove('menu-open');
    });
  }

  function toggleConceptActions(btn) {
    const item = btn?.closest?.('.concept-item');
    const menu = item?.querySelector?.('.concept-action-menu');
    if (!item || !menu) return;

    const shouldOpen = menu.hidden;
    closeConceptActionMenus();
    menu.hidden = !shouldOpen;
    item.classList.toggle('menu-open', shouldOpen);
    btn.setAttribute('aria-expanded', String(shouldOpen));
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
    const renderSeq = ++conceptListRenderSeq;
    renderShellConceptList({
      concepts,
      activeId: getSidebarActiveConceptId(),
      conceptListEl,
      onOpenConcept(c) {
        showDashboard();
        selectConcept(c.id);
        if (c.graphData) showMapView(c);
        if (window.innerWidth < 900) closeDrawer();
      },
    });

    if (!concepts.length) return;

    Promise.all(concepts.map(async (concept) => {
      const conceptId = String(concept?.id ?? '');
      if (!conceptId) return [conceptId, null];
      try {
        return [conceptId, await trainingStore.loadTraining(conceptId)];
      } catch (err) {
        /* c8 ignore next 2 -- defensive corrupt localStorage branch */
        console.warn('Training record unavailable for sidebar concept.', conceptId, err);
        return [conceptId, null];
      }
    }))
      .then((entries) => {
        if (renderSeq !== conceptListRenderSeq) return;
        const conceptsById = new Map(concepts.map((concept) => [String(concept?.id ?? ''), concept]));
        entries.forEach(([conceptId, training]) => {
          const item = Array.from(conceptListEl.querySelectorAll('.concept-item'))
            .find((el) => el.dataset.conceptId === conceptId);
          const dot = item?.querySelector('.concept-dot');
          if (!dot) return;
          const concept = conceptsById.get(conceptId);
          dot.dataset.state = deriveConceptBadge(concept, training) || '';
        });
      })
      .catch((err) => {
        /* c8 ignore next -- defensive localStorage failure branch */
        console.warn('Training records unavailable for sidebar render.', err);
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

    /* c8 ignore start -- source-attached creation requires the live extraction path; the store contract is covered directly. */
    const jsonPayload = { ...knowledgeMap, metadata: { ...(knowledgeMap.metadata || {}) } };
    jsonPayload.metadata.starting_map_context = startingMapContext;
    jsonPayload.metadata.map_maturity = 'provisional';
    jsonPayload.metadata.source_mode = 'source_attached';

    const concepts = loadConcepts();
    const concept = {
      id, name, state: 'growing',
      createdAt: Date.now(), timerStart: null,
      contentPreview: sourceText.slice(0, 500),
      contentType: sourceType,
      contentFilename: sourceFilename,
      sourceUrl: source?.url || null,
      sourceMode: 'source_attached',
      startingMapContext,
      graphData: JSON.stringify(jsonPayload)
    };
    contentStore.set(id, sourceText);
    concepts.push(concept);
    saveConcepts(concepts);
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
  // C-prime launch-pad flow. Overlay teardown stays in launch-pad.js.
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
    jsonPayload.metadata.source_mode = 'source_less';
    if (shell.goal) {
      jsonPayload.metadata.learner_goal = shell.goal;
    }

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
      sourceMode: 'source_less',
      learnerGoal: shell.goal || '',
      startingMapContext,
      graphData: JSON.stringify(jsonPayload),
    };
    // No source text — contentStore is not written for source-less concepts.
    concepts.push(concept);
    saveConcepts(concepts);
    // This in-memory marker is deliberately scoped to the current Door flow.
    // A legacy unbound map must not gain permission to replace node ids merely
    // because it lacks a persisted marker.
    freshSourceLessConceptIds.add(id);
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
    banner.textContent = '';
    banner.hidden = true;
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
    startDrill({ drillMode: 'seda' });
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
  /* c8 ignore next -- source-attached creation uses the same persistence boundary as launch-pad and is covered by live smoke. */
  async function runSourceAttachedSubmit({ name, source, startingSketch = '' }) {
    const setDoorError = (msg) => {
      const errEl = document.getElementById('hero-door-error');
      if (errEl) {
        errEl.textContent = msg;
        errEl.hidden = !msg;
      }
    };
    /* v8 ignore next -- clearing a pre-existing door error depends on browser state. */
    setDoorError('');

    /* v8 ignore next -- board-cap door guard depends on browser board state. */
    if (loadConcepts().length >= BOARD_SLOT_COUNT) {
      // Library is at the visible board cap. Don't pay for an LLM call.
      /* c8 ignore next -- board-cap guard is covered by launch-pad tests. */
      setDoorError('The board holds nine sessions. Retire one to start another.');
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
      const data = await submitConceptCreate({
        name,
        startingSketch,
        source: resolvedSource,
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
        startingSketch,
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
    const confirmed = window.confirm(`Delete "${conceptName}"?\n\nThis removes the concept and its recorded evidence from this browser.`);
    if (!confirmed) {
      closeConceptActionMenus();
      return;
    }

    const wasActive = getActiveId() === id;
    const item = btnEl?.closest?.('.concept-item');
    if (item) { item.style.transition = 'all 0.2s ease'; item.style.opacity = '0'; item.style.transform = 'translateX(-12px)'; }

    const finishDelete = () => {
      const concepts = loadConcepts().filter(c => c.id !== id);
      saveConcepts(concepts);
      clearRepairRepsStateForConcept(id);
      clearComparisonAcknowledgementsForConcept(id);
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
      renderDeskDueSurfaces();
      renderConceptList(concepts);
      renderIgnitionGate();
      scheduleLearnerStatePush();
    };

    if (item) {
      setTimeout(finishDelete, 200);
    } else {
      finishDelete();
    }
  }

  function selectTile(tileIdx) {
    const tileEl = tileEls[tileIdx];
    if (
      tileEl?.classList.contains('is-capacity')
      || tileEl?.classList.contains('is-filtered-out')
      || tileEl?.getAttribute('data-ready-filtered') === 'out'
    ) {
      return;
    }
    const concepts = loadConcepts();
    const concept = concepts[tileIdx];
    if (concept) {
      AudioFX.playTileClick();
      selectConcept(concept.id);
      if (concept.graphData) showMapView(concept);
    } else {
      // Empty tile → route straight to the start-learning surface.
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
    renderDeskDueSurfaces();
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
      consolidateBtn.textContent = 'Review later';
      consolidateBtn.title = 'Review opens after spacing.';
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

    mountSourcePanel(overlay, {
      onAttach: ({ text, type, filename, url }) => {
        const content = type === 'url' ? url : text;
        if (!content) return;
        contentStore.set(conceptId, content);
        updateActiveConcept({
          contentPreview: content.slice(0, 500),
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
    startDrill(buildDefaultDrillContext(concept, graphData));
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
  const routeAttemptDrafts = new Map();
  const repairChecksThisSession = new Set();

  function routeAttemptDraftKey(entryId) {
    return `${getActiveId() || 'concept'}:${entryId}`;
  }

  function entrySessionKey(conceptId, entryId) {
    return `${conceptId || 'concept'}:${entryId || 'entry'}`;
  }

  function conceptPageRenderOptionsForEntry(concept, entryId, training = null, options = {}) {
    if (!concept?.id || !entryId) return options;
    const persistedCheckedEntryIds = Object.entries(training?.node_records || {})
      .filter(([, record]) => Boolean(record?.repair_checked_at))
      .map(([id]) => id);
    const sessionCheckedEntryIds = [...repairChecksThisSession]
      .filter((key) => key.startsWith(`${concept.id}:`))
      .map((key) => key.slice(concept.id.length + 1));
    const repairCheckedEntryIds = [...new Set([
      ...persistedCheckedEntryIds,
      ...sessionCheckedEntryIds,
    ])];
    return {
      ...options,
      repairCheckedEntryIds,
      repairCheckedThisSession: repairCheckedEntryIds.includes(entryId),
      comparisonAcknowledged: options?.justRevealedEntryId === entryId
        ? false
        : hasComparisonAcknowledgement(concept.id, entryId),
    };
  }

  function captureActiveEntryDraft() {
    if (!_activeEntryId) return;
    const input = document.querySelector('.concept-page-b2__attempt-input');
    if (!input) return;
    routeAttemptDrafts.set(routeAttemptDraftKey(_activeEntryId), input.value || '');
  }

  function syncInlineAttemptSaveButton(panel, options = {}) {
    const input = panel?.querySelector?.('.concept-page-b2__attempt-input');
    const button = panel?.querySelector?.('.concept-page-b2__attempt-save');
    if (!input || !button) return;
    const hasDraft = Boolean((input.value || '').trim());
    button.disabled = !hasDraft;
    button.setAttribute('aria-disabled', hasDraft ? 'false' : 'true');
    refreshConstellationAvailability(options.training || null);
    if (hasDraft && options.clearError) {
      const errorEl = panel.querySelector?.('[data-attempt-error]');
      if (errorEl) errorEl.hidden = true;
    }
  }

  function restoreActiveEntryDraft(entryId) {
    const input = document.querySelector('.concept-page-b2__attempt-input');
    const key = routeAttemptDraftKey(entryId);
    if (!input || !routeAttemptDrafts.has(key)) return;
    input.value = routeAttemptDrafts.get(key) || '';
    syncInlineAttemptSaveButton(input.closest('.concept-page-b2__attempt'));
  }

  function focusRenderedMoment(selector) {
    requestAnimationFrame(() => {
      document.querySelector(selector)?.focus?.();
    });
  }

  /**
   * Wire event handlers on the work column after a swap or initial mount.
   * Handles the active reconstruction, study, and repair controls.
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
        if (ctaBtn.dataset.activeEntryAction === 'keep-working') {
          const entryId = ctaBtn.dataset.activeEntryId;
          markComparisonAcknowledged(concept.id, entryId);
          const mountEl = document.getElementById('map-content');
          if (mountEl) {
            renderConceptPageB2(mountEl, data, concept, training, {
              activeEntryId: entryId,
              viewMode: 'expanded-workspace',
              comparisonAcknowledged: true,
            });
          }
          return;
        }
        if (ctaBtn.dataset.activeEntryAction === 'write-repair') {
          const repairPanel = docEl.querySelector('.concept-page-b2__repair');
          const studyNote = docEl.querySelector('.concept-page-b2__study-note');
          const studyNoteToggle = docEl.querySelector('[data-study-note-toggle]');
          repairPanel?.removeAttribute('hidden');
          studyNote?.classList.add('is-collapsed');
          if (studyNoteToggle) {
            studyNoteToggle.textContent = 'Show study note';
            studyNoteToggle.setAttribute('aria-expanded', 'false');
          }
          ctaBtn.hidden = true;
          repairPanel?.querySelector('.concept-page-b2__repair-input')?.focus?.();
          return;
        }
        if (ctaBtn.dataset.activeEntryAction === 'drill-gap') {
          const entryId = ctaBtn.dataset.activeEntryId;
          startDrill(buildRepairGapDrillContext(entryId, concept, data, training));
          return;
        }
        if (ctaBtn.dataset.activeEntryAction === 'next-entry') {
          if (_activeEntryId) {
            markComparisonAcknowledged(concept.id, _activeEntryId);
          }
          setActiveEntry(ctaBtn.dataset.activeEntryId, data, concept, training, { focusAttempt: true });
          return;
        }
        const inlineAttempt = docEl.querySelector('.concept-page-b2__attempt-input');
        if (inlineAttempt) {
          /* c8 ignore next 2 -- defensive: CTA is not rendered while the inline attempt is present */
          inlineAttempt.focus();
          return;
        }
        /* c8 ignore next 3 -- SEDA resume routing is covered by visible Save draft product QA; this CTA state is the same handoff without the inline composer. */
        if (shouldResumeSedaForConcept(concept.id)) {
          startDrill(buildSedaResumeDrillContext(ctaBtn.dataset.activeEntryId, concept, data, training));
          return;
        }
        showInlineAttemptForEntry(ctaBtn.dataset.activeEntryId, concept, data, training);
      });
    }
    const attemptBtn = docEl.querySelector('.concept-page-b2__attempt-save');
    if (attemptBtn) {
      const attemptPanel = attemptBtn.closest('.concept-page-b2__attempt');
      const attemptInput = attemptPanel?.querySelector?.('.concept-page-b2__attempt-input');
      syncInlineAttemptSaveButton(attemptPanel, { training });
      attemptInput?.addEventListener('input', () => {
        syncInlineAttemptSaveButton(attemptPanel, { clearError: true, training });
      });
      attemptBtn.addEventListener('click', () => {
        void submitInlineAttemptForEntry(attemptBtn, concept, data);
      });
    }
    const blankStartBtn = docEl.querySelector('[data-blank-start]');
    if (blankStartBtn) {
      blankStartBtn.addEventListener('click', () => {
        const wrapper = blankStartBtn.closest('.concept-page-b2__blank-start');
        const hint = wrapper?.querySelector?.('[data-blank-start-hint]');
        if (hint) hint.hidden = false;
        blankStartBtn.setAttribute('aria-expanded', 'true');
        blankStartBtn.hidden = true;
        docEl.querySelector('.concept-page-b2__attempt-input')?.focus?.();
      });
    }
    const repairBtn = docEl.querySelector('.concept-page-b2__repair-save');
    if (repairBtn) {
      repairBtn.addEventListener('click', () => {
        void saveRepairForEntry(repairBtn, concept, data);
      });
    }
    const studyNote = docEl.querySelector('.concept-page-b2__study-note');
    const studyNoteToggle = docEl.querySelector('[data-study-note-toggle]');
    const setStudyNoteCollapsed = (collapsed) => {
      if (!studyNote) return;
      studyNote.classList.toggle('is-collapsed', Boolean(collapsed));
      if (studyNoteToggle) {
        studyNoteToggle.textContent = collapsed ? 'Show study note' : 'Hide study note';
        studyNoteToggle.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
      }
    };
    if (studyNoteToggle) {
      studyNoteToggle.addEventListener('click', () => {
        setStudyNoteCollapsed(!studyNote?.classList.contains('is-collapsed'));
      });
    }
    const repairInput = docEl.querySelector('.concept-page-b2__repair-input');
    if (repairInput) {
      repairInput.addEventListener('focus', () => setStudyNoteCollapsed(true));
      repairInput.addEventListener('input', () => {
        setStudyNoteCollapsed(Boolean(repairInput.value.trim()));
      });
      repairInput.addEventListener('blur', () => {
        setStudyNoteCollapsed(Boolean(repairInput.value.trim()));
      });
    }
    docEl.querySelectorAll('[data-feedback-rating]').forEach((button) => {
      button.addEventListener('click', () => {
        window.Feedback?.show?.({
          focus: 'rating',
          moment: button.getAttribute('data-feedback-moment') || '',
        });
      });
    });
  }

  function renderActiveEntryDocumentHtml(activeEntry, activeIdx, backbone, concept, data, training, renderOptions = {}) {
    const activeHtml = renderActiveEntryHtml(
      activeEntry,
      activeIdx,
      backbone,
      concept,
      data,
      training,
      renderOptions,
    );
    const postRepairBridge = derivePostRepairBridge(data, training, getConceptEntryId(activeEntry, activeIdx), renderOptions);
    if (!postRepairBridge) return { html: activeHtml, hasPostRepair: false };
    const constellationHtml = renderConceptConstellationHtml(data, {
      ...renderOptions,
      concept,
      training,
      activeEntryId: postRepairBridge.repairedEntryId,
      postRepairBridge,
    });
    return {
      html: `${activeHtml}<section class="concept-post-repair-host">${constellationHtml}</section>`,
      hasPostRepair: true,
    };
  }

  function renderActiveEntryWorkColumn(entryId, concept, data, training = null, options = {}) {
    const docEl = document.querySelector('.concept-page-b2__doc');
    const backbone = deriveConceptEntries(data);
    const fallbackMatch = entryId === 'core-thesis' && !backbone.length
      ? selectInitialConceptEntry(backbone, training)
      : null;
    const match = findConceptEntryById(backbone, entryId) || fallbackMatch;
    if (!docEl || !match) return;
    const renderBackbone = backbone.length ? backbone : [match.entry];
    const renderOptions = conceptPageRenderOptionsForEntry(concept, entryId, training, options);
    const rendered = renderActiveEntryDocumentHtml(
      match.entry,
      match.index,
      renderBackbone,
      concept,
      data,
      training,
      renderOptions,
    );
    docEl.innerHTML = rendered.html;
    docEl.classList.toggle('concept-page-b2__doc--post-repair', rendered.hasPostRepair);
    rebindActiveEntryHandlers(docEl, concept, data, training);
  }

  function showInlineAttemptForEntry(entryId, concept, data, training = null) {
    if (!entryId || !concept?.id) return;
    renderActiveEntryWorkColumn(entryId, concept, data, training, { attemptEntryId: entryId });
    requestAnimationFrame(() => {
      document.querySelector('.concept-page-b2__attempt-input')?.focus?.();
    });
  }

  function hasPendingSourceLessSedaRoute(concept, graphData = null) {
    const data = graphData || parseConceptGraphData(concept) || {};
    return isSourceLessConcept(concept, data)
      && data?.metadata?.route_status === 'pending_seda'
      && data?.metadata?.graph_neutral === true
      && !hasBoundSourceLessSedaRoute(data);
  }

  function shouldResumeSedaForConcept(conceptId) {
    const stored = loadSedaSessionState(conceptId);
    if (stored?.sessionId && stored?.latest?.caseComplete !== true) return true;
    const concept = loadConcepts().find((item) => item?.id === conceptId) || null;
    return hasPendingSourceLessSedaRoute(concept);
  }

  function buildSedaResumeDrillContext(entryId, concept, data, training = null, options = {}) {
    const graphData = parseConceptGraphData(concept) || data || {};
    const match = findConceptEntryById(deriveConceptEntries(graphData), entryId);
    const entry = match?.entry || {};
    const scaffold = entry.learner_scaffold || {};
    const label = entry.label || entry.task_label || entry.principle || concept?.name || 'Entry';
    const prompt = scaffold.entry_prompt || scaffold.task_cue || entry.purpose || '';
    return {
      id: entryId,
      type: entry.type || resolveNodeType(graphData, entryId, 'entry'),
      label,
      fullLabel: label,
      detail: entry.mechanism || entry.principle || entry.study_note || entry.detail || entry.purpose || prompt,
      prompt,
      learner_scaffold: entry.learner_scaffold,
      purpose: entry.purpose,
      trainingSnapshot: training,
      graphNeutral: true,
      drillMode: 'seda',
      ...options,
    };
  }

  function textFromRepairGap(gap) {
    if (!gap || typeof gap !== 'object') return '';
    return String(
      gap.correction
        || gap.description
        || gap.gap_description
        || gap.detail
        || ''
    ).trim();
  }

  function titleFromRepairGap(gap, fallback = 'the repaired link') {
    if (!gap || typeof gap !== 'object') return fallback;
    return String(
      gap.mechanism
        || gap.type
        || gap.label
        || fallback
    ).trim() || fallback;
  }

  function boundedDrillNodeMechanism(value) {
    const text = String(value || '');
    if (text.length <= DRILL_NODE_MECHANISM_MAX_CHARS) return text;
    const marker = '\n[earlier drill context truncated]\n';
    const tailBudget = 3000;
    const headBudget = DRILL_NODE_MECHANISM_MAX_CHARS - marker.length - tailBudget;
    return `${text.slice(0, headBudget)}${marker}${text.slice(-tailBudget)}`;
  }

  function buildRepairGapDrillContext(entryId, concept, data, training = null) {
    const graphData = parseConceptGraphData(concept) || data || {};
    const backbone = deriveConceptEntries(graphData);
    const match = findConceptEntryById(backbone, entryId);
    const entry = match?.entry || {};
    const record = training?.node_records?.[entryId] || {};
    const attempts = Array.isArray(record.attempts) ? record.attempts : [];
    const latestAttempt = attempts[attempts.length - 1] || {};
    const gaps = Array.isArray(latestAttempt.gaps) ? latestAttempt.gaps : [];
    const gap = gaps[0] || null;
    const repairs = Array.isArray(record.repairs) ? record.repairs : [];
    const latestRepair = repairs[repairs.length - 1] || null;
    const gapCorrection = textFromRepairGap(gap);
    const label = entry.label || entry.principle || entry.task_label || concept?.name || 'Entry';
    const gapTitle = titleFromRepairGap(gap, label);
    const visiblePrompt = gap
      ? `Rebuild the repaired link for ${gapTitle}: name the condition, the action, and what changes next.`
      : `Reconstruct this entry from memory.`;
    const repairContext = [
      entry.mechanism || entry.principle || entry.study_note || entry.detail || entry.purpose || '',
      latestAttempt.user_text ? `Learner cold draft: ${latestAttempt.user_text}` : '',
      gapCorrection ? `Detected repairable gap: ${gapCorrection}` : '',
      latestRepair?.text ? `Learner repair text: ${latestRepair.text}` : '',
      'Probe this gap with short Socratic turns. Do not lecture or treat the repair as solid evidence.',
    ].filter(Boolean).join('\n');
    return {
      id: entryId,
      type: entry.type || 'entry',
      label,
      fullLabel: label,
      detail: visiblePrompt,
      prompt: visiblePrompt,
      repairContext,
      trainingSnapshot: training,
      drillMode: 're_drill',
      graphNeutral: true,
    };
  }

  function buildDefaultDrillContext(concept, graphData, training = null) {
    const backbone = deriveConceptEntries(graphData || {});
    const activeMatch = _activeEntryId ? findConceptEntryById(backbone, _activeEntryId) : null;
    const match = activeMatch || (backbone.length ? selectInitialConceptEntry(backbone, training) : null);
    if (match?.entry && backbone.length) {
      const entry = match.entry;
      const id = match.id || getConceptEntryId(entry, match.index);
      const label = entry.label || entry.task_label || entry.principle || `Entry ${match.index + 1}`;
      const scaffold = entry.learner_scaffold || {};
      const prompt = scaffold.entry_prompt || scaffold.task_cue || entry.purpose || '';
      return {
        id,
        type: entry.type || resolveNodeType(graphData, id, 'entry'),
        label,
        fullLabel: label,
        detail: entry.mechanism || entry.principle || entry.study_note || entry.detail || entry.purpose || prompt,
        prompt,
        learner_scaffold: entry.learner_scaffold,
        purpose: entry.purpose,
      };
    }
    return {
      id: 'core-thesis',
      type: 'core',
      label: 'Core Thesis',
      fullLabel: 'Core Thesis',
      detail: graphData?.metadata?.core_thesis || graphData?.metadata?.thesis || concept.contentPreview || 'Explain this core idea in your own words.',
    };
  }

  function resolveDrillContextForConcept(nodeContext, concept, graphData, training = null) {
    if (!nodeContext || !nodeContext.id) {
      return {
        ...buildDefaultDrillContext(concept, graphData, training),
        ...(nodeContext || {}),
      };
    }
    const backbone = deriveConceptEntries(graphData || {});
    if (
      backbone.length
      && nodeContext.id === 'core-thesis'
      && !findConceptEntryById(backbone, nodeContext.id)
    ) {
      return buildDefaultDrillContext(concept, graphData, training);
    }
    return nodeContext;
  }

  async function revealStudyForEntry(entryId, concept, data) {
    if (!entryId || !concept?.id) return;
    const graphData = parseConceptGraphData(concept) || data || {};
    const backbone = deriveConceptEntries(graphData);
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
          concept_id: concept.id,
          schema_version: TRAINING_SCHEMA_VERSION,
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
        await trainingStore.saveTraining(training);
        renderActiveEntryWorkColumn(entryId, concept, graphData, training);
        focusRenderedMoment('.concept-page-b2__study-note');
        return;
      }
      const training = await trainingStore.setStudyRevealed(
        concept.id,
        entryId,
        new Date().toISOString(),
      );
      const renderOptions = {
        activeEntryId: entryId,
        justRevealedEntryId: entryId,
      };
      const mountEl = document.getElementById('map-content');
      if (mountEl) renderConceptPageB2(mountEl, graphData, concept, training, renderOptions);
      const constellationContent = document.getElementById('concept-constellation-content');
      if (constellationContent) renderConceptConstellationView(
        constellationContent,
        graphData,
        concept,
        training,
        renderOptions,
      );
      focusRenderedMoment('.concept-page-b2__study-note');
    } catch (err) {
      /* c8 ignore next -- defensive storage/invariant failure branch */
      console.warn('Study reveal failed.', err);
    }
  }

  async function submitInlineAttemptForEntry(button, concept, data) {
    const panel = button?.closest?.('.concept-page-b2__attempt');
    const entryId = button?.dataset?.attemptEntryId || panel?.dataset?.attemptEntryId || null;
    const input = panel?.querySelector?.('.concept-page-b2__attempt-input');
    const statusEl = panel?.querySelector?.('[data-attempt-status]');
    const errorEl = panel?.querySelector?.('[data-attempt-error]');
    const userText = input?.value || '';
    if (!entryId || !concept?.id) return;
    if (userText.trim() === '') {
      if (errorEl) {
        errorEl.hidden = false;
      }
      input?.focus?.();
      return;
    }
    if (errorEl) errorEl.hidden = true;
    const buttonLabel = button.querySelector?.('[data-attempt-save-label]');
    if (buttonLabel) buttonLabel.textContent = 'Saving draft…';
    button.disabled = true;
    button.setAttribute('aria-disabled', 'true');
    button.setAttribute('aria-busy', 'true');
    panel?.setAttribute('aria-busy', 'true');
    if (statusEl) statusEl.textContent = 'Checking and saving your draft…';

    const graphData = parseConceptGraphData(concept) || data || {};
    if (hasPendingSourceLessSedaRoute(concept, graphData)) {
      startDrill(buildSedaResumeDrillContext(entryId, concept, graphData, null, {
        // This draft was written against the durable shell, not the route SEDA
        // is about to generate. Keep it visible, but never auto-submit it.
        restoredDraftText: userText.trim(),
      }));
      return;
    }
    if (shouldResumeSedaForConcept(concept.id)) {
      startDrill(buildSedaResumeDrillContext(entryId, concept, data, null, {
        initialTurnText: userText.trim(),
      }));
      return;
    }

    const backbone = deriveConceptEntries(graphData);
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
      });
      if (getActiveId() !== concept.id) return;
      const training = await appendTrainingAttemptFromDrillTurn({
        conceptId: concept.id,
        nodeId: entryId,
        userText,
        result,
        at,
      });
      if (!training) {
        const nudge = inlineAttemptNudgeFromDrillResult(result);
        if (nudge) {
          button.disabled = false;
          button.setAttribute('aria-disabled', 'false');
          button.removeAttribute('aria-busy');
          panel?.removeAttribute('aria-busy');
          if (buttonLabel) buttonLabel.textContent = 'Save draft';
          if (statusEl) statusEl.textContent = '';
          if (errorEl) {
            errorEl.textContent = nudge;
            errorEl.hidden = false;
          }
          input?.focus?.();
          return;
        }
        throw new Error('attempt-not-recorded');
      }
      if (getActiveId() !== concept.id) return;
      const legacyGraphPatchedConcept = drillMode === 're_drill'
        ? patchActiveConceptDrillOutcome({ ...result, node_id: result?.node_id || entryId }, drillMode)
        : null;
      const renderConcept = legacyGraphPatchedConcept || concept;
      const renderGraphData = legacyGraphPatchedConcept
        ? parseConceptGraphData(legacyGraphPatchedConcept) || graphData
        : graphData;
      const mountEl = document.getElementById('map-content');
      if (mountEl) renderConceptPageB2(mountEl, renderGraphData, renderConcept, training, { activeEntryId: entryId });
      focusRenderedMoment('.concept-page-b2__evidence');
    } catch (err) {
      console.warn('Memory attempt failed.', err);
      button.disabled = false;
      button.setAttribute('aria-disabled', 'false');
      button.removeAttribute('aria-busy');
      if (buttonLabel) buttonLabel.textContent = 'Save draft';
      if (errorEl) {
        errorEl.textContent = 'The system could not record this yet. Try again.';
        errorEl.hidden = false;
      }
      panel?.removeAttribute('aria-busy');
      if (statusEl) statusEl.textContent = '';
    }
  }

  async function saveRepairForEntry(button, concept, data) {
    const panel = button?.closest?.('.concept-page-b2__repair');
    const entryId = button?.dataset?.repairEntryId || panel?.dataset?.repairEntryId || null;
    const input = panel?.querySelector?.('.concept-page-b2__repair-input');
    const statusEl = panel?.querySelector?.('[data-repair-status]');
    const errorEl = panel?.querySelector?.('[data-repair-error]');
    const text = (input?.value || '').trim().slice(0, 1200);
    if (!entryId || !concept?.id) return;
    if (!text) {
      if (errorEl) errorEl.hidden = false;
      input?.focus?.();
      return;
    }
    if (errorEl) errorEl.hidden = true;
    button.disabled = true;
    panel?.setAttribute('aria-busy', 'true');
    if (statusEl) statusEl.textContent = 'Saving your repair…';

    try {
      const training = await trainingStore.appendRepair(concept.id, entryId, {
        id: `repair-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        at: new Date().toISOString(),
        text,
      });
      const mountEl = document.getElementById('map-content');
      if (mountEl) {
        window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
        renderConceptPageB2(mountEl, data, concept, training, { activeEntryId: entryId });
        focusRenderedMoment(
          mountEl.querySelector('.concept-post-repair__rail')
            ? '.concept-post-repair__rail'
            : '.concept-page-b2__repair--saved',
        );
      }
    } catch (err) {
      /* c8 ignore next -- defensive storage/invariant failure branch */
      console.warn('Repair save failed.', err);
      if (errorEl) {
        errorEl.textContent = 'Repair could not be saved. Try again.';
        errorEl.hidden = false;
      }
      button.disabled = false;
      panel?.removeAttribute('aria-busy');
      if (statusEl) statusEl.textContent = '';
    }
  }

  /**
   * Swap the work column to show a different backbone entry without
   * rebuilding the whole concept page. Called by route-margin clicks
   * and vertical keyboard arrow nav.
   *
   * Animates: 240ms opacity fade-out, swap, 320ms opacity + 4px
   * translateY fade-in. Does NOT animate layout properties.
   *
   * @param {string} entryId - The id of the backbone entry to show
   * @param {Object} data - Parsed graphData
   * @param {Object} concept - The full concept object
   */
  function setActiveEntry(entryId, data, concept, training = null, options = {}) {
    if (!data || !entryId) return;
    if (entryId === _activeEntryId) return;

    const backbone = deriveConceptEntries(data);
    const activeMatch = findConceptEntryById(backbone, entryId);
    if (!activeMatch) return;
    const newEntry = activeMatch.entry;
    const newIdx = activeMatch.index;

    const mountEl = document.getElementById('map-content');
    if (!mountEl) return;

    // Swap the work column with a fade transition
    const doc = mountEl.querySelector('.concept-page-b2__doc');
    if (!doc) return;
    captureActiveEntryDraft();
    doc.classList.add('is-fading-out');
    const routeExpanded = mountEl.querySelector('.concept-page-b2__route')?.dataset?.routeExpanded === 'true';
    const renderOptions = conceptPageRenderOptionsForEntry(concept, entryId, training, routeExpanded ? {
      viewMode: 'expanded-workspace',
      comparisonAcknowledged: true,
    } : {});
    setTimeout(() => {
      const rendered = renderActiveEntryDocumentHtml(newEntry, newIdx, backbone, concept, data, training, renderOptions);
      doc.innerHTML = rendered.html;
      doc.classList.toggle('concept-page-b2__doc--post-repair', rendered.hasPostRepair);
      rebindActiveEntryHandlers(doc, concept, data, training);
      bindConceptRouteMarginHandlers(mountEl, data, concept, training);
      restoreActiveEntryDraft(entryId);
      refreshConstellationAvailability(training);
      doc.classList.remove('is-fading-out');
      void doc.offsetWidth; // force reflow so the fade-in animates
      doc.classList.add('is-fading-in');
      if (options?.focusAttempt) {
        const attemptInput = doc.querySelector('.concept-page-b2__attempt-input');
        window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
        attemptInput?.focus?.({ preventScroll: true });
      }
      setTimeout(() => doc.classList.remove('is-fading-in'), 360);
    }, 240);

    _activeEntryId = entryId;
    updateConstellationActiveEntry(entryId);
  }

  function bindConceptRouteMarginHandlers(mountEl, data, concept, training = null) {
    const route = mountEl?.querySelector('.concept-page-b2__route');
    if (!route || route.dataset.bound === 'true') return;
    route.dataset.bound = 'true';

    route.addEventListener('click', (e) => {
      const item = e.target.closest('.concept-page-b2__route-item');
      if (!item) return;
      const routeLockedInert = route.dataset.lockedInert === 'true';
      if (routeLockedInert && (drillState.active || item.dataset.routeState === 'locked')) return;
      const id = item.getAttribute('data-entry-id');
      if (id && drillState.active) {
        const activeConcept = getActiveConcept();
        cancelDrill({ restoreMap: false });
        if (activeConcept?.graphData) showMapView(activeConcept, { activeEntryId: id });
        return;
      }
      if (id) setActiveEntry(id, data, concept, training);
    });

    route.addEventListener('keydown', (e) => {
      const item = e.target.closest('.concept-page-b2__route-item');
      if (!item) return;

      if (e.key === 'Enter' || e.key === ' ') {
        const id = item.getAttribute('data-entry-id');
        const routeLockedInert = route.dataset.lockedInert === 'true';
        if (id && !(routeLockedInert && (drillState.active || item.dataset.routeState === 'locked'))) {
          e.preventDefault();
          if (drillState.active) {
            item.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
            return;
          }
          setActiveEntry(id, data, concept, training);
        }
        return;
      }

      if (e.key !== 'ArrowUp' && e.key !== 'ArrowDown') return;

      const backbone = deriveConceptEntries(data);
      if (!backbone.length) return;
      e.preventDefault();
      const dir = e.key === 'ArrowUp' ? -1 : 1;
      const currentMatch = findConceptEntryById(backbone, _activeEntryId);
      const currentIdx = currentMatch ? currentMatch.index : 0;
      const nextIdx = Math.max(0, Math.min(backbone.length - 1, currentIdx + dir));
      const nextEntry = backbone[nextIdx];
      if (!nextEntry) return;
      const nextId = getConceptEntryId(nextEntry, nextIdx);
      const nextItem = mountEl.querySelector(`.concept-page-b2__route-item[data-entry-id="${nextId}"]`);
      const routeLockedInert = route.dataset.lockedInert === 'true';
      if (routeLockedInert && (drillState.active || nextItem?.dataset?.routeState === 'locked')) return;
      if (drillState.active) {
        const activeConcept = getActiveConcept();
        cancelDrill({ restoreMap: false });
        if (activeConcept?.graphData) showMapView(activeConcept, { activeEntryId: nextId });
      } else {
        setActiveEntry(nextId, data, concept, training);
      }
      setTimeout(() => {
        nextItem?.focus();
      }, 280);
    });
  }

  function renderConceptConstellationView(mountEl, data, concept, training = null, options = {}) {
    if (!mountEl || !data) return;
    const activeId = options?.activeEntryId || _activeEntryId;
    mountEl.innerHTML = renderConceptConstellationHtml(data, {
      ...options,
      concept,
      training,
      activeEntryId: activeId,
    });
    updateConstellationActiveEntry(activeId);
  }

  function updateConstellationActiveEntry(entryId) {
    const mountEl = document.getElementById('concept-constellation-content');
    if (!mountEl || !entryId) return;
    mountEl.querySelectorAll('.concept-constellation__node').forEach((node) => {
      const isActive = node.getAttribute('data-entry-id') === entryId;
      node.classList.toggle('is-active', isActive);
      if (isActive) {
        const stateEl = mountEl.querySelector('[data-constellation-selected-state]');
        const titleEl = mountEl.querySelector('[data-constellation-selected-name]');
        const purposeEl = mountEl.querySelector('[data-constellation-selected-purpose]');
        if (stateEl) stateEl.textContent = node.getAttribute('data-state-label') || '';
        if (titleEl) titleEl.textContent = node.getAttribute('data-selected-name') || '';
        if (purposeEl) purposeEl.textContent = node.getAttribute('data-selected-purpose') || '';
      }
    });
    mountEl.querySelectorAll('.concept-constellation__edge').forEach((edge) => {
      edge.classList.toggle('is-lit', edge.getAttribute('data-edge-evidence') === 'true');
    });
  }

  /**
   * Render the B-2 route-margin concept page layout into #map-content.
   * Replaces the prior Route view card stack.
   *
   * @param {HTMLElement} mountEl - The #map-content element
   * @param {Object} data - Parsed graphData (metadata, backbone, clusters, relationships)
   * @param {Object} concept - The full concept object
   */
  function renderConceptPageB2(mountEl, data, concept, training = null, options = {}) {
    if (!mountEl || !data) return;
    setActiveConceptSourceMode(concept, data, training);
    const backbone = deriveConceptEntries(data);
    const preferredEntryId = options?.activeEntryId || null;
    const preferredEntry = preferredEntryId === 'core-thesis' && !backbone.length
      ? selectInitialConceptEntry(backbone, training)
      : findConceptEntryById(backbone, preferredEntryId);

    const {
      entry: activeEntry,
      index: activeIdx,
      id: activeEntryId,
    } = preferredEntry || selectInitialConceptEntry(backbone, training);
    const renderBackbone = backbone.length ? backbone : [activeEntry];

    const renderOptions = conceptPageRenderOptionsForEntry(concept, activeEntryId, training, options);
    const rendered = renderActiveEntryDocumentHtml(
      activeEntry,
      activeIdx,
      renderBackbone,
      concept,
      data,
      training,
      renderOptions,
    );

    // Mount the whole thing
    mountEl.classList.add('concept-page-b2');
    mountEl.innerHTML = `
      <div class="concept-page-b2__doc${rendered.hasPostRepair ? ' concept-page-b2__doc--post-repair' : ''}">
        ${rendered.html}
      </div>
    `;

    // Set module-level active entry state
    _activeEntryId = activeEntryId;

    // Wire active reconstruction, study, and repair controls.
    const docEl = mountEl.querySelector('.concept-page-b2__doc');
    if (docEl) rebindActiveEntryHandlers(docEl, concept, data, training);
    restoreActiveEntryDraft(activeEntryId);

    // Wire route-margin click + vertical keyboard nav.
    bindConceptRouteMarginHandlers(mountEl, data, concept, training);
  }

  function showMapView(concept, opts = {}) {
    const mapView = document.getElementById('map-view');
    const mapContent = document.getElementById('map-content');
    const constellationContent = document.getElementById('concept-constellation-content');
    const heroCard = document.querySelector('.hero-card');
    const libraryView = document.getElementById('library-view');

    if (!concept || !concept.graphData) return;
    showSessionRoute(concept.id, { replace: Boolean(opts.fromBoot) });

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
    const sourceTitle = String(meta.source_title || '').trim();
    const conceptTitle = String(concept.name || '').trim();
    const legacySyntheticTitle = `${conceptTitle} source-less route`;
    const displayTitle = sourceTitle === legacySyntheticTitle
      ? conceptTitle
      : (sourceTitle || conceptTitle);
    if (titleEl) titleEl.textContent = displayTitle;
    if (tagsEl) {
      tagsEl.innerHTML = '';
    }

    renderConceptPageB2(mapContent, data, concept, null, opts);
    renderConceptConstellationView(constellationContent, data, concept, null, { activeEntryId: _activeEntryId });
    refreshConstellationAvailability(null);
    // Keep first paint synchronous; training evidence re-renders when available.
    void trainingStore.loadTraining(concept.id)
      .then((training) => {
        if (!training) return;
        if (getActiveId() !== concept.id || document.body.dataset.mapOpen !== 'true') return;
        const renderOptions = { ...opts };
        if (drillState.active && drillState.node?.id) {
          renderConceptConstellationView(constellationContent, data, concept, training, { activeEntryId: _activeEntryId });
          refreshConstellationAvailability(training);
          return;
        }
        if (
          renderOptions.isDrilling
          && drillState.active
          && drillState.node?.id === renderOptions.activeEntryId
        ) {
          renderConceptConstellationView(constellationContent, data, concept, training, { activeEntryId: _activeEntryId });
          refreshConstellationAvailability(training);
          return;
        }
        if (
          renderOptions.isDrilling
          && (!drillState.active || drillState.node?.id !== renderOptions.activeEntryId)
        ) {
          renderOptions.isDrilling = false;
        }
        renderConceptPageB2(mapContent, data, concept, training, renderOptions);
        renderConceptConstellationView(constellationContent, data, concept, training, { activeEntryId: _activeEntryId });
        refreshConstellationAvailability(training);
      })
      .catch((err) => {
        /* c8 ignore next -- defensive localStorage failure branch */
        console.warn('Training records unavailable for concept page render.', err);
      });

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
    setMapMode('route');
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
      cancelDrill({ restoreMap: false });
    }
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

  function setMapMode(mode = 'route') {
    const nextMode = mode === 'constellation' ? 'constellation' : 'route';
    const mapContent = document.getElementById('map-content');
    const constellationContent = document.getElementById('concept-constellation-content');
    const mapView = document.getElementById('map-view');
    const switchBtn = conceptViewSwitchButton();

    currentMapMode = nextMode;
    if (mapContent) mapContent.hidden = nextMode !== 'route';
    if (constellationContent) constellationContent.hidden = nextMode !== 'constellation';
    if (mapView) mapView.dataset.mapMode = nextMode;
    if (switchBtn) {
      const showingConstellation = nextMode === 'constellation';
      switchBtn.textContent = showingConstellation ? 'Return to route' : 'Constellation';
      switchBtn.dataset.mapMode = showingConstellation ? 'route' : 'constellation';
      switchBtn.setAttribute('aria-pressed', String(showingConstellation));
      switchBtn.setAttribute('aria-controls', showingConstellation ? 'map-content' : 'concept-constellation-content');
    }
  }

  async function openConceptEntry(entryId, { focusAttempt = false } = {}) {
    const concept = getActiveConcept();
    const data = parseConceptGraphData(concept);
    const entries = deriveConceptEntries(data || {});
    const match = findConceptEntryById(entries, entryId);
    if (!entryId || !concept || !data || !match || entryId === _activeEntryId) return false;

    try {
      const training = await trainingStore.loadTraining(concept.id);
      const state = deriveConceptEntryViewState(entries, match.index, training);
      if (state.state === 'locked') return false;
      setActiveEntry(entryId, data, concept, training, { focusAttempt });
      return true;
    } catch (err) {
      console.warn('Concept entry unavailable.', err);
      return false;
    }
  }

  function bindMapModeControls() {
    document.addEventListener('click', (event) => {
      const target = event.target instanceof Element ? event.target : null;
      const postRepairAction = target?.closest('[data-post-repair-action]') || null;
      if (postRepairAction) {
        event.preventDefault();
        const action = postRepairAction.getAttribute('data-post-repair-action');
        if (action === 'break') {
          showDashboard();
          return;
        }
        if (action === 'next-entry') {
          const entryId = postRepairAction.getAttribute('data-entry-id');
          void openConceptEntry(entryId, { focusAttempt: true });
          return;
        }
        if (action === 'pressure-check') {
          const entryId = postRepairAction.getAttribute('data-repair-entry-id');
          const concept = getActiveConcept();
          const data = parseConceptGraphData(concept);
          if (!entryId || !concept || !data) return;
          void trainingStore.loadTraining(concept.id)
            .then((training) => startDrill(buildRepairGapDrillContext(entryId, concept, data, training)))
            .catch((err) => console.warn('Repair record unavailable for pressure-check.', err));
          return;
        }
      }
      const constellationNode = target?.closest('.concept-constellation__node[data-entry-id]') || null;
      if (constellationNode) {
        const entryId = constellationNode.getAttribute('data-entry-id');
        const state = constellationNode.getAttribute('data-state');
        const opensSuggestedRoom = constellationNode.getAttribute('data-bridge-target') === 'true';
        if (state === 'locked') return;
        if (entryId) {
          event.preventDefault();
          void openConceptEntry(entryId, { focusAttempt: opensSuggestedRoom });
        }
        return;
      }

      const button = target
        ? target.closest('button[data-map-mode]')
        : null;
      if (!button) return;
      const mode = button.getAttribute('data-map-mode');
      if (mode === 'route' || mode === 'constellation') {
        event.preventDefault();
        if (button.disabled || button.hidden || button.getAttribute('aria-disabled') === 'true') return;
        setMapMode(mode);
      }
    });

    document.addEventListener('keydown', (event) => {
      if (event.key !== 'Enter' && event.key !== ' ') return;
      const target = event.target instanceof Element ? event.target : null;
      const constellationNode = target?.closest('.concept-constellation__node[data-entry-id]') || null;
      if (!constellationNode) return;
      event.preventDefault();
      void openConceptEntry(
        constellationNode.getAttribute('data-entry-id'),
        { focusAttempt: constellationNode.getAttribute('data-bridge-target') === 'true' },
      );
    });

  }

  function setNavActive(id) {
    currentPrimaryNav = id;
    document.body.dataset.primaryView = id === 'nav-dashboard'
      ? 'desk'
      : id ? id.replace('nav-', '') : 'concept';
    ['nav-dashboard', 'nav-ignition', 'nav-library', 'nav-settings'].forEach((navId) => {
      const el = document.getElementById(navId);
      const isActive = navId === currentPrimaryNav;
      if (el) {
        el.classList.toggle('active', isActive);
        if (isActive) el.setAttribute('aria-current', 'page');
        else el.removeAttribute('aria-current');
      }

      const bnId = navId.replace('nav-', 'bn-');
      const bnEl = document.getElementById(bnId);
      if (bnEl) {
        bnEl.classList.toggle('active', isActive);
        if (isActive) bnEl.setAttribute('aria-current', 'page');
        else bnEl.removeAttribute('aria-current');
      }
    });
    syncConceptListActiveState();
  }

  function showDashboard() {
    clearSessionRoute();
    setNavActive('nav-dashboard');
    const heroCard = document.querySelector('.hero-card');

    clearSettingsPanel();
    teardownMapView();
    hidePrimaryViews();
    if (heroCard) heroCard.style.display = 'flex';
    renderDeskDueSurfaces();
    Bus.emit('dashboard:shown');
    if (window.innerWidth < 900) closeDrawer();
  }

  function collectTrainingByConceptId(concepts = loadConcepts()) {
    const trainingByConceptId = {};
    (Array.isArray(concepts) ? concepts : []).forEach((concept) => {
      if (!concept?.id) return;
      try {
        const raw = localStorage.getItem(`${TRAINING_STORE_KEY_PREFIX}${concept.id}`);
        if (!raw) return;
        const parsed = JSON.parse(raw);
        if (parsed && typeof parsed === 'object') {
          trainingByConceptId[concept.id] = parsed;
        }
      } catch {
        /* ignore corrupt training rows */
      }
    });
    return trainingByConceptId;
  }

  function refreshDueCache(concepts = loadConcepts()) {
    cachedDueItems = listDueForSpaced({
      concepts,
      trainingByConceptId: collectTrainingByConceptId(concepts),
    });
    if (!cachedDueItems.length) readyFilterActive = false;
    return cachedDueItems;
  }

  function renderReadyFilter() {
    const host = document.getElementById('desk-ready-filter-host');
    if (!host) return;
    const dueSessionCount = dueConceptIdSet(cachedDueItems).size;
    host.innerHTML = renderReadyFilterHtml({
      count: dueSessionCount,
      active: readyFilterActive,
    });
    const button = host.querySelector('#desk-ready-filter');
    if (!button) return;
    button.addEventListener('click', () => {
      readyFilterActive = !readyFilterActive;
      renderDeskDueSurfaces();
    });
  }

  function renderDueSelection() {
    const host = document.getElementById('desk-due-selection-host');
    if (!host) return;
    const activeId = getActiveId();
    const selectedDue = dueItemsForConcept(cachedDueItems, activeId);
    host.innerHTML = renderDueSelectionHtml(selectedDue);
    host.querySelectorAll('.desk-due-selection__action[data-concept-id]').forEach((button) => {
      button.addEventListener('click', () => {
        const conceptId = button.getAttribute('data-concept-id');
        const nodeId = button.getAttribute('data-node-id');
        if (!conceptId) return;
        const concept = loadConcepts().find((c) => c.id === conceptId);
        if (!concept) return;
        selectConcept(conceptId);
        if (!concept.graphData) return;
        const opts = nodeId ? { activeEntryId: nodeId } : {};
        showMapView(concept, opts);
      });
    });
  }

  function renderDeskDueSurfaces() {
    refreshDueCache();
    renderReadyFilter();
    renderDueSelection();
    renderGrid();
    const grid = document.getElementById('grid-container');
    if (!grid) return;
    const dueSessionCount = dueConceptIdSet(cachedDueItems).size;
    grid.classList.toggle('is-ready-filtered', readyFilterActive && dueSessionCount > 0);
    if (dueSessionCount) {
      grid.setAttribute('data-ready-count', String(dueSessionCount));
    } else {
      grid.removeAttribute('data-ready-count');
    }
  }

  Bus.on('desk:external-state-change', () => {
    renderConceptList();
    renderIgnitionGate();
    renderDeskDueSurfaces();
  });

  async function syncLearnerStateIfIdentified() {
    try {
      const session = await fetchAuthSession();
      if (!isIdentifiedUserSession(session)) return false;
      await hydrateAndSyncLearnerState({ isIdentified: true });
      renderConceptList();
      renderDeskDueSurfaces();
      return true;
    } catch (err) {
      console.warn('Learner state sync unavailable.', err);
      return false;
    }
  }

  async function pushLearnerStateIfIdentified() {
    try {
      const session = await fetchAuthSession();
      if (!isIdentifiedUserSession(session)) return;
      await pushLocalLearnerState({ isIdentified: true });
    } catch (err) {
      console.warn('Learner state push unavailable.', err);
    }
  }

  function sessionRouteConceptId() {
    const match = window.location.pathname.match(/^\/session\/([^/?#]+)/);
    if (!match) return '';
    try {
      return decodeURIComponent(match[1]);
    } catch {
      return '__malformed_session_route__';
    }
  }

  function showSessionRoute(conceptId, { replace = false } = {}) {
    if (!conceptId || !window.history?.pushState) return;
    const target = `/session/${encodeURIComponent(conceptId)}`;
    if (window.location.pathname === target) return;
    const method = replace ? 'replaceState' : 'pushState';
    window.history[method]({}, '', target);
  }

  function clearSessionRoute() {
    if (!window.history?.pushState || !window.location.pathname.startsWith('/session/')) return;
    window.history.pushState({}, '', '/');
  }

  function showMissingSessionFallback() {
    window.history?.replaceState?.({}, '', '/');
    showIgnition();
    const errEl = document.getElementById('hero-door-error');
    if (errEl) {
      errEl.textContent = 'That session is not saved in this browser.';
      errEl.hidden = false;
    }
  }

  function syncViewFromLocation() {
    const conceptId = sessionRouteConceptId();
    if (!conceptId) {
      showDashboard();
      return;
    }

    const concept = loadConcepts().find((item) => item.id === conceptId && item.graphData);
    if (!concept) {
      showMissingSessionFallback();
      return;
    }
    activateConceptSelection(concept.id);
    showMapView(concept);
  }

  function showIgnition() {
    clearSessionRoute();
    setNavActive('nav-ignition');
    clearSettingsPanel();
    teardownMapView();
    hidePrimaryViews();
    document.getElementById('ignition-view').hidden = false;
    renderIgnitionGate();
    if (window.innerWidth < 900) closeDrawer();
    requestAnimationFrame(() => doorSource.focusCurrent());
  }

  function renderIgnitionGate() {
    const gate = document.getElementById('ignition-cap-gate');
    const form = document.getElementById('hero-single-input');

    if (gate) gate.hidden = true;
    if (form) {
      form.dataset.state = northStarBusy ? 'busy' : '';
      form.setAttribute('aria-busy', northStarBusy ? 'true' : 'false');
    }
    doorSource.render(northStarSession?.awaiting?.key === 'target', northStarBusy);
    _doorUpdateSubmitState();

    ['nav-ignition', 'bn-ignition'].forEach((id) => {
      const el = document.getElementById(id);
      if (!el) return;
      el.classList.remove('at-cap');
      el.title = '';
    });
  }

  function showLibrary() {
    clearSessionRoute();
    setNavActive('nav-library');
    const libraryView = document.getElementById('library-view');
    const content = document.getElementById('library-content');

    clearSettingsPanel();
    teardownMapView();
    hidePrimaryViews();
    const concepts = loadConcepts().filter(c => c.graphData);
    const libraryOptions = { showLocalQaSeed: localQaSeedControlsEnabled() };

    content.innerHTML = buildLibraryHtml(concepts, {}, libraryOptions);

    libraryView.classList.add('visible');
    if (window.innerWidth < 900) closeDrawer();

    if (!concepts.length) return;

    // Keep Library open immediately; learner evidence fills in asynchronously.
    Promise.all(concepts.map(async (concept) => {
      const conceptId = String(concept.id);
      try {
        return [conceptId, await trainingStore.loadTraining(concept.id)];
      } catch (err) {
        /* c8 ignore next -- defensive corrupt localStorage branch */
        console.warn('Training record unavailable for library concept.', conceptId, err);
        return [conceptId, null];
      }
    }))
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
      /* c8 ignore next -- defensive fallback for malformed concept data after a map launch. */
      showDashboard();
    }
  }

  // ── 17. Init + restore ─────────────────────────────────────




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

  document.addEventListener('click', (event) => {
    const target = event.target;
    if (target instanceof Element && target.closest('#concept-list .concept-actions, #concept-list .concept-action-menu')) return;
    closeConceptActionMenus();
  });

  // Render grid first (populates polygon DOM nodes)
  themePreference = getStoredThemePreference();
  applyThemePreference(themePreference, { persist: false });
  void bootstrapAuthUi();
  void refreshDrawerFooter();
  bindMapModeControls();
  renderConceptList();
  renderDeskDueSurfaces();
  renderIgnitionGate();
  initHeroSingleInput();
  void syncLearnerStateIfIdentified();

  // Restore selected concept
  const concepts = loadConcepts();
  const routeConceptId = sessionRouteConceptId();
  const routeConcept = routeConceptId
    ? concepts.find((concept) => concept.id === routeConceptId && concept.graphData)
    : null;
  const pendingResumeState = loadPhaseBResumeState();
  const resumeConcept = pendingResumeState
    ? concepts.find((concept) => concept.id === pendingResumeState.conceptId && concept.graphData)
    : null;
  const toLoad = routeConcept || resumeConcept || concepts.find(c => c.id === getActiveId()) || concepts[0] || null;

  if (pendingResumeState && !resumeConcept) {
    /* c8 ignore next -- defensive cleanup for stale browser resume state. */
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
    sedaSessionId: null,
    sedaSessionVersion: null,
    sedaPendingSubmission: null,
    sedaActive: false,
  };

  // Tracks the last AI question shown in the chamber so the next learner
  // turn can be paired with it in history. Owned by requestDrillTurn.
  let chamberLastShownQuestion = '';

  // Boot routing runs AFTER drillState is initialized because showIgnition()
  // calls teardownMapView() which reads drillState — TDZ-unsafe earlier.
  if (routeConceptId && !routeConcept) {
    showMissingSessionFallback();
  } else if (!routeConcept && !resumeConcept) {
    showIgnition();
  } else {
    activateConceptSelection(toLoad.id);
    if (routeConcept || (resumeConcept && resumeConcept.id === toLoad.id)) {
      showMapView(toLoad, { fromBoot: Boolean(routeConcept) });
    }
  }
  window.addEventListener('popstate', syncViewFromLocation);

  function createDrillLogSessionId() {
    if (window.crypto?.randomUUID) return window.crypto.randomUUID();
    return `drill-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  }

  function sedaSessionKey(conceptId) {
    return `${SEDA_SESSION_STORE_KEY_PREFIX}${conceptId}`;
  }

  function loadSedaSessionState(conceptId) {
    try {
      const raw = localStorage.getItem(sedaSessionKey(conceptId));
      return raw ? JSON.parse(raw) : null;
    } catch {
      /* c8 ignore next -- defensive corrupt localStorage branch. */
      return null;
    }
  }

  function persistSedaSessionState(conceptId, state) {
    try {
      localStorage.setItem(sedaSessionKey(conceptId), JSON.stringify({
        ...state,
        updatedAt: new Date().toISOString(),
      }));
      return true;
    } catch (err) {
      /* c8 ignore next 2 -- defensive localStorage failure branch. */
      console.warn('SEDA session state unavailable.', err);
      return false;
    }
  }

  function clearSedaSessionState(conceptId) {
    try {
      localStorage.removeItem(sedaSessionKey(conceptId));
    } catch (err) {
      /* c8 ignore next -- defensive localStorage failure branch. */
      console.warn('SEDA session state could not be cleared.', err);
    }
  }

  function routeUnavailableError(reason) {
    const error = new Error(`Source-less route unavailable: ${reason}`);
    error.code = 'route_unavailable';
    error.reason = reason;
    return error;
  }

  function assertSedaStartupStillCurrent(conceptId, sessionToken) {
    if (
      sessionToken == null
      || (
        drillState.sessionToken === sessionToken
        && drillState.sedaActive
        && getActiveId() === conceptId
      )
    ) return;
    const error = new Error('Discarded a stale SEDA startup response.');
    error.code = 'stale_seda_start';
    throw error;
  }

  async function hasRecordedConceptEvidence(conceptId) {
    const training = await trainingStore.loadTraining(conceptId);
    return Object.values(training?.node_records || {}).some((record) => (
      (Array.isArray(record?.attempts) && record.attempts.length > 0)
      || (Array.isArray(record?.repairs) && record.repairs.length > 0)
    ));
  }

  function resetSourceLessRouteForFreshStart(concept) {
    const graphData = parseConceptGraphData(concept) || {};
    const persisted = persistActiveConceptGraphData(
      clearBoundSourceLessSedaRoute(graphData),
      { conceptId: concept.id },
    );
    if (!persisted) return null;
    clearSedaSessionState(concept.id);
    freshSourceLessConceptIds.add(concept.id);
    concept.graphData = persisted.graphData;
    return persisted;
  }

  function sedaPromptFromResponse(data) {
    return visibleSedaPromptFromResponse(data);
  }

  function drillPromptFromSedaResponse(data, nodeContext, concept) {
    return data?.awaiting?.key === 'launch_attempt'
      ? drillQuestionForNodeContext(nodeContext, concept)
      : sedaPromptFromResponse(data);
  }

  function openStudyAfterVerdict(conceptId, nodeId) {
    cancelDrill();
    const concept = loadConcepts().find((item) => item?.id === conceptId) || getActiveConcept();
    if (!concept) return;
    void revealStudyForEntry(nodeId, concept, parseConceptGraphData(concept) || {});
  }

  function restoreUnrecordedDraft(text, { chamber = false, entryId = null } = {}) {
    const draft = String(text || '').trim();
    if (!draft) return;
    if (chamber) {
      const target = document.getElementById('chamber-composer');
      if (target && 'value' in target) target.value = draft;
      return;
    }
    const resolvedEntryId = entryId || drillState.node?.id || _activeEntryId;
    if (!resolvedEntryId) return;
    routeAttemptDrafts.set(routeAttemptDraftKey(resolvedEntryId), draft);
    restoreActiveEntryDraft(resolvedEntryId);
  }

  async function saveSedaResponse(concept, nodeContext, data) {
    if (!concept?.id || !data?.sessionId) return false;
    sessionVersionFromResponse(data);
    const persisted = persistSedaSessionState(concept.id, {
      sessionId: data.sessionId,
      sessionVersion: data.sessionVersion,
      nodeId: nodeContext?.id || null,
      latest: data,
      record: data.record || null,
    });
    if (!persisted) return false;
    if (data.caseComplete && data.record) {
      return projectSedaEvidence(concept, nodeContext, data);
    }
    return !data.caseComplete;
  }

  // Reconstruction evidence must survive outside the chamber: project the
  // completed session record into the training store the concept page,
  // Library, and board read from.
  async function projectSedaEvidence(concept, nodeContext, data) {
    try {
      const training = await trainingStore.loadTraining(concept.id);
      const next = projectCompletedSedaRecord({
        training,
        conceptId: concept.id,
        nodeId: nodeContext?.id || null,
        record: data.record,
        sessionId: data.sessionId,
      });
      /* c8 ignore start -- completed-record idempotency is proven in the projection module contract. */
      if (!next) {
        const attempts = training?.node_records?.[nodeContext?.id || '']?.attempts;
        return Array.isArray(attempts) && attempts.some(
          (attempt) => attempt?.id === `seda-${data.sessionId}-0`,
        );
      }
      /* c8 ignore stop */
      await trainingStore.saveTraining(next);
      return true;
    } catch (err) {
      /* c8 ignore next 2 -- defensive storage failure branch. */
      console.warn('SEDA evidence projection unavailable.', err);
      return false;
    }
  }

  async function projectSedaAttemptEvent(concept, nodeContext, data) {
    try {
      const training = await trainingStore.loadTraining(concept.id);
      const next = projectLatestSedaAttemptEvent({
        training,
        conceptId: concept.id,
        nodeId: nodeContext?.id || null,
        data,
        sessionId: data.sessionId,
      });
      if (!next) {
        const attempts = training?.node_records?.[nodeContext?.id || '']?.attempts;
        const prefix = `seda-${data.sessionId}-event-`;
        const projected = Array.isArray(attempts)
          ? attempts.findLast((attempt) => String(attempt?.id || '').startsWith(prefix))
          : null;
        return { ok: true, classification: projected?.classification || null };
      }
      await trainingStore.saveTraining(next);
      const projected = next.node_records?.[nodeContext?.id || ''];
      const attempts = Array.isArray(projected?.attempts) ? projected.attempts : [];
      return {
        ok: true,
        classification: attempts[attempts.length - 1]?.classification || true,
      };
    } catch (err) {
      /* c8 ignore next 2 -- defensive storage failure branch. */
      console.warn('SEDA attempt projection unavailable.', err);
      return { ok: false, classification: null };
    }
  }

  function sessionVersionFromResponse(data) {
    const version = data?.sessionVersion;
    if (!Number.isInteger(version) || version < 0) {
      /* c8 ignore next -- transport helpers and server contracts reject invalid versions before this browser boundary. */
      throw new Error('The learning loop returned an invalid session version.');
    }
    return version;
  }

  function sedaSubmissionForResponse(text, data, requestId = null) {
    return createSedaTurnSubmission(
      text,
      sessionVersionFromResponse(data),
      requestId,
    );
  }

  async function loadOrCreateSedaResponse(
    concept,
    nodeContext,
    { sessionToken = null } = {},
  ) {
    const existingGraphData = parseConceptGraphData(concept) || {};
    const expectedGraphRevision = String(concept.graphData || '');
    const sourceLess = isSourceLessConcept(concept, existingGraphData);
    const routeBound = sourceLess && hasBoundSourceLessSedaRoute(existingGraphData);
    const durablePendingRoute = hasPendingSourceLessSedaRoute(
      concept,
      existingGraphData,
    );
    if (
      durablePendingRoute
      && await hasRecordedConceptEvidence(concept.id)
    ) {
      throw routeUnavailableError('pending_route_has_evidence');
    }
    if (
      sourceLess
      && !routeBound
      && !durablePendingRoute
      && !freshSourceLessConceptIds.has(concept.id)
    ) {
      throw routeUnavailableError('unbound_route_requires_confirmation');
    }
    const resumingBoundNode = routeBound
      && nodeContext?.id === boundSourceLessSedaNodeId(existingGraphData);
    if (routeBound && !resumingBoundNode) {
      throw routeUnavailableError('bound_node_mismatch');
    }
    const boundSessionId = resumingBoundNode
      ? boundSourceLessSedaSessionId(existingGraphData)
      : '';
    if (resumingBoundNode && !boundSessionId) {
      throw routeUnavailableError('missing_bound_session');
    }
    const stored = loadSedaSessionState(concept.id);
    const sameStoredNode = Boolean(stored?.nodeId && stored.nodeId === nodeContext?.id);
    const sameBoundSession = !resumingBoundNode || stored?.sessionId === boundSessionId;
    let data = null;
    if (stored?.sessionId && sameStoredNode && sameBoundSession && !stored?.latest?.caseComplete) {
      try {
        data = await getSedaSession(stored.sessionId);
      } catch {
        /* c8 ignore next -- the bound-session guard below fails closed after a stale resume. */
        data = null;
      }
    }
    if (!data) {
      if (resumingBoundNode) {
        throw routeUnavailableError('stale_bound_session');
      }
      data = await createSedaSession({ sourceLessDoorBootstrap: sourceLess });
    }
    if (resumingBoundNode && data?.sessionId !== boundSessionId) {
      throw routeUnavailableError('bound_session_mismatch');
    }
    if (data?.awaiting?.key === 'cmd') {
      data = await sendSedaTurn(
        data.sessionId,
        sedaSubmissionForResponse(concept.name || 'Untitled concept', data),
      );
    }
    if (data?.awaiting?.key === 'learner_goal') {
      data = await sendSedaTurn(
        data.sessionId,
        sedaSubmissionForResponse(concept.learnerGoal || '', data),
      );
    }
    if (data?.awaiting?.key === 'launch_attempt') {
      const launchAttempt = sourceLess
        ? String(
          concept.startingMapContext
          || existingGraphData?.metadata?.starting_map_context
          || ''
        ).trim()
        : '';
      if (launchAttempt) {
        // The source-less Door already captured this global starting model.
        // Feed it into SEDA before the chamber opens so the first answer the
        // learner writes in the room is the local, recordable cold attempt.
        // This bootstrap turn bypasses requestSedaTurn on purpose: launch
        // attempts shape routing but never append learner training evidence.
        data = await sendSedaTurn(
          data.sessionId,
          sedaSubmissionForResponse(launchAttempt, data),
        );
      }
    }

    // Model-backed route generation can finish after the learner has exited or
    // selected another concept. Do not let that late response write local
    // session, graph, or drill state into a different active surface.
    assertSedaStartupStillCurrent(concept.id, sessionToken);

    if (resumingBoundNode && data?.awaiting?.key === 'cold_attempt') {
      const readyRoute = readySourceLessSedaRoute(data);
      if (String(readyRoute.first_node?.id || '').trim() !== boundSourceLessSedaNodeId(existingGraphData)) {
        throw routeUnavailableError('bound_route_mismatch');
      }
    }

    let routeBinding = null;
    let activeConcept = concept;
    let responseSavedForBinding = false;
    if (sourceLess && !routeBound) {
      // SEDA chooses the actual learning target only after reading the Door
      // sketch. Bind and persist that route before the composer can open, so
      // prompt, evidence, and study all point at the same authoritative node.
      // Any malformed/missing route fails into the existing retry UI before
      // session state or learner training evidence is written.
      routeBinding = bindSourceLessSedaRoute({
        data,
        existingMap: existingGraphData,
        concept,
      });
      Object.assign(nodeContext, routeBinding.nodeContext, { drillMode: 'seda' });
      // Save the exact bound node/session before stamping the map marker. If
      // session storage is unavailable, fail without leaving a graph that
      // claims it has a resumable authoritative route.
      responseSavedForBinding = await saveSedaResponse(concept, nodeContext, data);
      /* c8 ignore start -- defensive browser-storage failure; save/persistence retry UX is covered on the active turn path. */
      if (!responseSavedForBinding) {
        throw new Error('Could not persist the source-less SEDA session.');
      }
      /* c8 ignore stop */
      const persistedConcept = persistActiveConceptGraphData(
        routeBinding.graphData,
        { conceptId: concept.id, expectedGraphRevision },
      );
      /* c8 ignore start -- stale graph revision is rejected before route state can be stamped. */
      if (!persistedConcept) {
        clearSedaSessionState(concept.id);
        throw new Error('Could not persist the source-less SEDA route.');
      }
      /* c8 ignore stop */
      activeConcept = persistedConcept;
      concept.graphData = persistedConcept.graphData;
      freshSourceLessConceptIds.delete(concept.id);
      drillState.node = nodeContext;
      activeDrillNode = nodeContext.id;
    }

    if (!responseSavedForBinding) {
      const responseSaved = await saveSedaResponse(activeConcept, nodeContext, data);
      /* c8 ignore start -- defensive browser-storage failure on bound-session resume. */
      if (!responseSaved) {
        throw new Error('Could not persist the source-less SEDA response.');
      }
      /* c8 ignore stop */
    }
    return { data, routeBinding, concept: activeConcept };
  }

  function parseConceptGraphData(concept) {
    if (!concept?.graphData) return null;
    return normalizeGraphData(concept.graphData).graphData;
  }

  function persistActiveConceptGraphData(
    graphData,
    { conceptId = getActiveId(), expectedGraphRevision = null } = {},
  ) {
    const concepts = loadConcepts();
    const conceptIdx = concepts.findIndex((concept) => concept.id === conceptId);
    if (conceptIdx === -1) return null;
    if (
      expectedGraphRevision != null
      && String(concepts[conceptIdx].graphData || '') !== expectedGraphRevision
    ) {
      /* c8 ignore next -- late-response CAS failure is covered through the stale-start browser contract. */
      return null;
    }

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
      label: nodeContext.type === 'core' ? 'Start With Core Thesis' : 'Write from memory',
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
    setMapMode('graph');
    return true;
  }

  async function startRepairReps(nodeContext) {
    const concept = getActiveConcept();
    if (!concept || !nodeContext?.id) return;

    const graphData = parseConceptGraphData(concept);
    const nodeData = resolveNodeData(graphData || {}, nodeContext.id) || {};
    if (!isRepairRepsEligible(nodeData)) {
      return;
    }

    const nodeLabel = nodeContext.fullLabel || nodeContext.label || concept.name || 'Repair target';
    activeDrillNode = nodeContext.id;
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
  }

  function reopenStudy(nodeContext) {
    startDrill({ ...nodeContext, graphNeutral: true, drillMode: 'seda' });
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
    /* c8 ignore next 3 -- completeStudy reset mirrors cancelDrill; SEDA state mutation is covered in the active path. */
    drillState.sedaSessionId = null;
    drillState.sedaSessionVersion = null;
    drillState.sedaPendingSubmission = null;
    drillState.sedaActive = false;
    drillState.sessionToken += 1;
    if (drillUi) drillUi.style.display = 'none';
    if (chatHistory) chatHistory.innerHTML = '';
    if (chatInput) {
      chatInput.value = '';
      chatInput.disabled = true;
    }

    persistPhaseBResumeState(null);
    activeDrillNode = null;
  }

  function patchActiveConceptDrillOutcome(result, drillMode, options = {}) {
    const resolvedColdAttempt = drillMode === 'cold_attempt' && options.coldAttemptRecorded === true;
    const isResolvedSessionComplete = result?.routing === 'SESSION_COMPLETE'
      && (drillMode === 'cold_attempt'
        ? resolvedColdAttempt
        : Boolean(result?.classification));

    if (
      !result?.node_id
      || (drillMode === 'cold_attempt' && !resolvedColdAttempt)
      || (drillMode !== 'cold_attempt' && result?.routing !== 'NEXT' && !isResolvedSessionComplete)
    ) {
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
      if (drillMode === 'cold_attempt' && resolvedColdAttempt) {
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

    /* v8 ignore start -- legacy embedded action parser is defensive; active loop routing uses typed turn responses. */
    let action = null;
    try {
      action = JSON.parse(match[1]);
    } catch (err) {
      console.warn('Failed to parse SYSTEM_ACTION payload', err);
    }

    const visibleText = rawText.replace(match[0], '').trim();
    return { visibleText, action };
    /* v8 ignore stop */
  }

  function handleSystemAction(action) {
    if (!action) return;

    if (action.action === 'UPDATE_NODE_STATE' && action.id && action.newState) {
      if (action.newState === 'solidified' && activeDrillNode === action.id) {
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

  function presentSedaSurface(data, { challengePrompt = null } = {}) {
    const surface = sedaSurfaceFromResponse(data);
    const chamber = window.DrillChamber;
    if (!chamber) return surface;

    chamber.setSurface?.(surface.mode, surface);
    chamber.setQuestion?.(surface.mode === 'challenge' && challengePrompt
      ? challengePrompt
      : surface.question);
    chamber.setComposerEnabled(surface.composerEnabled);
    if (surface.verdict) chamber.appendVerdict?.(surface.verdict);
    if (surface.completionAction) {
      const actionLabel = surface.completionAction.kind === 'study'
        ? sedaCompleteCompletionLabel()
        : surface.completionAction.label;
      chamber.setCompletionAction?.(actionLabel, () => {
        if (surface.completionAction.kind === 'return') {
          cancelDrill();
          return;
        }
        if (surface.completionAction.kind === 'study') {
          openStudyAfterVerdict(getActiveConcept()?.id, drillState.node?.id);
          return;
        }
        void requestSedaTurn(surface.completionAction.value, { internal: true });
      });
    }
    return surface;
  }

  async function requestSedaTurn(userText, { internal = false } = {}) {
    const concept = getActiveConcept();
    if (!concept || !drillState.node || !drillState.sedaSessionId) return;
    const sessionToken = drillState.sessionToken;

    drillState.pending = true;
    if (chatInput) chatInput.disabled = true;
    showTypingIndicator();
    window.DrillChamber?.setLoading?.(true, {
      checkingAnswer: !internal && Boolean(String(userText || '').trim()),
    });

    const normalizedText = String(userText ?? '');
    const pendingSubmission = drillState.sedaPendingSubmission;
    const submission = pendingSubmission?.text === normalizedText
      ? pendingSubmission
      : createSedaTurnSubmission(normalizedText, drillState.sedaSessionVersion);
    drillState.sedaPendingSubmission = submission;

    try {
      const data = await sendSedaTurn(drillState.sedaSessionId, submission);
      hideTypingIndicator();
      if (sessionToken !== drillState.sessionToken || !drillState.node) return;
      const responseSaved = await saveSedaResponse(concept, drillState.node, data);
      /* c8 ignore start -- session-state storage failure shares the proven idempotent persistence-retry UI. */
      if (!responseSaved) {
        showSedaPersistenceRetry(normalizedText, { internal });
        return;
      }
      /* c8 ignore stop */
      if (sessionToken !== drillState.sessionToken || !drillState.node) return;
      const projectedAttempt = data.caseComplete
        ? { ok: true, classification: null }
        : await projectSedaAttemptEvent(concept, drillState.node, data);
      if (!projectedAttempt.ok) {
        showSedaPersistenceRetry(normalizedText, { internal });
        return;
      }
      drillState.sedaPendingSubmission = null;
      drillState.sedaSessionId = data.sessionId;
      drillState.sedaSessionVersion = sessionVersionFromResponse(data);
      const projectedAttemptClassification = projectedAttempt.classification;
      if (sessionToken !== drillState.sessionToken || !drillState.node) return;
      const surface = sedaSurfaceFromResponse(data);
      const studyReady = data.caseComplete || (
        Boolean(projectedAttemptClassification) && surface.mode === 'unsupported'
      );
      if (!internal) drillState.messages.push({ role: 'user', content: normalizedText });
      drillState.messages.push({ role: 'assistant', content: surface.prompt });
      chamberLastShownQuestion = surface.prompt;
      drillState.pending = false;
      drillState.sessionCompletePending = Boolean(studyReady || surface.mode === 'settle');
      persistSessionState();

      if (window.DrillChamber) {
        window.DrillChamber.setLoading?.(false);
        presentSedaSurface(data);
        if (!internal && (studyReady || surface.mode === 'gap')) {
          window.DrillChamber.appendVerdict?.(verdictCopy({
            userText,
            sedaComplete: data.caseComplete,
            classification: projectedAttemptClassification || undefined,
          }));
        } else if (!internal && surface.mode === 'challenge') {
          const lastEvent = Array.isArray(data?.events) ? data.events.at(-1) : null;
          if (lastEvent?.graph_neutral === true && lastEvent?.score_eligible === false) {
            window.DrillChamber.appendVerdict?.(verdictCopy({ userText, recordable: false }));
          }
        }
        if (studyReady && surface.mode !== 'complete') {
          window.DrillChamber.setCompletionAction?.(
            sedaCompleteCompletionLabel(),
            () => openStudyAfterVerdict(concept.id, drillState.node?.id),
          );
        }
      }
    } catch (err) {
      /* c8 ignore start -- stale/error SEDA turn handling is defensive; happy path is covered by product e2e. */
      hideTypingIndicator();
      if (sessionToken !== drillState.sessionToken) return;
      drillState.pending = false;
      window.DrillChamber?.setLoading?.(false);
      if (err?.status === 409 && err?.body?.error === 'session_conflict') {
        await reconcileSedaSessionConflict(concept, normalizedText, sessionToken, { internal });
        return;
      }
      console.error(err);
      showSedaTransportRetry(normalizedText, { internal });
      return;
      /* c8 ignore stop */
    }
  }

  function showSedaPersistenceRetry(userText, { internal = false } = {}) {
    drillState.pending = false;
    window.DrillChamber?.setLoading?.(false);
    window.DrillChamber?.appendVerdict?.(
      'Answer received • Not saved in this browser yet.',
    );
    window.DrillChamber?.setCompletionAction?.('Try saving again', () => {
      window.DrillChamber?.setComposerEnabled(false);
      void requestSedaTurn(userText, { internal });
    });
    if (!internal) restoreUnrecordedDraft(userText, { chamber: true });
  }

  function showSedaTransportRetry(userText, { internal = false } = {}) {
    drillState.pending = false;
    window.DrillChamber?.setLoading?.(false);
    window.DrillChamber?.appendVerdict?.(
      'Answer kept • Not recorded • The learning loop did not respond.',
    );
    window.DrillChamber?.setCompletionAction?.('Try sending again', () => {
      window.DrillChamber?.setComposerEnabled(false);
      void requestSedaTurn(userText, { internal });
    });
    // Completion actions normally clear the composer. Put the learner's exact
    // draft back after installing the retry action so a network failure never
    // turns visible effort into a blank form.
    if (!internal) restoreUnrecordedDraft(userText, { chamber: true });
  }

  async function reconcileSedaSessionConflict(concept, draft, sessionToken, { internal = false } = {}) {
    try {
      const latest = await getSedaSession(drillState.sedaSessionId);
      if (sessionToken !== drillState.sessionToken || !drillState.node) return;
      const responseSaved = await saveSedaResponse(concept, drillState.node, latest);
      /* c8 ignore start -- conflict refresh storage failure reuses the persistence-retry contract. */
      if (!responseSaved) {
        showSedaPersistenceRetry(draft, { internal });
        return;
      }
      /* c8 ignore stop */
      drillState.sedaSessionVersion = sessionVersionFromResponse(latest);
      // A stale submission belongs to the prompt/version that produced it.
      // Clearing it here ensures an explicit resubmit gets a fresh id bound to
      // the newly fetched prompt instead of silently replaying stale text.
      drillState.sedaPendingSubmission = null;
      drillState.pending = false;
      /* c8 ignore start -- defensive conflict after remote case completion returns the preserved draft to the map. */
      if (latest.caseComplete) {
        window.DrillChamber?.appendVerdict?.(
          'Session changed in another tab • Your draft was not recorded.',
        );
        window.DrillChamber?.setCompletionAction?.('Return to map', () => {
          const entryId = drillState.node?.id;
          cancelDrill();
          restoreUnrecordedDraft(draft, { entryId });
        });
        return;
      }
      /* c8 ignore stop */
      const currentPrompt = sedaPromptFromResponse(latest);
      chamberLastShownQuestion = currentPrompt;
      presentSedaSurface(latest);
      if (!internal) restoreUnrecordedDraft(draft, { chamber: true });
      window.DrillChamber?.appendVerdict?.(
        'Session changed in another tab • Review the current question, then check your draft again.',
      );
    } catch (refreshError) {
      /* c8 ignore start -- refresh transport failure preserves the draft and is covered by the general transport-retry proof. */
      console.error(refreshError);
      if (sessionToken !== drillState.sessionToken) return;
      if (!internal) restoreUnrecordedDraft(draft, { chamber: true });
      window.DrillChamber?.appendVerdict?.(
        'Session changed in another tab • Your draft was not recorded.',
      );
      window.DrillChamber?.setComposerEnabled(true);
      /* c8 ignore stop */
    }
  }

  async function requestDrillTurn(userText) {
    const concept = getActiveConcept();
    if (!concept || !drillState.node) return;
    if (drillState.sedaActive) {
      await requestSedaTurn(userText);
      return;
    }
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

    const nodeData = resolveNodeData(knowledgeMap, drillState.node.id) || {};
    const graphNeutralDrill = drillState.node.graphNeutral === true;
    let drillMode = drillState.node.drillMode || 'cold_attempt';
    let reDrillCount = nodeData.re_drill_count || 0;
    if (
      !drillState.node.drillMode
      && (
      nodeData.drill_status === 'drilled'
      || (nodeData.drill_status === 'primed' && nodeData.drill_phase === 're_drill')
      )
    ) {
      drillMode = 're_drill';
    }

    try {
      const data = await runDrillTurn({
        concept_id: concept.id,
        node_id: drillState.node.id,
        node_label: nodeLabel,
        node_mechanism: boundedDrillNodeMechanism(drillState.node.repairContext || drillState.node.detail || ''),
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

      const completedColdAttempt = !graphNeutralDrill
        && drillMode === 'cold_attempt'
        && data.generative_commitment === true
        && isRecordableDrillAttempt(data);
      const terminalReDrillTurn = (
        data.routing === 'NEXT'
        || (data.routing === 'SESSION_COMPLETE' && !!data.classification)
      );
      const completedReDrill = !graphNeutralDrill && terminalReDrillTurn;
      const completedGraphNeutralReDrill = graphNeutralDrill && terminalReDrillTurn;
      const completedNodeTurn = completedColdAttempt || completedReDrill || completedGraphNeutralReDrill;

      if ((completedColdAttempt || completedReDrill) && userText) {
        const training = await appendTrainingAttemptFromDrillTurn({
          conceptId: concept.id,
          nodeId: drillState.node.id,
          userText,
          result: data,
          at: turnStartedAt,
        });
        if (!training) throw new Error('attempt-not-recorded');
      }

      if (!graphNeutralDrill) {
        patchActiveConceptDrillOutcome(data, drillMode, { coldAttemptRecorded: completedColdAttempt });
      }

      const handleVisualTransition = async () => {
        drillState.messages = outboundMessages;
        drillState.probeCount = data.probe_count ?? drillState.probeCount;
        persistSessionState();
        drillState.attemptTurnCount = data.attempt_turn_count ?? drillState.attemptTurnCount;
        drillState.helpTurnCount = data.help_turn_count ?? drillState.helpTurnCount;
        if (completedGraphNeutralReDrill) {
          repairChecksThisSession.add(entrySessionKey(concept.id, drillState.node.id));
          try {
            await trainingStore.markRepairChecked(concept.id, drillState.node.id, turnStartedAt);
          } catch (err) {
            if (err?.message !== 'repair-required') throw err;
          }
        }
        handleDrillAssistantMessage(data.agent_response || '');
        if (data.agent_response?.trim()) {
          drillState.messages.push({ role: 'assistant', content: data.agent_response.trim() });
        }
        if (window.DrillChamber && completedNodeTurn && userText) {
          window.DrillChamber.appendVerdict?.(verdictCopy({
            classification: mapDrillClassificationForTraining(data.classification),
            userText,
          }));
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
        // Mirror disabled state to the chamber composer. The local node
        // prompt is already visible, so loading cleanup must keep the
        // writing surface available until the turn actually resolves.
        if (window.DrillChamber) {
          window.DrillChamber.setLoading?.(false);
          if (completedNodeTurn || data.session_terminated) {
            const coldClassification = mapDrillClassificationForTraining(data.classification);
            window.DrillChamber.setCompletionAction?.(
              completedColdAttempt ? coldAttemptCompletionLabel(coldClassification) : 'Return to concept',
              completedColdAttempt
                ? () => openStudyAfterVerdict(concept.id, drillState.node?.id)
                : () => cancelDrill(),
            );
          } else {
            window.DrillChamber.setComposerEnabled(true);
          }
        }
      };

      if (completedColdAttempt) {
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
        } else {
          /* c8 ignore next -- legacy fallback when DrillChamber is unavailable */
          if (chatHistory) appendFirstColdAttemptCreed();
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

  function drillQuestionForNodeContext(nodeContext = {}, concept = {}) {
    const scaffold = nodeContext.learner_scaffold || nodeContext.learnerScaffold || {};
    const explicitPrompt = (
      scaffold.entry_prompt
      || scaffold.task_cue
      || nodeContext.prompt
      || nodeContext.drillPrompt
      || nodeContext.purpose
    );
    if (typeof explicitPrompt === 'string' && explicitPrompt.trim()) {
      return explicitPrompt.trim();
    }
    const label = nodeContext.fullLabel || nodeContext.label || concept?.name || 'this entry';
    return `Reconstruct ${label} from memory before checking the source.`;
  }

  function startDrill(nodeContext = null) {
    const concept = getActiveConcept();
    if (!concept) return;

    const km = parseConceptGraphData(concept) || {};
    nodeContext = resolveDrillContextForConcept(nodeContext, concept, km);

    const nodeData = resolveNodeData(km, nodeContext.id) || {};
    if (nodeData.drill_status === 'solidified') {
      return;
    }

    const usesSedaLoop = nodeContext?.drillMode === 'seda';
    const initialSedaTurnText = usesSedaLoop
      ? String(nodeContext?.initialTurnText || '').trim()
      : '';
    const restoredSedaDraftText = usesSedaLoop
      ? String(nodeContext?.restoredDraftText || '').trim()
      : '';
    const unrecordedSedaDraftText = restoredSedaDraftText || initialSedaTurnText;

    // TODO(post-launch): see paired comment ~line 3592. All four guards
    // below (re-drill spacing, 4-entries-per-session, time limit,
    // 3-retries-per-entry) are doctrinally sound but block iteration.
    // Re-introduce as suggestions when we add real telemetry.
    const bypassSessionLimits = true;

    if (!bypassSessionLimits && (nodeData.drill_status === 'primed' || nodeData.drill_status === 'drilled') && !isReDrillEligible(nodeData, nodeContext.id)) {
      return;
    }

    const visitedNodeIds = Array.isArray(sessionState.visitedNodeIds) ? sessionState.visitedNodeIds : [];
    const isNewSessionNode = !visitedNodeIds.includes(nodeContext.id);
    const uniqueNodeCount = getSessionNodeCount();

    if (!bypassSessionLimits && uniqueNodeCount >= 4 && isNewSessionNode) {
      return;
    }

    if (!bypassSessionLimits && hasDrillSessionTimeLimitElapsed(sessionState.startedAt)) {
      return;
    }

    if (!bypassSessionLimits && (sessionState.retriesByNode[nodeContext.id] || 0) >= 3) {
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
    drillState.sedaSessionId = null;
    drillState.sedaSessionVersion = null;
    drillState.sedaPendingSubmission = null;
    drillState.sedaActive = usesSedaLoop;
    drillState.sessionToken += 1;
    activeDrillNode = nodeContext?.id || null;

    const mapView = document.getElementById('map-view');
    const mapContent = document.getElementById('map-content');
    if (!mapView?.classList.contains('visible')) {
      showMapView(concept, {
        activeEntryId: nodeContext.id,
        isDrilling: true,
      });
    }
    if (mapContent) {
      renderConceptPageB2(mapContent, km, concept, nodeContext.trainingSnapshot || null, {
        activeEntryId: nodeContext.id,
        isDrilling: true,
      });
    }
    setMapMode('route');

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

    document.body.classList.add('is-drilling');

    // Show the ironclad chamber view.
    const conceptName = concept?.name || concept?.metadata?.name || 'Concept';
    const entryName = nodeContext.fullLabel || nodeContext.id || 'Entry';
    const awaitingAuthoritativeSourceLessRoute = usesSedaLoop
      && isSourceLessConcept(concept, km)
      && !hasBoundSourceLessSedaRoute(km);
    const visibleQuestion = awaitingAuthoritativeSourceLessRoute
      ? 'Preparing your first question…'
      : drillQuestionForNodeContext(nodeContext, concept);
    if (window.DrillChamber) {
      window.DrillChamber.show({
        conceptName,
        entryName,
        question: visibleQuestion,
      });
      if (usesSedaLoop) {
        const sedaStartToken = drillState.sessionToken;
        window.DrillChamber.setComposerEnabled(false);
        window.DrillChamber.setLoading?.(true);
        loadOrCreateSedaResponse(
          concept,
          nodeContext,
          { sessionToken: sedaStartToken },
        )
          .then(async ({ data, routeBinding, concept: activeConcept }) => {
            if (drillState.sessionToken !== sedaStartToken || !drillState.sedaActive) return;
            drillState.sedaSessionId = data.sessionId;
            drillState.sedaSessionVersion = sessionVersionFromResponse(data);
            const promptText = routeBinding && data?.awaiting?.key === 'cold_attempt'
              ? routeBinding.nodeContext.prompt
              : drillPromptFromSedaResponse(data, nodeContext, activeConcept);
            chamberLastShownQuestion = promptText;
            if (routeBinding) {
              const training = await trainingStore.loadTraining(activeConcept.id);
              if (drillState.sessionToken !== sedaStartToken || !drillState.sedaActive) return;
              const liveMapContent = document.getElementById('map-content');
              if (liveMapContent) {
                renderConceptPageB2(
                  liveMapContent,
                  routeBinding.graphData,
                  activeConcept,
                  training,
                  { activeEntryId: nodeContext.id, isDrilling: true },
                );
              }
              window.DrillChamber.show({
                conceptName: activeConcept?.name || 'Concept',
                entryName: nodeContext.fullLabel || nodeContext.id || 'Entry',
                question: promptText,
              });
              // show() enables a freshly rendered composer by default; keep it
              // closed until the authoritative node and session are both ready.
              window.DrillChamber.setComposerEnabled(false);
            } else {
              window.DrillChamber.swapQuestion(promptText);
            }
            window.DrillChamber.setLoading?.(false);
            if (initialSedaTurnText) {
              await requestSedaTurn(initialSedaTurnText);
            } else {
              presentSedaSurface(data, { challengePrompt: promptText });
              if (restoredSedaDraftText) {
                restoreUnrecordedDraft(restoredSedaDraftText, { chamber: true });
                window.DrillChamber.appendVerdict?.(
                  'Draft kept • Not recorded against this question.',
                );
              }
            }
          })
          .catch(async (err) => {
            /* c8 ignore start -- defensive startup failure branch for unavailable local loop backend. */
            console.error(err);
            if (drillState.sessionToken !== sedaStartToken || !drillState.sedaActive) return;
            if (err?.code === 'stale_seda_start') return;
            drillState.pending = false;
            drillState.sedaSessionId = null;
            drillState.sedaSessionVersion = null;
            drillState.sedaPendingSubmission = null;
            if (err?.code === 'route_unavailable') {
              let hasEvidence = err?.reason === 'bound_node_mismatch';
              if (!hasEvidence) {
                try {
                  hasEvidence = await hasRecordedConceptEvidence(concept.id);
                } catch (evidenceError) {
                  hasEvidence = true;
                  console.warn('Could not inspect recorded evidence during route recovery.', evidenceError);
                }
              }
              if (drillState.sessionToken !== sedaStartToken || !drillState.sedaActive) return;
              window.DrillChamber.setLoading?.(false);
              window.DrillChamber.setComposerEnabled(false);
              if (unrecordedSedaDraftText) {
                restoreUnrecordedDraft(unrecordedSedaDraftText);
                window.DrillChamber.appendVerdict?.('Draft kept • Not recorded.');
              }
              if (hasEvidence) {
                window.DrillChamber.swapQuestion(
                  'This learning route cannot be resumed. Your recorded work is still on the map.',
                );
                window.DrillChamber.setCompletionAction?.('Return to map', () => {
                  const entryId = nodeContext?.id;
                  cancelDrill();
                  restoreUnrecordedDraft(unrecordedSedaDraftText, { entryId });
                });
              } else {
                window.DrillChamber.swapQuestion(
                  'We could not build the first question. Your starting sketch is saved.',
                );
                window.DrillChamber.setCompletionAction?.('Build the first question again', () => {
                  const retryContext = {
                    ...nodeContext,
                    graphNeutral: true,
                    drillMode: 'seda',
                    // The fresh route may ask a different question. Do not
                    // silently submit text written against the stale route.
                    initialTurnText: '',
                    restoredDraftText: unrecordedSedaDraftText,
                  };
                  if (!resetSourceLessRouteForFreshStart(concept)) {
                    window.DrillChamber.swapQuestion(
                      'Your starting sketch is saved, but a fresh question could not be prepared.',
                    );
                    return;
                  }
                  cancelDrill({ restoreMap: false });
                  startDrill(retryContext);
                });
              }
              return;
            }
            window.DrillChamber.swapQuestion('The learning loop could not start. Try again when ready.');
            window.DrillChamber.setLoading?.(false);
            window.DrillChamber.setCompletionAction?.('Try again', () => {
              cancelDrill({ restoreMap: false });
              startDrill(nodeContext);
            });
            /* c8 ignore stop */
          });
      } else {
        window.DrillChamber.setComposerEnabled(true);
      }
      // Seed the last-shown question so the FIRST history pair records
      // the actual question the learner saw (the seed prompt from the
      // node detail). Without this, chamberLastShownQuestion is '' on
      // the first send because appendBubble('ai',...) hasn't run yet
      // (it fires after requestDrillTurn resolves, not before).
      chamberLastShownQuestion = visibleQuestion;
      // The visible node prompt is the first question. Keep the
      // composer editable immediately; the first API turn should react
      // to the learner's reconstruction, not block them while asking for
      // a redundant generated question.

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
        if (!drillState.sedaActive) {
          window.DrillChamber.appendHistoryTurn('ai', chamberLastShownQuestion || '');
          window.DrillChamber.appendHistoryTurn('learner', text);
        }
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
  }

  function cancelDrill(options = {}) {
    // Hide the chamber first, before any other state cleanup.
    if (window.DrillChamber) {
      window.DrillChamber.hide();
    }

    drillState.sessionToken += 1;
    drillState.active = false;
    drillState.messages = [];
    drillState.node = null;
    drillState.logSessionId = null;
    drillState.pending = false;
    drillState.probeCount = 0;
    drillState.helpTurnCount = 0;
    drillState.sessionCompletePending = false;
    drillState.sedaSessionId = null;
    drillState.sedaSessionVersion = null;
    drillState.sedaPendingSubmission = null;
    drillState.sedaActive = false;
    chamberLastShownQuestion = '';
    if (drillUi) drillUi.style.display = 'none';
    document.body.classList.remove('is-drilling');
    activeDrillNode = null;
    if (chatHistory) chatHistory.innerHTML = '';
    if (chatInput) {
      chatInput.value = '';
      chatInput.disabled = true;
    }
    persistPhaseBResumeState(null);

    // Restore the concept page view (map + detail).
    const activeConcept = getActiveConcept();
    if (activeConcept && options.restoreMap !== false) {
      showMapView(activeConcept);
      window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
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
    clearSessionRoute();
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
      setMapMode('route');
      const graphData = parseConceptGraphData(concept) || {};
      startDrill(buildDefaultDrillContext(concept, graphData));
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
    deleteConcept, toggleConceptActions,
    extract, drill, drillFail, drillPass, consolidate,
    fastForward,
    hideMapView, setMapMode,
    showLibrary, hideLibrary, openLibraryConcept, seedLocalQaConcept, seedLocalRepairQaConcept, showDashboard, showIgnition, showSettings,
    syncLearnerStateIfIdentified, pushLearnerStateIfIdentified,
    hidePrimaryViews,  // exposed for launch-pad.js to avoid enumerating view IDs directly
    toggleTheme, setTheme, runHeroAction,
    // C-prime launch pad — Round D implementation.
    // showLaunchPad is called by the no-source door path in runHeroAction after
    // writing the pending shell to sessionStorage. It hides the ignition view and
    // mounts the threshold-capture surface via launch-pad.js.
    showLaunchPad() { _showLaunchPad(App); },
    // runLaunchPadAction is called by the launch-pad form onsubmit handler.
    // It reads the pending shell, posts to /api/extract, persists, and navigates.
    runLaunchPadAction(event) { return _runLaunchPadAction(event, App); },
    mountExtractOverlayForLaunchPad(name) { return mountExtractOverlay({ name }); },
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
// window.App — read by inline onclick="App.foo()" handlers in
// public/index.html plus generated Library actions such as local QA
// seed buttons. HTML→JS bridge. Phase 2 keeps this intentional; a
// future micro-phase could rewrite the inline/generated handlers as
// addEventListener wiring and drop the global.
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
// import. Keep this bridge explicit until graph-view owns a typed
// app-intent boundary.
window.App = App;
window.SocratinkApp = App;
