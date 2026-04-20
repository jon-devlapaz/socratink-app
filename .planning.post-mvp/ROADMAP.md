# Roadmap: Socratink

## Overview

Socratink's core learning loop works but lives in localStorage and lacks onboarding, analytics, and mobile support. This roadmap takes the app from "works on my laptop" to "ready for personally-invited users" by migrating to Supabase (auth + storage), adding guided onboarding, instrumenting basic analytics, and making the core flow usable on phones. Each phase delivers a verifiable capability, ordered so that downstream phases can build on stable foundations.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Supabase Foundation** - Set up Supabase project, schema, RLS, and client integration for both frontend and backend
- [ ] **Phase 2: Auth Migration** - Replace WorkOS with Supabase Auth (Google, guest, session persistence, logout, JWT validation)
- [ ] **Phase 3: Knowledge Map Storage** - Migrate concept/knowledge map persistence from localStorage to Supabase Postgres
- [ ] **Phase 4: Drill State Storage** - Persist drill state (epistemic states, re-drill counts, timestamps) in a separate Supabase table
- [ ] **Phase 5: Analytics Foundation** - Instrument session-level user behavior tracking stored in Supabase
- [ ] **Phase 6: Onboarding Welcome & First Concept** - Guide new users from landing to their first extracted knowledge map
- [ ] **Phase 7: Onboarding Drill & Completion** - Guide users through their first drill and celebrate loop completion
- [ ] **Phase 8: Mobile Responsiveness** - Make dashboard, study view, and drill chat usable on mobile screen widths
- [ ] **Phase 9: UX Polish** - Loading states, error recovery, and jargon-free explanations across all flows

## Phase Details

### Phase 1: Supabase Foundation
**Goal**: The infrastructure layer exists and both frontend and backend can communicate with Supabase
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, INFRA-03
**Success Criteria** (what must be TRUE):
  1. Supabase project exists with tables for users, concepts, drill_states, and analytics events
  2. RLS policies are active on every user-data table and verified with test queries
  3. Frontend can import and initialize the Supabase JS client from CDN without a build step
  4. Backend can connect to Supabase Postgres via the Python client using connection pooling
**Plans**: TBD

### Phase 2: Auth Migration
**Goal**: Users can sign in, stay signed in, and sign out using Supabase Auth instead of WorkOS
**Depends on**: Phase 1
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05
**Success Criteria** (what must be TRUE):
  1. User can sign in with their Google account and land on the dashboard
  2. User can try the app as an anonymous guest without creating an account
  3. User can close the browser, reopen it, and still be logged in
  4. User can log out from any page and be returned to the login screen
  5. Backend rejects API requests that lack a valid Supabase JWT
**Plans**: TBD

### Phase 3: Knowledge Map Storage
**Goal**: Users' concepts and knowledge maps survive beyond the browser session
**Depends on**: Phase 2
**Requirements**: DATA-01, DATA-04
**Success Criteria** (what must be TRUE):
  1. When a user creates a concept via extraction, the resulting knowledge map is saved to Supabase Postgres as JSONB
  2. When a user returns after closing the browser, all previously created concepts appear on the dashboard
  3. Each user sees only their own concepts (RLS enforced)
  4. Every concept mutation auto-saves to Supabase (matching current localStorage behavior — no manual save required)
**Plans**: TBD

### Phase 4: Drill State Storage
**Goal**: Users' drill progress persists independently from knowledge maps so they never lose learning state
**Depends on**: Phase 3
**Requirements**: DATA-02, DATA-03
**Success Criteria** (what must be TRUE):
  1. Node epistemic states (locked, primed, drilled, solidified), re-drill counts, and timestamps are stored in a dedicated drill_states table
  2. After drilling a node and closing the browser, the user returns to find the node in its correct epistemic state
  3. Drill state updates do not rewrite the entire knowledge map JSONB (separate table, targeted updates)
**Plans**: TBD

### Phase 5: Analytics Foundation
**Goal**: Basic user behavior is recorded so the builder can learn from real usage patterns
**Depends on**: Phase 2
**Requirements**: ANLY-01, ANLY-02
**Success Criteria** (what must be TRUE):
  1. Session events (start, duration, pages visited) are recorded per authenticated user
  2. Analytics events are queryable in the Supabase analytics_events table
  3. Anonymous guest sessions are tracked with the same schema as authenticated sessions
**Plans**: TBD

### Phase 6: Onboarding Welcome & First Concept
**Goal**: A new user understands what socratink does and successfully creates their first knowledge map without confusion
**Depends on**: Phase 3
**Requirements**: ONBD-01, ONBD-02, ONBD-06
**Success Criteria** (what must be TRUE):
  1. A first-time user sees a welcome message explaining what socratink does and how it works
  2. Contextual cues guide the user through pasting text or a URL and triggering extraction
  3. User can skip or dismiss the onboarding guidance at any point without getting stuck
**Plans**: TBD
**UI hint**: yes

### Phase 7: Onboarding Drill & Completion
**Goal**: A new user completes their first full learning loop (extract, drill, understand progress) and knows what to do next
**Depends on**: Phase 6
**Requirements**: ONBD-03, ONBD-04, ONBD-05
**Success Criteria** (what must be TRUE):
  1. After first concept creation, coach marks point the user toward drilling and explain the next step
  2. After the user completes their first drill, the result screen explains what PRIMED or DRILLED means in plain language
  3. After completing the first full learning loop, the user sees a completion moment acknowledging their progress
**Plans**: TBD
**UI hint**: yes

### Phase 8: Mobile Responsiveness
**Goal**: The core learning loop (dashboard, study view, drill chat) works on phone-sized screens
**Depends on**: Phase 4
**Requirements**: MOBL-01, MOBL-02
**Success Criteria** (what must be TRUE):
  1. Dashboard, study view, and drill chat are usable at 375px width without horizontal scrolling or overlapping elements
  2. Viewport meta tag and scaling prevent unexpected zoom or layout shifts on mobile devices
  3. Text input in drill chat is usable on mobile (keyboard does not obscure the input area)
**Plans**: TBD
**UI hint**: yes

### Phase 9: UX Polish
**Goal**: The app feels responsive and recoverable -- users never wonder "is it broken?" or "what does that mean?"
**Depends on**: Phase 7
**Requirements**: UX-01, UX-02, UX-03
**Success Criteria** (what must be TRUE):
  1. AI operations (extraction and drilling) display a clear loading indicator so the user knows work is happening
  2. When an AI operation fails, the user sees a friendly error message with guidance on what to try next
  3. Concept epistemic states are labeled with jargon-free descriptions accessible to someone who has never used the app
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Supabase Foundation | 0/TBD | Not started | - |
| 2. Auth Migration | 0/TBD | Not started | - |
| 3. Knowledge Map Storage | 0/TBD | Not started | - |
| 4. Drill State Storage | 0/TBD | Not started | - |
| 5. Analytics Foundation | 0/TBD | Not started | - |
| 6. Onboarding Welcome & First Concept | 0/TBD | Not started | - |
| 7. Onboarding Drill & Completion | 0/TBD | Not started | - |
| 8. Mobile Responsiveness | 0/TBD | Not started | - |
| 9. UX Polish | 0/TBD | Not started | - |
