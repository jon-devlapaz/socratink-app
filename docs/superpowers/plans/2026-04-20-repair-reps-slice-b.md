# Repair Reps Slice B Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task with verification-before-completion at each step. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add pre-reveal confidence pill, soft reveal gate enforced inside `revealRepairRep()`, single-click lock-and-reveal with per-rep lock-duration tracking, and a completion-summary calibration readout (observational only).

**Architecture:** Frontend + localStorage only. Three source files touched (`public/js/app.js`, `public/js/graph-view.js`, `public/css/layout.css`) plus cache-bust bumps in `public/index.html`, `public/js/app.js` line 4, and `public/js/learner-analytics.js` line 2. State shape is additive, storage schema is additive, and old records read cleanly. No backend, no prompts, no graph-state mutation.

**Tech Stack:** Vanilla JS (ES modules, no build step), Cytoscape-driven graph view, FastAPI backend (untouched), localStorage persistence.

**Spec:** `docs/superpowers/specs/2026-04-18-repair-reps-slice-b-metacognitive-loop-design.md`

---

## Pre-flight context (read before starting)

1. **`setRepairRepsState` (app.js:2479) is pure assignment** — every call triggers `setInteractionMode('repair-reps', ...)` → `renderCurrentDetail()` → `detailEl.innerHTML = ...`. The textarea is torn down and rebuilt on every dispatch. **Do not dispatch state on every keystroke** — it destroys caret position. The spec's draft-preservation invariant is satisfied by reading the live textarea value at pill-click time (the re-render trigger), not per-keystroke. The textarea `input` listener stays DOM-local (toggle button `disabled` only).

2. **Existing state callers build from scratch in three places** (`startRepairReps` at 2703, 2749, 2769) and **spread-update in others** (`revealRepairRep` 2796, `rateRepairRep` 2813, `nextRepairRep` 2836+2846). Every scratch-build instance must list the new fields. Spread-updates inherit them.

3. **Existing `typedAnswer` render logic** (graph-view.js:623) currently renders `currentAnswer` **only in revealed state**. Pre-reveal renders empty. **Change to render in both states** so draft survives pill re-renders.

4. **`learnops_repair_reps_v1` is not read by `learner-analytics.js`** — grep confirms it only appears in `app.js`. Additive schema is safe.

5. **Wave 1 semantic tokens confirmed present** in `public/css/variables.css`: `--surface-card`, `--text-strong`, `--text-muted`, `--accent-primary`, `--accent-soft`, `--accent-border-strong`, `--border-subtle`, `--accent-ring`, `--radius-pill`, `--duration-micro`. Use these — skip deprecated aliases (`--bg`, `--card-bg`, `--text`, `--primary`, `--border`, `--text-sub`).

6. **Cache-bust discipline** (every commit touching JS or CSS):
   - `public/index.html:25` — bump `styles.css?v=N` when any CSS file changes.
   - `public/index.html:495` — bump `js/app.js?v=N` when `app.js` changes.
   - `public/js/app.js:4` — bump `./graph-view.js?v=N` when `graph-view.js` changes.
   - `public/js/learner-analytics.js:2` — bump `./graph-view.js?v=N` in lockstep with app.js. If one bumps and the other doesn't, `learner-analytics` holds a stale module reference.

7. **Commit message format (Wave 1 convention):**
   ```
   <type>(<scope>): <short summary>

   <body>

   Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
   ```

---

## File Map

| File | Responsibility | Touched in steps |
|------|---------------|-----------------|
| `public/js/app.js` | State shape, reducer, reveal gate, completion storage write, `window.SocratinkApp` export | Steps 1, 5 |
| `public/js/graph-view.js` | Markup helpers + listener binding in `renderCurrentDetail()` | Steps 2, 3 |
| `public/css/layout.css` | Pill/calibration CSS rules | Step 4 |
| `public/index.html` | `styles.css?v=N` + `js/app.js?v=N` cache-bust | Each step that touches the corresponding file |
| `public/js/learner-analytics.js` | `graph-view.js?v=N` cache-bust (lockstep with app.js line 4) | Steps 2, 3 |
| `docs/superpowers/plans/2026-04-20-repair-reps-slice-b.md` | This plan | Step 0 |

---

## Task 0: Commit this plan

**Files:**
- Create: `docs/superpowers/plans/2026-04-20-repair-reps-slice-b.md`

- [ ] **Step 0.1: Stage and commit the plan file**

```bash
git add docs/superpowers/plans/2026-04-20-repair-reps-slice-b.md
git commit -m "$(cat <<'EOF'
docs(plan): Repair Reps Slice B implementation plan

Step-by-step plan for pre-reveal confidence pill, soft reveal gate
inside revealRepairRep(), lock-and-reveal with per-rep lock duration,
and completion calibration summary. No backend or prompt changes.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

Expected: one commit, clean tree.

---

## Task 1: app.js reducer + state + reveal gate + predict export

**Files:**
- Modify: `public/js/app.js:2479-2482` (setRepairRepsState — no change; just verify)
- Modify: `public/js/app.js:2703-2720` (startRepairReps loading state init)
- Modify: `public/js/app.js:2749-2766` (startRepairReps ready state init)
- Modify: `public/js/app.js:2769-2786` (startRepairReps error state init)
- Modify: `public/js/app.js:2790-2805` (revealRepairRep preconditions + body)
- Modify: `public/js/app.js:2822-2855` (nextRepairRep reset + restamp + complete)
- Modify: `public/js/app.js` near line 2790 (add setRepairRepPreConfidence function)
- Modify: `public/js/app.js:3990-3995` (add to export list)
- Modify: `public/index.html:495` (cache-bust bump)

### Step 1.1 — Define pre-confidence enum constant

- [ ] **Add the enum constant above `REPAIR_REP_RATING_VALUES` (currently line 2437)**

Locate in `public/js/app.js`:
```js
  const REPAIR_REP_RATING_VALUES = new Set(['close_match', 'partial', 'missed']);
```

Replace with:
```js
  const REPAIR_REP_PRE_CONFIDENCE_VALUES = new Set(['guessing', 'hunch', 'can_explain']);
  const REPAIR_REP_RATING_VALUES = new Set(['close_match', 'partial', 'missed']);
