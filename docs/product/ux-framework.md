# socratink — Product UX Framework

## Agent Summary

> **What this document is**: The binding design contract for socratink. The unifying design principle is **metacognitive UX** — every surface is designed for the learner's awareness of their own cognitive process, not just the content. The document defines the three-phase learning loop (cold attempt → targeted study → spaced re-drill), the four-state graph model (locked → primed → drilled → solidified), the reward and sensory feedback layer, attribution management, session guardrails, bottleneck recovery, and the ethical engagement boundary. Every UX, state, routing, and AI design decision must pass the 14-question evaluation checklist at the end of this document.
>
> **When to read it**: Before making any change to drill UX, graph rendering, node state, AI prompt behavior, feedback copy, reward mechanics, or session flow. Before proposing any new feature.
>
> **What it is NOT**: It is not the implementation spec (read `progressive-disclosure.md`), the engineering invariants (read `../drill/engineering.md`), or the active release gate (read `../project/state.md`).
>
> **Key constraints an agent must never violate**:
> - The three-phase loop is mandatory. No phase may be skipped or collapsed.
> - `solidified` can only result from a spaced re-drill after buffer flush. Never from a cold attempt, study completion, or immediate post-study test.
> - The cold attempt is explicitly unscored. No classification, no tier/band, no performance metrics during Phase 1.
> - Sensory celebration is success-dependent and calibrated to cognitive load. Silence on unresolved outcomes.
> - The AI must remain the scaffold. The learner must remain the primary generator. If the AI talks more than the learner during drill, the passive trap has been triggered.
> - No streaks in MVP. If ever added, only as spaced session streaks that reward algorithmic adherence, not daily presence.
> - No features that lower the mastery bar to resolve progression bottlenecks.
> - Session cap: 25 minutes. Node cap: 4. Per-node retrieval ceiling: 3 successful retrievals per session.

---

## Product Thesis

The enemy is the illusion of competence.

Most learning tools reward exposure, recognition, and streak maintenance.
socratink should reward reconstruction.

The product is trying to make a hard cognitive act feel magnetic:

- enter a room you have never seen before
- attempt to explain what you think is inside
- discover where your understanding breaks
- earn the real explanation by struggling first
- return later and prove you actually understood it
- see the board change because of what was genuinely verified

The graph is not a content browser.
It is not a completion checklist.
It is a spatial record of verified understanding.

## Core Experience Goal

Make learning feel rewarding without lying to the learner.

That means:

- the learner should feel momentum
- the learner should feel curiosity
- the learner should feel a strong payoff when understanding is genuine
- the learner should get fast, specific feedback after they attempt reconstruction
- the initial struggle should feel like exploration, not evaluation
- the system should adapt support to the learner without lowering the mastery bar
- the product should become more accessible and more usable for different kinds of learners
- the system should never fake mastery to preserve motivation

Reward is allowed.
False reward is not.
Productive failure is a feature, not a bug — but it must be framed as exploration, never as judgment.

## Design Lens: Metacognitive UX

Every design decision in socratink is governed by a single unifying principle: **the product is designed for the learner's awareness of their own cognitive process, not just the content.**

Most learning products practice cognitive UX — they optimize how content is presented, consumed, and navigated. socratink practices metacognitive UX — it optimizes how accurately the learner can perceive, interpret, and trust their own understanding.

This lens determines what every surface in the product is actually doing:

| Surface | Cognitive UX would... | Metacognitive UX does... |
|---|---|---|
| Cold attempt | Pre-quiz the learner on upcoming content | Reveal the shape of what the learner doesn't know — and frame that discovery as exploration |
| Targeted study | Present information clearly | Show the learner exactly where their mental model broke, anchored to the prediction error they just generated |
| Spacing block | Enforce a wait | Teach the learner that their feeling of knowing is unreliable — post-study fluency is a cognitive illusion, not evidence of understanding |
| Trajectory contrast | Show a progress score | Show the learner how their own metacognitive predictions were wrong — the only intervention that updates beliefs about productive struggle |
| Normalization | Reduce anxiety | Teach the learner how to interpret difficulty — as a process feature, not an ability verdict |
| The graph | Track completion | Give the learner a spatial mirror of their understanding that they can trust because the system never inflates it |
| Session cap | Prevent fatigue | Teach the learner that their brain has consolidation constraints, and that respecting them is part of how mastery works |

When evaluating any new feature, the metacognitive UX lens asks: **does this make the learner's own cognitive process more visible and more accurately interpretable?** If it only makes content easier to consume without improving the learner's self-awareness, it is cognitive UX, not metacognitive UX — and it belongs in a different product.

## The Learning Loop

This section defines the canonical learning sequence for every node on the graph. It is the product's core architectural commitment and the foundation for all UX, state model, and AI design decisions.

### Why This Sequence

The research evidence establishes three findings that bind the product:

1. **Pretesting primes encoding.** Attempting retrieval on novel material — even with a near-total failure rate — produces stronger subsequent learning than studying first. The failed attempt generates a prediction error that makes the corrective study material land harder. The act of generating a guess activates semantic networks and primes the cognitive architecture for integration — simply showing preview questions does not produce this effect. (Kornell, Hays & Bjork 2009; Richland et al.)

2. **Corrective study after a cold attempt must be immediate.** The prediction error between the learner's guess and the real mechanism is most potent while the guess is still fresh. Delayed correction weakens the signal and risks encoding the error. (Prediction error learning literature; corrective feedback timing research.)

