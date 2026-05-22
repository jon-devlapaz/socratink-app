# socratink — DESIGN

Canonical product/design hub for agents and contributors. Slim by design: this file points to depth, it doesn't carry it.

For human-prose UX manifesto, read [`docs/design/socratink-ux.md`](docs/design/socratink-ux.md). For ops (commands, git workflow, conventions), read [`AGENTS.md`](AGENTS.md).

---

## 1. Product intent

**socratink** is a metacognitive learning tool. It teaches by **student generation**: the learner attempts a concept cold, receives targeted study, then re-drills the same concept after spacing. The interface exists to support that loop. The graph is the only public profile, and graph truth changes only when learner-generated evidence is recorded.

> The graph proposes. The cold attempt creates something to repair. Study makes the repair inspectable. The spaced re-drill records the strongest evidence.

**What socratink refuses to be** (hard exclusions, not preferences):

- Not a content browser, completion checklist, or streak/XP/badge surface.
- Not a chat product. Chat is ignition, not the product surface — chat extracts a learner-generated model and hands off.
- Not a diagnostic. The threshold is a starting map, never an evaluation.
- Not a mastery claim from reading or fluent prose. Only spaced reconstruction can record `solidified`.
- No learner-visible schema labels (beginner/intermediate/advanced, "your learning style").

---

## 2. Domain language

Canonical terms and aliases-to-avoid live in [`UBIQUITOUS_LANGUAGE.md`](UBIQUITOUS_LANGUAGE.md). Code or copy that disagrees with that file is wrong unless the file is updated first.

Quick reference (full list in UBIQUITOUS_LANGUAGE.md):

| Term | One-line | Don't call it |
| --- | --- | --- |
| **Cold attempt** | Unscored first generation on a local node before content appears | Quiz, test, assessment |
| **Targeted study** | Attempt-scoped corrective study unlocked by a substantive cold attempt | Proof, completion |
| **Spaced re-drill** | Later reconstruction after spacing; only event that can record `solidified` | Review, retry |
| **`primed`** | Learner reconstruction evidence on record; next action is derived from training evidence | Learned, partially mastered |
| **`needs repair`** | Current learner evidence has named gaps to repair | Failed, weak |
| **`solidified`** | Solid spaced reconstruction on record (evidence, not mastery) | Mastered, cleared |

---

## 3. State / data flow

```
Door (concept name [+ optional Learner goal] [+ optional Imported source])
  → if source: extraction pipeline → Provisional map
  → if no source: Launch pad → Launch attempt → Source-less generation → Smallest actionable route
→ Cold attempt (local) → writes learner attempt into `socratink:training:v1:<conceptId>`
→ Targeted study → records study reveal; no solidification
→ Repair Reps (optional) → no graph mutation
→ Interleaving Bridge → routing only, no mutation
→ Spaced re-drill → derives `solidified` only from spaced strong reconstruction; gaps derive `needs repair`
```

Architectural seams:

- **Map typed contract** — `ProvisionalMap` is a Pydantic model; the route boundary is the only `dict` shape. ADR-0001.
- **LLM seam** — application code imports `LLMClient`, never `google.genai`. Adding a provider is one new adapter file. ADR-0002.
- **Retry contract** — encoded in type system via `RetriableLLMError` marker class. ADR-0003.
- **Library boundary** — Library shows only the user's own reconstructed work; no built-in samples. ADR-0004.

Internal-only signals (routing hints, source-dependence scores, causal-depth) **never** surface to the learner.
Learner goal is relevance context for prompts and graph metadata; it is not graph-truth evidence.

---

## 4. Non-obvious decisions

