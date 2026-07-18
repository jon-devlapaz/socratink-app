# socratink — Product Specification

This document is the binding design and implementation contract for socratink. It defines the product philosophy, the cognitive architecture, the state model, and the learner-facing UX.

> Read alongside [evidence-weighted-map.md](evidence-weighted-map.md). That doctrine governs what the graph may and must not claim. Where wording here could be read as "the graph shows what the learner knows," the evidence-weighted-map doctrine controls: the graph shows what Socratink has evidence for.

Accepted operational learner-continuity contracts are split into:

- [source-less route continuity and evidence preservation](source-less-route-continuity-spec.md)
- [learner-state sync honesty](learner-state-sync-honesty-spec.md)
- [learner wait and recovery](learner-wait-and-recovery-spec.md)

---

## 1. Product Thesis
The enemy is the **illusion of competence**. Most learning tools reward exposure and recognition. socratink rewards **reconstruction**.

The goal is to make a hard cognitive act feel magnetic:
- **Expose** current model (Cold Attempt) — first evidence event.
- **Repair** where the attempt diverged from the mechanism (Targeted Study).
- **Reconstruct** under spacing (Spaced Re-Drill) — the only event that records `solidified`.
- **Accumulate** evidence on the graph; trust grows from recorded reconstruction, not from reading.

The graph is an evidence-weighted map. The map starts as a hypothesis. It earns trust through learner-generated evidence. Only spaced reconstruction mutates graph truth to `solidified`.

### Unifying Principle: Metacognitive UX
The product is designed for the learner's awareness of their own cognitive process. We don't just present content; we optimize how accurately the learner can perceive, interpret, and trust their own understanding.

| Surface | Metacognitive Function |
|---|---|
| **Cold Attempt** | Reveals the shape of what is unknown; frames discovery as exploration. |
| **Targeted Study** | Anchors correction to the specific prediction error just generated. |
| **Spacing Block** | Teaches that "feeling of knowing" (fluency) is a cognitive illusion. |
| **Trajectory Contrast** | Shows how metacognitive predictions were wrong to update beliefs about struggle. |
| **The Graph** | Shows what Socratink has evidence for — not what the learner knows. Topology is a hypothesis; node state is the accumulated evidence of actual reconstruction. |

---

## 2. The Learning Loop (Three Phases)
Every drillable node on the graph must move through these three phases. No phase may be skipped or collapsed.

### Phase 1: Cold Attempt (Exploration)
- **Goal**: Generate a prediction error to prime encoding.
- **Contract**: Exploratory question ("What do you think this involves?"). Learner-facing surfaces remain unscored; the system may privately classify the attempt to derive repair/study routing.
- **Generative Commitment**: Cold attempts unlock study only when the latest turn is a recordable learner attempt (`answer_mode === "attempt"`, `score_eligible === true`, usable classification) and drill-evaluation generative commitment is true. Non-recordable help/scaffold turns stay support turns and do not append evidence.
- **Learner Goal**: A learner goal may frame relevance, route emphasis, and local prompt copy. It is not evidence, is not graded, and must not mutate graph truth.
- **Zero-Schema Detection**: If the learner is completely lost, the AI seeds 2-3 concepts and asks for a micro-generation.
- **Outcome**: A recordable learner attempt is appended to the training record. Derived state becomes `primed` or `needs repair` depending on the evidence.
- **Persistence**: The attempt is recorded before study reveal. No downstream mastery unlock evaluation runs from a cold attempt alone.

### Phase 2: Targeted Study (Correction)
- **Goal**: Provide corrective feedback while the prediction error is fresh.
- **Contract**: Immediate access after cold attempt. The current inline flow uses an explicit reveal CTA; a future treatment may add a 2-3 second transition beat before study appears.
- **UX**: Highlights divergence from the learner's guess. Mechanism text is only for the attempted node and must not expose unattempted nodes.
- **Outcome**: Study reveal is recorded on the training record. Study alone does not produce `solidified`.

