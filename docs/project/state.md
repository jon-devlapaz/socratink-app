# Project State

## Snapshot

- Product: LearnOps-tamagachi
- Current branch focus: MVP delivery with drill flow, graph progression, and hosted deployment hardening
- Active concerns: deployment reliability, onboarding clarity, and evidence-backed product framing
- Hosted runtime: Vercel serverless

## Current Priorities

- stabilize hosted user flows
- refine drill UX and graph progression
- document research support for learning claims
- establish repeatable agent workflows in-repo

## Open Questions

- which hosted ingestion paths are reliable enough for MVP
- how YouTube and external content ingestion should degrade gracefully
- which product claims should be softened until evidence docs are complete

## Environment Lessons

- Local success is not deployment validation.
- Hosted YouTube transcript retrieval can fail because YouTube blocks cloud/serverless IPs.
- Current hosted fallback for blocked YouTube transcript retrieval is manual transcript paste.
- External ingestion work must be reviewed for SSRF risk and internal error leakage.
