---
name: socratink Design System
description: Designing for socratink — a metacognitive learning product. Use this skill whenever you are producing marketing, in-app, or documentation designs for socratink. It enforces the cream/ink/violet palette, Geom + Inter typography, the crystal polygon motif, motion/audio implementation rules, and the technical rendering constraints that support the UX doctrine.
---

# socratink design skill

This is the technical design-system surface for socratink. It names the tokens, typography, component implementation rules, motion timings, audio helpers, and rendering constraints that keep product surfaces consistent. Product feel, narrative voice, and the metacognitive happy path live in [socratink-ux.md](socratink-ux.md).

## When to load this skill

Use it when:
- Building marketing pages, landing components, FAQ sections, or pricing surfaces for socratink.
- Prototyping in-app views: the graph board, drill chat, sidebar, crystal tile state, onboarding, session summary.
- Writing product copy (button labels, state messages, empty states, emails, errors).
- Producing exports (PDF handoffs, PPTX decks) that represent the brand externally.

## Foundations

Read these first — in this order:

1. `socratink-ux.md` — product feel, copy voice, and concept-flow doctrine.
2. `colors_and_type.css` — the single source of truth for every token. Load it as the first stylesheet in any HTML you produce.
3. `preview/` — small cards that demonstrate each part of the system in situ.
4. `ui_kits/website/` and `ui_kits/app/` — fully-built React reference implementations to crib component shapes from.

## In-app default: Antigravity theme

The shipping in-app surface (`public/index.html`) loads `public/antigravity.css` and applies `.antigravity-theme` to `<body>` unconditionally. The rules below describe the **canonical marketing aesthetic** and remain authoritative for any cream-paper surface; treat the Antigravity layer as a deliberate, user-approved exception for the in-app shell:

- **Palette** — Antigravity light keeps `--cream-50` / `--ink-900` underneath but introduces `--accent-color` `#9067C6` (light) / `#9E8BFF` (dark) and `--accent-mint` `#4DBA8A` (light) / `#3CDDC7` (dark) as paired accents, with a graphite dark-mode page of `#18181b` (Pattern A unified scale) and a light-mode neutral surface of `#F2F0F5` for glassy panels. The mint is no longer reserved solely for the solidified state inside this theme.
- **Type** — Outfit (variable) is loaded alongside Inter and Manrope from Google Fonts and used for in-app display headings (`.ignition-title`, `.hero-title`, ignition/hero eyebrows). This is the only sanctioned fourth family and the only sanctioned Google-Fonts dependency; do not extend it to additional surfaces without explicit approval.

For marketing pages and external exports, fall back to the Core rules below verbatim.

## Core rules

Follow these without exception unless the user explicitly overrides one:

### Palette (use only)
- **Page** — `--cream-50` `#F7ECE1`. Never pure white in the light theme.
- **Text** — `--ink-900` `#242038`. Never true black.
- **Primary** — `--violet-600` `#9067C6`. One accent per screen.
- **Secondary** — `--lavender-500` `#8D86C9`. Kicker text, dusted surfaces.
- **Neutral** — `--mauve-200` `#CAC4CE`. Locked states, empty dashes.
- **Reserved** — `--success` `#4DBA8A` (only on solidified state), `--danger` `#E05C6B` (only on fractured crystal glow, subdued).

No neon purples. No clinical blues. No gold. No flat gradients from blue-to-purple.

### Type
- **Display** — Geom (variable, plus matching italic). The brand face.
- **Body** — Inter (variable, optical sizes). Weights 300–600 in practice.
- Manrope (variable) is loaded as a secondary fallback for display, not a first-class option.
- All three are self-hosted from `fonts/` — no Google Fonts. Don't introduce a fourth family.
- Use fluid `--text-*` clamp scales; don't write bespoke `font-size` in px.
- Tracking is load-bearing: `--tracking-hero` (-0.06em) for display, `--tracking-kicker` (+0.18em, UPPERCASE) for eyebrows. Eyebrows are the only uppercase text in the system.
- Body copy leans lighter than most marketing sites — `font-weight: 300` in the hero lede, `h4` at weight 500.

### Motif
The **crystal polygon** is the one distinctive brand illustration. It is the product's core metaphor:
- Dual-diamond, faceted, with a vertical axis.
- On a cream page, rendered with `--violet-600` strokes and `--lavender-500` mid-plane fills.
- Scales to nodes on the graph board and to the brand mark.
- Never stylized in a new way. Never recolored.

### The isometric board
The primary in-app map surface is an **isometric grid of tiles**. Tiles use the `--tile-top / left / right` tokens; each tile carries a crystal polygon whose live training state is `primed`, `needs repair`, or `solidified`; no-evidence/null state renders quietly. The board is always isometric, always cream.

### Constellation sibling view
Constellation is the only scoped graph-view exception: a secondary SVG orientation surface with orbiting crystal nodes and evidence-lit edges. It derives state from training evidence, keeps Route as the reconstruction default, and must not reveal future labels, mechanisms, study content, or source previews before reconstruction evidence exists.

