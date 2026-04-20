# Active Release Memory Queue

This file is the only short-form todo surface for Socratink Brain-promoted release work. Every item must move at least one of the three priorities in `docs/project/state.md` forward.

Promotion rules:
- Follow the `ACTIVE.md` contract in `.agents/skills/socratink-brain/SKILL.md`.
- Triage rule: *"If this were completed tomorrow, which state.md priority moves measurably forward?"* If the answer is "none," it does not belong here.

## P1 — Keep graph state and persisted state aligned

- [ ] Fix concept creation silently discarding user input in guest mode.
  Current failure: pasting title + body creates "Thermostat Control Loop" regardless of input, with no error surfaced. Either route to a local fallback extractor OR surface honest UI: *"Guest mode uses sample maps; sign in to extract your own."* Golden-path trust issue.
  Evidence: `.socratink-brain/raw/ux-audits/2026-04-16-full-product.md` (BLOCKER).

- [ ] Fix drill failure surface: add retry + remove backend-detail leak.
  Current error *"The drill service failed to respond. Check the backend or API key and try again"* destroys user trust. Ship a token-backed `.chat-bubble.error` variant with friendlier copy + retry button. Guest mode should ship a local fallback drill.
  Evidence: `.socratink-brain/raw/ux-audits/2026-04-16-full-product.md` (HIGH bug).

## P2 — Improve instrumentation

- [ ] UNBLOCK: stand up a durable telemetry store for hosted drill runs.
  `docs/project/state.md` explicitly flags Vercel serverless file writes as non-durable release evidence. Every P2 item below is blocked until this lands. Options: Supabase events table, external log sink, or managed Postgres. Decision deferred to design pass — but cannot instrument honestly without it.
  Evidence: `docs/project/state.md` Environment Lessons.

- [ ] Event schema additions in cold-attempt → reveal → re-drill flow.
  Land these fields + capture even if dashboards lag: `pre_confidence`, `post_confidence`, `reveal_gated_by` (`confidence` | `attempt` | `help_requested`), `reference_revealed_at`, `self_flagged_spans`, `reflection_attribution`.
  Evidence: `.socratink-brain/raw/ux-audits/2026-04-20-repair-reps-metacog.md` P0 instrumentation.
  Blocked by: durable telemetry store.

- [ ] Capture confidence on cold attempt (unscored) + abandonment-vs-difficulty correlation.
  Kornell & Bjork churn signature. Pre-attempt confidence must not feed scoring — Generation Before Recognition is non-negotiable.
  Evidence: theta research review, Kornell & Bjork on desirable difficulties.
  Blocked by: durable telemetry store.

- [ ] Delayed retention probe instrumentation: +7d / +30d re-drill success controlled for study time.
  The desirable-difficulty signature. Without this, the spaced re-drill claim is not observable.
  Evidence: theta 2026-04-18 review.
  Blocked by: durable telemetry store.

- [ ] Provable scaffolding fade instrumentation across `primed → drilled → solidified`.
  Cue density in re-drill prompts must measurably decrease as state advances. Without this, the scaffolding claim in `docs/product/spec.md` is false. Instrument cue-density metric per re-drill; trend must be non-increasing.
  Evidence: theta 2026-04-18 review; Wood-Bruner-Ross 1976; van de Pol 2010.
  Blocked by: durable telemetry store.

## P3 — Validate hosted behavior before treating local success as done

- [ ] Run hosted happy-path end-to-end on a throwaway account.
  Use `docs/project/mvp-happy-path.md` as the checklist. Document every local/hosted divergence into `.socratink-brain/raw/`. This is the gate itself.
  Evidence: `docs/project/state.md` Current Priorities.

- [ ] Hosted ingestion defense pass.
  (a) YouTube transcript fallback UX when serverless IPs are blocked. (b) SSRF review on external fetch paths. (c) Error-leakage audit on all external-call failure paths. Manual transcript paste remains the hosted fallback per state.md.
  Evidence: `docs/project/state.md` Active Risks.

---

## Archived — not active for current MVP gate

- Metacognitive UX expansion (split textarea, hedge-word detector, two-step reveal, Focus mode, Reflection cards, Calibration tiles) — see `raw/ux-audits/2026-04-20-repair-reps-metacog.md`. Re-promote items after current gate clears.
- Full-product UX polish (token rewiring for dark mode, Analytics tile redesign, Library card unification, focus rings, keyboard/a11y polish) — see `raw/ux-audits/2026-04-16-full-product.md`. Re-promote after current gate clears.
- Supabase migration (Phases 1–9) — see `.planning.post-mvp/ROADMAP.md`. This is post-Build-Measure-Learn work, not current gate work.
- Product-copy hygiene (Bloom attribution, 2-sigma → VanLehn, Vygotsky → Wood-Bruner-Ross) — important for doctrine integrity, not MVP release gate. Park in a dedicated doctrine-cleanup pass.
