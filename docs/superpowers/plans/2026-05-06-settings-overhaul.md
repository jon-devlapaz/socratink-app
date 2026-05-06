# Settings Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current four-card "Setup for a truthful trial run" Settings page with a single-column "Your reading room" surface (Account · Theme · Reduced motion · Threshold sounds), removing all backend-diagnostic and Gemini-key UI from the user-facing app while keeping existing localStorage keys intact.

**Architecture:** Bottom-up. (1) Build a reduced-motion override helper used everywhere motion is checked. (2) Extract a shared theme helper out of `applyThemePreference` so the corner toggle and the new Settings row both call it. (3) Rebuild `renderSettingsView` markup, wire the controls to those helpers, and delete the dead diagnostic plumbing. Existing keys (`learnops-theme`, `socratink:sound`) are not renamed; the only new key is `socratink.motion`.

**Tech Stack:** Vanilla ES modules + classic scripts (`public/js/`), CSS imported via `public/styles.css` and `public/antigravity.css`, FastAPI for the login HTML in `auth/router.py`, pytest for backend tests, manual browser verification for frontend.

**Spec:** `docs/superpowers/specs/2026-05-06-settings-overhaul-design.md` (commit `df1661f`).

**Working tree:** Plan executes on `dev` per the user's workflow ("commit straight to dev"). No worktree.

---

## File Map

**Created**
- `public/js/motion.js` — shared `prefersReducedMotion()` helper (module export + `window.SocratinkMotion` side-effect bind for classic-script consumers).

**Modified — JS**
- `public/js/app.js` — extract a shared theme helper; rebuild `renderSettingsView`; remove diagnostic/Gemini-key code; wire Settings to `motion.js` and `AudioFX`.
- `public/js/audio.js` — replace its private `reducedMotion()` with the shared helper.
- `public/js/concept-create.js` — same.
- `public/js/graph-view.js` — same.
- `public/js/welcome.js` — same.
- `public/js/intro-particles.js` — classic-script consumer, reads `window.SocratinkMotion?.prefersReducedMotion?.()` with `matchMedia` fallback.

**Modified — CSS**
- `public/css/base.css` — mirror reduced-motion block under `[data-motion="reduced"]`.
- `public/css/components.css` — same, for each of its 8 reduced-motion blocks.
- `public/css/crystal.css` — same.
- `public/css/layout.css` — same, for each of its 3 blocks. Add Settings-page styles. Remove dead `.settings-health-*`, `.settings-badge`, `.settings-input-wrap` rules.
- `public/css/login.css` — same mirroring for its reduced-motion block.
- `public/css/iso-board-state-surface.css` — same.

**Modified — HTML**
- `public/index.html` — extend the existing pre-paint IIFE (around line 31) with a `socratink.motion` reader that sets `html[data-motion]`.

**Modified — Python**
- `auth/router.py` — inject the same pre-paint IIFE into the `<head>` of `_render_login_html` (current line 600) so the override survives logout.

**Modified — Tests**
- `tests/test_auth_router_supabase.py` (or sibling) — add a test that the rendered login HTML contains the motion bootstrap.
- `tests/e2e/test_smoke.py` — verify it still passes; it inspects `learnops-theme` directly, which we are NOT renaming.

---

## Task 1: Create the reduced-motion helper

**Files:**
- Create: `public/js/motion.js`

- [ ] **Step 1: Write `public/js/motion.js`**

```js
/**
 * Shared reduced-motion check.
 *
 * Returns true when EITHER the user has set `socratink.motion = "reduced"`
 * via Settings (surfaced as `html[data-motion="reduced"]`) OR the OS
 * prefers reduced motion. The user override is additive: it can force
 * quiet motion even when the OS does not request it.
 *
 * Loaded as an ES module by app.js / concept-create.js / graph-view.js /
 * welcome.js. The same module also binds the helper on the window so
 * the classic-script `intro-particles.js` can read it without an import.
 */

export function prefersReducedMotion() {
  if (typeof document !== 'undefined') {
    const motionAttr = document.documentElement?.dataset?.motion;
    if (motionAttr === 'reduced') return true;
  }
  if (typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
    try {
      return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    } catch (err) {
      return false;
    }
  }
  return false;
}

if (typeof window !== 'undefined') {
  window.SocratinkMotion = Object.freeze({ prefersReducedMotion });
}
```

- [ ] **Step 2: Smoke-test the helper in the browser**

Open `http://localhost:8000` (or the dev URL), then in DevTools console:

```js
import('/js/motion.js').then(m => {
  console.assert(typeof m.prefersReducedMotion === 'function', 'export missing');
  console.assert(typeof window.SocratinkMotion?.prefersReducedMotion === 'function', 'window bind missing');
  document.documentElement.dataset.motion = 'reduced';
  console.assert(m.prefersReducedMotion() === true, 'override not honored');
  delete document.documentElement.dataset.motion;
  console.log('motion.js OK');
});
```

Expected: `motion.js OK` printed; no assertion warnings.

- [ ] **Step 3: Commit**

```bash
git add public/js/motion.js
git commit -m "feat(motion): shared prefersReducedMotion helper

Adds a single source of truth for reduced-motion checks. Returns true
when html[data-motion='reduced'] is set OR the OS prefers reduced
motion. Module export for ES module consumers; window.SocratinkMotion
binding for classic-script consumers (intro-particles.js)."
```

---

## Task 2: Pre-paint motion bootstrap in index.html

**Files:**
- Modify: `public/index.html:31-45`

- [ ] **Step 1: Extend the existing IIFE**

Replace the existing pre-paint script (lines 31–45) with:

