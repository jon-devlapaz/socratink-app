# Paper migration plan — umbrella roadmap

**Status:** active
**Owner:** Jon
**Created:** 2026-05-09
**Type:** umbrella spec (lists waves; no code itself)

## Why this exists

The marketing landing page at socratink.ai presents a coherent visual identity — cream paper, hairline borders, ruled lines, violet-deep accent, Geom typography. The app at app.socratink.ai presents a different identity — `body.antigravity-theme` glass cards, radial-gradient backdrops, large display titles with shadows. The two surfaces are the same brand and should read the same.

Customer-persona testing (a college sophomore, anti-cramming, anti-flashcard-only, anti-cheat-with-AI) converged hard on the paper identity. Persona quote: *"Direction B feels like a blank sheet of paper on a quiet desk — it sets the expectation that I have to bring the effort. Kill the gradient washes entirely. Learning isn't a vibe; it's just hard work, and the interface should have the confidence to just be a piece of paper."*

The current `public/antigravity.css` is 1955 lines, owns 121 unique selectors, and styles ignition view, launch-pad view, dashboard, hero card, library, settings, sidebar nav, bottom nav. It cannot be replaced in one PR. It must be replaced via Strangler Fig — one surface at a time, each PR small, each surface verifiable in browser smoke.

## Migration architecture (locked)

- **CSS Cascade Layers** (`@layer tokens, legacy, components, utilities`) handle cascade order so paper rules win over antigravity regardless of selector specificity. Browser support is universal as of Chrome 99 / Firefox 97 / Safari 15.4 (early 2022).
- **Three-tier design tokens** in `public/css/tokens.css`: primitive (`--violet-700: #6f4da1`), semantic (`--accent-deep: var(--violet-700)`), with light as default and `html[data-theme="dark"]` overriding the semantic layer for night-paper mode.
- **Single import root** `public/css/index.css` declares the layer order and imports all stylesheets in their assigned layers. `public/index.html` keeps one `<link>` to `index.css`.
- **Strangler Fig discipline:** each wave deletes its rules from `antigravity.css` in the same PR. No fallback class. No commented-out blocks. When `antigravity.css` is empty, the file is deleted.

## Wave order (execution sequence)

| Wave | Surface | Spec |
|---|---|---|
| **0** | Tokens + cascade layers infrastructure (no visible change) | `2026-05-09-paper-tokens-cascade-layers-refactor-design.md` |
| **1** | Ignition view + Launch Pad view | `2026-05-09-ignition-paper-redesign-design.md` |
| **2** | Dashboard / hero card / `.intro-page` | future wave — spec to be written when wave is scheduled |
| **3** | Library view (`.library-card-*`, `.library-vault-grid`, `.library-empty`) | future wave — spec to be written when wave is scheduled |
| **4** | Settings view (`.settings-shell`, `.settings-toggle`, `.settings-pill`, identity rows) | future wave — spec to be written when wave is scheduled |
| **5** | Sidebar + bottom nav active states | future wave — spec to be written when wave is scheduled |
| **6** | `intro-particles.js` retirement and `audio.js` review (if dropped); `antigravity.css` empty; delete file; remove `body.antigravity-theme` class | future wave — spec to be written when wave is scheduled |

Each wave gets its own spec, brainstorm, persona check, and browser smoke. Each wave is independently shippable and revertable.

## Constraints carried across all waves

- **AGENTS.md scope-lock applies to each wave.** No surface is touched outside its wave.
- **Browser smoke (`scripts/qa-smoke.sh`) is load-bearing.** Each wave must pass clean before merge to `dev`. Same-origin asset failures and console errors are real bugs.
- **Color contrast ≥ AA Normal (4.5:1)** for all functional text in both light and night-paper modes. Lighthouse a11y score ≥ 95 on each migrated view.
- **Reduced motion** (`prefers-reduced-motion: reduce`) suppresses transforms, animations, and panel transitions. Page itself stays static; reduced-motion is "calmer," not "no signal."
- **Keyboard a11y:** focus-visible ring on every interactive element; focus routing on view mount; no tab traps.
- **Audio FX retained** by default. If a future wave proposes dropping `audio.js` calls, that's a separate decision recorded in that wave's spec.
- **Three-tier tokens stay strict.** New rules in any wave reference only semantic tokens; primitive tokens are added only when a new color/dimension genuinely needs to enter the system.

## Out-of-scope across all waves

- Backend behavior (FastAPI, `auth/`, `ai_service.py`, `/api/extract` pipeline, ProvisionalMap shape).
- `audio.js`, `bus.js`, `telemetry.js` — restyle only their rendered DOM if relevant; no logic changes.
- The graph view (`graph-view.js`) — has its own design language for the dark-mode graph. Not part of this migration.
- The drill chat surface — has its own design surface in `socratink-design.skill`.

## Decision log (persona-driven)

Decisions locked during the 2026-05-09 brainstorm (recorded for future waves):

- **No atmospherics.** No gradient washes, no glass cards, no glow shadows, no particle fields. Persona explicitly rejected each.
- **Witness anchor adopted (Wave 1).** Inert SVG diamond above title; no fill, no glow, no animation. The future graph-node lives there empty until earned.
- **Title verb: "actually explain"** — italic emphasis, violet-deep with translucent underline.
- **Concept name on Screen 2: plain typeset line** — `on Photosynthesis`, italic "on" + ink-weight name.
- **Source-attach: meta line inside card.** `source: none yet — add` reads as a journal annotation, not a form widget.
- **Composer card: ruled paper, no redline.** 31px horizontal rules behind the textarea (via `background-attachment: local` on the field). No 80px violet redline indent.
- **Dark mode = night paper.** Same notebook structure, inverted to graphite. No glows, no blooms.
- **Cap gate above composer, composer locked-not-hidden.** Preserves the user's mental model of "this is where I write."

## File created on locking this plan

`public/css/tokens.css`, `public/css/index.css`, plus the BEM/component additions to `public/css/components.css`. The `body.antigravity-theme` class remains in `public/index.html` until Wave 6.
