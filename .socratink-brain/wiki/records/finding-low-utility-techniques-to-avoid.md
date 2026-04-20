---
title: "Low-Utility Techniques to Avoid"
type: finding
updated: 2026-04-18
related:
  - ../sources/research-note-dunlosky2013.md
  - ../concepts/testing-effect.md
  - ../concepts/spacing-effect.md
  - ../concepts/generation-effect.md
basis: sourced
workflow_status: open
flags: []
sources:
  - sources/research-note-dunlosky2013.md
confidence: high
---

# Low-Utility Techniques to Avoid

## Finding

Dunlosky et al. (2013) rate five common learning techniques as **low utility**: summarization, highlighting/underlining, keyword mnemonic, imagery use for text, and rereading. The monograph explicitly notes these are among the techniques students most commonly self-report using — creating a systematic learner-self-selection problem where intuition points learners toward the least-evidence-backed methods.

Socratink's three-phase loop already encodes the positive case (practice testing + distributed practice, Dunlosky's two HIGH-utility techniques). The negative case — what socratink must NOT default to — has not previously been explicit in the knowledge base.

## Evidence

Primary evidence: Dunlosky et al. 2013 monograph, *Psychological Science in the Public Interest* 14(1), 4–58. Utility ratings are methodological, integrating breadth of evidence (ages, materials, retention intervals, educational contexts) with magnitude of effect. Full raw note at `raw/research-notes/dunlosky2013.md`.

Convergent evidence from existing KB:
- [Generation Effect](../concepts/generation-effect.md) — Slamecka & Graf 1978, Bertsch 2007 (d≈0.40) establish that producing beats reading. Rereading-heavy review directly violates this.
- [Testing Effect](../concepts/testing-effect.md) — Roediger & Karpicke 2006, Rowland 2014 (g≈0.50) establish that retrieval beats restudy at delay.

Five low-utility techniques named:
1. **Rereading** — students most common habit; low retention benefit vs retrieval practice; direct conflict with Generation Before Recognition doctrine.
2. **Highlighting / underlining** — minimal encoding benefit; creates illusion of mastery without retrieval work.
3. **Summarization** — effortful but transfers poorly; quality varies widely with summarization skill.
4. **Keyword mnemonic** — specific to some memorization tasks (e.g., vocabulary pairings); does not generalize.
5. **Imagery use for text** — limited to visualizable content; not suitable for abstract clinical-reasoning material.

## Product Implication

Socratink must **actively steer learners away from these five techniques even when learners request them**. Rereading-heavy review flows, highlight-based "study" modes, and summary-generation features would ship evidence-disadvantaged mechanics dressed up as learning.

Specific product constraints this finding implies:
- Post-drill review panels should not become rereading surfaces. If learner pulls up transcript, surface retrieval cues (blurred answers, cloze deletions) rather than static text.
- Do not build highlight / annotation features in the drill content pane as a study mechanic. Annotation is a notes feature, not a learning mechanic.
- Do not let AI generate summaries as the default "learn this node" action. If summarization is offered, frame it as orientation (phase-1 encoding) not review (phase-4 consolidation).
- Marketing and onboarding copy should not promise "we'll highlight the important parts" or similar low-utility framing. Lead with retrieval + spacing.

This is a **negative doctrine** addition: it constrains what socratink must not do, complementing the positive doctrine (practice testing + spaced retrieval + generation-first) already in the knowledge base.