| Decision | Why | Don't do | Ref |
| --- | --- | --- | --- |
| `ProvisionalMap` is a typed Pydantic model, not a dict | Catches structural breakage at parse time, not three steps later | Walk dicts in downstream code; reintroduce loose JSON | ADR-0001 |
| LLM provider lives behind `llm/` package | Switching providers is a one-file addition; tests don't patch private names | Import `google.genai` outside `llm/gemini_adapter.py` | ADR-0002 |
| `RetriableLLMError` marker class governs retry set | Class hierarchy *is* the contract; no separate tuple to forget | Add error to an `except (...)` tuple instead of subclassing | ADR-0003 |
| Library is users' work only | The trust signal of Library is the user's own reconstructed work; samples dilute it | Add `BUILT_IN_LIBRARY_CONCEPTS`, "Saved articles", side-by-side curated cards | ADR-0004 |
| Threshold is global; cold attempt is local | Different scope, different prompt, different surface — protects against generation fatigue | Re-ask the threshold question at the first cold attempt | manifesto |
| No content before the cold attempt | The Locked Study Silhouette's absence of content is intentional — peeking defeats the cold attempt | Show definitions, solved diagrams, or examples on the locked node | manifesto |
| Interleaving Bridge is the target after repair | A fresh repair re-drilled immediately tests short-term echo, not reconstruction; current POC still exposes an inline repair retry so the learner can close a `needs repair` loop | Present repair retry as mastery, spacing, or interleaving credit | manifesto |
| Training evidence is separate from the provisional graph | The graph proposes structure; `socratink:training:v1:<conceptId>` records learner evidence and derives state so Library cannot confuse AI summaries with reconstruction | Write learner evidence into `graphData.metadata.core_thesis` or persist mastery/completion as mutable graph fields | memory |
| Concepts seed without a source | "Add X to concepts" is a valid first move; raw text flows through the same extraction pipeline | Require a citation up-front; refuse source-less generation | memory |
| Silent surface default | Every visible element earns its keep; additive bias produces debt | Ship eyebrows, helper lines, decorative arrows "because it looks empty" | memory |
| Adjacent-surface vocabulary clash is a bug class | Same word + different referents in one frame = immediate UX confusion | Place "Commit attempt" button above a "cold attempt" footnote | memory |
| Antigravity is the in-app theme exception | Sanctioned divergence from cream-paper rules for the shipping in-app shell | Extend Antigravity's Outfit font or `#18181b` page outside the app shell | design |

---

## 5. Design system primitives

For component rules, see [`docs/design/socratink-design-system.md`](docs/design/socratink-design-system.md). For hex values, see [`public/css/tokens.css`](public/css/tokens.css). This section is the agent-readable summary.

**Palette (tokens only — never raw hex):**

- Page → `--cream-50` (never pure white)
- Text → `--ink-900` (never true black)
- Primary → `--violet-600` (one accent per screen)
- Secondary → `--lavender-500` (kicker text, dusted surfaces)
- Neutral → `--mauve-200` (locked states, empty dashes)
- Reserved → `--success` (only on solidified), `--danger` (only on fractured glow, subdued)

**Typography:** Geom (display) + Inter (body) + Manrope (fallback). Self-hosted from `/fonts/`. No Google Fonts. Antigravity theme's Outfit (loaded from Google Fonts for `.ignition-title` / `.hero-title` / eyebrows) is the **one** approved exception.

**Motif:** Dual-diamond crystal polygon with a vertical axis. Same shape at three scales — favicon, wordmark, isometric tile. Never restylized, never recolored.

**Board:** Always isometric, always cream. Never flat. Never force-directed node-and-edge. Constellation is the scoped sibling-view exception: secondary orientation only, with evidence-derived states and no study/source-preview leakage.

**Theme archetypes:** dark = constellation / sky; light = drafting / blueprint. Never invert one into the other.

---

## 6. Voice & interaction model

This section also governs LLM-generated content. Drill prompts, system prompts, and error messages are first-class product surfaces — the voice rules apply to them.

**Posture:** calm, precise, Socratic. Reading room, not dashboard. Patient tutor, not coach app, not game.

**Hard rules:**

