# Desk Iso Board — Enhancement Handoff Brief

> **Status: complete (delivered 2026-05-05).** The Tier-1 work this brief commissioned landed:
> - 3×3 isometric grid with `BOARD_SLOT_COUNT` cap (`public/js/dom.js`, `public/js/app.js`, `public/index.html`).
> - State-aware tiles + crystal pin + quiet `+` empty-tile affordance (`public/css/iso-board-state-surface.css`, `public/js/iso-board-state-surface.js`).
> - Bus pub-sub re-sync (`Bus.emit('grid:rendered')` at the tail of `renderGrid`); no MutationObserver.
> - Floating-UI room-label generalized to empty tiles (`public/js/floating-room-label.js`).
> - Legacy `#tile-tooltip` deleted from `app.js`, `index.html`, `components.css`.
> - Smoke coverage: `tests/e2e/test_smoke.py::test_desk_iso_board_state_surface_and_room_labels`.
>
> Kept as the historical brief that scoped the work. Tier-2/3 backlog in §4 and the test-state matrix in §5 remain useful for follow-on enhancements.

---

**For:** A fresh agent starting on improving socratink's Desk view to make the isometric board feel like a complete, comprehensible learning surface — not a placeholder. Read this entire file before touching code.

**Status when this brief was written:** Board-first Desk landed (hero-info card hidden, board centered in a snug ~560px cream card). Approach-reveals hover treatment landed (pin lifts/grows, soft tile-face brighten, Floating-UI room-label tracking the `<g>`). The board is technically working but visually bare — four iso tiles, one selected, three empty, no state vocabulary, no light direction, no adjacency story. That's the gap.

---

## 1. The product context (read first)

This is a **learning tool, not a game and not a dashboard.** The iso board is the dungeon-map metaphor that underpins the whole product. Every visual decision must serve learner *comprehension* and *evidence-truth*, not engagement or aesthetics for their own sake.

**Required reading, in order:**

1. **`PRODUCT.md`** — register, users, anti-references, brand personality (calm, precise, Socratic), design principles. Especially: "Generation before recognition," "The graph tells the truth," "One active cognitive target."
2. **`DESIGN.md`** — section 2 (the dungeon-of-rooms metaphor), section 5 (state model — what the system may claim, and when), section 9 (the crystal — visual thesis), section 12 (sensory grammar), section 14 (what socratink refuses to be). The crystal polygon morphing across `locked / primed / drilled / solidified / fractured` is THE visual thesis. The board is its application at room scale.
3. **`UBIQUITOUS_LANGUAGE.md`** — binding term definitions for graph truth, recorded evidence, the four learning-loop states, and aliases to avoid. Copy edits to any iso-board element must conform.
4. **`AGENTS.md`** — agent execution discipline, the three-layer code exploration workflow (claude-context → code-review-graph → context7), the `SOCRATINK_DEV_AUTOGUEST` env var that lets local dev skip Google sign-in.
5. **The `socratink-design` skill** — invoke it before generating any visual work. It loads the palette, typography, crystal motif, copy voice, and dark-mode graph spec into context.

If you skip these, your work will read as AI slop because socratink's voice is highly specific and its anti-references are a long list. The product has explicit refusals (no streaks, no dashboards, no progress bars, no "AI tutor" framing). Internalize them.

---

## 2. What the iso board is, structurally

**The renderer.** `public/js/app.js:543` — `renderGrid(concepts = loadConcepts())`. Builds the SVG `<g>` for each of `BOARD_SLOT_COUNT` (currently 9) tile slots in a 3×3 isometric grid (`TILE_IDS` in `public/js/dom.js`). Each tile group has class `tile-group` plus `selected` (active concept) or `empty` (no concept yet). The grid SVG `viewBox` is `0 0 420 320` (`public/index.html#grid-svg`) with `overflow:visible` so lifted/scaled children can paint outside. Tile transforms are precomputed in the renderer; consult `renderGrid` for the current per-slot translate values rather than relying on this brief.

**The click handler.** `public/js/app.js:1531` — `selectTile(tileIdx)`. If the slot has a concept, calls `selectConcept(id)` then `showMapView(concept)` if there's `graphData`. If empty, opens the drawer and starts concept add. So clicking a populated tile already opens the room — no extra "Begin" button needed.

**The pin (the crystal).** Each populated tile contains `.concept-pin` with sub-elements `.concept-pin-shadow`, `.concept-pin-line`, `.concept-pin-head`, `.concept-pin-core`. Currently rendered identically regardless of concept state. **This is the single highest-leverage gap** — see section 4.

