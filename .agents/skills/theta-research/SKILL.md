---
name: theta-research
description: Use when answering questions about the neurocognitive science behind our product, the four-phase learning model, evidence quality, mechanism claims, research-backed product messaging, or when asked "what does the science say about X", "cite evidence for X", or "run a research prompt".
---

You are using the Theta research skill.

Workflow:
1. Start with references/00-index.md.
2. Check references/external-library.md when the needed papers live outside the repo.
3. Use assets/evidence-screen-template.md for quick triage before reading broadly.
4. Use assets/evidence-template.md when creating reusable paper notes.
5. Identify which phase(s) and which papers are relevant.
6. Prefer primary studies and strong review papers when available.
7. Distinguish clearly between:
   - direct evidence
   - indirect evidence
   - hypothesis/speculation
8. When making a product implication, cite the supporting paper notes.
9. If evidence is mixed or weak, say so plainly.
10. Do not invent neuroscientific certainty.
11. Evaluate whether findings warrant promotion to Socratink Brain. If yes, emit the brain_handoff block defined below. If the user says "feed this to Socratink Brain" or "promote this", emit the handoff block even if you would not have promoted autonomously.
12. When creating paper notes via evidence-template.md, also copy the note to `.socratink-brain/raw/research-notes/{citation-slug}.md` so Socratink Brain can trace provenance.

Output format:
- Question
- Relevant phase(s)
- Best evidence
- Limits / contradictions
- Product implication
- Confidence: high / medium / low

Handoff to Socratink Brain:

After producing the answer, apply the promotion gate: does this finding change
doctrine, mechanism, release risk, decision state, or instrumentation truth?

If YES — append this handoff block to your output:

```yaml
brain_handoff:
  page_type: doctrine | mechanism | synthesis | finding
  suggested_title: "slug-name"
  basis: sourced | inferred
  confidence: high | medium | low | speculative
  sources: [paper-notes/relevant-paper.md]
  raw_artifact_path: .socratink-brain/raw/research-notes/{slug}.md
  flags: []
  promotion_reason: "one line why this changes product truth"
```

Mapping rules:
- Novel principle that must remain true in socratink → `page_type: doctrine`
- How a learning/product mechanism actually works → `page_type: mechanism`
- Cross-cutting pattern across multiple papers → `page_type: synthesis`, `basis: inferred`
- Discrete observation from specific evidence → `page_type: finding`
- Claim supported directly by cited papers → `basis: sourced`
- Claim extending beyond direct evidence → `basis: inferred`, consider `flags: [hypothesis]`

If NO — state: "No brain promotion needed. Finding stays in theta references."
