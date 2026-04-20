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
- **Contract**: Exploratory question ("What do you think this involves?"). Explicitly unscored.
- **Generative Commitment**: Requires a minimum threshold (3+ words, no "idk") to unlock study.
- **Zero-Schema Detection**: If the learner is completely lost, the AI seeds 2-3 concepts and asks for a micro-generation.
- **Outcome**: Node transitions to `primed`.

### Phase 2: Targeted Study (Correction)
- **Goal**: Provide corrective feedback while the prediction error is fresh.
- **Contract**: Immediate access after cold attempt. 2-3 second "ADHD beat" delay.
- **UX**: Highlights divergence from the learner's guess. Mechanism text is only for the attempted node.
- **Outcome**: Node remains `primed`; `drill_phase` becomes `re_drill`.

### Phase 3: Spaced Re-Drill (Proof Event)
- **Goal**: Record evidence of long-term retrieval after the working memory buffer is cleared.
- **Buffer Flush**: 10-15 minutes of interleaved work on other nodes. Minimum 5 minutes.
- **Contract**: Demands multi-step causal reconstruction. Rubric: (a) initiating condition, (b) causal transition, (c) resulting state.
- **Outcome**: `solid` classification → `solidified` recorded. Non-solid classification → `drilled` recorded.
- **Evidence semantics**: `solidified` is the record of at least one solid spaced reconstruction. It is not a claim about the learner's mind or permanent ability.

---

## 3. State Model & Transitions

### Node States
Each state is a persisted record of a specific evidence event. States describe what Socratink has on record, not what the learner knows.

- `locked`: No attempt recorded; prerequisites not yet satisfied.
- `primed`: A substantive cold attempt is recorded; study is unlocked.
- `drilled`: A non-solid spaced reconstruction is recorded; node is return-worthy.
- `solidified`: At least one solid spaced reconstruction is recorded. Evidence, not mastery.

### Containers vs. Drill Targets
- Core thesis, backbone rooms, and child rooms are drillable in the MVP loop.
- Clusters are containers and synthesis surfaces in MVP, not primary drill targets.
- Cluster state is derived from the state of its child rooms and branch context.

### Valid Transitions
- `locked` → `primed` (via Cold Attempt)
- `primed` → `drilled` (via Non-solid Re-drill)
- `primed` → `solidified` (via Solid Re-drill + Spacing)
- `drilled` → `solidified` (via Solid Re-drill + Spacing)

### Persisted Fields (per node)
- `drill_status`: locked | primed | drilled | solidified
- `drill_phase`: cold_attempt | study | re_drill | null
- `cold_attempt_at`, `study_completed_at`, `re_drill_eligible_after` (timestamps)
- `gap_type`, `gap_description` (for `drilled` nodes)

---

## 4. Side Panel & Result States

The panel must be mode-pure with no content bleed.

### Seven Panel Modes
1. **Inspect**: Orientation. Shows prerequisites, study access, or re-drill readiness.
2. **Cold-Attempt-Active**: exploratory question + transcript. No scores.
3. **Study**: Mechanism text + normalization message.
4. **Re-Drill-Active**: Reconstruction demand + transcript.
5. **Post-Re-Drill**: Result card (Solidified/Needs Revisit) + Trajectory Contrast. Sticky until `Continue`.
6. **Session-Complete**: Session guardrail reached. Save-point copy.
7. **Repair-Reps**: Optional typed causal micro-practice after study completion or non-solid re-drill. No scores, no graph mutation, no interleaving credit, no mastery unlock.

### Result State UX
- **Solidified**: Strongest sensory celebration (crisp animation, satisfying sound). "Clear" trajectory.
- **Needs Revisit (Drilled)**: No celebration. "Wise feedback": High standards + belief + specific strategy-focused next step.
- **Normalization (Cold Attempt)**: "Most learners get this wrong the first time. Your guess just primed your brain."

---

## 5. Traversal & Routing

### In-Node Routing (AI to Frontend)
- `PROBE` / `SCAFFOLD`: Stay on node, provide help, no state mutation.
- `NEXT`: Resolve node phase, update graph state, offer traversal.
- `SESSION_COMPLETE`: Trigger guardrails.

### Session Traversal (Next Steps)
1. **Prefer `advance`**: Deeper into the current branch after `solidified`.
2. **Prefer `return/repair`**: Revisit a `drilled` node once spacing is met.
3. **Prefer `branch`**: Enter a newly unlocked area.
4. **Interleaving Recommendation**: After Phase 2, recommend a cold attempt on a *different* node to flush the buffer.

---

## 6. Guardrails & Constraints
- **Duration Cap**: Disabled by default in the current MVP; configurable via `DRILL_SESSION_TIME_LIMIT_SECONDS`.
- **Node Cap**: 4 nodes per session.
- **Retrieval Ceiling**: Max 3 successful retrievals per node per session.
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