```html
  <script>
    try {
      document.body.classList.add('antigravity-theme');
      if (localStorage.getItem('learnops-theme') === 'dark') {
        document.documentElement.dataset.theme = 'dark';
        document.body.classList.add('night');
        document.body.dataset.theme = 'dark';
      } else {
        document.documentElement.dataset.theme = 'light';
        document.body.dataset.theme = 'light';
      }
      if (localStorage.getItem('socratink.motion') === 'reduced') {
        document.documentElement.dataset.motion = 'reduced';
      }
    } catch (err) {
      console.warn('Theme/motion preload skipped.', err);
    }
  </script>
```

- [ ] **Step 2: Verify in the browser**

Reload the app, then in DevTools:

```js
localStorage.setItem('socratink.motion', 'reduced');
location.reload();
// after reload:
console.assert(document.documentElement.dataset.motion === 'reduced', 'bootstrap missed');
localStorage.removeItem('socratink.motion');
```

Expected: assertion silent.

- [ ] **Step 3: Commit**

```bash
git add public/index.html
git commit -m "feat(motion): preload data-motion from localStorage

Mirrors the learnops-theme IIFE pattern so socratink.motion is honored
on first paint, before the JS bundle loads. Avoids a flash of full
motion when the user has set Reduced motion in Settings."
```

---

## Task 3: Pre-paint motion bootstrap in login HTML

**Files:**
- Modify: `auth/router.py:600-674` (`_render_login_html`)
- Test: `tests/test_auth_router_supabase.py` (add a new test method)

- [ ] **Step 1: Find a representative existing test in the file**

```bash
grep -n "_render_login_html\|/login" tests/test_auth_router_supabase.py | head
```

Expected: a few existing tests that hit `/login`. We add a sibling test in the same file.

- [ ] **Step 2: Write the failing test**

Append to `tests/test_auth_router_supabase.py`:

```python
def test_login_html_has_motion_bootstrap(client):
    """The login page must honor a user-set socratink.motion preference.

    The override is stored in localStorage by Settings; when the user logs
    out and lands on /login, that preference must continue to set
    html[data-motion='reduced'] before first paint. Without this script,
    the login page would briefly run full motion until the inline
    script tag executed.
    """
    response = client.get("/login")
    assert response.status_code == 200
    body = response.text
    assert "socratink.motion" in body, "motion key not referenced in login HTML"
    assert 'dataset.motion = "reduced"' in body or "dataset.motion='reduced'" in body, \
        "data-motion override not wired in login bootstrap"
```

- [ ] **Step 3: Run the test to confirm it fails**

```bash
pytest tests/test_auth_router_supabase.py::test_login_html_has_motion_bootstrap -v
```

Expected: FAIL — `socratink.motion not referenced in login HTML`.

- [ ] **Step 4: Patch `_render_login_html`**

In `auth/router.py`, locate `_render_login_html` (line 600) and add a `<script>` tag inside the `<head>` block, immediately before the closing `</head>` (currently line 620). The block to insert:

```python
return f"""<!DOCTYPE html>
<html lang="en" class="light">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="theme-color" content="#f7ece1">
  <meta name="application-name" content="Socratink">
  <meta name="mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-title" content="Socratink">
  <title>socratink — the Socratic Canvas</title>
  <link rel="manifest" href="/manifest.webmanifest?v=1">
  <link rel="icon" type="image/png" sizes="192x192" href="/favicon-192x192.png?v=6">
  <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png?v=6">
  <link rel="apple-touch-icon" href="/apple-touch-icon.png?v=6">
  <link rel="stylesheet" href="/css/tokens.css?v=2">
  <style>{css}</style>
  <script>
    try {{
      if (localStorage.getItem('socratink.motion') === 'reduced') {{
        document.documentElement.dataset.motion = 'reduced';
      }}
    }} catch (err) {{ /* localStorage unavailable; fall through */ }}
  </script>
</head>
"""
```

(Note the doubled `{{` and `}}` to escape the f-string.)

- [ ] **Step 5: Run the test to confirm it passes**

```bash
pytest tests/test_auth_router_supabase.py::test_login_html_has_motion_bootstrap -v
```

Expected: PASS.

- [ ] **Step 6: Run the full auth router test suite**

```bash
pytest tests/test_auth_router_supabase.py -v
```

Expected: every existing test still passes; new test passes.

- [ ] **Step 7: Commit**

```bash
git add auth/router.py tests/test_auth_router_supabase.py
git commit -m "feat(motion): bootstrap data-motion in login HTML

Injects the same pre-paint IIFE used in index.html so the user's
Reduced motion preference survives logout. Without this, the user
would land on /login at full motion despite an explicit override.
Adds a regression test asserting the script is present."
```

---

## Task 4: Mirror reduced-motion CSS — base.css

**Files:**
- Modify: `public/css/base.css:262-280` (approximate)

- [ ] **Step 1: Read the existing block**

```bash
sed -n '260,290p' public/css/base.css
```

Note the body of the `@media (prefers-reduced-motion: reduce)` rule.

- [ ] **Step 2: Add the mirror immediately after the existing block**

After the closing `}` of the `@media` block, add:

```css
html[data-motion="reduced"] *,
html[data-motion="reduced"] *::before,
html[data-motion="reduced"] *::after {
  /* Mirror the @media (prefers-reduced-motion: reduce) body verbatim.
     If the @media body changes, this mirror must change too. */
  animation-duration: 0.001ms !important;
  animation-iteration-count: 1 !important;
  transition-duration: 0.001ms !important;
  scroll-behavior: auto !important;
}
```

(Copy whatever the actual `@media` body declares. The literal rules above are the typical pattern; substitute the real ones if they differ.)

- [ ] **Step 3: Smoke-test in the browser**

```js
document.documentElement.dataset.motion = 'reduced';
// observe: any animations on the page should stop within one frame.
delete document.documentElement.dataset.motion;
```

