# socratink — UX Design Document

> A capture of the user experience this design system encodes. Not a style sheet — a description of how the product **feels** to use, why each surface behaves the way it does, and what the system refuses to do.

> **Vocabulary.** This document uses the project's ubiquitous language. The authoritative term list — binding definitions for **Graph truth**, **Recorded evidence**, **Reconstruction evidence**, the four learning-loop states, and **Aliases to avoid** — lives in [/UBIQUITOUS_LANGUAGE.md](../../UBIQUITOUS_LANGUAGE.md). Copy edits to this file must conform.

---

## 1. The product, in one paragraph

**socratink** is a metacognitive learning tool. It teaches by **student generation**: the learner attempts a concept cold, receives targeted study, then re-drills the same concept after a deliberate spacing interval. The interface exists to support that loop and nothing else. There is no content browser, no completion checklist, no streak tracker — the **graph itself is the only profile that exists**, and graph truth changes only when learner-generated evidence is recorded.

The product's promise is small, specific, and load-bearing: **see what you can actually explain.**

---

## 2. The unifying metaphor — a dungeon of rooms

Every UX decision descends from a single mental model:

- The graph is a **dungeon map**.
- Each node is a **room**.
- The **cold attempt** is stepping through the door before you know what's inside.
- **Targeted study** is the room revealing itself *after* the attempt.
- The **spaced re-drill** is the room's boss fight.
- Traversal opens from recorded engagement evidence; mastery-gated progression waits for `solidified` evidence.

This metaphor is why the graph reads as **trustable**. A state change has to feel earned, not decorative. The reward layer is not a popup — it is the room itself changing shape.

---

## 3. The metacognitive happy path

The binding seven-screen onboarding into any concept. Every concept-facing surface descends from this arc.

```
Enter concept
  → 1. Concept Threshold        (global starting map; no graph mutation)
  → 2. Provisional Graph        (draft route as hypothesis)
  → 3. First Cold Attempt       (local; quotes the threshold; analogical fallback if signal is thin)
  → 4. Locked Study Silhouette  (purpose only — no content)
  → 5. Study Repair Artifact    (the hinge, the causal spine, one diagram)
  → 6. Interleaving Bridge      (2–3 nearby rooms + take a break)
  → 7. Repair History           (field journal of what was actually repaired)
  ↓
  Mutate graph truth only on solid spaced reconstruction.
```

### What each screen does — and refuses to do

**1. Concept Threshold — Door + Launch Pad (C-prime, 2026-05-07).** The door captures the concept name, optional source attach, and an optional learner goal when the input is phrased as intent. Source-less concepts pass through a **launch pad** that shows the preserved goal and captures the learner's threshold (rough whole-concept model) before any AI generation runs. The learner goal shapes relevance and prompt copy only; it is not learning evidence. See `docs/product/spec.md` for the current contract.

The launch pad replaces the previous in-form "Starting sketch" textarea. The threshold is no longer a field on the door; it is a dedicated post-commit surface. This change preserves the learner-seeded route contract: no graph or thesis is generated from the concept name alone.

*Prior implementation (pre-C-prime):* Threshold was captured as a two-textarea form on Ignition alongside the concept name. Copy distinguished it from the cold attempt: *"This is global context. The first room will ask one smaller question."*

**2. Provisional Graph / Gestalt Canvas.** A draft route, framed as a hypothesis. Legend is constrained to three words: *draft route · ready for first attempt · locked.* No mutation. When the learner opens the concept, the route may remain visible as a quiet vertical margin while the first local reconstruction surface is already inline. This margin is an advance organizer only: it shows phase cues and scope boundaries, not answer summaries or study material.

The Constellation sibling view is secondary orientation, not the primary work surface. Route stays the default reconstruction surface; Constellation may show position, availability, and training-derived state, but must not leak mechanisms, study content, source previews, or answer-shaped labels before reconstruction evidence.

