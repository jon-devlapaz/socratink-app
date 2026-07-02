import { escHtml } from './html.js';
import { deriveNodeTraining } from './training-derive.js';

const FALLBACK_ACTIVE_ENTRY = {
  id: 'core-thesis',
  label: 'Core thesis',
  purpose: 'The first entry asks for the governing idea, not the whole source.',
  drill_status: 'locked',
};

function legacyTrainingForEntry(entry, options = {}) {
  const status = String(entry?.drill_status || '').toLowerCase();
  const phase = String(entry?.drill_phase || '').toLowerCase();
  const legacyEligibleMs = Date.parse(entry?.re_drill_eligible_after || '');
  const nowMs = Date.parse(options?.now || new Date().toISOString());
  const waitingForLegacySpacing = (
    Number.isFinite(legacyEligibleMs)
    && Number.isFinite(nowMs)
    && legacyEligibleMs > nowMs
  );
  if (status === 'solidified' || status === 'solid') {
    return { state: 'solidified', next_action: null, attempted: true };
  }
  if (status === 'drilled') {
    return {
      state: 'needs repair',
      next_action: waitingForLegacySpacing ? 'review' : 'spaced_attempt',
      attempted: true,
    };
  }
  if (status === 'primed') {
    return {
      state: 'primed',
      next_action: phase === 'study' ? 'study' : (waitingForLegacySpacing ? 'review' : 'spaced_attempt'),
      attempted: true,
      legacy_study_required: phase === 'study',
    };
  }
  return null;
}

export function getConceptEntryId(entry, index) {
  return entry?.id || `entry-${index}`;
}

export function findConceptEntryById(backbone, entryId) {
  const index = backbone.findIndex((entry, i) => getConceptEntryId(entry, i) === entryId);
  if (index < 0) return null;
  return {
    entry: backbone[index],
    index,
    id: getConceptEntryId(backbone[index], index),
  };
}

function trainingRecordsFor(training) {
  return training?.node_records && typeof training.node_records === 'object'
    ? training.node_records
    : {};
}

function recordWithLegacyStudyReveal(entry, record, legacyEntry) {
  const status = String(entry?.drill_status || '').toLowerCase();
  const phase = String(entry?.drill_phase || '').toLowerCase();
  const postStudyLegacy = status === 'drilled'
    || status === 'solidified'
    || status === 'solid'
    || phase === 're_drill';
  if (
    !record
    || record.study_revealed_at
    || !legacyEntry?.attempted
    || legacyEntry?.legacy_study_required
    || !postStudyLegacy
  ) {
    return record;
  }
  const attempts = Array.isArray(record?.attempts) ? record.attempts : [];
  const revealedAt = entry?.study_completed_at || entry?.last_drilled || attempts[0]?.at || null;
  return revealedAt ? { ...record, study_revealed_at: revealedAt } : record;
}

function entryTraining(backbone, index, training, options = {}) {
  const entry = backbone[index] || null;
  const id = getConceptEntryId(entry, index);
  const record = trainingRecordsFor(training)[id] || null;
  const attempts = Array.isArray(record?.attempts) ? record.attempts : [];
  const legacyEntry = legacyTrainingForEntry(entry, options);
  const derivedRecord = recordWithLegacyStudyReveal(entry, record, legacyEntry);
  const baseLegacy = legacyEntry?.state === 'solidified' || !attempts.length ? legacyEntry : null;
  const legacy = baseLegacy?.legacy_study_required && derivedRecord?.study_revealed_at
    ? { ...baseLegacy, next_action: 'spaced_attempt' }
    : baseLegacy;
  const derived = deriveNodeTraining(derivedRecord, options);
  return {
    ...derived,
    ...legacy,
    id,
    record: derivedRecord,
    attempted: Boolean(derived.last_attempt_at) || Boolean(legacy?.attempted),
  };
}

function predecessorsAttempted(backbone, index, training, options = {}) {
  return index === 0 || backbone
    .slice(0, index)
    .every((_, i) => entryTraining(backbone, i, training, options).attempted);
}

function entryLearnerState(backbone, index, training, options = {}) {
  const derived = entryTraining(backbone, index, training, options);
  const entryId = getConceptEntryId(backbone[index], index);
  const checkedEntryIds = Array.isArray(options?.repairCheckedEntryIds)
    ? options.repairCheckedEntryIds
    : [];
  if (derived.attempted) {
    if (derived.state === 'needs repair' && checkedEntryIds.includes(entryId)) {
      return 'repair checked';
    }
    return derived.state || 'attempted';
  }
  return predecessorsAttempted(backbone, index, training, options)
    ? 'ready to reconstruct'
    : 'locked';
}

function entryDisplayLabel(entry, index) {
  const label = String(entry?.label || '').trim();
  if (label) return label;
  if (index === 0) return 'First entry';
  if (index === 1) return 'Second entry';
  if (index === 2) return 'Third entry';
  return `Entry ${index + 1}`;
}

function cleanScaffoldText(value) {
  return typeof value === 'string' ? value.trim() : '';
}

function normalizeSourceMode(value) {
  const mode = cleanScaffoldText(value);
  return mode === 'source_less' || mode === 'source_attached' ? mode : '';
}