- Second person, singular. Lowercase `socratink`, always.
- Lowercase state tokens: `primed`, `needs repair`, `solidified`; render no badge for null/untested training state.
- Plain complete sentences. Verbs over adjectives.
- No exclamation marks. No emoji. Ever.
- No hype jargon — *revolutionary, AI-powered, supercharge, 10×, unlock, crush, game-changing*. ("Unlock" is forbidden as user-facing hype; **Traversal unlock** remains valid as internal vocabulary.)
- No "our AI." Say what the system does instead (*identifies what depends on what · prompts for elaboration · halts at three retrievals*).
- Strategy over ability — describe the missing causal link, never the learner.
- No consolation copy on non-solid attempts. Replace "great try!" with strategy-framed next-step language.
- No scored language during the cold attempt (*quiz · test · exam · assessment · score*). Use *enter the room · what do you think this involves? · take your best guess.*
- Admit honest state. "Still testing. Still learning." is load-bearing brand.
- Trajectory bands (*spark → link → chain → clear → tetris*) surface only as post-attempt growth framing, never as a live score during an attempt.

**Silent surface default.** Every visible element earns its keep: ask "would the screen still work without this?" If yes, cut it. Reject SaaS-CTA arrows on commit buttons, progress hand-holding for short flows, brand-internal vocabulary as user-facing eyebrows.

**Adjacent-surface vocabulary clash check.** Before locking copy that sits inside a frame with other copy (button + footnote, eyebrow + title), scan content words for shared roots. If `attempt`, `commit`, `save`, `record`, `solidify`, `room`, `entry`, `sketch` appears in two adjacent strings with different referents, that's a bug, not a stylistic concern.

**Allowed state copy:** *suggested first · ready to reconstruct · primed for study · needs repair · solidified through spaced reconstruction.* **Forbidden:** *you know this · mastered · completed · advanced · diagnostic · evaluate · beginner/intermediate/advanced · we found your misconceptions.*

Full tone-by-surface table in [`docs/design/socratink-ux.md`](docs/design/socratink-ux.md) §10.

---

## 7. Boundaries

Design and code-contract boundaries only. For git, deploy, hooks, and other operational boundaries see [`AGENTS.md`](AGENTS.md).

| Tier | Examples |
| --- | --- |
| ✅ **Always** | Use palette tokens, not raw hex · respect `prefers-reduced-motion` · open the dev server in a browser before declaring UI work done · use UBIQUITOUS_LANGUAGE terms verbatim in user-facing copy · keep one cognitive target foregrounded; everything else dims |
| ⚠️ **Ask first** | Change palette tokens or type stack · introduce a third accent color · extend Antigravity (Outfit font, `#18181b` page) outside the in-app shell · bulk-restructure a canonical file (DESIGN.md, UBIQUITOUS_LANGUAGE.md, AGENTS.md) · invert a theme archetype (dark↔light) |
| 🚫 **Never** | Pure white page in light theme · true black text · emoji in any product surface · exclamation marks · force-directed node-and-edge graph (board is always isometric) · show content before the cold attempt (definitions, solved diagrams, examples on the locked silhouette) · mastery/completion claims from reading or fluent prose · learner-visible schema labels (beginner/intermediate/advanced, "your learning style") · "AI-powered" / "revolutionary" / "supercharge" copy · import `google.genai` outside `llm/gemini_adapter.py` · `extra="forbid"` on Gemini-bound Pydantic schemas |

---

## 8. Pointers

- Ops canon → [`AGENTS.md`](AGENTS.md)
- Full UX manifesto → [`docs/design/socratink-ux.md`](docs/design/socratink-ux.md)
- Domain language → [`UBIQUITOUS_LANGUAGE.md`](UBIQUITOUS_LANGUAGE.md)
- ADR history → [`docs/adr/`](docs/adr/)
- Design system component rules → [`docs/design/socratink-design-system.md`](docs/design/socratink-design-system.md)
- Product spec deep-dive → [`docs/product/spec.md`](docs/product/spec.md)
- Design tokens (code) → [`public/css/tokens.css`](public/css/tokens.css)
- Agent workflows → [`agents/`](agents/)
- Archive → [`docs/archive/`](docs/archive/)
