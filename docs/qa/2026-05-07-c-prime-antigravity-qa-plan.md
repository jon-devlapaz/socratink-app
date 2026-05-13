# C-prime Concept Entry — Browser QA Plan (Antigravity-runnable)

> **Superseded surface (2026-05-11, strip-as-nav port).** The Cytoscape graph view (`public/js/graph-view.js`, `#graph-content`) was deleted in the strip-as-nav port. Wherever this plan says "graph view," "graph-fresh", or "graph-revisit", read it as the **strip + concept page** surface (`public/js/drill-chamber.js`, `public/css/concept-page.css`, `public/css/drill-chamber.css`). Screenshot keys named `graph-*` should be re-keyed to `strip-*` / `concept-page-*` when capturing evidence against current code.

**Date:** 2026-05-07
**Branch under test:** `dev` (16 commits ahead of `origin/dev`)
**Spec:** `docs/archive/superpowers/specs/2026-05-07-progressive-route-materialization-design.md`
**Plan that produced this code:** `docs/archive/superpowers/plans/2026-05-07-progressive-route-materialization.md`

This plan is written for a browser-capable agent (e.g. Antigravity, Playwright, claude-in-chrome). Every test case has a deterministic setup, exact steps, and a verification you can mechanically check. The agent's job is to execute every test ruthlessly and fill in the **Breakfix Report** at the end.

**Mindset for the executing agent:** test like the user is about to dogfood this in production. Try things that look "obvious to skip" — they're where the bugs live. Don't accept "looks fine" as a pass; every test has a precise verifier and you must check it. If a test result is ambiguous, mark `BLOCKED` with a one-line reason rather than guessing.

---

## 0. Setup

### 0.1 Start the local stack

Run from repo root:

```bash
cd "$(git rev-parse --show-toplevel)"
bash ./scripts/bootstrap-python.sh   # only if first run
playwright install chromium          # only if first run
bash ./scripts/dev-host.sh           # backend at http://127.0.0.1:8000
```

Wait until the server logs `Application startup complete`. If `dev-host.sh` is not the canonical launcher in this repo, run `ls scripts/` and pick the launcher prefixed with `dev` or `serve` and matches the project's convention.

### 0.2 Open the app

Navigate the browser to `http://127.0.0.1:8000`.

If a Supabase auth gate appears, sign in with the dev account. If you don't have one, see `tests/conftest.py::_FakeAuthService` for the dev bypass header (e.g. `X-Dev-Auth-Bypass`) — set it as a request header in your browser if your tooling allows, or use a dev-mode flag.

### 0.3 Pre-flight clean state

Open DevTools → Application → Storage → **Clear site data**. This wipes localStorage (concept store), sessionStorage (pending shell), IndexedDB, cookies. Reload.

You should now land on an **empty home/desk** view:

- Title reads exactly **`Your concepts.`**
- The state chip reads **`no concepts yet`**
- Guidance reads **`Pick a tile to enter, or start a new concept.`**
- Primary action button reads **`New concept`**
- No "draft path" / "Begin at New Entry" / "no map yet" strings visible anywhere on screen

If any of those four strings is wrong, mark **PRE-FLIGHT FAIL** in the report and stop — Round E shipped a broken vocab swap.

---

## 1. Acceptance criteria — 1:1 mapping

The spec defines 14 acceptance criteria in §7. Each gets at least one test case here, plus aggressive edge cases.

| Test ID | Spec AC | What it covers |
|---|---|---|
| TC-01 | AC#1 | Source-less happy path (door → launch pad → graph + skeleton line) |
| TC-02 | AC#2 | Source-attached text happy path |
| TC-03 | AC#3 | Source-attached URL happy path (two-step) |
| TC-04 | AC#4 | Server-side bypass rejection (curl) |
| TC-05 | AC#5 | Existing concept-create modal source flow non-regression |
| TC-06 | AC#6 | sessionStorage shell hydration + bounce |
| TC-07 | AC#7 | Smallest-route ≤4 cap enforced |
| TC-08 | AC#8 | No concept persisted from canceled flows |
| TC-09 | AC#9 | Vocabulary on home/desk |
| TC-10 | AC#10 | Threshold validation parity |
| TC-11 | AC#11 | qa-smoke.sh |
| TC-12 | AC#12 | Browser smoke for all three paths |
| TC-13 | AC#13 | Visual screenshots |
| TC-14 | AC#14 | A11y on door submit (release-blocker) |

