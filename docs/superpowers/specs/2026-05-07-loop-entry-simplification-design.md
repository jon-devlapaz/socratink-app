# Loop entry simplification — design spec

**Status: SUPERSEDED 2026-05-07 by `2026-05-07-progressive-route-materialization-design.md`.**

This spec is preserved as provenance, not as guidance. Do not implement from this file.

**Why it was superseded.** This spec proposed concept-name-only full-graph generation when no source is attached. That violates the learner-seeded route contract from `docs/product/spec.md` and principle #7 of the deferred 2026-05-02 spec: a graph drafted from the model's prior knowledge alone, even with the right framing copy, is the *hallucinate-and-present* anti-pattern this product categorically rejects. The customer-persona feedback that motivated this spec ("one input at the door, no preaching") is real and still valid, but the simplification it pointed to crossed a doctrinal line. The successor spec preserves the persona insight (door is concept-only) while preserving doctrine (no full-graph generation from concept name alone — first entrance captures a learner threshold, then the system generates only a smallest actionable route).

The mechanical corrections in this file (route is `POST /api/extract` not `/concepts`; URL source two-steps through `/api/extract-url`; source panel lives in `concept-create.js::beginEditSource` and would need extraction) carry forward unchanged into the successor spec.

---

# Loop entry simplification — design spec (original draft, superseded)

**Date:** 2026-05-07
**Status:** Brainstorm complete; ready for plan + implementation
**Author:** Brainstormed with Claude, customer-persona pressure-test via Gemini, decisions made by jon-devlapaz
**Supersedes (deferred):** `docs/superpowers/specs/2026-05-02-conversational-concept-creation-design.md` is **deferred**, not torn up. Its premise — that loop entry should be a two-turn AI chat → summary card — is parked behind the simpler form-first MVP this spec defines. The conversational ignition surface is reconsidered after dogfood telemetry tells us whether the form is actually friction.

---

## 1. Why this exists

The current Ignition view (`public/index.html` lines 279–328) is a form with two textareas (Concept + Starting sketch), an eyebrow ("Start here"), a title, a voice line, a descriptive paragraph, and a "Create draft path" submit. It is overwrought as the door to the core game loop.

A customer-persona pressure-test (Gemini, college-sophomore persona, anti-cramming / anti-AI-tutor) returned a sharp verdict: **the screen is preaching before the user has earned the right to be preached to.** The persona explicitly rejected the conversational ignition the 2026-05-02 spec binds. They wanted: one input, optional source attach, plain language, get out of the way.

The dogfood goal is to shrink the door so the founder (and any future learner) can sit down, dump a topic, and be in the loop within ~10 seconds. Everything that is not "topic in, graph out" is fat.

## 2. Binding principles

> **The door in three lines:**
>
> - **One input** for the concept name.
> - **One optional affordance** for source material.
> - **One commit action** that names the next state ("Build my map").
>
> No eyebrow. No voice line. No "starting sketch" field. No "draft path" jargon.

1. **One cognitive target per screen.** The entry screen has exactly one job: capture what the learner wants to understand. Anything else competes with that job.
2. **Sketch is captured at cold attempt, not at entry.** The starting-map textarea is removed from the entry screen. The first cold attempt on the root node is where the learner externalises their current model. Asking twice (once at the door, once at the first node) is generation fatigue (`docs/product/starting-map-flow-artifact.md` §Friction Fixes).
3. **No philosophy at the door.** The voice line ("The map stays honest because evidence comes from your reconstruction") is removed from the entry screen. If it earns a place anywhere, it is in the empty-graph state (deferred decision).
4. **Source attach stays on the screen.** It is a small ghost affordance, not a chip, not a wizard. Source-less generation remains the default path; source is optional evidence.
5. **The honest-seed contract is preserved.** Source-less generation requires *something* substantive. With the sketch field removed from the entry screen, the substantiveness check shifts to the first cold attempt on the root node. See §3.3 for the revised gate.

## 3. The flow

Two stages now (was three). The summary-card stage from the deferred 2026-05-02 spec is removed entirely.

### 3.1 Stage A — entry screen

```
                    What do you want to understand?

         ┌────────────────────────────────────────────────────┐
         │ e.g. photosynthesis, the Krebs cycle, recursion    │
         │ in Python…                                         │
         └────────────────────────────────────────────────────┘

                          + add source material

                          [ Build my map → ]
```