function sourceModeForConcept(concept, data, training) {
  const explicitMode = normalizeSourceMode(training?.source_mode)
    || normalizeSourceMode(concept?.sourceMode)
    || normalizeSourceMode(concept?.source_mode)
    || normalizeSourceMode(data?.metadata?.source_mode);
  if (explicitMode) return explicitMode;
  const hasNullContentType = Object.prototype.hasOwnProperty.call(concept || {}, 'contentType')
    && concept?.contentType === null;
  const hasNullSourceUrl = Object.prototype.hasOwnProperty.call(concept || {}, 'sourceUrl')
    && concept?.sourceUrl === null;
  const hasSourceMarker = Boolean(
    cleanScaffoldText(concept?.contentType)
    || cleanScaffoldText(concept?.contentFilename)
    || cleanScaffoldText(concept?.sourceUrl)
    || cleanScaffoldText(data?.metadata?.source_url)
  );
  return hasNullContentType && hasNullSourceUrl && !hasSourceMarker ? 'source_less' : '';
}

function normalizeLearnerScaffold(scaffold) {
  if (!scaffold || typeof scaffold !== 'object') return null;
  const normalized = {
    bloom_level: cleanScaffoldText(scaffold.bloom_level),
    learner_move: cleanScaffoldText(scaffold.learner_move),
    task_label: cleanScaffoldText(scaffold.task_label),
    task_cue: cleanScaffoldText(scaffold.task_cue),
    tailoring_anchor: cleanScaffoldText(scaffold.tailoring_anchor),
    entry_prompt: cleanScaffoldText(scaffold.entry_prompt),
    expected_shape: cleanScaffoldText(scaffold.expected_shape),
    sentence_starter: cleanScaffoldText(scaffold.sentence_starter),
    blank_hint: cleanScaffoldText(scaffold.blank_hint),
    evidence_goal: cleanScaffoldText(scaffold.evidence_goal),
  };
  return Object.values(normalized).some(Boolean) ? normalized : null;
}

function entryScaffold(entry) {
  return normalizeLearnerScaffold(entry?.learner_scaffold);
}

function learnerGoalForConcept(concept, data) {
  return cleanScaffoldText(concept?.learnerGoal)
    || cleanScaffoldText(data?.metadata?.learner_goal);
}

function attemptPlaceholderForScaffold(scaffold) {
  if (!scaffold) return 'Draft what you can recall. Messy is useful.';
  const starter = cleanScaffoldText(scaffold.sentence_starter);
  if (starter) return starter;
  return 'Write what you can explain right now.';
}

function blankHintForScaffold(scaffold) {
  if (!scaffold) return 'Start with a word, a rough picture, or the part that feels fuzzy.';
  const hint = cleanScaffoldText(scaffold.blank_hint);
  if (hint) return hint;
  return 'Type one relationship you suspect, even if it feels incomplete.';
}

export function deriveConceptEntries(data = {}) {
  const backbone = Array.isArray(data?.backbone) ? data.backbone : [];
  const backboneEntries = backbone.map((entry, index) => ({
    ...entry,
    label: cleanScaffoldText(entry?.label) || cleanScaffoldText(entry?.principle) || entryDisplayLabel(entry, index),
    learner_scaffold: normalizeLearnerScaffold(entry?.learner_scaffold),
  }));

  const clusterEntries = (Array.isArray(data?.clusters) ? data.clusters : []).flatMap((cluster, clusterIndex) => {
    const subnodes = Array.isArray(cluster?.subnodes) ? cluster.subnodes : [];
    return subnodes.map((subnode, subnodeIndex) => {
      const scaffold = normalizeLearnerScaffold(subnode?.learner_scaffold || cluster?.learner_scaffold);
      const fallbackId = cluster?.id ? `${cluster.id}_s${subnodeIndex + 1}` : `entry-${clusterIndex}-${subnodeIndex}`;
      const label = (
        scaffold?.task_label
        || cleanScaffoldText(subnode?.label)
        || cleanScaffoldText(cluster?.label)
        || cleanScaffoldText(cluster?.title)
        || entryDisplayLabel(subnode, clusterIndex)
      );
      return {
        ...subnode,
        id: cleanScaffoldText(subnode?.id) || fallbackId,
        label,
        purpose: cleanScaffoldText(subnode?.purpose)
          || cleanScaffoldText(cluster?.description)
          || scaffold?.task_cue
          || '',
        study_note: subnode?.study_note || subnode?.study_material || subnode?.mechanism,
        cluster_id: cluster?.id || null,
        cluster_label: cluster?.label || cluster?.title || '',
        learner_scaffold: scaffold,
      };
    });
  });

  if (clusterEntries.length && (!backboneEntries.length || clusterEntries.some((entry) => entry.learner_scaffold))) {
    return clusterEntries;
  }
  return backboneEntries;
}

export function deriveConceptEntryViewState(backbone, index, training = null, options = {}) {
  const entries = Array.isArray(backbone) ? backbone : [];
  const safeIndex = Number.isInteger(index) && index >= 0 ? index : 0;
  const entry = entries[safeIndex] || null;
  /* c8 ignore next 7 -- defensive public-helper branch covered by Node module tests; the browser route always has a selected fallback entry. */
  if (!entry) {
    return {
      id: getConceptEntryId(null, safeIndex),
      attempted: false,
      state: 'locked',
      nextAction: null,
    };
  }
  const id = getConceptEntryId(entry, safeIndex);
  const derived = entryTraining(entries, safeIndex, training, options);
  const state = entryLearnerState(entries, safeIndex, training, options);
  return {
    id,
    attempted: Boolean(derived.attempted),
    state,
    nextAction: state === 'locked' ? null : (derived.next_action || null),
  };
}

function stripStateClass({ attempted, state, isReady }) {
  if (!attempted) return isReady ? 'concept-strip__node--ready' : 'concept-strip__node--locked';
  if (state === 'needs repair') return 'concept-strip__node--needs-repair';
  if (state === 'solidified') return 'concept-strip__node--solidified';
  return 'concept-strip__node--primed';
}