### Phase 3: Spaced Re-Drill (Proof Event)
- **Goal**: Record evidence of long-term retrieval after the working memory buffer is cleared.
- **Buffer Flush**: Current runtime uses an 18-hour elapsed interval before a strong attempt can count as spaced evidence. The 10-15 minute interleaved-work buffer remains product intent for the future scheduler, not the shipped derivation.
- **Contract**: Demands multi-step causal reconstruction. Rubric: (a) initiating condition, (b) causal transition, (c) resulting state.
- **Outcome**: spaced strong reconstruction can derive `solidified`. Non-solid evidence stays `primed` for a single lapse or derives `needs repair` when gaps persist.
- **Evidence semantics**: `solidified` is the record of at least one solid spaced reconstruction. It is not a claim about the learner's mind or permanent ability.
- **Prompt variation**: Re-drill prompts should vary the angle across attempts on the same node (self-explanation, summarization, teaching, problem-posing) to prevent linguistic mimicry.
- **Recovery**: Repeated non-solid results across sessions should escalate scaffolding per the Bottleneck Recovery contract in [docs/design/socratink-ux.md](../design/socratink-ux.md) §6 without treating scaffolded generation as independent reconstruction.

---

## 3. State Model & Transitions

### Node States
Node state is derived from the browser-local training record, not stored as mutable graph truth. States describe what Socratink has on record, not what the learner knows.

- `null`: No learner reconstruction attempt is recorded for this node. Render silently or as ready/locked based on predecessor availability.
- `primed`: Learner reconstruction evidence is recorded; study, repair, review, or spaced-attempt routing is derived from the latest attempt.
- `needs repair`: Current evidence contains named gaps that require repair.
- `solidified`: At least one solid spaced reconstruction is recorded. Evidence, not mastery.

### Containers vs. Drill Targets
- Core thesis, backbone rooms, and child rooms are drillable in the MVP loop.
- Clusters are containers and synthesis surfaces in MVP, not primary drill targets.
- Cluster state is derived from the state of its child rooms and branch context.
- A cluster branch is available only when its governing backbone is `solidified` and all incoming prerequisite clusters are already `solidified`.

### Valid Derivation
- no attempts → `null`
- first strong or partial attempt → `primed`
- first thin or wrong-direction attempt → `needs repair`
- single non-strong lapse after prior evidence → `primed`
- repeated non-strong evidence → `needs repair`
- strong attempt followed by another strong attempt after spacing → `solidified`

### Persisted Training Fields

Training evidence is stored separately from `concept.graphData` under
`socratink:training:v1:<conceptId>`.

- concept provenance: `source_mode`, `grounding`, `source_ref`
- learner sketch: `{ text, at }`
- per-node attempts: `id`, `kind`, `at`, `user_text`, `classification`, `gaps`, `grader_version`
- per-node `study_revealed_at`
- per-node repairs: learner-authored repair text and timestamp

All behavior and state must derive from the training record (deriving
`null | primed | needs repair | solidified`).

Legacy `drill_status`, `drill_phase`, gap metadata, timer fields, and
`concept.state` in `graphData` are compatibility inputs only; new behavior must
derive from the training record. Exception: legacy `drill_status: "primed"` +
`drill_phase: "study"` nodes with no attempts may record `study_revealed_at`
with `attempts: []` when the learner reveals study, so the app preserves the old
study route without inventing reconstruction evidence.

The knowledge map remains the provisional structure and legacy compatibility
surface until every view is rebound to the training derivation.

Current surface binding status:
- concept-page entry state, next actions, inline reconstruction, study reveal, and repair panels derive from `socratink:training:v1:<conceptId>`
- Library reconstruction text binds to learner-written training records
- Library badges, Desk tiles, and Sidebar concept markers derive concept-level badges from the training record, with legacy graph/status fields as compatibility fallback
- Map/graph badge surfaces that still exist outside the concept-page route may use legacy graph/status fields until their binding rollout lands

### Phase Tracking

Each node derives its next action within the three-phase loop:
- `cold_attempt`: no learner attempt is on record
- `study`: an attempt exists and study has not been revealed
- `repair`: current evidence has named gaps after study reveal
- `review`: study has been revealed but spacing or evidence conditions do not yet support solidification
- `spaced_attempt`: a new reconstruction attempt is available

The frontend uses derived `next_action`, not persisted `drill_phase`, to choose the concept-page mode.

Concept pages retain `source_mode` and the launch attempt as route provenance,
but do not repeat the launch attempt in the active reconstruction surface. The
local cold attempt must stay free of answer-shaped recall cues. The learner's
saved local draft becomes the comparison artifact after generation.

