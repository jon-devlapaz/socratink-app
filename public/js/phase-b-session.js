export const PHASE_B_SESSION_KEY_PREFIX = 'learnops-phase-b-session';
export const PHASE_B_RESUME_KEY = 'learnops-phase-b-resume';

export function getPhaseBSessionStorageKey(conceptId = null) {
  return conceptId ? `${PHASE_B_SESSION_KEY_PREFIX}:${conceptId}` : PHASE_B_SESSION_KEY_PREFIX;
}

export function getDefaultPhaseBSessionState() {
  return {
    startedAt: null,
    nodesDrilled: 0,
    visitedNodeIds: [],
    retriesByNode: {},
    events: [],
  };
}

function getStorage(storage) {
  if (storage) return storage;
  try {
    if (typeof sessionStorage !== 'undefined') return sessionStorage;
  } catch {
    return null;
  }
  return null;
}

function warn(logger, message, err) {
  if (logger && typeof logger.warn === 'function') {
    logger.warn(message, err);
  }
}

export function loadPhaseBSessionState({ conceptId = null, storage = null, logger = console } = {}) {
  const sessionStorageLike = getStorage(storage);
  if (!sessionStorageLike) return getDefaultPhaseBSessionState();
  try {
    const raw = sessionStorageLike.getItem(getPhaseBSessionStorageKey(conceptId));
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
    warn(logger, 'Phase B session state unavailable.', err);
    return getDefaultPhaseBSessionState();
  }
}

export function persistPhaseBSessionState(sessionState, { conceptId = null, storage = null, logger = console } = {}) {
  const sessionStorageLike = getStorage(storage);
  if (!sessionStorageLike) return;
  try {
    sessionStorageLike.setItem(getPhaseBSessionStorageKey(conceptId), JSON.stringify(sessionState));
  } catch (err) {
    warn(logger, 'Unable to persist Phase B session state.', err);
  }
}

export function loadPhaseBResumeState({ storage = null, logger = console } = {}) {
  const sessionStorageLike = getStorage(storage);
  if (!sessionStorageLike) return null;
  try {
    const raw = sessionStorageLike.getItem(PHASE_B_RESUME_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed?.conceptId || !parsed?.nodeId || parsed?.mode !== 'study') return null;
    return parsed;
  } catch (err) {
    warn(logger, 'Phase B resume state unavailable.', err);
    return null;
  }
}

export function persistPhaseBResumeState(nextState = null, { storage = null, logger = console } = {}) {
  const sessionStorageLike = getStorage(storage);
  if (!sessionStorageLike) return;
  try {
    if (!nextState) {
      sessionStorageLike.removeItem(PHASE_B_RESUME_KEY);
      return;
    }
    sessionStorageLike.setItem(PHASE_B_RESUME_KEY, JSON.stringify(nextState));
  } catch (err) {
    warn(logger, 'Unable to persist Phase B resume state.', err);
  }
}