**3. First Cold Attempt.** Narrower than the threshold. **Quotes or paraphrases the learner's threshold input** before asking one causal mechanism question inside the first node. The first writing surface is part of the concept canvas, not a separate mode the learner must enter. A recordable learner answer appends training evidence and derives `primed` or `needs repair`. Non-substantive input writes no attempt and asks for a micro-generation. **Analogical fallback** for low-signal learners: a familiar source analogy, learner predicts a causal relation *inside the analogy*, and no training evidence is recorded until something substantive lands. **The learner is never labeled zero-knowledge.**

**4. Locked Study Silhouette.** Pre-attempt. Title + one-line purpose + locked state + first-attempt CTA. **No explanation, no definitions, no solved diagram.** The absence of content is intentional — peeking at the room before entering would defeat the cold attempt.

**5. Study Repair Artifact.** Scoped to the attempted node only. Five parts in order: (a) the learner's exact words preserved, (b) **the hinge** — one specific correction, (c) **causal spine** — a compact arrow chain, (d) one clarifying diagram, (e) 1–2 connection cues. Never claims mastery. Target flow routes the primary CTA to *Choose next room* and the bridge; the current POC also exposes an inline repair retry after saved repair text, with no mastery or spacing credit.

**6. Interleaving Bridge.** Names *why* the learner is leaving the just-repaired node ("the repair is fresh, so re-drilling now would mostly test short-term echo"). Offers 2–3 nearby rooms with one-line purposes (no mechanism reveal). A non-punitive **"Take a short break instead"** is always present. Spacing is a valid choice. Interleaving is **never framed as reward or completion**. *Current runtime uses an 18-hour elapsed spacing placeholder; the 10-15 minute cognitively demanding buffer is future scheduler intent, not shipped enforcement.*

**7. Repair History.** A growing field journal — repaired misconceptions, recurring gaps, alternate explanations, learner-authored summaries. Accumulates from attempts, feedback, repair reps, and re-drills only — **never from reading**. Organized by the learner's voice, not the system's.

---

## 4. Three friction traps the flow exists to defeat

The shape of the path is a direct response to three failure modes. Designing against them is continuous, not one-shot.

| Trap | Symptom | Counter-design |
|---|---|---|
| **Generation fatigue** | Threshold and first cold attempt ask the same question; the learner answers twice. | Threshold is **global**; cold attempt is **local**. Different scope, different prompt, different surface. |
| **Zero-signal frustration** | A learner without vocabulary stares at a blank prompt and gives up. | The **analogical fallback** offers a familiar source domain; the learner predicts inside the analogy. The node stays locked until a substantive micro-generation lands. **Never labeled zero-knowledge.** |
| **Interleaving whiplash** | Repair → another cold attempt with no transition; the just-repaired material feels destabilized. | The **Interleaving Bridge** mediates every transition out of a repair. The bridge explains *why* the pivot helps and offers a break as a peer option. |

---

## 5. State model — what the system may claim, and when

The graph's vocabulary is small on purpose. Only these phrases appear as graph-state copy:

- **Allowed:** *suggested first · ready to reconstruct · primed for study · needs repair · solidified through spaced reconstruction.*
- **Forbidden:** *you know this · mastered (from graph generation) · completed (from reading) · advanced (from fluent prose).*

### State change rules — none of these may be violated

| Moment | What the learner sees | Allowed mutation |
|---|---|---|
| Threshold submitted | starting map captured | **none** |
| Provisional graph generated | suggested first | **none** |
| Local cold attempt — recordable | learner reconstruction acknowledged | training evidence appended; derives `primed` or `needs repair` |
| Local cold attempt — non-substantive | request for a micro-generation | **none** |
| Study revealed | repair artifact | study reveal recorded; no solidification |
| Interleaving bridge shown | next-choice set + break | **none** |
| Repair rep completed | practice history grows | **none** |
| Spaced re-drill — strong after spacing | solid spaced reconstruction recorded | derives `solidified` |
| Spaced re-drill — non-solid | "needs repair" | stores gaps; derives `needs repair` when warranted (warm, never red) |

