# Settings overhaul — design spec

**Date:** 2026-05-06
**Status:** Brainstorm complete; contract patched after codex review; ready for plan + implementation
**Author:** Brainstormed with Claude, decisions made by jon-devlapaz
**Sanity-check:** Reviewed against `DESIGN.md` via `gemini --approval-mode plan` — verdict "minor revisions"; the one blocker (uppercase-tracked section heading) is incorporated. Then reviewed against the existing repo shape via codex; the persistence-key, reduced-motion-scope, logout-semantics, and token-source mismatches that codex flagged are patched in §4–§6 and the acceptance checklist (§10).

---

## 1. Why this exists

The current Settings page (`renderSettingsView` in `public/js/app.js`) is a friends-and-family beta checklist. Headline reads "Setup for a truthful trial run." The body is four cards: Runtime Access (a backend-reachability button), Gemini API Key (paste/save/remove a local key), Account, and Sound. It is a diagnostic surface dressed as a settings page.

The driving intent for this overhaul is all of the following at once:

- **Audience reframe.** Returning user, not beta installer. Settings is preferences, not setup.
- **IA rethink.** The Runtime Access and Gemini API Key surfaces leave the user-facing app entirely. Configuration moves to env vars (already supported). They are not hidden behind a flag, not relocated to an admin route inside this spec — they are removed from the runtime UI. If a diagnostic surface ever returns, that's a separate `/admin` decision later.
- **Voice.** "Reading room, not dashboard" (DESIGN.md §10). The current page reads dashboard.
- **Visual refresh.** A grid of dashboard cards becomes a single calm column on the Antigravity dark surface (the in-app default).

## 2. Binding principles

1. **Settings is preferences, not status.** No reachability indicators. No build info. No "checking the API…" messages.
2. **One visual register.** The body uses rows, not nested cards. The only card-like surface is the page panel itself.
3. **Instant persistence.** Every change writes immediately to `localStorage`. No Save buttons. No unsaved-changes state.
4. **Identity is acknowledged once, in body.** The global page chrome already shows a name + Log Out chip top-right. The body has a slim identity row (avatar disc + email + Log out action) so Settings remains self-contained even when the chrome changes (mobile, future redesign). Two log-outs are visible — chrome's reads as a button, body's reads as a quiet text link (semantically still a `<button>` because logout is a POST; see §4.2).
5. **No fake state.** No skeleton shimmer for fields that aren't actually loading. Account row reads from `/api/me`, which is already cached after the page chrome resolves; render synchronously when possible.
6. **Tokens only.** No new color values. The runtime token sources, by surface:
   - **Main app (Settings lives here)** — `public/styles.css` imports `public/css/variables.css` first; that file (plus `public/antigravity.css` for `--accent-color` / `--accent-mint`) is the source of truth for Settings.
   - **Login surface** — `public/css/login.css` reads from `public/css/tokens.css` directly. If any token referenced by Settings turns out to be absent from `variables.css` (e.g. a missing `*-rgb` triplet), the implementation copies it from `tokens.css` into `variables.css` rather than asking Settings to import a second file.
   - The marketing reference at `docs/design/colors_and_type.css` is a copy of the same values for handoff and is not loaded at runtime.
   - The avatar gradient uses `--violet-600`, `--lavender-500`, and `--accent-mint`.
7. **No unilateral key renames.** Persistence keys that already exist in the codebase keep their existing names. The Theme key is `learnops-theme` (used by `public/js/app.js`, the inline preloader IIFE in `public/index.html`, the `admin/static.py` static page, and `tests/e2e/test_smoke.py`). The Sound key is `socratink:sound` (owned by `public/js/audio.js`). New keys introduced by this spec — `socratink.motion` only — are namespaced separately.

## 3. Information architecture

Single centered column inside the existing `#settings-view` full-page route, `max-width: 520px`. Top-to-bottom:

```
[ kicker: ◇ SETTINGS ]
[ headline: Your reading room ]
[ lede: Quiet preferences for how socratink looks and sounds. Saved to this browser. ]

[ identity row: ◐ jonathan10620@gmail.com ……………… Log out ]

[ section heading: Display ]

[ row: Theme              [ Light | Dark ] ]
[ row: Reduced motion     [ toggle ]       ]
[ row: Threshold sounds   [ toggle ]       ]
```