### Motion
- Standard easing `cubic-bezier(0.2, 0.8, 0.2, 1)`. Spring `cubic-bezier(0.34, 1.56, 0.64, 1)` **only** on solidified-state celebration.
- Durations cluster at 140 / 220 / 320ms for ordinary interaction. Crystal polygon morphs may use 600ms; avoid 1s+ except ambient body blooms.
- `IntersectionObserver` stagger-in on marketing sections, 150–300ms delay between. No scroll-hijacking. No parallax hero images.
- Respect `prefers-reduced-motion: reduce`.
- The in-app Settings -> Reduced motion toggle persists `socratink.motion = "reduced"` to localStorage, surfaces as `html[data-motion="reduced"]` (preloaded inline by `public/index.html` and the login page), and is mirrored across base/components/crystal/layout/login/experiment stylesheets via `public/js/motion.js`.

### Audio
- Canonical implementation lives in `public/js/audio.js`; retune there rather than creating new helpers.
- `playKeyClick` (F brush): lowpass noise around 600Hz, about 18ms. Bound to printable keystrokes in the Door concept field, source-attach fields, and Launch Pad input (`#launch-pad-input`).
- `playFocusTap` (I breath): highpass noise around 4kHz, about 10ms. Sidebar, bottom-nav, and primary-control focus.
- `playTileClick` (D thud): 60Hz square plus bandpass noise. Iso-board tile activation.
- `playDrawerToggle` (F body): lowpass cloth around 1.1kHz, about 30ms. Open/close of the desk drawer.
- `playSubmitChime`: long G4 to C4 settle. Reserved for the Ignition submit moment.
- No ambient loops, notification stings, or UI-as-instrument behavior.

### Cards
One card pattern across the product:
```
background: linear-gradient(180deg, rgba(white, 0.96), rgba(cream-50, 0.96));
border:     1px solid rgba(ink-900, 0.10);
border-radius: 16px;
box-shadow: 0 8px 32px rgba(violet-600, 0.10),
            inset 0 1px 0 rgba(white, 0.78);
padding:    24–32px;
backdrop-filter: blur(18px);
```
Hover lifts 3px, swaps border to `rgba(violet-600, 0.30)`, bumps shadow. That's the whole vocabulary.

### Iconography
- **Lucide** (`lucide-react` in the app; SVG CDN in prototypes) for marketing + shared UI.
- **Material Symbols Outlined** for in-app chrome only (sidebar, toolbar).
- Stroke 1.8, sizes 16–24 px, `currentColor` always.
- **No emoji, ever.** Not in headers, not in chips, not as decoration.

## UX Doctrine Pointer

Before designing a concept-facing surface, read [socratink-ux.md](socratink-ux.md) for the metacognitive happy path, copy voice, forbidden graph claims, and state-change meaning. This file does not restate that narrative; it only defines how to render the system once the UX contract is known.

Casing implementation: lowercase for product name and state tokens (`primed`, `needs repair`, `solidified`); Title Case for section headings; UPPERCASE with `--tracking-kicker` only on eyebrow labels.

## What to avoid

Hard forbidden patterns — these will fail review:

- Pure white page backgrounds (use `--cream-50`).
- True black text (use `--ink-900`).
- Stock photos, AI-generated portraits, hero photography of students in libraries.
- Emoji in any product surface.
- "Colored left border + rounded card" AI-slop pattern.
- Blue-to-purple gradient hero washes.
- Noise / grain / film-grain overlays.
- Rotating, skewing, or recoloring the brand mark.
- Streaks, XP bars, leaderboards, badges, achievement popups.
- Scored language during the cold attempt ("quiz", "test", "assessment", "score").
- Exclamation marks.
- Hype adjectives (revolutionary, next-generation, supercharge, unlock, game-changing).
- Scroll-hijacking, heavy parallax, autoplay video hero.
- Custom fonts outside Geom + Inter (with Manrope as fallback) without user approval. The in-app **Antigravity** theme's use of Outfit (loaded from Google Fonts for `.ignition-title` / `.hero-title` / eyebrow text) is the one approved exception; do not extend it elsewhere.
- A third accent color introduced ad-hoc. If you need semantic variance, use the tokens (success for solidified, danger only on fractured glow).
- `font-size` written in raw px — use the fluid `--text-*` tokens.

## Working pattern

When given a socratink task:

1. Read `README.md` end-to-end before writing a single line.
2. Link `colors_and_type.css` first. Reach for tokens — never invent hex values inline.
3. For any component more complex than a button, find its cousin in `ui_kits/` and crib the shape.
4. Write copy last — after the layout is right — and cold-read it against [socratink-ux.md](socratink-ux.md). If a sentence would feel at home on a SaaS landing page from 2018, rewrite it.
5. For state messaging (`primed` / `needs repair` / `solidified` / no-evidence), pull the exact tone from [socratink-ux.md](socratink-ux.md). For any concept-facing surface, re-read its metacognitive happy path before designing — every state-change claim must be earned by the rule table there.
6. Before shipping: grep your output for `!`, emoji, the literal strings "AI-powered", "revolutionary", "unlock", "supercharge". Remove.

## Deliverables checklist

Every socratink design should:

- [ ] Link `colors_and_type.css` first.
- [ ] Use cream page, ink text, one violet accent.
- [ ] Carry the crystal polygon motif somewhere visible (nav mark at minimum).
- [ ] Use Geom for display, Inter for body (Manrope as fallback only).
- [ ] Have visible warm-light shadows (violet-tinted), not gray.
- [ ] Respect `prefers-reduced-motion`.
- [ ] Pass the copy-voice grep above.
- [ ] Handle dark mode (or explicitly declare "light-only surface" in a comment).
