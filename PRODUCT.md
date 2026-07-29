# Socratink product truth

Authority: `socratink-north-star`, decided by the founder and effective 28 July 2026. The canonical doctrine is [`docs/product/north-star.md`](docs/product/north-star.md). This file is the implementation contract derived from that doctrine. If they conflict, the north star wins.

## Who it is for

Working professionals learning technical material for their jobs.

The first product accepts one narrow input: technical text the learner pastes into Socratink.

## The job

Help me discover what I can explain without the source, where my explanation breaks, and what I need to reconstruct later so I can use the material at work.

## The promise

**Close the source. Explain it. See what survives.**

Socratink preserves the learner's exact explanations, locates the important gap against the source, supports a learner-authored repair, and later asks for another unaided explanation so the learner can see what changed.

## The product loop

1. Paste one piece of technical material.
2. Name one explanation target.
3. Hide the source and explain it from memory.
4. Compare the attempt with the source and locate the consequential gap.
5. Write a repair in the learner's own words.
6. Leave, then return after real elapsed time.
7. Reconstruct again without the source.
8. Show the difference without claiming more than the attempts prove.

SEDA may orchestrate this loop internally. It is not the learner-facing product or navigation model.

## The evidence boundary

- The source, goal, model feedback, and repair guidance are context.
- Learner-generated attempts are evidence.
- Immediate fluency, completion, confidence, and AI agreement are not mastery.
- Only eligible source-hidden reconstruction across time can strengthen the product's claim about what the learner can currently explain.
- A reconstruction must be checked against the active target. Plausible prose is not correctness evidence.
- The graph records this evidence. It is not the leading promise and must never imply progress the learner did not demonstrate.

## Product requirements

| ID | Obligation | Acceptance signal |
|---|---|---|
| PT-1 | Socratink must accept pasted technical text and one explanation target. | A working professional can begin without creating a course, graph, account, or study plan. |
| PT-2 | Socratink must hide answer-bearing source and guidance during each reconstruction. | Neither the first nor return explanation surface reveals the source, prior guidance, or prior attempt. |
| PT-3 | Socratink must preserve each submitted explanation exactly. | Reloading the session returns the original text and submission time unchanged. |
| PT-4 | Socratink must check the explanation against both the active target and source. | Gap feedback identifies one consequential target-relevant break grounded in the source. |
| PT-5 | Socratink must require the learner to author the repair. | Model output may support the repair but cannot submit or record it for the learner. |
| PT-6 | Socratink must keep guidance, repair completion, confidence, and AI agreement from strengthening learner evidence. | None of those events changes the evidence claim or displays mastery. |
| PT-7 | Socratink must require real elapsed time before the return reconstruction becomes eligible. | The learner cannot complete the return reconstruction immediately after repair. |
| PT-8 | Socratink must restrict comparison claims to the exact recorded attempts. | The comparison describes observable differences and uncertainty without inferring mastery, retention, or ability. |
| PT-9 | Socratink must derive every visible graph claim from learner reconstruction evidence. | Removing the learner attempts removes the corresponding graph claim; context and model output alone cannot create it. |

These requirements derive from the founder-approved north star. Each acceptance signal is the minimum behavioral proof for implementation.

## First product slice

The first slice must support:

- one pasted technical source
- one explanation target
- one source-hidden first explanation
- one source-grounded consequential gap
- one learner-authored repair
- one genuinely delayed source-hidden return explanation
- one honest comparison of the exact attempts
- same-device session resume

The first slice will not include:

- graph-first storytelling, dashboards, Desk, or Library
- visible SEDA phases or agent choreography
- generic chat, generated summaries, or generated flashcards as the center of value
- broad all-learner positioning
- accounts, synchronization, collaboration, payments, or teams
- URL, document, audio, or video ingestion
- themes, sound, voice, animation systems, gamification, scores, or mastery labels

Existing code does not create a product requirement.

## Category and decision filter

Socratink is reconstruction practice. It is not a generic AI tutor, summarizer, flashcard generator, spaced-repetition clone, or knowledge-graph product.

Build a change only when it materially improves at least one of these:

- reaching the first unaided explanation
- grounding a precise, useful gap
- enabling learner-authored repair without answer substitution
- getting the learner back for a genuinely delayed reconstruction
- making longitudinal evidence more durable, truthful, or understandable

## Validation boundary

The north-star behavior is a working professional returning after real elapsed time and reconstructing a technical idea more completely without the source, while Socratink preserves both attempts and reports the change honestly.

This is direction, not proof of demand or learning efficacy. Expansion requires working professionals to use the loop with real job material, return, and show willingness to keep using or pay for it. Shipping, tests, and repository activity are not product validation.

## Deferred design

Product truth does not choose the framework, storage engine, model provider, visual system, deployment platform, exact return interval, or graph presentation. Use the smallest design that satisfies the requirements and replace it only when observed use reaches its limit.