3. **Mastery verification requires genuine retrieval from long-term memory.** Testing immediately after study measures buffer access, not understanding. The working memory buffer must be cleared before a mastery check is valid. Testing within 1-2 minutes of study actively *suppresses* recall of related concepts through retrieval-induced forgetting (RIF). This inhibitory effect dissipates by 8-14 minutes and inverts into retrieval-induced *facilitation* at 20+ minutes — testing one node then strengthens recall of related nodes. The ideal spacing for the first retrieval event is 10-15 minutes of cognitively demanding interpolated activity, which clears the buffer, allows early-stage synaptic consolidation, and eliminates inhibitory side effects. (Ebbinghaus replication data; distractor task literature; Agarwal et al.; RIF temporal dynamics research; New Theory of Disuse.)

### The Three-Phase Node Loop

Every node on the graph moves through three phases. No phase may be skipped. No phase may be collapsed into another.

#### Phase 1: Cold Attempt

The learner encounters the node for the first time and attempts to explain what they think the mechanism involves — before any study material is shown.

Contract:

- The learner has not seen the mechanism text for this node.
- The drill asks an open, exploratory question: "What do you think this involves?" — not "Explain this mechanism."
- The goal is to generate a prediction error, not to evaluate mastery.
- A wrong answer is the expected outcome. A partially right answer is a bonus.
- The cold attempt must never feel like a test. It is entering a room, not taking an exam.
- The cold attempt must force a generative commitment — passive reading of objectives or preview questions does not trigger the pretesting effect.
- No score, no points, and no performance metrics are shown during or after the cold attempt. It is explicitly unscored. This is required to prevent activation of the test anxiety response and to support affective inoculation.

Minimum generative commitment:

- The pretesting effect requires the learner to *commit to a guess*. Simply reading the question, typing "idk," or submitting a minimal-effort token is not generative and does not trigger semantic network activation.
- The cold attempt must require a minimum generative threshold before the study view unlocks. This is not a score — it is a structural gate that ensures the cognitive priming mechanism actually fires.
- The AI should prompt for elaboration on minimal responses: "Tell me more — what's your best guess about what happens here?" This is a neutral push for genuine generation, not a punitive demand.
- If the learner provides a substantive but wrong attempt, the study view unlocks immediately. If the learner provides a non-attempt (single word, "I don't know," random characters), the AI nudges once before unlocking. The nudge must stay warm and exploratory — it must never feel like gatekeeping.
- The study experience itself should be richer when the cold attempt was genuine. A real attempt creates a prediction-error anchor that makes the study view land harder. A non-attempt produces study without that anchor — the learner still sees the material, but the cognitive benefit is diminished. This creates a natural incentive to attempt genuinely without adding punitive consequences.

Zero-schema detection:

- The generation effect breaks down completely when the learner has absolute zero schema for the domain. Forcing unguided generation on a true novice causes cognitive overload, not productive struggle.
- The AI must detect zero-schema states within the first response. Signals include: inability to produce even basic relevant vocabulary, total absence of domain-adjacent concepts, or explicit statements of complete unfamiliarity.
- When zero schema is detected, the AI pivots to scaffolded cold attempt mode: it seeds two or three foundational concepts explicitly ("Here are the basic pieces..."), then asks for a micro-generation on a smaller piece ("Given those pieces, what do you think happens next?").
- The scaffolded cold attempt still forces generative commitment. It reduces the intrinsic cognitive load to a manageable level while preserving the pretesting effect on the micro-generation.
- Distinguishing genuine zero-schema from strategic speed-running is a known hard problem. The minimum generative threshold is the primary defense; zero-schema scaffolding is the secondary defense for genuinely lost learners.

What the cold attempt earns:

- The node transitions to a `primed` state.
- The study view unlocks for that node.
- No mastery credit. No downstream unlocks. No graph territory expansion.

#### Phase 2: Targeted Study

Immediately after the cold attempt, the study view opens with the mechanism text for the node the learner just attempted.

Contract:

- The study material is presented as corrective feedback, not as a standalone reading assignment.
- When the learner made a genuine cold attempt, the study view highlights where their attempt diverged from the mechanism. This prediction-error anchoring makes the material land harder cognitively.
- When the learner made a minimal or non-attempt, the study view still opens but without the anchoring contrast. The experience is complete but cognitively less potent — the learner skipped the priming step.
- The study view shows structure and explanation for the attempted node — not the entire graph.
- This is the reward for attempting. The learner earns the explanation by struggling first.
- The study view must not become a pre-drill answer key for future nodes.
- For ADHD learners, a brief transition beat (2-3 seconds) between the cold attempt and the study reveal is preferable to an instantaneous switch. Immediate feedback can overwhelm striatal dopamine pathways in ADHD populations. A micro-delay reroutes processing to declarative memory, where ADHD learners perform at parity with neurotypical peers. This is not a hard gate — it is a gentle breathing moment.

What targeted study earns:

- Nothing changes on the graph. The node remains `primed`.
- The learner now has an encoding event anchored by a prediction error.
- The node becomes eligible for the re-drill after sufficient buffer flush.

#### Phase 3: Spaced Re-Drill

After the working memory buffer has been cleared — through interleaved work on other nodes, distractor activity, or sufficient elapsed time — the learner is drilled again on the same node.