Nothing else. No footer. No second section. No hidden affordance behind a flag. (The "Three quiet dials." sub-line shown in earlier mockups is dropped per implementation review — adds no information.)

## 4. Surface specification

### 4.1 Header

- **Kicker** — `class="settings-page-kicker"`. Content: a 9px violet diamond glyph + the word `SETTINGS` in tracked uppercase. Glyph is `linear-gradient(135deg, var(--violet-600), var(--lavender-500))`, rotated 45deg, with a soft violet glow built from `rgba(var(--violet-600-rgb), 0.5)` (no new hex). Glyph is decorative; `aria-hidden="true"`.
- **Headline** — `class="settings-page-title"`, sentence-case "Your reading room". Display face (Outfit in Antigravity; Geom for marketing). Size from existing `--text-display-*` tokens; no raw `font-size: Npx`.
- **Lede** — `class="settings-page-copy"`, sentence-case "Quiet preferences for how socratink looks and sounds. Saved to this browser." Wraps at ~38ch.

### 4.2 Identity row

Single hairline row directly below the lede. Order: avatar disc, email block, Log out action.

- **Avatar disc** — 36×36 circle, `border-radius: 50%`, with the violet→mint gradient bead defined in §6.1. 1px inset highlight at ~10% white alpha (dark) / ~6% ink alpha (light), built via `rgba(var(--cream-50-rgb), 0.10)` style references — no new hex.
- **Email block** — primary line is the email address (color `--text-strong`). Sub line is the literal "Signed in" (smaller, dimmer, `letter-spacing: 0.02em`).
- **Log out action** — semantically a `<button type="button">`, visually a quiet text link. The reason it must be a button: logout is a POST through `logout()` in `public/js/auth.js` (current line ~55). An `<a>` cannot do that idempotently and would also break form-submit semantics. Style: no background, no border, inherited font, color `--text-muted`, single underline at `text-decoration-color` ~18% alpha, `text-underline-offset: 3px`. On hover the underline strengthens to ~40% alpha; on focus, the standard `--accent-ring` outline applies. No `:active` state styling.
- The row sits on a 1px bottom hairline (`var(--border-subtle)` in light, the dark-theme equivalent). No top hairline — the lede provides separation.

### 4.3 Display section

- **Heading** — `<h4 class="settings-section-heading">Display</h4>`. Title Case, weight 500–600, no tracking. *Explicitly not an eyebrow kicker — DESIGN.md §10 reserves uppercase tracking for kickers only.*
- **Three rows.** Each row:
  - Left: row label (Title Case, primary text color), then a row meta line (smaller, dimmer, ~38ch wrap).
  - Right: the control (pill segmented or toggle).
  - Top hairline `var(--border-subtle)`. First row's top hairline is full strength; last row gets a bottom hairline.

#### 4.3.1 Theme row

- Label: "Theme"
- Meta: "Cream paper or obsidian sky"
- Control: pill segmented control with two options: `Light`, `Dark`. Implemented as a radio-style button group (`<div role="radiogroup">` containing two `<button role="radio">` elements with `aria-checked`), not a `<select>`. Click flips the active option.
- Active option visual: violet fill at ~16% alpha, text in `--violet-600`, 1px inset stroke at ~34% violet alpha. Implementation chooses the alpha syntax — preferred is the existing `rgba(var(--violet-600-rgb), 0.16)` pattern already used in `tokens.css`. No new hex literal.
- Inactive: transparent fill, text at `--text-muted` (already ~55% alpha of ink in light theme; equivalent in dark).
- Behavior:
  - Reads existing `localStorage["learnops-theme"]` on render (`'dark'` ≠ `'light'`, anything else falls through to `'light'`, matching `getStoredThemePreference()` in `public/js/app.js:145`).
  - On click, calls a shared helper (extracted from the existing `applyThemePreference` in `app.js:165`) that writes `localStorage["learnops-theme"]`, sets `document.documentElement.dataset.theme`, toggles the `body.night` class, calls `updateThemeToggleUi(resolvedTheme)` to keep the corner toggle in sync, and re-mounts the open knowledge graph for the new theme via the existing `remountOpenKnowledgeGraphForTheme()`. The helper becomes the single source of truth for theme changes; both the corner toggle (`App.toggleTheme`) and this Settings row call it.

#### 4.3.2 Reduced motion row

