# socratink Design System

> **socratink.ai** — a metacognitive learning tool that increases signal, reduces cognitive load, and enhances real learning derived from **student generation**. The product strengthens active recall and mitigates the illusion of understanding that comes from mere familiarity.

This design system is the binding contract for how socratink looks, sounds, and moves. It is rooted in the product's single unifying principle: **metacognitive UX** — every surface is designed for the learner's awareness of their own cognitive process, not just the content. The aesthetic mirrors the work the product asks of its learners: **quiet, scholarly, crystalline.**

---

## Sources

This system is derived from the following materials:

| Source | Where | What it covers |
|---|---|---|
| Codebase | GitHub `jon-devlapaz/socratink-app` | Marketing site (`App.jsx`, `index.css`), in-app styles (`public/css/*.css`), brand mark (`public/favicon.png`) |
| UX framework | `docs/product/ux-framework.md` (same repo) | The product thesis, three-phase loop, node-state model, feedback calibration rules, voice |
| Uploads | `uploads/` (consumed into `assets/`) | `favicon.png` (primary mark), `socraTink.png` (palette reference), `tink_full_mobile.png` (isometric graph/board screenshot) |
| Brand notes | Provided by operator | Palette (cream-50, ink-900, violet-600, lavender-500, mauve-200), type pairing, motif (crystal polygon), voice posture ("premium-contemplative, reading room not dashboard") |

Assume the reader of this file does **not** have access to the above. If that assumption is wrong later, the citations above make it easy to drill deeper.

---

## Product context

socratink is (today) a single product surface with two faces:

1. **The app** (`app.socratink.ai`) — a React SPA. A sidebar of concepts, an isometric **grid board** of tiles, and on each tile a **crystal polygon** whose visual state (instantiated → growing → hibernating → fractured → actualized) is a **truthful record of verified understanding**. A drill chat panel drives the three-phase loop: **cold attempt → targeted study → spaced re-drill**. See `ui_kits/app/`.

2. **The marketing site** (`socratink.ai`) — a React landing page introducing the thesis, the loop, and the FAQ. Quiet type, cream page, violet accent. See `ui_kits/website/`.

Both surfaces share a single token set (`colors_and_type.css`).

### The product's unifying metaphor

The graph behaves like a **dungeon map**. Every node is a **room**. The cold attempt is stepping through the door before you know what's inside. Targeted study is the room revealing itself *after* the attempt. The spaced re-drill is the room's boss fight. New rooms open only when prerequisite understanding is real. The **graph tells the truth** — it is not a content browser or a completion checklist.

### What the visual language has to carry

- The graph must look **trustable**. A state change has to feel earned, not decorative.
- Struggle must be honored, not hidden. Colors for `drilled` (non-solid re-drill) are warm and return-worthy — never red, never punitive.
- Feedback is **calibrated to cognitive load** — a clean solidification gets a crisp crystallization; a scaffolded barely-solid retrieval gets a subdued, stabilizing effect. Both are true; the aesthetic mirrors the work.
- No streak fog, no gamification hype, no hollow badges. The reward layer is the state change itself.

---

## The metacognitive happy path

This is the binding narrative for **how the learner is onboarded into a concept** — and the most important design informant in this repo. It governs the shape of every concept-facing screen. Read it before designing any surface that touches a node.

### Design principle

> The graph **proposes** where to look.
> The cold attempt **creates something to repair.**
> The study view makes the repair **inspectable.**
> The spaced re-drill is **the only proof.**

A concept page is not where the learner goes to read. It is where **their understanding becomes inspectable.** socratink asks for the learner's **starting map** before showing explanatory content. That starting map shapes routing and repair — it must never create mastery claims.

### Friction fixes the flow must avoid

The shape of the path is a direct response to three traps — design against them continuously:

1. **Generation fatigue.** The threshold and the first cold attempt must not ask the same question twice. Threshold is **global**; cold attempt is **local**.
2. **Zero-signal frustration.** A learner without the technical vocabulary needs an **analogical** generation path, not a blind guess. Never label anyone zero-knowledge.
3. **Interleaving whiplash.** Moving from a repair artifact straight into another cold attempt needs a **bridge** that explains why the learner is leaving the just-repaired node.

### The path

```
Enter concept
  → Starting-map threshold (global model)         (Screen 1)
  → Build provisional graph / path                (Screen 2)
  → Local cold attempt derived from the threshold (Screen 3)
     └─ analogical fallback if signal is thin
  → Locked study silhouette if premature          (Screen 4)
  → Study repair artifact                         (Screen 5)
  → Interleaving bridge (pick a nearby room)      (Screen 6)
  → Later spaced re-drill
  → Repair history accumulates                    (Screen 7)
  ↓ Mutate graph truth only on solid reconstruction
```

### The seven screens

**1. Concept Threshold — global starting map.** *No graph state mutation.* The learner describes their **global** current model — rough is useful — before recognition-heavy content appears. Prompt asks for **parts, guesses, examples, or confusions** (not a mechanism). Optional paste for notes/syllabus/goal; one "what feels fuzzy" prompt; one confidence selector. Copy explicitly distinguishes: *"This is global context. The first room will ask one smaller question."* Primary action: **Build my starting path.**

**2. Provisional Graph.** *No state mutation.* A draft route is rendered from the starting map. Copy is explicit that the graph is a **hypothesis**, not a knowledge claim. Legend is limited to: draft route · ready for first attempt · locked. Primary action: **Start first attempt.**

**3. First Cold Attempt — local mechanism question.** *Still unscored.* The prompt is **narrower** than the threshold, and should **quote or paraphrase the learner's threshold input** before asking a single causal question inside the first node. Example: *"You said LLMs are built from lots of text and training. Narrow that into one causal guess: what do you think the training is trying to predict at each step?"* On submit — substantive: `locked → primed`, `drill_phase = study`. Non-substantive: no mutation; ask for a micro-generation.

   **Analogical fallback — when signal is too thin.** Pivot to an analogy-led generation *instead of* a blind guess. Rules: (a) give a familiar source analogy, never the target mechanism as the answer; (b) ask the learner to predict a causal relationship *inside the analogy*; (c) the node stays `locked` until a substantive micro-generation lands; (d) the learner is never labeled zero-knowledge.

**4. Locked Study Silhouette.** *Pre-attempt.* Node title + one-line purpose + locked state + first-attempt CTA. **No explanation, no definitions list, no solved diagram, no revealing examples.** The absence of content is intentional.

**5. Study Repair Artifact.** *Node is `primed`; content scoped to the attempted node only.* Five parts, in order: (a) the learner's exact words, preserved; (b) **the hinge** — one specific correction; (c) **causal spine** — a compact arrow chain; (d) **one clarifying diagram**; (e) 1–2 connection cues to nearby nodes, only after the local repair is readable. Do not claim mastery here. Primary action: **Choose next room** (which leads into the bridge, not directly into another cold attempt).

**6. Interleaving Bridge.** *Node remains `primed`; re-drill is not yet offered.* A short screen that names *why* the learner is leaving the just-repaired node ("the repair is fresh, so re-drilling Core Thesis right now would mostly test short-term echo") and offers **2–3 nearby rooms**, each with a **one-line purpose, not a mechanism reveal**. A non-punitive **"Take a short break instead"** is always present — spacing is a valid choice. Interleaving is **never framed as reward or completion**.

**7. Repair History.** *Accumulates from attempts, feedback, repair reps, and re-drills only — never from reading.* A growing field journal: repaired misconceptions, recurring gaps, alternate explanations, learner-authored summaries, causal bridges. The learner's own voice is the organizing unit, not the system's.

### What the system may claim — and when

