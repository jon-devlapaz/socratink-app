import { TRAINING_STORE_KEY_PREFIX } from './training-store.js';

export const LEARNER_STATE_SCHEMA_VERSION = 1;
export const CONCEPTS_STORE_KEY = 'learnops_concepts';

function defaultStorage() {
  try {
    return localStorage;
  } catch {
    return null;
  }
}

function parseJson(raw, fallback) {
  if (!raw) return fallback;
  try {
    return JSON.parse(raw);
  } catch {
    return fallback;
  }
}

export function collectLocalTrainingMap(storage = defaultStorage(), keyPrefix = TRAINING_STORE_KEY_PREFIX) {
  const out = {};
  if (!storage || typeof storage.length !== 'number') {
    // Memory-style Map/object storage used in tests may only implement getItem/setItem.
    if (!storage?.getItem) return out;
  }
  if (typeof storage.length === 'number' && typeof storage.key === 'function') {
    for (let i = 0; i < storage.length; i += 1) {
      const key = storage.key(i);
      if (!key || !key.startsWith(keyPrefix)) continue;
      const conceptId = key.slice(keyPrefix.length);
      const parsed = parseJson(storage.getItem(key), null);
      if (parsed && typeof parsed === 'object') out[conceptId] = parsed;
    }
    return out;
  }
  return out;
}

export function writeLocalTrainingMap(trainingMap, storage = defaultStorage(), keyPrefix = TRAINING_STORE_KEY_PREFIX) {
  if (!storage?.setItem || !trainingMap || typeof trainingMap !== 'object') return;
  Object.entries(trainingMap).forEach(([conceptId, training]) => {
    if (!conceptId || !training || typeof training !== 'object') return;
    storage.setItem(`${keyPrefix}${conceptId}`, JSON.stringify(training));
  });
}

function conceptRecency(concept) {
  const candidates = [
    concept?.updated_at,
    concept?.updatedAt,
    concept?.created_at,
    concept?.createdAt,
  ];
  for (const value of candidates) {
    const ms = Date.parse(value || '');
    if (Number.isFinite(ms)) return ms;
  }
  return 0;
}

function mergeAttemptLists(localAttempts, remoteAttempts) {
  const byId = new Map();
  [...(Array.isArray(remoteAttempts) ? remoteAttempts : []), ...(Array.isArray(localAttempts) ? localAttempts : [])]
    .forEach((attempt) => {
      if (!attempt || typeof attempt !== 'object' || !attempt.id) return;
      const existing = byId.get(attempt.id);
      if (!existing) {
        byId.set(attempt.id, attempt);
        return;
      }
      const existingAt = Date.parse(existing.at || '') || 0;
      const nextAt = Date.parse(attempt.at || '') || 0;
      if (nextAt >= existingAt) byId.set(attempt.id, attempt);
    });
  return [...byId.values()].sort((a, b) => (Date.parse(a.at || '') || 0) - (Date.parse(b.at || '') || 0));
}

function mergeRepairLists(localRepairs, remoteRepairs) {
  const byId = new Map();
  [...(Array.isArray(remoteRepairs) ? remoteRepairs : []), ...(Array.isArray(localRepairs) ? localRepairs : [])]
    .forEach((repair) => {
      if (!repair || typeof repair !== 'object' || !repair.id) return;
      byId.set(repair.id, repair);
    });
  return [...byId.values()].sort((a, b) => (Date.parse(a.at || '') || 0) - (Date.parse(b.at || '') || 0));
}

function earliestIso(a, b) {
  const aMs = Date.parse(a || '');
  const bMs = Date.parse(b || '');
  if (!Number.isFinite(aMs)) return b || null;
  if (!Number.isFinite(bMs)) return a || null;
  return aMs <= bMs ? a : b;
}

function latestIso(a, b) {
  const aMs = Date.parse(a || '');
  const bMs = Date.parse(b || '');
  if (!Number.isFinite(aMs)) return b || null;
  if (!Number.isFinite(bMs)) return a || null;
  return aMs >= bMs ? a : b;
}

export function mergeTrainingRecords(localTraining, remoteTraining) {
  if (!localTraining) return remoteTraining || null;
  if (!remoteTraining) return localTraining;

  const localNodes = localTraining.node_records && typeof localTraining.node_records === 'object'
    ? localTraining.node_records
    : {};
  const remoteNodes = remoteTraining.node_records && typeof remoteTraining.node_records === 'object'
    ? remoteTraining.node_records
    : {};
  const nodeIds = new Set([...Object.keys(localNodes), ...Object.keys(remoteNodes)]);
  const node_records = {};

  nodeIds.forEach((nodeId) => {
    const localNode = localNodes[nodeId] || {};
    const remoteNode = remoteNodes[nodeId] || {};
    node_records[nodeId] = {
      attempts: mergeAttemptLists(localNode.attempts, remoteNode.attempts),
      repairs: mergeRepairLists(localNode.repairs, remoteNode.repairs),
      study_revealed_at: earliestIso(localNode.study_revealed_at, remoteNode.study_revealed_at),
      repair_checked_at: latestIso(localNode.repair_checked_at, remoteNode.repair_checked_at),
    };
  });

  return {
    concept_id: localTraining.concept_id || remoteTraining.concept_id,
    schema_version: localTraining.schema_version || remoteTraining.schema_version || LEARNER_STATE_SCHEMA_VERSION,
    source_mode: localTraining.source_mode ?? remoteTraining.source_mode ?? null,
    grounding: localTraining.grounding || remoteTraining.grounding || 'ungrounded',
    source_ref: localTraining.source_ref ?? remoteTraining.source_ref ?? null,
    sketch: localTraining.sketch || remoteTraining.sketch || null,
    node_records,
  };
}

