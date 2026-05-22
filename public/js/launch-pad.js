// public/js/launch-pad.js
//
// Launch pad for source-less concept creation (C-prime spec §3.2).
//
// Reads the pending shell from sessionStorage, captures the learner's
// launch attempt (threshold), POSTs to /api/extract via submitConceptCreate
// (imported from ai_service.js), persists the returned ProvisionalMap through
// App.persistCreatedConceptFromLaunchPad, and only then clears the pending
// shell from sessionStorage.
//
// Exported functions are wired into the App namespace in app.js:
//   App.showLaunchPad      = () => showLaunchPad(App)
//   App.runLaunchPadAction = (event) => runLaunchPadAction(event, App)
//
// Doctrinal ordering contract:
//   1. POST /api/extract succeeds (returns ProvisionalMap).
//   2. App.persistCreatedConceptFromLaunchPad(map, shell) persists client-side.
//   3. ONLY AFTER persistence succeeds: clear socratink:pendingShell.
//   4. Navigate to graph view.
// If persistence fails, the shell remains in sessionStorage so the learner
// can retry without re-typing the threshold.

import { emitTelemetry } from './telemetry.js';
import { submitConceptCreate } from './ai_service.js';
import { AudioFX } from './audio.js';
import { isSubstantiveSketch } from './sketch-validation.js';

// Same printable-key heuristic the door uses (app.js) so launch-pad audio
// stays consistent: typing fires playKeyClick on visible keys + Backspace +
// Enter, but skips modifier combos and key-repeat.
const _isPrintableLaunchPadKey = (e) =>
  !e.metaKey && !e.ctrlKey && !e.altKey && !e.repeat &&
  (e.key.length === 1 || e.key === 'Backspace' || e.key === 'Enter');

const PENDING_SHELL_KEY = 'socratink:pendingShell';
const PENDING_SHELL_MAX_AGE_MS = 24 * 60 * 60 * 1000; // 24 hours

// Strategy-framed footer copy shown when the input is non-empty but not substantive.
// Names the *kind* of words that move the sketch over the line so the learner
// has something concrete to add, rather than the older "a few words" hand-wave
// which left users guessing why a 16-word sketch was being rejected.
const THIN_THRESHOLD_COPY =
  'Name a few concrete parts, guessed steps, examples, or confusions so socratink has enough signal to draft from.';

function normalizeWhitespace(text) {
  return String(text || '').replace(/\s+/g, ' ').trim();
}

function cleanConceptName(text) {
  return normalizeWhitespace(text)
    .replace(/[.?!]+$/g, '')
    .trim();
}