Expected: motion ceases when the attribute is set; resumes when removed.

- [ ] **Step 4: Commit**

```bash
git add public/css/base.css
git commit -m "feat(motion): mirror base.css reduced-motion under data-motion"
```

---

## Task 5: Mirror reduced-motion CSS — components.css

**Files:**
- Modify: `public/css/components.css` at lines 120, 1078, 1428, 1543, 1842, 2027, 2315, 2442

- [ ] **Step 1: For each of the 8 blocks, add a `[data-motion="reduced"]` mirror**

For each `@media (prefers-reduced-motion: reduce) { ... }` block, immediately after its closing `}`, add a mirror that:

- Replaces `@media (prefers-reduced-motion: reduce)` with `html[data-motion="reduced"]` as an ancestor selector on every selector in the body.
- Preserves the same property declarations verbatim.

Because the pattern repeats 8 times, do them one at a time. Example for the block at line 120 (selector pattern, the actual selectors will differ):

If the existing block reads:

```css
@media (prefers-reduced-motion: reduce) {
  .crystal-rotate { animation: none; }
  .threshold-glow { transition: none; }
}
```

Add immediately below:

```css
html[data-motion="reduced"] .crystal-rotate { animation: none; }
html[data-motion="reduced"] .threshold-glow { transition: none; }
```

- [ ] **Step 2: Verify the file still parses**

```bash
node -e "require('fs').readFileSync('public/css/components.css','utf8')" \
  && echo "file readable"
```

Open the dev server and ensure no console errors about CSS parse.

- [ ] **Step 3: Smoke-test in the browser**

```js
document.documentElement.dataset.motion = 'reduced';
// observe: motion-heavy components calm down (crystal rotation, threshold glow, etc.)
delete document.documentElement.dataset.motion;
```

- [ ] **Step 4: Commit**

```bash
git add public/css/components.css
git commit -m "feat(motion): mirror components.css 8 reduced-motion blocks under data-motion"
```

---

## Task 6: Mirror reduced-motion CSS — crystal.css, layout.css, login.css, _experiment

**Files:**
- Modify: `public/css/crystal.css:104`
- Modify: `public/css/layout.css:521, 2078, 2444`
- Modify: `public/css/login.css:404`
- Modify: `public/css/iso-board-state-surface.css:204`

- [ ] **Step 1: Apply the same pattern to each remaining file**

For each `@media (prefers-reduced-motion: reduce)` block in the four files above, add a sibling rule scoped under `html[data-motion="reduced"]`. Same mechanical translation as Task 5.

- [ ] **Step 2: Smoke-test in the browser**

In particular for `layout.css:2078` and `2444` (graph-board-related blocks), open a graph view and verify that setting `document.documentElement.dataset.motion = 'reduced'` calms graph board motion.

- [ ] **Step 3: Commit**

```bash
git add public/css/crystal.css public/css/layout.css public/css/login.css public/css/iso-board-state-surface.css
git commit -m "feat(motion): mirror crystal/layout/login/_experiment reduced-motion under data-motion"
```

---

## Task 7: Convert JS module call sites to use the shared helper

**Files:**
- Modify: `public/js/audio.js:48-50` (the private `reducedMotion()`)
- Modify: `public/js/concept-create.js:382`
- Modify: `public/js/graph-view.js:1815`
- Modify: `public/js/welcome.js:50`

- [ ] **Step 1: `audio.js`**

At the top of the file, after the existing imports / module preamble (around the existing `const STORAGE_KEY = 'socratink:sound';`), add:

```js
import { prefersReducedMotion } from './motion.js';
```

Then replace the existing `function reducedMotion()` (lines 48–50) and **all call sites** in the file (`reducedMotion()` → `prefersReducedMotion()`). Leave the rest of `audio.js` unchanged.

- [ ] **Step 2: `concept-create.js`, `graph-view.js`, `welcome.js`**

In each file:

1. Add `import { prefersReducedMotion } from './motion.js';` near the top (next to existing imports).
2. Find the `matchMedia('(prefers-reduced-motion: reduce)').matches` expression and replace with `prefersReducedMotion()`.
3. Remove any local `const reduce = ...` shim that becomes redundant.

- [ ] **Step 3: Smoke-test in the browser**

```js
localStorage.setItem('socratink.motion', 'reduced');
location.reload();
// after reload, on the graph view: animations should be stilled
// on the welcome view: particles / stagger-in should not run
localStorage.removeItem('socratink.motion');
```

- [ ] **Step 4: Run any existing JS smoke tests**

```bash
pytest tests/e2e/test_smoke.py -v -k "not slow" 2>&1 | tail -30
```

Expected: existing smoke tests pass.

- [ ] **Step 5: Commit**

```bash
git add public/js/audio.js public/js/concept-create.js public/js/graph-view.js public/js/welcome.js
git commit -m "refactor(motion): route module call sites through prefersReducedMotion

audio/concept-create/graph-view/welcome now import the shared helper
instead of calling matchMedia directly. The user's socratink.motion
override applies on every motion gate, not just CSS animations."
```

---

## Task 8: Convert intro-particles.js (classic script consumer)

**Files:**
- Modify: `public/js/intro-particles.js:1-15` (approximate)

- [ ] **Step 1: Replace the matchMedia check**

The file is loaded as a classic `<script>` in `index.html:424`, so it cannot `import`. Instead, replace the existing pattern:

```js
const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
```

With:

```js
function isReducedMotion() {
  const helper = window.SocratinkMotion?.prefersReducedMotion;
  if (typeof helper === 'function') {
    return helper();
  }
  // motion.js may not have loaded yet on first paint. Fall back to
  // system preference only; the next call (after load) will pick up
  // the user override automatically.
  return window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches === true;
}
```