```

### Step 1.2 — Extend `startRepairReps` loading state

- [ ] **Replace the `setRepairRepsState({ status: 'loading', ...})` block at lines 2703-2720**

```js
    setRepairRepsState({
      status: 'loading',
      conceptId: concept.id,
      nodeId: nodeContext.id,
      nodeLabel,
      gapType: nodeData.gap_type || null,
      promptVersion: null,
      reps: [],
      currentIndex: 0,
      revealed: false,
      currentAnswer: '',
      answerLengths: [],
      ratings: [],
      ratingSelected: false,
      isDealing: false,
      isRevealing: false,
      error: null,
      currentPreConfidence: null,
      repStartedAt: null,
      lockedAt: null,
      preConfidences: [],
      lockDurationsMs: [],
    });
```

### Step 1.3 — Extend `startRepairReps` ready state (stamp repStartedAt for rep 1)

- [ ] **Replace the `setRepairRepsState({ status: 'ready', ...})` block at lines 2749-2766**

```js
      setRepairRepsState({
        status: 'ready',
        conceptId: concept.id,
        nodeId: nodeContext.id,
        nodeLabel,
        gapType: nodeData.gap_type || null,
        promptVersion: payload.prompt_version || 'repair-reps-system-v1',
        reps,
        currentIndex: 0,
        revealed: false,
        currentAnswer: '',
        answerLengths: [],
        ratings: [],
        ratingSelected: false,
        isDealing: true,
        isRevealing: false,
        error: null,
        currentPreConfidence: null,
        repStartedAt: Date.now(),
        lockedAt: null,
        preConfidences: [],
        lockDurationsMs: [],
      });
```

### Step 1.4 — Extend `startRepairReps` error state

- [ ] **Replace the `setRepairRepsState({ status: 'error', ...})` block at lines 2769-2786**

```js
      setRepairRepsState({
        status: 'error',
        conceptId: concept.id,
        nodeId: nodeContext.id,
        nodeLabel,
        gapType: nodeData.gap_type || null,
        promptVersion: null,
        reps: [],
        currentIndex: 0,
        revealed: false,
        currentAnswer: '',
        answerLengths: [],
        ratings: [],
        ratingSelected: false,
        isDealing: false,
        isRevealing: false,
        error: 'Repair Reps could not load. Reopen study and try again later.',
        currentPreConfidence: null,
        repStartedAt: null,
        lockedAt: null,
        preConfidences: [],
        lockDurationsMs: [],
      });
```

### Step 1.5 — Replace `revealRepairRep` with idempotent, pre-confidence-gated version

- [ ] **Replace the entire `revealRepairRep` function (lines 2790-2805)**

```js
  function revealRepairRep(answerText = '') {
    if (!repairRepsState || repairRepsState.status !== 'ready') return;
    // Idempotency: second call on the same rep is a no-op so lockedAt,
    // preConfidences, and lockDurationsMs are written exactly once.
    if (repairRepsState.revealed === true) return;
    const answer = String(answerText || '').trim();
    if (!answer) return;
    if (!REPAIR_REP_PRE_CONFIDENCE_VALUES.has(repairRepsState.currentPreConfidence)) return;

    const currentIndex = repairRepsState.currentIndex || 0;
    const lockedAt = Date.now();
    const repStartedAt = Number.isFinite(repairRepsState.repStartedAt)
      ? repairRepsState.repStartedAt
      : lockedAt;
    const lockDuration = Math.max(0, lockedAt - repStartedAt);

    const answerLengths = [...(repairRepsState.answerLengths || [])];
    answerLengths[currentIndex] = answer.length;
    const preConfidences = [...(repairRepsState.preConfidences || []), repairRepsState.currentPreConfidence];
    const lockDurationsMs = [...(repairRepsState.lockDurationsMs || []), lockDuration];

    setRepairRepsState({
      ...repairRepsState,
      revealed: true,
      currentAnswer: answer,
      answerLengths,
      preConfidences,
      lockDurationsMs,
      lockedAt,
      ratingSelected: Boolean(repairRepsState.ratings?.[currentIndex]),
      isDealing: false,
      isRevealing: true,
    });
  }
```

### Step 1.6 — Add `setRepairRepPreConfidence` handler

- [ ] **Insert new function immediately after `revealRepairRep` (before `rateRepairRep`)**

```js
  function setRepairRepPreConfidence(value) {
    if (!repairRepsState || repairRepsState.status !== 'ready') return;
    // Pill is frozen post-reveal. UI also suppresses via aria-disabled + pointer-events,
    // but gate here so direct JS calls cannot mutate the locked-in stance.
    if (repairRepsState.revealed === true) return;
    if (!REPAIR_REP_PRE_CONFIDENCE_VALUES.has(value)) return;
    setRepairRepsState({
      ...repairRepsState,
      currentPreConfidence: value,
    });
  }
```

Note: `currentAnswer` preservation on pill click happens at the listener site in graph-view.js (it reads the live textarea value and passes it as part of a broader state update when needed). This handler is kept narrow: it only mutates `currentPreConfidence`. The render loop picks up the new pill highlight and re-renders the textarea from `state.currentAnswer`.

To make that work, the pill-click listener in graph-view.js (Task 3) will first write the live textarea value to `currentAnswer` by calling a sibling helper — see Step 1.6b.

### Step 1.6b — Add `setRepairRepDraft` helper (used by pill listener to preserve draft)

- [ ] **Insert new function immediately after `setRepairRepPreConfidence`**

```js
  function setRepairRepDraft(value) {
    if (!repairRepsState || repairRepsState.status !== 'ready') return;
    if (repairRepsState.revealed === true) return;
    setRepairRepsState({
      ...repairRepsState,
      currentAnswer: typeof value === 'string' ? value : '',
    });
  }
```

This helper is called by the pill-click listener **before** `setRepairRepPreConfidence`, so the draft is stamped into state first and the re-render renders it back into the textarea. The textarea `input` listener does **not** call this — it stays DOM-local to avoid caret thrash on every keystroke.

### Step 1.7 — Extend `nextRepairRep` — reset per-rep fields + restamp `repStartedAt`

- [ ] **Replace the entire `nextRepairRep` function (lines 2822-2855)**

```js
  function nextRepairRep() {
    if (!repairRepsState || repairRepsState.status !== 'ready') return;
    if (!repairRepsState.revealed || !repairRepsState.ratingSelected) return;
    const nextIndex = (repairRepsState.currentIndex || 0) + 1;
    if (nextIndex >= (repairRepsState.reps || []).length) {
      recordRepairRepsCompletion({
        conceptId: repairRepsState.conceptId,
        nodeId: repairRepsState.nodeId,
        repCount: repairRepsState.reps.length,
        promptVersion: repairRepsState.promptVersion,
        gapType: repairRepsState.gapType,
        answerLengths: repairRepsState.answerLengths,
        ratings: repairRepsState.ratings,
        preConfidences: repairRepsState.preConfidences,
        lockDurationsMs: repairRepsState.lockDurationsMs,
      });
      setRepairRepsState({
        ...repairRepsState,
        status: 'complete',
        revealed: true,
        isDealing: false,
        isRevealing: false,
      });
      return;
    }

    setRepairRepsState({
      ...repairRepsState,
      currentIndex: nextIndex,
      revealed: false,
      currentAnswer: '',
      ratingSelected: false,
      isDealing: true,
      isRevealing: false,
      currentPreConfidence: null,
      lockedAt: null,
      repStartedAt: Date.now(),
    });
  }