export function selectInitialConceptEntry(backbone, training = null, options = {}) {
  const actionableIndex = backbone.findIndex((_, index) => {
    const state = entryTraining(backbone, index, training, options).state;
    return state !== 'solidified';
  });
  const index = Math.max(0, actionableIndex >= 0 ? actionableIndex : (backbone.length ? 0 : -1));
  const entry = backbone[index] || FALLBACK_ACTIVE_ENTRY;
  return {
    entry,
    index,
    id: getConceptEntryId(entry, index),
  };
}

export function renderConceptStripHtml(backbone, activeEntry, activeIdx, training = null, options = {}) {
  const stripWidth = 600;
  const stripHeight = 110;
  const strokeY = stripHeight / 2;
  const totalNodes = backbone.length || 1;
  const padX = 60;
  const span = stripWidth - 2 * padX;
  const stepX = totalNodes > 1 ? span / (totalNodes - 1) : 0;

  const stripNodes = backbone.map((node, i) => {
    const x = padX + i * stepX;
    const derived = entryTraining(backbone, i, training, options);
    const isPrimed = derived.attempted;
    const isReady = !derived.attempted && predecessorsAttempted(backbone, i, training, options);
    const isActive = i === activeIdx;
    const cls = [
      'concept-strip__node',
      stripStateClass({ attempted: isPrimed, state: derived.state, isReady }),
    ];
    if (isActive) cls.push('is-active');
    const r = isActive ? 9 : (isPrimed ? 7 : (isReady ? 7 : 6));
    const entryId = node.id || `entry-${i}`;
    const label = escHtml(entryDisplayLabel(node, i));
    const learnerState = entryLearnerState(backbone, i, training, options);
    const ariaLabel = `${entryDisplayLabel(node, i)}, ${learnerState}${isActive ? ', current' : ''}`;
    return `
      <g class="${cls.join(' ')}"
         role="button"
         tabindex="0"
         data-entry-id="${escHtml(entryId)}"
         data-entry-index="${i}"
         aria-label="${escHtml(ariaLabel)}">
        <rect x="${x - 14}" y="${strokeY - 14}" width="28" height="28" fill="transparent" pointer-events="all"></rect>
        <circle cx="${x}" cy="${strokeY}" r="${r}"></circle>
        ${isActive ? `<text x="${x}" y="${strokeY + 25}">${label}</text>` : ''}
      </g>
    `;
  }).join('');

  const stripNodesHtml = backbone.length > 0
    ? stripNodes
    : `<g class="concept-strip__node concept-strip__node--ready is-active" role="button" tabindex="0" data-entry-id="core-thesis" data-entry-index="0" aria-label="core thesis, ready to reconstruct, current"><rect x="${padX - 14}" y="${strokeY - 14}" width="28" height="28" fill="transparent" pointer-events="all"></rect><circle cx="${padX}" cy="${strokeY}" r="9"></circle><text x="${padX}" y="${strokeY + 25}">core thesis</text></g>`;

  const stripEdges = backbone.slice(1).map((_, i) => {
    const x1 = padX + i * stepX;
    const x2 = padX + (i + 1) * stepX;
    const isActiveEdge = i + 1 === activeIdx;
    return `<line class="concept-strip__edge${isActiveEdge ? ' is-active' : ''}" x1="${x1}" y1="${strokeY}" x2="${x2}" y2="${strokeY}"></line>`;
  }).join('');

  const stripActiveLabel = `${escHtml(entryDisplayLabel(activeEntry, activeIdx))} · ${activeIdx + 1} of ${totalNodes}`;

  return `
    <div class="concept-strip">
      <div class="concept-strip__inner">
        <div class="concept-strip__tooltip" id="concept-strip-tooltip" hidden></div>
        <svg class="concept-strip__svg" viewBox="0 0 ${stripWidth} ${stripHeight}" preserveAspectRatio="xMidYMid meet">
          ${stripEdges}
          ${stripNodesHtml}
        </svg>
        <div class="concept-strip__overlay">
          <span class="eyebrow">draft route</span>
          <span class="concept-strip__active-name">${stripActiveLabel}</span>
        </div>
      </div>
    </div>
  `;
}

function activeEntryEyebrow({ isBlocked, attempted, state, nextAction, justRevealedStudy }) {
  if (isBlocked) return 'locked';
  if (!attempted) return 'Start from memory';
  if (justRevealedStudy) return 'Compare notes';
  if (nextAction === 'study') return 'Draft saved';
  if (nextAction === 'repair') return 'Needs repair';
  if (state === 'needs repair' && nextAction === 'spaced_attempt') return 'Ready to reconstruct again';
  if (state === 'solidified') return 'solidified';
  if (nextAction === 'spaced_attempt') return 'Ready to reconstruct again';
  if (nextAction === 'review') return 'Review later';
  if (state === 'needs repair') return 'Needs repair';
  return 'Ready to reconstruct again';
}

function activeEntryCtaLabel({ attempted, state, nextAction }) {
  if (!attempted) return 'Draft from memory';
  if (nextAction === 'study') return 'Reveal notes and compare';
  if (state === 'needs repair' && nextAction === 'spaced_attempt') return 'Write it again';
  if (state === 'solidified') return 'Reconstruct from memory';
  if (state === 'primed' && (nextAction === 'spaced_attempt' || nextAction === 'review')) {
    return 'Reconstruct from memory';
  }
  return 'Write it again';
}