- Label: "Reduced motion"
- Meta: "Calm transitions, no settle bloom"
- Control: toggle (track + thumb).
- Off (default): `localStorage["socratink.motion"] = "system"`. CSS continues to honor `@media (prefers-reduced-motion: reduce)` only; JS code paths that branch on `matchMedia('(prefers-reduced-motion: reduce)').matches` keep their existing behavior.
- On: `localStorage["socratink.motion"] = "reduced"`. Sets `document.documentElement.dataset.motion = "reduced"`. The user override is in addition to system preference, never replacing it.
- Both CSS and JS reduced-motion checks must consult the user override; full enumeration in §6.4.

#### 4.3.3 Threshold sounds row

- Label: "Threshold sounds"
- Meta: "Soft cues at focus and submit"
- Control: toggle.
- Wired through the existing `AudioFX` module (`public/js/audio.js`) and its existing `socratink:sound` key (note the colon, singular). This spec does not introduce a new key. The Settings row reads the current state via `AudioFX.enabled` and writes via `AudioFX.setEnabled(boolean)`. The first toggle-on plays `AudioFX.playFocusTap()` once for confirmation (existing behavior, preserved).

### 4.4 Edge cases

- **Guest user** (`/api/me` → `guest_mode: true`):
  - Avatar disc swaps to a neutral mauve gradient (no mint), to read as "no identity yet."
  - Email block shows: primary line `Guest`, sub line `Not signed in`.
  - Right-side action becomes a "Sign in" `<a>` link → `/login`. Text-link styling, but here it is genuinely a navigation, so an anchor is correct.
- **Auth disabled** (`/api/me` → `auth_enabled: false`, e.g. self-hosted dev with auth turned off):
  - Identity row omitted entirely. Display section still renders. The lede line is unchanged.
- **`/api/me` fails or is slow:**
  - Render the row with a placeholder pattern: avatar disc still shows (gradient is decorative, not user-derived), email line shows `…`, sub line is empty, the Log out button is hidden until resolution. No skeleton shimmer. If the call ultimately fails, fall through to the "auth disabled" omitted-row state and `console.warn`. Settings remains usable.

## 5. State and persistence

| Key | Values | Owner | Read by |
|---|---|---|---|
| `learnops-theme` *(existing, do not rename)* | `"light" \| "dark"` | `public/js/app.js` `applyThemePreference`; this Settings row writes via the same helper | the inline IIFE preloader in `public/index.html`, `App.toggleTheme`, `admin/static.py`, the smoke test |
| `socratink.motion` *(new)* | `"system" \| "reduced"` | this Settings row | a small bootstrap on `index.html` that mirrors the IIFE pattern (sets `html[data-motion]`) and any JS reduced-motion check in §6.4 |
| `socratink:sound` *(existing, do not rename)* | string boolean per AudioFX | `public/js/audio.js` (`AudioFX.setEnabled`); this Settings row writes via the same helper | `AudioFX` itself; no other surface reads it directly |

The existing `gemini_key` localStorage key is not touched by this spec — it remains read by the existing API helpers as a fallback. Settings simply stops surfacing it.

## 6. Visual treatment

### 6.1 Avatar disc

A small lit bead, not a photographic avatar. Three layered backgrounds in CSS-stacking order (top to bottom), all expressed against tokens:

1. `radial-gradient(circle at 28% 26%, rgba(var(--cream-50-rgb), 0.45) 0%, transparent 26%)` — the highlight.
2. `radial-gradient(circle at 70% 78%, var(--accent-mint) 0%, transparent 38%)` — the mint glance.
3. `radial-gradient(circle at 30% 70%, var(--violet-600) 0%, transparent 50%)` — the violet undertone.
4. `linear-gradient(135deg, var(--lavender-500) 0%, var(--violet-600) 55%, var(--accent-mint) 100%)` — the base.

Token resolution by theme:
- Dark (Antigravity): `--violet-600` resolves to `#9067C6` from `tokens.css`. The Antigravity dark scheme also exposes `--accent-color: #9E8BFF` and `--accent-mint: #3CDDC7`. Implementation should use `--accent-color` (Antigravity) for the violet stops when `[data-theme="dark"]` is active so the bead reads consistently with the rest of the in-app accent; fall back to `--violet-600` when only `tokens.css` is loaded (e.g. marketing pages).
- Light: `--violet-600`, `--lavender-500`, `--accent-mint: #4DBA8A`.