```

Note: Task 5 extends `recordRepairRepsCompletion` to accept the two new named arguments. The spread order above (`preConfidences`, `lockDurationsMs`) matches Task 5's signature.

### Step 1.8 — Add exports to `window.SocratinkApp`

- [ ] **Extend the export block at lines 3990-3995**

Find:
```js
    startRepairReps,
    getRepairRepsState,
    revealRepairRep,
    rateRepairRep,
    nextRepairRep,
    exitRepairReps,
```

Replace with:
```js
    startRepairReps,
    getRepairRepsState,
    revealRepairRep,
    rateRepairRep,
    nextRepairRep,
    exitRepairReps,
    setRepairRepPreConfidence,
    setRepairRepDraft,
```

### Step 1.9 — Bump `js/app.js` cache-bust

- [ ] **Edit `public/index.html:495`**

Find:
```html
  <script type="module" src="js/app.js?v=27"></script>
```

Replace with:
```html
  <script type="module" src="js/app.js?v=28"></script>
```

### Step 1.10 — Node syntax check

- [ ] **Run `node --check` on both JS files**

Run:
```bash
node --check public/js/app.js
node --check public/js/graph-view.js
```

Expected: both silent (no output = pass). Any parse error blocks progress; fix before continuing.

### Step 1.11 — Commit

- [ ] **Stage and commit**

```bash
git add public/js/app.js public/index.html
git commit -m "$(cat <<'EOF'
feat(repair-reps): Slice B reducer — per-rep pre-confidence + lock timing

- Add REPAIR_REP_PRE_CONFIDENCE_VALUES enum (guessing/hunch/can_explain).
- Extend startRepairReps loading/ready/error state init with
  currentPreConfidence, repStartedAt, lockedAt, preConfidences,
  lockDurationsMs. Stamp repStartedAt for rep 1 in ready state.
- Rewrite revealRepairRep with idempotency guard (no-op if already
  revealed), empty-answer guard, and pre-confidence enum guard.
  Compute lockedAt - repStartedAt and push to per-rep arrays.
- Add setRepairRepPreConfidence(value) + setRepairRepDraft(value)
  handlers, both frozen post-reveal. Export on window.SocratinkApp.
- Extend nextRepairRep to reset currentPreConfidence/lockedAt and
  re-stamp repStartedAt for subsequent reps. Forward preConfidences
  and lockDurationsMs into recordRepairRepsCompletion.
- Bump js/app.js?v=27 -> v=28.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

Expected: one new commit. `git status` clean.

---

## Task 2: graph-view.js markup helpers + ready/revealed/complete rendering

**Files:**
- Modify: `public/js/graph-view.js:553-654` (repairRepsMarkupForNode — ready block around lines 609-653 plus complete block 582-607)
- Modify: `public/js/graph-view.js` (add two new pure helpers immediately before `repairRepsMarkupForNode`)
- Modify: `public/js/app.js:4` (bump graph-view.js?v=3 -> v=4)
- Modify: `public/js/learner-analytics.js:2` (bump graph-view.js?v=3 -> v=4 in lockstep)

### Step 2.1 — Add label-map constants + two pure helpers

- [ ] **Insert above `function repairRepsMarkupForNode` (line 553) in `public/js/graph-view.js`**

```js
const REPAIR_PRE_CONFIDENCE_LABELS = {
  guessing: 'Guessing',
  hunch: 'Have a hunch',
  can_explain: 'Can explain',
};

const REPAIR_RATING_SUMMARY_LABELS = {
  close_match: 'Close match',
  partial: 'Partly linked',
  missed: 'Missed the link',
};

function repairPredictPillsMarkup(currentPreConfidence, isLocked) {
  const selected = typeof currentPreConfidence === 'string' ? currentPreConfidence : '';
  const lockedAttr = isLocked ? ' aria-disabled="true"' : '';
  const lockedClass = isLocked ? ' is-locked' : '';
  const pill = (value, label) => {
    const checked = selected === value ? 'true' : 'false';
    const selClass = selected === value ? ' is-selected' : '';
    return `<button type="button" class="graph-repair-predict-pill trigger-repair-predict${selClass}" data-pre="${value}" role="radio" aria-checked="${checked}">${label}</button>`;
  };
  return `
    <div class="graph-repair-predict">
      <div class="graph-detail-kicker">Before you peek</div>
      <div class="graph-repair-predict-group${lockedClass}" role="radiogroup" aria-label="Confidence before revealing reference"${lockedAttr}>
        ${pill('guessing', 'Guessing')}
        ${pill('hunch', 'Have a hunch')}
        ${pill('can_explain', 'Can explain')}
      </div>
    </div>
  `;
}

function repairCalibrationSummaryMarkup(preConfidences, ratings) {
  const preList = Array.isArray(preConfidences) ? preConfidences : [];
  const rateList = Array.isArray(ratings) ? ratings : [];
  const rowCount = Math.min(preList.length, rateList.length);
  if (rowCount === 0) return '';
  const rows = [];
  for (let i = 0; i < rowCount; i += 1) {
    const preLabel = REPAIR_PRE_CONFIDENCE_LABELS[preList[i]] || 'Not recorded';
    const rateLabel = REPAIR_RATING_SUMMARY_LABELS[rateList[i]] || 'Not recorded';
    rows.push(`
      <div class="graph-repair-summary-row">
        <span class="graph-repair-summary-rep">Rep ${i + 1}</span>
        <span class="graph-repair-summary-pair"><span class="muted">Predicted:</span> ${escHtml(preLabel)}</span>
        <span class="graph-repair-summary-pair"><span class="muted">Rated:</span> ${escHtml(rateLabel)}</span>
      </div>
    `);
  }
  return `<div class="graph-repair-summary graph-repair-calibration">${rows.join('')}</div>`;
}
```

