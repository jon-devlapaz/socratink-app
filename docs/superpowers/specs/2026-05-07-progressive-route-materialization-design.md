# Progressive route materialization — design spec (C-prime)

**Date:** 2026-05-07
**Status:** Brainstorm complete; ready for plan + implementation
**Author:** Brainstormed with Claude, two rounds of customer-persona pressure-test via Gemini, two rounds of doctrinal correction via Codex, decisions made by jon-devlapaz

**Relation to other specs.**

- **Supersedes:** `docs/superpowers/specs/2026-05-07-loop-entry-simplification-design.md` (proposed concept-name-only graph generation, which violated the learner-seeded route contract).
- **Defers:** `docs/superpowers/specs/2026-05-02-conversational-concept-creation-design.md` (the conversational chat → summary card surface).
- **Aligns with:** `docs/product/starting-map-flow-artifact.md` (canonical happy path: Concept Threshold → Provisional Graph → First Cold Attempt). This spec is a faithful implementation of that artifact.
- **C-prime refinement** of an earlier draft of this same file. The architecture survived the second persona round and the second codex review unchanged. The implementation got smaller: route generation is **stateless**, no new persisted creation-phase column, in-flight shell state lives in `sessionStorage`, and the resulting artifact is **ProvisionalMap-compatible** (not a new Pydantic model). Persona-driven copy refinements were absorbed.

---

## 1. Why this exists

The current Ignition view (`public/index.html` lines 279–328) is a form with two textareas (Concept + Starting sketch), an eyebrow, a voice line, a descriptive paragraph, and a "Create draft path" submit. Customer-persona pressure-test (Gemini, college-sophomore) returned: *"reject the urge to explain the app's philosophy to me before I've even used it… get out of my way."*

