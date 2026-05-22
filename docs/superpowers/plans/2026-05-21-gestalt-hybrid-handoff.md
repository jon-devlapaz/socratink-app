# Handoff: Gestalt Overview → Route Margin Hybrid Concept Page

**Date:** 2026-05-21
**Session:** Antigravity design exploration & UX research session
**Branch:** `dev` (implementation target)
**Worktree:** `codex/concept-gestalt-overview` (reference only — do NOT merge or rebase)

---

## 1. What We Decided

The `codex/concept-gestalt-overview` worktree branch built a **1-column cover/work surface** ("Gestalt Overview") that appears when a learner first opens a source-less concept with no recorded attempt on the active entry. The `dev` HEAD has a **2-column Route Margin Canvas** with a Constellation graph toggle — the active study/repair workspace.

After visual comparison, persona simulation, and pedagogical UX research, **the founder approved a hybrid view progression** that uses both layouts as render modes over the existing learning loop.

This is UX language only. The canonical product loop remains:
`Cold attempt -> Targeted study -> Spaced re-drill`.

Do not implement `GUESS`, `COMPARE`, or `EXPANDED WORKSPACE` as a persisted learning phase or a separate state machine. The frontend should project these views from the existing training record and derived per-entry `next_action`.

### Expanding Concept Surface (Approved)

```
Stage 1: GUESS (source-less concept, active entry has no recorded attempt)
  → Render Gestalt Overview as a 1-column cover/work surface
  → The active cold-attempt writing surface is visible immediately
  → Learner writes their first cold draft
  → Submit stays on the 1-column page (no jarring layout shift)

Stage 2: COMPARE (training derivation routes active entry to study/repair/review, still on the same cover/work surface)
  → Show the draft alongside a study note comparison
  → Keep the learner on the same concept surface
  → `Keep working` may expand the route margin from this same surface, but no separate "Enter Concept Board" destination is required

Stage 3: EXPANDED WORKSPACE (ongoing concept work after comparison is acknowledged)
  → The same concept surface expands into the 2-column Route Margin Canvas
  → Left: Route Margin checklist / Constellation toggle
  → Right: Active entry study/repair loops
  → This is the workspace state for all subsequent sessions
```

### Key Design Constraints (from persona + research)

1. **No separate destination after comparison.** When the learner submits their first draft, do NOT immediately flash to the 2-column layout and do NOT require an "Enter Concept Board" navigation step. The board is an expansion of the same concept surface after explicit comparison acknowledgement, not a second app the learner enters.
2. **The cover is evidence-derived, not arrival-derived.** Use the training record for the active entry to determine whether a cold attempt exists. Do NOT use a one-time first-arrival flag. Resetting progress should naturally restore the cover sheet because the attempt evidence is gone.
3. **No new overview schema unless proven necessary.** The minimum remarkable loop should derive the cover from existing concept data, `Starting sketch`, training provenance, `deriveConceptEntries()`, and `learner_scaffold`. Do not add `learner_overview` or a compatibility adapter unless a required cover element cannot be derived truthfully from the existing projection.
4. **The cover/work surface must NOT look like a loading screen, progress bar, or passive overview.** Keep the route dot-track clean, quiet, manual, and secondary to the active cold-attempt writing task.
5. **Expanded workspace is post-compare, not merely post-attempt.** Restore the expanded workspace only when the selected entry has a real recorded attempt, explicit `study_revealed_at`, and the immediate comparison is no longer the active render target. An unrevealed saved draft restores the one-column saved-draft study gate.
6. **Pre-attempt visibility is source-locked.** Before the first Cold attempt, every visible string must come from an allowed source. Do not let fallback chains leak AI-generated answer structure into the cover.

---

## 2. What Exists Today (Starting State)

### On `dev` HEAD (the implementation target)

- **2-column layout** in `renderActiveEntryHtml()` → wraps output in `.concept-page-b2__gestalt` with `grid-template-columns: minmax(150px, 220px) minmax(0, 1fr)`.
- **Route Margin sidebar** rendered by `renderRouteMarginHtml()` in `concept-page-view.js`.
- **Constellation graph toggle** in `concept-constellation-view.js`, wired via `#concept-view-switch` in `app.js`.
- **`renderConceptPageB2()`** in `app.js` (line ~2356) is the top-level mount function. It calls `renderActiveEntryHtml()` and sets `mountEl.innerHTML`.
- **No `renderConceptOverviewHtml`** exists on `dev`.
- **No `learner_overview` fields** exist in `models/provisional_map.py` on `dev`, and this should remain true unless the minimum remarkable loop proves it needs a new projection contract.