### Step 2.2 — Extend ready-before-reveal markup (pill section above textarea, locked row after reveal, render textarea from state in all states, update button label + helper)

- [ ] **Replace the ready-state return block (lines 609-653) in `repairRepsMarkupForNode`**

Find the block starting at line 609 (`const reps = Array.isArray(state.reps)...`) down to the closing backtick at line 653. Replace with:

```js
  const reps = Array.isArray(state.reps) ? state.reps : [];
  const currentIndex = Math.min(Math.max(Number(state.currentIndex || 0), 0), Math.max(reps.length - 1, 0));
  const rep = reps[currentIndex] || null;
  if (!rep) {
    return `
      ${repairContextStripMarkup({ nodeLabel, phaseLabel: 'Repair Reps' })}
      <div class="graph-detail-kicker">Repair Reps</div>
      <h3 class="graph-detail-title">${escHtml(nodeLabel)}</h3>
      <p class="graph-detail-copy">Repair Reps are not ready for this node yet.</p>
      <button class="${actionButtonClass} trigger-repair-exit">Back to graph</button>
    `;
  }

  const revealed = Boolean(state.revealed);
  const typedAnswer = escHtml(state.currentAnswer || '');
  const ratingSelected = Boolean(state.ratingSelected || state.ratings?.[currentIndex]);
  const preConfidence = state.currentPreConfidence || '';
  const pillsMarkup = repairPredictPillsMarkup(preConfidence, revealed);
  const preConfidenceValid = preConfidence === 'guessing' || preConfidence === 'hunch' || preConfidence === 'can_explain';
  const hasAnswer = typeof state.currentAnswer === 'string' && state.currentAnswer.trim().length > 0;
  const revealReady = preConfidenceValid && hasAnswer;
  return `
    ${repairContextStripMarkup({ nodeLabel, phaseLabel: `Repair Rep ${currentIndex + 1} of ${reps.length}` })}
    <div class="graph-study-shell graph-repair-shell">
      <section class="graph-detail-surface graph-repair-card ${state.isDealing ? 'is-dealing' : ''}">
        ${repairProgressMarkup({ currentIndex, total: reps.length })}
        <div class="graph-detail-kicker">Causal bridge</div>
        <p class="graph-detail-copy">${escHtml(rep.prompt)}</p>
        ${pillsMarkup}
        <div class="graph-detail-kicker">Your bridge</div>
        <textarea class="graph-repair-input" rows="4" aria-describedby="repair-reveal-helper" ${revealed ? 'readonly' : ''}>${typedAnswer}</textarea>
        ${revealed ? '' : '<p class="graph-detail-copy graph-repair-helper">Trace the causal link in one or two sentences.</p>'}
        ${revealed ? `
          <div class="graph-repair-bridge ${state.isRevealing ? 'is-revealing' : ''}">
            <div class="graph-detail-kicker">Reference bridge</div>
            <p class="graph-detail-copy">${escHtml(rep.target_bridge)}</p>
            <p class="graph-detail-copy graph-repair-compare-cue">Compare the link, not the wording.</p>
          </div>
          ${repairRatingMarkup(state, currentIndex)}
        ` : ''}
      </section>
      <section class="graph-detail-surface graph-study-next graph-repair-next">
        <p class="graph-detail-copy graph-repair-truth-line">Practice only. Graph progress comes from re-drill.</p>
        ${revealed
          ? (ratingSelected
            ? `<button class="${actionButtonClass} trigger-repair-next">${currentIndex + 1 >= reps.length ? 'Finish Reps' : 'Next Rep'}</button>`
            : '<p class="graph-detail-copy graph-repair-rating-hint">Choose the closest comparison before moving on.</p>')
          : `
            <button class="${actionButtonClass} trigger-repair-reveal" ${revealReady ? '' : 'disabled'} aria-describedby="repair-reveal-helper">Lock in and show reference bridge</button>
            <p class="graph-repair-reveal-helper" id="repair-reveal-helper">Pick a stance and type your bridge to continue.</p>
          `}
      </section>
    </div>
  `;
```

Changes from original:
- `typedAnswer = escHtml(state.currentAnswer || '')` is no longer gated by `revealed` — renders in both states for draft preservation.
- Pill markup injected between the rep prompt and the "Your bridge" kicker.
- Textarea gains `aria-describedby="repair-reveal-helper"`.
- Reveal button: label changes to **`Lock in and show reference bridge`**, `disabled` attribute now depends on `revealReady` (pill + non-empty answer), gains `aria-describedby`.
- Helper paragraph with `id="repair-reveal-helper"` added below reveal button.

### Step 2.3 — Extend complete-state markup with calibration summary

- [ ] **Replace the complete-state block in `repairRepsMarkupForNode` (lines 582-607)**

Find the block starting `if (status === 'complete')` at line 582 through the closing `}` at line 607. Replace with:

```js
  if (status === 'complete') {
    const reps = Array.isArray(state.reps) ? state.reps : [];
    const ratings = Array.isArray(state.ratings) ? state.ratings : [];
    const preConfidences = Array.isArray(state.preConfidences) ? state.preConfidences : [];
    const calibrationMarkup = repairCalibrationSummaryMarkup(preConfidences, ratings);
    const legacySummaryRows = reps.length && !calibrationMarkup
      ? reps.map((rep, index) => {
        const rating = ratings[index] || '';
        return `
          <div class="graph-repair-summary-row">
            <span class="graph-detail-pill">${escHtml(repairKindLabel(rep.kind))}</span>
            <span class="graph-repair-summary-rating ${escHtml(rating)}">${escHtml(repairRatingLabel(rating))}</span>
          </div>
        `;
      }).join('')
      : '';
    return `
      ${repairContextStripMarkup({ nodeLabel, phaseLabel: 'Repair Reps complete' })}
      <div class="graph-repair-complete">
        <div class="graph-detail-kicker">Repair Reps</div>
        ${repairProgressMarkup({ currentIndex: 2, total: Math.max(reps.length, 3), complete: true })}
        <h3 class="graph-detail-title">Practice logged</h3>
        <p class="graph-detail-copy">Three bridge reps saved on ${escHtml(nodeLabel)}.</p>
        ${calibrationMarkup || (legacySummaryRows ? `<div class="graph-repair-summary">${legacySummaryRows}</div>` : '')}
        <p class="graph-detail-copy">These reps are saved. Graph progress comes from the next re-drill.</p>
        <button class="${actionButtonClass} trigger-repair-exit">Back to graph</button>
      </div>
    `;
  }
```

