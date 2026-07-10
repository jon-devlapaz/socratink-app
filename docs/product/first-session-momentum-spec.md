# socratink — First-Session Momentum Spec

> Binding under [`evidence-weighted-map.md`](evidence-weighted-map.md) and
> [`post-drill-ux-spec.md`](post-drill-ux-spec.md). This spec governs the learner's
> first ~90 seconds: door, launch, extract wait, first drill check, and the
> surfaces that must reflect effort before reconstruction is complete.
>
> **Does not override** generation-before-recognition. Study still unlocks only
> after substantive learner generation. This spec defines *how* to reduce
> psychological friction without faking mastery or skipping cold attempts.

```yaml
title: First-Session Momentum UX
date: 2026-07-09
status: binding implementation spec
scope: learner-facing first session through first drill verdict
branch: agent/student-first-moment (partial land) → feat/first-session-momentum
```

---

## Agent Summary

> **Read this before** changing door copy, launch pad layout, extract overlay,
> first drill verdict, Desk/Library empty states during in-progress sessions, or
> guest-session continuity copy.
>
> **Goal:** Time-to-"oh I'm learning" ≤ 60s for a cold guest on source-less path.
>
> **Design law:** Every unit of learner effort must be immediately reflected as
> owned progress and answered with specific feedback — never with silence,
> emptiness, or a blank form again.
>
> **Ship-blocker:** Post-"Check my answer" silence or same-question re-prompt
> with empty composer (taste gate 2026-07-09).

---

## Problem (evidence)

Taste gate on `agent/student-first-moment` (2026-07-09, port 8002):

| Moment | Status |
| --- | --- |
| Door student copy ("Start session", write-first promise) | ✅ Improved |
| Source-less extract overlay | ✅ Shipped |
| Personalized first drill quoting cold attempt | ✅ Works |
| Post-check verdict + next step | ❌ Missing in live run |
| Desk/Library during in-progress session | ❌ Empty while sidebar has session |
| Two blank write gates (door → launch pad) | ⚠️ High bounce risk |

Soundboard consensus (Steve Jobs + Sal Khan personas, same PR picks):

1. Verdict strip + no same-question re-prompt
2. Collapse door + launch pad to one screen
3. Auto-open study after partial verdict

---

## Psychology → Product Rules

Derived from UX psychology research (smart defaults, goal gradient, reciprocity,
IKEA/endowment, loss aversion, contrast). **Socratink-compatible** forms only.

| Principle | Generic tactic | Socratink rule | Forbidden |
| --- | --- | --- | --- |
| **Smart defaults** | Pre-fill fields | Pre-structure the **guess**, not the answer. Topic may use editable example; cold area uses labeled stubs ("I think…", "I'm fuzzy on…"). | Pre-filling study content or model answers |
| **Goal gradient** | Never start at 0% | Count logged effort as progress: topic entered, guess saved, overlay steps, session on Desk/Library. | Fake mastery %, XP, streaks |
| **Reciprocity** | Give before ask | After each write/submit, return **specific** feedback within 2s. Guest signup only after value (drill + verdict). | Blurred results; signup before first personalized prompt |
| **IKEA / endowment** | Build before account | Show **their** map name, guess, session in sidebar/Desk/Library before sync. | Empty Library after active session |
| **Loss aversion** | Show cost of leaving | Guest: "This session stays in this browser." Mid-flow: don't lose repair moment. | Fake countdowns, streak loss |
| **Contrast** | Anchor first number | Door anchors vs ChatGPT: "You write first — then we show what you missed." | Absolute difficulty without context |

---

## PR Slices (implementation order)

### Slice A — Shipped (verify only)

**Branch:** `agent/student-first-moment` (partial)

| Change | Touchpoints |
| --- | --- |
| Student door/launch/drill CTAs | `public/index.html`, `public/js/drill-chamber.js`, `public/js/concept-page-view.js` |
| Source-less `mountExtractOverlay` | `public/js/launch-pad.js`, `public/js/app.js` (`mountExtractOverlay({ sourceLess: true })`) |
| SEDA verdict helpers (partial) | `public/js/app.js` (`sedaTurnVerdict`, `requestSedaTurn`), `public/js/drill-chamber.js` (`appendVerdict`) |

**Verify:** `tests/test_frontend_app_helper_modules.py` (launch pad overlay), e2e chamber copy, manual taste gate on worktree server.

