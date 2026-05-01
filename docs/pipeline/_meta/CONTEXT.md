# Project context (DDD glossary)

Project ubiquitous language + canonical terminology. Read by Step −1 of every `/pipette` run; updated inline during Step 1 by the `grill-with-docs` skill as decisions crystallise. Per-feature grill summaries live in each run's `01-grill.md`.

## Language

**Tink TODO**:
The single markdown file at `/Users/jondev/dev/socratink/todo.md` that holds Jon's actionable session-by-session work log. Maintained by the `tink-todo` skill (extracts new items + closes resolved items with evidence). Path is fixed; the file lives one directory above the `socratink-app` repo root.
_Avoid_: "the todo", "the task list" (ambiguous — could mean anything).

**TODO Item**:
A single line in the Tink TODO of the form `- [ ] {verb} {outcome}` (open) or `- [x] {body}` (closed). May carry inline metadata wrapped in italics: `*(resolved YYYY-MM-DD by <SHA>)*`, `*(deprecated YYYY-MM-DD — <reason>)*`, or `*(Builder's Trap? → <reasoning>)*`. Closed-deprecated items wrap the body in `~~strike~~`.
_Avoid_: "task", "todo" (overloaded).

**Bucket**:
An h3 sub-section under a Session Closeout that groups items by urgency. Canonical buckets: `Now`, `Next`, `Backlog`, `Housekeeping`, `Lessons`. Default placement for new items is `Backlog`.
_Avoid_: "category", "section".

**Session Closeout**:
An h2 heading of the form `## Session YYYY-MM-DD Closeout — <topic>` that groups items captured at the end of a working session. Closed items stay in place under their original Closeout for chronological readability.
_Avoid_: "session", "closeout" alone.

**Builder's Trap (flag)**:
An inline annotation `*(Builder's Trap? → <how does this serve June 2026 customer-acquisition goal>)*` on a TODO Item that may be infrastructure/tooling with no clear customer line. Not a blocker — a visible nudge requiring justification before the item ships.
_Avoid_: "yak shave", "tech debt" (different concepts).

**Admin Surface**:
The `/admin/*` route family inside `socratink-app` reserved for single-user (Jon) operational tools. Distinct from the customer-facing app. New as of this feature; first member is `/admin/todo`. Admin Surface is **not** the same as the existing **App Surface** (the customer-facing `/`, `/index.html`, and `/api/*` routes).
_Avoid_: "internal tools", "ops dashboard" (vague).

**Admin Gate**:
The handler-level enforcement that an authenticated user matches the hardcoded `ADMIN_EMAIL` constant. Layered on top of the existing `require_login_or_guest_entry` middleware (which only checks "authenticated OR guest"). Guest sessions never satisfy the Admin Gate (no email).
_Avoid_: "auth check", "permissions" (the codebase has no general permission system).

**Dev-only Route**:
A FastAPI route that refuses to register if the runtime environment is production (Vercel deploy). Detected via `APP_BASE_URL` not being a localhost URL, OR via missing required filesystem prerequisites (e.g., `/Users/jondev/dev/socratink/todo.md` does not exist on Vercel). New concept introduced by this feature; first member is `/admin/todo`.
_Avoid_: "local-only", "dev mode".

## Relationships

- A **Tink TODO** contains many **Session Closeouts**.
- A **Session Closeout** contains many **Buckets**.
- A **Bucket** contains many **TODO Items**.
- A **TODO Item** may carry zero or more inline metadata flags (`resolved`, `deprecated`, `Builder's Trap`).
- An **Admin Surface** route is a **Dev-only Route** AND requires an **Admin Gate**. The two checks are independent: Admin Gate alone is insufficient (would let `/admin/*` ship to prod broken); Dev-only alone is insufficient (would let any local user browse).

## Flagged ambiguities

- "todo" was overloaded at session start — could mean the file, an item, or the skill. Resolved: **Tink TODO** = file, **TODO Item** = line, `tink-todo` (kebab) = the skill that maintains it.
- "admin" was checked against the existing codebase — no prior `admin` pattern existed. Resolved: **Admin Surface** + **Admin Gate** are net-new to socratink-app, introduced by this feature.
