# Log

## [2026-04-08] init | External audit intake
Created a minimal Socratink Brain knowledge base for ingesting external repo audits and promoting only validated release-relevant signal.

## [2026-04-08] ingest | ChatGPT repo audit
Added a source page for the external audit, promoted replay coverage as the only active release-facing issue, and recorded that persistence remains a strategic gap rather than the immediate MVP gate.

## [2026-04-11] ingest | Happy path recall research note
Registered the recall happy-path note as a raw research artifact, added a source page, and distilled the narrow implication that it reinforces Socratink's existing recall-first MVP loop without expanding the active release gate.

## [2026-04-12] evaluate-logs | Action potential drill fixture
Registered the current drill run and turn logs as raw artifacts, added source pages for the 2026-04-12 action-potential fixture, promoted one finding about the narrow solid re-drill signal, and updated log coverage to distinguish fixture service logs from full endpoint transcript coverage.

## [2026-04-12] evaluate-logs | Hosted cold attempt transcript
Registered the newest hosted Vercel drill-chat exports as one grouped source, promoted a narrow finding for one unscored production cold-attempt path, and updated log coverage to mark duplicate and zero-byte exports as evaluation caveats rather than release proof.

## [2026-04-13] ingest | LLM KB and MemPalace PRD
Registered the MemPalace product-doc PRD as a raw artifact, added a curated source page, and promoted one synthesis that keeps internal Socratink Brain memory separate from a learner-facing post-MVP MemPalace/KG hypothesis.

## [2026-04-13] rename | Socratink Brain architecture
Renamed the product-memory substrate to `.socratink-brain/` and aligned the maintenance skill name with `socratink-brain`. The execution agent is now `socratinker`; Socratink Brain remains storage and compiled product memory rather than an executor.

## [2026-04-14] init | Concepts directory and first seed
Added `wiki/concepts/` to the Brain for founder-critical domain knowledge. Updated CLAUDE.md scope. Seeded with desirable-difficulty — the Bjork framework that underpins cold-attempt-first design, generation before recognition, and spaced re-drill.

## [2026-04-13] lint | Health check and replay issue closure
Closed replay-coverage-below-truth-bar (mechanism verified sound, automated tests deferred to DB milestone). Cleared ACTIVE.md queue. Updated log-coverage to mark replay instrumentation as deferred rather than blocking. Updated index entry to reflect closed status.

## [2026-04-14] ingest | Cluster-hosted Rebuild Run feature idea
Registered the product chat as a raw artifact, added a curated source page, and promoted one synthesis for a deferred cluster-hosted, child-node-resolved Rebuild Run idea. Left ACTIVE.md unchanged because the user explicitly wants to continue measuring runs before implementation.

## [2026-04-14] seed | Bloom's Taxonomy concept
Added Bloom's Taxonomy concept page — the revised Anderson & Krathwohl cognitive hierarchy that gives vocabulary for what drill depth means, what Socratic questioning targets, and how node mechanisms map to cognitive levels. Cross-linked with desirable difficulty and ZPD.

## [2026-04-14] seed | Zone of Proximal Development concept
Added ZPD concept page — Vygotsky's scaffolded learning gap that maps directly to how the AI drill partner scaffolds within the learner's reach and how node states track internalization. Cross-linked with desirable difficulty.

## [2026-04-14] lint | Brain validator warning cleanup
Changed the replay coverage issue workflow status from the non-schema value `closed` to `resolved`. Added a raw provenance note for the missing 2026-04-08 ChatGPT repo-audit transcript and updated the source page to point at that note while preserving the provenance limitation.

## [2026-04-17] ingest | Theta tetris-effect research note
Registered the 2026-04-17 theta research note on the Tetris effect as an already-present raw artifact, rewrote the source page to match the contract schema (frontmatter + Summary / Raw Artifacts / Connections sections), and aligned the companion concept page `tetris-effect-schema-consolidation.md` to the existing concepts/ frontmatter convention. Derived implication: Tetris effect holds as product metaphor but is not a valid mechanism claim for declarative learning — spacing, GBR, and interleaving remain the real substrate. Does not affect ACTIVE.md (foundational learning-science context, not release-gate).

## [2026-04-18] prune | Zero-byte orphan raw artifacts
Deleted 7 zero-byte raw files with no evidential content: 2 mindbank product-chat-log stubs (`2026-04-18-mindbank-mir`, `2026-04-18-mindbank-mirror-gap-distillation.md`) and 5 empty Vercel drill-chat exports (`2026-04-12T074207Z`, `075359Z`, `075629Z`, `220040Z`, `220130Z`). Updated the hosted modularity cold-attempt source page to list only the two non-empty exports (`213919Z`, `220245Z`) as raw artifacts and refreshed `log-coverage.md` so zero-byte Vercel exports are explicitly a non-evidence class going forward. Raw artifact reference rate: 15/15 (was 15/20).

## [2026-04-18] contract | Concepts promoted to first-class page type
Amended the Socratink Brain contract and validator to make `concept` a first-class page type with its own schema (`## Definition` + `## Why This Matters for Socratink`) and workflow states. Migrated all 7 concept frontmatters to the governed shape: the four evidence-backed concepts (generation-effect, testing-effect, spacing-effect, tetris-effect-schema-consolidation) are `basis: sourced` with high/medium confidence; the three unsourced seed concepts (desirable-difficulty, blooms-taxonomy, zone-of-proximal-development) are marked `basis: inferred`, `confidence: speculative`, and `flags: [open-question]` so the epistemic gap is explicit rather than silent. Why this matters for UX: concept pages ground every UX doctrine claim (cold attempt, scaffolded drill, solidified-only-from-spaced-re-drill); bringing them under the contract closes a parallel epistemic track that let UX decisions cite learning-science without provenance. Stats: 40 → 47 curated pages, all reachable, validator clean.

## [2026-04-18] ingest | Seed concepts backed with theta research notes
Registered three theta-authored primary-literature research notes under `raw/research-notes/2026-04-18-{desirable-difficulty, blooms-taxonomy, zone-of-proximal-development}.md`, created matching source pages in `wiki/sources/`, and promoted all three concept pages from `basis: inferred, confidence: speculative, flags: [open-question]` to `basis: sourced` (desirable-difficulty: high confidence; Bloom's and ZPD: medium). Reconciled over-reaching claims on the concept pages per theta's review: (1) Bloom's is reframed as pedagogical classification rather than cognitive mechanism — the state machine is no longer described as a gated Bloom's climb and Stanny 2016 inter-rater reliability issues are flagged against using Bloom's-level as an analytics key; (2) ZPD attribution is corrected — scaffolding and "more knowledgeable other" are cited to Wood-Bruner-Ross 1976 and van de Pol 2010 rather than Vygotsky directly, and any Socratink tutoring-strength claim should cite VanLehn 2011 (d ≈ 0.79) rather than Bloom 1984 "2 sigma"; (3) scaffolding must provably fade across re-drills is promoted from UX intuition to a ZPD design constraint. Desirable-difficulty page gains an explicit Boundary Conditions section surfacing expertise reversal, metacognitive resistance, and disfluency non-replication as first-class product risks. Stats: 47 → 50 curated pages, all reachable, validator clean.
