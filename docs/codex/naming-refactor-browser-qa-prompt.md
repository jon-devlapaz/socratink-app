# Browser QA prompt — socratink naming refactor (dev branch)

A self-contained Browser QA brief for an agent with native Chrome access. The target is the **in-app surface** at `app.socratink.ai` (or your local dev mirror) on the `dev` branch — not the marketing landing.

You're verifying that the recent naming refactor (motif: "Reading Room and Field Journal") has been applied cleanly and that no orphan vocabulary or visual regression slipped through. Read this entire brief before opening the browser.

---

## What changed (background, not a checklist)

The in-app vernacular was rewritten to align with the canonical domain language in `UBIQUITOUS_LANGUAGE.md`. Five batches landed on `dev`:

| Batch | Move |
|---|---|
| 0 | Voice + a11y cleanup: lowercase brand everywhere, drop `Socratic Canvas` from login title, retire diagnostic words (`challenge`, `Needs correction`), remove `data.reDrillBand` trajectory-band leak from learner copy, swap `Locked container` → `Locked section` and `${n} drill nodes` → `${n} entries`. |
| 1 | Disputed slot resolutions: top-level nav `Ignition` → **New Entry**; primary action `Start Cold Attempt` → **Try from memory**. |
| 2 | Dungeon-map vocabulary retires: `room` → `entry`, `cluster` → `section`, `drill node` / `subnode` → `entry`, `drill branch` → `entry branch`, `node` (in narrative copy) → `entry`. |
| 3 | `Starting map` → `Starting sketch` cascade; `Enter` → `Open` verb swap (the journal motif "opens" entries, no longer "enters" rooms). |
| 4 | Cleanups: `Documentation Concepts` → `Reference Concepts`; source-extraction status chip `Analyzing` → `Drafting`; drop `API key` leak from drill-service error toast; drop trailing ellipsis from feedback placeholder. |
| 5 | Library subhead voice-canon: `Your library shows what you've reconstructed, not what you've saved.`; PWA manifest description: `A study tool for learning by reconstruction. See what you can actually explain.` |

Code-side identifiers (`showIgnition()`, `nav-ignition`, `bn-ignition`, `App.toggleCluster`, `clusterIndex`, `roomLabel`, `kind: 'room'`, `data-state="locked|primed|drilled|solidified"`, etc.) were **deliberately left unchanged** per scope — only display labels moved. Don't flag them.

---

## Sources of truth — read this before running

The browser-served HTML is **not always** the file in `public/` with a matching name. Check the request path before assuming which file you'd edit if you found a string bug.

| Live URL | Source-of-truth file |
|---|---|
| `/` (logged-in app shell) | `public/index.html` |
| `/login.html` (302) → `/login` | **`auth/router.py:_render_login_html`** — an inlined Python f-string template, not `public/login.html`. The `public/login.html` file exists but is not on the request path. |
| `/manifest.webmanifest` | `public/manifest.webmanifest` (served as a static file). |
| `/css/*`, `/js/*`, fonts, brand mark | `public/css/*`, `public/js/*`, etc. |

When a P1 brand/voice bug is found on the login page, the fix lives in `auth/router.py`, not `public/login.html`. Confirm with `grep -rn "<offending-string>" auth/ public/` before reporting.

---

## Hard rules the UI must satisfy

These are absolute. Any violation is a P1 bug.

