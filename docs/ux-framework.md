# Product UX Framework: socraTink

## Purpose

This document defines the current UX philosophy for socraTink.

Use it when changing:

- `public/js/app.js`
- `public/js/graph-view.js`
- `ai_service.py`
- drill prompts, routing logic, graph state logic, onboarding, or reward design

This is not a visual style guide.

It is the interaction framework for making learning feel demanding, truthful, and rewarding enough that users want to come back.

## Product Thesis

The enemy is the illusion of competence.

Most learning tools reward exposure, recognition, and streak maintenance.
socraTink should reward reconstruction.

The product is trying to make a hard cognitive act feel magnetic:

- select one idea
- reconstruct it from memory
- get a truthful result
- feel the board change because of what you actually understood

The graph is not a content browser.
It is not a completion checklist.
It is a spatial record of verified understanding.

## Core Experience Goal

Make learning feel addictive without lying to the learner.

That means:

- the learner should feel momentum
- the learner should feel curiosity
- the learner should feel reward when understanding is genuine
- the system should never fake mastery for the sake of motivation

The dopamine must be attached to epistemic truth, not empty progress.

## Primary Metaphor: Dungeon Rooms

The main product metaphor is a dungeon map.

- each graph node is a room
- the active drill target is the room's boss
- the learner must beat that boss before the room is cleared
- a room can be entered without being cleared
- new rooms unlock only when prerequisite rooms are truly cleared

This metaphor governs the drill-graph relationship.

If a proposed feature makes the learner feel like they are fighting one room while the map updates another, it is wrong.

Current progression law inside that metaphor:

- `core-thesis` is the first room
- backbone principles are the second layer
- each backbone unlocks its own territory independently
- clusters are structural gates, not the main boss fights
- subnodes are the primary drill rooms inside each opened branch
- downstream territory opens only when dependencies are truly cleared

## Secondary Analogy: Tetris

Tetris is a useful emotional and mechanical analogy for how drilling should feel.

Not because the product should look like Tetris.
Because the rhythm is right.

Useful parallels:

- one problem at a time
- visible structure, hidden solution
- constrained but meaningful action
- mistakes change the board without ending the run
- strong reward when a move is especially clean

Applied to socraTink:

- the graph is the board
- the active node is the current problem
- drill is the placement decision
- `solidified` is the clear, satisfying resolution
- `drilled` is unresolved stack pressure, not failure

The learner should feel:

"I know what I am working on right now, I know what changed, and I can see the board opening because of what I really understood."

## Non-Negotiable UX Principles

### 1. Generation Before Recognition

The learner must generate the answer before the interface lets them recognize it.

That means during drill:

- answer-rich summaries should disappear
- mechanism text should not remain visible
- the graph can identify the active room
- the graph must not become a cheat sheet

This is the Generation Effect enforced at the UI layer.

### 2. One Active Room At A Time

The product should always make one active cognitive target obvious.

At any moment, the learner should know:

- what node they are drilling
- where that node sits in the map
- whether the node is unresolved or solidified

No silent target switching.
No mixed-state drill sessions.

### 3. The Graph Must Tell The Truth

The graph represents understanding, not activity.

That means:

- attempted is not mastered
- session advance is not mastery
- time spent is not mastery
- only verified understanding should unlock downstream territory

If the graph advances when understanding has not been demonstrated, the graph is lying.

Truthful fog-of-war is part of this.

Territory should be hidden because the learner has not earned access to it yet, not because the interface wants to look mysterious.

### 4. Reward Must Be Earned

The product should feel rewarding, but the reward has to be specifically tied to cognitive success.

Good reward design:

- crisp visual state change
- clear language about what was achieved
- stronger feedback when understanding is especially clean

Bad reward design:

- generic praise
- grade-school validation
- fake unlocks
- constant hype for mediocre answers

The learner should trust the reward because it is selective.

### 5. In-Progress Must Not Feel Punitive

Nodes that are not yet solid should feel return-worthy, not shameful.

The system must avoid turning knowledge gaps into identity judgments.

Preferred emotional framing:

- "come back here"
- "this is unfinished"
- "this is where the next gain lives"

Avoid:

- failure language
- red-error metaphors
- over-grading the learner

## The UX Loop

The current ideal loop is:

### Phase 1. Ingest

- learner brings their own content
- extraction produces a knowledge map
- the map becomes the source of truth for later drill and graph state

### Phase 2. Orient

- learner enters graph or study view
- they can inspect the structure and choose a reachable room
- the interface should make the next viable action obvious

At first run, that next viable action should be unmistakable:

- start with `core-thesis`
- then move into unlocked backbone branches
- then drill subnodes inside revealed clusters

### Phase 3. Drill

- learner enters a drill on one node only
- rich explanation disappears
- the interface shifts into constrained focus
- the AI asks for reconstruction, not recognition

### Phase 4. Resolve

- the backend evaluates the learner's response
- the node is marked truthfully
- the graph updates from persisted state

### Phase 5. Re-Engage

- the learner sees what changed
- the board remains legible
- the next action is obvious:
  - continue exploring
  - revisit later
  - drill again next session

## Graph View Strategy

The graph exists for orientation, not explanation.

It should answer:

- where am I?
- what is available?
- what changed?

It should not answer:

- what is the mechanism I am supposed to reconstruct right now?

## Progression Architecture

The graph should make progression feel earned, legible, and spatially coherent.

### `core-thesis` Is The Starting Room

`core-thesis` is the absolute first drill target.

Until it is `solidified`:

- backbone principles remain locked
- the right panel should clearly communicate "start here"
- the graph should not imply that branching is already available

