# Landing page refresh brief: socratink.ai

A self-contained brief for an agent updating the **socratink.ai** marketing/landing site. The current landing is outdated relative to the in-app voice and the recently-locked naming-refactor decisions. This brief consolidates everything an agent needs without access to the in-app codebase.

The app itself lives at `app.socratink.ai` (separate property; not edited by this brief). The brief is for the landing-marketing surface only.

---

## What socratink is (one paragraph)

socratink is a metacognitive learning tool for learning by reconstruction. The learner names a concept they want to understand, optionally attaches source material, and is taken straight into a **smallest actionable route** through the idea. The learner makes an unscored **cold attempt** before any explanation is shown. socratink shows targeted study only after the attempt, then asks the learner to reconstruct it again later under spacing. The graph of what's "learned" updates only when the learner provides reconstruction evidence — never from reading, viewing, or generating.

The core promise: **see what you can actually explain.**

---

## Brand and typography (hard rules)

- **`socratink`** — always lowercase in copy. Even sentence-initially, unless an external platform constraint forces otherwise.
- **No typographic emphasis on either syllable.** Don't write `socrat'ink'`, `socrat<em>ink</em>`, or `socra<strong>tink</strong>`. The wordmark stays flat, lowercase, plain. The brand reads as `socrat-ink` under the field-journal motif because the surrounding voice does the work; the wordmark itself stays neutral.
- **No brand-syllable extensions as nouns or verbs.** No `tink it`, `Inkwell`, `Inkstand`, `Pen`, etc. The brand name `socratink` is the only place either syllable appears as a semantic unit.
- **The visually-hidden `<h1>` of the page (for screen readers) is exactly `socratink`.** Not "socratink: see what you can actually explain." Not "socratink learning." Just `socratink`. The tagline goes in a separate `<h2>` or marketing copy block, not in the page heading.
- **Visual register options:** cream paper (#F2F0F5) with violet (#9067C6) ink accents, OR obsidian sky (#0B0D17 to #18181b graphite) with violet/lavender accents. Pick one for the landing or design a tasteful day/night switcher. **No neon. No gradient borders. No "AI" gradients in violet/blue.** The visual register matches a reading room, not a SaaS dashboard.

---

## Motif and voice (load-bearing)

The chosen voice register is **reading room and field journal**. Scholarly-naturalist — Audubon's notebooks, Darwin's marginalia, the patient tutor at the next desk. Not dark-academia roleplay; not literary. Quiet, exact, evidence-respecting.

### Voice rules
- calm, precise, Socratic
- plain complete sentences
- lowercase `socratink` everywhere
- **no exclamation marks**
- **no emoji**
- no hype, no praise that sounds like evidence
- no diagnostic framing
- no gamification vocabulary

### Anti-references (the chosen voice MUST NOT cross any of these)
- No gamification: streaks, XP, badges, leaderboards, ranks, combos, achievement popups.
- No mastery / completion / progress claims. Reading a thing does not mean you "know" it.
- No diagnostic labels: beginner, intermediate, advanced, schema, learning-style.
- No clinical SaaS, neon-dark dashboards, stock education imagery, emoji-led encouragement, hype copy.
- No graphs that look like content browsers, progress bars, or mastery charts.
- No quiz-app framing: scoring cold attempts, framing struggle as failure.
- No AI-tutor-knows-your-mind framing. Never say socratink "personalizes," "knows you," "tailors just for you," "understands your brain."

### Forbidden vocabulary (no exceptions)
- mastered, completed, unlocked, leveled-up, achieved, polished, gemmed
- score, scoring, ranked, rank
- XP, streak, badge, trophy, combo, win, quest, loot, power-up, reward, bonus
- crush, supercharge, revolutionary, AI-powered, game-changing
- "tailored just for you", "knows your mind", "understands you"
- challenge (in the cold-attempt context — this is on-app forbidden too)
- correction (in the diagnostic / defect-framing sense)

### Allowed verbs (these came through the in-app refactor)
- begin, open (an entry / a page / a draft route), reconstruct, sketch, repair, return, record, revisit, read, attempt, spaced re-drill, study
- **Avoid `enter` as a verb** for entering an "entry" — the field-journal motif uses `open` instead. (You "open a journal entry," not "enter" one.)

---

## Vocabulary the in-app refactor locked (use these on the landing page)

| Concept | Term | Notes |
| --- | --- | --- |
| Product | `socratink` | Always lowercase. |
| Empty-state nav for starting a new concept | `New Entry` | (replaces older "Ignition") |
| Primary action — the first reconstruction | `Draft from memory` | Use `Use this draft` when the scaffolded draft surface is already open. |
| The learner's source-less threshold submission | `launch attempt` | Raw learner text before the route exists; not learning evidence. |
| The smallest viable path the learner is taken into for a source-less concept | `smallest actionable route` | Produced from the launch attempt; do not use it as a synonym for the learner's input. |
| The act of attempting from memory before any explanation | `cold attempt` / `first cold attempt` | Domain noun. |
| The learning unit in the graph (learner-facing) | `entry` | (replaces the older internal "room" / "node") |
| A grouping of entries under a backbone branch | `section` | (replaces the older internal "cluster") |
| The repair-history record | `field journal` | (in-app: replaces "Repair History") |
| The spaced re-attempt | `spaced re-drill` | Domain noun; lowercase in copy. |
| The draft graph generated from sketch + source | `provisional graph` / `draft route` | Domain noun. |
| The visible-evidence graph | `evidence map` | Domain noun. |

### State labels (when shown on entries)
- no badge / `ready to reconstruct` — no learner reconstruction is on record yet
- `primed` — learner reconstruction evidence is on record; the next action is derived from it
- `needs repair` — learner reconstruction evidence has named gaps to repair
- `solidified` — you reconstructed under spacing; durable evidence on record

---

## Sample copy patterns (use these as register exemplars)

### Hero — what to say above the fold

Working hero options (pick one or remix):

**Option A (method-first):**
> See what you can actually explain.
>
> socratink is a reading room for learning by reconstruction. Bring source material, sketch how you think it works, then try from memory before any explanation appears. The graph only changes when you reconstruct.

**Option B (anti-pitch):**
> Not a flashcard app. Not an AI tutor. Not a quiz.
>
> socratink asks you to write what you think — *before* it shows you what it knows. Then it asks again, later, under spacing.

**Option C (quiet description):**
> socratink keeps the page quiet until your evidence changes the map.
>
> A reading-room tool for what you can actually reconstruct.

Each of these stays under 240 characters. Each respects: lowercase `socratink`, no hype, no exclamation, no emoji, no AI marketing, no completion claims.

### How-it-works section (the loop)

Three or four steps, each one to two sentences. No icons-with-checkmarks. No animated progress bar. Plain numbered scaffolding:

> **1. Bring source material.**
> Articles, transcripts, notes, your own model. socratink drafts a provisional graph from what you give it.
>
> **2. Sketch your starting model.**
> Parts, guesses, examples, confusions. No polished answer needed.
>
> **3. Draft from memory.**
> An unscored cold attempt — your words, before any explanation. socratink uses what you wrote to find the gap.
>
> **4. Return later.**
> Only spaced re-drill changes the record. The graph stays honest because evidence comes from your reconstruction.

### What socratink is *not* (anti-pitch section)

A short list, plain text, no visual treatment. **The negative space is what users opt in for.**

> - Not a quiz app — your cold attempt is unscored.
> - Not an "AI tutor" — socratink doesn't claim to know your mind.
> - Not a flashcard deck — recognition isn't reconstruction.
> - Not a course platform — there are no levels, no completion, no streaks.
> - Not a content browser — the graph is a record of evidence, not a map of what's available.

### Trust line (footer or near CTA)

> socratink doesn't reward reading. It records what you can actually rebuild.

Or:

> The graph stays honest because evidence comes from your reconstruction.

### CTA

Primary CTA: `Open socratink` or `Open a smallest route` or `Draft from memory`

**NOT acceptable CTAs:**
- "Get started for free" (SaaS marketing register)
- "Start your journey" (gamification adjacent)
- "Try our AI tutor" (anti-reference 7)
- "tink it" (brand-syllable extension; locked-out)

### Sign-in line

> Continue with Google
>
> *or*
>
> Continue as guest

Both verbs in lowercase except the brand name "Google." No "create account" / "sign up" framing — the model is opt-in-and-stay-anonymous-or-sign-in-when-you-want-sync.

---

## Sample BAD copy (rewrite if you see anything like this)

These would appear in any generic ed-tech landing — they directly violate this brief.

| ❌ Rewrite | ✅ With |
| --- | --- |
| "Master any concept faster!" | "See what you can actually reconstruct." |
| "AI-powered personalized learning" | "A reading room for what you can actually explain." |
| "Track your progress with streaks and XP" | (delete; gamification is anti-reference) |
| "Built for the modern learner" | "For learners who want to know what they can rebuild from memory." |
| "Try our AI tutor — it adapts to you!" | "socratink draws a provisional map and asks you to test it." |
| "Achieve mastery in 30 days" | (delete; mastery framing is forbidden) |
| "Discover your learning style" | (delete; diagnostic labels are anti-reference) |
| "Unlock your potential" | (delete; gamification + hype) |
| "Level up your study game" | (delete; gamification) |

---

## Recommended landing-page scaffold

If the agent has free rein on structure, recommend:

1. **Hero** — wordmark + one-line method statement + primary CTA. No animation. No "particles" or "constellation" effects (those are app chrome, not marketing).
2. **The loop (how it works)** — four numbered steps as above.
3. **What socratink is not** — anti-pitch list. Crucial differentiator.
4. **A worked example** — one concrete walk-through using a real concept (e.g., "How a learner uses socratink to study photosynthesis"). Show: the smallest actionable route, the cold attempt, the targeted repair, the spaced re-drill. Keep it text-heavy, scholarly. *Optional: skippable.*
5. **Trust paragraph** — the evidence-based promise; what the graph means and doesn't mean.
6. **Sign-in / try-it CTA** — Continue with Google + Continue as guest, with one-line "we keep what you write on this device until you sign in" reassurance.
7. **Footer** — socratink lowercase wordmark, links (about, contact, privacy), no social-icon row larger than the wordmark itself.

### What NOT to include
- Testimonials / star ratings — the product hasn't earned them and the persona explicitly distrusts them.
- "Trusted by learners at [logos]" — same.
- A "Pricing" page section unless pricing actually exists. If there's no paid tier, omit; don't pretend.
- Animated counters, "X concepts mastered today" tickers, or any "live activity" feed.
- A chatbot widget. socratink is not a chatbot.
- "Try the demo" with a fake AI conversation.

---

## Reference sites — what to study, what to imitate, what to avoid

### Top three closest cousins (study these first)

- **[Day One](https://dayoneapp.com)** *(journaling app)* — the closest aesthetic and metaphor cousin to socratink's chosen field-journal motif. Notice how they market journaling without gamification (no streaks above the fold, no "don't break the chain"). Steal: the scaffold of "what is journaling for" → "how this app supports it" → "what you get." Lead with the artifact (a journal entry) rather than the outcome.
- **[Anki](https://apps.ankiweb.net)** *(spaced-repetition flashcard tool)* — the sober gold-standard for "evidence-based learning tool that refuses to be cute." Plain, technical, almost academic. No hero illustration. Steal: the willingness to look austere instead of friendly. The persona test confirmed users like the imagined target trust this register.
- **[iA Writer](https://ia.net/writer)** — prose-led marketing. Their landing reads like an essay, not a product page. Steal: long-form sentences as the dominant element above the fold; tagline "Plain text. Everywhere." as the model for tagline density.

### Voice / tone exemplars

- **[Are.na](https://are.na)** — "this is a tool, not a product" register. About-page cadence (*"Are.na is for slow research, conversation, and the practice of looking again."*) maps directly to socratink's "see what you can actually explain."
- **[Things 3 by Cultured Code](https://culturedcode.com/things)** — typographic calm. One large beautiful serif headline, zero rotating animations.
- **[Obsidian](https://obsidian.md)** — quieter than Notion, respects-the-user-as-power-user voice. "Sharpen your thinking" is the upper bound for understated scholarly register.
- **[Robin Sloan's homepage](https://www.robinsloan.com)** — author site, prose-first. Hero is just a paragraph, almost no visual treatment. The closest model for "letting the writing be the design."
- **[Logseq](https://logseq.com)** *(open-source PKM)* — calmer than its competitors. Their footer warmth (`Made with ♥ by people who care about tools for thought.`) is the *upper limit* of allowable brand affection.

### Anti-pitch / "what we're NOT" exemplars

- **[HEY](https://hey.com)** *(Basecamp's email service)* — their landing's "It's not for everyone" page is the textbook anti-pitch. Tells you who shouldn't sign up. Steal: the courage to lose users at the door rather than mislead them in.
- **[DuckDuckGo](https://duckduckgo.com/about)** — the model for naming-your-anti-reference. Their entire brand is "we are not Google."
- **[Signal](https://signal.org)** — sober about *what* it is and *what it isn't*. No marketing fluff. "Speak Freely." End of pitch.
- **[Beeminder](https://www.beeminder.com)** — uses data without gamifying it. Anti-streak by design (they charge you when you fail). Useful for studying how to talk about evidence without claiming completion.

### Aesthetic / layout exemplars

- **[Mercury Banking](https://mercury.com)** — quiet typography in a category (banking) full of dashboards. The closest professional-tool reference.
- **[Bear](https://bear.app)** *(notes app)* — calm hero, cream-paper-ish palette, scholarly type pairing. Direct visual cousin to socratink's cream-paper theme.
- **[Blot](https://blot.im)** — extreme minimal. A single typeset paragraph as the entire homepage. Worth seeing as the *floor* of how minimal a landing can go.
- **[Arc Browser](https://arc.net)** — bolder than the others but still quiet by SaaS standards. A calibration point if some presence is wanted without crossing into hype.

### What NOT to imitate (concrete examples)

- **[Duolingo](https://duolingo.com)**, **[Quizlet](https://quizlet.com)**, **[Photomath](https://photomath.com)** — every gamification anti-reference rendered. The owl, the streaks, the leaderboard.
- **[Coursera](https://coursera.org)**, **[edX](https://edx.org)** — completion-claim and certificate-gamification register. The whole "Master X in Y weeks" industry.
- **[Khanmigo](https://www.khanmigo.ai)**, **[Replit Ghostwriter for learning](https://replit.com/ai)** — "AI knows your mind" framing.
- **Most YC-genre ed-tech landings** — even the well-written ones default to "Master X faster." Useful only as a calibration of genre averages, so socratink can sit visibly outside the band.

### Calibration exercise before commissioning

Open Day One, Anki, and HEY in three tabs. Read each above-the-fold copy block aloud. Notice how each tells you what the tool *is*, not how *amazing* it is. The landing-page agent's draft should hold its own in that lineup. If it reads more energetic than Day One but quieter than Coursera, it's in the right band.

---

## Acceptance checklist for the landing-page agent

Before publishing, verify:

- `socratink` is lowercase in every visible occurrence (alt text, og:title, twitter:title, the visually-hidden h1, footer wordmark).
- Wordmark has no typographic emphasis on either syllable. No `socrat'ink'`. No `socrat<em>ink</em>`.
- No exclamation marks in any copy.
- No emoji in any copy.
- No words from the forbidden-vocabulary list.
- No claims that reading or browsing changes learning state.
- No "AI tutor" / "personalized" / "knows you" framing.
- The hero says what socratink IS, not how AMAZING it is.
- The "what socratink is not" anti-pitch section exists. (Do not omit. It is the load-bearing differentiator.)
- A user with a screen reader hears `socratink` (lowercase, neutral), not `socrat tink` or `socrat ink`.
- The page renders legibly at iPhone SE 320×568 and Macbook Pro 13" 1280×800.
- Light/dark theme parity (if both are offered) — the voice doesn't shift between modes.
- The sign-in row exists and reads `Continue with Google` / `Continue as guest`.
- Page weight under 500KB (the calm voice is also a performance posture; no 4MB hero video).
- No third-party tracker beyond a privacy-respecting analytics tool (Plausible, Fathom, etc.).
- An OpenGraph image exists, depicts the wordmark + tagline cleanly, no stock photos of students-with-laptops.

---

## One-paragraph directive for the landing-page agent

You are refreshing the marketing landing page at socratink.ai. The product is **socratink** (always lowercase): a reading-room tool for learning by reconstruction. The voice is calm, Socratic, evidence-respecting; no hype, no exclamation marks, no emoji, no gamification, no AI-tutor framing. The brand wordmark stays flat lowercase — never typographically split (`socrat'ink'`), never extended into syllable-as-noun UI elements (`tink it`, `Inkwell`). Use the seven recommended sections above as a scaffold; the "what socratink is not" anti-pitch section is non-negotiable. Validate against the acceptance checklist before publishing. Expected deliverable: a working landing page draft (HTML or your framework of choice) plus a brief diff log explaining each non-obvious copy choice.
