# Socratink Onboarding Tutorial Research Report

## Objective
Determine the best tutorial-animation strategy for Socratink and shape a recommendation that can later be converted into a product requirements document (PRD).

## Product context
Socratink appears to center on a learner moving through a truthful learning loop:
1. Create a concept
2. Drill recall
3. Return based on analytics and next best move

This implies the onboarding experience should teach one meaningful loop, not the entire product surface.

## Working thesis
Socratink should not lead with a long cinematic tutorial or forced product tour.

Instead, it should use a hybrid onboarding system:
- contextual coach marks
- interactive guided task completion
- small motion cues that direct attention
- optional micro-demo clips for abstract concepts
- progressive disclosure for advanced areas

## Why this fits the product
Socratink is not a generic dashboard. It has a specific philosophy: truthful learning through concept creation, recall, and return. The first-run experience should help a user feel that philosophy through action.

The right onboarding question is:
"What is the smallest successful learning loop a new user can complete in under 2 minutes?"

Proposed answer:
- create first concept
- perform first recall attempt
- see one meaningful reflection or analytics state

## Recommendation
### Primary pattern
Use guided task completion, not a narrated tour.

### Supporting pattern
Use lightweight animation only in four places:
1. Attention cue: subtle pulse / highlight to the next important action
2. Cause-effect feedback: motion after user actions so the interface feels understandable
3. Empty-state explanation: tiny loop or demo clip in places that are conceptually unfamiliar
4. Success reinforcement: a restrained completion state after the first meaningful loop

### Avoid
- full-screen auto-playing intro sequences
- 6+ step tooltip tours on first load
- motion that exists only to feel "premium"
- blocking users from exploring until the tutorial ends
- large moving backgrounds or parallax in core workflows

## Proposed onboarding architecture
### Layer 1: First-session activation
Goal: get the user to their first truthful win.

Flow:
1. Welcome message with one sentence on value
2. Prompt to create the first concept
3. Contextual cue pointing to drill / recall
4. After recall attempt, show a small explanation of what the result means
5. Point to next best move or revisit queue
6. End with a completion moment and an option to continue or explore

### Layer 2: On-demand micro-learning
Use small “What is this?” or “Show me” entries next to confusing surfaces.

Ideal targets:
- Truthful Progress
- Next Best Move
- Re-Drill Conversion
- Friction Zones
- Graph View vs Study View

### Layer 3: Progressive disclosure
Hide advanced or less-frequent explanatory content behind:
- expandable cards
- secondary panels
- learn-more links
- optional quick guide

## Animation system guidance
### Best medium by use case
- CSS / native UI motion: best for highlights, fades, slides, and success states
- Short product video (WebM/MP4): best for demonstrating a real workflow or explaining an abstract concept using the actual UI
- Lottie: best for decorative or illustrative loops that do not need true interactivity
- Rive: best when the animation itself needs state, branching, or interaction tied to product events

### Default recommendation for Socratink
- Use CSS/native motion for most in-app guidance
- Use short product video clips for optional explainers
- Use Lottie sparingly for empty states or polish
- Only use Rive if you want a reusable interactive explainer with multiple states

## Experience principles
1. Teach by doing
2. One action at a time
3. Keep copy short and benefit-led
4. Explain unfamiliar concepts at point of need
5. Respect reduced-motion preferences
6. Let people dismiss, replay, or skip help
7. Measure completion of meaningful actions, not tutorial views

## Suggested storyboard for first-run onboarding
### Step 1: Welcome
Copy: "Build one concept. Test what you can actually explain."
CTA: "Create first concept"

### Step 2: Create concept
UI cue highlights Add Concept.
After save, the board settles with a subtle confirmation motion.

### Step 3: First drill
Coach mark points to Drill.
Copy: "Try recall before help. The goal is truth, not streaks."
CTA: "Start first drill"

### Step 4: Result framing
After attempt, explain the status in plain language.
Copy example: "In progress means you attempted it, but it still needs a return."

### Step 5: Next move
Highlight Next Best Move or Revisit Queue.
Copy: "This is your shortest path back into a truthful drill."

### Step 6: Completion
Completion state: "You completed your first truthful loop."
Then offer:
- Continue drilling
- Explore analytics
- Open quick guide

## Technical implementation notes
- Prefer transform and opacity for motion
- Keep most transitions fast and restrained
- Do not autoplay instructional video with sound
- Use poster images and lazy loading for optional clips
- Use reduced-motion handling at the system preference level
- Add a user-visible replay help entry

## Metrics to track
### Activation metrics
- first concept created
- first drill started
- first drill completed
- first analytics panel viewed
- first return scheduled or revisit action taken

### Tutorial quality metrics
- onboarding completion rate
- time to first truthful loop
- % of users who skip onboarding
- % of users who replay help
- downstream retention of users who complete the first loop vs those who do not

### Qualitative checks
- Can a new user explain what “truthful progress” means?
- Can they tell what to do next without guessing?
- Do they feel interrupted or guided?

## Risks
- Over-explaining the philosophy before users act
- Treating every screen as equally important
- Adding motion that harms clarity or performance
- Building a polished tour before validating the first-run sequence with users

## Recommended next experiments
### Experiment A
No tour. Only an empty-state CTA and one cue to Add Concept.

### Experiment B
3-step guided task flow: create concept -> drill -> next best move.

### Experiment C
Same as B plus optional micro-demo clips for analytics terms.

Compare activation, skip rate, time to first successful loop, and week-1 return behavior.

## Conversion path to PRD
This report can convert into a PRD with the following sections:
- problem statement
- goals and non-goals
- user segments
- jobs to be done
- success metrics
- onboarding flow requirements
- motion/accessibility requirements
- instrumentation events
- experiments and rollout plan
- open questions

## Draft PRD seed statement
Socratink needs a first-run onboarding system that helps new users complete one truthful learning loop quickly, understand what to do next, and learn the product through action rather than passive explanation.