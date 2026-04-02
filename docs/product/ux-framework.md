# Product UX Framework

Purpose: enduring product philosophy for how LearnOps-tamagachi should feel and what kinds of UX decisions are acceptable.

Use this document when deciding:

- what the product should reward
- what the graph should mean
- how drill should feel
- whether a proposed UX pattern is aligned or misleading

Do not use this document as the source of truth for:

- current routing semantics
- persistence fields
- unlock implementation details

For current implementation behavior, read:

- [progressive-disclosure.md](progressive-disclosure.md)
- [graph-invariants.md](../drill/graph-invariants.md)

## Product Thesis

The enemy is the illusion of competence.

Most learning tools reward exposure, recognition, and streak maintenance.
LearnOps-tamagachi should reward reconstruction.

The product is trying to make a hard cognitive act feel magnetic:

- select one idea
- reconstruct it from memory
- get a truthful result
- see the board change because of what was actually understood

The graph is not a content browser.
It is not a completion checklist.
It is a spatial record of verified understanding.

## Core Experience Goal

Make learning feel rewarding without lying to the learner.

That means:

- the learner should feel momentum
- the learner should feel curiosity
- the learner should feel a strong payoff when understanding is genuine
- the system should never fake mastery to preserve motivation

Reward is allowed.
False reward is not.

## Primary Metaphor

The graph behaves like a dungeon map.

- each graph node is a room
- the active drill target is the room's boss
- the learner must beat that boss before the room is truly cleared
- a room can be entered without being cleared
- new rooms should open only when prerequisite understanding is real

This metaphor is useful because it keeps effort, difficulty, and progression tied to truth.

If a feature makes it feel like the learner fought one room while the system updated another, the feature is wrong.

## Secondary Emotional Analogy

Tetris is a useful analogy for the rhythm of drilling.

Not visually.
Mechanically and emotionally.

The right feeling is:

- one problem at a time
- visible structure, hidden solution
- meaningful consequence
- satisfaction when a move is genuinely clean

Applied here:

- the graph is the board
- the active node is the current problem
- drill is the cognitive move
- `solidified` is a clean resolution
- `drilled` is unresolved stack pressure, not failure

## Non-Negotiable UX Principles

### 1. Generation Before Recognition

The learner must generate the answer before the interface lets them recognize it.

That means:

- the active mechanism should not remain visible during drill
- the graph may identify the active room
- the graph must not become a cheat sheet

### 2. One Active Cognitive Target

At any moment, the learner should know:

- what they are drilling
- where it sits in the map
- whether it is unresolved or cleared

No silent target switching.
No mixed-state drill sessions.

### 3. The Graph Must Tell The Truth

The graph represents understanding, not activity.

That means:

- attempted is not mastered
- session advance is not mastery
- time spent is not mastery
- only verified understanding should open downstream territory

### 4. Reward Must Be Earned

Good reward design:

- selective visual change
- clear acknowledgment of what changed
- stronger payoff when understanding is genuinely solid

Bad reward design:

- generic praise
- fake unlocks
- inflated positive feedback for weak answers

### 5. In-Progress Must Not Feel Punitive

Unresolved nodes should feel return-worthy, not shameful.

Preferred framing:

- unfinished
- worth revisiting
- the next gain is here

Avoid:

- failure identity language
- punitive color systems
- over-graded emotional feedback

## What The Graph Is For

The graph exists for orientation and truthful progression.

It should answer:

- where am I
- what is available
- what changed

It should not answer:

- what exact mechanism should I parrot back right now

## What This Means In Practice

When evaluating a new UX idea, ask:

1. Does this make the learner's current target clearer or blurrier?
2. Does this make the graph more truthful or more decorative?
3. Does this reward real reconstruction or mere participation?
4. Does this preserve curiosity without revealing the answer?

If the answer is wrong on those four questions, the idea is misaligned even if it feels polished.
