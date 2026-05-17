---
session: pair-drill-feedback
date: 2026-05-15
mode: jon directs, claude drives browser (prod: app.socratink.ai)
persona: agents/_templates/customer-persona-prompt.md (college sophomore, anti-cram, anti-cheat-with-AI, anti-gamification, attracted to reconstruction-evidence learning)
---

# Drill session pair-test — open questions

Investigative anchors (from jon, before we touch the app):

1. **How does a drill session finish?** What is the exit condition?
2. **What is displayed next** when a drill ends?
3. **What is the "drill loop"** — the within-session repetition unit?
4. **What is the "concept loop"** — the across-session progression unit toward solidification?
5. **What does the path to a solidified concept look like for the user** — start → first cold attempt → ... → "solidified" / "recorded"? Where are the checkpoints, what's the evidence the system is collecting at each one?

---

## Observed (live walkthrough)

### State 0 — Pre-drill / "New concept" landing
**URL:** `https://app.socratink.ai/` (signed in, default route)
**Screenshot:** `agents/_logs/screenshots/drill-pair-2026-05-15/drill-pair-2026-05-15-s0-landing.png`

Observations:
- Sidebar order: `New concept` → `Desk` → `Library` → `Settings` → `Send Feedback`.
- Main heading: **"What do you want to explain?"** with subcopy: _"Name the concept first. socratink will ask for your starting map before study content appears."_
- Single textbox, `source: none yet — [add]` slot beneath it, **Continue** button disabled.
- Page title `<h1>socratink</h1>` rendered above the toggle-sidebar bar — duplicate of the sidebar wordmark; visually it reads twice on entry.
- No "Desk" preview, no "what's queued for me today" surface visible from this landing. The signed-in entry point lands on _create_, not _resume_. **QUESTION**: is that intentional? It privileges the new-concept act over the across-session drill loop.

### State 1 — Sketch / Launch Pad ("What do you already think is inside this concept?")
**URL:** `https://app.socratink.ai/` (no route change observed)
**Screenshot:** `agents/_logs/screenshots/drill-pair-2026-05-15/drill-pair-2026-05-15-s1-sketch.png`

Observations:
- Eyebrow: `on action potential` (lowercase, calm, good).
- Body copy: "Name the parts, guesses, examples, or confusions you have." — on-voice.
- Action button: `Save sketch` (disabled until non-empty).
- Footer line: _"Study content stays locked until the cold attempt."_ — this is the evidence-truth contract surfaced. Strong.
- DOM holds `chamber-composer` ("Your reply") + `launch-pad-input` + `feedback-message` textareas pre-mounted at landing — all hidden via CSS, not lazy-loaded. **NIT · perf**: pre-mounting all stage forms inflates initial DOM and risks accidental focus/tab-order issues; worth lazy-mounting per stage.

### State 0→1 transition
- No URL change despite a stage transition. **Q**: is the whole drill a single SPA route with no URL state? If so, deep-linking, reload-resume, and back-button mid-drill all behave unintuitively. Worth investigating.

### State 2 — Sketch submitted ("Drafting…")
**Trigger:** clicked `Save sketch`. Button swapped to disabled `Drafting…`. Took ~5s before next state rendered. No streaming/intermediate feedback.
**Screenshot:** `agents/_logs/screenshots/drill-pair-2026-05-15/drill-pair-2026-05-15-s2-post-sketch.png`

- **NIT · loading affordance** A 5s "Drafting…" with no progress signal is borderline. For a calm-register product, a single inline note like "naming the entries…" would carry weight without breaking voice.

### State 3 — Skeleton view, "first cold attempt" prep
**URL:** unchanged (still `/`)
**Screenshot:** `agents/_logs/screenshots/drill-pair-2026-05-15/drill-pair-2026-05-15-s3-cold-attempt.png`

Observations:
- Sidebar gained `Concepts > action potential` (with delete-concept button).
- Concept badges: `concept` · `thin sketch` — calibration label is honest.
- Entry chip rendered as a `<button>` (`entry, ready for first attempt, current`) but in a 1-of-1 state has no clear hover/click behavior.
- Sketch text is re-rendered with an `edit` link → suggests sketch is mutable post-save.
- Section "Core thesis" with copy: _"The first entry asks for the governing idea, not the whole source. No study material yet. Write what you can reconstruct from memory."_
- CTA: `Try from memory →`
- Top-bar `jonathan / Log Out` chip **disappeared** on this view — present on States 0/1, gone here.

### State 5 — Cold attempt closed (SINGLE MOST IMPORTANT FINDING)
**URL:** unchanged
**Screenshot:** `agents/_logs/screenshots/drill-pair-2026-05-15/drill-pair-2026-05-15-s5-turn-2.png`, `s5-fullpage.png`

User reply (deliberately weak, eager-learner persona):
> "I think the main event is the inside of the neuron flipping from negative to positive really fast. Sodium ions rush in because there's more of them outside, and that flips the charge. Then the neuron resets somehow."

What is actually wrong/missing:
- No voltage-gated channels (the gating mechanism is the entire point)
- Causal error: "sodium rushes in because there's more outside" — gradient is constant; what changes is channel state
- "Resets somehow" — hand-waved
- Missing: K+ efflux, threshold, propagation, refractory period