Contract:

- The preferred buffer flush is 10-15 minutes of cognitively demanding interpolated activity. This is the evidence-backed ideal that clears the buffer, allows early-stage consolidation, and eliminates retrieval-induced forgetting of related concepts.
- The minimum acceptable buffer flush is 5 minutes of demanding interpolated activity. Below 8 minutes, residual inhibitory effects on related nodes may persist.
- Interleaving cold attempts and study on other nodes is the preferred distractor — it creates natural buffer flush while keeping the learner inside the product.
- The re-drill must require genuine long-term memory retrieval, not buffer echo.
- The re-drill should demand multi-step causal reconstruction, not simple fact recall. For complex mechanisms, the AI should prompt self-explanation ("explain why step 2 follows step 1"), summarization ("walk me through the sequence"), or teaching ("explain this to a confused beginner"). These Generative Learning Strategies produce deeper transfer than basic recall prompts.
- Only a `solid` classification on the spaced re-drill earns `solidified`.
- A non-solid result on the re-drill marks the node as `drilled` — attempted, understood partially, worth returning to.
- No hard time gates that force the learner to leave the app. The interleaved distraction paradigm solves spacing within a single session.
- Three successful retrievals of the same node in one session is the ceiling. Beyond three, retrieval strength is artificially high and additional practice provides near-zero Storage Strength gain. The system should automatically halt drilling on that node and schedule it for a later session.

What the spaced re-drill earns:

- `solid` classification → node becomes `solidified`, downstream unlocks may evaluate.
- Non-solid classification → node becomes `drilled`, remains return-worthy.

### Interleaving as the Spacing Mechanism

The product does not use clock-time gates to enforce spacing. Instead, it uses interleaved node work as a natural distractor.

The intended session rhythm:

- Cold attempt on Node A
- Cold attempt on Node B
- Targeted study on Node A
- Cold attempt on Node C
- Targeted study on Node B
- Spaced re-drill on Node A
- Targeted study on Node C
- Spaced re-drill on Node B
- ...and so on

This rhythm keeps the learner inside the product, maintains momentum, and achieves genuine buffer flush through cognitive interference rather than forced waiting. The natural elapsed time between study and re-drill in this rhythm is approximately 10-15 minutes — hitting the ideal spacing window.

The system may recommend the next node to attempt or re-drill. It must not silently retarget the active drill.

Two to three nodes in active rotation is the recommended ceiling. More than three risks cognitive overload, especially for learners with working memory deficits.

#### Interleaving Must Feel Like A Guided Path, Not A Juggling Act

The interleaving rhythm requires constant context-switching between nodes in different phases. For learners with organizational deficits, maintaining "where am I in the map" awareness while juggling disparate mechanism states will heavily tax working memory.

Mitigations that are binding:

- The graph must visually highlight the single active node and dim everything else.
- The side panel must unambiguously show the current phase (cold attempt, study, or re-drill) for the active node. No mode bleed.
- The interleaving recommendation must be a single, clear "next step" — not a menu of choices. "Next: explore Node B" or "Next: re-drill Node A" — one action, named explicitly.
- The system should manage the interleaving queue automatically. The learner's job is to follow the guided path, not to plan their own rotation. Advanced learners may override, but the default is guided.
- If the learner loses orientation ("wait, which node am I on?"), the interface has failed regardless of how correct the cognitive architecture is underneath.

### Bottleneck Recovery

If a learner repeatedly lands on `drilled` (non-solid) during spaced re-drills on a foundational node, and that node is gating downstream content, the product can functionally deadlock. The session ceiling (three attempts per node) forces them to wait for another session. If only 1-2 nodes are available in their current horizon, the dungeon locks up.

This is pedagogically sound but experientially catastrophic. The product must provide recovery paths that maintain graph truth while preventing session abandonment.

#### Escalating Scaffold Path

After repeated non-solid results on the same node across sessions, the AI should progressively increase scaffolding:

- First re-drill: standard open reconstruction demand.
- Second re-drill (same node, subsequent session): the AI breaks the mechanism into sub-steps and asks the learner to reconstruct one piece at a time.
- Third re-drill (same node, subsequent session): the AI provides the first step of the mechanism and asks the learner to generate the causal link to step two.

The mastery bar does not lower. `solid` still requires full mechanism reconstruction. But the scaffolding ramps up to reduce the gap between the learner's current understanding and the target.

#### Study Revisit Path

After a non-solid re-drill, the study view should reopen with a *different* framing of the same mechanism — an alternate explanation, a different analogy, a visual representation, or a reorganized causal sequence. This gives the learner new encoding material anchored to a fresh prediction error (the specific gap they just revealed on the re-drill) without lowering the bar.

#### Branch Escape Path

If the knowledge map has multiple backbone branches, the learner should be able to enter a different branch's cold-attempt sequence while the blocked node stays `drilled`. This prevents total session deadlock for maps with parallel structure.

For linear maps with no parallel branches, the escalating scaffold path is the only recovery mechanism.

#### What The Product Must Not Do

- Lower the mastery bar for gating nodes to resolve deadlock.
- Award `solidified` based on accumulated effort or number of attempts.
- Auto-unlock downstream content after N failed re-drills.
- Frame repeated `drilled` results as personal failure.

## Node State Model

The graph uses four learner-facing node states:

### `locked`

