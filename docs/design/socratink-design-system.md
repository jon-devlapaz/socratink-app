---
name: socratink Design System
description: Designing for socratink — a metacognitive learning product. Use this skill whenever you are producing marketing, in-app, or documentation designs for socratink. It enforces the cream/ink/violet palette, Geom + Inter typography, the crystal polygon motif, the product's calm, Socratic copy voice, and the binding metacognitive happy path (global threshold → provisional graph → local cold attempt + analogical fallback → locked silhouette → repair artifact → interleaving bridge → repair history).
---

# socratink design skill

socratink is a metacognitive learning product. It teaches by **student generation** — the learner attempts cold, receives targeted study, then re-drills the same concept spaced later. The UI is the interface layer of that loop. Every surface must either support generation, attribution, or spaced retrieval; nothing decorative survives.

## When to load this skill

Use it when:
- Building marketing pages, landing components, FAQ sections, or pricing surfaces for socratink.
- Prototyping in-app views: the graph board, drill chat, sidebar, crystal tile state, onboarding, session summary.
- Writing product copy (button labels, state messages, empty states, emails, errors).
- Producing exports (PDF handoffs, PPTX decks) that represent the brand externally.

## Foundations

Read these first — in this order:

1. `README.md` — full brand context, copy voice rules, iconography, visual foundations.
2. `colors_and_type.css` — the single source of truth for every token. Load it as the first stylesheet in any HTML you produce.
3. `preview/` — small cards that demonstrate each part of the system in situ.
4. `ui_kits/website/` and `ui_kits/app/` — fully-built React reference implementations to crib component shapes from.

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
The in-app surface is an **isometric grid of tiles**. Tiles use the `--tile-top / left / right` tokens; each tile carries a crystal polygon whose state is one of: `locked`, `primed`, `drilled`, `solidified`. Never draw the graph flat; never use a node-and-edge force-directed diagram. The board is always isometric, always cream.

### Motion
- Standard easing `cubic-bezier(0.2, 0.8, 0.2, 1)`. Spring `cubic-bezier(0.34, 1.56, 0.64, 1)` **only** on solidified-state celebration.
- Durations cluster at 140 / 220 / 320 / 700ms. Avoid 1s+ except ambient body blooms.
- `IntersectionObserver` stagger-in on marketing sections, 150–300ms delay between. No scroll-hijacking. No parallax hero images.
- Respect `prefers-reduced-motion: reduce`.

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

## The metacognitive happy path

The product's onboarding into any concept follows a fixed seven-screen arc. Designing any concept-facing surface without respecting it will fail review. Full narrative lives in `README.md` → *The metacognitive happy path*; the binding summary:

> **The graph proposes. The cold attempt creates something to repair. Study makes the repair inspectable. The spaced re-drill is the only proof.**

**Three friction traps the flow is designed against — never reintroduce them:**

1. **Generation fatigue.** Threshold and first cold attempt must not ask the same question. Threshold is **global**; cold attempt is **local**.
2. **Zero-signal frustration.** Low-vocabulary learners get an **analogical** generation, never a blind guess. Never label anyone zero-knowledge.
3. **Interleaving whiplash.** Going from repair → another cold attempt always passes through the **Interleaving Bridge** (Screen 6).

**The seven screens, in order:**

1. **Concept Threshold** — capture the learner's *global* starting map (parts, guesses, examples, confusions) *before* showing content. No graph mutation. Copy makes clear: “This is global context. The first room will ask one smaller question.”
2. **Provisional Graph** — a draft route presented as a hypothesis, never as a knowledge claim. Legend is limited to: *draft route · ready for first attempt · locked*. No mutation.
3. **First Cold Attempt (local)** — narrower than the threshold; quotes or paraphrases the threshold input, then asks **one** causal mechanism question inside the first node. Substantive → `locked → primed`. Non-substantive → no mutation; ask for a micro-generation. **Analogical fallback** for low-signal learners: familiar source analogy, learner predicts a causal relation *inside the analogy*, node stays `locked` until substantive.
4. **Locked Study Silhouette** — node title + one-line purpose + locked state + first-attempt CTA. **No explanation, no definitions, no solved diagram.** The absence of content is intentional.
5. **Study Repair Artifact** — scoped to the attempted node. Five parts: learner’s exact words → the hinge (one correction) → causal spine → one clarifying diagram → 1–2 connection cues. Never claim mastery here. CTA: **Choose next room** (routes to the bridge, not another cold attempt).
6. **Interleaving Bridge** — explains *why* the learner is leaving the repaired node (“the repair is fresh”), offers **2–3 nearby rooms** each with a one-line purpose (not a mechanism reveal), plus a non-punitive **“Take a short break instead”**. Never framed as reward or completion. Node stays `primed`.
7. **Repair History** — accumulates from attempts / feedback / repair reps / re-drills only. Never from reading.

