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

### Draft path *(deprecated)*

A card-state label that used to appear on `Reference Concepts` cards meaning
"this pre-prepared seed hasn't been imported into your library yet." Removed
along with the seeding mechanism in ADR-0004. The phrase has no referent in
the current product and should not be reintroduced.