Calibration markup (new per-rep predicted/rated rows) takes precedence. Legacy summary (kind + rating badges) is preserved as fallback only when the new arrays are both empty — ensures old records without `pre_confidences` still show something and don't regress.

### Step 2.4 — Bump graph-view.js cache-bust in BOTH importers

- [ ] **Edit `public/js/app.js:4`**

Find:
```js
import { escHtml, mountKnowledgeGraph } from './graph-view.js?v=3';
```

Replace with:
```js
import { escHtml, mountKnowledgeGraph } from './graph-view.js?v=4';
```

- [ ] **Edit `public/js/learner-analytics.js:2`**

Find:
```js
import { escHtml, transformKnowledgeMapToGraph } from './graph-view.js?v=3';
```

Replace with:
```js
import { escHtml, transformKnowledgeMapToGraph } from './graph-view.js?v=4';
```

Both must be bumped in lockstep. Skipping either leaves that importer pinned to a stale module.

### Step 2.5 — Bump `js/app.js` cache-bust again (since app.js line 4 changed)

- [ ] **Edit `public/index.html:495`**

Find:
```html
  <script type="module" src="js/app.js?v=28"></script>
```

Replace with:
```html
  <script type="module" src="js/app.js?v=29"></script>
```

### Step 2.6 — Node syntax check

- [ ] **Run `node --check` on both JS files**

```bash
node --check public/js/app.js
node --check public/js/graph-view.js
```

Expected: silent.

### Step 2.7 — Commit

- [ ] **Stage and commit**

```bash
git add public/js/graph-view.js public/js/app.js public/js/learner-analytics.js public/index.html
git commit -m "$(cat <<'EOF'
feat(repair-reps): Slice B markup helpers + ready/complete templates

- Add repairPredictPillsMarkup() and repairCalibrationSummaryMarkup()
  pure helpers with fixed enum->label maps. Calibration helper tolerates
  length mismatches (renders min(length) rows) and returns '' on empty
  arrays so old records omit the block entirely.
- Extend ready-state repairRepsMarkupForNode: inject pills above
  "Your bridge", always render textarea from state.currentAnswer for
  draft preservation (not just in revealed state), switch reveal-button
  label to "Lock in and show reference bridge", gate disabled by pill +
  non-empty answer, add aria-describedby helper text.
- Extend complete-state markup with calibration summary block
  ("Rep N / Predicted: X / Rated: Y"). Fall back to legacy kind/rating
  rows only when both new arrays are empty.
- Bump graph-view.js?v=3 -> v=4 in both importers (app.js line 4
  and learner-analytics.js line 2). Bump js/app.js?v=28 -> v=29 in
  index.html.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: graph-view.js listener binding in renderCurrentDetail

**Files:**
- Modify: `public/js/graph-view.js:1613-1636` (listener binding block)
- Modify: `public/js/app.js:4` (bump graph-view.js?v=4 -> v=5)
- Modify: `public/js/learner-analytics.js:2` (bump in lockstep)
- Modify: `public/index.html:495` (bump app.js?v=29 -> v=30)

### Step 3.1 — Rewrite the listener block in `renderCurrentDetail`

- [ ] **Replace lines 1613-1636 in `public/js/graph-view.js`** (from the `const repairBtn = ...` line through the `.trigger-repair-exit` binding)

Find the existing block that starts with:
```js
        const repairBtn = detailEl.querySelector('.trigger-repair');
        if (repairBtn) repairBtn.addEventListener('click', () => { window.SocratinkApp?.startRepairReps?.(activeNode.data()); });
        const repairRevealBtn = detailEl.querySelector('.trigger-repair-reveal');
```

And replace the listener block (through the `.trigger-repair-exit` listener) with:

```js
        const repairBtn = detailEl.querySelector('.trigger-repair');
        if (repairBtn) repairBtn.addEventListener('click', () => { window.SocratinkApp?.startRepairReps?.(activeNode.data()); });

        const repairInput = detailEl.querySelector('.graph-repair-input');
        const repairRevealBtn = detailEl.querySelector('.trigger-repair-reveal');

        // Read the current pre-confidence from app state — the render was
        // driven by it, so it's authoritative. Re-eval of the reveal-enable
        // predicate on every keystroke stays DOM-local (no state dispatch)
        // to avoid destroying caret position on textarea re-render.
        const repairState = window.SocratinkApp?.getRepairRepsState?.(activeNode.id()) || null;
        const preConfidenceValid = repairState
          && (repairState.currentPreConfidence === 'guessing'
            || repairState.currentPreConfidence === 'hunch'
            || repairState.currentPreConfidence === 'can_explain');

        if (repairInput && repairRevealBtn) {
          const syncRevealReadiness = () => {
            const hasAnswer = repairInput.value.trim().length > 0;
            repairRevealBtn.disabled = !(preConfidenceValid && hasAnswer);
          };
          syncRevealReadiness();
          repairInput.addEventListener('input', syncRevealReadiness);
        }

        if (repairRevealBtn) {
          repairRevealBtn.addEventListener('click', () => {
            const answer = repairInput?.value || '';
            window.SocratinkApp?.revealRepairRep?.(answer);
          });
        }

        // Pill listeners — on click, stamp the live textarea draft into
        // state first (so re-render preserves the in-flight answer), then
        // set the pre-confidence. The render loop will re-render the
        // textarea with value="${currentAnswer}" and re-highlight the pill.
        detailEl.querySelectorAll('.trigger-repair-predict').forEach((btn) => {
          btn.addEventListener('click', () => {
            const liveDraft = repairInput?.value || '';
            window.SocratinkApp?.setRepairRepDraft?.(liveDraft);
            window.SocratinkApp?.setRepairRepPreConfidence?.(btn.dataset.pre);
          });
        });

        const repairNextBtn = detailEl.querySelector('.trigger-repair-next');
        if (repairNextBtn) repairNextBtn.addEventListener('click', () => { window.SocratinkApp?.nextRepairRep?.(); });
        detailEl.querySelectorAll('.trigger-repair-rate').forEach((btn) => {
          btn.addEventListener('click', () => {
            window.SocratinkApp?.rateRepairRep?.(btn.dataset.rating);
          });
        });
        const repairExitBtn = detailEl.querySelector('.trigger-repair-exit');
        if (repairExitBtn) repairExitBtn.addEventListener('click', () => { window.SocratinkApp?.exitRepairReps?.(); });