The graph is **the only public profile**. Routing signals, source-dependence scores, causal-depth estimates exist internally — the learner **never sees their own schema label**. No beginner/intermediate/advanced tier, no "your learning style," no curriculum claim.

---

## 6. Session guardrails and bottleneck recovery

Cognitive effectiveness of retrieval practice is subject to severe diminishing returns.

- **Session Length**: No hard wall-clock cap in MVP, but duration should end at engagement, not exhaustion.
- **Retrieval Ceiling**: Maximum three successful retrievals per node per session. Beyond three, halt and schedule for later.
- **Node Cap**: Two to three nodes in active rotation is the recommended ceiling. Maximum 4 nodes per session.

### Bottleneck recovery paths

If a learner repeatedly lands on `needs repair` on a gating node, the product can deadlock. To prevent session abandonment without lowering the mastery bar:

- **Escalating Scaffold**: AI progressively breaks the mechanism into sub-steps across subsequent re-drills (e.g., reconstruct one piece at a time, or provide step 1 and ask for the link to step 2).
- **Study Revisit**: After a non-solid re-drill, reopen study with an *alternate* explanation or reorganized sequence anchored to their new prediction error.
- **Branch Escape**: For non-linear maps, allow entering a different branch's cold attempt while the blocked node stays `needs repair`.

---

## 7. AI drill prompt contract

AI is the scaffold, not the generator. The learner must be the primary generator of the target mechanism.

- **Boundary for the current MRP loop**: AI is used after learner
  reconstruction as a sparse grader / hinge extractor. The repair artifact
  renders the learner's exact words, the extracted hinge, and scoped study
  material; it must not become a tutor-chat transcript or present AI polish as
  evidence of learning.
- **Scaffold, never lecture**: During the cold attempt, ask an open question and listen. Do not pre-explain.
- **Zero-schema detection**: If absolute zero schema is detected (no relevant vocabulary), pivot to Load Reduction Instruction: provide basic pieces, ask for a micro-generation.
- **Sparse feedback**: AI responses during drill should be brief, pointed, and gap-identifying. If the AI talks more than the learner during a turn, the passive trap has been triggered.
- **Probe the gap**: If a response is substantive but incomplete, probe the specific gap instead of re-explaining the full mechanism.
- **No one-word answers**: During spaced re-drills on complex mechanisms, demand multi-step causal reconstruction (e.g., self-explanation or summarization).

---

## 8. Ethical engagement and endowed progress

If a mechanic relies on loss aversion, FOMO, or mechanisms that only work when the learner is unaware, it crosses into manipulation.

- **Endowed Progress through truth**: When entering a new cluster, visually illuminate prerequisite nodes that already carry `solidified` records. Frame the new territory as partially completed based on actual prior solid spaced reconstructions.
- **Anti-compulsion design**: End sessions at a point of engagement by enforcing guardrails. Stop the learner while wanting is still active, and explain the science transparently. *"Evidence recorded. Let spacing do its work while you're away."*
- **Roguelike dynamics**: The session is a "run." Permadeath means a node can stay `needs repair` until next time, not failed. Meta-progression is the knowledge graph recording effort. The mastery ceiling never lowers.

---

## 9. The crystal — the visual thesis

The core motif is a **dual-diamond crystal polygon** with a vertical axis. It is the same shape at three scales:

- **The brand mark** (favicon).
- **The product wordmark.**
- **Each tile on the isometric graph board.**

The crystal's appearance *is* the truthful projection of recorded evidence. It morphs across the live training states — no-evidence/unavailable (mauve, dim), `primed` (lavender mid-plane, faint glow), `needs repair` (warm, returnable), and `solidified` (success-green, crisp facets), with `fractured` reserved as a rare subdued danger glow. Color choice for `needs repair` is deliberate: **warm and return-worthy, never red, never punitive.** Struggle is honored, not hidden.

