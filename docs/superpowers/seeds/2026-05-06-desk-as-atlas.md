# Research handoff: "desk as self-contained atlas" — product vision seed

**Date:** 2026-05-06
**Status:** Pre-research seed; literature/prior-art review pending. NOT a feature spec.
**Origin:** Brain-blast moment captured during the Settings-overhaul session.

---

## Read first

You're researching a brain-blast moment for **socratink**, a metacognitive
learning product. The seed below is NOT a feature spec — it's an early
product-vision seed that needs literature, prior-art mapping, and naming
discipline before it's ready to be designed.

**Do NOT write code or specs.** Do NOT propose implementation. Output:

1. A research digest of relevant literature + prior art (linked).
2. A vocabulary proposal — naming conventions for the new concepts the
   seed introduces, with rationale for each choice and rejected alternatives.
3. Open questions that fleshing-out has surfaced.

The user is the product founder. They want this idea cross-referenced
against what already exists, then sharpened with names that match
socratink's voice (calm, precise, Socratic, reading-room not dashboard).

---

## The seed

**Today (v1):**

- A learner has ONE desk. The desk is a 3×3 isometric grid of 9 tiles.
  Each tile holds one *concept* (the learner's chosen domain to understand
  — e.g. "Photosynthesis", "Transformers", "Krebs Cycle").
