---
title: "Zone of Proximal Development Research Note"
type: source
updated: 2026-04-18
sources: []
related: [../concepts/zone-of-proximal-development.md, ../concepts/desirable-difficulty.md, ../concepts/blooms-taxonomy.md]
basis: sourced
workflow_status: active
flags: [open-question]
source_kind: research-note
raw_artifacts: [raw/research-notes/2026-04-18-zone-of-proximal-development.md]
log_surface: none
evaluated_sessions: 0
evaluated_runs: 0
---

# Zone of Proximal Development Research Note

## Summary

This source is the 2026-04-18 theta primary-literature review of the Zone of Proximal Development. Vygotsky introduced the concept in *Mind in Society* (1978, the English-translation compilation of work originally from the 1930s), but the note's load-bearing correction is that **the practical evidence base Socratink actually relies on is the scaffolding literature — not Vygotsky directly**.

The note's three critical corrections to the current concept page:

1. **"More knowledgeable other" and "scaffolding" are not Vygotsky's terms.** Scaffolding was introduced by Wood, Bruner & Ross (1976), *Journal of Child Psychology and Psychiatry*, in the context of parent-child tutoring. "More knowledgeable other" (MKO) is a Western pedagogy simplification that does not appear in Vygotsky's original writing. Citing these concepts as Vygotsky's risks misattribution. The modern empirical basis is van de Pol, Volman & Beishuizen (2010) review on scaffolding in teacher-student interaction, and VanLehn (2011) on human tutoring effects.

2. **The tutoring-effect claim that Socratink rides on is VanLehn 2011, not Bloom 1984.** Bloom's famous "2 sigma problem" claim (one-on-one tutoring produces a 2-standard-deviation improvement over classroom instruction) has not replicated at that magnitude. VanLehn (2011), *Educational Psychologist*, meta-analyzed human tutoring effects and found d ≈ 0.79 — substantially smaller than 2 sigma but still a meaningful and replicable effect. Any Socratink messaging about the strength of one-on-one Socratic tutoring should cite VanLehn's number, not Bloom's.

3. **AI scaffolding must actually fade across re-drills to claim ZPD-consistent design.** The scaffolding literature is explicit that scaffolding is only scaffolding if it is gradually withdrawn. A drill system that provides equally heavy hints on every re-drill is not scaffolding — it is permanent support, which does not drive internalization. This is a structural constraint on Socratink's re-drill prompt design: cue density should provably decrease from `primed → drilled → solidified`, and this should be instrumented.

Two further constraints: ZPD is defined relative to what the learner can do *with appropriate support*, so Socratink must explicitly handle outside-ZPD and zero-schema cases rather than treating every cold attempt as in-ZPD. The evidence on AI tutors specifically (VanLehn's human-vs-intelligent-tutoring comparison) is that well-designed intelligent tutoring systems approach human tutoring effect sizes, but only when scaffolding actually adapts to the learner's current state — static hint generation does not clear the bar.

The note's framing for Socratink: treat ZPD as a design constraint (scaffolding must adapt and must fade), not as a descriptive label on node states. Replace Bloom 1984 "2 sigma" language with VanLehn 2011 numbers anywhere that claim appears. Ground the "more knowledgeable other" / scaffolding vocabulary in Wood-Bruner-Ross 1976 and van de Pol 2010 rather than Vygotsky directly.

## Raw Artifacts
- `raw/research-notes/2026-04-18-zone-of-proximal-development.md`

## Connections
- Concept page: [Zone of Proximal Development](../concepts/zone-of-proximal-development.md)
- Related concepts: [Desirable Difficulty](../concepts/desirable-difficulty.md), [Bloom's Taxonomy](../concepts/blooms-taxonomy.md)