function studyNoteForEntry(activeEntry, concept, data) {
  const meta = data?.metadata || {};
  return (
    activeEntry?.study_note
    || activeEntry?.study_material
    || activeEntry?.mechanism
    || activeEntry?.detail
    || activeEntry?.purpose
    || activeEntry?.principle
    || meta.core_thesis
    || meta.thesis
    || concept?.contentPreview
    || 'No study note is available for this entry yet.'
  );
}

function repairGapTitle(gap, index) {
  if (!gap || typeof gap !== 'object') return `Gap ${index + 1}`;
  return gap.mechanism || gap.label || gap.type || `Gap ${index + 1}`;
}

function repairGapCorrection(gap) {
  if (!gap || typeof gap !== 'object') return String(gap || '');
  const text = gap.correction || gap.description || gap.detail || gap.text || '';
  return String(text)
    .replace(/^The learner correctly identifies\b/i, 'Your draft names')
    .replace(/^The learner\b/i, 'Your draft')
    .replace(/^Learner\b/i, 'Your draft');
}

function latestAttemptForRecord(record) {
  const attempts = Array.isArray(record?.attempts) ? record.attempts : [];
  return attempts.length ? attempts[attempts.length - 1] : null;
}

export function deriveSourceLessViewMode(derived, options = {}) {
  if (options?.viewMode) return options.viewMode;
  const attempts = Array.isArray(derived?.record?.attempts) ? derived.record.attempts : [];
  const repairs = Array.isArray(derived?.record?.repairs) ? derived.record.repairs : [];
  const firstAttempt = attempts[0] || null;
  const studyRevealedAt = derived?.record?.study_revealed_at || null;
  const firstAttemptMs = Date.parse(firstAttempt?.at || '');
  const studyRevealedMs = Date.parse(studyRevealedAt || '');
  if (repairs.length || derived?.state === 'solidified' || derived?.next_action === null) {
    return 'expanded-workspace';
  }
  const hasPreStudyColdAttempt = Boolean(firstAttempt && (
    !studyRevealedAt
    || !Number.isFinite(firstAttemptMs)
    || !Number.isFinite(studyRevealedMs)
    || firstAttemptMs <= studyRevealedMs
  ));
  if (
    derived.attempted
    && studyRevealedAt
    && hasPreStudyColdAttempt
    && options?.comparisonAcknowledged === false
  ) {
    return 'post-reveal-comparison';
  }
  if (derived.attempted && studyRevealedAt) return 'expanded-workspace';
  if (derived.attempted && derived.next_action === 'study') return 'saved-draft-study-gate';
  if (!derived.attempted) return 'cold-surface';
  return 'expanded-workspace';
}

function renderEvidenceArtifactHtml(derived) {
  const attempt = latestAttemptForRecord(derived.record);
  if (!attempt?.user_text) return '';
  const hasStudyReveal = Boolean(derived.record?.study_revealed_at);
  const isStudyGate = derived.next_action === 'study' && !hasStudyReveal;
  const isRepairing = derived.next_action === 'repair';
  const gaps = Array.isArray(attempt.gaps) && attempt.gaps.length
    ? attempt.gaps
    : (Array.isArray(derived.gaps) ? derived.gaps : []);
  const bridgeHtml = '';
  const hingeHtml = hasStudyReveal && !isRepairing && gaps.length
    ? `
      <div class="concept-page-b2__evidence-hinge">
        <span class="concept-page-b2__evidence-label">Missing piece</span>
        <ul>
          ${gaps.map((gap, index) => `
              <li>
                <strong>${escHtml(repairGapTitle(gap, index))}</strong>
                <span>${escHtml(repairGapCorrection(gap))}</span>
              </li>
            `).join('')}
        </ul>
      </div>
    `
    : '';

  return `
    <section class="concept-page-b2__evidence${isStudyGate ? ' concept-page-b2__evidence--study-gate' : ''}${isRepairing ? ' concept-page-b2__evidence--compact' : ''}" aria-label="Learner draft evidence">
      <span class="eyebrow concept-page-b2__evidence-eyebrow">${isStudyGate ? 'Your memory draft' : 'Your draft'}</span>
      <blockquote>${escHtml(attempt.user_text)}</blockquote>
      ${bridgeHtml}
      ${hingeHtml}
    </section>
  `;
}

