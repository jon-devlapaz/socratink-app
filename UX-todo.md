# Socratink UX TODO

Source: Full-product UX audit (2026-04-16) covering Dashboard, concept creation, Study/Graph/Drill, Library, Analytics, Settings, Quick Guide, keyboard, dark mode, mobile.

Severity legend: `[BLOCKER]` `[HIGH]` `[MED]` `[LOW]`
Classification: `bug` / `contract` (app breaks its own pattern) / `best-practice` / `polish`

---

## Root architectural finding

The token system is decorative, not driving. `--bg`, `--surface`, `--text`, `--primary`, `--success`, `--danger`, etc. are declared in `:root` but dark mode is implemented via selector-scoped overrides writing raw hex/rgb, not by reassigning tokens. Consequence: every component needs parallel dark-mode rules, and any view without them breaks. `--success` and `--danger` tokens are also declared but used by zero elements.

**Fix upstream in `public/css/variables.css` + `public/css/crystal.css`**: move dark colors into `[data-theme="dark"] :root { --bg: …; --surface: …; }` so components consume tokens without knowing the theme. Add `--surface-2` (elevated), `--ring` (focus), `--shadow-sm/-lg`, and wire theme-adaptive `--success`/`--danger` mappings.

This single change resolves findings #1, #4, #8, #14 and most of the dark-mode polish issues.

---

## Top 5 highest-leverage fixes (impact ÷ effort)

- [ ] **1. Rewire dark mode through the token layer.** Move hardcoded dark colors into `[data-theme="dark"] :root { … }` reassignments. Consume only tokens in components. Fixes invisible Analytics select, missing focus ring, dead `--success`/`--danger`, stale hero shadow, and the "Continue with Google" void in one PR.
- [ ] **2. Consolidate map-view chrome.** Kill the ambiguous top-left `<`. Replace with a proper "← Dashboard" text-back. Make sidebar open/closed state orthogonal to entry vector. Resolves findings #7 and #12.
- [ ] **3. Fix concept creation end-to-end.** Move form into a center dialog. Lock the shell with `inert` + scrim during extraction. Surface backend failures as retriable errors. In guest mode, honestly communicate "Guest mode uses sample maps; sign in to extract your own."
- [ ] **4. Make mobile first-class for theme, save, exit.** Add persistent user menu in mobile drawer footer: theme toggle, Save & Sync, Exit Guest, Settings. Currently mobile guest users have no egress path.
- [ ] **5. Rebuild Analytics `.stat-tile` with `value`/`value--empty`/`string` variants.** "No activity yet" at 28px is the worst typography moment in the app. Pair with a 2-col breakpoint for titles that wrap, and grade the pills with state tokens.

---

## Systemic patterns

### Pattern A — "Decorative tokens, imperative overrides"
Invisible selects, near-black Google button, unchanging hero shadow, dead `--success`/`--danger`, invisible focus rings. One root cause. Fix in stylesheet architecture, ~6 findings disappear.

### Pattern B — "Language drift between copy and UI"
Three names for a concept ("Concept" / "Tink" / "socratink"). Settings claims a "green" status that's actually purple. Four different CTAs ("Open concept" / "Open Map" / "Start Drill" / "Start With Core Thesis") with zero shared vocabulary. One writer + design-systems pass with a glossary resolves ~4 findings.

### Pattern C — "Shell vs. canvas confusion"
Sidebar used as canvas (creation form). Chrome buttons behave differently per view. Graph View is a static SVG inside a canvas-sized panel. The app hasn't decided which surface owns which job.

---

## Findings by path

### First-run / empty state

- [ ] `[HIGH]` `contract` — Three names for the same object in one viewport. Sidebar says "Add a New Tink", hero says "Add Concept", empty-state H1 says "Add your first socratink". Pick one noun ("Concept") and propagate. Files: `App.renderAddTrigger` (sidebar), dashboard empty-state template (hero).
- [ ] `[HIGH]` `bug / a11y` — Focus ring effectively invisible. `.theme-toggle` outline is `none`; `.hero-primary-action` outline is cream on a cream-text purple button. Add `:focus-visible { box-shadow: 0 0 0 3px var(--ring); }` with a `--ring` token.
- [ ] `[MED]` `best-practice` — First Tab stop is the theme toggle, not a primary action. Reorder so primary CTA is reached within 1–2 Tabs.
- [ ] `[LOW]` `polish` — Two competing Add paths with unequal weight (solid hero button + transparent sidebar card) both trigger `App.startAddConcept`. Either promote the sidebar one (used more once app has data) or demote the hero one.