Source-less first entries may use `learner_scaffold.tailoring_anchor` internally
to shape the cold-attempt prompt. It should not render as learner-facing AI
self-explanation: the learner sees the reconstruction target, not prompt
plumbing, feedback on correctness, diagnosis of a gap, a revealed mechanism, a
hidden target, or what the learner missed.

After a source-less learner saves the first draft and explicitly reveals study,
the concept page renders a post-reveal comparison on the same surface before
expanding the full route margin. This comparison may show the learner's draft,
the same-entry study note, and named gaps when recorded. It must not show
score/tier/band, diagnose the learner, reveal future entries, or count as graph
truth. The normal comparison-exit action is `Return to route`, which writes
UI-only acknowledgement state so return/reload can restore the expanded
workspace; it does not append training evidence or imply progress. The repair
branch is the exception: it suppresses that exit, shows the repair panel, and
after a repair is saved renders an interleaving bridge. If a later room is
genuinely ready under the existing training derivation, that room is the
primary suggestion; otherwise a short break is primary. A break remains visible
when a room is suggested, while `Pressure-check this link` stays behind
progressive disclosure as graph-neutral fresh practice. Saving the repair,
following the suggestion, taking a break, and pressure-checking do not mutate
graph truth or record new reconstruction evidence.

---

## 4. Inline Concept Entry & Result States

The current runtime does not use a standalone side-panel DOM for these states. The concept route stays visible, `#drill-chamber-view` mounts inline inside the active concept entry during drills, and study, repair, comparison, and result surfaces live in the same concept-entry work column. Any future side-panel treatment must preserve the same mode purity with no content bleed.

### Surface Modes
1. **Inspect**: Orientation. Shows prerequisites, study access, or re-drill readiness.
2. **Cold-Attempt-Active**: local node/scaffold prompt + inline chamber. No scores.
3. **Study**: Mechanism text + normalization message.
4. **Re-Drill-Active**: reconstruction demand + inline chamber transcript.
5. **Post-Re-Drill**: Result card (`solidified` / `needs repair`) + Trajectory Contrast. Sticky until `Continue`.
6. **Session-Complete**: Session guardrail reached. Save-point copy.
7. **Repair-Reps**: Optional typed causal micro-practice after study completion or non-solid re-drill. No scores, no graph mutation, no interleaving credit, no mastery unlock.

### Result State UX
- **Solidified**: Strongest sensory celebration (crisp animation, satisfying sound). "Clear" trajectory.
- **Needs Repair**: No celebration. "Wise feedback": High standards + specific strategy-focused next step.
- **Normalization (Cold Attempt)**: "Most learners get this wrong the first time. Your guess just primed your brain."
- **No Training Evidence**: Low-information, reduced-contrast state. Available only when predecessor evidence allows it; otherwise clearly unavailable.
- **Primed**: Warm, open state. Signals "entered but not yet challenged" and stays visually distinct from both unavailable/no-evidence and needs-repair states.

Show next-horizon nodes (3-5 adjacent available items) rather than the entire remaining graph. Detailed gap taxonomy belongs in the active concept-entry repair/result surface.

---

## 5. Traversal & Routing

The backend returns a structured drill result. The important fields are:
- `agent_response`
- `classification`
- `gap_description`
- `routing`
- `node_id`
- `answer_mode`
- `score_eligible`
- `response_tier`
- `response_band`

`classification` describes the quality of understanding. `routing` describes what the conversation should do next. `response_tier` and `response_band` describe the transient quality of the attempt for trajectory contrast display. During cold attempts, classification may be stored privately for routing, but learner-facing score/tier/band surfaces stay absent.

### Classification Sufficiency

The `solid` classification answers one question: did the learner reconstruct the causal mechanism from long-term memory, in their own words, with the critical links intact?

Three conditions must all be satisfied:
1. **Causal chain, not vocabulary.** The learner connected the steps in the correct directional sequence. Right keywords with no causal links = not solid.
2. **Spacing was satisfied.** Structural precondition enforced before the re-drill fires. Not an AI judgment.
3. **The attempt was self-generated.** If the AI's scaffolding essentially walked the learner through the mechanism during this drill turn, the classification should reflect assisted generation, not independent reconstruction.

The classification rubric in the system prompt must be concrete: "Does the response contain (a) the initiating condition, (b) the causal transition, and (c) the resulting state? If all three are present and correctly linked, classify as solid."