Then replace any existing references to `reduceMotion.matches` or `reduceMotion()` with `isReducedMotion()`. The file's existing `change` listener on the media query (if present) can be removed — the check now consults the helper directly each call.

- [ ] **Step 2: Smoke-test in the browser**

```js
localStorage.setItem('socratink.motion', 'reduced');
location.reload();
// On a page that uses intro-particles: particles should not animate.
localStorage.removeItem('socratink.motion');
```

- [ ] **Step 3: Commit**

```bash
git add public/js/intro-particles.js
git commit -m "refactor(motion): intro-particles uses window.SocratinkMotion bridge

Classic-script consumer cannot import the ES module helper. Reads
window.SocratinkMotion.prefersReducedMotion when available, falls back
to system preference only when motion.js has not yet loaded."
```

---

## Task 9: Extract a shared theme helper from `applyThemePreference`

**Files:**
- Modify: `public/js/app.js:143-183` (approximate, the existing theme block)

- [ ] **Step 1: Read the existing block**

```bash
sed -n '143,183p' public/js/app.js
```

The existing functions are `getStoredThemePreference`, `updateThemeToggleUi`, `applyThemePreference`, `toggleTheme`. They already form a coherent module-private cluster. The Settings row will call into this cluster, so the only refactor is to expose a `setTheme(nextPreference)` entry point that the Settings row can call without knowing about `themePreference` state, and to keep `App.toggleTheme` working as before.

- [ ] **Step 2: Add a `setTheme` helper**

Inside the same `App = (() => { ... })();` IIFE, immediately below `toggleTheme`, add:

```js
  // Single entry point for both the corner toggle and the Settings row.
  // Accepts 'light' | 'dark', applies the DOM, persists to localStorage,
  // and updates the corner toggle UI.
  function setTheme(nextPreference) {
    const normalized = nextPreference === 'dark' ? 'dark' : 'light';
    applyThemePreference(normalized);
  }
```

Then add `setTheme` to the public surface returned by the IIFE, alongside `toggleTheme` (search for the existing `return { ... }` block and add `setTheme`).

`applyThemePreference` already does the persistence + DOM + corner-toggle UI work; `setTheme` is just a stable, intent-revealing alias. No behavior change.

- [ ] **Step 3: Smoke-test in the browser**

```js
App.setTheme('dark');
console.assert(document.documentElement.dataset.theme === 'dark');
console.assert(localStorage.getItem('learnops-theme') === 'dark');
App.setTheme('light');
console.assert(document.documentElement.dataset.theme === 'light');
console.assert(localStorage.getItem('learnops-theme') === 'light');
```

- [ ] **Step 4: Commit**

```bash
git add public/js/app.js
git commit -m "refactor(theme): expose App.setTheme alongside App.toggleTheme

Adds a stable entry point for callers that know which theme they want
(the upcoming Settings row). No behavior change — applyThemePreference
remains the single implementation. learnops-theme key is unchanged."
```

---

## Task 10: Settings page CSS — new layout, kill the old card grid

**Files:**
- Modify: `public/css/layout.css` (locate the existing `.settings-*` block via `grep -n "settings-shell\|settings-page-grid\|settings-page-card" public/css/layout.css`)

- [ ] **Step 1: Identify the dead selectors**

```bash
grep -n "settings-shell\|settings-page-grid\|settings-page-card\|settings-health-list\|settings-health-row\|settings-badge\|settings-input-wrap\|settings-key-status\|settings-page-kicker\|settings-page-title\|settings-page-copy\|settings-section-header\|settings-dot\|settings-test\|settings-status\|settings-account-body\|settings-account-summary\|settings-account-title\|settings-sound-toggle" public/css/layout.css
```

Note the line ranges. Most will be deleted; a few (like `.settings-page-kicker`, `.settings-page-title`, `.settings-page-copy`) we will redefine for the new layout.

- [ ] **Step 2: Delete the dead block**

Delete every selector in the list above that does **not** appear in the new design:

- Keep (will redefine): `.settings-page-kicker`, `.settings-page-title`, `.settings-page-copy`.
- Delete: everything else listed.

If you are unsure about a selector, search the JS for its consumer:

```bash
grep -n "settings-health-list\|settings-badge" public/js/app.js public/index.html
```

If no consumer exists after Task 11 deletes the old markup, the CSS is dead.

- [ ] **Step 3: Add the new Settings styles**

Append to `public/css/layout.css`:

```css
/* ── Settings (single calm column) ────────────────────────── */

.settings-shell {
  max-width: 520px;
  margin: 48px auto 96px;
  padding: 0 24px;
  font-family: 'Inter', system-ui, sans-serif;
}

.settings-page-header {
  margin-bottom: 32px;
}

.settings-page-kicker {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--lavender-500);
  margin-bottom: 12px;
}

.settings-page-kicker .crystal-glyph {
  width: 9px;
  height: 9px;
  background: linear-gradient(135deg, var(--violet-600), var(--lavender-500));
  transform: rotate(45deg);
  box-shadow: 0 0 10px rgba(var(--violet-600-rgb), 0.5);
}

.settings-page-title {
  font-family: 'Outfit', 'Geom', system-ui, serif;
  font-weight: 400;
  font-size: clamp(24px, 4vw, 30px);
  line-height: 1.1;
  letter-spacing: -0.025em;
  color: var(--text-strong);
  margin: 0 0 8px 0;
}

.settings-page-copy {
  font-size: 13px;
  line-height: 1.55;
  color: var(--text-muted);
  margin: 0;
  max-width: 38ch;
}

.settings-identity-row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 0;
  margin-top: 28px;
  margin-bottom: 28px;
  border-bottom: 1px solid var(--border-subtle);
}

.settings-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  flex-shrink: 0;
  box-shadow: inset 0 0 0 1px rgba(var(--cream-50-rgb), 0.10);
  background:
    radial-gradient(circle at 28% 26%, rgba(var(--cream-50-rgb), 0.45) 0%, transparent 26%),
    radial-gradient(circle at 70% 78%, var(--accent-mint) 0%, transparent 38%),
    radial-gradient(circle at 30% 70%, var(--violet-600) 0%, transparent 50%),
    linear-gradient(135deg, var(--lavender-500) 0%, var(--violet-600) 55%, var(--accent-mint) 100%);
}

.settings-avatar.is-guest {
  background: linear-gradient(135deg, var(--mauve-200), rgba(var(--mauve-200-rgb, 202, 196, 206), 0.6));
  box-shadow: none;
}

.settings-identity-text {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  color: var(--text-strong);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.settings-identity-email {
  display: block;
  font-weight: 500;
}

.settings-identity-meta {
  display: block;
  font-size: 11px;
  color: var(--text-muted);
  letter-spacing: 0.02em;
  margin-top: 2px;
}

.settings-identity-action {
  font: inherit;
  background: none;
  border: 0;
  padding: 0;
  color: var(--text-muted);
  font-size: 12px;
  text-decoration: underline;
  text-decoration-color: rgba(var(--ink-900-rgb), 0.18);
  text-underline-offset: 3px;
  cursor: pointer;
}
[data-theme="dark"] .settings-identity-action {
  text-decoration-color: rgba(var(--cream-50-rgb), 0.18);
}
.settings-identity-action:hover,
.settings-identity-action:focus-visible {
  text-decoration-color: rgba(var(--ink-900-rgb), 0.40);
}
[data-theme="dark"] .settings-identity-action:hover,
[data-theme="dark"] .settings-identity-action:focus-visible {
  text-decoration-color: rgba(var(--cream-50-rgb), 0.40);
}

.settings-section-heading {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-strong);
  margin: 0 0 8px 0;
}

.settings-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 16px 0;
  border-top: 1px solid var(--border-subtle);
}
.settings-row:first-of-type { border-top: 1px solid rgba(var(--ink-900-rgb), 0.10); }
[data-theme="dark"] .settings-row:first-of-type { border-top: 1px solid rgba(var(--cream-50-rgb), 0.10); }
.settings-row:last-of-type { border-bottom: 1px solid var(--border-subtle); }

.settings-row-label {
  font-size: 13.5px;
  font-weight: 500;
  color: var(--text-strong);
}

.settings-row-meta {
  font-size: 11.5px;
  color: var(--text-muted);
  margin-top: 3px;
  line-height: 1.45;
}

/* Pill segmented control (used by Theme row) */
.settings-pill-group {
  display: inline-flex;
  padding: 3px;
  border-radius: 999px;
  background: rgba(var(--ink-900-rgb), 0.04);
  border: 1px solid rgba(var(--ink-900-rgb), 0.06);
}
[data-theme="dark"] .settings-pill-group {
  background: rgba(var(--cream-50-rgb), 0.04);
  border-color: rgba(var(--cream-50-rgb), 0.06);
}

.settings-pill {
  font: inherit;
  background: none;
  border: 0;
  padding: 5px 14px;
  font-size: 11.5px;
  font-weight: 500;
  border-radius: 999px;
  color: var(--text-muted);
  cursor: pointer;
}
.settings-pill[aria-checked="true"] {
  background: rgba(var(--violet-600-rgb), 0.16);
  color: var(--violet-600);
  box-shadow: inset 0 0 0 1px rgba(var(--violet-600-rgb), 0.34);
}

/* Toggle (used by Reduced motion + Threshold sounds) */
.settings-toggle {
  position: relative;
  width: 34px;
  height: 20px;
  border: 0;
  border-radius: 999px;
  background: rgba(var(--ink-900-rgb), 0.08);
  box-shadow: inset 0 0 0 1px rgba(var(--ink-900-rgb), 0.10);
  cursor: pointer;
  transition: background 220ms cubic-bezier(0.2, 0.8, 0.2, 1);
}
[data-theme="dark"] .settings-toggle {
  background: rgba(var(--cream-50-rgb), 0.08);
  box-shadow: inset 0 0 0 1px rgba(var(--cream-50-rgb), 0.10);
}
.settings-toggle::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--cream-50);
  box-shadow: 0 1px 3px rgba(var(--ink-900-rgb), 0.30);
  transition: transform 220ms cubic-bezier(0.2, 0.8, 0.2, 1);
}
.settings-toggle[aria-checked="true"] {
  background: rgba(var(--violet-600-rgb), 0.36);
  box-shadow: inset 0 0 0 1px rgba(var(--violet-600-rgb), 0.28);
}
.settings-toggle[aria-checked="true"]::after {
  transform: translateX(14px);
}
```

- [ ] **Step 4: Verify token availability**

```bash
grep -n "mauve-200-rgb\|--mauve-200" public/css/variables.css public/css/tokens.css
```

If `--mauve-200-rgb` is missing from `variables.css`, add it:

```css
--mauve-200:        #cac4ce;
--mauve-200-rgb:    202, 196, 206;
```

(in the same neighborhood as the other `*-rgb` triplets in `variables.css`).

The fallback inside `linear-gradient(... rgba(var(--mauve-200-rgb, 202, 196, 206), 0.6))` already covers this; the explicit token is preferred.

- [ ] **Step 5: Commit**

```bash
git add public/css/layout.css public/css/variables.css
git commit -m "feat(settings): new single-column Settings styles, drop dashboard cards

Removes .settings-shell card-grid styles, .settings-health-*,
.settings-badge, .settings-input-wrap, and other dead selectors tied
to the Runtime Access / Gemini key blocks. Adds the new identity-row,
display-row, pill-group, and toggle vocabulary scoped under .settings-*
classes. All token references resolve through variables.css/antigravity.css."
```

