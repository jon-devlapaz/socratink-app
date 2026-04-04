# Project State

## Snapshot

- Product: LearnOps-tamagachi
- Current branch focus: MVP delivery with drill flow, graph progression, and hosted deployment hardening
- Active concerns: deployment reliability, onboarding clarity, evidence-backed product framing, and safe AI boundaries
- Hosted runtime: Vercel serverless
- Operational workflow: narrow regressions can now be routed through `docs/codex/hotfix-workflow.md`

## Current Priorities

- stabilize hosted user flows
- refine drill UX and graph progression
- document research support for learning claims
- establish repeatable agent workflows in-repo

## Target User Signals

- Students are overwhelmed by fragmented study stacks and setup-heavy workflows.
- Card-authoring friction is a major abandonment risk, even when learners believe spaced repetition works.
- Many learners distrust AI that collapses the learning act into shortcut answers or cheating-adjacent behavior.
- Students report burnout from high-effort, low-yield habits and still want systems that push real retrieval.
- Accountability, pacing, and emotional regulation matter, but they must not be confused with mastery.

## Positioning

- MVP value proposition: remove prep friction and increase truthful retrieval reps.
- MVP is not an "AI studies for you" product; AI should automate setup, scheduling, provenance, and support around the loop rather than replace generation.
- Desirable AI value: personalization, post-attempt feedback, accessibility, concept rendering, and operator leverage around the truthful learning loop.
- Non-negotiable constraint: AI must not pre-answer the active target, inflate mastery, or become the source of graph progression.

## AI Guardrails

- Privacy, security, and data minimization are product requirements, not later compliance work.
- Model evaluation must be treated as fallible and bias-prone, especially across language, phrasing, and accessibility differences.
- Human teaching or coaching value should be amplified, not replaced.
- Core learner value should remain available without unsustainable model spend.
- Any feature that makes answer outsourcing easier than genuine reconstruction is misaligned.
- Fluent model output must not be treated as self-authenticating truth.

## Open Questions

- which hosted ingestion paths are reliable enough for MVP
- how YouTube and external content ingestion should degrade gracefully
- which product claims should be softened until evidence docs are complete
- which AI-assisted feedback patterns improve learning without leaking answers or lowering the mastery bar
- which AI affordances belong in the learner path versus teacher/operator tooling

## Recent Decisions

### 2026-04-02

- Decision: adopt an explicit AI value-and-risk model inside the UX framework and treat it as part of MVP product doctrine.
- Why: the product needs a clearer shared standard for where AI is desirable and where it would break truth, fairness, privacy, or real learning.
- Consequence: future AI features should be evaluated against generation-before-recognition, truthful graph progression, accessibility, trust, and anti-outsourcing constraints.
- Decision: split the public web surface so the marketing site lives at `socratink.ai` and the hosted product lives at `app.socratink.ai`.
- Why: the product now has distinct landing and app deployments, and collapsing both onto one hostname made routing and positioning ambiguous.
- Consequence: hosted verification and future copy work should treat apex and `app.` as separate surfaces; the landing repo still needs its hardcoded app links updated to the new subdomain.

### 2026-04-03

- Decision: treat post-drill UX as a separate product-spec layer and keep unresolved exits visibly distinct from true mastery.
- Why: `NEXT` can end a session without producing `solid`, and the UI must not let session resolution masquerade as room clearance.
- Consequence: future graph/detail changes should consult `docs/product/post-drill-ux-spec.md` before changing post-drill copy, badges, transcript visibility, or `Continue` behavior.

## Environment Lessons

- Local success is not deployment validation.
- Public host split is now `socratink.ai` for landing and `app.socratink.ai` for the app.
- Hosted YouTube transcript retrieval can fail because YouTube blocks cloud/serverless IPs.
- Current hosted fallback for blocked YouTube transcript retrieval is manual transcript paste.
- External ingestion work must be reviewed for SSRF risk and internal error leakage.
