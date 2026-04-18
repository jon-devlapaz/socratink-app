# Index

## System
- [Socratink Log Coverage](log-coverage.md) — Current chat and test coverage manifest

## Concepts
- [Desirable Difficulty](concepts/desirable-difficulty.md) — Productive struggle that produces stronger learning; theoretical foundation for cold-attempt-first design
- [Bloom's Taxonomy](concepts/blooms-taxonomy.md) — Cognitive hierarchy from Remember to Create; vocabulary for what drill depth actually means and what Socratic questioning targets
- [Zone of Proximal Development](concepts/zone-of-proximal-development.md) — Vygotsky's scaffolded gap between independent and assisted performance; informs AI drill partner behavior and node state progression
- [Testing Effect](concepts/testing-effect.md) — Active retrieval beats restudy at delay (Roediger & Karpicke 2006; Rowland 2014 g≈0.50); feedback-after-failure is the load-bearing moderator
- [Spacing Effect](concepts/spacing-effect.md) — Distributed practice beats massed (Cepeda 2006/2008 ridgeline); anchors `solidified` operational definition and `re_drill_band` policy
- [Generation Effect](concepts/generation-effect.md) — Producing beats reading (Slamecka & Graf 1978; Bertsch 2007 d≈0.40, ≈0.64 at >1d); foundational citation for Generation Before Recognition
- [Tetris Effect and Schema Consolidation](concepts/tetris-effect-schema-consolidation.md) — Tetris effect runs on procedural memory, not declarative; valid product metaphor, not a mechanism claim; real schema-integration substrate is spacing + GBR + interleaving

## Mechanisms
- [External Audit Triage Loop](mechanisms/external-audit-triage-loop.md) — How external critique becomes durable memory instead of backlog sprawl

## Records
- [External Audit Promotion Policy](records/decision-external-audit-promotion-policy.md) — Only validated, release-relevant signal becomes active work
- [Action Potential Fixture Solid Re-Drill](records/finding-action-potential-fixture-solid-redrill.md) — Sandbox fixture evidence for one solid re-drill path, not full-loop validation
- [Hosted Cold Attempt Transcript Evidence](records/finding-hosted-cold-attempt-transcript-evidence.md) — Production Vercel transcript evidence for one unscored cold-attempt path, not full-loop validation
- [Replay Coverage Below Truth Bar](records/issue-replay-coverage-below-truth-bar.md) — Closed: replay mechanism verified, automated tests deferred to DB milestone

## Sources
- [ChatGPT Repo Audit 2026-04-08](sources/product-chat-log-chatgpt-repo-audit-2026-04-08.md) — External repo evaluation stored as a raw artifact plus curated source page
- [Cluster-Hosted Rebuild Run Product Chat 2026-04-14](sources/product-chat-log-cluster-hosted-rebuild-run-2026-04-14.md) — Deferred feature idea for a cluster-hosted, child-node-resolved Rebuild Run
- [Action Potential Fixture Drill Run Log 2026-04-12](sources/drill-run-log-action-potential-fixture-2026-04-12.md) — Run-level drill telemetry for one sandbox solid re-drill fixture
- [Action Potential Fixture Drill Turn Log 2026-04-12](sources/drill-turn-log-action-potential-fixture-2026-04-12.md) — Turn-level drill telemetry for one sandbox solid re-drill fixture
- [Hosted Modularity Cold Attempt Drill Chat Log 2026-04-12](sources/drill-chat-log-hosted-modularity-cold-attempt-2026-04-12.md) — Production Vercel transcript evidence for one cold-attempt session plus duplicate and empty export artifacts
- [Happy Path Workflow for Human Memory Recall](sources/research-note-happy-path-workflow-human-memory-recall-product.md) — Secondary research note on recall-first product workflow and feedback patterns
- [Testing Effect Research Note](sources/research-note-testing-effect.md) — Primary-source coverage of testing/retrieval-practice literature including Rowland 2014 meta-analysis and Van Gog/Sweller debate
- [Spacing Effect Research Note](sources/research-note-spacing-effect.md) — Primary-source coverage of distributed-practice literature including Cepeda meta-analyses and the expanding-vs-uniform debate
- [Generation Effect Research Note](sources/research-note-generation-effect.md) — Primary-source coverage of generation-effect literature including Slamecka & Graf, Bertsch meta-analysis, errorful-generation, expertise reversal counterweight
- [Theta Research: Tetris Effect and Learning Science (2026-04-17)](sources/research-note-theta-tetris-effect-2026-04-17.md) — Neurocognitive note rejecting Tetris-effect mechanism framing for declarative learning; confirms spacing + GBR + interleaving as the real substrate
- [Desirable Difficulty Research Note](sources/research-note-desirable-difficulty.md) — Primary-literature review (Bjork 1994; New Theory of Disuse 1992; Bjork & Bjork 2011) grounding GBR, unscored cold attempt, and spaced-re-drill-only solidification; flags expertise reversal, metacognitive resistance, and UI-disfluency non-replication as product risks
- [Bloom's Taxonomy Research Note](sources/research-note-blooms-taxonomy.md) — Primary-literature review establishing Bloom's as pedagogical classification (not cognitive mechanism); Krathwohl 2002 weakens hierarchy claim; Stanny 2016 flags inter-rater reliability limits for using Bloom's-level as analytics key
- [Zone of Proximal Development Research Note](sources/research-note-zone-of-proximal-development.md) — Primary-literature review: Vygotsky 1978 frame, Wood-Bruner-Ross 1976 scaffolding attribution, van de Pol 2010, VanLehn 2011 d≈0.79 tutoring effect (replacing Bloom 1984 2-sigma); constrains Socratink to adaptive, provably-fading scaffolding
- [Product Spec (canonical)](sources/product-doc-spec.md) — Binding design and implementation contract: three-phase loop, four-state model, panel modes, traversal, guardrails, evaluation checklist
- [UX Framework (canonical)](sources/product-doc-ux-framework.md) — Metacognitive UX philosophy, reward/sensory rules, attribution management, session guardrails, ethical engagement, evidence posture
- [Evidence-Weighted Map Doctrine (canonical, overrides)](sources/product-doc-evidence-weighted-map.md) — Binding doctrine on graph-truth claims; overrides every other binding doc on what the graph may claim
- [Post-Drill UX Spec (implementation)](sources/product-doc-post-drill-ux-spec.md) — Post-phase panel copy, result-state visuals, sensory treatment, transcript policy, tier/band trajectory display
- [Progressive Disclosure (implementation)](sources/product-doc-progressive-disclosure.md) — Four-state model implementation: state transitions, persisted fields, phase tracking, drill contract, routing, progression layers
- [Repair Reps Card-Stack Spec (implementation)](sources/product-doc-repair-reps-card-stack.md) — Visual-only card-deck metaphor for Repair Reps UI; deal/flip/settle animations
- [Repair Reps Focused Mode Spec (implementation)](sources/product-doc-repair-reps-focused-mode.md) — Focused-workbench layout and copy for Repair Reps; never mutates graph state
- [Repair Reps Self-Rating Spec (implementation)](sources/product-doc-repair-reps-self-rating.md) — Learner self-rating step (close_match/partial/missed); never AI-scored, never graph-mutating
- [Starting Map Flow Artifact (storyboard, non-binding)](sources/product-doc-starting-map-flow-artifact.md) — Seven-screen storyboard for metacognitive concept-entry happy path; starting map is anchor not diagnostic
- [Project State (release-gate)](sources/product-doc-project-state.md) — Current release gate, stage, priorities, active risks, product constraints; consolidated by socratinker
- [Operations & Stabilization (release-gate)](sources/product-doc-project-operations.md) — Merge standard, six release checks, evidence policy, near-term engineering priorities
- [MVP Happy Path (release-gate)](sources/product-doc-mvp-happy-path.md) — Narrow manual ship gate for the thermostat loop; eight-step happy path + go/no-go criteria
- [Auth Rollout (implementation)](sources/product-doc-auth-rollout.md) — WorkOS AuthKit phased rollout with release gates; guest mode preserved
- [Docs Registry (doc-map)](sources/product-doc-doc-map.md) — Inventory of every doc with status/binding flags; precedence rule for evidence-weighted-map override
- [Drill & Graph Engineering (invariants)](sources/product-doc-drill-engineering.md) — Five core invariants for drill/graph state coherence; four-state mutation table; pre-change checklist
- [Drill & Graph Evaluation (manual eval set)](sources/product-doc-drill-evaluation.md) — Smallest useful eval set for thermostat loop; answer modes; obvious-break checklist
- [Theta State (canonical evidence posture)](sources/product-doc-theta-state.md) — Verified product loop, core claim ratings by confidence, phase grounding table, recent decisions, open scientific questions
- [Socratink LLM KB and MemPalace PRD](sources/product-doc-socratink-llm-kb-mempalace-prd.md) — Product-doc proposal for internal KB and learner-facing MemPalace memory integration
- [Ethical Gamification Vision Chat 2026-04-14](sources/product-chat-log-ethical-gamification-vision-2026-04-14.md) — Founder vision for TikTok-level engagement via ethical gamification, social proof maps, and cooperative dungeon runs

## Syntheses
- [External Audit Confirms MVP Priors](syntheses/external-audit-confirms-mvp-priors.md) — The audit mostly confirms existing repo truths and should narrow rather than expand active work
- [Cluster-Hosted Rebuild Run Feature Idea](syntheses/cluster-hosted-rebuild-run-feature-idea.md) — Parked idea: clusters can host Rebuild Runs while scored truth remains child-node-resolved
- [Recall Happy Path Supports MVP Loop](syntheses/recall-happy-path-supports-mvp-loop.md) — Recall happy path reinforces the existing cold attempt, targeted study, and spaced re-drill loop
- [MemPalace KB PRD Is Post-MVP Memory Hypothesis](syntheses/mempalace-kb-prd-is-post-mvp-memory-hypothesis.md) — Preserve MemPalace/KG as a post-MVP memory track until deployment and truthful-graph questions are answered
- [Ethical Gamification Vision and Tensions](syntheses/ethical-gamification-vision-and-tensions.md) — Post-MVP vision: ethical engagement via reconstruction gamification, social proof maps, and cooperative branch-and-converge runs
- [Feedback After Failure Is a Required Scaffold](syntheses/feedback-after-failure-required-scaffold.md) — Testing, spacing, generation literatures all converge: feedback after failure is the single moderator that separates productive struggle from harmful error encoding
