# Handoff — Conversational concept creation FRONTEND (Plan B)

**Date drafted:** 2026-05-04
**Status:** Ready for pickup. Backend (Plan A) is on `dev` at `086e617`.
**Drafted by:** Claude Opus 4.7 (1M context), in conversation with jon-devlapaz
**Supersedes:** `docs/design/handoffs/2026-05-01-new-concept-modal-redesign.md` (form-polish handoff). The form is being deleted, not polished.

## Required skills (load BOTH, in order, before touching any code)

1. **`socratink-design`** — loads `docs/design/socratink-design-system.md`, `docs/design/brand-reference.md`, `docs/design/colors_and_type.css`. Required for cream/ink/violet palette, Geom + Inter type, crystal motif, calm Socratic copy voice, single-violet-accent rule. Without this, the output looks like a generic SaaS chat.

2. **`impeccable`** — loads frontend-quality discipline: shape brief, register identification, the absolute bans (no gradient text, no glass-morphism default, no side-stripe borders, no chat-bubble vibe, no AI-slop affirmations). Without this, the chat reads like ChatGPT.

**Both must be loaded before code changes.** A missing skill load is a release-blocker. After loading, the executing agent must state its preflight:

```
IMPECCABLE_PREFLIGHT: context=pass product=pass shape=pass image_gate=skipped:spec-locked mutation=open
```

Shape is `pass` because the design spec at `docs/superpowers/specs/2026-05-02-conversational-concept-creation-design.md` (commits `43a3bf2` + `f584918`) is the locked, user-approved shape brief. Image gate is `skipped:spec-locked` because the `.superpowers/brainstorm/49698-1777699155/content/locked-design.html` mockup already shows the canonical surface — no new image probes needed unless a sub-component diverges from it.

## What this handoff is

The backend for source-optional concept creation shipped in Plan A. The frontend is still a form (`buildContentInputUI` in `public/js/app.js:684`). This handoff is the work order to replace that form with the conversational chat → summary card flow specified in the design spec.

This is Plan B of three:
- **Plan A (DONE)** — backend dispatch, source-less generation, LC enrichment, server validation, telemetry. On dev, 12 commits, 88 new tests, live Gemini smoke 3/3 PASS.
- **Plan B (THIS)** — frontend chat + summary card + integration with the new `/api/extract` payload + frontend telemetry + JS port of `is_substantive_sketch`.
- **Plan C (after B)** — `DESIGN.md` §3 Screen 1 update (binding doc), acceptance smokes #6-#10 from spec §8, screenshot evidence for the merge PR.

## Binding documents (must respect — copy/visual that conflicts is a regression)

Read these in this order **before** designing or coding:

1. `docs/superpowers/specs/2026-05-02-conversational-concept-creation-design.md` — the spec. The four-line invariant (§2 callout) and principles 1-7 are non-negotiable.
2. `PRODUCT.md` — calm/precise/Socratic brand personality, anti-references list (no quiz-app vibe, no generic AI tutor branding, no diagnostic dashboard, no gamified surface).
3. `DESIGN.md` — §3 Screen 1 (Concept Threshold spec — currently still says "form-style", but the spec supersedes; Plan C will reconcile DESIGN.md), §10 Copy voice (UPPERCASE eyebrows only, lowercase `socratink`, no exclamation marks, no consolation copy), §12 Sensory grammar (cream paper, ink text, **one violet accent at rest**, violet-tinted shadows, no left-stripe accents).
4. `UBIQUITOUS_LANGUAGE.md` Content Intake section — **Threshold chat**, **Starting sketch**, **Source-less generation**, **Grounding context**, plus existing terms.
5. `docs/design/socratink-design-system.md` — palette tokens, typography tokens, motion easing, the deliverables checklist at the bottom.

If any chosen UI behavior conflicts with these, the docs win. If a real product reason requires departing from a doc, update the doc as part of this PR (and mention in the PR body).

## What is in scope for Plan B

### 1. Frontend: replace the `showNameField` branch of `buildContentInputUI`

