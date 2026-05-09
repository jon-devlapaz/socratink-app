# Paper migration plan — umbrella roadmap

**Status:** active
**Owner:** Jon
**Created:** 2026-05-09
**Last revised:** 2026-05-09 — corrected after a fresh-subagent verification pass found that the prior version was authored against an inferred (and partially wrong) repo structure. This revision is grounded in actual file contents.
**Type:** umbrella spec (lists waves; no code itself)

## Why this exists

The marketing landing page at socratink.ai presents a coherent visual identity — cream paper, hairline borders, ruled lines, violet accent, Geom typography. The app at app.socratink.ai presents a different identity on the **Ignition + Launch Pad** views — `body.antigravity-theme` glass cards, radial-gradient backdrops, large display titles with shadows. The two surfaces are the same brand and should read the same.

Customer-persona testing converged hard on the paper identity. The persona's principle: *"Direction B feels like a blank sheet of paper on a quiet desk — kill the gradient washes entirely. Learning isn't a vibe; it's just hard work."*

## What's already in place (verified 2026-05-09)

The repo's base design tokens are already paper-system-aligned:

- `public/css/variables.css` (633 lines) is the live token source. It defines `--surface-page` = `--cream-50` (`#f7ece1`), `--surface-card` = `--paper-0` (`#fffaf6`), `--accent-primary` = `--violet-600` (`#9067c6`, matches landing), `--primary-fill` = `#7a59aa` (button fill), `--text-strong`, `--text-muted`, `--border-subtle`, `--border-strong`, `--shadow-card` (violet-tinted), `--font-display` Geom, `--font-body` Inter, complete spacing/radius/motion scales, and a fully realized dark theme with `--surface-page-theme: #18181b` (graphite-900) and `--surface-card-theme: #27272a` (graphite-800) — i.e., **night paper is already the existing dark theme**.
- `docs/design/colors_and_type.css` is the design-doc mirror (described as such on line 12 of variables.css).
- `public/css/tokens.css` is a separate, smaller file: a login-safe font-loader subset that ships brand fonts. Do **not** confuse it with variables.css.
- `public/css/base.css` line 27 already declares `[hidden] { display: none !important; }` — the `[hidden]` attribute hides any element regardless of selector specificity.
- `public/styles.css` is the entry-point stylesheet that `@imports` the chain `variables.css → base.css → crystal.css → components.css → layout.css → board-first.css → approach-reveals.css → iso-board-state-surface.css`.
- `public/antigravity.css` (1955 lines) layers ON TOP of the base, scoped under `body.antigravity-theme`. This is what currently makes the Ignition view look like a "VC AI app" rather than a paper journal.

**Implication:** the "paper redesign" is mostly **deletion** of antigravity overrides on the Ignition + Launch Pad views, plus a small set of additions for new visual atoms (witness anchor, ruled paper textarea, journal-meta line, "actually explain" emphasis). The base ignition styles already reference the canonical token system; once the antigravity overlay is removed, what remains IS the paper system the persona asked for.

## Migration architecture (locked)

- **CSS Cascade Layers** (`@layer components, legacy, paper`) provide a safety net so paper rules win over antigravity regardless of selector specificity. Browser support: Chrome 99+, Firefox 97+, Safari 15.4+ (universal as of 2022).
- **Layer ordering preserves current behavior on unmigrated views.** `legacy` loads later than `components` so `body.antigravity-theme …` rules continue to win on dashboard, library, settings.
- **Paper layer is reserved for new component CSS** introduced by Wave 1+. `paper.css` is created in Wave 1, not Wave 0.
- **Tokens live in the existing `public/css/variables.css`.** Wave 0 adds exactly two tokens (`--rule-line`, `--rule-step`); no parallel token system.
- **A single import root `public/css/index.css`** declares the layer order and `@imports` the existing `styles.css` and `antigravity.css` into their respective layers. The two existing `<link>` tags in `public/index.html` collapse to one.
- **Strangler Fig discipline:** each wave deletes its rules from `antigravity.css` in the same PR. No fallback class. When `antigravity.css` is empty, the file is deleted and the `body.antigravity-theme` class is removed from `public/index.html`.