The system should err toward false negatives. A slightly strict gate protects graph credibility better than a slightly loose one.

### AI Assistance Guardrails

AI support is allowed only if it preserves the three-phase loop, the drill contract, and graph truth:
- the learner must complete the cold attempt before the study view is shown
- the study view must not be accessible before a learner reconstruction attempt exists, except for legacy `primed` + `study` compatibility where no prior attempt exists; that exception may preserve the old study route but must not invent reconstruction evidence or weaken the three-phase loop, drill contract, or graph truth
- scaffolds and feedback may clarify the gap after an attempt, but must not silently change the target
- AI-generated explanation quality does not itself mutate graph state
- only persisted learner reconstruction evidence can derive `primed`, `needs repair`, or `solidified`
- study, Repair Reps, Gap drills / `Pressure-check this link`, starting-map capture, confidence ratings, and AI scaffolding must not produce `solidified`
- the AI must remain sparse during drill; if the AI talks more than the learner, the passive trap has been triggered
- the AI must detect zero-schema states and pivot to scaffolded generation

### In-Node Routing (AI to Frontend)
- `PROBE` / `SCAFFOLD`: Stay on node, provide help, no state mutation.
- `NEXT`: Resolve node phase. For recordable, non-graph-neutral attempts, append training evidence, re-render derived state, and offer traversal. Graph-neutral gap drills and non-recordable turns may end the drill UI without appending training evidence or mutating graph state.
- `SESSION_COMPLETE`: Trigger guardrails.

Recordable attempts behave as follows:
- Spaced strong reconstruction evidence appends the attempt, derives the current node as `solidified`, allows downstream unlock evaluation, and triggers the strongest sensory celebration.
- Non-solid evidence appends the attempt and structured gaps, derives `needs repair` when the gap evidence warrants it, does not treat the node as mastered, does not fake unlocks, and uses wise feedback instead of celebration.
- `SESSION_COMPLETE` ends or pauses the session, does not imply mastery by itself, and is framed as a save point.

### Session Traversal (Next Steps)
1. **Prefer `advance`**: Deeper into the current branch after `solidified`.
2. **Prefer `return/repair`**: Revisit a `needs repair` node once repair and spacing make reconstruction meaningful.
3. **Prefer `branch`**: Enter a newly unlocked area.
4. **Interleaving Recommendation**: After Phase 2, recommend a cold attempt on a *different* node to flush the buffer.

---

## 6. Guardrails & Constraints
- **Duration Cap**: Backend-configurable via `DRILL_SESSION_TIME_LIMIT_SECONDS`, but bypassed by the current frontend MVP.
- **Node Cap**: 4 nodes per session remains the intended guardrail, currently bypassed by the frontend.
- **Retrieval Ceiling**: Max 3 successful retrievals per node per session remains the intended guardrail, currently bypassed by the frontend.
- **AI Sparse Contract**: The AI must talk less than the learner. Sparse, gap-identifying feedback only.
- **Moat Constraint**: AI must never pre-answer the target or inflate mastery.
- **Session Ending**: End at a point of engagement, not exhaustion. Session-ending copy should feel like a save point, not a punishment.

---

## 7. Current Target Flow

The intended happy path is:
1. learner creates a concept
2. extraction produces a knowledge map
3. graph renders from `concept.graphData`; training evidence initializes under `socratink:training:v1:<conceptId>`
4. learner writes a reconstruction on the first available node
5. recordable attempt is stored; derived state and next action update; study can reveal
6. learner reads targeted study
7. system recommends next cold attempt on a different node (interleaving)
8. learner completes 1-2 more cold attempts and studies (buffer flush period)
9. system recommends spaced re-drill on the first node
10. backend returns structured drill result
11. frontend appends the attempt to the training store
12. concept page, Library reconstruction body, Library badges, Desk tiles, and Sidebar concept markers re-render from training evidence; remaining legacy graph/status fields are compatibility fallback only

---

## 8. Evaluation Checklist
*Ask these before shipping any feature:*
1. Does it preserve the three-phase loop?
2. Does it make the current target and phase clearer?
3. Does it reward real reconstruction or buffer echo?
4. Does the AI support the loop or replace the thinking?
5. Does it frame difficulty as exploration or evaluation?
6. Does the graph tell the truth?
7. Would the learner still choose this behavior if they knew how the system influenced them?