- Not yet reachable.
- Prerequisites not yet satisfied.

### `primed`

- Cold attempt completed.
- Study view unlocked for this node.
- Not yet eligible for mastery verification.
- Should feel like: "You've entered this room. Now prepare for the real challenge."

### `drilled`

- Spaced re-drill attempted but not solid.
- Should feel in-progress, not punitive.
- Worth revisiting. The next gain is here.

### `solidified`

- Mechanism successfully reconstructed from long-term memory on a spaced re-drill.
- Verified understanding.
- Downstream unlock checks may now re-evaluate.

These states are projected from persisted knowledge-map data, not invented by the rendering layer.

## AI Contracts

AI is desirable in this product when it increases the quality, speed, accessibility, and frequency of truthful learning loops.

AI is not the learning event.
It is a support layer around the learning event.

The core learning event is:

- learner enters a room cold and attempts to explain
- system captures the prediction error
- learner receives targeted corrective study
- after buffer flush, learner reconstructs from genuine memory
- system evaluates the attempt
- graph updates truthfully

If AI makes that loop easier to enter, easier to understand, or easier to repeat, it is useful.
If AI replaces that loop, it is misaligned.

### Drill Prompt Contract

The AI must remain the scaffold, not the generator. The learner must be the primary generator of the target mechanism.

Binding constraints:

- During the cold attempt, the AI asks one open question and listens. It does not lecture, pre-explain, or seed the answer.
- During the cold attempt, if the learner provides a minimal or non-generative response, the AI nudges once for elaboration before transitioning to study. The nudge must stay warm and exploratory.
- During the spaced re-drill, the AI prompts for multi-step causal reconstruction using Generative Learning Strategies: self-explanation, summarization, teaching, or problem-posing. It does not accept one-word or single-fact answers as sufficient for complex mechanisms.
- The AI must not provide the answer after a single "I don't know." It must break the question into scaffolded pieces first.
- If the learner gives a substantive but incomplete answer, the AI probes the specific gap — it does not re-explain the full mechanism.
- AI responses during drill should be deliberately sparse. Short. Pointed. Gap-identifying. If the AI talks more than the learner during a drill turn, the passive trap has been triggered and the generation effect is compromised.
- The AI must detect zero-schema states and pivot to Load Reduction Instruction rather than continuing to demand unguided generation from a completely lost learner.
- Periodically, the re-drill should ask for macro-level integration: "How does this node connect to the broader structure?" This forces organizational processing that isolated micro-section recall does not build — especially important for ADHD learners.
- On repeated non-solid results for the same node, the AI should escalate scaffolding per the Bottleneck Recovery contract.

### Desirable Uses Of AI

1. **Personalization without comfort-lying.** Tailor pacing, scaffolding, modality, and cold-attempt calibration to the learner's current state. Never hide difficulty. Never confuse preference with mastery.

2. **Feedback after generation.** Fast, specific feedback after the learner attempts. In the cold attempt: open the study view anchored to the divergence. In the re-drill: classification, gap description, and clear indication of room status. Generation first. Recognition second.

3. **Content creation as support.** Drills, examples, assessments, alternate explanations. Not answer leakage or low-truth assessment.

4. **Inclusivity and access.** Text-to-speech, speech-to-text (voice input activates the Production Effect for additive encoding), alternate reading levels, visual representations. Unlimited time. Feedback on the same screen as the attempt.

5. **Concept rendering.** Diagrams, analogies, alternate framings that clarify structure without collapsing the answer into the interface.

6. **Operational leverage.** Lesson planning, practice variants, learner pattern summaries, administrative support.

7. **Critical thinking about AI itself.** Reinforce checking coherence, noticing uncertainty, evaluating when output is misleading.

### AI Risk Flags

1. **Privacy drift.** Minimum necessary data. No trading learner privacy for convenience.
2. **Algorithmic bias.** Model fluency preferences must not masquerade as learning truth.
3. **Human relationship erosion.** More room for human support, not less.
4. **Cost equity.** No unsustainable spend to deliver the core loop.
5. **Answer outsourcing.** If cheating is easier than thinking, the UX is broken.
6. **Overconfidence.** AI output is assistive, not self-authenticating.

## Primary Metaphor

The graph behaves like a dungeon map.

- each graph node is a room
- the learner enters the room before they know what is inside
- the cold attempt is stepping through the door
- the targeted study is the room revealing itself after the learner has tried
- the spaced re-drill is the room's boss fight
- the learner must beat that boss before the room is truly cleared
- new rooms should open only when prerequisite understanding is real

If a feature makes it feel like the learner fought one room while the system updated another, the feature is wrong.
If a feature lets the learner read the boss's playbook before entering the room, the feature is wrong.

Keep the metaphor structural, not narrative. Light quest language improves satisfaction without cognitive cost. Elaborate storylines decrease procedural knowledge transfer (Armstrong & Landers 2017, d = -0.40).

## Secondary Emotional Analogy

Tetris is a useful analogy for the rhythm of drilling.

The right feeling is:

- one problem at a time
- visible structure, hidden solution
- meaningful consequence
- satisfaction when a move is genuinely clean

Applied:

- the graph is the board
- the active node is the current problem
- the cold attempt is the piece appearing
- the interleaved rhythm is the falling cadence
- `solidified` is a clean line clear
- `drilled` is unresolved stack pressure, not failure
- `primed` is a piece in play, not yet placed

