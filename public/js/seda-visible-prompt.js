// Keeps app-local SEDA responses learner-facing before they enter the chamber.

const PROMPT_STARTERS = [
  'try your first explanation',
  'in your own words',
  'close the note',
  'reconstruct',
  'explain',
  'describe',
  'name',
  'write',
  'when',
  'what',
  'why',
  'how',
  'which',
  'where',
];

function normalizePromptText(text) {
  return String(text || '').replace(/\s+/g, ' ').trim();
}

function findPromptStarter(text) {
  const lower = text.toLowerCase();
  let best = -1;
  for (const starter of PROMPT_STARTERS) {
    const idx = lower.indexOf(starter);
    if (idx > 0 && (best === -1 || idx < best)) best = idx;
  }
  return best;
}

export function learnerVisibleSedaText(text) {
  let visible = normalizePromptText(text);
  if (!visible) return '';
  if (/^\[[^\]]+\]$/i.test(visible)) return '';
  if (/^pick a concept\b/i.test(visible)) return '';

  if (/^concept:\s*/i.test(visible)) {
    const learnerGoalIdx = visible.search(/\blearner goal:\s*/i);
    if (learnerGoalIdx > 0) {
      visible = visible.slice(learnerGoalIdx).trim();
    } else {
      const promptIdx = findPromptStarter(visible);
      if (promptIdx > 0) visible = visible.slice(promptIdx).trim();
      else return '';
    }
  }

  if (/^learner goal:\s*/i.test(visible)) {
    const ownWordsIdx = visible.toLowerCase().indexOf('in your own words');
    if (ownWordsIdx > 0) {
      visible = visible.slice(ownWordsIdx).trim();
    } else {
      const sentenceEnd = visible.search(/[.!?]\s+/);
      if (sentenceEnd > 0) visible = visible.slice(sentenceEnd + 1).trim();
      else return '';
    }
  }

  return visible;
}

export function visibleSedaPromptFromResponse(data) {
  if (data?.caseComplete) {
    // Derived graph states are private routing data. Keep completion copy
    // controlled so rehydrating another tab cannot expose labels such as
    // "primed" or "solidified" to the learner.
    return 'Your attempt is on record. Study is ready.';
  }

  const cta = learnerVisibleSedaText(data?.awaiting?.ctaText || data?.awaiting?.ctaLabel || '');
  const transcript = Array.isArray(data?.learnerTranscript) ? data.learnerTranscript : [];
  const visible = transcript
    .map((entry) => learnerVisibleSedaText(entry?.text))
    .filter(Boolean)
    .slice(-2)
    .join('\n');
  return [visible, cta].filter(Boolean).join('\n\n') || 'Your turn.';
}

function latestEvent(data, type) {
  const events = Array.isArray(data?.events) ? data.events : [];
  return events.findLast((event) => event?.type === type) || null;
}

const AWAITING_SURFACE_MODE = Object.freeze({
  cmd: 'challenge',
  concept: 'challenge',
  learner_goal: 'challenge',
  launch_attempt: 'challenge',
  substrate_refinement: 'challenge',
  cold_attempt: 'challenge',
  repair: 'repair',
  repair_dialogue_turns: 'repair',
  repair_recovery: 'recovery',
  run_gap_drill: 'bridge',
  gap_attempt: 'transfer',
  spaced_attempt: 'settle',
});

function surfaceMode(data, lastEvent) {
  if (data?.caseComplete) return 'complete';
  const awaitingKey = data?.awaiting?.key || null;
  if (awaitingKey === 'continue') return lastEvent?.type === 'repair' ? 'repair-ready' : 'gap';
  return AWAITING_SURFACE_MODE[awaitingKey] || 'unsupported';
}

function surfacePresentation(mode, { prompt, gapText }) {
  if (mode === 'gap') return {
    question: gapText || 'There is one missing connection in your model.',
    composerEnabled: false,
    completionAction: { label: 'Work this link', kind: 'submit', value: 'continue' },
  };
  if (mode === 'repair') return {
    question: gapText || prompt,
    composerEnabled: true,
    completionAction: null,
  };
  if (mode === 'recovery') return {
    question: prompt || 'Name only the first part of the link you can see.',
    composerEnabled: true,
    completionAction: null,
  };
  if (mode === 'repair-ready') return {
    question: 'You formed the missing connection in your own words.',
    composerEnabled: false,
    completionAction: { label: 'See the connection', kind: 'submit', value: 'continue' },
  };
  if (mode === 'bridge') return {
    question: 'Close it when you can rebuild the link.',
    composerEnabled: false,
    completionAction: { label: 'Close and rebuild', kind: 'submit', value: 'y' },
  };
  if (mode === 'transfer') return {
    question: 'Without looking back, rebuild the connection in your own words. Then name one situation where it would matter.',
    composerEnabled: true,
    completionAction: null,
  };
  if (mode === 'settle') return {
    question: 'Keep the repaired connection. The next useful test is later, from memory.',
    composerEnabled: false,
    completionAction: { label: 'Return to concept', kind: 'return' },
    verdict: 'Repair practiced • This turn did not change your record.',
  };
  if (mode === 'complete') return {
    question: 'This learning loop is complete.',
    composerEnabled: false,
    completionAction: { label: 'Return to concept', kind: 'return' },
  };
  if (mode === 'unsupported') return {
    question: 'This learning step is not available here. Your recorded work is unchanged.',
    composerEnabled: false,
    completionAction: { label: 'Return to concept', kind: 'return' },
  };
  return {
    question: prompt,
    composerEnabled: true,
    completionAction: null,
  };
}

/**
 * Maps the hosted SEDA transport state onto the learner-facing nested loop.
 * This is presentation only: evidence eligibility stays owned by SEDA events.
 */
export function sedaSurfaceFromResponse(data) {
  const lastEvent = Array.isArray(data?.events) ? data.events.at(-1) : null;
  const mode = surfaceMode(data, lastEvent);

  const coldAttempt = latestEvent(data, 'cold_attempt');
  const gap = latestEvent(data, 'gap_identified');
  const repair = latestEvent(data, 'repair');
  const bridge = latestEvent(data, 'model_bridge');

  const surface = {
    mode,
    prompt: visibleSedaPromptFromResponse(data),
    originalText: learnerVisibleSedaText(coldAttempt?.text || ''),
    gapText: learnerVisibleSedaText(
      gap?.repair_scaffold?.socratic_question
      || gap?.gap_log?.missing_operation
      || data?.awaiting?.ctaText
      || '',
    ),
    repairText: learnerVisibleSedaText(repair?.text || ''),
    bridgeText: learnerVisibleSedaText(bridge?.text || ''),
  };
  return {
    ...surface,
    ...surfacePresentation(mode, surface),
  };
}
