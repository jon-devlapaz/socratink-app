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
  if (derived.attempted) return derived.state || 'attempted';
  return predecessorsAttempted(backbone, index, training, options)
    ? 'ready to reconstruct'
    : 'locked';
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
      isPrimed
        ? 'concept-strip__node--primed'
        : (isReady ? 'concept-strip__node--ready' : 'concept-strip__node--locked'),
    ];
    if (isActive) cls.push('is-active');
    const r = isActive ? 9 : (isPrimed ? 7 : (isReady ? 7 : 6));
    const entryId = node.id || `entry-${i}`;
    const label = escHtml(node.label || `entry ${i + 1}`);
    const learnerState = entryLearnerState(backbone, i, training, options);
    const ariaLabel = `${node.label || 'entry'}, ${learnerState}${isActive ? ', current' : ''}`;
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

  const stripActiveLabel = activeEntry.label
    ? `${escHtml(activeEntry.label)} · ${activeIdx + 1} of ${totalNodes}`
    : `${activeIdx + 1} of ${totalNodes}`;

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

function activeEntryEyebrow({ isBlocked, attempted, state, nextAction }) {
  if (isBlocked) return 'locked';
  if (!attempted) return 'Start from memory';
  if (nextAction === 'study') return 'Study the gap';
  if (nextAction === 'repair') return 'Needs repair';
  if (state === 'needs repair' && nextAction === 'spaced_attempt') return 'Ready to reconstruct again';
  if (state === 'solidified') return 'solidified';
  if (nextAction === 'spaced_attempt') return 'Ready to reconstruct again';
  if (nextAction === 'review') return 'review pending';
  if (state === 'needs repair') return 'Needs repair';
  return 'Ready to reconstruct again';
}

function activeEntryCtaLabel({ attempted, state, nextAction }) {
  if (!attempted) return 'Write from memory';
  if (nextAction === 'study') return 'Compare with notes';
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
  return gap.correction || gap.description || gap.detail || gap.text || '';
}

function latestAttemptForRecord(record) {
  const attempts = Array.isArray(record?.attempts) ? record.attempts : [];
  return attempts.length ? attempts[attempts.length - 1] : null;
}

function renderEvidenceArtifactHtml(derived) {
  const attempt = latestAttemptForRecord(derived.record);
  if (!attempt?.user_text) return '';
  const hasStudyReveal = Boolean(derived.record?.study_revealed_at);
  const gaps = Array.isArray(attempt.gaps) && attempt.gaps.length
    ? attempt.gaps
    : (Array.isArray(derived.gaps) ? derived.gaps : []);
  const hingeHtml = hasStudyReveal
    ? `
      <div class="concept-page-b2__evidence-hinge">
        <span class="concept-page-b2__evidence-label">Missing piece</span>
        <ul>
          ${gaps.length
            ? gaps.map((gap, index) => `
              <li>
                <strong>${escHtml(repairGapTitle(gap, index))}</strong>
                <span>${escHtml(repairGapCorrection(gap))}</span>
              </li>
            `).join('')
            : '<li><span>No missing piece recorded for this draft.</span></li>'}
        </ul>
      </div>
    `
    : '';

  return `
    <section class="concept-page-b2__evidence" aria-label="Learner draft evidence">
      <span class="eyebrow concept-page-b2__evidence-eyebrow">Your draft</span>
      <blockquote>${escHtml(attempt.user_text)}</blockquote>
      ${hingeHtml}
    </section>
  `;
}

function renderRepairPanelHtml(activeEntry, derived, activeEntryId) {
  if (derived.next_action !== 'repair') return '';
  const gaps = Array.isArray(derived.gaps) && derived.gaps.length
    ? derived.gaps
    : [{ mechanism: 'missing link', correction: 'Write the part that was missing from your first attempt.' }];
  const entryId = activeEntryId || activeEntry.id || 'core-thesis';
  const repairs = Array.isArray(derived.record?.repairs) ? derived.record.repairs : [];
  const nextAttemptButton = repairs.length
    ? `<button class="concept-page-b2__entry-cta concept-page-b2__repair-attempt" type="button" data-active-entry-id="${escHtml(entryId)}">Try from memory again</button>`
    : '';
  return `
    <section class="concept-page-b2__repair" data-repair-entry-id="${escHtml(entryId)}" aria-label="Repair missing link">
      <span class="eyebrow concept-page-b2__repair-eyebrow">Put it in your words</span>
      <h3>Write the missing link</h3>
      <ul class="concept-page-b2__repair-gaps">
        ${gaps.map((gap, index) => `
          <li>
            <strong>${escHtml(repairGapTitle(gap, index))}</strong>
            <span>${escHtml(repairGapCorrection(gap))}</span>
          </li>
        `).join('')}
      </ul>
      <textarea
        class="concept-page-b2__repair-input"
        data-repair-entry-id="${escHtml(entryId)}"
        aria-label="Write the missing link"
        rows="4"
        maxlength="1200"
        placeholder="Name the corrected link in your own words."
      ></textarea>
      <p class="concept-page-b2__repair-error" data-repair-error hidden>Write the missing link before saving.</p>
      <button class="concept-page-b2__repair-save" type="button" data-repair-entry-id="${escHtml(entryId)}">Save repair</button>
      ${nextAttemptButton}
    </section>
  `;
}