```

Key correctness notes:
- `setRepairRepDraft` is called **before** `setRepairRepPreConfidence` so the draft is in state before the re-render triggered by the pill change.
- The textarea `input` listener stays DOM-local — it only toggles `disabled` based on live textarea value and the (already rendered) pre-confidence. **It does not dispatch state**, preserving caret.
- The reveal-gate enforcement is dual: UI disables the button AND `revealRepairRep()` itself no-ops if preconditions fail (Task 1 Step 1.5).

### Step 3.2 — Bump cache-bust (graph-view.js and app.js both changed)

- [ ] **Edit `public/js/app.js:4`**

`./graph-view.js?v=4` → `./graph-view.js?v=5`

- [ ] **Edit `public/js/learner-analytics.js:2`**

`./graph-view.js?v=4` → `./graph-view.js?v=5`

- [ ] **Edit `public/index.html:495`**

`js/app.js?v=29` → `js/app.js?v=30`

### Step 3.3 — Node syntax check

- [ ] **Run**

```bash
node --check public/js/app.js
node --check public/js/graph-view.js
```

Expected: silent.

### Step 3.4 — Commit

- [ ] **Stage and commit**

```bash
git add public/js/graph-view.js public/js/app.js public/js/learner-analytics.js public/index.html
git commit -m "$(cat <<'EOF'
feat(repair-reps): Slice B listeners — pill click, dual reveal gate

- Bind .trigger-repair-predict click listeners. Each stamps the live
  textarea draft into state (setRepairRepDraft) BEFORE setting the
  pre-confidence (setRepairRepPreConfidence) so the render triggered
  by the pill change re-renders the draft.
- Rewire .graph-repair-input input listener to DOM-local enable/disable
  only (no state dispatch per keystroke) to preserve caret position on
  textarea re-render. Reveal-enable predicate requires BOTH a valid
  pre-confidence (from state) AND non-empty trimmed textarea.
- .trigger-repair-reveal click reads live textarea value and hands
  off to window.SocratinkApp.revealRepairRep(). The function itself
  gates on idempotency + answer + pre-confidence, so bypass via direct
  JS call (without pill + answer) is a no-op.
- Bump graph-view.js?v=4 -> v=5 in both importers; app.js?v=29 -> v=30.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: layout.css — pill + calibration styles with Wave 1 tokens

**Files:**
- Modify: `public/css/layout.css` (append new rules near existing `.graph-repair-*` block; if no such block exists, append at end of file)
- Modify: `public/index.html:25` (bump styles.css?v=42 -> v=43)

### Step 4.1 — Locate existing `.graph-repair-*` rules (to know insertion point)

- [ ] **Grep for existing rules**

```bash
grep -n "graph-repair-" public/css/layout.css | head -20
```

Insert the new block **after** the last existing `.graph-repair-*` rule in `layout.css`. If none exist in this file, append at the end of file (before any trailing `}` closing a media query).

### Step 4.2 — Append the new CSS rules

- [ ] **Edit `public/css/layout.css`** — append the following block

```css
/* ── Repair Reps Slice B — pre-reveal pill + calibration summary ── */

.graph-repair-predict {
  margin-bottom: 18px;
}

.graph-repair-predict > .graph-detail-kicker {
  margin-bottom: 8px;
}

.graph-repair-predict-group {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.graph-repair-predict-pill {
  padding: 6px 12px;
  border-radius: var(--radius-pill);
  font-size: 12px;
  font-weight: 500;
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  color: var(--text-strong);
  cursor: pointer;
  font-family: inherit;
  transition: background var(--duration-micro) var(--ease-standard, ease),
              border-color var(--duration-micro) var(--ease-standard, ease);
}

.graph-repair-predict-pill:hover {
  border-color: var(--accent-border-strong);
}

.graph-repair-predict-pill.is-selected,
.graph-repair-predict-pill[aria-checked="true"] {
  background: var(--accent-soft);
  border-color: var(--accent-border-strong);
  color: var(--accent-primary);
  font-weight: 600;
}

.graph-repair-predict-group.is-locked,
.graph-repair-predict-group[aria-disabled="true"] {
  pointer-events: none;
}

.graph-repair-predict-group.is-locked .graph-repair-predict-pill,
.graph-repair-predict-group[aria-disabled="true"] .graph-repair-predict-pill {
  cursor: default;
}

.graph-repair-reveal-helper {
  font-size: 11px;
  color: var(--text-muted);
  margin: 6px 0 0;
}

.graph-repair-calibration .graph-repair-summary-row {
  display: grid;
  grid-template-columns: max-content 1fr 1fr;
  gap: 10px 16px;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-subtle);
  font-size: 12px;
}

.graph-repair-calibration .graph-repair-summary-row:last-child {
  border-bottom: none;
}

.graph-repair-summary-rep {
  font-weight: 700;
  color: var(--text-muted);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 1.2px;
}

.graph-repair-summary-pair .muted {
  color: var(--text-muted);
}

@media (prefers-reduced-motion: reduce) {
  .graph-repair-predict-pill {
    transition: none;
  }
}
```

Note: `--ease-standard` has a fallback of plain `ease` so missing tokens degrade gracefully. The global reduced-motion block in `base.css` already suppresses transitions; the explicit rule here is a belt-and-suspenders per spec and is harmless.

### Step 4.3 — Bump styles.css cache-bust

- [ ] **Edit `public/index.html:25`**

Find:
```html
  <link rel="stylesheet" href="styles.css?v=42">
```

Replace with:
```html
  <link rel="stylesheet" href="styles.css?v=43">
```

### Step 4.4 — Commit

- [ ] **Stage and commit**

