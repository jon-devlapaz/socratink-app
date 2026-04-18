---
title: "Spacing Effect"
type: concept
updated: 2026-04-17
sources: [../sources/research-note-spacing-effect.md]
related: [../syntheses/feedback-after-failure-required-scaffold.md, ../concepts/testing-effect.md, ../concepts/desirable-difficulty.md]
basis: sourced
workflow_status: active
flags: []
confidence: high
domain_axes: [learning-science, product-design]
key_researchers: [Nicholas Cepeda, Harold Pashler, Doug Rohrer, Jeffrey Karpicke, Henry Roediger, Robert Bjork]
relevance: foundational
---

# Spacing Effect

## Definition

The spacing effect (distributed practice) is the finding that identical study or retrieval episodes distributed over time produce substantially better long-term retention than the same episodes massed together. It is one of the most robust findings in memory research — replicated across humans and animals, verbal and motor learning, and timescales from seconds to years.

Cepeda et al. (2006) meta-analyzed 839 effect sizes across 317 experiments. Cepeda et al. (2008) established the "temporal ridgeline": optimal interstudy interval (ISI) scales with retention interval (RI). Optimal ISI:RI ratio is ~20–40% for a 1-week test, dropping to ~5–10% for a 1-year test. The "10–20% rule" is a centering tendency, not a sharp peak.

## Key Mechanisms (Hybrid)

- **Study-phase retrieval / reminding** (Benjamin & Tullis 2010): a spaced repetition triggers retrieval of the prior episode, strengthening the trace.
- **Encoding variability** (Glenberg 1979): contextual drift between episodes diversifies retrieval cues.
- **Deficient processing** (Greene 1989): massed repetitions get attenuated attention.
- **Contextual variability**: temporal context drift increases retrieval pathways.

Consensus since Greene (1989): no single mechanism explains the full effect. Study-phase retrieval + deficient processing is the dominant hybrid account.

## Boundary Conditions

- **Immediate testing**: massed practice equals or beats spacing on same-session tests. Spacing's advantage emerges only at delay.
- **Very short lags** (<5% of RI): benefit shrinks toward zero.
- **Very long lags** (ISI >> RI): retrieval at the second episode fails, the trace is effectively re-learned, and the curve drops.
- **Highly complex tasks**: Donovan & Radosevich (1999) found small effects for tasks like flight simulation; element interactivity moderates.
- **Item difficulty asymmetry** (Pyc & Rawson 2009): difficult items benefit from shorter ISIs before being spaced out; easy items tolerate wider gaps. *Successful effortful* retrieval is what matters — failed retrievals at long lags can hurt.
- **Motor learning**: spacing effects exist but are modulated by skill complexity and consolidation windows; not a clean transfer of verbal-recall findings.

## Open Debate: Expanding vs. Uniform Schedules

This debate directly affects Socratink's `re_drill_band` design.

- **Landauer & Bjork (1978)** founding result: *expanding* retrieval (1 min → 5 min → 25 min) is optimal. Foundation of SuperMemo/Anki.
- **Karpicke & Roediger (2007)**: tested expanding vs. equal-interval. Expanding won on *immediate* tests but uniform spacing won at 2-day delay. Their interpretation: expanding's first retrieval comes too soon, before working-memory clearance.
- **Storm, Bjork & Storm (2010)**: expanding *can* beat uniform at 1-week delay, but only with high-interference tasks intervening.
- **Cepeda et al. (2006)**: expanding > uniform in 22 comparisons, but very large between-study variance — "noisy enough to be unsafe to design on."

The literature does *not* unambiguously support expanding for long retention.

## Why This Matters for Socratink

- **`solidified` operational definition (proposed):** ≥3 successful re-drills, across ≥2 distinct calendar days, with the final success at ≥7 days after most recent prior success. Without this, `solidified` cannot honestly claim durability.

- **MVP schedule shape:** quasi-uniform with a slight expanding tail (e.g., 1d → 4d → 10d → 21d) hedges both findings and avoids Karpicke & Roediger's "first retrieval too soon" failure mode. Aggressive doubling without instrumentation is unjustified by the evidence.

- **Same-session re-drills are massed, not spaced.** They yield no spacing benefit. If `re_drill_count` increments without a calendar-time gate, the count is meaningless as evidence of durability.

- **Retention target should be explicit per concept** (or default to ~30 days). Intervals derive from the target via Cepeda's ratio — don't pick intervals first.

- **`re_drill_band` should encode the gap that produced the success**, not just an ordinal rank — the band must carry diagnostic information.

**Required instrumentation:** per-drill `timestamp_utc` and `gap_since_prior_drill_hours`; binary `retrieval_success`; `final_test_lag_days` for any post-solidified probe; a 7d/30d retention probe on a sample of solidified nodes — the only direct evidence the system is working.

**Important uncertainty:** optimal intervals for *Socratic conversational drill* (vs. flashcard cued recall) are not directly studied. Treat 1d/4d/10d/21d as a prior, not a settled answer.

## Source

- [Spacing Effect Research Note](../sources/research-note-spacing-effect.md) — full primary-source coverage including Cepeda meta-analyses, the expanding-vs-uniform debate, instrumentation proposals.
