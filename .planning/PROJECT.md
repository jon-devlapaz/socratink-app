# Socratink

## What This Is

Socratink is an AI-powered learning app that extracts structured knowledge maps from raw content (text, URLs, files) and drills truthful recall through Socratic conversation. Learners paste material, the AI structures it into a drillable graph, and they prove understanding by explaining concepts from memory before seeing study material. Built as a vanilla JS/FastAPI web app deployed on Vercel.

## Core Value

AI removes prep friction and increases truthful retrieval reps without replacing the learner's generation step. The struggle is the point — cold recall before recognition.

## Requirements

### Validated

- User can sign up and log in via WorkOS (email, Google, guest, magic auth) — existing
- User can create concepts by pasting text, providing a URL, or uploading a file — existing
- AI extracts structured knowledge maps with backbone principles, clusters, and subnodes — existing
- User can inspect extracted material in Study View (expandable clusters and nodes) — existing
- User can visualize knowledge map as an interactive graph (Cytoscape.js) — existing
- User can drill any node via Socratic AI conversation (cold recall first) — existing
- Node epistemic states track learning progress (locked → primed → drilled → solidified) — existing
- AI evaluates recall quality and routes to next action (probe, scaffold, reroute, complete) — existing
- Next best move guidance directs user through the graph after each drill — existing
- Crystal UI metaphor reflects concept state on dashboard — existing
- App deploys to Vercel as serverless FastAPI — existing

### Active

- [ ] Migrate auth from WorkOS to Supabase Auth
- [ ] Migrate data persistence from localStorage to Supabase Postgres
- [ ] Build guided onboarding for first-run users (one truthful loop)
- [ ] Instrument analytics to measure user behavior and activation
- [ ] Make the app work well on mobile devices
- [ ] Polish UX rough edges across existing flows

### Out of Scope

- Native mobile app — web-first, responsive design only
- Real-time collaboration — single-learner product
- Custom AI model training — using Gemini API as-is
- Gamification / streaks / leaderboards — truthful progress, not engagement tricks
- Paid features / billing — pre-revenue, validating core loop first

## Context

Socratink is MVP-stage. The core learning loop works: extract → inspect → cold recall → targeted study → next move → return. But it's not ready for real users because data lives in localStorage (vanishes if they clear browser), there's no onboarding to guide first-time users through the loop, and there's no instrumentation to learn from how people actually use it.

The immediate goal is to get the product ready for a small batch of personally-invited users (friends, colleagues, early supporters). The purpose isn't scale — it's learning. Watch how real people use it, measure what matters, and iterate toward retention.

An onboarding research report (`socratink_onboarding_tutorial_research_report.md`) already exists with a clear recommendation: guided task completion (not narrated tours), hybrid coach marks + interactive tasks, and a 6-step first-run storyboard that gets users through one truthful loop in under 2 minutes.

The current auth system (WorkOS) will be replaced by Supabase Auth, and localStorage will be replaced by Supabase Postgres — consolidating auth and storage into one platform.

## Constraints

- **Tech stack**: Vanilla JS frontend (no frameworks, no build step), FastAPI backend, Gemini 2.5 Flash for AI
- **Deployment**: Vercel serverless — all backend routes through `api/index.py`
- **AI dependency**: Gemini API for extraction and drill — cost scales with usage
- **No build step**: Frontend is static files served from `public/` — keep it that way
- **Architecture invariants**: `setState()` is the only UI control-state entry point; knowledge map is source of truth for drill state; generation before recognition is non-negotiable

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Supabase for auth + storage | Consolidates WorkOS (auth) + localStorage (data) into one platform — simpler stack, persistent data, built-in auth | — Pending |
| Guided task completion for onboarding | Research report recommends teaching by doing over narrated tours — matches the product's "generation first" philosophy | — Pending |
| First users are personal invites | Learning from real usage, not chasing scale — small batch to iterate on retention | — Pending |
| Keep vanilla JS / no build step | Existing architecture works, no reason to add framework complexity for this milestone | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-15 after initialization*
