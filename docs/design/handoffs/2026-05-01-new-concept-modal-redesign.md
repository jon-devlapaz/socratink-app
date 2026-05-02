# Handoff — New Concept modal redesign (Stage 0 capture)

**Date drafted:** 2026-05-01
**Status:** Ready for pickup
**Drafted by:** Claude Opus 4.7 (1M context), in conversation with jon-devlapaz
**Skills the next agent must invoke (BOTH, in order):**

1. `socratink-design` — loads the brand system (palette, typography, crystal motif, copy voice, dark-mode graph spec, design tokens). Required before touching any socratink UI.
2. `impeccable` — frontend critique, redesign, polish workflow. Required for the actual UI changes (anti-patterns, visual hierarchy, motion, accessibility, edge states).

**Both skills must be loaded.** Do not skip one. `socratink-design` defines what "on-brand" means for this product specifically; `impeccable` is the general frontend-quality discipline that applies on top.

---

## What this handoff is

The New Concept modal is the learner's first product surface — it captures the **Concept Threshold** per `DESIGN.md` §3 Screen 1. It is mostly product-correct, but a critique pass on 2026-05-01 against `DESIGN.md` and `PRODUCT.md` surfaced six issues, ranked below.

This handoff is the work order to fix them without breaking what's working.

---

## Source artifacts

- **The modal in code:**
  - `public/js/app.js` — template literal renders the modal HTML
    - Modal title + dialog: `L1122` (`<h3 id="creation-dialog-title" class="creation-dialog-title">Start a concept</h3>`)
    - Fuzzy toggle: `L719`, `L969`
    - Source-material textarea + placeholder: `L740`
    - Paste actions row: `L741` (`<button class="paste-clipboard-btn">…</button><button class="wiki-random-btn">Random science</button>`)
    - Submit button: `L758`, `L802` (`Draft from Text`)
    - Random-prompt list: `L860` (`'Paste a Wikipedia article...', 'Paste a research paper...'`)
  - `public/css/components.css` — styling
    - `.overlay-extract`: L655
    - `.creation-fuzzy-toggle`: L948
    - `.creation-submit`: L1020
    - `.paste-clipboard-btn`: L1036
    - `.wiki-random-btn`: L1043
    - `.overlay-textarea`, dialog title styles: search the file
- **The screenshot reviewed in conversation:** the modal as rendered in dark mode (constellation/sky theme, violet accents, modal overlay over the constellation background). The redesigner can re-screenshot from the running app — the live state is the canonical reference.

## Binding docs (must respect)

- `DESIGN.md` — the UX design document. Especially:
  - §3 the metacognitive happy path — Screen 1 Concept Threshold spec is binding for this surface
  - §6 session guardrails (added in commit `6f352e8`)
  - §7 Copy voice — UPPERCASE eyebrows only, lowercase `socratink`, no hype, no emoji, no exclamation marks
  - §9 Sensory grammar — *"One violet accent per screen. Stack three of them and the screen has no foreground."* — this is the rule we are most clearly violating
  - §10 The MVP cut — *binding prioritization*. Note: *"Defer: URL ingestion (until SSRF hardening + manual fallback ships)"*
  - §11 What socratink refuses to be — anti-references list
- `PRODUCT.md` — product purpose, brand personality, anti-references, design principles
- `UBIQUITOUS_LANGUAGE.md` — the term list (Concept Threshold, starting map, Provisional map, Cold attempt, etc.)

If a proposed change conflicts with one of these docs, the docs win. If a real product reason requires departing from a doc, update the doc as part of the same PR.

---

## What is working — DO NOT CHANGE

These elements are in conformance with the binding docs and are working:

1. **Eyebrow `NEW CONCEPT`** — UPPERCASE wide tracking, exactly the eyebrow rule from DESIGN.md §7
2. **Title Case `Start a concept`** — section-heading style per §7
3. **Lowercase `socratink`** — used everywhere it appears
4. **The two binding lines in the subtitle:**
   - *"Start with your rough map."*
   - *"This is global context. The first room will ask one smaller question."*
   These match Screen 1 spec verbatim. They are load-bearing copy.