**Layout.**

- Vertically centered in the existing `ignition-view` shell. The intro-particles canvas (`#intro-particle-canvas`) stays.
- Title `What do you want to understand?` — `<h1 class="ignition-title">`. Reuse existing typography.
- Concept input — single textarea, 2 rows (allows a longer phrase but visually reads as a line), `maxlength="200"`, placeholder `e.g. photosynthesis, the Krebs cycle, recursion in Python…`. Reuses `hero-single-input__field--concept` styling.
- Source-attach affordance — small ghost button below the input: `+ add source material`. Click expands the existing source panel (`SourceMaterialPanel` from 2026-05-02 spec §4.2 — the Text/URL/File tabs component) inline below the input. No tabs row at rest.
- Submit — `Build my map` with the existing arrow icon. Reuses `hero-single-input__submit` styling.

**Removed from this screen.**

- `ignition-eyebrow` ("Start here")
- `hero-voice-line` ("The map stays honest…")
- `hero-guidance` descriptive paragraph
- `hero-threshold-field--sketch` textarea + label (the entire "Starting sketch" field)
- `hero-threshold-validation` (replaced — see §3.3)
- The `hero-state-chip` chip group at the top of the hero-info block, on this screen only (the home/desk view keeps its chip behaviour)

**Validation (entry screen).**

- `Build my map` is enabled when the concept input is non-empty after trimming. That is the only client-side gate on this screen.
- The substantiveness check that previously gated the sketch field moves to the first cold attempt (§3.3). The entry screen does not block on sketch quality because it no longer captures sketch.

