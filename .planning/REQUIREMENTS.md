# Requirements: Socratink

**Defined:** 2026-04-15
**Core Value:** AI removes prep friction and increases truthful retrieval reps without replacing the learner's generation step.

## v1 Requirements

Requirements for launch readiness — smooth core loop, persistent data, guided onboarding, session analytics.

### Infrastructure

- [ ] **INFRA-01**: Supabase project created with database schema, RLS policies, and connection pooling configured
- [ ] **INFRA-02**: Supabase JS client integrated via CDN in frontend (no build step)
- [ ] **INFRA-03**: Supabase Python client integrated in FastAPI backend

### Authentication

- [ ] **AUTH-01**: User can sign in with Google via Supabase Auth
- [ ] **AUTH-02**: User can try the app as anonymous guest via Supabase anonymous auth
- [ ] **AUTH-03**: User session persists across tabs and page refreshes
- [ ] **AUTH-04**: User can log out from any page
- [ ] **AUTH-05**: Backend middleware validates Supabase JWT on protected routes

### Data Persistence

- [ ] **DATA-01**: User's concepts (knowledge maps) are stored in Supabase Postgres as JSONB
- [ ] **DATA-02**: User's drill state (node epistemic states, re-drill counts, timestamps) is persisted in Supabase
- [ ] **DATA-03**: User can close browser, return later, and find all concepts and drill progress intact
- [ ] **DATA-04**: Concepts and drill state auto-save on every mutation (matching current localStorage behavior)

### Onboarding

- [ ] **ONBD-01**: New user sees a welcome message explaining the product's value on first visit
- [ ] **ONBD-02**: New user is guided through creating their first concept with contextual cues
- [ ] **ONBD-03**: After first concept creation, coach marks point to drill and explain next steps
- [ ] **ONBD-04**: After first drill attempt, result screen explains epistemic state (PRIMED/DRILLED) in plain language
- [ ] **ONBD-05**: After completing first learning loop, user sees a completion moment acknowledging their progress
- [ ] **ONBD-06**: User can skip or dismiss onboarding at any point without being blocked

### Analytics

- [ ] **ANLY-01**: Session events (start, duration, pages visited) are tracked per user
- [ ] **ANLY-02**: Analytics events are stored in Supabase Postgres for querying

### Mobile

- [ ] **MOBL-01**: Dashboard, study view, and drill chat are usable on mobile screen widths (down to 375px)
- [ ] **MOBL-02**: Viewport meta tag and scaling are correct on mobile devices

### UX Polish

- [ ] **UX-01**: AI operations (extraction, drilling) show clear loading states with progress indication
- [ ] **UX-02**: Errors during AI operations show user-friendly recovery guidance
- [ ] **UX-03**: Concept epistemic states have clear, jargon-free explanations accessible to new users

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Authentication

- **AUTH-06**: User can sign up and log in with email and password
- **AUTH-07**: User can log in via magic link (passwordless email)
- **AUTH-08**: User can delete their account and all associated data

### Data Persistence

- **DATA-05**: Migration utility to move existing localStorage data to Supabase
- **DATA-06**: User can access their concepts from any device (cross-device sync)
- **DATA-07**: User can export their concept data

### Analytics

- **ANLY-03**: Activation funnel tracked (concept_created -> drill_started -> drill_completed -> return_visit)
- **ANLY-04**: Time-to-first-loop metric measured per user
- **ANLY-05**: Drop-off detection (where in the flow users stop)
- **ANLY-06**: Analytics dashboard for reviewing user behavior patterns

### Mobile

- **MOBL-03**: Touch-optimized drill interface with larger touch targets
- **MOBL-04**: Simplified mobile graph view (list or reduced visualization)
- **MOBL-05**: Mobile-specific bottom navigation

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Native mobile app | Web-first, responsive design only |
| Real-time collaboration | Single-learner product |
| Gamification (streaks, leaderboards, badges) | Conflicts with truthful progress philosophy |
| Push notifications | Pre-revenue, small user batch, unnecessary pressure |
| AI-generated flashcards | Removes learner's generation step — anti-philosophy |
| Content marketplace | Scope creep, not relevant to core loop |
| Collaborative study | Not the product's purpose |
| Custom AI model training | Using Gemini API as-is |
| Paid features / billing | Pre-revenue, validating core loop first |
| Email/password auth (v1) | Google + guest sufficient for personal invites |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 1 | Pending |
| INFRA-02 | Phase 1 | Pending |
| INFRA-03 | Phase 1 | Pending |
| AUTH-01 | Phase 2 | Pending |
| AUTH-02 | Phase 2 | Pending |
| AUTH-03 | Phase 2 | Pending |
| AUTH-04 | Phase 2 | Pending |
| AUTH-05 | Phase 2 | Pending |
| DATA-01 | Phase 3 | Pending |
| DATA-02 | Phase 4 | Pending |
| DATA-03 | Phase 4 | Pending |
| DATA-04 | Phase 3 | Pending |
| ONBD-01 | Phase 6 | Pending |
| ONBD-02 | Phase 6 | Pending |
| ONBD-03 | Phase 7 | Pending |
| ONBD-04 | Phase 7 | Pending |
| ONBD-05 | Phase 7 | Pending |
| ONBD-06 | Phase 6 | Pending |
| ANLY-01 | Phase 5 | Pending |
| ANLY-02 | Phase 5 | Pending |
| MOBL-01 | Phase 8 | Pending |
| MOBL-02 | Phase 8 | Pending |
| UX-01 | Phase 9 | Pending |
| UX-02 | Phase 9 | Pending |
| UX-03 | Phase 9 | Pending |

**Coverage:**
- v1 requirements: 25 total
- Mapped to phases: 25
- Unmapped: 0

---
*Requirements defined: 2026-04-15*
*Last updated: 2026-04-15 after roadmap creation*