### On `codex/concept-gestalt-overview` worktree (reference only)

- **`renderConceptOverviewHtml()`** exists at lines 221–373 of `public/js/concept-page-view.js`. This is the 1-column cover/work renderer shape.
- **No `LearnerOverview` Pydantic model exists.** Treat any handoff claim that it does as drift. The useful worktree artifact is the one-column renderer shape, not a portable overview schema.
- **Prompt updates** in `app_prompts/generate-smallest-route-system-v1.txt` are not directly portable for overview fields. Current `dev` already uses `learner_scaffold` for non-answer route/task copy.
- **Tests** exist for model, renderer, and browser interaction.
- **The worktree diverged from `8c86b21`** (6 commits behind `dev`). It does NOT have the Constellation, Route Margin Canvas, or local guest auth fixes. Do not merge or rebase — cherry-pick the design intent manually.

### Key Files to Touch

| File | Action |
|:-----|:-------|
| `public/js/concept-page-view.js` | Port the useful 1-column renderer shape from worktree, adapt it into a cover/work surface that can show attempt and comparison without a separate board handoff |
| `public/js/app.js` | Add conditional render path in `renderConceptPageB2()` for cover/work vs expanded route-margin modes |
| `public/css/concept-page.css` | Add `.concept-page-b2__overview*` styles from worktree |
| `models/provisional_map.py` | Avoid changes unless an absolutely needed cover element cannot be derived from existing `LearnerScaffold` |
| `app_prompts/generate-smallest-route-system-v1.txt` | Avoid changes unless the current scaffold contract cannot produce the required minimum loop copy |
| `public/styles.css` + `public/css/index.css` + `public/index.html` | Cache-bust version bumps |
| `tests/test_extract_route_smallest.py` | Model + prompt contract tests |
| `tests/test_frontend_app_helper_modules.py` | Pure renderer tests |
| `tests/e2e/test_app_helper_modules.py` | Browser helper renderer tests |
| `tests/e2e/test_strip_nav.py` | Browser interaction tests for overview → entry routing |

---

## 3. Implementation Approach

### 3a. Backend: No New Projection Unless Forced

Do not add `LearnerOverview`, `LearnerRouteLabel`, or `metadata.learner_overview` as part of the first implementation pass.

The minimum remarkable loop should use the existing source-less route projection:
- `concept.name`
- `concept.startingMapContext` / `metadata.starting_map_context` as **Starting sketch**
- `training.source_mode === "source_less"` for provenance
- `deriveConceptEntries(data)` for route entries
- `entry.learner_scaffold` for non-answer learner-facing task copy

Only add a backend schema field if a required cover element cannot be derived from those existing sources without lying, leaking answer content, or duplicating a second route contract.

### 3b. Frontend: Conditional Rendering in `renderConceptPageB2()`

The core logic change is in `renderConceptPageB2()` in `app.js`:

```javascript
function renderConceptPageB2(mountEl, data, concept, training, options) {
  const backbone = deriveConceptEntries(data);
  const active = selectInitialConceptEntry(backbone, training);
  const activeRecord = training?.node_records?.[active.id] || null;
  const activeAttempts = Array.isArray(activeRecord?.attempts) ? activeRecord.attempts : [];
  const activeHasRealAttempt = activeAttempts.length > 0;
  const studyRevealed = Boolean(activeRecord?.study_revealed_at);
  const justRevealed = options?.justRevealedEntryId === active.id;
  const firstAttempt = activeAttempts[0] || null;
  const hasPreStudyColdAttempt = Boolean(firstAttempt && (
    !studyRevealed || firstAttempt.at <= activeRecord.study_revealed_at
  ));
  const comparisonAcknowledged = !hasPreStudyColdAttempt || hasComparisonAcknowledgement(concept.id, active.id);

  if (training?.source_mode === 'source_less' && !activeHasRealAttempt && !studyRevealed) {
    renderColdAttemptSurface(mountEl, data, concept, active, training);
    return;
  }

  if (training?.source_mode === 'source_less' && !activeHasRealAttempt && studyRevealed) {
    renderLegacyRevealedWorkspace(mountEl, data, concept, active, training);
    return;
  }

  if (training?.source_mode === 'source_less' && activeHasRealAttempt && !studyRevealed) {
    renderSavedDraftStudyGate(mountEl, data, concept, active, training);
    return;
  }

  if (training?.source_mode === 'source_less' && activeHasRealAttempt && studyRevealed && (justRevealed || !comparisonAcknowledged)) {
    renderPostRevealComparison(mountEl, data, concept, active, training);
    return;
  }

  // Expanded Route Margin Canvas (existing behavior)
  // ... existing renderActiveEntryHtml path ...
}
```

