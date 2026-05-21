# Learner Goal Thread Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the learner's stated goal shape the first drill question as relevance context without letting it mutate graph truth or grading.

**Architecture:** The existing source-less flow already saves the goal on the concept and as `metadata.learner_goal` in the knowledge map. This slice keeps that field through `models/knowledge_map_context.py::prune_context`, then teaches the drill prompt to use it only as relevance framing. Evaluation remains anchored to the active node mechanism and learner scaffold evidence goal.

**Tech Stack:** Python, pytest, Gemini structured-output prompt contract, Socratink knowledge-map JSON.

---

### Task 1: Preserve Learner Goal In Pruned Context

**Files:**
- Modify: `models/knowledge_map_context.py`
- Test: `tests/test_knowledge_map_context.py`

- [ ] **Step 1: Write the failing test**

In `tests/test_knowledge_map_context.py`, add `learner_goal` to `sample_map()` metadata:

```python
"learner_goal": "Explain why a thermostat turns heat on and off.",
```

Update `test_prune_context_for_backbone_target_keeps_dependent_cluster_shells()` expected metadata:

```python
assert pruned["metadata"] == {
    "thesis": "The thermostat closes a feedback loop.",
    "governing_assumptions": ["Room temperature can be measured."],
    "starting_map_context": "Thermostat control",
    "learner_goal": "Explain why a thermostat turns heat on and off.",
}
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_knowledge_map_context.py::test_prune_context_for_backbone_target_keeps_dependent_cluster_shells -v
```

Expected: FAIL because `prune_context()` does not include `learner_goal`.

- [ ] **Step 3: Write minimal implementation**

In `models/knowledge_map_context.py`, extend the metadata copy in `prune_context()`:

```python
"learner_goal": metadata.get("learner_goal"),
```

- [ ] **Step 4: Run context tests**

Run:

```bash
pytest tests/test_knowledge_map_context.py -v
```

Expected: PASS.

### Task 2: Add Goal Framing Guard To Drill Prompt

**Files:**
- Modify: `app_prompts/drill-system-v1.md`
- Test: `tests/test_drill_session_limits.py`

- [ ] **Step 1: Write the failing prompt contract test**

In `tests/test_drill_session_limits.py`, add a drill test next to `test_cold_attempt_passes_learner_scaffold_into_drill_contract`:

```python
def test_cold_attempt_passes_learner_goal_as_relevance_not_grading(self):
    """Goal may shape the question, but node grading stays local."""
    captured = {}
    knowledge_map = scaffolded_knowledge_map()
    knowledge_map["metadata"]["learner_goal"] = "Explain why thermostats avoid overheating a room."

    def fake_call(_client, *, model, contents, config):
        captured["contents"] = contents
        captured["system_instruction"] = getattr(config, "system_instruction", "")
        return drill_response(routing="NEXT", classification="deep")

    with (
        patch.dict(os.environ, {ai_service.DRILL_SESSION_TIME_LIMIT_ENV: "0"}),
        patch("ai_service._get_client", return_value=object()),
        patch("ai_service._call_gemini_with_retry", side_effect=fake_call),
    ):
        ai_service.drill_chat(
            knowledge_map=knowledge_map,
            concept_id="thermostat",
            node_id="c1_s1",
            node_label="Setpoint comparison",
            node_mechanism="server-resolved mechanism",
            messages=[],
            session_phase="init",
            drill_mode="cold_attempt",
            bypass_session_limits=True,
        )

    self.assertIn("learner_goal", captured["contents"])
    self.assertIn("Explain why thermostats avoid overheating a room.", captured["contents"])
    self.assertIn("use `metadata.learner_goal` only to frame relevance", captured["system_instruction"])
    self.assertIn("Do not grade against the broad learner goal", captured["system_instruction"])
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_drill_session_limits.py::DrillBypassAndDegradedResponseTests::test_cold_attempt_passes_learner_goal_as_relevance_not_grading -v
```

Expected: FAIL because `learner_goal` is pruned away and the system prompt has no explicit guard.

- [ ] **Step 3: Update the prompt guard**

In `app_prompts/drill-system-v1.md`, under `### Question Generation Instructions (Cold Starts)`, add:

```markdown
- If `metadata.learner_goal` is present, use it only to frame relevance: why this target node matters for what the learner wants to explain.
- Do not grade against the broad learner goal. Grade only against the Target Node mechanism, and when present, the Learner Scaffold `evidence_goal`.
```

- [ ] **Step 4: Run the targeted test**

Run:

```bash
pytest tests/test_drill_session_limits.py::DrillBypassAndDegradedResponseTests::test_cold_attempt_passes_learner_goal_as_relevance_not_grading -v
```

Expected: PASS.

### Task 3: Strengthen Runtime Cold-Attempt Instruction

**Files:**
- Modify: `ai_service.py`
- Test: `tests/test_drill_session_limits.py`

- [ ] **Step 1: Update the cold-attempt mode string**

In `ai_service.py`, replace the existing cold-attempt `system_prompt_extras +=` string with a multi-part string that keeps the current behavior and adds the goal guard:

```python
system_prompt_extras += (
    "\nMODE: COLD ATTEMPT. Ask an open exploratory question on init; do not reveal the mechanism. "
    "On turn, evaluate the learner's first genuine generative attempt against the rubric and populate "
    "classification, score_eligible, response_tier, response_band, and tier_reason. "
    "If metadata.starting_map_context is present, reference it as global context in one short clause, then ask one smaller target-node question. "
    "If metadata.learner_goal is present, use it only to frame why this node matters for the learner's goal. "
    "Do not grade against the broad learner goal; grade only against the Target Node mechanism and the Learner Scaffold evidence_goal when present. "
    "Do not treat the threshold as evidence, confidence, or diagnosis. Emphasize it is ok to guess. "
    "If the user produces zero schema or asks for help, provide a tiny hint or nudge to guess with classification/tier null."
)
```

- [ ] **Step 2: Run drill prompt tests**

Run:

```bash
pytest tests/test_drill_session_limits.py::DrillBypassAndDegradedResponseTests::test_cold_attempt_passes_learner_scaffold_into_drill_contract tests/test_drill_session_limits.py::DrillBypassAndDegradedResponseTests::test_cold_attempt_passes_learner_goal_as_relevance_not_grading -v
```

Expected: PASS.

### Task 4: Verify Slice

**Files:**
- No additional files.

- [ ] **Step 1: Run focused backend tests**

Run:

```bash
pytest tests/test_knowledge_map_context.py tests/test_drill_session_limits.py -v
```

Expected: PASS.

- [ ] **Step 2: Run coverage if the implementation touched production Python**

Run:

```bash
./scripts/check-coverage.sh
```

Expected: exit 0 with diff coverage at 100%.

- [ ] **Step 3: Commit the slice**

Run:

```bash
git add models/knowledge_map_context.py tests/test_knowledge_map_context.py app_prompts/drill-system-v1.md ai_service.py tests/test_drill_session_limits.py docs/product/evidence-weighted-map.md docs/superpowers/plans/2026-05-21-learner-goal-thread.md
git commit -m "feat(drill): thread learner goal into cold starts"
```

Commit body should mention: previous behavior dropped `metadata.learner_goal` before drill prompting; this change uses it for relevance only while preserving node-local evidence grading.
