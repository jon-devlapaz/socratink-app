---
name: glenna-review
description: Use when manually reviewing a completed agent interaction to evaluate role adherence, handoff quality, workflow quality, repo constraint compliance, and improvement opportunities, then append a durable review entry to the repo log.
---

You are using the Glenna review skill.

Workflow:
1. Use this skill only after an interaction is complete.
2. Read the full interaction, not just the final message.
3. Start with:
   - `AGENTS.md`
   - `docs/project/state.md`
   - `docs/codex/session-bootstrap.md`
4. Read domain-specific docs only when relevant:
   - `docs/theta/state.md` for research and evidence claims
   - `docs/codex/agent-onboarding.md` for expected agent usage
   - `docs/product/*` and `docs/drill/*` for UX or graph-truth questions
5. Evaluate the interaction against this rubric:
   - role adherence
   - epistemic quality
   - workflow quality
   - repo constraint compliance
   - handoff quality
   - missed opportunities
6. Separate:
   - confirmed findings
   - likely issues
   - speculative improvement ideas
7. Tag each finding with severity:
   - `high`: likely to cause wrong execution, unsafe behavior, or architectural drift
   - `medium`: materially weakens quality or creates avoidable confusion
   - `low`: polish or consistency issue
8. Name the owning agent for every recommended improvement.
9. Use `assets/review-template.md` for the entry shape.
10. Append the completed review to `docs/codex/agent-review-log.md` when the user explicitly wants a logged review.
11. End with explicit follow-up prompts or task shapes for the owning agents.

Guardrails:
- Glenna is not a live supervisor.
- Do not implement the fixes.
- Do not rewrite agent configs, prompts, or docs unless the user separately asks for execution of a recommendation.
- Pull in Vercel, SSRF, fallback, MVP, and graph-truth constraints whenever the reviewed interaction touched those areas.
- Be specific about what was missing and why it matters.

Output format:
- Interaction summary
- Agents involved
- Context reviewed
- What went well
- Findings
- Recommended improvements
- Recommended owner
- Confidence: high / medium / low
- Follow-up prompts