export function buildPendingShellFromDoorInput(rawInput) {
  const raw = normalizeWhitespace(rawInput);
  const fallback = cleanConceptName(raw);
  if (!fallback) return { name: '', goal: '' };

  const goalPatterns = [
    /^(?:i\s+)?(?:want|need|would like)\s+to\s+(?:understand|learn|know|explain|grasp|figure out)\s+/i,
    /^(?:i\s+am|i'm)\s+trying\s+to\s+(?:understand|learn|know|explain|grasp|figure out)\s+/i,
  ];
  const matchedPattern = goalPatterns.find((pattern) => pattern.test(raw));
  if (!matchedPattern) return { name: fallback, goal: '' };

  const derived = cleanConceptName(
    raw
      .replace(matchedPattern, '')
      .replace(/^(?:why|how|what|whether)\s+/i, ''),
  );

  return {
    name: derived || fallback,
    goal: raw,
  };
}

// ── Internal helpers ──────────────────────────────────────────────────────────

function isSubstantiveThreshold(text) {
  return isSubstantiveSketch(text);
}

function readPendingShell() {
  try {
    const raw = sessionStorage.getItem(PENDING_SHELL_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed.name !== 'string' || typeof parsed.ts !== 'number') return null;
    if (typeof parsed.goal !== 'string') parsed.goal = '';
    if (Date.now() - parsed.ts > PENDING_SHELL_MAX_AGE_MS) return null;
    return parsed;
  } catch {
    return null;
  }
}

function readPendingShellAge() {
  // Returns the raw shell (even if expired) for telemetry purposes.
  // Returns null if the key is absent or JSON is corrupt.
  try {
    const raw = sessionStorage.getItem(PENDING_SHELL_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed.ts !== 'number') return null;
    return { ...parsed, age_ms: Date.now() - parsed.ts };
  } catch {
    return null;
  }
}

function clearPendingShell() {
  try {
    sessionStorage.removeItem(PENDING_SHELL_KEY);
  } catch {
    // sessionStorage unavailable — best effort; the shell will evaporate on
    // tab close regardless.
  }
}

// ── showLaunchPad ─────────────────────────────────────────────────────────────

/**
 * Navigate to the launch-pad view.
 *
 * Called by App.showLaunchPad() which is wired by runHeroAction (no-source
 * door path). Reads the pending shell from sessionStorage and hydrates the
 * concept-name header. If the shell is absent or expired, bounces the learner
 * back to the door without mounting the surface.
 *
 * @param {object} App  The App namespace object (passed by app.js wrapper).
 */
export function showLaunchPad(App) {
  // Guard: the launch pad must NOT be reachable without a valid pending shell.
  const shell = readPendingShell();

  if (!shell) {
    // Shell absent or expired — bounce to door.
    const rawShell = readPendingShellAge();
    emitTelemetry('concept_create.launch_pad.evaporated', {
      age_ms: rawShell ? rawShell.age_ms : 0,
    });
    // Restore the door via the canonical entry point so nav highlight,
    // cap-gate, and hero-card visibility all stay in sync.
    App.showIgnition();
    return;
  }

  // Hide all primary views via shared helper, then reveal the launch pad.
  // App.hidePrimaryViews() also sets [hidden] on launch-pad-view, so we
  // call it first, then flip the attribute off to mount this surface.
  App.hidePrimaryViews();

  const view = document.getElementById('launch-pad-view');
  if (!view) return;
  view.hidden = false;
  view.removeAttribute('aria-busy');
  const form = document.getElementById('launch-pad-form');
  if (form) form.dataset.state = '';

  // Hydrate concept name and preserve the learner's raw goal when the door
  // input was phrased as intent rather than a clean topic title.
  const nameEl = document.getElementById('launch-pad-concept-name');
  if (nameEl) nameEl.textContent = shell.name;
  const goalEl = document.getElementById('launch-pad-concept-goal');
  if (goalEl) {
    goalEl.textContent = shell.goal ? `Goal: ${shell.goal}` : '';
    goalEl.hidden = !shell.goal;
  }

  emitTelemetry('concept_create.launch_pad.entered', {
    age_ms: Date.now() - shell.ts,
  });

  // Reset validation and input from any prior visit.
  const input = document.getElementById('launch-pad-input');
  const submit = document.getElementById('launch-pad-submit');
  const validation = document.getElementById('launch-pad-validation');
  if (input) input.value = '';
  if (submit) submit.disabled = true;
  if (validation) validation.textContent = '';

  // Wire input → submit-state → validation footer.
  // Remove any prior listener by cloning the input node (safest no-leak teardown).
  if (input) {
    const fresh = input.cloneNode(true);
    input.parentNode.replaceChild(fresh, input);

    fresh.addEventListener('input', () => {
      const ok = isSubstantiveThreshold(fresh.value);
      if (submit) submit.disabled = !ok;
      if (validation) {
        validation.textContent = !ok && (fresh.value || '').trim()
          ? THIN_THRESHOLD_COPY
          : '';
      }
    });

    // Audio cues mirror the door's concept-input pattern (app.js): focus tap
    // on arrival, key click on each printable keystroke. Keeps the threshold
    // surface sonically consistent with the door.
    fresh.addEventListener('focus', () => AudioFX.playFocusTap());
    fresh.addEventListener('keydown', (e) => {
      if (_isPrintableLaunchPadKey(e)) AudioFX.playKeyClick();
    });

    // Submit button matches the sidebar/bottom-nav click cue (app.js):
    // a single playFocusTap on click. Disabled state guards against
    // "thin threshold" double-fires; a successful click then triggers
    // navigation, so this listener naturally fires once per submit.
    if (submit) {
      submit.addEventListener('click', () => {
        if (!submit.disabled) AudioFX.playFocusTap();
      });
    }

    // Focus the textarea on entry — the surface is blank and the learner's
    // task is immediate.
    requestAnimationFrame(() => fresh.focus());
  }
}

// ── runLaunchPadAction ────────────────────────────────────────────────────────

/**
 * Handle the launch-pad form submission.
 *
 * Called by the form's onsubmit="return App.runLaunchPadAction(event)".
 * Posts to /api/extract, persists the returned ProvisionalMap, and clears
 * the pending shell ONLY after persistence succeeds.
 *
 * Persistence failures leave the shell in place so the learner can retry.
 * 422 thin-sketch rejections render the strategy-framed footer and leave
 * the shell in place for a retry.
 *
 * @param {Event} event  The form submit event.
 * @param {object} App   The App namespace object (passed by app.js wrapper).
 * @returns {false}  Always returns false to suppress default form submission.
 */
export async function runLaunchPadAction(event, App) {
  if (event && typeof event.preventDefault === 'function') {
    event.preventDefault();
  }

  const shell = readPendingShell();
  if (!shell) {
    // Shell evaporated mid-session — bounce to door silently.
    showLaunchPad(App);
    return false;
  }

  const input = document.getElementById('launch-pad-input');
  const submit = document.getElementById('launch-pad-submit');
  const validation = document.getElementById('launch-pad-validation');
  const threshold = (input ? input.value : '').trim();

  if (!isSubstantiveThreshold(threshold)) {
    // Client-side gate: the submit button should already be disabled, but
    // handle direct invocation (assistive tech, test harness) defensively.
    if (validation) validation.textContent = THIN_THRESHOLD_COPY;
    emitTelemetry('concept_create.bypass_rejected', { path: 'client' });
    return false;
  }

  // Disable submit to prevent double-submit during network call.
  if (submit) submit.disabled = true;
  if (validation) validation.textContent = '';

  // Swap the submit label to a quiet status word during the ~10-20s extract.
  // Persona QA on the busy state flagged the unchanged "Save sketch" label
  // + opacity dim alone as too quiet for a 15-second wait. A single-word
  // swap to "Drafting…" communicates progress without adding chrome.
  // (Restored to the original label on any error path so the user can retry.)
  const originalSubmitLabel = submit ? submit.textContent : '';
  if (submit) submit.textContent = 'Drafting…';

  // Mark the composer as busy while the extract is in flight.
  // aria-busy="true" tells assistive tech the surface is updating;
  // form.dataset.state='busy' drives the paper composer's dim
  // (paper.css .composer-card[data-state="busy"]).
  const form = document.getElementById('launch-pad-form');
  if (form) {
    form.setAttribute('aria-busy', 'true');
    form.dataset.state = 'busy';
  }
  const clearBuildingState = () => {
    if (!form) return;
    form.removeAttribute('aria-busy');
    form.dataset.state = '';
    if (submit) submit.textContent = originalSubmitLabel;
  };

  // ── Step 1: POST /api/extract ─────────────────────────────────────────────
  // Telemetry is emitted AFTER the network result is known — one event per
  // submit with the resolved build_blocked value.
  //   2xx  → emit submit { build_blocked: false }
  //   422  → emit submit { build_blocked: true }
  //   5xx / network / persistence → NO submit event (request didn't complete)
  let data;
  try {
    const apiKey =
      (typeof localStorage !== 'undefined' && localStorage.getItem('gemini_key')) ||
      undefined;
    data = await submitConceptCreate({
      name: shell.name,
      learnerGoal: shell.goal,
      startingSketch: threshold,
      source: null,
      apiKey,
    });
  } catch (err) {
    if (err && err.status === 422) {
      // Server-side thin-sketch rejection (thin_sketch_no_source) or other 422.
      // For thin_sketch_no_source specifically, override the server message
      // with THIN_THRESHOLD_COPY because the launch-pad has no source-attach
      // affordance — the server message names "or attach source material" as
      // an escape path, but that path only exists at the door / modal. For
      // other 422 codes, surface the server message verbatim.
      const code = err.body && err.body.error;
      const isThinSketch = code === 'thin_sketch_no_source';
      const validationCopy = isThinSketch
        ? THIN_THRESHOLD_COPY
        : ((err.body && err.body.message)
          ? String(err.body.message)
          : THIN_THRESHOLD_COPY);
      if (validation) validation.textContent = validationCopy;
      if (submit) submit.disabled = false;
      clearBuildingState();
      emitTelemetry('concept_create.launch_pad.submit', {
        threshold_len: threshold.length,
        build_blocked: true,
      });
      emitTelemetry('concept_create.bypass_rejected', { path: 'server' });
      return false;
    }
    // Network error, 5xx, or other failure: surface retry copy, leave shell.
    // For server-side cap exceeded, forward the actionable server message so
    // the learner knows to adjust the prompt rather than retry blindly, AND
    // emit submit telemetry so cap-exceeded rate is visible in dashboards
    // (parallel to the 422 branch above).
    console.error('launch_pad: extract failed', err);
    const capExceeded =
      err && err.status === 500 && err.body && err.body.error === 'smallest_route_cap_exceeded';
    if (capExceeded) {
      emitTelemetry('concept_create.launch_pad.submit', {
        threshold_len: threshold.length,
        build_blocked: true,
      });
      emitTelemetry('concept_create.cap_exceeded', { path: 'server' });
    }
    // Other transport failures (network, 5xx without cap-exceeded) emit no
    // submit telemetry — the request did not complete cleanly.
    const fallbackMsg = capExceeded && err.body.message
      ? String(err.body.message)
      : 'Something went wrong. Try again.';
    if (validation) validation.textContent = fallbackMsg;
    if (submit) submit.disabled = false;
    clearBuildingState();
    return false;
  }

  // 2xx success — emit exactly one submit event.
  emitTelemetry('concept_create.launch_pad.submit', {
    threshold_len: threshold.length,
    build_blocked: false,
  });

  const provisionalMap = data.provisional_map || data.knowledge_map || null;

  // ── Step 2: Persist client-side ───────────────────────────────────────────
  // Uses App.persistCreatedConceptFromLaunchPad — a helper wired in app.js
  // that follows the same path as finishConceptCreateAfterOverlay but without
  // the overlay teardown and navigates to graph view instead of dashboard.
  // The shell is cleared ONLY after persistence succeeds.
  try {
    App.persistCreatedConceptFromLaunchPad(provisionalMap, shell, threshold);
  } catch (err) {
    // Persistence failure — leave the shell so the learner can retry.
    console.error('launch_pad: persistence failed', err);
    // Board-at-capacity is a special case: a retry will not succeed, the
    // learner needs to retire a concept first. Surface a directive message
    // instead of the generic "try again" copy.
    const isBoardCap = err && err.code === 'board_at_capacity';
    const msg = isBoardCap
      ? 'The board holds nine concepts. Retire one in your library to start another.'
      : 'Could not save the concept locally. Try again.';
    if (validation) validation.textContent = msg;
    if (submit) submit.disabled = false;
    clearBuildingState();
    return false;
  }

  // ── Step 3: Clear shell ONLY after persistence succeeds ───────────────────
  clearPendingShell();

  // ── Step 4: Navigate to graph view ───────────────────────────────────────
  // App.navigateToGraphViewFromLaunchPad handles selectConcept + showMapView
  // and passes {fromLaunchPad: true} for Round E's skeleton-line hook.
  App.navigateToGraphViewFromLaunchPad({ fromLaunchPad: true });

  return false;
}
