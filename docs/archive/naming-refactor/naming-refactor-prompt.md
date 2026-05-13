# Naming convention refactor: socratink full vernacular revamp

You are revamping the **entire learner-visible vernacular** of **socratink**. Only the brand name `socratink` (lowercase) is fixed. Every other learner-visible word — screen names, navigation labels, action buttons, state-display labels, copy patterns, ARIA text, voice register — is open for rename.

This is a **naming and copy refactor only**. Do not change product logic, state transitions, graph semantics, learning rules, or implementation architecture.

Do not introduce gamification, progress claims, mastery claims, diagnostic labels, dashboard framing, content-browser framing, or AI-tutor-knows-your-mind framing. The seven anti-reference categories from `PRODUCT.md` are binding regardless of motif.

---

## Operating posture

A previous run of an earlier draft of this prompt produced ~80% "no change" rows because the previous draft told the agent to preserve too much. Under this revision, your default posture is the opposite:

- **Propose first; justify preservation second.** When in doubt, propose a rename. A "no change" row must be defended *with respect to the chosen motif* — not "this is shipped, so leave it alone."
- **The user's directive is "no word is safe except `socratink`."** Top-level navigation (`Ignition`, `Desk`, `Library`, `Settings`, `Map`), screen titles (`Concept Threshold`, `Provisional Graph`, `First Cold Attempt`, `Locked Study Silhouette`, `Study Repair Artifact`, `Interleaving Bridge`, `Repair History`), action labels (`Start Cold Attempt`, `Add concept`, `Create draft path`), state-display labels, and the dungeon-map vocabulary (`room`, `drill`, `cold attempt`, `boss fight`) are **all in-scope candidates**.
- **"No change" rows are allowed**, but must be tagged with reason: `[no change — motif keeps the term]`, `[no change — domain noun in UBIQUITOUS_LANGUAGE.md, unchanged in this naming pass]`, or `[no change — voice rule already satisfied]`. Don't emit "no change" without one of these tags.
- **When the inventory finds a string outside the chosen motif's vocabulary, propose how to bring it in.** Don't punt to "deferred" unless there's a real reason (feature not shipped, blocked on data layer, etc.).

---

## Mode: motif-then-grill-then-ledger

This refactor runs in **three phases**. Each phase has a single deliverable; **do not advance to the next phase without explicit user approval**.

### Phase 0 — Motif (output only, no code edits, no ledger)

1. Read `PRODUCT.md`, `UBIQUITOUS_LANGUAGE.md`, `DESIGN.md`, and `docs/adr/` if present.
2. Propose **2–3 candidate motifs** for the entire vernacular. Each candidate is a self-contained register the user could ship as a coherent voice. Examples of *registers* (not the actual proposals): crystalline-and-prismatic, atelier-and-archive, almanac-and-field-guide, observatory-and-instrument, library-and-margin. Do not pick from this list — propose your own based on what `PRODUCT.md` actually demands.
3. For each candidate motif, write:
   - A **two-sentence character description** ("This motif sounds like X. Its visual register is Y.").
   - **Eight sample renames** of currently-shipped labels, **deliberately covering**:
     - One top-level nav label (e.g., `Ignition` → ?)
     - One state-display label (e.g., `solidified` chip text → ?)
     - One primary action (e.g., `Start Cold Attempt` → ?)
     - One screen heading (e.g., `Concept Threshold` → ?)
     - One ARIA label (e.g., `Toggle sidebar` → ?)
     - One empty-state heading
     - One dungeon-map vocabulary term as it would appear in copy (e.g., `the room is primed for study` → ?)
     - One state-machine display label (e.g., `growing` → ?)
   - The **three risks** of this motif, in plain language.
4. Output the candidate motifs and STOP. The user picks one (or rejects all and asks for more), then Phase 1 begins.

### Phase 1 — Grill and ledger (output only, no code edits)

After motif approval:

1. Invoke `/grill-with-docs`. Stress-test the chosen motif against `PRODUCT.md`, `UBIQUITOUS_LANGUAGE.md`, and `docs/adr/`. Surface every conflict between the motif and the seven product invariants.
2. Grep the codebase for every learner-visible string in the in-scope surfaces (see "Scope" section). Build a complete inventory.
3. Cross-reference inventory against the **pre-discovered findings** below; confirm each finding's location and add a row.
4. For each inventory entry, propose a rename row:

   ```md
   | Surface (file:line) | Current label/copy | Proposed rename / fate | Rationale | Risk |
   ```

5. Append a **deferred / rejected appendix** — strings the agent considered and chose to leave alone, with reason. Rejected entries are as important as accepted ones.
6. Append a **motif glossary** — the 5–8 vocabulary anchors the chosen motif rests on (so future copy decisions can be made consistently without re-grilling).
7. Append **open questions for the user**.
8. STOP. The user reviews row-by-row.

### Phase 2 — Apply, only after row-by-row approval

Apply approved entries from the ledger. After each batch of edits, re-grep the affected files for consequential drift (e.g., a screen-name rename that requires its `aria-label` to change too, or a state-label rename that should appear consistently in chip text + status copy + screen-reader announcements). Do not improvise renames not in the approved ledger.

---

## Pre-discovered findings (from a prior Phase 1 run)

A prior run of an earlier draft of this prompt surfaced these real findings. They survive any motif choice — they're voice-rule cleanups or hygiene fixes, not motif-dependent renames. **Confirm each location's current state and include each as a Phase 1 ledger row regardless of motif.**

| Surface | Current | Proposed action | Reason |
| --- | --- | --- | --- |
| `public/login.html:28` (alt text) | `Socratink brand mark` | `socratink crystal mark` (or motif-aligned) | `Socratink` capitalized violates lowercase brand rule. |
| `public/index.html:77` (alt text) | `Socratink brand mark` | same as above | same as above |
| `public/login.html:11` | `socratink — the Socratic Canvas` | `socratink — sign in` (or motif-aligned tagline) | "Socratic Canvas" is not in canonical product vocabulary. |
| `public/js/app.js:299` | `Re-drill later if you want to challenge it.` | `Re-drill later if you want another reconstruction pass.` | "challenge" is on the avoid-list. |
| `public/js/graph-view.js:69` | `Needs correction` | `Needs a different causal link` (or motif-aligned) | "correction" reads as defect/diagnostic framing. |
| `public/js/graph-view.js:832` | renders `data.reDrillBand` (one of `spark/link/chain/clear/tetris`) directly to learners | **remove the visible band entirely**; replace with motif-aligned reconstruction-evidence copy | Trajectory bands are internal-only telemetry; rendering `tetris` to learners is a hard voice violation. |
| `public/js/graph-view.js:391, 906, 910`, `public/js/app.js:2377, 2378` | `Cluster`, `drill nodes`, `clusters` (in learner-visible copy) | propose motif-aligned `room set` / `rooms` (or whatever the motif renders) | "Cluster" is implementation terminology on a learner surface. |
| ARIA scan across drawer, map, theme, graph, repair controls | (no missing aria-label found in prior scan) | confirm; flag any new icon-only buttons missing `aria-label` | a11y baseline. |

Treat these as **starting points, not the full inventory**. The grep audit must still cover the entire learner-facing surface.

---

## What is fixed (do not change)

### Brand
- `socratink` — always lowercase in product copy. Even sentence-initially, unless code or platform constraints require otherwise.

### Voice rules (from `PRODUCT.md`)
- calm, precise, Socratic
- reading-room, not dashboard
- plain complete sentences
- no exclamation marks
- no emoji
- no hype, no praise that sounds like evidence
- no diagnostic framing
- no gamification vocabulary

### Anti-references (from `PRODUCT.md`; the chosen motif must respect all seven)
- No gamification: streaks, XP, badges, leaderboards, ranks, combos, achievement popups.
- No mastery / completion / progress claims.
- No diagnostic labels: beginner, intermediate, advanced, schema, learning-style.
- No clinical SaaS, neon-dark dashboards, stock education imagery, emoji-led encouragement, hype copy.
- No graphs that look like content browsers, progress bars, or mastery charts.
- No quiz-app framing: scoring cold attempts, framing struggle as failure.
- No AI-tutor-knows-your-mind framing.