5. **Footer copy:** *"Study content stays locked until the cold attempt."* — locks the generation-before-recognition principle into the surface (Design Principle 1, PRODUCT.md)
6. **Adaptive-attribution copy:** *"Add your starting map. It is global context, not evidence."*
7. **Two textareas of different heights** — starting-map textarea is taller than source-material textarea. Correct: learner words deserve more space than source material per the Concept Threshold spec. Keep this hierarchy.
8. **Cancel + primary action button layout** — primary button on the right is the right pattern.

---

## Issues to address (ranked by binding-doc severity)

### 🔴 1. Five+ violet accents — DESIGN.md §9 violation

DESIGN.md §9: *"One violet accent per screen. The crystalline warm violet is the only interactive color. Stack three of them and the screen has no foreground."*

Currently violet appears on:
- Eyebrow kicker (`NEW CONCEPT`)
- `0/4 active` pill (top right)
- `Add fuzzy area` link (`creation-fuzzy-toggle`)
- `Text` segmented-control fill (when active tab)
- `Paste from clipboard` link (`paste-clipboard-btn`)
- `Random science` link (`wiki-random-btn`)
- `Draft from Text` primary button (`creation-submit`)

**Fix:** Pick ONE violet anchor. The primary button (`Draft from Text`) earns it — that is the action the learner will take. Demote the rest:
- Eyebrow → keep UPPERCASE wide tracking but render in a muted ink color (DESIGN.md says eyebrows are the lone exception for tracking, not for color — re-check)
- Pill → ink + border (or remove entirely, see #3)
- Fuzzy toggle → ink with violet on hover only
- Tab fill → use elevation/shadow contrast for the active tab, not violet fill
- Paste-from-clipboard / Random-science → text-link style, ink, with violet on hover only

Keep the primary button the only hard-violet element on the surface at rest. The screen will gain a foreground.

### 🔴 2. "Random science" copy violates anti-hype rule

PRODUCT.md anti-references: *"Generic AI tutor branding"*, *"hype copy."* DESIGN.md §7: *"No hype jargon — revolutionary, AI-powered, supercharge, 10×, unlock, crush, game-changing."*

*"Random science"* sits in the same family — quirky-app vibe, narrows the surface to one domain (what about a non-science learner?).

**Fix options:**
- **Preferred:** remove the button entirely. The placeholder text already prompts "what to paste"; the random-prompt rotation in the placeholder (L860) already serves the "spark idea" function.
- **If keeping:** rename to `See an example` or `Try a sample`. Calm, Socratic verb. Update the random-prompt list at `L860` to be domain-agnostic (no hard-coded "Wikipedia article" / "research paper").

### 🟡 3. `0/4 active` pill is noise during concept creation

Per DESIGN.md §6 (session guardrails): *"Two to three nodes in active rotation is the recommended ceiling. Maximum 4 nodes per session."* The pill represents this cap, but during *concept creation* the learner has no active rooms yet. `0/4 active` is a counter that doesn't move until they're somewhere else.

DESIGN.md §9: *"One active cognitive target. Each screen should foreground the current room, phase, and next move while lowering the visual weight of everything else."*

**Fix:** Move the pill out of this modal entirely. It belongs on a surface where active concepts exist (probably the learner's home view after at least one Cold attempt has happened). On this modal, the cognitive target is "describe what you want to understand" — the pill steals attention.

### 🟡 4. `URL` tab — verify with founder against MVP cut

DESIGN.md §10 (binding prioritization): *"Pasted text + global learner-map inputs only. Defer: URL ingestion (until SSRF hardening + manual fallback ships)."*

Status now (2026-05-01): the `source_intake` module IS robust on URL ingestion (SSRF defense + DNS-rebinding defense + redirect re-validation + 2 MB cap + charset chain — verified during the foundation-design conversation). So the deferral condition has technically been met.

But the binding doc still flags this as deferred. **Do not silently keep the URL tab live** — confirm with the founder before shipping. Two acceptable outcomes:
- **(a)** Founder confirms URL is now in-scope: keep the tab, update DESIGN.md §10 to remove the URL deferral.
- **(b)** Founder wants URL still deferred: hide the URL tab from the segmented control and ship just `Text | File`.

Either way: code + docs in lockstep.

### 🟡 5. Placeholder text is too directive

`public/js/app.js:740` and `L860`: *"Paste a Wikipedia article..."* and the rotating list `'Paste a Wikipedia article...', 'Paste a research paper...'`.

PRODUCT.md describes users as arriving with *"source material, a concept name, notes, transcripts, articles, or a rough starting model."* The placeholder narrows that to two specific domains. A lecture-notes user, a textbook-chapter user, or a learner with their own writing all read this as "this isn't for me."

**Fix:** Generalize. Replace the rotation list with copy like:
- `Paste a passage you want socratink to structure`
- `Paste your notes, a transcript, or an article excerpt`
- `Paste any source material — socratink will sketch the room`

Aim for verbs the learner *does* (`paste`, `bring`, `try`) and nouns from PRODUCT.md's user description (passage, notes, transcript, article excerpt, rough starting model).

### 🟡 6. `Add fuzzy area` lacks affordance

Without context, a learner skips it. Either:
- **Surface a one-line preview when collapsed:** *"Mark a section you're uncertain about — socratink will probe it first."* (verify with founder that this is what the feature actually does)
- **Or:** if it's optional polish on first-time use, hide it behind a learn-as-you-go reveal.

The current state — a violet link with no preview — neither helps the new learner nor honors the calm-Socratic tone.

### 🟢 7. `Draft from Text` button verb (low priority)

*"Draft"* hedges nicely with the doc's `Draft map` → `Provisional map` language. Probably fine. If you want a tighter verb tied to the dungeon-map metaphor: `Sketch the room` or `Build the map`. Test with a real learner before changing.

---

## Deliverables

1. **Updated `public/js/app.js`** — modal template, action buttons, placeholder copy, random-prompt list (if kept), fuzzy-toggle copy (if reworked).
2. **Updated `public/css/components.css`** — accent demotion (most violet → ink/muted with hover-only violet), tab styling without violet fill, possibly typography updates if `socratink-design` calls for them.
3. **Possibly updated `DESIGN.md`** — §10 if URL tab decision changes the MVP cut. Document discipline: code and DESIGN.md ship together.
4. **Visual smoke** — open the running app in a browser, take a fresh screenshot of the redesigned modal in dark mode (constellation theme), include in the PR description.
5. **Test pass** — `bash scripts/qa-smoke.sh` against a deploy preview confirms no regressions; `pytest tests/ --ignore=tests/e2e` for backend (no changes expected).

## Success criteria

- Exactly one hard-violet element at rest (the primary action). Hover states may add violet to others.
- No hype copy anywhere. Specifically no `Random science`.
- No irrelevant metadata (`0/4 active` pill) on the creation surface.
- Placeholder text is general — covers the full PRODUCT.md user-description range.
- The two binding lines from DESIGN.md §3 Screen 1 are still present, verbatim.
- Footer line is still present, verbatim.
- The redesigned modal still feels like *the same product surface* — calm, Socratic, reading-room-not-dashboard. (PRODUCT.md brand personality.)
- All DESIGN.md anti-references (§11) still respected.
- Accessibility: keyboard navigation, focus rings, `prefers-reduced-motion: reduce` honored.

## Out of scope

- Backend changes — Stage 0 input contract is set (see `docs/superpowers/specs/2026-05-01-foundation-design.md` §5.7).
- The fresh-view "What do you want to understand?" form — different surface, addressed earlier.
- The drill / repair / re-drill UI — different surfaces.
- The graph / room rendering itself — different surfaces.

## How to start

1. Read `DESIGN.md` and `PRODUCT.md` end-to-end (mandatory). Note the binding sections cited above.
2. Invoke `socratink-design` skill — loads the brand system.
3. Invoke `impeccable` skill — loads the frontend-quality discipline.
4. Open the running app locally (`bash scripts/dev.sh`) and trigger the New Concept modal so you can iterate visually.
5. Tackle the issues in order — #1 first (it has the largest visual blast radius). Move to #2-#7 after the violet stack is resolved.
6. Surface decisions to the founder for #4 (URL tab) and #6 (fuzzy area copy) before writing the code change for those.

## Branch and PR shape

- **Branch:** `feat/concept-modal-redesign` off current `dev`
- **Worktree-ready:** `git worktree add .worktrees/concept-modal -b feat/concept-modal-redesign dev` — the post-checkout hook from `scripts/git-hooks/post-checkout` will auto-link `.env` and `.env.local`. Confirmed working.
- **PR title:** `feat(ui): redesign New Concept modal — single-anchor violet, calm copy, drop hype`
- **PR description:** include before/after screenshots, list the 6 issues + their fixes, link this handoff doc, and note any DESIGN.md updates that came along.
