# Drill Answer Grid: Action Potential

Purpose: ready-to-use taste-testing grid for the `Action Potential Generation and Propagation` concept.

Use this when:

- you want to trial the new extraction/drill contract immediately
- you want copy/paste answers without rewriting them each time
- you want to calibrate help mode, attempt mode, and tier behavior on a mechanism-rich concept

Read first if needed:

- [answer-grid-template.md](answer-grid-template.md)
- [happy-path-evals.md](happy-path-evals.md)

This file assumes a fresh extraction of the action-potential source used in this session.
If your latest extraction uses slightly different node labels, keep the answer bank and update the label/id lines only.

## Node Card

```text
CONCEPT: Action Potential Generation and Propagation
NODE LABEL: Core Thesis
NODE ID: core-thesis
NODE TYPE: core
MECHANISM IN ONE SENTENCE: An action potential is a threshold-triggered, self-propagating electrical signal caused by ordered ion-channel dynamics that let a neuron transmit information down the axon.
ANCHOR TERM: voltage-gated sodium channels
CAUSAL STEP: once threshold is reached, sodium channels open and depolarization spreads to the next segment of membrane
COMMON MISCONCEPTION: the action potential is just electricity passively flowing down the axon like current through a wire
MINIMUM SOLID ANSWER: An action potential is a rapid electrical signal neurons use to transmit information. It starts when inputs depolarize the membrane to threshold, opening voltage-gated sodium channels so sodium rushes in and causes rapid depolarization. Then sodium channels inactivate, potassium channels open, and the membrane repolarizes, while refractory periods help the signal keep moving forward down the axon.
```

## Copy/Paste Answer Bank

### 1. Pure Help Request: Explicit Unknown

Expected:

- `answer_mode = help_request`
- `score_eligible = false`
- `help_request_reason = explicit_unknown`
- `classification = null`
- `routing = SCAFFOLD`

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

```text
Can you explain how voltage-gated sodium channels fit into this?
```

### 3. Pure Help Request: Affective Confusion

Expected:

- `answer_mode = help_request`
- `score_eligible = false`
- `help_request_reason = affective_confusion`
- `classification = null`
- `routing = SCAFFOLD`

```text
This is confusing. I need a simpler way to think about it.
```

### 4. Mixed Turn: Hesitant But Real Attempt

Expected:

- `answer_mode = attempt`
- `score_eligible = true`
- `classification != null`
- usually `routing = PROBE`

```text
I'm not sure, but I think voltage-gated sodium channels are involved because once threshold is reached they open and start the signal.
```

### 5. Shallow Attempt: Functional But Vague

Expected:

- `answer_mode = attempt`
- `score_eligible = true`
- usually `classification = shallow`
- usually `routing = PROBE`
- tier usually `1` or `2`

```text
An action potential is basically the signal a neuron uses to send information down the axon.
```

### 6. Deep Attempt: Partial Causal Structure

Expected:

- `answer_mode = attempt`
- `score_eligible = true`
- usually `classification = deep`
- usually `routing = PROBE`
- tier usually `2` or `3`

```text
An action potential happens when the neuron gets to threshold and sodium channels open, which depolarizes the membrane and sends the signal forward, but I am probably missing how it resets and why it only moves one way.
```

### 7. Misconception Attempt: Confident Wrong Model

Expected:

- `answer_mode = attempt`
- `score_eligible = true`
- `classification = misconception`
- `routing = SCAFFOLD`
- tier should cap low

```text
I think an action potential is just electricity passively flowing down the axon like current through a wire, and the channels are mostly there to let it pass through.
```

### 8. Solid Attempt: Clean Clear

Expected:

- `answer_mode = attempt`
- `score_eligible = true`
- `classification = solid`
- `routing = NEXT`
- tier usually `3`, `4`, or `5`

```text
An action potential is a rapid electrical signal neurons use to transmit information. It starts when inputs depolarize the membrane to threshold, opening voltage-gated sodium channels so sodium rushes in and causes rapid depolarization. Then sodium channels inactivate, potassium channels open, and the membrane repolarizes, while refractory periods help the signal keep moving forward down the axon.
```

### 9. Masterful Solid Attempt: Crisp Full Reconstruction

Expected:

- `answer_mode = attempt`
- `score_eligible = true`
- `classification = solid`
- `routing = NEXT`
- tier should be high if the rubric is behaving well

```text
An action potential works because depolarizing input pushes the membrane to threshold, which opens voltage-gated sodium channels and causes a rapid sodium influx. That creates the rising phase and depolarizes adjacent membrane, so the signal regenerates instead of fading. Then sodium channels inactivate and slower potassium channels repolarize and briefly hyperpolarize the membrane, while refractory periods stop the signal from moving backward and keep propagation one-way along the axon.
```

### 10. Force-Advance Sequence

Use this to confirm help turns do not consume the scored cap.

1. Send the explicit-unknown help request above.
2. Send this shallow attempt:

```text
It is the signal neurons use to communicate, but I do not really remember how it gets generated.
```

3. Send this weak repeat:

```text
I know it moves along the axon, but I only remember the general idea and not the actual mechanism.
```

4. Send this weak deep-ish attempt:

```text
I think sodium channels open first and that starts the signal, but I cannot explain the full sequence after that.
```

Expected:

- the first turn stays `help_request`
- only the last three count as scored attempts
- forced `NEXT` should only happen after the scored attempts, not because of the help turn

## Observation Grid

```text
CONCEPT: Action Potential Generation and Propagation
NODE LABEL: Core Thesis
NODE ID: core-thesis
DATE:

1. Explicit Unknown
- Observed answer_mode:
- Observed score_eligible:
- Observed help_request_reason:
- Observed classification:
- Observed routing:
- Observed tier:
- Notes:

2. Explain Request
- Observed answer_mode:
- Observed score_eligible:
- Observed help_request_reason:
- Observed classification:
- Observed routing:
- Observed tier:
- Notes:

3. Affective Confusion
- Observed answer_mode:
- Observed score_eligible:
- Observed help_request_reason:
- Observed classification:
- Observed routing:
- Observed tier:
- Notes:

4. Mixed Hesitant Attempt
- Observed answer_mode:
- Observed score_eligible:
- Observed classification:
- Observed routing:
- Observed tier:
- Notes:

5. Shallow Attempt
- Observed answer_mode:
- Observed classification:
- Observed routing:
- Observed tier:
- Notes:

6. Deep Attempt
- Observed answer_mode:
- Observed classification:
- Observed routing:
- Observed tier:
- Notes:

7. Misconception
- Observed answer_mode:
- Observed classification:
- Observed routing:
- Observed tier:
- Notes:

8. Solid
- Observed answer_mode:
- Observed classification:
- Observed routing:
- Observed tier:
- Notes:

9. Masterful Solid
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

- Did the scaffold feel calm and useful on help requests?
- Did the mixed hesitant attempt get scored instead of slipping into help mode?
- Did `shallow` vs `deep` feel meaningfully different?
- Did the tutor ask one concrete missing-link question at a time?
- Did the solid/masterful split feel like clarity of mechanism rather than verbosity?