The graph board is **always isometric**, **always cream**. Never flat. Never a force-directed node-and-edge diagram. The isometric view enforces the dungeon-map reading and resists being mistaken for a content browser.

---

## 10. Copy voice — the attribution surface

The product has no human teacher to manage attributions in real time. The interface *is* the attribution manager. Every line either pushes the learner toward **adaptive attribution** ("I haven't built the model yet") or **maladaptive attribution** ("I'm not smart enough"). There is no neutral position.

### Posture
**Calm, precise, Socratic.** Reading room, not dashboard. Patient tutor, not coach app, not game.

### Rules
- Second person, singular. "You own the content." "You reconstruct from memory."
- Lowercase `socratink`, always — even sentence-initial.
- Lowercase state tokens: `primed`, `needs repair`, `solidified`; render no badge for no-evidence/null state.
- Title Case for section headings only.
- UPPERCASE with wide tracking only on eyebrow kickers — the lone exception.
- Plain, complete sentences. Periods, not telegraph style.
- Verbs over adjectives. The promise shows up as things the learner *does*: "Bring your material. Build a map. Record evidence."
- No exclamation marks. Ever.
- No emoji. Ever.
- No hype jargon — *revolutionary, AI-powered, supercharge, 10×, unlock, crush, game-changing.*
- Admit the state of the product honestly. *"Still testing. Still learning."* is load-bearing brand.

### Tone by surface

| Surface | Tone | Example |
|---|---|---|
| Marketing hero | Invitation, not pitch | "See what you can **actually explain.**" |
| Value strip | Plain declarative | "No fake state changes — the map updates when socratink records learner-generated evidence." |
| How it works | Imperative, low-volume | "Bring your material. Build a map. Record evidence." |
| Drill prompt | Sparse, gap-identifying | "Explain why node B matters in the system." |
| `primed` state | Quiet acknowledgment | "You've stepped inside. The real challenge is ahead." |
| `needs repair` state | Honored, not punitive | "Worth revisiting. The next gain is here." |
| `solidified` state | Earned, brief | "Solidified. Spaced reconstruction recorded." |
| Session cap | Warm, scientific | "Evidence recorded. Let spacing do its work while you're away." |
| Error / non-solid | Strategy, never ability | "The causal link between step 2 and step 3 needs a different angle." |

### What is forbidden in copy
- *Diagnostic · evaluate your current understanding.*
- *Beginner / intermediate / advanced.*
- *We found your misconceptions.*
- "You know this" from graph generation.
- "Completed" from reading.
- "Mastered" / "Advanced" from fluent prose.
- Scored language during the cold attempt — *quiz, test, exam, assessment, score.* Use *enter the room · what do you think this involves? · take your best guess.*
- Consolation copy on non-solid attempts. Replace "great try!" with specific, strategy-framed next-step language.
- Streaks, XP, combos, unlocks-as-reward, power-ups, level-ups, ranks.
- "Our AI." Say what the system does instead — *identifies what depends on what · prompts for elaboration · halts drilling at three successful retrievals.*

### Adjacent-surface vocabulary clash

Before locking copy that sits inside a frame with other copy — button + footnote, eyebrow + title, helper + label, modal title + body — explicitly scan the content words (verbs, nouns) of both strings for shared roots. If `attempt`, `commit`, `save`, `record`, `solidify`, `room`, `entry`, `sketch`, or any other project-vocabulary term appears in two adjacent strings with different referents, that is a bug class, not a stylistic concern.

Example — caught during the Paper Wave 1 button-rename round (2026-05-09): the candidate label `Commit attempt` for the launch-pad submit button sat directly above the footnote *"Study content stays locked until the cold attempt."* Same word, two referents, three inches apart. The persona caught it instantly: *"the footnote right below this button says the next phase is the cold attempt. If I click 'Commit attempt' here, I'm going to be confused about whether I just did the cold attempt or it's still coming."* Resolution: rename the button to `Save sketch` (names the artifact, not the act), leaving the footnote's `cold attempt` unambiguous.