function renderAttemptPanelHtml(activeEntryId) {
  return `
    <section class="concept-page-b2__attempt" data-attempt-entry-id="${escHtml(activeEntryId)}" aria-label="Memory reconstruction">
      <span class="eyebrow concept-page-b2__attempt-eyebrow">your reconstruction</span>
      <h3>Write what you can reconstruct</h3>
      <textarea
        class="concept-page-b2__attempt-input"
        data-attempt-entry-id="${escHtml(activeEntryId)}"
        aria-label="Write what you can reconstruct"
        rows="6"
        maxlength="2400"
        placeholder="Put the part you can explain in your own words."
      ></textarea>
      <p class="concept-page-b2__attempt-error" data-attempt-error hidden>Put down the part you can explain, even if it is incomplete.</p>
      <button class="concept-page-b2__attempt-save" type="button" data-attempt-entry-id="${escHtml(activeEntryId)}">Save what I wrote</button>
    </section>
  `;
}

export function renderActiveEntryHtml(activeEntry, activeIdx, backbone, concept, data, training = null, options = {}) {
  const meta = data?.metadata || {};
  const thresholdText = (concept?.startingMapContext || meta.starting_map_context || meta.core_thesis || '').trim();
  const totalNodes = backbone.length || 1;
  const activeEntryId = getConceptEntryId(activeEntry, activeIdx);

  const derived = entryTraining(backbone, activeIdx, training, options);
  const isBlocked = !derived.attempted && !predecessorsAttempted(backbone, activeIdx, training, options);
  const isAttempting = (
    !isBlocked
    && options?.attemptEntryId === activeEntryId
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
    activeIdx,
    totalNodes,
  });
  const entryPurpose = activeEntry.purpose
    || (isBlocked
      ? 'Locked until you write from memory on the entry above. The mechanism stays hidden until you have put your current model into words.'
      : 'The first entry asks for the governing idea, not the whole source. No study material yet. Write what you can reconstruct from memory.');
  const ctaLabel = activeEntryCtaLabel({
    attempted: derived.attempted,
    state: derived.state,
    nextAction: derived.next_action,
  });
  const ctaAction = derived.next_action === 'study' ? 'study' : 'drill';
  const studyNoteHtml = derived.record?.study_revealed_at && !isAttempting
    ? `
      <section class="concept-page-b2__study-note" aria-label="Study note">
        <div class="concept-page-b2__study-note-header">
          <span class="eyebrow concept-page-b2__study-note-eyebrow">Study note</span>
          <button class="concept-page-b2__study-note-toggle" type="button" data-study-note-toggle aria-expanded="true">Hide study note</button>
        </div>
        <p data-study-note-body>${escHtml(studyNoteForEntry(activeEntry, concept, data))}</p>
        <p class="concept-page-b2__study-note-hidden" data-study-note-hidden>Hidden while you write from memory.</p>
      </section>
    `
    : '';
  const evidenceArtifactHtml = !isAttempting ? renderEvidenceArtifactHtml(derived) : '';
  const repairPanelHtml = isAttempting ? '' : renderRepairPanelHtml(activeEntry, derived, activeEntryId);
  const attemptPanelHtml = isAttempting ? renderAttemptPanelHtml(activeEntryId) : '';

  const thresholdHtml = thresholdText
    ? `
      <p class="concept-page-b2__threshold">
        <span class="concept-page-b2__threshold-label">Your starting sketch:</span>
        ${escHtml(thresholdText)}
        <a class="concept-page-b2__threshold-edit" href="javascript:void(0)" data-edit-threshold>edit</a>
      </p>
    `
    : `
      <p class="concept-page-b2__threshold concept-page-b2__threshold--empty">
        You have not yet sketched what you think is inside this concept.
        <a class="concept-page-b2__threshold-edit" href="javascript:void(0)" data-edit-threshold>add sketch</a>
      </p>
    `;
  const provenanceHtml = training?.source_mode === 'source_less'
    ? `
      <p class="concept-page-b2__provenance">
        Shaped from your launch attempt, not verified against a source.
      </p>
    `
    : '';

  const ctaButton = isAttempting || derived.next_action === 'repair' || derived.next_action === 'review' || derived.next_action === null
    ? ''
    : isBlocked
    ? `<button class="concept-page-b2__entry-cta concept-page-b2__entry-cta--disabled" type="button" disabled aria-disabled="true" title="Write from memory on the entry above first">Locked</button>`
    : `<button class="concept-page-b2__entry-cta" type="button" data-active-entry-id="${escHtml(activeEntryId)}" data-active-entry-action="${escHtml(ctaAction)}">${ctaLabel}</button>`;

  const activeHtml = `
    <span class="eyebrow concept-page-b2__entry-eyebrow">${escHtml(entryEyebrow)}</span>
    <h2 class="concept-page-b2__entry-title">${escHtml(activeEntry.label || 'Core thesis')}</h2>
    <p class="concept-page-b2__entry-purpose">${escHtml(entryPurpose)}</p>
    ${evidenceArtifactHtml}
    ${studyNoteHtml}
    ${repairPanelHtml}
    ${attemptPanelHtml}
    ${ctaButton}
  `;

  const nearby = backbone.filter((n) => n !== activeEntry);
  const nearbyHtml = nearby.length
    ? `
      <section class="concept-page-b2__nearby">
        <span class="eyebrow concept-page-b2__nearby-eyebrow">nearby entries  all locked until first reconstruction</span>
        <div class="concept-page-b2__nearby-list">
          ${nearby.map((n) => {
            const idx = backbone.indexOf(n);
            const num = String(idx + 1).padStart(2, '0');
            const status = entryLearnerState(backbone, idx, training, options).toUpperCase();
            return `
              <div class="concept-page-b2__nearby-item">
                <span class="concept-page-b2__nearby-num">${escHtml(num)}</span>
                <span>${escHtml(n.label || `entry ${idx + 1}`)}</span>
                <span class="concept-page-b2__nearby-status">${escHtml(status)}</span>
              </div>
            `;
          }).join('')}
        </div>
      </section>
    `
    : '';

  return `${thresholdHtml}${provenanceHtml}${activeHtml}${nearbyHtml}`;
}
