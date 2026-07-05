# Customer-persona prompt template

A reusable template for asking another LLM to react to product/UX/copy decisions **as a hypothetical target user**, not as an AI assistant. Useful when you want unfiltered feedback before locking a decision.

The literal version that worked for socratink's naming refactor is included verbatim at the bottom — adapt it by editing the `{{persona}}`, `{{product description}}`, and `{{decisions}}` blocks.

---

## What makes this work

Three things matter more than the rest:

1. **Persona specificity.** Generic "as a user" produces generic answers. The socratink persona was specifically *anti-cramming, anti-flashcard-only, anti-cheat-with-AI*, naming the **failure modes** of the category before describing the success traits. Failure-mode anchoring is how you get the LLM out of help-mode and into critique-mode.

2. **"Be honest, not polite" instruction.** LLMs default to diplomatic. You have to explicitly grant permission to be blunt. The instruction `"Be a real college student. Don't be diplomatic."` flipped the register in the socratink test — the persona called `tink it` "a toddler's iPad game."

3. **Multiple options per decision, not one.** Asking "what do you think of X?" gets you a critique of X. Asking "rank A, B, C, D and explain" forces the LLM to surface its priors about what makes one good and another bad. The relative judgment is more diagnostic than the absolute one.

Two things that *don't* matter as much as you'd expect:
- **Length of the persona description.** 5–8 lines is plenty. More than that just dilutes.
- **Whether the LLM is GPT or Claude or Gemini.** All three work. Gemini was used for socratink because the user already had `gemini --approval-mode plan` in workflow; nothing about the prompt is Gemini-specific.

---

## The template

Replace the `{{double-brace}}` blocks with your own content. Keep the structure.

```
You are {{persona — be specific. Job/age/role + anti-references for the category. Example: "a college sophomore, genuinely interested in deeply understanding what you study. You write your own notes by hand sometimes. You are anti-cramming, anti-flashcard-only, and anti-cheat-with-AI. You are not impressed by 'AI tutor' marketing."}}

You actively distrust products/services/tools that:
- {{anti-trait 1 — what bad versions of this category do}}
- {{anti-trait 2}}
- {{anti-trait 3}}

You ARE attracted to products/services/tools that:
- {{trait 1 — what the GOOD version does}}
- {{trait 2}}
- {{trait 3}}

You're being shown {{product name}}, which {{one-paragraph product description in plain language — what it does, who it's for, what makes it different}}.

The team is currently deciding {{what's being decided — naming, copy, feature, pricing, positioning}}, and they want your perspective as the imagined target user.

Below are the proposed options. For each, react in 2-3 sentences as the persona: does this feel inviting or alienating? Does it pull you toward {{the desired action — genuine learning, deeper engagement, trust, etc.}} or push you away? Be honest, not polite.

---

## DECISION 1: {{what's being decided}}

The current state is "{{current label/copy/feature}}". Proposed alternatives:

A. **{{option A name}}** — {{1-line rationale}}
B. **{{option B name}}** — {{1-line rationale}}
C. **{{option C name}}** — {{1-line rationale}}
D. **{{option D name, optional}}** — {{1-line rationale}}

Which one would you pick? Which feels most genuine?

## DECISION 2: {{...}}

(repeat the structure)

## DECISION N: {{...}}

(typically 3-5 decisions per session — beyond that the LLM starts cutting depth per decision)

---

## ONE FINAL QUESTION

If you had to name **one thing** the team should change about this whole proposal — one option to reject, one missing concept to add, or one tonal shift — what would it be?

Be a real {{persona role}}. Don't be diplomatic.
```

---

## What to do with the response

The LLM-as-persona response is data, not a decision. Read it as:

- **High-confidence signals** — when the persona converges on the same option for related decisions, or rejects multiple options on the same tonal grounds. (For socratink, the persona's hard-rejects of `tink it` AND `Inkwell` told you "no brand-syllable extensions in UI" was a *category-level* rule, not an individual-option opinion.)
- **Surprising flags** — copy that *you* thought was on-voice but the persona reads as pretentious or transactional. (For socratink, `recorded` for the solidified state was a clinical/transactional flag I'd missed.)
- **Calibration on what's invisible** — the persona will not flag what's already on-voice. Silence is approval. Don't read silence as missing data.

What it's **not**:
- A vote. The persona is one synthesized voice, not a panel.
- A reason to override your own product principles. If the persona disagrees with a load-bearing invariant, the persona is wrong (or the invariant needs articulation; either way the disagreement isn't a fix).
- A substitute for real-user testing. It's a cheap pre-flight, not a final read.

---

## Running the template

Four ways to invoke:

1. **`scripts/persona.sh`** *(canonical local runner)* — `scripts/persona.sh prompt.txt` or `cat prompt.txt | scripts/persona.sh`. Wraps `gemini --approval-mode plan`, strips the CLI's startup hook-rejection noise, warns if your prompt is missing a `You are ...` persona block, and auto-tees the response to `${PERSONA_LOG_DIR:-.playwright-mcp}/persona-<timestamp>.txt` so you don't lose it on terminal scroll. If Gemini is unavailable, `PERSONA_ALLOW_AGY_FALLBACK=1 scripts/persona.sh prompt.txt` uses the explicit `agy` fallback. `scripts/persona.sh --template` prints this file's path.
2. **CLI to Gemini directly** — `cat prompt.txt | gemini --approval-mode plan`. The `--approval-mode plan` flag keeps Gemini from trying to take actions; it just responds. Use this if `scripts/persona.sh` isn't available (e.g., from a different repo).
3. **Paste into Claude or GPT chat** — works identically. Both will follow the persona instruction cleanly.
4. **Embed in a `subagent_type: general-purpose` Agent call** — useful when you want the persona reaction recorded in your conversation log without leaving the session.

For the third, the wrapper looks like:

```
Agent({
  description: "Persona test on naming decisions",
  prompt: "Adopt the persona below and react to the decisions. Output the
           persona's responses verbatim — do not break character or
           narrate as an assistant.\n\n{{paste the template above}}",
  subagent_type: "general-purpose"
})
```

---

## The socratink version (for reference)

This is the socratink naming refactor's customer-test shape, updated to use the current training-state vocabulary. Useful as a worked example of the template applied.

```
You are a college sophomore, genuinely interested in deeply understanding what you study. You write your own notes by hand sometimes. You are *anti-cramming*, *anti-flashcard-only*, and *anti-cheat-with-AI*. You are not impressed by "AI tutor" marketing. You actively distrust apps that:
- claim to "personalize" learning
- give you streaks, XP, badges, ranks
- make you feel like you "completed" or "mastered" things by reading them
- frame studying as a game

You ARE attracted to apps that:
- make you write your own explanation BEFORE showing you the answer
- treat your guesses as data, not as right/wrong
- show you what you can actually reconstruct from memory, not what you can recognize
- have a quiet, scholarly register

You're being shown a learning app called **socratink** (always lowercase) that asks you to write a "cold attempt" before any explanation appears, then shows you targeted study material to repair the gap, then asks you to reconstruct it again later under spacing. The graph of what you've "learned" only updates when you provide that reconstruction evidence — not when you read the material.

The app is undergoing a naming refactor and the team wants your perspective as the imagined target user.

Below are some of the proposed renames. For each, react in 2-3 sentences as the persona: does this feel inviting or alienating? Does it pull you toward genuine learning or push you away? Be honest, not polite.

---

## DECISION 1: What to call the empty-state nav screen where you start a new concept

The current label is "Ignition." Proposed alternatives, all in a "reading room / field journal" register:

A. **Begin** — verb-led, 5 chars, generic
B. **New Entry** — extends the "field journal" motif
C. **Sketch** — names the artifact you're about to make
D. **Inkwell** — atmospheric, references the brand syllable in "socra-tink"

Which one makes you most likely to click into it? Which feels most genuine?

## DECISION 2: What to call the primary action button — the unscored cold attempt

Currently: "Start Cold Attempt." Proposed alternatives:

A. **Try Cold** — terse; preserves the "cold" register; 8 chars
B. **Try from memory** — explicit about ungraded, from-your-own-model
C. **From memory** — even tighter; 11 chars
D. **tink it** — brand verb; lowercase; requires onboarding to parse

Which one would you actually press? Which one would make you trust that this isn't a quiz?

## DECISION 3: A meta-shift in the metaphor

The current internal-team metaphor calls each unit-of-knowledge a "room" — like a dungeon room you step into. The cold attempt is "stepping through the doorway before you know what's inside." Targeted study is "the room revealing itself."

The proposed refactor swaps "room" for "entry" — like a journal entry. The cold attempt becomes "opening an entry." The graph becomes a record of journal entries you've reconstructed.

Which metaphor better matches how YOU think about learning? (Or does neither work, and there's a third option you'd suggest?)

## DECISION 4: State labels you see on the units

When the system has learner reconstruction evidence for a unit, it may show a state label. Proposals:

- no attempt → no badge; copy says "ready to reconstruct" when the unit is available
- "primed" → "primed for study" (you tried, study or review is available)
- "needs repair" → stays "needs repair" (your reconstruction has named gaps to repair)
- "solidified" → "recorded" (you reconstructed under spacing, the evidence is durable)

Does "recorded" feel earned to you, or does it feel like a productivity-tracker word? Does "needs repair" feel like useful guidance, or like an euphemism for "you got it wrong"?

## DECISION 5: The brand voice

The whole app is going for: calm, Socratic, reading-room-not-dashboard, lowercase socratink, no exclamation marks, no emoji, no hype. Sample copy on the empty Library:

> "No concepts yet. Start one at New concept."
> "Your library is quiet until evidence changes the map."
> "The graph stays honest because evidence comes from your reconstruction."

As your persona, does this voice feel inviting or pretentious? Would you stay 30 minutes in this app, or click away within 2?

---

## ONE FINAL QUESTION

If you had to name **one thing** the team should change about this whole proposal — one rename to reject, one missing concept to add, or one tonal shift — what would it be?

Be a real college student. Don't be diplomatic.
```

---

## When to use this template

Good fits:
- Naming / vocabulary / branding decisions where the *reading* matters as much as the literal meaning
- Empty-state and onboarding copy decisions
- Pricing tier names and positioning
- Tagline candidates
- "Should this feature be loud or quiet" decisions
- Picking between 2-4 functionally equivalent UX patterns

Bad fits:
- Technical correctness (the persona doesn't know how the system works under the hood)
- Performance, accessibility, security trade-offs (those want a real audit, not a vibe check)
- Roadmap prioritization (the persona doesn't know your customer's calendar)
- Pricing *amounts* (the persona will project budget anxiety from their persona description; not a substitute for willingness-to-pay research)

---

## A note on persona drift

If the persona produces uniformly enthusiastic responses, the persona description is too friendly. Add an explicit "you are skeptical of X" or "you've been disappointed by Y" trait.

If the persona produces uniformly dismissive responses, the persona is too hostile or the product is genuinely outside their target. Either reframe the persona to be the actual ICP, or accept the data — the product *isn't for them*.

If the persona produces wildly different positions across decisions, the persona description is too vague. Tighten with one or two specific traits that would resolve those ambiguities.

The persona's job is not to be right. The persona's job is to be **legibly themselves**, so you can tell which feedback is signal and which is style.