| Moment | What the learner sees | What the system may infer | Allowed state change |
|---|---|---|---|
| Threshold submitted | starting map captured | routing signal, source dependence, causal depth | **none** |
| Provisional graph generated | draft path | first-node priority, prompt emphasis | **none** |
| Local cold attempt submitted | unscored node attempt | substantive vs non-attempt | `locked → primed` **only if substantive** |
| Study completed | repair artifact | study timestamp, next interleave target | stays `primed`; re-drill timer set |
| Interleaving bridge shown | small next-choice set (2–3 rooms + break) | route preference | **none** |
| Repair rep completed | practice history | self-rating, bridge quality | **none** |
| Spaced re-drill solid | proof through reconstruction | solid classification | `primed / drilled → solidified` |
| Spaced re-drill non-solid | needs revisit | gap metadata | `primed → drilled` |

### Copy guardrails for the happy path

**Safe:**
- "Your words shape the path; they do not grade you."
- "Give your best current map. Rough is fine."
- "What do you want to be able to explain when this clicks?"
- "This is global context. The first room will ask one smaller question."
- "Draft path." · "Suggested first." · "Ready for first attempt."
- "Let this one cool." · "The repair is fresh." · "Take a short break instead."

**Forbidden on these screens:**
- "Diagnostic" · "Evaluate your current understanding"
- "Beginner / intermediate / advanced"
- "We found your misconceptions"
- "You know this" from graph generation
- "Completed" from reading
- "Mastered" / "Advanced" from fluent prose

### Graph-claim vocabulary

Only these phrases may appear as graph-state copy:

- **Allowed:** *draft path · suggested first · ready for first attempt · primed for study · solidified through spaced reconstruction*
- **Forbidden:** *you know this · mastered (from graph generation) · completed (from reading) · advanced (from fluent prose)*

### Schema labels are internal

Routing signals, source-dependence scores, causal-depth estimates, schema profiles — the system may use them. **The learner never sees their own schema label.** No beginner/intermediate tier, no "your learning style," no curriculum claims. The graph's visible state is the only profile that exists.

### MVP cut (for design prioritization)

**Build first:** Concept Threshold before any study-like page · pasted text + global learner-map inputs only · internal routing signals · provisional-graph copy · **first cold attempt is local and derived from the threshold input** · **analogical cold-attempt fallback** for low-signal learners · locked study silhouette before attempt · attempt-scoped repair artifact after cold attempt · **interleaving bridge with 2–3 next-room choices plus a “take a short break” option** before another cold attempt · existing spacing and graph-mutation rules unchanged.

**Defer:** learner-visible schema profiles · long-term curriculum claims · cross-concept mastery summaries · rich notebook features · URL ingestion (until SSRF hardening + manual fallback ships).

---


## Index

| File / folder | What's in it |
|---|---|
| `README.md` | This file — orientation, content fundamentals, visual foundations, iconography. |
| `SKILL.md` | Agent Skill front-matter. Pull this skill into Claude Code / elsewhere to design with socratink's voice. |
| `colors_and_type.css` | The single source of truth. Primitive palette, semantic tokens, crystal state colors, type scale, shadows, radii, motion, dark mode. Import this first in any design. |
| `fonts/` | (Empty; Manrope + Inter loaded from Google Fonts — see **Type substitutions** below.) |
| `assets/` | Brand mark (`logo.png`), wordmark (`wordmark.png`), isometric board screenshot (`tink_full_mobile.png`). |
| `preview/` | Small HTML cards used by the Design System tab. Read them as a tour of the system. |
| `ui_kits/app/` | React/JSX recreation of the in-app experience: grid board, crystal tile, drill chat, sidebar, primary screens. |
| `ui_kits/website/` | React/JSX recreation of the marketing site: hero, three-phase explainer, FAQ, footer. |

---

## Content fundamentals

The product has **no human teacher** to manage attributions in real time. The interface *is* the attribution manager. Every piece of copy is either pushing the learner toward adaptive attribution ("I haven't built the model yet") or maladaptive attribution ("I'm not smart enough"). There is no neutral position. Copy is a cognitive-science surface, not decoration.