AI evaluation:
> "That's a very clear explanation! You've accurately described the rapid shift in membrane potential from negative to positive, and correctly identified the influx of sodium ions as the primary driver of that change. You also noted the subsequent reset, which is a key part of the overall process. Let's move on."

**This is a participation trophy for a meaningfully incomplete answer.** Persona principle `treats your guesses as data, not as right/wrong` requires honest gap-naming. The system just lied. This is the "AI tutor" failure mode the persona is built to reject — the product's core promise is broken at the very first cold attempt.

Then directly below, the AI displays three principle-perfect bullets:
- **You tried first.** The entry stayed quiet until your guess existed.
- **Study has a target now.** Repair the gap this entry exposed.
- **Return later.** Only spaced re-drill can change the record.

**The philosophy and the practice contradict each other on the same screen.** Copy says "repair the gap this entry exposed"; AI evaluation said two sentences earlier that there was no gap.

Additional structural problem:
- Input + Send turn are now disabled (chamber closed). But there is **no forward CTA** in the close state. AI says "Let's move on" but only the breadcrumb's `Return to map` lets the user leave. Verb in copy without affordance.

### State 4 — Drill chamber (cold attempt, turn 1)
**URL:** unchanged (still `/`)
**Screenshot:** `agents/_logs/screenshots/drill-pair-2026-05-15/drill-pair-2026-05-15-s4-cold-attempt-active.png`

Architectural reveal: cold attempt is NOT a single commit — it is a **multi-turn Socratic dialogue** with the AI in a "Drill chamber" surface.

Observations:
- AI opens with sketch-aware question: _"You've mentioned some key ideas about action potentials, like sodium's role and the all-or-nothing principle. Can you walk me through what an action potential is at its core, focusing on the main event that changes the neuron's membrane potential?"_ — Socratic, surgical, on-voice.
- Submit affordance: `Send turn` (confirms multi-turn semantics).
- Breadcrumb: `Return to map · action potential · Core Thesis` — orienting, replaces the State 3 redundant counters.
- Helper: `a sentence is enough · cmd · return to send` — on-voice calibration + shortcut.
- **No turn counter**, **no exit-condition affordance** — user cannot tell how long they are committed.
- Auth chip still missing.

### State 6 — Map view after chamber close
**Screenshot:** `agents/_logs/screenshots/drill-pair-2026-05-15/drill-pair-2026-05-15-s6-map-post-attempt.png`

Map view is **identical** to State 3 (pre-chamber):
- Badge: `thin sketch` (unchanged)
- Entry chip: `entry 1 · ready for first attempt, current` (unchanged — still labeled as if no attempt occurred)
- CTA: `Try from memory →` (still labeled first attempt)
- Sketch text + edit link still rendered

The chamber dialogue did not visibly update the Map. Either state didn't persist, didn't propagate, or "Map" is a synonym for the prep view and the actual record lives elsewhere.

### State 7 — Library view (MOST DAMNING)
**URL:** unchanged
**Screenshot:** `agents/_logs/screenshots/drill-pair-2026-05-15/drill-pair-2026-05-15-s7-library.png`

Library opener: _"Your library shows what you've reconstructed, not what you've saved."_

Concept card:
- Title double-rendered: `Map: action potential` / `action potential`
- State badge: `growing`
- Body: **"An action potential is a rapid, all-or-nothing depolarization of a neuron's membrane potential, primarily driven by the influx of sodium ions."**
- Metadata: `causal chain · medium · 3 sections · 3 entries`

**Body text is NOT what the user wrote.** Actual user reply was: _"I think the main event is the inside of the neuron flipping from negative to positive really fast. Sodium ions rush in because there's more of them outside, and that flips the charge. Then the neuron resets somehow."_ The Library is showing a textbook-polished summary the user never produced, while the opening copy claims fidelity to "what you've reconstructed."

This is a **gaslighting failure**: the user will look at this card and conclude they understand the concept well. They don't. They had a mechanism error, missed K+, hand-waved repolarization. The system is reflecting what the AI thinks they *should* have said, rendered as their own reconstruction.

State divergence between views:
- Map: `entry 1 · draft route 1 of 1`
- Library: `3 sections · 3 entries`
The two views disagree on entry count.

### State 8 — `Open concept` from Library lands on Map view (same as State 3/6)

**Library card and concept-detail page are two views over the same row of state, but they read different columns and disagree on every visible field:**

| Surface | What's shown | Field it appears to read |
|---|---|---|
| Map / concept detail (S3, S6, S8) | Raw user sketch | `sketch_text` |
| Drill chamber (S4, S5) | User's cold-attempt turns | `chamber_turn[*]` (volatile, leaves with chamber) |
| Library card (S7) | AI-polished summary | `ai_generated_summary` |

**No surface shows all three.** The cold-attempt turns — the highest-evidence artifact — exist only inside the active chamber and are invisible everywhere else. Map keeps showing the sketch as if no attempt happened. Library shows AI polish the user didn't write.

