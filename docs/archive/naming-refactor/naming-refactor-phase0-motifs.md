# Motif candidates for socratink vernacular revamp

> Phase 0 deliverable for `naming-refactor-prompt.md`. Output only — no code edits.
> The user picks one (or rejects all) before Phase 1 begins.

## Sources read

- `PRODUCT.md` — register, anti-references, design principles.
- `UBIQUITOUS_LANGUAGE.md` — domain nouns and aliases-to-avoid.
- `DESIGN.md` — seven-screen happy path, dungeon-map metaphor, copy voice, what socratink refuses to be.
- `docs/design/socratink-design-system.md` and `brand-reference.md` — palette, type, motif, tone-by-surface.
- `docs/adr/` (0001 provisional-map-typed-contract, 0002 llm-seam, 0003 retriable-error-marker — none constrain naming).

---

## Candidate A: Reading Room and Field Journal

**Character.** Scholarly-naturalist register — Audubon's notebooks, Darwin's marginalia, the patient field biologist who refuses to claim a specimen until a second observation. The visual register matches the already-shipped cream-paper / ink / violet aesthetic: ledger lines, marginalia, archival type, the quiet tutor at the next desk.

**Sample renames (8):**

| Surface | Current | Proposed |
| --- | --- | --- |
| Top-level nav | `Ignition` | `Intake` |
| State-display chip | `solidified` | `recorded` |
| Primary action | `Start Cold Attempt` | `First Pass` |
| Screen heading | `Concept Threshold` | `Starting Sketch` |
| ARIA label | `Toggle sidebar` | `Show concept index` |
| Empty-state heading | `Your Library` | `Your desk is empty` |
| Dungeon-map copy | `the room is primed for study` | `this entry is open for study` |
| State-machine display | `growing` | `in study` |

**Risks (3):**
1. The reading-room register is unmistakable but very quiet — first-time visitors expecting product energy can read it as twee or as a museum app.
2. `Pass` / `Reading` / `Entry` overlap with publishing-software vocabulary; users coming from Notion/Readwise/PDF apps may map the wrong mental model.
3. Anchors heavily on a print-culture metaphor that doesn't always shrink cleanly to mobile chrome — at 320px a state chip reading `Ready for first pass` is fine; a screen reader announcing `Your desk is empty, no entries yet` is verbose.

---

## Candidate B: Cartographer's Field

**Character.** Maps and expedition — the learner is the cartographer of their own understanding; concepts are sites; the cold attempt is a first sighting; spaced re-drill is the return survey. The register stays *dry surveyor* (USGS field manual, nautical chart), never *romantic explorer* — no expedition-as-adventure, no frontier vocabulary.

**Sample renames (8):**

| Surface | Current | Proposed |
| --- | --- | --- |
| Top-level nav | `Ignition` | `New Bearing` |
| State-display chip | `solidified` | `charted` |
| Primary action | `Start Cold Attempt` | `First Sighting` |
| Screen heading | `Concept Threshold` | `Bearing Sketch` |
| ARIA label | `Toggle sidebar` | `Show field map` |
| Empty-state heading | `Your Library` | `No bearings yet` |
| Dungeon-map copy | `the room is primed for study` | `this site is open for survey` |
| State-machine display | `growing` | `sighted` |

**Risks (3):**
1. Mapping vocabulary risks colonial-explorer overtones if pushed too far. The motif must stay surveyor-flat; one slip into `expedition` / `frontier` / `discovery` collapses the register.
2. New nouns (`site`, `bearing`, `survey`) need glossary support — first-time learners may not parse `First Sighting` as "the unscored attempt that creates evidence to repair."
3. **Subtle invariant collision.** A *map* of *places* implies the places exist before you arrive. This can quietly imply pre-existing knowledge, which fights the binding *graph-is-evidence, not knowledge* invariant. The motif must be paired with copy that frames sites as **proposed locations** until visited — otherwise the brand starts claiming things it cannot.

---

## Candidate C: Crystal Lattice

