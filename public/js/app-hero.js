export function getHeroStateLabel(state) {
  switch (state) {
    case 'instantiated': return 'source captured';
    case 'growing': return 'concept';
    case 'fractured': return 'worth revisiting';
    case 'hibernating': return 'spacing';
    case 'actualized': return 'spaced evidence';
    default: return 'no concepts yet';
  }
}

export function getHeroGuidance(concept) {
  if (!concept) return 'Pick a tile to enter, or start a new concept.';
  switch (concept.state) {
    case 'instantiated':
      return concept.graphData
        ? 'Open the concept. It is a hypothesis, not evidence yet.'
        : 'Map this source into a concept. The map is not learner evidence.';
    case 'growing':
      return concept.graphData
        ? 'Open the concept. Start with one cold attempt before study appears.'
        : 'Continue by mapping this source into a concept.';
    case 'fractured':
      return 'A spaced re-drill found a gap worth repairing. Revisit the mechanism, then return under spacing.';
    case 'hibernating':
      return 'This entry is spacing. Work elsewhere or return when re-drill is eligible.';
    case 'actualized':
      return 'Spaced evidence is on record. Re-drill later if you want another reconstruction pass.';
    default:
      return 'Pick a tile to enter, or start a new concept.';
  }
}

export function getHeroActionConfig(concept) {
  if (!concept) {
    return { label: 'Begin', action: 'add', disabled: false };
  }
  switch (concept.state) {
    case 'instantiated':
      return concept.graphData
        ? { label: 'Open Draft Path', action: 'open-map', disabled: false }
        : { label: 'Draft Map', action: 'extract', disabled: false };
    case 'growing':
      return concept.graphData
        ? { label: 'Open Draft Path', action: 'open-map', disabled: false }
        : { label: 'Draft Map', action: 'extract', disabled: false };
    case 'fractured':
      return { label: 'Repair Gap', action: 'drill', disabled: false };
    case 'hibernating':
      return concept.graphData
        ? { label: 'Open Evidence Map', action: 'open-map', disabled: false }
        : { label: 'Return Later', action: 'wait', disabled: true };
    case 'actualized':
      return concept.graphData
        ? { label: 'Open Evidence Map', action: 'open-map', disabled: false }
        : { label: 'Open Desk', action: 'wait', disabled: true };
    default:
      return { label: 'Begin', action: 'add', disabled: false };
  }
}

export function describeDoorSource(payload) {
  if (!payload) return '';
  if (payload.type === 'text') return `${(payload.text || '').length} chars pasted`;
  if (payload.type === 'url') return payload.url || 'URL';
  if (payload.type === 'file') return `${payload.filename || 'file'} · ${(payload.text || '').length} chars`;
  return payload.type;
}