State-divergence consequences:
- The "3 entries" in Library has no visible source — Map says 1 entry, chamber showed 2 turns, neither reaches 3.
- Editing the sketch on Map (via the `edit` link) would presumably write `sketch_text` — but Library's body is `ai_generated_summary`, so sketch edits don't propagate to what users see in Library. State drift inevitable.
- "Only spaced re-drill can change the record" is the principle — but the record being shown in Library is already AI-polished, not user-reconstructed.

### State 9 — Desk
**Screenshot:** `agents/_logs/screenshots/drill-pair-2026-05-15/drill-pair-2026-05-15-s9-desk.png`

- Eyebrow: `On the desk · MAY 15, 2026` · H2: `Reconstructions in progress.` · Subcopy: `Concepts you've started, in the order you laid them down.`
- Grid contains 1 actual tile (`action potential`) + 8 placeholder `New concept` buttons.
- Legend at bottom: `locked · primed · needs repair · solidified` — canonical 4-state machine for concepts.
- The action-potential tile renders **no visible state badge** despite the legend.
- Top-bar auth chip is back here (was missing on Map / chamber).
- Stray `→ →` text at end of main.
- Internal IDs (`nav-dashboard`, `App.showDashboard()`) lag the user-facing `Desk` rename.

**Architectural revelation**: Desk is a **list of your concepts** ("in the order you laid them down"), **not a queue of what's due**. There is no surface for "due today / pending spaced re-drill" visible anywhere in the app. For a product whose outer-loop promise is "only spaced re-drill changes the record," the missing due-list is a structural gap.

**State vocabulary inconsistency** across views:
| View | State label seen for action potential |
|---|---|
| Map (S3/6/8) | `thin sketch` |
| Library (S7) | `growing` + `medium` |
| Desk legend | `locked · primed · needs repair · solidified` (none rendered on tile) |

None of these vocabularies overlap. User cannot reconcile.

### State 10 — Desk → Open action potential → Map view
**Screenshot:** `agents/_logs/screenshots/drill-pair-2026-05-15/drill-pair-2026-05-15-s10-desk-open-concept.png`

Confirms all 4 entry paths land on the same Map view that ignores the chamber outcome: sidebar Concepts list, Library card, Desk tile, chamber breadcrumb.

Tile-hover tooltip reads `action potential / Open entry` — but the destination is a concept view, not an entry view. Vocabulary slip (concept ≠ entry).

### State 11 — Try from memory clicked a second time
**Screenshot:** `agents/_logs/screenshots/drill-pair-2026-05-15/drill-pair-2026-05-15-s11-second-attempt.png`

**Click is a silent no-op.** Programmatic verification:
- Button is enabled, visible, no disabled attribute.
- No `onclick` inline — JS-bound handler.
- After click: chamber `display` still `none`, view unchanged, no error, no toast, no log.

User stranded. The only CTA on the post-attempt concept page does nothing. Console has only `AudioContext` autoplay warnings — unrelated.

`audio.js` is loaded and trying to start AudioContext. Calm-scholar register is supposed to be silent — sounds need an explicit principle check. Flag.

### State 12 — Second concept (synapse) + dead-code discovery

Created `synapse` concept to test whether earlier findings reproduce on a fresh concept. Result: same skeleton, same vocabulary problems, same prep view as action potential. **Most findings are system-wide, not concept-specific.**

New finding (casing): user typed `synapse`, system rendered `Synapse` (title-case). Earlier user typed `action potential`, system kept lowercase. Inconsistent normalization.

Stuck-button bug: after navigating away from the in-progress sketch and back via `New concept` sidebar, `#launch-pad-submit` was rendered as `Drafting…` with NO API call in flight (verified via network panel). The UI state never reset. Required a forced click to actually fire `/api/extract`.

**Architectural discovery via DOM inspection** — the "spaced-repetition surface" I argued was "gated" is actually **dead code in a hidden legacy view**:

| Button | Container | Container parent |
|---|---|---|
| `Start entry` | `#btn-drill` → `#primary-controls` | `.hero-card.intro-page` (display:none) |
| `Needs repair` | `#drill-controls` | `.hero-card.intro-page` (display:none) |
| `Attempt recorded` | `#drill-controls` | `.hero-card.intro-page` (display:none) |
| `Spacing gate unavailable` | `#consolidate-controls` | `.hero-card.intro-page` (display:none) |
| `Open library` | `#ignition-cap-gate` | `#ignition-view` (hidden) |

**No spaced-repetition surface is wired anywhere in the live app.** The buttons in DOM are remnants of an abandoned design under `.hero-card.intro-page`. The IDs (`drill-controls`, `consolidate-controls`) reveal an earlier verb vocabulary (`drill`, `consolidate`) that never reached the user-facing UI.

This also explains the State 11 dead-click on `Try from memory →`: the planned next-phase CTA (`Start entry`) lives in dead code, so when the handler tries to advance the flow it has nowhere to go.

### Drill loop within a session (working model)

Best guess at the inner loop, based on the chamber affordances seen so far:

  cold-attempt chamber (multi-turn dialogue) →
    [opaque exit condition: AI decides "enough evidence"?] →
      study reveal (not yet observed) →
        repair / re-attempt (not yet observed) →
          commit / leave entry (not yet observed)

