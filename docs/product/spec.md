# socratink — Product Specification

This document is the binding design and implementation contract for socratink. It defines the product philosophy, the cognitive architecture, the state model, and the learner-facing UX.

> Read alongside [evidence-weighted-map.md](evidence-weighted-map.md). That doctrine governs what the graph may and must not claim. Where wording here could be read as "the graph shows what the learner knows," the evidence-weighted-map doctrine controls: the graph shows what Socratink has evidence for.

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
- **Generative Commitment**: Cold attempts use drill-evaluation generative commitment to decide whether study unlocks; source-less launch-pad generation uses the shared substantive-sketch gate (8+ substantive non-stopword tokens and no "don't know" pattern) before drafting a provisional map.
- **Zero-Schema Detection**: If the learner is completely lost, the AI seeds 2-3 concepts and asks for a micro-generation.
- **Outcome**: A learner attempt is appended to the training record. Derived state becomes `primed` or `needs repair` depending on the evidence.

### Phase 2: Targeted Study (Correction)
- **Goal**: Provide corrective feedback while the prediction error is fresh.
- **Contract**: Immediate access after cold attempt. 2-3 second "ADHD beat" delay.
- **UX**: Highlights divergence from the learner's guess. Mechanism text is only for the attempted node.
- **Outcome**: Study reveal is recorded on the training record. Study alone does not produce `solidified`.

### Phase 3: Spaced Re-Drill (Proof Event)
- **Goal**: Record evidence of long-term retrieval after the working memory buffer is cleared.
- **Buffer Flush**: Current runtime uses an 18-hour elapsed interval before a strong attempt can count as spaced evidence. The 10-15 minute interleaved-work buffer remains product intent for the future scheduler, not the shipped derivation.
- **Contract**: Demands multi-step causal reconstruction. Rubric: (a) initiating condition, (b) causal transition, (c) resulting state.
- **Outcome**: spaced strong reconstruction can derive `solidified`. Non-solid evidence stays `primed` for a single lapse or derives `needs repair` when gaps persist.
- **Evidence semantics**: `solidified` is the record of at least one solid spaced reconstruction. It is not a claim about the learner's mind or permanent ability.

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

Legacy `drill_status`, `drill_phase`, gap metadata, and timer fields in
`graphData` are compatibility inputs only; new behavior must derive from the
training record. Exception: legacy `drill_status: "primed"` +
`drill_phase: "study"` nodes with no attempts may record
`study_revealed_at` with `attempts: []` when the learner reveals study, so the
app preserves the old study route without inventing reconstruction evidence.

---

## 4. Side Panel & Result States

The panel must be mode-pure with no content bleed.

### Seven Panel Modes
1. **Inspect**: Orientation. Shows prerequisites, study access, or re-drill readiness.
2. **Cold-Attempt-Active**: exploratory question + transcript. No scores.
3. **Study**: Mechanism text + normalization message.
4. **Re-Drill-Active**: Reconstruction demand + transcript.
5. **Post-Re-Drill**: Result card (`solidified` / `needs repair`) + Trajectory Contrast. Sticky until `Continue`.
6. **Session-Complete**: Session guardrail reached. Save-point copy.
7. **Repair-Reps**: Optional typed causal micro-practice after study completion or non-solid re-drill. No scores, no graph mutation, no interleaving credit, no mastery unlock.

### Result State UX
- **Solidified**: Strongest sensory celebration (crisp animation, satisfying sound). "Clear" trajectory.
- **Needs Repair**: No celebration. "Wise feedback": High standards + specific strategy-focused next step.
- **Normalization (Cold Attempt)**: "Most learners get this wrong the first time. Your guess just primed your brain."

---

## 5. Traversal & Routing

### In-Node Routing (AI to Frontend)
- `PROBE` / `SCAFFOLD`: Stay on node, provide help, no state mutation.
- `NEXT`: Resolve node phase, append training evidence, re-render derived state, and offer traversal.
- `SESSION_COMPLETE`: Trigger guardrails.

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

---

## 7. Evaluation Checklist
*Ask these before shipping any feature:*
1. Does it preserve the three-phase loop?
2. Does it make the current target and phase clearer?
3. Does it reward real reconstruction or buffer echo?
4. Does the AI support the loop or replace the thinking?
5. Does it frame difficulty as exploration or evaluation?
6. Does the graph tell the truth?
7. Would the learner still choose this behavior if they knew how the system influenced them?
