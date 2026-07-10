function learnerSnippet(userText) {
  const text = String(userText || '').replace(/\s+/g, ' ').trim();
  return text.length > 72 ? `${text.slice(0, 69)}...` : text;
}

export function verdictCopy({
  classification,
  userText,
  recordable = true,
  sedaComplete = false,
} = {}) {
  const snippet = learnerSnippet(userText);
  const learnerLine = snippet ? `Your line: “${snippet}”` : 'Your attempt is on record.';
  if (!recordable) {
    return `Response received • Keep going • ${learnerLine} • Use the next question to add one cause-and-effect link.`;
  }
  if (sedaComplete) return 'Checked • Recorded • Your attempt is on record. • Study is ready.';
  if (classification === 'strong' || classification === 'solid') {
    return `Checked • Solid enough to compare • ${learnerLine} • Study will show what to add.`;
  }
  if (
    classification === 'partial'
    || classification === 'deep'
    || classification === 'thin'
    || classification === 'shallow'
  ) {
    return `Checked • Partly there • ${learnerLine} • Study will target the missing link.`;
  }
  if (classification === 'wrong_direction' || classification === 'misconception') {
    return `Checked • Wrong angle • ${learnerLine} • Study will show a different starting point.`;
  }
  return `Checked • Gap found • ${learnerLine} • Study will target what you just exposed.`;
}

export function nextSedaPromptAfterVerdict(promptText, previousPrompt, userText) {
  const next = String(promptText || '').trim();
  const prev = String(previousPrompt || '').trim();
  if (!next || next === prev) {
    return `You wrote: «${learnerSnippet(userText)}». Now: name the missing link in one sentence.`;
  }
  return `You wrote: «${learnerSnippet(userText)}». Now: ${next}`;
}

export function coldAttemptCompletionLabel(classification) {
  return classification === 'strong' ? 'Reveal notes and compare' : 'See what to study';
}

export function sedaCompleteCompletionLabel() {
  return 'See what to study';
}