Do not use a global `hasAnyTrainingAttempt(training)` gate. That would skip the same-surface compare beat as soon as the first attempt is persisted. The cover/work decision must be based on the active entry's training record and its derived next action.

The exact predicate for a real recorded attempt is:

```javascript
Array.isArray(record?.attempts) && record.attempts.length > 0
```

Legacy compatibility records with `attempts: []` do not count as real reconstruction evidence for this loop. If such a record already has `study_revealed_at`, do not send the learner back to a Cold attempt; the study boundary has already been crossed. Render a compatibility workspace that preserves the existing study surface without claiming route progress, mastery, or attempt evidence.

The immediate post-reveal comparison is only required for a genuine pre-study Cold attempt. If a legacy record already had `study_revealed_at` before its first attempt was appended, that later attempt must not be treated as the missing cold attempt that forces the comparison gate. Use the existing `attempt.at` and `study_revealed_at` timestamps to distinguish pre-study cold attempts from post-study legacy attempts.

`study_revealed_at` is training evidence that the learner opened study. It is not the same thing as acknowledging the comparison screen. Use a render-only discriminator such as `options.justRevealedEntryId` so the immediate `Reveal notes and compare` action lands on post-reveal comparison instead of falling through to the expanded workspace.

The comparison acknowledgement is UI state only, but it must survive reload/back navigation in the current browser. Store it outside the training record, keyed by concept id + entry id, for example `localStorage["socratink:comparison_ack:<conceptId>:<entryId>"]`. Clear or invalidate that key only when the entry's training record resets or the initial cold attempt is deleted/reset. Do not invalidate it when later repairs or spaced re-drills add attempts. This state never mutates graph truth and never counts as learner evidence.

The expanded renderer must either preserve the DOM contracts used by existing handlers (`.concept-page-b2__doc`, `.concept-page-b2__route`, `.concept-page-b2__route-item`) or adapt `setActiveEntry()` / route binding explicitly. Quiet pre-attempt or comparison markers are different: they must not use `.concept-page-b2__route-item`, `data-entry-id`, or any selector/attribute that the delegated route handler treats as navigation. Do not mount a standalone overview that silently breaks the existing active-entry handlers.

### 3c. Locked Pre-Attempt Visibility Rule

Before the learner submits the first Cold attempt, render only:
- concept name
- learner-authored **Launch attempt** labeled "Your starting sketch"
- source-less provenance
- one active `learner_scaffold.entry_prompt`
- the writing box/action
- at most 4 quiet route markers

Quiet route markers may use only:
- `learner_scaffold.task_label`
- `learner_scaffold.learner_move`

Before the first Cold attempt, do not render:
- `cluster.description`
- `subnode.mechanism`
- `metadata.core_thesis`
- relationship mechanisms
- prerequisite rationales
- study notes
- gap predictions
- route status text
- bridge/connective copy such as "because", "then", or "leads to"
- the current nearby-entries list

If a source-less route entry lacks `learner_scaffold`, suppress marker text rather than falling back to generated concept structure. Never label `metadata.core_thesis` or any AI-generated field as "Your starting sketch."

Before the first Cold attempt exists for the active source-less concept entry, quiet route markers are visual only. Do not render them as buttons, links, tabbable controls, or `data-entry-id` navigation targets, and do not bind them to `setActiveEntry()`. Their only pre-attempt job is to hint that a short route exists using `learner_scaffold.task_label` or `learner_scaffold.learner_move`.