Guest variant drops the mint stop entirely and substitutes a single `linear-gradient(135deg, var(--mauve-200), rgba(var(--mauve-200-rgb), 0.6))`. No highlight, no glow. (If `--mauve-200-rgb` is missing from `tokens.css`, this spec defers to implementation to add the triplet alongside the existing `*-rgb` block — not a "new color," same hex `#CAC4CE` already in `tokens.css`.)

### 6.2 Pill segmented control

- Group container: `inline-flex`, `padding: 3px`, `border-radius: 999px`, background `rgba(var(--cream-50-rgb), 0.04)` in dark / `rgba(var(--ink-900-rgb), 0.04)` in light, 1px hairline border at the same alpha bumped to ~0.06.
- Pill: padding via spacing tokens (or `5px 14px` if no token exists), font sized via `--text-*` tokens (no raw px), weight 500, full pill radius. Inactive text: `--text-muted`. Active fill + stroke per §4.3.1.
- Hover: inactive pill text strengthens (~80% alpha of `--text-strong`); no background change.
- Focus: `--accent-ring` outline.

### 6.3 Toggle

- Track: 34×20, full pill radius. Off: `rgba(var(--cream-50-rgb), 0.08)` in dark / `rgba(var(--ink-900-rgb), 0.08)` in light, 1px inset hairline at ~0.10 alpha. On: `rgba(var(--violet-600-rgb), 0.36)`, 1px inset at `rgba(var(--violet-600-rgb), 0.28)`.
- Thumb: 16×16 circle, `background: var(--cream-50)` in light; in dark, the thumb is the lightest text token in the active theme (effectively `--text-on-primary` resolved against dark). `box-shadow: 0 1px 3px rgba(var(--ink-900-rgb), 0.30)`.
- Transition: 220ms `cubic-bezier(0.2, 0.8, 0.2, 1)` on `background` and `transform` (already the standard easing in the design system).
- The toggle is wrapped in a `<button role="switch" aria-checked>` for accessibility.

### 6.4 Reduced-motion CSS hook (full scope)

The previous spec under-listed this. The actual reduced-motion surface in this repo:

**CSS files with `@media (prefers-reduced-motion: reduce)` blocks:**
- `public/css/base.css` (`:263`)
- `public/css/components.css` (`:120`, `:1078`, `:1428`, `:1543`, `:1842`, `:2027`, `:2315`, `:2442`)
- `public/css/crystal.css` (`:104`)
- `public/css/layout.css` (`:521`, `:2078`, `:2444`)
- `public/css/login.css` (`:404`)
- `public/css/iso-board-state-surface.css` (`:204`)

**JS files that branch on `matchMedia('(prefers-reduced-motion: reduce)').matches`:**
- `public/js/audio.js` (`:49` — used to gate threshold cue playback)
- `public/js/concept-create.js` (`:382`)
- `public/js/graph-view.js` (`:1815` — graph board motion)
- `public/js/intro-particles.js` (`:8`)
- `public/js/welcome.js` (`:50`)

**Rule for this spec.** Every CSS block above gains a sibling rule scoped under `html[data-motion="reduced"]` that mirrors the body verbatim.

Every JS check above is replaced with a shared helper that returns `true` when EITHER the media query matches OR `document.documentElement.dataset.motion === 'reduced'`. **Script-loading constraint:** four of the five JS call sites are loaded as ES modules in `public/index.html` (`app.js`, `concept-create.js` via `app.js`, `graph-view.js`, `welcome.js`), but `public/js/intro-particles.js` is loaded as a classic script (`<script src="js/intro-particles.js">` at `index.html:424`, no `type="module"`). The shared helper therefore lives in `public/js/motion.js` and must be exposed in **two** ways:

1. Module export — `export function prefersReducedMotion()` for the four module call sites.
2. Window binding — the same module sets `window.SocratinkMotion = { prefersReducedMotion }` as a side-effect, so the classic-script `intro-particles.js` can read `window.SocratinkMotion?.prefersReducedMotion?.() ?? matchMedia('(prefers-reduced-motion: reduce)').matches`.

The fallback on the right of the `??` matters: `intro-particles.js` may execute before `motion.js` finishes loading; in that case it should fall back to system preference only. The user override applies on the next motion check (most particle systems re-evaluate on resize / interaction). No JS check is allowed to remain that consults only `matchMedia`. *Alternative considered: convert `intro-particles.js` to `type="module"`. Rejected because it's loaded early and the deferred-execution timing change would risk a flash of particles before reduced-motion is honored on first paint.*