## Attribution Management

How a learner interprets difficulty determines whether they persist or quit. This is the primary determinant of product retention.

When a learner attributes struggle to fixed ability ("I'm not smart enough"), the result is learned helplessness and abandonment. When they attribute it to changeable strategy ("I haven't built the right mental model yet"), the result is persistence.

socratink has no human teacher to manage attributions in real time. The interface is the attribution manager. Every piece of copy, every state transition, every visual treatment is either pushing toward adaptive attribution or maladaptive attribution. There is no neutral position.

### Attribution Requirements

Binding:

#### 1. Frame Errors As Strategy Data, Not Ability Verdicts

All error states, gap descriptions, and non-solid classifications must be framed in terms of strategy and approach, never capacity or intelligence.

Good: "The causal link between step 2 and step 3 needs a different angle."
Bad: "You don't understand this concept."

#### 2. Normalize Struggle Through Social Proof

Brief messages conveying "struggle is universal and temporary" durably shift attribution patterns and increase persistence. (Park et al. 2022, N=6,163; Walton & Cohen 2011; Lin-Siegler et al. 2016.)

Show a normalization message during or after every cold attempt. Rotate variants. Use process-outcome framing for peer comparisons: "Learners who re-drilled this node improved by 40%." Never compare to top performers.

When the system detects repeated failures on a specific node, surface identity-reinforcing messaging: "This is a structurally complex node. Over 80% of learners require multiple spaced sessions to solidify this concept. Your current struggle is the exact mechanism of memory formation."

#### 3. Use Wise Feedback On Non-Solid Results

The "wise feedback" formula (Cohen, Steele & Ross 1999): high standards + belief in the learner + specific next steps.

Applied: "This concept is designed to be challenging. We know you can master it. Focus on the connection between [specific gap] next time."

#### 4. Build Metacognitive Correction Into The Loop

The tier/band system (`spark → link → chain → clear → tetris`) serves as the trajectory contrast mechanism.

Showing the learner their own improvement — "Your cold attempt was a spark. Your re-drill hit chain. That jump is real learning." — motivates through visible growth AND calibrates metacognitive accuracy.

Learners systematically undervalue pretesting even after experiencing better outcomes (Pan & Rivers 2023). The only intervention that updated their beliefs was explicit prediction-contrast.

## Framing and Attrition

The cold-attempt-first architecture guarantees that the learner's initial interaction with every node will be characterized by failure. This is the intended design. But if failure is not carefully framed, it triggers dropout.

- Learners cannot self-correct the belief that failure means incompetence.
- Unframed pretests increase attrition in self-directed digital environments.
- Up to 40% of learners experience test anxiety.
- However, repeated low-stakes pretesting *inoculates* against test anxiety by decoupling the threat response from being tested.

### Framing Requirements

Binding:

#### 1. The Cold Attempt Must Never Feel Like A Test

Avoid "test," "quiz," "exam," or "assessment" in any learner-facing surface during the cold attempt.

Preferred: "Enter the room" / "What do you think this involves?" / "Take your best guess — this is how the brain warms up."

#### 2. Wrong Answers Must Be Explicitly Normalized

The interface must actively communicate that wrong answers during the cold attempt are expected, productive, and part of the design.

#### 3. ADHD And Working Memory Accommodations Are Structural

Core design constraints, not edge-case toggles:

- No timed interactions. No ticking clocks. No countdown pressure.
- Feedback on the same screen as the attempt.
- 2-3 second transition beat between cold attempt and study reveal.
- Two to three nodes in active rotation is the ceiling.
- Periodic macro-level integration prompts.
- Session length caps enforced.

## Session Guardrails

Cognitive effectiveness of retrieval practice is subject to severe diminishing returns.

### Session Length

- Evidence-based optimal for ADHD: 15-25 minutes.
- Neurotypical ceiling: 40-60 minutes.
- Default hard cap: 25 minutes. Secondary: 4 nodes.

### Per-Node Retrieval Ceiling

Three successful retrievals per node per session. Beyond three, halt and schedule for later.

### Session Ending: Leave Them Hungry

End sessions at a point of engagement, not exhaustion. Use absolute limits (less reactance than flexible). Explain the science transparently. Frame warmly: "Progress locked in. Your neurons do the rest while you're away." Never end on a failure state.

This triggers episodic anticipation — stopping the learner while their dopaminergic "wanting" system is still active. The learner leaves with unresolved nodes visible (Ovsiankina resumption drive), clear progress data (competence satisfaction), and a physiological drive to return. Over time, they recognize the cap serves their mastery goal, supporting long-term autonomy. The instruction to "come back tomorrow" becomes a scientifically validated prescription, not a restriction.

## Reward and Sensory Feedback

The product must feel magnetic without lying about outcomes. The reward layer celebrates genuine cognitive achievement — it never rewards activity, exposure, or time spent as if they were understanding.

### The Engagement Engine Is Already Built

A retrieval practice system calibrated near the learner's retrieval threshold already generates maximal engagement:

- Dopamine neurons fire maximally at 50% probability of success. (Fiorillo, Tobler & Schultz 2003.)
- Reward prediction errors are strongest on surprising successes. (Schultz, Dayan & Montague 1997.)
- Flow states emerge from adaptive challenge just above current skill. (Csikszentmihalyi 1990.)