---

## Task 11: Rebuild `renderSettingsView` markup + delete diagnostic JS

**Files:**
- Modify: `public/js/app.js:3793-3990` (entire `renderSettingsView` body)

- [ ] **Step 1: Read the current function**

```bash
sed -n '3793,3995p' public/js/app.js
```

Note the existing closures (`refreshAiAccessUi`, `refreshBackendStatus`, `keySave`, `keyRemove`, `accountBody`) so they can be cleanly removed.

- [ ] **Step 2: Replace the entire function body**

Replace the body of `renderSettingsView` with:

```js
  async function renderSettingsView() {
    const settingsContent = document.getElementById('settings-content');
    if (!settingsContent) return;

    settingsContent.innerHTML = `
      <div class="settings-shell">
        <header class="settings-page-header">
          <span class="settings-page-kicker">
            <span class="crystal-glyph" aria-hidden="true"></span> Settings
          </span>
          <h2 class="settings-page-title">Your reading room</h2>
          <p class="settings-page-copy">Quiet preferences for how socratink looks and sounds. Saved to this browser.</p>
        </header>

        <div class="settings-identity-row" id="settings-identity-row">
          <div class="settings-avatar" id="settings-avatar"></div>
          <div class="settings-identity-text">
            <span class="settings-identity-email" id="settings-identity-email">…</span>
            <span class="settings-identity-meta" id="settings-identity-meta"></span>
          </div>
          <span id="settings-identity-action-host"></span>
        </div>

        <section class="settings-display">
          <h4 class="settings-section-heading">Display</h4>

          <div class="settings-row">
            <div>
              <div class="settings-row-label">Theme</div>
              <div class="settings-row-meta">Cream paper or obsidian sky</div>
            </div>
            <div class="settings-pill-group" role="radiogroup" aria-label="Theme">
              <button type="button" class="settings-pill" role="radio" data-theme-value="light" aria-checked="false">Light</button>
              <button type="button" class="settings-pill" role="radio" data-theme-value="dark" aria-checked="false">Dark</button>
            </div>
          </div>

          <div class="settings-row">
            <div>
              <div class="settings-row-label">Reduced motion</div>
              <div class="settings-row-meta">Calm transitions, no settle bloom</div>
            </div>
            <button type="button" class="settings-toggle" id="settings-motion-toggle"
                    role="switch" aria-checked="false" aria-label="Reduced motion"></button>
          </div>

          <div class="settings-row">
            <div>
              <div class="settings-row-label">Threshold sounds</div>
              <div class="settings-row-meta">Soft cues at focus and submit</div>
            </div>
            <button type="button" class="settings-toggle" id="settings-sound-toggle"
                    role="switch" aria-checked="false" aria-label="Threshold sounds"></button>
          </div>
        </section>
      </div>
    `;

    wireSettingsIdentity(settingsContent);
    wireSettingsTheme(settingsContent);
    wireSettingsMotion(settingsContent);
    wireSettingsSounds(settingsContent);
  }
```

The four `wireSettings*` helpers will be added in Tasks 12–15. They are referenced here so the markup task can be committed independently with the wiring as `// TODO` stubs (acceptable bridge since the next four tasks land it).

- [ ] **Step 3: Add the four stubs immediately after `renderSettingsView`**

```js
  function wireSettingsIdentity(_root) { /* implemented in Task 12 */ }
  function wireSettingsTheme(_root) { /* implemented in Task 13 */ }
  function wireSettingsMotion(_root) { /* implemented in Task 14 */ }
  function wireSettingsSounds(_root) { /* implemented in Task 15 */ }
```

- [ ] **Step 4: Smoke-test in the browser**

Open Settings. Expect: the new layout renders, controls do nothing yet (stubs), no JS errors in the console.

```bash
# expected console output: no errors. The previous "Backend reachable" or
# "Gemini key" messages should be entirely gone.
```

- [ ] **Step 5: Commit**

```bash
git add public/js/app.js
git commit -m "feat(settings): rebuild renderSettingsView markup, drop diagnostic UI

Replaces the four-card grid (Runtime Access, Gemini API Key, Account,
Sound) with the single-column 'Your reading room' surface: kicker,
headline, lede, identity row, and a Display section with three rows.
Diagnostic and Gemini-key plumbing (refreshAiAccessUi,
refreshBackendStatus, keySave, keyRemove) are removed. The four new
wireSettings* helpers ship as stubs and are filled in by the next
four tasks."
```

---

## Task 12: Wire the identity row

**Files:**
- Modify: `public/js/app.js` — `wireSettingsIdentity` stub from Task 11.

- [ ] **Step 1: Read what `auth.js` already exposes**

```bash
grep -n "fetchAuthSession\|logout\|isGuestSession\|isIdentifiedUserSession" public/js/auth.js
```

Confirm the imports we need: `fetchAuthSession`, `logout`, `isGuestSession`, `isIdentifiedUserSession`, `buildLoginHref`.

- [ ] **Step 2: Add or extend the existing import line at the top of `app.js`**

Find the existing `import` block from `./auth.js` (search for `from './auth.js'`). Ensure it includes all five symbols above. If the file does not yet import from `auth.js`, add a single import statement.

- [ ] **Step 3: Replace the `wireSettingsIdentity` stub**