### Concept creation

- [ ] `[BLOCKER]` `bug` — Re-test concept submission after starter removal. Earlier audit saw user input discarded into a starter seed with no error or warning. Either disable form in guest mode with a reason, wire to local fallback generator, or surface the backend error as retry prompt.
- [ ] `[HIGH]` `bug` — Extraction overlay doesn't lock the background. Sidebar form stays clickable during extraction; hero "Add Concept" stays enabled. Double-submit risk. Add full scrim with `backdrop-filter: blur(8px)`, `pointer-events: auto`, and `aria-busy="true"`.
- [ ] `[HIGH]` `contract` — Creation form lives in a 264px sidebar column. Textarea is ~200px wide for article-length pastes. Move creation into a center-stage dialog (Notion/Readwise pattern).
- [ ] `[LOW]` `best-practice` — Hero CTA stays active while creation form is open. Toggle to disabled or swap for "Cancel".

### Dashboard with one concept

- [ ] `[MED]` `polish` — Hero card uses stock isometric illustration, not real data. For a mapping app, showing the concept's real mini-map (cluster count, progress, state) would be warm and honest.
- [ ] `[LOW]` `polish` — Hero shadow is `0 40px 100px rgba(…, 0.05)` — expensive blur, reads flat. Consider `0 8px 24px rgba(…)` for tighter elevation.
- [ ] `[LOW]` `polish` — Add a secondary "Start Drill" shortcut on the hero card to save returning users a click.

### Entering a concept (Map View)

- [ ] `[HIGH]` `contract` — Two exits with different meanings. Top-left `<` is `.drawer-toggle` (collapses sidebar); top-right `×` is `.map-close-btn` (exits map). Users reading `<` as "back" will collapse the sidebar and think the app broke. Either (a) make top-left a real back-arrow that exits the map, or (b) remove it entirely and rely on `×`.
- [ ] `[MED]` `contract` — Sidebar auto-collapses when entering via sidebar click; stays open when entering via "Open Map". Same destination, two behaviors. Linear-style: keep sidebar open by default on desktop regardless of entry vector.

### Study View

- [ ] `[MED]` `best-practice` — "Start Drill" under-weighted for the primary action. 13px/700, tucked in top-right cluster. Consider a secondary CTA in chrome + a larger contextual "Start Drill" inside the first cluster or after the Backbone block.
- [ ] `[LOW]` `polish` — Tag pills don't differentiate semantics. "Feedback Control Loop" (topic) and "Introductory" (level) are both uppercase purple-tinted pills. Use two distinct variants.

### Graph View

- [ ] `[HIGH]` `best-practice` — Graph is a fixed `<svg viewBox="0 0 280 220">` inside a ~470px panel. It's an illustration of a graph, not a rendered graph. Cytoscape.js hint exists in the body but isn't mounted in this view. Ship a real rendered graph that fills the panel, with zoom + node legend.
- [ ] `[LOW]` `contract` — "Start With Core Thesis" button is a second primary CTA for the same gesture as "Start Drill". Consolidate.

### Drill

- [ ] `[HIGH]` `bug` — Drill error leaks backend detail. Message: "The drill service failed to respond. Check the backend or API key and try again." No error variant, no retry button. Add `.chat-bubble.error` token-backed variant with friendlier copy + retry. Guest mode should ship a local fallback drill.
- [ ] `[MED]` `contract` — Shell doesn't recognize "drill mode". `×` hard-exits to Dashboard and sidebar nav fires view changes mid-drill with no guard. Intercept view changes while `App.state.currentDrill` is active.
- [ ] `[MED]` `contract` — Graph reveal state persists after exit. After `← Back` and re-enter via "Open Map", the obfuscated-node reveal carries. If intentional, document it; if not, reset on map exit.
- [ ] Good — Obfuscated-node reveal pattern ("T·······C·······" → reveals as you progress) is thoughtful and distinctive. Keep it.

### Library

- [x] `[MED]` `contract` — Starter shelf card issues are obsolete. The old multi-concept starter shelf was removed; the Library now has one curated Hermes Agent documentation concept pending the broader Library revamp.

### Analytics

