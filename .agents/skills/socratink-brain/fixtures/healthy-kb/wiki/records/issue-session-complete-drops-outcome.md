---
title: "Session Complete Drops Outcome"
type: issue
updated: 2026-04-08
sources: [../sources/drill-chat-log-thermostat-session-1.md]
related: [decision-time-gate-policy.md, ../mechanisms/three-phase-node-loop.md]
basis: sourced
confidence: high
workflow_status: open
flags: []
---

# Session Complete Drops Outcome

## What Broke
A resolving turn can end a session without persisting the node outcome.

## Evidence
The behavior is captured in the drill-derived source material and related debugging notes.

## Product Implication
Session-ending logic must not override truthful node-state persistence.
