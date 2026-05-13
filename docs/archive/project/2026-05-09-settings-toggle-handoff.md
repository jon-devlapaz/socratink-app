# Settings toggle handoff — Codex pickup

**Date:** 2026-05-09
**Branch:** `inspect/pr-232`
**Tip:** `c13224e fix(settings): toggle knob contrast — gradient flip + hairline ring`
**Dev server:** running at `http://127.0.0.1:8000/` (uvicorn --reload, served from this worktree at `/Users/jondev/dev/socratink/prod/socratink-app`)

The previous agent (Claude Opus) iterated three times on the settings toggle and could not land it. User is handing off to you. **Read `## What still needs to happen` before any code change.**

---

## What the user is trying to accomplish

The PR (#232) is a 1680-line antigravity-theme expansion. After a customer-persona test rejected most of the original PR's motion, and after an unsuccessful "wonder at concept commitment" multi-agent race confirmed that decorative motion is anti-brand for socratink, the active path is:

> **Iterate on what the persona suggested**: calm, scholarly, reading-room voice. Strip ambient theater. Earn small moments only. Honor `prefers-reduced-motion` AND the in-app `html[data-motion="reduced"]` attribute. Default to light theme.

That work is mostly done (see commits below). The remaining open issue is the **settings page toggle UI**.

---

## What's already on the branch

```
c13224e  fix(settings): toggle knob contrast — gradient flip + hairline ring   [last attempt — user rejected]
7379ba3  fix(settings): restore violet→mint toggle gradient per taste call
6e8e349  fix(settings): solid-violet toggle, kill dark-bloom, split sound section
e9b8f9d  salvage(launchpad): aria-busy + is-building-route during extract
630f995  calm(dark): tone down particles + iso-board glow per persona test
ce02841  motion(claude): earned ignition handoff; strip ambient theater
aee5407  spruce(headline): swap .ig-highlight gradient shimmer for textbook underline
93909ad  style: enhance views with antigravity CSS layer        ← PR #232 base
0dad919  style: deepen gradient hues for light mode visibility   ← PR #232 base
93774ce  feat: enhance ignition view with richer CSS and HTML update  ← PR #232 base
```

The first six commits on top of the PR base are good and should land. Commits `6e8e349` → `7379ba3` → `c13224e` are the three settings-toggle attempts; the last one is what the user is calling "fucked up" and rejecting.

If you decide a clean fix needs a different approach than `c13224e`, **revert that commit and write your own on top**. Don't pile a fourth iteration on the same flawed diagnosis.

---

## What still needs to happen

### Step 0: Ask the user before touching code.

The previous agent's failure mode was iterating on hypotheses the user hadn't confirmed. The user said "weird" and "fucked up" with a close-up image but never specified what *kind* of wrong. Before touching the CSS, ask one targeted question:

> "Looking at the close-up — is the issue (a) the white knob's size or position inside the pill, (b) the gradient colors or direction, (c) the pill's shape itself, or (d) something else specific?"

Get an actual answer. Don't iterate on "weird."

### Step 1: Once you know what's wrong, fix it.

The toggle's CSS lives at `public/antigravity.css` lines ~1684–1735. The DOM markup is rendered by `public/js/app.js` around line 4109 (settings page template).

Current state of the toggle CSS:

```css
body.antigravity-theme .settings-toggle {
  position: relative;
  flex: none;
  width: 44px;
  height: 26px;
  border: none;
  border-radius: 999px;
  background: rgba(36, 32, 56, 0.14);
  cursor: pointer;
  padding: 0;
  transition: background 0.25s ease;
}

body.antigravity-theme .settings-toggle::after {
  content: "";
  position: absolute;
  top: 3px;
  left: 3px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #FFFFFF;
  box-shadow:
    0 0 0 1px rgba(36, 32, 56, 0.16),     /* hairline ring  */
    0 2px 6px rgba(36, 32, 56, 0.22),     /* soft drop      */
    0 1px 0 rgba(255, 255, 255, 0.85) inset; /* highlight   */
  transition: left 0.25s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

body.antigravity-theme .settings-toggle[aria-checked="true"] {
  background: linear-gradient(90deg, var(--ag-mint), var(--ag-violet));
  box-shadow: 0 4px 12px rgba(144, 103, 198, 0.20);
}

html[data-theme="dark"] body.antigravity-theme .settings-toggle[aria-checked="true"] {
  background: linear-gradient(90deg, var(--ag-mint), var(--ag-violet));
  box-shadow: none;  /* the 0.32-alpha drop bloomed onto navy as a stray purple dot */
}

body.antigravity-theme .settings-toggle[aria-checked="true"]::after {
  left: 21px;
}
```

Math: pill 44×26, knob 20×20 with 3px top/bottom/left margins. ON state moves knob to `left: 21px` so it sits 3px from the right edge. Mathematically symmetrical.

### Constraints to respect

1. **The user wants the mint color** — they explicitly said so. Don't replace the gradient with solid violet again. (That was iteration 1, rejected.)
2. **Dark-mode shadow suppression must stay.** The 0.32-alpha violet drop bloomed onto navy as a stray purple dot beneath the pill — confirmed bug. Iteration 2's `box-shadow: none` in dark mode is correct; keep it.
3. **The Display + Sound section split should stay.** The earlier "Display" heading containing the sounds toggle was misleading. The split into `Display` (theme + reduced motion) and `Sound` (threshold sounds) is committed and the user has not pushed back on it.
4. **Reduced-motion + forced-colors a11y honored** — the existing reduced-motion guards in this file MUST keep working for any new transition.

### Things the user has said they like (don't undo)

- The textbook violet underline on "understand" (commit `aee5407`).
- The earned-motion launch-pad arrival (commit `ce02841`).
- The dark-mode tone-down (commit `630f995`).
- The `aria-busy` + `is-building-route` extract-call state (commit `e9b8f9d`).
- The mint color in the toggle gradient.

### Things the user has said they DON'T like (don't reintroduce)

- Decorative ambient motion (orbs, halo, breathe, infinite dot pulse).
- Gradient-clipped text on the headline.
- The "Display" section heading containing the sounds toggle.
- The dual-diamond crystal "wonder" overlay (rejected outright).
- Codex's `concept-name-in-particles` 3.6s reveal (rejected even when trimmed to 1.6s).
- Gemini's 4000-particle phase-change field (rejected).

---

## Where to look for the real bug

The previous agent's hypothesis was contrast (white knob on the mint side of the gradient). They flipped the gradient direction and added a hairline ring. The user still called it weird. So the real issue is probably one of:

- **Knob size feels off relative to the pill.** 20px in a 26px pill = 3px margin. iOS toggles run closer to 4–5px. Could try `width: 18px; height: 18px; top: 4px; left: 4px;` and ON `left: 22px`. Pill might also benefit from slightly more height (e.g., 28px).
- **Pill width feels cramped.** 44px is on the small side. iOS standard is closer to 51×31. Worth trying `width: 48px` with knob position adjusted accordingly.
- **The gradient angle reads as "rainbow" rather than "active fill."** A solid `var(--ag-violet)` with the mint as a soft glow underneath (or a mint-tinted shadow) might read cleaner than a gradient.
- **The knob's hairline ring just added by `c13224e` might be the problem** — adding a dark ring on a white knob can read as "broken / cropped" if the contrast is too high. Worth A/B-ing with the ring gone.

But again: **don't guess. Ask first.**

---

## Tooling notes for Codex

- The dev server reloads on Python changes. Static assets need cache-bust query string bumps (`antigravity.css?v=N`) in `public/index.html` to force browser refresh. Current is `v=12`.
- Playwright screenshots can timeout with rAF-driven canvas animations on the page. The settings page doesn't have those, so you should be fine, but if you hit it: override `window.requestAnimationFrame = () => 0` and `document.getAnimations().forEach(a => a.pause())` before the screenshot.
- Each port has its own localStorage origin. The dev server's only on 8000 right now. Other servers (8001-8003) for the wonder-race worktrees are stopped.
- The user's preferred sanity check is hard-refresh (Cmd-Shift-R) in their actual Chrome, not Playwright screenshots.

---

## File map

```
public/antigravity.css                          # toggle CSS (~lines 1684-1735)
public/js/app.js                                # settings template (~line 4109)
public/index.html                               # cache-bust query strings
public/css/layout.css                           # particle-canvas dark-mode opacity (committed)
.claude/friction-log.md                         # session-retro entries from prior agent
~/.claude/projects/.../memory/                  # crystallized rules — feedback_*.md files

worktrees/pr232-claude/                         # round-1 motion race (motion/claude branch)
worktrees/pr232-codex/                          # round-1 motion race + aria-busy salvage source (motion/codex)
worktrees/pr232-gemini/                         # round-1 motion race (motion/gemini)
worktrees/wonder-claude/                        # rejected wonder-round race entry
worktrees/wonder-codex/                         # rejected wonder-round race entry
worktrees/wonder-gemini/                        # rejected wonder-round race entry
```

The wonder/* worktrees can be deleted (`git worktree remove`) — they're archive-only at this point.

---

## TL;DR for Codex

1. **Read this file.** Don't skim.
2. **Spin up at `http://127.0.0.1:8000/`.** Hard-refresh. Click into Settings. Toggle the threshold sounds on. See for yourself what's wrong.
3. **Ask the user one specific question** about what's weird before any edit.
4. **Apply the user-confirmed fix.** Bump cache-bust. Verify in browser. Commit.
5. **Don't reintroduce anything in the "DON'T" list above.**

The previous agent's mistake was three rounds of guessing what "weird" meant. Don't repeat that.

— Claude Opus (handing off)