**Library cap gate.** Unchanged from current behaviour. When the board is at 9 concepts, the `ignition-cap-gate` panel renders in place of the input and the input is hidden (today's `renderIgnitionGate()` logic). Copy unchanged: `The board holds nine concepts. Retire one to start another.`

### 3.2 Stage B — graph generation

Triggered by `Build my map`. Backend dispatches based on source-attachment state at submit time.

**3.2.1 Source attached.** Existing `extract_knowledge_map` pipeline. No change.

**3.2.2 No source attached.** New backend path. The 2026-05-02 spec defined `generate_provisional_map_from_sketch(concept, sketch, lc_context=None)`. With the sketch field removed from the entry screen, the signature changes:

```python
def generate_provisional_map_from_concept(
    concept: str,
    lc_context: list[StandardDescription] | None = None,
) -> ProvisionalMap:
    ...
```

The AI hypothesises a provisional map structure from the concept name alone. Learning Commons enrichment gates per 2026-05-02 spec §3.3.2 still apply — score floor, K-12 confidence, etc. — and the generation prompt at `app_prompts/generate-from-concept-system-v1.txt` (renamed from `generate-from-sketch-system-v1.txt`) drops the sketch input.

The provisional-graph framing copy (DESIGN.md §3 Screen 2) is unchanged: *draft route · ready for first attempt · locked.*

### 3.3 Where the substantiveness gate moves

The 2026-05-02 spec required a substantive sketch OR attached source as the seed for source-less generation. With the sketch field removed, the seed for source-less generation is *just the concept name*. That weakens the seed.

The compensating move: **the first cold attempt on the root node carries the substantiveness check that used to live at the door.**

- The root node opens in `cold_attempt` phase per existing flow.
- The cold-attempt composer enforces the existing cold-attempt threshold per `docs/product/spec.md` §2 Phase 1: *"Generative Commitment: Requires a minimum threshold (3+ words, no 'idk') to unlock study."* This is the gate that already lives in the product. The 2026-05-02 spec's stricter `≥8 non-stopword tokens` heuristic for the sketch field is **not** carried forward — that heuristic was specific to the sketch-as-seed contract this spec deletes.
- If the learner enters `idk` at the root node's first cold attempt, the existing zero-schema detection (spec §2 Phase 1) seeds 2-3 concepts and asks for a micro-generation. Same product contract as today.

**Net effect on principle #7 (no hallucinate-and-present).** The provisional graph from concept-name-only generation is *more hypothesis-shaped* than one drafted from sketch + concept. The framing copy (`draft route · ready for first attempt`) already reflects that. The graph never updates state until the cold attempt provides evidence. The honest-seed contract holds because:

- The graph is presented as hypothesis, not fact.
- Node state (`primed`, `drilled`, `solidified`) only mutates from learner-generated evidence.
- The first cold attempt is where the learner's model meets the hypothesis. Substantive cold attempt → `primed`. Non-attempt → no mutation, micro-generation scaffold.

This is a deliberate trade: lose some seed quality on the provisional graph in exchange for radically lower friction at the door. The bet is that learners who get into the loop fast will encounter the same model-externalisation demand at the cold attempt and respond there, rather than abandoning at the door because the door asked too much.

## 4. What changes — frontend

### 4.1 Files touched

- `public/index.html` lines 279–328 (the `ignition-view` section): remove eyebrow, voice line, sketch field; restructure the form.
- `public/css/components.css`: remove `.hero-threshold-field--sketch` styles; adjust `.hero-threshold-fields` to single-field layout; add ghost-button style for `+ add source material`; ensure `.ignition-eyebrow` is either removed entirely or class-styled but unused on this screen.
- `public/js/app.js`:
  - `runHeroAction()` (or wherever the entry-screen submit handler lives): drop the sketch payload field; pass `{name, source}` to the create-concept call.
  - The source-attach panel toggle: new lightweight expand/collapse on the source affordance.
  - `renderIgnitionGate()` cap-gate logic: unchanged.

### 4.2 Source attach behaviour

The 2026-05-02 spec defined `SourceMaterialPanel` as a chip-expanded inline panel. Reuse that component, mounted under the entry screen's input rather than inside a chip. Same Text/URL/File tabs, same paste/clipboard/file/url handlers.

States:

- **Collapsed (default):** ghost button `+ add source material` shows below the input.
- **Expanded:** the source panel renders inline; the ghost button becomes a `× cancel source` action that collapses back to default.
- **Source attached:** the ghost button becomes a chip-style summary `Source: notes.md · 2,108 chars` with a `replace` action.

### 4.3 Home / Desk view (separate from entry screen)

Open decision in §6. The current home view (`hero-card.intro-page`) carries the `hero-state-chip` ("no map yet"), title ("Your draft paths."), guidance ("Pick a tile to open an entry, or start a new draft path at New Entry."), voice line, and `hero-primary-action` ("Begin at New Entry").

Persona feedback flagged the "draft path" jargon as eye-rolling and pretentious (decision 4: "drop it entirely"). That cleanup is **in scope** for this spec but the exact replacement vocabulary ("Your concepts" vs "Your library" vs other) is **deferred** — see §6.

What is locked:

- "Begin at New Entry" → `New concept` (verb-led, plain).
- The "draft path / draft paths" string is removed from the home view title and guidance.

What is deferred to §6:

- The replacement noun for the home view title and the empty-state chip.
- Whether the voice line ("The map stays honest…") earns a place in the empty-graph state, the home view, or is removed entirely.

### 4.4 What stays from the 2026-05-02 spec

Even though the chat → summary-card flow is deferred, two artefacts from that spec are reused:

- The `SourceMaterialPanel` component (Text/URL/File tabs) — repurposed as the inline source-attach panel on the entry screen.
- The endpoint contract `POST /concepts` with `source: null | {...}` — minus the `starting_sketch` field, since sketch is no longer a payload.

## 5. What changes — backend

### 5.1 Generation path

Module: `ai_service.py` or successor.

```python
def generate_provisional_map_from_concept(
    concept: str,
    lc_context: list[StandardDescription] | None = None,
) -> ProvisionalMap:
    ...
```

Returns the same `ProvisionalMap` Pydantic model. Validation rules from the foundation spec (`2026-05-01-foundation-design.md` §5.1) apply unchanged.

New prompt at `app_prompts/generate-from-concept-system-v1.txt`. The prompt describes the cognitive task ("hypothesise a provisional concept map for a learner who provided only a concept name"), the output schema (same as `extract-system-v1.txt`), and the role of `<lc_context>` when present.

The 2026-05-02 spec's `app_prompts/threshold-chat-system-v1.txt` is **not built** in this spec (chat is deferred). It can be created later if the conversational ignition is revived.

### 5.2 Learning Commons client

Unchanged from 2026-05-02 spec §5.2. `LCClient`, threshold gate, score floor, K-12 confidence, telemetry skips. The four-gate logic carries over verbatim.

### 5.3 Endpoint shape

```jsonc
POST /concepts
{
  "name": "Photosynthesis",
  "source": null  // or { "type": "text"|"url"|"file", "text": "...", "url": "...", "filename": "..." }
}
```

The `starting_sketch` field is removed. The 2026-05-02 spec's server-side substantiveness check on `starting_sketch` is removed from this endpoint. No equivalent gate is needed at this endpoint — the gate moves to the cold-attempt endpoint (existing).

Validation (server-side):

- `name` empty/whitespace-only → `422` with `{"error": "missing_concept", "message": "Concept name required."}`.
- That's it.

### 5.4 Telemetry

Reduced from 2026-05-02 spec §5.4. Events kept:

- `concept_create.submit` — `{has_source, source_type}` (new, replaces the chat/summary events)
- `concept_create.lc.queried` — unchanged
- `concept_create.lc.enrichment_applied` — unchanged
- `concept_create.lc.enrichment_skipped` — unchanged
- `concept_create.ai_call` — `{stage, model, tokens_in, tokens_out, latency_ms, cost_usd_est}`. `stage` is one of: `generation_pure`, `generation_lc_enriched`. (The `chat_turn_2_probe`, `chat_fallback`, and `summary_extract` stages are deferred with the chat surface.)

Events dropped (return when chat ships):

- `concept_create.chat.*`
- `concept_create.summary.*`
- `concept_create.source.added` (replaced by the `has_source` flag on `submit`)
- `concept_create.build_blocked` (no client-side substantiveness gate at the door any more; the equivalent gate at cold attempt has its own telemetry)

## 6. Open decisions for implementation

These must be resolved before the implementation plan lands, but do not block writing the plan.

1. **Home / Desk view vocabulary.** Replace "Your draft paths." (title) and "no map yet" (chip) and "draft path" (guidance copy). Candidates: *Your concepts* (plain, matches the data), *Your library* (on-voice for reading-room register, earns its keep once populated). Lean — `Your concepts` for dogfood-of-one with an empty board; `Your library` may earn its place once the board has a few. Decide before frontend implementation.
2. **Voice line placement.** "The map stays honest because evidence comes from your reconstruction." Candidates: deferred to empty-graph state inside a concept (after build, before first cold attempt), kept on the home/desk view in a quieter slot, or cut entirely. Lean — quieter placement on the empty-graph state when a learner enters a freshly-built concept; *not* on the entry screen, *not* on the home view.
3. **Concept input field shape.** 2-row textarea (allows longer phrase, ambiguous "is this multi-line?") vs single-line input (clearer affordance, harder to paste a longer prompt). Pick during implementation; either is fine.

## 7. Out of scope (deliberate non-goals)

- The conversational ignition (chat → summary card) from the 2026-05-02 spec. Deferred. Revisit after dogfood telemetry signals whether the simpler form is enough.
- The `starting_sketch` payload field. Removed from the entry endpoint. The product still captures the learner's starting model — at the first cold attempt, where it always belonged.
- Any "tell me more about your goals" intake, learning-style picker, or onboarding wizard.
- Re-introducing the fuzzy-area input. (The 2026-05-02 spec already removed it; this spec keeps it removed.)

## 8. Acceptance criteria

The simplification ships when **all** of these hold:

1. The entry screen renders with: title, concept input, source-attach affordance, submit button. No eyebrow, no voice line, no descriptive paragraph, no sketch field.
2. A learner can enter a concept name, click `Build my map`, and land on a provisional graph within current latency budget. No source attached. No sketch asked.
3. A learner can attach source material (text/URL/file) inline on the entry screen, click `Build my map`, and land on a provisional graph. Source-attached behaviour matches today's extract pipeline.
4. The `starting_sketch` field is gone from the payload, the form, and the validation. `is_substantive_sketch` is no longer called from the create-concept endpoint.
5. The first cold attempt on the root node still enforces the substantiveness threshold per `docs/product/spec.md` §2 Phase 1 (existing behaviour, verified unchanged).
6. The home/desk view no longer renders the "draft path" / "draft paths" string. The replacement vocabulary is implemented per §6.1's resolution.
7. `bash scripts/qa-smoke.sh` passes against a deploy preview.
8. **Browser smoke (load-bearing per `feedback_browser_smoke_is_load_bearing.md`).** Manually open the entry screen at the dev server, submit a concept with no source, submit a concept with source attached, verify both flows reach the graph view without console errors and without global-CSS regressions on related screens. Screenshots attached to the PR.
9. Visual smoke: dark-mode and light-mode screenshots of the entry screen at rest, with source panel expanded, with source attached. Attached to the PR.

## 9. Implementation sequencing (handoff to writing-plans)

1. **Backend first.** Rename `generate_provisional_map_from_sketch` → `generate_provisional_map_from_concept`; drop the `sketch` parameter; update prompt at `app_prompts/generate-from-concept-system-v1.txt`. Drop `starting_sketch` from the endpoint payload + server-side validation. Test with curl. The LC client is reused as-is.
2. **Frontend HTML/CSS.** Strip the entry screen down per §3.1 and §4.1. Remove eyebrow, voice line, sketch field, descriptive paragraph. Add the `+ add source material` ghost affordance. Reuse `SourceMaterialPanel` mounted inline.
3. **Frontend JS.** Update `runHeroAction()` payload; wire source-attach toggle; verify cap-gate still renders correctly.
4. **Home/Desk view copy.** Replace "draft path" / "draft paths" strings per §6.1's resolution. (This blocks on §6.1 being decided.)
5. **Telemetry.** Strip the chat/summary events from the dispatcher; keep LC + ai_call events.
6. **Bindings docs.** Update DESIGN.md §3 Screen 1 to reflect that threshold capture has moved from a form field to the first cold attempt on the root node. Add a note pointing to this spec.

## 10. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Concept-name-only generation produces weaker provisional graphs than sketch-seeded generation. | The graph is framed as hypothesis (DESIGN.md §3 Screen 2 unchanged). The cold attempt + repair loop catches and repairs structural mistakes. The entry screen does not promise correctness. The trade is accepted explicitly: lower door friction in exchange for marginally weaker seed. |
| The 2026-05-02 spec's substantiveness contract appears violated at the door. | The contract moves, not removed. The cold attempt on the root node enforces the same `is_substantive_sketch` heuristic per `docs/product/spec.md` §2 Phase 1. Principle #7 of the 2026-05-02 spec ("no hallucinate-and-present") is preserved because the graph is hypothesis until learner-generated evidence mutates state. |
| Source attach on the entry screen feels like a mode switch / wizard. | The affordance is one ghost button. The panel only appears when the learner clicks it. Default state is one input + one button. Persona-tested as the simplest viable shape. |
| Removing "draft path" jargon costs the brand register. | The register lives in copy across the rest of the product (study artifact, repair history, spaced re-drill, library, the empty graph state). The entry screen is not the place to carry register; it is the place to capture intent. Lose the register here, keep it where it earns its weight. |
| Re-introducing the chat later is harder than building it now. | The `SourceMaterialPanel` is reused. The endpoint contract is forward-compatible (chat output produces `{name, sketch, source}`; the current spec just stops collecting `sketch`). When chat is revived, the additional layer plugs in above the existing entry screen, not in place of it. |

---

## Appendix A — Brainstorm provenance

Decisions made during the brainstorm session, in order:

1. Friction diagnosis (Claude → user): two fields too many, copy overwrought, frame slightly wrong.
2. Customer-persona pressure-test via Gemini using the template at `docs/codex/customer-persona-prompt-template.md`. Persona converged on D + B + B + B with the final note: *"reject the urge to explain the app's philosophy to me before I've even used it."*
3. User decision: bias toward Gemini feedback, defer the conversational ignition spec, keep source attach on the screen, agree with cutting fat.
4. Open decision parked: home/desk view replacement vocabulary (§6.1).

## Appendix B — Anti-patterns this spec deliberately rejects

- Re-introducing the "starting sketch" field on the entry screen "for users who want to provide more context." The honest path is: capture sketch at the cold attempt, where the learner is generating against a specific node anyway.
- Adding a second screen between the entry and the graph (loading spinner with "preparing your draft path…" + voice copy). The current loading state is fine; it does not need decoration.
- Promoting source material to a required field. Source remains optional evidence.
- A "popular concepts" suggestion list under the input. That is recognition-flavored content; it dilutes the generative demand the very next screen makes.
- Auto-completing the concept name from a list of curriculum standards. Same anti-pattern — recognition substituting for generation.
- Re-introducing the voice line on this screen "in a quieter style." Persona was explicit: no philosophy at the door.