Edge cases below are numbered TC-100+.

---

## 2. Tests

### TC-01 — Source-less happy path (AC#1)

**Setup:** clean state per §0.3.

**Steps:**
1. From the home view, click the **`New concept`** button (or the equivalent door entry — there may also be a `+` icon in the header).
2. The Ignition (door) view should appear. Verify:
   - Title: `What do you want to understand?`
   - One textarea with placeholder beginning `e.g. photosynthesis, the Krebs cycle, recursion in Python…`
   - A small ghost button: `+ add source material`
   - One submit button shaped as an arrow icon (no visible text)
   - Submit is **disabled** while the textarea is empty
3. Type `Photosynthesis` in the concept input. Submit becomes **enabled**.
4. Open DevTools → Application → Session Storage. Confirm `socratink:pendingShell` is **NOT yet set** (only writes on submit).
5. Click the arrow submit button.
6. The launch pad surface appears. Verify:
   - The concept name `Photosynthesis` is rendered as a header.
   - Title: `What do you already think is inside this concept?`
   - Helper line: `Name the parts, guesses, examples, or confusions you have.`
   - Textarea is autofocused (focus indicator visible).
   - Submit button reads `Build my map` and is **disabled**.
   - Footer reads exactly: `Study content stays locked until the cold attempt.`