### Forbidden vocabulary (regardless of motif)
- mastered, completed, unlocked, leveled-up, achieved, polished, gemmed
- score, scoring, ranked, rank
- XP, streak, badge, trophy, combo, win, quest, loot, power-up, reward, bonus
- crush, supercharge, revolutionary, AI-powered, game-changing
- "tailored just for you", "knows your mind", "understands you"
- challenge (in the cold-attempt / re-drill context)
- correction (in the diagnostic / defect-framing sense)

### Product truth (semantic invariants the motif must protect)
- The graph is a record of evidence socratink has seen, not a content browser.
- Graph truth changes only when learner-generated evidence is recorded.
- Reading, viewing, browsing, clicking, or graph generation does NOT change learning state.
- The core promise: "see what you can actually explain."
- Each node represents a learning unit; the learner makes a cold attempt before any explanation is shown; targeted study repairs the attempted mechanism; spaced re-attempt earns durable evidence.
- The seven-step learning loop is the invariant; it can be **renamed** but not **rerouted**: starting model → provisional graph → first cold attempt → locked study before generation → study repair after attempt → interleaving recommendation → repair-history record.

---

## Domain-noun vs display-label distinction (important)

`UBIQUITOUS_LANGUAGE.md` is a domain glossary. Terms there name **concepts in the product's mental model**, not visible labels. The display labels can change while the underlying domain noun stays.

Examples:
- The domain noun `hinge` (UBIQUITOUS_LANGUAGE) might appear in UI as `joint`, `pivot`, `keystone`, etc. The doc keeps `hinge`; the UI uses the motif's word. **Rename rows that touch only the display label are in-scope; rename rows that change the underlying domain noun are out-of-scope (defer to a separate domain refactor).**
- The data-state token `locked` (a string in `data-state="locked"` and JS state machine) stays as a code identifier. The chip text learners see for that state can become whatever the motif says. **Rename rows that touch only the chip text are in-scope; rename rows that change the data-state value are out-of-scope.**

When in doubt, propose the display-label rename and tag the underlying-domain-noun rename `[deferred — out of scope, separate domain refactor]`.

---

## What is in scope (renameable)

### Learner-visible surfaces
- HTML `innerText` and template-literal display strings.
- Button labels, link text, headings (h1–h6), kicker labels, chip labels, badge labels.
- Empty-state copy, validation messages, error messages, modal titles, toast text.
- Placeholder text on form inputs.
- View titles and section headings.
- State-display labels (the chip text shown for `growing`, `solidified`, `fractured`, etc. — the *display string*, not the underlying token).
- Marketing/landing copy in `public/`.

### ARIA and a11y surfaces (first-class — screen-readers announce these literally)
- `aria-label` on every interactive element.
- `aria-description` (where present).
- `title` attribute (announced as fallback by some screen-readers).
- Visually-hidden text (`<h1 class="visually-hidden">`, `<span class="sr-only">`, etc.).
- `alt` attributes on `<img>` elements (announced; brand-rule sensitive — note `Socratink brand mark` is a known violation, see pre-discovered findings).

### Hard preservation note
The learner-visible label and the internal token can diverge. The token `locked` stays as a `data-state` value in HTML and a JS state-machine string. The label users SEE for that state is open. Rename rows that touch internal tokens must be tagged `[deferred — domain refactor, not naming]`.

---

## What is out of scope (do not touch)