---

### Slice B — P0: Post-check verdict loop (ship-blocker)

**Intent:** Reciprocity + post-drill contract. User must never submit an answer and get silence or a duplicate empty prompt.

#### B0. Route-ready gate

For a source-less Door session, the saved Door sketch is the graph-neutral
launch attempt. The chamber composer opens only after the loop returns the
versioned `sourceLessRoute` as `ready` and awaits `cold_attempt`. Raw loop events
are audit data, not a frontend routing API.

SEDA is the single authoritative route owner. The Door's `/api/extract` call
validates the non-empty sketch and persists only a deterministic,
learner-sketch-grounded shell (`route_owner: seda`, `graph_neutral: true`); it
does not call Learning Commons or generate a second model route. While SEDA is
working, the chamber shows `Preparing your first question…`, never the shell's
provisional prompt.

The shell marker is durable across reloads. A draft written after reload starts
SEDA route recovery, remains unsubmitted against the newly generated question,
and cannot fall through to `/api/drill`. If the pending shell already has
attempt or repair evidence, recovery fails closed and preserves the old node
keys instead of replacing them.

If the route is unavailable or malformed, keep the composer closed and append
no evidence. Tell the learner their starting sketch is saved. A fresh-route
action is allowed only while no evidence exists; otherwise return to the map
with existing evidence unchanged.

#### B1. Verdict strip (≤2s after submit)

Show inline below the active question / above composer (reuse `.drill-chamber__verdict`).
If the final evaluation is still in flight after 1.2s, show the neutral pending
strip `Answer received • Checking the link you wrote.`. Replace it with the
final verdict on success and clear it on error. Pending copy must not diagnose,
score, or reveal study content.

**Copy pattern** (wise feedback; strategy not ability):

```
Checked • {verdict_label} • {learner_line} • {controlled_next_step}
```

| Classification / SEDA signal | `verdict_label` | Body pattern |
| --- | --- | --- |
| strong / solid | `Solid enough to compare` | "Your line: {learner snippet}. Study will show what to add." |
| partial / thin | `Partly there` | "Your line: {learner snippet}. Study will target the missing link." |
| wrong_direction | `Wrong angle` | "Your line: {learner snippet}. Study will show a different starting point." |
| SEDA `continue` / repair keys | `Gap found` | "Study will target what you just exposed." |
| case complete | `Recorded` | "Your attempt is on record. Study is ready." |

**Rules:**

- Align with [`post-drill-ux-spec.md`](post-drill-ux-spec.md): no raw classifier badges; no score on cold path.
- Do **not** show tier/band on first cold-adjacent check unless product spec already allows for spaced path only.
- Verdict must reference **learner words** when `user_text` is available.
- Do not render raw event evaluation, agent response, gap, correction, score,
  or diagnostic prose before study reveal. Verdict language is controlled copy.
- `Recorded` and a study CTA appear only after the app has persisted the local
  attempt evidence. A projection failure keeps the same idempotent submission
  available behind a neutral `Try saving again` action.

#### B2. No same-question re-prompt

After a learner-submitted turn with a recorded verdict:

- **Forbidden:** `swapQuestion(same_text)` + empty composer.
- **Required:** Either (a) completion CTA, or (b) a **different** metacognitive prompt if another turn is needed.

If another prompt is required, prefix:

> "You wrote: «{snippet}». Now: {new_question}"

Never repeat the identical question string in the active prompt area after verdict.

#### B3. Primary CTA after verdict

| Condition | Button label | Action |
| --- | --- | --- |
| `caseComplete` or study-ready (`continue`, repair keys) | `See what to study` | `cancelDrill()` → concept page study mode / reveal path |
| In-progress SEDA, needs another turn | `Keep going` | Enable composer with **new** question only |
| Non-SEDA cold attempt recorded (`generative_commitment`) | `Reveal notes and compare` | Per `post-drill-ux-spec` primed state |

#### Technical touchpoints

| Area | Files |
| --- | --- |
| SEDA turn | `public/js/app.js` — `requestSedaTurn`, `sedaTurnVerdict`, `shouldOfferSedaStudyCta` |
| Non-SEDA drill | `public/js/app.js` — `requestDrillTurn` → `handleVisualTransition` |
| Chamber UI | `public/js/drill-chamber.js` — `appendVerdict`, `setCompletionAction` |
| Classification source | `/api/drill` response; SEDA session response `record.derived` |

