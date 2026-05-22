# Starting Map Flow Artifact

> **Status (2026-05-07, state model refreshed 2026-05-17):** Storyboard only. The threshold flow has now shipped as **C-prime** (Door + Launch Pad -> smallest route). For the operational rules and current contracts, see the binding product spec at [docs/product/spec.md](spec.md), the canonical doctrine in [docs/product/evidence-weighted-map.md](evidence-weighted-map.md), and the drill data-model canon in [docs/superpowers/specs/2026-05-15-drill-data-model-design.md](../superpowers/specs/2026-05-15-drill-data-model-design.md). The archived C-prime material under [docs/archive/2026-05-design-md-refactor/](../archive/2026-05-design-md-refactor/) is historical context only. This artifact is preserved for design context; do not cite it as the implementation contract.

Purpose: a lightweight product design artifact for understanding the metacognitive happy path before implementation.

This is not the binding implementation spec. It is a simple storyboard for the flow where concept entry onboards the learner into their own current model, not into the content.

## Product Frame

The concept page should not be where the learner goes to read.
It should be where their understanding becomes inspectable.

Socratink should ask for the learner's starting map before showing explanatory content. That starting map can shape routing and repair, but it must not create mastery claims.

The starting map is not a diagnostic.
It is an anchor.

Without this anchor, a cold attempt can feel like the product is abruptly asking the learner to fight a concept they may not know yet. With the anchor, the same pedagogical move becomes collaborative: Socratink asks the learner to externalize their current model so the path has something personal and concrete to work with.

Concept entry should therefore start with the learner's current shape of the idea, not with the app explaining the idea.

```text
Bad first move:
  Here is a concept. Explain it.

Better first move:
  Before the room reveals itself, show me your current map.

Then:
  Based on that map, let's test one local mechanism.
```

This makes personalization real. The first graph is shaped by the collision between:

```text
domain structure
  + learner's starting map
  + learner's stated goal
```

The graph is not a progress bar, a content map, or confidence theater. It is an evidence instrument. The reward is not "you completed a lesson." The reward is "the map got more truthful because you proved something."

True game loop:

```text
hypothesis -> attempt -> delta -> repair -> spacing -> proof -> trust
```

## Happy Path

```text
Enter concept
  -> Show starting-map threshold
  -> Capture learner's global current model
  -> Build provisional graph/path
  -> Cold-attempt first node with a local question derived from the starting map
  -> Reveal attempted-node repair artifact
  -> Bridge out of the repair artifact
  -> Interleave into another node when the learner has a clear next target
  -> Later spaced re-drill
  -> Mutate graph truth only on solid reconstruction
```

## Friction Fixes

The flow must avoid three traps:

1. **Generation fatigue**: the threshold and first cold attempt cannot ask the same question twice.
2. **Zero-signal frustration**: learners without useful vocabulary need an analogy-based generation path, not a blind guess.
3. **Interleaving whiplash**: moving from repair directly into another cold attempt needs a short bridge that explains why the learner is leaving the node.

It must also avoid a deeper affective failure: the learner should never feel that Socratink is saying, "You don't know this? Prove it." The threshold reframes the entry contract as, "Show me where you're starting from so the path has something to repair."

## Screen 1: Concept Threshold

State: no graph state mutation.

Goal: capture the learner's global current model before recognition-heavy content appears. This is a broad starting map, not the first node attempt.

```text
+-------------------------------------------------------------+
| Building Large Language Models                              |
|                                                             |
| Show me your starting map.                                  |
|                                                             |
| Before Socratink builds your path, tell me what you already |
| think this concept involves. Rough is useful.               |
|                                                             |
| What do you already think is inside this concept?           |
| Name the parts, guesses, examples, or confusions you have.  |
| +---------------------------------------------------------+ |
| |                                                         | |
| |                                                         | |
| +---------------------------------------------------------+ |
|                                                             |
| Paste notes, syllabus, or a goal Socratink should use.       |
| +---------------------------------------------------------+ |
| | optional context                                         | |
| +---------------------------------------------------------+ |
|                                                             |
| What feels fuzzy?                                           |
| +-------------------------------+  Confidence: Unsure v     |
|                                                             |
| [Build my starting path]                                    |
+-------------------------------------------------------------+
```

Safe copy:

- "Your words shape the path; they do not grade you."
- "Give your best current map. Rough is fine."
- "What do you want to be able to explain when this clicks?"
- "This is global context. The first room will ask one smaller question."
- "Your starting map gives Socratink an anchor. It is not a diagnostic."

Avoid:

- "Diagnostic"
- "Evaluate your current understanding"
- "Beginner / intermediate / advanced"
- "We found your misconceptions"

## Screen 2: Provisional Graph

State: generated graph is a hypothesis. Nodes are still truthful learner states.

Goal: show a proposed route without implying knowledge.

```text
+-------------------------------------------------------------+
| Draft Route                                                 |
|                                                             |
| Here's the path Socratink thinks will expose and repair the |
| important mechanisms. Your starting map shaped the route.   |
| It did not prove mastery.                                  |
|                                                             |
|             (Core Thesis)  suggested first                  |
|                  |                                          |
|       +----------+----------+                               |
|       |                     |                               |
|  (Pretraining)          (Post-training)                     |
|       |                     |                               |
|  (Tokenization)         (Evaluation)                        |
|                                                             |
| Legend: draft route | ready for first attempt | locked      |
|                                                             |
| [Start first attempt]                                      |
+-------------------------------------------------------------+
```

Allowed graph claims:

- "Draft route"
- "Suggested first"
- "Ready for first attempt"
- "Primed for study"
- "Solidified through spaced reconstruction"

Forbidden graph claims:

- "You know this"
- "Mastered" from graph generation
- "Completed" from reading
- "Advanced" from fluent prose

## Screen 3: First Cold Attempt

State: still unscored until a substantive attempt resolves.

Goal: create a local prediction error before study. This prompt must be narrower than the threshold and should reuse the learner's starting map so the system does not feel forgetful.

```text
+-------------------------------------------------------------+
| Core Thesis                                                 |
| Cold attempt                                                |
|                                                             |
| You said LLMs are built from lots of text and training.      |
| Narrow that into one causal guess: what do you think the     |
| training is trying to predict at each step?                  |
|                                                             |
| This is not scored. It gives Socratink something real to    |
| repair.                                                     |
|                                                             |
| +---------------------------------------------------------+ |
| | learner answer                                           | |
| +---------------------------------------------------------+ |
|                                                             |
| [Submit first attempt]                                     |
+-------------------------------------------------------------+
```

Prompt rule:

- Screen 1 asks for the global model: broad parts, goals, fuzzy areas, source context.
- Screen 3 asks for a local mechanism: one causal link inside the first node.
- If possible, Screen 3 quotes or paraphrases the learner's threshold input before asking the local question.

If the learner has too little signal, pivot to an analogical cold attempt:

```text
You may not have the technical words yet. Use this analogy instead.

Imagine the model is learning to finish a sentence one piece at a time.
What do you think it has to notice in the earlier words to make a good next guess?
```

Analogical fallback rules:

- provide a familiar source analogy, not the target mechanism as an answer
- ask the learner to predict a causal relationship inside the analogy
- keep the node `locked` until the learner gives a substantive micro-generation
- do not label the learner as zero-knowledge

Training-evidence rule:

- recordable cold attempt: append learner evidence; derive `primed` or `needs repair`
- non-attempt: no graph mutation; ask for a micro-generation

## Screen 4: Locked Study Silhouette

State: available before attempt, but no mechanism content is visible.

Goal: make the absence of study content intentional.

```text
+-------------------------------------------------------------+
| Core Thesis                                                 |
| Repair layer locked                                         |
|                                                             |
| The repair layer unlocks after you make a first attempt.    |
|                                                             |
| Why this node matters: it anchors the rest of the path.      |
|                                                             |
| [Start first attempt]                                      |
+-------------------------------------------------------------+
```

Allowed:

- node title
- purpose
- locked state
- first-attempt CTA

Forbidden:

- full explanation
- definitions list
- solved causal diagram
- examples that reveal the mechanism

## Screen 5: Study Repair Artifact

State: node is `primed`; study content is scoped to the attempted node only.

Goal: turn the learner's attempt into targeted corrective feedback.

```text
+-------------------------------------------------------------+
| Core Thesis                                                 |
| Repair artifact                                             |
|                                                             |
| Your guess                                                  |
| "LLMs are built by collecting lots of text and training a    |
| giant neural network to answer questions."                  |
|                                                             |
| The hinge                                                   |
| You emphasized scale and answers. The mechanism turns on    |
| next-token prediction first, then post-training steers       |
| behavior.                                                   |
|                                                             |
| Causal spine                                                |
| [raw text] -> [tokens] -> [next-token prediction]            |
|          -> [capability] -> [post-training alignment]        |
|                                                             |
| One clarifying diagram                                      |
| raw text --tokenize--> training examples --predict--> model |
|    capability --align--> useful assistant behavior          |
|                                                             |
| Try this next                                               |
| Leave this node alone long enough for the easy feeling to   |
| fade. First, choose the next room Socratink should test.    |
|                                                             |
| [Choose next room]                                          |
+-------------------------------------------------------------+
```