**Character.** The shipped crystal motif extended to its full lapidary vocabulary. Concepts are crystals on a lattice; the cold attempt is a first cut; study reveals an inclusion (a flaw made inspectable); spaced re-drill is the cleavage test along the grain. Mineralogical and exact — the register of a museum geology cabinet, not a jewelry brand.

**Sample renames (8):**

| Surface | Current | Proposed |
| --- | --- | --- |
| Top-level nav | `Ignition` | `Seed` |
| State-display chip | `solidified` | `crystallized` |
| Primary action | `Start Cold Attempt` | `First Cut` |
| Screen heading | `Concept Threshold` | `Seed Sketch` |
| ARIA label | `Toggle sidebar` | `Show lattice` |
| Empty-state heading | `Your Library` | `The lattice is empty` |
| Dungeon-map copy | `the room is primed for study` | `this facet is ready for study` |
| State-machine display | `growing` | `facet forming` |

**Risks (3):**
1. Single-motif saturation. Pushing every noun onto `crystal / facet / lattice` flattens variety; screen readers begin to sound like a gem catalog (`show lattice`, `first cut on facet four`, `crystal four crystallized`).
2. Lapidary double meanings. `inclusion` reads as DEI/accessibility in product copy. `cleavage` is geologically correct but uncomfortable in learner UI. `cut` can sound surgical. Each must be argued per-row, not adopted wholesale.
3. The crystal already does the visual heavy lifting. Pushing it linguistically too can over-determine the brand — the surface stops sounding like a tutor and starts sounding like a museum label. A scholarly counter-register (margin notes, arrows, annotations) is needed *inside* the motif to keep variety alive.

---

## Recommendation

**Candidate A (Reading Room and Field Journal)** is the best fit for socratink as it stands today.

The product already half-speaks this register: `field journal` is the binding term for Repair History (Screen 7); `starting sketch` is a defined domain noun in `UBIQUITOUS_LANGUAGE.md`; "reading room, not dashboard" is the load-bearing voice rule in `DESIGN.md §10`. Adopting this motif is closer to *finishing the voice* than to introducing a new one — and a finished voice has the lowest blast radius across marketing, in-app, ARIA, and email surfaces.

**Use Candidate B if** the user wants the IA to lean harder on `Map` as the product's spine, and is willing to pay the *graph-as-pre-existing-places* invariant cost with disciplined copy. **Use Candidate C if** the user wants the crystal motif to govern copy as completely as it governs visuals — accepting the saturation risk and the ARIA monotony.

---

## Open questions for the user before Phase 1

1. **Dungeon-map vocabulary fate.** `room / dungeon / boss fight` is the binding internal designer metaphor (`DESIGN.md §2`). Default assumption: it survives as designer-only language and learner-visible uses get rewritten by the chosen motif. Confirm — or do you also want to retire it from designer docs?
2. **`Ignition` retention.** `Ignition` is a defined IA route in `UBIQUITOUS_LANGUAGE.md`. Default assumption: the *display label* is renameable in learner copy while `ignition` stays as the route identifier and code-side noun. Confirm.
3. **State-token display labels — scope.** Code tokens (`locked`, `primed`, `drilled`, `solidified`) stay. Are all four open for *display-label* rename, or only the ones that visibly strain the chosen motif? Default assumption: all four are open, evaluated per row.
4. **Mobile chip width.** Maximum character count at iPhone SE 320px? Eight is safe; some candidates above (`crystallized`, `Your desk is empty`) push toward twelve. A hard ceiling here narrows Phase 1 proposals.
5. **Tagline policy.** Pre-discovered finding flags `socratink — the Socratic Canvas` for replacement (`public/login.html:11`). Do you want a tagline at all in the chosen motif, on which surfaces, or do you prefer no-tagline / `socratink — sign in`?
6. **`tink it` CTA verb.** Brand reference cites `tink it` as a sanctioned lowercase verb. Is it in scope for this refactor (a candidate for replacement) or fixed alongside `socratink`?
7. **Dark-mode-graph copy.** The dark-mode graph patch introduces visual idioms (`obsidian stage`, `seam-of-light`, `starfield`) that read as crystalline. Should the chosen motif extend into dark-mode copy too, or does dark mode keep the crystal-heavy vocabulary regardless?
