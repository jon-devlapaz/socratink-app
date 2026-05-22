---
title: Nanny Feynman Prompt Integration
date: 2026-05-18
status: proposal (not runtime canon until a versioned prompt change ships)
scope: external Feynman-technique prompt patterns for Socratink drill and repair prompts
source_repo: https://github.com/Jonohobs/nanny-feynman
---

# Nanny Feynman Prompt Integration

This spec captures how to fold the useful parts of
`Jonohobs/nanny-feynman` into Socratink without importing its persona, quiz
posture, or licensing risk into the product runtime.

The source repo is a compact prompt package: `SKILL.md`, `doris.md`,
`questions.md`, `ORIGIN.md`, and `LICENSE`. Its durable value is not the
Croydon-grandmother character. Its durable value is a tight Feynman-technique
loop: learner explains, agent detects jargon or bluffing, agent asks one
smaller question, learner repairs the mechanism in plain language.

## What this document is for

Socratink already has the stronger production doctrine:

- Generation Before Recognition.
- Cold attempt before explanatory content.
- Targeted study only after learner reconstruction.
- Repair Reps as graph-truth-neutral practice.
- `solidified` only from spaced reconstruction evidence.
- The graph shows evidence Socratink has recorded, not what the learner knows.

Nanny Feynman should therefore be treated as a **pedagogical pattern library**,
not a product persona and not a prompt file to paste into `app_prompts/`.

This spec gives future prompt work a sharp boundary: extract the Feynman
pressure, reject the character layer, preserve Socratink's structured runtime
contracts.

## Current Socratink status

Prompt assets live under `app_prompts/` and are loaded by `ai_service.py`.
Current runtime prompts:

- `extract-system-v1.txt` creates a `ProvisionalMap`.
- `generate-smallest-route-system-v1.txt` creates the source-less smallest
  route.
- `drill-system-v1.md` drives the structured Socratic drill.
- `repair-reps-system-v1.md` creates graph-neutral causal micro-practice.

The drill backend appends the target node answer key at runtime. When the
target subnode carries `learner_scaffold`, it also appends scaffold task fields
and `evidence_goal`; when `metadata.learner_goal` is present, cold-attempt
instructions may use it for relevance only. The backend expects a strict
`DrillEvaluation` object with routing, classification, gap, tier, and mode
fields. Any prompt integration must preserve that parser contract and must not
turn learner goals or scaffold fields into graph-truth evidence.

## Decision

Do **not** import Doris as a learner-facing character.

Reasons:

- Socratink's product voice is calm, precise, Socratic, and non-character.
- The repo forbids generic "AI tutor" and quiz/test posture in learner-facing
  surfaces.
- Character catchphrases would compete with graph-truth language and can create
  a praise/shame register that the current drill prompt explicitly avoids.
- The source repo is GPL-3.0. Reusing ideas is fine; copying prompt text into a
  production prompt requires explicit licensing review or dual-license
  permission.

Adopt the underlying technique:

- pressure jargon into mechanism language;
- ask one smaller causal question at a time;
- reward honest uncertainty by scaffolding, not scoring;
- use analogy as a temporary bridge, not as answer-key leakage;
- require the learner to reconstruct in their own words.

## Pattern Mapping

| Nanny Feynman pattern | Socratink adaptation | Runtime target |
| --- | --- | --- |
| Explain it plainly | Require concrete mechanism language, not term labels | `drill-system-v2.md` |
| Interrupt jargon | Ask what the term does in this mechanism | `drill-system-v2.md` |
| One probing question | Keep the existing one-question rule and make gap targeting stricter | `drill-system-v2.md` |
| Warm but exact correction | Curiosity-framed, non-grading feedback | `drill-system-v2.md` |
| "I don't know" is acceptable | Route to `help_request` / `SCAFFOLD`, no classification or tier | `drill-system-v2.md` |
| Everyday analogy hints | Use only after collapse/help request and follow with a generation prompt | `drill-system-v2.md`, maybe `repair-reps-system-v2.md` |
| Question bank | Use as internal eval inspiration, not learner-facing canned content | prompt eval fixtures |
| Doris persona and catchphrases | Reject | out of scope |

## Prompt Contract

Future prompt work should create a versioned drill prompt rather than silently
editing v1:

1. Create `app_prompts/drill-system-v2.md`.
2. Update `DRILL_PROMPT_PATH` and `DRILL_PROMPT_VERSION` in `ai_service.py`.
3. Preserve the `DrillEvaluation` schema exactly unless the implementation is
   explicitly a parser/schema migration.
4. Add prompt contract tests that assert the Feynman rules are present and that
   forbidden persona/quiz wording is absent.
5. Run the normal prompt/unit checks before any wider browser or coverage gate.

Versioning matters because prompt behavior is part of product truth. A prompt
that changes grading, routing, or answer-key exposure must be reviewable as a
new version, not a silent mutation of v1.

## Required Drill Prompt Additions

These are the only Nanny-derived behaviors that should enter the drill prompt.

### 1. Plain-language pressure

When the learner uses a technical term without explaining its role, the agent
must not accept the term as evidence. It should ask what the term does in this
specific mechanism.

Good shape:

```text
You named X. In this mechanism, what does X change, block, enable, or produce?
```

Bad shape:

```text
Define X.
```

The difference matters: Socratink grades causal reconstruction, not vocabulary
recognition.

### 2. Single missing bridge

Every probe should expose one missing causal bridge. If the learner has three
gaps, choose the smallest bridge that unlocks the next reconstruction attempt.
Do not stack questions.

Good shape:

```text
You have the input and the result. What is the step that turns the input into
that result?
```

Bad shape:

```text
What causes it, why does it matter, and how does it connect to the next node?
```

### 3. Honest uncertainty is graph-neutral

If the learner says they do not know and gives no substantive mechanism claim,
the response remains `answer_mode = "help_request"`, `score_eligible = false`,
`classification = null`, `routing = "SCAFFOLD"`, and tier fields remain null.

The agent may give a tiny foothold, but must end by asking the learner to
generate the next small link.

### 4. Analogy as scaffold only

Analogies are allowed only when they reduce cognitive load after collapse or
explicit help request. The analogy must not reveal the target mechanism in full.
It should map to a smaller question the learner can answer.

Good shape:

```text
Think of it like a thermostat comparing two numbers. What has to be compared
before the system can decide what to do next?
```

Bad shape:

```text
It works like a thermostat: it compares current temperature to a set point and
turns heat on when there is a gap.
```

### 5. No praise-as-proof

Do not use warmth, approval, or character voice as evidence. If the learner
reconstructs the mechanism, the structured fields carry the outcome. The text
can be brief and clear, but graph truth comes from the parsed result and
training record.

## Repair Reps Adaptation

Repair Reps may borrow the Feynman pressure only in rep wording:

- ask for a typed causal bridge;
- avoid term-definition cards;
- avoid multiple choice;
- compare the learner's answer against structure, not vocabulary density.

Repair Reps must remain graph-truth-neutral. No Nanny-derived language may imply
that practice reps produce mastery, completion, unlocks, or `solidified`.

## Explicit Non-Goals

Do not:

- add Doris, Gerald, Croydon, tea, bridge club, or catchphrases to production
  learner-facing prompts;
- rename Socratink features around Nanny Feynman vocabulary;
- expose a generic "quiz me" mode;
- use the external question bank as live learner content;
- add learner-visible diagnostic labels such as beginner, advanced, or
  misconception detected;
- relax answer-key secrecy to make analogies easier;
- mutate graph truth from scaffolding, study, or Repair Reps.

## Evaluation Fixtures

Any implementation should add focused prompt contract tests before live provider
testing. Suggested fixture set:

1. **Jargon-only attempt**
   - Learner says: "It uses embeddings and cosine similarity."
   - Expected: not solid solely from terms; probe asks what the terms do in the
     mechanism.

2. **Honest unknown**
   - Learner says: "I don't know."
   - Expected: `help_request`, no classification, `SCAFFOLD`, tiny foothold.

3. **Partial causal bridge**
   - Learner gives input and output but omits transition.
   - Expected: `deep` or `shallow`, `PROBE`, one missing-link question.

4. **Wrong mental model**
   - Learner states a mechanism that contradicts the answer key.
   - Expected: `misconception`, `SCAFFOLD`, gentle correction without shame.

5. **Full reconstruction**
   - Learner states initiating condition, causal transition, and resulting
     state.
   - Expected: `solid`, `NEXT`; no extra lecture.

6. **Persona contamination guard**
   - Static test over prompt text.
   - Expected: no Doris/persona/catchphrase terms in production prompts.

## Implementation Sequence

1. Draft `app_prompts/drill-system-v2.md` from v1 with only the additions in
   this spec.
2. Add static tests in `tests/test_app_prompts.py` for required and forbidden
   prompt phrases.
3. Add or update drill normalization tests only if v2 exposes a real runtime
   mismatch; do not change schema for prompt-only work.
4. Switch `DRILL_PROMPT_PATH` and `DRILL_PROMPT_VERSION`.
5. Run targeted tests:
   - `pytest tests/test_app_prompts.py -v`
   - `pytest tests/test_drill_session_limits.py -v`
   - any new prompt fixture tests
6. For production prompt behavior, run at least one controlled live Gemini
   fixture before treating the prompt as quality-improved.
7. If JS or backend executable lines change, run `./scripts/check-coverage.sh`
   before completion.

## Acceptance Criteria

The integration is accepted only when all are true:

- The production prompt remains Socratink-voiced, not Doris-voiced.
- The structured output contract is unchanged and tests pass.
- Jargon-only attempts are pressured into mechanism language.
- Help requests remain unscored and graph-neutral.
- Analogies scaffold without revealing the answer key.
- Repair Reps remain graph-truth-neutral.
- No GPL prompt text is copied into production assets without explicit license
  clearance.

## Source Summary

External source inspected:

- `https://github.com/Jonohobs/nanny-feynman`
- `SKILL.md`: persona plus Feynman flow.
- `doris.md`: expanded character sheet and teaching posture.
- `questions.md`: 105-question bank with hint style.
- `ORIGIN.md`: origin narrative and first-session transcript.
- `LICENSE`: GPL-3.0.

Use those files for inspiration and comparison only. The Socratink runtime
contract remains governed by `app_prompts/`, `docs/product/spec.md`,
`docs/product/evidence-weighted-map.md`, and the drill data-model spec.
