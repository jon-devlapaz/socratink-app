# ADR-0004 — Library shows only the user's own reconstructed work

**Status:** Accepted (2026-05-09)
**Driver:** Customer-persona test on the library landing surface (round 2, dark mode, full surface) — see `docs/codex/customer-persona-prompt-template.md` for the methodology.

## Context

The Library page rendered two sections side-by-side:

1. **Reference Concepts** — a hard-coded array (`BUILT_IN_LIBRARY_CONCEPTS` in `public/js/app.js`) containing one pre-extracted concept ("Hermes Agent") with a card UI carrying a `+ Add concept` CTA. Clicking it loaded a pre-graphed JSON via `loadLibraryConcept(filename)` and pushed the concept into the user's `learnops_concepts` localStorage with `state: "growing"` — no cold attempt, no extraction, no user evidence. After import the seeded concept was indistinguishable from a self-authored concept.

2. **Your Library** — the user's actual concepts.

The two sections used the same card chrome (`.library-card-vault` with kicker, name, summary, pills, CTA). To a brand-new user with no concepts of their own, the Reference Concepts card was the *dominant* element on the Library landing.

Customer-persona testing (anti-cramming college sophomore, "ink not LED" register) ran twice on this surface:

- **Round 1** (light, partial subsurface): "Drafting Table" register won; no read on the side-by-side composition.
- **Round 2** (dark, full surface): the persona explicitly read Reference Concepts as **paternalistic** in the saas/loud variant ("mandatory course I have to pass to get my XP"), as a **syllabus assignment** in the journal variant, and as a **scaffold / cited source / spare tool on the workbench** only when the chrome was bibliography-style and the page didn't lead with it.

When asked where the seeding mechanism should live if not in Library, the persona unprompted produced a fifth option: **don't seed pre-graphed concepts at all** — let the user paste the raw source text and watch the same extraction pipeline run on it, the same way it would run on their own notes.

## Decision

Library shows **only the user's own reconstructed work**. Pre-prepared sample concepts are removed entirely from the codebase. There is no `BUILT_IN_LIBRARY_CONCEPTS`, no `importLibraryConcept`, no `loadLibraryConcept`, no `hermes_agent.json`, and no Reference Concepts section.

The `Library` term in `CONTEXT.md` is now constrained: *"the visible record of what this user can reconstruct from memory under spacing."* Anything that dilutes that signal — pre-loaded sample paths, "saved articles" patterns, side-by-side curated cards — does not belong on this surface.

A first-run user with no source of their own currently has no built-in sandbox concept. This is intentional: the friction of bringing real learning material is the filter the product wants. A "paste sample text" affordance on Ignition (the persona's option E) is a candidate for a follow-up but is **not** part of this decision — that's a new entry-point question, separate from the question of what Library is.

## Consequences

- **Files removed:** `public/data/library/hermes_agent.json`, `docs/reference/hermes-agent-concept-source.md`, `docs/reference/hermes-agent-docs-manifest.md`, `BUILT_IN_LIBRARY_CONCEPTS` and `importLibraryConcept` in `public/js/app.js`, `loadLibraryConcept` in `public/js/api-client.js`, the `App.importLibraryConcept` namespace export.
- **Files kept:** `.library-card-vault` CSS rules (still used by the user's own concept cards), `getLibraryConceptMeta` (called for user concepts in the non-empty render path), the `Your Library` section render.
- **Tests rewritten:** Three smoke tests in `tests/e2e/test_smoke.py` previously used Hermes Agent as a fixture (not as a feature under test). They now seed a single concept directly into `learnops_concepts` localStorage via a new `_seed_one_concept(page)` helper. No test coverage of real behavior is lost.
- **Term affected:** `draft path` was the card-state label for "this seed hasn't been imported yet." With seeding gone, the term has no referent. It is removed from product copy. Future use of the phrase should be considered legacy.
- **First-run friction:** A user landing on Library with no concepts sees only the empty-state line: *"No concepts yet. Start one at New concept."* They must bring a source. This is the persona-blessed posture; if real-user testing later shows new users bouncing on the friction, follow-up is a separate decision (likely option E from the grill-with-docs session).

## Alternatives considered

- **A — Quiet footer link in Ignition.** Keep the seeding mechanism, relocate the affordance into a "Samples" tab inside the source panel. Cheapest, but preserved the "draft path" jargon and the persona's "pre-baked" smell. Persona ranked second behind D.
- **E — "Paste sample text" button.** Replace the pre-graphed JSON import with a raw-text seed that flows through the same extraction pipeline as user-provided text. Highest alignment with "raw tool, not content library." Persona's unprompted invention. Scoped out of *this* decision because it's a new affordance question, not a Library-meaning question. Tracked as a follow-up candidate.
- **D — Removed entirely (chosen).** Most philosophically honest. Library's trust signal is preserved by deletion, not by relocation. Open question of "where does first-run scaffolding live?" is left for a separate design moment, when there's evidence it matters.

## References

- `CONTEXT.md` — "Library" glossary entry (resolved 2026-05-09).
- `public/_lab/library-empty-variants.NOTES.md` — round-2 persona test results (full surface, dark mode).
- `docs/codex/customer-persona-prompt-template.md` — persona methodology and reusable template.
- `.claude/friction-log.md` (2026-05-09) — relevant prior frictions on partial-surface persona tests.
