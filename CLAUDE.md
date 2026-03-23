# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**LearnOps Tamagachi** is an interactive prototype demonstrating a neurocognitive learning pipeline. The concept: raw information enters a three-stage lifecycle (Ingest → Drill → Consolidate) modeled as a living ecosystem that grows or hibernates based on learner performance.

The UI uses emoji-driven states that map to internal JS state names:
- `🌱` active/growing → `growing`
- `🥀` needs repair → `fractured`
- `🐛💤` consolidating → `hibernating`
- `💎` mastered → `actualized`

> Note: `instantiated` still exists in the state machine for backward compatibility with old localStorage data, but new concepts are never created in that state.

## Running the Project

No build step. Open directly in a browser:

```bash
open index.html
# or serve locally
python3 -m http.server 8000
```

## Architecture

The entire application lives in a single file: `index.html`. It is pure vanilla HTML/CSS/JavaScript with no dependencies or frameworks.

**Key patterns in index.html:**
- **`setState(state)`** — central function that drives all UI transitions; calls `applyControlsForState()` at its end — this is the *only* place controls are updated (no manual `showControls`/`setButtons` calls elsewhere)
- **`applyControlsForState(state, concept)`** — owns all button visibility/enabled state for a given state
- **`setButtons(extract, drill)`** — two-parameter helper (extract-enabled, drill-enabled); `btn-present` was removed
- **CSS variables** — `--bg`, `--primary`, `--danger`, `--success` etc. for theming; `hibernating` state triggers a dark mode swap via `body.night`
- **24-hour timer** — `setInterval`-based countdown; a hidden dev-skip button (top-right corner, click to reveal) fast-forwards it for demos
- **Drill simulation** — Pass/Fail buttons branch to `growing` or `fractured` states
- **Data persistence** — `localStorage` keys `learnops_concepts` (array of concept objects) and `learnops_active` (selected concept ID); max 4 concepts
- **Transient content store** — `contentStore = new Map()` (module-level) holds full text keyed by concept ID; does not survive page reload (intentional)

**JS is organized into 16 numbered sections** (see the table of contents comment near line ~500):
1. DOM references
2. Pub/sub `Bus` — lightweight event emitter used for cross-section communication
3. `GEO` — polygon coordinate arrays (5 states × 8 polygons) for the SVG crystal shapes
4. `STATES` — display config (title/desc text per state)
5. Coordinate utilities + easing
6. `MorphEngine` — shared `requestAnimationFrame` loop; morphs polygon coordinates between states
7. Transition animation helpers (`playAnim`)
8. Grid rendering — builds tile + crystal SVG content
9. Data store — `localStorage` CRUD helpers + `_readFile()` shared file-reading helper
10. Drawer UI
11. Concept list render
12. CRUD — `startAddConcept()` (content-first creation form), `renderAddTrigger()`, `deleteConcept()`
13. `setState()` + `applyControlsForState()`
14. Pipeline handlers — `extract()`, `showContentOverlay()`, `hideContentOverlay()`, `drill()`, `drillPass()`, `drillFail()`, `consolidate()`, `completeConsolidation()`, `fastForward()`
15. Timer
16. Init / restore

**CSS is organized into 12 numbered sections:**
1–10. Base styles, layout, grid, crystal, card, buttons, drawer, concept list, states, animations
11. Content overlay (shown when clicking Extract on a legacy `instantiated` concept)
12. Drawer creation form (`.creation-form`, `.creation-name-input`, `.creation-footer`, etc.)

## Content-First Concept Creation

Concepts are created via a form embedded in the drawer (`startAddConcept()`). The form collects content first, name second, and creates the concept directly in `growing` state — bypassing `instantiated` entirely.

**Flow:**
```
Drawer → paste/upload content → type name → "Add Concept →" → concept born in 🌱 growing
```

**`startAddConcept()` form features:**
- Two tabs: **Text** (textarea with cycling placeholder) and **File** (.txt/.md/.pdf upload with drag-and-drop)
- "⌘ Paste from clipboard" button in the Text tab (`navigator.clipboard.readText()` with `execCommand` fallback)
- "Add Concept →" stays disabled until both content and name are provided
- On submit: stores full text in `contentStore`, persists `contentPreview` (first 500 chars) + `contentType` + `contentFilename` to localStorage, creates concept in `growing` state

**`_readFile(file, onSuccess, onError)`** — shared helper used by both `startAddConcept` and `showContentOverlay`:
- Validates extension (.txt/.md/.pdf) and size (≤2MB)
- PDF: ArrayBuffer → BT/ET regex extraction; fallback message if <50 chars extracted
- Text: `FileReader.readAsText()`

## Three-Stage Pipeline

1. **Ingest** (at concept creation) — user provides raw content (paste or file upload); concept is born in `growing` state with content stored
2. **Drill** — Socratic stress-testing; pass keeps `growing`, fail transitions to `fractured` (requires repair before re-drill)
3. **Consolidate** — 24-hour sleep-gated hibernation; timer expires → concept becomes `actualized` 💎

> The "Extract" step (clicking "1. Extract" on a card) still exists as a fallback for legacy `instantiated` concepts in old localStorage data. New concepts never need it.

The biological constraint of hibernation-over-death is intentional: concepts go dormant rather than disappear, reducing shame spirals for learners with executive function variability.

## Integration Roadmap (per README)

The prototype is a UI demo. The intended production system uses Claude Agent Skills for each stage — extraction, drilling, and consolidation — none of which are wired up yet.