### Posture
**Calm, precise, Socratic.** It sounds like a reading room, not a dashboard. It sounds like a patient tutor who takes the learner seriously. It does not sound like a product pitch, a coach app, or a game.

### Voice

- **Second person, singular.** Copy talks to *you*. "You own the content." "You reconstruct from memory." The product rarely says "we." When it does, it's meta ("we ask you to build yours").
- **Lowercase product name.** `socratink` — even at the start of sentences. The wordmark is lowercase too.
- **Plain, complete sentences.** No telegraph style. Periods. Short paragraphs. The sentence "The floor dropped out." is the maximum drama the brand gets.
- **Verbs over adjectives.** "Bring your material." "Get a map." "Clear rooms." The product's promise shows up as things the learner *does*, never as things the product *is*.
- **Zero jargon that signals hype.** No "revolutionary," "AI-powered," "supercharge," "10×," "unlock your potential," "crush your goals." No exclamation marks. No emoji in product copy. Ever.
- **Admit the state of the product honestly.** The live site reads: *"Still testing. Still learning. socratink is in active development."* That kind of line is load-bearing brand, not filler.

### Tone by surface

| Surface | Tone | Example |
|---|---|---|
| Marketing hero | Invitation, not pitch | "See what you can **actually explain.**" |
| Value strip | Plain declarative | "No fake progress — the map updates only when you actually get it." |
| How it works | Imperative, low-volume | "Bring your material. Get a map. Clear rooms." |
| Drill prompt (AI) | Sparse, gap-identifying | "Explain why node B matters in the system." |
| `primed` state copy | Quiet acknowledgment | "You've stepped inside. The real challenge is ahead." |
| `drilled` state copy | Honored, not punitive | "Worth revisiting. The next gain is here." |
| `solidified` state copy | Earned, brief | "Cleared. You proved it." |
| Session cap / break | Warm, scientific, transparent | "Progress locked in. Your neurons do the rest while you're away." |
| Error / non-solid | Strategy, never ability | "The causal link between step 2 and step 3 needs a different angle." |

### Casing

- Lowercase for `socratink`, the CTA verb `tink it`, and node states (`primed`, `drilled`, `solidified`, `locked`).
- Title Case for major section headings ("How It Works", "Why It Feels Different").
- UPPERCASE **only** for the `kicker` eyebrow (`FAQ`, `NOT ANOTHER AI SUMMARY APP.`), with wide tracking.

### Forbidden patterns

- **No streaks in MVP.** If copy ever implies one, delete it.
- **No scored language during the cold attempt.** Never "quiz", "test", "exam", "assessment." Use "enter the room" / "what do you think this involves?" / "take your best guess."
- **No consolation copy.** Non-solid results don't get hype ("great try!"). They get useful, specific, strategy-framed next-step language.
- **No gamification words.** No XP, combo, unlock-as-reward, power-up, level-up, rank.
- **No AI product boilerplate.** Don't say "our AI". Say what the system does: "identifies what depends on what", "prompts for elaboration", "halts drilling at three successful retrievals."

### Trajectory vocabulary (internal only, shown as bands after the attempt)

The tier system `spark → link → chain → clear → tetris` is the product's **prediction-contrast** surface. It is shown only as *post-attempt* reflection on growth, always paired with interpretive framing ("Your cold attempt was a spark. Your re-drill hit chain. That jump is real learning."). Never a live score.

---

## Visual foundations

### Palette

Warm-muted jewel tones on a cream-paper page. Five primitives, plus two reserved semantics.

