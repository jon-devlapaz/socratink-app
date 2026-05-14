# Plan v2: DESIGN.md refactor — first agentic use

## Material discovery (changes v1 substantially)

The repo already contains:

- `DESIGN.md` (329 lines) — high-quality but **prose-heavy UX manifesto**, well over the 100–200 line agent-first sweet spot. Sections are narrative, not scannable. Examples: "the cold attempt is stepping through the door before you know what's inside" (poetic), no decision tables, no boundary tiers.
- `UBIQUITOUS_LANGUAGE.md` (117 lines) — **already agent-ready**: term/definition/aliases tables, "Relationships" section, drift report. Excellent format. Referenced as authoritative by current `DESIGN.md` and ADRs.
- `CONTEXT.md` (59 lines) — narrative glossary. Three entries: Library, Confusion artifact, Draft path (deprecated). Partially overlaps UBIQUITOUS_LANGUAGE.md.
- `AGENTS.md` (360 lines) — ops canon, separate concern.
- 4 ADRs in `docs/adr/`.

Plan v1 assumed DESIGN.md was being created from scratch and that CONTEXT.md was the only glossary. Both wrong.

## Revised goal

1. **Slim the current DESIGN.md** to ~160 lines, agent-first format (tables, boundary tiers, capability statements). Promote it to canonical product hub.
2. **Demote** current DESIGN.md's prose content to `docs/design/socratink-ux.md` as a deep-dive reference (the Gemini "don't obliterate" pattern).
3. **Keep** UBIQUITOUS_LANGUAGE.md as-is — it's already the right shape. New DESIGN.md §Domain is a 3-line pointer to it.
4. **Fold** CONTEXT.md's non-overlapping content (Confusion artifact, Draft path deprecation) into UBIQUITOUS_LANGUAGE.md, then delete CONTEXT.md.
5. **Add** `llms.txt` at repo root.

## Target end-state

```
DESIGN.md                              ~160 lines  REWRITE — slim agent hub
docs/design/socratink-ux.md            ~330 lines  NEW (=current DESIGN.md verbatim)  deep-dive ref
UBIQUITOUS_LANGUAGE.md                 keep        canonical domain language (already agent-ready)
AGENTS.md                              keep, trim  ops canon
README.md                              keep        human entry
llms.txt                               NEW         agent crawler index

CONTEXT.md                             DELETE      Confusion artifact + Draft path move to UBIQUITOUS_LANGUAGE.md first
docs/adr/                              keep        history
docs/design/socratink-design-system.md keep        deep-dive ref (pointed-to from DESIGN.md)
docs/product/spec.md                   keep        deep-dive ref (pointed-to from DESIGN.md)
docs/design/handoffs/*                 archive     ephemeral
docs/qa/2026-05-* (older)              archive     keep newest
docs/project/doc-map.md                rewrite     ~30-line pointer page
```

## New DESIGN.md section structure (7 sections, ~160 lines)

1. **Product intent** (~12 lines)
   - One paragraph: what socratink is, who for
   - The one-line summary: "The graph proposes. The cold attempt creates something to repair. Study makes the repair inspectable. The spaced re-drill records the strongest evidence."
   - "What socratink refuses to be" condensed to a 5-bullet hard-exclusion list (was §14 in current DESIGN.md)
   - Pointer: full UX manifesto → `docs/design/socratink-ux.md`

2. **Domain language** (~6 lines)
   - 3-line note: "Canonical terms and aliases-to-avoid live in `UBIQUITOUS_LANGUAGE.md`. Code/copy that disagrees is wrong unless that file is updated first."
   - Quick-reference table of the 6 most-used terms (Cold attempt, Targeted study, Spaced re-drill, locked/primed/drilled/solidified) with one-line defs
   - Pointer to full glossary

3. **State / data flow** (~12 lines)
   - 3–5 line summary: Imported source / Launch attempt → Provisional map → Cold attempt → Targeted study → Repair Reps → Spaced re-drill → Graph truth mutation
   - Names the seams: LLM seam (ADR-0002), Map typed contract (ADR-0001), Retriable error marker (ADR-0003), Library = users' work only (ADR-0004)
   - Internal-only signals callout (routing hints never user-visible)

