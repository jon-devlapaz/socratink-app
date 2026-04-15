# 2026-04-14 Product Chat — Cluster-Hosted Rebuild Run Feature Idea

## Context

The user asked whether a quiz-like feature should exist in Socratink, how it should differ from Repair Reps, and whether it should be offered only for clusters because clusters are containers where no direct drilling happens.

Relevant repo constraints discussed:

- Socratink's core loop is cold attempt -> targeted study -> spaced re-drill.
- Node states are locked -> primed -> drilled -> solidified.
- Generation Before Recognition is non-negotiable.
- The graph must tell the truth.
- Repair Reps are immediate/post-failure causal micro-practice with no scores, no graph mutation, no interleaving credit, and no mastery unlock.
- Clusters are containers and synthesis surfaces in MVP, not primary drill targets.
- Cluster state is derived from child node state.

## Feature Idea

The emerging idea is a cluster-hosted, node-resolved return surface:

- Learner-facing CTA on a cluster: "Rebuild This Cluster."
- Session object name: "Rebuild Run."
- The run queues 2-3 eligible child nodes from the cluster.
- Each scored step remains a normal spaced re-drill bound to exactly one child `node_id`.
- State changes can only happen through existing child-node spaced re-drill semantics: solid -> solidified; non-solid -> drilled.
- After the child-node checks, the product may ask one unscored synthesis prompt about how the mechanisms work together.
- Cluster state remains derived only from child node states; there is no direct cluster mastery mutation.

## Research And Product Rationale

Theta's read was that conventional quizzes are risky because recognition-heavy study can produce an illusion of competence. A quiz-like surface is valid only if it is actually delayed reconstruction after spacing/interleaving, not answer-first recognition.

Rob's read was that the concept is compelling because it gives clusters a real job without lying about mastery: "rebuild the wing" as an experience, "verify each room" as the mechanism. His risk callout was that the learner must not think the cluster itself is being graded. During the run, the interface must preserve one active child node.

The consolidated recommendation was:

> Cluster-hosted Rebuild Run: CTA on a cluster queues 2-3 eligible child-node spaced re-drills, resolves each step by `node_id`, then offers one unscored synthesis prompt. Cluster state remains derived only from child states.

## Decision State

The user liked the idea but explicitly does not want to implement it yet. The current product direction is to save it as a feature idea and continue measuring runs.
