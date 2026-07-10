// Projects a completed app-local SEDA session record into the learner-visible
// training evidence store (socratink:training:v1:<conceptId>).
//
// Product truth: the SEDA loop simulates spacing with fixed timestamps
// (lib/seda/constants.mjs), so copying backend attempt times verbatim would
// let a single sitting derive solidified. Every projected attempt is
// re-stamped to real wall-clock time so one sitting derives at most primed;
// solidified stays gated on a real spaced return visit.

export const TRAINING_SCHEMA_VERSION = 1;

function sedaAttemptId(sessionId, index) {
  return `seda-${sessionId}-${index}`;
}

function sedaEventAttemptId(sessionId, index) {
  return `seda-${sessionId}-event-${index}`;
}

function mapClassification(classification) {
  if (classification === 'solid' || classification === 'strong') return 'strong';
  if (
    classification === 'deep'
    || classification === 'shallow'
    || classification === 'partial'
  ) return 'partial';
  if (classification === 'misconception' || classification === 'wrong_direction') return 'wrong_direction';
  return classification ? 'thin' : null;
}

function gapsForEarlyAttempt(evaluation) {
  const correction = typeof evaluation?.gap_description === 'string'
    ? evaluation.gap_description.trim()
    : '';
  return correction
    ? [{ mechanism: 'target mechanism', correction }]
    : [];
}

function latestColdAttemptEvent(data) {
  const events = Array.isArray(data?.events) ? data.events : [];
  for (let index = events.length - 1; index >= 0; index -= 1) {
    const event = events[index];
    if (event?.type !== 'cold_attempt') continue;
    const text = typeof event.text === 'string' ? event.text.trim() : '';
    const classification = mapClassification(event?.evaluation?.classification);
    if (!text || !classification) continue;
    return { event, index, text, classification };
  }
  return null;
}

// Select the single attempted backend node record. A SEDA session completes
// exactly one node, so zero or several attempted records is unexpected; fail
// closed rather than arbitrarily projecting whichever happens to be first.
function attemptedNodeRecord(record) {
  const nodeRecords = record?.training?.node_records;
  if (!nodeRecords || typeof nodeRecords !== 'object') return null;
  const attempted = Object.values(nodeRecords).filter(
    (node) => node && Array.isArray(node.attempts) && node.attempts.length,
  );
  return attempted.length === 1 ? attempted[0] : null;
}

function restampedAttempts({ backendRecord, sessionId, now, offset, startIndex = 0 }) {
  return backendRecord.attempts.slice(startIndex).map((attempt, localIndex) => {
    const backendIndex = startIndex + localIndex;
    return {
      id: sedaAttemptId(sessionId, backendIndex),
      at: now,
      user_text: attempt.user_text,
      classification: attempt.classification,
      gaps: Array.isArray(attempt.gaps) ? attempt.gaps : [],
      grader_version: attempt.grader_version || 'seda-loop',
      // Positional provenance, matching training-store.js: projection re-stamps
      // every attempt to one real sitting, so the backend's simulated cold/spaced
      // timing is derived from position here, never copied verbatim (a backend
      // "spaced" label would otherwise falsely imply a real spaced return).
      kind: offset + localIndex === 0 ? 'cold' : 'spaced',
    };
  });
}

function restampedRepairs({ backendRecord, sessionId, now }) {
  const repairs = Array.isArray(backendRecord.repairs) ? backendRecord.repairs : [];
  return repairs.map((repair, index) => ({
    id: `${sedaAttemptId(sessionId, index)}-repair`,
    at: now,
    text: repair.text,
  }));
}

function baseTraining(training, conceptId) {
  if (training) return training;
  return {
    concept_id: conceptId,
    schema_version: TRAINING_SCHEMA_VERSION,
    source_mode: 'source_less',
    grounding: 'learner_sketch',
    source_ref: null,
    sketch: null,
    node_records: {},
  };
}

/**
 * Projects the latest recordable SEDA cold_attempt event before the case is
 * complete. This lets first-session study reveal honor the cold-attempt gate
 * without waiting for the whole spaced SEDA case to finish.
 */