Example mirroring for `base.css`:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: 0.001ms !important; /* ... */ }
}

html[data-motion="reduced"] *,
html[data-motion="reduced"] *::before,
html[data-motion="reduced"] *::after {
  animation-duration: 0.001ms !important;
  /* ... mirror the rest of the rule body verbatim ... */
}
```

The implementation plan must enumerate every CSS block by file:line and every JS call site, and check each off as it is converted.

**Bootstrap reach.** A small IIFE in `public/index.html` (paralleling the existing `learnops-theme` IIFE) reads `localStorage["socratink.motion"]` on first paint and sets `html[data-motion]` synchronously, avoiding a flash of full motion before the JS bundle loads.

The login surface is generated by `_render_login_html()` in `auth/router.py:600` (inline `<style>` + `<script type="module">`). The user's motion preference must follow them across logout — anything else is surprising. So the same bootstrap IIFE is injected into `_render_login_html`'s `<head>`, and `public/css/login.css`'s reduced-motion block gets the same `[data-motion="reduced"]` mirror as the others. *Decision recorded: login surface honors the user override, not just `prefers-reduced-motion`.*

### 6.5 Light-mode parity

All of the above renders correctly in light theme by swapping the panel background to a cream gradient (built from `--cream-50` and `--surface-page` tokens), dividers to `var(--border-subtle)`, and toggle thumb to `var(--cream-50)`. Light is not the default in-app, but Settings must not look broken when the user flips Theme → Light from this very surface. The first manual test of this spec is "click Light, then click Dark, then click Light again, in this exact order, on the Settings page."

## 7. Removed surfaces (delta against current code)

Deleted from `renderSettingsView` in `public/js/app.js` (current range roughly `:3793–3990`, exact range to be confirmed during implementation):

- `Runtime Access` card markup, including `#settings-dot`, `#settings-backend-badge`, `#settings-backend-detail`, `#settings-ai-badge`, `#settings-ai-detail`, `#settings-test-btn`, `#settings-status`.
- The closures `refreshAiAccessUi` and `refreshBackendStatus`, and their event wiring.
- `Gemini API Key` card markup, including `#settings-key-input`, `#settings-key-save`, `#settings-key-remove`, `#settings-key-status`, and their handlers.
- The headline "Setup for a truthful trial run" and its lede.
- The `<input type="checkbox" id="settings-sound-input">` block is replaced by a `<button role="switch">` toggle (§6.3); the underlying `AudioFX` wiring stays.
- `getStoredGeminiKey` is **not** deleted from this file — it remains called by other surfaces. Only its Settings-page consumption goes away.

CSS used only by these deleted blocks (e.g. `.settings-health-list`, `.settings-health-row`, `.settings-badge`, `.settings-input-wrap`, `.settings-key-status`-only utilities) should be deleted in the same pass to avoid orphan styles. The implementation plan will enumerate the exact selectors before deletion.

## 8. Added surfaces (new code)

- `<header class="settings-page-header">` — kicker glyph + headline + lede.
- `<div class="settings-identity-row">` — avatar disc + identity-text block + Log out `<button>` / Sign in `<a>` (depending on auth state).
- `<section class="settings-display">` — heading + three rows.
- A `pill-segmented` component (`role="radiogroup"`, two `role="radio"` buttons) for the Theme control. May be lifted into a shared component later; ships scoped to Settings now.
- A `motion-toggle` change handler that writes `socratink.motion` and toggles `html[data-motion]`.
- `public/js/motion.js` — a shared helper exporting `prefersReducedMotion()` AND side-effect-binding `window.SocratinkMotion = { prefersReducedMotion }`, so it serves both the four module call sites and the classic-script `intro-particles.js`. See §6.4 for the script-loading rationale.
- Mirrored CSS blocks under `[data-motion="reduced"]` in every file listed in §6.4 (six CSS files including `login.css`).
- A small bootstrap IIFE in `public/index.html` that reads `socratink.motion` on first paint, paralleling the existing `learnops-theme` IIFE.
- The same bootstrap IIFE injected into the login HTML in `auth/router.py:600` (`_render_login_html`), so the user's motion preference survives logout.
- A small refactor of `App.toggleTheme` / `applyThemePreference` so both surfaces share a single helper that updates state, applies the DOM, and notifies the corner toggle. **No rename of `learnops-theme`** — the key stays.