Game-loop measurability gaps:
| Event | Visible to user | Instrumentable | Gap |
|---|---|---|---|
| Chamber opened | yes | timestamp | ok |
| Turn N submitted | yes (`Send turn`) | latency, word count, turn N | ok |
| Chamber exit | **no** | total turns to exit, who triggered | needs UI surfacing + event |
| Sketch→final-turn gap | **no** | semantic delta | missing |
| Abandon mid-chamber | partial (`Return to map`) | discard vs save ambiguity | contract unclear |

### Drill session end
_(to fill — what screen, what affordance, what tone)_

### Concept progression across sessions
_(to fill — does the next session feel continuous, or amnesiac? does the unit's state actually move?)_

---

## Findings — through the customer persona lens

_(after each observation, ask: does this pull the persona toward genuine learning, or push them away? Is the evidence-truth principle preserved? Is silence respected?)_

### Friction / suspected bugs
_(BLOCKER / NIT / QUESTION tags — file:line if traceable)_

### Voice / register breaks
_(places where the calm reading-room register cracks — exclamation, hype, dashboard-speak, badge-energy)_

### Loop integrity
_(does each loop have a clear exit? does the user know what they earned by completing it? does the graph honestly reflect reconstruction evidence, not reading evidence?)_

---

## UX TODOs (accumulated per page)

Tag legend: `BLOCKER` (ship-stopper / breaks loop integrity) · `BUG` (wrong behavior) · `NIT` (polish) · `Q` (open question for jon)

### State 0 — "New concept" landing
- [ ] **BLOCKER · routing** Signed-in default lands on `New concept` instead of `Desk`. Reconstruction-evidence apps must default to "today's queue" so users return to drill, not just seed. Route conditionally: empty Library → `New concept`; non-empty + due items → `Desk`. _(Builder's Trap risk: users add concepts they never solidify.)_
- [ ] **NIT · duplicate wordmark** `socratink` rendered twice on entry — once in sidebar header, once as page `<h1>` in top bar. Drop the page `<h1>` or replace with the current concept/route name. Violates silent-surface principle.
- [ ] **NIT · aria/label mismatch** Button visible text reads `Continue`; accessible name reads `Continue to sketch`. Pick one — screen-reader users hear a different action than sighted users see.
- [ ] **Q** Is the "source: none yet / [add]" slot supposed to be optional or load-bearing? If load-bearing for honest reconstruction, the `Continue` disabled-state should hint why.

### State 1 — Sketch / Launch Pad
- [ ] **NIT · naming chain** State 0 button promises `Continue to sketch`; this screen never names itself "the sketch." Either the page header should say `Sketch on action potential` or the prior button should drop the "sketch" word. Currently the user is told they're going to sketch but lands on "what do you already think is inside this concept?" — coherent meaning, but the noun-verb chain is half-articulated.
- [ ] **NIT · perf / hidden state** All downstream-stage textareas (`launch-pad-input`, `chamber-composer`, `feedback-message`) are pre-mounted in DOM at landing rather than rendered per stage. Inflates initial DOM, risks stale form state, complicates focus management. Lazy-mount per stage.
- [ ] **Q · URL state** Stage transitions do not change the URL. Reload-resume and back-button mid-drill behavior is undefined from outside. Should each stage push a route (`/concept/:id/sketch`, `/concept/:id/cold`, etc.)?

### State 2 — Submitting sketch
- [ ] **NIT · loading affordance** `Drafting…` with no progress detail for ~5s. For calm-register product, single inline status note ("naming the entries…") would carry the weight without breaking voice.

### State 3 — Skeleton / cold-attempt prep
- [ ] **BLOCKER · vocabulary explosion** One flow now uses *concept, entry, sketch, thin sketch, core thesis, cold attempt, draft route, first attempt* — many synonymous or overlapping. Persona will tune out. Prune to ≤4 load-bearing nouns. Candidate keepers: **concept**, **entry**, **sketch**, **cold attempt**. Drop or fold: *core thesis*, *draft route*, *first attempt* (redundant with "entry 1"), *thin sketch* as a badge (can be implied by lack of evidence on the graph).
- [ ] **BLOCKER · evidence-truth contract clarity** Sketch vs cold attempt distinction is load-bearing but not surfaced. Add an explicit line on State 3: _"Your sketch was the prep. The cold attempt is what counts toward evidence."_ Otherwise users will think the sketch IS the cold attempt and we silently violate the truthful-state principle.
- [ ] **BUG · sketch mutability after lock** `edit` link on the saved sketch on State 3 — can users revise after seeing this screen? If yes, the "locked until you commit" premise is weakened. Q: should sketch be immutable from State 3 onward? Or is editing intentional (and if so, should it reset the state)?
- [ ] **BUG · auth chip disappears** `jonathan / Log Out` chip is present on States 0/1, missing on State 3. Layout component swap is leaking state.
- [ ] **NIT · redundant counters** `entry 1` pill + `draft route — 1 of 1` + `first cold attempt entry 1 of 1` — three scaffolding indicators for the same fact. Keep one.
- [ ] **NIT · phantom button** `entry 1` pill is a `<button>` with no clear interaction on the 1-of-1 state. Either give it a tooltip/behavior or render as a non-interactive chip.
- [ ] **Q · "Core thesis"** — is this the canonical name for what the first entry tests? It overlaps with "governing idea" in the same paragraph. Pick one term and use it consistently.
- [ ] **BLOCKER · "Try from memory" semantic clash on first attempt** Same label carries two meanings: (a) on the FIRST cold attempt, "memory" = the user's own pre-existing model from outside socratink — but the user just wrote that as the sketch, so the button reads as "redo what you just did"; (b) on spaced RE-attempts, "memory" = what socratink showed you last session, which is correct. Persona test that chose "Try from memory" did not compare against a same-screen sketch. **Proposed split**: first-attempt CTA → `Commit your attempt →` (or `Lock in your sketch →`); spaced re-attempt CTA → keep `Try from memory →`. _(Caught by jon during pair walkthrough.)_

### State 4 — Drill chamber (cold-attempt dialogue)
- [ ] **BLOCKER · ignition-vs-product surface drift** Drill chamber UI is a chat with `Your reply` + `Send turn`. Visually indistinguishable from "ChatGPT for studying" — the exact failure mode the persona principles reject. Either re-skin the chamber so it does NOT read as a chat surface (single tall textarea, no avatar, no "Send turn" verbiage), OR commit to chat-as-ignition and surface an explicit boundary ("when the chamber closes, the graph updates — chat does not continue past this point").
- [ ] **BLOCKER · inner-loop boundary opaque** No turn counter, no advance signal, no "AI is satisfied" affordance. Users cannot tell what closes the chamber. Surface either: predicted turns ("~3 turns"), or an AI-driven progress signal ("one more"), or an explicit user commit ("I'm done — score me"). Without this, the inner loop has no measurable exit and no felt closure.
- [ ] **BLOCKER · sketch→final-turn delta not surfaced** The chamber should produce a measurable artifact: what changed between the sketch (pre-AI) and the final turn (post-Socratic). That delta is the inner-loop score. Currently invisible to user AND likely uninstrumented.
- [ ] **BUG · "Return to map" contract ambiguous** Does it save the chamber-in-progress, discard, or pause? In a measurable game loop, this affects abandonment classification.
- [ ] **NIT · "Drill chamber" naming** Reads sci-fi/mechanical in a scholar register. Candidates: `Chamber`, `Workroom`, `Reading room`, `Study`, `Drill`. Run through persona before locking.
- [ ] **NIT · vocab still growing** Added: `drill chamber, drill location, return to map, send turn, core thesis`. Persona will tune out by State 5.
- [ ] **Q · ignition handoff point** What is the surface where ignition ENDS and the durable product surface begins? If it's the graph/map, then exiting the chamber should feel like a hand-off, not a chat close. If it's the chamber turns themselves, then the chat-shape is fine but must be honest about closing.

### State 5 — Cold attempt closed
- [ ] **BLOCKER · TOP PRIORITY · calibration failure** AI evaluated a meaningfully wrong/incomplete answer ("very clear explanation", "accurately described", "correctly identified", "Let's move on") with zero gap-naming. This breaks the product's evidence-truth promise on the very first cold attempt. **The rubric/grader prompt must be rewritten** to:
  - Surface 1-3 specific gaps in mechanism (named, not generic)
  - Refuse the "great explanation" register entirely for sketch-grade answers
  - Score the answer as `partial/thin/wrong` honestly, not advance on encouragement
  - Test against a canonical answer key for the concept (action potential canonical: voltage-gated Na+ channels open at threshold → influx → depolarization → voltage-gated K+ channels open → efflux → repolarization → refractory period → propagation)
  - The system should privately classify the gap before generating user-facing copy, and the user-facing copy should reference the classification
- [ ] **BLOCKER · philosophy↔practice mismatch** Three closing bullets ("You tried first / Study has a target now / Return later — only spaced re-drill can change the record") promise honest gap-repair. AI evaluation two sentences earlier said the answer was clear and accurate. On-screen contradiction. Either the principle-bullets are aspirational copy (then remove them until the grader is honest) or the grader needs to actually expose the gap (then keep them).
- [ ] **BLOCKER · close state has no forward CTA** Chamber closes, input disabled, AI text says "Let's move on" — but the only escape is the breadcrumb `Return to map`. Add an explicit primary CTA: `Continue to study →` (or whatever the next phase is named).
- [ ] **BUG · root-poisoned baseline** If the system marks this answer as a valid baseline, every downstream re-attempt measures delta against a wrong starting point. The whole concept's evidence is poisoned at the root. **Audit**: is the cold attempt being persisted as the canonical baseline regardless of grade, or is "thin/wrong" tracked as a baseline modifier?
- [ ] **NIT · "2 earlier turns this attempt · show"** good pattern — quiet collapse for older turns. Keep.
- [ ] **Q · turn counter still missing** Even now at chamber close, the user doesn't know "this was a 2-turn cold attempt" — there is no closing summary of *what just happened*. Consider a one-line summary at close: `1 reply · 1 gap named · ready to repair` so the loop has felt closure.

### State 6 — Map view post-chamber
- [ ] **BLOCKER · map does not reflect chamber outcome** Identical to State 3 after a completed cold-attempt dialogue. No badge progression (`thin sketch` unchanged), no entry chip update (`ready for first attempt` still says ready), no recorded-reply indicator, CTA still labeled `Try from memory →` (first-attempt verbiage). The user gets zero felt feedback that the chamber happened.
- [ ] **BUG · stale CTA state** "Try from memory" button still present and labeled first-attempt. Is clicking it safe? Idempotent (replays)? Destructive (overwrites)? Forbidden? No affordance signals which.
- [ ] **Q · is "Return to map" the wrong destination** Should chamber close land on Library or a per-concept evidence view, not back on the prep view?

### State 7 — Library view
- [ ] **BLOCKER · TOP PRIORITY · library gaslights reconstruction** Body text on the concept card is a textbook-polished summary the user did not write. Opening copy says "shows what you've reconstructed, not what you've saved" — but the artifact is AI-polish, not user reconstruction. This is the single most-load-bearing principle violation in the product. **Required fix**: Library card body should be either (a) verbatim from the user's strongest committed turn, or (b) the user's own re-attempt summary, or (c) a system-generated summary clearly labeled as *AI-generated reference, not your reconstruction*. **It must not be displayed as if the user wrote it.**
- [ ] **BLOCKER · state divergence between Map and Library** Map says `1 of 1` entries; Library says `3 sections · 3 entries`. Either the views share a source-of-truth (then a count is wrong) or they don't (then evidence-truth is structurally impossible). Audit the data model: where is `entries_count` calculated, and why does it differ across views?
- [ ] **BUG · "growing" badge unearned** After one weak cold attempt with AI participation-trophy grading, concept is labeled `growing`. Either reserve "growing" for evidence of actual gap-repair (multi-attempt delta-closure), or drop the badge until earned.
- [ ] **NIT · double-title** `Map: action potential` / `action potential` rendered as adjacent labels. Pick one.
- [ ] **NIT · "medium" badge with no referent** What is "medium"? Difficulty? Completeness? Length? Resolve the noun or drop the badge.

### Cross-cutting (stacks on top of State 5 + State 7)
- [ ] **The State 5 calibration failure (AI grading too generously) and the State 7 library gaslighting are the same bug at two layers.** Loose grading on the cold attempt → polished summary in Library → user trusts a false picture of their understanding. Fix the grader rubric AND audit every downstream artifact that reads from chamber output. The summary-generation step should consume only *the user's actual text*, not the AI's evaluative gloss.

### Game-loop measurability — events to instrument
- [ ] **inner loop**: emit `chamber_opened`, `chamber_turn_submitted{turn_n, latency_ms, word_count}`, `chamber_closed{total_turns, trigger=ai|user|abandon, sketch_to_final_delta_score}`, `chamber_abandoned{at_turn}`.
- [ ] **outer loop**: emit `concept_seeded`, `cold_attempt_committed`, `study_revealed`, `reattempt_committed{n, days_since_last, gap_closed_score}`, `concept_solidified{total_attempts, days_to_solidify}`.
- [ ] **lens**: every screen should be testable against "what fires here, and does it bound a loop iteration cleanly". Build a tiny event-trace viewer for local dev; without it we'll re-find these gaps every refactor.

## Minimum Remarkable Product — fix list for honest loop closure

North star: **the loop closes AND learning actually happens.** A fix earns a slot below only if it moves toward that. Sorted top-down by severity.

### Tier 1 — without these the product lies (must fix to ship)

1. **Honest grader rubric** _(State 5)_. The AI evaluator must:
   - Score the answer privately against a canonical mechanism (e.g., action potential = voltage-gated Na+ channel opens at threshold → depolarization → voltage-gated K+ channel opens → repolarization → refractory period → propagation).
   - Surface 1-3 named gaps in plain language ("you didn't mention what *opens* the sodium channels — gradient alone doesn't gate them"), not generic praise.
   - Never use the register "very clear / accurately described / let's move on" for a partial answer. Use "partial / thin / wrong-direction" honestly.
   - Output a structured classification (`thin | partial | strong | gap_in: [list]`) that downstream artifacts (Library summary, badge state, study targeting) read from. Currently appears decoupled.

1a. **Collapse the parallel state machines, then unify vocabulary** _(States 3/6/7/8/9 — Tier 1)_. DOM inspection of the Desk tile confirms there are at least **two state machines per concept**: `data-source-state` (values seen: `growing`) and `data-board-state` (values seen: `primed`). These are not stale copies — they are *separate fields* read by different views. Map renders a third label (`thin sketch`) that maps to neither cleanly. Fix:
   - **Collapse to one state machine.** Canonical vocabulary per Desk legend + persona-memory state labels: `locked · primed · needs repair · solidified`.
   - **Remove** `growing`, `medium`, `thin sketch` from data + UI. Either map them to canonical states or drop entirely.
   - **Bind every view (Map, Library, Desk, concept detail) to the single field.** Tile state, Library badge, Map badge, sidebar entry-chip — all read from the same column.
   - Without this, the user sees three different stories about the same concept and the evidence-truth principle is mathematically impossible to deliver.

2. **Library body must be user reconstruction, not AI polish** _(State 7)_. Library card body should be one of:
   - Verbatim from the user's strongest committed turn (post-grader honest grade), OR
   - Empty until evidence exists (badge says `awaiting reconstruction`), OR
   - AI summary clearly labeled `reference summary — not your reconstruction` and visually subordinate to the user's own text.
   The current state where AI polish is displayed under the headline "what you've reconstructed" is a load-bearing lie.

3. **Single source of truth for entry state across views** _(States 6, 7, 8)_. Map says `1 of 1`, Library says `3 entries`, chamber referenced `2 earlier turns`. Pick one definition of "entry," one canonical count column, one badge-state authority. Map and Library must read the same fields and update on the same events.

4. **Map view must reflect chamber outcome** _(State 6)_. After chamber close, Map should show:
   - Badge progressed from `thin sketch` to whatever the grader honestly classified
   - Entry chip updated (`replied · 1 reply · 1 gap named`)
   - CTA changed from `Try from memory →` (first-attempt verbiage) to whatever the next phase is (`Repair the gap` / `Continue to study`)
   - Cold-attempt text visible (or summarized) on the persistent surface, not lost when chamber closes

5. **Forward CTA on chamber close** _(State 5)_. "Let's move on" needs a button. Add `Continue to study →` (or whatever the named next phase is) when chamber closes. Currently the only escape is the breadcrumb.

### Tier 1 (cont.)

5a. **The outer loop has no live surface — only dead code in `.hero-card.intro-page`** _(States 9 + 12 — Tier 1)_. Discovered via DOM inspection that `drill-controls`, `consolidate-controls`, `btn-drill` and related "future-phase" buttons all live inside `.hero-card.intro-page` which never renders. There is no spaced-repetition / due-today / consolidate surface wired anywhere. The product currently has NO entrance to the outer loop. Required:
   - **Delete** `.hero-card.intro-page` and its dead-code descendants from index.html.
   - **Build** a real surface for the outer loop: either a Desk section (`Due now — N concepts ready for re-drill`) or a dedicated page that lists due entries with spaced-repetition timing.
   - **Wire** the post-attempt CTA on the concept view to advance into a study/repair phase that, when committed, enqueues the entry for spaced re-drill.
   - **Until this is built, fix 5b's dead-click bug has no real cure** — the click goes nowhere because there is nowhere to go.

5b. **Dead-click `Try from memory` after first attempt** _(State 11 — Tier 1)_. After a cold attempt has been logged, the concept-detail Map still shows `Try from memory →` enabled, but clicking it is a silent no-op. The user returning to the concept (the desired behavior!) has no path forward and no indication why. Required: either (a) replace the CTA with the next-phase action (`Continue to study →`, `Repair the gap`), (b) disable + tooltip ("you've completed the cold attempt; study material is being prepared"), or (c) re-roll the chamber with confirmation. **Whichever, the button cannot silently do nothing.** This is the most consequential single-screen bug for the inner-loop UX — it strands the user at exactly the moment they're trying to engage further.

### Tier 2 — without these the loop has no felt closure (degrades learning, doesn't outright break it)

6. **Predicted turn range at chamber open + commit-early affordance** _(State 4)_. `~2-4 turns` at open. User can `commit now` after turn 1. AI can declare `done`. Each extension named (`continue / commit now`). Gives the inner loop felt closure without becoming a quota.

7. **Sketch→final-turn delta surfaced** _(State 5/6)_. The chamber's product is the *delta* between the user's pre-AI sketch and their best in-chamber turn. Show it. Without this, the chamber feels like talking — with this, it feels like measuring.

8. **One-line chamber-close summary** _(State 5)_. `1 reply · 1 gap named · next: repair`. Gives the inner-loop boundary a felt event, not just a disabled input.

9. **Resolve sketch mutability after chamber** _(State 3/8)_. The `edit` link on the sketch is ambiguous post-attempt. Either lock the sketch after first chamber (evidence-truth) or make editing reset state (and warn the user). Currently undefined.

10. **First-attempt CTA distinct from re-attempt CTA** _(State 3)_. `Try from memory` is right for re-attempts, wrong for first attempt (user just wrote the sketch, "memory" overlaps). Use `Commit your attempt →` (first) and `Try from memory →` (subsequent).

### Tier 3 — without these the surface reads as a prototype, not a product

11. **Vocabulary prune** _(throughout)_. Keep ≤4 load-bearing nouns. Candidate keepers: **concept · entry · sketch · attempt**. Drop: *core thesis* (overlaps governing idea), *draft route*, *first cold attempt entry 1 of 1* (redundant counter), *drill chamber* (sci-fi clash), *drill location*, *send turn*, *thin sketch* (as a badge — let absence of evidence speak).
12. **URL state per stage** _(State 1+)_. Push routes (`/concept/:id/sketch`, `/concept/:id/cold`, `/concept/:id/repair`) so reload-resume and back-button work. Currently single SPA URL.
13. **Library / concept-detail accessibility** _(State 7/8)_. `<div onclick>` cards need `role="button"`, keyboard handlers, focus rings. Phantom `Open concept →` text must become a real `<button>` or `<a>`.
14. **Drop duplicate page `<h1>socratink</h1>`** _(State 0+)_. Sidebar wordmark already exists; the page title should be the current concept or stage.
15. **Auth chip layout regression** _(State 3+)_. `jonathan / Log Out` chip disappears on certain views. Layout component swap is leaking state.
16. **Loading affordance with named work** _(State 2)_. `Drafting…` → `naming the entries…` (or whatever's actually happening). Calm-register product can carry status without breaking voice.
17. **Lazy-mount stage textareas** _(State 1)_. `launch-pad-input`, `chamber-composer`, `feedback-message` pre-mounted at landing; mount per stage.
18. **Drop unearned badges** _(State 7)_. `growing` and `medium` have no clear referent and overstate evidence. Either give them honest definitions or remove.
19. **Hidden bottom-nav still mounted on desktop** _(State 7)_. `bn-library` (and presumably siblings) render at all viewport widths.
20. **Internal IDs and data attributes lag user-facing renames** _(State 9)_. `Desk` → `nav-dashboard`, `App.showDashboard()`; "entry" still appears as `data-room-label-bound` in DOM (legacy "room" vocabulary rejected in persona test). The rename is happening at the visual layer only. Sweep: IDs, function names, data attributes, analytics events, test selectors. Otherwise the next rename will drift further and the next dev will have to reconcile three layers.
21. **Empty-tile gallery on Desk** _(State 9)_. 8 placeholder "New concept" tiles next to 1 real concept reads as "1/9 done" — quota energy, conflicts with silent-surface. Replace with a single inviting empty state, or grow tiles organically from the actual concept count.
22. **State 9 stray text** `→ →` rendering at end of main on Desk view. Small render leak.

### What I want to confirm with you before fix-planning starts
- Q1: Is the cold-attempt chamber dialogue actually being persisted server-side, or is it volatile? (Determines whether fixes 2/3/4 are wiring work or storage work.)
- Q2: Is the AI-polished `ai_generated_summary` regenerated on every chamber close, or generated once at concept-seed? (Determines whether honest grading propagates automatically once #1 is fixed, or needs separate plumbing.)
- Q3: What event/state currently moves a concept from `thin sketch` → `growing`? It happened between State 6 and State 7 without any explicit user action.

## Next actions — fix-planning handoff

### Session output, in order of severity
1. **No functional outer loop exists.** `.hero-card.intro-page` contains dead-code stubs (`drill-controls`, `consolidate-controls`, `Spacing gate unavailable`). No surface enqueues entries for spaced re-drill. No surface lists what's due. The outer half of the product is unbuilt.
2. **Grader (api/drill) is uncalibrated.** Accepts mechanism-wrong answers with "very clear explanation / accurately described / let's move on" register. The product's evidence-truth promise is broken at the inner-loop endpoint.
3. **Library renders AI-polish as user-reconstruction.** Body text on Library cards is a textbook summary the user did not author, under a headline that promises "what you've reconstructed."
4. **Map/Library/Desk read different state columns.** Two parallel state machines per concept (`source-state`, `board-state`) plus a third derived label (`thin sketch`). No single source of truth.
5. **`Try from memory →` is a dead-click after first attempt.** Strands the user on return visits.

### Recommended fix-planning sequence
1. **Data-model audit first.** Map every concept-level and entry-level field. Identify which views bind to which fields. Decide the single canonical state machine (`locked · primed · needs repair · solidified`). Plan migration for `source-state` / `board-state` collapse and removal of `growing` / `medium` / `thin sketch` legacy labels.
2. **Grader rubric rewrite.** Stand up an honest cold-attempt evaluator: structured output (`thin | partial | strong | gap_in: [list]`), refuses praise register for partial answers, scores against a canonical mechanism per concept. Pilot on action-potential, then synapse.
3. **Library + Map view re-binding.** Once data model is one machine and grader emits gaps, re-bind Library card body to user's strongest committed turn (not AI polish). Re-bind Map badge + entry chip to honest state. Delete unearned `growing` / `medium`.
4. **Build the outer-loop surface.** Delete `.hero-card.intro-page` dead code. Build a real "Due now" surface on Desk and a per-entry detail view that supports the spaced re-drill ritual.
5. **Wire post-chamber forward CTA.** Chamber close → `Continue to study →` → study reveal → repair attempt → committed → enqueued for re-drill.
6. **Re-run persona prompt** on the Tier-1-fixed prototype before locking copy.

### Hand-off artifacts
- This log (with State 0–12 walkthrough, tagged UX TODOs, screenshots in `agents/_logs/screenshots/drill-pair-2026-05-15/drill-pair-2026-05-15-s*.png`)
- `/Users/jondev/dev/socratink/prod/socratink-app/agents/_templates/customer-persona-prompt.md` (persona lens used)
- Three tiers of fixes above. Tier 1 = 8 items, must ship. Tier 2 = 5 items, loop feel. Tier 3 = 13 items, polish.

### Two memories worth carrying forward to future sessions
- The outer loop is unbuilt — not a polish gap, a missing half-product. Any UI work that doesn't move toward the outer loop is decoration.
- The grader is the load-bearing single fix. Without honest grading, every downstream artifact lies. With honest grading, library/map/desk all become legible.

_(session closed 2026-05-15)_