- **CSS class names** (e.g., `.concept-tile`, `.map-mode-switch`, `.btn-start-drill`). High blast radius; every JS selector reference would need updating.
- **DOM `id` values** (e.g., `#concept-start-drill`). JS event handlers and ARIA `aria-controls` linkages depend on them.
- **JS function/variable/module names** — internal API.
- **File paths and file names.**
- **`data-*` attribute values** that JS reads as state (e.g., `data-state="growing"`, `data-map-mode="study"`). These are state-machine identifiers.
- **Database column names, API endpoint paths, JSON response keys, prompt schema keys.**
- **The data-layer state tokens themselves** as strings: `locked`, `primed`, `drilled`, `solidified`, `fractured`, `growing` — wherever they appear as code identifiers (the *display labels* for these states, however, are in-scope).
- **Internal tooling and devops surfaces.** Specifically: anything under `scripts/`, internal Python tooling, log strings, telemetry tags, internal devtool CLI output. The audit is **learner-facing only**.
- **`docs/` content** (this prompt lives in `docs/codex/`; treat all of `docs/` as out-of-scope unless the user explicitly asks for a docs sweep).

If a rename of in-scope copy would benefit from a class/id rename or token-string rename for legibility, **add it to the ledger as a separate row tagged `[deferred — out of scope]`**. The user will decide whether to schedule a follow-up domain refactor.

---

## Required outputs by phase

### Phase 0 deliverable

A document with this exact structure:

```md
# Motif candidates for socratink vernacular revamp

## Candidate A: <motif name>
**Character:** <two-sentence description>
**Sample renames (8):**
| Surface | Current | Proposed |
| --- | --- | --- |
| Top-level nav | Ignition | <new> |
| State-display chip | solidified | <new> |
| Primary action | Start Cold Attempt | <new> |
| Screen heading | Concept Threshold | <new> |
| ARIA label | Toggle sidebar | <new> |
| Empty-state heading | Your Library | <new> |
| Dungeon-map copy | "the room is primed for study" | <new> |
| State-machine display | growing | <new> |
**Risks (3):** <plain-language risks>

## Candidate B: <motif name>
... (same structure)

## Candidate C: <motif name>
... (same structure)

## Recommendation
<Which candidate the agent recommends and why, in 2-3 sentences. Or "all three are viable; user pick.">

## Open questions for the user before Phase 1
<Anything the agent needs answered before grilling.>
```

### Phase 1 deliverable

A document with:

1. **Rename ledger** (the table format above), one row per in-scope learner-visible string. Every row's `Proposed rename / fate` is one of:
   - A concrete motif-aligned rename, OR
   - `[no change — motif keeps the term]` + 1-line reason, OR
   - `[no change — domain noun, unchanged in this naming pass]` + 1-line reason, OR
   - `[no change — voice rule already satisfied]` + 1-line reason, OR
   - `[deferred — feature not shipped]` + 1-line reason, OR
   - `[deferred — out of scope]` + 1-line reason, OR
   - `[uncategorized — propose category]` + 1-line reason.
2. **Deferred / rejected appendix** — strings the agent considered and chose to leave alone, with reason.
3. **Motif glossary** — the 5–8 vocabulary anchors the chosen motif rests on. Include singular / plural pairs for any unusual nouns.
4. **Open questions for the user.**

### Phase 2 deliverable

After row-by-row approval, the agent applies edits in batches and reports:
- Files touched
- Strings renamed (count by file)
- Any consequential drift discovered (e.g., a button rename that required an `aria-label` co-rename) and how it was resolved
- Cache-buster bumps for any CSS/JS files affected
- A re-grep summary confirming no orphan references remain

---

## Grill questions to drive into Phase 1

For each candidate rename, the grill should answer at minimum:

1. **Does this term already exist in `UBIQUITOUS_LANGUAGE.md`?** If yes, are we changing the *display label* (in-scope) or the *domain noun* (deferred)? Document the choice.
2. **Does the new term collide with an existing reserved word** (state token, anti-reference register, brand reserved noun, code identifier in adjacent files)?
3. **What's the load-bearing audience?** First-run user, returning learner, accessibility user (screen-reader), or developer reading source? Different audiences may need different terms.
4. **Reading at 320×568 (iPhone SE, narrowest mobile target):** does the new label fit chip components? Long phrasings break tight UI. Drop the candidate or shorten in the ledger row, don't defer to a polish pass.
5. **Is the rename in active mental-model territory** (the top-level nav, state machine, primary actions) or in cold-decoration territory (a kicker, a tooltip)? Cold decoration is cheap; mental-model is expensive.
6. **What's the regression risk?** If we ship this rename, what could break for an existing user (muscle memory, screenshots in docs, support docs, marketing copy linked from elsewhere)?
7. **Does the rename respect the seven product invariants** (graph-as-evidence, no-state-from-reading, cold-attempt-first, etc.)? A rename that subtly implies "completion" — even if the word itself isn't on the forbidden list — should be rejected.
8. **For "no change" rows: how does this term fit the chosen motif?** If you can't articulate why the existing term is consistent with the new motif, propose a rename instead.

---

## Pluralization rules

Plural forms for unusual nouns must be specified in the motif glossary (singular / plural pair).

Common traps to specify:
- atlas → atlases (NOT "atlasi", "atlantes")
- prism → prisms
- almanac → almanacs
- archive → archives
- field → fields
- margin → margins
- lattice → lattices
- crystal → crystals (avoid "crystalline" as a count noun)

If the motif introduces a noun whose plural is debatable, default to the regular `-s` form and note the choice.

---

## ARIA and screen-reader copy

ARIA labels are first-class learner-visible surfaces. They are the literal text screen-reader users hear.

In-scope ARIA targets:
- `aria-label` on every interactive element.
- `aria-description` (where present).
- `title` attribute.
- Visually-hidden `<h1>`, `<span class="visually-hidden">`, etc.
- `alt` attributes on `<img>`.

Special considerations:
- ARIA labels for state changes (e.g., a button's accessible name when `aria-pressed="true"`) must read coherently aloud.
- Icon-only buttons (`.drawer-toggle`, `.drawer-close`, etc.) MUST have an `aria-label`. Prior scan found no missing aria-labels — re-confirm during this pass.
- The visually-hidden `<h1>socratink</h1>` is announced as the page heading. `socratink` itself is fixed; if the motif introduces a tagline, it does NOT go in the h1 (which stays just `socratink`).

When proposing rename rows, the ledger should include the visual label AND its associated aria-label as separate rows when they differ.

---

## Final acceptance checklist

Before completing **Phase 2** (after row-by-row approval), verify:

- `socratink` remains lowercase everywhere (including alt text — see pre-discovered findings).
- All chosen-motif vocabulary is consistent across screens, copy, and ARIA.
- No copy claims mastery from reading, graph generation, fluent prose, or membership in a collection.
- No copy says any unit is complete, mastered, unlocked, leveled, or scored.
- Internal `data-state` token values are unchanged (renames touched display labels only).
- `data.reDrillBand` no longer renders to learners (`spark/link/chain/clear/tetris` are internal-only telemetry).
- All renamed strings render legibly at iPhone SE 320×568. Long phrasings that overflow chip components were shortened in Phase 1, not deferred.
- ARIA labels are vocabulary-aligned; icon-only buttons have non-empty `aria-label`s.
- The seven product invariants from `PRODUCT.md` are intact in the new vernacular.
- The new vernacular respects all seven anti-reference categories.
- No exclamation marks, no emoji, no hype, no diagnostic framing, no dashboard framing, no content-browser framing, no AI-knows-your-mind framing.
- "challenge" (in cold-attempt context) and "correction" (in diagnostic-framing context) are absent from learner copy.
- Internal tooling and devops surfaces were not touched.

---

## One-sentence directive

Read `PRODUCT.md` + `UBIQUITOUS_LANGUAGE.md` + `DESIGN.md`; propose three candidate motifs with eight sample renames each that span nav / state / action / screen / ARIA / empty-state / dungeon-map copy / state-machine display, and stop. After motif approval, build a complete rename ledger (every row tagged with one of the seven row-fates), surface the pre-discovered findings, and stop. Apply only after row-by-row approval, batch by batch, with re-grep after each batch.