1. **`socratink` is always lowercase** in user-visible copy — page titles, headings, tooltips, alt text, ARIA labels, manifest fields. Even sentence-initially.
2. **No typographic emphasis on either syllable of the brand.** Don't accept `socrat'ink'`, `socrat<em>ink</em>`, or `socra<strong>tink</strong>`. The accepted markup is `socra<span class="brand-accent">tink</span>` (sidebar) and `socra<span class="brand-title-accent">tink</span>` (login) only.
3. **No brand-syllable extensions** as standalone nouns or verbs anywhere in the UI. No `tink it`, `Inkwell`, `Inkstand`, `Pen`, etc. The standalone tokens `tink` and `ink` may only appear inside the literal word `socratink` (or as the CSS variable name `--ink-900` in stylesheets, which isn't user-visible).
4. **No diagnostic / clinical / dungeon-map vocabulary** in learner copy: `Socratic Canvas`, `Socratink brand mark` (capitalized), `challenge it`, `Needs correction`, `Locked container`, `drill nodes`, `clusters`, `Locked room`, `Locked room set`, `Drill Node`, `Drill Result`, `Cluster Result`, `Cluster Focus`, `Drill branch`, `Starting Room`, `Starting map`, `STARTING MAP`, `Documentation Concepts`, `Analyzing` (as source-extraction status), `API key`, or band literals (`spark`, `link`, `chain`, `clear`, `tetris`) on a learner-facing panel.
5. **No `Ignition` or `Start Cold Attempt` strings in user-visible chrome.** They are display labels that fully retired this batch. (Code-side `showIgnition`, `renderIgnitionGate`, `Cold Attempt` as a screen title are **kept** — don't flag.)
6. **No exclamation marks. No emoji. No hype adjectives.** Calm, precise, Socratic register.

---

## Test plan

Run each step in the order listed. Capture a screenshot at each numbered step and note the result inline.

### 0. Setup

1. Open Chrome.
2. Navigate to the dev URL the user provides (typically a local server, e.g. `http://localhost:5173/` or a deployed preview). Confirm you reach the login page (`/login.html`) when unauthenticated, otherwise the in-app surface (`/`).
3. Open DevTools → Console. Watch for errors during the session — any JS error is a regression.

### 1. Login surface (`/login.html`)

1. Inspect the browser tab title. **Expect:** `socratink — sign in`. Reject `socratink — the Socratic Canvas`.
2. Read the brand mark image's `alt` attribute (DevTools → Elements → `<img class="brand-mark">`). **Expect:** `alt="socratink mark"`. Reject any capitalized `Socratink`.
3. Confirm the visible wordmark is `socra` + (accent) `tink` with the existing accent on `tink`. There must be no apostrophe, no italic, no strong on either syllable beyond the existing one accent.
4. Confirm pronunciation guide text is `sō·krə·tink`.
5. Read the `<meta name="application-name">` and `<meta name="apple-mobile-web-app-title">` — both must be lowercase `socratink`.
6. Read the `<link rel="manifest">` href and fetch it (or inspect via DevTools → Application → Manifest). **Expect:** `name: "socratink"`, `short_name: "socratink"`, `description: "A study tool for learning by reconstruction. See what you can actually explain."`. Reject "Socratic learning canvas".

### 2. Sign in / land on the in-app surface (`/`)

1. Continue as guest (or sign in via Google, whichever the user wants).
2. The first-run welcome overlay should appear if you've cleared `localStorage`. If it does:
   - Title: `socratink is a reading room, not a dashboard.`
   - Description: `Bring what you have. The first entry stays quiet until you begin.`
   - Primary CTA: `open the first entry`.
   - Reject any occurrence of `the first room` (display copy) or `enter the first room`.
3. Skip or advance the welcome overlay.

### 3. Sidebar + bottom-nav labels (desktop ≥ 1024px)

1. Resize the window to ≥ 1280px wide.
2. Read the sidebar nav items in order. **Expect:** `New Entry · Desk · Library · Settings · Send Feedback`. Reject any `Ignition` text in the sidebar.
3. Hover the `New Entry` item. Confirm the bolt material symbol icon is present (icons were not in scope for rename).
4. Take a screenshot of the sidebar.

### 4. Bottom-nav (mobile)

1. Resize to 320 × 568 px (iPhone SE narrowest target). Reload.
2. Read the bottom-nav items. **Expect:** `New Entry · Desk · Library · Settings` (the bottom nav drops Send Feedback).
3. Confirm `New Entry` does not overflow its 24-char container; the bottom-nav label fits without ellipsis at 320px.
4. Tap each bottom-nav item and confirm it switches the active surface without console error.

### 5. Desk hero (the empty/no-concept path)

1. With no concepts created yet, you should land on the Desk surface.
2. **Expect** the hero state-chip to read one of: `no map yet`, `draft path`, `worth revisiting`, `spacing`, `spaced evidence`, `source captured` (depending on state). Reject `growing`, `instantiated`, or any raw state-machine token.
3. Read the hero guidance paragraph (`.desc.hero-guidance`). **Expect:** `Pick a tile to open an entry, or start a new draft path at New Entry.` Reject `enter a room`, `enter an entry` (article should now be `open an`), or `at Ignition`.
4. Read the hero voice line (`.hero-voice-line`). **Expect:** `The map stays honest because evidence comes from your reconstruction.` (unchanged voice-canon.)
5. Read the hero primary action button label. **Expect:** `Begin at New Entry`. Reject `Begin at Ignition`.

### 6. New Entry — threshold composer

1. Click `New Entry` in the sidebar. The threshold composer should appear (form with concept name + starting-sketch fields).
2. Read the kicker above the page. **Expect:** `Start here`.
3. Read the heading. **Expect:** `What do you want to understand?`
4. Read the field labels:
   - Concept input: visible label `Concept`, placeholder rotates through `e.g. Photosynthesis / Entropy / Transformers / Attention`. (Whichever shows is fine.)
   - Sketch field: visible label `Starting sketch`, placeholder `Parts, guesses, examples, confusions. No polished answer needed.` Reject `Starting map`.
5. Read the submit button label. **Expect:** `Create draft path`.
6. With no input, hover the submit button. The disabled-state title attribute should mention `Add a few words about how you think it works…` — voice-canon, no diagnostic register.

### 7. Concept-create extended modal (if reachable)

If a separate concept-create modal opens (not the inline composer), spot-check:

1. The kicker `STARTING SKETCH` (uppercase). Reject `STARTING MAP`.
2. The disabled-state CTA copy `Build from my starting sketch`. Reject `Build from my starting map`.
3. The combined-source CTA `Build from my sketch and source`. Reject `Build from my map and source`.

### 8. Library

1. Click `Library`. **Expect** to see two sections.
2. The top section: `Reference Concepts` heading. Reject `Documentation Concepts`. The subhead reads `Curated draft paths you can open without treating the map as learner evidence.` Reject `you can enter without`.
3. The bottom section: `Your Library` heading. The subhead reads:
   `Your library shows what you've reconstructed, not what you've saved.`
   Reject `Draft paths and evidence maps you can reopen.`
4. If no concepts exist: empty state copy reads `No draft paths yet. Begin one at <a>New Entry</a>.` Reject `Begin one at Ignition`.
5. If concepts exist: each library card shows pills like `${n} sections` and `${n} entries`. Reject `${n} clusters` or `${n} drill nodes`.

### 9. Create a concept and walk the loop (smoke)

1. Go back to `New Entry`. Type a concept name (e.g. `Photosynthesis`) and a 1–2 sentence sketch. Submit `Create draft path`.
2. Wait for graph extraction. While the loading overlay is up, read the status chip. **Expect:** `Drafting` (not `Analyzing`). Reject `Analyzing`.
3. After extraction lands, the Desk surface should display the concept's draft path. Pillars to verify:
   - Detail panel kickers when a node is hovered or clicked: `Core Thesis`, `Backbone Principle`, `Section`, `Entry` (formerly `Cluster Focus` / `Drill Node`). Reject any of those forbidden kickers.
   - Hover a tile and read the floating-room-label tooltip. **Expect:** `Open entry`. Reject `Open room`.
4. Click `Try from memory` on the active node. The drill chat should open. Reject any `Start Cold Attempt` button text.
5. In the drill chat, confirm the prompt copy is the on-motif scoping question (e.g. for the core thesis: `What governing idea explains how this whole system behaves? Start here, then take your best guess.`). The post-submit acknowledgements should not contain `quiz`, `test`, `score`, `assessment`, or `challenge`.
6. After a substantive cold attempt, the post-attempt panel should show:
   - Kicker `what you just did`
   - Body lines that include `the entry stayed quiet until your guess existed` and `Repair the gap this entry exposed.` Reject `the room stayed quiet` or `this room exposed`.

### 10. Map mode toggle (Route ↔ Graph)

1. Switch the map view between `Route` and `Graph` modes via the segmented control.
2. Both labels remain `Route` and `Graph` (domain shortcuts kept per scope).
3. In Graph mode, click a section node. Detail panel kicker reads `Section`. Pill text reads `${n} entries`. Reject `Cluster` or `drill nodes`.
4. Click a leaf. Kicker reads `Entry`. Reject `Drill Node`.
5. Click a backbone. Kicker reads `Backbone Principle` (unchanged).
6. Click any locked node. Detail copy uses `Locked branch`, `Locked section`, or `Locked entry`. Reject `Locked container`, `Locked room set`, `Locked room`.

### 11. Theme toggle (light ↔ dark)

1. Toggle the theme to dark via the sidebar theme control.
2. Confirm the dark-mode obsidian stage and seam-of-light panel render correctly (the dark-mode-graph patch is unchanged by this refactor — visual regression check only).
3. Toggle back to light. No visual breakage; the cream-paper aesthetic is intact.

### 12. Settings

1. Open `Settings`. The page title reads `Your reading room` (load-bearing voice line — kept).
2. The sub-labels read `Theme`, `Reduced motion`, `Threshold sounds` (held verbatim per user lock).
3. Toggle `Reduced motion` on, reload, and confirm motion is suppressed (existing accessibility feature; not in rename scope, but smoke-check the toggle still works).

### 13. Drill error path (if reproducible)

1. If you can simulate a backend failure (e.g. set `localStorage.setItem('socratink.fakeBackendDown', '1')` if such a hook exists, or stub the API), trigger a drill submit.
2. The error toast must read `The drill service failed to respond. Try again when ready.` Reject any mention of `API key` or `backend`.

(If the error path can't be triggered locally, skip and note it in the report.)

### 14. Source-extraction error toasts

If you can trigger them (paste a video URL, an oversized PDF, etc.), confirm the existing voice-canon toasts (`Video links are not supported in this build...`, `File too large. Maximum size is 2MB.`, etc.) are unchanged.

### 15. PWA install dialog

1. Open Chrome's "Install app" prompt (DevTools → Application → Manifest → "Install").
2. The install dialog must show `socratink` as the name (lowercase) and the description `A study tool for learning by reconstruction. See what you can actually explain.` Reject `Socratink` capitalized or `Socratic learning canvas`.

### 16. ARIA / screen-reader spot-checks

Sample three icon-only or context-sensitive controls and confirm their `aria-label`s:

1. Sidebar toggle (`#drawer-toggle` or similar) — `aria-label="Toggle sidebar"`.
2. Theme toggle — `aria-label="Switch to dark mode"` or `Switch to light mode` matching current state.
3. Drawer close — `aria-label="Close sidebar"`.

Spot-check that no icon-only button has an empty or missing `aria-label`. Use Chrome's Accessibility panel.

### 17. Brand-syllable hard sweep

In DevTools → Elements, run a quick text content sweep:

1. Search the rendered DOM for `Socratink` (capital S). The only acceptable hits are JS code identifiers like `window.SocratinkApp` (which aren't part of rendered text content). No rendered text should match.
2. Search for `Socratic` (capital S). No hits expected.
3. Search for the standalone words `tink` and `ink`. Acceptable hits: only the literal word `socratink` (which the search engine usually flags only as the substring; word-boundary searches should miss it). Reject any free-standing `tink` (e.g., from a hypothetical `tink it` button) or free-standing `ink` (e.g., from `Inkwell`, `Inkstand`).

---

## Acceptance criteria (P1 / P2)

**P1 — block release if any of these fail:**
- Any rendered text contains the forbidden vocabulary listed in *Hard rules* §4 or §5.
- The brand `socratink` appears capitalized anywhere in user-visible chrome.
- The PWA manifest description still mentions `Socratic learning canvas`.
- A console JS error fires during the loop in step 9.
- Any icon-only button has empty or missing `aria-label`.
- The Welcome dialog primary CTA is not `open the first entry`.

**P2 — file but don't block:**
- Chip text (`primed for study`, `worth revisiting`, `spaced evidence`, etc.) overflows or wraps awkwardly at 320 × 568 px. Note exact viewport width where overflow first appears. (Voice-canonical strings are kept long deliberately; the chip ceiling was raised to 18 chars and most strings exceed even that.)
- Any minor copy infelicity that's on motif but reads slightly off in mobile.

---

## Reporting format

Return a single markdown report with:

```
# Browser QA report — naming refactor (dev)

## Environment
- URL tested: <url>
- Commit SHA: <git rev-parse HEAD on dev>
- Browser: Chrome <version>
- Viewport(s) tested: 1280×800, 320×568

## Step-by-step results
[For each numbered step in the test plan: PASS / FAIL / SKIP, plus
 a one-line note. Attach screenshots inline by reference.]

## P1 findings
[Numbered list. Each finding: surface (file:line if known, otherwise
 selector path), expected, actual, screenshot reference.]

## P2 findings
[Same format.]

## Brand-syllable sweep result
[PASS or list of free-standing tink/ink/Socratink occurrences in
 rendered text content with selector path.]

## Console errors observed
[List, with stack trace if available.]

## Notes / questions for the user
[Anything ambiguous about the spec that the test plan didn't cover.]
```

Keep the report under 400 lines. Be specific about selectors and expected text — the user is reading this to triage, not to repeat your work.