Route controls and the 2-column Route Margin Canvas are post-compare affordances, not merely post-attempt affordances. After the attempt is saved but before explicit study reveal, the learner remains in the one-column saved-draft study gate; route previews and route navigation must not let them skip reveal.

Once study is explicitly revealed for that entry, render the immediate post-reveal comparison first. The layout may expand into the Route Margin Canvas only after the learner clicks `Keep working`, or later returns to an entry that already has a real recorded attempt, `study_revealed_at`, and persistent UI-only comparison acknowledgement. An unrevealed saved draft restores the one-column saved-draft study gate.

Legacy `primed`/`study` records with `attempts: []` preserve compatibility only and must not count as evidence for route-control unlock. They also must not be routed to the Cold attempt surface if `study_revealed_at` already exists, because the learner is no longer truly pre-study.

### 3d. Stage 2 Compare and Expansion

After the learner submits their first draft in Stage 1:
1. Re-render the same concept surface in the **saved-draft study gate** with the draft visible and route previews hidden.
2. Preserve the current explicit study-reveal boundary: show a clear action such as `Reveal notes and compare`; do not automatically reveal study content immediately after the cold attempt.
3. After explicit reveal, show the study note/comparison on the same concept surface.
4. Keep the learner in context; do not introduce a separate "Enter Concept Board" destination.
5. Keep route markers inert through the immediate post-reveal comparison.
6. Expand route-margin affordances from the same surface only when the learner clicks `Keep working`, or when the learner later returns with recorded attempt evidence, `study_revealed_at`, and persistent UI-only comparison acknowledgement.

No session-level learning flag is needed. A persistent UI-only comparison acknowledgment is allowed only to preserve render continuity across reload/back navigation; it is not learning evidence. If the relevant training evidence exists and the comparison is no longer the immediate render target, returning to the concept restores the expanded route-margin workspace. If training evidence is reset, the cover/work surface naturally returns and the UI-only acknowledgment must be cleared or ignored.

The saved-draft study gate uses the C prototype verdict from `public/_lab/saved-draft-study-gate.html?v=C` / `public/_lab/saved-draft-study-gate-c.html`: show concept title, source-less provenance, learner-authored Starting sketch, the learner's exact draft, neutral bridge copy, and `Reveal notes and compare`. Hide route silhouettes, dormant route margins, route statuses, future prompt labels, study content, repair UI, gap/correction language, scores, tiers, bands, and classifier labels.

Preferred saved-draft bridge copy:
`Draft recorded. Having your own words fresh in mind makes it easier to notice the differences when you read the notes.`

After explicit `Reveal notes and compare`, render an immediate post-reveal comparison state before the full Route Margin Canvas takes over. This is a transient render mode over the existing training record, not a persisted phase.

The post-reveal comparison state must show:
- the learner's exact latest draft for the attempted entry
- the targeted study note for that same entry only
- neutral compare framing that asks the learner to notice differences, not judge ability
- recorded **Missing piece** details only when the latest attempt for that entry contains gaps

The post-reveal comparison state must not show:
- scores, tiers, bands, raw classifier labels, or ability labels
- concept-level route/composition status
- future-node study notes or future-node mechanism content
- a "no missing piece" verdict when no gaps are recorded
- mastery, completion, or graph-truth claims caused by reading

Repair UI may appear in this state only when the derived entry `next_action` is `repair` after `study_revealed_at`. Missing-piece comparison is not itself a repair composer.

Route affordances do not dismiss the immediate post-reveal comparison. If route markers are visible during comparison, they remain subordinate and inert. Full Route Margin Canvas expansion happens only when the learner clicks `Keep working`, or later returns to an entry with a real recorded attempt, `study_revealed_at`, and persistent UI-only comparison acknowledgement.

The learner leaves the immediate post-reveal comparison through one low-drama action: `Keep working`.

`Keep working` expands the same concept surface into the Route Margin Canvas. It is not a navigation gate, not a new destination, and not evidence of completion, mastery, progress, or route success.

During the immediate post-reveal comparison state, route markers may be visible only as subordinate, noninteractive orientation. Do not render them as buttons, links, tabbable controls, or `data-entry-id` navigation targets in this state. Clicking a route marker must not be an alternate way to dismiss the comparison.

After `Keep working`, the Route Margin Canvas may render normal route controls. Only traversal-allowed entries may be interactive; locked/future entries remain inert. The expanded workspace continues to derive all copy and actions from the training record and per-entry `next_action`.