- Each concept owns a knowledge graph (backbone + clusters + subnodes).
  Drilling happens *inside* one concept's graph; state (`locked → primed
  → drilled → solidified`) is per-node-per-concept.
- Concepts on the desk are independent — they don't share structure or
  resonate across each other. A single desk holds whatever the learner
  has been studying recently, with no thematic constraint.

**The seed (vNext):**

- A desk becomes a **self-contained atlas of related concepts.** The 9-tile
  cap stops being a constraint and becomes the *form* — a desk is a 3×3
  atlas of a coherent territory. ("Biology desk", "ML desk", "Music
  theory desk".)
- A learner has **multiple desks**, each one a coherent atlas.
- Cross-concept resonance ("this hinge appears in 3 other concepts on this
  desk") becomes *meaningful*, scoped to a single desk's territory — no
  identity collisions across unrelated domains.
- The desk is now a thing the learner *names*, *has*, and *returns to*.
  The library becomes an **atlas of atlases**.
- The interleaving bridge (current Screen 6 of the metacognitive happy
  path, today routes within a single concept's graph) can extend to
  route across concepts within the same desk — without violating the
  "earn the state" rule, because the rooms share a coherent map.

**Concrete framing exercise:** picture a returning learner with three
desks — Biology, ML, Music — each a named 3×3 atlas. That's a much more
legible "what I'm trying to know" picture than 9 unsorted concept tiles.

---

## Three load-bearing rules the seed MUST respect

These come from socratink's design system and crystallized memories. Any
research framing or naming proposal that violates one of these is wrong,
no matter how clever:

1. **"Chat is ignition, not the product surface."** Anything that pulls
   the learner *out* of the discrete metacognitive loop (threshold → cold
   attempt → repair → re-drill) and into open-ended navigation is the
   anti-product. The atlas cannot become a Wikipedia-surf surface. If
   "explore the atlas" becomes a competing primary action with "drill the
   room you primed," the loop frays.

2. **Graph state must be earned, not propagated.** When you solidify
   "energy transformation" in Photosynthesis, the same node in Cellular
   Respiration must NOT visibly upgrade to `primed` or `drilled` over
   there — that would be an unearned state claim. Cross-concept resonance
   shows *that* a node is shared, never claims status the learner hasn't
   earned by drilling there.

3. **One active cognitive target.** The current design dims everything
   except the foregrounded thing to 0.5–0.6 opacity at any moment. Atlas
   surfaces that light up "this node also lives in 3 other concepts"
   during the moment of repair would fragment attention. The atlas is a
   *retrospective / reflection* surface — appears AFTER repair, not in
   parallel to it. A cartographer's note in the margin, not a new path.

**The version that survives all three:** atlas as evidence/reflection, not
parallel study mode. After you solidify a node, *then* the atlas shows
"this same hinge lives in two other concepts on this desk — they're still
locked there." Resonance payoff without state propagation, without mid-
loop fragmentation, without unearned drill-readiness.

---

## Research directions — keywords

Cast a wide net. Quote the most relevant sources verbatim where helpful.
Group your findings by direction.

### Learning science

- **Concept maps** (Novak & Cañas, *The Theory Underlying Concept Maps*;
  IHMC CmapTools)
- **Schema theory** (Bartlett, Anderson) — how related concepts cluster
- **Transfer of learning** — near transfer, far transfer, structural
  alignment (Gentner)
- **Interleaving practice** vs blocked practice (Rohrer, Taylor)
- **Spacing effect** (Cepeda et al., Karpicke)
- **Retrieval-induced facilitation** — repair in one concept aiding
  others
- **Elaborative interrogation** and self-explanation (Chi)
- **Cognitive load theory** (Sweller) — particularly extraneous load
  from category-management
- **Encoding specificity** (Tulving) — how is knowledge accessed across
  contexts

### Knowledge representation

- **Knowledge graphs** — node identity, deduplication across domains
- **Ontology alignment / mapping** — how do separate domain ontologies
  share nodes (e.g., "ATP" in biochemistry vs. music)
- **Bipartite graphs**, **multipartite knowledge structures**
- **Semantic similarity** measures — how to decide two nodes are "the
  same hinge"
- **Topic modeling** for concept clustering — how AI might *suggest* a
  desk for a new concept

### HCI / UX patterns and prior art

Compare and contrast each. What metaphor do they use, what are their
units of organization, what's the cross-unit resonance behavior?

- **Heptabase** — visual whiteboard knowledge management; spatial
  organization of cards into "whiteboards"
- **Obsidian** — graph view of all notes; folders / tags; Canvas
  feature
- **Tana** — supertags, workspaces, swipes (workspace concept relevant)
- **Roam Research** — bidirectional links, daily notes
- **RemNote** — spaced repetition + concept hierarchy
- **Logseq** — hierarchical outliner with graph
- **Capacities** — object-based note-taking, "spaces" for grouping
- **Scrintal** — visual workspace for knowledge
- **Notion** — workspace / database / page model
- **Anki** — decks; cross-deck card behavior; tags
- **MIT Open Knowledge Network** — formal cross-domain ontology
- **Andy Matuschak's notes site** + Quartz / digital gardens — public
  knowledge atlases
- **Kindred Beasts** / map-of-content patterns in the PKM community

For each: what's their unit-above-the-card? Do they have nested workspaces
or separate workspaces? Does cross-workspace resonance exist?

### Spatial / cartographic metaphors

- **Method of loci / memory palaces** — spatial scaffolding for memory
- **Korzybski "the map is not the territory"** — the canonical caution
- **Tufte** on small multiples, sparkline grids, spatial information
  density
- **Cognitive cartography** — David Kennedy, Atlases of Mental Maps
- **Topological learning paths** — neuroscience papers on hippocampal
  cognitive maps (O'Keefe, Tolman) — relevance to "navigating a
  knowledge atlas"

### Product naming inspiration vocabulary

For the user to draw from when picking names:

- **Cartographic:** atlas, chart, map, territory, region, basin, terrain,
  ridge, contour, isobar, route, expedition, latitude, meridian
- **Library / archive:** shelf, codex, folio, atlas, manuscript, fascicle,
  scriptorium, fonds
- **Workspace:** desk, room, study, alcove, cabinet, atelier, workshop
- **Astronomical:** constellation, sector, system, neighborhood
- **Botanical:** garden, grove, glade, bed, plot, stand
- **Geological:** stratum, vein, basin, watershed

socratink's voice is **calm, precise, Socratic — reading-room, not
dashboard.** Names that read like they belong in a library or atlas, not
like a SaaS product. Lowercase product name and state tokens are
canonical (`primed`, `drilled`, `solidified`). Avoid jargon hype.

---

## Naming conventions to pin down

The seed introduces concepts that don't have names yet. Propose names for
each, with 2–3 rejected alternatives and rationale. Some of these may
overlap; surface that.

1. **The unit above "concept"**
   Currently called "the library" (singular, holds all concepts). The
   seed wants this to become plural and named. Each one is a
   self-contained atlas of related concepts.
   Candidates: **desk**? **atlas**? **room**? **study**? Note that
   "desk" is already in use as the name of the in-app surface; if the
   new unit is also "desk," there's vocabulary collision (which surface
   is the singular desk vs. plural?).

2. **The plural / collection of these units**
   What's the meta-container? "Library"? "Atlas of atlases"?
   "Bookshelf"? "Cabinet"?

3. **Cross-concept resonance**
   The phenomenon of "this hinge appears in N other concepts on this
   desk." Candidates: **echo**, **resonance**, **vein**, **ridge**,
   **chord**, **lattice**, **thread**, **kindred**.

4. **The reflection / evidence surface that surfaces resonance after
   repair**
   What's it called? "Atlas note"? "Margin note"? "Cartographer's
   note"? "Resonance log"? "Echo trail"? Make sure the name signals
   "this is reflection, not navigation."

5. **The state of a desk** (analogous to concept state)
   Is there a vocabulary? `seeded → tilling → bearing → fallow`? Or
   does the desk inherit aggregate state from its concepts? Or has no
   state of its own (just a name + a 3×3 of concept states)?

6. **The empty-desk affordance**
   Today a learner with no concepts gets a single-desk grid of empty
   tiles with `+` affordances. What does an empty *new desk* look like
   before any concepts? Is creating a desk a separate action from
   creating a concept, or does the first concept on a non-existent
   desk auto-create the desk?

7. **The "all my desks" view**
   The atlas-of-atlases view. What's it called? "Library"? "Map
   room"? "Reading room"? (Note: "reading room" is already the name
   of Settings — vocabulary collision risk again.)

8. **The unit *below* concept** (already named, but worth re-checking)
   Currently "node" / "subnode" / "cluster". Are those names compatible
   with the cartographic frame the seed introduces? Should "node"
   become "room"? Some of the design system already uses "room" loosely
   in copy ("the first room stays quiet").

---

## Open questions to surface (don't try to answer)

1. **Categorization burden.** Today: one desk, drop concepts in.
   Proposed: pick a desk for each new concept. That's mental overhead
   the metacognitive loop doesn't currently impose. AI-suggested desk
   placement could help, but adds AI judgment in the seam between
   threshold and provisional graph — needs research on how this is
   handled in similar products.

2. **Migration.** Existing users have one desk with N random concepts.
   How do they reorganize? Forced sort? Optional? Auto-clustered by AI?

3. **"Desk of everything" / generic catch-all.** Does an "uncategorized"
   desk exist as a default, or is the user always required to name?

4. **Interleaving bridge scope.** Currently routes within a concept.
   Should it route within a desk? Across desks? Just within a concept?
   The seed wants within-desk; need to validate that doesn't break the
   "one cognitive target" rule when the next room is a sibling concept
   rather than a sibling node.

5. **Cross-concept node identity.** When does "ATP" in two concepts on
   the same desk count as the SAME node? Manual link? AI deduplication?
   Embedding similarity threshold?

---

## Output format

Return a single research digest in markdown, with these sections:

```text
## Prior art digest
[Findings grouped by HCI/PKM tool — Heptabase, Obsidian, Tana, etc.
What's their unit-above-card, do they support cross-unit resonance,
what's the metaphor.]

## Learning science digest
[Citations + 1-paragraph summaries of the most relevant findings on
interleaving across vs within domains, schema theory, transfer of
learning, cognitive load of categorization.]

## Knowledge graph / ontology digest
[Citations on node-identity-across-domains, ontology alignment, semantic
similarity. What does the field say about when two nodes are "the same"?]

## Vocabulary proposal
[For each of the 8 naming items above, propose a primary name + 2 rejected
alternatives + one paragraph of rationale. Flag vocabulary collisions
explicitly (e.g., "desk" already exists as in-app surface name).]

## Open questions sharpened
[Restate the 5 open questions with what the research turned up that
informs each — even if the answer is "no precedent found, this is a real
unknown."]

## Recommendation on naming the seed itself
[The brain-blast doesn't have a name yet. Propose one. The seed is about
a desk being a self-contained atlas, multiple desks, cross-concept
resonance scoped within a desk, atlas as reflection surface. What's the
*phrase* the team uses to refer to this entire shape?]
```

Length budget: 2,500–4,000 words. Quality over quantity. If a citation
needs to be paraphrased rather than directly quoted, that's fine — just
flag uncertainty.

When you're done, the user will read your digest, pick names, and maybe
push back on framings. Stay open to the seed evolving.