- [ ] `[BLOCKER]` `bug` — Concept select invisible in dark mode. `.analytics-select` background stays `rgba(255,255,255,0.9)` but color is cream. Selected option unreadable. Move background to a token (`--input-bg`) and swap in the dark ruleset.
- [ ] `[HIGH]` `contract` — `.stat-tile-value` renders "No activity yet" at 28px, wrapping 3 lines inside a small column. Add a `value--empty` variant that drops to ~14–15px italic muted text.
- [ ] `[MED]` `polish` — Stat titles wrap to 3 lines on 278px columns ("Re-Drill Conversion", "Return Timing", "Recent Learning Journal"). Reduce title size, tighten to 2 columns, or shorten copy ("Re-Drill Wins", "Overdue Returns", "Journal").
- [ ] `[MED]` `best-practice` — All pills are lavender. "Solid 0", "Primed 0", "In progress 0", "Misconceptions 0" should differentiate at a glance. Use `--success`/`--warning`/`--danger`/`--info` tokens.
- [ ] `[LOW]` `polish` — Seven "?" help icons create tooltip-soup. Group into a single "How to read this page" affordance at the top.

### Settings

- [ ] `[MED]` `bug` — Copy references a "green" that isn't in the UI. "A green backend alone does not prove extract or drill is fully working." — actual dot is purple. Either restore green semantically via `--success` or change the copy to match reality.
- [ ] `[MED]` `best-practice` — Guest mode exposes a Gemini API key input inline on the main Settings surface. For broader audience, move behind an "Advanced" disclosure.
- [ ] `[LOW]` `polish` — "Continue with Google" in dark mode renders as a near-black void on dark-purple surface. Use Google brand tokens (white for light, `#131314` with visible white border for dark) if real SSO, or a neutral secondary if placeholder.
- [ ] `[LOW]` `polish` — Three different badge treatments on the same card: "Connected" filled pill, "Server key active" filled pill, `settings-dot.connected` 7×7 dot. Pick one.

### Navigation consistency

- [ ] `[BLOCKER]` `bug` — Mobile (≈375px) hides theme toggle, Save & Sync, Exit Guest via `display: none`, and none are in the drawer. Mobile guest users cannot toggle theme, save their work, or exit guest mode, anywhere. Silent data-loss path. Add to mobile drawer footer.
- [ ] `[LOW]` `contract` — Hamburger morphs between `≡` and `<`. Users fluent in browser "Back" will misread `<`. Add a tooltip label.

### Theme persistence

- [ ] `[MED]` `polish` — Hero shadow is unchanged between themes (`rgba(44,51,62,0.05) 0 40px 100px` in both) — too soft for dark, too heavy for light. Token-swap via `--shadow-hero`.
- [ ] Good — Theme persists across route changes (localStorage).
- [ ] Good — No legacy green (`#22c55e`/`#16a34a`/`#10b981`/`#4dba8a`) rendering anywhere. Remove `--success` token or wire it up.

### Keyboard and focus

- [ ] `[HIGH]` — First Tab stop is `.theme-toggle`. See #8.
- [ ] `[HIGH]` — Focus outlines are mostly invisible. See #8.
- [ ] `[MED]` — No focus trap in overlays. Extraction overlay leaves shell tabbable; tour beacons don't trap focus. Add focus management to modal/overlay patterns.

### Back-and-forth / state

- [ ] `[LOW]` `polish` — `#library-view`, `#analytics-view`, `#settings-view` all carry `.library-view` base class. A rule written for `.library-view .library-card` would leak into Analytics/Settings. Rename to unique base classes.
- [ ] Good — `#card` accumulates no state classes after navigation. No stale-class leakage.

### Quick Guide

- [ ] `[MED]` `contract` — Tour tooltip initially renders at 34×31 at (0, 8) — effectively invisible. Must click a beacon to see content. No auto-open, no "1 of 5" progress, no dismiss control on the tooltip. Auto-open step 1 with visible "Next / Skip" controls and a progress indicator.

---

## Architectural recommendation (post-fixes)

Extract a lightweight design-system layer — `tokens.css` + `components.css` — that any view imports.

- **Tokens**: single source of theme truth (light / dark / high-contrast later).
- **Components**: one implementation each: `Card`, `StatTile`, `Pill`, `Button` (primary/secondary/ghost), `ChatBubble` (info/error), `Scrim`, `Dialog`.

Today, `library-view` is the shared class for Library + Analytics + Settings — CSS leaks sideways. Once the system layer exists, each route owns only its IA, not the primitives. This is the actual Notion/Linear pattern.

**Do this after fixes 1–5. Do this before building Graph View for real** — an interactive graph will bring its own elevation/ring/focus requirements that will otherwise metastasize into more hardcoded hex values.

---

## Progress log

- 2026-04-16: UX-todo.md created from full-product audit.