## Wave order (execution sequence)

| Wave | Surface | Spec |
|---|---|---|
| **0** | Cascade-layer infrastructure: `index.css` + 2 token additions to variables.css. **Zero visible change.** | `2026-05-09-paper-tokens-cascade-layers-refactor-design.md` |
| **1** | Ignition view + Launch Pad view paper redesign | `2026-05-09-ignition-paper-redesign-design.md` |
| **2** | Dashboard / hero card / `.intro-page` | future wave — spec to be written when wave is scheduled |
| **3** | Library view (`.library-card-*`, `.library-vault-grid`, `.library-empty`) | future wave — spec to be written when wave is scheduled |
| **4** | Settings view (`.settings-shell`, `.settings-toggle`, `.settings-pill`, identity rows) | future wave — spec to be written when wave is scheduled |
| **5** | Sidebar + bottom nav active states | future wave — spec to be written when wave is scheduled |
| **6** | `intro-particles.js` retirement; `antigravity.css` empty; delete file; remove `body.antigravity-theme` class | future wave — spec to be written when wave is scheduled |

Each wave gets its own spec, brainstorm, persona check, and browser smoke. Each wave is independently shippable and revertable.

## Naming caveat

`public/css/variables.css` contains a separate "Wave 2" sweep referenced in its own legacy-aliases comment block — that's a pre-existing migration to grep-replace deprecated aliases like `--bg`, `--card-bg`, `--text`, `--text-sub` and is **unrelated to this paper migration**. To avoid confusion, this paper migration uses the term "Paper Wave N" in commit messages and inline comments.

## Constraints carried across all paper waves

- **AGENTS.md scope-lock applies to each wave.** No surface is touched outside its wave.
- **Browser smoke (`scripts/qa-smoke.sh`) is load-bearing.** Each wave must pass clean before merge to `dev`.
- **Color contrast ≥ AA Normal (4.5:1)** for all functional text in both light and night-paper modes.
- **Reduced motion** suppresses transforms, animations, and panel transitions.
- **Keyboard a11y:** focus-visible ring on every interactive element; no tab traps.
- **Audio FX retained** (focus tap, key click). If a future wave proposes dropping `audio.js`, that's a separate decision recorded in that wave's spec.
- **Reuse existing tokens.** New components must consume `--surface-*`, `--text-*`, `--accent-*`, `--border-*`, `--shadow-*` from variables.css. Net-new tokens require a justification line in the wave's spec.

## Out-of-scope across all waves

- Backend behavior (FastAPI, `auth/`, `ai_service.py`, `/api/extract`, ProvisionalMap shape).
- `audio.js`, `bus.js`, `telemetry.js` — restyle their rendered DOM if relevant; no logic changes.
- The graph view (`graph-view.js`) — has its own design language; not part of this migration.
- The drill chat surface — covered by `socratink-design.skill`.
- The unrelated "Wave 2" legacy-alias sweep mentioned in variables.css.

## Decision log (persona-driven)

Decisions locked during the 2026-05-09 brainstorm (recorded for future waves):

- **No atmospherics on Ignition + Launch Pad.** No gradient washes, no glass cards, no glow shadows, no particle field. Antigravity's overrides on these surfaces get deleted.
- **Witness anchor adopted (Wave 1).** Inert SVG diamond above title; no fill, no glow, no animation. The future graph-node lives there empty until earned.
- **Title verb: "actually explain"** — italic emphasis with violet underline.
- **Concept name on Screen 2: plain typeset line** — `on Photosynthesis`, italic "on" + ink-weight name.
- **Source-attach: meta line inside card.** `source: none yet — add` reads as a journal annotation, not a form widget.
- **Composer card: ruled paper, no redline.** 31px horizontal rules behind the textarea (via `background-attachment: local` on the field). No 80px violet redline indent.
- **Dark mode = existing graphite theme.** No new "night paper" tokens needed; the existing `--surface-page-theme: #18181b` IS night paper.
- **Cap gate above composer, composer locked-not-hidden.** Preserves the user's mental model of "this is where I write."
