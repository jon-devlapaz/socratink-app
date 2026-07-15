# ADR-0005 — LSL is a one-way evidence projection

**Status:** Proposed (2026-07-14)

## Context

[LSL 1.0-draft](https://github.com/learnerstate/LSL/blob/032fd0453cbe426e9a0f4ec553ff5ba1714e2669/SPEC.md)
describes a replaceable snapshot of claims about a learner. Its Core concept
object requires a numeric `mastery` estimate, confidence in that estimate, a
freshness date, and plain-language capability, gap, and misconception lists.
Core documents are unverified claims; provenance and signatures add
auditability or issuer integrity, not truth.

Socratink's canonical state has a different claim boundary. The
[evidence-weighted map doctrine](../product/evidence-weighted-map.md) says the
graph shows what Socratink has evidence for, not what the learner knows. The
browser-local [training store](../../public/js/training-store.js) records
learner text, classifications, gaps, repairs, and timestamps. The pure
[derivation](../../public/js/training-derive.js) produces `null`, `primed`,
`needs repair`, or `solidified`; only spaced strong reconstruction can produce
`solidified`. The [SEDA projection](../../public/js/seda-evidence-projection.js)
re-stamps attempts to real wall-clock time so one simulated session cannot
manufacture spacing.

The formats therefore overlap in evidence and provenance, but not in their
required summary claim. LSL's
[Core schema](https://github.com/learnerstate/LSL/blob/032fd0453cbe426e9a0f4ec553ff5ba1714e2669/schema/lsl-core.schema.json)
requires `concepts[].mastery`. Socratink neither stores nor derives a numeric
mastery estimate, and its four evidence states are not points or bands on the
LSL mastery scale. Any numeric crosswalk would invent a claim the evidence
model does not support.

## Decision

LSL integration is an outbound, one-way, read-only projection over Socratink's
canonical training record and derivation. The projection may summarize
existing evidence; it must never become a second state authority, write back
to the training store, alter derivation, or persist an LSL claim as graph
truth.

No LSL exporter is approved by this ADR. Under 1.0-draft, Socratink cannot emit
a meaningful conforming Core concept without inventing required `mastery`.
An implementation needs a later decision after either LSL permits an
evidence-native concept without numeric mastery or Socratink adopts a
separately justified measurement model. An empty `concepts` array may validate
but does not constitute useful compatibility.

If that blocker is removed, the adapter must read the training record and call
the canonical derivation at projection time. It must not infer state from
legacy graph fields, study exposure, repairs, self-report, or SEDA's simulated
timestamps.

### Field compatibility

"Conditional" means the source evidence and privacy conditions in the final
column must both hold. Unsupported optional fields are omitted; unsupported
required lists are empty. These mappings do not override the numeric-mastery
blocker.

| LSL field | Compatibility | Socratink source and constraint |
| --- | --- | --- |
| `lsl` | Direct | Exact supported LSL version, fixed by the future adapter. |
| `learner` | Conditional | A new opaque, per-export-scope pseudonym. Never expose an email, username, local account key, or reusable global identifier. |
| `updated` | Direct | Projection timestamp; it describes compilation, not new learner evidence. |
| `subject` | Conditional | Learner-visible concept or collection title from the provisional map. Context only. |
| `goals[].objective` / `target` / `by` | Conditional | Learner-declared goal metadata only. Goals remain relevance context and never evidence. Omit fields Socratink did not collect. |
| `concepts[].name` | Conditional | Learner-visible node or concept label. A label identifies the evidence target; it is not evidence itself. |
| `concepts[].id` | Conditional | A deliberately minted export IRI. Do not expose browser storage keys or assume cross-platform concept equivalence. |
| `concepts[].mastery` | **Incompatible and required** | No source. Do not map `null`, `primed`, `needs repair`, `solidified`, classification values, attempt counts, or spacing to a number or LSL band. |
| `concepts[].confidence` | Incompatible while `mastery` is absent | LSL confidence qualifies its mastery estimate. Socratink has grader provenance, not confidence in a numeric ability model. |
| `concepts[].last_seen` | Direct | Maximum `at` timestamp among attempts supporting the exported claim. Study, repair, sketch, and projection time do not count. |
| `concepts[].trend` | Unsupported | Socratink has no declared trend algorithm. Attempt order is not a rising/stable/falling estimate. |
| `concepts[].can[]` | Conditional | Only a narrow factual statement that the learner reconstructed the named mechanism strongly after real spacing, backed by a `solidified` derivation and the contributing attempt. Never say "knows" or "mastered" and never export AI-polished learner text as capability evidence. |
| `concepts[].cannot_yet[]` | Conditional, sensitive | Only a persistent, named gap supported by repeated non-strong reconstruction evidence or an explicit assessment of that mechanism. A single miss, untried material, or a repair prompt is insufficient. Private tutor scope only. |
| `concepts[].misconceptions[]` | Unsupported | `wrong_direction` and gap corrections do not establish a stable false belief. Emit an empty list rather than diagnose one. |
| `teaches_best[]` | Unsupported | Socratink does not derive outcome-backed learning preferences across sessions. |
| `next.learn` / `next.blocked` | Unsupported | Provisional topology and traversal affordances are routing hypotheses, not LSL learner-state claims. |
| `next.review` | Unsupported | `spaced_attempt` means a reconstruction may now count as spaced; it is not a prediction that knowledge has decayed. |
| Provenance `compiled_by` / `sources` | Conditional | Adapter identity and a non-public internal source label. Do not publish local storage locations or source material URLs. |
| Claim `evidence[]` | Conditional, sensitive | Opaque, authorization-checked references to contributing attempts. References must not reveal raw learner text and must not be fetchable by possession alone. |
| Relationships extension | Unsupported | Socratink's graph topology is provisional. LSL v1 relationships have no marker that preserves that distinction. |
| Federation proof | Integrity only | A valid signature may authenticate issuer and bytes. It does not upgrade a claim into Socratink evidence or mastery truth. |

### Received LSL documents

Import is not enabled. If a later feature receives LSL, every field is
untrusted external context, including signed claims. It may, with learner
consent, help select a claim to verify, but it must not:

- append or synthesize attempts, gaps, repairs, or spacing;
- set or influence derived graph state, badges, unlocks, or `next_action`;
- satisfy the cold-attempt gate or reveal answer-shaped content before the
  learner reconstructs;
- merge external concept identity or relationships into the provisional graph
  as fact; or
- be described as evidence Socratink recorded.

Any future import path requires a separate ADR and must re-establish evidence
through Socratink's reconstruction loop.

### Privacy and security

An LSL projection is a portable learner profile and may contain raw strengths,
gaps, goals, and deficit-shaped claims. A future adapter must therefore:

- require an explicit learner action for a named scope and recipient; default
  to private delivery, least privilege, and minimum fields;
- use per-scope pseudonyms and prevent correlation across exports by default;
- exclude raw attempt and repair text unless separately selected by the
  learner; never expose `cannot_yet`, gaps, or misconceptions publicly;
- preserve `updated`, `last_seen`, provenance, and issuer distinctions so stale
  or conflicting claims are not silently flattened;
- validate version, structure, field lengths, list sizes, and total document
  size before any rendering or model use;
- treat all free text as quoted data, not instructions, and keep it outside
  trusted system/developer prompt channels;
- never dereference concept, source, issuer, or evidence URLs merely because
  they appear in a document; any later fetch needs an allowlisted,
  authorization-preserving path; and
- avoid durable logs or caches of the projection unless the learner explicitly
  chose that retention, with deletion and revocation behavior defined first.

## Alternatives considered

- **Map Socratink states to fixed mastery numbers.** Rejected because it
  fabricates precision, makes incomparable states look comparable, and weakens
  the evidence boundary.
- **Treat LSL as a new canonical learner-state store.** Rejected because it
  creates two state authorities and lets summarized claims bypass reconstruction
  evidence and derivation.
- **Import signed LSL claims as evidence.** Rejected because signatures prove
  origin and integrity, not that Socratink observed the learner reconstructing.
- **Emit a useful non-conforming document now.** Rejected because calling it
  LSL would obscure the required-mastery incompatibility. A separately named
  evidence export could be considered under a different decision.

## Consequences

- Socratink can preserve a future interoperability seam without changing
  canonical training state or evidence semantics.
- LSL 1.0-draft Core export remains blocked at the schema boundary; no numeric
  mapping is implied by this ADR.
- Supported prose claims are narrower than LSL's examples and may remain empty
  when Socratink lacks repeat evidence or safe disclosure scope.
- External learner-state claims can guide verification only; they cannot create
  graph truth.
- A future implementation must prove conformance, privacy controls, and
  read-only behavior as a separate bounded slice.