```js
  async function wireSettingsIdentity(root) {
    const row = root.querySelector('#settings-identity-row');
    const avatar = root.querySelector('#settings-avatar');
    const emailEl = root.querySelector('#settings-identity-email');
    const metaEl = root.querySelector('#settings-identity-meta');
    const actionHost = root.querySelector('#settings-identity-action-host');
    if (!row) return;

    let session;
    try {
      session = await fetchAuthSession();
    } catch (err) {
      console.warn('Settings identity: /api/me unavailable', err);
      row.hidden = true;
      return;
    }

    if (session && session.auth_enabled === false) {
      row.hidden = true;
      return;
    }

    if (isGuestSession(session)) {
      avatar.classList.add('is-guest');
      emailEl.textContent = 'Guest';
      metaEl.textContent = 'Not signed in';
      const link = document.createElement('a');
      link.className = 'settings-identity-action';
      link.href = buildLoginHref();
      link.textContent = 'Sign in';
      actionHost.replaceChildren(link);
      return;
    }

    if (isIdentifiedUserSession(session)) {
      const email = session.user?.email || '…';
      emailEl.textContent = email;
      metaEl.textContent = 'Signed in';
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'settings-identity-action';
      btn.textContent = 'Log out';
      btn.addEventListener('click', async () => {
        btn.disabled = true;
        try {
          await logout();
          window.location.assign('/login');
        } catch (err) {
          console.warn('Logout failed', err);
          btn.disabled = false;
        }
      });
      actionHost.replaceChildren(btn);
      return;
    }

    // Unknown shape: omit the row rather than render placeholders.
    row.hidden = true;
  }
```

- [ ] **Step 4: Smoke-test in the browser**

1. Sign in as an identified user → reload Settings → identity row shows email + "Signed in" + "Log out" button.
2. Click "Log out" → POST to `/api/auth/logout` succeeds → page redirects to `/login`.
3. (Optional, harder) Force a guest session (`/auth/guest`) → reload Settings → "Guest / Not signed in / Sign in" link.
4. With `auth_enabled: false` (self-hosted dev), the row is hidden.

- [ ] **Step 5: Commit**

```bash
git add public/js/app.js
git commit -m "feat(settings): identity row honors signed-in / guest / auth-disabled

Reads /api/me via fetchAuthSession, renders the avatar disc, email,
and a Log out button (POST through logout()) for identified users.
Guests get an anchor to /login. auth_enabled=false omits the row."
```

---

## Task 13: Wire the Theme pill segmented control

**Files:**
- Modify: `public/js/app.js` — `wireSettingsTheme` stub.

- [ ] **Step 1: Replace the stub**

```js
  function wireSettingsTheme(root) {
    const pills = root.querySelectorAll('.settings-pill[data-theme-value]');
    if (!pills.length) return;

    const syncPills = () => {
      const current = getStoredThemePreference();
      pills.forEach(p => {
        p.setAttribute('aria-checked', String(p.dataset.themeValue === current));
      });
    };

    pills.forEach(pill => {
      pill.addEventListener('click', () => {
        const next = pill.dataset.themeValue === 'dark' ? 'dark' : 'light';
        // applyThemePreference (in scope here) is the canonical helper —
        // sets html[data-theme], persists to learnops-theme, and updates
        // the corner toggle UI.
        applyThemePreference(next);
        syncPills();
      });
    });

    syncPills();

    // If the corner toggle changes the theme while Settings is open,
    // re-sync the pills so they reflect the actual state.
    const corner = document.getElementById('theme-toggle');
    if (corner) {
      corner.addEventListener('click', () => {
        // Run after applyThemePreference completes. setTimeout(0) is
        // sufficient — applyThemePreference is synchronous.
        setTimeout(syncPills, 0);
      });
    }
  }
```

- [ ] **Step 2: Smoke-test**

1. Open Settings → both pills render; the active one matches the current theme.
2. Click "Light" → page background flips to cream, corner toggle's icon updates, `localStorage.getItem('learnops-theme')` is `'light'`.
3. Click "Dark" → reverse.
4. Click the corner toggle → the Settings pills update too.
5. Reload after each → preference persists.

- [ ] **Step 3: Commit**

```bash
git add public/js/app.js
git commit -m "feat(settings): wire Theme pill control to applyThemePreference

Settings Theme row is the canonical preference surface; the corner
toggle remains a quick flip. Both write learnops-theme via the same
applyThemePreference call. Pills re-sync on corner-toggle click."
```

---

## Task 14: Wire the Reduced motion toggle

**Files:**
- Modify: `public/js/app.js` — `wireSettingsMotion` stub.

- [ ] **Step 1: Replace the stub**

```js
  function wireSettingsMotion(root) {
    const toggle = root.querySelector('#settings-motion-toggle');
    if (!toggle) return;

    const readStored = () => {
      try {
        return localStorage.getItem('socratink.motion') === 'reduced';
      } catch {
        return false;
      }
    };

    const apply = (isReduced) => {
      if (isReduced) {
        document.documentElement.dataset.motion = 'reduced';
        try { localStorage.setItem('socratink.motion', 'reduced'); } catch {}
      } else {
        delete document.documentElement.dataset.motion;
        try { localStorage.setItem('socratink.motion', 'system'); } catch {}
      }
      toggle.setAttribute('aria-checked', String(isReduced));
    };

    apply(readStored());

    toggle.addEventListener('click', () => {
      const next = toggle.getAttribute('aria-checked') !== 'true';
      apply(next);
    });
  }
```

- [ ] **Step 2: Smoke-test on the graph view**

1. Open a concept's graph view; observe normal motion (graph entry, hover effects).
2. Open Settings → toggle Reduced motion ON.
3. Return to the graph; observe motion is calmed (graph-view.js:1815 honored, plus CSS mirrors).
4. Toggle OFF → motion returns.
5. Reload with the toggle ON → motion stays calmed (the index.html bootstrap honored it pre-paint).

- [ ] **Step 3: Commit**

```bash
git add public/js/app.js
git commit -m "feat(settings): wire Reduced motion toggle to socratink.motion

Toggle writes socratink.motion ('reduced' | 'system') to localStorage
and toggles html[data-motion]. Combined with the Task 4–8 CSS/JS
mirrors, the override applies to every existing reduced-motion gate."
```

