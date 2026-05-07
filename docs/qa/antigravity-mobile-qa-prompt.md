# socratink — comprehensive mobile QA browser-test prompt (Antigravity IDE)

**Purpose.** A self-contained directive for the Antigravity Browser Sub-Agent to run a comprehensive, bug-finding QA pass on socratink-app, targeting mobile (iPhone SE 1st-gen 320×568, SE 2nd/3rd-gen 375×667), light + dark themes, default-motion + reduced-motion, with structured reporting.

**Hand-off.** Paste the **Directive** block below into a new Antigravity agent thread. The agent has Chromium control, Gemini-3 vision, screenshot, DOM/console access, and can run shell commands. Do not pre-explain the codebase to it — the directive is self-contained.

---

## Directive (paste this verbatim into Antigravity)

> **Role:** You are a QA agent running a regression + bug-finding pass on socratink-app, a metacognitive learning web app. You have full Chromium control via the Browser Sub-Agent, Gemini-3 vision, console/DOM access, and shell access. **Do not modify code.** This is a read-only audit; output is a bug report.
>
> **App location.** Local FastAPI/uvicorn dev server. Start it if not running:
> ```bash
> cd /Users/jondev/dev/socratink/prod/socratink-app
> lsof -ti :8000 | xargs kill -9 2>/dev/null
> bash scripts/dev.sh &
> sleep 4
> curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/   # expect 302
> ```
> Default-guest login is auto-minted via `SOCRATINK_DEV_AUTOGUEST=1` (set by `scripts/dev.sh`); you should land on the empty-state Ignition view without a login wall.
>
> **App map.**
> - `/` Ignition view (empty-state hero with Concept + Starting-map composer)
> - Bottom nav: Ignition / Desk / Library / Settings (mobile only, `<900px`)
> - Top chrome: floating hamburger button only (fixed, translucent blur scrim on mobile)
> - Library has a seed "Hermes Agent" draft path — clicking it opens the Map view (`#map-view`) with a draft Route + Graph
> - Map view chrome (mobile): segmented "Route / Graph" switch (peripheral, ~30 px tall) + sticky bottom action bar with "Start Cold Attempt" CTA
> - Drilling activates `body.is-drilling`. **Mobile only (`<900px`)**: chrome, bottom nav, segmented switch, and action bar are all hidden — full-screen takeover. **Desktop (`≥900px`)**: drilling is inline in the right column of `.graph-layout` (`#drill-ui` inside `#graph-detail`); the sidebar/drawer and `.main-header` STAY VISIBLE by design — do NOT flag this as a bug on desktop.
>
> **Tooling fallbacks.** If your Browser Sub-Agent cannot natively resize the viewport or inject CDN scripts, use these escape hatches BEFORE skipping a pass:
>
> 1. **Viewport resize.** Try in this order until one works: (a) Chromium DevTools Protocol `Emulation.setDeviceMetricsOverride` via the agent's `evaluate` API; (b) `window.resizeTo(w,h)` from the page console (works in some Chromium-launch modes); (c) launch Chromium with explicit `--window-size=375,667` flags from the shell wrapper. If all three fail, fall back to **direct CSS-state injection**: at the document level, run
> ```js
> document.documentElement.style.setProperty('--qa-viewport-w', '375px');
> document.documentElement.style.setProperty('--qa-viewport-h', '667px');
> // Force the mobile media query to evaluate true:
> const s = document.createElement('style');
> s.textContent = `html { width: 375px !important; max-width: 375px !important; }`;
> document.head.appendChild(s);
> ```
> This won't trigger media queries (which key off the actual viewport) but it lets you visually inspect rendered widths. Where media-query coverage matters, use Chromium's `--device-scale-factor` + `--window-size` launch flags. Document in the report which fallback you used.
>
> 2. **axe-core injection.** If CDN injection is blocked by CSP, fetch the script via the shell instead and serve it locally:
> ```bash
> curl -sL https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.0/axe.min.js > /tmp/axe.min.js
> ```
> Then inject as a `<script>` element with the file's text content (not src):
> ```js
> const script = document.createElement('script');
> script.textContent = `${await fetch('file:///tmp/axe.min.js').then(r=>r.text())}`;
> document.head.appendChild(script);
> ```
> If the dev server allows static-file serving, copy axe to `public/qa/axe.min.js` (do not commit) and load it from `/qa/axe.min.js`. If neither path works, run `npx @axe-core/cli http://localhost:8000/` from the shell — this gives a JSON report you can summarize directly without DOM injection.
>
> 3. **Skip-with-justification rule.** If a fallback genuinely fails, add a `### [INFRA-LIMIT]` block to the report describing exactly what failed and what was skipped. Do NOT silently omit a pass — silent omission makes the report unreliable.
>
> **Test matrix — run every check in every cell unless noted.**
>
> | Dim | Values |
> |---|---|
> | Viewport | 320×568, 375×667, 414×896, 768×1024 (tablet portrait, sanity), 1280×800 (desktop, regression) |
> | Theme | Light (`html[data-theme="light"]`, default), Dark (`html[data-theme="dark"]`) |
> | Motion | Default, Reduced (`html[data-motion="reduced"]`) |
> | View | Ignition (empty-state), Library (Hermes seed), Map view (after click), Settings, Desk (after creating a concept) |
>
> **For each (viewport × theme × motion) cell, run the 8 inspection passes below.**
>
> ---
>
> ### Pass 1 — Layout integrity
>
> 1. Compute `document.documentElement.scrollWidth - window.innerWidth` on every view. **Fail if > 0** (horizontal overflow).
> 2. Snapshot bounding rects of: `.main-header`, `.bottom-nav`, `#ignition-view`, `.library-view`, `.settings-view`, `.map-view`, `.hero-card`, `.map-action-bar`. **Fail if any element overlaps another fixed element** (chrome ↔ content, action-bar ↔ bottom-nav). Allow ≤2px sub-pixel touching.
> 3. Verify each view's `padding-top` ≥ chrome height (64px + safe-area-inset-top) and `padding-bottom` ≥ bottom-nav height + (action-bar height if Map view) + safe-area. Use `getBoundingClientRect` to measure both fixed strips and confirm content's first/last children are not occluded.
> 4. Top chrome (`.main-header`) must have `position: fixed` and a non-empty `backdrop-filter` at `<900px`. **Fail otherwise.**
>
> ### Pass 2 — Touch targets and tap density
>
> 1. For every interactive element (`button`, `a`, `[role="button"]`, `[onclick]`, `[role="tab"]`, `input[type="checkbox"]`, segmented buttons), measure `getBoundingClientRect`. **Flag (warning, not fail) any element below 36×36 px**, **fail any below 28×28 px** unless it is part of an explicit segmented-control group sized as a unit.
> 2. The peripheral segmented `.map-mode-switch` is ALLOWED to host buttons under 44×44; its individual buttons should be ≥24 px tall.
> 3. The primary action `.btn-start-drill` inside `.map-action-bar` MUST be ≥44×44.
> 4. Bottom-nav items (`.bottom-nav-item`) MUST be ≥48 px min-height.
>
> ### Pass 3 — iOS auto-zoom prevention
>
> Every focusable form element (`input`, `textarea`, `select`) on every view: read computed `font-size`. **Fail if any < 16px** at viewport ≤414px. (iOS Safari auto-zooms on focus when a form field's font-size is under 16px.) Currently expected to FAIL on `#hero-single-input-field` at 15px — record as known issue if seen, do not flag again per cell.
>
> ### Pass 4 — Accessibility (axe-core via DevTools)
>
> 1. Inject `axe-core` from CDN (`https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.0/axe.min.js`) and run `axe.run()` on each view. Report all violations with their nodes; treat `serious` and `critical` as fail, `moderate` and `minor` as warning.
> 2. Verify the segmented `.map-mode-switch` has `role="tablist"`, both `.map-mode-btn` have `aria-pressed`, and the active state's `aria-pressed="true"` matches the `.active` class.
> 3. Verify the floating hamburger has a non-empty `aria-label` and `aria-expanded` toggles when the drawer opens.
> 4. Check focus-visible ring renders on all interactive elements when tabbed: navigate with `Tab` and screenshot the focused element each time. **Fail if any focused element has no visible focus indicator.**
> 5. Verify color contrast on key text against background using axe; report any below WCAG AA (4.5:1 normal, 3:1 large).
>
> ### Pass 5 — Motion preference fidelity
>
> 1. With `prefers-reduced-motion: reduce` (set via Chromium emulation), navigate through every view. **Fail if any animation longer than 80ms plays**, including but not limited to: `mapFadeIn`, `viewSlideIn`, hero-particle drift, the placeholder cycler in `#hero-single-input-field` (poll placeholder every 250ms for 8s — should NOT change), tile click "thud", focus tap audio.
> 2. With reduced-motion off, the placeholder cycler MUST advance through `Photosynthesis → Entropy → Transformers → Attention` over ~12.8s. Verify ≥3 distinct values seen.
> 3. With reduced-motion off but Settings → Reduced motion toggled ON, the cycler MUST stop within one tick (verify by polling for 4s after toggle).
>
> ### Pass 6 — Functional flows (golden paths)
>
> Run each flow and assert at every step. Capture a Walkthrough for each.
>
> 1. **Empty-state hero → submit gate.** Type "Photosynthesis" in Concept, leave Starting-map empty. Submit must be disabled. Type a 6-word sketch. Submit must enable. Submit (don't follow). Verify `App.runHeroAction` fires.
> 2. **Library → Hermes draft path → Map view.** From Library, click Hermes Agent. Wait for `#concept-start-drill` to be unhidden. Verify "Start Cold Attempt" button text. Verify segmented switch shows Route active. Click Graph. Verify `body.is-drilling` is unset, `#graph-content` is no longer `hidden`, `#map-content` is hidden. Click Route. Reverse holds.
> 3. **Start Cold Attempt drill.** From Map view, click Start Cold Attempt. Verify `body.classList.contains('is-drilling')` becomes true. **Only on mobile (`<900px`)**, verify chrome, bottom nav, segmented switch, and action bar all set `display: none`. **On desktop (`≥900px`)**, verify the sidebar/`.main-header` REMAIN visible (this is intended) and the drill UI appears inline within `.graph-detail`. In both cases, verify `#drill-ui` is visible and chat input is focused.
> 4. **Cancel drill.** Click "← Back" inside drill. Verify `is-drilling` removes, all chrome restored.
> 5. **Empty-tile click in Desk.** From Desk view (after creating a concept), click a blank tile. Verify `AudioFX.playTileClick()` fires (assert via `console.log` instrumentation OR by listening for the underlying `<audio>` start event), then verify the add-concept drawer opens.
> 6. **Bottom-nav cycling.** Tap each nav item; verify the corresponding view becomes `.visible` and others lose `.visible` within 400ms. Verify URL or in-memory route updates.
> 7. **Drawer toggle.** Tap hamburger; verify `body[data-drawer-open="true"]` and `aria-expanded="true"`. Tap again; verify cleanup.
>
> ### Pass 7 — Visual regression (Gemini-3 vision)
>
> For each (viewport × theme × motion × view) cell, take a full-page screenshot. Run a vision pass with these prompts and report findings:
>
> 1. *"Is there any visible color seam, hard edge, or banding between the top floating chrome and the page background? Describe the gradient transition. The intended look is a soft translucent blur with no hard edge."*
> 2. *"Identify the primary call-to-action on this view. Describe its position, weight, and contrast vs. surrounding content. The intended primary action on the Map view is 'Start Cold Attempt' in a sticky bottom bar."*
> 3. *"Describe the segmented control labeled 'Route / Graph' (if present). Is its visual weight peripheral (subtle, ≤30px tall, content-width) or primary (heavy, full-width, deep saturation)? Intended: peripheral."*
> 4. *"Are any controls or text clipped, cut off, or overlapped by other UI? List positions."*
> 5. *"Does the bottom nav have any element overlapping it? Describe the gap between the bottom nav and the closest non-nav element above."*
> 6. *"In the dark theme, list any element whose color reads as out-of-system (off-brand). socratink's palette is deep navy (#0B0D17) backgrounds with violet (#9067C6) accents and warm cream paper (#F2F0F5) for the light theme."*
> 7. *"Are there any 'awkward' surface transitions — places where two adjacent surfaces have noticeably different tones with a visible seam between them?"*
>
> ### Pass 8 — Console + network hygiene
>
> 1. Capture all console messages during every pass. **Fail on any unhandled error** other than the known `_vercel/speed-insights/script.js` 404 in local dev.
> 2. Capture all failed network requests (`fetch`/`XHR` non-2xx, image 404, missing fonts, missing CSS). Report each.
> 3. Capture any `Cross-Origin Read Blocking` warnings, mixed-content warnings, or `Refused to apply style` errors.
> 4. Verify CSS cache-busters on `styles.css`, `antigravity.css`, and the `@import`-ed `css/*.css` files are bumped if any of those files have `git diff` against `main`. (Run `git diff --name-only origin/main` in `public/css/` to find changed files; cross-reference against the `?v=` query param in `styles.css`.)
>
> ---
>
> ### Bug report format
>
> Output a single Markdown report with this exact structure. Each finding gets its own block.
>
> ```
> ### [SEV-{1-4}] {Short title}
>
> **Pass:** {1–8} — {pass name}
> **Cell:** {viewport × theme × motion × view}, e.g. 375×667 dark default Map
> **Severity:**
>  - SEV-1 = ships-broken (a11y critical, broken interaction, layout collapse, console error)
>  - SEV-2 = ships-degraded (touch target under 28px, contrast under WCAG-AA, visible seam, regression)
>  - SEV-3 = polish (touch target under 36px, minor visual rough edge, animation wrong duration)
>  - SEV-4 = nice-to-have (copy nit, micro-spacing)
>
> **What I saw:** {1–2 sentences, concrete observation}
> **What I expected:** {1 sentence, derived from the directive's expected behavior}
> **Repro steps:** {numbered list, lossless — same agent should be able to follow}
> **Evidence:** {paths to saved screenshots, console snippets, computed-style snapshots}
> **Hypothesis (optional):** {if you can guess at the cause}
> ```
>
> Then a final summary table:
>
> ```
> ## Summary
> | Cell | SEV-1 | SEV-2 | SEV-3 | SEV-4 |
> |------|-------|-------|-------|-------|
> | 320×568 dark default Library | 0 | 1 | 2 | 0 |
> ...
> ```
>
> And a known-issues block listing things you saw but did not flag (e.g., the 15px concept textarea pre-existing).
>
> ---
>
> ### Coverage requirements before declaring done
>
> - [ ] Every cell in the test matrix attempted (60 cells: 5 viewports × 2 themes × 2 motion × 3 view-shapes; some cells are no-ops where view doesn't apply).
> - [ ] Each Pass attempted at least once per representative cell.
> - [ ] axe-core run on each view in each theme (≥10 axe runs).
> - [ ] At least one full-page screenshot per cell saved.
> - [ ] Walkthrough recordings of all 7 functional flows in Pass 6.
> - [ ] Final summary table is filled.
> - [ ] Known-issues block lists pre-existing items so reviewers don't re-investigate them.
>
> ### Things you must NOT do
>
> - Do not write or edit code in `public/`, `main.py`, `scripts/`, `css/`, or `js/`.
> - Do not run `git commit`, `git push`, or modify `package.json` / `requirements*.txt`.
> - Do not enable or disable a feature flag.
> - Do not delete or move screenshots/artifacts; save under `.qa-runs/{timestamp}/` for archival.
> - Do not ask follow-up questions if a check is ambiguous — make a reasonable interpretation, document it in the report's preamble, and continue.

---

## Why this prompt is shaped this way

- **Directive style** matches Antigravity's expected agent input ("Refactor X and verify against design specs").
- **Self-contained app map + start command** so the agent has zero priors. Antigravity's Browser Sub-Agent runs Chromium independently; without these, it would have to spelunk the repo to find the dev-server entry point.
- **Test matrix shape** (viewport × theme × motion × view) borrowed directly from BrowserStack / QA Wolf accessibility-testing playbooks — small enough to be tractable, large enough to catch the failure modes that actually ship in mobile webapps (auto-zoom, touch density, motion-preference drift, dark-mode seams).
- **Eight passes** correspond to the canonical mobile-web QA failure modes: layout overflow, touch density, iOS form auto-zoom, axe-core a11y, motion preference, golden-path functional, vision-based visual regression, console hygiene. None of these are skippable on a real shipping app.
- **Severity scale** matches socratink's "MVP-blocker vs polish" rubric so review triage is fast.
- **Walkthrough recordings** leverage Antigravity's session-recording capability so review is not just textual but replayable — meaning a human reviewer can confirm a flow without re-running it locally.
- **Vision-pass prompts are specific** (named the gradient, named the colors, named the elements) so Gemini-3's multimodal pass produces actionable output rather than generic descriptions.

## Sources

- [Build with Google Antigravity, our new agentic development platform — Google Developers Blog](https://developers.googleblog.com/build-with-google-antigravity-our-new-agentic-development-platform/)
- [Antigravity Browser Extension Setup Guide](https://antigravity.im/browser-extension)
- [Getting Started with Google Antigravity — Google Codelabs](https://codelabs.developers.google.com/getting-started-google-antigravity)
- [Google Antigravity Review (2026): The "Agent-First" IDE for Gemini 3](https://leaveit2ai.com/ai-tools/code-development/antigravity)
- [Website QA Testing: Complete Guide to Quality Assurance in 2026 — BugHerd](https://bugherd.com/blog/website-qa-testing-complete-guide-to-quality-assurance)
- [Mobile Accessibility Testing: Guidelines, Tools, Best Practices — BrowserStack](https://www.browserstack.com/guide/accessibility-testing-for-mobile-apps)
- [Accessibility Testing for Web & Mobile — QA Wolf](https://www.qawolf.com/solutions/accessibility-testing)
- [Mobile Accessibility QA Testing Checklist — Paul J Adam](https://pauljadam.com/demos/mobilechecklist.html)
- [Quick Website Accessibility Testing Checklist — BrowserStack](https://www.browserstack.com/guide/website-accessibility-testing-checklist)
- [Website Testing Checklist & Template — Testsigma](https://testsigma.com/blog/web-app-testing-checklist/)