Study artifact rules:

- preserve the learner's words
- show one hinge correction
- show one compact causal spine
- show one clarifying diagram
- show 1-2 connection cues only after the local repair
- do not offer immediate mastery unless spacing is truly satisfied

## Screen 6: Interleaving Bridge

State: node remains `primed`; re-drill is not yet offered.

Goal: lower drop-off risk by explaining why the learner is leaving the repaired node and letting them choose from a small next set.

```text
+-------------------------------------------------------------+
| Let this one cool                                           |
|                                                             |
| The repair is fresh, so re-drilling Core Thesis right now   |
| would mostly test short-term echo.                          |
|                                                             |
| Pick one nearby room to create useful distance:             |
|                                                             |
| [Pretraining]                                               |
| Tests how raw text becomes model capability.                |
|                                                             |
| [Tokenization]                                              |
| Tests the bridge from words to training units.              |
|                                                             |
| [Post-training]                                             |
| Tests how behavior gets shaped after capability exists.     |
|                                                             |
| [Take a short break instead]                                |
+-------------------------------------------------------------+
```

Bridge rules:

- offer 2-3 nearby rooms, not the whole graph
- each option gets a one-line purpose, not a mechanism reveal
- allow a short break as a non-punitive spacing path
- do not frame interleaving as a reward or completion state
- do not offer same-node mastery unless spacing is satisfied

## Screen 7: Accumulating Repair History

State: history grows only from attempts, feedback, repair reps, or re-drills.

Goal: make study become a personal metacognitive field journal.

```text
+-------------------------------------------------------------+
| Core Thesis                                                 |
| Repair history                                              |
|                                                             |
| First attempt                                               |
| - You emphasized scale and answers.                         |
| - Hinge repaired: pretraining creates capability;            |
|   post-training steers behavior.                            |
|                                                             |
| Recurring gap                                               |
| - Tokenization keeps appearing as a missing bridge.          |
|                                                             |
| Your summary                                                |
| - "Pretraining teaches the model statistical structure;      |
|    alignment changes how it behaves for people."            |
|                                                             |
| Next valid proof                                            |
| - Spaced re-drill after interleaving.                        |
+-------------------------------------------------------------+
```

History may include:

- repaired misconceptions
- recurring gaps
- alternate explanations
- learner-authored summaries
- causal bridges to attempted nearby nodes
- re-drill contrast after later retrieval

History must not include:

- passive reading as evidence
- unattempted-node answers
- mastery claims without spaced reconstruction

## Truth Table

| Moment | What Learner Sees | What System May Infer | Allowed State Change |
| --- | --- | --- | --- |
| Threshold submitted | starting map captured | routing signal, source dependence, causal depth | none |
| Provisional graph generated | draft route | first-node priority, prompt emphasis | none |
| Local cold attempt submitted | learner-facing unscored node attempt | private classification and gaps | training evidence appended; derives `primed` or `needs repair` |
| Study revealed | repair artifact | study timestamp, next interleave target | no solidification |
| Interleaving bridge shown | small next-choice set | route preference | none |
| Repair rep completed | practice history | self-rating, bridge quality | none |
| Spaced re-drill strong | proof through reconstruction | strong classification after spacing | derives `solidified` |
| Spaced re-drill non-solid | needs repair | gap metadata | derives `needs repair` when warranted |

## MVP Cut

Build first:

- Concept Threshold before any study-like page.
- Pasted text and global learner-map inputs only.
- Internal routing signals, never learner-facing schema labels.
- Provisional graph copy.
- First cold attempt is local and derived from the threshold input.
- Analogical cold-attempt fallback for low-signal learners.
- Locked study silhouette before attempt.
- Attempt-scoped repair artifact after cold attempt.
- Interleaving bridge with 2-3 next-room choices before another cold attempt.
- Training evidence writes to the browser-local training store; displayed state derives from that record, with `solidified` still gated by the shipped 18-hour spacing interval.

Defer:

- learner-visible schema profiles
- long-term curriculum claims
- cross-concept mastery summaries
- rich notebook features
- URL ingestion unless SSRF protections and manual fallback are already in place

## Design Principle

The graph proposes where to look.
The cold attempt creates something to repair.
The study view makes the repair inspectable.
The spaced re-drill is the only proof.
