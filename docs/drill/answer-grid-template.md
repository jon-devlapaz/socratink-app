# Drill Answer Grid Template

Purpose: fast manual taste-testing for a freshly extracted knowledge map.

Use this when:

- the library starter maps are no longer representative
- you want to trial a new concept quickly
- you want copy/paste answers covering help requests, weak attempts, strong attempts, and misconceptions
- you want to compare observed backend behavior against the new drill contract

Read these first if needed:

- [graph-invariants.md](graph-invariants.md)
- [happy-path-evals.md](happy-path-evals.md)
- [ux-framework.md](../product/ux-framework.md)

This document is intentionally operational.
It is a testing harness, not a product manifesto.

## What To Fill In First

For the node you are testing, fill in this card from the extracted knowledge map:

```text
CONCEPT: [concept title]
NODE LABEL: [node label]
NODE ID: [node id]
NODE TYPE: [core | backbone | subnode]
MECHANISM IN ONE SENTENCE: [the actual mechanism]
ANCHOR TERM: [one key noun, e.g. sodium channels]
CAUSAL STEP: [one key cause->effect link]
COMMON MISCONCEPTION: [one wrong but plausible model]
MINIMUM SOLID ANSWER: [one clean reconstruction sentence]
```

You do not need perfect prose here.
You need enough material to adapt the answer bank below.

## Expected Contract

When tasting the drill, these are the fields that matter:

- `answer_mode`
- `score_eligible`
- `help_request_reason`
- `classification`
- `routing`
- `response_tier`
- `response_band`

Rules to remember:

- `help_request` should be unscored
- help requests should route `SCAFFOLD`
- help requests should not mutate graph state
- only genuine `attempt` turns count toward probe/force-advance behavior
- mixed turns like "I'm not sure, but..." should count as `attempt` if they make a substantive mechanistic claim

## Fast-Fill Answer Bank

Replace bracketed text with node-specific content from your card.

### 1. Pure Help Request: Explicit Unknown

Expected:

- `answer_mode = help_request`
- `score_eligible = false`
- `help_request_reason = explicit_unknown`
- `classification = null`
- `routing = SCAFFOLD`

Copy/paste:

```text
I don't know.
```

### 2. Pure Help Request: Explain Request

Expected:

- `answer_mode = help_request`
- `score_eligible = false`
- `help_request_reason = explicit_explain_request`
- `classification = null`
- `routing = SCAFFOLD`

Copy/paste:

```text
Can you explain how [ANCHOR TERM] fits into this?
```

### 3. Pure Help Request: Affective Confusion

Expected:

- `answer_mode = help_request`
- `score_eligible = false`
- `help_request_reason = affective_confusion`
- `classification = null`
- `routing = SCAFFOLD`

Copy/paste:

```text
This is confusing. I need a simpler way to think about it.
```

### 4. Mixed Turn: Hesitant But Real Attempt

Expected:

- `answer_mode = attempt`
- `score_eligible = true`
- `classification != null`
- usually `routing = PROBE`

Copy/paste:

```text
I'm not sure, but I think [ANCHOR TERM] is involved because [CAUSAL STEP].
```

### 5. Shallow Attempt: Functional But Vague

Expected:

- `answer_mode = attempt`
- `score_eligible = true`
- usually `classification = shallow`
- usually `routing = PROBE`
- tier usually `1` or `2`

Copy/paste:

```text
[NODE LABEL] is basically about [high-level function], and it helps the system do what it is supposed to do.
```

### 6. Deep Attempt: Partial Causal Structure

Expected:

- `answer_mode = attempt`
- `score_eligible = true`
- usually `classification = deep`
- usually `routing = PROBE`
- tier usually `2` or `3`

Copy/paste:

```text
[ANCHOR TERM] helps drive the process because [partial causal step], but I am probably missing part of how [missing downstream effect] happens.
```

### 7. Misconception Attempt: Confident Wrong Model

Expected:

- `answer_mode = attempt`
- `score_eligible = true`
- `classification = misconception`
- `routing = SCAFFOLD`
- tier should cap low

Copy/paste:

```text
I think [COMMON MISCONCEPTION].
```

### 8. Solid Attempt: Clean Clear

Expected:

- `answer_mode = attempt`
- `score_eligible = true`
- `classification = solid`
- `routing = NEXT`
- tier usually `3`, `4`, or `5`

Copy/paste:

```text
[MINIMUM SOLID ANSWER]
```

### 9. Masterful Solid Attempt: Crisp Full Reconstruction

Expected:

- `answer_mode = attempt`
- `score_eligible = true`
- `classification = solid`
- `routing = NEXT`
- tier should be high if the rubric is behaving well

Copy/paste:

```text
[NODE LABEL] works because [step 1]. That causes [step 2], which leads to [step 3]. So the node matters because [functional consequence].
```

### 10. Force-Advance Sequence

Use this only when you want to verify scored attempts consume the cap while help requests do not.

Recommended sequence:

1. Send one pure help request.
2. Send one shallow attempt.
3. Send one shallow attempt again with different wording.
4. Send one weak deep-ish attempt.

Expected:

- first turn stays `help_request`
- only the three actual attempts count toward forced `NEXT`
- help turn should not silently consume the budget

Weak repeat copy/paste options:

```text
It has something to do with [ANCHOR TERM], but I cannot explain the mechanism clearly.
```

```text
I know [NODE LABEL] matters, but I only remember the general idea, not the exact process.
```

## Observation Grid

Duplicate this block once per node.

```text
CONCEPT:
NODE LABEL:
NODE ID:
DATE:

1. Explicit Unknown
- Answer:
- Observed answer_mode:
- Observed score_eligible:
- Observed help_request_reason:
- Observed classification:
- Observed routing:
- Observed tier:
- Notes:

2. Explain Request
- Answer:
- Observed answer_mode:
- Observed score_eligible:
- Observed help_request_reason:
- Observed classification:
- Observed routing:
- Observed tier:
- Notes:

3. Affective Confusion
- Answer:
- Observed answer_mode:
- Observed score_eligible:
- Observed help_request_reason:
- Observed classification:
- Observed routing:
- Observed tier:
- Notes:

4. Mixed Hesitant Attempt
- Answer:
- Observed answer_mode:
- Observed score_eligible:
- Observed classification:
- Observed routing:
- Observed tier:
- Notes:

5. Shallow Attempt
- Answer:
- Observed answer_mode:
- Observed classification:
- Observed routing:
- Observed tier:
- Notes:

6. Deep Attempt
- Answer:
- Observed answer_mode:
- Observed classification:
- Observed routing:
- Observed tier:
- Notes:

7. Misconception
- Answer:
- Observed answer_mode:
- Observed classification:
- Observed routing:
- Observed tier:
- Notes:

8. Solid
- Answer:
- Observed answer_mode:
- Observed classification:
- Observed routing:
- Observed tier:
- Notes:

9. Masterful Solid
- Answer:
- Observed answer_mode:
- Observed classification:
- Observed routing:
- Observed tier:
- Notes:

10. Force-Advance Sequence
- Help turn counted as scored attempt?:
- Forced NEXT only after scored attempts?:
- Graph mutated only on NEXT?:
- Notes:
```

## Taste Questions

After one node, answer these quickly:

- Did help mode feel supportive rather than graded?
- Did mixed hesitant answers get treated as real attempts?
- Did shallow and deep feel meaningfully different?
- Did the tutor ask one concrete question at a time?
- Did the tier feel like answer quality, not verbosity?
- Did the graph stay truthful?

## Suggested Trial Order For A Fresh Map

Use this order for fastest signal:

1. Core thesis
2. One backbone node
3. One subnode with a compact mechanism
4. One subnode with an easy misconception

If the core thesis rubric is off, stop and recalibrate before spending time on deeper nodes.