**File:** `public/js/app.js`
**Function:** `buildContentInputUI(container, { onSubmit, onCancel, showNameField, showClipboard })` at line 684.

The function has two branches today:
- `showNameField === true` → the in-modal "Start a concept" form (full creation flow).
- `showNameField === false` → an inline overlay extract path (used elsewhere). **OUT OF SCOPE — leave intact.**

You are replacing the `showNameField` branch's HTML template + state machine + submit logic with the conversational two-stage flow.

#### Stage A — Threshold chat (ignition)

State machine per spec §3.1, pattern E:

```
chat:turn-1 → AI question rendered → learner replies → chat:turn-2 → AI probe rendered → learner replies
  ├── substantive → exit to summary-card stage
  └── thin       → chat:fallback (analogical scaffold) → learner replies → exit to summary-card stage
```

**Hard bound: at most 3 AI turns and 3 learner replies, then exit. No way to re-open the chat once the summary card appears.**

Visual posture (DESIGN.md §12 + impeccable):
- The AI's question reads as text on the page, **not** as a chat bubble with avatar.
- No "AI" label, no name, no typing indicator, no thinking dots.
- The composer is a single textarea with a calm submit button. No send-on-enter without explicit support; learners may want newlines in their reply.
- A small one-line breadcrumb above shows the eyebrow `NEW CONCEPT` (lavender, UPPERCASE, `--tracking-kicker`) and the title `Start a concept`. Both already in `creation-dialog-shell` markup; reuse that header.
- Composer respects `prefers-reduced-motion: reduce`. No fade-in animation on AI text by default; if added, ≤140ms duration, `var(--ease-standard)`, gated by the media query.

**Turn 1 copy is fixed (from spec §3.1):**

> *What do you want to understand?*

**Turn 2 copy** is shaped by the backend's threshold-chat system prompt (already shipped at `app_prompts/threshold-chat-system-v1.txt`). The frontend does NOT hardcode turn 2 — it asks the backend (or a small thin wrapper) for the next AI turn given the previous reply. **For the first cut**, you may hardcode turn 2's copy as `"Sketch what you think it does — rough is fine. What parts come to mind?"` — this matches the prompt's example shape verbatim and avoids needing a new chat-turn endpoint right now. Document the hardcode and file as a Plan B follow-up to wire to a real `/api/threshold-chat-turn` endpoint when the team is ready.

**Analogical fallback** — the spec calls for a context-aware analogy when turn-2 reply is thin. Same simplification: hardcode a generic-but-honest fallback for v1: `"Try this: think of something familiar that takes inputs and produces outputs. What inputs does this concept take, and what does it produce?"` — this is concept-derived in spirit (it leans on the input-output frame which most causal concepts share) without requiring a backend round-trip. Concept-derived analogy generation goes to the same Plan B follow-up.

#### Stage B — Summary card (the handoff)

Layout P2 from the brainstorm (per spec §3.2). Three chips, one CTA.

Render (visual structure — match the mockup at `.superpowers/brainstorm/49698-1777699155/content/locked-design.html`):

```
[NEW CONCEPT]                                                       [×]
Start a concept

↑ chat (collapsed): "Photosynthesis" · sketch captured

STARTING MAP

CONCEPT                                              [edit]
Photosynthesis

YOUR SKETCH                                          [edit]
Plants take in light and make sugar from water and CO2…

SOURCE MATERIAL                                      [Add source]
None added — build will start from your model only

[Build from my starting map]
Study content stays locked until the cold attempt.
```

**Chip vocabulary (binding):**

| Chip | Source of value | Action affordance | Empty state |
|---|---|---|---|
| Concept | AI extracts canonical name from chat replies (Plan B may default to literal turn-1 reply for v1) | `edit` → swap chip body to `<input>`, save on blur | n/a (always populated, even if just literal turn-1 text) |
| Your sketch | Concatenated turn-2 + fallback replies, verbatim | `edit` → swap to `<textarea>`, save on blur | n/a (always populated) |
| Source material | None at first | `Add source` → expand inline source-material panel (Text / URL / File tabs) | *"None added — build will start from your model only"* (italic, muted, dashed border) |