```bash
git add public/css/layout.css public/index.html
git commit -m "$(cat <<'EOF'
feat(repair-reps): Slice B CSS — predict pills + calibration rows

- Add .graph-repair-predict / .graph-repair-predict-group /
  .graph-repair-predict-pill rules. Pills render as Wave 1 chips:
  --surface-card + --border-subtle; selected = --accent-soft +
  --accent-primary + stronger border.
- Lock state via .is-locked and [aria-disabled="true"] sets
  pointer-events: none on the group and cursor: default on children.
- Add .graph-repair-reveal-helper for the "Pick a stance..." helper.
- Add .graph-repair-calibration row grid (max-content 1fr 1fr) with
  subtle dividers; .graph-repair-summary-rep small-caps label; .muted
  inline tag for Predicted/Rated prefixes.
- Respect prefers-reduced-motion: reduce on pill transitions (global
  base.css already handles this, but spec calls it out explicitly).
- Bump styles.css?v=42 -> v=43.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: app.js recordRepairRepsCompletion — persist the two new arrays + invariant comment

**Files:**
- Modify: `public/js/app.js:2439-2456` (recordRepairRepsCompletion)
- Modify: `public/index.html:495` (bump app.js?v=30 -> v=31)

### Step 5.1 — Extend `recordRepairRepsCompletion`

- [ ] **Replace the function (lines 2439-2456)**

```js
  function recordRepairRepsCompletion({
    conceptId, nodeId, repCount, promptVersion, gapType,
    answerLengths, ratings, preConfidences, lockDurationsMs,
  }) {
    if (!conceptId || !nodeId) return;
    const history = loadRepairRepsHistory();
    const key = `${conceptId}::${nodeId}`;
    const entries = Array.isArray(history[key]) ? history[key] : [];
    // pre_confidences and lock_durations_ms are practice metadata — a
    // calibration read-out for the learner. They MUST NOT feed scheduling,
    // node prioritization, drill_status, or any graph-truth mutation.
    // See spec §Invariant Boundary.
    history[key] = [
      ...entries,
      {
        completed_at: new Date().toISOString(),
        rep_count: repCount,
        prompt_version: promptVersion,
        gap_type: gapType || null,
        answer_lengths: Array.isArray(answerLengths) ? answerLengths : [],
        ratings: Array.isArray(ratings) ? ratings : [],
        pre_confidences: Array.isArray(preConfidences) ? preConfidences : [],
        lock_durations_ms: Array.isArray(lockDurationsMs) ? lockDurationsMs : [],
      },
    ].slice(-20);
    saveRepairRepsHistory(history);
  }
```

Task 1 Step 1.7 already forwards `preConfidences` and `lockDurationsMs` into this function from `nextRepairRep`. No other call sites need updating.

### Step 5.2 — Bump app.js cache-bust

- [ ] **Edit `public/index.html:495`**

`js/app.js?v=30` → `js/app.js?v=31`

### Step 5.3 — Node syntax check

- [ ] **Run**

```bash
node --check public/js/app.js
```

Expected: silent.

### Step 5.4 — Commit

- [ ] **Stage and commit**

```bash
git add public/js/app.js public/index.html
git commit -m "$(cat <<'EOF'
feat(repair-reps): Slice B persist pre_confidences + lock_durations_ms

Extend recordRepairRepsCompletion to accept preConfidences and
lockDurationsMs named params and persist them as additive arrays
on each learnops_repair_reps_v1 record. Missing arrays from older
records read as []; no migration needed.

Add inline invariant comment: these fields are practice metadata
only, must not feed scheduling or graph-truth mutation (spec
Invariant Boundary).

Bump js/app.js?v=30 -> v=31.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Automated verification + manual browser flow

**Files:** none modified.

### Step 6.1 — Automated checks

- [ ] **Node syntax on both JS files**

```bash
node --check public/js/app.js && node --check public/js/graph-view.js
```

Expected: silent (both pass).

- [ ] **Repair Reps unit + prompt tests (unchanged surface — must stay green)**

```bash
python -m pytest tests/test_repair_reps.py tests/test_app_prompts.py -v
```

Expected: all pass. Slice B touches no backend code; any failure here is a regression unrelated to Slice B and must be investigated before proceeding.

- [ ] **Full test discovery (call out pre-existing failures if telemetry tests flake — document but do not treat as new regression)**

```bash
python -m unittest discover -s tests -v 2>&1 | tail -40
```

Expected: no NEW failures. Pre-existing flakes (if any) are documented in `docs/project/state.md` — compare before blocking.

- [ ] **Whitespace / trailing-space check**

```bash
git diff --check origin/dev...HEAD
```

Expected: silent (no whitespace errors).

### Step 6.2 — Serve and cache-verify

- [ ] **Kill any existing uvicorn on :8000 and restart from this worktree**

```bash
pkill -f "uvicorn main:app" || true
sleep 1
uvicorn main:app --reload
```

(Run in a separate terminal pane, or as `&` in background.)

- [ ] **Cache-bust & feature-landing curl checks**

```bash
curl -s http://localhost:8000/ | grep -oE 'styles\.css\?v=[0-9]+'
curl -s http://localhost:8000/ | grep -oE 'js/app\.js\?v=[0-9]+'
curl -s "http://localhost:8000/js/app.js?v=31" | grep -c 'setRepairRepPreConfidence'
curl -s "http://localhost:8000/js/app.js?v=31" | grep -c 'setRepairRepDraft'
curl -s "http://localhost:8000/js/graph-view.js?v=5" | grep -c 'trigger-repair-predict'
```

Expected:
- `styles.css?v=43`
- `js/app.js?v=31`
- `setRepairRepPreConfidence` count > 0 (should be ≥2: definition + export)
- `setRepairRepDraft` count > 0
- `trigger-repair-predict` count > 0 (markup + class)

If any of these is wrong, investigate cache-bust mismatch before running manual tests.

### Step 6.3 — Manual browser verification (20-item spec test plan)

Open `http://localhost:8000/` in a browser on a fresh profile (or hard-reload). Create or open a concept where at least one node is eligible for Repair Reps (post-study, non-solid). Click `Start Repair Reps`.

Walk through each item. Tick the box only after observation (not assumption).