#### Acceptance criteria

- [ ] After "Check my answer" with non-empty text, verdict strip visible within 2s (no silent spinner >3s without copy).
- [ ] Same prompt text does not reappear as empty active question after verdict.
- [ ] `See what to study` or `Reveal notes and compare` visible when routing permits study.
- [ ] `tests/e2e/test_smoke.py` or new e2e: launch → drill → submit → expects verdict element.
- [ ] Node contract test for `sedaTurnVerdict` / verdict copy mapping.
- [ ] POST-launch and GET-rehydrate responses expose the same versioned ready route.
- [ ] Missing/stale route recovery keeps the Door sketch and never replaces recorded evidence.

---

### Slice C — P0: Single-screen door (collapse launch pad)

**Intent:** Smart defaults + decision fatigue. One write surface before extract.

#### C1. Layout

Replace navigation `door → launch pad view` with **one screen**:

```
┌─────────────────────────────────────────┐
│ NEW SESSION                             │
│ {headline}                              │
│ {subhead — contrast vs instant AI}      │
│ ┌ topic field (short, max 200) ───────┐ │
│ ┌ cold guess (tall, max 1200) ────────┐ │
│ │ scaffold placeholder (see copy)     │ │
│ └─────────────────────────────────────┘ │
│ [Optional source attach]                │
│ footnote: one line only                 │
│ [Start session]                         │
└─────────────────────────────────────────┘
```

#### C2. Copy (binding)

| Element | Text |
| --- | --- |
| Headline | `What are you trying to explain?` (keep) |
| Subhead | `Write what you remember first. We'll show what to study — not a summary.` |
| Cold placeholder | `I think…\nI'm fuzzy on…\n(e.g. parts, guesses, confusions)` |
| Footnote | `You'll write first. Answers come after.` |
| CTA | `Start session` |

#### C3. Behavior

- `Start session` disabled until **both** topic and cold guess non-empty (trimmed).
- On submit: write `pendingShell` to sessionStorage (unchanged), call `/api/extract` with `startingSketch`, mount overlay **without** navigating to `#launch-pad-view`.
- Retire `#launch-pad-view` as separate nav step; keep `launch-pad.js` helpers or inline into `runHeroAction`.
- Telemetry: preserve `concept_create.door.submit` and `concept_create.launch_pad.submit` or merge into single event with `cold_len`.

#### Technical touchpoints

| Area | Files |
| --- | --- |
| HTML | `public/index.html` — merge launch pad into ignition form |
| Door submit | `public/js/app.js` — `runHeroAction` (source-less path) |
| Launch pad | `public/js/launch-pad.js` — extract submit path reused |
| CSS | `public/css/` — paper composer tall field on door |

#### Acceptance criteria

- [ ] No `#launch-pad-view` navigation on happy path.
- [ ] One click from filled form → overlay → concept/drill.
- [ ] E2E: `test_launch_pad_*` updated or replaced with `test_single_screen_door_*`.
- [ ] `agent-work` / guest path unchanged for source-attached door.

---

### Slice D — P0: Auto-open study after partial verdict

**Intent:** Goal gradient + reciprocity. Channel "partly there" into repair, not another blank drill.

#### D1. Trigger

When verdict is `Partly there`, `Gap found`, or `Wrong angle` **and** training record has `study_revealed_at` unset for active node:

1. Show verdict strip (Slice B).
2. Primary CTA: `See what to study`.
3. On CTA (or optional 1-tap auto after 1.5s if user setting allows — **default off**): call `revealStudyForEntry` / `cancelDrill` → concept page with study column unlocked per `post-drill-ux-spec` primed flow.

#### D2. Auto vs manual

| Mode | Behavior |
| --- | --- |
| **v1 (required)** | Manual tap on `See what to study` only |
| **v2 (optional)** | Settings toggle "Open study after check" — off by default |

Do not auto-navigate without learner tap in v1.

#### Technical touchpoints

- `public/js/app.js` — `revealStudyForEntry`, `cancelDrill`, `persistPhaseBResumeState`
- `public/js/concept-page-view.js` — primed / reveal CTA states

#### Acceptance criteria

- [ ] Partial verdict → tap `See what to study` → study material visible on concept page (not chamber).
- [ ] No study content before cold attempt recorded (doctrine).
- [ ] Training record shows attempt before `study_revealed_at`.