**The CSS layers:**
- `public/css/crystal.css` — base tile face/side/pin styles, plus `body.night` / `[data-theme="dark"]` overrides. Also has `.crystal-instance[data-state="..."]` rules for the brand-mark / wordmark crystals (NOT the board pins).
- `public/css/board-first.css` — hides `.hero-info`, snug-frames the card, overrides the 2-column grid.
- `public/css/approach-reveals.css` — hover/focus treatment for non-empty tiles, plus the Floating-UI `.room-label` tooltip styles.
- `public/js/floating-room-label.js` — uses `@floating-ui/dom` (already used elsewhere in `public/js/tooltips.js`) to anchor a singleton `.room-label` element to the hovered/focused tile-group.

**These files graduated from `_experiment-*` names to canonical names in commit c0aeaf8 and are committed on `dev`.**

**The legacy `#tile-tooltip`** has been removed (deleted from `app.js`, `index.html`, `components.css`); the Floating-UI room-label is the only tooltip surface on the board.

---

## 3. The three constraints you cannot violate

1. **State vocabulary is fixed.** Per DESIGN.md §5, the only allowed graph-state copy is: `draft path · suggested first · ready for first attempt · primed for study · solidified through spaced reconstruction`. Forbidden: "you know this", "mastered", "completed", "advanced". Do not invent new state labels.
2. **`drilled` is warm and return-worthy, never red.** Struggle is honored, not punished. Color it like dusk, not danger. (DESIGN.md §9.)
3. **No game-vocabulary metaphors leak in.** No XP, no streaks, no quest icons, no minimap, no fog-of-war. The dungeon metaphor is *spatial and architectural*, not *roguelike combat*. (DESIGN.md §14.)

---

## 4. The enhancement opportunities, ranked by leverage

**Tier 1 — what the board is missing most:**

- **State-aware tile faces and pins.** The board currently uses one visual treatment for every populated tile. The four learner states (`locked`, `primed`, `drilled`, `solidified`, `fractured`) should each be glanceable in the iso projection — that's the entire premise of "the graph tells the truth." Pattern to mirror: `public/css/crystal.css:180+` has `.crystal-instance[data-state="growing"]` etc. for the brand-mark crystal at hero scale. Apply the same data-state hook to `.concept-pin` elements on the iso board, with state-specific fill, glow, and possibly subtle edge animation. Consult the `socratink-design` skill for the palette per state.

- **Light source consistency.** Iso UIs feel right when one notional light direction governs all faces. Currently `.tile-left` and `.tile-right` have slightly inconsistent shading values. Pick a light direction (top-front-left is the convention) and re-derive the side fills from a single base + opacity ramp. Keeps the board feeling like a real surface, not a sticker.

**Tier 2 — once state is solved, depth helps comprehension:**

- **Adjacency hints.** Tiles that share an edge in the iso layout already imply spatial relationship. When the bridge / interleaving feature lands (DESIGN.md §3, screen 6), adjacent tiles should hint at connection through a shared glow or seam highlight when one of them is in `primed`. This is read-only signal — never a trigger for action — and only activates when the room is interleaving-eligible.

- ~~**Empty-tile treatment that invites without shouting.**~~ *Delivered* — quiet `+` empty-tile affordance shipped (`public/css/iso-board-state-surface.css`, `public/js/iso-board-state-surface.js`); empty-tile room-labels piggyback on the Floating-UI `.room-label`. See the status callout at the top of this brief.

- **Selection trail.** When a learner returns to a concept they've previously drilled, the path between rooms (interleaving history) could quietly surface as a faint connecting line on the iso surface — *only* showing solid spaced reconstructions, never reading attempts. Lines drawn with sub-30% opacity, never as decoration.

**Tier 3 — atmospheric, optional:**

- **Late-afternoon light overlay.** DESIGN.md §12: "Late-afternoon light through paper, not Instagram filter." A very subtle radial gradient on the desk surface behind the board, warm-side biased. The Ignition view already has `intro-particles` doing similar work — the Desk could earn a quieter version.

- **Crystal animation on state change.** DESIGN.md §9: "Crystal polygon morphs at 600ms; everything else lives at 140 / 220 / 320ms." When a re-drill records a state mutation, the affected pin should morph (not pop or pulse) over ~600ms with `prefers-reduced-motion: reduce` honored. Spring overshoot is reserved for `solidified` only — every other transition is ease-out-quart.

**Anti-priorities — don't do these:**

- Do not add tile labels by default (only on hover/focus). DESIGN.md §3 screen 4 prohibits revealing the room before the cold attempt; tile labels at rest would be the same anti-pattern at the desk scale.
- Do not add scoring, progress, or session-cap UI to the board. Those are session controls, not graph-truth surfaces.
- Do not redesign the iso projection itself. The 420×320 viewBox and tile transforms are baked into renderGrid; staying within them is a hard constraint until a renderer rewrite is on the table (it is not).

