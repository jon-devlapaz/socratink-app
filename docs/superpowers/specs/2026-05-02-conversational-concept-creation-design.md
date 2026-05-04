# Conversational concept creation — design spec

**Date:** 2026-05-02
**Status:** Brainstorm complete; ready for plan + implementation
**Author:** Brainstormed with Claude, decisions made by jon-devlapaz
**Supersedes (the form):** `docs/design/handoffs/2026-05-01-new-concept-modal-redesign.md` is no longer the work order. Its copy/voice fixes have been merged into `dev`; its premise — that the concept-creation surface should remain a form — is no longer the direction.

---

## 1. Why this exists

The New Concept modal, even after the 2026-05-01 redesign, is a form. socratink is an AI-native metacognitive learning product, and the entry surface should reflect that. The form asks the learner to type into labeled fields. A conversational entry asks the learner to think out loud and have the system structure the result.

The brainstorm settled on a precise framing: **the chat is the ignition mechanism. The summary card is the handoff into the learning system. The product itself is graph / repair / reconstruction.** Anything that grows the chat into a study surface is the wrong direction — that path leads to "ChatGPT for studying," which is the anti-product. (Saved as auto-memory `feedback_chat_as_ignition.md`.)

This spec defines the new entry surface end-to-end and the backend changes needed to support source-optional graph generation.

## 2. Binding principles

> **The system in four lines:**
>
> - **Chat** = ignition.
> - **Summary card** = the learner confirms the package.
> - **Source** = optional evidence.
> - **Graph** = provisional draft from a valid seed.
>
> A *valid seed* is operationally defined in §3.2: a substantive sketch, OR attached source material, OR both. No seed → no graph; the system blocks build rather than fabricate one.

These principles are load-bearing. Any implementation choice that violates one is a design break, not a polish question.

1. **Chat is ignition.** Two AI turns, then exit. The chat must not become a persistent surface, must not gain history scrollback, must not invite open conversation. It extracts the learner's starting model and hands off.
2. **Summary card is the handoff.** Once it appears, the learner is in product surface, not chat surface. The card is editable, the build CTA lives there, and the build action is the moment of commitment.
3. **The learner's model is the baseline (when source-less generation is used).** Concept name + sketch are the reference truth for everything downstream — comparison, repair, re-drill. Source material, when attached, is *evidence*, not the baseline. When source-less generation runs, the sketch is the seed; the AI hypothesizes structure *around* the sketch, never *from* its own prior knowledge wearing the sketch as a costume.
4. **No silent source backfill.** When the learner explicitly chooses to build without source, the system never silently fetches arbitrary content (Wikipedia, web scrape, vendor library) to fill the gap. The learner's choice is honored.
5. **Learning Commons is enrichment, not a dependency.** LC may be queried for grounding context when the concept is high-confidence K-12 academic. LC is never required, never silently substituted for source, and never blocks generation when unavailable.
6. **Provisional graph is hypothesis, not knowledge.** DESIGN.md §3 Screen 2 already binds this. Source-less generation strengthens the requirement: a graph drafted from sketch alone is *more* hypothesis-shaped than one drafted from pasted source. Copy and visual treatment must reflect that.
7. **No hallucinated graphs presented as learner-seeded.** When the learner has not provided enough signal to form a baseline — sketch is non-substantive AND no source is attached — source-less generation is **blocked**, not silently fulfilled from the model's prior. The two valid resolution paths the system offers are: (a) edit the sketch into something substantive, (b) attach source material. The system never substitutes its own latent knowledge for the learner's model and presents the result as the learner's draft. This is the anti-pattern this entire spec exists to prevent; it is the failure mode that would silently break the product's foundational promise (PRODUCT.md: *"the graph shows what socratink has evidence for, not what the learner knows"*).

## 3. The flow

Three stages. Each is its own surface.

### 3.1 Stage A — chat (ignition)

The chat lives inside the existing `creation-dialog` modal shell. Two AI turns, fixed structure (pattern E from the brainstorm).

**Turn 1.** AI opens with the framing question. The learner answers in a single composer at the bottom.

> AI: *What do you want to understand?*

**Turn 2.** AI follows up with a structured probe based on the reply. The probe asks for the learner's rough sketch — parts, guesses — without explicitly asking for confusion (DESIGN.md §3 Screen 1 requires confusions, but they can be inferred from gaps in the sketch instead of solicited directly).

> AI: *Sketch what you think it does — rough is fine. What parts come to mind?*