The dopaminergic "wanting" system (mesolimbic, incentive salience) is neurally separable from the "liking" system (hedonic hotspots, mu opioids). Satisfying micro-animations and sounds most likely target the wanting system — driving return behavior without inflating perceived competence. But when wanting chronically outstrips liking, the result resembles addiction rather than engagement. The product must keep both systems aligned by tying sensory reward to genuine achievement.

The primary design challenge is not *creating* engagement but *not destroying* the engagement that genuine difficulty already provides.

### Sensory Feedback: Calibrated To Cognitive Load

Moderate sensory celebration of genuine success is safe and effective. Both no feedback and excessive feedback hurt. (Kao 2020, N=3,018 — inverted-U relationship.)

Binding constraints:

- Sensory feedback must be **success-dependent** — tied to actually achieving a state transition. Success-independent celebration does not increase enjoyment. (Ballou et al. 2024.)
- Sensory treatment should be **calibrated to the cognitive load of the achievement.** A fluent, high-confidence solidification gets a crisp, snapping animation that implies immediate crystallization. A heavily scaffolded, barely-solid retrieval gets a subdued, stabilizing visual effect that acknowledges the struggle. Both are truthfully solidified — the aesthetic mirrors the quality of the cognitive work without lying about the outcome.
- `solidified` transitions: strongest celebration — this is the line clear.
- `primed` transitions: subtle, warm acknowledgment — the learner entered the room.
- `drilled` (non-solid re-drill): **no celebration**. The sensory layer stays silent. Copy and framing handle the affect.
- Sound effects on correct retrieval enhance motivation and concentration but do not independently improve encoding. (Wang & Lieberoth 2016, N=593.) Audio should mirror cognitive load: a deep, resolving harmonic chord for a complex mechanism solidified; a lighter confirmation tone for simpler nodes. Brief is safe. Elaborate is distraction risk.
- Haptic feedback should punctuate the **moment of generation**, not the system's processing or result display. A subtle tactile pulse timed to the exact moment the learner commits their generated response grounds the abstract retrieval task in a physical sensation tied to the generation effect itself. This transforms haptics from generic feedback into embodied reinforcement of cognitive effort. Use brief, subtle vibration on solidified commits only. Complex vibration patterns carry distraction and metacognitive distortion risk. (Froehlich et al. 2025; Jones et al. 2021.)
- Consider fading feedback frequency over time — reducing feedback frequency is itself a desirable difficulty (Bjork 1994).

### Node State Visual Transitions

The graph's visual state changes *are* the primary reward mechanism.

- Color conventions: muted gray/slate = locked, cool blue or soft warm tone = primed, warm amber = drilled, gold/green = solidified. Transitions should be perceptually smooth — follow perceptual uniformity principles (e.g., CIEDE2000) so the central range of a color transition carries the majority of the visual change, avoiding abrupt jumps. Follow the 60-30-10 rule: 60% neutral base, 30% secondary color, 10% energizing accent. Treat specific color choices as hypotheses to test.
- Front-load achievable early nodes. Goal-gradient: learners accelerate near completion horizons of 5-8 nodes. (Kivetz et al. 2006.)
- Slow early progress produces highest abandonment. (Conrad et al. 2010.) The graph should feel responsive to initial effort.
- Show next-horizon nodes (3-5 adjacent), not the entire remaining graph. Too much visible incompleteness creates anxiety. (Masicampo & Baumeister 2011.) The Ovsiankina effect (behavioral urge to resume incomplete tasks) makes visible `primed` and `drilled` nodes pull learners back — but this operates through resumption drive, not enhanced memory for the content. The Zeigarnik memory advantage for incomplete tasks has not been supported by modern meta-analytic evidence (Ghibellini & Meier 2025).

### Endowed Progress Through Truthful Prerequisites

When a learner enters a new cluster or branch, the graph should visually connect and illuminate prerequisite nodes they have already legitimately mastered from earlier work. Frame the new territory as a partially completed structure: "You already possess the foundational mechanisms for this area."

This triggers the endowed progress effect (Nunes & Dreze 2006: 34% vs 19% completion) without faking mastery. The 10-25% initial progress sweet spot applies — over-endowment undermines the effect because the effort feels unearned. The advancement must reflect real, previously verified understanding.

### Streaks, Badges, and Points

High-risk mechanics in a product built on truthful mastery.

#### Streaks