7. DevTools → Session Storage now shows `socratink:pendingShell = {"name":"Photosynthesis","ts":<unix-ms>}`. Confirm `ts` is recent (within 60 s of now).
8. Type three weak words: `light makes sugar`. Submit **enables**.
9. Click `Build my map`. The Network tab shows `POST /api/extract` with body containing `name: "Photosynthesis"`, `starting_sketch: "light makes sugar"`, `source: null`, returning **200**.
10. After the response resolves, the launch pad disappears and the graph view renders. Verify:
    - At most 4 drillable nodes total (count crystal/tile elements that represent drillable nodes; cluster/container chrome doesn't count toward the cap).
    - One node is clearly marked the suggested first target / core thesis (visual emphasis varies; just confirm one target stands out).
    - Above (or near) the graph, the skeleton-line banner reads exactly: `This is the skeleton. It will grow as you reconstruct.`
    - DevTools → Session Storage: `socratink:pendingShell` is **gone**.
11. Reload the page. The concept appears as a tile on the home/desk view (named `Photosynthesis`). The skeleton-line is **NO LONGER visible** when reopening the same concept.

**Pass criteria:** every check above is true.
**Fail modes to log:**
- Skeleton-line missing or persists on subsequent visits
- More than 4 drillable nodes
- sessionStorage cleared before persistence (open DevTools console, throttle network to "Slow 3G" before clicking `Build my map` — confirm shell stays in sessionStorage until the persist actually completes)

---

### TC-02 — Source-attached text happy path (AC#2)

**Setup:** clean state.

**Steps:**
1. Open the door. Type `Krebs cycle`.
2. Click `+ add source material`. The source panel expands inline. Verify three tabs are visible: **Text**, **URL**, **File**.
3. Click the **Text** tab if not already active. Paste a few sentences (e.g. `The Krebs cycle is a series of reactions that produce ATP from acetyl-CoA. It happens in the mitochondria. It produces NADH and FADH2 along the way.`).
4. Click `Attach`. The source panel collapses and the `+ add source material` button text changes to e.g. `Source: 256 chars pasted (replace)`.
5. Click the door's arrow submit. Verify:
   - sessionStorage `socratink:pendingShell` is **NOT** written (this is the source-attached path).
   - The launch pad does **NOT** appear.
   - The existing concept-create modal opens directly at the **summary card** stage (not at chat turn 1; not at any sketch field).
   - Network shows `POST /api/extract` with `source: {type: "text", text: "<the pasted content>"}`.
6. Walk the existing modal to completion (click `Build` or equivalent). Land on a graph view (not the launch pad).
7. **No skeleton-line banner** appears (this path didn't go through the launch pad).

**Pass criteria:** all of the above hold.

---

### TC-03 — Source-attached URL happy path (two-step) (AC#3)

**Setup:** clean state. Have a public URL ready (e.g. `https://en.wikipedia.org/wiki/Photosynthesis`).

**Steps:**
1. Open the door. Type `Photosynthesis URL test`.
2. Click `+ add source material` → **URL** tab.
3. Paste the URL. The Attach button enables once the URL is well-formed.
4. Click `Attach`. **Network tab MUST show two requests in order:**
   - First: `POST /api/extract-url` with body `{url: "..."}` — returns 200 with the materialized text.
   - Second: `POST /api/extract` with `source: {type: "url", text: "<materialized>", url: "<the URL>", filename: ""}`.
5. If the URL is sent directly to `/api/extract` first (skipping `/api/extract-url`), this is a **regression** of the spec §5.3 contract — log it.
6. Land on a graph view. No launch pad. No skeleton line.
7. **Negative check:** also try sending a URL source to `/api/extract` directly via curl (see TC-04 setup) with `{name: "X", source: {type: "url", url: "https://example.com"}}`. The server MUST return 422 with `error: "url_source_unsupported_here"`.

**Pass criteria:** `/api/extract-url` fires before `/api/extract`; raw-URL POST to `/api/extract` is rejected.

---

### TC-04 — Server-side bypass rejection (AC#4)

**Setup:** terminal access; backend running.

**Steps:**

In a terminal:

```bash
python -c "from fastapi.testclient import TestClient; from main import app; c = TestClient(app); r = c.post('/api/extract', json={'name':'X','starting_sketch':'','source':None}); print(r.status_code, r.json())"
```

(If the TestClient bypasses auth via the `_FakeAuthService` fixture, this runs without credentials. If it doesn't, replicate the same call with `curl -i` against the running server, including the auth header.)

**Expected output:**

```
422 {'detail': {'error': 'thin_sketch_no_source', 'message': 'Add more to your sketch, or attach source material — either path opens the build.'}}
```

**Variations to test (all should be 422 `thin_sketch_no_source`):**

- `{name: "X", starting_sketch: "  ", source: null}` — whitespace-only sketch
- `{name: "X", starting_sketch: "idk", source: null}`
- `{name: "X", starting_sketch: "?", source: null}`
- `{name: "X", starting_sketch: "i don't know", source: null}`

**Variations that should be 422 `missing_concept`:**

- `{name: "", starting_sketch: "anything", source: null}`
- `{name: "   ", starting_sketch: "anything", source: null}`

**Variations that should NOT 422 (substantive sketch):**

- `{name: "X", starting_sketch: "plants take in light and somehow make sugar", source: null}` — should call generation (mock or real, return 200).

**Pass criteria:** every 422 case returns the documented error code; every 200 case dispatches to source-less generation.

---

### TC-05 — Existing concept-create modal source flow non-regression (AC#5)

**Setup:** clean state. **Open the existing concept-create modal directly** — NOT through the door. (Some surfaces have their own "+" affordance separate from the door — e.g. an empty-state CTA on the library page or a `+` icon in the header. Find one.)

If you cannot reach the modal independently, walk through the door with no source attached, then back out and find the modal entry point.

**Steps:**
1. Open the modal. Verify three chips are visible: **Concept**, **Your sketch**, **Source material**.
2. Click the source chip's `+ add source` action. The same Text/URL/File panel appears (it must be the same component as the door's — Round B extracted them into one module).
3. Walk all three source paths in the modal:
   - **Text:** paste → Attach → chip header reads e.g. `Source: 240 chars pasted` with a `replace` action.
   - **URL:** paste a public URL → Attach → chip reads `Source: <chars> chars from a URL` (or similar).
   - **File:** drop a small `.txt` or `.md` file (≤2MB) → Attach → chip reads `Source: filename · N chars`.
4. Each path must complete without console errors.
5. After attach, click the modal's `Build` CTA. The existing extraction flow runs (today's behavior unchanged).

**Pass criteria:** no regression in any of the three modal source paths. Console clean. The modal's persistence path produces the same client-side concept record it always has.

---

### TC-06 — sessionStorage shell hydration + bounce (AC#6)

**Setup:** clean state.

**Test 6a — happy hydration:**
1. Open door. Type `Mitochondria`. Submit.
2. DevTools → Session Storage shows `socratink:pendingShell = {"name":"Mitochondria","ts":<recent>}`.
3. Reload the page. The launch pad re-mounts with `Mitochondria` as the concept-name header (the `ts < 24h` gate passes).

**Test 6b — bounce on missing shell:**
1. From the launch-pad view, open DevTools → Session Storage. Delete `socratink:pendingShell`.
2. Reload. Verify the launch pad does NOT render. The user is bounced to the door (Ignition view).
3. Console should log a `concept_create.launch_pad.evaporated` telemetry event (look in console or in a telemetry tab if the project has one).

**Test 6c — bounce on stale shell:**
1. Manually set `socratink:pendingShell = {"name":"Stale","ts":1}` in DevTools (epoch 1970).
2. Reload. Bounce to door. Same `evaporated` event.

**Test 6d — bounce on malformed shell:**
1. Set `socratink:pendingShell = "not-json-{garbage"`.
2. Reload. Bounce to door. No JS console error (the read should be defensive).

**Test 6e — bounce on shape-violation shell:**
1. Set `socratink:pendingShell = '{"foo":"bar"}'`.
2. Reload. Bounce to door (no `name` field).

**Pass criteria:** 6a renders the launch pad; 6b/c/d/e all bounce to the door without throwing.

---

### TC-07 — Smallest-route cap enforced (AC#7)

**Setup:** terminal access.

**Steps:**

Run from repo root:

```bash
cd "$(git rev-parse --show-toplevel)"
pytest tests/test_generate_smallest_route.py tests/test_extract_route_smallest.py -v
```

**Expected:** all tests pass. Look for the test that mocks `generate_smallest_provisional_map` to raise `SmallestRouteCapExceeded` and asserts the endpoint returns **500** (not 422). That test name should contain `cap_exceeded_returns_500` or similar.

**Live test (if you have model API keys):**
- Submit a launch attempt for an unusually broad concept like `everything` or `the entire universe`. Inspect the Network tab response: the returned ProvisionalMap must contain ≤4 drillable nodes. If the model violates the cap, the validator raises and the endpoint returns 500 — verify the launch pad surfaces a "Something went wrong. Try again." message and leaves the pending shell intact.

**Pass criteria:** unit + integration tests pass. If a live cap-violation can be reproduced, the 500 path engages cleanly.

---

### TC-08 — No concept persisted from canceled flows (AC#8)

**Setup:** clean state.

**Test 8a — cancel at door:**
1. Open door. Type `CancelTest`. Do NOT submit. Navigate away (back to home, or close the door).
2. Verify: no concept named `CancelTest` appears anywhere. sessionStorage has no pending shell.

**Test 8b — cancel at launch pad:**
1. Open door. Type `CancelTest2`. Submit.
2. Land on launch pad. **Do NOT click `Build my map`**.
3. Navigate away (use browser back, or the explicit cancel/close affordance if one exists).
4. Verify: no concept named `CancelTest2` appears in the home/desk view, library, or anywhere else. The pending shell may still be in sessionStorage (this is fine — it evaporates on tab close per spec; it's not a persisted concept).
5. Reload the page. If sessionStorage still holds the shell, the launch pad re-mounts (this is by design — recovery from accidental nav). If you want to verify true cancel, close the tab entirely and reopen — sessionStorage is per-tab, so the shell is gone.

**Test 8c — server failure during launch attempt:**
1. Open door. Type `FailureTest`. Submit. Land on launch pad. Type a substantive threshold.
2. Use DevTools → Network → Block request URL pattern `*/api/extract*` (or use throttling to time out).
3. Click `Build my map`. The fetch fails.
4. Verify: validation footer shows a retry-friendly message. Pending shell is **still in sessionStorage**. No concept appears in the client store.
5. Unblock the URL. Click `Build my map` again — the retry should succeed and persist the concept normally. Pending shell clears.

**Pass criteria:** No `/api/extract` is invoked for canceled flows. No client-store concept for failed flows.

---

### TC-09 — Vocabulary on home/desk (AC#9)

**Setup:** clean state, then build at least one concept (TC-01) so the desk has a non-empty state too.

**Empty state:**
- Title: `Your concepts.`
- State chip: `no concepts yet`
- Guidance: `Pick a tile to enter, or start a new concept.`
- CTA: `New concept`
- Voice line: NOT visible (`The map stays honest…` is gone)

**Non-empty state (after building one concept):**
- Title still reads `Your concepts.`
- State chip text varies by concept state — verify NONE of them say `draft path` or `draft paths`.
- Guidance text for each state should not contain `draft path`.

**Repository-level grep:**

```bash
grep -rn "draft path\|draft paths" public/
```

Expected matches (out of scope per spec §8 — these are NOT failures):
- `app.js` line ~1601 — creation modal error fallback
- `app.js` line ~1684 — delete confirmation dialog
- `app.js` lines ~2497, 2508, 2528 — library view copy

ANY OTHER matches (especially in user-facing home/desk surfaces) → log as failure.

**Pass criteria:** empty + non-empty desk show no "draft path" jargon; remaining grep matches are confined to the three out-of-scope surfaces.

---

### TC-10 — Threshold validation parity (AC#10)

**Setup:** terminal access.

**Steps:**

```bash
pytest tests/test_frontend_sketch_validation.py -v
```

This test suite verifies `public/js/sketch-validation.js` matches `models/sketch_validation.py` byte-for-byte on a shared fixture (~30 inputs). All should pass.

Note: the **launch-pad's own gate** (`launch-pad.js::isSubstantiveThreshold`) is intentionally lighter than `sketch-validation.js`. This is documented in the launch-pad source as a deliberate choice (client fail-fast with a 3+ word check; the server's stricter 8-token gate is the actual contract).

**Pass criteria:** parity test passes; launch-pad's lighter gate is documented in code comments.

---

### TC-11 — qa-smoke.sh (AC#11)

**Setup:** dev server running.

**Steps:**

```bash
bash scripts/qa-smoke.sh
```

If `qa-smoke.sh` runs against `localhost:8000`, the dev server must be running. If it targets a deploy preview, push to a preview branch first. Use whichever path the project's CI uses today.

**Pass criteria:** exit 0. Any failures must be triaged: pre-existing or introduced by this branch?

To distinguish, run the same script against `main` and compare. Anything failing on `dev` but passing on `main` is a regression to log.

---

### TC-12 — Browser smoke (AC#12)

This is essentially TC-01 + TC-02 + TC-03 above. If those passed, AC#12 passes.

Add console-noise check:
- Open the browser console with "Errors only" filter.
- Walk all three happy paths.
- Console should be clean — no errors, no warnings related to this code (third-party warnings from libraries are tolerable but log them).

---

### TC-13 — Visual screenshots (AC#13)

Capture in **dark mode** AND **light mode** (toggle via system or in-app theme):

| Screenshot | Description | Filename suggestion |
|---|---|---|
| 1 | Door at rest (empty) | `door-rest-{dark,light}.png` |
| 2 | Door with source panel expanded (Text tab) | `door-source-text-{dark,light}.png` |
| 3 | Launch pad with empty input | `launchpad-empty-{dark,light}.png` |
| 4 | Launch pad with substantive threshold (submit enabled) | `launchpad-substantive-{dark,light}.png` |
| 5 | Launch pad with thin threshold + validation footer | `launchpad-thin-{dark,light}.png` |
| 6 | Graph view post-launch with skeleton-line | `graph-fresh-{dark,light}.png` |
| 7 | Same graph reopened later (no skeleton-line) | `graph-revisit-{dark,light}.png` |
| 8 | Home/desk empty state | `desk-empty-{dark,light}.png` |
| 9 | Home/desk with one concept | `desk-populated-{dark,light}.png` |

Save to `/tmp/socratink-cprime-qa-screenshots/` or include in the breakfix report directly.

**Pass criteria:** all 18 screenshots captured. Visual review: no broken layouts, no overlapping elements, no missing copy, no color-contrast violations evident at a glance.

---

### TC-14 — A11y on door submit (RELEASE-BLOCKER, AC#14)

**Setup:** door view loaded.

**Steps:**

1. Open DevTools → Elements. Click the door submit button (the arrow icon).
2. Switch to the Accessibility pane (Chrome) or Inspector → Accessibility (Firefox). Verify:
   - **Name:** non-empty, AND not raw SVG path data. Any short label is fine (`Continue`, `Build my map`, etc.) — the contract is "the screen-reader user gets words, not path coordinates".
   - **Role:** `button`
   - **Disabled state:** matches the input's empty/non-empty state
3. Run a Lighthouse Accessibility audit on the door surface:
   - Open DevTools → Lighthouse.
   - Select **Accessibility** category, mobile or desktop, generate report.
   - Confirm WCAG 4.1.2 ("Name, Role, Value") passes.
4. Run with **screen reader** if possible (VoiceOver Cmd+F5 on macOS):
   - Tab to submit. The reader should announce something like "Continue, button, dimmed" (or "disabled").
   - Type a concept. Tab back. The reader announces "Continue, button" (no longer dimmed).

**Pass criteria:** all three substeps pass. **Failure here is a release blocker** per spec §7 #14.

---

## 3. Aggressive edge cases (TC-100+)

These extend the acceptance criteria to test failure modes that aren't explicit in the spec.

### TC-100 — Door submits empty concept

Type `   ` (whitespace only). Submit must stay disabled. If you bypass the disabled state via DevTools (`document.getElementById('hero-door-submit').disabled = false; document.getElementById('hero-single-input').requestSubmit()`), the handler should still return early (no sessionStorage write, no navigation).

### TC-101 — Door very long concept name

Paste a 200-char concept name. Must accept up to maxlength. 201 chars must be truncated by the textarea's `maxlength` attribute. sessionStorage should hold exactly the trimmed value.

### TC-102 — Door concept with weird characters

Try names with emoji, RTL text, line breaks, HTML tags (`<script>alert(1)</script>`).
- The text must be stored as plain text.
- It must NOT execute as HTML when rendered on the launch pad header (XSS check — verify in DevTools that the rendered `#launch-pad-concept-name` element shows the literal characters, not interpreted markup).

### TC-103 — Door rapid-click submit

Click the submit button 10 times in a row very fast. There must be ONE pending shell write, ONE navigation. Not 10 stacked launch-pad mounts, not 10 race-condition pending shells.

### TC-104 — Source-attach toggle race (Round C fix verification)

Network throttle: Slow 3G. Click `+ add source material` then click `+` again before the dynamic import resolves. Verify:
- The panel collapses cleanly.
- After ~5 seconds (when import resolves), the panel does NOT silently re-mount with stale source-panel DOM.
- DevTools → Elements: `<div id="hero-source-panel">` is empty and `hidden`.
- Open the panel again — fresh source panel mounts cleanly.

This is the bug Round C's `_sourcePanelGen` token fixes. If it regresses, the door has a real wedge.

### TC-105 — Launch pad thin threshold variations

Test each of these in the launch-pad textarea. Submit must stay disabled and the validation footer must show the strategy-framed message:

- empty
- `   ` (whitespace)
- `idk`
- `IDK` (uppercase)
- `i don't know`
- `i dont know`
- `no idea`
- `?`
- `??????`
- `…`
- `dunno`
- `not sure` (Round D's lighter client gate also rejects this)
- `no clue`
- `aaaaaaaa` (single repeated char — server-side `_REPEATED_CHAR_RE` rejects, client-side may pass; verify server returns 422 if reached)
- single word, e.g. `photosynthesis` (only 1 word — fails 3-word gate)
- two words, `green leaves` (2 words — fails 3-word gate)
- exactly three words, `light makes sugar` (passes client gate)

Each transition (typing → submit-enable, deleting → submit-disable) must update the button state and validation footer in real time.

### TC-106 — Launch pad over-long threshold

Try pasting >1200 chars. The textarea's `maxlength` must clip at 1200. Submit still works.

### TC-107 — Launch pad concurrent tab

Open the same site in TWO browser tabs.

- Tab A: open door, type `ConceptA`, submit. Land on launch pad in Tab A.
- Tab B: open door, type `ConceptB`, submit. Land on launch pad in Tab B.

Because sessionStorage is **per-tab**, Tab A's launch pad should still display `ConceptA` (NOT `ConceptB`). If Tab A's launch pad now shows `ConceptB`, there's a localStorage leak — log it (this would be a regression of the Round D fix that switched localStorage → sessionStorage).

### TC-108 — Launch pad after a long idle

After landing on the launch pad, leave the page idle for >24 hours OR manually set `socratink:pendingShell.ts` to 25 hours ago in DevTools and reload. The launch pad must bounce to the door.

### TC-109 — Skeleton-line leak across views

After TC-01 (skeleton-line visible), navigate:
- to the home/desk and back to the same concept → skeleton-line GONE
- to the library and back to the same concept → skeleton-line GONE
- to settings and back to the same concept → skeleton-line GONE
- open a different concept → skeleton-line GONE
- via browser back button to the graph from another view → skeleton-line GONE

The line should ONLY ever appear on first arrival via the launch pad's `fromLaunchPad: true` flag.

### TC-110 — Library cap gate

Build 9 concepts. Try to start a 10th from the door. The cap-gate panel should appear: `The board holds nine concepts. Retire one to start another.` with an `Open Library` button. The door's textarea/submit should be hidden in this state.

### TC-111 — Backend smallest-route cap exceeded → 500

If the model can be forced to emit >4 drillable nodes (mock the AI response or temporarily relax the prompt), confirm the endpoint returns **500** with `error: smallest_route_cap_exceeded` (not 422). The launch pad should surface the server-supplied message ("Could not generate a valid starting map. Try again or adjust the prompt.") in the validation footer and leave the pending shell intact.

### TC-112 — Re-running TC-01 with different concepts

Run TC-01 with three very different concepts to confirm the smallest-route generation is sensitive to the threshold:

- K-12 academic: `Photosynthesis` + threshold `plants take in light and somehow make sugar`
- College: `Metacognition` + threshold `thinking about thinking; how I judge my own knowledge`
- Niche / non-academic: `Kubernetes` + threshold `containers running in clusters; pods, nodes, services`

For each, verify ≤4 drillable nodes, the suggested first target is plausibly the core thesis (one-sentence orientation that matches the concept), and backbone hints are coherent.

If any concept produces obvious junk (e.g., a node named `node-1` or unrelated topology), log as a prompt-quality finding for follow-up — not necessarily a release blocker, but worth knowing.

### TC-113 — Persistence-then-clear ordering under failure

Stress-test the persist-then-clear contract:
1. Open DevTools console. Patch `App.persistCreatedConceptFromLaunchPad` to throw before saving:
   ```javascript
   const orig = App.persistCreatedConceptFromLaunchPad;
   App.persistCreatedConceptFromLaunchPad = function() { throw new Error('test failure'); };
   ```
2. Walk through TC-01: type concept, submit, threshold, `Build my map`.
3. The fetch succeeds (200). The persistence fails (your patched throw).
4. Verify in this order:
   - `/api/extract` returned 200 (Network tab).
   - `socratink:pendingShell` is **STILL in sessionStorage** (NOT cleared).
   - The launch pad shows an error in the validation footer (not crashed).
   - The user can edit the threshold and click `Build my map` again to retry.
5. Restore `App.persistCreatedConceptFromLaunchPad = orig` and confirm the retry works.

This is the doctrinal contract from spec §3.2: persistence-failure must not orphan the shell.

### TC-114 — Pre-flight grep regression

```bash
grep -rn "Begin at New Entry\|no map yet\|hero-voice-line>The map stays honest\|Your draft paths" public/
```

Should return ZERO matches in user-facing files. If anything resurfaces, the vocab swap regressed.

### TC-115 — Door submit with attached source — sessionStorage MUST NOT be written

After source-attach (text/URL/file), click submit. Open DevTools → Session Storage. `socratink:pendingShell` must NOT exist. The source-attached path must skip the launch-pad surface entirely.

### TC-116 — Console error scan during all happy paths

Throughout TC-01, TC-02, TC-03: monitor the console with no filter. Log any error or warning (excluding network 401s during auth bootstrap and any pre-known third-party noise).

---

## 4. Breakfix Report

Fill in below. **Do not delete unfilled rows** — leave them as `NOT EXECUTED` so the user can see what was skipped.

```markdown
# C-prime Concept Entry — Breakfix Report

**Run date:** {YYYY-MM-DD HH:MM TZ}
**Branch:** dev @ {commit SHA you tested against}
**Tester:** {agent name + model}
**Browser:** {Chrome/Safari/Firefox + version}
**Backend:** {local | preview | prod URL}

## Summary

- Total tests: 36 (14 acceptance + 22 edge cases)
- PASS: {count}
- FAIL: {count}
- BLOCKED: {count}
- NOT EXECUTED: {count}
- RELEASE BLOCKERS: {count}  ← any FAIL on TC-01, TC-04, TC-07, TC-14 a11y, or TC-113 persistence-then-clear

## Verdict

[READY TO SHIP | CONDITIONALLY READY (list conditions) | DO NOT SHIP (list blockers)]

## Per-test results

| Test | Status | Notes |
|---|---|---|
| TC-01 source-less happy path | PASS/FAIL/BLOCKED | |
| TC-02 source-attached text | PASS/FAIL/BLOCKED | |
| TC-03 source-attached URL | PASS/FAIL/BLOCKED | |
| TC-04 server bypass rejection | PASS/FAIL/BLOCKED | |
| TC-05 modal non-regression | PASS/FAIL/BLOCKED | |
| TC-06 sessionStorage hydration | PASS/FAIL/BLOCKED | |
| TC-07 smallest-route cap | PASS/FAIL/BLOCKED | |
| TC-08 no concept on cancel | PASS/FAIL/BLOCKED | |
| TC-09 vocabulary | PASS/FAIL/BLOCKED | |
| TC-10 substantiveness parity | PASS/FAIL/BLOCKED | |
| TC-11 qa-smoke.sh | PASS/FAIL/BLOCKED | |
| TC-12 browser smoke | PASS/FAIL/BLOCKED | |
| TC-13 visual screenshots | PASS/FAIL/BLOCKED | |
| TC-14 a11y door submit (RELEASE-BLOCKER) | PASS/FAIL/BLOCKED | |
| TC-100 empty concept | PASS/FAIL/BLOCKED | |
| TC-101 long concept | PASS/FAIL/BLOCKED | |
| TC-102 weird characters | PASS/FAIL/BLOCKED | |
| TC-103 rapid-click | PASS/FAIL/BLOCKED | |
| TC-104 source-attach toggle race | PASS/FAIL/BLOCKED | |
| TC-105 thin threshold variations | PASS/FAIL/BLOCKED | |
| TC-106 over-long threshold | PASS/FAIL/BLOCKED | |
| TC-107 concurrent tabs | PASS/FAIL/BLOCKED | |
| TC-108 stale shell | PASS/FAIL/BLOCKED | |
| TC-109 skeleton-line leak | PASS/FAIL/BLOCKED | |
| TC-110 library cap gate | PASS/FAIL/BLOCKED | |
| TC-111 cap exceeded → 500 | PASS/FAIL/BLOCKED | |
| TC-112 multiple concepts | PASS/FAIL/BLOCKED | |
| TC-113 persistence-then-clear | PASS/FAIL/BLOCKED | |
| TC-114 vocab regression grep | PASS/FAIL/BLOCKED | |
| TC-115 source-attach no shell | PASS/FAIL/BLOCKED | |
| TC-116 console errors | PASS/FAIL/BLOCKED | |

## Failures — detailed

For each FAIL, fill in:

### {TC-XX} — {one-line failure summary}

- **Spec / contract violated:** {link to spec section or "no explicit spec — agent flagged ruthless edge case"}
- **Steps to reproduce:** {numbered, complete}
- **Expected:** {what the spec/test expected}
- **Actual:** {what happened}
- **Severity:** [BLOCKER | HIGH | MEDIUM | LOW]
- **Suggested fix scope:** {file path + ~line range, or "needs investigation"}
- **Console output / network / screenshots:** {paste or reference}

(Repeat for each FAIL.)

## BLOCKED tests

For each BLOCKED test, one line on why (e.g. "no model API key available — could not exercise live LLM cap behavior").

## Notes / observations not tied to a specific failure

- {anything the user should know — copy nits, prompt-quality observations on TC-112, latency outliers, etc.}

## Next-step recommendations

- {list of items to address before push, in priority order}
```

---

## 5. Doctrine reminders for the executing agent

- **Don't accept "looks fine."** Every test has a verifier. Run it.
- **Don't fix bugs you find unless explicitly requested.** Log them in the breakfix report.
- **If a test is ambiguous, mark BLOCKED with a one-line reason.** Better than guessing.
- **Visual screenshots matter.** Even if every test passes, dark/light mode broken layouts are still ship blockers.
- **A11y is a release blocker (TC-14).** Not a polish item.
- **The persistence-then-clear ordering (TC-113) is doctrinally load-bearing.** If it regresses, the spec's principle #2 is violated even if the happy path works.
- **Keep the report tight.** PASS rows can be one line. FAIL rows need full repro + suggested fix scope.
