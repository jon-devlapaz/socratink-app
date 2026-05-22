const COMPARISON_ACK_PREFIX = 'socratink:comparison_ack:v1';

function storageKey(conceptId, entryId) {
  if (!conceptId || !entryId) return null;
  return `${COMPARISON_ACK_PREFIX}:${conceptId}:${entryId}`;
}

function defaultStorage() {
  try {
    return globalThis.localStorage || null;
  } catch {
    /* c8 ignore next -- localStorage can throw in privacy-restricted browsers. */
    return null;
  }
}

export function hasComparisonAcknowledgement(conceptId, entryId, storage = defaultStorage()) {
  const key = storageKey(conceptId, entryId);
  if (!key || !storage) return false;
  return storage.getItem(key) === '1';
}

export function markComparisonAcknowledged(conceptId, entryId, storage = defaultStorage()) {
  const key = storageKey(conceptId, entryId);
  if (!key || !storage) return;
  storage.setItem(key, '1');
}

export function clearComparisonAcknowledgement(conceptId, entryId, storage = defaultStorage()) {
  const key = storageKey(conceptId, entryId);
  if (!key || !storage) return;
  storage.removeItem(key);
}

export function clearComparisonAcknowledgementsForConcept(conceptId, storage = defaultStorage()) {
  if (!conceptId || !storage) return;
  const prefix = `${COMPARISON_ACK_PREFIX}:${conceptId}:`;
  const keys = [];
  for (let i = 0; i < (storage.length || 0); i += 1) {
    const key = storage.key?.(i);
    if (key?.startsWith(prefix)) keys.push(key);
  }
  keys.forEach((key) => storage.removeItem(key));
}