Traditional daily-login streaks produce hollow engagement. "People weren't logging in to learn anymore. They were logging in so they didn't lose." (Duolingo's own assessment.)

No streaks in MVP. If ever implemented, only as **spaced session streaks** — rewarding adherence to the algorithmically prescribed spacing intervals, even if that means not logging in for two days. This aligns the psychological pull of a streak with the cognitive science of memory formation. The optimal action might be *not* opening the app today, and the streak should reward that discipline rather than punishing it.

#### Badges

- **Mastery badges** (demonstrated retrieval competence) satisfy competence needs and are informational by nature. (Abramovich et al. 2013.)
- **Resilience badges** (solidified a node after multiple failed re-drills across sessions) explicitly celebrate productive failure recovery. These reinforce the psychological safety of making mistakes and honor the persistence required to overcome cognitive friction. This is the strongest badge the product can award.
- **Effort/participation badges** have no impact on learning or motivation and risk feeling patronizing. Do not implement.
- Caution: low performers find mastery badges demotivating when unachievable. Early badges must be achievable (solidified your first node, completed your first re-drill) before escalating.
- Frame as competence feedback ("this tells me I've mastered a real skill"), never behavioral mandates ("earn this to progress"). Controlling rewards undermine intrinsic motivation at d = -0.36 to -0.40. (Deci et al. 1999.)

#### Points

- As progress indicators (not currency) can work. (Mekler et al. 2017.)
- Never purchasable, tradeable, or gating.
- Represent verified understanding, not activity volume.
- Variable/surprise point bonuses may be applied to engagement behaviors (returning to the app, completing a spaced session) but never to accuracy — variable reinforcement on accuracy distorts metacognitive calibration and undermines the learner's ability to judge what they actually know.

### Trajectory Contrast

The `spark → link → chain → clear → tetris` progression serves as the primary metacognitive and motivational mechanism.

- Show trajectory, not score: "Your cold attempt was a spark. Your re-drill hit chain. That jump is real learning."
- Never show during the attempt. Show as post-attempt reflection on growth.
- Always pair with interpretive framing. Raw analytics without meaning frames show null or negative effects.
- Temporal self-comparison raises pride and calibrates metacognitive accuracy. (Chiviacowsky et al. 2018; Butler, Karpicke & Roediger 2008.)

## Non-Negotiable UX Principles

### 1. Attempt Before Exposure

The study view does not unlock until the cold attempt is complete. AI must not reveal the mechanism before the attempt. The graph may identify the active room but must not display mechanism text for unattempted nodes.

### 2. One Active Cognitive Target

At any moment, the learner should know what they are working on, where it sits, what phase it is in, and whether it is primed, drilled, or cleared. No silent target switching. No mode bleed. The interleaving rhythm must feel guided — if the learner loses orientation, the interface has failed.

### 3. The Graph Must Tell The Truth

A cold attempt is not mastery. Studying is not mastery. A buffer-echo test is not mastery. Accumulated effort is not mastery. Only a solid classification on a spaced re-drill earns `solidified`. Only verified long-term retrieval opens downstream territory. Repeated non-solid results on a gating node do not auto-unlock.

### 4. Reward Must Be Earned

Selective visual and sensory change on `solidified`, calibrated to cognitive load. Silence on `drilled`. The study view is a reward earned by attempting. Moderate juice on genuine success. No consolation animations. Never treat the cold attempt as scored.

### 5. In-Progress Must Not Feel Punitive

- `primed`: "You've stepped inside. The real challenge is ahead."
- `drilled`: "Worth revisiting. The next gain is here."
- `solidified`: "Cleared. You proved it."

The Ovsiankina effect makes incomplete nodes a natural return driver.

### 6. AI Should Reduce Friction, Not Remove Thinking

Good: faster entry, clearer diagnosis, easier access, automated interleaving.
Bad: skipping the cold attempt, revealing the mechanism early, AI responses so rich the learner goes passive.

### 7. AI Must Preserve Trust, Fairness, And Human Judgment

Bounded data. Fair evaluation. Visible uncertainty. Preserve human teachers and coaches.

## What The Graph Is For

The graph exists for orientation and truthful progression.

It should answer: where am I, what is available, what phase is each node in, what changed.

It should not answer: what exact mechanism should I parrot back right now.

The study view is the mechanism-revealing surface. It is gated behind the cold attempt. The graph is the map. The map shows rooms, not answers.

## Ethical Engagement Boundary

The diagnostic question (Kim & Werbach 2016): Would the learner still choose this behavior if they fully understood how the system was influencing them?

If a mechanic relies on loss aversion, near-miss frustration, FOMO, or mechanisms that only work when the learner is unaware — it has crossed into manipulation. If it transparently supports a goal the learner reflectively endorses — it is ethical.

### Roguelike Design Patterns

Mastery-based game design provides the model for ethical magnetic engagement:

- **The run = the spaced session.** The learner engages in a session of difficult retrievals. Failure is expected. When a concept isn't retrieved, the node's progress resets to `drilled`, requiring re-drilling in a future session. No points lost, no punishment — just an honest record.
- **Permadeath = the node stays drilled.** The node is not permanently failed. It is honestly unresolved and scheduled for return. Every failed retrieval contributes data to the spacing algorithm and the escalating scaffold path.
- **Meta-progression = the knowledge graph.** Even a session full of non-solid results advances the meta-game. The graph records effort, adjusts difficulty, and unlocks contextual scaffolding. The learner never feels their time was wasted.
- **High skill ceiling.** The mastery bar never lowers. `tetris`-band responses on complex mechanism nodes represent genuine cognitive achievement that most learners will reach only after multiple sessions.
- **Enforced scarcity builds anticipation.** Session caps stop the learner while wanting is still active. Like Wordle's one puzzle per day — no streak anxiety, no monetization pressure, just anticipation.

socratink enforces session caps and spacing. This is anti-compulsion by design. When the science is explained transparently and the cap is absolute, learners internalize the constraint as self-endorsed. (Laurin et al. 2012.)

## Evidence Posture

### Directly Supported By Research

- Pretesting on novel material improves subsequent encoding, even with ~95% initial failure rates. (Kornell, Hays & Bjork 2009.)
- The pretesting effect requires active generative commitment. (Kornell et al. Experiment 5.)
- Immediate corrective feedback after pretesting maximizes the prediction error signal.
- Testing within 1-2 minutes suppresses related recall (RIF, d = 0.73-1.00). Testing at 20+ minutes facilitates it.
- 10-15 minutes of interpolated activity is ideal for buffer clearance and early-stage consolidation.
- Lower working memory capacity learners benefit disproportionately. (Agarwal et al.)
- Three successful retrievals per session is the ceiling for Storage Strength gain.
- The generation effect breaks down at zero schema. Load Reduction Instruction required. (Cognitive Load Theory.)
- Multi-step mechanisms require Generative Learning Strategies. (Fiorella & Mayer.)
- Typed responses ≈ handwriting for free recall.
- Socratic AI tutoring ≥ human-led active learning when scaffolded with domain expertise. (Harvard physics RCT.)
- Learners undervalue pretesting. Prediction-contrast is the only belief-updating intervention. (Pan & Rivers 2023.)
- Low-stakes pretesting inoculates against test anxiety.
- ADHD: equivalent testing effect, weaker initial encoding, 15-25 min session caps, micro-delayed feedback achieves parity, macro retrieval > fragmented micro-recall.
- Moderate success-dependent sensory feedback follows inverted-U. (Kao 2020; Ballou et al. 2024.)
- Dopamine signals prediction error, maximum at 50% success probability. Wanting is separable from liking. (Schultz et al. 1997; Fiorillo et al. 2003; Berridge & Robinson.)
- Social normalization increases persistence. (Park et al. 2022; Walton & Cohen 2011; Lin-Siegler et al. 2016.)
- Controlling rewards undermine intrinsic motivation (d = -0.36 to -0.40). Competence feedback enhances it (d = +0.33). (Deci et al. 1999.)
- Mastery badges > participation badges. Low performers find unachievable mastery badges demotivating. (Abramovich et al. 2013.)
- Absolute limits produce less reactance than flexible limits. (Laurin et al. 2012.)
- Temporal self-comparison raises pride and competence. (Chiviacowsky et al. 2018; Gürel et al. 2020.)
- Open learner models with mastery visualization enhance learning. (Long & Aleven 2017; Hooshyar et al. 2019.)
- Endowed progress effect increases completion (34% vs 19%). 10-25% initial progress sweet spot. (Nunes & Dreze 2006.)
- Elaborate narrative framing decreases procedural knowledge (d = -0.40). (Armstrong & Landers 2017.)
- The Ovsiankina effect (behavioral resumption drive for incomplete tasks) is robust. The Zeigarnik memory advantage is NOT supported by modern meta-analysis. (Ghibellini & Meier 2025.)

### Indirectly Supported

- Interleaved node work should produce effective buffer flush by analogy to studied interpolated activity paradigms.
- Voice input would activate the Production Effect for additive encoding.
- Goal-gradient acceleration near completion horizons should increase engagement.
- Haptic feedback timed to the generation moment should ground retrieval in embodied reinforcement. (Motor learning haptic research; not tested in declarative retrieval.)
- Calibrating juice intensity to cognitive load should provide informative intrinsic feedback. (Game design juice research; not tested in educational retrieval.)
- Endowed progress through truthful prerequisite visualization should increase persistence in new clusters. (Nunes & Dreze; not tested in knowledge graph contexts.)

### Product Hypothesis

- The interleaving rhythm will feel natural. UX hypothesis.
- Two to three nodes is the right rotation ceiling. Calibrated to ADHD, not validated in-product.
- The tier/band system can serve as metacognitive prediction-contrast. Informed by Pan & Rivers, not directly tested.
- Color-state transitions carry expected affective weight. Industry convention, no experimental validation.
- Session caps with transparent science increase return motivation. Grounded in reactance research, not tested in-product.
- Minimum generative threshold prevents button-mashing without feeling punitive. Design hypothesis.
- Guided interleaving prevents cognitive overload during context-switching. Design hypothesis.
- Escalating scaffolding prevents deadlock without lowering the mastery bar. Informed by Load Reduction research.
- Spaced session streaks align streak psychology with spacing science. Not tested anywhere.
- Resilience badges celebrate productive failure recovery. Informed by badge literature, not directly tested.
- Perceptually uniform color transitions (CIEDE2000) feel more natural than abrupt color jumps. Supported in color science; not validated in learning graphs.

## Evaluating New Ideas

When evaluating a new UX idea, ask:

1. Does this preserve the three-phase node loop, or does it let the learner skip a phase?
2. Does this make the learner's current target and current phase clearer or blurrier?
3. Does this make the graph more truthful or more decorative?
4. Does this reward real reconstruction from long-term memory, or does it reward buffer echo?
5. Does this preserve curiosity without revealing the answer before the attempt?
6. Does the AI support the learning loop or replace the learner's thinking?
7. Does this frame difficulty as exploration or as evaluation?
8. Does the reward layer celebrate genuine achievement or cushion failure?
9. Does this preserve trust, fairness, privacy, and meaningful human oversight?
10. Could this feature cause attrition among anxious or neurodivergent learners?
11. Would the learner still choose this behavior if they fully understood how the system was influencing them?
12. Does this create a new way to game the system without genuine cognitive effort?
13. Could this cause session deadlock for learners stuck on a gating node?
14. Does this make the learner's own cognitive process more visible and accurately interpretable — or does it only make content easier to consume?

If the answer is wrong on any of those questions, the idea is misaligned even if it feels polished.