## 9. Out of scope

These were explicitly removed from this spec by the user during brainstorming and are not added in implementation:

- Display name editing (no backend support; magic-link auth treats email as identity).
- Password change (auth is magic-link; no passwords exist).
- Data export / download.
- Delete account / wipe data.
- Build info / SHA / env footer.
- Diagnostics or backend-reachability surface in any form.
- Notifications / email cadence.
- Keyboard shortcuts reference.
- Three-way (system) Theme option — binary only, mirroring the existing corner toggle.
- An admin route. (May surface later; not part of this work.)
- A persistence-key migration to a new namespace. The existing `learnops-theme` and `socratink:sound` keys keep their names.

## 10. Acceptance checklist

Before shipping, the implementation must satisfy every box.

**Layout / surface**
- [ ] Renders inside the existing `#settings-view` full-page route. Reachable via `App.showSettings()` from bottom nav and sidebar drawer.
- [ ] No card grid. One centered column, `max-width: 520px`.
- [ ] Header: violet diamond glyph + tracked-uppercase `SETTINGS` kicker, sentence-case "Your reading room" headline, sentence-case "Saved to this browser" lede.
- [ ] Identity row: avatar disc (violet→mint), email + "Signed in" sub line, Log out **`<button type="button">`** styled as a quiet text link (**not** an `<a>` — logout is a POST). Guest variant uses an `<a>` to `/login`; auth-disabled variant omits the row.
- [ ] "Display" section heading is **Title Case**, not uppercase-tracked. (Gemini-flagged blocker.)
- [ ] Three rows: Theme (pill segmented `<button role="radio">` group), Reduced motion (toggle `<button role="switch">`), Threshold sounds (toggle `<button role="switch">`). Each row has a label + meta line.

**Persistence (codex-flagged contract)**
- [ ] Theme is read from and written to **`learnops-theme`** (existing key). Both the corner toggle and the Settings Theme row call the shared helper. No new theme key is introduced.
- [ ] Threshold sounds is read from and written to **`socratink:sound`** (existing key, colon, singular) via `AudioFX.enabled` / `AudioFX.setEnabled`. No new sound key is introduced.
- [ ] `socratink.motion` is the only new key introduced by this spec.
- [ ] `gemini_key` is untouched in localStorage; only its Settings-page UI consumption is removed.

**Reduced motion (codex-flagged scope)**
- [ ] Every `@media (prefers-reduced-motion: reduce)` block in the six CSS files listed in §6.4 has a mirrored `html[data-motion="reduced"]` rule (including `login.css`).
- [ ] Every JS call site in the five JS files listed in §6.4 reaches the user override. The four module call sites import `prefersReducedMotion` from `public/js/motion.js`. The classic-script `public/js/intro-particles.js` reads `window.SocratinkMotion?.prefersReducedMotion?.()` with `matchMedia` fallback (see §6.4 script-loading constraint).
- [ ] An IIFE in `public/index.html` sets `html[data-motion]` from `localStorage["socratink.motion"]` before first paint.
- [ ] The same IIFE is injected into `_render_login_html` in `auth/router.py:600`, so the override applies on the login surface after logout.
- [ ] With the toggle on and `prefers-reduced-motion: no-preference` at the OS level, animations on the **graph board** (the most motion-heavy surface, see `graph-view.js:1815`) are disabled.

**Removed surfaces**
- [ ] No `Check Backend` button anywhere. No Gemini key UI anywhere. The corresponding closures (`refreshAiAccessUi`, `refreshBackendStatus`, `keySave`, `keyRemove`) are deleted.

**Behavior / parity**
- [ ] Light/Dark roundtrip from this page works: Light → reload → Light persists; same for Dark; corner toggle reflects the same state.
- [ ] Guest, auth-disabled, and `/api/me` failure paths render correctly (manual test).
- [ ] DESIGN.md grep passes: no `!`, no emoji, no "AI-powered", "revolutionary", "unlock", "supercharge".
- [ ] `prefers-reduced-motion: reduce` CSS still works for users who haven't toggled the in-page setting.
- [ ] `tests/e2e/test_smoke.py` passes (it inspects the `learnops-theme` key directly; not renaming it preserves this).