**Edit interaction details:**
- Click `edit` on a chip → chip body becomes the matching input element with the current value populated.
- Save on blur AND on Enter (single-line inputs only — Concept). Sketch chip uses textarea, save on blur or Cmd+Enter.
- Cancel: Escape reverts to prior value, exits edit mode.
- No explicit per-chip save button. The chip is the unit; one extra interactive layer is too many.

**Source-material panel (when expanded):**
- Reuses today's existing `Text | URL | File` tab structure from the form. The tab styles already exist in `components.css` (`.creation-source-tabs .overlay-tab` with the redesigned non-violet active state from the 2026-05-01 polish — keep that).
- When attached, the chip transitions to `replace` action with an attached descriptor: `3,421 chars from a Wikipedia article` (URL), `notes.md · 2,108 chars` (file), `2,640 chars pasted` (text).

**State-dependent CTA copy** (per spec §3.2 truth table):

| Source attached? | Sketch substantive? | CTA copy | CTA enabled? |
|---|---|---|---|
| No | Yes | `Build from my starting map` | ✅ |
| Yes | Yes | `Build from my map and source` | ✅ |
| Yes | No | `Build from source` | ✅ |
| No | No | `Build from my starting map` (visually disabled) | ❌ — see footer |

**Disabled CTA + thin-sketch footer copy** (when `source=null` and `is_substantive_sketch(sketch) === false`):

Below the sketch chip, render a strategy-framed muted footer:
> *A few words about how you think it works will give socratink something to draft from. Or attach source material — either path opens the build.*

This is from spec §3.2 verbatim. Do NOT paraphrase. Do NOT add an emoji. Do NOT use consolation framing.

**Footer (always present, unchanged from existing modal):**
> Study content stays locked until the cold attempt.

#### Stage C — Submit + dispatch

Submit constructs the new payload shape:

```js
{
  name: <concept chip value>,
  starting_sketch: <sketch chip value>,
  source: null  // or { type: 'text'|'url'|'file', text: '...', url: '...', filename: '...' }
}
```

POST to `/api/extract`. Backend handles dispatch + validation + LC enrichment + telemetry + generation. On 200, render the resulting `provisional_map` exactly as today's flow does (existing graph-render code path, unchanged). On 422 with `error: thin_sketch_no_source`, surface the response's `message` field in the sketch-chip footer (overrides the default footer copy). On 422 with `error: missing_concept`, focus the concept chip + show the response's `message` near it. On other errors, fall through to today's existing error-banner code.

**Critical: don't re-do the validation client-side and skip the server call.** The client-side gate is a UX optimization; the server is the authority. Frontend's substantiveness check exists to disable the CTA preemptively, but if a learner somehow submits anyway (cached client, edge case), the server's 422 with the strategy-framed message is the safety net. Render the server's `message` if it differs from what the client showed.

### 2. Shared `is_substantive_sketch` JS port (the parity contract)

**File to create:** `public/js/sketch-validation.js` (or alongside the existing `public/js/api-client.js` etc.).

**Contract:** byte-for-byte parity with the Python implementation at `models/sketch_validation.py`. Verified against the shared parity fixture at `tests/fixtures/sketch_validation_parity.json` (28 entries — Python ASCII set + 3 unicode entries: Spanish, French, mixed-script).

**Source of truth for the heuristic:** read the Python module's docstring (especially the `JS PORT NOTE` block at lines 22-40) before writing. It calls out the exact regex semantics required:

```js
// CORRECT — Unicode-aware, matches Python's default \w semantics
text.replace(/[^\p{L}\p{N}_\s]/gu, ' ')

// WRONG — ASCII-only, will silently shred non-English learner sketches
text.replace(/[^\w\s]/g, ' ')
```

The `_REPEATED_CHAR_RE` pattern also needs the `/u` flag.

