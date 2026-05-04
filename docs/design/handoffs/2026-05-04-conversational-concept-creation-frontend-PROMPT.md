# Handoff prompt — Plan B (conversational concept creation frontend)

> Paste the block below into a fresh Claude Code (or equivalent) session in the socratink-app repo. The prompt is self-contained: it loads the binding docs, the required skills, the worktree, and the discipline.

---

```
You are picking up Plan B of three for socratink — the FRONTEND of the conversational
concept creation flow. Plan A (backend) shipped on 2026-05-03 and is on dev at commit
086e617. Plan C (DESIGN.md reconciliation + acceptance smokes) follows after this
plan lands.

PROJECT ROOT: /Users/jondev/dev/socratink/prod/socratink-app

YOUR WORK ORDER LIVES AT:
  docs/design/handoffs/2026-05-04-conversational-concept-creation-frontend.md

That document is the contract. Every chip, every CTA copy variant, every anti-
pattern, every acceptance criterion, every file-path-and-line-number is in there.
If you find yourself improvising a UI decision that isn't in the handoff or the
spec it references, STOP and ask before coding.

== STEP 1: LOAD THE TWO REQUIRED SKILLS (BOTH, IN ORDER) ==

  socratink-design   — palette, typography, crystal motif, copy voice
  impeccable         — frontend-quality discipline; absolute bans

After loading both, print this preflight verbatim:

  IMPECCABLE_PREFLIGHT: context=pass product=pass shape=pass image_gate=skipped:spec-locked mutation=open

Both skills MUST load before any code change. Missing skill load = release-blocker.

== STEP 2: READ THE BINDING DOCS, IN THIS ORDER ==

  1. docs/design/handoffs/2026-05-04-conversational-concept-creation-frontend.md
     (your work order — read END TO END before anything else)
  2. docs/superpowers/specs/2026-05-02-conversational-concept-creation-design.md
     (the design spec — §2 four-line invariant + principles 1-7 are non-negotiable)
  3. PRODUCT.md
     (calm/precise/Socratic personality + anti-references list)
  4. DESIGN.md sections §3 (happy path), §10 (copy voice), §12 (sensory grammar)
     (NOTE: DESIGN.md §3 still describes the form-based threshold; the spec
      supersedes it. Plan C reconciles DESIGN.md — out of scope for you.)
  5. UBIQUITOUS_LANGUAGE.md — Content Intake section
     (Threshold chat, Starting sketch, Source-less generation, Grounding context)
  6. docs/design/socratink-design-system.md
     (the deliverables checklist at the bottom is your acceptance gate)

Open .superpowers/brainstorm/49698-1777699155/content/locked-design.html in a
browser to see the canonical visual reference for the summary card.

== STEP 3: SET UP THE WORKTREE ==

  git worktree add .worktrees/concept-create-frontend -b feat/concept-create-frontend dev
  cd .worktrees/concept-create-frontend
  bash scripts/bootstrap-python.sh   # for the parity-test toolchain

The post-checkout hook auto-links .env and .env.local. Verify clean baseline:
  . .venv/bin/activate && python -m pytest tests/ --ignore=tests/e2e -q
You should see all current tests pass (the count after Plan A landed was 518; the
exact number now is whatever dev's tip provides).

== STEP 4: WRITE A PLAN ==

This surface is multi-component (chat state machine + summary card + chip edit +
source panel + JS port of is_substantive_sketch + frontend telemetry). Write a
plan first; do NOT improvise. Use the writing-plans skill:

  Save plan to: docs/superpowers/plans/2026-05-XX-conversational-concept-creation-frontend.md
  Mirror Plan A's batched structure (one batch per coherent surface, TDD per
  task, commit at end of each batch).

Get user approval on the plan before executing.

== STEP 5: EXECUTE VIA SUBAGENT-DRIVEN DEVELOPMENT ==

Use the subagent-driven-development skill. One implementer subagent per batch,
followed by a code-quality reviewer subagent. After all batches: cross-cutting
final review. Then finishing-a-development-branch.

Recommended batching (mirrors Plan A's "1+B" pacing):
  B1: JS port of is_substantive_sketch + parity-fixture test (against
      tests/fixtures/sketch_validation_parity.json — release-blocker contract)
  B2: Chat state machine (turn 1 → turn 2 → fallback → exit) — vanilla JS,
      no chat-bubble vibe, no avatars, no typing dots
  B3: Summary card + three chips + chip-edit interactions
  B4: Source-material panel (reuse existing Text/URL/File tab markup)
  B5: State-dependent CTA + thin-sketch footer
  B6: Frontend telemetry events (per spec §5.4)
  B7: Remove the deleted form HTML + CSS (per handoff "Removed surfaces")
  B8: Visual smoke (manual screenshots — dark + light mode)

== HARD CONSTRAINTS (from spec + handoff anti-pattern list) ==

DO NOT:
- Build chat bubbles with avatars / "AI" labels / colored speaker names
- Add typing indicators / thinking dots / animated ellipses
- Generate or display affirming copy ("Great start!", "Got it,", "Interesting,")
- Use emoji ANYWHERE (headers, chips, errors, success states — anywhere)
- Use exclamation marks in any UI copy
- Apply background-clip:text gradients
- Add glass-morphism beyond the existing card pattern
- Add side-stripe colored borders > 1px on chips
- Add a second CTA at the bottom of the summary card
- Add a "tell me more" / "ask another question" affordance to the chat
- Build persistent chat history accessible from anywhere
- Auto-derive sketch text on the learner's behalf
- Change the verbatim spec copy: "A few words about how you think it works
  will give socratink something to draft from. Or attach source material —
  either path opens the build."
- Lower MIN_SUBSTANTIVE_TOKENS from 8 in the JS port (the parity fixture is
  the contract; the constant is locked)
- Touch the backend (server-side validation is the authority; frontend trusts
  the 422 response and renders the server's `message` field)
- Add new npm dependencies (use stdlib JS regex with the /u flag)
- Bypass the spec's verbatim copy by paraphrasing for "flow"

DO:
- Render AI questions as text on the page (no chat bubbles)
- Use the existing modal shell (.creation-dialog-* classes) — don't rebuild
- Use the existing source-material tab markup + 2026-05-01 redesigned tab
  styles already in components.css
- Hardcode v1 chat copy verbatim from the handoff (turn 2 + fallback) and
  TODO the wiring to a real /api/threshold-chat-turn endpoint
- Ship the JS port of is_substantive_sketch with the JS PORT NOTE from the
  Python module's docstring as your spec — especially the /[^\p{L}\p{N}_\s]/gu
  regex and /u flag on _REPEATED_CHAR_RE
- Run the parity-fixture test (28+ entries) in CI; failure is a release-blocker
- Emit telemetry events with origin:'client' so dashboards can detect drift
  against the backend's origin:'server' events
- Take dark-mode + light-mode screenshots for the PR description (5 angles
  per the handoff acceptance criterion #9)

== ACCEPTANCE CRITERIA (12 items in the handoff §"Acceptance criteria") ==

Every one must verify before merge. Read them now. The release-blocker subset:
  - JS substantiveness parity (#7)
  - 2-turn chat hard stop (#4)
  - Single-violet anchor at rest (#5)
  - Substantiveness validation works (CTA disabled + footer when thin sketch
    + no source) (#6)
  - AI voice review against the threshold-chat backend prompt (#10)

== SURFACE FAILURES IMMEDIATELY ==

If during implementation you discover the spec is wrong, the handoff is wrong,
or a binding doc contradicts itself, STOP and surface to the user. Do not
silently choose. Examples:
  - The handoff says "use the existing source-material tab markup" but you
    find the tabs were deleted — STOP.
  - The parity fixture has an entry your JS heuristic can't match without
    lowering the threshold — STOP.
  - You discover an XSS-shaped issue in how chip values are interpolated
    into HTML — STOP and harden, do not silently ship.

== WHAT BETTER-THAN-CODEX LOOKS LIKE ==

The handoff document specifically calls out the failure modes LLM coding agents
hit on frontend work. Read its closing section ("What 'better than codex could
ever do' looks like"). When in doubt, re-read the spec, re-read the handoff,
and ask the user. The cost of one clarifying question is much lower than the
cost of a vibe-coded chat surface that has to be torn out.

START NOW: load the two skills, state the preflight, then read the handoff doc.
```

---

## Notes for the human pasting this prompt

- **Where the executor lives** — this prompt assumes a fresh Claude Code (or codex / cursor) session opened in the socratink-app repo. Path constants are absolute; portable across agents.
- **What this prompt does NOT do** — it doesn't AUTO-execute. It enforces preflight discipline + reading order + planning step. The executor still has agency at every step (write the plan, get your approval, then execute).
- **If pasting into a non-Claude-Code agent** — strip the skill-loading lines (`socratink-design`, `impeccable`) since other harnesses don't have those exact skill names. Replace with the equivalent: "read these docs as binding context: [list]". The discipline still holds; only the loading mechanism differs.
- **Permission to deviate from the prompt** — none. The prompt itself is the contract. If it's wrong, fix this prompt file (and the handoff) before re-pasting.