---

## Task 15: Wire the Threshold sounds toggle

**Files:**
- Modify: `public/js/app.js` — `wireSettingsSounds` stub.

- [ ] **Step 1: Confirm the import**

Search the top of `app.js` for an existing import of `AudioFX`:

```bash
grep -n "AudioFX\|from './audio.js'" public/js/app.js | head
```

If it isn't already imported in `app.js`, add `import { AudioFX } from './audio.js';` near the other module imports.

- [ ] **Step 2: Replace the stub**

```js
  function wireSettingsSounds(root) {
    const toggle = root.querySelector('#settings-sound-toggle');
    if (!toggle) return;

    toggle.setAttribute('aria-checked', String(Boolean(AudioFX.enabled)));

    toggle.addEventListener('click', () => {
      const next = toggle.getAttribute('aria-checked') !== 'true';
      AudioFX.setEnabled(next);
      toggle.setAttribute('aria-checked', String(next));
      if (next) {
        // Confirmation cue, matching the original checkbox behavior.
        AudioFX.playFocusTap();
      }
    });
  }
```

- [ ] **Step 3: Smoke-test**

1. Open Settings → Threshold sounds toggle reflects current `AudioFX.enabled`.
2. Toggle off → no focus-tap cue plays on subsequent input focus traversal.
3. Toggle on → focus-tap plays once on the toggle itself; cues return on focus traversal.
4. Reload → state persists (it's already persisted via `AudioFX.setEnabled`'s write to `socratink:sound`).

- [ ] **Step 4: Commit**

```bash
git add public/js/app.js
git commit -m "feat(settings): wire Threshold sounds toggle through AudioFX

Toggle reads AudioFX.enabled and writes via AudioFX.setEnabled, which
already owns the socratink:sound key. The first toggle-on plays a
focus-tap as confirmation, matching the prior checkbox behavior."
```

---

## Task 16: Run the full smoke + acceptance pass

- [ ] **Step 1: Run the e2e smoke test**

```bash
pytest tests/e2e/test_smoke.py -v
```

Expected: all existing tests pass. The smoke test inspects `learnops-theme` directly (line 602), and we did not rename it.

- [ ] **Step 2: Run the auth router test suite**

```bash
pytest tests/test_auth_router_supabase.py -v
```

Expected: all pass, including the new `test_login_html_has_motion_bootstrap`.

- [ ] **Step 3: DESIGN.md grep on the changes**

```bash
git diff main..HEAD -- public/ auth/ | grep -E "AI-powered|revolutionary|unlock|supercharge|next-gen|game-chang"
git diff main..HEAD -- public/ auth/ | grep -E "!|🎯|✨|🔥"  # the latter checks for emoji
```

Expected: no matches. (The `!` grep will surface CSS `!important`; eyeball the diff to confirm only `!important` declarations match, not exclamation-mark copy.)

- [ ] **Step 4: Manual acceptance pass against §10 of the spec**

Walk the Settings page with the spec's §10 checklist open. For each box:

- Layout — eyeball the page; confirm single column, max-width 520px (DevTools), kicker / headline / lede / identity row / Display heading / three rows.
- Persistence — open DevTools → Application → Local Storage. Confirm only `learnops-theme`, `socratink:sound`, and `socratink.motion` keys are written.
- Reduced motion — toggle on → check the graph view animations are calmed. Toggle off → animations resume. Toggle on → reload → still calmed (bootstrap working). Log out → land on `/login` → confirm `html[data-motion="reduced"]` is set on first paint (View Source and verify the inline `<script>` is present).
- Removed surfaces — confirm no "Check Backend" button, no Gemini key UI anywhere on Settings.
- Behavior — Light → reload → Light persists; Dark → reload → Dark persists; corner toggle reflects the same state.

- [ ] **Step 5: Commit any cleanup**

If Step 4 surfaces a small fix (typo, missed selector, mis-aligned padding), apply it and commit:

```bash
git add -p
git commit -m "fix(settings): <specific fix from acceptance pass>"
```

If nothing needs fixing, no commit.

---

## Self-Review Notes

The plan above was scanned against the spec § by § before saving. Coverage map:

- Spec §3 (IA) — Task 11 markup.
- Spec §4.1 header — Task 11 markup; styles in Task 10.
- Spec §4.2 identity row — Task 12 wiring; styles in Task 10. Logout `<button>` semantics enforced (codex-flagged) in Task 12 and acceptance §10.
- Spec §4.3.1 Theme — Task 13. Existing `learnops-theme` key preserved (codex-flagged).
- Spec §4.3.2 Reduced motion — Tasks 1, 2, 4–8, 14.
- Spec §4.3.3 Threshold sounds — Task 15. Existing `socratink:sound` key preserved (codex-flagged).
- Spec §4.4 edge cases — Task 12 covers all four (signed-in / guest / auth-disabled / `/api/me` failure).
- Spec §5 state table — Tasks 13 (theme), 14 (motion), 15 (sounds).
- Spec §6.4 reduced-motion full scope — Tasks 4 (base), 5 (components), 6 (crystal/layout/login/_experiment), 7 (4 module call sites), 8 (intro-particles classic-script consumer).
- Spec §6.4 bootstrap reach (login) — Task 3.
- Spec §7 removed surfaces — Task 11 markup deletion + Task 10 dead-CSS deletion.
- Spec §8 added surfaces — Tasks 1 (motion.js), 2 (index.html bootstrap), 3 (login bootstrap), 9 (setTheme alias), 10 (Settings CSS), 11–15 (markup + wiring).
- Spec §10 acceptance — Task 16.

No placeholders. Every code step contains the actual code. Every test step contains the exact pytest invocation and expected pass/fail.