If the active entry derives `next_action === "repair"` after `study_revealed_at`, the post-reveal comparison must keep repair clearly available and strategy-framed. `Keep working` may expand the workspace, but it must not hide or demote the repair obligation behind generic navigation.

Forbidden copy: `Enter Concept Board`, `Continue the route`, `Complete`, `Done`, `Mastered`, `Progress made`, or any label implying that reading the study note changed graph truth.

### 3e. Seam Contracts

| Seam | Trigger | Required evidence | Allowed UI | Forbidden UI / claims | Mutation | Verification |
|:--|:--|:--|:--|:--|:--|:--|
| Load -> Cold attempt surface | Source-less concept opens on active entry | `source_mode === "source_less"`; active record has zero real attempts and no `study_revealed_at` | concept name, learner Launch attempt as Starting sketch, provenance, one scaffold prompt, textarea, inert markers | `core_thesis`, mechanisms, study notes, statuses, nearby entries, clickable markers | none | no marker is tabbable/clickable; no `core_thesis` visible as sketch |
| Cold submit -> Saved-draft gate | recordable drill result from inline attempt | latest real attempt persisted with exact `user_text`; no `study_revealed_at` | exact draft, neutral bridge, `Reveal notes and compare` | gaps, note, score/tier/band, route/status chrome, repair UI | append attempt only | reload restores saved gate, not workspace |
| Saved gate -> Post-reveal comparison | learner clicks `Reveal notes and compare` | real attempt exists; `study_revealed_at` written | exact draft, same-entry study note, neutral compare copy, gaps only if present | "no missing piece", scores, future notes, route clicks, completion/progress | persist `study_revealed_at`; pass render-only `justRevealedEntryId` | immediate screen is comparison, not route canvas |
| Comparison -> Expanded workspace | learner clicks `Keep working` | real attempt + `study_revealed_at`; comparison acknowledged in persistent UI-only state | Route Margin Canvas, traversal-gated route controls, repair primary if `next_action === "repair"` | route marker as alternate exit, `Continue the route`, mastery/progress copy | no training mutation; write/invalidate UI-only acknowledgement | before click markers inert; after click allowed controls work; reload/back restores workspace |
| Legacy revealed/no-attempt -> Compatibility workspace | legacy source-less record has `study_revealed_at` but zero attempts | study boundary already crossed; no real attempt evidence | existing study surface without cold-attempt framing | cold attempt claim, route progress, mastery, route unlock from study alone | none | does not ask for a "cold" attempt after study reveal |
| Expanded -> Repair / re-drill | save repair or later reconstruction | repair requires `study_revealed_at`; re-drill derives from spacing/evidence | repair composer, study reference, later spaced attempt | `solidified` from study/repair, scores during active work | append repair or spaced attempt | only spaced strong reconstruction can derive `solidified` |

### 3f. Prototype and Goal Workflow

Before production edits, use `/prototype` with the UI branch:
- Build one throwaway full-flow lab route under `public/_lab/`.
- Keep the question narrow: "Does the full state chain preserve the minimum remarkable loop without dashboard creep?"
- Simulate the full chain: `Cold attempt -> saved-draft study gate -> Reveal notes and compare -> immediate comparison -> Keep working -> Route Margin Canvas`.
- Include both branches: a no-gap attempt with no "no missing piece" verdict, and a gap/repair attempt where **Missing piece** is visible and repair remains clearly available.
- Verify route markers are inert until `Keep working`, and that `Keep working` is the only comparison-exit action.
- Capture the verdict in a sibling `*.NOTES.md` before deleting or absorbing the prototype.

When ready to implement, use `/codebaseGoalPlanner` to produce one reviewable `/goal` prompt for the bounded production slice. Do not let it expand the product scope; constrain it to the files and validation in this handoff.

### 3g. Compatibility

No `learner_overview` compatibility adapter is needed if no new overview schema is added.

Legacy compatibility should remain at the existing UI boundary: missing scaffold or route copy falls back to safe generic labels (`First entry`, `Draft what you can recall`, etc.) without showing raw schema names or answer content.

### 3h. CSS

Port the `.concept-page-b2__overview*` styles from the worktree's `public/css/concept-page.css`. The worktree has comprehensive dark mode support. Follow cache-bust discipline (bump all three version pins).