| Role | Token | Hex | Usage |
|---|---|---|---|
| Ink | `--ink-900` | `#242038` | All text, deep shadows, crystal lower edges. Treat as near-black; never use true black. |
| Primary | `--violet-600` | `#9067C6` | Accent strokes, active states, most interactive hover glow. The "crystalline" warm violet. |
| Secondary | `--lavender-500` | `#8D86C9` | Kicker text, dust on surfaces, crystal mid-planes, locked/hibernating state. |
| Neutral | `--mauve-200` | `#CAC4CE` | Locked tiles, empty-tile dashes, inactive chips. Calm, never sad. |
| Page | `--cream-50` | `#F7ECE1` | Every page background. **Never pure white** in the light theme. |
| White | `--white` | `#FFFFFF` | Raised card faces only; never a page. |
| Success | `--success` | `#4DBA8A` | `solidified` / actualized state. Single celebrant color. |
| Danger | `--danger` | `#E05C6B` | Reserved. Used only on `fractured` crystal glow — rarely, and muted. |

The palette explicitly **excludes**: neon purples, pure white pages, clinical SaaS blues, gradient-bluish-to-purple hero washes, gold trim.

### Type pairing

- **Geom** for display (variable weight + matching italic). The brand face — self-hosted from `fonts/Geom-VariableFont_wght.ttf` and `fonts/Geom-Italic-VariableFont_wght.ttf`. Geometric but humanist — enough softness for cream paper, enough structure for scientific tone.
- **Manrope** (variable) is loaded as the secondary display fallback, from `fonts/Manrope-VariableFont_wght.ttf`.
- **Inter** (variable, optical sizes + italic) for body — self-hosted from `fonts/Inter-VariableFont_opsz,wght.ttf` and `fonts/Inter-Italic-VariableFont_opsz,wght.ttf`. Weights 300–600 in practice.
- **Fluid clamp() scales** (`--text-xs` through `--text-display`) so one rule works from phone to large desktop. No responsive breakpoint overrides for type.
- **Tracking is a load-bearing signal:**
  - `--tracking-hero: -0.06em` — huge display headlines
  - `--tracking-display: -0.03em` — section heads
  - `--tracking-kicker: 0.18em` + UPPERCASE — eyebrow text (the only uppercase in the system)
- **Weights are deliberately low for scholarly tone.** `h4` is weight 500, not 600. Body copy leans on `font-weight: 300` in the marketing hero's lede.

### Spacing rhythm

4px base. `--space-1` = 4px, doubling/adjusting by rhythm: 4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96. Card internal padding is almost always `var(--space-6)` to `var(--space-8)` (24–32px). Section bands are `var(--space-24)` (96px) top/bottom.

### Corner radii

Soft — 1–1.25rem everywhere, with larger radii reserved for primary hero shells. Nothing is sharp; nothing is pill-shaped except actual pills.

| Token | Use |
|---|---|
| `--radius-sm` (10px) | Chips, inputs, small buttons |
| `--radius-btn` (10px) | Most buttons |
| `--radius-card` (16px) | Standard cards |
| `--radius-lg` (20px) | Primary panels |
| `--radius-xl` (27px) | Demo windows, marketing hero mock |
| `--radius-2xl` (32px) | Hero shells |
| `--radius-pill` | True pills — state chips, CTAs in nav |

### Shadows & elevation

**Violet-tinted, never gray.** Every shadow carries 10–20% `rgba(--violet-600, α)` so the elevation reads as warm light, not ink smudge. A card is `--shadow-card`; its hover is `--shadow-hover`; a raised dialog is `--shadow-raised`; the hero itself gets `--shadow-hero`. Inset 1px top highlight `rgba(--white, 0.52–0.82)` is used on gradient cards to imply a lit edge — this is what makes cream cards read as "paper."

### Backgrounds

- **Never flat.** Every background is a radial gradient plus a linear wash. See `--page-background` and `--hero-gradient` in `colors_and_type.css`. These are subtle — think "late-afternoon light through paper," not "Instagram filter."
- **Ambient blooms.** `body::before` and `body::after` carry `--page-bloom-primary/secondary` at huge blur (100–130px), translated off-center — two pale lanterns in the corner of the room.
- **Not full-bleed imagery.** socratink does not use hero photos or stock illustrations. The isometric **crystal board** is the one signature illustration; it may be placeholder-sized in mocks.
- **No repeating patterns or noise/grain textures.** The warmth comes from the gradient, not from noise.