**State-change rules (do not violate):**

- Only a **substantive, local cold attempt** may move `locked → primed`.
- Study stays `primed`; it sets the re-drill timer but never claims mastery.
- The interleaving bridge mutates nothing — it is a routing choice.
- `primed / drilled → solidified` happens **only** on a solid spaced re-drill.
- A non-solid spaced re-drill moves `primed → drilled`. Never red, never punitive.

**Graph-claim vocabulary:**

- *Allowed* — draft path · suggested first · ready for first attempt · primed for study · solidified through spaced reconstruction.
- *Forbidden* — you know this · mastered (from graph generation) · completed (from reading) · advanced (from fluent prose).

**Forbidden on threshold / graph / attempt screens:** the words *diagnostic, evaluate, beginner/intermediate/advanced, misconceptions*; learner-visible schema labels; curriculum claims; cross-concept mastery summaries. Schema inference is internal only — the learner never sees their own schema tier.

**Happy-path MVP cut (for prioritization):** Concept Threshold before any study-like page · pasted text + global learner-map inputs only · internal routing signals · provisional-graph copy · **local first cold attempt derived from threshold input** · **analogical cold-attempt fallback** · locked study silhouette · attempt-scoped repair artifact · **interleaving bridge with 2–3 next-room options + break** before another cold attempt · existing spacing + mutation rules unchanged.

## Copy voice

Calm, precise, Socratic. Reading room, not dashboard.

- **Second person, singular.** "You own the content."
- **Lowercase `socratink`**, always — even sentence-initial.
- **No jargon hype.** Never "revolutionary," "AI-powered," "10×," "unlock," "crush your goals," "supercharge."
- **No exclamation marks.** Ever.
- **Honor struggle.** A `drilled` (non-solid re-drill) state is described as "Worth revisiting." Never punitive, never consoling.
- **Strategy over ability.** Errors describe the missing link ("The causal connection between step 2 and step 3 needs a different angle"), never the learner ("You got it wrong").
- **No streaks, no XP, no badges, no leaderboards.** The reward is the crystal state change itself.
- **Admit the product's honest state.** Lines like "Still testing. Still learning." are load-bearing brand.
- **Imperative + verb-led marketing copy.** "Bring your material. Get a map. Clear rooms."

Casing: lowercase for product name and state tokens (`primed`, `drilled`, `solidified`); Title Case for section headings; UPPERCASE with `--tracking-kicker` only on eyebrow labels.

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
- Custom fonts outside Geom + Inter (with Manrope as fallback) without user approval.
- A third accent color introduced ad-hoc. If you need semantic variance, use the tokens (success for solidified, danger only on fractured glow).
- `font-size` written in raw px — use the fluid `--text-*` tokens.

## Working pattern

When given a socratink task:

1. Read `README.md` end-to-end before writing a single line.
2. Link `colors_and_type.css` first. Reach for tokens — never invent hex values inline.
3. For any component more complex than a button, find its cousin in `ui_kits/` and crib the shape.
4. Write copy last — after the layout is right — and cold-read it against the **Copy voice** rules above. If a sentence would feel at home on a SaaS landing page from 2018, rewrite it.
5. For state messaging (primed / drilled / solidified / locked), pull the exact tone from `README.md` → *Tone by surface*. For any concept-facing surface, re-read `README.md` → *The metacognitive happy path* before designing — every state-change claim must be earned by the rule table there.
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