---

## 4. What NOT to Do

- **Do NOT merge or rebase `codex/concept-gestalt-overview` onto `dev`.** The branches diverged 6 commits ago. Manual, scope-locked edits on `dev` are the path.
- **Do NOT add `learner_overview` fields unless proven absolutely necessary.** The default answer is no new schema.
- **Do NOT render raw schema names** (`ProvisionalMap`, `core_thesis`, `cluster`, `subnode`) to learners.
- **Do NOT render `metadata.core_thesis` or any AI-generated field as "Your starting sketch."** The sketch label is reserved for learner-authored Launch attempt text.
- **Do NOT use fallback labels for pre-attempt route markers.** If `learner_scaffold.task_label` / `learner_scaffold.learner_move` are missing, suppress marker text before the first attempt.
- **Do NOT make pre-attempt route markers interactive.** Before the first Cold attempt, route markers are not buttons, links, tabbable controls, `data-entry-id` navigation targets, or `setActiveEntry()` triggers.
- **Do NOT show route previews during the saved-draft study gate.** After attempt save and before explicit reveal, keep the learner's draft as the object of attention.
- **Do NOT skip the post-reveal comparison state.** Recording `study_revealed_at` must not immediately dump the learner into the full Route Margin Canvas.
- **Do NOT render "no missing piece" as a verdict.** Absence of recorded gaps is not a mastery, correctness, or graph-truth claim.
- **Do NOT let route marker clicks dismiss post-reveal comparison.** The only comparison-exit action is `Keep working`.
- **Do NOT use progress/completion copy for the comparison exit.** `Keep working` is allowed; `Continue the route`, `Complete`, `Done`, `Mastered`, and `Progress made` are not.
- **Do NOT create a separate active-entry state variable.** Expanded route controls must reuse the existing `setActiveEntry()` path. Quiet pre-attempt/comparison markers are not route controls and must not use the route-item class, `data-entry-id`, or delegated route selectors.
- **Do NOT use `extra="forbid"` on the Pydantic models.** This repo intentionally avoids that for Gemini-bound schemas.
- **Do NOT skip the Stage 2 "compare" beat.** The persona research specifically flagged that an instant layout swap from cover/work surface → double-column is jarring.
- **Do NOT add an "Enter Concept Board" gate.** Later critique flagged this as dashboard creep and a stitched-surface failure. The board should emerge as the same concept workspace expands.

---

## 5. Verification Plan

1. **Unit tests:** Model validation, prompt contract assertions, pure renderer output.
2. **Browser tests:** Cover/work surface appears before first attempt, pre-attempt route markers are visible but not clickable/focusable and cannot reveal future entry prompts, inline cold attempt persists through the drill evaluator path, the saved-draft study gate shows the learner's draft without route previews before study reveal, post-reveal comparison appears on the same surface only after explicit reveal without score/tier/band/no-gap verdicts, route markers cannot dismiss comparison, `Keep working` expands the workspace, reload/back preserves that expansion via UI-only acknowledgement, and route controls navigate to entries without a separate board gate only after real attempt evidence plus `study_revealed_at` plus comparison acknowledgement exists.
3. **Coverage gate:** `./scripts/check-coverage.sh` must pass (diff-level 100%).
4. **Manual inspection:**
   - Create a source-less concept → see cover/work surface with the active cold-attempt writing task visible.
   - Write first draft → see saved draft on the same concept surface with no route preview and an explicit `Reveal notes and compare` action.
   - Reveal notes → see immediate post-reveal comparison on the same concept surface, not the full route-margin workspace yet.
   - Click `Keep working` → see the route-margin workspace expand from the same concept surface.
   - After expansion, choose a traversal-allowed route entry → see the existing route-margin workspace change active entry, with no "Enter Concept Board" gate.
   - Return to concept with saved draft but no study reveal → restore one-column saved-draft study gate.
   - Return to concept after study reveal but before `Keep working` → restore immediate post-reveal comparison.
   - Return to concept after `Keep working` → bypass cover-only/comparison state, land in expanded workspace.
   - Reset training → cover/work surface reappears.

---

## 6. Research That Informed This Decision