### Animation & motion

- **Easing is almost always** `cubic-bezier(0.2, 0.8, 0.2, 1)` (`--ease-standard`) for ordinary hover/press, and `cubic-bezier(0.34, 1.56, 0.64, 1)` (`--ease-spring`) for `solidified` celebrations. A 600ms `--morph-ms` is reserved for crystal polygon fill transitions.
- **Durations cluster** at 140 / 220 / 320 / 700ms. No 1s+ animations except ambient body blooms.
- **No bouncy / fun motion on drill surfaces.** Drill is quiet. Spring easing only on `solidified` — the one moment that earns celebration.
- **`prefers-reduced-motion: reduce` is respected.** Crystal state transitions + hero loop both obey it — the repo's `App.jsx` and `crystal.css` both pin transitions to 0ms under the query.
- **No scroll-hijacking.** Simple `IntersectionObserver`-gated fade-ups with ~150–300ms `transitionDelay` staggers. That's the whole motion budget on the marketing site.

### Hover & press states

- **Hover** = `transform: translateY(-1 to -3px)` + swap of border from `--accent-border` to `--accent-border-strong` + bump from `--shadow-card` to `--shadow-hover`. The page lifts, it doesn't brighten.
- **Press / active** = `transform: scale(0.97)` on buttons, no color shift. The component admits it was touched.
- **Focus** = `--accent-ring` (3px `rgba(violet-600, 0.14)`). Never a thick blue outline; never nothing.
- **Disabled** = surface goes to `--surface-nested`, text to `--text-muted`, shadow off.

### Borders

- **1px, subtle.** `--border-subtle: rgba(--ink-900, 0.10)` is the default. Active states go to `--accent-border-strong: rgba(--violet-600, 0.30)`. Nothing heavier than that on a card.
- **No left-border-accent cards.** The "colored left border + rounded card" pattern is explicitly forbidden — it reads as AI-slop tropes and clashes with the jeweled palette.

### Transparency & blur

Used **sparingly**, and always for a reason:
- Nav bars: `backdrop-filter: blur(20px)` + `rgba(nav-surface)` for the "glass over paper" effect.
- Drill chat bubbles and tooltip backgrounds — heavy blur on overlay modals only.
- Avoid blur on normal cards and text blocks; the cream page does the softness work.

### Layout rules

- **Max content width** ≈ `max-w-7xl` (80rem, 1280px) with `mx-auto`.
- **Hero panels** go to `max-w-[86rem]` (1376px) with a 0.96fr / 1.04fr split favoring the visual side.
- **Cards breathe.** Interior padding of `var(--space-6)` (24px) minimum; `var(--space-8)` (32px) for feature cards.
- **One active cognitive target.** Per the UX framework: at any moment one thing must be clearly foregrounded, everything else dimmed. In practice: use `opacity: 0.5–0.6` on non-active nodes and full opacity on the active one. Never display more than ~3 things at peer prominence on a drill surface.
- **Two to three visual hierarchy levels per screen.** Kicker → heading → body. If you need four, you have too many things.

### Color vibe of imagery

When imagery is used (rarely), it is:
- **Warm, low-saturation.** Matches the cream page.
- **Isometric, line-weight restrained, violet on cream.** The `tink_full_mobile.png` reference is the canonical example.
- **Never photographic.** No stock portraits, no landscape hero photos, no "student-in-library" imagery.
- **Never grainy, never noisy, never blurred as an effect.**

### Cards — the anatomy

A `landing-card` / standard socratink card is:

```
background: linear-gradient(180deg, rgba(white, 0.96), rgba(cream-50, 0.96));
border:     1px solid rgba(ink-900, 0.10);
border-radius: 16px;
box-shadow: 0 8px 32px rgba(violet-600, 0.10),
            inset 0 1px 0 rgba(white, 0.78);   /* the lit edge */
padding:    24–32px;
backdrop-filter: blur(18px);
```

Hover adds `translateY(-3px)`, swaps border to `rgba(violet-600, 0.30)`, bumps the shadow. That's the whole card system.

---

## Iconography

### System

socratink pulls its icons from **[Lucide](https://lucide.dev/)** (via the `lucide-react` package in the live codebase). Lucide is the chosen set because it is:
- **Line-weight restrained** (stroke 1.8–2), matching Manrope's humanist geometry.
- **Consistent corner radii** that echo the 1–1.25rem UI radii.
- **Large enough** (1000+ icons) to cover every surface need without leaving the set.

In mocks and prototypes here, load Lucide from CDN — e.g. `https://unpkg.com/lucide@latest` as a script, or use the standalone SVG source if React isn't loaded.

### Icons in active use (observed in codebase)

`Brain`, `Shield`, `Sparkles`, `Lock`, `Activity`, `ArrowRight`, `ChevronRight`, `ChevronDown` — from `lucide-react`. Plus a hand-rolled **Discord** SVG glyph (because Lucide does not ship brand logos).

**Sizes** in practice: 16, 18, 20, 22, 24 px. Stroke weight 1.8. Use `currentColor` so icons inherit text color.

### Material Symbols (in-app only)

The in-app views use **Material Symbols Outlined** for sidebar nav, toolbar, etc. — loaded as a variable font with `FILL 1, wght 400, GRAD 0, opsz 24`. This is a second icon system, reserved for app chrome. **Do not** mix Material Symbols into marketing surfaces — Lucide only there.

### Brand mark

The primary mark (`assets/logo.png`) is a **dual-diamond crystal polygon with a vertical axis** rendered in violet on cream. It is the crystal polygon motif — the same shape the app draws at large scale on each graph tile. The mark *is* the visual thesis of the product.

- Minimum size: 24×24 px (favicon is 32×32).
- Clearspace: 0.5× mark height on all sides.
- On dark backgrounds, use as-is (the mark works on `--surface-page` dark mode).
- Do **not** rotate, skew, or recolor the mark.

### Emoji

**Never used** in product, marketing, or docs copy. Not in headers, not in bullet lists, not in status chips. The brand's warmth comes from typography, color, and the crystal motif — not from emoji.

### Unicode as decoration

Rarely, and only structural: `§` appears in one illustration (the IsoVault locked vault). Arrow glyphs (`→`) are allowed in copy as literal directionals but are preferably replaced by Lucide `ArrowRight` in UI.

### Illustrations

The codebase uses three **isometric SVG illustrations** (`IsoExtraction`, `IsoVault`, `IsoreFeyn`) for the three-step explainer — each drawn in `currentColor` violet strokes on cream, using simple polygons + sparse circle nodes. When an illustration is needed here and we don't have the exact asset, **use a placeholder** (bordered cream rectangle with a muted label) rather than inventing a new illustration — the visual vocabulary is specific enough that off-brand SVG will clash immediately.

---

## Type substitutions

- **Geom**, **Manrope**, and **Inter** are all self-hosted variable fonts shipped under `fonts/`. No Google Fonts, no external CDN fetch — the system works offline.
- If a different weight or optical size is needed, set it via `font-weight` / `font-variation-settings` directly; the variable axes cover 100–900.

---

## How to use this system

1. Link `colors_and_type.css` as the first stylesheet in any new HTML file.
2. Read `README.md` (this file) + `SKILL.md` before writing copy.
3. For component shapes, open the relevant `ui_kits/<product>/index.html` and crib from the JSX components there — they are pixel-close to production and already use the tokens.
4. When in doubt: cream page, ink text, one violet accent, one state change at a time.