function renderRepairPanelHtml(activeEntry, derived, activeEntryId, options = {}) {
  if (derived.next_action !== 'repair') return '';
  const gaps = Array.isArray(derived.gaps) && derived.gaps.length
    ? derived.gaps
    : [{ mechanism: 'missing link', correction: 'Write the part that was missing from your first attempt.' }];
  const entryId = activeEntryId || activeEntry.id || 'core-thesis';
  const repairs = Array.isArray(derived.record?.repairs) ? derived.record.repairs : [];
  const repairCheckedThisSession = repairs.length && options?.repairCheckedThisSession === true;
  const nextAttemptButton = repairs.length && !repairCheckedThisSession
    ? `<button class="concept-page-b2__entry-cta concept-page-b2__repair-attempt" type="button" data-active-entry-id="${escHtml(entryId)}" data-active-entry-action="drill-gap">Pressure-check this link</button>`
    : '';
  const repairTarget = repairGapCorrection(gaps[0]) || 'Write the part that was missing from your first attempt.';

  const helperHtml = repairCheckedThisSession
    ? '<p class="concept-page-b2__repair-helper">Return later for spaced reconstruction. A strong later answer can update the record. <button class="concept-page-b2__feedback-link" type="button" data-feedback-rating data-feedback-moment="repair checked">Rate this moment</button></p>'
    : repairs.length
    ? ''
    : `<p class="concept-page-b2__repair-helper">Use your words. One or two sentences is enough.</p>`;

  const inputFormHtml = repairs.length
    ? ''
    : `
      <textarea
        class="concept-page-b2__repair-input"
        data-repair-entry-id="${escHtml(entryId)}"
        aria-label="Write the missing link"
        rows="4"
        maxlength="1200"
        placeholder="Write the corrected link here."
      ></textarea>
      <p class="concept-page-b2__repair-error" data-repair-error hidden>Write the missing link before saving.</p>
      <button class="concept-page-b2__repair-save" type="button" data-repair-entry-id="${escHtml(entryId)}">Save repair</button>
    `;

  return `
    <section class="concept-page-b2__repair${repairs.length ? ' concept-page-b2__repair--saved' : ''}" data-repair-entry-id="${escHtml(entryId)}" aria-label="Repair missing link">
      <span class="eyebrow concept-page-b2__repair-eyebrow">${repairCheckedThisSession ? 'Repair checked' : repairs.length ? 'Repair saved' : 'Repair'}</span>
      <h3>${repairCheckedThisSession ? 'Repair checked for now.' : repairs.length ? 'Pressure-check the repaired link.' : 'Write the missing link.'}</h3>
      <div class="concept-page-b2__repair-target">
        <span>Missing link</span>
        <p>${escHtml(repairTarget)}</p>
      </div>
      ${helperHtml}
      ${inputFormHtml}
      ${nextAttemptButton}
    </section>
  `;
}

function nextReadyEntry(backbone, activeIdx, training, options = {}) {
  for (let index = activeIdx + 1; index < backbone.length; index += 1) {
    const derived = entryTraining(backbone, index, training, options);
    if (!derived.attempted && predecessorsAttempted(backbone, index, training, options)) {
      const entry = backbone[index];
      return {
        id: getConceptEntryId(entry, index),
      };
    }
  }
  return null;
}

function renderAttemptPanelHtml(activeEntryId, activeEntry, options = {}) {
  const scaffold = options.useScaffold ? entryScaffold(activeEntry) : null;
  const learnerGoal = cleanScaffoldText(options.learnerGoal);
  const targetLabel = cleanScaffoldText(scaffold?.task_label) || cleanScaffoldText(activeEntry?.label) || 'this entry';
  const heading = scaffold?.entry_prompt || 'Draft what you can recall';
  const helperParts = [
    learnerGoal && scaffold
      ? `Goal: ${learnerGoal}. First make a starting guess for ${targetLabel}.`
      : '',
    scaffold?.expected_shape || '',
  ].filter(Boolean);
  const helper = helperParts.join(' ');
  const placeholder = attemptPlaceholderForScaffold(scaffold);
  const buttonLabel = 'Save draft';
  const errorText = scaffold
    ? 'Write the smallest useful guess before study appears.'
    : 'Put down the part you can explain, even if it is incomplete.';
  const cueHtml = options.showCue ? renderBlankStartHtml(scaffold, activeEntryId) : '';
  return `
    <section class="concept-page-b2__attempt" data-attempt-entry-id="${escHtml(activeEntryId)}" aria-label="Memory reconstruction">
      <span class="eyebrow concept-page-b2__attempt-eyebrow visually-hidden">cold attempt</span>
      <h3>${escHtml(heading)}</h3>
      ${helper ? `<p class="concept-page-b2__attempt-helper">${escHtml(helper)}</p>` : ''}
      <textarea
        class="concept-page-b2__attempt-input"
        data-attempt-entry-id="${escHtml(activeEntryId)}"
        aria-label="Write what you can reconstruct"
        rows="6"
        maxlength="2400"
        placeholder="${escHtml(placeholder)}"
      ></textarea>
      <p class="concept-page-b2__attempt-error" data-attempt-error hidden>${escHtml(errorText)}</p>
      <div class="concept-page-b2__attempt-actions">
        <button class="concept-page-b2__attempt-save" type="button" data-attempt-entry-id="${escHtml(activeEntryId)}" disabled aria-disabled="true">${escHtml(buttonLabel)}</button>
        ${cueHtml}
      </div>
    </section>
  `;
}

function routeMarginPhase(entry, index) {
  const scaffold = entryScaffold(entry);
  if (scaffold) {
    return {
      title: scaffold.task_label || scaffold.learner_move || `Entry ${index + 1}`,
      cue: scaffold.task_cue || 'Write the smallest useful guess.',
    };
  }
  const phases = [
    { title: 'Say it', cue: 'Put the current model into words.' },
    { title: 'Explain how', cue: 'Name what causes what.' },
    { title: 'Use it', cue: 'Try the idea in a nearby case.' },
    { title: 'Test the edge', cue: 'Find where the model might break.' },
  ];
  return phases[index] || { title: `Entry ${index + 1}`, cue: 'continue the route' };
}

function getCrystalSvg(state) {
  const normalized = String(state || '').toLowerCase().replace(/\s+/g, '-');
  const stateClass = [
    'solidified',
    'needs-repair',
    'primed',
    'attempted',
    'ready-to-reconstruct',
    'locked',
  ].includes(normalized) ? normalized : 'locked';
  return `
    <svg class="node-strip-crystal node-strip-crystal--${stateClass}" viewBox="0 0 28 38" aria-hidden="true" focusable="false">
      <path class="node-strip-crystal__facet node-strip-crystal__facet--top" d="M14 1 26 10 14 17 2 10Z"></path>
      <path class="node-strip-crystal__facet node-strip-crystal__facet--left" d="M2 10 14 17 14 37 3 23Z"></path>
      <path class="node-strip-crystal__facet node-strip-crystal__facet--right" d="M26 10 14 17 14 37 25 23Z"></path>
      <path class="node-strip-crystal__axis" d="M14 1v36"></path>
    </svg>
  `;
}