The fastest test is the persona walkthrough: ask *"what does the reader think `X` refers to in each spot?"* If the two answers differ, rewrite the less-load-bearing string. This rule is sharper than usual for socratink because the ubiquitous language (`cold attempt`, `recorded`, `solidified`, `primed`, `needs repair`, `sketch`, `entry`) carries project-binding meaning that everyday-English will overwrite if a clash exists.

---

## 11. The trajectory bands (post-attempt only)

A reflective vocabulary — `spark → link → chain → clear → tetris` — surfaces *only* as post-attempt growth framing, always paired with interpretation: *"Your cold attempt was a spark. Your re-drill hit chain. Stronger reconstruction evidence is on record."* It is **never a live score** during an attempt. The bands describe trajectory, not standing.

---

## 12. Sensory grammar — how the surfaces feel

The aesthetic mirrors the work the product asks of its learners: **quiet, scholarly, crystalline.**

- **Page is cream paper, never white.** True white reads clinical; cream reads "reading room."
- **Text is ink, never true black.** Reduces glare; matches the warm page.
- **One violet accent per screen.** The crystalline warm violet is the only interactive color. Stack three of them and the screen has no foreground.
- **Shadows are violet-tinted, never gray.** Elevation reads as warm light, not ink smudge. Inset 1px top highlight on cards reads as a lit edge — that's the "paper" effect.
- **Backgrounds are never flat.** Subtle radial + linear gradients; ambient blooms in the corners at huge blur. Late-afternoon light through paper, not Instagram filter.
- **No hero photography.** The isometric crystal board is the one signature illustration.
- **No noise, grain, or film overlays.** Warmth comes from the gradient.
- **No left-border-accent cards.** Reads as AI-slop trope; clashes with the jeweled palette.

> **In-app exception (Antigravity theme).** The shipping in-app shell deliberately diverges from the cream-paper marketing surface: it is calmer, glassier, and tuned for repeated work inside the app rather than external persuasion. Marketing pages and external surfaces still follow the cream-paper rules verbatim. Technical token values, font exceptions, and file-level implementation details live in `docs/design/socratink-design-system.md` and `docs/design/brand-reference.md`.

### Motion
Drill surfaces are quiet. Motion should feel like attention moving across paper, not like an app performing for the learner. **Spring motion is reserved for `solidified`** — the one moment that earns celebration. Everything else should be brief, legible, and subordinate to the current cognitive target. No scroll-hijacking, no parallax, no autoplay video. Reduced-motion preferences are binding; implementation details live in the design-system doc.

### Audio
Material, not musical. Audio should read as contact with the surface: brush, breath, thud, cloth, settle. It is feedback for an action the learner just took, never ambience and never a notification layer. On by default, user-controllable in Settings, and respectful of reduced-motion/sensory restraint. The canonical helper names and synthesis details live in the design-system doc.

### Hover, press, focus
- **Hover** = the page lifts, it doesn't brighten.
- **Press** = the component admits it was touched without becoming louder.
- **Focus** = a soft violet ring. Never a thick blue outline; never nothing.
- **Disabled** = surface drops to nested, text to muted, shadow off.

### One active cognitive target
At any moment one thing is foregrounded; everything else dims to 0.5–0.6 opacity. Never more than three peers at equal prominence on a drill surface. Two to three visual hierarchy levels per screen — kicker → heading → body. If a fourth tier is needed, the screen has too many things.

### Silent surface — every visible element earns its keep

The default for any socratink UI is silence: a screen that says nothing it has not earned the right to say. Every visible element — eyebrow, helper line, emphasis treatment, decorative icon, branded vocabulary, progress indicator — must justify its presence against the question *"would the screen still work without this?"* If yes, cut it.