### Persona Simulation
A college sophomore persona (anti-gamification, pro-Socratic) was run through all three options. Key feedback:
- **Option A (Direct Route Margin):** "Feels like being shoved into a test room the second I walk into the library."
- **Option B (Gestalt Overview):** "I like this much better. It feels like opening a notebook and seeing my own starting thoughts."
- **Option C (Hybrid):** "This makes the most sense. Starting with B and moving to A is a natural progression."
- **Final request:** "Make sure the transition doesn't feel jarring."

Full persona simulation output: `.playwright-mcp/persona-simulation.txt`

### Later Grill Critique
A follow-up customer/persona critique accepted the immediate writing box but rejected the explicit "Enter Concept Board" step as dashboard creep. A skeptical pedagogy critique reinforced that pre-attempt scaffold must not leak answer structure. The resulting decision:
- the cover is a work surface, not passive orientation
- the cold-attempt writing task is primary
- generated route/scaffold is restrained before the attempt
- the route-margin board expands from the same concept surface only after explicit compare/reveal and `Keep working`
- no separate overview prompt/schema unless absolutely required

### Vault Context Check

The Socratink distillations vault was used only as product context; app-repo canon remains `docs/product/spec.md` and `docs/product/evidence-weighted-map.md`.

High-signal vault findings that reinforce this handoff:
- **Training evidence surface binding:** visible state surfaces must derive learner-facing truth from `socratink:training:v1:<conceptId>`, not legacy shell state. This supports keeping comparison acknowledgement UI-only and keeping graph truth tied to attempts, repair, and spaced re-drill evidence.
- **Finished-loop demo:** first-session clarity depends on showing what the learner supplies, what Socratink transforms, and what evidence returns to the map. This supports the self-contained loop shape: learner draft -> targeted comparison -> continued route work, without an "Enter Concept Board" dashboard step.
- **Tiny Repair Rep floor:** Repair Reps are optional typed micro-practice after a visible gap; they never unlock graph progress, spacing credit, scores, completion, mastery, or `solidified`. This supports showing repair only after study reveal when `next_action === "repair"`, while keeping repair separate from the comparison itself.
- **Surface leverage map:** Provisional map / Route Margin work must make structure inspectable without implying knowledge, mastery, completion, or diagnostic certainty. This supports inert pre-attempt markers and traversal-gated route controls only after `Keep working`.

No new runtime feature is promoted from the vault check. The accepted move is contract tightening only: preserve the minimum loop, keep Repair Reps graph-neutral, and verify the visible surfaces against training-derived evidence.

### Pedagogical UX Research
Research into cognitive load theory, desirable difficulties, and metacognitive scaffolding supports the hybrid:
- **Generation effect** (Slamecka & Graf, 1978): Writing before seeing material produces stronger retention. The cover/work surface enforces this.
- **Cognitive load theory** (Sweller): Staging reduces extraneous load by hiding the full workspace complexity until the learner is oriented.
- **Scaffolding withdrawal** (Vygotsky → Wood/Bruner): The cover/work surface is scaffolding that naturally withdraws as the learner gains competence.

---

## 7. Artifact Index

Session artifacts are in the Antigravity brain directory. Key references:

| Artifact | Content |
|:---------|:--------|
| `ab_evaluation.md` | Side-by-side A/B comparison matrix with integration recommendation |
| `analysis_results.md` | Full technical divergence analysis between branches |
| `git_sitrep.md` | Branch topology, commit history, merge conflict preview |
| `persona_prompt.txt` | The persona simulation prompt that was used |
| Screenshots | `route_margin_canvas.png`, `constellation_view.png`, `minimal_gestalt_overview.png`, `variant_e.png`, `concept_overview_*.png` |

---

## 8. Reference: Worktree Plan

The worktree has a detailed 6-task implementation plan at:
`docs/superpowers/plans/2026-05-20-concept-gestalt-overview.md`

Do not treat the old plan as directly portable. In particular, any backend/prompt tasks that add `LearnerOverview`, `LearnerRouteLabel`, or `metadata.learner_overview` are superseded by this handoff's no-new-schema default.

Portable intent:
- the 1-column cover/work renderer shape
- the restrained visual density
- focused renderer/browser tests
- relevant CSS patterns, with current cache-bust discipline

Non-portable or must-adapt:
- any new overview schema
- any separate "Enter Concept Board" gate
- any mount path that breaks current route-margin or active-entry bindings
