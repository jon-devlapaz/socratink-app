function learnerSnippet(userText) {
  const text = String(userText || '').replace(/\s+/g, ' ').trim();
  return text.length > 72 ? `${text.slice(0, 69)}...` : text;
}

export function verdictCopy({ classification, userText, sedaComplete = false } = {}) {
  const snippet = learnerSnippet(userText);
  const x = snippet ? `your line "${snippet}"` : 'the attempt';
  if (sedaComplete) return `Checked • Recorded • ${x} is on record. • Study is ready.`;
  if (classification === 'strong' || classification === 'solid') {
    return `Checked • Solid enough to compare • You named ${x}. • Study will show what to add.`;
  }
  if (classification === 'partial' || classification === 'deep') {
    return `Checked • Partly there • You have ${x}. • Study will target the missing link.`;
  }
  if (classification === 'wrong_direction' || classification === 'misconception') {
    return `Checked • Wrong angle • You focused on ${x}. • Study will reset the mechanism.`;
  }
  return `Checked • Gap found • ${x} exposed what to study next. • Study will target it.`;
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