function renderRouteMarginHtml(backbone, activeIdx, training, options = {}) {
  const nodes = backbone.length ? backbone : [FALLBACK_ACTIVE_ENTRY];
  const interactive = options.interactive !== false;
  const quiet = Boolean(options.quiet);
  const routeAttrs = [
    options.expandedRoute ? 'data-route-expanded="true"' : '',
    options.lockedInert ? 'data-locked-inert="true"' : '',
  ].filter(Boolean).join(' ');
  return `
    <aside class="concept-page-b2__route node-strip" aria-label="Concept route"${routeAttrs ? ` ${routeAttrs}` : ''}>
      <div class="node-strip__header">
        <span class="eyebrow concept-page-b2__route-eyebrow">draft route</span>
      </div>
      <ol class="concept-page-b2__route-list node-strip__list">
        ${nodes.map((entry, index) => {
          const scaffold = entryScaffold(entry);
          const phase = quiet
            ? {
              title: scaffold?.task_label || scaffold?.learner_move || '',
              cue: '',
            }
            : routeMarginPhase(entry, index);
          const state = entryLearnerState(nodes, index, training, options);
          const isActive = index === activeIdx;
          const entryId = getConceptEntryId(entry, index);
          const currentAttr = isActive ? ' aria-current="step"' : '';
          const stateToken = state.toLowerCase().replace(/\s+/g, '-');
          if (!interactive) {
            return `
              <li class="node-strip-item concept-page-b2__route-marker-item${isActive ? ' is-active' : ''}" data-route-state="${escHtml(state)}" data-node-state="${escHtml(stateToken)}" aria-label="${escHtml(`${phase.title || `Entry ${index + 1}`}${isActive ? ', current' : ''}`)}"${currentAttr}>
                <span class="concept-page-b2__route-index node-strip-num">${String(index + 1).padStart(2, '0')}</span>
                <span class="concept-page-b2__route-marker node-strip-marker" aria-hidden="true">${getCrystalSvg(state)}</span>
                ${phase.title ? `
                  <span class="concept-page-b2__route-copy node-strip-text">
                    <span class="concept-page-b2__route-title node-strip-title">${escHtml(phase.title)}</span>
                  </span>
                ` : ''}
              </li>
            `;
          }
          return `
            <li class="node-strip-item concept-page-b2__route-item${isActive ? ' is-active' : ''}" role="button" tabindex="0" data-entry-id="${escHtml(entryId)}" data-entry-index="${index}" data-route-state="${escHtml(state)}" data-node-state="${escHtml(stateToken)}" aria-label="${escHtml(`${phase.title}, ${state}${isActive ? ', current' : ''}`)}"${currentAttr}>
              <span class="concept-page-b2__route-index node-strip-num">${String(index + 1).padStart(2, '0')}</span>
              <span class="concept-page-b2__route-marker node-strip-marker" aria-hidden="true">${getCrystalSvg(state)}</span>
              <span class="concept-page-b2__route-copy node-strip-text">
                <span class="concept-page-b2__route-title node-strip-title">${escHtml(phase.title)}</span>
              </span>
            </li>
          `;
        }).join('')}
      </ol>
    </aside>
  `;
}

function renderBlankStartHtml(scaffold = null, activeEntryId = 'entry') {
  const hint = blankHintForScaffold(scaffold);
  const hintId = `blank-start-${String(activeEntryId || 'entry').replace(/[^a-zA-Z0-9_-]/g, '-')}`;
  return `
    <div class="concept-page-b2__blank-start">
      <button class="concept-page-b2__blank-start-button" type="button" data-blank-start aria-expanded="false" aria-controls="${escHtml(hintId)}">Need a cue?</button>
      <p class="concept-page-b2__blank-start-hint" id="${escHtml(hintId)}" data-blank-start-hint hidden>${escHtml(hint)}</p>
    </div>
  `;
}

function renderSketchWrapperHtml(thresholdText) {
  const hasSketch = Boolean(thresholdText);
  const preview = hasSketch
    ? thresholdText
    : 'You have not yet sketched what you think is inside this concept.';
  return `
    <section class="vd-sketch-wrapper concept-page-b2__threshold${hasSketch ? '' : ' concept-page-b2__threshold--empty'}" data-sketch-collapsed="true" aria-label="Concept context">
      <div class="vd-sketch-head">
        <button class="vd-sketch-toggle" type="button" data-action="toggle-sketch" aria-expanded="false" aria-controls="vd-sketch-body">
          <span class="concept-page-b2__threshold-label">Context</span>
          <span class="vd-sketch-preview">${escHtml(preview)}</span>
        </button>
        <a class="concept-page-b2__threshold-edit" href="javascript:void(0)" data-edit-threshold>${hasSketch ? 'edit' : 'add sketch'}</a>
      </div>
      <div class="vd-sketch-body" id="vd-sketch-body" hidden>
        <p>${escHtml(preview)}</p>
      </div>
    </section>
  `;
}