The earned elements are usually small in number: one title, one input surface, one commit button, and any boundary footnote that names a real system constraint (e.g., *"Study content stays locked until the cold attempt"* — earned because the system actually enforces it). Almost everything else is silent-surface debt.

Specifically reject:
- SaaS-CTA arrows (`→`) on commit buttons. The label already names the action.
- Progress hand-holding for short flows (`1 of 2`). The user clicked a labeled nav link to get here; orientation is sufficient.
- Helper lines that explain how the app works *in advance of the user needing to know.* Trust the user to discover the next step from the structure.
- Typographic emphasis (italic + color + underline) as a substitute for prose discipline. If a word is doing real work, the prose makes that obvious; if the prose doesn't, the typography is preaching.
- Brand-internal vocabulary as user-facing eyebrows (e.g., `IGNITION` on the New-concept screen). Internal labels stay internal.

This rule was hammered out during the Paper Wave 1 first-principles persona round (2026-05-09). The persona converged on the most-subtractive option for every single decision and named the category-level rule directly: *"strip out absolutely every piece of branded or conversational vocabulary so the interface goes completely silent."* All four subtractions shipped; the result reads as a "quiet, serious notebook" — the brand register the prior atmospheric design was failing.

The corollary discipline: when authoring a new surface, start from blank paper + a single title, then add only what the screen visibly fails without. This is harder than starting full and trimming — but the additive bias is exactly what produces silent-surface debt in the first place.

---

## 13. The MVP cut — what to build first

This is the binding prioritization. Build first:

- Door + Launch Pad *before* any study-like page.
- Concept name plus optional learner goal/source at the Door; any non-empty source-less Launch attempt on the Launch Pad.
- Internal routing signals (never learner-visible).
- Smallest-actionable-route copy.
- Local first cold attempt derived from the Launch attempt.
- Analogical cold-attempt fallback.
- Locked study silhouette before attempt.
- Attempt-scoped repair artifact after cold attempt.
- Interleaving bridge with 2–3 next-room choices plus a break option *before* another cold attempt.
- Training evidence writes to the browser-local training store; displayed state derives from `null | primed | needs repair | solidified`, with `solidified` still gated by the shipped 18-hour spacing interval.

Defer:

- Learner-visible schema profiles.
- Long-term curriculum claims.
- Cross-concept mastery summaries.
- Rich notebook features.

---

## 14. What socratink refuses to be

The product is defined as much by what it will not do. The following are hard exclusions, not preferences:

- **No streaks. No XP. No badges. No leaderboards. No achievement popups.** The reward is the crystal state change itself.
- **No content browser.** The graph is not a library; it is a record of evidence socratink has seen.
- **No completion checklist.** Reading does not advance state. Only generation and spaced reconstruction evidence do.
- **No "diagnostic" framing.** The threshold is a starting map, not an evaluation.
- **No mastery claims** from graph generation, from reading, or from fluent prose. Only spaced reconstruction can record `solidified`.
- **No learner-visible schema labels.** The system may infer; the learner never sees a tier.
- **No punitive surface for struggle.** `needs repair` is warm, return-worthy, honored.
- **No hype.** No exclamation marks, no superlatives, no "AI-powered" boilerplate.
- **No emoji.**
- **No stock photos, AI portraits, "student in library" hero imagery.**
- **No flat blue-to-purple gradients.** No clinical SaaS palette.
- **No scroll-hijacking, no heavy parallax, no autoplay video hero.**
- **No third accent color introduced ad-hoc.** Success is reserved for `solidified`; danger is reserved for the rare `fractured` glow, subdued.

---

## 15. The one-line summary

> **The graph proposes. The cold attempt creates something to repair. Study makes the repair inspectable. The spaced re-drill records the strongest evidence.**

Every surface in socratink is in service of that sentence. If a screen does not advance one of those four moves, it does not belong in the product.
