# socratink — Domain Context

This file captures the domain language used in socratink. Terms here are
canonical; if the code or copy disagrees with this file, the code or copy
is wrong unless this file gets updated first.

## Glossary

### Library
The surface where a user sees their **own** reconstructed work — concepts they
have authored (or imported) and then put their own evidence into through the
reconstruction loop. Library is not a content catalog, a sample shelf, or a
browseable archive of pre-made material; it is the visible record of *what
this user can reconstruct from memory under spacing*.

The trust signal of Library is what gives "your library shows what you've
reconstructed, not what you've saved" its weight. Anything that dilutes that
signal — pre-loaded sample paths shown side-by-side with the user's own
work, "saved articles" patterns, etc. — does not belong on this surface.

*(Resolved 2026-05-09 during library-landing grilling session. Reference
Concepts seeding was previously rendered alongside Your Library; the
register read as paternalistic in persona testing and contradicted this
definition. See [ADR-0004](docs/adr/0004-library-is-users-work-only.md).)*

### Confusion artifact

A concrete piece of material the user already has in hand that represents
their own confusion or incompleteness — a textbook paragraph they re-read
three times, a practice question they missed, a lecture note that didn't
land, a code snippet they couldn't write, a homework problem they couldn't
finish. socratink's entry-point primitive: the user pastes a confusion
artifact, socratink extracts the **principle** the confusion is pointing
at, and the user cold-attempts that principle.

A confusion artifact is *not* content to be consumed. It is evidence of
where the user's mental model is incomplete. This distinguishes the entry
from the rejected catalog patterns: a Reference Concept (ADR-0004) was
content the system supplied; a confusion artifact is evidence the user
supplies. The artifact answers the question *"what should we work on?"*
with the user's own friction, not the system's curation.

*(Resolved 2026-05-10 during empirical-grill session on first-run
scaffolding. The persona's option F was framed narrowly as "a multiple-
choice practice question you missed"; user instinct generalized it to any
artifact of confusion. See `docs/research/2026-05-10-first-run-scaffolding.md`.)*

**Audience note:** "Confusion artifact" is an *internal-team term*. User-
facing copy should use the concrete form ("paste something that confused
you", "a textbook paragraph", "a question you missed"), not the abstract
noun. If the abstract noun appears in product surfaces, that's a register
violation — it'll read clinical.

### Draft path *(deprecated)*

A card-state label that used to appear on `Reference Concepts` cards meaning
"this pre-prepared seed hasn't been imported into your library yet." Removed
along with the seeding mechanism in ADR-0004. The phrase has no referent in
the current product and should not be reintroduced.
