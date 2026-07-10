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