4. **Non-obvious decisions** (~35 lines)
   - Decision table: decision | why | don't do | ADR
   - Rows:
     - Map is typed contract — ADR-0001
     - LLM behind seam — ADR-0002
     - RetriableLLMError marker — ADR-0003
     - Library = users' work only — ADR-0004
     - Concepts seeded without source — memory
     - No dual-state designs (truthful state) — memory
     - Silent surface default — memory
     - Adjacent-surface vocabulary clash is a bug class — memory
     - Antigravity theme is the in-app exception to cream-paper rules — design system
     - Chat is ignition, not the product surface — memory

5. **Design system primitives** (~20 lines)
   - Palette (token names + 1-line each): `--cream-50`, `--ink-900`, `--violet-600`, `--lavender-500`, `--mauve-200`, `--success` (solidified only), `--danger` (fractured only)
   - Type: Geom display + Inter body + Manrope fallback (self-hosted, no Google Fonts — Antigravity Outfit is the one exception)
   - Motif: crystal polygon at three scales (favicon, wordmark, isometric tile)
   - Theme archetypes: dark = constellation/sky, light = drafting/blueprint
   - Pointers: `public/css/tokens.css` (hex), `docs/design/socratink-design-system.md` (component rules)

6. **Voice & interaction model** (~25 lines)
   - Posture: calm, precise, Socratic. Reading room, not dashboard.
   - 6 hard rules (lowercase `socratink`; no exclamation; no emoji; no hype jargon; strategy over ability; admit honest state)
   - Silent surface default — every visible element earns its keep
   - Adjacent-surface vocabulary clash check (verbatim short form from memory)
   - State copy vocabulary table (allowed vs. forbidden)
   - Applies to UI copy, error messages, **LLM prompts**, interaction logic
   - Pointer: full tone-by-surface table → `docs/design/socratink-ux.md` §10

7. **Boundaries** (~25 lines)
   - Three-tier table for both **design** and **engineering** decisions:
     - ✅ Always: use tokens not raw hex; commit straight to dev; respect prefers-reduced-motion; grep `<<<<<<<` before commit; bump cache-bust on both stylesheet AND importer when editing CSS imported via `@import`
     - ⚠️ Ask first: change palette tokens; edit AGENTS.md hooks; introduce a third accent color; deviate from Antigravity in-app shell
     - 🚫 Never: pure white in light theme; true black text; emoji in any surface; exclamation marks; force push main; ship `<<<<<<<` to prod; deploy without QA; invert theme archetypes; learner-visible schema labels; "AI-powered" / "revolutionary" / "supercharge" copy

8. **Pointers** (~20 lines)
   - Ops canon → `AGENTS.md`
   - Full UX manifesto → `docs/design/socratink-ux.md`
   - Domain language → `UBIQUITOUS_LANGUAGE.md`
   - ADR history → `docs/adr/`
   - Deep-dive design system → `docs/design/socratink-design-system.md`
   - Deep-dive product spec → `docs/product/spec.md`
   - Design tokens (code) → `public/css/tokens.css`
   - Agent workflows → `agents/`
   - Archive → `docs/archive/`

## llms.txt

```
# socratink-app

> Learner-led knowledge mapping app. Generation > recognition. Graph reflects learner-generated evidence, not reading.

## Canon
- [DESIGN.md](/DESIGN.md): product intent, decisions, design primitives, voice, boundaries
- [AGENTS.md](/AGENTS.md): agent ops — commands, conventions, git workflow
- [UBIQUITOUS_LANGUAGE.md](/UBIQUITOUS_LANGUAGE.md): canonical domain terms + aliases to avoid
- [ADRs](/docs/adr/README.md): append-only architectural decisions

## Deep-dive
- [Full UX manifesto](/docs/design/socratink-ux.md)
- [Design system component rules](/docs/design/socratink-design-system.md)
- [Product spec](/docs/product/spec.md)
- [Design tokens (code)](/public/css/tokens.css)
- [Agent workflows](/agents/README.md)
```

## Execution steps