---

## 5. How to test what you build

**Local dev server with autoguest active:**

```bash
bash scripts/dev.sh
# Opens uvicorn on :8000 with SOCRATINK_DEV_AUTOGUEST=1 already exported.
# Visiting / trampolines through /auth/guest, no Google sign-in needed.
```

**Get a real concept on the board fast:** Library → click the "Hermes Agent" card. It imports a pre-extracted draft path and lands you on Desk with the tile populated. Since guest concept creation is also unlocked under DEV_AUTOGUEST, you can also ignite a fresh concept end-to-end if you have `GEMINI_API_KEY` in `.env.local`.

**The four learner states for visual testing:**

- `instantiated` — concept just submitted, pre-extract
- `growing` — graph data exists, learner has not yet drilled (Hermes Agent imports here)
- `fractured` — a re-drill found a gap (rare)
- `actualized` — solid spaced reconstruction recorded
- `hibernating` — spacing window not yet open

To force a state for visual testing: edit `localStorage['learnops_concepts']` directly in DevTools and set the `state` field on the active concept. Reload. The cap-aware logic uses the same key.

**Keep changes reversible during exploration.** Earlier iterations of this work staged enhancements as `public/css/_experiment-*.css` and `public/js/_experiment-*.js`, imported via `public/styles.css` and a script tag in `public/index.html`, then graduated to canonical names once approved (commit c0aeaf8). Adopt the same pattern: write new enhancements as `_experiment-<name>.{css,js}`, gate via cache-busted import, never edit canonical files until the user has approved the direction.

**Tests that matter:**

- `tests/e2e/test_smoke.py` — Playwright suite, runs the user's actual app shell. Add a visual-or-DOM smoke for any new state-driven board variant. Match the existing pattern.
- `tests/test_auth_gate_supabase.py` — covers the dev-mode env hard-gating; don't break it.
- The console must stay clean of new errors on first paint.

---

## 6. Definition of done for the iso board

The board is "done enough to ship" when, given any single concept tile on the desk:

- [ ] Its **state** is unmistakable from a glance — the pin/crystal looks materially different in `growing` vs `primed` vs `actualized` (DESIGN.md §9 morph spec).
- [ ] **Hovering or keyboard-focusing** it reveals the concept name + an action hint, positioned correctly even when the layout shifts (already wired via Floating UI; preserve).
- [ ] **Clicking it** opens the room (already wired via `selectTile`; preserve).
- [ ] **Empty slots invite without shouting** — a hover affordance reveals "Begin a concept" without on-page chrome at rest.
- [ ] **Dark mode reads correctly** — both ink-and-cream daytime and the night/dark-graph spec (DESIGN.md §9, plus the `body.night` overrides in `crystal.css`).
- [ ] **`prefers-reduced-motion: reduce`** disables the hover lift/scale and the crystal morph, falls back to opacity-only signal.
- [ ] **No console errors** on first paint or on any hover/focus interaction.
- [ ] **The three anti-priorities above are honored.** Verify before claiming done.

A nice-to-have but not blocking: the brand-mark crystal in the sidebar logo and the active iso-board pin should share a visual lineage (same proportions, same state vocabulary). They're the same crystal at different scales per DESIGN.md §9.

---

## 7. What's already committed on `dev` that you build on top of

Recent IA + design work landed since `main` last merged:

- IA: Ignition is a top-level route; Desk = isometric workshop only; sidebar nav order is Ignition before Desk; the `+ new tink` button was deleted; first-run boot routes to Ignition when the library is empty
- Auth: `SOCRATINK_DEV_AUTOGUEST` env var unlocks both the /login wall and guest concept creation locally; hard-gated against Vercel/CI
- Polish: Ignition view trimmed of two body paragraphs and a helper line; one eyebrow per surface; particles relocated from Desk-empty-state to `#ignition-view`
- Tests: 12/12 in `test_auth_gate_supabase.py`, 9/9 e2e smoke

The iso-board experiments described in section 2 graduated to canonical filenames in commit c0aeaf8 and are now committed on `dev`.

---

## 8. Where to ask for help if stuck

- The `claude-context` MCP for fuzzy code orientation
- The `code-review-graph` MCP for structural caller/callee verification before deleting any iso-board JS
- The `socratink-design` skill for any question about palette, motif, or copy voice
- `gemini --approval-mode plan -p "<prompt>"` for a second-opinion review on plan-shaped work (per project memory `feedback_propose_then_gemini_then_execute`)

End of brief.