export function mergeLearnerState(localState, remoteState) {
  const localConcepts = Array.isArray(localState?.concepts) ? localState.concepts : [];
  const remoteConcepts = Array.isArray(remoteState?.concepts) ? remoteState.concepts : [];
  const byId = new Map();

  remoteConcepts.forEach((concept) => {
    if (concept?.id) byId.set(concept.id, concept);
  });
  localConcepts.forEach((concept) => {
    if (!concept?.id) return;
    const existing = byId.get(concept.id);
    if (!existing) {
      byId.set(concept.id, concept);
      return;
    }
    byId.set(
      concept.id,
      conceptRecency(concept) >= conceptRecency(existing) ? concept : existing,
    );
  });

  const localTraining = localState?.training && typeof localState.training === 'object'
    ? localState.training
    : {};
  const remoteTraining = remoteState?.training && typeof remoteState.training === 'object'
    ? remoteState.training
    : {};
  const trainingIds = new Set([...Object.keys(localTraining), ...Object.keys(remoteTraining)]);
  const training = {};
  trainingIds.forEach((conceptId) => {
    const merged = mergeTrainingRecords(localTraining[conceptId], remoteTraining[conceptId]);
    if (merged) training[conceptId] = merged;
  });

  return {
    schema_version: LEARNER_STATE_SCHEMA_VERSION,
    concepts: [...byId.values()],
    training,
    updated_at: new Date().toISOString(),
  };
}

export function readLocalLearnerState(storage = defaultStorage()) {
  const concepts = parseJson(storage?.getItem?.(CONCEPTS_STORE_KEY), []);
  return {
    schema_version: LEARNER_STATE_SCHEMA_VERSION,
    concepts: Array.isArray(concepts) ? concepts : [],
    training: collectLocalTrainingMap(storage),
    updated_at: null,
  };
}

export function writeLocalLearnerState(state, storage = defaultStorage()) {
  if (!storage?.setItem || !state) return;
  storage.setItem(CONCEPTS_STORE_KEY, JSON.stringify(Array.isArray(state.concepts) ? state.concepts : []));
  writeLocalTrainingMap(state.training || {}, storage);
}

export async function fetchRemoteLearnerState({
  fetchImpl = fetch,
} = {}) {
  const response = await fetchImpl('/api/learner-state', {
    method: 'GET',
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  });
  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new Error(`learner-state-get-failed:${response.status}`);
  }
  return response.json();
}

export async function putRemoteLearnerState(state, {
  fetchImpl = fetch,
} = {}) {
  const response = await fetchImpl('/api/learner-state', {
    method: 'PUT',
    credentials: 'same-origin',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      schema_version: LEARNER_STATE_SCHEMA_VERSION,
      concepts: Array.isArray(state?.concepts) ? state.concepts : [],
      training: state?.training && typeof state.training === 'object' ? state.training : {},
      updated_at: state?.updated_at || new Date().toISOString(),
    }),
  });
  if (!response.ok) {
    throw new Error(`learner-state-put-failed:${response.status}`);
  }
  return response.json();
}

export async function hydrateAndSyncLearnerState({
  storage = defaultStorage(),
  fetchImpl = fetch,
  isIdentified = false,
} = {}) {
  if (!isIdentified) return { synced: false, reason: 'guest-or-anonymous' };

  const local = readLocalLearnerState(storage);
  const remote = await fetchRemoteLearnerState({ fetchImpl });
  const merged = mergeLearnerState(local, remote || { concepts: [], training: {} });
  writeLocalLearnerState(merged, storage);
  await putRemoteLearnerState(merged, { fetchImpl });
  return { synced: true, state: merged };
}

export async function pushLocalLearnerState({
  storage = defaultStorage(),
  fetchImpl = fetch,
  isIdentified = false,
} = {}) {
  if (!isIdentified) return { pushed: false, reason: 'guest-or-anonymous' };
  const local = readLocalLearnerState(storage);
  local.updated_at = new Date().toISOString();
  await putRemoteLearnerState(local, { fetchImpl });
  return { pushed: true, state: local };
}