function renderDrillChamberHtml() {
  return `
    <section id="drill-chamber-view" class="drill-chamber-view" hidden aria-label="Reconstruction check">
      <div class="drill-chamber__inner">
        <nav class="drill-chamber__crumb" aria-label="Drill location">
          <a href="javascript:void(0)" id="chamber-exit" aria-label="Return to concept">
            <svg class="drill-chamber__back" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="15 18 9 12 15 6"/></svg>
            Return to concept
          </a>
          <span class="drill-chamber__sep" aria-hidden="true">·</span>
          <span id="chamber-concept-name">—</span>
          <span class="drill-chamber__sep" aria-hidden="true">·</span>
          <span class="drill-chamber__here" id="chamber-entry-name">—</span>
        </nav>

        <div class="drill-chamber__chat-log" id="chamber-chat-log" hidden></div>

        <div class="drill-chamber__active" id="chamber-active">
          <p class="drill-chamber__question" id="chamber-question">—</p>
          <div class="drill-chamber__composer">
            <textarea id="chamber-composer" placeholder="Write your reconstruction here. Fragments are fine." aria-label="Your reply" rows="3"></textarea>
            <div class="drill-chamber__composer-foot">
              <span class="drill-chamber__hint">A sentence is enough.</span>
              <button class="drill-chamber__send" id="chamber-send" type="button">Check reconstruction</button>
            </div>
          </div>
        </div>
      </div>
    </section>
  `;
}