export function projectLatestSedaAttemptEvent({
  training = null,
  conceptId,
  nodeId,
  data,
  sessionId,
  now = new Date().toISOString(),
} = {}) {
  if (!conceptId || !nodeId || !sessionId) return null;
  const coldAttempt = latestColdAttemptEvent(data);
  if (!coldAttempt) return null;

  const next = baseTraining(training, conceptId);
  const nodeRecords = next.node_records && typeof next.node_records === 'object'
    ? next.node_records
    : {};
  const existing = nodeRecords[nodeId] || { attempts: [], repairs: [] };
  const existingAttempts = Array.isArray(existing.attempts) ? existing.attempts : [];
  const attemptId = sedaEventAttemptId(sessionId, coldAttempt.index);
  if (existingAttempts.some((attempt) => attempt?.id === attemptId)) {
    return null;
  }

  return {
    ...next,
    concept_id: conceptId,
    schema_version: TRAINING_SCHEMA_VERSION,
    node_records: {
      ...nodeRecords,
      [nodeId]: {
        ...existing,
        attempts: [
          ...existingAttempts,
          {
            id: attemptId,
            at: now,
            user_text: coldAttempt.text,
            classification: coldAttempt.classification,
            gaps: gapsForEarlyAttempt(coldAttempt.event?.evaluation),
            grader_version: coldAttempt.event?.evaluation?.prompt_version
              || coldAttempt.event?.evaluation?.grader_version
              || 'seda-loop',
            kind: existingAttempts.length === 0 ? 'cold' : 'spaced',
          },
        ],
        repairs: Array.isArray(existing.repairs) ? existing.repairs : [],
      },
    },
  };
}

/**
 * Returns the next training object to save, or null when there is nothing
 * new to project (no completed record, no attempts, or already projected).
 */
export function projectCompletedSedaRecord({
  training = null,
  conceptId,
  nodeId,
  record,
  sessionId,
  now = new Date().toISOString(),
} = {}) {
  if (!conceptId || !nodeId || !sessionId) return null;
  const backendRecord = attemptedNodeRecord(record);
  if (!backendRecord) return null;

  const next = baseTraining(training, conceptId);
  const nodeRecords = next.node_records && typeof next.node_records === 'object'
    ? next.node_records
    : {};
  const existing = nodeRecords[nodeId] || { attempts: [], repairs: [] };
  const existingAttempts = Array.isArray(existing.attempts) ? existing.attempts : [];
  if (existingAttempts.some((attempt) => attempt?.id === sedaAttemptId(sessionId, 0))) {
    return null;
  }

  // A recordable cold event may already have been projected to unlock study
  // before the SEDA case completed. Reconcile that provisional event into the
  // canonical completed-session attempt instead of appending the same learner
  // answer twice under a second id.
  const eventPrefix = `seda-${sessionId}-event-`;
  const eventAttemptIndex = existingAttempts.findIndex(
    (attempt) => String(attempt?.id || '').startsWith(eventPrefix),
  );
  const reconciledAttempts = [...existingAttempts];
  let completedStartIndex = 0;
  if (eventAttemptIndex >= 0) {
    const [completedCold] = restampedAttempts({
      backendRecord,
      sessionId,
      now,
      offset: eventAttemptIndex,
    });
    reconciledAttempts[eventAttemptIndex] = {
      ...completedCold,
      at: existingAttempts[eventAttemptIndex]?.at || now,
      kind: existingAttempts[eventAttemptIndex]?.kind || completedCold.kind,
    };
    completedStartIndex = 1;
  }

  const projected = {
    ...existing,
    attempts: [
      ...reconciledAttempts,
      ...restampedAttempts({
        backendRecord,
        sessionId,
        now,
        offset: reconciledAttempts.length,
        startIndex: completedStartIndex,
      }),
    ],
    repairs: [
      ...(Array.isArray(existing.repairs) ? existing.repairs : []),
      ...restampedRepairs({ backendRecord, sessionId, now }),
    ],
  };
  if (backendRecord.study_revealed_at && !projected.study_revealed_at) {
    projected.study_revealed_at = now;
  }

  return {
    ...next,
    concept_id: conceptId,
    schema_version: TRAINING_SCHEMA_VERSION,
    node_records: {
      ...nodeRecords,
      [nodeId]: projected,
    },
  };
}
