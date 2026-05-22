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
  try {
    return storage.getItem(key) === '1';
  } catch {
    return false;
  }
}

export function markComparisonAcknowledged(conceptId, entryId, storage = defaultStorage()) {
  const key = storageKey(conceptId, entryId);
  if (!key || !storage) return;
  try {
    storage.setItem(key, '1');
  } catch {
    // Storage acknowledgement is best-effort UI state.
  }
}

export function clearComparisonAcknowledgement(conceptId, entryId, storage = defaultStorage()) {
  const key = storageKey(conceptId, entryId);
  if (!key || !storage) return;
  try {
    storage.removeItem(key);
  } catch {
    // Storage acknowledgement is best-effort UI state.
  }
}

export function clearComparisonAcknowledgementsForConcept(conceptId, storage = defaultStorage()) {
  if (!conceptId || !storage) return;
  const prefix = `${COMPARISON_ACK_PREFIX}:${conceptId}:`;
  const keys = [];
  let length = 0;
  try {
    length = Number(storage.length) || 0;
  } catch {
    return;
  }
  for (let i = 0; i < length; i += 1) {
    try {
      const key = typeof storage.key === 'function' ? storage.key(i) : null;
      if (typeof key === 'string' && key.startsWith(prefix)) keys.push(key);
    } catch {
      // Keep scanning; one bad storage slot should not break cleanup.
    }
  }
  keys.forEach((key) => {
    try {
      storage.removeItem(key);
    } catch {
      // Storage acknowledgement is best-effort UI state.
    }
  });
}