export function renderActiveEntryHtml(activeEntry, activeIdx, backbone, concept, data, training = null, options = {}) {
  const meta = data?.metadata || {};
  const thresholdText = (concept?.startingMapContext || meta.starting_map_context || '').trim();
  const totalNodes = backbone.length || 1;
  const activeEntryId = getConceptEntryId(activeEntry, activeIdx);

  const derived = entryTraining(backbone, activeIdx, training, options);
  const sourceMode = sourceModeForConcept(concept, data, training);
  const isSourceLess = sourceMode === 'source_less';
  const viewMode = isSourceLess ? deriveSourceLessViewMode(derived, options) : (options?.viewMode || 'expanded-workspace');
  const isSavedDraftStudyGate = viewMode === 'saved-draft-study-gate';
  const isPostRevealComparison = viewMode === 'post-reveal-comparison';
  const isExpandedWorkspace = viewMode === 'expanded-workspace';
  const showsOnlyQuietRoute = viewMode === 'cold-surface';
  const hidesRouteAndNearby = isSourceLess || isSavedDraftStudyGate || isPostRevealComparison;
  const isBlocked = !derived.attempted && !predecessorsAttempted(backbone, activeIdx, training, options);
  const isColdReadyEntry = !isBlocked && !derived.attempted;
  const isAttempting = (
    !isBlocked
    && (isColdReadyEntry || options?.attemptEntryId === activeEntryId)
    && derived.next_action !== 'study'
    && (
      derived.next_action !== 'repair'
      || (Array.isArray(derived.record?.repairs) && derived.record.repairs.length > 0)
    )
    && derived.next_action !== 'review'
  );

  const entryEyebrow = activeEntryEyebrow({
    isBlocked,
    attempted: derived.attempted,
    state: derived.state,
    nextAction: derived.next_action,
    justRevealedStudy: (options?.justRevealedEntryId === activeEntryId || isPostRevealComparison) && Boolean(derived.record?.study_revealed_at),
    activeIdx,
    totalNodes,
  });
  const visibleEntryEyebrow = options?.isDrilling
    ? 'Pressure check'
    : options?.repairCheckedThisSession && derived.next_action === 'repair'
    ? 'Repair checked'
    : entryEyebrow;
  const studyGatePurpose = derived.attempted && derived.next_action === 'study'
    ? 'Your draft gives the notes something specific to work against. Study stays hidden until you choose to compare.'
    : '';
  const scaffold = entryScaffold(activeEntry);
  const activeEntryTitle = isSourceLess && scaffold
    ? (scaffold.task_label || scaffold.learner_move || activeEntry.label || 'Core thesis')
    : (activeEntry.label || 'Core thesis');
  const suppressPurposeForScaffoldAttempt = isAttempting && isColdReadyEntry && Boolean(scaffold?.entry_prompt);
  const entryPurpose = suppressPurposeForScaffoldAttempt
    ? ''
    : studyGatePurpose
      || scaffold?.task_cue
      || activeEntry.purpose
      || (isBlocked
        ? 'Locked until you write from memory on the entry above. The mechanism stays hidden until you have put your current model into words.'
        : 'The first entry asks for the governing idea, not the whole source. No study material yet. Write what you can reconstruct from memory.');
  const ctaLabel = activeEntryCtaLabel({
    attempted: derived.attempted,
    state: derived.state,
    nextAction: derived.next_action,
  });
  const ctaAction = derived.next_action === 'study' ? 'study' : 'drill';
  const collapseStudyNote = derived.next_action === 'repair' && !isPostRevealComparison;
  const hiddenStudyNoteText = options?.repairCheckedThisSession && derived.next_action === 'repair'
    ? 'Study note stays hidden for later reconstruction.'
    : 'Study note stays hidden while you repair.';
  const studyNoteHtml = derived.record?.study_revealed_at && !isAttempting
    ? `
      <section class="concept-page-b2__study-note${collapseStudyNote ? ' is-collapsed' : ''}" aria-label="Study note">
        <div class="concept-page-b2__study-note-header">
          <span class="eyebrow concept-page-b2__study-note-eyebrow">Study note</span>
          <button class="concept-page-b2__study-note-toggle" type="button" data-study-note-toggle aria-expanded="${collapseStudyNote ? 'false' : 'true'}">${collapseStudyNote ? 'Show study note' : 'Hide study note'}</button>
        </div>
        <p data-study-note-body>${escHtml(studyNoteForEntry(activeEntry, concept, data))}</p>
        <p class="concept-page-b2__study-note-hidden" data-study-note-hidden>${escHtml(hiddenStudyNoteText)}</p>
      </section>
    `
    : '';
  const evidenceArtifactHtml = !isAttempting ? renderEvidenceArtifactHtml(derived) : '';
  const repairPanelHtml = isAttempting ? '' : renderRepairPanelHtml(activeEntry, derived, activeEntryId, options);
  const attemptPanelHtml = isAttempting ? renderAttemptPanelHtml(activeEntryId, activeEntry, {
    useScaffold: isColdReadyEntry,
    showCue: isColdReadyEntry,
    learnerGoal: learnerGoalForConcept(concept, data),
  }) : '';

  const thresholdHtml = thresholdText
    ? renderSketchWrapperHtml(thresholdText)
    : renderSketchWrapperHtml('');
  const sourceLessProvenanceHtml = '';
  const contextDockLabel = 'Recall context';
  const nextReady = (derived.next_action === 'review' || (derived.next_action === 'repair' && options?.repairCheckedThisSession))
    ? nextReadyEntry(backbone, activeIdx, training, options)
    : null;
  const nextReadyButton = nextReady
    ? `<button class="concept-page-b2__entry-cta" type="button" data-active-entry-id="${escHtml(nextReady.id)}" data-active-entry-action="next-entry">${isSourceLess ? 'Continue' : 'Continue route'}</button>`
    : '';
  const ctaButton = options?.isDrilling || isAttempting || derived.next_action === 'repair' || derived.next_action === 'review' || derived.next_action === null
    ? (isPostRevealComparison
      && derived.next_action !== 'repair'
      ? (nextReadyButton || `<button class="concept-page-b2__entry-cta" type="button" data-active-entry-id="${escHtml(activeEntryId)}" data-active-entry-action="keep-working">Keep working</button>`)
      : nextReadyButton)
    : isBlocked
    ? `<button class="concept-page-b2__entry-cta concept-page-b2__entry-cta--disabled" type="button" disabled aria-disabled="true" title="Write from memory on the entry above first">Locked</button>`
    : `<button class="concept-page-b2__entry-cta" type="button" data-active-entry-id="${escHtml(activeEntryId)}" data-active-entry-action="${escHtml(ctaAction)}">${ctaLabel}</button>`;
  const compareFeedbackHtml = isPostRevealComparison
    ? ' <button class="concept-page-b2__feedback-link" type="button" data-feedback-rating data-feedback-moment="compare notes">Rate this moment</button>'
    : '';

  const activeEntryClass = [
    'concept-page-b2__active-entry',
    options?.isDrilling ? 'concept-page-b2__active-entry--drilling' : '',
    suppressPurposeForScaffoldAttempt ? 'concept-page-b2__active-entry--prompt-first' : '',
  ].filter(Boolean).join(' ');
  const activeHtml = `
    <section class="${activeEntryClass}" aria-label="Active concept entry">
      <span class="eyebrow concept-page-b2__entry-eyebrow">${escHtml(visibleEntryEyebrow)}</span>
      <h2 class="concept-page-b2__entry-title">${escHtml(activeEntryTitle)}</h2>
      ${entryPurpose ? `<p class="concept-page-b2__entry-purpose">${escHtml(entryPurpose)}</p>` : ''}
      ${options?.isDrilling ? renderDrillChamberHtml() : `
        ${evidenceArtifactHtml}
        ${studyNoteHtml}
        ${repairPanelHtml}
        ${attemptPanelHtml}
        ${ctaButton}
        <p class="concept-page-b2__truth-note">Your words shape the path. This is not a grade.${compareFeedbackHtml}</p>
      `}
    </section>
  `;

  const suppressNearbyForPrimaryHandoff = Boolean(nextReadyButton) && options?.repairCheckedThisSession === true;
  const nearby = !hidesRouteAndNearby && isExpandedWorkspace && !isAttempting && !suppressNearbyForPrimaryHandoff
    ? backbone.filter((n) => n !== activeEntry)
    : [];
  const nearbyHtml = nearby.length
    ? `
      <section class="concept-page-b2__nearby">
        <span class="eyebrow concept-page-b2__nearby-eyebrow">Nearby entries</span>
        <div class="concept-page-b2__nearby-list">
          ${nearby.map((n) => {
            const idx = backbone.indexOf(n);
            const num = String(idx + 1).padStart(2, '0');
            const status = entryLearnerState(backbone, idx, training, options);
            return `
              <div class="concept-page-b2__nearby-item">
                <span class="concept-page-b2__nearby-num">${escHtml(num)}</span>
                <span>${escHtml(entryDisplayLabel(n, idx))}</span>
                <span class="concept-page-b2__nearby-status">${escHtml(status)}</span>
              </div>
            `;
          }).join('')}
        </div>
      </section>
    `
    : '';

  const gestaltClass = `concept-page-b2__gestalt${hidesRouteAndNearby ? ' concept-page-b2__gestalt--single-column' : ''}`;

  return `
    <section class="${gestaltClass}" aria-label="Concept gestalt canvas">
      ${hidesRouteAndNearby ? '' : renderRouteMarginHtml(backbone, activeIdx, training, {
        ...options,
        interactive: !showsOnlyQuietRoute,
        quiet: showsOnlyQuietRoute,
        expandedRoute: isSourceLess && isExpandedWorkspace,
        lockedInert: isSourceLess && isExpandedWorkspace,
      })}
      <div class="concept-page-b2__work">
        <div class="concept-page-b2__context-dock" aria-label="${escHtml(contextDockLabel)}">
          ${thresholdHtml}
          ${sourceLessProvenanceHtml}
        </div>
        ${activeHtml}
        ${nearbyHtml}
      </div>
    </section>
  `;
}