1. **Pre-flight audit** (catch hidden CONTEXT.md references that grep misses):
   - `grep -rn "CONTEXT.md" --include="*.json" --include="*.yaml" --include="*.yml" --include="*.toml" --include="*.py" --include="*.js" .` for config/hook references
   - Check `.claude/settings.json`, `.claude/hooks/`, `agents/founder/WORKFLOWS/03-prototyping.md` (confirmed reference), `agents/_templates/`, `app_prompts/*` for system-prompt-level references
   - Catalog references that must be redirected (most likely → DESIGN.md or UBIQUITOUS_LANGUAGE.md)

2. **Move existing DESIGN.md to deep-dive location** — `git mv DESIGN.md docs/design/socratink-ux.md`. Preserves all 329 lines verbatim.

3. **Draft new slim DESIGN.md at root** (~160 lines, sections above). Source content from current DESIGN.md, AGENTS.md, ADRs, design system spec, product spec, and memory. Decision tables. Real terminology verbatim.

4. **Show new DESIGN.md draft to user** before any further moves. User reviews tone, completeness, what's missing. Iterate.

5. **Only after user approval**:
   - Fold CONTEXT.md's "Confusion artifact" and "Draft path (deprecated)" entries into UBIQUITOUS_LANGUAGE.md (the latter may already be implicit in the drift report — verify before duplicating).
   - Delete CONTEXT.md.
   - Update the 6 cataloged references (AI_READINESS.md, AGENTS.md, agents/founder/WORKFLOWS/03-prototyping.md, docs/adr/0004-library-is-users-work-only.md, docs/project/doc-map.md) to point to DESIGN.md or UBIQUITOUS_LANGUAGE.md as appropriate.
   - Write `llms.txt`.
   - Trim AGENTS.md (remove anything that duplicates DESIGN.md; show diff to user before commit).
   - Move ephemeral docs to `docs/archive/2026-05-design-md-refactor/`.
   - Rewrite `docs/project/doc-map.md` as a 30-line pointer.

6. **Verify**:
   - `wc -l DESIGN.md` is 140–180
   - `grep -rn "CONTEXT.md" .` (excluding archive + .plans) returns 0
   - `grep -rn "/DESIGN.md\|^DESIGN.md\|](DESIGN.md" .` resolves
   - All ADR links in DESIGN.md resolve
   - All deep-dive pointers in DESIGN.md resolve

7. **Single commit on dev**: `refactor(docs): consolidate canonical design hub into slim DESIGN.md (agent-first)`

## Risks & mitigations

- **Risk: lossy compression of current 329-line DESIGN.md.** Mitigation: preserved verbatim at `docs/design/socratink-ux.md` and linked from new DESIGN.md. The new DESIGN.md is *index-not-archive*.
- **Risk: UBIQUITOUS_LANGUAGE.md gets out-of-sync with DESIGN.md §Domain quick-ref.** Mitigation: §Domain holds only 6 terms and is explicitly described as "quick reference; canonical is UBIQUITOUS_LANGUAGE.md."
- **Risk: hooks/agents that load CONTEXT.md silently break.** Mitigation: pre-flight audit (step 1) widens grep beyond markdown. Step 4's user-review gate catches anything missed.
- **Risk: AGENTS.md trim removes ops context.** Mitigation: separate diff review with user before commit.

## Out of scope

- Rewriting ADRs (append-only history)
- Refactoring `agents/` subtree (already agent-native)
- Touching `docs/product/` feature specs (repair-reps, starting-map-flow, etc.)
- Code changes
- New brand or design decisions

## Sanity-check questions for v2

1. Is the "rename current DESIGN.md → `docs/design/socratink-ux.md` and create new slim one at root" move correct, or should the new agent hub get a different name (e.g., DESIGN_HUB.md, AGENT_DESIGN.md) to avoid breaking any existing tooling that expects the current 329-line shape?
2. Should §Voice & interaction model promote the LLM-prompt application explicitly (i.e., a sub-section: "this voice also governs how we author drill prompts and system prompts"), given the Gemini v1 feedback that voice rules govern agent LLM-prompt authoring too?
3. The UBIQUITOUS_LANGUAGE.md drift report (Section 2026-05-12) is interesting embedded canon. Should it move to its own file (`docs/project/language-drift-report.md`), or stay inline in UBIQUITOUS_LANGUAGE.md as evidence the language is being actively monitored?