### Backbone Principles Are The Second Layer

Backbone principles are the governing causal claims for each branch of the map.

They establish why a branch matters before the learner drills the lower-level mechanisms inside it.

Important rule:

- each backbone independently unlocks its own `dependent_clusters`

This means:

- `b1` becoming solid can open `b1`'s territory
- unresolved `b2` should not block the `b1` branch

The product should feel branch-based, not all-or-nothing.

### Clusters Are Gates, Not Primary Drill Targets

Clusters are structural containers.

They become available only when both are true:

- their governing backbone is `solid`
- all incoming prerequisite clusters are already `solidified`

Clusters should read as opened territory, not as the main boss themselves.

### Subnodes Are The Main Drill Rooms

Subnodes are the primary units of active reconstruction.

Once a cluster branch is available:

- its subnodes become the drillable rooms
- each subnode can be `locked`, `drilled`, or `solidified`
- cluster status is derived from those subnode outcomes

That means:

- all subnodes solid -> cluster reads `solidified`
- some attempted, not all solid -> cluster reads `drilled`
- none attempted -> cluster reads `locked`

### Fog Of War Must Be Truthful

Fog-of-war is not a skin.

It is the visual form of dependency logic.

The learner should be able to infer:

- what is not yet reachable
- what has been opened
- what has been cleared

without the system pretending they have earned access they have not yet earned.

### Graph Modes

The graph should support three UX modes:

#### `inspect`

Purpose:

- orientation
- node selection
- curiosity

Behavior:

- graph is legible
- selected node panel can show richer summary
- `Start Drill` is the dominant action

#### `drill-active`

Purpose:

- protect the Generation Effect

Behavior:

- active node remains clearly identified
- surrounding graph recedes
- prerequisite context may remain faintly visible for orientation
- answer-rich text is hidden
- right panel becomes task-focused

This mode should feel like combat:
the room is clear, the answer is not.

#### `post-drill`

Purpose:

- let the learner feel the result
- let the graph tell the truth
- give the learner control over pacing

Behavior:

- node state is updated
- result language is clear and non-judgmental
- mode persists until learner action
- no automatic timeout-driven transition

The user should decide when to continue.

## Right Panel Rules

The right panel is high risk because it can easily become a hidden answer key.

### In `inspect`

Allowed:

- node identity
- concise explanation
- status/gap metadata
- `Start Drill`

Important:

- on first entry or empty-space click, the panel should reinforce the current starting room
- it should not fall back to abstract filler copy that obscures the real progression state

### In `drill-active`

Allowed:

- node identity
- short instruction
- drill chat
- minimal state context

Not allowed:

- mechanism summary
- explanatory paragraph that gives away the answer
- detailed neighboring logic

### In `post-drill`

Allowed:

- truthful result framing
- gap description when relevant
- explicit continue action

Preferred copy:

- `Solidified. You rebuilt this from scratch.`
- `Revisit next session.`

Avoid:

- `Needs Re-drill`
- `Incorrect`
- `Failed`

## State Model

The graph uses three learner-facing states:

### `locked`

- not yet reachable
- low information
- inaccessible

### `drilled`

- attempted but not solid
- warm and return-worthy
- should not read as failure

### `solidified`

- mechanism successfully reconstructed
- stable, clear, rewarding

Gap taxonomy belongs in detail surfaces, not as a graph-wide decoding burden.

## Reward Design

Reward is part of the product, not decoration.

The system should create a visible, felt difference between:

- a routine correct step
- a genuinely strong causal reconstruction

Current product truth:

- solid answers should visibly solidify the node
- the graph should provide a small but clear resolution moment

Emerging direction:

- rare, stronger "critical hit" reward moments for exceptional causal answers
- sharper AI acknowledgment tone
- stronger UI bloom for unusually clean reconstruction

This is not current product law yet.
It is an evaluated direction to explore after functional reliability and testing.

## Personalization Strategy

Personalization in socraTink should not mean over-accommodation.

It should mean:

- adaptive pacing
- clear next actions
- preserving state across sessions
- surfacing revisit-worthy nodes
- making the learner's specific gaps visible and actionable

The product should feel like it understands where the learner's map is weak without turning that weakness into shame.

## What Makes It Addictive

The product becomes sticky when five things happen together:

1. The next action is always obvious.
2. The active problem feels bounded.
3. The interface withholds just enough to force generation.
4. The result feels truthful and visible.
5. The board changes in a way that creates immediate curiosity about what to do next.

This is the engine.

Not streaks.
Not XP bars.
Not empty praise.

## Current MVP Reality

The current app already has the right structural pieces:

- extraction to knowledge map
- graph rendered from persisted map state
- structured drill outcomes
- graph/drill lockstep at the node level
- `locked` / `drilled` / `solidified` state model
- graph inspect vs drill-active behavior
- `core-thesis` first-room progression
- independent backbone branch unlocking
- truthful fog-of-war based on dependency logic

Still emerging:

- stronger post-drill reward effects
- exceptional-answer reward tier
- deeper session persistence across refresh or device

## Design Questions To Use Before Shipping A Feature

Ask these before changing drill, graph, or reward behavior:

1. Does this help the learner generate, or does it help them recognize?
2. Does this keep the graph truthful, or does it fake progress?
3. Does this make the next action clearer, or add noise?
4. Does this make an unfinished node feel return-worthy rather than punitive?
5. Does this reward genuine understanding, or just participation?
6. Would this still feel good to a learner who is struggling, not just succeeding?

If the answer is weak on those questions, the feature is probably off-model.