**Adaptive fallback.** If the learner's reply to turn 2 is thin (heuristic: token count below threshold, or matches a "don't know" pattern like `idk`, `no idea`, one-word reply), the AI offers an analogical scaffold per DESIGN.md §3 Screen 3 (analogical-fallback rule). The fallback is **one bounded extra scaffold** — a single additional AI question with a single learner reply — *not* a return to open conversation. After the fallback reply lands (substantive or not), the chat exits to the summary card. The learner cannot trigger a second fallback, a second scaffold, or any further AI turn. The bound is hard: at most three AI turns total (turn 1 + turn 2 + at most one fallback) and three learner replies, then exit.

> AI: *Try this: think of it like a kitchen taking in ingredients and making a meal. What ingredients does the system take in, and what does it produce?*

The kitchen analogy is **illustrative only.** The actual analogy must be derived from the learner's concept — a kitchen will not work for "kubernetes" or "cognitive bias." The system prompt instructs the AI to choose a source domain familiar enough to the typical adult learner that no domain expertise is required and that maps cleanly onto the target concept's causal structure.

**Constraint on AI voice across all chat turns and the analogical fallback.** Output is the question or analogy *only*. No acknowledgments (`"Fair."`, `"Got it"`, `"OK"`), no affirmations (`"Great start"`, `"Interesting"`), no preambles (`"Let me think"`, `"Sure"`), no consolation copy (`"That's tricky"`). Plain, complete, Socratic sentences per DESIGN.md §10. The system prompt at `app_prompts/threshold-chat-system-v1.txt` enforces this; voice drift is a release-blocker (see §8 acceptance criterion #9).

**Hard stop.** No open-ended continuation. The chat exits after turn 2 (or after the analogical fallback reply if that path was taken). There is no "ask another question" affordance, no "tell me more" option, no scroll-back. Once the summary card appears, the chat collapses to a one-line breadcrumb: `↑ chat (collapsed): "Photosynthesis" · sketch captured`.

**Visual posture.** Quiet. Not bubble-heavy. The AI's question reads as text on the page, not as a chat avatar with a name. The composer is a single textarea with a calm submit. No typing indicators, no thinking dots, no "AI" label. The learner is talking *with* the system, not *to* a chatbot.

**State machine.**

```
chat:turn-1 → learner replies → chat:turn-2 (probe) → learner replies
  ├── substantive → summary-card
  └── thin       → chat:fallback (analogical) → learner replies → summary-card
```

### 3.2 Stage B — summary card (handoff)

Layout P2 from the brainstorm. The chat collapses to a breadcrumb. Three chips appear: Concept, Your sketch, Source material. One CTA: **Build from my starting map**.

**Chip semantics.**

| Chip | Source | Edit affordance | Empty state |
|---|---|---|---|
| Concept | AI extracts canonical name from chat turn 1+2 | "edit" → input field, save on blur | n/a (always populated) |
| Your sketch | Concatenated learner replies from chat (verbatim) | "edit" → textarea, save on blur | n/a (always populated) |
| Source material | None at first | "Add source" → inline expansion of the existing Text/URL/File tabs panel | *"None added — build will start from your model only"* (italic, muted) |

**Source-material chip states.**

- **Empty (default).** Dashed border, transparent background, italic muted copy. `Add source` action in violet on the chip header.
- **Attached.** Solid border, white background. Value shows the captured source descriptor: `3,421 chars from a Wikipedia article` (URL), `notes.md · 2,108 chars` (file), `2,640 chars pasted` (text). `replace` action on the chip header.

**CTA copy is state-dependent.** The build button names the actual seed of the build:

| State | CTA copy | Why |
|---|---|---|
| Substantive sketch, no source | `Build from my starting map` | Sketch is the sole seed; learner's ownership is named explicitly |
| Substantive sketch + source attached | `Build from my map and source` | Both are part of the seed; copy reflects the package |
| Thin sketch + source attached | `Build from source` | Source is the seed; sketch is shaping context only — the copy is honest about which is doing the structural work |
| Thin sketch + no source | (CTA disabled — see Validation) | No valid seed; build is blocked |

The state-dependent CTA prevents a quiet lie: a learner who attached substantial source material with a one-line sketch deserves to see *"Build from source"* rather than *"Build from my starting map"*, because the source is the actual structural input. Naming the seed honestly is part of principle #7 (no hallucinate-and-present).

**Footer copy.** `Study content stays locked until the cold attempt.` (unchanged from existing modal).

**Validation.** Build is enabled only when:

- `Concept` is non-empty after trimming, AND
- **Either**:
  - `Your sketch` is **substantive** — heuristic: ≥8 non-stopword tokens AND does not match a "don't know" pattern (`idk`, `no idea`, `i dont know`, `?`, `…`, repeated single characters, keyboard mashing), **OR**
  - Source material is attached.

| Source attached? | Sketch substantive? | Build allowed? | Reason |
|---|---|---|---|
| No | No | **No** | No valid seed for source-less generation |
| No | Yes | Yes | Learner model is the seed |
| Yes | No | Yes | Source is the seed |
| Yes | Yes | Yes | Learner model + source are the seed |

**Why source-attached can build with a thin sketch.** When source material is present, the source provides the structural seed for graph generation and the sketch becomes shaping context rather than the seed itself. The learner's act of attaching evidence carries the load the sketch would otherwise carry alone. This is the spec's honest contract: source-less generation **requires** a substantive sketch; sourced generation does not.

**Empty/thin-sketch state when build is blocked.** When the build is disabled because the sketch is non-substantive AND no source is attached, the `Your sketch` chip shows a strategy-framed footer line (DESIGN.md §10):

> *A few words about how you think it works will give socratink something to draft from. Or attach source material — either path opens the build.*

Never consolation copy, never *"you need to do more."* The block names two equally-valid resolutions and lets the learner pick. The CTA stays disabled until one resolves.

**Edit interactions.**

- Click `edit` on a chip → chip body becomes the matching input (text input for Concept, textarea for Your sketch, source panel for Source material).
- Save on blur, on Enter (single-line inputs only), or on clicking outside the chip. No explicit save button per chip — that would add a fourth interactive layer.
- Cancel: Escape reverts to the prior value.

**No mid-flow back-to-chat affordance.** Once the summary card appears, the learner cannot reopen the chat. If they want to start over, they cancel the modal entirely. (The breadcrumb is a label, not a button.) This is deliberate — going back to the chat would invite a longer dialogue, which violates principle 1.

### 3.3 Stage C — graph generation

Triggered by `Build from my starting map`. Two backend code paths, selected by source-attachment state at submit time.

**3.3.1 Source attached.** Existing `extract_knowledge_map` pipeline. No change. Source text is the extraction input; threshold (concept + sketch) is shaping context. This is today's behavior.

**3.3.2 No source attached.** New backend code path: `generate_provisional_map_from_sketch(concept, sketch, lc_context=None)`.

The default behavior is **pure-AI generation** from `{concept, sketch}` alone. The AI hypothesizes a provisional map structure using the sketch as the seed and the concept name as the topic anchor. The output is the same `ProvisionalMap` Pydantic model used by the source-attached path (per the foundation spec, `2026-05-01-foundation-design.md` §5.1).

**LC enrichment is opt-in by quality.** Before generation, the backend may query Learning Commons:

```
GET https://api.learningcommons.org/knowledge-graph/v0/academic-standards/search
  ?query={concept}&limit=5
Authorization: Bearer ${LEARNING_COMMONS_API_KEY}
```

LC enrichment is applied only when **all four gates pass**. The gates are stated as contracts; the bracketed parenthetical inside each gate is the *initial implementation heuristic*, deliberately separated from the contract so the heuristic can be tightened or loosened from telemetry without rewriting the rule.

1. **API responded.** The query returned successfully (HTTP 200) within the timeout budget. (Implementation: 800ms wall-clock; see §5.2.)
2. **Results returned.** The response payload contains ≥1 standard.
3. **Score floor.** The top result's relevance score clears the threshold above which LC's matches are real semantic hits rather than closest-substring noise. (Implementation: top `score` ≥ `LC_RELEVANCE_THRESHOLD`, initial value `0.70`, configurable. Verification log in Appendix A established that scores below ~0.66 plateau into garbage matches like *"photosynthesis" → "Draw conclusions from picture graphs"*.)
4. **K-12 academic confidence.** The top result is identifiably a K-12 academic standard, not a generic literacy/numeracy fragment LC returned because nothing better matched. (Implementation: `jurisdiction` is `Multi-State` or a US state name, AND `statementCode` is non-null OR `description` length ≥ 40 characters. The heuristic is deliberately loose for v1; telemetry on `enrichment_skipped: non_k12` reveals where it under-fires; the gate tightens or loosens from there. Future iteration may add a topic-classifier or LC-side metadata field if available.)

When all four gates pass, the top 2-3 standard descriptions are passed to the generation prompt as **optional grounding context** under a clearly-marked `<lc_context>` block. The prompt instructs the AI to use the context to ground hypothesis structure but to favor the learner's sketch when the two diverge. The AI is explicitly told the context is curriculum-aligned but not authoritative for this specific learner.

When **any** gate fails — or LC is unreachable, times out, or errors — the generation proceeds with `lc_context=None`. No fallback fetch from any other source is attempted. The system never tells the learner LC was queried; the enrichment is invisible UX-side. Each skip carries a telemetry reason (see §5.4) so we can measure the gate's behavior in production rather than guess at it.

**Provisional graph framing.** The generated graph is rendered with the same Provisional Graph treatment as today (DESIGN.md §3 Screen 2 — *draft route · ready for first attempt · locked*). It does not mark which nodes came from LC vs from pure inference. The learner sees a hypothesis to attempt, not a pedigree of where the structure came from.

## 4. What changes — frontend

### 4.1 Files touched

- `public/js/app.js` — `buildContentInputUI` is the current modal builder; replace its `showNameField` branch with the chat → summary state machine. The non-`showNameField` branch (inline overlay extract path) is out of scope and unchanged.
- `public/css/components.css` — new styles for the chat surface and summary card; the `.creation-fuzzy-toggle`, `.creation-fuzzy-row`, `.creation-fuzzy-hint` styles introduced in the 2026-05-01 redesign are removed (the fuzzy area is no longer a separate field; confusion is captured implicitly in the chat).
- `public/js/api.js` (or wherever the create-concept call lives) — payload adds an explicit `has_source: bool` flag and allows `source_text: null` / `source_url: null`. New endpoint may be needed if the existing one assumes source presence.
- Modal shell `.creation-dialog` is reused. Header, scrim, focus trap, and dismiss handlers are unchanged.

### 4.2 New components

| Component | Purpose | DOM root |
|---|---|---|
| `ChatStage` | Stage A state machine; renders the AI question, the learner composer, and handles turn 1 / turn 2 / fallback transitions. Calls a backend endpoint per turn to get the AI question copy (or uses a deterministic prompt template for turn 1; only turn 2 + fallback need backend). | `.creation-chat` |
| `SummaryCard` | Stage B; renders the three chips, edit interactions, and the build CTA. Receives `{concept, sketch}` from `ChatStage`'s exit signal; renders the chat breadcrumb. | `.creation-summary` |
| `SummaryChip` | Single chip with label, value, action, and inline edit mode. Generic across all three chip types. | `.creation-chip` |
| `SourceMaterialPanel` | Reused / refactored from current `overlay-panel` set (Text/URL/File tabs + paste/clipboard/file/url handlers). Rendered inline inside the source chip when expanded. | `.creation-source-panel` |

The chat composer is a plain `<textarea>` + submit button — not a chat-bubble component library.

### 4.3 Removed surfaces

- `creation-name-input` (concept name as a separate field)
- `creation-threshold-input` (starting-map textarea)
- `creation-fuzzy-toggle` / `creation-fuzzy-panel` / `creation-fuzzy-input` / `creation-fuzzy-hint`
- The 2026-05-01 redesign's `.creation-source-tabs`, `.paste-clipboard-btn`, and the inline source-tabs row at the form-level. These move *inside* the `SourceMaterialPanel` which only appears when the source chip is expanded.

### 4.4 What stays from the 2026-05-01 redesign

- Single hard-violet anchor (the build CTA). The summary card respects "one violet accent per screen."
- Calm copy voice, no hype.
- Footer line: *Study content stays locked until the cold attempt.*
- Modal shell, kicker (`NEW CONCEPT`), title (`Start a concept`), close button, scrim, focus trap.
- DESIGN.md §10 already updated (URL deferral removed).

## 5. What changes — backend

### 5.1 New generation path

Module: `ai_service.py` or its successor per the foundation spec (`docs/superpowers/specs/2026-05-01-foundation-design.md`).

```python
def generate_provisional_map_from_sketch(
    concept: str,
    sketch: str,
    lc_context: list[StandardDescription] | None = None,
) -> ProvisionalMap:
    ...
```

Returns the same `ProvisionalMap` Pydantic model the existing extraction path returns. Validation rules per the foundation spec §5.1 apply unchanged.

A new prompt at `app_prompts/generate-from-sketch-system-v1.txt` defines the system prompt for source-less generation. It describes the cognitive task ("hypothesize a provisional concept map for a learner who is starting with their own sketch"), the output JSON schema (same as `extract-system-v1.txt`), and the role of `<lc_context>` when present (grounding-only, never authoritative).

A second new prompt at `app_prompts/threshold-chat-system-v1.txt` defines the AI voice for the threshold chat (turn 2 probe and the analogical fallback). The prompt enforces three hard constraints — these are not stylistic preferences, they are release-blocker contracts:

1. **No conversational filler.** No acknowledgments (`"Fair."`, `"Got it"`, `"OK"`), no affirmations (`"Great start"`, `"Interesting"`), no preambles (`"Let me think"`, `"Sure"`), no consolation copy. The AI's output is the question or analogy *only*. This mirrors DESIGN.md §10's copy voice rules, restated at the prompt level so the LLM does not default to chatbot affirmation patterns.
2. **Calm, precise, Socratic.** Plain, complete sentences. Verbs over adjectives. No emoji. No exclamation marks. Match DESIGN.md §10 verbatim.
3. **Analogy is concept-derived.** When the analogical fallback fires, the AI selects a source domain familiar to the typical adult learner that maps cleanly onto the target concept's causal structure. The kitchen analogy referenced in §3.1 is illustrative only — the AI must not template it. For "kubernetes," the analogy might be a shipping yard with containers; for "cognitive bias," a familiar perception illusion. The AI generates the analogy fresh from the concept each time.

Both prompts (`generate-from-sketch` and `threshold-chat`) carry the anti-filler and Socratic-voice constraints. Voice drift is a regression; see §8 acceptance criterion #9.

### 5.2 Learning Commons client

New module: `lc_client.py` or `learning_commons.py`.

**Public surface.**

```python
class LCClient:
    def search_concept(self, concept: str) -> LCSearchResult | None: ...

@dataclass(frozen=True)
class LCSearchResult:
    top_score: float
    standards: list[LCStandard]  # sorted by score desc, max 5

@dataclass(frozen=True)
class LCStandard:
    case_uuid: str
    statement_code: str | None
    description: str
    jurisdiction: str
    score: float
```

**Behavior.**

- Reads `LEARNING_COMMONS_API_KEY` from env. If missing, `search_concept` returns `None` immediately (treated identically to LC unreachable).
- Hard timeout: 800ms wall-clock per call. Beyond timeout, returns `None`.
- HTTP errors (non-200) → returns `None`. Logs at `WARNING` level with status + request_id for ops visibility.
- In-process LRU cache keyed on the lowercased, normalized concept string. Cache size 256, TTL 24h. Cuts cost and latency on repeated submits of the same concept across users.
- No retries. LC is best-effort enrichment; a single failure falls through cleanly.

**Threshold gate.** A separate function `should_enrich_with_lc(result: LCSearchResult | None) -> list[LCStandard] | None` applies the three-rule check from §3.3.2 and returns the standards to inject (top 2-3 by score), or `None` if the gate fails.

### 5.3 Endpoint shape

Today's `POST /concepts` (or equivalent) takes a payload that assumes source text. Update:

```jsonc
POST /concepts
{
  "name": "Photosynthesis",
  "starting_sketch": "Plants take in light and somehow make sugar…",
  "source": null  // or { "type": "text"|"url"|"file", "text": "...", "url": "...", "filename": "..." }
}
```

When `source == null`, the handler dispatches to `generate_provisional_map_from_sketch`. When `source` is present, it dispatches to today's path.

The existing fuzzy-area input is removed from the payload entirely. Confusion signal is captured implicitly in the sketch text and (optionally) inferred by the AI from gaps. The 2026-05-01 redesign carried `fuzzyText` into a `Fuzzy area:` suffix on `thresholdContext`; that suffix is dropped.

**Server-side validation (defense in depth).** The handler enforces the §3.2 substantiveness rule independently of the client; client-side CTA-disabling is a UX optimization, not the gate. The check, before any AI call:

- `name` empty/whitespace-only → `422` with `{"error": "missing_concept", "message": "Concept name required."}`
- `source == null` AND `is_substantive_sketch(starting_sketch) == False` → `422` with `{"error": "thin_sketch_no_source", "message": "Add more to your sketch, or attach source material — either path opens the build."}`

The `is_substantive_sketch(text: str) -> bool` helper lives in the same module as `generate_provisional_map_from_sketch` so frontend and backend share the same definition through a synchronized heuristic spec. The frontend's TypeScript/JS implementation must mirror it byte-for-byte (same stopword set, same ≥8 token threshold, same "don't know" pattern list), and a shared test fixture with ~30 inputs (substantive / thin / borderline) verifies parity. A divergence between client and server checks is a release-blocker.

The 422 response surfaces back to the frontend, which renders `message` in the same chip footer the client-side validation would have used — so a learner who somehow bypasses the client gate still sees the same strategy-framed copy, not a server-error toast.

This server-side check is the only thing standing between principle #7 and a buggy/old/malicious client triggering source-less generation on a thin sketch. It is not optional.

### 5.4 Telemetry (load-bearing)

Add structured-log events for:

- `concept_create.chat.turn_started` — `{turn, has_prior_reply}`
- `concept_create.chat.turn_replied` — `{turn, reply_len, used_fallback: bool}`
- `concept_create.summary.shown` — `{has_concept, has_sketch, sketch_len}`
- `concept_create.summary.edited` — `{chip}`
- `concept_create.source.added` — `{type}`
- `concept_create.build_clicked` — `{has_source, has_sketch}`
- `concept_create.lc.queried` — `{concept_hash, top_score, standards_count, latency_ms}`
- `concept_create.lc.enrichment_applied` — `{standards_count}` (only when gate passed)
- `concept_create.lc.enrichment_skipped` — `{reason: "no_results"|"low_score"|"non_k12"|"timeout"|"error"|"key_missing"}`
- `concept_create.build_blocked` — `{reason: "missing_concept"|"thin_sketch_no_source", origin: "client"|"server"}` — fires every time the build is prevented (whether by client-side CTA-disable or by server-side 422). The `origin` field lets us spot client/server validation drift: in a healthy state, all blocks should fire as `origin: client` and zero as `origin: server`. Server-side blocks indicate either a client bug, an old cached client, or an attempted bypass — all worth knowing about.
- `concept_create.ai_call` — `{stage, model, tokens_in, tokens_out, latency_ms, cost_usd_est}` — fires after every AI call within the concept creation flow. `stage` is one of: `chat_turn_2_probe`, `chat_fallback`, `summary_extract` (if extracting canonical concept name from chat replies is a separate call), `generation_pure`, `generation_lc_enriched`. Aggregating across `stage` per session gives the actual model-call count and dollar cost per concept created — the data that backs the §10 cost risk row.

These events power post-launch diagnostics: where the chat actually fails, how often LC enrichment is applied, where the K-12 heuristic is wrong, where build is blocked and at which layer, and how AI cost per concept evolves as the flow stabilizes. The `build_blocked` and `ai_call` events are load-bearing for principle #7 enforcement and cost governance respectively — both must be wired before launch.

## 6. Open questions for implementation

These are deliberately left for the implementation plan, not for the brainstorm.

- **K-12 detection heuristic.** §3.3.2 specifies a loose initial heuristic (jurisdiction + statementCode/description present). After the initial launch, telemetry on `enrichment_skipped: non_k12` will reveal false negatives; tighten or loosen from there. The brainstorm verified that score ≥ 0.70 is a reasonably clean threshold for "real K-12 match" vs "garbage closest-match."
- **LC cache invalidation strategy.** TTL 24h is a guess. If LC's standards change rarely (likely), this can be longer. If they update frequently, shorter.
- **Exact AI copy for chat turns.** The shape is fixed. The literal token strings should go through copy review before launch, not be set in stone here.
- **Concept name extraction from chat.** The AI extracts the canonical name from the learner's reply to turn 1. Open: does the AI also normalize/correct casing (e.g., "photosynthesis" → "Photosynthesis")? Implementation choice.
- **Modal shell refactor.** `buildContentInputUI` is currently a giant function that branches on `showNameField`. Implementation may want to split that into two builders (`buildInlineExtractUI` for the non-modal overlay path, `buildConversationalCreateUI` for this new flow) rather than further nesting branches.
- **Backend test fixtures.** The new generation path needs golden-fixture tests on `{concept, sketch}` → `ProvisionalMap` for at least: K-12 science (LC enriched), college-level (no LC), and an explicit thin-sketch case (analogical-fallback path).

## 7. Out of scope (deliberate non-goals)

These are *real* opportunities surfaced during the LC verification, parked here so the implementation doesn't try to bundle them in.

- **Prerequisite-aware Interleaving Bridge.** The LC `prerequisites` / `builds-towards` / `related-standards` endpoints are empty as of the 2026-05-02 verification. When LC populates those, the bridge can use them. Until then, the bridge stays inferred from socratink's own graph topology per existing behavior.
- **LC Evaluator gating.** Repair-artifact quality scoring against LC's literacy / motivation evaluators. Real value, separate brainstorm.
- **Standards-alignment metadata on tiles.** Each crystal carrying its NGSS / CCSS code as a tag. Easy add later, no learner-visible behavior change required.
- **Learner Variability Navigator signals.** Internal-only routing signals. Speculative until we see the dataset shape and confirm it doesn't leak into UX as a category.
- **MCP integration for LC.** Today's spec uses REST. MCP is an option later, after the integration is stable and we want to remove the explicit code path.
- **Adaptive chat (pattern C from brainstorm).** AI deciding turn count dynamically. The 2-turn-with-analogical-fallback (pattern E) is what's bound; pure adaptive can be revisited after we have session telemetry on where pattern E actually breaks.
- **The fuzzy-area input as an explicit field.** Removed in this redesign. Confusion is captured implicitly in the sketch and (potentially) inferred by the AI. If post-launch telemetry shows we're losing important confusion signal, an explicit field can be revived as a follow-on.
- **Going back to the chat from the summary card.** Deliberate omission — see §3.2.
- **Persisted chat history / "previous conversations" view.** The chat is ignition, not a record. The captured sketch is the only artifact retained.

## 8. Acceptance criteria

The redesign ships when **all** of these hold:

1. A learner can complete the flow end-to-end with **no source material** attached, and the resulting graph renders with the existing Provisional Graph treatment.
2. A learner can complete the flow end-to-end with source material (text / URL / file) attached, and the source-attached behavior is unchanged from today.
3. With LC unreachable (network blocked, key removed, host down), the source-less flow still completes within normal latency budget, and `concept_create.lc.enrichment_skipped` logs the correct reason.
4. With a non-K12 concept (e.g., "metacognition", "kubernetes"), the source-less flow completes via pure-AI generation, and LC enrichment is correctly skipped (`reason: "low_score"` or `reason: "non_k12"`).
5. The 2-turn chat is a hard stop. There is no UI affordance to add a third turn or reopen the chat once the summary card appears.
6. The summary card respects "one violet accent per screen": the build CTA is the only hard-violet element at rest.
7. `bash scripts/qa-smoke.sh` passes against a deploy preview.
8. Visual smoke: dark-mode and light-mode screenshots of the chat stage, the summary card with no source, and the summary card with source attached, attached to the PR description.
9. **AI voice review (release-blocker).** Manual review of 10 sample threshold-chat sessions sampling concepts across K-12 academic (e.g., photosynthesis, long division), college / adult-learning (e.g., metacognition, machine learning), and abstract / non-academic (e.g., kubernetes, cognitive bias). Confirm: no acknowledgment / affirmation / filler tokens in any AI turn; the analogy in any analogical-fallback turn is concept-derived (not templated); no exclamation marks, no emoji. Any drift is a release-blocker, not a polish item.
10. **Substantiveness validation works.** Manual smoke: enter `idk` as the sketch with no source attached → build is disabled, sketch chip shows the strategy-framed footer line, learner can resolve by editing the sketch substantively OR by attaching source. Build re-enables in both cases.

## 9. Implementation sequencing (handoff to writing-plans)

The plan should sequence in this order:

1. **Backend first.** Build `LCClient` with the threshold gate. Build `generate_provisional_map_from_sketch` with optional `lc_context`. New prompt at `app_prompts/generate-from-sketch-system-v1.txt`. Wire endpoint dispatch in the create-concept handler. Test with curl + golden fixtures *before* touching frontend.
2. **Frontend second.** Build the chat surface in isolation (state machine + composer). Build the summary card in isolation (chips + edit interactions). Wire them together. Connect to the (already-tested) backend. Remove the old form template and CSS.
3. **Telemetry third.** All structured-log events from §5.4 wired before launch. Without them, post-launch diagnostics are blind.
4. **Bindings docs last.** Update DESIGN.md §3 Screen 1 to reflect that threshold capture is now conversational (not a form). Add a note to UBIQUITOUS_LANGUAGE.md if `starting sketch` (the new term for the captured threshold output) needs codifying.

## 10. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Pure-AI generation produces hallucinated structure for non-K12 concepts the AI doesn't actually know | The graph is framed as hypothesis (DESIGN.md §3 Screen 2). The cold attempt + repair loop catches and repairs hallucinated structure. The system makes no claim of correctness pre-attempt. |
| LC API quality degrades or schema changes silently | Threshold gate + score-based filtering. If quality drops, `enrichment_applied` rate falls; we notice. If schema breaks, `LCClient` returns `None`; nothing breaks downstream. |
| Chat feels like a wizard, not a conversation | Pattern E is the brainstormed compromise. Post-launch, telemetry on `chat.turn_replied.reply_len` distribution + drop-off reveals whether learners are engaging or speed-clicking. If speed-click rate is high, the chat copy or pacing needs work — but the architecture still holds. |
| Learners with source feel forced through the chat for no reason | The chat captures the sketch — that's the threshold (DESIGN.md §3 Screen 1), and it remains required even when source is provided. The chat is not a tax on source-bearing learners; it's the same threshold capture they would have done in the form, just conversational. |
| K-12 detection heuristic has false negatives (e.g., misses real K-12 concepts) | Loose initial heuristic. Telemetry on `enrichment_skipped: non_k12` reveals the false-negative space. Iterate on the heuristic post-launch. |
| Increased AI cost from chat turns + source-less generation | Chat is 2 turns max. Source-less generation is 1 model call (same as existing extraction). Net: 3 model calls per concept creation vs. 1 today (extraction). Real but bounded. Cost telemetry should be added. |
| AI voice drifts to chatbot affirmation patterns ("That's a great start!", "Let me think…") | Threshold-chat system prompt explicitly forbids acknowledgment/affirmation/filler/preamble tokens (§5.1). Acceptance criterion #9 reviews 10 sample sessions across diverse concepts before launch. Voice regression is a release-blocker. |
| Zero-signal sketch (`idk`) bypasses validation and triggers hallucinated graph from training prior | Substantiveness check on the sketch (§3.2): non-substantive sketch + no source → build disabled. The contract is honest: source-less generation requires a substantive sketch; sourced generation does not. |

---

## Appendix A — Brainstorm provenance

Decisions made during the brainstorm session, in order:

1. Scope: **D** (hybrid: chat opens, form completes).
2. Pattern: **E** (lean two-turn backbone + analogical fallback).
3. Principle: chat is ignition; summary card is handoff. The product is graph / repair / reconstruction.
4. Layout: **P2** (chip-style attachment).
5. Source-less generation: revised option 4 (pure-AI primary + optional LC enrichment when high-confidence + K-12).
6. Integration mechanism: REST (MCP parked as future option).

LC verification artifacts (queries + responses) saved to `/tmp/lc-probes/` during the session. Score thresholds and audience boundary findings are codified in §3.3.2 and §6.

## Appendix B — Anti-patterns this spec deliberately rejects

For future-proofing against the "let's just add one more thing" drift:

- A "tell me more" button in chat that adds a third turn.
- A persistent chat history accessible from the dashboard.
- Auto-fetching Wikipedia / web content when the learner declined to attach source.
- Showing the learner that LC was queried, what it returned, or which standards were used as enrichment.
- Adding a confidence indicator on the provisional graph based on whether LC enrichment was applied.
- Promoting source material to a required field in any state.
- Re-introducing the fuzzy-area as an explicit input field "for power users."
- A chat-style interface anywhere downstream (drill, repair, re-drill). Those surfaces have their own design and are not chat surfaces.
- "Friendly" AI affirmations or acknowledgments in any chat turn (`"Great start!"`, `"Got it"`, `"Fair enough"`, `"That's a tricky one"`).
- A templated kitchen analogy (or any other fixed-template analogy) used regardless of concept. The analogy is concept-derived every time.
- Allowing `idk` / `?` / keyboard mash to bypass build validation when no source is attached. The honest contract is: source-less requires substantive sketch.
- **The hallucinate-and-present anti-pattern.** Drafting a provisional graph from the model's prior knowledge and presenting it as the learner's seeded draft. Principle #7 binds against this categorically; §3.2's substantiveness validation is the operational defense; the truth table in §3.2 names the exact state where this anti-pattern would otherwise fire (no source + thin sketch). Any future "let's just generate something so the learner sees a graph" suggestion fails review here.
- A "smart" backend that auto-derives a sketch from the concept name when the sketch is thin (e.g., "I'll fill in 'cells use sugar from photosynthesis to make energy' if the learner only typed 'photosynthesis'"). Same anti-pattern, different costume — the system is still substituting its own model for the learner's.