The instinct to remove the sketch field from the door entirely (the persona's literal preference) crossed a doctrinal line: a graph drafted from concept name alone is the AI's prior knowledge dressed as the learner's draft — the *hallucinate-and-present* anti-pattern principle #7 of the 2026-05-02 spec categorically forbids.

The persona's second-round push was: *"skip screen 2 entirely. Door → small map → cold-attempt-as-threshold."* Codex rejected raw path (c) — a 1-node-plus-thesis launch pad generated from concept name alone is still concept-name-only generation; collapsing threshold and cold attempt loses canon's distinction; smuggling progressive expansion into v1 boils the ocean.

**C-prime is the resolution.** It preserves the persona's spirit (door is one input, no preaching, no AI generation before learner-authored seed) while preserving doctrine (no graph or thesis from concept name alone; threshold remains a distinct surface; the launch attempt mutates no node state).

The dogfood goal: a learner sits down, dumps a topic, lands on a "launch pad" surface that asks them to dump what they already think, and is in the cold-attempt loop within ~10–20 seconds.

## 2. Binding principles

> **The door in three lines:**
>
> - **Concept name** is the only required field at the door.
> - **Source material** is optional. If attached, today's full-graph extraction path runs.
> - **No graph, no thesis, no AI-generated artifact of any kind from concept name alone.** Source-less concepts pass through a launch pad that captures a learner-authored launch attempt before any model call.

1. **One cognitive target per screen.** The door captures intent (the concept). The launch pad captures the learner's starting model. Each screen has one job.
2. **No provider-prior generation from name alone.** No graph. No core thesis. No "core thesis + one node placeholder." Nothing the model produces from the concept name without a learner seed gets shown to the learner. Codex was explicit: *"no generated core thesis from concept name alone."*
3. **The launch attempt is threshold capture, not the first cold attempt.** Per `starting-map-flow-artifact.md` truth table: threshold capture mutates no node state. The launch attempt is *global* (rough whole-concept model). The first cold attempt is *local* (one mechanism inside one node), fires after the route renders, and carries the existing `locked → primed` mutation.
4. **Smallest actionable route, ProvisionalMap-compatible.** The artifact returned from `{concept, threshold}` generation is a `ProvisionalMap` (the existing Pydantic model, used today for source-attached extraction). It is constrained at the wire level to ≤4 drillable nodes total: a suggested first target (which carries the core thesis as its display name and is the node the first cold attempt fires against) plus at most 3 backbone hints. No new Pydantic model. No cluster lattice.
5. **No progressive expansion logic in v1.** The route exists or it does not. Mechanisms for the route to grow after cold-attempt evidence, repair events, source attachments, or other learner signals are deferred. v1 ships the smallest route as a terminal artifact for this spec.
6. **Source-attached path is unchanged.** Asymmetry acknowledged: source-attached → full ProvisionalMap (existing `extract_knowledge_map` pipeline); source-less → smallest ProvisionalMap (new generation path, same model). v1 lives with this. Convergence is a future call.
7. **Stateless route generation; sessionStorage holds in-flight state; client owns persistence.** `/api/extract` is stateless — given `{concept, threshold}` it returns a `ProvisionalMap` in the existing response shape and persists nothing server-side. The "shell" (concept name committed at the door, no threshold yet) lives only in `sessionStorage`. After the server returns a smallest route, the frontend persists the resulting concept through the existing client-side concept-store path; only after that client persistence succeeds is the pending-shell key cleared. v1 adds no `creation_phase` column. If the learner closes the tab on the launch pad, the in-flight shell evaporates — that is acceptable for v1.
8. **`/api/extract` must reject name-only/source-null bypasses.** Server-side validation enforces principle #2 at the wire. A request with no source AND no substantive `starting_sketch` is rejected with `422`. This is non-optional; it is the only thing standing between principle #2 and a buggy/old/malicious client triggering provider-prior generation.

## 3. The flow

Three stages. The third (cold attempt) is the existing product loop and not redesigned here.

### 3.1 Stage A — door (concept entry)

```
                    What do you want to understand?

         ┌────────────────────────────────────────────────────┐
         │ e.g. photosynthesis, the Krebs cycle, recursion    │
         │ in Python…                                         │
         └────────────────────────────────────────────────────┘

                          + add source material

                                  →
```

**Layout.**

- Vertically centered in the existing `ignition-view` shell. The intro-particles canvas (`#intro-particle-canvas`) stays.
- Title `What do you want to understand?` — `<h1 class="ignition-title">`. Reuse existing typography.
- Concept input — single textarea, 2 rows, `maxlength="200"`, placeholder `e.g. photosynthesis, the Krebs cycle, recursion in Python…`. Reuses `hero-single-input__field--concept` styling.
- Source-attach affordance — small ghost button below the input: `+ add source material`. Click expands the source panel inline. (The panel itself requires extracting the existing `beginEditSource` from `concept-create.js`; see §6.2.)
- Submit — **arrow icon only, no visible word.** Persona was explicit on the second round: *"kill `Continue`, just use an arrow icon and no word. The arrow alone is enough; the word adds nothing."* Reuses `hero-single-input__submit` styling with the existing arrow SVG, no visible label.
  - **Accessibility:** the button MUST carry a non-empty accessible name. Use a visually-hidden label (`<span class="sr-only">`) reading *"Continue to launch pad"* (when no source attached) or *"Build map from source"* (when source is attached) — or, if the dynamic copy is more cost than benefit, a static `aria-label="Continue"` on the button. Both keyboard and screen-reader users must hear what pressing the button does. A bare-icon button with no accessible name fails WCAG 4.1.2 and is a release-blocker.

**Removed from this screen.**

- `ignition-eyebrow` ("Start here")
- `hero-voice-line` ("The map stays honest…")
- `hero-guidance` descriptive paragraph
- `hero-threshold-field--sketch` textarea + label (the entire "Starting sketch" field — moves to the launch pad)
- `hero-threshold-validation`

**Validation.** Submit is enabled when the concept input is non-empty after trimming.

**Library cap gate.** Unchanged from current behavior.

**Submit branches.**

| State at submit | Action | Persisted? | Next screen |
|---|---|---|---|
| Source attached (text/file) | `POST /api/extract` (today's path) with `{name, source, starting_sketch: null}` | Yes (full concept created) | Existing post-extract flow → graph view |
| Source attached (URL) | `POST /api/extract-url` then `POST /api/extract` with returned text | Yes (full concept created) | Existing post-extract flow → graph view |
| No source | Save `{name, ts}` to `sessionStorage` under key `socratink:pendingShell`. Navigate to launch pad. | **No** (sessionStorage only) | Launch pad (Stage B) |

The URL two-step is enforced by today's backend (`main.py:336–342` rejects URL source on `/api/extract` with *"URL sources go through /api/extract-url"*). v1 preserves this contract verbatim.

### 3.2 Stage B — launch pad (threshold capture for source-less concepts)

Only reached when no source was attached at the door. Reads the pending concept name from `sessionStorage`. Source-attached concepts do not see this screen.

```
                              [concept name]

                       What do you already think is
                          inside this concept?

  Name the parts, guesses, examples, or confusions you have.

         ┌────────────────────────────────────────────────────┐
         │                                                    │
         │                                                    │
         │                                                    │
         └────────────────────────────────────────────────────┘

                          [ Build my map → ]
```

**Layout.**

- New surface, sibling to `ignition-view`. Lives in `public/index.html` as a new `<section class="primary-view launch-pad-view">`. Visual register matches the door (calm, single-input).
- Concept name renders at the top (reads as a header, not a chip).
- Title and helper line are taken **directly from `starting-map-flow-artifact.md` Screen 1 safe-copy** rather than freshly written. Persona round 2 was explicit: *"'Show me your starting map' sounds slightly precious… don't make me feel like I'm being led through a corporate design thinking workshop."* The canonical safe-copy *"What do you already think is inside this concept? Name the parts, guesses, examples, or confusions you have."* is on-voice, anti-precious, and already binding-doc text.
- One textarea, multi-row (5 rows), `maxlength="1200"`. Reuses existing sketch-field styling.
- Submit — `Build my map` with arrow icon. (The word stays here, unlike the door, because this *is* the build commit point.)

**No back-to-door affordance in v1.** If the learner wants to re-enter the concept, they cancel out and start over. The pending shell in `sessionStorage` is cleared on either successful build or explicit cancel.

**Pending shell hydration.** On mount, the launch pad reads `socratink:pendingShell` from `sessionStorage`. If absent or stale (>24h), the user is bounced back to the door — the launch pad cannot be visited directly without a pending shell.

**Validation.** `Build my map` is enabled when the threshold input meets the existing cold-attempt threshold per `docs/product/spec.md` §2 Phase 1: *3+ words, no "idk" pattern.* This is the existing product gate.

**Validation copy when blocked.** Strategy-framed footer line: *"A few words about how you think it works will give socratink something to draft from."* Never consolation copy.

**Submit behavior.** `POST /api/extract` with `{name, starting_sketch: <threshold>, source: null}`. The endpoint is **stateless**: the server runs smallest-route generation (see §5.1) and returns the `ProvisionalMap` in the existing `/api/extract` response shape. The server does **not** persist the concept. The frontend takes the response, persists the concept locally (the existing client-side concept-store path), and only after that client persistence succeeds clears `sessionStorage` of the pending shell and navigates to the graph view. On `422` (server-side substantiveness rejection), the frontend shows the same strategy-framed footer line — no toast. On any failure during client persistence, the pending shell stays in `sessionStorage` so the learner can retry without re-typing.

### 3.3 Stage C — first cold attempt (existing flow, unchanged)

Once the route renders, the existing graph view is shown. The suggested first target appears in `cold_attempt` phase. The learner's cold attempt against that node fires the existing `locked → primed` mutation.

**The route screen carries one new framing line.** Persona round 2: *"If the screen just loads with three nodes, I'll think the app is broken. Put a tiny line of text that says: 'This is the skeleton. It expands as you prove what you know.'"* This copy lands on the route view itself, not on the launch pad. Exact wording for v1: *"This is the skeleton. It will grow as you reconstruct."* (Tightened slightly to match the product's reconstruction-evidence framing — "reconstruct" carries the load-bearing meaning; "prove what you know" is too transactional.)

This line is the only piece of voice copy on the post-launch view that wasn't there before. Everything else (graph rendering, cold-attempt UI, node states) is unchanged from today's behavior.

## 4. State model

### 4.1 No new persisted field in v1

v1 deliberately does not add a `creation_phase` column to the concept record. Codex's guidance round 2: *keep concept shell / creation phase in client storage for v1; make route generation stateless with {concept, threshold}.* Codex's guidance round 4 sharpened this: pending-shell state belongs in `sessionStorage` (tab-scoped, evaporates on tab close, no cross-tab overwrite); the resulting concept (after the route is returned) is persisted through the **existing client-side concept-store path** — `/api/extract` itself stays stateless, returning the map with the existing response shape and persisting nothing server-side.

There is no new `shell` row, no `seeded` row, no creation-phase field anywhere — neither client-side nor server-side. Concepts on the home/desk view are exactly today's concept-store records, with no lifecycle markers added.

### 4.2 In-flight state in `sessionStorage`

The browser holds the only record of the in-flight shell during the door → launch pad → build window:

```
key: socratink:pendingShell
value: { name: string, ts: number /* unix ms */ }
```

Lifecycle:

- **Set** when the learner submits the door with no source attached.
- **Read** by the launch pad on mount. If absent or `ts > 24h ago`, navigate the learner back to the door (no orphaned launch pad sessions).
- **Cleared** on successful `201` from `/api/extract` after launch attempt, OR on explicit cancel of the launch pad.

Acknowledged v1 limitation: closing the tab on the launch pad evaporates the pending shell. The learner re-enters at the door. This is acceptable because:

- The work invested at this point is one concept name (low cost to re-type).
- The threshold textarea is what carries cognitive load; it has not been submitted yet, so re-typing the concept name is not blocking the threshold from being captured.
- v1 is a dogfood ship; multi-device or multi-tab launch resumption is not a v1 concern.

If dogfood telemetry shows learners regularly losing pending shells in non-trivial ways, server-side persistence of the shell row gets revisited in a follow-on spec.

### 4.3 Implications for the home / desk view (library)

Because shells are not persisted server-side in v1, the home/desk view does **not** show shell tiles. Only concepts that have been built (either via source extraction or via launch-attempt → smallest-route generation) appear in the library.

This removes the "mixed-state library" design pressure entirely. There is no shell-vs-routed-vs-mapped tile rendering decision in v1. All tiles are full-concept tiles (today's behavior, unchanged).

### 4.4 Vocabulary — home/desk view

Persona has voted twice across two rounds for *"Your concepts"* over *"Your library"* (round 1 decision 4: *"Just call it 'your concepts' or 'your library' — don't force me to learn your proprietary startup jargon"*; round 2 decision 4: *"Just call it 'Your Concepts.' 'Library' is precious; 'concepts' is plain and matches the data."*).

Codex's earlier "library earns its keep with mixed-state tiles" argument is now moot — there are no mixed-state tiles in v1.

**Locked decision: home/desk view is named "Your concepts."**

What changes:

- `hero-state-chip` data-state="empty" content: `no map yet` → `no concepts yet`.
- `hero-title` for empty desk: `Your draft paths.` → `Your concepts.`
- `hero-guidance` for empty desk: rewritten to *"Pick a tile to enter, or start a new concept."*
- `hero-primary-action` label: `Begin at New Entry` → `New concept`.
- `hero-eyebrow` content: `Desk` stays.

What does **not** change:

- The library/inventory page (`#library-view`) copy is out of scope for this spec.
- The voice line *"The map stays honest because evidence comes from your reconstruction"* — removed from the home/desk view in this spec. If it earns a place anywhere later, it is on the empty-graph state of a freshly-routed concept (deferred design call).

## 5. Backend — what changes

### 5.1 Generation path: smallest ProvisionalMap from `{concept, threshold}`

Module: `ai_service.py` or successor.

```python
def generate_smallest_provisional_map(
    concept: str,
    threshold: str,
    lc_context: list[StandardDescription] | None = None,
) -> ProvisionalMap:
    ...
```

**Returns the existing `ProvisionalMap` Pydantic model** — not a new model. Codex was explicit: *"after launch attempt, generate a smallest route that is still ProvisionalMap-compatible."* The existing schema is reused; a smallest route is a small ProvisionalMap.

**Hard contract.** The returned `ProvisionalMap` must contain at most 4 drillable nodes total: **the suggested first target IS the core thesis** (one node, carrying both roles — its display name is the thesis statement, and it is the node the first cold attempt fires against), plus at most 3 backbone hints (≤3 additional nodes). There is no separate "thesis" node distinct from the suggested first target. No cluster lattice. The prompt at `app_prompts/generate-smallest-route-system-v1.txt` enforces this; the validator rejects any output exceeding the cap with `500` and a clear reason. (`500` not `422` because this is a server-side generation failure, not a client input failure.)

**Learning Commons enrichment.** The four-gate logic from the deferred 2026-05-02 spec §3.3.2 carries over verbatim. When all four gates pass, top 2-3 standards descriptions are passed as `<lc_context>`. When any gate fails, generation proceeds with `lc_context=None`.

### 5.2 `POST /api/extract` — bypass rejection (load-bearing)

The existing `/api/extract` endpoint dispatches both paths:

| Payload | Dispatch |
|---|---|
| `name` non-empty + `source` present | Today's `extract_knowledge_map` pipeline. Full ProvisionalMap. |
| `name` non-empty + `source` null + `starting_sketch` substantive (3+ words, not idk) | New `generate_smallest_provisional_map(name, starting_sketch)` path. Smallest ProvisionalMap (≤4 nodes). |
| `name` non-empty + `source` null + `starting_sketch` null/empty/thin | **`422 Unprocessable Entity`** with `{"error": "thin_sketch_no_source", "message": "Add more to your sketch, or attach source material — either path opens the build."}`. |
| `name` empty/whitespace-only | `422` with `{"error": "missing_concept", "message": "Concept name required."}` (today's behavior). |

The third row is the bypass guard codex required: *"/api/extract must reject name-only/source-null bypasses."* Without it, a buggy or malicious client could `POST {name: "X", source: null, starting_sketch: ""}` and get a graph back from concept name alone — exactly the doctrine break this spec exists to prevent. This server-side check is non-optional.

The substantiveness heuristic for `starting_sketch` is the existing cold-attempt 3+ words / no-idk gate per `docs/product/spec.md` §2 Phase 1. A shared helper (`is_substantive_threshold(text: str) -> bool`) lives in the same module as `generate_smallest_provisional_map`; the frontend's JS implementation of the same gate is verified parity through a shared test fixture (~30 substantive / thin / borderline inputs). Client/server divergence is a release-blocker.

### 5.3 `POST /api/extract-url` — unchanged

URL source materialization continues as today. Frontend `submitConceptCreate` two-steps through `/api/extract-url` then `/api/extract` for URL sources. v1 does not touch this contract.

### 5.4 No new endpoints

There is no `/api/concepts/shell` and no `/api/concepts/<id>/route`. The single existing `/api/extract` endpoint handles all paths via the dispatch above. v1 ships zero new HTTP routes.

### 5.5 Telemetry

- `concept_create.door.submit` — `{has_source, source_type, sourceless: bool}`
- `concept_create.launch_pad.entered` — `{age_ms}` — fires when the launch pad mounts with a valid pending shell.
- `concept_create.launch_pad.evaporated` — `{age_ms}` — fires when the launch pad is mounted with an expired pending shell and the learner is bounced. Tells us how often the sessionStorage state is lost.
- `concept_create.launch_pad.submit` — `{threshold_len, build_blocked: bool}`
- `concept_create.bypass_rejected` — `{path: "client" | "server"}` — fires when the name-only/source-null bypass is caught. `client` is the disabled-button path; `server` is `/api/extract` 422. In a healthy state, every block fires as `client`; `server` blocks indicate an old/buggy/malicious client and are worth knowing about.
- `concept_create.lc.queried` / `enrichment_applied` / `enrichment_skipped` — unchanged from prior spec drafts.
- `concept_create.ai_call` — `{stage, model, tokens_in, tokens_out, latency_ms, cost_usd_est}`. `stage` ∈ `smallest_route`, `smallest_route_lc_enriched`, `extract` (existing).

The `bypass_rejected` event is load-bearing for principle #8 enforcement — it is the visibility layer that confirms the wire-level guard is firing.

## 6. Frontend — what changes

### 6.1 Files touched

- `public/index.html` — strip the `ignition-view` form per §3.1; add new `launch-pad-view` section per §3.2; update home/desk hero copy per §4.4.
- `public/css/components.css` — strip eyebrow/voice-line/sketch styles from ignition-view; add styles for launch pad; add the "skeleton, it will grow" framing line style on the route view.
- `public/js/app.js`:
  - Door submit handler: no source → write `socratink:pendingShell` to sessionStorage → navigate to launch pad. Source attached → existing `submitConceptCreate` flow with `starting_sketch: null`.
  - New `launch_pad.js` module (or section in `app.js`): mount handler reads `sessionStorage`, hydrates concept name, validates ts < 24h; submit handler calls `submitConceptCreate({name, startingSketch, source: null})`; on success clears `sessionStorage` and navigates to graph view.
- `public/js/concept-create.js` — extract `beginEditSource` and the source-panel markup/handlers into a reusable module (see §6.2). Consumers: existing concept-create modal AND the new door affordance.
- `public/js/ai_service.js` — `submitConceptCreate({name, startingSketch, source, apiKey})` keeps its current signature. The frontend wraps it for the source-less launch-pad submit. No new functions strictly required.
- Any place the home/desk view renders — update title, chip, guidance, CTA per §4.4.

### 6.2 Source-panel extraction (load-bearing)

The source panel currently lives inline inside `concept-create.js::beginEditSource` (line 601). To mount it on the door, it has to be extracted into a reusable helper.

- Factor `beginEditSource` and its handlers (`creation-source-panel`, `creation-source-panel-cancel`, `creation-source-panel-attach`, paste/clipboard/file/url handlers) into a new module `public/js/source-panel.js` exporting `mountSourcePanel(targetEl, onAttach, onCancel)`. Both the existing modal and the new door call it.
- Acceptance criterion #5 below requires verifying the existing concept-create modal source flow still works after extraction.

### 6.3 What stays

- The single hard-violet anchor (the build/submit CTA). One violet accent per screen.
- Calm copy voice. No emoji. No exclamation marks.
- Footer line *"Study content stays locked until the cold attempt"* — kept on the launch pad. (The launch attempt itself does not unlock study; the cold attempt does.)
- DESIGN.md §10 voice rules.

## 7. Acceptance criteria

The redesign ships when **all** of these hold:

1. **Source-less happy path.** Learner enters concept name with no source, taps door submit (arrow), lands on launch pad showing the canonical helper copy, enters substantive threshold (3+ words, not idk), taps `Build my map`, lands on a graph view with a smallest ProvisionalMap (≤4 drillable nodes) AND the *"This is the skeleton. It will grow as you reconstruct."* framing line visible.
2. **Source-attached happy path (text/file).** Existing `/api/extract` pipeline runs, full ProvisionalMap returned, no launch pad shown.
3. **Source-attached happy path (URL).** Two-step through `/api/extract-url` then `/api/extract`. No launch pad shown. Server-side rejection of raw URL source on `/api/extract` is preserved.
4. **Bypass rejection (server-side).** A direct POST to `/api/extract` with `{name: "X", source: null, starting_sketch: ""}` returns `422` with `error: "thin_sketch_no_source"`. Verified with curl.
5. **Source panel extraction does not regress the existing modal.** After the source-panel module extraction, the existing concept-create modal's source-attach flow (text, URL, file) continues to work. Manual smoke + any existing tests pass.
6. **sessionStorage shell hydration.** After submitting the door with no source: opening DevTools shows `socratink:pendingShell` set with the typed name and a recent ts. After successfully building or canceling: the key is cleared. Loading the launch pad URL directly without a pending shell bounces the learner to the door.
7. **Smallest-route cap enforced.** A regression that returned a ProvisionalMap with >4 drillable nodes from the source-less generation path is rejected by the validator with `500`. Tested with a deliberately permissive prompt fixture.
8. **No graph generated from concept name alone.** Verified by canceling at the launch pad and checking that (a) the pending shell in `sessionStorage` is cleared (or evaporates on tab close), (b) no `/api/extract` request was issued, and (c) no concept appears in the client-side concept-store. Pending shells live only in sessionStorage and never round-trip to the server. Combined with acceptance criterion #4, this confirms principle #2 holds end-to-end: no provider-prior artifact is generated, returned, persisted, or shown for a name-only flow.
9. **Home/desk vocabulary updated.** No instance of "draft path" or "draft paths" remains in the home/desk view's title, chip, guidance, or CTA. Replacement vocabulary per §4.4 is implemented.
10. **Threshold validation parity.** `is_substantive_threshold` shared test fixture (~30 inputs, substantive / thin / borderline) returns identical client and server verdicts. Divergence is a release-blocker.
11. **`scripts/qa-smoke.sh` passes against a deploy preview.**
12. **Browser smoke (load-bearing per `feedback_browser_smoke_is_load_bearing.md`).** Manually walk all three happy paths (source-less, source-attached text, source-attached URL) at the dev server. Verify no console errors and no regression on adjacent screens (graph view, library, settings) from CSS changes.
13. **Visual smoke.** Dark-mode and light-mode screenshots of: door at rest, door with source panel expanded, launch pad with empty/substantive/thin threshold states, route view showing the "skeleton" framing line. Attached to the PR.
14. **Accessibility — arrow-only door CTA.** The door submit button (visible as an arrow icon with no visible text) carries a non-empty accessible name, verified by (a) inspecting the rendered DOM for `aria-label` or a visually-hidden `<span class="sr-only">` child, AND (b) running an axe-core / Lighthouse a11y check on the door surface and confirming WCAG 4.1.2 ("Name, Role, Value") passes. A bare-icon button with empty accessible name is a release-blocker.

## 8. Out of scope (deliberate non-goals)

- **Progressive route expansion logic.** Mechanisms that grow the smallest route into a fuller graph after cold-attempt evidence, repair events, source attachments, or other learner signals. v1 ships the smallest route as a terminal artifact.
- **Server-side persisted shell state (`creation_phase` column).** v1 keeps the shell in sessionStorage. Server persistence revisited if dogfood telemetry shows non-trivial loss.
- **Re-introducing the conversational ignition.** The deferred 2026-05-02 spec stays deferred.
- **Convergence of source-attached and source-less paths.** The asymmetry (full vs smallest ProvisionalMap) is accepted in v1.
- **Promoting source attach to required.** Source remains optional.
- **Mixed-state library tiles.** Removed from v1 because shells aren't persisted; revisited if/when shell persistence is added.
- **Re-entering the door from the launch pad.** No back affordance in v1. Cancel + restart is the only path.
- **Multi-tab or multi-device pending-shell sync.** sessionStorage is per-browser-tab. v1 does not sync.
- **The library/inventory page copy.** Out of scope.
- **An explicit "fuzzy area" input.** Stays removed.

## 9. Implementation sequencing (handoff to writing-plans)

1. **Backend foundation.**
   - Add `generate_smallest_provisional_map(concept, threshold, lc_context=None)` in the AI service module. New prompt at `app_prompts/generate-smallest-route-system-v1.txt`. Validator enforces ≤4 drillable nodes.
   - Add `is_substantive_threshold(text: str) -> bool` helper. Shared test fixture.
   - Update `/api/extract` dispatch to handle the three rows in §5.2's table. Add the `thin_sketch_no_source` 422 path.
   - Existing `extract_knowledge_map` and `/api/extract-url` are unchanged; `starting_sketch` is now optional on the source-attached path (it was previously always sent).
   - Test all paths with curl + golden fixtures *before* touching frontend.
2. **Source-panel extraction.**
   - Pull `beginEditSource` and its markup/handlers into `public/js/source-panel.js`.
   - Verify the existing concept-create modal source flow still works (acceptance #5).
3. **Frontend door.**
   - Strip the existing `ignition-view` form per §3.1.
   - Wire arrow-only submit; add source-attach affordance using the extracted source-panel module.
   - On no-source submit: write `sessionStorage`, navigate to launch pad. On source-attached: existing flow.
4. **Frontend launch pad.**
   - New `launch-pad-view` section. Mount handler reads sessionStorage, hydrates concept name, validates ts.
   - Submit calls `submitConceptCreate` with `starting_sketch: <threshold>, source: null`.
   - Handle 422 from the server-side substantiveness gate by rendering the strategy-framed footer.
   - On 2xx success: persist the returned `ProvisionalMap` through the existing client-side concept-store path. **Only after** that persistence succeeds, clear `socratink:pendingShell` from sessionStorage and navigate to the graph view. If client persistence fails for any reason, leave the pending shell in place so the learner can retry without re-typing.
5. **Frontend home/desk view.** Update title, chip, guidance, CTA per §4.4. Verify no "draft path" string remains in any visible surface.
6. **Frontend route view framing line.** Add the *"This is the skeleton. It will grow as you reconstruct."* line on the post-launch route view (only when arriving fresh from the launch pad — not when revisiting an existing concept).
7. **Telemetry.** Wire all events from §5.5. Critical: `bypass_rejected` and `launch_pad.evaporated` need to be visible in logs from day one.
8. **Bindings docs.** Update DESIGN.md §3 Screen 1 to reflect that threshold capture has moved to a dedicated post-door surface and now seeds smallest-route generation. Add a note pointing to this spec. Update UBIQUITOUS_LANGUAGE.md if `launch pad`, `launch attempt`, `pending shell`, or `smallest actionable route` need codifying.

## 10. Risks and mitigations

| Risk | Mitigation |
|---|---|
| sessionStorage shell evaporates on tab close, frustrating learners. | v1 limitation. Telemetry on `launch_pad.evaporated` makes the rate visible. If non-trivial in dogfood, follow-on spec persists shells server-side. The cost of losing a pending shell is low (re-type concept name; the threshold textarea hadn't been filled yet). |
| Smallest-route generation produces a worse first-cold-attempt experience than today's full extraction. | The cold-attempt UX is unchanged; the cold attempt fires against the suggested first target, which is a normal drillable node. Telemetry on time-to-first-substantive-cold-attempt + cold-attempt completion rate post-launch will confirm. |
| Asymmetry between source-attached (full ProvisionalMap) and source-less (smallest ProvisionalMap) confuses learners. | Acknowledged; v1 trade-off. Convergence is a future call. |
| The smallest-route prompt fails to produce a useful suggested first target for niche concepts. | Validator enforces ≤4 nodes; prompt enforces structure. If generation fails repeatedly, the server returns `500` and the launch pad surfaces a retry affordance ("socratink could not draft a route from this; try elaborating the threshold further"). |
| The `thin_sketch_no_source` server-side guard regresses (someone "fixes" the 422 to allow a graceful default). | Acceptance criterion #4 tests for it explicitly. Telemetry on `bypass_rejected{path: "server"}` makes any regression visible immediately — server bypasses should be near-zero in steady state. |
| Source-panel extraction breaks the existing concept-create modal. | Acceptance criterion #5 requires explicit verification. The extraction is mechanical (move markup + handlers behind a module export), but it touches a working surface; manual smoke is non-optional. |
| Concept-name-only generation re-emerges as a "let's just generate something" suggestion during implementation. | Principle #2 is binding. Acceptance criteria #4 and #8 specifically test for it. The supersession note in `2026-05-07-loop-entry-simplification-design.md` preserves the warning. |
| Increased AI cost from running smallest-route generation on source-less concepts. | Source-less concepts run smallest-route generation only (one model call); source-attached concepts run extraction only (one model call). Net per concept created: still one model call, different prompt, smaller output. LC enrichment adds at most one HTTP call. Cost impact is bounded and tracked via `concept_create.ai_call`. |
| Persona's preferred path (c) — door → small map → cold-attempt-as-threshold — is genuinely a better UX and we shipped a worse one. | Path (c) was rejected by codex on doctrinal grounds (no graph from concept name alone; threshold and cold attempt are distinct surfaces; v1 cannot smuggle in progressive expansion). C-prime is the closest to (c) we can ship without breaking doctrine. If post-launch telemetry shows learners clicking through the launch pad in <3 seconds with thin thresholds, the launch pad is being treated as friction, and we revisit. The persona insight is preserved as a future-design concern, not abandoned. |

---

## Appendix A — Brainstorm provenance

1. **Initial friction diagnosis** (Claude → user): two fields too many, copy overwrought, frame slightly wrong.
2. **Persona round 1 (Gemini, college-sophomore).** Converged D + B + B + B with the final note: *"reject the urge to explain the app's philosophy to me before I've even used it."*
3. **First spec draft** (`2026-05-07-loop-entry-simplification-design.md`) proposed concept-name-only generation as the simplification.
4. **Codex round 1.** Four corrections: route is `/api/extract` not `/concepts`; URL source two-steps through `/api/extract-url`; source panel needs extraction from `concept-create.js::beginEditSource`; concept-name-only generation violates the learner-seeded route contract.
5. **Codex round 2.** User explored *"what if the concept is ingested as a seed, and then the first entrance into that concept attempts to determine the best map for the learner?"* Codex proposed Path D — Progressive Route Materialization — with the smallest-actionable-route framing.
6. **Codex round 2 refinement.** User added *"the map generation shouldn't try to boil the ocean."* Codex tightened: smallest actionable route only at first entrance; progressive expansion deferred; threshold-only at first entrance (no node-state mutation).
7. **Path D first draft of this spec.** Proposed `creation_phase` column, `/api/concepts/shell`, `/api/concepts/<id>/route`, new `SmallestRoute` Pydantic model.
8. **Persona round 2.** Confirmed the architecture but pushed for path (c): *"skip screen 2 entirely. Door → small map (thesis + one node) → cold attempt absorbs threshold."* Absorbable copy/CTA/vocabulary feedback came along: rename Screen 2 copy to canon-safe, add "skeleton" framing on the route view, kill the door CTA word in favor of arrow-only, lock vocabulary to "Your concepts."
9. **Codex round 3.** Rejected raw path (c) (still concept-name-only generation; collapses threshold and cold attempt; smuggles in progressive expansion). Specified C-prime: launch pad not graph, no thesis from concept name alone, launch attempt is threshold capture and mutates no node state, smallest ProvisionalMap-compatible artifact, sessionStorage for in-flight state, no new persisted column, `/api/extract` rejects name-only/source-null bypasses.
10. **C-prime is the version of this spec.**

## Appendix B — Anti-patterns this spec deliberately rejects

- **Concept-name-only full-graph generation.** The doctrinal failure of the superseded spec.
- **Concept-name-only thesis generation.** Same anti-pattern, scaled down. Codex round 3 was explicit: *"no generated core thesis from concept name alone."* Even a tiny generated artifact from name alone is provider-prior dressed as learner-seeded.
- **Collapsing threshold and first cold attempt.** Distinct surfaces with distinct mutation contracts. The launch attempt is global (rough whole-concept model), mutates no node state. The first cold attempt is local (one mechanism), mutates `locked → primed`. Collapsing them loses canon's distinction.
- **Progressive expansion logic in v1.** §8 out-of-scope. Smuggling it in here would re-create the boil-the-ocean failure mode by other means.
- **Adding a `creation_phase` column "to be safe."** v1 keeps state in sessionStorage. Adding the column is a follow-on if dogfood demands it.
- **A "back to door" affordance from the launch pad.** Same anti-pattern as the deferred 2026-05-02 spec's "back to chat" — invites recursive surfaces.
- **Auto-fetching content (Wikipedia, web scrape, vendor library) when no source is attached.** Carries forward from the deferred 2026-05-02 spec.
- **Voice line preaching at the door OR the launch pad.** Persona feedback was explicit in both rounds. Voice copy is removed from both surfaces.
- **A "popular concepts" / "suggested topics" list under the door input.** Recognition substituting for generation.
- **A `Continue` (or any word) on the door submit.** Persona round 2 was emphatic: arrow-only.
- **"Show me your starting map" or any precious framing on the launch pad.** Persona round 2: *"sounds slightly precious… don't make me feel like I'm being led through a corporate design thinking workshop."* Canon-safe copy from `starting-map-flow-artifact.md` is the binding text.
- **Allowing the launch pad to be visited without a pending shell.** No deep-link entry. The launch pad is a continuation surface, not a standalone route.
- **A "graceful default" if the bypass guard fires.** The 422 response with the strategy-framed footer is the only correct behavior. Any "let's just generate from concept name to be friendly" suggestion fails review here.
