# Explore-Compress

A session-branching pattern for answering questions that require free iteration without polluting the primary thread.

Also known as: **summary-and-handoff** (Anthropic), **context compression** (LangChain Deep Agents).

## Trigger

You are mid-session on a design, grilling, or architecture question and hit a fork where answering it requires prototyping, copy variants, or free-form exploration — but you don't want the iteration noise to overwrite the primary thread's context.

## Goal

Diverge into free exploration, reach resolution, compress the result to signal only, and merge the signal back into the primary session via a structured handoff prompt. The prototype or artifact is retained; the iteration churn is not.

## Inputs To Inspect

- the specific question that sent you into exploration (must be nameable before diverging)
- the primary session type (design grilling, architecture review, copy decision, etc.)
- the best exploration vehicle: code prototype, copy variants, conversation iteration
- what "done" looks like for the question: a preference, a verdict, a decision, a constraint discovered

## Risk Classification

- `safe`: diverging, iterating freely, compressing, resuming
- `confirm`: deciding what the compressed answer carries back vs. drops
- `hard-confirm`: not applicable — this workflow does not touch production surfaces

## Recommended Route

```
1. Name the fork
   State the specific question before diverging.
   If you can't name it, you're not at a real fork yet.

2. Diverge
   Enter free-iteration mode. Burn tokens without ceremony.
   Follow 03-prototyping.md rules if the exploration vehicle is a code prototype.

3. Reach resolution
   Know when you have an answer, not just progress.
   Timebox if the exploration keeps expanding.

4. Compress  [prompt-based — works in any agent]
   Send this to the agent:

     "Summarize this exploration phase:
      - Question we were answering: [X]
      - Answer reached: [decision or finding]
      - Key artifacts to retain: [file paths, notes, prototype location]
      Signal only — no recap of failed variants or intermediate steps."

5. Merge  [prompt-based — works in any agent]
   Start a new message:

     "Continue [primary session] from [fork point].
      Answer to [question]: [paste compressed summary]."

6. Resume
   The primary session continues from the fork point with the compressed answer in hand.
   Retain the artifact; discard the iteration noise.
```

## Required Confirmation

- The compression prompt must name the specific question — not "here's what we tried"
- The primary session resumes from the fork point, not from after the exploration
- Iteration-phase churn (failed variants, intermediate states) must not leak into the resumed thread

## Verification

- The named question from step 1 has a clear answer in the compressed summary
- The primary session continues coherently from the fork point
- No exploration noise in the resumed thread

## Stop Rules

- Stop if you cannot name the specific question before diverging
- Stop if exploration keeps expanding without converging — timebox or reclassify the task
- Stop if the summary is too long to carry back without re-injecting all the noise

## Artifact Destination

- Compressed summary: carried into primary session thread (no file)
- Prototype artifact: governed by `03-prototyping.md` (throwaway vs. promote decision)
- Workflow truth: this file

## Tool Optimizations

Steps 4–5 above are agent-agnostic prompt patterns. Tool-specific shortcuts exist but are optional:

### Claude Code

`/rewind` to the fork point → select "summarize" → prompt: *"summarize what we learned about [X]"*

This replaces the manual compress + merge prompts and also prunes iteration noise from the active context window — the cleanest implementation available.

### Other agents (Gemini, Codex, Cursor, etc.)

Use the prompt pattern in steps 4–5 verbatim. No equivalent to `/rewind`; the iteration noise stays in context but the signal is carried forward cleanly via the handoff prompt.