- [ ] **1. Pill renders**: "Before you peek" kicker + three pills render above "Your bridge". Reveal button disabled. Helper text reads "Pick a stance and type your bridge to continue."
- [ ] **2. Type without pill**: helper remains visible, reveal button stays disabled.
- [ ] **3. Pill no-type**: select `Have a hunch`; pill highlights with `aria-checked="true"` (inspect element to confirm); textarea empty; reveal stays disabled.
- [ ] **4. Type-then-pill draft preservation**: type `test draft`, THEN select `Guessing`. Textarea still reads `test draft` after the re-render. (This is the draft-preservation test — the reason for Step 1.6b's `setRepairRepDraft`.)
- [ ] **5. Both satisfied**: pill + non-empty trimmed attempt → reveal button enables.
- [ ] **6. Clear textarea**: clear after enabling → reveal re-disables, pill selection persists.
- [ ] **7. Change pill pre-reveal**: click a different pill → highlight moves; reveal stays enabled.
- [ ] **8. Single-click reveal**: click `Lock in and show reference bridge`. Textarea becomes `readonly` (inspect); pill row gains `aria-disabled="true"` and `.is-locked` class (inspect); reference bridge unfolds; self-rating row renders with `Close match / Partly linked / Missed the link`.
- [ ] **9. Post-reveal pill click**: click pills after reveal → nothing happens (CSS `pointer-events: none`).
- [ ] **10. Direct JS bypass**: in DevTools console, run before selecting a pill on a fresh rep: `window.SocratinkApp.revealRepairRep("x")` — no reveal. Then select a pill, type, and run it again — reveal happens.
- [ ] **11. Idempotency**: after reveal, run `window.SocratinkApp.revealRepairRep("anything")` a second time. Inspect `window.SocratinkApp.getRepairRepsState()`: `lockedAt`, `preConfidences`, and `lockDurationsMs` are each written exactly once for this rep (lengths should match `currentIndex + 1`).
- [ ] **12. Lock duration**: `getRepairRepsState()` shows `lockedAt - repStartedAt > 0`. After `nextRepairRep()`, `repStartedAt` has a new value, `lockedAt` is null.
- [ ] **13. Complete 3 reps**: walk through reps 2 and 3 with different `Predicted → Rated` combinations (aim for at least one of each pill value).
- [ ] **14. Completion summary**: three rows `Rep N / Predicted: <label> / Rated: <label>` with the fixed label map. Observational language only — no "overconfident", "miscalibrated", or "wrong". Closing copy "These reps are saved. Graph progress comes from the next re-drill." visible.
- [ ] **15. localStorage record**: run `JSON.parse(localStorage.learnops_repair_reps_v1)` in DevTools. The latest record for the concept has `pre_confidences.length === 3`, `lock_durations_ms.length === 3` (all positive integers), alongside existing `ratings` and `answer_lengths`. No `answer`, `prompt`, `target_bridge`, or `feedback_cue` fields.
- [ ] **16. Old-record backward compat**: inject a pre-slice-B record into localStorage:

    ```js
    const k = 'learnops_repair_reps_v1';
    const h = JSON.parse(localStorage.getItem(k) || '{}');
    h['fake-concept::fake-node'] = [{
      completed_at: new Date().toISOString(), rep_count: 3,
      prompt_version: 'repair-reps-system-v1', gap_type: 'mechanism',
      answer_lengths: [10, 20, 30], ratings: ['close_match', 'partial', 'missed'],
    }];
    localStorage.setItem(k, JSON.stringify(h));
    ```

    Reload. No crash on any surface that reads this store. (App doesn't currently re-render history from this store, so the check is: page loads and Repair Reps still works on real nodes.)

- [ ] **17. Length-mismatch injection**: inject a record with `pre_confidences.length === 2` and `ratings.length === 3` (paste one manually into localStorage). No code surface currently re-renders this back, but simulate by temporarily overriding a state object in DevTools and forcing a render. Or simpler: complete a 3-rep run, then in DevTools directly call `repairCalibrationSummaryMarkup(['guessing','hunch'], ['close_match','partial','missed'])` after importing it (or observe via unit inspection of the render). **If the helper isn't trivially callable from DevTools** (it's not exported globally), verify by reading the source: Task 2 Step 2.1 uses `Math.min(preList.length, rateList.length)` — ≤ min rows. Check passes by inspection.
- [ ] **18. Exit**: `Back to graph` releases focused mode and returns to the graph view.
- [ ] **19. Reduced motion**: toggle OS `prefers-reduced-motion: reduce` (macOS: System Preferences → Accessibility → Display → Reduce motion). Reload. Pill transitions suppressed.
- [ ] **20. A11y**: Tab key cycles into the pill group. Space/Enter activates the focused pill. Selected pill has `aria-checked="true"`. Disabled reveal button has `aria-describedby="repair-reveal-helper"` pointing at the helper paragraph.

### Step 6.4 — If any manual check fails

Do not fix silently. Log the failure + reproduction in a scratch note, triage whether it is spec-correct-but-impl-wrong (fix and re-verify that step + all subsequent) or impl-correct-but-spec-ambiguous (surface to the user before deciding).

### Step 6.5 — Verification tail commit (optional, only if final tweaks needed)

If a manual check revealed a small fix (e.g., missing `aria-describedby`, off-by-one in label), land it as a single commit with message `fix(repair-reps): <specific fix>` and re-run only the affected manual checks.

---

## Final verification

- [ ] **Full test run (last check before PR)**

```bash
node --check public/js/app.js && node --check public/js/graph-view.js
python -m pytest tests/test_repair_reps.py tests/test_app_prompts.py -v
git diff --check origin/dev...HEAD
git log --oneline origin/dev..HEAD
```

Expected: all pass; commit graph shows 5-6 focused commits (plan + Task 1-5, optional Task 6 fix).

- [ ] **Confirm zero-touch invariants via grep**

```bash
# Must NOT appear in any Slice B diff:
git diff origin/dev...HEAD -- public/js/app.js public/js/graph-view.js \
  | grep -E 'patchActiveConceptDrillOutcome|recordInterleavingEvent|markNodeVisitedThisSession|drill_status\s*[:=]|drill_phase\s*[:=]|study_completed_at\s*[:=]|re_drill_eligible_after\s*[:=]' \
  | grep -v '^-'
```

Expected: empty (no NEW lines touching those identifiers). Any match is an invariant violation.

- [ ] **Confirm no backend / prompt drift**

```bash
git diff origin/dev...HEAD -- main.py ai_service.py app_prompts/
```

Expected: empty.

---

## PR checklist

- [ ] Branch: `claude/repair-reps-slice-b`, target `dev`.
- [ ] PR body references `docs/superpowers/specs/2026-04-18-repair-reps-slice-b-metacognitive-loop-design.md`.
- [ ] Test-plan items 1-20 checked (mark the three that only a human can run: **#10 direct-JS bypass**, **#11 idempotency**, **#17 length-mismatch** — note human-verified).
- [ ] Zero backend diff.
- [ ] Cache-bust values at final commit: `styles.css?v=43`, `app.js?v=31`, `graph-view.js?v=5` (both importers).