**Constants to mirror exactly:**
- `MIN_SUBSTANTIVE_TOKENS = 8` (do NOT lower; if a unit test forces this lower, the test sketch is wrong, not the constant)
- `_DONT_KNOW_PATTERNS = ['idk', 'i dont know', "i don't know", 'no idea', 'no clue', 'dunno', 'not sure']`
- `_STOPWORDS` = the same small frozenset (a, an, the, and, or, but, if, of, for, in, on, at, to, from, by, with, as, is, are, was, were, be, been, being, do, does, did, has, have, had, this, that, these, those, it, its)
- Repeated-char threshold: `^(.)\1{4,}$` with `/u` flag

**Test:** create `tests/test_frontend_sketch_validation.{js|html}` (project's existing `tests/test_frontend_syntax.py` suggests Python-based JS testing — follow that pattern). The test must:
1. Load `tests/fixtures/sketch_validation_parity.json`
2. For each entry: assert `is_substantive_sketch(entry.text) === entry.expected_substantive`
3. Run as part of `bash scripts/qa-smoke.sh` so a parity divergence is caught before merge.

**Parity divergence is a release-blocker.** A single fixture entry that disagrees between Python and JS means a thin-sketch attack vector in production. Do not adjust the fixture to mask a JS heuristic gap — adjust the JS until it conforms.

### 3. Frontend telemetry events (per spec §5.4)

Wire these via the existing logging / telemetry helper (find `bus.js` or whatever the frontend event bus is called; if there isn't a unified telemetry path yet, create the smallest helper that posts to a single backend endpoint or `console.info` and TODO the wiring for production):

- `concept_create.chat.turn_started` — `{turn: 1|2|fallback, has_prior_reply: bool}`
- `concept_create.chat.turn_replied` — `{turn, reply_len, used_fallback: bool}`
- `concept_create.summary.shown` — `{has_concept, has_sketch, sketch_len}`
- `concept_create.summary.edited` — `{chip: 'concept'|'sketch'|'source'}`
- `concept_create.source.added` — `{type: 'text'|'url'|'file'}`
- `concept_create.build_clicked` — `{has_source, has_sketch}`
- `concept_create.build_blocked` — `{reason: 'missing_concept'|'thin_sketch_no_source', origin: 'client'}`

The `origin: 'client'` flag matches the backend's `origin: 'server'` so the dashboards can detect client/server validation drift. In a healthy state, all blocks should fire as `client`; server-side blocks indicate a client bug, an old cached client, or a bypass attempt — all worth knowing.

### 4. Removed surfaces (DELETE — do not just hide)

From `public/js/app.js`:
- The entire `showNameField === true` HTML template (the form: name input, threshold textarea, fuzzy area toggle/panel/input, source-tabs row at form level).
- All event handlers tied to the deleted elements (`creation-name-input` listeners, `creation-threshold-input` listeners, fuzzy toggle handler).
- The placeholder rotation logic (`PLACEHOLDERS` array, `phTimer`) — the chat composer doesn't rotate placeholders.
- The `NAME_PLACEHOLDERS` array + rotation — the AI's turn 1 question replaces it.

From `public/css/components.css`:
- `.creation-name-input` and its focus / placeholder rules.
- `.creation-threshold`, `.creation-threshold-head`, `.creation-threshold-copy`, `.creation-threshold-input`.
- `.creation-fuzzy-toggle`, `.creation-fuzzy-row`, `.creation-fuzzy-hint`, `.creation-fuzzy-panel`, `.creation-fuzzy-input`.
- `.creation-source-meta`, `.creation-source-copy`.
- `.creation-source-header`.
- `.creation-validation` (replaced by chip-footer pattern).

**KEEP from today's CSS** (still in use by the new design):
- `.creation-dialog`, `.creation-dialog-scrim`, `.creation-dialog-shell`, `.creation-dialog-header`, `.creation-dialog-kicker`, `.creation-dialog-close`, `.creation-dialog-title`, `.creation-dialog-meta` — modal shell.
- `.creation-source-tabs .overlay-tab` and `.creation-source-tabs .overlay-tab.active` — tab styles, redesigned in 2026-05-01 polish.
- `.creation-cancel`, `.creation-submit` — button styles (CTA copy changes per state but classes unchanged).
- `.paste-clipboard-btn` and the `.paste-actions` row — used inside the source-material panel when expanded.

**Add:**
- `.creation-chat`, `.creation-chat-question`, `.creation-chat-composer`, `.creation-chat-breadcrumb` — chat surface.
- `.creation-summary`, `.creation-chip`, `.creation-chip-card`, `.creation-chip-empty`, `.creation-chip-label-row`, `.creation-chip-label`, `.creation-chip-action`, `.creation-chip-value` — summary card chips.
- `.creation-build-cta` — state-dependent CTA, swaps copy + enabled state. Inherits `--primary-fill` (single hard-violet element at rest).

## Anti-patterns to reject (impeccable + socratink, in priority order)

These are match-and-refuse. If you find yourself writing one, rewrite the element.

1. **Chat bubbles with avatars / "AI" label / colored speaker name.** Reads as ChatGPT for studying — exact thing spec principle saved as `feedback_chat_as_ignition.md` rejects.
2. **Typing indicators / "thinking…" dots / animated ellipses on AI turns.** Performative. The AI is not pretending to think; it's a tutor presenting a question.
3. **Affirming response from AI between turns** (`"Great start!"`, `"Got it!"`, `"That's interesting,"`). The backend prompt forbids these; the frontend must not paste them in either if it ever generates a synthetic acknowledgment.
4. **Emoji anywhere.** Headers, chips, errors, success states. Spec is absolute.
5. **Exclamation marks in any UI copy.** Spec is absolute.
6. **Gradient text.** `background-clip: text` with a gradient fill. Use solid `--ink-900`. Emphasis via weight or size only.
7. **Glass-morphism on the chat surface or chips.** Heavy `backdrop-filter` blur, semi-transparent layers stacked. Cards already use `backdrop-filter: blur(18px)` — that's the existing pattern; don't add a second layer of blur.
8. **Side-stripe borders on chips** (left or right colored border > 1px as decorative accent). Use full borders (`var(--border-subtle)`) only.
9. **Two CTAs at the bottom of the summary card** (e.g., "Build" + "Save draft"). One cognitive target per screen.
10. **A "tell me more" / "ask another question" affordance on the chat.** Hard cap is 3 AI turns. No retry, no continuation.
11. **Persistent chat history accessible from anywhere.** The chat exits cleanly. The captured sketch is the only artifact.
12. **Auto-derived sketch text** ("I'll fill in 'plants need light' for you"). The system never substitutes its own model for the learner's. This is principle #7 in the spec, repeated here because it's the failure mode that would silently break the product's promise.
13. **Templated kitchen analogy used regardless of concept.** When the analogical fallback is wired to the backend (Plan B follow-up), the analogy must be derived from the concept. The hardcoded v1 fallback ("inputs and outputs") is generic enough not to mislead but specific enough to scaffold; do NOT replace it with "imagine a kitchen…" for non-cooking concepts.
14. **Passing a thin `idk` sketch to the server expecting it to silently auto-fill.** Server returns 422; frontend renders the strategy-framed footer. Do not wrap the 422 in a generic toast or hide it from the learner.

## Acceptance criteria (release-blockers — each must verify before merge)

1. A learner can complete the flow end-to-end with **no source material** attached, and the resulting graph renders with the existing Provisional Graph treatment.
2. A learner can complete the flow end-to-end with source material (text / URL / file) attached, and the source-attached behavior is unchanged from today.
3. With LC unreachable (network blocked, key removed, host down), the source-less flow still completes within normal latency budget. (Backend handles this; frontend just trusts the response.)
4. The 2-turn chat is a hard stop. There is no UI affordance to add a third turn or reopen the chat once the summary card appears.
5. The summary card respects "one violet accent per screen": the build CTA is the only hard-`--primary-fill` element at rest. Eyebrow stays lavender (`--accent-secondary`) — that's secondary, not primary.
6. Substantiveness validation works end-to-end: enter `idk` as the sketch with no source attached → CTA disabled with the strategy-framed footer line. Edit sketch substantively OR attach source → CTA re-enables.
7. JS `is_substantive_sketch` passes ALL 28+ parity-fixture entries against the shared `tests/fixtures/sketch_validation_parity.json`. Any divergence is a release-blocker.
8. Frontend telemetry events fire at the right times with the spec'd `extra={...}` field shapes (see §5.4 list above). Verify with browser devtools or a small inline assertion in dev mode.
9. Visual smoke: dark-mode + light-mode screenshots of (a) chat turn 1, (b) chat turn 2, (c) summary card with no source, (d) summary card with source attached, (e) summary card with thin sketch + no source (CTA disabled with footer copy). Attach to PR description.
10. AI voice review: the hardcoded v1 chat copy is calm, Socratic, no filler. Cross-check against `app_prompts/threshold-chat-system-v1.txt`'s constraint list.
11. `bash scripts/qa-smoke.sh` passes against a deploy preview.
12. `pytest tests/ --ignore=tests/e2e -q` passes (backend unchanged, but verify nothing accidentally broke).

## Test plan

**Frontend unit tests (port the Python parity test to JS or to the existing Python-based JS-syntax pattern):**
- Substantiveness parity fixture: all 28+ entries pass.
- Chat state machine: turn 1 → turn 2 → exit (substantive); turn 1 → turn 2 → fallback → exit (thin); cannot trigger third turn; cannot reopen after summary card mounts.
- Summary card chip edit interactions: click `edit` → input renders with current value → blur saves → escape reverts.
- Source-material chip expand → tab switching → attach → chip shows attached descriptor → CTA copy updates.
- CTA state-dependence: enumerate all 4 truth-table states, assert the CTA's text content + disabled attribute.
- Server 422 handling: mock 422 with `error: thin_sketch_no_source` → footer renders message; 422 with `missing_concept` → focuses concept chip with message.

**Visual smoke (manual, in browser):**
- Turn 1 renders with single textarea composer, no chat bubbles.
- Turn 2 renders, breadcrumb of turn 1 appears above quietly.
- Summary card transition: chat collapses to one-line breadcrumb; chips appear; build CTA single-violet at rest.
- Edit a chip — input swap is calm, no flash, focus lands in the input.
- Add source material — panel expands inline, tabs styled per existing CSS.
- Submit with substantive sketch + no source: chat persists none, summary card persists none, dashboard renders provisional graph.
- Submit with `idk` + no source: CTA stays disabled, sketch chip footer shows the strategy-framed message verbatim.

**Accessibility checks:**
- Keyboard: Tab through chat composer → submit; Tab through summary card chips → edit → save → CTA.
- Focus rings on all interactive elements use `var(--accent-ring)` (soft violet, never thick blue).
- `prefers-reduced-motion: reduce` honored (no animation longer than essential state changes).
- Modal traps focus correctly (existing `trapFocusHandler` logic should work — verify after replacing the form).

## Out of scope (Plan C lands these)

- DESIGN.md §3 Screen 1 update reflecting that threshold capture is conversational. (The spec supersedes; reconciling DESIGN.md is a separate doc commit so it doesn't bloat this branch.)
- Wiring the chat turns to a real backend endpoint (currently hardcoded). Plan B follow-up.
- Concept-derived analogy generation (currently a generic input-output fallback). Plan B follow-up.
- Standards-alignment tile metadata. Already-out-of-scope per spec §7.
- Prerequisite-aware Interleaving Bridge. Already-out-of-scope per spec §7.
- LC Evaluator gating on repair artifacts. Already-out-of-scope per spec §7.

## Risk register

| Risk | Mitigation |
|---|---|
| AI voice drift in hardcoded chat copy (turn 2 + fallback) | Cross-check copy against `app_prompts/threshold-chat-system-v1.txt`'s constraint list. Acceptance criterion #10. |
| JS substantiveness heuristic diverges from Python (false-positive thin sketch passes through) | Parity fixture test in CI (acceptance criterion #7). Server-side validation from Plan A is the safety net even if client check fails. |
| Edit-chip state machine has a stuck state (e.g., escape inside textarea while typing closes the modal) | Standard escape-key precedence: textarea-edit handler should `event.stopPropagation()` so the modal-level escape doesn't fire while a chip is in edit mode. |
| Source panel UI clashes with the chip aesthetic | Reuse the existing `Text | URL | File` tab markup + the redesigned tab styles from 2026-05-01 polish (already in `components.css`). The panel renders inside the chip's expanded body, NOT as a sibling section. |
| Chat surface drifts toward chat-app vibe | Hold the line: text on the page, no bubbles, no avatar, no typing dots. The brand is "calm reading room with a rigorous tutor present" — not a chat app. |
| Substantiveness footer copy gets paraphrased / softened | Render the spec's verbatim copy. Acceptance criterion #6. |

## Branch + worktree shape (recommended)

```bash
git worktree add .worktrees/concept-create-frontend -b feat/concept-create-frontend dev
cd .worktrees/concept-create-frontend
bash scripts/bootstrap-python.sh   # for the parity-test toolchain (pytest)
```

Branch off the current `dev` (which contains Plan A). The worktree's post-checkout hook auto-links `.env` and `.env.local`. The implementation work is mostly JS + CSS + one or two test files; no Python prod code touched.

PR title suggestion: `feat(ui): conversational concept creation — chat → summary card flow`
PR description: paste the acceptance criteria + visual smoke screenshots + the JS parity test summary + a note that Plan A backend (`086e617`) is the dependency and is already on dev.

## How to start (executor's first 10 minutes)

1. Read this handoff end-to-end. Re-read the binding docs (spec, PRODUCT.md, DESIGN.md §3 + §10 + §12, the four new ubiquitous-language terms).
2. Invoke `socratink-design`. Confirm the deliverables checklist at the bottom of `docs/design/socratink-design-system.md` is loaded.
3. Invoke `impeccable`. State the preflight as instructed at the top of this handoff.
4. Open `.superpowers/brainstorm/49698-1777699155/content/locked-design.html` in a browser to see the canonical visual reference.
5. Open `public/js/app.js` and `public/css/components.css` side by side. Read `buildContentInputUI` (around line 684) end-to-end so you understand what you're replacing.
6. Set up the worktree.
7. Decide: do you write a Plan B (formal implementation plan via `superpowers:writing-plans`), or implement directly because the surface is well-bounded? **Recommendation: write the plan first.** This is multi-component (chat state machine + summary card + chip edit + source panel + parity port + telemetry) — a plan keeps the rhythm. Save to `docs/superpowers/plans/2026-05-XX-conversational-concept-creation-frontend.md`.
8. After plan + user approval, dispatch via `superpowers:subagent-driven-development` with batched tasks (mirror the rhythm Plan A used: one batch per coherent surface, code-quality review per batch, final cross-cutting review before merge).

## What "better than codex could ever do" looks like

Concretely, this handoff is built to defeat the most common ways an LLM coding agent fails on frontend work:

- **No vibe coding** — every visible surface has a binding spec reference. The chip table is binding. The CTA truth table is binding. The chat hard-stop is binding.
- **No AI-slop affirmations** — the anti-pattern list calls them out by name and the constraint also lives in the backend prompt.
- **No silent parity drift** — the JS substantiveness port has a fixture-backed parity contract that fails CI on divergence.
- **No "let me just rebuild from scratch"** — exact line numbers, exact CSS class lists to keep, exact CSS class lists to delete.
- **No "I'll patch the design later"** — DESIGN.md §3 reconciliation is moved to Plan C so this branch stays focused.
- **No "I'll skip telemetry, we can add it later"** — events are listed with exact `extra={...}` shapes; the dashboard contract is locked.
- **No "I'll figure out auth"** — the existing `_FakeAuthService` test pattern (used by Plan A's route tests) is documented as the same pattern to use; auth is not in scope.
- **No backend changes** — server-side validation is the authority; the frontend trusts the 422.
- **No new dependencies** — the JS parity port uses stdlib JS regex (with `/u` flag) and the existing parity fixture; no new npm package.

If you're an LLM coding agent picking this up: when in doubt, re-read the spec, re-read this handoff, and ask the user before deviating from either. The cost of one clarifying question is much lower than the cost of a vibe-coded chat surface that has to be torn out.
