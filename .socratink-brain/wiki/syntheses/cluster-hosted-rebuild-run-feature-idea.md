---
title: "Cluster-Hosted Rebuild Run Feature Idea"
type: synthesis
updated: 2026-04-14
sources: [../sources/product-chat-log-cluster-hosted-rebuild-run-2026-04-14.md, ../../../docs/product/spec.md, ../../../docs/product/progressive-disclosure.md, ../../../docs/drill/engineering.md, ../../../docs/theta/state.md]
related: []
basis: inferred
confidence: speculative
workflow_status: open
flags: [hypothesis, open-question]
---

# Cluster-Hosted Rebuild Run Feature Idea

## Pattern
Socratink may need a future return-session surface that gives clusters a meaningful learner-facing role without making clusters primary drill targets. The promising shape is **cluster-hosted, node-resolved**: a cluster CTA starts a Rebuild Run, but the actual scored checks remain child-node spaced re-drills.

The learner-facing frame can be:

- CTA: "Rebuild This Cluster"
- Session object: "Rebuild Run"
- Context line during the run: "Rebuild Run - Cluster: {cluster} - Current room: {child node}"

## Evidence
The product contract says Socratink rewards reconstruction rather than exposure or recognition, and `solidified` can only result from spaced re-drill. It also says clusters are containers and synthesis surfaces in MVP, not primary drill targets. See [docs/product/spec.md](../../../docs/product/spec.md).

The implementation-facing progression spec says cluster state is derived from subnode outcomes and that subnodes are the smallest meaningful mechanisms the learner must reconstruct through the full three-phase loop. See [docs/product/progressive-disclosure.md](../../../docs/product/progressive-disclosure.md).

The drill engineering rules require one active node at a time, derived graph state, and derived cluster state. They also prohibit graph mutation, interleaving credit, or mastery unlock from Repair Reps. See [docs/drill/engineering.md](../../../docs/drill/engineering.md).

Theta state rates Generation Before Recognition and spaced retrieval as high-confidence constraints, while warning that recognition-heavy study can create an illusion of competence. See [docs/theta/state.md](../../../docs/theta/state.md).

The source product chat records Theta's and Rob's product-science/product-instinct reads: conventional quizzes are risky; a delayed reconstruction surface can fit; clusters are a good doorway if state truth remains child-node-resolved; the feature should be parked while run measurement continues.

## Inference
A Rebuild Run can be product-distinct from Repair Reps if it is delayed, cluster-framed, and uses existing child-node spaced re-drill mechanics. Repair Reps remain immediate or post-failure practice with reveal and self-rating; Rebuild Run becomes a guided cluster return session that tests whether the learner can reconstruct child mechanisms after spacing/interleaving.

The synthesis prompt at the end should remain unscored unless Socratink later defines a real cluster-level mastery model. Directly scoring a cluster would create a new state machine and risk confusing "integrated reflection" with verified child-node mastery.

## Product Implication
Do not implement this yet. Preserve it as a future feature idea while continuing to measure runs.

If revisited, the smallest safe version should:

- Offer **Rebuild This Cluster** only from an eligible cluster.
- Queue 2-3 eligible child nodes.
- Resolve each scored step through the existing spaced re-drill path bound to a single child `node_id`.
- Keep the active child node explicit at every step.
- Optionally ask one unscored synthesis question after the child checks.
- Derive cluster state from child node outcomes only.
- Avoid learner-facing "quiz," "test," aggregate score, cluster grade, or direct cluster mastery language.