---

### Slice E — P1: Endowment surfaces (Desk + Library)

**Intent:** IKEA + goal gradient. Never show empty vault while session exists.

#### E1. Desk

- On launch-pad/extract submit (before graph returns): persist **stub concept** `{ name, state: 'growing', draftStatus: 'extracting', graphData: null }`.
- `renderDeskGrid`: tile state `extracting` (pulsing or legend `draft saved`).
- Replace stub with full concept when `persistCreatedConceptFromLaunchPad` completes.

#### E2. Library

- `showLibrary()`: include concepts where `graphData` OR `draftStatus === 'extracting'` OR any `training.node_records` attempt exists.
- Card summary: cold attempt excerpt (`getLibraryConceptMeta` already prefers learner attempt).
- Badge: `draft saved` not empty-state ignition.

#### Acceptance criteria

- [ ] During overlay wait, Desk shows named tile in extracting state.
- [ ] After cold attempt, Library lists session with learner text snippet.
- [ ] Empty ignition only when zero concepts in storage.

#### Touchpoints

- `public/js/launch-pad.js`, `public/js/app.js` (`showLibrary`, `renderGrid`)
- `public/js/library-view.js`, `public/js/board-grid.js`

---

### Slice F — P1: Copy diet (cut non-earning pixels)

**Intent:** Steve Jobs soundboard — remove lecture copy on door/launch.

| Remove / shorten | Keep |
| --- | --- |
| Duplicate footnotes across door and launch | One footnote line |
| Long helper paragraphs | Scaffold placeholder inside field |
| Process jargon in visible CTAs | `Start session`, `Check my answer`, `See what to study` |

Optional headline A/B (product pick one):

- `Write your first answer now. Get your custom drill in under a minute.`
- `Write what you think first. I'll show you exactly what to study.`

---

## Guest / signup reciprocity

| When | Ask |
| --- | --- |
| Before first personalized drill | Nothing (guest OK) |
| After verdict + study preview | `Save & Sync` soft prompt |
| Exit guest mid-session | Loss copy: "This session stays in this browser until you save." |

Never blur drill results behind signup.

---

## Metrics (funnel events)

Add or preserve telemetry:

| Event | When |
| --- | --- |
| `concept_create.door.submit` | Single-screen submit |
| `extract.overlay.shown` | `sourceLess: true` |
| `drill.first_personalized_prompt_shown` | Chamber shows quote of learner words |
| `drill.first_verdict_shown` | `appendVerdict` fires |
| `study.surface_opened` | After `See what to study` |

**Target:** >60% of guests who submit cold guess reach `drill.first_verdict_shown` without visiting empty Desk/Library.

---

## Test plan

| Layer | Commands |
| --- | --- |
| Unit | `.venv/bin/pytest -q tests/test_frontend_app_helper_modules.py -k "launch_pad or door"` |
| Node | `sedaTurnVerdict`, overlay mount, library filter with stub concept |
| E2E | `pytest tests/e2e/test_smoke.py -k "launch_pad or chamber"` (worktree server) |
| Manual taste gate | `http://localhost:8002` guest → photosynthesis path; screenshot folder |

---

## Implementation handoff (GPT 5.5 xhigh)

**Recommended order:** B → C → D → E → F (B is ship-blocker; C reduces bounce for everything after).

**Worktree:** `../socratink-app-student-first-moment` on `agent/student-first-moment`.

**Before coding:**

```bash
agent-work guard .
```

**Canon to re-read:**

- `docs/product/first-session-momentum-spec.md` (this file)
- `docs/product/post-drill-ux-spec.md` (primed / needs repair copy)
- `DESIGN.md` § generation-before-recognition
- `UBIQUITOUS_LANGUAGE.md` (cold attempt, targeted study, not "quiz")

**Do not:**

- Record mastery from reading or verdict copy alone
- Show study before cold attempt
- Add streaks, XP, or fake progress %
- Re-introduce `Build draft route`, `Save first model`, `Check reconstruction` as visible labels

---

## References

- Taste gate screenshots: `/tmp/socratink-taste-gate/` (2026-07-09)
- Partial implementation: `agent/student-first-moment` slice A
- Post-drill canon: [`post-drill-ux-spec.md`](post-drill-ux-spec.md)
- Evidence doctrine: [`evidence-weighted-map.md`](evidence-weighted-map.md)
